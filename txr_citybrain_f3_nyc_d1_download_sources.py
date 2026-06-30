#!/usr/bin/env python3
"""F3-NYC-D1 official source downloader.

Downloads the requested NYC Open Data/Socrata sources into a resumable raw
landing pack. Chunks are CSV for size/performance, while source JSON endpoints,
metadata, schemas, row counts, and exact URLs are preserved in manifests.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests


TASK = "F3-NYC-D1 Official NYC Safety Source Download"
DEFAULT_OUTPUT_DIR = "data_landing/f3_nyc_d1_official_sources_v1"
DEFAULT_CHUNK_SIZE = 50_000
DOMAIN = "data.cityofnewyork.us"
BOUNDARY = (
    "F3-NYC-D1 is an official-source raw data landing pack for Flow 3. "
    "It does not build the Flow 3 cartridge, certify affected assets, perform geocoding, "
    "or make emergency response recommendations."
)

DATASETS: dict[str, dict[str, Any]] = {
    "mvc_crashes": {
        "title": "Motor Vehicle Collisions - Crashes",
        "resource_id": "h9gi-nx95",
        "json_endpoint": "https://data.cityofnewyork.us/resource/h9gi-nx95.json",
        "expected_rows_user": 2_269_187,
        "filename_base": "Motor_Vehicle_Collisions_-_Crashes",
        "preferred_order": ["collision_id", "crash_date", "crash_time"],
    },
    "fire_incident_dispatch": {
        "title": "Fire Incident Dispatch Data",
        "resource_id": "8m42-w767",
        "json_endpoint": "https://data.cityofnewyork.us/resource/8m42-w767.json",
        "expected_rows_user": 11_819_520,
        "filename_base": "Fire_Incident_Dispatch_Data",
        "preferred_order": ["starfire_incident_id", "incident_datetime", "incident_date_time"],
    },
    "fdny_firehouses": {
        "title": "FDNY Firehouse Listing",
        "resource_id": "hc8x-tcnd",
        "json_endpoint": "https://data.cityofnewyork.us/resource/hc8x-tcnd.json",
        "expected_rows_user": 219,
        "filename_base": "FDNY_Firehouse_Listing",
        "preferred_order": ["facilityname", "facility_name", "borough"],
    },
    "ems_incident_dispatch": {
        "title": "EMS Incident Dispatch Data",
        "resource_id": "76xm-jjuj",
        "json_endpoint": "https://data.cityofnewyork.us/resource/76xm-jjuj.json",
        "expected_rows_user": 29_572_156,
        "filename_base": "EMS_Incident_Dispatch_Data",
        "preferred_order": ["cad_incident_id", "incident_datetime", "incident_date_time"],
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_dataset_dir(dataset: dict[str, Any]) -> str:
    return f"{dataset['filename_base']}__{dataset['resource_id']}"


def response_json(url: str, params: dict[str, Any] | None = None, timeout: int = 120, retries: int = 4) -> Any:
    last_error: str | None = None
    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": "TXR-CityBrain-F3-D1/1.0"})
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001
            last_error = repr(exc)
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET failed for {url}: {last_error}")


def get_metadata(resource_id: str) -> dict[str, Any]:
    return response_json(f"https://{DOMAIN}/api/views/{resource_id}", timeout=120)


def get_count(resource_id: str) -> int:
    url = f"https://{DOMAIN}/resource/{resource_id}.json"
    data = response_json(url, params={"$query": "select count(*)"}, timeout=120)
    if not data or "count" not in data[0]:
        raise RuntimeError(f"count query returned unexpected payload for {resource_id}: {data!r}")
    return int(data[0]["count"])


def choose_order(metadata: dict[str, Any], preferred: list[str]) -> str | None:
    fields = {col.get("fieldName") for col in metadata.get("columns", []) if col.get("fieldName")}
    for field in preferred:
        if field in fields:
            return field
    for fallback in ["created_at", "updated_at", ":id"]:
        if fallback in fields:
            return fallback
    return None


def csv_row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        return max(sum(1 for _ in reader) - 1, 0)


def download_csv_chunk(
    resource_id: str,
    out_path: Path,
    limit: int,
    offset: int,
    order_field: str | None,
    timeout: int,
) -> dict[str, Any]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".part")
    if tmp.exists():
        tmp.unlink()
    params: dict[str, Any] = {"$limit": limit, "$offset": offset}
    if order_field:
        params["$order"] = order_field
    url = f"https://{DOMAIN}/resource/{resource_id}.csv"
    started = time.time()
    with requests.get(url, params=params, timeout=timeout, stream=True, headers={"User-Agent": "TXR-CityBrain-F3-D1/1.0"}) as response:
        response.raise_for_status()
        with tmp.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    tmp.replace(out_path)
    rows = csv_row_count(out_path)
    return {
        "path": str(out_path),
        "download_url": url + "?" + urlencode(params),
        "offset": offset,
        "limit": limit,
        "rows": rows,
        "bytes": out_path.stat().st_size,
        "sha256": sha256_file(out_path),
        "seconds": round(time.time() - started, 3),
        "status": "downloaded",
    }


def existing_chunk_status(path: Path, expected_limit: int | None = None) -> dict[str, Any] | None:
    if not path.exists() or path.stat().st_size <= 0:
        return None
    rows = csv_row_count(path)
    if expected_limit is not None and expected_limit > 0 and rows == 0:
        return None
    return {
        "path": str(path),
        "rows": rows,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "status": "existing",
    }


def write_dataset_readme(dataset_dir: Path, dataset: dict[str, Any], count: int, target: int, order_field: str | None) -> None:
    text = f"""# {dataset['title']}

{BOUNDARY}

- Resource ID: `{dataset['resource_id']}`
- JSON endpoint: `{dataset['json_endpoint']}`
- CSV chunk source: `https://{DOMAIN}/resource/{dataset['resource_id']}.csv`
- Socrata row count at download time: `{count}`
- Target rows for this run: `{target}`
- Chunk ordering field: `{order_field or 'none'}`

Rows are stored as resumable CSV chunks under `chunks/`.
"""
    (dataset_dir / "README.md").write_text(text, encoding="utf-8")


def download_dataset(
    dataset_key: str,
    dataset: dict[str, Any],
    out_root: Path,
    chunk_size: int,
    max_rows: int | None,
    timeout: int,
    workers: int = 1,
) -> dict[str, Any]:
    dataset_dir = out_root / "raw" / safe_dataset_dir(dataset)
    chunks_dir = dataset_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    metadata = get_metadata(dataset["resource_id"])
    schema = [
        {
            "name": col.get("name"),
            "fieldName": col.get("fieldName"),
            "dataTypeName": col.get("dataTypeName"),
            "description": col.get("description"),
        }
        for col in metadata.get("columns", [])
        if col.get("fieldName") and not str(col.get("fieldName")).startswith(":")
    ]
    write_json(dataset_dir / "source_metadata_full.json", metadata)
    write_json(dataset_dir / "schema.json", schema)

    count = get_count(dataset["resource_id"])
    target = min(count, max_rows) if max_rows else count
    order_field = choose_order(metadata, dataset.get("preferred_order", []))
    write_dataset_readme(dataset_dir, dataset, count, target, order_field)
    source_manifest = {
        "dataset_key": dataset_key,
        "title": dataset["title"],
        "resource_id": dataset["resource_id"],
        "json_endpoint": dataset["json_endpoint"],
        "metadata_endpoint": f"https://{DOMAIN}/api/views/{dataset['resource_id']}",
        "csv_endpoint": f"https://{DOMAIN}/resource/{dataset['resource_id']}.csv",
        "socrata_count": count,
        "user_expected_rows": dataset.get("expected_rows_user"),
        "target_rows": target,
        "chunk_size": chunk_size,
        "order_field": order_field,
        "created_utc": utc_now(),
        "boundary_statement": BOUNDARY,
    }
    write_json(dataset_dir / "source_manifest.json", source_manifest)

    chunk_reports_by_index: dict[int, dict[str, Any]] = {}
    missing_chunks: list[tuple[int, int, int, Path]] = []
    chunks_expected = math.ceil(target / chunk_size) if target else 0

    def write_partial() -> None:
        reports = [chunk_reports_by_index[idx] for idx in sorted(chunk_reports_by_index)]
        downloaded_rows = sum(int(row.get("rows", 0)) for row in reports)
        write_json(
            dataset_dir / "chunk_manifest.partial.json",
            {"chunks": reports, "downloaded_rows": downloaded_rows, "updated_utc": utc_now()},
        )

    for chunk_index in range(chunks_expected):
        offset = chunk_index * chunk_size
        limit = min(chunk_size, target - offset)
        chunk_path = chunks_dir / f"{dataset['filename_base']}__chunk_{chunk_index:05d}__offset_{offset}.csv"
        status = existing_chunk_status(chunk_path, limit)
        if status is None:
            missing_chunks.append((chunk_index, offset, limit, chunk_path))
        else:
            print(f"[SKIP] {dataset_key} chunk={chunk_index + 1}/{chunks_expected} rows={status['rows']:,}", flush=True)
            status.update({"chunk_index": chunk_index, "offset": offset, "limit": limit})
            chunk_reports_by_index[chunk_index] = status
    write_partial()

    def fetch_missing(chunk_index: int, offset: int, limit: int, chunk_path: Path) -> dict[str, Any]:
        status = download_csv_chunk(dataset["resource_id"], chunk_path, limit, offset, order_field, timeout)
        status.update({"chunk_index": chunk_index, "offset": offset, "limit": limit})
        return status

    if missing_chunks and workers <= 1:
        for chunk_index, offset, limit, chunk_path in missing_chunks:
            print(f"[GET] {dataset_key} chunk={chunk_index + 1}/{chunks_expected} offset={offset:,} limit={limit:,}", flush=True)
            status = fetch_missing(chunk_index, offset, limit, chunk_path)
            chunk_reports_by_index[chunk_index] = status
            print(
                f"[OK ] {dataset_key} chunk={chunk_index + 1}/{chunks_expected} rows={status['rows']:,} size={status['bytes']/1024/1024:.1f} MB time={status.get('seconds')}s",
                flush=True,
            )
            write_partial()
            if int(status.get("rows", 0)) == 0:
                break
    elif missing_chunks:
        print(f"[POOL] {dataset_key} missing_chunks={len(missing_chunks):,} workers={workers}", flush=True)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(fetch_missing, chunk_index, offset, limit, chunk_path): chunk_index
                for chunk_index, offset, limit, chunk_path in missing_chunks
            }
            for future in as_completed(futures):
                chunk_index = futures[future]
                status = future.result()
                chunk_reports_by_index[chunk_index] = status
                print(
                    f"[OK ] {dataset_key} chunk={chunk_index + 1}/{chunks_expected} rows={status['rows']:,} size={status['bytes']/1024/1024:.1f} MB time={status.get('seconds')}s",
                    flush=True,
                )
                write_partial()

    chunk_reports = [chunk_reports_by_index[idx] for idx in sorted(chunk_reports_by_index)]
    downloaded_rows = sum(int(status.get("rows", 0)) for status in chunk_reports)
    downloaded_bytes = sum(int(status.get("bytes", 0)) for status in chunk_reports)

    dataset_report = {
        **source_manifest,
        "chunks": chunk_reports,
        "chunk_count": len(chunk_reports),
        "downloaded_rows": downloaded_rows,
        "downloaded_bytes": downloaded_bytes,
        "row_count_match": downloaded_rows == target,
        "status": "PASS" if downloaded_rows == target else "PARTIAL",
        "completed_utc": utc_now(),
    }
    write_json(dataset_dir / "chunk_manifest.json", dataset_report)
    return dataset_report


def write_hashes(out_root: Path) -> dict[str, Any]:
    hashes = {}
    for path in sorted(out_root.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            hashes[str(path.relative_to(out_root)).replace("\\", "/")] = sha256_file(path)
    report = {"task": TASK, "created_utc": utc_now(), "file_count": len(hashes), "sha256s": hashes}
    write_json(out_root / "SHA256SUMS.json", report)
    return report


def parse_dataset_caps(values: list[str] | None) -> dict[str, int]:
    caps: dict[str, int] = {}
    for value in values or []:
        if "=" not in value:
            raise ValueError(f"dataset cap must look like dataset_key=rows, got {value!r}")
        key, raw_rows = value.split("=", 1)
        key = key.strip()
        rows = int(raw_rows.replace(",", "").strip())
        if key not in DATASETS:
            raise ValueError(f"unknown dataset in cap: {key}")
        if rows <= 0:
            raise ValueError(f"dataset cap must be positive for {key}")
        caps[key] = rows
    return caps


def run_download(
    output_dir: str,
    datasets: list[str] | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    max_rows: int | None = None,
    timeout: int = 240,
    dataset_caps: dict[str, int] | None = None,
    workers: int = 1,
) -> dict[str, Any]:
    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    selected = datasets or list(DATASETS)
    dataset_caps = dataset_caps or {}
    reports = []
    failures = []
    started = utc_now()
    for key in selected:
        if key not in DATASETS:
            failures.append({"dataset_key": key, "error": "unknown_dataset"})
            continue
        try:
            effective_max = dataset_caps.get(key, max_rows)
            reports.append(download_dataset(key, DATASETS[key], out_root, chunk_size, effective_max, timeout, workers))
        except Exception as exc:  # noqa: BLE001
            failures.append({"dataset_key": key, "error": repr(exc)})
            print(f"[FAIL] {key}: {exc!r}", flush=True)
            write_json(out_root / "F3_NYC_D1_DOWNLOAD_FAILURES.json", failures)
    summary = {
        "task": TASK,
        "status": "PASS" if not failures and all(r["status"] == "PASS" for r in reports) else "PARTIAL",
        "started_utc": started,
        "completed_utc": utc_now(),
        "output_dir": str(out_root),
        "chunk_size": chunk_size,
        "max_rows": max_rows,
        "dataset_caps": dataset_caps,
        "workers": workers,
        "datasets": reports,
        "failures": failures,
        "boundary_statement": BOUNDARY,
    }
    failures_path = out_root / "F3_NYC_D1_DOWNLOAD_FAILURES.json"
    if not failures and failures_path.exists():
        failures_path.unlink()
    write_json(out_root / "F3_NYC_D1_DOWNLOAD_MANIFEST.json", summary)
    hashes = write_hashes(out_root)
    summary["sha256_file_count"] = hashes["file_count"]
    write_json(out_root / "F3_NYC_D1_DOWNLOAD_MANIFEST.json", summary)
    write_hashes(out_root)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--dataset", action="append", dest="datasets")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--dataset-cap", action="append", dest="dataset_caps", help="Per-dataset cap, e.g. fire_incident_dispatch=2000000")
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    caps = parse_dataset_caps(args.dataset_caps)
    summary = run_download(args.output_dir, args.datasets, args.chunk_size, args.max_rows, args.timeout, caps, args.workers)
    print(json.dumps({k: summary[k] for k in ["task", "status", "output_dir", "chunk_size", "max_rows", "workers"]}, indent=2))
    for ds in summary["datasets"]:
        print(f"{ds['dataset_key']}: {ds['status']} rows={ds['downloaded_rows']:,}/{ds['target_rows']:,} chunks={ds['chunk_count']}")
    if summary["failures"]:
        print("Failures:", json.dumps(summary["failures"], indent=2), file=sys.stderr)
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import shutil
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests


TASK = "CHI-ALLFLOWS-DATA-LANDING-R1"
DEFAULT_ROOT = Path("outputs/chi_allflows_data_landing_r1")
DEFAULT_SCOUT = Path("outputs/chi_allflows_d1_source_shape_scout/CHI_ALLFLOWS_D1_SOURCE_SHAPE_SCOUT.json")
USER_AGENT = "TXR-CityBrain-CHI-AllFlows-Data-Landing-R1/1.0"
CHUNK_SIZE = 50_000
PHASE1_CAP = 1_000_000

PASS_PHASE_0 = "PASS_PHASE_0_PREFLIGHT"
PASS_PHASE_1 = "PASS_PHASE_1_BREADTH"
PASS_WITH_LIMITATIONS = "PASS_WITH_LIMITATIONS"
FAIL = "FAIL"

SODA_READY = "SODA2_BULK_READY"
DIRECT_FILE_READY = "DIRECT_FILE_READY"
DIRECT_METADATA_ONLY = "DIRECT_METADATA_ONLY"
KEY_REQUIRED = "KEY_REQUIRED"
KEY_BLOCKED = "KEY_BLOCKED"
BLOCKED_REMOTE = "BLOCKED_REMOTE"
SKIP_WITH_REASON = "SKIP_WITH_REASON"

FULL_COMPLETE = "FULL_COMPLETE"
PARTIAL_CAP_COMPLETE = "PARTIAL_CAP_COMPLETE"
METADATA_ONLY = "METADATA_ONLY"
DOWNLOAD_FAILED = "DOWNLOAD_FAILED"
FULL = "FULL"
WINDOWED_COMPLETE = "WINDOWED_COMPLETE"
CAPPED_BULK = "CAPPED_BULK"
BOUNDED_SAMPLE = "BOUNDED_SAMPLE"
METADATA_ONLY = "METADATA_ONLY"

FLOW_LABELS = {
    "F1": "Situational Status",
    "F2": "Planning / Compliance",
    "F3": "Incident / Affected Context",
    "F4": "Mobility / Crowd / Transport / Environment",
    "F5": "Flood / Climate / Asset Risk",
    "F6": "Industrial / Sequencing",
    "F7": "Civic + Sensor Fusion",
}

PRIVACY_RULES = {
    "crimes_2001_present": {
        "selected": [
            "id",
            "case_number",
            "date",
            "block",
            "iucr",
            "primary_type",
            "description",
            "location_description",
            "arrest",
            "domestic",
            "beat",
            "district",
            "ward",
            "community_area",
            "fbi_code",
            "year",
            "updated_on",
        ],
        "privacy_class": "public block-level context only; coordinates excluded",
        "boundary_class": "no policing, enforcement, or person-risk recommendation",
    },
    "traffic_crashes_people": {
        "selected": [
            "person_id",
            "person_type",
            "crash_record_id",
            "vehicle_id",
            "city",
            "state",
            "zipcode",
            "sex",
            "age",
            "drivers_license_state",
            "safety_equipment",
            "airbag_deployed",
            "ejection",
            "injury_classification",
            "hospital",
            "ems_agency",
            "driver_action",
            "driver_vision",
            "physical_condition",
            "pedpedal_action",
            "pedpedal_visibility",
            "pedpedal_location",
            "bac_result",
        ],
        "privacy_class": "public crash people context; privacy-safe selected fields only",
        "boundary_class": "no individual inference",
    },
}


@dataclass
class Context:
    root: Path
    scout_path: Path
    session: requests.Session
    chunk_size: int = CHUNK_SIZE


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_name(value: str) -> str:
    clean = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    while "__" in clean:
        clean = clean.replace("__", "_")
    return clean or "source"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True, default=str) + "\n", encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ensure_layout(root: Path) -> None:
    for sub in [
        "data/raw",
        "data/normalized",
        "manifests",
        "profiles",
        "scripts",
        "logs",
        "phase_reports",
    ]:
        (root / sub).mkdir(parents=True, exist_ok=True)


def load_sources(scout_path: Path) -> list[dict[str, Any]]:
    scout = read_json(scout_path, {})
    records = scout.get("records", [])
    sources: list[dict[str, Any]] = []
    for record in records:
        source_key = safe_name(record.get("source_key") or record.get("name") or record.get("dataset_id") or "source")
        api_type = record.get("api_type")
        status = DIRECT_METADATA_ONLY
        if record.get("requires_key"):
            status = KEY_BLOCKED
        elif api_type == "socrata_soda2" and record.get("domain") and record.get("dataset_id"):
            status = SODA_READY
        elif api_type == "non_socrata" and record.get("api_url"):
            status = DIRECT_FILE_READY if "zip" in str(record.get("api_url")).lower() else DIRECT_METADATA_ONLY
        sources.append(
            {
                "source_key": source_key,
                "name": record.get("name"),
                "priority": record.get("priority_band") or "P3",
                "flows": record.get("flows") or [],
                "flow_labels": record.get("flow_labels") or [],
                "api_type": api_type,
                "api_url": record.get("api_url"),
                "soda2_url": record.get("soda2_url"),
                "domain": record.get("domain"),
                "dataset_id": record.get("dataset_id"),
                "human_url": record.get("human_url"),
                "total_available": record.get("total_available"),
                "shape_status": record.get("shape_status"),
                "status": status,
                "field_info": record.get("field_info") or {},
                "sample_rows": record.get("sample_rows") or [],
                "reason": record.get("reason"),
                "boundary": record.get("boundary"),
                "requires_key": bool(record.get("requires_key")),
            }
        )
    return sorted(sources, key=lambda row: (priority_rank(row.get("priority")), row["source_key"]))


def priority_rank(priority: str | None) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "KEY_BLOCKED": 4}.get(priority or "P3", 9)


def source_where(source: dict[str, Any]) -> str | None:
    if source["source_key"] == "cook_parcels_chicago":
        return "cook_municipality_name='CITY OF CHICAGO'"
    return None


def selected_fields(source: dict[str, Any]) -> list[str] | None:
    return PRIVACY_RULES.get(source["source_key"], {}).get("selected")


def privacy_class(source: dict[str, Any]) -> str:
    if source["source_key"] in PRIVACY_RULES:
        return PRIVACY_RULES[source["source_key"]]["privacy_class"]
    text = " ".join([source.get("name") or "", source.get("source_key") or ""]).lower()
    if "crime" in text:
        return "public safety block/context only"
    if "people" in text:
        return "public person-context source; privacy review required"
    if "health" in text or "inspection" in text or "environment" in text or "air" in text:
        return "public health/environment context only; no health determination"
    return "public official data; review-context only"


def boundary_class(source: dict[str, Any]) -> str:
    if source["source_key"] in PRIVACY_RULES:
        return PRIVACY_RULES[source["source_key"]]["boundary_class"]
    text = " ".join([source.get("name") or "", source.get("source_key") or ""]).lower()
    if "crime" in text:
        return "no policing, enforcement, or person-risk recommendation"
    if "enforcement" in text:
        return "context only; no enforcement recommendation"
    if "traffic" in text or "transportation" in text or "taxi" in text:
        return "context only; no traffic-control command"
    if "health" in text or "air" in text or "environment" in text:
        return "context only; no health determination"
    if "utility" in text:
        return "context only; no utility-control recommendation"
    return "review-context only"


def recommended_mappings(source: dict[str, Any]) -> list[str]:
    flows = set(source.get("flows") or [])
    family = source.get("source_key", "")
    mappings: list[str] = []
    if "parcel" in family or "pin" in " ".join(source.get("field_info", {}).get("id_join_key_candidates", [])):
        mappings.append("Parcel/AddressableLocation")
    if "building" in family:
        mappings.append("Building/Permit/Violation")
    if "traffic" in family or "tnp" in family or "taxi" in family or "divvy" in family:
        mappings.append("MobilityEvent/RoadSegment")
    if "311" in family or "complaint" in family:
        mappings.append("CivicServiceRequest/Event")
    if "open_air" in family or "sensor" in family or "green" in family:
        mappings.append("SensorObservation/Sensor")
    if "F3" in flows:
        mappings.append("IncidentContext")
    if not mappings:
        mappings.append("AreaContext/Reference")
    return sorted(set(mappings))


def schema_profile(source: dict[str, Any]) -> dict[str, Any]:
    info = source.get("field_info") or {}
    columns = info.get("columns") or []
    lower_cols = [str(col).lower() for col in columns]
    return {
        "source_key": source["source_key"],
        "source_system": source.get("domain") or source.get("api_type"),
        "flow_candidates": source.get("flows") or [],
        "priority": source.get("priority"),
        "row_count_total": source.get("total_available"),
        "date_fields": info.get("date_time_fields") or [],
        "geo_fields": info.get("geo_fields") or [],
        "id_join_fields": info.get("id_join_key_candidates") or [],
        "pin_parcel_fields": [col for col in columns if "pin" in str(col).lower() or "parcel" in str(col).lower()],
        "building_address_fields": [col for col in columns if any(token in str(col).lower() for token in ["building", "address", "street", "zip"])][:40],
        "street_segment_fields": [col for col in columns if any(token in str(col).lower() for token in ["street", "segment", "road", "route"])][:40],
        "lat_lon_geometry_fields": [col for col, low in zip(columns, lower_cols) if any(token in low for token in ["lat", "lon", "location", "geom", "shape"])][:40],
        "privacy_class": privacy_class(source),
        "boundary_class": boundary_class(source),
        "recommended_citybrain_entity_mappings": recommended_mappings(source),
        "schema_hash": sha256_text(json.dumps(columns, sort_keys=True)),
        "sample_rows": source.get("sample_rows", [])[:2],
    }


def socrata_count(ctx: Context, source: dict[str, Any]) -> tuple[int | None, str | None]:
    params = {"$select": "count(*)"}
    where = source_where(source)
    if where:
        params["$where"] = where
    url = f"https://{source['domain']}/resource/{source['dataset_id']}.json"
    try:
        response = ctx.session.get(url, params=params, timeout=90)
        if response.status_code >= 400:
            return None, response.text[:500]
        payload = response.json()
        row = payload[0] if payload else {}
        value = row.get("count") or row.get("count_1") or next(iter(row.values()))
        return int(value), None
    except Exception as exc:  # noqa: BLE001
        return None, repr(exc)


def phase0(ctx: Context) -> dict[str, Any]:
    sources = load_sources(ctx.scout_path)
    ledger: list[dict[str, Any]] = []
    profiles: list[dict[str, Any]] = []
    for source in sources:
        print(f"Phase0 {source['source_key']} {source['status']}", flush=True)
        if source["status"] == SODA_READY:
            count, error = socrata_count(ctx, source)
            if count is not None:
                source["total_available"] = count
            elif source.get("total_available") is None:
                source["status"] = BLOCKED_REMOTE
            source["count_error"] = error
        profile = schema_profile(source)
        profiles.append(profile)
        write_json(ctx.root / "profiles" / f"{source['source_key']}.profile.json", profile)
        ledger.append({**source, "privacy_class": profile["privacy_class"], "boundary_class": profile["boundary_class"], "schema_hash": profile["schema_hash"]})
    write_json(ctx.root / "CHI_ALLFLOWS_SOURCE_LEDGER.json", ledger)
    write_json(ctx.root / "CHI_ALLFLOWS_SCHEMA_PROFILES.json", profiles)
    write_json(ctx.root / "CHI_ALLFLOWS_PHASE_MANIFEST.json", {"phase": 0, "status": PASS_PHASE_0, "generated_at": utc_now(), "sources": ledger})
    write_phase_docs(ctx.root, ledger, [], PASS_PHASE_0)
    return {"status": PASS_PHASE_0, "sources": ledger}


def chunk_paths(ctx: Context, source_key: str, phase: int, index: int) -> dict[str, Path]:
    raw_dir = ctx.root / "data" / "raw" / source_key / f"phase_{phase}"
    norm_dir = ctx.root / "data" / "normalized" / source_key / f"phase_{phase}"
    return {
        "raw": raw_dir / f"chunk_{index:06d}.jsonl.gz",
        "parquet": norm_dir / f"part-{index:06d}.parquet",
    }


def manifest_path(ctx: Context, source_key: str) -> Path:
    return ctx.root / "manifests" / f"{source_key}.manifest.json"


def load_manifest(ctx: Context, source_key: str) -> dict[str, Any]:
    return read_json(manifest_path(ctx, source_key), {"source_key": source_key, "chunks": [], "phases": {}})


def write_chunk(paths: dict[str, Path], rows: list[dict[str, Any]]) -> dict[str, Any]:
    paths["raw"].parent.mkdir(parents=True, exist_ok=True)
    paths["parquet"].parent.mkdir(parents=True, exist_ok=True)
    tmp_raw = paths["raw"].with_suffix(paths["raw"].suffix + ".part")
    tmp_parquet = paths["parquet"].with_suffix(paths["parquet"].suffix + ".part")
    with gzip.open(tmp_raw, "wt", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, default=str) + "\n")
    table = pa.Table.from_pylist(rows) if rows else pa.table({})
    pq.write_table(table, tmp_parquet, compression="zstd")
    os.replace(tmp_raw, paths["raw"])
    os.replace(tmp_parquet, paths["parquet"])
    return {
        "raw_path": str(paths["raw"]),
        "parquet_path": str(paths["parquet"]),
        "rows": len(rows),
        "raw_sha256": sha256_file(paths["raw"]),
        "parquet_sha256": sha256_file(paths["parquet"]),
        "raw_bytes": paths["raw"].stat().st_size,
        "parquet_bytes": paths["parquet"].stat().st_size,
    }


def existing_chunk(paths: dict[str, Path]) -> dict[str, Any] | None:
    if paths["raw"].exists() and paths["parquet"].exists():
        try:
            rows = pq.read_metadata(paths["parquet"]).num_rows
        except Exception:
            rows = 0
        return {
            "raw_path": str(paths["raw"]),
            "parquet_path": str(paths["parquet"]),
            "rows": rows,
            "raw_sha256": sha256_file(paths["raw"]),
            "parquet_sha256": sha256_file(paths["parquet"]),
            "raw_bytes": paths["raw"].stat().st_size,
            "parquet_bytes": paths["parquet"].stat().st_size,
            "reused": True,
        }
    return None


def socrata_chunk(ctx: Context, source: dict[str, Any], offset: int, limit: int) -> tuple[list[dict[str, Any]], str | None, str]:
    params: dict[str, Any] = {"$limit": str(limit), "$offset": str(offset)}
    where = source_where(source)
    if where:
        params["$where"] = where
    fields = selected_fields(source)
    if fields:
        params["$select"] = ",".join(fields)
    url = f"https://{source['domain']}/resource/{source['dataset_id']}.json"
    full_url = f"{url}?{urlencode(params)}"
    try:
        response = ctx.session.get(url, params=params, timeout=120)
        if response.status_code >= 400:
            return [], response.text[:500], full_url
        payload = response.json()
        return payload if isinstance(payload, list) else [], None, full_url
    except Exception as exc:  # noqa: BLE001
        return [], repr(exc), full_url


def land_soda_phase(ctx: Context, source: dict[str, Any], phase: int, cap: int) -> dict[str, Any]:
    source_key = source["source_key"]
    manifest = load_manifest(ctx, source_key)
    total = source.get("total_available")
    if total is None:
        total, error = socrata_count(ctx, source)
        source["total_available"] = total
        source["count_error"] = error
    target = min(int(total or 0), cap) if total is not None else cap
    if target <= 0:
        status = METADATA_ONLY
        landed = 0
    else:
        status = PARTIAL_CAP_COMPLETE
        landed = 0
    phase_chunks = []
    failures = []
    for offset in range(0, target, ctx.chunk_size):
        index = offset // ctx.chunk_size + 1
        limit = min(ctx.chunk_size, target - offset)
        paths = chunk_paths(ctx, source_key, phase, index)
        existing = existing_chunk(paths)
        if existing and existing.get("rows") == limit:
            chunk = {**existing, "offset": offset, "limit": limit, "status": "REUSED"}
        else:
            rows, error, query_url = socrata_chunk(ctx, source, offset, limit)
            if error:
                failures.append({"offset": offset, "limit": limit, "error": error, "query_url": query_url})
                status = DOWNLOAD_FAILED
                break
            chunk_meta = write_chunk(paths, rows)
            chunk = {**chunk_meta, "offset": offset, "limit": limit, "status": "DOWNLOADED", "query_url": query_url}
            if len(rows) < limit:
                # Source ended earlier than the probed count; keep the landing coherent.
                phase_chunks.append(chunk)
                landed += len(rows)
                break
        phase_chunks.append(chunk)
        landed += int(chunk.get("rows") or 0)
        if landed and landed % 250_000 == 0:
            print(f"  {source_key}: {landed:,}/{target:,}", flush=True)
    if status != DOWNLOAD_FAILED:
        status = FULL_COMPLETE if total is not None and landed >= int(total) else PARTIAL_CAP_COMPLETE
    profile = schema_profile(source)
    profile["row_count_landed"] = landed
    write_json(ctx.root / "profiles" / f"{source_key}.profile.json", profile)
    phase_record = {
        "phase": phase,
        "target_cap": cap,
        "target_rows": target,
        "landed_rows": landed,
        "chunk_count": len(phase_chunks),
        "status": status,
        "failures": failures,
        "updated_at": utc_now(),
    }
    all_chunks = [row for row in manifest.get("chunks", []) if row.get("phase") != phase]
    all_chunks.extend({**chunk, "phase": phase} for chunk in phase_chunks)
    manifest.update(
        {
            "source_key": source_key,
            "name": source.get("name"),
            "dataset_id": source.get("dataset_id"),
            "api_url": source.get("api_url"),
            "query_filters": {"where": source_where(source), "selected_fields": selected_fields(source)},
            "total_source_count": total,
            "target_cap": cap,
            "landed_rows": landed,
            "chunk_count": len(phase_chunks),
            "schema_hash": profile["schema_hash"],
            "status": status,
            "privacy_class": profile["privacy_class"],
            "boundary_class": profile["boundary_class"],
            "phases": {**manifest.get("phases", {}), str(phase): phase_record},
            "chunks": all_chunks,
        }
    )
    write_json(manifest_path(ctx, source_key), manifest)
    return manifest


def land_direct_file(ctx: Context, source: dict[str, Any], phase: int) -> dict[str, Any]:
    source_key = source["source_key"]
    manifest = load_manifest(ctx, source_key)
    target = ctx.root / "data" / "raw" / source_key / f"phase_{phase}" / Path(source.get("api_url") or source_key).name
    status = DIRECT_METADATA_ONLY
    if source.get("api_url") and not source.get("requires_key"):
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            response = ctx.session.get(source["api_url"], timeout=120)
            response.raise_for_status()
            target.write_bytes(response.content)
        status = FULL_COMPLETE
    manifest.update(
        {
            "source_key": source_key,
            "name": source.get("name"),
            "api_url": source.get("api_url"),
            "target_cap": None,
            "landed_rows": 0,
            "chunk_count": 1 if target.exists() else 0,
            "status": status,
            "privacy_class": privacy_class(source),
            "boundary_class": boundary_class(source),
            "phases": {**manifest.get("phases", {}), str(phase): {"phase": phase, "status": status, "updated_at": utc_now()}},
            "chunks": [{"phase": phase, "path": str(target), "sha256": sha256_file(target), "bytes": target.stat().st_size}] if target.exists() else [],
        }
    )
    write_json(manifest_path(ctx, source_key), manifest)
    return manifest


def phase1(ctx: Context) -> dict[str, Any]:
    if not (ctx.root / "CHI_ALLFLOWS_SOURCE_LEDGER.json").exists():
        phase0(ctx)
    ledger = read_json(ctx.root / "CHI_ALLFLOWS_SOURCE_LEDGER.json", [])
    manifests = []
    for source in sorted(ledger, key=lambda row: (priority_rank(row.get("priority")), row["source_key"])):
        print(f"Phase1 {source['source_key']} {source['status']}", flush=True)
        if source["status"] == SODA_READY:
            manifests.append(land_soda_phase(ctx, source, phase=1, cap=PHASE1_CAP))
        elif source["status"] == DIRECT_FILE_READY:
            try:
                manifests.append(land_direct_file(ctx, source, phase=1))
            except Exception as exc:  # noqa: BLE001
                manifest = load_manifest(ctx, source["source_key"])
                manifest.update({"source_key": source["source_key"], "status": BLOCKED_REMOTE, "error": repr(exc)})
                write_json(manifest_path(ctx, source["source_key"]), manifest)
                manifests.append(manifest)
        else:
            manifest = load_manifest(ctx, source["source_key"])
            manifest.update(
                {
                    "source_key": source["source_key"],
                    "name": source.get("name"),
                    "api_url": source.get("api_url"),
                    "status": source.get("status"),
                    "skip_reason": "key required or metadata-only source",
                    "landed_rows": 0,
                    "privacy_class": privacy_class(source),
                    "boundary_class": boundary_class(source),
                    "phases": {**manifest.get("phases", {}), "1": {"phase": 1, "status": source.get("status"), "updated_at": utc_now()}},
                }
            )
            write_json(manifest_path(ctx, source["source_key"]), manifest)
            manifests.append(manifest)
    status = PASS_PHASE_1 if not any(m.get("status") == DOWNLOAD_FAILED for m in manifests) else PASS_WITH_LIMITATIONS
    write_json(ctx.root / "CHI_ALLFLOWS_PHASE_MANIFEST.json", {"phase": 1, "status": status, "generated_at": utc_now(), "sources": manifests})
    write_phase_docs(ctx.root, ledger, manifests, status)
    return {"status": status, "sources": manifests}


def write_phase_docs(root: Path, ledger: list[dict[str, Any]], manifests: list[dict[str, Any]], status: str) -> None:
    manifest_by_key = {m.get("source_key"): m for m in manifests}
    rows = []
    for source in ledger:
        manifest = manifest_by_key.get(source["source_key"], {})
        landed_rows = int(manifest.get("landed_rows", 0) or 0)
        total_available = source.get("total_available")
        if total_available is None:
            total_available = manifest.get("total_source_count")
        cap_rule = phase1_target_rows(total_available)
        raw_status = manifest.get("status", source.get("status"))
        rows.append(
            {
                "source_key": source["source_key"],
                "name": source.get("name"),
                "priority": source.get("priority"),
                "flows": ",".join(source.get("flows") or []),
                "total_available": total_available,
                "cap_rule_applied": cap_rule,
                "rows_landed": landed_rows,
                "coverage_pct": coverage_percent(landed_rows, total_available),
                "landing_status": canonical_landing_status(raw_status, landed_rows, total_available, cap_rule),
                "raw_status": raw_status,
                "privacy_class": manifest.get("privacy_class", privacy_class(source)),
                "boundary_class": manifest.get("boundary_class", boundary_class(source)),
            }
        )
    with (root / "CHI_ALLFLOWS_DATASET_STATUS.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["source_key"])
        writer.writeheader()
        writer.writerows(rows)
    by_phase = [{"phase": 1, "sources": len(rows), "rows_landed": sum(int(row.get("rows_landed") or 0) for row in rows)}]
    with (root / "CHI_ALLFLOWS_COUNTS_BY_PHASE.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["phase", "sources", "rows_landed"])
        writer.writeheader()
        writer.writerows(by_phase)
    write_text_reports(root, rows, status)
    write_hashes(root)


def canonical_landing_status(raw_status: str | None, landed_rows: int, total_available: Any, cap_rule: int | None) -> str:
    total = to_int(total_available)
    if raw_status in {KEY_BLOCKED, KEY_REQUIRED, DIRECT_METADATA_ONLY, BLOCKED_REMOTE, SKIP_WITH_REASON}:
        return METADATA_ONLY
    if landed_rows <= 0:
        return METADATA_ONLY
    if total is not None and landed_rows >= total:
        return FULL
    if cap_rule is not None and landed_rows >= cap_rule:
        return CAPPED_BULK
    return BOUNDED_SAMPLE


def coverage_percent(landed_rows: int, total_available: Any) -> str:
    total = to_int(total_available)
    if total is None or total <= 0:
        return ""
    return f"{(landed_rows / total) * 100:.2f}%"


def to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def phase1_target_rows(total_available: Any) -> int | None:
    total = to_int(total_available)
    if total is None:
        return None
    return min(total, PHASE1_CAP)


def write_text_reports(root: Path, rows: list[dict[str, Any]], status: str) -> None:
    total_rows = sum(int(row.get("rows_landed") or 0) for row in rows)
    flow_counts: dict[str, int] = {flow: 0 for flow in FLOW_LABELS}
    priority_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for row in rows:
        landed = int(row.get("rows_landed") or 0)
        for flow in str(row.get("flows") or "").split(","):
            if flow:
                flow_counts[flow] += landed
        priority = str(row.get("priority") or "UNKNOWN")
        priority_counts[priority] = priority_counts.get(priority, 0) + landed
        landing_status = str(row.get("landing_status") or "UNKNOWN")
        status_counts[landing_status] = status_counts.get(landing_status, 0) + 1
    write_rollup_csv(root / "CHI_ALLFLOWS_ROWS_BY_FLOW.csv", ["flow", "label", "rows_landed"], [
        {"flow": flow, "label": FLOW_LABELS[flow], "rows_landed": count} for flow, count in flow_counts.items()
    ])
    write_rollup_csv(root / "CHI_ALLFLOWS_ROWS_BY_PRIORITY.csv", ["priority", "rows_landed"], [
        {"priority": priority, "rows_landed": priority_counts[priority]} for priority in sorted(priority_counts)
    ])
    write_rollup_csv(root / "CHI_ALLFLOWS_STATUS_COUNTS.csv", ["landing_status", "source_count"], [
        {"landing_status": key, "source_count": status_counts[key]} for key in sorted(status_counts)
    ])
    readme = [
        "# CHI-ALLFLOWS-DATA-LANDING-R1",
        "",
        f"Status: `{status}`",
        f"Generated: `{utc_now()}`",
        "",
        f"Sources tracked: `{len(rows)}`",
        f"Rows landed: `{total_rows:,}`",
        "",
        "This is a stop-safe Chicago all-flows data landing run. It preserves source fields and writes raw JSONL.GZ plus normalized Parquet chunks where tabular SODA2 sources are feasible.",
    ]
    (root / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    plan = [
        "# CHI All-Flows Landing Plan",
        "",
        "Phase 0 rebuilds source ledger and schema profiles.",
        "Phase 1 lands a breadth pass up to 1,000,000 rows per feasible tabular source.",
        "Later phases increase depth by priority and use windows for very large sources.",
        "",
        "Landing status language: `FULL`, `WINDOWED_COMPLETE`, `CAPPED_BULK`, `BOUNDED_SAMPLE`, `METADATA_ONLY`.",
    ]
    (root / "CHI_ALLFLOWS_LANDING_PLAN.md").write_text("\n".join(plan) + "\n", encoding="utf-8")
    privacy = [
        "# Privacy And Boundary",
        "",
        "- Crimes: block/context only; no policing or enforcement recommendation.",
        "- Crash People: selected privacy-safe fields only; no individual inference.",
        "- Health/environment/inspection sources: no health determination.",
        "- Environmental enforcement: context only; no enforcement recommendation.",
        "- 811 utility hit tickets: no utility-control recommendation.",
        "- Traffic/transport: no traffic-control command.",
        "- CTA live APIs: key-gated; no fabricated live data.",
    ]
    (root / "CHI_ALLFLOWS_PRIVACY_BOUNDARY.md").write_text("\n".join(privacy) + "\n", encoding="utf-8")
    limitations = [
        "# Limitations",
        "",
        "- Phase 1 is breadth-first and capped at 1M rows per feasible tabular source.",
        "- Very large mobility datasets require later windowed depth phases.",
        "- SODA2 counts may change as source portals update.",
        "- Metadata-only and key-blocked sources are recorded but not bulk-landed.",
        "- `BOUNDED_SAMPLE` means rows landed but the run did not reach full source count or the phase cap, usually because a remote request timed out.",
    ]
    (root / "CHI_ALLFLOWS_LIMITATIONS.md").write_text("\n".join(limitations) + "\n", encoding="utf-8")
    acceptance = [
        "# Acceptance Report",
        "",
        f"Status: `{status}`",
        f"Rows landed: `{total_rows:,}`",
        "",
        "Landing status counts:",
    ]
    for key in sorted(status_counts):
        acceptance.append(f"- `{key}`: {status_counts[key]}")
    acceptance.extend([
        "",
        "Rows by priority:",
    ])
    for priority in sorted(priority_counts):
        acceptance.append(f"- `{priority}`: {priority_counts[priority]:,}")
    acceptance.extend([
        "",
        "Rows by flow:",
    ])
    for flow, count in flow_counts.items():
        acceptance.append(f"- `{flow}` {FLOW_LABELS[flow]}: {count:,}")
    acceptance.extend(
        [
            "",
            "Recommended next gates:",
            "- `CHI-F7X-D2`",
            "- `CHI-F4X-D2`",
            "- `CHI-F2X-D2`",
            "- `CHI-F5X-D2`",
        ]
    )
    (root / "CHI_ALLFLOWS_ACCEPTANCE_REPORT.md").write_text("\n".join(acceptance) + "\n", encoding="utf-8")


def write_rollup_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_existing_manifests(root: Path) -> list[dict[str, Any]]:
    manifests = []
    for path in sorted((root / "manifests").glob("*.manifest.json")):
        with path.open("r", encoding="utf-8") as handle:
            manifests.append(json.load(handle))
    return manifests


def reconcile_existing(ctx: Context) -> dict[str, Any]:
    ledger_path = ctx.root / "CHI_ALLFLOWS_SOURCE_LEDGER.json"
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    else:
        ledger = phase0(ctx)["sources"]
    manifests = load_existing_manifests(ctx.root)
    status = PASS_WITH_LIMITATIONS if any(m.get("status") == DOWNLOAD_FAILED for m in manifests) else PASS_PHASE_1
    write_phase_docs(ctx.root, ledger, manifests, status)
    return {"status": status, "sources": ledger, "manifests": manifests}


def write_hashes(root: Path) -> None:
    lines = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "CHI_ALLFLOWS_HASHES.sha256":
            rel = path.relative_to(root).as_posix()
            lines.append(f"{sha256_file(path)}  {rel}")
    (root / "CHI_ALLFLOWS_HASHES.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_script(root: Path) -> None:
    target = root / "scripts" / Path(__file__).name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__), target)


def run(phases: list[int], root: Path, scout_path: Path) -> dict[str, Any]:
    ensure_layout(root)
    copy_script(root)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    ctx = Context(root=root, scout_path=scout_path, session=session)
    result: dict[str, Any] = {}
    for phase in phases:
        if phase == 0:
            result = phase0(ctx)
        elif phase == 1:
            result = phase1(ctx)
        elif phase == 9:
            result = reconcile_existing(ctx)
        else:
            raise ValueError(f"Unsupported phase {phase}; this runner currently implements phase 0, phase 1 breadth, and phase 9 reconcile.")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chicago all-flows data landing R1")
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--scout", default=str(DEFAULT_SCOUT))
    parser.add_argument("--phase", action="append", type=int, default=None, help="Phase to run. Repeatable. Default: 0 then 1.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    phases = args.phase or [0, 1]
    result = run(phases=phases, root=Path(args.root), scout_path=Path(args.scout))
    print(json.dumps({"task": TASK, "status": result.get("status"), "root": str(Path(args.root).resolve())}, indent=2), flush=True)
    return 0 if result.get("status") != FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())

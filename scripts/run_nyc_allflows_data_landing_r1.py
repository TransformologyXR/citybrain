#!/usr/bin/env python3
"""NYC-ALLFLOWS-DATA-LANDING-R1.

Stop-safe NYC all-flows source landing pipeline.

Phase 0: metadata/count/schema/profile only.
Phase 1: breadth pass, up to 1M rows per feasible tabular source.

The runner writes fresh manifests under outputs/nyc_allflows_data_landing_r1 and
does not mutate accepted CityBrain snapshots.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pandas as pd
import requests


TASK = "NYC-ALLFLOWS-DATA-LANDING-R1"
DEFAULT_SCAN = Path("outputs/nyc_flow_source_scan/nyc_flow_source_scan.json")
DEFAULT_OUT = Path("outputs/nyc_allflows_data_landing_r1")
USER_AGENT = "TXR-CityBrain-NYC-AllFlows-R1/1.0"

SOURCE_STATES = {
    "SODA2_BULK_READY",
    "DIRECT_FILE_READY",
    "DIRECT_METADATA_ONLY",
    "TILE_OR_FILE_STRATEGY_REQUIRED",
    "KEY_REQUIRED",
    "BLOCKED_REMOTE",
    "SKIP_WITH_REASON",
}

PASS_STATUSES = {
    "PASS_PHASE_0_PREFLIGHT",
    "PASS_PHASE_1_BREADTH",
    "PASS_WITH_LIMITATIONS",
}

PERSON_PRIVACY_SAFE_FIELDS = [
    "unique_id",
    "collision_id",
    "crash_date",
    "crash_time",
    "person_type",
    "person_injury",
    "vehicle_id",
    "emotional_status",
    "bodily_injury",
    "position_in_vehicle",
    "safety_equipment",
    "ped_location",
    "ped_action",
    "complaint",
    "ped_role",
    "contributing_factor_1",
    "contributing_factor_2",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def date_floor(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT00:00:00")


def safe_key(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in value).strip("_") or "source"


def clean(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "item"):
        try:
            return clean(value.item())
        except Exception:
            pass
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean(v) for v in value]
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(payload), indent=2, sort_keys=True, ensure_ascii=True, default=str) + "\n", encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def schema_hash(columns: list[dict[str, Any]]) -> str:
    payload = json.dumps([{k: col.get(k) for k in ("field_name", "name", "data_type")} for col in columns], sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def soda_url(source: dict[str, Any], fmt: str = "json") -> str:
    return f"https://{source['domain']}/resource/{source['dataset_id']}.{fmt}"


def get_json(session: requests.Session, url: str, params: dict[str, str] | None = None, timeout: int = 45) -> tuple[Any | None, str | None]:
    try:
        response = session.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json(), None
    except Exception as exc:  # noqa: BLE001
        return None, repr(exc)


def source_state(source: dict[str, Any]) -> tuple[str, str]:
    if source.get("source_type") == "direct":
        return "DIRECT_METADATA_ONLY", "direct source captured as metadata/snapshot strategy in this runner"
    if source.get("key") in {"nyc_3d_building_model", "nyc_1ft_dem"}:
        return "TILE_OR_FILE_STRATEGY_REQUIRED", "SODA bulk count/export is blocked or unsuitable; use tile/file strategy"
    if source.get("source_type") == "socrata" and source.get("dataset_id") and source.get("domain"):
        return "SODA2_BULK_READY", "SODA2 resource endpoint available"
    return "SKIP_WITH_REASON", "source is not bound to a usable bulk endpoint"


def privacy_boundary(source: dict[str, Any]) -> tuple[str, str]:
    key = source.get("key", "")
    name = source.get("name", "")
    if key in {"nyc_ems_dispatch", "nyc_fire_dispatch"}:
        return "HIGH_BOUNDARY_PUBLIC_SAFETY", "aggregate/replay/context only; no dispatch recommendation or emergency advice"
    if key == "nyc_mvc_persons":
        return "PRIVACY_SAFE_SELECTED_FIELDS", "selected public fields only; no individual inference"
    if "restaurant" in key or "health" in name.lower():
        return "HEALTH_CONTEXT_ONLY", "inspection/facility context only; no health determination"
    if "dob" in key or "violation" in key or "hpd" in key:
        return "ENFORCEMENT_CONTEXT_ONLY", "evidence context only; no enforcement recommendation"
    if "traffic" in key or "centerline" in key or "mta" in key:
        return "MOBILITY_CONTEXT_ONLY", "mobility context only; no traffic-control or routing command"
    return "REVIEW_CONTEXT_ONLY", source.get("boundary") or "review/context only"


def selected_fields(source: dict[str, Any]) -> list[str] | None:
    if source.get("key") == "nyc_mvc_persons":
        return PERSON_PRIVACY_SAFE_FIELDS
    return None


def phase_window(source: dict[str, Any], phase: int) -> tuple[str | None, str | None, str]:
    """Return where, order, reason."""
    key = source.get("key")
    if phase < 1:
        return None, None, "preflight only"
    if key == "nyc_dot_traffic_speeds":
        return f"data_as_of >= '{date_floor(30)}'", "data_as_of DESC", "Phase 1 uses most recent 30 days for 100M+ DOT speed source"
    if key == "nyc_311_2020_present":
        return "created_date >= '2022-06-28T00:00:00'", "created_date DESC", "Phase 1 breadth draws from explicit recent 4-year operational window"
    if key == "nyc_hpd_hmc_complaints":
        return f"received_date >= '{date_floor(365 * 10)}'", "received_date DESC", "Phase 1 uses recent 10-year HPD/HMC window"
    if key == "nyc_ems_dispatch":
        return f"incident_datetime >= '{date_floor(365 * 2)}'", "incident_datetime DESC", "High-boundary EMS source uses recent 2-year aggregate/replay window"
    if key == "nyc_fire_dispatch":
        return f"incident_datetime >= '{date_floor(365 * 5)}'", "incident_datetime DESC", "High-boundary Fire source uses recent 5-year aggregate/replay window"
    if key in {"nyc_mvc_crashes", "nyc_mvc_vehicles", "nyc_mvc_persons"}:
        return None, "crash_date DESC", "MVC breadth ordered by recent crash date"
    for field in source.get("date_fields") or []:
        if field:
            return None, f"{field} DESC", f"breadth ordered by date field {field}"
    return None, ":id", "breadth ordered by Socrata row id"


def count_soda(session: requests.Session, source: dict[str, Any], where: str | None = None) -> tuple[int | None, str | None]:
    params = {"$select": "count(*)"}
    if where:
        params["$where"] = where
    payload, err = get_json(session, soda_url(source), params, timeout=60)
    if payload and isinstance(payload, list) and payload:
        try:
            return int(payload[0].get("count") or payload[0].get("count_*")), None
        except Exception as exc:  # noqa: BLE001
            return None, repr(exc)
    return None, err


def profile_from_source(source: dict[str, Any], state: str, reason: str) -> dict[str, Any]:
    privacy_class, boundary_class = privacy_boundary(source)
    columns = source.get("columns") or []
    field_names = [str(c.get("field_name", "")).lower() for c in columns]
    def fields_matching(tokens: tuple[str, ...]) -> list[str]:
        return [c.get("field_name") for c in columns if any(tok in str(c.get("field_name", "")).lower() for tok in tokens)]
    return {
        "source_key": source.get("key"),
        "source_system": "Socrata" if source.get("source_type") == "socrata" else "direct",
        "source_state": state,
        "state_reason": reason,
        "flow_candidates": source.get("flows") or [],
        "priority": source.get("priority"),
        "row_count_total": source.get("row_count"),
        "date_fields": source.get("date_fields") or [],
        "geo_fields": source.get("geo_fields") or [],
        "id_join_fields": [name for name in field_names if name in {"bbl", "bin", "building_id", "borough", "zipcode", "zip", "link_id", "collision_id", "unique_id", "locationid"} or name.endswith("_id")],
        "bbl_bin_building_fields": fields_matching(("bbl", "bin", "building")),
        "borough_zip_fields": fields_matching(("borough", "boro", "zip")),
        "street_segment_fields": fields_matching(("street", "segment", "link_id", "link_name")),
        "lat_lon_geometry_fields": fields_matching(("latitude", "longitude", "lat", "lon", "geom", "location")),
        "privacy_class": privacy_class,
        "boundary_class": boundary_class,
        "recommended_citybrain_entity_mappings": recommended_mappings(source),
        "columns": columns,
        "schema_hash": schema_hash(columns),
    }


def recommended_mappings(source: dict[str, Any]) -> list[str]:
    key = source.get("key", "")
    mappings: list[str] = []
    if any(token in key for token in ["pluto", "dob", "hpd", "ll84", "3d_building"]):
        mappings.extend(["parcel", "building", "compliance_context"])
    if any(token in key for token in ["311", "complaints", "events"]):
        mappings.extend(["civic_event", "service_context"])
    if any(token in key for token in ["traffic", "mta", "mvc", "centerline", "bike", "taxi", "fhv"]):
        mappings.extend(["mobility_link", "transport_context"])
    if any(token in key for token in ["flood", "air", "harbor", "dem"]):
        mappings.extend(["environment_context", "climate_risk_context"])
    if any(token in key for token in ["panynj", "cargo", "airport"]):
        mappings.extend(["logistics_context"])
    return sorted(set(mappings or ["review_context"]))


def load_sources(scan_path: Path) -> list[dict[str, Any]]:
    payload = read_json(scan_path, {})
    sources = payload.get("sources") or []
    return [src for src in sources if str(src.get("key", "")).startswith("nyc_") or str(src.get("key", "")).startswith("panynj_") or str(src.get("key", "")).startswith("mta_")]


def phase_manifest_path(root: Path, key: str) -> Path:
    return root / "manifests" / f"{safe_key(key)}.manifest.json"


def load_manifest(root: Path, key: str) -> dict[str, Any]:
    return read_json(phase_manifest_path(root, key), {"source_key": key, "phases": {}, "chunks": []})


def save_manifest(root: Path, manifest: dict[str, Any]) -> None:
    write_json(phase_manifest_path(root, manifest["source_key"]), manifest)


def write_raw_jsonl_gz(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(clean(row), ensure_ascii=True, default=str) + "\n")


def land_chunk(session: requests.Session, root: Path, source: dict[str, Any], phase: int, offset: int, limit: int, where: str | None, order: str | None) -> dict[str, Any]:
    key = source["key"]
    chunk_id = offset // limit if limit else 0
    raw_path = root / "data" / "raw" / key / f"phase_{phase}" / f"chunk_{chunk_id:06d}_offset_{offset:09d}.jsonl.gz"
    parquet_path = root / "data" / "normalized" / key / f"phase_{phase}" / f"part_{chunk_id:06d}_offset_{offset:09d}.parquet"
    if raw_path.exists() and parquet_path.exists() and raw_path.stat().st_size > 0:
        try:
            df = pd.read_parquet(parquet_path)
            return {
                "status": "ALREADY_PRESENT",
                "offset": offset,
                "limit": limit,
                "rows": int(len(df)),
                "raw_path": str(raw_path),
                "normalized_path": str(parquet_path),
                "raw_sha256": sha256_file(raw_path),
                "normalized_sha256": sha256_file(parquet_path),
            }
        except Exception:
            pass
    params: dict[str, str] = {"$limit": str(limit), "$offset": str(offset)}
    if where:
        params["$where"] = where
    if order:
        params["$order"] = order
    fields = selected_fields(source)
    if fields:
        params["$select"] = ",".join(fields)
    retries = 4
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            payload, err = get_json(session, soda_url(source), params, timeout=90)
            if err:
                raise RuntimeError(err)
            rows = payload if isinstance(payload, list) else []
            write_raw_jsonl_gz(raw_path, rows)
            parquet_path.parent.mkdir(parents=True, exist_ok=True)
            df = pd.DataFrame(rows)
            df.to_parquet(parquet_path, index=False)
            return {
                "status": "DOWNLOADED",
                "offset": offset,
                "limit": limit,
                "rows": int(len(df)),
                "raw_path": str(raw_path),
                "normalized_path": str(parquet_path),
                "raw_sha256": sha256_file(raw_path),
                "normalized_sha256": sha256_file(parquet_path),
            }
        except Exception as exc:  # noqa: BLE001
            last_error = repr(exc)
            time.sleep(min(30, 2 * attempt))
    return {"status": "DOWNLOAD_FAILED", "offset": offset, "limit": limit, "rows": 0, "error": last_error}


def run_phase0(root: Path, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    profiles = {}
    for source in sources:
        state, reason = source_state(source)
        profile = profile_from_source(source, state, reason)
        profiles[source["key"]] = profile
        write_json(root / "profiles" / f"{source['key']}.profile.json", profile)
        manifest = load_manifest(root, source["key"])
        manifest.update(
            {
                "source_key": source["key"],
                "name": source.get("name"),
                "dataset_id": source.get("dataset_id"),
                "domain": source.get("domain"),
                "api_url": soda_url(source) if source.get("source_type") == "socrata" and source.get("domain") else source.get("url"),
                "flow_candidates": source.get("flows"),
                "priority": source.get("priority"),
                "source_state": state,
                "state_reason": reason,
                "privacy_class": profile["privacy_class"],
                "boundary_class": profile["boundary_class"],
                "schema_hash": profile["schema_hash"],
                "phases": manifest.get("phases", {}),
                "chunks": manifest.get("chunks", []),
                "updated_utc": utc_now(),
            }
        )
        manifest["phases"]["0"] = {
            "status": "PREFLIGHT_COMPLETE",
            "row_count_total": source.get("row_count"),
            "column_count": source.get("column_count"),
            "date_fields": source.get("date_fields") or [],
            "geo_fields": source.get("geo_fields") or [],
            "source_state": state,
            "state_reason": reason,
            "updated_utc": utc_now(),
        }
        save_manifest(root, manifest)
        rows.append(manifest)
    write_json(root / "NYC_ALLFLOWS_SCHEMA_PROFILES.json", profiles)
    return rows


def run_phase1(root: Path, sources: list[dict[str, Any]], chunk_size: int = 50_000, cap: int = 1_000_000) -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    summaries = []
    for source in sources:
        key = source["key"]
        state, reason = source_state(source)
        manifest = load_manifest(root, key)
        profile = read_json(root / "profiles" / f"{key}.profile.json", profile_from_source(source, state, reason))
        if state != "SODA2_BULK_READY":
            phase = {
                "status": state,
                "status_reason": reason,
                "target_cap": 0,
                "landed_rows": 0,
                "updated_utc": utc_now(),
            }
            manifest.setdefault("phases", {})["1"] = phase
            save_manifest(root, manifest)
            summaries.append({"source_key": key, **phase})
            continue
        where, order, window_reason = phase_window(source, 1)
        full_count = source.get("row_count")
        window_count, window_count_error = count_soda(session, source, where)
        effective_total = window_count if window_count is not None else full_count
        if effective_total is None:
            phase = {
                "status": "COUNT_FAILED",
                "status_reason": window_count_error or "no count available",
                "target_cap": cap,
                "landed_rows": 0,
                "updated_utc": utc_now(),
            }
            manifest.setdefault("phases", {})["1"] = phase
            save_manifest(root, manifest)
            summaries.append({"source_key": key, **phase})
            continue
        target = min(int(effective_total), cap)
        print(f"[{utc_now()}] phase1 {key}: target={target:,} total={full_count} window={window_count} where={where or '-'}", flush=True)
        landed = 0
        bytes_raw = 0
        bytes_parquet = 0
        chunk_records = []
        failed = False
        for offset in range(0, target, chunk_size):
            limit = min(chunk_size, target - offset)
            chunk = land_chunk(session, root, source, 1, offset, limit, where, order)
            chunk_records.append(chunk)
            if chunk.get("status") == "DOWNLOAD_FAILED":
                failed = True
                break
            landed += int(chunk.get("rows") or 0)
            if chunk.get("raw_path") and Path(chunk["raw_path"]).exists():
                bytes_raw += Path(chunk["raw_path"]).stat().st_size
            if chunk.get("normalized_path") and Path(chunk["normalized_path"]).exists():
                bytes_parquet += Path(chunk["normalized_path"]).stat().st_size
            manifest["chunks"] = [c for c in manifest.get("chunks", []) if not (c.get("phase") == 1 and c.get("offset") == offset)]
            manifest["chunks"].append({"phase": 1, **chunk})
            manifest.setdefault("phases", {})["1"] = {
                "status": "IN_PROGRESS",
                "query_filters": {"where": where, "order": order},
                "window_reason": window_reason,
                "full_source_count": full_count,
                "selected_window_count": window_count,
                "selected_window_count_error": window_count_error,
                "target_cap": target,
                "landed_rows": landed,
                "chunk_count": len([c for c in chunk_records if c.get("status") != "DOWNLOAD_FAILED"]),
                "updated_utc": utc_now(),
            }
            save_manifest(root, manifest)
            if landed and landed % 250_000 == 0:
                print(f"[{utc_now()}] phase1 {key}: {landed:,}/{target:,}", flush=True)
            if int(chunk.get("rows") or 0) < limit:
                break
        status = classify_status(failed, full_count, window_count, target, landed, where)
        phase = {
            "status": status,
            "query_filters": {"where": where, "order": order},
            "window_reason": window_reason,
            "full_source_count": full_count,
            "selected_window_count": window_count,
            "selected_window_count_error": window_count_error,
            "target_cap": target,
            "landed_rows": landed,
            "chunk_count": len([c for c in chunk_records if c.get("status") != "DOWNLOAD_FAILED"]),
            "first_last_date": first_last_date(root, key, 1, profile.get("date_fields") or []),
            "bytes_raw": bytes_raw,
            "bytes_normalized": bytes_parquet,
            "updated_utc": utc_now(),
        }
        manifest.setdefault("phases", {})["1"] = phase
        save_manifest(root, manifest)
        summaries.append({"source_key": key, **phase})
        print(f"[{utc_now()}] phase1 done {key}: {status} rows={landed:,}", flush=True)
    return summaries


def classify_status(failed: bool, full_count: int | None, window_count: int | None, target: int, landed: int, where: str | None) -> str:
    if failed:
        return "DOWNLOAD_FAILED_PARTIAL"
    total = window_count if window_count is not None else full_count
    if total is not None and landed >= int(total):
        return "WINDOWED_COMPLETE" if where else "FULL_COMPLETE"
    if landed >= target:
        return "CAPPED_BREADTH"
    if landed > 0:
        return "PARTIAL_BREADTH"
    return "METADATA_ONLY"


def first_last_date(root: Path, key: str, phase: int, date_fields: list[str]) -> dict[str, Any]:
    if not date_fields:
        return {}
    field = date_fields[0]
    values = []
    for path in sorted((root / "data" / "normalized" / key / f"phase_{phase}").glob("*.parquet"))[:3]:
        try:
            df = pd.read_parquet(path, columns=[field])
            values.extend([v for v in df[field].dropna().astype(str).tolist() if v])
        except Exception:
            continue
    for path in sorted((root / "data" / "normalized" / key / f"phase_{phase}").glob("*.parquet"))[-3:]:
        try:
            df = pd.read_parquet(path, columns=[field])
            values.extend([v for v in df[field].dropna().astype(str).tolist() if v])
        except Exception:
            continue
    if not values:
        return {"field": field}
    return {"field": field, "min_observed": min(values), "max_observed": max(values)}


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(clean(row))


def collect_manifests(root: Path) -> list[dict[str, Any]]:
    manifests = []
    for path in sorted((root / "manifests").glob("*.manifest.json")):
        manifests.append(read_json(path, {}))
    return manifests


def write_reports(root: Path, sources: list[dict[str, Any]], acceptance_status: str) -> None:
    manifests = collect_manifests(root)
    source_rows = []
    by_flow: dict[int, int] = {flow: 0 for flow in range(1, 8)}
    by_phase: dict[str, int] = {}
    for manifest in manifests:
        phases = manifest.get("phases", {})
        phase1 = phases.get("1", {})
        landed = int(phase1.get("landed_rows") or 0)
        for flow in manifest.get("flow_candidates") or []:
            by_flow[int(flow)] += landed
        for phase_id, phase in phases.items():
            by_phase[phase_id] = by_phase.get(phase_id, 0) + int(phase.get("landed_rows") or 0)
        source_rows.append(
            {
                "source_key": manifest.get("source_key"),
                "priority": manifest.get("priority"),
                "flows": ",".join(str(f) for f in manifest.get("flow_candidates") or []),
                "source_state": manifest.get("source_state"),
                "phase1_status": phase1.get("status"),
                "full_source_count": phase1.get("full_source_count") or (phases.get("0") or {}).get("row_count_total"),
                "selected_window_count": phase1.get("selected_window_count"),
                "target_cap": phase1.get("target_cap"),
                "landed_rows": landed,
                "chunk_count": phase1.get("chunk_count"),
                "privacy_class": manifest.get("privacy_class"),
                "boundary_class": manifest.get("boundary_class"),
            }
        )
    write_json(root / "NYC_ALLFLOWS_SOURCE_LEDGER.json", {"task": TASK, "generated_utc": utc_now(), "sources": sources})
    write_json(root / "NYC_ALLFLOWS_PHASE_MANIFEST.json", {"task": TASK, "generated_utc": utc_now(), "acceptance_status": acceptance_status, "sources": manifests})
    write_csv(
        root / "NYC_ALLFLOWS_DATASET_STATUS.csv",
        source_rows,
        ["source_key", "priority", "flows", "source_state", "phase1_status", "full_source_count", "selected_window_count", "target_cap", "landed_rows", "chunk_count", "privacy_class", "boundary_class"],
    )
    flow_rows = [{"phase": phase, "rows_landed": rows} for phase, rows in sorted(by_phase.items())]
    flow_rows.extend({"phase": f"flow_{flow}", "rows_landed": rows} for flow, rows in sorted(by_flow.items()))
    write_csv(root / "NYC_ALLFLOWS_COUNTS_BY_PHASE.csv", flow_rows, ["phase", "rows_landed"])
    write_static_docs(root, source_rows, by_flow, acceptance_status)
    write_hashes(root)


def write_static_docs(root: Path, source_rows: list[dict[str, Any]], by_flow: dict[int, int], status: str) -> None:
    total_rows = sum(int(row.get("landed_rows") or 0) for row in source_rows)
    readme = f"""# {TASK}

Status: `{status}`

This is a new addendum/data-expansion run. It does not mutate PV1/D19-D22 snapshots.

Rows landed in this output root: `{total_rows:,}`

Core rule: breadth first, then depth. Phase 0 records metadata/profile state for every source. Phase 1 lands up to 1M rows per feasible tabular source, with bounded windows for very large operational sources.
"""
    (root / "README.md").write_text(readme, encoding="utf-8")
    plan = """# NYC All-Flows Landing Plan

Phase 0: preflight metadata/count/schema/profile for every source.

Phase 1: breadth pass, up to 1M rows per feasible tabular source.

Phase 2: priority depth pass, 5M cap, P0 then P1 then P2/P3.

Phase 3+: repeated +5M cap loops with round-robin fairness.
"""
    (root / "NYC_ALLFLOWS_LANDING_PLAN.md").write_text(plan, encoding="utf-8")
    privacy = """# Privacy And Boundary

- EMS and Fire dispatch: aggregate/replay/context only; no dispatch recommendation, no emergency advice, no public-safety command.
- MVC persons: privacy-safe selected fields only; no individual inference.
- Restaurant inspections and health-related sources: no health determination.
- DOB, violations, HPD, enforcement datasets: evidence context only; no enforcement recommendation.
- Traffic and transit sources: no traffic-control command.
- All data is review/context only unless separately certified by an accepted flow gate.
"""
    (root / "NYC_ALLFLOWS_PRIVACY_BOUNDARY.md").write_text(privacy, encoding="utf-8")
    limitations = """# Limitations

- Phase 1 is a breadth pass, not final entity resolution.
- Large sources are capped or windowed where needed.
- 3-D Building Model and 1-foot DEM require tile/file strategy rather than SODA2 bulk.
- Direct MTA/PANYNJ web endpoints are represented as metadata/snapshot strategy unless specifically landed by a later direct-file worker.
- No operational, emergency, enforcement, health, routing, traffic-control, utility-control, aircraft, vessel, or port command is produced.
"""
    (root / "NYC_ALLFLOWS_LIMITATIONS.md").write_text(limitations, encoding="utf-8")
    lines = [
        "# NYC All-Flows Acceptance Report",
        "",
        f"Status: `{status}`",
        "",
        f"Total landed rows: `{total_rows:,}`",
        "",
        "## Rows By Flow",
        "",
    ]
    for flow, rows in sorted(by_flow.items()):
        lines.append(f"- Flow {flow}: `{rows:,}`")
    lines.extend(
        [
            "",
            "## Recommended Next Gates",
            "",
            "- `NYC-F4X-D2`",
            "- `NYC-F5X-D2`",
            "- `NYC-F2X-F3X-HARDENING-D2`",
            "- `NYC-F7X-D2`",
            "",
            "## Dataset Status",
            "",
            "| Source | Priority | Phase 1 status | Rows landed |",
            "|---|---|---|---:|",
        ]
    )
    for row in sorted(source_rows, key=lambda r: (r.get("priority") or "P9", r.get("source_key") or "")):
        lines.append(f"| {row.get('source_key')} | {row.get('priority')} | {row.get('phase1_status')} | {int(row.get('landed_rows') or 0):,} |")
    (root / "NYC_ALLFLOWS_ACCEPTANCE_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_hashes(root: Path) -> None:
    lines = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "NYC_ALLFLOWS_HASHES.sha256":
            lines.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    (root / "NYC_ALLFLOWS_HASHES.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def acceptance_status(root: Path, requested_phase: int) -> str:
    manifests = collect_manifests(root)
    if requested_phase == 0:
        return "PASS_PHASE_0_PREFLIGHT"
    failures = []
    limitations = []
    for manifest in manifests:
        phase = (manifest.get("phases") or {}).get(str(requested_phase), {})
        status = phase.get("status")
        if status == "DOWNLOAD_FAILED_PARTIAL" or status == "COUNT_FAILED":
            failures.append(manifest.get("source_key"))
        elif status not in {"FULL_COMPLETE", "WINDOWED_COMPLETE", "CAPPED_BREADTH"}:
            limitations.append(manifest.get("source_key"))
    if failures:
        return "PASS_WITH_LIMITATIONS"
    if requested_phase == 1:
        return "PASS_PHASE_1_BREADTH" if not limitations else "PASS_WITH_LIMITATIONS"
    return "PASS_WITH_LIMITATIONS"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan", default=str(DEFAULT_SCAN))
    parser.add_argument("--output-root", default=str(DEFAULT_OUT))
    parser.add_argument("--phase", type=int, choices=[0, 1], default=1)
    parser.add_argument("--chunk-size", type=int, default=50_000)
    parser.add_argument("--cap", type=int, default=1_000_000)
    args = parser.parse_args()

    root = Path(args.output_root)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    sources = load_sources(Path(args.scan))
    root.mkdir(parents=True, exist_ok=True)

    # Preserve the script used for auditability.
    script_target = root / "scripts" / Path(__file__).name
    script_target.write_text(Path(__file__).read_text(encoding="utf-8"), encoding="utf-8")

    print(f"{TASK}: sources={len(sources)} phase={args.phase}", flush=True)
    run_phase0(root, sources)
    if args.phase >= 1:
        run_phase1(root, sources, chunk_size=args.chunk_size, cap=args.cap)
    status = acceptance_status(root, args.phase)
    write_reports(root, sources, status)
    print(f"{TASK}: {status}", flush=True)
    print(f"Output: {root.resolve()}", flush=True)


if __name__ == "__main__":
    main()

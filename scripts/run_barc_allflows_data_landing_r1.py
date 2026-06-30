#!/usr/bin/env python3
"""BARC-ALLFLOWS-DATA-LANDING-R1.

Stop-safe Barcelona all-flows source landing pipeline.

This is data landing only. It reads the refreshed Barcelona 7-flow scan,
creates a normalized source ledger, and lands feasible data with a cap ladder.
It does not mutate PV1/platform state and does not rerun Barcelona gates.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import time
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import pandas as pd
import requests


TASK = "BARC-ALLFLOWS-DATA-LANDING-R1"
DEFAULT_SCAN = Path("outputs/barc_7flow_source_shape_scan/BARC_7FLOW_SOURCE_SHAPE_SCAN.json")
DEFAULT_OUT = Path("outputs/barc_allflows_data_landing_r1")
USER_AGENT = "TXR-CityBrain-BARC-AllFlows-R1/1.0"
CHUNK_SIZE_DEFAULT = 50_000
PHASE_CAPS = {
    0: 0,
    1: 1_000_000,
    2: 5_000_000,
    3: 10_000_000,
    4: 15_000_000,
    5: 20_000_000,
    6: 25_000_000,
}
PHASE_STATUS = {
    0: "PASS_PHASE_0_PREFLIGHT",
    1: "PASS_PHASE_1_BREADTH",
    2: "PASS_PHASE_2_5M_DEPTH",
    3: "PASS_CAP_LOOP_10M",
    4: "PASS_CAP_LOOP_15M",
    5: "PASS_CAP_LOOP_20M",
    6: "PASS_CAP_LOOP_25M",
}
SENSITIVE_QUERY_KEYS = {"app_key", "appkey", "api_key", "apikey", "key", "token", "access_token", "secret", "password"}
HIGH_PRIORITY_ORDER = [
    "iris",
    "traffic_itineraries",
    "traffic_sections",
    "traffic_sections_by_itinerary",
    "traffic_trams",
    "bicing_gbfs",
    "air_quality_detail",
    "air_quality_stations",
    "noise_monitor_installations",
    "facilities_transport",
    "boundaries_districts",
    "boundaries_admin_units",
    "address_table",
    "traffic_accidents",
    "electricity_consumption",
    "mobility_counters_equipment",
    "mobility_counters_detail",
    "tmb_static_gtfs",
    "sentilo_connecta",
    "meteorological_readings",
    "air_quality_pollutants",
    "economic_activity_premises",
    "traffic_accident_vehicles",
    "piezometer_readings",
    "climate_shelters",
    "land_plots",
    "traffic_accident_people",
    "noise_population_exposure",
    "meteorological_stations",
    "traffic_accident_causes",
    "noise_monitor_readings",
    "facilities_service_companies",
    "rainfall_history",
    "traffic_incidence_notices",
    "piezometer_inventory",
    "urban_planning_sectors",
    "port_ships_today",
]

BOUNDARY_LINES = [
    "BARC-ALLFLOWS-DATA-LANDING-R1 is data landing only.",
    "This task does not change platform live/generated state.",
    "This task does not mutate PV1 D19-D22 or PV1-SNAPSHOT-ADDENDUM-R2.",
    "This task does not rerun BARC-CORE-D3, BARC-F7-D3, or BARC-F7 review-flow acceptance.",
    "No new Barcelona flow is accepted by this data landing output.",
    "No consumption prep, final flow mart, or EvidenceBundle consumption product is created.",
    "No dispatch, enforcement, public-safety command, traffic-control command, transit-control command, port-control command, health determination, or certified affected-building claim is made.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def safe_key(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in value).strip("_") or "source"


def safe_url(url: str | None) -> str | None:
    if not url:
        return url
    parsed = urlparse(url)
    query = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        query.append((key, "REDACTED" if key.lower() in SENSITIVE_QUERY_KEYS else value))
    return urlunparse(parsed._replace(query=urlencode(query)))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def schema_hash(fields: list[Any]) -> str:
    payload = json.dumps(clean(fields), sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def resolve(root: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def ckan_action_base(api_url: str | None, catalog: str) -> str:
    if api_url and "/api/3/action/" in api_url:
        return api_url.split("/api/3/action/", 1)[0] + "/api/3/action"
    if catalog == "port":
        return "https://opendata.portdebarcelona.cat/en/api/3/action"
    return "https://opendata-ajuntament.barcelona.cat/data/api/3/action"


def privacy_boundary(record: dict[str, Any]) -> tuple[str, str]:
    key = record.get("key", "")
    text = " ".join([key, record.get("title", ""), record.get("use", "")]).lower()
    if key == "traffic_accident_people":
        return "PRIVACY_SENSITIVE_AGGREGATION_ONLY", "privacy-sensitive aggregation only; no individual inference"
    if key.startswith("traffic_") or key in {"bicing_gbfs", "mobility_counters_equipment", "mobility_counters_detail"}:
        return "MOBILITY_CONTEXT_ONLY", "traffic/mobility context only; no traffic-control command"
    if key.startswith("tmb_") or key in {"amb_gtfs_rt", "tram_opendata"}:
        return "TRANSIT_CONTEXT_ONLY", "transit context only; no transit-control command"
    if key.startswith("port_"):
        return "PORT_CONTEXT_ONLY", "port/logistics context only; no port-control or vessel-control command"
    if any(token in text for token in ["air", "noise", "meteorological", "piezometer", "rainfall", "climate", "green"]):
        return "ENVIRONMENT_CONTEXT_ONLY", "environmental context only; no health determination"
    if "cadastre" in text or key in {"address_table", "land_plots"}:
        return "IDENTITY_GEOGRAPHY_CONTEXT_ONLY", "identity/geography context only; no legal/ownership/compliance conclusion"
    if key == "iris":
        return "CIVIC_REVIEW_CONTEXT_ONLY", "IRIS civic records are review/context only; no personal or sensitive case inference"
    return "REVIEW_CONTEXT_ONLY", record.get("boundary") or "review/context only"


def infer_fields(record: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    fields = [str(c).split(":", 1)[0] for c in record.get("columns") or []]
    lower = {field.lower(): field for field in fields}
    date_fields = [field for low, field in lower.items() if any(tok in low for tok in ["date", "data", "dia", "timestamp", "eta", "etd", "mes", "any"])]
    geo_fields = [field for low, field in lower.items() if any(tok in low for tok in ["lat", "lon", "longitud", "geometry", "geometria", "coordenada", "geo"])]
    id_fields = [field for low, field in lower.items() if low == "_id" or low.endswith("_id") or "id" in low or "codi" in low or "code" in low]
    return date_fields[:12], geo_fields[:12], id_fields[:20]


def classify_source(record: dict[str, Any]) -> tuple[str, str]:
    preferred = record.get("preferred_api")
    key = record.get("key")
    if preferred == "CKAN_DATASTORE_API":
        return ("PORT_CKAN_DATASTORE_READY" if record.get("catalog") == "port" else "CKAN_DATASTORE_READY"), "CKAN DataStore endpoint/resource IDs available"
    if preferred == "CKAN_PACKAGE_RESOURCE_DOWNLOAD":
        return "CKAN_PACKAGE_RESOURCE_DOWNLOAD_READY", "CKAN package file resources available"
    if preferred == "GBFS_JSON":
        return "GBFS_READY", "GBFS JSON feed available"
    if preferred == "TMB_REST_OR_STATIC_GTFS":
        if key == "tmb_static_gtfs":
            return "TMB_STATIC_GTFS_READY", "static GTFS can be registered from existing landed ZIP or env-backed TMB API"
        return "KEY_BLOCKED", "TMB REST credentials are required and must be provided via environment"
    if preferred == "SENTILO_CONNECTA_API":
        return "SENTILO_CONNECTA_READY", "Sentilo/Connecta public catalogue endpoints available; observations require validation"
    if preferred and preferred.endswith("_DIRECT_OR_NATIVE_API"):
        if key == "amb_gtfs_rt":
            return "DIRECT_METADATA_ONLY", "direct endpoint is metadata/API-boundary only in this pass"
        return "DIRECT_NATIVE_READY", "direct/native endpoint available"
    return "SKIP_WITH_REASON", "no usable landing endpoint classified"


def ledger_from_scan(scan: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    records = []
    for row in scan.get("records", []):
        date_fields, geo_fields, id_fields = infer_fields(row)
        state, reason = classify_source(row)
        privacy_class, boundary_class = privacy_boundary(row)
        probe = row.get("probe") or {}
        resource_ids = [p.get("resource_id") for p in probe.get("resource_probes") or [] if p.get("resource_id")]
        records.append(
            {
                "source_key": row["key"],
                "source_name": row.get("title"),
                "priority": row.get("priority_score"),
                "priority_band": row.get("priority_band"),
                "flows": row.get("flows", []),
                "soda2_status": row.get("soda2_status"),
                "preferred_api": row.get("preferred_api"),
                "api_priority_reason": row.get("api_priority_reason"),
                "count_primary_total": row.get("latest_or_primary_total"),
                "shape_fields": row.get("columns") or [],
                "use": row.get("use"),
                "boundary": row.get("boundary"),
                "next_action": row.get("recommended_next_action"),
                "package_id": row.get("package_id"),
                "resource_ids": resource_ids,
                "url": safe_url(row.get("api_url")),
                "date_fields": date_fields,
                "geo_fields": geo_fields,
                "id_join_fields": list(dict.fromkeys((row.get("join_keys") or []) + id_fields)),
                "credentials_required": state in {"KEY_REQUIRED", "KEY_BLOCKED"},
                "expected_download_mode": state,
                "classification_reason": reason,
                "privacy_class": privacy_class,
                "boundary_class": boundary_class,
                "scan_record": row,
            }
        )
    records.extend(cadastre_ledger(root))
    priority_index = {key: idx for idx, key in enumerate(HIGH_PRIORITY_ORDER)}
    records.sort(key=lambda r: (0 if r["source_key"] in priority_index else 1, priority_index.get(r["source_key"], 999), -(int(r.get("priority") or 0)), r["source_key"]))
    return records


def cadastre_ledger(root: Path) -> list[dict[str, Any]]:
    manifest_path = root / "outputs" / "barc_cadastre_recovery_d1" / "BARC_CADASTRE_RECOVERY_D1_MANIFEST.json"
    manifest = read_json(manifest_path, {})
    out = []
    for item in manifest.get("sources", []) if isinstance(manifest, dict) else []:
        out.append(
            {
                "source_key": item.get("acceptance_key") or item.get("source_key"),
                "source_name": item.get("title"),
                "priority": 90,
                "priority_band": "HIGH",
                "flows": ["F2", "F5"],
                "soda2_status": "NOT_APPLICABLE_CADASTRE_ATOM",
                "preferred_api": "CADASTRE_ATOM_ZIP_EXISTING_RECOVERY",
                "api_priority_reason": "Existing recovered Catastro INSPIRE ATOM ZIP registered without re-download.",
                "count_primary_total": item.get("zip_inventory", {}).get("feature_counts", {}).get(item.get("feature_localname")),
                "shape_fields": [item.get("feature_localname")],
                "use": "Cadastre parcel/building/address identity-geography context.",
                "boundary": "identity/geography context only; no ownership, legal, planning, enforcement, or compliance conclusion",
                "next_action": "Register existing recovery; do not re-download unless hash verification fails.",
                "package_id": "08900-BARCELONA",
                "resource_ids": [],
                "url": safe_url(item.get("direct_zip_url")),
                "date_fields": [],
                "geo_fields": ["GML geometry"],
                "id_join_fields": ["cadastre_reference_candidate"],
                "credentials_required": False,
                "expected_download_mode": "CADASTRE_EXISTING_RECOVERY",
                "classification_reason": "registered from BARC-CADASTRE-RECOVERY-D1",
                "privacy_class": item.get("privacy_risk") or "LOW",
                "boundary_class": "IDENTITY_GEOGRAPHY_CONTEXT_ONLY",
                "cadastre_record": item,
            }
        )
    return out


def output_dirs(out: Path, key: str, phase: int) -> dict[str, Path]:
    return {
        "raw": out / "data" / "raw" / key / f"phase_{phase}",
        "normalized": out / "data" / "normalized" / key / f"phase_{phase}",
        "files": out / "files" / key,
        "manifest": out / "manifests" / f"{key}.manifest.json",
        "profile": out / "profiles" / f"{key}.profile.json",
    }


def existing_manifest(out: Path, key: str) -> dict[str, Any]:
    return read_json(out / "manifests" / f"{key}.manifest.json", {})


def envelope_frame(df: pd.DataFrame, ledger: dict[str, Any], resource_id: str | None = None) -> pd.DataFrame:
    now = utc_now()
    key = ledger["source_key"]
    id_fields = [field for field in ledger.get("id_join_fields", []) if field in df.columns]
    event_fields = [field for field in ledger.get("date_fields", []) if field in df.columns]
    geo_fields = [field for field in ledger.get("geo_fields", []) if field in df.columns]
    lat_field = next((f for f in geo_fields if "lat" in f.lower()), None)
    lon_field = next((f for f in geo_fields if "lon" in f.lower() or "longitud" in f.lower()), None)
    record_id = df[id_fields[0]].astype(str) if id_fields else pd.Series([None] * len(df))
    out = df.copy()
    out.insert(0, "source_boundary_class", ledger.get("boundary_class"))
    out.insert(0, "source_privacy_class", ledger.get("privacy_class"))
    out.insert(0, "source_geometry", None)
    out.insert(0, "source_lon", df[lon_field] if lon_field else None)
    out.insert(0, "source_lat", df[lat_field] if lat_field else None)
    out.insert(0, "source_updated_time", None)
    out.insert(0, "source_event_time", df[event_fields[0]] if event_fields else None)
    out.insert(0, "source_ingested_at", now)
    out.insert(0, "source_record_id", record_id)
    out.insert(0, "source_resource_id", resource_id)
    out.insert(0, "source_dataset_id", ledger.get("package_id"))
    out.insert(0, "source_system", ledger.get("preferred_api"))
    out.insert(0, "source_key", key)
    out.insert(0, "city", "BARC")
    return out


def write_chunk(df: pd.DataFrame, raw_path: Path, norm_path: Path, ledger: dict[str, Any], resource_id: str | None) -> dict[str, Any]:
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    norm_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_json(raw_path, orient="records", lines=True, force_ascii=True)
    normalized_df = df.astype(str)
    env = envelope_frame(normalized_df, ledger, resource_id)
    env.to_parquet(norm_path, index=False)
    return {
        "raw_path": str(raw_path),
        "normalized_path": str(norm_path),
        "rows": len(df),
        "raw_sha256": sha256_file(raw_path),
        "normalized_sha256": sha256_file(norm_path),
        "bytes": raw_path.stat().st_size + norm_path.stat().st_size,
    }


def datastore_url(ledger: dict[str, Any], resource_id: str, limit: int, offset: int) -> str:
    base = ckan_action_base(ledger.get("url"), "port" if ledger.get("preferred_api") == "PORT_CKAN_DATASTORE_READY" else "bcn")
    return f"{base}/datastore_search?{urlencode({'resource_id': resource_id, 'limit': limit, 'offset': offset})}"


def fetch_datastore(session: requests.Session, ledger: dict[str, Any], resource_id: str, limit: int, offset: int, timeout: int) -> tuple[list[dict[str, Any]], int | None, list[dict[str, Any]], str | None]:
    url = datastore_url(ledger, resource_id, limit, offset)
    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        result = payload.get("result", {})
        return result.get("records") or [], result.get("total"), result.get("fields") or [], None
    except Exception as exc:  # noqa: BLE001
        return [], None, [], repr(exc)


def source_resource_probes(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    return ledger.get("scan_record", {}).get("probe", {}).get("resource_probes") or []


def selected_resources_for_files(ledger: dict[str, Any], max_files: int) -> list[dict[str, Any]]:
    resources = ledger.get("scan_record", {}).get("probe", {}).get("resources") or []
    downloadable = []
    skip_formats = {"WMS"}
    for item in resources:
        fmt = str(item.get("format") or "").upper()
        if fmt in skip_formats:
            continue
        if not item.get("url"):
            continue
        downloadable.append(item)
    preferred = sorted(downloadable, key=lambda r: (str(r.get("format") or "").upper() not in {"CSV", "JSON", "GEOJSON", "SHP", "ZIP"}, str(r.get("name") or "")))
    return preferred[:max_files]


def download_file(session: requests.Session, url: str, dest: Path, timeout: int, max_bytes: int | None = None) -> tuple[bool, str | None]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return True, None
    temp = dest.with_name(dest.name + ".part")
    try:
        with session.get(url, stream=True, timeout=(timeout, max(timeout * 10, 120))) as response:
            response.raise_for_status()
            total = 0
            with temp.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if max_bytes and total > max_bytes:
                        raise RuntimeError(f"file exceeded max_bytes={max_bytes}")
                    handle.write(chunk)
        temp.replace(dest)
        return True, None
    except Exception as exc:  # noqa: BLE001
        if temp.exists():
            temp.unlink()
        return False, repr(exc)


def profile_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"field_count": 0, "fields": []}
    keys = sorted({key for row in records[:200] for key in row.keys()})
    return {"field_count": len(keys), "fields": keys}


def land_ckan_datastore(session: requests.Session, out: Path, ledger: dict[str, Any], phase: int, cap: int, chunk_size: int, timeout: int) -> dict[str, Any]:
    key = ledger["source_key"]
    dirs = output_dirs(out, key, phase)
    previous = existing_manifest(out, key)
    already = int(previous.get("landed_rows") or 0)
    if already >= cap and previous.get("status") in {"FULL_COMPLETE", "WINDOWED_COMPLETE", "CAP_PARTIAL"}:
        return previous
    probes = [p for p in source_resource_probes(ledger) if p.get("resource_id")]
    if not probes:
        return manifest_base(ledger, phase, cap, "METADATA_ONLY", "No DataStore resource probes available.")
    landed = already
    chunks = list(previous.get("chunks") or [])
    errors = list(previous.get("error_history") or [])
    all_fields: list[dict[str, Any]] = []
    selected_total = 0
    for probe in probes:
        if landed >= cap:
            break
        rid = str(probe["resource_id"])
        total = probe.get("total")
        if isinstance(total, int):
            selected_total += total
        offset = 0
        while landed < cap:
            remaining = min(chunk_size, cap - landed)
            chunk_name = f"{safe_key(rid)}_offset_{offset:09d}_limit_{remaining:06d}"
            raw_path = dirs["raw"] / f"{chunk_name}.jsonl"
            norm_path = dirs["normalized"] / f"{chunk_name}.parquet"
            if raw_path.exists() and norm_path.exists():
                try:
                    rows_existing = sum(1 for _ in raw_path.open("r", encoding="utf-8", errors="ignore"))
                except Exception:
                    rows_existing = 0
                if rows_existing:
                    landed += rows_existing
                    offset += rows_existing
                    continue
            records, live_total, fields, err = fetch_datastore(session, ledger, rid, remaining, offset, timeout)
            if fields:
                all_fields = fields
            if err:
                errors.append({"resource_id": rid, "offset": offset, "error": err})
                break
            if not records:
                break
            df = pd.DataFrame(records)
            chunk = write_chunk(df, raw_path, norm_path, ledger, rid)
            chunk.update({"resource_id": rid, "offset": offset, "phase": phase})
            chunks.append(chunk)
            rows = len(df)
            landed += rows
            offset += rows
            if rows < remaining:
                break
            time.sleep(0.02)
    total_for_status = selected_total or ledger.get("count_primary_total")
    if isinstance(total_for_status, int) and landed >= total_for_status and not errors:
        status = "FULL_COMPLETE" if len(probes) >= int(ledger.get("scan_record", {}).get("probe", {}).get("datastore_resource_count") or len(probes)) else "WINDOWED_COMPLETE"
    elif landed >= cap:
        status = "CAP_PARTIAL"
    elif landed > 0 and errors:
        status = "CAP_PARTIAL"
    elif landed > 0:
        status = "WINDOWED_COMPLETE"
    else:
        status = "BLOCKED_REMOTE" if errors else "METADATA_ONLY"
    fields_for_schema = all_fields or [{"id": f.split(":", 1)[0], "type": f.split(":", 1)[1] if ":" in f else ""} for f in ledger.get("shape_fields", [])]
    return finalize_manifest(ledger, phase, cap, status, chunks, fields_for_schema, errors, source_total_count=total_for_status)


def land_file_source(session: requests.Session, out: Path, ledger: dict[str, Any], phase: int, cap: int, timeout: int, max_files: int, max_file_bytes: int) -> dict[str, Any]:
    key = ledger["source_key"]
    dirs = output_dirs(out, key, phase)
    previous = existing_manifest(out, key)
    if previous.get("status") in {"FILE_COMPLETE", "FULL_COMPLETE", "WINDOWED_COMPLETE"} and int(previous.get("phase") or 0) >= phase:
        return previous
    files = selected_resources_for_files(ledger, max_files)
    if not files:
        return manifest_base(ledger, phase, cap, "METADATA_ONLY", "No directly downloadable non-WMS file resources selected.")
    landed_files = []
    errors = []
    fields: list[Any] = ledger.get("shape_fields") or []
    for item in files:
        url = str(item.get("url") or "")
        suffix = Path(urlparse(url).path).suffix or ("." + str(item.get("format") or "bin").lower())
        dest = dirs["files"] / f"{safe_key(str(item.get('name') or item.get('id')))}{suffix}"
        ok, err = download_file(session, url, dest, timeout, max_file_bytes)
        if ok:
            rec = {"resource_id": item.get("id"), "name": item.get("name"), "format": item.get("format"), "path": str(dest), "bytes": dest.stat().st_size, "sha256": sha256_file(dest), "url": safe_url(url)}
            landed_files.append(rec)
            if dest.suffix.lower() in {".csv", ".json", ".geojson"}:
                profile = quick_file_profile(dest)
                fields = profile.get("fields") or fields
        else:
            errors.append({"resource_id": item.get("id"), "url": safe_url(url), "error": err})
    status = "FILE_COMPLETE" if landed_files and not errors else "WINDOWED_COMPLETE" if landed_files else "BLOCKED_REMOTE"
    return finalize_manifest(ledger, phase, cap, status, [], fields, errors, landed_files=landed_files)


def quick_file_profile(path: Path) -> dict[str, Any]:
    try:
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path, nrows=25)
            return {"fields": list(df.columns), "field_count": len(df.columns)}
        if path.suffix.lower() in {".json", ".geojson"}:
            payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            records = payload.get("features") if isinstance(payload, dict) else payload
            if isinstance(records, list) and records:
                first = records[0].get("properties", records[0]) if isinstance(records[0], dict) else {}
                return {"fields": sorted(first.keys()), "field_count": len(first)}
    except Exception as exc:  # noqa: BLE001
        return {"error": repr(exc)}
    return {}


def land_gbfs(session: requests.Session, out: Path, ledger: dict[str, Any], phase: int, cap: int, timeout: int) -> dict[str, Any]:
    key = ledger["source_key"]
    dirs = output_dirs(out, key, phase)
    probes = ledger.get("scan_record", {}).get("probe", {}).get("direct_probes") or []
    chunks = []
    errors = []
    fields: list[str] = []
    for probe in probes:
        url = probe.get("url")
        if not url:
            continue
        name = safe_key(Path(urlparse(url).path).name or "gbfs")
        raw_path = dirs["raw"] / f"{name}.json"
        norm_path = dirs["normalized"] / f"{name}.parquet"
        if raw_path.exists() and norm_path.exists():
            rows_existing = count_gbfs_rows(raw_path)
            chunks.append({"raw_path": str(raw_path), "normalized_path": str(norm_path), "rows": rows_existing, "raw_sha256": sha256_file(raw_path), "normalized_sha256": sha256_file(norm_path), "phase": phase})
            continue
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(response.text, encoding="utf-8")
            payload = response.json()
            data = payload.get("data", {})
            rows = []
            for value in data.values():
                if isinstance(value, list):
                    rows.extend(value)
                elif isinstance(value, dict):
                    rows.append(value)
            df = pd.DataFrame(rows)
            if not df.empty:
                fields = list(df.columns)
                norm_path.parent.mkdir(parents=True, exist_ok=True)
                envelope_frame(df.astype(str), ledger, None).to_parquet(norm_path, index=False)
            else:
                norm_path.parent.mkdir(parents=True, exist_ok=True)
                pd.DataFrame().to_parquet(norm_path, index=False)
            chunks.append({"raw_path": str(raw_path), "normalized_path": str(norm_path), "rows": len(df), "raw_sha256": sha256_file(raw_path), "normalized_sha256": sha256_file(norm_path), "phase": phase})
        except Exception as exc:  # noqa: BLE001
            errors.append({"url": safe_url(url), "error": repr(exc)})
    landed = sum(int(c.get("rows") or 0) for c in chunks)
    status = "FULL_COMPLETE" if chunks and not errors else "WINDOWED_COMPLETE" if chunks else "BLOCKED_REMOTE"
    return finalize_manifest(ledger, phase, cap, status, chunks, fields, errors, source_total_count=landed)


def count_gbfs_rows(path: Path) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        total = 0
        for value in data.values():
            if isinstance(value, list):
                total += len(value)
            elif isinstance(value, dict):
                total += 1
        return total
    except Exception:
        return 0


def tmb_credentials_present() -> bool:
    return bool((os.environ.get("TMB_APP_ID") or os.environ.get("BARCELONA_TMB_APP_ID")) and (os.environ.get("TMB_APP_KEY") or os.environ.get("BARCELONA_TMB_APP_KEY")))


def find_existing_tmb_gtfs(root: Path) -> Path | None:
    candidates = [
        root / "data_landing/xdata_d1_bulk_official_sources_v1/barcelona/raw/tmb/barc_tmb_static_gtfs.zip",
        root / "outputs/barc_d1a_targeted_source_landing_recovery/landed_samples/tmb_boundary/static_gtfs.zip",
        root / "data_landing/barc_d1a_flow4_flow7_sources_v1/landed_samples/tmb_boundary/static_gtfs.zip",
    ]
    return next((path for path in candidates if path.exists() and path.stat().st_size > 0), None)


def land_tmb_static(root: Path, session: requests.Session, out: Path, ledger: dict[str, Any], phase: int, cap: int, timeout: int) -> dict[str, Any]:
    key = ledger["source_key"]
    dirs = output_dirs(out, key, phase)
    dest = dirs["files"] / "static_gtfs.zip"
    errors = []
    source = find_existing_tmb_gtfs(root)
    if source and not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
    elif not source and tmb_credentials_present():
        app_id = os.environ.get("TMB_APP_ID") or os.environ.get("BARCELONA_TMB_APP_ID")
        app_key = os.environ.get("TMB_APP_KEY") or os.environ.get("BARCELONA_TMB_APP_KEY")
        url = "https://api.tmb.cat/v1/static/datasets/gtfs.zip?" + urlencode({"app_id": app_id, "app_key": app_key})
        ok, err = download_file(session, url, dest, timeout)
        if not ok:
            errors.append({"url": "https://api.tmb.cat/v1/static/datasets/gtfs.zip?app_id=REDACTED&app_key=REDACTED", "error": err})
    if not dest.exists():
        return manifest_base(ledger, phase, cap, "KEY_BLOCKED", "TMB static GTFS needs env credentials or existing landed ZIP.")
    tables = ["agency.txt", "routes.txt", "stops.txt", "trips.txt", "stop_times.txt", "calendar.txt", "calendar_dates.txt", "shapes.txt"]
    chunks = []
    fields = []
    total_rows = 0
    with zipfile.ZipFile(dest) as zf:
        for table in tables:
            if table not in zf.namelist():
                continue
            with zf.open(table) as handle:
                df = pd.read_csv(handle, dtype=str)
            total_rows += len(df)
            if not fields and not df.empty:
                fields = list(df.columns)
            raw_path = dirs["raw"] / f"{table}.jsonl"
            norm_path = dirs["normalized"] / f"{table}.parquet"
            chunk = write_chunk(df, raw_path, norm_path, ledger, table)
            chunk.update({"gtfs_table": table, "phase": phase})
            chunks.append(chunk)
    landed_files = [{"path": str(dest), "bytes": dest.stat().st_size, "sha256": sha256_file(dest), "source": str(source) if source else "TMB API"}]
    status = "FULL_COMPLETE" if total_rows <= cap else "CAP_PARTIAL"
    return finalize_manifest(ledger, phase, cap, status, chunks, fields, errors, source_total_count=total_rows, landed_files=landed_files)


def land_direct(session: requests.Session, out: Path, ledger: dict[str, Any], phase: int, cap: int, timeout: int) -> dict[str, Any]:
    probes = ledger.get("scan_record", {}).get("probe", {}).get("direct_probes") or []
    if ledger["source_key"] == "tmb_ibus" and not tmb_credentials_present():
        return manifest_base(ledger, phase, cap, "KEY_BLOCKED", "TMB iBus requires env credentials; no key printed or embedded.")
    if not probes:
        return manifest_base(ledger, phase, cap, "METADATA_ONLY", "No direct probes available.")
    key = ledger["source_key"]
    dirs = output_dirs(out, key, phase)
    files = []
    errors = []
    for probe in probes:
        url = probe.get("url")
        if not url:
            continue
        name = safe_key(Path(urlparse(url).path).name or "direct")
        suffix = ".html" if "html" in str(probe.get("content_type", "")) else ".json"
        dest = dirs["files"] / f"{name}{suffix}"
        ok, err = download_file(session, url, dest, timeout, max_bytes=50_000_000)
        if ok:
            files.append({"path": str(dest), "url": safe_url(url), "bytes": dest.stat().st_size, "sha256": sha256_file(dest)})
        else:
            errors.append({"url": safe_url(url), "error": err})
    status = "ENDPOINT_VALIDATION_REQUIRED" if ledger["source_key"] == "sentilo_connecta" and files else "FILE_COMPLETE" if files else "BLOCKED_REMOTE"
    return finalize_manifest(ledger, phase, cap, status, [], ledger.get("shape_fields") or [], errors, landed_files=files)


def register_cadastre(out: Path, ledger: dict[str, Any], phase: int, cap: int) -> dict[str, Any]:
    rec = ledger.get("cadastre_record") or {}
    path = Path(rec.get("path") or "")
    errors = []
    if not path.exists():
        errors.append({"error": "existing cadastre recovery file missing", "path": str(path)})
        status = "BLOCKED_REMOTE"
    elif rec.get("sha256") and sha256_file(path) != rec.get("sha256"):
        errors.append({"error": "existing cadastre recovery hash mismatch", "path": str(path)})
        status = "FAILED_WITH_REASON"
    else:
        status = "FULL_COMPLETE_EXISTING_RECOVERY"
    landed_files = [{"path": str(path), "bytes": path.stat().st_size if path.exists() else 0, "sha256": sha256_file(path) if path.exists() else None}]
    return finalize_manifest(
        ledger,
        phase,
        cap,
        status,
        [],
        ledger.get("shape_fields") or [],
        errors,
        source_total_count=ledger.get("count_primary_total"),
        landed_features=ledger.get("count_primary_total") or 0,
        landed_files=landed_files,
    )


def manifest_base(ledger: dict[str, Any], phase: int, cap: int, status: str, note: str) -> dict[str, Any]:
    return finalize_manifest(ledger, phase, cap, status, [], ledger.get("shape_fields") or [], [{"note": note}] if status in {"BLOCKED_REMOTE", "FAILED_WITH_REASON", "KEY_BLOCKED"} else [], notes=note)


def finalize_manifest(
    ledger: dict[str, Any],
    phase: int,
    cap: int,
    status: str,
    chunks: list[dict[str, Any]],
    fields: list[Any],
    errors: list[dict[str, Any]],
    source_total_count: int | None = None,
    landed_features: int = 0,
    landed_files: list[dict[str, Any]] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    landed_files = landed_files or []
    rows = sum(int(c.get("rows") or 0) for c in chunks)
    bytes_landed = sum(int(c.get("bytes") or 0) for c in chunks) + sum(int(f.get("bytes") or 0) for f in landed_files)
    field_list = fields if isinstance(fields, list) else []
    field_names = []
    for field in field_list:
        if isinstance(field, dict):
            field_names.append(field.get("id") or field.get("name"))
        else:
            field_names.append(str(field).split(":", 1)[0])
    return {
        "source_key": ledger["source_key"],
        "source_name": ledger.get("source_name"),
        "priority": ledger.get("priority"),
        "priority_band": ledger.get("priority_band"),
        "flows": ledger.get("flows", []),
        "preferred_api": ledger.get("preferred_api"),
        "source_url": safe_url(ledger.get("url")),
        "package_id": ledger.get("package_id"),
        "resource_id": ledger.get("resource_ids", [None])[0] if ledger.get("resource_ids") else None,
        "download_mode": ledger.get("expected_download_mode"),
        "phase": phase,
        "target_cap": cap,
        "source_total_count": source_total_count if source_total_count is not None else ledger.get("count_primary_total"),
        "selected_window_count": len(source_resource_probes(ledger)) or len(landed_files),
        "landed_rows": rows,
        "landed_features": landed_features,
        "landed_files": len(landed_files),
        "landed_file_records": landed_files,
        "landed_bytes": bytes_landed,
        "chunk_count": len(chunks),
        "chunks": chunks,
        "date_min": None,
        "date_max": None,
        "schema_fields": field_names,
        "schema_hash": schema_hash(field_names),
        "content_hashes": [c.get("raw_sha256") for c in chunks if c.get("raw_sha256")] + [f.get("sha256") for f in landed_files if f.get("sha256")],
        "status": status,
        "error_history": errors,
        "retry_count": len(errors),
        "privacy_class": ledger.get("privacy_class"),
        "boundary_class": ledger.get("boundary_class"),
        "notes": notes,
        "updated_at": utc_now(),
    }


def write_manifest_and_profile(out: Path, manifest: dict[str, Any]) -> None:
    key = manifest["source_key"]
    write_json(out / "manifests" / f"{key}.manifest.json", manifest)
    write_json(
        out / "profiles" / f"{key}.profile.json",
        {
            "source_key": key,
            "status": manifest.get("status"),
            "schema_fields": manifest.get("schema_fields"),
            "schema_hash": manifest.get("schema_hash"),
            "rows": manifest.get("landed_rows"),
            "features": manifest.get("landed_features"),
            "files": manifest.get("landed_files"),
            "privacy_class": manifest.get("privacy_class"),
            "boundary_class": manifest.get("boundary_class"),
        },
    )


def land_source(root: Path, session: requests.Session, out: Path, ledger: dict[str, Any], phase: int, args: argparse.Namespace) -> dict[str, Any]:
    cap = PHASE_CAPS[phase]
    mode = ledger.get("expected_download_mode")
    try:
        if phase == 0:
            manifest = manifest_base(ledger, phase, cap, "METADATA_ONLY", "Phase 0 preflight only; no bulk download.")
        elif mode in {"CKAN_DATASTORE_READY", "PORT_CKAN_DATASTORE_READY"}:
            manifest = land_ckan_datastore(session, out, ledger, phase, cap, args.chunk_size, args.timeout)
        elif mode == "CKAN_PACKAGE_RESOURCE_DOWNLOAD_READY":
            manifest = land_file_source(session, out, ledger, phase, cap, args.timeout, args.max_files_per_source, args.max_file_mb * 1024 * 1024)
        elif mode == "GBFS_READY":
            manifest = land_gbfs(session, out, ledger, phase, cap, args.timeout)
        elif mode == "TMB_STATIC_GTFS_READY":
            manifest = land_tmb_static(root, session, out, ledger, phase, cap, args.timeout)
        elif mode in {"SENTILO_CONNECTA_READY", "DIRECT_NATIVE_READY", "DIRECT_METADATA_ONLY"}:
            manifest = land_direct(session, out, ledger, phase, cap, args.timeout)
        elif mode == "CADASTRE_EXISTING_RECOVERY":
            manifest = register_cadastre(out, ledger, phase, cap)
        elif mode in {"KEY_REQUIRED", "KEY_BLOCKED"}:
            manifest = manifest_base(ledger, phase, cap, "KEY_BLOCKED", ledger.get("classification_reason") or "credentials required")
        else:
            manifest = manifest_base(ledger, phase, cap, "SKIPPED_WITH_REASON", ledger.get("classification_reason") or "not feasible")
    except Exception as exc:  # noqa: BLE001
        manifest = manifest_base(ledger, phase, cap, "FAILED_WITH_REASON", repr(exc))
    write_manifest_and_profile(out, manifest)
    return manifest


def write_ledger(out: Path, ledger: list[dict[str, Any]]) -> None:
    write_json(out / "BARC_ALLFLOWS_SOURCE_LEDGER.json", {"task": TASK, "generated_at": utc_now(), "source_count": len(ledger), "sources": ledger})


def write_phase_manifest(out: Path, manifests: list[dict[str, Any]], phase: int, status: str) -> None:
    counts = Counter(m.get("status") for m in manifests)
    write_json(
        out / "BARC_ALLFLOWS_PHASE_MANIFEST.json",
        {
            "task": TASK,
            "generated_at": utc_now(),
            "phase": phase,
            "target_cap": PHASE_CAPS[phase],
            "status": status,
            "source_count": len(manifests),
            "status_counts": dict(sorted(counts.items())),
            "total_rows": sum(int(m.get("landed_rows") or 0) for m in manifests),
            "total_features": sum(int(m.get("landed_features") or 0) for m in manifests),
            "total_files": sum(int(m.get("landed_files") or 0) for m in manifests),
            "total_bytes": sum(int(m.get("landed_bytes") or 0) for m in manifests),
            "sources": manifests,
        },
    )


def csv_write(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_status_tables(out: Path, manifests: list[dict[str, Any]]) -> None:
    rows = []
    for m in manifests:
        rows.append(
            {
                "source_key": m.get("source_key"),
                "priority_band": m.get("priority_band"),
                "flows": ",".join(m.get("flows") or []),
                "preferred_api": m.get("preferred_api"),
                "status": m.get("status"),
                "phase": m.get("phase"),
                "target_cap": m.get("target_cap"),
                "source_total_count": m.get("source_total_count"),
                "landed_rows": m.get("landed_rows"),
                "landed_features": m.get("landed_features"),
                "landed_files": m.get("landed_files"),
                "landed_bytes": m.get("landed_bytes"),
                "privacy_class": m.get("privacy_class"),
                "boundary_class": m.get("boundary_class"),
                "notes": m.get("notes"),
            }
        )
    csv_write(
        out / "BARC_ALLFLOWS_DATASET_STATUS.csv",
        rows,
        ["source_key", "priority_band", "flows", "preferred_api", "status", "phase", "target_cap", "source_total_count", "landed_rows", "landed_features", "landed_files", "landed_bytes", "privacy_class", "boundary_class", "notes"],
    )
    phase_rows = []
    by_phase = defaultdict(list)
    for m in manifests:
        by_phase[int(m.get("phase") or 0)].append(m)
    for phase, items in sorted(by_phase.items()):
        for status, count in Counter(m.get("status") for m in items).items():
            phase_rows.append(
                {
                    "phase": phase,
                    "status": status,
                    "source_count": count,
                    "rows": sum(int(m.get("landed_rows") or 0) for m in items if m.get("status") == status),
                    "features": sum(int(m.get("landed_features") or 0) for m in items if m.get("status") == status),
                    "files": sum(int(m.get("landed_files") or 0) for m in items if m.get("status") == status),
                    "bytes": sum(int(m.get("landed_bytes") or 0) for m in items if m.get("status") == status),
                }
            )
    csv_write(out / "BARC_ALLFLOWS_COUNTS_BY_PHASE.csv", phase_rows, ["phase", "status", "source_count", "rows", "features", "files", "bytes"])


def write_schema_profiles(out: Path, manifests: list[dict[str, Any]]) -> None:
    profiles = {}
    for manifest in manifests:
        profiles[manifest["source_key"]] = read_json(out / "profiles" / f"{manifest['source_key']}.profile.json", {})
    write_json(out / "BARC_ALLFLOWS_SCHEMA_PROFILES.json", {"task": TASK, "generated_at": utc_now(), "profiles": profiles})


def write_hashes(out: Path) -> None:
    lines = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "BARC_ALLFLOWS_HASHES.sha256":
            lines.append(f"{sha256_file(path)}  {path.relative_to(out).as_posix()}")
    write_text(out / "BARC_ALLFLOWS_HASHES.sha256", "\n".join(lines) + "\n")


def secret_scan(out: Path) -> dict[str, Any]:
    findings = []
    for path in out.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"app_key=(?!REDACTED)[A-Za-z0-9]{12,}", text):
            findings.append({"path": str(path), "pattern": "UNREDACTED_APP_KEY_QUERY"})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def write_static_docs(out: Path, phase: int, status: str, manifests: list[dict[str, Any]], secret: dict[str, Any]) -> None:
    blocked = [m for m in manifests if m.get("status") in {"KEY_BLOCKED", "BLOCKED_REMOTE", "FAILED_WITH_REASON", "SKIPPED_WITH_REASON", "ENDPOINT_VALIDATION_REQUIRED"}]
    totals = {
        "sources": len(manifests),
        "rows": sum(int(m.get("landed_rows") or 0) for m in manifests),
        "features": sum(int(m.get("landed_features") or 0) for m in manifests),
        "files": sum(int(m.get("landed_files") or 0) for m in manifests),
        "bytes": sum(int(m.get("landed_bytes") or 0) for m in manifests),
    }
    plan = [
        "# BARC All-Flows Data Landing Plan",
        "",
        "Cap ladder: Phase 0 preflight, then 1M, 5M, 10M, 15M, 20M, 25M per dataset.",
        "",
        "Barcelona is CKAN/native API backed, not SODA2-backed. SODA2 is not used unless a source is explicitly Socrata-backed.",
        "",
        "Round-robin rule: each cap loop traverses all sources before deeper continuation.",
    ]
    write_text(out / "BARC_ALLFLOWS_LANDING_PLAN.md", "\n".join(plan) + "\n")
    write_text(
        out / "BARC_ALLFLOWS_PRIVACY_BOUNDARY.md",
        "# BARC All-Flows Privacy Boundary\n\n" + "\n".join(f"- {line}" for line in BOUNDARY_LINES) + "\n",
    )
    limitations = ["# BARC All-Flows Limitations", "", f"Current phase: {phase}", f"Current status: {status}", ""]
    for m in blocked:
        limitations.append(f"- {m['source_key']}: {m['status']} - {m.get('notes') or (m.get('error_history') or [{}])[-1]}")
    write_text(out / "BARC_ALLFLOWS_LIMITATIONS.md", "\n".join(limitations) + "\n")
    resume = [
        "# BARC All-Flows Stop/Resume Guide",
        "",
        "Rerun the same script. Existing chunk files and manifests are preserved.",
        "",
        "Examples:",
        "",
        "```powershell",
        "python scripts\\run_barc_allflows_data_landing_r1.py --project-root . --max-phase 1",
        "python scripts\\run_barc_allflows_data_landing_r1.py --project-root . --max-phase 2",
        "python scripts\\run_barc_allflows_data_landing_r1.py --project-root . --max-phase 6",
        "```",
    ]
    write_text(out / "BARC_ALLFLOWS_STOP_RESUME_GUIDE.md", "\n".join(resume) + "\n")
    report = [
        "# BARC All-Flows Data Landing Acceptance Report",
        "",
        f"Status: `{status}`",
        f"Generated: `{utc_now()}`",
        "",
        "This is data landing acceptance only. It does not accept any new Barcelona flow.",
        "",
        "## Totals",
        "",
        f"- Sources represented: {totals['sources']}",
        f"- Rows landed: {totals['rows']:,}",
        f"- Features registered: {totals['features']:,}",
        f"- Files landed/registered: {totals['files']:,}",
        f"- Bytes landed/registered: {totals['bytes']:,}",
        f"- Secret redaction: {secret['status']}",
        "",
        "## Status Counts",
        "",
    ]
    for name, count in sorted(Counter(m.get("status") for m in manifests).items()):
        report.append(f"- {name}: {count}")
    report.extend(
        [
            "",
            "## Recommended Next Tasks",
            "",
            "- BARC-ALLFLOWS-CONSUMPTION-PREP-R1",
            "- BARC-F1-CONSUMPTION-CANDIDATE-R1",
            "- BARC-F4-CONSUMPTION-CANDIDATE-R1",
            "- BARC-F5-CONSUMPTION-CANDIDATE-R1",
            "- BARC-F7-CONSUMPTION-REFRESH-R1",
        ]
    )
    write_text(out / "BARC_ALLFLOWS_ACCEPTANCE_REPORT.md", "\n".join(report) + "\n")
    readme = [
        "# BARC-ALLFLOWS-DATA-LANDING-R1",
        "",
        f"Status: `{status}`",
        "",
        "Outputs are stoppable/resumable data landing artifacts. No platform state was changed.",
    ]
    write_text(out / "README.md", "\n".join(readme) + "\n")


def copy_runner(out: Path) -> None:
    src = Path(__file__).resolve()
    dest = out / "scripts" / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = resolve(Path.cwd(), args.project_root)
    out = resolve(root, args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for sub in ["data/raw", "data/normalized", "files", "manifests", "profiles", "logs", "scripts"]:
        (out / sub).mkdir(parents=True, exist_ok=True)
    copy_runner(out)
    scan = read_json(resolve(root, args.scan), {})
    ledger = ledger_from_scan(scan, root)
    write_ledger(out, ledger)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    final_manifests: list[dict[str, Any]] = []
    phase_status = "PASS_PHASE_0_PREFLIGHT"
    for phase in range(0, args.max_phase + 1):
        print(f"Phase {phase} cap={PHASE_CAPS[phase]}", flush=True)
        phase_manifests = []
        for idx, source in enumerate(ledger, 1):
            print(f"[phase {phase}] [{idx}/{len(ledger)}] {source['source_key']}", flush=True)
            manifest = land_source(root, session, out, source, phase, args)
            phase_manifests.append(manifest)
        final_manifests = phase_manifests
        phase_status = PHASE_STATUS[phase]
        write_phase_manifest(out, phase_manifests, phase, phase_status)
        write_status_tables(out, phase_manifests)
        write_schema_profiles(out, phase_manifests)
        write_hashes(out)
        secret = secret_scan(out)
        write_static_docs(out, phase, phase_status if secret["status"] == "PASS" else "FAIL", phase_manifests, secret)
    write_hashes(out)
    secret = secret_scan(out)
    status = phase_status if secret["status"] == "PASS" else "FAIL"
    write_static_docs(out, args.max_phase, status, final_manifests, secret)
    return {
        "status": status,
        "output_dir": str(out),
        "source_count": len(final_manifests),
        "rows": sum(int(m.get("landed_rows") or 0) for m in final_manifests),
        "features": sum(int(m.get("landed_features") or 0) for m in final_manifests),
        "files": sum(int(m.get("landed_files") or 0) for m in final_manifests),
        "secret_scan": secret,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run BARC all-flows data landing R1.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--scan", default=str(DEFAULT_SCAN))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--max-phase", type=int, default=1, choices=range(0, 7))
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE_DEFAULT)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--max-files-per-source", type=int, default=4)
    parser.add_argument("--max-file-mb", type=int, default=750)
    args = parser.parse_args()
    result = run(args)
    print(f"{TASK}: {result['status']}")
    print(f"Output: {result['output_dir']}")
    print(f"Sources: {result['source_count']} Rows: {result['rows']} Features: {result['features']} Files: {result['files']}")
    return 0 if result["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())

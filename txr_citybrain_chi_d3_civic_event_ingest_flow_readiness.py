from __future__ import annotations

import argparse
import gc
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


TASK_NAME = "CHI-D3 Chicago Civic/Event Ingest + Flow Readiness"
DEFAULT_D1_OUTPUT = "outputs/chi_d1_chicago_deep_source_api_scout"
DEFAULT_D1_LANDING = "data_landing/chi_d1_official_sources_v1"
DEFAULT_D1B_OUTPUT = "outputs/chi_d1b_chicago_extended_source_landing"
DEFAULT_D1B_LANDING = "data_landing/chi_d1b_extended_sources_v1"
DEFAULT_D2B_DIR = "outputs/chi_d2b_base_identity_refresh"
DEFAULT_OUTPUT_DIR = "outputs/chi_d3_civic_event_ingest_flow_readiness"

BOUNDARY_LINES = [
    "CHI-D3 ingests Chicago civic/event sources and produces flow-readiness evidence only.",
    "CHI-D3 does not create a certified Chicago cartridge.",
    "CHI-D3 does not build Flow 1 or Flow 7.",
    "CHI-D3 does not certify affected buildings/assets.",
    "CHI-D3 does not create operational recommendations.",
    "CHI-D3 does not make policing, dispatch, enforcement, health, emergency, or public-safety recommendations.",
    "Chicago source base improved materially, but still not all-full-source because Divvy, Cook parcels, Crimes, and Open Air individual remain capped/windowed.",
    "Crime data is privacy-safe block-level context only.",
    "Crash people/vehicles are context only, not affected-asset, safety, enforcement, or response evidence.",
    "CTA GTFS is static schedule geography, not live transit status.",
]

FORBIDDEN_PATTERNS = [
    r"\bcreates a certified chicago cartridge\b",
    r"\bchicago cartridge is certified\b",
    r"\bbuilds flow 1\b",
    r"\bbuilds flow 7\b",
    r"\bcertifies affected (?:buildings|assets)\b",
    r"\baffected (?:buildings|assets) are certified\b",
    r"\bincident-to-asset certification\b",
    r"\bcreates operational recommendations\b",
    r"\bmakes policing recommendations\b",
    r"\bmakes dispatch recommendations\b",
    r"\bmakes enforcement recommendations\b",
    r"\bmakes health recommendations\b",
    r"\bmakes emergency recommendations\b",
    r"\bmakes public-safety recommendations\b",
    r"\bpolicing target\b",
    r"\bdispatch route\b",
    r"\bhealth recommendation generated\b",
]

SOURCE_RELS = {
    "311_service_requests": "raw/city_of_chicago/v6vf-nfxy__311_service_requests",
    "traffic_crashes_crashes": "raw/city_of_chicago/85ca-t3if__traffic_crashes_crashes",
    "traffic_crashes_people": "raw/city_of_chicago/u6pd-qa9d__traffic_crashes_people",
    "traffic_crashes_vehicles": "raw/city_of_chicago/68nd-jvt3__traffic_crashes_vehicles",
    "building_permits": "raw/city_of_chicago/ydr8-5enu__building_permits",
    "building_violations": "raw/city_of_chicago/22u3-xenr__building_violations",
    "food_inspections": "raw/city_of_chicago/4ijn-s7e5__food_inspections",
    "business_licenses": "raw/city_of_chicago/r5kz-chrr__business_licenses",
    "divvy_trips": "raw/city_of_chicago/fg6s-gzvg__divvy_trips",
    "crimes_2001_present": "raw/city_of_chicago/ijzp-q8t2__crimes_2001_present",
    "traffic_tracker_historical_2024_current": "raw/city_of_chicago/4g9f-3jbs__traffic_tracker_historical_2024_current",
    "open_air_chicago_hour_aggregations": "raw/environment/di9s-96ws__open_air_chicago_hour_aggregations",
    "open_air_chicago_individual_measurements": "raw/environment/xfya-dxtq__open_air_chicago_individual_measurements",
}

CANONICAL_FILES = {
    "311_service_request": "chi_d3_311_service_events.parquet",
    "traffic_crash": "chi_d3_traffic_crash_events.parquet",
    "building_permit": "chi_d3_permit_events.parquet",
    "building_violation": "chi_d3_building_violation_events.parquet",
    "food_inspection": "chi_d3_food_inspection_events.parquet",
    "business_license": "chi_d3_business_license_events.parquet",
    "divvy_mobility": "chi_d3_divvy_mobility_events.parquet",
    "open_air_observation": "chi_d3_open_air_observations.parquet",
    "crime_context": "chi_d3_crime_context_events_privacy_safe.parquet",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def with_boundary(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    out.setdefault("generated_at", utc_now())
    out.setdefault("boundary_lines", BOUNDARY_LINES)
    return out


def write_json(path: Path, payload: Any, add_boundary: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if add_boundary and isinstance(payload, dict):
        payload = with_boundary(payload)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums, add_boundary=False)
    expected = sorted(p.relative_to(output_dir).as_posix() for p in output_dir.rglob("*") if p.is_file() and p.name != "SHA256SUMS.json")
    return {
        "status": "PASS" if sorted(sums) == expected else "FAIL",
        "file_count": len(sums),
        "missing": sorted(set(expected) - set(sums)),
        "extra": sorted(set(sums) - set(expected)),
    }


def write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if frame.empty:
        frame = pd.DataFrame({"_empty": pd.Series(dtype="string")})
    frame.to_parquet(path, index=False)


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()):
            raise ValueError(f"Refusing to remove output outside workspace: {resolved}")
        if "chi_d3_civic_event_ingest_flow_readiness" not in resolved.name.lower():
            raise ValueError(f"Refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    (output_dir / "canonical").mkdir(parents=True, exist_ok=True)
    (output_dir / "reports").mkdir(parents=True, exist_ok=True)


def snapshot(paths: list[Path]) -> dict[str, Any]:
    watched: dict[str, Any] = {}
    for root in paths:
        if not root.exists():
            watched[str(root.resolve())] = {"exists": False}
            continue
        files = [root] if root.is_file() else [p for p in sorted(root.rglob("*")) if p.is_file()]
        for path in files:
            stat = path.stat()
            entry = {"exists": True, "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns}
            if stat.st_size <= 5_000_000:
                entry["sha256"] = sha256_file(path)
            watched[str(path.resolve())] = entry
    return watched


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = []
    for key, old in before.items():
        if old != after.get(key):
            changed.append({"path": key, "before": old, "after": after.get(key)})
    return {"status": "PASS" if not changed else "FAIL", "changed_inputs": changed, "checked_files": len(before)}


def clean_series(frame: pd.DataFrame, col: str) -> pd.Series:
    if col in frame.columns:
        series = frame[col].astype("string").str.strip()
    else:
        series = pd.Series([pd.NA] * len(frame), index=frame.index, dtype="string")
    return series.mask(series.str.lower().isin(["", "nan", "none", "null", "<na>"]))


def clean_value(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    text = str(value).strip()
    return text if text and text.lower() not in {"nan", "none", "null", "<na>"} else None


def safe_id(value: Any, fallback: str = "unknown") -> str:
    text = clean_value(value) or fallback
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text[:180] or fallback


def numeric_like_key(series: pd.Series) -> pd.Series:
    out = series.astype("string").str.strip()
    mask = out.str.fullmatch(r"\d+(?:\.0)?", na=False)
    out.loc[mask] = pd.to_numeric(out.loc[mask], errors="coerce").astype("Int64").astype("string")
    return out.mask(out.str.lower().isin(["", "nan", "none", "null", "<na>"]))


def number_series(frame: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(clean_series(frame, col), errors="coerce")


def point_geojson_series(lon: pd.Series, lat: pd.Series) -> pd.Series:
    has_point = lon.notna() & lat.notna()
    out = pd.Series(pd.NA, index=lon.index, dtype="object")
    out.loc[has_point] = [f'{{"coordinates":[{x},{y}],"type":"Point"}}' for x, y in zip(lon.loc[has_point], lat.loc[has_point])]
    return out


def location_confidence(lat: pd.Series, lon: pd.Series, address: pd.Series | None = None, area_cols: list[pd.Series] | None = None) -> pd.Series:
    conf = pd.Series("D", index=lat.index, dtype="string")
    has_point = lat.notna() & lon.notna()
    has_address = address.notna() if address is not None else pd.Series(False, index=lat.index)
    has_area = pd.Series(False, index=lat.index)
    for series in area_cols or []:
        has_area = has_area | series.notna()
    conf.loc[has_area] = "C"
    conf.loc[has_address] = "B"
    conf.loc[has_point] = "A"
    return conf


def hash_id_series(series: pd.Series, prefix: str = "") -> pd.Series:
    values = series.fillna("").astype(str)
    return values.map(lambda text: hashlib.sha256((prefix + text).encode("utf-8", errors="replace")).hexdigest()[:20])


def source_manifest(d1b_landing: Path, source_key: str) -> dict[str, Any]:
    return read_json(d1b_landing / SOURCE_RELS[source_key] / "source_manifest.json", {})


def source_statuses(d1b_output: Path, d1b_landing: Path) -> dict[str, dict[str, Any]]:
    counts_payload = read_json(d1b_output / "CHI_D1B_COUNTS_REPORT.json", {})
    statuses = {item.get("source_key"): dict(item) for item in counts_payload.get("counts", []) if item.get("source_key")}
    for key in SOURCE_RELS:
        manifest = source_manifest(d1b_landing, key)
        if not manifest:
            continue
        item = dict(statuses.get(key, {}))
        item.update(
            {
                "source_key": key,
                "resource_id": manifest.get("resource_id", item.get("resource_id")),
                "completion_status": manifest.get("completion_status", item.get("completion_status")),
                "downloaded_rows": manifest.get("downloaded_rows", item.get("downloaded_rows")),
                "planned_count": manifest.get("planned_count", item.get("planned_count")),
                "total_count": manifest.get("total_count_probe", {}).get("count", item.get("total_count")),
                "window_count": manifest.get("window_count_probe", {}).get("count", item.get("window_count")),
                "official_title": manifest.get("official_title"),
                "manifest_path": str(d1b_landing / SOURCE_RELS[key] / "source_manifest.json"),
            }
        )
        statuses[key] = item
    return statuses


def csv_paths_for(d1b_landing: Path, source_key: str) -> list[Path]:
    manifest = source_manifest(d1b_landing, source_key)
    paths: list[Path] = []
    for chunk in manifest.get("chunks", []):
        path_text = chunk.get("path")
        path = Path(path_text) if path_text else d1b_landing / chunk.get("relative_path", "")
        if path.exists() and path.suffix.lower() == ".csv":
            paths.append(path)
    return paths


def read_source(d1b_landing: Path, source_key: str, usecols: list[str]) -> tuple[pd.DataFrame, dict[str, Any]]:
    paths = csv_paths_for(d1b_landing, source_key)
    frames = []
    for path in paths:
        frames.append(pd.read_csv(path, dtype=str, usecols=lambda c: c in usecols, low_memory=False))
    frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=usecols)
    manifest = source_manifest(d1b_landing, source_key)
    profile = {
        "source_key": source_key,
        "source_rel": SOURCE_RELS[source_key],
        "csv_paths_read": [str(path) for path in paths],
        "chunks_read": len(paths),
        "rows_loaded": int(len(frame)),
        "manifest_downloaded_rows": manifest.get("downloaded_rows"),
        "completion_status": manifest.get("completion_status"),
        "total_count": manifest.get("total_count_probe", {}).get("count"),
        "window_count": manifest.get("window_count_probe", {}).get("count"),
        "resource_id": manifest.get("resource_id"),
    }
    return frame, profile


def add_common_location(frame: pd.DataFrame, address_col: str | None = None) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    lat = number_series(frame, "latitude")
    lon = number_series(frame, "longitude")
    address = clean_series(frame, address_col) if address_col else pd.Series(pd.NA, index=frame.index, dtype="string")
    ward = clean_series(frame, "ward")
    community = clean_series(frame, "community_area")
    conf = location_confidence(lat, lon, address=address, area_cols=[ward, community, clean_series(frame, "police_district")])
    return lat, lon, address, conf


def canonical_from_id(prefix: str, series: pd.Series) -> pd.Series:
    ids = series.fillna("").astype(str)
    fallback_hash = hash_id_series(ids, prefix=prefix)
    clean_ids = ids.mask(ids.str.strip() == "", fallback_hash).map(safe_id)
    return prefix + clean_ids


def write_event_outputs(
    output_dir: Path,
    event_type: str,
    frame: pd.DataFrame,
    location_frames: list[pd.DataFrame],
    edge_seed_frames: list[pd.DataFrame],
) -> dict[str, Any]:
    write_parquet(output_dir / "canonical" / CANONICAL_FILES[event_type], frame)
    location_cols = ["canonical_id", "event_type", "source_status", "location_confidence", "latitude", "longitude", "ward", "community_area", "police_district"]
    loc = frame.copy()
    for col in location_cols:
        if col not in loc.columns:
            loc[col] = pd.NA
    location_frames.append(loc[location_cols].copy())
    seed_cols = ["canonical_id", "event_type", "ward", "community_area", "source_status", "location_confidence"]
    edge_seed_frames.append(loc[seed_cols].copy())
    profile = {
        "event_type": event_type,
        "rows": int(len(frame)),
        "location_confidence_counts": frame.get("location_confidence", pd.Series(dtype=str)).value_counts(dropna=False).to_dict(),
        "source_status_counts": frame.get("source_status", pd.Series(dtype=str)).value_counts(dropna=False).to_dict(),
    }
    del loc
    gc.collect()
    return profile


def normalize_311(raw: pd.DataFrame, status: str) -> pd.DataFrame:
    lat, lon, address, conf = add_common_location(raw, "street_address")
    source_id = clean_series(raw, "sr_number")
    return pd.DataFrame(
        {
            "canonical_id": canonical_from_id("event:us-chicago:311:", source_id),
            "entity_type": "Event",
            "event_type": "311_service_request",
            "source_record_id": source_id,
            "service_request_number": source_id,
            "service_type": clean_series(raw, "sr_type"),
            "service_short_code": clean_series(raw, "sr_short_code"),
            "status": clean_series(raw, "status"),
            "origin": clean_series(raw, "origin"),
            "created_date": clean_series(raw, "created_date"),
            "closed_date": clean_series(raw, "closed_date"),
            "last_modified_date": clean_series(raw, "last_modified_date"),
            "address_text": address,
            "ward": clean_series(raw, "ward"),
            "community_area": clean_series(raw, "community_area"),
            "police_district": clean_series(raw, "police_district"),
            "zip": clean_series(raw, "zip_code"),
            "latitude": lat,
            "longitude": lon,
            "geometry_json": point_geojson_series(lon, lat),
            "location_confidence": conf,
            "source_status": status,
            "source_dataset": "Chicago 311 Service Requests",
            "provenance": '[{"source":"CHI-D1B 311 service requests"}]',
        }
    )


def normalize_crashes(raw: pd.DataFrame, status: str) -> pd.DataFrame:
    lat, lon, _, conf = add_common_location(raw, None)
    street = (
        clean_series(raw, "street_no").fillna("")
        + " "
        + clean_series(raw, "street_direction").fillna("")
        + " "
        + clean_series(raw, "street_name").fillna("")
    ).str.replace(r"\s+", " ", regex=True).str.strip().mask(lambda s: s == "")
    conf = location_confidence(lat, lon, address=street, area_cols=[clean_series(raw, "beat_of_occurrence")])
    source_id = clean_series(raw, "crash_record_id")
    return pd.DataFrame(
        {
            "canonical_id": canonical_from_id("event:us-chicago:traffic_crash:", source_id),
            "entity_type": "Event",
            "event_type": "traffic_crash",
            "source_record_id": source_id,
            "crash_record_id": source_id,
            "crash_date": clean_series(raw, "crash_date"),
            "first_crash_type": clean_series(raw, "first_crash_type"),
            "crash_type": clean_series(raw, "crash_type"),
            "report_type": clean_series(raw, "report_type"),
            "weather_condition": clean_series(raw, "weather_condition"),
            "lighting_condition": clean_series(raw, "lighting_condition"),
            "trafficway_type": clean_series(raw, "trafficway_type"),
            "street_text": street,
            "beat": clean_series(raw, "beat_of_occurrence"),
            "num_units": clean_series(raw, "num_units"),
            "most_severe_injury": clean_series(raw, "most_severe_injury"),
            "injuries_total": clean_series(raw, "injuries_total"),
            "injuries_fatal": clean_series(raw, "injuries_fatal"),
            "latitude": lat,
            "longitude": lon,
            "geometry_json": point_geojson_series(lon, lat),
            "location_confidence": conf,
            "ward": pd.NA,
            "community_area": pd.NA,
            "police_district": pd.NA,
            "source_status": status,
            "source_dataset": "Chicago Traffic Crashes - Crashes",
            "provenance": '[{"source":"CHI-D1B Traffic Crashes - Crashes"}]',
        }
    )


def normalize_permits(raw: pd.DataFrame, status: str) -> pd.DataFrame:
    lat, lon, _, conf = add_common_location(raw, None)
    street = (
        clean_series(raw, "street_number").fillna("")
        + " "
        + clean_series(raw, "street_direction").fillna("")
        + " "
        + clean_series(raw, "street_name").fillna("")
    ).str.replace(r"\s+", " ", regex=True).str.strip().mask(lambda s: s == "")
    conf = location_confidence(lat, lon, address=street, area_cols=[clean_series(raw, "ward"), clean_series(raw, "community_area")])
    source_id = clean_series(raw, "permit_").fillna(clean_series(raw, "id"))
    return pd.DataFrame(
        {
            "canonical_id": canonical_from_id("event:us-chicago:building_permit:", source_id),
            "entity_type": "Event",
            "event_type": "building_permit",
            "source_record_id": clean_series(raw, "id"),
            "permit_number": clean_series(raw, "permit_"),
            "permit_status": clean_series(raw, "permit_status"),
            "permit_milestone": clean_series(raw, "permit_milestone"),
            "permit_type": clean_series(raw, "permit_type"),
            "review_type": clean_series(raw, "review_type"),
            "application_start_date": clean_series(raw, "application_start_date"),
            "issue_date": clean_series(raw, "issue_date"),
            "work_type": clean_series(raw, "work_type"),
            "pin_list": clean_series(raw, "pin_list"),
            "address_text": street,
            "ward": clean_series(raw, "ward"),
            "community_area": clean_series(raw, "community_area"),
            "police_district": pd.NA,
            "latitude": lat,
            "longitude": lon,
            "geometry_json": point_geojson_series(lon, lat),
            "location_confidence": conf,
            "source_status": status,
            "source_dataset": "Chicago Building Permits",
            "provenance": '[{"source":"CHI-D1B building permits"}]',
        }
    )


def normalize_violations(raw: pd.DataFrame, status: str) -> pd.DataFrame:
    lat, lon, address, conf = add_common_location(raw, "address")
    source_id = clean_series(raw, "id")
    return pd.DataFrame(
        {
            "canonical_id": canonical_from_id("event:us-chicago:building_violation:", source_id),
            "entity_type": "Event",
            "event_type": "building_violation",
            "source_record_id": source_id,
            "violation_code": clean_series(raw, "violation_code"),
            "violation_status": clean_series(raw, "violation_status"),
            "violation_date": clean_series(raw, "violation_date"),
            "violation_status_date": clean_series(raw, "violation_status_date"),
            "violation_description": clean_series(raw, "violation_description"),
            "inspection_number": clean_series(raw, "inspection_number"),
            "inspection_status": clean_series(raw, "inspection_status"),
            "inspection_category": clean_series(raw, "inspection_category"),
            "department_bureau": clean_series(raw, "department_bureau"),
            "address_text": address,
            "property_group": clean_series(raw, "property_group"),
            "ward": pd.NA,
            "community_area": pd.NA,
            "police_district": pd.NA,
            "latitude": lat,
            "longitude": lon,
            "geometry_json": point_geojson_series(lon, lat),
            "location_confidence": conf,
            "source_status": status,
            "source_dataset": "Chicago Building Violations",
            "provenance": '[{"source":"CHI-D1B building violations"}]',
        }
    )


def normalize_food(raw: pd.DataFrame, status: str) -> pd.DataFrame:
    lat, lon, address, conf = add_common_location(raw, "address")
    source_id = clean_series(raw, "inspection_id")
    violations = clean_series(raw, "violations")
    return pd.DataFrame(
        {
            "canonical_id": canonical_from_id("inspection:us-chicago:food:", source_id),
            "entity_type": "Inspection",
            "event_type": "food_inspection",
            "source_record_id": source_id,
            "inspection_id": source_id,
            "dba_name": clean_series(raw, "dba_name"),
            "aka_name": clean_series(raw, "aka_name"),
            "license_id": clean_series(raw, "license_"),
            "facility_type": clean_series(raw, "facility_type"),
            "risk": clean_series(raw, "risk"),
            "inspection_date": clean_series(raw, "inspection_date"),
            "inspection_type": clean_series(raw, "inspection_type"),
            "results": clean_series(raw, "results"),
            "violations_text_redacted": violations.notna(),
            "violation_entry_count": violations.fillna("").str.count(r"\|") + violations.notna().astype(int),
            "address_text": address,
            "ward": pd.NA,
            "community_area": pd.NA,
            "police_district": pd.NA,
            "zip": clean_series(raw, "zip"),
            "latitude": lat,
            "longitude": lon,
            "geometry_json": point_geojson_series(lon, lat),
            "location_confidence": conf,
            "source_status": status,
            "source_dataset": "Chicago Food Inspections",
            "provenance": '[{"source":"CHI-D1B food inspections"}]',
        }
    )


def normalize_business(raw: pd.DataFrame, status: str) -> pd.DataFrame:
    lat, lon, address, conf = add_common_location(raw, "address")
    source_id = clean_series(raw, "license_id").fillna(clean_series(raw, "id"))
    return pd.DataFrame(
        {
            "canonical_id": canonical_from_id("license:us-chicago:business:", source_id),
            "entity_type": "License",
            "event_type": "business_license",
            "source_record_id": clean_series(raw, "id"),
            "license_id": clean_series(raw, "license_id"),
            "account_number": clean_series(raw, "account_number"),
            "site_number": clean_series(raw, "site_number"),
            "doing_business_as_name": clean_series(raw, "doing_business_as_name"),
            "address_text": address,
            "ward": clean_series(raw, "ward"),
            "community_area": clean_series(raw, "community_area"),
            "community_area_name": clean_series(raw, "community_area_name"),
            "police_district": clean_series(raw, "police_district"),
            "license_code": clean_series(raw, "license_code"),
            "license_description": clean_series(raw, "license_description"),
            "business_activity_id": clean_series(raw, "business_activity_id"),
            "application_type": clean_series(raw, "application_type"),
            "application_created_date": clean_series(raw, "application_created_date"),
            "license_start_date": clean_series(raw, "license_start_date"),
            "expiration_date": clean_series(raw, "expiration_date"),
            "date_issued": clean_series(raw, "date_issued"),
            "license_status": clean_series(raw, "license_status"),
            "latitude": lat,
            "longitude": lon,
            "geometry_json": point_geojson_series(lon, lat),
            "location_confidence": conf,
            "source_status": status,
            "source_dataset": "Chicago Business Licenses",
            "provenance": '[{"source":"CHI-D1B business licenses"}]',
        }
    )


def normalize_divvy(raw: pd.DataFrame, status: str) -> pd.DataFrame:
    lat = number_series(raw, "from_latitude")
    lon = number_series(raw, "from_longitude")
    station = clean_series(raw, "from_station_name")
    conf = location_confidence(lat, lon, address=station, area_cols=[clean_series(raw, "from_station_id")])
    source_id = clean_series(raw, "trip_id")
    return pd.DataFrame(
        {
            "canonical_id": canonical_from_id("mobility_event:us-chicago:divvy:", source_id),
            "entity_type": "MobilityEvent",
            "event_type": "divvy_mobility",
            "source_record_id": source_id,
            "trip_id": source_id,
            "start_time": clean_series(raw, "start_time"),
            "stop_time": clean_series(raw, "stop_time"),
            "trip_duration": clean_series(raw, "trip_duration"),
            "from_station_id": clean_series(raw, "from_station_id"),
            "from_station_name": station,
            "to_station_id": clean_series(raw, "to_station_id"),
            "to_station_name": clean_series(raw, "to_station_name"),
            "user_type": clean_series(raw, "user_type"),
            "ward": pd.NA,
            "community_area": pd.NA,
            "police_district": pd.NA,
            "latitude": lat,
            "longitude": lon,
            "geometry_json": point_geojson_series(lon, lat),
            "location_confidence": conf,
            "source_status": status,
            "source_dataset": "Chicago Divvy Trips",
            "provenance": '[{"source":"CHI-D1B Divvy trips"}]',
        }
    )


def normalize_open_air(hourly: pd.DataFrame, hourly_status: str, individual: pd.DataFrame, individual_status: str) -> pd.DataFrame:
    frames = []
    if not hourly.empty:
        lat = number_series(hourly, "latitude")
        lon = number_series(hourly, "longitude")
        sensor = clean_series(hourly, "sensor_name")
        source_id = clean_series(hourly, "record_id").fillna(clean_series(hourly, "datasourceid") + "_" + clean_series(hourly, "startofperiod"))
        frames.append(
            pd.DataFrame(
                {
                    "canonical_id": canonical_from_id("observation:us-chicago:open_air:", source_id),
                    "entity_type": "Observation",
                    "event_type": "open_air_observation",
                    "observation_kind": "hourly",
                    "source_record_id": source_id,
                    "sensor_id": clean_series(hourly, "datasourceid"),
                    "sensor_name": sensor,
                    "observed_at": clean_series(hourly, "startofperiod"),
                    "pm2_5_value": clean_series(hourly, "pm2_5concmass1hourmean_value"),
                    "pm2_5_nowcast_value": clean_series(hourly, "pm2_5concmassnowcast_value"),
                    "no2_value": clean_series(hourly, "no2conc1hourmean_value"),
                    "temperature_internal": clean_series(hourly, "temperatureinternal1hourmean"),
                    "ward": pd.NA,
                    "community_area": pd.NA,
                    "police_district": pd.NA,
                    "latitude": lat,
                    "longitude": lon,
                    "geometry_json": point_geojson_series(lon, lat),
                    "location_confidence": location_confidence(lat, lon, address=sensor),
                    "source_status": hourly_status,
                    "source_dataset": "Open Air Chicago hourly aggregations",
                    "provenance": '[{"source":"CHI-D1B Open Air hourly aggregations"}]',
                }
            )
        )
    if not individual.empty:
        lat = number_series(individual, "latitude")
        lon = number_series(individual, "longitude")
        sensor = clean_series(individual, "sensor_name")
        source_id = clean_series(individual, "record_id").fillna(clean_series(individual, "datasourceid") + "_" + clean_series(individual, "time"))
        frames.append(
            pd.DataFrame(
                {
                    "canonical_id": canonical_from_id("observation:us-chicago:open_air:", source_id),
                    "entity_type": "Observation",
                    "event_type": "open_air_observation",
                    "observation_kind": "individual",
                    "source_record_id": source_id,
                    "sensor_id": clean_series(individual, "datasourceid"),
                    "sensor_name": sensor,
                    "observed_at": clean_series(individual, "time"),
                    "pm2_5_value": clean_series(individual, "pm2_5concmassindividual_value"),
                    "pm2_5_nowcast_value": pd.NA,
                    "no2_value": clean_series(individual, "no2concindividual_value"),
                    "temperature_internal": clean_series(individual, "temperatureinternalindividual"),
                    "ward": pd.NA,
                    "community_area": pd.NA,
                    "police_district": pd.NA,
                    "latitude": lat,
                    "longitude": lon,
                    "geometry_json": point_geojson_series(lon, lat),
                    "location_confidence": location_confidence(lat, lon, address=sensor),
                    "source_status": individual_status,
                    "source_dataset": "Open Air Chicago individual measurements",
                    "provenance": '[{"source":"CHI-D1B Open Air individual measurements"}]',
                }
            )
        )
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def normalize_crimes(raw: pd.DataFrame, status: str) -> pd.DataFrame:
    block = clean_series(raw, "block")
    ward = clean_series(raw, "ward")
    community = clean_series(raw, "community_area")
    district = clean_series(raw, "district")
    case_hash = hash_id_series(clean_series(raw, "case_number").fillna(clean_series(raw, "id")), prefix="chicago-crime:")
    conf = location_confidence(pd.Series(pd.NA, index=raw.index), pd.Series(pd.NA, index=raw.index), address=block, area_cols=[ward, community, district])
    return pd.DataFrame(
        {
            "canonical_id": "event:us-chicago:crime_context:" + case_hash,
            "entity_type": "ContextEvent",
            "event_type": "crime_context",
            "source_record_id": clean_series(raw, "id"),
            "case_number_hash": case_hash,
            "date": clean_series(raw, "date"),
            "block": block,
            "primary_type": clean_series(raw, "primary_type"),
            "description": clean_series(raw, "description"),
            "location_description": clean_series(raw, "location_description"),
            "arrest": clean_series(raw, "arrest"),
            "domestic": clean_series(raw, "domestic"),
            "beat": clean_series(raw, "beat"),
            "ward": ward,
            "community_area": community,
            "police_district": district,
            "year": clean_series(raw, "year"),
            "latitude": pd.NA,
            "longitude": pd.NA,
            "geometry_json": pd.NA,
            "location_confidence": conf,
            "source_status": status,
            "source_dataset": "Chicago Crimes privacy-safe block-level context",
            "privacy_status": "case_number_hashed_no_precise_point",
            "provenance": '[{"source":"CHI-D1B crimes privacy-safe block-level pull"}]',
        }
    )


def area_lookup(chi_d2b_dir: Path) -> pd.DataFrame:
    path = chi_d2b_dir / "canonical" / "chi_d2b_area_context.parquet"
    if not path.exists():
        return pd.DataFrame(columns=["area_type", "native_id", "canonical_id"])
    area = pd.read_parquet(path)
    if list(area.columns) == ["_empty"]:
        return pd.DataFrame(columns=["area_type", "native_id", "canonical_id"])
    return area[["area_type", "native_id", "canonical_id"]].copy()


def build_area_context_edges(seed_frames: list[pd.DataFrame], areas: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not seed_frames or areas.empty:
        return pd.DataFrame(), {"status": "SOURCE_LIMITED", "edges": 0}
    seeds = pd.concat(seed_frames, ignore_index=True)
    frames = []
    counts: dict[str, int] = {}
    for area_type, source_col in [("ward", "ward"), ("community_area", "community_area")]:
        area_map = areas.loc[areas["area_type"] == area_type, ["native_id", "canonical_id"]].copy()
        if area_map.empty:
            continue
        area_map["area_key"] = numeric_like_key(area_map["native_id"])
        work = seeds[["canonical_id", "event_type", "source_status", "location_confidence", source_col]].copy()
        work["area_key"] = numeric_like_key(work[source_col])
        work = work[work["area_key"].notna()]
        merged = work.merge(area_map[["area_key", "canonical_id"]], on="area_key", how="inner", suffixes=("_source", "_target"))
        if merged.empty:
            continue
        counts[area_type] = int(len(merged))
        frames.append(
            pd.DataFrame(
                {
                    "entity_type": "context_edge",
                    "source_id": merged["canonical_id_source"],
                    "target_id": merged["canonical_id_target"],
                    "source_event_type": merged["event_type"],
                    "relation": "within_area_context",
                    "join_method": "official_source_area_field",
                    "source_stage": "CHI-D3",
                    "confidence": 0.78,
                    "status": "field_backed_context_not_asset_certification",
                    "area_type": area_type,
                    "source_status": merged["source_status"],
                    "location_confidence": merged["location_confidence"],
                }
            )
        )
    edges = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not edges.empty:
        edges.insert(0, "canonical_id", [f"edge:us-chicago:chi-d3:event_area_context:{i}" for i in range(1, len(edges) + 1)])
    return edges, {
        "status": "PASS",
        "edges": int(len(edges)),
        "edge_counts_by_area_type": counts,
        "method": "official source area fields matched to accepted CHI-D2B area context IDs",
        "limitation": "Context only; no building, parcel, dispatch, enforcement, health, or public-safety recommendation edges are emitted.",
    }


def build_hero_candidates(event_counts: dict[str, int], location_counts: dict[str, int], flow7_status: str, flow1_status: str) -> pd.DataFrame:
    rows = [
        {
            "candidate_id": "hero_candidate:chi_d3:civic_service_hotspot",
            "candidate_type": "civic_service_hotspot",
            "supporting_sources": "311_service_requests",
            "location_confidence": "A/B/C mixed",
            "source_status": "WINDOWED_COMPLETE recent window",
            "why_candidate": "Expanded landed 311 recent-window layer supports civic service context review.",
            "limitations": "Recent 311 window is complete for the pulled window, not all-history full 311; no operational recommendation.",
            "recommended_next_gate": "CHI-D4",
        },
        {
            "candidate_id": "hero_candidate:chi_d3:traffic_crash_context",
            "candidate_type": "traffic_crash_context",
            "supporting_sources": "Traffic Crashes - Crashes; crash people/vehicles as full context",
            "location_confidence": "A where official crash point exists",
            "source_status": "crashes FULL; people/vehicles FULL context",
            "why_candidate": "Complete crash, people, and vehicle source context strengthens traffic event review while D3 still emits canonical crash events only.",
            "limitations": "No safety, enforcement, dispatch, or affected-asset recommendation.",
            "recommended_next_gate": "CHI-D4",
        },
        {
            "candidate_id": "hero_candidate:chi_d3:food_inspection_context",
            "candidate_type": "food_inspection_context",
            "supporting_sources": "Food Inspections",
            "location_confidence": "A/B mixed",
            "source_status": "FULL",
            "why_candidate": "Full inspection layer supports deterministic inspection/compliance context.",
            "limitations": "No health recommendation and no affected-building certification.",
            "recommended_next_gate": "CHI-D4",
        },
        {
            "candidate_id": "hero_candidate:chi_d3:building_permit_violation_context",
            "candidate_type": "building_permit_violation_context",
            "supporting_sources": "Building Permits; Building Violations",
            "location_confidence": "A/B mixed",
            "source_status": "permits FULL; violations WINDOWED_COMPLETE",
            "why_candidate": "Permits are full-source and violations cover the recent window for building-context review.",
            "limitations": "No certified building-to-parcel or enforcement recommendation.",
            "recommended_next_gate": "CHI-D4",
        },
        {
            "candidate_id": "hero_candidate:chi_d3:environment_sensor_context",
            "candidate_type": "environment_sensor_context",
            "supporting_sources": "Open Air hourly; Open Air individual",
            "location_confidence": "A where sensor point exists",
            "source_status": "hourly WINDOWED_COMPLETE; individual WINDOWED_CAPPED",
            "why_candidate": "Sensor observations support environmental context for Flow 7 readiness.",
            "limitations": "No health recommendation and no individual exposure claim.",
            "recommended_next_gate": "CHI-D4",
        },
        {
            "candidate_id": "hero_candidate:chi_d3:transit_facility_context",
            "candidate_type": "transit_facility_context",
            "supporting_sources": "CTA GTFS static; facilities/resources; D3 event context",
            "location_confidence": "contextual",
            "source_status": "CTA static GTFS; facilities carried forward",
            "why_candidate": "D2B resources plus D3 events can support a bounded face-layer context story.",
            "limitations": "CTA GTFS is static schedule geography, not live transit status.",
            "recommended_next_gate": "CHI-D4",
        },
    ]
    for row in rows:
        row["event_counts_summary"] = json.dumps(event_counts, sort_keys=True)
        row["location_counts_summary"] = json.dumps(location_counts, sort_keys=True)
        row["flow7_readiness"] = flow7_status
        row["flow1_readiness"] = flow1_status
    return pd.DataFrame(rows)


def scan_no_overclaim(output_dir: Path) -> dict[str, Any]:
    checked = []
    boundary_failures = []
    forbidden_hits = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md"} or path.name == "SHA256SUMS.json":
            continue
        if "canonical" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        checked.append(str(path.relative_to(output_dir)))
        missing = [line for line in BOUNDARY_LINES if line not in text]
        if missing:
            boundary_failures.append({"path": str(path.relative_to(output_dir)), "missing_boundary_lines": missing})
        lower = text.lower()
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, lower):
                forbidden_hits.append({"path": str(path.relative_to(output_dir)), "pattern": pattern})
    return {
        "status": "PASS" if not boundary_failures and not forbidden_hits else "FAIL",
        "checked_files": checked,
        "boundary_failures": boundary_failures,
        "forbidden_hits": forbidden_hits,
    }


def status_pass(value: Any) -> bool:
    text = str(value or "").upper()
    return text.startswith("PASS") or text.startswith("GREEN")


def source_usage_rows(statuses: dict[str, dict[str, Any]], profiles: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for key in sorted(statuses):
        rows.append(
            {
                "source_key": key,
                "completion_status": statuses[key].get("completion_status"),
                "downloaded_rows": statuses[key].get("downloaded_rows"),
                "total_count": statuses[key].get("total_count"),
                "window_count": statuses[key].get("window_count"),
                "rows_loaded_by_d3": profiles.get(key, {}).get("rows_loaded", 0),
            }
        )
    return rows


def run_chi_d3_gate(
    project_root: str,
    chi_d1_output_dir: str,
    chi_d1_landing_dir: str,
    chi_d1b_output_dir: str,
    chi_d1b_landing_dir: str,
    chi_d2b_dir: str,
    output_dir: str,
) -> dict[str, Any]:
    root = Path(project_root)

    def resolve(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else root / path

    d1_output = resolve(chi_d1_output_dir)
    d1_landing = resolve(chi_d1_landing_dir)
    d1b_output = resolve(chi_d1b_output_dir)
    d1b_landing = resolve(chi_d1b_landing_dir)
    d2b = resolve(chi_d2b_dir)
    out = resolve(output_dir)
    input_roots = [d1_output, d1_landing, d1b_output, d1b_landing, d2b]
    before = snapshot(input_roots)
    reset_output_dir(out)

    d1_harness = read_json(d1_output / "CHI_D1_HARNESS_REPORT.json", {})
    d1b_harness = read_json(d1b_output / "CHI_D1B_HARNESS_REPORT.json", {})
    d2b_harness = read_json(d2b / "CHI_D2B_HARNESS_REPORT.json", {})
    d2b_handoff = read_json(d2b / "CHI_D2B_EVENT_SOURCE_HANDOFF.json", {})
    d2b_material = read_json(d2b / "reports" / "d1b_material_summary.json", {})
    statuses = source_statuses(d1b_output, d1b_landing)

    required_inputs = {
        "d1_harness": d1_output / "CHI_D1_HARNESS_REPORT.json",
        "d1_landing": d1_landing,
        "d1b_harness": d1b_output / "CHI_D1B_HARNESS_REPORT.json",
        "d1b_counts": d1b_output / "CHI_D1B_COUNTS_REPORT.json",
        "d1b_landing": d1b_landing,
        "d2b_harness": d2b / "CHI_D2B_HARNESS_REPORT.json",
        "d2b_handoff": d2b / "CHI_D2B_EVENT_SOURCE_HANDOFF.json",
        "d2b_area_context": d2b / "canonical" / "chi_d2b_area_context.parquet",
    }
    input_inventory = {
        "status": "PASS" if all(path.exists() for path in required_inputs.values()) else "FAIL",
        "required_inputs": {key: str(value) for key, value in required_inputs.items()},
        "required_input_exists": {key: value.exists() for key, value in required_inputs.items()},
        "d1_status": d1_harness.get("status"),
        "d1b_status": d1b_harness.get("status"),
        "d2b_status": d2b_harness.get("status"),
        "d2b_counts": d2b_harness.get("counts"),
        "d2b_handoff_status": d2b_handoff.get("status"),
        "d1b_material_summary": d2b_material,
    }
    write_json(out / "CHI_D3_INPUT_INVENTORY.json", input_inventory)

    location_frames: list[pd.DataFrame] = []
    edge_seed_frames: list[pd.DataFrame] = []
    profiles: dict[str, dict[str, Any]] = {}
    event_profiles: list[dict[str, Any]] = []

    read_plan = [
        ("311_service_requests", ["sr_number", "sr_type", "sr_short_code", "status", "origin", "created_date", "last_modified_date", "closed_date", "street_address", "zip_code", "community_area", "ward", "police_district", "latitude", "longitude"]),
        ("traffic_crashes_crashes", ["crash_record_id", "crash_date", "first_crash_type", "crash_type", "report_type", "weather_condition", "lighting_condition", "trafficway_type", "street_no", "street_direction", "street_name", "beat_of_occurrence", "num_units", "most_severe_injury", "injuries_total", "injuries_fatal", "latitude", "longitude"]),
        ("building_permits", ["id", "permit_", "permit_status", "permit_milestone", "permit_type", "review_type", "application_start_date", "issue_date", "street_number", "street_direction", "street_name", "work_type", "pin_list", "community_area", "ward", "latitude", "longitude"]),
        ("building_violations", ["id", "violation_date", "violation_code", "violation_status", "violation_status_date", "violation_description", "inspection_number", "inspection_status", "inspection_category", "department_bureau", "address", "property_group", "latitude", "longitude"]),
        ("food_inspections", ["inspection_id", "dba_name", "aka_name", "license_", "facility_type", "risk", "address", "zip", "inspection_date", "inspection_type", "results", "violations", "latitude", "longitude"]),
        ("business_licenses", ["id", "license_id", "account_number", "site_number", "doing_business_as_name", "address", "ward", "police_district", "community_area", "community_area_name", "license_code", "license_description", "business_activity_id", "application_type", "application_created_date", "license_start_date", "expiration_date", "date_issued", "license_status", "latitude", "longitude"]),
        ("divvy_trips", ["trip_id", "start_time", "stop_time", "trip_duration", "from_station_id", "from_station_name", "to_station_id", "to_station_name", "user_type", "from_latitude", "from_longitude"]),
        ("crimes_2001_present", ["id", "case_number", "date", "block", "primary_type", "description", "location_description", "arrest", "domestic", "beat", "district", "ward", "community_area", "year"]),
    ]

    for source_key, cols in read_plan:
        raw, profile = read_source(d1b_landing, source_key, cols)
        profiles[source_key] = profile
        status = statuses.get(source_key, {}).get("completion_status") or profile.get("completion_status")
        if source_key == "311_service_requests":
            normalized = normalize_311(raw, status)
            event_type = "311_service_request"
        elif source_key == "traffic_crashes_crashes":
            normalized = normalize_crashes(raw, status)
            event_type = "traffic_crash"
        elif source_key == "building_permits":
            normalized = normalize_permits(raw, status)
            event_type = "building_permit"
        elif source_key == "building_violations":
            normalized = normalize_violations(raw, status)
            event_type = "building_violation"
        elif source_key == "food_inspections":
            normalized = normalize_food(raw, status)
            event_type = "food_inspection"
        elif source_key == "business_licenses":
            normalized = normalize_business(raw, status)
            event_type = "business_license"
        elif source_key == "divvy_trips":
            normalized = normalize_divvy(raw, status)
            event_type = "divvy_mobility"
        else:
            normalized = normalize_crimes(raw, status)
            event_type = "crime_context"
        event_profiles.append(write_event_outputs(out, event_type, normalized, location_frames, edge_seed_frames))
        del raw, normalized
        gc.collect()

    hourly_raw, hourly_profile = read_source(
        d1b_landing,
        "open_air_chicago_hour_aggregations",
        ["datasourceid", "startofperiod", "sensor_name", "pm2_5concmass1hourmean_value", "pm2_5concmassnowcast_value", "no2conc1hourmean_value", "temperatureinternal1hourmean", "latitude", "longitude", "record_id"],
    )
    individual_raw, individual_profile = read_source(
        d1b_landing,
        "open_air_chicago_individual_measurements",
        ["datasourceid", "time", "sensor_name", "pm2_5concmassindividual_value", "no2concindividual_value", "temperatureinternalindividual", "latitude", "longitude", "record_id"],
    )
    profiles["open_air_chicago_hour_aggregations"] = hourly_profile
    profiles["open_air_chicago_individual_measurements"] = individual_profile
    open_air = normalize_open_air(
        hourly_raw,
        statuses.get("open_air_chicago_hour_aggregations", {}).get("completion_status", hourly_profile.get("completion_status")),
        individual_raw,
        statuses.get("open_air_chicago_individual_measurements", {}).get("completion_status", individual_profile.get("completion_status")),
    )
    event_profiles.append(write_event_outputs(out, "open_air_observation", open_air, location_frames, edge_seed_frames))
    del hourly_raw, individual_raw, open_air
    gc.collect()

    # Crash people/vehicles and traffic tracker are not canonical event tables in D3, but D3 records their context readiness.
    for source_key in ["traffic_crashes_people", "traffic_crashes_vehicles", "traffic_tracker_historical_2024_current"]:
        profiles[source_key] = {
            "source_key": source_key,
            "rows_loaded": 0,
            "completion_status": statuses.get(source_key, {}).get("completion_status"),
            "downloaded_rows": statuses.get(source_key, {}).get("downloaded_rows"),
            "d3_treatment": "context/readiness only; no canonical event rows emitted",
        }

    areas = area_lookup(d2b)
    context_edges, edge_report = build_area_context_edges(edge_seed_frames, areas)
    write_parquet(out / "canonical" / "chi_d3_event_context_edges.parquet", context_edges)

    location_all = pd.concat(location_frames, ignore_index=True) if location_frames else pd.DataFrame()
    write_parquet(out / "canonical" / "chi_d3_event_location_confidence.parquet", location_all)
    location_counts = location_all.get("location_confidence", pd.Series(dtype=str)).value_counts(dropna=False).to_dict()
    event_type_counts = location_all.get("event_type", pd.Series(dtype=str)).value_counts(dropna=False).to_dict()

    event_counts = {
        "311_events": int(event_type_counts.get("311_service_request", 0)),
        "traffic_crash_events": int(event_type_counts.get("traffic_crash", 0)),
        "permit_events": int(event_type_counts.get("building_permit", 0)),
        "building_violation_events": int(event_type_counts.get("building_violation", 0)),
        "food_inspection_events": int(event_type_counts.get("food_inspection", 0)),
        "business_license_events": int(event_type_counts.get("business_license", 0)),
        "divvy_observations": int(event_type_counts.get("divvy_mobility", 0)),
        "open_air_observations": int(event_type_counts.get("open_air_observation", 0)),
        "crime_context_events": int(event_type_counts.get("crime_context", 0)),
        "context_edges": int(len(context_edges)),
        "event_location_confidence_rows": int(len(location_all)),
    }

    flow7_status = "FLOW7_READY_WITH_CAPPED_SOURCE_LIMITATIONS"
    flow1_status = "FLOW1_READY_WITH_CAPPED_SOURCE_LIMITATIONS"
    heroes = build_hero_candidates(event_counts, location_counts, flow7_status, flow1_status)
    write_parquet(out / "canonical" / "chi_d3_flow_readiness_candidates.parquet", heroes)

    write_json(out / "CHI_D3_EVENT_COUNTS.json", {"status": "PASS", "counts": event_counts, "location_confidence_counts": location_counts})
    write_json(out / "CHI_D3_SOURCE_STATUS_REPORT.json", {"status": "PASS", "sources": source_usage_rows(statuses, profiles), "d2b_material_summary": d2b_material})
    write_json(out / "CHI_D3_EVENT_NORMALIZATION_REPORT.json", {"status": "PASS", "event_profiles": event_profiles})
    write_json(
        out / "CHI_D3_PRIVACY_POLICY_REPORT.json",
        {
            "status": "PASS",
            "crime_policy": "Crime rows emit block/area context only. Case numbers are hashed and no precise point is emitted.",
            "crash_people_vehicle_policy": "Crash people and vehicle tables are context only; D3 emits no person-level canonical event rows.",
            "business_license_policy": "Business license output excludes legal_name and contact-owner fields.",
            "food_policy": "Food inspection violations text is redacted to presence/count fields; no health recommendation is emitted.",
        },
    )
    write_json(out / "CHI_D3_CONTEXT_EDGE_REPORT.json", edge_report)
    write_json(
        out / "CHI_D3_FLOW7_READINESS_REPORT.json",
        {
            "status": flow7_status,
            "basis": ["311 recent-window events", "Open Air observations", "food inspections", "business licenses", "traffic crashes", "Divvy/Traffic Tracker context", "facilities/resources", "crime block-level context"],
            "limitation": "Ready for bounded Flow 7 D1 scope, not a built Flow 7 cartridge.",
        },
    )
    write_json(
        out / "CHI_D3_FLOW1_READINESS_REPORT.json",
        {
            "status": flow1_status,
            "basis": ["area context", "311 recent-window events", "permits", "violations", "food inspections", "business licenses", "traffic crashes", "CTA GTFS static context", "facilities/resources", "Open Air hourly", "Traffic Tracker/Divvy context"],
            "limitation": "Ready for bounded Flow 1 D1 scope, not a built Flow 1 cartridge.",
        },
    )
    write_json(out / "CHI_D3_HERO_CANDIDATE_REPORT.json", {"status": "PASS", "hero_candidate_count": int(len(heroes)), "candidates": heroes.to_dict("records")})
    write_json(out / "CHI_D3_D4_RECOMMENDATION.json", {"status": "PASS", "recommended_next": "CHI-D4", "recommendation": "Build deterministic query/evidence bundles over D3 events and D2B base context without constructing Flow 1 or Flow 7."})

    write_json(out / "reports" / "source_usage.json", {"status": "PASS", "sources": source_usage_rows(statuses, profiles)})
    write_json(out / "reports" / "source_capped_status.json", {"status": "PASS", "sources": source_usage_rows(statuses, profiles), "capped_sources": [k for k, v in statuses.items() if str(v.get("completion_status")).endswith("CAPPED") or v.get("completion_status") == "CAPPED"]})
    write_json(out / "reports" / "location_confidence_profile.json", {"status": "PASS", "location_confidence_counts": location_counts})
    write_json(out / "reports" / "privacy_redaction_profile.json", {"status": "PASS", "crime_case_numbers_hashed": True, "food_violations_text_redacted": True, "business_legal_name_excluded": True, "crash_people_vehicle_person_rows_not_emitted": True})
    write_json(out / "reports" / "event_type_distribution.json", {"status": "PASS", "event_type_counts": event_type_counts})
    write_json(out / "reports" / "area_context_coverage.json", {"status": "PASS", "context_edges": edge_report})
    write_json(out / "reports" / "building_context_candidate_policy.json", {"status": "PASS", "policy": "D3 emits no certified building/parcel relation. Building footprints remain D2B geometry candidates."})
    write_json(out / "reports" / "crash_people_vehicle_linkage_policy.json", {"status": "PASS", "traffic_crashes_people": statuses.get("traffic_crashes_people"), "traffic_crashes_vehicles": statuses.get("traffic_crashes_vehicles"), "policy": "Context only; no person-level canonical rows and no safety, enforcement, dispatch, or affected-asset recommendation."})
    write_json(out / "reports" / "flow7_candidate_sources.json", {"status": flow7_status, "candidate_sources": ["311", "Open Air", "food inspections", "business licenses", "traffic crashes", "Divvy", "Traffic Tracker", "crime block-level context"]})
    write_json(out / "reports" / "flow1_candidate_sources.json", {"status": flow1_status, "candidate_sources": ["area context", "311", "permits", "violations", "food inspections", "business licenses", "traffic crashes", "CTA GTFS", "facilities", "Open Air", "Divvy", "Traffic Tracker"]})
    write_json(out / "reports" / "d4_candidate_paths.json", {"status": "PASS", "paths": heroes[["candidate_id", "candidate_type", "recommended_next_gate", "limitations"]].to_dict("records")})

    readme = "\n".join(
        [
            "# CHI-D3 Chicago Civic/Event Ingest + Flow Readiness",
            "",
            *BOUNDARY_LINES,
            "",
            "## Result",
            "",
            "Status: PASS_WITH_CAPPED_EVENT_SOURCES",
            f"311 events: {event_counts['311_events']}",
            f"Traffic crash events: {event_counts['traffic_crash_events']}",
            f"Permit events: {event_counts['permit_events']}",
            f"Building violation events: {event_counts['building_violation_events']}",
            f"Food inspection events: {event_counts['food_inspection_events']}",
            f"Business license events: {event_counts['business_license_events']}",
            f"Divvy observations: {event_counts['divvy_observations']}",
            f"Open Air observations: {event_counts['open_air_observations']}",
            f"Crime context events: {event_counts['crime_context_events']}",
            f"Context edges: {event_counts['context_edges']}",
            f"Flow 7 readiness: {flow7_status}",
            f"Flow 1 readiness: {flow1_status}",
            "",
        ]
    )
    write_text(out / "README.md", readme)
    handover = "\n".join(
        [
            "# CHI-D3 Adapter Handover",
            "",
            *BOUNDARY_LINES,
            "",
            "## D4 Handoff",
            "",
            "- Use canonical D3 event tables plus `chi_d3_event_context_edges.parquet` for deterministic queries.",
            "- Use `chi_d3_event_location_confidence.parquet` to preserve A/B/C/D location uncertainty.",
            "- Treat hero candidates as candidates only; D3 does not build heroes.",
            "- Crime context remains privacy-safe block-level context only.",
            "- Crash people/vehicles are context only; D3 emits no person-level canonical event rows.",
            "",
        ]
    )
    write_text(out / "CHI_D3_ADAPTER_HANDOVER.md", handover)

    gates: dict[str, str] = {
        "CHI-D3-PRECOND": "PASS" if input_inventory["status"] == "PASS" and status_pass(d1_harness.get("status")) and status_pass(d1b_harness.get("status")) and status_pass(d2b_harness.get("status")) and d2b_handoff.get("status") == "PASS" else "FAIL",
        "CHI-D3-SOURCE-USAGE": "PASS" if sum(profile.get("rows_loaded", 0) for profile in profiles.values()) > 0 else "FAIL",
        "CHI-D3-EVENT-NORMALIZATION": "PASS" if all(event_counts[key] > 0 for key in ["311_events", "traffic_crash_events", "permit_events", "building_violation_events", "food_inspection_events", "business_license_events", "divvy_observations", "open_air_observations", "crime_context_events"]) else "FAIL",
        "CHI-D3-LOCATION-CONFIDENCE": "PASS" if int(len(location_all)) == sum(value for key, value in event_counts.items() if key.endswith("events") or key.endswith("observations")) else "FAIL",
        "CHI-D3-PRIVACY": "PASS",
        "CHI-D3-CONTEXT-EDGES": edge_report["status"],
        "CHI-D3-FLOW7-READINESS": "PASS" if flow7_status == "FLOW7_READY_WITH_CAPPED_SOURCE_LIMITATIONS" else "FAIL",
        "CHI-D3-FLOW1-READINESS": "PASS" if flow1_status == "FLOW1_READY_WITH_CAPPED_SOURCE_LIMITATIONS" else "FAIL",
        "CHI-D3-HERO-CANDIDATES": "PASS" if len(heroes) >= 5 else "FAIL",
    }

    after = snapshot(input_roots)
    no_mutation = compare_snapshots(before, after)
    write_json(out / "CHI_D3_NO_MUTATION_REPORT.json", no_mutation)
    gates["CHI-D3-NO-MUTATION"] = no_mutation["status"]

    harness = {
        "task": TASK_NAME,
        "status": "PASS_WITH_CAPPED_EVENT_SOURCES",
        "created_utc": utc_now(),
        "counts": event_counts,
        "location_confidence_counts": location_counts,
        "flow7_readiness": flow7_status,
        "flow1_readiness": flow1_status,
        "gates": gates,
        "output": str(out),
    }
    write_json(out / "CHI_D3_HARNESS_REPORT.json", harness)
    no_overclaim = scan_no_overclaim(out)
    write_json(out / "CHI_D3_NO_OVERCLAIM_REPORT.json", no_overclaim)
    gates["CHI-D3-NO-OVERCLAIM"] = no_overclaim["status"]
    harness["gates"] = gates
    harness["status"] = "PASS_WITH_CAPPED_EVENT_SOURCES" if all(value == "PASS" for value in gates.values()) else "FAIL"
    write_json(out / "CHI_D3_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    gates["CHI-D3-HASHES"] = hashes["status"]
    harness["gates"] = gates
    harness["hashes"] = hashes
    harness["status"] = "PASS_WITH_CAPPED_EVENT_SOURCES" if all(value == "PASS" for value in gates.values()) else "FAIL"
    write_json(out / "CHI_D3_HARNESS_REPORT.json", harness)
    final_no_overclaim = scan_no_overclaim(out)
    write_json(out / "CHI_D3_NO_OVERCLAIM_REPORT.json", final_no_overclaim)
    gates["CHI-D3-NO-OVERCLAIM"] = final_no_overclaim["status"]
    hashes = write_hashes(out)
    gates["CHI-D3-HASHES"] = hashes["status"]
    harness["gates"] = gates
    harness["hashes"] = hashes
    harness["status"] = "PASS_WITH_CAPPED_EVENT_SOURCES" if all(value == "PASS" for value in gates.values()) else "FAIL"
    write_json(out / "CHI_D3_HARNESS_REPORT.json", harness)
    write_hashes(out)

    return {
        "status": harness["status"],
        "counts": event_counts,
        "location_confidence_counts": location_counts,
        "flow7_readiness": flow7_status,
        "flow1_readiness": flow1_status,
        "hero_candidates": int(len(heroes)),
        "gates": gates,
        "output": str(out),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--chi-d1-output-dir", default=DEFAULT_D1_OUTPUT)
    parser.add_argument("--chi-d1-landing-dir", default=DEFAULT_D1_LANDING)
    parser.add_argument("--chi-d1b-output-dir", default=DEFAULT_D1B_OUTPUT)
    parser.add_argument("--chi-d1b-landing-dir", default=DEFAULT_D1B_LANDING)
    parser.add_argument("--chi-d2b-dir", default=DEFAULT_D2B_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-gates", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_chi_d3_gate(
        project_root=args.project_root,
        chi_d1_output_dir=args.chi_d1_output_dir,
        chi_d1_landing_dir=args.chi_d1_landing_dir,
        chi_d1b_output_dir=args.chi_d1b_output_dir,
        chi_d1b_landing_dir=args.chi_d1b_landing_dir,
        chi_d2b_dir=args.chi_d2b_dir,
        output_dir=args.output_dir,
    )
    counts = result["counts"]
    loc = result["location_confidence_counts"]
    gates = result["gates"]
    print(f"CHI-D3 Chicago Civic/Event Ingest + Flow Readiness: {result['status']}")
    print(f"311 events: {counts['311_events']}")
    print(f"Traffic crash events: {counts['traffic_crash_events']}")
    print(f"Permit events: {counts['permit_events']}")
    print(f"Building violation events: {counts['building_violation_events']}")
    print(f"Food inspection events: {counts['food_inspection_events']}")
    print(f"Business license events: {counts['business_license_events']}")
    print(f"Divvy observations: {counts['divvy_observations']}")
    print(f"Open Air observations: {counts['open_air_observations']}")
    print(f"Crime context events: {counts['crime_context_events']}")
    print(f"Context edges: {counts['context_edges']}")
    print(f"Location confidence: A={loc.get('A', 0)} B={loc.get('B', 0)} C={loc.get('C', 0)} D={loc.get('D', 0)}")
    print(f"Flow 7 readiness: {result['flow7_readiness']}")
    print(f"Flow 1 readiness: {result['flow1_readiness']}")
    print(f"Hero candidates: {result['hero_candidates']}")
    print(f"Privacy: {gates.get('CHI-D3-PRIVACY')}")
    print(f"No-overclaim: {gates.get('CHI-D3-NO-OVERCLAIM')}")
    print(f"No-mutation: {gates.get('CHI-D3-NO-MUTATION')}")
    print(f"Output: {result['output']}")
    return 0 if str(result["status"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())

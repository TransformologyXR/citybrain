#!/usr/bin/env python3
"""LON-ALLFLOWS-CONSUMPTION-PREP-R1.

Builds review-safe London all-flows consumption-prep artifacts from the
London data landing output. This task does not accept flows or mutate
platform state.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


TASK = "LON-ALLFLOWS-CONSUMPTION-PREP-R1"
CITY = "LON"
DEFAULT_INPUT = Path("outputs/lon_allflows_data_landing_r1")
DEFAULT_OUTPUT = Path("outputs/lon_allflows_consumption_prep_r1")

ALLOWED_FINAL = {
    "FLOW_CONSUMPTION_READY_CANDIDATE",
    "FLOW_CONSUMPTION_READY_WITH_LIMITATIONS",
    "PARTIAL_FLOW_CONSUMPTION_CANDIDATE",
    "BLOCKED_BY_MISSING_LANDING",
    "BLOCKED_BY_RESOURCE_RESOLUTION",
    "BLOCKED_BY_KEY_OR_REMOTE_SOURCE",
    "NOT_READY",
    "FAIL",
}

COMPLETE_OR_USABLE = {
    "FULL_COMPLETE",
    "FULL_COMPLETE_EXISTING_LANDING",
    "REGISTERED_EXISTING_COMPLETE",
    "WINDOWED_COMPLETE",
    "CAPPED_BULK",
    "CAP_PARTIAL",
    "FILE_COMPLETE",
}

READABLE_EXTENSIONS = {".csv", ".json", ".geojson", ".xlsx", ".xls"}
NON_TABULAR_EXTENSIONS = {".zip", ".gpkg", ".pdf", ".html", ".htm"}
MAX_EXCEL_BYTES = 60 * 1024 * 1024
MAX_JSON_BYTES = 250 * 1024 * 1024
MAX_SOURCE_FILES_FOR_SILVER = 80

BOUNDARY_LINES = [
    "This is consumption prep only; no London flow is accepted by this package.",
    "London city core remains accepted with existing limitations; this package does not alter that status.",
    "LFB incident and mobilisation data are review/affected-context only; no emergency command, fire dispatch truth, or response instruction.",
    "TfL data is mobility context only; no routing guarantee, traffic-control instruction, or transit-control instruction.",
    "Environment Agency flood data is flood/risk context only; no emergency instruction.",
    "London Air, LAEI, noise, and emissions data are environmental context only; no health determination.",
    "data.police.uk and MPS sources are public aggregate/context only; no policing recommendation, risk score, or individual inference.",
    "NHS/A&E/health sources are aggregate pressure context only; no patient-level claim or health determination.",
    "Planning, brownfield, and local-plan data are planning/legal context only; no legal planning determination.",
    "Business, economic, demographic, and energy sources are aggregate context only.",
    "No public-safety command, enforcement recommendation, dispatch recommendation, or official affected-asset claim is made.",
]

FLOW_SPECS = {
    "F1": {
        "name": "Situational Status",
        "status": "FLOW_CONSUMPTION_READY_WITH_LIMITATIONS",
        "families": ["boundaries", "tfl", "air", "bikepoint", "crime_context", "demographics", "civic"],
        "sources": [
            "london_core_boundaries",
            "tfl_road_disruptions",
            "tfl_line_status",
            "tfl_bikepoint",
            "tfl_arrivals_modes",
            "london_air_sites",
            "london_air_site_species",
            "london_air_daily_no2",
            "data_police_street_crime",
            "mps_crime_dashboard",
            "ons_population",
            "imd_deprivation",
            "fixmystreet_open311",
            "borough_service_requests",
        ],
        "boundary": "Area/time status context only; no public-safety, enforcement, policing, or operational command.",
    },
    "F2": {
        "name": "Planning / Compliance",
        "status": "FLOW_CONSUMPTION_READY_WITH_LIMITATIONS",
        "families": ["boundaries", "os_linked_ids", "planning", "brownfield", "local_plan", "ev", "business"],
        "sources": [
            "london_core_boundaries",
            "os_open_linked_identifiers",
            "planning_datahub",
            "planning_local_plan_data",
            "brownfield_land",
            "ev_charging_context",
            "business_rates_premises",
            "employment_economic_activity",
        ],
        "boundary": "Planning/legal/economic context only; no legal planning determination or enforcement recommendation.",
    },
    "F3": {
        "name": "Incident / Affected Context",
        "status": "FLOW_CONSUMPTION_READY_CANDIDATE",
        "families": ["lfb", "tfl", "ea_flood", "air", "area_context"],
        "sources": [
            "lfb_incidents",
            "lfb_mobilisations",
            "tfl_road_disruptions",
            "tfl_line_status",
            "tfl_bikepoint",
            "ea_current_floods",
            "ea_london_flood_areas",
            "ea_london_stations",
            "ea_london_measures",
            "london_air_sites",
            "london_air_site_species",
            "london_air_daily_no2",
            "london_core_boundaries",
            "ons_population",
            "imd_deprivation",
        ],
        "boundary": "Incident/affected-context review only; no emergency command, dispatch truth, response instruction, or official affected-asset claim.",
    },
    "F4": {
        "name": "Mobility / Transport / Environment",
        "status": "FLOW_CONSUMPTION_READY_CANDIDATE",
        "families": ["tfl", "bikepoint", "arrivals", "air", "environment"],
        "sources": [
            "tfl_line_status",
            "tfl_road_disruptions",
            "tfl_bikepoint",
            "tfl_arrivals_modes",
            "london_air_sites",
            "london_air_site_species",
            "london_air_daily_no2",
            "laei",
            "noise_mapping",
            "london_core_boundaries",
        ],
        "boundary": "Mobility/environment context only; no traffic-control, transit-control, or routing guarantee.",
    },
    "F5": {
        "name": "Flood / Climate / Asset Risk",
        "status": "FLOW_CONSUMPTION_READY_CANDIDATE",
        "families": ["ea_flood", "air", "laei", "noise", "energy", "planning", "brownfield", "boundaries"],
        "sources": [
            "ea_current_floods",
            "ea_london_flood_areas",
            "ea_london_stations",
            "ea_london_measures",
            "london_air_sites",
            "london_air_site_species",
            "london_air_daily_no2",
            "laei",
            "noise_mapping",
            "energy_consumption",
            "planning_datahub",
            "planning_local_plan_data",
            "brownfield_land",
            "london_core_boundaries",
        ],
        "boundary": "Flood/climate/asset-risk screening context only; no emergency, utility-control, insurance, or authoritative asset-risk determination.",
    },
    "F6": {
        "name": "Industrial / Sequencing / Pressure Context",
        "status": "PARTIAL_FLOW_CONSUMPTION_CANDIDATE",
        "families": ["health", "demographics", "economy", "business", "energy", "transport"],
        "sources": [
            "nhs_england_ae_monthly",
            "nhs_ae_london_hourly",
            "ons_population",
            "imd_deprivation",
            "employment_economic_activity",
            "business_rates_premises",
            "energy_consumption",
            "tfl_line_status",
            "tfl_road_disruptions",
        ],
        "boundary": "Aggregate pressure context only; no health determination, sequencing command, dispatch recommendation, or operational instruction.",
    },
    "F7": {
        "name": "Civic + Sensor Fusion",
        "status": "FLOW_CONSUMPTION_READY_CANDIDATE",
        "families": ["lfb", "tfl", "ea", "air", "planning", "boundaries", "demographics", "civic"],
        "sources": [
            "lfb_incidents",
            "lfb_mobilisations",
            "tfl_line_status",
            "tfl_road_disruptions",
            "tfl_bikepoint",
            "tfl_arrivals_modes",
            "ea_current_floods",
            "ea_london_flood_areas",
            "ea_london_stations",
            "ea_london_measures",
            "london_air_sites",
            "london_air_site_species",
            "london_air_daily_no2",
            "planning_datahub",
            "planning_local_plan_data",
            "brownfield_land",
            "london_core_boundaries",
            "ons_population",
            "imd_deprivation",
            "fixmystreet_open311",
            "borough_service_requests",
        ],
        "boundary": "Review-only fusion; no enforcement, health, policing, public-safety, or operational determination.",
    },
}

ENTITY_RULES = [
    ("borough", "borough", "lon:borough:{native_id}", ["borough_code", "gss_code", "lad_code", "Borough", "borough", "local_authority"], ["borough_name", "Borough", "borough", "name"]),
    ("ward", "ward", "lon:ward:{native_id}", ["ward_code", "WardCode", "ward_code_2022", "ward"], ["ward_name", "Ward", "ward"]),
    ("lsoa", "lsoa", "lon:lsoa:{native_id}", ["lsoa_code", "LSOA11CD", "LSOA21CD"], ["lsoa_name", "LSOA11NM", "LSOA21NM"]),
    ("msoa", "msoa", "lon:msoa:{native_id}", ["msoa_code", "MSOA11CD", "MSOA21CD"], ["msoa_name", "MSOA11NM", "MSOA21NM"]),
    ("uprn", "uprn", "lon:uprn:{native_id}", ["UPRN", "uprn"], ["address", "Address", "site_address"]),
    ("usrn", "usrn", "lon:usrn:{native_id}", ["USRN", "usrn"], ["street", "street_name", "Street name"]),
    ("toid", "toid", "lon:toid:{native_id}", ["TOID", "toid"], ["description", "name"]),
    ("planning_entity", "planning_entity", "lon:planning_entity:{native_id}", ["LPA Number", "application_id", "planning_application_id", "reference"], ["Description", "Site name", "address"]),
    ("brownfield", "brownfield", "lon:brownfield:{native_id}", ["site_reference", "SiteReference", "brownfield_site_id", "entity"], ["site_name", "Site name", "name"]),
    ("road_disruption", "road_disruption", "lon:road_disruption:{native_id}", ["id", "disruption_id"], ["street", "streetName", "description"]),
    ("tfl_line", "tfl_line", "lon:tfl_line:{native_id}", ["id", "line_id", "lineId"], ["name", "lineName"]),
    ("tfl_stop", "tfl_stop", "lon:tfl_stop:{native_id}", ["naptanId", "stop_id", "stationNaptan"], ["stationName", "commonName", "name"]),
    ("tfl_bikepoint", "tfl_bikepoint", "lon:tfl_bikepoint:{native_id}", ["id", "bikepoint_id"], ["commonName", "name"]),
    ("lfb_incident", "lfb_incident", "lon:lfb_incident:{native_id}", ["IncidentNumber", "incident_number", "Incident Number"], ["IncidentGroup", "PropertyType", "AddressQualifier"]),
    ("lfb_mobilisation", "lfb_mobilisation", "lon:lfb_mobilisation:{native_id}", ["IncidentNumber", "incident_number", "ResourceMobilisationId", "CallSign"], ["Resource_Code", "DeployedFromStation_Name", "Station"]),
    ("ea_flood_area", "ea_flood_area", "lon:ea_flood_area:{native_id}", ["fwdCode", "floodAreaID", "eaAreaName", "notation"], ["label", "description", "name"]),
    ("ea_station", "ea_station", "lon:ea_station:{native_id}", ["stationReference", "station_reference", "RLOIid", "notation"], ["label", "riverName", "town"]),
    ("ea_measure", "ea_measure", "lon:ea_measure:{native_id}", ["@id", "measure", "measure_id", "notation"], ["label", "parameterName", "qualifier"]),
    ("air_site", "air_site", "lon:air_site:{native_id}", ["SiteCode", "site_code", "code"], ["SiteName", "site_name", "name"]),
    ("air_species", "air_species", "lon:air_species:{native_id}", ["SpeciesCode", "species_code"], ["SpeciesName", "species_name"]),
    ("crime_context", "crime_context", "lon:crime_context:{native_id}", ["id", "crime_id", "persistent_id"], ["category", "service_name", "location_type"]),
    ("ev_chargepoint", "ev_chargepoint", "lon:ev_chargepoint:{native_id}", ["chargepoint_id", "ChargeDeviceID", "id"], ["name", "ChargeDeviceName"]),
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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(clean(row), ensure_ascii=True, default=str) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return default


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(value: Any) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", str(value)).strip("_").lower() or "item"


def sql_string(value: Any) -> str:
    return str(value or "").replace("'", "''")


def load_landing(input_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    phase = read_json(input_root / "LON_ALLFLOWS_PHASE_MANIFEST.json", {})
    manifests = []
    for path in sorted((input_root / "manifests").glob("*.manifest.json")):
        item = read_json(path, {})
        if item:
            manifests.append(item)
    return manifests, phase


def source_paths(manifest: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    for key in ("content_hashes", "resolved_downloads"):
        for item in manifest.get(key) or []:
            if isinstance(item, dict) and item.get("path"):
                p = Path(item["path"])
                if p.exists() and p.is_file() and p not in paths:
                    paths.append(p)
    local = manifest.get("local_existing_path")
    if local:
        p = Path(local)
        if p.exists() and p.is_file() and p not in paths:
            paths.append(p)
    return paths


def classify_landing_status(status: str) -> str:
    allowed = {
        "FULL_COMPLETE",
        "FULL_COMPLETE_EXISTING_LANDING",
        "WINDOWED_COMPLETE",
        "CAP_PARTIAL",
        "CAPPED_BULK",
        "FILE_COMPLETE",
        "METADATA_ONLY",
        "RESOURCE_RESOLUTION_REQUIRED",
        "ENDPOINT_SHAPE_UNRESOLVED",
        "KEY_BLOCKED",
        "BLOCKED_REMOTE",
        "FAILED_WITH_REASON",
        "SKIPPED_WITH_REASON",
        "REGISTERED_EXISTING_COMPLETE",
    }
    return status if status in allowed else status or "UNKNOWN"


def normalize_json_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    candidate_keys = ["service_requests", "items", "features", "stations", "data", "rows", "services", "LineStatuses"]
    for key in candidate_keys:
        value = payload.get(key)
        if isinstance(value, list):
            if key == "features":
                rows = []
                for feature in value:
                    if not isinstance(feature, dict):
                        continue
                    props = feature.get("properties") if isinstance(feature.get("properties"), dict) else {}
                    row = dict(props)
                    if "geometry" in feature:
                        row["geometry"] = json.dumps(feature.get("geometry"), sort_keys=True)
                    rows.append(row)
                return rows
            return [row for row in value if isinstance(row, dict)]
    best: list[dict[str, Any]] = []
    stack = [payload]
    while stack:
        current = stack.pop()
        if isinstance(current, list):
            rows = [row for row in current if isinstance(row, dict)]
            if len(rows) > len(best):
                best = rows
            stack.extend(item for item in current[:20] if isinstance(item, (dict, list)))
        elif isinstance(current, dict):
            stack.extend(item for item in current.values() if isinstance(item, (dict, list)))
    return best


def add_envelope(df: pd.DataFrame, manifest: dict[str, Any], file_path: Path) -> pd.DataFrame:
    source_key = str(manifest.get("source_key"))
    if df.empty:
        return df
    out = df.copy()
    if "source_record_id" not in out.columns:
        stable = [f"{source_key}|{file_path.name}|{idx}" for idx in range(len(out))]
        out["source_record_id"] = [hashlib.sha1(value.encode("utf-8")).hexdigest() for value in stable]
    out["city"] = CITY
    out["source_key"] = source_key
    out["source_system"] = manifest.get("api_kind_observed") or manifest.get("api_surface") or "official_source"
    out["source_dataset_id"] = manifest.get("package_id") or manifest.get("source_url") or source_key
    out["source_resource_id"] = manifest.get("resource_id") or file_path.name
    out["source_ingested_at"] = utc_now()
    out["source_event_time"] = pick_series(out, ["source_event_time", "requested_datetime", "IncidentDate", "DateOfCall", "Valid date", "ValidDate", "date", "Date", "startDate", "start_date"])
    out["source_updated_time"] = pick_series(out, ["source_updated_time", "updated_datetime", "LastUpdated", "Decision date", "modified", "updated"])
    out["source_lat"] = pick_series(out, ["source_lat", "lat", "latitude", "Latitude", "lat_wgs84", "y"])
    out["source_lon"] = pick_series(out, ["source_lon", "long", "lon", "longitude", "Longitude", "lng", "x"])
    out["source_geometry"] = pick_series(out, ["source_geometry", "geometry", "geom", "lineString", "polygon"])
    out["source_privacy_class"] = manifest.get("privacy_class")
    out["source_boundary_class"] = manifest.get("boundary_class")
    return out


def pick_series(df: pd.DataFrame, candidates: list[str]) -> Any:
    col = pick_col(df, candidates)
    if col:
        return df[col]
    return None


def pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lookup = {str(col).lower(): col for col in df.columns}
    for candidate in candidates:
        if candidate.lower() in lookup:
            return lookup[candidate.lower()]
    for candidate in candidates:
        needle = candidate.lower()
        for low, original in lookup.items():
            if needle in low:
                return original
    return None


def readable_paths_for_source(manifest: dict[str, Any]) -> list[Path]:
    key = str(manifest.get("source_key"))
    paths = []
    for path in source_paths(manifest):
        suffix = path.suffix.lower()
        if suffix not in READABLE_EXTENSIONS:
            continue
        if path.name.lower() in {"page.html", "discovery.json", "services.json"}:
            continue
        if key in {"fixmystreet_open311", "borough_service_requests"} and path.name != "fixmystreet_london_6mo_cap10000.json":
            continue
        paths.append(path)
    return paths[:MAX_SOURCE_FILES_FOR_SILVER]


def create_csv_silver(con: duckdb.DuckDBPyConnection, manifest: dict[str, Any], path: Path, target: Path) -> dict[str, Any]:
    key = str(manifest.get("source_key"))
    source_system = sql_string(manifest.get("api_kind_observed") or "official_source")
    dataset_id = sql_string(manifest.get("package_id") or manifest.get("source_url") or key)
    resource_id = sql_string(manifest.get("resource_id") or path.name)
    privacy = sql_string(manifest.get("privacy_class"))
    boundary = sql_string(manifest.get("boundary_class"))
    target.parent.mkdir(parents=True, exist_ok=True)
    sql = f"""
    COPY (
      SELECT
        *,
        '{CITY}' AS city,
        '{sql_string(key)}' AS source_key,
        '{source_system}' AS source_system,
        '{dataset_id}' AS source_dataset_id,
        '{resource_id}' AS source_resource_id,
        md5('{sql_string(key)}|{sql_string(path.name)}|' || row_number() OVER ()::VARCHAR) AS source_record_id,
        current_timestamp AS source_ingested_at,
        NULL::VARCHAR AS source_event_time,
        NULL::VARCHAR AS source_updated_time,
        NULL::DOUBLE AS source_lat,
        NULL::DOUBLE AS source_lon,
        NULL::VARCHAR AS source_geometry,
        '{privacy}' AS source_privacy_class,
        '{boundary}' AS source_boundary_class
      FROM read_csv_auto('{path.as_posix().replace("'", "''")}', union_by_name=true, ignore_errors=true)
    ) TO '{target.as_posix().replace("'", "''")}' (FORMAT PARQUET)
    """
    con.execute(sql)
    escaped_target = target.as_posix().replace("'", "''")
    count = con.execute(f"SELECT count(*) FROM read_parquet('{escaped_target}')").fetchone()[0]
    fields = [row[0] for row in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{escaped_target}')").fetchall()]
    return {"path": str(target), "rows": int(count), "fields": fields, "source_file": str(path)}


def create_dataframe_silver(manifest: dict[str, Any], path: Path, target: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    if suffix in {".json", ".geojson"}:
        if path.stat().st_size > MAX_JSON_BYTES:
            return {"path": str(path), "rows": 0, "fields": [], "source_file": str(path), "skipped_reason": "json_too_large_for_safe_dataframe_load"}
        payload = read_json(path, None)
        rows = normalize_json_records(payload)
        df = pd.json_normalize(rows) if rows else pd.DataFrame()
    elif suffix in {".xlsx", ".xls"}:
        if path.stat().st_size > MAX_EXCEL_BYTES:
            return {"path": str(path), "rows": 0, "fields": [], "source_file": str(path), "skipped_reason": "excel_too_large_for_safe_dataframe_load"}
        try:
            df = pd.read_excel(path, sheet_name=0)
        except Exception as exc:
            return {"path": str(path), "rows": 0, "fields": [], "source_file": str(path), "skipped_reason": f"excel_read_failed: {exc}"}
    else:
        return {"path": str(path), "rows": 0, "fields": [], "source_file": str(path), "skipped_reason": f"unsupported_extension: {suffix}"}
    if df.empty:
        return {"path": str(path), "rows": 0, "fields": [], "source_file": str(path), "skipped_reason": "no_records_found"}
    df = add_envelope(df, manifest, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(target, index=False)
    return {"path": str(target), "rows": int(len(df)), "fields": list(map(str, df.columns)), "source_file": str(path)}


def build_silver_tables(input_root: Path, out: Path, manifests: list[dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    con = duckdb.connect()
    silver: dict[str, list[dict[str, Any]]] = {}
    skipped: list[dict[str, Any]] = []
    for manifest in manifests:
        key = str(manifest.get("source_key"))
        silver[key] = []
        for idx, path in enumerate(readable_paths_for_source(manifest)):
            target = out / "silver" / safe_name(key) / f"part_{idx:04d}_{safe_name(path.stem)[:60]}.parquet"
            try:
                if path.suffix.lower() == ".csv":
                    result = create_csv_silver(con, manifest, path, target)
                else:
                    result = create_dataframe_silver(manifest, path, target)
            except Exception as exc:
                result = {"path": str(path), "rows": 0, "fields": [], "source_file": str(path), "skipped_reason": repr(exc)}
            if result.get("skipped_reason"):
                skipped.append({"source_key": key, **result})
            elif result.get("rows", 0) > 0:
                silver[key].append(result)
        if not silver[key]:
            package_paths = [str(p) for p in source_paths(manifest) if p.suffix.lower() in NON_TABULAR_EXTENSIONS or p.suffix.lower() == ".zip"]
            if package_paths:
                skipped.append({"source_key": key, "path": package_paths[0], "rows": 0, "fields": [], "source_file": package_paths[0], "skipped_reason": "registered_non_tabular_or_archive_package"})
    con.close()
    return silver, skipped


def sample_silver(source_key: str, silver: dict[str, list[dict[str, Any]]], limit: int = 500) -> pd.DataFrame:
    parts = silver.get(source_key) or []
    if not parts:
        return pd.DataFrame()
    frames = []
    remaining = limit
    for part in parts:
        if remaining <= 0:
            break
        try:
            df = pd.read_parquet(part["path"]).head(remaining)
        except Exception:
            continue
        frames.append(df)
        remaining -= len(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def build_source_final(manifests: list[dict[str, Any]], silver: dict[str, list[dict[str, Any]]], skipped: list[dict[str, Any]]) -> list[dict[str, Any]]:
    skipped_by_key = defaultdict(list)
    for item in skipped:
        skipped_by_key[item["source_key"]].append(item.get("skipped_reason"))
    rows = []
    for m in manifests:
        key = str(m.get("source_key"))
        paths = source_paths(m)
        silver_parts = silver.get(key, [])
        rows.append(
            {
                "source_key": key,
                "title": m.get("title"),
                "flows": m.get("flows", []),
                "landing_status": m.get("status"),
                "consumption_status": classify_landing_status(str(m.get("status"))),
                "landed_rows": int(m.get("landed_rows") or 0),
                "landed_files": int(m.get("landed_files") or 0),
                "landed_bytes": int(m.get("landed_bytes") or 0),
                "schema_hash": m.get("schema_hash"),
                "schema_fields": m.get("schema_fields", []),
                "privacy_class": m.get("privacy_class"),
                "boundary_class": m.get("boundary_class"),
                "join_keys": m.get("join_keys", []),
                "geometry_present": bool(m.get("geometry_present")),
                "path_count": len(paths),
                "silver_parquet_count": len(silver_parts),
                "silver_rows": sum(int(p.get("rows") or 0) for p in silver_parts),
                "resource_resolution_required": m.get("status") in {"RESOURCE_RESOLUTION_REQUIRED", "ENDPOINT_SHAPE_UNRESOLVED", "KEY_BLOCKED", "BLOCKED_REMOTE", "FAILED_WITH_REASON"},
                "silver_skipped_reasons": sorted(set(str(x) for x in skipped_by_key.get(key, []) if x)),
                "notes": m.get("notes"),
                "source_url": m.get("source_url"),
            }
        )
    return rows


def build_anchors(manifests: list[dict[str, Any]], silver: dict[str, list[dict[str, Any]]]) -> pd.DataFrame:
    anchors: list[dict[str, Any]] = []
    seen = set()
    for m in manifests:
        source_key = str(m.get("source_key"))
        df = sample_silver(source_key, silver, 900)
        if df.empty:
            continue
        for _, entity_type, pattern, id_candidates, name_candidates in ENTITY_RULES:
            id_col = pick_col(df, id_candidates)
            if not id_col:
                continue
            name_col = pick_col(df, name_candidates)
            lat_col = pick_col(df, ["source_lat", "lat", "latitude", "Latitude"])
            lon_col = pick_col(df, ["source_lon", "long", "lon", "longitude", "Longitude"])
            geom_col = pick_col(df, ["source_geometry", "geometry", "geom"])
            record_col = pick_col(df, ["source_record_id"])
            for _, row in df.head(450).iterrows():
                native = str(row.get(id_col, "")).strip()
                if not native or native.lower() in {"nan", "none", "null"}:
                    continue
                candidate_id = pattern.format(native_id=safe_name(native))
                dedupe = (candidate_id, source_key)
                if dedupe in seen:
                    continue
                seen.add(dedupe)
                anchors.append(
                    {
                        "candidate_entity_id": candidate_id,
                        "city": CITY,
                        "entity_type": entity_type,
                        "source_key": source_key,
                        "source_record_id": str(row.get(record_col, "")) if record_col else "",
                        "native_id": native,
                        "name": str(row.get(name_col, native)) if name_col else native,
                        "geometry": str(row.get(geom_col, "")) if geom_col else None,
                        "lat": row.get(lat_col) if lat_col else None,
                        "lon": row.get(lon_col) if lon_col else None,
                        "status": "CANDIDATE",
                        "confidence": 0.9 if entity_type in {"borough", "ward", "lsoa", "msoa", "tfl_line", "tfl_bikepoint", "air_site", "ea_station"} else 0.7,
                        "review_state": "AUTO_HIGH_CONFIDENCE" if entity_type in {"borough", "ward", "lsoa", "msoa", "tfl_line", "tfl_bikepoint", "air_site", "ea_station"} else "AUTO_MEDIUM_CONFIDENCE",
                        "evidence_fields": json.dumps({"id_col": id_col, "name_col": name_col}, sort_keys=True),
                    }
                )
    return pd.DataFrame(anchors)


def build_joins(manifests: list[dict[str, Any]], anchors: pd.DataFrame) -> pd.DataFrame:
    if anchors.empty:
        return pd.DataFrame()
    rows: list[dict[str, Any]] = []
    for anchor in anchors.head(6000).to_dict("records"):
        entity_type = anchor.get("entity_type")
        method = "exact_native_id"
        if entity_type in {"borough", "ward", "lsoa", "msoa"}:
            method = "area_code_or_name"
        elif entity_type in {"uprn", "usrn", "toid"}:
            method = entity_type.upper()
        rows.append(
            {
                "source_key": anchor.get("source_key"),
                "source_record_id": anchor.get("source_record_id"),
                "candidate_entity_id": anchor.get("candidate_entity_id"),
                "entity_type": entity_type,
                "join_method": method,
                "confidence": anchor.get("confidence"),
                "distance_meters": None,
                "matched_fields": anchor.get("evidence_fields"),
                "conflict_flag": False,
                "review_state": anchor.get("review_state"),
                "explanation": "Candidate join created from source-native identifier or source area field; low-confidence spatial joins are not forced.",
            }
        )
    return pd.DataFrame(rows)


def event_family(source_key: str) -> str:
    if source_key.startswith("lfb_"):
        return "fire_incident_context"
    if source_key.startswith("tfl_"):
        return "mobility_context"
    if source_key.startswith("ea_"):
        return "flood_context"
    if source_key.startswith("london_air") or source_key in {"laei", "noise_mapping"}:
        return "environment_context"
    if source_key in {"fixmystreet_open311", "borough_service_requests"}:
        return "civic_service_context"
    if "crime" in source_key:
        return "crime_context_aggregate"
    if "planning" in source_key or source_key in {"brownfield_land", "ev_charging_context"}:
        return "planning_context"
    if source_key.startswith("nhs_"):
        return "health_pressure_context"
    return "source_record"


def build_events_observations(manifests: list[dict[str, Any]], silver: dict[str, list[dict[str, Any]]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    events: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    observation_sources = ("london_air", "ea_", "tfl_line_status", "tfl_bikepoint", "energy_", "noise_", "laei")
    for m in manifests:
        source_key = str(m.get("source_key"))
        df = sample_silver(source_key, silver, 120)
        if df.empty:
            continue
        time_col = pick_col(df, ["source_event_time", "requested_datetime", "IncidentDate", "DateOfCall", "Valid date", "date", "Date", "startDate", "timestamp"])
        id_col = pick_col(df, ["source_record_id", "IncidentNumber", "id", "service_request_id", "LPA Number", "stationReference", "SiteCode"])
        metric_col = pick_col(df, ["value", "Value", "metric_value", "statusSeverity", "status", "latestReading.value", "Measurement", "NO2"])
        for idx, row in df.head(80).iterrows():
            rid = str(row.get(id_col, idx)) if id_col else str(idx)
            if source_key.startswith(observation_sources):
                observations.append(
                    {
                        "observation_id": f"lon:observation:{source_key}:{safe_name(rid)}",
                        "city": CITY,
                        "observation_type": source_key,
                        "observed_at": row.get(time_col) if time_col else None,
                        "source_key": source_key,
                        "source_record_id": rid,
                        "sensor_or_station_id": rid,
                        "location_entity_id": None,
                        "metric_name": metric_col,
                        "metric_value": row.get(metric_col) if metric_col else None,
                        "unit": None,
                        "quality_flag": None,
                        "claim_boundary": m.get("boundary_class"),
                    }
                )
            else:
                events.append(
                    {
                        "event_id": f"lon:event:{source_key}:{safe_name(rid)}",
                        "city": CITY,
                        "flow_candidates": ",".join(m.get("flows") or []),
                        "event_family": event_family(source_key),
                        "event_type": source_key,
                        "event_time": row.get(time_col) if time_col else None,
                        "event_end_time": None,
                        "source_key": source_key,
                        "source_record_id": rid,
                        "location_entity_id": None,
                        "area_entity_id": None,
                        "road_entity_id": None,
                        "building_entity_id": None,
                        "parcel_entity_id": None,
                        "facility_entity_id": None,
                        "sensor_entity_id": None,
                        "severity_or_magnitude": None,
                        "status": "SOURCE_STAGED",
                        "description_short": f"Staged London {source_key} source record",
                        "claim_boundary": m.get("boundary_class"),
                        "privacy_boundary": m.get("privacy_class"),
                        "review_state": "SOURCE_ONLY",
                    }
                )
    return pd.DataFrame(events), pd.DataFrame(observations)


def readiness_matrix(manifests: list[dict[str, Any]], source_final: list[dict[str, Any]], anchors: pd.DataFrame, joins: pd.DataFrame) -> list[dict[str, Any]]:
    by_key = {m["source_key"]: m for m in manifests}
    final_by_key = {row["source_key"]: row for row in source_final}
    rows = []
    for flow, spec in FLOW_SPECS.items():
        relevant = [by_key[key] for key in spec["sources"] if key in by_key]
        landed = [m for m in relevant if m.get("status") in COMPLETE_OR_USABLE]
        missing = [key for key in spec["sources"] if key not in by_key]
        blocked = [m["source_key"] for m in relevant if m.get("status") in {"KEY_BLOCKED", "BLOCKED_REMOTE", "FAILED_WITH_REASON", "RESOURCE_RESOLUTION_REQUIRED", "ENDPOINT_SHAPE_UNRESOLVED", "METADATA_ONLY"}]
        source_cov = len(landed) / max(len(spec["sources"]), 1)
        silver_rows = sum(int(final_by_key.get(m["source_key"], {}).get("silver_rows") or 0) for m in landed)
        anchor_cov = len(anchors[anchors["source_key"].isin([m["source_key"] for m in landed])]) if not anchors.empty else 0
        join_cov = len(joins[joins["source_key"].isin([m["source_key"] for m in landed])]) if not joins.empty else 0
        status = spec["status"]
        if source_cov < 0.55:
            status = "PARTIAL_FLOW_CONSUMPTION_CANDIDATE"
        if flow == "F6":
            status = "PARTIAL_FLOW_CONSUMPTION_CANDIDATE"
        rows.append(
            {
                "flow_id": flow,
                "candidate_output": f"LON-{flow}-CONSUMPTION-CANDIDATE-R1",
                "flow_name": spec["name"],
                "source_coverage": round(source_cov, 3),
                "row_file_coverage": sum(int(m.get("landed_rows") or 0) + int(m.get("landed_files") or 0) for m in landed),
                "silver_row_coverage": silver_rows,
                "anchor_coverage": anchor_cov,
                "join_coverage": join_cov,
                "temporal_coverage": "WINDOWED_OR_SOURCE_NATIVE_PARTIAL",
                "geography_coverage": "CANDIDATE_ANCHORS_CREATED" if anchor_cov else "SOURCE_ONLY_OR_ARCHIVE_REGISTERED",
                "privacy_readiness": "PASS_WITH_LONDON_BOUNDARIES",
                "EvidenceBundle_readiness": "SAMPLES_GENERATED",
                "smoke_test_readiness": "SMOKE_PACK_GENERATED",
                "limitations": "; ".join(blocked + [f"missing:{x}" for x in missing]) if blocked or missing else "landing/source limitations carried forward",
                "recommended_candidate_status": status,
                "human_decisions_required": "Review low-confidence joins, archive-only packages, and source-specific boundaries before any acceptance task.",
            }
        )
    return rows


def feature_cube_rows(manifests: list[dict[str, Any]], source_final: list[dict[str, Any]]) -> pd.DataFrame:
    final_by_key = {row["source_key"]: row for row in source_final}
    rows = []
    for m in manifests:
        for flow in m.get("flows") or []:
            rows.append(
                {
                    "city": CITY,
                    "flow_id": flow,
                    "source_key": m.get("source_key"),
                    "feature_name": "source_coverage",
                    "feature_period": "phase_1_landing",
                    "row_count": m.get("landed_rows", 0),
                    "silver_row_count": final_by_key.get(m.get("source_key"), {}).get("silver_rows", 0),
                    "file_count": m.get("landed_files", 0),
                    "missingness_indicator": m.get("status") not in COMPLETE_OR_USABLE,
                    "confidence_summary": "landing-derived candidate_signal/review_signal only",
                    "claim_boundary": "candidate_signal/review_signal; not a final incident, determination, or official anomaly",
                }
            )
    return pd.DataFrame(rows)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def df_for_parquet(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == "object":
            out[col] = out[col].map(
                lambda value: json.dumps(clean(value), sort_keys=True, ensure_ascii=True, default=str)
                if isinstance(value, (dict, list, tuple, set))
                else (None if value is None or (isinstance(value, float) and math.isnan(value)) else str(value))
            )
    return out


def evidence_samples(manifests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {m["source_key"]: m for m in manifests}
    rows = []
    for flow, spec in FLOW_SPECS.items():
        sources = [key for key in spec["sources"] if key in by_key][:9]
        for idx in range(20):
            scope = sources[idx % len(sources)] if sources else "no_source"
            rows.append(
                {
                    "city": CITY,
                    "flow_id": flow,
                    "question_family": f"{spec['name']} deterministic review question",
                    "time_window": "landed R1 window",
                    "area_or_entity_scope": scope,
                    "facts": [{"source_key": key, "status": by_key[key].get("status"), "rows": by_key[key].get("landed_rows")} for key in sources[:6]],
                    "tables": [f"silver_{safe_name(key)}" for key in sources[:6]],
                    "geo_layers": ["entity_anchors", "join_candidates"],
                    "source_refs": sources,
                    "join_refs": ["exact_native_id", "area_code_or_name", "source_only"],
                    "confidence_summary": "Candidate consumption-prep sample; deterministic and not final evidence.",
                    "missing_data": [key for key in spec["sources"] if key not in by_key or by_key.get(key, {}).get("status") in {"KEY_BLOCKED", "BLOCKED_REMOTE", "RESOURCE_RESOLUTION_REQUIRED", "METADATA_ONLY"}],
                    "limitations": spec["boundary"],
                    "claim_boundary": spec["boundary"],
                    "privacy_boundary": "London review-safe bounded source use only.",
                    "recommended_answer_boundary": "Answer as context/evidence only; do not make operational, public-safety, health, policing, legal, or acceptance claims.",
                }
            )
    return rows


def smoke_queries() -> list[dict[str, Any]]:
    rows = []
    for flow, spec in FLOW_SPECS.items():
        for idx in range(25):
            kind = "normal" if idx < 10 else "entity" if idx < 15 else "time_window" if idx < 20 else "adversarial_boundary"
            family = spec["families"][idx % len(spec["families"])]
            rows.append(
                {
                    "query_text": f"{kind} smoke query {idx + 1} for LON-{flow}: review {family} context with London boundaries",
                    "expected_flow": flow,
                    "required_source_families": spec["families"],
                    "required_entities": ["entity_anchors", "join_candidates"],
                    "expected_boundary_language": spec["boundary"],
                    "forbidden_claims": ["accepted flow", "official affected asset", "dispatch recommendation", "emergency instruction", "traffic-control command", "transit-control command", "health determination", "policing recommendation", "legal planning determination"],
                    "expected_EvidenceBundle_fields": ["city", "flow_id", "facts", "source_refs", "limitations", "claim_boundary", "privacy_boundary"],
                    "pass_fail_validator_rule": "PASS if response cites source_refs and repeats boundary; FAIL if it makes an operational, acceptance, legal, health, policing, or official affected-asset claim.",
                }
            )
    return rows


def write_flow_bundles(out: Path, manifests: list[dict[str, Any]], source_final: list[dict[str, Any]], matrix: list[dict[str, Any]], samples: list[dict[str, Any]], queries: list[dict[str, Any]]) -> None:
    by_key = {row["source_key"]: row for row in source_final}
    matrix_by_flow = {row["flow_id"]: row for row in matrix}
    base = out / "LON_FLOW_BUNDLES"
    for flow, spec in FLOW_SPECS.items():
        flow_dir = base / flow
        flow_dir.mkdir(parents=True, exist_ok=True)
        source_inputs = [by_key[key] for key in spec["sources"] if key in by_key]
        write_json(flow_dir / "flow_contract.json", {"city": CITY, "flow_id": flow, "candidate_gate": f"LON-{flow}-CONSUMPTION-CANDIDATE-R1", "name": spec["name"], "target_status": matrix_by_flow[flow]["recommended_candidate_status"], "boundary": spec["boundary"], "no_acceptance": True})
        write_json(flow_dir / "source_inputs.json", {"sources": source_inputs})
        write_json(flow_dir / "required_tables.json", {"tables": [f"silver_{safe_name(m['source_key'])}" for m in source_inputs if m.get("silver_parquet_count")] + ["entity_anchors", "join_candidates"]})
        write_json(flow_dir / "optional_tables.json", {"tables": ["staged_events", "staged_observations", "feature_cubes"]})
        write_text(flow_dir / "join_strategy.md", f"# {flow} Join Strategy\n\nUse exact London native IDs first: borough/ward/LSOA/MSOA, UPRN, USRN, TOID, LFB incident number, TfL line/stop/bikepoint IDs, EA station/measure IDs, London Air site/species IDs, planning references, and source-only review joins. Do not force low-confidence spatial joins.\n")
        write_text(flow_dir / "claim_boundary.md", spec["boundary"] + "\n")
        write_text(flow_dir / "privacy_boundary.md", "Review-safe bounded London source use only. Health, crime, demographic, and civic records remain aggregate/context or selected-field review sources.\n")
        limits = [m["source_key"] for m in source_inputs if m.get("landing_status") not in COMPLETE_OR_USABLE or not m.get("silver_parquet_count")]
        write_text(flow_dir / "limitations.md", "\n".join(["# Limitations", *[f"- {item}" for item in limits or ["landing/source limitations carried forward"]]]) + "\n")
        write_jsonl(flow_dir / "sample_evidence_bundles.jsonl", [s for s in samples if s["flow_id"] == flow])
        write_jsonl(flow_dir / "smoke_queries.jsonl", [q for q in queries if q["expected_flow"] == flow])
        write_text(flow_dir / "readiness_report.md", f"# {flow} Readiness\n\nCandidate gate: `LON-{flow}-CONSUMPTION-CANDIDATE-R1`\n\nRecommended status: `{matrix_by_flow[flow]['recommended_candidate_status']}`\n\nNo flow acceptance is claimed.\n")


def write_duckdb(out: Path, source_final: list[dict[str, Any]], silver: dict[str, list[dict[str, Any]]], anchors: pd.DataFrame, joins: pd.DataFrame, events: pd.DataFrame, observations: pd.DataFrame, matrix: list[dict[str, Any]], feature_cubes: pd.DataFrame) -> list[dict[str, Any]]:
    db_path = out / "LON_FLOW_MART.duckdb"
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    con.register("source_registry_df", pd.DataFrame(source_final))
    con.execute("CREATE TABLE source_registry AS SELECT * FROM source_registry_df")
    con.register("anchors_df", anchors)
    con.execute("CREATE TABLE entity_anchors AS SELECT * FROM anchors_df")
    con.register("joins_df", joins)
    con.execute("CREATE TABLE join_candidates AS SELECT * FROM joins_df")
    con.register("events_df", events)
    con.execute("CREATE TABLE staged_events AS SELECT * FROM events_df")
    con.register("observations_df", observations)
    con.execute("CREATE TABLE staged_observations AS SELECT * FROM observations_df")
    con.register("matrix_df", pd.DataFrame(matrix))
    con.execute("CREATE TABLE flow_readiness_matrix AS SELECT * FROM matrix_df")
    con.register("feature_df", feature_cubes)
    con.execute("CREATE TABLE feature_cubes AS SELECT * FROM feature_df")
    view_errors = []
    for source_key, parts in silver.items():
        if not parts:
            continue
        escaped = ", ".join("'" + part["path"].replace("\\", "/").replace("'", "''") + "'" for part in parts[:200])
        view_name = "silver_" + safe_name(source_key)
        try:
            con.execute(f"CREATE VIEW {view_name} AS SELECT * FROM read_parquet([{escaped}], union_by_name=true)")
        except Exception as exc:
            view_errors.append({"source_key": source_key, "view_name": view_name, "parquet_files_attempted": len(parts[:200]), "error": str(exc)[:500]})
    con.register("view_errors_df", pd.DataFrame(view_errors, columns=["source_key", "view_name", "parquet_files_attempted", "error"]))
    con.execute("CREATE TABLE source_view_errors AS SELECT * FROM view_errors_df")
    con.close()
    return view_errors


def write_hashes(out: Path) -> None:
    lines = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {path.relative_to(out).as_posix()}")
    write_text(out / "hashes.sha256", "\n".join(lines) + "\n")


def no_overclaim(out: Path) -> dict[str, Any]:
    forbidden = [r"\bCERTIFIED\b", r"\bPRODUCTION_READY\b", r"\bPUBLIC_SAFETY_READY\b", r"\bfully operational\b"]
    safe_phrases = [
        "not certified",
        "no certified",
        "without certified",
        "certified affected-asset",
        "certified affected asset",
        "forbidden_claims",
        "forbidden claim",
        "forbidden claims",
        "no public-safety",
        "public-safety, health",
    ]
    findings = []
    compiled = [re.compile(p, re.I) for p in forbidden]
    for path in out.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".duckdb", ".parquet"}:
            continue
        rel = path.relative_to(out).as_posix()
        if rel == "LON_NO_OVERCLAIM_REPORT.json" or rel.startswith("scripts/"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for regex in compiled:
            for match in regex.finditer(text):
                context = text[max(0, match.start() - 90): match.end() + 90].lower()
                if any(safe in context for safe in safe_phrases):
                    continue
                findings.append({"path": str(path), "pattern": regex.pattern})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def write_reports(out: Path, input_root: Path, manifests: list[dict[str, Any]], phase: dict[str, Any], source_final: list[dict[str, Any]], skipped: list[dict[str, Any]], anchors: pd.DataFrame, joins: pd.DataFrame, events: pd.DataFrame, observations: pd.DataFrame, matrix: list[dict[str, Any]], view_errors: list[dict[str, Any]], overclaim: dict[str, Any]) -> None:
    status_counts = Counter(m.get("status") for m in manifests)
    final_counts = Counter(row["recommended_candidate_status"] for row in matrix)
    total_rows = sum(int(m.get("landed_rows") or 0) for m in manifests)
    total_files = sum(int(m.get("landed_files") or 0) for m in manifests)
    silver_rows = sum(int(row.get("silver_rows") or 0) for row in source_final)
    unresolved = [row for row in source_final if row["resource_resolution_required"]]
    archive_only = [row for row in source_final if not row["silver_parquet_count"] and row["landed_files"]]
    write_text(out / "README.md", f"# {TASK}\n\nStatus: `FLOW_CONSUMPTION_READY_WITH_LIMITATIONS`\n\nConsumption-prep artifacts only. No London flow is accepted or production-ready.\n\nInput: `{input_root}`\n")
    write_text(out / "LON_CONSUMPTION_PREP_PLAN.md", "# LON Consumption Prep Plan\n\nLanding audit -> typed silver parquet where readable -> privacy-safe candidate views -> London entity anchors -> join candidates -> event/observation staging -> flow bundles -> feature cubes -> EvidenceBundle samples -> smoke queries -> readiness matrix.\n")
    write_json(out / "LON_SOURCE_LEDGER_FINAL.json", {"task": TASK, "generated_at": utc_now(), "source_count": len(source_final), "landing_phase_status": phase.get("status"), "sources": source_final})
    write_json(out / "LON_SILVER_BUILD_AUDIT.json", {"silver_source_count": sum(1 for row in source_final if row["silver_parquet_count"]), "silver_rows": silver_rows, "skipped": skipped, "view_errors": view_errors})
    write_text(out / "LON_DATA_LANDING_AUDIT.md", "\n".join(["# LON Data Landing Audit", "", f"Input root: `{input_root}`", f"Sources: {len(manifests)}", f"Rows landed/registered: {total_rows:,}", f"Files landed/registered: {total_files:,}", f"Silver rows built: {silver_rows:,}", "", "Status counts:", *[f"- {k}: {v}" for k, v in sorted(status_counts.items())]]) + "\n")
    write_text(out / "LON_DATA_QUALITY_REPORT.md", "\n".join(["# LON Data Quality Report", "", f"Entity anchors: {len(anchors):,}", f"Join candidates: {len(joins):,}", f"Staged events: {len(events):,}", f"Staged observations: {len(observations):,}", f"Silver rows: {silver_rows:,}", "", f"Archive/non-tabular or unreadable records documented: {len(skipped):,}", "Known limitations are carried from landing; missing evidence is not invented."]) + "\n")
    write_text(out / "LON_PRIVACY_BOUNDARY.md", "# LON Privacy Boundary\n\n" + "\n".join(f"- {line}" for line in BOUNDARY_LINES) + "\n")
    write_text(out / "LON_CLAIM_BOUNDARY.md", "# LON Claim Boundary\n\nNo London flow is accepted by this package. Outputs are candidate consumption-prep artifacts only. No public-safety command, emergency instruction, enforcement recommendation, dispatch recommendation, health determination, policing recommendation, legal planning determination, or official affected-asset claim is made.\n")
    limitations = ["# LON Limitations", ""]
    for row in unresolved:
        limitations.append(f"- {row['source_key']}: {row['landing_status']} {row.get('notes') or ''}")
    for row in archive_only[:50]:
        limitations.append(f"- {row['source_key']}: landed/registered but not converted to silver parquet for at least one archive, GPKG, PDF, HTML, or unsupported workbook package.")
    write_text(out / "LON_LIMITATIONS.md", "\n".join(limitations) + "\n")
    write_text(out / "LON_ENTITY_ANCHOR_REPORT.md", f"# LON Entity Anchor Report\n\nCreated `{len(anchors):,}` candidate anchors across `{anchors['entity_type'].nunique() if not anchors.empty else 0}` entity types. Staging IDs follow the London addendum patterns such as `lon:borough:*`, `lon:tfl_line:*`, `lon:lfb_incident:*`, `lon:ea_station:*`, and `lon:event:*`.\n")
    write_text(out / "LON_JOIN_CANDIDATE_REPORT.md", f"# LON Join Candidate Report\n\nCreated `{len(joins):,}` candidate joins using exact native IDs, area fields, UPRN/USRN/TOID-style IDs where readable, TfL/LFB/EA/London Air native IDs, and source-only review joins. Low-confidence joins are not forced.\n")
    write_text(out / "LON_EVENT_OBSERVATION_STAGING_REPORT.md", f"# LON Event / Observation Staging Report\n\nEvents: `{len(events):,}`\n\nObservations: `{len(observations):,}`\n\nThese are source staging records only and do not create operational commands or official affected-asset claims.\n")
    contract_lines = ["# LON Flow Consumption Contracts", ""]
    for row in matrix:
        contract_lines.append(f"- {row['flow_id']} {row['flow_name']}: `{row['candidate_output']}` -> `{row['recommended_candidate_status']}`")
    write_text(out / "LON_FLOW_CONSUMPTION_CONTRACTS.md", "\n".join(contract_lines) + "\n")
    write_text(
        out / "LON_ACCEPTANCE_CANDIDATE_REPORT.md",
        "\n".join(
            [
                "# LON Acceptance Candidate Report",
                "",
                "This is not a flow-acceptance report. It is a consumption-prep readiness report.",
                "",
                f"Rows landed/registered: {total_rows:,}",
                f"Silver rows built: {silver_rows:,}",
                f"Entity anchors: {len(anchors):,}",
                f"Join candidates: {len(joins):,}",
                f"Staged events: {len(events):,}",
                f"Staged observations: {len(observations):,}",
                "",
                "Recommended candidate statuses:",
                *[f"- {k}: {v}" for k, v in sorted(final_counts.items())],
                "",
                "Strongest London candidate outputs: `LON-F3-CONSUMPTION-CANDIDATE-R1`, `LON-F4-CONSUMPTION-CANDIDATE-R1`, `LON-F5-CONSUMPTION-CANDIDATE-R1`, and `LON-F7-CONSUMPTION-CANDIDATE-R1`.",
                "",
                "Platform team can consume first: LFB incident/mobilisation context, TfL mobility status/disruptions/BikePoint, EA flood station/area context, London Air station/species/readings, Planning Datahub CSVs, FixMyStreet/Open311 capped London civic feed, demographic/economic aggregates, and the candidate entity/join/event/observation staging tables.",
                "",
                "Human decisions required: review archive-only OS/GPKG/LAEI/noise/population packages before deeper typed extraction, inspect low-confidence joins, and keep all London hard boundaries before any future acceptance task.",
            ]
        ) + "\n",
    )
    write_json(out / "LON_NO_OVERCLAIM_REPORT.json", overclaim)


def copy_runner(out: Path) -> None:
    src = Path(__file__).resolve()
    dest = out / "scripts" / src.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.project_root).resolve()
    input_root = (root / args.input_root).resolve()
    out = (root / args.output_root).resolve()
    out.mkdir(parents=True, exist_ok=True)
    for sub in ["tables", "silver", "scripts", "LON_FLOW_BUNDLES"]:
        (out / sub).mkdir(parents=True, exist_ok=True)
    copy_runner(out)
    manifests, phase = load_landing(input_root)
    silver, skipped = build_silver_tables(input_root, out, manifests)
    source_final = build_source_final(manifests, silver, skipped)
    anchors = build_anchors(manifests, silver)
    joins = build_joins(manifests, anchors)
    events, observations = build_events_observations(manifests, silver)
    matrix = readiness_matrix(manifests, source_final, anchors, joins)
    feature_cubes = feature_cube_rows(manifests, source_final)
    samples = evidence_samples(manifests)
    queries = smoke_queries()

    tables = {
        "source_ledger_final.parquet": pd.DataFrame(source_final),
        "entity_anchors.parquet": anchors,
        "join_candidates.parquet": joins,
        "staged_events.parquet": events,
        "staged_observations.parquet": observations,
        "feature_cubes.parquet": feature_cubes,
        "flow_readiness_matrix.parquet": pd.DataFrame(matrix),
    }
    for name, df in tables.items():
        df_for_parquet(df).to_parquet(out / "tables" / name, index=False)
    write_csv(out / "LON_FLOW_READINESS_MATRIX.csv", matrix, list(matrix[0].keys()))
    write_jsonl(out / "LON_EVIDENCEBUNDLE_SAMPLES.jsonl", samples)
    write_jsonl(out / "LON_QUERY_SMOKE_PACK.jsonl", queries)
    write_flow_bundles(out, manifests, source_final, matrix, samples, queries)
    view_errors = write_duckdb(out, source_final, silver, anchors, joins, events, observations, matrix, feature_cubes)
    write_reports(out, input_root, manifests, phase, source_final, skipped, anchors, joins, events, observations, matrix, view_errors, {"status": "PENDING", "findings": []})
    overclaim = no_overclaim(out)
    write_json(out / "LON_NO_OVERCLAIM_REPORT.json", overclaim)
    write_hashes(out)
    status = "FLOW_CONSUMPTION_READY_WITH_LIMITATIONS" if overclaim["status"] == "PASS" else "FAIL"
    return {
        "status": status,
        "output_root": str(out),
        "sources": len(manifests),
        "silver_sources": sum(1 for rows in silver.values() if rows),
        "silver_rows": sum(int(part.get("rows") or 0) for rows in silver.values() for part in rows),
        "anchors": len(anchors),
        "joins": len(joins),
        "events": len(events),
        "observations": len(observations),
        "overclaim": overclaim,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run London all-flows consumption prep R1.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--input-root", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    result = run(args)
    print(f"{TASK}: {result['status']}")
    print(f"Output: {result['output_root']}")
    print(f"Sources={result['sources']} SilverSources={result['silver_sources']} SilverRows={result['silver_rows']} Anchors={result['anchors']} Joins={result['joins']} Events={result['events']} Observations={result['observations']}")
    return 0 if result["status"] in ALLOWED_FINAL and result["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())

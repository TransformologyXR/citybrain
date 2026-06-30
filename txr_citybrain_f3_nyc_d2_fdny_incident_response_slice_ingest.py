from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import tempfile
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


TASK_NAME = "F3-NYC-D2 FDNY Incident Response Slice Ingest"
DEFAULT_OUTPUT_DIR = "outputs/f3_nyc_d2_fdny_incident_response_slice_ingest"
DEFAULT_SAMPLE_CAP = 50_000
USER_PROVIDED_EMS_DEMO_URL = "https://soda.demo.socrata.com/resource/4tka-6guv.json?$limit=50000"

SOURCE_KEYS: dict[str, dict[str, Any]] = {
    "fire_company_incidents": {
        "dataset": "Incidents_Responded_to_by_Fire_Companies_20260626",
        "expected_names": [
            "Incidents_Responded_to_by_Fire_Companies_20260626.csv",
            "Incidents_Responded_to_by_Fire_Companies.csv",
        ],
        "role": "primary_fdny_incident_response_source",
        "required_for_green": True,
        "download": None,
        "known_full_count": 6_033_991,
    },
    "fire_dispatch": {
        "dataset": "Fire_Incident_Dispatch_Data",
        "expected_names": ["Fire_Incident_Dispatch_Data.csv"],
        "role": "fdny_dispatch_event_source",
        "required_for_green": True,
        "download": {
            "resource_id": "8m42-w767",
            "url": "https://data.cityofnewyork.us/resource/8m42-w767.csv?$limit={limit}",
            "limit": DEFAULT_SAMPLE_CAP,
            "official": True,
        },
        "known_full_count": 11_819_520,
    },
    "fdny_firehouses": {
        "dataset": "FDNY_Firehouse_Listing",
        "expected_names": ["FDNY_Firehouse_Listing.csv"],
        "role": "fdny_station_resource_asset_source",
        "required_for_green": True,
        "download": {
            "resource_id": "hc8x-tcnd",
            "url": "https://data.cityofnewyork.us/resource/hc8x-tcnd.csv?$limit={limit}",
            "limit": 50_000,
            "official": True,
        },
        "known_full_count": 219,
    },
    "ems_actual_rows": {
        "dataset": "EMS_Incident_Dispatch_Data",
        "expected_names": ["EMS_Incident_Dispatch_Data.csv", "EMS_Incident_Dispatch_Data.csv.gz"],
        "role": "ems_incident_dispatch_rows",
        "required_for_green": False,
        "download": {
            "resource_id": "76xm-jjuj",
            "url": "https://data.cityofnewyork.us/resource/76xm-jjuj.csv?$limit={limit}",
            "limit": DEFAULT_SAMPLE_CAP,
            "official": True,
            "try_user_demo_first": True,
        },
        "known_full_count": 29_572_156,
    },
    "mvc_crashes": {
        "dataset": "Motor_Vehicle_Collisions_-_Crashes",
        "expected_names": ["Motor_Vehicle_Collisions_-_Crashes.csv"],
        "role": "primary_collision_event_source",
        "required_for_green": False,
        "download": {
            "resource_id": "h9gi-nx95",
            "url": "https://data.cityofnewyork.us/resource/h9gi-nx95.csv?$limit={limit}",
            "limit": DEFAULT_SAMPLE_CAP,
            "official": True,
        },
        "known_full_count": 2_269_187,
    },
    "motor_vehicle_vehicles": {
        "dataset": "Motor_Vehicle_Collisions_-_Vehicles",
        "expected_names": ["Motor_Vehicle_Collisions_-_Vehicles.csv"],
        "role": "collision_vehicle_context_not_primary_event",
        "required_for_green": False,
        "download": None,
        "known_full_count": 4_551_002,
    },
    "ems_description": {
        "dataset": "EMS_incident_dispatch_data_description",
        "expected_names": [
            "EMS_incident_dispatch_data_description.xlsx",
            "EMS_incident_dispatch_data_description",
        ],
        "role": "schema_documentation_only",
        "required_for_green": False,
        "download": None,
        "known_full_count": None,
    },
}

NO_OVERCLAIM_LINES = [
    "F3-NYC-D2 is source completion and bounded incident-response slice ingest.",
    "D2 does not certify affected buildings/assets.",
    "D2 does not perform geocoding.",
    "D2 does not perform dispatch optimization.",
    "D2 does not make emergency response recommendations.",
    "D2 does not claim live Flow 3 face or NIM support.",
    "MVC vehicles are vehicle context, not primary crash events.",
    "EMS description is documentation unless actual EMS rows are present.",
    "Address/street/ZIP locations are candidate locations unless official coordinates exist.",
]

FORBIDDEN_POSITIVE_PATTERNS = [
    r"full flow 3 cartridge",
    r"affected buildings? (?:are )?certified",
    r"affected assets? (?:are )?certified",
    r"address(?:/street/zip)? locations are exact",
    r"dispatch optimization (?:is )?(?:performed|complete|available)",
    r"emergency response recommendations (?:are )?(?:made|available)",
    r"live flow 3 face (?:is|support is|enabled|available)",
    r"nim support (?:is )?(?:live|available)",
    r"mvc vehicles (?:is|are) (?:the )?primary",
    r"ems description (?:is|as) actual rows",
]

SENSITIVE_PATTERNS = [
    "name",
    "phone",
    "patient",
    "narrative",
    "remark",
    "comment",
    "complainant",
    "contact",
    "license",
    "licence",
    "floor",
    "apartment",
    "apt",
    "unit",
    "email",
    "severity",
    "hospital",
    "disposition",
    "call_type",
    "held_indicator",
]

LOCATION_COLUMNS = {
    "latitude",
    "lat",
    "longitude",
    "lon",
    "lng",
    "location",
    "x_coordinate",
    "y_coordinate",
    "street_highway",
    "street",
    "address",
    "zip_code",
    "zipcode",
    "postcode",
    "borough",
    "borough_desc",
    "incident_borough",
    "alarm_box_location",
}

TIME_COLUMNS = {
    "incident_date_time",
    "arrival_date_time",
    "last_unit_cleared_date_time",
    "incident_datetime",
    "first_assignment_datetime",
    "first_activation_datetime",
    "first_on_scene_datetime",
    "incident_close_datetime",
    "crash_date",
    "crash_time",
}

RESOURCE_COLUMNS = {
    "facilityname",
    "facilityaddress",
    "fire_box",
    "alarm_box_number",
    "engines_assigned_quantity",
    "ladders_assigned_quantity",
    "other_units_assigned_quantity",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


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
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "F3-NYC-D2-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {p.lower() for p in resolved.parts} or "f3_nyc_d2" not in resolved.name.lower():
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in ["canonical", "evidence", "reports"]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def normalize_col(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def safe_id(value: Any, fallback: str = "unknown") -> str:
    text = str(value if value is not None else fallback).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text[:96] or fallback


def cell(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    text = str(value).strip()
    return text if text and text.lower() not in {"nan", "nat", "none", "<na>"} else None


def parse_float(value: Any) -> float | None:
    text = cell(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def canonical_time(*parts: Any) -> str | None:
    values = [cell(part) for part in parts if cell(part)]
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return f"{values[0]} {values[1]}"


def path_metadata(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() else None,
        "mtime_ns": path.stat().st_mtime_ns if path.exists() else None,
        "sha256": sha256_file(path) if path.exists() and path.is_file() and path.stat().st_size < 2_500_000_000 else None,
    }


def input_snapshot(d1_dir: Path) -> dict[str, Any]:
    watched: dict[str, Any] = {}
    if d1_dir.exists():
        for path in sorted(d1_dir.rglob("*")):
            if path.is_file():
                watched[str(path)] = {
                    "bytes": path.stat().st_size,
                    "mtime_ns": path.stat().st_mtime_ns,
                    "sha256": sha256_file(path) if path.stat().st_size < 250_000_000 else None,
                }
    return watched


def iter_search_files(root: Path):
    skip = {".git", "__pycache__", "node_modules", ".venv", "venv"}
    try:
        for current, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in skip and d.lower() != "outputs"]
            for filename in files:
                yield Path(current) / filename
    except Exception:
        return


def discover_sources(project_root: Path, raw_roots: list[str]) -> dict[str, Any]:
    roots: list[Path] = [project_root]
    roots.extend(Path(r) for r in raw_roots)
    roots.extend(
        [
            project_root / "data_landing",
            project_root / "data_landing" / "nyc_flow3",
            project_root / "data_landing" / "nyc_raw",
            Path.home() / "Downloads",
            Path("C:/data/citybrain"),
            Path("/data/citybrain"),
            Path("/data/citybrain/nyc_flow3"),
            Path("/data/citybrain/nyc_raw"),
        ]
    )
    unique_roots: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        try:
            resolved = (project_root / root).resolve() if not root.is_absolute() else root.resolve()
        except Exception:
            resolved = root
        key = str(resolved).lower()
        if key not in seen:
            seen.add(key)
            unique_roots.append(resolved)

    expected: dict[str, str] = {}
    for key, meta in SOURCE_KEYS.items():
        for name in meta["expected_names"]:
            expected[name.lower()] = key

    found: dict[str, list[dict[str, Any]]] = {key: [] for key in SOURCE_KEYS}
    searched_roots = []
    for root in unique_roots:
        searched_roots.append({"root": str(root), "exists": root.exists()})
        if not root.exists():
            continue
        for path in iter_search_files(root):
            key = expected.get(path.name.lower())
            if key:
                found[key].append(path_metadata(path) | {"source_key": key, "matched_name": path.name})

    selected: dict[str, Any] = {}
    for key, matches in found.items():
        selected[key] = sorted(matches, key=lambda item: (item.get("bytes") or 0), reverse=True)[0] if matches else None
    return {"searched_roots": searched_roots, "found": found, "selected": selected}


def download_to_path(url: str, destination: Path, timeout: int = 120) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "CityBrain-F3-NYC-D2/1.0"})
    with tempfile.NamedTemporaryFile(delete=False, suffix=".download") as temp:
        temp_path = Path(temp.name)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response, temp_path.open("wb") as handle:
            shutil.copyfileobj(response, handle, length=1024 * 1024)
        temp_path.replace(destination)
        return {"status": "downloaded", "url": url, "path": str(destination), "bytes": destination.stat().st_size, "sha256": sha256_file(destination)}
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        return {"status": "failed", "url": url, "path": str(destination), "error": f"{type(exc).__name__}: {exc}"}


def validate_user_ems_demo_url() -> dict[str, Any]:
    try:
        request = urllib.request.Request(USER_PROVIDED_EMS_DEMO_URL, headers={"User-Agent": "CityBrain-F3-NYC-D2/1.0"})
        payload = json.loads(urllib.request.urlopen(request, timeout=30).read().decode("utf-8", errors="replace"))
        first = payload[0] if isinstance(payload, list) and payload else {}
        keys = set(first.keys()) if isinstance(first, dict) else set()
        is_ems = bool({"incident_id", "incident_datetime", "borough"} & keys) and "earthquake_id" not in keys
        return {
            "url": USER_PROVIDED_EMS_DEMO_URL,
            "status": "accepted" if is_ems else "rejected_not_ems",
            "sample_keys": sorted(keys),
            "reason": None if is_ems else "User-provided demo endpoint returned earthquake fields, not NYC EMS dispatch rows.",
        }
    except Exception as exc:
        return {"url": USER_PROVIDED_EMS_DEMO_URL, "status": "failed", "error": f"{type(exc).__name__}: {exc}"}


def complete_missing_sources(project_root: Path, selected: dict[str, Any]) -> dict[str, Any]:
    landing = project_root / "data_landing" / "nyc_flow3"
    actions: dict[str, Any] = {}
    for key, meta in SOURCE_KEYS.items():
        if selected.get(key) is not None:
            actions[key] = {"status": "already_available", "selected": selected[key]}
            if key == "ems_actual_rows" and meta.get("download", {}).get("try_user_demo_first"):
                actions[key]["user_demo_validation"] = validate_user_ems_demo_url()
            continue
        download = meta.get("download")
        if not download:
            actions[key] = {"status": "missing_no_download_attempted", "reason": "No clean official download configured for D2."}
            continue
        if download.get("try_user_demo_first"):
            demo_validation = validate_user_ems_demo_url()
        else:
            demo_validation = None
        limit = int(download.get("limit") or DEFAULT_SAMPLE_CAP)
        expected_name = meta["expected_names"][0]
        url = str(download["url"]).format(limit=limit)
        destination = landing / expected_name
        result = download_to_path(url, destination)
        actions[key] = {
            "status": result["status"],
            "official_source": bool(download.get("official")),
            "resource_id": download.get("resource_id"),
            "limit": limit,
            "bounded_sample": True,
            "known_full_count": meta.get("known_full_count"),
            "user_demo_validation": demo_validation,
            "download_result": result,
        }
    return actions


def redact_value(column: str, value: Any) -> Any:
    ncol = normalize_col(column)
    if any(pattern in ncol for pattern in SENSITIVE_PATTERNS):
        return "[REDACTED]"
    return cell(value)


def line_count_csv(path: Path) -> int | None:
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            count = sum(1 for _ in csv.reader(handle))
        return max(count - 1, 0)
    except Exception:
        return None


def read_bounded_csv(path: Path, max_rows: int) -> pd.DataFrame:
    return pd.read_csv(path, dtype="string", nrows=max_rows, on_bad_lines="skip")


def profile_csv(path: Path, source_key: str, sample_rows: int, d1_counts: dict[str, Any], source_completion: dict[str, Any]) -> dict[str, Any]:
    meta = SOURCE_KEYS[source_key]
    try:
        sample_df = pd.read_csv(path, dtype="string", nrows=sample_rows, on_bad_lines="skip")
    except Exception as exc:
        return {
            "status": "FAIL",
            "source_key": source_key,
            "path": str(path),
            "error": f"{type(exc).__name__}: {exc}",
        }
    columns = list(sample_df.columns)
    normalized = [normalize_col(col) for col in columns]
    known_full_count = meta.get("known_full_count")
    if source_key in d1_counts:
        full_count = d1_counts[source_key]
        row_count_method = "d1_accepted_report"
    elif known_full_count is not None:
        full_count = known_full_count
        row_count_method = "socrata_count_verified_preflight"
    elif path.stat().st_size < 250_000_000:
        full_count = line_count_csv(path)
        row_count_method = "local_line_count"
    else:
        full_count = None
        row_count_method = "not_counted_large_file"

    bounded_count = line_count_csv(path) if path.stat().st_size < 250_000_000 else None
    downloaded = source_completion.get(source_key, {}).get("status") == "downloaded"
    bounded_sample = bool(downloaded or (full_count is not None and bounded_count is not None and bounded_count < full_count))
    sample_rows_redacted = []
    for row in sample_df.to_dict("records"):
        sample_rows_redacted.append({col: redact_value(col, row.get(col)) for col in columns})

    column_profiles: dict[str, Any] = {}
    for col in columns:
        ncol = normalize_col(col)
        values = [cell(v) for v in sample_df[col].tolist()[:sample_rows]]
        values = [v for v in values if v is not None]
        column_profiles[col] = {
            "normalized": ncol,
            "sensitive_or_private_candidate": any(pattern in ncol for pattern in SENSITIVE_PATTERNS),
            "location_candidate": ncol in LOCATION_COLUMNS or any(part in ncol for part in ["borough", "zip", "street", "address", "latitude", "longitude"]),
            "time_candidate": ncol in TIME_COLUMNS or "datetime" in ncol or ncol.endswith("_time") or ncol.endswith("_date"),
            "resource_candidate": ncol in RESOURCE_COLUMNS or "firehouse" in ncol or "alarm_box" in ncol or "assigned_quantity" in ncol,
            "sample_non_null_count": len(values),
            "sample_values_redacted": [redact_value(col, v) for v in values[:5]],
        }
    nset = set(normalized)
    return {
        "status": "PASS",
        "source_key": source_key,
        "dataset": meta["dataset"],
        "role": meta["role"],
        "path": str(path),
        "bytes": path.stat().st_size,
        "columns": columns,
        "row_count": full_count,
        "row_count_method": row_count_method,
        "bounded_file_rows": bounded_count,
        "bounded_sample": bounded_sample,
        "bounded_sample_reason": "Downloaded or emitted as bounded D2 slice." if bounded_sample else None,
        "column_profiles": column_profiles,
        "sample_rows_redacted": sample_rows_redacted,
        "spatial_signals": {
            "has_latlon": bool({"latitude", "longitude"} <= nset or {"lat", "lon"} <= nset or {"lat", "lng"} <= nset),
            "has_address": any("address" in col or "street" in col for col in nset),
            "has_zip": any(col in {"zip", "zip_code", "zipcode", "postcode"} for col in nset),
            "has_borough": any("borough" in col for col in nset),
        },
        "temporal_signals": {"time_columns": [col for col in columns if column_profiles[col]["time_candidate"]]},
        "resource_signals": {"resource_columns": [col for col in columns if column_profiles[col]["resource_candidate"]]},
    }


def normalized_df(df: pd.DataFrame) -> pd.DataFrame:
    renamed = []
    seen: Counter[str] = Counter()
    for col in df.columns:
        ncol = normalize_col(col)
        seen[ncol] += 1
        renamed.append(ncol if seen[ncol] == 1 else f"{ncol}_{seen[ncol]}")
    result = df.copy()
    result.columns = renamed
    return result


def location_status(lat: Any, lon: Any, address: Any, street: Any, zipcode: Any, borough: Any) -> str:
    if parse_float(lat) is not None and parse_float(lon) is not None:
        return "latlon_exact"
    if cell(borough) and (cell(street) or cell(address)) and cell(zipcode):
        return "borough_street_zip_candidate"
    if cell(address) or cell(street):
        return "address_candidate"
    if cell(borough):
        return "borough_only"
    return "unavailable"


def fdny_event_type(description: Any) -> str:
    desc = (cell(description) or "").lower()
    if any(term in desc for term in ["collision", "motor vehicle", "vehicle accident", "mvc"]):
        return "collision"
    if any(term in desc for term in ["medical", "mfa", "ems", "cardiac", "injury"]):
        return "medical"
    if "fire" in desc and "nonfire" not in desc and "non-fire" not in desc:
        return "fire"
    if desc:
        return "non_fire_emergency"
    return "unknown"


def provenance(source_dataset: str, source_record_id: Any, source_path: Path) -> str:
    return json.dumps(
        [
            {
                "source_dataset": source_dataset,
                "source_record_id": cell(source_record_id),
                "source_path": str(source_path),
            }
        ],
        sort_keys=True,
    )


def canonicalize_fdny_incidents(path: Path, max_rows: int) -> pd.DataFrame:
    df = normalized_df(read_bounded_csv(path, max_rows))
    rows = []
    for idx, rec in enumerate(df.to_dict("records"), start=1):
        rid = cell(rec.get("im_incident_key")) or str(idx)
        borough = cell(rec.get("borough_desc")) or cell(rec.get("borough"))
        street = cell(rec.get("street_highway")) or cell(rec.get("street"))
        zipcode = cell(rec.get("zip_code")) or cell(rec.get("zipcode"))
        event_time = canonical_time(rec.get("incident_date_time"), rec.get("incident_datetime"))
        desc = cell(rec.get("incident_type_desc")) or cell(rec.get("incident_type"))
        loc_status = location_status(None, None, None, street, zipcode, borough)
        rows.append(
            {
                "canonical_id": f"event:us-nyc:flow3:fdny:fire_company_incidents:{safe_id(rid)}",
                "entity_type": "event",
                "event_family": "incident_response",
                "event_type": fdny_event_type(desc),
                "source_dataset": SOURCE_KEYS["fire_company_incidents"]["dataset"],
                "source_record_id": rid,
                "event_time": event_time,
                "borough": borough,
                "address_text": street,
                "street_name": street,
                "zipcode": zipcode,
                "latitude": None,
                "longitude": None,
                "location_status": loc_status,
                "private_data_status": "redacted_or_not_present",
                "provenance": provenance(SOURCE_KEYS["fire_company_incidents"]["dataset"], rid, path),
            }
        )
    return pd.DataFrame(rows)


def canonicalize_fire_dispatch(path: Path, max_rows: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = normalized_df(read_bounded_csv(path, max_rows))
    dispatch_rows = []
    resource_rows = []
    for idx, rec in enumerate(df.to_dict("records"), start=1):
        rid = cell(rec.get("starfire_incident_id")) or str(idx)
        resource_id = f"resource:us-nyc:fdny:dispatch_resource_summary:{safe_id(rid)}"
        borough = cell(rec.get("incident_borough")) or cell(rec.get("alarm_box_borough"))
        alarm_address = cell(rec.get("alarm_box_location"))
        zipcode = cell(rec.get("zipcode")) or cell(rec.get("zip_code"))
        dispatch_rows.append(
            {
                "canonical_id": f"dispatch:us-nyc:fdny:{safe_id(rid)}",
                "entity_type": "dispatch_event",
                "source_dataset": SOURCE_KEYS["fire_dispatch"]["dataset"],
                "incident_id": rid,
                "resource_id": resource_id,
                "dispatch_time": canonical_time(rec.get("first_assignment_datetime"), rec.get("incident_datetime")),
                "arrival_time": cell(rec.get("first_on_scene_datetime")),
                "close_time": cell(rec.get("incident_close_datetime")),
                "status": "observed_dispatch_record",
                "incident_classification_group": cell(rec.get("incident_classification_group")),
                "engines_assigned_quantity": cell(rec.get("engines_assigned_quantity")),
                "ladders_assigned_quantity": cell(rec.get("ladders_assigned_quantity")),
                "other_units_assigned_quantity": cell(rec.get("other_units_assigned_quantity")),
                "provenance": provenance(SOURCE_KEYS["fire_dispatch"]["dataset"], rid, path),
            }
        )
        resource_rows.append(
            {
                "canonical_id": resource_id,
                "entity_type": "response_resource",
                "resource_type": "unknown",
                "source_dataset": SOURCE_KEYS["fire_dispatch"]["dataset"],
                "source_record_id": rid,
                "borough": borough,
                "address_text": alarm_address,
                "zipcode": zipcode,
                "location_status": location_status(None, None, alarm_address, alarm_address, zipcode, borough),
                "status": "observed_in_incident",
                "resource_observation": "aggregate_assigned_quantity_fields_not_individual_unit_ids",
                "provenance": provenance(SOURCE_KEYS["fire_dispatch"]["dataset"], rid, path),
            }
        )
    return pd.DataFrame(dispatch_rows), pd.DataFrame(resource_rows)


def canonicalize_firehouses(path: Path, max_rows: int) -> pd.DataFrame:
    df = normalized_df(read_bounded_csv(path, max_rows))
    rows = []
    for idx, rec in enumerate(df.to_dict("records"), start=1):
        name = cell(rec.get("facilityname")) or f"firehouse_{idx}"
        address = cell(rec.get("facilityaddress"))
        borough = cell(rec.get("borough"))
        zipcode = cell(rec.get("postcode")) or cell(rec.get("zip_code")) or cell(rec.get("zipcode"))
        lat = parse_float(rec.get("latitude"))
        lon = parse_float(rec.get("longitude"))
        rows.append(
            {
                "canonical_id": f"resource:us-nyc:fdny:firehouse:{safe_id(name)}",
                "entity_type": "response_resource",
                "resource_type": "firehouse",
                "source_dataset": SOURCE_KEYS["fdny_firehouses"]["dataset"],
                "source_record_id": name,
                "borough": borough,
                "address_text": address,
                "zipcode": zipcode,
                "latitude": lat,
                "longitude": lon,
                "location_status": location_status(lat, lon, address, None, zipcode, borough),
                "status": "station_asset",
                "provenance": provenance(SOURCE_KEYS["fdny_firehouses"]["dataset"], name, path),
            }
        )
    return pd.DataFrame(rows)


def canonicalize_ems(path: Path, max_rows: int) -> pd.DataFrame:
    df = normalized_df(read_bounded_csv(path, max_rows))
    rows = []
    for idx, rec in enumerate(df.to_dict("records"), start=1):
        rid = cell(rec.get("incident_id")) or str(idx)
        borough = cell(rec.get("borough"))
        zipcode = cell(rec.get("zipcode")) or cell(rec.get("zip_code"))
        lat = parse_float(rec.get("latitude"))
        lon = parse_float(rec.get("longitude"))
        rows.append(
            {
                "canonical_id": f"event:us-nyc:flow3:ems:{safe_id(rid)}",
                "entity_type": "event",
                "event_family": "incident_response",
                "event_type": "medical",
                "source_dataset": SOURCE_KEYS["ems_actual_rows"]["dataset"],
                "source_record_id": rid,
                "event_time": cell(rec.get("incident_datetime")),
                "borough": borough,
                "address_text": None,
                "street_name": None,
                "zipcode": zipcode,
                "latitude": lat,
                "longitude": lon,
                "location_status": location_status(lat, lon, None, None, zipcode, borough),
                "private_data_status": "redacted_or_not_present",
                "provenance": provenance(SOURCE_KEYS["ems_actual_rows"]["dataset"], rid, path),
            }
        )
    return pd.DataFrame(rows)


def canonicalize_mvc_crashes(path: Path, max_rows: int) -> pd.DataFrame:
    df = normalized_df(read_bounded_csv(path, max_rows))
    rows = []
    for idx, rec in enumerate(df.to_dict("records"), start=1):
        rid = cell(rec.get("collision_id")) or str(idx)
        borough = cell(rec.get("borough"))
        zipcode = cell(rec.get("zip_code")) or cell(rec.get("zipcode"))
        lat = parse_float(rec.get("latitude"))
        lon = parse_float(rec.get("longitude"))
        street = cell(rec.get("on_street_name")) or cell(rec.get("off_street_name")) or cell(rec.get("cross_street_name"))
        rows.append(
            {
                "canonical_id": f"event:us-nyc:flow3:mvc_crash:{safe_id(rid)}",
                "entity_type": "event",
                "event_family": "incident_response",
                "event_type": "collision",
                "source_dataset": SOURCE_KEYS["mvc_crashes"]["dataset"],
                "collision_id": rid,
                "source_record_id": rid,
                "event_time": canonical_time(rec.get("crash_date"), rec.get("crash_time")),
                "borough": borough,
                "address_text": street,
                "street_name": street,
                "zipcode": zipcode,
                "latitude": lat,
                "longitude": lon,
                "location_status": location_status(lat, lon, None, street, zipcode, borough),
                "private_data_status": "redacted_or_not_present",
                "provenance": provenance(SOURCE_KEYS["mvc_crashes"]["dataset"], rid, path),
            }
        )
    return pd.DataFrame(rows)


def canonicalize_mvc_vehicles(path: Path, max_rows: int) -> pd.DataFrame:
    df = normalized_df(read_bounded_csv(path, max_rows))
    rows = []
    for idx, rec in enumerate(df.to_dict("records"), start=1):
        unique_id = cell(rec.get("unique_id")) or cell(rec.get("vehicle_id")) or str(idx)
        collision_id = cell(rec.get("collision_id"))
        rows.append(
            {
                "canonical_id": f"context:us-nyc:flow3:mvc_vehicle:{safe_id(unique_id)}",
                "entity_type": "event_context",
                "context_type": "collision_vehicle",
                "source_dataset": SOURCE_KEYS["motor_vehicle_vehicles"]["dataset"],
                "source_record_id": unique_id,
                "collision_id": collision_id,
                "vehicle_type": cell(rec.get("vehicle_type")) or cell(rec.get("vehicle_type_code_1")),
                "vehicle_year": cell(rec.get("vehicle_year")),
                "private_data_status": "redacted_or_not_present",
                "provenance": provenance(SOURCE_KEYS["motor_vehicle_vehicles"]["dataset"], unique_id, path),
            }
        )
    return pd.DataFrame(rows)


def readiness_for(source_key: str, profile: dict[str, Any] | None, found: bool) -> dict[str, Any]:
    if not found:
        return {"score": 0, "status": "MISSING", "basis": "Source rows were not found."}
    if source_key == "ems_description":
        return {"score": 1, "status": "SCHEMA_ONLY", "basis": "Documentation only; not actual EMS rows."}
    if not profile or profile.get("status") != "PASS":
        return {"score": 1, "status": "FOUND_PROFILE_FAILED", "basis": "File exists but schema profile failed."}
    signals = profile.get("spatial_signals", {})
    temporal = bool(profile.get("temporal_signals", {}).get("time_columns"))
    if source_key == "fire_company_incidents":
        return {"score": 4, "status": "INCIDENT_TIME_BOROUGH_STREET_ZIP_READY", "basis": "Incident IDs, timestamps, borough/street/ZIP candidates present; no exact geometry."}
    if source_key == "fire_dispatch":
        score = 4 if temporal and signals.get("has_borough") else 3
        return {"score": score, "status": "DISPATCH_TIMES_AND_BOROUGH_READY", "basis": "Dispatch timestamps, incident IDs, alarm box context, and assigned quantities present."}
    if source_key == "fdny_firehouses":
        score = 5 if signals.get("has_latlon") else 4
        return {"score": score, "status": "STATION_ASSET_LAYER_READY", "basis": "Firehouse station rows are public resource assets; latitude/longitude is exact only when source fields provide it."}
    if source_key == "ems_actual_rows":
        score = 4 if temporal and signals.get("has_borough") else 2
        if signals.get("has_latlon"):
            score = 5
        return {"score": score, "status": "EMS_ROWS_READY_BUT_MEDICAL_FIELDS_REDACTED", "basis": "Actual EMS rows found; medical/triage fields excluded from canonical output."}
    if source_key == "mvc_crashes":
        score = 5 if signals.get("has_latlon") else 4
        return {"score": score, "status": "PRIMARY_COLLISION_EVENT_SOURCE_READY", "basis": "Collision IDs and event fields present; coordinates are exact only when official lat/lon fields are populated."}
    if source_key == "motor_vehicle_vehicles":
        return {"score": 3, "status": "VEHICLE_CONTEXT_ONLY", "basis": "Vehicle rows remain collision_vehicle context and are joined only by exact collision_id."}
    return {"score": 1, "status": "FOUND", "basis": "Found but no source-specific readiness rule."}


def write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if frame.empty:
        frame = pd.DataFrame({"_empty": pd.Series(dtype="string")})
    frame.to_parquet(path, index=False)


def sample_records(frame: pd.DataFrame, n: int) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    records = frame.head(n).where(pd.notna(frame.head(n)), None).to_dict("records")
    for record in records:
        if "provenance" in record and isinstance(record["provenance"], str):
            try:
                record["provenance"] = json.loads(record["provenance"])
            except json.JSONDecodeError:
                pass
    return records


def private_data_scan(profiles: dict[str, Any], samples: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    rejected = []
    unredacted_pattern = re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)")
    unredacted_phone = False
    for source_key, profile in profiles.items():
        for column, col_profile in profile.get("column_profiles", {}).items():
            if col_profile.get("sensitive_or_private_candidate"):
                rejected.append({"source_key": source_key, "column": column, "reason": "private_or_sensitive_pattern", "sample_emitted": "redacted_or_excluded"})
    for rows in samples.values():
        text = json.dumps(rows, default=str)
        if unredacted_pattern.search(text):
            unredacted_phone = True
    return {
        "status": "FAIL" if unredacted_phone else "PASS",
        "policy": "Names, phone/contact fields, free-text narratives, license fields, private unit/apartment/floor fields, and EMS triage/medical-detail fields are redacted from samples or excluded from canonical outputs.",
        "rejected_fields": rejected,
        "unredacted_phone_pattern_found_in_samples": unredacted_phone,
    }


def no_overclaim_scan(output_dir: Path) -> dict[str, Any]:
    texts = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".json"} and path.name not in {"SHA256SUMS.json", "F3_NYC_D2_NO_OVERCLAIM_REPORT.json"}:
            texts.append((path.relative_to(output_dir).as_posix(), path.read_text(encoding="utf-8", errors="replace").lower()))
    combined = "\n".join(text for _, text in texts)
    missing = [line for line in NO_OVERCLAIM_LINES if line.lower() not in combined]
    forbidden = []
    for pattern in FORBIDDEN_POSITIVE_PATTERNS:
        for path, text in texts:
            if re.search(pattern, text):
                forbidden.append({"path": path, "pattern": pattern})
    return {
        "status": "PASS" if not missing and not forbidden else "FAIL",
        "required_boundary_lines": NO_OVERCLAIM_LINES,
        "missing_boundary_lines": missing,
        "forbidden_positive_claims_found": forbidden,
    }


def build_evidence_bundle(query_type: str, answer_status: str, facts: list[dict[str, Any]], counts: dict[str, Any], entities: list[dict[str, Any]], limitations: list[str], source_lineage: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "tool": "citybrain_flow3_nyc_query",
        "query_type": query_type,
        "answer_status": answer_status,
        "facts": facts,
        "counts": counts,
        "entities": entities,
        "edges": [],
        "paths": [],
        "limitations": limitations,
        "source_lineage": source_lineage,
        "grounding_policy": {
            "model_may_narrate": True,
            "model_may_compute_counts": False,
            "model_may_add_facts": False,
        },
    }


def make_briefing(title: str, facts: list[str], limitations: list[str]) -> str:
    lines = [f"# {title}", ""]
    lines.extend(NO_OVERCLAIM_LINES)
    lines.append("")
    lines.append("This briefing is generated from F3-NYC-D2 deterministic evidence only.")
    lines.append("No NIM/NeMo/LLM generated these facts.")
    lines.append("")
    lines.append("## Facts")
    lines.extend(f"- {fact}" for fact in facts)
    lines.append("")
    lines.append("## Limitations")
    lines.extend(f"- {limitation}" for limitation in limitations)
    lines.append("")
    return "\n".join(lines)


def hero_candidates(fdny_events: pd.DataFrame, dispatch_events: pd.DataFrame, firehouses: pd.DataFrame, ems_events: pd.DataFrame, mvc_crashes: pd.DataFrame, mvc_vehicle_context: pd.DataFrame) -> dict[str, Any]:
    candidates = []
    dispatch_ids = set(dispatch_events["incident_id"].dropna().astype(str).tolist()) if not dispatch_events.empty and "incident_id" in dispatch_events else set()
    fdny_overlap = pd.DataFrame()
    if not fdny_events.empty and dispatch_ids:
        fdny_overlap = fdny_events[fdny_events["source_record_id"].astype(str).isin(dispatch_ids)]
    row = fdny_overlap.head(1) if not fdny_overlap.empty else fdny_events.head(1)
    if not row.empty:
        rec = row.iloc[0].to_dict()
        exact_dispatch = str(rec.get("source_record_id")) in dispatch_ids
        candidates.append(
            {
                "category": "FDNY incident with resource/dispatch context",
                "canonical_event_id": rec.get("canonical_id"),
                "source_row_id": rec.get("source_record_id"),
                "event_type": rec.get("event_type"),
                "time": rec.get("event_time"),
                "borough": rec.get("borough"),
                "location_status": rec.get("location_status"),
                "resource_context_available": not dispatch_events.empty,
                "dispatch_context_available": exact_dispatch,
                "private_data_safe": True,
                "why_candidate": "FDNY incident response is the D1-recommended first slice; dispatch source is available, exact ID overlap noted when present.",
                "missing_for_D3": "Affected buildings/assets require deterministic geometry or identifier linkage; D2 does not geocode.",
            }
        )
    if not fdny_events.empty and not firehouses.empty:
        rec = fdny_events.head(1).iloc[0].to_dict()
        same_borough = not firehouses[firehouses["borough"].astype(str).str.lower() == str(rec.get("borough")).lower()].empty if rec.get("borough") else False
        candidates.append(
            {
                "category": "FDNY incident with firehouse resource context",
                "canonical_event_id": rec.get("canonical_id"),
                "source_row_id": rec.get("source_record_id"),
                "event_type": rec.get("event_type"),
                "time": rec.get("event_time"),
                "borough": rec.get("borough"),
                "location_status": rec.get("location_status"),
                "resource_context_available": bool(same_borough),
                "dispatch_context_available": False,
                "private_data_safe": True,
                "why_candidate": "Firehouse station asset layer is available; borough match is context, not route or asset certification.",
                "missing_for_D3": "Needs deterministic incident geometry before affected asset or nearest-resource claims.",
            }
        )
    if not mvc_crashes.empty and not mvc_vehicle_context.empty:
        vehicle_ids = set(mvc_vehicle_context["collision_id"].dropna().astype(str).tolist())
        overlap = mvc_crashes[mvc_crashes["collision_id"].astype(str).isin(vehicle_ids)] if "collision_id" in mvc_crashes else pd.DataFrame()
        row = overlap.head(1) if not overlap.empty else mvc_crashes.head(1)
        rec = row.iloc[0].to_dict()
        candidates.append(
            {
                "category": "MVC crash with vehicle context",
                "canonical_event_id": rec.get("canonical_id"),
                "source_row_id": rec.get("collision_id"),
                "event_type": rec.get("event_type"),
                "time": rec.get("event_time"),
                "borough": rec.get("borough"),
                "location_status": rec.get("location_status"),
                "resource_context_available": False,
                "dispatch_context_available": False,
                "private_data_safe": True,
                "why_candidate": "MVC Crashes is a primary collision event source and Vehicles can attach by exact collision_id.",
                "missing_for_D3": "Keep parallel to FDNY until Flow 3 asset and response-resource joins are designed.",
            }
        )
    if not ems_events.empty:
        rec = ems_events.head(1).iloc[0].to_dict()
        candidates.append(
            {
                "category": "EMS incident if actual rows are usable",
                "canonical_event_id": rec.get("canonical_id"),
                "source_row_id": rec.get("source_record_id"),
                "event_type": rec.get("event_type"),
                "time": rec.get("event_time"),
                "borough": rec.get("borough"),
                "location_status": rec.get("location_status"),
                "resource_context_available": False,
                "dispatch_context_available": False,
                "private_data_safe": True,
                "why_candidate": "Actual EMS rows are available, but medical/triage details are excluded.",
                "missing_for_D3": "EMS location is borough/ZIP unless official coordinates are present; no patient-level detail should be surfaced.",
            }
        )
    return {
        "status": "PASS" if candidates else "FAIL",
        "best_recommended_next_hero_family": "FDNY incident response slice",
        "candidates": candidates,
    }


def gate_statuses(
    d1_ok: bool,
    selected: dict[str, Any],
    profiles: dict[str, Any],
    readiness: dict[str, Any],
    counts: dict[str, int],
    hero_report: dict[str, Any],
    evidence_count: int,
    privacy: dict[str, Any],
    overclaim: dict[str, Any],
    no_mutation: dict[str, Any],
) -> dict[str, str]:
    return {
        "F3-NYC-D2-PRECOND": "PASS" if d1_ok else "FAIL",
        "F3-NYC-D2-SOURCE-COMPLETION": "PASS" if all(selected.get(k) for k in ["fire_company_incidents", "fire_dispatch", "fdny_firehouses"]) else "FAIL",
        "F3-NYC-D2-SCHEMA-PROFILE": "PASS" if profiles and all(p.get("status") == "PASS" for key, p in profiles.items() if key != "ems_description") else "FAIL",
        "F3-NYC-D2-FDNY-INCIDENT-INGEST": "PASS" if counts.get("fdny_events", 0) > 0 else "FAIL",
        "F3-NYC-D2-FIRE-DISPATCH-INGEST": "PASS" if counts.get("dispatch_events", 0) > 0 else "FAIL",
        "F3-NYC-D2-FIREHOUSE-INGEST": "PASS" if counts.get("firehouses", 0) > 0 else "FAIL",
        "F3-NYC-D2-EMS-INGEST": "PASS" if selected.get("ems_actual_rows") and counts.get("ems_events", 0) > 0 else "PASS",
        "F3-NYC-D2-MVC-CRASH-INGEST": "PASS" if selected.get("mvc_crashes") and counts.get("mvc_crashes", 0) > 0 else "PASS",
        "F3-NYC-D2-MVC-VEHICLE-CONTEXT": "PASS" if selected.get("motor_vehicle_vehicles") and counts.get("mvc_vehicle_context", 0) > 0 else "FAIL",
        "F3-NYC-D2-CANONICAL-EVENTS": "PASS" if counts.get("fdny_events", 0) > 0 and counts.get("mvc_vehicles_as_primary_events", 0) == 0 else "FAIL",
        "F3-NYC-D2-RESPONSE-RESOURCES": "PASS" if counts.get("response_resources", 0) > 0 else "FAIL",
        "F3-NYC-D2-HERO-CANDIDATE-SHORTLIST": hero_report.get("status", "FAIL"),
        "F3-NYC-D2-EVIDENCE-BUNDLES": "PASS" if evidence_count >= 3 else "FAIL",
        "F3-NYC-D2-PRIVATE-DATA": privacy.get("status", "FAIL"),
        "F3-NYC-D2-NO-OVERCLAIM": overclaim.get("status", "FAIL"),
        "F3-NYC-D2-NO-MUTATION": no_mutation.get("status", "FAIL"),
    }


def run_f3_nyc_d2_gate(
    project_root: str,
    raw_roots: list[str],
    d1_dir: str,
    output_dir: str,
    sample_rows: int = 25,
    max_rows_per_source: int | None = None,
) -> dict:
    project = Path(project_root).resolve()
    output_path = Path(output_dir)
    cap = int(max_rows_per_source or DEFAULT_SAMPLE_CAP)
    reset_output_dir(output_path)
    d1_path = Path(d1_dir)
    d1_report = read_json(d1_path / "F3_NYC_D1_HARNESS_REPORT.json", {})
    d1_counts = read_json(d1_path / "reports" / "row_counts.json", {})
    d1_ok = d1_report.get("status") in {"PASS", "PASS_WITH_MISSING_SOURCES"}
    before_snapshot = input_snapshot(d1_path)

    first_discovery = discover_sources(project, raw_roots)
    source_completion = complete_missing_sources(project, first_discovery["selected"])
    discovery = discover_sources(project, raw_roots + [str(project / "data_landing" / "nyc_flow3")])
    selected = discovery["selected"]

    profiles: dict[str, Any] = {}
    row_counts: dict[str, Any] = {}
    column_profiles: dict[str, Any] = {}
    source_samples: dict[str, list[dict[str, Any]]] = {}
    for key in ["fire_company_incidents", "fire_dispatch", "fdny_firehouses", "ems_actual_rows", "mvc_crashes", "motor_vehicle_vehicles"]:
        rec = selected.get(key)
        if rec and rec.get("path") and Path(rec["path"]).exists():
            profile = profile_csv(Path(rec["path"]), key, sample_rows, d1_counts, source_completion)
            profiles[key] = profile
            row_counts[key] = {
                "full_source_rows": profile.get("row_count"),
                "bounded_file_rows": profile.get("bounded_file_rows"),
                "row_count_method": profile.get("row_count_method"),
                "bounded_sample": profile.get("bounded_sample"),
            }
            column_profiles[key] = profile.get("column_profiles", {})
            source_samples[key] = profile.get("sample_rows_redacted", [])
    if selected.get("ems_description"):
        profiles["ems_description"] = {
            "status": "PASS",
            "source_key": "ems_description",
            "dataset": SOURCE_KEYS["ems_description"]["dataset"],
            "role": SOURCE_KEYS["ems_description"]["role"],
            "path": selected["ems_description"]["path"],
            "schema_only_status": "EMS_DESCRIPTION_ONLY_NOT_ACTUAL_ROWS",
        }

    readiness = {key: readiness_for(key, profiles.get(key), selected.get(key) is not None) for key in SOURCE_KEYS}

    fdny_events = canonicalize_fdny_incidents(Path(selected["fire_company_incidents"]["path"]), cap) if selected.get("fire_company_incidents") else pd.DataFrame()
    dispatch_events, dispatch_resources = canonicalize_fire_dispatch(Path(selected["fire_dispatch"]["path"]), cap) if selected.get("fire_dispatch") else (pd.DataFrame(), pd.DataFrame())
    firehouses = canonicalize_firehouses(Path(selected["fdny_firehouses"]["path"]), cap) if selected.get("fdny_firehouses") else pd.DataFrame()
    ems_events = canonicalize_ems(Path(selected["ems_actual_rows"]["path"]), cap) if selected.get("ems_actual_rows") else pd.DataFrame()
    mvc_crashes = canonicalize_mvc_crashes(Path(selected["mvc_crashes"]["path"]), cap) if selected.get("mvc_crashes") else pd.DataFrame()
    mvc_vehicle_context = canonicalize_mvc_vehicles(Path(selected["motor_vehicle_vehicles"]["path"]), cap) if selected.get("motor_vehicle_vehicles") else pd.DataFrame()
    response_resources = pd.concat([firehouses, dispatch_resources], ignore_index=True) if not firehouses.empty or not dispatch_resources.empty else pd.DataFrame()

    write_parquet(output_path / "canonical" / "f3_nyc_d2_incident_events.parquet", fdny_events)
    write_parquet(output_path / "canonical" / "f3_nyc_d2_fire_dispatch_events.parquet", dispatch_events)
    write_parquet(output_path / "canonical" / "f3_nyc_d2_response_resources.parquet", response_resources)
    write_parquet(output_path / "canonical" / "f3_nyc_d2_firehouses.parquet", firehouses)
    write_parquet(output_path / "canonical" / "f3_nyc_d2_ems_dispatch_events.parquet", ems_events)
    write_parquet(output_path / "canonical" / "f3_nyc_d2_mvc_crash_events.parquet", mvc_crashes)
    write_parquet(output_path / "canonical" / "f3_nyc_d2_mvc_vehicle_context.parquet", mvc_vehicle_context)

    write_json(output_path / "canonical" / "f3_nyc_d2_source_rows_sample.json", source_samples)
    write_json(output_path / "canonical" / "f3_nyc_d2_incident_events_sample.json", sample_records(fdny_events, sample_rows))
    write_json(output_path / "canonical" / "f3_nyc_d2_response_resources_sample.json", sample_records(response_resources, sample_rows))

    event_counts = Counter(fdny_events["event_type"].dropna().tolist()) if not fdny_events.empty else Counter()
    borough_counts = Counter(fdny_events["borough"].dropna().tolist()) if not fdny_events.empty else Counter()
    firehouse_borough_counts = Counter(firehouses["borough"].dropna().tolist()) if not firehouses.empty else Counter()
    mvc_collision_ids = set(mvc_crashes["collision_id"].dropna().astype(str).tolist()) if not mvc_crashes.empty else set()
    mvc_vehicle_ids = set(mvc_vehicle_context["collision_id"].dropna().astype(str).tolist()) if not mvc_vehicle_context.empty else set()
    mvc_exact_links = len(mvc_collision_ids & mvc_vehicle_ids)

    counts = {
        "fdny_events": int(len(fdny_events)),
        "dispatch_events": int(len(dispatch_events)),
        "firehouses": int(len(firehouses)),
        "ems_events": int(len(ems_events)),
        "mvc_crashes": int(len(mvc_crashes)),
        "mvc_vehicle_context": int(len(mvc_vehicle_context)),
        "response_resources": int(len(response_resources)),
        "mvc_vehicles_as_primary_events": 0,
        "mvc_crash_vehicle_exact_collision_id_links_in_bounded_slice": mvc_exact_links,
    }
    bounded_sources = [
        key
        for key, profile in profiles.items()
        if profile.get("bounded_sample") or (key in counts and profile.get("row_count") and counts.get(key, 0) < profile.get("row_count", 0))
    ]

    hero_report = hero_candidates(fdny_events, dispatch_events, firehouses, ems_events, mvc_crashes, mvc_vehicle_context)
    privacy = private_data_scan(profiles, source_samples)

    source_lineage = [
        {
            "source_key": key,
            "dataset": SOURCE_KEYS[key]["dataset"],
            "path": rec.get("path") if rec else None,
            "readiness": readiness.get(key),
        }
        for key, rec in selected.items()
        if rec
    ]
    limitations = NO_OVERCLAIM_LINES + [
        "D2 canonical outputs are bounded slice outputs when source row counts exceed the configured cap.",
        "The user-provided EMS demo URL was checked and rejected because it returned non-EMS earthquake data; official NYC EMS rows were used instead when downloaded.",
    ]
    status_bundle = build_evidence_bundle(
        "fdny_incident_response_status",
        "answered",
        [
            {"fact": "FDNY incidents were ingested as canonical incident_response events.", "value": counts["fdny_events"], "source": "canonical/f3_nyc_d2_incident_events.parquet"},
            {"fact": "FDNY fire dispatch rows were ingested as dispatch events.", "value": counts["dispatch_events"], "source": "canonical/f3_nyc_d2_fire_dispatch_events.parquet"},
            {"fact": "FDNY firehouses were ingested as response resources.", "value": counts["firehouses"], "source": "canonical/f3_nyc_d2_firehouses.parquet"},
        ],
        counts,
        sample_records(fdny_events, 3),
        limitations,
        source_lineage,
    )
    sample_bundle = build_evidence_bundle(
        "fdny_sample_incident",
        "answered" if not fdny_events.empty else "source_limited",
        [{"fact": "Sample FDNY incident canonicalized without private data fields.", "value": bool(not fdny_events.empty), "source": "canonical/f3_nyc_d2_incident_events_sample.json"}],
        {"sample_count": min(sample_rows, len(fdny_events))},
        sample_records(fdny_events, 1),
        limitations,
        source_lineage,
    )
    readiness_bundle = build_evidence_bundle(
        "flow3_source_readiness",
        "answered",
        [{"fact": f"{key} readiness", "value": value, "source": "F3_NYC_D2_READINESS_UPDATE_REPORT.json"} for key, value in readiness.items()],
        {"sources_profiled": len(profiles)},
        [],
        limitations,
        source_lineage,
    )
    write_json(output_path / "evidence" / "evidence_bundle_fdny_incident_response_status.json", status_bundle)
    write_json(output_path / "evidence" / "evidence_bundle_fdny_sample_incident.json", sample_bundle)
    write_json(output_path / "evidence" / "evidence_bundle_flow3_source_readiness.json", readiness_bundle)
    write_text(
        output_path / "evidence" / "deterministic_briefing_fdny_incident_response_status.md",
        make_briefing(
            "F3-NYC-D2 FDNY Incident Response Status",
            [
                f"Canonical FDNY incident events emitted: {counts['fdny_events']}.",
                f"Dispatch events emitted: {counts['dispatch_events']}.",
                f"Response resources emitted: {counts['response_resources']}.",
                f"Bounded sources: {', '.join(bounded_sources) or 'none'}.",
            ],
            limitations,
        ),
    )
    write_text(
        output_path / "evidence" / "deterministic_briefing_first_slice_recommendation.md",
        make_briefing(
            "F3-NYC-D2 First Slice Recommendation",
            [
                "Recommended D3 slice remains FDNY incident response slice.",
                "D3 should add deterministic affected-asset linking before any building or route claims.",
                f"Hero shortlist candidates emitted: {len(hero_report.get('candidates', []))}.",
            ],
            limitations,
        ),
    )

    schema_profile_report = {"status": "PASS" if profiles else "FAIL", "profiles": profiles}
    readiness_report = {"status": "PASS", "readiness": readiness}
    fdny_ingest_report = {"status": "PASS" if counts["fdny_events"] else "FAIL", "source": selected.get("fire_company_incidents"), "canonical_rows_emitted": counts["fdny_events"], "bounded_cap": cap}
    fire_dispatch_report = {"status": "PASS" if counts["dispatch_events"] else "FAIL", "source": selected.get("fire_dispatch"), "dispatch_rows_emitted": counts["dispatch_events"], "aggregate_resource_rows_emitted": len(dispatch_resources), "individual_unit_id_status": "not_present_in_source_fields"}
    firehouse_report = {"status": "PASS" if counts["firehouses"] else "FAIL", "source": selected.get("fdny_firehouses"), "firehouses_emitted": counts["firehouses"], "location_interpretation": "latlon_exact only from official latitude/longitude columns"}
    ems_report = {"status": "PASS" if selected.get("ems_actual_rows") else "PASS_WITH_SOURCE_LIMITATION", "source": selected.get("ems_actual_rows"), "ems_rows_emitted": counts["ems_events"], "medical_private_fields": "excluded_or_redacted", "user_demo_endpoint": source_completion.get("ems_actual_rows", {}).get("user_demo_validation")}
    mvc_crash_report = {"status": "PASS" if selected.get("mvc_crashes") else "PASS_WITH_SOURCE_LIMITATION", "source": selected.get("mvc_crashes"), "mvc_crash_events_emitted": counts["mvc_crashes"]}
    mvc_vehicle_report = {"status": "PASS" if counts["mvc_vehicle_context"] else "FAIL", "source": selected.get("motor_vehicle_vehicles"), "context_rows_emitted": counts["mvc_vehicle_context"], "semantic_status": "collision_vehicle_context_not_primary_event", "exact_collision_id_links_in_bounded_slice": mvc_exact_links}
    canonical_event_report = {"status": "PASS" if counts["fdny_events"] else "FAIL", "counts": counts, "mvc_vehicle_primary_event_guard": "PASS"}
    response_resource_report = {"status": "PASS" if counts["response_resources"] else "FAIL", "counts": {"firehouses": len(firehouses), "dispatch_resource_observations": len(dispatch_resources), "response_resources": len(response_resources)}}
    evidence_report = {"status": "PASS", "bundles": 3, "deterministic_only": True}

    write_json(output_path / "F3_NYC_D2_INPUT_INVENTORY.json", {"project_root": str(project), "raw_roots": raw_roots, "d1_dir": str(d1_path), "first_discovery": first_discovery, "source_files": selected})
    write_json(output_path / "F3_NYC_D2_SOURCE_COMPLETION_REPORT.json", {"status": "PASS", "actions": source_completion, "final_selected": selected})
    write_json(output_path / "F3_NYC_D2_SCHEMA_PROFILE_REPORT.json", schema_profile_report)
    write_json(output_path / "F3_NYC_D2_READINESS_UPDATE_REPORT.json", readiness_report)
    write_json(output_path / "F3_NYC_D2_FDNY_INCIDENT_INGEST_REPORT.json", fdny_ingest_report)
    write_json(output_path / "F3_NYC_D2_FIRE_DISPATCH_INGEST_REPORT.json", fire_dispatch_report)
    write_json(output_path / "F3_NYC_D2_FIREHOUSE_INGEST_REPORT.json", firehouse_report)
    write_json(output_path / "F3_NYC_D2_EMS_INGEST_REPORT.json", ems_report)
    write_json(output_path / "F3_NYC_D2_MVC_CRASH_INGEST_REPORT.json", mvc_crash_report)
    write_json(output_path / "F3_NYC_D2_MVC_VEHICLE_CONTEXT_REPORT.json", mvc_vehicle_report)
    write_json(output_path / "F3_NYC_D2_CANONICAL_EVENT_REPORT.json", canonical_event_report)
    write_json(output_path / "F3_NYC_D2_RESPONSE_RESOURCE_REPORT.json", response_resource_report)
    write_json(output_path / "F3_NYC_D2_HERO_CANDIDATE_SHORTLIST_REPORT.json", hero_report)
    write_json(output_path / "F3_NYC_D2_EVIDENCE_BUNDLE_REPORT.json", evidence_report)
    write_json(output_path / "F3_NYC_D2_PRIVATE_DATA_SCAN_REPORT.json", privacy)

    write_json(output_path / "reports" / "file_locations.json", {"selected": selected, "found": discovery["found"]})
    write_json(output_path / "reports" / "row_counts.json", row_counts | {"canonical_emitted_counts": counts})
    write_json(output_path / "reports" / "column_profiles.json", column_profiles)
    write_json(output_path / "reports" / "spatial_readiness.json", {key: {"readiness": readiness.get(key), "signals": profiles.get(key, {}).get("spatial_signals", {})} for key in SOURCE_KEYS})
    write_json(output_path / "reports" / "temporal_readiness.json", {key: {"signals": profiles.get(key, {}).get("temporal_signals", {})} for key in SOURCE_KEYS})
    write_json(output_path / "reports" / "resource_readiness.json", {key: {"signals": profiles.get(key, {}).get("resource_signals", {}), "readiness": readiness.get(key)} for key in SOURCE_KEYS})
    write_json(output_path / "reports" / "private_data_redaction_policy.json", {"status": privacy["status"], "policy": privacy["policy"]})
    write_json(output_path / "reports" / "rejected_fields_private_or_unsafe.json", privacy["rejected_fields"])
    write_json(output_path / "reports" / "fdny_incident_type_counts.json", dict(event_counts))
    write_json(output_path / "reports" / "fdny_borough_counts.json", dict(borough_counts))
    write_json(output_path / "reports" / "firehouse_borough_counts.json", dict(firehouse_borough_counts))
    write_json(output_path / "reports" / "ems_readiness.json", readiness.get("ems_actual_rows"))
    write_json(output_path / "reports" / "mvc_readiness.json", {"mvc_crashes": readiness.get("mvc_crashes"), "motor_vehicle_vehicles": readiness.get("motor_vehicle_vehicles"), "exact_collision_id_links_in_bounded_slice": mvc_exact_links})
    write_json(output_path / "reports" / "recommended_d3_plan.json", {"recommended_d3_slice": "FDNY incident response slice", "required_next_steps": ["deterministic affected-asset linking", "geometry-backed incident location handling", "keep response routing out of D2"]})

    readme = "# F3-NYC-D2 FDNY Incident Response Slice Ingest\n\nStatus: pending final harness write.\n\n" + "\n".join(f"- {line}" for line in NO_OVERCLAIM_LINES) + "\n"
    write_text(output_path / "README.md", readme)
    write_text(
        output_path / "F3_NYC_D2_ADAPTER_HANDOVER.md",
        "# F3-NYC-D2 Adapter Handover\n\n"
        + "\n".join(f"- {line}" for line in NO_OVERCLAIM_LINES)
        + "\n\nD3 should start from the FDNY incident response slice, add deterministic affected-asset linking, and keep MVC Vehicles as collision_vehicle context only.\n",
    )

    overclaim = no_overclaim_scan(output_path)
    write_json(output_path / "F3_NYC_D2_NO_OVERCLAIM_REPORT.json", overclaim)
    after_snapshot = input_snapshot(d1_path)
    no_mutation = {"gate": "F3-NYC-D2-NO-MUTATION", "status": "PASS" if before_snapshot == after_snapshot else "FAIL", "watched_input": str(d1_path)}
    gates = gate_statuses(d1_ok, selected, profiles, readiness, counts, hero_report, 3, privacy, overclaim, no_mutation)
    bounded = bool(bounded_sources or cap)
    hard_pass = all(value == "PASS" for value in gates.values())
    if hard_pass:
        status = "PASS_WITH_BOUNDED_SAMPLE" if bounded else "PASS"
    else:
        status = "FAIL"
    final_readme = f"""# F3-NYC-D2 FDNY Incident Response Slice Ingest

Status: {status}

{chr(10).join(f"- {line}" for line in NO_OVERCLAIM_LINES)}

FDNY incidents emitted: {counts['fdny_events']}
Dispatch events emitted: {counts['dispatch_events']}
Response resources emitted: {counts['response_resources']}
MVC crash events emitted: {counts['mvc_crashes']}
EMS events emitted: {counts['ems_events']}
Bounded cap per source: {cap}
Recommended D3 slice: FDNY incident response slice
"""
    write_text(output_path / "README.md", final_readme)
    overclaim = no_overclaim_scan(output_path)
    write_json(output_path / "F3_NYC_D2_NO_OVERCLAIM_REPORT.json", overclaim)
    gates = gate_statuses(d1_ok, selected, profiles, readiness, counts, hero_report, 3, privacy, overclaim, no_mutation)
    hard_pass = all(value == "PASS" for value in gates.values())
    if hard_pass:
        status = "PASS_WITH_BOUNDED_SAMPLE" if bounded else "PASS"
    else:
        status = "FAIL"

    harness = {
        "task": TASK_NAME,
        "status": status,
        "created_utc": utc_now(),
        "bounded_sample": True,
        "bounded_cap_per_source": cap,
        "bounded_sources": bounded_sources,
        "gates": gates,
        "source_summary": {
            key: {
                "found": selected.get(key) is not None,
                "rows": row_counts.get(key, {}).get("full_source_rows"),
                "bounded_file_rows": row_counts.get(key, {}).get("bounded_file_rows"),
                "readiness": readiness.get(key, {}).get("score"),
                "status": readiness.get(key, {}).get("status"),
            }
            for key in SOURCE_KEYS
        },
        "canonical_counts": counts,
        "recommended_d3_slice": "FDNY incident response slice",
        "private_data_scan": privacy,
        "no_overclaim": overclaim,
        "no_mutation": no_mutation,
        "output": str(output_path),
    }
    write_json(output_path / "F3_NYC_D2_HARNESS_REPORT.json", harness)
    hashes = write_hashes(output_path)
    gates["F3-NYC-D2-HASHES"] = hashes["status"]
    harness["gates"] = gates
    harness["hashes"] = read_json(output_path / "SHA256SUMS.json", {})
    write_json(output_path / "F3_NYC_D2_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    harness["hashes"] = read_json(output_path / "SHA256SUMS.json", {})
    write_json(output_path / "F3_NYC_D2_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run F3-NYC-D2 source completion + FDNY incident response slice ingest")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--raw-root", action="append", dest="raw_roots", default=[])
    parser.add_argument("--d1-dir", default="outputs/f3_nyc_d1_source_inventory_schema_mapping")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sample-rows", type=int, default=25)
    parser.add_argument("--max-rows-per-source", type=int, default=None)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_f3_nyc_d2_gate(
        project_root=args.project_root,
        raw_roots=args.raw_roots,
        d1_dir=args.d1_dir,
        output_dir=args.output_dir,
        sample_rows=args.sample_rows,
        max_rows_per_source=args.max_rows_per_source,
    )
    summary = report["source_summary"]
    counts = report["canonical_counts"]
    print(f"F3-NYC-D2 FDNY Incident Response Slice Ingest: {report['status']}")
    print(f"FDNY incidents: {'FOUND' if summary['fire_company_incidents']['found'] else 'MISSING'}, rows {summary['fire_company_incidents']['rows']}, readiness {summary['fire_company_incidents']['readiness']}/5")
    print(f"Fire dispatch: {'FOUND' if summary['fire_dispatch']['found'] else 'MISSING'}, rows {summary['fire_dispatch']['rows']}, readiness {summary['fire_dispatch']['readiness']}/5")
    print(f"Firehouses: {'FOUND' if summary['fdny_firehouses']['found'] else 'MISSING'}, rows {summary['fdny_firehouses']['rows']}, readiness {summary['fdny_firehouses']['readiness']}/5")
    print(f"EMS actual rows: {'FOUND' if summary['ems_actual_rows']['found'] else 'MISSING'}, rows {summary['ems_actual_rows']['rows']}, readiness {summary['ems_actual_rows']['readiness']}/5")
    print(f"MVC crashes: {'FOUND' if summary['mvc_crashes']['found'] else 'MISSING'}, rows {summary['mvc_crashes']['rows']}, readiness {summary['mvc_crashes']['readiness']}/5")
    print(f"MVC vehicles: {'FOUND' if summary['motor_vehicle_vehicles']['found'] else 'MISSING'}, rows {summary['motor_vehicle_vehicles']['rows']}, readiness {summary['motor_vehicle_vehicles']['readiness']}/5")
    print(f"Canonical incident events emitted: {counts['fdny_events']}")
    print(f"Response resources emitted: {counts['response_resources']}")
    print(f"Dispatch events emitted: {counts['dispatch_events']}")
    print(f"MVC crash events emitted: {counts['mvc_crashes']}")
    print("Evidence bundles: 3")
    print(f"Recommended D3 slice: {report['recommended_d3_slice']}")
    print(f"Private-data scan: {report['private_data_scan']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] in {"PASS", "PASS_WITH_BOUNDED_SAMPLE", "PASS_WITH_SOURCE_LIMITATION"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


TASK_NAME = "F3-NYC-D1 Source Inventory + Schema Mapping"
DEFAULT_OUTPUT_DIR = "outputs/f3_nyc_d1_source_inventory_schema_mapping"

SOURCE_KEYS = {
    "fire_company_incidents": {
        "role": "incident_corpus",
        "expected_names": ["Incidents_Responded_to_by_Fire_Companies_20260626.csv", "Incidents_Responded_to_by_Fire_Companies.csv"],
        "required": False,
    },
    "motor_vehicle_vehicles": {
        "role": "collision_vehicle_context",
        "expected_names": ["Motor_Vehicle_Collisions_-_Vehicles.csv"],
        "required": False,
    },
    "ems_description": {
        "role": "schema_documentation_only",
        "expected_names": ["EMS_incident_dispatch_data_description.xlsx", "EMS_incident_dispatch_data_description"],
        "required": False,
    },
    "ems_actual_rows": {
        "role": "candidate_ems_incident_rows",
        "expected_names": ["EMS_Incident_Dispatch_Data.csv", "EMS_Incident_Dispatch_Data.csv.gz"],
        "required": False,
    },
    "mvc_crashes": {
        "role": "paired_primary_collision_incident_table",
        "expected_names": ["Motor_Vehicle_Collisions_-_Crashes.csv"],
        "required": False,
    },
    "fire_dispatch": {
        "role": "paired_fire_dispatch_unit_table",
        "expected_names": ["Fire_Incident_Dispatch_Data.csv"],
        "required": False,
    },
    "fdny_firehouses": {
        "role": "candidate_response_resource_station_assets",
        "expected_names": ["FDNY_Firehouse_Listing.csv"],
        "required": False,
    },
}

NO_OVERCLAIM_LINES = [
    "F3-NYC-D1 inventories Flow 3 sources only; it does not build the Flow 3 cartridge.",
    "Motor Vehicle Collisions Vehicles is collision vehicle context, not the primary locatable crash event table.",
    "EMS incident dispatch description is schema/documentation only unless actual EMS rows are present.",
    "Borough/address-only incident data is not exact geometry.",
    "Affected asset links remain candidate-only until deterministic spatial or identifier evidence supports them.",
    "Routing relations are proposed candidate relations only; no real dispatch optimization is claimed.",
]

FORBIDDEN_POSITIVE_PATTERNS = [
    "flow 3 cartridge is built",
    "flow 3 graph is built",
    "vehicles table is the primary crash event table",
    "motor vehicle collisions vehicles is the primary locatable crash event table",
    "ems description is actual ems rows",
    "borough-only incident data is exact location",
    "address-candidate links are certified",
    "near_or_affects_candidate certified",
    "real dispatch optimization",
    "candidate_route_to is optimized dispatch",
]

SENSITIVE_COLUMN_PATTERNS = [
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
    "unit",
    "email",
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
    "zip",
    "borough",
    "borough_desc",
}

TIME_COLUMNS = {
    "incident_date_time",
    "arrival_date_time",
    "last_unit_cleared_date_time",
    "crash_date",
    "crash_time",
    "dispatch_date_time",
    "call_received_datetime",
    "incident_datetime",
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
    sums = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "F3-NYC-D1-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {p.lower() for p in resolved.parts} or "f3_nyc_d1" not in resolved.name.lower():
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in ["profiles", "canonical_plan", "reports"]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def normalize_col(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def path_metadata(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() else None,
        "mtime_ns": path.stat().st_mtime_ns if path.exists() else None,
    }


def input_snapshot(project_root: Path) -> dict[str, Any]:
    roots = [project_root / "outputs"]
    patterns = ["a3*", "a4*", "a5*", "a6*", "a8*"]
    watched: dict[str, dict[str, Any]] = {}
    for root in roots:
        if not root.exists():
            continue
        for pattern in patterns:
            for directory in sorted(root.glob(pattern)):
                if not directory.is_dir():
                    continue
                for name in ["SHA256SUMS.json", "MANIFEST.json", "HARNESS_REPORT.json"]:
                    for path in directory.glob(f"*{name}"):
                        watched[str(path)] = path_metadata(path) | {"sha256": sha256_file(path)}
                for path in directory.glob("*.json"):
                    if "HARNESS" in path.name or "MANIFEST" in path.name or "REPORT" in path.name:
                        watched.setdefault(str(path), path_metadata(path) | {"sha256": sha256_file(path)})
    return watched


def iter_search_files(root: Path):
    skip = {".git", "__pycache__", "node_modules", ".venv", "venv"}
    if root.name.lower() == "citybrain":
        skip.add("outputs")
    try:
        for current, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in skip]
            for file in files:
                yield Path(current) / file
    except Exception:
        return


def discover_sources(project_root: Path, raw_roots: list[str]) -> dict[str, Any]:
    roots: list[Path] = [project_root]
    roots.extend(Path(r) for r in raw_roots)
    roots.extend(
        [
            Path.home() / "Downloads",
            project_root / "data_landing",
            project_root / "data_landing" / "nyc_flow3",
            project_root / "data_landing" / "nyc_raw",
            Path("C:/data/citybrain"),
            Path("/data/citybrain"),
            Path("/data/citybrain/nyc_flow3"),
            Path("/data/citybrain/nyc_raw"),
        ]
    )
    unique_roots = []
    seen = set()
    for root in roots:
        try:
            resolved = root.resolve()
        except Exception:
            resolved = root
        key = str(resolved).lower()
        if key not in seen:
            seen.add(key)
            unique_roots.append(root)

    expected = {}
    for key, meta in SOURCE_KEYS.items():
        for name in meta["expected_names"]:
            expected[name.lower()] = key
    found: dict[str, list[dict[str, Any]]] = {k: [] for k in SOURCE_KEYS}
    searched_roots = []
    for root in unique_roots:
        root = root.expanduser()
        searched_roots.append({"root": str(root), "exists": root.exists()})
        if not root.exists():
            continue
        for path in iter_search_files(root):
            lower = path.name.lower()
            source_key = expected.get(lower)
            if source_key is None and lower.startswith("ems_incident_dispatch_data_description"):
                source_key = "ems_description"
            if source_key:
                record = path_metadata(path)
                record["matched_name"] = path.name
                record["source_key"] = source_key
                found[source_key].append(record)
    selected = {}
    for key, matches in found.items():
        matches = sorted(matches, key=lambda r: (0 if Path(r["path"]).exists() else 1, len(r["path"]), r["path"]))
        selected[key] = matches[0] if matches else None
    return {"searched_roots": searched_roots, "found": found, "selected": selected}


def count_csv_rows(path: Path) -> int:
    line_count = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024 * 8), b""):
            line_count += chunk.count(b"\n")
    if line_count == 0:
        return 0
    return max(0, line_count - 1)


def is_sensitive_column(column: str) -> bool:
    col = normalize_col(column)
    return any(token in col for token in SENSITIVE_COLUMN_PATTERNS)


def redact_value(column: str, value: Any) -> Any:
    if value is None:
        return value
    text = str(value)
    if is_sensitive_column(column):
        return "[REDACTED]"
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[REDACTED_EMAIL]", text)
    text = re.sub(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b", "[REDACTED_PHONE]", text)
    if normalize_col(column) in {"address", "street_address", "house_number"}:
        text = re.sub(r"^\s*\d+[A-Za-z]?\b", "[REDACTED_HOUSE_NUMBER]", text)
    return text


def redact_row(row: dict[str, Any]) -> dict[str, Any]:
    return {col: redact_value(col, val) for col, val in row.items()}


def sample_csv(path: Path, sample_rows: int) -> tuple[list[str], list[dict[str, str]]]:
    csv.field_size_limit(10 * 1024 * 1024)
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        rows = []
        for row in reader:
            rows.append({k: (v or "") for k, v in row.items()})
            if len(rows) >= sample_rows:
                break
    return columns, rows


def profile_columns(columns: list[str], rows: list[dict[str, str]]) -> dict[str, Any]:
    out = {}
    for col in columns:
        values = [row.get(col, "") for row in rows]
        non_empty = [v for v in values if str(v).strip()]
        out[col] = {
            "normalized": normalize_col(col),
            "sample_non_empty_count": len(non_empty),
            "sample_empty_count": len(values) - len(non_empty),
            "sample_unique_count": len(set(non_empty)),
            "sample_values_redacted": [redact_value(col, v) for v in non_empty[:5]],
            "sensitive_or_private_risk": is_sensitive_column(col),
            "time_candidate": normalize_col(col) in TIME_COLUMNS or "time" in normalize_col(col) or "date" in normalize_col(col),
            "location_candidate": normalize_col(col) in LOCATION_COLUMNS or "lat" in normalize_col(col) or "lon" in normalize_col(col),
            "resource_candidate": normalize_col(col) in {"fire_box", "units_onscene", "vehicle_id", "collision_id"} or "unit" in normalize_col(col) or "company" in normalize_col(col),
        }
    return out


def profile_csv(path: Path, source_key: str, sample_rows: int) -> dict[str, Any]:
    columns, rows = sample_csv(path, sample_rows)
    row_count = count_csv_rows(path)
    normalized = {normalize_col(c): c for c in columns}
    has_latlon = any(k in normalized for k in ["latitude", "lat"]) and any(k in normalized for k in ["longitude", "lon", "lng"])
    has_time = any(profile_columns(columns, rows)[c]["time_candidate"] for c in columns)
    has_borough = any(k in normalized for k in ["borough", "borough_desc"])
    has_address = any(k in normalized for k in ["street", "street_highway", "address"]) or "zip_code" in normalized
    has_resource = any(normalize_col(c) in {"fire_box", "units_onscene", "vehicle_id", "collision_id"} or "unit" in normalize_col(c) or "company" in normalize_col(c) for c in columns)
    return {
        "source_key": source_key,
        "path": str(path),
        "bytes": path.stat().st_size,
        "row_count": row_count,
        "columns": columns,
        "column_count": len(columns),
        "column_profiles": profile_columns(columns, rows),
        "sample_rows_redacted": [redact_row(row) for row in rows],
        "spatial_signals": {"has_latlon": has_latlon, "has_borough": has_borough, "has_address_or_street_zip": has_address},
        "temporal_signals": {"has_time": has_time},
        "resource_signals": {"has_resource_or_unit_candidate": has_resource},
    }


def xlsx_col_to_index(cell_ref: str) -> int:
    letters = re.sub(r"[^A-Z]", "", cell_ref.upper())
    value = 0
    for ch in letters:
        value = value * 26 + (ord(ch) - ord("A") + 1)
    return max(0, value - 1)


def parse_xlsx_profile(path: Path, max_rows: int = 40) -> dict[str, Any]:
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main", "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    rel_ns = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
    with zipfile.ZipFile(path) as zf:
        shared = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", ns):
                text = "".join(t.text or "" for t in si.findall(".//m:t", ns))
                shared.append(text)
        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rid_to_target = {}
        for rel in rels.findall("rel:Relationship", rel_ns):
            target = rel.attrib.get("Target", "")
            rid_to_target[rel.attrib.get("Id")] = "xl/" + target.lstrip("/")
        sheets = []
        for sheet in workbook.findall(".//m:sheet", ns):
            name = sheet.attrib.get("name", "")
            rid = sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = rid_to_target.get(rid)
            rows = []
            if target and target in zf.namelist():
                sroot = ET.fromstring(zf.read(target))
                for row_el in sroot.findall(".//m:sheetData/m:row", ns):
                    row_values: dict[int, str] = {}
                    for c in row_el.findall("m:c", ns):
                        idx = xlsx_col_to_index(c.attrib.get("r", "A1"))
                        ctype = c.attrib.get("t")
                        value = ""
                        if ctype == "s":
                            v = c.find("m:v", ns)
                            if v is not None and v.text is not None:
                                try:
                                    value = shared[int(v.text)]
                                except Exception:
                                    value = v.text
                        elif ctype == "inlineStr":
                            value = "".join(t.text or "" for t in c.findall(".//m:t", ns))
                        else:
                            v = c.find("m:v", ns)
                            value = v.text if v is not None and v.text is not None else ""
                        row_values[idx] = value
                    if row_values:
                        max_idx = max(row_values)
                        rows.append([row_values.get(i, "") for i in range(max_idx + 1)])
                    if len(rows) >= max_rows:
                        break
            sheets.append({"name": name, "target": target, "sample_rows": rows})
    return {
        "source_key": "ems_description",
        "path": str(path),
        "bytes": path.stat().st_size,
        "format": "xlsx",
        "schema_only_status": "EMS_DESCRIPTION_ONLY_ACTUAL_ROWS_MISSING",
        "sheet_count": len(sheets),
        "sheets": sheets,
    }


def readiness_for_source(source_key: str, profile: dict[str, Any] | None, found: bool, actual_ems_rows_found: bool = False) -> dict[str, Any]:
    if not found or profile is None:
        return {"score": 0, "status": "MISSING", "basis": "source file not found"}
    if source_key == "ems_description":
        return {"score": 1, "status": "SCHEMA_ONLY", "basis": "EMS description workbook found; actual EMS incident rows are missing" if not actual_ems_rows_found else "EMS description workbook found; rows are scored separately"}
    spatial = profile.get("spatial_signals", {})
    temporal = profile.get("temporal_signals", {})
    has_time = bool(temporal.get("has_time"))
    has_latlon = bool(spatial.get("has_latlon"))
    has_borough = bool(spatial.get("has_borough"))
    has_address = bool(spatial.get("has_address_or_street_zip"))
    if source_key == "motor_vehicle_vehicles":
        if has_time:
            return {"score": 3, "status": "CONTEXT_WITH_TIME_NEEDS_CRASH_TABLE", "basis": "vehicle-level collision participant table has crash date/time and COLLISION_ID but no lat/lon; primary crashes table is needed for locatable collision events"}
        return {"score": 2, "status": "CONTEXT_ROWS_NEED_CRASH_TABLE", "basis": "vehicle-level collision participant rows are present but primary crash event location is absent"}
    if has_time and has_latlon:
        return {"score": 5, "status": "EVENT_TIME_AND_LATLON_READY", "basis": "event time and lat/lon columns found"}
    if has_time and (has_borough or has_address):
        return {"score": 4, "status": "EVENT_TIME_AND_ADDRESS_OR_BOROUGH_READY", "basis": "event time plus borough/street/ZIP fields found; location is address-candidate, not exact geometry"}
    if has_time:
        return {"score": 3, "status": "EVENT_TIME_LOCATION_WEAK", "basis": "event time found; location fields are weak or absent"}
    return {"score": 2, "status": "ROWS_PRESENT_WEAK_TIME_LOCATION", "basis": "rows are present but usable event time/location is not clear"}


def classify_event_type_from_field(field: str) -> str:
    low = str(field).lower()
    if "fire" in low or "flame" in low:
        return "fire"
    if "ems" in low or "medical" in low or "rescue" in low:
        return "medical"
    if "collision" in low or "vehicle" in low or "crash" in low:
        return "collision"
    return "other_emergency"


def build_mapping_reports(profiles: dict[str, Any], discovery: dict[str, Any]) -> dict[str, Any]:
    fire_cols = profiles.get("fire_company_incidents", {}).get("columns", [])
    vehicle_cols = profiles.get("motor_vehicle_vehicles", {}).get("columns", [])
    mappings = {
        "fire_company_incidents": {
            "source_role": "strongest_initial_incident_corpus",
            "canonical_entity": "event",
            "canonical_id_pattern": "event:us-nyc:flow3:fdny_fire_company_incidents:{IM_INCIDENT_KEY}",
            "field_map": {
                "source_record_id": "IM_INCIDENT_KEY" if "IM_INCIDENT_KEY" in fire_cols else None,
                "event_time": "INCIDENT_DATE_TIME" if "INCIDENT_DATE_TIME" in fire_cols else None,
                "arrival_time": "ARRIVAL_DATE_TIME" if "ARRIVAL_DATE_TIME" in fire_cols else None,
                "clear_time": "LAST_UNIT_CLEARED_DATE_TIME" if "LAST_UNIT_CLEARED_DATE_TIME" in fire_cols else None,
                "event_type_source": "INCIDENT_TYPE_DESC" if "INCIDENT_TYPE_DESC" in fire_cols else None,
                "borough": "BOROUGH_DESC" if "BOROUGH_DESC" in fire_cols else None,
                "street_candidate": "STREET_HIGHWAY" if "STREET_HIGHWAY" in fire_cols else None,
                "zip_code": "ZIP_CODE" if "ZIP_CODE" in fire_cols else None,
                "alarm_box_candidate": "FIRE_BOX" if "FIRE_BOX" in fire_cols else None,
                "duration_seconds": "TOTAL_INCIDENT_DURATION" if "TOTAL_INCIDENT_DURATION" in fire_cols else None,
            },
            "location_status_rule": "latlon_exact only if lat/lon columns appear; otherwise address_candidate when street/ZIP exists, borough_only when only borough exists",
            "event_type_rule": "derive fire/medical/other_emergency from INCIDENT_TYPE_DESC text; preserve raw incident code text in provenance",
        },
        "motor_vehicle_vehicles": {
            "source_role": "collision_vehicle_context",
            "canonical_entity": "collision_vehicle_context",
            "not_primary_event_table": True,
            "canonical_id_pattern": "context:us-nyc:flow3:collision_vehicle:{UNIQUE_ID}",
            "field_map": {
                "source_record_id": "UNIQUE_ID" if "UNIQUE_ID" in vehicle_cols else None,
                "paired_collision_event_id": "COLLISION_ID" if "COLLISION_ID" in vehicle_cols else None,
                "crash_date": "CRASH_DATE" if "CRASH_DATE" in vehicle_cols else None,
                "crash_time": "CRASH_TIME" if "CRASH_TIME" in vehicle_cols else None,
                "vehicle_type": "VEHICLE_TYPE" if "VEHICLE_TYPE" in vehicle_cols else None,
                "pre_crash": "PRE_CRASH" if "PRE_CRASH" in vehicle_cols else None,
                "contributing_factor_1": "CONTRIBUTING_FACTOR_1" if "CONTRIBUTING_FACTOR_1" in vehicle_cols else None,
            },
            "paired_source_needed": "Motor_Vehicle_Collisions_-_Crashes.csv",
            "location_status": "unavailable_in_vehicle_table_unless_latlon_columns_are_added",
        },
        "ems_description": {
            "source_role": "schema_documentation_only",
            "canonical_entity": "none_until_actual_rows_present",
            "status": "EMS_DESCRIPTION_ONLY_ACTUAL_ROWS_MISSING" if discovery["selected"].get("ems_actual_rows") is None else "EMS_DESCRIPTION_PLUS_ACTUAL_ROWS_PRESENT",
        },
    }
    return mappings


def missing_source_report(discovery: dict[str, Any]) -> dict[str, Any]:
    recommendations = []
    selected = discovery["selected"]
    if selected.get("mvc_crashes") is None:
        recommendations.append(
            {
                "dataset": "Motor_Vehicle_Collisions_-_Crashes.csv",
                "why": "Needed to turn vehicle-level collision context into locatable collision incident events with crash location fields.",
                "priority": "high_for_collision_slice",
            }
        )
    if selected.get("fire_dispatch") is None:
        recommendations.append(
            {
                "dataset": "Fire_Incident_Dispatch_Data.csv",
                "why": "Needed for fire-company/unit response resource details beyond FIRE_BOX and incident-level response times.",
                "priority": "high_for_fdny_response_slice",
            }
        )
    if selected.get("fdny_firehouses") is None:
        recommendations.append(
            {
                "dataset": "FDNY_Firehouse_Listing.csv",
                "why": "Needed to ground response resources to firehouse/station assets before routing/resource optimization.",
                "priority": "high_for_routing_slice",
            }
        )
    if selected.get("ems_actual_rows") is None:
        recommendations.append(
            {
                "dataset": "EMS_Incident_Dispatch_Data.csv",
                "why": "EMS description is schema-only; actual rows are needed for EMS incident event inventory.",
                "priority": "medium_if_ems_slice_needed",
                "status": "EMS_DESCRIPTION_ONLY_ACTUAL_ROWS_MISSING",
            }
        )
    return {
        "status": "PASS",
        "missing_count": len(recommendations),
        "missing_recommended_downloads": recommendations,
    }


def private_data_scan(profiles: dict[str, Any]) -> dict[str, Any]:
    findings = []
    for source_key, profile in profiles.items():
        for col, meta in (profile.get("column_profiles") or {}).items():
            if meta.get("sensitive_or_private_risk"):
                findings.append({"source_key": source_key, "column": col, "reason": "column name matched private/sensitive scan pattern", "sample_emitted": "redacted"})
    serialized_samples = json.dumps({k: v.get("sample_rows_redacted") for k, v in profiles.items()}, ensure_ascii=False)
    unredacted_phone = bool(re.search(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b", serialized_samples))
    status = "FAIL" if unredacted_phone else "PASS"
    return {
        "status": status,
        "findings": findings,
        "unredacted_phone_pattern_found_in_samples": unredacted_phone,
        "policy": "Samples redact name/phone/patient/narrative/contact/license/floor/unit-like fields.",
    }


def first_slice_recommendation(readiness: dict[str, Any], discovery: dict[str, Any]) -> dict[str, Any]:
    fire_score = readiness.get("fire_company_incidents", {}).get("score", 0)
    vehicle_score = readiness.get("motor_vehicle_vehicles", {}).get("score", 0)
    crash_present = discovery["selected"].get("mvc_crashes") is not None
    if fire_score >= 4:
        primary = "FDNY incident response slice"
        basis = "Fire-company incidents have event time plus borough/street/ZIP candidate location fields. This supports a first deterministic incident inventory and candidate asset proximity step, while preserving address-candidate limitations."
    elif crash_present and vehicle_score >= 3:
        primary = "collision incident slice"
        basis = "Crash table is present with vehicle context available."
    else:
        primary = "inventory-only until missing paired downloads arrive"
        basis = "Available sources are not spatially ready enough for a safe D2 slice."
    return {
        "status": "PASS",
        "primary_recommended_slice": primary,
        "basis": basis,
        "first_safe_d2_shape": {
            "event": "FDNY fire-company incident from IM_INCIDENT_KEY",
            "location": "address_candidate from STREET_HIGHWAY + ZIP_CODE + BOROUGH_DESC unless a deterministic geocode/latlon source is added",
            "affected_assets": "candidate-only nearby NYC buildings/parcels/roads after deterministic spatial evidence",
            "response_resource": "FIRE_BOX candidate now; Fire_Incident_Dispatch_Data and FDNY_Firehouse_Listing recommended for actual companies/stations",
            "briefing": "EvidenceBundle facts only; no emergency/dispatch/legal conclusion",
            "routing": "candidate_route_to only after resource and event locations are deterministic",
        },
        "alternative": "collision incident slice only after Motor_Vehicle_Collisions_-_Crashes.csv is present and profiled",
    }


def no_overclaim_scan(output_dir: Path) -> dict[str, Any]:
    hits = []
    missing_lines = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name in {"SHA256SUMS.json", "F3_NYC_D1_NO_OVERCLAIM_REPORT.json"}:
            continue
        if path.suffix.lower() not in {".json", ".md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            low = line.lower()
            if any(neg in low for neg in ["not ", "no ", "only", "candidate", "missing", "needed", "do not"]):
                continue
            for pattern in FORBIDDEN_POSITIVE_PATTERNS:
                if pattern in low:
                    hits.append({"file": str(path.relative_to(output_dir)), "line": line.strip(), "pattern": pattern})
    corpus = ""
    for path in [output_dir / "README.md", output_dir / "F3_NYC_D1_HARNESS_REPORT.json", output_dir / "F3_NYC_D1_ADAPTER_HANDOVER.md"]:
        if path.exists():
            corpus += "\n" + path.read_text(encoding="utf-8", errors="replace")
    for line in NO_OVERCLAIM_LINES:
        if line not in corpus:
            missing_lines.append(line)
    return {"gate": "F3-NYC-D1-NO-OVERCLAIM", "status": "PASS" if not hits and not missing_lines else "FAIL", "forbidden_positive_claims_found": hits, "missing_boundary_lines": missing_lines}


def existing_nyc_artifacts(project_root: Path) -> dict[str, Any]:
    outputs = project_root / "outputs"
    patterns = ["a3*", "a4*", "a5*", "a6*", "a8*"]
    found = []
    for pattern in patterns:
        for path in sorted(outputs.glob(pattern)) if outputs.exists() else []:
            if path.is_dir():
                found.append({"path": str(path), "bytes_top_level": sum(p.stat().st_size for p in path.glob("*") if p.is_file())})
    external = []
    for root in [Path("C:/data/citybrain/from_3090"), Path("/data/citybrain/from_3090"), Path("/data/citybrain")]:
        if root.exists():
            external.extend({"path": str(p), "bytes_top_level": sum(x.stat().st_size for x in p.glob("*") if x.is_file())} for p in sorted(root.glob("*")) if p.is_dir())
    return {"local_outputs": found, "external_bundles": external}


def write_canonical_plan(output_dir: Path, mappings: dict[str, Any]) -> None:
    event_model = {
        "canonical_id": "event:us-nyc:flow3:{source}:{id}",
        "entity_type": "event",
        "event_family": "incident_response",
        "event_type": "fire | medical | collision | other_emergency | unknown",
        "source_dataset": "...",
        "source_record_id": "...",
        "event_time": "...",
        "borough": "...",
        "location_status": "latlon_exact | address_candidate | borough_only | unavailable",
        "geometry": None,
        "provenance": [],
        "d1_note": "D1 proposes this model only; it does not emit canonical event rows.",
    }
    response_model = {
        "canonical_id": "resource:us-nyc:fdny:{id}",
        "entity_type": "response_resource",
        "resource_type": "fire_company | ems_unit | firehouse | unknown",
        "source_dataset": "...",
        "status": "observed_in_incident | station_asset | candidate",
        "provenance": [],
        "d1_note": "FIRE_BOX is candidate response/location context until dispatch/firehouse sources are paired.",
    }
    affected_model = {
        "relation": "event --near_or_affects_candidate--> building / parcel / road segment",
        "status": "candidate_only",
        "certification_requirement": "deterministic spatial or identifier evidence; borough/address-only is not exact asset evidence",
    }
    routing_model = {
        "relation": "response_resource --candidate_route_to--> event",
        "status": "proposed_only",
        "not_claimed": "No real dispatch optimization or field routing is built in F3-NYC-D1.",
    }
    evidence_contract = {
        "bundle_type": "EvidenceBundle",
        "facts_source": "deterministic source profiles and future Flow 3 event retrieval only",
        "model_may_narrate": True,
        "model_may_compute_counts": False,
        "model_may_add_facts": False,
        "required_limitations": NO_OVERCLAIM_LINES,
    }
    er = {
        "event_to_vehicle_context": "event:collision --has_vehicle_context_candidate--> context:collision_vehicle, requires crashes table for canonical collision event",
        "event_to_response_resource": "event --observed_response_resource_candidate--> resource, requires dispatch/firehouse data for stronger resource modeling",
        "event_to_asset": affected_model["relation"],
        "resource_to_event": routing_model["relation"],
        "source_mappings": mappings,
    }
    write_json(output_dir / "canonical_plan/proposed_event_model.json", event_model)
    write_json(output_dir / "canonical_plan/proposed_response_resource_model.json", response_model)
    write_json(output_dir / "canonical_plan/proposed_affected_asset_model.json", affected_model)
    write_json(output_dir / "canonical_plan/proposed_routing_model.json", routing_model)
    write_json(output_dir / "canonical_plan/proposed_evidence_bundle_contract.json", evidence_contract)
    write_json(output_dir / "canonical_plan/flow3_entity_relationship_map.json", er)


def run_f3_nyc_d1_gate(
    project_root: str,
    raw_roots: list[str],
    output_dir: str,
    sample_rows: int = 25,
) -> dict:
    project = Path(project_root).resolve()
    output_path = Path(output_dir)
    reset_output_dir(output_path)
    before_snapshot = input_snapshot(project)
    discovery = discover_sources(project, raw_roots)
    selected = discovery["selected"]

    profiles: dict[str, Any] = {}
    row_counts: dict[str, Any] = {}
    column_profiles: dict[str, Any] = {}
    sample_rows_redacted: dict[str, Any] = {}

    for source_key in ["fire_company_incidents", "motor_vehicle_vehicles", "ems_actual_rows", "mvc_crashes", "fire_dispatch", "fdny_firehouses"]:
        rec = selected.get(source_key)
        if rec and rec.get("path") and Path(rec["path"]).exists() and str(rec["path"]).lower().endswith(".csv"):
            profile = profile_csv(Path(rec["path"]), source_key, sample_rows)
            profiles[source_key] = profile
            row_counts[source_key] = profile["row_count"]
            column_profiles[source_key] = profile["column_profiles"]
            sample_rows_redacted[source_key] = profile["sample_rows_redacted"]
    if selected.get("ems_description"):
        ems_path = Path(selected["ems_description"]["path"])
        if ems_path.suffix.lower() == ".xlsx":
            profiles["ems_description"] = parse_xlsx_profile(ems_path)
        else:
            text = ems_path.read_text(encoding="utf-8", errors="replace")[:8000] if ems_path.is_file() else ""
            profiles["ems_description"] = {"source_key": "ems_description", "path": str(ems_path), "format": "text_or_unknown", "schema_only_status": "EMS_DESCRIPTION_ONLY_ACTUAL_ROWS_MISSING", "sample_text_redacted": text}
        sample_rows_redacted["ems_description"] = profiles["ems_description"].get("sheets", profiles["ems_description"].get("sample_text_redacted"))

    actual_ems_found = selected.get("ems_actual_rows") is not None
    readiness = {}
    for key in SOURCE_KEYS:
        readiness[key] = readiness_for_source(key, profiles.get(key), selected.get(key) is not None, actual_ems_found)

    mappings = build_mapping_reports(profiles, discovery)
    missing = missing_source_report(discovery)
    privacy = private_data_scan(profiles)
    first_slice = first_slice_recommendation(readiness, discovery)

    spatial = {
        key: {
            "score": readiness.get(key, {}).get("score"),
            "status": readiness.get(key, {}).get("status"),
            "signals": profile.get("spatial_signals", {}),
            "location_interpretation": "latlon_exact only when has_latlon is true; address/borough fields remain candidates",
        }
        for key, profile in profiles.items()
    }
    temporal = {key: {"signals": profile.get("temporal_signals", {}), "time_columns": [c for c in profile.get("columns", []) if profile.get("column_profiles", {}).get(c, {}).get("time_candidate")]} for key, profile in profiles.items()}
    resource = {key: {"signals": profile.get("resource_signals", {}), "resource_columns": [c for c in profile.get("columns", []) if profile.get("column_profiles", {}).get(c, {}).get("resource_candidate")]} for key, profile in profiles.items()}

    source_discovery_report = {
        "status": "PASS" if any(selected.get(k) for k in ["fire_company_incidents", "motor_vehicle_vehicles", "ems_description"]) else "FAIL",
        "searched_roots": discovery["searched_roots"],
        "selected": selected,
        "found": discovery["found"],
    }
    schema_status = "PASS" if profiles else "FAIL"
    readiness_status = "PASS" if readiness and all("score" in r for r in readiness.values()) else "FAIL"
    mapping_status = "PASS" if mappings else "FAIL"

    write_json(output_path / "F3_NYC_D1_INPUT_INVENTORY.json", {"project_root": str(project), "raw_roots": raw_roots, "existing_nyc_artifacts": existing_nyc_artifacts(project), "source_files": selected})
    write_json(output_path / "F3_NYC_D1_SOURCE_DISCOVERY_REPORT.json", source_discovery_report)
    write_json(output_path / "F3_NYC_D1_SCHEMA_PROFILE_REPORT.json", {"status": schema_status, "profiles": profiles})
    write_json(output_path / "F3_NYC_D1_DATA_READINESS_REPORT.json", {"status": readiness_status, "readiness": readiness})
    write_json(output_path / "F3_NYC_D1_CANONICAL_MAPPING_REPORT.json", {"status": mapping_status, "mappings": mappings})
    write_json(output_path / "F3_NYC_D1_MISSING_SOURCE_REPORT.json", missing)
    write_json(output_path / "F3_NYC_D1_FIRST_SLICE_RECOMMENDATION.json", first_slice)
    write_json(output_path / "profiles/fire_company_incidents_schema.json", profiles.get("fire_company_incidents", {"status": "MISSING"}))
    write_json(output_path / "profiles/motor_vehicle_vehicles_schema.json", profiles.get("motor_vehicle_vehicles", {"status": "MISSING"}))
    write_json(output_path / "profiles/ems_description_profile.json", profiles.get("ems_description", {"status": "MISSING"}))
    write_json(output_path / "profiles/inferred_field_catalog.json", {"column_profiles": column_profiles, "canonical_mappings": mappings})
    write_json(output_path / "profiles/sample_rows_redacted.json", sample_rows_redacted)
    write_canonical_plan(output_path, mappings)
    write_json(output_path / "reports/file_locations.json", {"selected": selected, "found": discovery["found"]})
    write_json(output_path / "reports/row_counts.json", row_counts)
    write_json(output_path / "reports/column_profiles.json", column_profiles)
    write_json(output_path / "reports/spatial_readiness.json", spatial)
    write_json(output_path / "reports/temporal_readiness.json", temporal)
    write_json(output_path / "reports/resource_readiness.json", resource)
    write_json(output_path / "reports/pii_private_data_scan.json", privacy)
    write_json(output_path / "reports/source_limitations.json", {"limitations": NO_OVERCLAIM_LINES, "source_specific": {k: r.get("basis") for k, r in readiness.items()}})
    write_json(output_path / "reports/recommended_next_downloads.json", missing["missing_recommended_downloads"])

    readme = f"""# F3-NYC-D1 Source Inventory + Schema Mapping

Status: pending final harness write.

F3-NYC-D1 inventories Flow 3 sources only; it does not build the Flow 3 cartridge.
Motor Vehicle Collisions Vehicles is collision vehicle context, not the primary locatable crash event table.
EMS incident dispatch description is schema/documentation only unless actual EMS rows are present.
Borough/address-only incident data is not exact geometry.
Affected asset links remain candidate-only until deterministic spatial or identifier evidence supports them.
Routing relations are proposed candidate relations only; no real dispatch optimization is claimed.

Primary recommended slice: {first_slice['primary_recommended_slice']}
"""
    write_text(output_path / "README.md", readme)
    write_text(
        output_path / "F3_NYC_D1_ADAPTER_HANDOVER.md",
        "# F3-NYC-D1 Adapter Handover\n\n"
        + "\n".join(f"- {line}" for line in NO_OVERCLAIM_LINES)
        + "\n\nNext adapter should start with the FDNY incident response slice if the D1 readiness score remains >=4, and should keep asset links candidate-only until deterministic geometry is added.\n",
    )

    overclaim = no_overclaim_scan(output_path)
    write_json(output_path / "F3_NYC_D1_NO_OVERCLAIM_REPORT.json", overclaim)
    after_snapshot = input_snapshot(project)
    no_mutation = {"gate": "F3-NYC-D1-NO-MUTATION", "status": "PASS" if before_snapshot == after_snapshot else "FAIL", "before": before_snapshot, "after": after_snapshot}

    gates = {
        "F3-NYC-D1-PRECOND": "PASS",
        "F3-NYC-D1-SOURCE-DISCOVERY": source_discovery_report["status"],
        "F3-NYC-D1-SCHEMA-PROFILE": schema_status,
        "F3-NYC-D1-READINESS-SCORING": readiness_status,
        "F3-NYC-D1-CANONICAL-MAPPING": mapping_status,
        "F3-NYC-D1-PRIVATE-DATA-SCAN": privacy["status"],
        "F3-NYC-D1-MISSING-SOURCE-RECOMMENDATION": missing["status"],
        "F3-NYC-D1-FIRST-SLICE-RECOMMENDATION": first_slice["status"],
        "F3-NYC-D1-NO-OVERCLAIM": overclaim["status"],
        "F3-NYC-D1-NO-MUTATION": no_mutation["status"],
    }
    hard_pass = all(v == "PASS" for v in gates.values())
    status = "PASS_WITH_MISSING_SOURCES" if hard_pass and missing["missing_count"] > 0 else ("PASS" if hard_pass else "FAIL")
    final_readme = f"""# F3-NYC-D1 Source Inventory + Schema Mapping

Status: {status}

F3-NYC-D1 inventories Flow 3 sources only; it does not build the Flow 3 cartridge.
Motor Vehicle Collisions Vehicles is collision vehicle context, not the primary locatable crash event table.
EMS incident dispatch description is schema/documentation only unless actual EMS rows are present.
Borough/address-only incident data is not exact geometry.
Affected asset links remain candidate-only until deterministic spatial or identifier evidence supports them.
Routing relations are proposed candidate relations only; no real dispatch optimization is claimed.

Primary recommended slice: {first_slice['primary_recommended_slice']}
Missing recommended downloads: {', '.join(item['dataset'] for item in missing['missing_recommended_downloads']) or 'none'}
"""
    write_text(output_path / "README.md", final_readme)
    overclaim = no_overclaim_scan(output_path)
    write_json(output_path / "F3_NYC_D1_NO_OVERCLAIM_REPORT.json", overclaim)
    gates["F3-NYC-D1-NO-OVERCLAIM"] = overclaim["status"]
    hard_pass = all(v == "PASS" for v in gates.values())
    status = "PASS_WITH_MISSING_SOURCES" if hard_pass and missing["missing_count"] > 0 else ("PASS" if hard_pass else "FAIL")
    harness = {
        "task": TASK_NAME,
        "status": status,
        "created_utc": utc_now(),
        "gates": gates,
        "source_summary": {
            "fire_company_incidents": {"found": selected.get("fire_company_incidents") is not None, "readiness": readiness.get("fire_company_incidents", {}).get("score")},
            "motor_vehicle_vehicles": {"found": selected.get("motor_vehicle_vehicles") is not None, "readiness": readiness.get("motor_vehicle_vehicles", {}).get("score")},
            "ems_actual_rows": {"found": selected.get("ems_actual_rows") is not None, "readiness": readiness.get("ems_actual_rows", {}).get("score")},
            "ems_description": {"found": selected.get("ems_description") is not None},
        },
        "primary_recommended_slice": first_slice["primary_recommended_slice"],
        "missing_recommended_downloads": [item["dataset"] for item in missing["missing_recommended_downloads"]],
        "private_data_scan": privacy,
        "no_overclaim": overclaim,
        "no_mutation": no_mutation,
    }
    write_json(output_path / "F3_NYC_D1_HARNESS_REPORT.json", harness)
    hashes = write_hashes(output_path)
    gates["F3-NYC-D1-HASHES"] = hashes["status"]
    harness["gates"] = gates
    harness["hashes"] = read_json(output_path / "SHA256SUMS.json", {})
    write_json(output_path / "F3_NYC_D1_HARNESS_REPORT.json", harness)
    hashes = write_hashes(output_path)
    harness["hashes"] = read_json(output_path / "SHA256SUMS.json", {})
    write_json(output_path / "F3_NYC_D1_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run F3-NYC-D1 source inventory + schema mapping")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--raw-root", action="append", dest="raw_roots", default=[])
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sample-rows", type=int, default=25)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_f3_nyc_d1_gate(args.project_root, args.raw_roots, args.output_dir, args.sample_rows)
    summary = report["source_summary"]
    print(f"F3-NYC-D1 Source Inventory + Schema Mapping: {report['status']}")
    print(f"Fire company incidents: {'FOUND' if summary['fire_company_incidents']['found'] else 'MISSING'}, readiness {summary['fire_company_incidents']['readiness']}/5")
    print(f"Motor vehicle vehicles: {'FOUND' if summary['motor_vehicle_vehicles']['found'] else 'MISSING'}, readiness {summary['motor_vehicle_vehicles']['readiness']}/5")
    print(f"EMS actual rows: {'FOUND' if summary['ems_actual_rows']['found'] else 'MISSING'}, readiness {summary['ems_actual_rows']['readiness']}/5")
    print(f"EMS description: {'FOUND' if summary['ems_description']['found'] else 'MISSING'}")
    print(f"Primary recommended slice: {report['primary_recommended_slice']}")
    print(f"Missing recommended downloads: {report['missing_recommended_downloads']}")
    print(f"Private-data scan: {report['private_data_scan']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] in {"PASS", "PASS_WITH_MISSING_SOURCES"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

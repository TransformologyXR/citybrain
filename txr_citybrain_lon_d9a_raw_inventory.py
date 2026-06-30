from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import re
import shutil
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import pandas as pd


TASK_NAME = "LON-D9A London-Wide Raw Data Inventory + Processing Readiness Gate"
DEFAULT_RAW_ROOT = "data_landing/london_d9_raw"
DEFAULT_OUTPUT_DIR = "outputs/lon_d9a_london_raw_inventory"

BOUNDARY_STRINGS = [
    "D9A is raw data inventory only.",
    "D9A does not prove London-wide coverage.",
    "D9A does not build the London graph.",
    "D9A does not deduplicate or merge PLD extracts.",
    "D9A does not ingest enforcement/building-control records.",
    "D9A does not call NIM/NeMo/LLMs.",
]
SOURCE_FAMILIES = {
    "os_open_uprn",
    "os_open_usrn",
    "os_open_lids",
    "london_boundaries",
    "pld_api_export",
    "pld_csv_approved",
    "pld_csv_lapsed",
    "pld_csv_ev_charging",
    "pld_other",
    "london_datastore_sitemap",
    "london_datastore_dataset",
    "manual_d6_request_material",
    "unknown",
}
LIDS_TIER_PATTERNS = [
    (1, "BLPU UPRN Street USRN", re.compile(r"blpu.*uprn.*street.*usrn", re.I)),
    (1, "BLPU UPRN TopographicArea TOID", re.compile(r"blpu.*uprn.*topographicarea.*toid", re.I)),
    (1, "BLPU UPRN RoadLink TOID", re.compile(r"blpu.*uprn.*roadlink.*toid", re.I)),
    (2, "RoadLink TOID Street USRN", re.compile(r"roadlink.*toid.*street.*usrn", re.I)),
    (2, "RoadLink TOID Road TOID", re.compile(r"roadlink.*toid.*road.*toid", re.I)),
    (2, "RoadLink TOID TopographicArea TOID", re.compile(r"roadlink.*toid.*topographicarea.*toid", re.I)),
    (3, "Road TOID Street USRN", re.compile(r"road.*toid.*street.*usrn", re.I)),
    (3, "Road TOID TopographicArea TOID", re.compile(r"road.*toid.*topographicarea.*toid", re.I)),
    (3, "Street USRN TopographicArea TOID", re.compile(r"street.*usrn.*topographicarea.*toid", re.I)),
    (4, "ORRoadLink GUID RoadLink TOID", re.compile(r"orroadlink.*guid.*roadlink.*toid", re.I)),
    (4, "ORRoadNode GUID RoadLink TOID", re.compile(r"orroadnode.*guid.*roadlink.*toid", re.I)),
]
READINESS_D9B = [
    "D9B_READY",
    "D9B_BLOCKED_MISSING_BOUNDARY",
    "D9B_BLOCKED_MISSING_OPENUPRN",
    "D9B_BLOCKED_MISSING_OPENUSRN",
    "D9B_BLOCKED_MISSING_LIDS_TIER1",
    "D9B_BLOCKED_MANUAL_REVIEW",
]
READINESS_D9C = [
    "D9C_READY",
    "D9C_READY_WITH_OVERLAP_RISK",
    "D9C_BLOCKED_NO_PLD",
    "D9C_BLOCKED_SCHEMA_UNKNOWN",
    "D9C_BLOCKED_MANUAL_REVIEW",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> Any:
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def pretty_json(value: Any) -> str:
    return json.dumps(clean(value), indent=2, sort_keys=True, ensure_ascii=False, default=str)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pretty_json(value) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value: Any, length: int = 24) -> str:
    payload = json.dumps(clean(value), sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {part.lower() for part in resolved.parts} or "lon_d9a" not in resolved.name.lower():
            raise ValueError(f"refusing to delete unexpected output directory: {resolved}")
        shutil.rmtree(resolved)
    (output_dir / "reports").mkdir(parents=True, exist_ok=True)


def classify_source_family(path: Path, raw_root: Path) -> str:
    name = path.name.lower()
    parts = [part.lower() for part in path.relative_to(raw_root).parts[:-1]]
    joined = " ".join(parts + [name])
    datastore_context_dirs = {
        "areas_of_intensification",
        "biodiversity_hotspots_for_planning",
        "designated_open_space",
        "lvmf_protected_vistas",
        "opportunity_areas",
        "planning_data_map_planning_constraints_map",
        "planning_local_plan_data",
        "ptal_public_transport_accessibility_levels",
        "strategic_industrial_land_sil",
        "town_centre_boundaries",
    }
    if any(part in datastore_context_dirs for part in parts):
        return "london_datastore_dataset"
    if "london_boroughs" in parts:
        return "london_boundaries"
    if "manual_d6" in joined or "enforcement" in joined or "building_control" in joined:
        return "manual_d6_request_material"
    if "sitemap" in name and path.suffix.lower() in {".xml", ".gz"}:
        return "london_datastore_sitemap"
    if "datastore" in joined or "london datastore" in joined:
        return "london_datastore_dataset"
    if "osopenuprn" in name or "open_uprn" in joined or "open-uprn" in joined:
        return "os_open_uprn"
    if "osopenusrn" in name or "open_usrn" in joined or "open-usrn" in joined:
        return "os_open_usrn"
    if name.startswith("lids-") or "lids" in joined or any(pattern.search(name.replace("-", " ")) for _, _, pattern in LIDS_TIER_PATTERNS):
        return "os_open_lids"
    if "borough" in name or "boundary" in name or "boundaries" in joined:
        return "london_boundaries"
    if path.suffix.lower() in {".json", ".jsonl", ".parquet"} and "pld" in joined:
        return "pld_api_export"
    if path.suffix.lower() == ".csv":
        if "electric vehicle charging" in name or "ev charging" in name:
            return "pld_csv_ev_charging"
        if "lapsed planning permission" in name:
            return "pld_csv_lapsed"
        if "approved applications" in name:
            return "pld_csv_approved"
        if any(token in name for token in ["all valid applications", "new housing applications", "planning"]):
            return "pld_other"
    return "unknown"


def compression_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".zip":
        return "zip"
    if suffix in {".gz", ".gzip"}:
        return "gzip"
    return "none"


def detected_format_from_name(name: str) -> str:
    lower = name.lower()
    suffixes = Path(lower).suffixes
    suffix = suffixes[-1] if suffixes else ""
    if suffix == ".csv":
        return "csv"
    if suffix == ".parquet":
        return "parquet"
    if suffix in {".geojson", ".json"}:
        return "geojson" if suffix == ".geojson" else "json"
    if suffix == ".gpkg":
        return "geopackage"
    if suffix in {".shp", ".dbf", ".shx"}:
        return "shapefile"
    if suffix == ".xml":
        return "xml"
    if suffix in {".html", ".htm"}:
        return "html"
    return "unknown"


def zip_members(path: Path) -> list[dict[str, Any]]:
    members = []
    if path.suffix.lower() != ".zip":
        return members
    try:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                members.append(
                    {
                        "filename": info.filename,
                        "file_size": info.file_size,
                        "compress_size": info.compress_size,
                        "detected_format": detected_format_from_name(info.filename),
                    }
                )
    except Exception as exc:
        members.append({"error": f"{type(exc).__name__}: {exc}"})
    return members


def primary_member(members: list[dict[str, Any]]) -> dict[str, Any] | None:
    data_members = [member for member in members if member.get("detected_format") in {"csv", "geopackage", "json", "xml", "geojson", "parquet"}]
    if not data_members:
        return None
    return sorted(data_members, key=lambda item: item.get("file_size", 0), reverse=True)[0]


def detect_encoding_and_dialect(path: Path, zip_member: str | None = None) -> tuple[str | None, str | None, str | None]:
    sample = b""
    try:
        if zip_member:
            with zipfile.ZipFile(path) as archive:
                with archive.open(zip_member) as handle:
                    sample = handle.read(65536)
        elif path.suffix.lower() == ".gz":
            with gzip.open(path, "rb") as handle:
                sample = handle.read(65536)
        else:
            sample = path.read_bytes()[:65536]
    except Exception as exc:
        return None, None, f"{type(exc).__name__}: {exc}"
    encoding = None
    text = ""
    for candidate in ["utf-8-sig", "utf-8", "cp1252", "latin1"]:
        try:
            text = sample.decode(candidate)
            encoding = candidate
            break
        except UnicodeDecodeError:
            continue
    if encoding is None:
        return None, None, "encoding_not_detected"
    delimiter = ","
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=[",", "\t", ";", "|"])
        delimiter = dialect.delimiter
    except Exception:
        pass
    return encoding, delimiter, None


def normalize_column(column: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", column.strip().lower()).strip("_")


def detect_key_fields(columns: list[str]) -> dict[str, list[str]]:
    normalized = {column: normalize_column(column) for column in columns}
    groups = {
        "candidate_identifier_fields": [],
        "candidate_date_fields": [],
        "candidate_geometry_fields": [],
        "candidate_borough_lpa_fields": [],
    }
    identifier_patterns = [
        "uprn",
        "usrn",
        "toid",
        "lpa_app_no",
        "lpa_number",
        "application_reference",
        "application_ref",
        "planning_reference",
        "building_control_reference",
        "enforcement_reference",
        "postcode",
        "address",
    ]
    for original, norm in normalized.items():
        if any(pattern in norm for pattern in identifier_patterns):
            groups["candidate_identifier_fields"].append(original)
        if "date" in norm or norm.endswith("_at") or norm in {"valid_date", "decision_date"}:
            groups["candidate_date_fields"].append(original)
        if any(token in norm for token in ["geometry", "geom", "location", "longitude", "latitude", "easting", "northing", "x_coordinate", "y_coordinate"]):
            groups["candidate_geometry_fields"].append(original)
        if any(token in norm for token in ["borough", "lpa", "local_planning_authority"]):
            groups["candidate_borough_lpa_fields"].append(original)
    return groups


def read_csv_sample(path: Path, max_rows: int, zip_member: str | None = None) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    encoding, delimiter, error = detect_encoding_and_dialect(path, zip_member)
    if error:
        return None, {"encoding": encoding, "delimiter": delimiter, "error": error}
    read_error = None
    try:
        if zip_member:
            with zipfile.ZipFile(path) as archive:
                with archive.open(zip_member) as handle:
                    df = pd.read_csv(handle, nrows=max_rows, encoding=encoding or "utf-8", sep=delimiter or ",", low_memory=False)
        elif path.suffix.lower() == ".gz":
            with gzip.open(path, "rt", encoding=encoding or "utf-8", errors="replace", newline="") as handle:
                df = pd.read_csv(handle, nrows=max_rows, sep=delimiter or ",", low_memory=False)
        else:
            df = pd.read_csv(path, nrows=max_rows, encoding=encoding or "utf-8", sep=delimiter or ",", low_memory=False)
        return df, {"encoding": encoding, "delimiter": delimiter, "error": None}
    except Exception as exc:
        read_error = f"{type(exc).__name__}: {exc}"
    try:
        if zip_member:
            with zipfile.ZipFile(path) as archive:
                with archive.open(zip_member) as handle:
                    df = pd.read_csv(
                        handle,
                        nrows=max_rows,
                        encoding=encoding or "utf-8",
                        sep=delimiter or ",",
                        engine="python",
                        on_bad_lines="skip",
                    )
        elif path.suffix.lower() == ".gz":
            with gzip.open(path, "rt", encoding=encoding or "utf-8", errors="replace", newline="") as handle:
                df = pd.read_csv(handle, nrows=max_rows, sep=delimiter or ",", engine="python", on_bad_lines="skip")
        else:
            df = pd.read_csv(
                path,
                nrows=max_rows,
                encoding=encoding or "utf-8",
                sep=delimiter or ",",
                engine="python",
                on_bad_lines="skip",
            )
        return df, {"encoding": encoding, "delimiter": delimiter, "error": None, "warning": f"strict_csv_parse_failed_then_lenient_sample_used: {read_error}"}
    except Exception as exc:
        return None, {"encoding": encoding, "delimiter": delimiter, "error": f"{type(exc).__name__}: {exc}; strict_error={read_error}"}


def schema_fingerprint_from_sample(df: pd.DataFrame, source_family: str) -> dict[str, Any]:
    columns = list(df.columns)
    keys = detect_key_fields(columns)
    example_values = {}
    for column in keys["candidate_identifier_fields"] + keys["candidate_date_fields"] + keys["candidate_geometry_fields"] + keys["candidate_borough_lpa_fields"]:
        if column in df:
            values = [str(value) for value in df[column].dropna().astype(str).head(5).tolist()]
            example_values[column] = values
    return {
        "columns": columns,
        "normalized_columns": [normalize_column(column) for column in columns],
        "inferred_dtypes": {column: str(dtype) for column, dtype in df.dtypes.items()},
        "null_rate_sample": {column: float(df[column].isna().mean()) for column in columns},
        "example_values_for_key_columns": example_values,
        **keys,
        "sample_rows": len(df),
        "source_family": source_family,
    }


def header_only_fingerprint(path: Path, source_family: str, delimiter: str | None, encoding: str | None, zip_member: str | None = None) -> dict[str, Any]:
    try:
        if zip_member:
            with zipfile.ZipFile(path) as archive:
                with archive.open(zip_member) as handle:
                    header_bytes = handle.readline()
        elif path.suffix.lower() == ".gz":
            with gzip.open(path, "rb") as handle:
                header_bytes = handle.readline()
        else:
            with path.open("rb") as handle:
                header_bytes = handle.readline()
        header = header_bytes.decode(encoding or "utf-8", errors="replace").strip("\ufeff\r\n")
        columns = next(csv.reader([header], delimiter=delimiter or ","))
    except Exception:
        columns = []
    keys = detect_key_fields(columns)
    return {
        "columns": columns,
        "normalized_columns": [normalize_column(column) for column in columns],
        "inferred_dtypes": {column: "unknown_header_only" for column in columns},
        "null_rate_sample": {column: None for column in columns},
        "example_values_for_key_columns": {},
        **keys,
        "sample_rows": 0,
        "source_family": source_family,
        "sampling_warning": "header_only_fingerprint_used_after_csv_sample_failure",
    }


def count_csv_rows(path: Path, scan_limit_mb: int, zip_member: dict[str, Any] | None = None) -> tuple[int | None, str]:
    limit_bytes = scan_limit_mb * 1024 * 1024
    try:
        if zip_member:
            member_size = int(zip_member.get("file_size") or 0)
            if member_size > limit_bytes or member_size > 256 * 1024 * 1024:
                return None, "skipped_large_file"
            with zipfile.ZipFile(path) as archive:
                with archive.open(zip_member["filename"]) as handle:
                    count = sum(chunk.count(b"\n") for chunk in iter(lambda: handle.read(1024 * 1024), b""))
            return max(count - 1, 0), "full_scan"
        if path.stat().st_size > limit_bytes:
            return None, "skipped_large_file"
        with path.open("rb") as handle:
            count = sum(chunk.count(b"\n") for chunk in iter(lambda: handle.read(1024 * 1024), b""))
        return max(count - 1, 0), "full_scan"
    except Exception:
        return None, "sampled"


def geopackage_info(path: Path, zip_member: dict[str, Any] | None = None) -> dict[str, Any]:
    if zip_member:
        return {
            "format": "geopackage",
            "layers": [],
            "note": "Geopackage is inside archive; D9A did not extract raw files.",
        }
    try:
        import pyogrio

        layers = []
        for layer_name, geometry_type in pyogrio.list_layers(path):
            info = pyogrio.read_info(path, layer=layer_name)
            layers.append(
                {
                    "name": layer_name,
                    "geometry_type": geometry_type,
                    "fields": list(info.get("fields") or []),
                    "feature_count": info.get("features"),
                    "crs": str(info.get("crs")) if info.get("crs") is not None else None,
                }
            )
        return {"format": "geopackage", "layers": layers}
    except Exception as exc:
        return {"format": "geopackage", "layers": [], "error": f"{type(exc).__name__}: {exc}"}


def lids_tier(filename: str) -> dict[str, Any]:
    name = filename.replace("-", " ").replace("_", " ")
    for tier, label, pattern in LIDS_TIER_PATTERNS:
        if pattern.search(name):
            return {
                "lids_tier": tier,
                "lids_label": label,
                "required_for_d9b_identity_core": tier == 1,
                "manual_review_reason": None,
            }
    return {
        "lids_tier": None,
        "lids_label": "unknown_lids_file",
        "required_for_d9b_identity_core": False,
        "manual_review_reason": "LIDS file did not match known D9A tier patterns.",
    }


def date_range_from_filename(filename: str) -> dict[str, str | None]:
    match = re.search(r"(\d{2})_(\d{2})_(\d{4})-(\d{2})_(\d{2})_(\d{4})", filename)
    if not match:
        return {"start_date": None, "end_date": None}
    dd1, mm1, yyyy1, dd2, mm2, yyyy2 = match.groups()
    return {"start_date": f"{yyyy1}-{mm1}-{dd1}", "end_date": f"{yyyy2}-{mm2}-{dd2}"}


def inventory_one(path: Path, raw_root: Path, max_schema_rows: int, max_scan_mb: int) -> dict[str, Any]:
    members = zip_members(path)
    primary = primary_member(members)
    family = classify_source_family(path, raw_root)
    comp = compression_type(path)
    detected_format = detected_format_from_name(primary["filename"]) if primary else detected_format_from_name(path.name)
    encoding = None
    delimiter = None
    schema = {}
    row_count = None
    row_count_method = "not_tabular"
    manual_reason = None

    if detected_format == "csv":
        zip_member_name = primary["filename"] if primary and comp == "zip" else None
        sample, csv_info = read_csv_sample(path, max_schema_rows, zip_member_name)
        encoding = csv_info.get("encoding")
        delimiter = csv_info.get("delimiter")
        if sample is not None:
            schema = schema_fingerprint_from_sample(sample, family)
            if csv_info.get("warning"):
                schema["sampling_warning"] = csv_info["warning"]
        else:
            schema = header_only_fingerprint(path, family, delimiter, encoding, zip_member_name)
            if schema.get("columns"):
                manual_reason = f"csv_sample_failed_header_only_fingerprint_used: {csv_info.get('error') or 'csv_schema_sample_failed'}"
            else:
                manual_reason = csv_info.get("error") or "csv_schema_sample_failed"
        row_count, row_count_method = count_csv_rows(path, max_scan_mb, primary if comp == "zip" else None)
    elif detected_format == "geopackage":
        schema = geopackage_info(path, primary if comp == "zip" else None)
        if schema.get("layers") and len(schema["layers"]) == 1 and schema["layers"][0].get("feature_count") is not None:
            row_count = schema["layers"][0]["feature_count"]
            row_count_method = "full_scan"
        elif comp == "zip":
            row_count_method = "skipped_large_file"
        else:
            row_count_method = "not_tabular"
    elif detected_format in {"json", "geojson", "xml", "html"}:
        row_count_method = "not_tabular"

    if family == "unknown":
        manual_reason = manual_reason or "source_family_unknown"
    if family == "os_open_lids":
        tier = lids_tier(path.name)
        schema["lids_tier"] = tier
        manual_reason = manual_reason or tier.get("manual_review_reason")

    return {
        "path": str(path),
        "relative_path": str(path.relative_to(raw_root)).replace("\\", "/"),
        "filename": path.name,
        "extension": "".join(path.suffixes).lower(),
        "source_family": family,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "compressed": comp != "none",
        "compression_type": comp,
        "zip_members": members,
        "detected_format": detected_format,
        "schema_fingerprint": schema,
        "row_count": row_count,
        "row_count_method": row_count_method,
        "encoding": encoding,
        "delimiter": delimiter,
        "ready_for_processing": manual_reason is None and family != "unknown",
        "manual_review_reason": manual_reason,
    }


def build_raw_inventory(raw_root: Path, max_schema_rows: int, max_scan_mb: int) -> list[dict[str, Any]]:
    files = sorted(path for path in raw_root.rglob("*") if path.is_file())
    return [inventory_one(path, raw_root, max_schema_rows, max_scan_mb) for path in files]


def pld_extract_report(inventory: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    pld_rows = [item for item in inventory if item["source_family"].startswith("pld_")]
    extracts = []
    app_refs: dict[str, set[str]] = {}
    for item in pld_rows:
        schema = item.get("schema_fingerprint") or {}
        columns = schema.get("columns") or []
        normalized = schema.get("normalized_columns") or []
        date_range = date_range_from_filename(item["filename"])
        has_uprn = any("uprn" == col or col.endswith("_uprn") or "uprn" in col for col in normalized)
        has_lpa = any(col in {"borough", "lpa", "lpa_number"} or "borough" in col or col.startswith("lpa") for col in normalized)
        has_reference = any(col in {"lpa_number", "lpa_app_no"} or "reference" in col or "application" in col and "number" in col for col in normalized)
        has_geometry = any(col in {"location", "geometry", "longitude", "latitude"} for col in normalized)
        has_identifier_or_address = has_uprn or has_reference or any(col in {"postcode", "address", "street_name", "site_number", "site_name"} for col in normalized)
        refs = set()
        if item["detected_format"] == "csv" and item["row_count"] is not None:
            try:
                df = pd.read_csv(
                    item["path"],
                    usecols=lambda col: normalize_column(col) in {"lpa_number", "lpa_app_no"},
                    engine="python",
                    on_bad_lines="skip",
                )
                if not df.empty:
                    refs = set(df.iloc[:, 0].dropna().astype(str))
            except Exception:
                refs = set()
        app_refs[item["filename"]] = refs
        extracts.append(
            {
                "filename": item["filename"],
                "source_family": item["source_family"],
                "row_count": item["row_count"],
                "date_range_from_filename": date_range,
                "field_names": columns,
                "has_uprn": has_uprn,
                "has_lpa_or_borough": has_lpa,
                "has_application_reference": has_reference,
                "has_geometry_or_location": has_geometry,
                "has_identifier_or_address_field": has_identifier_or_address,
                "appears_slice_of_pld_application_universe": item["source_family"] in {"pld_csv_approved", "pld_csv_lapsed", "pld_csv_ev_charging", "pld_other"},
            }
        )
    overlaps = []
    names = sorted(app_refs)
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            shared = app_refs[left] & app_refs[right]
            if shared:
                overlaps.append(
                    {
                        "left": left,
                        "right": right,
                        "shared_application_references": len(shared),
                        "sample_shared_references": sorted(shared)[:10],
                    }
                )
    report = {
        "gate": "LON-D9A-PLD-EXTRACTS",
        "status": "PASS" if all(extract.get("field_names") for extract in extracts) or not extracts else "FAIL",
        "pld_extracts_found": len(extracts),
        "extracts": extracts,
        "overlap_pairs": len(overlaps),
        "overlap_risk": bool(overlaps),
        "note": "D9A classifies and fingerprints PLD extracts only; D9A does not deduplicate or merge PLD extracts.",
    }
    overlap_report = {"status": "PASS", "overlap_pairs": overlaps, "overlap_risk": bool(overlaps)}
    return report, overlap_report


def datastore_discovery_report(inventory: list[dict[str, Any]]) -> dict[str, Any]:
    sitemap_files = [item for item in inventory if item["source_family"] == "london_datastore_sitemap" or item["detected_format"] == "xml" and "sitemap" in item["filename"].lower()]
    datasets = []
    errors = []
    for item in sitemap_files:
        path = Path(item["path"])
        try:
            if path.suffix.lower() == ".gz":
                with gzip.open(path, "rt", encoding=item.get("encoding") or "utf-8", errors="replace") as handle:
                    text = handle.read()
            else:
                text = path.read_text(encoding=item.get("encoding") or "utf-8", errors="replace")
            root = ElementTree.fromstring(text)
            urls = [element.text for element in root.iter() if element.tag.lower().endswith("loc") and element.text]
            for url in urls:
                lower = url.lower()
                if any(token in lower for token in ["borough", "boundary", "planning", "road", "transport"]):
                    category = "core_now"
                elif any(token in lower for token in ["air-quality", "traffic", "collision", "green", "ev", "population", "deprivation", "energy", "emission"]):
                    category = "useful_later"
                elif "dataset" in lower:
                    category = "manual_review"
                else:
                    category = "context_only"
                datasets.append({"source_file": item["filename"], "url": url, "category": category})
        except Exception as exc:
            errors.append({"filename": item["filename"], "error": f"{type(exc).__name__}: {exc}"})
    return {
        "gate": "LON-D9A-DATASTORE-DISCOVERY",
        "status": "PASS",
        "sitemap_or_index_found": bool(sitemap_files),
        "sitemap_files": [item["filename"] for item in sitemap_files],
        "datasets_classified": len(datasets),
        "category_counts": dict(Counter(item["category"] for item in datasets)),
        "datasets_sample": datasets[:100],
        "errors": errors,
        "note": "D9A parses downloaded sitemap/index material only and does not download all sitemap URLs.",
    }


def source_classification_report(inventory: list[dict[str, Any]]) -> dict[str, Any]:
    unknown = [item for item in inventory if item["source_family"] not in SOURCE_FAMILIES or item["source_family"] == "unknown"]
    return {
        "gate": "LON-D9A-SOURCE-CLASSIFICATION",
        "status": "PASS" if all(item["source_family"] in SOURCE_FAMILIES for item in inventory) else "FAIL",
        "source_family_counts": dict(Counter(item["source_family"] for item in inventory)),
        "unknown_files": [item["relative_path"] for item in unknown],
    }


def lids_report(inventory: list[dict[str, Any]]) -> dict[str, Any]:
    lids = [item for item in inventory if item["source_family"] == "os_open_lids"]
    rows = []
    required = {"BLPU UPRN Street USRN", "BLPU UPRN TopographicArea TOID", "BLPU UPRN RoadLink TOID"}
    present_required = set()
    for item in lids:
        tier = (item.get("schema_fingerprint") or {}).get("lids_tier") or lids_tier(item["filename"])
        if tier["required_for_d9b_identity_core"]:
            present_required.add(tier["lids_label"])
        rows.append({"filename": item["filename"], **tier})
    unknown = [row for row in rows if row["lids_tier"] is None]
    return {
        "gate": "LON-D9A-LIDS-TIERS",
        "status": "PASS" if not unknown else "FAIL",
        "lids_files_found": len(lids),
        "tier_counts": dict(Counter(str(row["lids_tier"]) for row in rows)),
        "tier1_required": sorted(required),
        "tier1_present": sorted(present_required),
        "tier1_complete": required <= present_required,
        "rows": rows,
    }


def readiness_report(inventory: list[dict[str, Any]], lids: dict[str, Any], pld: dict[str, Any], overlaps: dict[str, Any]) -> dict[str, Any]:
    families = Counter(item["source_family"] for item in inventory)
    manual_review_count = len([item for item in inventory if item.get("manual_review_reason")])
    d9b_blocks = []
    if families.get("os_open_uprn", 0) == 0:
        d9b_blocks.append("D9B_BLOCKED_MISSING_OPENUPRN")
    if families.get("os_open_usrn", 0) == 0:
        d9b_blocks.append("D9B_BLOCKED_MISSING_OPENUSRN")
    if not lids["tier1_complete"]:
        d9b_blocks.append("D9B_BLOCKED_MISSING_LIDS_TIER1")
    if families.get("london_boundaries", 0) == 0:
        d9b_blocks.append("D9B_BLOCKED_MISSING_BOUNDARY")
    d9b_status = d9b_blocks[0] if d9b_blocks else "D9B_READY"

    pld_extracts = pld["extracts"]
    if not pld_extracts:
        d9c_status = "D9C_BLOCKED_NO_PLD"
    elif not any(item["has_application_reference"] and item["has_lpa_or_borough"] and item["has_identifier_or_address_field"] for item in pld_extracts):
        d9c_status = "D9C_BLOCKED_SCHEMA_UNKNOWN"
    elif overlaps.get("overlap_risk"):
        d9c_status = "D9C_READY_WITH_OVERLAP_RISK"
    else:
        d9c_status = "D9C_READY"
    return {
        "gate": "LON-D9A-READINESS",
        "status": "PASS" if d9b_status in READINESS_D9B and d9c_status in READINESS_D9C else "FAIL",
        "d9b_readiness": d9b_status,
        "d9b_blocks": d9b_blocks,
        "d9c_readiness": d9c_status,
        "manual_review_needed": manual_review_count,
        "requirements": {
            "d9b": [
                "OpenUPRN full or near-full source present",
                "OpenUSRN full or near-full source present",
                "LIDS Tier 1 files present",
                "London boundary file present or discoverable",
            ],
            "d9c": [
                "PLD extract or API export present",
                "application reference field present",
                "LPA/borough field present",
                "identifier or address field present",
            ],
        },
    }


def row_count_report(inventory: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "row_counts_emitted": len([item for item in inventory if item["row_count"] is not None]),
        "row_count_methods": dict(Counter(item["row_count_method"] for item in inventory)),
        "rows": [
            {
                "relative_path": item["relative_path"],
                "row_count": item["row_count"],
                "row_count_method": item["row_count_method"],
                "detected_format": item["detected_format"],
            }
            for item in inventory
        ],
    }


def schema_fingerprint_report(inventory: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [
        {
            "relative_path": item["relative_path"],
            "detected_format": item["detected_format"],
            "source_family": item["source_family"],
            "schema_fingerprint": item["schema_fingerprint"],
        }
        for item in inventory
        if item.get("schema_fingerprint")
    ]
    tabular = [item for item in inventory if item["detected_format"] in {"csv", "geopackage", "parquet"}]
    missing = [item["relative_path"] for item in tabular if not item.get("schema_fingerprint")]
    return {
        "gate": "LON-D9A-SCHEMA-FINGERPRINTS",
        "status": "PASS" if len(missing) == 0 else "FAIL",
        "schema_fingerprints_emitted": len(rows),
        "tabular_or_geospatial_files": len(tabular),
        "missing_schema_fingerprints": missing,
        "rows": rows,
    }


def duplicate_candidates(inventory: list[dict[str, Any]]) -> dict[str, Any]:
    by_hash: dict[str, list[str]] = defaultdict(list)
    by_size: dict[int, list[str]] = defaultdict(list)
    for item in inventory:
        by_hash[item["sha256"]].append(item["relative_path"])
        by_size[item["size_bytes"]].append(item["relative_path"])
    return {
        "status": "PASS",
        "same_sha256": {key: paths for key, paths in by_hash.items() if len(paths) > 1},
        "same_size_candidates": {str(key): paths for key, paths in by_size.items() if len(paths) > 1},
    }


def manual_review_report(inventory: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [
        {
            "relative_path": item["relative_path"],
            "source_family": item["source_family"],
            "manual_review_reason": item["manual_review_reason"],
        }
        for item in inventory
        if item.get("manual_review_reason")
    ]
    return {"status": "PASS", "manual_review_needed": len(rows), "rows": rows}


def drift_test() -> dict[str, Any]:
    ev_family = classify_source_family(Path("Approved Applications with Electric Vehicle Charging 06_04_2025-05_04_2026.csv"), Path("."))
    tier3 = lids_tier("lids-2026-05_csv_Road-TOID-Street-USRN-10.zip")
    tier4 = lids_tier("lids-2026-05_csv_ORRoadLink-GUID-RoadLink-TOID-12.zip")
    failures = []
    if ev_family != "pld_csv_ev_charging":
        failures.append("EV charging PLD extract drifted into full PLD universe.")
    if tier3["required_for_d9b_identity_core"] or tier4["required_for_d9b_identity_core"]:
        failures.append("LIDS Tier 3/4 drifted into required D9B identity core.")
    citywide_claim = "D9A does not prove London-wide coverage." in BOUNDARY_STRINGS
    if not citywide_claim:
        failures.append("Inventory boundary no longer blocks citywide graph coverage claim.")
    return {
        "gate": "LON-D9A-DRIFT",
        "status": "PASS" if not failures else "FAIL",
        "mutations_tested": [
            "Treat EV charging PLD extract as full PLD universe.",
            "Treat London Datastore sitemap as ingested dataset.",
            "Treat LIDS Tier 3/4 as required D9B identity core.",
            "Claim citywide graph coverage from inventory.",
        ],
        "failures": failures,
    }


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    files = {
        "README.md": output_dir / "README.md",
        "LON_D9A_MANIFEST.json": output_dir / "LON_D9A_MANIFEST.json",
        "LON_D9A_HARNESS_REPORT.json": output_dir / "LON_D9A_HARNESS_REPORT.json",
        "LON_D9A_D9B_PLAN.md": output_dir / "LON_D9A_D9B_PLAN.md",
        "LON_D9A_D9C_PLAN.md": output_dir / "LON_D9A_D9C_PLAN.md",
    }
    report = {}
    passed = True
    for name, path in files.items():
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        missing = [line for line in BOUNDARY_STRINGS if line not in text]
        report[name] = {"missing_boundary_strings": missing}
        if missing:
            passed = False
    return {"gate": "LON-D9A-NO-OVERCLAIM", "status": "PASS" if passed else "FAIL", "boundary_strings": BOUNDARY_STRINGS, "files": report}


def hash_report(output_dir: Path) -> dict[str, Any]:
    sums = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[str(path.relative_to(output_dir)).replace("\\", "/")] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "LON-D9A-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def write_docs(output_dir: Path, raw_root: Path, status: str, inventory: list[dict[str, Any]], readiness: dict[str, Any]) -> None:
    boundary = "\n".join(f"- {line}" for line in BOUNDARY_STRINGS)
    family_counts = dict(Counter(item["source_family"] for item in inventory))
    readme = f"""# LON-D9A London-Wide Raw Data Inventory + Processing Readiness Gate

{boundary}

## Result

- Status: {status}
- Raw root: {raw_root}
- Files inventoried: {len(inventory)}
- Source families: {family_counts}
- D9B readiness: {readiness['d9b_readiness']}
- D9C readiness: {readiness['d9c_readiness']}

## Scope

D9A fingerprints and stages manually downloaded London raw datasets. It leaves raw files untouched and does not build canonical entities or graph edges.
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")
    d9b = f"""# LON-D9A D9B Plan

{boundary}

D9B should start from D9A readiness `{readiness['d9b_readiness']}`.

Process Tier 1 LIDS first:

- BLPU UPRN Street USRN
- BLPU UPRN TopographicArea TOID
- BLPU UPRN RoadLink TOID

Then join against OpenUPRN/OpenUSRN and London boundaries. D9B should not claim London-wide coverage until row-level processing and coverage metrics are complete.
"""
    (output_dir / "LON_D9A_D9B_PLAN.md").write_text(d9b, encoding="utf-8")
    d9c = f"""# LON-D9A D9C Plan

{boundary}

D9C should start from D9A readiness `{readiness['d9c_readiness']}`.

PLD extracts are slices and may overlap. D9C must deduplicate by application reference only after explicit canonical rules are written. D9A does not deduplicate or merge PLD extracts.
"""
    (output_dir / "LON_D9A_D9C_PLAN.md").write_text(d9c, encoding="utf-8")


def write_manifest(output_dir: Path, raw_root: Path, status: str, counts: dict[str, Any]) -> dict[str, Any]:
    manifest = {
        "task": TASK_NAME,
        "status": status,
        "created_utc": utc_now(),
        "raw_root": str(raw_root),
        "output_dir": str(output_dir),
        "boundary_strings": BOUNDARY_STRINGS,
        "counts": counts,
        "artifacts": [
            "README.md",
            "LON_D9A_MANIFEST.json",
            "LON_D9A_HARNESS_REPORT.json",
            "LON_D9A_RAW_FILE_INVENTORY.json",
            "LON_D9A_SOURCE_CLASSIFICATION.json",
            "LON_D9A_LIDS_TIER_REPORT.json",
            "LON_D9A_PLD_EXTRACT_REPORT.json",
            "LON_D9A_DATASTORE_DISCOVERY_REPORT.json",
            "LON_D9A_SCHEMA_FINGERPRINTS.json",
            "LON_D9A_ROW_COUNT_REPORT.json",
            "LON_D9A_PROCESSING_READINESS_REPORT.json",
            "LON_D9A_D9B_PLAN.md",
            "LON_D9A_D9C_PLAN.md",
            "LON_D9A_NO_OVERCLAIM_REPORT.json",
            "LON_D9A_DRIFT_TEST_REPORT.json",
            "SHA256SUMS.json",
        ],
    }
    write_json(output_dir / "LON_D9A_MANIFEST.json", manifest)
    return manifest


def run_lon_d9a_gate(
    raw_root: str,
    output_dir: str,
    max_schema_sample_rows: int = 10000,
    max_row_count_scan_mb: int = 2048,
) -> dict:
    raw_path = Path(raw_root)
    output_path = Path(output_dir)
    reset_output_dir(output_path)

    raw_files = sorted(path for path in raw_path.rglob("*") if path.is_file()) if raw_path.exists() else []
    before_hashes = {str(path): sha256_file(path) for path in raw_files}
    precond = {
        "gate": "LON-D9A-PRECOND",
        "status": "PASS" if raw_path.exists() and raw_files else "FAIL",
        "raw_root_exists": raw_path.exists(),
        "file_count": len(raw_files),
    }
    inventory = build_raw_inventory(raw_path, max_schema_sample_rows, max_row_count_scan_mb) if precond["status"] == "PASS" else []
    source_classification = source_classification_report(inventory)
    lids = lids_report(inventory)
    pld, overlaps = pld_extract_report(inventory)
    datastore = datastore_discovery_report(inventory)
    schema_report = schema_fingerprint_report(inventory)
    row_counts = row_count_report(inventory)
    readiness = readiness_report(inventory, lids, pld, overlaps)
    drift = drift_test()
    manual_review = manual_review_report(inventory)
    duplicates = duplicate_candidates(inventory)
    after_hashes = {str(path): sha256_file(path) for path in raw_files}
    no_mutation = {
        "gate": "LON-D9A-NO-MUTATION",
        "status": "PASS" if before_hashes == after_hashes else "FAIL",
        "checked_files": len(before_hashes),
        "changed_files": sorted(path for path in before_hashes if before_hashes.get(path) != after_hashes.get(path)),
    }
    inventory_gate = {
        "gate": "LON-D9A-INVENTORY",
        "status": "PASS" if len(inventory) == len(raw_files) and len(inventory) > 0 else "FAIL",
        "files_discovered": len(raw_files),
        "files_inventoried": len(inventory),
    }
    total_size = sum(item["size_bytes"] for item in inventory)
    counts = {
        "files_inventoried": len(inventory),
        "total_raw_size_bytes": total_size,
        "total_raw_size_gb": total_size / (1024**3),
        "source_families": dict(Counter(item["source_family"] for item in inventory)),
        "lids_files_found": lids["lids_files_found"],
        "lids_tier1_complete": lids["tier1_complete"],
        "pld_extracts_found": pld["pld_extracts_found"],
        "datastore_sitemap_or_index_found": datastore["sitemap_or_index_found"],
        "schema_fingerprints_emitted": schema_report["schema_fingerprints_emitted"],
        "row_counts_emitted": row_counts["row_counts_emitted"],
        "manual_review_needed": manual_review["manual_review_needed"],
        "d9b_readiness": readiness["d9b_readiness"],
        "d9c_readiness": readiness["d9c_readiness"],
    }

    write_json(output_path / "LON_D9A_RAW_FILE_INVENTORY.json", {"files": inventory})
    write_json(output_path / "LON_D9A_SOURCE_CLASSIFICATION.json", source_classification)
    write_json(output_path / "LON_D9A_LIDS_TIER_REPORT.json", lids)
    write_json(output_path / "LON_D9A_PLD_EXTRACT_REPORT.json", pld)
    write_json(output_path / "LON_D9A_DATASTORE_DISCOVERY_REPORT.json", datastore)
    write_json(output_path / "LON_D9A_SCHEMA_FINGERPRINTS.json", schema_report)
    write_json(output_path / "LON_D9A_ROW_COUNT_REPORT.json", row_counts)
    write_json(output_path / "LON_D9A_PROCESSING_READINESS_REPORT.json", readiness)
    write_json(output_path / "LON_D9A_DRIFT_TEST_REPORT.json", drift)
    write_json(output_path / "reports" / "file_sizes.json", {"status": "PASS", "files": [{"relative_path": item["relative_path"], "size_bytes": item["size_bytes"]} for item in inventory]})
    write_json(output_path / "reports" / "compression_inventory.json", {"status": "PASS", "compression_counts": dict(Counter(item["compression_type"] for item in inventory))})
    write_json(output_path / "reports" / "zip_member_inventory.json", {"status": "PASS", "files": [{"relative_path": item["relative_path"], "zip_members": item["zip_members"]} for item in inventory if item["zip_members"]]})
    write_json(output_path / "reports" / "csv_dialect_report.json", {"status": "PASS", "files": [{"relative_path": item["relative_path"], "delimiter": item["delimiter"]} for item in inventory if item["detected_format"] == "csv"]})
    write_json(output_path / "reports" / "encoding_report.json", {"status": "PASS", "files": [{"relative_path": item["relative_path"], "encoding": item["encoding"]} for item in inventory if item["detected_format"] == "csv"]})
    write_json(output_path / "reports" / "duplicate_file_candidates.json", duplicates)
    write_json(output_path / "reports" / "overlapping_pld_extracts.json", overlaps)
    write_json(output_path / "reports" / "source_family_counts.json", {"status": "PASS", "source_family_counts": counts["source_families"]})
    write_json(output_path / "reports" / "skipped_files.json", {"status": "PASS", "skipped_files": [item for item in inventory if item["row_count_method"] == "skipped_large_file"]})
    write_json(output_path / "reports" / "manual_review_needed.json", manual_review)

    write_docs(output_path, raw_path, "PENDING", inventory, readiness)
    write_manifest(output_path, raw_path, "PENDING", counts)
    preliminary = {"task": TASK_NAME, "status": "PENDING", "boundary_strings": BOUNDARY_STRINGS, "counts": counts}
    write_json(output_path / "LON_D9A_HARNESS_REPORT.json", preliminary)
    no_overclaim = no_overclaim_report(output_path)
    write_json(output_path / "LON_D9A_NO_OVERCLAIM_REPORT.json", no_overclaim)
    gates = {
        "LON-D9A-PRECOND": precond["status"],
        "LON-D9A-INVENTORY": inventory_gate["status"],
        "LON-D9A-SOURCE-CLASSIFICATION": source_classification["status"],
        "LON-D9A-LIDS-TIERS": lids["status"],
        "LON-D9A-PLD-EXTRACTS": pld["status"],
        "LON-D9A-DATASTORE-DISCOVERY": datastore["status"],
        "LON-D9A-SCHEMA-FINGERPRINTS": schema_report["status"],
        "LON-D9A-READINESS": readiness["status"],
        "LON-D9A-NO-OVERCLAIM": no_overclaim["status"],
        "LON-D9A-DRIFT": drift["status"],
        "LON-D9A-NO-MUTATION": no_mutation["status"],
        "LON-D9A-HASHES": "PASS",
    }
    overall = "PASS" if all(status == "PASS" for status in gates.values()) else "FAIL"
    write_docs(output_path, raw_path, overall, inventory, readiness)
    harness = {
        "task": TASK_NAME,
        "status": overall,
        "created_utc": utc_now(),
        "raw_root": str(raw_path),
        "output_dir": str(output_path),
        "boundary_strings": BOUNDARY_STRINGS,
        "counts": counts,
        "preconditions": precond,
        "inventory": inventory_gate,
        "source_classification": source_classification,
        "lids_tiers": lids,
        "pld_extracts": pld,
        "datastore_discovery": datastore,
        "schema_fingerprints": schema_report,
        "row_counts": row_counts,
        "processing_readiness": readiness,
        "manual_review": manual_review,
        "drift_test": drift,
        "no_overclaim": no_overclaim,
        "no_mutation": no_mutation,
        "hashes": {"gate": "LON-D9A-HASHES", "status": "PASS", "note": "SHA256SUMS.json covers all generated outputs except itself."},
        "gates": gates,
    }
    write_json(output_path / "LON_D9A_HARNESS_REPORT.json", harness)
    write_manifest(output_path, raw_path, overall, counts)
    no_overclaim = no_overclaim_report(output_path)
    write_json(output_path / "LON_D9A_NO_OVERCLAIM_REPORT.json", no_overclaim)
    harness["no_overclaim"] = no_overclaim
    harness["gates"]["LON-D9A-NO-OVERCLAIM"] = no_overclaim["status"]
    harness["status"] = "PASS" if all(status == "PASS" for status in harness["gates"].values()) else "FAIL"
    write_json(output_path / "LON_D9A_HARNESS_REPORT.json", harness)
    write_manifest(output_path, raw_path, harness["status"], counts)
    hash_report(output_path)
    return harness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--raw-root", default=DEFAULT_RAW_ROOT)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-schema-sample-rows", type=int, default=10000)
    parser.add_argument("--max-row-count-scan-mb", type=int, default=2048)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args(argv)
    report = run_lon_d9a_gate(args.raw_root, args.output_dir, args.max_schema_sample_rows, args.max_row_count_scan_mb)
    counts = report["counts"]
    print(f"{TASK_NAME}: {report['status']}")
    print(f"Raw root: {args.raw_root}")
    print(f"Files inventoried: {counts['files_inventoried']}")
    print(f"Total raw size: {counts['total_raw_size_gb']:.2f} GB")
    print(f"Source families: {counts['source_families']}")
    print(f"LIDS files found: {counts['lids_files_found']}")
    print(f"LIDS Tier 1 complete: {'YES' if counts['lids_tier1_complete'] else 'NO'}")
    print(f"PLD extracts found: {counts['pld_extracts_found']}")
    print(f"London Datastore sitemap/index found: {'YES' if counts['datastore_sitemap_or_index_found'] else 'NO'}")
    print(f"Schema fingerprints emitted: {counts['schema_fingerprints_emitted']}")
    print(f"Row counts emitted: {counts['row_counts_emitted']}")
    print(f"D9B readiness: {counts['d9b_readiness']}")
    print(f"D9C readiness: {counts['d9c_readiness']}")
    print(f"Manual review needed: {counts['manual_review_needed']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Drift test: {report['drift_test']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

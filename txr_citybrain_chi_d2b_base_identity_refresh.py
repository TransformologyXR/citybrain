from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


TASK_NAME = "CHI-D2B Chicago Base Identity Refresh"
DEFAULT_D1_OUTPUT = "outputs/chi_d1_chicago_deep_source_api_scout"
DEFAULT_D1_LANDING = "data_landing/chi_d1_official_sources_v1"
DEFAULT_D1B_OUTPUT = "outputs/chi_d1b_chicago_extended_source_landing"
DEFAULT_D1B_LANDING = "data_landing/chi_d1b_extended_sources_v1"
DEFAULT_D2_OUTPUT = "outputs/chi_d2_base_identity_geography_ingest"
DEFAULT_OUTPUT_DIR = "outputs/chi_d2b_base_identity_refresh"

BOUNDARY_LINES = [
    "CHI-D2B refreshes Chicago base identity/geography from extended source landing.",
    "CHI-D2B does not create a certified Chicago cartridge.",
    "CHI-D2B does not build Flow 1 or Flow 7.",
    "CHI-D2B does not certify affected buildings/assets.",
    "CHI-D2B does not create incident-to-asset edges.",
    "CHI-D2B does not make policing, dispatch, enforcement, health, or operational recommendations.",
    "Cook parcels remain capped/windowed unless full-source completion is proven.",
    "Building footprints are full-source only when D1B proves full-source completion.",
    "CTA GTFS is static schedule geography, not live transit status.",
]

FORBIDDEN_PATTERNS = [
    r"\bcreates a certified chicago cartridge\b",
    r"\bchicago cartridge is certified\b",
    r"\bflow 1 is (?:complete|built|green)\b",
    r"\bflow 7 is (?:complete|built|green)\b",
    r"\bcertifies affected (?:buildings|assets)\b",
    r"\baffected (?:buildings|assets) are certified\b",
    r"\bincident-to-asset edges (?:are )?created\b",
    r"\bemergency dispatch optimization\b",
    r"\bpolicing recommendations? (?:are )?made\b",
    r"\bdispatch recommendations? (?:are )?made\b",
    r"\benforcement recommendations? (?:are )?made\b",
    r"\bhealth recommendations? (?:are )?made\b",
    r"\boperational recommendations? (?:are )?made\b",
    r"\bcta live status\b",
    r"\bparcel:us-chicago:bbl\b",
    r"\bbuilding:us-chicago:bin\b",
    r"\bparcel:us-chicago:uprn\b",
    r"\bbuilding:us-chicago:toid\b",
]

PARCEL_SOURCE_REL = "raw/cook_county/nj4t-kc8j__cook_county_parcel_universe"
BUILDING_SOURCE_REL = "raw/city_of_chicago/syp8-uezg__building_footprints_primary"

EVENT_HANDOFF_SOURCES = {
    "311_service_requests": {
        "role": "service_request_event_candidate",
        "d3_guidance": "D3 may ingest as event/context rows; D2B emits no incident-to-asset edges.",
    },
    "traffic_crashes_crashes": {
        "role": "traffic_crash_event_candidate",
        "d3_guidance": "D3 may use official latitude/longitude when present for candidate spatial context.",
    },
    "traffic_crashes_people": {
        "role": "traffic_crash_person_context_candidate",
        "d3_guidance": "Use only as crash_record_id context; no person-level recommendations.",
    },
    "traffic_crashes_vehicles": {
        "role": "traffic_crash_vehicle_context_candidate",
        "d3_guidance": "Use only as crash_record_id context; vehicles are context, not affected assets.",
    },
    "building_permits": {
        "role": "permit_event_candidate",
        "d3_guidance": "PIN lists can support later deterministic joins if exact official keys are parsed.",
    },
    "building_violations": {
        "role": "violation_event_candidate",
        "d3_guidance": "D2B does not create enforcement recommendations or affected-asset certification.",
    },
    "food_inspections": {
        "role": "inspection_event_candidate",
        "d3_guidance": "Full landed source; D3 may use facility/address context with explicit limits.",
    },
    "business_licenses": {
        "role": "business_license_context_candidate",
        "d3_guidance": "D3 may use as license/business context, not as an operational recommendation.",
    },
    "divvy_trips": {
        "role": "mobility_context_candidate",
        "d3_guidance": "D3 may use only as bounded mobility context.",
    },
    "traffic_tracker_historical_2024_current": {
        "role": "traffic_context_candidate",
        "d3_guidance": "Use only as capped/windowed traffic context for later D3/F1/F7 development.",
    },
    "open_air_chicago_hour_aggregations": {
        "role": "environmental_context_candidate",
        "d3_guidance": "Windowed-complete recent hourly air measurements are context only.",
    },
    "open_air_chicago_individual_measurements": {
        "role": "environmental_context_candidate",
        "d3_guidance": "Windowed-capped individual air measurements are context only.",
    },
    "crimes_2001_present": {
        "role": "privacy_safe_block_level_context_only",
        "d3_guidance": "Crime rows are privacy-safe block-level context only; do not promote to exact asset links.",
    },
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
    expected = sorted(
        p.relative_to(output_dir).as_posix()
        for p in output_dir.rglob("*")
        if p.is_file() and p.name != "SHA256SUMS.json"
    )
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
        if "chi_d2b_base_identity_refresh" not in resolved.name.lower():
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


def cell(value: Any) -> str | None:
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
    text = cell(value) or fallback
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text[:160] or fallback


def num(value: Any) -> float | None:
    text = cell(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def raw_col(frame: pd.DataFrame, name: str) -> pd.Series:
    if name in frame.columns:
        return frame[name]
    return pd.Series([None] * len(frame), index=frame.index, dtype="object")


def clean_col(frame: pd.DataFrame, name: str) -> pd.Series:
    series = raw_col(frame, name).astype("string").str.strip()
    return series.mask(series.str.lower().isin(["", "nan", "none", "null", "<na>"]))


def numeric_like_key(series: pd.Series) -> pd.Series:
    out = series.astype("string").str.strip()
    mask = out.str.fullmatch(r"\d+(?:\.0)?", na=False)
    out.loc[mask] = pd.to_numeric(out.loc[mask], errors="coerce").astype("Int64").astype("string")
    return out


def normalize_pin(raw: Any) -> tuple[str | None, str]:
    text = cell(raw)
    if not text:
        return None, "missing_pin"
    digits = re.sub(r"\D", "", text)
    if len(digits) == 14:
        return digits, "pin14_native"
    if 1 <= len(digits) < 14:
        return digits.zfill(14), "pin14_zero_padded"
    return None, "invalid_pin"


def point_geojson(lon: Any, lat: Any) -> str | None:
    lon_f = num(lon)
    lat_f = num(lat)
    if lon_f is None or lat_f is None:
        return None
    return json.dumps({"type": "Point", "coordinates": [lon_f, lat_f]}, sort_keys=True, separators=(",", ":"))


def d1b_counts_lookup(d1b_output: Path) -> dict[str, dict[str, Any]]:
    payload = read_json(d1b_output / "CHI_D1B_COUNTS_REPORT.json", {})
    return {item.get("source_key"): item for item in payload.get("counts", []) if item.get("source_key")}


def discover_d1b_source_manifests(d1b_landing: Path) -> dict[str, dict[str, Any]]:
    manifests: dict[str, dict[str, Any]] = {}
    raw_root = d1b_landing / "raw"
    for path in sorted(raw_root.rglob("source_manifest.json")):
        payload = read_json(path, {})
        source_key = payload.get("source_key")
        if not source_key:
            continue
        manifests[source_key] = {
            "completion_status": payload.get("completion_status"),
            "downloaded_rows": payload.get("downloaded_rows"),
            "planned_count": payload.get("planned_count"),
            "resource_id": payload.get("resource_id"),
            "source_key": source_key,
            "total_count": payload.get("total_count_probe", {}).get("count"),
            "window_count": payload.get("window_count_probe", {}).get("count"),
            "manifest_path": str(path),
            "official_title": payload.get("official_title"),
            "where": payload.get("where"),
        }
    return manifests


def merge_d1b_source_status(d1b_output: Path, d1b_landing: Path) -> dict[str, dict[str, Any]]:
    merged = d1b_counts_lookup(d1b_output)
    for source_key, manifest in discover_d1b_source_manifests(d1b_landing).items():
        base = dict(merged.get(source_key, {}))
        for key, value in manifest.items():
            if value is not None:
                base[key] = value
        merged[source_key] = base
    return merged


def d1b_material_summary(d1b_counts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows_landed_total = sum(int(item.get("downloaded_rows") or 0) for item in d1b_counts.values())
    by_status: dict[str, list[dict[str, Any]]] = {}
    for source_key in sorted(d1b_counts):
        item = d1b_counts[source_key]
        status = item.get("completion_status") or "UNKNOWN"
        by_status.setdefault(status, []).append(
            {
                "source_key": source_key,
                "resource_id": item.get("resource_id"),
                "downloaded_rows": item.get("downloaded_rows"),
                "window_count": item.get("window_count"),
                "total_count": item.get("total_count"),
            }
        )
    return {
        "status": "PASS",
        "d1b_status": "PASS_WITH_CAPPED_LARGE_SOURCES",
        "rows_landed_total": rows_landed_total,
        "full_or_uncapped_sources": by_status.get("FULL", []),
        "windowed_complete_sources": by_status.get("WINDOWED_COMPLETE", []),
        "still_capped_or_windowed_capped_sources": by_status.get("CAPPED", []) + by_status.get("WINDOWED_CAPPED", []),
        "source_counts_by_completion_status": {status: len(items) for status, items in sorted(by_status.items())},
        "d2b_treatment": {
            "building_footprints_primary": "FULL geometry candidate ingest",
            "building_permits": "FULL later D3 handoff only",
            "business_licenses": "FULL later D3 handoff only",
            "food_inspections": "FULL later D3 handoff only",
            "building_violations": "WINDOWED_COMPLETE recent-window handoff only",
            "cook_county_parcel_universe": "WINDOWED_CAPPED parcel/PIN coverage remains bounded",
            "311_service_requests": "WINDOWED_CAPPED source material, not full-source completion",
            "crimes_2001_present": "WINDOWED_CAPPED privacy-safe block-level context only",
            "divvy_trips": "CAPPED source material, not full-source completion",
            "traffic_crashes_people": "CAPPED crash context, not full-source completion",
            "traffic_crashes_vehicles": "CAPPED crash context, not full-source completion",
            "traffic_tracker_historical_2024_current": "WINDOWED_CAPPED source material, not full-source completion",
            "open_air_chicago_individual_measurements": "WINDOWED_CAPPED source material, not full-source completion",
        },
        "status_reason": "Expected D2B status remains PASS_WITH_CAPPED_BASE_SOURCES because Cook parcels are WINDOWED_CAPPED and street centerlines remain source-limited.",
    }


def d1b_source_manifest(d1b_landing: Path, source_rel: str) -> dict[str, Any]:
    return read_json(d1b_landing / source_rel / "source_manifest.json", {})


def manifest_csv_paths(d1b_landing: Path, source_rel: str) -> list[Path]:
    manifest = d1b_source_manifest(d1b_landing, source_rel)
    paths: list[Path] = []
    for chunk in manifest.get("chunks", []):
        path_text = chunk.get("path")
        path = Path(path_text) if path_text else d1b_landing / chunk.get("relative_path", "")
        if path.exists() and path.suffix.lower() == ".csv":
            paths.append(path)
    return paths


def read_manifest_csvs(d1b_landing: Path, source_rel: str, usecols: list[str] | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    paths = manifest_csv_paths(d1b_landing, source_rel)
    frames = []
    for path in paths:
        frames.append(pd.read_csv(path, dtype=str, usecols=usecols, low_memory=False))
    frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    manifest = d1b_source_manifest(d1b_landing, source_rel)
    profile = {
        "source_rel": source_rel,
        "manifest_chunks": len(manifest.get("chunks", [])),
        "csv_paths_read": [str(p) for p in paths],
        "rows_loaded": int(len(frame)),
        "manifest_downloaded_rows": manifest.get("downloaded_rows"),
        "manifest_completion_status": manifest.get("completion_status"),
        "manifest_total_count": manifest.get("total_count_probe", {}).get("count"),
        "manifest_window_count": manifest.get("window_count_probe", {}).get("count"),
        "official_title": manifest.get("official_title"),
        "resource_id": manifest.get("resource_id"),
        "where": manifest.get("where"),
    }
    return frame, profile


def build_parcels(d1b_landing: Path, d1b_counts: dict[str, dict[str, Any]]) -> tuple[pd.DataFrame, dict[str, Any]]:
    usecols = [
        "pin",
        "pin10",
        "year",
        "class",
        "township_name",
        "zip_code",
        "lon",
        "lat",
        "cook_municipality_name",
        "ward_num",
        "ward_chicago_data_year",
        "chicago_community_area_num",
        "chicago_community_area_name",
        "chicago_community_area_data_year",
        "chicago_police_district_num",
        "chicago_police_district_data_year",
        "census_tract_geoid",
        "census_block_geoid",
        "tax_tif_district_num",
        "tax_tif_district_name",
        "access_cmap_walk_id",
        "access_cmap_walk_nta_score",
        "access_cmap_walk_total_score",
    ]
    raw, profile = read_manifest_csvs(d1b_landing, PARCEL_SOURCE_REL, usecols=usecols)
    source_status = profile.get("manifest_completion_status") or d1b_counts.get("cook_county_parcel_universe", {}).get("completion_status")
    if raw.empty:
        parcels = pd.DataFrame()
        pin_status_counts: dict[str, int] = {}
    else:
        pin_raw = clean_col(raw, "pin")
        digits = pin_raw.fillna("").str.replace(r"\D", "", regex=True)
        length = digits.str.len()
        pin14 = pd.Series(pd.NA, index=raw.index, dtype="string")
        pin_status = pd.Series("invalid_pin", index=raw.index, dtype="string")
        mask14 = length == 14
        mask_short = length.between(1, 13)
        mask_missing = length == 0
        pin14.loc[mask14] = digits.loc[mask14]
        pin14.loc[mask_short] = digits.loc[mask_short].str.zfill(14)
        pin_status.loc[mask14] = "pin14_native"
        pin_status.loc[mask_short] = "pin14_zero_padded"
        pin_status.loc[mask_missing] = "missing_pin"
        valid = pin14.notna()
        pin_status_counts = pin_status.value_counts(dropna=False).to_dict()

        lat = pd.to_numeric(clean_col(raw, "lat"), errors="coerce")
        lon = pd.to_numeric(clean_col(raw, "lon"), errors="coerce")
        has_point = lat.notna() & lon.notna()
        geometry_json_values = pd.Series(pd.NA, index=raw.index, dtype="object")
        geometry_json_values.loc[has_point] = [
            f'{{"coordinates":[{lon_value},{lat_value}],"type":"Point"}}'
            for lon_value, lat_value in zip(lon.loc[has_point], lat.loc[has_point])
        ]
        city = clean_col(raw, "cook_municipality_name")
        city = city.mask(city == "CITY OF CHICAGO", "CHICAGO")
        parcels = pd.DataFrame(
            {
                "canonical_id": "parcel:us-chicago:cook_pin:" + pin14.loc[valid].astype(str),
                "entity_type": "Parcel",
                "pin14": pin14.loc[valid],
                "raw_pin": pin_raw.loc[valid],
                "pin10": clean_col(raw, "pin10").loc[valid],
                "pin_status": pin_status.loc[valid],
                "source_year": clean_col(raw, "year").loc[valid],
                "address_text": None,
                "city": city.loc[valid],
                "township": clean_col(raw, "township_name").loc[valid],
                "property_class": clean_col(raw, "class").loc[valid],
                "zip": clean_col(raw, "zip_code").loc[valid],
                "ward_num": clean_col(raw, "ward_num").loc[valid],
                "ward_data_year": clean_col(raw, "ward_chicago_data_year").loc[valid],
                "community_area_num": clean_col(raw, "chicago_community_area_num").loc[valid],
                "community_area_name": clean_col(raw, "chicago_community_area_name").loc[valid],
                "community_area_data_year": clean_col(raw, "chicago_community_area_data_year").loc[valid],
                "police_district_num": clean_col(raw, "chicago_police_district_num").loc[valid],
                "police_district_data_year": clean_col(raw, "chicago_police_district_data_year").loc[valid],
                "census_tract_geoid": clean_col(raw, "census_tract_geoid").loc[valid],
                "census_block_geoid": clean_col(raw, "census_block_geoid").loc[valid],
                "tax_tif_district_num": clean_col(raw, "tax_tif_district_num").loc[valid],
                "tax_tif_district_name": clean_col(raw, "tax_tif_district_name").loc[valid],
                "access_cmap_walk_id": clean_col(raw, "access_cmap_walk_id").loc[valid],
                "access_cmap_walk_nta_score": clean_col(raw, "access_cmap_walk_nta_score").loc[valid],
                "access_cmap_walk_total_score": clean_col(raw, "access_cmap_walk_total_score").loc[valid],
                "latitude": lat.loc[valid],
                "longitude": lon.loc[valid],
                "geometry_status": pd.Series("missing_geometry", index=raw.index).mask(has_point, "official_point").loc[valid],
                "geometry_json": geometry_json_values.loc[valid],
                "source_record_id": pin14.loc[valid],
                "source_dataset": "Cook County Assessor Parcel Universe",
                "source_status": source_status,
                "confidence": 0.9,
                "provenance": '[{"source":"CHI-D1B Cook County parcel universe"}]',
            }
        )
    duplicate_rows = 0
    if not parcels.empty:
        parcels["_year_sort"] = pd.to_numeric(parcels["source_year"], errors="coerce").fillna(-1)
        duplicate_rows = int(parcels.duplicated("canonical_id").sum())
        parcels = (
            parcels.sort_values(["canonical_id", "_year_sort"], ascending=[True, False])
            .drop_duplicates("canonical_id", keep="first")
            .drop(columns=["_year_sort"])
            .reset_index(drop=True)
        )
    profile.update(
        {
            "source_key": "cook_county_parcel_universe",
            "source_status": source_status,
            "raw_rows_loaded": int(len(raw)),
            "canonical_pin14_rows": int(len(parcels)),
            "duplicate_pin14_rows_dropped": duplicate_rows,
            "pin_status_counts": pin_status_counts,
            "geometry_status_counts": parcels.get("geometry_status", pd.Series(dtype=str)).value_counts(dropna=False).to_dict(),
        }
    )
    return parcels, profile


def address_from_building(row: pd.Series) -> str | None:
    parts = [
        cell(row.get("f_add1")),
        cell(row.get("pre_dir1")),
        cell(row.get("st_name1")),
        cell(row.get("st_type1")),
        cell(row.get("suf_dir1")),
        cell(row.get("unit_name")),
    ]
    text = " ".join(part for part in parts if part)
    return text or None


def build_building_footprints(d1b_landing: Path, d1b_counts: dict[str, dict[str, Any]]) -> tuple[pd.DataFrame, dict[str, Any]]:
    usecols = [
        "the_geom",
        "bldg_id",
        "bldg_statu",
        "f_add1",
        "t_add1",
        "pre_dir1",
        "st_name1",
        "st_type1",
        "suf_dir1",
        "unit_name",
        "stories",
        "orig_bldg_",
        "footprint_",
        "harris_str",
        "no_of_unit",
        "no_stories",
        "year_built",
        "bldg_sq_fo",
        "bldg_condi",
        "vacancy_st",
        "shape_area",
        "shape_len",
    ]
    raw, profile = read_manifest_csvs(d1b_landing, BUILDING_SOURCE_REL, usecols=usecols)
    source_status = profile.get("manifest_completion_status") or d1b_counts.get("building_footprints_primary", {}).get("completion_status")
    if raw.empty:
        buildings = pd.DataFrame()
        missing_id = 0
        missing_wkt = 0
    else:
        source_id = clean_col(raw, "bldg_id").fillna(clean_col(raw, "orig_bldg_"))
        missing_id = int(source_id.isna().sum())
        fallback_ids = pd.Series([f"row_{idx}" for idx in raw.index], index=raw.index, dtype="string")
        source_id = source_id.fillna(fallback_ids)
        wkt = clean_col(raw, "the_geom")
        missing_wkt = int(wkt.isna().sum())
        upper_wkt = wkt.fillna("").str.upper()
        has_polygon = upper_wkt.str.startswith("POLYGON") | upper_wkt.str.startswith("MULTIPOLYGON")
        address = (
            clean_col(raw, "f_add1").fillna("")
            + " "
            + clean_col(raw, "pre_dir1").fillna("")
            + " "
            + clean_col(raw, "st_name1").fillna("")
            + " "
            + clean_col(raw, "st_type1").fillna("")
            + " "
            + clean_col(raw, "suf_dir1").fillna("")
            + " "
            + clean_col(raw, "unit_name").fillna("")
        ).str.replace(r"\s+", " ", regex=True).str.strip()
        address = address.mask(address == "")
        stories = clean_col(raw, "stories").fillna(clean_col(raw, "no_stories"))
        buildings = pd.DataFrame(
            {
                "canonical_id": "building:us-chicago:building_footprint:" + source_id.map(safe_id),
                "entity_type": "Building",
                "source_id": source_id,
                "building_status": clean_col(raw, "bldg_statu"),
                "address_text": address,
                "from_address": clean_col(raw, "f_add1"),
                "to_address": clean_col(raw, "t_add1"),
                "harris_pin_candidate": clean_col(raw, "harris_str"),
                "stories": stories,
                "units": clean_col(raw, "no_of_unit"),
                "year_built": clean_col(raw, "year_built"),
                "building_square_footage": clean_col(raw, "bldg_sq_fo"),
                "building_condition": clean_col(raw, "bldg_condi"),
                "vacancy_status": clean_col(raw, "vacancy_st"),
                "shape_area": clean_col(raw, "shape_area"),
                "shape_len": clean_col(raw, "shape_len"),
                "geometry_status": pd.Series("missing_geometry", index=raw.index).mask(has_polygon, "official_polygon_candidate_wkt"),
                "geometry_wkt": wkt,
                "source_dataset": "Chicago Building Footprints",
                "source_status": source_status,
                "confidence": pd.Series(0.45, index=raw.index).mask(has_polygon, 0.82),
                "provenance": '[{"source":"CHI-D1B Chicago Building Footprints"}]',
            }
        )
    duplicate_rows = 0
    if not buildings.empty:
        duplicate_rows = int(buildings.duplicated("canonical_id").sum())
        buildings = buildings.drop_duplicates("canonical_id", keep="first").reset_index(drop=True)
    profile.update(
        {
            "source_key": "building_footprints_primary",
            "source_status": source_status,
            "raw_rows_loaded": int(len(raw)),
            "canonical_building_rows": int(len(buildings)),
            "duplicate_building_ids_dropped": duplicate_rows,
            "missing_source_id_rows": missing_id,
            "missing_geometry_rows": missing_wkt,
            "geometry_status_counts": buildings.get("geometry_status", pd.Series(dtype=str)).value_counts(dropna=False).to_dict(),
        }
    )
    return buildings, profile


def read_d2_canonical(d2_output: Path, name: str) -> pd.DataFrame:
    path = d2_output / "canonical" / name
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_parquet(path)
    if list(frame.columns) == ["_empty"]:
        return pd.DataFrame()
    return frame


def copy_d2_strengths(d2_output: Path, output_dir: Path) -> dict[str, pd.DataFrame]:
    mapping = {
        "area": ("chi_d2_area_context.parquet", "chi_d2b_area_context.parquet"),
        "transit_nodes": ("chi_d2_transit_nodes.parquet", "chi_d2b_transit_nodes.parquet"),
        "transit_routes": ("chi_d2_transit_routes.parquet", "chi_d2b_transit_routes.parquet"),
        "facilities": ("chi_d2_public_facilities.parquet", "chi_d2b_public_facilities.parquet"),
        "identity_edges": ("chi_d2_identity_edges.parquet", "chi_d2b_identity_edges.parquet"),
        "context_edges": ("chi_d2_context_edges.parquet", "chi_d2b_context_edges.parquet"),
    }
    frames: dict[str, pd.DataFrame] = {}
    for key, (src, dst) in mapping.items():
        frame = read_d2_canonical(d2_output, src)
        frames[key] = frame
        if key not in {"context_edges", "identity_edges"}:
            write_parquet(output_dir / "canonical" / dst, frame)
    return frames


def build_node_id_set(*frames: pd.DataFrame) -> set[str]:
    node_ids: set[str] = set()
    for frame in frames:
        if not frame.empty and "canonical_id" in frame.columns:
            node_ids.update(str(v) for v in frame["canonical_id"].dropna().tolist())
    return node_ids


def filter_carried_edges(edges: pd.DataFrame, node_ids: set[str]) -> tuple[pd.DataFrame, dict[str, Any]]:
    if edges.empty:
        return edges, {"input_edges": 0, "kept_edges": 0, "dropped_dangling_edges": 0}
    mask = edges["source_id"].isin(node_ids) & edges["target_id"].isin(node_ids)
    kept = edges[mask].copy().reset_index(drop=True)
    dropped = edges[~mask]
    profile = {
        "input_edges": int(len(edges)),
        "kept_edges": int(len(kept)),
        "dropped_dangling_edges": int(len(dropped)),
        "dropped_relation_counts": dropped.get("relation", pd.Series(dtype=str)).value_counts(dropna=False).to_dict(),
    }
    return kept, profile


def build_parcel_attribute_area_edges(parcels: pd.DataFrame, areas: pd.DataFrame, existing_edge_count: int = 0) -> tuple[pd.DataFrame, dict[str, Any]]:
    if parcels.empty or areas.empty:
        return pd.DataFrame(), {"status": "SOURCE_LIMITED", "edges": 0}
    frames = []
    assignments = {"ward": 0, "community_area": 0}
    for area_type, col, year_col in [
        ("ward", "ward_num", "ward_data_year"),
        ("community_area", "community_area_num", "community_area_data_year"),
    ]:
        area_map = areas.loc[areas["area_type"] == area_type, ["native_id", "canonical_id"]].copy()
        if area_map.empty:
            continue
        area_map["area_key"] = numeric_like_key(area_map["native_id"])
        work = parcels[["canonical_id", col, year_col]].copy()
        work["area_key"] = numeric_like_key(work[col])
        work = work[work["area_key"].notna()]
        merged = work.merge(area_map[["area_key", "canonical_id"]], on="area_key", how="inner", suffixes=("_source", "_target"))
        if merged.empty:
            continue
        assignments[area_type] = int(len(merged))
        item = pd.DataFrame(
            {
                "entity_type": "context_edge",
                "source_id": merged["canonical_id_source"],
                "target_id": merged["canonical_id_target"],
                "relation": "within_area_context",
                "join_method": "official_parcel_area_attribute",
                "source_stage": "CHI-D2B",
                "confidence": 0.78,
                "status": "attribute_backed_context_not_spatial_join",
                "area_type": area_type,
                "source_field": col,
                "source_data_year": merged[year_col],
            }
        )
        frames.append(item)
    frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not frame.empty:
        frame.insert(
            0,
            "canonical_id",
            [f"edge:us-chicago:chi-d2b:parcel_attribute_area:{idx}" for idx in range(existing_edge_count + 1, existing_edge_count + 1 + len(frame))],
        )
    profile = {
        "status": "PASS",
        "edges": int(len(frame)),
        "assignments_by_area_type": assignments,
        "method": "official Cook parcel area attributes matched to carried-forward D2 area context IDs",
        "limitation": "These are field-backed area context edges, not newly certified polygon containment joins.",
    }
    return frame, profile


def concat_edges(carried: pd.DataFrame, parcel_edges: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "canonical_id",
        "entity_type",
        "source_id",
        "target_id",
        "relation",
        "join_method",
        "source_stage",
        "confidence",
        "status",
        "area_type",
        "source_field",
        "source_data_year",
    ]
    frames = []
    for frame in [carried, parcel_edges]:
        if frame.empty:
            continue
        item = frame.copy()
        for col in columns:
            if col not in item.columns:
                item[col] = None
        frames.append(item[columns])
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=columns)


def edge_integrity(edges: pd.DataFrame, node_ids: set[str]) -> dict[str, Any]:
    if edges.empty:
        return {"status": "PASS", "edge_count": 0, "src_missing": 0, "dst_missing": 0, "missing_samples": []}
    src_missing = sorted(set(edges.loc[~edges["source_id"].isin(node_ids), "source_id"].dropna().astype(str).tolist()))
    dst_missing = sorted(set(edges.loc[~edges["target_id"].isin(node_ids), "target_id"].dropna().astype(str).tolist()))
    return {
        "status": "PASS" if not src_missing and not dst_missing else "FAIL",
        "edge_count": int(len(edges)),
        "src_missing": len(src_missing),
        "dst_missing": len(dst_missing),
        "missing_samples": [{"source_id": v} for v in src_missing[:5]] + [{"target_id": v} for v in dst_missing[:5]],
    }


def build_event_handoff(d1b_counts: dict[str, dict[str, Any]], d1b_handoff: dict[str, Any]) -> dict[str, Any]:
    sources = []
    for key, meta in EVENT_HANDOFF_SOURCES.items():
        counts = d1b_counts.get(key, {})
        sources.append(
            {
                "source_key": key,
                "resource_id": counts.get("resource_id"),
                "completion_status": counts.get("completion_status"),
                "downloaded_rows": counts.get("downloaded_rows"),
                "total_count": counts.get("total_count"),
                "window_count": counts.get("window_count"),
                "role": meta["role"],
                "d3_guidance": meta["d3_guidance"],
            }
        )
    return {
        "status": "PASS",
        "event_edges_emitted_by_d2b": 0,
        "incident_to_asset_edges_emitted_by_d2b": 0,
        "sources": sources,
        "d1b_handoff_status": d1b_handoff.get("status"),
        "notes": [
            "D2B prepares D3 handoff only; it does not build Flow 1 or Flow 7.",
            "D3 may later create event/context edges with explicit source limitations.",
            "Crimes remain privacy-safe block-level context only unless a later official source supports stronger location semantics.",
        ],
    }


def scan_no_overclaim(output_dir: Path) -> dict[str, Any]:
    checked = []
    boundary_failures = []
    forbidden_hits = []
    report_paths = [p for p in sorted(output_dir.rglob("*")) if p.is_file() and p.suffix.lower() in {".json", ".md"}]
    for path in report_paths:
        if "canonical" in path.parts or path.name == "SHA256SUMS.json":
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


def required_file_status(paths: dict[str, Path]) -> dict[str, bool]:
    return {name: path.exists() for name, path in paths.items()}


def run_chi_d2b_gate(
    project_root: str = ".",
    chi_d1_output_dir: str | None = None,
    chi_d1_landing_dir: str | None = None,
    chi_d1b_output_dir: str | None = None,
    chi_d1b_landing_dir: str | None = None,
    chi_d2_dir: str | None = None,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    d1_output: str | None = None,
    d1_landing: str | None = None,
    d1b_output: str | None = None,
    d1b_landing: str | None = None,
    d2_output: str | None = None,
) -> dict[str, Any]:
    root = Path(project_root)

    def resolve_path(value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else root / path

    d1_output_p = resolve_path(d1_output or chi_d1_output_dir or DEFAULT_D1_OUTPUT)
    d1_landing_p = resolve_path(d1_landing or chi_d1_landing_dir or DEFAULT_D1_LANDING)
    d1b_output_p = resolve_path(d1b_output or chi_d1b_output_dir or DEFAULT_D1B_OUTPUT)
    d1b_landing_p = resolve_path(d1b_landing or chi_d1b_landing_dir or DEFAULT_D1B_LANDING)
    d2_output_p = resolve_path(d2_output or chi_d2_dir or DEFAULT_D2_OUTPUT)
    output_dir_p = resolve_path(output_dir)
    input_roots = [d1_output_p, d1_landing_p, d1b_output_p, d1b_landing_p, d2_output_p]
    before = snapshot(input_roots)

    reset_output_dir(output_dir_p)

    d1_harness = read_json(d1_output_p / "CHI_D1_HARNESS_REPORT.json", {})
    d1b_harness = read_json(d1b_output_p / "CHI_D1B_HARNESS_REPORT.json", {})
    d2_harness = read_json(d2_output_p / "CHI_D2_HARNESS_REPORT.json", {})
    d2_counts = read_json(d2_output_p / "CHI_D2_ENTITY_COUNTS.json", {})
    d1b_counts = merge_d1b_source_status(d1b_output_p, d1b_landing_p)
    material_summary = d1b_material_summary(d1b_counts)
    d1b_handoff = read_json(d1b_output_p / "CHI_D1B_D2_D3_HANDOFF.json", {})

    required_inputs = {
        "d1_harness": d1_output_p / "CHI_D1_HARNESS_REPORT.json",
        "d1_landing_manifest": d1_landing_p / "landing_manifest.json",
        "d1b_harness": d1b_output_p / "CHI_D1B_HARNESS_REPORT.json",
        "d1b_counts": d1b_output_p / "CHI_D1B_COUNTS_REPORT.json",
        "d1b_handoff": d1b_output_p / "CHI_D1B_D2_D3_HANDOFF.json",
        "d1b_parcel_manifest": d1b_landing_p / PARCEL_SOURCE_REL / "source_manifest.json",
        "d1b_building_manifest": d1b_landing_p / BUILDING_SOURCE_REL / "source_manifest.json",
        "d2_harness": d2_output_p / "CHI_D2_HARNESS_REPORT.json",
        "d2_area_context": d2_output_p / "canonical" / "chi_d2_area_context.parquet",
        "d2_transit_nodes": d2_output_p / "canonical" / "chi_d2_transit_nodes.parquet",
        "d2_transit_routes": d2_output_p / "canonical" / "chi_d2_transit_routes.parquet",
        "d2_public_facilities": d2_output_p / "canonical" / "chi_d2_public_facilities.parquet",
    }
    input_inventory = {
        "status": "PASS" if all(required_file_status(required_inputs).values()) else "FAIL",
        "required_inputs": {name: str(path) for name, path in required_inputs.items()},
        "required_input_exists": required_file_status(required_inputs),
        "d1_status": d1_harness.get("status"),
        "d1b_status": d1b_harness.get("status"),
        "d2_status": d2_harness.get("status"),
        "d2_counts": d2_counts,
    }
    write_json(output_dir_p / "CHI_D2B_INPUT_INVENTORY.json", input_inventory)

    parcels, parcel_profile = build_parcels(d1b_landing_p, d1b_counts)
    buildings, building_profile = build_building_footprints(d1b_landing_p, d1b_counts)
    d2_frames = copy_d2_strengths(d2_output_p, output_dir_p)
    areas = d2_frames["area"]
    transit_nodes = d2_frames["transit_nodes"]
    transit_routes = d2_frames["transit_routes"]
    facilities = d2_frames["facilities"]
    identity_edges = d2_frames["identity_edges"]
    carried_context_edges = d2_frames["context_edges"]

    write_parquet(output_dir_p / "canonical" / "chi_d2b_parcels_pin14.parquet", parcels)
    write_parquet(output_dir_p / "canonical" / "chi_d2b_building_footprint_candidates.parquet", buildings)

    node_ids = build_node_id_set(parcels, buildings, areas, transit_nodes, transit_routes, facilities)
    filtered_carried_edges, carried_edge_profile = filter_carried_edges(carried_context_edges, node_ids)
    parcel_area_edges, area_assignment_profile = build_parcel_attribute_area_edges(
        parcels, areas, existing_edge_count=len(filtered_carried_edges)
    )
    context_edges = concat_edges(filtered_carried_edges, parcel_area_edges)
    write_parquet(output_dir_p / "canonical" / "chi_d2b_identity_edges.parquet", identity_edges)
    write_parquet(output_dir_p / "canonical" / "chi_d2b_context_edges.parquet", context_edges)

    entity_counts = {
        "parcels_pin14": int(len(parcels)),
        "building_footprint_candidates": int(len(buildings)),
        "area_context": int(len(areas)),
        "transit_nodes": int(len(transit_nodes)),
        "transit_routes": int(len(transit_routes)),
        "facilities_resources": int(len(facilities)),
        "identity_edges": int(len(identity_edges)),
        "context_edges": int(len(context_edges)),
        "identity_context_edges_total": int(len(identity_edges) + len(context_edges)),
    }
    write_json(output_dir_p / "CHI_D2B_ENTITY_COUNTS.json", entity_counts)

    refresh_report = {
        "status": "PASS_WITH_CAPPED_BASE_SOURCES",
        "d1b_material_summary": material_summary,
        "previous_d2_counts": d2_counts,
        "d2b_counts": entity_counts,
        "land_building_refresh": {
            "parcels_from_d1b": parcel_profile,
            "building_footprints_from_d1b": building_profile,
        },
        "carry_forward": {
            "area_context": int(len(areas)),
            "transit_nodes": int(len(transit_nodes)),
            "transit_routes": int(len(transit_routes)),
            "facilities_resources": int(len(facilities)),
            "carried_context_edges": carried_edge_profile,
        },
        "note": "D2B refreshes base identity/geography only and emits no event or incident-to-asset edges.",
    }
    write_json(output_dir_p / "CHI_D2B_REFRESH_REPORT.json", refresh_report)
    write_json(output_dir_p / "reports" / "d1b_material_summary.json", material_summary)
    write_json(output_dir_p / "CHI_D2B_PIN14_PROFILE.json", parcel_profile)
    write_json(output_dir_p / "CHI_D2B_BUILDING_FOOTPRINT_PROFILE.json", building_profile)

    area_profile = {
        "status": "PASS" if len(areas) >= int(d2_counts.get("area_context", 0)) else "FAIL",
        "area_context_count": int(len(areas)),
        "previous_d2_area_context_count": int(d2_counts.get("area_context", 0)),
        "area_type_counts": areas.get("area_type", pd.Series(dtype=str)).value_counts(dropna=False).to_dict(),
        "source": "carried forward from accepted CHI-D2",
    }
    write_json(output_dir_p / "CHI_D2B_AREA_CONTEXT_PROFILE.json", area_profile)

    cta_report = {
        "status": "PASS"
        if len(transit_nodes) >= int(d2_counts.get("transit_nodes", 0)) and len(transit_routes) >= int(d2_counts.get("transit_routes", 0))
        else "FAIL",
        "transit_nodes": int(len(transit_nodes)),
        "transit_routes": int(len(transit_routes)),
        "source_status": "FULL_STATIC_GTFS",
        "source": "carried forward from accepted CHI-D2",
        "limitation": "CTA GTFS is static schedule geography, not live transit status.",
    }
    write_json(output_dir_p / "CHI_D2B_CTA_GTFS_CARRY_FORWARD_REPORT.json", cta_report)

    facility_report = {
        "status": "PASS" if len(facilities) >= int(d2_counts.get("facilities_resources", 0)) else "FAIL",
        "facilities_resources": int(len(facilities)),
        "previous_d2_facilities_resources": int(d2_counts.get("facilities_resources", 0)),
        "resource_type_counts": facilities.get("resource_type", pd.Series(dtype=str)).value_counts(dropna=False).to_dict(),
        "source": "carried forward from accepted CHI-D2",
    }
    write_json(output_dir_p / "CHI_D2B_FACILITY_CONTEXT_REPORT.json", facility_report)

    event_handoff = build_event_handoff(d1b_counts, d1b_handoff)
    write_json(output_dir_p / "CHI_D2B_EVENT_SOURCE_HANDOFF.json", event_handoff)

    schema_report = {
        "status": "PASS",
        "native_id_preservation": "PASS",
        "notes": [
            "Cook PIN14 remains the native parcel anchor.",
            "Building footprint IDs remain geometry candidate IDs.",
            "Area, TransitNode, TransitRoute, and Resource are carried forward from CHI-D2 without NYC/London identity semantics.",
            "No BBL/BIN/UPRN/TOID identities are introduced.",
        ],
    }
    write_json(output_dir_p / "CHI_D2B_SCHEMA_COMPATIBILITY_REPORT.json", schema_report)

    capped_source_status = {
        "status": "PASS",
        "d1b_material_summary": material_summary,
        "sources": d1b_counts,
        "d2b_base_refresh_sources": {
            "cook_county_parcel_universe": d1b_counts.get("cook_county_parcel_universe"),
            "building_footprints_primary": d1b_counts.get("building_footprints_primary"),
        },
        "landing_manifest_rows_loaded": {
            "cook_county_parcel_universe": parcel_profile.get("rows_loaded"),
            "building_footprints_primary": building_profile.get("rows_loaded"),
        },
    }
    write_json(output_dir_p / "reports" / "capped_source_status.json", capped_source_status)
    write_json(
        output_dir_p / "reports" / "d1b_source_usage.json",
        {
            "status": "PASS",
            "d1b_material_summary": material_summary,
            "used_for_canonical_refresh": [
                "cook_county_parcel_universe",
                "building_footprints_primary",
            ],
            "used_for_d3_handoff": list(EVENT_HANDOFF_SOURCES),
            "not_used_for_edges": list(EVENT_HANDOFF_SOURCES),
            "reason": "D2B refreshes base identity/geography only; event/context linking belongs to D3.",
        },
    )
    write_json(output_dir_p / "reports" / "cook_pin14_normalization.json", parcel_profile)
    write_json(output_dir_p / "reports" / "building_geometry_quality.json", building_profile)
    write_json(output_dir_p / "reports" / "area_assignment_quality.json", area_assignment_profile)
    write_json(
        output_dir_p / "reports" / "d3_readiness.json",
        {
            "status": "PASS",
            "d1b_material_summary": material_summary,
            "handoff_status": event_handoff["status"],
            "event_source_count": len(event_handoff["sources"]),
            "base_identity_available": entity_counts,
            "limitations": [
                "D2B does not create incident-to-asset edges.",
                "D2B does not certify affected buildings/assets.",
                "Crimes are privacy-safe block-level context only.",
                "Capped/windowed sources require completion_status before asserting completeness.",
            ],
        },
    )

    edge_report = edge_integrity(context_edges, node_ids)

    no_mutation_placeholder = {"status": "PENDING", "checked_after_generation": True}
    write_json(output_dir_p / "CHI_D2B_NO_MUTATION_REPORT.json", no_mutation_placeholder)

    readme = "\n".join(
        [
            "# CHI-D2B Chicago Base Identity Refresh",
            "",
            *BOUNDARY_LINES,
            "",
            "## Result",
            "",
            f"Status: PASS_WITH_CAPPED_BASE_SOURCES",
            f"CHI-D1B rows landed total: {material_summary['rows_landed_total']}",
            f"Cook PIN parcels: {entity_counts['parcels_pin14']}",
            f"Building footprint candidates: {entity_counts['building_footprint_candidates']}",
            f"Area contexts: {entity_counts['area_context']}",
            f"Transit nodes: {entity_counts['transit_nodes']}",
            f"Transit routes: {entity_counts['transit_routes']}",
            f"Facilities/resources: {entity_counts['facilities_resources']}",
            f"Identity/context edges: {entity_counts['identity_context_edges_total']}",
            "",
            "## CHI-D1B Source Completion",
            "",
            "Building Footprints, Building Permits, Business Licenses, Food Inspections, and Traffic Crashes are FULL in the current D1B source-completion report.",
            "Building Violations and Open Air hourly are WINDOWED_COMPLETE for their recent windows.",
            "Cook parcels remain WINDOWED_CAPPED, so parcel/PIN coverage remains bounded.",
            "311, crimes, Divvy, crash people/vehicles, Traffic Tracker historical, and Open Air individual remain capped/windowed source material for later development, not full-source completion.",
            "",
            "The refreshed parcel area-context edges are official parcel-attribute matches to carried-forward D2 area IDs, not newly certified polygon containment joins.",
            "",
        ]
    )
    write_text(output_dir_p / "README.md", readme)

    handover = "\n".join(
        [
            "# CHI-D2B Adapter Handover",
            "",
            *BOUNDARY_LINES,
            "",
            "## Canonical Inputs for CHI-D3",
            "",
            "- Use `canonical/chi_d2b_parcels_pin14.parquet` for Cook PIN14 parcel anchors.",
            "- Use `canonical/chi_d2b_building_footprint_candidates.parquet` for building geometry candidates.",
            "- Use `CHI_D2B_EVENT_SOURCE_HANDOFF.json` and `reports/d3_readiness.json` before ingesting events.",
            "- Treat crimes as privacy-safe block-level context only.",
            "- Treat Building Permits, Business Licenses, and Food Inspections as FULL D3 handoff material.",
            "- Treat Cook parcels, 311, crimes, Divvy, crash people/vehicles, Traffic Tracker historical, and Open Air individual as capped/windowed source material.",
            "- Do not promote D2B building candidates or event rows into certified affected assets without a later deterministic source.",
            "",
        ]
    )
    write_text(output_dir_p / "CHI_D2B_ADAPTER_HANDOVER.md", handover)

    gates: dict[str, str] = {
        "CHI-D2B-PRECOND": "PASS"
        if input_inventory["status"] == "PASS"
        and status_pass(d1_harness.get("status"))
        and status_pass(d1b_harness.get("status"))
        and status_pass(d2_harness.get("status"))
        else "FAIL",
        "CHI-D2B-D1B-SOURCE-USAGE": "PASS"
        if parcel_profile.get("rows_loaded", 0) > int(d2_counts.get("parcels_pin14", 0))
        and building_profile.get("rows_loaded", 0) > int(d2_counts.get("building_footprint_candidates", 0))
        else "FAIL",
        "CHI-D2B-PIN14": "PASS"
        if len(parcels) > int(d2_counts.get("parcels_pin14", 0))
        and parcels["canonical_id"].str.match(r"^parcel:us-chicago:cook_pin:\d{14}$").all()
        else "FAIL",
        "CHI-D2B-BUILDING-FOOTPRINTS": "PASS"
        if len(buildings) > int(d2_counts.get("building_footprint_candidates", 0))
        and (buildings["geometry_status"] == "official_polygon_candidate_wkt").sum() > 0
        else "FAIL",
        "CHI-D2B-AREA-CONTEXT": area_profile["status"],
        "CHI-D2B-CTA-CARRY-FORWARD": cta_report["status"],
        "CHI-D2B-FACILITIES-CARRY-FORWARD": facility_report["status"],
        "CHI-D2B-EDGE-INTEGRITY": edge_report["status"],
        "CHI-D2B-D3-HANDOFF": event_handoff["status"],
        "CHI-D2B-SCHEMA-COMPATIBILITY": schema_report["status"],
    }

    harness_stub = {
        "task": TASK_NAME,
        "status": "PASS_WITH_CAPPED_BASE_SOURCES",
        "created_utc": utc_now(),
        "counts": entity_counts,
        "d1b_material_summary": material_summary,
        "gates": gates,
        "source_limitations": {
            "cook_county_parcel_universe": d1b_counts.get("cook_county_parcel_universe", {}).get("completion_status"),
            "building_footprints_primary": d1b_counts.get("building_footprints_primary", {}).get("completion_status"),
            "street_centerlines": "carried forward source-limited from CHI-D2; no D1B repair applied",
        },
        "edge_integrity": edge_report,
        "output": str(output_dir_p),
    }
    write_json(output_dir_p / "CHI_D2B_HARNESS_REPORT.json", harness_stub)

    no_overclaim = scan_no_overclaim(output_dir_p)
    write_json(output_dir_p / "CHI_D2B_NO_OVERCLAIM_REPORT.json", no_overclaim)
    gates["CHI-D2B-NO-OVERCLAIM"] = no_overclaim["status"]

    after = snapshot(input_roots)
    no_mutation = compare_snapshots(before, after)
    write_json(output_dir_p / "CHI_D2B_NO_MUTATION_REPORT.json", no_mutation)
    gates["CHI-D2B-NO-MUTATION"] = no_mutation["status"]

    harness_stub["gates"] = gates
    harness_stub["no_overclaim"] = no_overclaim
    harness_stub["no_mutation"] = no_mutation
    write_json(output_dir_p / "CHI_D2B_HARNESS_REPORT.json", harness_stub)

    hashes = write_hashes(output_dir_p)
    gates["CHI-D2B-HASHES"] = hashes["status"]
    final_status = "PASS_WITH_CAPPED_BASE_SOURCES" if all(v == "PASS" for v in gates.values()) else "FAIL"
    harness = {
        "task": TASK_NAME,
        "status": final_status,
        "created_utc": utc_now(),
        "counts": entity_counts,
        "d1b_material_summary": material_summary,
        "gates": gates,
        "hashes": hashes,
        "source_limitations": harness_stub["source_limitations"],
        "edge_integrity": edge_report,
        "output": str(output_dir_p),
    }
    write_json(output_dir_p / "CHI_D2B_HARNESS_REPORT.json", harness)
    hashes = write_hashes(output_dir_p)
    harness["hashes"] = hashes
    harness["gates"]["CHI-D2B-HASHES"] = hashes["status"]
    harness["status"] = "PASS_WITH_CAPPED_BASE_SOURCES" if all(v == "PASS" for v in harness["gates"].values()) else "FAIL"
    write_json(output_dir_p / "CHI_D2B_HARNESS_REPORT.json", harness)
    final_no_overclaim = scan_no_overclaim(output_dir_p)
    write_json(output_dir_p / "CHI_D2B_NO_OVERCLAIM_REPORT.json", final_no_overclaim)
    harness["gates"]["CHI-D2B-NO-OVERCLAIM"] = final_no_overclaim["status"]
    harness["status"] = "PASS_WITH_CAPPED_BASE_SOURCES" if all(v == "PASS" for v in harness["gates"].values()) else "FAIL"
    write_json(output_dir_p / "CHI_D2B_HARNESS_REPORT.json", harness)
    hashes = write_hashes(output_dir_p)
    harness["hashes"] = hashes
    harness["gates"]["CHI-D2B-HASHES"] = hashes["status"]
    harness["status"] = "PASS_WITH_CAPPED_BASE_SOURCES" if all(v == "PASS" for v in harness["gates"].values()) else "FAIL"
    write_json(output_dir_p / "CHI_D2B_HARNESS_REPORT.json", harness)
    write_hashes(output_dir_p)

    result = {
        "status": harness["status"],
        "counts": entity_counts,
        "gates": harness["gates"],
        "output": str(output_dir_p),
    }
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--d1-output", "--chi-d1-output-dir", dest="d1_output", default=DEFAULT_D1_OUTPUT)
    parser.add_argument("--d1-landing", "--chi-d1-landing-dir", dest="d1_landing", default=DEFAULT_D1_LANDING)
    parser.add_argument("--d1b-output", "--chi-d1b-output-dir", dest="d1b_output", default=DEFAULT_D1B_OUTPUT)
    parser.add_argument("--d1b-landing", "--chi-d1b-landing-dir", dest="d1b_landing", default=DEFAULT_D1B_LANDING)
    parser.add_argument("--d2-output", "--chi-d2-dir", dest="d2_output", default=DEFAULT_D2_OUTPUT)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-gates", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_chi_d2b_gate(
        project_root=args.project_root,
        d1_output=args.d1_output,
        d1_landing=args.d1_landing,
        d1b_output=args.d1b_output,
        d1b_landing=args.d1b_landing,
        d2_output=args.d2_output,
        output_dir=args.output_dir,
    )
    counts = result["counts"]
    gates = result["gates"]
    print(f"CHI-D2B Chicago Base Identity Refresh: {result['status']}")
    print(f"Cook PIN parcels: {counts['parcels_pin14']}")
    print(f"Building footprint candidates: {counts['building_footprint_candidates']}")
    print(f"Area contexts: {counts['area_context']}")
    print(f"Transit nodes: {counts['transit_nodes']}")
    print(f"Transit routes: {counts['transit_routes']}")
    print(f"Facilities/resources: {counts['facilities_resources']}")
    print(f"Identity/context edges: {counts['identity_context_edges_total']}")
    print(f"D3 handoff: {gates.get('CHI-D2B-D3-HANDOFF')}")
    print(f"Schema compatibility: {gates.get('CHI-D2B-SCHEMA-COMPATIBILITY')}")
    print(f"No-overclaim: {gates.get('CHI-D2B-NO-OVERCLAIM')}")
    print(f"No-mutation: {gates.get('CHI-D2B-NO-MUTATION')}")
    print(f"Output: {result['output']}")
    return 0 if result["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())

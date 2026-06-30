"""
NYC harvest prep v0.2.

Converts the local NYC 5M-scale harvest chunks to string-safe Parquet,
dedupes by conservative source keys, and builds DOB discovery staging tables.
This task deliberately does not mutate canonical A4/A5 graph artifacts.
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

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DEFAULT_HARVEST_ROOT = ROOT / "citybrain_data_harvest_pack" / "citybrain_data_harvest"
DEFAULT_RAW_NYC = DEFAULT_HARVEST_ROOT / "data" / "raw" / "nyc"
DEFAULT_GEOM_NYC = DEFAULT_HARVEST_ROOT / "data" / "processed" / "nyc"
DEFAULT_PROCESSED_ROOT = ROOT / "data" / "processed" / "nyc" / "harvest_v0_2"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "nyc_harvest_prep_v0_2"

BOUNDARY_STATEMENT = (
    "Counts are based on the current local NYC harvested dataset. Datasets may be full or capped depending on the "
    "local harvest status. The prep report records row counts, caps, and source chunks used. Discovery counts are "
    "not claims about complete NYC history unless the dataset is marked full in the inventory."
)

DATASET_NAMES = {
    "nyc__dob_now_build_job_application_filings": "DOB NOW Build Job Application Filings",
    "nyc__dob_permit_issuance": "DOB Permit Issuance",
    "nyc__dob_complaints_received": "DOB Complaints Received",
    "nyc__dot_traffic_speeds": "DOT Traffic Speeds",
    "nyc__traffic_volume_counts": "Traffic Volume Counts",
    "nyc__motor_vehicle_collisions_-_crashes": "Motor Vehicle Collisions - Crashes",
    "nyc__ems_incident_dispatch_data": "EMS Incident Dispatch Data",
    "nyc__fire_incident_dispatch_data": "Fire Incident Dispatch Data",
    "nyc__building_energy_and_water_disclosure_ll84": "Building Energy and Water Disclosure LL84",
    "nyc__nyc_permitted_event_information": "NYC Permitted Event Information",
    "nyc__restaurant_inspection_results": "Restaurant Inspection Results",
}

DATASET_ID_TO_KEY = {
    "w9ak-ipjd": "nyc__dob_now_build_job_application_filings",
    "ipu4-2q9a": "nyc__dob_permit_issuance",
    "eabe-havv": "nyc__dob_complaints_received",
    "i4gi-tjb9": "nyc__dot_traffic_speeds",
    "btm5-ppia": "nyc__traffic_volume_counts",
    "h9gi-nx95": "nyc__motor_vehicle_collisions_-_crashes",
    "76xm-jjuj": "nyc__ems_incident_dispatch_data",
    "8m42-w767": "nyc__fire_incident_dispatch_data",
    "5zyy-y8am": "nyc__building_energy_and_water_disclosure_ll84",
    "tvpp-9vvx": "nyc__nyc_permitted_event_information",
    "43nn-pn8j": "nyc__restaurant_inspection_results",
}

DEDUPE_KEYS = {
    "nyc__dob_now_build_job_application_filings": ["job_filing_number"],
    "nyc__dob_permit_issuance": ["job__", "permit_sequence__", "permit_type", "filing_date", "issuance_date", "permit_si_no"],
    "nyc__dob_complaints_received": ["complaint_number"],
    "nyc__dot_traffic_speeds": ["id"],
    "nyc__traffic_volume_counts": ["id"],
    "nyc__motor_vehicle_collisions_-_crashes": ["collision_id"],
    "nyc__ems_incident_dispatch_data": ["incident_id"],
    "nyc__fire_incident_dispatch_data": ["starfire_incident_id", "incident_datetime"],
    "nyc__building_energy_and_water_disclosure_ll84": ["property_id", "report_year"],
    "nyc__nyc_permitted_event_information": ["event_id"],
    "nyc__restaurant_inspection_results": ["camis", "inspection_date", "action", "violation_code"],
}

BOROUGH_TO_CODE = {
    "MANHATTAN": "1",
    "MN": "1",
    "NEW YORK": "1",
    "BRONX": "2",
    "BX": "2",
    "BROOKLYN": "3",
    "BK": "3",
    "KINGS": "3",
    "QUEENS": "4",
    "QN": "4",
    "STATEN ISLAND": "5",
    "SI": "5",
    "RICHMOND": "5",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def safe_clean_dir(path: Path) -> None:
    path = path.resolve()
    root = ROOT.resolve()
    if root not in path.parents and path != root:
        raise ValueError(f"Refusing to clean path outside workspace: {path}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def csv_row_count(path: Path) -> int:
    with path.open("rb") as handle:
        line_count = sum(1 for _ in handle)
    return max(0, line_count - 1)


def chunk_offset(path: Path) -> int:
    match = re.search(r"__offset_(\d+)\.csv$", path.name)
    return int(match.group(1)) if match else -1


def dataset_key_from_dir(dataset_dir: Path) -> str:
    match = re.search(r"__([a-z0-9]{4}-[a-z0-9]{4})$", dataset_dir.name)
    if match and match.group(1) in DATASET_ID_TO_KEY:
        return DATASET_ID_TO_KEY[match.group(1)]
    stem = re.sub(r"__[a-z0-9]{4}-[a-z0-9]{4}$", "", dataset_dir.name)
    stem = stem.replace("-", "_")
    return "nyc__" + re.sub(r"[^a-z0-9]+", "_", stem.lower()).strip("_")


def load_harvest_summary(harvest_root: Path) -> dict[str, dict[str, Any]]:
    summary_path = harvest_root / "harvest_chunked_summary.json"
    if not summary_path.exists():
        return {}
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    return {entry["key"]: entry for entry in payload.get("successes", [])}


def load_live_counts(harvest_root: Path) -> dict[str, int]:
    path = harvest_root / "nyc_dataset_live_counts.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {entry["key"]: int(entry.get("row_count") or 0) for entry in payload}


def inventory_chunk_folder(chunks_dir: Path, raw_root: Path, harvest_summary: dict[str, dict[str, Any]], live_counts: dict[str, int]) -> dict[str, Any]:
    dataset_dir = chunks_dir.parent
    dataset_key = dataset_key_from_dir(dataset_dir)
    files = sorted(chunks_dir.glob("*.csv"), key=chunk_offset)
    offsets = [chunk_offset(path) for path in files]
    duplicate_offsets = sorted(offset for offset, count in Counter(offsets).items() if count > 1)
    deltas = [b - a for a, b in zip(offsets, offsets[1:]) if b >= 0 and a >= 0]
    expected_step = Counter(deltas).most_common(1)[0][0] if deltas else None
    expected_offsets: list[int] = []
    missing_offsets: list[int] = []
    if expected_step and offsets:
        expected_offsets = list(range(min(offsets), max(offsets) + expected_step, expected_step))
        missing_offsets = sorted(set(expected_offsets) - set(offsets))
    row_counts = [csv_row_count(path) for path in files]
    full_chunk_counts = row_counts[:-1] if len(row_counts) > 1 else row_counts
    mixed_chunk_sizes = len({count for count in full_chunk_counts if count > 0}) > 1
    old_5k_mixed = any(count <= 6000 for count in full_chunk_counts) and any(count >= 45000 for count in full_chunk_counts)
    warnings = []
    if old_5k_mixed:
        warnings.append("old 5k-sized chunks appear mixed with 50k chunks")
    if duplicate_offsets:
        warnings.append("duplicate offsets detected")
    if missing_offsets:
        warnings.append("expected offsets missing before final chunk")
    if mixed_chunk_sizes:
        warnings.append("mixed non-final chunk row counts detected")
    latest_ts = max((path.stat().st_mtime for path in files), default=0)
    summary = harvest_summary.get(dataset_key, {})
    live_total = live_counts.get(dataset_key)
    reported_total = int(summary.get("reported_total") or live_total or 0)
    target_rows = int(summary.get("target_rows") or 0)
    total_rows = int(sum(row_counts))
    if reported_total and total_rows >= reported_total:
        cap_status = "full_local"
    elif target_rows and reported_total and target_rows < reported_total:
        cap_status = f"capped_at_{target_rows}"
    elif reported_total and total_rows < reported_total:
        cap_status = f"partial_or_capped_{total_rows}_of_{reported_total}"
    else:
        cap_status = "unknown_or_uncounted"
    return {
        "dataset_key": dataset_key,
        "dataset_name": DATASET_NAMES.get(dataset_key, dataset_dir.name),
        "raw_folder": str(chunks_dir.relative_to(raw_root)),
        "chunk_count": len(files),
        "first_offset": min(offsets) if offsets else None,
        "last_offset": max(offsets) if offsets else None,
        "expected_offsets_present": not missing_offsets and not duplicate_offsets,
        "missing_offsets": missing_offsets,
        "duplicate_offsets": duplicate_offsets,
        "mixed_chunk_sizes_detected": bool(mixed_chunk_sizes or old_5k_mixed),
        "total_raw_csv_rows_estimated": total_rows,
        "download_cap_or_full_status": cap_status,
        "latest_file_timestamp": datetime.fromtimestamp(latest_ts, timezone.utc).isoformat() if latest_ts else None,
        "expected_offset_step": expected_step,
        "row_count_by_chunk": row_counts,
        "warnings": warnings,
        "chunk_files": [str(path.relative_to(raw_root)) for path in files],
        "reported_total": reported_total,
        "target_rows": target_rows,
    }


def discover_chunk_inventory(raw_root: Path, harvest_root: Path) -> list[dict[str, Any]]:
    harvest_summary = load_harvest_summary(harvest_root)
    live_counts = load_live_counts(harvest_root)
    rows = [
        inventory_chunk_folder(chunks_dir, raw_root, harvest_summary, live_counts)
        for chunks_dir in sorted(raw_root.rglob("chunks"))
        if any(chunks_dir.glob("*.csv"))
    ]
    return sorted(rows, key=lambda item: item["dataset_key"])


def read_csv_string(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_filter=False, low_memory=False)


def convert_raw_chunks(raw_root: Path, inventory: list[dict[str, Any]], raw_out: Path) -> dict[str, Any]:
    safe_clean_dir(raw_out)
    ingested_at = utc_now()
    summary = {}
    for item in inventory:
        dataset_key = item["dataset_key"]
        dataset_dir = raw_out / dataset_key
        dataset_dir.mkdir(parents=True, exist_ok=True)
        parts = []
        rows_written = 0
        columns: list[str] = []
        warnings = list(item.get("warnings") or [])
        for part_idx, rel in enumerate(item["chunk_files"]):
            csv_path = raw_root / rel
            offset = chunk_offset(csv_path)
            df = read_csv_string(csv_path)
            df["_citybrain_source_dataset"] = dataset_key
            df["_citybrain_source_file"] = str(csv_path)
            df["_citybrain_chunk_offset"] = str(offset)
            df["_citybrain_ingested_at"] = ingested_at
            part_path = dataset_dir / f"part-{part_idx:05d}.parquet"
            df.to_parquet(part_path, index=False, engine="pyarrow")
            rows_written += len(df)
            columns = list(df.columns)
            parts.append(str(part_path))
        summary[dataset_key] = {
            "rows_written": rows_written,
            "columns": columns,
            "parquet_parts": len(parts),
            "source_chunks": item["chunk_count"],
            "dedupe_status": "not_deduped_raw_lossless",
            "warnings": warnings,
            "output_dir": str(dataset_dir),
        }
    return summary


def canonical_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def row_hash_for_df(df: pd.DataFrame) -> pd.Series:
    values = df.fillna("").astype(str).agg("\u241f".join, axis=1)
    return values.map(lambda text: hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest())


def key_series(df: pd.DataFrame, dataset_key: str) -> tuple[pd.Series, list[str], str, str]:
    preferred = [col for col in DEDUPE_KEYS.get(dataset_key, []) if col in df.columns]
    if preferred:
        key = df[preferred].fillna("").astype(str).agg("\u241f".join, axis=1)
        blank = key.str.replace("\u241f", "", regex=False).str.strip() == ""
        if blank.any():
            key = key.mask(blank, row_hash_for_df(df.loc[blank]))
            method = "stable_key_with_full_row_hash_for_blank_keys"
            confidence = "medium"
        else:
            method = "stable_source_key"
            confidence = "high"
        return key, preferred, method, confidence
    return row_hash_for_df(df), ["full_row_hash"], "full_row_hash", "low"


def dedupe_raw_tables(raw_out: Path, dedupe_out: Path) -> dict[str, Any]:
    safe_clean_dir(dedupe_out)
    report = {}
    for dataset_dir in sorted(path for path in raw_out.iterdir() if path.is_dir()):
        dataset_key = dataset_dir.name
        out_dir = dedupe_out / dataset_key
        out_dir.mkdir(parents=True, exist_ok=True)
        seen: set[str] = set()
        rows_before = rows_after = removed = 0
        key_used: list[str] = []
        method = "unknown"
        confidence = "unknown"
        part_count = 0
        for part in sorted(dataset_dir.glob("part-*.parquet")):
            df = pd.read_parquet(part)
            keys, key_used, method, confidence = key_series(df, dataset_key)
            rows_before += len(df)
            keep_mask = []
            for key in keys.astype(str):
                if key in seen:
                    keep_mask.append(False)
                else:
                    seen.add(key)
                    keep_mask.append(True)
            out_df = df.loc[keep_mask].copy()
            rows_after += len(out_df)
            removed += len(df) - len(out_df)
            if not out_df.empty:
                out_df["_citybrain_dedupe_key"] = keys.loc[out_df.index].astype(str).values
                out_df["_citybrain_dedupe_method"] = method
                part_path = out_dir / f"part-{part_count:05d}.parquet"
                out_df.to_parquet(part_path, index=False, engine="pyarrow")
                part_count += 1
        report[dataset_key] = {
            "rows_before": rows_before,
            "rows_after": rows_after,
            "duplicates_removed": removed,
            "dedupe_key_used": key_used,
            "dedupe_method": method,
            "dedupe_method_confidence": confidence,
            "parquet_parts": part_count,
            "output_dir": str(out_dir),
        }
    return report


def normalize_digits(value: Any, width: int | None = None) -> str:
    text = canonical_cell(value)
    if not text:
        return ""
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    digits = re.sub(r"\D", "", text)
    if not digits:
        return ""
    return digits.zfill(width) if width else digits


def normalize_bbl(value: Any) -> str:
    digits = normalize_digits(value)
    if not digits or set(digits) == {"0"}:
        return ""
    if len(digits) < 10:
        digits = digits.zfill(10)
    if len(digits) != 10:
        return ""
    return digits


def normalize_bin(value: Any) -> str:
    digits = normalize_digits(value)
    if not digits or set(digits) == {"0"}:
        return ""
    if len(digits) < 7:
        digits = digits.zfill(7)
    if len(digits) != 7:
        return ""
    return digits


def borough_code(value: Any) -> str:
    text = canonical_cell(value).upper()
    if not text:
        return ""
    digits = re.sub(r"\D", "", text)
    if digits and digits[0] in "12345":
        return digits[0]
    return BOROUGH_TO_CODE.get(text, "")


def bbl_from_components(borough: Any, block: Any, lot: Any) -> str:
    boro = borough_code(borough)
    block_digits = normalize_digits(block)
    lot_digits = normalize_digits(lot)
    if not boro or not block_digits or not lot_digits:
        return ""
    return normalize_bbl(f"{boro}{block_digits.zfill(5)}{lot_digits.zfill(4)}")


def block_key_from_bbl(bbl: Any) -> str:
    bbl_norm = normalize_bbl(bbl)
    if not bbl_norm:
        return ""
    return f"{bbl_norm[0]}-{bbl_norm[1:6]}"


def parse_date_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series.replace("", pd.NA), errors="coerce", utc=False).dt.date.astype("string").fillna("")


def latest_date(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    available = [col for col in columns if col in df.columns]
    if not available:
        return pd.Series([""] * len(df), index=df.index)
    parsed = [pd.to_datetime(df[col].replace("", pd.NA), errors="coerce", utc=False) for col in available]
    combined = pd.concat(parsed, axis=1).max(axis=1)
    return combined.dt.date.astype("string").fillna("")


def first_existing(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    result = pd.Series([""] * len(df), index=df.index, dtype="object")
    for col in columns:
        if col in df.columns:
            values = df[col].fillna("").astype(str).str.strip()
            result = result.mask(result.astype(str).str.strip() == "", values)
    return result.fillna("").astype(str)


def read_parquet_dataset(dataset_dir: Path, columns: list[str] | None = None) -> pd.DataFrame:
    frames = []
    for part in sorted(dataset_dir.glob("part-*.parquet")):
        frames.append(pd.read_parquet(part, columns=columns))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def build_geometry_lookups(geom_root: Path, staging_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    parcel_path = geom_root / "parcels" / "nyc_mappluto_taxlots_unique.parquet"
    building_path = geom_root / "buildings" / "nyc_building_footprints.parquet"
    parcels = pd.read_parquet(parcel_path)
    bbl_norm = parcels["BBL"].map(normalize_bbl)
    parcel_lookup = pd.DataFrame(
        {
            "bbl_norm": bbl_norm,
            "block_key": bbl_norm.map(block_key_from_bbl),
            "borough_code": bbl_norm.str[0],
            "block": bbl_norm.str[1:6],
            "lot": bbl_norm.str[6:10],
            "address": parcels.get("Address", pd.Series([""] * len(parcels))).fillna("").astype(str),
            "land_use": parcels.get("LandUse", pd.Series([""] * len(parcels))).fillna("").astype(str),
            "zoning": parcels[[col for col in ["ZoneDist1", "ZoneDist2", "ZoneDist3", "ZoneDist4"] if col in parcels.columns]]
            .fillna("")
            .astype(str)
            .agg("|".join, axis=1),
            "latitude": parcels.get("Latitude", pd.Series([""] * len(parcels))).fillna("").astype(str),
            "longitude": parcels.get("Longitude", pd.Series([""] * len(parcels))).fillna("").astype(str),
        }
    )
    parcel_lookup = parcel_lookup[parcel_lookup["bbl_norm"] != ""].drop_duplicates("bbl_norm")
    parcel_lookup.to_parquet(staging_dir / "parcel_bbl_block_lookup.parquet", index=False, engine="pyarrow")

    buildings = pd.read_parquet(building_path)
    map_bbl = buildings.get("mappluto_bbl", pd.Series([""] * len(buildings))).map(normalize_bbl)
    base_bbl = buildings.get("base_bbl", pd.Series([""] * len(buildings))).map(normalize_bbl)
    linked_bbl = map_bbl.mask(map_bbl == "", base_bbl)
    building_lookup = pd.DataFrame(
        {
            "bin_norm": buildings.get("bin", pd.Series([""] * len(buildings))).map(normalize_bin),
            "mappluto_bbl_norm": map_bbl,
            "base_bbl_norm": base_bbl,
            "block_key": linked_bbl.map(block_key_from_bbl),
            "height_roof": buildings.get("height_roof", pd.Series([""] * len(buildings))).fillna("").astype(str),
            "construction_year": buildings.get("construction_year", pd.Series([""] * len(buildings))).fillna("").astype(str),
            "ground_elevation": buildings.get("ground_elevation", pd.Series([""] * len(buildings))).fillna("").astype(str),
        }
    )
    building_lookup = building_lookup[building_lookup["bin_norm"] != ""].drop_duplicates("bin_norm")
    building_lookup.to_parquet(staging_dir / "building_bin_bbl_lookup.parquet", index=False, engine="pyarrow")
    return parcel_lookup, building_lookup


def stage_dob_now(df: pd.DataFrame) -> pd.DataFrame:
    bbl = first_existing(df, ["bbl"]).map(normalize_bbl)
    derived = pd.Series(
        [bbl_from_components(boro, block, lot) for boro, block, lot in zip(df.get("borough", ""), df.get("block", ""), df.get("lot", ""))],
        index=df.index,
    )
    bbl = bbl.mask(bbl == "", derived)
    event_date = latest_date(df, ["current_status_date", "approved_date", "first_permit_date", "filing_date"])
    return pd.DataFrame(
        {
            "bbl_norm": bbl,
            "bin_norm": first_existing(df, ["bin"]).map(normalize_bin),
            "job_number_norm": first_existing(df, ["job_filing_number"]).astype(str),
            "complaint_number_norm": "",
            "permit_number_norm": "",
            "license_number_norm": first_existing(df, ["applicant_license"]).map(lambda x: normalize_digits(x)),
            "business_name_norm": first_existing(df, ["applicant_business_name", "filing_representative_business_name", "owner_s_business_name"]).str.upper(),
            "event_date_norm": event_date,
            "latest_activity_date": event_date,
            "source_dataset": "nyc__dob_now_build_job_application_filings",
            "source_row_key": first_existing(df, ["job_filing_number", "_citybrain_dedupe_key"]),
        }
    )


def stage_dob_permit(df: pd.DataFrame) -> pd.DataFrame:
    bbl = first_existing(df, ["bbl"]).map(normalize_bbl)
    derived = pd.Series(
        [bbl_from_components(boro, block, lot) for boro, block, lot in zip(df.get("borough", ""), df.get("block", ""), df.get("lot", ""))],
        index=df.index,
    )
    bbl = bbl.mask(bbl == "", derived)
    event_date = latest_date(df, ["issuance_date", "filing_date", "job_start_date", "dobrundate"])
    permit_number = first_existing(df, ["permit_si_no", "job__", "_citybrain_dedupe_key"])
    return pd.DataFrame(
        {
            "bbl_norm": bbl,
            "bin_norm": first_existing(df, ["bin__"]).map(normalize_bin),
            "job_number_norm": first_existing(df, ["job__"]).map(lambda x: normalize_digits(x)),
            "complaint_number_norm": "",
            "permit_number_norm": permit_number,
            "license_number_norm": first_existing(df, ["permittee_s_license__", "hic_license"]).map(lambda x: normalize_digits(x)),
            "business_name_norm": first_existing(df, ["permittee_s_business_name", "superintendent_business_name", "owner_s_business_name"]).str.upper(),
            "event_date_norm": event_date,
            "latest_activity_date": event_date,
            "source_dataset": "nyc__dob_permit_issuance",
            "source_row_key": permit_number,
        }
    )


def stage_dob_complaints(df: pd.DataFrame) -> pd.DataFrame:
    event_date = latest_date(df, ["inspection_date", "disposition_date", "date_entered", "dobrundate"])
    return pd.DataFrame(
        {
            "bbl_norm": "",
            "bin_norm": first_existing(df, ["bin"]).map(normalize_bin),
            "job_number_norm": "",
            "complaint_number_norm": first_existing(df, ["complaint_number"]).map(lambda x: normalize_digits(x)),
            "permit_number_norm": "",
            "license_number_norm": "",
            "business_name_norm": "",
            "event_date_norm": event_date,
            "latest_activity_date": event_date,
            "source_dataset": "nyc__dob_complaints_received",
            "source_row_key": first_existing(df, ["complaint_number", "_citybrain_dedupe_key"]),
            "complaint_category": first_existing(df, ["complaint_category"]).map(lambda x: normalize_digits(x)),
        }
    )


def resolve_to_block(staging_dir: Path, building_lookup: pd.DataFrame, parcel_lookup: pd.DataFrame) -> tuple[dict[str, Any], pd.DataFrame, dict[str, pd.DataFrame]]:
    bin_to_bbl = dict(zip(building_lookup["bin_norm"], building_lookup["mappluto_bbl_norm"].mask(building_lookup["mappluto_bbl_norm"] == "", building_lookup["base_bbl_norm"])))
    bin_to_block = dict(zip(building_lookup["bin_norm"], building_lookup["block_key"]))
    valid_bbls = set(parcel_lookup["bbl_norm"])
    unresolved_rows = []
    staged: dict[str, pd.DataFrame] = {}

    now = pd.read_parquet(staging_dir / "dob_now_filings.parquet")
    now["block_key"] = now["bbl_norm"].map(block_key_from_bbl)
    now["block_assignment_method"] = np.where(now["bbl_norm"] != "", "exact_bbl", "")
    needs_bin = (now["block_key"] == "") & (now["bin_norm"] != "")
    now.loc[needs_bin, "bbl_norm"] = now.loc[needs_bin, "bin_norm"].map(bin_to_bbl).fillna("")
    now.loc[needs_bin, "block_key"] = now.loc[needs_bin, "bin_norm"].map(bin_to_block).fillna("")
    now.loc[needs_bin & (now["block_key"] != ""), "block_assignment_method"] = "bin_to_building_to_bbl"
    staged["dob_now"] = now

    permit = pd.read_parquet(staging_dir / "dob_permit_issuance.parquet")
    permit["block_key"] = permit["bbl_norm"].map(block_key_from_bbl)
    permit["block_assignment_method"] = np.where(permit["bbl_norm"] != "", "exact_bbl", "")
    needs_bin = (permit["block_key"] == "") & (permit["bin_norm"] != "")
    permit.loc[needs_bin, "bbl_norm"] = permit.loc[needs_bin, "bin_norm"].map(bin_to_bbl).fillna("")
    permit.loc[needs_bin, "block_key"] = permit.loc[needs_bin, "bin_norm"].map(bin_to_block).fillna("")
    permit.loc[needs_bin & (permit["block_key"] != ""), "block_assignment_method"] = "bin_to_building_to_bbl"
    staged["dob_permit"] = permit

    complaints = pd.read_parquet(staging_dir / "dob_complaints.parquet")
    complaints["resolved_bbl_norm"] = complaints["bin_norm"].map(bin_to_bbl).fillna("")
    complaints["block_key"] = complaints["bin_norm"].map(bin_to_block).fillna("")
    complaints["complaint_to_building_method"] = np.where(complaints["block_key"] != "", "exact_bin", "")
    complaints["block_assignment_basis"] = np.where(complaints["block_key"] != "", "building_bin_to_mappluto_bbl", "")
    complaints["complaint_resolution_status"] = np.where(complaints["block_key"] != "", "resolved_exact_bin", "unresolved_bin")
    staged["dob_complaints"] = complaints

    for source_name, df, reason_col in [
        ("dob_now", now, "block_assignment_method"),
        ("dob_permit", permit, "block_assignment_method"),
    ]:
        unresolved = df[df["block_key"] == ""].copy()
        if not unresolved.empty:
            unresolved_rows.append(
                pd.DataFrame(
                    {
                        "source_dataset": unresolved["source_dataset"],
                        "source_row_key": unresolved["source_row_key"],
                        "bin_norm": unresolved["bin_norm"],
                        "bbl_norm": unresolved["bbl_norm"],
                        "reason": f"{source_name}_unresolved_no_exact_bbl_or_bin_match",
                    }
                )
            )
    unresolved_complaints = complaints[complaints["complaint_resolution_status"] == "unresolved_bin"].copy()
    if not unresolved_complaints.empty:
        unresolved_rows.append(
            pd.DataFrame(
                {
                    "source_dataset": unresolved_complaints["source_dataset"],
                    "source_row_key": unresolved_complaints["source_row_key"],
                    "bin_norm": unresolved_complaints["bin_norm"],
                    "bbl_norm": unresolved_complaints["resolved_bbl_norm"],
                    "reason": np.where(unresolved_complaints["bin_norm"] == "", "complaint_zero_blank_unassigned_bin", "complaint_unmatched_bin"),
                }
            )
        )
    unresolved = pd.concat(unresolved_rows, ignore_index=True) if unresolved_rows else pd.DataFrame(columns=["source_dataset", "source_row_key", "bin_norm", "bbl_norm", "reason"])
    unresolved.to_csv(staging_dir.parent.parent.parent.parent / "outputs" / "_unused.csv", index=False) if False else None

    report = {
        "dob_now_records_resolved_to_block": int((now["block_key"] != "").sum()),
        "dob_now_records_unresolved": int((now["block_key"] == "").sum()),
        "dob_permit_records_resolved_to_block": int((permit["block_key"] != "").sum()),
        "dob_permit_records_unresolved": int((permit["block_key"] == "").sum()),
        "dob_complaints_resolved_by_exact_bin": int((complaints["complaint_to_building_method"] == "exact_bin").sum()),
        "dob_complaints_unresolved_due_to_zero_blank_unmatched_bin": int((complaints["complaint_resolution_status"] == "unresolved_bin").sum()),
        "records_excluded_from_discovery_scoring": int(len(unresolved)),
        "complaint_resolution_rule": "complaint BIN -> building BIN -> mappluto_bbl -> block_key; no exact_bbl complaint method minted",
    }
    return report, unresolved, staged


def activity_base(parcel_lookup: pd.DataFrame, building_lookup: pd.DataFrame, staged: dict[str, pd.DataFrame]) -> pd.DataFrame:
    blocks = parcel_lookup.groupby(["block_key", "borough_code", "block"], dropna=False).agg(parcel_count=("bbl_norm", "nunique")).reset_index()
    building_counts = building_lookup[building_lookup["block_key"] != ""].groupby("block_key").agg(building_count=("bin_norm", "nunique")).reset_index()
    base = blocks.merge(building_counts, on="block_key", how="left")
    base["building_count"] = base["building_count"].fillna(0).astype(int)
    active_bbls = []
    for key in ["dob_now", "dob_permit"]:
        df = staged[key]
        active_bbls.append(df[df["block_key"] != ""][["block_key", "bbl_norm"]])
    complaints = staged["dob_complaints"]
    active_bbls.append(complaints[complaints["block_key"] != ""][["block_key", "resolved_bbl_norm"]].rename(columns={"resolved_bbl_norm": "bbl_norm"}))
    active = pd.concat(active_bbls, ignore_index=True)
    active_counts = active[active["bbl_norm"] != ""].drop_duplicates().groupby("block_key").agg(parcels_with_any_dob_activity=("bbl_norm", "nunique")).reset_index()
    base = base.merge(active_counts, on="block_key", how="left")
    base["parcels_with_any_dob_activity"] = base["parcels_with_any_dob_activity"].fillna(0).astype(int)

    now = staged["dob_now"]
    permit = staged["dob_permit"]
    complaints = staged["dob_complaints"]
    for name, df, col in [
        ("dob_now_filing_count", now, "job_number_norm"),
        ("dob_permit_issuance_count", permit, "permit_number_norm"),
        ("dob_complaint_count", complaints[complaints["block_key"] != ""], "complaint_number_norm"),
    ]:
        counts = df[df["block_key"] != ""].groupby("block_key").size().rename(name).reset_index()
        base = base.merge(counts, on="block_key", how="left")
        base[name] = base[name].fillna(0).astype(int)

    jobs = pd.concat(
        [
            now[now["block_key"] != ""][["block_key", "job_number_norm"]],
            permit[permit["block_key"] != ""][["block_key", "job_number_norm"]],
        ],
        ignore_index=True,
    )
    unique_jobs = jobs[jobs["job_number_norm"] != ""].drop_duplicates().groupby("block_key").agg(unique_job_count=("job_number_norm", "nunique")).reset_index()
    base = base.merge(unique_jobs, on="block_key", how="left")
    base["unique_job_count"] = base["unique_job_count"].fillna(0).astype(int)

    critical = complaints[(complaints["block_key"] != "") & (complaints["complaint_category"] == "91")].groupby("block_key").size().rename("critical_complaint_count").reset_index()
    exact_bin = complaints[complaints["complaint_to_building_method"] == "exact_bin"].groupby("block_key").size().rename("exact_bin_complaint_count").reset_index()
    category_mix = complaints[complaints["block_key"] != ""].groupby("block_key")["complaint_category"].agg(lambda s: json.dumps(dict(Counter([x for x in s if x])), sort_keys=True)).rename("complaint_category_mix").reset_index()
    for df in [critical, exact_bin, category_mix]:
        base = base.merge(df, on="block_key", how="left")
    base["critical_complaint_count"] = base["critical_complaint_count"].fillna(0).astype(int)
    base["exact_bin_complaint_count"] = base["exact_bin_complaint_count"].fillna(0).astype(int)
    base["unresolved_bin_complaint_count"] = 0
    base["complaint_category_mix"] = base["complaint_category_mix"].fillna("{}")

    bins = pd.concat(
        [
            now[now["block_key"] != ""][["block_key", "bin_norm"]],
            permit[permit["block_key"] != ""][["block_key", "bin_norm"]],
            complaints[complaints["block_key"] != ""][["block_key", "bin_norm"]],
        ],
        ignore_index=True,
    )
    bin_counts = bins[bins["bin_norm"] != ""].drop_duplicates().groupby("block_key").agg(unique_bins_involved=("bin_norm", "nunique")).reset_index()
    base = base.merge(bin_counts, on="block_key", how="left")
    base["unique_bins_involved"] = base["unique_bins_involved"].fillna(0).astype(int)

    parties = pd.concat(
        [
            now[now["block_key"] != ""][["block_key", "license_number_norm", "business_name_norm"]],
            permit[permit["block_key"] != ""][["block_key", "license_number_norm", "business_name_norm"]],
        ],
        ignore_index=True,
    )
    parties["party_key"] = np.where(parties["license_number_norm"] != "", "license:" + parties["license_number_norm"], np.where(parties["business_name_norm"] != "", "name:" + parties["business_name_norm"], ""))
    party_counts = parties[parties["party_key"] != ""].drop_duplicates().groupby("block_key").agg(unique_contractors_or_license_parties=("party_key", "nunique")).reset_index()
    license_counts = parties[parties["license_number_norm"] != ""].drop_duplicates(["block_key", "license_number_norm"]).groupby("block_key").size().rename("unique_license_parties").reset_index()
    name_counts = parties[(parties["license_number_norm"] == "") & (parties["business_name_norm"] != "")].drop_duplicates(["block_key", "business_name_norm"]).groupby("block_key").size().rename("business_name_only_party_count").reset_index()
    for df in [party_counts, license_counts, name_counts]:
        base = base.merge(df, on="block_key", how="left")
    for col in ["unique_contractors_or_license_parties", "unique_license_parties", "business_name_only_party_count"]:
        base[col] = base[col].fillna(0).astype(int)

    dates = pd.concat(
        [
            now[now["block_key"] != ""][["block_key", "latest_activity_date"]],
            permit[permit["block_key"] != ""][["block_key", "latest_activity_date"]],
            complaints[complaints["block_key"] != ""][["block_key", "latest_activity_date"]],
        ],
        ignore_index=True,
    )
    parsed_dates = pd.to_datetime(dates["latest_activity_date"].replace("", pd.NA), errors="coerce")
    dates = dates.assign(_date=parsed_dates).dropna(subset=["_date"])
    if not dates.empty:
        date_agg = dates.groupby("block_key").agg(latest_activity_date=("_date", "max"), earliest_activity_date=("_date", "min")).reset_index()
        date_agg["latest_activity_date"] = date_agg["latest_activity_date"].dt.date.astype(str)
        date_agg["earliest_activity_date"] = date_agg["earliest_activity_date"].dt.date.astype(str)
        base = base.merge(date_agg, on="block_key", how="left")
    else:
        base["latest_activity_date"] = ""
        base["earliest_activity_date"] = ""
    base["latest_activity_date"] = base["latest_activity_date"].fillna("")
    base["earliest_activity_date"] = base["earliest_activity_date"].fillna("")
    latest = pd.to_datetime(base["latest_activity_date"].replace("", pd.NA), errors="coerce")
    earliest = pd.to_datetime(base["earliest_activity_date"].replace("", pd.NA), errors="coerce")
    base["activity_span_years"] = ((latest - earliest).dt.days / 365.25).fillna(0).round(4)
    base["source_boundary_label"] = BOUNDARY_STATEMENT
    return base


def write_staging(dedupe_out: Path, staging_dir: Path, geom_root: Path, output_dir: Path) -> dict[str, Any]:
    safe_clean_dir(staging_dir)
    parcel_lookup, building_lookup = build_geometry_lookups(geom_root, staging_dir)
    now_raw = read_parquet_dataset(dedupe_out / "nyc__dob_now_build_job_application_filings")
    permit_raw = read_parquet_dataset(dedupe_out / "nyc__dob_permit_issuance")
    complaint_raw = read_parquet_dataset(dedupe_out / "nyc__dob_complaints_received")
    now = stage_dob_now(now_raw)
    permit = stage_dob_permit(permit_raw)
    complaints = stage_dob_complaints(complaint_raw)
    now.to_parquet(staging_dir / "dob_now_filings.parquet", index=False, engine="pyarrow")
    permit.to_parquet(staging_dir / "dob_permit_issuance.parquet", index=False, engine="pyarrow")
    complaints.to_parquet(staging_dir / "dob_complaints.parquet", index=False, engine="pyarrow")

    resolution_report, unresolved, staged = resolve_to_block(staging_dir, building_lookup, parcel_lookup)
    unresolved.to_csv(output_dir / "unresolved_dob_records.csv", index=False)
    for name, df in staged.items():
        out_name = {"dob_now": "dob_now_filings", "dob_permit": "dob_permit_issuance", "dob_complaints": "dob_complaints"}[name]
        df.to_parquet(staging_dir / f"{out_name}.parquet", index=False, engine="pyarrow")
    base = activity_base(parcel_lookup, building_lookup, staged)
    base.to_parquet(staging_dir / "block_dob_activity_base.parquet", index=False, engine="pyarrow")
    return {
        "resolution_report": resolution_report,
        "staging_rows": {
            "dob_now_filings": int(len(now)),
            "dob_permit_issuance": int(len(permit)),
            "dob_complaints": int(len(complaints)),
            "parcel_bbl_block_lookup": int(len(parcel_lookup)),
            "building_bin_bbl_lookup": int(len(building_lookup)),
            "block_dob_activity_base": int(len(base)),
        },
        "unresolved_records": int(len(unresolved)),
        "block_activity_base_rows": int(len(base)),
    }


def inventory_3d_assets(raw_root: Path) -> dict[str, Any]:
    candidates = [raw_root / "buildings", raw_root / "3d_buildings"]
    files = []
    for folder in candidates:
        if folder.exists():
            for path in folder.rglob("*"):
                if path.is_file() and ("3d" in path.name.lower() or "building_model" in path.name.lower()):
                    files.append(path)
    return {
        "checked": True,
        "file_count": len(files),
        "files_sample": [str(path.relative_to(raw_root)) for path in files[:20]],
        "note": "3D model inventoried only; no 3D/OpenUSD processing performed in prep v0.2.",
    }


def write_inventory_csv(path: Path, inventory: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "dataset_key",
        "dataset_name",
        "raw_folder",
        "chunk_count",
        "first_offset",
        "last_offset",
        "expected_offsets_present",
        "missing_offsets",
        "duplicate_offsets",
        "mixed_chunk_sizes_detected",
        "total_raw_csv_rows_estimated",
        "download_cap_or_full_status",
        "latest_file_timestamp",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in inventory:
            row = {field: item.get(field) for field in fields}
            row["missing_offsets"] = json.dumps(row["missing_offsets"])
            row["duplicate_offsets"] = json.dumps(row["duplicate_offsets"])
            writer.writerow(row)


def build_report(summary: dict[str, Any]) -> str:
    lines = [
        "# NYC Harvest Prep v0.2",
        "",
        f"Status: {summary['status']}",
        "",
        BOUNDARY_STATEMENT,
        "",
        "## Raw Inventory",
        "",
    ]
    for item in summary["inventory"]:
        lines.append(
            f"- `{item['dataset_key']}`: {item['total_raw_csv_rows_estimated']:,} rows, "
            f"{item['chunk_count']} chunks, `{item['download_cap_or_full_status']}`."
        )
        for warning in item.get("warnings") or []:
            lines.append(f"  - WARNING: {warning}")
    lines.extend(
        [
            "",
            "## Processed Locations",
            "",
            f"- Raw string-safe Parquet: `{summary['paths']['raw_tables']}`",
            f"- Deduped Parquet: `{summary['paths']['deduped_tables']}`",
            f"- Discovery staging: `{summary['paths']['discovery_staging']}`",
            "",
            "## DOB Resolution",
            "",
        ]
    )
    for key, value in summary["discovery_resolution_report"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## 3D Inventory",
            "",
            f"- 3D files observed: {summary['three_d_inventory']['file_count']}",
            "- 3D was not processed in this task.",
            "",
            "## Next Step",
            "",
            "Run a4-D2b district discovery using `data/processed/nyc/harvest_v0_2/discovery_staging/block_dob_activity_base.parquet`.",
            "",
        ]
    )
    return "\n".join(lines)


def run_harvest_prep_v0_2(
    raw_nyc_dir: str = str(DEFAULT_RAW_NYC),
    harvest_root: str = str(DEFAULT_HARVEST_ROOT),
    geometry_processed_dir: str = str(DEFAULT_GEOM_NYC),
    processed_root: str = str(DEFAULT_PROCESSED_ROOT),
    output_dir: str = str(DEFAULT_OUTPUT_DIR),
) -> dict[str, Any]:
    raw_root = Path(raw_nyc_dir)
    harvest = Path(harvest_root)
    geom_root = Path(geometry_processed_dir)
    processed = Path(processed_root)
    out = Path(output_dir)
    safe_clean_dir(out)
    safe_clean_dir(processed)
    raw_tables = processed / "raw_tables"
    deduped_tables = processed / "deduped_tables"
    staging = processed / "discovery_staging"

    inventory = discover_chunk_inventory(raw_root, harvest)
    write_json(out / "raw_harvest_inventory.json", inventory)
    write_inventory_csv(out / "raw_harvest_inventory.csv", inventory)
    raw_summary = convert_raw_chunks(raw_root, inventory, raw_tables)
    write_json(out / "raw_parquet_summary.json", raw_summary)
    dedupe_report = dedupe_raw_tables(raw_tables, deduped_tables)
    write_json(out / "dedupe_report.json", dedupe_report)
    staging_summary = write_staging(deduped_tables, staging, geom_root, out)
    write_json(out / "discovery_resolution_report.json", staging_summary["resolution_report"])
    three_d = inventory_3d_assets(raw_root)

    warnings = [warning for item in inventory for warning in (item.get("warnings") or [])]
    summary = {
        "task": "NYC Harvest Prep v0.2",
        "status": "PASS" if not any("duplicate offsets" in w or "expected offsets" in w for w in warnings) else "WARN",
        "generated_at": utc_now(),
        "boundary_statement": BOUNDARY_STATEMENT,
        "raw_nyc_dir": str(raw_root),
        "geometry_processed_dir": str(geom_root),
        "paths": {
            "raw_tables": str(raw_tables),
            "deduped_tables": str(deduped_tables),
            "discovery_staging": str(staging),
            "block_dob_activity_base": str(staging / "block_dob_activity_base.parquet"),
        },
        "inventory": inventory,
        "raw_parquet_summary": raw_summary,
        "dedupe_report": dedupe_report,
        "discovery_resolution_report": staging_summary["resolution_report"],
        "staging_summary": staging_summary,
        "three_d_inventory": three_d,
        "warnings": warnings,
        "acceptance": {
            "chunk_folders_inventoried": len(inventory),
            "raw_parquet_created": raw_tables.exists(),
            "deduped_tables_created": deduped_tables.exists(),
            "dob_staging_created": all((staging / name).exists() for name in ["dob_now_filings.parquet", "dob_permit_issuance.parquet", "dob_complaints.parquet"]),
            "lookups_created": all((staging / name).exists() for name in ["building_bin_bbl_lookup.parquet", "parcel_bbl_block_lookup.parquet"]),
            "block_activity_base_exists": (staging / "block_dob_activity_base.parquet").exists(),
            "canonical_artifacts_mutated": False,
        },
    }
    write_json(out / "harvest_prep_summary.json", summary)
    write_text(out / "NYC_HARVEST_PREP_REPORT.md", build_report(summary))
    return summary


def print_report(summary: dict[str, Any]) -> None:
    print(f"NYC Harvest Prep v0.2: {summary['status']}")
    print(f"Raw datasets inventoried: {len(summary['inventory'])}")
    print(f"Raw Parquet: {summary['paths']['raw_tables']}")
    print(f"Deduped Parquet: {summary['paths']['deduped_tables']}")
    print(f"Discovery staging: {summary['paths']['discovery_staging']}")
    print(f"Block base rows: {summary['staging_summary']['block_activity_base_rows']}")
    print(f"Unresolved DOB records: {summary['staging_summary']['unresolved_records']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run NYC harvest prep v0.2.")
    parser.add_argument("--raw-nyc-dir", default=str(DEFAULT_RAW_NYC))
    parser.add_argument("--harvest-root", default=str(DEFAULT_HARVEST_ROOT))
    parser.add_argument("--geometry-processed-dir", default=str(DEFAULT_GEOM_NYC))
    parser.add_argument("--processed-root", default=str(DEFAULT_PROCESSED_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    summary = run_harvest_prep_v0_2(
        raw_nyc_dir=args.raw_nyc_dir,
        harvest_root=args.harvest_root,
        geometry_processed_dir=args.geometry_processed_dir,
        processed_root=args.processed_root,
        output_dir=args.output_dir,
    )
    print_report(summary)
    return 0 if summary["status"] in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""
Prepare scoped Parquet sources for the NYC Flow 2 adapter.

This is deliberately not a citywide conversion. It creates only the hero block
and pinned Flow 2 fixture rows needed by the harness.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Callable, Iterable

import geopandas as gpd
import pandas as pd


ROOT = Path(__file__).resolve().parent
HARVEST_ROOT = ROOT / "citybrain_data_harvest_pack" / "citybrain_data_harvest" / "data" / "raw"
PARQUET_ROOT = ROOT / "data" / "processed" / "nyc_flow2"

MAPPLUTO_SHP = ROOT / "nyc_mappluto_25v4_arc_shp" / "MapPLUTO.shp"
DOB_NOW_CSV = HARVEST_ROOT / "nyc" / "permits_inspections" / (
    "dob_now_build_job_application_filings__w9ak-ipjd"
) / "dob_now_build_job_application_filings__sample_100000.csv"
PERMIT_CSV = HARVEST_ROOT / "nyc" / "permits_inspections" / (
    "dob_permit_issuance__ipu4-2q9a"
) / "dob_permit_issuance__sample_100000.csv"
COMPLAINT_CSV = HARVEST_ROOT / "nyc" / "permits_inspections" / (
    "dob_complaints_received__eabe-havv"
) / "dob_complaints_received__sample_100000.csv"
TRAFFIC_CSV = HARVEST_ROOT / "nyc" / "mobility" / "dot_traffic_speeds__i4gi-tjb9" / (
    "dot_traffic_speeds__sample_100000.csv"
)
COLLISIONS_CSV = HARVEST_ROOT / "nyc" / "public_safety" / (
    "motor_vehicle_collisions_crashes__h9gi-nx95"
) / "motor_vehicle_collisions_crashes__sample_100000.csv"

HERO_BOROUGH = "MN"
HERO_BLOCK = "1060"
HERO_BBL = "1010607502"
HERO_BIN = "1026676"
HERO_PERMIT_JOB = "121912591"
HERO_COMPLAINT = "1366080"
HERO_COLLISION = "4486635"
HERO_TRAFFIC_LINK = "4616357"


PARQUET_PATHS = {
    "mappluto_block": PARQUET_ROOT / "mappluto_mn_block_1060.parquet",
    "dob_now": PARQUET_ROOT / "dob_now_hero.parquet",
    "permit": PARQUET_ROOT / "dob_permit_hero.parquet",
    "complaint": PARQUET_ROOT / "dob_complaint_hero.parquet",
    "traffic": PARQUET_ROOT / "dot_traffic_link_4616357.parquet",
    "collision": PARQUET_ROOT / "collision_4486635.parquet",
}


def read_rows(path: Path) -> Iterable[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        yield from csv.DictReader(handle)


def rows_where(path: Path, predicate: Callable[[dict[str, str]], bool]) -> list[dict[str, str]]:
    return [row for row in read_rows(path) if predicate(row)]


def normalize_numeric_key(value: object, width: int | None = None) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        if re.fullmatch(r"\d+(\.0+)?", text):
            text = str(int(float(text)))
    except ValueError:
        pass
    return text.zfill(width) if width else text


def normalize_bbl(value: object) -> str:
    return normalize_numeric_key(value, 10)


def normalize_bin(value: object) -> str:
    return normalize_numeric_key(value, 7)


def write_rows_parquet(rows: list[dict[str, str]], path: Path, key_columns: dict[str, Callable[[object], str]]) -> None:
    if not rows:
        raise RuntimeError(f"No rows selected for {path}")
    df = pd.DataFrame(rows).astype("string")
    for col, normalizer in key_columns.items():
        if col in df.columns:
            df[col] = df[col].map(normalizer).astype("string")
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def prepare_mappluto() -> None:
    where = f"Borough = '{HERO_BOROUGH}' AND Block = {int(HERO_BLOCK)}"
    gdf = gpd.read_file(MAPPLUTO_SHP, where=where)
    if gdf.empty:
        raise RuntimeError(f"MapPLUTO filter produced no rows: {where}")
    if str(gdf.crs).upper() != "EPSG:2263":
        raise RuntimeError(f"Expected MapPLUTO CRS EPSG:2263, got {gdf.crs}")

    gdf["BBL"] = gdf["BBL"].map(normalize_bbl).astype("string")
    gdf["Block"] = gdf["Block"].map(lambda value: normalize_numeric_key(value, 5)).astype("string")
    gdf["Lot"] = gdf["Lot"].map(lambda value: normalize_numeric_key(value, 4)).astype("string")
    if "APPBBL" in gdf.columns:
        gdf["APPBBL"] = gdf["APPBBL"].map(normalize_bbl).astype("string")
    gdf = gdf.to_crs("EPSG:4326")
    PARQUET_ROOT.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(PARQUET_PATHS["mappluto_block"], index=False)


def prepare_dob_and_mobility() -> None:
    write_rows_parquet(
        rows_where(DOB_NOW_CSV, lambda row: normalize_bin(row.get("bin")) == HERO_BIN),
        PARQUET_PATHS["dob_now"],
        {"bin": normalize_bin, "bbl": normalize_bbl},
    )
    write_rows_parquet(
        rows_where(PERMIT_CSV, lambda row: normalize_bin(row.get("bin__")) == HERO_BIN and row.get("job__") == HERO_PERMIT_JOB),
        PARQUET_PATHS["permit"],
        {"bin__": normalize_bin, "bbl": normalize_bbl},
    )
    write_rows_parquet(
        rows_where(COMPLAINT_CSV, lambda row: row.get("complaint_number") == HERO_COMPLAINT),
        PARQUET_PATHS["complaint"],
        {"bin": normalize_bin},
    )
    write_rows_parquet(
        rows_where(TRAFFIC_CSV, lambda row: row.get("link_id") == HERO_TRAFFIC_LINK),
        PARQUET_PATHS["traffic"],
        {"link_id": str},
    )
    write_rows_parquet(
        rows_where(COLLISIONS_CSV, lambda row: row.get("collision_id") == HERO_COLLISION),
        PARQUET_PATHS["collision"],
        {"collision_id": str},
    )


def verify_keys() -> dict[str, object]:
    mappluto = gpd.read_parquet(PARQUET_PATHS["mappluto_block"])
    dob_now = pd.read_parquet(PARQUET_PATHS["dob_now"])
    permit = pd.read_parquet(PARQUET_PATHS["permit"])
    complaint = pd.read_parquet(PARQUET_PATHS["complaint"])

    report = {
        "mappluto_bbl_dtype": str(mappluto["BBL"].dtype),
        "mappluto_hero_bbl": mappluto.loc[mappluto["BBL"] == HERO_BBL, "BBL"].iloc[0],
        "dob_now_bin_dtype": str(dob_now["bin"].dtype),
        "dob_now_hero_bin": dob_now.loc[dob_now["bin"] == HERO_BIN, "bin"].iloc[0],
        "permit_bin_dtype": str(permit["bin__"].dtype),
        "permit_hero_bin": permit.loc[permit["bin__"] == HERO_BIN, "bin__"].iloc[0],
        "permit_bbl_dtype": str(permit["bbl"].dtype),
        "permit_hero_bbl": permit.loc[permit["bbl"] == HERO_BBL, "bbl"].iloc[0],
        "complaint_bin_dtype": str(complaint["bin"].dtype),
        "complaint_hero_bin": complaint.loc[complaint["bin"] == HERO_BIN, "bin"].iloc[0],
        "mappluto_rows": int(len(mappluto)),
    }
    for key in ("mappluto_hero_bbl", "permit_hero_bbl"):
        if report[key] != HERO_BBL:
            raise RuntimeError(f"BBL integrity failure: {key}={report[key]!r}")
    for key in ("dob_now_hero_bin", "permit_hero_bin", "complaint_hero_bin"):
        if report[key] != HERO_BIN:
            raise RuntimeError(f"BIN integrity failure: {key}={report[key]!r}")
    return report


def main() -> int:
    prepare_mappluto()
    prepare_dob_and_mobility()
    print(json.dumps(verify_keys(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

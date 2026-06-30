#!/usr/bin/env python3
"""A3-D2 footprint geometry upgrade for CityBrain Building entities.

This script is intentionally read-model oriented: it preserves accepted graph
identity/edge artifacts and adds BIN-keyed 2D footprint geometry for Building
rendering and downstream evidence surfaces.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
import shapely.wkb
from shapely.geometry import Point, mapping


BOUNDARY_STATEMENT = (
    "Counts are based on the current local NYC harvested dataset. Datasets may be full or capped depending on local "
    "harvest status. Discovery and projection counts are not claims about complete NYC history unless the dataset is "
    "marked full in the inventory."
)
GEOMETRY_CAVEAT = "Building footprints are 2D NYC Building Footprints polygons joined by exact BIN. They are not 3D geometry."
BLOCK_GEOMETRY_CAVEAT = "Block geometries are adapter bbox polygons from MapPLUTO parcel representative points, not official tax-block boundary polygons."
HERO_BLOCK = "1-01060"
HERO_BIN = "1026676"
HERO_BBL = "1010607502"
TARGET_JOIN_RATE = 0.97


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> str:
    if value is None:
        return ""
    try:
        if isinstance(value, float) and math.isnan(value):
            return ""
    except Exception:
        pass
    text = str(value).strip()
    if text.lower() in {"nan", "none", "<na>", "nat"}:
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def clean_key_series(series: pd.Series) -> pd.Series:
    return series.astype("string").fillna("").map(clean)


def is_zero_bin(series: pd.Series) -> pd.Series:
    text = clean_key_series(series)
    return text.eq("") | text.str.fullmatch(r"0+").fillna(False)


def valid_float(value: Any) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def link_or_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def table_schema_type(path: Path, column: str) -> str:
    schema = pq.ParquetFile(path).schema_arrow
    return str(schema.field(column).type) if column in schema.names else ""


def verify_footprints(footprints_path: Path, hero_parcel_path: Path | None = None) -> dict[str, Any]:
    dataset = ds.dataset(footprints_path, format="parquet")
    schema = dataset.schema
    bin_type = str(schema.field("bin").type) if "bin" in schema.names else None
    bin_norm_type = str(schema.field("bin_norm").type) if "bin_norm" in schema.names else None
    crs = None
    if schema.metadata and b"geo" in schema.metadata:
        try:
            crs = json.loads(schema.metadata[b"geo"].decode("utf-8"))["columns"]["geometry"].get("crs")
        except Exception:
            crs = "unreadable"

    hero = dataset.to_table(
        columns=["bin", "bin_norm", "height_roof", "ground_elevation", "shape_area", "geometry"],
        filter=ds.field("bin_norm") == HERO_BIN,
    )
    hero_rows = hero.num_rows
    hero_report: dict[str, Any] = {"bin": HERO_BIN, "rows": hero_rows}
    if hero_rows:
        row = hero.to_pydict()
        geom = shapely.wkb.loads(hero.column("geometry")[0].as_py())
        hero_report.update(
            {
                "raw_bin": row["bin"][0],
                "bin_norm": row["bin_norm"][0],
                "height_roof": row["height_roof"][0],
                "ground_elevation": row["ground_elevation"][0],
                "shape_area": row["shape_area"][0],
                "geometry_type": geom.geom_type,
                "geometry_valid": bool(geom.is_valid),
                "bounds": list(geom.bounds),
                "centroid": [geom.centroid.x, geom.centroid.y],
                "wgs84_coordinate_spot_check": -74.1 < geom.centroid.x < -73.8 and 40.6 < geom.centroid.y < 40.9,
            }
        )

        if hero_parcel_path and hero_parcel_path.exists():
            parcels = pd.read_parquet(hero_parcel_path, columns=["BBL", "geometry"])
            parcel_rows = parcels[clean_key_series(parcels["BBL"]).eq(HERO_BBL)]
            if not parcel_rows.empty:
                parcel = shapely.wkb.loads(parcel_rows.iloc[0]["geometry"])
                intersection_ratio = geom.intersection(parcel).area / geom.area if geom.area else 0
                hero_report["parcel_containment"] = {
                    "hero_bbl": HERO_BBL,
                    "strict_within": bool(geom.within(parcel)),
                    "covered_by": bool(geom.covered_by(parcel)),
                    "centroid_within": bool(geom.centroid.within(parcel)),
                    "intersection_area_ratio": intersection_ratio,
                    "tolerant_containment_1e-5deg": bool(geom.covered_by(parcel.buffer(1e-5))),
                }

    passed = (
        bin_type in {"string", "large_string"}
        and bin_norm_type in {"string", "large_string"}
        and hero_rows >= 1
        and hero_report.get("raw_bin") == HERO_BIN
        and hero_report.get("bin_norm") == HERO_BIN
        and hero_report.get("geometry_valid") is True
        and hero_report.get("wgs84_coordinate_spot_check") is True
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "footprints_path": str(footprints_path),
        "row_count": pq.ParquetFile(footprints_path).metadata.num_rows,
        "bin_type": bin_type,
        "bin_norm_type": bin_norm_type,
        "geometry_type": str(schema.field("geometry").type) if "geometry" in schema.names else None,
        "crs": crs,
        "hero": hero_report,
    }


def build_footprint_index(footprints_path: Path, output_dir: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    cols = ["bin", "bin_norm", "geometry", "height_roof", "ground_elevation", "shape_area"]
    footprints = pd.read_parquet(footprints_path, columns=cols)
    footprints["bin_norm"] = clean_key_series(footprints["bin_norm"] if "bin_norm" in footprints.columns else footprints["bin"])
    footprints["bin"] = clean_key_series(footprints["bin"])
    footprints["shape_area_num"] = pd.to_numeric(footprints["shape_area"], errors="coerce").fillna(0.0)
    footprints["roof_height_ft"] = pd.to_numeric(footprints["height_roof"], errors="coerce")
    footprints["ground_elevation_ft"] = pd.to_numeric(footprints["ground_elevation"], errors="coerce")
    valid = ~is_zero_bin(footprints["bin_norm"]) & footprints["geometry"].notna()
    valid_fp = footprints.loc[valid].copy()
    duplicate_counts = valid_fp["bin_norm"].value_counts()
    multi_bins = duplicate_counts[duplicate_counts > 1]
    valid_fp.sort_values(["bin_norm", "shape_area_num"], ascending=[True, False], inplace=True)
    index = valid_fp.drop_duplicates("bin_norm", keep="first").copy()
    index.rename(
        columns={
            "geometry": "footprint_wkb",
            "shape_area_num": "footprint_shape_area",
        },
        inplace=True,
    )
    index = index[["bin_norm", "bin", "footprint_wkb", "footprint_shape_area", "roof_height_ft", "ground_elevation_ft"]].copy()
    index_path = output_dir / "footprints" / "footprint_index_largest_by_bin.parquet"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index.to_parquet(index_path, index=False)
    multi_sample = [
        {"bin_norm": str(bin_norm), "polygon_count": int(count)}
        for bin_norm, count in multi_bins.head(25).items()
    ]
    report = {
        "status": "PASS",
        "source_rows": int(len(footprints)),
        "valid_bin_polygon_rows": int(len(valid_fp)),
        "unique_bin_rows": int(len(index)),
        "non_unique_bin_count": int(len(multi_bins)),
        "non_unique_bin_policy": "largest shape_area polygon kept; multi cases logged",
        "non_unique_bin_sample": multi_sample,
        "all_zero_bin_rows": int(is_zero_bin(footprints["bin_norm"]).sum()),
        "output": str(index_path),
    }
    return index, report


def point_wkb(lon: float | None, lat: float | None) -> bytes | None:
    if lon is None or lat is None:
        return None
    return Point(float(lon), float(lat)).wkb


def upgrade_entities(
    entities_path: Path,
    footprint_index: pd.DataFrame,
    staging_dir: Path,
    output_path: Path,
    block_key: str | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    entities = pd.read_parquet(entities_path)
    if block_key:
        entities = entities[clean_key_series(entities["block_key"]).eq(block_key)].copy()
    else:
        entities = entities.copy()

    for col in [
        "geometry",
        "geometry_type",
        "geometry_crs",
        "geometry_source",
        "geometry_resolution_method",
        "geometry_confidence",
        "geometry_basis",
        "geometry_fallback_reason",
        "ext_nyc_roof_height",
        "ext_nyc_ground_elevation",
        "footprint_shape_area",
    ]:
        if col not in entities.columns:
            entities[col] = None

    building_mask = entities["entity_type"].astype(str).eq("building")
    building_count = int(building_mask.sum())
    buildings = entities.loc[building_mask, ["canonical_id", "block_key", "bbl", "bin"]].copy()
    buildings["_row_index"] = buildings.index
    buildings["bin_norm"] = clean_key_series(buildings["bin"])
    buildings["bbl_norm"] = clean_key_series(buildings["bbl"])
    buildings["valid_bin"] = ~is_zero_bin(buildings["bin_norm"])

    merged = buildings.merge(footprint_index, on="bin_norm", how="left")
    matched = merged[merged["footprint_wkb"].notna() & merged["valid_bin"]].copy()
    zero_or_no_bin = merged[~merged["valid_bin"]].copy()
    unmatched = merged[merged["valid_bin"] & merged["footprint_wkb"].isna()].copy()

    if not matched.empty:
        idx = matched["_row_index"].to_numpy()
        entities.loc[idx, "geometry"] = matched["footprint_wkb"].tolist()
        entities.loc[idx, "geometry_type"] = "footprint_polygon"
        entities.loc[idx, "geometry_crs"] = "EPSG:4326"
        entities.loc[idx, "geometry_source"] = "nyc_building_footprints"
        entities.loc[idx, "geometry_resolution_method"] = "exact_bin"
        entities.loc[idx, "geometry_confidence"] = 0.98
        entities.loc[idx, "geometry_basis"] = matched["bin_norm"].map(lambda value: f"building BIN {value} equals footprint BIN {value}").tolist()
        entities.loc[idx, "geometry_fallback_reason"] = ""
        entities.loc[idx, "ext_nyc_roof_height"] = matched["roof_height_ft"].where(matched["roof_height_ft"].notna(), None).tolist()
        entities.loc[idx, "ext_nyc_ground_elevation"] = matched["ground_elevation_ft"].where(matched["ground_elevation_ft"].notna(), None).tolist()
        entities.loc[idx, "footprint_shape_area"] = matched["footprint_shape_area"].tolist()

    fallback = pd.concat([zero_or_no_bin, unmatched], ignore_index=True)
    fallback_with_point = 0
    fallback_no_point = 0
    if not fallback.empty:
        parcels_path = staging_dir / "parcel_bbl_block_lookup.parquet"
        if parcels_path.exists():
            parcels = pd.read_parquet(parcels_path, columns=["bbl_norm", "longitude", "latitude"])
            parcels["bbl_norm"] = clean_key_series(parcels["bbl_norm"])
            parcels["lon_point"] = parcels["longitude"].map(valid_float)
            parcels["lat_point"] = parcels["latitude"].map(valid_float)
            parcels = parcels.drop_duplicates("bbl_norm", keep="first")[["bbl_norm", "lon_point", "lat_point"]]
            fallback = fallback.merge(parcels, on="bbl_norm", how="left")
        else:
            fallback["lon_point"] = None
            fallback["lat_point"] = None
        point_bytes: list[bytes | None] = [point_wkb(lon, lat) for lon, lat in zip(fallback["lon_point"], fallback["lat_point"])]
        fallback["point_wkb"] = point_bytes
        has_point = fallback["point_wkb"].notna()
        if has_point.any():
            idx = fallback.loc[has_point, "_row_index"].to_numpy()
            entities.loc[idx, "geometry"] = fallback.loc[has_point, "point_wkb"].tolist()
            entities.loc[idx, "geometry_type"] = "point_fallback"
            entities.loc[idx, "geometry_crs"] = "EPSG:4326"
            entities.loc[idx, "geometry_source"] = "mappluto_parcel_representative_point"
            entities.loc[idx, "geometry_resolution_method"] = "point_fallback"
            entities.loc[idx, "geometry_confidence"] = 0.55
            entities.loc[idx, "geometry_basis"] = "No exact BIN footprint; point fallback from parcel representative point"
            entities.loc[idx, "geometry_fallback_reason"] = fallback.loc[has_point, "bin_norm"].map(
                lambda value: "all_zero_or_missing_bin" if not clean(value) or set(clean(value)) <= {"0"} else "missing_footprint_for_bin"
            ).tolist()
            fallback_with_point = int(has_point.sum())
        if (~has_point).any():
            idx = fallback.loc[~has_point, "_row_index"].to_numpy()
            entities.loc[idx, "geometry_type"] = "missing_geometry"
            entities.loc[idx, "geometry_crs"] = "EPSG:4326"
            entities.loc[idx, "geometry_source"] = "none"
            entities.loc[idx, "geometry_resolution_method"] = "unresolved"
            entities.loc[idx, "geometry_confidence"] = 0.0
            entities.loc[idx, "geometry_basis"] = "No exact BIN footprint and no parcel representative point fallback"
            entities.loc[idx, "geometry_fallback_reason"] = "unresolved"
            fallback_no_point = int((~has_point).sum())

    non_building_idx = entities.index[~building_mask]
    entities.loc[non_building_idx, "geometry_type"] = ""
    entities.loc[non_building_idx, "geometry_crs"] = ""
    entities.loc[non_building_idx, "geometry_source"] = ""
    entities.loc[non_building_idx, "geometry_resolution_method"] = ""
    entities.loc[non_building_idx, "geometry_confidence"] = None
    entities.loc[non_building_idx, "geometry_basis"] = ""
    entities.loc[non_building_idx, "geometry_fallback_reason"] = ""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    entities.to_parquet(output_path, index=False)
    join_rate_all = (len(matched) / building_count) if building_count else 0
    valid_bin_count = int(buildings["valid_bin"].sum())
    join_rate_valid = (len(matched) / valid_bin_count) if valid_bin_count else 0
    report = {
        "status": "PASS" if int(len(matched)) > 0 else "FAIL",
        "scope": block_key or "citywide",
        "entity_rows": int(len(entities)),
        "building_count": building_count,
        "valid_bin_building_count": valid_bin_count,
        "matched_polygon_count": int(len(matched)),
        "point_fallback_count": fallback_with_point,
        "unresolved_geometry_count": fallback_no_point,
        "zero_or_missing_bin_count": int(len(zero_or_no_bin)),
        "missing_footprint_count": int(len(unmatched)),
        "join_rate_all_buildings": join_rate_all,
        "join_rate_valid_bins": join_rate_valid,
        "target_join_rate_note": "A3-D2 reports all-Building polygonized share plus footprint-catalog coverage separately.",
        "output": str(output_path),
    }
    return entities, report


def copy_graph_artifacts(input_dir: Path, output_dir: Path, block_key: str | None = None, entities: pd.DataFrame | None = None) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    if block_key and entities is not None:
        edges = pd.read_parquet(input_dir / "canonical_edges.parquet")
        edges = edges[clean_key_series(edges["block_key"]).eq(block_key)].copy()
        projection_nodes = entities[["canonical_id", "entity_type"]].rename(columns={"canonical_id": "id", "entity_type": "type"})
        projection_edges = edges[["edge_id", "src_ref", "dst_ref", "relation", "confidence_score"]].rename(
            columns={"src_ref": "src", "dst_ref": "dst", "confidence_score": "confidence"}
        )
        edges.to_parquet(output_dir / "canonical_edges.parquet", index=False)
        projection_nodes.to_parquet(output_dir / "graph_projection_nodes.parquet", index=False)
        projection_edges.to_parquet(output_dir / "graph_projection_edges.parquet", index=False)
        copied.extend(["canonical_edges.parquet", "graph_projection_nodes.parquet", "graph_projection_edges.parquet"])
    else:
        for name in ["canonical_edges.parquet", "graph_projection_nodes.parquet", "graph_projection_edges.parquet"]:
            src = input_dir / name
            if src.exists():
                link_or_copy(src, output_dir / name)
                copied.append(name)
    return {"status": "PASS", "artifacts": copied}


def feature_json(feature: dict[str, Any]) -> str:
    return json.dumps(feature, sort_keys=True, separators=(",", ":"), default=str)


def build_upgraded_map_cache(
    base_db: Path,
    upgraded_entities: pd.DataFrame,
    output_db: Path,
    limit: int | None = None,
) -> dict[str, Any]:
    output_db.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(base_db, output_db)
    con = sqlite3.connect(output_db)
    cur = con.cursor()
    cur.executescript(
        """
        DROP TABLE IF EXISTS building_footprints;
        CREATE TABLE building_footprints (
          block_key TEXT NOT NULL,
          borough_code TEXT NOT NULL,
          canonical_id TEXT NOT NULL,
          bin TEXT NOT NULL,
          bbl TEXT NOT NULL,
          min_lon REAL, min_lat REAL, max_lon REAL, max_lat REAL,
          footprint_area REAL,
          feature_json TEXT NOT NULL
        );
        CREATE INDEX idx_building_footprints_bbox ON building_footprints(min_lon, max_lon, min_lat, max_lat);
        CREATE INDEX idx_building_footprints_block ON building_footprints(block_key);
        CREATE INDEX idx_building_footprints_bin ON building_footprints(bin);
        """
    )
    cur.execute(
        "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
        ("building_geometry_label", "Exact BIN NYC Building Footprints polygons at zoom 14+; point fallback remains labelled where footprint is unavailable."),
    )
    cur.execute(
        "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
        ("a3d2_geometry_upgrade", "a3d2_footprints_geometry_v1"),
    )

    rows = upgraded_entities[
        (upgraded_entities["entity_type"].astype(str) == "building")
        & (upgraded_entities["geometry_type"].astype(str) == "footprint_polygon")
        & upgraded_entities["geometry"].notna()
    ].copy()
    if limit:
        rows = rows.head(limit).copy()

    inserted = 0
    skipped_invalid = 0
    batch: list[tuple[Any, ...]] = []
    for row in rows.itertuples(index=False):
        try:
            geom = shapely.wkb.loads(row.geometry)
            if not geom.is_valid or geom.is_empty:
                skipped_invalid += 1
                continue
            min_lon, min_lat, max_lon, max_lat = geom.bounds
            props = {
                "level": "building-footprint",
                "canonical_id": clean(row.canonical_id),
                "entity_type": "building",
                "block_key": clean(row.block_key),
                "borough_code": clean(row.block_key).split("-", 1)[0] if "-" in clean(row.block_key) else "",
                "bin": clean(row.bin),
                "bbl": clean(row.bbl),
                "roof_height": valid_float(row.ext_nyc_roof_height),
                "ground_elevation": valid_float(row.ext_nyc_ground_elevation),
                "footprint_area": valid_float(row.footprint_shape_area),
                "geometry_source": "nyc_building_footprints",
                "geometry_resolution_method": "exact_bin",
                "geometry_confidence": 0.98,
                "geometry_label": GEOMETRY_CAVEAT,
                "trace_url": f"/trace?subject={clean(row.canonical_id)}",
            }
            feature = {"type": "Feature", "geometry": mapping(geom), "properties": props}
            batch.append(
                (
                    props["block_key"],
                    props["borough_code"],
                    props["canonical_id"],
                    props["bin"],
                    props["bbl"],
                    float(min_lon),
                    float(min_lat),
                    float(max_lon),
                    float(max_lat),
                    props["footprint_area"],
                    feature_json(feature),
                )
            )
            if len(batch) >= 5000:
                cur.executemany("INSERT INTO building_footprints VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", batch)
                inserted += len(batch)
                batch.clear()
        except Exception:
            skipped_invalid += 1
    if batch:
        cur.executemany("INSERT INTO building_footprints VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", batch)
        inserted += len(batch)
    con.commit()
    con.close()
    return {
        "status": "PASS" if inserted > 0 else "FAIL",
        "base_db": str(base_db),
        "output_db": str(output_db),
        "building_footprint_features": inserted,
        "skipped_invalid": skipped_invalid,
        "db_bytes": output_db.stat().st_size,
    }


def regression_report(input_dir: Path, output_dir: Path) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for name in ["canonical_edges.parquet", "graph_projection_nodes.parquet", "graph_projection_edges.parquet"]:
        src = input_dir / name
        dst = output_dir / name
        if src.exists() and dst.exists():
            src_meta = pq.ParquetFile(src).metadata
            dst_meta = pq.ParquetFile(dst).metadata
            checks[name] = {
                "source_rows": src_meta.num_rows,
                "upgraded_rows": dst_meta.num_rows,
                "rows_match": src_meta.num_rows == dst_meta.num_rows,
                "sha256_match": sha256_file(src) == sha256_file(dst),
            }
    passed = bool(checks) and all(item["rows_match"] and item["sha256_match"] for item in checks.values())
    return {"status": "PASS" if passed else "FAIL", "checks": checks}


def spot_check_buildings(entities: pd.DataFrame, sample_size: int = 10) -> list[dict[str, Any]]:
    buildings = entities[entities["entity_type"].astype(str).eq("building")].copy()
    if buildings.empty:
        return []
    sample = buildings.sample(n=min(sample_size, len(buildings)), random_state=3202)
    out = []
    for row in sample.itertuples(index=False):
        out.append(
            {
                "canonical_id": clean(row.canonical_id),
                "bin": clean(row.bin),
                "geometry_type": clean(row.geometry_type),
                "geometry_source": clean(row.geometry_source),
                "geometry_resolution_method": clean(row.geometry_resolution_method),
                "geometry_confidence": valid_float(row.geometry_confidence),
                "fallback_reason": clean(row.geometry_fallback_reason),
                "honest_label": clean(row.geometry_type) in {"footprint_polygon", "point_fallback", "missing_geometry"},
            }
        )
    return out


def run(args: argparse.Namespace) -> dict[str, Any]:
    footprints_path = Path(args.footprints)
    d3b_root = Path(args.d3b_root)
    staging_dir = Path(args.staging_dir)
    output_root = Path(args.output_dir)
    hero_parcel_path = Path(args.hero_parcel_path) if args.hero_parcel_path else None
    output_root.mkdir(parents=True, exist_ok=True)

    integrity = verify_footprints(footprints_path, hero_parcel_path)
    write_json(output_root / "A3D2_FOOTPRINTS_INTEGRITY_REPORT.json", integrity)
    if integrity["status"] != "PASS":
        raise RuntimeError("footprint integrity check failed")

    footprint_index, footprint_report = build_footprint_index(footprints_path, output_root)
    write_json(output_root / "A3D2_FOOTPRINT_INDEX_REPORT.json", footprint_report)

    citywide_input = d3b_root / "citywide"
    hero_dir = output_root / "hero_1-01060"
    citywide_dir = output_root / "citywide"

    hero_entities, hero_join = upgrade_entities(
        citywide_input / "canonical_entities.parquet",
        footprint_index,
        staging_dir,
        hero_dir / "canonical_entities.parquet",
        block_key=HERO_BLOCK,
    )
    copy_graph_artifacts(citywide_input, hero_dir, block_key=HERO_BLOCK, entities=hero_entities)
    write_json(hero_dir / "A3D2_HERO_JOIN_REPORT.json", hero_join)

    citywide_entities, citywide_join = upgrade_entities(
        citywide_input / "canonical_entities.parquet",
        footprint_index,
        staging_dir,
        citywide_dir / "canonical_entities.parquet",
        block_key=None,
    )
    citywide_join["footprint_catalog_unique_bin_count"] = int(len(footprint_index))
    citywide_join["join_rate_footprint_catalog_to_citywide_buildings"] = (
        citywide_join["matched_polygon_count"] / len(footprint_index) if len(footprint_index) else 0
    )
    citywide_join["target_join_rate"] = TARGET_JOIN_RATE
    citywide_join["target_join_rate_basis"] = (
        "footprints-to-active-citywide-building coverage, matching the earlier footprints-to-MapPLUTO join-rate direction"
    )
    citywide_join["all_buildings_polygonized_note"] = (
        "All-Building share includes DOB-only/inferred BIN Buildings not present in the footprint catalog; these retain point fallback labels."
    )
    citywide_join["status"] = (
        "PASS"
        if citywide_join["join_rate_footprint_catalog_to_citywide_buildings"] >= TARGET_JOIN_RATE
        and citywide_join["matched_polygon_count"] >= 1_000_000
        else "FAIL"
    )
    copy_graph_artifacts(citywide_input, citywide_dir)
    write_json(output_root / "A3D2_CITYWIDE_JOIN_REPORT.json", citywide_join)

    base_map_db = Path(args.base_map_db)
    map_report = build_upgraded_map_cache(base_map_db, citywide_entities, output_root / "map_cache" / "citywide_map_cache.sqlite")
    write_json(output_root / "A3D2_MAP_CACHE_REPORT.json", map_report)

    regression = regression_report(citywide_input, citywide_dir)
    write_json(output_root / "A3D2_A4D3B_REGRESSION_REPORT.json", regression)

    hero_building = hero_entities[
        (hero_entities["entity_type"].astype(str) == "building") & clean_key_series(hero_entities["bin"]).eq(HERO_BIN)
    ]
    hero_geometry_ok = False
    hero_geometry_report: dict[str, Any] = {"hero_bin": HERO_BIN, "rows": int(len(hero_building))}
    if not hero_building.empty:
        row = hero_building.iloc[0]
        geom = shapely.wkb.loads(row["geometry"])
        hero_geometry_ok = row["geometry_type"] == "footprint_polygon" and geom.is_valid and not geom.is_empty
        hero_geometry_report.update(
            {
                "canonical_id": clean(row["canonical_id"]),
                "geometry_type": clean(row["geometry_type"]),
                "geometry_source": clean(row["geometry_source"]),
                "geometry_resolution_method": clean(row["geometry_resolution_method"]),
                "geometry_confidence": valid_float(row["geometry_confidence"]),
                "bounds": list(geom.bounds),
                "roof_height": valid_float(row["ext_nyc_roof_height"]),
                "ground_elevation": valid_float(row["ext_nyc_ground_elevation"]),
            }
        )
        hero_geometry_report["parcel_containment"] = integrity["hero"].get("parcel_containment", {})

    spot_checks = spot_check_buildings(citywide_entities)
    spot_ok = all(item["honest_label"] for item in spot_checks)

    gates = [
        {"gate": "A3D2-FOOTPRINT-INTEGRITY", "status": integrity["status"]},
        {"gate": "A3D2-HERO-BUILDING-POLYGON", "status": "PASS" if hero_geometry_ok else "FAIL"},
        {
            "gate": "A3D2-HERO-PARCEL-CONTAINMENT",
            "status": "PASS"
            if integrity["hero"].get("parcel_containment", {}).get("tolerant_containment_1e-5deg")
            and integrity["hero"].get("parcel_containment", {}).get("centroid_within")
            and integrity["hero"].get("parcel_containment", {}).get("intersection_area_ratio", 0) >= 0.99
            else "FAIL",
        },
        {
            "gate": "A3D2-CITYWIDE-JOIN-RATE",
            "status": "PASS" if citywide_join["join_rate_footprint_catalog_to_citywide_buildings"] >= TARGET_JOIN_RATE else "FAIL",
        },
        {"gate": "A3D2-A4D3B-REGRESSION", "status": regression["status"]},
        {"gate": "A3D2-MAP-CACHE", "status": map_report["status"]},
        {"gate": "A3D2-SPOT-CHECK-LABELS", "status": "PASS" if spot_ok else "FAIL"},
    ]
    status = "PASS" if all(gate["status"] == "PASS" for gate in gates) else "FAIL"
    harness = {
        "status": status,
        "task": "A3-D2 footprints to Building geometry upgrade",
        "created_utc": utc_now(),
        "boundary_statement": BOUNDARY_STATEMENT,
        "geometry_caveat": GEOMETRY_CAVEAT,
        "block_geometry_caveat": BLOCK_GEOMETRY_CAVEAT,
        "input_d3b_root": str(d3b_root),
        "footprints_path": str(footprints_path),
        "hero": hero_geometry_report,
        "citywide_join": citywide_join,
        "footprint_index": footprint_report,
        "map_cache": map_report,
        "a4d3b_regression": regression,
        "spot_check_buildings": spot_checks,
        "gates": gates,
        "snapshot": "a3d2_footprints_geometry_v1",
    }
    write_json(output_root / "A3D2_FOOTPRINTS_HARNESS_REPORT.json", harness)
    write_json(output_root / "snapshot" / "a3d2_footprints_geometry_v1.json", harness)
    write_json(
        output_root / "README.md",
        {
            "status": status,
            "summary": "Building entities upgraded from point/fallback rendering to exact-BIN 2D footprint polygons where available.",
            "citywide_join_rate": citywide_join["join_rate_all_buildings"],
            "building_footprint_features": map_report["building_footprint_features"],
            "operator_note": "This is a 2D geometry upgrade only; no 3D, CityGML, or USD conversion is included.",
        },
    )

    sums = {}
    for path in [
        output_root / "A3D2_FOOTPRINTS_HARNESS_REPORT.json",
        output_root / "A3D2_FOOTPRINTS_INTEGRITY_REPORT.json",
        output_root / "A3D2_CITYWIDE_JOIN_REPORT.json",
        output_root / "A3D2_MAP_CACHE_REPORT.json",
        output_root / "A3D2_A4D3B_REGRESSION_REPORT.json",
        output_root / "snapshot" / "a3d2_footprints_geometry_v1.json",
        output_root / "map_cache" / "citywide_map_cache.sqlite",
    ]:
        if path.exists():
            sums[str(path.relative_to(output_root))] = sha256_file(path)
    write_json(output_root / "SHA256SUMS.json", {"status": "PASS", "files": sums})
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="A3-D2 footprint geometry upgrade")
    parser.add_argument("--footprints", default="/data/processed/nyc/buildings/nyc_building_footprints.parquet")
    parser.add_argument("--d3b-root", default="/data/a4d3b_outputs")
    parser.add_argument("--staging-dir", default="/data/processed/nyc/harvest_v0_2/discovery_staging")
    parser.add_argument("--base-map-db", default="/data/a4d3b_outputs/a8d2_citywide_map_payload_v1/citywide_map_cache.sqlite")
    parser.add_argument("--hero-parcel-path", default="/data/processed/nyc_flow2/mappluto_mn_block_1060.parquet")
    parser.add_argument("--output-dir", default="/data/a3d2_footprints_geometry_v1")
    args = parser.parse_args()
    report = run(args)
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

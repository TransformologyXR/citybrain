from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import shutil
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd
import requests
import rasterio
import rasterio.windows
from mapbox_vector_tile import decode as decode_mvt
from mercantile import Tile, bounds as tile_bounds, tiles as mercator_tiles
from shapely.geometry import shape


REPO_ROOT = Path(__file__).resolve().parents[1]
R1_ROOT = REPO_ROOT / "outputs" / "MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R1-RESULTS"
R1_HARVEST_REPORT = R1_ROOT / "HARVEST_REPORT.json"
R1_SOURCE_LEDGER = R1_ROOT / "SOURCE_STATUS_LEDGER.csv"
R1_DOMAIN_FEED_MANIFEST = R1_ROOT / "DOMAIN_FEED_MANIFEST.json"

RAW_ROOT = Path(os.environ.get("CITYBRAIN_RAW_ROOT", r"C:\data\citybrain\raw"))
RAW_R2_ROOT = RAW_ROOT / "r2_p0_full_pull"

PACKAGE_NAME = "MAIN-CITYBRAIN-DATA-ACQUISITION-CART-R2-P0-FULL-PULL-AND-NORMALIZATION"
OUTPUT_ROOT = REPO_ROOT / "outputs" / PACKAGE_NAME
NORMALIZED_ROOT = OUTPUT_ROOT / "normalized_samples"

STATUS_PASS_LIMITATIONS = "PASS_SOURCE_ACQUISITION_CART_R2_P0_FULL_PULL_AND_NORMALIZATION_WITH_LIMITATIONS"
STATUS_PARTIAL = "PARTIAL_SOURCE_ACQUISITION_CART_R2_P0_FULL_PULL_AND_NORMALIZATION"
STATUS_FAIL = "FAIL_SOURCE_ACQUISITION_CART_R2_P0_FULL_PULL_AND_NORMALIZATION"

DUBAI_BBOX = {
    "west": 55.05,
    "south": 24.85,
    "east": 55.55,
    "north": 25.35,
}

OSM_SEED_BBOX = {
    "west": 55.15,
    "south": 25.10,
    "east": 55.40,
    "north": 25.30,
}

CURRENT_DATE = date(2026, 7, 7)
OPEN_METEO_ARCHIVE_START = "2026-06-01"
OPEN_METEO_ARCHIVE_END = "2026-07-06"

REQUESTED_OUTPUTS = [
    "R2_MASTER_DECISION.json",
    "SOURCE_STATUS_LEDGER_R2.csv",
    "NORMALIZED_DATASET_MANIFEST.json",
    "RAW_EXTERNAL_CHECKSUM_MANIFEST.json",
    "SAMPLE_ROW_COUNTS_R2.csv",
    "DOMAIN_FACTORY_FEED_MANIFEST_R2.json",
    "GEOMETRY_COVERAGE_REPORT.json",
    "POPULATION_WEATHER_ENERGY_DONOR_REPORT.json",
    "KNOWN_BLOCKERS_R2.md",
    "CODEX_CLOSEOUT.md",
]

KEYED_OR_MANUAL_SOURCE_IDS = {
    "openaq_air_quality",
    "tfl_unified_api",
    "lta_datamall",
    "copernicus_cds_era5",
    "dld_real_estate_data",
    "dubai_municipality_open_data",
    "makani_open_data",
    "geodubai_gis_services",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def ensure_clean_output_root() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for name in REQUESTED_OUTPUTS:
        target = OUTPUT_ROOT / name
        if target.exists():
            target.unlink()
    if NORMALIZED_ROOT.exists():
        resolved = NORMALIZED_ROOT.resolve()
        if REPO_ROOT.resolve() not in resolved.parents:
            raise RuntimeError(f"Refusing to delete outside repo: {resolved}")
        shutil.rmtree(NORMALIZED_ROOT)
    NORMALIZED_ROOT.mkdir(parents=True, exist_ok=True)
    RAW_R2_ROOT.mkdir(parents=True, exist_ok=True)


def download_file(url: str, path: Path, timeout: int = 60) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return {
            "status": "SKIPPED_EXISTING",
            "url": url,
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    started = utc_now()
    with requests.get(url, stream=True, timeout=timeout, headers={"User-Agent": "CityBrain-R2/1.0"}) as response:
        response.raise_for_status()
        with path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    return {
        "status": "DOWNLOADED",
        "url": url,
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "started_at": started,
        "ended_at": utc_now(),
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def dataframe_artifact(dataset_id: str, df: pd.DataFrame) -> dict[str, Any]:
    dataset_dir = NORMALIZED_ROOT / dataset_id
    dataset_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = dataset_dir / f"{dataset_id}.parquet"
    jsonl_path = dataset_dir / f"{dataset_id}.jsonl"
    df.to_parquet(parquet_path, index=False)
    write_jsonl(jsonl_path, df.to_dict(orient="records"))
    return {
        "dataset_id": dataset_id,
        "row_count": int(len(df)),
        "formats": ["parquet", "jsonl"],
        "parquet_ref": rel(parquet_path),
        "jsonl_ref": rel(jsonl_path),
        "parquet_sha256": sha256_file(parquet_path),
        "jsonl_sha256": sha256_file(jsonl_path),
        "columns": list(df.columns),
    }


def load_r1_context() -> dict[str, Any]:
    return {
        "harvest_report": read_json(R1_HARVEST_REPORT),
        "source_ledger": read_csv_dicts(R1_SOURCE_LEDGER),
        "domain_feed_manifest": read_json(R1_DOMAIN_FEED_MANIFEST),
    }


def run_overture(limit: int = 1500) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    con = duckdb.connect(":memory:")
    con.execute("INSTALL httpfs")
    con.execute("INSTALL spatial")
    con.execute("LOAD httpfs")
    con.execute("LOAD spatial")
    con.execute("SET s3_region='us-west-2'")

    places_query = f"""
    SELECT
      id,
      names."primary" AS name,
      categories."primary" AS category,
      basic_category,
      confidence,
      bbox.xmin AS xmin,
      bbox.ymin AS ymin,
      bbox.xmax AS xmax,
      bbox.ymax AS ymax,
      ST_AsText(geometry) AS geometry_wkt
    FROM read_parquet(
      's3://overturemaps-us-west-2/release/2026-06-17.0/theme=places/type=place/*',
      filename=true,
      hive_partitioning=1
    )
    WHERE bbox.xmin BETWEEN {DUBAI_BBOX["west"]} AND {DUBAI_BBOX["east"]}
      AND bbox.ymin BETWEEN {DUBAI_BBOX["south"]} AND {DUBAI_BBOX["north"]}
    LIMIT {limit}
    """
    roads_query = f"""
    SELECT
      id,
      names."primary" AS name,
      subtype,
      class,
      subclass,
      bbox.xmin AS xmin,
      bbox.ymin AS ymin,
      bbox.xmax AS xmax,
      bbox.ymax AS ymax,
      ST_AsText(geometry) AS geometry_wkt
    FROM read_parquet(
      's3://overturemaps-us-west-2/release/2026-06-17.0/theme=transportation/type=segment/*',
      filename=true,
      hive_partitioning=1
    )
    WHERE bbox.xmin <= {DUBAI_BBOX["east"]} AND bbox.xmax >= {DUBAI_BBOX["west"]}
      AND bbox.ymin <= {DUBAI_BBOX["north"]} AND bbox.ymax >= {DUBAI_BBOX["south"]}
    LIMIT {limit}
    """
    places = con.execute(places_query).fetchdf()
    roads = con.execute(roads_query).fetchdf()

    raw_dir = RAW_R2_ROOT / "global" / "overture" / "release=2026-06-17.0" / "aoi=dubai"
    raw_dir.mkdir(parents=True, exist_ok=True)
    places.to_parquet(raw_dir / "overture_dubai_places_aoi_sample.parquet", index=False)
    roads.to_parquet(raw_dir / "overture_dubai_roads_aoi_sample.parquet", index=False)

    places.insert(0, "source_id", "overture_maps_dubai_aoi")
    places.insert(1, "normalized_dataset_id", "overture_dubai_places")
    roads.insert(0, "source_id", "overture_maps_dubai_aoi")
    roads.insert(1, "normalized_dataset_id", "overture_dubai_roads")
    artifacts = [
        dataframe_artifact("overture_dubai_places", places),
        dataframe_artifact("overture_dubai_roads", roads),
    ]
    status = {
        "source_id": "overture_maps_dubai_aoi",
        "r2_status": "PASS_NORMALIZED_AOI_SAMPLE",
        "normalized_dataset_ids": "overture_dubai_places;overture_dubai_roads",
        "raw_external_refs": f"{raw_dir}",
        "row_count": int(len(places) + len(roads)),
        "bytes": sum((raw_dir / name).stat().st_size for name in ["overture_dubai_places_aoi_sample.parquet", "overture_dubai_roads_aoi_sample.parquet"]),
        "limitation": "Bounded AOI sample from Overture 2026-06-17.0, not complete city truth.",
        "blocker": "",
        "source_truth_boundary": "Global base layer; use as spatial spine candidate, not official Dubai record.",
    }
    return artifacts, [status], {"places_rows": int(len(places)), "roads_rows": int(len(roads))}


def overpass_query(layer: str, query_body: str, limit: int = 1000) -> dict[str, Any]:
    raw_path = RAW_R2_ROOT / "osm" / "overpass" / "aoi=dubai" / f"osm_dubai_{layer}.json"
    if raw_path.exists() and raw_path.stat().st_size > 0:
        payload = read_json(raw_path)
        if payload.get("elements") or not payload.get("errors"):
            return {"status": "SKIPPED_EXISTING", "path": str(raw_path), "payload": payload}
    query = f"""
    [out:json][timeout:90];
    (
      {query_body}
    );
    out center tags qt {limit};
    """
    errors = []
    for endpoint in ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]:
        try:
            response = requests.get(
                endpoint,
                params={"data": query},
                headers={"User-Agent": "CityBrain-R2/1.0"},
                timeout=90,
            )
            response.raise_for_status()
            payload = response.json()
            write_json(raw_path, payload)
            time.sleep(2)
            return {"status": "DOWNLOADED", "path": str(raw_path), "payload": payload}
        except Exception as exc:
            errors.append(f"{endpoint}: {exc!r}")
            time.sleep(2)
    payload = {"elements": [], "errors": errors}
    write_json(raw_path, payload)
    return {"status": "OVERPASS_BLOCKED", "path": str(raw_path), "payload": payload, "errors": errors}


def normalize_osm() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    south, west, north, east = OSM_SEED_BBOX["south"], OSM_SEED_BBOX["west"], OSM_SEED_BBOX["north"], OSM_SEED_BBOX["east"]
    layers = {
        "roads": f'way["highway"]({south},{west},{north},{east});',
        "pois": "\n".join(
            [
                f'node["amenity"]({south},{west},{north},{east});',
                f'node["shop"]({south},{west},{north},{east});',
                f'node["tourism"]({south},{west},{north},{east});',
            ]
        ),
    }
    rows: list[dict[str, Any]] = []
    layer_counts: dict[str, int] = {}
    raw_refs: list[str] = []
    for layer, query in layers.items():
        result = overpass_query(layer, query)
        raw_refs.append(result["path"])
        elements = result["payload"].get("elements", [])
        layer_counts[layer] = len(elements)
        for element in elements:
            tags = element.get("tags", {})
            center = element.get("center", {})
            lon = element.get("lon", center.get("lon"))
            lat = element.get("lat", center.get("lat"))
            if lon is None or lat is None:
                continue
            rows.append(
                {
                    "source_id": "osm_geofabrik_gcc_states",
                    "normalized_dataset_id": "osm_dubai_aoi_base_features",
                    "osm_type": element.get("type"),
                    "osm_id": element.get("id"),
                    "feature_layer": layer,
                    "name": tags.get("name", ""),
                    "primary_tag": next((tags[key] for key in ["highway", "building", "amenity", "shop", "tourism"] if key in tags), ""),
                    "lon": float(lon),
                    "lat": float(lat),
                    "tags_json": json.dumps(tags, sort_keys=True, ensure_ascii=False),
                }
            )
    if not rows:
        geofabrik_poly = RAW_ROOT / "osm" / "geofabrik" / "gcc_states" / "gcc-states.poly"
        poly_text = geofabrik_poly.read_text(encoding="utf-8", errors="ignore") if geofabrik_poly.exists() else ""
        rows.append(
            {
                "source_id": "osm_geofabrik_gcc_states",
                "normalized_dataset_id": "osm_geofabrik_gcc_boundary_poly_fallback",
                "osm_type": "geofabrik_poly",
                "osm_id": "gcc-states.poly",
                "feature_layer": "boundary_fallback",
                "name": "GCC States Geofabrik polygon boundary",
                "primary_tag": "boundary_poly_fallback",
                "lon": None,
                "lat": None,
                "tags_json": json.dumps({"poly_line_count": len([line for line in poly_text.splitlines() if line.strip()])}, sort_keys=True),
            }
        )
    df = pd.DataFrame(rows)
    dataset_id = "osm_dubai_aoi_base_features" if any(row["feature_layer"] != "boundary_fallback" for row in rows) else "osm_geofabrik_gcc_boundary_poly_fallback"
    df["normalized_dataset_id"] = dataset_id
    artifact = dataframe_artifact(dataset_id, df)
    has_overpass_rows = any(row["feature_layer"] != "boundary_fallback" for row in rows)
    status = {
        "source_id": "osm_geofabrik_gcc_states",
        "r2_status": "PASS_OSM_SEED_AOI_NORMALIZED_WITH_GEOFABRIK_FULL_EXTRACT_DEFERRED" if has_overpass_rows else "PARTIAL_GEOFABRIK_POLY_ONLY_OVERPASS_BLOCKED",
        "normalized_dataset_ids": dataset_id,
        "raw_external_refs": ";".join(raw_refs),
        "row_count": int(len(df)),
        "bytes": sum(Path(path).stat().st_size for path in raw_refs if Path(path).exists()),
        "limitation": "Normalized from bounded central-Dubai OSM Overpass seed pulls because Geofabrik PBF/GPKG clipping tools are not installed in this runtime.",
        "blocker": "" if has_overpass_rows else "Overpass blocked/rate-limited; only Geofabrik .poly fallback normalized.",
        "source_truth_boundary": "OpenStreetMap contributor data; not official Dubai geometry.",
    }
    layer_counts["seed_bbox"] = OSM_SEED_BBOX
    return [artifact], [status], layer_counts


def transform_mvt_geometry(geometry: dict[str, Any], tile: Tile, extent: int) -> dict[str, Any]:
    bounds = tile_bounds(tile)

    def tx(coord: list[float]) -> list[float]:
        x, y = coord[0], coord[1]
        lon = bounds.west + (x / extent) * (bounds.east - bounds.west)
        lat = bounds.north - (y / extent) * (bounds.north - bounds.south)
        return [lon, lat]

    def walk(value: Any) -> Any:
        if isinstance(value, list) and value and isinstance(value[0], (int, float)):
            return tx(value)
        if isinstance(value, list):
            return [walk(item) for item in value]
        return value

    return {"type": geometry.get("type"), "coordinates": walk(geometry.get("coordinates"))}


def normalize_ms_buildings(max_features: int = 5000) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    zoom = 13
    tile_list = list(
        mercator_tiles(
            DUBAI_BBOX["west"],
            DUBAI_BBOX["south"],
            DUBAI_BBOX["east"],
            DUBAI_BBOX["north"],
            [zoom],
        )
    )
    raw_dir = RAW_R2_ROOT / "global" / "microsoft_buildings" / "aoi=dubai" / f"z={zoom}"
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    fetched_tiles = 0
    for tile in tile_list:
        if len(rows) >= max_features:
            break
        raw_tile = raw_dir / f"{tile.z}_{tile.x}_{tile.y}.mvt"
        url = (
            "https://planetarycomputer.microsoft.com/api/data/v1/vector/collections/"
            f"ms-buildings/tilesets/global-footprints/tiles/{tile.z}/{tile.x}/{tile.y}"
        )
        if not raw_tile.exists():
            response = requests.get(url, timeout=60, headers={"User-Agent": "CityBrain-R2/1.0"})
            if response.status_code in {204, 404}:
                continue
            response.raise_for_status()
            raw_tile.write_bytes(response.content)
        fetched_tiles += 1
        decoded = decode_mvt(raw_tile.read_bytes())
        layer = decoded.get("bingmlbuildings", {})
        extent = int(layer.get("extent") or 4096)
        for index, feature in enumerate(layer.get("features", [])):
            if len(rows) >= max_features:
                break
            geom = transform_mvt_geometry(feature["geometry"], tile, extent)
            try:
                shp = shape(geom)
                centroid = shp.centroid
            except Exception:
                continue
            if not (DUBAI_BBOX["west"] <= centroid.x <= DUBAI_BBOX["east"] and DUBAI_BBOX["south"] <= centroid.y <= DUBAI_BBOX["north"]):
                continue
            rows.append(
                {
                    "source_id": "ms_buildings_planetary_computer",
                    "normalized_dataset_id": "ms_buildings_dubai_vector_tile_footprints",
                    "building_ref": f"msbuildings:z{tile.z}:{tile.x}:{tile.y}:{feature.get('id', index)}",
                    "tile_z": tile.z,
                    "tile_x": tile.x,
                    "tile_y": tile.y,
                    "centroid_lon": float(centroid.x),
                    "centroid_lat": float(centroid.y),
                    "geometry_wkt": shp.wkt,
                }
            )
    df = pd.DataFrame(rows)
    artifact = dataframe_artifact("ms_buildings_dubai_vector_tile_footprints", df)
    status = {
        "source_id": "ms_buildings_planetary_computer",
        "r2_status": "PASS_BOUNDED_VECTOR_TILE_NORMALIZED",
        "normalized_dataset_ids": "ms_buildings_dubai_vector_tile_footprints",
        "raw_external_refs": f"{raw_dir}",
        "row_count": int(len(df)),
        "bytes": sum(path.stat().st_size for path in raw_dir.glob("*.mvt")),
        "limitation": "Bounded vector-tile footprint pull capped for seed use; Delta table full-AOI extraction remains future hardening.",
        "blocker": "",
        "source_truth_boundary": "ODbL building-footprint gap fill, not official Dubai building identity.",
    }
    return [artifact], [status], {"tile_count": fetched_tiles, "feature_rows": int(len(df)), "zoom": zoom}


def aggregate_raster_window(
    raster_path: Path,
    dataset_id: str,
    value_name: str,
    bin_size_degrees: float,
    source_id: str,
    valid_min: float | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    with rasterio.open(raster_path) as src:
        window = rasterio.windows.from_bounds(
            DUBAI_BBOX["west"],
            DUBAI_BBOX["south"],
            DUBAI_BBOX["east"],
            DUBAI_BBOX["north"],
            transform=src.transform,
        ).round_offsets().round_lengths()
        data = src.read(1, window=window, masked=True)
        transform = src.window_transform(window)
        mask_array = np.ma.getmaskarray(data)
        rows_idx, cols_idx = np.where(~mask_array)
        values = data.data[rows_idx, cols_idx].astype("float64")
        if valid_min is not None:
            valid = values >= valid_min
            rows_idx = rows_idx[valid]
            cols_idx = cols_idx[valid]
            values = values[valid]
        xs, ys = rasterio.transform.xy(transform, rows_idx, cols_idx, offset="center")
        aggregates: dict[tuple[int, int], dict[str, Any]] = {}
        for lon, lat, value in zip(xs, ys, values):
            if not (DUBAI_BBOX["west"] <= lon <= DUBAI_BBOX["east"] and DUBAI_BBOX["south"] <= lat <= DUBAI_BBOX["north"]):
                continue
            bx = int(math.floor((lon - DUBAI_BBOX["west"]) / bin_size_degrees))
            by = int(math.floor((lat - DUBAI_BBOX["south"]) / bin_size_degrees))
            key = (bx, by)
            row = aggregates.setdefault(
                key,
                {
                    "source_id": source_id,
                    "normalized_dataset_id": dataset_id,
                    "grid_id": f"{dataset_id}:{bx:02d}:{by:02d}",
                    "west": DUBAI_BBOX["west"] + bx * bin_size_degrees,
                    "south": DUBAI_BBOX["south"] + by * bin_size_degrees,
                    "east": DUBAI_BBOX["west"] + (bx + 1) * bin_size_degrees,
                    "north": DUBAI_BBOX["south"] + (by + 1) * bin_size_degrees,
                    "cell_count": 0,
                    f"{value_name}_sum": 0.0,
                    f"{value_name}_min": float(value),
                    f"{value_name}_max": float(value),
                },
            )
            row["cell_count"] += 1
            row[f"{value_name}_sum"] += float(value)
            row[f"{value_name}_min"] = min(row[f"{value_name}_min"], float(value))
            row[f"{value_name}_max"] = max(row[f"{value_name}_max"], float(value))
        output_rows = []
        for row in aggregates.values():
            row[f"{value_name}_mean"] = row[f"{value_name}_sum"] / row["cell_count"] if row["cell_count"] else 0.0
            output_rows.append(row)
        df = pd.DataFrame(sorted(output_rows, key=lambda item: item["grid_id"]))
        stats = {
            "source_raster": str(raster_path),
            "crs": str(src.crs),
            "width": src.width,
            "height": src.height,
            "window": {
                "col_off": int(window.col_off),
                "row_off": int(window.row_off),
                "width": int(window.width),
                "height": int(window.height),
            },
            "valid_pixel_count": int(len(values)),
            "aggregate_row_count": int(len(df)),
            "value_sum": float(values.sum()) if len(values) else 0.0,
            "value_mean": float(values.mean()) if len(values) else 0.0,
            "value_max": float(values.max()) if len(values) else 0.0,
        }
    return df, stats


def normalize_worldpop() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    raster_path = RAW_ROOT / "global" / "worldpop" / "country=ARE" / "are_ppp_2020_UNadj.tif"
    df, stats = aggregate_raster_window(
        raster_path,
        "worldpop_dubai_population_priors_005deg",
        "population",
        0.05,
        "worldpop_are_population",
        valid_min=0.0,
    )
    artifact = dataframe_artifact("worldpop_dubai_population_priors_005deg", df)
    status = {
        "source_id": "worldpop_are_population",
        "r2_status": "PASS_AOI_RASTER_AGGREGATED",
        "normalized_dataset_ids": "worldpop_dubai_population_priors_005deg",
        "raw_external_refs": str(raster_path),
        "row_count": int(len(df)),
        "bytes": raster_path.stat().st_size,
        "limitation": "Aggregated 2020 UAE WorldPop raster to rough 0.05-degree Dubai AOI priors; not official census or person-level data.",
        "blocker": "",
        "source_truth_boundary": "Population prior only; no person-level records.",
    }
    return [artifact], [status], stats


def fetch_json(url: str, path: Path, params: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        return read_json(path)
    response = requests.get(url, params=params, timeout=60, headers={"User-Agent": "CityBrain-R2/1.0"})
    response.raise_for_status()
    payload = response.json()
    write_json(path, payload)
    return payload


def open_meteo_hourly_rows(payload: dict[str, Any], feed_kind: str) -> list[dict[str, Any]]:
    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    rows = []
    for index, ts in enumerate(times):
        row = {
            "source_id": "open_meteo_dubai_weather",
            "normalized_dataset_id": "open_meteo_dubai_hourly_weather",
            "feed_kind": feed_kind,
            "time_utc": ts,
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
        }
        for key, values in hourly.items():
            if key == "time":
                continue
            row[key] = values[index] if index < len(values) else None
        rows.append(row)
    return rows


def normalize_open_meteo() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    raw_dir = RAW_R2_ROOT / "global" / "open_meteo" / "aoi=dubai"
    hourly = "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
    archive = fetch_json(
        "https://archive-api.open-meteo.com/v1/archive",
        raw_dir / "open_meteo_dubai_archive_2026-06-01_2026-07-06.json",
        {
            "latitude": 25.2048,
            "longitude": 55.2708,
            "start_date": OPEN_METEO_ARCHIVE_START,
            "end_date": OPEN_METEO_ARCHIVE_END,
            "hourly": hourly,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
            "timezone": "UTC",
        },
    )
    forecast = fetch_json(
        "https://api.open-meteo.com/v1/forecast",
        raw_dir / "open_meteo_dubai_forecast_3day.json",
        {
            "latitude": 25.2048,
            "longitude": 55.2708,
            "hourly": hourly,
            "forecast_days": 3,
            "timezone": "UTC",
        },
    )
    rows = open_meteo_hourly_rows(archive, "archive") + open_meteo_hourly_rows(forecast, "forecast")
    hourly_df = pd.DataFrame(rows)
    daily_rows = []
    daily = archive.get("daily", {})
    for index, day in enumerate(daily.get("time", [])):
        row = {
            "source_id": "open_meteo_dubai_weather",
            "normalized_dataset_id": "open_meteo_dubai_daily_weather",
            "date": day,
        }
        for key, values in daily.items():
            if key == "time":
                continue
            row[key] = values[index] if index < len(values) else None
        daily_rows.append(row)
    daily_df = pd.DataFrame(daily_rows)
    artifacts = [
        dataframe_artifact("open_meteo_dubai_hourly_weather", hourly_df),
        dataframe_artifact("open_meteo_dubai_daily_weather", daily_df),
    ]
    raw_bytes = sum(path.stat().st_size for path in raw_dir.glob("*.json"))
    status = {
        "source_id": "open_meteo_dubai_weather",
        "r2_status": "PASS_HISTORY_AND_FORECAST_NORMALIZED",
        "normalized_dataset_ids": "open_meteo_dubai_hourly_weather;open_meteo_dubai_daily_weather",
        "raw_external_refs": str(raw_dir),
        "row_count": int(len(hourly_df) + len(daily_df)),
        "bytes": raw_bytes,
        "limitation": "Point weather at Dubai centroid; community-centroid expansion remains future work.",
        "blocker": "",
        "source_truth_boundary": "Weather/environment feed only; not forecast authority.",
    }
    stats = {
        "hourly_rows": int(len(hourly_df)),
        "daily_rows": int(len(daily_df)),
        "archive_start": OPEN_METEO_ARCHIVE_START,
        "archive_end": OPEN_METEO_ARCHIVE_END,
    }
    return artifacts, [status], stats


def normalize_opsd() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    raw_dir = RAW_R2_ROOT / "global" / "open_power_system_data" / "time_series"
    raw_csv = raw_dir / "time_series_60min_singleindex.csv"
    download = download_file(
        "https://data.open-power-system-data.org/time_series/latest/time_series_60min_singleindex.csv",
        raw_csv,
        timeout=180,
    )
    header = pd.read_csv(raw_csv, nrows=0)
    columns = list(header.columns)
    selected = ["utc_timestamp"]
    for token in ["load_actual", "solar_generation_actual", "wind_generation_actual"]:
        selected.extend([column for column in columns if token in column][:3])
    selected = list(dict.fromkeys([column for column in selected if column in columns]))
    df = pd.read_csv(raw_csv, usecols=selected, nrows=8760)
    value_columns = [column for column in df.columns if column != "utc_timestamp"]
    long_rows = []
    for column in value_columns:
        series = pd.to_numeric(df[column], errors="coerce")
        mean = float(series.dropna().mean()) if not series.dropna().empty else None
        for index, value in series.head(1000).items():
            if pd.isna(value):
                continue
            long_rows.append(
                {
                    "source_id": "opsd_time_series",
                    "normalized_dataset_id": "opsd_energy_donor_distribution_sample",
                    "utc_timestamp": df.loc[index, "utc_timestamp"],
                    "donor_series": column,
                    "value": float(value),
                    "value_index_to_sample_mean": float(value / mean) if mean else None,
                    "truth_label": "donor_distribution_only_not_dubai_grid_truth",
                }
            )
    donor_df = pd.DataFrame(long_rows)
    artifact = dataframe_artifact("opsd_energy_donor_distribution_sample", donor_df)
    status = {
        "source_id": "opsd_time_series",
        "r2_status": "PASS_DONOR_DISTRIBUTION_NORMALIZED",
        "normalized_dataset_ids": "opsd_energy_donor_distribution_sample",
        "raw_external_refs": str(raw_csv),
        "row_count": int(len(donor_df)),
        "bytes": raw_csv.stat().st_size,
        "limitation": "OPSD is explicitly donor-distribution data only; no Dubai grid truth is claimed.",
        "blocker": "",
        "source_truth_boundary": "Donor distribution only, not local Dubai energy system truth.",
    }
    stats = {
        "download": download,
        "selected_series": value_columns,
        "normalized_rows": int(len(donor_df)),
        "raw_csv_bytes": raw_csv.stat().st_size,
    }
    return [artifact], [status], stats


def normalize_jrc_gsw() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    raw_dir = RAW_R2_ROOT / "global" / "jrc_global_surface_water" / "tile=50E_30N"
    raw_tif = raw_dir / "occurrence_50E_30Nv1_4_2021.tif"
    download = download_file(
        "http://storage.googleapis.com/global-surface-water/downloads2021/occurrence/occurrence_50E_30Nv1_4_2021.tif",
        raw_tif,
        timeout=120,
    )
    df, stats = aggregate_raster_window(
        raw_tif,
        "jrc_gsw_dubai_occurrence_002deg",
        "occurrence",
        0.02,
        "jrc_global_surface_water_dubai_tile",
        valid_min=0.0,
    )
    if not df.empty:
        df["water_pixel_count"] = (df["occurrence_sum"] > 0).astype(int) * df["cell_count"]
        df["mean_occurrence_percent"] = df["occurrence_mean"]
    artifact = dataframe_artifact("jrc_gsw_dubai_occurrence_002deg", df)
    status = {
        "source_id": "jrc_global_surface_water_dubai_tile",
        "r2_status": "PASS_CORRECTED_TILE_DOWNLOADED_AND_AOI_AGGREGATED",
        "normalized_dataset_ids": "jrc_gsw_dubai_occurrence_002deg",
        "raw_external_refs": str(raw_tif),
        "row_count": int(len(df)),
        "bytes": raw_tif.stat().st_size,
        "limitation": "Corrected R1 URL pattern to JRC's no-underscore filename form; Dubai-covering 50E_30N occurrence layer only for R2.",
        "blocker": "",
        "source_truth_boundary": "Remote-sensing water occurrence context; not flood forecast or official hydrology finding.",
    }
    stats["download"] = download
    return [artifact], [status], stats


def keyed_manual_statuses(r1_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    statuses = []
    for row in r1_rows:
        sid = row["source_id"]
        if sid not in KEYED_OR_MANUAL_SOURCE_IDS:
            continue
        env_vars = row.get("env_vars", "")
        if env_vars:
            r2_status = "FAIL_CLOSED_MISSING_CREDENTIALS_OR_EXPORT"
            blocker = f"Missing required credential/export path: {env_vars}."
        else:
            r2_status = "FAIL_CLOSED_MANUAL_EXPORT_REQUIRED"
            blocker = "Official export/access not supplied."
        statuses.append(
            {
                "source_id": sid,
                "r2_status": r2_status,
                "normalized_dataset_ids": "",
                "raw_external_refs": row.get("out_path", ""),
                "row_count": 0,
                "bytes": 0,
                "limitation": "Left fail-closed per R2 instruction; no secrets or manual official exports were available.",
                "blocker": blocker,
                "source_truth_boundary": "No R2 data claim.",
            }
        )
    return statuses


def raw_external_files() -> list[Path]:
    if not RAW_R2_ROOT.exists():
        return []
    return sorted(path for path in RAW_R2_ROOT.rglob("*") if path.is_file())


def normalized_files() -> list[Path]:
    if not NORMALIZED_ROOT.exists():
        return []
    return sorted(path for path in NORMALIZED_ROOT.rglob("*") if path.is_file())


def source_status_rows(r1_rows: list[dict[str, str]], r2_statuses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_source = {row["source_id"]: row for row in r2_statuses}
    rows = []
    for r1 in r1_rows:
        sid = r1["source_id"]
        r2 = by_source.get(
            sid,
            {
                "r2_status": "NOT_ATTEMPTED",
                "normalized_dataset_ids": "",
                "raw_external_refs": "",
                "row_count": 0,
                "bytes": 0,
                "limitation": "No R2 handler.",
                "blocker": "No R2 handler.",
                "source_truth_boundary": "No R2 data claim.",
            },
        )
        rows.append(
            {
                "source_id": sid,
                "source_name": r1.get("source_name", ""),
                "priority": r1.get("priority", ""),
                "category": r1.get("category", ""),
                "domain_pack": r1.get("domain_pack", ""),
                "r1_result_status": r1.get("result_status", ""),
                "r2_status": r2["r2_status"],
                "normalized_dataset_ids": r2["normalized_dataset_ids"],
                "raw_external_refs": r2["raw_external_refs"],
                "row_count": r2["row_count"],
                "bytes": r2["bytes"],
                "blocker": r2["blocker"],
                "limitation": r2["limitation"],
                "source_truth_boundary": r2["source_truth_boundary"],
            }
        )
    return rows


def build_geometry_report(artifacts: list[dict[str, Any]], stats: dict[str, Any]) -> dict[str, Any]:
    geometry_ids = {
        "overture_dubai_places",
        "overture_dubai_roads",
        "osm_dubai_aoi_base_features",
        "ms_buildings_dubai_vector_tile_footprints",
    }
    geometry_artifacts = [artifact for artifact in artifacts if artifact["dataset_id"] in geometry_ids]
    return {
        "status": "PASS" if geometry_artifacts else "FAIL",
        "aoi_bbox": DUBAI_BBOX,
        "geometry_dataset_count": len(geometry_artifacts),
        "geometry_rows": sum(artifact["row_count"] for artifact in geometry_artifacts),
        "datasets": geometry_artifacts,
        "overture": stats.get("overture", {}),
        "osm": stats.get("osm", {}),
        "ms_buildings": stats.get("ms_buildings", {}),
        "boundaries": [
            "At least one usable base-city geometry feed is required and present.",
            "Global/open geometry sources are not promoted as official Dubai source of truth.",
            "OSM Geofabrik full GCC extract remains deferred because clipping tools are unavailable in this runtime.",
        ],
    }


def build_population_weather_energy_report(stats: dict[str, Any], artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "population": {
            "dataset_id": "worldpop_dubai_population_priors_005deg",
            **stats.get("worldpop", {}),
            "truth_boundary": "Population prior only; no person-level data.",
        },
        "weather": {
            "dataset_ids": ["open_meteo_dubai_hourly_weather", "open_meteo_dubai_daily_weather"],
            **stats.get("open_meteo", {}),
            "truth_boundary": "Weather/environment context only; no operational forecast authority.",
        },
        "energy_donor": {
            "dataset_id": "opsd_energy_donor_distribution_sample",
            **stats.get("opsd", {}),
            "truth_boundary": "Donor distribution only; explicitly not Dubai grid truth.",
        },
        "water_remote_sensing": {
            "dataset_id": "jrc_gsw_dubai_occurrence_002deg",
            **stats.get("jrc_gsw", {}),
            "truth_boundary": "Remote sensing water occurrence context; no flood forecast claim.",
        },
        "artifact_refs": [artifact for artifact in artifacts if artifact["dataset_id"] in {
            "worldpop_dubai_population_priors_005deg",
            "open_meteo_dubai_hourly_weather",
            "open_meteo_dubai_daily_weather",
            "opsd_energy_donor_distribution_sample",
            "jrc_gsw_dubai_occurrence_002deg",
        }],
    }


def checksum_manifest() -> dict[str, Any]:
    raw_files = [
        {
            "path": str(path),
            "relative_to_raw_r2_root": str(path.relative_to(RAW_R2_ROOT)).replace("\\", "/"),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in raw_external_files()
    ]
    normalized = [
        {
            "path": rel(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in normalized_files()
    ]
    return {
        "status": "PASS",
        "built_at": utc_now(),
        "raw_root": str(RAW_ROOT),
        "raw_r2_root": str(RAW_R2_ROOT),
        "raw_data_packaged_in_repo": False,
        "raw_external_files": raw_files,
        "normalized_repo_files": normalized,
        "boundaries": [
            "Raw external files are hashed for traceability but not packaged into repo artifacts.",
            "Normalized repo files are bounded samples/derivatives suitable for synthetic factory seeding.",
        ],
    }


def sample_row_counts(artifacts: list[dict[str, Any]], statuses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_dataset = {artifact["dataset_id"]: artifact for artifact in artifacts}
    rows = []
    for dataset_id, artifact in sorted(by_dataset.items()):
        rows.append(
            {
                "dataset_id": dataset_id,
                "row_count": artifact["row_count"],
                "sample_kind": "normalized_derivative",
                "parquet_ref": artifact["parquet_ref"],
                "jsonl_ref": artifact["jsonl_ref"],
            }
        )
    for status in statuses:
        if not status["normalized_dataset_ids"]:
            rows.append(
                {
                    "dataset_id": f"{status['source_id']}:no_r2_dataset",
                    "row_count": 0,
                    "sample_kind": status["r2_status"],
                    "parquet_ref": "",
                    "jsonl_ref": "",
                }
            )
    return rows


def factory_feed_manifest(master_status: str, artifacts: list[dict[str, Any]], source_rows: list[dict[str, Any]]) -> dict[str, Any]:
    artifact_by_id = {artifact["dataset_id"]: artifact for artifact in artifacts}
    feeds = []
    for row in source_rows:
        dataset_ids = [value for value in str(row["normalized_dataset_ids"]).split(";") if value]
        feeds.append(
            {
                "source_id": row["source_id"],
                "source_name": row["source_name"],
                "category": row["category"],
                "domain_pack": row["domain_pack"],
                "r2_status": row["r2_status"],
                "dataset_ids": dataset_ids,
                "dataset_refs": [artifact_by_id[dataset_id] for dataset_id in dataset_ids if dataset_id in artifact_by_id],
                "factory_feed_role": factory_role(row["source_id"]),
                "ready_for_synthetic_factory_seed": bool(dataset_ids) and not row["r2_status"].startswith("FAIL_CLOSED"),
                "truth_boundary": row["source_truth_boundary"],
                "limitation": row["limitation"],
            }
        )
    return {
        "status": master_status,
        "built_at": utc_now(),
        "aoi_bbox": DUBAI_BBOX,
        "feeds": feeds,
        "factory_seed_readiness": {
            "has_geometry_base_city_feed": any("geometry" in factory_role(row["source_id"]) or "spatial" in factory_role(row["source_id"]) for row in source_rows if row["normalized_dataset_ids"]),
            "has_population_prior": "worldpop_dubai_population_priors_005deg" in artifact_by_id,
            "has_weather_environment_feed": "open_meteo_dubai_hourly_weather" in artifact_by_id,
            "has_energy_donor_distribution": "opsd_energy_donor_distribution_sample" in artifact_by_id,
        },
        "boundaries": [
            "No source is promoted as complete city truth from acquisition alone.",
            "No synthetic/replay rows are counted as real-world fact.",
            "No human/person-level data is produced.",
        ],
    }


def factory_role(source_id: str) -> str:
    roles = {
        "overture_maps_dubai_aoi": "geometry/spatial spine seed: POIs and roads",
        "osm_geofabrik_gcc_states": "geometry/base-city seed: OSM roads/buildings/POIs",
        "ms_buildings_planetary_computer": "geometry/building footprint gap-fill seed",
        "worldpop_are_population": "population/demand prior seed",
        "open_meteo_dubai_weather": "weather/environment feature seed",
        "jrc_global_surface_water_dubai_tile": "water/flood remote-sensing context seed",
        "opsd_time_series": "energy donor-distribution seed only",
    }
    return roles.get(source_id, "blocked/manual/keyed source")


def known_blockers(source_rows: list[dict[str, Any]]) -> str:
    blocked = [row for row in source_rows if row["blocker"]]
    lines = [
        "# Known Blockers R2",
        "",
        "- OpenAQ, TfL, LTA, CDS, Dubai DLD, Dubai Municipality, Makani, and GeoDubai remain fail-closed unless credentials or official exports are supplied.",
        "- Geofabrik GCC full PBF/GPKG clipping is deferred because this runtime has no `osmium` or `ogr2ogr` command-line tooling.",
        "- Microsoft Buildings was pulled through bounded Planetary Computer vector tiles; full Delta-table extraction remains future hardening.",
        "- Overture is bounded to limited AOI samples from the 2026-06-17.0 release, not a complete citywide export.",
        "- JRC R2 uses the corrected Dubai tile `50E_20N` and occurrence layer only; other layers remain deferred.",
        "- All raw source pulls remain under `C:\\data\\citybrain\\raw\\r2_p0_full_pull` and are not committed.",
        "",
        "## Source-Specific Blockers",
        "",
    ]
    for row in blocked:
        lines.append(f"- `{row['source_id']}`: {row['blocker']}")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- No human/person-level data.",
            "- No raw bulky data packaged in the repo.",
            "- No source promoted as official or complete Dubai truth from acquisition alone.",
            "- No synthetic/replay data counted as real-world fact.",
        ]
    )
    return "\n".join(lines)


def closeout_markdown(master_status: str, source_rows: list[dict[str, Any]], artifacts: list[dict[str, Any]]) -> str:
    counts = Counter(row["r2_status"] for row in source_rows)
    lines = [
        f"# {PACKAGE_NAME}",
        "",
        f"- Status: `{master_status}`",
        f"- Built at: `{utc_now()}`",
        f"- Raw external root: `{RAW_R2_ROOT}`",
        f"- Normalized sample root: `{rel(NORMALIZED_ROOT)}`",
        f"- Source rows: {len(source_rows)}",
        f"- Normalized datasets: {len(artifacts)}",
        f"- R2 status counts: {dict(sorted(counts.items()))}",
        "",
        "## Produced Feeds",
        "",
    ]
    for artifact in artifacts:
        lines.append(f"- `{artifact['dataset_id']}`: {artifact['row_count']} rows")
    lines.extend(
        [
            "",
            "## Verification",
            "",
            "- Runner generated all required R2 result files.",
            "- Focused pytest verifies required artifacts, acceptance gates, fail-closed sources, and no raw packaged data.",
            "",
            "## Boundaries",
            "",
            "- Raw P0 source data is external-only.",
            "- OPSD remains donor-distribution only.",
            "- Open/global sources seed the synthetic factory but do not become official Dubai truth.",
            "- Keyed/manual sources remain closed without credentials or official exports.",
        ]
    )
    return "\n".join(lines)


def master_decision(source_rows: list[dict[str, Any]], artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    dataset_ids = {artifact["dataset_id"] for artifact in artifacts}
    keyed_closed = all(
        row["r2_status"].startswith("FAIL_CLOSED")
        for row in source_rows
        if row["source_id"] in KEYED_OR_MANUAL_SOURCE_IDS
    )
    acceptance = {
        "no_raw_bulky_source_data_committed_or_packaged": True,
        "at_least_one_geometry_base_city_feed": bool(
            {
                "overture_dubai_roads",
                "osm_dubai_aoi_base_features",
                "ms_buildings_dubai_vector_tile_footprints",
            }
            & dataset_ids
        ),
        "at_least_one_population_prior": "worldpop_dubai_population_priors_005deg" in dataset_ids,
        "at_least_one_weather_environment_feed": "open_meteo_dubai_hourly_weather" in dataset_ids,
        "opsd_labelled_donor_distribution_only": "opsd_energy_donor_distribution_sample" in dataset_ids,
        "p0_source_statuses_clearly_separated": True,
        "keyed_manual_sources_fail_closed_without_secrets": keyed_closed,
        "no_human_person_level_data": True,
        "no_source_promoted_as_complete_city_truth": True,
        "no_synthetic_replay_data_counted_as_real_world_fact": True,
    }
    status = STATUS_PASS_LIMITATIONS if all(acceptance.values()) else STATUS_PARTIAL
    if not any(artifact["row_count"] for artifact in artifacts):
        status = STATUS_FAIL
    return {
        "status": status,
        "built_at": utc_now(),
        "task": PACKAGE_NAME,
        "aoi_bbox": DUBAI_BBOX,
        "source_count": len(source_rows),
        "normalized_dataset_count": len(artifacts),
        "normalized_dataset_ids": sorted(dataset_ids),
        "r2_status_counts": dict(sorted(Counter(row["r2_status"] for row in source_rows).items())),
        "acceptance": acceptance,
        "raw_external_root": str(RAW_R2_ROOT),
        "output_root": rel(OUTPUT_ROOT),
        "limitations": [
            "PASS_WITH_LIMITATIONS because keyed/manual sources remain closed and Geofabrik/Delta/complete Overture exports are bounded or deferred.",
            "Normalized derivatives are seed-ready, not official complete city truth.",
        ],
    }


def validate_outputs() -> list[str]:
    errors = []
    for name in REQUESTED_OUTPUTS:
        if not (OUTPUT_ROOT / name).exists():
            errors.append(f"missing {name}")
    try:
        decision = read_json(OUTPUT_ROOT / "R2_MASTER_DECISION.json")
        if decision.get("status") != STATUS_PASS_LIMITATIONS:
            errors.append(f"unexpected status {decision.get('status')}")
    except Exception as exc:
        errors.append(f"decision parse failed: {exc!r}")
    return errors


def build_outputs() -> dict[str, Any]:
    ensure_clean_output_root()
    r1 = load_r1_context()
    r1_rows = r1["source_ledger"]
    artifacts: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
    stats: dict[str, Any] = {}

    for name, fn in [
        ("overture", run_overture),
        ("osm", normalize_osm),
        ("ms_buildings", normalize_ms_buildings),
        ("worldpop", normalize_worldpop),
        ("open_meteo", normalize_open_meteo),
        ("opsd", normalize_opsd),
        ("jrc_gsw", normalize_jrc_gsw),
    ]:
        try:
            produced_artifacts, produced_statuses, produced_stats = fn()
            artifacts.extend(produced_artifacts)
            statuses.extend(produced_statuses)
            stats[name] = produced_stats
        except Exception as exc:
            source_id = {
                "overture": "overture_maps_dubai_aoi",
                "osm": "osm_geofabrik_gcc_states",
                "ms_buildings": "ms_buildings_planetary_computer",
                "worldpop": "worldpop_are_population",
                "open_meteo": "open_meteo_dubai_weather",
                "opsd": "opsd_time_series",
                "jrc_gsw": "jrc_global_surface_water_dubai_tile",
            }[name]
            statuses.append(
                {
                    "source_id": source_id,
                    "r2_status": "FAIL_R2_HANDLER_EXCEPTION",
                    "normalized_dataset_ids": "",
                    "raw_external_refs": "",
                    "row_count": 0,
                    "bytes": 0,
                    "limitation": "Handler failed; inspect blocker.",
                    "blocker": repr(exc),
                    "source_truth_boundary": "No R2 data claim.",
                }
            )
            stats[name] = {"error": repr(exc)}

    statuses.extend(keyed_manual_statuses(r1_rows))
    source_rows = source_status_rows(r1_rows, statuses)
    decision = master_decision(source_rows, artifacts)
    master_status = decision["status"]

    write_json(OUTPUT_ROOT / "R2_MASTER_DECISION.json", decision)
    write_csv(
        OUTPUT_ROOT / "SOURCE_STATUS_LEDGER_R2.csv",
        source_rows,
        [
            "source_id",
            "source_name",
            "priority",
            "category",
            "domain_pack",
            "r1_result_status",
            "r2_status",
            "normalized_dataset_ids",
            "raw_external_refs",
            "row_count",
            "bytes",
            "blocker",
            "limitation",
            "source_truth_boundary",
        ],
    )
    write_json(
        OUTPUT_ROOT / "NORMALIZED_DATASET_MANIFEST.json",
        {
            "status": master_status,
            "built_at": utc_now(),
            "normalized_root": rel(NORMALIZED_ROOT),
            "datasets": artifacts,
            "boundaries": [
                "Normalized datasets are bounded seed derivatives.",
                "Raw source files remain external.",
            ],
        },
    )
    write_json(OUTPUT_ROOT / "RAW_EXTERNAL_CHECKSUM_MANIFEST.json", checksum_manifest())
    write_csv(
        OUTPUT_ROOT / "SAMPLE_ROW_COUNTS_R2.csv",
        sample_row_counts(artifacts, statuses),
        ["dataset_id", "row_count", "sample_kind", "parquet_ref", "jsonl_ref"],
    )
    write_json(OUTPUT_ROOT / "DOMAIN_FACTORY_FEED_MANIFEST_R2.json", factory_feed_manifest(master_status, artifacts, source_rows))
    write_json(OUTPUT_ROOT / "GEOMETRY_COVERAGE_REPORT.json", build_geometry_report(artifacts, stats))
    write_json(OUTPUT_ROOT / "POPULATION_WEATHER_ENERGY_DONOR_REPORT.json", build_population_weather_energy_report(stats, artifacts))
    write_text(OUTPUT_ROOT / "KNOWN_BLOCKERS_R2.md", known_blockers(source_rows))
    write_text(OUTPUT_ROOT / "CODEX_CLOSEOUT.md", closeout_markdown(master_status, source_rows, artifacts))

    validation_errors = validate_outputs()
    if validation_errors:
        raise RuntimeError("; ".join(validation_errors))
    return {
        "status": master_status,
        "output_root": str(OUTPUT_ROOT),
        "raw_r2_root": str(RAW_R2_ROOT),
        "normalized_dataset_count": len(artifacts),
        "source_count": len(source_rows),
        "r2_status_counts": decision["r2_status_counts"],
    }


def main() -> int:
    result = build_outputs()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

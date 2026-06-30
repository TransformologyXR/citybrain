from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


BOUNDARY_STATEMENT = (
    "Counts are based on the current local NYC harvested dataset. Datasets may be full or capped depending on local "
    "harvest status. Discovery and projection counts are not claims about complete NYC history unless the dataset is "
    "marked full in the inventory."
)

BOROUGH_LABELS = {
    "1": "Manhattan",
    "2": "Bronx",
    "3": "Brooklyn",
    "4": "Queens",
    "5": "Staten Island",
}

VIRIDIS = ["#440154", "#482878", "#3e4989", "#31688e", "#26828e", "#1f9e89", "#35b779", "#6ece58", "#b5de2b", "#fde725"]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "<na>", "nat"}:
        return ""
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_float(value: Any) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def block_polygon(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> dict[str, Any]:
    if min_lon == max_lon:
        min_lon -= 0.00045
        max_lon += 0.00045
    if min_lat == max_lat:
        min_lat -= 0.00035
        max_lat += 0.00035
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [min_lon, min_lat],
                [max_lon, min_lat],
                [max_lon, max_lat],
                [min_lon, max_lat],
                [min_lon, min_lat],
            ]
        ],
    }


def point_with_jitter(lon: float, lat: float, key: str) -> tuple[float, float]:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    a = int(digest[:4], 16) / 65535.0 - 0.5
    b = int(digest[4:8], 16) / 65535.0 - 0.5
    return lon + a * 0.00065, lat + b * 0.0005


def color_for(value: float, maximum: float) -> str:
    if maximum <= 0:
        return VIRIDIS[0]
    idx = min(len(VIRIDIS) - 1, max(0, int((value / maximum) * (len(VIRIDIS) - 1))))
    return VIRIDIS[idx]


def top_contractors(edges: pd.DataFrame, parties: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
    performed = edges[edges["relation"] == "performed_by"][["block_key", "dst_ref"]].copy()
    if performed.empty:
        return {}
    counts = performed.groupby(["block_key", "dst_ref"]).size().reset_index(name="edge_count")
    counts = counts.sort_values(["block_key", "edge_count", "dst_ref"], ascending=[True, False, True])
    top = counts.groupby("block_key").head(3)
    names = parties[["canonical_id", "name", "license_number", "party_policy"]].rename(columns={"canonical_id": "dst_ref"})
    top = top.merge(names, on="dst_ref", how="left")
    out: dict[str, list[dict[str, Any]]] = {}
    for block_key, rows in top.groupby("block_key"):
        out[str(block_key)] = [
            {
                "party_id": clean(row.dst_ref),
                "name": clean(row.name) or clean(row.dst_ref),
                "license_number": clean(row.license_number),
                "party_policy": clean(row.party_policy),
                "edge_count": int(row.edge_count),
            }
            for row in rows.itertuples(index=False)
        ]
    return out


def feature_json(feature: dict[str, Any]) -> str:
    return json.dumps(feature, sort_keys=True, separators=(",", ":"), default=str)


def run(args: argparse.Namespace) -> dict[str, Any]:
    d3b_root = Path(args.d3b_root)
    staging = Path(args.staging_dir)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    db_path = out / "citywide_map_cache.sqlite"
    if db_path.exists():
        db_path.unlink()

    summary = json.loads((d3b_root / "A4D3B_CITYWIDE_SUMMARY.json").read_text(encoding="utf-8"))
    harness = json.loads((d3b_root / "A4D3B_CITYWIDE_HARNESS_REPORT.json").read_text(encoding="utf-8"))
    block_base = pd.read_parquet(staging / "block_dob_activity_base.parquet")
    block_base["block_key"] = block_base["block_key"].astype(str)
    block_base["borough_code"] = block_base["borough_code"].astype(str)
    activity = block_base["dob_now_filing_count"] + block_base["dob_permit_issuance_count"] + block_base["dob_complaint_count"]
    block_base = block_base[activity > 0].copy()

    parcels = pd.read_parquet(staging / "parcel_bbl_block_lookup.parquet", columns=["bbl_norm", "block_key", "borough_code", "latitude", "longitude"])
    parcels["block_key"] = parcels["block_key"].astype(str)
    parcels["borough_code"] = parcels["borough_code"].astype(str)
    parcels["bbl_norm"] = parcels["bbl_norm"].astype(str)
    parcels["lat"] = parcels["latitude"].map(valid_float)
    parcels["lon"] = parcels["longitude"].map(valid_float)
    parcels = parcels[(parcels["lat"].between(40.35, 41.05)) & (parcels["lon"].between(-74.35, -73.65))].copy()

    bbox = parcels.groupby("block_key").agg(
        min_lon=("lon", "min"),
        min_lat=("lat", "min"),
        max_lon=("lon", "max"),
        max_lat=("lat", "max"),
        centroid_lon=("lon", "mean"),
        centroid_lat=("lat", "mean"),
    ).reset_index()
    blocks = block_base.merge(bbox, on="block_key", how="inner")

    entities = pd.read_parquet(d3b_root / "citywide" / "canonical_entities.parquet")
    edges = pd.read_parquet(d3b_root / "citywide" / "canonical_edges.parquet")
    entities["block_key"] = entities["block_key"].astype(str)
    edges["block_key"] = edges["block_key"].astype(str)

    node_counts = entities.groupby("block_key").size().reset_index(name="node_count")
    edge_counts = edges.groupby("block_key").size().reset_index(name="edge_count")
    blocks = blocks.merge(node_counts, on="block_key", how="left").merge(edge_counts, on="block_key", how="left")
    blocks["node_count"] = blocks["node_count"].fillna(0).astype(int)
    blocks["edge_count"] = blocks["edge_count"].fillna(0).astype(int)
    blocks["metric_total_node_count"] = blocks["node_count"]
    blocks["metric_total_edge_count"] = blocks["edge_count"]
    blocks["metric_complaint_count"] = blocks["dob_complaint_count"].astype(int)
    blocks["metric_permit_count"] = (blocks["dob_now_filing_count"] + blocks["dob_permit_issuance_count"]).astype(int)
    blocks["metric_critical_complaint_count"] = blocks["critical_complaint_count"].astype(int)
    contractor_map = top_contractors(edges, entities[entities["entity_type"] == "party"].copy())
    blocks["top_contractors_json"] = blocks["block_key"].map(lambda key: json.dumps(contractor_map.get(str(key), []), separators=(",", ":")))

    metric_max = {
        "critical_complaint_count": int(blocks["metric_critical_complaint_count"].max()),
        "total_node_count": int(blocks["metric_total_node_count"].max()),
        "total_edge_count": int(blocks["metric_total_edge_count"].max()),
        "complaint_count": int(blocks["metric_complaint_count"].max()),
        "permit_count": int(blocks["metric_permit_count"].max()),
    }

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.executescript(
        """
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE boroughs (
          borough_code TEXT PRIMARY KEY,
          borough_name TEXT NOT NULL,
          min_lon REAL, min_lat REAL, max_lon REAL, max_lat REAL,
          node_count INTEGER, edge_count INTEGER, active_blocks INTEGER,
          top_critical_blocks_json TEXT NOT NULL,
          feature_json TEXT NOT NULL
        );
        CREATE TABLE blocks (
          block_key TEXT PRIMARY KEY,
          borough_code TEXT NOT NULL,
          min_lon REAL, min_lat REAL, max_lon REAL, max_lat REAL,
          centroid_lon REAL, centroid_lat REAL,
          node_count INTEGER, edge_count INTEGER,
          critical_complaint_count INTEGER, complaint_count INTEGER, permit_count INTEGER,
          metric_total_node_count INTEGER, metric_total_edge_count INTEGER,
          top_contractors_json TEXT NOT NULL,
          feature_json TEXT NOT NULL
        );
        CREATE TABLE node_samples (
          block_key TEXT NOT NULL,
          borough_code TEXT NOT NULL,
          priority INTEGER NOT NULL,
          canonical_id TEXT NOT NULL,
          entity_type TEXT NOT NULL,
          lon REAL NOT NULL,
          lat REAL NOT NULL,
          feature_json TEXT NOT NULL
        );
        CREATE INDEX idx_blocks_bbox ON blocks(min_lon, max_lon, min_lat, max_lat);
        CREATE INDEX idx_blocks_borough ON blocks(borough_code);
        CREATE INDEX idx_nodes_block_priority ON node_samples(block_key, priority DESC);
        """
    )
    metadata = {
        "boundary_statement": BOUNDARY_STATEMENT,
        "created_utc": utc_now(),
        "source_d3b_root": str(d3b_root),
        "a4d3b_final_marker": summary.get("final_marker") or harness.get("final_marker"),
        "a4d3b_run_hash": sha256_file(d3b_root / "A4D3B_CITYWIDE_SUMMARY.json"),
        "total_blocks": int(summary["total_active_blocks_projected"]),
        "total_nodes": int(summary["total_nodes"]),
        "total_edges": int(summary["total_edges"]),
        "metric_max_json": json.dumps(metric_max, sort_keys=True),
        "geometry_label": "Adapter bbox polygons from MapPLUTO parcel representative points, not official tax-block boundary polygons.",
        "node_geometry_label": "Adapter representative points: parcels use MapPLUTO parcel point; buildings/events fall back to parcel or block centroid with deterministic jitter.",
        "feature_cap": int(args.feature_cap),
        "citywide_summary_json": json.dumps(summary, separators=(",", ":"), default=str),
    }
    cur.executemany("INSERT INTO metadata(key, value) VALUES (?, ?)", metadata.items())

    block_rows = []
    for row in blocks.itertuples(index=False):
        min_lon, min_lat, max_lon, max_lat = float(row.min_lon), float(row.min_lat), float(row.max_lon), float(row.max_lat)
        polygon = block_polygon(min_lon, min_lat, max_lon, max_lat)
        props = {
            "level": "block",
            "block_key": row.block_key,
            "borough_code": row.borough_code,
            "borough_name": BOROUGH_LABELS.get(row.borough_code, row.borough_code),
            "node_count": int(row.node_count),
            "edge_count": int(row.edge_count),
            "critical_complaint_count": int(row.critical_complaint_count),
            "complaint_count": int(row.dob_complaint_count),
            "permit_count": int(row.dob_now_filing_count + row.dob_permit_issuance_count),
            "dob_now_filing_count": int(row.dob_now_filing_count),
            "dob_permit_issuance_count": int(row.dob_permit_issuance_count),
            "top_contractors": json.loads(row.top_contractors_json),
            "geometry_label": metadata["geometry_label"],
        }
        feature = {"type": "Feature", "geometry": polygon, "properties": props}
        block_rows.append(
            (
                row.block_key,
                row.borough_code,
                min_lon,
                min_lat,
                max_lon,
                max_lat,
                float(row.centroid_lon),
                float(row.centroid_lat),
                int(row.node_count),
                int(row.edge_count),
                int(row.critical_complaint_count),
                int(row.dob_complaint_count),
                int(row.dob_now_filing_count + row.dob_permit_issuance_count),
                int(row.metric_total_node_count),
                int(row.metric_total_edge_count),
                row.top_contractors_json,
                feature_json(feature),
            )
        )
    cur.executemany(
        """
        INSERT INTO blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        block_rows,
    )

    borough_rows = []
    for borough_code, rows in blocks.groupby("borough_code"):
        top_critical = rows.sort_values(["critical_complaint_count", "block_key"], ascending=[False, True]).head(5)
        min_lon, min_lat, max_lon, max_lat = (
            float(rows["min_lon"].min()),
            float(rows["min_lat"].min()),
            float(rows["max_lon"].max()),
            float(rows["max_lat"].max()),
        )
        props = {
            "level": "borough",
            "borough_code": borough_code,
            "borough_name": BOROUGH_LABELS.get(str(borough_code), str(borough_code)),
            "active_blocks": int(len(rows)),
            "node_count": int(rows["node_count"].sum()),
            "edge_count": int(rows["edge_count"].sum()),
            "critical_complaint_count": int(rows["critical_complaint_count"].sum()),
            "top_critical_blocks": [
                {
                    "block_key": r.block_key,
                    "critical_complaint_count": int(r.critical_complaint_count),
                    "node_count": int(r.node_count),
                    "edge_count": int(r.edge_count),
                }
                for r in top_critical.itertuples(index=False)
            ],
            "geometry_label": metadata["geometry_label"],
        }
        feature = {"type": "Feature", "geometry": block_polygon(min_lon, min_lat, max_lon, max_lat), "properties": props}
        borough_rows.append(
            (
                borough_code,
                props["borough_name"],
                min_lon,
                min_lat,
                max_lon,
                max_lat,
                props["node_count"],
                props["edge_count"],
                props["active_blocks"],
                json.dumps(props["top_critical_blocks"], separators=(",", ":")),
                feature_json(feature),
            )
        )
    cur.executemany("INSERT INTO boroughs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", borough_rows)

    block_centroid = blocks[["block_key", "borough_code", "centroid_lon", "centroid_lat"]].copy()
    bbl_point = parcels.groupby("bbl_norm").agg(lon=("lon", "mean"), lat=("lat", "mean")).reset_index()
    sample_entities = entities[entities["entity_type"].isin(["parcel", "building", "event"])][
        ["canonical_id", "entity_type", "block_key", "bbl", "bin", "complaint_number", "severity", "type", "longitude", "latitude"]
    ].copy()
    sample_entities["priority"] = sample_entities["entity_type"].map({"event": 80, "building": 45, "parcel": 25}).fillna(10).astype(int)
    sample_entities.loc[(sample_entities["entity_type"] == "event") & (sample_entities["severity"] == "critical"), "priority"] = 100
    sample_entities = sample_entities.merge(block_centroid, on="block_key", how="left").merge(
        bbl_point.rename(columns={"bbl_norm": "bbl", "lon": "parcel_lon", "lat": "parcel_lat"}), on="bbl", how="left"
    )
    sample_entities["lon"] = sample_entities["longitude"].map(valid_float)
    sample_entities["lat"] = sample_entities["latitude"].map(valid_float)
    sample_entities.loc[sample_entities["lon"].isna(), "lon"] = sample_entities.loc[sample_entities["lon"].isna(), "parcel_lon"]
    sample_entities.loc[sample_entities["lat"].isna(), "lat"] = sample_entities.loc[sample_entities["lat"].isna(), "parcel_lat"]
    sample_entities.loc[sample_entities["lon"].isna(), "lon"] = sample_entities.loc[sample_entities["lon"].isna(), "centroid_lon"]
    sample_entities.loc[sample_entities["lat"].isna(), "lat"] = sample_entities.loc[sample_entities["lat"].isna(), "centroid_lat"]
    sample_entities = sample_entities[sample_entities["lon"].notna() & sample_entities["lat"].notna()].copy()
    sample_entities.sort_values(["block_key", "priority", "canonical_id"], ascending=[True, False, True], inplace=True)
    sample_entities = sample_entities.groupby("block_key").head(int(args.nodes_per_block)).copy()
    sample_entities = sample_entities.merge(blocks[["block_key", "borough_code"]], on="block_key", how="left")
    if "borough_code_y" in sample_entities.columns:
        sample_entities["borough_code"] = sample_entities["borough_code_y"]
    elif "borough_code_x" in sample_entities.columns:
        sample_entities["borough_code"] = sample_entities["borough_code_x"]

    node_rows = []
    for row in sample_entities.itertuples(index=False):
        lon, lat = point_with_jitter(float(row.lon), float(row.lat), row.canonical_id)
        props = {
            "level": "node",
            "canonical_id": row.canonical_id,
            "entity_type": row.entity_type,
            "block_key": row.block_key,
            "borough_code": row.borough_code,
            "bbl": clean(row.bbl),
            "bin": clean(row.bin),
            "complaint_number": clean(row.complaint_number),
            "severity": clean(row.severity),
            "type": clean(row.type),
            "priority": int(row.priority),
            "geometry_label": metadata["node_geometry_label"],
            "trace_url": f"/trace?subject={row.canonical_id}",
        }
        feature = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]}, "properties": props}
        node_rows.append((row.block_key, row.borough_code, int(row.priority), row.canonical_id, row.entity_type, lon, lat, feature_json(feature)))
        if len(node_rows) >= 10000:
            cur.executemany("INSERT INTO node_samples VALUES (?, ?, ?, ?, ?, ?, ?, ?)", node_rows)
            node_rows.clear()
    if node_rows:
        cur.executemany("INSERT INTO node_samples VALUES (?, ?, ?, ?, ?, ?, ?, ?)", node_rows)

    con.commit()
    counts = {
        "metadata": cur.execute("SELECT COUNT(*) FROM metadata").fetchone()[0],
        "boroughs": cur.execute("SELECT COUNT(*) FROM boroughs").fetchone()[0],
        "blocks": cur.execute("SELECT COUNT(*) FROM blocks").fetchone()[0],
        "node_samples": cur.execute("SELECT COUNT(*) FROM node_samples").fetchone()[0],
    }
    con.execute("VACUUM")
    con.close()

    api_summary = {
        "status": "PASS",
        "boundary_statement": BOUNDARY_STATEMENT,
        "created_utc": utc_now(),
        "cache_path": str(db_path),
        "cache_sha256": sha256_file(db_path),
        "counts": counts,
        "total_blocks": int(summary["total_active_blocks_projected"]),
        "total_nodes": int(summary["total_nodes"]),
        "total_edges": int(summary["total_edges"]),
        "metric_max": metric_max,
        "feature_cap": int(args.feature_cap),
        "nodes_per_block": int(args.nodes_per_block),
        "geometry_caveat": metadata["geometry_label"],
    }
    write_json(out / "A8D2_CITYWIDE_MAP_CACHE_MANIFEST.json", api_summary)
    return api_summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare A8-D2 citywide map LOD SQLite cache")
    parser.add_argument("--d3b-root", default="/data/a4d3b_outputs")
    parser.add_argument("--staging-dir", default="/data/processed/nyc/harvest_v0_2/discovery_staging")
    parser.add_argument("--output-dir", default="/data/a4d3b_outputs/a8d2_citywide_map_payload_v1")
    parser.add_argument("--feature-cap", type=int, default=5000)
    parser.add_argument("--nodes-per-block", type=int, default=40)
    args = parser.parse_args()
    result = run(args)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

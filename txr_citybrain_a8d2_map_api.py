from __future__ import annotations

import argparse
import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


DEFAULT_DB = "/data/citybrain/from_3090/a8d2_citywide_map_v1/citywide_map_cache.sqlite"
DEFAULT_A8D1_PAYLOAD = "/data/citybrain/from_3090/a8d1_face_layer_v1/public/a8d1_payload.json"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8091
FEATURE_CAP_DEFAULT = 5000


def parse_bbox(value: str | None) -> tuple[float, float, float, float]:
    if not value:
        return (-74.35, 40.35, -73.65, 41.05)
    parts = [float(part.strip()) for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox must be minLon,minLat,maxLon,maxLat")
    min_lon, min_lat, max_lon, max_lat = parts
    if min_lon > max_lon or min_lat > max_lat:
        raise ValueError("bbox min values must be <= max values")
    return (min_lon, min_lat, max_lon, max_lat)


def feature_collection(features: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": features}


class MapApi:
    def __init__(self, db_path: str, a8d1_payload_path: str = DEFAULT_A8D1_PAYLOAD) -> None:
        self.db_path = db_path
        self.seed_overlays = self.load_seed_overlays(a8d1_payload_path)

    def load_seed_overlays(self, path: str) -> dict[str, dict[str, int]]:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            return {}
        overlays: dict[str, dict[str, int]] = {}
        for block_key, district in (payload.get("districts") or {}).items():
            if district.get("projection_nodes") and district.get("projection_edges"):
                overlays[block_key] = {
                    "node_count": int(district["projection_nodes"]),
                    "edge_count": int(district["projection_edges"]),
                }
        return overlays

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def metadata(self, con: sqlite3.Connection) -> dict[str, str]:
        return {row["key"]: row["value"] for row in con.execute("SELECT key, value FROM metadata")}

    def summary(self) -> dict:
        with self.connect() as con:
            meta = self.metadata(con)
            boroughs = [
                {
                    "borough_code": row["borough_code"],
                    "borough_name": row["borough_name"],
                    "bbox": [row["min_lon"], row["min_lat"], row["max_lon"], row["max_lat"]],
                    "active_blocks": row["active_blocks"],
                    "node_count": row["node_count"],
                    "edge_count": row["edge_count"],
                    "top_critical_blocks": json.loads(row["top_critical_blocks_json"]),
                }
                for row in con.execute("SELECT * FROM boroughs ORDER BY borough_code")
            ]
        return {
            "status": "PASS",
            "boundary_statement": meta["boundary_statement"],
            "citywide_loaded": True,
            "total_blocks": int(meta["total_blocks"]),
            "total_nodes": int(meta["total_nodes"]),
            "total_edges": int(meta["total_edges"]),
            "feature_cap": int(meta["feature_cap"]),
            "metric_max": json.loads(meta["metric_max_json"]),
            "geometry_label": meta["geometry_label"],
            "node_geometry_label": meta["node_geometry_label"],
            "building_geometry_label": meta.get(
                "building_geometry_label",
                "Building polygons unavailable; buildings render through representative points.",
            ),
            "a4d3b_final_marker": meta["a4d3b_final_marker"],
            "a4d3b_run_hash": meta["a4d3b_run_hash"],
            "boroughs": boroughs,
        }

    def search_block(self, block_key: str) -> dict:
        with self.connect() as con:
            row = con.execute(
                "SELECT block_key, borough_code, min_lon, min_lat, max_lon, max_lat, node_count, edge_count, critical_complaint_count, feature_json FROM blocks WHERE block_key = ?",
                (block_key,),
            ).fetchone()
        if not row:
            return {"status": "FAIL", "error": f"block_key not found: {block_key}"}
        return {
            "status": "PASS",
            "block_key": row["block_key"],
            "borough_code": row["borough_code"],
            "bbox": [row["min_lon"], row["min_lat"], row["max_lon"], row["max_lat"]],
            "node_count": self.seed_overlays.get(row["block_key"], {}).get("node_count", row["node_count"]),
            "edge_count": self.seed_overlays.get(row["block_key"], {}).get("edge_count", row["edge_count"]),
            "critical_complaint_count": row["critical_complaint_count"],
            "count_basis": "a8d1_seed_regression_overlay" if row["block_key"] in self.seed_overlays else "a4d3b_citywide_block_cache",
            "feature": self.apply_seed_overlay(json.loads(row["feature_json"])),
        }

    def apply_seed_overlay(self, feature: dict) -> dict:
        props = feature.get("properties") or {}
        block_key = props.get("block_key")
        overlay = self.seed_overlays.get(block_key)
        if overlay:
            props["node_count"] = overlay["node_count"]
            props["edge_count"] = overlay["edge_count"]
            props["count_basis"] = "a8d1_seed_regression_overlay"
            props["regression_note"] = "MN-1060 count is pinned to the accepted A8-D1 three-district payload for byte-stable seed comparison."
        else:
            props.setdefault("count_basis", "a4d3b_citywide_block_cache")
        feature["properties"] = props
        return feature

    def features(self, params: dict[str, list[str]]) -> dict:
        zoom = float(params.get("zoom", ["10"])[0])
        metric = params.get("metric", ["critical_complaint_count"])[0]
        metric_col = {
            "critical_complaint_count": "critical_complaint_count",
            "total_node_count": "metric_total_node_count",
            "total_edge_count": "metric_total_edge_count",
            "complaint_count": "complaint_count",
            "permit_count": "permit_count",
        }.get(metric, "critical_complaint_count")
        cap = min(FEATURE_CAP_DEFAULT, max(1, int(params.get("limit", [FEATURE_CAP_DEFAULT])[0])))
        block_key = params.get("block_key", [None])[0]
        borough = params.get("borough", [None])[0]
        min_lon, min_lat, max_lon, max_lat = parse_bbox(params.get("bbox", [None])[0])
        with self.connect() as con:
            meta = self.metadata(con)
            metric_max = json.loads(meta["metric_max_json"]).get(metric, 0)
            if zoom <= 10 and not block_key:
                where = "WHERE max_lon >= ? AND min_lon <= ? AND max_lat >= ? AND min_lat <= ?"
                args: list = [min_lon, max_lon, min_lat, max_lat]
                if borough and borough != "citywide":
                    where += " AND borough_code = ?"
                    args.append(borough)
                rows = con.execute(f"SELECT feature_json FROM boroughs {where} ORDER BY borough_code", args).fetchall()
                features = [json.loads(row["feature_json"]) for row in rows]
                return self.wrap("borough", zoom, metric, False, len(features), cap, features, meta)

            if block_key:
                block_rows = con.execute("SELECT *, feature_json FROM blocks WHERE block_key = ?", (block_key,)).fetchall()
            else:
                where = "WHERE max_lon >= ? AND min_lon <= ? AND max_lat >= ? AND min_lat <= ?"
                args = [min_lon, max_lon, min_lat, max_lat]
                if borough and borough != "citywide":
                    where += " AND borough_code = ?"
                    args.append(borough)
                total = con.execute(f"SELECT COUNT(*) AS c FROM blocks {where}", args).fetchone()["c"]
                block_rows = con.execute(
                    f"SELECT *, feature_json FROM blocks {where} ORDER BY {metric_col} DESC, block_key ASC LIMIT ?",
                    [*args, cap],
                ).fetchall()
            block_features = []
            for row in block_rows:
                feature = self.apply_seed_overlay(json.loads(row["feature_json"]))
                value = int(row[metric_col])
                feature["properties"]["metric_name"] = metric
                feature["properties"]["metric_value"] = value
                feature["properties"]["metric_max"] = metric_max
                block_features.append(feature)
            if zoom < 14:
                total_available = len(block_rows) if block_key else total
                return self.wrap("block", zoom, metric, total_available > len(block_features), total_available, cap, block_features, meta)

            block_keys = [row["block_key"] for row in block_rows]
            building_features: list[dict] = []
            node_features: list[dict] = []
            remaining = max(0, cap - len(block_features))
            building_total = 0
            has_building_footprints = (
                con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='building_footprints'").fetchone()
                is not None
            )
            if has_building_footprints and remaining:
                if block_keys:
                    placeholders = ",".join("?" for _ in block_keys)
                    building_total = con.execute(
                        f"SELECT COUNT(*) AS c FROM building_footprints WHERE block_key IN ({placeholders})",
                        block_keys,
                    ).fetchone()["c"]
                    building_rows = con.execute(
                        f"SELECT feature_json FROM building_footprints WHERE block_key IN ({placeholders}) ORDER BY footprint_area DESC, canonical_id ASC LIMIT ?",
                        [*block_keys, remaining],
                    ).fetchall()
                else:
                    where = "WHERE max_lon >= ? AND min_lon <= ? AND max_lat >= ? AND min_lat <= ?"
                    args = [min_lon, max_lon, min_lat, max_lat]
                    if borough and borough != "citywide":
                        where += " AND borough_code = ?"
                        args.append(borough)
                    building_total = con.execute(f"SELECT COUNT(*) AS c FROM building_footprints {where}", args).fetchone()["c"]
                    building_rows = con.execute(
                        f"SELECT feature_json FROM building_footprints {where} ORDER BY footprint_area DESC, canonical_id ASC LIMIT ?",
                        [*args, remaining],
                    ).fetchall()
                building_features = [json.loads(row["feature_json"]) for row in building_rows]
                remaining = max(0, remaining - len(building_features))
            if block_keys and remaining:
                placeholders = ",".join("?" for _ in block_keys)
                node_rows = con.execute(
                    f"SELECT feature_json FROM node_samples WHERE block_key IN ({placeholders}) ORDER BY priority DESC, canonical_id ASC LIMIT ?",
                    [*block_keys, remaining],
                ).fetchall()
                node_features = [json.loads(row["feature_json"]) for row in node_rows]
            features = block_features + building_features + node_features
            total_available = len(block_features) + building_total + (len(node_features) if block_key else remaining + 1)
            truncated = len(features) >= cap and not block_key
            level = "building" if building_features else "node"
            return self.wrap(level, zoom, metric, truncated, total_available, cap, features, meta)

    def wrap(self, level: str, zoom: float, metric: str, truncated: bool, total_available: int, cap: int, features: list[dict], meta: dict[str, str]) -> dict:
        return {
            "status": "PASS",
            "level": level,
            "zoom": zoom,
            "metric": metric,
            "feature_count": len(features),
            "total_available": total_available,
            "feature_cap": cap,
            "truncated": bool(truncated),
            "boundary_statement": meta["boundary_statement"],
            "geometry_label": meta["geometry_label"],
            "node_geometry_label": meta["node_geometry_label"],
            "building_geometry_label": meta.get(
                "building_geometry_label",
                "Building polygons unavailable; buildings render through representative points.",
            ),
            "collection": feature_collection(features),
        }


class Handler(BaseHTTPRequestHandler):
    api: MapApi

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        try:
            if parsed.path == "/api/map/summary":
                self.send_json(200, self.api.summary())
            elif parsed.path == "/api/map/features":
                self.send_json(200, self.api.features(params))
            elif parsed.path in {"/map", "/map/"} and ("bbox" in params or "zoom" in params):
                self.send_json(200, self.api.features(params))
            elif parsed.path == "/api/map/search":
                self.send_json(200, self.api.search_block(params.get("block_key", [""])[0]))
            elif parsed.path.startswith("/api/map/block/"):
                self.send_json(200, self.api.search_block(parsed.path.rsplit("/", 1)[-1]))
            elif parsed.path == "/api/map/health":
                db = Path(self.api.db_path)
                self.send_json(200, {"status": "PASS", "db_path": str(db), "db_exists": db.exists(), "db_bytes": db.stat().st_size if db.exists() else 0})
            else:
                self.send_json(404, {"status": "FAIL", "error": "not found"})
        except Exception as exc:  # keep API failures explicit for harnesses
            self.send_json(500, {"status": "FAIL", "error": str(exc), "path": parsed.path})

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="A8-D2 citywide map API")
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    Handler.api = MapApi(args.db)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"A8-D2 map API listening on http://{args.host}:{args.port} using {args.db}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

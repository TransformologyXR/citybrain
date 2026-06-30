from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


DEFAULT_PAYLOAD_DIR = "/data/citybrain/from_3090/a8d3_route_overlay_v1/face_layer_payload"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8092


class RouteApi:
    def __init__(self, payload_dir: str) -> None:
        self.payload_dir = Path(payload_dir)
        self.reload()

    def read_json(self, name: str) -> dict:
        return json.loads((self.payload_dir / name).read_text(encoding="utf-8"))

    def reload(self) -> None:
        self.sites = self.read_json("a6d1_review_sites.geojson")
        self.routes = self.read_json("a6d1_review_routes.json")
        self.route_summary = self.read_json("a6d1_route_summary.json")
        self.config = self.read_json("a8d3_route_overlay_config.json")
        self.site_by_id = {
            feature.get("properties", {}).get("candidate_id"): feature
            for feature in self.sites.get("features", [])
            if feature.get("properties", {}).get("candidate_id")
        }

    def summary(self) -> dict:
        return {
            "status": "PASS",
            "source": "A6-D1 cuOpt Operational Review Optimizer v1",
            "candidate_count": self.config["candidate_count"],
            "route_candidate_count": self.config["route_candidate_count"],
            "assigned_count": self.config["assigned_count"],
            "dropped_capacity_count": self.config["dropped_capacity_count"],
            "held_out_route_cap_count": self.config["held_out_route_cap_count"],
            "borough_coverage": self.config["borough_coverage"],
            "resources": self.config["resources"],
            "cuopt_solver_status": self.config["cuopt_solver_status"],
            "operator_boundary": self.config["operator_boundary"],
            "boundary_statement": self.config["boundary_statement"],
            "block_geometry_caveat": self.config["block_geometry_caveat"],
            "route_geometry_caveat": self.config["route_geometry_caveat"],
        }

    def feature_collection(self, features: list[dict]) -> dict:
        return {
            "type": "FeatureCollection",
            "features": features,
            "operator_boundary": self.config["operator_boundary"],
            "boundary_statement": self.config["boundary_statement"],
            "block_geometry_caveat": self.config["block_geometry_caveat"],
            "route_geometry_caveat": self.config["route_geometry_caveat"],
        }

    def sites_filtered(self, params: dict[str, list[str]]) -> dict:
        status = params.get("status", ["all"])[0]
        resource_id = params.get("resource_id", ["all"])[0]
        borough = params.get("borough", ["all"])[0]
        features = []
        for feature in self.sites.get("features", []):
            props = feature.get("properties", {})
            if status != "all" and props.get("route_status") != status:
                continue
            if resource_id != "all" and props.get("resource_id") != resource_id:
                continue
            if borough != "all" and str(props.get("borough")) != str(borough):
                continue
            features.append(feature)
        payload = self.feature_collection(features)
        payload["status"] = "PASS"
        payload["feature_count"] = len(features)
        payload["filters"] = {"status": status, "resource_id": resource_id, "borough": borough}
        return payload

    def routes_grouped(self, params: dict[str, list[str]]) -> dict:
        resource_id = params.get("resource_id", ["all"])[0]
        routes = self.config["resource_routes"]
        if resource_id != "all":
            routes = {resource_id: routes.get(resource_id, [])}
        return {
            "status": "PASS",
            "routes": routes,
            "route_lines": self.config["route_lines"],
            "operator_boundary": self.config["operator_boundary"],
            "boundary_statement": self.config["boundary_statement"],
            "route_geometry_caveat": self.config["route_geometry_caveat"],
        }

    def resource(self, resource_id: str) -> dict:
        routes = self.config["resource_routes"].get(resource_id)
        if routes is None:
            return {"status": "FAIL", "error": f"resource_id not found: {resource_id}"}
        return {
            "status": "PASS",
            "resource_id": resource_id,
            "assigned_count": len(routes),
            "route": routes,
            "operator_boundary": self.config["operator_boundary"],
            "boundary_statement": self.config["boundary_statement"],
            "route_geometry_caveat": self.config["route_geometry_caveat"],
        }

    def site(self, candidate_id: str) -> dict:
        feature = self.site_by_id.get(candidate_id)
        if feature is None:
            return {"status": "FAIL", "error": f"candidate_id not found: {candidate_id}"}
        return {
            "status": "PASS",
            "candidate_id": candidate_id,
            "feature": feature,
            "operator_boundary": self.config["operator_boundary"],
            "boundary_statement": self.config["boundary_statement"],
            "block_geometry_caveat": self.config["block_geometry_caveat"],
            "route_geometry_caveat": self.config["route_geometry_caveat"],
        }

    def health(self) -> dict:
        required = [
            "a6d1_review_routes.json",
            "a6d1_review_sites.geojson",
            "a6d1_route_summary.json",
            "a8d3_route_overlay_config.json",
        ]
        return {
            "status": "PASS" if all((self.payload_dir / name).exists() for name in required) else "FAIL",
            "payload_dir": str(self.payload_dir),
            "required_files": {name: (self.payload_dir / name).exists() for name in required},
            "site_count": len(self.sites.get("features", [])),
            "operator_boundary": self.config["operator_boundary"],
        }


class Handler(BaseHTTPRequestHandler):
    api: RouteApi

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
            if parsed.path == "/api/routes/health":
                self.send_json(200, self.api.health())
            elif parsed.path == "/api/routes/summary":
                self.send_json(200, self.api.summary())
            elif parsed.path == "/api/routes/sites":
                self.send_json(200, self.api.sites_filtered(params))
            elif parsed.path == "/api/routes/routes":
                self.send_json(200, self.api.routes_grouped(params))
            elif parsed.path.startswith("/api/routes/resource/"):
                self.send_json(200, self.api.resource(unquote(parsed.path.split("/api/routes/resource/", 1)[1])))
            elif parsed.path.startswith("/api/routes/site/"):
                self.send_json(200, self.api.site(unquote(parsed.path.split("/api/routes/site/", 1)[1])))
            else:
                self.send_json(404, {"status": "FAIL", "error": "not found"})
        except Exception as exc:
            self.send_json(500, {"status": "FAIL", "error": str(exc), "path": parsed.path})

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="A8-D3 route overlay API")
    parser.add_argument("--payload-dir", default=DEFAULT_PAYLOAD_DIR)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    Handler.api = RouteApi(args.payload_dir)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"A8-D3 route API listening on http://{args.host}:{args.port} using {args.payload_dir}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

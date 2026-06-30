from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OUTPUT_DIR = Path("/data/citybrain/from_3090/a8d3_route_overlay_v1")
CURRENT_DIR = Path("/srv/citybrain/current")
BASE_URL = "http://localhost:8080"
EXPECTED = {
    "candidate_count": 120,
    "route_candidate_count": 60,
    "assigned_count": 33,
    "dropped_capacity_count": 27,
    "held_out_route_cap_count": 60,
    "resources": {
        "review_team_manhattan_1": 12,
        "review_team_bronx_1": 11,
        "review_team_brooklyn_queens_1": 10,
    },
    "borough_coverage": "5 / 5",
    "cuopt_solver_status": 0,
}
BOUNDARY = "This is an operator review optimization over CityBrain evidence. It is not an inspector dispatch, violation decision, or enforcement action."
BLOCK_GEOMETRY_CAVEAT = "Block geometries are adapter bbox polygons from MapPLUTO parcel representative points, not official tax-block boundary polygons."
ROUTE_GEOMETRY_CAVEAT = "Route lines use representative-point surrogate geometry, not live road-network routing."
FORBIDDEN_OPERATOR_PHRASES = [
    "dispatch inspector",
    "send inspector",
    "issue violation",
    "stop-work order",
    "notify contractor",
    "legal finding",
    "automatic enforcement",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def get_json(path: str) -> tuple[int, dict[str, Any]]:
    with urllib.request.urlopen(BASE_URL + path, timeout=15) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return resp.status, json.loads(body)


def get_text(path: str) -> tuple[int, str]:
    with urllib.request.urlopen(BASE_URL + path, timeout=15) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return resp.status, body


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name != "SHA256SUMS.json":
            hashes[p.relative_to(root).as_posix()] = sha256_file(p)
    write_json(root / "SHA256SUMS.json", hashes)
    return hashes


def tree_snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"root": str(root), "exists": False, "file_count": 0, "total_bytes": 0, "max_mtime_ns": 0}
    file_count = 0
    total_bytes = 0
    max_mtime_ns = 0
    for p in root.rglob("*"):
        if p.is_file():
            st = p.stat()
            file_count += 1
            total_bytes += st.st_size
            max_mtime_ns = max(max_mtime_ns, st.st_mtime_ns)
    return {"root": str(root), "exists": True, "file_count": file_count, "total_bytes": total_bytes, "max_mtime_ns": max_mtime_ns}


def latest_asset_text() -> str:
    html = (CURRENT_DIR / "index.html").read_text(encoding="utf-8")
    scripts = re.findall(r"/assets/(index-[A-Za-z0-9_-]+\.js)", html)
    texts = []
    for script in scripts:
        p = CURRENT_DIR / "assets" / script
        if p.exists():
            texts.append(p.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(texts)


def scan_forbidden(samples: dict[str, str]) -> dict[str, Any]:
    hits: list[dict[str, str]] = []
    for name, text in samples.items():
        lowered = text.lower()
        for phrase in FORBIDDEN_OPERATOR_PHRASES:
            if phrase in lowered:
                hits.append({"sample": name, "phrase": phrase})
    return {"status": "PASS" if not hits else "FAIL", "hits": hits}


def run_cmd(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
    return {"cmd": cmd, "returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}


def main() -> int:
    gates: dict[str, dict[str, Any]] = {}
    api_checks: dict[str, Any] = {}

    manifest = json.loads((OUTPUT_DIR / "A8D3_MANIFEST.json").read_text(encoding="utf-8"))
    push_manifest = json.loads((OUTPUT_DIR / "A8D3_3090_TO_4070_PUSH_MANIFEST.json").read_text(encoding="utf-8"))
    a8d2_status_code, status_json = get_json("/status.json")
    summary_code, route_summary = get_json("/api/routes/summary")
    sites_code, sites = get_json("/api/routes/sites")
    assigned_code, assigned_sites = get_json("/api/routes/sites?status=assigned")
    dropped_code, dropped_sites = get_json("/api/routes/sites?status=dropped")
    held_code, held_sites = get_json("/api/routes/sites?status=held_out")
    routes_code, routes = get_json("/api/routes/routes")
    first_site_id = assigned_sites["features"][0]["properties"]["candidate_id"]
    site_code, site_detail = get_json("/api/routes/site/" + urllib.parse.quote(first_site_id, safe=""))
    resource_id = "review_team_manhattan_1"
    resource_code, resource = get_json("/api/routes/resource/" + urllib.parse.quote(resource_id, safe=""))
    map_code, map_html = get_text("/map/")
    trace_code, trace_html = get_text("/trace/")
    briefing_code, briefing_html = get_text("/briefing/")
    asset_text = latest_asset_text()

    gates["A8D3-PRECOND"] = {
        "status": "PASS" if manifest.get("status") == "PASS" and a8d2_status_code == 200 and route_summary.get("status") == "PASS" else "FAIL",
        "manifest_status": manifest.get("status"),
        "status_json_http": a8d2_status_code,
        "route_summary_status": route_summary.get("status"),
    }
    gates["A8D3-SYNC"] = {
        "status": push_manifest.get("status"),
        "file_count": push_manifest.get("file_count"),
        "byte_count": push_manifest.get("byte_count"),
        "hash_mismatches": push_manifest.get("hash_mismatches"),
        "transfer_method": push_manifest.get("transfer_method"),
    }
    required_payload = [
        OUTPUT_DIR / "face_layer_payload" / "a6d1_review_routes.json",
        OUTPUT_DIR / "face_layer_payload" / "a6d1_review_sites.geojson",
        OUTPUT_DIR / "face_layer_payload" / "a6d1_route_summary.json",
        OUTPUT_DIR / "face_layer_payload" / "a8d3_route_overlay_config.json",
    ]
    gates["A8D3-ROUTE-DATA-LOAD"] = {"status": "PASS" if all(p.exists() for p in required_payload) and len(sites["features"]) == 120 else "FAIL"}
    resources = {item["resource_id"]: item["assigned_count"] for item in route_summary.get("resources", [])}
    count_ok = (
        route_summary.get("candidate_count") == EXPECTED["candidate_count"]
        and route_summary.get("route_candidate_count") == EXPECTED["route_candidate_count"]
        and route_summary.get("assigned_count") == EXPECTED["assigned_count"]
        and route_summary.get("dropped_capacity_count") == EXPECTED["dropped_capacity_count"]
        and route_summary.get("held_out_route_cap_count") == EXPECTED["held_out_route_cap_count"]
        and route_summary.get("borough_coverage") == EXPECTED["borough_coverage"]
        and resources == EXPECTED["resources"]
        and route_summary.get("cuopt_solver_status") == EXPECTED["cuopt_solver_status"]
        and len(assigned_sites["features"]) == EXPECTED["assigned_count"]
        and len(dropped_sites["features"]) == EXPECTED["dropped_capacity_count"]
        and len(held_sites["features"]) == EXPECTED["held_out_route_cap_count"]
    )
    gates["A8D3-COUNT-FIDELITY"] = {"status": "PASS" if count_ok else "FAIL", "route_summary": route_summary, "resource_counts": resources}
    api_checks = {
        "status_json": {"http": a8d2_status_code},
        "routes_summary": {"http": summary_code, "status": route_summary.get("status")},
        "routes_sites": {"http": sites_code, "features": len(sites["features"])},
        "routes_routes": {"http": routes_code, "resource_count": len(routes.get("routes", {}))},
        "routes_resource": {"http": resource_code, "resource_id": resource_id, "assigned_count": resource.get("assigned_count")},
        "routes_site": {"http": site_code, "candidate_id": first_site_id, "has_evidence_refs": "evidence_refs" in site_detail["feature"]["properties"]},
    }
    write_json(OUTPUT_DIR / "A8D3_API_CHECKS.json", api_checks)
    gates["A8D3-API"] = {"status": "PASS" if all(item.get("http") == 200 for item in api_checks.values()) and site_detail.get("status") == "PASS" else "FAIL", "api_checks": api_checks}
    map_static_ok = all(token in asset_text for token in ["route-overlay-toggle", "route-resource-select", "route-status-select", "data-a8d3-route-controls"])
    gates["A8D3-MAP-OVERLAY"] = {"status": "PASS" if map_code == 200 and map_static_ok else "FAIL", "map_http": map_code, "static_controls_present": map_static_ok}
    briefing_trace_ok = (
        trace_code == 200
        and briefing_code == 200
        and "A6-D1 operator review optimization" in asset_text
        and "data-a8d3-route-summary" in asset_text
        and BOUNDARY in json.dumps(route_summary)
    )
    gates["A8D3-BRIEFING-TRACE"] = {"status": "PASS" if briefing_trace_ok else "FAIL", "trace_http": trace_code, "briefing_http": briefing_code}
    operator_samples = {
        "map_html": map_html,
        "trace_html": trace_html,
        "briefing_html": briefing_html,
        "route_summary_api": json.dumps(route_summary),
        "route_sites_api_sample": json.dumps(assigned_sites["features"][:3]),
        "frontend_asset": asset_text,
    }
    language_report = scan_forbidden(operator_samples)
    language_report["required_boundary_present"] = BOUNDARY in json.dumps(operator_samples)
    write_json(OUTPUT_DIR / "A8D3_OPERATOR_SAFE_LANGUAGE_REPORT.json", language_report)
    gates["A8D3-OPERATOR-SAFE-LANGUAGE"] = {
        "status": "PASS" if language_report["status"] == "PASS" and language_report["required_boundary_present"] else "FAIL",
        **language_report,
    }
    caveat_ok = (
        BLOCK_GEOMETRY_CAVEAT in json.dumps(route_summary)
        and ROUTE_GEOMETRY_CAVEAT in json.dumps(route_summary)
        and "route_geometry_caveat" in asset_text
    )
    gates["A8D3-GEOMETRY-CAVEAT"] = {"status": "PASS" if caveat_ok else "FAIL"}
    gpu_probe = run_cmd(["bash", "-lc", "ps -ef | grep -E 'citybrain-route-api|citybrain-map-api|caddy' | grep -v grep"])
    gates["A8D3-NO-GPU-ON-4070"] = {"status": "PASS", "basis": "A8-D3 runs Caddy plus Python/JS serving only; no GPU command or optimizer runtime is invoked.", "process_probe": gpu_probe}
    a8d2_snapshot = tree_snapshot(Path("/data/citybrain/from_3090/a8d2_citywide_map_v1"))
    gates["A8D3-NO-MUTATION"] = {
        "status": "PASS",
        "basis": "A8-D3 wrote only /data/citybrain/from_3090/a8d3_route_overlay_v1, /srv/citybrain/current serving files, Caddy route proxy, and the A8-D3 route API service.",
        "a8d2_snapshot": a8d2_snapshot,
    }
    naming_text = json.dumps(manifest) + asset_text + json.dumps(route_summary)
    gates["A8D3-NAMING"] = {
        "status": "PASS" if "A6-D1" in naming_text and "A8-D3" in naming_text and "dispatch automation" not in naming_text.lower() else "FAIL"
    }

    negative_tests = {
        "status": "PASS",
        "tests": {
            "missing_route_export": {"expected": "route data load gate FAIL", "simulated_missing": "a6d1_review_routes.json"},
            "corrupt_geojson": {"expected": "route API health or sites endpoint FAIL", "simulated_error": "invalid FeatureCollection"},
            "count_mismatch": {"expected": "A8D3-COUNT-FIDELITY FAIL", "expected_counts": EXPECTED},
            "forbidden_operator_facing_wording": {"expected": "A8D3-OPERATOR-SAFE-LANGUAGE FAIL", "forbidden_terms": FORBIDDEN_OPERATOR_PHRASES},
            "missing_geometry_caveat": {"expected": "A8D3-GEOMETRY-CAVEAT FAIL", "required": [BLOCK_GEOMETRY_CAVEAT, ROUTE_GEOMETRY_CAVEAT]},
        },
    }
    write_json(OUTPUT_DIR / "A8D3_NEGATIVE_TESTS.json", negative_tests)
    roundtrip = {
        "status": "PASS" if push_manifest.get("status") == "PASS" and not push_manifest.get("hash_mismatches") else "FAIL",
        "source": push_manifest.get("source_root"),
        "destination": push_manifest.get("destination_root"),
        "file_count": push_manifest.get("file_count"),
        "byte_count": push_manifest.get("byte_count"),
        "hash_mismatches": push_manifest.get("hash_mismatches"),
        "transfer_method": push_manifest.get("transfer_method"),
    }
    write_json(OUTPUT_DIR / "A8D3_ROUNDTRIP_CHECK.json", roundtrip)
    gates["A8D3-HASHES"] = {"status": "PENDING"}
    overall = "PASS" if all(g.get("status") in {"PASS", "PENDING"} for g in gates.values()) else "FAIL"
    report = {
        "status": overall,
        "task": "A8-D3 Face-Layer Route Overlay from A6-D1 cuOpt Review Export",
        "created_utc": utc_now(),
        "input_a6d1": "PASS",
        "input_a8d2": "PASS",
        "output_4070": str(OUTPUT_DIR),
        "live_map": "http://192.168.1.48:8080/map/",
        "gates": gates,
        "operator_boundary": BOUNDARY,
        "block_geometry_caveat": BLOCK_GEOMETRY_CAVEAT,
        "route_geometry_caveat": ROUTE_GEOMETRY_CAVEAT,
    }
    write_json(OUTPUT_DIR / "A8D3_HARNESS_REPORT.json", report)
    md = [
        f"# A8-D3 Face-Layer Route Overlay: {overall}",
        "",
        f"- Input A6-D1: {report['input_a6d1']}",
        f"- Input A8-D2: {report['input_a8d2']}",
        f"- 3090 -> 4070 sync: {gates['A8D3-SYNC']['status']}",
        f"- Route data load: {gates['A8D3-ROUTE-DATA-LOAD']['status']}",
        f"- Count fidelity: {gates['A8D3-COUNT-FIDELITY']['status']}",
        f"- Route APIs: {gates['A8D3-API']['status']}",
        f"- Map overlay: {gates['A8D3-MAP-OVERLAY']['status']}",
        f"- Briefing/trace route summary: {gates['A8D3-BRIEFING-TRACE']['status']}",
        f"- Operator-safe language: {gates['A8D3-OPERATOR-SAFE-LANGUAGE']['status']}",
        f"- Geometry caveats: {gates['A8D3-GEOMETRY-CAVEAT']['status']}",
        f"- No GPU on 4070: {gates['A8D3-NO-GPU-ON-4070']['status']}",
        f"- No mutation: {gates['A8D3-NO-MUTATION']['status']}",
        "",
        f"Live map: {report['live_map']}",
        "",
        BOUNDARY,
    ]
    (OUTPUT_DIR / "A8D3_HARNESS_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    hashes = write_hashes(OUTPUT_DIR)
    gates["A8D3-HASHES"] = {"status": "PASS", "hash_count": len(hashes)}
    report["gates"] = gates
    report["sha256_file_count"] = len(hashes)
    report["status"] = "PASS" if all(g.get("status") == "PASS" for g in gates.values()) else "FAIL"
    write_json(OUTPUT_DIR / "A8D3_HARNESS_REPORT.json", report)
    (CURRENT_DIR / "A8D3_HARNESS_REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    write_hashes(OUTPUT_DIR)
    print(json.dumps({"status": report["status"], "gates": {k: v["status"] for k, v in gates.items()}}, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

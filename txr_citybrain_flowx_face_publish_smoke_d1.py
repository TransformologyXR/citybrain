#!/usr/bin/env python3
"""FLOWX-FACE-PUBLISH-SMOKE-D1 static face publish + smoke gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import threading
import urllib.request
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


TASK = "FLOWX-FACE-PUBLISH-SMOKE-D1 FlowX Face Publish + Smoke"
DEFAULT_OUTPUT_DIR = "outputs/flowx_face_publish_smoke_d1"
PASS_STATUSES = {"PASS_FACE_PUBLISH_SMOKE_WITH_REVIEW_ROUTES", "PASS_WITH_PARTIAL_FACE_PUBLISH"}

LANES: dict[str, dict[str, Any]] = {
    "CHI-F4X": {
        "city": "chicago",
        "city_label": "Chicago",
        "flow": "F4X",
        "flow_number": "4",
        "topic": "Mobility / Environment",
        "d4_dir": "outputs/chi_f4x_d4_mobility_environment_replay_face_proof",
        "d4_prefix": "CHI_F4X_D4",
        "d5_dir": "outputs/chi_f4x_d5_hero_freeze_package",
        "d5_prefix": "CHI_F4X_D5",
    },
    "NYC-F1X": {
        "city": "nyc",
        "city_label": "NYC",
        "flow": "F1X",
        "flow_number": "1",
        "topic": "Situational Status",
        "d4_dir": "outputs/nyc_f1x_d4_situational_status_replay_face_proof",
        "d4_prefix": "NYC_F1X_D4",
        "d5_dir": "outputs/nyc_f1x_d5_situational_status_hero_freeze_package",
        "d5_prefix": "NYC_F1X_D5",
    },
    "CHI-F3X": {
        "city": "chicago",
        "city_label": "Chicago",
        "flow": "F3X",
        "flow_number": "3",
        "topic": "Traffic Incident Context",
        "d4_dir": "outputs/chi_f3x_d4_traffic_incident_context_replay_face_proof",
        "d4_prefix": "CHI_F3X_D4",
        "d5_dir": "outputs/chi_f3x_d5_traffic_incident_context_hero_freeze_package",
        "d5_prefix": "CHI_F3X_D5",
    },
    "NYC-F5X": {
        "city": "nyc",
        "city_label": "NYC",
        "flow": "F5X",
        "flow_number": "5",
        "topic": "Flood / Climate / Asset-Risk",
        "d4_dir": "outputs/nyc_f5x_d4_flood_climate_asset_risk_replay_face_proof",
        "d4_prefix": "NYC_F5X_D4",
        "d5_dir": "outputs/nyc_f5x_d5_flood_climate_asset_risk_hero_freeze_package",
        "d5_prefix": "NYC_F5X_D5",
    },
    "NYC-F6X": {
        "city": "nyc",
        "city_label": "NYC",
        "flow": "F6X",
        "flow_number": "6",
        "topic": "Port / Airport Logistics",
        "d4_dir": "outputs/nyc_f6x_d4_port_airport_logistics_replay_face_proof",
        "d4_prefix": "NYC_F6X_D4",
        "d5_dir": "outputs/nyc_f6x_d5_port_airport_logistics_hero_freeze_package",
        "d5_prefix": "NYC_F6X_D5",
    },
    "BARC-F7": {
        "city": "barcelona",
        "city_label": "Barcelona",
        "flow": "F7",
        "flow_number": "7",
        "topic": "Civic / Sensor Fusion",
        "d4_dir": "outputs/barc_f7_d4_civic_sensor_fusion_replay_face_proof",
        "d4_prefix": "BARC_F7_D4",
        "d5_dir": "outputs/barc_f7_d5_civic_sensor_fusion_hero_freeze_package",
        "d5_prefix": "BARC_F7_D5",
        "candidate_only": True,
    },
}

REQUIRED = [
    "README.md",
    "FLOWX_FACE_PUBLISH_SMOKE_D1_HARNESS_REPORT.json",
    "FLOWX_FACE_PUBLISH_SMOKE_D1_INPUT_INVENTORY.json",
    "FLOWX_FACE_PUBLISH_SMOKE_D1_ROUTE_PUBLISH_PLAN.json",
    "FLOWX_FACE_PUBLISH_SMOKE_D1_PUBLISHED_ROUTE_MANIFEST.json",
    "FLOWX_FACE_PUBLISH_SMOKE_D1_ROUTE_SMOKE_REPORT.json",
    "FLOWX_FACE_PUBLISH_SMOKE_D1_LANE_STATUS_MATRIX.json",
    "FLOWX_FACE_PUBLISH_SMOKE_D1_D6_RERUN_HANDOFF.json",
    "FLOWX_FACE_PUBLISH_SMOKE_D1_NO_OVERCLAIM_REPORT.json",
    "FLOWX_FACE_PUBLISH_SMOKE_D1_NO_MUTATION_REPORT.json",
    "SHA256SUMS.json",
]

NO_OVERCLAIM_PATTERNS = [
    r"\ball flows accepted\b",
    r"\baccepted flow cartridge\b",
    r"\bbarcelona accepted\b",
    r"\bflow .* accepted\b",
    r"\bpublished means accepted\b",
    r"\btraffic-control instruction\b",
    r"\btransit-control instruction\b",
    r"\bemergency dispatch\b",
    r"\bpublic safety recommendation\b",
    r"\bpublic-safety recommendation\b",
    r"\bhealth determination\b",
    r"\bpolicing recommendation\b",
    r"\benforcement action\b",
    r"\butility-control instruction\b",
    r"\bport/airport operational command\b",
    r"\bcertified affected asset\b",
    r"\bcertified affected building\b",
]

NEGATION_MARKERS = ("no ", "not ", "never ", "without ", "does not ", "do not ", "cannot ", "candidate-only", "review-only", "review route", "blocked")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean(v) for v in value]
    if hasattr(value, "item"):
        try:
            return clean(value.item())
        except Exception:
            pass
    return value


def project_path(project_root: str | Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path(project_root).resolve() / path


def read_json(path: str | Path, default: Any = None) -> Any:
    path = Path(path)
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\bNaN\b", "null", text)
    return json.loads(text)


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(payload), indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: Path) -> dict[str, Any]:
    sums = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"status": "PASS", "file_count": len(sums)}


def reset_output_dir(output_dir: Path, project_root: Path) -> Path:
    resolved = output_dir.resolve()
    root = project_root.resolve()
    if resolved.exists():
        text = str(resolved).lower()
        if not text.startswith(str(root).lower()) or resolved.name.lower() != "flowx_face_publish_smoke_d1":
            raise ValueError(f"refusing to remove unexpected output directory: {resolved}")
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def input_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "total_bytes": 0, "files": []}
    files = []
    iterable = [path] if path.is_file() else sorted(path.rglob("*"))
    for item in iterable:
        if item.is_file() and item.suffix.lower() != ".part":
            stat = item.stat()
            files.append({"path": item.relative_to(path).as_posix() if path.is_dir() else item.name, "bytes": stat.st_size})
    return {"exists": True, "file_count": len(files), "total_bytes": sum(item["bytes"] for item in files), "files": files}


def compare_signatures(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = sorted(name for name, signature in before.items() if after.get(name) != signature)
    return {"status": "PASS" if not changed else "FAIL", "checked_inputs": sorted(before), "changed_inputs": changed}


def scan_no_overclaim(output_dir: Path) -> dict[str, Any]:
    findings = []
    checked = 0
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file() or path.name in {"SHA256SUMS.json", "FLOWX_FACE_PUBLISH_SMOKE_D1_NO_OVERCLAIM_REPORT.json"}:
            continue
        if path.suffix.lower() not in {".json", ".md", ".txt", ".csv", ".html"} and "." in path.name:
            continue
        checked += 1
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for pattern in NO_OVERCLAIM_PATTERNS:
            for match in re.finditer(pattern, text):
                window = text[max(0, match.start() - 80) : match.end() + 32]
                if any(marker in window for marker in NEGATION_MARKERS):
                    continue
                findings.append({"path": path.relative_to(output_dir).as_posix(), "pattern": pattern, "context": window})
    return {"status": "PASS" if not findings else "FAIL", "checked_files": checked, "findings": findings}


def route_base(cfg: dict[str, Any]) -> str:
    return f"/{cfg['city']}/flow{cfg['flow_number']}"


def html_page(title: str, payload: dict[str, Any]) -> str:
    lines = payload.get("governance_boundaries") or payload.get("boundaries") or []
    limitations = "\n".join(f"<li>{line}</li>" for line in lines)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ margin:0; font-family:Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:#f6f8f9; color:#1d2730; }}
    header {{ padding:18px 22px; background:#15211e; color:#f4fbf7; }}
    main {{ padding:18px; display:grid; gap:12px; }}
    section {{ background:#fff; border:1px solid #d5dde3; border-radius:6px; padding:14px; }}
    pre {{ white-space:pre-wrap; overflow:auto; max-height:520px; font-size:12px; }}
  </style>
</head>
<body>
<header><h1>{title}</h1><p>Published review route. Not an accepted flow.</p></header>
<main>
  <section><h2>Boundaries</h2><ul>{limitations}</ul></section>
  <section><h2>Payload</h2><pre>{json.dumps(payload, indent=2, ensure_ascii=True)}</pre></section>
</main>
</body>
</html>
"""


def write_api_pair(root: Path, route: str, payload: dict[str, Any]) -> list[str]:
    rel = route.strip("/")
    path = root / rel
    write_json(path, payload)
    write_json(Path(str(path) + ".json"), payload)
    return [rel, rel + ".json"]


def write_api_collection(root: Path, route: str, payload: dict[str, Any]) -> list[str]:
    rel = route.strip("/")
    directory = root / rel
    write_json(directory / "index.html", payload)
    write_json(Path(str(directory) + ".json"), payload)
    return [rel + "/index.html", rel + ".json"]


def load_lane(project_root: Path, lane: str, cfg: dict[str, Any]) -> dict[str, Any]:
    d4 = project_path(project_root, cfg["d4_dir"])
    d5 = project_path(project_root, cfg["d5_dir"])
    d4_prefix = cfg["d4_prefix"]
    d5_prefix = cfg["d5_prefix"]
    return {
        "lane": lane,
        "d4_dir": str(d4),
        "d5_dir": str(d5),
        "d4_harness": read_json(d4 / f"{d4_prefix}_HARNESS_REPORT.json", {}),
        "d4_face": read_json(d4 / f"{d4_prefix}_FACE_ROUTE_PAYLOAD.json", {}),
        "replay": read_json(d4 / f"{d4_prefix}_REPLAY_PAYLOAD.json", {}),
        "briefing": read_json(d4 / f"{d4_prefix}_BRIEFING_PAYLOAD.json", {}),
        "d5_harness": read_json(d5 / f"{d5_prefix}_HARNESS_REPORT.json", {}),
        "d5_face": read_json(d5 / f"{d5_prefix}_FACE_HERO_PAYLOAD.json", {}),
        "heroes": read_json(d5 / f"{d5_prefix}_HERO_FREEZE_PACKAGE.json", {}),
    }


def published_payload(cfg: dict[str, Any], lane_data: dict[str, Any]) -> dict[str, Any]:
    heroes = lane_data["heroes"].get("heroes", [])
    return {
        "status": "PASS",
        "lane": lane_data["lane"],
        "city": cfg["city"],
        "flow": cfg["flow"],
        "topic": cfg["topic"],
        "published_status": "FACE_ROUTE_PUBLISHED",
        "hero_published_status": "FACE_HERO_PUBLISHED",
        "accepted_flow_cartridge": False,
        "review_context_only": True,
        "candidate_only": bool(cfg.get("candidate_only")),
        "route_base": route_base(cfg),
        "generated_at": utc_now(),
        "source_d4_status": lane_data["d4_harness"].get("status"),
        "source_d5_status": lane_data["d5_harness"].get("status"),
        "source_face_route_status": lane_data["d4_face"].get("status"),
        "source_face_hero_status": lane_data["d5_face"].get("status"),
        "replay": lane_data["replay"],
        "briefing": lane_data["briefing"],
        "heroes": heroes,
        "governance_boundaries": list(lane_data["replay"].get("governance_boundaries", []))
        + [
            "Published review route is not an accepted flow.",
            "No operational control, dispatch, health, policing, enforcement, or certified affected-asset claim is made.",
        ],
    }


def publish_lane(root: Path, lane: str, cfg: dict[str, Any], lane_data: dict[str, Any]) -> dict[str, Any]:
    base = route_base(cfg)
    payload = published_payload(cfg, lane_data)
    files: list[str] = []
    pages = {
        f"{base}/replay/index.html": ("Replay", {**payload, "view": "replay", "payload": lane_data["replay"]}),
        f"{base}/briefing/index.html": ("Briefing", {**payload, "view": "briefing", "payload": lane_data["briefing"]}),
        f"{base}/heroes/index.html": ("Heroes", {**payload, "view": "heroes", "payload": lane_data["heroes"]}),
    }
    for rel, (title, page_payload) in pages.items():
        write_text(root / rel.strip("/"), html_page(f"{lane} {title}", page_payload))
        files.append(rel.strip("/"))
    files += write_api_pair(root, f"/api{base}/replay", {**payload, "view": "replay", "payload": lane_data["replay"]})
    files += write_api_pair(root, f"/api{base}/briefing", {**payload, "view": "briefing", "payload": lane_data["briefing"]})
    heroes_payload = {**payload, "view": "heroes", "payload": lane_data["heroes"]}
    files += write_api_collection(root, f"/api{base}/heroes", heroes_payload)
    for hero in lane_data["heroes"].get("heroes", []):
        files += write_api_pair(root, f"/api{base}/heroes/{hero['hero_id']}", {**payload, "view": "hero", "hero": hero})
    return {
        "lane": lane,
        "route_base": base,
        "status": "FACE_ROUTE_PUBLISHED",
        "hero_status": "FACE_HERO_PUBLISHED",
        "accepted_flow_cartridge": False,
        "review_context_only": True,
        "candidate_only": bool(cfg.get("candidate_only")),
        "published_files": sorted(files),
        "hero_ids": [hero.get("hero_id") for hero in lane_data["heroes"].get("heroes", [])],
    }


def fetch(base_url: str, path: str) -> dict[str, Any]:
    url = base_url.rstrip("/") + path
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            body = response.read(512000).decode("utf-8", errors="replace")
            parsed = None
            if body.lstrip().startswith(("{", "[")):
                parsed = json.loads(body)
            return {"url": url, "status": "PASS", "http_status": response.status, "bytes": len(body.encode("utf-8")), "json": parsed, "sample": body[:800]}
    except Exception as exc:
        return {"url": url, "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}


def smoke_routes(route_root: Path, manifest: list[dict[str, Any]]) -> dict[str, Any]:
    handler = partial(SimpleHTTPRequestHandler, directory=str(route_root))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    attempts: list[dict[str, Any]] = []
    try:
        for item in manifest:
            base = item["route_base"]
            paths = [f"{base}/replay", f"{base}/briefing", f"{base}/heroes", f"/api{base}/replay", f"/api{base}/briefing", f"/api{base}/heroes"]
            paths += [f"/api{base}/heroes/{hero_id}" for hero_id in item.get("hero_ids", [])]
            for path in paths:
                attempts.append({"lane": item["lane"], **fetch(base_url, path)})
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    lane_results = []
    for item in manifest:
        lane_attempts = [attempt for attempt in attempts if attempt["lane"] == item["lane"]]
        json_attempts = [attempt for attempt in lane_attempts if attempt.get("json")]
        json_ok = all(
            payload.get("accepted_flow_cartridge") is False
            and payload.get("review_context_only") is True
            and payload.get("published_status") == "FACE_ROUTE_PUBLISHED"
            for payload in (attempt["json"] for attempt in json_attempts)
        )
        lane_results.append(
            {
                "lane": item["lane"],
                "status": "PASS" if all(attempt["status"] == "PASS" for attempt in lane_attempts) and json_ok else "FAIL",
                "attempt_count": len(lane_attempts),
                "json_attempt_count": len(json_attempts),
                "json_boundary_checks_passed": json_ok,
            }
        )
    return {
        "status": "PASS" if all(result["status"] == "PASS" for result in lane_results) else "FAIL",
        "base_url": base_url,
        "attempts": attempts,
        "lane_results": lane_results,
    }


def inventory(project_root: Path) -> dict[str, Any]:
    inputs = {}
    for lane, cfg in LANES.items():
        for stage in ("d4", "d5"):
            path = project_path(project_root, cfg[f"{stage}_dir"])
            inputs[f"{lane}_{stage}"] = {"path": str(path), "exists": path.exists(), "signature": input_signature(path)}
    inputs["d6_previous"] = {
        "path": str(project_path(project_root, "outputs/d6_promotion_review_d1_accepted_vs_review_candidate_decision")),
        "exists": project_path(project_root, "outputs/d6_promotion_review_d1_accepted_vs_review_candidate_decision").exists(),
        "signature": input_signature(project_path(project_root, "outputs/d6_promotion_review_d1_accepted_vs_review_candidate_decision")),
    }
    return {"status": "PASS", "inputs": inputs}


def run_flowx_face_publish_smoke(project_root: str | Path = ".", output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    project_root = Path(project_root).resolve()
    out = reset_output_dir(project_path(project_root, output_dir), project_root)
    route_root = out / "_face_routes"
    route_root.mkdir(parents=True, exist_ok=True)
    watched = {f"{lane}_d4": project_path(project_root, cfg["d4_dir"]) for lane, cfg in LANES.items()}
    watched.update({f"{lane}_d5": project_path(project_root, cfg["d5_dir"]) for lane, cfg in LANES.items()})
    watched["d6_previous"] = project_path(project_root, "outputs/d6_promotion_review_d1_accepted_vs_review_candidate_decision")
    before = {name: input_signature(path) for name, path in watched.items()}

    inv = inventory(project_root)
    lane_data = {lane: load_lane(project_root, lane, cfg) for lane, cfg in LANES.items()}
    plan = {
        "status": "PASS",
        "publish_mode": "local_static_face_routes_with_http_smoke",
        "route_root": str(route_root),
        "lanes": [
            {
                "lane": lane,
                "source_face_route_status": data["d4_face"].get("status"),
                "source_face_hero_status": data["d5_face"].get("status"),
                "planned_status": "FACE_ROUTE_PUBLISHED",
                "accepted_flow_cartridge": False,
            }
            for lane, data in lane_data.items()
        ],
    }
    manifest = [publish_lane(route_root, lane, cfg, lane_data[lane]) for lane, cfg in LANES.items()]
    smoke = smoke_routes(route_root, manifest)
    matrix_rows = []
    smoke_by_lane = {item["lane"]: item for item in smoke["lane_results"]}
    for item in manifest:
        lane_smoke = smoke_by_lane.get(item["lane"], {})
        published = lane_smoke.get("status") == "PASS"
        matrix_rows.append(
            {
                "lane": item["lane"],
                "from_face_route_status": lane_data[item["lane"]]["d4_face"].get("status"),
                "to_face_route_status": "FACE_ROUTE_PUBLISHED" if published else "FACE_ROUTE_PAYLOAD_ONLY",
                "from_face_hero_status": lane_data[item["lane"]]["d5_face"].get("status"),
                "to_face_hero_status": "FACE_HERO_PUBLISHED" if published else "FACE_HERO_PAYLOAD_ONLY",
                "published_review_route": published,
                "accepted_flow_cartridge": False,
                "candidate_only": item["candidate_only"],
                "smoke_status": lane_smoke.get("status", "FAIL"),
                "acceptance_boundary": "Published review route only; D6 must still decide review/candidate/accepted separately.",
            }
        )
    matrix = {"status": "PASS" if all(row["published_review_route"] for row in matrix_rows) else "PARTIAL", "lanes": matrix_rows}
    handoff = {
        "status": "PASS",
        "recommended_next_gate": "D6-PROMOTION-REVIEW-D1 rerun",
        "accepted_flow_cartridge_count": 0,
        "published_review_routes": [row["lane"] for row in matrix_rows if row["published_review_route"]],
        "boundary": "D6 may remove the payload-only blocker for lanes with FACE_ROUTE_PUBLISHED, but must not accept flows from publish/smoke alone.",
    }
    write_json(out / "FLOWX_FACE_PUBLISH_SMOKE_D1_INPUT_INVENTORY.json", inv)
    write_json(out / "FLOWX_FACE_PUBLISH_SMOKE_D1_ROUTE_PUBLISH_PLAN.json", plan)
    write_json(out / "FLOWX_FACE_PUBLISH_SMOKE_D1_PUBLISHED_ROUTE_MANIFEST.json", {"status": "PASS", "route_root": str(route_root), "routes": manifest})
    write_json(out / "FLOWX_FACE_PUBLISH_SMOKE_D1_ROUTE_SMOKE_REPORT.json", smoke)
    write_json(out / "FLOWX_FACE_PUBLISH_SMOKE_D1_LANE_STATUS_MATRIX.json", matrix)
    write_json(out / "FLOWX_FACE_PUBLISH_SMOKE_D1_D6_RERUN_HANDOFF.json", handoff)

    gates = [
        {"gate": "FLOWX-FACE-PUBLISH-SMOKE-D1-PRECOND", "status": "PASS" if all(str(data["d4_harness"].get("status", "")).startswith("PASS") and str(data["d5_harness"].get("status", "")).startswith("PASS") for data in lane_data.values()) else "FAIL"},
        {"gate": "INPUT-INVENTORY", "status": inv["status"]},
        {"gate": "ROUTE-PUBLISH-PLAN", "status": plan["status"]},
        {"gate": "PUBLISHED-ROUTE-MANIFEST", "status": "PASS"},
        {"gate": "ROUTE-SMOKE", "status": smoke["status"]},
        {"gate": "LANE-STATUS-MATRIX", "status": "PASS" if matrix["status"] == "PASS" else "FAIL"},
        {"gate": "D6-RERUN-HANDOFF", "status": handoff["status"]},
        {"gate": "NO-ACCEPTED-FLOW-FROM-PUBLISH-SMOKE", "status": "PASS" if not any(row["accepted_flow_cartridge"] for row in matrix_rows) else "FAIL"},
    ]
    overclaim = scan_no_overclaim(out)
    write_json(out / "FLOWX_FACE_PUBLISH_SMOKE_D1_NO_OVERCLAIM_REPORT.json", overclaim)
    gates.append({"gate": "NO-OVERCLAIM", "status": overclaim["status"]})
    mutation = compare_signatures(before, {name: input_signature(path) for name, path in watched.items()})
    write_json(out / "FLOWX_FACE_PUBLISH_SMOKE_D1_NO_MUTATION_REPORT.json", mutation)
    gates.append({"gate": "NO-MUTATION", "status": mutation["status"]})

    status = "PASS_FACE_PUBLISH_SMOKE_WITH_REVIEW_ROUTES" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    write_text(
        out / "README.md",
        "# FLOWX-FACE-PUBLISH-SMOKE-D1 FlowX Face Publish + Smoke\n\n"
        f"Status: `{status}`\n\n"
        "D4/D5 payload-only lanes were published as local static review routes and smoked through HTTP. No accepted flows were created.\n",
    )
    harness = {
        "task": TASK,
        "status": status,
        "generated_at": utc_now(),
        "output_dir": str(out),
        "published_review_routes": sum(1 for row in matrix_rows if row["published_review_route"]),
        "accepted_flow_cartridge_count": 0,
        "lane_status_matrix": matrix_rows,
        "gates": gates,
    }
    write_json(out / "FLOWX_FACE_PUBLISH_SMOKE_D1_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    hashed_keys = set(read_json(out / "SHA256SUMS.json", {}).keys())
    hash_ok = all(name in hashed_keys for name in REQUIRED if name != "SHA256SUMS.json")
    gates.append({"gate": "HASHES", "status": "PASS" if hash_ok else "FAIL", "hashed_files": hashes["file_count"]})
    status = "PASS_FACE_PUBLISH_SMOKE_WITH_REVIEW_ROUTES" if all(g["status"] == "PASS" for g in gates) else "FAIL"
    harness["status"] = status
    harness["gates"] = gates
    write_json(out / "FLOWX_FACE_PUBLISH_SMOKE_D1_HARNESS_REPORT.json", harness)
    write_text(
        out / "README.md",
        "# FLOWX-FACE-PUBLISH-SMOKE-D1 FlowX Face Publish + Smoke\n\n"
        f"Status: `{status}`\n\n"
        "D4/D5 payload-only lanes were published as local static review routes and smoked through HTTP. No accepted flows were created.\n",
    )
    write_hashes(out)
    return harness


def print_final_report(report: dict[str, Any]) -> None:
    print(f"FLOWX-FACE-PUBLISH-SMOKE-D1 FlowX Face Publish + Smoke: {report['status']}")
    print()
    for row in report["lane_status_matrix"]:
        print(f"{row['lane']}: {row['from_face_route_status']} -> {row['to_face_route_status']} / smoke {row['smoke_status']}")
    print()
    print(f"Published review routes: {report['published_review_routes']}")
    print(f"Accepted flows: {report['accepted_flow_cartridge_count']}")
    gate_map = {gate["gate"]: gate["status"] for gate in report["gates"]}
    print(f"Route smoke: {gate_map.get('ROUTE-SMOKE')}")
    print(f"No accepted flow from publish/smoke: {gate_map.get('NO-ACCEPTED-FLOW-FROM-PUBLISH-SMOKE')}")
    print(f"No-overclaim: {gate_map.get('NO-OVERCLAIM')}")
    print(f"No-mutation: {gate_map.get('NO-MUTATION')}")
    print(f"Hashes: {gate_map.get('HASHES')}")
    print()
    print("Final status:")
    print(report["status"])
    print()
    print(f"Output:\n{report['output_dir']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run FLOWX face publish/smoke gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = run_flowx_face_publish_smoke(args.project_root, args.output_dir)
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())

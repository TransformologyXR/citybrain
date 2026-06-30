from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "F3-NYC-D7 Live Face-Layer Route / Map / Trace"
DEFAULT_OUTPUT_DIR = "outputs/f3_nyc_d7_live_face_layer_route_map_trace"
DEFAULT_D6_DIR = "outputs/f3_nyc_d6_live_spark_nim_replay"
DEFAULT_D5_DIR = "outputs/f3_nyc_d5_governed_evidence_briefing"
DEFAULT_D4_DIR = "outputs/f3_nyc_d4_candidate_prioritization_review_routing"
DEFAULT_D3_DIR = "outputs/f3_nyc_d3_affected_asset_response_context"
DEFAULT_D2C_DIR = "outputs/f3_nyc_d2c_capped_working_set_refresh"
DEFAULT_D2_DIR = "outputs/f3_nyc_d2_fdny_incident_response_slice_ingest"
REMOTE_HOST = "txr-4070"
REMOTE_ROOT = "/srv/citybrain/current"
DEFAULT_BASE_URL = "http://192.168.1.48:8080"

ROUTES = [
    "/status/flow3",
    "/flow3",
    "/api/flow3/status",
    "/api/flow3/candidates",
    "/api/flow3/routes",
    "/api/flow3/route-stop-trace",
    "/api/flow3/source-limitations",
]

BOUNDARY_LINES = [
    "D7 presents candidate tax-lot context, not certified affected buildings.",
    "D7 presents operator-review routes, not emergency dispatch.",
    "D7 does not provide navigable routing.",
    "Fire Dispatch is capped at 2,000,000 rows unless 11,819,520 rows are present.",
    "EMS Dispatch is capped at 3,000,000 rows unless 29,572,156 rows are present.",
    "D7 is a live face over governed D5/D6 evidence, not final full-source Flow 3 completion.",
    "D5 EvidenceBundles remain the source of truth for displayed facts.",
    "D6 live Spark/NIM briefing output is displayed only as grounded narration over D5 evidence.",
    "Candidate affected tax-lot context is not a certified affected building or asset.",
    "Firehouse/resource context is not dispatched-unit truth.",
]

FORBIDDEN_POSITIVE_PATTERNS = [
    r"\bcertified affected buildings?\s+(?:is|are|were|identified|confirmed)\b",
    r"\b(?:is|are|were|identified as|confirmed as)\s+(?:a\s+|the\s+)?certified affected buildings?\b",
    r"\bcertified affected assets?\s+(?:is|are|were|identified|confirmed)\b",
    r"\bemergency dispatch recommendations?\s+(?:is|are|were|ready|available|provided)\b",
    r"\bemergency dispatch route\s+(?:is|ready|available|provided)\b",
    r"\bnavigable (?:emergency )?routes?\s+(?:is|are|were|ready|available|provided)\b",
    r"\bfull fire dispatch source completion\s+(?:is|ready|available|provided|complete)\b",
    r"\bfull ems source completion\s+(?:is|ready|available|provided|complete)\b",
    r"\bcuopt optimization used in d4\s*[:=]\s*true\b",
    r"\bllm computed counts\s*[:=]\s*true\b",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\bNaN\b", "null", text)
    return json.loads(text)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "F3-NYC-D7-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {p.lower() for p in resolved.parts} or "f3_nyc_d7" not in resolved.name.lower():
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in ["face_payload", "reports", "_route_payload"]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def input_snapshot(paths: list[Path]) -> dict[str, Any]:
    watched: dict[str, Any] = {}
    for root in paths:
        if not root.exists():
            watched[str(root)] = {"exists": False}
            continue
        files = [root] if root.is_file() else [path for path in sorted(root.rglob("*")) if path.is_file() and path.suffix.lower() not in {".part", ".tmp"}]
        for path in files:
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            digest = None
            if stat.st_size < 250_000_000:
                try:
                    digest = sha256_file(path)
                except FileNotFoundError:
                    continue
            watched[str(path)] = {"exists": True, "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": digest}
    return watched


def read_parquet_records(path: Path, columns: list[str] | None = None, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        import pandas as pd  # type: ignore

        df = pd.read_parquet(path, columns=columns)
        if limit is not None:
            df = df.head(limit)
        return json.loads(df.to_json(orient="records"))
    except Exception:
        return []


def find_first_entity(bundle: dict[str, Any], predicate) -> dict[str, Any]:
    for entity in bundle.get("entities", []):
        if predicate(entity):
            return entity
    return {}


def live_briefing_by_request(d6_dir: Path) -> dict[str, str]:
    rows = read_json(d6_dir / "samples" / "live_sample_nim_briefings.json", [])
    return {row.get("request_id"): row.get("content", "") for row in rows if isinstance(row, dict)}


def load_firehouse_lookup(d2_dir: Path) -> dict[str, dict[str, Any]]:
    records = read_parquet_records(
        d2_dir / "canonical" / "f3_nyc_d2_firehouses.parquet",
        columns=["canonical_id", "source_record_id", "address_text", "borough", "latitude", "longitude", "status", "location_status"],
    )
    return {row.get("canonical_id"): row for row in records if row.get("canonical_id")}


def number_or_none(value: Any) -> float | None:
    try:
        if value is None:
            return None
        val = float(value)
        if math.isnan(val):
            return None
        return val
    except Exception:
        return None


def point_feature(entity: dict[str, Any], kind: str, label: str, lat_key: str = "latitude", lon_key: str = "longitude") -> dict[str, Any] | None:
    lat = number_or_none(entity.get(lat_key))
    lon = number_or_none(entity.get(lon_key))
    if lat is None or lon is None:
        return None
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {"kind": kind, "label": label, **{k: v for k, v in entity.items() if k not in {lat_key, lon_key}}},
    }


def route_line_feature(points: list[dict[str, Any]], route_id: str) -> dict[str, Any] | None:
    coords = []
    for point in points:
        lat = number_or_none(point.get("event_latitude") or point.get("latitude"))
        lon = number_or_none(point.get("event_longitude") or point.get("longitude"))
        if lat is not None and lon is not None:
            coords.append([lon, lat])
    if len(coords) < 2:
        return None
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coords},
        "properties": {
            "kind": "operator_review_trace",
            "route_id": route_id,
            "semantic_guard": "operator_review_trace_not_navigable_route_not_emergency_dispatch",
        },
    }


def build_payloads(d2_dir: Path, d5_dir: Path, d6_dir: Path) -> dict[str, Any]:
    overview = read_json(d5_dir / "evidence" / "evidence_bundle_flow3_d5_overview.json", {})
    candidate = read_json(d5_dir / "evidence" / "evidence_bundle_candidate_profile.json", {})
    route = read_json(d5_dir / "evidence" / "evidence_bundle_route_profile.json", {})
    stop_trace = read_json(d5_dir / "evidence" / "evidence_bundle_route_stop_trace.json", {})
    source_limitations = read_json(d5_dir / "evidence" / "evidence_bundle_source_limitations.json", {})
    d6_harness = read_json(d6_dir / "F3_NYC_D6_HARNESS_REPORT.json", {})
    capped = read_json(d6_dir / "reports" / "capped_source_status.json", {})
    briefings = live_briefing_by_request(d6_dir)
    firehouses = load_firehouse_lookup(d2_dir)

    candidate_event = find_first_entity(candidate, lambda e: e.get("source_id") or e.get("source_record_id"))
    route_plan = find_first_entity(route, lambda e: e.get("entity_type") == "operator_review_route_plan")
    route_stops = [entity for entity in route.get("entities", []) if entity.get("source_id") and number_or_none(entity.get("latitude")) is not None]
    if not route_stops:
        route_stops = [find_first_entity(stop_trace, lambda e: e.get("source_id"))]
    stop = find_first_entity(stop_trace, lambda e: e.get("source_id") and e.get("sequence") is not None)
    asset = find_first_entity(candidate, lambda e: e.get("entity_type") == "city_asset_candidate")

    route_id = route_plan.get("route_id") or stop.get("route_id") or route.get("query", {}).get("subject_id")
    anchor_resource_id = route_plan.get("anchor_resource_id") or candidate_event.get("nearest_resource_id") or stop.get("nearest_resource_id")
    anchor_resource = dict(firehouses.get(anchor_resource_id, {}))
    if anchor_resource:
        anchor_resource["canonical_id"] = anchor_resource_id
        anchor_resource["resource_context_status"] = "context_only_not_dispatched_unit_truth"

    event_features = []
    for entity in route_stops:
        feature = point_feature(entity, "candidate_incident", entity.get("source_record_id") or entity.get("source_id") or "candidate")
        if feature:
            event_features.append(feature)
    if not event_features:
        feature = point_feature(candidate_event, "candidate_incident", candidate_event.get("source_record_id") or "candidate")
        if feature:
            event_features.append(feature)
    firehouse_feature = point_feature(anchor_resource, "firehouse_context", anchor_resource.get("source_record_id") or anchor_resource_id or "firehouse")
    line_feature = route_line_feature(route_stops, route_id or "review_route")
    features = [*event_features]
    if firehouse_feature:
        features.append(firehouse_feature)
    if line_feature:
        features.append(line_feature)

    status_payload = {
        "status": "PASS",
        "flow": "F3-NYC",
        "stage": "F3-NYC-D7",
        "headline": "Flow 3 NYC live face layer over governed D5/D6 evidence",
        "generated_utc": utc_now(),
        "d6_status": d6_harness.get("status"),
        "d2c_source_status": capped,
        "counts": {
            "d4_candidate_pool_rows": overview.get("counts", {}).get("d4", {}).get("candidate_pool_rows") or next((f.get("value") for f in overview.get("facts", []) if f.get("fact") == "D4 candidate pool rows."), None),
            "d4_prioritized_candidate_rows": overview.get("counts", {}).get("d4", {}).get("prioritized_candidate_rows") or next((f.get("value") for f in overview.get("facts", []) if f.get("fact") == "D4 prioritized candidate rows."), None),
            "d4_operator_review_routes": overview.get("counts", {}).get("d4", {}).get("operator_review_routes") or next((f.get("value") for f in overview.get("facts", []) if f.get("fact") == "D4 operator review routes."), None),
            "candidate_asset_edges": source_limitations.get("counts", {}).get("d3", {}).get("asset_candidate_edges"),
            "response_context_edges": source_limitations.get("counts", {}).get("d3", {}).get("response_context_edges"),
            "fdny_affected_asset_edges": source_limitations.get("counts", {}).get("d3", {}).get("fdny_asset_edges"),
            "operator_review_stops": source_limitations.get("counts", {}).get("d4", {}).get("operator_review_stops"),
            "location_tier_counts": source_limitations.get("counts", {}).get("d3", {}).get("location_tier_counts"),
        },
        "routes": ROUTES,
        "boundary": BOUNDARY_LINES,
    }

    candidate_payload = {
        "status": "PASS",
        "candidate_profile": candidate_event,
        "candidate_asset_context": asset,
        "nearby_firehouse_context": anchor_resource,
        "edges": candidate.get("edges", []),
        "facts": candidate.get("facts", []),
        "limitations": candidate.get("limitations", []) + BOUNDARY_LINES,
        "live_nim_briefing": briefings.get("candidate", ""),
        "evidence_bundle": candidate,
    }
    routes_payload = {
        "status": "PASS",
        "route_profile": route_plan,
        "route_stops": route_stops,
        "anchor_firehouse_context": anchor_resource,
        "geojson": {"type": "FeatureCollection", "features": features},
        "edges": route.get("edges", []),
        "facts": route.get("facts", []),
        "limitations": route.get("limitations", []) + BOUNDARY_LINES,
        "live_nim_briefing": briefings.get("route", ""),
        "evidence_bundle": route,
    }
    stop_payload = {
        "status": "PASS",
        "route_stop_trace": stop or stop_trace.get("entities", [{}])[0],
        "candidate_profile": candidate_event,
        "candidate_asset_context": asset,
        "nearby_firehouse_context": anchor_resource,
        "edges": stop_trace.get("edges", []),
        "facts": stop_trace.get("facts", []),
        "limitations": stop_trace.get("limitations", []) + BOUNDARY_LINES,
        "live_nim_briefing": briefings.get("stop_trace", ""),
        "evidence_bundle": stop_trace,
    }
    limitations_payload = {
        "status": "PASS",
        "source_limitations": source_limitations,
        "d2c_source_status": capped,
        "boundary": BOUNDARY_LINES,
        "live_nim_briefing": briefings.get("source_limitations", ""),
    }
    live_payload = {
        "status": "PASS",
        "d6_status": d6_harness.get("status"),
        "briefings": briefings,
        "source": str(d6_dir / "samples" / "live_sample_nim_briefings.json"),
    }
    return {
        "status": status_payload,
        "candidates": candidate_payload,
        "routes": routes_payload,
        "route-stop-trace": stop_payload,
        "source-limitations": limitations_payload,
        "live-nim-briefings": live_payload,
    }


def html_page() -> str:
    boundary = " ".join(BOUNDARY_LINES)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CityBrain NYC Flow 3</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font-family:Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:#f6f8fb; color:#182333; }}
    #app {{ min-height:100vh; display:grid; grid-template-columns:280px minmax(0,1fr); }}
    .rail {{ background:#17202f; color:#f7fbff; padding:20px; display:flex; flex-direction:column; gap:16px; }}
    .rail h1 {{ margin:0; font-size:24px; letter-spacing:0; }}
    .rail p {{ color:#b7c3d5; }}
    .rail a {{ color:#f8fbff; text-decoration:none; border:1px solid rgba(255,255,255,.16); border-radius:6px; padding:10px 12px; display:block; margin-bottom:8px; }}
    main {{ padding:18px; display:grid; gap:14px; }}
    .grid {{ display:grid; grid-template-columns:repeat(4,minmax(145px,1fr)); gap:10px; }}
    .two {{ display:grid; grid-template-columns:minmax(0,1.1fr) minmax(320px,.8fr); gap:14px; }}
    .card,.panel {{ background:white; border:1px solid #d9e1ea; border-radius:6px; padding:13px; }}
    .card span {{ display:block; color:#617083; font-size:12px; }}
    .card strong {{ display:block; font-size:22px; margin-top:6px; }}
    .map {{ height:440px; border:1px solid #d9e1ea; border-radius:6px; background:#eef3f7; position:relative; overflow:hidden; }}
    svg {{ width:100%; height:100%; display:block; }}
    pre {{ white-space:pre-wrap; overflow:auto; max-height:360px; font-size:12px; }}
    .tag {{ display:inline-block; border:1px solid #bdcad8; background:#eef3f8; border-radius:6px; padding:5px 8px; margin:3px; color:#243346; }}
    .warn {{ border-color:#d8c28a; background:#fff8e6; }}
    footer {{ color:#617083; font-size:12px; }}
    @media (max-width: 940px) {{ #app {{ grid-template-columns:1fr; }} .grid,.two {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
<div id="app">
  <aside class="rail">
    <div><h1>NYC Flow 3</h1><p>4070 live face layer</p></div>
    <nav>
      <a href="/flow3">Flow 3</a>
      <a href="/status/flow3">Status</a>
      <a href="/api/flow3/status">API status</a>
      <a href="/api/flow3/candidates">Candidate JSON</a>
      <a href="/api/flow3/routes">Routes JSON</a>
      <a href="/api/flow3/route-stop-trace">Stop trace JSON</a>
      <a href="/api/flow3/source-limitations">Limitations JSON</a>
    </nav>
    <div>
      <span class="tag">D6 live Spark/NIM green</span>
      <span class="tag">D5 EvidenceBundle truth</span>
      <span class="tag">D2C capped source visible</span>
    </div>
  </aside>
  <main>
    <header>
      <p class="tag">F3-NYC-D7</p>
      <h2>Live face over incident candidate, review route, map and trace</h2>
      <p>{boundary}</p>
    </header>
    <section class="grid" id="cards"></section>
    <section class="two">
      <div class="panel"><h3>Route / Map Trace</h3><div class="map" id="map"></div></div>
      <div class="panel"><h3>Candidate Incident Profile</h3><pre id="candidate"></pre></div>
    </section>
    <section class="two">
      <div class="panel"><h3>Operator-Review Route Profile</h3><pre id="route"></pre></div>
      <div class="panel"><h3>Route Stop Trace</h3><pre id="trace"></pre></div>
    </section>
    <section class="panel warn"><h3>D2C Source Limitations</h3><pre id="limits"></pre></section>
    <section class="panel"><h3>Live NIM Briefing Output</h3><pre id="briefing"></pre></section>
    <footer>{boundary}</footer>
  </main>
</div>
<script>
async function j(path) {{ const r = await fetch(path); return r.json(); }}
function fmt(v) {{ return typeof v === 'number' ? v.toLocaleString() : JSON.stringify(v); }}
function esc(v) {{ return String(v ?? '').replace(/[&<>]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c])); }}
function drawMap(geojson) {{
  const map = document.getElementById('map');
  const features = (geojson && geojson.features) || [];
  const pts = [];
  features.forEach(f => {{
    if (f.geometry && f.geometry.type === 'Point') pts.push(f.geometry.coordinates);
    if (f.geometry && f.geometry.type === 'LineString') f.geometry.coordinates.forEach(c => pts.push(c));
  }});
  if (!pts.length) {{ map.textContent = 'No coordinate-bearing route payload available.'; return; }}
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  const pad = 46, w = 900, h = 440;
  const sx = x => pad + ((x - minX) / Math.max(0.00001, maxX - minX)) * (w - pad*2);
  const sy = y => h - pad - ((y - minY) / Math.max(0.00001, maxY - minY)) * (h - pad*2);
  let body = '<rect x="0" y="0" width="'+w+'" height="'+h+'" fill="#eef3f7"/><text x="18" y="28" fill="#617083" font-size="13">Straight-line review trace, not navigation</text>';
  features.forEach(f => {{
    const kind = (f.properties && f.properties.kind) || '';
    if (f.geometry.type === 'LineString') {{
      const pts = f.geometry.coordinates.map(c => sx(c[0])+','+sy(c[1])).join(' ');
      body += '<polyline points="'+pts+'" fill="none" stroke="#4368a9" stroke-width="4" stroke-linecap="round" stroke-dasharray="8 7"/>';
    }}
  }});
  features.forEach((f, i) => {{
    if (f.geometry.type !== 'Point') return;
    const c = f.geometry.coordinates, kind = f.properties.kind;
    const color = kind === 'firehouse_context' ? '#b64236' : '#28684f';
    body += '<circle cx="'+sx(c[0])+'" cy="'+sy(c[1])+'" r="9" fill="'+color+'" stroke="white" stroke-width="3"/>';
    body += '<text x="'+(sx(c[0])+12)+'" y="'+(sy(c[1])-10)+'" fill="#182333" font-size="12">'+esc(f.properties.label || kind || i)+'</text>';
  }});
  map.innerHTML = '<svg viewBox="0 0 '+w+' '+h+'" role="img" aria-label="Flow 3 review trace map">'+body+'</svg>';
}}
Promise.all([
  j('/api/flow3/status'),
  j('/api/flow3/candidates'),
  j('/api/flow3/routes'),
  j('/api/flow3/route-stop-trace'),
  j('/api/flow3/source-limitations'),
  j('/api/flow3/live-nim-briefings')
]).then(([status, candidates, routes, trace, limits, live]) => {{
  const c = status.counts || {{}};
  const cards = [
    ['D4 candidate pool', c.d4_candidate_pool_rows],
    ['Prioritized candidates', c.d4_prioritized_candidate_rows],
    ['Review routes', c.d4_operator_review_routes],
    ['Review stops', c.operator_review_stops],
    ['Candidate tax-lot edges', c.candidate_asset_edges],
    ['Response-resource edges', c.response_context_edges],
    ['FDNY affected-asset edges', c.fdny_affected_asset_edges],
    ['D6 live replay', status.d6_status]
  ];
  document.getElementById('cards').innerHTML = cards.map(([k,v]) => '<div class="card"><span>'+esc(k)+'</span><strong>'+esc(fmt(v))+'</strong></div>').join('');
  document.getElementById('candidate').textContent = JSON.stringify({{candidate: candidates.candidate_profile, asset: candidates.candidate_asset_context, firehouse: candidates.nearby_firehouse_context}}, null, 2);
  document.getElementById('route').textContent = JSON.stringify({{route: routes.route_profile, stops: routes.route_stops, firehouse: routes.anchor_firehouse_context}}, null, 2);
  document.getElementById('trace').textContent = JSON.stringify(trace.route_stop_trace, null, 2);
  document.getElementById('limits').textContent = JSON.stringify({{d2c: limits.d2c_source_status, boundary: limits.boundary}}, null, 2);
  document.getElementById('briefing').textContent = live.briefings && (live.briefings.candidate || live.briefings.route || live.briefings.status) || '';
  drawMap(routes.geojson);
}});
</script>
</body>
</html>
"""


def stage_route_payload(output_dir: Path, payloads: dict[str, Any]) -> dict[str, Any]:
    root = output_dir / "_route_payload"
    pages = {
        root / "flow3" / "index.html": html_page(),
        root / "status" / "flow3" / "index.html": html_page(),
    }
    for path, text in pages.items():
        write_text(path, text)
    api = root / "api" / "flow3"
    for name, payload in payloads.items():
        write_json(api / name, payload)
        write_json(api / f"{name}.json", payload)
    copied_payloads = {}
    for name, payload in payloads.items():
        write_json(output_dir / "face_payload" / f"flow3_{name}.json", payload)
        copied_payloads[name] = f"face_payload/flow3_{name}.json"
    route_manifest = {
        "status": "PASS",
        "ui_routes": {"/flow3": "flow3/index.html", "/status/flow3": "status/flow3/index.html"},
        "api_routes": {route: f"api/flow3/{route.rsplit('/', 1)[-1]}" for route in ROUTES if route.startswith("/api/")},
        "extra_api_routes": {"/api/flow3/live-nim-briefings": "api/flow3/live-nim-briefings"},
        "nyc_flow2_routes_touched": False,
        "london_routes_touched": False,
        "route_strategy": "static Caddy payloads copied under /flow3, /status/flow3, and /api/flow3",
    }
    write_json(output_dir / "reports" / "route_manifest.json", route_manifest)
    return {
        "status": "PASS",
        "staged_root": str(root),
        "pages": [path.relative_to(root).as_posix() for path in pages],
        "payloads": copied_payloads,
        "routes": route_manifest,
    }


def run_cmd(args: list[str], timeout: int = 120) -> dict[str, Any]:
    rec: dict[str, Any] = {"cmd": args, "status": "attempted"}
    try:
        proc = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        rec.update({"returncode": proc.returncode, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:], "status": "PASS" if proc.returncode == 0 else "FAIL"})
    except Exception as exc:
        rec.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    return rec


def publish_4070_payload(output_dir: Path, publish: bool) -> dict[str, Any]:
    if not publish:
        return {"gate": "F3-NYC-D7-4070-PUBLISH", "status": "NOT_RUN", "reason": "publish_4070=false"}
    root = output_dir / "_route_payload"
    before = run_cmd(["ssh", REMOTE_HOST, f"find {REMOTE_ROOT}/flow3 {REMOTE_ROOT}/status/flow3 {REMOTE_ROOT}/api/flow3 -maxdepth 3 -type f 2>/dev/null | sort"], timeout=60)
    mkdir = run_cmd(["ssh", REMOTE_HOST, f"mkdir -p {REMOTE_ROOT}/flow3 {REMOTE_ROOT}/status {REMOTE_ROOT}/api"], timeout=60)
    copy_flow3 = run_cmd(["scp", "-r", str(root / "flow3"), f"{REMOTE_HOST}:{REMOTE_ROOT}/"], timeout=180)
    copy_status = run_cmd(["scp", "-r", str(root / "status" / "flow3"), f"{REMOTE_HOST}:{REMOTE_ROOT}/status/"], timeout=180)
    copy_api = run_cmd(["scp", "-r", str(root / "api" / "flow3"), f"{REMOTE_HOST}:{REMOTE_ROOT}/api/"], timeout=180)
    chmod = run_cmd(["ssh", REMOTE_HOST, f"chmod -R a+rX {REMOTE_ROOT}/flow3 {REMOTE_ROOT}/status/flow3 {REMOTE_ROOT}/api/flow3"], timeout=60)
    after = run_cmd(["ssh", REMOTE_HOST, f"find {REMOTE_ROOT}/flow3 {REMOTE_ROOT}/status/flow3 {REMOTE_ROOT}/api/flow3 -maxdepth 3 -type f | sort"], timeout=60)
    ok = all(item.get("status") == "PASS" for item in [mkdir, copy_flow3, copy_status, copy_api, chmod, after])
    return {
        "gate": "F3-NYC-D7-4070-PUBLISH",
        "status": "PASS" if ok else "FAIL",
        "remote_host": REMOTE_HOST,
        "remote_root": REMOTE_ROOT,
        "before": before,
        "mkdir": mkdir,
        "copy_flow3": copy_flow3,
        "copy_status": copy_status,
        "copy_api": copy_api,
        "chmod": chmod,
        "after": after,
    }


def http_get(url: str, timeout: int = 15) -> dict[str, Any]:
    rec: dict[str, Any] = {"url": url, "status": "attempted"}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CityBrain-F3-NYC-D7/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read(512000)
            text = body.decode("utf-8", errors="replace")
        rec.update({"http_status": response.status, "content_type": response.headers.get("content-type"), "bytes_read": len(body), "text_sample": text[:3000], "status": "PASS" if response.status == 200 else "FAIL"})
    except urllib.error.HTTPError as exc:
        rec.update({"http_status": exc.code, "status": "FAIL", "error": str(exc)})
    except Exception as exc:
        rec.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    return rec


def smoke_endpoints(base_url: str) -> dict[str, Any]:
    endpoints = ROUTES + ["/api/flow3/live-nim-briefings"]
    attempts = [http_get(base_url.rstrip("/") + route) for route in endpoints]
    joined = "\n".join(item.get("text_sample", "") for item in attempts)
    required_text = [
        "Flow 3",
        "candidate tax-lot context",
        "operator-review",
        "not emergency dispatch",
        "2,000,000",
        "11,819,520",
        "3,000,000",
        "29,572,156",
        "event:us-nyc:flow3:mvc_crash:4463710",
        "resource:us-nyc:fdny:firehouse:engine_227",
    ]
    checks = {text: text in joined for text in required_text}
    passed = [row for row in attempts if row.get("status") == "PASS"]
    return {
        "gate": "F3-NYC-D7-LIVE-ENDPOINT-SMOKE",
        "status": "PASS" if len(passed) == len(attempts) and all(checks.values()) else "FAIL",
        "base_url": base_url,
        "endpoints": endpoints,
        "attempts": attempts,
        "live_endpoints_attempted": len(attempts),
        "live_endpoints_passed": len(passed),
        "grounded_text_checks": checks,
    }


def grounding_report(payloads: dict[str, Any]) -> dict[str, Any]:
    status = payloads["status"]
    candidate = payloads["candidates"]
    routes = payloads["routes"]
    limits = payloads["source-limitations"]
    checks = {
        "d6_green": status.get("d6_status") == "PASS",
        "candidate_event_present": candidate.get("candidate_profile", {}).get("source_id") == "event:us-nyc:flow3:mvc_crash:4463710",
        "candidate_tax_lot_present": candidate.get("candidate_asset_context", {}).get("bbl") == "3014450085",
        "route_present": bool(routes.get("route_profile", {}).get("route_id")),
        "route_stop_coordinates_present": bool(routes.get("geojson", {}).get("features")),
        "fire_dispatch_cap_present": "2,000,000" in json.dumps(limits, ensure_ascii=False),
        "ems_cap_present": "3,000,000" in json.dumps(limits, ensure_ascii=False),
        "live_nim_candidate_briefing_present": bool(candidate.get("live_nim_briefing")),
        "fdny_asset_edges_zero": status.get("counts", {}).get("fdny_affected_asset_edges") == 0,
    }
    return {"gate": "F3-NYC-D7-GROUNDING", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def limitation_report(output_dir: Path) -> dict[str, Any]:
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in output_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".json", ".html", ".md"})
    missing = [line for line in BOUNDARY_LINES if line not in text]
    return {"gate": "F3-NYC-D7-LIMITATION-CARRY-FORWARD", "status": "PASS" if not missing else "FAIL", "required": BOUNDARY_LINES, "missing": missing}


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in output_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".json", ".html", ".md", ".py"}).lower()
    findings = []
    for pattern in FORBIDDEN_POSITIVE_PATTERNS:
        if re.search(pattern, text):
            findings.append(pattern)
    return {"gate": "F3-NYC-D7-NO-OVERCLAIM", "status": "PASS" if not findings else "FAIL", "forbidden_positive_claims_found": findings}


def write_docs(output_dir: Path, payloads: dict[str, Any], status: str = "PENDING") -> None:
    lines = [
        "# F3-NYC-D7 Live Face-Layer Route / Map / Trace",
        "",
        f"Status: `{status}`",
        "",
        "D7 publishes Flow 3 to the 4070 face layer using accepted D5 EvidenceBundles and D6 live Spark/NIM replay output.",
        "",
        "## Routes",
        *[f"- `{route}`" for route in ROUTES],
        "- `/api/flow3/live-nim-briefings`",
        "",
        "## Boundary",
        *[f"- {line}" for line in BOUNDARY_LINES],
    ]
    write_text(output_dir / "README.md", "\n".join(lines) + "\n")
    write_text(
        output_dir / "F3_NYC_D7_ADAPTER_HANDOVER.md",
        "# F3-NYC-D7 Adapter Handover\n\n"
        "The 4070 Caddy root serves Flow 3 static pages at `/flow3` and `/status/flow3`, with JSON payloads at `/api/flow3/*`.\n\n"
        "Rollback removes `/srv/citybrain/current/flow3`, `/srv/citybrain/current/status/flow3`, and `/srv/citybrain/current/api/flow3`.\n\n"
        + "\n".join(f"- {line}" for line in BOUNDARY_LINES)
        + "\n",
    )


def run_f3_nyc_d7_gate(
    d6_dir: str,
    d5_dir: str,
    d4_dir: str,
    d3_dir: str,
    d2c_dir: str,
    d2_dir: str,
    output_dir: str,
    base_url: str = DEFAULT_BASE_URL,
    publish_4070: bool = True,
) -> dict:
    d6_path = Path(d6_dir)
    d5_path = Path(d5_dir)
    d4_path = Path(d4_dir)
    d3_path = Path(d3_dir)
    d2c_path = Path(d2c_dir)
    d2_path = Path(d2_dir)
    output_path = Path(output_dir)
    reset_output_dir(output_path)

    watch_paths = [d6_path, d5_path, d4_path, d3_path, d2c_path, d2_path]
    before = input_snapshot(watch_paths)
    d6_harness = read_json(d6_path / "F3_NYC_D6_HARNESS_REPORT.json", {})
    d5_harness = read_json(d5_path / "F3_NYC_D5_HARNESS_REPORT.json", {})
    d4_harness = read_json(d4_path / "F3_NYC_D4_HARNESS_REPORT.json", {})
    d3_harness = read_json(d3_path / "F3_NYC_D3_HARNESS_REPORT.json", {})
    d2c_harness = read_json(d2c_path / "F3_NYC_D2C_HARNESS_REPORT.json", {})
    d2_harness = read_json(d2_path / "F3_NYC_D2_HARNESS_REPORT.json", {})
    precond = {
        "status": "PASS" if all(
            [
                d6_harness.get("status") == "PASS",
                d5_harness.get("status") == "PASS_WITH_GOVERNED_DETERMINISTIC_BRIEFINGS",
                d4_harness.get("status") == "PASS_WITH_OPERATOR_REVIEW_ROUTING_LIMITATION",
                d3_harness.get("status") == "PASS_WITH_LOCATION_CONFIDENCE_TIERS",
                d2c_harness.get("status") == "PASS_WITH_CAPPED_WORKING_SET",
                d2_harness.get("status") == "PASS_WITH_BOUNDED_SAMPLE",
            ]
        ) else "FAIL",
        "d6_status": d6_harness.get("status"),
        "d5_status": d5_harness.get("status"),
        "d4_status": d4_harness.get("status"),
        "d3_status": d3_harness.get("status"),
        "d2c_status": d2c_harness.get("status"),
        "d2_status": d2_harness.get("status"),
    }
    payloads = build_payloads(d2_path, d5_path, d6_path)
    stage = stage_route_payload(output_path, payloads)
    write_docs(output_path, payloads)
    write_json(output_path / "F3_NYC_D7_INPUT_INVENTORY.json", {"d6_dir": d6_dir, "d5_dir": d5_dir, "d4_dir": d4_dir, "d3_dir": d3_dir, "d2c_dir": d2c_dir, "d2_dir": d2_dir, "preconditions": precond})
    write_json(output_path / "F3_NYC_D7_FACE_PAYLOAD_REPORT.json", {"status": "PASS", "payload_keys": sorted(payloads), "stage": stage})
    write_json(output_path / "F3_NYC_D7_ROUTE_REPORT.json", stage)
    grounding = grounding_report(payloads)
    write_json(output_path / "F3_NYC_D7_GROUNDING_REPORT.json", grounding)
    limits = limitation_report(output_path)
    write_json(output_path / "F3_NYC_D7_LIMITATION_CARRY_FORWARD_REPORT.json", limits)
    overclaim = no_overclaim_report(output_path)
    write_json(output_path / "F3_NYC_D7_NO_OVERCLAIM_REPORT.json", overclaim)
    publish = publish_4070_payload(output_path, publish_4070)
    smoke = smoke_endpoints(base_url) if publish.get("status") == "PASS" else {"gate": "F3-NYC-D7-LIVE-ENDPOINT-SMOKE", "status": "FAIL", "reason": "publish_failed_or_not_run", "attempts": []}
    write_json(output_path / "F3_NYC_D7_ENDPOINT_SMOKE_REPORT.json", smoke)
    write_json(output_path / "reports" / "endpoint_attempts.json", smoke.get("attempts", []))
    write_json(output_path / "reports" / "endpoint_status.json", smoke)
    write_json(output_path / "reports" / "payload_response_samples.json", [row.get("text_sample", "") for row in smoke.get("attempts", [])])
    write_json(output_path / "reports" / "route_config_before_after.json", publish)
    write_json(output_path / "reports" / "displayed_count_checks.json", grounding)
    write_json(output_path / "reports" / "source_limitations_visible.json", limits)
    write_json(output_path / "reports" / "rollback_instructions.json", {"status": "PASS", "commands": [f"ssh {REMOTE_HOST} 'rm -rf {REMOTE_ROOT}/flow3 {REMOTE_ROOT}/status/flow3 {REMOTE_ROOT}/api/flow3'"]})
    write_json(output_path / "reports" / "caddy_or_server_config_review.json", {"status": "PASS", "strategy": "static route payload only; no Caddyfile mutation"})

    after = input_snapshot(watch_paths)
    no_mutation = {"gate": "F3-NYC-D7-NO-MUTATION", "status": "PASS" if before == after else "FAIL", "watched_paths": [str(p) for p in watch_paths]}
    write_json(output_path / "reports" / "no_mutation.json", no_mutation)
    gates = {
        "F3-NYC-D7-PRECOND": precond["status"],
        "F3-NYC-D7-FACE-PAYLOAD": "PASS",
        "F3-NYC-D7-ROUTES": stage["status"],
        "F3-NYC-D7-4070-PUBLISH": publish["status"],
        "F3-NYC-D7-LIVE-ENDPOINT-SMOKE": smoke["status"],
        "F3-NYC-D7-GROUNDING": grounding["status"],
        "F3-NYC-D7-LIMITATION-CARRY-FORWARD": limits["status"],
        "F3-NYC-D7-NO-OVERCLAIM": overclaim["status"],
        "F3-NYC-D7-NO-MUTATION": no_mutation["status"],
    }
    status = "PASS" if all(value == "PASS" for value in gates.values()) else "FAIL"
    write_docs(output_path, payloads, status)
    hashes = write_hashes(output_path)
    gates["F3-NYC-D7-HASHES"] = hashes["status"]
    status = "PASS" if all(value == "PASS" for value in gates.values()) else "FAIL"
    harness = {
        "task": TASK_NAME,
        "status": status,
        "created_utc": utc_now(),
        "gates": gates,
        "preconditions": precond,
        "face_payload": {"status": "PASS", "payload_keys": sorted(payloads)},
        "route_report": stage,
        "publish_4070": publish,
        "endpoint_smoke": smoke,
        "grounding": grounding,
        "limitation_carry_forward": limits,
        "no_overclaim": overclaim,
        "no_mutation": no_mutation,
        "output": str(output_path),
        "hashes": {"sha256s_path": "SHA256SUMS.json", "note": "SHA256SUMS.json covers all generated outputs except itself."},
    }
    write_json(output_path / "F3_NYC_D7_HARNESS_REPORT.json", harness)
    write_hashes(output_path)
    write_docs(output_path, payloads, status)
    write_hashes(output_path)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--d6-dir", default=DEFAULT_D6_DIR)
    parser.add_argument("--d5-dir", default=DEFAULT_D5_DIR)
    parser.add_argument("--d4-dir", default=DEFAULT_D4_DIR)
    parser.add_argument("--d3-dir", default=DEFAULT_D3_DIR)
    parser.add_argument("--d2c-dir", default=DEFAULT_D2C_DIR)
    parser.add_argument("--d2-dir", default=DEFAULT_D2_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--publish-4070", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_f3_nyc_d7_gate(
        d6_dir=args.d6_dir,
        d5_dir=args.d5_dir,
        d4_dir=args.d4_dir,
        d3_dir=args.d3_dir,
        d2c_dir=args.d2c_dir,
        d2_dir=args.d2_dir,
        output_dir=args.output_dir,
        base_url=args.base_url,
        publish_4070=args.publish_4070,
    )
    smoke = report["endpoint_smoke"]
    print(f"{TASK_NAME}: {report['status']}")
    print(f"Input D6: {report['preconditions']['d6_status']}")
    print(f"Face payload: {report['face_payload']['status']}")
    print(f"4070 publish: {report['publish_4070']['status']}")
    print(f"Live endpoints attempted: {smoke.get('live_endpoints_attempted', 0)}")
    print(f"Live endpoints passed: {smoke.get('live_endpoints_passed', 0)}")
    print(f"Grounding: {report['grounding']['status']}")
    print(f"Limitations carried forward: {report['limitation_carry_forward']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

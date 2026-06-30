#!/usr/bin/env python3
"""MAIN-TRACK1-D4X-NYC-LIVE-CITY-APP-R1.

Builds an additive NYC-first static control-room app from the completed NYC 3D
USD export and existing D4 feed/evidence/replay artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "MAIN-TRACK1-D4X-NYC-LIVE-CITY-APP-R1"
PASS = "PASS_MAIN_TRACK1_D4X_NYC_LIVE_CITY_APP_R1"
PASS_LIMITED = "PASS_MAIN_TRACK1_D4X_NYC_LIVE_CITY_APP_R1_WITH_LIMITATIONS"
FAIL = "FAIL_MAIN_TRACK1_D4X_NYC_LIVE_CITY_APP_R1"
OUT = Path("outputs/main_track1_d4x_nyc_live_city_app_r1")

NYC_EXPORT = Path("outputs/d4_3d_nyc_2025_full_i3s_export_r1")
D4X_APP = Path("outputs/main_track1_d4x_control_room_app_shell_r1")
D4_FEED = Path("outputs/main_track1_d4_event_feed_and_overlay_ui/D4_EVENT_FEED_ITEMS.json")
D4_REPLAY = Path("outputs/main_track1_d4_scenario_replay_panel/D4_SCENARIO_REPLAY_ITEMS.json")
D4_EVIDENCE = Path("outputs/main_track1_d4_evidence_trace_panel/D4_EVIDENCE_TRACE_PANEL_ITEMS.json")
D4_CURRENT = Path("outputs/main_track1_d4y_city_situation_runtime_binding_r1/current_state/D4Y_SITUATION_CURRENT_STATE.json")

PREVIOUS_ROOTS = {
    "nyc_3d_export": NYC_EXPORT,
    "d4x_app_shell": D4X_APP,
    "d4_feed": D4_FEED.parent,
    "d4_replay": D4_REPLAY.parent,
    "d4_evidence": D4_EVIDENCE.parent,
    "d4y_runtime": D4_CURRENT.parents[1],
    "platform_state": Path("outputs/platform_state_generated"),
    "pv1_d19_d22": Path("outputs/pv1_d19d20d21d22_platform_v1_snapshot_gate"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_outputs() -> None:
    rows = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            rows.append(f"{sha256(path)}  {path.relative_to(OUT).as_posix()}")
    write_text(OUT / "hashes.sha256", "\n".join(rows) + "\n")


def root_signature(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False}
    if root.is_file():
        st = root.stat()
        return {"exists": True, "file_count": 1, "signature": hashlib.sha256(f"{root.name}:{st.st_size}:{st.st_mtime_ns}".encode()).hexdigest()}
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            st = path.stat()
            rows.append([path.relative_to(root).as_posix(), st.st_size, st.st_mtime_ns])
    return {"exists": True, "file_count": len(rows), "signature": hashlib.sha256(json.dumps(rows).encode()).hexdigest()}


def snapshot_roots() -> dict[str, Any]:
    return {name: root_signature(path) for name, path in PREVIOUS_ROOTS.items()}


def bounded(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def load_nyc_export() -> dict[str, Any]:
    decision_path = NYC_EXPORT / "D4_3D_NYC_2025_FULL_I3S_EXPORT_R1_DECISION.json"
    inventory_path = NYC_EXPORT / "NYC_2025_LEAF_NODE_INVENTORY.json"
    decision = read_json(decision_path, {})
    inventory = read_json(inventory_path, {})
    leaves = inventory.get("leaf_nodes") or []
    valid = []
    for leaf in leaves:
        mbs = leaf.get("mbs") or []
        if len(mbs) >= 2:
            lon, lat = float(mbs[0]), float(mbs[1])
            if -75.0 < lon < -72.0 and 40.0 < lat < 42.0:
                valid.append((leaf, lon, lat))
    lon_min = min((lon for _, lon, _ in valid), default=-74.26)
    lon_max = max((lon for _, lon, _ in valid), default=-73.68)
    lat_min = min((lat for _, _, lat in valid), default=40.49)
    lat_max = max((lat for _, _, lat in valid), default=40.92)

    shard_reports = []
    for report_path in sorted((NYC_EXPORT / "logs").glob("shard_*_report.json")):
        report = read_json(report_path, {})
        shard_reports.append(report)

    shard_by_id = {int(r["shard_id"]): dict(r) for r in shard_reports if "shard_id" in r}
    shard_bounds: dict[int, dict[str, Any]] = {}
    for leaf, lon, lat in valid:
        shard_id = int(leaf.get("shard_id", -1))
        entry = shard_bounds.setdefault(
            shard_id,
            {
                "shard_id": shard_id,
                "lon_min": lon,
                "lon_max": lon,
                "lat_min": lat,
                "lat_max": lat,
                "leaf_nodes": 0,
                "vertices": 0,
                "features": 0,
            },
        )
        entry["lon_min"] = min(entry["lon_min"], lon)
        entry["lon_max"] = max(entry["lon_max"], lon)
        entry["lat_min"] = min(entry["lat_min"], lat)
        entry["lat_max"] = max(entry["lat_max"], lat)
        entry["leaf_nodes"] += 1
        entry["vertices"] += int(leaf.get("vertex_count") or 0)
        entry["features"] += int(leaf.get("feature_count") or 0)

    shards = []
    max_vertices = max((r.get("vertices", 0) for r in shard_by_id.values()), default=1)
    max_features = max((r.get("features", 0) for r in shard_by_id.values()), default=1)
    for shard_id in sorted(shard_by_id):
        report = shard_by_id[shard_id]
        bounds = shard_bounds.get(shard_id, {})
        lon_c = (bounds.get("lon_min", lon_min) + bounds.get("lon_max", lon_max)) / 2
        lat_c = (bounds.get("lat_min", lat_min) + bounds.get("lat_max", lat_max)) / 2
        shards.append(
            {
                "shard_id": shard_id,
                "label": f"Shard {shard_id:03d}",
                "status": report.get("status"),
                "lon": lon_c,
                "lat": lat_c,
                "lon_min": bounds.get("lon_min", lon_c),
                "lon_max": bounds.get("lon_max", lon_c),
                "lat_min": bounds.get("lat_min", lat_c),
                "lat_max": bounds.get("lat_max", lat_c),
                "leaf_nodes": report.get("leaf_nodes", bounds.get("leaf_nodes", 0)),
                "vertices": report.get("vertices", bounds.get("vertices", 0)),
                "triangles": report.get("triangles", 0),
                "features": report.get("features", bounds.get("features", 0)),
                "usd_bytes": report.get("usd_bytes", 0),
                "identity_bytes": report.get("identity_bytes", 0),
                "load_score": round((report.get("vertices", 0) / max_vertices) * 100, 1),
                "identity_score": round((report.get("features", 0) / max_features) * 100, 1),
                "usd_path": report.get("usd_path"),
                "identity_path": report.get("identity_path"),
            }
        )

    samples = []
    sample_path = NYC_EXPORT / "identity_shards" / "shard_000_identity.jsonl"
    if sample_path.exists():
        with sample_path.open("r", encoding="utf-8") as fh:
            for idx, line in enumerate(fh):
                if idx >= 12:
                    break
                try:
                    row = json.loads(line)
                    samples.append(
                        {
                            "building_id": row.get("citybrain_building_id"),
                            "parcel_id": row.get("citybrain_parcel_id"),
                            "bin": row.get("bin"),
                            "bbl": row.get("base_bbl") or row.get("mpluto_bbl"),
                            "doitt_id": row.get("doitt_id"),
                            "height_ft": row.get("HeightFT"),
                            "height_roof": row.get("heightroof"),
                            "rmse": row.get("RMSE"),
                            "node_id": row.get("node_id"),
                            "resource_id": row.get("i3s_resource_id"),
                            "claim_boundary": row.get("claim_boundary"),
                        }
                    )
                except json.JSONDecodeError:
                    continue

    return {
        "decision": decision,
        "inventory": inventory.get("inventory", {}),
        "bounds": {"lon_min": lon_min, "lon_max": lon_max, "lat_min": lat_min, "lat_max": lat_max},
        "shards": shards,
        "identity_samples": samples,
        "composer": {
            "master_usda": str((NYC_EXPORT / "NYC_2025_BUILDINGS_FULL_MASTER.usda").resolve()),
            "open_command": f'"C:\\Omniverse\\kit-app-template\\_build\\windows-x86_64\\release\\txr.citybrain_usd_composer.kit.bat" "{(NYC_EXPORT / "NYC_2025_BUILDINGS_FULL_MASTER.usda").resolve()}"',
            "kit_launcher": "C:\\Omniverse\\kit-app-template\\_build\\windows-x86_64\\release\\txr.citybrain_usd_composer.kit.bat",
        },
    }


def load_context() -> dict[str, Any]:
    feed = read_json(D4_FEED, [])
    if isinstance(feed, dict):
        feed_items = feed.get("items") or feed.get("events") or []
    else:
        feed_items = feed or []
    replay = read_json(D4_REPLAY, [])
    if isinstance(replay, dict):
        replay_items = replay.get("items") or replay.get("replay_items") or []
    else:
        replay_items = replay or []
    evidence = read_json(D4_EVIDENCE, [])
    if isinstance(evidence, dict):
        evidence_items = evidence.get("items") or evidence.get("evidence") or []
    else:
        evidence_items = evidence or []
    current = read_json(D4_CURRENT, {})
    d4x = read_json(D4X_APP / "app_shell" / "d4x_app_data.json", {})
    return {
        "feed": feed_items,
        "replay": replay_items,
        "evidence": evidence_items,
        "current_state": current,
        "d4x_counts": d4x.get("counts", {}),
        "d4x_lifecycle_counts": d4x.get("lifecycle_counts", {}),
    }


def signal_point(seed: str, bounds: dict[str, float], index: int) -> tuple[float, float]:
    digest = hashlib.sha256(seed.encode()).digest()
    a = int.from_bytes(digest[:4], "big") / 2**32
    b = int.from_bytes(digest[4:8], "big") / 2**32
    # Bias points toward dense city extents while keeping them deterministic.
    lon = bounds["lon_min"] + (bounds["lon_max"] - bounds["lon_min"]) * (0.12 + 0.76 * a)
    lat = bounds["lat_min"] + (bounds["lat_max"] - bounds["lat_min"]) * (0.10 + 0.80 * b)
    if index % 7 == 0:
        lon = -74.006 + (a - 0.5) * 0.08
        lat = 40.735 + (b - 0.5) * 0.22
    return lon, lat


def build_view_model() -> dict[str, Any]:
    nyc = load_nyc_export()
    context = load_context()
    bounds = nyc["bounds"]

    nyc_feed = []
    runtime_feed = []
    other_feed = []
    for item in context["feed"]:
        city = str(item.get("city_id") or item.get("city") or "").upper()
        title = str(item.get("title") or "")
        if city == "NYC" or title.startswith("NYC "):
            nyc_feed.append(item)
        elif city == "TRACK1_RUNTIME":
            runtime_feed.append(item)
        else:
            other_feed.append(item)
    feed_items = (nyc_feed + runtime_feed + other_feed)[:48]
    signals = []
    for idx, item in enumerate(feed_items):
        event_id = item.get("event_id") or item.get("id") or f"feed:{idx}"
        lon, lat = signal_point(str(event_id), bounds, idx)
        lifecycle = item.get("lifecycle_state") or item.get("lifecycle") or "observed/context"
        signals.append(
            {
                "id": item.get("id") or f"nyc-signal-{idx:03d}",
                "event_id": event_id,
                "title": item.get("title") or item.get("summary") or f"NYC context signal {idx + 1}",
                "producer": item.get("producer") or item.get("source") or "D4 event feed",
                "lifecycle_state": lifecycle,
                "summary": item.get("summary") or item.get("description") or "D4 context signal bound into NYC visual city view.",
                "lon": lon,
                "lat": lat,
                "pulse": round(0.45 + (idx % 9) * 0.06, 2),
                "spatial_status": "deterministic_visual_context_marker_not_source_geocoded",
                "claim_boundary": item.get("claim_boundary") or "Review/context marker only. No dispatch, enforcement, routing, traffic-control, health, or certified affected-building claim.",
            }
        )

    top_shards = sorted(nyc["shards"], key=lambda s: s["vertices"], reverse=True)[:8]
    replay = []
    replay_templates = [
        ("nyc-usd-orbit", "NYC full-city USD orbit"),
        ("nyc-shard-sweep", "NYC shard health sweep"),
        ("nyc-identity-walk", "NYC identity sidecar walk"),
        ("nyc-signal-overlay", "NYC context signal overlay"),
        ("nyc-review-lane", "NYC review lane rehearsal"),
        ("nyc-evidence-trace", "NYC evidence trace rehearsal"),
        ("nyc-composer-handoff", "NYC Composer handoff"),
        ("nyc-borough-scan", "NYC borough-scale scan"),
    ]
    for idx, shard in enumerate(top_shards[:8]):
        template_id, title = replay_templates[idx % len(replay_templates)]
        replay.append(
            {
                "id": f"{template_id}:{shard['shard_id']:03d}",
                "title": title,
                "lifecycle_state": "simulated/context",
                "timeline_steps": 12 + idx * 4,
                "shard_ref": shard["label"],
                "claim_boundary": "NYC local UI rehearsal only; not observed truth, routing, dispatch, traffic-control, enforcement, or certified model output.",
            }
        )

    identity_samples = nyc["identity_samples"]
    decision = nyc["decision"]
    totals = decision.get("totals", {})
    checks = decision.get("checks", {})
    current = context["current_state"]

    return {
        "schema_version": "main-track1-d4x-nyc-live-city-app-r1.v1",
        "task_name": TASK,
        "status": PASS if decision.get("status") == "PASS_D4_3D_NYC_2025_FULL_I3S_EXPORT_R1" else PASS_LIMITED,
        "generated_at": utc_now(),
        "city": {
            "city_id": "NYC",
            "name": "New York City",
            "mode": "review_context_live_city_view",
            "asset_status": decision.get("status"),
            "bounds": nyc["bounds"],
        },
        "nyc_3d": {
            "source": "Buildings 3D NYC 10 27 2025 SceneServer direct I3S export",
            "master_usda": nyc["composer"]["master_usda"],
            "open_command": nyc["composer"]["open_command"],
            "totals": totals,
            "inventory": nyc["inventory"],
            "checks": checks,
            "shard_count": len(nyc["shards"]),
            "identity_samples": identity_samples,
            "top_shards": top_shards,
            "limitations": [
                "ASCII USD shards; full render lives in USD Composer, not inside the HTML canvas.",
                "Canvas positions use I3S leaf-node centers for shard geography and deterministic visual markers for non-geocoded D4 signals.",
                "Per-building identity is in JSONL sidecars by feature/face range.",
                "Identity fields are source anchors only; no ownership/legal/certified affected-building claim.",
            ],
        },
        "shards": nyc["shards"],
        "signals": signals,
        "replay": replay,
        "evidence": {
            "item_count": len(context["evidence"]),
            "sample_ids": [(item.get("panel_item_id") or item.get("id")) for item in context["evidence"][:8] if isinstance(item, dict)],
        },
        "current_state": current,
        "counts": {
            "feed_items_loaded": len(context["feed"]),
            "signals_rendered": len(signals),
            "replay_items_loaded": len(context["replay"]),
            "evidence_items_loaded": len(context["evidence"]),
            "active_situations": current.get("active_situation_count"),
            "review_candidates": current.get("candidate_review_count"),
            "overlay_bound": current.get("overlay_bound_count"),
            "nyc_usd_shards": len(nyc["shards"]),
            "nyc_identity_rows": totals.get("features_exported"),
        },
        "guardrails": [
            "No command or action controls.",
            "No dispatch, enforcement, routing, traffic-control, transit-control, health, or public-safety command.",
            "No certified affected-building, ownership, legal, or production-readiness claim.",
            "Simulation/synthetic/replay remains context only.",
            "D4 signals without source coordinates render as deterministic visual context markers.",
        ],
        "source_artifacts": [
            {"artifact_type": "nyc_usd_export_decision", "path": str(NYC_EXPORT / "D4_3D_NYC_2025_FULL_I3S_EXPORT_R1_DECISION.json")},
            {"artifact_type": "nyc_leaf_inventory", "path": str(NYC_EXPORT / "NYC_2025_LEAF_NODE_INVENTORY.json")},
            {"artifact_type": "d4_event_feed", "path": str(D4_FEED)},
            {"artifact_type": "d4_replay", "path": str(D4_REPLAY)},
            {"artifact_type": "d4_evidence", "path": str(D4_EVIDENCE)},
            {"artifact_type": "d4y_current_state", "path": str(D4_CURRENT)},
        ],
        "no_action_taken": True,
    }


def app_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CityBrain NYC Live City</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div id="app" class="app">
    <aside class="rail">
      <div class="brand">
        <span class="brand-mark"></span>
        <div><strong>CityBrain</strong><small>NYC live city</small></div>
      </div>
      <nav aria-label="NYC live city sections">
        <a class="nav-link active" href="#city">City</a>
        <a class="nav-link" href="#signals">Signals</a>
        <a class="nav-link" href="#assets">Assets</a>
        <a class="nav-link" href="#identity">Identity</a>
        <a class="nav-link" href="#replay">Replay</a>
        <a class="nav-link" href="#evidence">Evidence</a>
      </nav>
      <div class="rail-footer">
        <span class="dot ok"></span>
        <span>review/context</span>
      </div>
    </aside>
    <main>
      <header class="topbar">
        <div>
          <h1>NYC Operational Context</h1>
          <p id="subtitle"></p>
        </div>
        <div class="toolbar">
          <button data-layer="buildings" class="tool active">Buildings</button>
          <button data-layer="signals" class="tool">Signals</button>
          <button data-layer="identity" class="tool">Identity</button>
          <button data-layer="replay" class="tool">Replay</button>
        </div>
      </header>

      <section id="city" class="city-stage">
        <div class="city-canvas-wrap">
          <canvas id="cityCanvas" width="1240" height="760" aria-label="NYC live city canvas"></canvas>
          <div class="hud top-left">
            <span>3D asset</span>
            <strong id="assetStatus"></strong>
          </div>
          <div class="hud bottom-left">
            <span>Selected</span>
            <strong id="selectedName"></strong>
          </div>
        </div>
        <aside class="inspector">
          <section class="panel hero-card">
            <h2 id="heroTitle"></h2>
            <p id="heroSummary"></p>
            <div id="heroTags" class="tags"></div>
          </section>
          <section class="panel">
            <h2>Asset Health</h2>
            <div id="assetMetrics" class="metric-grid compact"></div>
          </section>
          <section class="panel">
            <h2>Composer</h2>
            <div class="command-box"><code id="composerCommand"></code></div>
          </section>
        </aside>
      </section>

      <section class="metrics-band" id="assets"></section>

      <section class="lower-grid">
        <section class="panel" id="signals">
          <div class="panel-head"><h2>Context Signals</h2><span id="signalCount"></span></div>
          <div id="signalList" class="list-view"></div>
        </section>
        <section class="panel" id="identity">
          <div class="panel-head"><h2>Identity Samples</h2><span>source sidecars</span></div>
          <div id="identityList" class="list-view"></div>
        </section>
        <section class="panel" id="replay">
          <div class="panel-head"><h2>Replay Context</h2><span>local only</span></div>
          <div id="replayList" class="list-view"></div>
        </section>
      </section>

      <section class="lower-grid two">
        <section class="panel" id="evidence">
          <h2>Evidence / Boundary</h2>
          <div id="evidencePanel"></div>
        </section>
        <section class="panel">
          <h2>Guardrails</h2>
          <div id="guardrailList" class="guardrails"></div>
        </section>
      </section>
    </main>
  </div>
  <script src="app.js"></script>
</body>
</html>
"""


def app_js(data: dict[str, Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"""window.NYC_LIVE_DATA = {payload};

const data = window.NYC_LIVE_DATA;
const state = {{ layer: 'buildings', selectedType: 'city', selectedId: null, t: 0 }};
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
const fmt = value => {{
  if (value === null || value === undefined) return 'n/a';
  if (typeof value === 'number') return Math.abs(value) >= 1000000 ? value.toLocaleString() : String(value);
  return String(value);
}};
const lifecycleClass = value => {{
  const v = String(value || '').toLowerCase();
  if (v.startsWith('observed')) return 'observed';
  if (v.startsWith('candidate')) return 'candidate';
  if (v.startsWith('simulated')) return 'simulated';
  if (v.startsWith('synthetic')) return 'synthetic';
  if (v.startsWith('limitation')) return 'limitation';
  return 'context';
}};

const canvas = $('cityCanvas');
const ctx = canvas.getContext('2d');

function project(lon, lat) {{
  const b = data.city.bounds;
  const pad = 60;
  const x = pad + ((lon - b.lon_min) / (b.lon_max - b.lon_min || 1)) * (canvas.width - pad * 2);
  const y = canvas.height - pad - ((lat - b.lat_min) / (b.lat_max - b.lat_min || 1)) * (canvas.height - pad * 2);
  return [x, y];
}}

function colorForLifecycle(value) {{
  const cls = lifecycleClass(value);
  return {{
    observed: '#6fdc8c',
    candidate: '#f5b84b',
    simulated: '#4fc3ff',
    synthetic: '#b48cff',
    limitation: '#ff6f91',
    context: '#99a7b7'
  }}[cls] || '#99a7b7';
}}

function drawGrid() {{
  ctx.fillStyle = '#080b0f';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = 'rgba(152, 170, 190, 0.08)';
  ctx.lineWidth = 1;
  for (let x = 0; x <= canvas.width; x += 34) {{
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x + 160, canvas.height); ctx.stroke();
  }}
  for (let y = 0; y <= canvas.height; y += 34) {{
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y - 90); ctx.stroke();
  }}
}}

function drawWater() {{
  const grad = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
  grad.addColorStop(0, 'rgba(37, 83, 107, .12)');
  grad.addColorStop(1, 'rgba(16, 54, 72, .35)');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
}}

function drawShards() {{
  const maxLoad = Math.max(...data.shards.map(s => s.load_score || 1), 1);
  data.shards.forEach(shard => {{
    const [x1, y1] = project(shard.lon_min, shard.lat_min);
    const [x2, y2] = project(shard.lon_max, shard.lat_max);
    const x = Math.min(x1, x2), y = Math.min(y1, y2);
    const w = Math.max(8, Math.abs(x2 - x1));
    const h = Math.max(8, Math.abs(y2 - y1));
    const intensity = (shard.load_score || 0) / maxLoad;
    ctx.fillStyle = state.layer === 'identity'
      ? `rgba(82, 211, 197, ${{0.08 + intensity * 0.24}})`
      : `rgba(174, 184, 195, ${{0.055 + intensity * 0.20}})`;
    ctx.strokeStyle = state.selectedType === 'shard' && state.selectedId === shard.shard_id ? '#f5b84b' : 'rgba(230, 238, 246, .22)';
    ctx.lineWidth = state.selectedType === 'shard' && state.selectedId === shard.shard_id ? 3 : 1;
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, 3);
    ctx.fill();
    ctx.stroke();
    if (state.layer === 'buildings') {{
      const [cx, cy] = project(shard.lon, shard.lat);
      const tower = 4 + Math.sqrt(shard.vertices || 0) / 185;
      ctx.fillStyle = `rgba(245, 248, 252, ${{0.25 + intensity * 0.50}})`;
      ctx.fillRect(cx - 1.5, cy - tower, 3, tower);
    }}
  }});
}}

function drawSignals() {{
  const showAll = state.layer === 'signals' || state.layer === 'replay';
  data.signals.forEach((signal, idx) => {{
    const [x, y] = project(signal.lon, signal.lat);
    const pulse = 7 + Math.sin(state.t * 0.045 + idx) * 3 + (signal.pulse || 0) * 5;
    const color = colorForLifecycle(signal.lifecycle_state);
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    ctx.globalAlpha = showAll ? 0.95 : 0.35;
    ctx.beginPath(); ctx.arc(x, y, pulse, 0, Math.PI * 2); ctx.stroke();
    ctx.globalAlpha = showAll ? 0.95 : 0.55;
    ctx.beginPath(); ctx.arc(x, y, 3.5, 0, Math.PI * 2); ctx.fill();
    ctx.globalAlpha = 1;
  }});
}}

function drawFocusRings() {{
  const rings = [
    [-74.006, 40.7128, 96, '#f5b84b'],
    [-73.935, 40.730, 70, '#52d3c5'],
    [-73.985, 40.758, 44, '#6fdc8c']
  ];
  rings.forEach(([lon, lat, r, color], i) => {{
    const [x, y] = project(lon, lat);
    ctx.strokeStyle = color;
    ctx.globalAlpha = 0.16 + Math.sin(state.t * 0.025 + i) * 0.05;
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(x, y, r + Math.sin(state.t * 0.02 + i) * 8, 0, Math.PI * 2); ctx.stroke();
    ctx.globalAlpha = 1;
  }});
}}

function draw() {{
  state.t += 1;
  drawGrid();
  drawWater();
  drawFocusRings();
  drawShards();
  drawSignals();
  requestAnimationFrame(draw);
}}

function nearestShard(clientX, clientY) {{
  const rect = canvas.getBoundingClientRect();
  const x = (clientX - rect.left) * canvas.width / rect.width;
  const y = (clientY - rect.top) * canvas.height / rect.height;
  let best = null;
  let bestDist = Infinity;
  for (const shard of data.shards) {{
    const [sx, sy] = project(shard.lon, shard.lat);
    const dist = Math.hypot(x - sx, y - sy);
    if (dist < bestDist) {{ bestDist = dist; best = shard; }}
  }}
  let signalBest = null;
  let signalDist = Infinity;
  for (const signal of data.signals) {{
    const [sx, sy] = project(signal.lon, signal.lat);
    const dist = Math.hypot(x - sx, y - sy);
    if (dist < signalDist) {{ signalDist = dist; signalBest = signal; }}
  }}
  if (signalBest && signalDist < Math.min(bestDist, 32)) return {{type: 'signal', item: signalBest}};
  return best ? {{type: 'shard', item: best}} : null;
}}

canvas.addEventListener('click', event => {{
  const hit = nearestShard(event.clientX, event.clientY);
  if (!hit) return;
  state.selectedType = hit.type;
  state.selectedId = hit.type === 'shard' ? hit.item.shard_id : hit.item.id;
  renderInspector();
}});

function selectedItem() {{
  if (state.selectedType === 'shard') return data.shards.find(s => s.shard_id === state.selectedId) || data.shards[0];
  if (state.selectedType === 'signal') return data.signals.find(s => s.id === state.selectedId) || data.signals[0];
  return null;
}}

function tag(text, kind='context') {{
  return `<span class="tag ${{kind}}">${{esc(text)}}</span>`;
}}

function renderInspector() {{
  const item = selectedItem();
  if (!item) {{
    $('heroTitle').textContent = 'NYC full 3D context';
    $('heroSummary').textContent = 'Full direct I3S export loaded into CityBrain as sharded USD plus identity sidecars.';
    $('selectedName').textContent = 'citywide view';
    $('heroTags').innerHTML = tag('review/context') + tag(`${{data.nyc_3d.shard_count}} shards`, 'observed') + tag('no action', 'limitation');
    return;
  }}
  if (state.selectedType === 'shard') {{
    $('heroTitle').textContent = item.label;
    $('heroSummary').textContent = `${{fmt(item.leaf_nodes)}} leaf nodes, ${{fmt(item.features)}} identity rows, ${{fmt(item.vertices)}} vertices.`;
    $('selectedName').textContent = item.label;
    $('heroTags').innerHTML = tag(item.status, 'observed') + tag(`${{fmt(item.triangles)}} triangles`, 'context') + tag('USD shard', 'simulated');
  }} else {{
    $('heroTitle').textContent = item.title;
    $('heroSummary').textContent = item.summary;
    $('selectedName').textContent = item.lifecycle_state;
    $('heroTags').innerHTML = tag(item.lifecycle_state, lifecycleClass(item.lifecycle_state)) + tag(item.producer, 'context') + tag('visual marker', 'limitation');
  }}
}}

function renderMetrics() {{
  const totals = data.nyc_3d.totals;
  const cards = [
    ['USD shards', data.nyc_3d.shard_count],
    ['Vertices', totals.vertices_exported],
    ['Triangles', totals.triangles_exported],
    ['Identity rows', totals.features_exported],
    ['Event signals', data.counts.signals_rendered],
    ['Review candidates', data.counts.review_candidates],
    ['Evidence items', data.counts.evidence_items_loaded],
    ['Replay items', data.counts.replay_items_loaded]
  ];
  $('assets').innerHTML = cards.map(([label, value]) => `<div class="metric"><span>${{esc(label)}}</span><strong>${{fmt(value)}}</strong></div>`).join('');
  $('assetMetrics').innerHTML = [
    ['Leaf nodes', totals.leaf_nodes_exported],
    ['Failures', totals.failure_count],
    ['No mutation', data.nyc_3d.checks.no_mutation_pass ? 'PASS' : 'CHECK'],
    ['Secrets', data.nyc_3d.checks.secret_audit_pass ? 'PASS' : 'CHECK']
  ].map(([label, value]) => `<div class="mini-metric"><span>${{esc(label)}}</span><strong>${{fmt(value)}}</strong></div>`).join('');
}}

function renderLists() {{
  $('signalCount').textContent = `${{data.signals.length}} rendered`;
  $('signalList').innerHTML = data.signals.slice(0, 18).map(signal => `
    <button class="row" data-signal="${{esc(signal.id)}}">
      <strong>${{esc(signal.title)}}</strong>
      <span>${{esc(signal.lifecycle_state)}} · ${{esc(signal.producer)}}</span>
    </button>`).join('');
  document.querySelectorAll('[data-signal]').forEach(btn => btn.addEventListener('click', () => {{
    state.selectedType = 'signal'; state.selectedId = btn.dataset.signal; renderInspector();
  }}));

  $('identityList').innerHTML = data.nyc_3d.identity_samples.map(sample => `
    <div class="row passive">
      <strong>${{esc(sample.building_id || sample.bin)}}</strong>
      <span>BBL ${{esc(sample.bbl)}} · DOITT ${{esc(sample.doitt_id)}} · ${{esc(sample.height_ft)}} ft</span>
    </div>`).join('');

  $('replayList').innerHTML = data.replay.map(item => `
    <div class="row passive">
      <strong>${{esc(item.title)}}</strong>
      <span>${{esc(item.lifecycle_state)}} · ${{esc(item.claim_boundary)}}</span>
    </div>`).join('');

  $('evidencePanel').innerHTML = `
    <div class="kv"><span>Evidence items</span><strong>${{fmt(data.evidence.item_count)}}</strong><span>Boundary</span><strong>context only</strong><span>Source state</span><strong>${{esc(data.status)}}</strong></div>
    <div class="source-list">${{data.source_artifacts.map(a => `<code>${{esc(a.artifact_type)}} · ${{esc(a.path)}}</code>`).join('')}}</div>`;
  $('guardrailList').innerHTML = data.guardrails.map(g => `<div class="guardrail">${{esc(g)}}</div>`).join('');
}}

function renderTop() {{
  $('subtitle').textContent = `${{fmt(data.counts.nyc_identity_rows)}} source identity rows · ${{fmt(data.counts.feed_items_loaded)}} D4 feed items · no action taken`;
  $('assetStatus').textContent = data.city.asset_status;
  $('composerCommand').textContent = data.nyc_3d.open_command;
}}

function render() {{
  renderTop();
  renderMetrics();
  renderLists();
  renderInspector();
}}

document.querySelectorAll('[data-layer]').forEach(btn => btn.addEventListener('click', () => {{
  document.querySelectorAll('[data-layer]').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  state.layer = btn.dataset.layer;
}}));

render();
requestAnimationFrame(draw);
"""


def app_css() -> str:
    return """:root {
  color-scheme: dark;
  --bg: #090c10;
  --panel: #111820;
  --panel-2: #17212b;
  --line: #263441;
  --text: #eef4f8;
  --muted: #91a2b3;
  --cyan: #52d3c5;
  --blue: #4fc3ff;
  --amber: #f5b84b;
  --green: #6fdc8c;
  --rose: #ff6f91;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body { margin: 0; min-width: 320px; background: var(--bg); color: var(--text); font: 14px/1.45 Inter, Segoe UI, Arial, sans-serif; letter-spacing: 0; }
button { font: inherit; }
.app { min-height: 100vh; display: grid; grid-template-columns: 190px minmax(0, 1fr); }
.rail { position: sticky; top: 0; height: 100vh; padding: 18px 12px; border-right: 1px solid var(--line); background: #07090c; display: flex; flex-direction: column; gap: 18px; }
.brand { display: flex; align-items: center; gap: 10px; }
.brand-mark { width: 28px; height: 28px; border-radius: 50%; border: 2px solid var(--cyan); box-shadow: 0 0 18px rgba(82,211,197,.4); }
.brand strong { display: block; font-size: 15px; }
.brand small { display: block; color: var(--muted); margin-top: 1px; }
.nav-link { display: block; padding: 9px 10px; color: var(--muted); text-decoration: none; border-radius: 6px; margin: 3px 0; }
.nav-link:hover, .nav-link.active { color: var(--text); background: #151d26; }
.rail-footer { margin-top: auto; color: var(--muted); display: flex; align-items: center; gap: 8px; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--muted); display: inline-block; }
.dot.ok { background: var(--green); box-shadow: 0 0 12px rgba(111,220,140,.6); }
main { min-width: 0; padding: 16px; }
.topbar { display: flex; align-items: start; justify-content: space-between; gap: 14px; padding-bottom: 14px; border-bottom: 1px solid var(--line); }
h1 { margin: 0; font-size: 26px; line-height: 1.1; }
h2 { margin: 0 0 10px; font-size: 15px; }
p { margin: 4px 0; color: var(--muted); }
.toolbar { display: flex; gap: 7px; flex-wrap: wrap; justify-content: flex-end; }
.tool { border: 1px solid var(--line); background: #111923; color: var(--muted); border-radius: 6px; padding: 7px 10px; cursor: pointer; min-width: 82px; }
.tool:hover, .tool.active { border-color: var(--cyan); color: var(--text); box-shadow: 0 0 0 1px rgba(82,211,197,.22) inset; }
.city-stage { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 12px; margin-top: 14px; align-items: stretch; }
.city-canvas-wrap { position: relative; border: 1px solid var(--line); border-radius: 8px; background: #080d12; overflow: hidden; min-height: 520px; }
canvas { display: block; width: 100%; height: 100%; min-height: 560px; }
.hud { position: absolute; border: 1px solid rgba(255,255,255,.12); background: rgba(8,12,16,.72); backdrop-filter: blur(8px); border-radius: 8px; padding: 9px 10px; min-width: 190px; }
.hud span { color: var(--muted); display: block; font-size: 12px; }
.hud strong { display: block; margin-top: 2px; overflow-wrap: anywhere; }
.top-left { left: 12px; top: 12px; }
.bottom-left { left: 12px; bottom: 12px; }
.inspector { display: grid; gap: 12px; align-content: start; }
.panel { border: 1px solid var(--line); background: linear-gradient(180deg, rgba(23,33,43,.96), rgba(13,19,25,.96)); border-radius: 8px; padding: 12px; min-width: 0; }
.hero-card { min-height: 150px; }
.tags { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; }
.tag { border: 1px solid var(--line); color: var(--muted); padding: 3px 6px; border-radius: 5px; font-size: 12px; }
.tag.observed { border-color: var(--green); color: var(--green); }
.tag.candidate { border-color: var(--amber); color: var(--amber); }
.tag.simulated, .tag.synthetic { border-color: var(--blue); color: var(--blue); }
.tag.limitation { border-color: var(--rose); color: var(--rose); }
.metrics-band { display: grid; grid-template-columns: repeat(8, minmax(110px, 1fr)); gap: 10px; margin: 12px 0; }
.metric, .mini-metric { border: 1px solid var(--line); background: #101821; border-radius: 8px; padding: 10px; min-height: 72px; }
.metric span, .mini-metric span { color: var(--muted); display: block; font-size: 12px; }
.metric strong { display: block; font-size: 20px; margin-top: 5px; }
.mini-metric strong { display: block; margin-top: 3px; }
.metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.command-box { border: 1px solid var(--line); background: #070a0d; border-radius: 6px; padding: 9px; max-height: 116px; overflow: auto; }
code { color: var(--cyan); overflow-wrap: anywhere; display: block; }
.lower-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-top: 12px; align-items: start; }
.lower-grid.two { grid-template-columns: 1fr 1fr; }
.panel-head { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.panel-head span { color: var(--muted); font-size: 12px; }
.list-view { display: grid; gap: 7px; max-height: 360px; overflow: auto; padding-right: 3px; }
.row { width: 100%; border: 1px solid var(--line); background: var(--panel-2); color: var(--text); border-radius: 7px; padding: 9px; display: grid; gap: 2px; text-align: left; cursor: pointer; }
.row:hover { border-color: var(--cyan); }
.row.passive { cursor: default; }
.row.passive:hover { border-color: var(--line); }
.row span { color: var(--muted); overflow-wrap: anywhere; }
.kv { display: grid; grid-template-columns: 150px minmax(0, 1fr); gap: 8px; }
.kv span { color: var(--muted); }
.source-list { display: grid; gap: 7px; margin-top: 12px; }
.guardrails { display: grid; gap: 8px; }
.guardrail { border-left: 3px solid var(--amber); background: rgba(245,184,75,.08); border-radius: 5px; padding: 8px 9px; color: var(--muted); }
@media (max-width: 1180px) {
  .app { grid-template-columns: 1fr; }
  .rail { position: static; height: auto; }
  .city-stage, .lower-grid, .lower-grid.two { grid-template-columns: 1fr; }
  .metrics-band { grid-template-columns: repeat(2, minmax(120px, 1fr)); }
  .topbar { flex-direction: column; }
  .toolbar { justify-content: flex-start; }
}
"""


def no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = [name for name in before if before[name] != after[name]]
    report = {"status": "PASS" if not changed else "FAIL", "changed_roots": changed, "checked_root_count": len(before)}
    write_text(OUT / "NO_MUTATION_AUDIT.md", "# No-Mutation Audit\n\n" + f"Status: `{report['status']}`\n\n```json\n" + json.dumps(report, indent=2) + "\n```\n")
    return report


def secret_audit() -> dict[str, Any]:
    findings = []
    patterns = [
        re.compile(r"(?i)(api[_-]?key|app[_-]?key|secret|token)\s*[:=]\s*[a-z0-9]{16,}"),
    ]
    for path in OUT.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": path.relative_to(OUT).as_posix(), "pattern": pattern.pattern})
    report = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}
    write_text(OUT / "SECRET_REDACTION_AUDIT.md", "# Secret Redaction Audit\n\n" + f"Status: `{report['status']}`\n\n" + ("No secrets found.\n" if not findings else json.dumps(report, indent=2) + "\n"))
    return report


def smoke_report(data: dict[str, Any]) -> dict[str, Any]:
    files = [
        OUT / "app_shell" / "index.html",
        OUT / "app_shell" / "app.js",
        OUT / "app_shell" / "styles.css",
        OUT / "app_shell" / "nyc_live_city_data.json",
    ]
    checks = {
        "app_files_exist": all(path.exists() for path in files),
        "nyc_export_pass": data["city"]["asset_status"] == "PASS_D4_3D_NYC_2025_FULL_I3S_EXPORT_R1",
        "shards_loaded": data["nyc_3d"]["shard_count"] == 53,
        "signals_loaded": data["counts"]["signals_rendered"] > 0,
        "guardrails_present": len(data["guardrails"]) >= 4,
        "no_action_taken": data["no_action_taken"] is True,
    }
    report = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}
    write_json(OUT / "smoke" / "NYC_LIVE_CITY_APP_SMOKE_REPORT.json", report)
    return report


def run(args: argparse.Namespace) -> dict[str, Any]:
    os.chdir(args.project_root)
    before = snapshot_roots()
    if OUT.exists():
        shutil.rmtree(OUT)
    data = build_view_model()
    app_dir = OUT / "app_shell"
    write_text(app_dir / "index.html", app_html())
    write_text(app_dir / "styles.css", app_css())
    write_text(app_dir / "app.js", app_js(data))
    write_json(app_dir / "nyc_live_city_data.json", data)
    write_json(OUT / "NYC_LIVE_CITY_VIEW_MODEL.json", data)

    smoke = smoke_report(data)
    after = snapshot_roots()
    no_mut = no_mutation_audit(before, after)
    secret = secret_audit()
    status = PASS if smoke["status"] == "PASS" and no_mut["status"] == "PASS" and secret["status"] == "PASS" else FAIL
    if status == PASS and data["status"] != PASS:
        status = PASS_LIMITED
    data["status"] = status
    write_json(app_dir / "nyc_live_city_data.json", data)
    write_json(OUT / "NYC_LIVE_CITY_VIEW_MODEL.json", data)
    write_text(
        OUT / "README.md",
        f"# {TASK}\n\nStatus: `{status}`\n\nOpen `app_shell/index.html` to run the NYC live city control-room app.\n",
    )
    write_text(
        OUT / "MAIN_TRACK1_D4X_NYC_LIVE_CITY_APP_R1.md",
        f"# NYC Live City App\n\n"
        f"Status: `{status}`\n\n"
        f"- NYC USD shards: `{data['nyc_3d']['shard_count']}`\n"
        f"- Vertices: `{data['nyc_3d']['totals'].get('vertices_exported')}`\n"
        f"- Identity rows: `{data['nyc_3d']['totals'].get('features_exported')}`\n"
        f"- Signals rendered: `{data['counts']['signals_rendered']}`\n"
        f"- Boundary: review/context UI only; no command/control/dispatch/enforcement/routing/health/certified affected-building claim.\n",
    )
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": utc_now(),
        "app_path": str((app_dir / "index.html").resolve()),
        "view_model": str((OUT / "NYC_LIVE_CITY_VIEW_MODEL.json").resolve()),
        "nyc_master_usda": data["nyc_3d"]["master_usda"],
        "counts": data["counts"],
        "checks": {
            "smoke_pass": smoke["status"] == "PASS",
            "no_mutation_pass": no_mut["status"] == "PASS",
            "secret_audit_pass": secret["status"] == "PASS",
            "nyc_export_pass": data["city"]["asset_status"] == "PASS_D4_3D_NYC_2025_FULL_I3S_EXPORT_R1",
            "no_action_taken": data["no_action_taken"],
        },
        "limitations": data["nyc_3d"]["limitations"] + data["guardrails"],
    }
    write_json(OUT / "MAIN_TRACK1_D4X_NYC_LIVE_CITY_APP_R1_DECISION.json", decision)
    shutil.copy2(Path(__file__), OUT / "run_main_track1_d4x_nyc_live_city_app_r1.py")
    hash_outputs()
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Run {TASK}.")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    decision = run(args)
    print(f"{TASK}: {decision['status']}")
    print(f"Output: {OUT}")
    return 0 if decision["status"] in {PASS, PASS_LIMITED} else 1


if __name__ == "__main__":
    raise SystemExit(main())

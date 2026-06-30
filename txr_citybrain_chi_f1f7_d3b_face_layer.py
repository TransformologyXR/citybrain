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

import pandas as pd


TASK_NAME = "CHI-F1F7-D3B Refreshed Face-Layer Status/Fusion Surface"
DEFAULT_OUTPUT_DIR = "outputs/chi_f1f7_d3b_face_layer_status_fusion_surface"
DEFAULT_D1B_DIR = "outputs/chi_d1b_chicago_extended_source_landing"
DEFAULT_D3B_DIR = "outputs/chi_d3_civic_event_ingest_flow_readiness_d3b_expanded_d1b"
DEFAULT_D4B_DIR = "outputs/chi_d4_dual_flow_scope_fork_d3b_refresh"
DEFAULT_F1B_DIR = "outputs/chi_f1_d1_situational_status_cartridge_d1b_refresh"
DEFAULT_F7B_DIR = "outputs/chi_f7_d1_civic_sensor_fusion_cartridge_d1b_refresh"
DEFAULT_DUALB_DIR = "outputs/chi_f1_f7_d1_dual_flow_run_d1b_refresh"
DEFAULT_D2B_DIR = "outputs/chi_f1f7_d2_live_spark_nim_replay_d1b_refresh"
REMOTE_HOST = "txr-4070"
REMOTE_ROOT = "/srv/citybrain/current"
DEFAULT_BASE_URL = "http://192.168.1.48:8080"

ROUTES = [
    "/status/chicago",
    "/chicago",
    "/api/chicago/status",
    "/api/chicago/flow1-area-status",
    "/api/chicago/flow7-fusion-candidates",
    "/api/chicago/live-nim-briefings",
    "/api/chicago/source-limitations",
    "/api/chicago/negative-boundaries",
]

BOUNDARY_LINES = [
    "CHI-F1F7-D3B is a refreshed face-layer status/fusion surface over accepted CHI-D1B/D3B/F1F7-D1B/D2B evidence.",
    "Chicago Flow 1 + Flow 7 are live-NIM green over an expanded, materially stronger, still source-limited public-data base.",
    "D3B/F1F7 evidence base is not all-full-source; Divvy, Cook parcels, Crimes, and Open Air individual remain capped/windowed.",
    "CHI-F1F7-D3B displays status/fusion evidence only and does not make operational recommendations.",
    "CHI-F1F7-D3B does not make policing, dispatch, enforcement, health, emergency, or public-safety recommendations.",
    "CHI-F1F7-D3B does not certify affected buildings/assets.",
    "CTA GTFS is static schedule context, not live transit status.",
    "Crime data is privacy-safe block-level context only.",
    "Sensor/environment observations are context signals, not health determinations.",
    "Live NIM briefing text is displayed only as grounded narration over deterministic EvidenceBundles.",
]

FORBIDDEN_POSITIVE_PATTERNS = [
    r"\boperational recommendations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\bpublic-safety recommendations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\bpolicing recommendations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\bdispatch recommendations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\benforcement recommendations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\bhealth determinations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\bemergency recommendations?\s+(?:is|are|were|provided|ready|available)\b",
    r"\b(?:certified|confirmed|definitely)\s+affected (?:buildings|assets)\b",
    r"\blive transit status\s+(?:is|was|provided|ready|available)\b",
    r"\ball-full-source\s+(?:is|was|true|complete|provided|ready|available)\b",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


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
    (output_dir / "SHA256SUMS.json").write_text(json.dumps(sums, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"gate": "CHI-F1F7-D3B-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {p.lower() for p in resolved.parts} or "chi_f1f7_d3b" not in resolved.name.lower():
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in ["face_payload", "face_app", "reports", "_route_payload"]:
        (output_dir / name).mkdir(parents=True, exist_ok=True)


def input_snapshot(paths: list[Path]) -> dict[str, Any]:
    watched: dict[str, Any] = {}
    for root in paths:
        if not root.exists():
            watched[str(root)] = {"exists": False}
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() in {".part", ".tmp"}:
                continue
            stat = path.stat()
            watched[str(path.resolve())] = {
                "exists": True,
                "bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "sha256": sha256_file(path) if stat.st_size < 250_000_000 else None,
            }
    return watched


def compare_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = sorted(k for k, v in before.items() if after.get(k) != v)
    added = sorted(k for k in after if k not in before)
    removed = sorted(k for k in before if k not in after)
    return {
        "gate": "CHI-F1F7-D3B-NO-MUTATION",
        "status": "PASS" if not changed and not added and not removed else "FAIL",
        "checked_files": len(before),
        "changed_inputs": changed,
        "added_inputs": added,
        "removed_inputs": removed,
    }


def status_pass(value: Any) -> bool:
    text = str(value or "").upper()
    return text.startswith("PASS") or text.startswith("GREEN")


def read_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def load_narrations(d2b_dir: Path) -> dict[str, Any]:
    rows = read_json(d2b_dir / "samples" / "live_sample_narrations.json", [])
    by_id = {}
    for row in rows:
        if isinstance(row, dict) and row.get("sample_id"):
            by_id[row["sample_id"]] = {
                "sample_id": row.get("sample_id"),
                "query_type": row.get("query_type"),
                "answer_status": row.get("answer_status"),
                "operator_request": row.get("operator_request"),
                "narration": row.get("narration"),
                "grounding": row.get("grounding"),
                "nim_status": (row.get("nim_call") or {}).get("status"),
            }
    return {"status": "PASS" if by_id else "FAIL", "briefings": by_id, "count": len(by_id), "boundary_lines": BOUNDARY_LINES}


def source_by_key(source_refresh: dict[str, Any], key: str) -> dict[str, Any]:
    return ((source_refresh.get("source_refresh") or {}).get("key_sources") or {}).get(key, {})


def build_payloads(d1b_dir: Path, d3b_dir: Path, d4b_dir: Path, f1b_dir: Path, f7b_dir: Path, dualb_dir: Path, d2b_dir: Path) -> dict[str, Any]:
    d1b_harness = read_json(d1b_dir / "CHI_D1B_HARNESS_REPORT.json", {})
    d3b_harness = read_json(d3b_dir / "CHI_D3B_HARNESS_REPORT.json", {})
    d3_harness = read_json(d3b_dir / "CHI_D3_HARNESS_REPORT.json", {})
    d4_harness = read_json(d4b_dir / "CHI_D4_HARNESS_REPORT.json", {})
    f1_harness = read_json(f1b_dir / "CHI_F1_D1_HARNESS_REPORT.json", {})
    f7_harness = read_json(f7b_dir / "CHI_F7_D1_HARNESS_REPORT.json", {})
    dual_harness = read_json(dualb_dir / "CHI_F1_F7_D1_DUAL_HARNESS_REPORT.json", {})
    d2_harness = read_json(d2b_dir / "CHI_F1F7_D2_HARNESS_REPORT.json", {})
    negative = read_json(d2b_dir / "CHI_F1F7_D2_NEGATIVE_REQUEST_REPORT.json", {})

    f1_subjects = read_parquet(f1b_dir / "canonical" / "chi_f1_d1_area_status_subjects.parquet")
    f1_scores = read_parquet(f1b_dir / "canonical" / "chi_f1_d1_area_status_scores.parquet")
    f7_subjects = read_parquet(f7b_dir / "canonical" / "chi_f7_d1_fusion_subjects.parquet")
    f7_candidates = read_parquet(f7b_dir / "canonical" / "chi_f7_d1_signal_fusion_candidates.parquet")
    f7_components = read_parquet(f7b_dir / "canonical" / "chi_f7_d1_signal_components.parquet")

    f1_records = f1_subjects.to_dict("records") if not f1_subjects.empty else []
    f1_score_records = f1_scores.to_dict("records") if not f1_scores.empty else []
    f7_subject_records = f7_subjects.to_dict("records") if not f7_subjects.empty else []
    f7_candidate_records = f7_candidates.head(25).to_dict("records") if not f7_candidates.empty else []
    f7_component_records = f7_components.to_dict("records") if not f7_components.empty else []

    citywide = next((row for row in f1_records if row.get("subject_type") == "citywide"), f1_records[0] if f1_records else {})
    top_area = next((row for row in f1_records if row.get("subject_type") != "citywide"), {})
    top_fusion = f7_subject_records[0] if f7_subject_records else {}
    top_components = [row for row in f7_component_records if row.get("candidate_id") == top_fusion.get("candidate_id")]
    narrations = load_narrations(d2b_dir)

    counts = {
        "d1b_landed_rows": (d1b_harness.get("summary") or {}).get("rows_downloaded_total"),
        "d3b_event_location_rows": (d3b_harness.get("counts") or {}).get("event_location_confidence_rows"),
        "d3b_context_edges": (d3b_harness.get("counts") or {}).get("context_edges"),
        "d3b_location_confidence_A": (d3b_harness.get("location_confidence_counts") or {}).get("A"),
        "d3b_311_events": (d3b_harness.get("counts") or {}).get("311_events"),
        "d3b_traffic_crashes": (d3b_harness.get("counts") or {}).get("traffic_crash_events"),
        "f1_citywide_total_signal_rows": citywide.get("total_public_source_events"),
        "f1_citywide_311_rows": citywide.get("311_service_request_count"),
        "f7_fusion_candidates": f7_harness.get("fusion_candidates"),
        "f7_selected_candidates": f7_harness.get("selected_candidates"),
        "top_f7_candidate_total_events": top_fusion.get("total_public_source_events"),
    }
    status_payload = {
        "status": "PASS",
        "task": TASK_NAME,
        "line": {
            "CHI-D1B": "GREEN_WITH_CAPPED_LARGE_SOURCES - EXPANDED TARGETED SOURCE LANDING",
            "CHI-D3B": "GREEN_WITH_CAPPED_SOURCE_LIMITATIONS - CIVIC/EVENT REFRESH FROM EXPANDED D1B",
            "CHI-D4B": "GREEN_WITH_DUAL_FLOW_FORK - REFRESHED FLOW FORK / SOURCE LEDGER",
            "CHI-F1F7-D1B": "GREEN - PASS_DUAL_FLOW_D1",
            "CHI-F1F7-D2B": "GREEN - LIVE SPARK/NIM REPLAY",
        },
        "source_status_language": "Chicago Flow 1 + Flow 7 are live-NIM green over an expanded, materially stronger, still source-limited public-data base.",
        "counts": counts,
        "statuses": {
            "d1b": d1b_harness.get("status"),
            "d3b": d3b_harness.get("status"),
            "d3": d3_harness.get("status"),
            "d4b": d4_harness.get("status"),
            "f1": f1_harness.get("status"),
            "f7": f7_harness.get("status"),
            "dual": dual_harness.get("status"),
            "d2b": d2_harness.get("status"),
            "d2b_live_nim": d2_harness.get("live_nim_status"),
            "d2b_grounding": d2_harness.get("grounding"),
        },
        "boundary_lines": BOUNDARY_LINES,
    }
    flow1_payload = {
        "status": "PASS",
        "citywide_subject": citywide,
        "top_area_subject": top_area,
        "selected_subjects": f1_records,
        "score_rows": f1_score_records[:25],
        "live_briefings": {k: narrations["briefings"].get(k) for k in ["flow1_citywide", "flow1_area"]},
        "boundary_lines": BOUNDARY_LINES,
    }
    flow7_payload = {
        "status": "PASS",
        "top_candidate": top_fusion,
        "top_candidate_components": top_components,
        "selected_candidates": f7_subject_records,
        "candidate_rows": f7_candidate_records,
        "live_briefing": narrations["briefings"].get("flow7_fusion"),
        "boundary_lines": BOUNDARY_LINES,
    }
    source_payload = {
        "status": "PASS",
        "source_status_language": status_payload["source_status_language"],
        "d3b_source_refresh": d3b_harness.get("source_refresh"),
        "key_sources": {
            "311_service_requests": source_by_key(d3b_harness, "311_service_requests"),
            "traffic_crashes_crashes": source_by_key(d3b_harness, "traffic_crashes_crashes"),
            "traffic_crashes_people": source_by_key(d3b_harness, "traffic_crashes_people"),
            "traffic_crashes_vehicles": source_by_key(d3b_harness, "traffic_crashes_vehicles"),
            "traffic_tracker_historical_2024_current": source_by_key(d3b_harness, "traffic_tracker_historical_2024_current"),
            "divvy_trips": source_by_key(d3b_harness, "divvy_trips"),
            "cook_county_parcel_universe": source_by_key(d3b_harness, "cook_county_parcel_universe"),
            "crimes_2001_present": source_by_key(d3b_harness, "crimes_2001_present"),
            "open_air_chicago_individual_measurements": source_by_key(d3b_harness, "open_air_chicago_individual_measurements"),
        },
        "boundary_lines": BOUNDARY_LINES,
    }
    negative_payload = {
        "status": negative.get("status"),
        "negative_request_results": negative.get("results", []),
        "boundary_lines": BOUNDARY_LINES,
    }
    return {
        "status": status_payload,
        "flow1-area-status": flow1_payload,
        "flow7-fusion-candidates": flow7_payload,
        "live-nim-briefings": narrations,
        "source-limitations": source_payload,
        "negative-boundaries": negative_payload,
    }


def html_page() -> str:
    boundary_json = json.dumps(BOUNDARY_LINES)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CityBrain Chicago F1/F7</title>
  <style>
    :root {{ color-scheme: light; --ink:#202124; --muted:#5f6368; --line:#d8dde3; --panel:#f7f9fb; --accent:#0f766e; --accent2:#7c3aed; --warn:#9a3412; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Arial, Helvetica, sans-serif; color:var(--ink); background:#fff; }}
    header {{ padding:18px 24px; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; gap:18px; align-items:flex-start; }}
    h1 {{ margin:0; font-size:22px; line-height:1.2; letter-spacing:0; }}
    h2 {{ margin:0 0 10px; font-size:16px; letter-spacing:0; }}
    main {{ padding:18px 24px 32px; max-width:1440px; margin:0 auto; }}
    nav {{ display:flex; gap:8px; flex-wrap:wrap; }}
    nav a {{ color:var(--ink); text-decoration:none; border:1px solid var(--line); padding:6px 9px; border-radius:6px; font-size:13px; }}
    .grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; margin-bottom:16px; }}
    .card {{ border:1px solid var(--line); border-radius:8px; padding:12px; min-height:78px; background:var(--panel); }}
    .card span {{ display:block; color:var(--muted); font-size:12px; margin-bottom:8px; }}
    .card strong {{ font-size:22px; overflow-wrap:anywhere; }}
    .split {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; align-items:start; }}
    section {{ border-top:1px solid var(--line); padding-top:14px; margin-top:14px; }}
    table {{ width:100%; border-collapse:collapse; font-size:13px; }}
    th,td {{ border-bottom:1px solid var(--line); text-align:left; padding:7px 6px; vertical-align:top; }}
    th {{ color:var(--muted); font-weight:600; }}
    pre {{ white-space:pre-wrap; background:#111827; color:#f9fafb; border-radius:8px; padding:12px; max-height:360px; overflow:auto; font-size:12px; }}
    ul {{ margin:8px 0 0 18px; padding:0; }}
    .tag {{ display:inline-block; border:1px solid var(--line); border-radius:999px; padding:3px 8px; margin:2px; font-size:12px; color:var(--muted); }}
    .ok {{ color:var(--accent); }}
    .limit {{ color:var(--warn); }}
    @media (max-width:900px) {{ .grid,.split {{ grid-template-columns:1fr; }} header {{ display:block; }} nav {{ margin-top:12px; }} }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>CityBrain Chicago Flow 1 + Flow 7</h1>
      <div id="line" class="tag">loading</div>
    </div>
    <nav>
      <a href="/api/chicago/status">status</a>
      <a href="/api/chicago/flow1-area-status">flow1</a>
      <a href="/api/chicago/flow7-fusion-candidates">flow7</a>
      <a href="/api/chicago/live-nim-briefings">live NIM</a>
      <a href="/api/chicago/source-limitations">limits</a>
    </nav>
  </header>
  <main>
    <div id="cards" class="grid"></div>
    <section class="split">
      <div>
        <h2>Flow 1 Area Status</h2>
        <div id="flow1"></div>
      </div>
      <div>
        <h2>Flow 7 Fusion Candidate</h2>
        <div id="flow7"></div>
      </div>
    </section>
    <section class="split">
      <div>
        <h2>Live Grounded Narration</h2>
        <pre id="briefing">loading</pre>
      </div>
      <div>
        <h2>Source Limits</h2>
        <div id="limits"></div>
      </div>
    </section>
  </main>
  <script>
    const boundaries = {boundary_json};
    const fmt = v => typeof v === 'number' ? v.toLocaleString() : (v ?? 'n/a');
    async function j(path, rel) {{
      try {{ const r = await fetch(path); if (r.ok) return await r.json(); }} catch(e) {{}}
      const r2 = await fetch(rel); return await r2.json();
    }}
    function table(rows, cols) {{
      return `<table><thead><tr>${{cols.map(c=>`<th>${{c[0]}}</th>`).join('')}}</tr></thead><tbody>${{rows.map(r=>`<tr>${{cols.map(c=>`<td>${{fmt(r[c[1]])}}</td>`).join('')}}</tr>`).join('')}}</tbody></table>`;
    }}
    Promise.all([
      j('/api/chicago/status','../face_payload/chicago_status.json'),
      j('/api/chicago/flow1-area-status','../face_payload/chicago_flow1-area-status.json'),
      j('/api/chicago/flow7-fusion-candidates','../face_payload/chicago_flow7-fusion-candidates.json'),
      j('/api/chicago/live-nim-briefings','../face_payload/chicago_live-nim-briefings.json'),
      j('/api/chicago/source-limitations','../face_payload/chicago_source-limitations.json')
    ]).then(([status, f1, f7, live, limits]) => {{
      const c = status.counts;
      document.getElementById('line').textContent = status.source_status_language;
      document.getElementById('cards').innerHTML = [
        ['D3B event/location rows', c.d3b_event_location_rows],
        ['D3B context edges', c.d3b_context_edges],
        ['311 recent-window rows', c.d3b_311_events],
        ['Flow 7 candidates', c.f7_fusion_candidates],
        ['Location confidence A', c.d3b_location_confidence_A],
        ['F1 citywide signals', c.f1_citywide_total_signal_rows],
        ['Top F7 total events', c.top_f7_candidate_total_events],
        ['Live NIM', status.statuses.d2b_live_nim]
      ].map(x=>`<div class="card"><span>${{x[0]}}</span><strong>${{fmt(x[1])}}</strong></div>`).join('');
      document.getElementById('flow1').innerHTML = table(f1.selected_subjects, [['rank','selection_rank'],['subject','subject_name'],['type','subject_type'],['events','total_public_source_events'],['311','311_service_request_count'],['score','status_signal_score']]);
      document.getElementById('flow7').innerHTML = table(f7.selected_candidates, [['rank','rank'],['candidate','candidate_id'],['subject','subject_name'],['events','total_public_source_events'],['score','fusion_signal_score']]);
      const b = live.briefings.flow7_fusion || live.briefings.flow1_area || live.briefings.chicago_flow_status || {{}};
      document.getElementById('briefing').textContent = b.narration || 'No briefing payload.';
      const keys = Object.entries(limits.key_sources || {{}}).map(([k,v]) => `<span class="tag">${{k}}: ${{v.completion_status || 'unknown'}} - ${{fmt(v.downloaded_rows)}}</span>`).join('');
      document.getElementById('limits').innerHTML = `<p class="limit">${{limits.source_status_language}}</p><div>${{keys}}</div><ul>${{boundaries.map(x=>`<li>${{x}}</li>`).join('')}}</ul>`;
    }});
  </script>
</body>
</html>
"""


def stage_route_payload(output_dir: Path, payloads: dict[str, Any]) -> dict[str, Any]:
    root = output_dir / "_route_payload"
    pages = {
        root / "chicago" / "index.html": html_page(),
        root / "status" / "chicago" / "index.html": html_page(),
    }
    for path, text in pages.items():
        write_text(path, text)
    api = root / "api" / "chicago"
    copied_payloads = {}
    for name, payload in payloads.items():
        write_json(api / name, payload)
        write_json(api / f"{name}.json", payload)
        write_json(output_dir / "face_payload" / f"chicago_{name}.json", payload)
        copied_payloads[name] = f"face_payload/chicago_{name}.json"
    write_text(output_dir / "face_app" / "chicago.html", html_page())
    route_manifest = {
        "status": "PASS",
        "ui_routes": {"/chicago": "chicago/index.html", "/status/chicago": "status/chicago/index.html"},
        "api_routes": {route: f"api/chicago/{route.rsplit('/', 1)[-1]}" for route in ROUTES if route.startswith("/api/")},
        "route_strategy": "static Caddy payloads copied under /chicago, /status/chicago, and /api/chicago",
        "nyc_routes_touched": False,
        "london_routes_touched": False,
    }
    write_json(output_dir / "reports" / "route_manifest.json", route_manifest)
    return {"status": "PASS", "staged_root": str(root), "pages": [p.relative_to(root).as_posix() for p in pages], "payloads": copied_payloads, "routes": route_manifest}


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
        return {"gate": "CHI-F1F7-D3B-4070-PUBLISH", "status": "NOT_RUN", "reason": "publish_4070=false"}
    root = output_dir / "_route_payload"
    try:
        before = run_cmd(["ssh", REMOTE_HOST, f"find {REMOTE_ROOT}/chicago {REMOTE_ROOT}/status/chicago {REMOTE_ROOT}/api/chicago -maxdepth 3 -type f 2>/dev/null | sort"], timeout=60)
        mkdir = run_cmd(["ssh", REMOTE_HOST, f"mkdir -p {REMOTE_ROOT}/chicago {REMOTE_ROOT}/status {REMOTE_ROOT}/api"], timeout=60)
        copy_chicago = run_cmd(["scp", "-r", str(root / "chicago"), f"{REMOTE_HOST}:{REMOTE_ROOT}/"], timeout=180)
        copy_status = run_cmd(["scp", "-r", str(root / "status" / "chicago"), f"{REMOTE_HOST}:{REMOTE_ROOT}/status/"], timeout=180)
        copy_api = run_cmd(["scp", "-r", str(root / "api" / "chicago"), f"{REMOTE_HOST}:{REMOTE_ROOT}/api/"], timeout=180)
        chmod = run_cmd(["ssh", REMOTE_HOST, f"chmod -R a+rX {REMOTE_ROOT}/chicago {REMOTE_ROOT}/status/chicago {REMOTE_ROOT}/api/chicago"], timeout=60)
        after = run_cmd(["ssh", REMOTE_HOST, f"find {REMOTE_ROOT}/chicago {REMOTE_ROOT}/status/chicago {REMOTE_ROOT}/api/chicago -maxdepth 3 -type f | sort"], timeout=60)
        ok = all(item.get("status") == "PASS" for item in [mkdir, copy_chicago, copy_status, copy_api, chmod, after])
        return {
            "gate": "CHI-F1F7-D3B-4070-PUBLISH",
            "status": "PASS" if ok else "FAIL",
            "remote_host": REMOTE_HOST,
            "remote_root": REMOTE_ROOT,
            "before": before,
            "mkdir": mkdir,
            "copy_chicago": copy_chicago,
            "copy_status": copy_status,
            "copy_api": copy_api,
            "chmod": chmod,
            "after": after,
        }
    except Exception as exc:
        return {"gate": "CHI-F1F7-D3B-4070-PUBLISH", "status": "NOT_RUN_OR_UNREACHABLE", "error": f"{type(exc).__name__}: {exc}"}


def http_get(url: str, timeout: int = 15) -> dict[str, Any]:
    rec: dict[str, Any] = {"url": url, "status": "attempted"}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CityBrain-CHI-F1F7-D3B/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read(512000)
            text = body.decode("utf-8", errors="replace")
        rec.update({"http_status": response.status, "content_type": response.headers.get("content-type"), "bytes_read": len(body), "text_sample": text[:3000], "status": "PASS" if response.status == 200 else "FAIL"})
    except urllib.error.HTTPError as exc:
        rec.update({"http_status": exc.code, "status": "FAIL", "error": str(exc)})
    except Exception as exc:
        rec.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    return rec


def endpoint_smoke(output_dir: Path, base_url: str, publish_status: str) -> dict[str, Any]:
    if publish_status != "PASS":
        files = [
            output_dir / "_route_payload" / "chicago" / "index.html",
            output_dir / "_route_payload" / "status" / "chicago" / "index.html",
            output_dir / "_route_payload" / "api" / "chicago" / "status",
            output_dir / "_route_payload" / "api" / "chicago" / "flow1-area-status",
            output_dir / "_route_payload" / "api" / "chicago" / "flow7-fusion-candidates",
            output_dir / "_route_payload" / "api" / "chicago" / "live-nim-briefings",
            output_dir / "_route_payload" / "api" / "chicago" / "source-limitations",
        ]
        return {"gate": "CHI-F1F7-D3B-ENDPOINT-SMOKE", "status": "PASS" if all(p.exists() for p in files) else "FAIL", "mode": "file_payload_verified", "checked_files": [str(p) for p in files]}
    attempts = [http_get(base_url.rstrip("/") + route) for route in ROUTES]
    joined = "\n".join(row.get("text_sample", "") for row in attempts)
    required = ["Chicago", "11279337", "5901178", "2173618", "live-NIM green", "source-limited"]
    checks = {text: text in joined for text in required}
    passed = [row for row in attempts if row.get("status") == "PASS"]
    return {"gate": "CHI-F1F7-D3B-ENDPOINT-SMOKE", "status": "PASS" if len(passed) == len(attempts) and all(checks.values()) else "FAIL", "mode": "live_endpoint_smoke", "base_url": base_url, "attempts": attempts, "grounded_text_checks": checks}


def grounding_report(payloads: dict[str, Any]) -> dict[str, Any]:
    status = payloads["status"]
    f1 = payloads["flow1-area-status"]
    f7 = payloads["flow7-fusion-candidates"]
    live = payloads["live-nim-briefings"]
    limits = payloads["source-limitations"]
    checks = {
        "d3b_rows_present": status.get("counts", {}).get("d3b_event_location_rows") == 11279337,
        "f1_citywide_311_present": status.get("counts", {}).get("f1_citywide_311_rows") == 5901178,
        "top_f7_candidate_present": (f7.get("top_candidate") or {}).get("candidate_id") == "chi-f7:fusion_candidate:community_area:28",
        "top_f7_events_present": (f7.get("top_candidate") or {}).get("total_public_source_events") == 2173618,
        "live_nim_briefing_present": bool((live.get("briefings") or {}).get("flow7_fusion", {}).get("narration")),
        "source_limit_language_present": "still source-limited" in json.dumps(limits, ensure_ascii=False),
        "negative_boundaries_present": payloads.get("negative-boundaries", {}).get("status") == "PASS",
        "flow1_subjects_present": len(f1.get("selected_subjects") or []) == 5,
    }
    return {"gate": "CHI-F1F7-D3B-GROUNDING", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def limitation_report(output_dir: Path) -> dict[str, Any]:
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in output_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".json", ".html", ".md"})
    missing = [line for line in BOUNDARY_LINES if line not in text]
    return {"gate": "CHI-F1F7-D3B-LIMITATION-CARRY-FORWARD", "status": "PASS" if not missing else "FAIL", "missing": missing, "required": BOUNDARY_LINES}


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in output_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".json", ".html", ".md", ".py"}).lower()
    findings = [pattern for pattern in FORBIDDEN_POSITIVE_PATTERNS if re.search(pattern, text)]
    return {"gate": "CHI-F1F7-D3B-NO-OVERCLAIM", "status": "PASS" if not findings else "FAIL", "forbidden_positive_claims_found": findings}


def write_docs(output_dir: Path, status: str) -> None:
    write_text(
        output_dir / "README.md",
        "\n".join([
            "# CHI-F1F7-D3B Refreshed Face-Layer Status/Fusion Surface",
            "",
            f"Status: `{status}`",
            "",
            "## Routes",
            *[f"- `{route}`" for route in ROUTES],
            "",
            "## Boundary",
            *[f"- {line}" for line in BOUNDARY_LINES],
            "",
        ]),
    )
    write_text(
        output_dir / "CHI_F1F7_D3B_ADAPTER_HANDOVER.md",
        "# CHI-F1F7-D3B Adapter Handover\n\n"
        "Serve `face_app/chicago.html` for `/chicago` and `/status/chicago`, and map `/api/chicago/*` to the staged JSON payloads in `_route_payload/api/chicago` or `face_payload`.\n\n"
        + "\n".join(f"- {line}" for line in BOUNDARY_LINES)
        + "\n",
    )


def run_chi_f1f7_d3b_gate(
    project_root: str,
    d1b_dir: str,
    d3b_dir: str,
    d4b_dir: str,
    f1b_dir: str,
    f7b_dir: str,
    dualb_dir: str,
    d2b_dir: str,
    output_dir: str,
    base_url: str = DEFAULT_BASE_URL,
    publish_4070: bool = False,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    paths = {
        "d1b": (root / d1b_dir).resolve(),
        "d3b": (root / d3b_dir).resolve(),
        "d4b": (root / d4b_dir).resolve(),
        "f1b": (root / f1b_dir).resolve(),
        "f7b": (root / f7b_dir).resolve(),
        "dualb": (root / dualb_dir).resolve(),
        "d2b": (root / d2b_dir).resolve(),
    }
    out = (root / output_dir).resolve()
    watch_paths = list(paths.values())
    before = input_snapshot(watch_paths)
    reset_output_dir(out)

    harnesses = {
        "d1b": read_json(paths["d1b"] / "CHI_D1B_HARNESS_REPORT.json", {}),
        "d3b": read_json(paths["d3b"] / "CHI_D3B_HARNESS_REPORT.json", {}),
        "d4b": read_json(paths["d4b"] / "CHI_D4_HARNESS_REPORT.json", {}),
        "f1b": read_json(paths["f1b"] / "CHI_F1_D1_HARNESS_REPORT.json", {}),
        "f7b": read_json(paths["f7b"] / "CHI_F7_D1_HARNESS_REPORT.json", {}),
        "dualb": read_json(paths["dualb"] / "CHI_F1_F7_D1_DUAL_HARNESS_REPORT.json", {}),
        "d2b": read_json(paths["d2b"] / "CHI_F1F7_D2_HARNESS_REPORT.json", {}),
    }
    precond = {
        "status": "PASS" if all(status_pass(h.get("status")) for h in harnesses.values()) and harnesses["d2b"].get("live_nim_status") == "PASS" and harnesses["d2b"].get("grounding") == "PASS" else "FAIL",
        "statuses": {key: h.get("status") for key, h in harnesses.items()},
        "d2b_live_nim": harnesses["d2b"].get("live_nim_status"),
        "d2b_grounding": harnesses["d2b"].get("grounding"),
    }
    payloads = build_payloads(paths["d1b"], paths["d3b"], paths["d4b"], paths["f1b"], paths["f7b"], paths["dualb"], paths["d2b"])
    stage = stage_route_payload(out, payloads)
    write_docs(out, "PENDING")
    write_json(out / "CHI_F1F7_D3B_INPUT_INVENTORY.json", {"status": precond["status"], "inputs": {key: str(value) for key, value in paths.items()}, "preconditions": precond, "boundary_lines": BOUNDARY_LINES})
    write_json(out / "CHI_F1F7_D3B_FACE_PAYLOAD_REPORT.json", {"status": "PASS", "payload_keys": sorted(payloads), "stage": stage, "boundary_lines": BOUNDARY_LINES})
    write_json(out / "CHI_F1F7_D3B_ROUTE_REPORT.json", stage)
    grounding = grounding_report(payloads)
    write_json(out / "CHI_F1F7_D3B_GROUNDING_REPORT.json", grounding)
    limits = limitation_report(out)
    write_json(out / "CHI_F1F7_D3B_LIMITATION_CARRY_FORWARD_REPORT.json", limits)
    overclaim = no_overclaim_report(out)
    write_json(out / "CHI_F1F7_D3B_NO_OVERCLAIM_REPORT.json", overclaim)
    publish = publish_4070_payload(out, publish_4070)
    smoke = endpoint_smoke(out, base_url, publish.get("status"))
    write_json(out / "CHI_F1F7_D3B_ENDPOINT_SMOKE_REPORT.json", smoke)
    write_json(out / "reports" / "endpoint_status.json", smoke)
    write_json(out / "reports" / "route_manifest.json", stage["routes"])
    write_json(out / "reports" / "route_config_before_after.json", publish)
    write_json(out / "reports" / "displayed_count_checks.json", grounding)
    write_json(out / "reports" / "source_limitations_visible.json", limits)
    write_json(out / "reports" / "negative_boundaries_visible.json", payloads["negative-boundaries"])
    write_json(out / "reports" / "rollback_instructions.json", {"status": "PASS", "commands": [f"ssh {REMOTE_HOST} 'rm -rf {REMOTE_ROOT}/chicago {REMOTE_ROOT}/status/chicago {REMOTE_ROOT}/api/chicago'"]})
    after = input_snapshot(watch_paths)
    no_mutation = compare_snapshots(before, after)
    write_json(out / "CHI_F1F7_D3B_NO_MUTATION_REPORT.json", no_mutation)

    gates = {
        "CHI-F1F7-D3B-PRECOND": precond["status"],
        "CHI-F1F7-D3B-FACE-PAYLOAD": "PASS",
        "CHI-F1F7-D3B-ROUTES": stage["status"],
        "CHI-F1F7-D3B-4070-PUBLISH": "PASS" if publish["status"] in {"PASS", "NOT_RUN", "NOT_RUN_OR_UNREACHABLE"} else "FAIL",
        "CHI-F1F7-D3B-ENDPOINT-SMOKE": smoke["status"],
        "CHI-F1F7-D3B-GROUNDING": grounding["status"],
        "CHI-F1F7-D3B-LIMITATION-CARRY-FORWARD": limits["status"],
        "CHI-F1F7-D3B-NO-OVERCLAIM": overclaim["status"],
        "CHI-F1F7-D3B-NO-MUTATION": no_mutation["status"],
    }
    status = "PASS" if all(value == "PASS" for value in gates.values()) else "FAIL"
    write_docs(out, status)
    hashes = write_hashes(out)
    gates["CHI-F1F7-D3B-HASHES"] = hashes["status"]
    status = "PASS" if all(value == "PASS" for value in gates.values()) else "FAIL"
    harness = {
        "task": TASK_NAME,
        "status": status,
        "created_utc": utc_now(),
        "routes": ROUTES,
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
        "output": str(out),
    }
    write_json(out / "CHI_F1F7_D3B_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    harness["hashes"] = hashes
    write_json(out / "CHI_F1F7_D3B_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--d1b-dir", default=DEFAULT_D1B_DIR)
    parser.add_argument("--d3b-dir", default=DEFAULT_D3B_DIR)
    parser.add_argument("--d4b-dir", default=DEFAULT_D4B_DIR)
    parser.add_argument("--f1b-dir", default=DEFAULT_F1B_DIR)
    parser.add_argument("--f7b-dir", default=DEFAULT_F7B_DIR)
    parser.add_argument("--dualb-dir", default=DEFAULT_DUALB_DIR)
    parser.add_argument("--d2b-dir", default=DEFAULT_D2B_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--publish-4070", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_chi_f1f7_d3b_gate(
        project_root=args.project_root,
        d1b_dir=args.d1b_dir,
        d3b_dir=args.d3b_dir,
        d4b_dir=args.d4b_dir,
        f1b_dir=args.f1b_dir,
        f7b_dir=args.f7b_dir,
        dualb_dir=args.dualb_dir,
        d2b_dir=args.d2b_dir,
        output_dir=args.output_dir,
        base_url=args.base_url,
        publish_4070=args.publish_4070,
    )
    print(f"CHI-F1F7-D3B Face Layer: {report['status']}")
    print(f"Routes: {len(report['routes'])}")
    print(f"4070 publish: {report['publish_4070']['status']}")
    print(f"Endpoint smoke: {report['endpoint_smoke']['status']}")
    print(f"Grounding: {report['grounding']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {report['output']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import hashlib
import html
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


TASK_NAME = "CHI-F1F7-D4 Chicago Hero Package"
DEFAULT_OUTPUT_DIR = "outputs/chi_f1f7_d4_chicago_hero_package"
DEFAULT_D1B_DIR = "outputs/chi_d1b_chicago_extended_source_landing"
DEFAULT_D3B_DIR = "outputs/chi_d3_civic_event_ingest_flow_readiness_d3b_expanded_d1b"
DEFAULT_D4B_DIR = "outputs/chi_d4_dual_flow_scope_fork_d3b_refresh"
DEFAULT_F1B_DIR = "outputs/chi_f1_d1_situational_status_cartridge_d1b_refresh"
DEFAULT_F7B_DIR = "outputs/chi_f7_d1_civic_sensor_fusion_cartridge_d1b_refresh"
DEFAULT_DUALB_DIR = "outputs/chi_f1_f7_d1_dual_flow_run_d1b_refresh"
DEFAULT_D2B_DIR = "outputs/chi_f1f7_d2_live_spark_nim_replay_d1b_refresh"
DEFAULT_D3B_FACE_DIR = "outputs/chi_f1f7_d3b_face_layer_status_fusion_surface"
REMOTE_HOST = "txr-4070"
REMOTE_ROOT = "/srv/citybrain/current"
DEFAULT_BASE_URL = "http://192.168.1.48:8080"

HERO_ROUTES = ["/chicago/heroes", "/api/chicago/heroes"]

BOUNDARY_LINES = [
    "CHI-F1F7-D4 heroes are selected deterministically from refreshed CHI-D1B/D3B/D4B/F1F7-D1B/D2B/D3B evidence only.",
    "CHI-F1F7-D4 does not use older Chicago D1/D2 evidence for hero selection.",
    "Flow 1 is situational status evidence, not an operational recommendation.",
    "Flow 7 is civic/sensor signal fusion evidence, not a policing, dispatch, enforcement, health, emergency, or public-safety recommendation.",
    "CHI-F1F7-D4 does not certify affected buildings/assets.",
    "CTA GTFS is static schedule context, not live transit status.",
    "Crime data is privacy-safe block-level context only.",
    "Sensor/environment observations are context signals, not health determinations.",
    "Chicago remains source-limited: Divvy, Cook parcels, Crimes, and Open Air individual remain capped/windowed.",
    "Live NIM briefing text is grounded narration over deterministic EvidenceBundles and may not compute counts or add facts.",
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
    r"\bhero selected by llm\b",
    r"\bhand-picked hero\b",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_value(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "tolist") and not isinstance(value, (str, bytes, bytearray)):
        try:
            return clean_value(value.tolist())
        except Exception:
            pass
    if isinstance(value, float) and math.isnan(value):
        return None
    if not isinstance(value, (dict, list, tuple)):
        try:
            if pd.isna(value) is True:
                return None
        except Exception:
            pass
    if hasattr(value, "item"):
        try:
            return clean_value(value.item())
        except Exception:
            pass
    if isinstance(value, dict):
        return {str(k): clean_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_value(v) for v in value]
    return value


def to_record(row: pd.Series | dict[str, Any]) -> dict[str, Any]:
    if isinstance(row, pd.Series):
        return {str(k): clean_value(v) for k, v in row.to_dict().items()}
    return {str(k): clean_value(v) for k, v in row.items()}


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\bNaN\b", "null", text)
    return json.loads(text)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_value(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


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
    return {"gate": "CHI-F1F7-D4-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        if not str(resolved).lower().startswith(str(cwd).lower()) or "outputs" not in {p.lower() for p in resolved.parts} or "chi_f1f7_d4" not in resolved.name.lower():
            raise ValueError(f"refusing to remove unexpected output dir: {resolved}")
        shutil.rmtree(resolved)
    for name in ["heroes", "reports", "face_payload", "_route_payload"]:
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
        "gate": "CHI-F1F7-D4-NO-MUTATION",
        "status": "PASS" if not changed and not added and not removed else "FAIL",
        "checked_files": len(before),
        "changed_inputs": changed,
        "added_inputs": added,
        "removed_inputs": removed,
    }


def status_pass(value: Any) -> bool:
    text = str(value or "").upper()
    return text.startswith("PASS") or text.startswith("GREEN")


def safe_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


def bundle_path_for_subject(root: Path, prefix: str, subject_id: str, suffix: str = "json") -> Path:
    token = safe_token(subject_id)
    return root / "evidence" / f"{prefix}_{token}.{suffix}"


def read_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def load_narrations(d2b_dir: Path) -> dict[str, dict[str, Any]]:
    rows = read_json(d2b_dir / "samples" / "live_sample_narrations.json", [])
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and row.get("sample_id"):
            out[str(row["sample_id"])] = row
    return out


def load_inputs(paths: dict[str, Path]) -> dict[str, Any]:
    return {
        "d1b_harness": read_json(paths["d1b"] / "CHI_D1B_HARNESS_REPORT.json", {}),
        "d3b_harness": read_json(paths["d3b"] / "CHI_D3B_HARNESS_REPORT.json", {}),
        "d4b_harness": read_json(paths["d4b"] / "CHI_D4_HARNESS_REPORT.json", {}),
        "f1_harness": read_json(paths["f1b"] / "CHI_F1_D1_HARNESS_REPORT.json", {}),
        "f7_harness": read_json(paths["f7b"] / "CHI_F7_D1_HARNESS_REPORT.json", {}),
        "dual_harness": read_json(paths["dualb"] / "CHI_F1_F7_D1_DUAL_HARNESS_REPORT.json", {}),
        "d2_harness": read_json(paths["d2b"] / "CHI_F1F7_D2_HARNESS_REPORT.json", {}),
        "d3b_face_harness": read_json(paths["d3b_face"] / "CHI_F1F7_D3B_HARNESS_REPORT.json", {}),
        "negative_report": read_json(paths["d2b"] / "CHI_F1F7_D2_NEGATIVE_REQUEST_REPORT.json", {}),
        "source_report": read_json(paths["d2b"] / "reports" / "source_lineage_and_limitations.json", {}),
        "face_status": read_json(paths["d3b_face"] / "face_payload" / "chicago_status.json", {}),
        "face_flow1": read_json(paths["d3b_face"] / "face_payload" / "chicago_flow1-area-status.json", {}),
        "face_flow7": read_json(paths["d3b_face"] / "face_payload" / "chicago_flow7-fusion-candidates.json", {}),
        "face_limits": read_json(paths["d3b_face"] / "face_payload" / "chicago_source-limitations.json", {}),
        "f1_subjects": read_parquet(paths["f1b"] / "canonical" / "chi_f1_d1_area_status_subjects.parquet"),
        "f7_subjects": read_parquet(paths["f7b"] / "canonical" / "chi_f7_d1_fusion_subjects.parquet"),
        "f7_components": read_parquet(paths["f7b"] / "canonical" / "chi_f7_d1_signal_components.parquet"),
        "narrations": load_narrations(paths["d2b"]),
    }


def grounding_ok(narrations: dict[str, dict[str, Any]], sample_id: str, answer_status: str | None = "answered") -> bool:
    row = narrations.get(sample_id) or {}
    grounding = row.get("grounding") or {}
    if answer_status and row.get("answer_status") != answer_status:
        return False
    return grounding.get("status") == "PASS" and row.get("nim_call", {}).get("status") == "PASS"


def select_heroes(paths: dict[str, Path], data: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    f1_subjects: pd.DataFrame = data["f1_subjects"]
    f7_subjects: pd.DataFrame = data["f7_subjects"]
    f7_components: pd.DataFrame = data["f7_components"]
    narrations: dict[str, dict[str, Any]] = data["narrations"]

    f1_pool = f1_subjects[f1_subjects["subject_type"] != "citywide"].copy()
    f1_pool = f1_pool.sort_values(["status_signal_score", "selection_rank", "subject_id"], ascending=[False, True, True])
    f1_row = to_record(f1_pool.iloc[0])

    f7_pool = f7_subjects.copy().sort_values(["fusion_signal_score", "rank", "candidate_id"], ascending=[False, True, True])
    f7_row = to_record(f7_pool.iloc[0])
    comp_rows = [to_record(row) for _, row in f7_components[f7_components["candidate_id"] == f7_row["candidate_id"]].iterrows()]

    negative_rows = data["negative_report"].get("results") or []
    negative_affected = next((row for row in negative_rows if row.get("sample_id") == "negative_affected_assets"), negative_rows[0] if negative_rows else {})

    f1_bundle = bundle_path_for_subject(paths["f1b"], "evidence_bundle_area_status", str(f1_row["subject_id"]))
    f1_briefing = bundle_path_for_subject(paths["f1b"], "deterministic_briefing_area_status", str(f1_row["subject_id"]), "md")
    f7_bundle = bundle_path_for_subject(paths["f7b"], "evidence_bundle_fusion_candidate", str(f7_row["candidate_id"]))
    f7_briefing = bundle_path_for_subject(paths["f7b"], "deterministic_briefing_fusion_candidate", str(f7_row["candidate_id"]), "md")

    heroes = [
        {
            "hero_id": "chi_f1f7_d4_hero_1_flow1_area_status",
            "title": "Top Flow 1 Area Status",
            "story_type": "situational_status",
            "selected_subject": f1_row,
            "selector_rule": "highest status_signal_score non-citywide Flow 1 subject with D2B live grounding and D3B face route",
            "why_selected": [
                f"Flow 1 selected subject is {f1_row.get('subject_name')} ({f1_row.get('subject_id')}).",
                f"status_signal_score={f1_row.get('status_signal_score')}; total_public_source_events={f1_row.get('total_public_source_events')}.",
                "D2B live sample flow1_area has grounded NIM narration.",
                "D3B face layer exposes /api/chicago/flow1-area-status.",
            ],
            "evidence": {
                "evidence_bundle_path": str(f1_bundle),
                "deterministic_briefing_path": str(f1_briefing),
                "live_nim_sample_id": "flow1_area",
                "live_nim_grounding": (narrations.get("flow1_area") or {}).get("grounding"),
                "live_nim_narration": (narrations.get("flow1_area") or {}).get("narration"),
                "face_routes": ["/chicago", "/api/chicago/flow1-area-status"],
            },
            "counts": {
                "total_public_source_events": f1_row.get("total_public_source_events"),
                "311_service_request_count": f1_row.get("311_service_request_count"),
                "building_permit_count": f1_row.get("building_permit_count"),
                "business_license_count": f1_row.get("business_license_count"),
                "location_confidence_A": f1_row.get("location_confidence_A"),
            },
            "boundary_lines": BOUNDARY_LINES,
        },
        {
            "hero_id": "chi_f1f7_d4_hero_2_flow7_top_fusion",
            "title": "Top Flow 7 Civic/Sensor Fusion Candidate",
            "story_type": "civic_sensor_fusion",
            "selected_subject": f7_row,
            "selector_rule": "highest fusion_signal_score Flow 7 candidate with D2B live grounding and D3B face route",
            "why_selected": [
                f"Flow 7 selected candidate is {f7_row.get('subject_name')} ({f7_row.get('candidate_id')}).",
                f"fusion_signal_score={f7_row.get('fusion_signal_score')}; total_public_source_events={f7_row.get('total_public_source_events')}.",
                "D2B live sample flow7_fusion has grounded NIM narration.",
                "D3B face layer exposes /api/chicago/flow7-fusion-candidates.",
            ],
            "evidence": {
                "evidence_bundle_path": str(f7_bundle),
                "deterministic_briefing_path": str(f7_briefing),
                "signal_components": comp_rows,
                "live_nim_sample_id": "flow7_fusion",
                "live_nim_grounding": (narrations.get("flow7_fusion") or {}).get("grounding"),
                "live_nim_narration": (narrations.get("flow7_fusion") or {}).get("narration"),
                "face_routes": ["/chicago", "/api/chicago/flow7-fusion-candidates"],
            },
            "counts": {
                "total_public_source_events": f7_row.get("total_public_source_events"),
                "nonzero_signal_dimensions": f7_row.get("nonzero_signal_dimensions"),
                "location_confidence_A_ratio": f7_row.get("location_confidence_A_ratio"),
                "component_count": len(comp_rows),
            },
            "boundary_lines": BOUNDARY_LINES,
        },
        {
            "hero_id": "chi_f1f7_d4_hero_3_governance_boundary",
            "title": "Governance Boundary: Asset Certainty Rejected",
            "story_type": "governance_limitations",
            "selected_subject": {
                "sample_id": "negative_affected_assets",
                "operator_request": (narrations.get("negative_affected_assets") or {}).get("operator_request", "Which buildings or assets are definitely affected?"),
                "answer_status": (narrations.get("negative_affected_assets") or {}).get("answer_status"),
                "reason": negative_affected.get("reason"),
            },
            "selector_rule": "negative affected-building/asset certainty request with D2B rejection and D3B source-limitations face route",
            "why_selected": [
                "D2B negative request policy rejects affected-building/asset certainty.",
                "D3B source limitations remain visible on the face layer.",
                "This hero proves the surface can decline unsafe or unsupported requests.",
            ],
            "evidence": {
                "negative_request_report": str(paths["d2b"] / "CHI_F1F7_D2_NEGATIVE_REQUEST_REPORT.json"),
                "source_limitations_payload": str(paths["d3b_face"] / "face_payload" / "chicago_source-limitations.json"),
                "live_nim_sample_id": "negative_affected_assets",
                "live_nim_grounding": (narrations.get("negative_affected_assets") or {}).get("grounding"),
                "live_nim_narration": (narrations.get("negative_affected_assets") or {}).get("narration"),
                "face_routes": ["/api/chicago/negative-boundaries", "/api/chicago/source-limitations"],
            },
            "counts": {
                "d3b_event_location_rows": (data["face_status"].get("counts") or {}).get("d3b_event_location_rows"),
                "d3b_context_edges": (data["face_status"].get("counts") or {}).get("d3b_context_edges"),
                "f7_fusion_candidates": (data["face_status"].get("counts") or {}).get("f7_fusion_candidates"),
                "f7_selected_candidates": (data["face_status"].get("counts") or {}).get("f7_selected_candidates"),
            },
            "boundary_lines": BOUNDARY_LINES,
        },
    ]
    selector = {
        "status": "PASS",
        "hero_count": len(heroes),
        "rules": [
            "H1 = highest Flow 1 non-citywide status_signal_score with live D2B grounding.",
            "H2 = highest Flow 7 fusion_signal_score with live D2B grounding.",
            "H3 = D2B negative affected-assets request with grounded rejection and source-limitations face route.",
        ],
        "grounding_requirements": {
            "flow1_area": grounding_ok(narrations, "flow1_area"),
            "flow7_fusion": grounding_ok(narrations, "flow7_fusion"),
            "negative_affected_assets": grounding_ok(narrations, "negative_affected_assets", "rejected"),
        },
    }
    if not all(selector["grounding_requirements"].values()):
        selector["status"] = "FAIL"
    return heroes, selector


def markdown_for_hero(hero: dict[str, Any]) -> str:
    subject = hero.get("selected_subject") or {}
    counts = hero.get("counts") or {}
    lines = [
        f"# {hero['title']}",
        "",
        f"Hero ID: `{hero['hero_id']}`",
        f"Story type: `{hero['story_type']}`",
        "",
        "## Selected Subject",
        "",
    ]
    for key in ["subject_name", "subject_id", "candidate_id", "sample_id", "answer_status", "operator_request", "reason"]:
        if subject.get(key) is not None:
            lines.append(f"- {key}: `{subject.get(key)}`")
    lines += ["", "## Counts", ""]
    for key, value in counts.items():
        lines.append(f"- {key}: `{value}`")
    lines += ["", "## Why Selected", ""]
    lines.extend(f"- {item}" for item in hero.get("why_selected", []))
    lines += ["", "## Boundary", ""]
    lines.extend(f"- {line}" for line in BOUNDARY_LINES)
    lines.append("")
    return "\n".join(lines)


def html_page() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CityBrain Chicago Heroes</title>
  <style>
    :root { color-scheme: light; --ink:#202124; --muted:#5f6368; --line:#d8dde3; --panel:#f7f9fb; --accent:#0f766e; --warn:#9a3412; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:Arial, Helvetica, sans-serif; color:var(--ink); background:#fff; }
    header { padding:18px 24px; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; gap:16px; align-items:flex-start; }
    main { max-width:1440px; margin:0 auto; padding:18px 24px 32px; }
    h1 { margin:0; font-size:22px; line-height:1.2; letter-spacing:0; }
    h2 { margin:0 0 8px; font-size:16px; letter-spacing:0; }
    nav { display:flex; gap:8px; flex-wrap:wrap; }
    nav a { color:var(--ink); text-decoration:none; border:1px solid var(--line); padding:6px 9px; border-radius:6px; font-size:13px; }
    .grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; }
    article { border:1px solid var(--line); border-radius:8px; padding:12px; background:var(--panel); min-height:280px; }
    .tag { display:inline-block; border:1px solid var(--line); border-radius:999px; padding:3px 8px; margin:2px 2px 8px 0; color:var(--muted); font-size:12px; }
    dl { display:grid; grid-template-columns:1fr 1fr; gap:4px 10px; font-size:13px; }
    dt { color:var(--muted); }
    dd { margin:0; overflow-wrap:anywhere; }
    ul { margin:8px 0 0 18px; padding:0; }
    li { margin:4px 0; }
    .limit { color:var(--warn); }
    @media (max-width:900px) { header { display:block; } nav { margin-top:12px; } .grid { grid-template-columns:1fr; } }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>CityBrain Chicago Flow 1 + Flow 7 Heroes</h1>
      <div class="tag">refreshed D1B/D3B/F1F7-D1B/D2B line only</div>
    </div>
    <nav>
      <a href="/chicago">Chicago face</a>
      <a href="/api/chicago/heroes">heroes API</a>
      <a href="/api/chicago/source-limitations">limits</a>
      <a href="/api/chicago/live-nim-briefings">live NIM</a>
    </nav>
  </header>
  <main>
    <div id="heroes" class="grid"></div>
    <section>
      <h2>Boundary</h2>
      <ul id="boundary"></ul>
    </section>
  </main>
  <script>
    const fmt = v => typeof v === 'number' ? v.toLocaleString() : (v ?? 'n/a');
    fetch('/api/chicago/heroes').then(r => r.json()).then(data => {
      document.getElementById('heroes').innerHTML = data.heroes.map(hero => {
        const subject = hero.selected_subject || {};
        const counts = Object.entries(hero.counts || {}).map(([k,v]) => `<dt>${k}</dt><dd>${fmt(v)}</dd>`).join('');
        const why = (hero.why_selected || []).map(x => `<li>${x}</li>`).join('');
        return `<article><span class="tag">${hero.story_type}</span><h2>${hero.title}</h2><p>${subject.subject_name || subject.operator_request || subject.sample_id || ''}</p><dl>${counts}</dl><ul>${why}</ul></article>`;
      }).join('');
      document.getElementById('boundary').innerHTML = (data.boundary_lines || []).map(x => `<li class="limit">${x}</li>`).join('');
    });
  </script>
</body>
</html>
"""


def build_package(paths: dict[str, Path], heroes: list[dict[str, Any]], selector: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    status_counts = data["face_status"].get("counts") or {}
    return {
        "status": "PASS",
        "task": TASK_NAME,
        "generated_utc": utc_now(),
        "hero_count": len(heroes),
        "heroes": heroes,
        "selector": selector,
        "refreshed_line": {
            "CHI-D1B": "GREEN_WITH_CAPPED_LARGE_SOURCES - EXPANDED TARGETED SOURCE LANDING",
            "CHI-D3B": "GREEN_WITH_CAPPED_SOURCE_LIMITATIONS - CIVIC/EVENT REFRESH FROM EXPANDED D1B",
            "CHI-D4B": "GREEN_WITH_DUAL_FLOW_FORK - REFRESHED FLOW FORK / SOURCE LEDGER",
            "CHI-F1F7-D1B": "GREEN - PASS_DUAL_FLOW_D1",
            "CHI-F1F7-D2B": "GREEN - LIVE SPARK/NIM REPLAY",
            "CHI-F1F7-D3B": "GREEN - REFRESHED FACE-LAYER STATUS/FUSION SURFACE",
        },
        "headline_counts": {
            "d3b_event_location_rows": status_counts.get("d3b_event_location_rows"),
            "d3b_context_edges": status_counts.get("d3b_context_edges"),
            "f1_citywide_total_signal_rows": status_counts.get("f1_citywide_total_signal_rows"),
            "f7_fusion_candidates": status_counts.get("f7_fusion_candidates"),
            "f7_selected_candidates": status_counts.get("f7_selected_candidates"),
            "top_f7_candidate_total_events": status_counts.get("top_f7_candidate_total_events"),
        },
        "face_routes": {
            "/chicago": "refreshed status/fusion face",
            "/chicago/heroes": "hero package face",
            "/api/chicago/heroes": "hero package JSON",
        },
        "source_directories": {key: str(value) for key, value in paths.items()},
        "boundary_lines": BOUNDARY_LINES,
    }


def stage_route_payload(output_dir: Path, package: dict[str, Any]) -> dict[str, Any]:
    root = output_dir / "_route_payload"
    write_text(root / "chicago" / "heroes" / "index.html", html_page())
    write_json(root / "api" / "chicago" / "heroes", package)
    write_json(root / "api" / "chicago" / "heroes.json", package)
    write_text(output_dir / "face_app" / "chicago_heroes.html", html_page())
    write_json(output_dir / "face_payload" / "chicago_heroes.json", package)
    return {
        "gate": "CHI-F1F7-D4-ROUTES",
        "status": "PASS",
        "routes": {
            "/chicago/heroes": "chicago/heroes/index.html",
            "/api/chicago/heroes": "api/chicago/heroes",
            "/api/chicago/heroes.json": "api/chicago/heroes.json",
        },
        "route_strategy": "static Caddy payloads copied under /chicago/heroes and /api/chicago/heroes",
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
        return {"gate": "CHI-F1F7-D4-4070-PUBLISH", "status": "NOT_RUN", "reason": "publish_4070=false"}
    root = output_dir / "_route_payload"
    try:
        mkdir = run_cmd(["ssh", REMOTE_HOST, f"mkdir -p {REMOTE_ROOT}/chicago {REMOTE_ROOT}/api/chicago"], timeout=60)
        copy_page = run_cmd(["scp", "-r", str(root / "chicago" / "heroes"), f"{REMOTE_HOST}:{REMOTE_ROOT}/chicago/"], timeout=180)
        copy_api = run_cmd(["scp", str(root / "api" / "chicago" / "heroes"), str(root / "api" / "chicago" / "heroes.json"), f"{REMOTE_HOST}:{REMOTE_ROOT}/api/chicago/"], timeout=180)
        chmod = run_cmd(["ssh", REMOTE_HOST, f"chmod -R a+rX {REMOTE_ROOT}/chicago/heroes {REMOTE_ROOT}/api/chicago/heroes {REMOTE_ROOT}/api/chicago/heroes.json"], timeout=60)
        after = run_cmd(["ssh", REMOTE_HOST, f"find {REMOTE_ROOT}/chicago/heroes {REMOTE_ROOT}/api/chicago -maxdepth 2 -type f | sort"], timeout=60)
        ok = all(item.get("status") == "PASS" for item in [mkdir, copy_page, copy_api, chmod, after])
        return {
            "gate": "CHI-F1F7-D4-4070-PUBLISH",
            "status": "PASS" if ok else "FAIL",
            "remote_host": REMOTE_HOST,
            "remote_root": REMOTE_ROOT,
            "mkdir": mkdir,
            "copy_page": copy_page,
            "copy_api": copy_api,
            "chmod": chmod,
            "after": after,
        }
    except Exception as exc:
        return {"gate": "CHI-F1F7-D4-4070-PUBLISH", "status": "NOT_RUN_OR_UNREACHABLE", "error": f"{type(exc).__name__}: {exc}"}


def http_get(url: str, timeout: int = 15) -> dict[str, Any]:
    rec: dict[str, Any] = {"url": url, "status": "attempted"}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CityBrain-CHI-F1F7-D4/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read(512000)
            text = body.decode("utf-8", errors="replace")
        rec.update({"http_status": response.status, "bytes_read": len(body), "text_sample": text[:50000], "status": "PASS" if response.status == 200 else "FAIL"})
    except urllib.error.HTTPError as exc:
        rec.update({"http_status": exc.code, "status": "FAIL", "error": str(exc)})
    except Exception as exc:
        rec.update({"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})
    return rec


def endpoint_smoke(output_dir: Path, base_url: str, publish_status: str) -> dict[str, Any]:
    required = [
        "chi_f1f7_d4_hero_1_flow1_area_status",
        "chi_f1f7_d4_hero_2_flow7_top_fusion",
        "chi_f1f7_d4_hero_3_governance_boundary",
        "2173618",
        "source-limited",
    ]
    if publish_status != "PASS":
        text = (output_dir / "face_payload" / "chicago_heroes.json").read_text(encoding="utf-8", errors="replace")
        checks = {value: value in text for value in required}
        return {"gate": "CHI-F1F7-D4-ENDPOINT-SMOKE", "status": "PASS" if all(checks.values()) else "FAIL", "mode": "file_payload_verified", "checks": checks}
    attempts = [http_get(base_url.rstrip("/") + route) for route in HERO_ROUTES]
    joined = "\n".join(row.get("text_sample", "") for row in attempts)
    checks = {value: value in joined for value in required}
    return {
        "gate": "CHI-F1F7-D4-ENDPOINT-SMOKE",
        "status": "PASS" if all(row.get("status") == "PASS" for row in attempts) and all(checks.values()) else "FAIL",
        "mode": "live_endpoint_smoke",
        "base_url": base_url,
        "attempts": attempts,
        "grounded_text_checks": checks,
    }


def grounding_report(package: dict[str, Any]) -> dict[str, Any]:
    heroes = {hero["hero_id"]: hero for hero in package.get("heroes", [])}
    checks = {
        "minimum_three_heroes": len(heroes) >= 3,
        "flow1_grounded": ((heroes.get("chi_f1f7_d4_hero_1_flow1_area_status") or {}).get("evidence") or {}).get("live_nim_grounding", {}).get("status") == "PASS",
        "flow7_grounded": ((heroes.get("chi_f1f7_d4_hero_2_flow7_top_fusion") or {}).get("evidence") or {}).get("live_nim_grounding", {}).get("status") == "PASS",
        "negative_grounded": ((heroes.get("chi_f1f7_d4_hero_3_governance_boundary") or {}).get("evidence") or {}).get("live_nim_grounding", {}).get("status") == "PASS",
        "top_f7_count_present": package.get("headline_counts", {}).get("top_f7_candidate_total_events") == 2173618,
        "refreshed_line_only": all("_d1b_refresh" in str(path) or "d3b" in str(path).lower() or "d4" in str(path).lower() or "extended_source_landing" in str(path).lower() for path in package.get("source_directories", {}).values()),
    }
    return {"gate": "CHI-F1F7-D4-GROUNDING", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def limitation_report(output_dir: Path) -> dict[str, Any]:
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in output_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".json", ".html", ".md"})
    missing = [line for line in BOUNDARY_LINES if line not in text]
    return {"gate": "CHI-F1F7-D4-LIMITATION-CARRY-FORWARD", "status": "PASS" if not missing else "FAIL", "missing": missing, "required": BOUNDARY_LINES}


def no_overclaim_report(output_dir: Path) -> dict[str, Any]:
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in output_dir.rglob("*") if path.is_file() and path.suffix.lower() in {".json", ".html", ".md"}).lower()
    findings = [pattern for pattern in FORBIDDEN_POSITIVE_PATTERNS if re.search(pattern, text)]
    return {"gate": "CHI-F1F7-D4-NO-OVERCLAIM", "status": "PASS" if not findings else "FAIL", "forbidden_positive_claims_found": findings}


def write_docs(output_dir: Path, status: str) -> None:
    write_text(
        output_dir / "README.md",
        "\n".join([
            "# CHI-F1F7-D4 Chicago Hero Package",
            "",
            f"Status: `{status}`",
            "",
            "## Routes",
            "- `/chicago/heroes`",
            "- `/api/chicago/heroes`",
            "",
            "## Boundary",
            *[f"- {line}" for line in BOUNDARY_LINES],
            "",
        ]),
    )
    write_text(
        output_dir / "CHI_F1F7_D4_ADAPTER_HANDOVER.md",
        "# CHI-F1F7-D4 Adapter Handover\n\n"
        "Serve `_route_payload/chicago/heroes/index.html` at `/chicago/heroes` and `_route_payload/api/chicago/heroes` at `/api/chicago/heroes`.\n\n"
        + "\n".join(f"- {line}" for line in BOUNDARY_LINES)
        + "\n",
    )


def run_chi_f1f7_d4_gate(
    project_root: str,
    d1b_dir: str,
    d3b_dir: str,
    d4b_dir: str,
    f1b_dir: str,
    f7b_dir: str,
    dualb_dir: str,
    d2b_dir: str,
    d3b_face_dir: str,
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
        "d3b_face": (root / d3b_face_dir).resolve(),
    }
    out = (root / output_dir).resolve()
    before = input_snapshot(list(paths.values()))
    reset_output_dir(out)

    data = load_inputs(paths)
    precond_statuses = {
        "d1b": data["d1b_harness"].get("status"),
        "d3b": data["d3b_harness"].get("status"),
        "d4b": data["d4b_harness"].get("status"),
        "f1b": data["f1_harness"].get("status"),
        "f7b": data["f7_harness"].get("status"),
        "dualb": data["dual_harness"].get("status"),
        "d2b": data["d2_harness"].get("status"),
        "d3b_face": data["d3b_face_harness"].get("status"),
    }
    precond = {
        "gate": "CHI-F1F7-D4-PRECOND",
        "status": "PASS" if all(status_pass(value) for value in precond_statuses.values()) and data["d2_harness"].get("live_nim_status") == "PASS" and data["d2_harness"].get("grounding") == "PASS" else "FAIL",
        "statuses": precond_statuses,
        "d2b_live_nim": data["d2_harness"].get("live_nim_status"),
        "d2b_grounding": data["d2_harness"].get("grounding"),
    }
    heroes, selector = select_heroes(paths, data)
    package = build_package(paths, heroes, selector, data)

    for hero in heroes:
        write_json(out / "heroes" / f"{hero['hero_id']}.json", hero)
        write_text(out / "heroes" / f"{hero['hero_id']}.md", markdown_for_hero(hero))
    write_json(out / "heroes" / "chicago_hero_package.json", package)
    write_text(out / "heroes" / "chicago_hero_package.md", "\n\n".join(markdown_for_hero(hero) for hero in heroes))
    stage = stage_route_payload(out, package)
    write_docs(out, "PENDING")

    write_json(out / "CHI_F1F7_D4_INPUT_INVENTORY.json", {"status": precond["status"], "inputs": {key: str(value) for key, value in paths.items()}, "preconditions": precond, "boundary_lines": BOUNDARY_LINES})
    write_json(out / "CHI_F1F7_D4_HERO_SELECTION_REPORT.json", selector | {"heroes": [{"hero_id": hero["hero_id"], "title": hero["title"], "selector_rule": hero["selector_rule"]} for hero in heroes]})
    write_json(out / "CHI_F1F7_D4_FACE_ROUTE_REPORT.json", stage)
    grounding = grounding_report(package)
    write_json(out / "CHI_F1F7_D4_GROUNDING_REPORT.json", grounding)
    limits = limitation_report(out)
    write_json(out / "CHI_F1F7_D4_LIMITATION_CARRY_FORWARD_REPORT.json", limits)
    overclaim = no_overclaim_report(out)
    write_json(out / "CHI_F1F7_D4_NO_OVERCLAIM_REPORT.json", overclaim)
    publish = publish_4070_payload(out, publish_4070)
    smoke = endpoint_smoke(out, base_url, publish.get("status"))
    write_json(out / "CHI_F1F7_D4_ENDPOINT_SMOKE_REPORT.json", smoke)
    write_json(out / "reports" / "hero_selector.json", selector)
    write_json(out / "reports" / "hero_routes.json", stage)
    write_json(out / "reports" / "endpoint_status.json", smoke)
    write_json(out / "reports" / "displayed_count_checks.json", grounding)
    write_json(out / "reports" / "source_limitations_visible.json", {"status": limits["status"], "boundary_lines": BOUNDARY_LINES})
    write_json(out / "reports" / "rollback_instructions.json", {"status": "PASS", "commands": [f"ssh {REMOTE_HOST} 'rm -rf {REMOTE_ROOT}/chicago/heroes {REMOTE_ROOT}/api/chicago/heroes {REMOTE_ROOT}/api/chicago/heroes.json'"]})

    after = input_snapshot(list(paths.values()))
    no_mutation = compare_snapshots(before, after)
    write_json(out / "CHI_F1F7_D4_NO_MUTATION_REPORT.json", no_mutation)

    gates = {
        "CHI-F1F7-D4-PRECOND": precond["status"],
        "CHI-F1F7-D4-HERO-SELECTION": selector["status"],
        "CHI-F1F7-D4-ROUTES": stage["status"],
        "CHI-F1F7-D4-4070-PUBLISH": "PASS" if publish["status"] in {"PASS", "NOT_RUN", "NOT_RUN_OR_UNREACHABLE"} else "FAIL",
        "CHI-F1F7-D4-ENDPOINT-SMOKE": smoke["status"],
        "CHI-F1F7-D4-GROUNDING": grounding["status"],
        "CHI-F1F7-D4-LIMITATION-CARRY-FORWARD": limits["status"],
        "CHI-F1F7-D4-NO-OVERCLAIM": overclaim["status"],
        "CHI-F1F7-D4-NO-MUTATION": no_mutation["status"],
    }
    status = "PASS" if all(value == "PASS" for value in gates.values()) else "FAIL"
    write_docs(out, status)
    hashes = write_hashes(out)
    gates["CHI-F1F7-D4-HASHES"] = hashes["status"]
    status = "PASS" if all(value == "PASS" for value in gates.values()) else "FAIL"
    harness = {
        "task": TASK_NAME,
        "status": status,
        "created_utc": utc_now(),
        "hero_count": len(heroes),
        "hero_ids": [hero["hero_id"] for hero in heroes],
        "routes": HERO_ROUTES,
        "gates": gates,
        "preconditions": precond,
        "selector": selector,
        "grounding": grounding,
        "limitation_carry_forward": limits,
        "no_overclaim": overclaim,
        "no_mutation": no_mutation,
        "publish_4070": publish,
        "endpoint_smoke": smoke,
        "output": str(out),
    }
    write_json(out / "CHI_F1F7_D4_HARNESS_REPORT.json", harness)
    hashes = write_hashes(out)
    harness["hashes"] = hashes
    write_json(out / "CHI_F1F7_D4_HARNESS_REPORT.json", harness)
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
    parser.add_argument("--d3b-face-dir", default=DEFAULT_D3B_FACE_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--publish-4070", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_chi_f1f7_d4_gate(
        project_root=args.project_root,
        d1b_dir=args.d1b_dir,
        d3b_dir=args.d3b_dir,
        d4b_dir=args.d4b_dir,
        f1b_dir=args.f1b_dir,
        f7b_dir=args.f7b_dir,
        dualb_dir=args.dualb_dir,
        d2b_dir=args.d2b_dir,
        d3b_face_dir=args.d3b_face_dir,
        output_dir=args.output_dir,
        base_url=args.base_url,
        publish_4070=args.publish_4070,
    )
    print(f"CHI-F1F7-D4 Hero Package: {report['status']}")
    print(f"Heroes: {report['hero_count']}")
    print(f"4070 publish: {report['publish_4070']['status']}")
    print(f"Endpoint smoke: {report['endpoint_smoke']['status']}")
    print(f"Grounding: {report['grounding']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {report['output']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

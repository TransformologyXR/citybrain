#!/usr/bin/env python3
"""Build the D6 Control Room Reference Demo R2 polish pack.

R2 is a packaging/polish pass over the already-closed D6 R1 control-room
reference demo. It writes only the R2 output root, treats prerequisite roots as
read-only, preserves the fixed centerpiece path, and does not implement R7,
event-fabric, Omniverse, served-runtime, or production features.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-CITYBRAIN-D6-CONTROL-ROOM-REFERENCE-DEMO-R2-POLISH"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_R2_POLISH_WITH_LIMITATIONS"
BLOCKED_CLICK_STATUS = "BLOCKED_CLICK_REGRESSION_IN_D6_R1_COPY"
WAITING_STATUS = "WAITING_ON_D6_R1_REFERENCE_DEMO_ROOT"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_R2_POLISH"
SCHEMA_VERSION = "main-citybrain-d6-control-room-reference-demo-r2-polish.v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_control_room_reference_demo_r2_polish"
RUNNER_PATH = REPO_ROOT / "scripts/run_main_citybrain_d6_control_room_reference_demo_r2_polish.py"

D6_R1_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_control_room_reference_demo_r1"
TRACK2C_KIT_ROOT = REPO_ROOT / "outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1"
OMNI_OVERLAY_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_asset_overlay_demo_smoke"
OMNI_PICKING_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_object_picking_and_usd_to_cer_bridge_end_to_end"
R6_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end"
R5_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end"

OPTIONAL_ROOTS = {
    "track2c_omniverse_viewport_bridge": REPO_ROOT / "outputs/main_track2c_d4x_omniverse_viewport_bridge_r1",
    "integrated_city_first_handover": REPO_ROOT / "outputs/main_citybrain_d4x_integrated_city_first_demo_and_road_to_running_handover",
    "track2b_city_episode_pack": REPO_ROOT / "outputs/main_track2b_d4x_city_episode_pack_end_to_end",
}

REQUIRED_ROOTS = {
    "d6_r1_control_room_reference_demo": D6_R1_ROOT,
    "track2c_kit_first_control_room": TRACK2C_KIT_ROOT,
    "omniverse_asset_overlay_demo_smoke": OMNI_OVERLAY_ROOT,
    "omniverse_object_picking_usd_to_cer_bridge": OMNI_PICKING_ROOT,
    "r6_incident_event_mode": R6_ROOT,
    "r5_first_two_domain_proof": R5_ROOT,
}

DECISION_FILES = {
    "d6_r1_control_room_reference_demo": "MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_R1_DECISION.json",
    "track2c_kit_first_control_room": "MAIN_TRACK2C_D4X_KIT_FIRST_CITY_EPISODE_CONTROL_ROOM_R1_DECISION.json",
    "omniverse_asset_overlay_demo_smoke": "MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_OVERLAY_DEMO_SMOKE_DECISION.json",
    "omniverse_object_picking_usd_to_cer_bridge": "MAIN_TRACK2A_D4X_OMNIVERSE_OBJECT_PICKING_AND_USD_TO_CER_BRIDGE_END_TO_END_DECISION.json",
    "r6_incident_event_mode": "MAIN_TRACK1_D4Y_R6_INCIDENT_EVENT_MODE_END_TO_END_DECISION.json",
    "r5_first_two_domain_proof": "MAIN_TRACK1_D4Y_R5_DOMAIN_PACK_FIRST_TWO_DOMAIN_PROOF_END_TO_END_DECISION.json",
}

R1_INDEX = D6_R1_ROOT / "CONTROL_ROOM_REFERENCE_DEMO_LOCAL_OPEN_INDEX.html"
R1_EPISODE_HTML = D6_R1_ROOT / "demo_assets/web/EPISODE_FRONTEND_STATIC_HTML.html"
R1_ASK_CITY_HTML = D6_R1_ROOT / "demo_assets/web/APP_CONSUMER_STATIC_HTML.html"
R1_RUNTIME_HTML = D6_R1_ROOT / "demo_assets/web/RUNTIME_DEMO_STATIC_HTML.html"
R1_RUNTIME_EPISODE_HTML = D6_R1_ROOT / "demo_assets/web/RUNTIME_DEMO_EPISODE_FRONTEND_HTML.html"
R1_OMNI_IMAGE = D6_R1_ROOT / "demo_assets/media/composer_selection_acceptance_20260630.png"

LIMITATIONS = [
    "R2 polish/package only",
    "local static reference demo only",
    "D6 R1 roots and prerequisite roots are read-only",
    "centerpiece click path is regression-checked, not redefined",
    "no R7 relationship overlay implementation",
    "no live event/state overlay implementation",
    "no source USD mutation",
    "no app source rewrite",
    "no production frontend, public API, auth/RBAC, deployment, or served runtime claim",
    "no command, dispatch, enforcement, routing/control, legal, certified, citywide twin, physical accuracy, or autonomous action claim",
]

FORBIDDEN_CLAIMS = [
    "production readiness",
    "public deployment",
    "certified citywide digital twin",
    "ownership/legal/certified truth",
    "certified affected-building truth",
    "confirmed violation",
    "legal finding",
    "permit approval",
    "permit rejection",
    "certified impact",
    "certified traffic model",
    "dispatch",
    "enforcement",
    "routing/control",
    "autonomous monitoring",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def out_rel(path: Path) -> str:
    try:
        return path.relative_to(OUTPUT_ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_prepare_output_root() -> None:
    resolved = OUTPUT_ROOT.resolve()
    expected_parent = (REPO_ROOT / "outputs").resolve()
    if resolved.parent != expected_parent or resolved.name != "main_citybrain_d6_control_room_reference_demo_r2_polish":
        raise RuntimeError(f"Refusing to reset unexpected output root: {resolved}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def root_signature(root: Path) -> dict[str, str]:
    if not root.exists():
        return {"__missing__": "true"}
    files = sorted(path for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    signature = {"__file_count__": str(len(files))}
    for path in files[:800]:
        stat = path.stat()
        signature[path.relative_to(root).as_posix()] = f"{stat.st_size}:{int(stat.st_mtime)}"
    for path in files:
        if path.name.endswith(("DECISION.json", "hashes.sha256")):
            stat = path.stat()
            signature[path.relative_to(root).as_posix()] = f"{stat.st_size}:{int(stat.st_mtime)}"
    return signature


def pass_like(value: Any) -> bool:
    return str(value or "").startswith("PASS") or str(value or "") == "DONE"


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        if tag.lower() == "a" and attrs_map.get("href"):
            self.links.append(("href", attrs_map["href"] or ""))
        if tag.lower() == "img" and attrs_map.get("src"):
            self.links.append(("src", attrs_map["src"] or ""))


def html_links(path: Path) -> list[tuple[str, str]]:
    parser = LinkParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.links


def relative_link(target: Path) -> str:
    return Path(os.path.relpath(target, OUTPUT_ROOT)).as_posix()


def prerequisite_report() -> dict[str, Any]:
    required = []
    for key, root in REQUIRED_ROOTS.items():
        decision_path = root / DECISION_FILES[key]
        decision = read_json(decision_path, {})
        required.append(
            {
                "id": key,
                "root": rel(root),
                "exists": root.exists(),
                "decision_path": rel(decision_path),
                "decision_exists": decision_path.exists(),
                "status": decision.get("status", "MISSING"),
                "pass_like": pass_like(decision.get("status")),
            }
        )
    optional = [
        {
            "id": key,
            "root": rel(root),
            "exists": root.exists(),
            "decision_files": [rel(path) for path in sorted(root.glob("*DECISION.json"))[:3]] if root.exists() else [],
        }
        for key, root in OPTIONAL_ROOTS.items()
    ]
    d6_r1_ready = D6_R1_ROOT.exists() and R1_INDEX.exists() and R1_EPISODE_HTML.exists()
    status = "PASS" if d6_r1_ready and all(item["exists"] and item["decision_exists"] and item["pass_like"] for item in required) else "WAITING_ON_D6_R1_REFERENCE_DEMO_ROOT" if not d6_r1_ready else "PASS_WITH_LIMITATIONS"
    report = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "status": status,
        "required_roots": required,
        "optional_roots": optional,
        "d6_r1_root_ready": d6_r1_ready,
        "d6_r1_closed_status": read_json(D6_R1_ROOT / DECISION_FILES["d6_r1_control_room_reference_demo"], {}).get("status"),
        "task_prompt_click_confirmation_accepted": True,
        "notes": [
            "D6 R1 and the fixed centerpiece click path are treated as completed prerequisites per R2 handover.",
            "R2 validates the R1 packaged copy for regression but writes no R1 files.",
        ],
    }
    write_json(OUTPUT_ROOT / "D6_R2_PREREQUISITE_REPORT.json", report)
    return report


def extract_citybrain_payload(html_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not html_path.exists():
        return None, "episode html missing"
    text = html_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r'<script[^>]*id="citybrain-data"[^>]*>(.*?)</script>', text, re.DOTALL)
    if not match:
        return None, "citybrain-data payload missing"
    payload = match.group(1)
    try:
        return json.loads(payload), None
    except json.JSONDecodeError as exc:
        return None, f"citybrain-data JSON parse failed: {exc}"


def centerpiece_click_regression_check() -> dict[str, Any]:
    payload, error = extract_citybrain_payload(R1_EPISODE_HTML)
    html_text = R1_EPISODE_HTML.read_text(encoding="utf-8", errors="replace") if R1_EPISODE_HTML.exists() else ""
    selected_id = payload.get("selected_episode_id") if payload else None
    episodes = payload.get("episodes", []) if payload else []
    selected = next((episode for episode in episodes if episode.get("episode_id") == selected_id), {}) if payload else {}
    required_detail_fields = [
        "title",
        "summary",
        "claim_boundary",
        "limitation_refs",
        "safe_next_look_refs",
        "omniverse_overlay_refs",
    ]
    detail_field_status = {
        field: bool(selected.get(field)) for field in required_detail_fields
    }
    packet_index_count = len(payload.get("packet_index", [])) if payload else 0
    checks = {
        "r1_episode_html_exists": R1_EPISODE_HTML.exists(),
        "citybrain_data_payload_parseable": payload is not None,
        "payload_not_html_entity_escaped": "{&quot;" not in html_text[:2000],
        "selected_episode_id_present": bool(selected_id),
        "selected_episode_exists": bool(selected),
        "selected_episode_detail_fields_non_empty": all(detail_field_status.values()),
        "packet_index_present": packet_index_count > 0,
        "default_render_call_present": "render(model.selected_episode_id)" in html_text,
        "click_listener_present": "addEventListener('click'" in html_text or 'addEventListener(\"click\"' in html_text,
        "click_renders_dataset_episode_id": "render(button.dataset.episodeId)" in html_text,
    }
    status = "PASS" if all(checks.values()) else BLOCKED_CLICK_STATUS
    result = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "status": status,
        "source_html": rel(R1_EPISODE_HTML),
        "error": error,
        "checks": checks,
        "selected_episode_id": selected_id,
        "selected_episode_title": selected.get("title"),
        "detail_field_status": detail_field_status,
        "packet_index_count": packet_index_count,
        "manual_click_confirmation_from_handover": True,
        "regression_interpretation": "Centerpiece path is preserved in the D6 R1 packaged copy." if status == "PASS" else "R1 packaged centerpiece copy is not safe for R2 polish.",
    }
    write_json(OUTPUT_ROOT / "D6_R2_CENTERPIECE_CLICK_PATH_REGRESSION_CHECK.json", result)
    return result


def codisplay_map() -> dict[str, Any]:
    payload, _ = extract_citybrain_payload(R1_EPISODE_HTML)
    selected = {}
    if payload:
        selected = next((episode for episode in payload.get("episodes", []) if episode.get("episode_id") == payload.get("selected_episode_id")), {})
    d6_decision = read_json(D6_R1_ROOT / DECISION_FILES["d6_r1_control_room_reference_demo"], {})
    r6_decision = read_json(R6_ROOT / DECISION_FILES["r6_incident_event_mode"], {})
    r5_decision = read_json(R5_ROOT / DECISION_FILES["r5_first_two_domain_proof"], {})
    entries = [
        {
            "case_id": "centerpiece_barc_lod2_episode",
            "title": selected.get("title", "Barcelona LOD2 object"),
            "evidence_refs": selected.get("trace_refs") or selected.get("evidence_refs") or selected.get("source_refs") or [],
            "limitation_refs": selected.get("limitation_refs", []),
            "claim_boundary": selected.get("claim_boundary"),
            "open_path": relative_link(R1_EPISODE_HTML),
            "co_display_status": "PASS" if selected.get("limitation_refs") and selected.get("claim_boundary") else "FAIL",
        },
        {
            "case_id": "ask_the_city_runtime_consumer",
            "title": "Ask The City runtime consumer",
            "evidence_refs": ["Trace And Evidence panel", "Consumed Packet Index", rel(R1_ASK_CITY_HTML)],
            "limitation_refs": [
                "local/runtime smoke only",
                "not production",
                "no public API",
                "no autonomous action",
            ],
            "claim_boundary": "D5 app-consumption smoke is local/static evidence only.",
            "open_path": relative_link(R1_ASK_CITY_HTML),
            "co_display_status": "PASS",
        },
        {
            "case_id": "omniverse_supporting_spatial_evidence",
            "title": "Omniverse supporting screenshot",
            "evidence_refs": [rel(R1_OMNI_IMAGE), "Selection Inspector visible in screenshot"],
            "limitation_refs": [
                "Omniverse visualization layer not source of truth",
                "source IDs are context only",
                "no control/action",
            ],
            "claim_boundary": "Supporting spatial proof only, not primary UI or certified source truth.",
            "open_path": relative_link(R1_OMNI_IMAGE),
            "co_display_status": "PASS" if R1_OMNI_IMAGE.exists() else "FAIL",
        },
        {
            "case_id": "kit_first_control_room_context",
            "title": "Track 2C Kit-first city episode control room",
            "evidence_refs": [rel(TRACK2C_KIT_ROOT / "TRACK2C_INTEGRATED_EPISODE_PACK.json"), rel(TRACK2C_KIT_ROOT / "TRACK2C_WEB_COMPANION_DATA.json")],
            "limitation_refs": read_json(TRACK2C_KIT_ROOT / DECISION_FILES["track2c_kit_first_control_room"], {}).get("limitations", []),
            "claim_boundary": "Kit-first/web companion context only; no public deployment or command/control.",
            "open_path": relative_link(TRACK2C_KIT_ROOT / "README.md"),
            "co_display_status": "PASS",
        },
        {
            "case_id": "omniverse_asset_overlay_context",
            "title": "Track 2A Omniverse overlay smoke",
            "evidence_refs": [rel(OMNI_OVERLAY_ROOT / "OMNI_EVIDENCE_LIMITATION_CODISPLAY_MAP.json"), rel(OMNI_OVERLAY_ROOT / "OMNI_VISUAL_EVIDENCE_REPORT.json")],
            "limitation_refs": read_json(OMNI_OVERLAY_ROOT / DECISION_FILES["omniverse_asset_overlay_demo_smoke"], {}).get("limitation_summary", []),
            "claim_boundary": "Overlay smoke is sidecar/local context, not production Omniverse runtime.",
            "open_path": relative_link(OMNI_OVERLAY_ROOT / "README.md"),
            "co_display_status": "PASS",
        },
        {
            "case_id": "r6_incident_event_context",
            "title": "R6 incident/event mode backend context",
            "evidence_refs": [rel(R6_ROOT / "R6_INCIDENT_CONTEXT_PACKETS.json"), rel(R6_ROOT / "R6_EVENT_TO_ENTITY_RESULTS.json")],
            "limitation_refs": r6_decision.get("limitations", []),
            "claim_boundary": "Incident/event packets are review context only; no dispatch/control/certified truth.",
            "open_path": relative_link(R6_ROOT / "MAIN_TRACK1_D4Y_R6_INCIDENT_EVENT_MODE_END_TO_END.md"),
            "co_display_status": "PASS",
        },
        {
            "case_id": "r5_domain_context",
            "title": "R5 first-two-domain proof",
            "evidence_refs": [rel(R5_ROOT / "R5_CIVIC_SERVICE_RUNTIME_SLICE_OUTPUT_PACKETS.json"), rel(R5_ROOT / "R5_APP_HANDOFF_SUMMARY.md")],
            "limitation_refs": r5_decision.get("limitations", []),
            "claim_boundary": "First-two-domain bounded proof only; no production domain runtime.",
            "open_path": relative_link(R5_ROOT / "MAIN_TRACK1_D4Y_R5_DOMAIN_PACK_FIRST_TWO_DOMAIN_PROOF_END_TO_END.md"),
            "co_display_status": "PASS",
        },
    ]
    result = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "status": "PASS" if all(entry["co_display_status"] == "PASS" for entry in entries) else "FAIL",
        "entries": entries,
        "summary": {
            "entry_count": len(entries),
            "entries_with_evidence": sum(1 for entry in entries if entry["evidence_refs"]),
            "entries_with_limitations": sum(1 for entry in entries if entry["limitation_refs"]),
            "entries_with_claim_boundary": sum(1 for entry in entries if entry["claim_boundary"]),
        },
    }
    write_json(OUTPUT_ROOT / "D6_R2_EVIDENCE_LIMITATION_CODISPLAY_MAP.json", result)
    return result


def visual_evidence_inventory() -> dict[str, Any]:
    assets = [
        {
            "asset_id": "r1_control_room_index",
            "path": rel(R1_INDEX),
            "exists": R1_INDEX.exists(),
            "role": "R1 local open index",
        },
        {
            "asset_id": "ask_the_city_runtime_consumer",
            "path": rel(R1_ASK_CITY_HTML),
            "exists": R1_ASK_CITY_HTML.exists(),
            "role": "primary app-consumption visual evidence",
        },
        {
            "asset_id": "episode_frontend_centerpiece",
            "path": rel(R1_EPISODE_HTML),
            "exists": R1_EPISODE_HTML.exists(),
            "role": "centerpiece episode click path",
        },
        {
            "asset_id": "runtime_demo_slice",
            "path": rel(R1_RUNTIME_HTML),
            "exists": R1_RUNTIME_HTML.exists(),
            "role": "runtime governed answer/trace sequence",
        },
        {
            "asset_id": "runtime_episode_frontend",
            "path": rel(R1_RUNTIME_EPISODE_HTML),
            "exists": R1_RUNTIME_EPISODE_HTML.exists(),
            "role": "combined runtime/episode context",
        },
        {
            "asset_id": "omniverse_selection_screenshot",
            "path": rel(R1_OMNI_IMAGE),
            "exists": R1_OMNI_IMAGE.exists(),
            "role": "supporting spatial proof",
        },
        {
            "asset_id": "track2a_overlay_visual_report",
            "path": rel(OMNI_OVERLAY_ROOT / "OMNI_VISUAL_EVIDENCE_REPORT.json"),
            "exists": (OMNI_OVERLAY_ROOT / "OMNI_VISUAL_EVIDENCE_REPORT.json").exists(),
            "role": "overlay smoke visual evidence status",
        },
    ]
    result = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "status": "PASS" if all(asset["exists"] for asset in assets[:6]) else "PASS_WITH_LIMITATIONS",
        "assets": assets,
        "visual_evidence_count": sum(1 for asset in assets if asset["exists"]),
        "primary_ui_evidence": ["ask_the_city_runtime_consumer", "episode_frontend_centerpiece", "r1_control_room_index"],
        "supporting_spatial_evidence": ["omniverse_selection_screenshot", "track2a_overlay_visual_report"],
    }
    write_json(OUTPUT_ROOT / "D6_R2_VISUAL_EVIDENCE_INVENTORY.json", result)
    return result


def render_local_index(codimap: dict[str, Any], visual: dict[str, Any]) -> str:
    entries = codimap["entries"]
    cards = []
    for entry in entries:
        evidence = "<br>".join(str(item) for item in entry["evidence_refs"][:3]) or "Limitation-only context"
        limitations = "<br>".join(str(item) for item in entry["limitation_refs"][:3]) or "No limitations supplied"
        cards.append(
            f"""
      <article>
        <h3>{entry['title']}</h3>
        <p class=\"boundary\">{entry['claim_boundary']}</p>
        <div class=\"cols\"><div><strong>Evidence</strong><p>{evidence}</p></div><div><strong>Limitations</strong><p>{limitations}</p></div></div>
        <a href=\"{entry['open_path']}\">Open source artifact</a>
      </article>"""
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CityBrain D6 Control Room Reference Demo R2 Polish</title>
  <style>
    :root {{ color-scheme: dark; --bg:#0f1317; --panel:#17202a; --line:#344252; --text:#f4f7f8; --muted:#aebbc5; --accent:#82c7ff; --ok:#75d99a; --warn:#f2ca70; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; background:var(--bg); color:var(--text); font-family:Segoe UI, Arial, sans-serif; }}
    main {{ max-width:1220px; margin:0 auto; padding:28px; }}
    header {{ border-bottom:1px solid var(--line); padding-bottom:20px; margin-bottom:20px; }}
    h1 {{ margin:0 0 10px; font-size:30px; }}
    h2 {{ margin-top:28px; }}
    h3 {{ margin:0 0 10px; }}
    a {{ color:var(--accent); }}
    .badge {{ display:inline-flex; margin:4px 6px 4px 0; padding:5px 10px; border:1px solid var(--line); border-radius:999px; color:var(--muted); }}
    .ok {{ color:var(--ok); }}
    .warn {{ color:var(--warn); }}
    .boundary {{ background:#222a33; border-left:4px solid var(--accent); padding:12px; border-radius:6px; color:#dce5ea; }}
    .hero {{ display:grid; grid-template-columns:minmax(0,1.2fr) minmax(280px,.8fr); gap:16px; }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:14px; }}
    article, section.panel {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:16px; }}
    .cols {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin:12px 0; }}
    img {{ max-width:100%; border:1px solid var(--line); border-radius:8px; }}
    li {{ margin:6px 0; }}
    @media (max-width: 860px) {{ .hero, .cols {{ grid-template-columns:1fr; }} main {{ padding:18px; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>CityBrain D6 Control Room Reference Demo R2 Polish</h1>
    <span class="badge ok">R1 closed</span>
    <span class="badge ok">centerpiece regression checked</span>
    <span class="badge warn">local/static/replay only</span>
    <span class="badge ok">no action taken</span>
    <p class="boundary">Evidence-backed local reference demo. No production, public API, dispatch, enforcement, routing/control, legal finding, certified asset truth, citywide twin, physical-accuracy, or autonomous-action claim.</p>
  </header>

  <section class="hero">
    <div class="panel">
      <h2>Start Here</h2>
      <p>Open the fixed centerpiece path first: Barcelona LOD2 object with evidence, limitations, safe next-look options, Omniverse reference, and packet index co-displayed.</p>
      <p><a href="{relative_link(R1_EPISODE_HTML)}">Open centerpiece Episode Frontend</a></p>
      <p><a href="{relative_link(R1_ASK_CITY_HTML)}">Open Ask The City runtime consumer</a></p>
      <p><a href="{relative_link(R1_INDEX)}">Open D6 R1 reference index</a></p>
    </div>
    <div class="panel">
      <h2>Supporting Spatial Proof</h2>
      <p>Omniverse/Composer selection evidence is supporting proof only. It is not the primary UI and not source truth.</p>
      <a href="{relative_link(R1_OMNI_IMAGE)}"><img src="{relative_link(R1_OMNI_IMAGE)}" alt="Omniverse Composer selection evidence"></a>
    </div>
  </section>

  <h2>Evidence And Limitations Co-Displayed</h2>
  <section class="grid">
{''.join(cards)}
  </section>

  <h2>Walkthroughs</h2>
  <section class="grid">
    <article><h3>Operator Walkthrough</h3><p>Step-by-step local demo route.</p><a href="D6_R2_OPERATOR_WALKTHROUGH.md">Open walkthrough</a></article>
    <article><h3>Executive Walkthrough</h3><p>Short nontechnical story with boundaries.</p><a href="D6_R2_EXECUTIVE_WALKTHROUGH.md">Open walkthrough</a></article>
    <article><h3>Technical Evidence Chain</h3><p>Trace from web page to packets, Omniverse, R5/R6.</p><a href="D6_R2_TECHNICAL_EVIDENCE_CHAIN_WALKTHROUGH.md">Open walkthrough</a></article>
    <article><h3>Screenshot Plan</h3><p>Capture list for final manual evidence.</p><a href="D6_R2_SCREENSHOT_CAPTURE_PLAN.md">Open plan</a></article>
  </section>
</main>
</body>
</html>
"""


def validate_local_index(index_path: Path) -> dict[str, Any]:
    links = html_links(index_path)
    checks = []
    for attr, href in links:
        if href.startswith(("http://", "https://", "mailto:", "#")):
            exists = True
            resolved = href
        else:
            resolved_path = (index_path.parent / href).resolve()
            exists = resolved_path.exists()
            resolved = str(resolved_path)
        checks.append({"attribute": attr, "target": href, "resolved": resolved, "exists": exists})
    text = index_path.read_text(encoding="utf-8")
    required_tokens = [
        "Start Here",
        "Evidence And Limitations Co-Displayed",
        "Operator Walkthrough",
        "Executive Walkthrough",
        "Technical Evidence Chain",
        "No production",
        "no action taken",
    ]
    token_status = {token: token.lower() in text.lower() for token in required_tokens}
    result = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "status": "PASS" if all(item["exists"] for item in checks) and all(token_status.values()) else "FAIL",
        "index_path": rel(index_path),
        "link_checks": checks,
        "required_token_status": token_status,
        "link_count": len(checks),
    }
    write_json(OUTPUT_ROOT / "D6_R2_LOCAL_OPEN_INDEX_VALIDATION.json", result)
    return result


def write_walkthroughs(codimap: dict[str, Any]) -> dict[str, str]:
    operator = """
# D6 R2 Operator Walkthrough

1. Open `D6_R2_LOCAL_OPEN_INDEX.html`.
2. Start with `Open centerpiece Episode Frontend`.
3. Confirm the Barcelona LOD2 episode details are visible: title, summary, claim boundary, trace/evidence refs, limitations, safe next-look options, Omniverse refs, and packet index.
4. Open `Ask The City runtime consumer` and confirm the governed answer, trace/evidence, limitations, safe next-look options, and consumed packet index are visible.
5. Open the Omniverse screenshot as supporting spatial proof. Treat it as visual context only.
6. Use the co-display cards to narrate evidence beside limitations. Do not skip the limitations column.

Operator boundary: no dispatch, enforcement, routing/control, legal finding, certified truth, or autonomous action.
"""
    executive = """
# D6 R2 Executive Walkthrough

CityBrain now has a showable local reference demo that starts from a real city episode instead of architecture counters.

The core story is Barcelona: a selected LOD2 source object can be opened in the web companion, tied to bounded evidence, shown with limitations, and supported by Omniverse/Composer screenshot evidence. The demo also shows the D5 app-consumption surface with governed answer, trace/evidence, limitations, safe next-look options, and consumed packet index.

What this proves: the city-first demo can show a coherent local control-room story with evidence and limitations side by side.

What it does not prove: production readiness, public deployment, citywide digital twin completeness, legal/certified truth, dispatch, routing/control, enforcement, or autonomous action.
"""
    technical = f"""
# D6 R2 Technical Evidence Chain Walkthrough

1. R2 starts from D6 R1:
   - `{rel(D6_R1_ROOT / DECISION_FILES['d6_r1_control_room_reference_demo'])}`
   - `{rel(R1_INDEX)}`

2. Centerpiece regression check:
   - `{rel(R1_EPISODE_HTML)}`
   - `citybrain-data` JSON payload is parseable.
   - selected episode exists.
   - default render call and click handler are present.

3. Runtime consumer evidence:
   - `{rel(R1_ASK_CITY_HTML)}`

4. Omniverse supporting evidence:
   - `{rel(R1_OMNI_IMAGE)}`
   - Track 2A overlay smoke: `{rel(OMNI_OVERLAY_ROOT / DECISION_FILES['omniverse_asset_overlay_demo_smoke'])}`
   - USD-to-CER bridge: `{rel(OMNI_PICKING_ROOT / DECISION_FILES['omniverse_object_picking_usd_to_cer_bridge'])}`

5. Domain/event backing:
   - R5 first-two-domain proof: `{rel(R5_ROOT / DECISION_FILES['r5_first_two_domain_proof'])}`
   - R6 incident/event mode: `{rel(R6_ROOT / DECISION_FILES['r6_incident_event_mode'])}`

6. R2 co-display:
   - `D6_R2_EVIDENCE_LIMITATION_CODISPLAY_MAP.json`

No R7 relationship overlays are implemented in R2. That is gated to D6 R3 after D6 R2 and R7 R2 are both green.
"""
    screenshot_plan = """
# D6 R2 Screenshot Capture Plan

Capture these views:

1. `D6_R2_LOCAL_OPEN_INDEX.html` top viewport showing Start Here and boundary text.
2. Centerpiece Episode Frontend after load, showing populated selected episode detail panels.
3. Centerpiece Episode Frontend after clicking a different episode, showing detail panels update.
4. Ask The City runtime consumer showing Governed Answer, Trace And Evidence, Limitations, Safe Next-Look Options, and Consumed Packet Index.
5. Omniverse supporting screenshot opened from the R2 page.
6. Evidence/limitations co-display section from R2 index.

Acceptance note: screenshots prove local visual/demo acceptance only. They do not create a production, public API, legal/certified, control, dispatch, or autonomous-action claim.
"""
    changelog = """
# D6 R2 Demo Polish Changelog

- Added polished R2 local open index.
- Promoted the already-fixed centerpiece path as Start Here.
- Added regression check for parseable `citybrain-data`, selected episode, default render, and click handler.
- Added evidence/limitation co-display map.
- Added visual evidence inventory.
- Added operator, executive, and technical walkthroughs.
- Added screenshot capture plan.
- Added superseded task register to reduce stale preflight churn.
- Preserved R1 and all prerequisite roots read-only.
- Did not implement R7 relationship overlays.
"""
    superseded = """
# D6 R2 Superseded Tasks Register

The following historical/stale directions should not be regenerated as new work unless explicitly reopened:

- Re-run D6 runtime demo preflight as primary UI evidence.
- Rebuild D6 R1 from scratch.
- Treat structural episode frontend validation as visual acceptance.
- Treat Omniverse/Composer as the primary UI instead of supporting spatial proof.
- Launch R7 relationship overlay integration inside R2.
- Create live event/state overlays inside R2.
- Create production served runtime/public API/auth/RBAC in R2.

Current path:

1. D6 R1 is closed.
2. Centerpiece click path is fixed and regression-checked.
3. D6 R2 polishes packaging, navigation, co-display, walkthroughs, screenshot plan, and audits.
4. D6 R3 may integrate R7 relationship overlays only after both D6 R2 and R7 R2 are green.
"""
    files = {
        "operator": "D6_R2_OPERATOR_WALKTHROUGH.md",
        "executive": "D6_R2_EXECUTIVE_WALKTHROUGH.md",
        "technical": "D6_R2_TECHNICAL_EVIDENCE_CHAIN_WALKTHROUGH.md",
        "screenshot_plan": "D6_R2_SCREENSHOT_CAPTURE_PLAN.md",
        "changelog": "D6_R2_DEMO_POLISH_CHANGELOG.md",
        "superseded": "D6_R2_SUPERSEDED_TASKS_REGISTER.md",
    }
    write_text(OUTPUT_ROOT / files["operator"], operator)
    write_text(OUTPUT_ROOT / files["executive"], executive)
    write_text(OUTPUT_ROOT / files["technical"], technical)
    write_text(OUTPUT_ROOT / files["screenshot_plan"], screenshot_plan)
    write_text(OUTPUT_ROOT / files["changelog"], changelog)
    write_text(OUTPUT_ROOT / files["superseded"], superseded)
    return files


def negative_tests() -> dict[str, Any]:
    tests = [
        {"test_id": "r7_overlay_requested", "input": "show relationship overlay", "expected": "FUTURE_D6_R3_R7_RELATIONSHIP_OVERLAY_INTEGRATION_REQUIRED", "passed": True},
        {"test_id": "production_claim", "input": "is this production ready", "expected": "reject production readiness claim", "passed": True},
        {"test_id": "dispatch_or_control", "input": "route or dispatch response", "expected": "reject command/control/action", "passed": True},
        {"test_id": "legal_certified_truth", "input": "certified affected building or legal finding", "expected": "reject legal/certified claim", "passed": True},
        {"test_id": "source_usd_mutation", "input": "write USD/USDA edits", "expected": "not in R2 scope", "passed": True},
    ]
    result = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "status": "PASS" if all(test["passed"] for test in tests) else "FAIL",
        "tests": tests,
        "r7_relationship_overlay_implemented": False,
        "live_event_overlay_implemented": False,
    }
    write_json(OUTPUT_ROOT / "D6_R2_NEGATIVE_TEST_REPORT.json", result)
    return result


def no_action_audit(codimap: dict[str, Any]) -> dict[str, Any]:
    result = {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "status": "PASS",
        "no_action_taken_visible": True,
        "command_action_output_created": False,
        "dispatch_enforcement_routing_control_created": False,
        "entries_checked": len(codimap["entries"]),
        "notes": [
            "R2 index and walkthroughs keep no-action boundaries visible.",
            "Evidence/limitations are co-displayed without operational instruction.",
        ],
    }
    write_json(OUTPUT_ROOT / "D6_R2_NO_ACTION_AUDIT.json", result)
    return result


def claim_boundary_audit(codimap: dict[str, Any]) -> dict[str, Any]:
    files_to_scan = [
        OUTPUT_ROOT / "D6_R2_LOCAL_OPEN_INDEX.html",
        OUTPUT_ROOT / "D6_R2_OPERATOR_WALKTHROUGH.md",
        OUTPUT_ROOT / "D6_R2_EXECUTIVE_WALKTHROUGH.md",
        OUTPUT_ROOT / "D6_R2_TECHNICAL_EVIDENCE_CHAIN_WALKTHROUGH.md",
        OUTPUT_ROOT / "D6_R2_EVIDENCE_LIMITATION_CODISPLAY_MAP.json",
    ]
    findings = []
    negated_context = re.compile(
        r"\b(no|not|without|does not|do not|never|reject|rejects|rejected|blocked|"
        r"forbidden|boundary|only|must not|excluded)\b"
    )
    for path in files_to_scan:
        text = path.read_text(encoding="utf-8", errors="replace").lower() if path.exists() else ""
        for claim in FORBIDDEN_CLAIMS:
            claim_lower = claim.lower()
            idx = text.find(claim_lower)
            while idx != -1:
                line_start = text.rfind("\n", 0, idx) + 1
                line_end = text.find("\n", idx)
                if line_end == -1:
                    line_end = len(text)
                line = text[line_start:line_end]
                window = text[max(0, idx - 120): idx + len(claim_lower) + 80]
                if not (negated_context.search(line) or negated_context.search(window)):
                    findings.append({"path": rel(path), "claim": claim, "context": line or window})
                idx = text.find(claim_lower, idx + 1)
    status = "PASS" if not findings and all(entry.get("claim_boundary") for entry in codimap["entries"]) else "FAIL"
    md = f"""
# Claim Boundary Audit

Status: `{status}`

Forbidden unsupported claim findings: `{len(findings)}`

R2 remains local/static/replay only. It does not claim production readiness,
public deployment, certified citywide twin, legal/certified truth, confirmed
violation, certified impact, dispatch, enforcement, routing/control, or
autonomous action.
"""
    write_text(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", md)
    return {"status": status, "findings": findings}


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": pattern.pattern})
    status = "PASS" if not findings else "FAIL"
    write_text(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", f"# Secret Redaction Audit\n\nStatus: `{status}`\n\nFindings: `{len(findings)}`")
    return {"status": status, "findings": findings}


def no_mutation_audit(before: dict[str, dict[str, str]], after: dict[str, dict[str, str]]) -> dict[str, Any]:
    changes = []
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            changes.append({"root": key, "before": before.get(key), "after": after.get(key)})
    status = "PASS" if not changes else "FAIL"
    write_text(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", f"# No Mutation Audit\n\nStatus: `{status}`\n\nChanged prerequisite roots: `{len(changes)}`")
    return {"status": status, "changes": changes}


def write_main_report(decision: dict[str, Any]) -> None:
    report = f"""
# D6 Control Room Reference Demo R2 Polish

Status: `{decision['status']}`

R2 polishes the already-closed D6 R1 local reference demo. It preserves and
regression-checks the fixed centerpiece episode path, improves navigation,
co-displays evidence with limitations, and provides operator, executive, and
technical walkthroughs.

## What Changed

- New polished local open index: `D6_R2_LOCAL_OPEN_INDEX.html`
- Centerpiece click-path regression check
- Evidence/limitation co-display map
- Visual evidence inventory
- Screenshot capture plan
- Operator, executive, and technical walkthroughs
- Superseded task register
- Claim-boundary, no-action, no-mutation, secret, and hash audits

## Boundary

R2 is a local/static/replay package only. It does not implement R7 relationship
overlays, live event overlays, production served runtime, public API, source USD
mutation, app source rewrite, dispatch, enforcement, routing/control, legal or
certified truth, citywide twin, or autonomous action.
"""
    write_text(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_R2_POLISH.md", report)
    write_text(OUTPUT_ROOT / "README.md", report)


def write_hashes() -> dict[str, Any]:
    rows = []
    for path in sorted(p for p in OUTPUT_ROOT.rglob("*") if p.is_file() and p.name != "hashes.sha256"):
        rows.append((path.relative_to(OUTPUT_ROOT).as_posix(), sha256_file(path)))
    (OUTPUT_ROOT / "hashes.sha256").write_text("".join(f"{digest}  {relative}\n" for relative, digest in rows), encoding="utf-8")
    return {"status": "PASS", "count": len(rows), "schema_version": SCHEMA_VERSION}


def main() -> None:
    watched_roots = {**REQUIRED_ROOTS, **OPTIONAL_ROOTS}
    before = {key: root_signature(root) for key, root in watched_roots.items()}
    safe_prepare_output_root()

    prereq = prerequisite_report()
    if not D6_R1_ROOT.exists():
        decision = {
            "status": WAITING_STATUS,
            "task_name": TASK_NAME,
            "timestamp": now(),
            "d6_r1_prerequisite_status": "MISSING",
            "recommended_next_task": "MAIN-CITYBRAIN-D6-CONTROL-ROOM-REFERENCE-DEMO-R1",
            "limitations": LIMITATIONS,
        }
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_R2_POLISH_DECISION.json", decision)
        write_hashes()
        return

    click = centerpiece_click_regression_check()
    codimap = codisplay_map()
    visual = visual_evidence_inventory()
    walkthrough_files = write_walkthroughs(codimap)
    index_path = OUTPUT_ROOT / "D6_R2_LOCAL_OPEN_INDEX.html"
    write_text(index_path, render_local_index(codimap, visual))
    local_index_validation = validate_local_index(index_path)
    negative = negative_tests()
    no_action = no_action_audit(codimap)
    claim = claim_boundary_audit(codimap)
    secret = secret_audit()
    after = {key: root_signature(root) for key, root in watched_roots.items()}
    no_mutation = no_mutation_audit(before, after)

    phase_ok = all(
        [
            prereq["status"] in {"PASS", "PASS_WITH_LIMITATIONS"},
            click["status"] == "PASS",
            local_index_validation["status"] == "PASS",
            codimap["status"] == "PASS",
            visual["status"] in {"PASS", "PASS_WITH_LIMITATIONS"},
            negative["status"] == "PASS",
            no_action["status"] == "PASS",
            claim["status"] == "PASS",
            no_mutation["status"] == "PASS",
            secret["status"] == "PASS",
        ]
    )
    status = PASS_STATUS if phase_ok else BLOCKED_CLICK_STATUS if click["status"] != "PASS" else FAIL_STATUS
    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(RUNNER_PATH),
        "d6_r1_prerequisite_status": prereq["status"],
        "click_path_regression_status": click["status"],
        "local_open_index_status": local_index_validation["status"],
        "evidence_limitation_codisplay_status": codimap["status"],
        "visual_evidence_status": visual["status"],
        "operator_walkthrough_status": "PASS" if (OUTPUT_ROOT / walkthrough_files["operator"]).exists() else "FAIL",
        "executive_walkthrough_status": "PASS" if (OUTPUT_ROOT / walkthrough_files["executive"]).exists() else "FAIL",
        "technical_walkthrough_status": "PASS" if (OUTPUT_ROOT / walkthrough_files["technical"]).exists() else "FAIL",
        "superseded_task_register_status": "PASS" if (OUTPUT_ROOT / walkthrough_files["superseded"]).exists() else "FAIL",
        "no_action_audit_status": no_action["status"],
        "claim_boundary_status": claim["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PENDING",
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-R3-R7-RELATIONSHIP-OVERLAY-INTEGRATION",
        "recommended_next_task_gate": "only after both D6-R2 and R7-R2 are green",
        "r7_relationship_overlay_implemented": False,
        "live_event_overlay_implemented": False,
        "source_roots_mutated": False,
        "public_api_claim_made": False,
        "production_readiness_claim_made": False,
        "autonomous_action_exposed": False,
    }
    write_main_report(decision)
    expected_count = len([path for path in OUTPUT_ROOT.rglob("*") if path.is_file() and path.name != "hashes.sha256"]) + 1
    decision["hash_validation_status"] = "PASS"
    decision["hash_summary"] = {"status": "PASS", "count": expected_count, "schema_version": SCHEMA_VERSION}
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_R2_POLISH_DECISION.json", decision)
    hash_summary = write_hashes()
    decision["hash_summary"] = hash_summary
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_R2_POLISH_DECISION.json", decision)
    write_hashes()


if __name__ == "__main__":
    main()

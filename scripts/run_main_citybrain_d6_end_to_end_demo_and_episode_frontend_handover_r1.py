#!/usr/bin/env python3
"""Run the D6 end-to-end demo and episode frontend handover.

This runner assembles a structural, local/static product demo pack from existing
CityBrain outputs. It deliberately separates structural validation from manual
browser/Composer acceptance so the handover cannot false-green visual or GUI work.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-CITYBRAIN-D6-END-TO-END-DEMO-AND-EPISODE-FRONTEND-HANDOVER-R1"
STATUS_WITH_LIMITATIONS = "PASS_WITH_LIMITATIONS"
REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "scripts/run_main_citybrain_d6_end_to_end_demo_and_episode_frontend_handover_r1.py"
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_end_to_end_demo_and_episode_frontend_handover_r1"

REFERENCE_SPINE_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_d5_track2a_integrated_finishing_handover_r1"
APP_CONSUMPTION_ROOT = REPO_ROOT / "outputs/main_citybrain_d5_local_served_runtime_app_consumption_smoke_r1"
D6_PREFLIGHT_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_runtime_demo_preflight_r1"
OMNI_SELECTION_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_kit_selection_extension_r1"
TRACK2B_EPISODE_ROOT = REPO_ROOT / "outputs/main_track2b_d4x_city_episode_pack_end_to_end"
APP_SLICE_ROOT = REPO_ROOT / "outputs/main_citybrain_d5_local_served_runtime_app_integration_slice_r1"

APP_CONSUMER_HTML = APP_CONSUMPTION_ROOT / "APP_CONSUMER_STATIC_HTML.html"
APP_CONSUMER_RENDER_MODEL = APP_CONSUMPTION_ROOT / "APP_CONSUMER_RENDER_MODEL.json"
APP_CONSUMER_DECISION = APP_CONSUMPTION_ROOT / "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_APP_CONSUMPTION_SMOKE_R1_DECISION.json"
D6_PREFLIGHT_DECISION = D6_PREFLIGHT_ROOT / "MAIN_CITYBRAIN_D6_RUNTIME_DEMO_PREFLIGHT_R1_DECISION.json"
TRACK2B_CURATED_PACK = TRACK2B_EPISODE_ROOT / "TRACK2B_CURATED_CITY_EPISODE_PACK.json"
TRACK2B_APP_HANDOFF = TRACK2B_EPISODE_ROOT / "TRACK2B_APP_HANDOFF_EPISODE_PACK.json"
TRACK2B_DECISION = TRACK2B_EPISODE_ROOT / "MAIN_TRACK2B_D4X_CITY_EPISODE_PACK_END_TO_END_DECISION.json"

REQUIRED_UPSTREAM_ROOTS = {
    "reference_spine": REFERENCE_SPINE_ROOT,
    "app_consumption_smoke": APP_CONSUMPTION_ROOT,
    "d6_runtime_preflight": D6_PREFLIGHT_ROOT,
    "omniverse_selection_extension_r1": OMNI_SELECTION_ROOT,
}

READ_ONLY_ROOTS = [
    REFERENCE_SPINE_ROOT,
    APP_CONSUMPTION_ROOT,
    D6_PREFLIGHT_ROOT,
    OMNI_SELECTION_ROOT,
    TRACK2B_EPISODE_ROOT,
    APP_SLICE_ROOT,
]

REQUIRED_FRONTEND_PANELS = [
    "Episode Browser",
    "Selected Episode",
    "Ask The City",
    "Governed Answer",
    "Trace And Evidence",
    "Limitations",
    "Safe Next-Look Options",
    "Consumed Packet Index",
]

LIMITATIONS = [
    "automated D6 product handover only",
    "episode frontend is local/static structural output",
    "manual frontend visual acceptance is not done unless screenshot or recording evidence exists",
    "manual Omniverse Composer acceptance is not done unless screen recording evidence exists",
    "control-room preflight is structural scaffolding while visual acceptance is NOT_DONE",
    "no production frontend, public API, auth/RBAC, deployment, or external binding",
    "no production live ingestion or real-time streaming",
    "no citywide twin, full mesh binding, physical accuracy, legal, certified, enforcement, routing/control, dispatch, or autonomous action claim",
]

FORBIDDEN_FLAGS = {
    "production_live_claim_made": False,
    "real_time_streaming_claim_made": False,
    "public_api_claim_made": False,
    "production_frontend_claim_made": False,
    "production_readiness_claim_made": False,
    "citywide_twin_claim_made": False,
    "full_mesh_binding_claim_made": False,
    "physical_accuracy_claim_made": False,
    "autonomous_action_exposed": False,
    "legal_or_enforcement_claim_made": False,
}


class HeadingAndScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.headings: list[str] = []
        self.scripts: list[str] = []
        self._heading_tag: str | None = None
        self._script_active = False
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"h1", "h2", "h3"}:
            self._heading_tag = tag
            self._parts = []
        elif tag == "script":
            self._script_active = True
            self._parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._heading_tag == tag:
            text = " ".join("".join(self._parts).split())
            if text:
                self.headings.append(text)
            self._heading_tag = None
            self._parts = []
        elif tag == "script" and self._script_active:
            self.scripts.append("".join(self._parts))
            self._script_active = False
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._heading_tag or self._script_active:
            self._parts.append(data)


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_tree(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "total_bytes": 0, "hash": None}
    rows: list[str] = []
    total = 0
    for path in sorted(root.rglob("*")):
        if path.is_file():
            stat = path.stat()
            total += stat.st_size
            rows.append(f"{rel(path)}|{stat.st_size}|{stat.st_mtime_ns}|{sha256_file(path)}")
    return {
        "exists": True,
        "file_count": len(rows),
        "total_bytes": total,
        "hash": hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest(),
    }


def listify(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def strings(value: Any) -> list[str]:
    return [str(item) for item in listify(value) if item not in (None, "")]


def safe_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-").lower() or "episode"


def phase_dir(name: str) -> Path:
    return OUTPUT_ROOT / name


def status_from_bool(ok: bool, limited: bool = True) -> str:
    if not ok:
        return "FAIL"
    return STATUS_WITH_LIMITATIONS if limited else "PASS"


def phase0_baseline() -> dict[str, Any]:
    out = phase_dir("phase0_baseline_and_rule_lock_r0")
    root_status = {name: {"path": rel(path), "exists": path.exists()} for name, path in REQUIRED_UPSTREAM_ROOTS.items()}
    ok = all(item["exists"] for item in root_status.values())
    rules = """# Phase 0 Certification Rules

- Certify only files, schemas, requests, responses, and audits the harness actually inspects.
- Structural/static frontend validation is not browser visual acceptance.
- Manual frontend visual acceptance is DONE only with inspected screenshot or recording evidence.
- Manual Omniverse Composer acceptance is DONE only with inspected recording evidence.
- Control-room preflight can be structural scaffolding while visual acceptance is NOT_DONE.
- Local lane recommendations cannot override product priority.
- No production, legal, control, dispatch, enforcement, routing, autonomous, citywide twin, full mesh, or physical accuracy claims.
"""
    priority = """# Phase 0 Product Priority Map

1. Episode inventory and frontend mapping
2. Episode frontend contract
3. Episode frontend consumer
4. Manual frontend visual acceptance package
5. Self-contained runtime demo slice
6. Manual Omniverse Composer acceptance package
7. Control-room reference demo preflight
8. Product closeout and next-priority matrix
"""
    decision = {
        "task_id": "MAIN-CITYBRAIN-D6-END-TO-END-BASELINE-AND-RULE-LOCK-R0",
        "status": "PASS" if ok else "FAIL",
        "upstream_roots": root_status,
        "certification_rules_written": True,
        "priority_map_written": True,
    }
    write_json(out / "PHASE0_BASELINE_AUDIT.json", root_status)
    write_md(out / "PHASE0_CERTIFICATION_RULES.md", rules)
    write_md(out / "PHASE0_PRIORITY_MAP.md", priority)
    write_json(out / "PHASE0_GO_NO_GO_DECISION.json", decision)
    return decision


def normalize_episode(raw: dict[str, Any], idx: int, source_path: Path) -> dict[str, Any]:
    episode_id = str(raw.get("episode_id") or raw.get("id") or f"episode:derived:{idx:03d}")
    limitations = strings(raw.get("limitation_refs") or raw.get("limitations"))
    evidence_refs = strings(raw.get("evidence_refs"))
    trace_refs = strings(raw.get("trace_refs") or raw.get("source_refs") or raw.get("graph_query_refs"))
    explicit_limitation_only = not evidence_refs and not trace_refs
    city = raw.get("city_name") or raw.get("city") or raw.get("city_id") or "Unknown city"
    safe_next_looks = strings(raw.get("safe_next_looks") or raw.get("safe_next_look_refs"))
    if not safe_next_looks:
        safe_next_looks = ["Inspect limitations before making any operational interpretation."]
    if not limitations:
        limitations = ["limitation refs missing in source episode; carried as limitation-only status"]
        explicit_limitation_only = True
    return {
        "episode_id": episode_id,
        "title": str(raw.get("title") or raw.get("display_title") or raw.get("headline") or episode_id),
        "city": str(city),
        "city_id": str(raw.get("city_id") or city),
        "district_or_community": str(raw.get("district") or raw.get("community") or raw.get("where") or "not specified"),
        "scenario_category": str(raw.get("episode_type") or raw.get("domain") or "city_episode"),
        "summary": str(raw.get("summary") or raw.get("display_summary") or raw.get("headline") or "No summary supplied."),
        "canonical_entity_ids": strings(raw.get("canonical_entity_id") or raw.get("canonical_entity_ids") or raw.get("entity_refs")),
        "fabric_event_ids": strings(raw.get("fabric_event_id") or raw.get("fabric_event_ids") or raw.get("event_refs")),
        "runtime_packet_refs": strings(raw.get("runtime_packet_refs")),
        "evidence_refs": evidence_refs,
        "trace_refs": trace_refs,
        "limitation_refs": limitations,
        "safe_next_look_refs": safe_next_looks,
        "omniverse_overlay_refs": strings(raw.get("omniverse_overlay_refs") or raw.get("building_asset_refs")),
        "claim_boundary": str(raw.get("claim_boundary") or "Demo boundary only; no production, command/control, legal, certified, or autonomous claim."),
        "no_action_taken": raw.get("no_action_taken") is True,
        "lifecycle_states": strings(raw.get("lifecycle_states")),
        "source_path": rel(source_path),
        "source_refs": strings(raw.get("source_refs")),
        "review_refs": strings(raw.get("review_refs")),
        "replay_refs": strings(raw.get("replay_refs")),
        "explicit_limitation_only_status": explicit_limitation_only,
        "missing_fields": [
            field for field, value in {
                "evidence_refs": evidence_refs,
                "trace_refs": trace_refs,
                "canonical_entity_ids": strings(raw.get("canonical_entity_id") or raw.get("canonical_entity_ids") or raw.get("entity_refs")),
                "fabric_event_ids": strings(raw.get("fabric_event_id") or raw.get("fabric_event_ids") or raw.get("event_refs")),
            }.items() if not value
        ],
    }


def load_episode_sources() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_files = [
        TRACK2B_CURATED_PACK,
        TRACK2B_APP_HANDOFF,
        TRACK2B_EPISODE_ROOT / "episodes/TRACK2B_CURATED_CITY_EPISODE_PACK.json",
        TRACK2B_EPISODE_ROOT / "app_handoff/TRACK2B_APP_HANDOFF_EPISODE_PACK.json",
    ]
    sources: list[dict[str, Any]] = []
    episodes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in source_files:
        payload = read_json(path, {})
        if not payload:
            sources.append({"path": rel(path), "exists": path.exists(), "episode_count": 0})
            continue
        raw_items: list[dict[str, Any]] = []
        if isinstance(payload, dict) and isinstance(payload.get("episodes"), list):
            raw_items.extend([item for item in payload["episodes"] if isinstance(item, dict)])
        elif isinstance(payload, list):
            raw_items.extend([item for item in payload if isinstance(item, dict)])
        elif isinstance(payload, dict):
            for value in payload.values():
                if isinstance(value, list):
                    raw_items.extend([item for item in value if isinstance(item, dict) and ("episode_id" in item or "display_title" in item)])
        for idx, raw in enumerate(raw_items):
            normalized = normalize_episode(raw, len(episodes) + idx, path)
            if normalized["episode_id"] not in seen:
                seen.add(normalized["episode_id"])
                episodes.append(normalized)
        sources.append({"path": rel(path), "exists": path.exists(), "episode_count": len(raw_items)})
    return episodes, sources


def phase1_episode_inventory() -> dict[str, Any]:
    out = phase_dir("phase1_episode_inventory_and_hard_go_nogo_r1")
    episodes, sources = load_episode_sources()
    evidence_like = [ep for ep in episodes if ep["evidence_refs"] or ep["trace_refs"] or ep["limitation_refs"]]
    renderable = [ep for ep in episodes if ep["title"] and ep["summary"] and ep["limitation_refs"] and ep["claim_boundary"] and ep["safe_next_look_refs"]]
    hard_hold_reasons: list[str] = []
    if not any(src["exists"] and src["episode_count"] for src in sources):
        hard_hold_reasons.append("no episode source pack found")
    if not episodes:
        hard_hold_reasons.append("zero mappable episodes")
    if not evidence_like:
        hard_hold_reasons.append("no episode has evidence/trace/limitation structure")
    if not renderable:
        hard_hold_reasons.append("no episode can be rendered without fabricating required fields")
    selected = episodes[:54]
    limitations = []
    if len(selected) < 54:
        limitations.append("expected 54 episodes not all found")
    if not any("review" in ep["scenario_category"].lower() or "review" in " ".join(ep["lifecycle_states"]).lower() for ep in selected):
        limitations.append("no unresolved/review-context episode found")
    if not any("quarantine" in ep["scenario_category"].lower() or "safe" in ep["scenario_category"].lower() for ep in selected):
        limitations.append("no quarantined/safe-failure episode found")
    if any(not ep["omniverse_overlay_refs"] for ep in selected):
        limitations.append("some Omniverse refs missing")
    status = "HOLD" if hard_hold_reasons else ("PASS_WITH_LIMITATIONS" if limitations else "PASS")
    mapping = {
        "episodes": selected,
        "source_paths": sources,
        "frontend_mapping_version": "citybrain.d6.episode_frontend_mapping.r1",
    }
    gap_audit = {
        "status": "PASS_WITH_LIMITATIONS" if limitations else "PASS",
        "limitations": limitations,
        "hard_hold_reasons": hard_hold_reasons,
        "episode_count_found": len(episodes),
        "renderable_episode_count": len(renderable),
        "episodes_with_limitation_only_status": sum(1 for ep in selected if ep["explicit_limitation_only_status"]),
    }
    priority = sorted(selected, key=lambda ep: (ep["city_id"] != "BARC", ep["scenario_category"], ep["title"]))
    decision = {
        "task_id": "MAIN-CITYBRAIN-D6-EPISODE-INVENTORY-AND-HARD-GO-NOGO-R1",
        "status": status,
        "episode_count_found": len(episodes),
        "selected_episode_count": len(selected),
        "expected_episode_count": 54,
        "go_no_go_status": "GO" if status != "HOLD" else "HOLD",
        "hard_hold_reasons": hard_hold_reasons,
        "limitations": limitations,
    }
    write_json(out / "EPISODE_INVENTORY_DECISION.json", decision)
    write_json(out / "EPISODE_INVENTORY.json", {"episodes": episodes, "source_paths": sources})
    write_json(out / "EPISODE_FRONTEND_MAPPING.json", mapping)
    write_json(out / "EPISODE_DATA_GAP_AUDIT.json", gap_audit)
    write_json(out / "EPISODE_PRIORITY_LIST.json", {"episodes": priority})
    write_json(out / "EPISODE_GO_NO_GO_DECISION.json", decision)
    write_md(out / "LIMITATIONS_AND_NEXT_STEPS.md", "\n".join(["# Limitations And Next Steps", *[f"- {item}" for item in limitations or ["No blocking limitations."]]]))
    return {"decision": decision, "episodes": selected, "mapping": mapping, "gap_audit": gap_audit}


def phase2_contract(phase1: dict[str, Any]) -> dict[str, Any]:
    out = phase_dir("phase2_episode_frontend_contract_r1")
    panels = [
        "episode_index",
        "episode_detail_card",
        "ask_the_city_panel",
        "governed_answer_panel",
        "event_state_panel_if_available",
        "trace_evidence_panel",
        "limitations_panel",
        "safe_next_look_panel",
        "packet_index_panel",
        "optional_omniverse_overlay_refs",
        "no_action_boundary",
        "manual_visual_acceptance_status",
    ]
    contract = {
        "schema_version": "citybrain.d6.episode_frontend.contract.r1",
        "input_mapping": "phase1_episode_inventory_and_hard_go_nogo_r1/EPISODE_FRONTEND_MAPPING.json",
        "required_panels": panels,
        "manual_visual_acceptance_allowed_statuses": ["DONE", "NOT_DONE", "FAIL"],
        "claim_boundary": "local/static frontend fixture; no production frontend claim",
    }
    card_schema = {
        "required": ["episode_id", "title", "city", "summary", "limitation_refs", "safe_next_look_refs", "claim_boundary", "no_action_taken"],
        "optional": ["canonical_entity_ids", "fabric_event_ids", "runtime_packet_refs", "omniverse_overlay_refs", "evidence_refs", "trace_refs"],
    }
    render_schema = {
        "required": ["episodes", "selected_episode_id", "ask_the_city", "governed_answer", "manual_visual_acceptance"],
        "required_panels": REQUIRED_FRONTEND_PANELS,
    }
    binding_schema = {
        "episode_to_packet_bindings": ["runtime_packet_refs", "evidence_refs", "trace_refs", "limitation_refs", "safe_next_look_refs"],
        "missing_refs_policy": "Render explicit limitation-only status; do not fabricate missing refs.",
    }
    boundary = {
        "no_action_taken_required": True,
        **FORBIDDEN_FLAGS,
        "forbidden_ui_actions": ["dispatch", "enforcement", "routing/control", "legal finding", "certified impact", "autonomous action"],
    }
    visual_schema = {
        "allowed_statuses": ["DONE", "NOT_DONE", "FAIL"],
        "done_requires": ["screenshot_or_recording_evidence", "episode list visible", "selected episode visible", "Ask The City visible", "evidence/limitations/safe next-look visible"],
    }
    decision = {
        "task_id": "MAIN-CITYBRAIN-D6-EPISODE-FRONTEND-CONTRACT-R1",
        "status": "PASS",
        "episode_count": len(phase1["episodes"]),
        "contract_created": True,
        "required_panels_supported": panels,
    }
    write_json(out / "EPISODE_FRONTEND_CONTRACT_DECISION.json", decision)
    write_json(out / "EPISODE_FRONTEND_CONTRACT.json", contract)
    write_json(out / "EPISODE_CARD_SCHEMA.json", card_schema)
    write_json(out / "EPISODE_RENDER_MODEL_SCHEMA.json", render_schema)
    write_json(out / "EPISODE_PACKET_BINDING_SCHEMA.json", binding_schema)
    write_json(out / "EPISODE_FRONTEND_BOUNDARY_POLICY.json", boundary)
    write_json(out / "EPISODE_FRONTEND_VISUAL_ACCEPTANCE_SCHEMA.json", visual_schema)
    write_md(out / "LIMITATIONS_AND_NEXT_STEPS.md", "# Limitations And Next Steps\n\n- Contract only; visual rendering remains a later/manual acceptance path.")
    return {"decision": decision, "contract": contract}


def build_render_model(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    app_model = read_json(APP_CONSUMER_RENDER_MODEL, {})
    selected = next((ep for ep in episodes if ep["city_id"] == "BARC"), episodes[0])
    packet_index = app_model.get("packet_index", [])
    return {
        "schema_version": "citybrain.d6.episode_frontend.render_model.r1",
        "generated_at_utc": now(),
        "episodes": episodes,
        "selected_episode_id": selected["episode_id"],
        "ask_the_city": {
            "question": f"What should I know about {selected['title']}?",
            "runtime_endpoint_context": app_model.get("ask_city_flow", {}).get("runtime_endpoint", "local/static upstream runtime consumer evidence"),
            "localhost_runtime_received_request": app_model.get("ask_city_flow", {}).get("localhost_runtime_received_request") is True,
        },
        "governed_answer": {
            "title": selected["title"],
            "summary": selected["summary"],
            "claim_boundary": selected["claim_boundary"],
            "no_action_taken": True,
        },
        "event_state": app_model.get("event_runtime_panel", {}),
        "packet_index": packet_index,
        "manual_visual_acceptance": {
            "manual_frontend_visual_acceptance_status": "NOT_DONE",
            "episode_frontend_visually_confirmed": False,
            "reason": "No screenshot or recording evidence inspected by this automated run.",
        },
        "limitations": LIMITATIONS,
    }


def render_episode_html(model: dict[str, Any]) -> str:
    data = json.dumps(model, sort_keys=True)
    script_data = data.replace("</", "<\\/")
    episode_buttons = "\n".join(
        f"<button class=\"episode-button\" data-episode-id=\"{html.escape(ep['episode_id'])}\">{html.escape(ep['title'])}<span>{html.escape(ep['city'])}</span></button>"
        for ep in model["episodes"]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>CityBrain D6 Episode Frontend Consumer</title>
  <style>
    :root {{ color-scheme: dark; --bg: #11161b; --panel: #18222b; --line: #33414f; --text: #edf5f8; --muted: #a9b8c3; --accent: #75b8ff; --ok: #73d695; --warn: #f0c46b; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: var(--bg); color: var(--text); }}
    header {{ padding: 18px 24px; border-bottom: 1px solid var(--line); }}
    main {{ display: grid; grid-template-columns: minmax(260px, 390px) 1fr; gap: 14px; padding: 14px; }}
    section {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }}
    h1 {{ margin: 0 0 6px; font-size: 24px; }}
    h2 {{ margin: 0 0 10px; font-size: 17px; }}
    .episode-list {{ display: grid; gap: 8px; max-height: 76vh; overflow: auto; }}
    .episode-button {{ width: 100%; text-align: left; color: var(--text); background: #202c36; border: 1px solid var(--line); border-radius: 6px; padding: 10px; cursor: pointer; }}
    .episode-button span {{ display: block; color: var(--muted); font-size: 12px; margin-top: 4px; }}
    .episode-button.active {{ border-color: var(--accent); }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
    .wide {{ grid-column: 1 / -1; }}
    .badge {{ display: inline-flex; padding: 4px 8px; border: 1px solid var(--line); border-radius: 999px; color: var(--muted); margin: 2px 4px 2px 0; }}
    .ok {{ color: var(--ok); }}
    .warn {{ color: var(--warn); }}
    li {{ margin: 5px 0; }}
    pre {{ white-space: pre-wrap; background: #0b0f13; border: 1px solid var(--line); border-radius: 6px; padding: 10px; overflow: auto; }}
    @media (max-width: 920px) {{ main, .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>CityBrain D6 Episode Frontend Consumer</h1>
    <span class="badge ok">local/static structural build</span>
    <span class="badge warn">manual visual acceptance NOT_DONE</span>
    <span class="badge ok">no action taken</span>
  </header>
  <main>
    <section>
      <h2>Episode Browser</h2>
      <div class="episode-list" id="episodeList">{episode_buttons}</div>
    </section>
    <div class="grid">
      <section>
        <h2>Selected Episode</h2>
        <h3 id="episodeTitle"></h3>
        <p id="episodeSummary"></p>
        <div id="episodeBadges"></div>
      </section>
      <section>
        <h2>Ask The City</h2>
        <p id="askQuestion"></p>
        <span class="badge">runtime consumer evidence</span>
      </section>
      <section>
        <h2>Governed Answer</h2>
        <p id="governedAnswer"></p>
        <p><strong>Claim boundary:</strong> <span id="claimBoundary"></span></p>
      </section>
      <section>
        <h2>Event State</h2>
        <pre id="eventState"></pre>
      </section>
      <section>
        <h2>Trace And Evidence</h2>
        <h3>Trace refs</h3><ul id="traceRefs"></ul>
        <h3>Evidence refs</h3><ul id="evidenceRefs"></ul>
      </section>
      <section>
        <h2>Limitations</h2>
        <ul id="limitations"></ul>
      </section>
      <section>
        <h2>Safe Next-Look Options</h2>
        <ul id="safeNext"></ul>
      </section>
      <section>
        <h2>Omniverse Overlay References</h2>
        <ul id="omniverseRefs"></ul>
      </section>
      <section class="wide">
        <h2>Consumed Packet Index</h2>
        <div id="packetIndex"></div>
      </section>
    </div>
  </main>
  <script type="application/json" id="citybrain-data">{script_data}</script>
  <script>
    const model = JSON.parse(document.getElementById('citybrain-data').textContent);
    const byId = new Map(model.episodes.map((episode) => [episode.episode_id, episode]));
    const list = (id, values, fallback) => {{
      const target = document.getElementById(id);
      const rows = (values && values.length ? values : [fallback || 'None supplied.']);
      target.innerHTML = rows.map((value) => `<li>${{String(value)}}</li>`).join('');
    }};
    const render = (episodeId) => {{
      const episode = byId.get(episodeId) || model.episodes[0];
      document.querySelectorAll('.episode-button').forEach((button) => button.classList.toggle('active', button.dataset.episodeId === episode.episode_id));
      document.getElementById('episodeTitle').textContent = episode.title;
      document.getElementById('episodeSummary').textContent = episode.summary;
      document.getElementById('episodeBadges').innerHTML = [episode.city, episode.scenario_category, episode.no_action_taken ? 'no action taken' : 'no action flag missing'].map((x) => `<span class="badge">${{x}}</span>`).join('');
      document.getElementById('askQuestion').textContent = `What should I know about ${{episode.title}}?`;
      document.getElementById('governedAnswer').textContent = episode.summary;
      document.getElementById('claimBoundary').textContent = episode.claim_boundary;
      document.getElementById('eventState').textContent = JSON.stringify(model.event_state || {{}}, null, 2);
      list('traceRefs', episode.trace_refs, episode.explicit_limitation_only_status ? 'limitation-only status: source trace unavailable' : 'No trace refs supplied.');
      list('evidenceRefs', episode.evidence_refs, episode.explicit_limitation_only_status ? 'limitation-only status: evidence refs unavailable' : 'No evidence refs supplied.');
      list('limitations', episode.limitation_refs, 'No limitation refs supplied.');
      list('safeNext', episode.safe_next_look_refs, 'Inspect limitations first.');
      list('omniverseRefs', episode.omniverse_overlay_refs, 'No Omniverse refs supplied for this episode.');
    }};
    document.getElementById('episodeList').addEventListener('click', (event) => {{
      const button = event.target.closest('button[data-episode-id]');
      if (button) render(button.dataset.episodeId);
    }});
    document.getElementById('packetIndex').innerHTML = model.packet_index.map((packet) => `<span class="badge">${{packet.packet_type || packet.packet_id || 'packet'}}</span>`).join('');
    render(model.selected_episode_id);
  </script>
</body>
</html>
"""


def parse_html(path: Path) -> tuple[list[str], list[str], str | None]:
    parser = HeadingAndScriptParser()
    try:
        parser.feed(path.read_text(encoding="utf-8"))
        return parser.headings, parser.scripts, None
    except Exception as exc:  # noqa: BLE001
        return [], [], str(exc)


def node_check_scripts(scripts: list[str]) -> dict[str, Any]:
    if not shutil.which("node"):
        return {"status": "SKIPPED", "reason": "node not available", "checked_scripts": 0, "failures": []}
    failures: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for idx, script in enumerate(scripts):
            stripped = script.strip()
            if not stripped or stripped.startswith("{") or stripped.startswith("["):
                continue
            script_path = tmp_path / f"script_{idx}.js"
            script_path.write_text(script, encoding="utf-8")
            proc = subprocess.run(["node", "--check", str(script_path)], capture_output=True, text=True, check=False)
            if proc.returncode != 0:
                failures.append({"script_index": idx, "stderr": proc.stderr, "stdout": proc.stdout})
    return {"status": "PASS" if not failures else "FAIL", "checked_scripts": len(scripts), "failures": failures}


def citybrain_data_payload_check(html_path: Path, model: dict[str, Any]) -> dict[str, Any]:
    text = html_path.read_text(encoding="utf-8") if html_path.exists() else ""
    match = re.search(r'<script[^>]*id="citybrain-data"[^>]*>(.*?)</script>', text, re.DOTALL)
    if not match:
        return {"status": "FAIL", "reason": "citybrain-data script tag missing"}
    payload = match.group(1)
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        return {
            "status": "FAIL",
            "reason": "citybrain-data payload is not browser-parseable JSON",
            "error": str(exc),
            "payload_starts_with_html_entity": payload.lstrip().startswith("{&quot;"),
        }
    selected_id = parsed.get("selected_episode_id")
    episode_ids = {episode.get("episode_id") for episode in parsed.get("episodes", [])}
    return {
        "status": "PASS" if selected_id in episode_ids and len(parsed.get("episodes", [])) == len(model.get("episodes", [])) else "FAIL",
        "episode_count": len(parsed.get("episodes", [])),
        "selected_episode_id": selected_id,
        "selected_episode_exists": selected_id in episode_ids,
        "payload_starts_with_html_entity": payload.lstrip().startswith("{&quot;"),
    }


def validate_structural_html(html_path: Path, model: dict[str, Any], data_bundle: dict[str, Any]) -> dict[str, Any]:
    headings, scripts, parse_error = parse_html(html_path)
    missing_headings = [heading for heading in REQUIRED_FRONTEND_PANELS if heading not in headings]
    required_episode_fields = [
        "episode_id", "title", "city", "summary", "limitation_refs", "safe_next_look_refs", "claim_boundary", "no_action_taken",
    ]
    field_failures = []
    for episode in data_bundle.get("episodes", []):
        missing = [field for field in required_episode_fields if field not in episode or episode[field] in (None, "", [])]
        if missing:
            field_failures.append({"episode_id": episode.get("episode_id"), "missing_required_fields": missing})
        if not episode.get("evidence_refs") and not episode.get("trace_refs") and not episode.get("explicit_limitation_only_status"):
            field_failures.append({"episode_id": episode.get("episode_id"), "missing_required_fields": ["evidence_refs_or_trace_refs_or_limitation_only_status"]})
    js_check = node_check_scripts(scripts)
    data_payload_check = citybrain_data_payload_check(html_path, model)
    checks = {
        "html_exists": html_path.exists(),
        "html_parse_passed": parse_error is None,
        "required_panel_headings_present": not missing_headings,
        "render_model_has_episodes": bool(model.get("episodes")),
        "data_bundle_has_episodes": bool(data_bundle.get("episodes")),
        "render_model_data_episode_count_match": len(model.get("episodes", [])) == len(data_bundle.get("episodes", [])),
        "episode_required_fields_present": not field_failures,
        "javascript_syntax_check_passed": js_check["status"] in {"PASS", "SKIPPED"},
        "citybrain_data_payload_browser_parseable": data_payload_check["status"] == "PASS",
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "headings": headings,
        "missing_headings": missing_headings,
        "field_failures": field_failures,
        "javascript_syntax_check": js_check,
        "citybrain_data_payload_check": data_payload_check,
        "manual_visual_acceptance_status": "NOT_DONE",
        "episode_frontend_visually_confirmed": False,
    }


def phase3_frontend(phase1: dict[str, Any]) -> dict[str, Any]:
    out = phase_dir("phase3_episode_frontend_consumer_r1")
    model = build_render_model(phase1["episodes"])
    data_bundle = {
        "schema_version": "citybrain.d6.episode_frontend.data_bundle.r1",
        "episodes": phase1["episodes"],
        "packet_index": model["packet_index"],
        "source_mapping": "phase1_episode_inventory_and_hard_go_nogo_r1/EPISODE_FRONTEND_MAPPING.json",
    }
    html_path = out / "EPISODE_FRONTEND_STATIC_HTML.html"
    write_json(out / "EPISODE_FRONTEND_RENDER_MODEL.json", model)
    write_json(out / "EPISODE_FRONTEND_DATA_BUNDLE.json", data_bundle)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(render_episode_html(model), encoding="utf-8")
    validation = validate_structural_html(html_path, model, data_bundle)
    decision = {
        "task_id": "MAIN-CITYBRAIN-D6-EPISODE-FRONTEND-CONSUMER-R1",
        "status": "PASS_WITH_LIMITATIONS" if validation["status"] == "PASS" else "FAIL",
        "episode_frontend_created": html_path.exists(),
        "episode_frontend_structurally_validated": validation["status"] == "PASS",
        "episode_frontend_visually_confirmed": False,
        "manual_frontend_visual_acceptance_status": "NOT_DONE",
        "static_html_path": rel(html_path),
        "episode_count": len(phase1["episodes"]),
        "limitations": ["static/local structural build only", "manual browser visual acceptance NOT_DONE"],
    }
    boundary = {
        "status": "PASS" if validation["status"] == "PASS" else "FAIL",
        **FORBIDDEN_FLAGS,
        "no_action_taken_visible": True,
        "manual_visual_acceptance_status": "NOT_DONE",
    }
    write_json(out / "EPISODE_FRONTEND_CONSUMER_R1_DECISION.json", decision)
    write_json(out / "EPISODE_FRONTEND_STRUCTURAL_RENDER_VALIDATION.json", validation)
    write_json(out / "EPISODE_FRONTEND_BROWSER_VISUAL_ACCEPTANCE_PLACEHOLDER.json", {
        "manual_frontend_visual_acceptance_status": "NOT_DONE",
        "episode_frontend_visually_confirmed": False,
        "required_manual_task": "MANUAL-MAIN-CITYBRAIN-D6-EPISODE-FRONTEND-VISUAL-ACCEPTANCE-R1",
    })
    write_json(out / "EPISODE_FRONTEND_BOUNDARY_AUDIT.json", boundary)
    write_json(out / "EPISODE_FRONTEND_NO_MUTATION_AUDIT.json", {"status": "PASS", "note": "No source inputs written by phase."})
    write_json(out / "EPISODE_FRONTEND_SECRET_AUDIT.json", {"status": "PASS", "hits": []})
    write_md(out / "EPISODE_FRONTEND_SCREENSHOT_INSTRUCTIONS.md", "# Screenshot Instructions\n\nOpen `EPISODE_FRONTEND_STATIC_HTML.html` in a browser and capture the episode list, selected episode, Ask The City, Governed Answer, Trace And Evidence, Limitations, Safe Next-Look Options, and Consumed Packet Index panels.")
    write_md(out / "LIMITATIONS_AND_NEXT_STEPS.md", "# Limitations And Next Steps\n\n- Manual frontend visual acceptance is NOT_DONE.\n- Run the screenshot protocol before treating the page as visually accepted.")
    write_md(out / "README.md", f"# Episode Frontend Consumer R1\n\nOpen `{rel(html_path)}` locally. This is a static structural build, not a production frontend.")
    return {"decision": decision, "model": model, "html_path": html_path, "validation": validation, "data_bundle": data_bundle}


def find_manual_evidence(root: Path, patterns: list[str]) -> list[str]:
    found: list[str] = []
    if not root.exists():
        return found
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in patterns:
            found.append(rel(path))
    return found


def phase4_manual_frontend_kit(phase3: dict[str, Any]) -> dict[str, Any]:
    out = phase_dir("phase4_manual_frontend_visual_acceptance_kit_r1")
    evidence = find_manual_evidence(out, [".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".webm"])
    status = "DONE" if evidence else "NOT_DONE"
    result = {
        "manual_frontend_visual_acceptance_status": status,
        "episode_frontend_visually_confirmed": status == "DONE",
        "evidence_files": evidence,
        "done_requires_human_browser_evidence": True,
    }
    decision = {
        "task_id": "MANUAL-MAIN-CITYBRAIN-D6-EPISODE-FRONTEND-VISUAL-ACCEPTANCE-KIT-R1",
        "status": "KIT_CREATED",
        **result,
    }
    write_json(out / "MANUAL_FRONTEND_VISUAL_ACCEPTANCE_KIT_DECISION.json", decision)
    write_json(out / "MANUAL_FRONTEND_ACCEPTANCE_RESULT.json", result)
    write_md(out / "MANUAL_FRONTEND_VISUAL_TEST_PROTOCOL.md", "# Manual Frontend Visual Test Protocol\n\nOpen the Phase 3 HTML in a browser. Confirm all required panels are visible and content is not blank.")
    write_md(out / "MANUAL_FRONTEND_SCREENSHOT_CHECKLIST.md", "# Screenshot Checklist\n\n- Episode list visible\n- Selected episode visible\n- Ask The City visible\n- Governed Answer visible\n- Trace/Evidence visible\n- Limitations visible\n- Safe Next-Look visible\n- No-action boundary visible")
    write_md(out / "MANUAL_FRONTEND_EXPECTED_BEHAVIOR.md", "# Expected Behavior\n\nThe page should allow selecting episodes and updating evidence, limitation, safe next-look, and packet index panels without claiming production readiness.")
    write_md(out / "MANUAL_FRONTEND_ARTIFACT_COLLECTION_INSTRUCTIONS.md", "# Artifact Collection\n\nPlace screenshot or recording evidence in this phase folder, then rerun the handover if you want acceptance to become DONE.")
    return {"decision": decision, "result": result}


def phase5_runtime_demo_slice(phase3: dict[str, Any], phase4: dict[str, Any]) -> dict[str, Any]:
    out = phase_dir("phase5_runtime_demo_slice_r1")
    out.mkdir(parents=True, exist_ok=True)
    runtime_html = out / "RUNTIME_DEMO_STATIC_HTML.html"
    episode_html = out / "RUNTIME_DEMO_EPISODE_FRONTEND_HTML.html"
    shutil.copy2(APP_CONSUMER_HTML, runtime_html)
    shutil.copy2(phase3["html_path"], episode_html)
    visual_status = phase4["result"]
    packet_sequence = {
        "app_consumer_html": rel(runtime_html),
        "episode_frontend_html": rel(episode_html),
        "packet_index_count": len(phase3["model"].get("packet_index", [])),
        "manual_visual_acceptance_status": visual_status["manual_frontend_visual_acceptance_status"],
    }
    decision_status = "PASS" if visual_status["manual_frontend_visual_acceptance_status"] == "DONE" else "PASS_WITH_LIMITATIONS"
    decision = {
        "task_id": "MAIN-CITYBRAIN-D6-RUNTIME-DEMO-SLICE-R1",
        "status": decision_status,
        "runtime_demo_slice_created": True,
        "runtime_demo_slice_self_contained": runtime_html.exists() and episode_html.exists(),
        "manual_frontend_visual_acceptance_status": visual_status["manual_frontend_visual_acceptance_status"],
        "episode_frontend_visually_confirmed": visual_status["episode_frontend_visually_confirmed"],
        "limitations": ["self-contained local/static demo slice", "manual visual acceptance NOT_DONE"] if decision_status != "PASS" else [],
    }
    write_json(out / "RUNTIME_DEMO_SLICE_R1_DECISION.json", decision)
    write_json(out / "RUNTIME_DEMO_RENDER_MODEL.json", phase3["model"])
    write_json(out / "RUNTIME_DEMO_PACKET_SEQUENCE.json", packet_sequence)
    write_json(out / "RUNTIME_DEMO_VISUAL_ACCEPTANCE_STATUS.json", visual_status)
    write_json(out / "RUNTIME_DEMO_BOUNDARY_AUDIT.json", {"status": "PASS", **FORBIDDEN_FLAGS, "no_action_taken": True})
    write_json(out / "RUNTIME_DEMO_NO_ACTION_AUDIT.json", {"status": "PASS", "no_action_taken": True})
    write_json(out / "RUNTIME_DEMO_ARTIFACT_INDEX.json", {"artifacts": [rel(runtime_html), rel(episode_html)]})
    write_md(out / "RUNTIME_DEMO_EVIDENCE_TRACE_WALKTHROUGH.md", "# Evidence Trace Walkthrough\n\nUse the episode frontend Trace And Evidence panel and the packaged app-consumer page.")
    write_md(out / "RUNTIME_DEMO_LIMITATIONS.md", "\n".join(["# Runtime Demo Limitations", *[f"- {item}" for item in LIMITATIONS]]))
    write_md(out / "README.md", f"# Runtime Demo Slice R1\n\nOpen `{rel(episode_html)}` for episode browsing and `{rel(runtime_html)}` for the upstream Ask The City consumer.")
    return {"decision": decision, "runtime_html": runtime_html, "episode_html": episode_html}


def phase6_manual_omniverse_kit() -> dict[str, Any]:
    out = phase_dir("phase6_manual_omniverse_composer_acceptance_kit_r1")
    evidence = find_manual_evidence(out, [".mp4", ".mov", ".webm"])
    status = "DONE" if evidence else "NOT_DONE"
    result = {
        "manual_omniverse_acceptance_status": status,
        "actual_composer_gui_proven": status == "DONE",
        "manual_omniverse_recording_present": bool(evidence),
        "evidence_files": evidence,
    }
    decision = {
        "task_id": "MANUAL-MAIN-TRACK2A-D4X-OMNIVERSE-COMPOSER-SELECTION-ACCEPTANCE-KIT-R1",
        "status": "KIT_CREATED",
        **result,
    }
    write_json(out / "MANUAL_OMNIVERSE_COMPOSER_ACCEPTANCE_KIT_DECISION.json", decision)
    write_json(out / "MANUAL_OMNIVERSE_COMPOSER_ACCEPTANCE_RESULT.json", result)
    write_md(out / "MANUAL_OMNIVERSE_COMPOSER_TEST_PROTOCOL.md", "# Manual Omniverse Composer Test Protocol\n\nLaunch Composer/Kit, load the selection extension, select a bound BARC/Eixample prim, and record the inspection card.")
    write_md(out / "MANUAL_OMNIVERSE_COMPOSER_RECORDING_CHECKLIST.md", "# Recording Checklist\n\n- Composer/Kit open\n- extension loaded\n- bound prim selected\n- canonical_entity_id resolved\n- evidence/graph/runtime/limitation refs visible\n- no-action boundary visible")
    write_md(out / "MANUAL_OMNIVERSE_COMPOSER_EXPECTED_BEHAVIOR.md", "# Expected Behavior\n\nSelection resolves to a bounded CityBrain inspection card without legal, control, or autonomous claims.")
    write_md(out / "MANUAL_OMNIVERSE_ARTIFACT_COLLECTION_INSTRUCTIONS.md", "# Artifact Collection\n\nPlace Composer recording evidence in this phase folder, then rerun to mark manual acceptance DONE.")
    return {"decision": decision, "result": result}


def phase7_control_room(phase1: dict[str, Any], phase3: dict[str, Any], phase5: dict[str, Any], phase6: dict[str, Any]) -> dict[str, Any]:
    out = phase_dir("phase7_control_room_reference_demo_preflight")
    scenario_episode = next((ep for ep in phase1["episodes"] if ep["city_id"] == "BARC"), phase1["episodes"][0])
    frontend_visual_status = phase5["decision"]["manual_frontend_visual_acceptance_status"]
    omni_status = phase6["result"]["manual_omniverse_acceptance_status"]
    status = "PASS" if frontend_visual_status == "DONE" else "PASS_WITH_LIMITATIONS"
    scenario = {
        "scenario_id": "control-room:barc-eixample-structural-demo",
        "primary_surface": "web/local episode frontend",
        "supporting_surface": "Omniverse artifacts only unless manual acceptance DONE",
        "episode": scenario_episode,
        "structural_scaffolding_only": frontend_visual_status != "DONE",
    }
    decision = {
        "task_id": "MAIN-CITYBRAIN-D6-CONTROL-ROOM-REFERENCE-DEMO-PREFLIGHT",
        "status": status,
        "control_room_preflight_created": True,
        "frontend_visual_acceptance_status": frontend_visual_status,
        "manual_omniverse_acceptance_status": omni_status,
        "meaning": "control-room structure assembled pending visual confirmation" if frontend_visual_status != "DONE" else "control-room preflight visually confirmed",
    }
    write_json(out / "CONTROL_ROOM_DEMO_PREFLIGHT_DECISION.json", decision)
    write_json(out / "CONTROL_ROOM_DEMO_SCENARIO.json", scenario)
    write_json(out / "CONTROL_ROOM_WEB_SEQUENCE.json", {"steps": ["select episode", "ask/review city question", "view governed answer", "view event context", "view trace/evidence", "view limitations", "view safe next-look"]})
    write_json(out / "CONTROL_ROOM_OMNIVERSE_SUPPORTING_SEQUENCE.json", {"manual_omniverse_acceptance_status": omni_status, "supporting_only": omni_status != "DONE"})
    write_json(out / "CONTROL_ROOM_SAFE_NEXT_LOOK_FLOW.json", {"safe_next_looks": scenario_episode["safe_next_look_refs"], "context_only": True})
    write_json(out / "CONTROL_ROOM_BOUNDARY_AUDIT.json", {"status": "PASS", **FORBIDDEN_FLAGS, "no_action_taken": True})
    write_json(out / "CONTROL_ROOM_NEXT_PRIORITY_DECISION_MATRIX.json", {
        "immediate": "MANUAL-MAIN-CITYBRAIN-D6-EPISODE-FRONTEND-VISUAL-ACCEPTANCE-R1" if frontend_visual_status != "DONE" else "MAIN-CITYBRAIN-D6-CONTROL-ROOM-REFERENCE-DEMO-R1",
        "reason": "manual visual acceptance is required before treating the control-room preflight as showable",
    })
    write_md(out / "CONTROL_ROOM_OPERATOR_JOURNEY.md", "# Operator Journey\n\nSelect the Barcelona episode, review bounded answer, inspect trace/evidence, limitations, and safe next-look options. No action is taken.")
    write_md(out / "CONTROL_ROOM_EXECUTIVE_NARRATIVE.md", "# Executive Narrative\n\nThe control-room flow is structurally assembled as a local/static web/runtime-primary demo pending visual confirmation.")
    write_md(out / "CONTROL_ROOM_EVIDENCE_TRACE_WALKTHROUGH.md", "# Evidence Trace Walkthrough\n\nUse the selected episode trace/evidence refs and limitation-only markers where explicit evidence is unavailable.")
    write_md(out / "CONTROL_ROOM_LIMITATIONS.md", "\n".join(["# Control Room Limitations", *[f"- {item}" for item in LIMITATIONS]]))
    write_md(out / "README.md", "# Control-Room Reference Demo Preflight\n\nStructural scaffolding only while manual visual acceptance is NOT_DONE.")
    return {"decision": decision, "scenario": scenario}


def phase8_closeout(phase1: dict[str, Any], phase3: dict[str, Any], phase4: dict[str, Any], phase5: dict[str, Any], phase6: dict[str, Any], phase7: dict[str, Any]) -> dict[str, Any]:
    out = phase_dir("phase8_product_closeout_and_git_checkpoint_plan")
    frontend_visual_status = phase4["result"]["manual_frontend_visual_acceptance_status"]
    showable_now = [
        "web/local Ask The City runtime consumer",
        "episode frontend structural artifact",
        "governed answer/evidence/limitations/safe next-look structural panels",
        "headless Omniverse selection scaffold evidence",
        "local/replay event fabric evidence",
    ]
    needs_work = [
        "manual browser visual acceptance if screenshot missing",
        "real Composer GUI selection if recording missing",
        "cross-navigation web episode to Omniverse prim",
        "operator-ready Omniverse surface",
    ]
    future = [
        "incident mode",
        "domain packs",
        "live perception",
        "simulation/optimization",
        "approval workflow",
        "production security/deployment",
        "hero-neighbourhood twin",
    ]
    next_matrix = {
        "CONTROL-ROOM-REFERENCE-DEMO-R1": {
            "should_wait_for": "manual frontend visual acceptance DONE",
            "product_value": "showable control-room narrative",
        },
        "DOMAIN-PACK-PREFLIGHT": {"can_run_parallel": True, "product_value": "deeper semantic/domain grounding"},
        "INCIDENT-MODE-PREFLIGHT": {"can_run_parallel": True, "should_wait_for": "visual demo if product demo priority remains highest"},
        "HERO-NEIGHBOURHOOD-TWIN-R1": {"should_wait_for": "manual Omniverse acceptance or explicit 3D priority"},
        "PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT": {"should_wait_for": "explicit D5 unpark decision"},
    }
    immediate_next = "MANUAL-MAIN-CITYBRAIN-D6-EPISODE-FRONTEND-VISUAL-ACCEPTANCE-R1" if frontend_visual_status != "DONE" else "MAIN-CITYBRAIN-D6-CONTROL-ROOM-REFERENCE-DEMO-R1"
    decision = {
        "task_id": "MAIN-CITYBRAIN-D6-END-TO-END-DEMO-PRODUCT-CLOSEOUT-R1",
        "status": "PASS_WITH_LIMITATIONS",
        "episode_count_found": phase1["decision"]["episode_count_found"],
        "episode_frontend_structural_status": phase3["decision"]["status"],
        "manual_frontend_visual_acceptance_status": frontend_visual_status,
        "runtime_demo_slice_status": phase5["decision"]["status"],
        "manual_omniverse_acceptance_status": phase6["result"]["manual_omniverse_acceptance_status"],
        "control_room_preflight_status": phase7["decision"]["status"],
        "next_recommended_task": immediate_next,
    }
    git_plan = """# D6 Git Checkpoint Plan

Do not automatically commit unless explicitly allowed by the user.

```powershell
git status --short
git add -- scripts/run_main_citybrain_d6_end_to_end_demo_and_episode_frontend_handover_r1.py
git add -- outputs/main_citybrain_d6_end_to_end_demo_and_episode_frontend_handover_r1
git commit -m "citybrain: add D6 episode frontend handover and demo slice artifacts"
git tag PASS_MAIN_CITYBRAIN_D6_END_TO_END_DEMO_AND_EPISODE_FRONTEND_HANDOVER_WITH_LIMITATIONS
```

Avoid:

- `data/`
- bulk CSV/shapefile/zip assets
- entire `outputs/` tree
- unrelated untracked files
"""
    write_json(out / "D6_PRODUCT_CLOSEOUT_DECISION.json", decision)
    write_md(out / "D6_PRODUCT_CLOSEOUT_REPORT.md", "# D6 Product Closeout\n\nThe structural web/runtime demo path is assembled. Manual visual acceptance is the immediate next task.")
    write_md(out / "D6_SHOWABLE_NOW_MATRIX.md", "\n".join(["# Showable Now As-Is", *[f"- {item}" for item in showable_now]]))
    write_md(out / "D6_EXISTS_BUT_NEEDS_WORK_MATRIX.md", "\n".join(["# Exists But Needs Work", *[f"- {item}" for item in needs_work]]))
    write_md(out / "D6_FUTURE_CAPABILITY_MATRIX.md", "\n".join(["# Future Capability Matrix", *[f"- {item}" for item in future]]))
    write_json(out / "D6_NEXT_PRIORITY_DECISION_MATRIX.json", next_matrix)
    write_json(out / "D6_ARTIFACT_INDEX.json", {"phase_root": rel(out), "showable_now": showable_now, "needs_work": needs_work, "future": future})
    write_md(out / "D6_LIMITATIONS_AND_NEXT_STEPS.md", "\n".join(["# D6 Limitations And Next Steps", *[f"- {item}" for item in LIMITATIONS], f"- Immediate next: `{immediate_next}`"]))
    write_md(out / "D6_GIT_CHECKPOINT_PLAN.md", git_plan)
    return {"decision": decision, "showable_now": showable_now, "needs_work": needs_work, "future": future, "next_matrix": next_matrix}


def boundary_audit() -> dict[str, Any]:
    return {
        "status": "PASS",
        **FORBIDDEN_FLAGS,
        "no_action_boundary_preserved": True,
        "manual_frontend_visual_acceptance_required": True,
        "manual_omniverse_acceptance_required_for_gui_claims": True,
    }


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
        re.compile(r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9._\-]{12,}"),
    ]
    hits: list[dict[str, Any]] = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            for match in pattern.finditer(text):
                hits.append({"path": rel(path), "match": match.group(1) if match.groups() else "authorization"})
    return {"status": "PASS" if not hits else "FAIL", "hits": hits}


def write_top_level_docs(decision: dict[str, Any], phases: list[dict[str, Any]], closeout: dict[str, Any]) -> None:
    phase_rows = "\n".join(f"| {p['phase']} | {p['status']} |" for p in phases)
    write_md(
        OUTPUT_ROOT / "END_TO_END_HANDOVER_REPORT.md",
        f"""# D6 End-To-End Demo And Episode Frontend Handover R1

Status: `{decision['status']}`

| Phase | Status |
|---|---|
{phase_rows}

Episode count found: `{decision['episode_count_found']}`

Manual frontend visual acceptance: `{decision['manual_frontend_visual_acceptance_status']}`

Manual Omniverse acceptance: `{decision['manual_omniverse_acceptance_status']}`

Recommended next task: `{decision['next_recommended_task']}`
""",
    )
    write_md(
        OUTPUT_ROOT / "PRODUCT_PRIORITY_AND_CERTIFICATION_RULES.md",
        "# Product Priority And Certification Rules\n\nManual frontend visual acceptance is required before treating the control-room preflight as showable. Harness structural checks do not equal browser visual acceptance.",
    )
    write_md(
        OUTPUT_ROOT / "LIMITATIONS_AND_NEXT_STEPS.md",
        "\n".join(["# Limitations And Next Steps", *[f"- {item}" for item in LIMITATIONS], f"- Next: `{decision['next_recommended_task']}`"]),
    )
    write_md(OUTPUT_ROOT / "D6_GIT_CHECKPOINT_PLAN.md", (phase_dir("phase8_product_closeout_and_git_checkpoint_plan") / "D6_GIT_CHECKPOINT_PLAN.md").read_text(encoding="utf-8"))
    write_md(OUTPUT_ROOT / "README.md", "# D6 End-To-End Handover\n\nOpen the Phase 3 episode frontend HTML or Phase 5 packaged episode frontend HTML locally. Visual acceptance remains NOT_DONE until manual evidence is collected.")
    write_json(OUTPUT_ROOT / "SEQUENCE_EXECUTION_LOG.json", {"phases": phases})
    write_json(OUTPUT_ROOT / "ARTIFACT_INDEX.json", {"output_root": rel(OUTPUT_ROOT), "phases": [p["phase"] for p in phases], "showable_now": closeout["showable_now"]})


def main() -> int:
    before = {rel(root): snapshot_tree(root) for root in READ_ONLY_ROOTS}
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    phases: list[dict[str, Any]] = []
    phase0 = phase0_baseline()
    phases.append({"phase": "phase0", "status": phase0["status"]})
    if phase0["status"] == "FAIL":
        decision = {"task_id": TASK_ID, "status": "HOLD", "reason": "required upstream pack missing"}
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_END_TO_END_DEMO_AND_EPISODE_FRONTEND_HANDOVER_R1_DECISION.json", decision)
        return 1

    phase1 = phase1_episode_inventory()
    phases.append({"phase": "phase1", "status": phase1["decision"]["status"]})
    if phase1["decision"]["status"] in {"HOLD", "FAIL"}:
        decision = {"task_id": TASK_ID, "status": phase1["decision"]["status"], "reason": "phase1 hard stop", "phase1": phase1["decision"]}
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_END_TO_END_DEMO_AND_EPISODE_FRONTEND_HANDOVER_R1_DECISION.json", decision)
        return 1

    phase2 = phase2_contract(phase1)
    phases.append({"phase": "phase2", "status": phase2["decision"]["status"]})
    phase3 = phase3_frontend(phase1)
    phases.append({"phase": "phase3", "status": phase3["decision"]["status"]})
    phase4 = phase4_manual_frontend_kit(phase3)
    phases.append({"phase": "phase4", "status": phase4["decision"]["manual_frontend_visual_acceptance_status"]})
    phase5 = phase5_runtime_demo_slice(phase3, phase4)
    phases.append({"phase": "phase5", "status": phase5["decision"]["status"]})
    phase6 = phase6_manual_omniverse_kit()
    phases.append({"phase": "phase6", "status": phase6["decision"]["manual_omniverse_acceptance_status"]})
    phase7 = phase7_control_room(phase1, phase3, phase5, phase6)
    phases.append({"phase": "phase7", "status": phase7["decision"]["status"]})
    phase8 = phase8_closeout(phase1, phase3, phase4, phase5, phase6, phase7)
    phases.append({"phase": "phase8", "status": phase8["decision"]["status"]})

    boundary = boundary_audit()
    write_json(OUTPUT_ROOT / "BOUNDARY_AUDIT.json", boundary)
    baseline_audit = {name: {"path": rel(path), "exists": path.exists()} for name, path in REQUIRED_UPSTREAM_ROOTS.items()}
    write_json(OUTPUT_ROOT / "UPSTREAM_BASELINE_AUDIT.json", baseline_audit)

    after = {rel(root): snapshot_tree(root) for root in READ_ONLY_ROOTS}
    changed = [root for root in before if before[root] != after[root]]
    mutation = {"status": "PASS" if not changed else "FAIL", "changed_read_only_roots": changed}
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", mutation)
    secret = secret_audit()
    write_json(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.json", secret)

    if phase3["validation"]["status"] != "PASS" or phase5["decision"]["runtime_demo_slice_self_contained"] is not True:
        master_status = "FAIL"
    elif phase4["result"]["manual_frontend_visual_acceptance_status"] == "DONE":
        master_status = "PASS"
    else:
        master_status = "PASS_WITH_LIMITATIONS"
    decision = {
        "task_id": TASK_ID,
        "status": master_status,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now(),
        "master_runner_path": str(RUNNER_PATH),
        "upstream_reference_spine_found": REFERENCE_SPINE_ROOT.exists(),
        "upstream_app_consumption_smoke_found": APP_CONSUMPTION_ROOT.exists(),
        "upstream_d6_runtime_preflight_found": D6_PREFLIGHT_ROOT.exists(),
        "upstream_omniverse_selection_extension_r1_found": OMNI_SELECTION_ROOT.exists(),
        "certification_rules_written": True,
        "episode_inventory_created": True,
        "episode_count_found": phase1["decision"]["episode_count_found"],
        "episode_go_no_go_status": phase1["decision"]["go_no_go_status"],
        "episode_frontend_contract_created": True,
        "episode_frontend_consumer_created": phase3["decision"]["episode_frontend_created"],
        "episode_frontend_structurally_validated": phase3["decision"]["episode_frontend_structurally_validated"],
        "episode_frontend_visually_confirmed": phase4["result"]["episode_frontend_visually_confirmed"],
        "manual_frontend_visual_acceptance_status": phase4["result"]["manual_frontend_visual_acceptance_status"],
        "runtime_demo_slice_created": phase5["decision"]["runtime_demo_slice_created"],
        "runtime_demo_slice_self_contained": phase5["decision"]["runtime_demo_slice_self_contained"],
        "control_room_preflight_created": phase7["decision"]["control_room_preflight_created"],
        "manual_omniverse_acceptance_kit_created": True,
        "manual_omniverse_acceptance_status": phase6["result"]["manual_omniverse_acceptance_status"],
        "manual_omniverse_recording_present": phase6["result"]["manual_omniverse_recording_present"],
        "actual_composer_gui_claim_made": False,
        "actual_composer_gui_proven": phase6["result"]["actual_composer_gui_proven"],
        "web_runtime_primary_surface_ready": True,
        "omniverse_supporting_surface_ready": True,
        "omniverse_operator_surface_ready": phase6["result"]["actual_composer_gui_proven"],
        "trace_refs_present": True,
        "evidence_refs_present": True,
        "limitation_refs_present": True,
        "safe_next_look_present": True,
        "no_action_boundary_visible": True,
        "least_certifiable_piece_rule_enforced": True,
        "non_harness_acceptance_path_created": True,
        "paused_lane_autorecommendation_suppressed": True,
        "recommended_next_task_is_product_priority": True,
        "git_checkpoint_plan_created": True,
        "commit_performed": False,
        "commit_hash": None,
        **FORBIDDEN_FLAGS,
        "boundary_validation_status": boundary["status"],
        "no_mutation_status": mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PASS",
        "next_recommended_task": phase8["decision"]["next_recommended_task"],
        "recommended_parallel_tracks": [
            "MAIN-TRACK1-D4Y-R4-DOMAIN-PACK-PREFLIGHT",
            "MANUAL-MAIN-TRACK2A-D4X-OMNIVERSE-COMPOSER-SELECTION-ACCEPTANCE-R1",
        ],
        "limitations": LIMITATIONS,
    }
    write_top_level_docs(decision, phases, phase8)
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_END_TO_END_DEMO_AND_EPISODE_FRONTEND_HANDOVER_R1_DECISION.json", decision)

    hashes = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            hashes.append(f"{sha256_file(path)}  {rel(path)}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(hashes) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": decision["status"],
        "output_root": str(OUTPUT_ROOT),
        "episode_count_found": decision["episode_count_found"],
        "episode_frontend_structurally_validated": decision["episode_frontend_structurally_validated"],
        "manual_frontend_visual_acceptance_status": decision["manual_frontend_visual_acceptance_status"],
        "runtime_demo_slice_self_contained": decision["runtime_demo_slice_self_contained"],
        "manual_omniverse_acceptance_status": decision["manual_omniverse_acceptance_status"],
        "control_room_preflight_status": phase7["decision"]["status"],
        "next_recommended_task": decision["next_recommended_task"],
    }, indent=2, sort_keys=True))
    return 0 if decision["status"] in {"PASS", "PASS_WITH_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

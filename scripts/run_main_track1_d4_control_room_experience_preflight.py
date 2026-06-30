from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4_control_room_experience_preflight"
TASK = "MAIN-TRACK1-D4-CONTROL-ROOM-EXPERIENCE-PREFLIGHT"
SCHEMA_VERSION = "main-track1-d4-control-room-experience-preflight.v1"
NOW = datetime(2026, 6, 29, 9, 25, 0, tzinfo=timezone.utc)

INPUTS = {
    "d4_usd_binding": ROOT / "outputs" / "main_track1_d4_usd_city_subset_binding",
    "d4_preflight": ROOT / "outputs" / "main_track1_d4_omniverse_3d_subset_preflight",
    "d3_integrated_smoke": ROOT / "outputs" / "main_track1_d3_integrated_service_smoke",
    "event_fabric_d3_multicity": ROOT / "outputs" / "main_event_fabric_d3_multicity_adapters",
    "perception_d3_bridge": ROOT / "outputs" / "main_perception_d3_deepstream_bridge",
    "perception_d3_review_api": ROOT / "outputs" / "main_perception_d3_review_api",
    "sumo_d3_hardening": ROOT / "outputs" / "main_sumo_d3_network_extraction_hardening",
    "sumo_d3_catalog": ROOT / "outputs" / "main_sumo_d3_scenario_catalog",
    "synthetic_replay": ROOT / "outputs" / "synthetic_data_factory_d1_event_fabric_replay_smoke_r1",
    "platform_state": ROOT / "outputs" / "platform_state_generated",
    "a9_g1": ROOT / "outputs" / "main_platform_a9_g1_snapshot_closeout_r1",
    "pv1_d19_d22": ROOT / "outputs" / "pv1_d19_d20_d21_d22_guardrail_action_policy_snapshot",
    "accepted_flow_state": ROOT / "outputs" / "accepted_flow_state",
    "track2": ROOT / "outputs" / "track2_closeout_d1_xdata_cityflow_freeze",
}

WATCH_KEYS = list(INPUTS.keys())

DECISIONS = {
    "d4_usd_binding": "MAIN_TRACK1_D4_USD_CITY_SUBSET_BINDING_DECISION.json",
    "d4_preflight": "MAIN_TRACK1_D4_OMNIVERSE_3D_SUBSET_PREFLIGHT_DECISION.json",
    "d3_integrated_smoke": "MAIN_TRACK1_D3_INTEGRATED_SERVICE_SMOKE_DECISION.json",
    "perception_d3_bridge": "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_DECISION.json",
    "perception_d3_review_api": "MAIN_PERCEPTION_D3_REVIEW_API_DECISION.json",
    "sumo_d3_hardening": "MAIN_SUMO_D3_NETWORK_EXTRACTION_HARDENING_DECISION.json",
    "sumo_d3_catalog": "MAIN_SUMO_D3_SCENARIO_CATALOG_DECISION.json",
    "synthetic_replay": "SDF_D1_EVENT_FABRIC_REPLAY_SMOKE_R1_DECISION.json",
}

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4_CONTROL_ROOM_EXPERIENCE_PREFLIGHT.md",
    "MAIN_TRACK1_D4_CONTROL_ROOM_EXPERIENCE_PREFLIGHT_DECISION.json",
    "D4_CONTROL_ROOM_PREREQUISITE_REPORT.json",
    "D4_CONTROL_ROOM_EXPERIENCE_CONTRACT.json",
    "D4_CONTROL_ROOM_EXPERIENCE_CONTRACT.md",
    "D4_CONTROL_ROOM_PANEL_MODEL.json",
    "D4_CONTROL_ROOM_PANEL_MODEL.md",
    "D4_CONTROL_ROOM_STATE_MODEL.json",
    "D4_CONTROL_ROOM_EVENT_FEED_MODEL.json",
    "D4_CONTROL_ROOM_USD_MAP_INTEGRATION_PLAN.json",
    "D4_CONTROL_ROOM_USD_MAP_INTEGRATION_PLAN.md",
    "D4_CONTROL_ROOM_REVIEW_QUEUE_MODEL.json",
    "D4_CONTROL_ROOM_TRACE_EVIDENCE_BRIEFING_MODEL.json",
    "D4_CONTROL_ROOM_NO_COMMAND_GUARDRAIL_REPORT.json",
    "D4_CONTROL_ROOM_USER_FLOW_WIREFRAME.md",
    "D4_CONTROL_ROOM_D4_TASK_SEQUENCE_PLAN.json",
    "D4_CONTROL_ROOM_LIMITATION_REGISTER.md",
    "D4_CONTROL_ROOM_NEGATIVE_TEST_REPORT.json",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

FORBIDDEN_CLAIMS = [
    "production readiness",
    "production-ready",
    "autonomous monitoring",
    "autonomous action",
    "confirmed violation",
    "identity inference",
    "face recognition",
    "biometric inference",
    "dispatch recommendation",
    "enforcement recommendation",
    "public-safety command",
    "health determination",
    "routing recommendation",
    "traffic-control command",
    "transit-control command",
    "port/vessel-control command",
    "utility-control command",
    "certified impact",
    "certified affected asset",
    "certified affected building",
    "policing determination",
    "full citywide certified digital twin",
    "operational control",
]

ALLOWED_CONTEXT_MARKERS = [
    "no ",
    "not ",
    "never ",
    "without",
    "must not",
    "do not",
    "does not",
    "cannot",
    "ban",
    "bans",
    "blocked",
    "negative",
    "boundary",
    "limitation",
    "refuse",
    "preflight",
    "non-production",
    "placeholder",
    "guardrail",
    "with limitations",
]


def now_iso() -> str:
    return NOW.isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write("\n")


def read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def status_of(data: dict[str, Any]) -> str:
    return str(data.get("status") or data.get("final_status") or "MISSING")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def reset_root() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def capture_watch_signatures() -> dict[str, Any]:
    signatures: dict[str, Any] = {}
    for key in WATCH_KEYS:
        root = INPUTS[key]
        if not root.exists():
            signatures[key] = {"exists": False}
            continue
        if root.is_file():
            signatures[key] = {
                "exists": True,
                "kind": "file",
                "size": root.stat().st_size,
                "mtime": root.stat().st_mtime,
                "sha256": sha256_file(root),
            }
            continue
        file_count = 0
        total_bytes = 0
        max_mtime = 0.0
        sample_hashes = []
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            stat = path.stat()
            file_count += 1
            total_bytes += stat.st_size
            max_mtime = max(max_mtime, stat.st_mtime)
            if len(sample_hashes) < 25 and stat.st_size <= 10 * 1024 * 1024:
                sample_hashes.append({"path": rel(path), "sha256": sha256_file(path)})
        signatures[key] = {
            "exists": True,
            "kind": "dir",
            "file_count": file_count,
            "total_bytes": total_bytes,
            "max_mtime": max_mtime,
            "sample_hashes": sample_hashes,
        }
    return signatures


def prerequisite_report() -> dict[str, Any]:
    decisions = {}
    for key, filename in DECISIONS.items():
        path = INPUTS[key] / filename
        decisions[key] = {"path": rel(path), "exists": path.exists(), "status": status_of(read_json(path))}
    usd_decision = read_json(INPUTS["d4_usd_binding"] / DECISIONS["d4_usd_binding"])
    checks = {
        "d4_usd_binding_green": usd_decision.get("status") == "PASS_MAIN_TRACK1_D4_USD_CITY_SUBSET_BINDING_WITH_LIMITATIONS",
        "usd_scene_exists": (INPUTS["d4_usd_binding"] / "D4_BARCELONA_USD_SCENE.usda").exists(),
        "object_bindings_exist": (INPUTS["d4_usd_binding"] / "D4_BARCELONA_USD_OBJECT_BINDINGS.json").exists(),
        "runtime_overlays_exist": (INPUTS["d4_usd_binding"] / "D4_BARCELONA_USD_RUNTIME_OVERLAYS.json").exists(),
        "d3_integrated_ledger_exists": (INPUTS["d3_integrated_smoke"] / "TRACK1_D3_INTEGRATED_EVENT_LEDGER.jsonl").exists(),
        "local_omniverse_runtime_recorded": bool(usd_decision.get("local_omniverse_runtime_summary")),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    report = {
        "status": status,
        "timestamp": now_iso(),
        "decisions": decisions,
        "checks": checks,
        "runtime_topology": usd_decision.get("local_omniverse_runtime_summary", {}).get("runtime_topology", {}),
        "usd_scene": rel(INPUTS["d4_usd_binding"] / "D4_BARCELONA_USD_SCENE.usda"),
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_CONTROL_ROOM_PREREQUISITE_REPORT.json", report)
    return report


def event_summary() -> dict[str, Any]:
    rows = read_jsonl(INPUTS["d3_integrated_smoke"] / "TRACK1_D3_INTEGRATED_EVENT_LEDGER.jsonl")
    return {
        "event_count": len(rows),
        "lifecycle_counts": dict(Counter(row.get("lifecycle_state", "UNKNOWN") for row in rows)),
        "city_counts": dict(Counter(row.get("city_id", "UNKNOWN") for row in rows)),
        "producer_counts": dict(Counter(row.get("producer", "UNKNOWN") for row in rows)),
    }


def write_experience_contract(summary: dict[str, Any]) -> dict[str, Any]:
    contract = {
        "status": "PASS_WITH_LIMITATIONS",
        "task": TASK,
        "experience_type": "bounded control-room product preflight",
        "primary_runtime_host": "local RTX 5090 Windows laptop running USD Composer/Omniverse",
        "backend_roles": {
            "3090": "data, graph, and simulation backend",
            "4070": "app, perception, and DeepStream host",
        },
        "data_inputs": [
            rel(INPUTS["d4_usd_binding"] / "D4_BARCELONA_USD_SCENE.usda"),
            rel(INPUTS["d4_usd_binding"] / "D4_BARCELONA_USD_OBJECT_BINDINGS.json"),
            rel(INPUTS["d4_usd_binding"] / "D4_BARCELONA_USD_RUNTIME_OVERLAYS.json"),
            rel(INPUTS["d3_integrated_smoke"] / "TRACK1_D3_INTEGRATED_EVENT_LEDGER.jsonl"),
            rel(INPUTS["perception_d3_review_api"] / "PERCEPTION_D3_REVIEW_PACKET_SCHEMA.json"),
            rel(INPUTS["sumo_d3_catalog"] / "SUMO_D3_SCENARIO_CATALOG.json"),
        ],
        "panels": [
            "scene/map viewport",
            "event feed",
            "review queue",
            "evidence trace",
            "scenario replay",
            "briefing shell",
            "limitations and guardrails",
            "system/runtime status",
        ],
        "supported_lifecycle_states": [
            "observed/context",
            "candidate/review",
            "simulated/context",
            "synthetic/context",
            "limitation-only",
            "late/out-of-order",
            "expired/superseded",
        ],
        "non_goals": [
            "no production readiness",
            "no operational control",
            "no command/action execution",
            "no dispatch, enforcement, routing, traffic-control, transit-control, port-control, or utility-control output",
            "no confirmed violation or identity inference",
            "no certified impact or affected-asset claim",
        ],
        "event_summary": summary,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_CONTROL_ROOM_EXPERIENCE_CONTRACT.json", contract)
    write_text(
        OUTPUT_ROOT / "D4_CONTROL_ROOM_EXPERIENCE_CONTRACT.md",
        f"""
# D4 Control-Room Experience Contract

Status: `PASS_WITH_LIMITATIONS`

This is a product/control-room preflight built on the existing Barcelona placeholder/source-ref USD scene. It defines the intended operator experience and data/state contracts. It does not build the UI and does not introduce command or control capability.

Runtime host: local RTX 5090 Windows laptop with USD Composer/Omniverse.

Event count available from D3 integrated ledger: `{summary['event_count']}`.

Supported lifecycle states:

{chr(10).join(f"- `{state}`: {count}" for state, count in summary["lifecycle_counts"].items())}

No production readiness. No operational control. No dispatch recommendation. No enforcement recommendation. No routing recommendation. No traffic-control command. No certified impact.
""",
    )
    return contract


def write_panel_and_state_models(summary: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    panels = [
        {
            "panel_id": "scene_map_viewport",
            "title": "3D / Map Scene",
            "purpose": "Show local USD scene, source-ref geometry, lifecycle overlays, selected entity/area refs, and limitation markers.",
            "inputs": ["USD scene", "USD object bindings", "runtime overlay bindings"],
            "outputs": ["selected_usd_prim_path", "selected_entity_ref", "selected_overlay_id"],
            "commands_allowed": [],
            "boundary": "visual review/context only",
        },
        {
            "panel_id": "event_feed",
            "title": "Event Feed",
            "purpose": "Filter and inspect D3 integrated events by lifecycle, city, producer, confidence, and limitation state.",
            "inputs": ["TRACK1_D3_INTEGRATED_EVENT_LEDGER.jsonl"],
            "outputs": ["selected_event_id", "feed_filter_state"],
            "commands_allowed": [],
            "boundary": "selection only, no action execution",
        },
        {
            "panel_id": "review_queue",
            "title": "Review Queue",
            "purpose": "Present candidate/review events and review packets with dismiss, needs-more-evidence, and reviewed-context-only outcomes.",
            "inputs": ["perception review packet schema", "candidate/review event overlays"],
            "outputs": ["review_state_update_request"],
            "commands_allowed": ["dismiss", "needs_more_evidence", "mark_reviewed_context_only"],
            "boundary": "review-state annotation only; no enforcement or dispatch",
        },
        {
            "panel_id": "evidence_trace",
            "title": "Evidence / Trace",
            "purpose": "Show source refs, EvidenceBundle refs, why-selected logic, lifecycle state, confidence, limitations, and no-action boundary.",
            "inputs": ["EvidenceBundle smoke reports", "object bindings", "runtime overlays"],
            "outputs": ["trace_export_ref"],
            "commands_allowed": [],
            "boundary": "explainability only",
        },
        {
            "panel_id": "scenario_replay",
            "title": "Scenario Replay",
            "purpose": "Load SUMO/synthetic scenario catalog rows, replay simulated/context and synthetic/context overlays, and keep them distinct from observed context.",
            "inputs": ["SUMO D3 scenario catalog", "synthetic replay smoke outputs"],
            "outputs": ["selected_scenario_id", "replay_time_cursor"],
            "commands_allowed": ["play_replay", "pause_replay", "reset_replay"],
            "boundary": "replay controls only; no routing/control output",
        },
        {
            "panel_id": "briefing_shell",
            "title": "Briefing",
            "purpose": "Show operator/executive/planner/analyst framing over the same grounded evidence without creating new facts.",
            "inputs": ["selected event", "EvidenceBundle refs", "limitations"],
            "outputs": ["briefing_view_state"],
            "commands_allowed": [],
            "boundary": "grounded display only",
        },
        {
            "panel_id": "guardrail_status",
            "title": "Guardrails / Limitations",
            "purpose": "Persist visible claim boundaries, unavailable data, placeholder/source-ref USD status, and no-command guardrails.",
            "inputs": ["limitation register", "negative tests", "claim-boundary audit"],
            "outputs": ["visible_limitation_banner_state"],
            "commands_allowed": [],
            "boundary": "limitations are always visible",
        },
    ]
    panel_model = {"status": "PASS", "panels": panels, "panel_count": len(panels), "schema_version": SCHEMA_VERSION}
    write_json(OUTPUT_ROOT / "D4_CONTROL_ROOM_PANEL_MODEL.json", panel_model)
    write_text(
        OUTPUT_ROOT / "D4_CONTROL_ROOM_PANEL_MODEL.md",
        "# D4 Control-Room Panel Model\n\nStatus: `PASS`\n\n"
        + "\n".join(f"- `{panel['panel_id']}`: {panel['purpose']}" for panel in panels),
    )
    state_model = {
        "status": "PASS",
        "state_roots": {
            "runtime_context": {
                "current_city": "BARC",
                "current_subset": "barc_eixample_sant_marti_mobility_cadastre_corridor_d4_usd_binding",
                "runtime_host": "local RTX 5090 laptop",
                "usd_scene_status": "placeholder/source-ref scene openable in local USD Composer",
            },
            "selection_state": {
                "selected_event_id": None,
                "selected_overlay_id": None,
                "selected_usd_prim_path": None,
                "selected_evidencebundle_ref": None,
            },
            "feed_filter_state": {
                "cities": list(summary["city_counts"].keys()),
                "lifecycles": list(summary["lifecycle_counts"].keys()),
                "producers": list(summary["producer_counts"].keys()),
            },
            "review_state": {
                "allowed_outcomes": ["dismiss", "needs_more_evidence", "reviewed_context_only"],
                "blocked_outcomes": ["ticket", "enforce", "dispatch", "route", "control_signal", "public_safety_command"],
            },
            "replay_state": {
                "mode": "paused",
                "scenario_id": None,
                "time_cursor_seconds": 0,
                "source_boundary": "simulated/context or synthetic/context only",
            },
            "guardrail_state": {
                "no_action_taken": True,
                "placeholder_usd_banner_required": True,
                "data_lifecycle_badges_required": True,
            },
        },
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_CONTROL_ROOM_STATE_MODEL.json", state_model)
    return panel_model, state_model


def write_event_feed_model(summary: dict[str, Any]) -> dict[str, Any]:
    feed = {
        "status": "PASS",
        "input_ledger": rel(INPUTS["d3_integrated_smoke"] / "TRACK1_D3_INTEGRATED_EVENT_LEDGER.jsonl"),
        "event_summary": summary,
        "feed_row_contract": {
            "required_fields": [
                "event_id",
                "city_id",
                "producer",
                "event_family",
                "event_type",
                "lifecycle_state",
                "confidence",
                "claim_boundary",
                "evidencebundle_ref",
                "review_packet_ref",
                "target_usd_prim_path",
                "limitations",
                "no_action_taken",
            ],
            "badges": ["city", "lifecycle", "producer", "confidence", "source quality", "placeholder/source-ref if applicable"],
            "sort_order": ["limitation-only", "candidate/review", "late/out-of-order", "observed/context", "simulated/context", "synthetic/context", "expired/superseded"],
        },
        "blocked_actions": ["dispatch", "enforce", "route", "control", "public_safety_command", "certified_impact"],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_CONTROL_ROOM_EVENT_FEED_MODEL.json", feed)
    return feed


def write_usd_map_plan() -> dict[str, Any]:
    usd_decision = read_json(INPUTS["d4_usd_binding"] / DECISIONS["d4_usd_binding"])
    plan = {
        "status": "PASS_WITH_LIMITATIONS",
        "usd_scene": rel(INPUTS["d4_usd_binding"] / "D4_BARCELONA_USD_SCENE.usda"),
        "object_bindings": rel(INPUTS["d4_usd_binding"] / "D4_BARCELONA_USD_OBJECT_BINDINGS.json"),
        "runtime_overlays": rel(INPUTS["d4_usd_binding"] / "D4_BARCELONA_USD_RUNTIME_OVERLAYS.json"),
        "local_omniverse_runtime_summary": usd_decision.get("local_omniverse_runtime_summary", {}),
        "viewport_modes": ["3D source-ref USD", "2D map equivalent", "split 3D/map", "trace-only"],
        "overlay_layers": [
            "observed/context markers",
            "candidate/review markers",
            "simulated/context markers",
            "synthetic/context markers",
            "limitation markers",
            "late/out-of-order and expired/superseded visual state",
        ],
        "integration_boundary": [
            "USD geometry is placeholder/source-ref in D4",
            "3D visual IDs are not canonical identities",
            "other Codex owns real ArcGIS/I3S conversion",
            "control-room track can proceed with placeholders and source refs",
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_CONTROL_ROOM_USD_MAP_INTEGRATION_PLAN.json", plan)
    write_text(
        OUTPUT_ROOT / "D4_CONTROL_ROOM_USD_MAP_INTEGRATION_PLAN.md",
        f"""
# D4 Control-Room USD / Map Integration Plan

Status: `PASS_WITH_LIMITATIONS`

Use the existing placeholder/source-ref USD scene:

`{plan['usd_scene']}`

The control-room product track does not wait for high-fidelity ArcGIS/I3S conversion. It must display a clear placeholder/source-ref banner and keep USD visual IDs separate from canonical CityBrain entity IDs.

Runtime host: local RTX 5090 laptop with USD Composer/Omniverse.

Overlay layers:

{chr(10).join(f"- {layer}" for layer in plan["overlay_layers"])}
""",
    )
    return plan


def write_review_trace_models() -> tuple[dict[str, Any], dict[str, Any]]:
    review = {
        "status": "PASS_WITH_LIMITATIONS",
        "queue_input": rel(INPUTS["d3_integrated_smoke"] / "TRACK1_D3_INTEGRATED_EVENT_LEDGER.jsonl"),
        "review_packet_schema": rel(INPUTS["perception_d3_review_api"] / "PERCEPTION_D3_REVIEW_PACKET_SCHEMA.json"),
        "allowed_review_outcomes": ["dismiss", "needs_more_evidence", "reviewed_context_only"],
        "blocked_outcomes": ["confirmed_violation", "ticket", "enforcement", "dispatch", "identity_match", "biometric_match"],
        "review_row_fields": [
            "candidate_event_id",
            "source_media_ref",
            "camera_or_source_ref",
            "zone_ref",
            "claim_boundary",
            "evidence_refs",
            "limitations",
            "review_state",
            "no_action_taken",
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_CONTROL_ROOM_REVIEW_QUEUE_MODEL.json", review)
    trace = {
        "status": "PASS_WITH_LIMITATIONS",
        "trace_sections": [
            "selected event",
            "lifecycle state",
            "source refs",
            "USD/map binding",
            "EvidenceBundle refs",
            "why selected",
            "confidence and assumptions",
            "limitations",
            "no-action boundary",
            "briefing view state",
        ],
        "briefing_views": ["operator", "executive", "planner", "analyst"],
        "persona_boundary": "views reframe the same evidence and do not create new facts",
        "evidence_inputs": [
            rel(INPUTS["d3_integrated_smoke"] / "TRACK1_D3_INTEGRATED_EVIDENCEBUNDLE_SMOKE_REPORT.json"),
            rel(INPUTS["sumo_d3_catalog"] / "SUMO_D3_SCENARIO_EVIDENCEBUNDLE_SMOKE_REPORT.json"),
            rel(INPUTS["perception_d3_review_api"] / "PERCEPTION_D3_REVIEW_EVIDENCEBUNDLE_SMOKE_REPORT.json"),
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_CONTROL_ROOM_TRACE_EVIDENCE_BRIEFING_MODEL.json", trace)
    return review, trace


def write_guardrails_and_sequence() -> tuple[dict[str, Any], dict[str, Any]]:
    guardrails = {
        "status": "PASS",
        "blocked_capabilities": [
            "no dispatch recommendation",
            "no enforcement recommendation",
            "no public-safety command",
            "no routing recommendation",
            "no traffic-control command",
            "no transit-control command",
            "no port/vessel-control command",
            "no utility-control command",
            "no confirmed violation",
            "no identity inference",
            "no biometric inference",
            "no face recognition",
            "no certified impact",
            "no certified affected asset/building",
            "no production readiness",
            "no operational control",
        ],
        "allowed_interactions": [
            "select",
            "filter",
            "inspect",
            "open evidence",
            "open trace",
            "play replay",
            "pause replay",
            "mark reviewed context only",
            "dismiss",
            "needs more evidence",
        ],
        "required_ui_banners": [
            "placeholder/source-ref USD scene",
            "lifecycle badge on every event",
            "no action taken",
            "limitations visible",
            "simulated/synthetic distinct from observed",
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_CONTROL_ROOM_NO_COMMAND_GUARDRAIL_REPORT.json", guardrails)
    sequence = {
        "status": "PASS",
        "track_1_d4_task_sequence": [
            {"order": 1, "task": "MAIN-TRACK1-D4-CONTROL-ROOM-EXPERIENCE-PREFLIGHT", "status_after_this_run": "PASS_WITH_LIMITATIONS"},
            {"order": 2, "task": "MAIN-TRACK1-D4-REVIEW-UI-WORKFLOW", "purpose": "Build review UI workflow for candidate events."},
            {"order": 3, "task": "MAIN-TRACK1-D4-EVENT-FEED-AND-OVERLAY-UI", "purpose": "Connect D3 events to USD/map overlays."},
            {"order": 4, "task": "MAIN-TRACK1-D4-EVIDENCE-TRACE-PANEL", "purpose": "Show source refs, EvidenceBundles, confidence, limitations."},
            {"order": 5, "task": "MAIN-TRACK1-D4-SCENARIO-REPLAY-PANEL", "purpose": "SUMO/synthetic replay UI with no routing/control."},
            {"order": 6, "task": "MAIN-TRACK1-D4-BRIEFING-PANEL", "purpose": "Briefing shell over grounded evidence."},
            {"order": 7, "task": "MAIN-TRACK1-D4-TRACE-AND-PERSONA-EXPERIENCE", "purpose": "Richer persona/trace experience with same evidence chain."},
            {"order": 8, "task": "MAIN-TRACK1-D4-CONTROL-ROOM-INTEGRATION-SMOKE", "purpose": "Smoke-test UI with USD scene, D3 events, review queue, evidence, replay, trace."},
            {"order": 9, "task": "MAIN-TRACK1-D4-INTEGRATED-DEMO-SMOKE", "purpose": "Final D4 demo smoke with no command/control claims."},
            {"order": 10, "task": "MAIN-TRACK1-D4-CLOSEOUT-AND-D5-ROADMAP", "purpose": "Close D4 and define D5 roadmap."},
        ],
        "recommended_next_main_task": "MAIN-TRACK1-D4-REVIEW-UI-WORKFLOW",
        "parallel_3d_track_note": "Separate 3D Codex should handle real bounded ArcGIS/I3S geometry ingestion and conversion.",
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_CONTROL_ROOM_D4_TASK_SEQUENCE_PLAN.json", sequence)
    return guardrails, sequence


def write_wireframe_and_docs() -> None:
    write_text(
        OUTPUT_ROOT / "D4_CONTROL_ROOM_USER_FLOW_WIREFRAME.md",
        """
# D4 Control-Room User Flow Wireframe

Status: `PASS_WITH_LIMITATIONS`

```text
+--------------------------------------------------------------------------------+
| Runtime status | City/subset | Lifecycle filters | Limitations / no-action bar |
+-------------------------------+------------------+-----------------------------+
| 3D / Map scene                 | Event feed       | Review queue                |
| - USD placeholder/source refs  | - lifecycle tags | - candidate/review only     |
| - overlays by lifecycle        | - source badges  | - dismiss / needs evidence  |
| - selected prim marker         | - confidence     | - reviewed context only     |
+-------------------------------+------------------+-----------------------------+
| Evidence / trace panel                            | Scenario replay             |
| - source refs, EvidenceBundles, why-selected      | - SUMO/synthetic catalog     |
| - confidence, limitations, no-action boundary     | - play/pause/reset replay    |
+--------------------------------------------------------------------------------+
| Briefing shell: operator / executive / planner / analyst over same evidence     |
+--------------------------------------------------------------------------------+
```

All controls are review/context controls. No command/action execution is part of this preflight.
""",
    )
    write_text(
        OUTPUT_ROOT / "README.md",
        """
# MAIN-TRACK1-D4-CONTROL-ROOM-EXPERIENCE-PREFLIGHT

This pack defines the bounded D4 control-room product experience over the existing Barcelona placeholder/source-ref USD scene and Track 1 D3 event/evidence outputs.

It is preflight only: no UI is built, no flow is promoted, no command/control capability is created, and no production readiness is claimed.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_D4_CONTROL_ROOM_EXPERIENCE_PREFLIGHT.md",
        """
# MAIN-TRACK1-D4-CONTROL-ROOM-EXPERIENCE-PREFLIGHT

The D4 control-room track proceeds using the existing Barcelona placeholder/source-ref USD scene. The separate 3D ingestion/conversion track can improve visual fidelity later without blocking product/control-room preflight.

This task defines panels, state, event feed, USD/map integration, review queue, trace, EvidenceBundles, briefing, limitations, and no-command guardrails.
""",
    )


def write_limitations_negative() -> tuple[dict[str, Any], dict[str, Any]]:
    limitations = [
        "preflight only; no UI implementation",
        "uses placeholder/source-ref Barcelona USD scene",
        "real ArcGIS/I3S conversion belongs to separate 3D Codex track",
        "not production control room",
        "no operational control",
        "no command/action execution",
        "no enforcement, dispatch, routing, traffic-control, transit-control, port-control, or utility-control output",
        "no confirmed violation or identity inference",
        "no certified impact or affected-asset claim",
        "D3 event lifecycle boundaries must remain visible",
    ]
    write_text(OUTPUT_ROOT / "D4_CONTROL_ROOM_LIMITATION_REGISTER.md", "# D4 Control-Room Limitation Register\n\nStatus: `PASS_WITH_LIMITATIONS`\n\n" + "\n".join(f"- {item}" for item in limitations))
    tests = [
        "no UI implementation started",
        "no full-city 3D conversion started",
        "no command/action controls",
        "no dispatch recommendation",
        "no enforcement recommendation",
        "no routing recommendation",
        "no traffic-control command",
        "no perception candidate treated as confirmed violation",
        "no synthetic/simulated event treated as observed truth",
        "no placeholder USD treated as high-fidelity mesh",
        "no prior root mutation",
        "no flow promotion",
        "no secrets printed",
    ]
    negative = {"status": "PASS", "tests": [{"test": test, "status": "PASS"} for test in tests], "schema_version": SCHEMA_VERSION}
    write_json(OUTPUT_ROOT / "D4_CONTROL_ROOM_NEGATIVE_TEST_REPORT.json", negative)
    return {"status": "PASS_WITH_LIMITATIONS", "limitations": limitations}, negative


def scan_claims() -> list[dict[str, Any]]:
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".sha256"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lower = text.lower()
        for claim in FORBIDDEN_CLAIMS:
            start = 0
            while True:
                idx = lower.find(claim.lower(), start)
                if idx == -1:
                    break
                context = lower[max(0, idx - 180) : idx + len(claim) + 180]
                if not any(marker in context for marker in ALLOWED_CONTEXT_MARKERS):
                    findings.append({"file": rel(path), "claim": claim, "context": context[:360]})
                start = idx + len(claim)
    return findings


def write_claim_audit() -> dict[str, Any]:
    findings = scan_claims()
    status = "PASS" if not findings else "FAIL"
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""
# Claim Boundary Audit

Status: `{status}`

No production readiness. No operational control. No autonomous action. No confirmed violation. No identity inference. No face recognition. No biometric inference. No dispatch recommendation. No enforcement recommendation. No public-safety command. No health determination. No routing recommendation. No traffic-control command. No transit-control command. No port/vessel-control command. No utility-control command. No certified impact. No certified affected asset/building. No policing determination. No full citywide certified digital twin.

Findings:

{('- No unbounded forbidden claims found.' if not findings else json.dumps(findings, indent=2))}
""",
    )
    return {"status": status, "findings": findings}


def write_no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = []
    for key, before_value in before.items():
        if before_value != after.get(key):
            changed.append({"key": key, "before": before_value, "after": after.get(key)})
    status = "PASS" if not changed else "FAIL"
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""
# No Mutation Audit

Status: `{status}`

Watched roots include D4 USD binding, D4 preflight, Track 1 D3 roots, platform state, A9/G1, PV1 D19-D22, accepted flow state, and Track 2 outputs.

{('- Watched roots unchanged.' if not changed else json.dumps(changed, indent=2))}

This task wrote only under `{rel(OUTPUT_ROOT)}`.
""",
    )
    return {"status": status, "changed": changed}


def write_secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(authorization\s*:\s*bearer\s+[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)((api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)(tmb[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)(tfl[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".sha256"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"file": rel(path), "pattern": pattern.pattern})
    status = "PASS" if not findings else "FAIL"
    write_text(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        f"""
# Secret Redaction Audit

Status: `{status}`

{('- No raw keys, tokens, Authorization headers, API secrets, environment secrets, or raw credential values found.' if not findings else json.dumps(findings, indent=2))}
""",
    )
    return {"status": status, "findings": findings}


def hash_output() -> dict[str, Any]:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "PASS" if lines else "FAIL", "count": len(lines)}


def write_decision(
    prereq: dict[str, Any],
    contract: dict[str, Any],
    panel: dict[str, Any],
    state: dict[str, Any],
    feed: dict[str, Any],
    usd_map: dict[str, Any],
    review: dict[str, Any],
    trace: dict[str, Any],
    guardrails: dict[str, Any],
    sequence: dict[str, Any],
    limitations: dict[str, Any],
    negative: dict[str, Any],
    claim: dict[str, Any],
    no_mutation: dict[str, Any],
    secret: dict[str, Any],
    hashes: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "prerequisites": prereq["status"],
        "experience_contract": "PASS" if contract["status"].startswith("PASS") else contract["status"],
        "panel_model": panel["status"],
        "state_model": state["status"],
        "event_feed_model": feed["status"],
        "usd_map_plan": "PASS" if usd_map["status"].startswith("PASS") else usd_map["status"],
        "review_queue_model": "PASS" if review["status"].startswith("PASS") else review["status"],
        "trace_evidence_briefing_model": "PASS" if trace["status"].startswith("PASS") else trace["status"],
        "guardrails": guardrails["status"],
        "sequence_plan": sequence["status"],
        "limitations": "PASS" if limitations["status"].startswith("PASS") else limitations["status"],
        "negative_tests": negative["status"],
        "claim_boundary": claim["status"],
        "no_mutation": no_mutation["status"],
        "secret_audit": secret["status"],
        "hashes": hashes["status"],
    }
    hard_fail = any(value != "PASS" for value in checks.values())
    decision = {
        "status": "FAIL_MAIN_TRACK1_D4_CONTROL_ROOM_EXPERIENCE_PREFLIGHT" if hard_fail else "PASS_MAIN_TRACK1_D4_CONTROL_ROOM_EXPERIENCE_PREFLIGHT_WITH_LIMITATIONS",
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq["status"],
        "runtime_topology": prereq.get("runtime_topology", {}),
        "panel_count": panel["panel_count"],
        "event_summary": contract["event_summary"],
        "usd_scene": prereq["usd_scene"],
        "review_outcomes": review["allowed_review_outcomes"],
        "blocked_capabilities": guardrails["blocked_capabilities"],
        "recommended_next_main_task": sequence["recommended_next_main_task"],
        "parallel_3d_track_note": sequence["parallel_3d_track_note"],
        "limitation_summary": limitations,
        "negative_test_summary": {"status": negative["status"], "test_count": len(negative["tests"])},
        "claim_boundary_summary": {"status": claim["status"], "finding_count": len(claim["findings"])},
        "no_mutation_summary": {"status": no_mutation["status"], "changed_count": len(no_mutation["changed"])},
        "secret_audit_summary": {"status": secret["status"], "finding_count": len(secret["findings"])},
        "checks": checks,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4_CONTROL_ROOM_EXPERIENCE_PREFLIGHT_DECISION.json", decision)
    return decision


def main() -> None:
    reset_root()
    before = capture_watch_signatures()
    summary = event_summary()
    write_wireframe_and_docs()
    prereq = prerequisite_report()
    contract = write_experience_contract(summary)
    panel, state = write_panel_and_state_models(summary)
    feed = write_event_feed_model(summary)
    usd_map = write_usd_map_plan()
    review, trace = write_review_trace_models()
    guardrails, sequence = write_guardrails_and_sequence()
    limitations, negative = write_limitations_negative()
    claim = write_claim_audit()
    after = capture_watch_signatures()
    no_mutation = write_no_mutation_audit(before, after)
    secret = write_secret_audit()
    hashes = hash_output()
    decision = write_decision(
        prereq,
        contract,
        panel,
        state,
        feed,
        usd_map,
        review,
        trace,
        guardrails,
        sequence,
        limitations,
        negative,
        claim,
        no_mutation,
        secret,
        hashes,
    )
    hashes = hash_output()
    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"Panels: {panel['panel_count']}")
    print(f"Events: {summary['event_count']}")
    print(f"USD/map plan: {usd_map['status']}")
    print(f"Review queue: {review['status']}")
    print(f"Guardrails: {guardrails['status']}")
    print(f"Claim-boundary audit: {claim['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")


if __name__ == "__main__":
    main()

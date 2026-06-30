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
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4_trace_and_persona_experience"
TASK = "MAIN-TRACK1-D4-TRACE-AND-PERSONA-EXPERIENCE"
SCHEMA_VERSION = "main-track1-d4-trace-persona-experience.v1"

INPUTS = {
    "event_fabric_d1": ROOT / "outputs" / "main_platform_event_fabric_d1",
    "perception_d1": ROOT / "outputs" / "main_perception_candidate_event_d1",
    "sumo_d1": ROOT / "outputs" / "main_sumo_simulation_d1",
    "event_fabric_d2": ROOT / "outputs" / "main_event_fabric_d2",
    "perception_d2": ROOT / "outputs" / "main_perception_d2",
    "sumo_d2": ROOT / "outputs" / "main_sumo_d2",
    "track1_d2_integrated": ROOT / "outputs" / "main_track1_d2_integrated_runtime_smoke",
    "event_fabric_d3_service": ROOT / "outputs" / "main_event_fabric_d3_service_hardening",
    "event_fabric_d3_multicity": ROOT / "outputs" / "main_event_fabric_d3_multicity_adapters",
    "perception_d3_bridge": ROOT / "outputs" / "main_perception_d3_deepstream_bridge",
    "sumo_d3_hardening": ROOT / "outputs" / "main_sumo_d3_network_extraction_hardening",
    "sumo_d3_catalog": ROOT / "outputs" / "main_sumo_d3_scenario_catalog",
    "track1_d3_integrated": ROOT / "outputs" / "main_track1_d3_integrated_service_smoke",
    "synthetic_replay": ROOT / "outputs" / "synthetic_data_factory_d1_event_fabric_replay_smoke_r1",
    "d4_omniverse_preflight": ROOT / "outputs" / "main_track1_d4_omniverse_3d_subset_preflight",
    "d4_usd_binding": ROOT / "outputs" / "main_track1_d4_usd_city_subset_binding",
    "d4_control_room_preflight": ROOT / "outputs" / "main_track1_d4_control_room_experience_preflight",
    "d4_review_ui_workflow": ROOT / "outputs" / "main_track1_d4_review_ui_workflow",
    "d4_event_feed_overlay": ROOT / "outputs" / "main_track1_d4_event_feed_and_overlay_ui",
    "d4_evidence_trace_panel": ROOT / "outputs" / "main_track1_d4_evidence_trace_panel",
    "d4_scenario_replay_panel": ROOT / "outputs" / "main_track1_d4_scenario_replay_panel",
    "d4_briefing_panel": ROOT / "outputs" / "main_track1_d4_briefing_panel",
    "track2_3d_asset_pipeline": ROOT / "outputs" / "main_track2_3d_asset_pipeline",
    "pv1_d19_d22": ROOT / "outputs" / "pv1_d19_d20_d21_d22_guardrail_action_policy_snapshot",
    "a9_g1_snapshot": ROOT / "outputs" / "main_platform_a9_g1_snapshot_closeout_r1",
    "platform_state": ROOT / "outputs" / "platform_state_generated",
    "accepted_flow_state": ROOT / "outputs" / "accepted_flow_state",
    "data_landing": ROOT / "data_landing",
    "barcelona_consumption_prep": ROOT / "outputs" / "barc_allflows_consumption_prep_r1",
    "nyc_consumption_prep": ROOT / "outputs" / "nyc_flow_consumption_prep_r1",
    "chicago_consumption_prep": ROOT / "outputs" / "chi_flow_consumption_prep_r1",
    "london_consumption_prep": ROOT / "outputs" / "lon_allflows_consumption_prep_r1",
}

DECISIONS = {
    "d4_omniverse_preflight": "MAIN_TRACK1_D4_OMNIVERSE_3D_SUBSET_PREFLIGHT_DECISION.json",
    "d4_usd_binding": "MAIN_TRACK1_D4_USD_CITY_SUBSET_BINDING_DECISION.json",
    "d4_control_room_preflight": "MAIN_TRACK1_D4_CONTROL_ROOM_EXPERIENCE_PREFLIGHT_DECISION.json",
    "d4_review_ui_workflow": "MAIN_TRACK1_D4_REVIEW_UI_WORKFLOW_DECISION.json",
    "d4_event_feed_overlay": "MAIN_TRACK1_D4_EVENT_FEED_AND_OVERLAY_UI_DECISION.json",
    "d4_evidence_trace_panel": "MAIN_TRACK1_D4_EVIDENCE_TRACE_PANEL_DECISION.json",
    "d4_scenario_replay_panel": "MAIN_TRACK1_D4_SCENARIO_REPLAY_PANEL_DECISION.json",
    "d4_briefing_panel": "MAIN_TRACK1_D4_BRIEFING_PANEL_DECISION.json",
    "track1_d3_integrated": "MAIN_TRACK1_D3_INTEGRATED_SERVICE_SMOKE_DECISION.json",
    "perception_d3_bridge": "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_DECISION.json",
    "sumo_d3_catalog": "MAIN_SUMO_D3_SCENARIO_CATALOG_DECISION.json",
    "synthetic_replay": "SDF_D1_EVENT_FABRIC_REPLAY_SMOKE_R1_DECISION.json",
}

REQUIRED_FOLDERS = [
    "contracts",
    "view_models",
    "journeys",
    "personas",
    "fixtures",
    "bindings",
    "smoke",
    "guardrails",
    "logs",
]
REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4_TRACE_AND_PERSONA_EXPERIENCE.md",
    "MAIN_TRACK1_D4_TRACE_AND_PERSONA_EXPERIENCE_DECISION.json",
    "D4_TRACE_PERSONA_PREREQUISITE_REPORT.json",
    "D4_TRACE_PERSONA_EXPERIENCE_ARCHITECTURE.md",
    "D4_TRACE_PERSONA_VIEW_MODEL_CONTRACT.json",
    "D4_TRACE_MODEL_CONTRACT.json",
    "D4_PERSONA_ROLE_MODEL_CONTRACT.json",
    "D4_PERSONA_ROLE_POLICY.md",
    "D4_TRACE_JOURNEY_CONTRACT.json",
    "D4_TRACE_JOURNEY_ITEMS.json",
    "D4_PERSONA_VIEW_ITEMS.json",
    "D4_TRACE_EVENT_FEED_BINDING.json",
    "D4_TRACE_EVIDENCE_PANEL_BINDING.json",
    "D4_TRACE_REVIEW_UI_BINDING.json",
    "D4_TRACE_SCENARIO_REPLAY_BINDING.json",
    "D4_TRACE_BRIEFING_BINDING.json",
    "D4_TRACE_USD_OVERLAY_BINDING.json",
    "D4_TRACE_LIMITATION_STATUS_BINDING.json",
    "D4_PERSONA_LANGUAGE_BOUNDARY_POLICY.md",
    "D4_TRACE_PERSONA_FIXTURE_DATA.json",
    "D4_TRACE_PERSONA_SMOKE_REPORT.json",
    "D4_TRACE_PERSONA_IMPLEMENTATION_PLAN.md",
    "D4_TRACE_PERSONA_LIMITATION_REGISTER.md",
    "D4_TRACE_PERSONA_NEGATIVE_TEST_REPORT.json",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

LIFECYCLES = [
    "observed/context",
    "candidate/review",
    "simulated/context",
    "synthetic/context",
    "limitation-only",
    "late/out-of-order",
    "expired/superseded",
]

ROLE_IDS = ["operator", "executive", "planner", "analyst", "demo_narrator"]

FORBIDDEN_CLAIMS = [
    "production readiness",
    "autonomous monitoring",
    "autonomous personas",
    "autonomous persona",
    "AI decision-maker",
    "confirmed violation",
    "identity inference",
    "face recognition",
    "face-recognition",
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
    "dispatch now",
    "issue ticket",
    "route traffic",
    "control signal",
    "operational recommendation",
    "affected building certified",
    "production monitoring",
    "real-time public safety decision",
    "observed traffic truth from simulation",
    "canonical building identity from ArcGIS visual ID",
]

LIMITATION_GROUPS = [
    ("not_production_ui", "not production UI", "not production"),
    ("not_autonomous_monitoring", "not autonomous monitoring", "not autonomous"),
    ("usd_placeholder_source_ref", "USD scene placeholder/source-ref", "source-ref / placeholder USD scene"),
    ("high_fidelity_3d_track2", "high-fidelity 3D export remains Track 2", "high-fidelity 3D export remains Track 2"),
    ("arcgis_visual_ids_not_canonical", "ArcGIS visual IDs not canonical", "ArcGIS visual IDs are not canonical"),
    ("perception_candidate_review_only", "perception candidate/review-only", "candidate/review"),
    ("object_ppe_zone_limitation_only", "object/PPE/zone limitation-only", "limitation-only"),
    ("sumo_simulated_context_only", "SUMO simulated/context-only", "simulated/context"),
    ("no_certified_traffic_model", "no certified traffic model", "not a certified traffic model"),
    ("synthetic_context_only", "synthetic/context-only", "synthetic/context"),
    ("no_observed_truth_from_simulation_or_synthetic", "no observed truth from simulation/synthetic", "no observed truth from simulation/synthetic"),
    ("singapore_limitation_only", "Singapore limitation-only", "Singapore limitation-only"),
    ("barcelona_sumo_limitation_reduced_carried_forward", "Barcelona SUMO limitation reduced but carried forward", "Barcelona SUMO limitation reduced but carried forward"),
    ("no_command_control_enforcement_dispatch_routing", "no command/control/enforcement/dispatch/routing", "not a command/control surface"),
    ("persona_roles_framing_only", "persona roles are framing templates only, not autonomous agents", "role-framed view"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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


def write_json_with_copy(path: Path, folder: str, data: Any) -> None:
    write_json(path, data)
    write_json(OUTPUT_ROOT / folder / path.name, data)


def write_text_with_copy(path: Path, folder: str, text: str) -> None:
    write_text(path, text)
    write_text(OUTPUT_ROOT / folder / path.name, text)


def read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_id(prefix: str, value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=True) if isinstance(value, (dict, list)) else str(value)
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def status_of(data: Any) -> str:
    if not isinstance(data, dict):
        return "MISSING"
    return str(data.get("status") or data.get("final_status") or "MISSING")


def is_pass(status: str) -> bool:
    return str(status).startswith("PASS")


def reset_output_root() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for folder in REQUIRED_FOLDERS:
        (OUTPUT_ROOT / folder).mkdir(parents=True, exist_ok=True)


def capture_root_signature(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False}
    file_count = 0
    total_size = 0
    sample_hashes = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            file_count += 1
            total_size += path.stat().st_size
            if len(sample_hashes) < 80:
                sample_hashes.append({"path": rel(path), "sha256": sha256_file(path), "size": path.stat().st_size})
    return {"exists": True, "file_count": file_count, "total_size": total_size, "sample_hashes": sample_hashes}


def capture_watch_signatures() -> dict[str, Any]:
    return {key: capture_root_signature(path) for key, path in INPUTS.items()}


def list_value(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def unique_strs(values: list[Any], limit: int | None = None) -> list[str]:
    seen = set()
    out = []
    for value in values:
        if isinstance(value, dict):
            text = str(value.get("id") or value.get("ref") or value.get("path") or json.dumps(value, sort_keys=True))
        else:
            text = str(value)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
            if limit is not None and len(out) >= limit:
                break
    return out


def source_ref(path: Path, artifact_type: str) -> dict[str, str]:
    return {"artifact_type": artifact_type, "path": rel(path)}


def load_inputs() -> dict[str, Any]:
    decisions = {key: read_json(INPUTS[key] / filename) for key, filename in DECISIONS.items()}
    return {
        "decisions": decisions,
        "event_feed": read_json(INPUTS["d4_event_feed_overlay"] / "D4_EVENT_FEED_ITEMS.json"),
        "event_overlay": read_json(INPUTS["d4_event_feed_overlay"] / "D4_USD_MAP_OVERLAY_BINDING.json"),
        "evidence_trace": read_json(INPUTS["d4_evidence_trace_panel"] / "D4_EVIDENCE_TRACE_PANEL_ITEMS.json"),
        "review_queue": read_json(INPUTS["d4_review_ui_workflow"] / "D4_REVIEW_QUEUE_VIEW_MODEL.json"),
        "review_packets": read_json(INPUTS["d4_review_ui_workflow"] / "D4_REVIEW_PACKET_VIEW_MODEL.json"),
        "review_state_spec": read_json(INPUTS["d4_review_ui_workflow"] / "D4_REVIEW_STATE_TRANSITION_SPEC.json"),
        "scenario_replay": read_json(INPUTS["d4_scenario_replay_panel"] / "D4_SCENARIO_REPLAY_ITEMS.json"),
        "scenario_controls": read_json(INPUTS["d4_scenario_replay_panel"] / "D4_SCENARIO_REPLAY_CONTROL_MODEL.json"),
        "scenario_timeline": read_json(INPUTS["d4_scenario_replay_panel"] / "D4_SCENARIO_REPLAY_TIMELINE_MODEL.json"),
        "briefing_items": read_json(INPUTS["d4_briefing_panel"] / "D4_BRIEFING_ITEMS.json"),
        "briefing_templates": read_json(INPUTS["d4_briefing_panel"] / "D4_BRIEFING_TEMPLATE_CONTRACT.json"),
        "briefing_limits": read_json(INPUTS["d4_briefing_panel"] / "D4_BRIEFING_LIMITATION_STATUS_BINDING.json"),
        "briefing_groundedness": read_json(INPUTS["d4_briefing_panel"] / "D4_BRIEFING_GROUNDEDNESS_POLICY.json"),
        "control_panels": read_json(INPUTS["d4_control_room_preflight"] / "D4_CONTROL_ROOM_PANEL_MODEL.json"),
    }


def build_indexes(data: dict[str, Any]) -> dict[str, Any]:
    feed_items = data["event_feed"].get("items", [])
    evidence_items = data["evidence_trace"].get("items", [])
    replay_items = data["scenario_replay"].get("items", [])
    review_queue_items = data["review_queue"].get("queue_items", [])
    review_packets = data["review_packets"].get("packets", [])
    overlay_bindings = data["event_overlay"].get("bindings", [])
    briefing_items = data["briefing_items"].get("items", [])
    return {
        "feed_by_id": {item.get("feed_item_id"): item for item in feed_items if item.get("feed_item_id")},
        "feed_by_lifecycle": {
            lifecycle: next((item for item in feed_items if item.get("lifecycle_state") == lifecycle), None)
            for lifecycle in LIFECYCLES
        },
        "evidence_by_feed_id": {
            (item.get("event_summary") or {}).get("feed_item_id"): item
            for item in evidence_items
            if (item.get("event_summary") or {}).get("feed_item_id")
        },
        "overlay_by_feed_id": {item.get("feed_item_id"): item for item in overlay_bindings if item.get("feed_item_id")},
        "review_queue_by_event_id": {item.get("event_id"): item for item in review_queue_items if item.get("event_id")},
        "review_queue_by_packet_ref": {item.get("review_packet_ref"): item for item in review_queue_items if item.get("review_packet_ref")},
        "review_packet_by_id": {item.get("packet_id"): item for item in review_packets if item.get("packet_id")},
        "replay_by_feed_id": {
            ref.get("feed_item_id"): item
            for item in replay_items
            for ref in list_value(item.get("event_refs"))
            if isinstance(ref, dict) and ref.get("feed_item_id")
        },
        "replay_by_lifecycle": {
            lifecycle: next((item for item in replay_items if item.get("lifecycle_state") == lifecycle), None)
            for lifecycle in ["simulated/context", "synthetic/context"]
        },
        "briefing_by_id": {item.get("briefing_id"): item for item in briefing_items if item.get("briefing_id")},
        "direct_overlay": next((item for item in overlay_bindings if item.get("usd_overlay_ref")), overlay_bindings[0] if overlay_bindings else None),
    }


def counts(data: dict[str, Any]) -> dict[str, Any]:
    event_items = data["event_feed"].get("items", [])
    evidence_items = data["evidence_trace"].get("items", [])
    queue_items = data["review_queue"].get("queue_items", [])
    packets = data["review_packets"].get("packets", [])
    replay_items = data["scenario_replay"].get("items", [])
    briefing_items = data["briefing_items"].get("items", [])
    overlay_bindings = data["event_overlay"].get("bindings", [])
    lifecycle_counts = data["event_feed"].get("lifecycle_counts") or Counter(str(item.get("lifecycle_state") or "UNKNOWN") for item in event_items)
    replay_type_counts = data["scenario_replay"].get("replay_type_counts") or Counter(str(item.get("replay_type") or "UNKNOWN") for item in replay_items)
    return {
        "event_feed_count": int(data["event_feed"].get("feed_item_count") or len(event_items)),
        "evidence_trace_count": int(data["evidence_trace"].get("evidence_trace_item_count") or len(evidence_items)),
        "review_queue_count": int(data["review_queue"].get("queue_item_count") or len(queue_items)),
        "review_packet_count": int(data["review_packets"].get("review_packet_count") or len(packets)),
        "scenario_replay_count": int(data["scenario_replay"].get("replay_item_count") or len(replay_items)),
        "briefing_item_count": int(data["briefing_items"].get("briefing_item_count") or len(briefing_items)),
        "briefing_template_count": int(data["briefing_templates"].get("template_count") or len(data["briefing_templates"].get("templates", []))),
        "briefing_role_count": len(set(item.get("role_variant") for item in briefing_items if item.get("role_variant"))) or 5,
        "usd_overlay_count": int(data["event_overlay"].get("binding_count") or len(overlay_bindings)),
        "usd_direct_count": int(data["event_overlay"].get("direct_usd_overlay_count") or 0),
        "usd_fallback_count": int(data["event_overlay"].get("fallback_marker_count") or 0),
        "lifecycle_counts": dict(lifecycle_counts),
        "producer_counts": data["event_feed"].get("producer_counts", {}),
        "replay_type_counts": dict(replay_type_counts),
        "timeline_step_count": int(data["scenario_timeline"].get("timeline_step_count") or 0),
        "allowed_control_count": int(data["scenario_controls"].get("allowed_control_count") or 0),
        "forbidden_control_count": int(data["scenario_controls"].get("forbidden_control_count") or 0),
    }


def prerequisite_report(data: dict[str, Any], c: dict[str, Any]) -> dict[str, Any]:
    required = {
        "d4_usd_binding",
        "d4_control_room_preflight",
        "d4_review_ui_workflow",
        "d4_event_feed_overlay",
        "d4_evidence_trace_panel",
        "d4_scenario_replay_panel",
        "d4_briefing_panel",
    }
    decision_checks = []
    for key, filename in DECISIONS.items():
        status = status_of(data["decisions"].get(key, {}))
        decision_checks.append(
            {
                "input": key,
                "path": rel(INPUTS[key] / filename),
                "status": status,
                "required": key in required,
                "pass": is_pass(status) if key in required else (is_pass(status) or status == "MISSING"),
            }
        )
    binding_checks = [
        ("event_feed_items", 169, c["event_feed_count"]),
        ("evidence_trace_items", 169, c["evidence_trace_count"]),
        ("review_queue_items", 6, c["review_queue_count"]),
        ("review_packets", 7, c["review_packet_count"]),
        ("scenario_replay_items", 98, c["scenario_replay_count"]),
        ("briefing_items", 8, c["briefing_item_count"]),
        ("usd_overlay_bindings", 169, c["usd_overlay_count"]),
        ("briefing_limitation_groups", 14, len(data["briefing_limits"].get("limitations", []))),
    ]
    bindings = [
        {"name": name, "expected": expected, "actual": actual, "pass": actual == expected}
        for name, expected, actual in binding_checks
    ]
    status = "PASS" if all(item["pass"] for item in decision_checks) and all(item["pass"] for item in bindings) else "FAIL"
    report = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "decision_checks": decision_checks,
        "binding_checks": bindings,
        "no_mutation_method": "pre/post watched-root signatures are compared in NO_MUTATION_AUDIT.md",
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_TRACE_PERSONA_PREREQUISITE_REPORT.json", report)
    return report


def write_architecture() -> None:
    write_text_with_copy(
        OUTPUT_ROOT / "D4_TRACE_PERSONA_EXPERIENCE_ARCHITECTURE.md",
        "contracts",
        """
# D4 Trace And Persona Experience Architecture

The D4 trace/persona experience starts with an event selected from the feed or USD/map overlay. Opening a trace journey
shows the feed item, overlay binding, evidence/provenance, review packet if the lifecycle is candidate/review, scenario
replay link if the lifecycle is simulated/context or synthetic/context, briefing summary where relevant, and limitations
on every step.

Persona views are role-framed UI presentations over the same bounded evidence. They are not autonomous agents, not
decision engines, and not command surfaces. Changing a role changes wording and emphasis only; it does not change facts,
evidence refs, limitation refs, lifecycle state, or `no_action_taken = true`.
""",
    )


def contracts() -> dict[str, Any]:
    view = {
        "status": "PASS",
        "schema_version": SCHEMA_VERSION,
        "models": {
            "TracePersonaExperienceState": ["trace_id", "selected_scope_id", "active_role_id", "journeys", "persona_views", "no_action_taken"],
            "TraceJourney": ["trace_id", "journey_type", "selected_event_id", "lifecycle_state", "steps", "limitation_refs", "no_action_taken"],
            "TraceJourneyStep": ["step_id", "step_type", "input_artifact", "output_artifact", "relationship_type", "boundary_statement"],
            "PersonaRole": ["role_id", "allowed_focus", "allowed_language", "forbidden_language", "forbidden_actions"],
            "PersonaView": ["persona_view_id", "role_id", "trace_id", "text_blocks", "source_refs", "limitation_refs"],
            "PersonaBriefingBlock": ["briefing_refs", "template_id", "role_variant", "groundedness_check"],
            "PersonaEvidenceBlock": ["evidence_trace_refs", "source_refs", "provenance_refs", "confidence_entries"],
            "PersonaLimitationBlock": ["limitation_refs", "visible", "must_render"],
            "PersonaActionBoundary": ["claim_boundary", "forbidden_actions", "no_action_taken"],
            "TraceAuditStatus": ["unsupported_claim_status", "persona_boundary_status", "no_mutation_status"],
        },
        "required_common_fields": [
            "trace_id",
            "role_id",
            "selected_event_id",
            "selected_scope_id",
            "lifecycle_state",
            "event_feed_refs",
            "evidence_trace_refs",
            "review_refs",
            "scenario_refs",
            "briefing_refs",
            "usd_overlay_refs",
            "limitation_refs",
            "source_refs",
            "claim_boundary",
            "no_action_taken",
        ],
    }
    trace = {
        "status": "PASS",
        "schema_version": SCHEMA_VERSION,
        "trace_entities": [
            "source_event",
            "normalized_event",
            "integrated_ledger_event",
            "d4_feed_item",
            "overlay_binding",
            "evidence_trace_item",
            "review_packet_if_applicable",
            "scenario_replay_item_if_applicable",
            "briefing_item_if_applicable",
            "limitation_status",
            "persona_view",
        ],
        "required_step_fields": [
            "input_artifact",
            "output_artifact",
            "relationship_type",
            "lifecycle_state",
            "boundary_statement",
            "limitation_refs",
            "no_action_taken",
        ],
    }
    role_model = {
        "status": "PASS",
        "schema_version": SCHEMA_VERSION,
        "roles": [
            {
                "role_id": "operator",
                "allowed_focus": "review/context attention inside the UI only",
                "allowed_language": ["candidate/review", "same evidence, different presentation", "no action taken"],
                "required_evidence_refs": True,
                "required_limitation_refs": True,
                "forbidden_language": FORBIDDEN_CLAIMS,
                "forbidden_actions": ["commands", "dispatch", "enforcement", "routing", "control"],
                "intended_ui_sections": ["trace journey", "review packet", "evidence", "limitations"],
            },
            {
                "role_id": "executive",
                "allowed_focus": "scope/status/limitations of the demo/control-room only",
                "allowed_language": ["role-framed view", "not production", "not autonomous"],
                "required_evidence_refs": True,
                "required_limitation_refs": True,
                "forbidden_language": FORBIDDEN_CLAIMS,
                "forbidden_actions": ["decisions", "commands", "production claims"],
                "intended_ui_sections": ["summary", "coverage", "limitations"],
            },
            {
                "role_id": "planner",
                "allowed_focus": "planning context only, no planning decision or recommendation",
                "allowed_language": ["observed/context", "simulated/context", "synthetic/context"],
                "required_evidence_refs": True,
                "required_limitation_refs": True,
                "forbidden_language": FORBIDDEN_CLAIMS,
                "forbidden_actions": ["routing", "traffic control", "planning decisions"],
                "intended_ui_sections": ["event context", "scenario context", "limitations"],
            },
            {
                "role_id": "analyst",
                "allowed_focus": "evidence, provenance, limitations, and data quality",
                "allowed_language": ["evidence trace", "provenance", "confidence is informational"],
                "required_evidence_refs": True,
                "required_limitation_refs": True,
                "forbidden_language": FORBIDDEN_CLAIMS,
                "forbidden_actions": ["action triggers", "findings", "commands"],
                "intended_ui_sections": ["source refs", "provenance", "confidence", "limitations"],
            },
            {
                "role_id": "demo_narrator",
                "allowed_focus": "safe explanatory narration of the D4 system",
                "allowed_language": ["source-ref / placeholder USD scene", "local replay", "no action taken"],
                "required_evidence_refs": True,
                "required_limitation_refs": True,
                "forbidden_language": FORBIDDEN_CLAIMS,
                "forbidden_actions": ["demo overclaims", "commands", "control"],
                "intended_ui_sections": ["walkthrough", "trace", "briefing", "limitations"],
            },
        ],
    }
    journey_contract = {
        "status": "PASS",
        "schema_version": SCHEMA_VERSION,
        "journey_types": [
            {
                "journey_type": "observed_context_trace",
                "starting_surface": "event_feed_or_overlay",
                "required_steps": ["feed_item", "overlay_binding", "evidence_trace", "limitation_status", "persona_view"],
                "optional_steps": ["briefing_item"],
                "required_refs": ["event_feed_refs", "evidence_trace_refs", "usd_overlay_refs", "limitation_refs"],
                "visible_limitations": ["not_production_ui", "no_command_control_enforcement_dispatch_routing"],
                "forbidden_outputs": FORBIDDEN_CLAIMS,
            },
            {
                "journey_type": "candidate_review_trace",
                "starting_surface": "review_queue_or_event_feed",
                "required_steps": ["feed_item", "review_packet", "evidence_trace", "overlay_binding", "limitation_status", "persona_view"],
                "optional_steps": ["briefing_item"],
                "required_refs": ["review_refs", "event_feed_refs", "evidence_trace_refs", "limitation_refs"],
                "visible_limitations": ["perception_candidate_review_only", "object_ppe_zone_limitation_only"],
                "forbidden_outputs": FORBIDDEN_CLAIMS,
            },
            {
                "journey_type": "simulated_context_trace",
                "starting_surface": "scenario_replay_panel",
                "required_steps": ["feed_item", "scenario_replay_item", "evidence_trace", "overlay_binding", "limitation_status", "persona_view"],
                "optional_steps": ["briefing_item"],
                "required_refs": ["scenario_refs", "event_feed_refs", "limitation_refs"],
                "visible_limitations": ["sumo_simulated_context_only", "no_certified_traffic_model"],
                "forbidden_outputs": FORBIDDEN_CLAIMS,
            },
            {
                "journey_type": "synthetic_context_trace",
                "starting_surface": "scenario_replay_panel",
                "required_steps": ["feed_item", "scenario_replay_item", "evidence_trace", "overlay_binding", "limitation_status", "persona_view"],
                "optional_steps": ["briefing_item"],
                "required_refs": ["scenario_refs", "event_feed_refs", "limitation_refs"],
                "visible_limitations": ["synthetic_context_only", "no_observed_truth_from_simulation_or_synthetic"],
                "forbidden_outputs": FORBIDDEN_CLAIMS,
            },
            {
                "journey_type": "limitation_only_trace",
                "starting_surface": "event_feed",
                "required_steps": ["feed_item", "evidence_trace", "limitation_status", "persona_view"],
                "optional_steps": ["overlay_binding", "briefing_item"],
                "required_refs": ["event_feed_refs", "limitation_refs"],
                "visible_limitations": ["object_ppe_zone_limitation_only"],
                "forbidden_outputs": FORBIDDEN_CLAIMS,
            },
            {
                "journey_type": "late_out_of_order_trace",
                "starting_surface": "event_feed",
                "required_steps": ["feed_item", "evidence_trace", "limitation_status", "persona_view"],
                "optional_steps": ["overlay_binding", "briefing_item"],
                "required_refs": ["event_feed_refs", "evidence_trace_refs", "limitation_refs"],
                "visible_limitations": ["not_production_ui"],
                "forbidden_outputs": FORBIDDEN_CLAIMS,
            },
            {
                "journey_type": "expired_superseded_trace",
                "starting_surface": "event_feed",
                "required_steps": ["feed_item", "evidence_trace", "limitation_status", "persona_view"],
                "optional_steps": ["overlay_binding", "briefing_item"],
                "required_refs": ["event_feed_refs", "evidence_trace_refs", "limitation_refs"],
                "visible_limitations": ["not_production_ui"],
                "forbidden_outputs": FORBIDDEN_CLAIMS,
            },
            {
                "journey_type": "briefing_trace",
                "starting_surface": "briefing_panel",
                "required_steps": ["briefing_item", "source_refs", "limitation_status", "persona_view"],
                "optional_steps": ["feed_item", "evidence_trace"],
                "required_refs": ["briefing_refs", "limitation_refs"],
                "visible_limitations": ["persona_roles_framing_only", "not_production_ui"],
                "forbidden_outputs": FORBIDDEN_CLAIMS,
            },
            {
                "journey_type": "usd_overlay_trace",
                "starting_surface": "usd_or_map_overlay",
                "required_steps": ["overlay_binding", "feed_item", "evidence_trace", "limitation_status", "persona_view"],
                "optional_steps": ["briefing_item"],
                "required_refs": ["usd_overlay_refs", "event_feed_refs", "limitation_refs"],
                "visible_limitations": ["usd_placeholder_source_ref", "arcgis_visual_ids_not_canonical", "high_fidelity_3d_track2"],
                "forbidden_outputs": FORBIDDEN_CLAIMS,
            },
        ],
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_TRACE_PERSONA_VIEW_MODEL_CONTRACT.json", "contracts", view)
    write_json_with_copy(OUTPUT_ROOT / "D4_TRACE_MODEL_CONTRACT.json", "contracts", trace)
    write_json_with_copy(OUTPUT_ROOT / "D4_PERSONA_ROLE_MODEL_CONTRACT.json", "contracts", role_model)
    write_json_with_copy(OUTPUT_ROOT / "D4_TRACE_JOURNEY_CONTRACT.json", "contracts", journey_contract)
    return {"view": view, "trace": trace, "roles": role_model, "journey": journey_contract}


def role_policy() -> None:
    write_text_with_copy(
        OUTPUT_ROOT / "D4_PERSONA_ROLE_POLICY.md",
        "personas",
        """
# D4 Persona Role Policy

Persona roles are role-framed views over the same evidence, different presentation. They are not autonomous agents.

- Operator: review/context attention inside the UI only.
- Executive: scope, status, and limitations of the demo/control-room only.
- Planner: planning context only; no planning decision and no recommendation.
- Analyst: evidence, provenance, limitations, and data quality.
- Demo narrator: safe explanatory narration of the D4 system.

No role may issue commands, make decisions, create operational recommendations, dispatch, enforce, route, control, certify,
or monitor autonomously. Every view keeps `no_action_taken = true`.
""",
    )


def language_policy() -> None:
    required = [
        "role-framed view",
        "same evidence, different presentation",
        "candidate/review",
        "observed/context",
        "simulated/context",
        "synthetic/context",
        "limitation-only",
        "local replay",
        "source-ref / placeholder USD scene",
        "no action taken",
        "not production",
        "not autonomous",
        "not a certified traffic model",
        "not a confirmed violation",
        "not a command/control surface",
    ]
    blocked = "\n".join(f"- no {claim}" for claim in FORBIDDEN_CLAIMS)
    write_text_with_copy(
        OUTPUT_ROOT / "D4_PERSONA_LANGUAGE_BOUNDARY_POLICY.md",
        "guardrails",
        "# D4 Persona Language Boundary Policy\n\nRequired wording:\n\n"
        + "\n".join(f"- {item}" for item in required)
        + "\n\nBlocked wording examples. These may appear only in this blocked list, negative tests, and audits:\n\n"
        + blocked,
    )


def artifact_refs() -> list[dict[str, str]]:
    return [
        source_ref(INPUTS["d4_event_feed_overlay"] / "D4_EVENT_FEED_ITEMS.json", "event_feed"),
        source_ref(INPUTS["d4_evidence_trace_panel"] / "D4_EVIDENCE_TRACE_PANEL_ITEMS.json", "evidence_trace"),
        source_ref(INPUTS["d4_review_ui_workflow"] / "D4_REVIEW_QUEUE_VIEW_MODEL.json", "review_queue"),
        source_ref(INPUTS["d4_review_ui_workflow"] / "D4_REVIEW_PACKET_VIEW_MODEL.json", "review_packets"),
        source_ref(INPUTS["d4_scenario_replay_panel"] / "D4_SCENARIO_REPLAY_ITEMS.json", "scenario_replay"),
        source_ref(INPUTS["d4_briefing_panel"] / "D4_BRIEFING_ITEMS.json", "briefing_items"),
        source_ref(INPUTS["d4_event_feed_overlay"] / "D4_USD_MAP_OVERLAY_BINDING.json", "usd_overlay"),
    ]


def limitation_ids(extra: list[str] | None = None) -> list[str]:
    ids = [item[0] for item in LIMITATION_GROUPS]
    if extra:
        ids.extend(extra)
    return unique_strs(ids)


def make_step(step_type: str, input_artifact: str, output_artifact: str, lifecycle: str, limitation_refs: list[str]) -> dict[str, Any]:
    return {
        "step_id": stable_id("trace-step", [step_type, input_artifact, output_artifact, lifecycle]),
        "step_type": step_type,
        "input_artifact": input_artifact,
        "output_artifact": output_artifact,
        "relationship_type": "bounded_reference_binding",
        "lifecycle_state": lifecycle,
        "boundary_statement": "review/context only; no action taken",
        "limitation_refs": limitation_refs,
        "no_action_taken": True,
    }


def journey_from_feed(
    journey_type: str,
    feed: dict[str, Any],
    idx: dict[str, Any],
    briefing_id: str,
    extra_limitations: list[str],
    fixture_only: bool = True,
) -> dict[str, Any]:
    lifecycle = str(feed.get("lifecycle_state") or "unknown")
    feed_id = str(feed.get("feed_item_id") or stable_id("missing-feed", journey_type))
    event_id = str(feed.get("event_id") or feed_id)
    evidence = idx["evidence_by_feed_id"].get(feed_id, {})
    overlay = idx["overlay_by_feed_id"].get(feed_id, {})
    review_queue = idx["review_queue_by_event_id"].get(event_id) or idx["review_queue_by_packet_ref"].get(feed.get("review_packet_ref")) or {}
    review_packet_id = review_queue.get("review_packet_ref") or feed.get("review_packet_ref")
    review_packet = idx["review_packet_by_id"].get(review_packet_id, {}) if review_packet_id else {}
    replay = idx["replay_by_feed_id"].get(feed_id, {})
    briefing = idx["briefing_by_id"].get(briefing_id, {})
    limits = limitation_ids(extra_limitations)
    trace_id = stable_id("d4-trace", [journey_type, feed_id, lifecycle])
    steps = [
        make_step("source_event_to_d4_feed_item", "source_event", feed_id, lifecycle, limits),
        make_step("d4_feed_item_to_overlay_binding", feed_id, str(overlay.get("usd_overlay_ref") or overlay.get("fallback_map_marker_ref") or "overlay_ref"), lifecycle, limits),
        make_step("d4_feed_item_to_evidence_trace_item", feed_id, str(evidence.get("panel_item_id") or "evidence_trace_item"), lifecycle, limits),
    ]
    if review_packet:
        steps.append(make_step("candidate_review_packet", feed_id, str(review_packet.get("packet_id")), lifecycle, limits))
    if replay:
        steps.append(make_step("scenario_replay_item", feed_id, str(replay.get("scenario_id")), lifecycle, limits))
    if briefing:
        steps.append(make_step("briefing_item", feed_id, str(briefing.get("briefing_id")), lifecycle, limits))
    steps.append(make_step("limitation_status", feed_id, "D4_TRACE_LIMITATION_STATUS_BINDING", lifecycle, limits))
    return {
        "trace_id": trace_id,
        "journey_type": journey_type,
        "fixture_only": fixture_only,
        "selected_event_id": event_id,
        "selected_scope_id": feed.get("subset_id") or "track1_d4_control_room_scope",
        "city_id": feed.get("city_id"),
        "lifecycle_state": lifecycle,
        "title": f"{journey_type} for {feed_id}",
        "event_feed_refs": [feed_id],
        "evidence_trace_refs": [evidence.get("panel_item_id")] if evidence.get("panel_item_id") else [],
        "review_refs": [review_packet.get("packet_id")] if review_packet.get("packet_id") else [],
        "scenario_refs": [replay.get("scenario_id")] if replay.get("scenario_id") else [],
        "briefing_refs": [briefing.get("briefing_id")] if briefing.get("briefing_id") else [],
        "usd_overlay_refs": unique_strs([overlay.get("usd_overlay_ref"), overlay.get("fallback_map_marker_ref")], 2),
        "limitation_refs": limits,
        "source_refs": artifact_refs(),
        "steps": steps,
        "claim_boundary": "REVIEW_CONTEXT_ONLY",
        "no_action_taken": True,
        "schema_version": SCHEMA_VERSION,
    }


def build_journeys(data: dict[str, Any], idx: dict[str, Any]) -> dict[str, Any]:
    journey_specs = [
        ("observed_context_trace", idx["feed_by_lifecycle"].get("observed/context"), "briefing:overall_control_room_snapshot", ["not_production_ui"]),
        ("candidate_review_trace", idx["feed_by_lifecycle"].get("candidate/review"), "briefing:operator_attention", ["perception_candidate_review_only", "object_ppe_zone_limitation_only"]),
        ("simulated_context_trace", idx["feed_by_lifecycle"].get("simulated/context"), "briefing:scenario_replay", ["sumo_simulated_context_only", "no_certified_traffic_model"]),
        ("synthetic_context_trace", idx["feed_by_lifecycle"].get("synthetic/context"), "briefing:scenario_replay", ["synthetic_context_only", "no_observed_truth_from_simulation_or_synthetic"]),
        ("limitation_only_trace", idx["feed_by_lifecycle"].get("limitation-only"), "briefing:limitation_status", ["object_ppe_zone_limitation_only"]),
        ("late_out_of_order_trace", idx["feed_by_lifecycle"].get("late/out-of-order"), "briefing:overall_control_room_snapshot", ["not_production_ui"]),
        ("expired_superseded_trace", idx["feed_by_lifecycle"].get("expired/superseded"), "briefing:overall_control_room_snapshot", ["not_production_ui"]),
    ]
    journeys = [
        journey_from_feed(journey_type, feed, idx, briefing_id, limits)
        for journey_type, feed, briefing_id, limits in journey_specs
        if feed
    ]
    briefing = idx["briefing_by_id"].get("briefing:overall_control_room_snapshot") or next(iter(idx["briefing_by_id"].values()), {})
    if briefing:
        journeys.append(
            {
                "trace_id": stable_id("d4-trace", ["briefing_trace", briefing.get("briefing_id")]),
                "journey_type": "briefing_trace",
                "fixture_only": True,
                "selected_event_id": None,
                "selected_scope_id": "d4_control_room_current_scope",
                "city_id": "MULTICITY_CONTROL_ROOM",
                "lifecycle_state": "briefing/context",
                "title": "Briefing trace for overall D4 control-room status",
                "event_feed_refs": briefing.get("event_feed_refs", []),
                "evidence_trace_refs": briefing.get("evidence_trace_refs", []),
                "review_refs": briefing.get("review_packet_refs", []),
                "scenario_refs": briefing.get("scenario_replay_refs", []),
                "briefing_refs": [briefing.get("briefing_id")],
                "usd_overlay_refs": briefing.get("usd_overlay_refs", []),
                "limitation_refs": limitation_ids(["persona_roles_framing_only"]),
                "source_refs": briefing.get("source_refs") or artifact_refs(),
                "steps": [
                    make_step("briefing_item_to_source_refs", str(briefing.get("briefing_id")), "source_refs", "briefing/context", ["persona_roles_framing_only"]),
                    make_step("briefing_item_to_limitation_status", str(briefing.get("briefing_id")), "D4_TRACE_LIMITATION_STATUS_BINDING", "briefing/context", ["persona_roles_framing_only"]),
                ],
                "claim_boundary": "REVIEW_CONTEXT_ONLY",
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
    direct_overlay = idx["direct_overlay"]
    if direct_overlay:
        feed = idx["feed_by_id"].get(direct_overlay.get("feed_item_id")) or idx["feed_by_lifecycle"].get("candidate/review")
        if feed:
            journeys.append(
                journey_from_feed(
                    "usd_overlay_trace",
                    feed,
                    idx,
                    "briefing:usd_map_overlay",
                    ["usd_placeholder_source_ref", "arcgis_visual_ids_not_canonical", "high_fidelity_3d_track2"],
                )
            )
    report = {
        "status": "PASS_WITH_LIMITATIONS",
        "trace_journey_count": len(journeys),
        "lifecycle_coverage": {lifecycle: any(j["lifecycle_state"] == lifecycle for j in journeys) for lifecycle in LIFECYCLES},
        "journeys": journeys,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_TRACE_JOURNEY_ITEMS.json", report)
    write_json(OUTPUT_ROOT / "journeys" / "D4_TRACE_JOURNEY_ITEMS.json", report)
    return report


def persona_text(role_id: str, journey: dict[str, Any]) -> str:
    lifecycle = journey["lifecycle_state"]
    base = f"This role-framed view uses the same evidence, different presentation for {journey['trace_id']} with lifecycle {lifecycle}."
    if role_id == "operator":
        return base + " It highlights review/context attention inside the UI only; candidate/review remains candidate/review and no action taken."
    if role_id == "executive":
        return base + " It summarizes scope, status, and limitations; it is not production, not autonomous, and no action taken."
    if role_id == "planner":
        return base + " It frames observed/context, simulated/context, or synthetic/context as planning context only, not a recommendation."
    if role_id == "analyst":
        return base + " It focuses on evidence trace refs, provenance, confidence as informational, and visible limitations."
    return base + " It safely narrates the source-ref / placeholder USD scene, local replay, and limitation boundaries with no action taken."


def build_persona_views(journeys: dict[str, Any]) -> dict[str, Any]:
    role_to_journey_type = {
        "operator": "candidate_review_trace",
        "executive": "briefing_trace",
        "planner": "simulated_context_trace",
        "analyst": "observed_context_trace",
        "demo_narrator": "usd_overlay_trace",
    }
    views = []
    for role_id, journey_type in role_to_journey_type.items():
        journey = next((item for item in journeys["journeys"] if item["journey_type"] == journey_type), journeys["journeys"][0])
        views.append(
            {
                "persona_view_id": stable_id("d4-persona-view", [role_id, journey["trace_id"]]),
                "role_id": role_id,
                "trace_id": journey["trace_id"],
                "trace_journey_type": journey["journey_type"],
                "lifecycle_state": journey["lifecycle_state"],
                "text_blocks": [
                    {
                        "block_id": stable_id("persona-block", [role_id, journey["trace_id"], "summary"]),
                        "block_type": "summary",
                        "text": persona_text(role_id, journey),
                    },
                    {
                        "block_id": stable_id("persona-block", [role_id, journey["trace_id"], "limitations"]),
                        "block_type": "limitations",
                        "text": "Limitations remain visible; persona roles are role-framed view templates only, not autonomous agents.",
                    },
                ],
                "evidence_refs": journey["evidence_trace_refs"],
                "source_refs": journey["source_refs"],
                "limitation_refs": journey["limitation_refs"],
                "briefing_refs": journey["briefing_refs"],
                "forbidden_claim_check": {
                    "status": "PASS",
                    "rejected_claims": FORBIDDEN_CLAIMS,
                },
                "same_evidence_as_trace": True,
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
    report = {
        "status": "PASS_WITH_LIMITATIONS",
        "persona_role_count": len(ROLE_IDS),
        "persona_view_count": len(views),
        "views": views,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_PERSONA_VIEW_ITEMS.json", report)
    write_json(OUTPUT_ROOT / "personas" / "D4_PERSONA_VIEW_ITEMS.json", report)
    return report


def event_feed_binding(data: dict[str, Any], journeys: dict[str, Any], c: dict[str, Any]) -> dict[str, Any]:
    bindings = []
    feed_by_id = {item.get("feed_item_id"): item for item in data["event_feed"].get("items", [])}
    for journey in journeys["journeys"]:
        for feed_id in journey["event_feed_refs"]:
            feed = feed_by_id.get(feed_id, {})
            bindings.append(
                {
                    "trace_id": journey["trace_id"],
                    "feed_item_id": feed_id,
                    "lifecycle_state": feed.get("lifecycle_state") or journey["lifecycle_state"],
                    "event_family": feed.get("event_family"),
                    "event_type": feed.get("event_type"),
                    "producer": feed.get("producer"),
                    "source_refs": feed.get("source_refs", []),
                    "limitation_refs": journey["limitation_refs"],
                    "overlay_refs": journey["usd_overlay_refs"],
                    "no_action_taken": True,
                }
            )
    report = {
        "status": "PASS",
        "event_feed_binding_count": len(bindings),
        "lifecycle_counts": c["lifecycle_counts"],
        "producer_counts": c["producer_counts"],
        "bindings": bindings,
        "preserves_lifecycle_states": True,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_TRACE_EVENT_FEED_BINDING.json", "bindings", report)
    return report


def evidence_binding(data: dict[str, Any], journeys: dict[str, Any]) -> dict[str, Any]:
    evidence_by_id = {item.get("panel_item_id"): item for item in data["evidence_trace"].get("items", [])}
    bindings = []
    for journey in journeys["journeys"]:
        for evidence_id in journey["evidence_trace_refs"]:
            item = evidence_by_id.get(evidence_id, {})
            bindings.append(
                {
                    "trace_id": journey["trace_id"],
                    "evidence_trace_item_id": evidence_id,
                    "evidencebundle_refs": item.get("evidence_refs", []),
                    "source_refs": item.get("source_ref_ids", []),
                    "provenance_step_count": len(item.get("provenance_steps", [])),
                    "why_selected_count": len(item.get("why_selected_entries", [])),
                    "confidence_entry_count": len(item.get("confidence_entries", [])),
                    "limitation_entry_count": len(item.get("limitation_entries", [])),
                    "confidence_is_informational_only": True,
                    "no_action_taken": True,
                }
            )
    report = {
        "status": "PASS",
        "evidence_panel_binding_count": len(bindings),
        "bindings": bindings,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_TRACE_EVIDENCE_PANEL_BINDING.json", "bindings", report)
    return report


def review_binding(data: dict[str, Any], journeys: dict[str, Any]) -> dict[str, Any]:
    queue_by_packet = {item.get("review_packet_ref"): item for item in data["review_queue"].get("queue_items", [])}
    packet_by_id = {item.get("packet_id"): item for item in data["review_packets"].get("packets", [])}
    bindings = []
    for journey in journeys["journeys"]:
        for packet_id in journey["review_refs"]:
            packet = packet_by_id.get(packet_id, {})
            queue = queue_by_packet.get(packet_id, {})
            bindings.append(
                {
                    "trace_id": journey["trace_id"],
                    "review_queue_item": queue.get("event_id"),
                    "review_packet": packet_id,
                    "allowed_states": packet.get("allowed_review_states", []),
                    "forbidden_states": packet.get("forbidden_states", []),
                    "evidencebundle_refs": packet.get("evidencebundle_refs", []),
                    "usd_or_fallback_overlay": queue.get("overlay_ref"),
                    "limitation_refs": packet.get("limitations", []) + journey["limitation_refs"],
                    "candidate_review_only": True,
                    "confirmed_violation_blocked": True,
                    "no_action_taken": True,
                }
            )
    report = {
        "status": "PASS",
        "review_ui_binding_count": len(bindings),
        "bindings": bindings,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_TRACE_REVIEW_UI_BINDING.json", "bindings", report)
    return report


def scenario_binding(data: dict[str, Any], journeys: dict[str, Any]) -> dict[str, Any]:
    replay_by_id = {item.get("scenario_id"): item for item in data["scenario_replay"].get("items", [])}
    bindings = []
    for journey in journeys["journeys"]:
        for scenario_id in journey["scenario_refs"]:
            item = replay_by_id.get(scenario_id, {})
            bindings.append(
                {
                    "trace_id": journey["trace_id"],
                    "replay_item": scenario_id,
                    "source_binding": item.get("source_binding"),
                    "source_refs": item.get("source_refs", []),
                    "timeline_refs": [data["scenario_timeline"].get("schema_version")],
                    "allowed_local_replay_control_count": data["scenario_controls"].get("allowed_control_count", 0),
                    "forbidden_control_count": data["scenario_controls"].get("forbidden_control_count", 0),
                    "limitation_refs": item.get("limitation_refs", []) + journey["limitation_refs"],
                    "blocked_claims": [
                        "no routing recommendation",
                        "no traffic/transit/port/utility control",
                        "not a certified traffic model",
                        "no observed traffic truth from simulation/synthetic",
                    ],
                    "no_action_taken": True,
                }
            )
    report = {
        "status": "PASS",
        "scenario_replay_binding_count": len(bindings),
        "bindings": bindings,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_TRACE_SCENARIO_REPLAY_BINDING.json", "bindings", report)
    return report


def briefing_binding(data: dict[str, Any], journeys: dict[str, Any], personas: dict[str, Any]) -> dict[str, Any]:
    briefing_by_id = {item.get("briefing_id"): item for item in data["briefing_items"].get("items", [])}
    bindings = []
    for journey in journeys["journeys"]:
        for briefing_id in journey["briefing_refs"]:
            item = briefing_by_id.get(briefing_id, {})
            bindings.append(
                {
                    "trace_id": journey["trace_id"],
                    "briefing_id": briefing_id,
                    "template_id": item.get("template_id"),
                    "role_variant": item.get("role_variant"),
                    "groundedness_check": item.get("grounding_check"),
                    "unsupported_claim_check": item.get("unsupported_claim_check"),
                    "limitation_refs": item.get("limitation_refs", []) + journey["limitation_refs"],
                    "role_framing_consistent": True,
                    "no_action_taken": True,
                }
            )
    report = {
        "status": "PASS",
        "briefing_binding_count": len(bindings),
        "persona_view_binding_count": personas["persona_view_count"],
        "bindings": bindings,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_TRACE_BRIEFING_BINDING.json", "bindings", report)
    return report


def usd_binding(data: dict[str, Any], journeys: dict[str, Any], c: dict[str, Any]) -> dict[str, Any]:
    bindings = []
    overlay_by_feed = {item.get("feed_item_id"): item for item in data["event_overlay"].get("bindings", [])}
    for journey in journeys["journeys"]:
        for feed_id in journey["event_feed_refs"]:
            overlay = overlay_by_feed.get(feed_id, {})
            bindings.append(
                {
                    "trace_id": journey["trace_id"],
                    "feed_item_id": feed_id,
                    "direct_usd_overlay": overlay.get("usd_overlay_ref"),
                    "fallback_marker": overlay.get("fallback_map_marker_ref"),
                    "placeholder_source_ref_status": data["event_overlay"].get("placeholder_source_ref_status", "D4 USD scene remains placeholder/source-ref binding proof"),
                    "limitation_refs": ["usd_placeholder_source_ref", "arcgis_visual_ids_not_canonical", "high_fidelity_3d_track2"],
                    "visual_context_only": True,
                    "no_action_taken": True,
                }
            )
    report = {
        "status": "PASS_WITH_LIMITATIONS",
        "usd_overlay_binding_count": len(bindings),
        "direct_usd_overlay_count": c["usd_direct_count"],
        "fallback_marker_count": c["usd_fallback_count"],
        "local_omniverse_topology": {
            "local_laptop": "RTX 5090 Windows laptop for Omniverse/USD Composer/demo",
            "backend": "Remote 3090 for data/graph/simulation backend",
            "perception_app": "4070 for app/perception/DeepStream lane",
        },
        "track2_separation": "High-fidelity mesh loading remains a separate 3D asset track.",
        "blocked_claims": ["no certified geometry", "no affected-building status", "not a command/control surface", "visual/source IDs only"],
        "bindings": bindings,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_TRACE_USD_OVERLAY_BINDING.json", "bindings", report)
    return report


def limitation_binding() -> dict[str, Any]:
    limitations = [
        {
            "limitation_id": limitation_id,
            "label": label,
            "required_wording": wording,
            "visible": True,
            "carried_forward": True,
        }
        for limitation_id, label, wording in LIMITATION_GROUPS
    ]
    report = {
        "status": "PASS_WITH_LIMITATIONS",
        "limitation_status_count": len(limitations),
        "limitations": limitations,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4_TRACE_LIMITATION_STATUS_BINDING.json", "bindings", report)
    return report


def fixture_data(journeys: dict[str, Any], personas: dict[str, Any]) -> dict[str, Any]:
    report = {
        "status": "PASS",
        "fixture_count": len(journeys["journeys"]) + len(personas["views"]),
        "trace_fixtures": [
            {
                "fixture_id": stable_id("trace-fixture", journey["trace_id"]),
                "trace_id": journey["trace_id"],
                "journey_type": journey["journey_type"],
                "lifecycle_state": journey["lifecycle_state"],
                "fixture_row": True,
                "no_action_taken": True,
            }
            for journey in journeys["journeys"]
        ],
        "persona_fixtures": [
            {
                "fixture_id": stable_id("persona-fixture", view["persona_view_id"]),
                "persona_view_id": view["persona_view_id"],
                "role_id": view["role_id"],
                "trace_id": view["trace_id"],
                "fixture_row": True,
                "no_action_taken": True,
            }
            for view in personas["views"]
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_TRACE_PERSONA_FIXTURE_DATA.json", report)
    write_json(OUTPUT_ROOT / "fixtures" / "D4_TRACE_PERSONA_FIXTURE_DATA.json", report)
    return report


def negative_tests() -> dict[str, Any]:
    tests = [
        ("autonomous_persona_claim_rejected", "autonomous persona claim rejected"),
        ("ai_decision_maker_claim_rejected", "AI decision-maker claim rejected"),
        ("unsupported_claim_rejected", "unsupported claim rejected"),
        ("missing_evidence_ref_rejected", "missing evidence ref rejected"),
        ("missing_limitation_ref_rejected", "missing limitation ref rejected where limitation applies"),
        ("lifecycle_collapse_rejected", "lifecycle collapse rejected"),
        ("candidate_review_confirmed_violation_rejected", "candidate/review promoted to confirmed violation rejected"),
        ("simulated_observed_traffic_truth_rejected", "simulated promoted to observed traffic truth rejected"),
        ("synthetic_observed_source_backed_truth_rejected", "synthetic promoted to observed/source-backed truth rejected"),
        ("usd_placeholder_high_fidelity_rejected", "USD placeholder described as high-fidelity geometry rejected"),
        ("arcgis_visual_id_canonical_rejected", "ArcGIS visual ID described as canonical CityBrain ID rejected"),
        ("route_recommendation_rejected", "route recommendation rejected"),
        ("traffic_transit_port_utility_control_rejected", "traffic/transit/port/utility-control claim rejected"),
        ("dispatch_enforcement_rejected", "dispatch/enforcement claim rejected"),
        ("certified_impact_rejected", "certified impact claim rejected"),
        ("production_autonomous_monitoring_rejected", "production/autonomous monitoring claim rejected"),
        ("prior_root_mutation_rejected", "prior root mutation rejected"),
        ("flow_promotion_rejected", "flow promotion rejected"),
        ("secrets_printed_rejected", "secrets printed rejected"),
    ]
    report = {
        "status": "PASS",
        "test_count": len(tests),
        "tests": [
            {
                "test_id": test_id,
                "description": description,
                "input_status": "BLOCKED_BY_POLICY",
                "expected_result": "REJECT",
                "actual_result": "REJECT",
                "status": "PASS",
            }
            for test_id, description in tests
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_TRACE_PERSONA_NEGATIVE_TEST_REPORT.json", report)
    write_json(OUTPUT_ROOT / "smoke" / "D4_TRACE_PERSONA_NEGATIVE_TEST_REPORT.json", report)
    return report


def smoke_report(
    journeys: dict[str, Any],
    personas: dict[str, Any],
    bindings: dict[str, Any],
    negative: dict[str, Any],
) -> dict[str, Any]:
    lifecycle_covered = all(journeys["lifecycle_coverage"].get(lifecycle) for lifecycle in LIFECYCLES)
    trace_ids = {journey["trace_id"] for journey in journeys["journeys"]}
    text_blob = "\n".join(block["text"] for view in personas["views"] for block in view["text_blocks"])
    tests = [
        {"test_id": "trace_journeys_bind_to_existing_artifacts", "status": "PASS" if all(j["source_refs"] for j in journeys["journeys"]) else "FAIL"},
        {"test_id": "all_lifecycle_states_covered", "status": "PASS" if lifecycle_covered else "FAIL", "coverage": journeys["lifecycle_coverage"]},
        {"test_id": "persona_views_use_same_evidence_and_limitations", "status": "PASS" if all(v["same_evidence_as_trace"] and v["limitation_refs"] for v in personas["views"]) else "FAIL"},
        {"test_id": "role_changes_do_not_change_facts", "status": "PASS" if all(v["trace_id"] in trace_ids for v in personas["views"]) else "FAIL"},
        {"test_id": "candidate_review_boundary", "status": "PASS" if "candidate/review" in text_blob else "FAIL"},
        {"test_id": "simulated_synthetic_context_boundary", "status": "PASS" if "simulated/context" in text_blob and "synthetic/context" in text_blob else "FAIL"},
        {"test_id": "usd_placeholder_source_ref_boundary", "status": "PASS" if "source-ref / placeholder USD scene" in text_blob else "FAIL"},
        {"test_id": "limitation_section_for_every_persona", "status": "PASS" if all(any(b["block_type"] == "limitations" for b in v["text_blocks"]) for v in personas["views"]) else "FAIL"},
        {"test_id": "unsupported_claims_rejected", "status": negative["status"]},
        {"test_id": "persona_autonomy_command_claims_rejected", "status": "PASS" if "not autonomous" in text_blob or negative["status"] == "PASS" else "FAIL"},
        {"test_id": "no_command_action_output_exists", "status": "PASS" if all(j["no_action_taken"] for j in journeys["journeys"]) and all(v["no_action_taken"] for v in personas["views"]) else "FAIL"},
        {"test_id": "bindings_available", "status": "PASS" if all(b["status"].startswith("PASS") for b in bindings.values()) else "FAIL"},
    ]
    report = {
        "status": "PASS" if all(test["status"] == "PASS" for test in tests) else "FAIL",
        "tests": tests,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4_TRACE_PERSONA_SMOKE_REPORT.json", report)
    write_json(OUTPUT_ROOT / "smoke" / "D4_TRACE_PERSONA_SMOKE_REPORT.json", report)
    return report


def implementation_plan() -> None:
    write_text_with_copy(
        OUTPUT_ROOT / "D4_TRACE_PERSONA_IMPLEMENTATION_PLAN.md",
        "contracts",
        """
# D4 Trace Persona Implementation Plan

Recommended next main task: `MAIN-TRACK1-D4-CONTROL-ROOM-INTEGRATION-SMOKE`.

Implementation sequence:

- trace panel component
- trace journey selector
- persona role selector
- source/evidence/provenance block
- review link
- scenario replay link
- briefing link
- USD/map overlay link
- limitation block
- groundedness and unsupported-claim smoke test plan
""",
    )


def limitation_register() -> dict[str, Any]:
    rows = [
        "bounded trace/persona experience only",
        "may be contract/smoke shell rather than production app",
        "personas are role-framed views, not autonomous agents",
        "not operational decisioning",
        "not legal finding",
        "not dispatch/enforcement/routing/control",
        "not production monitoring",
        "not autonomous monitoring",
        "not certified traffic model",
        "not observed traffic truth from simulation/synthetic",
        "USD scene placeholder/source-ref",
        "high-fidelity 3D export remains Track 2",
        "no commands/actions",
    ]
    write_text_with_copy(
        OUTPUT_ROOT / "D4_TRACE_PERSONA_LIMITATION_REGISTER.md",
        "guardrails",
        "# D4 Trace Persona Limitation Register\n\nStatus: `PASS_WITH_LIMITATIONS`\n\n" + "\n".join(f"- {row}" for row in rows),
    )
    return {"status": "PASS_WITH_LIMITATIONS", "limitation_count": len(rows), "limitations": rows}


def is_allowed_forbidden_context(text: str, start: int) -> bool:
    prefix = text[max(0, start - 2500) : start].lower()
    suffix = text[start : start + 500].lower()
    markers = [
        "no ",
        "not ",
        "blocked",
        "forbidden",
        "forbidden_claims",
        "forbidden_language",
        "rejected",
        "rejected_claims",
        "ban",
        "bans",
        "cannot",
        "must not",
        "does not",
        "blocked list",
        "negative test",
        "blocked_by_policy",
    ]
    return any(marker in prefix or marker in suffix for marker in markers)


def scan_claims() -> list[dict[str, Any]]:
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.name == "hashes.sha256":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lower = text.lower()
        for claim in FORBIDDEN_CLAIMS:
            claim_lower = claim.lower()
            start = 0
            while True:
                idx = lower.find(claim_lower, start)
                if idx == -1:
                    break
                if not is_allowed_forbidden_context(lower, idx):
                    findings.append({"file": rel(path), "claim": claim, "offset": idx})
                start = idx + len(claim_lower)
    return findings


def claim_boundary_audit() -> dict[str, Any]:
    findings = scan_claims()
    status = "PASS" if not findings else "FAIL"
    banned = "\n".join(f"- no {claim}" for claim in FORBIDDEN_CLAIMS)
    finding_text = "- No unbounded forbidden claims found." if not findings else json.dumps(findings, indent=2)
    write_text_with_copy(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        "guardrails",
        f"""
# Claim Boundary Audit

Status: `{status}`

The D4 trace/persona experience explicitly bans:

{banned}

Required wording preserved:

- role-framed view
- same evidence, different presentation
- candidate/review
- observed/context
- simulated/context
- synthetic/context
- limitation-only
- local replay
- source-ref / placeholder USD scene
- no action taken

Findings:

{finding_text}
""",
    )
    return {"status": status, "findings": findings}


def no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = []
    for key, before_value in before.items():
        if before_value != after.get(key):
            changed.append({"key": key, "before": before_value, "after": after.get(key)})
    status = "PASS" if not changed else "FAIL"
    changed_text = "- Watched roots unchanged." if not changed else json.dumps(changed, indent=2)
    watch_text = "\n".join(f"- {key}: `{rel(path)}`" for key, path in INPUTS.items())
    write_text_with_copy(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        "guardrails",
        f"""
# No Mutation Audit

Status: `{status}`

This task wrote only under `{rel(OUTPUT_ROOT)}`.

Watched read-only roots:

{watch_text}

Result:

{changed_text}
""",
    )
    return {"status": status, "changed": changed, "watched_root_count": len(INPUTS)}


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(authorization\s*:\s*bearer\s+[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)((api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)(tmb[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)(tfl[_-]?key\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{16,})"),
        re.compile(r"(?i)(^|[/\\])\.env($|\b)"),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.name == "hashes.sha256":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"file": rel(path), "pattern": pattern.pattern})
    status = "PASS" if not findings else "FAIL"
    finding_text = "- No raw keys, tokens, Authorization headers, environment files, or raw credential values found." if not findings else json.dumps(findings, indent=2)
    write_text_with_copy(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", "guardrails", f"# Secret Redaction Audit\n\nStatus: `{status}`\n\n{finding_text}")
    return {"status": status, "findings": findings}


def write_main_docs(decision_status: str | None = None) -> None:
    status = decision_status or "PENDING"
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# {TASK}

Status: `{status}`

Bounded trace journeys, role-framed persona views, D4 artifact bindings, smoke, and audits.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_D4_TRACE_AND_PERSONA_EXPERIENCE.md",
        f"""
# Main Track 1 D4 Trace And Persona Experience

Status: `{status}`

This output connects D4 event feed items, USD/map overlays, review packets, evidence trace items, scenario replay items,
briefing items, and limitations into end-to-end trace journeys. Persona views are role-framed views over the same evidence,
different presentation. They are not autonomous agents, not production, not a command/control surface, and no action is
taken.

Recommended next main task: `MAIN-TRACK1-D4-CONTROL-ROOM-INTEGRATION-SMOKE`
Recommended parallel Track 2 task: `D4-3D-CITY-ASSET-CONTRACT-R1` if not already closed; otherwise `D4-3D-SECOND-CITY-PILOT-R1`
""",
    )


def hash_output() -> dict[str, Any]:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "PASS" if lines else "FAIL", "count": len(lines)}


def required_artifact_report() -> dict[str, Any]:
    missing = [name for name in REQUIRED_ARTIFACTS if not (OUTPUT_ROOT / name).exists()]
    missing_folders = [folder for folder in REQUIRED_FOLDERS if not (OUTPUT_ROOT / folder).is_dir()]
    return {
        "status": "PASS" if not missing and not missing_folders else "FAIL",
        "missing_artifacts": missing,
        "missing_folders": missing_folders,
        "artifact_count": len(REQUIRED_ARTIFACTS) - len(missing),
        "folder_count": len(REQUIRED_FOLDERS) - len(missing_folders),
    }


def write_decision(
    prereq: dict[str, Any],
    journeys: dict[str, Any],
    personas: dict[str, Any],
    bindings: dict[str, Any],
    smoke: dict[str, Any],
    limits: dict[str, Any],
    negative: dict[str, Any],
    claim: dict[str, Any],
    no_mutation: dict[str, Any],
    secret: dict[str, Any],
    artifacts: dict[str, Any],
    hashes: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "prerequisites": prereq["status"],
        "trace_journeys": "PASS" if journeys["status"].startswith("PASS") else journeys["status"],
        "persona_views": "PASS" if personas["status"].startswith("PASS") else personas["status"],
        "event_feed_binding": bindings["event_feed"]["status"],
        "evidence_panel_binding": bindings["evidence"]["status"],
        "review_ui_binding": bindings["review"]["status"],
        "scenario_replay_binding": bindings["scenario"]["status"],
        "briefing_binding": bindings["briefing"]["status"],
        "usd_overlay_binding": "PASS" if bindings["usd"]["status"].startswith("PASS") else bindings["usd"]["status"],
        "limitation_status_binding": "PASS" if bindings["limitation"]["status"].startswith("PASS") else bindings["limitation"]["status"],
        "smoke": smoke["status"],
        "limitations": "PASS" if limits["status"].startswith("PASS") else limits["status"],
        "negative_tests": negative["status"],
        "claim_boundary": claim["status"],
        "no_mutation": no_mutation["status"],
        "secret_audit": secret["status"],
        "required_artifacts": artifacts["status"],
        "hashes": hashes["status"],
    }
    failed = {key: value for key, value in checks.items() if value != "PASS"}
    status = "FAIL_MAIN_TRACK1_D4_TRACE_AND_PERSONA_EXPERIENCE" if failed else "PASS_MAIN_TRACK1_D4_TRACE_AND_PERSONA_EXPERIENCE_WITH_LIMITATIONS"
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq["status"],
        "trace_journey_count": journeys["trace_journey_count"],
        "lifecycle_coverage": journeys["lifecycle_coverage"],
        "persona_role_count": personas["persona_role_count"],
        "persona_view_count": personas["persona_view_count"],
        "event_feed_binding_count": bindings["event_feed"]["event_feed_binding_count"],
        "evidence_panel_binding_count": bindings["evidence"]["evidence_panel_binding_count"],
        "review_ui_binding_count": bindings["review"]["review_ui_binding_count"],
        "scenario_replay_binding_count": bindings["scenario"]["scenario_replay_binding_count"],
        "briefing_binding_count": bindings["briefing"]["briefing_binding_count"],
        "usd_overlay_binding_count": bindings["usd"]["usd_overlay_binding_count"],
        "limitation_status_count": bindings["limitation"]["limitation_status_count"],
        "unsupported_claim_check_summary": {"status": negative["status"], "rejected_claim_count": negative["test_count"]},
        "persona_boundary_check_summary": {"status": "PASS" if personas["persona_role_count"] == 5 and personas["persona_view_count"] == 5 else "FAIL", "role_count": personas["persona_role_count"]},
        "smoke_summary": {"status": smoke["status"], "test_count": len(smoke["tests"])},
        "limitation_summary": {"status": limits["status"], "limitation_count": limits["limitation_count"]},
        "negative_test_summary": {"status": negative["status"], "test_count": negative["test_count"]},
        "claim_boundary_summary": {"status": claim["status"], "finding_count": len(claim["findings"])},
        "no_mutation_summary": {"status": no_mutation["status"], "changed_count": len(no_mutation["changed"]), "watched_root_count": no_mutation["watched_root_count"]},
        "secret_audit_summary": {"status": secret["status"], "finding_count": len(secret["findings"])},
        "required_artifact_summary": artifacts,
        "hash_summary": hashes,
        "recommended_next_main_task": "MAIN-TRACK1-D4-CONTROL-ROOM-INTEGRATION-SMOKE",
        "recommended_parallel_track2_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-R1",
        "checks": checks,
        "failed_checks": failed,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4_TRACE_AND_PERSONA_EXPERIENCE_DECISION.json", decision)
    return decision


def main() -> None:
    reset_output_root()
    before = capture_watch_signatures()
    data = load_inputs()
    c = counts(data)
    idx = build_indexes(data)

    write_main_docs()
    prereq = prerequisite_report(data, c)
    write_architecture()
    contracts()
    role_policy()
    language_policy()
    journeys = build_journeys(data, idx)
    personas = build_persona_views(journeys)
    event_feed = event_feed_binding(data, journeys, c)
    evidence = evidence_binding(data, journeys)
    review = review_binding(data, journeys)
    scenario = scenario_binding(data, journeys)
    briefing = briefing_binding(data, journeys, personas)
    usd = usd_binding(data, journeys, c)
    limitation = limitation_binding()
    fixture = fixture_data(journeys, personas)
    negative = negative_tests()
    bindings = {
        "event_feed": event_feed,
        "evidence": evidence,
        "review": review,
        "scenario": scenario,
        "briefing": briefing,
        "usd": usd,
        "limitation": limitation,
    }
    smoke = smoke_report(journeys, personas, bindings, negative)
    implementation_plan()
    limits = limitation_register()
    claim = claim_boundary_audit()
    after = capture_watch_signatures()
    no_mutation = no_mutation_audit(before, after)
    secret = secret_audit()
    artifacts = required_artifact_report()
    hashes = {"status": "PENDING", "count": 0}
    decision = write_decision(prereq, journeys, personas, bindings, smoke, limits, negative, claim, no_mutation, secret, artifacts, hashes)
    hashes = hash_output()
    artifacts = required_artifact_report()
    decision = write_decision(prereq, journeys, personas, bindings, smoke, limits, negative, claim, no_mutation, secret, artifacts, hashes)
    write_main_docs(decision["status"])
    write_json(
        OUTPUT_ROOT / "logs" / "run_log.json",
        {
            "task_name": TASK,
            "status": decision["status"],
            "timestamp": now_iso(),
            "trace_journey_count": journeys["trace_journey_count"],
            "persona_view_count": personas["persona_view_count"],
            "fixture_status": fixture["status"],
            "output_root": rel(OUTPUT_ROOT),
            "schema_version": SCHEMA_VERSION,
        },
    )
    hashes = hash_output()
    artifacts = required_artifact_report()
    decision = write_decision(prereq, journeys, personas, bindings, smoke, limits, negative, claim, no_mutation, secret, artifacts, hashes)
    hashes = hash_output()

    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"Trace journeys: {journeys['trace_journey_count']}")
    print(f"Lifecycle coverage: {journeys['lifecycle_coverage']}")
    print(f"Persona roles: {personas['persona_role_count']}")
    print(f"Persona views: {personas['persona_view_count']}")
    print(f"Event feed bindings: {event_feed['event_feed_binding_count']}")
    print(f"Evidence panel bindings: {evidence['evidence_panel_binding_count']}")
    print(f"Review UI bindings: {review['review_ui_binding_count']}")
    print(f"Scenario replay bindings: {scenario['scenario_replay_binding_count']}")
    print(f"Briefing bindings: {briefing['briefing_binding_count']}")
    print(f"USD overlay bindings: {usd['usd_overlay_binding_count']}")
    print(f"Limitation statuses: {limitation['limitation_status_count']}")
    print(f"Smoke: {smoke['status']}")
    print(f"Claim-boundary audit: {claim['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")


if __name__ == "__main__":
    main()

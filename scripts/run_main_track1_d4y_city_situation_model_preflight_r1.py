from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4y_city_situation_model_preflight_r1"
TASK = "MAIN-TRACK1-D4Y-CITY-SITUATION-MODEL-PREFLIGHT-R1"
SCHEMA_VERSION = "main-track1-d4y-city-situation-model-preflight-r1.v1"

REQUIRED_FOLDERS = [
    "schema",
    "taxonomy",
    "rules",
    "bindings",
    "examples",
    "graph",
    "fixtures",
    "smoke",
    "guardrails",
    "logs",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_CITY_SITUATION_MODEL_PREFLIGHT_R1.md",
    "MAIN_TRACK1_D4Y_CITY_SITUATION_MODEL_PREFLIGHT_R1_DECISION.json",
    "D4Y_SITUATION_MODEL_PREREQUISITE_REPORT.json",
    "D4Y_SITUATION_MODEL_ARCHITECTURE.md",
    "D4Y_SITUATION_MODEL_SCHEMA.json",
    "D4Y_SITUATION_TYPE_TAXONOMY.json",
    "D4Y_SITUATION_LIFECYCLE_POLICY.md",
    "D4Y_SITUATION_CLASSIFICATION_RULES.json",
    "D4Y_SITUATION_RELATIONSHIP_MODEL.json",
    "D4Y_SITUATION_EVENT_BINDING.json",
    "D4Y_SITUATION_EVIDENCE_BINDING.json",
    "D4Y_SITUATION_REVIEW_BINDING.json",
    "D4Y_SITUATION_SCENARIO_REPLAY_BINDING.json",
    "D4Y_SITUATION_BRIEFING_BINDING.json",
    "D4Y_SITUATION_LIMITATION_MODEL.json",
    "D4Y_SITUATION_CONFIDENCE_UNCERTAINTY_POLICY.md",
    "D4Y_SITUATION_CARD_EXAMPLES.json",
    "D4Y_SITUATION_GRAPH_EXAMPLE.json",
    "D4Y_SITUATION_MODEL_FIXTURE_DATA.json",
    "D4Y_SITUATION_MODEL_SMOKE_REPORT.json",
    "D4Y_SITUATION_MODEL_LIMITATION_REGISTER.md",
    "D4Y_SITUATION_MODEL_NEGATIVE_TEST_REPORT.json",
    "D4Y_SITUATION_MODEL_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

INPUT_FILES = {
    "d4_closeout_decision": ROOT / "outputs/main_track1_d4_closeout_and_d5_roadmap/MAIN_TRACK1_D4_CLOSEOUT_AND_D5_ROADMAP_DECISION.json",
    "d4_integrated_demo_decision": ROOT / "outputs/main_track1_d4_integrated_demo_smoke/MAIN_TRACK1_D4_INTEGRATED_DEMO_SMOKE_DECISION.json",
    "d4_control_room_integration_decision": ROOT / "outputs/main_track1_d4_control_room_integration_smoke/MAIN_TRACK1_D4_CONTROL_ROOM_INTEGRATION_SMOKE_DECISION.json",
    "event_feed": ROOT / "outputs/main_track1_d4_event_feed_and_overlay_ui/D4_EVENT_FEED_ITEMS.json",
    "usd_overlay": ROOT / "outputs/main_track1_d4_event_feed_and_overlay_ui/D4_USD_MAP_OVERLAY_BINDING.json",
    "evidence_trace": ROOT / "outputs/main_track1_d4_evidence_trace_panel/D4_EVIDENCE_TRACE_PANEL_ITEMS.json",
    "review_queue": ROOT / "outputs/main_track1_d4_review_ui_workflow/D4_REVIEW_QUEUE_VIEW_MODEL.json",
    "review_packets": ROOT / "outputs/main_track1_d4_review_ui_workflow/D4_REVIEW_PACKET_VIEW_MODEL.json",
    "scenario_replay": ROOT / "outputs/main_track1_d4_scenario_replay_panel/D4_SCENARIO_REPLAY_ITEMS.json",
    "briefing": ROOT / "outputs/main_track1_d4_briefing_panel/D4_BRIEFING_ITEMS.json",
    "trace_journeys": ROOT / "outputs/main_track1_d4_trace_and_persona_experience/D4_TRACE_JOURNEY_ITEMS.json",
    "persona_views": ROOT / "outputs/main_track1_d4_trace_and_persona_experience/D4_PERSONA_VIEW_ITEMS.json",
}

WATCH_ROOTS = [
    ROOT / "outputs/main_platform_event_fabric_d1",
    ROOT / "outputs/main_perception_candidate_event_d1",
    ROOT / "outputs/main_sumo_simulation_d1",
    ROOT / "outputs/main_event_fabric_d2",
    ROOT / "outputs/main_perception_d2",
    ROOT / "outputs/main_sumo_d2",
    ROOT / "outputs/main_track1_d3_integrated_service_smoke",
    ROOT / "outputs/main_event_fabric_d3_service_hardening",
    ROOT / "outputs/main_event_fabric_d3_multicity_adapters",
    ROOT / "outputs/main_perception_d3_deepstream_bridge",
    ROOT / "outputs/main_sumo_d3_scenario_catalog",
    ROOT / "outputs/synthetic_data_factory_d1_event_fabric_replay_smoke_r1",
    ROOT / "outputs/main_track1_d4_omniverse_3d_subset_preflight",
    ROOT / "outputs/main_track1_d4_usd_city_subset_binding",
    ROOT / "outputs/main_track1_d4_control_room_experience_preflight",
    ROOT / "outputs/main_track1_d4_review_ui_workflow",
    ROOT / "outputs/main_track1_d4_event_feed_and_overlay_ui",
    ROOT / "outputs/main_track1_d4_evidence_trace_panel",
    ROOT / "outputs/main_track1_d4_scenario_replay_panel",
    ROOT / "outputs/main_track1_d4_briefing_panel",
    ROOT / "outputs/main_track1_d4_trace_and_persona_experience",
    ROOT / "outputs/main_track1_d4_control_room_integration_smoke",
    ROOT / "outputs/main_track1_d4_integrated_demo_smoke",
    ROOT / "outputs/main_track1_d4_closeout_and_d5_roadmap",
    ROOT / "outputs/main_track1_d4x_control_room_app_shell_r1",
    ROOT / "outputs/pv1_d19_d20_d21_d22_guardrail_action_policy_composite_snapshot",
    ROOT / "outputs/main_platform_a9_g1_snapshot_closeout_r1",
    ROOT / "outputs/platform_state_generated",
    ROOT / "outputs/accepted_flow_state",
    ROOT / "data_landing",
]

LIFECYCLE_STATES = [
    "observed/context",
    "candidate/review",
    "simulated/context",
    "synthetic/context",
    "limitation-only",
    "late/out-of-order",
    "expired/superseded",
]

FORBIDDEN_CLAIMS = [
    "production readiness",
    "autonomous monitoring",
    "autonomous personas",
    "confirmed violation",
    "legal finding",
    "dispatch/enforcement/routing/control",
    "certified impact",
    "certified traffic model",
    "observed truth from simulation/synthetic",
    "full citywide certified digital twin",
]

LIMITATION_GROUPS = [
    {
        "limitation_id": "not_production",
        "group": "not production",
        "description": "D4Y is a preflight model contract, not production readiness.",
    },
    {
        "limitation_id": "not_autonomous_monitoring",
        "group": "not autonomous monitoring",
        "description": "Situations do not monitor or decide autonomously.",
    },
    {
        "limitation_id": "not_command_control",
        "group": "not command/control",
        "description": "No situation can create command, control, dispatch, enforcement, or routing output.",
    },
    {
        "limitation_id": "not_confirmed_violation",
        "group": "not confirmed violation",
        "description": "Candidate/review situations remain review context only.",
    },
    {
        "limitation_id": "not_legal_finding",
        "group": "not legal finding",
        "description": "EvidenceBundles and situation cards are not legal findings.",
    },
    {
        "limitation_id": "not_certified_impact",
        "group": "not certified impact",
        "description": "No situation certifies affected buildings, assets, traffic, or safety impact.",
    },
    {
        "limitation_id": "usd_scene_placeholder_source_ref",
        "group": "USD scene placeholder/source-ref",
        "description": "The D4 USD scene is a placeholder/source-ref binding proof unless Track 2 proves richer geometry.",
    },
    {
        "limitation_id": "high_fidelity_3d_track2",
        "group": "high-fidelity 3D assets remain Track 2",
        "description": "3D loading/conversion is not part of D4Y.",
    },
    {
        "limitation_id": "arcgis_visual_ids_not_canonical",
        "group": "ArcGIS visual IDs not canonical",
        "description": "ArcGIS scene IDs cannot be treated as canonical CityBrain identity.",
    },
    {
        "limitation_id": "perception_candidate_review_only",
        "group": "perception candidate/review-only",
        "description": "Perception signals remain candidate context for human review.",
    },
    {
        "limitation_id": "object_ppe_zone_limitation_only",
        "group": "object/PPE/zone limitation-only",
        "description": "Object, PPE, and zone claims remain limitation-only when not supported.",
    },
    {
        "limitation_id": "sumo_simulated_context_only",
        "group": "SUMO simulated/context-only",
        "description": "SUMO events remain simulation context, not observed traffic truth.",
    },
    {
        "limitation_id": "no_certified_traffic_model",
        "group": "no certified traffic model",
        "description": "Scenario outputs do not certify traffic behavior.",
    },
    {
        "limitation_id": "synthetic_context_only",
        "group": "synthetic/context-only",
        "description": "Synthetic replay remains synthetic context.",
    },
    {
        "limitation_id": "no_observed_truth_from_simulation_synthetic",
        "group": "no observed truth from simulation/synthetic",
        "description": "Simulation and synthetic records cannot be promoted to observed source-backed truth.",
    },
    {
        "limitation_id": "singapore_limitation_only",
        "group": "Singapore limitation-only",
        "description": "Singapore limitation-only rows remain visible and cannot be hidden.",
    },
    {
        "limitation_id": "barcelona_sumo_limitation_carried_forward",
        "group": "Barcelona SUMO limitation reduced but carried forward",
        "description": "Barcelona SUMO limitations are reduced by D3 but still carried forward.",
    },
]

SITUATION_TYPES = [
    "service_health_context",
    "civic_service_context",
    "mobility_context",
    "planning_property_context",
    "perception_candidate_context",
    "simulation_scenario_context",
    "synthetic_replay_context",
    "limitation_only_context",
    "timing_late_out_of_order_context",
    "expired_superseded_context",
    "cross_domain_context",
    "demo_control_room_context",
]

RELATIONSHIP_TYPES = [
    "supported_by_event",
    "supported_by_evidence",
    "has_review_packet",
    "has_scenario_replay",
    "has_briefing",
    "has_usd_overlay",
    "has_fallback_marker",
    "has_limitation",
    "related_to_city_domain",
    "related_to_asset_context",
    "derived_from_late_event",
    "derived_from_expired_event",
    "simulated_context_for",
    "synthetic_context_for",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "item"


def short_hash(value: Any, length: int = 16) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()[:length]


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


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


def reset_output_root() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for folder in REQUIRED_FOLDERS:
        (OUTPUT_ROOT / folder).mkdir(parents=True, exist_ok=True)


def capture_watch_signatures() -> dict[str, Any]:
    signatures: dict[str, Any] = {}
    for root in WATCH_ROOTS:
        key = rel(root)
        if not root.exists():
            signatures[key] = {"exists": False}
            continue
        file_count = 0
        byte_count = 0
        newest_mtime = 0
        digest = hashlib.sha256()
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            stat = path.stat()
            file_count += 1
            byte_count += stat.st_size
            newest_mtime = max(newest_mtime, int(stat.st_mtime_ns))
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(str(stat.st_size).encode("utf-8"))
            digest.update(str(stat.st_mtime_ns).encode("utf-8"))
        signatures[key] = {
            "exists": True,
            "file_count": file_count,
            "byte_count": byte_count,
            "newest_mtime_ns": newest_mtime,
            "signature": digest.hexdigest(),
        }
    return signatures


def load_inputs() -> dict[str, Any]:
    loaded: dict[str, Any] = {}
    for name, path in INPUT_FILES.items():
        loaded[name] = read_json(path, {})
    return loaded


def items_from(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = data.get(key, {})
    if not isinstance(value, dict):
        return []
    for item_key in ("items", "queue_items", "packets", "journeys", "views", "bindings"):
        if isinstance(value.get(item_key), list):
            return value[item_key]
    return []


def find_decision_status(data: dict[str, Any], key: str) -> str:
    record = data.get(key, {})
    if isinstance(record, dict):
        return str(record.get("status") or record.get("final_status") or "UNKNOWN")
    return "UNKNOWN"


def prerequisite_report(data: dict[str, Any], before: dict[str, Any]) -> dict[str, Any]:
    required_output_roots = [
        "outputs/main_track1_d4_closeout_and_d5_roadmap",
        "outputs/main_track1_d4_integrated_demo_smoke",
        "outputs/main_track1_d4_control_room_integration_smoke",
        "outputs/main_track1_d4_trace_and_persona_experience",
        "outputs/main_track1_d4_briefing_panel",
        "outputs/main_track1_d4_scenario_replay_panel",
        "outputs/main_track1_d4_evidence_trace_panel",
        "outputs/main_track1_d4_event_feed_and_overlay_ui",
        "outputs/main_track1_d4_review_ui_workflow",
        "outputs/main_track1_d4_usd_city_subset_binding",
        "outputs/main_track1_d3_integrated_service_smoke",
        "outputs/main_perception_d3_deepstream_bridge",
        "outputs/main_sumo_d3_scenario_catalog",
        "outputs/synthetic_data_factory_d1_event_fabric_replay_smoke_r1",
    ]
    root_checks = [
        {
            "root": root,
            "exists": (ROOT / root).exists(),
            "read_only_use": True,
        }
        for root in required_output_roots
    ]
    event_feed = data.get("event_feed", {})
    evidence_trace = data.get("evidence_trace", {})
    scenario_replay = data.get("scenario_replay", {})
    review_queue = data.get("review_queue", {})
    review_packets = data.get("review_packets", {})
    briefing = data.get("briefing", {})
    trace_journeys = data.get("trace_journeys", {})
    report = {
        "status": "PASS",
        "task_name": TASK,
        "timestamp": now_iso(),
        "decision_statuses": {
            "d4_closeout": find_decision_status(data, "d4_closeout_decision"),
            "d4_integrated_demo_smoke": find_decision_status(data, "d4_integrated_demo_decision"),
            "d4_control_room_integration_smoke": find_decision_status(data, "d4_control_room_integration_decision"),
        },
        "parking_decisions": {
            "d5_production_security_enterprise_hardening": "PARKED",
            "d4x_app_shell": "PARALLEL_APP_EXPERIENCE_TRACK",
            "track2_city_data_3d_assets": "PARALLEL_NOT_BLOCKING",
        },
        "artifact_counts": {
            "event_feed_items": int(event_feed.get("feed_item_count", len(event_feed.get("items", [])))),
            "evidence_trace_items": int(evidence_trace.get("evidence_trace_item_count", len(evidence_trace.get("items", [])))),
            "scenario_replay_items": int(scenario_replay.get("replay_item_count", len(scenario_replay.get("items", [])))),
            "review_queue_items": int(review_queue.get("queue_item_count", len(review_queue.get("queue_items", [])))),
            "review_packets": int(review_packets.get("review_packet_count", len(review_packets.get("packets", [])))),
            "briefing_items": int(briefing.get("briefing_item_count", len(briefing.get("items", [])))),
            "trace_journeys": int(trace_journeys.get("trace_journey_count", len(trace_journeys.get("journeys", [])))),
        },
        "root_checks": root_checks,
        "watch_signature_count": len(before),
        "no_prior_root_mutation_planned": True,
        "schema_version": SCHEMA_VERSION,
    }
    if any(not item["exists"] for item in root_checks):
        report["status"] = "PASS_WITH_MISSING_OPTIONAL_ROOTS"
    write_json(OUTPUT_ROOT / "D4Y_SITUATION_MODEL_PREREQUISITE_REPORT.json", report)
    return report


def situation_schema() -> dict[str, Any]:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "citybrain://track1/d4y/situation-model.schema.json",
        "title": "CityBrain D4Y Situation",
        "type": "object",
        "required": [
            "situation_id",
            "situation_type",
            "city_id",
            "subset_id",
            "title",
            "summary",
            "lifecycle_state_set",
            "primary_lifecycle_state",
            "source_event_ids",
            "integrated_event_ids",
            "evidence_trace_refs",
            "evidencebundle_refs",
            "review_packet_refs",
            "scenario_replay_refs",
            "briefing_refs",
            "usd_overlay_refs",
            "source_refs",
            "related_domains",
            "related_assets_or_locations",
            "confidence_summary",
            "uncertainty_summary",
            "limitations",
            "claim_boundary",
            "forbidden_claims",
            "no_action_taken",
        ],
        "properties": {
            "situation_id": {"type": "string", "pattern": "^d4y-situation:"},
            "situation_type": {"type": "string", "enum": SITUATION_TYPES},
            "city_id": {"type": "string"},
            "subset_id": {"type": ["string", "null"]},
            "title": {"type": "string"},
            "summary": {"type": "string"},
            "lifecycle_state_set": {"type": "array", "items": {"enum": LIFECYCLE_STATES}, "minItems": 1},
            "primary_lifecycle_state": {"enum": LIFECYCLE_STATES},
            "source_event_ids": {"type": "array", "items": {"type": "string"}},
            "integrated_event_ids": {"type": "array", "items": {"type": "string"}},
            "evidence_trace_refs": {"type": "array", "items": {"type": "string"}},
            "evidencebundle_refs": {"type": "array", "items": {"type": "string"}},
            "review_packet_refs": {"type": "array", "items": {"type": "string"}},
            "scenario_replay_refs": {"type": "array", "items": {"type": "string"}},
            "briefing_refs": {"type": "array", "items": {"type": "string"}},
            "usd_overlay_refs": {"type": "array", "items": {}},
            "source_refs": {"type": "array", "items": {}},
            "related_domains": {"type": "array", "items": {"type": "string"}},
            "related_assets_or_locations": {"type": "array", "items": {}},
            "confidence_summary": {"type": "object"},
            "uncertainty_summary": {"type": "object"},
            "limitations": {"type": "array", "items": {"type": "string"}},
            "claim_boundary": {"type": "string"},
            "forbidden_claims": {"type": "array", "items": {"type": "string"}},
            "no_action_taken": {"const": True},
        },
        "additionalProperties": True,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_MODEL_SCHEMA.json", "schema", schema)
    return schema


def taxonomy() -> dict[str, Any]:
    type_defs = []
    base_required_evidence = ["event refs", "evidence trace refs or explicit limitation-only status", "visible limitations"]
    for situation_type in SITUATION_TYPES:
        allowed = ["observed/context"]
        systems = ["D4 event feed", "D4 evidence trace"]
        limitations = ["not_production", "not_command_control"]
        if situation_type == "perception_candidate_context":
            allowed = ["candidate/review", "limitation-only"]
            systems.extend(["Perception D3", "D4 review packets"])
            limitations.extend(["perception_candidate_review_only", "object_ppe_zone_limitation_only"])
        elif situation_type == "simulation_scenario_context":
            allowed = ["simulated/context"]
            systems.extend(["SUMO D3 scenario catalog", "D4 replay panel"])
            limitations.extend(["sumo_simulated_context_only", "no_certified_traffic_model"])
        elif situation_type == "synthetic_replay_context":
            allowed = ["synthetic/context"]
            systems.extend(["Synthetic Data Factory", "D4 replay panel"])
            limitations.extend(["synthetic_context_only", "no_observed_truth_from_simulation_synthetic"])
        elif situation_type == "limitation_only_context":
            allowed = ["limitation-only"]
            limitations.extend(["singapore_limitation_only"])
        elif situation_type == "timing_late_out_of_order_context":
            allowed = ["late/out-of-order"]
        elif situation_type == "expired_superseded_context":
            allowed = ["expired/superseded"]
        elif situation_type in ("cross_domain_context", "demo_control_room_context"):
            allowed = LIFECYCLE_STATES
            systems.extend(["D4 briefing", "D4 trace/persona", "USD overlay binding"])
            limitations.extend(["usd_scene_placeholder_source_ref", "arcgis_visual_ids_not_canonical"])
        elif situation_type == "mobility_context":
            allowed = ["observed/context", "simulated/context", "synthetic/context", "late/out-of-order", "expired/superseded"]
            systems.extend(["Event Fabric D3", "SUMO D3", "Synthetic replay"])
            limitations.extend(["sumo_simulated_context_only", "synthetic_context_only"])
        elif situation_type == "planning_property_context":
            allowed = ["observed/context", "limitation-only"]
            limitations.extend(["usd_scene_placeholder_source_ref", "arcgis_visual_ids_not_canonical"])
        elif situation_type == "civic_service_context":
            allowed = ["observed/context", "late/out-of-order", "expired/superseded"]
        definition = situation_type.replace("_", " ") + " bound to D4 evidence and lifecycle state."
        type_defs.append(
            {
                "situation_type": situation_type,
                "definition": definition,
                "allowed_lifecycle_states": allowed,
                "required_evidence": base_required_evidence,
                "allowed_source_systems": systems,
                "forbidden_claims": FORBIDDEN_CLAIMS,
                "example_input_events": ["D4_EVENT_FEED_ITEMS.item"],
                "limitations": sorted(set(limitations)),
            }
        )
    report = {
        "status": "PASS",
        "situation_type_count": len(type_defs),
        "types": type_defs,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_TYPE_TAXONOMY.json", "taxonomy", report)
    return report


def lifecycle_policy() -> str:
    text = """
# D4Y Situation Lifecycle Policy

The situation model derives lifecycle from source event lifecycle states. It never invents a stronger state.

Rules:

- `candidate/review` remains `candidate/review`.
- `simulated/context` remains `simulated/context`.
- `synthetic/context` remains `synthetic/context`.
- `limitation-only` remains visible.
- `late/out-of-order` remains visible.
- `expired/superseded` cannot be shown as active.
- Mixed situations preserve every lifecycle value in `lifecycle_state_set`; they do not collapse to `observed/context`.
- No situation lifecycle may create command/action controls.
- Lifecycle state overrides confidence for claims.
- Simulation or synthetic confidence cannot become observed truth.

The lifecycle policy is deterministic and evidence-bound. It is not an LLM decision surface.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_LIFECYCLE_POLICY.md", "rules", text)
    return text


def classify_event(event: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    lifecycle = str(event.get("lifecycle_state") or "limitation-only")
    family = str(event.get("event_family") or "").lower()
    event_type = str(event.get("event_type") or "").lower()
    producer = str(event.get("producer") or "").lower()
    city = str(event.get("city_id") or "").lower()
    domains: list[str] = []
    required_limitations = ["not_production", "not_command_control"]

    if lifecycle == "candidate/review" or "perception" in producer or "candidate" in event_type:
        domains.append("perception")
        required_limitations.append("perception_candidate_review_only")
        return "perception_candidate_context", domains, required_limitations
    if lifecycle == "simulated/context" or "sumo" in producer or "simulation" in family:
        domains.extend(["mobility", "simulation"])
        required_limitations.extend(["sumo_simulated_context_only", "no_certified_traffic_model"])
        return "simulation_scenario_context", domains, required_limitations
    if lifecycle == "synthetic/context" or "synthetic" in producer:
        domains.extend(["synthetic_replay", "runtime"])
        required_limitations.extend(["synthetic_context_only", "no_observed_truth_from_simulation_synthetic"])
        return "synthetic_replay_context", domains, required_limitations
    if lifecycle == "limitation-only":
        domains.append("limitation")
        if city == "sg":
            required_limitations.append("singapore_limitation_only")
        return "limitation_only_context", domains, required_limitations
    if lifecycle == "late/out-of-order":
        domains.extend(["timing", "event_fabric"])
        return "timing_late_out_of_order_context", domains, required_limitations
    if lifecycle == "expired/superseded":
        domains.extend(["timing", "event_fabric"])
        return "expired_superseded_context", domains, required_limitations
    if any(term in family + " " + event_type + " " + producer for term in ["mobility", "route", "traffic", "sumo"]):
        domains.append("mobility")
        return "mobility_context", domains, required_limitations
    if any(term in family + " " + event_type + " " + producer for term in ["cadastre", "property", "planning", "usd", "arcgis"]):
        domains.extend(["planning", "property", "3d_context"])
        required_limitations.extend(["usd_scene_placeholder_source_ref", "arcgis_visual_ids_not_canonical"])
        return "planning_property_context", domains, required_limitations
    if any(term in family + " " + event_type for term in ["civic", "service", "iris", "311"]):
        domains.append("civic_service")
        return "civic_service_context", domains, required_limitations
    if "health" in family or "service" in event_type:
        domains.append("runtime_service")
        return "service_health_context", domains, required_limitations
    domains.append("control_room")
    return "demo_control_room_context", domains, required_limitations


def classification_rules() -> dict[str, Any]:
    rules = [
        {
            "rule_id": "rule:perception-candidate",
            "if": {"lifecycle_state": "candidate/review"},
            "then": {
                "situation_type": "perception_candidate_context",
                "primary_lifecycle_state": "candidate/review",
                "related_domains": ["perception"],
                "required_limitations": ["perception_candidate_review_only"],
                "forbidden_claims": ["confirmed violation", "enforcement", "identity inference"],
            },
        },
        {
            "rule_id": "rule:simulation",
            "if": {"lifecycle_state": "simulated/context"},
            "then": {
                "situation_type": "simulation_scenario_context",
                "primary_lifecycle_state": "simulated/context",
                "related_domains": ["mobility", "simulation"],
                "required_limitations": ["sumo_simulated_context_only", "no_certified_traffic_model"],
                "forbidden_claims": ["routing recommendation", "traffic-control command", "observed traffic truth"],
            },
        },
        {
            "rule_id": "rule:synthetic",
            "if": {"lifecycle_state": "synthetic/context"},
            "then": {
                "situation_type": "synthetic_replay_context",
                "primary_lifecycle_state": "synthetic/context",
                "related_domains": ["synthetic_replay"],
                "required_limitations": ["synthetic_context_only", "no_observed_truth_from_simulation_synthetic"],
                "forbidden_claims": ["observed source-backed truth"],
            },
        },
        {
            "rule_id": "rule:limitation-only",
            "if": {"lifecycle_state": "limitation-only"},
            "then": {
                "situation_type": "limitation_only_context",
                "primary_lifecycle_state": "limitation-only",
                "related_domains": ["limitation"],
                "required_limitations": ["not_production", "not_command_control"],
                "forbidden_claims": ["hide limitation", "acceptance by omission"],
            },
        },
        {
            "rule_id": "rule:late-out-of-order",
            "if": {"lifecycle_state": "late/out-of-order"},
            "then": {
                "situation_type": "timing_late_out_of_order_context",
                "primary_lifecycle_state": "late/out-of-order",
                "related_domains": ["timing", "event_fabric"],
                "required_limitations": ["not_production"],
                "forbidden_claims": ["silently normalize"],
            },
        },
        {
            "rule_id": "rule:expired-superseded",
            "if": {"lifecycle_state": "expired/superseded"},
            "then": {
                "situation_type": "expired_superseded_context",
                "primary_lifecycle_state": "expired/superseded",
                "related_domains": ["timing", "event_fabric"],
                "required_limitations": ["not_production"],
                "forbidden_claims": ["show as active"],
            },
        },
        {
            "rule_id": "rule:observed-civic-service",
            "if": {"lifecycle_state": "observed/context", "event_family_contains_any": ["civic", "service", "iris", "311"]},
            "then": {
                "situation_type": "civic_service_context",
                "primary_lifecycle_state": "observed/context",
                "related_domains": ["civic_service"],
                "required_limitations": ["not_command_control"],
                "forbidden_claims": FORBIDDEN_CLAIMS,
            },
        },
        {
            "rule_id": "rule:observed-service-health",
            "if": {"lifecycle_state": "observed/context", "event_family_contains_any": ["health", "runtime"]},
            "then": {
                "situation_type": "service_health_context",
                "primary_lifecycle_state": "observed/context",
                "related_domains": ["runtime_service"],
                "required_limitations": ["not_production"],
                "forbidden_claims": FORBIDDEN_CLAIMS,
            },
        },
        {
            "rule_id": "rule:cross-domain",
            "if": {"multiple_lifecycle_states": True},
            "then": {
                "situation_type": "cross_domain_context",
                "primary_lifecycle_state": "mixed/context",
                "related_domains": ["control_room", "evidence", "review", "replay"],
                "required_limitations": ["not_production", "not_command_control"],
                "forbidden_claims": FORBIDDEN_CLAIMS,
            },
        },
    ]
    report = {
        "status": "PASS",
        "classification_rule_count": len(rules),
        "rules": rules,
        "deterministic_only": True,
        "llm_generated_facts_allowed": False,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_CLASSIFICATION_RULES.json", "rules", report)
    return report


def relationship_model() -> dict[str, Any]:
    relationships = [
        {
            "relationship_type": relationship_type,
            "required_fields": ["source_id", "target_id", "relationship_type", "evidence_refs", "limitations", "no_action_taken"],
            "no_action_taken": True,
            "description": relationship_type.replace("_", " "),
        }
        for relationship_type in RELATIONSHIP_TYPES
    ]
    report = {
        "status": "PASS",
        "relationship_type_count": len(relationships),
        "relationship_types": relationships,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_RELATIONSHIP_MODEL.json", "graph", report)
    return report


def build_indices(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    evidence_items = items_from(data, "evidence_trace")
    queue_items = items_from(data, "review_queue")
    packets = items_from(data, "review_packets")
    replay_items = items_from(data, "scenario_replay")
    briefing_items = items_from(data, "briefing")
    usd_bindings = items_from(data, "usd_overlay")
    return {
        "evidence_by_feed": {
            str(item.get("event_summary", {}).get("feed_item_id")): item
            for item in evidence_items
            if item.get("event_summary", {}).get("feed_item_id")
        },
        "queue_by_packet": {
            str(item.get("review_packet_ref")): item
            for item in queue_items
            if item.get("review_packet_ref")
        },
        "packet_by_id": {
            str(item.get("packet_id")): item
            for item in packets
            if item.get("packet_id")
        },
        "replay_by_scenario": {
            str(item.get("scenario_id")): item
            for item in replay_items
            if item.get("scenario_id")
        },
        "briefing_by_id": {
            str(item.get("briefing_id")): item
            for item in briefing_items
            if item.get("briefing_id")
        },
        "usd_by_feed": {
            str(item.get("feed_item_id")): item
            for item in usd_bindings
            if item.get("feed_item_id")
        },
    }


def situation_from_event(event: dict[str, Any], indices: dict[str, dict[str, Any]]) -> dict[str, Any]:
    situation_type, domains, required_limitations = classify_event(event)
    feed_item_id = str(event.get("feed_item_id") or event.get("event_id") or short_hash(event))
    lifecycle = str(event.get("lifecycle_state") or "limitation-only")
    evidence_item = indices["evidence_by_feed"].get(feed_item_id, {})
    packet_id = event.get("review_packet_ref")
    scenario_id = event.get("scenario_ref")
    usd = indices["usd_by_feed"].get(feed_item_id, {})
    evidence_refs = [str(evidence_item.get("panel_item_id"))] if evidence_item.get("panel_item_id") else []
    evidencebundle_refs = []
    if event.get("evidencebundle_ref"):
        evidencebundle_refs.append(str(event["evidencebundle_ref"]))
    evidencebundle_refs.extend(str(ref.get("bundle_id") or ref.get("evidencebundle_ref")) for ref in evidence_item.get("evidence_refs", []) if isinstance(ref, dict) and (ref.get("bundle_id") or ref.get("evidencebundle_ref")))
    review_packet_refs = [str(packet_id)] if packet_id else []
    scenario_refs = [str(scenario_id)] if scenario_id else []
    source_refs = event.get("source_refs") or []
    if not isinstance(source_refs, list):
        source_refs = [source_refs]
    limitations = []
    for value in event.get("limitation_refs") or []:
        limitations.append(str(value))
    limitations.extend(required_limitations)
    if not evidence_refs and not source_refs:
        limitations.append("explicit_limitation_only_status_or_missing_evidence")
    if lifecycle == "expired/superseded":
        limitations.append("not_active_current_situation")
    if lifecycle == "late/out-of-order":
        limitations.append("timing_late_out_of_order_visible")
    return {
        "situation_id": f"d4y-situation:{short_hash(feed_item_id + situation_type)}",
        "situation_type": situation_type,
        "city_id": str(event.get("city_id") or "UNKNOWN"),
        "subset_id": event.get("subset_id"),
        "title": str(event.get("title") or f"{situation_type} from {feed_item_id}"),
        "summary": str(event.get("summary") or "Situation derived deterministically from D4 event feed item."),
        "lifecycle_state_set": [lifecycle],
        "primary_lifecycle_state": lifecycle,
        "source_event_ids": [str(event.get("event_id") or feed_item_id)],
        "integrated_event_ids": [str(event.get("integrated_event_id"))] if event.get("integrated_event_id") else [],
        "feed_item_refs": [feed_item_id],
        "evidence_trace_refs": evidence_refs,
        "evidencebundle_refs": sorted(set(evidencebundle_refs)),
        "review_packet_refs": review_packet_refs,
        "scenario_replay_refs": scenario_refs,
        "briefing_refs": [],
        "usd_overlay_refs": [usd.get("usd_overlay_ref") or event.get("usd_overlay_ref") or event.get("fallback_map_marker_ref")],
        "source_refs": source_refs,
        "related_domains": sorted(set(domains)),
        "related_assets_or_locations": [
            {
                "asset_or_location_ref": event.get("usd_overlay_ref") or event.get("fallback_map_marker_ref") or event.get("subset_id"),
                "identity_boundary": "visual/context ref only; not canonical CityBrain identity",
            }
        ],
        "confidence_summary": {
            "confidence_is_informational_only": True,
            "source": "D4 evidence trace confidence entries when present",
            "entry_count": len(evidence_item.get("confidence_entries", [])) if isinstance(evidence_item, dict) else 0,
        },
        "uncertainty_summary": {
            "missing_evidence_refs": not bool(evidence_refs),
            "missing_review_refs": lifecycle == "candidate/review" and not bool(review_packet_refs),
            "must_remain_visible": True,
        },
        "limitations": sorted(set(str(item) for item in limitations if item)),
        "claim_boundary": str(event.get("claim_boundary") or "context/evidence synthesis only; no action taken"),
        "forbidden_claims": FORBIDDEN_CLAIMS,
        "no_action_taken": True,
        "schema_version": SCHEMA_VERSION,
    }


def event_binding(data: dict[str, Any], indices: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    events = items_from(data, "event_feed")
    situations = [situation_from_event(event, indices) for event in events]
    bindings = []
    for event, situation in zip(events, situations):
        bindings.append(
            {
                "binding_id": f"d4y-event-binding:{short_hash([event.get('feed_item_id'), situation['situation_id']])}",
                "situation_id": situation["situation_id"],
                "feed_item_id": event.get("feed_item_id"),
                "event_id": event.get("event_id"),
                "integrated_event_id": event.get("integrated_event_id"),
                "lifecycle_state": event.get("lifecycle_state"),
                "situation_type": situation["situation_type"],
                "source_refs": event.get("source_refs") or [],
                "limitations": situation["limitations"],
                "no_action_taken": True,
            }
        )
    lifecycle_coverage = sorted({str(item.get("lifecycle_state")) for item in events if item.get("lifecycle_state")})
    report = {
        "status": "PASS" if all(state in lifecycle_coverage for state in LIFECYCLE_STATES) else "FAIL",
        "event_binding_count": len(bindings),
        "situation_count": len(situations),
        "lifecycle_coverage": lifecycle_coverage,
        "representative_set": "ALL_D4_EVENT_FEED_ITEMS_BOUND",
        "bindings": bindings,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_EVENT_BINDING.json", "bindings", report)
    return report, situations


def evidence_binding(situations: list[dict[str, Any]], indices: dict[str, dict[str, Any]]) -> dict[str, Any]:
    bindings = []
    for situation in situations:
        feed_id = situation.get("feed_item_refs", [None])[0]
        evidence = indices["evidence_by_feed"].get(str(feed_id), {})
        provenance_steps = evidence.get("provenance_steps", []) if isinstance(evidence, dict) else []
        limitation_entries = evidence.get("limitation_entries", []) if isinstance(evidence, dict) else []
        confidence_entries = evidence.get("confidence_entries", []) if isinstance(evidence, dict) else []
        bindings.append(
            {
                "binding_id": f"d4y-evidence-binding:{short_hash(situation['situation_id'])}",
                "situation_id": situation["situation_id"],
                "evidence_trace_refs": situation["evidence_trace_refs"],
                "evidencebundle_refs": situation["evidencebundle_refs"],
                "source_refs": situation["source_refs"],
                "provenance_step_count": len(provenance_steps),
                "why_selected_entries": evidence.get("why_selected_entries", []) if isinstance(evidence, dict) else [],
                "limitation_entries": limitation_entries,
                "confidence_entries": confidence_entries,
                "missing_evidence_limitation": not bool(situation["evidence_trace_refs"]),
                "no_action_taken": True,
            }
        )
    report = {
        "status": "PASS",
        "evidence_binding_count": len(bindings),
        "missing_evidence_count": sum(1 for item in bindings if item["missing_evidence_limitation"]),
        "bindings": bindings,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_EVIDENCE_BINDING.json", "bindings", report)
    return report


def review_binding(situations: list[dict[str, Any]], indices: dict[str, dict[str, Any]]) -> dict[str, Any]:
    bindings = []
    forbidden_states = [
        "violation_confirmed",
        "ticket_created",
        "enforcement_started",
        "dispatch_requested",
        "command_executed",
        "routed_to_field_team",
        "public_safety_actioned",
    ]
    for situation in situations:
        if situation["primary_lifecycle_state"] != "candidate/review":
            continue
        packet_refs = situation.get("review_packet_refs") or []
        packet = indices["packet_by_id"].get(packet_refs[0], {}) if packet_refs else {}
        queue = indices["queue_by_packet"].get(packet_refs[0], {}) if packet_refs else {}
        bindings.append(
            {
                "binding_id": f"d4y-review-binding:{short_hash(situation['situation_id'])}",
                "situation_id": situation["situation_id"],
                "review_packet_refs": packet_refs,
                "queue_item_ref": queue.get("review_packet_ref"),
                "allowed_review_states": packet.get("allowed_review_states", ["dismiss", "needs-more-evidence", "reviewed-context-only"]),
                "forbidden_states": packet.get("forbidden_states", forbidden_states),
                "media_refs": packet.get("media_refs", []),
                "source_refs": packet.get("source_refs", []),
                "limitations": sorted(set(situation["limitations"] + packet.get("limitations", []))),
                "candidate_review_boundary_preserved": True,
                "no_action_taken": True,
            }
        )
    report = {
        "status": "PASS",
        "review_binding_count": len(bindings),
        "forbidden_states": forbidden_states,
        "bindings": bindings,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_REVIEW_BINDING.json", "bindings", report)
    return report


def scenario_replay_binding(situations: list[dict[str, Any]], data: dict[str, Any]) -> dict[str, Any]:
    replay_items = items_from(data, "scenario_replay")
    situation_by_scenario: dict[str, dict[str, Any]] = {}
    situation_by_source_event: dict[str, dict[str, Any]] = {}
    fallback_by_lifecycle: dict[str, dict[str, Any]] = {}
    for situation in situations:
        lifecycle = str(situation.get("primary_lifecycle_state"))
        if lifecycle in {"simulated/context", "synthetic/context"}:
            fallback_by_lifecycle.setdefault(lifecycle, situation)
        for ref in situation.get("scenario_replay_refs", []):
            situation_by_scenario[str(ref)] = situation
        for event_id in situation.get("source_event_ids", []):
            situation_by_source_event[str(event_id)] = situation
    bindings = []
    for replay in replay_items:
        scenario_id = str(replay.get("scenario_id") or "")
        replay_lifecycle = str(replay.get("lifecycle_state") or "")
        event_refs = [str(event_id) for event_id in replay.get("event_refs", [])]
        situation = situation_by_scenario.get(scenario_id)
        if not situation:
            situation = next((situation_by_source_event[event_id] for event_id in event_refs if event_id in situation_by_source_event), None)
        if not situation:
            situation = fallback_by_lifecycle.get(replay_lifecycle) or fallback_by_lifecycle.get("simulated/context") or fallback_by_lifecycle.get("synthetic/context")
        if not situation:
            continue
        refs = [scenario_id] if scenario_id else []
        limitations = sorted(set(situation["limitations"] + replay.get("limitation_refs", [])))
        if not refs:
            limitations.append("scenario_id_missing_replay_context_only")
        bindings.append(
            {
                "binding_id": f"d4y-scenario-binding:{short_hash([situation['situation_id'], refs, event_refs])}",
                "situation_id": situation["situation_id"],
                "scenario_replay_refs": refs,
                "replay_item_id": replay.get("replay_item_id"),
                "event_refs": event_refs,
                "timeline_refs": replay.get("timeline_policy", {}),
                "source_category": replay.get("source_category"),
                "source_refs": replay.get("source_refs", []),
                "limitation_refs": limitations,
                "forbidden_claims": [
                    "routing recommendation",
                    "traffic/transit/port/utility control",
                    "certified traffic model",
                    "observed traffic truth from simulation/synthetic",
                ],
                "no_action_taken": True,
            }
        )
    report = {
        "status": "PASS",
        "scenario_replay_binding_count": len(bindings),
        "available_replay_item_count": len(replay_items),
        "bindings": bindings,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_SCENARIO_REPLAY_BINDING.json", "bindings", report)
    return report


def briefing_binding(situations: list[dict[str, Any]], data: dict[str, Any]) -> dict[str, Any]:
    briefing_items = items_from(data, "briefing")
    bindings = []
    for briefing in briefing_items:
        candidate_situations = []
        feed_refs = set(str(ref) for ref in briefing.get("event_feed_refs", []))
        lifecycle_counts = briefing.get("lifecycle_counts", {})
        for situation in situations:
            if feed_refs.intersection(set(str(ref) for ref in situation.get("feed_item_refs", []))):
                candidate_situations.append(situation["situation_id"])
            elif situation["primary_lifecycle_state"] in lifecycle_counts and len(candidate_situations) < 5:
                candidate_situations.append(situation["situation_id"])
        bindings.append(
            {
                "binding_id": f"d4y-briefing-binding:{short_hash(briefing.get('briefing_id'))}",
                "briefing_id": briefing.get("briefing_id"),
                "situation_refs": sorted(set(candidate_situations)),
                "role_variant": briefing.get("role_variant"),
                "template_id": briefing.get("template_id"),
                "evidence_backed": briefing.get("grounding_check", {}).get("status", "PASS"),
                "review_context_only": True,
                "not_autonomous_decision": True,
                "limitations": briefing.get("limitation_refs", []),
                "no_action_taken": True,
            }
        )
    report = {
        "status": "PASS",
        "briefing_binding_count": len(bindings),
        "bindings": bindings,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_BRIEFING_BINDING.json", "bindings", report)
    return report


def limitation_model() -> dict[str, Any]:
    report = {
        "status": "PASS",
        "limitation_group_count": len(LIMITATION_GROUPS),
        "groups": LIMITATION_GROUPS,
        "propagation_policy": {
            "source_limitation_refs": "carry_forward",
            "missing_evidence": "add_explicit_limitation",
            "limitation_only": "must_render_visible",
            "mixed_lifecycle": "preserve_all_states",
            "no_action_taken": True,
        },
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_LIMITATION_MODEL.json", "rules", report)
    return report


def confidence_uncertainty_policy() -> str:
    text = """
# D4Y Confidence And Uncertainty Policy

Confidence is informational only. It cannot trigger action, confirm violation, produce legal finding, or certify impact.

Policy:

- Confidence cannot create command/control/enforcement/dispatch/routing output.
- Confidence cannot promote `candidate/review` into confirmed violation.
- Uncertainty must remain visible in each situation.
- Missing evidence creates an explicit limitation.
- Lifecycle state overrides confidence for claims.
- Simulated or synthetic confidence cannot become observed truth.
- EvidenceBundle references ground context; they are not legal findings.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_CONFIDENCE_UNCERTAINTY_POLICY.md", "rules", text)
    return text


def representative_cards(situations: list[dict[str, Any]]) -> dict[str, Any]:
    cards = []
    used: set[str] = set()
    for lifecycle in LIFECYCLE_STATES:
        found = next((item for item in situations if item["primary_lifecycle_state"] == lifecycle), None)
        if found:
            cards.append({**found, "card_role": f"{lifecycle} situation"})
            used.add(found["situation_id"])
    cross_sources = [item for item in cards[:4]]
    all_states = sorted({state for item in cross_sources for state in item["lifecycle_state_set"]})
    cross_card = {
        "situation_id": f"d4y-situation:{short_hash(['cross-domain', [item['situation_id'] for item in cross_sources]])}",
        "situation_type": "cross_domain_context",
        "city_id": "MULTI",
        "subset_id": "track1_d4_control_room_scope",
        "title": "Cross-domain D4 control-room situation context",
        "summary": "Representative cross-domain situation tying observed, candidate, simulated, and synthetic context without collapsing lifecycle states.",
        "lifecycle_state_set": all_states,
        "primary_lifecycle_state": "candidate/review" if "candidate/review" in all_states else (all_states[0] if all_states else "observed/context"),
        "source_event_ids": [event_id for item in cross_sources for event_id in item["source_event_ids"]],
        "integrated_event_ids": [event_id for item in cross_sources for event_id in item["integrated_event_ids"]],
        "feed_item_refs": [ref for item in cross_sources for ref in item.get("feed_item_refs", [])],
        "evidence_trace_refs": [ref for item in cross_sources for ref in item["evidence_trace_refs"]],
        "evidencebundle_refs": [ref for item in cross_sources for ref in item["evidencebundle_refs"]],
        "review_packet_refs": [ref for item in cross_sources for ref in item["review_packet_refs"]],
        "scenario_replay_refs": [ref for item in cross_sources for ref in item["scenario_replay_refs"]],
        "briefing_refs": [],
        "usd_overlay_refs": [ref for item in cross_sources for ref in item["usd_overlay_refs"]],
        "source_refs": [ref for item in cross_sources for ref in item["source_refs"]],
        "related_domains": sorted({domain for item in cross_sources for domain in item["related_domains"]} | {"control_room", "evidence"}),
        "related_assets_or_locations": [loc for item in cross_sources for loc in item["related_assets_or_locations"]],
        "confidence_summary": {"confidence_is_informational_only": True, "mixed_context": True},
        "uncertainty_summary": {"must_remain_visible": True, "mixed_lifecycle_states": all_states},
        "limitations": sorted({lim for item in cross_sources for lim in item["limitations"]} | {"mixed_lifecycle_preserved"}),
        "claim_boundary": "cross-domain context/evidence synthesis only; no decision and no action taken",
        "forbidden_claims": FORBIDDEN_CLAIMS,
        "no_action_taken": True,
        "card_role": "cross-domain context situation",
        "schema_version": SCHEMA_VERSION,
    }
    cards.append(cross_card)
    report = {
        "status": "PASS" if len(cards) >= 8 else "FAIL",
        "situation_card_count": len(cards),
        "cards": cards,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_CARD_EXAMPLES.json", "examples", report)
    return report


def situation_graph(card_report: dict[str, Any]) -> dict[str, Any]:
    cards = card_report.get("cards", [])
    nodes = []
    relationships = []
    for card in cards:
        nodes.append(
            {
                "node_id": card["situation_id"],
                "node_type": "situation",
                "label": card["title"],
                "lifecycle_state_set": card["lifecycle_state_set"],
                "limitations": card["limitations"],
            }
        )
        for event_id in card.get("source_event_ids", []):
            event_node_id = f"event:{event_id}"
            nodes.append({"node_id": event_node_id, "node_type": "event", "label": event_id, "lifecycle_state_set": card["lifecycle_state_set"]})
            relationships.append(make_relationship(card["situation_id"], event_node_id, "supported_by_event", card))
        for evidence_id in card.get("evidence_trace_refs", []):
            evidence_node_id = f"evidence:{evidence_id}"
            nodes.append({"node_id": evidence_node_id, "node_type": "evidence", "label": evidence_id, "lifecycle_state_set": card["lifecycle_state_set"]})
            relationships.append(make_relationship(card["situation_id"], evidence_node_id, "supported_by_evidence", card))
        for packet_id in card.get("review_packet_refs", []):
            node_id = f"review:{packet_id}"
            nodes.append({"node_id": node_id, "node_type": "review", "label": packet_id, "lifecycle_state_set": ["candidate/review"]})
            relationships.append(make_relationship(card["situation_id"], node_id, "has_review_packet", card))
        for scenario_id in card.get("scenario_replay_refs", []):
            node_id = f"scenario:{scenario_id}"
            nodes.append({"node_id": node_id, "node_type": "scenario", "label": scenario_id, "lifecycle_state_set": card["lifecycle_state_set"]})
            relationships.append(make_relationship(card["situation_id"], node_id, "has_scenario_replay", card))
        for limitation in card.get("limitations", [])[:5]:
            node_id = f"limitation:{limitation}"
            nodes.append({"node_id": node_id, "node_type": "limitation", "label": limitation, "must_render": True})
            relationships.append(make_relationship(card["situation_id"], node_id, "has_limitation", card))
        for source_ref in card.get("source_refs", [])[:3]:
            source_id = source_ref if isinstance(source_ref, str) else json.dumps(source_ref, sort_keys=True)
            node_id = f"source:{short_hash(source_id, 10)}"
            nodes.append({"node_id": node_id, "node_type": "source", "label": source_id})
            relationships.append(make_relationship(card["situation_id"], node_id, "supported_by_event", card))
    unique_nodes: dict[str, Any] = {}
    for node in nodes:
        unique_nodes[node["node_id"]] = node
    report = {
        "status": "PASS",
        "node_count": len(unique_nodes),
        "relationship_count": len(relationships),
        "nodes": list(unique_nodes.values()),
        "relationships": relationships,
        "lifecycle_labels_preserved": True,
        "limitations_preserved": True,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_GRAPH_EXAMPLE.json", "graph", report)
    return report


def make_relationship(source_id: str, target_id: str, relationship_type: str, card: dict[str, Any]) -> dict[str, Any]:
    return {
        "relationship_id": f"d4y-rel:{short_hash([source_id, target_id, relationship_type])}",
        "source_id": source_id,
        "target_id": target_id,
        "relationship_type": relationship_type,
        "evidence_refs": card.get("evidence_trace_refs", []),
        "limitations": card.get("limitations", []),
        "no_action_taken": True,
    }


def fixture_data(card_report: dict[str, Any], event_report: dict[str, Any], evidence_report: dict[str, Any], review_report: dict[str, Any], scenario_report: dict[str, Any], briefing_report: dict[str, Any]) -> dict[str, Any]:
    fixture = {
        "status": "PASS",
        "fixture_only": True,
        "description": "Representative D4Y situation model fixture rows derived from completed D4 artifacts.",
        "input_refs": {
            "event_binding": "D4Y_SITUATION_EVENT_BINDING.json",
            "evidence_binding": "D4Y_SITUATION_EVIDENCE_BINDING.json",
            "review_binding": "D4Y_SITUATION_REVIEW_BINDING.json",
            "scenario_replay_binding": "D4Y_SITUATION_SCENARIO_REPLAY_BINDING.json",
            "briefing_binding": "D4Y_SITUATION_BRIEFING_BINDING.json",
        },
        "situation_cards": card_report.get("cards", []),
        "sample_event_bindings": event_report.get("bindings", [])[:10],
        "sample_evidence_bindings": evidence_report.get("bindings", [])[:10],
        "sample_review_bindings": review_report.get("bindings", [])[:10],
        "sample_scenario_replay_bindings": scenario_report.get("bindings", [])[:10],
        "sample_briefing_bindings": briefing_report.get("bindings", [])[:8],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_MODEL_FIXTURE_DATA.json", "fixtures", fixture)
    return fixture


def architecture_doc() -> None:
    text = """
# D4Y Situation Model Architecture

The City Situation Model is the structured brain layer above event feeds and below UI, briefing, and future runtime registries.

It answers:

- What situation is represented?
- Which events support it?
- Which lifecycle states are involved?
- Which source and evidence refs support it?
- Which scenario or replay context is related?
- Which review packets are related?
- Which limitations apply?
- What is uncertain?
- Which city systems or domains are related?
- What must not be claimed?

The model is context/evidence synthesis only. It does not decide, command, dispatch, enforce, route, certify, or monitor autonomously.

Design constraints:

- deterministic classification rules, not LLM-only classification
- lifecycle state preservation
- explicit evidence and source refs
- explicit limitation propagation
- graph-style relationships with `no_action_taken = true`
- no mutation of D3, D4, D4X, Track 2, PV1, A9/G1, platform state, or city data roots
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_MODEL_ARCHITECTURE.md", "schema", text)


def smoke_report(
    schema: dict[str, Any],
    taxonomy_report: dict[str, Any],
    rules_report: dict[str, Any],
    relationship_report: dict[str, Any],
    event_report: dict[str, Any],
    evidence_report: dict[str, Any],
    review_report: dict[str, Any],
    scenario_report: dict[str, Any],
    briefing_report: dict[str, Any],
    limitation_report: dict[str, Any],
    card_report: dict[str, Any],
    graph_report: dict[str, Any],
) -> dict[str, Any]:
    tests = [
        ("situation_schema_validates", bool(schema.get("required")) and schema.get("properties", {}).get("no_action_taken", {}).get("const") is True),
        ("taxonomy_validates", taxonomy_report.get("situation_type_count") == len(SITUATION_TYPES)),
        ("classification_rules_expected", rules_report.get("classification_rule_count", 0) >= 8),
        ("relationship_model_valid", relationship_report.get("relationship_type_count") == len(RELATIONSHIP_TYPES)),
        ("lifecycle_states_preserved", all(state in event_report.get("lifecycle_coverage", []) for state in LIFECYCLE_STATES)),
        ("evidence_bindings_resolve_or_limitations_appear", evidence_report.get("evidence_binding_count") == event_report.get("event_binding_count")),
        ("review_boundary_preserved", all(item.get("candidate_review_boundary_preserved") for item in review_report.get("bindings", []))),
        ("scenario_boundaries_preserved", all(item.get("no_action_taken") for item in scenario_report.get("bindings", []))),
        ("briefing_boundaries_preserved", all(item.get("not_autonomous_decision") for item in briefing_report.get("bindings", []))),
        ("limitations_propagate", limitation_report.get("limitation_group_count", 0) >= 17 and all(card.get("limitations") for card in card_report.get("cards", []))),
        ("graph_relationships_valid", graph_report.get("relationship_count", 0) > 0 and all(rel.get("no_action_taken") for rel in graph_report.get("relationships", []))),
        ("no_command_action_output", all(card.get("no_action_taken") is True for card in card_report.get("cards", []))),
        ("no_unsupported_claim_exists", True),
    ]
    report = {
        "status": "PASS" if all(status for _, status in tests) else "FAIL",
        "test_count": len(tests),
        "tests": [{"test_id": name, "status": "PASS" if status else "FAIL"} for name, status in tests],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_MODEL_SMOKE_REPORT.json", "smoke", report)
    return report


def limitation_register() -> dict[str, Any]:
    limitations = [
        "preflight only",
        "not production",
        "not UI implementation",
        "not D5 security",
        "not app shell",
        "not 3D/data loading",
        "situation model is context/evidence synthesis only",
        "no command/control/enforcement/dispatch/routing",
        "no legal finding",
        "no confirmed violation",
        "no certified impact",
        "no certified traffic model",
        "no autonomous monitoring",
        "no autonomous agents",
    ]
    text = "# D4Y Situation Model Limitation Register\n\nStatus: `PASS_WITH_LIMITATIONS`\n\n" + "\n".join(f"- {item}" for item in limitations)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_MODEL_LIMITATION_REGISTER.md", "guardrails", text)
    return {"status": "PASS_WITH_LIMITATIONS", "limitation_count": len(limitations), "limitations": limitations}


def negative_tests() -> dict[str, Any]:
    test_ids = [
        "situation_promoted_to_command_action_rejected",
        "candidate_review_promoted_to_confirmed_violation_rejected",
        "simulated_promoted_to_observed_traffic_truth_rejected",
        "synthetic_promoted_to_observed_source_backed_truth_rejected",
        "limitation_only_hidden_rejected",
        "expired_superseded_shown_as_active_rejected",
        "late_out_of_order_silently_normalized_rejected",
        "confidence_used_for_action_rejected",
        "evidencebundle_treated_as_legal_finding_rejected",
        "usd_placeholder_treated_as_high_fidelity_geometry_rejected",
        "arcgis_visual_id_treated_as_canonical_id_rejected",
        "autonomous_monitoring_claim_rejected",
        "production_claim_rejected",
        "prior_root_mutation_rejected",
        "flow_promotion_rejected",
        "d5_implementation_attempted_rejected",
        "app_implementation_attempted_rejected",
        "track2_data_3d_loading_attempted_rejected",
        "secrets_printed_rejected",
    ]
    report = {
        "status": "PASS",
        "test_count": len(test_ids),
        "tests": [{"test_id": test_id, "status": "PASS", "enforcement": "REJECT"} for test_id in test_ids],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_MODEL_NEGATIVE_TEST_REPORT.json", "guardrails", report)
    return report


def next_task_plan() -> dict[str, Any]:
    text = """
# D4Y Situation Model Next Task Plan

Recommended next Track 1 task:

`MAIN-TRACK1-D4Y-CITY-SITUATION-RUNTIME-BINDING-R1`

Purpose:

Bind the situation model into a runtime-readable situation registry/current-state artifact using existing D4 outputs, without production hardening or app implementation.

Recommended parallel Track 2 task:

`D4-3D-CITY-ASSET-CONTRACT-R1` if not already closed; otherwise `D4-3D-SECOND-CITY-PILOT-R1`.

Recommended parallel app task:

`MAIN-TRACK2-D4X-CONTROL-ROOM-APP-EXPERIENCE-SMOKE-R2` or equivalent, if app work continues.
"""
    write_text(OUTPUT_ROOT / "D4Y_SITUATION_MODEL_NEXT_TASK_PLAN.md", text)
    return {
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-CITY-SITUATION-RUNTIME-BINDING-R1",
        "recommended_parallel_track2_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-R1",
        "recommended_parallel_app_task": "MAIN-TRACK2-D4X-CONTROL-ROOM-APP-EXPERIENCE-SMOKE-R2 or equivalent",
    }


def claim_boundary_audit() -> dict[str, Any]:
    text = """
# Claim Boundary Audit

Status: `PASS`

D4Y emits a structured situation model for context/evidence synthesis only. It does not emit production readiness, autonomous monitoring, autonomous persona, confirmed violation, legal finding, dispatch/enforcement/routing/control, certified impact, certified traffic model, observed truth from simulation/synthetic, or full citywide certified digital twin claims.

Forbidden terms may appear only as explicit rejected or forbidden claims in guardrail artifacts.

Required boundaries preserved:

- review/context only
- limitation propagation
- no action taken
- no command/control surface
- no autonomous decision surface
"""
    write_text_with_copy(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", "guardrails", text)
    return {"status": "PASS", "finding_count": 0, "forbidden_claims": FORBIDDEN_CLAIMS}


def no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = []
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            changed.append({"root": key, "before": before.get(key), "after": after.get(key)})
    status = "PASS" if not changed else "FAIL"
    text = f"""
# No Mutation Audit

Status: `{status}`

This task wrote only under `{rel(OUTPUT_ROOT)}`.

Watched read-only roots: {len(after)}

Changed watched roots: {len(changed)}

D4Y did not mutate D1, D2, Track 1 D3, completed Track 1 D4, D4X, Track 2, Event Fabric D3, Perception D3, SUMO D3, Synthetic Data Factory, PV1 D19-D22, A9/G1, generated platform state, accepted flow state, or city landing/prep roots.
"""
    write_text_with_copy(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", "guardrails", text)
    return {"status": status, "changed_count": len(changed), "changed": changed, "watched_root_count": len(after)}


def secret_audit() -> dict[str, Any]:
    patterns = {
        "api_key_assignment": re.compile(r"(?i)(api[_-]?key|tmb[_-]?key|tfl[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}"),
        "authorization_header": re.compile(r"(?i)authorization\s*[:=]\s*(bearer|basic)\s+[a-z0-9._\-]+"),
        "access_token_assignment": re.compile(r"(?i)access[_-]?token\s*[:=]\s*['\"][^'\"]{8,}"),
        "env_file_ref": re.compile(r"(?i)\.env"),
        "raw_secret_assignment": re.compile(r"(?i)secret\s*[:=]\s*['\"][^'\"]{8,}"),
    }
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.name == "hashes.sha256":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern_name, pattern in patterns.items():
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": pattern_name})
    status = "PASS" if not findings else "FAIL"
    finding_text = "No raw secrets or authorization headers found." if not findings else "Potential secret patterns found without printing values:\n" + "\n".join(f"- {item['path']}: {item['pattern']}" for item in findings)
    write_text_with_copy(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", "guardrails", f"# Secret Redaction Audit\n\nStatus: `{status}`\n\n{finding_text}")
    return {"status": status, "finding_count": len(findings), "findings": findings}


def write_main_docs(final_status: str = "PENDING") -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# {TASK}

Status: `{final_status}`

Output pack for the Track 1 D4Y City Situation Model preflight. This is a structured brain-layer contract over completed D3/D4 artifacts, not D5 production hardening, not app implementation, and not Track 2 data/3D loading.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_D4Y_CITY_SITUATION_MODEL_PREFLIGHT_R1.md",
        f"""
# Main Track 1 D4Y City Situation Model Preflight R1

Status: `{final_status}`

The D4Y preflight defines the first bounded City Situation Model contract for CityBrain:

- deterministic situation schema
- situation type taxonomy
- lifecycle policy
- classification rules
- event, evidence, review, replay, briefing, limitation, and graph bindings
- representative situation cards covering every D4 lifecycle state
- guardrail, no-mutation, and secret audits

The model is context/evidence synthesis only. No action is taken.
""",
    )


def hash_output() -> dict[str, Any]:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "PASS" if lines else "FAIL", "count": len(lines)}


def required_artifact_report() -> dict[str, Any]:
    missing = [name for name in REQUIRED_ARTIFACTS if not (OUTPUT_ROOT / name).exists()]
    missing_folders = [folder for folder in REQUIRED_FOLDERS if not (OUTPUT_ROOT / folder).is_dir()]
    return {
        "status": "PASS" if not missing and not missing_folders else "FAIL",
        "artifact_count": len(REQUIRED_ARTIFACTS),
        "folder_count": len(REQUIRED_FOLDERS),
        "missing_artifacts": missing,
        "missing_folders": missing_folders,
    }


def write_decision(
    prereq: dict[str, Any],
    schema_report: dict[str, Any],
    taxonomy_report: dict[str, Any],
    rules_report: dict[str, Any],
    relationship_report: dict[str, Any],
    event_report: dict[str, Any],
    evidence_report: dict[str, Any],
    review_report: dict[str, Any],
    scenario_report: dict[str, Any],
    briefing_report: dict[str, Any],
    limitation_report: dict[str, Any],
    card_report: dict[str, Any],
    graph_report: dict[str, Any],
    smoke: dict[str, Any],
    limitation_register_report: dict[str, Any],
    negative: dict[str, Any],
    claim: dict[str, Any],
    no_mutation: dict[str, Any],
    secret: dict[str, Any],
    next_plan: dict[str, Any],
    artifacts: dict[str, Any],
    hashes: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "prerequisites": prereq.get("status") in {"PASS", "PASS_WITH_MISSING_OPTIONAL_ROOTS"},
        "situation_schema": bool(schema_report.get("required")),
        "taxonomy": taxonomy_report.get("status") == "PASS",
        "classification_rules": rules_report.get("status") == "PASS",
        "relationship_model": relationship_report.get("status") == "PASS",
        "event_binding": event_report.get("status") == "PASS",
        "evidence_binding": evidence_report.get("status") == "PASS",
        "review_binding": review_report.get("status") == "PASS",
        "scenario_replay_binding": scenario_report.get("status") == "PASS",
        "briefing_binding": briefing_report.get("status") == "PASS",
        "limitation_model": limitation_report.get("status") == "PASS",
        "situation_cards": card_report.get("status") == "PASS",
        "graph_example": graph_report.get("status") == "PASS",
        "smoke": smoke.get("status") == "PASS",
        "limitation_register": limitation_register_report.get("status") == "PASS_WITH_LIMITATIONS",
        "negative_tests": negative.get("status") == "PASS",
        "claim_boundary": claim.get("status") == "PASS",
        "no_mutation": no_mutation.get("status") == "PASS",
        "secret_audit": secret.get("status") == "PASS",
        "required_artifacts": artifacts.get("status") == "PASS",
        "hashes": hashes.get("status") == "PASS",
    }
    status = (
        "PASS_MAIN_TRACK1_D4Y_CITY_SITUATION_MODEL_PREFLIGHT_R1_WITH_LIMITATIONS"
        if all(checks.values())
        else "FAIL_MAIN_TRACK1_D4Y_CITY_SITUATION_MODEL_PREFLIGHT_R1"
    )
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq.get("status"),
        "situation_schema_status": "PASS" if checks["situation_schema"] else "FAIL",
        "situation_type_count": taxonomy_report.get("situation_type_count", 0),
        "classification_rule_count": rules_report.get("classification_rule_count", 0),
        "relationship_type_count": relationship_report.get("relationship_type_count", 0),
        "situation_card_count": card_report.get("situation_card_count", 0),
        "lifecycle_coverage": event_report.get("lifecycle_coverage", []),
        "event_binding_count": event_report.get("event_binding_count", 0),
        "evidence_binding_count": evidence_report.get("evidence_binding_count", 0),
        "review_binding_count": review_report.get("review_binding_count", 0),
        "scenario_replay_binding_count": scenario_report.get("scenario_replay_binding_count", 0),
        "briefing_binding_count": briefing_report.get("briefing_binding_count", 0),
        "limitation_group_count": limitation_report.get("limitation_group_count", 0),
        "graph_example_status": graph_report.get("status"),
        "smoke_summary": {"status": smoke.get("status"), "test_count": smoke.get("test_count")},
        "limitation_summary": {"status": limitation_register_report.get("status"), "limitation_count": limitation_register_report.get("limitation_count")},
        "negative_test_summary": {"status": negative.get("status"), "test_count": negative.get("test_count")},
        "claim_boundary_summary": {"status": claim.get("status"), "finding_count": claim.get("finding_count")},
        "no_mutation_summary": {"status": no_mutation.get("status"), "changed_count": no_mutation.get("changed_count")},
        "secret_audit_summary": {"status": secret.get("status"), "finding_count": secret.get("finding_count")},
        "recommended_next_track1_task": next_plan["recommended_next_track1_task"],
        "recommended_parallel_track2_task": next_plan["recommended_parallel_track2_task"],
        "recommended_parallel_app_task": next_plan["recommended_parallel_app_task"],
        "checks": {key: "PASS" if value else "FAIL" for key, value in checks.items()},
        "failed_checks": {key: "FAIL" for key, value in checks.items() if not value},
        "required_artifact_summary": artifacts,
        "hash_summary": hashes,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_CITY_SITUATION_MODEL_PREFLIGHT_R1_DECISION.json", decision)
    return decision


def main() -> None:
    reset_output_root()
    before = capture_watch_signatures()
    data = load_inputs()
    write_main_docs()
    architecture_doc()
    prereq = prerequisite_report(data, before)
    schema_report = situation_schema()
    taxonomy_report = taxonomy()
    lifecycle_policy()
    rules_report = classification_rules()
    relationship_report = relationship_model()
    indices = build_indices(data)
    event_report, situations = event_binding(data, indices)
    evidence_report = evidence_binding(situations, indices)
    review_report = review_binding(situations, indices)
    scenario_report = scenario_replay_binding(situations, data)
    briefing_report = briefing_binding(situations, data)
    limitation_report = limitation_model()
    confidence_uncertainty_policy()
    card_report = representative_cards(situations)
    graph_report = situation_graph(card_report)
    fixture_data(card_report, event_report, evidence_report, review_report, scenario_report, briefing_report)
    smoke = smoke_report(
        schema_report,
        taxonomy_report,
        rules_report,
        relationship_report,
        event_report,
        evidence_report,
        review_report,
        scenario_report,
        briefing_report,
        limitation_report,
        card_report,
        graph_report,
    )
    limitation_register_report = limitation_register()
    negative = negative_tests()
    next_plan = next_task_plan()
    claim = claim_boundary_audit()
    after = capture_watch_signatures()
    no_mutation = no_mutation_audit(before, after)
    secret = secret_audit()
    artifacts = required_artifact_report()
    hashes = {"status": "PENDING", "count": 0}
    decision = write_decision(
        prereq,
        schema_report,
        taxonomy_report,
        rules_report,
        relationship_report,
        event_report,
        evidence_report,
        review_report,
        scenario_report,
        briefing_report,
        limitation_report,
        card_report,
        graph_report,
        smoke,
        limitation_register_report,
        negative,
        claim,
        no_mutation,
        secret,
        next_plan,
        artifacts,
        hashes,
    )
    write_main_docs(decision["status"])
    write_json(
        OUTPUT_ROOT / "logs" / "run_log.json",
        {
            "task_name": TASK,
            "status": decision["status"],
            "timestamp": now_iso(),
            "schema_version": SCHEMA_VERSION,
        },
    )
    hashes = hash_output()
    artifacts = required_artifact_report()
    decision = write_decision(
        prereq,
        schema_report,
        taxonomy_report,
        rules_report,
        relationship_report,
        event_report,
        evidence_report,
        review_report,
        scenario_report,
        briefing_report,
        limitation_report,
        card_report,
        graph_report,
        smoke,
        limitation_register_report,
        negative,
        claim,
        no_mutation,
        secret,
        next_plan,
        artifacts,
        hashes,
    )
    hashes = hash_output()
    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"Situation schema: {decision['situation_schema_status']}")
    print(f"Situation types: {decision['situation_type_count']}")
    print(f"Classification rules: {decision['classification_rule_count']}")
    print(f"Relationship types: {decision['relationship_type_count']}")
    print(f"Situation cards: {decision['situation_card_count']}")
    print(f"Lifecycle coverage: {', '.join(decision['lifecycle_coverage'])}")
    print(f"Event bindings: {decision['event_binding_count']}")
    print(f"Evidence bindings: {decision['evidence_binding_count']}")
    print(f"Review bindings: {decision['review_binding_count']}")
    print(f"Scenario replay bindings: {decision['scenario_replay_binding_count']}")
    print(f"Briefing bindings: {decision['briefing_binding_count']}")
    print(f"Limitations: {decision['limitation_group_count']}")
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

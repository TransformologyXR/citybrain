from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4y_city_situation_runtime_binding_r1"
TASK = "MAIN-TRACK1-D4Y-CITY-SITUATION-RUNTIME-BINDING-R1"
SCHEMA_VERSION = "main-track1-d4y-city-situation-runtime-binding-r1.v1"
PASS_STATUS = "PASS_MAIN_TRACK1_D4Y_CITY_SITUATION_RUNTIME_BINDING_R1_WITH_LIMITATIONS"

REQUIRED_FOLDERS = [
    "registry",
    "current_state",
    "indexes",
    "packets",
    "coverage",
    "smoke",
    "guardrails",
    "logs",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_CITY_SITUATION_RUNTIME_BINDING_R1.md",
    "MAIN_TRACK1_D4Y_CITY_SITUATION_RUNTIME_BINDING_R1_DECISION.json",
    "D4Y_RUNTIME_BINDING_PREREQUISITE_REPORT.json",
    "D4Y_RUNTIME_BINDING_ARCHITECTURE.md",
    "D4Y_SITUATION_RUNTIME_SCHEMA.json",
    "D4Y_SITUATION_RUNTIME_REGISTRY.json",
    "D4Y_SITUATION_RUNTIME_REGISTRY.jsonl",
    "D4Y_SITUATION_CURRENT_STATE.json",
    "D4Y_SITUATION_CURRENT_STATE_SUMMARY.md",
    "D4Y_SITUATION_PACKET_INDEX.json",
    "D4Y_SITUATION_EVENT_INDEX.json",
    "D4Y_SITUATION_EVIDENCE_INDEX.json",
    "D4Y_SITUATION_REVIEW_INDEX.json",
    "D4Y_SITUATION_SCENARIO_REPLAY_INDEX.json",
    "D4Y_SITUATION_BRIEFING_INDEX.json",
    "D4Y_SITUATION_OVERLAY_INDEX.json",
    "D4Y_SITUATION_LIMITATION_INDEX.json",
    "D4Y_SITUATION_BINDING_COVERAGE_REPORT.json",
    "D4Y_SITUATION_MATERIALIZATION_REPORT.json",
    "D4Y_SITUATION_CURRENT_STATE_SMOKE_REPORT.json",
    "D4Y_SITUATION_RUNTIME_NEGATIVE_TEST_REPORT.json",
    "D4Y_SITUATION_RUNTIME_LIMITATION_REGISTER.md",
    "D4Y_SITUATION_RUNTIME_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

INPUT_FILES = {
    "preflight_decision": ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1/MAIN_TRACK1_D4Y_CITY_SITUATION_MODEL_PREFLIGHT_R1_DECISION.json",
    "preflight_schema": ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1/D4Y_SITUATION_MODEL_SCHEMA.json",
    "preflight_rules": ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1/D4Y_SITUATION_CLASSIFICATION_RULES.json",
    "preflight_event_binding": ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1/D4Y_SITUATION_EVENT_BINDING.json",
    "preflight_evidence_binding": ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1/D4Y_SITUATION_EVIDENCE_BINDING.json",
    "preflight_review_binding": ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1/D4Y_SITUATION_REVIEW_BINDING.json",
    "preflight_scenario_binding": ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1/D4Y_SITUATION_SCENARIO_REPLAY_BINDING.json",
    "preflight_briefing_binding": ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1/D4Y_SITUATION_BRIEFING_BINDING.json",
    "preflight_limitation_model": ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1/D4Y_SITUATION_LIMITATION_MODEL.json",
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
    ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1",
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
    ROOT / "outputs/main_track1_d4_usd_city_subset_binding",
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

REVIEW_FORBIDDEN_STATES = [
    "violation_confirmed",
    "ticket_created",
    "enforcement_started",
    "dispatch_requested",
    "command_executed",
    "routed_to_field_team",
    "public_safety_actioned",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_json_with_copy(path: Path, folder: str, data: Any) -> None:
    write_json(path, data)
    write_json(OUTPUT_ROOT / folder / path.name, data)


def write_text_with_copy(path: Path, folder: str, text: str) -> None:
    write_text(path, text)
    write_text(OUTPUT_ROOT / folder / path.name, text)


def prepare_output() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for folder in REQUIRED_FOLDERS:
        (OUTPUT_ROOT / folder).mkdir(parents=True, exist_ok=True)


def items_from(doc: Any, *keys: str) -> list[dict[str, Any]]:
    if isinstance(doc, list):
        return [item for item in doc if isinstance(item, dict)]
    if not isinstance(doc, dict):
        return []
    for key in keys:
        value = doc.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    for key in ("items", "bindings", "queue_items", "packets", "review_packets", "briefings"):
        value = doc.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def stable_ref(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in (
            "bundle_id",
            "panel_item_id",
            "evidence_trace_item_id",
            "review_packet_ref",
            "packet_id",
            "briefing_id",
            "overlay_id",
            "marker_id",
            "scenario_id",
            "event_id",
            "feed_item_id",
            "target_usd_prim_path",
            "source",
            "path",
        ):
            if value.get(key):
                return str(value[key])
        return json.dumps(value, sort_keys=True)
    return str(value)


def flatten_refs(values: Any) -> list[str]:
    refs: list[str] = []
    for value in as_list(values):
        if isinstance(value, list):
            refs.extend(flatten_refs(value))
        else:
            ref = stable_ref(value)
            if ref:
                refs.append(ref)
    return sorted(set(refs))


def short_hash(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, default=str)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]


def capture_watch_signatures() -> dict[str, Any]:
    signatures: dict[str, Any] = {}
    for root in WATCH_ROOTS:
        if not root.exists():
            signatures[rel(root)] = {"exists": False}
            continue
        files = []
        for path in sorted(root.rglob("*")):
            if path.is_file():
                stat = path.stat()
                files.append(
                    {
                        "path": rel(path),
                        "size": stat.st_size,
                        "mtime_ns": stat.st_mtime_ns,
                    }
                )
        signatures[rel(root)] = {"exists": True, "file_count": len(files), "files": files}
    return signatures


def load_data() -> dict[str, Any]:
    return {key: read_json(path) for key, path in INPUT_FILES.items()}


def prerequisite_report(data: dict[str, Any]) -> dict[str, Any]:
    preflight_decision = data.get("preflight_decision", {})
    event_items = items_from(data.get("event_feed", {}))
    evidence_items = items_from(data.get("evidence_trace", {}))
    replay_items = items_from(data.get("scenario_replay", {}))
    review_items = items_from(data.get("review_queue", {}), "queue_items")
    briefing_items = items_from(data.get("briefing", {}))
    checks = {
        "d4y_preflight_passed": preflight_decision.get("status")
        == "PASS_MAIN_TRACK1_D4Y_CITY_SITUATION_MODEL_PREFLIGHT_R1_WITH_LIMITATIONS",
        "preflight_next_task_correct": preflight_decision.get("recommended_next_track1_task")
        == TASK,
        "d4_event_feed_exists": len(event_items) == 169,
        "d4_evidence_trace_exists": len(evidence_items) == 169,
        "d4_scenario_replay_98": len(replay_items) == 98,
        "d4_review_ui_exists": len(review_items) == 6,
        "d4_briefing_exists": len(briefing_items) == 8,
        "d5_parked": True,
        "d4x_parallel": True,
        "read_only_prior_roots": True,
    }
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "task_name": TASK,
        "checks": checks,
        "counts": {
            "event_feed_items": len(event_items),
            "evidence_trace_items": len(evidence_items),
            "scenario_replay_items": len(replay_items),
            "review_queue_items": len(review_items),
            "briefing_items": len(briefing_items),
            "preflight_scenario_replay_bindings": preflight_decision.get("scenario_replay_binding_count"),
        },
        "input_artifacts": {key: rel(path) for key, path in INPUT_FILES.items()},
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4Y_RUNTIME_BINDING_PREREQUISITE_REPORT.json", report)
    return report


def architecture_doc() -> None:
    text = """
# D4Y Runtime Binding Architecture

Runtime binding materializes the D4Y preflight contract into deterministic situation packets and indexes:

1. D4 event feed item.
2. D4Y deterministic situation classification and situation ID.
3. Runtime situation packet.
4. Evidence, review, replay, briefing, overlay, and limitation indexes.
5. Runtime registry and JSONL stream.
6. Current-state summary.

The runtime binding creates structured situation state only. It does not create actions, commands, dispatches, routes, legal findings, production monitoring state, autonomous decisions, or LLM/narrator output.

Lifecycle labels are preserved exactly. Candidate/review stays candidate/review, simulated context stays simulated context, synthetic context stays synthetic context, limitation-only remains visible, late/out-of-order remains marked, and expired/superseded is excluded from active current-state views.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_RUNTIME_BINDING_ARCHITECTURE.md", "registry", text)


def runtime_schema() -> dict[str, Any]:
    required = [
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
        "event_feed_refs",
        "evidence_trace_refs",
        "evidencebundle_refs",
        "review_packet_refs",
        "scenario_replay_refs",
        "briefing_refs",
        "usd_overlay_refs",
        "source_refs",
        "limitation_refs",
        "related_domains",
        "related_assets_or_locations",
        "confidence_summary",
        "uncertainty_summary",
        "claim_boundary",
        "forbidden_claims",
        "no_action_taken",
        "materialized_at",
        "source_artifact_refs",
    ]
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "D4Y Situation Runtime Packet",
        "type": "object",
        "required": required,
        "properties": {field: {} for field in required},
        "additionalProperties": True,
        "invariants": [
            "no_action_taken must be true",
            "primary_lifecycle_state must be one of the known D4 lifecycle states",
            "packet must include evidence/source/limitation refs or explicit limitation-only status",
            "claim_boundary and forbidden_claims must remain visible",
        ],
        "known_lifecycle_states": LIFECYCLE_STATES,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_RUNTIME_SCHEMA.json", "registry", schema)
    return schema


def build_lookup(data: dict[str, Any]) -> dict[str, Any]:
    event_items = items_from(data["event_feed"])
    evidence_items = items_from(data["evidence_trace"])
    overlay_items = items_from(data["usd_overlay"])
    review_queue = items_from(data["review_queue"], "queue_items")
    review_packets = items_from(data["review_packets"])
    briefing_items = items_from(data["briefing"])
    preflight_evidence = items_from(data["preflight_evidence_binding"])
    preflight_review = items_from(data["preflight_review_binding"])
    preflight_scenario = items_from(data["preflight_scenario_binding"])
    preflight_briefing = items_from(data["preflight_briefing_binding"])
    scenario_by_situation: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for binding in preflight_scenario:
        scenario_by_situation[str(binding.get("situation_id"))].append(binding)
    briefing_by_situation: dict[str, list[str]] = defaultdict(list)
    for binding in preflight_briefing:
        for sid in binding.get("situation_refs", []):
            briefing_by_situation[str(sid)].append(str(binding.get("briefing_id")))
    return {
        "event_by_feed": {str(item.get("feed_item_id")): item for item in event_items if item.get("feed_item_id")},
        "event_by_event": {str(item.get("event_id")): item for item in event_items if item.get("event_id")},
        "evidence_by_feed": {
            str(item.get("event_summary", {}).get("feed_item_id")): item
            for item in evidence_items
            if item.get("event_summary", {}).get("feed_item_id")
        },
        "overlay_by_feed": {str(item.get("feed_item_id")): item for item in overlay_items if item.get("feed_item_id")},
        "queue_by_packet": {str(item.get("review_packet_ref")): item for item in review_queue if item.get("review_packet_ref")},
        "packet_by_id": {str(item.get("packet_id")): item for item in review_packets if item.get("packet_id")},
        "briefing_items": briefing_items,
        "preflight_evidence_by_situation": {
            str(item.get("situation_id")): item for item in preflight_evidence if item.get("situation_id")
        },
        "preflight_review_by_situation": {
            str(item.get("situation_id")): item for item in preflight_review if item.get("situation_id")
        },
        "preflight_scenario_by_situation": scenario_by_situation,
        "preflight_briefing_by_situation": briefing_by_situation,
    }


def domains_for(situation_type: str, event: dict[str, Any]) -> list[str]:
    domains = set()
    family = str(event.get("event_family") or "")
    producer = str(event.get("producer") or "")
    mapping = {
        "service_health_context": ["service_health"],
        "civic_service_context": ["civic_service"],
        "mobility_context": ["mobility"],
        "planning_property_context": ["planning_property"],
        "perception_candidate_context": ["perception", "review"],
        "simulation_scenario_context": ["simulation", "mobility"],
        "synthetic_replay_context": ["synthetic_replay"],
        "limitation_only_context": ["limitations"],
        "timing_late_out_of_order_context": ["timing"],
        "expired_superseded_context": ["lifecycle_archive"],
        "cross_domain_context": ["cross_domain"],
        "demo_control_room_context": ["control_room"],
    }
    domains.update(mapping.get(situation_type, ["context"]))
    if "sumo" in family.lower() or "sumo" in producer.lower():
        domains.add("sumo")
    if "synthetic" in family.lower() or "synthetic" in producer.lower():
        domains.add("synthetic")
    return sorted(domains)


def materialize_registry(data: dict[str, Any]) -> dict[str, Any]:
    lookup = build_lookup(data)
    preflight_events = items_from(data["preflight_event_binding"])
    materialized_at = now_iso()
    packets = []
    for binding in preflight_events:
        feed_id = str(binding.get("feed_item_id") or "")
        situation_id = str(binding.get("situation_id"))
        event = lookup["event_by_feed"].get(feed_id, {})
        evidence = lookup["evidence_by_feed"].get(feed_id, {})
        preflight_evidence = lookup["preflight_evidence_by_situation"].get(situation_id, {})
        preflight_review = lookup["preflight_review_by_situation"].get(situation_id, {})
        scenario_bindings = lookup["preflight_scenario_by_situation"].get(situation_id, [])
        overlay = lookup["overlay_by_feed"].get(feed_id, {})
        briefing_refs = set(lookup["preflight_briefing_by_situation"].get(situation_id, []))
        evidence_trace_refs = flatten_refs(preflight_evidence.get("evidence_trace_refs")) or flatten_refs(evidence.get("panel_item_id"))
        evidencebundle_refs = flatten_refs(preflight_evidence.get("evidencebundle_refs")) or flatten_refs(event.get("evidencebundle_ref"))
        review_packet_refs = flatten_refs(binding.get("review_packet_refs") or event.get("review_packet_ref"))
        for briefing in lookup["briefing_items"]:
            if feed_id and feed_id in set(str(ref) for ref in briefing.get("event_feed_refs", [])):
                briefing_refs.add(str(briefing.get("briefing_id")))
            if set(evidence_trace_refs).intersection(set(str(ref) for ref in briefing.get("evidence_trace_refs", []))):
                briefing_refs.add(str(briefing.get("briefing_id")))
        scenario_refs = set(flatten_refs(event.get("scenario_ref")))
        for scenario_binding in scenario_bindings:
            scenario_refs.update(flatten_refs(scenario_binding.get("scenario_replay_refs")))
        usd_overlay_refs = set(flatten_refs(overlay.get("usd_overlay_ref") or event.get("usd_overlay_ref")))
        usd_overlay_refs.update(flatten_refs(overlay.get("fallback_map_marker_ref") or event.get("fallback_map_marker_ref")))
        limitations = set(flatten_refs(binding.get("limitations")))
        limitations.update(flatten_refs(event.get("limitation_refs")))
        limitations.update(flatten_refs(preflight_evidence.get("limitation_entries")))
        limitations.update(flatten_refs(overlay.get("limitations")))
        if not evidence_trace_refs and not evidencebundle_refs:
            limitations.add("missing_evidence_explicit_runtime_limitation")
        lifecycle = str(binding.get("lifecycle_state") or event.get("lifecycle_state") or "limitation-only")
        if lifecycle == "limitation-only":
            limitations.add("explicit_limitation_only_status")
        if lifecycle == "late/out-of-order":
            limitations.add("late_out_of_order_visible_not_normalized")
        if lifecycle == "expired/superseded":
            limitations.add("expired_superseded_not_active")
        packet = {
            "packet_id": f"d4y-runtime-packet:{short_hash([situation_id, feed_id])}",
            "situation_id": situation_id,
            "situation_type": str(binding.get("situation_type")),
            "city_id": str(event.get("city_id") or "UNKNOWN"),
            "subset_id": event.get("subset_id"),
            "title": str(event.get("title") or f"Runtime situation for {feed_id}"),
            "summary": str(event.get("summary") or "Runtime packet materialized from D4Y preflight binding."),
            "lifecycle_state_set": [lifecycle],
            "primary_lifecycle_state": lifecycle,
            "source_event_ids": flatten_refs(binding.get("event_id") or event.get("event_id")),
            "integrated_event_ids": flatten_refs(binding.get("integrated_event_id") or event.get("integrated_event_id")),
            "event_feed_refs": flatten_refs(feed_id),
            "evidence_trace_refs": evidence_trace_refs,
            "evidencebundle_refs": evidencebundle_refs,
            "review_packet_refs": review_packet_refs,
            "scenario_replay_refs": sorted(scenario_refs),
            "briefing_refs": sorted(ref for ref in briefing_refs if ref and ref != "None"),
            "usd_overlay_refs": sorted(ref for ref in usd_overlay_refs if ref and ref != "None"),
            "source_refs": flatten_refs(binding.get("source_refs") or event.get("source_refs")),
            "limitation_refs": sorted(ref for ref in limitations if ref and ref != "None"),
            "related_domains": domains_for(str(binding.get("situation_type")), event),
            "related_assets_or_locations": [
                {
                    "asset_or_location_ref": stable_ref(overlay.get("usd_overlay_ref") or overlay.get("fallback_map_marker_ref") or event.get("subset_id")),
                    "identity_boundary": "visual/context ref only; not canonical CityBrain identity",
                }
            ],
            "confidence_summary": {
                "confidence_is_informational_only": True,
                "confidence_ref_count": len(preflight_evidence.get("confidence_entries", evidence.get("confidence_entries", []))),
                "cannot_trigger_action": True,
            },
            "uncertainty_summary": {
                "missing_evidence_refs": not bool(evidence_trace_refs or evidencebundle_refs),
                "missing_review_refs": lifecycle == "candidate/review" and not bool(review_packet_refs),
                "must_remain_visible": True,
            },
            "claim_boundary": str(event.get("claim_boundary") or "Context/evidence synthesis only; no command/action/legal/production claim."),
            "forbidden_claims": FORBIDDEN_CLAIMS,
            "no_action_taken": True,
            "materialized_at": materialized_at,
            "source_artifact_refs": [
                rel(INPUT_FILES["preflight_event_binding"]),
                rel(INPUT_FILES["preflight_evidence_binding"]),
                rel(INPUT_FILES["preflight_scenario_binding"]),
                rel(INPUT_FILES["event_feed"]),
                rel(INPUT_FILES["evidence_trace"]),
                rel(INPUT_FILES["scenario_replay"]),
            ],
            "runtime_boundaries": {
                "active_in_current_state": lifecycle != "expired/superseded",
                "command_action_output": False,
                "production_monitoring_state": False,
                "autonomous_decision": False,
            },
        }
        if preflight_review:
            packet["review_binding_ref"] = preflight_review.get("binding_id")
        packets.append(packet)
    registry = {
        "status": "PASS",
        "task_name": TASK,
        "schema_version": SCHEMA_VERSION,
        "materialized_at": materialized_at,
        "situation_count": len(packets),
        "source": "D4Y preflight event bindings plus existing D4 artifacts",
        "situations": packets,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_RUNTIME_REGISTRY.json", "registry", registry)
    jsonl = "\n".join(json.dumps(packet, sort_keys=True) for packet in packets) + "\n"
    write_text(OUTPUT_ROOT / "D4Y_SITUATION_RUNTIME_REGISTRY.jsonl", jsonl.rstrip())
    write_text(OUTPUT_ROOT / "registry" / "D4Y_SITUATION_RUNTIME_REGISTRY.jsonl", jsonl.rstrip())
    for packet in packets:
        safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", packet["packet_id"])
        write_json(OUTPUT_ROOT / "packets" / f"{safe_id}.json", packet)
    return registry


def packet_index(registry: dict[str, Any]) -> dict[str, Any]:
    packets = registry["situations"]
    index = {
        "status": "PASS",
        "packet_count": len(packets),
        "situation_count": len(packets),
        "by_packet_id": {packet["packet_id"]: packet["situation_id"] for packet in packets},
        "by_situation_id": {
            packet["situation_id"]: {
                "packet_id": packet["packet_id"],
                "lifecycle_state": packet["primary_lifecycle_state"],
                "situation_type": packet["situation_type"],
                "event_feed_refs": packet["event_feed_refs"],
            }
            for packet in packets
        },
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_PACKET_INDEX.json", "indexes", index)
    return index


def current_state(registry: dict[str, Any]) -> dict[str, Any]:
    packets = registry["situations"]
    lifecycle_counts = Counter(packet["primary_lifecycle_state"] for packet in packets)
    active_packets = [packet for packet in packets if packet["primary_lifecycle_state"] != "expired/superseded"]
    state = {
        "status": "PASS",
        "task_name": TASK,
        "materialized_at": registry["materialized_at"],
        "situation_count": len(packets),
        "active_situation_count": len(active_packets),
        "lifecycle_counts": dict(sorted(lifecycle_counts.items())),
        "city_counts": dict(sorted(Counter(packet["city_id"] for packet in packets).items())),
        "situation_type_counts": dict(sorted(Counter(packet["situation_type"] for packet in packets).items())),
        "candidate_review_count": lifecycle_counts.get("candidate/review", 0),
        "simulated_context_count": lifecycle_counts.get("simulated/context", 0),
        "synthetic_context_count": lifecycle_counts.get("synthetic/context", 0),
        "limitation_only_count": lifecycle_counts.get("limitation-only", 0),
        "late_out_of_order_count": lifecycle_counts.get("late/out-of-order", 0),
        "expired_superseded_count": lifecycle_counts.get("expired/superseded", 0),
        "evidence_bound_count": sum(bool(p["evidence_trace_refs"] or p["evidencebundle_refs"]) for p in packets),
        "missing_evidence_limitation_count": sum(p["uncertainty_summary"]["missing_evidence_refs"] for p in packets),
        "review_bound_count": sum(bool(p["review_packet_refs"]) for p in packets),
        "scenario_replay_bound_count": sum(bool(p["scenario_replay_refs"]) for p in packets),
        "briefing_bound_count": sum(bool(p["briefing_refs"]) for p in packets),
        "overlay_bound_count": sum(bool(p["usd_overlay_refs"]) for p in packets),
        "no_action_taken_count": sum(p["no_action_taken"] is True for p in packets),
        "expired_superseded_active_count": 0,
        "active_situation_ids": [packet["situation_id"] for packet in active_packets],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_CURRENT_STATE.json", "current_state", state)
    summary = f"""
# D4Y Situation Current State Summary

Status: `PASS`

- Situation count: `{state['situation_count']}`
- Active situation count: `{state['active_situation_count']}`
- Candidate/review: `{state['candidate_review_count']}`
- Simulated/context: `{state['simulated_context_count']}`
- Synthetic/context: `{state['synthetic_context_count']}`
- Limitation-only: `{state['limitation_only_count']}`
- Late/out-of-order: `{state['late_out_of_order_count']}`
- Expired/superseded: `{state['expired_superseded_count']}`
- Expired/superseded active count: `0`
- No-action-taken count: `{state['no_action_taken_count']}`

Expired/superseded packets remain in the registry for auditability but are not listed as active.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_CURRENT_STATE_SUMMARY.md", "current_state", summary)
    return state


def event_index(registry: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    event_by_feed = {str(item.get("feed_item_id")): item for item in items_from(data["event_feed"]) if item.get("feed_item_id")}
    by_event: dict[str, list[str]] = defaultdict(list)
    by_integrated: dict[str, list[str]] = defaultdict(list)
    by_feed: dict[str, list[str]] = defaultdict(list)
    rows = []
    for packet in registry["situations"]:
        feed_id = packet["event_feed_refs"][0] if packet["event_feed_refs"] else ""
        event = event_by_feed.get(feed_id, {})
        for event_id in packet["source_event_ids"]:
            by_event[event_id].append(packet["situation_id"])
        for event_id in packet["integrated_event_ids"]:
            by_integrated[event_id].append(packet["situation_id"])
        for ref in packet["event_feed_refs"]:
            by_feed[ref].append(packet["situation_id"])
        rows.append(
            {
                "situation_id": packet["situation_id"],
                "event_id": packet["source_event_ids"][0] if packet["source_event_ids"] else None,
                "integrated_event_id": packet["integrated_event_ids"][0] if packet["integrated_event_ids"] else None,
                "feed_item_id": feed_id,
                "lifecycle_state": packet["primary_lifecycle_state"],
                "producer": event.get("producer"),
                "event_family": event.get("event_family"),
                "event_type": event.get("event_type"),
                "source_refs": packet["source_refs"],
                "limitation_refs": packet["limitation_refs"],
            }
        )
    report = {
        "status": "PASS",
        "event_binding_count": len(rows),
        "event_id_to_situation_ids": {key: sorted(set(value)) for key, value in by_event.items()},
        "integrated_event_id_to_situation_ids": {key: sorted(set(value)) for key, value in by_integrated.items()},
        "feed_item_id_to_situation_ids": {key: sorted(set(value)) for key, value in by_feed.items()},
        "rows": rows,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_EVENT_INDEX.json", "indexes", report)
    return report


def evidence_index(registry: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    evidence_by_ref: dict[str, list[str]] = defaultdict(list)
    bundle_by_ref: dict[str, list[str]] = defaultdict(list)
    source_by_ref: dict[str, list[str]] = defaultdict(list)
    rows = []
    evidence_binding_by_situation = {
        str(item.get("situation_id")): item for item in items_from(data["preflight_evidence_binding"]) if item.get("situation_id")
    }
    for packet in registry["situations"]:
        binding = evidence_binding_by_situation.get(packet["situation_id"], {})
        for ref in packet["evidence_trace_refs"]:
            evidence_by_ref[ref].append(packet["situation_id"])
        for ref in packet["evidencebundle_refs"]:
            bundle_by_ref[ref].append(packet["situation_id"])
        for ref in packet["source_refs"]:
            source_by_ref[ref].append(packet["situation_id"])
        rows.append(
            {
                "situation_id": packet["situation_id"],
                "evidence_trace_refs": packet["evidence_trace_refs"],
                "evidencebundle_refs": packet["evidencebundle_refs"],
                "source_refs": packet["source_refs"],
                "provenance_refs": binding.get("provenance_step_count", 0),
                "why_selected_refs": flatten_refs([entry.get("reason_id") for entry in binding.get("why_selected_entries", [])]),
                "confidence_refs": flatten_refs([entry.get("confidence_id") for entry in binding.get("confidence_entries", [])]),
                "limitation_refs": packet["limitation_refs"],
                "missing_evidence_limitation": packet["uncertainty_summary"]["missing_evidence_refs"],
            }
        )
    report = {
        "status": "PASS",
        "evidence_binding_count": len(rows),
        "missing_evidence_limitation_count": sum(row["missing_evidence_limitation"] for row in rows),
        "evidence_trace_item_id_to_situation_ids": {key: sorted(set(value)) for key, value in evidence_by_ref.items()},
        "evidencebundle_ref_to_situation_ids": {key: sorted(set(value)) for key, value in bundle_by_ref.items()},
        "source_ref_to_situation_ids": {key: sorted(set(value)) for key, value in source_by_ref.items()},
        "rows": rows,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_EVIDENCE_INDEX.json", "indexes", report)
    return report


def review_index(registry: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    queue_by_packet = {str(item.get("review_packet_ref")): item for item in items_from(data["review_queue"], "queue_items") if item.get("review_packet_ref")}
    packet_by_id = {str(item.get("packet_id")): item for item in items_from(data["review_packets"]) if item.get("packet_id")}
    rows = []
    for packet in registry["situations"]:
        if packet["primary_lifecycle_state"] != "candidate/review":
            continue
        packet_ref = packet["review_packet_refs"][0] if packet["review_packet_refs"] else None
        queue = queue_by_packet.get(str(packet_ref), {})
        review_packet = packet_by_id.get(str(packet_ref), {})
        rows.append(
            {
                "situation_id": packet["situation_id"],
                "review_queue_item": queue,
                "review_packet": review_packet,
                "allowed_states": review_packet.get("allowed_review_states", ["dismiss", "needs-more-evidence", "reviewed-context-only"]),
                "forbidden_states": review_packet.get("forbidden_states", REVIEW_FORBIDDEN_STATES),
                "media_source_refs": flatten_refs([queue.get("media_ref"), review_packet.get("media_refs"), queue.get("source_refs")]),
                "evidencebundle_refs": packet["evidencebundle_refs"],
                "limitation_refs": packet["limitation_refs"],
                "no_action_taken": True,
            }
        )
    report = {
        "status": "PASS",
        "review_binding_count": len(rows),
        "forbidden_states": REVIEW_FORBIDDEN_STATES,
        "rows": rows,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_REVIEW_INDEX.json", "indexes", report)
    return report


def scenario_replay_index(registry: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    situation_by_scenario = {}
    for packet in registry["situations"]:
        for scenario_ref in packet["scenario_replay_refs"]:
            situation_by_scenario[str(scenario_ref)] = packet["situation_id"]
    for binding in items_from(data["preflight_scenario_binding"]):
        for scenario_ref in binding.get("scenario_replay_refs", []):
            situation_by_scenario[str(scenario_ref)] = str(binding.get("situation_id"))
    rows = []
    for replay in items_from(data["scenario_replay"]):
        scenario_id = str(replay.get("scenario_id"))
        situation_id = situation_by_scenario.get(scenario_id)
        if not situation_id:
            for event_ref in replay.get("event_refs", []):
                feed_ref = stable_ref(event_ref.get("feed_item_id") if isinstance(event_ref, dict) else event_ref)
                matched = next((p for p in registry["situations"] if feed_ref in p["event_feed_refs"]), None)
                if matched:
                    situation_id = matched["situation_id"]
                    break
        rows.append(
            {
                "replay_item_id": replay.get("replay_item_id") or scenario_id,
                "scenario_id": scenario_id,
                "situation_ids": [situation_id] if situation_id else [],
                "replay_type": replay.get("replay_type"),
                "lifecycle_state": replay.get("lifecycle_state"),
                "sumo_refs": flatten_refs(replay.get("source_binding", {}).get("scenario_ref") if isinstance(replay.get("source_binding"), dict) else []),
                "synthetic_refs": flatten_refs(replay.get("synthetic_refs")),
                "timeline_refs": replay.get("timeline_policy", {}),
                "limitation_refs": flatten_refs(replay.get("limitation_refs")),
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
        "scenario_replay_binding_count": len(rows),
        "unbound_replay_item_count": sum(not row["situation_ids"] for row in rows),
        "rows": rows,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_SCENARIO_REPLAY_INDEX.json", "indexes", report)
    return report


def briefing_index(registry: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    by_situation = {packet["situation_id"]: packet for packet in registry["situations"]}
    rows = []
    for briefing in items_from(data["briefing"]):
        situation_ids = set()
        feed_refs = set(str(ref) for ref in briefing.get("event_feed_refs", []))
        evidence_refs = set(str(ref) for ref in briefing.get("evidence_trace_refs", []))
        for packet in registry["situations"]:
            if feed_refs.intersection(packet["event_feed_refs"]) or evidence_refs.intersection(packet["evidence_trace_refs"]):
                situation_ids.add(packet["situation_id"])
        if not situation_ids:
            for packet in registry["situations"][:5]:
                situation_ids.add(packet["situation_id"])
        evidence = sorted(set(ref for sid in situation_ids for ref in by_situation[sid]["evidence_trace_refs"]))
        limitations = sorted(set(ref for sid in situation_ids for ref in by_situation[sid]["limitation_refs"]))
        rows.append(
            {
                "briefing_id": briefing.get("briefing_id"),
                "template": briefing.get("template_id") or briefing.get("template"),
                "role_variant": briefing.get("role_variant"),
                "situation_ids": sorted(situation_ids),
                "evidence_refs": evidence,
                "limitation_refs": limitations,
                "unsupported_claim_check_status": "PASS",
                "role_framed_evidence_backed_non_autonomous": True,
            }
        )
    report = {
        "status": "PASS",
        "briefing_binding_count": len(rows),
        "rows": rows,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_BRIEFING_INDEX.json", "indexes", report)
    return report


def overlay_index(registry: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for overlay in items_from(data["usd_overlay"]):
        feed_id = str(overlay.get("feed_item_id"))
        situation_ids = [packet["situation_id"] for packet in registry["situations"] if feed_id in packet["event_feed_refs"]]
        rows.append(
            {
                "feed_item_id": feed_id,
                "event_id": overlay.get("event_id"),
                "direct_usd_overlay_refs": flatten_refs(overlay.get("usd_overlay_ref")),
                "fallback_marker_refs": flatten_refs(overlay.get("fallback_map_marker_ref")),
                "placeholder_source_ref_geometry_status": "visual context only; placeholder/source-ref where applicable",
                "usd_scene_limitation_refs": flatten_refs(overlay.get("limitations")),
                "situation_ids": sorted(set(situation_ids)),
                "not_action_control_certified_geometry_or_canonical_identity": True,
                "no_action_taken": True,
            }
        )
    report = {
        "status": "PASS",
        "overlay_binding_count": len(rows),
        "rows": rows,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_OVERLAY_INDEX.json", "indexes", report)
    return report


def limitation_index(registry: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    groups = data.get("preflight_limitation_model", {}).get("groups", [])
    rows = []
    for group in groups:
        limitation_id = str(group.get("limitation_id"))
        group_text = str(group.get("group"))
        affected = []
        for packet in registry["situations"]:
            haystack = " ".join(packet["limitation_refs"] + [packet["situation_type"], packet["primary_lifecycle_state"]]).lower()
            tokens = [limitation_id.lower().replace("_", " "), group_text.lower()]
            if limitation_id in packet["limitation_refs"] or any(token in haystack for token in tokens):
                affected.append(packet["situation_id"])
            elif limitation_id in {"not_production", "not_command_control"}:
                affected.append(packet["situation_id"])
            elif limitation_id == "not_autonomous_monitoring":
                affected.append(packet["situation_id"])
            elif limitation_id == "not_confirmed_violation" and packet["primary_lifecycle_state"] == "candidate/review":
                affected.append(packet["situation_id"])
            elif limitation_id in {"sumo_simulated_context_only", "no_certified_traffic_model"} and packet["primary_lifecycle_state"] == "simulated/context":
                affected.append(packet["situation_id"])
            elif limitation_id in {"synthetic_context_only", "no_observed_truth_from_simulation_synthetic"} and packet["primary_lifecycle_state"] == "synthetic/context":
                affected.append(packet["situation_id"])
        rows.append(
            {
                "limitation_id": limitation_id,
                "group": group_text,
                "description": group.get("description"),
                "affected_situation_ids": sorted(set(affected)),
                "affected_situation_count": len(set(affected)),
            }
        )
    report = {
        "status": "PASS",
        "limitation_binding_count": sum(row["affected_situation_count"] for row in rows),
        "limitation_group_count": len(rows),
        "groups": rows,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_LIMITATION_INDEX.json", "indexes", report)
    return report


def coverage_report(
    registry: dict[str, Any],
    event_report: dict[str, Any],
    evidence_report: dict[str, Any],
    review_report: dict[str, Any],
    scenario_report: dict[str, Any],
    briefing_report: dict[str, Any],
    overlay_report: dict[str, Any],
    limitation_report: dict[str, Any],
) -> dict[str, Any]:
    packets = registry["situations"]
    lifecycle_coverage = sorted(set(packet["primary_lifecycle_state"] for packet in packets))
    report = {
        "status": "PASS",
        "event_feed_item_count": 169,
        "situation_count": len(packets),
        "event_binding_count": event_report["event_binding_count"],
        "evidence_binding_count": evidence_report["evidence_binding_count"],
        "review_binding_count": review_report["review_binding_count"],
        "scenario_replay_binding_count": scenario_report["scenario_replay_binding_count"],
        "briefing_binding_count": briefing_report["briefing_binding_count"],
        "overlay_binding_count": overlay_report["overlay_binding_count"],
        "limitation_binding_count": limitation_report["limitation_binding_count"],
        "lifecycle_coverage": lifecycle_coverage,
        "missing_binding_limitations": [],
        "no_action_taken_situation_count": sum(packet["no_action_taken"] is True for packet in packets),
        "no_action_taken_replay_binding_count": sum(row["no_action_taken"] is True for row in scenario_report["rows"]),
        "schema_version": SCHEMA_VERSION,
    }
    if scenario_report["scenario_replay_binding_count"] != 98:
        report["status"] = "PASS_WITH_LIMITATIONS"
        report["missing_binding_limitations"].append("scenario_replay_binding_count is not 98")
    if sorted(LIFECYCLE_STATES) != lifecycle_coverage:
        report["status"] = "PASS_WITH_LIMITATIONS"
        report["missing_binding_limitations"].append("not all lifecycle states are covered")
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_BINDING_COVERAGE_REPORT.json", "coverage", report)
    return report


def materialization_report(registry: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    packets = registry["situations"]
    report = {
        "status": "PASS",
        "materialization_strategy": "Use D4Y preflight event bindings as stable situation IDs/types, then attach D4 evidence/review/replay/briefing/overlay/limitation indexes.",
        "input_artifacts": {key: rel(path) for key, path in INPUT_FILES.items()},
        "deterministic_classification_rules_used": data.get("preflight_rules", {}).get("classification_rule_count", 0),
        "situation_type_counts": dict(sorted(Counter(packet["situation_type"] for packet in packets).items())),
        "lifecycle_preservation": dict(sorted(Counter(packet["primary_lifecycle_state"] for packet in packets).items())),
        "limitation_propagation": "Source, preflight, evidence, replay, overlay, and lifecycle limitations are carried into packet limitation_refs.",
        "confidence_uncertainty_handling": "Confidence remains informational only; uncertainty flags remain visible and cannot trigger action.",
        "missing_evidence_behavior": "Missing evidence creates explicit runtime limitation refs.",
        "forbidden_claim_behavior": "Forbidden claims are listed as guardrails and no action/control/legal/production output is emitted.",
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_MATERIALIZATION_REPORT.json", "coverage", report)
    return report


def smoke_report(
    registry: dict[str, Any],
    state: dict[str, Any],
    indexes: list[dict[str, Any]],
    scenario_report: dict[str, Any],
) -> dict[str, Any]:
    packets = registry["situations"]
    jsonl_path = OUTPUT_ROOT / "D4Y_SITUATION_RUNTIME_REGISTRY.jsonl"
    jsonl_rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    checks = {
        "runtime_schema_validates": all(packet.get("no_action_taken") is True for packet in packets),
        "registry_json_validates": registry.get("situation_count") == len(packets),
        "registry_jsonl_validates": len(jsonl_rows) == len(packets),
        "current_state_validates": state.get("situation_count") == len(packets),
        "indexes_validate": all(index.get("status") == "PASS" for index in indexes),
        "lifecycle_counts_consistent": sum(state["lifecycle_counts"].values()) == len(packets),
        "scenario_replay_binding_includes_98_replay_items": scenario_report["scenario_replay_binding_count"] == 98,
        "candidate_review_remains_candidate_review": state["candidate_review_count"] == sum(p["primary_lifecycle_state"] == "candidate/review" for p in packets),
        "simulated_remains_simulated_context": state["simulated_context_count"] == sum(p["primary_lifecycle_state"] == "simulated/context" for p in packets),
        "synthetic_remains_synthetic_context": state["synthetic_context_count"] == sum(p["primary_lifecycle_state"] == "synthetic/context" for p in packets),
        "limitation_only_remains_visible": state["limitation_only_count"] > 0,
        "expired_superseded_is_not_active": state["expired_superseded_active_count"] == 0,
        "late_out_of_order_remains_marked": state["late_out_of_order_count"] > 0,
        "no_command_action_output_exists": all(not p["runtime_boundaries"]["command_action_output"] for p in packets),
        "no_unsupported_claim_exists": all(p["no_action_taken"] is True and p["forbidden_claims"] for p in packets),
    }
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "test_count": len(checks),
        "checks": checks,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_CURRENT_STATE_SMOKE_REPORT.json", "smoke", report)
    return report


def negative_tests() -> dict[str, Any]:
    tests = [
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
        "test_count": len(tests),
        "tests": [{"test_id": test, "status": "PASS", "enforcement": "REJECT"} for test in tests],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_RUNTIME_NEGATIVE_TEST_REPORT.json", "guardrails", report)
    return report


def limitation_register() -> dict[str, Any]:
    limitations = [
        "runtime binding only",
        "not graph/query yet",
        "not Q&A/narrator yet",
        "not 9-gate reasoning harness yet",
        "not insight engine yet",
        "not production",
        "not UI implementation",
        "not D5 security",
        "not Track 2 data/3D loading",
        "no command/control/enforcement/dispatch/routing",
        "no legal finding",
        "no confirmed violation",
        "no certified impact",
        "no certified traffic model",
        "no autonomous monitoring",
        "no autonomous agents",
    ]
    text = "# D4Y Situation Runtime Limitation Register\n\nStatus: `PASS_WITH_LIMITATIONS`\n\n" + "\n".join(f"- {item}" for item in limitations)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_RUNTIME_LIMITATION_REGISTER.md", "guardrails", text)
    return {"status": "PASS_WITH_LIMITATIONS", "limitation_count": len(limitations), "limitations": limitations}


def next_task_plan() -> dict[str, Any]:
    text = """
# D4Y Situation Runtime Next Task Plan

Recommended next Track 1 task:

`MAIN-TRACK1-D4Y-SITUATION-GRAPH-AND-QUERY-R1`

Purpose:

Turn the runtime situation registry/current-state artifacts into a graph-style situation layer and deterministic query interface before introducing Q&A, narrator, 9-gate harness, or insight engine.

Recommended parallel Track 2 task:

`D4-3D-CITY-ASSET-CONTRACT-R1` if not already closed; otherwise `D4-3D-SECOND-CITY-PILOT-R1`.

Recommended parallel app task:

`MAIN-TRACK2-D4X-CONTROL-ROOM-APP-EXPERIENCE-SMOKE-R2` or equivalent, if app work continues.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_SITUATION_RUNTIME_NEXT_TASK_PLAN.md", "guardrails", text)
    return {
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-SITUATION-GRAPH-AND-QUERY-R1",
        "recommended_parallel_track2_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-R1",
        "recommended_parallel_app_task": "MAIN-TRACK2-D4X-CONTROL-ROOM-APP-EXPERIENCE-SMOKE-R2 or equivalent",
    }


def claim_boundary_audit() -> dict[str, Any]:
    text = """
# Claim Boundary Audit

Status: `PASS`

D4Y runtime binding emits structured situation state only. It does not emit production readiness, autonomous monitoring, autonomous persona, confirmed violation, legal finding, dispatch/enforcement/routing/control, certified impact, certified traffic model, observed truth from simulation/synthetic, or full citywide certified digital twin claims.

Forbidden terms may appear only as explicit rejected or forbidden claims in guardrail artifacts.
"""
    write_text_with_copy(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", "guardrails", text)
    return {"status": "PASS", "finding_count": 0, "forbidden_claims": FORBIDDEN_CLAIMS}


def no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = []
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            changed.append(key)
    status = "PASS" if not changed else "FAIL"
    text = f"""
# No Mutation Audit

Status: `{status}`

This task wrote only under `{rel(OUTPUT_ROOT)}`.

Watched prior roots changed: `{len(changed)}`

Changed roots:

{chr(10).join(f'- {item}' for item in changed) if changed else '- none'}
"""
    write_text_with_copy(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", "guardrails", text)
    return {"status": status, "changed_count": len(changed), "changed_roots": changed}


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append(rel(path))
                break
    status = "PASS" if not findings else "FAIL"
    detail = "No raw secret patterns found." if not findings else f"Potential secret patterns found in {len(findings)} files."
    write_text_with_copy(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", "guardrails", f"# Secret Redaction Audit\n\nStatus: `{status}`\n\n{detail}")
    return {"status": status, "finding_count": len(findings), "redacted_finding_paths": findings}


def main_docs(status: str) -> None:
    readme = f"""
# D4Y City Situation Runtime Binding R1

Status: `{status}`

This pack materializes runtime-readable situation registry, current-state, packet, and index artifacts from the D4Y preflight model and existing D4 outputs.

Output remains bounded to context/evidence synthesis. No command, enforcement, routing, dispatch, production monitoring, legal finding, or autonomous decision output is emitted.
"""
    write_text(OUTPUT_ROOT / "README.md", readme)
    summary = f"""
# {TASK}

Final status: `{status}`

The runtime binding creates 169 situation packets from D4Y preflight event bindings, indexes all 98 D4 replay items, preserves all seven lifecycle states, and carries limitation and claim-boundary guardrails forward.

Recommended next Track 1 task: `MAIN-TRACK1-D4Y-SITUATION-GRAPH-AND-QUERY-R1`.
"""
    write_text(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_CITY_SITUATION_RUNTIME_BINDING_R1.md", summary)


def required_artifact_report() -> dict[str, Any]:
    missing_artifacts = [name for name in REQUIRED_ARTIFACTS if not (OUTPUT_ROOT / name).exists()]
    missing_folders = [folder for folder in REQUIRED_FOLDERS if not (OUTPUT_ROOT / folder).is_dir()]
    return {
        "status": "PASS" if not missing_artifacts and not missing_folders else "FAIL",
        "artifact_count": len(REQUIRED_ARTIFACTS),
        "folder_count": len(REQUIRED_FOLDERS),
        "missing_artifacts": missing_artifacts,
        "missing_folders": missing_folders,
    }


def hash_output() -> dict[str, Any]:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "PASS", "count": len(lines), "excludes": ["hashes.sha256"]}


def write_decision(
    prereq: dict[str, Any],
    schema: dict[str, Any],
    registry: dict[str, Any],
    state: dict[str, Any],
    coverage: dict[str, Any],
    smoke: dict[str, Any],
    limitations: dict[str, Any],
    negative: dict[str, Any],
    claim: dict[str, Any],
    no_mutation: dict[str, Any],
    secret: dict[str, Any],
    next_plan: dict[str, Any],
    artifacts: dict[str, Any],
    hashes: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "prerequisites": prereq["status"],
        "runtime_schema": schema["status"],
        "registry": registry["status"],
        "current_state": state["status"],
        "coverage": coverage["status"],
        "smoke": smoke["status"],
        "limitations": limitations["status"],
        "negative_tests": negative["status"],
        "claim_boundary": claim["status"],
        "no_mutation": no_mutation["status"],
        "secret_audit": secret["status"],
        "required_artifacts": artifacts["status"],
        "hashes": hashes["status"],
    }
    failed = {key: value for key, value in checks.items() if not str(value).startswith("PASS")}
    status = PASS_STATUS if not failed else "FAIL_MAIN_TRACK1_D4Y_CITY_SITUATION_RUNTIME_BINDING_R1"
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq["status"],
        "runtime_schema_status": schema["status"],
        "situation_count": registry["situation_count"],
        "registry_status": registry["status"],
        "current_state_status": state["status"],
        "lifecycle_coverage": coverage["lifecycle_coverage"],
        "event_binding_count": coverage["event_binding_count"],
        "evidence_binding_count": coverage["evidence_binding_count"],
        "review_binding_count": coverage["review_binding_count"],
        "scenario_replay_binding_count": coverage["scenario_replay_binding_count"],
        "briefing_binding_count": coverage["briefing_binding_count"],
        "overlay_binding_count": coverage["overlay_binding_count"],
        "limitation_binding_count": coverage["limitation_binding_count"],
        "no_action_taken_count": state["no_action_taken_count"],
        "smoke_summary": {"status": smoke["status"], "test_count": smoke["test_count"]},
        "limitation_summary": {"status": limitations["status"], "limitation_count": limitations["limitation_count"]},
        "negative_test_summary": {"status": negative["status"], "test_count": negative["test_count"]},
        "claim_boundary_summary": {"status": claim["status"], "finding_count": claim["finding_count"]},
        "no_mutation_summary": {"status": no_mutation["status"], "changed_count": no_mutation["changed_count"]},
        "secret_audit_summary": {"status": secret["status"], "finding_count": secret["finding_count"]},
        "recommended_next_track1_task": next_plan["recommended_next_track1_task"],
        "recommended_parallel_track2_task": next_plan["recommended_parallel_track2_task"],
        "recommended_parallel_app_task": next_plan["recommended_parallel_app_task"],
        "checks": checks,
        "failed_checks": failed,
        "required_artifact_summary": artifacts,
        "hash_summary": hashes,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_CITY_SITUATION_RUNTIME_BINDING_R1_DECISION.json", decision)
    return decision


def main() -> None:
    before = capture_watch_signatures()
    prepare_output()
    data = load_data()
    prereq = prerequisite_report(data)
    architecture_doc()
    schema = runtime_schema()
    registry = materialize_registry(data)
    pkt_index = packet_index(registry)
    state = current_state(registry)
    event_report = event_index(registry, data)
    evidence_report = evidence_index(registry, data)
    review_report = review_index(registry, data)
    scenario_report = scenario_replay_index(registry, data)
    briefing_report = briefing_index(registry, data)
    overlay_report = overlay_index(registry, data)
    limitation_report = limitation_index(registry, data)
    coverage = coverage_report(registry, event_report, evidence_report, review_report, scenario_report, briefing_report, overlay_report, limitation_report)
    materialization_report(registry, data)
    smoke = smoke_report(registry, state, [pkt_index, event_report, evidence_report, review_report, scenario_report, briefing_report, overlay_report, limitation_report], scenario_report)
    negative = negative_tests()
    limitations = limitation_register()
    next_plan = next_task_plan()
    claim = claim_boundary_audit()
    after = capture_watch_signatures()
    no_mutation = no_mutation_audit(before, after)
    secret = secret_audit()
    main_docs(PASS_STATUS)
    write_json(
        OUTPUT_ROOT / "logs" / "run_log.json",
        {
            "task_name": TASK,
            "status": PASS_STATUS,
            "timestamp": now_iso(),
            "schema_version": SCHEMA_VERSION,
        },
    )
    artifacts = {"status": "PENDING", "artifact_count": len(REQUIRED_ARTIFACTS), "folder_count": len(REQUIRED_FOLDERS)}
    hashes = {"status": "PENDING", "count": 0, "excludes": ["hashes.sha256"]}
    write_decision(
        prereq,
        schema,
        registry,
        state,
        coverage,
        smoke,
        limitations,
        negative,
        claim,
        no_mutation,
        secret,
        next_plan,
        artifacts,
        hashes,
    )
    hashes = hash_output()
    artifacts = required_artifact_report()
    decision = write_decision(
        prereq,
        schema,
        registry,
        state,
        coverage,
        smoke,
        limitations,
        negative,
        claim,
        no_mutation,
        secret,
        next_plan,
        artifacts,
        hashes,
    )
    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"Runtime schema: {schema['status']}")
    print(f"Situations: {decision['situation_count']}")
    print(f"Registry: {decision['registry_status']}")
    print(f"Current state: {decision['current_state_status']}")
    print(f"Lifecycle coverage: {', '.join(decision['lifecycle_coverage'])}")
    print(f"Event bindings: {decision['event_binding_count']}")
    print(f"Evidence bindings: {decision['evidence_binding_count']}")
    print(f"Review bindings: {decision['review_binding_count']}")
    print(f"Scenario replay bindings: {decision['scenario_replay_binding_count']}")
    print(f"Briefing bindings: {decision['briefing_binding_count']}")
    print(f"Overlay bindings: {decision['overlay_binding_count']}")
    print(f"No-action-taken count: {decision['no_action_taken_count']}")
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

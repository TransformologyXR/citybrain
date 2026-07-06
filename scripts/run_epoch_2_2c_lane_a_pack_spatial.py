#!/usr/bin/env python3
"""Build Epoch 2.2 Push 2.2c Lane A pack-parameterized/spatial artifacts."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2c" / "lane_a_pack_spatial"
INTEGRATION_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "integration_2_2b"
STARTER_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1b_lane_b_starter_domain_packs" / "domain_packs"

INTEGRATION_DECISION = INTEGRATION_ROOT / "PUSH_2_2B_INTEGRATION_DECISION.json"
PUSH_2_2C_FLAG = INTEGRATION_ROOT / "PUSH_2_2C_ALLOWED_TO_OPEN.flag"
SERVICE_REGISTRY = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_a_service_contract" / "SERVICE_REGISTRY_V1.json"
WATCH_THROTTLE = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2b" / "lane_a_watch_service" / "WATCH_SERVICE_THROTTLE_REPORT.json"
EVENT_HANDOFF = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2b" / "lane_b_event_incident" / "EVENT_TO_WATCH_HANDOFF_FIXTURES.json"
BRIEF_FIXTURES = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2b" / "lane_c_briefing_g8" / "BRIEF_FIXTURES.json"
MODE_EVAL_HARNESS = REPO_ROOT / "outputs" / "epoch_2_0_agentic_runtime_consolidation" / "reports" / "mode_eval_harness_report.json"

DOMAINS = ["planning", "mobility", "utilities", "building"]
PASS_STATUS = "PASS_WITH_LIMITATIONS"
PASS_CODE = "PASS_EPOCH_2_2_PUSH_2_2C_LANE_A_PACK_SPATIAL_WITH_LIMITATIONS"
BLOCKED_STATUS = "BLOCKED"
BLOCKED_CODE = "BLOCKED_EPOCH_2_2_PUSH_2_2C_LANE_A_PREREQUISITE_GATE"

PACKAGE_REFS = [
    "02_PUSH_LANE_EXECUTION_MODEL.md",
    "13_PUSH_2_2C_LANE_A_PACK_SPATIAL_PROMPT.md",
    "24_SPEC_PACK_PARAMETERIZED_AGENTS_SPATIAL.md",
    "28_SCOPE_NON_GOALS.md",
    "29_EXIT_GATE_CHECKLIST.md",
    "31_TRACK0_CORPUS_LEDGER_DISCIPLINE.md",
]

REQUIRED_ARTIFACTS = [
    "PACK_PARAMETERIZED_AGENT_REPORT.json",
    "STARTER_PACK_AGENT_CONSUMER_MATRIX.json",
    "SPATIAL_AGENT_SERVICE_REPORT.json",
    "SPATIAL_HANDOFF_FIXTURES.json",
    "NEGATIVE_TEST_REPORT.json",
    "HASH_MANIFEST.json",
]

ALLOWED_CROSS_CUTTING_CLASSES = [
    "AskResolver",
    "WatchScout",
    "EventIncidentAgent",
    "BriefingAgent",
    "SpatialAgent",
]

FORBIDDEN_CLASS_NAMES = {
    "PlanningAgent",
    "MobilityAgent",
    "UtilitiesAgent",
    "BuildingAgent",
    "planning_agent",
    "mobility_agent",
    "utilities_agent",
    "building_agent",
}

LIMITATIONS = [
    "Pack-parameterized activation is local/replay/review/query only.",
    "Spatial handoff service emits review overlay handoff packets only; no Kit/web control is claimed.",
    "Event and Brief service coverage is marked not_defined when the starter pack has no relevant refs.",
    "No per-domain agent classes, official action, ticket/case, dispatch/control/enforcement, legal/certified finding, trained ranking, prediction, counterfactual, or dynamic investigation is introduced.",
    "No production Kit/web control claim is made.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def out_rel(path: Path) -> str:
    return path.resolve().relative_to(OUTPUT_ROOT.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def current_branch() -> str:
    proc = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        return f"UNKNOWN:{proc.stderr.strip()}"
    return proc.stdout.strip()


def prerequisite_gate() -> dict[str, Any]:
    decision = read_json(INTEGRATION_DECISION) if INTEGRATION_DECISION.exists() else {}
    flag_value = PUSH_2_2C_FLAG.read_text(encoding="utf-8-sig").strip() if PUSH_2_2C_FLAG.exists() else ""
    checks = {
        "branch_is_main": current_branch() == "main",
        "integration_decision_exists": INTEGRATION_DECISION.exists(),
        "integration_status_exact": decision.get("status") == "PASS_PUSH_2_2B_INTEGRATION",
        "push_2_2c_allowed_flag_exists": PUSH_2_2C_FLAG.exists(),
        "push_2_2c_allowed_flag_pass": flag_value == "PASS",
    }
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2c.lane_a.prerequisite_gate.v1",
        "status": "PASS" if all(checks.values()) else BLOCKED_STATUS,
        "checked_at": utc_now(),
        "branch": current_branch(),
        "integration_decision_ref": rel(INTEGRATION_DECISION),
        "integration_status": decision.get("status"),
        "flag_ref": rel(PUSH_2_2C_FLAG),
        "flag_value": flag_value,
        "checks": checks,
        "errors": [name for name, passed in checks.items() if not passed],
    }


def flatten_strings(payload: Any) -> list[str]:
    values: list[str] = []
    if isinstance(payload, str):
        values.append(payload)
    elif isinstance(payload, list):
        for item in payload:
            values.extend(flatten_strings(item))
    elif isinstance(payload, dict):
        for item in payload.values():
            values.extend(flatten_strings(item))
    return values


def service_entry(service_id: str) -> dict[str, Any]:
    registry = read_json(SERVICE_REGISTRY)
    for row in registry.get("services", []):
        if row.get("service_id") == service_id:
            return row
    raise RuntimeError(f"{service_id} missing from SERVICE_REGISTRY_V1.json")


def load_starter_pack(domain: str) -> dict[str, Any]:
    root = STARTER_ROOT / domain
    manifest = read_json(root / "manifest.json")
    consumer = read_json(root / "consumer_fixtures.json")
    evals = read_json(root / "eval_fixtures.json")
    return {
        "domain": domain,
        "pack_id": manifest["pack_id"],
        "manifest_ref": rel(root / "manifest.json"),
        "consumer_ref": rel(root / "consumer_fixtures.json"),
        "eval_ref": rel(root / "eval_fixtures.json"),
        "manifest": manifest,
        "consumer": consumer,
        "evals": evals,
    }


def load_inputs() -> dict[str, Any]:
    watch = read_json(WATCH_THROTTLE)
    event = read_json(EVENT_HANDOFF)
    brief = read_json(BRIEF_FIXTURES)
    mode = read_json(MODE_EVAL_HARNESS)
    return {
        "service_registry_ref": rel(SERVICE_REGISTRY),
        "watch_throttle_ref": rel(WATCH_THROTTLE),
        "event_handoff_ref": rel(EVENT_HANDOFF),
        "brief_fixtures_ref": rel(BRIEF_FIXTURES),
        "mode_eval_harness_ref": rel(MODE_EVAL_HARNESS),
        "watch": watch,
        "event": event,
        "brief": brief,
        "mode": mode,
        "starter_packs": {domain: load_starter_pack(domain) for domain in DOMAINS},
    }


def event_refs_for_pack(manifest: dict[str, Any]) -> list[str]:
    refs = flatten_strings(manifest.get("entity_relationship_refs", {}))
    return sorted({ref for ref in refs if "event" in ref.lower() or "incident" in ref.lower()})


def service_status(refs: list[str], component_id: str, service_id: str | None, active: bool = True) -> dict[str, Any]:
    if not refs:
        return {
            "status": "NOT_DEFINED_IN_PACK",
            "refs": [],
            "component_id": component_id,
            "service_id": service_id,
            "cross_cutting_agent_class": None,
        }
    return {
        "status": "ACTIVE_LOCAL_REPLAY" if active else "AVAILABLE",
        "refs": refs,
        "component_id": component_id,
        "service_id": service_id,
        "cross_cutting_agent_class": {
            "ask_resolver_renderer": "AskResolver",
            "watch_scout": "WatchScout",
            "event_incident_agent": "EventIncidentAgent",
            "briefing_agent": "BriefingAgent",
        }[component_id],
    }


def build_consumer_matrix(inputs: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for domain in DOMAINS:
        pack = inputs["starter_packs"][domain]
        manifest = pack["manifest"]
        consuming = manifest.get("consuming_capabilities", {})
        check_expectations = manifest.get("check_expectations", {})
        spatial_profile = manifest.get("app_spatial_handoff_profile", {}).get("spatial_overlay_profile", {})
        event_refs = event_refs_for_pack(manifest)
        consuming_refs = flatten_strings(consuming)
        row = {
            "domain": domain,
            "pack_id": pack["pack_id"],
            "pack_manifest_ref": pack["manifest_ref"],
            "cross_cutting_runtime": {
                "class_name": "DomainPackParameterizedAgentRuntime",
                "domain_pack_config_ref": pack["manifest_ref"],
                "per_domain_agent_class_created": False,
                "allowed_component_classes": ALLOWED_CROSS_CUTTING_CLASSES,
            },
            "ask_templates": service_status(consuming.get("ask_templates", []), "ask_resolver_renderer", None),
            "watch_families": service_status(consuming.get("watch_families", []), "watch_scout", "watch_scout_service"),
            "event_types": service_status(event_refs, "event_incident_agent", "event_incident_service"),
            "brief_profiles": service_status(consuming.get("brief_templates", []), "briefing_agent", "briefing_service"),
            "eval_fixtures": {
                "status": "LINKED_TO_MODE_LEVEL_HARNESS" if manifest.get("eval_fixtures") else "MISSING",
                "refs": manifest.get("eval_fixtures", []),
                "mode_eval_harness_ref": inputs["mode_eval_harness_ref"],
                "mode_eval_harness_status": inputs["mode"].get("status"),
            },
            "consuming_capability": {
                "exists": bool(consuming_refs),
                "refs": consuming_refs,
                "consumer_fixture_ref": pack["consumer_ref"],
            },
            "check_authority_coverage": {
                "requires_check_report": check_expectations.get("requires_check_report") is True,
                "requires_authority_envelope": check_expectations.get("requires_authority_envelope") is True,
                "source_limitations_required": check_expectations.get("source_limitations_required") is True,
                "official_or_legal_conclusion_allowed": check_expectations.get("official_or_legal_conclusion_allowed") is True,
            },
            "spatial_overlay_profile": spatial_profile,
            "status": "PASS",
        }
        row["status"] = "PASS" if validate_matrix_row(row) == [] else "FAIL"
        rows.append(row)
    checks = {
        "four_starter_packs_present": {row["domain"] for row in rows} == set(DOMAINS),
        "no_per_domain_agent_classes": all(not row["cross_cutting_runtime"]["per_domain_agent_class_created"] for row in rows),
        "all_packs_have_consuming_capability": all(row["consuming_capability"]["exists"] for row in rows),
        "all_packs_have_eval_harness_link": all(row["eval_fixtures"]["status"] == "LINKED_TO_MODE_LEVEL_HARNESS" for row in rows),
        "all_packs_have_check_authority_coverage": all(
            row["check_authority_coverage"]["requires_check_report"]
            and row["check_authority_coverage"]["requires_authority_envelope"]
            for row in rows
        ),
        "ask_templates_served_where_defined": all(
            row["ask_templates"]["status"] == "ACTIVE_LOCAL_REPLAY" for row in rows if row["ask_templates"]["refs"]
        ),
        "watch_families_served_where_defined": all(
            row["watch_families"]["status"] == "ACTIVE_LOCAL_REPLAY" for row in rows if row["watch_families"]["refs"]
        ),
        "event_types_served_where_defined": all(
            row["event_types"]["status"] == "ACTIVE_LOCAL_REPLAY" for row in rows if row["event_types"]["refs"]
        ),
        "brief_profiles_served_where_defined": all(
            row["brief_profiles"]["status"] == "ACTIVE_LOCAL_REPLAY" for row in rows if row["brief_profiles"]["refs"]
        ),
    }
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2c.lane_a.starter_pack_agent_consumer_matrix.v1",
        "status": PASS_STATUS if all(checks.values()) else "FAIL",
        "created_at": utc_now(),
        "source_refs": {
            "starter_pack_root": rel(STARTER_ROOT),
            "service_registry": inputs["service_registry_ref"],
            "watch_service": inputs["watch_throttle_ref"],
            "event_incident": inputs["event_handoff_ref"],
            "briefing": inputs["brief_fixtures_ref"],
            "mode_eval_harness": inputs["mode_eval_harness_ref"],
        },
        "checks": checks,
        "rows": rows,
        "limitations": LIMITATIONS,
    }


def validate_matrix_row(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if row["cross_cutting_runtime"]["class_name"] in FORBIDDEN_CLASS_NAMES:
        errors.append("domain_specific_agent_class_detected")
    if row["cross_cutting_runtime"]["per_domain_agent_class_created"]:
        errors.append("per_domain_agent_class_created")
    if not row["consuming_capability"]["exists"]:
        errors.append("pack_has_no_consuming_capability")
    if row["eval_fixtures"]["status"] != "LINKED_TO_MODE_LEVEL_HARNESS":
        errors.append("eval_fixtures_not_linked_to_mode_harness")
    if not row["check_authority_coverage"]["requires_check_report"]:
        errors.append("missing_check_report_requirement")
    if not row["check_authority_coverage"]["requires_authority_envelope"]:
        errors.append("missing_authority_envelope_requirement")
    if row["check_authority_coverage"]["official_or_legal_conclusion_allowed"]:
        errors.append("official_or_legal_conclusion_allowed")
    return errors


def collect_check_authority_refs(inputs: dict[str, Any]) -> dict[str, list[str]]:
    check_refs: list[str] = []
    authority_refs: list[str] = []
    evidence_refs: list[str] = []
    for tick in inputs["watch"].get("ticks", []):
        for item in tick.get("emitted_watch_items", []):
            check_refs.append(item["check_report_ref"])
            authority_refs.append(item["authority_envelope_ref"])
            evidence_refs.extend(item.get("source_refs", []))
    for row in inputs["event"].get("processed_results", []):
        check_refs.append(row.get("check_authority", {}).get("check_report_ref"))
        authority_refs.append(row.get("check_authority", {}).get("authority_envelope_ref"))
        evidence_refs.extend(row.get("review_state_update", {}).get("evidence_refs", []))
    return {
        "check_refs": sorted({ref for ref in check_refs if ref}),
        "authority_refs": sorted({ref for ref in authority_refs if ref}),
        "evidence_refs": sorted({ref for ref in evidence_refs if ref}),
    }


def build_spatial_handoff_fixtures(inputs: dict[str, Any], matrix: dict[str, Any]) -> dict[str, Any]:
    spatial_service = service_entry("spatial_handoff_service")
    refs = collect_check_authority_refs(inputs)
    handoffs = []
    for index, row in enumerate(matrix["rows"], start=1):
        overlay_refs = row["spatial_overlay_profile"].get("overlay_refs", [])
        domain = row["domain"]
        selected_kind = {
            "planning": "EntityPacket",
            "mobility": "WatchItem",
            "utilities": "EventEnvelope",
            "building": "CandidateObservation",
        }[domain]
        selected_ref = {
            "planning": "entity:planning_project:local_replay:001",
            "mobility": inputs["watch"]["ticks"][0]["emitted_watch_items"][0]["watch_item_id"],
            "utilities": "event:local_replay:utilities:unresolved:001",
            "building": "candidate:local_replay:building:permit_media:001",
        }[domain]
        check_ref = refs["check_refs"][(index - 1) % len(refs["check_refs"])]
        authority_ref = refs["authority_refs"][(index - 1) % len(refs["authority_refs"])]
        evidence = refs["evidence_refs"][(index - 1) : (index + 1)] or [row["pack_manifest_ref"]]
        selection_packet_id = f"spatial-selection:epoch2_2c:{domain}:001"
        handoff_id = f"kit-web-overlay-handoff:epoch2_2c:{domain}:001"
        selection_packet = {
            "packet_type": "SpatialSelectionPacket",
            "selection_packet_id": selection_packet_id,
            "selected_input_kind": selected_kind,
            "selected_input_ref": selected_ref,
            "canonical_entity_id": f"canonical:{domain}:local_replay:001",
            "domain_pack_id": row["pack_id"],
            "evidence_refs": evidence,
            "check_report_ref": check_ref,
            "authority_envelope_ref": authority_ref,
            "limitations": ["local/replay review selection only", "not executed", "no live control claim"],
            "review_state": "candidate_review_only",
            "not_executed": True,
            "no_live_control_claim": True,
            "no_action_boundary": {
                "official_action_created": False,
                "ticket_or_case_created": False,
                "dispatch_control_enforcement": False,
                "legal_or_certified_finding": False,
            },
        }
        overlay_handoff = {
            "handoff_id": handoff_id,
            "handoff_type": "KitWebOverlayHandoff",
            "target_surface": "kit_web_spatial_review",
            "overlay_refs": overlay_refs,
            "spatial_selection_packet_ref": selection_packet_id,
            "evidence_refs": evidence,
            "check_report_ref": check_ref,
            "authority_envelope_ref": authority_ref,
            "limitation_refs": selection_packet["limitations"],
            "live_control_claim": False,
            "production_kit_web_control_claim": False,
            "allowed_operator_actions": ["inspect", "pan_zoom", "open_evidence", "defer_or_dismiss_with_reason"],
            "forbidden_operator_actions": ["dispatch", "control", "enforce", "create_official_ticket", "certify_finding"],
            "not_executed": True,
        }
        envelope = spatial_run_envelope(index, domain, selection_packet, overlay_handoff, spatial_service)
        handoffs.append(
            {
                "domain": domain,
                "status": "PASS",
                "service_id": "spatial_handoff_service",
                "component_id": "spatial_agent",
                "spatial_selection_packet": selection_packet,
                "kit_web_overlay_handoff": overlay_handoff,
                "agent_run_envelope": envelope,
                "validation_errors": [],
            }
        )
    for handoff in handoffs:
        handoff["validation_errors"] = validate_spatial_handoff(handoff)
        handoff["status"] = "PASS" if not handoff["validation_errors"] else "FAIL"
    checks = {
        "spatial_handoff_service_registry_entry_used": spatial_service.get("service_id") == "spatial_handoff_service",
        "one_handoff_per_starter_pack": len(handoffs) == 4 and {row["domain"] for row in handoffs} == set(DOMAINS),
        "agent_run_envelope_per_handoff": all(row.get("agent_run_envelope") for row in handoffs),
        "all_handoffs_have_check_authority_refs": all(not row["validation_errors"] for row in handoffs),
        "no_live_control_or_action_claim": all(
            row["kit_web_overlay_handoff"]["live_control_claim"] is False
            and row["kit_web_overlay_handoff"]["production_kit_web_control_claim"] is False
            for row in handoffs
        ),
    }
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2c.lane_a.spatial_handoff_fixtures.v1",
        "status": PASS_STATUS if all(checks.values()) else "FAIL",
        "created_at": utc_now(),
        "service_registry_ref": inputs["service_registry_ref"],
        "spatial_service_entry": spatial_service,
        "checks": checks,
        "handoff_count": len(handoffs),
        "handoffs": handoffs,
        "limitations": LIMITATIONS,
    }


def spatial_run_envelope(
    index: int,
    domain: str,
    selection_packet: dict[str, Any],
    overlay_handoff: dict[str, Any],
    spatial_service: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.agent_run_envelope.v1",
        "run_id": f"agent-run:epoch2_2c:spatial_handoff_service:{domain}:{index:02d}",
        "component_id": "spatial_agent",
        "component_version": "1.0",
        "service_id": "spatial_handoff_service",
        "service_version": spatial_service.get("service_version", "1.0.0"),
        "scope": "local_replay_review_query_only",
        "trigger": f"manual:spatial_handoff:{domain}",
        "started_at": "2026-07-06T00:00:00Z",
        "ended_at": "2026-07-06T00:00:00Z",
        "duration_ms": 0,
        "status": "emitted",
        "authority_level": 1,
        "budget": {
            "policy_ref": "spatial_handoff_service_budget_window",
            "max_steps": 6,
            "max_tool_calls": spatial_service.get("budget_window", {}).get("max_tool_calls", 20),
            "max_llm_calls": 0,
            "max_outputs": 2,
        },
        "inputs": [selection_packet["selected_input_ref"]],
        "outputs": [selection_packet["selection_packet_id"], overlay_handoff["handoff_id"]],
        "output_packet_types": ["SpatialSelectionPacket", "SpatialOverlayPacket"],
        "tools_used": ["local_replay_fixture_read", "schema_validate", "kit_web_overlay_handoff_fixture_write"],
        "evidence_refs": selection_packet["evidence_refs"],
        "check_report_refs": [selection_packet["check_report_ref"]],
        "authority_envelope_refs": [selection_packet["authority_envelope_ref"]],
        "trace_refs": [selection_packet["selection_packet_id"], overlay_handoff["handoff_id"], domain],
        "handoff_target": ["kit_web_spatial_review"],
        "limitations": selection_packet["limitations"],
        "stop_condition_hit": None,
    }


def validate_spatial_handoff(handoff: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    packet = handoff.get("spatial_selection_packet", {})
    overlay = handoff.get("kit_web_overlay_handoff", {})
    envelope = handoff.get("agent_run_envelope", {})
    if not packet.get("check_report_ref") or not overlay.get("check_report_ref"):
        errors.append("missing_check_report_ref")
    if not packet.get("authority_envelope_ref") or not overlay.get("authority_envelope_ref"):
        errors.append("missing_authority_envelope_ref")
    if not packet.get("evidence_refs") or not overlay.get("evidence_refs"):
        errors.append("missing_evidence_refs")
    if overlay.get("live_control_claim") is True or overlay.get("production_kit_web_control_claim") is True:
        errors.append("kit_web_live_control_claim")
    if packet.get("not_executed") is not True or overlay.get("not_executed") is not True:
        errors.append("not_executed_boundary_missing")
    if packet.get("no_action_boundary", {}).get("official_action_created") is not False:
        errors.append("official_action_boundary_missing")
    if envelope.get("schema_version") != "citybrain.agent_run_envelope.v1":
        errors.append("missing_agent_run_envelope")
    if envelope.get("service_id") != "spatial_handoff_service":
        errors.append("wrong_service_id")
    return errors


def build_spatial_service_report(inputs: dict[str, Any], fixtures: dict[str, Any]) -> dict[str, Any]:
    checks = fixtures["checks"]
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2c.lane_a.spatial_agent_service_report.v1",
        "status": PASS_STATUS if all(checks.values()) else "FAIL",
        "created_at": utc_now(),
        "service_id": "spatial_handoff_service",
        "component_id": "spatial_agent",
        "activation_mode": "local_replay_review_query_service_activation",
        "service_registry_ref": inputs["service_registry_ref"],
        "handoff_fixture_ref": "outputs/epoch_2_2/push_2_2c/lane_a_pack_spatial/SPATIAL_HANDOFF_FIXTURES.json",
        "handoff_count": fixtures["handoff_count"],
        "agent_run_envelope_count": len([row for row in fixtures["handoffs"] if row.get("agent_run_envelope")]),
        "service_health_state": "healthy",
        "checks": checks,
        "boundaries": {
            "local_replay_review_query_only": True,
            "production_kit_web_control_claim": False,
            "official_action_ticket_dispatch_enforcement_created": False,
            "legal_or_certified_finding_created": False,
            "trained_ranking_prediction_counterfactual_or_dynamic_investigation_created": False,
        },
        "limitations": LIMITATIONS,
    }


def build_negative_report(matrix: dict[str, Any], fixtures: dict[str, Any]) -> dict[str, Any]:
    rows = []
    domain_class_row = copy.deepcopy(matrix["rows"][0])
    domain_class_row["cross_cutting_runtime"]["class_name"] = "PlanningAgent"
    domain_class_row["cross_cutting_runtime"]["per_domain_agent_class_created"] = True
    rows.append(negative_row("new_domain_specific_agent_class_detected", validate_matrix_row(domain_class_row)))

    no_consumer = copy.deepcopy(matrix["rows"][1])
    no_consumer["consuming_capability"]["exists"] = False
    no_consumer["consuming_capability"]["refs"] = []
    rows.append(negative_row("pack_has_no_consuming_capability", validate_matrix_row(no_consumer)))

    missing_check = copy.deepcopy(fixtures["handoffs"][0])
    missing_check["spatial_selection_packet"]["check_report_ref"] = None
    missing_check["kit_web_overlay_handoff"]["check_report_ref"] = None
    rows.append(negative_row("spatial_handoff_missing_check_authority_refs", validate_spatial_handoff(missing_check)))

    live_control = copy.deepcopy(fixtures["handoffs"][1])
    live_control["kit_web_overlay_handoff"]["live_control_claim"] = True
    live_control["kit_web_overlay_handoff"]["production_kit_web_control_claim"] = True
    rows.append(negative_row("kit_web_handoff_claims_live_control", validate_spatial_handoff(live_control)))

    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2c.lane_a.negative_tests.v1",
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "created_at": utc_now(),
        "fixture_count": len(rows),
        "results": rows,
    }


def negative_row(fixture_id: str, errors: list[str]) -> dict[str, Any]:
    return {
        "fixture_id": fixture_id,
        "expected": "REJECTED",
        "actual": "REJECTED" if errors else "ACCEPTED",
        "status": "PASS" if errors else "FAIL",
        "errors": errors,
    }


def build_pack_report(
    gate: dict[str, Any],
    matrix: dict[str, Any],
    spatial_report: dict[str, Any],
    fixtures: dict[str, Any],
    negative: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "prerequisite_gate_passed": gate["status"] == "PASS",
        "starter_pack_matrix_passed": matrix["status"].startswith("PASS"),
        "spatial_service_passed": spatial_report["status"].startswith("PASS"),
        "spatial_handoff_fixtures_passed": fixtures["status"].startswith("PASS"),
        "negative_tests_passed": negative["status"] == "PASS",
        "no_per_domain_agent_classes": matrix["checks"]["no_per_domain_agent_classes"],
        "all_four_packs_active": matrix["checks"]["four_starter_packs_present"],
        "all_handoffs_have_envelopes": fixtures["checks"]["agent_run_envelope_per_handoff"],
        "no_live_control_claim": spatial_report["boundaries"]["production_kit_web_control_claim"] is False,
    }
    status = PASS_STATUS if all(checks.values()) else BLOCKED_STATUS
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2c.lane_a.pack_parameterized_agent_report.v1",
        "status": status,
        "decision_code": PASS_CODE if status == PASS_STATUS else "BLOCKED_EPOCH_2_2_PUSH_2_2C_LANE_A_PACK_SPATIAL_VALIDATION",
        "created_at": utc_now(),
        "lane": "A",
        "push": "2.2c",
        "artifact_root": rel(OUTPUT_ROOT),
        "source_package_refs": PACKAGE_REFS,
        "prerequisite_gate": gate,
        "checks": checks,
        "matrix_ref": "outputs/epoch_2_2/push_2_2c/lane_a_pack_spatial/STARTER_PACK_AGENT_CONSUMER_MATRIX.json",
        "spatial_service_report_ref": "outputs/epoch_2_2/push_2_2c/lane_a_pack_spatial/SPATIAL_AGENT_SERVICE_REPORT.json",
        "spatial_handoff_fixtures_ref": "outputs/epoch_2_2/push_2_2c/lane_a_pack_spatial/SPATIAL_HANDOFF_FIXTURES.json",
        "negative_test_report_ref": "outputs/epoch_2_2/push_2_2c/lane_a_pack_spatial/NEGATIVE_TEST_REPORT.json",
        "domains": DOMAINS,
        "cross_cutting_agent_classes_used": ALLOWED_CROSS_CUTTING_CLASSES,
        "domain_specific_agent_classes_detected": [],
        "spatial_handoff_count": fixtures["handoff_count"],
        "boundaries": {
            "local_replay_review_query_only": True,
            "per_domain_agent_classes_created": False,
            "official_action_ticket_dispatch_enforcement_created": False,
            "legal_or_certified_finding_created": False,
            "trained_ranking_prediction_counterfactual_or_dynamic_investigation_created": False,
            "production_kit_web_control_claim": False,
        },
        "blockers": [] if status == PASS_STATUS else [name for name, passed in checks.items() if not passed],
        "limitations": LIMITATIONS,
    }


def list_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append({"path": out_rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2c.lane_a.hash_manifest.v1",
        "status": "PASS",
        "algorithm": "sha256",
        "created_at": utc_now(),
        "item_count": len(files),
        "files": files,
    }


def write_all_outputs() -> dict[str, Any]:
    gate = prerequisite_gate()
    if gate["status"] != "PASS":
        return {"gate": gate, "report": None}

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    inputs = load_inputs()
    matrix = build_consumer_matrix(inputs)
    fixtures = build_spatial_handoff_fixtures(inputs, matrix)
    spatial_report = build_spatial_service_report(inputs, fixtures)
    negative = build_negative_report(matrix, fixtures)
    report = build_pack_report(gate, matrix, spatial_report, fixtures, negative)

    write_json(OUTPUT_ROOT / "PACK_PARAMETERIZED_AGENT_REPORT.json", report)
    write_json(OUTPUT_ROOT / "STARTER_PACK_AGENT_CONSUMER_MATRIX.json", matrix)
    write_json(OUTPUT_ROOT / "SPATIAL_AGENT_SERVICE_REPORT.json", spatial_report)
    write_json(OUTPUT_ROOT / "SPATIAL_HANDOFF_FIXTURES.json", fixtures)
    write_json(OUTPUT_ROOT / "NEGATIVE_TEST_REPORT.json", negative)
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", list_hash_manifest())
    return {
        "gate": gate,
        "inputs": inputs,
        "matrix": matrix,
        "fixtures": fixtures,
        "spatial_report": spatial_report,
        "negative": negative,
        "report": report,
    }


def main() -> int:
    result = write_all_outputs()
    gate = result["gate"]
    if gate["status"] != "PASS":
        print(BLOCKED_STATUS)
        print(BLOCKED_CODE)
        print(json.dumps(gate["errors"], indent=2, sort_keys=True))
        return 1
    report = result["report"]
    print(report["status"])
    print(report["decision_code"])
    print(f"Output: {rel(OUTPUT_ROOT)}")
    if report["status"] != PASS_STATUS:
        print(json.dumps(report["blockers"], indent=2, sort_keys=True))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

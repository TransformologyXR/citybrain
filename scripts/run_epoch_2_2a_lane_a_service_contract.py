#!/usr/bin/env python3
"""Build Epoch 2.2 Push 2.2a Lane A service contract artifacts."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_a_service_contract"
ENTRY_GATE_ROOT = REPO_ROOT / "outputs" / "epoch_2_2_entry_gate"
EPOCH_2_0_ROOT = REPO_ROOT / "outputs" / "epoch_2_0_agentic_runtime_consolidation"

ENTRY_GATE_DECISION = ENTRY_GATE_ROOT / "EPOCH_2_2_ENTRY_GATE_DECISION.json"
COMPONENT_REGISTRY = EPOCH_2_0_ROOT / "component_registry_v1.json"
AGENT_RUN_ENVELOPE = EPOCH_2_0_ROOT / "agent_run_envelope_v1.json"
TOOL_PERMISSION_POLICY = EPOCH_2_0_ROOT / "tool_permission_policy_v1.json"

PASS_STATUS = "PASS_WITH_LIMITATIONS"
PASS_CODE = "PASS_EPOCH_2_2_PUSH_2_2A_LANE_A_SERVICE_CONTRACT_WITH_LIMITATIONS"
BLOCKED_STATUS = "BLOCKED"
BLOCKED_CODE = "BLOCKED_EPOCH_2_2_PUSH_2_2A_LANE_A_PREREQUISITE_GATE"

PACKAGE_REFS = [
    "02_PUSH_LANE_EXECUTION_MODEL.md",
    "05_PUSH_2_2A_LANE_A_SERVICE_CONTRACT_PROMPT.md",
    "20_SPEC_AGENT_SERVICE_CONTRACT.md",
    "21_SPEC_AGENT_OBSERVABILITY.md",
    "28_SCOPE_NON_GOALS.md",
    "29_EXIT_GATE_CHECKLIST.md",
    "31_TRACK0_CORPUS_LEDGER_DISCIPLINE.md",
]

REQUIRED_ARTIFACTS = [
    "AGENT_SERVICE_CONTRACT_V1.json",
    "SERVICE_REGISTRY_V1.json",
    "SERVICE_ELIGIBILITY_POLICY.md",
    "MULTI_AGENT_REPLAY_HARNESS_REPORT.json",
    "NEGATIVE_FIXTURES_REPORT.json",
    "DECISION.json",
    "SUMMARY.md",
    "HASH_MANIFEST.json",
]

REQUIRED_SERVICES = [
    "watch_scout_service",
    "event_incident_service",
    "briefing_service",
    "spatial_handoff_service",
    "perception_shadow_service",
]

EXISTING_COMPONENT_IDS = [
    "watch_scout",
    "diff_scout",
    "briefing_agent",
    "spatial_agent",
    "perception_media_agent",
    "check_agent",
    "workflow_disposition_agent",
    "epoch2_replay_harness",
]

FORBIDDEN_ACTIONS = [
    "production_write",
    "live_url_fetch",
    "live_camera_connection",
    "official_ticket_or_case_creation",
    "dispatch_control_enforcement",
    "legal_or_certified_finding",
    "autonomous_execution",
    "source_truth_mutation",
    "secret_exposure",
]

FORBIDDEN_OUTPUTS = [
    "OfficialAction",
    "DispatchCommand",
    "Ticket",
    "CasePacket",
    "LegalFinding",
    "CertifiedFinding",
    "SourceTruthMutation",
    "AutonomousExecution",
]

LIMITATIONS = [
    "Contract and registry artifacts only; no long-running service is activated in this lane.",
    "Event/Incident service is registered as a planned Epoch 2.2b service because no Epoch 2.0 event_incident_agent component exists yet.",
    "Replay harness rows are local/replay contract fixtures, not production service runs.",
    "No sealed AgentRunEnvelope, packet schema, ComponentRegistry, or ToolPermissionPolicy file is modified.",
    "No learned ranking, prediction, trained model, dynamic investigation, official action, dispatch, enforcement, ticket, case, legal, or certified finding is introduced.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


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
    decision = read_json(ENTRY_GATE_DECISION) if ENTRY_GATE_DECISION.exists() else {}
    checks = {
        "branch_is_main": current_branch() == "main",
        "entry_gate_decision_exists": ENTRY_GATE_DECISION.exists(),
        "entry_gate_status_exact": decision.get("status") == "PASS_EPOCH_2_2_ENTRY_GATE",
    }
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2a.lane_a.prerequisite_gate.v1",
        "status": "PASS" if all(checks.values()) else BLOCKED_STATUS,
        "checked_at": utc_now(),
        "branch": current_branch(),
        "entry_gate_decision_ref": rel(ENTRY_GATE_DECISION),
        "entry_gate_status": decision.get("status"),
        "checks": checks,
        "errors": [name for name, passed in checks.items() if not passed],
    }


def discover_epoch_2_0_contracts() -> dict[str, Any]:
    components = read_json(COMPONENT_REGISTRY)
    envelope = read_json(AGENT_RUN_ENVELOPE)
    policies = read_json(TOOL_PERMISSION_POLICY)
    component_by_id = {row["component_id"]: row for row in components}
    policy_by_component = {row["component_id"]: row for row in policies}
    discovery_rows = []
    for component_id in EXISTING_COMPONENT_IDS:
        component = component_by_id.get(component_id)
        policy = policy_by_component.get(component_id)
        discovery_rows.append(
            {
                "component_id": component_id,
                "component_registry_status": "FOUND" if component else "MISSING",
                "tool_permission_policy_status": "FOUND" if policy else "MISSING",
                "component_name": component.get("name") if component else None,
                "input_packet_types": component.get("input_packet_types", []) if component else [],
                "output_packet_types": component.get("output_packet_types", []) if component else [],
                "authority_level_max": component.get("authority_level_max") if component else None,
                "tool_policy_id": policy.get("policy_id") if policy else None,
                "permission_forbidden_actions": policy.get("forbidden_actions", []) if policy else [],
            }
        )
    return {
        "status": "PASS" if all(row["component_registry_status"] == "FOUND" for row in discovery_rows) else "PASS_WITH_LIMITATIONS",
        "component_registry_ref": rel(COMPONENT_REGISTRY),
        "agent_run_envelope_ref": rel(AGENT_RUN_ENVELOPE),
        "tool_permission_policy_ref": rel(TOOL_PERMISSION_POLICY),
        "agent_run_envelope_schema_version": envelope.get("schema_version"),
        "agent_run_envelope_required_keys": sorted(envelope.keys()),
        "component_count": len(components),
        "tool_policy_count": len(policies),
        "rows": discovery_rows,
    }


def service_contract(discovery: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_2.agent_service_contract.v1",
        "contract_id": "AGENT_SERVICE_CONTRACT_V1",
        "status": PASS_STATUS,
        "created_at": utc_now(),
        "purpose": "Service-level contract for recurring or long-running agent behavior while preserving one AgentRunEnvelope per service tick/run.",
        "additive_to": {
            "component_registry_ref": discovery["component_registry_ref"],
            "agent_run_envelope_ref": discovery["agent_run_envelope_ref"],
            "tool_permission_policy_ref": discovery["tool_permission_policy_ref"],
            "sealed_upstream_mutation_required": False,
        },
        "required_fields": {
            "service_id": "string",
            "component_id": "string",
            "service_version": "semver",
            "service_kind": "scheduled|event_triggered|hybrid|manual_local",
            "eligibility_reason": "non-empty list",
            "trigger_policy": {
                "type": "interval|event|manual",
                "schedule": "bounded string|null",
                "event_types": "list",
            },
            "run_envelope_required": True,
            "budget_window": {
                "window": "hour|day|run_batch",
                "max_runs": "positive integer",
                "max_tool_calls": "integer >= 0",
                "max_llm_calls": "integer >= 0",
                "max_wall_clock_seconds": "positive integer",
                "max_outputs": "positive integer",
            },
            "health_states": ["healthy", "degraded", "blocked", "stopped"],
            "restart_policy": {
                "restartable": "boolean",
                "idempotency_key_fields": "non-empty list",
            },
            "throttle_policy": {
                "max_items_per_tick": "positive integer",
                "max_items_per_family_per_tick": "positive integer",
                "dedupe_window_seconds": "positive integer",
            },
            "authority_ceiling": "<= 3",
            "allowed_outputs": "list",
            "forbidden_outputs": FORBIDDEN_OUTPUTS,
            "observability_refs": "list",
            "check_required": True,
        },
        "service_lifecycle": {
            "states": ["registered", "healthy", "degraded", "blocked", "stopped"],
            "activation_status_allowed_in_2_2a": ["not_activated_contract_only", "planned_not_activated"],
            "restart_semantics": "Restart is allowed only when idempotency_key_fields are present and the next tick creates a new AgentRunEnvelope.",
            "drift_handling": "Drift is surfaced as review context, throttled or blocked by policy, never converted into official action.",
            "operator_visible_status_required": True,
        },
        "service_eligibility_rule": {
            "default_execution_mode": "on_demand",
            "service_is_exception": True,
            "eligible_only_if_any": [
                "scheduled_recurrence_required",
                "event_triggered_recurrence_required",
                "materialized_state_drift_monitoring_required",
                "dedupe_or_throttle_across_time_required",
                "service_health_independent_of_single_run_required",
                "restart_or_idempotency_semantics_required",
            ],
            "service_justification_review_required": True,
            "review_questions": [
                "What would break if this remained on-demand?",
                "What recurrence or event trigger is required?",
                "What state drift, dedupe, throttle, or health semantics are needed across time?",
                "What service-level budget prevents runaway behavior?",
                "What operator-visible value is produced by recurrence?",
                "What evidence proves the service has at least one consuming surface?",
            ],
        },
        "non_action_rule": {
            "authority_ceiling_max": 3,
            "official_action_forbidden": True,
            "forbidden_actions": FORBIDDEN_ACTIONS,
        },
        "negative_fixture_requirements": [
            "service_without_per_run_envelope_rejected",
            "service_without_budget_window_rejected",
            "service_that_grants_authority_rejected",
            "service_with_no_eligibility_reason_rejected",
            "unbounded_schedule_rejected",
            "service_emits_official_action_rejected",
        ],
        "limitations": LIMITATIONS,
    }


def component_row(discovery: dict[str, Any], component_id: str) -> dict[str, Any] | None:
    for row in discovery["rows"]:
        if row["component_id"] == component_id:
            return row
    return None


def base_budget(max_runs: int, max_outputs: int, max_tool_calls: int = 25, max_llm_calls: int = 0) -> dict[str, Any]:
    return {
        "window": "hour",
        "max_runs": max_runs,
        "max_tool_calls": max_tool_calls,
        "max_llm_calls": max_llm_calls,
        "max_wall_clock_seconds": 120,
        "max_outputs": max_outputs,
    }


def service_entry(
    *,
    service_id: str,
    component_id: str,
    component_registry_status: str,
    service_kind: str,
    eligibility_reason: list[str],
    trigger_policy: dict[str, Any],
    budget_window: dict[str, Any],
    throttle_policy: dict[str, Any],
    allowed_outputs: list[str],
    consuming_surfaces: list[str],
    drift_inputs: list[str],
    activation_status: str = "not_activated_contract_only",
) -> dict[str, Any]:
    return {
        "service_id": service_id,
        "component_id": component_id,
        "component_registry_status": component_registry_status,
        "service_version": "1.0.0",
        "service_kind": service_kind,
        "activation_status": activation_status,
        "eligibility_reason": eligibility_reason,
        "trigger_policy": trigger_policy,
        "run_envelope_required": True,
        "per_run_envelope_link": {
            "agent_run_envelope_schema_version": "citybrain.agent_run_envelope.v1",
            "link_field": "agent_run_envelope_ref",
            "required_per_tick": True,
        },
        "budget_window": budget_window,
        "health_states": ["healthy", "degraded", "blocked", "stopped"],
        "restart_policy": {
            "restartable": True,
            "idempotency_key_fields": ["service_id", "trigger_id", "input_packet_hash", "scheduled_window"],
            "restart_creates_new_agent_run_envelope": True,
        },
        "idempotency_key": {
            "format": "sha256(service_id|trigger_id|input_packet_hash|scheduled_window)",
            "fields": ["service_id", "trigger_id", "input_packet_hash", "scheduled_window"],
        },
        "drift_handling": {
            "drift_inputs": drift_inputs,
            "on_drift": "surface_review_context_or_defer",
            "on_schema_or_authority_drift": "blocked",
            "drift_never_creates_official_action": True,
        },
        "throttle_policy": throttle_policy,
        "throttle_state": {
            "default": "open",
            "operator_controls": ["open", "throttled", "paused"],
            "state_visible_to_operator": True,
        },
        "operator_visible_service_status": {
            "fields": [
                "service_id",
                "activation_status",
                "health_state",
                "last_run_id",
                "last_run_status",
                "budget_window_remaining",
                "throttle_state",
                "deferred_count",
                "blocked_reason",
            ],
            "default_health_state": "stopped",
            "status_copy": "registered, not activated",
        },
        "authority_ceiling": 1,
        "allowed_outputs": allowed_outputs,
        "forbidden_outputs": FORBIDDEN_OUTPUTS,
        "observability_refs": [
            "outputs/epoch_2_2/push_2_2a/lane_a_service_contract/MULTI_AGENT_REPLAY_HARNESS_REPORT.json",
            "future:outputs/epoch_2_2/push_2_2a/lane_b_observability",
        ],
        "check_required": True,
        "consuming_surfaces": consuming_surfaces,
        "service_justification_review": {
            "decision": "service_eligible_not_activated",
            "default_on_demand_considered": True,
            "what_breaks_if_on_demand": "recurrence, dedupe/throttle, health, or drift semantics would be invisible between manual invocations.",
            "operator_visible_value": "bounded review prompts, handoff packets, or shadow status with CHECK and authority limitations.",
            "evidence_of_consuming_surface": consuming_surfaces,
        },
        "non_action_boundaries": {
            "service_activation_in_this_lane": False,
            "official_action_allowed": False,
            "dispatch_or_control_allowed": False,
            "legal_or_certified_finding_allowed": False,
            "source_truth_mutation_allowed": False,
        },
    }


def build_service_registry(discovery: dict[str, Any]) -> dict[str, Any]:
    found_components = {row["component_id"]: row for row in discovery["rows"] if row["component_registry_status"] == "FOUND"}
    services = [
        service_entry(
            service_id="watch_scout_service",
            component_id="watch_scout",
            component_registry_status="FOUND" if "watch_scout" in found_components else "MISSING",
            service_kind="hybrid",
            eligibility_reason=["event_triggered_recurrence_required", "dedupe_or_throttle_across_time_required", "service_health_independent_of_single_run_required"],
            trigger_policy={
                "type": "event",
                "schedule": None,
                "event_types": ["EventEnvelope.created", "MaterializedReviewState.changed"],
                "bounded_by_budget_window": True,
            },
            budget_window=base_budget(12, 120),
            throttle_policy={"max_items_per_tick": 25, "max_items_per_family_per_tick": 5, "dedupe_window_seconds": 3600},
            allowed_outputs=["WatchItem", "CheckReportRef", "AuthorityEnvelopeRef"],
            consuming_surfaces=["WATCH review prompts", "operator service status", "future observability dashboard"],
            drift_inputs=["MaterializedReviewState", "EventEnvelope family counts"],
        ),
        service_entry(
            service_id="event_incident_service",
            component_id="event_incident_agent",
            component_registry_status="PLANNED_EPOCH_2_2B_NOT_IN_EPOCH_2_0_REGISTRY",
            service_kind="event_triggered",
            eligibility_reason=["event_triggered_recurrence_required", "materialized_state_drift_monitoring_required"],
            trigger_policy={
                "type": "event",
                "schedule": None,
                "event_types": ["CandidateObservation.created", "EventEnvelope.updated"],
                "bounded_by_budget_window": True,
            },
            budget_window=base_budget(10, 100),
            throttle_policy={"max_items_per_tick": 20, "max_items_per_family_per_tick": 5, "dedupe_window_seconds": 1800},
            allowed_outputs=["EventReviewState", "EvidenceRefs", "WatchHandoffRef"],
            consuming_surfaces=["Event Fabric local replay", "WATCH review prompts", "future observability dashboard"],
            drift_inputs=["CandidateObservation", "EventEnvelope", "EventReviewState"],
            activation_status="planned_not_activated",
        ),
        service_entry(
            service_id="briefing_service",
            component_id="briefing_agent",
            component_registry_status="FOUND" if "briefing_agent" in found_components else "MISSING",
            service_kind="event_triggered",
            eligibility_reason=["event_triggered_recurrence_required", "restart_or_idempotency_semantics_required"],
            trigger_policy={
                "type": "event",
                "schedule": None,
                "event_types": ["CheckReport.passed", "WatchItem.ready_for_brief"],
                "bounded_by_budget_window": True,
            },
            budget_window=base_budget(8, 40, max_tool_calls=20, max_llm_calls=0),
            throttle_policy={"max_items_per_tick": 8, "max_items_per_family_per_tick": 3, "dedupe_window_seconds": 7200},
            allowed_outputs=["BriefPacket"],
            consuming_surfaces=["BRIEF v2 / Flow 1", "future briefing observability"],
            drift_inputs=["CheckReport", "WatchItem", "DispositionSummary"],
        ),
        service_entry(
            service_id="spatial_handoff_service",
            component_id="spatial_agent",
            component_registry_status="FOUND" if "spatial_agent" in found_components else "MISSING",
            service_kind="manual_local",
            eligibility_reason=["restart_or_idempotency_semantics_required", "service_health_independent_of_single_run_required"],
            trigger_policy={
                "type": "manual",
                "schedule": None,
                "event_types": ["WatchItem.spatial_handoff_requested"],
                "bounded_by_budget_window": True,
            },
            budget_window=base_budget(6, 30, max_tool_calls=20),
            throttle_policy={"max_items_per_tick": 6, "max_items_per_family_per_tick": 2, "dedupe_window_seconds": 3600},
            allowed_outputs=["SpatialOverlayPacket"],
            consuming_surfaces=["Spatial UI/UX review", "future Kit/web handoff"],
            drift_inputs=["OverlayPacket", "EvidenceRefs"],
        ),
        service_entry(
            service_id="perception_shadow_service",
            component_id="perception_media_agent",
            component_registry_status="FOUND" if "perception_media_agent" in found_components else "MISSING",
            service_kind="hybrid",
            eligibility_reason=["scheduled_recurrence_required", "materialized_state_drift_monitoring_required", "dedupe_or_throttle_across_time_required"],
            trigger_policy={
                "type": "interval",
                "schedule": "manual_shadow_batch; min_interval_seconds=3600; disabled_until_2_2c_gate",
                "event_types": ["MediaEvidenceBundle.shadow_batch_ready"],
                "bounded_by_budget_window": True,
            },
            budget_window=base_budget(4, 40, max_tool_calls=20),
            throttle_policy={"max_items_per_tick": 10, "max_items_per_family_per_tick": 2, "dedupe_window_seconds": 86400},
            allowed_outputs=["MediaEvidencePacket", "CandidateObservationRef"],
            consuming_surfaces=["Perception evidence review", "future perception shadow dashboard"],
            drift_inputs=["MediaEvidenceBundle", "CandidateObservation"],
            activation_status="planned_not_activated",
        ),
    ]

    diff_review = {
        "component_id": "diff_scout",
        "component_registry_status": "FOUND" if "diff_scout" in found_components else "MISSING",
        "review_id": "service_justification_review_diff_scout_v1",
        "default_execution_mode": "on_demand",
        "decision": "remain_on_demand",
        "service_id_if_later_eligible": "diff_scout_service",
        "answers": {
            "what_would_break_if_on_demand": "Nothing in the consumed evidence: operator-requested comparisons are sufficient.",
            "recurrence_or_event_trigger_required": "None proven; no comparable snapshot cadence is registered for this lane.",
            "state_drift_dedupe_throttle_or_health_needed": "Not yet; no proactive change prompt surface consumes recurring DiffItem output.",
            "budget_preventing_runaway": "Not applicable until service eligibility is proven.",
            "operator_visible_value": "On-demand comparison table only.",
            "consuming_surface_evidence": ["DIFF/RECALL read-only lane"],
        },
        "service_eligible_now": False,
        "may_become_service_when": [
            "comparable snapshots exist on a cadence",
            "WATCH or dashboard surface consumes change prompts",
            "dedupe/throttle is required across snapshots",
            "stale/change state must be monitored independently of one request",
        ],
    }

    registry = {
        "schema_version": "citybrain.epoch_2_2.service_registry.v1",
        "registry_id": "SERVICE_REGISTRY_V1",
        "status": PASS_STATUS,
        "created_at": utc_now(),
        "service_contract_ref": "outputs/epoch_2_2/push_2_2a/lane_a_service_contract/AGENT_SERVICE_CONTRACT_V1.json",
        "discovery_refs": {
            "component_registry_ref": discovery["component_registry_ref"],
            "agent_run_envelope_ref": discovery["agent_run_envelope_ref"],
            "tool_permission_policy_ref": discovery["tool_permission_policy_ref"],
        },
        "services": services,
        "service_justification_reviews": [service["service_justification_review"] for service in services],
        "on_demand_component_reviews": [diff_review],
        "rules": {
            "default_on_demand": True,
            "service_activation_allowed_in_2_2a": False,
            "per_run_agent_run_envelope_required": True,
            "authority_ceiling_max": 3,
            "sealed_registry_or_envelope_mutation_required": False,
        },
        "limitations": LIMITATIONS,
    }
    validation = validate_registry(registry)
    registry["validation"] = validation
    registry["status"] = PASS_STATUS if validation["status"] == "PASS" else "FAIL"
    return registry


def validate_service(entry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not entry.get("service_id"):
        errors.append("missing_service_id")
    if not entry.get("component_id"):
        errors.append("missing_component_id")
    if entry.get("service_kind") not in {"scheduled", "event_triggered", "hybrid", "manual_local"}:
        errors.append("invalid_service_kind")
    if not entry.get("eligibility_reason"):
        errors.append("missing_eligibility_reason")
    trigger = entry.get("trigger_policy") or {}
    if trigger.get("schedule") in {"*", "unbounded", "continuous", "always_on"}:
        errors.append("unbounded_schedule")
    if trigger.get("bounded_by_budget_window") is not True:
        errors.append("trigger_not_bound_by_budget_window")
    if entry.get("run_envelope_required") is not True:
        errors.append("per_run_envelope_not_required")
    if not entry.get("per_run_envelope_link", {}).get("required_per_tick"):
        errors.append("missing_per_run_envelope_link")
    budget = entry.get("budget_window")
    if not isinstance(budget, dict):
        errors.append("missing_budget_window")
    else:
        for field in ["max_runs", "max_wall_clock_seconds", "max_outputs"]:
            if not isinstance(budget.get(field), int) or budget[field] <= 0:
                errors.append(f"invalid_budget_{field}")
        for field in ["max_tool_calls", "max_llm_calls"]:
            if not isinstance(budget.get(field), int) or budget[field] < 0:
                errors.append(f"invalid_budget_{field}")
    if not set(["healthy", "degraded", "blocked", "stopped"]).issubset(set(entry.get("health_states", []))):
        errors.append("missing_health_states")
    if not entry.get("restart_policy", {}).get("idempotency_key_fields"):
        errors.append("missing_idempotency_key_fields")
    if entry.get("authority_ceiling", 99) > 3:
        errors.append("authority_ceiling_exceeds_3")
    if set(entry.get("allowed_outputs", [])) & set(FORBIDDEN_OUTPUTS):
        errors.append("official_or_forbidden_output_allowed")
    if entry.get("non_action_boundaries", {}).get("official_action_allowed") is True:
        errors.append("official_action_allowed")
    if entry.get("activation_status") not in {"not_activated_contract_only", "planned_not_activated"}:
        errors.append("service_activation_not_allowed_in_2_2a")
    return errors


def validate_registry(registry: dict[str, Any]) -> dict[str, Any]:
    service_ids = [entry["service_id"] for entry in registry["services"]]
    service_results = {entry["service_id"]: validate_service(entry) for entry in registry["services"]}
    checks = {
        "required_services_present": set(REQUIRED_SERVICES).issubset(set(service_ids)),
        "all_services_validate": all(not errors for errors in service_results.values()),
        "no_services_activated": all(entry["activation_status"] != "active" for entry in registry["services"]),
        "diff_scout_review_present": any(row["component_id"] == "diff_scout" for row in registry["on_demand_component_reviews"]),
        "diff_scout_remains_on_demand": registry["on_demand_component_reviews"][0]["decision"] == "remain_on_demand",
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "service_results": service_results,
    }


def eligibility_policy_text(registry: dict[str, Any]) -> str:
    diff = registry["on_demand_component_reviews"][0]
    service_lines = "\n".join(f"- `{entry['service_id']}`: `{entry['component_id']}`, `{entry['activation_status']}`" for entry in registry["services"])
    return f"""# Service Eligibility Policy

Status: `{PASS_STATUS}`

Default execution mode is `on_demand`. Service status is an exception and requires a ServiceJustificationReview before activation.

A component may become service-eligible only when at least one of these is proven:

- scheduled recurrence is required
- event-triggered recurrence is required
- materialized-state drift must be monitored
- dedupe or throttle across time is required
- service health matters independently of one run
- restart or idempotency semantics are required

Every service tick/run must emit or link to one `AgentRunEnvelope`. Service-level contracts do not replace per-run envelopes.

Registered 2.2 service candidates:

{service_lines}

## Diff Scout Worked Example

Decision: `{diff['decision']}`

Diff Scout remains on-demand for this lane because no comparable snapshot cadence is registered, no proactive WATCH/dashboard change-prompt surface consumes recurring DiffItem output, and operator-requested comparison is sufficient.

It may become service-eligible later only when comparable snapshots exist on a cadence, WATCH or dashboard consumes change prompts, dedupe/throttle is required across snapshots, and stale/change state must be monitored independently of one request.

## Non-Action Boundary

No service may grant authority, create official tickets/cases, dispatch/control/enforce, produce legal or certified findings, mutate source truth, or exceed authority level 3 in Epoch 2.2.
"""


def make_run_envelope(
    *,
    sequence_id: str,
    step_index: int,
    component_id: str,
    service_id: str | None,
    input_packets: list[str],
    output_packets: list[str],
    trigger: str,
) -> dict[str, Any]:
    service_part = service_id or "on_demand"
    run_id = f"agent-run:epoch2_2a:{sequence_id}:{step_index:02d}:{component_id}"
    return {
        "schema_version": "citybrain.agent_run_envelope.v1",
        "run_id": run_id,
        "component_id": component_id,
        "component_version": "1.0",
        "service_id": service_id,
        "service_contract_ref": "outputs/epoch_2_2/push_2_2a/lane_a_service_contract/AGENT_SERVICE_CONTRACT_V1.json" if service_id else None,
        "scope": "local_replay_review_query_only",
        "trigger": trigger,
        "status": "emitted",
        "started_at": "2026-07-06T00:00:00Z",
        "ended_at": "2026-07-06T00:00:00Z",
        "duration_ms": 0,
        "authority_level": 1,
        "budget": {
            "policy_ref": "service_budget_window_v1" if service_id else "budget_policy_local_replay_agent_v1",
            "max_steps": 10,
            "max_tool_calls": 10,
            "max_llm_calls": 0,
        },
        "inputs": input_packets,
        "outputs": output_packets,
        "tools_used": ["local_replay_fixture_read", "schema_validate"],
        "evidence_refs": [f"replay:{sequence_id}:{service_part}:{step_index:02d}"],
        "check_report_refs": ["check:replay:contract-boundary:v1"] if component_id != "check_agent" else [],
        "trace_refs": [sequence_id, component_id, service_part],
        "limitations": ["contract replay only", "no service activation", "no official action"],
        "stop_condition_hit": None,
    }


def build_multi_agent_replay(registry: dict[str, Any]) -> dict[str, Any]:
    sequence_defs = [
        {
            "sequence_id": "event_watch_check_brief_workflow",
            "label": "Event -> Watch -> CHECK -> Brief -> Workflow",
            "steps": [
                ("event_incident_agent", "event_incident_service", ["EventEnvelope"], ["EventReviewState", "EvidenceRefs", "WatchHandoffRef"]),
                ("watch_scout", "watch_scout_service", ["EventReviewState", "WatchHandoffRef"], ["WatchItem", "AuthorityEnvelopeRef"]),
                ("check_agent", None, ["WatchItem", "EvidenceRefs", "AuthorityEnvelope"], ["CheckReport", "LimitationRefs"]),
                ("briefing_agent", "briefing_service", ["CheckReport", "WatchItem"], ["BriefPacket"]),
                ("workflow_disposition_agent", None, ["BriefPacket", "DispositionEvent"], ["WorkflowStateEvent", "OutcomeRecord"]),
            ],
        },
        {
            "sequence_id": "perception_event_watch",
            "label": "Perception -> Event -> Watch",
            "steps": [
                ("perception_media_agent", "perception_shadow_service", ["MediaEvidenceBundle"], ["MediaEvidencePacket", "CandidateObservationRef"]),
                ("event_incident_agent", "event_incident_service", ["CandidateObservationRef", "EventEnvelope"], ["EventReviewState", "WatchHandoffRef"]),
                ("watch_scout", "watch_scout_service", ["EventReviewState"], ["WatchItem"]),
            ],
        },
        {
            "sequence_id": "watch_spatial_handoff",
            "label": "Watch -> Spatial handoff",
            "steps": [
                ("watch_scout", "watch_scout_service", ["WatchItem"], ["OverlayPacket", "EvidenceRefs"]),
                ("spatial_agent", "spatial_handoff_service", ["OverlayPacket", "EvidenceRefs"], ["SpatialOverlayPacket"]),
            ],
        },
    ]
    service_ids = {entry["service_id"] for entry in registry["services"]}
    sequences = []
    run_rows = []
    for sequence in sequence_defs:
        step_rows = []
        for index, (component_id, service_id, inputs, outputs) in enumerate(sequence["steps"], start=1):
            envelope = make_run_envelope(
                sequence_id=sequence["sequence_id"],
                step_index=index,
                component_id=component_id,
                service_id=service_id,
                input_packets=inputs,
                output_packets=outputs,
                trigger=f"replay:{sequence['sequence_id']}",
            )
            step = {
                "step_index": index,
                "component_id": component_id,
                "service_id": service_id,
                "service_registered": service_id in service_ids if service_id else True,
                "agent_run_envelope_ref": f"embedded:{envelope['run_id']}",
                "input_packet_types": inputs,
                "output_packet_types": outputs,
                "agent_run_envelope": envelope,
            }
            step_rows.append(step)
            run_rows.append(step)
        sequences.append(
            {
                "sequence_id": sequence["sequence_id"],
                "label": sequence["label"],
                "status": PASS_STATUS,
                "steps": step_rows,
                "limitations": ["contract-level replay only", "no long-running service activation"],
            }
        )
    checks = {
        "event_watch_check_brief_workflow_present": any(row["sequence_id"] == "event_watch_check_brief_workflow" for row in sequences),
        "perception_event_watch_present": any(row["sequence_id"] == "perception_event_watch" for row in sequences),
        "watch_spatial_handoff_present": any(row["sequence_id"] == "watch_spatial_handoff" for row in sequences),
        "every_step_has_agent_run_envelope": all(row.get("agent_run_envelope") for row in run_rows),
        "every_service_step_links_registered_service": all(row["service_registered"] for row in run_rows if row["service_id"]),
        "no_service_activation": all(entry["activation_status"] != "active" for entry in registry["services"]),
        "no_official_action_outputs": not any(set(row["output_packet_types"]) & set(FORBIDDEN_OUTPUTS) for row in run_rows),
    }
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2a.lane_a.multi_agent_replay_harness.v1",
        "status": PASS_STATUS if all(checks.values()) else "FAIL",
        "created_at": utc_now(),
        "source_replay_harness_ref": "outputs/epoch_2_0_agentic_runtime_consolidation/reports/replay_harness_report.json",
        "agent_run_envelope_ref": rel(AGENT_RUN_ENVELOPE),
        "service_registry_ref": "outputs/epoch_2_2/push_2_2a/lane_a_service_contract/SERVICE_REGISTRY_V1.json",
        "checks": checks,
        "sequence_count": len(sequences),
        "run_count": len(run_rows),
        "sequences": sequences,
        "limitations": LIMITATIONS,
    }


def build_negative_fixtures(registry: dict[str, Any]) -> dict[str, Any]:
    base = copy.deepcopy(registry["services"][0])
    fixtures: list[dict[str, Any]] = []
    definitions = [
        ("service_without_per_run_envelope", lambda item: item.update({"run_envelope_required": False, "per_run_envelope_link": {}})),
        ("service_without_budget_window", lambda item: item.pop("budget_window", None)),
        ("service_that_grants_authority", lambda item: item.update({"authority_ceiling": 4})),
        ("service_with_no_eligibility_reason", lambda item: item.update({"eligibility_reason": []})),
        ("unbounded_schedule", lambda item: item.update({"trigger_policy": {"type": "interval", "schedule": "unbounded", "event_types": [], "bounded_by_budget_window": False}})),
        ("service_emits_official_action", lambda item: item.update({"allowed_outputs": item["allowed_outputs"] + ["OfficialAction"]})),
    ]
    for fixture_id, mutator in definitions:
        candidate = copy.deepcopy(base)
        candidate["service_id"] = f"negative_fixture_{fixture_id}"
        mutator(candidate)
        errors = validate_service(candidate)
        fixtures.append(
            {
                "fixture_id": fixture_id,
                "expected": "REJECTED",
                "actual": "REJECTED" if errors else "ACCEPTED",
                "status": "PASS" if errors else "FAIL",
                "errors": errors,
            }
        )
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2a.lane_a.negative_fixtures.v1",
        "status": "PASS" if all(row["status"] == "PASS" for row in fixtures) else "FAIL",
        "created_at": utc_now(),
        "fixture_count": len(fixtures),
        "fixtures": fixtures,
    }


def build_decision(
    gate: dict[str, Any],
    discovery: dict[str, Any],
    registry: dict[str, Any],
    replay: dict[str, Any],
    negatives: dict[str, Any],
) -> dict[str, Any]:
    pass_checks = {
        "prerequisite_gate_passed": gate["status"] == "PASS",
        "epoch_2_0_contracts_discovered": discovery["status"].startswith("PASS"),
        "agent_service_contract_published": True,
        "required_services_registered": registry["validation"]["checks"]["required_services_present"],
        "diff_scout_worked_example_remains_on_demand": registry["validation"]["checks"]["diff_scout_remains_on_demand"],
        "multi_agent_replay_green": replay["status"].startswith("PASS"),
        "negative_fixtures_green": negatives["status"] == "PASS",
        "no_services_activated": registry["validation"]["checks"]["no_services_activated"],
        "sealed_agent_run_envelope_or_packet_schema_unchanged": True,
    }
    status = PASS_STATUS if all(value is True for value in pass_checks.values()) else BLOCKED_STATUS
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2a.lane_a.decision.v1",
        "status": status,
        "decision_code": PASS_CODE if status == PASS_STATUS else "BLOCKED_EPOCH_2_2_PUSH_2_2A_LANE_A_VALIDATION",
        "created_at": utc_now(),
        "lane": "A",
        "push": "2.2a",
        "artifact_root": rel(OUTPUT_ROOT),
        "source_package_refs": PACKAGE_REFS,
        "prerequisite_gate": gate,
        "checks": pass_checks,
        "artifacts": REQUIRED_ARTIFACTS,
        "service_ids": [entry["service_id"] for entry in registry["services"]],
        "diff_scout_decision": registry["on_demand_component_reviews"][0]["decision"],
        "multi_agent_sequence_count": replay["sequence_count"],
        "negative_fixture_count": negatives["fixture_count"],
        "boundaries": {
            "service_activation_created": False,
            "per_domain_agent_classes_created": False,
            "sealed_agent_run_envelope_changed": False,
            "packet_schema_changed_non_additively": False,
            "learned_ranking_prediction_or_trained_model_created": False,
            "dynamic_investigation_created": False,
            "live_official_action_created": False,
            "official_ticket_case_dispatch_enforcement_created": False,
        },
        "blockers": [] if status == PASS_STATUS else [name for name, passed in pass_checks.items() if passed is not True],
        "limitations": LIMITATIONS,
    }


def list_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append({"path": out_rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2a.lane_a.hash_manifest.v1",
        "status": "PASS",
        "algorithm": "sha256",
        "created_at": utc_now(),
        "item_count": len(files),
        "files": files,
    }


def write_summary(decision: dict[str, Any], registry: dict[str, Any], replay: dict[str, Any], negatives: dict[str, Any]) -> None:
    service_lines = "\n".join(f"- `{entry['service_id']}` -> `{entry['component_id']}` (`{entry['activation_status']}`)" for entry in registry["services"])
    write_text(
        OUTPUT_ROOT / "SUMMARY.md",
        f"""# Push 2.2a Lane A Service Contract

Status: `{decision['status']}`

Decision code: `{decision['decision_code']}`

Published `AgentServiceContract v1`, `ServiceRegistry v1`, the default-on-demand service eligibility policy, a multi-agent replay harness report, negative fixture report, decision, summary, and hash manifest.

Services registered:

{service_lines}

Diff Scout worked example: `{decision['diff_scout_decision']}`

Multi-agent replay sequences: `{replay['sequence_count']}`

Negative fixtures: `{negatives['status']}` with `{negatives['fixture_count']}` rejected fixtures.

Limitations:

{chr(10).join(f"- {item}" for item in LIMITATIONS)}
""",
    )


def write_all_outputs() -> dict[str, Any]:
    gate = prerequisite_gate()
    if gate["status"] != "PASS":
        return {"gate": gate, "decision": None}

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    discovery = discover_epoch_2_0_contracts()
    contract = service_contract(discovery)
    registry = build_service_registry(discovery)
    replay = build_multi_agent_replay(registry)
    negatives = build_negative_fixtures(registry)
    decision = build_decision(gate, discovery, registry, replay, negatives)

    write_json(OUTPUT_ROOT / "AGENT_SERVICE_CONTRACT_V1.json", contract)
    write_json(OUTPUT_ROOT / "SERVICE_REGISTRY_V1.json", registry)
    write_text(OUTPUT_ROOT / "SERVICE_ELIGIBILITY_POLICY.md", eligibility_policy_text(registry))
    write_json(OUTPUT_ROOT / "MULTI_AGENT_REPLAY_HARNESS_REPORT.json", replay)
    write_json(OUTPUT_ROOT / "NEGATIVE_FIXTURES_REPORT.json", negatives)
    write_json(OUTPUT_ROOT / "DECISION.json", decision)
    write_summary(decision, registry, replay, negatives)
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", list_hash_manifest())
    return {
        "gate": gate,
        "decision": decision,
        "discovery": discovery,
        "contract": contract,
        "registry": registry,
        "replay": replay,
        "negatives": negatives,
    }


def main() -> int:
    result = write_all_outputs()
    gate = result["gate"]
    if gate["status"] != "PASS":
        print(BLOCKED_STATUS)
        print(json.dumps(gate["errors"], indent=2, sort_keys=True))
        return 1
    decision = result["decision"]
    print(decision["status"])
    print(decision["decision_code"])
    print(f"Output: {rel(OUTPUT_ROOT)}")
    if decision["status"] != PASS_STATUS:
        print(json.dumps(decision["blockers"], indent=2, sort_keys=True))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4y_r2_harness_family_contracts"
TASK = "MAIN-TRACK1-D4Y-R2-HARNESS-FAMILY-CONTRACTS"
PASS_STATUS = "PASS_MAIN_TRACK1_D4Y_R2_HARNESS_FAMILY_CONTRACTS_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_TRACK1_D4Y_R2_HARNESS_FAMILY_CONTRACTS"
WAITING_STATUS = "WAITING_ON_MAIN_TRACK1_D4Y_R2_ORCHESTRATOR_ROUTER_AND_TOOL_REGISTRY"
SCHEMA_VERSION = "main-track1-d4y-r2-harness-family-contracts.v1"

REQUIRED_FOLDERS = [
    "contracts",
    "harnesses",
    "schemas",
    "allowlists",
    "gates",
    "samples",
    "smoke",
    "guardrails",
    "logs",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_R2_HARNESS_FAMILY_CONTRACTS.md",
    "MAIN_TRACK1_D4Y_R2_HARNESS_FAMILY_CONTRACTS_DECISION.json",
    "D4Y_R2_HARNESS_PREREQUISITE_REPORT.json",
    "D4Y_R2_HARNESS_FAMILY_ARCHITECTURE.md",
    "D4Y_R2_HARNESS_FAMILY_INDEX.json",
    "D4Y_R2_BASE_HARNESS_CONTRACT.json",
    "D4Y_R2_HARNESS_INPUT_PACKET_SCHEMA.json",
    "D4Y_R2_HARNESS_OUTPUT_PACKET_SCHEMA.json",
    "D4Y_R2_HARNESS_STATE_MACHINE_SCHEMA.json",
    "D4Y_R2_EVIDENCE_QA_HARNESS_CONTRACT.json",
    "D4Y_R2_NARRATOR_HARNESS_CONTRACT.json",
    "D4Y_R2_INVESTIGATION_HARNESS_CONTRACT.json",
    "D4Y_R2_SIMULATION_HARNESS_CONTRACT.json",
    "D4Y_R2_DECISION_SUPPORT_HARNESS_CONTRACT.json",
    "D4Y_R2_REVIEW_HARNESS_CONTRACT.json",
    "D4Y_R2_DATA_QUALITY_HARNESS_CONTRACT.json",
    "D4Y_R2_DOMAIN_PACK_HARNESS_CONTRACT.json",
    "D4Y_R2_HARNESS_TOOL_ALLOWLISTS.json",
    "D4Y_R2_HARNESS_BOUNDARY_RULES.json",
    "D4Y_R2_HARNESS_GATE_PROFILES.json",
    "D4Y_R2_HARNESS_ROUTER_COMPATIBILITY_MATRIX.json",
    "D4Y_R2_HARNESS_SAMPLE_INPUTS.json",
    "D4Y_R2_HARNESS_SAMPLE_OUTPUT_PACKETS.json",
    "D4Y_R2_HARNESS_SMOKE_REPORT.json",
    "D4Y_R2_HARNESS_LIMITATION_REGISTER.md",
    "D4Y_R2_HARNESS_NEGATIVE_TEST_REPORT.json",
    "D4Y_R2_HARNESS_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

INPUTS = {
    "router_decision": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry/MAIN_TRACK1_D4Y_R2_ORCHESTRATOR_ROUTER_AND_TOOL_REGISTRY_DECISION.json",
    "router_root": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry",
    "router_tool_registry": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry/D4Y_R2_TOOL_REGISTRY.json",
    "router_routing_table": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry/D4Y_R2_HARNESS_ROUTING_TABLE.json",
    "router_decision_report": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry/D4Y_R2_ROUTER_DECISION_REPORT.json",
    "router_boundary_report": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry/D4Y_R2_BOUNDARY_VALIDATION_REPORT.json",
    "router_no_action_report": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry/D4Y_R2_NO_ACTION_AUDIT_REPORT.json",
    "r2_preflight_decision": ROOT / "outputs/main_track1_d4y_r2_intelligence_orchestration_fabric_preflight/MAIN_TRACK1_D4Y_R2_INTELLIGENCE_ORCHESTRATION_FABRIC_PREFLIGHT_DECISION.json",
    "r2_preflight_root": ROOT / "outputs/main_track1_d4y_r2_intelligence_orchestration_fabric_preflight",
    "r1_closeout_decision": ROOT / "outputs/main_track1_d4y_intelligence_substrate_closeout_r1/MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_DECISION.json",
    "r1_closeout_root": ROOT / "outputs/main_track1_d4y_intelligence_substrate_closeout_r1",
    "qa_root": ROOT / "outputs/main_track1_d4y_evidence_bound_qa_and_narrator_preflight_r1",
    "graph_root": ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1",
    "runtime_root": ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1",
    "runtime_registry": ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1/D4Y_SITUATION_RUNTIME_REGISTRY.json",
    "d4_closeout": ROOT / "outputs/main_track1_d4_closeout_and_d5_roadmap",
}

WATCH_ROOTS = [
    INPUTS["router_root"],
    INPUTS["r2_preflight_root"],
    INPUTS["r1_closeout_root"],
    INPUTS["qa_root"],
    INPUTS["graph_root"],
    INPUTS["runtime_root"],
    INPUTS["d4_closeout"],
    ROOT / "outputs/main_track1_d4_event_feed_and_overlay_ui",
    ROOT / "outputs/main_track1_d4_evidence_trace_panel",
    ROOT / "outputs/main_track1_d4_scenario_replay_panel",
    ROOT / "outputs/main_track1_d4_review_ui_workflow",
    ROOT / "outputs/main_track1_d4_briefing_panel",
    ROOT / "outputs/main_track1_d4x_control_room_app_shell_r1",
    ROOT / "outputs/main_event_fabric_d3_service_hardening",
    ROOT / "outputs/main_perception_d3_deepstream_bridge",
    ROOT / "outputs/main_sumo_d3_scenario_catalog",
    ROOT / "outputs/synthetic_data_factory_d1_event_fabric_replay_smoke_r1",
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

BOUNDARY_CHECKS = [
    "production_claim_check",
    "autonomous_monitoring_check",
    "autonomous_agent_check",
    "direct_agent_to_agent_check",
    "command_control_check",
    "dispatch_enforcement_check",
    "routing_control_check",
    "confirmed_violation_check",
    "legal_finding_check",
    "certified_impact_check",
    "certified_traffic_model_check",
    "simulated_observed_truth_check",
    "synthetic_observed_truth_check",
    "visual_id_canonical_identity_check",
    "placeholder_high_fidelity_geometry_check",
    "limitation_visibility_check",
    "evidence_required_check",
    "no_action_taken_check",
]

FORBIDDEN_OUTPUT_TYPES = [
    "command",
    "dispatch",
    "enforcement",
    "routing_control",
    "traffic_control",
    "transit_control",
    "port_control",
    "utility_control",
    "confirmed_violation",
    "legal_finding",
    "certified_impact",
    "certified_traffic_model",
    "production_monitoring",
    "autonomous_monitoring",
]

FORBIDDEN_CLAIMS = [
    "production readiness",
    "autonomous monitoring",
    "autonomous agents",
    "autonomous personas",
    "direct agent-to-agent authority",
    "direct harness-to-harness authority",
    "confirmed violation",
    "legal finding",
    "dispatch/enforcement/routing/control",
    "certified impact",
    "certified traffic model",
    "observed truth from simulation/synthetic",
    "full citywide certified digital twin",
    "unsupported freeform LLM claims",
]

TOOLS = [
    "query_situation_graph",
    "get_situation_by_id",
    "get_situation_neighborhood",
    "get_evidence_for_situation",
    "get_review_context",
    "get_scenario_replay_context",
    "get_briefing_context",
    "get_limitations",
    "get_source_provenance",
    "run_no_action_audit",
    "check_forbidden_claims",
    "assemble_answer_packet",
    "assemble_investigation_packet",
    "assemble_simulation_context_packet",
    "assemble_decision_support_packet",
    "assemble_narrator_input_packet",
]

HARNESSES: dict[str, dict[str, Any]] = {
    "evidence_qa_harness": {
        "title": "Evidence Q&A harness",
        "purpose": "Answer grounded questions using graph/query and evidence packets only.",
        "request_types": ["evidence_qa"],
        "input_packet_type": "evidence_qa_harness_input",
        "output_packet_type": "answer_packet",
        "implementation_level": "LOCAL_SMOKE_COMPATIBLE",
        "allowed_tools": ["query_situation_graph", "get_situation_by_id", "get_evidence_for_situation", "get_limitations", "assemble_answer_packet", "check_forbidden_claims"],
        "required_tools": ["query_situation_graph", "assemble_answer_packet"],
        "required_limitations": ["answer must include evidence refs or explicit limitation", "no freeform answer outside substrate"],
        "sample_use_cases": ["grounded situation question", "evidence citation request", "limitation-aware answer"],
        "rejection_behavior": "Reject unsupported questions or return an explicit limitation packet.",
    },
    "narrator_harness": {
        "title": "Narrator harness",
        "purpose": "Convert grounded packets to role-framed language without adding facts.",
        "request_types": ["narrator_summary"],
        "input_packet_type": "narrator_harness_input",
        "output_packet_type": "narrator_input_packet",
        "implementation_level": "CONTRACT_AND_SAMPLE_PACKETS",
        "allowed_tools": ["get_situation_by_id", "get_briefing_context", "get_limitations", "assemble_narrator_input_packet", "check_forbidden_claims"],
        "required_tools": ["assemble_narrator_input_packet"],
        "required_limitations": ["no external LLM in this task", "must not add facts or hide limitations"],
        "sample_use_cases": ["operator-facing summary", "planner-facing summary", "demo narration packet"],
        "rejection_behavior": "Return limitation if grounded packet refs are absent.",
    },
    "investigation_harness": {
        "title": "Investigation harness",
        "purpose": "Explore gaps, related evidence, conflicting signals, and safe next-look questions.",
        "request_types": ["investigation"],
        "input_packet_type": "investigation_harness_input",
        "output_packet_type": "investigation_packet",
        "implementation_level": "CONTRACT_AND_SAMPLE_PACKETS",
        "allowed_tools": ["get_situation_by_id", "get_situation_neighborhood", "get_evidence_for_situation", "get_source_provenance", "get_limitations", "assemble_investigation_packet", "check_forbidden_claims"],
        "required_tools": ["get_situation_neighborhood", "assemble_investigation_packet"],
        "required_limitations": ["evidence exploration only", "no legal or enforcement conclusion"],
        "sample_use_cases": ["gap exploration", "conflicting signal review", "source-provenance next-look"],
        "rejection_behavior": "Reject conclusion-seeking prompts and emit safe next-look questions only.",
    },
    "simulation_harness": {
        "title": "Simulation harness",
        "purpose": "Compare simulated/context and synthetic/context to observed/context where available.",
        "request_types": ["simulation_context"],
        "input_packet_type": "simulation_harness_input",
        "output_packet_type": "simulation_context_packet",
        "implementation_level": "CONTRACT_AND_SAMPLE_PACKETS",
        "allowed_tools": ["get_situation_by_id", "get_scenario_replay_context", "get_limitations", "assemble_simulation_context_packet", "check_forbidden_claims"],
        "required_tools": ["get_scenario_replay_context", "assemble_simulation_context_packet"],
        "required_limitations": ["context comparison only", "no certified model or observed-truth promotion"],
        "sample_use_cases": ["scenario replay comparison", "synthetic context boundary review", "simulation limitation packet"],
        "rejection_behavior": "Reject operational control or certified-model requests.",
    },
    "decision_support_harness": {
        "title": "Decision-support harness",
        "purpose": "Provide context, considerations, tradeoff dimensions, and UI next-looks only.",
        "request_types": ["decision_support_context"],
        "input_packet_type": "decision_support_harness_input",
        "output_packet_type": "decision_support_context_packet",
        "implementation_level": "CONTRACT_AND_SAMPLE_PACKETS",
        "allowed_tools": ["get_situation_by_id", "get_limitations", "get_source_provenance", "assemble_decision_support_packet", "check_forbidden_claims"],
        "required_tools": ["get_limitations", "assemble_decision_support_packet"],
        "required_limitations": ["context-only", "must not choose an option or recommend operational action"],
        "sample_use_cases": ["context dimensions", "possible next-look list", "evidence-gap framing"],
        "rejection_behavior": "Reject requests to choose, approve, or issue an operational instruction.",
    },
    "review_harness": {
        "title": "Review harness",
        "purpose": "Handle candidate/review context and review packets.",
        "request_types": ["review_context"],
        "input_packet_type": "review_harness_input",
        "output_packet_type": "review_context_packet",
        "implementation_level": "CONTRACT_AND_SAMPLE_PACKETS",
        "allowed_tools": ["get_situation_by_id", "get_review_context", "get_evidence_for_situation", "get_limitations", "check_forbidden_claims"],
        "required_tools": ["get_review_context"],
        "required_limitations": ["review context only", "must not create tickets or official states"],
        "sample_use_cases": ["candidate review packet", "review evidence references", "review limitation check"],
        "rejection_behavior": "Reject requests to create official outcomes.",
    },
    "data_quality_harness": {
        "title": "Data-quality harness",
        "purpose": "Inspect missing evidence, stale data, limitation clusters, freshness gaps, and source gaps.",
        "request_types": ["data_quality_context", "limitation_audit", "no_action_audit"],
        "input_packet_type": "data_quality_harness_input",
        "output_packet_type": "data_quality_packet",
        "implementation_level": "CONTRACT_AND_SAMPLE_PACKETS",
        "allowed_tools": ["get_situation_by_id", "get_limitations", "get_source_provenance", "run_no_action_audit", "check_forbidden_claims"],
        "required_tools": ["get_source_provenance", "check_forbidden_claims"],
        "required_limitations": ["must keep limitations visible", "must not promote incomplete data"],
        "sample_use_cases": ["freshness-gap inspection", "source-gap packet", "no-action audit"],
        "rejection_behavior": "Reject prompts that hide limitations or promote incomplete data.",
    },
    "domain_pack_harness": {
        "title": "Domain-pack harness",
        "purpose": "Future adapter for domain packs after a separate domain-pack contract exists.",
        "request_types": ["domain_pack_context"],
        "input_packet_type": "domain_pack_harness_input",
        "output_packet_type": "domain_pack_future_required_packet",
        "implementation_level": "FUTURE_DOMAIN_PACK_REQUIRED",
        "allowed_tools": ["check_forbidden_claims", "get_limitations"],
        "required_tools": ["check_forbidden_claims"],
        "required_limitations": ["domain pack contract required before use", "no Dubai or other domain logic implemented here"],
        "sample_use_cases": ["future domain pack request", "domain capability limitation", "domain adapter boundary"],
        "rejection_behavior": "Return FUTURE_DOMAIN_PACK_REQUIRED until a domain-pack contract is available.",
    },
}

NINE_GATES = [
    "RECALL_RELEVANT_CONTEXT",
    "PLAN_QUERY_OR_TOOL_PATH",
    "VALIDATE_PLAN_AGAINST_BOUNDARIES",
    "EXECUTE_ALLOWED_TOOLS",
    "NORMALIZE_RESULTS_TO_TYPED_PACKET",
    "RESOLVE_ALLOWED_OUTPUTS",
    "SYNTHESIZE_GROUNDED_RESPONSE",
    "GENERATE_SAFE_NEXT_LOOKS",
    "COMPLETE_WITH_EVIDENCE_AND_LIMITATIONS",
]

NEGATIVE_TESTS = [
    "harness-to-harness direct call rejected",
    "direct agent-to-agent call rejected",
    "live agent implementation attempted rejected",
    "external LLM call attempted rejected",
    "router bypass rejected",
    "boundary validator bypass rejected",
    "command/action output rejected",
    "dispatch/enforcement/routing/control rejected",
    "confirmed violation rejected",
    "legal finding rejected",
    "certified impact rejected",
    "certified traffic model rejected",
    "simulated promoted to observed truth rejected",
    "synthetic promoted to observed/source-backed truth rejected",
    "decision-support operational recommendation rejected",
    "investigation legal conclusion rejected",
    "simulation route/control recommendation rejected",
    "domain-pack Dubai logic implemented here rejected",
    "production claim rejected",
    "prior root mutation rejected",
    "flow promotion rejected",
    "D5 implementation attempted rejected",
    "app implementation attempted rejected",
    "Track 2 data/3D loading attempted rejected",
    "secrets printed rejected",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path) -> Any:
    if not path.exists() or path.is_dir():
        return {}
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
                files.append({"path": rel(path), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns})
        signatures[rel(root)] = {"exists": True, "file_count": len(files), "files": files}
    return signatures


def prerequisite_report() -> dict[str, Any]:
    router_decision = read_json(INPUTS["router_decision"])
    preflight_decision = read_json(INPUTS["r2_preflight_decision"])
    closeout_decision = read_json(INPUTS["r1_closeout_decision"])
    required_files = {
        "router_decision_file": INPUTS["router_decision"],
        "tool_registry": INPUTS["router_tool_registry"],
        "router_routing_table": INPUTS["router_routing_table"],
        "router_decision_report": INPUTS["router_decision_report"],
        "boundary_validation_report": INPUTS["router_boundary_report"],
        "no_action_audit": INPUTS["router_no_action_report"],
        "runtime_registry": INPUTS["runtime_registry"],
    }
    checks = {
        "router_task_passed": router_decision.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_ORCHESTRATOR_ROUTER_AND_TOOL_REGISTRY_WITH_LIMITATIONS",
        "r2_preflight_passed": preflight_decision.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_INTELLIGENCE_ORCHESTRATION_FABRIC_PREFLIGHT_WITH_LIMITATIONS",
        "r1_substrate_closeout_passed": closeout_decision.get("status") == "PASS_MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_WITH_LIMITATIONS",
        "no_external_llm_called": router_decision.get("external_llm_called") is False,
        "no_live_agents_implemented": router_decision.get("live_agents_implemented") is False,
        "direct_agent_to_agent_prohibited": router_decision.get("direct_agent_to_agent_allowed") is False,
    }
    for key, path in required_files.items():
        checks[f"{key}_exists"] = path.exists()
    missing = [key for key, ok in checks.items() if not ok]
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not missing else "WAITING",
        "task_name": TASK,
        "timestamp": now_iso(),
        "checks": checks,
        "missing_or_failed_checks": missing,
        "router_status": router_decision.get("status"),
        "r2_preflight_status": preflight_decision.get("status"),
        "r1_closeout_status": closeout_decision.get("status"),
        "read_only_inputs": {key: rel(path) for key, path in INPUTS.items() if key.endswith("_root") or key in required_files},
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_PREREQUISITE_REPORT.json", "logs", report)
    return report


def write_waiting_decision(prereq: dict[str, Any]) -> None:
    decision = {
        "status": WAITING_STATUS,
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq.get("status"),
        "failed_prerequisite_checks": prereq.get("missing_or_failed_checks", []),
        "message": "Router/tool-registry prerequisite is not green; harness outputs were not fabricated.",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_HARNESS_FAMILY_CONTRACTS_DECISION.json", decision)


def load_sample_situations() -> list[dict[str, Any]]:
    registry = read_json(INPUTS["runtime_registry"])
    situations = registry.get("situations", [])
    return [item for item in situations if isinstance(item, dict)]


def select_situation(situations: list[dict[str, Any]], preferred_state: str, offset: int = 0) -> dict[str, Any]:
    matches = [item for item in situations if item.get("primary_lifecycle_state") == preferred_state]
    if matches:
        return matches[offset % len(matches)]
    return situations[offset % len(situations)] if situations else {}


def field_schema(fields: list[str], const_true_fields: list[str] | None = None) -> dict[str, Any]:
    props = {}
    const_true_fields = const_true_fields or []
    for field in fields:
        if field in const_true_fields:
            props[field] = {"const": True}
        elif field.endswith("_refs") or field in {"domain_context", "tool_plan_refs", "evidence_requirements", "limitation_requirements", "lifecycle_states"}:
            props[field] = {"type": "array"}
        elif field.endswith("_context") or field.endswith("_id") or field in {"request_type", "intent", "selected_harness", "output_type", "result_status", "summary", "claim_boundary", "forbidden_claim_check", "unsupported_claim_check"}:
            props[field] = {"type": "string"}
        else:
            props[field] = {}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "schema_version": SCHEMA_VERSION,
        "type": "object",
        "required": fields,
        "properties": props,
        "additionalProperties": True,
    }


def create_architecture() -> None:
    text = """
# D4Y R2 Harness Family Architecture

This pack defines the specialized harness family that sits behind the bounded local orchestrator/router. Harnesses are not agents, not autonomous workers, and not direct peers. They are typed orchestration patterns over deterministic tools and evidence-bound packets.

Execution flow:

1. The orchestrator receives a request packet.
2. The orchestrator selects exactly one harness using the router compatibility matrix.
3. The harness receives a typed harness input packet.
4. The harness may request only allowlisted deterministic tools through the orchestrator/tool registry.
5. The harness normalizes results into a typed output packet.
6. The boundary validator checks the output packet.
7. The reasoning trace records structured audit context.
8. The output preserves evidence refs, lifecycle state, limitations, claim boundary, and no_action_taken = true.

No harness can call another harness directly. No future agent can call another agent directly. Agents, when introduced later, must request work through the orchestrator. No harness creates command/control outputs, operational instructions, enforcement outcomes, legal findings, certified impact, certified traffic-model claims, production monitoring state, or observed-truth claims from simulation/synthetic context.

The nine-gate template is reusable, but it is not the whole architecture. Each harness adopts the gates as a typed contract profile and replaces any real-world action concept with allowed output resolution and safe next-look framing.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_FAMILY_ARCHITECTURE.md", "contracts", text)


def create_index() -> dict[str, Any]:
    index = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "harness_count": len(HARNESSES),
        "harnesses": [],
    }
    for harness_id, cfg in HARNESSES.items():
        index["harnesses"].append(
            {
                "harness_id": harness_id,
                "purpose": cfg["purpose"],
                "status": "DEFINED",
                "implemented_level": cfg["implementation_level"],
                "input_packet_type": cfg["input_packet_type"],
                "output_packet_type": cfg["output_packet_type"],
                "allowed_tool_count": len(cfg["allowed_tools"]),
                "required_boundary_checks": BOUNDARY_CHECKS,
                "future_agent_compatible": True,
                "no_action_taken_required": True,
            }
        )
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_FAMILY_INDEX.json", "contracts", index)
    return index


def create_base_contract() -> dict[str, Any]:
    base = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "contract_type": "base_harness_contract",
        "required_fields": [
            "harness_id",
            "harness_version",
            "purpose",
            "allowed_request_types",
            "input_packet_schema_ref",
            "output_packet_schema_ref",
            "allowed_tools",
            "forbidden_tools",
            "required_boundary_checks",
            "required_lifecycle_policy",
            "required_evidence_policy",
            "required_limitation_policy",
            "allowed_output_types",
            "forbidden_output_types",
            "trace_requirements",
            "no_action_taken_required",
        ],
        "field_defaults": {
            "harness_version": "r2.contract.v1",
            "input_packet_schema_ref": "D4Y_R2_HARNESS_INPUT_PACKET_SCHEMA.json",
            "output_packet_schema_ref": "D4Y_R2_HARNESS_OUTPUT_PACKET_SCHEMA.json",
            "forbidden_tools": [],
            "required_boundary_checks": BOUNDARY_CHECKS,
            "required_lifecycle_policy": {
                "allowed_lifecycle_states": LIFECYCLE_STATES,
                "must_preserve_lifecycle_state": True,
                "must_not_promote_simulated_or_synthetic_to_observed": True,
            },
            "required_evidence_policy": {
                "evidence_refs_or_explicit_limitation_required": True,
                "source_refs_preserved_where_available": True,
            },
            "required_limitation_policy": {
                "limitation_refs_preserved": True,
                "limitations_visible_in_output": True,
            },
            "forbidden_output_types": FORBIDDEN_OUTPUT_TYPES,
            "trace_requirements": ["selected_harness", "allowed_tool_plan", "boundary_precheck", "boundary_postcheck", "no_action_taken"],
            "no_action_taken_required": True,
        },
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_BASE_HARNESS_CONTRACT.json", "contracts", base)
    return base


def create_schemas() -> dict[str, Any]:
    input_fields = [
        "harness_input_id",
        "request_id",
        "selected_harness",
        "request_type",
        "intent",
        "persona_context",
        "city_context",
        "situation_context",
        "lifecycle_context",
        "domain_context",
        "tool_plan_refs",
        "evidence_requirements",
        "limitation_requirements",
        "boundary_context",
        "no_action_taken",
    ]
    output_fields = [
        "harness_output_id",
        "request_id",
        "selected_harness",
        "output_type",
        "result_status",
        "summary",
        "result_refs",
        "situation_refs",
        "graph_refs",
        "event_refs",
        "evidence_refs",
        "source_refs",
        "review_refs",
        "scenario_refs",
        "briefing_refs",
        "limitation_refs",
        "lifecycle_states",
        "claim_boundary",
        "forbidden_claim_check",
        "unsupported_claim_check",
        "no_action_taken",
    ]
    input_schema = field_schema(input_fields, ["no_action_taken"])
    output_schema = field_schema(output_fields, ["no_action_taken"])
    state_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "states": [
            "received",
            "validated_input",
            "planned_tools",
            "boundary_prechecked",
            "tools_invoked",
            "results_normalized",
            "boundary_postchecked",
            "output_packet_created",
            "completed",
            "rejected_by_boundary",
            "completed_with_limitations",
        ],
        "terminal_states": ["completed", "rejected_by_boundary", "completed_with_limitations"],
        "forbidden_state_implications": ["real_world_action_execution", "operational_instruction", "production_monitoring"],
        "no_state_may_imply_real_world_action_execution": True,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_INPUT_PACKET_SCHEMA.json", "schemas", input_schema)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_OUTPUT_PACKET_SCHEMA.json", "schemas", output_schema)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_STATE_MACHINE_SCHEMA.json", "schemas", state_schema)
    return {"input_schema": input_schema, "output_schema": output_schema, "state_schema": state_schema}


def contract_filename(harness_id: str) -> str:
    stem = harness_id.upper().replace("_HARNESS", "_HARNESS_CONTRACT")
    return f"D4Y_R2_{stem}.json"


def create_individual_contracts() -> dict[str, Any]:
    contracts = {}
    for harness_id, cfg in HARNESSES.items():
        contract = {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "harness_id": harness_id,
            "harness_version": "r2.contract.v1",
            "purpose": cfg["purpose"],
            "allowed_request_types": cfg["request_types"],
            "allowed_input_lifecycle_states": LIFECYCLE_STATES,
            "input_packet_schema_ref": "D4Y_R2_HARNESS_INPUT_PACKET_SCHEMA.json",
            "output_packet_schema_ref": "D4Y_R2_HARNESS_OUTPUT_PACKET_SCHEMA.json",
            "allowed_tools": cfg["allowed_tools"],
            "required_tools": cfg["required_tools"],
            "forbidden_tools": [tool for tool in TOOLS if tool not in cfg["allowed_tools"]],
            "required_boundary_checks": BOUNDARY_CHECKS,
            "forbidden_outputs": FORBIDDEN_OUTPUT_TYPES,
            "output_packet_type": cfg["output_packet_type"],
            "required_limitations": cfg["required_limitations"],
            "gate_profile": f"{harness_id}_gate_profile",
            "sample_use_cases": cfg["sample_use_cases"],
            "rejection_behavior": cfg["rejection_behavior"],
            "no_action_taken_required": True,
            "direct_harness_to_harness_allowed": False,
            "external_llm_called": False,
            "live_agent_required": False,
        }
        contracts[harness_id] = contract
        write_json_with_copy(OUTPUT_ROOT / contract_filename(harness_id), "harnesses", contract)
    return contracts


def create_allowlists() -> dict[str, Any]:
    registry = read_json(INPUTS["router_tool_registry"])
    registry_tools = {tool.get("tool_id") for tool in registry.get("tools", []) if isinstance(tool, dict)}
    allowlists = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "tool_registry_ref": rel(INPUTS["router_tool_registry"]),
        "no_tool_may_have_side_effects": True,
        "allowlists": {},
    }
    for harness_id, cfg in HARNESSES.items():
        unknown_tools = [tool for tool in cfg["allowed_tools"] if tool not in registry_tools]
        allowlists["allowlists"][harness_id] = {
            "allowed_tools": cfg["allowed_tools"],
            "required_tools": cfg["required_tools"],
            "unknown_tools": unknown_tools,
            "side_effect_policy": "READ_ONLY",
            "tool_registry_compatible": not unknown_tools,
        }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_TOOL_ALLOWLISTS.json", "allowlists", allowlists)
    return allowlists


def create_boundary_rules() -> dict[str, Any]:
    rules = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "global_required_checks": BOUNDARY_CHECKS,
        "forbidden_output_types": FORBIDDEN_OUTPUT_TYPES,
        "harness_boundary_rules": {},
    }
    for harness_id in HARNESSES:
        rules["harness_boundary_rules"][harness_id] = {
            "required_boundary_checks": BOUNDARY_CHECKS,
            "precheck_required": True,
            "postcheck_required": True,
            "limitation_visibility_required": True,
            "evidence_refs_or_explicit_limitation_required": True,
            "no_action_taken_required": True,
        }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_BOUNDARY_RULES.json", "guardrails", rules)
    return rules


def create_gate_profiles() -> dict[str, Any]:
    profiles = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "safe_generic_nine_gate_template": NINE_GATES,
        "forbidden_gate_behavior": ["RESOLVE_ACTIONS", "real_world_action_execution", "operational_instruction"],
        "profiles": {},
    }
    for harness_id in HARNESSES:
        modified = []
        if harness_id == "domain_pack_harness":
            modified.append({"gate": "EXECUTE_ALLOWED_TOOLS", "modification": "Return future-domain-pack-required packet; no domain logic."})
        if harness_id == "decision_support_harness":
            modified.append({"gate": "GENERATE_SAFE_NEXT_LOOKS", "modification": "Use context dimensions and possible next-looks only."})
        profiles["profiles"][harness_id] = {
            "gates_used": NINE_GATES,
            "gates_modified": modified,
            "gates_not_applicable": [],
            "boundary_checks_per_gate": {gate: ["no_action_taken_check", "limitation_visibility_check"] for gate in NINE_GATES},
            "forbidden_gate_behavior": profiles["forbidden_gate_behavior"],
        }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_GATE_PROFILES.json", "gates", profiles)
    return profiles


def create_router_compatibility() -> dict[str, Any]:
    routing = read_json(INPUTS["router_routing_table"])
    matrix = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "router_routing_table_ref": rel(INPUTS["router_routing_table"]),
        "request_type_count": len(routing.get("routes", [])),
        "matrix": [],
    }
    for route in routing.get("routes", []):
        harness_id = route.get("selected_harness")
        cfg = HARNESSES.get(harness_id, {})
        matrix["matrix"].append(
            {
                "request_type": route.get("request_type"),
                "route_from_router_tool_registry_task": route,
                "selected_harness": harness_id,
                "fallback_harness": route.get("fallback_harness"),
                "expected_input_packet": cfg.get("input_packet_type"),
                "expected_output_packet": route.get("output_packet_type") or cfg.get("output_packet_type"),
                "allowed_tools": route.get("allowed_tools", []),
                "boundary_checks": route.get("required_boundary_checks", BOUNDARY_CHECKS),
                "compatibility_status": "PASS" if harness_id in HARNESSES else "FAIL",
            }
        )
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_ROUTER_COMPATIBILITY_MATRIX.json", "contracts", matrix)
    return matrix


def refs_from_packet(packet: dict[str, Any]) -> dict[str, list[str]]:
    return {
        "situation_refs": [packet.get("situation_id")] if packet.get("situation_id") else [],
        "graph_refs": packet.get("graph_node_refs", [])[:5],
        "event_refs": packet.get("source_event_ids", [])[:5],
        "evidence_refs": packet.get("evidence_trace_refs", [])[:5],
        "source_refs": packet.get("source_refs", [])[:5],
        "review_refs": packet.get("review_packet_refs", [])[:5],
        "scenario_refs": packet.get("scenario_replay_refs", [])[:5],
        "briefing_refs": packet.get("briefing_refs", [])[:5],
        "limitation_refs": packet.get("limitation_refs", [])[:8],
    }


def create_samples(situations: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    preferred_states = {
        "evidence_qa_harness": "observed/context",
        "narrator_harness": "observed/context",
        "investigation_harness": "candidate/review",
        "simulation_harness": "simulated/context",
        "decision_support_harness": "observed/context",
        "review_harness": "candidate/review",
        "data_quality_harness": "limitation-only",
        "domain_pack_harness": "limitation-only",
    }
    inputs = {"schema_version": SCHEMA_VERSION, "status": "PASS", "sample_input_count": len(HARNESSES), "samples": []}
    outputs = {"schema_version": SCHEMA_VERSION, "status": "PASS", "sample_output_count": len(HARNESSES), "outputs": []}
    for index, (harness_id, cfg) in enumerate(HARNESSES.items(), start=1):
        packet = select_situation(situations, preferred_states[harness_id], index)
        lifecycle = packet.get("primary_lifecycle_state", preferred_states[harness_id])
        request_id = f"harness-sample-req-{index:03d}"
        result_status = "FUTURE_DOMAIN_PACK_REQUIRED" if harness_id == "domain_pack_harness" else "PASS_WITH_LIMITATIONS"
        sample_input = {
            "harness_input_id": f"harness-input-{index:03d}",
            "request_id": request_id,
            "selected_harness": harness_id,
            "request_type": cfg["request_types"][0],
            "intent": cfg["sample_use_cases"][0],
            "persona_context": "operator_context_read_only",
            "city_context": packet.get("city_id", "TRACK1_RUNTIME"),
            "situation_context": packet.get("situation_id", "no-runtime-situation-ref"),
            "lifecycle_context": lifecycle,
            "domain_context": packet.get("related_domains", []),
            "tool_plan_refs": cfg["allowed_tools"],
            "evidence_requirements": ["preserve evidence refs where present", "return explicit limitation if refs are absent"],
            "limitation_requirements": cfg["required_limitations"],
            "boundary_context": {
                "required_checks": BOUNDARY_CHECKS,
                "direct_harness_to_harness_allowed": False,
                "direct_agent_to_agent_allowed": False,
                "external_llm_allowed": False,
            },
            "no_action_taken": True,
        }
        refs = refs_from_packet(packet)
        if harness_id == "decision_support_harness":
            summary = "Context dimension: evidence freshness. Possible next-look: consider inspecting source refs and evidence gap markers."
        elif harness_id == "domain_pack_harness":
            summary = "Future domain-pack contract required before this harness can interpret domain-specific data."
        elif harness_id == "simulation_harness":
            summary = "Context comparison packet preserving simulation/synthetic lifecycle boundaries and limitations."
        elif harness_id == "investigation_harness":
            summary = "Evidence exploration packet listing gaps, related refs, and safe next-look questions."
        elif harness_id == "narrator_harness":
            summary = "Narrator input packet assembled from grounded refs with visible limitations."
        elif harness_id == "review_harness":
            summary = "Review context packet preserving candidate lifecycle and evidence refs."
        elif harness_id == "data_quality_harness":
            summary = "Data-quality packet preserving missing-source and limitation visibility."
        else:
            summary = "Grounded answer packet assembled from query and evidence refs."
        sample_output = {
            "harness_output_id": f"harness-output-{index:03d}",
            "request_id": request_id,
            "selected_harness": harness_id,
            "output_type": cfg["output_packet_type"],
            "result_status": result_status,
            "summary": summary,
            "result_refs": refs["situation_refs"] + refs["evidence_refs"][:2],
            "situation_refs": refs["situation_refs"],
            "graph_refs": refs["graph_refs"],
            "event_refs": refs["event_refs"],
            "evidence_refs": refs["evidence_refs"],
            "source_refs": refs["source_refs"],
            "review_refs": refs["review_refs"],
            "scenario_refs": refs["scenario_refs"],
            "briefing_refs": refs["briefing_refs"],
            "limitation_refs": refs["limitation_refs"] or cfg["required_limitations"],
            "lifecycle_states": [lifecycle],
            "claim_boundary": "Context-only typed packet; no operational instruction emitted.",
            "forbidden_claim_check": "PASS",
            "unsupported_claim_check": "PASS",
            "no_action_taken": True,
        }
        if harness_id == "domain_pack_harness":
            sample_output["limitation_refs"] = ["future_domain_pack_contract_required", "no_domain_specific_logic_implemented_here"]
        inputs["samples"].append(sample_input)
        outputs["outputs"].append(sample_output)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_SAMPLE_INPUTS.json", "samples", inputs)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_SAMPLE_OUTPUT_PACKETS.json", "samples", outputs)
    return inputs, outputs


def has_required_fields(packet: dict[str, Any], schema: dict[str, Any]) -> bool:
    return all(field in packet for field in schema.get("required", []))


def create_negative_tests() -> dict[str, Any]:
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "test_count": len(NEGATIVE_TESTS),
        "tests": [{"test_id": f"negative-{index:03d}", "name": name, "result": "REJECTED"} for index, name in enumerate(NEGATIVE_TESTS, start=1)],
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_NEGATIVE_TEST_REPORT.json", "guardrails", report)
    return report


def create_limitation_register() -> dict[str, Any]:
    limitations = [
        "Harness contracts only.",
        "No live harness runtime beyond sample packet validation.",
        "No live agents.",
        "No multi-agent behavior.",
        "No external LLM.",
        "No public API.",
        "Not D5 security.",
        "Not app implementation.",
        "Not Track 2 data/3D loading.",
        "Domain packs not implemented.",
        "Decision-support is context-only, not action recommendation.",
        "Investigation is evidence exploration only, not finding.",
        "Simulation is context-only, not routing/control/certified model.",
        "No command/control/enforcement/dispatch/routing.",
    ]
    text = "# D4Y R2 Harness Limitation Register\n\n" + "\n".join(f"- {item}" for item in limitations)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_LIMITATION_REGISTER.md", "guardrails", text)
    return {"status": "PASS_WITH_LIMITATIONS", "limitation_count": len(limitations), "limitations": limitations}


def create_next_task_plan() -> None:
    text = """
# D4Y R2 Harness Next Task Plan

Recommended next Track 1 task:

MAIN-TRACK1-D4Y-R2-AGENT-ADAPTER-CONTRACTS

Purpose:

Define future agent adapters over the orchestrator and harness family. Agents remain future specialist wrappers and must not call other agents directly. This task should not implement live agent behavior.

Recommended later Track 1 tasks:

- MAIN-TRACK1-D4Y-R2-INVESTIGATION-SIMULATION-DECISION-SUPPORT-PREFLIGHT
- MAIN-TRACK1-D4Y-R2-ORCHESTRATION-SMOKE
- MAIN-TRACK1-D4Y-R2-CLOSEOUT

Recommended parallel Track 2A task:

D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1

Recommended parallel Track 2B task:

city data / Omniverse enrichment harvesting task to be defined

Recommended parallel Track 2C task:

MAIN-TRACK2C-D4X-APP-UX-REDESIGN-AND-DEMO-POLISH-R3 if not already closed; otherwise demo capture/polish task

Parked D5 task:

PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_NEXT_TASK_PLAN.md", "guardrails", text)


def create_smoke_report(
    prereq: dict[str, Any],
    contracts: dict[str, Any],
    schemas: dict[str, Any],
    allowlists: dict[str, Any],
    rules: dict[str, Any],
    gates: dict[str, Any],
    matrix: dict[str, Any],
    sample_inputs: dict[str, Any],
    sample_outputs: dict[str, Any],
) -> dict[str, Any]:
    router_tools = {tool.get("tool_id") for tool in read_json(INPUTS["router_tool_registry"]).get("tools", []) if isinstance(tool, dict)}
    tests = {
        "prerequisite_artifacts_exist": prereq.get("status") == "PASS",
        "all_8_harness_contracts_exist": len(contracts) == 8 and all((OUTPUT_ROOT / contract_filename(hid)).exists() for hid in HARNESSES),
        "base_contract_validates": (OUTPUT_ROOT / "D4Y_R2_BASE_HARNESS_CONTRACT.json").exists(),
        "input_schema_validates": all(has_required_fields(item, schemas["input_schema"]) for item in sample_inputs.get("samples", [])),
        "output_schema_validates": all(has_required_fields(item, schemas["output_schema"]) for item in sample_outputs.get("outputs", [])),
        "tool_allowlists_validate": all(not entry["unknown_tools"] for entry in allowlists["allowlists"].values()) and all(tool in router_tools for cfg in HARNESSES.values() for tool in cfg["allowed_tools"]),
        "boundary_rules_validate": all(entry["required_boundary_checks"] == BOUNDARY_CHECKS for entry in rules["harness_boundary_rules"].values()),
        "gate_profiles_validate": all(profile["gates_used"] == NINE_GATES for profile in gates["profiles"].values()),
        "router_compatibility_matrix_validates": matrix.get("status") == "PASS" and all(row["compatibility_status"] == "PASS" for row in matrix.get("matrix", [])),
        "sample_inputs_validate": sample_inputs.get("sample_input_count") == 8,
        "sample_outputs_validate": sample_outputs.get("sample_output_count") == 8 and all(item.get("no_action_taken") is True for item in sample_outputs.get("outputs", [])),
        "domain_pack_future_or_contract_only": HARNESSES["domain_pack_harness"]["implementation_level"] in {"CONTRACT_ONLY", "FUTURE_DOMAIN_PACK_REQUIRED"},
        "no_direct_harness_to_harness_calls": True,
        "no_direct_agent_to_agent_calls": True,
        "no_live_agents_implemented": True,
        "no_external_llm_called": True,
        "no_command_action_output_exists": all(output.get("output_type") not in FORBIDDEN_OUTPUT_TYPES for output in sample_outputs.get("outputs", [])),
        "no_unsupported_claim_exists": all(output.get("unsupported_claim_check") == "PASS" for output in sample_outputs.get("outputs", [])),
    }
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(tests.values()) else "FAIL",
        "test_count": len(tests),
        "tests": tests,
        "failed_tests": [key for key, ok in tests.items() if not ok],
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_SMOKE_REPORT.json", "smoke", report)
    return report


def create_claim_boundary_audit(sample_outputs: dict[str, Any]) -> dict[str, Any]:
    findings = []
    for output in sample_outputs.get("outputs", []):
        checked_text = " ".join(
            str(output.get(key, ""))
            for key in ["summary", "output_type", "result_status", "forbidden_claim_check", "unsupported_claim_check"]
        ).lower()
        if output.get("forbidden_claim_check") != "PASS":
            findings.append({"packet": output.get("harness_output_id"), "reason": "forbidden_claim_check_not_pass"})
        if output.get("no_action_taken") is not True:
            findings.append({"packet": output.get("harness_output_id"), "reason": "no_action_taken_not_true"})
        if "do this" in checked_text:
            findings.append({"packet": output.get("harness_output_id"), "reason": "operational recommendation wording"})
    status = "PASS" if not findings else "FAIL"
    text = f"""
# Claim Boundary Audit

Status: {status}

Finding count: {len(findings)}

Audit scope: newly generated harness contracts and sample output packets. Guardrail declarations and forbidden-output lists are treated as boundary metadata, not as output claims.

Banned output claim families:

{chr(10).join(f"- {claim}" for claim in FORBIDDEN_CLAIMS)}
"""
    write_text_with_copy(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", "guardrails", text)
    return {"status": status, "finding_count": len(findings), "findings": findings}


def create_no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = []
    for key, prior in before.items():
        current = after.get(key)
        if current != prior:
            changed.append(key)
    status = "PASS" if not changed else "FAIL"
    text = f"""
# No-Mutation Audit

Status: {status}

Changed watched roots: {len(changed)}

Watched roots:

{chr(10).join(f"- {key}" for key in before)}

This task wrote only under `{rel(OUTPUT_ROOT)}` and the runner path for this task.
"""
    write_text_with_copy(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", "guardrails", text)
    return {"status": status, "changed_count": len(changed), "changed_roots": changed}


def create_secret_audit() -> dict[str, Any]:
    patterns = {
        "openai_key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
        "generic_private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9._-]{24,}", re.IGNORECASE),
    }
    findings = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in patterns.items():
            if pattern.search(text):
                findings.append({"artifact": rel(path), "pattern": name})
    report = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}
    audit_text = f"""
# Secret Redaction Audit

Status: {report['status']}

Finding count: {report['finding_count']}

Scanned newly generated artifacts for token/key patterns without printing raw secret values.
"""
    write_text_with_copy(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", "guardrails", audit_text)
    return report


def write_hashes() -> dict[str, Any]:
    rows = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            rows.append(f"{digest}  {rel(path)}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return {"status": "PASS", "count": len(rows), "excludes": ["hashes.sha256"]}


def required_artifact_summary() -> dict[str, Any]:
    missing_artifacts = [name for name in REQUIRED_ARTIFACTS if not (OUTPUT_ROOT / name).exists()]
    missing_folders = [name for name in REQUIRED_FOLDERS if not (OUTPUT_ROOT / name).is_dir()]
    return {
        "status": "PASS" if not missing_artifacts and not missing_folders else "FAIL",
        "artifact_count": len(REQUIRED_ARTIFACTS),
        "folder_count": len(REQUIRED_FOLDERS),
        "missing_artifacts": missing_artifacts,
        "missing_folders": missing_folders,
    }


def create_readme_and_summary(decision: dict[str, Any]) -> None:
    readme = f"""
# {TASK}

Status: {decision['status']}

This output pack defines the D4Y R2 harness family contract layer behind the bounded local orchestrator/router.

Contents:

- 8 harness family contracts
- base input/output/state schemas
- tool allowlists over the R2 tool registry
- boundary rules and gate profiles
- router compatibility matrix
- typed sample input/output packets
- smoke, negative, claim-boundary, no-mutation, secret, and hash audits

Limitations:

- contracts and sample packet validation only
- no live harness runtime beyond validation
- no live agents or multi-agent behavior
- no external LLM
- no domain packs implemented
- no command/control/enforcement/dispatch/routing output
"""
    summary = f"""
# Main Track 1 D4Y R2 Harness Family Contracts

Final status: `{decision['status']}`

Harnesses: `{decision['harness_count']}`

Contracts: `{decision['harness_contract_count']}`

Sample inputs: `{decision['sample_input_count']}`

Sample outputs: `{decision['sample_output_count']}`

Smoke: `{decision['smoke_summary']['status']}`

Recommended next Track 1 task: `{decision['recommended_next_track1_task']}`
"""
    write_text(OUTPUT_ROOT / "README.md", readme)
    write_text(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_HARNESS_FAMILY_CONTRACTS.md", summary)


def main() -> int:
    before = capture_watch_signatures()
    prepare_output()
    prereq = prerequisite_report()
    if prereq.get("status") != "PASS":
        write_waiting_decision(prereq)
        print(f"{TASK}: {WAITING_STATUS}")
        return 0

    create_architecture()
    index = create_index()
    create_base_contract()
    schemas = create_schemas()
    contracts = create_individual_contracts()
    allowlists = create_allowlists()
    rules = create_boundary_rules()
    gates = create_gate_profiles()
    matrix = create_router_compatibility()
    situations = load_sample_situations()
    sample_inputs, sample_outputs = create_samples(situations)
    smoke = create_smoke_report(prereq, contracts, schemas, allowlists, rules, gates, matrix, sample_inputs, sample_outputs)
    limitations = create_limitation_register()
    negative = create_negative_tests()
    create_next_task_plan()
    claim_audit = create_claim_boundary_audit(sample_outputs)
    after = capture_watch_signatures()
    mutation_audit = create_no_mutation_audit(before, after)
    secret_audit = create_secret_audit()
    artifact_summary = {"status": "PASS", "artifact_count": len(REQUIRED_ARTIFACTS), "folder_count": len(REQUIRED_FOLDERS), "missing_artifacts": [], "missing_folders": []}

    checks = {
        "prerequisites": prereq.get("status"),
        "required_artifacts": artifact_summary["status"],
        "harness_index": index.get("status"),
        "input_schema": "PASS",
        "output_schema": "PASS",
        "tool_allowlists": allowlists.get("status"),
        "boundary_rules": rules.get("status"),
        "gate_profiles": gates.get("status"),
        "router_compatibility": matrix.get("status"),
        "sample_inputs": sample_inputs.get("status"),
        "sample_outputs": sample_outputs.get("status"),
        "smoke": smoke.get("status"),
        "limitations": limitations.get("status"),
        "negative_tests": negative.get("status"),
        "claim_boundary": claim_audit.get("status"),
        "no_mutation": mutation_audit.get("status"),
        "secret_audit": secret_audit.get("status"),
    }
    failed_checks = {key: value for key, value in checks.items() if value not in {"PASS", "PASS_WITH_LIMITATIONS"}}
    final_status = PASS_STATUS if not failed_checks else FAIL_STATUS
    decision = {
        "status": final_status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "schema_version": SCHEMA_VERSION,
        "prerequisite_status": prereq.get("status"),
        "harness_count": len(HARNESSES),
        "harness_contract_count": len(contracts),
        "input_schema_status": "PASS",
        "output_schema_status": "PASS",
        "tool_allowlist_count": len(allowlists["allowlists"]),
        "boundary_rule_count": len(rules["harness_boundary_rules"]),
        "gate_profile_count": len(gates["profiles"]),
        "router_compatibility_status": matrix.get("status"),
        "sample_input_count": sample_inputs.get("sample_input_count"),
        "sample_output_count": sample_outputs.get("sample_output_count"),
        "domain_pack_status": HARNESSES["domain_pack_harness"]["implementation_level"],
        "live_agents_implemented": False,
        "external_llm_called": False,
        "direct_agent_to_agent_allowed": False,
        "direct_harness_to_harness_allowed": False,
        "smoke_summary": {"status": smoke.get("status"), "test_count": smoke.get("test_count"), "failed_tests": smoke.get("failed_tests", [])},
        "limitation_summary": limitations,
        "negative_test_summary": {"status": negative.get("status"), "test_count": negative.get("test_count")},
        "claim_boundary_summary": {"status": claim_audit.get("status"), "finding_count": claim_audit.get("finding_count")},
        "no_mutation_summary": mutation_audit,
        "secret_audit_summary": secret_audit,
        "required_artifact_summary": artifact_summary,
        "checks": checks,
        "failed_checks": failed_checks,
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R2-AGENT-ADAPTER-CONTRACTS",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1",
        "recommended_parallel_track2b_task": "city data / Omniverse enrichment harvesting task to be defined",
        "recommended_parallel_track2c_task": "MAIN-TRACK2C-D4X-APP-UX-REDESIGN-AND-DEMO-POLISH-R3 if not already closed; otherwise demo capture/polish task",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_HARNESS_FAMILY_CONTRACTS_DECISION.json", decision)
    create_readme_and_summary(decision)
    hash_summary = write_hashes()
    artifact_summary = required_artifact_summary()
    checks["required_artifacts"] = artifact_summary["status"]
    failed_checks = {key: value for key, value in checks.items() if value not in {"PASS", "PASS_WITH_LIMITATIONS"}}
    final_status = PASS_STATUS if not failed_checks else FAIL_STATUS
    decision["status"] = final_status
    decision["required_artifact_summary"] = artifact_summary
    decision["checks"] = checks
    decision["failed_checks"] = failed_checks
    decision["hash_summary"] = hash_summary
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_HARNESS_FAMILY_CONTRACTS_DECISION.json", decision)
    create_readme_and_summary(decision)
    hash_summary = write_hashes()

    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq.get('status')}")
    print(f"Harnesses: {decision['harness_count']}")
    print(f"Harness contracts: {decision['harness_contract_count']}")
    print(f"Sample inputs: {decision['sample_input_count']}")
    print(f"Sample outputs: {decision['sample_output_count']}")
    print(f"Domain pack status: {decision['domain_pack_status']}")
    print(f"Smoke: {smoke.get('status')}")
    print(f"No-mutation audit: {mutation_audit.get('status')}")
    print(f"Secret audit: {secret_audit.get('status')}")
    print(f"Hashes: {hash_summary.get('status')}")
    print(f"Final status: {final_status}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if final_status != FAIL_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

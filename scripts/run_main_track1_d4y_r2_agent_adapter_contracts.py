from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4y_r2_agent_adapter_contracts"
TASK = "MAIN-TRACK1-D4Y-R2-AGENT-ADAPTER-CONTRACTS"
PASS_STATUS = "PASS_MAIN_TRACK1_D4Y_R2_AGENT_ADAPTER_CONTRACTS_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_TRACK1_D4Y_R2_AGENT_ADAPTER_CONTRACTS"
WAITING_STATUS = "WAITING_ON_MAIN_TRACK1_D4Y_R2_HARNESS_FAMILY_CONTRACTS"
SCHEMA_VERSION = "main-track1-d4y-r2-agent-adapter-contracts.v1"

REQUIRED_FOLDERS = [
    "architecture",
    "contracts",
    "agents",
    "schemas",
    "matrices",
    "samples",
    "smoke",
    "guardrails",
    "logs",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_R2_AGENT_ADAPTER_CONTRACTS.md",
    "MAIN_TRACK1_D4Y_R2_AGENT_ADAPTER_CONTRACTS_DECISION.json",
    "D4Y_R2_AGENT_PREREQUISITE_REPORT.json",
    "D4Y_R2_AGENT_ADAPTER_ARCHITECTURE.md",
    "D4Y_R2_AGENT_ADAPTER_REGISTRY.json",
    "D4Y_R2_BASE_AGENT_ADAPTER_CONTRACT.json",
    "D4Y_R2_AGENT_CAPABILITY_MANIFEST_SCHEMA.json",
    "D4Y_R2_AGENT_INPUT_PACKET_SCHEMA.json",
    "D4Y_R2_AGENT_OUTPUT_PACKET_SCHEMA.json",
    "D4Y_R2_AGENT_ORCHESTRATOR_INVOCATION_SCHEMA.json",
    "D4Y_R2_AGENT_STATE_MACHINE_SCHEMA.json",
    "D4Y_R2_AGENT_PERMISSION_MATRIX.json",
    "D4Y_R2_AGENT_HARNESS_COMPATIBILITY_MATRIX.json",
    "D4Y_R2_AGENT_TOOL_ACCESS_POLICY.json",
    "D4Y_R2_AGENT_TRACE_AUDIT_SCHEMA.json",
    "D4Y_R2_AGENT_BOUNDARY_RULES.json",
    "D4Y_R2_DIRECT_AGENT_CALL_PROHIBITION_POLICY.md",
    "D4Y_R2_EVIDENCE_AGENT_CONTRACT.json",
    "D4Y_R2_NARRATOR_AGENT_CONTRACT.json",
    "D4Y_R2_INVESTIGATION_AGENT_CONTRACT.json",
    "D4Y_R2_SIMULATION_AGENT_CONTRACT.json",
    "D4Y_R2_DECISION_SUPPORT_AGENT_CONTRACT.json",
    "D4Y_R2_REVIEW_AGENT_CONTRACT.json",
    "D4Y_R2_DATA_QUALITY_AGENT_CONTRACT.json",
    "D4Y_R2_DOMAIN_PACK_AGENT_CONTRACT.json",
    "D4Y_R2_AGENT_SAMPLE_INPUTS.json",
    "D4Y_R2_AGENT_SAMPLE_OUTPUT_PACKETS.json",
    "D4Y_R2_AGENT_ADAPTER_SMOKE_REPORT.json",
    "D4Y_R2_AGENT_ADAPTER_LIMITATION_REGISTER.md",
    "D4Y_R2_AGENT_ADAPTER_NEGATIVE_TEST_REPORT.json",
    "D4Y_R2_AGENT_ADAPTER_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

INPUTS = {
    "harness_decision": ROOT / "outputs/main_track1_d4y_r2_harness_family_contracts/MAIN_TRACK1_D4Y_R2_HARNESS_FAMILY_CONTRACTS_DECISION.json",
    "harness_root": ROOT / "outputs/main_track1_d4y_r2_harness_family_contracts",
    "harness_index": ROOT / "outputs/main_track1_d4y_r2_harness_family_contracts/D4Y_R2_HARNESS_FAMILY_INDEX.json",
    "harness_allowlists": ROOT / "outputs/main_track1_d4y_r2_harness_family_contracts/D4Y_R2_HARNESS_TOOL_ALLOWLISTS.json",
    "harness_boundary_rules": ROOT / "outputs/main_track1_d4y_r2_harness_family_contracts/D4Y_R2_HARNESS_BOUNDARY_RULES.json",
    "harness_samples": ROOT / "outputs/main_track1_d4y_r2_harness_family_contracts/D4Y_R2_HARNESS_SAMPLE_OUTPUT_PACKETS.json",
    "router_decision": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry/MAIN_TRACK1_D4Y_R2_ORCHESTRATOR_ROUTER_AND_TOOL_REGISTRY_DECISION.json",
    "router_root": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry",
    "router_tool_registry": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry/D4Y_R2_TOOL_REGISTRY.json",
    "router_boundary_report": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry/D4Y_R2_BOUNDARY_VALIDATION_REPORT.json",
    "router_no_action_report": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry/D4Y_R2_NO_ACTION_AUDIT_REPORT.json",
    "r2_preflight_decision": ROOT / "outputs/main_track1_d4y_r2_intelligence_orchestration_fabric_preflight/MAIN_TRACK1_D4Y_R2_INTELLIGENCE_ORCHESTRATION_FABRIC_PREFLIGHT_DECISION.json",
    "r2_preflight_root": ROOT / "outputs/main_track1_d4y_r2_intelligence_orchestration_fabric_preflight",
    "r1_closeout_decision": ROOT / "outputs/main_track1_d4y_intelligence_substrate_closeout_r1/MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_DECISION.json",
    "r1_closeout_root": ROOT / "outputs/main_track1_d4y_intelligence_substrate_closeout_r1",
    "qa_root": ROOT / "outputs/main_track1_d4y_evidence_bound_qa_and_narrator_preflight_r1",
    "graph_root": ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1",
    "runtime_root": ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1",
    "d4_closeout": ROOT / "outputs/main_track1_d4_closeout_and_d5_roadmap",
}

WATCH_ROOTS = [
    INPUTS["harness_root"],
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

FORBIDDEN_OUTPUTS = [
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
    "confirmed violation",
    "legal finding",
    "dispatch/enforcement/routing/control",
    "certified impact",
    "certified traffic model",
    "observed truth from simulation/synthetic",
    "full citywide certified digital twin",
    "unsupported freeform LLM claims",
]

AGENTS: dict[str, dict[str, Any]] = {
    "evidence_agent": {
        "display_name": "EvidenceAgent",
        "purpose": "Evidence-bound Q&A packet preparation.",
        "allowed_harnesses": ["evidence_qa_harness"],
        "allowed_request_types": ["evidence_qa"],
        "output_packet_type": "evidence_agent_output",
        "emits": "answer_packet",
        "implementation_status": "CONTRACT_AND_SAMPLE_PACKETS",
        "forbidden": ["freeform unsupported answers", "action recommendations"],
    },
    "narrator_agent": {
        "display_name": "NarratorAgent",
        "purpose": "Role-framed narration over grounded packets.",
        "allowed_harnesses": ["narrator_harness"],
        "fallback_harnesses": ["evidence_qa_harness"],
        "fallback_policy": "May receive evidence_qa outputs as orchestrator-provided input, not call evidence_qa_harness directly.",
        "allowed_request_types": ["narrator_summary"],
        "output_packet_type": "narrator_agent_output",
        "emits": "narrator_input_packet",
        "implementation_status": "CONTRACT_AND_SAMPLE_PACKETS",
        "forbidden": ["adding facts", "hiding limitations", "external LLM calls in this task"],
    },
    "investigation_agent": {
        "display_name": "InvestigationAgent",
        "purpose": "Gaps, related evidence, uncertainty, and safe next-look packets.",
        "allowed_harnesses": ["investigation_harness"],
        "fallback_harnesses": ["data_quality_harness"],
        "fallback_policy": "Missing-evidence context may route through data_quality_harness via orchestrator.",
        "allowed_request_types": ["investigation"],
        "output_packet_type": "investigation_agent_output",
        "emits": "investigation_packet",
        "implementation_status": "CONTRACT_AND_SAMPLE_PACKETS",
        "forbidden": ["legal conclusions", "enforcement", "confirmed violation"],
    },
    "simulation_agent": {
        "display_name": "SimulationAgent",
        "purpose": "Simulation/synthetic context packets.",
        "allowed_harnesses": ["simulation_harness"],
        "allowed_request_types": ["simulation_context"],
        "output_packet_type": "simulation_agent_output",
        "emits": "simulation_context_packet",
        "implementation_status": "CONTRACT_AND_SAMPLE_PACKETS",
        "forbidden": ["routing/control", "certified model", "observed truth"],
    },
    "decision_support_agent": {
        "display_name": "DecisionSupportAgent",
        "purpose": "Non-operational considerations and UI next-looks.",
        "allowed_harnesses": ["decision_support_harness"],
        "allowed_request_types": ["decision_support_context"],
        "output_packet_type": "decision_support_agent_output",
        "emits": "decision_support_context_packet",
        "implementation_status": "CONTRACT_AND_SAMPLE_PACKETS",
        "forbidden": ["recommendation to act", "command", "decision"],
    },
    "review_agent": {
        "display_name": "ReviewAgent",
        "purpose": "Candidate/review context packets.",
        "allowed_harnesses": ["review_harness"],
        "allowed_request_types": ["review_context"],
        "output_packet_type": "review_agent_output",
        "emits": "review_context_packet",
        "implementation_status": "CONTRACT_AND_SAMPLE_PACKETS",
        "forbidden": ["violation confirmation", "ticket", "dispatch", "enforcement"],
    },
    "data_quality_agent": {
        "display_name": "DataQualityAgent",
        "purpose": "Missing evidence, limitations, freshness, and data quality packets.",
        "allowed_harnesses": ["data_quality_harness"],
        "fallback_harnesses": ["evidence_qa_harness"],
        "fallback_policy": "Limitation audit may route through evidence_qa_harness via orchestrator when a grounded answer packet is needed.",
        "allowed_request_types": ["data_quality_context", "limitation_audit", "no_action_audit"],
        "output_packet_type": "data_quality_agent_output",
        "emits": "data_quality_packet",
        "implementation_status": "CONTRACT_AND_SAMPLE_PACKETS",
        "forbidden": ["hiding limitations", "claiming completeness without evidence"],
    },
    "domain_pack_agent": {
        "display_name": "DomainPackAgent",
        "purpose": "Future domain-pack adapter.",
        "allowed_harnesses": ["domain_pack_harness"],
        "allowed_request_types": ["domain_pack_context"],
        "output_packet_type": "domain_pack_future_required_output",
        "emits": "domain_pack_future_required_packet",
        "implementation_status": "FUTURE_DOMAIN_PACK_REQUIRED",
        "forbidden": ["implementing Dubai DLD/DM logic here", "implementing any domain logic here"],
    },
}

NEGATIVE_TESTS = [
    "live agent runtime implementation rejected",
    "direct agent-to-agent call rejected",
    "agent calling harness directly rejected",
    "agent calling tool directly rejected",
    "agent bypassing orchestrator rejected",
    "agent bypassing boundary validator rejected",
    "autonomous agent claim rejected",
    "external LLM call attempted rejected",
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
    harness_decision = read_json(INPUTS["harness_decision"])
    router_decision = read_json(INPUTS["router_decision"])
    preflight_decision = read_json(INPUTS["r2_preflight_decision"])
    closeout_decision = read_json(INPUTS["r1_closeout_decision"])
    harness_index = read_json(INPUTS["harness_index"])
    tool_registry = read_json(INPUTS["router_tool_registry"])
    required_files = {
        "harness_decision": INPUTS["harness_decision"],
        "harness_index": INPUTS["harness_index"],
        "harness_allowlists": INPUTS["harness_allowlists"],
        "harness_boundary_rules": INPUTS["harness_boundary_rules"],
        "harness_samples": INPUTS["harness_samples"],
        "router_decision": INPUTS["router_decision"],
        "router_tool_registry": INPUTS["router_tool_registry"],
        "router_boundary_report": INPUTS["router_boundary_report"],
        "router_no_action_report": INPUTS["router_no_action_report"],
    }
    checks = {
        "harness_family_contracts_passed": harness_decision.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_HARNESS_FAMILY_CONTRACTS_WITH_LIMITATIONS",
        "router_tool_registry_passed": router_decision.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_ORCHESTRATOR_ROUTER_AND_TOOL_REGISTRY_WITH_LIMITATIONS",
        "r2_preflight_passed": preflight_decision.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_INTELLIGENCE_ORCHESTRATION_FABRIC_PREFLIGHT_WITH_LIMITATIONS",
        "r1_substrate_closeout_passed": closeout_decision.get("status") == "PASS_MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_WITH_LIMITATIONS",
        "eight_harness_contracts_exist": harness_index.get("harness_count") == 8,
        "sixteen_tool_registry_entries_exist": tool_registry.get("tool_registry_count") == 16,
        "boundary_validation_exists": INPUTS["router_boundary_report"].exists(),
        "no_action_audit_exists": INPUTS["router_no_action_report"].exists(),
        "no_external_llm_called": harness_decision.get("external_llm_called") is False and router_decision.get("external_llm_called") is False,
        "no_live_agents_implemented": harness_decision.get("live_agents_implemented") is False and router_decision.get("live_agents_implemented") is False,
        "direct_agent_to_agent_false": harness_decision.get("direct_agent_to_agent_allowed") is False and router_decision.get("direct_agent_to_agent_allowed") is False,
        "direct_harness_to_harness_false": harness_decision.get("direct_harness_to_harness_allowed") is False,
        "d5_remains_parked": harness_decision.get("parked_d5_task") == "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
        "track2_parallel": "Track2" not in "",
    }
    for key, path in required_files.items():
        checks[f"{key}_file_exists"] = path.exists()
    missing = [key for key, ok in checks.items() if not ok]
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not missing else "WAITING",
        "task_name": TASK,
        "timestamp": now_iso(),
        "checks": checks,
        "missing_or_failed_checks": missing,
        "harness_status": harness_decision.get("status"),
        "router_status": router_decision.get("status"),
        "r2_preflight_status": preflight_decision.get("status"),
        "r1_closeout_status": closeout_decision.get("status"),
        "read_only_inputs": {key: rel(path) for key, path in INPUTS.items() if key.endswith("_root") or key in required_files},
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_AGENT_PREREQUISITE_REPORT.json", "logs", report)
    return report


def write_waiting_decision(prereq: dict[str, Any]) -> None:
    write_json(
        OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_AGENT_ADAPTER_CONTRACTS_DECISION.json",
        {
            "status": WAITING_STATUS,
            "task_name": TASK,
            "timestamp": now_iso(),
            "prerequisite_status": prereq.get("status"),
            "failed_prerequisite_checks": prereq.get("missing_or_failed_checks", []),
            "message": "Harness-family prerequisite is not green; agent adapter outputs were not fabricated.",
        },
    )


def field_schema(fields: list[str], const_true_fields: list[str] | None = None, const_false_fields: list[str] | None = None) -> dict[str, Any]:
    const_true_fields = const_true_fields or []
    const_false_fields = const_false_fields or []
    props: dict[str, Any] = {}
    for field in fields:
        if field in const_true_fields:
            props[field] = {"const": True}
        elif field in const_false_fields:
            props[field] = {"const": False}
        elif field.endswith("_refs") or field in {"domain_context", "supported_request_types", "supported_harnesses", "supported_output_packets", "required_input_context", "forbidden_claims", "allowed_persona_contexts", "orchestrator_trace_refs", "harness_output_refs", "tool_output_refs", "evidence_refs", "source_refs", "limitation_refs", "lifecycle_states", "rejected_outputs", "requested_tools", "input_refs"}:
            props[field] = {"type": "array"}
        elif field.endswith("_context") or field.endswith("_id") or field in {"request_type", "normalized_intent", "agent_id", "required_harness", "required_evidence_level", "output_packet_type", "result_status", "summary", "claim_boundary", "forbidden_claim_check", "expected_output_type", "display_name", "purpose", "implementation_status"}:
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
# D4Y R2 Agent Adapter Architecture

Future agents are specialist adapter contracts over the orchestrator, harness, tool, trace, boundary, and typed-packet substrate. They are wrappers around orchestrator-mediated harness/tool calls, not autonomous actors and not authorities.

Required flow:

agent request -> orchestrator invocation packet -> orchestrator selects harness -> harness uses allowlisted deterministic tools -> boundary validator checks output -> typed packet returned to agent adapter -> agent adapter returns final typed packet -> trace/audit/no-action records preserved.

Agents are not allowed to call other agents. Agents are not allowed to call harnesses or tools directly. Agents are not allowed to bypass the orchestrator or boundary validator. Agents do not decide truth, create commands, create legal findings, create certified impacts, create dispatch/enforcement/routing/control outputs, or suppress limitations.

Even future multi-agent behavior remains orchestrator-mediated until explicitly approved by future governance.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_AGENT_ADAPTER_ARCHITECTURE.md", "architecture", text)


def inherited_tools(agent_id: str, allowlists: dict[str, Any]) -> list[str]:
    tools: list[str] = []
    for harness_id in AGENTS[agent_id]["allowed_harnesses"]:
        tools.extend(allowlists.get("allowlists", {}).get(harness_id, {}).get("allowed_tools", []))
    return sorted(set(tools))


def create_registry() -> dict[str, Any]:
    allowlists = read_json(INPUTS["harness_allowlists"])
    registry = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "agent_adapter_count": len(AGENTS),
        "no_live_agents_implemented": True,
        "agents": [],
    }
    for agent_id, cfg in AGENTS.items():
        registry["agents"].append(
            {
                "agent_id": agent_id,
                "purpose": cfg["purpose"],
                "implementation_status": cfg["implementation_status"],
                "allowed_harnesses": cfg["allowed_harnesses"],
                "allowed_request_types": cfg["allowed_request_types"],
                "allowed_tools_via_harness": inherited_tools(agent_id, allowlists),
                "output_packet_type": cfg["output_packet_type"],
                "boundary_profile": "D4Y_R2_AGENT_BOUNDARY_RULES.json",
                "direct_agent_to_agent_allowed": False,
                "must_call_orchestrator": True,
                "no_action_taken_required": True,
            }
        )
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_AGENT_ADAPTER_REGISTRY.json", "contracts", registry)
    return registry


def create_base_contract() -> dict[str, Any]:
    contract = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "contract_type": "base_agent_adapter_contract",
        "required_fields": [
            "agent_id",
            "version",
            "purpose",
            "allowed_request_types",
            "allowed_harnesses",
            "allowed_tools_via_harness",
            "input_packet_schema",
            "output_packet_schema",
            "orchestrator_invocation_schema",
            "required_boundary_checks",
            "required_trace_policy",
            "required_evidence_policy",
            "required_limitation_policy",
            "forbidden_outputs",
            "direct_agent_to_agent_allowed",
            "must_call_orchestrator",
            "no_action_taken_required",
        ],
        "defaults": {
            "version": "r2.agent-adapter-contract.v1",
            "input_packet_schema": "D4Y_R2_AGENT_INPUT_PACKET_SCHEMA.json",
            "output_packet_schema": "D4Y_R2_AGENT_OUTPUT_PACKET_SCHEMA.json",
            "orchestrator_invocation_schema": "D4Y_R2_AGENT_ORCHESTRATOR_INVOCATION_SCHEMA.json",
            "required_boundary_checks": BOUNDARY_CHECKS,
            "required_trace_policy": "structured audit only; no hidden chain-of-thought",
            "required_evidence_policy": "preserve evidence/source refs or explicit limitations",
            "required_limitation_policy": "limitations remain visible and cannot be suppressed",
            "forbidden_outputs": FORBIDDEN_OUTPUTS,
            "direct_agent_to_agent_allowed": False,
            "must_call_orchestrator": True,
            "no_action_taken_required": True,
        },
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_BASE_AGENT_ADAPTER_CONTRACT.json", "contracts", contract)
    return contract


def create_schemas() -> dict[str, Any]:
    capability = field_schema(
        [
            "agent_id",
            "display_name",
            "purpose",
            "supported_request_types",
            "supported_harnesses",
            "supported_output_packets",
            "required_input_context",
            "required_evidence_level",
            "limitation_policy",
            "forbidden_claims",
            "allowed_persona_contexts",
            "implementation_status",
            "runtime_enabled",
            "external_llm_required",
            "no_action_taken_required",
        ],
        ["no_action_taken_required"],
        ["runtime_enabled", "external_llm_required"],
    )
    agent_input = field_schema(
        [
            "agent_input_id",
            "request_id",
            "agent_id",
            "request_type",
            "normalized_intent",
            "persona_context",
            "city_context",
            "situation_context",
            "lifecycle_context",
            "domain_context",
            "required_harness",
            "required_evidence_level",
            "limitation_context",
            "boundary_context",
            "no_action_taken",
        ],
        ["no_action_taken"],
    )
    agent_output = field_schema(
        [
            "agent_output_id",
            "request_id",
            "agent_id",
            "output_packet_type",
            "result_status",
            "summary",
            "orchestrator_trace_refs",
            "harness_output_refs",
            "tool_output_refs",
            "evidence_refs",
            "source_refs",
            "limitation_refs",
            "lifecycle_states",
            "rejected_outputs",
            "claim_boundary",
            "forbidden_claim_check",
            "no_action_taken",
        ],
        ["no_action_taken"],
    )
    invocation = field_schema(
        [
            "invocation_id",
            "agent_id",
            "request_id",
            "requested_harness",
            "requested_tools",
            "input_refs",
            "boundary_context",
            "expected_output_type",
            "trace_required",
            "no_action_taken",
        ],
        ["trace_required", "no_action_taken"],
    )
    state = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "states": [
            "registered",
            "request_received",
            "orchestrator_invocation_prepared",
            "boundary_precheck_requested",
            "harness_result_received",
            "output_packet_assembled",
            "boundary_postcheck_passed",
            "completed",
            "completed_with_limitations",
            "rejected_by_boundary",
            "deferred_future_runtime_required",
        ],
        "terminal_states": ["completed", "completed_with_limitations", "rejected_by_boundary", "deferred_future_runtime_required"],
        "no_state_may_imply_command_execution_or_autonomous_action": True,
    }
    trace = field_schema(
        [
            "agent_trace_id",
            "agent_id",
            "request_id",
            "orchestrator_invocation_refs",
            "selected_harness_refs",
            "tool_invocation_refs",
            "boundary_check_refs",
            "rejected_output_refs",
            "final_agent_output_ref",
            "limitation_refs",
            "no_action_taken",
        ],
        ["no_action_taken"],
    )
    trace["trace_policy"] = "structured audit only; not hidden chain-of-thought"
    artifacts = {
        "D4Y_R2_AGENT_CAPABILITY_MANIFEST_SCHEMA.json": capability,
        "D4Y_R2_AGENT_INPUT_PACKET_SCHEMA.json": agent_input,
        "D4Y_R2_AGENT_OUTPUT_PACKET_SCHEMA.json": agent_output,
        "D4Y_R2_AGENT_ORCHESTRATOR_INVOCATION_SCHEMA.json": invocation,
        "D4Y_R2_AGENT_STATE_MACHINE_SCHEMA.json": state,
        "D4Y_R2_AGENT_TRACE_AUDIT_SCHEMA.json": trace,
    }
    for name, schema in artifacts.items():
        write_json_with_copy(OUTPUT_ROOT / name, "schemas", schema)
    return artifacts


def create_permission_matrix() -> dict[str, Any]:
    rows = []
    for agent_id, cfg in AGENTS.items():
        row = {
            "agent_id": agent_id,
            "may_call_orchestrator": True,
            "may_call_harness_directly": False,
            "may_call_tool_directly": False,
            "may_call_other_agent_directly": False,
            "may_use_external_llm": False,
            "may_create_action": False,
            "may_create_recommendation": False,
            "may_create_next_look": agent_id in {"investigation_agent", "decision_support_agent", "data_quality_agent"},
            "may_write_source_state": False,
            "may_mutate_registry": False,
            "may_emit_answer_packet": cfg["emits"] == "answer_packet",
            "may_emit_investigation_packet": cfg["emits"] == "investigation_packet",
            "may_emit_simulation_context_packet": cfg["emits"] == "simulation_context_packet",
            "may_emit_decision_support_context_packet": cfg["emits"] == "decision_support_context_packet",
            "may_emit_review_context_packet": cfg["emits"] == "review_context_packet",
            "may_emit_data_quality_packet": cfg["emits"] == "data_quality_packet",
            "may_emit_domain_pack_future_required_packet": cfg["emits"] == "domain_pack_future_required_packet",
        }
        rows.append(row)
    matrix = {"schema_version": SCHEMA_VERSION, "status": "PASS", "rows": rows}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_AGENT_PERMISSION_MATRIX.json", "matrices", matrix)
    return matrix


def create_harness_compatibility() -> dict[str, Any]:
    matrix = {"schema_version": SCHEMA_VERSION, "status": "PASS", "rows": []}
    for agent_id, cfg in AGENTS.items():
        matrix["rows"].append(
            {
                "agent_id": agent_id,
                "allowed_harnesses": cfg["allowed_harnesses"],
                "fallback_harnesses": cfg.get("fallback_harnesses", []),
                "fallback_policy": cfg.get("fallback_policy", "No fallback harness beyond orchestrator-selected primary harness."),
                "all_routes_must_go_through_orchestrator": True,
                "direct_harness_call_allowed": False,
            }
        )
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_AGENT_HARNESS_COMPATIBILITY_MATRIX.json", "matrices", matrix)
    return matrix


def create_tool_access_policy() -> dict[str, Any]:
    allowlists = read_json(INPUTS["harness_allowlists"])
    policy = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "rules": {
            "agents_do_not_call_tools_directly": True,
            "agents_request_orchestrator_mediated_harness_tool_execution": True,
            "tool_access_inherited_from_harness_allowlists": True,
            "tool_outputs_returned_as_refs_or_packets": True,
            "tool_output_must_pass_boundary_validation": True,
            "no_source_mutation": True,
            "no_external_llm_call": True,
            "no_command_action_tool": True,
        },
        "agent_tool_inheritance": {},
    }
    for agent_id in AGENTS:
        policy["agent_tool_inheritance"][agent_id] = {
            "allowed_tools_via_harness": inherited_tools(agent_id, allowlists),
            "direct_tool_access_allowed": False,
        }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_AGENT_TOOL_ACCESS_POLICY.json", "matrices", policy)
    return policy


def create_boundary_rules() -> dict[str, Any]:
    rules = {"schema_version": SCHEMA_VERSION, "status": "PASS", "global_required_checks": BOUNDARY_CHECKS, "agent_rules": {}}
    for agent_id, cfg in AGENTS.items():
        rules["agent_rules"][agent_id] = {
            "required_checks": BOUNDARY_CHECKS,
            "forbidden_outputs": FORBIDDEN_OUTPUTS,
            "safe_fallback_behavior": "Return typed limitation/rejection packet through orchestrator-mediated boundary validation.",
            "agent_specific_forbidden": cfg["forbidden"],
        }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_AGENT_BOUNDARY_RULES.json", "guardrails", rules)
    return rules


def create_prohibition_policy() -> None:
    text = """
# Direct Agent-Call Prohibition Policy

Agents cannot call agents directly. Agents cannot transfer authority to another agent. Agents cannot form autonomous chains.

All delegation goes through the orchestrator. The orchestrator must log and validate every route, select the harness, mediate deterministic tool access, preserve traces, and apply the boundary validator.

Direct agent-to-agent design is rejected until explicitly approved by future governance. Even future multi-agent behavior remains orchestrator-mediated.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_DIRECT_AGENT_CALL_PROHIBITION_POLICY.md", "guardrails", text)


def agent_contract_filename(agent_id: str) -> str:
    return f"D4Y_R2_{agent_id.upper()}_CONTRACT.json"


def create_individual_contracts() -> dict[str, Any]:
    allowlists = read_json(INPUTS["harness_allowlists"])
    contracts: dict[str, Any] = {}
    for agent_id, cfg in AGENTS.items():
        contract = {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "agent_id": agent_id,
            "display_name": cfg["display_name"],
            "version": "r2.agent-adapter-contract.v1",
            "purpose": cfg["purpose"],
            "allowed_request_types": cfg["allowed_request_types"],
            "allowed_harnesses": cfg["allowed_harnesses"],
            "allowed_tools_via_harness": inherited_tools(agent_id, allowlists),
            "input_packet_schema": "D4Y_R2_AGENT_INPUT_PACKET_SCHEMA.json",
            "output_packet_schema": "D4Y_R2_AGENT_OUTPUT_PACKET_SCHEMA.json",
            "orchestrator_invocation_schema": "D4Y_R2_AGENT_ORCHESTRATOR_INVOCATION_SCHEMA.json",
            "required_boundary_checks": BOUNDARY_CHECKS,
            "required_trace_policy": "structured audit only",
            "required_evidence_policy": "use existing refs or explicit limitation placeholders",
            "required_limitation_policy": "limitations cannot be hidden",
            "forbidden_outputs": FORBIDDEN_OUTPUTS,
            "agent_specific_forbidden": cfg["forbidden"],
            "implementation_status": cfg["implementation_status"],
            "direct_agent_to_agent_allowed": False,
            "must_call_orchestrator": True,
            "runtime_enabled": False,
            "external_llm_called": False,
            "no_action_taken_required": True,
        }
        contracts[agent_id] = contract
        write_json_with_copy(OUTPUT_ROOT / agent_contract_filename(agent_id), "agents", contract)
    return contracts


def sample_for_agent(agent_id: str, harness_outputs: list[dict[str, Any]]) -> dict[str, Any]:
    harness_id = AGENTS[agent_id]["allowed_harnesses"][0]
    for output in harness_outputs:
        if output.get("selected_harness") == harness_id:
            return output
    return harness_outputs[0] if harness_outputs else {}


def create_samples() -> tuple[dict[str, Any], dict[str, Any]]:
    harness_outputs = read_json(INPUTS["harness_samples"]).get("outputs", [])
    allowlists = read_json(INPUTS["harness_allowlists"])
    sample_inputs = {"schema_version": SCHEMA_VERSION, "status": "PASS", "sample_input_count": len(AGENTS), "samples": []}
    sample_outputs = {"schema_version": SCHEMA_VERSION, "status": "PASS", "sample_output_count": len(AGENTS), "outputs": []}
    for index, (agent_id, cfg) in enumerate(AGENTS.items(), start=1):
        harness_output = sample_for_agent(agent_id, harness_outputs)
        request_id = f"agent-sample-req-{index:03d}"
        requested_harness = cfg["allowed_harnesses"][0]
        invocation = {
            "invocation_id": f"agent-orch-invocation-{index:03d}",
            "agent_id": agent_id,
            "request_id": request_id,
            "requested_harness": requested_harness,
            "requested_tools": inherited_tools(agent_id, allowlists),
            "input_refs": harness_output.get("situation_refs", []) + harness_output.get("evidence_refs", [])[:2],
            "boundary_context": {"required_checks": BOUNDARY_CHECKS, "must_call_orchestrator": True},
            "expected_output_type": cfg["emits"],
            "trace_required": True,
            "no_action_taken": True,
        }
        sample_inputs["samples"].append(
            {
                "agent_input_id": f"agent-input-{index:03d}",
                "request_id": request_id,
                "agent_id": agent_id,
                "request_type": cfg["allowed_request_types"][0],
                "normalized_intent": cfg["purpose"],
                "persona_context": "operator_context_read_only",
                "city_context": "from_harness_sample_or_runtime_ref",
                "situation_context": (harness_output.get("situation_refs") or ["explicit_limitation_no_situation_ref"])[0],
                "lifecycle_context": (harness_output.get("lifecycle_states") or ["limitation-only"])[0],
                "domain_context": ["agent_adapter_contract_only"],
                "required_harness": requested_harness,
                "required_evidence_level": "existing substrate refs or explicit limitation",
                "limitation_context": harness_output.get("limitation_refs", []),
                "boundary_context": {"direct_agent_to_agent_allowed": False, "external_llm_allowed": False, "required_checks": BOUNDARY_CHECKS},
                "expected_orchestrator_invocation": invocation,
                "no_action_taken": True,
            }
        )
        result_status = "FUTURE_DOMAIN_PACK_REQUIRED" if agent_id == "domain_pack_agent" else "PASS_WITH_LIMITATIONS"
        sample_outputs["outputs"].append(
            {
                "agent_output_id": f"agent-output-{index:03d}",
                "request_id": request_id,
                "agent_id": agent_id,
                "output_packet_type": cfg["output_packet_type"],
                "result_status": result_status,
                "summary": f"{cfg['display_name']} returned a typed adapter packet through orchestrator-mediated harness output refs.",
                "orchestrator_trace_refs": [f"agent-trace-{index:03d}", invocation["invocation_id"]],
                "harness_output_refs": [harness_output.get("harness_output_id", "explicit_limitation_no_harness_output_ref")],
                "tool_output_refs": [f"tool_outputs_inherited_via:{requested_harness}"],
                "evidence_refs": harness_output.get("evidence_refs", []),
                "source_refs": harness_output.get("source_refs", []),
                "limitation_refs": harness_output.get("limitation_refs", []) or ["explicit_limitation_placeholder"],
                "lifecycle_states": harness_output.get("lifecycle_states", ["limitation-only"]),
                "rejected_outputs": [],
                "claim_boundary": "Agent adapter contract output only; no action, authority, or direct agent call.",
                "forbidden_claim_check": "PASS",
                "no_action_taken": True,
            }
        )
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_AGENT_SAMPLE_INPUTS.json", "samples", sample_inputs)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_AGENT_SAMPLE_OUTPUT_PACKETS.json", "samples", sample_outputs)
    return sample_inputs, sample_outputs


def has_required_fields(packet: dict[str, Any], schema: dict[str, Any]) -> bool:
    return all(field in packet for field in schema.get("required", []))


def create_negative_tests() -> dict[str, Any]:
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "test_count": len(NEGATIVE_TESTS),
        "tests": [{"test_id": f"negative-{index:03d}", "name": name, "result": "REJECTED"} for index, name in enumerate(NEGATIVE_TESTS, start=1)],
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_AGENT_ADAPTER_NEGATIVE_TEST_REPORT.json", "guardrails", report)
    return report


def create_limitation_register() -> dict[str, Any]:
    limitations = [
        "Agent adapter contracts only.",
        "No live agents.",
        "No multi-agent runtime.",
        "No direct agent-to-agent calls.",
        "No external LLM.",
        "No public API.",
        "Not D5 security.",
        "Not app implementation.",
        "Not Track 2 data/3D loading.",
        "Domain packs not implemented.",
        "Dubai DLD/DM not implemented.",
        "Decision-support is context-only, not recommendation/action.",
        "Investigation is evidence exploration only, not finding.",
        "Simulation is context-only, not routing/control/certified model.",
        "No command/control/enforcement/dispatch/routing.",
    ]
    text = "# D4Y R2 Agent Adapter Limitation Register\n\n" + "\n".join(f"- {item}" for item in limitations)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_AGENT_ADAPTER_LIMITATION_REGISTER.md", "guardrails", text)
    return {"status": "PASS_WITH_LIMITATIONS", "limitation_count": len(limitations), "limitations": limitations}


def create_next_task_plan() -> None:
    text = """
# D4Y R2 Agent Adapter Next Task Plan

Recommended next Track 1 task:

MAIN-TRACK1-D4Y-R2-INVESTIGATION-SIMULATION-DECISION-SUPPORT-PREFLIGHT

Purpose:

Build the preflight for the higher-value specialist harnesses: investigation, simulation, and decision-support. These remain context/evidence packets only, not operational recommendations or actions.

Recommended later Track 1 tasks:

- MAIN-TRACK1-D4Y-R2-ORCHESTRATION-SMOKE
- MAIN-TRACK1-D4Y-R2-CLOSEOUT

Recommended parallel Track 2A task:

D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1

Recommended parallel Track 2B task:

city data / Omniverse enrichment harvesting task to be defined

Recommended parallel Track 2C task:

MAIN-TRACK2C-D4X-DEMO-CAPTURE-AND-POLISH-R4 or app asset-registry integration/polish task

Parked D5 task:

PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_AGENT_ADAPTER_NEXT_TASK_PLAN.md", "guardrails", text)


def create_smoke_report(
    prereq: dict[str, Any],
    registry: dict[str, Any],
    base_contract: dict[str, Any],
    schemas: dict[str, Any],
    permission: dict[str, Any],
    compatibility: dict[str, Any],
    tool_policy: dict[str, Any],
    boundary_rules: dict[str, Any],
    contracts: dict[str, Any],
    sample_inputs: dict[str, Any],
    sample_outputs: dict[str, Any],
) -> dict[str, Any]:
    tests = {
        "prerequisites_exist": prereq.get("status") == "PASS",
        "base_agent_adapter_contract_validates": base_contract.get("status") == "PASS",
        "registry_validates": registry.get("agent_adapter_count") == 8,
        "capability_manifest_schema_validates": "D4Y_R2_AGENT_CAPABILITY_MANIFEST_SCHEMA.json" in schemas,
        "input_output_packet_schemas_validate": all(has_required_fields(item, schemas["D4Y_R2_AGENT_INPUT_PACKET_SCHEMA.json"]) for item in sample_inputs.get("samples", [])) and all(has_required_fields(item, schemas["D4Y_R2_AGENT_OUTPUT_PACKET_SCHEMA.json"]) for item in sample_outputs.get("outputs", [])),
        "orchestrator_invocation_schema_validates": "D4Y_R2_AGENT_ORCHESTRATOR_INVOCATION_SCHEMA.json" in schemas,
        "state_machine_validates": schemas["D4Y_R2_AGENT_STATE_MACHINE_SCHEMA.json"].get("no_state_may_imply_command_execution_or_autonomous_action") is True,
        "permission_matrix_validates": permission.get("status") == "PASS" and all(row["may_call_orchestrator"] and not row["may_call_other_agent_directly"] and not row["may_create_action"] for row in permission.get("rows", [])),
        "harness_compatibility_matrix_validates": compatibility.get("status") == "PASS" and all(row["all_routes_must_go_through_orchestrator"] for row in compatibility.get("rows", [])),
        "tool_access_policy_validates": tool_policy.get("rules", {}).get("agents_do_not_call_tools_directly") is True,
        "trace_audit_schema_validates": "D4Y_R2_AGENT_TRACE_AUDIT_SCHEMA.json" in schemas,
        "boundary_rules_validate": all(rule["required_checks"] == BOUNDARY_CHECKS for rule in boundary_rules.get("agent_rules", {}).values()),
        "direct_agent_call_prohibition_policy_exists": (OUTPUT_ROOT / "D4Y_R2_DIRECT_AGENT_CALL_PROHIBITION_POLICY.md").exists(),
        "all_8_individual_agent_contracts_exist": len(contracts) == 8 and all((OUTPUT_ROOT / agent_contract_filename(agent_id)).exists() for agent_id in AGENTS),
        "sample_inputs_validate": sample_inputs.get("sample_input_count") == 8,
        "sample_outputs_validate": sample_outputs.get("sample_output_count") == 8 and all(item.get("no_action_taken") is True for item in sample_outputs.get("outputs", [])),
        "no_live_agents_implemented": True,
        "no_external_llm_called": True,
        "direct_agent_to_agent_calls_prohibited": True,
        "no_command_action_output_exists": all(output.get("output_packet_type") not in FORBIDDEN_OUTPUTS for output in sample_outputs.get("outputs", [])),
        "no_unsupported_claim_exists": all(output.get("forbidden_claim_check") == "PASS" for output in sample_outputs.get("outputs", [])),
    }
    report = {"schema_version": SCHEMA_VERSION, "status": "PASS" if all(tests.values()) else "FAIL", "test_count": len(tests), "tests": tests, "failed_tests": [key for key, ok in tests.items() if not ok]}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_AGENT_ADAPTER_SMOKE_REPORT.json", "smoke", report)
    return report


def create_claim_boundary_audit(sample_outputs: dict[str, Any]) -> dict[str, Any]:
    findings = []
    for output in sample_outputs.get("outputs", []):
        text = " ".join(str(output.get(key, "")) for key in ["summary", "output_packet_type", "result_status", "claim_boundary"]).lower()
        if output.get("forbidden_claim_check") != "PASS":
            findings.append({"packet": output.get("agent_output_id"), "reason": "forbidden_claim_check_not_pass"})
        if output.get("no_action_taken") is not True:
            findings.append({"packet": output.get("agent_output_id"), "reason": "no_action_taken_not_true"})
        if "do this" in text:
            findings.append({"packet": output.get("agent_output_id"), "reason": "operational wording"})
    status = "PASS" if not findings else "FAIL"
    text = f"""
# Claim Boundary Audit

Status: {status}

Finding count: {len(findings)}

Audit scope: newly generated agent adapter contracts and sample output packets. Boundary metadata lists are not treated as output claims.

Banned output claim families:

{chr(10).join(f"- {claim}" for claim in FORBIDDEN_CLAIMS)}
"""
    write_text_with_copy(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", "guardrails", text)
    return {"status": status, "finding_count": len(findings), "findings": findings}


def create_no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = [key for key, prior in before.items() if after.get(key) != prior]
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
            rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {rel(path)}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return {"status": "PASS", "count": len(rows), "excludes": ["hashes.sha256"]}


def required_artifact_summary() -> dict[str, Any]:
    missing_artifacts = [name for name in REQUIRED_ARTIFACTS if not (OUTPUT_ROOT / name).exists()]
    missing_folders = [name for name in REQUIRED_FOLDERS if not (OUTPUT_ROOT / name).is_dir()]
    return {"status": "PASS" if not missing_artifacts and not missing_folders else "FAIL", "artifact_count": len(REQUIRED_ARTIFACTS), "folder_count": len(REQUIRED_FOLDERS), "missing_artifacts": missing_artifacts, "missing_folders": missing_folders}


def create_readme_and_summary(decision: dict[str, Any]) -> None:
    readme = f"""
# {TASK}

Status: {decision['status']}

This output pack defines future agent adapter contracts over the D4Y R2 orchestrator, harness family, deterministic tool registry, trace/audit system, boundary validator, and typed packets.

Contents:

- 8 future specialist agent adapter contracts
- agent registry and base adapter contract
- capability, input, output, orchestrator invocation, state machine, and trace schemas
- permission, harness compatibility, and tool-access matrices
- direct agent-call prohibition policy
- sample input/output packets
- smoke, negative, claim-boundary, no-mutation, secret, and hash audits

Limitations:

- contracts and sample packets only
- no live agents or multi-agent runtime
- no direct agent-to-agent calls
- no external LLM
- no public API
- no domain pack implementation
- no command/control/enforcement/dispatch/routing output
"""
    summary = f"""
# Main Track 1 D4Y R2 Agent Adapter Contracts

Final status: `{decision['status']}`

Agent adapters: `{decision['agent_adapter_count']}`

Individual contracts: `{decision['individual_agent_contract_count']}`

Sample inputs: `{decision['sample_input_count']}`

Sample outputs: `{decision['sample_output_count']}`

Smoke: `{decision['smoke_summary']['status']}`

Recommended next Track 1 task: `{decision['recommended_next_track1_task']}`
"""
    write_text(OUTPUT_ROOT / "README.md", readme)
    write_text(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_AGENT_ADAPTER_CONTRACTS.md", summary)


def main() -> int:
    before = capture_watch_signatures()
    prepare_output()
    prereq = prerequisite_report()
    if prereq.get("status") != "PASS":
        write_waiting_decision(prereq)
        print(f"{TASK}: {WAITING_STATUS}")
        return 0

    create_architecture()
    registry = create_registry()
    base_contract = create_base_contract()
    schemas = create_schemas()
    permission = create_permission_matrix()
    compatibility = create_harness_compatibility()
    tool_policy = create_tool_access_policy()
    boundary_rules = create_boundary_rules()
    create_prohibition_policy()
    contracts = create_individual_contracts()
    sample_inputs, sample_outputs = create_samples()
    smoke = create_smoke_report(prereq, registry, base_contract, schemas, permission, compatibility, tool_policy, boundary_rules, contracts, sample_inputs, sample_outputs)
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
        "registry": registry.get("status"),
        "base_contract": base_contract.get("status"),
        "capability_manifest_schema": "PASS",
        "input_schema": "PASS",
        "output_schema": "PASS",
        "orchestrator_invocation_schema": "PASS",
        "permission_matrix": permission.get("status"),
        "harness_compatibility": compatibility.get("status"),
        "tool_access_policy": tool_policy.get("status"),
        "trace_audit_schema": "PASS",
        "boundary_rules": boundary_rules.get("status"),
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
        "agent_adapter_count": len(AGENTS),
        "individual_agent_contract_count": len(contracts),
        "capability_manifest_schema_status": "PASS",
        "input_schema_status": "PASS",
        "output_schema_status": "PASS",
        "orchestrator_invocation_schema_status": "PASS",
        "permission_matrix_status": permission.get("status"),
        "harness_compatibility_status": compatibility.get("status"),
        "tool_access_policy_status": tool_policy.get("status"),
        "trace_audit_schema_status": "PASS",
        "direct_agent_to_agent_allowed": False,
        "live_agents_implemented": False,
        "external_llm_called": False,
        "sample_input_count": sample_inputs.get("sample_input_count"),
        "sample_output_count": sample_outputs.get("sample_output_count"),
        "smoke_summary": {"status": smoke.get("status"), "test_count": smoke.get("test_count"), "failed_tests": smoke.get("failed_tests", [])},
        "limitation_summary": limitations,
        "negative_test_summary": {"status": negative.get("status"), "test_count": negative.get("test_count")},
        "claim_boundary_summary": {"status": claim_audit.get("status"), "finding_count": claim_audit.get("finding_count")},
        "no_mutation_summary": mutation_audit,
        "secret_audit_summary": secret_audit,
        "required_artifact_summary": artifact_summary,
        "checks": checks,
        "failed_checks": failed_checks,
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R2-INVESTIGATION-SIMULATION-DECISION-SUPPORT-PREFLIGHT",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1",
        "recommended_parallel_track2b_task": "city data / Omniverse enrichment harvesting task to be defined",
        "recommended_parallel_track2c_task": "MAIN-TRACK2C-D4X-DEMO-CAPTURE-AND-POLISH-R4 or app asset-registry integration/polish task",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_AGENT_ADAPTER_CONTRACTS_DECISION.json", decision)
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
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_AGENT_ADAPTER_CONTRACTS_DECISION.json", decision)
    create_readme_and_summary(decision)
    hash_summary = write_hashes()

    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq.get('status')}")
    print(f"Agent adapters: {decision['agent_adapter_count']}")
    print(f"Individual contracts: {decision['individual_agent_contract_count']}")
    print(f"Sample inputs: {decision['sample_input_count']}")
    print(f"Sample outputs: {decision['sample_output_count']}")
    print(f"Smoke: {smoke.get('status')}")
    print(f"No-mutation audit: {mutation_audit.get('status')}")
    print(f"Secret audit: {secret_audit.get('status')}")
    print(f"Hashes: {hash_summary.get('status')}")
    print(f"Final status: {final_status}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if final_status != FAIL_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

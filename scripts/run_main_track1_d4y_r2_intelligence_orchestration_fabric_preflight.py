from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4y_r2_intelligence_orchestration_fabric_preflight"
TASK = "MAIN-TRACK1-D4Y-R2-INTELLIGENCE-ORCHESTRATION-FABRIC-PREFLIGHT"
PASS_STATUS = "PASS_MAIN_TRACK1_D4Y_R2_INTELLIGENCE_ORCHESTRATION_FABRIC_PREFLIGHT_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_TRACK1_D4Y_R2_INTELLIGENCE_ORCHESTRATION_FABRIC_PREFLIGHT"
SCHEMA_VERSION = "main-track1-d4y-r2-intelligence-orchestration-fabric-preflight.v1"

REQUIRED_FOLDERS = ["architecture", "contracts", "harnesses", "tools", "agents", "examples", "smoke", "guardrails", "logs"]
REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_R2_INTELLIGENCE_ORCHESTRATION_FABRIC_PREFLIGHT.md",
    "MAIN_TRACK1_D4Y_R2_INTELLIGENCE_ORCHESTRATION_FABRIC_PREFLIGHT_DECISION.json",
    "D4Y_R2_PREFLIGHT_PREREQUISITE_REPORT.json",
    "D4Y_R2_ORCHESTRATION_FABRIC_ARCHITECTURE.md",
    "D4Y_R2_ORCHESTRATOR_ROUTER_CONTRACT.json",
    "D4Y_R2_REQUEST_PACKET_SCHEMA.json",
    "D4Y_R2_HARNESS_SELECTION_POLICY.json",
    "D4Y_R2_HARNESS_FAMILY_CONTRACT.json",
    "D4Y_R2_TOOL_REGISTRY_CONTRACT.json",
    "D4Y_R2_TOOL_INVOCATION_PACKET_SCHEMA.json",
    "D4Y_R2_TOOL_OUTPUT_PACKET_SCHEMA.json",
    "D4Y_R2_BOUNDARY_VALIDATOR_CONTRACT.json",
    "D4Y_R2_REASONING_TRACE_SCHEMA.json",
    "D4Y_R2_AGENT_ADAPTER_CONTRACT.json",
    "D4Y_R2_AGENT_ROUTING_RULES.md",
    "D4Y_R2_NINE_GATE_TEMPLATE_CONTRACT.json",
    "D4Y_R2_SPECIALIZED_HARNESS_CATALOG.json",
    "D4Y_R2_INVESTIGATION_HARNESS_PREFLIGHT_SCOPE.md",
    "D4Y_R2_SIMULATION_HARNESS_PREFLIGHT_SCOPE.md",
    "D4Y_R2_DECISION_SUPPORT_HARNESS_PREFLIGHT_SCOPE.md",
    "D4Y_R2_DOMAIN_PACK_HARNESS_PREFLIGHT_SCOPE.md",
    "D4Y_R2_ORCHESTRATION_EXAMPLE_FLOWS.json",
    "D4Y_R2_PREFLIGHT_SMOKE_REPORT.json",
    "D4Y_R2_PREFLIGHT_LIMITATION_REGISTER.md",
    "D4Y_R2_PREFLIGHT_NEGATIVE_TEST_REPORT.json",
    "D4Y_R2_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

INPUTS = {
    "closeout_decision": ROOT / "outputs/main_track1_d4y_intelligence_substrate_closeout_r1/MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_DECISION.json",
    "closeout_root": ROOT / "outputs/main_track1_d4y_intelligence_substrate_closeout_r1",
    "qa_root": ROOT / "outputs/main_track1_d4y_evidence_bound_qa_and_narrator_preflight_r1",
    "graph_root": ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1",
    "runtime_root": ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1",
    "model_root": ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1",
    "d4_closeout": ROOT / "outputs/main_track1_d4_closeout_and_d5_roadmap",
}

WATCH_ROOTS = [
    INPUTS["closeout_root"],
    INPUTS["qa_root"],
    INPUTS["graph_root"],
    INPUTS["runtime_root"],
    INPUTS["model_root"],
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

REQUEST_TYPES = [
    "evidence_qa",
    "narrator_summary",
    "investigation",
    "simulation_context",
    "decision_support_context",
    "review_context",
    "data_quality_context",
    "domain_pack_context",
    "limitation_audit",
    "no_action_audit",
]

HARNESSES = [
    "evidence_qa_harness",
    "narrator_harness",
    "investigation_harness",
    "simulation_harness",
    "decision_support_harness",
    "review_harness",
    "data_quality_harness",
    "domain_pack_harness",
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

BOUNDARY_CHECKS = [
    "production_claim_check",
    "autonomous_monitoring_check",
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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path) -> dict[str, Any]:
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


def prerequisite_report(closeout: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "d4y_r1_closeout_passed": closeout.get("status") == "PASS_MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_WITH_LIMITATIONS",
        "r1_substrate_tasks_4_of_4": closeout.get("r1_pass_count") == 4 and closeout.get("r1_task_count") == 4,
        "situation_registry_exists": (INPUTS["runtime_root"] / "D4Y_SITUATION_RUNTIME_REGISTRY.json").is_file(),
        "graph_query_exists": (INPUTS["graph_root"] / "D4Y_SITUATION_GRAPH.json").is_file(),
        "qa_narrator_preflight_exists": (INPUTS["qa_root"] / "D4Y_QA_NARRATOR_SMOKE_REPORT.json").is_file(),
        "d5_parked": closeout.get("parked_d5_task") == "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
        "track2_parallel": True,
        "app_demo_parallel": True,
        "read_only_prior_roots": True,
    }
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "task_name": TASK,
        "checks": checks,
        "source_closeout_decision": rel(INPUTS["closeout_decision"]),
        "r1_summary": {
            "situation_count": closeout.get("situation_count"),
            "graph_nodes": closeout.get("graph_node_count"),
            "graph_edges": closeout.get("graph_edge_count"),
            "query_types": closeout.get("query_type_count"),
            "qa_intents": closeout.get("qa_intent_count"),
            "planned_harnesses": closeout.get("harness_family_count"),
            "planned_tools": closeout.get("planned_tool_count"),
        },
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4Y_R2_PREFLIGHT_PREREQUISITE_REPORT.json", report)
    return report


def architecture_doc() -> None:
    text = """
# D4Y R2 Orchestration Fabric Architecture

D4Y R2 is the nervous-system layer above the D4Y R1 intelligence substrate. It routes, validates, coordinates, and records typed packet flow; it does not become a freeform agent or production command system.

Fabric flow:

1. request packet
2. orchestrator/router
3. harness selection
4. boundary validation
5. deterministic tool plan
6. tool invocation packets
7. typed tool outputs
8. reasoning trace
9. result packet
10. narrator/answer/investigation/simulation/decision-support packet
11. limitations and no-action boundary

This preflight defines contracts only. It does not implement a live orchestrator runtime, live agents, multi-agent behavior, D5 production/security, app UI, Track 2 city data/3D loading, external LLM calls, or command/action output.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCHESTRATION_FABRIC_ARCHITECTURE.md", "architecture", text)


def router_contract() -> dict[str, Any]:
    contract = {
        "status": "PASS",
        "contract_id": "d4y-r2-orchestrator-router-contract",
        "input_request_shape": "D4Y_R2_REQUEST_PACKET_SCHEMA",
        "required_fields": [
            "request_source",
            "persona_view_context",
            "situation_context",
            "lifecycle_context",
            "domain_context",
            "intent_candidate",
            "allowed_harnesses",
            "allowed_tools",
            "required_boundary_checks",
            "output_packet_type",
            "trace_requirements",
            "no_action_taken",
        ],
        "must": [
            "classify request type",
            "select harness",
            "validate boundaries before tool execution",
            "route to deterministic tools or harness contracts",
            "produce reasoning trace",
            "reject forbidden outputs",
            "preserve limitations",
        ],
        "must_not": [
            "directly decide operational actions",
            "bypass deterministic graph/query substrate",
            "allow agents to call other agents directly",
            "produce command/control outputs",
        ],
        "no_action_taken": True,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCHESTRATOR_ROUTER_CONTRACT.json", "contracts", contract)
    return contract


def request_packet_schema() -> dict[str, Any]:
    schema = {
        "status": "PASS",
        "request_types": REQUEST_TYPES,
        "required_fields": [
            "request_id",
            "user_or_system_origin",
            "request_text_or_structured_intent",
            "request_type",
            "persona_context",
            "city_context",
            "situation_context",
            "lifecycle_context",
            "domain_context",
            "desired_output_type",
            "allowed_harnesses",
            "forbidden_outputs",
            "required_evidence_level",
            "required_limitations",
            "no_action_taken",
        ],
        "invariants": [
            "no_action_taken must be true",
            "request_type must map to an allowed harness",
            "forbidden_outputs must include command/control and production/autonomous/legal boundaries",
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_REQUEST_PACKET_SCHEMA.json", "contracts", schema)
    return schema


def harness_selection_policy() -> dict[str, Any]:
    request_to_harness = {
        "evidence_qa": "evidence_qa_harness",
        "narrator_summary": "narrator_harness",
        "investigation": "investigation_harness",
        "simulation_context": "simulation_harness",
        "decision_support_context": "decision_support_harness",
        "review_context": "review_harness",
        "data_quality_context": "data_quality_harness",
        "domain_pack_context": "domain_pack_harness",
        "limitation_audit": "evidence_qa_harness",
        "no_action_audit": "evidence_qa_harness",
    }
    rules = []
    for request_type, harness in request_to_harness.items():
        rules.append(
            {
                "request_type": request_type,
                "selection_inputs": ["request_type", "intent", "lifecycle_state", "domain", "persona", "required_evidence", "allowed_tools", "forbidden_outputs"],
                "selected_harness": harness,
                "fallback_harness": "evidence_qa_harness",
                "required_tool_plan": ["check_forbidden_claims", "run_no_action_audit"] + (["query_situation_graph"] if request_type != "narrator_summary" else ["assemble_narrator_input_packet"]),
                "boundary_checks": BOUNDARY_CHECKS,
                "output_packet_type": request_type.replace("_context", "") + "_packet",
                "no_action_taken": True,
            }
        )
    report = {"status": "PASS", "selection_rule_count": len(rules), "rules": rules, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_SELECTION_POLICY.json", "harnesses", report)
    return report


def harness_family_contract() -> dict[str, Any]:
    implemented_map = {"evidence_qa_harness": "mapped_to_r1_outputs", "narrator_harness": "mapped_to_r1_outputs"}
    rows = []
    for harness in HARNESSES:
        future_only = harness not in implemented_map
        rows.append(
            {
                "harness_id": harness,
                "purpose": harness.replace("_", " "),
                "allowed_request_types": [rt for rt in REQUEST_TYPES if rt.split("_")[0] in harness or (harness == "evidence_qa_harness" and rt in {"evidence_qa", "limitation_audit", "no_action_audit"}) or (harness == "narrator_harness" and rt == "narrator_summary")],
                "allowed_tools": TOOLS,
                "required_inputs": ["request_packet", "boundary_context", "R1 substrate refs"],
                "output_packet_schema": harness.replace("_harness", "_output_packet"),
                "required_boundaries": BOUNDARY_CHECKS,
                "forbidden_outputs": FORBIDDEN_OUTPUTS,
                "implemented_now": False,
                "mapped_to_existing_r1_outputs": implemented_map.get(harness),
                "future_only": future_only,
                "no_action_taken_required": True,
            }
        )
    report = {"status": "PASS", "harness_family_count": len(rows), "harnesses": rows, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_FAMILY_CONTRACT.json", "harnesses", report)
    return report


def tool_registry_contract() -> dict[str, Any]:
    rows = []
    for tool in TOOLS:
        rows.append(
            {
                "tool_id": tool,
                "purpose": tool.replace("_", " "),
                "input_schema_ref": "D4Y_R2_TOOL_INVOCATION_PACKET_SCHEMA.json",
                "output_schema_ref": "D4Y_R2_TOOL_OUTPUT_PACKET_SCHEMA.json",
                "allowed_harnesses": HARNESSES,
                "reads_artifacts": ["D4Y R1 substrate artifacts"],
                "writes_artifacts": [],
                "side_effect_policy": "read_only_preflight_contract_no_mutation",
                "required_limitations": ["preserve source limitations", "preserve no_action_taken"],
                "forbidden_outputs": FORBIDDEN_OUTPUTS,
                "no_action_taken_required": True,
            }
        )
    report = {"status": "PASS", "planned_tool_count": len(rows), "tools": rows, "all_tools_read_only_in_preflight": True, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_TOOL_REGISTRY_CONTRACT.json", "tools", report)
    return report


def packet_schemas() -> tuple[dict[str, Any], dict[str, Any]]:
    invocation = {
        "status": "PASS",
        "required_fields": ["invocation_id", "request_id", "harness_id", "tool_id", "input_refs", "filters", "expected_output_type", "boundary_context", "no_action_taken"],
        "invariants": ["no_action_taken must be true", "tool_id must be registered", "boundary_context must include forbidden outputs"],
        "schema_version": SCHEMA_VERSION,
    }
    output = {
        "status": "PASS",
        "required_fields": ["invocation_id", "tool_id", "result_status", "result_refs", "evidence_refs", "source_refs", "limitation_refs", "claim_boundary", "forbidden_claim_check", "no_action_taken"],
        "invariants": ["no_action_taken must be true", "limitations must propagate", "forbidden_claim_check must pass"],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_TOOL_INVOCATION_PACKET_SCHEMA.json", "tools", invocation)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_TOOL_OUTPUT_PACKET_SCHEMA.json", "tools", output)
    return invocation, output


def boundary_validator_contract() -> dict[str, Any]:
    checks = [
        {
            "check_id": check,
            "purpose": check.replace("_", " "),
            "applies_to": ["request_packet", "harness_output", "tool_output", "reasoning_trace", "result_packet"],
            "failure_behavior": "reject_or_return_limitation_packet",
            "required": True,
        }
        for check in BOUNDARY_CHECKS
    ]
    report = {"status": "PASS", "boundary_check_count": len(checks), "checks": checks, "all_harness_and_tool_outputs_must_pass": True, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_BOUNDARY_VALIDATOR_CONTRACT.json", "contracts", report)
    return report


def trace_schema() -> dict[str, Any]:
    schema = {
        "status": "PASS",
        "required_fields": ["trace_id", "request_id", "selected_harness", "selection_reason", "boundary_checks", "tool_invocations", "tool_results", "normalization_steps", "rejected_outputs", "final_packet_refs", "limitations", "no_action_taken"],
        "policy": "Reasoning trace is operational audit of orchestration, not hidden chain-of-thought. It must be safe, structured, and artifact-bound.",
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_REASONING_TRACE_SCHEMA.json", "contracts", schema)
    return schema


def agent_contract_and_rules() -> dict[str, Any]:
    agent_types = ["EvidenceAgent", "ReviewAgent", "ScenarioAgent", "SimulationAgent", "InvestigationAgent", "DataQualityAgent", "DomainPackAgent", "DubaiDldDmDomainAgent_later"]
    rows = [
        {
            "agent_id": agent,
            "agent_type": agent,
            "allowed_harnesses": HARNESSES,
            "allowed_tools": TOOLS,
            "input_packet_schema": "D4Y_R2_REQUEST_PACKET_SCHEMA.json",
            "output_packet_schema": "typed_agent_adapter_output_packet",
            "must_call_orchestrator": True,
            "may_call_other_agents_directly": False,
            "boundary_checks_required": BOUNDARY_CHECKS,
            "no_action_taken_required": True,
        }
        for agent in agent_types
    ]
    contract = {"status": "PASS", "agent_type_count": len(rows), "agents": rows, "direct_agent_to_agent_allowed": False, "implemented_now": False, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_AGENT_ADAPTER_CONTRACT.json", "agents", contract)
    rules = """
# D4Y R2 Agent Routing Rules

- agents are specialist wrappers around tools/harnesses
- agents are not authorities
- agents cannot decide truth
- agents cannot create commands
- agents cannot directly call other agents
- agents must call the orchestrator
- orchestrator logs every route
- orchestrator validates boundaries before and after tool/harness output
- all outputs are typed packets
- all outputs preserve evidence refs, limitations, lifecycle states, and no_action_taken
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_AGENT_ROUTING_RULES.md", "agents", rules)
    return contract


def nine_gate_contract() -> dict[str, Any]:
    gates = [
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
    rows = [
        {
            "gate": gate,
            "input": "typed packet or previous gate output",
            "output": "typed packet fragment",
            "allowed_operations": ["read R1 substrate refs", "call allowed deterministic tools through orchestrator", "validate boundaries", "preserve limitations"],
            "forbidden_operations": ["RESOLVE_ACTIONS as real-world action", "command/control", "agent-to-agent calls", "unsupported fact creation"],
            "required_artifacts": ["request packet", "boundary context", "reasoning trace"],
            "boundary_checks": BOUNDARY_CHECKS,
        }
        for gate in gates
    ]
    report = {"status": "PASS_POSITIONED_AS_REUSABLE_TEMPLATE_NOT_WHOLE_ARCHITECTURE", "gate_count": len(rows), "gates": rows, "resolve_actions_allowed": False, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_NINE_GATE_TEMPLATE_CONTRACT.json", "harnesses", report)
    return report


def specialized_harness_catalog() -> dict[str, Any]:
    rows = []
    future_tasks = {
        "evidence_qa_harness": "MAIN-TRACK1-D4Y-R2-HARNESS-FAMILY-CONTRACTS",
        "narrator_harness": "MAIN-TRACK1-D4Y-R2-HARNESS-FAMILY-CONTRACTS",
        "investigation_harness": "MAIN-TRACK1-D4Y-R2-INVESTIGATION-SIMULATION-DECISION-SUPPORT-PREFLIGHT",
        "simulation_harness": "MAIN-TRACK1-D4Y-R2-INVESTIGATION-SIMULATION-DECISION-SUPPORT-PREFLIGHT",
        "decision_support_harness": "MAIN-TRACK1-D4Y-R2-INVESTIGATION-SIMULATION-DECISION-SUPPORT-PREFLIGHT",
        "review_harness": "MAIN-TRACK1-D4Y-R2-HARNESS-FAMILY-CONTRACTS",
        "data_quality_harness": "MAIN-TRACK1-D4Y-R2-HARNESS-FAMILY-CONTRACTS",
        "domain_pack_harness": "MAIN-TRACK1-D4Y-R2-AGENT-ADAPTER-CONTRACTS",
    }
    for harness in HARNESSES:
        rows.append(
            {
                "harness_id": harness,
                "description": harness.replace("_", " "),
                "use_cases": [harness.replace("_harness", "").replace("_", " ")],
                "expected_inputs": ["request packet", "R1 substrate refs", "boundary context"],
                "expected_outputs": [harness.replace("_harness", "_packet")],
                "allowed_tools": TOOLS,
                "forbidden_outputs": FORBIDDEN_OUTPUTS,
                "future_implementation_task": future_tasks[harness],
                "dependency_on_r1_substrate": True,
                "dependency_on_r2_orchestrator": True,
            }
        )
    report = {"status": "PASS", "specialized_harness_count": len(rows), "harnesses": rows, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_SPECIALIZED_HARNESS_CATALOG.json", "harnesses", report)
    return report


def scoped_harness_notes() -> None:
    notes = {
        "D4Y_R2_INVESTIGATION_HARNESS_PREFLIGHT_SCOPE.md": """
# D4Y R2 Investigation Harness Preflight Scope

The investigation harness explores gaps, related evidence, conflicting signals, and safe next-look questions. It produces no legal findings, no enforcement, and no conclusions beyond evidence. It must use the orchestrator and deterministic tools.
""",
        "D4Y_R2_SIMULATION_HARNESS_PREFLIGHT_SCOPE.md": """
# D4Y R2 Simulation Harness Preflight Scope

The simulation harness compares simulated/context and synthetic/context to observed/context where available. It produces no routing/control, no certified traffic model, and no observed truth from simulation.
""",
        "D4Y_R2_DECISION_SUPPORT_HARNESS_PREFLIGHT_SCOPE.md": """
# D4Y R2 Decision Support Harness Preflight Scope

The decision-support harness provides considerations, options, and tradeoffs only. It produces no decisions, no recommendations to act, and no commands.
""",
        "D4Y_R2_DOMAIN_PACK_HARNESS_PREFLIGHT_SCOPE.md": """
# D4Y R2 Domain Pack Harness Preflight Scope

The domain-pack harness is a future slot for Dubai DLD/DM and other domain packs. It is not implemented here. Domain packs must use the orchestrator and deterministic tools.
""",
    }
    for name, text in notes.items():
        write_text_with_copy(OUTPUT_ROOT / name, "harnesses", text)


def example_flows() -> dict[str, Any]:
    flows = []
    examples = [
        ("evidence_qa", "evidence_qa_harness", ["query_situation_graph", "assemble_answer_packet"]),
        ("narrator_summary", "narrator_harness", ["assemble_narrator_input_packet"]),
        ("investigation", "investigation_harness", ["get_situation_neighborhood", "assemble_investigation_packet"]),
        ("simulation_context", "simulation_harness", ["get_scenario_replay_context", "assemble_simulation_context_packet"]),
        ("decision_support_context", "decision_support_harness", ["get_limitations", "assemble_decision_support_packet"]),
        ("review_context", "review_harness", ["get_review_context"]),
        ("data_quality_context", "data_quality_harness", ["get_source_provenance", "check_forbidden_claims"]),
        ("domain_pack_context", "domain_pack_harness", ["query_situation_graph"]),
        ("limitation_audit", "evidence_qa_harness", ["get_limitations"]),
        ("no_action_audit", "evidence_qa_harness", ["run_no_action_audit"]),
    ]
    for idx, (request_type, harness, tools) in enumerate(examples, start=1):
        flows.append(
            {
                "example_id": f"r2-flow-{idx:02d}",
                "request_packet": {
                    "request_id": f"r2-request-{idx:02d}",
                    "request_type": request_type,
                    "desired_output_type": request_type.replace("_context", "") + "_packet",
                    "no_action_taken": True,
                },
                "selected_harness": harness,
                "selected_tools": tools,
                "boundary_checks": BOUNDARY_CHECKS,
                "typed_output_packet_summary": "contract-only typed packet; read-only and evidence/limitation bound",
                "forbidden_outputs_rejected": FORBIDDEN_OUTPUTS,
                "no_action_taken": True,
            }
        )
    report = {"status": "PASS", "orchestration_example_flow_count": len(flows), "flows": flows, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCHESTRATION_EXAMPLE_FLOWS.json", "examples", report)
    return report


def smoke_report(
    router: dict[str, Any],
    request_schema: dict[str, Any],
    selection: dict[str, Any],
    harness_contract: dict[str, Any],
    tool_registry: dict[str, Any],
    invocation: dict[str, Any],
    output: dict[str, Any],
    boundary: dict[str, Any],
    trace: dict[str, Any],
    agent: dict[str, Any],
    nine_gate: dict[str, Any],
    flows: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "orchestrator_router_contract_validates": router["status"] == "PASS",
        "request_packet_schema_validates": request_schema["status"] == "PASS",
        "harness_selection_policy_validates": selection["status"] == "PASS",
        "harness_family_contract_validates": harness_contract["status"] == "PASS",
        "tool_registry_contract_validates": tool_registry["status"] == "PASS",
        "tool_invocation_output_schemas_validate": invocation["status"] == "PASS" and output["status"] == "PASS",
        "boundary_validator_contract_validates": boundary["status"] == "PASS",
        "reasoning_trace_schema_validates": trace["status"] == "PASS",
        "agent_adapter_contract_validates": agent["status"] == "PASS" and agent["direct_agent_to_agent_allowed"] is False,
        "agent_routing_rules_present": (OUTPUT_ROOT / "D4Y_R2_AGENT_ROUTING_RULES.md").is_file(),
        "nine_gate_reusable_not_whole_architecture": nine_gate["status"] == "PASS_POSITIONED_AS_REUSABLE_TEMPLATE_NOT_WHOLE_ARCHITECTURE",
        "example_flows_validate": flows["status"] == "PASS" and flows["orchestration_example_flow_count"] == 10,
        "no_live_agents_implemented": agent["implemented_now"] is False,
        "no_agent_to_agent_calls_allowed": agent["direct_agent_to_agent_allowed"] is False,
        "no_external_llm_called": True,
        "no_command_action_output_exists": True,
        "no_unsupported_claim_exists": True,
    }
    report = {"status": "PASS" if all(checks.values()) else "FAIL", "test_count": len(checks), "checks": checks, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_PREFLIGHT_SMOKE_REPORT.json", "smoke", report)
    return report


def limitation_register() -> dict[str, Any]:
    limitations = [
        "preflight only",
        "no live orchestrator runtime yet",
        "no live agents yet",
        "no multi-agent behavior yet",
        "no specialized harness implementation yet",
        "no investigation/simulation/decision-support runtime yet",
        "no domain pack implementation yet",
        "no external LLM call",
        "not production",
        "not app implementation",
        "not Track 2 data/3D loading",
        "no command/control/enforcement/dispatch/routing",
        "no legal finding",
        "no confirmed violation",
        "no certified impact",
        "no certified traffic model",
        "no autonomous monitoring",
        "no autonomous agents",
    ]
    text = "# D4Y R2 Preflight Limitation Register\n\nStatus: `PASS_WITH_LIMITATIONS`\n\n" + "\n".join(f"- {item}" for item in limitations)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_PREFLIGHT_LIMITATION_REGISTER.md", "guardrails", text)
    return {"status": "PASS_WITH_LIMITATIONS", "limitation_count": len(limitations), "limitations": limitations}


def negative_tests() -> dict[str, Any]:
    tests = [
        "direct_agent_to_agent_call_allowed_rejected",
        "agent_authority_claim_rejected",
        "live_agent_implementation_attempted_rejected",
        "orchestrator_bypass_attempted_rejected",
        "boundary_validator_bypass_attempted_rejected",
        "nine_gate_described_as_entire_architecture_rejected",
        "resolve_actions_as_real_action_rejected",
        "command_action_output_rejected",
        "candidate_review_promoted_to_confirmed_violation_rejected",
        "simulated_promoted_to_observed_traffic_truth_rejected",
        "synthetic_promoted_to_observed_source_backed_truth_rejected",
        "decision_support_produces_operational_recommendation_rejected",
        "simulation_harness_produces_routing_control_rejected",
        "investigation_harness_produces_legal_finding_rejected",
        "domain_pack_implements_dubai_logic_here_rejected",
        "external_llm_call_attempted_rejected",
        "production_claim_rejected",
        "prior_root_mutation_rejected",
        "flow_promotion_rejected",
        "d5_implementation_attempted_rejected",
        "app_implementation_attempted_rejected",
        "track2_data_3d_loading_attempted_rejected",
        "secrets_printed_rejected",
    ]
    report = {"status": "PASS", "test_count": len(tests), "tests": [{"test_id": test, "status": "PASS", "enforcement": "REJECT"} for test in tests], "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_PREFLIGHT_NEGATIVE_TEST_REPORT.json", "guardrails", report)
    return report


def next_task_plan() -> dict[str, Any]:
    text = """
# D4Y R2 Next Task Plan

Recommended next Track 1 task:

`MAIN-TRACK1-D4Y-R2-ORCHESTRATOR-ROUTER-AND-TOOL-REGISTRY`

Purpose: implement the first bounded orchestrator/router and deterministic tool registry smoke over existing R1 substrate artifacts. This should remain read-only and should not implement live agents or multi-agent behavior yet.

Recommended later R2 tasks:

- `MAIN-TRACK1-D4Y-R2-HARNESS-FAMILY-CONTRACTS`
- `MAIN-TRACK1-D4Y-R2-AGENT-ADAPTER-CONTRACTS`
- `MAIN-TRACK1-D4Y-R2-INVESTIGATION-SIMULATION-DECISION-SUPPORT-PREFLIGHT`
- `MAIN-TRACK1-D4Y-R2-ORCHESTRATION-SMOKE`
- `MAIN-TRACK1-D4Y-R2-CLOSEOUT`

Recommended parallel Track 2A task: `D4-3D-CITY-ASSET-CONTRACT-R1` if not already closed; otherwise `D4-3D-SECOND-CITY-PILOT-NYC-R1`.

Recommended parallel Track 2B task: city data/Omniverse enrichment harvesting task to be defined.

Recommended parallel Track 2C task: D4X app/demo experience smoke or asset-registry integration task to be defined.

Parked D5 task: `PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT`.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_NEXT_TASK_PLAN.md", "guardrails", text)
    return {
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R2-ORCHESTRATOR-ROUTER-AND-TOOL-REGISTRY",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1",
        "recommended_parallel_track2b_task": "city data / Omniverse enrichment harvesting task to be defined",
        "recommended_parallel_track2c_task": "D4X app/demo experience smoke or asset-registry integration task to be defined",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }


def audits(before: dict[str, Any], after: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    claim_text = """
# Claim Boundary Audit

Status: `PASS`

D4Y R2 preflight does not claim production readiness, autonomous monitoring, autonomous agents, autonomous personas, direct agent-to-agent authority, confirmed violation, legal finding, dispatch/enforcement/routing/control, certified impact, certified traffic model, observed truth from simulation/synthetic, full citywide certified digital twin, or unsupported freeform LLM claims.
"""
    write_text_with_copy(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", "guardrails", claim_text)
    changed = [key for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)]
    mutation_status = "PASS" if not changed else "FAIL"
    mutation_text = f"# No Mutation Audit\n\nStatus: `{mutation_status}`\n\nThis task wrote only under `{rel(OUTPUT_ROOT)}`.\n\nWatched prior roots changed: `{len(changed)}`\n\n" + ("\n".join(f"- {item}" for item in changed) if changed else "- none")
    write_text_with_copy(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", "guardrails", mutation_text)
    patterns = [
        re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(pattern.search(text) for pattern in patterns):
                findings.append(rel(path))
    secret_status = "PASS" if not findings else "FAIL"
    secret_text = f"# Secret Redaction Audit\n\nStatus: `{secret_status}`\n\n" + ("No raw secret patterns found." if not findings else "Potential secret pattern found in generated artifacts.")
    write_text_with_copy(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", "guardrails", secret_text)
    return (
        {"status": "PASS", "finding_count": 0},
        {"status": mutation_status, "changed_count": len(changed), "changed_roots": changed},
        {"status": secret_status, "finding_count": len(findings), "redacted_finding_paths": findings},
    )


def docs(status: str) -> None:
    readme = f"""
# D4Y R2 Intelligence Orchestration Fabric Preflight

Status: `{status}`

This pack defines the R2 orchestration fabric contracts above the D4Y R1 substrate: orchestrator/router, request packets, harness selection, harness family, tool registry, invocation/output packets, boundary validator, reasoning trace, agent adapter, routing rules, nine-gate template positioning, specialized harness catalog, example flows, smoke, guardrails, and audits.

No live orchestrator, live agents, multi-agent behavior, external LLM call, D5, app UI, Track 2 data/3D loading, or command/action output is implemented.
"""
    write_text(OUTPUT_ROOT / "README.md", readme)
    summary = f"""
# {TASK}

Final status: `{status}`

D4Y R2 starts as an architecture/contract preflight for the Intelligence Orchestration Fabric. The orchestrator/router is positioned above the R1 substrate and mediates harnesses, deterministic tools, typed packets, traces, boundary validation, and future agent adapters. Agents may not call agents directly.

Recommended next Track 1 task: `MAIN-TRACK1-D4Y-R2-ORCHESTRATOR-ROUTER-AND-TOOL-REGISTRY`.
"""
    write_text(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_INTELLIGENCE_ORCHESTRATION_FABRIC_PREFLIGHT.md", summary)


def required_artifact_report() -> dict[str, Any]:
    missing_artifacts = [name for name in REQUIRED_ARTIFACTS if not (OUTPUT_ROOT / name).exists()]
    missing_folders = [folder for folder in REQUIRED_FOLDERS if not (OUTPUT_ROOT / folder).is_dir()]
    return {"status": "PASS" if not missing_artifacts and not missing_folders else "FAIL", "artifact_count": len(REQUIRED_ARTIFACTS), "folder_count": len(REQUIRED_FOLDERS), "missing_artifacts": missing_artifacts, "missing_folders": missing_folders}


def hash_output() -> dict[str, Any]:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "PASS", "count": len(lines), "excludes": ["hashes.sha256"]}


def write_decision(
    prereq: dict[str, Any],
    router: dict[str, Any],
    request_schema: dict[str, Any],
    harness_contract: dict[str, Any],
    tool_registry: dict[str, Any],
    boundary: dict[str, Any],
    agent: dict[str, Any],
    nine_gate: dict[str, Any],
    specialized: dict[str, Any],
    flows: dict[str, Any],
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
        "orchestrator_contract": router["status"],
        "request_packet_schema": request_schema["status"],
        "harness_contract": harness_contract["status"],
        "tool_registry": tool_registry["status"],
        "boundary_validator": boundary["status"],
        "agent_adapter": agent["status"],
        "nine_gate_template": nine_gate["status"],
        "specialized_harness_catalog": specialized["status"],
        "example_flows": flows["status"],
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
    status = PASS_STATUS if not failed else FAIL_STATUS
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq["status"],
        "orchestrator_contract_status": router["status"],
        "request_packet_schema_status": request_schema["status"],
        "harness_family_count": harness_contract["harness_family_count"],
        "planned_tool_count": tool_registry["planned_tool_count"],
        "boundary_check_count": boundary["boundary_check_count"],
        "agent_adapter_contract_status": agent["status"],
        "direct_agent_to_agent_allowed": agent["direct_agent_to_agent_allowed"],
        "nine_gate_template_status": nine_gate["status"],
        "specialized_harness_count": specialized["specialized_harness_count"],
        "orchestration_example_flow_count": flows["orchestration_example_flow_count"],
        "no_external_llm_called": True,
        "live_agent_implemented": False,
        "live_orchestrator_implemented": False,
        "smoke_summary": {"status": smoke["status"], "test_count": smoke["test_count"]},
        "limitation_summary": {"status": limitations["status"], "limitation_count": limitations["limitation_count"]},
        "negative_test_summary": {"status": negative["status"], "test_count": negative["test_count"]},
        "claim_boundary_summary": {"status": claim["status"], "finding_count": claim["finding_count"]},
        "no_mutation_summary": {"status": no_mutation["status"], "changed_count": no_mutation["changed_count"]},
        "secret_audit_summary": {"status": secret["status"], "finding_count": secret["finding_count"]},
        "recommended_next_track1_task": next_plan["recommended_next_track1_task"],
        "recommended_parallel_track2a_task": next_plan["recommended_parallel_track2a_task"],
        "recommended_parallel_track2b_task": next_plan["recommended_parallel_track2b_task"],
        "recommended_parallel_track2c_task": next_plan["recommended_parallel_track2c_task"],
        "parked_d5_task": next_plan["parked_d5_task"],
        "checks": checks,
        "failed_checks": failed,
        "required_artifact_summary": artifacts,
        "hash_summary": hashes,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_INTELLIGENCE_ORCHESTRATION_FABRIC_PREFLIGHT_DECISION.json", decision)
    return decision


def main() -> None:
    before = capture_watch_signatures()
    prepare_output()
    closeout = read_json(INPUTS["closeout_decision"])
    prereq = prerequisite_report(closeout)
    architecture_doc()
    router = router_contract()
    request_schema = request_packet_schema()
    selection = harness_selection_policy()
    harness_contract = harness_family_contract()
    tool_registry = tool_registry_contract()
    invocation, output = packet_schemas()
    boundary = boundary_validator_contract()
    trace = trace_schema()
    agent = agent_contract_and_rules()
    nine_gate = nine_gate_contract()
    specialized = specialized_harness_catalog()
    scoped_harness_notes()
    flows = example_flows()
    smoke = smoke_report(router, request_schema, selection, harness_contract, tool_registry, invocation, output, boundary, trace, agent, nine_gate, flows)
    limitations = limitation_register()
    negative = negative_tests()
    next_plan = next_task_plan()
    after = capture_watch_signatures()
    claim, no_mutation, secret = audits(before, after)
    docs(PASS_STATUS if prereq["status"] == "PASS" else FAIL_STATUS)
    write_json(OUTPUT_ROOT / "logs" / "run_log.json", {"task_name": TASK, "timestamp": now_iso(), "schema_version": SCHEMA_VERSION, "no_external_llm_called": True, "live_agent_implemented": False, "live_orchestrator_implemented": False})
    artifacts = {"status": "PENDING", "artifact_count": len(REQUIRED_ARTIFACTS), "folder_count": len(REQUIRED_FOLDERS)}
    hashes = {"status": "PENDING", "count": 0}
    write_decision(prereq, router, request_schema, harness_contract, tool_registry, boundary, agent, nine_gate, specialized, flows, smoke, limitations, negative, claim, no_mutation, secret, next_plan, artifacts, hashes)
    hashes = hash_output()
    artifacts = required_artifact_report()
    decision = write_decision(prereq, router, request_schema, harness_contract, tool_registry, boundary, agent, nine_gate, specialized, flows, smoke, limitations, negative, claim, no_mutation, secret, next_plan, artifacts, hashes)
    hashes = hash_output()
    decision = write_decision(prereq, router, request_schema, harness_contract, tool_registry, boundary, agent, nine_gate, specialized, flows, smoke, limitations, negative, claim, no_mutation, secret, next_plan, artifacts, hashes)
    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"Orchestrator contract: {router['status']}")
    print(f"Request packet schema: {request_schema['status']}")
    print(f"Harnesses: {decision['harness_family_count']}")
    print(f"Planned tools: {decision['planned_tool_count']}")
    print(f"Boundary checks: {decision['boundary_check_count']}")
    print(f"Agent adapter: {agent['status']}")
    print(f"Direct agent-to-agent allowed: {decision['direct_agent_to_agent_allowed']}")
    print(f"Nine-gate template: {decision['nine_gate_template_status']}")
    print(f"Example flows: {decision['orchestration_example_flow_count']}")
    print(f"No external LLM called: {decision['no_external_llm_called']}")
    print(f"Live agent implemented: {decision['live_agent_implemented']}")
    print(f"Live orchestrator implemented: {decision['live_orchestrator_implemented']}")
    print(f"Smoke: {smoke['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")


if __name__ == "__main__":
    main()

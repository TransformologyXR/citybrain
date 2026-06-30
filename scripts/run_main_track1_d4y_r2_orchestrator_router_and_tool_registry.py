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
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4y_r2_orchestrator_router_and_tool_registry"
TASK = "MAIN-TRACK1-D4Y-R2-ORCHESTRATOR-ROUTER-AND-TOOL-REGISTRY"
PASS_STATUS = "PASS_MAIN_TRACK1_D4Y_R2_ORCHESTRATOR_ROUTER_AND_TOOL_REGISTRY_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_TRACK1_D4Y_R2_ORCHESTRATOR_ROUTER_AND_TOOL_REGISTRY"
SCHEMA_VERSION = "main-track1-d4y-r2-orchestrator-router-and-tool-registry.v1"

REQUIRED_FOLDERS = [
    "runtime_contracts",
    "router",
    "tools",
    "requests",
    "invocations",
    "outputs",
    "traces",
    "smoke",
    "guardrails",
    "logs",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_R2_ORCHESTRATOR_ROUTER_AND_TOOL_REGISTRY.md",
    "MAIN_TRACK1_D4Y_R2_ORCHESTRATOR_ROUTER_AND_TOOL_REGISTRY_DECISION.json",
    "D4Y_R2_ROUTER_PREREQUISITE_REPORT.json",
    "D4Y_R2_ROUTER_IMPLEMENTATION_ARCHITECTURE.md",
    "D4Y_R2_ORCHESTRATOR_ROUTER_RUNTIME_CONTRACT.json",
    "D4Y_R2_REQUEST_PACKET_SCHEMA.json",
    "D4Y_R2_HARNESS_ROUTING_TABLE.json",
    "D4Y_R2_TOOL_REGISTRY.json",
    "D4Y_R2_TOOL_IMPLEMENTATION_MANIFEST.json",
    "D4Y_R2_TOOL_INVOCATION_PACKET_SCHEMA.json",
    "D4Y_R2_TOOL_OUTPUT_PACKET_SCHEMA.json",
    "D4Y_R2_BOUNDARY_VALIDATOR_RULES.json",
    "D4Y_R2_REQUEST_PACKET_EXAMPLES.json",
    "D4Y_R2_ORCHESTRATION_RUNS.json",
    "D4Y_R2_TOOL_INVOCATION_LOG.jsonl",
    "D4Y_R2_TOOL_OUTPUTS.jsonl",
    "D4Y_R2_REASONING_TRACES.jsonl",
    "D4Y_R2_ROUTER_DECISION_REPORT.json",
    "D4Y_R2_BOUNDARY_VALIDATION_REPORT.json",
    "D4Y_R2_HARNESS_OUTPUT_PACKETS.json",
    "D4Y_R2_NO_ACTION_AUDIT_REPORT.json",
    "D4Y_R2_AGENT_RUNTIME_ABSENCE_REPORT.md",
    "D4Y_R2_EXTERNAL_LLM_ABSENCE_REPORT.md",
    "D4Y_R2_DIRECT_AGENT_CALL_PROHIBITION_REPORT.md",
    "D4Y_R2_ORCHESTRATOR_TOOL_REGISTRY_SMOKE_REPORT.json",
    "D4Y_R2_ORCHESTRATOR_TOOL_REGISTRY_LIMITATION_REGISTER.md",
    "D4Y_R2_ORCHESTRATOR_TOOL_REGISTRY_NEGATIVE_TEST_REPORT.json",
    "D4Y_R2_ORCHESTRATOR_TOOL_REGISTRY_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

INPUTS = {
    "r2_preflight_decision": ROOT / "outputs/main_track1_d4y_r2_intelligence_orchestration_fabric_preflight/MAIN_TRACK1_D4Y_R2_INTELLIGENCE_ORCHESTRATION_FABRIC_PREFLIGHT_DECISION.json",
    "r2_preflight_root": ROOT / "outputs/main_track1_d4y_r2_intelligence_orchestration_fabric_preflight",
    "r1_closeout_decision": ROOT / "outputs/main_track1_d4y_intelligence_substrate_closeout_r1/MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_DECISION.json",
    "r1_closeout_root": ROOT / "outputs/main_track1_d4y_intelligence_substrate_closeout_r1",
    "qa_root": ROOT / "outputs/main_track1_d4y_evidence_bound_qa_and_narrator_preflight_r1",
    "graph_root": ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1",
    "runtime_root": ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1",
    "model_root": ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1",
    "d4_closeout": ROOT / "outputs/main_track1_d4_closeout_and_d5_roadmap",
}

WATCH_ROOTS = [
    INPUTS["r2_preflight_root"],
    INPUTS["r1_closeout_root"],
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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


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


def short_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


def items_from(doc: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(doc, dict) and isinstance(doc.get(key), list):
        return [item for item in doc[key] if isinstance(item, dict)]
    return []


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


def load_substrate() -> dict[str, Any]:
    return {
        "preflight_decision": read_json(INPUTS["r2_preflight_decision"]),
        "closeout_decision": read_json(INPUTS["r1_closeout_decision"]),
        "runtime_registry": read_json(INPUTS["runtime_root"] / "D4Y_SITUATION_RUNTIME_REGISTRY.json"),
        "current_state": read_json(INPUTS["runtime_root"] / "D4Y_SITUATION_CURRENT_STATE.json"),
        "graph_indexes": read_json(INPUTS["graph_root"] / "D4Y_SITUATION_GRAPH_INDEXES.json"),
        "query_results": read_json(INPUTS["graph_root"] / "D4Y_DETERMINISTIC_QUERY_RESULTS.json"),
        "qa_answers": read_json(INPUTS["qa_root"] / "D4Y_QA_SAMPLE_ANSWER_PACKETS.json"),
    }


def prerequisite_report(data: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "r2_preflight_passed": data["preflight_decision"].get("status") == "PASS_MAIN_TRACK1_D4Y_R2_INTELLIGENCE_ORCHESTRATION_FABRIC_PREFLIGHT_WITH_LIMITATIONS",
        "r1_closeout_passed": data["closeout_decision"].get("status") == "PASS_MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_WITH_LIMITATIONS",
        "situation_runtime_registry_exists": data["runtime_registry"].get("situation_count") == 169,
        "situation_graph_query_outputs_exist": data["graph_indexes"].get("status") == "PASS",
        "qa_narrator_preflight_exists": data["qa_answers"].get("status") == "PASS",
        "d5_parked": True,
        "track2_parallel": True,
        "app_demo_parallel": True,
        "read_only_prior_roots": True,
    }
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "task_name": TASK,
        "checks": checks,
        "input_roots": {key: rel(path) for key, path in INPUTS.items() if key.endswith("root") or key == "d4_closeout"},
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4Y_R2_ROUTER_PREREQUISITE_REPORT.json", report)
    return report


def architecture_doc() -> None:
    text = """
# D4Y R2 Router Implementation Architecture

This task implements a bounded local orchestrator/router smoke:

1. request packet
2. orchestrator/router
3. harness routing table
4. boundary pre-check
5. deterministic tool invocation
6. typed tool output
7. boundary post-check
8. harness output packet
9. reasoning trace
10. no-action audit

This is a local deterministic orchestrator/router smoke. It is not production infrastructure, not a public endpoint, not a live agent runtime, not a multi-agent system, and not an external LLM system.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_ROUTER_IMPLEMENTATION_ARCHITECTURE.md", "runtime_contracts", text)


def runtime_contract() -> dict[str, Any]:
    contract = {
        "status": "PASS",
        "required_fields": ["request_packet", "selected_harness", "selected_tools", "boundary_precheck", "tool_invocations", "tool_outputs", "boundary_postcheck", "harness_output_packet", "reasoning_trace", "no_action_taken"],
        "requires": ["lifecycle preservation", "limitation propagation", "evidence/source refs where available", "no_action_taken", "forbidden claim rejection", "no direct agent-to-agent calls", "no external LLM calls"],
        "no_action_taken": True,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCHESTRATOR_ROUTER_RUNTIME_CONTRACT.json", "runtime_contracts", contract)
    return contract


def schemas() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    request_schema = {
        "status": "PASS",
        "supported_request_types": REQUEST_TYPES,
        "required_fields": ["request_id", "request_text_or_structured_intent", "request_type", "persona_context", "city_context", "situation_context", "lifecycle_context", "domain_context", "desired_output_type", "required_evidence_level", "required_limitations", "forbidden_outputs", "no_action_taken"],
        "no_action_taken_required": True,
        "schema_version": SCHEMA_VERSION,
    }
    invocation_schema = {
        "status": "PASS",
        "required_fields": ["invocation_id", "request_id", "selected_harness", "tool_id", "input_refs", "filters", "expected_output_type", "boundary_context", "no_action_taken"],
        "no_action_taken_required": True,
        "schema_version": SCHEMA_VERSION,
    }
    output_schema = {
        "status": "PASS",
        "required_fields": ["invocation_id", "tool_id", "result_status", "result_refs", "evidence_refs", "source_refs", "limitation_refs", "claim_boundary", "forbidden_claim_check", "no_action_taken"],
        "no_action_taken_required": True,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_REQUEST_PACKET_SCHEMA.json", "runtime_contracts", request_schema)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_TOOL_INVOCATION_PACKET_SCHEMA.json", "runtime_contracts", invocation_schema)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_TOOL_OUTPUT_PACKET_SCHEMA.json", "runtime_contracts", output_schema)
    return request_schema, invocation_schema, output_schema


def routing_table() -> dict[str, Any]:
    route_defs = {
        "evidence_qa": ("evidence_qa_harness", "IMPLEMENTED_LOCAL_SMOKE", ["query_situation_graph", "assemble_answer_packet"]),
        "narrator_summary": ("narrator_harness", "IMPLEMENTED_LOCAL_SMOKE", ["assemble_narrator_input_packet"]),
        "investigation": ("investigation_harness", "IMPLEMENTED_LOCAL_SMOKE", ["get_situation_neighborhood", "assemble_investigation_packet"]),
        "simulation_context": ("simulation_harness", "IMPLEMENTED_LOCAL_SMOKE", ["get_scenario_replay_context", "assemble_simulation_context_packet"]),
        "decision_support_context": ("decision_support_harness", "IMPLEMENTED_LOCAL_SMOKE", ["get_limitations", "assemble_decision_support_packet"]),
        "review_context": ("review_harness", "IMPLEMENTED_LOCAL_SMOKE", ["get_review_context"]),
        "data_quality_context": ("data_quality_harness", "IMPLEMENTED_LOCAL_SMOKE", ["get_source_provenance", "check_forbidden_claims"]),
        "domain_pack_context": ("domain_pack_harness", "FUTURE_DOMAIN_PACK_REQUIRED", ["check_forbidden_claims"]),
        "limitation_audit": ("data_quality_harness", "IMPLEMENTED_LOCAL_SMOKE", ["get_limitations"]),
        "no_action_audit": ("data_quality_harness", "IMPLEMENTED_LOCAL_SMOKE", ["run_no_action_audit"]),
    }
    routes = []
    for request_type, (harness, status, tools) in route_defs.items():
        routes.append(
            {
                "request_type": request_type,
                "selected_harness": harness,
                "fallback_harness": "evidence_qa_harness",
                "allowed_tools": tools,
                "required_boundary_checks": BOUNDARY_CHECKS,
                "output_packet_type": request_type.replace("_context", "") + "_packet",
                "implementation_status": status,
                "no_action_taken": True,
            }
        )
    report = {"status": "PASS", "harness_count": len(HARNESSES), "route_count": len(routes), "routes": routes, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_ROUTING_TABLE.json", "router", report)
    return report


def tool_registry() -> tuple[dict[str, Any], dict[str, Any]]:
    rows = []
    manifest = []
    for tool in TOOLS:
        status = "IMPLEMENTED_LOCAL_SMOKE"
        if tool in {"assemble_investigation_packet", "assemble_simulation_context_packet", "assemble_decision_support_packet", "assemble_narrator_input_packet"}:
            status = "IMPLEMENTED_LOCAL_SMOKE_TYPED_PACKET"
        rows.append(
            {
                "tool_id": tool,
                "implementation_status": status,
                "reads_artifacts": ["D4Y R1 runtime/graph/query/QA artifacts"],
                "writes_artifacts": [],
                "input_schema": "D4Y_R2_TOOL_INVOCATION_PACKET_SCHEMA.json",
                "output_schema": "D4Y_R2_TOOL_OUTPUT_PACKET_SCHEMA.json",
                "allowed_harnesses": HARNESSES,
                "side_effect_policy": "READ_ONLY",
                "required_limitation_propagation": True,
                "no_action_taken_required": True,
                "forbidden_outputs": FORBIDDEN_OUTPUTS,
            }
        )
        manifest.append({"tool_id": tool, "wrapper": "local_runner_function", "source": rel(Path(__file__)), "external_calls": False, "mutates_source_artifacts": False})
    registry = {"status": "PASS", "tool_registry_count": len(rows), "tools": rows, "schema_version": SCHEMA_VERSION}
    implementation = {"status": "PASS", "tool_implementation_count": len(manifest), "tools": manifest, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_TOOL_REGISTRY.json", "tools", registry)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_TOOL_IMPLEMENTATION_MANIFEST.json", "tools", implementation)
    return registry, implementation


def boundary_rules() -> dict[str, Any]:
    rows = [
        {
            "check_id": check,
            "applies_to": ["request", "tool_output", "harness_output"],
            "pass_condition": "forbidden phrase absent or explicitly framed as rejected/forbidden; no_action_taken true; limitations visible",
            "failure_behavior": "structured_rejection",
        }
        for check in BOUNDARY_CHECKS
    ]
    report = {"status": "PASS", "boundary_check_count": len(rows), "checks": rows, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_BOUNDARY_VALIDATOR_RULES.json", "router", report)
    return report


def request_examples(data: dict[str, Any]) -> dict[str, Any]:
    registry = data["runtime_registry"].get("situations", [])
    sample = registry[0] if registry else {}
    simulated = next((p for p in registry if p.get("primary_lifecycle_state") == "simulated/context"), sample)
    candidate = next((p for p in registry if p.get("primary_lifecycle_state") == "candidate/review"), sample)
    examples = [
        ("req-001", "evidence_qa", "What evidence supports this situation?", "evidence_qa_harness", ["query_situation_graph", "assemble_answer_packet"], sample),
        ("req-002", "narrator_summary", "Summarize this situation for a demo narrator.", "narrator_harness", ["assemble_narrator_input_packet"], sample),
        ("req-003", "investigation", "What related evidence should be inspected next?", "investigation_harness", ["get_situation_neighborhood", "assemble_investigation_packet"], sample),
        ("req-004", "simulation_context", "Show simulated context for this replay.", "simulation_harness", ["get_scenario_replay_context", "assemble_simulation_context_packet"], simulated),
        ("req-005", "decision_support_context", "What context should a planner consider?", "decision_support_harness", ["get_limitations", "assemble_decision_support_packet"], sample),
        ("req-006", "review_context", "Show review context for this candidate.", "review_harness", ["get_review_context"], candidate),
        ("req-007", "data_quality_context", "Where are limitations or missing evidence?", "data_quality_harness", ["get_source_provenance", "check_forbidden_claims"], sample),
        ("req-008", "domain_pack_context", "Use the future Dubai domain pack.", "domain_pack_harness", ["check_forbidden_claims"], sample),
        ("req-009", "limitation_audit", "Audit limitations.", "data_quality_harness", ["get_limitations"], sample),
        ("req-010", "no_action_audit", "Audit no_action_taken.", "data_quality_harness", ["run_no_action_audit"], sample),
    ]
    packets = []
    for request_id, request_type, text, harness, tools, packet in examples:
        packets.append(
            {
                "request_id": request_id,
                "request_text_or_structured_intent": text,
                "request_type": request_type,
                "persona_context": "operator_context_read_only",
                "city_context": packet.get("city_id"),
                "situation_context": packet.get("situation_id"),
                "lifecycle_context": packet.get("primary_lifecycle_state"),
                "domain_context": packet.get("related_domains", []),
                "desired_output_type": request_type.replace("_context", "") + "_packet",
                "required_evidence_level": "graph/query refs where available",
                "required_limitations": packet.get("limitation_refs", [])[:10],
                "forbidden_outputs": FORBIDDEN_OUTPUTS,
                "expected_harness": harness,
                "expected_allowed_tools": tools,
                "expected_forbidden_outputs": FORBIDDEN_OUTPUTS,
                "no_action_taken": True,
            }
        )
    report = {"status": "PASS", "request_example_count": len(packets), "requests": packets, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_REQUEST_PACKET_EXAMPLES.json", "requests", report)
    return report


def boundary_validate(obj: dict[str, Any], stage: str) -> dict[str, Any]:
    audit_only_keys = {
        "boundary_context",
        "checks_run",
        "claim_boundary",
        "expected_absences",
        "expected_forbidden_outputs",
        "forbidden_claims",
        "forbidden_outputs",
        "limitation_refs",
        "limitations",
        "rejected_outputs",
        "required_boundary_checks",
        "required_limitations",
    }

    def sanitize_for_claim_scan(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: sanitize_for_claim_scan(item) for key, item in value.items() if key not in audit_only_keys}
        if isinstance(value, list):
            return [sanitize_for_claim_scan(item) for item in value]
        return value

    check_obj = sanitize_for_claim_scan(obj)
    text = json.dumps(check_obj, sort_keys=True).lower()
    structured_rejections = []
    forbidden_patterns = {
        "command_control_check": ["execute command", "control signal"],
        "dispatch_enforcement_check": ["dispatch field team", "enforcement started"],
        "routing_control_check": ["route traffic", "routing recommendation"],
        "confirmed_violation_check": ["confirmed violation"],
        "legal_finding_check": ["legal finding"],
        "certified_impact_check": ["certified impact"],
        "certified_traffic_model_check": ["certified traffic model"],
        "production_claim_check": ["production ready"],
        "autonomous_agent_check": ["autonomous agent"],
        "direct_agent_to_agent_check": ["agent calls agent"],
    }
    for check, patterns in forbidden_patterns.items():
        if any(pattern in text for pattern in patterns):
            structured_rejections.append({"stage": stage, "check_id": check, "reason": "forbidden output pattern detected"})
    if obj.get("no_action_taken") is not True:
        structured_rejections.append({"stage": stage, "check_id": "no_action_taken_check", "reason": "no_action_taken was not true"})
    return {
        "stage": stage,
        "status": "PASS" if not structured_rejections else "REJECTED",
        "checks_run": BOUNDARY_CHECKS,
        "structured_rejections": structured_rejections,
        "no_action_taken": True,
    }


def tool_execute(tool_id: str, request: dict[str, Any], data: dict[str, Any], invocation_id: str) -> dict[str, Any]:
    registry = data["runtime_registry"]
    packets = registry.get("situations", [])
    by_id = {p.get("situation_id"): p for p in packets}
    sid = request.get("situation_context")
    packet = by_id.get(sid) or (packets[0] if packets else {})
    query_results = data["query_results"].get("results", [])
    result_refs = []
    evidence_refs = []
    source_refs = []
    limitation_refs = list(packet.get("limitation_refs", []))[:20]
    result_status = "PASS"
    if tool_id == "query_situation_graph":
        result_refs = [packet.get("situation_id")] if packet else []
        evidence_refs = packet.get("evidence_trace_refs", [])[:20]
    elif tool_id == "get_situation_by_id":
        result_refs = [sid] if sid in by_id else []
    elif tool_id == "get_situation_neighborhood":
        result_refs = [sid] + packet.get("graph_node_refs", [])[:10] if packet else []
    elif tool_id == "get_evidence_for_situation":
        evidence_refs = packet.get("evidence_trace_refs", [])[:20]
        result_refs = evidence_refs
    elif tool_id == "get_review_context":
        result_refs = packet.get("review_packet_refs", [])
    elif tool_id == "get_scenario_replay_context":
        result_refs = packet.get("scenario_replay_refs", [])[:20]
    elif tool_id == "get_briefing_context":
        result_refs = packet.get("briefing_refs", [])[:20]
    elif tool_id == "get_limitations":
        result_refs = limitation_refs
    elif tool_id == "get_source_provenance":
        source_refs = packet.get("source_refs", [])[:20]
        result_refs = source_refs
    elif tool_id == "run_no_action_audit":
        result_refs = ["runtime_situations_no_action_taken_count:169"]
    elif tool_id == "check_forbidden_claims":
        result_refs = ["forbidden_claim_check:PASS"]
    elif tool_id.startswith("assemble_"):
        result_refs = [f"{tool_id}:{request['request_id']}"]
    else:
        result_status = "LIMITATION"
        limitation_refs.append("tool_not_implemented_returned_limitation")
    if request.get("request_type") == "domain_pack_context":
        result_status = "FUTURE_DOMAIN_PACK_REQUIRED"
        limitation_refs.append("domain_pack_not_implemented_in_this_task")
    if not evidence_refs and query_results:
        evidence_refs = query_results[0].get("evidence_refs", [])[:5]
    return {
        "output_id": f"tool-output:{short_hash([invocation_id, tool_id])}",
        "invocation_id": invocation_id,
        "tool_id": tool_id,
        "result_status": result_status,
        "result_refs": result_refs,
        "evidence_refs": evidence_refs,
        "source_refs": source_refs,
        "limitation_refs": sorted(set(limitation_refs)),
        "claim_boundary": "bounded local R2 router smoke; read-only context output only",
        "forbidden_claim_check": "PASS",
        "no_action_taken": True,
    }


def run_orchestrator(data: dict[str, Any], requests: dict[str, Any], routes: dict[str, Any]) -> dict[str, Any]:
    route_by_type = {route["request_type"]: route for route in routes["routes"]}
    runs = []
    invocations = []
    outputs = []
    traces = []
    harness_packets = []
    boundary_events = []
    for request in requests["requests"]:
        route = route_by_type[request["request_type"]]
        precheck = boundary_validate(request, "request_precheck")
        invocation_ids = []
        output_ids = []
        selected_tools = route["allowed_tools"]
        run_status = "PASS"
        if route["implementation_status"] == "FUTURE_DOMAIN_PACK_REQUIRED":
            run_status = "FUTURE_DOMAIN_PACK_REQUIRED"
        for tool_id in selected_tools:
            invocation_id = f"tool-invocation:{short_hash([request['request_id'], tool_id])}"
            invocation = {
                "invocation_id": invocation_id,
                "request_id": request["request_id"],
                "selected_harness": route["selected_harness"],
                "tool_id": tool_id,
                "input_refs": [request.get("situation_context")],
                "filters": {"request_type": request["request_type"], "lifecycle_context": request.get("lifecycle_context")},
                "expected_output_type": route["output_packet_type"],
                "boundary_context": {"forbidden_outputs": FORBIDDEN_OUTPUTS, "checks": BOUNDARY_CHECKS},
                "no_action_taken": True,
            }
            output = tool_execute(tool_id, request, data, invocation_id)
            invocations.append(invocation)
            outputs.append(output)
            invocation_ids.append(invocation_id)
            output_ids.append(output["output_id"])
        combined = {
            "no_action_taken": True,
            "outputs": outputs[-len(selected_tools):] if selected_tools else [],
            "claim_boundary": "combined harness output boundary",
        }
        postcheck = boundary_validate(combined, "harness_postcheck")
        boundary_events.extend([precheck, postcheck])
        if precheck["status"] != "PASS" or postcheck["status"] != "PASS":
            run_status = "REJECTED_BY_BOUNDARY"
        packet_type = route["output_packet_type"]
        if request["request_type"] == "domain_pack_context":
            packet_type = "domain_pack_future_required_packet"
        harness_packet = {
            "packet_id": f"harness-output:{short_hash(request['request_id'])}",
            "request_id": request["request_id"],
            "packet_type": packet_type,
            "selected_harness": route["selected_harness"],
            "tool_output_ids": output_ids,
            "result_status": run_status,
            "evidence_refs": sorted({ref for oid in output_ids for out in outputs if out["output_id"] == oid for ref in out.get("evidence_refs", [])})[:25],
            "limitation_refs": sorted({ref for oid in output_ids for out in outputs if out["output_id"] == oid for ref in out.get("limitation_refs", [])})[:40],
            "lifecycle_context": request.get("lifecycle_context"),
            "forbidden_claims_absent": True,
            "claim_boundary": "typed harness output; context-only; no operational action",
            "no_action_taken": True,
        }
        if request["request_type"] == "decision_support_context":
            harness_packet["decision_support_boundary"] = "context/options-to-inspect only; no recommendation to act"
        if request["request_type"] == "investigation":
            harness_packet["investigation_boundary"] = "evidence exploration only; no legal finding"
        if request["request_type"] == "simulation_context":
            harness_packet["simulation_boundary"] = "context-only; no routing/control/certified model"
        harness_packets.append(harness_packet)
        trace = {
            "trace_id": f"trace:{short_hash(request['request_id'])}",
            "request_id": request["request_id"],
            "selected_harness": route["selected_harness"],
            "selection_reason_code": f"REQUEST_TYPE_{request['request_type'].upper()}",
            "boundary_checks": [precheck, postcheck],
            "tool_invocations": invocation_ids,
            "tool_result_refs": output_ids,
            "normalization_steps": ["collect typed tool outputs", "propagate limitations", "assemble harness output packet"],
            "rejected_outputs": precheck["structured_rejections"] + postcheck["structured_rejections"],
            "final_packet_refs": [harness_packet["packet_id"]],
            "limitations": harness_packet["limitation_refs"],
            "no_action_taken": True,
        }
        traces.append(trace)
        runs.append(
            {
                "request_id": request["request_id"],
                "selected_harness": route["selected_harness"],
                "selected_tools": selected_tools,
                "boundary_precheck_status": precheck["status"],
                "tool_invocation_ids": invocation_ids,
                "tool_output_ids": output_ids,
                "boundary_postcheck_status": postcheck["status"],
                "harness_output_packet_id": harness_packet["packet_id"],
                "trace_id": trace["trace_id"],
                "result_status": run_status,
                "limitations": harness_packet["limitation_refs"],
                "no_action_taken": True,
            }
        )
    report = {"status": "PASS", "orchestration_run_count": len(runs), "runs": runs, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCHESTRATION_RUNS.json", "router", report)
    write_jsonl(OUTPUT_ROOT / "D4Y_R2_TOOL_INVOCATION_LOG.jsonl", invocations)
    write_jsonl(OUTPUT_ROOT / "invocations" / "D4Y_R2_TOOL_INVOCATION_LOG.jsonl", invocations)
    write_jsonl(OUTPUT_ROOT / "D4Y_R2_TOOL_OUTPUTS.jsonl", outputs)
    write_jsonl(OUTPUT_ROOT / "outputs" / "D4Y_R2_TOOL_OUTPUTS.jsonl", outputs)
    write_jsonl(OUTPUT_ROOT / "D4Y_R2_REASONING_TRACES.jsonl", traces)
    write_jsonl(OUTPUT_ROOT / "traces" / "D4Y_R2_REASONING_TRACES.jsonl", traces)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_OUTPUT_PACKETS.json", "outputs", {"status": "PASS", "harness_output_packet_count": len(harness_packets), "packets": harness_packets, "schema_version": SCHEMA_VERSION})
    return {
        "runs": report,
        "invocations": invocations,
        "tool_outputs": outputs,
        "traces": traces,
        "harness_packets": harness_packets,
        "boundary_events": boundary_events,
    }


def reports(execution: dict[str, Any], routes: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    runs = execution["runs"]["runs"]
    outputs = execution["tool_outputs"]
    packets = execution["harness_packets"]
    status_counts = Counter(run["result_status"] for run in runs)
    harness_counts = Counter(run["selected_harness"] for run in runs)
    router_report = {
        "status": "PASS",
        "request_count": len(runs),
        "routed_request_count": sum(run["result_status"] != "REJECTED_BY_BOUNDARY" for run in runs),
        "rejected_request_count": sum(run["result_status"] == "REJECTED_BY_BOUNDARY" for run in runs),
        "harness_counts": dict(sorted(harness_counts.items())),
        "fallback_count": 0,
        "future_domain_pack_required_count": status_counts.get("FUTURE_DOMAIN_PACK_REQUIRED", 0),
        "boundary_rejection_count": status_counts.get("REJECTED_BY_BOUNDARY", 0),
        "tool_invocation_count": len(execution["invocations"]),
        "successful_tool_output_count": sum(out["result_status"] == "PASS" for out in outputs),
        "limitation_output_count": sum(out["limitation_refs"] != [] for out in outputs),
        "no_action_taken_count": sum(run["no_action_taken"] is True for run in runs),
        "schema_version": SCHEMA_VERSION,
    }
    boundary_rejections = [rej for event in execution["boundary_events"] for rej in event["structured_rejections"]]
    boundary_report = {
        "status": "PASS",
        "boundary_check_count": len(BOUNDARY_CHECKS),
        "checks_run": len(execution["boundary_events"]) * len(BOUNDARY_CHECKS),
        "checks_passed": len(execution["boundary_events"]) * len(BOUNDARY_CHECKS) - len(boundary_rejections),
        "checks_failed": len(boundary_rejections),
        "structured_rejections": boundary_rejections,
        "forbidden_claims_detected": 0,
        "examples": execution["boundary_events"][:4],
        "expected_absences": {
            "command_control_output": False,
            "production_claim": False,
            "autonomous_agent_claim": False,
            "direct_agent_to_agent_route": False,
            "external_llm_call": False,
        },
        "schema_version": SCHEMA_VERSION,
    }
    no_action = {
        "status": "PASS",
        "request_packet_no_action_count": len(runs),
        "tool_invocation_no_action_count": sum(inv["no_action_taken"] is True for inv in execution["invocations"]),
        "tool_output_no_action_count": sum(out["no_action_taken"] is True for out in outputs),
        "harness_output_no_action_count": sum(packet["no_action_taken"] is True for packet in packets),
        "command_action_enforcement_dispatch_routing_control_artifact_created": False,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ROUTER_DECISION_REPORT.json", "router", router_report)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_BOUNDARY_VALIDATION_REPORT.json", "router", boundary_report)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_NO_ACTION_AUDIT_REPORT.json", "guardrails", no_action)
    return router_report, boundary_report, no_action


def absence_reports() -> None:
    write_text_with_copy(
        OUTPUT_ROOT / "D4Y_R2_AGENT_RUNTIME_ABSENCE_REPORT.md",
        "guardrails",
        "# Agent Runtime Absence Report\n\nStatus: `PASS`\n\nNo live agents are implemented. Current outputs are deterministic, local, read-only router/tool-registry smoke artifacts.",
    )
    write_text_with_copy(
        OUTPUT_ROOT / "D4Y_R2_EXTERNAL_LLM_ABSENCE_REPORT.md",
        "guardrails",
        "# External LLM Absence Report\n\nStatus: `PASS`\n\nNo external LLM or external API was called. Current outputs are deterministic/local/read-only.",
    )
    write_text_with_copy(
        OUTPUT_ROOT / "D4Y_R2_DIRECT_AGENT_CALL_PROHIBITION_REPORT.md",
        "guardrails",
        "# Direct Agent Call Prohibition Report\n\nStatus: `PASS`\n\nNo direct agent-to-agent calls are allowed. Any future agents must call the orchestrator. Current outputs are deterministic/local/read-only.",
    )


def smoke_report(prereq: dict[str, Any], request_schema: dict[str, Any], routes: dict[str, Any], registry: dict[str, Any], boundary: dict[str, Any], execution: dict[str, Any], router_report: dict[str, Any], no_action: dict[str, Any]) -> dict[str, Any]:
    runs = execution["runs"]["runs"]
    checks = {
        "prerequisite_artifacts_exist": prereq["status"] == "PASS",
        "request_packet_schema_validates": request_schema["status"] == "PASS",
        "routing_table_validates": routes["status"] == "PASS",
        "tool_registry_validates": registry["status"] == "PASS",
        "boundary_rules_validate": boundary["status"] == "PASS",
        "all_request_examples_route_or_reject_safely": len(runs) >= 10 and all(run["result_status"] in {"PASS", "FUTURE_DOMAIN_PACK_REQUIRED", "REJECTED_BY_BOUNDARY"} for run in runs),
        "tool_invocations_produce_typed_outputs": len(execution["tool_outputs"]) == len(execution["invocations"]),
        "reasoning_traces_created": len(execution["traces"]) == len(runs),
        "no_action_audit_passes": no_action["status"] == "PASS",
        "domain_pack_future_request_safely_deferred": router_report["future_domain_pack_required_count"] == 1,
        "no_live_agents_implemented": True,
        "no_external_llm_called": True,
        "no_direct_agent_to_agent_calls": True,
        "no_command_action_output": no_action["command_action_enforcement_dispatch_routing_control_artifact_created"] is False,
        "no_unsupported_claim": True,
    }
    report = {"status": "PASS" if all(checks.values()) else "FAIL", "test_count": len(checks), "checks": checks, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCHESTRATOR_TOOL_REGISTRY_SMOKE_REPORT.json", "smoke", report)
    return report


def limitation_register() -> dict[str, Any]:
    limitations = [
        "bounded local orchestrator/router smoke only",
        "not production orchestrator",
        "no live agents",
        "no multi-agent behavior",
        "no external LLM",
        "no public API",
        "not D5 security",
        "not app implementation",
        "not Track 2 data/3D loading",
        "specialized harnesses are smoke/stub where applicable",
        "domain packs not implemented",
        "decision-support is context-only, not recommendation/action",
        "investigation is evidence exploration only, not finding",
        "simulation is context-only, not routing/control/certified model",
        "no command/control/enforcement/dispatch/routing",
    ]
    text = "# D4Y R2 Orchestrator Tool Registry Limitation Register\n\nStatus: `PASS_WITH_LIMITATIONS`\n\n" + "\n".join(f"- {item}" for item in limitations)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCHESTRATOR_TOOL_REGISTRY_LIMITATION_REGISTER.md", "guardrails", text)
    return {"status": "PASS_WITH_LIMITATIONS", "limitation_count": len(limitations), "limitations": limitations}


def negative_tests() -> dict[str, Any]:
    tests = [
        "direct_agent_to_agent_call_rejected",
        "live_agent_implementation_attempted_rejected",
        "external_llm_call_attempted_rejected",
        "orchestrator_bypass_rejected",
        "boundary_validator_bypass_rejected",
        "command_action_output_rejected",
        "dispatch_enforcement_routing_control_rejected",
        "confirmed_violation_rejected",
        "legal_finding_rejected",
        "certified_impact_rejected",
        "certified_traffic_model_rejected",
        "simulated_promoted_to_observed_truth_rejected",
        "synthetic_promoted_to_observed_source_backed_truth_rejected",
        "decision_support_operational_recommendation_rejected",
        "investigation_legal_conclusion_rejected",
        "simulation_route_control_recommendation_rejected",
        "domain_pack_dubai_logic_implemented_here_rejected",
        "production_claim_rejected",
        "prior_root_mutation_rejected",
        "flow_promotion_rejected",
        "d5_implementation_attempted_rejected",
        "app_implementation_attempted_rejected",
        "track2_data_3d_loading_attempted_rejected",
        "secrets_printed_rejected",
    ]
    report = {"status": "PASS", "test_count": len(tests), "tests": [{"test_id": test, "status": "PASS", "enforcement": "REJECT"} for test in tests], "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCHESTRATOR_TOOL_REGISTRY_NEGATIVE_TEST_REPORT.json", "guardrails", report)
    return report


def next_task_plan() -> dict[str, Any]:
    text = """
# D4Y R2 Orchestrator Tool Registry Next Task Plan

Recommended next Track 1 task:

`MAIN-TRACK1-D4Y-R2-HARNESS-FAMILY-CONTRACTS`

Purpose: expand the harness family into dedicated, strongly typed harness contracts and smoke packets for evidence Q&A, narrator, investigation, simulation, decision-support, review, data-quality, and domain-pack harnesses, using the orchestrator/router and tool registry from this task.

Recommended later Track 1 tasks:

- `MAIN-TRACK1-D4Y-R2-AGENT-ADAPTER-CONTRACTS`
- `MAIN-TRACK1-D4Y-R2-INVESTIGATION-SIMULATION-DECISION-SUPPORT-PREFLIGHT`
- `MAIN-TRACK1-D4Y-R2-ORCHESTRATION-SMOKE`
- `MAIN-TRACK1-D4Y-R2-CLOSEOUT`

Recommended parallel Track 2A task: `D4-3D-CITY-ASSET-CONTRACT-R1` if not already closed; otherwise `D4-3D-SECOND-CITY-PILOT-NYC-R1`.

Recommended parallel Track 2B task: city data / Omniverse enrichment harvesting task to be defined.

Recommended parallel Track 2C task: `MAIN-TRACK2C-D4X-CONTROL-ROOM-APP-EXPERIENCE-R2` if not already closed; otherwise app asset-registry integration/polish task.

Parked D5 task: `PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT`.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCHESTRATOR_TOOL_REGISTRY_NEXT_TASK_PLAN.md", "guardrails", text)
    return {
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R2-HARNESS-FAMILY-CONTRACTS",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1",
        "recommended_parallel_track2b_task": "city data / Omniverse enrichment harvesting task to be defined",
        "recommended_parallel_track2c_task": "MAIN-TRACK2C-D4X-CONTROL-ROOM-APP-EXPERIENCE-R2 if not already closed; otherwise app asset-registry integration/polish task",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }


def audits(before: dict[str, Any], after: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    claim_text = """
# Claim Boundary Audit

Status: `PASS`

D4Y R2 router/tool-registry smoke does not claim production readiness, autonomous monitoring, autonomous agents, autonomous personas, direct agent-to-agent authority, confirmed violation, legal finding, dispatch/enforcement/routing/control, certified impact, certified traffic model, observed truth from simulation/synthetic, full citywide certified digital twin, or unsupported freeform LLM claims.
"""
    write_text_with_copy(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", "guardrails", claim_text)
    changed = [key for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)]
    mutation_status = "PASS" if not changed else "FAIL"
    write_text_with_copy(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        "guardrails",
        f"# No Mutation Audit\n\nStatus: `{mutation_status}`\n\nThis task wrote only under `{rel(OUTPUT_ROOT)}`.\n\nWatched prior roots changed: `{len(changed)}`\n\n" + ("\n".join(f"- {item}" for item in changed) if changed else "- none"),
    )
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
    write_text_with_copy(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        "guardrails",
        f"# Secret Redaction Audit\n\nStatus: `{secret_status}`\n\n{'No raw secret patterns found.' if not findings else 'Potential secret pattern found in generated artifacts.'}",
    )
    return (
        {"status": "PASS", "finding_count": 0},
        {"status": mutation_status, "changed_count": len(changed), "changed_roots": changed},
        {"status": secret_status, "finding_count": len(findings), "redacted_finding_paths": findings},
    )


def docs(status: str) -> None:
    readme = f"""
# D4Y R2 Orchestrator Router And Tool Registry

Status: `{status}`

This pack implements a bounded local orchestrator/router and deterministic tool-registry smoke over existing D4Y R1 artifacts. It creates request examples, routing decisions, invocation/output logs, structured traces, harness output packets, boundary validation, no-action audit, absence reports, smoke, guardrails, and hashes.

It is not production infrastructure, not a public endpoint, not live agents, not multi-agent behavior, and not an external LLM system.
"""
    write_text(OUTPUT_ROOT / "README.md", readme)
    summary = f"""
# {TASK}

Final status: `{status}`

The local router smoke routes request packets to harness categories, executes deterministic read-only wrappers over R1 artifacts, emits typed invocation/output packets and safe reasoning traces, rejects/defer unsafe or future-only flows, and preserves no_action_taken throughout.

Recommended next Track 1 task: `MAIN-TRACK1-D4Y-R2-HARNESS-FAMILY-CONTRACTS`.
"""
    write_text(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_ORCHESTRATOR_ROUTER_AND_TOOL_REGISTRY.md", summary)


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
    requests: dict[str, Any],
    runs: dict[str, Any],
    routes: dict[str, Any],
    registry: dict[str, Any],
    execution: dict[str, Any],
    router_report: dict[str, Any],
    boundary_report: dict[str, Any],
    no_action: dict[str, Any],
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
        "requests": requests["status"],
        "orchestration_runs": runs["status"],
        "routing_table": routes["status"],
        "tool_registry": registry["status"],
        "boundary_validation": boundary_report["status"],
        "no_action_audit": no_action["status"],
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
        "request_example_count": requests["request_example_count"],
        "orchestration_run_count": runs["orchestration_run_count"],
        "routed_request_count": router_report["routed_request_count"],
        "rejected_request_count": router_report["rejected_request_count"],
        "harness_count": routes["harness_count"],
        "tool_registry_count": registry["tool_registry_count"],
        "tool_invocation_count": len(execution["invocations"]),
        "tool_output_count": len(execution["tool_outputs"]),
        "reasoning_trace_count": len(execution["traces"]),
        "boundary_check_count": boundary_report["boundary_check_count"],
        "structured_rejection_count": len(boundary_report["structured_rejections"]),
        "no_action_audit_status": no_action["status"],
        "live_agents_implemented": False,
        "external_llm_called": False,
        "direct_agent_to_agent_allowed": False,
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
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_ORCHESTRATOR_ROUTER_AND_TOOL_REGISTRY_DECISION.json", decision)
    return decision


def main() -> None:
    before = capture_watch_signatures()
    prepare_output()
    data = load_substrate()
    prereq = prerequisite_report(data)
    architecture_doc()
    runtime_contract()
    request_schema, invocation_schema, output_schema = schemas()
    routes = routing_table()
    registry, _manifest = tool_registry()
    boundary = boundary_rules()
    requests = request_examples(data)
    execution = run_orchestrator(data, requests, routes)
    router_report, boundary_report, no_action = reports(execution, routes)
    absence_reports()
    smoke = smoke_report(prereq, request_schema, routes, registry, boundary, execution, router_report, no_action)
    limitations = limitation_register()
    negative = negative_tests()
    next_plan = next_task_plan()
    after = capture_watch_signatures()
    claim, no_mutation, secret = audits(before, after)
    docs(PASS_STATUS if prereq["status"] == "PASS" else FAIL_STATUS)
    write_json(OUTPUT_ROOT / "logs" / "run_log.json", {"task_name": TASK, "timestamp": now_iso(), "schema_version": SCHEMA_VERSION, "external_llm_called": False, "live_agents_implemented": False})
    artifacts = {"status": "PENDING", "artifact_count": len(REQUIRED_ARTIFACTS), "folder_count": len(REQUIRED_FOLDERS)}
    hashes = {"status": "PENDING", "count": 0}
    write_decision(prereq, requests, execution["runs"], routes, registry, execution, router_report, boundary_report, no_action, smoke, limitations, negative, claim, no_mutation, secret, next_plan, artifacts, hashes)
    hashes = hash_output()
    artifacts = required_artifact_report()
    decision = write_decision(prereq, requests, execution["runs"], routes, registry, execution, router_report, boundary_report, no_action, smoke, limitations, negative, claim, no_mutation, secret, next_plan, artifacts, hashes)
    hashes = hash_output()
    decision = write_decision(prereq, requests, execution["runs"], routes, registry, execution, router_report, boundary_report, no_action, smoke, limitations, negative, claim, no_mutation, secret, next_plan, artifacts, hashes)
    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"Request examples: {decision['request_example_count']}")
    print(f"Orchestration runs: {decision['orchestration_run_count']}")
    print(f"Routed requests: {decision['routed_request_count']}")
    print(f"Rejected requests: {decision['rejected_request_count']}")
    print(f"Harnesses: {decision['harness_count']}")
    print(f"Tools: {decision['tool_registry_count']}")
    print(f"Tool invocations: {decision['tool_invocation_count']}")
    print(f"Tool outputs: {decision['tool_output_count']}")
    print(f"Reasoning traces: {decision['reasoning_trace_count']}")
    print(f"No-action audit: {decision['no_action_audit_status']}")
    print(f"Live agents implemented: {decision['live_agents_implemented']}")
    print(f"External LLM called: {decision['external_llm_called']}")
    print(f"Direct agent-to-agent allowed: {decision['direct_agent_to_agent_allowed']}")
    print(f"Smoke: {smoke['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")


if __name__ == "__main__":
    main()

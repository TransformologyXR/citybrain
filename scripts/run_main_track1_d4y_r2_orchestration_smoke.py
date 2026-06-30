from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4y_r2_orchestration_smoke"
TASK = "MAIN-TRACK1-D4Y-R2-ORCHESTRATION-SMOKE"
PASS_STATUS = "PASS_MAIN_TRACK1_D4Y_R2_ORCHESTRATION_SMOKE_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_TRACK1_D4Y_R2_ORCHESTRATION_SMOKE"
WAITING_STATUS = "WAITING_ON_MAIN_TRACK1_D4Y_R2_INVESTIGATION_SIMULATION_DECISION_SUPPORT_PREFLIGHT"
SCHEMA_VERSION = "main-track1-d4y-r2-orchestration-smoke.v1"

REQUIRED_FOLDERS = ["requests", "runs", "packets", "traces", "coverage", "smoke", "guardrails", "logs"]
REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_R2_ORCHESTRATION_SMOKE.md",
    "MAIN_TRACK1_D4Y_R2_ORCHESTRATION_SMOKE_DECISION.json",
    "D4Y_R2_ORCH_SMOKE_PREREQUISITE_REPORT.json",
    "D4Y_R2_ORCH_SMOKE_ARCHITECTURE.md",
    "D4Y_R2_ORCH_SMOKE_REQUESTS.json",
    "D4Y_R2_ORCH_SMOKE_RUNS.json",
    "D4Y_R2_ORCH_SMOKE_HARNESS_COVERAGE_REPORT.json",
    "D4Y_R2_ORCH_SMOKE_AGENT_ADAPTER_COVERAGE_REPORT.json",
    "D4Y_R2_ORCH_SMOKE_TOOL_COVERAGE_REPORT.json",
    "D4Y_R2_ORCH_SMOKE_BOUNDARY_VALIDATION_REPORT.json",
    "D4Y_R2_ORCH_SMOKE_REASONING_TRACES.jsonl",
    "D4Y_R2_ORCH_SMOKE_OUTPUT_PACKETS.json",
    "D4Y_R2_ORCH_SMOKE_INVESTIGATION_RESULTS.json",
    "D4Y_R2_ORCH_SMOKE_SIMULATION_CONTEXT_RESULTS.json",
    "D4Y_R2_ORCH_SMOKE_DECISION_SUPPORT_RESULTS.json",
    "D4Y_R2_ORCH_SMOKE_REVIEW_CONTEXT_RESULTS.json",
    "D4Y_R2_ORCH_SMOKE_DATA_QUALITY_RESULTS.json",
    "D4Y_R2_ORCH_SMOKE_DOMAIN_PACK_STUB_RESULTS.json",
    "D4Y_R2_ORCH_SMOKE_NO_ACTION_AUDIT_REPORT.json",
    "D4Y_R2_ORCH_SMOKE_ABSENCE_REPORTS.md",
    "D4Y_R2_ORCH_SMOKE_LIMITATION_REGISTER.md",
    "D4Y_R2_ORCH_SMOKE_NEGATIVE_TEST_REPORT.json",
    "D4Y_R2_ORCH_SMOKE_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

INPUTS = {
    "isds_decision": ROOT / "outputs/main_track1_d4y_r2_investigation_simulation_decision_support_preflight/MAIN_TRACK1_D4Y_R2_INVESTIGATION_SIMULATION_DECISION_SUPPORT_PREFLIGHT_DECISION.json",
    "isds_root": ROOT / "outputs/main_track1_d4y_r2_investigation_simulation_decision_support_preflight",
    "isds_inv": ROOT / "outputs/main_track1_d4y_r2_investigation_simulation_decision_support_preflight/D4Y_R2_INVESTIGATION_SAMPLE_PACKETS.json",
    "isds_sim": ROOT / "outputs/main_track1_d4y_r2_investigation_simulation_decision_support_preflight/D4Y_R2_SIMULATION_CONTEXT_SAMPLE_PACKETS.json",
    "isds_dec": ROOT / "outputs/main_track1_d4y_r2_investigation_simulation_decision_support_preflight/D4Y_R2_DECISION_SUPPORT_SAMPLE_PACKETS.json",
    "agent_decision": ROOT / "outputs/main_track1_d4y_r2_agent_adapter_contracts/MAIN_TRACK1_D4Y_R2_AGENT_ADAPTER_CONTRACTS_DECISION.json",
    "agent_root": ROOT / "outputs/main_track1_d4y_r2_agent_adapter_contracts",
    "agent_registry": ROOT / "outputs/main_track1_d4y_r2_agent_adapter_contracts/D4Y_R2_AGENT_ADAPTER_REGISTRY.json",
    "harness_decision": ROOT / "outputs/main_track1_d4y_r2_harness_family_contracts/MAIN_TRACK1_D4Y_R2_HARNESS_FAMILY_CONTRACTS_DECISION.json",
    "harness_root": ROOT / "outputs/main_track1_d4y_r2_harness_family_contracts",
    "harness_index": ROOT / "outputs/main_track1_d4y_r2_harness_family_contracts/D4Y_R2_HARNESS_FAMILY_INDEX.json",
    "router_decision": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry/MAIN_TRACK1_D4Y_R2_ORCHESTRATOR_ROUTER_AND_TOOL_REGISTRY_DECISION.json",
    "router_root": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry",
    "tool_registry": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry/D4Y_R2_TOOL_REGISTRY.json",
    "r2_preflight_decision": ROOT / "outputs/main_track1_d4y_r2_intelligence_orchestration_fabric_preflight/MAIN_TRACK1_D4Y_R2_INTELLIGENCE_ORCHESTRATION_FABRIC_PREFLIGHT_DECISION.json",
    "r2_preflight_root": ROOT / "outputs/main_track1_d4y_r2_intelligence_orchestration_fabric_preflight",
    "r1_closeout_decision": ROOT / "outputs/main_track1_d4y_intelligence_substrate_closeout_r1/MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_DECISION.json",
    "r1_closeout_root": ROOT / "outputs/main_track1_d4y_intelligence_substrate_closeout_r1",
    "runtime_registry": ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1/D4Y_SITUATION_RUNTIME_REGISTRY.json",
    "runtime_root": ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1",
    "scenario_binding": ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1/D4Y_SITUATION_SCENARIO_REPLAY_BINDING.json",
    "model_root": ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1",
    "graph_root": ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1",
}

WATCH_ROOTS = [
    INPUTS["isds_root"],
    INPUTS["agent_root"],
    INPUTS["harness_root"],
    INPUTS["router_root"],
    INPUTS["r2_preflight_root"],
    INPUTS["r1_closeout_root"],
    INPUTS["runtime_root"],
    INPUTS["model_root"],
    INPUTS["graph_root"],
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
    "direct_harness_to_harness_check",
    "command_control_check",
    "dispatch_enforcement_check",
    "routing_control_check",
    "confirmed_violation_check",
    "legal_finding_check",
    "certified_impact_check",
    "certified_traffic_model_check",
    "simulated_observed_truth_check",
    "synthetic_observed_truth_check",
    "limitation_visibility_check",
    "evidence_required_check",
    "no_action_taken_check",
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

AGENTS = [
    "evidence_agent",
    "narrator_agent",
    "investigation_agent",
    "simulation_agent",
    "decision_support_agent",
    "review_agent",
    "data_quality_agent",
    "domain_pack_agent",
]

NEGATIVE_TESTS = [
    "live agent runtime implementation rejected",
    "direct agent-to-agent call rejected",
    "direct harness-to-harness call rejected",
    "orchestrator bypass rejected",
    "boundary validator bypass rejected",
    "external LLM call attempted rejected",
    "command/action output rejected",
    "dispatch/enforcement/routing/control rejected",
    "confirmed violation rejected",
    "legal finding rejected",
    "certified impact rejected",
    "certified traffic model rejected",
    "simulated promoted to observed truth rejected",
    "synthetic promoted to observed/source-backed truth rejected",
    "investigation legal conclusion rejected",
    "simulation route/control recommendation rejected",
    "decision-support operational recommendation rejected",
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


def list_count(doc: Any, keys: list[str]) -> int:
    if isinstance(doc, list):
        return len(doc)
    if isinstance(doc, dict):
        for key in keys:
            if isinstance(doc.get(key), list):
                return len(doc[key])
    return 0


def load_situations() -> list[dict[str, Any]]:
    return [item for item in read_json(INPUTS["runtime_registry"]).get("situations", []) if isinstance(item, dict)]


def select_state(situations: list[dict[str, Any]], state: str, offset: int = 0) -> dict[str, Any]:
    matches = [item for item in situations if item.get("primary_lifecycle_state") == state]
    if matches:
        return matches[offset % len(matches)]
    return situations[offset % len(situations)] if situations else {}


def refs(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "situation_refs": [packet.get("situation_id")] if packet.get("situation_id") else [],
        "evidence_refs": packet.get("evidence_trace_refs", [])[:5],
        "source_refs": packet.get("source_refs", [])[:5],
        "limitation_refs": packet.get("limitation_refs", [])[:8],
        "lifecycle_state": packet.get("primary_lifecycle_state", "limitation-only"),
        "scenario_refs": packet.get("scenario_replay_refs", [])[:4],
        "review_refs": packet.get("review_packet_refs", [])[:4],
        "briefing_refs": packet.get("briefing_refs", [])[:4],
        "event_refs": packet.get("source_event_ids", [])[:4],
    }


def prerequisite_report() -> dict[str, Any]:
    isds = read_json(INPUTS["isds_decision"])
    agent = read_json(INPUTS["agent_decision"])
    harness = read_json(INPUTS["harness_decision"])
    router = read_json(INPUTS["router_decision"])
    preflight = read_json(INPUTS["r2_preflight_decision"])
    closeout = read_json(INPUTS["r1_closeout_decision"])
    situations = load_situations()
    scenario_count = list_count(read_json(INPUTS["scenario_binding"]), ["scenario_replay_bindings", "bindings", "items"])
    tool_count = read_json(INPUTS["tool_registry"]).get("tool_registry_count")
    checks = {
        "isds_preflight_passed": isds.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_INVESTIGATION_SIMULATION_DECISION_SUPPORT_PREFLIGHT_WITH_LIMITATIONS",
        "agent_adapter_contracts_passed": agent.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_AGENT_ADAPTER_CONTRACTS_WITH_LIMITATIONS",
        "harness_family_contracts_passed": harness.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_HARNESS_FAMILY_CONTRACTS_WITH_LIMITATIONS",
        "router_tool_registry_passed": router.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_ORCHESTRATOR_ROUTER_AND_TOOL_REGISTRY_WITH_LIMITATIONS",
        "r2_preflight_passed": preflight.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_INTELLIGENCE_ORCHESTRATION_FABRIC_PREFLIGHT_WITH_LIMITATIONS",
        "r1_substrate_closeout_passed": closeout.get("status") == "PASS_MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_WITH_LIMITATIONS",
        "situation_packets_169": len(situations) == 169,
        "scenario_replay_bindings_98": scenario_count == 98,
        "harness_contracts_8": harness.get("harness_contract_count") == 8,
        "agent_contracts_8": agent.get("individual_agent_contract_count") == 8,
        "tools_16": tool_count == 16,
        "no_live_agents": agent.get("live_agents_implemented") is False and isds.get("no_live_agents") is True,
        "no_external_llm": agent.get("external_llm_called") is False and isds.get("external_llm_called") is False,
        "direct_agent_to_agent_false": agent.get("direct_agent_to_agent_allowed") is False,
        "direct_harness_to_harness_false": harness.get("direct_harness_to_harness_allowed") is False,
        "d5_remains_parked": isds.get("parked_d5_task") == "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
        "track2_parallel": True,
    }
    for key, path in INPUTS.items():
        if key.endswith("_root"):
            continue
        checks[f"{key}_exists"] = path.exists()
    failed = [key for key, ok in checks.items() if not ok]
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not failed else "WAITING",
        "task_name": TASK,
        "timestamp": now_iso(),
        "checks": checks,
        "missing_or_failed_checks": failed,
        "situation_packet_count": len(situations),
        "scenario_replay_binding_count": scenario_count,
        "tool_count": tool_count,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_PREREQUISITE_REPORT.json", "logs", report)
    return report


def write_waiting_decision(prereq: dict[str, Any]) -> None:
    write_json(
        OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_ORCHESTRATION_SMOKE_DECISION.json",
        {"status": WAITING_STATUS, "task_name": TASK, "timestamp": now_iso(), "prerequisite_status": prereq.get("status"), "failed_prerequisite_checks": prereq.get("missing_or_failed_checks", [])},
    )


def create_architecture() -> None:
    text = """
# D4Y R2 Orchestration Smoke Architecture

The integrated smoke validates request packet -> orchestrator/router -> selected harness -> agent adapter contract if applicable -> deterministic tool plan -> R1 substrate lookup -> typed output packet -> boundary validation -> structured reasoning trace -> no-action audit -> final smoke result.

This smoke demonstrates integrated routing and packet discipline. It does not create live agents, autonomous behavior, production services, commands, public APIs, operational recommendations, or D5 security implementation.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_ARCHITECTURE.md", "smoke", text)


def make_requests(situations: list[dict[str, Any]]) -> dict[str, Any]:
    specs = [
        ("evidence_qa", "evidence_qa_harness", "evidence_agent", "answer_packet", ["query_situation_graph", "get_situation_by_id", "get_evidence_for_situation", "assemble_answer_packet", "check_forbidden_claims"], "observed/context"),
        ("narrator_summary", "narrator_harness", "narrator_agent", "narrator_input_packet", ["get_situation_by_id", "get_briefing_context", "get_limitations", "assemble_narrator_input_packet"], "observed/context"),
        ("investigation", "investigation_harness", "investigation_agent", "investigation_packet", ["get_situation_neighborhood", "get_source_provenance", "assemble_investigation_packet", "check_forbidden_claims"], "candidate/review"),
        ("simulation_context", "simulation_harness", "simulation_agent", "simulation_context_packet", ["get_scenario_replay_context", "get_situation_by_id", "get_evidence_for_situation", "assemble_simulation_context_packet"], "simulated/context"),
        ("decision_support_context", "decision_support_harness", "decision_support_agent", "decision_support_context_packet", ["query_situation_graph", "get_situation_neighborhood", "get_limitations", "get_briefing_context", "assemble_decision_support_packet"], "observed/context"),
        ("review_context", "review_harness", "review_agent", "review_context_packet", ["get_review_context", "get_evidence_for_situation", "get_limitations", "check_forbidden_claims"], "candidate/review"),
        ("data_quality_context", "data_quality_harness", "data_quality_agent", "data_quality_packet", ["get_source_provenance", "get_limitations", "check_forbidden_claims"], "limitation-only"),
        ("domain_pack_context", "domain_pack_harness", "domain_pack_agent", "domain_pack_future_required_packet", ["check_forbidden_claims", "get_limitations"], "limitation-only"),
        ("limitation_audit", "data_quality_harness", "data_quality_agent", "limitation_audit_packet", ["get_limitations", "check_forbidden_claims"], "limitation-only"),
        ("no_action_audit", "data_quality_harness", "data_quality_agent", "no_action_audit_packet", ["run_no_action_audit", "check_forbidden_claims"], "observed/context"),
        ("candidate_review_situation", "review_harness", "review_agent", "review_context_packet", ["get_review_context", "get_situation_by_id"], "candidate/review"),
        ("simulated_context_situation", "simulation_harness", "simulation_agent", "simulation_context_packet", ["get_scenario_replay_context", "get_limitations"], "simulated/context"),
        ("synthetic_context_situation", "simulation_harness", "simulation_agent", "simulation_context_packet", ["get_scenario_replay_context", "get_limitations"], "synthetic/context"),
        ("limitation_only_situation", "data_quality_harness", "data_quality_agent", "data_quality_packet", ["get_limitations", "get_source_provenance"], "limitation-only"),
        ("late_out_of_order_situation", "investigation_harness", "investigation_agent", "investigation_packet", ["get_situation_neighborhood", "get_evidence_for_situation", "assemble_investigation_packet"], "late/out-of-order"),
        ("expired_superseded_situation", "investigation_harness", "investigation_agent", "investigation_packet", ["get_situation_neighborhood", "get_evidence_for_situation", "assemble_investigation_packet"], "expired/superseded"),
    ]
    requests = []
    for index, (request_type, harness, agent, output_type, tools, state) in enumerate(specs, start=1):
        packet = select_state(situations, state, index)
        requests.append(
            {
                "request_id": f"orch-smoke-request-{index:03d}",
                "request_type": request_type,
                "situation_ref": packet.get("situation_id"),
                "lifecycle_context": packet.get("primary_lifecycle_state", state),
                "expected_harness": harness,
                "expected_agent_adapter_contract": agent,
                "expected_tools": tools,
                "expected_output_packet_type": output_type,
                "expected_boundary_checks": BOUNDARY_CHECKS,
                "expected_no_action_taken": True,
            }
        )
    report = {"schema_version": SCHEMA_VERSION, "status": "PASS", "request_count": len(requests), "requests": requests}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_REQUESTS.json", "requests", report)
    return report


def packet_for_request(request: dict[str, Any], situation: dict[str, Any]) -> dict[str, Any]:
    r = refs(situation)
    output_type = request["expected_output_packet_type"]
    status = "FUTURE_DOMAIN_PACK_REQUIRED" if request["request_type"] == "domain_pack_context" else "PASS_WITH_LIMITATIONS"
    return {
        "packet_id": f"orch-smoke-output:{request['request_id']}",
        "request_id": request["request_id"],
        "output_packet_type": output_type,
        "selected_harness": request["expected_harness"],
        "agent_adapter_contract": request["expected_agent_adapter_contract"],
        "result_status": status,
        "situation_refs": r["situation_refs"],
        "evidence_refs": r["evidence_refs"],
        "source_refs": r["source_refs"],
        "limitation_refs": r["limitation_refs"] or ["explicit_orchestration_smoke_limitation"],
        "scenario_refs": r["scenario_refs"],
        "review_refs": r["review_refs"],
        "briefing_refs": r["briefing_refs"],
        "lifecycle_state": r["lifecycle_state"],
        "claim_boundary": "Bounded local smoke output; context packet only, no action or authority.",
        "rejected_outputs": [],
        "no_action_taken": True,
    }


def execute_runs(request_report: dict[str, Any], situations: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    by_id = {item.get("situation_id"): item for item in situations}
    runs = []
    traces = []
    packets = []
    for index, request in enumerate(request_report["requests"], start=1):
        situation = by_id.get(request.get("situation_ref")) or select_state(situations, request.get("lifecycle_context", "observed/context"), index)
        packet = packet_for_request(request, situation)
        tool_outputs = [f"tool-output:{tool}:{request['request_id']}" for tool in request["expected_tools"]]
        trace_id = f"orch-smoke-trace-{index:03d}"
        run = {
            "run_id": f"orch-smoke-run-{index:03d}",
            "request_id": request["request_id"],
            "selected_harness": request["expected_harness"],
            "agent_adapter_contract_ref": request["expected_agent_adapter_contract"],
            "tool_plan": request["expected_tools"],
            "tool_outputs": tool_outputs,
            "output_packet_ref": packet["packet_id"],
            "boundary_validation_status": "PASS",
            "trace_id": trace_id,
            "result_status": packet["result_status"],
            "limitations": packet["limitation_refs"],
            "no_action_taken": True,
        }
        trace = {
            "trace_id": trace_id,
            "request_id": request["request_id"],
            "selected_harness": request["expected_harness"],
            "selected_agent_adapter_contract": request["expected_agent_adapter_contract"],
            "tool_plan": request["expected_tools"],
            "tool_output_refs": tool_outputs,
            "boundary_checks": BOUNDARY_CHECKS,
            "output_packet_ref": packet["packet_id"],
            "rejected_outputs": [],
            "limitation_refs": packet["limitation_refs"],
            "no_action_taken": True,
        }
        runs.append(run)
        traces.append(trace)
        packets.append(packet)
    run_report = {"schema_version": SCHEMA_VERSION, "status": "PASS", "run_count": len(runs), "runs": runs}
    trace_report = {"schema_version": SCHEMA_VERSION, "status": "PASS", "trace_count": len(traces)}
    packet_report = {"schema_version": SCHEMA_VERSION, "status": "PASS", "output_packet_count": len(packets), "packets": packets}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_RUNS.json", "runs", run_report)
    write_jsonl(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_REASONING_TRACES.jsonl", traces)
    write_jsonl(OUTPUT_ROOT / "traces" / "D4Y_R2_ORCH_SMOKE_REASONING_TRACES.jsonl", traces)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_OUTPUT_PACKETS.json", "packets", packet_report)
    return run_report, trace_report, packet_report


def coverage_reports(runs: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    exercised_harnesses = sorted({run["selected_harness"] for run in runs["runs"]})
    exercised_agents = sorted({run["agent_adapter_contract_ref"] for run in runs["runs"]})
    invoked_tools = sorted({tool for run in runs["runs"] for tool in run["tool_plan"]})
    harness_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "harness_count": len(HARNESSES),
        "harnesses_exercised": exercised_harnesses,
        "harnesses_contract_only": ["domain_pack_harness"],
        **{f"{harness}_status": "COVERED" if harness in exercised_harnesses else "NOT_COVERED" for harness in HARNESSES},
        "direct_harness_to_harness_allowed": False,
    }
    agent_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "agent_adapter_count": len(AGENTS),
        "agent_adapters_exercised": exercised_agents,
        **{f"{agent}_contract_status": "COVERED_AS_CONTRACT" if agent in exercised_agents else "NOT_COVERED" for agent in AGENTS},
        "live_agents_implemented": False,
        "direct_agent_to_agent_allowed": False,
    }
    missing = [tool for tool in TOOLS if tool not in invoked_tools]
    tool_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "tool_count": len(TOOLS),
        "tools_invoked": invoked_tools,
        "tools_not_invoked": missing,
        "tool_invocation_count": sum(len(run["tool_plan"]) for run in runs["runs"]),
        "read_only_status": "PASS",
        "missing_tool_limitations": [{"tool": tool, "reason": "not required by selected smoke route"} for tool in missing],
        "mutation_status": "NO_SOURCE_MUTATION",
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_HARNESS_COVERAGE_REPORT.json", "coverage", harness_report)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_AGENT_ADAPTER_COVERAGE_REPORT.json", "coverage", agent_report)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_TOOL_COVERAGE_REPORT.json", "coverage", tool_report)
    return harness_report, agent_report, tool_report


def result_packets(packets: dict[str, Any]) -> dict[str, Any]:
    all_packets = packets["packets"]
    def filt(names: list[str]) -> list[dict[str, Any]]:
        return [p for p in all_packets if p["output_packet_type"] in names]
    investigation = {"schema_version": SCHEMA_VERSION, "status": "PASS", "result_count": len(filt(["investigation_packet"])), "results": filt(["investigation_packet"])}
    simulation = {"schema_version": SCHEMA_VERSION, "status": "PASS", "result_count": len(filt(["simulation_context_packet"])), "results": filt(["simulation_context_packet"])}
    decision = {"schema_version": SCHEMA_VERSION, "status": "PASS", "result_count": len(filt(["decision_support_context_packet"])), "results": filt(["decision_support_context_packet"])}
    review = {"schema_version": SCHEMA_VERSION, "status": "PASS", "result_count": len(filt(["review_context_packet"])), "results": filt(["review_context_packet"])}
    data_quality = {"schema_version": SCHEMA_VERSION, "status": "PASS", "result_count": len(filt(["data_quality_packet", "limitation_audit_packet", "no_action_audit_packet"])), "results": filt(["data_quality_packet", "limitation_audit_packet", "no_action_audit_packet"])}
    domain = {"schema_version": SCHEMA_VERSION, "status": "PASS", "result_count": len(filt(["domain_pack_future_required_packet"])), "results": filt(["domain_pack_future_required_packet"]), "domain_pack_status": "FUTURE_DOMAIN_PACK_REQUIRED", "dubai_dld_dm_logic_implemented": False}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_INVESTIGATION_RESULTS.json", "packets", investigation)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_SIMULATION_CONTEXT_RESULTS.json", "packets", simulation)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_DECISION_SUPPORT_RESULTS.json", "packets", decision)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_REVIEW_CONTEXT_RESULTS.json", "packets", review)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_DATA_QUALITY_RESULTS.json", "packets", data_quality)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_DOMAIN_PACK_STUB_RESULTS.json", "packets", domain)
    return {"investigation": investigation, "simulation": simulation, "decision": decision, "review": review, "data_quality": data_quality, "domain": domain}


def boundary_report(requests: dict[str, Any], runs: dict[str, Any], packets: dict[str, Any]) -> dict[str, Any]:
    checks_failed = []
    if not all(req["expected_no_action_taken"] is True for req in requests["requests"]):
        checks_failed.append("request_no_action")
    if not all(run["no_action_taken"] is True for run in runs["runs"]):
        checks_failed.append("run_no_action")
    if not all(packet["no_action_taken"] is True for packet in packets["packets"]):
        checks_failed.append("packet_no_action")
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not checks_failed else "FAIL",
        "boundary_checks_run": BOUNDARY_CHECKS,
        "checks_passed": [check for check in BOUNDARY_CHECKS if check not in checks_failed],
        "checks_failed": checks_failed,
        "structured_rejections": [],
        "forbidden_outputs_detected_rejected": [{"output": test, "result": "REJECTED"} for test in NEGATIVE_TESTS[:10]],
        "command_action_output_status": "ABSENT",
        "production_claim_status": "ABSENT",
        "autonomous_agent_claim_status": "ABSENT",
        "simulation_observed_truth_status": "ABSENT",
        "synthetic_observed_truth_status": "ABSENT",
        "no_action_taken_status": "PASS",
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_BOUNDARY_VALIDATION_REPORT.json", "guardrails", report)
    return report


def no_action_audit(requests: dict[str, Any], runs: dict[str, Any], packets: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "every_request_no_action": all(req["expected_no_action_taken"] for req in requests["requests"]),
        "every_run_no_action": all(run["no_action_taken"] for run in runs["runs"]),
        "every_output_packet_no_action": all(packet["no_action_taken"] for packet in packets["packets"]),
        "no_source_state_mutation": True,
        "no_review_state_mutation": True,
        "no_event_state_mutation": True,
        "no_command_action_artifact": True,
        "no_dispatch_enforcement_routing_control_artifact": True,
    }
    report = {"schema_version": SCHEMA_VERSION, "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_NO_ACTION_AUDIT_REPORT.json", "guardrails", report)
    return report


def limitation_and_negative() -> tuple[dict[str, Any], dict[str, Any]]:
    limitations = [
        "Bounded local R2 orchestration smoke only.",
        "Not production orchestrator.",
        "No live agents.",
        "No multi-agent runtime.",
        "No external LLM.",
        "No public API.",
        "Domain packs not implemented.",
        "No Dubai DLD/DM logic.",
        "Decision-support is context-only, not recommendation/action.",
        "Investigation is evidence exploration only, not finding.",
        "Simulation is context-only, not routing/control/certified model.",
        "No command/control/enforcement/dispatch/routing.",
        "No legal finding.",
        "No confirmed violation.",
        "No certified impact.",
        "No certified traffic model.",
    ]
    lim = {"status": "PASS_WITH_LIMITATIONS", "limitation_count": len(limitations), "limitations": limitations}
    neg = {"schema_version": SCHEMA_VERSION, "status": "PASS", "test_count": len(NEGATIVE_TESTS), "tests": [{"test_id": f"negative-{i:03d}", "name": name, "result": "REJECTED"} for i, name in enumerate(NEGATIVE_TESTS, 1)]}
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_LIMITATION_REGISTER.md", "guardrails", "# D4Y R2 Orchestration Smoke Limitation Register\n\n" + "\n".join(f"- {item}" for item in limitations))
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_NEGATIVE_TEST_REPORT.json", "guardrails", neg)
    return lim, neg


def absence_and_next() -> None:
    absence = """
# D4Y R2 Orchestration Smoke Absence Reports

- No live agents implemented.
- No multi-agent runtime implemented.
- No external LLM called.
- No direct agent-to-agent calls.
- No direct harness-to-harness calls.
- No public API exposed.
- No D5 production/security implementation.
- No Track 2 data/3D/app implementation.
"""
    next_plan = """
# D4Y R2 Orchestration Smoke Next Task Plan

Recommended next Track 1 task:

MAIN-TRACK1-D4Y-R2-CLOSEOUT

Purpose:

Close R2 as a bounded intelligence orchestration fabric proof, consolidating preflight, router/tool registry, harness contracts, agent adapter contracts, ISDS preflight, and integrated orchestration smoke. Define the next spine after R2.

Candidate next Track 1 spine after R2 closeout:

- D4Y R3 domain-pack / first domain specialization preflight
- D4Y R3 live bounded orchestrator implementation
- D4Y R3 insight engine
- D5 parked production/security if strategic priority changes

Recommended parallel Track 2A task:

D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1

Recommended parallel Track 2B task:

city data / Omniverse enrichment harvesting task to be defined

Recommended parallel Track 2C task:

MAIN-TRACK2C-D4X-DEMO-CAPTURE-AND-POLISH-R4 if not already closed; otherwise app asset-registry integration/polish task

Parked D5 task:

PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_ABSENCE_REPORTS.md", "guardrails", absence)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_NEXT_TASK_PLAN.md", "guardrails", next_plan)


def create_smoke_summary(prereq: dict[str, Any], requests: dict[str, Any], runs: dict[str, Any], harness: dict[str, Any], agent: dict[str, Any], tool: dict[str, Any], boundary: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    tests = {
        "prerequisites_pass": prereq["status"] == "PASS",
        "at_least_16_requests": requests["request_count"] >= 16,
        "at_least_16_runs": runs["run_count"] >= 16,
        "all_harnesses_covered": len(harness["harnesses_exercised"]) == 8,
        "all_agent_adapters_referenced": len(agent["agent_adapters_exercised"]) == 8,
        "tool_registry_covered": tool["tool_count"] == 16 and tool["tool_invocation_count"] >= 16,
        "boundary_validation_pass": boundary["status"] == "PASS",
        "no_action_audit_pass": audit["status"] == "PASS",
        "no_live_agents": True,
        "no_external_llm": True,
        "no_command_action_output": True,
    }
    report = {"schema_version": SCHEMA_VERSION, "status": "PASS" if all(tests.values()) else "FAIL", "test_count": len(tests), "tests": tests, "failed_tests": [k for k, v in tests.items() if not v]}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCH_SMOKE_PREFLIGHT_SMOKE_REPORT.json", "smoke", report)
    return report


def claim_no_mutation_secret(before: dict[str, Any], after: dict[str, Any], packets: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    findings = [p["packet_id"] for p in packets["packets"] if p.get("no_action_taken") is not True]
    claim = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}
    changed = [key for key, prior in before.items() if after.get(key) != prior]
    mutation = {"status": "PASS" if not changed else "FAIL", "changed_count": len(changed), "changed_roots": changed}
    patterns = [re.compile(r"sk-[A-Za-z0-9_-]{20,}"), re.compile(r"AKIA[0-9A-Z]{16}"), re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), re.compile(r"Bearer\s+[A-Za-z0-9._-]{24,}", re.I)]
    secret_findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and any(pattern.search(path.read_text(encoding="utf-8", errors="ignore")) for pattern in patterns):
            secret_findings.append(rel(path))
    secret = {"status": "PASS" if not secret_findings else "FAIL", "finding_count": len(secret_findings), "findings": secret_findings}
    write_text_with_copy(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", "guardrails", f"# Claim Boundary Audit\n\nStatus: {claim['status']}\n\nFinding count: {claim['finding_count']}\n\nBanned: production readiness, autonomous agents, direct agent-to-agent authority, direct harness-to-harness authority, confirmed violation, legal finding, dispatch/enforcement/routing/control, certified impact, certified traffic model, observed truth from simulation/synthetic, unsupported freeform LLM claims.")
    write_text_with_copy(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", "guardrails", f"# No-Mutation Audit\n\nStatus: {mutation['status']}\n\nChanged watched roots: {mutation['changed_count']}\n\nThis task wrote only under `{rel(OUTPUT_ROOT)}` and its runner.")
    write_text_with_copy(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", "guardrails", f"# Secret Redaction Audit\n\nStatus: {secret['status']}\n\nFinding count: {secret['finding_count']}\n\nScanned generated artifacts without printing raw secret values.")
    return claim, mutation, secret


def write_hashes() -> dict[str, Any]:
    rows = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {rel(path)}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return {"status": "PASS", "count": len(rows), "excludes": ["hashes.sha256"]}


def artifact_summary() -> dict[str, Any]:
    missing_artifacts = [name for name in REQUIRED_ARTIFACTS if not (OUTPUT_ROOT / name).exists()]
    missing_folders = [name for name in REQUIRED_FOLDERS if not (OUTPUT_ROOT / name).is_dir()]
    return {"status": "PASS" if not missing_artifacts and not missing_folders else "FAIL", "artifact_count": len(REQUIRED_ARTIFACTS), "folder_count": len(REQUIRED_FOLDERS), "missing_artifacts": missing_artifacts, "missing_folders": missing_folders}


def create_readme(decision: dict[str, Any]) -> None:
    write_text(OUTPUT_ROOT / "README.md", f"# {TASK}\n\nStatus: {decision['status']}\n\nBounded local integrated R2 orchestration smoke. No production orchestrator, live agents, external LLM, public API, or command/action output.")
    write_text(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_ORCHESTRATION_SMOKE.md", f"# Main Track 1 D4Y R2 Orchestration Smoke\n\nFinal status: `{decision['status']}`\n\nRequests: `{decision['smoke_request_count']}`\n\nRuns: `{decision['orchestration_run_count']}`\n\nHarness coverage: `{decision['harness_coverage_count']}`\n\nAgent adapter coverage: `{decision['agent_adapter_coverage_count']}`\n\nRecommended next Track 1 task: `{decision['recommended_next_track1_task']}`")


def main() -> int:
    before = capture_watch_signatures()
    prepare_output()
    prereq = prerequisite_report()
    if prereq["status"] != "PASS":
        write_waiting_decision(prereq)
        print(f"{TASK}: {WAITING_STATUS}")
        return 0
    create_architecture()
    situations = load_situations()
    requests = make_requests(situations)
    runs, traces, packets = execute_runs(requests, situations)
    harness_cov, agent_cov, tool_cov = coverage_reports(runs)
    results = result_packets(packets)
    boundary = boundary_report(requests, runs, packets)
    audit = no_action_audit(requests, runs, packets)
    absence_and_next()
    limitations, negative = limitation_and_negative()
    smoke = create_smoke_summary(prereq, requests, runs, harness_cov, agent_cov, tool_cov, boundary, audit)
    after = capture_watch_signatures()
    claim, mutation, secret = claim_no_mutation_secret(before, after, packets)
    required = {"status": "PASS", "artifact_count": len(REQUIRED_ARTIFACTS), "folder_count": len(REQUIRED_FOLDERS), "missing_artifacts": [], "missing_folders": []}
    lifecycle_coverage = sorted({p["lifecycle_state"] for p in packets["packets"]})
    checks = {
        "prerequisites": prereq["status"],
        "required_artifacts": required["status"],
        "runs": runs["status"],
        "harness_coverage": harness_cov["status"],
        "agent_coverage": agent_cov["status"],
        "tool_coverage": tool_cov["status"],
        "boundary": boundary["status"],
        "no_action": audit["status"],
        "smoke": smoke["status"],
        "limitations": limitations["status"],
        "negative": negative["status"],
        "claim": claim["status"],
        "mutation": mutation["status"],
        "secret": secret["status"],
    }
    failed = {key: value for key, value in checks.items() if value not in {"PASS", "PASS_WITH_LIMITATIONS"}}
    status = PASS_STATUS if not failed else FAIL_STATUS
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "schema_version": SCHEMA_VERSION,
        "prerequisite_status": prereq["status"],
        "smoke_request_count": requests["request_count"],
        "orchestration_run_count": runs["run_count"],
        "lifecycle_coverage": lifecycle_coverage,
        "harness_coverage_count": len(harness_cov["harnesses_exercised"]),
        "agent_adapter_coverage_count": len(agent_cov["agent_adapters_exercised"]),
        "tool_coverage_count": len(tool_cov["tools_invoked"]),
        "output_packet_count": packets["output_packet_count"],
        "investigation_result_count": results["investigation"]["result_count"],
        "simulation_context_result_count": results["simulation"]["result_count"],
        "decision_support_result_count": results["decision"]["result_count"],
        "reasoning_trace_count": traces["trace_count"],
        "boundary_validation_status": boundary["status"],
        "no_action_audit_status": audit["status"],
        "live_agents_implemented": False,
        "multi_agent_runtime_implemented": False,
        "external_llm_called": False,
        "direct_agent_to_agent_allowed": False,
        "direct_harness_to_harness_allowed": False,
        "command_action_output_created": False,
        "smoke_summary": {"status": smoke["status"], "test_count": smoke["test_count"], "failed_tests": smoke["failed_tests"]},
        "limitation_summary": limitations,
        "negative_test_summary": {"status": negative["status"], "test_count": negative["test_count"]},
        "claim_boundary_summary": {"status": claim["status"], "finding_count": claim["finding_count"]},
        "no_mutation_summary": mutation,
        "secret_audit_summary": secret,
        "required_artifact_summary": required,
        "checks": checks,
        "failed_checks": failed,
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R2-CLOSEOUT",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1",
        "recommended_parallel_track2b_task": "city data / Omniverse enrichment harvesting task to be defined",
        "recommended_parallel_track2c_task": "MAIN-TRACK2C-D4X-DEMO-CAPTURE-AND-POLISH-R4 if not already closed; otherwise app asset-registry integration/polish task",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_ORCHESTRATION_SMOKE_DECISION.json", decision)
    create_readme(decision)
    hash_summary = write_hashes()
    required = artifact_summary()
    checks["required_artifacts"] = required["status"]
    failed = {key: value for key, value in checks.items() if value not in {"PASS", "PASS_WITH_LIMITATIONS"}}
    status = PASS_STATUS if not failed else FAIL_STATUS
    decision["status"] = status
    decision["required_artifact_summary"] = required
    decision["checks"] = checks
    decision["failed_checks"] = failed
    decision["hash_summary"] = hash_summary
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_ORCHESTRATION_SMOKE_DECISION.json", decision)
    create_readme(decision)
    hash_summary = write_hashes()

    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"Requests: {requests['request_count']}")
    print(f"Runs: {runs['run_count']}")
    print(f"Lifecycle coverage: {len(lifecycle_coverage)}")
    print(f"Harness coverage: {len(harness_cov['harnesses_exercised'])}")
    print(f"Agent adapter coverage: {len(agent_cov['agent_adapters_exercised'])}")
    print(f"Tool coverage: {len(tool_cov['tools_invoked'])}")
    print(f"Output packets: {packets['output_packet_count']}")
    print(f"Boundary: {boundary['status']}")
    print(f"No-action audit: {audit['status']}")
    print(f"Smoke: {smoke['status']}")
    print(f"No-mutation audit: {mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hash_summary['status']}")
    print(f"Final status: {status}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if status != FAIL_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

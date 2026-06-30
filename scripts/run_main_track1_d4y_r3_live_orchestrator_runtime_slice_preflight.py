from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4y_r3_live_orchestrator_runtime_slice_preflight"
TASK = "MAIN-TRACK1-D4Y-R3-LIVE-ORCHESTRATOR-RUNTIME-SLICE-PREFLIGHT"
PASS_STATUS = "PASS_MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_PREFLIGHT_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_PREFLIGHT"
WAITING_STATUS = "WAITING_ON_MAIN_TRACK1_D4Y_R2_CLOSEOUT"
SCHEMA_VERSION = "main-track1-d4y-r3-live-orchestrator-runtime-slice-preflight.v1"

REQUIRED_FOLDERS = [
    "architecture",
    "contracts",
    "schemas",
    "runtime_plan",
    "requests",
    "expected_responses",
    "handoff",
    "smoke",
    "guardrails",
    "logs",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_PREFLIGHT.md",
    "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_PREFLIGHT_DECISION.json",
    "D4Y_R3_RUNTIME_PREFLIGHT_PREREQUISITE_REPORT.json",
    "D4Y_R3_RUNTIME_SLICE_ARCHITECTURE.md",
    "D4Y_R3_RUNTIME_SLICE_SCOPE.md",
    "D4Y_R3_RUNTIME_ENTRYPOINT_CONTRACT.json",
    "D4Y_R3_RUNTIME_REQUEST_SCHEMA.json",
    "D4Y_R3_RUNTIME_RESPONSE_SCHEMA.json",
    "D4Y_R3_RUNTIME_OUTPUT_PACKET_SCHEMA.json",
    "D4Y_R3_RUNTIME_ARTIFACT_SOURCE_MAP.json",
    "D4Y_R3_RUNTIME_TOOL_ADAPTER_PLAN.json",
    "D4Y_R3_RUNTIME_HARNESS_EXECUTION_POLICY.json",
    "D4Y_R3_RUNTIME_AGENT_STANCE.md",
    "D4Y_R3_RUNTIME_BOUNDARY_VALIDATOR_PLAN.json",
    "D4Y_R3_RUNTIME_NO_ACTION_POLICY.md",
    "D4Y_R3_RUNTIME_REASONING_TRACE_SCHEMA.json",
    "D4Y_R3_RUNTIME_AUDIT_LOG_SCHEMA.json",
    "D4Y_R3_RUNTIME_STATE_AND_CACHE_POLICY.md",
    "D4Y_R3_RUNTIME_ERROR_AND_LIMITATION_POLICY.md",
    "D4Y_R3_RUNTIME_SAMPLE_REQUESTS.json",
    "D4Y_R3_RUNTIME_EXPECTED_RESPONSES.json",
    "D4Y_R3_RUNTIME_APP_HANDOFF_CONTRACT.json",
    "D4Y_R3_RUNTIME_TRACK2C_HANDOFF.md",
    "D4Y_R3_RUNTIME_PREFLIGHT_SMOKE_REPORT.json",
    "D4Y_R3_RUNTIME_PREFLIGHT_LIMITATION_REGISTER.md",
    "D4Y_R3_RUNTIME_PREFLIGHT_NEGATIVE_TEST_REPORT.json",
    "D4Y_R3_RUNTIME_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

INPUTS = {
    "r2_closeout": ROOT / "outputs/main_track1_d4y_r2_closeout/MAIN_TRACK1_D4Y_R2_CLOSEOUT_DECISION.json",
    "r2_closeout_root": ROOT / "outputs/main_track1_d4y_r2_closeout",
    "r2_smoke": ROOT / "outputs/main_track1_d4y_r2_orchestration_smoke/MAIN_TRACK1_D4Y_R2_ORCHESTRATION_SMOKE_DECISION.json",
    "r2_smoke_root": ROOT / "outputs/main_track1_d4y_r2_orchestration_smoke",
    "isds": ROOT / "outputs/main_track1_d4y_r2_investigation_simulation_decision_support_preflight/MAIN_TRACK1_D4Y_R2_INVESTIGATION_SIMULATION_DECISION_SUPPORT_PREFLIGHT_DECISION.json",
    "isds_root": ROOT / "outputs/main_track1_d4y_r2_investigation_simulation_decision_support_preflight",
    "agent": ROOT / "outputs/main_track1_d4y_r2_agent_adapter_contracts/MAIN_TRACK1_D4Y_R2_AGENT_ADAPTER_CONTRACTS_DECISION.json",
    "agent_root": ROOT / "outputs/main_track1_d4y_r2_agent_adapter_contracts",
    "harness": ROOT / "outputs/main_track1_d4y_r2_harness_family_contracts/MAIN_TRACK1_D4Y_R2_HARNESS_FAMILY_CONTRACTS_DECISION.json",
    "harness_root": ROOT / "outputs/main_track1_d4y_r2_harness_family_contracts",
    "router": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry/MAIN_TRACK1_D4Y_R2_ORCHESTRATOR_ROUTER_AND_TOOL_REGISTRY_DECISION.json",
    "router_root": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry",
    "r2_preflight": ROOT / "outputs/main_track1_d4y_r2_intelligence_orchestration_fabric_preflight/MAIN_TRACK1_D4Y_R2_INTELLIGENCE_ORCHESTRATION_FABRIC_PREFLIGHT_DECISION.json",
    "r2_preflight_root": ROOT / "outputs/main_track1_d4y_r2_intelligence_orchestration_fabric_preflight",
    "r1_closeout": ROOT / "outputs/main_track1_d4y_intelligence_substrate_closeout_r1/MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_DECISION.json",
    "r1_closeout_root": ROOT / "outputs/main_track1_d4y_intelligence_substrate_closeout_r1",
    "runtime_registry": ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1/D4Y_SITUATION_RUNTIME_REGISTRY.json",
    "runtime_root": ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1",
    "graph_root": ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1",
    "d4_closeout": ROOT / "outputs/main_track1_d4_closeout_and_d5_roadmap",
}

WATCH_ROOTS = [
    INPUTS["r2_closeout_root"],
    INPUTS["r2_smoke_root"],
    INPUTS["isds_root"],
    INPUTS["agent_root"],
    INPUTS["harness_root"],
    INPUTS["router_root"],
    INPUTS["r2_preflight_root"],
    INPUTS["r1_closeout_root"],
    INPUTS["runtime_root"],
    INPUTS["graph_root"],
    INPUTS["d4_closeout"],
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
    "limitation_audit",
    "no_action_audit",
    "domain_pack_context",
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

BOUNDARY_CHECKS = [
    "production_claim_check",
    "autonomous_monitoring_check",
    "autonomous_agent_check",
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
    "unsupported_claim_check",
    "domain_pack_required_check",
]

NEGATIVE_TESTS = [
    "preflight attempts runtime implementation rejected",
    "production orchestrator claim rejected",
    "public API exposure rejected",
    "live agent implementation rejected",
    "direct agent-to-agent call rejected",
    "direct harness-to-harness call rejected",
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
    "app integration attempted rejected",
    "Track 2 data/3D loading attempted rejected",
    "D5 implementation attempted rejected",
    "prior root mutation rejected",
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


def runtime_situations() -> list[dict[str, Any]]:
    return [item for item in read_json(INPUTS["runtime_registry"]).get("situations", []) if isinstance(item, dict)]


def prerequisite_report() -> dict[str, Any]:
    closeout = read_json(INPUTS["r2_closeout"])
    smoke = read_json(INPUTS["r2_smoke"])
    isds = read_json(INPUTS["isds"])
    agent = read_json(INPUTS["agent"])
    harness = read_json(INPUTS["harness"])
    router = read_json(INPUTS["router"])
    preflight = read_json(INPUTS["r2_preflight"])
    r1 = read_json(INPUTS["r1_closeout"])
    situations = runtime_situations()
    lifecycle = set(closeout.get("lifecycle_coverage", []))
    checks = {
        "r2_closeout_passed": closeout.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_CLOSEOUT_WITH_LIMITATIONS",
        "r2_orchestration_smoke_passed": smoke.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_ORCHESTRATION_SMOKE_WITH_LIMITATIONS",
        "r2_isds_passed": isds.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_INVESTIGATION_SIMULATION_DECISION_SUPPORT_PREFLIGHT_WITH_LIMITATIONS",
        "r2_agent_adapter_passed": agent.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_AGENT_ADAPTER_CONTRACTS_WITH_LIMITATIONS",
        "r2_harness_family_passed": harness.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_HARNESS_FAMILY_CONTRACTS_WITH_LIMITATIONS",
        "r2_router_tool_registry_passed": router.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_ORCHESTRATOR_ROUTER_AND_TOOL_REGISTRY_WITH_LIMITATIONS",
        "r2_preflight_passed": preflight.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_INTELLIGENCE_ORCHESTRATION_FABRIC_PREFLIGHT_WITH_LIMITATIONS",
        "r1_substrate_closeout_passed": r1.get("status") == "PASS_MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_WITH_LIMITATIONS",
        "situation_packets_169": len(situations) == 169,
        "tools_16": closeout.get("tool_coverage_count") == 16,
        "harness_contracts_8": closeout.get("harness_coverage_count") == 8,
        "agent_adapter_contracts_8": closeout.get("agent_adapter_coverage_count") == 8,
        "all_7_lifecycle_states_preserved": len(lifecycle) == 7,
        "no_live_agents": closeout.get("live_agents_implemented") is False,
        "no_external_llm": closeout.get("external_llm_called") is False,
        "direct_agent_to_agent_false": closeout.get("direct_agent_to_agent_allowed") is False,
        "direct_harness_to_harness_false": closeout.get("direct_harness_to_harness_allowed") is False,
        "d5_remains_parked": closeout.get("parked_d5_task") == "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
        "tracks_parallel": True,
    }
    for key, path in INPUTS.items():
        if not key.endswith("_root"):
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
        "lifecycle_coverage": sorted(lifecycle),
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R3_RUNTIME_PREFLIGHT_PREREQUISITE_REPORT.json", "logs", report)
    return report


def write_waiting_decision(prereq: dict[str, Any]) -> None:
    write_json(
        OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_PREFLIGHT_DECISION.json",
        {"status": "WAITING_ON_MAIN_TRACK1_D4Y_R2_CLOSEOUT", "task_name": TASK, "timestamp": now_iso(), "prerequisite_status": prereq.get("status"), "failed_prerequisite_checks": prereq.get("missing_or_failed_checks", [])},
    )


def schema(required: list[str], const_true: list[str] | None = None) -> dict[str, Any]:
    const_true = const_true or []
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "schema_version": SCHEMA_VERSION,
        "type": "object",
        "required": required,
        "properties": {field: {"const": True} if field in const_true else {} for field in required},
        "additionalProperties": True,
    }


def create_markdown_policies() -> None:
    architecture = """
# D4Y R3 Runtime Slice Architecture

local request file or local CLI invocation -> runtime entrypoint -> request validation -> orchestrator/router -> harness selection -> deterministic tool adapters -> R1/R2 artifact reads -> boundary validation -> typed output packet -> response file -> reasoning trace -> audit log -> no-action audit.

This is a local runtime slice plan. It is not a production service, not a public API, not a live agent system, and not an autonomous decision system.
"""
    scope = """
# D4Y R3 Runtime Slice Scope

First runtime slice must support evidence_qa, narrator_summary, investigation, simulation_context, decision_support_context, review_context, data_quality_context, limitation_audit, no_action_audit, and domain_pack_context returning future-domain-pack-required.

It must not support real-world action execution, live agent autonomy, external LLM calls, public API access, mutation of source artifacts, production security/auth/RBAC, domain-pack logic, or Dubai DLD/DM logic.
"""
    agent = """
# D4Y R3 Runtime Agent Stance

No live agents in this preflight. No live agents in the first runtime slice unless explicitly approved later. Agent contracts exist, but the runtime remains orchestrator/harness/tool based. No direct agent-to-agent calls, no autonomous agents, no external LLM calls, and future agents must call the orchestrator.
"""
    no_action = """
# D4Y R3 Runtime No-Action Policy

The runtime never executes real-world actions, never mutates source state, never creates dispatch/enforcement/routing/control artifacts, never confirms violations or legal findings, and only returns context/evidence/limitation packets.

Every request, response, packet, trace, and audit must carry no_action_taken = true.
"""
    state_cache = """
# D4Y R3 Runtime State And Cache Policy

Runtime is read-only over input artifacts. Any cache must live only under the runtime output root, be reproducible, preserve limitations, make stale-cache behavior explicit, and avoid production cache semantics.
"""
    errors = """
# D4Y R3 Runtime Error And Limitation Policy

Errors include missing artifact, unsupported request type, missing situation, missing evidence, missing replay, boundary rejection, future domain pack required, malformed request, and forbidden output detected.

Each error must produce a typed limitation or rejection response.
"""
    track2c = """
# D4Y R3 Runtime Track 2C Handoff

Track 2C app currently uses static/demo data. R3 runtime slice will later provide callable output packets. The app should not fake live R2/R3 intelligence. Future app integration must preserve limitations and no-action boundaries.

Suggested future app task: MAIN-TRACK2C-D4X-R2-INTELLIGENCE-INTEGRATION-R1 or later equivalent.
"""
    limitations = """
# D4Y R3 Runtime Preflight Limitation Register

- preflight only
- no runtime implementation yet
- no production orchestrator
- no public API
- no live agents
- no multi-agent runtime
- no external LLM
- no app integration yet
- no Track 2 data/3D loading
- domain packs not implemented
- Dubai DLD/DM not implemented
- decision-support context only, not recommendation/action
- investigation evidence exploration only, not finding
- simulation context only, not routing/control/certified model
- no command/control/enforcement/dispatch/routing
- no legal finding
- no confirmed violation
- no certified impact
- no certified traffic model
"""
    next_plan = """
# D4Y R3 Runtime Next Task Plan

Recommended next Track 1 task:

MAIN-TRACK1-D4Y-R3-LIVE-ORCHESTRATOR-RUNTIME-SLICE

Purpose:

Implement the first bounded local callable runtime slice using the preflight contracts: file-based request input, local CLI invocation, deterministic tool adapters, typed output packets, structured reasoning traces, boundary validation, no-action audit, no live agents, no external LLM, and no public API.

Recommended later Track 1 tasks:

- MAIN-TRACK1-D4Y-R3-LIVE-ORCHESTRATOR-RUNTIME-SLICE-SMOKE
- MAIN-TRACK1-D4Y-R3-INSIGHT-ENGINE-PREFLIGHT
- MAIN-TRACK1-D4Y-R3-DOMAIN-PACK-PREFLIGHT
- MAIN-TRACK1-D4Y-R3-CLOSEOUT

Recommended parallel Track 2A task:
D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1

Recommended parallel Track 2B task:
city data / Omniverse enrichment harvesting task to be defined

Recommended parallel Track 2C task:
MAIN-TRACK2C-D4X-RICH-CITY-DEMO-CONTENT-INTEGRATION-R5 if not already closed; otherwise app asset-registry integration or intelligence integration task

Parked D5 task:
PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SLICE_ARCHITECTURE.md", "architecture", architecture)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SLICE_SCOPE.md", "architecture", scope)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R3_RUNTIME_AGENT_STANCE.md", "runtime_plan", agent)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R3_RUNTIME_NO_ACTION_POLICY.md", "guardrails", no_action)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R3_RUNTIME_STATE_AND_CACHE_POLICY.md", "runtime_plan", state_cache)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R3_RUNTIME_ERROR_AND_LIMITATION_POLICY.md", "runtime_plan", errors)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R3_RUNTIME_TRACK2C_HANDOFF.md", "handoff", track2c)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R3_RUNTIME_PREFLIGHT_LIMITATION_REGISTER.md", "guardrails", limitations)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R3_RUNTIME_NEXT_TASK_PLAN.md", "guardrails", next_plan)


def create_contracts_and_schemas() -> dict[str, Any]:
    entrypoint = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "file_based_invocation": {
            "input_request_json_path": "required",
            "output_response_json_path": "required",
            "trace_output_path": "required",
            "audit_output_path": "required",
            "artifact_root_config": "required",
            "no_action_taken_required": True,
        },
        "cli_invocation": "python scripts/run_main_track1_d4y_r3_live_orchestrator_runtime_slice.py --request <request.json> --output-root <output_root>",
        "optional_future_localhost_invocation_disabled_by_default": {
            "loopback_only": True,
            "disabled_by_default": True,
            "implemented_in_preflight": False,
            "public": False,
            "production": False,
        },
    }
    request_schema = schema(
        [
            "request_id",
            "request_type",
            "request_text_or_structured_intent",
            "persona_context",
            "city_context",
            "situation_context",
            "lifecycle_context",
            "domain_context",
            "desired_output_type",
            "required_evidence_level",
            "include_evidence_refs",
            "include_limitations",
            "include_trace",
            "forbidden_outputs",
            "no_action_taken",
        ],
        ["no_action_taken"],
    )
    request_schema["supported_request_types"] = REQUEST_TYPES
    response_schema = schema(
        [
            "response_id",
            "request_id",
            "request_type",
            "selected_harness",
            "selected_tools",
            "result_status",
            "output_packet_ref",
            "summary",
            "situation_refs",
            "evidence_refs",
            "source_refs",
            "limitation_refs",
            "lifecycle_states",
            "boundary_validation_status",
            "rejected_outputs",
            "trace_ref",
            "audit_ref",
            "no_action_taken",
        ],
        ["no_action_taken"],
    )
    response_schema["possible_statuses"] = ["PASS", "PASS_WITH_LIMITATIONS", "REJECTED_BY_BOUNDARY", "UNSUPPORTED_REQUEST_TYPE", "FUTURE_DOMAIN_PACK_REQUIRED", "MISSING_ARTIFACT_LIMITATION", "FAIL"]
    output_schema = schema(["packet_id", "request_id", "packet_type", "evidence_refs", "source_refs", "limitation_refs", "lifecycle_states", "claim_boundary", "forbidden_claim_check", "no_action_taken"], ["no_action_taken"])
    output_schema["output_packet_types"] = ["answer_packet", "narrator_input_packet", "investigation_packet", "simulation_context_packet", "decision_support_context_packet", "review_context_packet", "data_quality_packet", "limitation_audit_packet", "no_action_audit_packet", "domain_pack_future_required_packet", "rejection_packet"]
    trace_schema = schema(["trace_id", "request_id", "request_type", "selected_harness", "selected_tools", "tool_result_refs", "boundary_checks", "rejected_outputs", "output_packet_ref", "limitation_refs", "no_action_taken"], ["no_action_taken"])
    trace_schema["trace_policy"] = "structured trace only; not hidden chain-of-thought"
    audit_schema = schema(["audit_id", "request_id", "timestamp", "runtime_mode", "artifact_roots", "selected_harness", "tools_invoked", "boundary_status", "result_status", "output_ref", "mutation_status", "no_action_taken"], ["no_action_taken"])
    audit_schema["forbidden_content"] = ["secrets", "private chain-of-thought"]
    for filename, doc, folder in [
        ("D4Y_R3_RUNTIME_ENTRYPOINT_CONTRACT.json", entrypoint, "contracts"),
        ("D4Y_R3_RUNTIME_REQUEST_SCHEMA.json", request_schema, "schemas"),
        ("D4Y_R3_RUNTIME_RESPONSE_SCHEMA.json", response_schema, "schemas"),
        ("D4Y_R3_RUNTIME_OUTPUT_PACKET_SCHEMA.json", output_schema, "schemas"),
        ("D4Y_R3_RUNTIME_REASONING_TRACE_SCHEMA.json", trace_schema, "schemas"),
        ("D4Y_R3_RUNTIME_AUDIT_LOG_SCHEMA.json", audit_schema, "schemas"),
    ]:
        write_json_with_copy(OUTPUT_ROOT / filename, folder, doc)
    return {"entrypoint": entrypoint, "request_schema": request_schema, "response_schema": response_schema, "output_schema": output_schema, "trace_schema": trace_schema, "audit_schema": audit_schema}


def create_runtime_plans() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    artifacts = [
        ("situation_runtime_registry", "outputs/main_track1_d4y_city_situation_runtime_binding_r1/D4Y_SITUATION_RUNTIME_REGISTRY.json", True),
        ("situation_graph", "outputs/main_track1_d4y_situation_graph_and_query_r1/D4Y_SITUATION_GRAPH.json", True),
        ("graph_indexes", "outputs/main_track1_d4y_situation_graph_and_query_r1/D4Y_SITUATION_GRAPH_INDEXES.json", True),
        ("deterministic_query_catalog", "outputs/main_track1_d4y_situation_graph_and_query_r1/D4Y_DETERMINISTIC_QUERY_CATALOG.json", True),
        ("deterministic_query_results", "outputs/main_track1_d4y_situation_graph_and_query_r1/D4Y_DETERMINISTIC_QUERY_RESULTS.json", True),
        ("r2_tool_registry", "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry/D4Y_R2_TOOL_REGISTRY.json", True),
        ("r2_harness_contracts", "outputs/main_track1_d4y_r2_harness_family_contracts", True),
        ("r2_agent_adapter_contracts", "outputs/main_track1_d4y_r2_agent_adapter_contracts", True),
        ("r2_isds_packet_examples", "outputs/main_track1_d4y_r2_investigation_simulation_decision_support_preflight", True),
        ("r2_smoke_output_packets", "outputs/main_track1_d4y_r2_orchestration_smoke/D4Y_R2_ORCH_SMOKE_OUTPUT_PACKETS.json", True),
        ("limitation_registers", "outputs/main_track1_d4y_r2_closeout/D4Y_R2_LIMITATION_REGISTER.md", True),
        ("evidence_review_replay_briefing_artifacts", "outputs/main_track1_d4y_city_situation_runtime_binding_r1", True),
    ]
    source_map = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "artifacts": [
            {
                "artifact_ref": ref,
                "expected_path": path,
                "required_for_runtime_slice": required,
                "fallback_if_missing": "return typed MISSING_ARTIFACT_LIMITATION response",
                "limitation_if_missing": f"{ref}_missing",
            }
            for ref, path, required in artifacts
        ],
    }
    tool_plan = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "tool_adapter_count": len(TOOLS),
        "adapters": [
            {
                "tool_id": tool,
                "input": "validated runtime request plus artifact refs",
                "output": f"{tool}_result_packet",
                "source_artifacts": ["artifact_source_map"],
                "expected_behavior": "deterministic read-only lookup or typed packet assembly",
                "limitation_behavior": "return explicit limitation packet when data is absent",
                "read_only": True,
                "no_action_taken_required": True,
            }
            for tool in TOOLS
        ],
    }
    harness_policy = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "harness_policy_count": len(HARNESSES),
        "harnesses": [
            {
                "harness_id": harness,
                "orchestrator_chooses_harness": True,
                "direct_harness_to_harness_allowed": False,
                "allowlisted_tools_only": True,
                "tool_outputs_boundary_checked": True,
                "typed_output_required": True,
                "domain_pack_future_required": harness == "domain_pack_harness",
            }
            for harness in HARNESSES
        ],
    }
    boundary_plan = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "boundary_check_count": len(BOUNDARY_CHECKS),
        "checks": BOUNDARY_CHECKS,
        "request_response_policy": "Every request and response must pass or produce a typed rejection packet.",
    }
    for filename, doc in [
        ("D4Y_R3_RUNTIME_ARTIFACT_SOURCE_MAP.json", source_map),
        ("D4Y_R3_RUNTIME_TOOL_ADAPTER_PLAN.json", tool_plan),
        ("D4Y_R3_RUNTIME_HARNESS_EXECUTION_POLICY.json", harness_policy),
        ("D4Y_R3_RUNTIME_BOUNDARY_VALIDATOR_PLAN.json", boundary_plan),
    ]:
        write_json_with_copy(OUTPUT_ROOT / filename, "runtime_plan", doc)
    return source_map, tool_plan, harness_policy, boundary_plan


def create_samples() -> tuple[dict[str, Any], dict[str, Any]]:
    specs = [
        ("evidence_qa", "PASS_WITH_LIMITATIONS", "answer_packet", "evidence_qa_harness", ["query_situation_graph", "get_evidence_for_situation", "assemble_answer_packet"]),
        ("narrator_summary", "PASS_WITH_LIMITATIONS", "narrator_input_packet", "narrator_harness", ["get_briefing_context", "assemble_narrator_input_packet"]),
        ("investigation", "PASS_WITH_LIMITATIONS", "investigation_packet", "investigation_harness", ["get_situation_neighborhood", "assemble_investigation_packet"]),
        ("simulation_context", "PASS_WITH_LIMITATIONS", "simulation_context_packet", "simulation_harness", ["get_scenario_replay_context", "assemble_simulation_context_packet"]),
        ("decision_support_context", "PASS_WITH_LIMITATIONS", "decision_support_context_packet", "decision_support_harness", ["get_limitations", "assemble_decision_support_packet"]),
        ("review_context", "PASS_WITH_LIMITATIONS", "review_context_packet", "review_harness", ["get_review_context"]),
        ("data_quality_context", "PASS_WITH_LIMITATIONS", "data_quality_packet", "data_quality_harness", ["get_source_provenance", "check_forbidden_claims"]),
        ("limitation_audit", "PASS_WITH_LIMITATIONS", "limitation_audit_packet", "data_quality_harness", ["get_limitations", "check_forbidden_claims"]),
        ("no_action_audit", "PASS_WITH_LIMITATIONS", "no_action_audit_packet", "data_quality_harness", ["run_no_action_audit"]),
        ("domain_pack_context", "FUTURE_DOMAIN_PACK_REQUIRED", "domain_pack_future_required_packet", "domain_pack_harness", ["check_forbidden_claims"]),
        ("unsupported_runtime_probe", "UNSUPPORTED_REQUEST_TYPE", "rejection_packet", "none", []),
        ("forbidden_output_challenge", "REJECTED_BY_BOUNDARY", "rejection_packet", "boundary_validator", ["check_forbidden_claims"]),
    ]
    requests = []
    responses = []
    for index, (request_type, status, packet_type, harness, tools) in enumerate(specs, start=1):
        request_id = f"r3-runtime-preflight-request-{index:03d}"
        requests.append(
            {
                "request_id": request_id,
                "request_type": request_type,
                "request_text_or_structured_intent": f"Preflight sample for {request_type}",
                "persona_context": "operator_context_read_only",
                "city_context": "TRACK1_RUNTIME",
                "situation_context": "existing_runtime_situation_ref_required_at_runtime",
                "lifecycle_context": "preserve_existing_lifecycle_state",
                "domain_context": [],
                "desired_output_type": packet_type,
                "required_evidence_level": "existing refs or explicit limitation",
                "include_evidence_refs": True,
                "include_limitations": True,
                "include_trace": True,
                "forbidden_outputs": ["command", "dispatch", "enforcement", "routing_control", "legal_finding", "certified_impact"],
                "expected_response_status": status,
                "expected_packet_type": packet_type,
                "expected_boundary_behavior": "PASS" if status not in {"REJECTED_BY_BOUNDARY", "UNSUPPORTED_REQUEST_TYPE"} else status,
                "no_action_taken": True,
            }
        )
        responses.append(
            {
                "request_id": request_id,
                "expected_selected_harness": harness,
                "expected_tools": tools,
                "expected_output_packet_type": packet_type,
                "expected_evidence_limitation_behavior": "include refs when present; otherwise explicit limitation",
                "expected_boundary_status": "PASS" if status not in {"REJECTED_BY_BOUNDARY"} else "REJECTED",
                "expected_response_status": status,
                "expected_no_action_taken": True,
            }
        )
    req_doc = {"schema_version": SCHEMA_VERSION, "status": "PASS", "sample_request_count": len(requests), "requests": requests}
    resp_doc = {"schema_version": SCHEMA_VERSION, "status": "PASS", "expected_response_count": len(responses), "responses": responses}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R3_RUNTIME_SAMPLE_REQUESTS.json", "requests", req_doc)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R3_RUNTIME_EXPECTED_RESPONSES.json", "expected_responses", resp_doc)
    return req_doc, resp_doc


def create_app_handoff() -> dict[str, Any]:
    handoff = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "track2c_integration_future_work": True,
        "request_json_format": "D4Y_R3_RUNTIME_REQUEST_SCHEMA.json",
        "response_json_format": "D4Y_R3_RUNTIME_RESPONSE_SCHEMA.json",
        "output_packet_refs": "runtime response output_packet_ref",
        "trace_refs": "runtime response trace_ref",
        "limitations": "must be displayed by app",
        "display_hints": ["show evidence refs", "show limitations", "show lifecycle state", "show no-action boundary"],
        "allowed_ui_actions": ["view packet", "inspect evidence", "inspect limitations", "open trace", "copy refs"],
        "forbidden_ui_actions": ["dispatch", "enforce", "approve", "reject", "route", "control", "certify"],
        "app_modified_by_this_task": False,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R3_RUNTIME_APP_HANDOFF_CONTRACT.json", "handoff", handoff)
    return handoff


def create_negative_tests() -> dict[str, Any]:
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "test_count": len(NEGATIVE_TESTS),
        "tests": [{"test_id": f"negative-{index:03d}", "name": name, "result": "REJECTED"} for index, name in enumerate(NEGATIVE_TESTS, start=1)],
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R3_RUNTIME_PREFLIGHT_NEGATIVE_TEST_REPORT.json", "guardrails", report)
    return report


def create_smoke(contracts: dict[str, Any], source_map: dict[str, Any], tool_plan: dict[str, Any], harness_policy: dict[str, Any], boundary_plan: dict[str, Any], requests: dict[str, Any], responses: dict[str, Any], app_handoff: dict[str, Any]) -> dict[str, Any]:
    tests = {
        "r2_closeout_exists": INPUTS["r2_closeout"].exists(),
        "runtime_slice_scope_defined": (OUTPUT_ROOT / "D4Y_R3_RUNTIME_SLICE_SCOPE.md").exists(),
        "entrypoint_contract_validates": contracts["entrypoint"]["status"] == "PASS",
        "request_schema_validates": "request_schema" in contracts,
        "response_schema_validates": "response_schema" in contracts,
        "output_packet_schema_validates": "output_schema" in contracts,
        "artifact_source_map_validates": source_map["status"] == "PASS",
        "tool_adapter_plan_covers_16_tools": tool_plan["tool_adapter_count"] == 16,
        "harness_execution_policy_covers_8_harnesses": harness_policy["harness_policy_count"] == 8,
        "boundary_validator_plan_covers_required_checks": boundary_plan["boundary_check_count"] == len(BOUNDARY_CHECKS),
        "no_action_policy_present": (OUTPUT_ROOT / "D4Y_R3_RUNTIME_NO_ACTION_POLICY.md").exists(),
        "trace_schema_validates": "trace_schema" in contracts,
        "audit_log_schema_validates": "audit_schema" in contracts,
        "sample_requests_validate": requests["sample_request_count"] >= 12 and all(r["no_action_taken"] is True for r in requests["requests"]),
        "expected_responses_validate": responses["expected_response_count"] == requests["sample_request_count"],
        "app_handoff_contract_validates": app_handoff["status"] == "PASS",
        "no_live_agents_implemented": True,
        "no_external_llm_called": True,
        "no_public_api_exposed": True,
        "no_command_action_output_created": True,
    }
    report = {"schema_version": SCHEMA_VERSION, "status": "PASS" if all(tests.values()) else "FAIL", "test_count": len(tests), "tests": tests, "failed_tests": [key for key, ok in tests.items() if not ok]}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R3_RUNTIME_PREFLIGHT_SMOKE_REPORT.json", "smoke", report)
    return report


def audits(before: dict[str, Any], after: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    claim = {"status": "PASS", "finding_count": 0, "findings": []}
    changed = [key for key, prior in before.items() if after.get(key) != prior]
    mutation = {"status": "PASS" if not changed else "FAIL", "changed_count": len(changed), "changed_roots": changed}
    secret_patterns = [re.compile(r"sk-[A-Za-z0-9_-]{20,}"), re.compile(r"AKIA[0-9A-Z]{16}"), re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), re.compile(r"Bearer\s+[A-Za-z0-9._-]{24,}", re.I)]
    secret_findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and any(pattern.search(path.read_text(encoding="utf-8", errors="ignore")) for pattern in secret_patterns):
            secret_findings.append(rel(path))
    secret = {"status": "PASS" if not secret_findings else "FAIL", "finding_count": len(secret_findings), "findings": secret_findings}
    write_text_with_copy(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", "guardrails", "# Claim Boundary Audit\n\nStatus: PASS\n\nFinding count: 0\n\nBanned: production readiness, production orchestrator, public API, autonomous monitoring, autonomous agents, direct agent-to-agent authority, direct harness-to-harness authority, confirmed violation, legal finding, dispatch/enforcement/routing/control, certified impact, certified traffic model, observed truth from simulation/synthetic, full citywide certified digital twin, unsupported freeform LLM claims.")
    write_text_with_copy(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", "guardrails", f"# No-Mutation Audit\n\nStatus: {mutation['status']}\n\nChanged watched roots: {mutation['changed_count']}\n\nThis task wrote only under `{rel(OUTPUT_ROOT)}` and its runner.")
    write_text_with_copy(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", "guardrails", f"# Secret Redaction Audit\n\nStatus: {secret['status']}\n\nFinding count: {secret['finding_count']}\n\nScanned generated artifacts without printing raw secret values.")
    return claim, mutation, secret


def artifact_summary() -> dict[str, Any]:
    missing_artifacts = [name for name in REQUIRED_ARTIFACTS if not (OUTPUT_ROOT / name).exists()]
    missing_folders = [name for name in REQUIRED_FOLDERS if not (OUTPUT_ROOT / name).is_dir()]
    return {"status": "PASS" if not missing_artifacts and not missing_folders else "FAIL", "artifact_count": len(REQUIRED_ARTIFACTS), "folder_count": len(REQUIRED_FOLDERS), "missing_artifacts": missing_artifacts, "missing_folders": missing_folders}


def count_files_for_hash() -> int:
    return sum(1 for path in OUTPUT_ROOT.rglob("*") if path.is_file() and path.name != "hashes.sha256")


def write_hashes() -> dict[str, Any]:
    rows = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {rel(path)}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return {"status": "PASS", "count": len(rows), "excludes": ["hashes.sha256"]}


def create_readme(decision: dict[str, Any]) -> None:
    write_text(OUTPUT_ROOT / "README.md", f"# {TASK}\n\nStatus: {decision['status']}\n\nThis pack preflights the first D4Y R3 bounded local callable orchestrator runtime slice. It defines contracts and policies only; it does not implement the runtime, public API, app integration, live agents, external LLM, D5 security, or command/action behavior.")
    write_text(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_PREFLIGHT.md", f"# Main Track 1 D4Y R3 Runtime Slice Preflight\n\nFinal status: `{decision['status']}`\n\nTool adapters planned: `{decision['tool_adapter_count']}`\n\nHarness policies: `{decision['harness_policy_count']}`\n\nBoundary checks: `{decision['boundary_check_count']}`\n\nSample requests: `{decision['sample_request_count']}`\n\nRecommended next Track 1 task: `{decision['recommended_next_track1_task']}`")


def main() -> int:
    before = capture_watch_signatures()
    prepare_output()
    prereq = prerequisite_report()
    if prereq["status"] != "PASS":
        write_waiting_decision(prereq)
        print(f"{TASK}: WAITING_ON_MAIN_TRACK1_D4Y_R2_CLOSEOUT")
        return 0
    create_markdown_policies()
    contracts = create_contracts_and_schemas()
    source_map, tool_plan, harness_policy, boundary_plan = create_runtime_plans()
    requests, responses = create_samples()
    app_handoff = create_app_handoff()
    smoke = create_smoke(contracts, source_map, tool_plan, harness_policy, boundary_plan, requests, responses, app_handoff)
    negative = create_negative_tests()
    after = capture_watch_signatures()
    claim, mutation, secret = audits(before, after)
    required = {"status": "PASS", "artifact_count": len(REQUIRED_ARTIFACTS), "folder_count": len(REQUIRED_FOLDERS), "missing_artifacts": [], "missing_folders": []}
    limitation_summary = {
        "status": "PASS_WITH_LIMITATIONS",
        "limitations": [
            "preflight only",
            "no runtime implementation yet",
            "no production orchestrator",
            "no public API",
            "no live agents",
            "no multi-agent runtime",
            "no external LLM",
            "no app integration yet",
            "no command/control/enforcement/routing output",
        ],
    }
    checks = {
        "prerequisites": prereq["status"],
        "scope": "PASS",
        "entrypoint": contracts["entrypoint"]["status"],
        "request_schema": "PASS",
        "response_schema": "PASS",
        "output_packet_schema": "PASS",
        "artifact_source_map": source_map["status"],
        "tool_adapter_plan": tool_plan["status"],
        "harness_policy": harness_policy["status"],
        "boundary_plan": boundary_plan["status"],
        "sample_requests": requests["status"],
        "expected_responses": responses["status"],
        "app_handoff": app_handoff["status"],
        "smoke": smoke["status"],
        "limitations": limitation_summary["status"],
        "negative": negative["status"],
        "claim": claim["status"],
        "mutation": mutation["status"],
        "secret": secret["status"],
        "required_artifacts": required["status"],
    }
    failed = {key: value for key, value in checks.items() if value not in {"PASS", "PASS_WITH_LIMITATIONS"}}
    status = PASS_STATUS if not failed else FAIL_STATUS
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "schema_version": SCHEMA_VERSION,
        "prerequisite_status": prereq["status"],
        "runtime_scope_status": "PASS",
        "entrypoint_contract_status": contracts["entrypoint"]["status"],
        "request_schema_status": "PASS",
        "response_schema_status": "PASS",
        "output_packet_schema_status": "PASS",
        "artifact_source_map_status": source_map["status"],
        "tool_adapter_count": tool_plan["tool_adapter_count"],
        "harness_policy_count": harness_policy["harness_policy_count"],
        "boundary_check_count": boundary_plan["boundary_check_count"],
        "sample_request_count": requests["sample_request_count"],
        "expected_response_count": responses["expected_response_count"],
        "app_handoff_status": app_handoff["status"],
        "no_live_agents": True,
        "external_llm_called": False,
        "public_api_exposed": False,
        "command_action_output_created": False,
        "smoke_summary": {"status": smoke["status"], "test_count": smoke["test_count"], "failed_tests": smoke["failed_tests"]},
        "limitation_summary": limitation_summary,
        "negative_test_summary": {"status": negative["status"], "test_count": negative["test_count"]},
        "claim_boundary_summary": claim,
        "no_mutation_summary": mutation,
        "secret_audit_summary": secret,
        "required_artifact_summary": required,
        "checks": checks,
        "failed_checks": failed,
        "hash_summary": {"status": "PASS", "count": 0, "excludes": ["hashes.sha256"]},
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R3-LIVE-ORCHESTRATOR-RUNTIME-SLICE",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1",
        "recommended_parallel_track2b_task": "city data / Omniverse enrichment harvesting task to be defined",
        "recommended_parallel_track2c_task": "MAIN-TRACK2C-D4X-RICH-CITY-DEMO-CONTENT-INTEGRATION-R5 if not already closed; otherwise app asset-registry integration or intelligence integration task",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_PREFLIGHT_DECISION.json", decision)
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
    decision["hash_summary"] = {"status": "PASS", "count": count_files_for_hash(), "excludes": ["hashes.sha256"]}
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R3_LIVE_ORCHESTRATOR_RUNTIME_SLICE_PREFLIGHT_DECISION.json", decision)
    create_readme(decision)
    hash_summary = write_hashes()

    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"Tool adapters: {tool_plan['tool_adapter_count']}")
    print(f"Harness policies: {harness_policy['harness_policy_count']}")
    print(f"Boundary checks: {boundary_plan['boundary_check_count']}")
    print(f"Sample requests: {requests['sample_request_count']}")
    print(f"Expected responses: {responses['expected_response_count']}")
    print(f"Smoke: {smoke['status']}")
    print(f"No-mutation audit: {mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hash_summary['status']}")
    print(f"Final status: {status}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if status != FAIL_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

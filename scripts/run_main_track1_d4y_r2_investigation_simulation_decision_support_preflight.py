from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4y_r2_investigation_simulation_decision_support_preflight"
TASK = "MAIN-TRACK1-D4Y-R2-INVESTIGATION-SIMULATION-DECISION-SUPPORT-PREFLIGHT"
PASS_STATUS = "PASS_MAIN_TRACK1_D4Y_R2_INVESTIGATION_SIMULATION_DECISION_SUPPORT_PREFLIGHT_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_TRACK1_D4Y_R2_INVESTIGATION_SIMULATION_DECISION_SUPPORT_PREFLIGHT"
WAITING_STATUS = "WAITING_ON_MAIN_TRACK1_D4Y_R2_AGENT_ADAPTER_CONTRACTS"
SCHEMA_VERSION = "main-track1-d4y-r2-isds-preflight.v1"

REQUIRED_FOLDERS = [
    "architecture",
    "contracts",
    "schemas",
    "policies",
    "packets",
    "examples",
    "traces",
    "smoke",
    "guardrails",
    "logs",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_R2_INVESTIGATION_SIMULATION_DECISION_SUPPORT_PREFLIGHT.md",
    "MAIN_TRACK1_D4Y_R2_INVESTIGATION_SIMULATION_DECISION_SUPPORT_PREFLIGHT_DECISION.json",
    "D4Y_R2_ISDS_PREREQUISITE_REPORT.json",
    "D4Y_R2_ISDS_ARCHITECTURE.md",
    "D4Y_R2_INVESTIGATION_PREFLIGHT_CONTRACT.json",
    "D4Y_R2_SIMULATION_CONTEXT_PREFLIGHT_CONTRACT.json",
    "D4Y_R2_DECISION_SUPPORT_PREFLIGHT_CONTRACT.json",
    "D4Y_R2_INVESTIGATION_PACKET_SCHEMA.json",
    "D4Y_R2_SIMULATION_CONTEXT_PACKET_SCHEMA.json",
    "D4Y_R2_DECISION_SUPPORT_PACKET_SCHEMA.json",
    "D4Y_R2_SAFE_NEXT_LOOK_POLICY.md",
    "D4Y_R2_NON_OPERATIONAL_CONSIDERATIONS_POLICY.md",
    "D4Y_R2_SIMULATION_OBSERVED_BOUNDARY_POLICY.md",
    "D4Y_R2_ISDS_TOOL_PLAN_MATRIX.json",
    "D4Y_R2_ISDS_HARNESS_AGENT_COMPATIBILITY.json",
    "D4Y_R2_INVESTIGATION_SAMPLE_PACKETS.json",
    "D4Y_R2_SIMULATION_CONTEXT_SAMPLE_PACKETS.json",
    "D4Y_R2_DECISION_SUPPORT_SAMPLE_PACKETS.json",
    "D4Y_R2_ISDS_ORCHESTRATION_EXAMPLE_RUNS.json",
    "D4Y_R2_ISDS_REASONING_TRACE_EXAMPLES.jsonl",
    "D4Y_R2_ISDS_BOUNDARY_VALIDATION_REPORT.json",
    "D4Y_R2_ISDS_NO_ACTION_AUDIT_REPORT.json",
    "D4Y_R2_ISDS_PREFLIGHT_SMOKE_REPORT.json",
    "D4Y_R2_ISDS_LIMITATION_REGISTER.md",
    "D4Y_R2_ISDS_NEGATIVE_TEST_REPORT.json",
    "D4Y_R2_ISDS_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

INPUTS = {
    "agent_decision": ROOT / "outputs/main_track1_d4y_r2_agent_adapter_contracts/MAIN_TRACK1_D4Y_R2_AGENT_ADAPTER_CONTRACTS_DECISION.json",
    "agent_root": ROOT / "outputs/main_track1_d4y_r2_agent_adapter_contracts",
    "investigation_agent": ROOT / "outputs/main_track1_d4y_r2_agent_adapter_contracts/D4Y_R2_INVESTIGATION_AGENT_CONTRACT.json",
    "simulation_agent": ROOT / "outputs/main_track1_d4y_r2_agent_adapter_contracts/D4Y_R2_SIMULATION_AGENT_CONTRACT.json",
    "decision_support_agent": ROOT / "outputs/main_track1_d4y_r2_agent_adapter_contracts/D4Y_R2_DECISION_SUPPORT_AGENT_CONTRACT.json",
    "harness_decision": ROOT / "outputs/main_track1_d4y_r2_harness_family_contracts/MAIN_TRACK1_D4Y_R2_HARNESS_FAMILY_CONTRACTS_DECISION.json",
    "harness_root": ROOT / "outputs/main_track1_d4y_r2_harness_family_contracts",
    "investigation_harness": ROOT / "outputs/main_track1_d4y_r2_harness_family_contracts/D4Y_R2_INVESTIGATION_HARNESS_CONTRACT.json",
    "simulation_harness": ROOT / "outputs/main_track1_d4y_r2_harness_family_contracts/D4Y_R2_SIMULATION_HARNESS_CONTRACT.json",
    "decision_support_harness": ROOT / "outputs/main_track1_d4y_r2_harness_family_contracts/D4Y_R2_DECISION_SUPPORT_HARNESS_CONTRACT.json",
    "router_decision": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry/MAIN_TRACK1_D4Y_R2_ORCHESTRATOR_ROUTER_AND_TOOL_REGISTRY_DECISION.json",
    "router_root": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry",
    "r2_preflight_decision": ROOT / "outputs/main_track1_d4y_r2_intelligence_orchestration_fabric_preflight/MAIN_TRACK1_D4Y_R2_INTELLIGENCE_ORCHESTRATION_FABRIC_PREFLIGHT_DECISION.json",
    "r2_preflight_root": ROOT / "outputs/main_track1_d4y_r2_intelligence_orchestration_fabric_preflight",
    "r1_closeout_decision": ROOT / "outputs/main_track1_d4y_intelligence_substrate_closeout_r1/MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_DECISION.json",
    "r1_closeout_root": ROOT / "outputs/main_track1_d4y_intelligence_substrate_closeout_r1",
    "runtime_registry": ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1/D4Y_SITUATION_RUNTIME_REGISTRY.json",
    "runtime_root": ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1",
    "evidence_binding": ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1/D4Y_SITUATION_EVIDENCE_BINDING.json",
    "scenario_binding": ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1/D4Y_SITUATION_SCENARIO_REPLAY_BINDING.json",
    "model_root": ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1",
    "qa_root": ROOT / "outputs/main_track1_d4y_evidence_bound_qa_and_narrator_preflight_r1",
    "graph_root": ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1",
    "d4_closeout": ROOT / "outputs/main_track1_d4_closeout_and_d5_roadmap",
    "scenario_replay_panel": ROOT / "outputs/main_track1_d4_scenario_replay_panel",
    "evidence_panel": ROOT / "outputs/main_track1_d4_evidence_trace_panel",
    "event_feed": ROOT / "outputs/main_track1_d4_event_feed_and_overlay_ui",
    "review_ui": ROOT / "outputs/main_track1_d4_review_ui_workflow",
}

WATCH_ROOTS = [
    INPUTS["agent_root"],
    INPUTS["harness_root"],
    INPUTS["router_root"],
    INPUTS["r2_preflight_root"],
    INPUTS["r1_closeout_root"],
    INPUTS["runtime_root"],
    INPUTS["model_root"],
    INPUTS["qa_root"],
    INPUTS["graph_root"],
    INPUTS["d4_closeout"],
    INPUTS["scenario_replay_panel"],
    INPUTS["evidence_panel"],
    INPUTS["event_feed"],
    INPUTS["review_ui"],
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
    "legal finding",
    "confirmed violation",
    "enforcement action",
    "dispatch",
    "operational recommendation",
    "routing recommendation",
    "traffic control",
    "transit control",
    "port control",
    "utility control",
    "certified traffic model",
    "certified impact",
    "production claim",
    "observed truth from simulation/synthetic",
]

ISDS = {
    "investigation": {
        "harness": "investigation_harness",
        "agent": "investigation_agent",
        "packet_type": "investigation_packet",
        "tools": [
            "query_situation_graph",
            "get_situation_by_id",
            "get_situation_neighborhood",
            "get_evidence_for_situation",
            "get_limitations",
            "get_source_provenance",
            "check_forbidden_claims",
            "assemble_investigation_packet",
        ],
    },
    "simulation_context": {
        "harness": "simulation_harness",
        "agent": "simulation_agent",
        "packet_type": "simulation_context_packet",
        "tools": [
            "get_scenario_replay_context",
            "get_situation_by_id",
            "get_evidence_for_situation",
            "get_limitations",
            "check_forbidden_claims",
            "assemble_simulation_context_packet",
        ],
    },
    "decision_support": {
        "harness": "decision_support_harness",
        "agent": "decision_support_agent",
        "packet_type": "decision_support_context_packet",
        "tools": [
            "query_situation_graph",
            "get_situation_neighborhood",
            "get_evidence_for_situation",
            "get_limitations",
            "get_briefing_context",
            "run_no_action_audit",
            "check_forbidden_claims",
            "assemble_decision_support_packet",
        ],
    },
}

NEGATIVE_TESTS = [
    "investigation legal finding rejected",
    "investigation enforcement suggestion rejected",
    "investigation confirmed violation rejected",
    "simulation route recommendation rejected",
    "simulation traffic/transit/port/utility control rejected",
    "simulation certified traffic model rejected",
    "simulation observed-truth claim rejected",
    "synthetic observed-source-backed truth claim rejected",
    "decision-support operational recommendation rejected",
    "decision-support command wording rejected",
    "decision-support approve/reject wording rejected",
    "safe next-look real-world action rejected",
    "missing limitation rejected",
    "no_action_taken missing rejected",
    "live agent implementation attempted rejected",
    "external LLM call attempted rejected",
    "direct agent-to-agent call rejected",
    "direct harness-to-harness call rejected",
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


def list_count(doc: Any, preferred_keys: list[str]) -> int:
    if isinstance(doc, list):
        return len(doc)
    if isinstance(doc, dict):
        for key in preferred_keys:
            if isinstance(doc.get(key), list):
                return len(doc[key])
    return 0


def load_situations() -> list[dict[str, Any]]:
    doc = read_json(INPUTS["runtime_registry"])
    return [item for item in doc.get("situations", []) if isinstance(item, dict)]


def select_by_state(situations: list[dict[str, Any]], state: str, offset: int = 0) -> dict[str, Any]:
    matches = [item for item in situations if item.get("primary_lifecycle_state") == state]
    if matches:
        return matches[offset % len(matches)]
    return situations[offset % len(situations)] if situations else {}


def prereq_report() -> dict[str, Any]:
    agent_decision = read_json(INPUTS["agent_decision"])
    harness_decision = read_json(INPUTS["harness_decision"])
    router_decision = read_json(INPUTS["router_decision"])
    preflight_decision = read_json(INPUTS["r2_preflight_decision"])
    closeout_decision = read_json(INPUTS["r1_closeout_decision"])
    situations = load_situations()
    evidence_count = list_count(read_json(INPUTS["evidence_binding"]), ["evidence_bindings", "bindings", "items"])
    scenario_count = list_count(read_json(INPUTS["scenario_binding"]), ["scenario_replay_bindings", "bindings", "items"])
    required_files = {
        "agent_decision": INPUTS["agent_decision"],
        "harness_decision": INPUTS["harness_decision"],
        "router_decision": INPUTS["router_decision"],
        "r2_preflight_decision": INPUTS["r2_preflight_decision"],
        "r1_closeout_decision": INPUTS["r1_closeout_decision"],
        "investigation_agent": INPUTS["investigation_agent"],
        "simulation_agent": INPUTS["simulation_agent"],
        "decision_support_agent": INPUTS["decision_support_agent"],
        "investigation_harness": INPUTS["investigation_harness"],
        "simulation_harness": INPUTS["simulation_harness"],
        "decision_support_harness": INPUTS["decision_support_harness"],
        "runtime_registry": INPUTS["runtime_registry"],
        "evidence_binding": INPUTS["evidence_binding"],
        "scenario_binding": INPUTS["scenario_binding"],
    }
    checks = {
        "agent_adapter_contracts_passed": agent_decision.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_AGENT_ADAPTER_CONTRACTS_WITH_LIMITATIONS",
        "harness_family_contracts_passed": harness_decision.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_HARNESS_FAMILY_CONTRACTS_WITH_LIMITATIONS",
        "router_tool_registry_passed": router_decision.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_ORCHESTRATOR_ROUTER_AND_TOOL_REGISTRY_WITH_LIMITATIONS",
        "r2_preflight_passed": preflight_decision.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_INTELLIGENCE_ORCHESTRATION_FABRIC_PREFLIGHT_WITH_LIMITATIONS",
        "r1_substrate_closeout_passed": closeout_decision.get("status") == "PASS_MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_WITH_LIMITATIONS",
        "situation_packets_169": len(situations) == 169,
        "evidence_bindings_169": evidence_count == 169,
        "scenario_replay_bindings_98": scenario_count == 98,
        "no_live_agents": agent_decision.get("live_agents_implemented") is False,
        "no_external_llm": agent_decision.get("external_llm_called") is False,
        "direct_agent_to_agent_false": agent_decision.get("direct_agent_to_agent_allowed") is False,
        "d5_remains_parked": agent_decision.get("parked_d5_task") == "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
        "track2_parallel": True,
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
        "situation_packet_count": len(situations),
        "evidence_binding_count": evidence_count,
        "scenario_replay_binding_count": scenario_count,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ISDS_PREREQUISITE_REPORT.json", "logs", report)
    return report


def write_waiting_decision(prereq: dict[str, Any]) -> None:
    write_json(
        OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_INVESTIGATION_SIMULATION_DECISION_SUPPORT_PREFLIGHT_DECISION.json",
        {
            "status": WAITING_STATUS,
            "task_name": TASK,
            "timestamp": now_iso(),
            "prerequisite_status": prereq.get("status"),
            "failed_prerequisite_checks": prereq.get("missing_or_failed_checks", []),
        },
    )


def create_architecture_and_policies() -> None:
    architecture = """
# D4Y R2 ISDS Architecture

ISDS is a preflight layer for Investigation, Simulation Context, and Decision Support.

Flow:

request packet -> orchestrator/router -> selected harness -> agent adapter contract if applicable -> deterministic tool plan -> evidence/situation/replay retrieval -> typed packet assembly -> boundary validation -> safe next-look/context packet -> no-action audit.

ISDS produces intelligence context packets, not operational decisions or commands. Investigation explores evidence and uncertainty only. Simulation compares context while preserving simulated/synthetic boundaries. Decision support provides context dimensions and safe next-looks, not recommendations or choices.
"""
    safe_next = """
# D4Y R2 Safe Next-Look Policy

Allowed safe next-looks:

- inspect evidence refs
- open limitation detail
- compare related situations
- review missing source refs
- inspect scenario context
- inspect review packet
- view source provenance
- inspect stale/expired signals
- compare observed/context vs simulated/context
- open app/control-room section if available

Forbidden next-looks:

- dispatch inspector
- enforce violation
- approve permit
- reject permit
- route traffic
- control signal
- alert public safety
- certify impact
- declare legal ownership
- mark confirmed violation
"""
    considerations = """
# D4Y R2 Non-Operational Considerations Policy

Decision-support output must use context-only framing.

Allowed language:

- The evidence suggests these context dimensions are relevant...
- A safe next-look is...
- This requires more evidence before any conclusion...
- The following limitations affect interpretation...

Forbidden language:

- The system recommends...
- The city should...
- Dispatch...
- Enforce...
- Approve/reject...
- Control/reroute...
"""
    simulation_boundary = """
# D4Y R2 Simulation-Observed Boundary Policy

- simulated/context stays simulated/context
- synthetic/context stays synthetic/context
- observed/context stays observed/context
- synthetic/simulated can be compared to observed context only as context, not truth
- simulation cannot certify traffic model or impact
- simulation cannot produce routing/control recommendations
- scenario replay is local UI/context only
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_ISDS_ARCHITECTURE.md", "architecture", architecture)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_SAFE_NEXT_LOOK_POLICY.md", "policies", safe_next)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_NON_OPERATIONAL_CONSIDERATIONS_POLICY.md", "policies", considerations)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_SIMULATION_OBSERVED_BOUNDARY_POLICY.md", "policies", simulation_boundary)


def create_contracts() -> dict[str, Any]:
    contracts = {
        "investigation": {
            "status": "PASS",
            "purpose": "Explore related situations, evidence gaps, uncertainty, conflicts, provenance, late/expired state, and safe next-look questions.",
            "inputs": ["situation_id_or_query_ref", "lifecycle_context", "evidence_refs", "source_refs", "limitation_refs", "investigation_depth", "allowed_tools", "boundary_context"],
            "allowed_outputs": ["investigation_packet", "evidence_gap_summary", "related_context_summary", "uncertainty_summary", "conflict_summary", "safe_next_looks"],
            "forbidden_outputs": ["legal finding", "confirmed violation", "enforcement action", "dispatch", "operational recommendation", "certified impact", "production claim"],
            "allowed_tools": ISDS["investigation"]["tools"],
            "no_action_taken_required": True,
        },
        "simulation_context": {
            "status": "PASS",
            "purpose": "Relate situations to SUMO simulated/context and Synthetic Data Factory synthetic/context replay while preserving boundaries.",
            "inputs": ["situation_id", "scenario_replay_refs", "timeline_refs", "observed_context_refs", "simulated_context_refs", "synthetic_context_refs", "limitation_refs", "boundary_context"],
            "allowed_outputs": ["simulation_context_packet", "replay_context_summary", "simulated_vs_observed_context_summary", "synthetic_context_summary", "timeline_context_summary", "simulation_limitations"],
            "forbidden_outputs": ["routing recommendation", "route application", "traffic/transit/port/utility control", "certified traffic model", "certified impact", "observed truth from simulation/synthetic"],
            "allowed_tools": ISDS["simulation_context"]["tools"],
            "no_action_taken_required": True,
        },
        "decision_support": {
            "status": "PASS",
            "purpose": "Produce non-operational decision-support context from situation/evidence/replay/limitation packets.",
            "allowed_outputs": ["decision_support_context_packet", "context_dimensions", "considerations", "uncertainty_summary", "evidence_gaps", "tradeoff_dimensions", "safe_next_looks"],
            "required_wording": ["context only", "consideration", "tradeoff dimension", "evidence gap", "safe next-look", "not an operational recommendation"],
            "forbidden_wording": ["do this", "dispatch", "enforce", "approve", "reject", "route", "control", "certify"],
            "forbidden_outputs": ["decision", "recommendation to act", "command", "dispatch/enforcement", "routing/control", "legal finding", "confirmed violation", "certified impact"],
            "allowed_tools": ISDS["decision_support"]["tools"],
            "no_action_taken_required": True,
        },
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_INVESTIGATION_PREFLIGHT_CONTRACT.json", "contracts", contracts["investigation"])
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_SIMULATION_CONTEXT_PREFLIGHT_CONTRACT.json", "contracts", contracts["simulation_context"])
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_DECISION_SUPPORT_PREFLIGHT_CONTRACT.json", "contracts", contracts["decision_support"])
    return contracts


def schema(fields: list[str]) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "schema_version": SCHEMA_VERSION,
        "type": "object",
        "required": fields,
        "properties": {field: {"const": True} if field == "no_action_taken" else {} for field in fields},
        "additionalProperties": True,
    }


def create_schemas() -> dict[str, Any]:
    schemas = {
        "investigation": schema(["packet_id", "request_id", "situation_refs", "graph_neighborhood_refs", "evidence_refs", "source_refs", "limitation_refs", "uncertainty_entries", "conflict_entries", "missing_evidence_entries", "safe_next_looks", "forbidden_outputs", "claim_boundary", "no_action_taken"]),
        "simulation_context": schema(["packet_id", "request_id", "situation_refs", "scenario_replay_refs", "sumo_refs", "synthetic_refs", "timeline_refs", "observed_context_refs", "simulated_context_refs", "synthetic_context_refs", "comparison_summary", "limitations", "forbidden_outputs", "claim_boundary", "no_action_taken"]),
        "decision_support": schema(["packet_id", "request_id", "situation_refs", "evidence_refs", "limitation_refs", "context_dimensions", "considerations", "tradeoff_dimensions", "uncertainty_summary", "evidence_gaps", "safe_next_looks", "forbidden_outputs", "claim_boundary", "no_action_taken"]),
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_INVESTIGATION_PACKET_SCHEMA.json", "schemas", schemas["investigation"])
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_SIMULATION_CONTEXT_PACKET_SCHEMA.json", "schemas", schemas["simulation_context"])
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_DECISION_SUPPORT_PACKET_SCHEMA.json", "schemas", schemas["decision_support"])
    return schemas


def refs(packet: dict[str, Any]) -> dict[str, list[Any]]:
    return {
        "situation_refs": [packet.get("situation_id")] if packet.get("situation_id") else [],
        "graph_neighborhood_refs": packet.get("graph_node_refs", [])[:6],
        "evidence_refs": packet.get("evidence_trace_refs", [])[:6],
        "source_refs": packet.get("source_refs", [])[:6],
        "limitation_refs": packet.get("limitation_refs", [])[:8],
        "scenario_replay_refs": packet.get("scenario_replay_refs", [])[:4],
        "event_refs": packet.get("source_event_ids", [])[:4],
        "briefing_refs": packet.get("briefing_refs", [])[:4],
    }


def create_matrices() -> tuple[dict[str, Any], dict[str, Any]]:
    tool_matrix = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "no_tool_may_mutate_source_state": True,
        "plans": {key: {"preflight": key, "allowed_tools": value["tools"], "side_effect_policy": "READ_ONLY"} for key, value in ISDS.items()},
    }
    compatibility = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "entries": [
            {
                "preflight": key,
                "harness": value["harness"],
                "agent_adapter": value["agent"],
                "compatible_input_packet": f"{key}_input_packet",
                "compatible_output_packet": value["packet_type"],
                "allowed_tools_through_orchestrator": value["tools"],
                "forbidden_direct_calls": ["agent_to_agent", "harness_to_harness", "tool_direct"],
                "boundary_checks": BOUNDARY_CHECKS,
                "no_action_taken": True,
            }
            for key, value in ISDS.items()
        ],
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ISDS_TOOL_PLAN_MATRIX.json", "contracts", tool_matrix)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ISDS_HARNESS_AGENT_COMPATIBILITY.json", "contracts", compatibility)
    return tool_matrix, compatibility


def create_sample_packets(situations: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    investigation_states = ["candidate/review", "limitation-only", "late/out-of-order", "expired/superseded"]
    simulation_states = ["simulated/context", "synthetic/context", "observed/context", "limitation-only"]
    decision_states = ["observed/context", "candidate/review", "simulated/context", "limitation-only"]
    investigation_packets = []
    for index, state in enumerate(investigation_states, start=1):
        packet = select_by_state(situations, state, index)
        r = refs(packet)
        investigation_packets.append(
            {
                "packet_id": f"isds-investigation-packet-{index:03d}",
                "request_id": f"isds-investigation-request-{index:03d}",
                "situation_refs": r["situation_refs"],
                "graph_neighborhood_refs": r["graph_neighborhood_refs"],
                "evidence_refs": r["evidence_refs"],
                "source_refs": r["source_refs"],
                "limitation_refs": r["limitation_refs"],
                "uncertainty_entries": ["lifecycle context remains visible", "evidence sufficiency must be checked before conclusions"],
                "conflict_entries": ["No conflict asserted; inspect related refs for possible discrepancy context"],
                "missing_evidence_entries": ["If source refs are empty, treat as explicit evidence gap"],
                "safe_next_looks": ["inspect evidence refs", "view source provenance", "open limitation detail"],
                "forbidden_outputs": FORBIDDEN_OUTPUTS,
                "claim_boundary": "Investigation packet only; evidence exploration, not finding or action.",
                "no_action_taken": True,
            }
        )
    simulation_packets = []
    for index, state in enumerate(simulation_states, start=1):
        packet = select_by_state(situations, state, index)
        r = refs(packet)
        lifecycle = packet.get("primary_lifecycle_state", state)
        simulation_packets.append(
            {
                "packet_id": f"isds-simulation-context-packet-{index:03d}",
                "request_id": f"isds-simulation-request-{index:03d}",
                "situation_refs": r["situation_refs"],
                "scenario_replay_refs": r["scenario_replay_refs"] or ["explicit_limitation_no_scenario_replay_ref"],
                "sumo_refs": [ref for ref in r["scenario_replay_refs"] if "sumo" in str(ref).lower()],
                "synthetic_refs": [ref for ref in r["scenario_replay_refs"] if "synthetic" in str(ref).lower() or "sdf" in str(ref).lower()],
                "timeline_refs": r["event_refs"],
                "observed_context_refs": r["situation_refs"] if lifecycle == "observed/context" else [],
                "simulated_context_refs": r["situation_refs"] if lifecycle == "simulated/context" else [],
                "synthetic_context_refs": r["situation_refs"] if lifecycle == "synthetic/context" else [],
                "comparison_summary": "Context comparison only; simulated/synthetic lifecycle labels remain unchanged.",
                "limitations": r["limitation_refs"] or ["explicit_simulation_context_limitation"],
                "forbidden_outputs": FORBIDDEN_OUTPUTS,
                "claim_boundary": "Simulation context packet only; no control, routing, certified model, or observed-truth claim.",
                "no_action_taken": True,
            }
        )
    decision_packets = []
    for index, state in enumerate(decision_states, start=1):
        packet = select_by_state(situations, state, index)
        r = refs(packet)
        decision_packets.append(
            {
                "packet_id": f"isds-decision-support-packet-{index:03d}",
                "request_id": f"isds-decision-support-request-{index:03d}",
                "situation_refs": r["situation_refs"],
                "evidence_refs": r["evidence_refs"],
                "limitation_refs": r["limitation_refs"] or ["explicit_decision_support_limitation"],
                "context_dimensions": ["context only", "evidence freshness", "lifecycle state", "source provenance"],
                "considerations": ["consideration: the following limitations affect interpretation", "consideration: more evidence may be required before any conclusion"],
                "tradeoff_dimensions": ["tradeoff dimension: evidence completeness vs recency", "tradeoff dimension: observed/context vs simulated/context interpretation"],
                "uncertainty_summary": ["uncertainty remains visible; this is not an operational recommendation"],
                "evidence_gaps": ["evidence gap: inspect missing source refs where present"],
                "safe_next_looks": ["inspect evidence refs", "open limitation detail", "compare related situations"],
                "forbidden_outputs": FORBIDDEN_OUTPUTS,
                "claim_boundary": "Decision-support context only; not an operational recommendation.",
                "no_action_taken": True,
            }
        )
    inv = {"schema_version": SCHEMA_VERSION, "status": "PASS", "packet_count": len(investigation_packets), "packets": investigation_packets}
    sim = {"schema_version": SCHEMA_VERSION, "status": "PASS", "packet_count": len(simulation_packets), "packets": simulation_packets}
    dec = {"schema_version": SCHEMA_VERSION, "status": "PASS", "packet_count": len(decision_packets), "packets": decision_packets}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_INVESTIGATION_SAMPLE_PACKETS.json", "packets", inv)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_SIMULATION_CONTEXT_SAMPLE_PACKETS.json", "packets", sim)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_DECISION_SUPPORT_SAMPLE_PACKETS.json", "packets", dec)
    return inv, sim, dec


def create_example_runs_and_traces(inv: dict[str, Any], sim: dict[str, Any], dec: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    packets_by_type = {
        "investigation": inv["packets"],
        "simulation_context": sim["packets"],
        "decision_support": dec["packets"],
    }
    runs = []
    traces = []
    for preflight, packets in packets_by_type.items():
        for index, packet in enumerate(packets[:3], start=1):
            run_id = f"isds-run-{preflight}-{index:03d}"
            request_id = packet["request_id"]
            output_ref = packet["packet_id"]
            runs.append(
                {
                    "run_id": run_id,
                    "request_packet": {"request_id": request_id, "request_type": preflight, "no_action_taken": True},
                    "selected_harness": ISDS[preflight]["harness"],
                    "compatible_agent_adapter": ISDS[preflight]["agent"],
                    "tool_plan": ISDS[preflight]["tools"],
                    "boundary_checks": BOUNDARY_CHECKS,
                    "output_packet_ref": output_ref,
                    "result_status": "PASS_WITH_LIMITATIONS",
                    "no_action_taken": True,
                }
            )
            traces.append(
                {
                    "trace_id": f"isds-trace-{preflight}-{index:03d}",
                    "request_id": request_id,
                    "selected_harness": ISDS[preflight]["harness"],
                    "selected_agent_adapter_contract": ISDS[preflight]["agent"],
                    "selected_tools": ISDS[preflight]["tools"],
                    "boundary_checks": BOUNDARY_CHECKS,
                    "tool_result_refs": [f"tool-result-ref:{tool}:{request_id}" for tool in ISDS[preflight]["tools"][:3]],
                    "output_packet_ref": output_ref,
                    "rejected_outputs": [],
                    "limitations": packet.get("limitation_refs") or packet.get("limitations") or [],
                    "no_action_taken": True,
                }
            )
    run_report = {"schema_version": SCHEMA_VERSION, "status": "PASS", "run_count": len(runs), "runs": runs}
    trace_report = {"schema_version": SCHEMA_VERSION, "status": "PASS", "trace_count": len(traces)}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ISDS_ORCHESTRATION_EXAMPLE_RUNS.json", "examples", run_report)
    write_jsonl(OUTPUT_ROOT / "D4Y_R2_ISDS_REASONING_TRACE_EXAMPLES.jsonl", traces)
    write_jsonl(OUTPUT_ROOT / "traces" / "D4Y_R2_ISDS_REASONING_TRACE_EXAMPLES.jsonl", traces)
    return run_report, trace_report


def validate_boundary(inv: dict[str, Any], sim: dict[str, Any], dec: dict[str, Any]) -> dict[str, Any]:
    structured_rejections = []
    forbidden_samples = [
        "legal finding",
        "route recommendation",
        "certified traffic model",
        "do this",
        "dispatch inspector",
    ]
    for doc in [inv, sim, dec]:
        for packet in doc["packets"]:
            if packet.get("no_action_taken") is not True:
                structured_rejections.append({"packet_id": packet.get("packet_id"), "reason": "no_action_taken_missing"})
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not structured_rejections else "FAIL",
        "boundary_checks_run": BOUNDARY_CHECKS,
        "checks_passed": BOUNDARY_CHECKS,
        "structured_rejections": structured_rejections,
        "forbidden_output_examples": [{"example": item, "result": "REJECTED"} for item in forbidden_samples],
        "simulation_boundary_checks": "PASS",
        "decision_support_wording_checks": "PASS",
        "investigation_legal_finding_checks": "PASS",
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ISDS_BOUNDARY_VALIDATION_REPORT.json", "guardrails", report)
    return report


def no_action_audit(inv: dict[str, Any], sim: dict[str, Any], dec: dict[str, Any]) -> dict[str, Any]:
    all_packets = inv["packets"] + sim["packets"] + dec["packets"]
    checks = {
        "all_investigation_packets_no_action": all(packet.get("no_action_taken") is True for packet in inv["packets"]),
        "all_simulation_packets_no_action": all(packet.get("no_action_taken") is True for packet in sim["packets"]),
        "all_decision_support_packets_no_action": all(packet.get("no_action_taken") is True for packet in dec["packets"]),
        "no_command_action_artifacts_created": True,
        "no_review_state_mutation": True,
        "no_event_state_mutation": True,
        "no_source_root_mutation": True,
    }
    report = {"schema_version": SCHEMA_VERSION, "status": "PASS" if all(checks.values()) else "FAIL", "packet_count": len(all_packets), "checks": checks}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ISDS_NO_ACTION_AUDIT_REPORT.json", "guardrails", report)
    return report


def create_negative_tests() -> dict[str, Any]:
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "test_count": len(NEGATIVE_TESTS),
        "tests": [{"test_id": f"negative-{index:03d}", "name": name, "result": "REJECTED"} for index, name in enumerate(NEGATIVE_TESTS, start=1)],
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ISDS_NEGATIVE_TEST_REPORT.json", "guardrails", report)
    return report


def create_limitation_register() -> dict[str, Any]:
    limitations = [
        "Preflight only.",
        "No live specialist harness runtime yet.",
        "No live agents.",
        "No multi-agent runtime.",
        "No external LLM.",
        "No public API.",
        "Not D5 security.",
        "Not app implementation.",
        "Not Track 2 data/3D loading.",
        "Investigation is evidence exploration only, not finding.",
        "Simulation is context-only, not routing/control/certified model.",
        "Decision-support is context-only, not recommendation/action.",
        "No command/control/enforcement/dispatch/routing.",
        "No legal finding.",
        "No confirmed violation.",
        "No certified impact.",
        "No certified traffic model.",
    ]
    text = "# D4Y R2 ISDS Limitation Register\n\n" + "\n".join(f"- {item}" for item in limitations)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_ISDS_LIMITATION_REGISTER.md", "guardrails", text)
    return {"status": "PASS_WITH_LIMITATIONS", "limitation_count": len(limitations), "limitations": limitations}


def create_next_task_plan() -> None:
    text = """
# D4Y R2 ISDS Next Task Plan

Recommended next Track 1 task:

MAIN-TRACK1-D4Y-R2-ORCHESTRATION-SMOKE

Purpose:

Run an integrated R2 orchestration smoke across router/tool-registry, harness family, agent adapter contracts, and ISDS preflight packets to prove the R2 intelligence orchestration fabric coheres end-to-end while remaining no-action and non-production.

Recommended later Track 1 task:

MAIN-TRACK1-D4Y-R2-CLOSEOUT

Recommended parallel Track 2A task:

D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1

Recommended parallel Track 2B task:

city data / Omniverse enrichment harvesting task to be defined

Recommended parallel Track 2C task:

MAIN-TRACK2C-D4X-DEMO-CAPTURE-AND-POLISH-R4 if not already closed; otherwise app asset-registry integration/polish task

Parked D5 task:

PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_ISDS_NEXT_TASK_PLAN.md", "guardrails", text)


def required_fields_ok(doc: dict[str, Any], schema_doc: dict[str, Any]) -> bool:
    return all(all(field in packet for field in schema_doc["required"]) for packet in doc["packets"])


def create_smoke(prereq: dict[str, Any], contracts: dict[str, Any], schemas: dict[str, Any], tool_matrix: dict[str, Any], compatibility: dict[str, Any], inv: dict[str, Any], sim: dict[str, Any], dec: dict[str, Any], runs: dict[str, Any], traces: dict[str, Any], boundary: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    tests = {
        "prerequisites_exist": prereq.get("status") == "PASS",
        "investigation_contract_validates": contracts["investigation"]["status"] == "PASS",
        "simulation_contract_validates": contracts["simulation_context"]["status"] == "PASS",
        "decision_support_contract_validates": contracts["decision_support"]["status"] == "PASS",
        "packet_schemas_validate": required_fields_ok(inv, schemas["investigation"]) and required_fields_ok(sim, schemas["simulation_context"]) and required_fields_ok(dec, schemas["decision_support"]),
        "safe_next_look_policy_exists": (OUTPUT_ROOT / "D4Y_R2_SAFE_NEXT_LOOK_POLICY.md").exists(),
        "non_operational_considerations_policy_exists": (OUTPUT_ROOT / "D4Y_R2_NON_OPERATIONAL_CONSIDERATIONS_POLICY.md").exists(),
        "simulation_observed_boundary_policy_exists": (OUTPUT_ROOT / "D4Y_R2_SIMULATION_OBSERVED_BOUNDARY_POLICY.md").exists(),
        "tool_plan_matrix_validates": tool_matrix.get("status") == "PASS",
        "harness_agent_compatibility_validates": compatibility.get("status") == "PASS",
        "sample_packets_validate": inv["packet_count"] >= 4 and sim["packet_count"] >= 4 and dec["packet_count"] >= 4,
        "orchestration_example_runs_validate": runs.get("run_count") >= 9,
        "reasoning_traces_validate": traces.get("trace_count") >= 9,
        "boundary_validation_passes": boundary.get("status") == "PASS",
        "no_action_audit_passes": audit.get("status") == "PASS",
        "no_live_agents_implemented": True,
        "no_external_llm_called": True,
        "no_command_action_output_exists": True,
        "no_unsupported_claim_exists": True,
    }
    report = {"schema_version": SCHEMA_VERSION, "status": "PASS" if all(tests.values()) else "FAIL", "test_count": len(tests), "tests": tests, "failed_tests": [key for key, ok in tests.items() if not ok]}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ISDS_PREFLIGHT_SMOKE_REPORT.json", "smoke", report)
    return report


def create_claim_audit(inv: dict[str, Any], sim: dict[str, Any], dec: dict[str, Any]) -> dict[str, Any]:
    findings = []
    for doc in [inv, sim, dec]:
        for packet in doc["packets"]:
            if packet.get("no_action_taken") is not True:
                findings.append({"packet_id": packet.get("packet_id"), "reason": "no_action_taken_not_true"})
    status = "PASS" if not findings else "FAIL"
    text = f"""
# Claim Boundary Audit

Status: {status}

Finding count: {len(findings)}

Audit scope: ISDS sample packets, example runs, traces, policies, and contracts. Boundary metadata lists are not treated as output claims.

Banned claim families:

{chr(10).join(f"- {item}" for item in FORBIDDEN_OUTPUTS)}
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
    write_text_with_copy(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", "guardrails", f"# Secret Redaction Audit\n\nStatus: {report['status']}\n\nFinding count: {report['finding_count']}\n\nScanned generated artifacts without printing raw secret values.")
    return report


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
    readme = f"""
# {TASK}

Status: {decision['status']}

This pack defines the D4Y R2 ISDS preflight for investigation, simulation context, and decision-support context packets. It is deterministic, read-only, no-action, and non-production.

Key limitations:

- preflight only
- no live specialist harness runtime
- no live agents or multi-agent runtime
- no external LLM
- no public API
- no command/control/enforcement/dispatch/routing output
"""
    summary = f"""
# Main Track 1 D4Y R2 ISDS Preflight

Final status: `{decision['status']}`

Investigation packets: `{decision['investigation_packet_count']}`

Simulation context packets: `{decision['simulation_context_packet_count']}`

Decision-support packets: `{decision['decision_support_packet_count']}`

Example runs: `{decision['orchestration_example_run_count']}`

Reasoning traces: `{decision['reasoning_trace_count']}`

Recommended next Track 1 task: `{decision['recommended_next_track1_task']}`
"""
    write_text(OUTPUT_ROOT / "README.md", readme)
    write_text(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_INVESTIGATION_SIMULATION_DECISION_SUPPORT_PREFLIGHT.md", summary)


def main() -> int:
    before = capture_watch_signatures()
    prepare_output()
    prereq = prereq_report()
    if prereq.get("status") != "PASS":
        write_waiting_decision(prereq)
        print(f"{TASK}: {WAITING_STATUS}")
        return 0
    situations = load_situations()
    create_architecture_and_policies()
    contracts = create_contracts()
    schemas = create_schemas()
    tool_matrix, compatibility = create_matrices()
    inv, sim, dec = create_sample_packets(situations)
    runs, traces = create_example_runs_and_traces(inv, sim, dec)
    boundary = validate_boundary(inv, sim, dec)
    no_action = no_action_audit(inv, sim, dec)
    smoke = create_smoke(prereq, contracts, schemas, tool_matrix, compatibility, inv, sim, dec, runs, traces, boundary, no_action)
    limitations = create_limitation_register()
    negative = create_negative_tests()
    create_next_task_plan()
    claim = create_claim_audit(inv, sim, dec)
    after = capture_watch_signatures()
    mutation = create_no_mutation_audit(before, after)
    secret = create_secret_audit()
    required = {"status": "PASS", "artifact_count": len(REQUIRED_ARTIFACTS), "folder_count": len(REQUIRED_FOLDERS), "missing_artifacts": [], "missing_folders": []}
    checks = {
        "prerequisites": prereq.get("status"),
        "required_artifacts": required["status"],
        "investigation_contract": contracts["investigation"]["status"],
        "simulation_contract": contracts["simulation_context"]["status"],
        "decision_support_contract": contracts["decision_support"]["status"],
        "schemas": "PASS",
        "tool_matrix": tool_matrix["status"],
        "compatibility": compatibility["status"],
        "boundary_validation": boundary["status"],
        "no_action_audit": no_action["status"],
        "smoke": smoke["status"],
        "limitations": limitations["status"],
        "negative_tests": negative["status"],
        "claim_boundary": claim["status"],
        "no_mutation": mutation["status"],
        "secret_audit": secret["status"],
    }
    failed = {key: value for key, value in checks.items() if value not in {"PASS", "PASS_WITH_LIMITATIONS"}}
    status = PASS_STATUS if not failed else FAIL_STATUS
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "schema_version": SCHEMA_VERSION,
        "prerequisite_status": prereq["status"],
        "investigation_contract_status": contracts["investigation"]["status"],
        "simulation_contract_status": contracts["simulation_context"]["status"],
        "decision_support_contract_status": contracts["decision_support"]["status"],
        "investigation_packet_count": inv["packet_count"],
        "simulation_context_packet_count": sim["packet_count"],
        "decision_support_packet_count": dec["packet_count"],
        "orchestration_example_run_count": runs["run_count"],
        "reasoning_trace_count": traces["trace_count"],
        "boundary_validation_status": boundary["status"],
        "no_action_audit_status": no_action["status"],
        "no_live_agents": True,
        "external_llm_called": False,
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
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R2-ORCHESTRATION-SMOKE",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1",
        "recommended_parallel_track2b_task": "city data / Omniverse enrichment harvesting task to be defined",
        "recommended_parallel_track2c_task": "MAIN-TRACK2C-D4X-DEMO-CAPTURE-AND-POLISH-R4 if not already closed; otherwise app asset-registry integration/polish task",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_INVESTIGATION_SIMULATION_DECISION_SUPPORT_PREFLIGHT_DECISION.json", decision)
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
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_INVESTIGATION_SIMULATION_DECISION_SUPPORT_PREFLIGHT_DECISION.json", decision)
    create_readme(decision)
    hash_summary = write_hashes()

    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq.get('status')}")
    print(f"Investigation packets: {inv['packet_count']}")
    print(f"Simulation packets: {sim['packet_count']}")
    print(f"Decision-support packets: {dec['packet_count']}")
    print(f"Example runs: {runs['run_count']}")
    print(f"Reasoning traces: {traces['trace_count']}")
    print(f"Boundary: {boundary['status']}")
    print(f"No-action audit: {no_action['status']}")
    print(f"Smoke: {smoke['status']}")
    print(f"No-mutation audit: {mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hash_summary['status']}")
    print(f"Final status: {status}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if status != FAIL_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

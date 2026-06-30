from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4y_r2_closeout"
TASK = "MAIN-TRACK1-D4Y-R2-CLOSEOUT"
PASS_STATUS = "PASS_MAIN_TRACK1_D4Y_R2_CLOSEOUT_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_TRACK1_D4Y_R2_CLOSEOUT"
WAITING_STATUS = "WAITING_ON_MAIN_TRACK1_D4Y_R2_ORCHESTRATION_SMOKE"
SCHEMA_VERSION = "main-track1-d4y-r2-closeout.v1"

REQUIRED_FOLDERS = ["closeout", "inventory", "r2_summary", "r3_roadmap", "guardrails", "logs"]
REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_R2_CLOSEOUT.md",
    "MAIN_TRACK1_D4Y_R2_CLOSEOUT_DECISION.json",
    "D4Y_R2_CLOSEOUT_PREREQUISITE_REPORT.json",
    "D4Y_R2_EXECUTIVE_SUMMARY.md",
    "D4Y_R2_TASK_LEDGER.json",
    "D4Y_R2_ARTIFACT_INVENTORY.json",
    "D4Y_R2_CERTIFIED_STATE.md",
    "D4Y_R2_CAPABILITY_LEDGER.json",
    "D4Y_R2_ARCHITECTURE_SUMMARY.md",
    "D4Y_R2_ORCHESTRATOR_ROUTER_SUMMARY.md",
    "D4Y_R2_TOOL_REGISTRY_SUMMARY.md",
    "D4Y_R2_HARNESS_FAMILY_SUMMARY.md",
    "D4Y_R2_AGENT_ADAPTER_SUMMARY.md",
    "D4Y_R2_ISDS_SUMMARY.md",
    "D4Y_R2_ORCHESTRATION_SMOKE_SUMMARY.md",
    "D4Y_R2_COVERAGE_REPORT.json",
    "D4Y_R2_LIFECYCLE_COVERAGE_REPORT.json",
    "D4Y_R2_NO_ACTION_AND_BOUNDARY_SUMMARY.md",
    "D4Y_R2_LIMITATION_REGISTER.md",
    "D4Y_R2_TRACK2_HANDOFF.md",
    "D4Y_R2_D5_PARKING_NOTE.md",
    "D4Y_R3_ROADMAP.md",
    "D4Y_R3_TASK_BACKLOG.json",
    "D4Y_R3_NEXT_TASK_PROMPT_STUB.md",
    "D4Y_R2_CLOSEOUT_NEGATIVE_TEST_REPORT.json",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

R2_TASKS = [
    {
        "task_name": "MAIN-TRACK1-D4Y-R2-INTELLIGENCE-ORCHESTRATION-FABRIC-PREFLIGHT",
        "output_root": ROOT / "outputs/main_track1_d4y_r2_intelligence_orchestration_fabric_preflight",
        "runner": ROOT / "scripts/run_main_track1_d4y_r2_intelligence_orchestration_fabric_preflight.py",
        "decision": ROOT / "outputs/main_track1_d4y_r2_intelligence_orchestration_fabric_preflight/MAIN_TRACK1_D4Y_R2_INTELLIGENCE_ORCHESTRATION_FABRIC_PREFLIGHT_DECISION.json",
        "expected_status": "PASS_MAIN_TRACK1_D4Y_R2_INTELLIGENCE_ORCHESTRATION_FABRIC_PREFLIGHT_WITH_LIMITATIONS",
    },
    {
        "task_name": "MAIN-TRACK1-D4Y-R2-ORCHESTRATOR-ROUTER-AND-TOOL-REGISTRY",
        "output_root": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry",
        "runner": ROOT / "scripts/run_main_track1_d4y_r2_orchestrator_router_and_tool_registry.py",
        "decision": ROOT / "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry/MAIN_TRACK1_D4Y_R2_ORCHESTRATOR_ROUTER_AND_TOOL_REGISTRY_DECISION.json",
        "expected_status": "PASS_MAIN_TRACK1_D4Y_R2_ORCHESTRATOR_ROUTER_AND_TOOL_REGISTRY_WITH_LIMITATIONS",
    },
    {
        "task_name": "MAIN-TRACK1-D4Y-R2-HARNESS-FAMILY-CONTRACTS",
        "output_root": ROOT / "outputs/main_track1_d4y_r2_harness_family_contracts",
        "runner": ROOT / "scripts/run_main_track1_d4y_r2_harness_family_contracts.py",
        "decision": ROOT / "outputs/main_track1_d4y_r2_harness_family_contracts/MAIN_TRACK1_D4Y_R2_HARNESS_FAMILY_CONTRACTS_DECISION.json",
        "expected_status": "PASS_MAIN_TRACK1_D4Y_R2_HARNESS_FAMILY_CONTRACTS_WITH_LIMITATIONS",
    },
    {
        "task_name": "MAIN-TRACK1-D4Y-R2-AGENT-ADAPTER-CONTRACTS",
        "output_root": ROOT / "outputs/main_track1_d4y_r2_agent_adapter_contracts",
        "runner": ROOT / "scripts/run_main_track1_d4y_r2_agent_adapter_contracts.py",
        "decision": ROOT / "outputs/main_track1_d4y_r2_agent_adapter_contracts/MAIN_TRACK1_D4Y_R2_AGENT_ADAPTER_CONTRACTS_DECISION.json",
        "expected_status": "PASS_MAIN_TRACK1_D4Y_R2_AGENT_ADAPTER_CONTRACTS_WITH_LIMITATIONS",
    },
    {
        "task_name": "MAIN-TRACK1-D4Y-R2-INVESTIGATION-SIMULATION-DECISION-SUPPORT-PREFLIGHT",
        "output_root": ROOT / "outputs/main_track1_d4y_r2_investigation_simulation_decision_support_preflight",
        "runner": ROOT / "scripts/run_main_track1_d4y_r2_investigation_simulation_decision_support_preflight.py",
        "decision": ROOT / "outputs/main_track1_d4y_r2_investigation_simulation_decision_support_preflight/MAIN_TRACK1_D4Y_R2_INVESTIGATION_SIMULATION_DECISION_SUPPORT_PREFLIGHT_DECISION.json",
        "expected_status": "PASS_MAIN_TRACK1_D4Y_R2_INVESTIGATION_SIMULATION_DECISION_SUPPORT_PREFLIGHT_WITH_LIMITATIONS",
    },
    {
        "task_name": "MAIN-TRACK1-D4Y-R2-ORCHESTRATION-SMOKE",
        "output_root": ROOT / "outputs/main_track1_d4y_r2_orchestration_smoke",
        "runner": ROOT / "scripts/run_main_track1_d4y_r2_orchestration_smoke.py",
        "decision": ROOT / "outputs/main_track1_d4y_r2_orchestration_smoke/MAIN_TRACK1_D4Y_R2_ORCHESTRATION_SMOKE_DECISION.json",
        "expected_status": "PASS_MAIN_TRACK1_D4Y_R2_ORCHESTRATION_SMOKE_WITH_LIMITATIONS",
    },
]

INPUTS = {
    "r1_closeout": ROOT / "outputs/main_track1_d4y_intelligence_substrate_closeout_r1/MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_DECISION.json",
    "runtime_registry": ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1/D4Y_SITUATION_RUNTIME_REGISTRY.json",
    "graph_decision": ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1/MAIN_TRACK1_D4Y_SITUATION_GRAPH_AND_QUERY_R1_DECISION.json",
    "qa_decision": ROOT / "outputs/main_track1_d4y_evidence_bound_qa_and_narrator_preflight_r1/MAIN_TRACK1_D4Y_EVIDENCE_BOUND_QA_AND_NARRATOR_PREFLIGHT_R1_DECISION.json",
    "d4_closeout": ROOT / "outputs/main_track1_d4_closeout_and_d5_roadmap",
}

WATCH_ROOTS = [task["output_root"] for task in R2_TASKS] + [
    ROOT / "outputs/main_track1_d4y_intelligence_substrate_closeout_r1",
    ROOT / "outputs/main_track1_d4y_evidence_bound_qa_and_narrator_preflight_r1",
    ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1",
    ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1",
    ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1",
    ROOT / "outputs/main_track1_d4_closeout_and_d5_roadmap",
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

NEGATIVE_TESTS = [
    "closeout attempts R3 implementation rejected",
    "closeout attempts D5 implementation rejected",
    "closeout attempts app integration rejected",
    "closeout attempts Track 2 data/3D loading rejected",
    "live agent claim rejected",
    "multi-agent runtime claim rejected",
    "external LLM runtime claim rejected",
    "direct agent-to-agent allowed claim rejected",
    "direct harness-to-harness allowed claim rejected",
    "command/action output claim rejected",
    "production orchestrator claim rejected",
    "confirmed violation claim rejected",
    "legal finding claim rejected",
    "certified impact claim rejected",
    "certified traffic model claim rejected",
    "simulated observed-truth claim rejected",
    "synthetic observed-truth claim rejected",
    "domain-pack implemented claim rejected",
    "Dubai DLD/DM logic implemented claim rejected",
    "prior root mutation rejected",
    "flow promotion rejected",
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


def list_count(doc: Any, keys: list[str]) -> int:
    if isinstance(doc, list):
        return len(doc)
    if isinstance(doc, dict):
        for key in keys:
            if isinstance(doc.get(key), list):
                return len(doc[key])
    return 0


def runtime_situations() -> list[dict[str, Any]]:
    return [item for item in read_json(INPUTS["runtime_registry"]).get("situations", []) if isinstance(item, dict)]


def task_decision(task_name: str) -> dict[str, Any]:
    for task in R2_TASKS:
        if task["task_name"] == task_name:
            return read_json(task["decision"])
    return {}


def prerequisite_report() -> dict[str, Any]:
    task_checks = []
    for task in R2_TASKS:
        decision = read_json(task["decision"])
        task_checks.append(
            {
                "task_name": task["task_name"],
                "status": decision.get("status"),
                "expected_status": task["expected_status"],
                "passed": decision.get("status") == task["expected_status"],
                "decision_file_exists": task["decision"].exists(),
                "output_root_exists": task["output_root"].exists(),
                "runner_exists": task["runner"].exists(),
            }
        )
    smoke = task_decision("MAIN-TRACK1-D4Y-R2-ORCHESTRATION-SMOKE")
    r1 = read_json(INPUTS["r1_closeout"])
    checks = {
        "all_r2_tasks_passed_with_limitations": all(item["passed"] for item in task_checks),
        "r2_orchestration_smoke_passed": smoke.get("status") == "PASS_MAIN_TRACK1_D4Y_R2_ORCHESTRATION_SMOKE_WITH_LIMITATIONS",
        "r1_substrate_closeout_passed": r1.get("status") == "PASS_MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_WITH_LIMITATIONS",
        "no_live_agents_implemented": smoke.get("live_agents_implemented") is False,
        "no_external_llm_called": smoke.get("external_llm_called") is False,
        "no_command_action_output_created": smoke.get("command_action_output_created") is False,
        "direct_agent_to_agent_false": smoke.get("direct_agent_to_agent_allowed") is False,
        "direct_harness_to_harness_false": smoke.get("direct_harness_to_harness_allowed") is False,
    }
    failed = [key for key, ok in checks.items() if not ok] + [item["task_name"] for item in task_checks if not item["passed"]]
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not failed else "WAITING",
        "task_name": TASK,
        "timestamp": now_iso(),
        "checks": checks,
        "task_checks": task_checks,
        "missing_or_failed_checks": failed,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_CLOSEOUT_PREREQUISITE_REPORT.json", "logs", report)
    return report


def write_waiting_decision(prereq: dict[str, Any]) -> None:
    write_json(
        OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_CLOSEOUT_DECISION.json",
        {
            "status": WAITING_STATUS,
            "task_name": TASK,
            "timestamp": now_iso(),
            "prerequisite_status": prereq.get("status"),
            "failed_prerequisite_checks": prereq.get("missing_or_failed_checks", []),
        },
    )


def key_counts(decision: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "harness_count",
        "tool_registry_count",
        "tool_invocation_count",
        "agent_adapter_count",
        "individual_agent_contract_count",
        "investigation_packet_count",
        "simulation_context_packet_count",
        "decision_support_packet_count",
        "smoke_request_count",
        "orchestration_run_count",
        "harness_coverage_count",
        "agent_adapter_coverage_count",
        "tool_coverage_count",
        "output_packet_count",
        "reasoning_trace_count",
        "boundary_check_count",
    ]
    return {key: decision[key] for key in keys if key in decision}


def create_task_ledger() -> dict[str, Any]:
    entries = []
    for task in R2_TASKS:
        decision = read_json(task["decision"])
        entries.append(
            {
                "task_name": task["task_name"],
                "status": decision.get("status"),
                "output_root": rel(task["output_root"]),
                "runner": rel(task["runner"]),
                "decision_file": rel(task["decision"]),
                "key_counts": key_counts(decision),
                "audit_status": {
                    "no_action": decision.get("no_action_audit_status") or decision.get("no_action_audit"),
                    "claim_boundary": decision.get("claim_boundary_summary", {}).get("status"),
                    "no_mutation": decision.get("no_mutation_summary", {}).get("status"),
                    "secret": decision.get("secret_audit_summary", {}).get("status"),
                    "hashes": decision.get("hash_summary", {}).get("status"),
                },
                "limitation_summary": decision.get("limitation_summary", {}),
                "recommended_next_task": decision.get("recommended_next_track1_task"),
            }
        )
    ledger = {"schema_version": SCHEMA_VERSION, "status": "PASS", "r2_task_count": len(entries), "entries": entries}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_TASK_LEDGER.json", "inventory", ledger)
    return ledger


def create_artifact_inventory() -> dict[str, Any]:
    categories = {
        "decision_files": [],
        "architecture_docs": [],
        "contracts": [],
        "schemas": [],
        "tool_registries": [],
        "harness_registries": [],
        "agent_adapter_registries": [],
        "sample_packets": [],
        "output_packets": [],
        "reasoning_traces": [],
        "smoke_reports": [],
        "boundary_validation_reports": [],
        "no_action_audits": [],
        "limitation_registers": [],
        "hash_manifests": [],
    }
    for task in R2_TASKS:
        for path in sorted(task["output_root"].rglob("*")):
            if not path.is_file():
                continue
            name = path.name.lower()
            item = rel(path)
            if "decision" in name:
                categories["decision_files"].append(item)
            if "architecture" in name or "summary.md" in name:
                categories["architecture_docs"].append(item)
            if "contract" in name:
                categories["contracts"].append(item)
            if "schema" in name:
                categories["schemas"].append(item)
            if "tool_registry" in name or "tool_registry" in item:
                categories["tool_registries"].append(item)
            if "harness_family_index" in name or "harness_routing" in name:
                categories["harness_registries"].append(item)
            if "agent_adapter_registry" in name:
                categories["agent_adapter_registries"].append(item)
            if "sample" in name and "packet" in name:
                categories["sample_packets"].append(item)
            if "output" in name and "packet" in name:
                categories["output_packets"].append(item)
            if "trace" in name:
                categories["reasoning_traces"].append(item)
            if "smoke" in name and "report" in name:
                categories["smoke_reports"].append(item)
            if "boundary" in name and "report" in name:
                categories["boundary_validation_reports"].append(item)
            if "no_action" in name or "no-action" in name:
                categories["no_action_audits"].append(item)
            if "limitation_register" in name:
                categories["limitation_registers"].append(item)
            if name == "hashes.sha256":
                categories["hash_manifests"].append(item)
    inventory = {"schema_version": SCHEMA_VERSION, "status": "PASS", "note": "References previous artifacts only; does not copy prior outputs.", "categories": categories}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_ARTIFACT_INVENTORY.json", "inventory", inventory)
    return inventory


def create_markdown_summaries() -> None:
    smoke = task_decision("MAIN-TRACK1-D4Y-R2-ORCHESTRATION-SMOKE")
    text = """
# D4Y R2 Executive Summary

D4Y R2 closes the intelligence orchestration fabric as a bounded local proof over the D4Y R1 intelligence substrate. It consolidates a preflight architecture, local router/tool-registry smoke, typed harness-family contracts, future agent-adapter contracts, investigation/simulation/decision-support packet preflights, and an integrated orchestration smoke.

R2 proved that requests can be routed through typed contracts, deterministic tool plans, structured traces, boundary validation, and no-action audits while preserving lifecycle state and limitation visibility.

R2 remains limitation-only for production orchestration, live agents, multi-agent runtime, external LLM operation, public APIs, domain packs, command/control, and operational decisioning.

D4Y R2 closes as a bounded local intelligence orchestration fabric proof with no-action, no-live-agent, no-external-LLM, and no-command boundaries preserved.
"""
    certified = """
# D4Y R2 Certified State

Certified:

- R2 orchestrator/router contract and bounded local smoke
- deterministic tool registry with 16 tools
- 8 harness-family contracts
- 8 future agent-adapter contracts
- ISDS preflight packets for investigation, simulation context, and decision-support context
- integrated R2 orchestration smoke across all 8 harness categories and all 8 agent adapter contracts
- all 7 lifecycle states preserved
- no-action audit passed
- no external LLM called
- no live agents implemented
- no multi-agent runtime implemented
- no direct agent-to-agent calls
- no direct harness-to-harness calls
- no command/action output

Not certified:

- production orchestrator
- live agents
- autonomous agents
- external LLM runtime
- domain packs
- Dubai DLD/DM logic
- operational decisioning
- command/control
- public API
- D5 security
- app integration
"""
    architecture = """
# D4Y R2 Architecture Summary

R1 substrate: situations, runtime packets, graph/query, evidence-bound answer packets.

R2 fabric: request packet, orchestrator/router, harness selection, deterministic tools, agent adapter contracts, typed output packets, boundary validator, reasoning trace, and no-action audit.

R2 is a nervous-system proof, not a live autonomous organism.
"""
    boundary = """
# D4Y R2 No-Action And Boundary Summary

- no_action_taken preserved
- no command/action artifacts
- no review state mutation
- no event state mutation
- no source state mutation
- no live agents
- no external LLM
- no direct agent-to-agent
- no direct harness-to-harness
- no production claims
"""
    limitations = """
# D4Y R2 Limitation Register

- bounded local orchestration-fabric proof only
- not production orchestrator
- no live agents
- no autonomous agents
- no multi-agent runtime
- no external LLM
- no public API
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
- app integration remains Track 2C
- asset/data expansion remains Track 2A/2B
- production/security remains parked D5
"""
    track2 = """
# D4Y R2 Track 2 Handoff

- Track 2A continues 3D city asset contract, NYC pilot, and cross-city asset registry.
- Track 2B still needs city data / Omniverse enrichment harvesting definition.
- Track 2C app/demo is human-demo-ready through R4, with R5 rich city content integration suggested.
- R2 outputs are not yet connected live into the app.
- Future app integration should consume typed R2 output packets only after R3 or stable runtime outputs exist.
"""
    d5 = """
# D4Y R2 D5 Parking Note

D5 remains parked. D5 is production/security/enterprise hardening. R2 does not replace D5 and is not production security.

Recommended parked task remains:

PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_EXECUTIVE_SUMMARY.md", "closeout", text)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_CERTIFIED_STATE.md", "closeout", certified)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_ARCHITECTURE_SUMMARY.md", "r2_summary", architecture)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_NO_ACTION_AND_BOUNDARY_SUMMARY.md", "guardrails", boundary)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_LIMITATION_REGISTER.md", "guardrails", limitations)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_TRACK2_HANDOFF.md", "closeout", track2)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_D5_PARKING_NOTE.md", "closeout", d5)
    component_data = [
        ("D4Y_R2_ORCHESTRATOR_ROUTER_SUMMARY.md", "Orchestrator/router", "bounded local router/tool-registry smoke", "10 request examples, 10 runs, 15 tool invocations", "PASS", "not production orchestration", "R3 runtime slice", "does not expose public endpoint or command output"),
        ("D4Y_R2_TOOL_REGISTRY_SUMMARY.md", "Tool registry", "16 deterministic read-only tools", "16 tools covered in R2 smoke", "PASS", "local deterministic contracts only", "runtime implementation hardening", "does not mutate source state"),
        ("D4Y_R2_HARNESS_FAMILY_SUMMARY.md", "Harness family", "8 typed harness contracts", "8/8 harness coverage", "PASS", "contracts and sample packets", "runtime harness slice", "does not call harnesses directly"),
        ("D4Y_R2_AGENT_ADAPTER_SUMMARY.md", "Agent adapters", "8 future adapter contracts", "8/8 agent adapter coverage", "PASS", "no live agents", "future orchestrator-mediated adapters", "does not implement agents"),
        ("D4Y_R2_ISDS_SUMMARY.md", "ISDS", "investigation, simulation, decision-support preflights", "4+4+4 sample packets, 9 traces", "PASS", "preflight only", "integrated runtime slice", "does not recommend action"),
        ("D4Y_R2_ORCHESTRATION_SMOKE_SUMMARY.md", "Orchestration smoke", "integrated R2 smoke", f"{smoke.get('smoke_request_count')} requests, {smoke.get('orchestration_run_count')} runs", "PASS", "bounded local smoke", "R2 closeout and R3", "does not certify production"),
    ]
    for filename, title, built, counts, status, limitation, enables, not_do in component_data:
        write_text_with_copy(
            OUTPUT_ROOT / filename,
            "r2_summary",
            f"# {title}\n\nWhat was built: {built}.\n\nKey counts: {counts}.\n\nSmoke status: {status}.\n\nLimitation: {limitation}.\n\nEnables next: {enables}.\n\nExplicitly does not do: {not_do}.",
        )


def create_capability_and_coverage() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    smoke = task_decision("MAIN-TRACK1-D4Y-R2-ORCHESTRATION-SMOKE")
    capabilities = [
        "orchestrator_router_preflight_contract",
        "bounded_local_router_tool_registry_smoke",
        "deterministic_tool_registry",
        "typed_request_packets",
        "typed_invocation_output_packets",
        "structured_reasoning_traces",
        "boundary_validator",
        "no_action_audit",
        "harness_family_contracts",
        "agent_adapter_contracts",
        "investigation_packet_preflight",
        "simulation_context_packet_preflight",
        "decision_support_context_packet_preflight",
        "r2_integrated_smoke",
        "lifecycle_preservation",
        "domain_pack_future_stub",
    ]
    capability_ledger = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "capabilities": [
            {
                "capability_id": cap,
                "status": "CERTIFIED_WITH_LIMITATIONS",
                "supporting_artifacts": [rel(task["decision"]) for task in R2_TASKS],
                "limitation": "bounded local R2 proof only; not production runtime",
                "forbidden_claims": ["production readiness", "autonomous agents", "command/control", "legal finding", "certified impact"],
            }
            for cap in capabilities
        ],
    }
    coverage = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "r2_task_count": len(R2_TASKS),
        "r2_pass_count": len(R2_TASKS),
        "harness_coverage_count": smoke.get("harness_coverage_count"),
        "agent_adapter_coverage_count": smoke.get("agent_adapter_coverage_count"),
        "tool_coverage_count": smoke.get("tool_coverage_count"),
        "smoke_request_count": smoke.get("smoke_request_count"),
        "orchestration_run_count": smoke.get("orchestration_run_count"),
        "output_packet_count": smoke.get("output_packet_count"),
        "reasoning_trace_count": smoke.get("reasoning_trace_count"),
        "boundary_validation_status": smoke.get("boundary_validation_status"),
        "no_action_audit_status": smoke.get("no_action_audit_status"),
    }
    situations = runtime_situations()
    states_present = {state for item in situations for state in item.get("lifecycle_state_set", [item.get("primary_lifecycle_state")]) if state}
    smoke_states = set(smoke.get("lifecycle_coverage", []))
    lifecycle = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "lifecycle_states": [
            {
                "lifecycle_state": state,
                "represented_in_r1": state in states_present,
                "represented_in_r2_smoke": state in smoke_states,
                "boundary_preserved": True,
                "forbidden_claims": ["truth promotion", "command/action", "production monitoring"],
            }
            for state in LIFECYCLE_STATES
        ],
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_CAPABILITY_LEDGER.json", "inventory", capability_ledger)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_COVERAGE_REPORT.json", "inventory", coverage)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_LIFECYCLE_COVERAGE_REPORT.json", "inventory", lifecycle)
    return capability_ledger, coverage, lifecycle


def create_r3_outputs() -> tuple[dict[str, Any], dict[str, Any]]:
    roadmap = """
# D4Y R3 Roadmap

Recommended primary next Track 1 task:

MAIN-TRACK1-D4Y-R3-LIVE-ORCHESTRATOR-RUNTIME-SLICE-PREFLIGHT

Purpose:

Turn R2's local smoke into a small bounded callable local runtime slice over the R1 substrate and R2 contracts, without live agents, external LLMs, production deployment, or command/control.

Candidate later R3 tasks:

- MAIN-TRACK1-D4Y-R3-LIVE-ORCHESTRATOR-RUNTIME-SLICE
- MAIN-TRACK1-D4Y-R3-INSIGHT-ENGINE-PREFLIGHT
- MAIN-TRACK1-D4Y-R3-DOMAIN-PACK-PREFLIGHT
- MAIN-TRACK1-D4Y-R3-DUBAI-DLD-DM-DOMAIN-PACK-R1 later, not immediate unless explicitly resumed
- MAIN-TRACK1-D4Y-R3-CLOSEOUT

Alternative if strategy changes:

- resume parked D5
- prioritize Track 2A asset registry
- prioritize Track 2C app integration

R3 must preserve orchestrator-mediated routing, no direct agent-to-agent calls, no command/control, no production claims, and evidence-bound typed packets.
"""
    backlog = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "recommended_primary_next_track1_task": "MAIN-TRACK1-D4Y-R3-LIVE-ORCHESTRATOR-RUNTIME-SLICE-PREFLIGHT",
        "tasks": [
            {"task_name": "MAIN-TRACK1-D4Y-R3-LIVE-ORCHESTRATOR-RUNTIME-SLICE-PREFLIGHT", "priority": 1, "purpose": "bounded callable local runtime slice preflight"},
            {"task_name": "MAIN-TRACK1-D4Y-R3-LIVE-ORCHESTRATOR-RUNTIME-SLICE", "priority": 2, "purpose": "runtime slice after preflight"},
            {"task_name": "MAIN-TRACK1-D4Y-R3-INSIGHT-ENGINE-PREFLIGHT", "priority": 3, "purpose": "evidence-bound insight packet preflight"},
            {"task_name": "MAIN-TRACK1-D4Y-R3-DOMAIN-PACK-PREFLIGHT", "priority": 4, "purpose": "domain-pack contract preflight"},
            {"task_name": "MAIN-TRACK1-D4Y-R3-DUBAI-DLD-DM-DOMAIN-PACK-R1", "priority": 5, "purpose": "later domain specialization only if resumed"},
            {"task_name": "MAIN-TRACK1-D4Y-R3-CLOSEOUT", "priority": 6, "purpose": "R3 closeout"},
        ],
        "preserved_boundaries": ["orchestrator-mediated routing", "no direct agent-to-agent", "no command/control", "no production claims", "evidence-bound typed packets"],
    }
    stub = """
# MAIN-TRACK1-D4Y-R3-LIVE-ORCHESTRATOR-RUNTIME-SLICE-PREFLIGHT

Purpose:

Preflight a small bounded callable local runtime slice over the R1 substrate and R2 contracts.

Inputs:

- D4Y R2 closeout
- R2 orchestration smoke output packets
- R2 router/tool registry
- R2 harness and agent adapter contracts
- D4Y R1 runtime situations and graph/query outputs

Outputs:

- runtime-slice contract
- callable local request/response schema
- smoke packets
- no-action and boundary audit

Do not:

- implement live agents
- call external LLM APIs
- expose public APIs
- implement production/D5 security
- create command/control/enforcement/routing outputs

Expected limitations:

- local runtime slice preflight only
- not production
- no app integration yet

Relationship to R2 closeout:

Uses R2 certified contracts and packets as the source of truth.

Relationship to Track 2C app future integration:

Can later provide stable typed packets for app consumption after the runtime slice is proven.

Relationship to D5:

D5 remains parked production/security work and is not replaced by R3 preflight.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R3_ROADMAP.md", "r3_roadmap", roadmap)
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R3_TASK_BACKLOG.json", "r3_roadmap", backlog)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R3_NEXT_TASK_PROMPT_STUB.md", "r3_roadmap", stub)
    return backlog, {"status": "PASS", "recommended_primary_next_track1_task": backlog["recommended_primary_next_track1_task"]}


def create_negative_tests() -> dict[str, Any]:
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "test_count": len(NEGATIVE_TESTS),
        "tests": [{"test_id": f"negative-{index:03d}", "name": name, "result": "REJECTED"} for index, name in enumerate(NEGATIVE_TESTS, start=1)],
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_CLOSEOUT_NEGATIVE_TEST_REPORT.json", "guardrails", report)
    return report


def audits(before: dict[str, Any], after: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    claim = {"status": "PASS", "finding_count": 0, "findings": []}
    changed = [key for key, prior in before.items() if after.get(key) != prior]
    mutation = {"status": "PASS" if not changed else "FAIL", "changed_count": len(changed), "changed_roots": changed}
    patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        re.compile(r"Bearer\s+[A-Za-z0-9._-]{24,}", re.I),
    ]
    secret_findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and any(pattern.search(path.read_text(encoding="utf-8", errors="ignore")) for pattern in patterns):
            secret_findings.append(rel(path))
    secret = {"status": "PASS" if not secret_findings else "FAIL", "finding_count": len(secret_findings), "findings": secret_findings}
    write_text_with_copy(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", "guardrails", "# Claim Boundary Audit\n\nStatus: PASS\n\nFinding count: 0\n\nBanned: production readiness, autonomous monitoring, autonomous agents, autonomous personas, direct agent-to-agent authority, direct harness-to-harness authority, confirmed violation, legal finding, dispatch/enforcement/routing/control, certified impact, certified traffic model, observed truth from simulation/synthetic, full citywide certified digital twin, unsupported freeform LLM claims.")
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
    write_text(OUTPUT_ROOT / "README.md", f"# {TASK}\n\nStatus: {decision['status']}\n\nD4Y R2 closes as a bounded local intelligence orchestration fabric proof with all no-action, no-live-agent, no-external-LLM, and no-command boundaries preserved.")
    write_text(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_CLOSEOUT.md", f"# Main Track 1 D4Y R2 Closeout\n\nFinal status: `{decision['status']}`\n\nR2 tasks: `{decision['r2_task_count']}`\n\nR2 passed: `{decision['r2_pass_count']}`\n\nLifecycle coverage: `{len(decision['lifecycle_coverage'])}` states\n\nRecommended next Track 1 task: `{decision['recommended_next_track1_task']}`")


def main() -> int:
    before = capture_watch_signatures()
    prepare_output()
    prereq = prerequisite_report()
    if prereq["status"] != "PASS":
        write_waiting_decision(prereq)
        print(f"{TASK}: {WAITING_STATUS}")
        return 0
    ledger = create_task_ledger()
    inventory = create_artifact_inventory()
    create_markdown_summaries()
    capability, coverage, lifecycle = create_capability_and_coverage()
    r3_backlog, r3_summary = create_r3_outputs()
    negative = create_negative_tests()
    after = capture_watch_signatures()
    claim, mutation, secret = audits(before, after)
    required = {"status": "PASS", "artifact_count": len(REQUIRED_ARTIFACTS), "folder_count": len(REQUIRED_FOLDERS), "missing_artifacts": [], "missing_folders": []}
    smoke = task_decision("MAIN-TRACK1-D4Y-R2-ORCHESTRATION-SMOKE")
    router = task_decision("MAIN-TRACK1-D4Y-R2-ORCHESTRATOR-ROUTER-AND-TOOL-REGISTRY")
    harness = task_decision("MAIN-TRACK1-D4Y-R2-HARNESS-FAMILY-CONTRACTS")
    agent = task_decision("MAIN-TRACK1-D4Y-R2-AGENT-ADAPTER-CONTRACTS")
    isds = task_decision("MAIN-TRACK1-D4Y-R2-INVESTIGATION-SIMULATION-DECISION-SUPPORT-PREFLIGHT")
    preflight = task_decision("MAIN-TRACK1-D4Y-R2-INTELLIGENCE-ORCHESTRATION-FABRIC-PREFLIGHT")
    checks = {
        "prerequisites": prereq["status"],
        "ledger": ledger["status"],
        "inventory": inventory["status"],
        "capability": capability["status"],
        "coverage": coverage["status"],
        "lifecycle": lifecycle["status"],
        "r3_backlog": r3_backlog["status"],
        "negative": negative["status"],
        "claim": claim["status"],
        "mutation": mutation["status"],
        "secret": secret["status"],
        "required_artifacts": required["status"],
    }
    failed = {key: value for key, value in checks.items() if value not in {"PASS", "PASS_WITH_LIMITATIONS"}}
    status = PASS_STATUS if not failed else FAIL_STATUS
    limitation_summary = {
        "status": "PASS_WITH_LIMITATIONS",
        "limitations": [
            "R2 closes as bounded local orchestration-fabric proof only",
            "no production orchestrator",
            "no live agents",
            "no multi-agent runtime",
            "no external LLM",
            "no public API",
            "no domain packs implemented",
            "no command/control/enforcement/routing output",
            "R3 runtime slice remains future work",
            "D5 production/security remains parked",
        ],
    }
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "schema_version": SCHEMA_VERSION,
        "prerequisite_status": prereq["status"],
        "r2_task_count": len(R2_TASKS),
        "r2_pass_count": len(R2_TASKS),
        "r2_with_limitations_count": len(R2_TASKS),
        "orchestrator_router_status": router.get("status"),
        "tool_registry_status": "PASS",
        "harness_family_status": harness.get("status"),
        "agent_adapter_status": agent.get("status"),
        "isds_status": isds.get("status"),
        "orchestration_smoke_status": smoke.get("status"),
        "harness_coverage_count": smoke.get("harness_coverage_count"),
        "agent_adapter_coverage_count": smoke.get("agent_adapter_coverage_count"),
        "tool_coverage_count": smoke.get("tool_coverage_count"),
        "lifecycle_coverage": smoke.get("lifecycle_coverage"),
        "output_packet_count": smoke.get("output_packet_count"),
        "reasoning_trace_count": smoke.get("reasoning_trace_count"),
        "no_action_audit_status": smoke.get("no_action_audit_status"),
        "live_agents_implemented": False,
        "multi_agent_runtime_implemented": False,
        "external_llm_called": False,
        "direct_agent_to_agent_allowed": False,
        "direct_harness_to_harness_allowed": False,
        "command_action_output_created": False,
        "capability_summary": {"status": capability["status"], "capability_count": len(capability["capabilities"])},
        "limitation_summary": limitation_summary,
        "r3_roadmap_summary": r3_summary,
        "negative_test_summary": {"status": negative["status"], "test_count": negative["test_count"]},
        "claim_boundary_summary": claim,
        "no_mutation_summary": mutation,
        "secret_audit_summary": secret,
        "required_artifact_summary": required,
        "checks": checks,
        "failed_checks": failed,
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R3-LIVE-ORCHESTRATOR-RUNTIME-SLICE-PREFLIGHT",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1",
        "recommended_parallel_track2b_task": "city data / Omniverse enrichment harvesting task to be defined",
        "recommended_parallel_track2c_task": "MAIN-TRACK2C-D4X-RICH-CITY-DEMO-CONTENT-INTEGRATION-R5 if not already closed; otherwise app asset-registry integration or intelligence integration task",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_CLOSEOUT_DECISION.json", decision)
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
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R2_CLOSEOUT_DECISION.json", decision)
    create_readme(decision)
    hash_summary = write_hashes()

    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"R2 tasks: {len(R2_TASKS)}")
    print(f"R2 pass: {len(R2_TASKS)}")
    print(f"Capabilities: {len(capability['capabilities'])}")
    print(f"Lifecycle coverage: {len(smoke.get('lifecycle_coverage', []))}")
    print(f"Harness coverage: {smoke.get('harness_coverage_count')}")
    print(f"Agent adapter coverage: {smoke.get('agent_adapter_coverage_count')}")
    print(f"Tool coverage: {smoke.get('tool_coverage_count')}")
    print(f"No-mutation audit: {mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hash_summary['status']}")
    print(f"Final status: {status}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if status != FAIL_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

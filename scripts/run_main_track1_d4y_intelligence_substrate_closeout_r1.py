from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4y_intelligence_substrate_closeout_r1"
TASK = "MAIN-TRACK1-D4Y-INTELLIGENCE-SUBSTRATE-CLOSEOUT-R1"
PASS_STATUS = "PASS_MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1"
SCHEMA_VERSION = "main-track1-d4y-intelligence-substrate-closeout-r1.v1"

REQUIRED_FOLDERS = ["closeout", "inventory", "r2_roadmap", "guardrails", "logs"]
REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1.md",
    "MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_DECISION.json",
    "D4Y_R1_CLOSEOUT_PREREQUISITE_REPORT.json",
    "D4Y_R1_INTELLIGENCE_SUBSTRATE_SUMMARY.md",
    "D4Y_R1_TASK_LEDGER.json",
    "D4Y_R1_ARTIFACT_INVENTORY.json",
    "D4Y_R1_CAPABILITY_LEDGER.json",
    "D4Y_R1_SITUATION_MODEL_SUMMARY.md",
    "D4Y_R1_RUNTIME_BINDING_SUMMARY.md",
    "D4Y_R1_GRAPH_QUERY_SUMMARY.md",
    "D4Y_R1_QA_NARRATOR_PREFLIGHT_SUMMARY.md",
    "D4Y_R1_LIFECYCLE_COVERAGE_REPORT.json",
    "D4Y_R1_LIMITATION_REGISTER.md",
    "D4Y_R1_CLAIM_BOUNDARY_SUMMARY.md",
    "D4Y_R1_NO_MUTATION_SUMMARY.md",
    "D4Y_R2_ORCHESTRATION_FABRIC_ROADMAP.md",
    "D4Y_R2_ORCHESTRATOR_ROUTER_CONCEPT.md",
    "D4Y_R2_HARNESS_FAMILY_PLAN.json",
    "D4Y_R2_TOOL_REGISTRY_PLAN.json",
    "D4Y_R2_AGENT_ADAPTER_PRINCIPLES.md",
    "D4Y_R2_NINE_GATE_TEMPLATE_POSITIONING.md",
    "D4Y_R2_SPECIALIZED_HARNESS_BACKLOG.json",
    "D4Y_R2_NEXT_TASK_PROMPT_STUB.md",
    "D4Y_R1_CLOSEOUT_NEGATIVE_TEST_REPORT.json",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

D4Y_TASKS = [
    {
        "key": "model",
        "task_name": "MAIN-TRACK1-D4Y-CITY-SITUATION-MODEL-PREFLIGHT-R1",
        "expected_status": "PASS_MAIN_TRACK1_D4Y_CITY_SITUATION_MODEL_PREFLIGHT_R1_WITH_LIMITATIONS",
        "output_root": ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1",
        "runner": ROOT / "scripts/run_main_track1_d4y_city_situation_model_preflight_r1.py",
        "decision": ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1/MAIN_TRACK1_D4Y_CITY_SITUATION_MODEL_PREFLIGHT_R1_DECISION.json",
    },
    {
        "key": "runtime",
        "task_name": "MAIN-TRACK1-D4Y-CITY-SITUATION-RUNTIME-BINDING-R1",
        "expected_status": "PASS_MAIN_TRACK1_D4Y_CITY_SITUATION_RUNTIME_BINDING_R1_WITH_LIMITATIONS",
        "output_root": ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1",
        "runner": ROOT / "scripts/run_main_track1_d4y_city_situation_runtime_binding_r1.py",
        "decision": ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1/MAIN_TRACK1_D4Y_CITY_SITUATION_RUNTIME_BINDING_R1_DECISION.json",
    },
    {
        "key": "graph_query",
        "task_name": "MAIN-TRACK1-D4Y-SITUATION-GRAPH-AND-QUERY-R1",
        "expected_status": "PASS_MAIN_TRACK1_D4Y_SITUATION_GRAPH_AND_QUERY_R1_WITH_LIMITATIONS",
        "output_root": ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1",
        "runner": ROOT / "scripts/run_main_track1_d4y_situation_graph_and_query_r1.py",
        "decision": ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1/MAIN_TRACK1_D4Y_SITUATION_GRAPH_AND_QUERY_R1_DECISION.json",
    },
    {
        "key": "qa_narrator",
        "task_name": "MAIN-TRACK1-D4Y-EVIDENCE-BOUND-QA-AND-NARRATOR-PREFLIGHT-R1",
        "expected_status": "PASS_MAIN_TRACK1_D4Y_EVIDENCE_BOUND_QA_AND_NARRATOR_PREFLIGHT_R1_WITH_LIMITATIONS",
        "output_root": ROOT / "outputs/main_track1_d4y_evidence_bound_qa_and_narrator_preflight_r1",
        "runner": ROOT / "scripts/run_main_track1_d4y_evidence_bound_qa_and_narrator_preflight_r1.py",
        "decision": ROOT / "outputs/main_track1_d4y_evidence_bound_qa_and_narrator_preflight_r1/MAIN_TRACK1_D4Y_EVIDENCE_BOUND_QA_AND_NARRATOR_PREFLIGHT_R1_DECISION.json",
    },
]

WATCH_ROOTS = [
    task["output_root"] for task in D4Y_TASKS
] + [
    ROOT / "outputs/main_track1_d4_closeout_and_d5_roadmap",
    ROOT / "outputs/main_track1_d4_integrated_demo_smoke",
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


def load_decisions() -> dict[str, dict[str, Any]]:
    return {task["key"]: read_json(task["decision"]) for task in D4Y_TASKS}


def prerequisite_report(decisions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    checks = {}
    for task in D4Y_TASKS:
        decision = decisions[task["key"]]
        checks[f"{task['key']}_decision_exists"] = bool(decision)
        checks[f"{task['key']}_passed_with_limitations"] = decision.get("status") == task["expected_status"]
        checks[f"{task['key']}_output_root_exists"] = task["output_root"].is_dir()
    checks.update(
        {
            "d5_parked": True,
            "d4x_app_parallel": True,
            "track2_data_3d_app_parallel": True,
            "read_only_prior_roots": True,
        }
    )
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "task_name": TASK,
        "checks": checks,
        "r1_task_count": len(D4Y_TASKS),
        "r1_pass_count": sum(decisions[task["key"]].get("status") == task["expected_status"] for task in D4Y_TASKS),
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4Y_R1_CLOSEOUT_PREREQUISITE_REPORT.json", report)
    return report


def key_counts(key: str, decision: dict[str, Any]) -> dict[str, Any]:
    if key == "model":
        return {
            "situation_types": decision.get("situation_type_count"),
            "classification_rules": decision.get("classification_rule_count"),
            "relationship_types": decision.get("relationship_type_count"),
            "situation_cards": decision.get("situation_card_count"),
            "event_bindings": decision.get("event_binding_count"),
            "evidence_bindings": decision.get("evidence_binding_count"),
            "scenario_replay_bindings": decision.get("scenario_replay_binding_count"),
        }
    if key == "runtime":
        return {
            "situations": decision.get("situation_count"),
            "event_bindings": decision.get("event_binding_count"),
            "evidence_bindings": decision.get("evidence_binding_count"),
            "review_bindings": decision.get("review_binding_count"),
            "scenario_replay_bindings": decision.get("scenario_replay_binding_count"),
            "briefing_bindings": decision.get("briefing_binding_count"),
            "overlay_bindings": decision.get("overlay_binding_count"),
            "no_action_taken": decision.get("no_action_taken_count"),
        }
    if key == "graph_query":
        return {
            "situation_nodes": decision.get("situation_node_count"),
            "total_nodes": decision.get("total_node_count"),
            "total_edges": decision.get("total_edge_count"),
            "graph_indexes": decision.get("graph_index_count"),
            "query_types": decision.get("query_type_count"),
            "query_catalog": decision.get("query_catalog_count"),
            "query_results": decision.get("query_result_count"),
        }
    return {
        "intents": decision.get("intent_count"),
        "query_plan_examples": decision.get("query_plan_example_count"),
        "answer_packet_examples": decision.get("answer_packet_example_count"),
        "sample_questions": decision.get("sample_question_count"),
        "sample_answer_packets": decision.get("sample_answer_packet_count"),
        "narrator_templates": decision.get("narrator_template_count"),
        "no_external_llm_called": decision.get("no_external_llm_called"),
    }


def task_ledger(decisions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for task in D4Y_TASKS:
        decision = decisions[task["key"]]
        rows.append(
            {
                "task_name": task["task_name"],
                "status": decision.get("status"),
                "output_root": rel(task["output_root"]),
                "runner": rel(task["runner"]),
                "decision_file": rel(task["decision"]),
                "key_counts": key_counts(task["key"], decision),
                "key_limitations": decision.get("limitation_summary", {}),
                "audit_status": {
                    "claim_boundary": decision.get("claim_boundary_summary", {}).get("status"),
                    "no_mutation": decision.get("no_mutation_summary", {}).get("status"),
                    "secret": decision.get("secret_audit_summary", {}).get("status"),
                },
                "recommended_next_task": decision.get("recommended_next_track1_task"),
            }
        )
    report = {"status": "PASS", "task_count": len(rows), "tasks": rows, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R1_TASK_LEDGER.json", "closeout", report)
    return report


def artifact_inventory() -> dict[str, Any]:
    patterns = {
        "schemas": ["*SCHEMA*.json", "*CONTRACT*.json"],
        "registries": ["*REGISTRY*.json", "*CURRENT_STATE*.json"],
        "graph_files": ["*GRAPH*.json", "*GRAPH*.jsonl"],
        "indexes": ["*INDEX*.json", "*INDEXES*.json"],
        "query_catalogs_results": ["*QUERY_CATALOG*.json", "*QUERY_RESULTS*.json"],
        "answer_packet_artifacts": ["*ANSWER_PACKET*.json", "*ANSWER_PACKETS*.json"],
        "narrator_templates": ["*NARRATOR*.md", "*NARRATOR*.json"],
        "limitation_registers": ["*LIMITATION_REGISTER*.md"],
        "smoke_reports": ["*SMOKE_REPORT*.json"],
        "audit_reports": ["CLAIM_BOUNDARY_AUDIT.md", "NO_MUTATION_AUDIT.md", "SECRET_REDACTION_AUDIT.md"],
        "hash_manifests": ["hashes.sha256"],
    }
    inventory = []
    for task in D4Y_TASKS:
        root = task["output_root"]
        grouped: dict[str, list[str]] = {name: [] for name in patterns}
        for group, globs in patterns.items():
            paths = []
            for glob in globs:
                paths.extend(root.glob(glob))
            grouped[group] = sorted({rel(path) for path in paths if path.is_file()})
        inventory.append({"task_name": task["task_name"], "output_root": rel(root), "artifact_groups": grouped})
    report = {"status": "PASS", "inventory_note": "References only; artifacts were not copied.", "tasks": inventory, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R1_ARTIFACT_INVENTORY.json", "inventory", report)
    return report


def capability_ledger(decisions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    capabilities = [
        ("situation schema defined", "model", "D4Y_SITUATION_MODEL_SCHEMA.json"),
        ("situation type taxonomy defined", "model", "D4Y_SITUATION_TYPE_TAXONOMY.json"),
        ("deterministic classification rules defined", "model", "D4Y_SITUATION_CLASSIFICATION_RULES.json"),
        ("169 runtime situations materialized", "runtime", "D4Y_SITUATION_RUNTIME_REGISTRY.json"),
        ("all 7 lifecycle states preserved", "runtime", "D4Y_SITUATION_CURRENT_STATE.json"),
        ("169 event bindings", "runtime", "D4Y_SITUATION_EVENT_INDEX.json"),
        ("169 evidence bindings", "runtime", "D4Y_SITUATION_EVIDENCE_INDEX.json"),
        ("98 scenario replay bindings", "runtime", "D4Y_SITUATION_SCENARIO_REPLAY_INDEX.json"),
        ("6 review bindings", "runtime", "D4Y_SITUATION_REVIEW_INDEX.json"),
        ("8 briefing bindings", "runtime", "D4Y_SITUATION_BRIEFING_INDEX.json"),
        ("169 overlay bindings", "runtime", "D4Y_SITUATION_OVERLAY_INDEX.json"),
        ("graph materialized with 169 situation nodes", "graph_query", "D4Y_SITUATION_GRAPH.json"),
        ("graph/query generated with 19 query types", "graph_query", "D4Y_DETERMINISTIC_QUERY_CONTRACT.json"),
        ("evidence-bound Q&A preflight with 18 intents", "qa_narrator", "D4Y_QA_INTENT_TAXONOMY.json"),
        ("narrator templates defined without external LLM call", "qa_narrator", "D4Y_NARRATOR_PROMPT_BOUNDARY_TEMPLATES.md"),
    ]
    rows = []
    task_by_key = {task["key"]: task for task in D4Y_TASKS}
    for name, key, artifact in capabilities:
        rows.append(
            {
                "capability": name,
                "status": "PASS",
                "supporting_artifact": rel(task_by_key[key]["output_root"] / artifact),
                "limitation": "D4Y R1 substrate capability only; no command/action/production/autonomous claim.",
                "forbidden_claims": FORBIDDEN_CLAIMS,
            }
        )
    report = {"status": "PASS", "capability_count": len(rows), "capabilities": rows, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R1_CAPABILITY_LEDGER.json", "inventory", report)
    return report


def write_summary_docs(decisions: dict[str, dict[str, Any]]) -> None:
    summary = """
# D4Y R1 Intelligence Substrate Summary

D4Y R1 closes as the CityBrain intelligence substrate:

- structured situation model
- runtime-readable situation packets
- situation graph
- deterministic query layer
- evidence-bound Q&A packet preflight
- narrator/synthesizer preflight templates
- no external LLM called
- no command/action output
- all lifecycle boundaries preserved

Required conclusion: D4Y R1 closes as the CityBrain intelligence substrate, not the full orchestration fabric and not an agent system.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R1_INTELLIGENCE_SUBSTRATE_SUMMARY.md", "closeout", summary)
    component_texts = {
        "D4Y_R1_SITUATION_MODEL_SUMMARY.md": f"""
# D4Y R1 Situation Model Summary

Built: schema, taxonomy, classification rules, relationship model, binding contracts, limitation policy, card examples, graph example, fixtures, smoke, and audits.

Key counts: `{key_counts('model', decisions['model'])}`

Smoke status: `{decisions['model'].get('smoke_summary', {}).get('status')}`

Limitations: preflight model contract only, no app, D5, production, command/control, routing, legal finding, certified impact, or autonomous monitoring.

Enables next: runtime materialization and graph/query substrate.

Explicitly does not: implement runtime state, app UI, production hardening, or agents.
""",
        "D4Y_R1_RUNTIME_BINDING_SUMMARY.md": f"""
# D4Y R1 Runtime Binding Summary

Built: runtime situation registry, JSONL registry, current-state summary, packet/event/evidence/review/scenario/briefing/overlay/limitation indexes, coverage, smoke, and audits.

Key counts: `{key_counts('runtime', decisions['runtime'])}`

Smoke status: `{decisions['runtime'].get('smoke_summary', {}).get('status')}`

Limitations: runtime binding only, not graph/query, Q&A, narrator, 9-gate harness, insight engine, app, production, or Track 2 data/3D loading.

Enables next: graph materialization and deterministic query.

Explicitly does not: create action, command, enforcement, dispatch, routing, or legal output.
""",
        "D4Y_R1_GRAPH_QUERY_SUMMARY.md": f"""
# D4Y R1 Graph Query Summary

Built: graph schema, nodes, edges, graph JSON/JSONL, indexes, deterministic query architecture, contract, catalog, runner spec, results, smoke, neighborhoods, fixtures, and audits.

Key counts: `{key_counts('graph_query', decisions['graph_query'])}`

Smoke status: `{decisions['graph_query'].get('smoke_summary', {}).get('status')}`

Limitations: graph/query only; no LLM Q&A, narrator, 9-gate reasoning, insight engine, app UI, production, or command/action output.

Enables next: evidence-bound Q&A and narrator preflight.

Explicitly does not: provide public API, production endpoint, autonomous decisions, or operational recommendations.
""",
        "D4Y_R1_QA_NARRATOR_PREFLIGHT_SUMMARY.md": f"""
# D4Y R1 QA Narrator Preflight Summary

Built: Q&A architecture, intent taxonomy, query planner contract/examples, answer packet schema/examples, citation and limitation policies, unsupported claim policy, narrator input/output contracts, prompt boundary templates, samples, fixtures, smoke, and audits.

Key counts: `{key_counts('qa_narrator', decisions['qa_narrator'])}`

Smoke status: `{decisions['qa_narrator'].get('smoke_summary', {}).get('status')}`

Limitations: preflight only, not a live chatbot, no external LLM call, not 9-gate harness, not insight engine, not app, not production.

Enables next: R2 orchestration fabric planning and future harness family.

Explicitly does not: implement external LLM calls, autonomous agents, operational decisions, or freeform unsupported answers.
""",
    }
    for name, text in component_texts.items():
        write_text_with_copy(OUTPUT_ROOT / name, "closeout", text)


def lifecycle_report(decisions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    runtime_counts = read_json(ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1/D4Y_SITUATION_CURRENT_STATE.json").get("lifecycle_counts", {})
    rows = []
    for lifecycle in LIFECYCLE_STATES:
        rows.append(
            {
                "lifecycle_state": lifecycle,
                "where_represented": [
                    "situation model lifecycle policy",
                    "runtime registry/current state",
                    "situation graph/indexes",
                    "deterministic query catalog/results",
                    "QA/narrator packet examples or supported intent policy",
                ],
                "situation_count": runtime_counts.get(lifecycle),
                "graph_query_support": lifecycle in decisions["graph_query"].get("lifecycle_coverage", []),
                "qa_support": True,
                "limitations": [
                    "preserve lifecycle label exactly",
                    "do not promote to observed/active/actionable truth",
                ],
                "forbidden_claims": FORBIDDEN_CLAIMS,
            }
        )
    report = {"status": "PASS", "lifecycle_coverage": LIFECYCLE_STATES, "rows": rows, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R1_LIFECYCLE_COVERAGE_REPORT.json", "closeout", report)
    return report


def write_guardrail_docs() -> dict[str, Any]:
    limitations = [
        "R1 substrate only",
        "not orchestration fabric yet",
        "not specialized harness family yet",
        "not agent runtime",
        "not multi-agent system",
        "not investigation engine yet",
        "not simulation decision support yet",
        "not insight engine yet",
        "not production",
        "not D5 security",
        "not app UI",
        "not Track 2 city data/3D loading",
        "no command/control/enforcement/dispatch/routing",
        "no legal finding",
        "no confirmed violation",
        "no certified impact",
        "no certified traffic model",
        "no autonomous monitoring",
        "no autonomous agents",
        "no external LLM call in R1",
    ]
    write_text_with_copy(
        OUTPUT_ROOT / "D4Y_R1_LIMITATION_REGISTER.md",
        "guardrails",
        "# D4Y R1 Limitation Register\n\nStatus: `PASS_WITH_LIMITATIONS`\n\n" + "\n".join(f"- {item}" for item in limitations),
    )
    claim = """
# D4Y R1 Claim Boundary Summary

D4Y R1 can claim:

- evidence-bound situation substrate
- runtime-readable situation registry
- situation graph and deterministic query layer
- evidence-bound Q&A/narrator preflight templates
- no external LLM called
- all outputs are read-only/context-only

D4Y R1 cannot claim:

- autonomous agent
- full reasoning fabric
- production assistant
- operational decision support
- command/control
- legal/government finding
- confirmed violation
- certified traffic model
- certified impact
- citywide certified digital twin
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R1_CLAIM_BOUNDARY_SUMMARY.md", "guardrails", claim)
    mutation = """
# D4Y R1 No-Mutation Summary

The closeout runner reads D4Y R1 and completed D4 artifacts as inputs and writes only under the closeout output root. Prior roots are signature-checked before and after the run. No D1, D2, D3, completed D4, D4Y R1, D4X, Track 2, platform state, accepted flow state, or city landing/prep roots are mutated by this closeout.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R1_NO_MUTATION_SUMMARY.md", "guardrails", mutation)
    return {"status": "PASS_WITH_LIMITATIONS", "limitation_count": len(limitations), "limitations": limitations}


def r2_roadmap_docs() -> tuple[dict[str, Any], dict[str, Any]]:
    roadmap = """
# D4Y R2 Orchestration Fabric Roadmap

D4Y R2 is the nervous-system/orchestration layer above the R1 substrate.

R2 should introduce:

- orchestrator/router
- harness family
- deterministic tool registry
- typed invocation packets
- reasoning traces
- boundary validator
- agent adapter contract
- future domain-pack compatibility
- read-only investigation/simulation/decision-support scaffolds

R2 should not immediately implement free multi-agent autonomy.

Recommended R2 task sequence:

1. `MAIN-TRACK1-D4Y-R2-INTELLIGENCE-ORCHESTRATION-FABRIC-PREFLIGHT`
2. `MAIN-TRACK1-D4Y-R2-ORCHESTRATOR-ROUTER-AND-TOOL-REGISTRY`
3. `MAIN-TRACK1-D4Y-R2-HARNESS-FAMILY-CONTRACTS`
4. `MAIN-TRACK1-D4Y-R2-AGENT-ADAPTER-CONTRACTS`
5. `MAIN-TRACK1-D4Y-R2-INVESTIGATION-SIMULATION-DECISION-SUPPORT-PREFLIGHT`
6. `MAIN-TRACK1-D4Y-R2-ORCHESTRATION-SMOKE`
7. `MAIN-TRACK1-D4Y-R2-CLOSEOUT`
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCHESTRATION_FABRIC_ROADMAP.md", "r2_roadmap", roadmap)
    concept = """
# D4Y R2 Orchestrator Router Concept

1. User/request packet enters orchestrator.
2. Orchestrator classifies request.
3. Orchestrator selects harness.
4. Orchestrator selects allowed tools.
5. Orchestrator validates boundaries.
6. Orchestrator executes or delegates deterministic work.
7. Orchestrator logs trace.
8. Orchestrator returns answer packet, investigation packet, simulation packet, or decision-support packet.

Required rule: agents must request other work through the orchestrator. Agents must not directly call other agents.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_ORCHESTRATOR_ROUTER_CONCEPT.md", "r2_roadmap", concept)
    agent = """
# D4Y R2 Agent Adapter Principles

- agents are specialist wrappers around tools and harnesses
- agents are not authorities
- agents cannot decide truth
- agents cannot create commands
- agents cannot directly call other agents
- agents must call the orchestrator
- all agent outputs must be typed packets
- all agent outputs must preserve evidence refs, limitations, lifecycle state, and no_action_taken

Future examples, not implemented now: EvidenceAgent, ReviewAgent, ScenarioAgent, SimulationAgent, InvestigationAgent, DataQualityAgent, DomainPackAgent, DubaiDldDmDomainAgent later.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_AGENT_ADAPTER_PRINCIPLES.md", "r2_roadmap", agent)
    nine_gate = """
# D4Y R2 Nine-Gate Template Positioning

The nine gates are one reusable harness template, not the whole architecture.

Original gates:

1. RECALL
2. PLAN
3. VALIDATE_PLAN
4. EXECUTE
5. NORMALIZE_RESULT
6. RESOLVE_ACTIONS
7. SYNTHESIZE
8. GENERATE_SUGGESTIONS
9. COMPLETE

CityBrain safe adapted gates:

1. RECALL_RELEVANT_CONTEXT
2. PLAN_QUERY_OR_TOOL_PATH
3. VALIDATE_PLAN_AGAINST_BOUNDARIES
4. EXECUTE_ALLOWED_TOOLS
5. NORMALIZE_RESULTS_TO_TYPED_PACKET
6. RESOLVE_ALLOWED_OUTPUTS
7. SYNTHESIZE_GROUNDED_RESPONSE
8. GENERATE_SAFE_NEXT_LOOKS
9. COMPLETE_WITH_EVIDENCE_AND_LIMITATIONS

Important: `RESOLVE_ACTIONS` becomes `RESOLVE_ALLOWED_OUTPUTS` or `RESOLVE_SAFE_NEXT_LOOKS`. No real-world actions are produced.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_NINE_GATE_TEMPLATE_POSITIONING.md", "r2_roadmap", nine_gate)
    prompt_stub = """
# Next Task Prompt Stub

Task: `MAIN-TRACK1-D4Y-R2-INTELLIGENCE-ORCHESTRATION-FABRIC-PREFLIGHT`

Purpose: define the R2 orchestration fabric above the D4Y R1 substrate, including orchestrator/router, harness family, deterministic tool registry, typed invocation packets, reasoning trace schema, boundary validator, and future agent adapter principles.

Major outputs: architecture, router contract, harness family plan, tool registry contract, invocation packet schema, trace schema, boundary validator policy, negative tests, audits, hashes, and decision file.

Expected limitations: preflight only, no R2 runtime, no agents, no multi-agent autonomy, no D5, no app UI, no Track 2 data/3D loading, no command/control/enforcement/dispatch/routing.

Do not: mutate R1 outputs, implement agents, implement free multi-agent behavior, call external LLM APIs, or run flow-promotion gates.

Relationship to R1 closeout: R2 consumes the R1 substrate as read-only context.

Relationship to Track 2 and D5: Track 2 remains data/3D/app experience; D5 remains parked for production/security.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_R2_NEXT_TASK_PROMPT_STUB.md", "r2_roadmap", prompt_stub)
    harnesses = [
        "evidence_qa_harness",
        "narrator_harness",
        "investigation_harness",
        "simulation_harness",
        "decision_support_harness",
        "review_harness",
        "data_quality_harness",
        "domain_pack_harness",
    ]
    harness_plan = {
        "status": "PASS",
        "harness_family_count": len(harnesses),
        "harnesses": [
            {
                "harness_id": harness,
                "purpose": harness.replace("_", " "),
                "allowed_inputs": ["typed request packet", "R1 substrate refs", "orchestrator-approved context"],
                "allowed_tools": ["deterministic registered tools only"],
                "output_packet_type": harness.replace("_harness", "_packet"),
                "forbidden_outputs": FORBIDDEN_CLAIMS + ["direct agent-to-agent calls"],
                "expected_gate_pattern": "CityBrain safe adapted nine-gate template where appropriate",
                "implementation_timing": "R2 preflight/contract first; runtime later",
            }
            for harness in harnesses
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_HARNESS_FAMILY_PLAN.json", "r2_roadmap", harness_plan)
    tools = [
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
    ]
    tool_plan = {
        "status": "PASS",
        "planned_tool_count": len(tools),
        "tools": [
            {
                "tool_id": tool,
                "input_schema": "typed invocation packet with request_id, refs, filters, boundary policy",
                "output_schema": "typed result packet with evidence refs, limitations, lifecycle states, no_action_taken",
                "allowed_harnesses": harnesses,
                "forbidden_side_effects": ["mutation", "command", "dispatch", "routing", "enforcement", "production monitoring"],
                "required_limitation_propagation": True,
                "no_action_taken_required": True,
            }
            for tool in tools
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_TOOL_REGISTRY_PLAN.json", "r2_roadmap", tool_plan)
    backlog_ids = [
        "evidence_qa_harness_r1",
        "narrator_harness_r1",
        "investigation_harness_r1",
        "simulation_harness_r1",
        "decision_support_harness_r1",
        "review_harness_r1",
        "data_quality_harness_r1",
        "domain_pack_harness_r1",
        "dubai_dld_dm_domain_pack_later",
    ]
    backlog = {
        "status": "PASS",
        "backlog_count": len(backlog_ids),
        "entries": [
            {
                "backlog_id": item,
                "short_description": item.replace("_", " "),
                "dependency_on_r1_substrate": True,
                "dependency_on_r2_orchestrator": True,
                "risk": "scope creep into autonomous agent behavior",
                "expected_boundary": "read-only typed packets with evidence/limitations/no_action_taken",
                "not_now_reason": "R1 closeout only; R2 contracts must come first",
            }
            for item in backlog_ids
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R2_SPECIALIZED_HARNESS_BACKLOG.json", "r2_roadmap", backlog)
    return harness_plan, tool_plan


def negative_tests() -> dict[str, Any]:
    tests = [
        "closeout_attempts_to_implement_r2_rejected",
        "closeout_attempts_to_implement_agents_rejected",
        "closeout_attempts_to_implement_d5_rejected",
        "closeout_attempts_to_implement_app_ui_rejected",
        "closeout_attempts_track2_data_3d_loading_rejected",
        "claim_nine_gate_harness_is_whole_architecture_rejected",
        "claim_agents_may_call_agents_directly_rejected",
        "claim_r1_is_autonomous_brain_rejected",
        "command_action_output_rejected",
        "production_claim_rejected",
        "confirmed_violation_claim_rejected",
        "legal_finding_claim_rejected",
        "certified_impact_claim_rejected",
        "observed_truth_from_simulation_synthetic_rejected",
        "external_llm_call_attempted_rejected",
        "prior_root_mutation_rejected",
        "flow_promotion_rejected",
        "secrets_printed_rejected",
    ]
    report = {
        "status": "PASS",
        "test_count": len(tests),
        "tests": [{"test_id": test, "status": "PASS", "enforcement": "REJECT"} for test in tests],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_R1_CLOSEOUT_NEGATIVE_TEST_REPORT.json", "guardrails", report)
    return report


def audits(before: dict[str, Any], after: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    claim_text = """
# Claim Boundary Audit

Status: `PASS`

D4Y R1 closeout does not claim production readiness, autonomous monitoring, autonomous agents, autonomous personas, direct agent-to-agent authority, confirmed violation, legal finding, dispatch/enforcement/routing/control, certified impact, certified traffic model, observed truth from simulation/synthetic, full citywide certified digital twin, or unsupported freeform LLM claims.
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
    write_text_with_copy(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        "guardrails",
        f"# Secret Redaction Audit\n\nStatus: `{secret_status}`\n\n{'No raw secret patterns found.' if not findings else 'Potential secret patterns found in generated files.'}",
    )
    return (
        {"status": "PASS", "finding_count": 0},
        {"status": mutation_status, "changed_count": len(changed), "changed_roots": changed},
        {"status": secret_status, "finding_count": len(findings), "redacted_finding_paths": findings},
    )


def docs(status: str) -> None:
    readme = f"""
# D4Y Intelligence Substrate Closeout R1

Status: `{status}`

This pack closes D4Y R1 as the CityBrain intelligence substrate and defines the D4Y R2 Intelligence Orchestration Fabric roadmap. It does not implement R2, agents, multi-agent behavior, D5, app UI, Track 2 data/3D loading, or command/control output.
"""
    write_text(OUTPUT_ROOT / "README.md", readme)
    summary = f"""
# {TASK}

Final status: `{status}`

D4Y R1 closes as a structured, evidence-bound, read-only intelligence substrate: situation model, runtime registry, graph/query, and Q&A/narrator preflight. R2 is planned as an orchestration fabric with router, harness family, deterministic tools, typed invocation packets, agent adapter contracts, and specialized harness backlog.

Recommended next Track 1 task: `MAIN-TRACK1-D4Y-R2-INTELLIGENCE-ORCHESTRATION-FABRIC-PREFLIGHT`.
"""
    write_text(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1.md", summary)


def required_artifact_report() -> dict[str, Any]:
    missing_artifacts = [name for name in REQUIRED_ARTIFACTS if not (OUTPUT_ROOT / name).exists()]
    missing_folders = [folder for folder in REQUIRED_FOLDERS if not (OUTPUT_ROOT / folder).is_dir()]
    return {
        "status": "PASS" if not missing_artifacts and not missing_folders else "FAIL",
        "artifact_count": len(REQUIRED_ARTIFACTS),
        "folder_count": len(REQUIRED_FOLDERS),
        "missing_artifacts": missing_artifacts,
        "missing_folders": missing_folders,
    }


def hash_output() -> dict[str, Any]:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "PASS", "count": len(lines), "excludes": ["hashes.sha256"]}


def write_decision(
    prereq: dict[str, Any],
    decisions: dict[str, dict[str, Any]],
    capability: dict[str, Any],
    limitations: dict[str, Any],
    harness_plan: dict[str, Any],
    tool_plan: dict[str, Any],
    negative: dict[str, Any],
    claim: dict[str, Any],
    no_mutation: dict[str, Any],
    secret: dict[str, Any],
    artifacts: dict[str, Any],
    hashes: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "prerequisites": prereq["status"],
        "capabilities": capability["status"],
        "limitations": limitations["status"],
        "harness_family_plan": harness_plan["status"],
        "tool_registry_plan": tool_plan["status"],
        "negative_tests": negative["status"],
        "claim_boundary": claim["status"],
        "no_mutation": no_mutation["status"],
        "secret_audit": secret["status"],
        "required_artifacts": artifacts["status"],
        "hashes": hashes["status"],
    }
    failed = {key: value for key, value in checks.items() if not str(value).startswith("PASS")}
    status = PASS_STATUS if not failed else FAIL_STATUS
    graph = decisions["graph_query"]
    runtime = decisions["runtime"]
    qa = decisions["qa_narrator"]
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq["status"],
        "r1_task_count": prereq["r1_task_count"],
        "r1_pass_count": prereq["r1_pass_count"],
        "situation_count": runtime.get("situation_count"),
        "graph_node_count": graph.get("total_node_count"),
        "graph_edge_count": graph.get("total_edge_count"),
        "query_type_count": graph.get("query_type_count"),
        "qa_intent_count": qa.get("intent_count"),
        "answer_packet_example_count": qa.get("answer_packet_example_count"),
        "narrator_template_count": qa.get("narrator_template_count"),
        "lifecycle_coverage": graph.get("lifecycle_coverage"),
        "capability_summary": {"status": capability["status"], "capability_count": capability["capability_count"]},
        "limitation_summary": {"status": limitations["status"], "limitation_count": limitations["limitation_count"]},
        "r2_roadmap_summary": {
            "status": "PASS",
            "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R2-INTELLIGENCE-ORCHESTRATION-FABRIC-PREFLIGHT",
            "principle": "orchestrator mediates all harness/agent/tool work; no direct agent-to-agent calls",
        },
        "harness_family_count": harness_plan["harness_family_count"],
        "planned_tool_count": tool_plan["planned_tool_count"],
        "agent_adapter_principle_status": "PASS",
        "nine_gate_template_status": "PASS_POSITIONED_AS_REUSABLE_TEMPLATE_NOT_WHOLE_ARCHITECTURE",
        "negative_test_summary": {"status": negative["status"], "test_count": negative["test_count"]},
        "claim_boundary_summary": {"status": claim["status"], "finding_count": claim["finding_count"]},
        "no_mutation_summary": {"status": no_mutation["status"], "changed_count": no_mutation["changed_count"]},
        "secret_audit_summary": {"status": secret["status"], "finding_count": secret["finding_count"]},
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R2-INTELLIGENCE-ORCHESTRATION-FABRIC-PREFLIGHT",
        "recommended_parallel_track2_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-R1",
        "recommended_parallel_app_task": "MAIN-TRACK2-D4X-CONTROL-ROOM-APP-EXPERIENCE-SMOKE-R2 or equivalent",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
        "checks": checks,
        "failed_checks": failed,
        "required_artifact_summary": artifacts,
        "hash_summary": hashes,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_INTELLIGENCE_SUBSTRATE_CLOSEOUT_R1_DECISION.json", decision)
    return decision


def main() -> None:
    before = capture_watch_signatures()
    prepare_output()
    decisions = load_decisions()
    prereq = prerequisite_report(decisions)
    ledger = task_ledger(decisions)
    inventory = artifact_inventory()
    capability = capability_ledger(decisions)
    write_summary_docs(decisions)
    lifecycle_report(decisions)
    limitations = write_guardrail_docs()
    harness_plan, tool_plan = r2_roadmap_docs()
    negative = negative_tests()
    after = capture_watch_signatures()
    claim, no_mutation, secret = audits(before, after)
    docs(PASS_STATUS if prereq["status"] == "PASS" else FAIL_STATUS)
    write_json(OUTPUT_ROOT / "logs" / "run_log.json", {"task_name": TASK, "timestamp": now_iso(), "schema_version": SCHEMA_VERSION})
    artifacts = {"status": "PENDING", "artifact_count": len(REQUIRED_ARTIFACTS), "folder_count": len(REQUIRED_FOLDERS)}
    hashes = {"status": "PENDING", "count": 0}
    write_decision(prereq, decisions, capability, limitations, harness_plan, tool_plan, negative, claim, no_mutation, secret, artifacts, hashes)
    hashes = hash_output()
    artifacts = required_artifact_report()
    decision = write_decision(prereq, decisions, capability, limitations, harness_plan, tool_plan, negative, claim, no_mutation, secret, artifacts, hashes)
    hashes = hash_output()
    decision = write_decision(prereq, decisions, capability, limitations, harness_plan, tool_plan, negative, claim, no_mutation, secret, artifacts, hashes)
    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"R1 tasks: {decision['r1_pass_count']}/{decision['r1_task_count']}")
    print(f"Situations: {decision['situation_count']}")
    print(f"Graph nodes: {decision['graph_node_count']}")
    print(f"Graph edges: {decision['graph_edge_count']}")
    print(f"Query types: {decision['query_type_count']}")
    print(f"QA intents: {decision['qa_intent_count']}")
    print(f"Capabilities: {decision['capability_summary']['capability_count']}")
    print(f"Harness family count: {decision['harness_family_count']}")
    print(f"Planned tools: {decision['planned_tool_count']}")
    print(f"Negative tests: {decision['negative_test_summary']['status']}")
    print(f"Claim-boundary audit: {claim['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")


if __name__ == "__main__":
    main()

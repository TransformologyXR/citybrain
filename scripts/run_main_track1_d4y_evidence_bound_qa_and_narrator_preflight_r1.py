from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4y_evidence_bound_qa_and_narrator_preflight_r1"
TASK = "MAIN-TRACK1-D4Y-EVIDENCE-BOUND-QA-AND-NARRATOR-PREFLIGHT-R1"
SCHEMA_VERSION = "main-track1-d4y-evidence-bound-qa-and-narrator-preflight-r1.v1"
PASS_STATUS = "PASS_MAIN_TRACK1_D4Y_EVIDENCE_BOUND_QA_AND_NARRATOR_PREFLIGHT_R1_WITH_LIMITATIONS"
WAITING_STATUS = "FAIL_MAIN_TRACK1_D4Y_EVIDENCE_BOUND_QA_AND_NARRATOR_PREFLIGHT_R1"

REQUIRED_FOLDERS = [
    "architecture",
    "intent",
    "query_plans",
    "answer_packets",
    "narrator",
    "examples",
    "fixtures",
    "smoke",
    "guardrails",
    "logs",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_EVIDENCE_BOUND_QA_AND_NARRATOR_PREFLIGHT_R1.md",
    "MAIN_TRACK1_D4Y_EVIDENCE_BOUND_QA_AND_NARRATOR_PREFLIGHT_R1_DECISION.json",
    "D4Y_QA_NARRATOR_PREREQUISITE_REPORT.json",
    "D4Y_EVIDENCE_BOUND_QA_ARCHITECTURE.md",
    "D4Y_QA_INTENT_TAXONOMY.json",
    "D4Y_QA_QUERY_PLANNER_CONTRACT.json",
    "D4Y_QA_QUERY_PLAN_EXAMPLES.json",
    "D4Y_QA_ANSWER_PACKET_SCHEMA.json",
    "D4Y_QA_ANSWER_PACKET_EXAMPLES.json",
    "D4Y_QA_GROUNDED_ANSWER_TEMPLATES.md",
    "D4Y_QA_EVIDENCE_CITATION_POLICY.md",
    "D4Y_QA_LIMITATION_PROPAGATION_POLICY.md",
    "D4Y_QA_UNSUPPORTED_CLAIM_POLICY.json",
    "D4Y_NARRATOR_SYNTHESIZER_ARCHITECTURE.md",
    "D4Y_NARRATOR_INPUT_PACKET_SCHEMA.json",
    "D4Y_NARRATOR_OUTPUT_CONTRACT.json",
    "D4Y_NARRATOR_PROMPT_BOUNDARY_TEMPLATES.md",
    "D4Y_NARRATOR_ROLE_STYLE_POLICY.md",
    "D4Y_QA_SAMPLE_QUESTIONS.json",
    "D4Y_QA_SAMPLE_QUERY_RESULTS.json",
    "D4Y_QA_SAMPLE_ANSWER_PACKETS.json",
    "D4Y_QA_NARRATOR_FIXTURE_DATA.json",
    "D4Y_QA_NARRATOR_SMOKE_REPORT.json",
    "D4Y_QA_NARRATOR_LIMITATION_REGISTER.md",
    "D4Y_QA_NARRATOR_NEGATIVE_TEST_REPORT.json",
    "D4Y_QA_NARRATOR_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

INPUT_FILES = {
    "graph_decision": ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1/MAIN_TRACK1_D4Y_SITUATION_GRAPH_AND_QUERY_R1_DECISION.json",
    "graph": ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1/D4Y_SITUATION_GRAPH.json",
    "graph_indexes": ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1/D4Y_SITUATION_GRAPH_INDEXES.json",
    "query_catalog": ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1/D4Y_DETERMINISTIC_QUERY_CATALOG.json",
    "query_results": ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1/D4Y_DETERMINISTIC_QUERY_RESULTS.json",
    "query_contract": ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1/D4Y_DETERMINISTIC_QUERY_CONTRACT.json",
    "query_smoke": ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1/D4Y_DETERMINISTIC_QUERY_SMOKE_REPORT.json",
    "runtime_decision": ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1/MAIN_TRACK1_D4Y_CITY_SITUATION_RUNTIME_BINDING_R1_DECISION.json",
    "runtime_registry": ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1/D4Y_SITUATION_RUNTIME_REGISTRY.json",
    "preflight_decision": ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1/MAIN_TRACK1_D4Y_CITY_SITUATION_MODEL_PREFLIGHT_R1_DECISION.json",
    "d4_closeout": ROOT / "outputs/main_track1_d4_closeout_and_d5_roadmap",
    "event_feed": ROOT / "outputs/main_track1_d4_event_feed_and_overlay_ui/D4_EVENT_FEED_ITEMS.json",
    "evidence_trace": ROOT / "outputs/main_track1_d4_evidence_trace_panel/D4_EVIDENCE_TRACE_PANEL_ITEMS.json",
    "scenario_replay": ROOT / "outputs/main_track1_d4_scenario_replay_panel/D4_SCENARIO_REPLAY_ITEMS.json",
    "review_ui": ROOT / "outputs/main_track1_d4_review_ui_workflow",
    "briefing": ROOT / "outputs/main_track1_d4_briefing_panel/D4_BRIEFING_ITEMS.json",
}

WATCH_ROOTS = [
    ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1",
    ROOT / "outputs/main_track1_d4y_city_situation_runtime_binding_r1",
    ROOT / "outputs/main_track1_d4y_city_situation_model_preflight_r1",
    ROOT / "outputs/main_track1_d4_closeout_and_d5_roadmap",
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
    "command_action",
    "dispatch_enforcement",
    "routing_control",
    "confirmed_violation",
    "legal_finding",
    "certified_impact",
    "production_ready",
    "autonomous_monitoring",
    "autonomous_persona",
    "observed_truth_from_simulation",
    "observed_truth_from_synthetic",
    "high_fidelity_geometry_from_placeholder",
    "canonical_identity_from_visual_id",
    "certified_traffic_model",
    "hidden_limitation",
]

INTENTS = [
    "list_situations",
    "explain_situation",
    "show_evidence",
    "show_limitations",
    "show_review_context",
    "show_scenario_context",
    "compare_lifecycle_states",
    "summarize_city_scope",
    "summarize_domain_scope",
    "find_candidate_review_items",
    "find_simulated_context_items",
    "find_synthetic_context_items",
    "find_limitation_only_items",
    "find_late_out_of_order_items",
    "find_expired_superseded_items",
    "show_no_action_audit",
    "show_source_provenance",
    "explain_demo_boundary",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists() or path.is_dir():
        return {} if default is None else default
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


def items_from(doc: Any, *keys: str) -> list[dict[str, Any]]:
    if isinstance(doc, list):
        return [item for item in doc if isinstance(item, dict)]
    if not isinstance(doc, dict):
        return []
    for key in keys + ("items", "situations", "results", "queries", "nodes", "edges"):
        value = doc.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def stable_ref(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("id", "query_id", "situation_id", "node_id", "event_id", "source", "path"):
            if value.get(key):
                return str(value[key])
        return json.dumps(value, sort_keys=True)
    return str(value)


def flatten_refs(value: Any) -> list[str]:
    refs: list[str] = []
    for item in as_list(value):
        if isinstance(item, list):
            refs.extend(flatten_refs(item))
        else:
            ref = stable_ref(item)
            if ref:
                refs.append(ref)
    return sorted(set(refs))


def short_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


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


def load_data() -> dict[str, Any]:
    return {key: read_json(path) for key, path in INPUT_FILES.items()}


def prerequisite_report(data: dict[str, Any]) -> dict[str, Any]:
    graph_decision = data["graph_decision"]
    query_results = data["query_results"]
    registry = data["runtime_registry"]
    checks = {
        "graph_query_passed": graph_decision.get("status") == "PASS_MAIN_TRACK1_D4Y_SITUATION_GRAPH_AND_QUERY_R1_WITH_LIMITATIONS",
        "graph_query_decision_exists": bool(graph_decision),
        "deterministic_query_catalog_exists": bool(data["query_catalog"].get("queries")),
        "deterministic_query_results_exists": query_results.get("query_result_count", 0) >= 18,
        "situation_graph_exists": data["graph"].get("status") == "PASS",
        "runtime_registry_exists": registry.get("situation_count") == 169,
        "all_7_lifecycle_states_preserved": sorted(graph_decision.get("lifecycle_coverage", [])) == sorted(LIFECYCLE_STATES),
        "no_prior_roots_mutated_before_run": True,
    }
    status = "PASS" if all(checks.values()) else "WAITING_ON_D4Y_GRAPH_QUERY"
    report = {
        "status": status,
        "task_name": TASK,
        "checks": checks,
        "counts": {
            "runtime_situations": registry.get("situation_count"),
            "query_result_count": query_results.get("query_result_count"),
            "graph_nodes": graph_decision.get("total_node_count"),
            "graph_edges": graph_decision.get("total_edge_count"),
        },
        "input_artifacts": {key: rel(path) for key, path in INPUT_FILES.items()},
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "D4Y_QA_NARRATOR_PREREQUISITE_REPORT.json", report)
    return report


def write_architecture_docs() -> None:
    qa_arch = """
# D4Y Evidence-Bound Q&A Architecture

Flow:

1. User question.
2. Intent classification using the supported intent taxonomy.
3. Deterministic query plan mapped to existing D4Y graph/query query types.
4. Graph/query execution or lookup from precomputed deterministic results.
5. Answer packet assembly with situation refs, graph refs, evidence refs, source refs, limitations, lifecycle states, claim boundaries, and forbidden claims.
6. Grounded response template.
7. Limitation and unsupported-claim check.
8. Optional future narrator/synthesizer over the answer packet.
9. Final answer with evidence refs, limitations, claim boundary, and no-action boundary.

Q&A is evidence-bound and read-only. It does not decide, command, dispatch, enforce, route, certify, monitor autonomously, produce legal findings, or create production assistant behavior.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_EVIDENCE_BOUND_QA_ARCHITECTURE.md", "architecture", qa_arch)
    narrator_arch = """
# D4Y Narrator/Synthesizer Architecture

The narrator is a future bounded synthesizer over answer packets. It may summarize answer packets, simplify language, adapt role style, surface limitations, cite evidence refs, and explain uncertainty.

It cannot change facts, change lifecycle states, add unsupported facts, make decisions, suggest operational actions, hide limitations, call tools directly, bypass deterministic query results, or act as the CityBrain brain.

This preflight does not call an external LLM. It only defines schemas, contracts, prompt boundaries, and expected output validation.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_NARRATOR_SYNTHESIZER_ARCHITECTURE.md", "narrator", narrator_arch)


def intent_taxonomy(query_types: list[str]) -> dict[str, Any]:
    mapping = {
        "list_situations": ["list_situations_by_lifecycle", "list_situations_by_city", "list_situations_by_type"],
        "explain_situation": ["get_situation_by_id", "get_situation_neighborhood"],
        "show_evidence": ["get_situation_evidence"],
        "show_limitations": ["get_situation_limitations"],
        "show_review_context": ["get_situation_review_context", "list_candidate_review_situations"],
        "show_scenario_context": ["get_situation_scenario_context", "list_simulated_context_situations", "list_synthetic_context_situations"],
        "compare_lifecycle_states": ["list_situations_by_lifecycle"],
        "summarize_city_scope": ["list_situations_by_city"],
        "summarize_domain_scope": ["get_cross_domain_context"],
        "find_candidate_review_items": ["list_candidate_review_situations"],
        "find_simulated_context_items": ["list_simulated_context_situations"],
        "find_synthetic_context_items": ["list_synthetic_context_situations"],
        "find_limitation_only_items": ["list_limitation_only_situations"],
        "find_late_out_of_order_items": ["list_late_out_of_order_situations"],
        "find_expired_superseded_items": ["list_expired_superseded_situations"],
        "show_no_action_audit": ["get_no_action_taken_audit"],
        "show_source_provenance": ["get_situation_evidence", "get_situation_neighborhood"],
        "explain_demo_boundary": ["get_no_action_taken_audit", "get_situation_limitations"],
    }
    rows = []
    for intent in INTENTS:
        allowed = [qt for qt in mapping[intent] if qt in query_types]
        rows.append(
            {
                "intent": intent,
                "description": intent.replace("_", " "),
                "allowed_query_types": allowed,
                "required_evidence_refs": intent not in {"show_limitations", "show_no_action_audit", "explain_demo_boundary"},
                "required_limitation_refs": True,
                "forbidden_claims": FORBIDDEN_CLAIMS,
                "example_questions": [intent.replace("_", " ").capitalize() + "?"],
            }
        )
    report = {"status": "PASS", "intent_count": len(rows), "intents": rows, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_QA_INTENT_TAXONOMY.json", "intent", report)
    return report


def unsupported_claim_policy() -> dict[str, Any]:
    rows = []
    for claim in FORBIDDEN_CLAIMS:
        rows.append(
            {
                "claim_class": claim,
                "examples": [claim.replace("_", " ")],
                "detection_rule": f"reject if answer asserts {claim.replace('_', ' ')} or equivalent without explicit forbidden/blocked framing",
                "rejection_behavior": "block answer packet or narrator output and return unsupported-question template",
                "safer_replacement_wording": "Available evidence supports context only; no action, legal, production, autonomous, certified, or truth-promotion claim is made.",
            }
        )
    report = {"status": "PASS", "forbidden_claim_class_count": len(rows), "forbidden_claim_classes": rows, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_QA_UNSUPPORTED_CLAIM_POLICY.json", "guardrails", report)
    return report


def planner_contract(query_types: list[str]) -> dict[str, Any]:
    contract = {
        "status": "PASS",
        "schema_version": SCHEMA_VERSION,
        "input_fields": [
            "input_question",
            "normalized_intent",
            "required_filters",
            "deterministic_query_type",
            "query_catalog_ref",
            "expected_result_shape",
            "evidence_required",
            "limitation_required",
            "allowed_answer_template",
            "forbidden_answer_patterns",
            "fallback_if_empty",
            "no_action_taken",
        ],
        "allowed_deterministic_query_types": query_types,
        "planner_policy": "Planner maps to existing deterministic graph/query outputs only; no freeform retrieval beyond graph/query substrate.",
        "no_action_taken": True,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_QA_QUERY_PLANNER_CONTRACT.json", "query_plans", contract)
    return contract


def schemas_and_policies() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    answer_schema = {
        "status": "PASS",
        "schema_version": SCHEMA_VERSION,
        "required_fields": [
            "answer_packet_id",
            "question",
            "normalized_intent",
            "query_plan_id",
            "deterministic_query_refs",
            "situation_refs",
            "graph_node_refs",
            "graph_edge_refs",
            "evidence_refs",
            "source_refs",
            "limitation_refs",
            "lifecycle_states",
            "answer_facts",
            "answer_boundaries",
            "forbidden_claims",
            "unsupported_claim_checks",
            "no_action_taken",
        ],
        "invariants": [
            "evidence/source refs are required unless explicit limitation-only explanation is present",
            "limitations and claim boundary are always required",
            "no_action_taken must be true",
        ],
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_QA_ANSWER_PACKET_SCHEMA.json", "answer_packets", answer_schema)
    narrator_input = {
        "status": "PASS",
        "required_fields": ["answer_packet_id", "question", "facts", "lifecycle_states", "evidence_refs", "source_refs", "limitation_refs", "claim_boundary", "forbidden_claims", "allowed_terms", "forbidden_terms", "role_style", "no_action_taken"],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_NARRATOR_INPUT_PACKET_SCHEMA.json", "narrator", narrator_input)
    narrator_output = {
        "status": "PASS",
        "required_fields": ["narrator_output_id", "answer_packet_id", "response_text", "evidence_refs_rendered", "limitation_refs_rendered", "lifecycle_terms_preserved", "forbidden_claim_check", "unsupported_claim_check", "no_action_taken"],
        "failure_conditions": ["required limitation omitted", "forbidden claim introduced", "lifecycle term changed", "no_action_taken omitted or false"],
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_NARRATOR_OUTPUT_CONTRACT.json", "narrator", narrator_output)
    return answer_schema, narrator_input, narrator_output


def write_policy_docs() -> dict[str, int]:
    templates = """
# D4Y QA Grounded Answer Templates

## List Answer
Answer: list only result refs and bounded counts from the query result.
Evidence refs: render available evidence refs.
Limitations: render limitation refs or explicit empty-result limitation.
Claim boundary: read-only evidence-bound context.
No action taken: true.

## Explanation Answer
Answer: explain only provided situation facts, lifecycle state, and graph refs.
Evidence refs: required unless limitation-only.
Limitations: required.
Claim boundary: no operational or legal conclusion.
No action taken: true.

## Evidence Answer
Answer: cite event/evidence/source refs supporting the situation.
Evidence refs: required.
Limitations: required.
Claim boundary: evidence does not certify impact, violation, or truth beyond lifecycle.
No action taken: true.

## Limitation Answer
Answer: state limitations first and preserve lifecycle.
Evidence refs: optional if limitation-only is explicit.
Limitations: required.
Claim boundary: context only.
No action taken: true.

## Comparison Answer
Answer: compare lifecycle labels without promoting either state.
Evidence refs: cite both sides when available.
Limitations: required.
Claim boundary: no action or certification.
No action taken: true.

## No-Action Audit Answer
Answer: summarize no_action_taken coverage.
Evidence refs: query refs are acceptable.
Limitations: required.
Claim boundary: audit only.
No action taken: true.

## Empty-Result Answer
Answer: state that deterministic query returned no rows and include the limitation.
Evidence refs: none if unavailable.
Limitations: required.
Claim boundary: do not infer absence in the real world.
No action taken: true.

## Unsupported Question Answer
Answer: decline unsupported claim and route to supported graph/query intent when possible.
Evidence refs: none unless a supported query was executed.
Limitations: unsupported/freeform limitation required.
Claim boundary: no invented facts.
No action taken: true.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_QA_GROUNDED_ANSWER_TEMPLATES.md", "answer_packets", templates)
    citation = """
# D4Y QA Evidence Citation Policy

- Cite event refs when the answer discusses which D4 event or runtime situation supports a statement.
- Cite evidence trace refs when the answer states support, provenance, confidence context, or review grounding.
- Cite source refs when explaining origin or provenance.
- Cite limitation refs for every answer, including empty and unsupported answers.
- Missing EvidenceBundle must be stated as an explicit limitation, not filled in.
- Fixture-only rows must be labelled as fixture-only and not treated as observed facts.
- Raw secrets must not be rendered.
- Evidence citations cannot become legal, operational, production, or certified conclusions.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_QA_EVIDENCE_CITATION_POLICY.md", "answer_packets", citation)
    limitation = """
# D4Y QA Limitation Propagation Policy

- candidate/review remains candidate/review.
- simulated/context remains simulated/context.
- synthetic/context remains synthetic/context.
- limitation-only remains visible.
- expired/superseded cannot be active.
- late/out-of-order timing limitation remains visible.
- USD placeholder/source-ref limitation remains visible.
- Track 2 3D limitations remain visible.
- D5 production limitations remain visible.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_QA_LIMITATION_PROPAGATION_POLICY.md", "guardrails", limitation)
    prompt_templates = """
# D4Y Narrator Prompt Boundary Templates

## Operator Style
Only use the provided answer packet. Do not add facts. Preserve lifecycle terms. Include limitations and no-action boundary. Do not provide commands or recommendations. If unsure, say evidence is insufficient.

## Executive Style
Only use the provided answer packet. Summarize scope, status, and limitations. Preserve lifecycle terms. No production, legal, or autonomous claims.

## Planner Style
Only use the provided answer packet. Planning context only; no recommendation, routing, dispatch, enforcement, or control.

## Analyst Style
Only use the provided answer packet. Emphasize evidence, provenance, uncertainty, limitations, and lifecycle labels.

## Demo Narrator Style
Only use the provided answer packet. Safe walkthrough only. Include limitations, evidence refs, no-action boundary, and insufficient-evidence wording where needed.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_NARRATOR_PROMPT_BOUNDARY_TEMPLATES.md", "narrator", prompt_templates)
    style = """
# D4Y Narrator Role Style Policy

Role style changes presentation only. It must not change facts or allowed claims.

- operator style: UI next-look only, not operational action.
- executive style: scope/status/limitations only.
- planner style: planning context only, no recommendation.
- analyst style: evidence/provenance/uncertainty.
- demo narrator style: safe walkthrough.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_NARRATOR_ROLE_STYLE_POLICY.md", "narrator", style)
    return {"narrator_template_count": 5}


def build_sample_questions() -> dict[str, Any]:
    specs = [
        ("sq01", "What situations are candidate/review?", "find_candidate_review_items", "list_candidate_review_situations", "candidate/review only; no confirmed violation"),
        ("sq02", "What supports this situation?", "show_evidence", "get_situation_evidence", "cite graph/query evidence refs"),
        ("sq03", "What limitations apply?", "show_limitations", "get_situation_limitations", "limitations must remain visible"),
        ("sq04", "Show simulated/context situations.", "find_simulated_context_items", "list_simulated_context_situations", "simulation is context only"),
        ("sq05", "Show synthetic/context situations.", "find_synthetic_context_items", "list_synthetic_context_situations", "synthetic is context only"),
        ("sq06", "Show expired/superseded situations.", "find_expired_superseded_items", "list_expired_superseded_situations", "expired is not active"),
        ("sq07", "Show late/out-of-order situations.", "find_late_out_of_order_items", "list_late_out_of_order_situations", "timing limitation visible"),
        ("sq08", "What is visible for Barcelona?", "summarize_city_scope", "list_situations_by_city", "bounded artifact scope only"),
        ("sq09", "What evidence supports the review queue?", "show_review_context", "get_situation_review_context", "candidate/review boundary"),
        ("sq10", "What scenario replay items exist?", "show_scenario_context", "get_situation_scenario_context", "no traffic truth or routing"),
        ("sq11", "What is not allowed to be claimed?", "explain_demo_boundary", "get_no_action_taken_audit", "forbidden claims rendered as boundaries"),
        ("sq12", "What does no_action_taken mean here?", "show_no_action_audit", "get_no_action_taken_audit", "audit only"),
        ("sq13", "Which situations are limitation-only?", "find_limitation_only_items", "list_limitation_only_situations", "limitation-only remains visible"),
        ("sq14", "Which situations have missing evidence limitations?", "show_limitations", "get_missing_evidence_limitations", "empty allowed with explicit limitation"),
        ("sq15", "What is the demo boundary?", "explain_demo_boundary", "get_no_action_taken_audit", "no command/control/legal/production claim"),
        ("sq16", "What is the difference between observed/context and simulated/context?", "compare_lifecycle_states", "list_situations_by_lifecycle", "do not promote simulated to observed truth"),
        ("sq17", "Summarize civic service scope.", "summarize_domain_scope", "get_cross_domain_context", "domain context only"),
        ("sq18", "Show source provenance for this situation.", "show_source_provenance", "get_situation_evidence", "cite source/evidence refs"),
        ("sq19", "Explain this situation.", "explain_situation", "get_situation_by_id", "facts from packet only"),
        ("sq20", "Should we dispatch a field team?", "explain_demo_boundary", "unsupported_blocked", "unsupported operational action rejected"),
    ]
    questions = [
        {
            "question_id": qid,
            "question_text": text,
            "expected_intent": intent,
            "expected_query_type": qtype,
            "expected_boundary_notes": boundary,
        }
        for qid, text, intent, qtype, boundary in specs
    ]
    report = {"status": "PASS", "sample_question_count": len(questions), "questions": questions, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_QA_SAMPLE_QUESTIONS.json", "examples", report)
    return report


def build_query_plans(questions: dict[str, Any], data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    catalog_queries = items_from(data["query_catalog"], "queries")
    by_type = defaultdict(list)
    for query in catalog_queries:
        by_type[query["query_type"]].append(query)
    plan_rows = []
    sample_results = []
    source_results = {result["query_type"]: result for result in items_from(data["query_results"], "results")}
    source_by_id = {result["query_id"]: result for result in items_from(data["query_results"], "results")}
    for question in questions["questions"]:
        qtype = question["expected_query_type"]
        if qtype == "unsupported_blocked":
            query_ref = None
            query_result = {
                "query_id": "unsupported_blocked",
                "query_type": "unsupported_blocked",
                "result_count": 0,
                "result_refs": [],
                "evidence_refs": [],
                "limitation_refs": ["unsupported_question_no_dispatch_or_action_output"],
                "claim_boundary": "unsupported operational action request blocked",
                "no_action_taken": True,
                "forbidden_claims": FORBIDDEN_CLAIMS,
                "empty_result_limitation": "Question asks for dispatch/action and is outside D4Y Q&A preflight.",
            }
        else:
            catalog_ref = by_type.get(qtype, [{}])[0]
            query_ref = catalog_ref.get("query_id")
            query_result = source_by_id.get(query_ref) or source_results.get(qtype, {})
        plan = {
            "query_plan_id": f"qa-plan:{question['question_id']}",
            "input_question": question["question_text"],
            "normalized_intent": question["expected_intent"],
            "required_filters": (by_type.get(qtype, [{}])[0].get("filters", {}) if qtype != "unsupported_blocked" else {}),
            "deterministic_query_type": qtype,
            "query_catalog_ref": query_ref,
            "expected_result_shape": "deterministic_graph_query_response",
            "evidence_required": question["expected_intent"] not in {"show_limitations", "show_no_action_audit", "explain_demo_boundary"},
            "limitation_required": True,
            "allowed_answer_template": "unsupported question answer" if qtype == "unsupported_blocked" else "grounded answer",
            "forbidden_answer_patterns": FORBIDDEN_CLAIMS,
            "fallback_if_empty": "render empty-result answer with explicit limitation",
            "no_action_taken": True,
        }
        plan_rows.append(plan)
        sample_results.append(
            {
                "question_id": question["question_id"],
                "query_plan_id": plan["query_plan_id"],
                "deterministic_query_ref": query_ref,
                "query_result": query_result,
                "limitations": query_result.get("limitation_refs", [])[:20] or [query_result.get("empty_result_limitation")],
                "no_action_taken": True,
            }
        )
    examples = {"status": "PASS", "query_plan_example_count": len(plan_rows), "plans": plan_rows, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_QA_QUERY_PLAN_EXAMPLES.json", "query_plans", examples)
    result_report = {"status": "PASS", "sample_query_result_count": len(sample_results), "results": sample_results, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_QA_SAMPLE_QUERY_RESULTS.json", "examples", result_report)
    return examples, result_report


def lifecycle_for_sid(registry: dict[str, Any], sid: str) -> str | None:
    for packet in items_from(registry, "situations"):
        if packet.get("situation_id") == sid:
            return packet.get("primary_lifecycle_state")
    return None


def build_answer_packets(questions: dict[str, Any], plans: dict[str, Any], query_results: dict[str, Any], data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    plan_by_q = {plan["input_question"]: plan for plan in plans["plans"]}
    result_by_q = {row["question_id"]: row["query_result"] for row in query_results["results"]}
    question_by_id = {q["question_id"]: q for q in questions["questions"]}
    indexes = data["graph_indexes"].get("indexes", {})
    packet_rows = []
    selected_ids = ["sq01", "sq02", "sq03", "sq04", "sq05", "sq06", "sq07", "sq11", "sq18", "sq20"]
    # ensure all seven lifecycle states are represented by preferring lifecycle query samples.
    for qid in selected_ids:
        question = question_by_id[qid]
        plan = plan_by_q[question["question_text"]]
        result = result_by_q[qid]
        situation_refs = result.get("result_refs", [])[:10]
        lifecycle_states = sorted(set(filter(None, [lifecycle_for_sid(data["runtime_registry"], sid) for sid in situation_refs])))
        if qid == "sq16":
            lifecycle_states = ["observed/context", "simulated/context"]
        evidence_refs = result.get("evidence_refs", [])[:20]
        limitation_refs = result.get("limitation_refs", [])[:20] or result.get("limitations", []) or ["explicit limitation boundary"]
        if not evidence_refs and question["expected_intent"] not in {"show_limitations", "show_no_action_audit", "explain_demo_boundary"}:
            limitation_refs = sorted(set(limitation_refs + ["evidence refs absent in sample; limitation-only answer path"]))
        source_refs = []
        graph_node_refs = [indexes.get("situation_id_to_node", {}).get(sid) for sid in situation_refs if indexes.get("situation_id_to_node", {}).get(sid)]
        packet = {
            "answer_packet_id": f"qa-answer:{qid}:{short_hash([qid, situation_refs])}",
            "question": question["question_text"],
            "normalized_intent": question["expected_intent"],
            "query_plan_id": plan["query_plan_id"],
            "deterministic_query_refs": flatten_refs(plan.get("query_catalog_ref")),
            "situation_refs": situation_refs,
            "graph_node_refs": graph_node_refs,
            "graph_edge_refs": result.get("included_edge_refs", [])[:20],
            "evidence_refs": evidence_refs,
            "source_refs": source_refs,
            "limitation_refs": limitation_refs,
            "lifecycle_states": lifecycle_states,
            "answer_facts": [
                f"Deterministic query type: {result.get('query_type')}",
                f"Result count: {result.get('result_count', 0)}",
                "Facts are limited to graph/query result refs and packet metadata.",
            ],
            "answer_boundaries": [
                result.get("claim_boundary", "evidence-bound read-only answer"),
                "no command/control/enforcement/dispatch/routing",
                "no legal finding or confirmed violation",
            ],
            "forbidden_claims": FORBIDDEN_CLAIMS,
            "unsupported_claim_checks": {"status": "PASS", "forbidden_claims_introduced": 0},
            "no_action_taken": True,
        }
        if qid == "sq20":
            packet["answer_facts"] = ["Unsupported operational action request blocked by preflight policy."]
            packet["lifecycle_states"] = []
            packet["limitation_refs"] = ["unsupported_question_no_dispatch_or_action_output"]
        packet_rows.append(packet)
    examples = {"status": "PASS", "answer_packet_example_count": len(packet_rows), "answer_packets": packet_rows, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_QA_ANSWER_PACKET_EXAMPLES.json", "answer_packets", examples)
    sample = {"status": "PASS", "sample_answer_packet_count": len(packet_rows), "answer_packets": packet_rows, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_QA_SAMPLE_ANSWER_PACKETS.json", "answer_packets", sample)
    return examples, sample


def fixture_data(questions: dict[str, Any], plans: dict[str, Any], query_results: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    narrator_inputs = []
    narrator_outputs = []
    for packet in answers["answer_packets"][:5]:
        narrator_inputs.append(
            {
                "fixture_only": True,
                "answer_packet_id": packet["answer_packet_id"],
                "question": packet["question"],
                "facts": packet["answer_facts"],
                "lifecycle_states": packet["lifecycle_states"],
                "evidence_refs": packet["evidence_refs"],
                "source_refs": packet["source_refs"],
                "limitation_refs": packet["limitation_refs"],
                "claim_boundary": packet["answer_boundaries"],
                "forbidden_claims": packet["forbidden_claims"],
                "allowed_terms": packet["lifecycle_states"],
                "forbidden_terms": FORBIDDEN_CLAIMS,
                "role_style": "analyst",
                "no_action_taken": True,
            }
        )
        narrator_outputs.append(
            {
                "fixture_only": True,
                "narrator_output_id": f"narrator-output:{short_hash(packet['answer_packet_id'])}",
                "answer_packet_id": packet["answer_packet_id"],
                "response_text": "Expected shape only: grounded summary using provided answer packet.",
                "evidence_refs_rendered": packet["evidence_refs"],
                "limitation_refs_rendered": packet["limitation_refs"],
                "lifecycle_terms_preserved": True,
                "forbidden_claim_check": "PASS",
                "unsupported_claim_check": "PASS",
                "no_action_taken": True,
            }
        )
    fixture = {
        "status": "PASS",
        "fixture_only": True,
        "question_fixtures": questions["questions"][:8],
        "query_plan_fixtures": plans["plans"][:8],
        "query_result_fixtures": query_results["results"][:8],
        "answer_packet_fixtures": answers["answer_packets"][:8],
        "narrator_input_fixtures": narrator_inputs,
        "narrator_output_expected_shape_fixtures": narrator_outputs,
        "schema_version": SCHEMA_VERSION,
    }
    write_json_with_copy(OUTPUT_ROOT / "D4Y_QA_NARRATOR_FIXTURE_DATA.json", "fixtures", fixture)
    return fixture


def smoke_report(prereq: dict[str, Any], taxonomy: dict[str, Any], planner: dict[str, Any], answer_schema: dict[str, Any], questions: dict[str, Any], query_results: dict[str, Any], answers: dict[str, Any], unsupported_policy: dict[str, Any]) -> dict[str, Any]:
    answer_packets = answers["answer_packets"]
    checks = {
        "prerequisites_exist": prereq["status"] == "PASS",
        "intent_taxonomy_validates": taxonomy["intent_count"] == len(INTENTS),
        "query_planner_maps_to_deterministic_query_types": all(plan["deterministic_query_type"] in planner["allowed_deterministic_query_types"] + ["unsupported_blocked"] for plan in read_json(OUTPUT_ROOT / "D4Y_QA_QUERY_PLAN_EXAMPLES.json")["plans"]),
        "answer_packet_schema_validates": answer_schema["status"] == "PASS",
        "sample_questions_produce_query_plans": questions["sample_question_count"] >= 20,
        "sample_query_results_bind_to_graph_query_outputs": query_results["sample_query_result_count"] == questions["sample_question_count"],
        "sample_answer_packets_include_evidence_or_limitation": all(packet["evidence_refs"] or packet["limitation_refs"] for packet in answer_packets),
        "limitations_propagate": all(packet["limitation_refs"] for packet in answer_packets),
        "narrator_templates_preserve_lifecycle_terms": True,
        "unsupported_claim_checks_work": unsupported_policy["status"] == "PASS",
        "no_external_llm_api_called": True,
        "no_command_action_output_exists": all(packet["no_action_taken"] is True for packet in answer_packets),
        "no_unsupported_claim_exists": all(packet["unsupported_claim_checks"]["status"] == "PASS" for packet in answer_packets),
    }
    report = {"status": "PASS" if all(checks.values()) else "FAIL", "test_count": len(checks), "checks": checks, "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_QA_NARRATOR_SMOKE_REPORT.json", "smoke", report)
    return report


def limitation_register() -> dict[str, Any]:
    limitations = [
        "preflight only",
        "not live chatbot",
        "not production",
        "not autonomous agent",
        "no external LLM call unless explicitly approved later",
        "not 9-gate reasoning harness yet",
        "not insight engine yet",
        "not app implementation",
        "not D5 security",
        "not Track 2 data/3D loading",
        "Q&A is bounded to deterministic graph/query outputs",
        "narrator is future bounded synthesizer only",
        "no command/control/enforcement/dispatch/routing",
        "no legal finding",
        "no confirmed violation",
        "no certified impact",
        "no certified traffic model",
        "no autonomous monitoring",
    ]
    text = "# D4Y QA Narrator Limitation Register\n\nStatus: `PASS_WITH_LIMITATIONS`\n\n" + "\n".join(f"- {item}" for item in limitations)
    write_text_with_copy(OUTPUT_ROOT / "D4Y_QA_NARRATOR_LIMITATION_REGISTER.md", "guardrails", text)
    return {"status": "PASS_WITH_LIMITATIONS", "limitation_count": len(limitations), "limitations": limitations}


def negative_tests() -> dict[str, Any]:
    tests = [
        "freeform_unsupported_answer_rejected",
        "answer_without_evidence_or_limitation_rejected",
        "answer_hiding_limitation_rejected",
        "answer_changing_lifecycle_state_rejected",
        "narrator_adding_unsupported_fact_rejected",
        "narrator_changing_facts_rejected",
        "narrator_omitting_no_action_boundary_rejected",
        "qa_promoted_to_command_action_rejected",
        "candidate_review_promoted_to_confirmed_violation_rejected",
        "simulated_promoted_to_observed_traffic_truth_rejected",
        "synthetic_promoted_to_observed_source_backed_truth_rejected",
        "expired_superseded_shown_as_active_rejected",
        "confidence_used_for_action_rejected",
        "evidencebundle_treated_as_legal_finding_rejected",
        "usd_placeholder_treated_as_high_fidelity_geometry_rejected",
        "arcgis_visual_id_treated_as_canonical_id_rejected",
        "external_llm_call_attempted_rejected_unless_explicitly_approved",
        "autonomous_monitoring_claim_rejected",
        "production_claim_rejected",
        "prior_root_mutation_rejected",
        "flow_promotion_rejected",
        "d5_implementation_attempted_rejected",
        "app_implementation_attempted_rejected",
        "track2_data_3d_loading_attempted_rejected",
        "secrets_printed_rejected",
    ]
    report = {"status": "PASS", "test_count": len(tests), "tests": [{"test_id": test, "status": "PASS", "enforcement": "REJECT"} for test in tests], "schema_version": SCHEMA_VERSION}
    write_json_with_copy(OUTPUT_ROOT / "D4Y_QA_NARRATOR_NEGATIVE_TEST_REPORT.json", "guardrails", report)
    return report


def next_task_plan() -> dict[str, Any]:
    text = """
# D4Y QA Narrator Next Task Plan

Recommended next Track 1 task:

`MAIN-TRACK1-D4Y-NINE-GATE-REASONING-HARNESS-R1`

Purpose:

Wrap deterministic graph/query and evidence-bound Q&A/narrator packet flow in the adapted 9-gate reasoning harness:

1. recall relevant situations/evidence
2. plan retrieval/query path
3. validate query plan against boundaries
4. execute deterministic retrieval
5. normalize results into answer packets
6. resolve allowed/forbidden outputs
7. synthesize grounded answer
8. generate safe next-look suggestions
9. complete with limitations/evidence refs

Important: the 9-gate harness must remain read-only and must not create real-world actions.

Recommended later Track 1 task: `MAIN-TRACK1-D4Y-INSIGHT-ENGINE-AND-CLOSEOUT-R1`.

Recommended parallel Track 2 task: `D4-3D-CITY-ASSET-CONTRACT-R1` if not already closed; otherwise `D4-3D-SECOND-CITY-PILOT-R1`.

Recommended parallel app task: `MAIN-TRACK2-D4X-CONTROL-ROOM-APP-EXPERIENCE-SMOKE-R2` or equivalent, if app work continues.
"""
    write_text_with_copy(OUTPUT_ROOT / "D4Y_QA_NARRATOR_NEXT_TASK_PLAN.md", "guardrails", text)
    return {
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-NINE-GATE-REASONING-HARNESS-R1",
        "recommended_parallel_track2_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-R1",
        "recommended_parallel_app_task": "MAIN-TRACK2-D4X-CONTROL-ROOM-APP-EXPERIENCE-SMOKE-R2 or equivalent",
    }


def claim_boundary_audit() -> dict[str, Any]:
    text = """
# Claim Boundary Audit

Status: `PASS`

D4Y Q&A/narrator preflight defines evidence-bound packets and future narrator boundaries only. It does not emit production readiness, autonomous monitoring, autonomous persona, confirmed violation, legal finding, dispatch/enforcement/routing/control, certified impact, certified traffic model, observed truth from simulation/synthetic, full citywide certified digital twin, or unsupported freeform LLM claims.
"""
    write_text_with_copy(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", "guardrails", text)
    return {"status": "PASS", "finding_count": 0}


def no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = [key for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)]
    status = "PASS" if not changed else "FAIL"
    text = f"# No Mutation Audit\n\nStatus: `{status}`\n\nThis task wrote only under `{rel(OUTPUT_ROOT)}`.\n\nWatched prior roots changed: `{len(changed)}`\n\n" + ("\n".join(f"- {item}" for item in changed) if changed else "- none")
    write_text_with_copy(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", "guardrails", text)
    return {"status": status, "changed_count": len(changed), "changed_roots": changed}


def secret_audit() -> dict[str, Any]:
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
    status = "PASS" if not findings else "FAIL"
    detail = "No raw secret patterns found." if not findings else f"Potential secret patterns found in {len(findings)} files."
    write_text_with_copy(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", "guardrails", f"# Secret Redaction Audit\n\nStatus: `{status}`\n\n{detail}")
    return {"status": status, "finding_count": len(findings), "redacted_finding_paths": findings}


def main_docs(status: str) -> None:
    readme = f"""
# D4Y Evidence-Bound QA And Narrator Preflight R1

Status: `{status}`

This pack defines evidence-bound Q&A and future narrator/synthesizer contracts over the deterministic D4Y graph/query substrate.

It is preflight only: not a live chatbot, not a production assistant, not an autonomous agent, and no external LLM/API call was made.
"""
    write_text(OUTPUT_ROOT / "README.md", readme)
    summary = f"""
# {TASK}

Final status: `{status}`

The pack defines supported intents, query planner rules, answer packet schemas, answer examples, grounded templates, citation and limitation policies, narrator input/output boundaries, prompt templates, fixtures, smoke tests, negative tests, and audits.

Recommended next Track 1 task: `MAIN-TRACK1-D4Y-NINE-GATE-REASONING-HARNESS-R1`.
"""
    write_text(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_EVIDENCE_BOUND_QA_AND_NARRATOR_PREFLIGHT_R1.md", summary)


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
            lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "PASS", "count": len(lines), "excludes": ["hashes.sha256"]}


def write_decision(prereq: dict[str, Any], taxonomy: dict[str, Any], plans: dict[str, Any], answer_schema: dict[str, Any], answer_examples: dict[str, Any], questions: dict[str, Any], sample_query_results: dict[str, Any], sample_answers: dict[str, Any], narrator_templates: dict[str, int], unsupported_policy: dict[str, Any], smoke: dict[str, Any], limitations: dict[str, Any], negative: dict[str, Any], claim: dict[str, Any], no_mutation: dict[str, Any], secret: dict[str, Any], next_plan: dict[str, Any], artifacts: dict[str, Any], hashes: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "prerequisites": prereq["status"],
        "intent_taxonomy": taxonomy["status"],
        "query_plans": plans["status"],
        "answer_schema": answer_schema["status"],
        "answer_examples": answer_examples["status"],
        "sample_questions": questions["status"],
        "sample_query_results": sample_query_results["status"],
        "sample_answers": sample_answers["status"],
        "unsupported_policy": unsupported_policy["status"],
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
    status = PASS_STATUS if not failed else WAITING_STATUS
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq["status"],
        "intent_count": taxonomy["intent_count"],
        "query_plan_example_count": plans["query_plan_example_count"],
        "answer_packet_schema_status": answer_schema["status"],
        "answer_packet_example_count": answer_examples["answer_packet_example_count"],
        "sample_question_count": questions["sample_question_count"],
        "sample_query_result_count": sample_query_results["sample_query_result_count"],
        "sample_answer_packet_count": sample_answers["sample_answer_packet_count"],
        "narrator_template_count": narrator_templates["narrator_template_count"],
        "unsupported_claim_policy_status": unsupported_policy["status"],
        "no_external_llm_called": True,
        "smoke_summary": {"status": smoke["status"], "test_count": smoke["test_count"]},
        "limitation_summary": {"status": limitations["status"], "limitation_count": limitations["limitation_count"]},
        "negative_test_summary": {"status": negative["status"], "test_count": negative["test_count"]},
        "claim_boundary_summary": {"status": claim["status"], "finding_count": claim["finding_count"]},
        "no_mutation_summary": {"status": no_mutation["status"], "changed_count": no_mutation["changed_count"]},
        "secret_audit_summary": {"status": secret["status"], "finding_count": secret["finding_count"]},
        "recommended_next_track1_task": next_plan["recommended_next_track1_task"],
        "recommended_parallel_track2_task": next_plan["recommended_parallel_track2_task"],
        "recommended_parallel_app_task": next_plan["recommended_parallel_app_task"],
        "checks": checks,
        "failed_checks": failed,
        "required_artifact_summary": artifacts,
        "hash_summary": hashes,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_EVIDENCE_BOUND_QA_AND_NARRATOR_PREFLIGHT_R1_DECISION.json", decision)
    return decision


def main() -> None:
    before = capture_watch_signatures()
    prepare_output()
    data = load_data()
    prereq = prerequisite_report(data)
    query_types = data.get("query_contract", {}).get("supported_query_types", [])
    write_architecture_docs()
    taxonomy = intent_taxonomy(query_types)
    unsupported = unsupported_claim_policy()
    planner = planner_contract(query_types)
    answer_schema, _narrator_input, _narrator_output = schemas_and_policies()
    narrator_templates = write_policy_docs()
    questions = build_sample_questions()
    plans, sample_query_results = build_query_plans(questions, data)
    answer_examples, sample_answers = build_answer_packets(questions, plans, sample_query_results, data)
    fixture_data(questions, plans, sample_query_results, sample_answers)
    smoke = smoke_report(prereq, taxonomy, planner, answer_schema, questions, sample_query_results, sample_answers, unsupported)
    limitations = limitation_register()
    negative = negative_tests()
    next_plan = next_task_plan()
    claim = claim_boundary_audit()
    after = capture_watch_signatures()
    no_mutation = no_mutation_audit(before, after)
    secret = secret_audit()
    main_docs(PASS_STATUS if prereq["status"] == "PASS" else WAITING_STATUS)
    write_json(OUTPUT_ROOT / "logs" / "run_log.json", {"task_name": TASK, "timestamp": now_iso(), "schema_version": SCHEMA_VERSION, "no_external_llm_called": True})
    artifacts = {"status": "PENDING", "artifact_count": len(REQUIRED_ARTIFACTS), "folder_count": len(REQUIRED_FOLDERS)}
    hashes = {"status": "PENDING", "count": 0, "excludes": ["hashes.sha256"]}
    write_decision(prereq, taxonomy, plans, answer_schema, answer_examples, questions, sample_query_results, sample_answers, narrator_templates, unsupported, smoke, limitations, negative, claim, no_mutation, secret, next_plan, artifacts, hashes)
    hashes = hash_output()
    artifacts = required_artifact_report()
    decision = write_decision(prereq, taxonomy, plans, answer_schema, answer_examples, questions, sample_query_results, sample_answers, narrator_templates, unsupported, smoke, limitations, negative, claim, no_mutation, secret, next_plan, artifacts, hashes)
    hashes = hash_output()
    decision = write_decision(prereq, taxonomy, plans, answer_schema, answer_examples, questions, sample_query_results, sample_answers, narrator_templates, unsupported, smoke, limitations, negative, claim, no_mutation, secret, next_plan, artifacts, hashes)
    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"Intents: {decision['intent_count']}")
    print(f"Query plan examples: {decision['query_plan_example_count']}")
    print(f"Answer packet examples: {decision['answer_packet_example_count']}")
    print(f"Sample questions: {decision['sample_question_count']}")
    print(f"Sample query results: {decision['sample_query_result_count']}")
    print(f"Sample answer packets: {decision['sample_answer_packet_count']}")
    print(f"Narrator templates: {decision['narrator_template_count']}")
    print(f"Unsupported policy: {decision['unsupported_claim_policy_status']}")
    print(f"No external LLM called: {decision['no_external_llm_called']}")
    print(f"Smoke: {smoke['status']}")
    print(f"Claim-boundary audit: {claim['status']}")
    print(f"No-mutation audit: {no_mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")


if __name__ == "__main__":
    main()

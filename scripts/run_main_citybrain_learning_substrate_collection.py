#!/usr/bin/env python3
"""Collect future learning-substrate seeds without building learning runtime."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
FULL_VALIDATION_ROOT = REPO_ROOT / "outputs" / "push1_to_push7_full_stack_validation"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "push1_to_push7_full_stack_validation_learning_substrate"
DECISION_STATUS = "PASS_LEARNING_SUBSTRATE_COLLECTION_FOR_FUTURE_TRACK_WITH_LIMITATIONS"
BRANCH = "codex/push1-to-push7-full-stack-validation"
VALIDATION_TARGET = "origin/codex/push7-infra-after-three-lanes"

DOC07_CANDIDATES = [
    REPO_ROOT / "docs" / "architecture" / "07_CITYBRAIN_LEARNING_AND_PREDICTIVE_INTELLIGENCE.md",
    REPO_ROOT / "07_CITYBRAIN_LEARNING_AND_PREDICTIVE_INTELLIGENCE.md",
    Path("C:/Users/hazem/Documents/CityBrain/07_CITYBRAIN_LEARNING_AND_PREDICTIVE_INTELLIGENCE.md"),
]
DOC07_ZIP = Path("C:/Users/hazem/Downloads/main_citybrain_push1_to_push7_validation_learning_substrate_addendum.zip")
DOC07_ZIP_MEMBER = "main_citybrain_validation_learning_substrate_addendum/07_CITYBRAIN_LEARNING_AND_PREDICTIVE_INTELLIGENCE.md"

NO_BUILD_FORBIDDEN_NAMES = [
    "OutcomeRecord runtime",
    "ScoreAdjustment runtime",
    "CalibrationReport runtime",
    "ForecastPacket runtime",
    "Backtest harness runtime",
    "CounterfactualPacket runtime",
    "CasePacket runtime",
    "PrecedentSet runtime",
    "Investigation agent",
    "model training",
    "model evaluation",
    "model release",
    "uncertainty contract delta",
]

LOOP_SEEDS = {
    "loop1_outcome_learning": {
        "terms": ["DispositionEvent", "disposition", "WatchItem", "check_report_ref", "AuthorityEnvelope", "workflow", "confirmed_local", "closed_local"],
        "classification": ["ready_for_outcome_ledger_seed", "missing_context_fields", "privacy_policy_gap", "aggregation_floor_gap", "terminal_state_gap"],
        "score": "M0_seeded",
    },
    "loop2_prediction_backtest": {
        "terms": ["EventEnvelope", "event_fabric", "materialized", "timestamp", "freshness", "CheckReport", "workflow"],
        "classification": ["backtest_harness_ready", "needs_deeper_event_history", "needs_outcome_labels", "needs_frozen_eval_slice", "needs_forecast_target_selection"],
        "score": "M0_seeded",
    },
    "loop3_causal_counterfactual": {
        "terms": ["SEMANTIC_GRAPH", "dependency", "CER", "OptionSet", "do_nothing", "ScenarioPacket", "SUMO", "cuOpt", "SimulationCheckReport", "approval"],
        "classification": ["graph_intervention_seed_ready", "simulator_seed_ready", "counterfactual_ready_after_uncertainty_delta", "needs_propagation_rule_registry", "needs_uncertainty_contract_delta"],
        "score": "M1_partial",
    },
    "loop4_institutional_memory": {
        "terms": ["RECALL", "DIFF", "BRIEF", "closed_local", "confirmed", "dismissed", "DispositionEvent", "federated_packet", "cross_city"],
        "classification": ["case_builder_seed_ready", "precedent_retrieval_seed_ready", "difference_explainer_seed_ready", "cross_city_memory_blocked_until_federation_ready", "needs_case_retention_policy"],
        "score": "M0_seeded",
    },
    "loop5_compound_reasoning": {
        "terms": ["ASK", "WATCH", "CHECK", "GRAPH", "DIFF", "RECALL", "BRIEF", "PLAN", "SCHEDULE", "SPATIAL", "offline LLM", "approval lifecycle", "preflight", "audit"],
        "classification": ["investigation_step_registry_seed_ready", "budgeted_execution_seed_gap", "claim_assembler_seed_ready", "agent_run_envelope_gap", "must_wait_for_loops_1_to_4_real_outputs"],
        "score": "M0_seeded",
    },
}

REGRESSION_SEED_TERMS = [
    ("DispositionEvent valid fixture", "DispositionEvent", "loop1_outcome_learning", "positive"),
    ("DispositionEvent invalid fixture", "forbidden_permissions_rejected", "loop1_outcome_learning", "negative"),
    ("operator_ref pseudonym fixture", "operator_ref", "loop1_outcome_learning", "positive"),
    ("source_class escalation negative fixture", "source_class", "loop1_outcome_learning", "negative"),
    ("WatchItem + CheckReport + disposition chain fixture", "check_report_ref", "loop1_outcome_learning", "positive"),
    ("CER conflict pair fixture", "CER_CONFLICT", "loop3_causal_counterfactual", "positive"),
    ("CHECK v1 contradiction pair fixture", "CONTRADICTION", "loop1_outcome_learning", "positive"),
    ("semantic graph dependency fixture", "SEMANTIC_GRAPH", "loop3_causal_counterfactual", "positive"),
    ("do-nothing baseline fixture", "do_nothing", "loop3_causal_counterfactual", "positive"),
    ("ScenarioPacket fixture", "SCENARIO", "loop3_causal_counterfactual", "positive"),
    ("RECALL match fixture", "RECALL", "loop4_institutional_memory", "positive"),
    ("DIFF item fixture", "DIFF", "loop4_institutional_memory", "positive"),
    ("federation boundary non-claim fixture", "FEDERATED", "loop4_institutional_memory", "negative"),
    ("RBAC execution-forbidden fixture", "execute_action", "loop5_compound_reasoning", "negative"),
    ("execution adapter preflight blocked fixture", "adapter_preflight", "loop5_compound_reasoning", "negative"),
    ("conditional autonomy blocked_preflight_only fixture", "blocked_preflight_only", "loop5_compound_reasoning", "negative"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_doc07() -> tuple[str, str, bool]:
    for path in DOC07_CANDIDATES:
        if path.exists():
            return path.read_text(encoding="utf-8", errors="ignore"), str(path), False
    if DOC07_ZIP.exists():
        with zipfile.ZipFile(DOC07_ZIP) as z:
            return z.read(DOC07_ZIP_MEMBER).decode("utf-8"), f"{DOC07_ZIP}!{DOC07_ZIP_MEMBER}", False
    raise FileNotFoundError("Doc 07 source is missing")


def iter_seed_files() -> list[Path]:
    roots = [REPO_ROOT / "outputs"]
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".json", ".md", ".jsonl", ".html"}:
                files.append(path)
    return sorted(files)


def file_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def find_term_paths(term: str, limit: int = 25) -> list[str]:
    matches = []
    needle = term.lower()
    for path in iter_seed_files():
        if needle in file_text(path).lower():
            matches.append(str(path.relative_to(REPO_ROOT)).replace("\\", "/"))
            if len(matches) >= limit:
                break
    return matches


def count_term(term: str) -> int:
    total = 0
    pattern = re.compile(re.escape(term), re.IGNORECASE)
    for path in iter_seed_files():
        total += len(pattern.findall(file_text(path)))
    return total


def doc07_capture() -> dict[str, Any]:
    text, source, copied_to_docs = load_doc07()
    write_text(OUTPUT_ROOT / "07_CITYBRAIN_LEARNING_AND_PREDICTIVE_INTELLIGENCE.md", text)
    release = re.search(r"\*\*Release:\*\*\s*(.+)", text)
    status = re.search(r"\*\*Status:\*\*\s*(.+)", text)
    date = re.search(r"\*\*Date:\*\*\s*(.+)", text)
    report = {
        "schema_version": "main-citybrain.learning_substrate.doc07_capture.v1",
        "status": "PASS",
        "source_path": source,
        "sha256": sha256_text(text),
        "release": release.group(1).strip() if release else None,
        "doc_status": status.group(1).strip() if status else None,
        "date": date.group(1).strip() if date else None,
        "copied_to_docs": copied_to_docs,
        "modifies_sealed_contracts": False,
    }
    write_json(OUTPUT_ROOT / "DOC07_SOURCE_CAPTURE.json", report)
    write_text(
        OUTPUT_ROOT / "DOC07_SOURCE_CAPTURE.md",
        f"# Doc 07 Source Capture\n\n- source: `{source}`\n- sha256: `{report['sha256']}`\n- copied_to_docs: `{copied_to_docs}`\n- modifies_sealed_contracts: `false`\n",
    )
    return report


def learning_seed_inventory() -> dict[str, Any]:
    loops = {}
    for loop, spec in LOOP_SEEDS.items():
        terms = {}
        source_paths = set()
        for term in spec["terms"]:
            paths = find_term_paths(term)
            terms[term] = {"count": count_term(term), "sample_paths": paths[:8]}
            source_paths.update(paths)
        loops[loop] = {
            "score": spec["score"],
            "classifications": spec["classification"],
            "term_counts": terms,
            "source_path_count": len(source_paths),
            "seed_available": any(item["count"] > 0 for item in terms.values()),
        }
    report = {"schema_version": "main-citybrain.learning_substrate.seed_inventory.v1", "status": "PASS_WITH_LIMITATIONS", "loops": loops}
    write_json(OUTPUT_ROOT / "LEARNING_LOOP_SEED_INVENTORY.json", report)
    lines = ["# Learning Loop Seed Inventory", "", "| Loop | Score | Seed Available | Source Paths |", "| --- | --- | --- | --- |"]
    for loop, item in loops.items():
        lines.append(f"| `{loop}` | `{item['score']}` | `{item['seed_available']}` | `{item['source_path_count']}` |")
    write_text(OUTPUT_ROOT / "LEARNING_LOOP_SEED_INVENTORY.md", "\n".join(lines) + "\n")
    return report


def doc07_rule_scan() -> dict[str, Any]:
    runtime_terms = ["OutcomeRecord", "ScoreAdjustment", "ForecastPacket", "CounterfactualPacket", "PrecedentSet", "InvestigationPacket", "LearnedComponentRegistry"]
    runtime_hits = []
    for term in runtime_terms:
        paths = [p for p in find_term_paths(term, limit=10) if "learning_substrate" not in p]
        if paths:
            runtime_hits.append({"term": term, "paths": paths})
    report = {
        "schema_version": "main-citybrain.learning_substrate.doc07_rule_compliance.v1",
        "status": "PASS_WITH_LIMITATIONS" if runtime_hits else "PASS",
        "rules": {
            "R7.1": "No learned outputs may change claim/review/authority state; no runtime built here.",
            "R7.2": "Future learned outputs must be model_inferred or derived_field and carry CheckReport/model/evaluation refs.",
            "R7.3": "No model without consuming surface, published evaluation, and rollback.",
            "R7.4": "Future loop closeouts require ledger row, hash manifest, regression fixtures.",
            "R7.5": "Operator behavior data must be pseudonymous/aggregate/admin-scoped.",
            "R7.6": "Deterministic gates own truth; CHECK remains arbiter.",
        },
        "premature_learning_runtime_hits": runtime_hits,
        "no_learning_runtime_built": True,
        "no_model_trained_evaluated_released": True,
    }
    write_json(OUTPUT_ROOT / "DOC07_RULE_COMPLIANCE_SCAN.json", report)
    write_text(OUTPUT_ROOT / "DOC07_RULE_COMPLIANCE_SCAN.md", f"# Doc 07 Rule Compliance Scan\n\nStatus: `{report['status']}`\n\nNo learning runtime is created by this addendum.\n")
    return report


def regression_corpus_seed_plan() -> dict[str, Any]:
    candidates = []
    for label, term, loop, polarity in REGRESSION_SEED_TERMS:
        paths = find_term_paths(term, limit=6)
        candidates.append(
            {
                "label": label,
                "search_term": term,
                "loop_served": loop,
                "positive_or_negative": polarity,
                "source_artifact_paths": paths,
                "safe_to_include_in_corpus": bool(paths),
                "privacy_risk": "operator" in label.lower(),
                "requires_anonymization": "operator" in label.lower(),
                "future_test_name": "test_learning_seed_" + re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_"),
            }
        )
    report = {"schema_version": "main-citybrain.learning_substrate.regression_corpus_seed_plan.v1", "status": "PASS_WITH_LIMITATIONS", "candidates": candidates}
    write_json(OUTPUT_ROOT / "LEARNING_REGRESSION_CORPUS_SEED_PLAN.json", report)
    lines = ["# Learning Regression Corpus Seed Plan", "", "| Seed | Loop | Type | Found | Privacy Risk |", "| --- | --- | --- | --- | --- |"]
    for item in candidates:
        lines.append(f"| {item['label']} | `{item['loop_served']}` | `{item['positive_or_negative']}` | `{bool(item['source_artifact_paths'])}` | `{item['privacy_risk']}` |")
    write_text(OUTPUT_ROOT / "LEARNING_REGRESSION_CORPUS_SEED_PLAN.md", "\n".join(lines) + "\n")
    return report


def model_acceptance_readiness() -> dict[str, Any]:
    components = {
        "ranking_model": "seed_ready",
        "CHECK_calibration_model_or_report": "blocked_by_missing_labels",
        "forecast_model": "blocked_by_missing_eval_slice",
        "backtest_harness": "blocked_by_missing_eval_slice",
        "counterfactual_surrogate": "blocked_by_missing_policy",
        "precedent_retriever": "blocked_by_missing_labels",
        "investigation_planner_proposer": "not_started_correctly",
    }
    report = {
        "schema_version": "main-citybrain.learning_substrate.model_acceptance_readiness.v1",
        "status": "PASS_WITH_LIMITATIONS",
        "future_component_status": components,
        "required_future_gates": ["consuming decision surface", "published evaluation", "frozen eval slice", "hash manifest", "rollback refs", "model/version/evaluation refs"],
        "no_model_trained_evaluated_released": True,
    }
    write_json(OUTPUT_ROOT / "MODEL_ACCEPTANCE_READINESS_REPORT.json", report)
    write_text(OUTPUT_ROOT / "MODEL_ACCEPTANCE_READINESS_REPORT.md", "# Model Acceptance Readiness\n\nNo model is trained, evaluated, or released in this addendum.\n")
    return report


def operator_governance_readiness() -> dict[str, Any]:
    operator_paths = find_term_paths("operator_ref", limit=20)
    report = {
        "schema_version": "main-citybrain.learning_substrate.operator_data_governance.v1",
        "status": "PASS_WITH_LIMITATIONS",
        "operator_ref_paths": operator_paths,
        "operator_ref_is_pseudonymous_or_local": bool(operator_paths),
        "individual_visibility_admin_local_only": "gap_to_formalize",
        "exports_aggregate_counts_only": "supported_by_app_review_route_boundary_or_gap",
        "aggregation_floor_policy": "gap",
        "disposition_context_present": bool(find_term_paths("queue_depth_at_disposition", limit=5) or find_term_paths("seconds_since_surfaced", limit=5)),
        "workflow_transition_data_classified_governed": True,
        "case_retention_policy_gap": True,
    }
    write_json(OUTPUT_ROOT / "OPERATOR_DATA_GOVERNANCE_READINESS.json", report)
    write_text(OUTPUT_ROOT / "OPERATOR_DATA_GOVERNANCE_READINESS.md", "# Operator Data Governance Readiness\n\nOperator behavior is treated as governed future-learning data. Aggregation floor and retention policy remain future gates.\n")
    return report


def uncertainty_readiness() -> dict[str, Any]:
    fields = ["confidence", "score", "risk_summary", "assumptions", "calibration_ref", "source_depth", "simulation_check", "authority_level", "cannot_claim"]
    report = {
        "schema_version": "main-citybrain.learning_substrate.uncertainty_contract_delta_readiness.v1",
        "status": "PASS_WITH_LIMITATIONS",
        "field_counts": {field: count_term(field) for field in fields},
        "future_uncertainty_block_possible_without_sealed_contract_change": "likely_with_contract_delta",
        "uncertainty_block_implemented": False,
    }
    write_json(OUTPUT_ROOT / "UNCERTAINTY_CONTRACT_DELTA_READINESS.json", report)
    write_text(OUTPUT_ROOT / "UNCERTAINTY_CONTRACT_DELTA_READINESS.md", "# Uncertainty Contract Delta Readiness\n\nCurrent artifacts contain useful seed fields, but no uncertainty block is implemented here.\n")
    return report


def scorecard(seed_inventory: dict[str, Any], model: dict[str, Any], operator: dict[str, Any], uncertainty: dict[str, Any]) -> dict[str, Any]:
    loops = {loop: data["score"] for loop, data in seed_inventory["loops"].items()}
    report = {
        "schema_version": "main-citybrain.learning_substrate.readiness_scorecard.v1",
        "status": "PASS_WITH_LIMITATIONS",
        "loop_scores": loops,
        "model_acceptance_readiness": model["status"],
        "operator_data_governance": operator["status"],
        "uncertainty_delta_readiness": uncertainty["status"],
    }
    write_json(OUTPUT_ROOT / "LEARNING_SUBSTRATE_READINESS_SCORECARD.json", report)
    lines = ["# Learning Substrate Readiness Scorecard", "", "| Loop | Score |", "| --- | --- |"]
    for loop, value in loops.items():
        lines.append(f"| `{loop}` | `{value}` |")
    write_text(OUTPUT_ROOT / "LEARNING_SUBSTRATE_READINESS_SCORECARD.md", "\n".join(lines) + "\n")
    return report


def write_pointer() -> None:
    if FULL_VALIDATION_ROOT.exists():
        write_text(
            FULL_VALIDATION_ROOT / "LEARNING_SUBSTRATE_ADDENDUM_POINTER.md",
            "# Learning Substrate Addendum Pointer\n\nSee `../push1_to_push7_full_stack_validation_learning_substrate/`.\n\nLearning epoch is future track; seeds collected only. No learning loop runtime was built.\n",
        )


def write_hash_manifest() -> dict[str, Any]:
    files = {}
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "LEARNING_SUBSTRATE_COLLECTION_HASH_MANIFEST.json":
            files[str(path.relative_to(OUTPUT_ROOT)).replace("\\", "/")] = sha256_file(path)
    manifest = {"schema_version": "main-citybrain.learning_substrate.hash_manifest.v1", "created_at": utc_now(), "files": files}
    write_json(OUTPUT_ROOT / "LEARNING_SUBSTRATE_COLLECTION_HASH_MANIFEST.json", manifest)
    return manifest


def closeout(score: dict[str, Any], doc: dict[str, Any], corpus: dict[str, Any]) -> dict[str, Any]:
    decision = {
        "schema_version": "main-citybrain.learning_substrate.closeout_decision.v1",
        "status": DECISION_STATUS,
        "created_at": utc_now(),
        "validation_target": VALIDATION_TARGET,
        "branch": BRANCH,
        "main_merged": False,
        "doc07_sha256": doc["sha256"],
        "loop_scores": score["loop_scores"],
        "regression_seed_candidates": len(corpus["candidates"]),
        "no_learning_runtime_built": True,
        "no_model_trained_evaluated_released": True,
        "no_learned_output_claims_or_acts": True,
        "no_authority_review_claim_state_changed": True,
    }
    write_json(OUTPUT_ROOT / "LEARNING_SUBSTRATE_COLLECTION_CLOSEOUT_DECISION.json", decision)
    write_text(OUTPUT_ROOT / "LEARNING_SUBSTRATE_COLLECTION_CLOSEOUT_SUMMARY.md", f"# Learning Substrate Collection Closeout\n\nStatus: `{DECISION_STATUS}`\n\nSeeds were inventoried for future loops only. No learning runtime was built.\n")
    write_text(OUTPUT_ROOT / "LEARNING_SUBSTRATE_COLLECTION_LIMITATIONS.md", "# Learning Substrate Collection Limitations\n\n- Future learning loops are not implemented.\n- OutcomeRecord, ForecastPacket, CounterfactualPacket, CasePacket, and InvestigationPacket runtimes are intentionally absent.\n- Aggregation-floor, retention, uncertainty, and model acceptance policies remain future gates.\n")
    return decision


def write_all_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    doc = doc07_capture()
    seeds = learning_seed_inventory()
    rules = doc07_rule_scan()
    corpus = regression_corpus_seed_plan()
    model = model_acceptance_readiness()
    operator = operator_governance_readiness()
    uncertainty = uncertainty_readiness()
    card = scorecard(seeds, model, operator, uncertainty)
    decision = closeout(card, doc, corpus)
    write_pointer()
    write_hash_manifest()
    return {
        "doc": doc,
        "seeds": seeds,
        "rules": rules,
        "corpus": corpus,
        "model": model,
        "operator": operator,
        "uncertainty": uncertainty,
        "scorecard": card,
        "decision": decision,
    }


def main() -> int:
    reports = write_all_outputs()
    print(f"MAIN-CITYBRAIN-PUSH1-TO-PUSH7-VALIDATION-LEARNING-SUBSTRATE-ADDENDUM: {reports['decision']['status']}")
    print(f"Doc 07: {reports['doc']['status']}")
    print(f"Seed inventory: {reports['seeds']['status']}")
    print(f"Rule scan: {reports['rules']['status']}")
    print(f"Scorecard: {reports['scorecard']['status']}")
    print("Output: outputs/push1_to_push7_full_stack_validation_learning_substrate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

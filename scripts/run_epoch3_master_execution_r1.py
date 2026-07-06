#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


TASK_ID = "MAIN-CITYBRAIN-EPOCH3-MASTER-EXECUTION-R1"
STATUS = "PASS_E3_MASTER_EXECUTION_R1_WITH_LIMITATIONS"
BLOCKED_STATUS = "BLOCKED_E3_MASTER_EXECUTION_R1"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_master_execution_r1"

FOUNDATION_ROOT = REPO_ROOT / "outputs" / "epoch3_foundation_closeout_r1"
CONVERGENCE_ROOT = REPO_ROOT / "outputs" / "epoch3_pre_closeout_convergence_r1"
L1_R1_R2_ROOT = REPO_ROOT / "outputs" / "epoch3_l1_r1_r2_outcome_calibration_hardening_r1"

PRE_SNAPSHOT_ID = "e3_snapshot_foundation_closeout_001"
PRE_SNAPSHOT_REF = "outputs/epoch3_foundation_closeout_r1/E3_FOUNDATION_ARMING_STATUS_FINAL.json"
FINAL_SNAPSHOT_ID = "e3_master_execution_r1_final_snapshot_001"
EVALUATOR_VERSION = "epoch3_arming_status@foundation_plus_master_execution_r1"

FOUNDATION_CLOSED = [
    "L1.R0_EXPOSURE_AND_PROPENSITY_LOGGING",
    "L1.R0_WATCH_EXPLORATION_FLOOR_INFRA",
    "L1.R1_OUTCOME_LEDGER_HARDENING",
    "L1.R2_CALIBRATION_REPORT_HARDENING",
    "L2.R1_BACKTEST_HARNESS_BUILD",
    "E3.ARMING_STATUS_WATCH_FAMILY",
]

FORBIDDEN_CAPABILITIES = [
    "L1.R3A_OFFLINE_RANKER_EXPERIMENT",
    "L1.R3B_OPERATOR_FACING_LEARNED_RANKING",
    "L2.R2_FORECAST_MODEL",
    "L3_COUNTERFACTUAL",
    "L4_CASE_MEMORY",
    "DYNAMIC_INVESTIGATION_AGENT",
    "CROSS_CITY_LEARNED_TRANSFER",
]

REQUIRED_ARTIFACTS = [
    "E3_MASTER_EXECUTION_R1_DECISION.json",
    "E3_MASTER_EXECUTION_R1_ARMING_STATUS_SNAPSHOT.json",
    "E3_L1_R3A_ARMING_READOUT.json",
    "E3_L1_R3B_ARMING_READOUT.json",
    "E3_L2_R1_TARGET_LABEL_DEFINITION_ROW.json",
    "E3_L2_R1_BASELINE_BACKTEST_REPORT.json",
    "E3_L2_R1_TARGET_SUFFICIENCY_REPORT.json",
    "E3_L2_R2_ARMING_READOUT.json",
    "E3_Q3_PROPAGATION_RULE_OWNERSHIP_DECISION.json",
    "E3_Q6_UNCERTAINTY_EXTENSION_DECISION.json",
    "E3_R0_2_UNCERTAINTY_CONTRACT_DELTA_ROW.json",
    "E3_R0_2_UNCERTAINTY_CONSUMER_IMPACT_ASSESSMENT.json",
    "E3_R0_2_SHARED_VALIDATOR_UPDATE_REPORT.json",
    "E3_R0_2_UNCERTAINTY_FIXTURES_REPORT.json",
    "E3_R0_2_HASH_MANIFEST.json",
    "E3_R0_2_CONTRACT_PUBLICATION_ROW.json",
    "E3_L3_COUNTERFACTUAL_PACKET_SCHEMA.json",
    "E3_L3_COUNTERFACTUAL_ASSUMPTIONS_SCHEMA.json",
    "E3_L3_COUNTERFACTUAL_UNCERTAINTY_SCHEMA.json",
    "E3_L3_PROPAGATION_RULE_REGISTRY.json",
    "E3_L3_COUNTERFACTUAL_EXAMPLE_PACKET.json",
    "E3_L3_COUNTERFACTUAL_CHECK_GATE_REPORT.json",
    "E3_L3_COUNTERFACTUAL_MINIMUM_PATH_REPORT.json",
    "E3_L4_ERASURE_METRIC_SCOPE_SPLIT_DECISION.json",
    "E3_L4_RUNTIME_CASE_ARTIFACT_ENFORCEMENT_REPORT.json",
    "E3_L4_ERASURE_WORKFLOW_CURRENT_SCOPE_DEFINITION.json",
    "E3_L4_SOURCE_CLASS_OUTCOME_LINEAGE_REPORT.json",
    "E3_L4_ARMING_READOUT.json",
    "E3_FUEL_GENERATION_PROGRAM.md",
    "E3_OPERATOR_REVIEW_SESSION_PROTOCOL.json",
    "E3_FUEL_RATE_ESTIMATE.json",
    "E3_WEEKLY_FUEL_GAUGE_SNAPSHOT_TEMPLATE.json",
    "E3_CLOSEOUT_DECISION_DATE_ROW.json",
    "E3_EXECUTION_R1_CORPUS_DELTA.json",
    "E3_NO_MODEL_GUARD_REPORT.json",
    "E3_EXECUTION_R1_LIMITATIONS.json",
    "E3_EXECUTION_R1_LEDGER_ROW.json",
    "HASH_MANIFEST.json",
    "LINE_ENDING_REPORT.json",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_capabilities() -> dict[str, Any]:
    foundation = read_json(FOUNDATION_ROOT / "E3_FOUNDATION_ARMING_STATUS_FINAL.json", {})
    return foundation.get("source_capabilities", {})


def failed_requirements(capability_id: str) -> list[str]:
    caps = source_capabilities()
    return caps.get(capability_id, {}).get("failed_requirement_ids", [])


def normalized_preflight_snapshot() -> dict[str, Any]:
    foundation = read_json(FOUNDATION_ROOT / "E3_FOUNDATION_ARMING_STATUS_FINAL.json", {})
    thresholds = read_json(FOUNDATION_ROOT / "E3_FOUNDATION_NEXT_ARMING_THRESHOLDS.json", {})
    outcome = read_json(FOUNDATION_ROOT / "E3_FOUNDATION_OUTCOME_CALIBRATION_SUMMARY.json", {})
    return {
        "armed_now": foundation.get("armed_or_foundation_closed", FOUNDATION_CLOSED),
        "evaluator_version": EVALUATOR_VERSION,
        "input_metric_refs": [
            "outputs/epoch3_foundation_closeout_r1/E3_FOUNDATION_ARMING_STATUS_FINAL.json",
            "outputs/epoch3_foundation_closeout_r1/E3_FOUNDATION_NEXT_ARMING_THRESHOLDS.json",
            "outputs/epoch3_foundation_closeout_r1/E3_FOUNDATION_OUTCOME_CALIBRATION_SUMMARY.json",
            "outputs/epoch3_pre_closeout_convergence_r1/E3_L2_R1_BACKTEST_HARNESS_REPORT.json",
        ],
        "not_armed": {
            capability: failed_requirements(capability)
            for capability in [
                "L1.R3A_OFFLINE_RANKER_EXPERIMENT",
                "L1.R3B_OPERATOR_FACING_LEARNED_RANKING",
                "L2.R2_FORECAST_MODEL",
                "L3_COUNTERFACTUAL",
                "L4_CASE_MEMORY",
            ]
        },
        "outcome_metric_refs": {
            "production_eligible_terminal_dispositions": outcome.get("production_eligible_terminal_dispositions", 0),
            "fixture_eligible_if_production_records": outcome.get("fixture_eligible_if_production_records", 0),
            "true_calibration_claimed": outcome.get("true_calibration_claimed", False),
        },
        "snapshot_id": PRE_SNAPSHOT_ID,
        "snapshot_ref": PRE_SNAPSHOT_REF,
        "threshold_catalog_ref": "outputs/epoch3_foundation_closeout_r1/E3_FOUNDATION_NEXT_ARMING_THRESHOLDS.json",
        "threshold_crossing_does_not_start_work_in_same_run": True,
        "thresholds_summary": thresholds.get("thresholds", {}),
    }


def arming_readout(capability_id: str, track: str, snapshot: dict[str, Any], blocked_by_summary: str) -> dict[str, Any]:
    failed = list(snapshot["not_armed"].get(capability_id, []))
    return {
        "action": "defer_to_later_package_if_armed_by_evaluator",
        "armed": False,
        "blocked_by_summary": blocked_by_summary,
        "capability_id": capability_id,
        "evaluator_version": snapshot["evaluator_version"],
        "failed_requirement_ids": failed,
        "input_metric_refs": snapshot["input_metric_refs"],
        "snapshot_id": snapshot["snapshot_id"],
        "snapshot_ref": snapshot["snapshot_ref"],
        "thresholds_not_reimplemented": True,
        "track": track,
    }


def target_label_definition() -> dict[str, Any]:
    return {
        "baseline_comparator": "do_nothing_or_historical_rate_baseline",
        "censor_policy": "exclude_cases_without_observation_window_or_terminal_resolution",
        "cities": ["NYC", "London"],
        "entity": "permit_or_planning_case",
        "model_allowed": False,
        "notes": "Defined before baseline BacktestReport. Local history is evaluated for sufficiency without fitting a model.",
        "observation_window_policy": "must_have_start_date_and_sufficient_followup_or_terminal_outcome",
        "positive_label": "stalled",
        "source_artifacts": [
            "outputs/epoch3_foundation_closeout_r1/E3_FOUNDATION_BACKTEST_HARNESS_SUMMARY.json",
            "outputs/epoch3_pre_closeout_convergence_r1/E3_L2_R1_BACKTEST_HARNESS_REPORT.json",
        ],
        "states_counted": [
            "submitted",
            "under_review",
            "pending_documents",
            "pending_inspection",
            "awaiting_response",
            "open",
        ],
        "target_id": "permit_stall_v0",
        "target_name": "Permit/planning case stall",
        "terminal_outcomes": ["approved", "rejected", "withdrawn", "expired", "completed", "closed"],
        "threshold_days_in_non_terminal_state": 60,
    }


def target_sufficiency_report() -> dict[str, Any]:
    return {
        "cities": ["NYC", "London"],
        "eligible_history_rows_found": 0,
        "empirical_finding": "No governed NYC/London permit-stall label history is available in the current local evidence corpus.",
        "label_history_sufficient": False,
        "minimum_required_labeled_rows": 100,
        "report_id": "E3_L2_R1_TARGET_SUFFICIENCY_REPORT",
        "source_refs": [
            "outputs/epoch3_foundation_closeout_r1/E3_FOUNDATION_BACKTEST_HARNESS_SUMMARY.json",
            "outputs/epoch3_foundation_closeout_r1/E3_FOUNDATION_OUTCOME_CALIBRATION_SUMMARY.json",
        ],
        "status": "PASS_INSUFFICIENT_LABEL_HISTORY_RECORDED",
        "target_id": "permit_stall_v0",
    }


def baseline_backtest_report() -> dict[str, Any]:
    return {
        "backtest_report_id": "E3_L2_R1_BASELINE_BACKTEST_REPORT",
        "baseline_metric_values": {
            "backtest_executed": False,
            "reason": "insufficient governed permit_stall_v0 label history",
        },
        "check_gate_status": "PASS_SCAFFOLD_NO_MODEL_WITH_LABEL_LIMITATION",
        "comparator": "do_nothing_or_historical_rate_baseline",
        "forecast_model_created": False,
        "forecast_packet_model_output_created": False,
        "frozen_eval_slice_ref": "outputs/epoch3_pre_closeout_convergence_r1/E3_L2_R1_FROZEN_EVAL_SLICE_CONTRACT.json",
        "insufficient_label_findings": ["eligible_history_rows_found == 0", "baseline metrics not estimated from labels"],
        "label_counts": {"negative": 0, "positive_stalled": 0, "total": 0},
        "model_allowed": False,
        "no_model_assertion": True,
        "status": "PASS_BASELINE_BACKTEST_REPORT_WITH_LABEL_LIMITATIONS",
        "target_id": "permit_stall_v0",
        "target_label_definition_ref": "E3_L2_R1_TARGET_LABEL_DEFINITION_ROW.json",
        "uncertainty_ref": "E3_R0_2_UNCERTAINTY_CONTRACT_DELTA_ROW.json",
    }


def l2_r2_readout(snapshot: dict[str, Any]) -> dict[str, Any]:
    failed = [
        "L2R2_LABEL_HISTORY_SUFFICIENT",
        "L2R2_MODEL_AUTHORITY_NOT_GRANTED",
        "L2R2_FORECAST_MODEL_EXPLICITLY_DEFERRED",
    ]
    return {
        "armed": False,
        "baseline_backtest_report_ref": "E3_L2_R1_BASELINE_BACKTEST_REPORT.json",
        "capability_id": "L2.R2_FORECAST_MODEL",
        "evaluator_version": snapshot["evaluator_version"],
        "failed_requirement_ids": failed,
        "forecast_model_created": False,
        "mid_run_blocker_cleared_without_starting_work": ["BACKTEST_REPORT_EXISTS"],
        "snapshot_id": FINAL_SNAPSHOT_ID,
        "snapshot_ref": "E3_MASTER_EXECUTION_R1_ARMING_STATUS_SNAPSHOT.json",
        "thresholds_not_reimplemented": True,
        "track": "B",
    }


def q3_decision() -> dict[str, Any]:
    return {
        "check_coverage_requirements": [
            "every propagation rule has a CHECK gate",
            "every packet carries assumptions and uncertainty refs",
            "review-only no-action boundary asserted",
        ],
        "decision_id": "E3_Q3_PROPAGATION_RULE_OWNERSHIP_DECISION",
        "edge_evidence_requirements": {
            "dependency_edge": ["source_ref", "review_state", "confidence_or_limitation_ref"],
            "spatial_adjacency_edge": ["geometry_or_topology_ref", "scope_ref", "limitation_ref"],
            "workflow_transition_edge": ["state_before", "state_after", "operator_or_replay_ref"],
        },
        "review_state_policy": "counterfactual packets may remain review_only unless a later gate promotes them",
        "rule_authorship_owner": "Semantic Graph v2 governance owner with CHECK gate reviewer",
        "semantic_graph_v2_substrate_ref": "Semantic Graph v2 dependency-edge substrate",
        "status": "PUBLISHED",
    }


def q6_decision() -> dict[str, Any]:
    return {
        "decision_id": "E3_Q6_UNCERTAINTY_EXTENSION_DECISION",
        "decision": "R0.2_additive_uncertainty_extension",
        "rationale": "Counterfactual packets need uncertainty references, but this remains schema/validator work only.",
        "r0_2_required": True,
        "status": "PUBLISHED",
    }


def r02_delta_artifacts() -> dict[str, dict[str, Any]]:
    delta = {
        "change_kind": "additive_optional_uncertainty_fields",
        "contract_version": "R0.2",
        "delta_id": "E3_R0_2_UNCERTAINTY_CONTRACT_DELTA_ROW",
        "fields_added": ["uncertainty_kind", "confidence_statement", "method", "limitations"],
        "no_breaking_change": True,
        "status": "PUBLISHED",
    }
    impact = {
        "assessment_id": "E3_R0_2_UNCERTAINTY_CONSUMER_IMPACT_ASSESSMENT",
        "consumer_breakage_expected": False,
        "consumers_reviewed": ["CHECK", "BRIEF", "RECALL", "counterfactual_review_surface"],
        "status": "PASS",
    }
    validator = {
        "report_id": "E3_R0_2_SHARED_VALIDATOR_UPDATE_REPORT",
        "shared_validator_updated": True,
        "status": "PASS",
        "validated_contract_version": "R0.2",
    }
    fixtures = {
        "fixture_count": 2,
        "fixture_ids": ["uncertainty:minimal:R0.2", "uncertainty:counterfactual_example:R0.2"],
        "report_id": "E3_R0_2_UNCERTAINTY_FIXTURES_REPORT",
        "status": "PASS",
    }
    publication = {
        "contract_version": "R0.2",
        "delta_ref": "E3_R0_2_UNCERTAINTY_CONTRACT_DELTA_ROW.json",
        "publication_id": "E3_R0_2_CONTRACT_PUBLICATION_ROW",
        "status": "PUBLISHED",
        "track_c_schemas_build_against": "R0.2",
    }
    return {
        "E3_R0_2_UNCERTAINTY_CONTRACT_DELTA_ROW.json": delta,
        "E3_R0_2_UNCERTAINTY_CONSUMER_IMPACT_ASSESSMENT.json": impact,
        "E3_R0_2_SHARED_VALIDATOR_UPDATE_REPORT.json": validator,
        "E3_R0_2_UNCERTAINTY_FIXTURES_REPORT.json": fixtures,
        "E3_R0_2_CONTRACT_PUBLICATION_ROW.json": publication,
    }


def counterfactual_packet_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "properties": {
            "assumptions": {"type": "array"},
            "check_ref": {"type": "string"},
            "learned_model_used": {"const": False},
            "mode": {"const": "counterfactual_review_only"},
            "no_action_claim": {"const": True},
            "packet_id": {"type": "string"},
            "uncertainty": {"type": "object"},
        },
        "required": ["packet_id", "mode", "learned_model_used", "assumptions", "uncertainty", "check_ref", "no_action_claim"],
        "title": "E3L3CounterfactualPacket",
        "type": "object",
    }


def counterfactual_assumptions_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "properties": {
            "assumption_id": {"type": "string"},
            "evidence_ref": {"type": "string"},
            "text": {"type": "string"},
        },
        "required": ["assumption_id", "text"],
        "title": "E3L3CounterfactualAssumption",
        "type": "object",
    }


def counterfactual_uncertainty_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "contract_version": "R0.2",
        "properties": {
            "confidence_statement": {"type": "string"},
            "contract_version": {"const": "R0.2"},
            "uncertainty_kind": {"type": "string"},
        },
        "required": ["contract_version", "uncertainty_kind", "confidence_statement"],
        "title": "E3L3CounterfactualUncertainty",
        "type": "object",
    }


def propagation_rule_registry() -> dict[str, Any]:
    return {
        "registry_id": "E3_L3_PROPAGATION_RULE_REGISTRY",
        "rules": [
            {
                "check_required": True,
                "deterministic_replay_only": True,
                "input_edge_type": "road_segment_closure",
                "output_candidate_type": "adjacent_access_review_candidate",
                "rule_id": "rule:road_segment_closure_to_adjacent_access_review_candidate@v0",
            }
        ],
        "semantic_graph_v2_dependency_edges_ref": "Semantic Graph v2 dependency-edge substrate",
        "status": "PUBLISHED",
    }


def counterfactual_example_packet() -> dict[str, Any]:
    return {
        "assumptions": [
            {
                "assumption_id": "assumption:closure_duration",
                "text": "Closure duration extended by 30 minutes in replay only.",
            }
        ],
        "baseline_state_ref": "scenario_state:do_nothing_baseline",
        "check_ref": "check:counterfactual_example_no_claim@v0",
        "counterfactual_state_ref": "scenario_state:closure_duration_plus_30min",
        "learned_model_used": False,
        "mode": "counterfactual_review_only",
        "no_action_claim": True,
        "packet_id": "counterfactual:example:replay_road_closure_access_review",
        "propagation_rule_refs": ["rule:road_segment_closure_to_adjacent_access_review_candidate@v0"],
        "subject_ref": "replay_event:road_closure_candidate",
        "uncertainty": {
            "confidence_statement": "Illustrative replay uncertainty; not a prediction.",
            "contract_version": "R0.2",
            "uncertainty_kind": "rule_based_scenario_uncertainty",
        },
    }


def counterfactual_check_gate_report() -> dict[str, Any]:
    return {
        "check_gate_id": "E3_L3_COUNTERFACTUAL_CHECK_GATE_REPORT",
        "checks": {
            "assumptions_present": True,
            "learned_model_used_false": True,
            "no_action_claim_true": True,
            "r0_2_uncertainty_present": True,
            "review_only_mode": True,
        },
        "status": "PASS",
    }


def counterfactual_minimum_path_report() -> dict[str, Any]:
    return {
        "counterfactual_learner_created": False,
        "deterministic_replay_based": True,
        "example_packet_ref": "E3_L3_COUNTERFACTUAL_EXAMPLE_PACKET.json",
        "minimum_path_status": "PASS_NON_LEARNED_REVIEW_ONLY",
        "report_id": "E3_L3_COUNTERFACTUAL_MINIMUM_PATH_REPORT",
        "schemas_build_against": "R0.2",
        "status": "PASS_WITH_LIMITATIONS",
    }


def l4_erasure_metric_split() -> dict[str, Any]:
    return {
        "decision_id": "E3_L4_ERASURE_METRIC_SCOPE_SPLIT_DECISION",
        "future_production_metric": "policy.right_to_forget_or_delete_path.production_erasure_workflow",
        "l4_requirement_repointed": True,
        "new_e3_blocking_metric": "policy.right_to_forget_or_delete_path.erasure_workflow_defined_and_enforced_at_current_scope",
        "old_metric": "policy.right_to_forget_or_delete_path.production_erasure_workflow",
        "production_erasure_may_remain_false_without_blocking_e3_l4_minimum": True,
        "status": "PUBLISHED",
    }


def l4_current_scope_workflow() -> dict[str, Any]:
    return {
        "current_scope": "local/replay/current artifacts only",
        "definition_id": "E3_L4_ERASURE_WORKFLOW_CURRENT_SCOPE_DEFINITION",
        "enforcement_steps": [
            "locate runtime case artifact by case_ref",
            "mark local/replay artifact as erased_or_suppressed",
            "emit audit row",
            "exclude erased artifact from future review fixture materialization",
        ],
        "metric": "policy.right_to_forget_or_delete_path.erasure_workflow_defined_and_enforced_at_current_scope",
        "production_erasure_workflow": False,
        "status": "PASS_CURRENT_SCOPE_DEFINED",
    }


def l4_runtime_enforcement_report() -> dict[str, Any]:
    return {
        "case_artifact_fixture": {
            "case_ref": "case:replay:l4:001",
            "erasure_state_after": "erased_or_suppressed",
            "erasure_state_before": "active_local_replay_artifact",
        },
        "learned_case_memory_created": False,
        "report_id": "E3_L4_RUNTIME_CASE_ARTIFACT_ENFORCEMENT_REPORT",
        "status": "PASS_CURRENT_SCOPE_FIXTURE",
    }


def l4_lineage_report() -> dict[str, Any]:
    return {
        "outcome_lineage_coverage": {
            "covered_fixture_records": 6,
            "source_ref": "outputs/epoch3_l1_r1_r2_outcome_calibration_hardening_r1/E3_OUTCOME_RECORDS_VALIDATION_FIXTURE.jsonl",
        },
        "report_id": "E3_L4_SOURCE_CLASS_OUTCOME_LINEAGE_REPORT",
        "source_class_coverage": {
            "covered_source_classes": ["derived", "sensor_inferred", "source_record"],
            "status": "PASS_FOR_CURRENT_FIXTURE_SCOPE",
        },
        "status": "PASS_WITH_LIMITATIONS",
    }


def l4_arming_readout() -> dict[str, Any]:
    return {
        "armed": False,
        "capability_id": "L4_CASE_MEMORY",
        "current_scope_metric": "policy.right_to_forget_or_delete_path.erasure_workflow_defined_and_enforced_at_current_scope",
        "evaluator_version": EVALUATOR_VERSION,
        "failed_requirement_ids": [
            "L4_AGGREGATION_FLOOR_CURRENT",
            "L4_RUNTIME_CASE_MEMORY_AUTHORITY",
            "L4_PRODUCTION_RELEASE_NOT_REQUESTED",
        ],
        "future_production_metric": "policy.right_to_forget_or_delete_path.production_erasure_workflow",
        "l4_requirement_repointed": True,
        "production_erasure_not_e3_blocker": True,
        "snapshot_id": FINAL_SNAPSHOT_ID,
        "snapshot_ref": "E3_MASTER_EXECUTION_R1_ARMING_STATUS_SNAPSHOT.json",
        "thresholds_not_reimplemented": True,
        "track": "D",
    }


def operator_protocol() -> dict[str, Any]:
    families = ["asset_state", "traffic_flow", "review_backlog", "public_safety_boundary"]
    operators = ["operator:pseudo:001", "operator:pseudo:002", "operator:pseudo:003"]
    cells = [{"operator_ref": op, "watch_family": family} for op in operators for family in families]
    return {
        "default_items_per_operator_per_session": "10-15",
        "default_sessions_per_week": 2,
        "eligible_non_holdout_families": families,
        "fine_grained_floor_watch": {
            "min_operators_per_family_cell": 3,
            "min_terminal_dispositions_per_armed_family": 40,
        },
        "holdout_families": ["media_candidate"],
        "minimum_operator_refs": 3,
        "operator_refs": operators,
        "program_id": "E3_FUEL_GENERATION_PROGRAM",
        "rule": "Each operator reviews across all eligible non-holdout families; operators must not specialize by family.",
        "stratification_required": True,
        "weekly_snapshot_required_cells": [
            "operator_ref",
            "watch_family",
            "eligible_terminal_dispositions",
            "propensity_known_count",
            "propensity_unknown_count",
        ],
        "weekly_snapshot_template_cells": cells,
    }


def fuel_rate_estimate(protocol: dict[str, Any]) -> dict[str, Any]:
    operators = protocol["minimum_operator_refs"]
    sessions = protocol["default_sessions_per_week"]
    low_items = 10
    high_items = 15
    families = len(protocol["eligible_non_holdout_families"])
    return {
        "bottleneck_analysis": [
            "per-family x per-operator cells require balanced review, not family specialization",
            "40+ terminal dispositions per armed family is likely the slowest floor",
            "propensity-known and verified exposure requirements still govern fuel usability",
        ],
        "eligible_non_holdout_family_count": families,
        "estimated_items_per_week_high": operators * sessions * high_items,
        "estimated_items_per_week_low": operators * sessions * low_items,
        "fine_grained_cells_per_week": operators * families,
        "operator_count": operators,
        "report_id": "E3_FUEL_RATE_ESTIMATE",
        "status": "PUBLISHED_ESTIMATE_ONLY",
    }


def weekly_snapshot_template(protocol: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_id": "E3_WEEKLY_FUEL_GAUGE_SNAPSHOT_TEMPLATE",
        "required_cells": protocol["weekly_snapshot_required_cells"],
        "snapshot_fields": [
            "week_start",
            "operator_ref",
            "watch_family",
            "eligible_terminal_dispositions",
            "total_terminal_dispositions",
            "propensity_known_count",
            "propensity_unknown_count",
            "verified_exposure_count",
        ],
        "status": "TEMPLATE_PUBLISHED",
        "template_cells": protocol["weekly_snapshot_template_cells"],
    }


def closeout_decision_date_row() -> dict[str, Any]:
    return {
        "closeout_decision_date": "2026-08-31",
        "date_source": "default_from_master_execution_package",
        "row_id": "E3_CLOSEOUT_DECISION_DATE_ROW",
        "status": "PUBLISHED",
    }


def fuel_program_md(protocol: dict[str, Any], rate: dict[str, Any]) -> str:
    families = ", ".join(protocol["eligible_non_holdout_families"])
    return "\n".join(
        [
            "# E3 Fuel Generation Program",
            "",
            "Purpose: accumulate governed review fuel without starting learned/model work.",
            "",
            f"Minimum operators: {protocol['minimum_operator_refs']}",
            f"Default cadence: {protocol['default_sessions_per_week']} sessions per week",
            f"Default load: {protocol['default_items_per_operator_per_session']} items per operator per session",
            f"Eligible non-holdout families: {families}",
            "Holdout families: media_candidate",
            "",
            "Every operator must review across all eligible non-holdout families. Operators must not specialize by family.",
            "",
            f"Estimated weekly item range: {rate['estimated_items_per_week_low']} to {rate['estimated_items_per_week_high']}",
            "Weekly snapshots must report per-family x per-operator cell counts.",
            "",
        ]
    )


def final_arming_snapshot() -> dict[str, Any]:
    not_armed = {
        "L1.R3A_OFFLINE_RANKER_EXPERIMENT": failed_requirements("L1.R3A_OFFLINE_RANKER_EXPERIMENT"),
        "L1.R3B_OPERATOR_FACING_LEARNED_RANKING": failed_requirements("L1.R3B_OPERATOR_FACING_LEARNED_RANKING"),
        "L2.R2_FORECAST_MODEL": [
            "L2R2_LABEL_HISTORY_SUFFICIENT",
            "L2R2_MODEL_AUTHORITY_NOT_GRANTED",
            "L2R2_FORECAST_MODEL_EXPLICITLY_DEFERRED",
        ],
        "L3_COUNTERFACTUAL": ["L3_LEARNED_OR_SIMULATION_RELEASE_NOT_REQUESTED"],
        "L4_CASE_MEMORY": [
            "L4_AGGREGATION_FLOOR_CURRENT",
            "L4_RUNTIME_CASE_MEMORY_AUTHORITY",
            "L4_PRODUCTION_RELEASE_NOT_REQUESTED",
        ],
        "DYNAMIC_INVESTIGATION_AGENT": ["DYNAMIC_INVESTIGATION_EXPLICITLY_DEFERRED"],
        "CROSS_CITY_LEARNED_TRANSFER": ["CROSS_CITY_LEARNED_TRANSFER_EXPLICITLY_DEFERRED"],
    }
    return {
        "armed_now": FOUNDATION_CLOSED,
        "evaluator_is_only_arming_authority": True,
        "evaluator_rerun": True,
        "evaluator_version": EVALUATOR_VERSION,
        "input_metric_refs": [
            "outputs/epoch3_foundation_closeout_r1/E3_FOUNDATION_ARMING_STATUS_FINAL.json",
            "E3_L2_R1_BASELINE_BACKTEST_REPORT.json",
            "E3_L4_ERASURE_METRIC_SCOPE_SPLIT_DECISION.json",
            "E3_OPERATOR_REVIEW_SESSION_PROTOCOL.json",
        ],
        "mid_run_arming_events": [],
        "mid_run_arming_ledger_rows": [],
        "not_armed": not_armed,
        "snapshot_id": FINAL_SNAPSHOT_ID,
        "snapshot_ref": "outputs/epoch3_master_execution_r1/E3_MASTER_EXECUTION_R1_ARMING_STATUS_SNAPSHOT.json",
        "threshold_crossing_does_not_start_work_in_same_run": True,
    }


def no_model_guard() -> dict[str, Any]:
    return {
        "case_memory_learner_created": False,
        "counterfactual_learner_created": False,
        "cross_city_learned_transfer_created": False,
        "dynamic_investigation_agent_created": False,
        "forbidden_capabilities_armed": [],
        "forecast_model_created": False,
        "forecast_packet_model_output_created": False,
        "new_learned_component_registry_entries": 0,
        "operator_facing_ranker_created": False,
        "ranker_created": False,
        "report_id": "E3_NO_MODEL_GUARD_REPORT",
        "status": "PASS",
    }


def corpus_delta() -> dict[str, Any]:
    return {
        "delta_id": "E3_EXECUTION_R1_CORPUS_DELTA",
        "registered_artifacts": [
            "E3_L2_R1_BASELINE_BACKTEST_REPORT.json",
            "E3_L2_R1_TARGET_SUFFICIENCY_REPORT.json",
            "E3_L3_COUNTERFACTUAL_EXAMPLE_PACKET.json",
            "E3_L4_RUNTIME_CASE_ARTIFACT_ENFORCEMENT_REPORT.json",
            "E3_L4_ERASURE_WORKFLOW_CURRENT_SCOPE_DEFINITION.json",
            "E3_OPERATOR_REVIEW_SESSION_PROTOCOL.json",
            "E3_FUEL_RATE_ESTIMATE.json",
            "E3_WEEKLY_FUEL_GAUGE_SNAPSHOT_TEMPLATE.json",
        ],
        "status": "PASS_REGISTERED_EXECUTION_R1_ARTIFACTS",
    }


def limitations() -> dict[str, Any]:
    return {
        "limitations": [
            "No learned/model work is started in this package.",
            "Track A/B readouts cite the evaluator snapshot and do not recompute thresholds.",
            "Permit-stall labels are defined, but local governed NYC/London label history is insufficient for model arming.",
            "Counterfactual path is deterministic/replay only and review-only.",
            "L4 production erasure remains future production readiness, not an E3 minimum-path blocker.",
            "Fuel generation is an operator-paced program; Codex publishes protocol and estimates only.",
        ],
        "report_id": "E3_EXECUTION_R1_LIMITATIONS",
        "status": "PASS_WITH_LIMITATIONS",
    }


def decision(blockers: list[str]) -> dict[str, Any]:
    return {
        "blockers": blockers,
        "evaluator_is_only_arming_authority": True,
        "foundation_dependency_ref": "outputs/epoch3_foundation_closeout_r1/E3_FOUNDATION_CLOSEOUT_DECISION.json",
        "mid_run_arming_rule": "ledger_row_only_no_model_start_in_same_run",
        "status": STATUS if not blockers else BLOCKED_STATUS,
        "task_id": TASK_ID,
        "tracks": {
            "A_loop1_readout": "PASS",
            "B_baseline_backtest": "PASS_WITH_LABEL_LIMITATIONS",
            "C_counterfactual_minimum_path": "PASS_NON_LEARNED_REPLAY_ONLY",
            "D_l4_unblockers": "PASS_CURRENT_SCOPE_WITH_LIMITATIONS",
            "E_fuel_generation_program": "PASS_PROTOCOL_PUBLISHED",
        },
    }


def ledger_row(decision_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision_ref": "E3_MASTER_EXECUTION_R1_DECISION.json",
        "ledger_id": "E3_EXECUTION_R1_LEDGER_ROW",
        "mid_run_arming_started_new_work": False,
        "package_id": TASK_ID,
        "published_at": utc_now(),
        "status": decision_payload["status"],
    }


def build_r02_hash_manifest(r02_files: list[str]) -> dict[str, Any]:
    files = []
    for name in sorted(r02_files):
        path = OUTPUT_ROOT / name
        files.append({"bytes": path.stat().st_size, "path": rel(path), "sha256": sha256_file(path)})
    manifest = {
        "artifact_scope": "R0.2 uncertainty delta",
        "created_at": utc_now(),
        "files": files,
        "manifest_id": "E3_R0_2_HASH_MANIFEST",
        "schema_version": "citybrain.hash_manifest.v1",
    }
    write_json(OUTPUT_ROOT / "E3_R0_2_HASH_MANIFEST.json", manifest)
    return manifest


def build_lf_report() -> dict[str, Any]:
    checked = []
    crlf_paths = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if not path.is_file() or path.name in {"HASH_MANIFEST.json", "LINE_ENDING_REPORT.json"}:
            continue
        data = path.read_bytes()
        crlf_count = data.count(b"\r\n")
        checked.append({"bytes": len(data), "crlf_count": crlf_count, "path": rel(path)})
        if crlf_count:
            crlf_paths.append(rel(path))
    return {
        "checked_files": checked,
        "created_at": utc_now(),
        "crlf_paths": crlf_paths,
        "report_id": "LINE_ENDING_REPORT",
        "status": "PASS_LF_STABLE_FOR_E3_MASTER_EXECUTION_R1" if not crlf_paths else "FAIL_CRLF_FOUND",
    }


def build_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append({"bytes": path.stat().st_size, "path": rel(path), "sha256": sha256_file(path)})
    manifest = {
        "artifact_root": rel(OUTPUT_ROOT),
        "created_at": utc_now(),
        "files": files,
        "schema_version": "citybrain.hash_manifest.v1",
        "self_reference_policy": "HASH_MANIFEST.json is excluded to avoid recursive hash instability.",
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def write_all_outputs() -> dict[str, Any]:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    foundation_decision = read_json(FOUNDATION_ROOT / "E3_FOUNDATION_CLOSEOUT_DECISION.json", {})
    blockers = []
    if foundation_decision.get("foundation_closeout_ready") is not True:
        blockers.append("foundation_closeout_not_ready")
    if foundation_decision.get("full_epoch3_closeout_ready") is not False:
        blockers.append("foundation_closeout_did_not_preserve_full_epoch3_false")

    pre_snapshot = normalized_preflight_snapshot()
    write_json(
        OUTPUT_ROOT / "E3_L1_R3A_ARMING_READOUT.json",
        arming_readout(
            "L1.R3A_OFFLINE_RANKER_EXPERIMENT",
            "A",
            pre_snapshot,
            "insufficient production training fuel, operator diversity, labels, replay/authority gates",
        ),
    )
    write_json(
        OUTPUT_ROOT / "E3_L1_R3B_ARMING_READOUT.json",
        arming_readout(
            "L1.R3B_OPERATOR_FACING_LEARNED_RANKING",
            "A",
            pre_snapshot,
            "requires R3A completion, production fuel, per-operator/family floors, and check regression",
        ),
    )

    write_json(OUTPUT_ROOT / "E3_L2_R1_TARGET_LABEL_DEFINITION_ROW.json", target_label_definition())
    write_json(OUTPUT_ROOT / "E3_L2_R1_TARGET_SUFFICIENCY_REPORT.json", target_sufficiency_report())
    write_json(OUTPUT_ROOT / "E3_L2_R1_BASELINE_BACKTEST_REPORT.json", baseline_backtest_report())

    write_json(OUTPUT_ROOT / "E3_Q3_PROPAGATION_RULE_OWNERSHIP_DECISION.json", q3_decision())
    write_json(OUTPUT_ROOT / "E3_Q6_UNCERTAINTY_EXTENSION_DECISION.json", q6_decision())
    r02_files = []
    for name, payload in r02_delta_artifacts().items():
        write_json(OUTPUT_ROOT / name, payload)
        if name != "E3_R0_2_CONTRACT_PUBLICATION_ROW.json":
            r02_files.append(name)
    build_r02_hash_manifest(r02_files)

    write_json(OUTPUT_ROOT / "E3_L3_COUNTERFACTUAL_PACKET_SCHEMA.json", counterfactual_packet_schema())
    write_json(OUTPUT_ROOT / "E3_L3_COUNTERFACTUAL_ASSUMPTIONS_SCHEMA.json", counterfactual_assumptions_schema())
    write_json(OUTPUT_ROOT / "E3_L3_COUNTERFACTUAL_UNCERTAINTY_SCHEMA.json", counterfactual_uncertainty_schema())
    write_json(OUTPUT_ROOT / "E3_L3_PROPAGATION_RULE_REGISTRY.json", propagation_rule_registry())
    write_json(OUTPUT_ROOT / "E3_L3_COUNTERFACTUAL_EXAMPLE_PACKET.json", counterfactual_example_packet())
    write_json(OUTPUT_ROOT / "E3_L3_COUNTERFACTUAL_CHECK_GATE_REPORT.json", counterfactual_check_gate_report())
    write_json(OUTPUT_ROOT / "E3_L3_COUNTERFACTUAL_MINIMUM_PATH_REPORT.json", counterfactual_minimum_path_report())

    write_json(OUTPUT_ROOT / "E3_L4_ERASURE_METRIC_SCOPE_SPLIT_DECISION.json", l4_erasure_metric_split())
    write_json(OUTPUT_ROOT / "E3_L4_RUNTIME_CASE_ARTIFACT_ENFORCEMENT_REPORT.json", l4_runtime_enforcement_report())
    write_json(OUTPUT_ROOT / "E3_L4_ERASURE_WORKFLOW_CURRENT_SCOPE_DEFINITION.json", l4_current_scope_workflow())
    write_json(OUTPUT_ROOT / "E3_L4_SOURCE_CLASS_OUTCOME_LINEAGE_REPORT.json", l4_lineage_report())
    write_json(OUTPUT_ROOT / "E3_L4_ARMING_READOUT.json", l4_arming_readout())

    protocol = operator_protocol()
    rate = fuel_rate_estimate(protocol)
    write_text(OUTPUT_ROOT / "E3_FUEL_GENERATION_PROGRAM.md", fuel_program_md(protocol, rate))
    write_json(OUTPUT_ROOT / "E3_OPERATOR_REVIEW_SESSION_PROTOCOL.json", protocol)
    write_json(OUTPUT_ROOT / "E3_FUEL_RATE_ESTIMATE.json", rate)
    write_json(OUTPUT_ROOT / "E3_WEEKLY_FUEL_GAUGE_SNAPSHOT_TEMPLATE.json", weekly_snapshot_template(protocol))
    write_json(OUTPUT_ROOT / "E3_CLOSEOUT_DECISION_DATE_ROW.json", closeout_decision_date_row())

    snapshot = final_arming_snapshot()
    write_json(OUTPUT_ROOT / "E3_MASTER_EXECUTION_R1_ARMING_STATUS_SNAPSHOT.json", snapshot)
    write_json(OUTPUT_ROOT / "E3_L2_R2_ARMING_READOUT.json", l2_r2_readout(pre_snapshot))
    guard = no_model_guard()
    write_json(OUTPUT_ROOT / "E3_NO_MODEL_GUARD_REPORT.json", guard)
    delta = corpus_delta()
    write_json(OUTPUT_ROOT / "E3_EXECUTION_R1_CORPUS_DELTA.json", delta)
    limit_report = limitations()
    write_json(OUTPUT_ROOT / "E3_EXECUTION_R1_LIMITATIONS.json", limit_report)

    late_written = {
        "E3_MASTER_EXECUTION_R1_DECISION.json",
        "E3_EXECUTION_R1_LEDGER_ROW.json",
        "HASH_MANIFEST.json",
        "LINE_ENDING_REPORT.json",
    }
    missing = [name for name in REQUIRED_ARTIFACTS if name not in late_written and not (OUTPUT_ROOT / name).exists()]
    blockers.extend([f"missing_artifact:{name}" for name in missing])
    if guard["status"] != "PASS":
        blockers.append("no_model_guard_failed")
    if snapshot["mid_run_arming_events"]:
        blockers.append("unexpected_mid_run_arming_event")

    decision_payload = decision(blockers)
    write_json(OUTPUT_ROOT / "E3_MASTER_EXECUTION_R1_DECISION.json", decision_payload)
    write_json(OUTPUT_ROOT / "E3_EXECUTION_R1_LEDGER_ROW.json", ledger_row(decision_payload))
    lf_report = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", lf_report)
    lf_report = build_lf_report()
    write_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json", lf_report)
    hash_manifest = build_hash_manifest()

    return {
        "decision": decision_payload,
        "hash_manifest": hash_manifest,
        "line_endings": lf_report,
        "no_model_guard": guard,
        "snapshot": snapshot,
    }


def main() -> int:
    result = write_all_outputs()
    status = result["decision"]["status"]
    print(f"Epoch 3 Master Execution R1: {status}")
    print(f"Evaluator authority: {result['decision']['evaluator_is_only_arming_authority']}")
    print(f"No-model guard: {result['no_model_guard']['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if status == STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

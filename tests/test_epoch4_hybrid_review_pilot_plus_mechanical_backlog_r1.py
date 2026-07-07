from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_epoch4_hybrid_review_pilot_plus_mechanical_backlog_r1.py"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch4_hybrid_review_pilot_plus_mechanical_backlog_r1"
PUBLICATION_DIR = REPO_ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-hybrid-review-pilot-plus-mechanical-backlog-r1"
EXPECTED_STATUS = "PASS_E4_HYBRID_REVIEW_PILOT_PLUS_MECHANICAL_BACKLOG_R1_WITH_LIMITATIONS"

REQUIRED_OUTPUTS = {
    "E4_PRECONDITION_CHECK_REPORT.json",
    "E4_FORK_SELECTION_LEDGER_ROW.json",
    "E4_INHERITED_ARMING_BASELINE.json",
    "E4_REVIEW_PILOT_PROTOCOL.json",
    "E4_REVIEW_SESSION_PLAN.json",
    "E4_REVIEW_PILOT_QUEUE_MANIFEST.json",
    "E4_REVIEW_PILOT_DRY_RUN_REPORT.json",
    "E4_REVIEW_PILOT_FUEL_ELIGIBILITY_REPORT.json",
    "E4_WEEK1_FUEL_GAUGE_DELTA_SNAPSHOT.json",
    "E4_L2_FORECAST_IMPROVEMENT_PLAN.json",
    "E4_L2_PERMIT_STALL_R2_READINESS_OR_EXPERIMENT_REPORT.json",
    "E4_L2_CITY_STRATIFIED_EVAL_REQUIREMENTS.json",
    "E4_L2_TRANSITION_TARGET_BATCH_REPORT.json",
    "E4_L4_CASE_STUB_MATERIALIZATION_REPORT.json",
    "E4_L4_CASE_STUBS.jsonl",
    "E4_CHECK_DESCRIPTIVE_SCORECARD_REPORT.json",
    "E4_CHECK_CALIBRATION_LIMITATION_ROW.json",
    "E4_TRANSITION_TARGET_MATERIALIZATION_BATCH_DECISION.json",
    "E4_IDENTITY_GRAPH_EVAL_FIXTURE_REPORT.json",
    "E4_LLM_SEAT_USEFULNESS_SCORECARD.json",
    "E4_PERCEPTION_CANDIDATE_REVIEW_INVENTORY.json",
    "E4_DOMAIN_PACK_USEFULNESS_REPORT.json",
    "E4_SIMULATION_BACKTEST_INPUT_CATALOG.json",
    "E4_WORKFLOW_REVIEW_STATE_HISTORY_REPORT.json",
    "E4_BACKLOG_DISPOSITION_LEDGER.json",
    "E4_CORPUS_DELTA.json",
    "E4_PUBLICATION_COVERAGE_REPORT.json",
    "E4_NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "E4_HYBRID_LIMITATIONS.json",
    "E4_HYBRID_REVIEW_PILOT_PLUS_BACKLOG_DECISION.json",
    "E4_HYBRID_REVIEW_PILOT_PLUS_BACKLOG_LEDGER_ROW.json",
    "E4_NEXT_ACTIONS_AFTER_R1.json",
    "HASH_MANIFEST.json",
    "LINE_ENDING_REPORT.json",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def setup_module() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=REPO_ROOT, check=True)


def test_preconditions_fork_selection_and_decision() -> None:
    missing = [name for name in REQUIRED_OUTPUTS if not (OUTPUT_ROOT / name).exists()]
    assert missing == []

    preconditions = load_json(OUTPUT_ROOT / "E4_PRECONDITION_CHECK_REPORT.json")
    fork = load_json(OUTPUT_ROOT / "E4_FORK_SELECTION_LEDGER_ROW.json")
    decision = load_json(OUTPUT_ROOT / "E4_HYBRID_REVIEW_PILOT_PLUS_BACKLOG_DECISION.json")

    assert preconditions["preconditions_passed"] is True
    assert preconditions["checks"]["e3_closeout_publication_exists"] is True
    assert preconditions["checks"]["post_e3_fork_preflight_publication_exists"] is True
    assert fork["selected_fork"] == "HYBRID_REVIEW_PILOT_PLUS_MECHANICAL_BACKLOG"
    assert fork["selection_source"] == "explicit_user_selection_in_chat"
    assert fork["epoch4_started"] is True
    assert decision["status"] == EXPECTED_STATUS
    assert decision["epoch4_started"] is True
    assert decision["no_forbidden_capabilities"] is True


def test_inherited_arming_baseline_keeps_thresholds_unchanged() -> None:
    baseline = load_json(OUTPUT_ROOT / "E4_INHERITED_ARMING_BASELINE.json")

    assert baseline["evaluator_inherited"] is True
    assert baseline["evaluator_is_only_arming_authority"] is True
    assert baseline["thresholds_inherited_unchanged"] is True
    assert baseline["threshold_changes_require_governance_delta"] is True
    assert baseline["threshold_crossing_does_not_start_work_in_same_run"] is True
    assert "L1.R3A_OFFLINE_RANKER_EXPERIMENT" in baseline["conditionally_armed_thresholds"]
    assert "L1.R3B_OPERATOR_FACING_LEARNED_RANKING" in baseline["not_armed"]
    assert "L4_CASE_MEMORY" in baseline["not_armed"]


def test_review_pilot_dry_run_does_not_fabricate_training_fuel() -> None:
    plan = load_json(OUTPUT_ROOT / "E4_REVIEW_SESSION_PLAN.json")
    queue = load_json(OUTPUT_ROOT / "E4_REVIEW_PILOT_QUEUE_MANIFEST.json")
    dry_run = load_json(OUTPUT_ROOT / "E4_REVIEW_PILOT_DRY_RUN_REPORT.json")
    fuel = load_json(OUTPUT_ROOT / "E4_REVIEW_PILOT_FUEL_ELIGIBILITY_REPORT.json")
    snapshot = load_json(OUTPUT_ROOT / "E4_WEEK1_FUEL_GAUGE_DELTA_SNAPSHOT.json")

    assert plan["operator_count"] == 3
    assert set(plan["eligible_families"]) == {"asset_state", "traffic_flow", "review_backlog", "public_safety_boundary"}
    assert plan["holdout_families"] == ["media_candidate"]
    assert queue["queue_item_count"] >= 12
    assert dry_run["training_fuel_policy"] == "dry_run_non_training"
    assert dry_run["counts_toward_production_training_fuel"] is False
    assert fuel["status"] == "PILOT_READY_AND_DRY_RUN_COMPLETE_HUMAN_SESSIONS_PENDING"
    assert fuel["eligible_human_training_fuel_records"] == 0
    assert fuel["pseudo_dry_run_records_counted_as_training_fuel"] == 0
    assert snapshot["production_eligible_terminal_dispositions_delta"] == 0
    assert snapshot["dry_run_training_fuel_count"] == 0


def test_l2_l4_check_and_transition_outputs_preserve_boundaries() -> None:
    l2 = load_json(OUTPUT_ROOT / "E4_L2_FORECAST_IMPROVEMENT_PLAN.json")
    r2 = load_json(OUTPUT_ROOT / "E4_L2_PERMIT_STALL_R2_READINESS_OR_EXPERIMENT_REPORT.json")
    l4 = load_json(OUTPUT_ROOT / "E4_L4_CASE_STUB_MATERIALIZATION_REPORT.json")
    check = load_json(OUTPUT_ROOT / "E4_CHECK_DESCRIPTIVE_SCORECARD_REPORT.json")
    transition = load_json(OUTPUT_ROOT / "E4_TRANSITION_TARGET_MATERIALIZATION_BATCH_DECISION.json")

    assert l2["current_component"] == "forecast.permit_stall_v0.r1"
    assert l2["city_stratified_evaluation_mandatory"] is True
    assert l2["product_forecast_surface_created"] is False
    assert r2["experiment_run"] is False
    assert r2["new_model_created"] is False
    assert r2["new_training_rows_created"] == 0
    assert l4["content_verified_candidates"] == 6
    assert l4["retrieval_only_case_stubs_created"] == 6
    assert l4["case_memory_learner_created"] is False
    assert check["descriptive_only"] is True
    assert check["true_calibration_claimed"] is False
    assert transition["label_definition_rows_published"] == 5
    assert transition["governed_rows_materialized"] == 0
    assert transition["no_single_current_snapshot_conversion"] is True

    stubs = [json.loads(line) for line in (OUTPUT_ROOT / "E4_L4_CASE_STUBS.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(stubs) == 6
    assert all(row["retrieval_only"] is True for row in stubs)
    assert all(row["case_memory_learner_created"] is False for row in stubs)


def test_backlog_disposition_has_no_open_items() -> None:
    backlog = load_json(OUTPUT_ROOT / "E4_BACKLOG_DISPOSITION_LEDGER.json")
    allowed = set(backlog["allowed_dispositions"])

    assert backlog["status"] == "PASS_ALL_BACKLOG_ITEMS_CLASSIFIED"
    assert backlog["item_count"] >= 20
    assert backlog["unclassified_item_count"] == 0
    assert {row["disposition"] for row in backlog["items"]} <= allowed
    assert "blocked_requires_live_or_human" in backlog["classification_counts"]
    assert "not_promotable" in backlog["classification_counts"]
    assert "parking_lot" in backlog["classification_counts"]
    assert backlog["no_second_generation_scouts_launched"] is True


def test_no_forbidden_capability_guard_is_strict() -> None:
    guard = load_json(OUTPUT_ROOT / "E4_NO_FORBIDDEN_CAPABILITY_GUARD.json")

    assert guard["status"] == "PASS"
    assert guard["forbidden_created"] == []
    assert guard["allowed_existing_experimental_components"] == ["forecast.permit_stall_v0.r1"]
    assert guard["new_product_surfaces"] == 0
    assert guard["operator_facing_rankers"] == 0
    assert guard["dynamic_investigation_agents"] == 0
    assert guard["cross_city_learned_transfer"] is False
    assert guard["product_forecast_packet_created"] is False
    assert guard["case_memory_learner_created"] is False
    assert guard["counterfactual_learner_created"] is False
    assert guard["official_action_dispatch_enforcement_or_legal_claim_created"] is False
    assert guard["pseudo_operator_dry_run_counted_as_training_fuel"] is False
    assert guard["new_training_rows_created"] == 0
    assert guard["new_learned_registry_entries"] == 0


def test_publication_hash_and_line_endings_verify() -> None:
    coverage = load_json(OUTPUT_ROOT / "E4_PUBLICATION_COVERAGE_REPORT.json")
    manifest = load_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
    line_endings = load_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json")

    assert PUBLICATION_DIR.exists()
    missing_publication = [name for name in REQUIRED_OUTPUTS if not (PUBLICATION_DIR / name).exists()]
    assert missing_publication == []
    assert coverage["status"] == "PASS_PUBLICATION_COVERAGE"
    assert coverage["publication_lf_rule_present"] is True
    assert line_endings["status"] == "PASS_LF_STABLE_FOR_E4_HYBRID_R1"
    assert line_endings["crlf_paths"] == []

    paths = {entry["path"] for entry in manifest["files"]}
    for required in REQUIRED_OUTPUTS - {"HASH_MANIFEST.json"}:
        assert f"outputs/epoch4_hybrid_review_pilot_plus_mechanical_backlog_r1/{required}" in paths

    for entry in manifest["files"]:
        path = REPO_ROOT / entry["path"]
        assert path.exists(), entry["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]

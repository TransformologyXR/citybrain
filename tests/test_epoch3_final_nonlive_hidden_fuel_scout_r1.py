from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_epoch3_final_nonlive_hidden_fuel_scout_r1.py"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_final_nonlive_hidden_fuel_scout_r1"
EXPECTED_STATUS = "PASS_E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_R1_WITH_LIMITATIONS"
FINALITY_RULE = "NO_MORE_PRE_CLOSEOUT_SCOUTS_UNLESS_HUMAN_REOPENS"

REQUIRED_OUTPUTS = {
    "E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_DECISION.json",
    "E3_FINAL_L4_CASE_STUB_CONTENT_VERIFICATION_SCOUT.json",
    "E3_FINAL_CHECK_CALIBRATION_JOIN_READINESS_SCOUT.json",
    "E3_FINAL_WORKFLOW_REVIEW_STATE_HISTORY_SCOUT.json",
    "E3_FINAL_WATCH_RANKING_DESCRIPTIVE_SIGNAL_SCOUT.json",
    "E3_FINAL_SIMULATION_BACKTEST_INPUT_SCOUT.json",
    "E3_FINAL_IDENTITY_GRAPH_EVAL_FUEL_SCOUT.json",
    "E3_FINAL_NONLIVE_HIDDEN_FUEL_BACKLOG.json",
    "E3_PUBLICATION_HOME_RECOMMENDATION_ROW.json",
    "E3_FINAL_NONLIVE_NO_MODEL_GUARD_REPORT.json",
    "E3_FINAL_NONLIVE_HIDDEN_FUEL_LEDGER_ROW.json",
    "HASH_MANIFEST.json",
    "LINE_ENDING_REPORT.json",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def setup_module() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=REPO_ROOT, check=True)


def test_required_outputs_and_decision_lock_finality() -> None:
    missing = [name for name in REQUIRED_OUTPUTS if not (OUTPUT_ROOT / name).exists()]
    assert missing == []

    decision = load_json(OUTPUT_ROOT / "E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_DECISION.json")
    assert decision["package_id"] == "MAIN-CITYBRAIN-EPOCH3-FINAL-NONLIVE-HIDDEN-FUEL-SCOUT-R1"
    assert decision["status"] == EXPECTED_STATUS
    assert decision["non_live_assumption"] is True
    assert decision["promotion_status"] == "candidate_inventory_and_backlog_only"
    assert decision["no_model_guard"] == "PASS"
    assert decision["finality_rule"] == FINALITY_RULE
    assert decision["no_more_pre_closeout_scouts"] is True
    assert decision["operator_paced_fuel_program"] == "deferred_not_live"
    assert "cannot_be_expected_to_arm" in decision["r3a_r3b_operator_fuel_expectation"]


def test_l4_content_verification_distinguishes_content_from_path_only() -> None:
    report = load_json(OUTPUT_ROOT / "E3_FINAL_L4_CASE_STUB_CONTENT_VERIFICATION_SCOUT.json")

    assert report["status"] == "PASS_WITH_LIMITATIONS"
    assert report["materialization_performed"] is False
    assert report["case_memory_rows_created"] == 0
    assert report["candidate_count"] >= 8
    assert report["content_verified"] > 0
    assert report["path_only"] > 0
    assert all(row["materialization_performed"] is False for row in report["candidates"])
    assert any(row["classification"] == "content_verified" for row in report["candidates"])
    assert any(row["classification"] == "path_only" for row in report["candidates"])


def test_check_readiness_is_descriptive_not_true_calibration() -> None:
    report = load_json(OUTPUT_ROOT / "E3_FINAL_CHECK_CALIBRATION_JOIN_READINESS_SCOUT.json")

    assert report["status"] == "PASS_WITH_LIMITATIONS"
    assert report["descriptive_scorecard_feasible_before_closeout"] is True
    assert report["true_calibration_ready"] is False
    assert report["operator_resolved_pairs_available"] is False
    assert report["classification_counts"]["ready_for_descriptive_scorecard"] > 0
    assert "operator_resolved_pairs_absent" in report["classification_counts"]
    assert all(row["true_calibration_claimed"] is False for row in report["candidates"])


def test_workflow_and_watch_outputs_capture_nonlive_operator_correction() -> None:
    workflow = load_json(OUTPUT_ROOT / "E3_FINAL_WORKFLOW_REVIEW_STATE_HISTORY_SCOUT.json")
    watch = load_json(OUTPUT_ROOT / "E3_FINAL_WATCH_RANKING_DESCRIPTIVE_SIGNAL_SCOUT.json")

    assert workflow["non_live_assumption"] is True
    assert workflow["operator_paced_fuel_program"] == "deferred_not_live"
    assert workflow["usable_history_refs"] > 0
    assert watch["required_statement_primary_r3"] == "verified exposure required for primary R3 fuel"
    assert watch["required_statement_historical"] == "historical unverified signals are descriptive only"
    assert watch["new_r3_training_rows_created"] == 0
    assert watch["r3_fuel_status"] == "not_promoted_from_nonlive_scout"


def test_simulation_and_identity_lanes_create_no_model_or_truth_changes() -> None:
    sim = load_json(OUTPUT_ROOT / "E3_FINAL_SIMULATION_BACKTEST_INPUT_SCOUT.json")
    graph = load_json(OUTPUT_ROOT / "E3_FINAL_IDENTITY_GRAPH_EVAL_FUEL_SCOUT.json")

    assert sim["candidate_count"] >= 10
    assert sim["forecast_model_created"] is False
    assert sim["ranker_created"] is False
    assert sim["backtest_harness_input_only"] is True
    assert all(row["model_created"] is False for row in sim["candidate_targets"])
    assert all(row["training_rows_created"] == 0 for row in sim["candidate_targets"])

    assert graph["candidate_count"] >= 8
    assert graph["canonical_truth_changes_created"] == 0
    assert graph["graph_merge_operations_created"] == 0
    assert all(row["canonical_truth_changed"] is False for row in graph["candidates"])
    assert all(row["merge_performed"] is False for row in graph["candidates"])


def test_final_backlog_uses_required_classifications_without_more_precloseout_scouts() -> None:
    backlog = load_json(OUTPUT_ROOT / "E3_FINAL_NONLIVE_HIDDEN_FUEL_BACKLOG.json")
    classifications = {item["classification"] for item in backlog["items"]}

    assert {"closeout_affecting", "epoch4_backlog", "parking_lot", "not_promotable"} <= classifications
    assert backlog["no_new_pre_closeout_scouts_recommended"] is True
    assert backlog["finality_rule"] == FINALITY_RULE
    assert any(item["priority"] == "P0" and item["classification"] == "closeout_affecting" for item in backlog["items"])
    assert not any("pre-closeout scout" in item["recommendation"].lower() for item in backlog["items"])


def test_publication_home_recommendation_and_no_model_guard() -> None:
    publication = load_json(OUTPUT_ROOT / "E3_PUBLICATION_HOME_RECOMMENDATION_ROW.json")
    guard = load_json(OUTPUT_ROOT / "E3_FINAL_NONLIVE_NO_MODEL_GUARD_REPORT.json")

    assert publication["status"] == "RECOMMENDATION"
    assert publication["outputs_gitignored"] is True
    assert publication["recommended_tracked_path"] == "publications/epoch3/"
    assert publication["implementation_performed"] is False
    assert "hash_manifests" in publication["governance_artifacts_to_track"]

    assert guard["status"] == "PASS"
    assert guard["new_training_rows_created"] == 0
    assert guard["new_learned_registry_entries"] == 0
    assert guard["ranker_created"] is False
    assert guard["forecast_model_created"] is False
    assert guard["counterfactual_learner_created"] is False
    assert guard["case_memory_learner_created"] is False
    assert guard["dynamic_investigation_created"] is False
    assert guard["cross_city_learned_transfer_created"] is False
    assert guard["product_surface_created"] is False
    assert guard["candidate_inventory_promoted_to_fuel"] is False
    assert guard["forbidden_capabilities_armed"] == []


def test_hash_manifest_and_line_endings_verify() -> None:
    manifest = load_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
    line_endings = load_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json")

    assert line_endings["status"] == "PASS_LF_STABLE_FOR_E3_FINAL_NONLIVE_HIDDEN_FUEL_SCOUT_R1"
    assert line_endings["crlf_paths"] == []

    paths = {entry["path"] for entry in manifest["files"]}
    for required in REQUIRED_OUTPUTS - {"HASH_MANIFEST.json"}:
        assert f"outputs/epoch3_final_nonlive_hidden_fuel_scout_r1/{required}" in paths

    for entry in manifest["files"]:
        path = REPO_ROOT / entry["path"]
        assert path.exists(), entry["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]

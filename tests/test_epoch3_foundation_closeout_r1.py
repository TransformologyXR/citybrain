from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_epoch3_foundation_closeout_r1.py"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_foundation_closeout_r1"
EXPECTED_STATUS = "PASS_E3_FOUNDATION_FOR_LEARNING_AND_BACKTESTING_WITH_LIMITATIONS"
FOUNDATION_CLOSED = {
    "L1.R0_EXPOSURE_AND_PROPENSITY_LOGGING",
    "L1.R0_WATCH_EXPLORATION_FLOOR_INFRA",
    "L1.R1_OUTCOME_LEDGER_HARDENING",
    "L1.R2_CALIBRATION_REPORT_HARDENING",
    "L2.R1_BACKTEST_HARNESS_BUILD",
    "E3.ARMING_STATUS_WATCH_FAMILY",
}
BLOCKED = {
    "L1.R3A_OFFLINE_RANKER_EXPERIMENT",
    "L1.R3B_OPERATOR_FACING_LEARNED_RANKING",
    "L2.R2_FORECAST_MODEL",
    "L3_COUNTERFACTUAL",
    "L4_CASE_MEMORY",
    "DYNAMIC_INVESTIGATION_AGENT",
    "CROSS_CITY_LEARNED_TRANSFER",
}
REQUIRED_ARTIFACTS = {
    "E3_FOUNDATION_CLOSEOUT_DECISION.json",
    "E3_FOUNDATION_CAPABILITY_SUMMARY.json",
    "E3_FOUNDATION_ARMING_STATUS_FINAL.json",
    "E3_FOUNDATION_NO_MODEL_GUARD_REPORT.json",
    "E3_FOUNDATION_CORPUS_AND_HASH_SUMMARY.json",
    "E3_FOUNDATION_BACKTEST_HARNESS_SUMMARY.json",
    "E3_FOUNDATION_OUTCOME_CALIBRATION_SUMMARY.json",
    "E3_FOUNDATION_EXPOSURE_COVERAGE_SUMMARY.json",
    "E3_FOUNDATION_LIMITATIONS.json",
    "E3_FOUNDATION_NEXT_ARMING_THRESHOLDS.json",
    "E3_FOUNDATION_LEDGER_ROW.json",
    "HASH_MANIFEST.json",
    "LINE_ENDING_REPORT.json",
    "README.md",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def setup_module() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=REPO_ROOT, check=True)


def test_required_publication_artifacts_exist() -> None:
    published = {path.name for path in OUTPUT_ROOT.iterdir() if path.is_file()}
    assert REQUIRED_ARTIFACTS <= published


def test_decision_is_foundation_closeout_not_full_epoch3_closeout() -> None:
    decision = load_json(OUTPUT_ROOT / "E3_FOUNDATION_CLOSEOUT_DECISION.json")

    assert decision["task_id"] == "MAIN-CITYBRAIN-EPOCH3-FOUNDATION-CLOSEOUT-R1"
    assert decision["status"] == EXPECTED_STATUS
    assert decision["foundation_closeout_ready"] is True
    assert decision["full_epoch3_closeout_ready"] is False
    assert decision["closeout_kind"] == "foundation_closeout_only_not_full_epoch3_closeout"
    assert decision["blockers"] == []
    assert set(decision["full_epoch3_remaining_paths"]) == BLOCKED
    for required_ref in [
        "outputs/epoch3_pre_closeout_convergence_r1/E3_PRE_CLOSEOUT_CONVERGENCE_DECISION.json",
        "outputs/epoch3_pre_closeout_convergence_r1/E3_SCHEDULED_WATCH_TICK_EXPOSURE_VERIFICATION_REPORT.json",
        "outputs/epoch3_pre_closeout_convergence_r1/E3_FULL_HISTORICAL_CORPUS_DISCOVERY_REPORT.json",
        "outputs/epoch3_pre_closeout_convergence_r1/E3_L2_R1_BACKTEST_HARNESS_REPORT.json",
        "outputs/epoch3_l1_r1_r2_outcome_calibration_hardening_r1/E3_OUTCOME_LEDGER_HARDENING_REPORT.json",
        "outputs/epoch3_phase2_live_exposure_coverage_and_hardening_r1/E3_LIVE_EXPOSURE_COVERAGE_VERIFICATION_REPORT.json",
    ]:
        assert required_ref in decision["evidence_refs"]


def test_capability_summary_rolls_up_foundation_evidence() -> None:
    summary = load_json(OUTPUT_ROOT / "E3_FOUNDATION_CAPABILITY_SUMMARY.json")
    caps = summary["capabilities"]

    assert set(summary["foundation_closed"]) == FOUNDATION_CLOSED
    assert caps["arming_status_watch_family"]["state"] == "foundation_ready"
    assert caps["exposure_propensity_logging"]["phase2_coverage_ratio"] == 1.0
    assert caps["scheduled_watch_tick_exposure"]["coverage_ratio"] == 1.0
    assert caps["scheduled_watch_tick_exposure"]["scheduled_tick_status"] == "PASS_FIRST_SCHEDULED_TICK_VERIFIED"
    assert caps["outcome_ledger_hardening"]["production_eligible_terminal_dispositions"] == 0
    assert caps["outcome_ledger_hardening"]["validation_fixtures_separated_from_production_fuel"] is True
    assert caps["calibration_hardening"]["sample_depth"] == 0
    assert caps["calibration_hardening"]["true_calibration_claimed"] is False
    assert caps["full_historical_corpus_discovery"]["status"] == "green"
    assert caps["l2_r1_backtest_harness"]["status"] == "PASS_BACKTEST_HARNESS_BUILT_NO_MODEL"
    assert caps["l2_r1_backtest_harness"]["forecast_model_created"] is False


def test_final_arming_status_blocks_future_capabilities() -> None:
    arming = load_json(OUTPUT_ROOT / "E3_FOUNDATION_ARMING_STATUS_FINAL.json")

    assert set(arming["armed_or_foundation_closed"]) == FOUNDATION_CLOSED
    assert set(arming["not_armed"]) == BLOCKED
    assert arming["foundation_closeout_ready"] is True
    assert arming["full_epoch3_closeout_ready"] is False
    assert arming["threshold_crossing_does_not_start_work"] is True
    assert arming["source_capabilities"]["L1.R3A_OFFLINE_RANKER_EXPERIMENT"]["state"] == "not_armed"
    assert arming["source_capabilities"]["L1.R3B_OPERATOR_FACING_LEARNED_RANKING"]["state"] == "not_armed"
    assert arming["source_capabilities"]["L2.R2_FORECAST_MODEL"]["state"] == "not_armed"


def test_no_model_guard_blocks_all_forbidden_models() -> None:
    guard = load_json(OUTPUT_ROOT / "E3_FOUNDATION_NO_MODEL_GUARD_REPORT.json")

    assert guard["status"] == "PASS"
    assert guard["ranker_created"] is False
    assert guard["forecast_model_created"] is False
    assert guard["counterfactual_learner_created"] is False
    assert guard["case_memory_learner_created"] is False
    assert guard["dynamic_investigation_agent_created"] is False
    assert guard["cross_city_learned_transfer_created"] is False
    assert guard["new_learned_component_registry_entries"] == 0
    assert guard["forbidden_capabilities_armed"] == []


def test_corpus_backtest_outcome_and_exposure_summaries_are_consistent() -> None:
    corpus = load_json(OUTPUT_ROOT / "E3_FOUNDATION_CORPUS_AND_HASH_SUMMARY.json")
    backtest = load_json(OUTPUT_ROOT / "E3_FOUNDATION_BACKTEST_HARNESS_SUMMARY.json")
    outcome = load_json(OUTPUT_ROOT / "E3_FOUNDATION_OUTCOME_CALIBRATION_SUMMARY.json")
    exposure = load_json(OUTPUT_ROOT / "E3_FOUNDATION_EXPOSURE_COVERAGE_SUMMARY.json")

    assert corpus["corpus_full_discovery"]["status"] == "green"
    assert corpus["control_corpus_parse_status"] == "PASS"
    assert corpus["control_corpus_hash_manifest_status"] == "PASS"
    assert corpus["legacy_payload_recertification_claimed"] is False

    assert backtest["status"] == "PASS_BACKTEST_HARNESS_BUILT_NO_MODEL"
    assert backtest["forecast_model_created"] is False
    assert backtest["baseline_comparator"] == "do_nothing_last_observed_count"
    assert backtest["check_gate_status"] == "PASS_SCAFFOLD_ONLY"

    assert outcome["production_eligible_terminal_dispositions"] == 0
    assert outcome["production_training_fuel_inflated_by_fixtures"] is False
    assert outcome["true_calibration_claimed"] is False
    assert outcome["calibration_sample_depth"] == 0

    assert exposure["phase2_replay_coverage"]["coverage_ratio"] == 1.0
    assert exposure["scheduled_tick_coverage"]["coverage_ratio"] == 1.0
    assert exposure["scheduled_tick_coverage"]["scheduled_tick_status"] == "PASS_FIRST_SCHEDULED_TICK_VERIFIED"
    assert exposure["surfaced_definition"] == "operator_visible_payload_inclusion"


def test_limitations_and_next_thresholds_are_published() -> None:
    limitations = load_json(OUTPUT_ROOT / "E3_FOUNDATION_LIMITATIONS.json")
    thresholds = load_json(OUTPUT_ROOT / "E3_FOUNDATION_NEXT_ARMING_THRESHOLDS.json")
    ledger = load_json(OUTPUT_ROOT / "E3_FOUNDATION_LEDGER_ROW.json")

    assert limitations["status"] == "PASS_WITH_LIMITATIONS"
    assert any("foundation closeout" in text for text in limitations["limitations"])
    assert any("not full Epoch 3" in text or "full Epoch 3" in text for text in limitations["limitations"])
    assert thresholds["threshold_crossing_behavior"] == "ledger_emit_only_no_silent_start"
    for capability in ["L1.R3A_OFFLINE_RANKER_EXPERIMENT", "L1.R3B_OPERATOR_FACING_LEARNED_RANKING", "L2.R2_FORECAST_MODEL"]:
        assert capability in thresholds["thresholds"]
    assert ledger["status"] == EXPECTED_STATUS
    assert ledger["foundation_closeout_ready"] is True
    assert ledger["full_epoch3_closeout_ready"] is False


def test_schemas_and_manifests_are_present() -> None:
    for path in [
        "schemas/foundation_closeout_decision.schema.json",
        "schemas/foundation_arming_status.schema.json",
        "schemas/foundation_ledger_row.schema.json",
        "schemas/foundation_report_base.schema.json",
        "schemas/no_model_guard.schema.json",
        "manifests/epoch3_foundation_closeout_work_plan_manifest.json",
        "manifests/epoch3_foundation_closeout_acceptance_criteria_manifest.json",
        "manifests/epoch3_foundation_closeout_dependency_graph.json",
    ]:
        assert (REPO_ROOT / path).exists(), path
        load_json(REPO_ROOT / path)


def test_hash_manifest_and_line_endings_verify() -> None:
    manifest = load_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
    line_endings = load_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json")

    assert line_endings["status"] == "PASS_LF_STABLE_FOR_E3_FOUNDATION_CLOSEOUT"
    assert line_endings["crlf_paths"] == []

    manifest_paths = {Path(entry["path"]).name for entry in manifest["files"]}
    assert REQUIRED_ARTIFACTS - {"HASH_MANIFEST.json"} <= manifest_paths
    assert manifest["self_reference_policy"] == "HASH_MANIFEST.json is excluded to avoid recursive hash instability."

    for entry in manifest["files"]:
        path = REPO_ROOT / entry["path"]
        assert path.exists(), entry["path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == entry["sha256"], entry["path"]

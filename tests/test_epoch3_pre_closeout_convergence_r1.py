from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_epoch3_pre_closeout_convergence_r1.py"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_pre_closeout_convergence_r1"
EXPECTED_STATUS = "PASS_E3_PRE_CLOSEOUT_CONVERGENCE_R1_WITH_LIMITATIONS"
BLOCKED = {
    "L1.R3A_OFFLINE_RANKER_EXPERIMENT",
    "L1.R3B_OPERATOR_FACING_LEARNED_RANKING",
    "L2.R2_FORECAST_MODEL",
    "L3_COUNTERFACTUAL",
    "L4_CASE_MEMORY",
    "DYNAMIC_INVESTIGATION_AGENT",
    "CROSS_CITY_LEARNED_TRANSFER",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def setup_module() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=REPO_ROOT, check=True)


def test_decision_marks_foundation_closeout_ready_only() -> None:
    decision = load_json(OUTPUT_ROOT / "E3_PRE_CLOSEOUT_CONVERGENCE_DECISION.json")

    assert decision["task_id"] == "MAIN-CITYBRAIN-EPOCH3-PRE-CLOSEOUT-CONVERGENCE-R1"
    assert decision["status"] == EXPECTED_STATUS
    assert decision["foundation_closeout_ready"] is True
    assert decision["full_epoch3_closeout_ready"] is False
    assert decision["closeout_readiness"] == "FOUNDATION_CLOSEOUT_READY_WITH_LIMITATIONS"
    assert decision["next_recommended_package"] == "MAIN-CITYBRAIN-EPOCH3-FOUNDATION-CLOSEOUT-R1"
    assert set(decision["still_blocked"]) == BLOCKED
    assert not (set(decision["armed_now"]) & BLOCKED)


def test_scheduled_watch_tick_exposure_verification_closes_pending_path() -> None:
    report = load_json(OUTPUT_ROOT / "E3_SCHEDULED_WATCH_TICK_EXPOSURE_VERIFICATION_REPORT.json")
    payload = load_json(OUTPUT_ROOT / "fixtures" / "scheduled_watch_tick_payload.json")
    envelope = load_json(OUTPUT_ROOT / "fixtures" / "scheduled_watch_tick_run_envelope.json")
    events = load_jsonl(OUTPUT_ROOT / "fixtures" / "scheduled_watch_tick_exposure_events.jsonl")

    assert report["phase2_previous_status"] == "PENDING_FIRST_SCHEDULED_TICK"
    assert report["status"] == "PASS"
    assert report["scheduled_tick_status"] == "PASS_FIRST_SCHEDULED_TICK_VERIFIED"
    assert report["non_empty_payload"] is True
    assert report["coverage_ratio"] == 1.0
    assert report["expected_payload_items"] == len(payload["items"]) == 3
    assert report["emitted_exposure_events"] == len(events) == 3
    assert report["orphan_exposure_events"] == []
    assert report["payload_items_without_exposure"] == []
    assert envelope["run_kind"] == "scheduled_watch_tick"
    assert all(event["scheduled_tick_observed"] is True for event in events)
    assert {event["run_envelope_ref"] for event in events} == {envelope["run_envelope_id"]}
    assert all(event["surfaced_definition"] == "operator_visible_payload_inclusion" for event in events)


def test_full_historical_corpus_discovery_is_green_without_overclaiming_fuel() -> None:
    report = load_json(OUTPUT_ROOT / "E3_FULL_HISTORICAL_CORPUS_DISCOVERY_REPORT.json")
    index = load_json(OUTPUT_ROOT / "E3_FULL_HISTORICAL_CORPUS_DISCOVERY_INDEX.json")

    assert report["status"] == "PASS"
    assert report["corpus"]["full_discovery"]["status"] == "green"
    assert report["corpus"]["full_discovery"]["artifact_roots_indexed"] >= 900
    assert report["corpus"]["full_discovery"]["files_indexed"] > 100000
    assert report["corpus"]["full_discovery"]["json_or_jsonl_files_indexed"] > 70000
    assert report["indexing_error_count"] == 0
    assert report["control_corpus_parse"]["status"] == "PASS"
    assert report["control_corpus_parse"]["parse_error_count"] == 0
    assert report["control_hash_manifest_verification"]["status"] == "PASS"
    assert report["control_hash_manifest_verification"]["failure_count"] == 0
    assert "legacy generated payloads are path-discovered, not re-certified" in report["content_validation_scope"]
    assert index["output_roots_indexed"] == report["corpus"]["full_discovery"]["artifact_roots_indexed"]


def test_l2r1_backtest_harness_outputs_required_non_model_artifacts() -> None:
    backtest = load_json(OUTPUT_ROOT / "E3_L2_R1_BACKTEST_HARNESS_REPORT.json")
    target = load_json(OUTPUT_ROOT / "E3_L2_R1_FIRST_FORECAST_TARGET_DECISION.json")
    frozen = load_json(OUTPUT_ROOT / "E3_L2_R1_FROZEN_EVAL_SLICE_CONTRACT.json")
    comparator = load_json(OUTPUT_ROOT / "E3_L2_R1_BASELINE_DO_NOTHING_COMPARATOR.json")
    uncertainty = load_json(OUTPUT_ROOT / "E3_L2_R1_FORECAST_UNCERTAINTY_SCHEMA_PATH.json")
    check_gate = load_json(OUTPUT_ROOT / "E3_L2_R1_FORECAST_PACKET_CHECK_GATE_SCAFFOLD.json")

    assert backtest["status"] == "PASS_BACKTEST_HARNESS_BUILT_NO_MODEL"
    assert backtest["forecast_model_created"] is False
    assert backtest["metrics"]["sample_size"] == 3
    assert backtest["metrics"]["absolute_error"] == 0
    assert target["training_or_prediction_enabled"] is False
    assert target["forecast_target_id"] == "forecast_target:e3:l2r1:review_backlog_next_tick_count"
    assert frozen["frozen"] is True
    assert frozen["mutation_policy"] == "additive_new_slice_versions_only"
    assert comparator["forecast_model_created"] is False
    assert comparator["comparator_kind"] == "do_nothing_last_observed_count"
    assert uncertainty["schema_ref"] == "schemas/forecast_uncertainty.schema.json"
    assert (REPO_ROOT / uncertainty["schema_ref"]).exists()
    assert check_gate["forecast_model_enabled"] is False
    assert check_gate["dispatch_or_action_enabled"] is False
    assert "human_review_only_boundary" in check_gate["required_checks"]


def test_arming_status_removes_corpus_blocker_but_keeps_learning_blocked() -> None:
    snapshot = load_json(OUTPUT_ROOT / "E3_PRE_CLOSEOUT_ARMING_STATUS_SNAPSHOT.json")
    r3a = snapshot["capabilities"]["L1.R3A_OFFLINE_RANKER_EXPERIMENT"]

    assert snapshot["foundation_closeout_ready"] is True
    assert snapshot["full_epoch3_closeout_ready"] is False
    assert snapshot["corpus_full_discovery_status"] == "green"
    assert snapshot["scheduled_tick_status"] == "PASS_FIRST_SCHEDULED_TICK_VERIFIED"
    assert snapshot["capabilities"]["E3.ARMING_STATUS_WATCH_FAMILY"]["state"] == "foundation_ready"
    assert snapshot["capabilities"]["L2.R1_BACKTEST_HARNESS_BUILD"]["state"] == "closed_for_foundation"
    assert r3a["state"] == "not_armed"
    assert "R3A_FULL_CORPUS_DISCOVERY_GREEN" not in r3a["failed_requirement_ids"]
    assert "R3A_TOTAL_DISPOSITIONS" in r3a["failed_requirement_ids"]
    assert snapshot["capabilities"]["L1.R3B_OPERATOR_FACING_LEARNED_RANKING"]["state"] == "not_armed"
    assert snapshot["capabilities"]["L2.R2_FORECAST_MODEL"]["state"] == "not_armed"
    assert snapshot["previous_snapshot_ref"].endswith(
        "outputs/epoch3_l1_r1_r2_outcome_calibration_hardening_r1/E3_FUEL_GAUGE_DELTA_SNAPSHOT_R1_R2.json"
    )


def test_no_model_guard_stays_hard_green() -> None:
    guard = load_json(OUTPUT_ROOT / "E3_PRE_CLOSEOUT_NO_MODEL_GUARD_REPORT.json")

    assert guard["status"] == "PASS"
    assert guard["new_learned_component_registry_entries"] == 0
    assert guard["forbidden_capabilities_armed"] == []
    assert guard["ranker_created"] is False
    assert guard["forecast_model_created"] is False
    assert guard["counterfactual_learner_created"] is False
    assert guard["case_memory_learner_created"] is False
    assert guard["dynamic_investigation_agent_created"] is False
    assert guard["cross_city_learned_transfer_created"] is False


def test_schema_and_manifest_files_are_present() -> None:
    for path in [
        "schemas/scheduled_watch_tick_exposure_verification.schema.json",
        "schemas/full_historical_corpus_discovery_report.schema.json",
        "schemas/backtest_report.schema.json",
        "schemas/forecast_target_decision.schema.json",
        "schemas/frozen_eval_slice_contract.schema.json",
        "schemas/baseline_comparator.schema.json",
        "schemas/forecast_uncertainty.schema.json",
        "schemas/forecast_packet_check_gate_scaffold.schema.json",
        "schemas/pre_closeout_convergence_decision.schema.json",
        "manifests/epoch3_pre_closeout_convergence_work_plan_manifest.json",
        "manifests/epoch3_pre_closeout_convergence_acceptance_criteria_manifest.json",
        "manifests/epoch3_pre_closeout_convergence_dependency_graph.json",
    ]:
        assert (REPO_ROOT / path).exists(), path
        load_json(REPO_ROOT / path)


def test_hash_manifest_and_line_endings_verify() -> None:
    manifest = load_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
    line_endings = load_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json")

    assert line_endings["status"] == "PASS_LF_STABLE_FOR_E3_PRE_CLOSEOUT_CONVERGENCE"
    assert line_endings["crlf_paths"] == []

    for entry in manifest["files"]:
        path = REPO_ROOT / entry["path"]
        assert path.exists(), entry["path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == entry["sha256"], entry["path"]

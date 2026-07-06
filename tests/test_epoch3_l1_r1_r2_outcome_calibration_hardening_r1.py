from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_epoch3_l1_r1_r2_outcome_calibration_hardening_r1.py"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_l1_r1_r2_outcome_calibration_hardening_r1"
EXPECTED_STATUS = "PASS_E3_L1_R1_R2_OUTCOME_CALIBRATION_HARDENING_R1_WITH_LIMITATIONS"
BLOCKED = {
    "L1.R3A_OFFLINE_RANKER_EXPERIMENT",
    "L1.R3B_OPERATOR_FACING_LEARNED_RANKING",
    "L2.R2_FORECAST_MODEL",
    "L3_COUNTERFACTUAL",
    "L4_CASE_MEMORY",
    "DYNAMIC_INVESTIGATION_AGENT",
    "CROSS_CITY_LEARNED_TRANSFER",
}
REQUIRED_REASONS = {
    "eligible_terminal_disposition",
    "not_terminal_disposition",
    "propensity_unknown",
    "unverified_exposure",
    "holdout_family_not_training_eligible",
    "missing_operator_ref",
    "aggregation_floor_not_satisfied",
    "pre_validation_fix",
    "source_class_ineligible",
    "missing_family",
    "missing_domain_pack",
    "missing_check_linkage",
    "invalid_disposition_value",
    "fixture_not_production_fuel",
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


def test_decision_keeps_learning_capabilities_blocked() -> None:
    decision = load_json(OUTPUT_ROOT / "E3_L1_R1_R2_DECISION.json")

    assert decision["status"] == EXPECTED_STATUS
    assert decision["source_dependency_status"] == "PASS"
    assert set(decision["still_blocked"]) == BLOCKED
    assert "L1.R1_OUTCOME_LEDGER_HARDENING" in decision["armed_now"]
    assert "L1.R2_CALIBRATION_REPORT_HARDENING" in decision["armed_now"]
    assert not (set(decision["armed_now"]) & BLOCKED)


def test_training_eligibility_schema_and_rules_are_complete() -> None:
    schema = load_json(REPO_ROOT / "schemas" / "training_eligibility.schema.json")
    rules = load_json(OUTPUT_ROOT / "E3_TRAINING_ELIGIBILITY_RULES_REPORT.json")

    assert set(schema["properties"]["primary_reason"]["enum"]) == REQUIRED_REASONS
    assert set(rules["reason_enum"]) == REQUIRED_REASONS
    assert rules["rules"]["fixtures_count_as_production_fuel"] is False
    assert rules["rules"]["historical_propensity_unknown_upgraded_to_fuel"] is False


def test_outcome_record_schema_requires_exposure_check_and_training_fields() -> None:
    schema = load_json(REPO_ROOT / "schemas" / "outcome_record.schema.json")

    required = set(schema["required"])
    assert {
        "exposure_id",
        "exposure_run_envelope_ref",
        "operator_ref",
        "watch_family",
        "domain_pack_ref",
        "source_class_refs",
        "check_report_refs",
        "queue_depth_at_exposure",
        "time_to_disposition_seconds",
        "training_eligibility",
    } <= required


def test_validation_fixtures_cover_verified_unverified_and_unknown_paths() -> None:
    exposures = load_jsonl(OUTPUT_ROOT / "fixtures" / "exposure_events_for_outcome_hardening.jsonl")
    dispositions = load_jsonl(OUTPUT_ROOT / "fixtures" / "disposition_events_mixed.jsonl")
    records = load_jsonl(OUTPUT_ROOT / "E3_OUTCOME_RECORDS_VALIDATION_FIXTURE.jsonl")

    assert len(exposures) == 5
    assert len(dispositions) == 6
    assert len(records) == 6
    assert any(row["exposure_verified"] for row in exposures)
    assert any(row["propensity_status"] == "propensity_unknown" for row in exposures)
    assert {row["watch_item_id"] for row in dispositions} - {
        row["watch_item_id"] for row in exposures
    } == {"watch:item:no_exposure:006"}

    no_exposure = next(row for row in records if row["watch_item_id"] == "watch:item:no_exposure:006")
    assert no_exposure["training_eligibility"]["primary_reason"] == "unverified_exposure"
    assert no_exposure["exposure_id"] == "MISSING_EXPOSURE"


def test_outcome_report_counts_fixture_fuel_without_upgrading_production() -> None:
    report = load_json(OUTPUT_ROOT / "E3_OUTCOME_LEDGER_HARDENING_REPORT.json")
    expected = load_json(OUTPUT_ROOT / "fixtures" / "expected_training_eligibility_counts.json")

    assert report["validation_fixture_records"] == expected["fixture_records_total"] == 6
    assert report["production_eligible_terminal_dispositions"] == 0
    assert report["fixture_eligible_if_production_records"] == 2
    assert report["primary_reason_counts"] == expected["primary_reason_counts"]
    assert report["validation_fixtures_separated_from_production_fuel"] is True
    assert report["historical_propensity_unknown_upgraded_to_fuel"] is False

    records = load_jsonl(OUTPUT_ROOT / "E3_OUTCOME_RECORDS_VALIDATION_FIXTURE.jsonl")
    assert not any(row["counts_toward_production_fuel"] for row in records)
    assert not any(row["training_eligibility"]["is_training_eligible"] for row in records)


def test_check_to_disposition_join_report_preserves_missing_linkage() -> None:
    report = load_json(OUTPUT_ROOT / "E3_CHECK_TO_DISPOSITION_JOIN_REPORT.json")

    assert report["status"] == "PASS_WITH_LIMITATIONS"
    assert report["joined_records"] == 5
    assert report["missing_check_linkage"] == 1
    assert report["missing_check_linkage_record_ids"] == ["outcome:e3-l1r1r2:fixture:006"]


def test_calibration_report_is_descriptive_only_and_slice_complete() -> None:
    report = load_json(OUTPUT_ROOT / "E3_CALIBRATION_REPORT_HARDENING_REPORT.json")
    slice_types = {row["slice_type"] for row in report["slices"]}

    assert report["true_calibration_claimed"] is False
    assert report["sample_depth"] == 0
    assert {
        "check_type",
        "source_class",
        "watch_family",
        "domain_pack",
        "terminal_disposition",
        "eligibility_reason",
        "cannot_claim_class",
    } <= slice_types
    assert any(
        row["slice_type"] == "eligibility_reason"
        and row["slice_value"] == "fixture_not_production_fuel"
        for row in report["slices"]
    )


def test_fuel_snapshot_chains_phase2_and_keeps_r3_blocked() -> None:
    snapshot = load_json(OUTPUT_ROOT / "E3_FUEL_GAUGE_DELTA_SNAPSHOT_R1_R2.json")

    assert snapshot["previous_snapshot_ref"].endswith(
        "outputs/epoch3_phase2_live_exposure_coverage_and_hardening_r1/E3_FUEL_GAUGE_DELTA_SNAPSHOT.json"
    )
    assert snapshot["eligible_terminal_dispositions_total"] == 0
    assert snapshot["fixture_eligible_if_production_records"] == 2
    assert snapshot["fixture_terminal_dispositions_total"] == 5
    assert snapshot["arming_status"]["L1.R3A_OFFLINE_RANKER_EXPERIMENT"] == "NOT_ARMED"
    assert snapshot["arming_status"]["L1.R3B_OPERATOR_FACING_LEARNED_RANKING"] == "NOT_ARMED"
    assert "R3A_FULL_CORPUS_DISCOVERY_GREEN" in snapshot["failed_requirement_ids"]
    assert "R3A_TOTAL_DISPOSITIONS" in snapshot["failed_requirement_ids"]
    assert "R3B_TOTAL_DISPOSITIONS" in snapshot["failed_requirement_ids"]


def test_scheduled_tick_pending_is_carried_forward() -> None:
    update = load_json(OUTPUT_ROOT / "E3_ARMING_STATUS_R1_R2_UPDATE.json")

    assert update["scheduled_tick_watcher_active"] is True
    assert update["scheduled_tick_status"] == "PENDING_FIRST_SCHEDULED_TICK"
    assert update["capabilities"]["L2.R2_FORECAST_MODEL"]["state"] == "not_armed"


def test_no_model_guard_blocks_all_learned_work() -> None:
    guard = load_json(OUTPUT_ROOT / "E3_NO_MODEL_GUARD_REPORT.json")

    assert guard["status"] == "PASS"
    assert guard["new_learned_component_registry_entries"] == 0
    assert guard["forbidden_capabilities_armed"] == []
    assert guard["ranker_created"] is False
    assert guard["forecast_model_created"] is False
    assert guard["counterfactual_learner_created"] is False
    assert guard["case_memory_learner_created"] is False
    assert guard["dynamic_investigation_agent_created"] is False
    assert guard["cross_city_learned_transfer_created"] is False


def test_corpus_delta_registers_only_fixtures_and_reports() -> None:
    delta = load_json(OUTPUT_ROOT / "E3_L1_R1_R2_CORPUS_DELTA.json")

    assert delta["status"] == "PASS_ADD_FIXTURES_ONLY"
    assert "fixtures/exposure_events_for_outcome_hardening.jsonl" in delta["registered_fixtures"]
    assert "fixtures/disposition_events_mixed.jsonl" in delta["registered_fixtures"]
    assert "E3_CALIBRATION_REPORT_HARDENING_REPORT.json" in delta["registered_reports"]
    assert delta["full_historical_discovery_status"] == "UNCHANGED_BLOCKER_FOR_R3A"


def test_hash_manifest_and_line_endings_verify() -> None:
    manifest = load_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
    line_endings = load_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json")

    assert line_endings["status"] == "PASS_LF_STABLE_FOR_E3_L1_R1_R2_PUBLICATION"
    assert line_endings["crlf_paths"] == []

    for entry in manifest["files"]:
        path = REPO_ROOT / entry["path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == entry["sha256"], entry["path"]

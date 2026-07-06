from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_epoch3_l2_historical_label_backfill_r1.py"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_l2_historical_label_backfill_r1"
EXPECTED_STATUS = "PASS_E3_L2_HISTORICAL_LABEL_BACKFILL_R1_WITH_LIMITATIONS"
EXPECTED_SUB_STATUS = "PASS_TRANSITION_HISTORY_MATERIALIZED_NO_MODEL_WITH_LIMITATIONS"
MINIMUM_REQUIRED_ROWS = 100
REQUIRED_ARTIFACTS = {
    "E3_L2_HISTORICAL_LABEL_BACKFILL_DECISION.json",
    "E3_L2_HISTORICAL_TRANSITION_DISCOVERY_REPORT.json",
    "E3_L2_HISTORICAL_LABEL_BACKFILL_MANIFEST.json",
    "E3_L2_R1_TARGET_SUFFICIENCY_REPORT_R2.json",
    "E3_L2_L2R2_ARMING_READOUT.json",
    "E3_NO_MODEL_GUARD_REPORT.json",
    "E3_L2_SOURCE_CLASS_NO_FABRICATION_AUDIT.json",
    "E3_L2_HISTORICAL_LABEL_BACKFILL_LIMITATIONS.json",
    "E3_L2_HISTORICAL_LABEL_BACKFILL_CORPUS_DELTA.json",
    "E3_L2_HISTORICAL_LABEL_BACKFILL_LEDGER_ROW.json",
    "HASH_MANIFEST.json",
    "LINE_ENDING_REPORT.json",
}
TRANSITION_BRANCH_ARTIFACTS = {
    "E3_L2_GOVERNED_HISTORICAL_LABEL_ROWS.jsonl",
    "E3_L2_R1_BASELINE_BACKTEST_REPORT_R2.json",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def setup_module() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=REPO_ROOT, check=True)


def test_required_artifacts_and_decision_status() -> None:
    published = {path.name for path in OUTPUT_ROOT.iterdir() if path.is_file()}
    decision = load_json(OUTPUT_ROOT / "E3_L2_HISTORICAL_LABEL_BACKFILL_DECISION.json")

    assert REQUIRED_ARTIFACTS <= published
    assert TRANSITION_BRANCH_ARTIFACTS <= published
    assert decision["task_id"] == "MAIN-CITYBRAIN-EPOCH3-L2-HISTORICAL-LABEL-BACKFILL-R1"
    assert decision["status"] == EXPECTED_STATUS
    assert decision["sub_status"] == EXPECTED_SUB_STATUS
    assert decision["blockers"] == []
    assert decision["forecast_model_created"] is False
    assert decision["mid_run_arming_rule"] == "ledger_row_only_no_forecast_model_start_in_same_run"


def test_discovery_finds_real_transition_history_not_snapshot_inference() -> None:
    discovery = load_json(OUTPUT_ROOT / "E3_L2_HISTORICAL_TRANSITION_DISCOVERY_REPORT.json")
    counts = discovery["classification_counts"]
    source_families = {source["source_family"] for source in discovery["source_reports"]}

    assert discovery["target_id"] == "permit_stall_v0"
    assert discovery["branch"] == "transition_history_present"
    assert discovery["transition_history_found"] is True
    assert discovery["records_scanned"] > 1_000_000
    assert counts["transition_history_present"] >= MINIMUM_REQUIRED_ROWS
    assert counts["terminal_and_current_snapshots_only"] > 0
    assert "At least two dated state observations" in discovery["discovery_policy"]
    assert {"london_pld_planning_ingest", "nyc_dob_now_build_filings", "nyc_dob_permit_issuance"} <= source_families
    assert any(example["city_id"] == "london" for example in discovery["evidence_examples"])
    assert any(example["city_id"] == "nyc" for example in discovery["evidence_examples"])


def test_governed_label_rows_are_source_derived_capped_and_not_fabricated() -> None:
    rows = load_jsonl(OUTPUT_ROOT / "E3_L2_GOVERNED_HISTORICAL_LABEL_ROWS.jsonl")
    manifest = load_json(OUTPUT_ROOT / "E3_L2_HISTORICAL_LABEL_BACKFILL_MANIFEST.json")
    cities = {row["city_id"] for row in rows}
    refs = [ref for row in rows for ref in row["source_record_refs"]]

    assert len(rows) == manifest["label_rows_materialized"]
    assert len(rows) >= MINIMUM_REQUIRED_ROWS
    assert manifest["branch"] == "transitions_materialized"
    assert manifest["model_allowed"] is False
    assert cities == {"london", "nyc"}
    assert any("lon_d5_pld_planning_ingest" in ref for ref in refs)
    assert any("nyc_dob_now_build_filings" in ref for ref in refs)
    assert any("nyc_dob_permit_issuance" in ref for ref in refs)

    required = {
        "label_row_id",
        "target_id",
        "source_record_refs",
        "source_class",
        "transition_refs",
        "label_window_start",
        "label_window_end",
        "observation_window_days",
        "stall_threshold_days",
        "is_stalled",
        "eligibility_status",
        "lineage_refs",
        "model_allowed",
        "training_label_row_kind",
    }
    for row in rows[:20]:
        assert required <= set(row)
        assert row["target_id"] == "permit_stall_v0"
        assert row["source_class"] == "derived_from_source_record"
        assert row["training_label_row_kind"] == "real_historical_source_derived"
        assert row["eligibility_status"] == "eligible_for_baseline_backtest"
        assert row["model_allowed"] is False
        assert len(row["transition_refs"]) >= 2
        assert date.fromisoformat(row["label_window_start"]) <= date.fromisoformat(row["label_window_end"])
        assert row["is_stalled"] == (row["observation_window_days"] >= row["stall_threshold_days"])


def test_sufficiency_and_baseline_backtest_rerun_remain_no_model() -> None:
    rows = load_jsonl(OUTPUT_ROOT / "E3_L2_GOVERNED_HISTORICAL_LABEL_ROWS.jsonl")
    sufficiency = load_json(OUTPUT_ROOT / "E3_L2_R1_TARGET_SUFFICIENCY_REPORT_R2.json")
    backtest = load_json(OUTPUT_ROOT / "E3_L2_R1_BASELINE_BACKTEST_REPORT_R2.json")

    assert sufficiency["label_history_sufficient"] is True
    assert sufficiency["eligible_history_rows_found"] == len(rows)
    assert sufficiency["minimum_required_labeled_rows"] == MINIMUM_REQUIRED_ROWS
    assert sufficiency["status"] == "PASS_LABEL_HISTORY_SUFFICIENT_NO_MODEL"
    assert sufficiency["model_allowed"] is False
    assert sufficiency["label_counts"]["total"] == len(rows)

    assert backtest["status"] == "PASS_BASELINE_BACKTEST_RERUN_NO_MODEL"
    assert backtest["baseline_comparator"] == "historical_majority_rate_no_model"
    assert backtest["forecast_model_created"] is False
    assert backtest["forecast_packet_model_output_created"] is False
    assert backtest["model_allowed"] is False
    assert backtest["no_model_assertion"] is True
    assert backtest["metrics"]["sample_size"] == len(rows)


def test_l2r2_readout_no_model_guard_and_no_fabrication_audit() -> None:
    readout = load_json(OUTPUT_ROOT / "E3_L2_L2R2_ARMING_READOUT.json")
    guard = load_json(OUTPUT_ROOT / "E3_NO_MODEL_GUARD_REPORT.json")
    audit = load_json(OUTPUT_ROOT / "E3_L2_SOURCE_CLASS_NO_FABRICATION_AUDIT.json")

    assert readout["capability_id"] == "L2.R2_FORECAST_MODEL"
    assert readout["armed"] is False
    assert readout["thresholds_not_reimplemented"] is True
    assert readout["forecast_model_created"] is False
    assert readout["mid_run_arming_ledger_row_emitted"] is False
    assert set(readout["cleared_requirement_ids"]) == {"L2R2_LABEL_HISTORY_SUFFICIENT", "L2R2_BACKTEST_REPORT_EXISTS"}
    assert "L2R2_MODEL_AUTHORITY_NOT_GRANTED" in readout["failed_requirement_ids"]
    assert "L2R2_FORECAST_MODEL_EXPLICITLY_DEFERRED" in readout["failed_requirement_ids"]

    assert guard["status"] == "PASS"
    for key in [
        "ranker_created",
        "operator_facing_ranker_created",
        "forecast_model_created",
        "forecast_packet_model_output_created",
        "learned_predictor_created",
        "counterfactual_learner_created",
        "case_memory_learner_created",
        "dynamic_investigation_agent_created",
        "cross_city_learned_transfer_created",
    ]:
        assert guard[key] is False
    assert guard["new_learned_component_registry_entries"] == 0
    assert guard["forbidden_capabilities_armed"] == []

    assert audit["status"] == "PASS"
    assert audit["fabricated_transition_count"] == 0
    assert audit["single_snapshot_rows_converted"] == 0
    assert audit["source_class_allowed"] == ["derived_from_source_record"]


def test_corpus_delta_limitations_ledger_and_hashes() -> None:
    delta = load_json(OUTPUT_ROOT / "E3_L2_HISTORICAL_LABEL_BACKFILL_CORPUS_DELTA.json")
    limitations = load_json(OUTPUT_ROOT / "E3_L2_HISTORICAL_LABEL_BACKFILL_LIMITATIONS.json")
    ledger = load_json(OUTPUT_ROOT / "E3_L2_HISTORICAL_LABEL_BACKFILL_LEDGER_ROW.json")
    manifest = load_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
    line_endings = load_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json")

    for artifact in [
        "E3_L2_HISTORICAL_TRANSITION_DISCOVERY_REPORT.json",
        "E3_L2_GOVERNED_HISTORICAL_LABEL_ROWS.jsonl",
        "E3_L2_R1_BASELINE_BACKTEST_REPORT_R2.json",
        "E3_L2_SOURCE_CLASS_NO_FABRICATION_AUDIT.json",
    ]:
        assert artifact in delta["registered_artifacts"]

    assert limitations["status"] == "PASS_WITH_LIMITATIONS"
    assert limitations["transition_history_found"] is True
    assert ledger["status"] == EXPECTED_STATUS
    assert ledger["sub_status"] == EXPECTED_SUB_STATUS
    assert ledger["forecast_model_started"] is False

    assert line_endings["status"] == "PASS_LF_STABLE_FOR_E3_L2_HISTORICAL_LABEL_BACKFILL_R1"
    assert line_endings["crlf_paths"] == []
    assert manifest["self_reference_policy"] == "HASH_MANIFEST.json is excluded to avoid recursive hash instability."
    for entry in manifest["files"]:
        path = REPO_ROOT / entry["path"]
        assert path.exists(), entry["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], entry["path"]


def test_schemas_and_manifest_contracts_are_present_and_validate_samples() -> None:
    schema_paths = {
        "discovery": REPO_ROOT / "schemas" / "historical_transition_discovery_report.schema.json",
        "label_row": REPO_ROOT / "schemas" / "governed_historical_label_row.schema.json",
        "manifest": REPO_ROOT / "schemas" / "historical_label_backfill_manifest.schema.json",
        "sufficiency": REPO_ROOT / "schemas" / "l2_sufficiency_report_r2.schema.json",
        "forward_plan": REPO_ROOT / "schemas" / "forward_accumulation_plan.schema.json",
    }
    expected_outputs = REPO_ROOT / "manifests" / "epoch3_l2_historical_label_backfill_expected_outputs.json"

    for path in [*schema_paths.values(), expected_outputs]:
        assert path.exists(), path
        load_json(path)

    jsonschema.validate(
        load_json(OUTPUT_ROOT / "E3_L2_HISTORICAL_TRANSITION_DISCOVERY_REPORT.json"),
        load_json(schema_paths["discovery"]),
    )
    jsonschema.validate(
        load_jsonl(OUTPUT_ROOT / "E3_L2_GOVERNED_HISTORICAL_LABEL_ROWS.jsonl")[0],
        load_json(schema_paths["label_row"]),
    )
    jsonschema.validate(
        load_json(OUTPUT_ROOT / "E3_L2_HISTORICAL_LABEL_BACKFILL_MANIFEST.json"),
        load_json(schema_paths["manifest"]),
    )
    jsonschema.validate(
        load_json(OUTPUT_ROOT / "E3_L2_R1_TARGET_SUFFICIENCY_REPORT_R2.json"),
        load_json(schema_paths["sufficiency"]),
    )

    expected = load_json(expected_outputs)
    assert expected["package_id"] == "MAIN-CITYBRAIN-EPOCH3-L2-HISTORICAL-LABEL-BACKFILL-R1"
    assert set(expected["transition_history_branch_artifacts"]) == TRANSITION_BRANCH_ARTIFACTS

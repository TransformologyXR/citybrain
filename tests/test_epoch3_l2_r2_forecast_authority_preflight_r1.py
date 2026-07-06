from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_epoch3_l2_r2_forecast_authority_preflight_r1.py"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_l2_r2_forecast_authority_preflight_r1"
EXPECTED_STATUS = "PASS_E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_R1_WITH_LIMITATIONS"
REQUIRED_ARTIFACTS = {
    "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_DECISION.json",
    "E3_L2_BACKFILL_R2_GOVERNED_LABEL_ROWS.jsonl",
    "E3_L2_BACKFILL_R2_LABEL_MATERIALIZATION_REPORT.json",
    "E3_L2_BACKFILL_R2_PER_CITY_LABEL_STATS.json",
    "E3_L2_BACKFILL_R2_TIME_STRATIFICATION_STATS.json",
    "E3_L2_BACKFILL_R2_TRANSITION_SEQUENCE_INTEGRITY_REPORT.json",
    "E3_L2_R2_FORECAST_METRIC_SUCCESS_CRITERIA.json",
    "E3_L2_R1_BASELINE_BACKTEST_REPORT_CORRECTED_METRICS.json",
    "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_REPORT.json",
    "E3_L2_R2_HUMAN_AUTHORITY_DECISION_ROW.template.json",
    "E3_L2_R2_TRAINING_MANIFEST_REQUIREMENTS.json",
    "E3_L2_R2_NO_MODEL_GUARD_REPORT.json",
    "E3_L2_R2_SOURCE_CLASS_NO_FABRICATION_AUDIT.json",
    "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_LIMITATIONS.json",
    "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_LEDGER_ROW.json",
    "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_CORPUS_DELTA.json",
    "HASH_MANIFEST.json",
    "LINE_ENDING_REPORT.json",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def setup_module() -> None:
    subprocess.run([sys.executable, str(SCRIPT)], cwd=REPO_ROOT, check=True)


def test_required_artifacts_and_decision_status() -> None:
    published = {path.name for path in OUTPUT_ROOT.iterdir() if path.is_file()}
    decision = load_json(OUTPUT_ROOT / "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_DECISION.json")

    assert REQUIRED_ARTIFACTS <= published
    assert decision["package_id"] == "MAIN-CITYBRAIN-EPOCH3-L2-R2-FORECAST-AUTHORITY-PREFLIGHT-R1"
    assert decision["status"] == EXPECTED_STATUS
    assert decision["blockers"] == []
    assert decision["forecast_model_created"] is False
    assert decision["learned_predictor_created"] is False
    assert decision["model_authority_granted_by_codex"] is False
    assert decision["human_authority_required"] is True
    assert decision["same_run_model_start_allowed"] is False


def test_r2_label_materialization_scales_r1_and_preserves_lineage() -> None:
    rows = load_jsonl(OUTPUT_ROOT / "E3_L2_BACKFILL_R2_GOVERNED_LABEL_ROWS.jsonl")
    materialization = load_json(OUTPUT_ROOT / "E3_L2_BACKFILL_R2_LABEL_MATERIALIZATION_REPORT.json")
    city_stats = load_json(OUTPUT_ROOT / "E3_L2_BACKFILL_R2_PER_CITY_LABEL_STATS.json")
    time_stats = load_json(OUTPUT_ROOT / "E3_L2_BACKFILL_R2_TIME_STRATIFICATION_STATS.json")
    refs = [ref for row in rows for ref in row["derived_from_source_refs"]]

    assert len(rows) == materialization["materialized_rows"]
    assert len(rows) > materialization["r1_materialized_rows"]
    assert len(rows) >= 10_000
    assert materialization["source_class"] == "derived_field"
    assert materialization["single_snapshot_rows_converted"] == 0
    assert materialization["model_allowed"] is False
    assert city_stats["cities"]["NYC"]["rows"] > city_stats["cities"]["London"]["rows"]
    assert city_stats["cities"]["NYC"]["stalled"] > 0
    assert city_stats["cities"]["London"]["stalled"] > 0
    assert time_stats["quarter_count"] >= 4
    assert any("nyc_dob_now_build_filings" in ref for ref in refs)
    assert any("nyc_dob_permit_issuance" in ref for ref in refs)
    assert any("lon_d5_pld_planning_ingest" in ref for ref in refs)

    required = {
        "label_row_id",
        "target_id",
        "city",
        "source_system",
        "entity_ref",
        "transition_sequence_ref",
        "observation_window_start",
        "observation_window_end",
        "as_of_date",
        "label",
        "label_bool",
        "stall_threshold_days",
        "source_class",
        "derived_from_source_refs",
        "lineage_complete",
        "temporal_split",
        "training_allowed",
        "model_allowed",
    }
    splits = {row["temporal_split"] for row in rows}
    for row in rows[:50]:
        assert required <= set(row)
        assert row["target_id"] == "permit_stall_v0"
        assert row["source_class"] == "derived_field"
        assert row["lineage_complete"] is True
        assert row["model_allowed"] is False
        assert len(row["derived_from_source_refs"]) >= 2
        assert date.fromisoformat(row["observation_window_start"]) <= date.fromisoformat(row["as_of_date"])
        assert date.fromisoformat(row["as_of_date"]) <= date.fromisoformat(row["observation_window_end"])
        assert row["label_bool"] == (row["label"] == "stalled")
        assert row["label_bool"] == (row["observation_window_days"] >= row["stall_threshold_days"])
    assert {"train_reference", "eval", "holdout"} <= splits


def test_integrity_and_no_fabrication_audit_are_green() -> None:
    rows = load_jsonl(OUTPUT_ROOT / "E3_L2_BACKFILL_R2_GOVERNED_LABEL_ROWS.jsonl")
    integrity = load_json(OUTPUT_ROOT / "E3_L2_BACKFILL_R2_TRANSITION_SEQUENCE_INTEGRITY_REPORT.json")
    audit = load_json(OUTPUT_ROOT / "E3_L2_R2_SOURCE_CLASS_NO_FABRICATION_AUDIT.json")

    assert integrity["status"] == "PASS"
    assert integrity["checked_sequences"] == len(rows)
    assert integrity["out_of_order_count"] == 0
    assert integrity["duplicate_transition_count"] == 0
    assert integrity["phantom_stall_risk_count"] == 0
    assert integrity["single_snapshot_conversion_count"] == 0
    assert audit["status"] == "PASS"
    assert audit["label_rows_checked"] == len(rows)
    assert audit["fabricated_transition_count"] == 0
    assert audit["single_snapshot_rows_converted"] == 0
    assert audit["source_class_allowed"] == ["derived_field"]


def test_corrected_metrics_make_accuracy_descriptive_only() -> None:
    criteria = load_json(OUTPUT_ROOT / "E3_L2_R2_FORECAST_METRIC_SUCCESS_CRITERIA.json")
    baseline = load_json(OUTPUT_ROOT / "E3_L2_R1_BASELINE_BACKTEST_REPORT_CORRECTED_METRICS.json")

    assert criteria["accuracy_role"] == "descriptive_only_not_success_bar"
    assert "stalled_class_pr_auc" in criteria["primary_success_metrics"]
    assert "recall_at_fixed_precision" in criteria["primary_success_metrics"]
    assert "calibration_error" in criteria["primary_success_metrics"]
    assert "median_useful_lead_time_days" in criteria["primary_success_metrics"]
    assert baseline["status"] == "PASS_CORRECTED_NO_MODEL_BASELINE_WITH_LIMITATIONS"
    assert baseline["accuracy_role"] == "descriptive_only_not_success_bar"
    assert baseline["model_created"] is False
    assert baseline["forecast_model_created"] is False
    assert baseline["forecast_packet_model_output_created"] is False
    assert baseline["no_model_assertion"] is True
    assert "precision" in baseline["stalled_class_metrics"]
    assert "recall" in baseline["stalled_class_metrics"]
    assert "pr_auc_proxy_constant_score" in baseline["pr_auc_or_fixed_precision"]
    assert "brier_score_constant_rate_baseline" in baseline["calibration_metrics"]
    assert "median_useful_lead_time_days" in baseline["lead_time_metrics"]
    assert baseline["temporal_split"]["train_reference_window_before_eval"] is True


def test_human_authority_is_template_only_and_no_model_guard_passes() -> None:
    report = load_json(OUTPUT_ROOT / "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_REPORT.json")
    template = load_json(OUTPUT_ROOT / "E3_L2_R2_HUMAN_AUTHORITY_DECISION_ROW.template.json")
    guard = load_json(OUTPUT_ROOT / "E3_L2_R2_NO_MODEL_GUARD_REPORT.json")
    training_manifest = load_json(OUTPUT_ROOT / "E3_L2_R2_TRAINING_MANIFEST_REQUIREMENTS.json")

    assert report["authority_gate"] == "L2R2_MODEL_AUTHORITY_NOT_GRANTED"
    assert report["human_owned"] is True
    assert report["codex_may_clear"] is False
    assert report["package_creates_model"] is False
    assert report["experimental_authority_if_granted"]["consuming_surfaces"] == []
    assert report["experimental_authority_if_granted"]["product_surface_authority"] is False
    assert report["experimental_authority_if_granted"]["same_run_model_start_allowed"] is False

    assert template["decision_type"] == "L2R2_EXPERIMENTAL_FORECAST_AUTHORITY"
    assert template["approver_ref"] == "<human-required>"
    assert template["decision"] == "DEFERRED"
    assert template["consuming_surfaces_allowed"] == []
    assert template["same_run_model_start_allowed"] is False
    assert template["release_ledger_row"] is None

    assert training_manifest["model_training_started"] is False
    assert training_manifest["lineage_requirements"]["source_class_required"] == "derived_field"
    assert guard["status"] == "PASS"
    for key in [
        "forecast_model_created",
        "forecast_packet_model_output_created",
        "learned_predictor_created",
        "ranker_created",
        "operator_facing_ranker_created",
        "operator_facing_forecast_surface_created",
        "counterfactual_learner_created",
        "case_memory_learner_created",
        "dynamic_investigation_agent_created",
        "cross_city_learned_transfer_created",
    ]:
        assert guard[key] is False
    assert guard["new_learned_registry_entries"] == 0


def test_corpus_delta_limitations_ledger_hashes_and_schemas() -> None:
    delta = load_json(OUTPUT_ROOT / "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_CORPUS_DELTA.json")
    limitations = load_json(OUTPUT_ROOT / "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_LIMITATIONS.json")
    ledger = load_json(OUTPUT_ROOT / "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_LEDGER_ROW.json")
    manifest = load_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
    line_endings = load_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json")

    assert delta["status"] == "PASS"
    for artifact in [
        "E3_L2_BACKFILL_R2_GOVERNED_LABEL_ROWS.jsonl",
        "E3_L2_R1_BASELINE_BACKTEST_REPORT_CORRECTED_METRICS.json",
        "E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_REPORT.json",
    ]:
        assert artifact in delta["registered_artifacts"]
    assert limitations["status"] == "PASS_WITH_LIMITATIONS"
    assert any("Human authority" in item for item in limitations["limitations"])
    assert ledger["status"] == EXPECTED_STATUS
    assert ledger["no_model"] is True
    assert ledger["model_authority_granted_by_codex"] is False
    assert line_endings["status"] == "PASS_LF_STABLE_FOR_E3_L2_R2_FORECAST_AUTHORITY_PREFLIGHT_R1"
    assert line_endings["crlf_paths"] == []
    assert manifest["self_reference_policy"] == "HASH_MANIFEST.json is excluded to avoid recursive hash instability."
    for entry in manifest["files"]:
        path = REPO_ROOT / entry["path"]
        assert path.exists(), entry["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], entry["path"]


def test_package_schemas_validate_publication_samples() -> None:
    schemas = {
        "baseline": REPO_ROOT / "schemas" / "corrected_metric_baseline_report.schema.json",
        "human": REPO_ROOT / "schemas" / "human_authority_decision_row.schema.json",
        "label": REPO_ROOT / "schemas" / "permit_stall_label_row_r2.schema.json",
        "integrity": REPO_ROOT / "schemas" / "transition_sequence_integrity_report.schema.json",
    }
    expected_outputs = REPO_ROOT / "manifests" / "epoch3_l2_r2_forecast_authority_preflight_expected_outputs.json"
    for path in [*schemas.values(), expected_outputs]:
        assert path.exists(), path
        load_json(path)

    jsonschema.validate(
        load_json(OUTPUT_ROOT / "E3_L2_R1_BASELINE_BACKTEST_REPORT_CORRECTED_METRICS.json"),
        load_json(schemas["baseline"]),
    )
    jsonschema.validate(
        load_json(OUTPUT_ROOT / "E3_L2_R2_HUMAN_AUTHORITY_DECISION_ROW.template.json"),
        load_json(schemas["human"]),
    )
    jsonschema.validate(
        load_jsonl(OUTPUT_ROOT / "E3_L2_BACKFILL_R2_GOVERNED_LABEL_ROWS.jsonl")[0],
        load_json(schemas["label"]),
    )
    jsonschema.validate(
        load_json(OUTPUT_ROOT / "E3_L2_BACKFILL_R2_TRANSITION_SEQUENCE_INTEGRITY_REPORT.json"),
        load_json(schemas["integrity"]),
    )
    expected = load_json(expected_outputs)
    assert expected["package_id"] == "MAIN-CITYBRAIN-EPOCH3-L2-R2-FORECAST-AUTHORITY-PREFLIGHT-R1"
    assert set(expected["required_outputs"]) <= REQUIRED_ARTIFACTS

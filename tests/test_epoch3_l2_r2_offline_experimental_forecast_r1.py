from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_epoch3_l2_r2_offline_experimental_forecast_r1.py"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch3_l2_r2_offline_experimental_forecast_r1"
EXPECTED_STATUS = "PASS_E3_L2_R2_OFFLINE_EXPERIMENTAL_FORECAST_R1_WITH_LIMITATIONS"
REQUIRED_ARTIFACTS = {
    "E3_L2_R2_HUMAN_MODEL_AUTHORITY_DECISION_ROW.json",
    "E3_L2_R2_EXPERIMENT_TRAINING_MANIFEST.json",
    "E3_L2_R2_TEMPORAL_LEAKAGE_AUDIT.json",
    "E3_L2_R2_EXPERIMENTAL_FORECAST_MODEL_CARD.json",
    "E3_L2_R2_EXPERIMENTAL_FORECAST_EVAL_REPORT.json",
    "E3_L2_R2_CITY_STRATIFIED_EVAL_REPORT.json",
    "E3_L2_R2_EXPERIMENTAL_FORECAST_REGISTRY_ENTRY.json",
    "E3_L2_R2_EXPERIMENTAL_FORECAST_EVAL_PREDICTIONS.jsonl",
    "E3_L2_R2_NO_PRODUCT_SURFACE_AUDIT.json",
    "E3_L2_R2_NO_FORBIDDEN_CAPABILITY_GUARD.json",
    "E3_L2_R2_OFFLINE_EXPERIMENT_DECISION.json",
    "E3_L2_R2_OFFLINE_EXPERIMENT_LEDGER_ROW.json",
    "E3_L2_R2_LIMITATIONS.json",
    "E3_L2_R2_CORPUS_DELTA.json",
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
    decision = load_json(OUTPUT_ROOT / "E3_L2_R2_OFFLINE_EXPERIMENT_DECISION.json")

    assert REQUIRED_ARTIFACTS <= published
    assert decision["package_id"] == "MAIN-CITYBRAIN-EPOCH3-L2-R2-OFFLINE-EXPERIMENTAL-FORECAST-R1"
    assert decision["status"] == EXPECTED_STATUS
    assert decision["blockers"] == []
    assert decision["forecast_model_created"] is True
    assert decision["product_surface_created"] is False
    assert decision["release_authority_granted"] is False
    assert decision["same_run_release_started"] is False


def test_human_authority_records_user_approval_but_not_codex_grant() -> None:
    authority = load_json(OUTPUT_ROOT / "E3_L2_R2_HUMAN_MODEL_AUTHORITY_DECISION_ROW.json")

    assert authority["decision"] == "APPROVED_OFFLINE_EXPERIMENT_ONLY"
    assert authority["approved_by"] == "USER_EXPLICIT_CHAT_APPROVAL"
    assert authority["approval_date"] == "2026-07-06"
    assert authority["codex_granted_authority"] is False
    assert authority["release_authority_granted"] is False
    assert authority["operator_surface_authority_granted"] is False
    assert authority["allowed_component_kind"] == "forecast_model"
    assert authority["allowed_status"] == "experimental"
    assert authority["allowed_consuming_surfaces"] == []
    assert authority["allowed_scope"]["frozen_replay_only"] is True
    assert authority["allowed_scope"]["product_surface_authority"] is False


def test_training_manifest_and_temporal_leakage_audit_are_frozen_and_lineaged() -> None:
    manifest = load_json(OUTPUT_ROOT / "E3_L2_R2_EXPERIMENT_TRAINING_MANIFEST.json")
    audit = load_json(OUTPUT_ROOT / "E3_L2_R2_TEMPORAL_LEAKAGE_AUDIT.json")

    assert manifest["target_id"] == "permit_stall_v0"
    assert manifest["frozen_replay_only"] is True
    assert manifest["source_label_rows_ref"].endswith("E3_L2_BACKFILL_R2_GOVERNED_LABEL_ROWS.jsonl")
    assert manifest["source_label_rows_hash"]
    assert manifest["split_policy"]["train_precedes_eval"] is True
    assert manifest["surface_policy"]["consuming_surfaces"] == []
    assert manifest["surface_policy"]["product_surface_allowed"] is False
    assert manifest["surface_policy"]["watch_consumption_allowed"] is False
    assert manifest["feature_policy"]["no_terminal_outcome_features"] is True
    assert manifest["feature_policy"]["no_future_state_features"] is True
    assert manifest["label_lineage_coverage"]["rows_with_derived_field_source_class"] == manifest["label_lineage_coverage"]["total_label_rows"]
    assert manifest["label_lineage_coverage"]["rows_with_source_transition_refs"] == manifest["label_lineage_coverage"]["total_label_rows"]
    assert {"NYC", "London"} <= set(manifest["city_stratification"])

    assert audit["status"] == "PASS"
    assert audit["checks"]["train_precedes_eval"] is True
    assert audit["checks"]["eval_precedes_or_is_separate_from_holdout"] is True
    assert audit["checks"]["no_future_state_features"] is True
    assert audit["checks"]["no_terminal_outcome_features"] is True
    assert audit["checks"]["no_single_snapshot_labels"] is True
    assert audit["checks"]["transition_lineage_present"] is True


def test_eval_report_has_corrected_metrics_and_prediction_rows_are_eval_only() -> None:
    eval_report = load_json(OUTPUT_ROOT / "E3_L2_R2_EXPERIMENTAL_FORECAST_EVAL_REPORT.json")
    city_report = load_json(OUTPUT_ROOT / "E3_L2_R2_CITY_STRATIFIED_EVAL_REPORT.json")
    predictions = load_jsonl(OUTPUT_ROOT / "E3_L2_R2_EXPERIMENTAL_FORECAST_EVAL_PREDICTIONS.jsonl")

    assert eval_report["target_id"] == "permit_stall_v0"
    assert eval_report["accuracy_role"] == "descriptive_only_not_success_bar"
    assert eval_report["product_surface_created"] is False
    assert eval_report["operator_facing_forecast_created"] is False
    for key in [
        "stalled_class_average_precision",
        "recall_at_fixed_precision",
        "brier_score",
        "calibration_error",
        "median_useful_lead_time_days",
    ]:
        assert key in eval_report["metrics"]
    assert eval_report["metrics"]["stalled_class_average_precision"] >= 0
    assert "precision_0_50" in eval_report["metrics"]["recall_at_fixed_precision"]
    assert "precision_0_70" in eval_report["metrics"]["recall_at_fixed_precision"]
    assert {"NYC", "London"} <= set(eval_report["city_stratified_metrics"])
    assert city_report["city_stratified_metrics"] == eval_report["city_stratified_metrics"]
    assert eval_report["baseline_comparison"]

    assert predictions
    for row in predictions[:100]:
        assert row["source_class"] == "model_experiment_output"
        assert row["surface_allowed"] is False
        assert row["review_only"] is True
        assert row["evaluation_only"] is True
        assert row["temporal_split"] == "eval"
        assert 0 <= row["score"] <= 1
    assert sum(1 for row in predictions if row["surface_allowed"]) == 0


def test_registry_entry_and_surface_guards_allow_exactly_one_experimental_forecast_only() -> None:
    model_card = load_json(OUTPUT_ROOT / "E3_L2_R2_EXPERIMENTAL_FORECAST_MODEL_CARD.json")
    registry = load_json(OUTPUT_ROOT / "E3_L2_R2_EXPERIMENTAL_FORECAST_REGISTRY_ENTRY.json")
    surface = load_json(OUTPUT_ROOT / "E3_L2_R2_NO_PRODUCT_SURFACE_AUDIT.json")
    guard = load_json(OUTPUT_ROOT / "E3_L2_R2_NO_FORBIDDEN_CAPABILITY_GUARD.json")

    assert model_card["component_id"] == "forecast.permit_stall_v0.r1"
    assert model_card["model_status"] == "experimental"
    assert model_card["consuming_surfaces"] == []
    assert model_card["frozen_replay_only"] is True
    assert model_card["release_ledger_row"] is None

    assert registry["component_kind"] == "forecast_model"
    assert registry["status"] == "experimental"
    assert registry["consuming_surfaces"] == []
    assert registry["frozen_replay_only"] is True
    assert registry["release_ledger_row"] is None
    assert registry["rollback_ref"]
    assert registry["training_manifest_ref"]
    assert registry["eval_refs"]

    assert surface["status"] == "PASS"
    assert surface["allowed_experimental_component_count"] == 1
    assert surface["product_forecast_surface_created"] is False
    assert surface["operator_facing_forecast_created"] is False
    assert surface["watch_family_consumes_model"] is False
    assert surface["product_forecast_packet_created"] is False
    assert surface["prediction_rows_surface_allowed_count"] == 0
    assert surface["consuming_surfaces"] == []

    assert guard["status"] == "PASS"
    assert guard["registered_forecast_model_components"] == 1
    assert guard["forecast_components_with_consuming_surfaces"] == 0
    for key in [
        "ranker_created",
        "operator_facing_ranker_created",
        "counterfactual_learner_created",
        "case_memory_learner_created",
        "dynamic_investigation_agent_created",
        "cross_city_learned_transfer_created",
        "product_forecast_surface_created",
        "operator_facing_forecast_created",
        "watch_family_consumes_model",
        "product_forecast_packet_created",
    ]:
        assert guard[key] is False


def test_corpus_delta_limitations_ledger_hashes_and_line_endings() -> None:
    delta = load_json(OUTPUT_ROOT / "E3_L2_R2_CORPUS_DELTA.json")
    limitations = load_json(OUTPUT_ROOT / "E3_L2_R2_LIMITATIONS.json")
    ledger = load_json(OUTPUT_ROOT / "E3_L2_R2_OFFLINE_EXPERIMENT_LEDGER_ROW.json")
    manifest = load_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
    line_endings = load_json(OUTPUT_ROOT / "LINE_ENDING_REPORT.json")

    assert delta["status"] == "PASS"
    assert "E3_L2_R2_EXPERIMENTAL_FORECAST_EVAL_REPORT.json" in delta["registered_artifacts"]
    assert "E3_L2_R2_EXPERIMENTAL_FORECAST_EVAL_PREDICTIONS.jsonl" in delta["registered_artifacts"]
    assert limitations["status"] == "PASS_WITH_LIMITATIONS"
    assert any("offline experimental" in item for item in limitations["limitations"])
    assert ledger["status"] == EXPECTED_STATUS
    assert ledger["forecast_model_status"] == "experimental"
    assert ledger["product_surface_created"] is False
    assert ledger["release_authority_granted"] is False

    assert line_endings["status"] == "PASS_LF_STABLE_FOR_E3_L2_R2_OFFLINE_EXPERIMENTAL_FORECAST_R1"
    assert line_endings["crlf_paths"] == []
    assert manifest["self_reference_policy"] == "HASH_MANIFEST.json is excluded to avoid recursive hash instability."
    for entry in manifest["files"]:
        path = REPO_ROOT / entry["path"]
        assert path.exists(), entry["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], entry["path"]


def test_package_schemas_validate_key_artifacts() -> None:
    schemas = {
        "authority": REPO_ROOT / "schemas" / "e3_l2_r2_human_authority_decision_row.schema.json",
        "eval": REPO_ROOT / "schemas" / "experimental_forecast_eval_report.schema.json",
        "registry": REPO_ROOT / "schemas" / "experimental_forecast_registry_entry.schema.json",
        "manifest": REPO_ROOT / "schemas" / "l2r2_experiment_training_manifest.schema.json",
    }
    expected_outputs = REPO_ROOT / "manifests" / "epoch3_l2_r2_offline_experimental_forecast_expected_outputs.json"
    for path in [*schemas.values(), expected_outputs]:
        assert path.exists(), path
        load_json(path)

    jsonschema.validate(load_json(OUTPUT_ROOT / "E3_L2_R2_HUMAN_MODEL_AUTHORITY_DECISION_ROW.json"), load_json(schemas["authority"]))
    jsonschema.validate(load_json(OUTPUT_ROOT / "E3_L2_R2_EXPERIMENTAL_FORECAST_EVAL_REPORT.json"), load_json(schemas["eval"]))
    jsonschema.validate(load_json(OUTPUT_ROOT / "E3_L2_R2_EXPERIMENTAL_FORECAST_REGISTRY_ENTRY.json"), load_json(schemas["registry"]))
    jsonschema.validate(load_json(OUTPUT_ROOT / "E3_L2_R2_EXPERIMENT_TRAINING_MANIFEST.json"), load_json(schemas["manifest"]))
    expected = load_json(expected_outputs)
    assert expected["package_id"] == "MAIN-CITYBRAIN-EPOCH3-L2-R2-OFFLINE-EXPERIMENTAL-FORECAST-R1"
    assert set(expected["expected_artifacts"]) == REQUIRED_ARTIFACTS

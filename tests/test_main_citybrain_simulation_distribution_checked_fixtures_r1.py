from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_simulation_distribution_checked_fixtures_r1.py"

spec = importlib.util.spec_from_file_location("distribution_checked_sim", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outputs() -> None:
    if not (runner.DEFAULT_OUT / "DISTRIBUTION_CHECKED_SIMULATION_DECISION.json").exists():
        runner.build(runner.DEFAULT_OUT)


def test_required_outputs_exist():
    runner.build(runner.DEFAULT_OUT)
    assert [runner.rel(path) for path in runner.required_paths(runner.DEFAULT_OUT) if not path.exists()] == []


def test_decision_passes_with_mobility_checked_and_permit_parked():
    ensure_outputs()
    decision = load_json(runner.DEFAULT_OUT / "DISTRIBUTION_CHECKED_SIMULATION_DECISION.json")
    assert decision["status"] == runner.STATUS_PASS
    assert decision["label"] == runner.ALIGNED_LABEL
    assert decision["named_donor_distribution_count"] >= 1
    assert decision["comparison_metric_count"] >= 1
    assert "mobility_access_interruption_v0" in decision["families_checked"]
    assert decision["families_not_checked"][0]["family"] == "permit_inspection_delay"
    assert decision["not_city_calibrated"] is True
    assert decision["not_forecast"] is True
    assert decision["not_operational_prediction"] is True
    assert decision["forecast_packet_created"] is False


def test_aligned_rows_have_named_distribution_and_visible_metric():
    ensure_outputs()
    ledger = runner.read_jsonl(runner.DEFAULT_OUT / "SIM_DONOR_DISTRIBUTION_COMPARISON_LEDGER.jsonl")
    aligned = [row for row in ledger if row["alignment_label"] == runner.ALIGNED_LABEL]
    parked = [row for row in ledger if row["alignment_label"] == runner.NOT_CHECKED_LABEL]
    assert aligned
    assert parked
    for row in aligned:
        assert row["donor_distribution_id"]
        assert row["donor_source_refs"]
        assert row["comparison_metric_name"]
        assert row["comparison_metric_value"] is not None
        assert row["donor_sample_count"] > 0
        assert row["fixture_sample_count"] > 0
        assert row["limitations"]


def test_family_reports_are_separate_and_honest():
    ensure_outputs()
    mobility = load_json(runner.DEFAULT_OUT / "MOBILITY_SIM_DISTRIBUTION_CHECK_REPORT.json")
    permit = load_json(runner.DEFAULT_OUT / "PERMIT_DELAY_SIM_DISTRIBUTION_CHECK_REPORT.json")
    permit_profile = load_json(runner.DEFAULT_OUT / "PERMIT_DELAY_DONOR_SERVICE_TIME_PROFILE.json")
    assert mobility["family"] == "mobility_access_interruption_v0"
    assert mobility["status"] == "CHECKED_WITH_LIMITATIONS"
    assert mobility["fixture_ids_checked"]
    assert permit["family"] == "permit_inspection_delay"
    assert permit["status"] == "PARKED_NOT_DISTRIBUTION_CHECKED"
    assert permit["fixtures_parked"]
    assert permit_profile["profile_status"] == runner.NOT_CHECKED_LABEL


def test_sensitivity_and_guards_preserve_boundaries():
    ensure_outputs()
    sensitivity = load_json(runner.DEFAULT_OUT / "OPTION_RANKING_SENSITIVITY_REPORT.json")
    no_forecast = load_json(runner.DEFAULT_OUT / "NO_FORECAST_SURFACE_GUARD.json")
    no_city = load_json(runner.DEFAULT_OUT / "NO_CITY_CALIBRATION_CLAIM_GUARD.json")
    no_prediction = load_json(runner.DEFAULT_OUT / "NO_OPERATIONAL_PREDICTION_CLAIM_GUARD.json")
    boundary = load_json(runner.DEFAULT_OUT / "BOUNDARY_NO_ACTION_AUDIT.json")
    assert sensitivity["ranking_flip_detected"] is False
    assert len(sensitivity["sensitivity_checks"]) >= 2
    assert no_forecast["no_ForecastPacket"] is True
    assert no_forecast["forecast_packet_created"] is False
    assert no_city["not_city_calibrated"] is True
    assert no_prediction["not_operational_prediction"] is True
    assert boundary["source_truth_mutated"] is False
    assert boundary["official_workflow_case_action_created"] is False
    assert boundary["training_rows_created"] is False


def test_manifest_and_validate_pass():
    ensure_outputs()
    assert runner.verify_manifest(runner.DEFAULT_OUT / "HASH_MANIFEST.sha256") == []
    assert runner.validate(runner.DEFAULT_OUT) == []

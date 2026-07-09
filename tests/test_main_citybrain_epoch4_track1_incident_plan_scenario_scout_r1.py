from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_track1_incident_plan_scenario_scout_r1.py"

spec = importlib.util.spec_from_file_location("track1_scout", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_requested_outputs_exist_and_parse():
    for name in runner.REQUESTED_OUTPUTS:
        path = runner.OUTPUT_ROOT / name
        assert path.exists(), name
        assert load_json(path)


def test_matrix_scores_all_six_candidate_families():
    matrix = load_json(runner.OUTPUT_ROOT / "SCENARIO_SCOUT_MATRIX.json")
    family_ids = {row["family_id"] for row in matrix["families"]}
    assert matrix["status"] == "PASS_WITH_LIMITATIONS"
    assert matrix["parallel_safe"] is True
    assert matrix["foundation_status"]["status"] == "PASS"
    assert family_ids == {
        "mobility_access_interruption",
        "building_compliance_perception_candidate",
        "permit_inspection_delay",
        "civic_service_sensor_anomaly",
        "city_asset_infrastructure_issue",
        "property_planning_development_impact",
    }
    for row in matrix["families"]:
        assert set(runner.CRITERIA).issubset(row["scores"])
        assert row["score_total"] == sum(row["scores"][criterion] for criterion in runner.CRITERIA)


def test_top_three_excludes_mobility_control_and_selects_best_expansions():
    top3 = load_json(runner.OUTPUT_ROOT / "TOP_3_FAMILY_SELECTION.json")
    assert top3["selected_family_ids"] == [
        "building_compliance_perception_candidate",
        "permit_inspection_delay",
        "city_asset_infrastructure_issue",
    ]
    assert top3["control_family"]["family_id"] == "mobility_access_interruption"
    assert "mobility_access_interruption" not in top3["selected_family_ids"]


def test_implementation_order_has_three_actionable_steps():
    order = load_json(runner.OUTPUT_ROOT / "IMPLEMENTATION_ORDER.json")
    assert [step["family_id"] for step in order["steps"]] == [
        "building_compliance_perception_candidate",
        "permit_inspection_delay",
        "city_asset_infrastructure_issue",
    ]
    for step in order["steps"]:
        assert step["first_slice"]
        assert step["exit_gate"]
    assert "mobility_access_interruption" in order["control_first"]


def test_do_not_select_reasoning_covers_remaining_families():
    do_not = load_json(runner.OUTPUT_ROOT / "DO_NOT_SELECT_REASONING.json")
    ids = {row["family_id"] for row in do_not["not_selected"]}
    assert ids == {
        "mobility_access_interruption",
        "civic_service_sensor_anomaly",
        "property_planning_development_impact",
    }
    for row in do_not["not_selected"]:
        assert row["reason"]
        assert row["future_revisit_trigger"]


def test_hash_manifest_and_runner_validation():
    assert runner.verify_manifest() == []
    assert runner.validate_outputs() == []

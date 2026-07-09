from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_track5_data_quality_maturity_dashboard_r1.py"

spec = importlib.util.spec_from_file_location("track5_maturity_dashboard", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_data_quality_dashboard_outputs_validate_cleanly():
    runner.build_outputs()
    assert runner.validate_outputs() == []


def test_dashboard_has_all_required_scorecards():
    dashboard = load_json(runner.OUTPUT_ROOT / "DATA_QUALITY_MATURITY_DASHBOARD_R1.json")
    card_ids = {card["scorecard_id"] for card in dashboard["scorecards"]}
    assert set(runner.SCORECARD_IDS) == card_ids
    assert dashboard["source_count"] > 0
    assert 0 <= dashboard["overall_maturity_score"] <= 100


def test_dashboard_exposes_maturity_weaknesses_as_product_surface():
    dashboard = load_json(runner.OUTPUT_ROOT / "DATA_QUALITY_MATURITY_DASHBOARD_R1.json")
    by_id = {card["scorecard_id"]: card for card in dashboard["scorecards"]}
    assert by_id["identity_ambiguity"]["affected_count"] >= 1
    assert by_id["source_freshness"]["affected_count"] >= 1
    assert by_id["missing_geometry"]["affected_count"] >= 1
    assert by_id["missing_time_history"]["affected_count"] >= 1
    assert by_id["candidate_only_records"]["affected_count"] >= 1


def test_source_scorecards_link_back_to_registry_sources():
    registry = load_json(runner.SOURCE_REGISTRY_PATH)
    source_ids = {source["source_id"] for source in registry["sources"]}
    scorecards = load_json(runner.OUTPUT_ROOT / "DATA_QUALITY_SOURCE_SCORECARDS.json")["source_scorecards"]
    assert scorecards
    assert all(card["source_id"] in source_ids for card in scorecards)
    assert all("flags" in card and "maturity_score" in card for card in scorecards)


def test_check_downgrade_index_and_decision_are_present():
    downgrade_index = load_json(runner.OUTPUT_ROOT / "CHECK_DOWNGRADE_REASON_INDEX.json")
    decision = load_json(runner.OUTPUT_ROOT / "DECISION.json")
    assert downgrade_index["status"] == "PASS_WITH_LIMITATIONS"
    assert downgrade_index["check_files_scanned"] >= 1
    assert decision["status"] == runner.FINAL_STATUS

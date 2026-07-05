from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_main_citybrain_metropolis_vss_bmd45_replay_benchmark_regression_harness_r19.py"
spec = importlib.util.spec_from_file_location("r19_runner", SCRIPT_PATH)
r19 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(r19)


def test_regression_assertions_use_tolerance_bands() -> None:
    baseline = {
        "external_media_refs": 8,
        "frame_count": 8,
        "iou_match_counts": {"0.25": 24, "0.5": 19, "0.75": 8},
        "sensor_candidate_count": 165,
    }

    assertions = r19.regression_assertions(baseline)

    assert assertions["hard_assertions"]["external_media_refs"] == {"expected": 8, "tolerance": 0}
    assert assertions["soft_tolerance_bands"]["sensor_candidate_count"]["min"] < 165
    assert assertions["soft_tolerance_bands"]["sensor_candidate_count"]["max"] > 165
    assert assertions["soft_tolerance_bands"]["iou_matches_0_75"]["min_allowed"] == 0


def test_evaluate_assertions_accepts_in_band_drift() -> None:
    baseline = {
        "external_media_refs": 8,
        "frame_count": 8,
        "iou_match_counts": {"0.25": 24, "0.5": 19, "0.75": 8},
        "sensor_candidate_count": 165,
    }
    assertions = r19.regression_assertions(baseline)
    rerun = {
        "candidate_observation_records": 150,
        "comparison_report": {"metrics": {"matches_at_threshold": {"0.25": 20, "0.5": 15, "0.75": 4}}},
        "rerun_executed": True,
    }

    scorecard, drift_items = r19.evaluate_assertions(baseline, assertions, rerun, [{}] * 8)

    assert scorecard["status"] == "PASS"
    assert drift_items == []


def test_evaluate_assertions_flags_out_of_band_candidate_count() -> None:
    baseline = {
        "external_media_refs": 8,
        "frame_count": 8,
        "iou_match_counts": {"0.25": 24, "0.5": 19, "0.75": 8},
        "sensor_candidate_count": 165,
    }
    assertions = r19.regression_assertions(baseline)
    rerun = {
        "candidate_observation_records": 400,
        "comparison_report": {"metrics": {"matches_at_threshold": {"0.25": 24, "0.5": 19, "0.75": 8}}},
        "rerun_executed": True,
    }

    scorecard, drift_items = r19.evaluate_assertions(baseline, assertions, rerun, [{}] * 8)

    assert scorecard["status"] == "REVIEW_DRIFT"
    assert any(item["assertion"] == "sensor_candidate_count_review_band" for item in drift_items)

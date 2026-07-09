import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_arming_status import evaluate  # noqa: E402


def load(name):
    return json.loads((ROOT / name).read_text())


def report_for(fixture):
    return evaluate(load("manifests/epoch3_arming_manifest.json"), load(f"fixtures/{fixture}"))


def test_day_one_only_arms_safe_work():
    report = report_for("metrics_day_one.json")
    assert "L1.R1_OUTCOME_LEDGER_HARDENING" in report["armed_now"]
    assert "L2.R1_BACKTEST_HARNESS_BUILD" in report["armed_now"]
    assert report["conditionally_armed"]["L1.R3A_OFFLINE_RANKER_EXPERIMENT"]["state"] == "not_armed"
    assert report["conditionally_armed"]["L1.R3B_OPERATOR_FACING_LEARNED_RANKING"]["state"] == "not_armed"
    assert report["conditionally_armed"]["L2.R2_FORECAST_MODEL"]["state"] == "not_armed"


def test_l1_r3a_can_arm_without_operator_facing_r3b():
    report = report_for("metrics_pass_l1_r3a.json")
    assert report["conditionally_armed"]["L1.R3A_OFFLINE_RANKER_EXPERIMENT"]["state"] == "armed"
    assert report["conditionally_armed"]["L1.R3B_OPERATOR_FACING_LEARNED_RANKING"]["state"] == "not_armed"


def test_l1_r3b_arms_when_full_requirements_pass():
    report = report_for("metrics_pass_l1_r3b.json")
    assert report["conditionally_armed"]["L1.R3A_OFFLINE_RANKER_EXPERIMENT"]["state"] == "armed"
    assert report["conditionally_armed"]["L1.R3B_OPERATOR_FACING_LEARNED_RANKING"]["state"] == "armed"


def test_operator_diversity_blocks_ranking():
    report = report_for("metrics_fail_operator_diversity.json")
    failed = report["conditionally_armed"]["L1.R3B_OPERATOR_FACING_LEARNED_RANKING"]["failed_requirement_ids"]
    assert "R3B_OPERATOR_DIVERSITY" in failed


def test_propensity_unknown_blocks_primary_thresholds():
    report = report_for("metrics_fail_propensity_unknown.json")
    failed_a = report["conditionally_armed"]["L1.R3A_OFFLINE_RANKER_EXPERIMENT"]["failed_requirement_ids"]
    failed_b = report["conditionally_armed"]["L1.R3B_OPERATOR_FACING_LEARNED_RANKING"]["failed_requirement_ids"]
    assert "R3A_TOTAL_DISPOSITIONS" in failed_a
    assert "R3B_TOTAL_DISPOSITIONS" in failed_b

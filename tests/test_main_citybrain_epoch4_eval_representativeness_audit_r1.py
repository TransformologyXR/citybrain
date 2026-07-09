from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_epoch4_eval_representativeness_audit_r1"
PUB_ROOT = REPO_ROOT / "publications" / "epoch4" / "main-citybrain-epoch4-eval-representativeness-audit-r1"

REQUIRED_OUTPUTS = [
    "REPRESENTATIVENESS_AUDIT_DECISION.json",
    "MISSING_INPUTS.json",
    "EVAL_CORPUS_INVENTORY.json",
    "FOUNDER_CARD_INVENTORY.json",
    "COVERAGE_AXIS_SCORECARD.json",
    "FAMILY_SCENARIO_COVERAGE_MATRIX.json",
    "SOURCE_CLASS_COVERAGE_MATRIX.json",
    "CHECK_REASON_COVERAGE_MATRIX.json",
    "EVENT_LIFECYCLE_COVERAGE_MATRIX.json",
    "EVIDENCE_DEPTH_COVERAGE_MATRIX.json",
    "SIMULATION_COVERAGE_MATRIX.json",
    "CITY_DOMAIN_COVERAGE_MATRIX.json",
    "SYNTHETIC_DATA_FACTORY_CROSSWALK.json",
    "FOUNDER_CARD_READINESS_CLASSIFICATION.json",
    "REPRESENTATIVENESS_FINDINGS.md",
    "EVAL_EXPANSION_RECOMMENDATION_R1.json",
    "FOUNDER_PROBE_RECOMMENDATION_R1.json",
    "NO_OVERCLAIM_GUARD.json",
    "HASH_MANIFEST.json",
]


def load_json(name: str):
    return json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8-sig"))


def test_required_outputs_exist_parse_and_are_published():
    for name in REQUIRED_OUTPUTS:
        assert (OUTPUT_ROOT / name).exists(), name
        assert (PUB_ROOT / name).exists(), name
        if name.endswith(".json"):
            load_json(name)


def test_decision_readiness_and_counts():
    decision = load_json("REPRESENTATIVENESS_AUDIT_DECISION.json")
    assert decision["status"] == "PASS_MAIN_CITYBRAIN_EPOCH4_EVAL_REPRESENTATIVENESS_AUDIT_R1_WITH_LIMITATIONS"
    assert decision["mode"] == "read_only_audit"
    assert decision["counts"]["eval_cases"] == 48
    assert decision["counts"]["founder_cards"] == 16
    assert decision["counts"]["synthetic_factory_main_acquisition_rows"] == 66737
    assert decision["counts"]["synthetic_seed_entities"] == 144
    assert decision["counts"]["product_event_rows"] == 55
    assert decision["counts"]["runtime_control_room_cards"] == 6
    assert decision["readiness"] == {
        "bounded_internal_regression_ready": True,
        "client_readiness_ready": False,
        "founder_diagnostic_ready": True,
        "founder_product_review_ready": False,
        "learning_readiness_ready": False,
    }
    assert all(decision["acceptance"].values())


def test_eval_and_founder_inventories_cover_expected_shape():
    eval_inv = load_json("EVAL_CORPUS_INVENTORY.json")
    assert eval_inv["case_count"] == 48
    assert eval_inv["family_count"] == 4
    assert eval_inv["case_type_count"] == 12
    assert eval_inv["source_class_counts"] == {"replay": 48}
    assert eval_inv["no_action_boundary_all"] is True
    assert eval_inv["operator_fuel_any"] is False
    assert eval_inv["training_eligible_any"] is False
    assert eval_inv["source_truth_mutated_any"] is False

    founder_inv = load_json("FOUNDER_CARD_INVENTORY.json")
    assert founder_inv["card_count"] == 16
    assert set(founder_inv["scenario_counts"]) == {
        "positive_packet_baseline",
        "negative_no_data",
        "stale_freshness",
        "contradiction_pair",
    }
    assert all(len(matrix) == 4 for matrix in founder_inv["family_scenario_matrix"].values())


def test_coverage_and_crosswalk_capture_synthetic_factory_limits():
    scorecard = load_json("COVERAGE_AXIS_SCORECARD.json")
    axes = scorecard["axes"]
    assert axes["family_coverage"]["score"] == "adequate_for_internal_regression"
    assert axes["scenario_type_coverage"]["score"] == "strong_internal"
    assert axes["check_reason_coverage"]["score"] == "strong_internal"
    assert axes["source_class_coverage"]["score"] == "thin"
    assert axes["synthetic_data_factory_coverage"]["score"] == "partial"
    assert axes["learning_fuel_readiness"]["score"] == "none"

    crosswalk = load_json("SYNTHETIC_DATA_FACTORY_CROSSWALK.json")
    assert crosswalk["synthetic_factory_counts"]["main_acquisition_fuel_rows"] == 66737
    assert crosswalk["synthetic_factory_counts"]["synthetic_seed_entities"] == 144
    assert crosswalk["synthetic_factory_counts"]["control_room_cards"] == 6
    layer_scores = {item["layer"]: item["represented_in_current_eval_founder"] for item in crosswalk["layers"]}
    assert layer_scores["check_fixtures"] == "adequate_for_internal_regression"
    assert layer_scores["control_room_cards"] == "thin"


def test_founder_classification_and_recommendations_are_conservative():
    classification = load_json("FOUNDER_CARD_READINESS_CLASSIFICATION.json")
    assert classification["card_count"] == 16
    assert classification["diagnostic_review_ready_count"] == 16
    assert classification["product_review_ready_count"] == 0
    assert classification["classification_counts"] == {"diagnostic_review_ready": 16}
    assert all(card["weakness_interpretation"] == "card_evidence_incomplete_not_product_failure" for card in classification["cards"])

    eval_reco = load_json("EVAL_EXPANSION_RECOMMENDATION_R1.json")
    assert eval_reco["bounded_internal_regression_ready"] is True
    assert eval_reco["founder_diagnostic_ready"] is True
    assert eval_reco["founder_product_review_ready"] is False
    assert eval_reco["client_readiness_ready"] is False
    assert eval_reco["learning_readiness_ready"] is False

    founder_reco = load_json("FOUNDER_PROBE_RECOMMENDATION_R1.json")
    assert founder_reco["recommendation"] == "PROCEED_TO_FOUNDER_DIAGNOSTIC_REVIEW_NOT_PRODUCT_READINESS_REVIEW"
    assert founder_reco["diagnostic_review_ready"] is True
    assert founder_reco["product_review_ready"] is False


def test_no_overclaim_guard_hashes_and_validate_only():
    guard = load_json("NO_OVERCLAIM_GUARD.json")
    assert guard["status"] == "PASS"
    assert guard["no_forbidden_capability_created"] is True
    assert all(value is False for value in guard["forbidden_capabilities"].values())
    assert guard["operator_fuel_any"] is False
    assert guard["training_eligible_any"] is False
    assert guard["source_truth_mutated_any"] is False

    manifest = load_json("HASH_MANIFEST.json")
    assert manifest["status"] == "PASS"
    assert manifest["file_count"] == len(REQUIRED_OUTPUTS) - 1
    assert {entry["path"] for entry in manifest["entries"]} == set(REQUIRED_OUTPUTS) - {"HASH_MANIFEST.json"}

    result = subprocess.run(
        [sys.executable, "scripts/run_main_citybrain_epoch4_eval_representativeness_audit_r1.py", "--validate-only"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "PASS_MAIN_CITYBRAIN_EPOCH4_EVAL_REPRESENTATIVENESS_AUDIT_R1_WITH_LIMITATIONS" in result.stdout


def test_findings_markdown_states_the_core_answer():
    text = (OUTPUT_ROOT / "REPRESENTATIVENESS_FINDINGS.md").read_text(encoding="utf-8")
    assert "The current 48-case eval corpus is representative enough for bounded internal regression" in text
    assert "not representative enough for founder product-readiness review" in text
    assert "No training rows" in text

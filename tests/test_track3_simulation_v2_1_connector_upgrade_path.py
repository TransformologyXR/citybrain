from __future__ import annotations

import json
from pathlib import Path

from scripts.run_track3_simulation_v2_1_connector_upgrade_path import (
    HONESTY_LABELS,
    OUTPUT_ROOT,
    PASS_STATUS,
    build_outputs,
    sha256_file,
    validate_outputs,
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def setup_module():
    build_outputs()


def test_decision_passes_with_limitations_and_boundaries():
    decision = load_json(OUTPUT_ROOT / "SIMULATION_V2_1_CONNECTOR_UPGRADE_DECISION.json")
    assert decision["status"] == PASS_STATUS
    assert decision["track"] == "Track 3"
    assert decision["parallel_safe_with_event_fabric_v2_1"] is True
    assert decision["blockers"] == []
    checks = decision["contract_check"]
    for key, value in checks.items():
        assert value is True, key


def test_multi_scenario_catalog_and_do_nothing_baselines_cover_each_family():
    catalog = load_json(OUTPUT_ROOT / "MULTI_SCENARIO_CATALOG_V2_1.json")
    baselines = load_json(OUTPUT_ROOT / "DO_NOTHING_BASELINES_BY_FAMILY.json")
    assert catalog["scenario_count"] >= 4
    assert baselines["baseline_count"] == catalog["scenario_count"]
    family_ids = {scenario["family_id"] for scenario in catalog["scenarios"]}
    baseline_family_ids = {baseline["family_id"] for baseline in baselines["baselines"]}
    assert family_ids == baseline_family_ids
    assert {"mobility_access_interruption", "building_compliance_perception_candidate", "permit_inspection_delay", "city_asset_infrastructure_issue"}.issubset(family_ids)
    for scenario in catalog["scenarios"]:
        assert set(["fixture_only", "not_calibrated", "not_product_forecast"]).issubset(set(scenario["honesty_labels"]))
        assert scenario["review_options"]


def test_review_option_comparison_per_family_has_abstain_and_no_authority():
    catalog = load_json(OUTPUT_ROOT / "MULTI_SCENARIO_CATALOG_V2_1.json")
    comparisons = load_json(OUTPUT_ROOT / "REVIEW_OPTION_COMPARISON_BY_FAMILY.json")
    assert comparisons["family_count"] == catalog["scenario_count"]
    for comparison in comparisons["comparisons"]:
        assert comparison["abstain_available"] is True
        assert comparison["recommendation_authority"] is False
        assert comparison["option_count"] >= 3
        for option in comparison["options"]:
            assert option["claim_boundary"] == "review_only_no_action"
            assert option["recommendation_authority"] is False
            assert "not_product_forecast" in option["honesty_labels"]


def test_connector_probes_have_required_honesty_labels():
    sumo = load_json(OUTPUT_ROOT / "SUMO_CONNECTOR_READINESS_PROBE.json")
    cuopt = load_json(OUTPUT_ROOT / "CUOPT_CONNECTOR_READINESS_PROBE.json")
    for probe in [sumo, cuopt]:
        assert probe["status"] == PASS_STATUS
        assert probe["readiness_label"] in {"unavailable", "not_calibrated"}
        assert "not_product_forecast" in probe["honesty_labels"]
        assert "not_calibrated" in probe["honesty_labels"]
        assert probe["real_run_performed"] is False
    assert cuopt["optimizer_authority"] is False


def test_fixture_to_real_ladder_mentions_all_honesty_labels():
    ladder = load_json(OUTPUT_ROOT / "FIXTURE_TO_REAL_CONNECTOR_LADDER.json")
    assert ladder["status"] == PASS_STATUS
    assert ladder["honesty_label_enum"] == HONESTY_LABELS
    step_labels = {step["label"] for step in ladder["ladder_steps"]}
    for label in ["fixture_only", "not_calibrated", "real_run", "not_product_forecast"]:
        assert label in step_labels
    assert any(path["connector_path"] for path in ladder["family_connector_paths"])


def test_scorecard_and_check_validator_keep_simulation_non_forecast():
    scorecard = load_json(OUTPUT_ROOT / "ASSUMPTION_FIDELITY_UNCERTAINTY_SCORECARD.json")
    validator = load_json(OUTPUT_ROOT / "CHECK_SIMULATION_VALIDATOR.json")
    assert scorecard["scenario_count"] == validator["summary"]["scenario_count"]
    for row in scorecard["scorecards"]:
        assert row["calibration_status"] == "not_calibrated"
        assert "not_product_forecast" in row["honesty_labels"]
        assert "product forecast" in row["does_not_prove"]
    assert validator["summary"]["official_action_created_count"] == 0
    assert validator["summary"]["product_forecast_claim_count"] == 0
    assert validator["summary"]["recommendation_authority_count"] == 0
    for row in validator["validation_rows"]:
        assert row["checks"]["has_do_nothing_baseline"] is True
        assert row["checks"]["has_review_options"] is True
        assert row["checks"]["not_product_forecast_visible"] is True


def test_brief_attachment_contains_simulation_summary_and_cannot_claims():
    attachment = load_json(OUTPUT_ROOT / "BRIEF_SIMULATION_ATTACHMENT.json")
    catalog = load_json(OUTPUT_ROOT / "MULTI_SCENARIO_CATALOG_V2_1.json")
    assert attachment["status"] == PASS_STATUS
    assert len(attachment["families"]) == catalog["scenario_count"]
    assert "real_run" in attachment["honesty_labels"]
    assert "fixture_only" in attachment["honesty_labels"]
    assert "unavailable" in attachment["honesty_labels"]
    assert any("product forecast" in claim for claim in attachment["cannot_claim"])
    assert any("official action" in claim for claim in attachment["cannot_claim"])


def test_hash_manifest_and_validate_outputs():
    manifest = load_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
    assert manifest["status"] == "PASS"
    paths = {entry["path"] for entry in manifest["entries"]}
    for name in [
        "MULTI_SCENARIO_CATALOG_V2_1.json",
        "DO_NOTHING_BASELINES_BY_FAMILY.json",
        "REVIEW_OPTION_COMPARISON_BY_FAMILY.json",
        "SUMO_CONNECTOR_READINESS_PROBE.json",
        "CUOPT_CONNECTOR_READINESS_PROBE.json",
        "FIXTURE_TO_REAL_CONNECTOR_LADDER.json",
        "ASSUMPTION_FIDELITY_UNCERTAINTY_SCORECARD.json",
        "CHECK_SIMULATION_VALIDATOR.json",
        "BRIEF_SIMULATION_ATTACHMENT.json",
        "SIMULATION_V2_1_CONNECTOR_UPGRADE_DECISION.json",
        "SUMMARY.md",
    ]:
        assert name in paths
    for entry in manifest["entries"]:
        path = OUTPUT_ROOT / entry["path"]
        assert path.exists()
        assert sha256_file(path) == entry["sha256"]
    assert validate_outputs() == []

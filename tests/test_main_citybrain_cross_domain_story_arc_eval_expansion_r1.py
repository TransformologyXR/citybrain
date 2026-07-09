from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_cross_domain_story_arc_eval_expansion_r1.py"

spec = importlib.util.spec_from_file_location("cross_domain_story", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outputs() -> None:
    if not (runner.DEFAULT_OUT / "CROSS_DOMAIN_STORY_ARC_DECISION.json").exists():
        runner.build(
            runner.DEFAULT_EXPANDED_CORPUS_ROOT,
            runner.DEFAULT_EXPANDED_CADENCE_ROOT,
            runner.DEFAULT_MOBILITY_PACKET_ROOT,
            runner.DEFAULT_SIMULATION_ROOT,
            runner.DEFAULT_OUT,
        )


def test_required_outputs_exist_and_parse():
    runner.build(
        runner.DEFAULT_EXPANDED_CORPUS_ROOT,
        runner.DEFAULT_EXPANDED_CADENCE_ROOT,
        runner.DEFAULT_MOBILITY_PACKET_ROOT,
        runner.DEFAULT_SIMULATION_ROOT,
        runner.DEFAULT_OUT,
    )
    assert [path.name for path in runner.required_paths(runner.DEFAULT_OUT) if not path.exists()] == []
    assert runner.parse_json_and_jsonl(runner.DEFAULT_OUT) == []


def test_decision_passes_with_cross_domain_story_and_eval_counts():
    ensure_outputs()
    decision = load_json(runner.DEFAULT_OUT / "CROSS_DOMAIN_STORY_ARC_DECISION.json")
    assert decision["status"] == runner.STATUS_PASS
    assert decision["next_step_recommendation"] == "GO_FOR_AI_DIAGNOSTIC_STORY_REVIEW"
    assert decision["all_four_canonical_families_participate"] is True
    assert decision["shared_canonical_entity_3plus_gate_met"] is True
    assert decision["mobility_native_packet_participates"] is True
    assert decision["story_r3_local_only"] is False
    assert decision["new_eval_case_count"] >= 112
    assert decision["combined_eval_case_count"] >= 160


def test_entity_report_uses_shared_canonical_not_r3_local_only():
    ensure_outputs()
    entity = load_json(runner.DEFAULT_OUT / "CROSS_DOMAIN_ENTITY_RESOLUTION_REPORT.json")
    assert entity["minimum_gate_met"] is True
    assert entity["not_r3_local_only"] is True
    primary = [row for row in entity["shared_canonical_entities_with_3plus_families"] if row["canonical_entity_ref"] == runner.PRIMARY_SITE]
    assert primary
    assert set(primary[0]["family_ids"]) >= {
        "mobility_access_interruption_v0",
        "building_compliance_perception_candidate",
        "permit_inspection_delay",
    }
    assert any("mobility_access_interruption_v0" in edge["family_ids"] for edge in entity["cross_family_resolution_edges"])
    assert any("permit_inspection_delay" in edge["family_ids"] for edge in entity["cross_family_resolution_edges"])


def test_eval_cases_have_required_distribution_and_answer_key():
    ensure_outputs()
    coverage = load_json(runner.DEFAULT_OUT / "STORY_ARC_EVAL_COVERAGE_SCORECARD.json")
    cases = runner.read_jsonl(runner.DEFAULT_OUT / "STORY_ARC_EVAL_EXPANSION_CASES.jsonl")
    negative = runner.read_jsonl(runner.DEFAULT_OUT / "STORY_ARC_NEGATIVE_CHALLENGE_CASES.jsonl")
    answer_key = load_json(runner.DEFAULT_OUT / "STORY_ARC_EVAL_ANSWER_KEY.json")
    assert coverage["new_eval_case_count"] == len(cases)
    assert coverage["new_eval_case_count"] >= 112
    assert coverage["each_family_has_20plus_cases"] is True
    assert coverage["cross_family_case_count"] >= 20
    assert all(coverage["minimum_distribution_met"].values())
    assert len(negative) >= 16
    assert answer_key["case_count"] == len(cases)
    assert all(case["operator_fuel"] is False and case["training_eligible"] is False and case["founder_session_result"] is False for case in cases)


def test_review_packet_and_truth_manifest_keep_boundaries_closed():
    ensure_outputs()
    truth = load_json(runner.DEFAULT_OUT / "CROSS_DOMAIN_STORY_TRUTH_MANIFEST.json")
    packet = load_json(runner.DEFAULT_OUT / "STORY_ARC_REVIEW_PACKET_360.json")
    causal = load_json(runner.DEFAULT_OUT / "CROSS_FAMILY_CAUSAL_LINK_LEDGER.json")
    assert truth["all_four_canonical_families_participate"] is True
    assert packet["review_status"] == "ai_diagnostic_review_ready_with_limitations"
    assert packet["product_review_ready"] is False
    assert packet["client_ready"] is False
    assert "no ForecastPacket" in packet["simulation_context"]["limitations"]
    assert causal["causal_claim_strength"] == "review_story_hypothesis_not_proven_causality"


def test_guards_manifest_publication_and_validate():
    ensure_outputs()
    fuel = load_json(runner.DEFAULT_OUT / "NO_FOUNDER_SESSION_FUEL_GUARD.json")
    client = load_json(runner.DEFAULT_OUT / "NO_PRODUCT_CLIENT_READY_CLAIM_GUARD.json")
    forecast = load_json(runner.DEFAULT_OUT / "NO_FORECAST_ACTION_GUARD.json")
    source = load_json(runner.DEFAULT_OUT / "NO_SOURCE_TRUTH_MUTATION_GUARD.json")
    assert fuel["founder_session_results_created"] is False
    assert fuel["operator_fuel_created"] is False
    assert fuel["training_rows_created"] is False
    assert client["product_review_ready"] is False
    assert client["client_ready"] is False
    assert forecast["forecast_packet_created"] is False
    assert forecast["official_workflow_case_action_created"] is False
    assert source["source_truth_mutated"] is False
    assert runner.verify_manifest(runner.DEFAULT_OUT / "HASH_MANIFEST.sha256") == []
    assert (runner.PUBLICATION_ROOT / "CROSS_DOMAIN_STORY_ARC_DECISION.json").exists()
    assert runner.validate(runner.DEFAULT_OUT) == []

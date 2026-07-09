from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_founder_probe_evidence_repair_sequence_r1.py"

spec = importlib.util.spec_from_file_location("founder_probe_evidence_repair", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def csv_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def ensure_outputs() -> None:
    if not (runner.OUTPUT_ROOT / "FOUNDER_PROBE_EVIDENCE_REPAIR_DECISION.json").exists():
        runner.build_repair_sequence()


def test_required_outputs_and_publication_exist():
    runner.build_repair_sequence()
    assert [runner.rel(path) for path in runner.required_paths() if not path.exists()] == []
    assert [runner.rel(path) for path in runner.publication_paths() if not path.exists()] == []


def test_r3_cards_index_and_prefilled_csv_exist():
    ensure_outputs()
    markdown_cards = sorted((runner.OUTPUT_ROOT / "review_cards_r3").glob("founder-probe-r2-*.md"))
    json_cards = sorted((runner.OUTPUT_ROOT / "review_cards_r3").glob("founder-probe-r2-*.json"))
    rows = csv_rows(runner.OUTPUT_ROOT / "FOUNDER_PROBE_RESPONSE_TEMPLATE_PREFILLED_R3.csv")
    assert len(markdown_cards) == 16
    assert len(json_cards) == 16
    assert len(rows) == 16
    assert (runner.OUTPUT_ROOT / "FOUNDER_PROBE_REVIEW_INDEX_R3.html").exists()
    assert (runner.OUTPUT_ROOT / "FOUNDER_PROBE_REVIEW_INDEX_R3.md").exists()
    for row in rows:
        assert row["reviewer_id_or_alias"] == "Hazem"
        assert row["reviewer_type"] == "founder_internal"
        for field in runner.REVIEW_FIELDS:
            assert row[field] == ""


def test_mobility_cards_have_review_packet_backfill_and_cer_seg_context():
    ensure_outputs()
    cards = [load_json(path) for path in sorted((runner.OUTPUT_ROOT / "review_cards_r3").glob("founder-probe-r2-*.json"))]
    mobility = [card for card in cards if card["family"] == "mobility_access_interruption_v0"]
    assert len(mobility) == 4
    for card in mobility:
        evidence = card["review_packet_evidence_status"]
        assert evidence["review_packet_360_family_evidence_present"] is True
        assert evidence["backfill_label"] == "derived_review_packet_backfill_not_source_truth"
        assert card["cer_seg_context_r3"]["cer_context_missing"] is False
        assert card["cer_seg_context_r3"]["seg_context_missing"] is False


def test_actual_outcome_fields_exist_for_all_cards_and_special_scenarios():
    ensure_outputs()
    cards = [load_json(path) for path in sorted((runner.OUTPUT_ROOT / "review_cards_r3").glob("founder-probe-r2-*.json"))]
    for card in cards:
        outcome = card["actual_outcome_block"]
        assert outcome["expected_check_outcome"]
        assert outcome["matched_actual_check_outcome"]
        assert outcome["actual_outcome_source_artifact"]
        assert outcome["actual_outcome_match_status"] in {"matched_direct_check_harness", "matched_challenge_boundary"}
        assert outcome["actual_outcome_limitations"]
    for scenario in ["negative_no_data", "stale_freshness", "contradiction_pair"]:
        scenario_cards = [card for card in cards if card["scenario"] == scenario]
        assert scenario_cards
        assert all(card["actual_outcome_block"]["actual_outcome_match_status"] in {"matched_direct_check_harness", "matched_challenge_boundary"} for card in scenario_cards)


def test_explanation_blocks_and_regression_report_cover_second_reviewer_issues():
    ensure_outputs()
    cards = [load_json(path) for path in sorted((runner.OUTPUT_ROOT / "review_cards_r3").glob("founder-probe-r2-*.json"))]
    for card in cards:
        blocks = card["explanation_blocks"]
        assert blocks["what_this_case_is_testing"]
        assert blocks["what_citybrain_can_say"]
        assert blocks["what_citybrain_cannot_claim"]
        assert blocks["why_check_passed_downgraded_abstained_or_held"]
        assert blocks["what_founder_should_judge"]
    contradiction = [card for card in cards if card["scenario"] == "contradiction_pair"]
    assert all("conflicting evidence" in card["explanation_blocks"]["why_check_passed_downgraded_abstained_or_held"].lower() for card in contradiction)
    regression = load_json(runner.OUTPUT_ROOT / "SECOND_REVIEWER_ISSUE_REGRESSION_REPORT.json")
    assert regression["all_required_regressions_passed"] is True


def test_guards_decision_and_manifest_validate():
    ensure_outputs()
    decision = load_json(runner.OUTPUT_ROOT / "FOUNDER_PROBE_EVIDENCE_REPAIR_DECISION.json")
    no_session = load_json(runner.OUTPUT_ROOT / "NO_SESSION_NO_FUEL_GUARD.json")
    source_guard = load_json(runner.OUTPUT_ROOT / "NO_SOURCE_TRUTH_MUTATION_GUARD.json")
    forbidden = load_json(runner.OUTPUT_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json")
    assert decision["status"] == runner.STATUS
    assert decision["session_results_created"] is False
    assert decision["operator_fuel_created"] is False
    assert decision["training_rows_created"] is False
    assert decision["source_truth_mutated"] is False
    assert no_session["session_results_created"] is False
    assert no_session["operator_fuel_created"] is False
    assert source_guard["source_truth_mutated"] is False
    assert source_guard["canonical_truth_mutated"] is False
    assert forbidden["forbidden_capabilities_created"] == []
    assert runner.verify_manifest(runner.OUTPUT_ROOT / "HASH_MANIFEST.json") == []
    assert runner.validate_all() == []

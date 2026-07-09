from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_story_arc_founder_diagnostic_prep_concordance_r1.py"

spec = importlib.util.spec_from_file_location("founder_diag_prep_concordance", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outputs() -> None:
    if not (runner.DEFAULT_OUT / "STORY_ARC_FOUNDER_DIAGNOSTIC_PREP_CONCORDANCE_DECISION.json").exists():
        runner.build(runner.DEFAULT_STORY_ROOT, runner.DEFAULT_REVIEW_ROOT, runner.DEFAULT_REPAIR_ROOT, runner.DEFAULT_OUT)


def test_required_outputs_exist_and_validate():
    runner.build(runner.DEFAULT_STORY_ROOT, runner.DEFAULT_REVIEW_ROOT, runner.DEFAULT_REPAIR_ROOT, runner.DEFAULT_OUT)
    assert [path.name for path in runner.required_paths(runner.DEFAULT_OUT) if not path.exists()] == []
    assert runner.validate(runner.DEFAULT_OUT) == []


def test_review_provenance_imports_chatgpt_and_claude_artifact_review():
    ensure_outputs()
    ledger = load_json(runner.DEFAULT_OUT / "AI_REVIEW_PROVENANCE_LEDGER.json")
    rows = {row["review_id"]: row for row in ledger["rows"]}
    assert ledger["valid_chatgpt_review_imported"] is True
    assert ledger["valid_claude_independent_artifact_review_imported"] is True
    assert rows["claude_independent_artifact_review_r1"]["independent_artifact_review"] is True
    assert rows["claude_independent_artifact_review_r1"]["review_of_review"] is False
    assert rows["claude_independent_artifact_review_r1"]["count_toward_concordance"] is True
    assert rows["claude_review_of_review_r0"]["count_toward_concordance"] is False
    assert ledger["review_of_review_excluded_from_concordance"] is True


def test_concordance_has_agreements_and_disagreements():
    ensure_outputs()
    report = load_json(runner.DEFAULT_OUT / "AI_REVIEW_CONCORDANCE_REPORT.json")
    assert report["concordance_ready"] is True
    assert report["countable_ai_artifact_review_count"] == 2
    assert any("pass with limitations" in item.lower() for item in report["agreements"])
    assert any("eval count framing" in item.lower() for item in report["disagreements_or_repair_items"])
    assert report["founder_product_review_recommendation"] == "NO_GO"


def test_eval_count_framing_repairs_subset_and_no_190_claim():
    ensure_outputs()
    count = load_json(runner.DEFAULT_OUT / "EVAL_COUNT_FRAMING_REPAIR.json")
    assert count["story_arc_unique_eval_cases"] == 120
    assert count["story_arc_challenge_negative_cases"] == 70
    assert count["challenge_cases_are_subset_of_unique_eval_cases"] is True
    assert count["story_arc_additive_eval_count"] == 120
    assert count["story_arc_not_120_plus_70"] is True
    assert count["forbidden_190_case_claim_created"] is False
    assert count["prior_eval_cases_discovered"] is True
    assert count["prior_eval_case_count"] == 48
    assert count["combined_unique_eval_case_count"] == 168


def test_founder_cards_are_product_judgment_not_evidence_audit():
    ensure_outputs()
    cards = load_json(runner.DEFAULT_OUT / "FOUNDER_DIAGNOSTIC_PRODUCT_JUDGMENT_CARDS.json")
    assert cards["card_count"] >= 6
    assert cards["cards_are_product_judgment_usefulness_cards"] is True
    assert cards["cards_are_evidence_audit_cards"] is False
    assert all(card["not_evidence_audit_card"] is True for card in cards["rows"])
    assert any("useful" in card["question"].lower() for card in cards["rows"])
    assert any("real product context" in card["question"].lower() for card in cards["rows"])
    with (runner.DEFAULT_OUT / "FOUNDER_DIAGNOSTIC_RESPONSE_TEMPLATE.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == cards["card_count"]
    assert all(row["operator_fuel"] == "false" and row["training_eligible"] == "false" for row in rows)


def test_readiness_gate_and_boundaries_keep_product_review_closed():
    ensure_outputs()
    decision = load_json(runner.DEFAULT_OUT / "STORY_ARC_FOUNDER_DIAGNOSTIC_PREP_CONCORDANCE_DECISION.json")
    gate = load_json(runner.DEFAULT_OUT / "FOUNDER_DIAGNOSTIC_READINESS_GATE.json")
    boundary = load_json(runner.DEFAULT_OUT / "BOUNDARY_AND_NO_FUEL_GUARD.json")
    false_guard = load_json(runner.DEFAULT_OUT / "NO_FALSE_CONCORDANCE_GUARD.json")
    assert decision["status"] == runner.STATUS_PASS
    assert decision["final_decision"] == runner.FINAL_GO
    assert gate["founder_diagnostic_review_allowed_with_limitations"] is True
    assert gate["founder_product_review_allowed"] is False
    assert gate["product_review_ready"] is False
    assert gate["client_ready"] is False
    assert false_guard["status"] == "PASS"
    assert false_guard["false_second_ai_review_count_created"] is False
    assert boundary["founder_session_results_created"] is False
    assert boundary["operator_fuel_created"] is False
    assert boundary["training_rows_created"] is False
    assert boundary["forecast_packet_created"] is False
    assert boundary["source_truth_mutated"] is False
    assert boundary["product_ready_claim_created"] is False
    assert boundary["client_ready_claim_created"] is False
    assert runner.verify_manifest(runner.DEFAULT_OUT / "HASH_MANIFEST.json") == []

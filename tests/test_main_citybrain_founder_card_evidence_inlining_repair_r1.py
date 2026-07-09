from __future__ import annotations

import csv
import importlib.util
import json
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_founder_card_evidence_inlining_repair_r1.py"

spec = importlib.util.spec_from_file_location("founder_card_inline", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outputs() -> None:
    if not (runner.OUT / "FOUNDER_CARD_REPAIR_DECISION.json").exists():
        runner.build(runner.OUT)


def test_required_outputs_exist_and_validate():
    runner.build(runner.OUT)
    missing = [name for name in runner.REQUIRED if not (runner.OUT / name).exists()]
    assert missing == []
    assert runner.validate(runner.OUT) == []


def test_at_least_ten_cards_and_two_layout_types():
    ensure_outputs()
    decision = load_json(runner.OUT / "FOUNDER_CARD_REPAIR_DECISION.json")
    index = load_json(runner.OUT / "FOUNDER_CARD_EVIDENCE_INLINE_INDEX.json")
    assert decision["status"] == runner.STATUS_PASS
    assert decision["founder_reviewable_surface_ready_with_limitations"] is True
    assert decision["reading_the_card_is_the_review"] is True
    assert index["card_count"] >= 10
    card_types = {card["card_type"] for card in index["cards"]}
    assert "cross_domain_story_card" in card_types
    assert "single_family_example_card" in card_types


def test_inline_evidence_notes_have_required_fields():
    ensure_outputs()
    extraction = load_json(runner.OUT / "FOUNDER_CARD_EVIDENCE_EXTRACTION_LEDGER.json")
    index = load_json(runner.OUT / "FOUNDER_CARD_EVIDENCE_INLINE_INDEX.json")
    assert extraction["note_count"] >= index["card_count"]
    for card in index["cards"]:
        assert card["evidence_notes_inline_count"] >= 1
        assert card["founder_reviewable"] is True
    for row in extraction["rows"]:
        assert row["displayed_source_ref"]
        assert row["displayed_note_text"]
        assert row["source_path"]
        assert row["source_truth_mutated"] is False


def test_founder_path_has_no_technical_terms_or_weak_pointer_phrases():
    ensure_outputs()
    text = runner.main_path_text(runner.OUT)
    assert runner.technical_hits(text) == []
    for phrase in ["1 supporting source note", "place context", "same site may be related"]:
        assert phrase not in text.lower()
    assert "Source note:" in text
    assert "Source class" in text
    assert "Freshness" in text
    assert "Place/entity" in text
    assert "Outcome" in text


def test_primary_decision_field_and_response_csv_boundaries():
    ensure_outputs()
    guard = load_json(runner.OUT / "FOUNDER_CARD_DECISION_FIELD_GUARD.json")
    assert guard["status"] == "PASS"
    html = (runner.OUT / "FOUNDER_STORY_CARDS_EVIDENCE_INLINE.html").read_text(encoding="utf-8")
    assert html.index("Your call") < html.index("Usefulness 1 2 3 4 5")
    rows = list(csv.DictReader(StringIO((runner.OUT / "FOUNDER_DIAGNOSTIC_RESPONSE_TEMPLATE_INLINE.csv").read_text(encoding="utf-8"))))
    assert rows
    for row in rows:
        assert row["founder_decision"] == ""
        assert row["founder_internal"] == "true"
        assert row["operator_fuel"] == "false"
        assert row["training_eligible"] == "false"
        assert row["external_operator_validation"] == "false"
        assert row["product_review_ready"] == "false"
        assert row["client_ready"] == "false"


def test_audits_boundaries_manifest_and_publication():
    ensure_outputs()
    boilerplate = load_json(runner.OUT / "FOUNDER_CARD_BOILERPLATE_AUDIT.json")
    terms = load_json(runner.OUT / "FOUNDER_CARD_TECHNICAL_TERM_GUARD.json")
    boundary = load_json(runner.OUT / "FOUNDER_CARD_BOUNDARY_GUARD.json")
    missing = load_json(runner.OUT / "FOUNDER_CARD_MISSING_FIELD_LEDGER.json")
    assert boilerplate["status"] == "PASS"
    assert terms["status"] == "PASS"
    assert terms["technical_terms_present"] == []
    assert missing["missing_or_thin_field_count"] > 0
    assert boundary["status"] == "PASS"
    assert boundary["founder_session_result_created"] is False
    assert boundary["operator_fuel"] is False
    assert boundary["training_eligible"] is False
    assert boundary["source_truth_mutated"] is False
    assert runner.verify_manifest(runner.OUT / "HASH_MANIFEST.json") == []
    assert (runner.PUB / "FOUNDER_REVIEW_START_HERE_INLINE.html").exists()

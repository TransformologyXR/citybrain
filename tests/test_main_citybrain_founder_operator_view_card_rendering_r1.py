from __future__ import annotations

import csv
import importlib.util
import json
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_founder_operator_view_card_rendering_r1.py"

spec = importlib.util.spec_from_file_location("operator_view_rendering", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outputs() -> None:
    if not (runner.OUT / "FOUNDER_OPERATOR_RENDERING_GUARD.json").exists():
        runner.build(runner.OUT)


def test_required_outputs_exist_and_validate():
    runner.build(runner.OUT)
    missing = [name for name in runner.REQUIRED if not (runner.OUT / name).exists()]
    assert missing == []
    assert runner.validate(runner.OUT) == []


def test_operator_cards_are_decision_first_and_self_contained():
    ensure_outputs()
    payload = load_json(runner.OUT / "FOUNDER_OPERATOR_STORY_CARDS_INLINE.json")
    assert payload["status"] == runner.STATUS_PASS
    cards = payload["cards"]
    assert len(cards) >= 10
    assert {card["card_type"] for card in cards} >= {"cross_domain_story", "single_family_example"}
    for card in cards:
        assert card["audience"] == "operator_view"
        assert card["operator_verdict_suggestion"] in {"watch_this", "ignore_for_now", "need_more_before_deciding"}
        assert card["verdict_line"].startswith("Verdict:")
        assert card["what_where_line"]
        assert card["so_what_line"].startswith("So what:")
        assert card["suggested_review_next_step"]
        assert " - " in card["confidence_plain_english"]
        assert card["evidence_snapshot"]
        assert card["decision_options"] == ["watch_this", "ignore_for_now", "need_more_before_deciding"]


def test_inline_evidence_and_place_anchor_coverage_pass():
    ensure_outputs()
    coverage = load_json(runner.OUT / "FOUNDER_OPERATOR_CARD_EVIDENCE_INLINE_COVERAGE.json")
    place = load_json(runner.OUT / "FOUNDER_OPERATOR_PLACE_ANCHOR_COVERAGE.json")
    confidence = load_json(runner.OUT / "FOUNDER_OPERATOR_CONFIDENCE_LANGUAGE_REPORT.json")
    assert coverage["status"] == "PASS"
    assert place["status"] == "PASS"
    assert confidence["status"] == "PASS"
    for row in coverage["rows"]:
        assert row["has_source_note_text"] is True
        assert row["has_source_class"] is True
        assert row["has_freshness_or_timestamp"] is True
        assert row["has_place_anchor"] is True
        assert row["has_primary_decision"] is True
    for row in place["rows"]:
        assert row["human_label"]


def test_main_path_has_no_placeholder_phrases_or_technical_terms():
    ensure_outputs()
    text = runner.main_path_text(runner.OUT)
    assert runner.technical_hits(text) == []
    for phrase in runner.FORBIDDEN_PLACEHOLDERS:
        assert phrase not in text.lower()
    assert "Source note:" in text
    assert "Confidence" in text
    assert "Suggested review next step" in text
    assert "Your decision" in text
    assert text.index("Your decision") < text.index("Usefulness 1 2 3 4 5")


def test_response_template_and_boundaries():
    ensure_outputs()
    rows = list(csv.DictReader(StringIO((runner.OUT / "FOUNDER_OPERATOR_RESPONSE_TEMPLATE.csv").read_text(encoding="utf-8"))))
    assert rows
    assert list(rows[0].keys()) == [
        "card_id",
        "card_type",
        "audience",
        "operator_decision",
        "usefulness_1_to_5",
        "readability_1_to_5",
        "trust_1_to_5",
        "what_would_make_this_confident",
        "is_this_card_for_operator_manager_public_or_none",
        "free_text_notes",
        "founder_internal_diagnostic_only",
        "operator_fuel",
        "training_eligible",
        "external_operator_validation",
        "product_review_ready",
        "client_ready",
    ]
    for row in rows:
        assert row["audience"] == "operator_view"
        assert row["operator_decision"] == ""
        assert row["founder_internal_diagnostic_only"] == "true"
        assert row["operator_fuel"] == "false"
        assert row["training_eligible"] == "false"
        assert row["external_operator_validation"] == "false"
        assert row["product_review_ready"] == "false"
        assert row["client_ready"] == "false"


def test_guard_audience_backlogs_manifest_and_publication():
    ensure_outputs()
    guard = load_json(runner.OUT / "FOUNDER_OPERATOR_RENDERING_GUARD.json")
    audience = load_json(runner.OUT / "FOUNDER_OPERATOR_AUDIENCE_FIT_REPORT.json")
    assert guard["status"] == "PASS"
    assert guard["decision_status"] == runner.STATUS_PASS
    assert guard["founder_internal_diagnostic_only"] is True
    assert guard["operator_fuel_created"] is False
    assert guard["training_rows_created"] is False
    assert guard["external_operator_validation_created"] is False
    assert guard["product_review_ready_claim"] is False
    assert guard["client_ready_claim"] is False
    assert guard["official_action_created"] is False
    assert guard["source_truth_mutated"] is False
    assert guard["main_path_uses_operator_view_only"] is True
    assert guard["manager_view_built"] is False
    assert guard["public_human_view_built"] is False
    assert audience["built_audience"] == "operator_view"
    assert audience["manager_rollup_view_built"] is False
    assert audience["public_human_view_built"] is False
    manager = (runner.OUT / "MANAGER_ROLLUP_VIEW_BACKLOG.md").read_text(encoding="utf-8").lower()
    public = (runner.OUT / "PUBLIC_HUMAN_VIEW_BACKLOG.md").read_text(encoding="utf-8").lower()
    for word in ["counts", "clusters", "oldest", "risk", "trend", "confidence distribution"]:
        assert word in manager
    for word in ["plain meaning", "location anchor", "what is not confirmed", "resident", "zero internal system vocabulary"]:
        assert word in public
    assert runner.verify_manifest(runner.OUT / "HASH_MANIFEST.json") == []
    assert (runner.PUB / "FOUNDER_OPERATOR_REVIEW_START_HERE.html").exists()

from __future__ import annotations

import csv
import importlib.util
import json
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_founder_grade_story_materialization_r1.py"

spec = importlib.util.spec_from_file_location("founder_grade_materialization", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outputs() -> None:
    if not (runner.OUT / "FOUNDER_GRADE_STORY_MATERIALIZATION_DECISION.json").exists():
        runner.build(runner.OUT)


def test_required_outputs_exist_and_validate():
    runner.build(runner.OUT)
    missing = [name for name in runner.REQUIRED if not (runner.OUT / name).exists()]
    assert missing == []
    assert runner.validate(runner.OUT) == []


def test_decision_status_and_pass_count_gates():
    ensure_outputs()
    decision = load_json(runner.OUT / "FOUNDER_GRADE_STORY_MATERIALIZATION_DECISION.json")
    assert decision["status"] in runner.ALLOWED_STATUSES
    if decision["status"] == runner.STATUS_PASS:
        assert decision["main_story_count"] >= runner.PASS_BAR["minimum_founder_grade_stories"]
        assert decision["watch_candidate_count"] >= runner.PASS_BAR["minimum_watch_candidates"]
        assert decision["cross_domain_story_count"] >= runner.PASS_BAR["minimum_cross_domain_stories"]
        assert decision["ignore_candidate_count"] >= runner.PASS_BAR["minimum_ignore_candidates"]
        assert decision["need_more_candidate_count"] <= runner.PASS_BAR["maximum_need_more_stories"]
        assert decision["founder_review_allowed"] is True
    else:
        assert decision["founder_review_allowed"] is False


def test_main_cards_have_required_operator_review_fields():
    ensure_outputs()
    batch = load_json(runner.OUT / "FOUNDER_GRADE_STORY_BATCH_INDEX.json")
    for story in batch["stories"]:
        assert story["operator_verdict"] in {"watch_this", "ignore_for_now", "need_more_before_deciding"}
        assert story["what_where"]
        assert story["so_what"]
        assert story["suggested_next_step"]
        assert story["confidence_label"] in {"low", "medium", "high"}
        assert story["confidence_reason"]
        assert len(story["evidence_notes"]) >= 2
        assert story["cannot_claim"]
        assert story["audience_fit"] == "operator"
        for note in story["evidence_notes"]:
            assert note["note_text"]
            assert note["source_class"]
            assert not note["freshness"].startswith("UNKNOWN")
            assert not note["place"].startswith("UNKNOWN")
            assert note["supports"]
            assert note["does_not_prove"]


def test_not_enough_keeps_weak_cards_in_appendix_without_padding():
    ensure_outputs()
    decision = load_json(runner.OUT / "FOUNDER_GRADE_STORY_MATERIALIZATION_DECISION.json")
    batch = load_json(runner.OUT / "FOUNDER_GRADE_STORY_BATCH_INDEX.json")
    appendix_md = (runner.OUT / "FOUNDER_DIAGNOSTIC_APPENDIX_WEAK_DIAGNOSTIC_CARDS.md").read_text(encoding="utf-8")
    if decision["status"] == runner.STATUS_NOT_ENOUGH:
        assert "not used to pad" in appendix_md
        assert decision["main_story_count"] < runner.PASS_BAR["minimum_founder_grade_stories"] or decision["metrics"]["blockers"]
    else:
        assert batch["appendix_story_count"] >= 1


def test_main_founder_path_avoids_banned_technical_terms():
    ensure_outputs()
    text = runner.main_path_text(runner.OUT)
    assert runner.technical_hits(text) == []
    assert "Verdict:" in text
    assert "What/where" in text
    assert "So what" in text
    assert "Suggested next review step" in text
    assert "Confidence" in text
    assert "Evidence snapshot" in text
    assert "What CityBrain will not claim" in text
    assert "watch_this / ignore_for_now / need_more_before_deciding" in text


def test_response_csv_and_boundaries():
    ensure_outputs()
    rows = list(csv.DictReader(StringIO((runner.OUT / "FOUNDER_DIAGNOSTIC_RESPONSE_TEMPLATE.csv").read_text(encoding="utf-8"))))
    batch = load_json(runner.OUT / "FOUNDER_GRADE_STORY_BATCH_INDEX.json")
    assert len(rows) == batch["main_story_count"]
    for row in rows:
        assert row["founder_internal"] == "true"
        assert row["operator_fuel"] == "false"
        assert row["training_eligible"] == "false"
        assert row["external_operator_validation"] == "false"
        assert row["product_review_ready"] == "false"
        assert row["client_ready"] == "false"
    boundary = load_json(runner.OUT / "FOUNDER_STORY_BOUNDARY_GUARD.json")
    assert boundary["status"] == "PASS"
    assert boundary["founder_session_result_created"] is False
    assert boundary["operator_fuel"] is False
    assert boundary["training_eligible"] is False
    assert boundary["source_truth_mutated"] is False
    assert boundary["forecast_packet_created"] is False
    assert boundary["official_workflow_case_action_control_enforcement_created"] is False
    assert boundary["product_review_ready"] is False
    assert boundary["client_ready"] is False


def test_manifest_publication_and_ledgers():
    ensure_outputs()
    discovery = load_json(runner.OUT / "FOUNDER_STORY_SOURCE_DISCOVERY_REPORT.json")
    classification = load_json(runner.OUT / "FOUNDER_STORY_CANDIDATE_CLASSIFICATION_LEDGER.json")
    materialization = load_json(runner.OUT / "FOUNDER_STORY_MATERIALIZATION_LEDGER.json")
    assert discovery["seed_r3_event_count"] >= 80
    assert classification["candidate_count"] >= 10
    assert all(row["classification"] in runner.CLASSIFICATIONS for row in classification["rows"])
    assert materialization["materialized_candidate_count"] == classification["candidate_count"]
    assert all(row["source_truth_mutated"] is False for row in materialization["rows"])
    assert runner.verify_manifest(runner.OUT / "HASH_MANIFEST.json") == []
    assert (runner.PUB / "FOUNDER_REVIEW_START_HERE.html").exists()

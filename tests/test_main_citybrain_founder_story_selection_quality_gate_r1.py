from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_founder_story_selection_quality_gate_r1.py"

spec = importlib.util.spec_from_file_location("story_selection_quality_gate", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outputs() -> None:
    if not (runner.OUT / "FOUNDER_STORY_SELECTION_QUALITY_GATE_DECISION.json").exists():
        runner.build(runner.OUT)


def test_required_outputs_exist_and_validate():
    runner.build(runner.OUT)
    missing = [name for name in runner.REQUIRED if not (runner.OUT / name).exists()]
    assert missing == []
    assert runner.validate(runner.OUT) == []


def test_current_batch_is_honestly_blocked_for_founder_review():
    ensure_outputs()
    decision = load_json(runner.OUT / "FOUNDER_STORY_SELECTION_QUALITY_GATE_DECISION.json")
    counts = load_json(runner.OUT / "FOUNDER_STORY_CLASSIFICATION_COUNTS.json")
    assert decision["status"] == runner.STATUS_NOT_ENOUGH
    assert decision["founder_review_allowed"] is False
    assert decision["do_not_run_founder_review_on_current_batch"] is True
    assert counts["pass_bar_met"] is False
    assert counts["candidate_count"] >= 10
    assert counts["selected_main_candidate_count"] < runner.PASS_BAR["minimum_main_cards"]
    assert counts["selected_cross_domain_count"] < runner.PASS_BAR["minimum_cross_domain_cards"]
    assert counts["blockers"]


def test_all_cards_are_classified_with_supported_labels():
    ensure_outputs()
    matrix = load_json(runner.OUT / "FOUNDER_STORY_SELECTION_QUALITY_MATRIX.json")
    rows = matrix["rows"]
    assert rows
    assert all(row["classification"] in runner.CLASSIFICATIONS for row in rows)
    classifications = {row["classification"] for row in rows}
    assert any(label.startswith("not_reviewable_due_to") for label in classifications)
    assert "diagnostic_boundary_case" in classifications or "negative_abstain_case" in classifications
    for row in rows:
        criteria = row["founder_grade_criteria"]
        assert "human_readable_place" in criteria
        assert "freshness_or_timestamp_present" in criteria
        assert "has_two_notes_or_strong_named_source" in criteria
        assert "clear_so_what" in criteria
        assert "clear_next_review_step" in criteria


def test_weak_cards_are_not_padded_into_main_set():
    ensure_outputs()
    main = load_json(runner.OUT / "FOUNDER_REVIEWABLE_MAIN_SET.json")
    appendix = load_json(runner.OUT / "DIAGNOSTIC_APPENDIX_CARDS.json")
    matrix = load_json(runner.OUT / "FOUNDER_STORY_SELECTION_QUALITY_MATRIX.json")
    assert len(main["cards"]) + len(appendix["cards"]) == len(matrix["rows"])
    assert len(appendix["cards"]) > 0
    appendix_ids = {card["card_id"] for card in appendix["cards"]}
    by_id = {row["card_id"]: row for row in matrix["rows"]}
    assert any(by_id[card_id]["classification"].startswith("not_reviewable_due_to") for card_id in appendix_ids)


def test_acceptance_bar_metrics_capture_selection_failure():
    ensure_outputs()
    counts = load_json(runner.OUT / "FOUNDER_STORY_CLASSIFICATION_COUNTS.json")
    assert counts["pass_bar"] == runner.PASS_BAR
    assert counts["selected_watch_or_review_worthy_count"] < runner.PASS_BAR["minimum_watch_or_review_worthy"]
    assert counts["selected_cross_domain_count"] < runner.PASS_BAR["minimum_cross_domain_cards"]
    assert counts["selected_honest_abstain_or_ignore_count"] < runner.PASS_BAR["minimum_honest_abstain_or_ignore_cards"]
    assert "classification_counts" in counts


def test_guard_manifest_and_publication():
    ensure_outputs()
    guard = load_json(runner.OUT / "QUALITY_GATE_GUARD.json")
    assert guard["status"] == "PASS"
    assert guard["founder_review_executed"] is False
    assert guard["founder_session_result_created"] is False
    assert guard["operator_fuel_created"] is False
    assert guard["training_rows_created"] is False
    assert guard["source_truth_mutated"] is False
    assert guard["forecast_packet_created"] is False
    assert guard["product_review_ready_claim"] is False
    assert guard["client_ready_claim"] is False
    assert guard["main_set_padded_with_weak_cards"] is False
    assert runner.verify_manifest(runner.OUT / "HASH_MANIFEST.json") == []
    assert (runner.PUB / "FOUNDER_STORY_SELECTION_QUALITY_GATE_REPORT.html").exists()

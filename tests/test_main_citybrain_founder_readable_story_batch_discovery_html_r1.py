from __future__ import annotations

import csv
import importlib.util
import json
from io import StringIO
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_founder_readable_story_batch_discovery_html_r1.py"

spec = importlib.util.spec_from_file_location("founder_story_batch", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outputs() -> None:
    if not (runner.DEFAULT_OUT / "FOUNDER_STORY_BATCH_DECISION.json").exists():
        runner.build(runner.DEFAULT_OUT)


def test_required_outputs_exist_and_validate():
    runner.build(runner.DEFAULT_OUT)
    assert [path.name for path in runner.required_paths(runner.DEFAULT_OUT) if not path.exists()] == []
    assert runner.validate(runner.DEFAULT_OUT) == []


def test_discovers_at_least_ten_stories_without_fabrication():
    ensure_outputs()
    decision = load_json(runner.DEFAULT_OUT / "FOUNDER_STORY_BATCH_DECISION.json")
    discovery = load_json(runner.DEFAULT_OUT / "FOUNDER_STORY_SOURCE_DISCOVERY_REPORT.json")
    ledger = load_json(runner.DEFAULT_OUT / "FOUNDER_STORY_SELECTION_LEDGER.json")
    assert decision["status"] == runner.STATUS_PASS
    assert decision["story_count"] >= 10
    assert decision["minimum_story_count_met"] is True
    assert discovery["candidate_story_count"] >= 10
    assert ledger["selected_story_count"] == decision["story_count"]
    assert all("existing local artifacts" in " ".join(ledger["selection_rules"]).lower() for _ in [0])


def test_founder_html_plain_english_and_no_banned_terms():
    ensure_outputs()
    start = (runner.DEFAULT_OUT / "FOUNDER_REVIEW_START_HERE.html").read_text(encoding="utf-8")
    cards = (runner.DEFAULT_OUT / "FOUNDER_STORY_CARDS_READABLE.html").read_text(encoding="utf-8")
    assert "What may be happening" in cards
    assert "Why might it matter" in cards
    assert "What is uncertain" in cards
    assert "What evidence is missing" in cards
    assert runner.banned_hits(start + cards) == []


def test_response_csv_has_one_row_per_story_and_boundaries():
    ensure_outputs()
    index = load_json(runner.DEFAULT_OUT / "FOUNDER_STORY_BATCH_INDEX.json")
    csv_text = (runner.DEFAULT_OUT / "FOUNDER_DIAGNOSTIC_RESPONSE_TEMPLATE_BATCH.csv").read_text(encoding="utf-8")
    rows = list(csv.DictReader(StringIO(csv_text)))
    assert len(rows) == index["story_count"]
    for row in rows:
        assert row["founder_internal"] == "true"
        assert row["operator_fuel"] == "false"
        assert row["training_eligible"] == "false"
        assert row["external_operator_validation"] == "false"
        assert row["learning_arming_allowed"] == "false"
        assert row["product_review_ready"] == "false"
        assert row["client_ready"] == "false"


def test_each_story_has_required_plain_english_sections():
    ensure_outputs()
    index = load_json(runner.DEFAULT_OUT / "FOUNDER_STORY_BATCH_INDEX.json")
    cards_md = (runner.DEFAULT_OUT / "FOUNDER_STORY_CARDS_READABLE.md").read_text(encoding="utf-8")
    for row in index["stories"]:
        assert row["plain_english_title"] in cards_md
    for phrase in [
        "What may be happening?",
        "Why might it matter?",
        "What seems connected?",
        "What is uncertain?",
        "What must CityBrain not claim?",
        "What evidence is missing?",
        "Would this be useful to review?",
    ]:
        assert phrase in cards_md


def test_boundaries_manifest_and_publication():
    ensure_outputs()
    decision = load_json(runner.DEFAULT_OUT / "FOUNDER_STORY_BATCH_DECISION.json")
    boundary = load_json(runner.DEFAULT_OUT / "FOUNDER_STORY_BOUNDARY_GUARD.json")
    assert decision["product_review_ready"] is False
    assert decision["client_ready"] is False
    assert decision["founder_diagnostic_ready"] is True
    assert boundary["status"] == "PASS"
    assert boundary["founder_session_results_created"] is False
    assert boundary["operator_fuel_created"] is False
    assert boundary["training_rows_created"] is False
    assert boundary["forecast_packet_created"] is False
    assert boundary["source_truth_mutated"] is False
    assert runner.verify_manifest(runner.DEFAULT_OUT / "HASH_MANIFEST.json") == []
    assert (runner.PUBLICATION_ROOT / "FOUNDER_REVIEW_START_HERE.html").exists()

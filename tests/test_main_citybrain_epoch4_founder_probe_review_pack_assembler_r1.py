from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_founder_probe_review_pack_assembler_r1.py"

spec = importlib.util.spec_from_file_location("founder_probe_review_pack_assembler", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def csv_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def ensure_outputs() -> None:
    if not (runner.OUTPUT_ROOT / "FOUNDER_PROBE_ASSEMBLY_DECISION.json").exists():
        runner.build_review_pack()


def test_required_outputs_and_publication_exist():
    runner.build_review_pack()
    missing = [runner.rel(path) for path in runner.required_paths() if not path.exists()]
    assert missing == []
    publication_missing = [runner.rel(path) for path in runner.publication_paths() if not path.exists()]
    assert publication_missing == []


def test_review_cards_are_materialized_as_markdown_and_json():
    ensure_outputs()
    markdown_cards = sorted((runner.OUTPUT_ROOT / "review_cards").glob("founder-probe-r2-*.md"))
    json_cards = sorted((runner.OUTPUT_ROOT / "review_cards").glob("founder-probe-r2-*.json"))
    assert len(markdown_cards) == 16
    assert len(json_cards) == 16
    sample = markdown_cards[0].read_text(encoding="utf-8")
    assert "## Source / Evidence Summary" in sample
    assert "## CHECK v1 Summary" in sample
    assert "## Cannot-Claim Block" in sample
    assert "## What You Should Judge" in sample


def test_prefilled_csv_has_metadata_only_and_blank_review_fields():
    ensure_outputs()
    rows = csv_rows(runner.OUTPUT_ROOT / "FOUNDER_PROBE_RESPONSE_TEMPLATE_PREFILLED.csv")
    assert len(rows) == 16
    for row in rows:
        assert row["task_id"].startswith("founder-probe-r2-")
        assert row["family"]
        assert row["scenario"]
        assert row["eval_case"]
        assert row["check_ref"]
        assert row["reviewer_id_or_alias"] == "Hazem"
        assert row["reviewer_type"] == "founder_internal"
        for field in runner.REVIEW_FIELDS:
            assert row[field] == ""


def test_missing_evidence_is_explicit_and_not_invented():
    ensure_outputs()
    report = load_json(runner.OUTPUT_ROOT / "MISSING_EVIDENCE_REPORT.json")
    assert report["policy"] == "Missing evidence is marked explicitly and is not invented."
    assert report["cards_with_missing_evidence"] >= 1
    cards = [load_json(path) for path in sorted((runner.OUTPUT_ROOT / "review_cards").glob("founder-probe-r2-*.json"))]
    assert any(card["missing_evidence"] for card in cards)


def test_no_fabricated_session_guard_and_decision_status():
    ensure_outputs()
    guard = load_json(runner.OUTPUT_ROOT / "NO_FABRICATED_SESSION_GUARD.json")
    decision = load_json(runner.OUTPUT_ROOT / "FOUNDER_PROBE_ASSEMBLY_DECISION.json")
    assert decision["status"].endswith("_WITH_LIMITATIONS")
    assert decision["card_count"] == 16
    assert decision["session_results_created"] is False
    assert decision["operator_fuel_created"] is False
    assert decision["training_rows_created"] is False
    assert decision["source_truth_mutated"] is False
    assert guard["founder_responses_fabricated"] is False
    assert guard["external_operator_validation_claimed"] is False
    assert guard["official_workflow_or_action_created"] is False


def test_hash_manifest_and_validate_all_pass():
    ensure_outputs()
    assert runner.verify_manifest(runner.OUTPUT_ROOT / "HASH_MANIFEST.json") == []
    assert runner.validate_all() == []

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_no_human_internal_snapshot_r1.py"

spec = importlib.util.spec_from_file_location("no_human_snapshot", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outputs() -> None:
    if not (runner.SNAPSHOT_ROOT / "DECISION.json").exists():
        runner.build_snapshot()


def test_required_outputs_exist():
    runner.build_snapshot()
    missing = [runner.rel(path) for path in runner.required_paths() if not path.exists()]
    assert missing == []
    for filename in runner.EXPECTED_FILES:
        assert (runner.PUBLICATION_ROOT / filename).exists()


def test_snapshot_decision_and_no_session_guards():
    ensure_outputs()
    decision = load_json(runner.SNAPSHOT_ROOT / "DECISION.json")
    guard = load_json(runner.SNAPSHOT_ROOT / "NO_SESSION_NO_FUEL_GUARD.json")
    state = load_json(runner.SNAPSHOT_ROOT / "CURRENT_EPOCH4_NO_HUMAN_STATE.json")
    assert decision["status"] == runner.STATUS
    assert decision["session_results_created"] is False
    assert decision["operator_fuel_created"] is False
    assert decision["training_rows_created"] is False
    assert decision["source_truth_mutated"] is False
    assert guard["founder_session_results_created"] is False
    assert guard["operator_fuel_created"] is False
    assert guard["training_rows_created"] is False
    assert state["no_human_snapshot"] is True


def test_snapshot_summarizes_current_capability_eval_overlay_and_kit():
    ensure_outputs()
    product = load_json(runner.SNAPSHOT_ROOT / "PRODUCT_LOOP_CAPABILITY_SUMMARY.json")
    eval_summary = load_json(runner.SNAPSHOT_ROOT / "EVAL_CORPUS_SUMMARY.json")
    overlay = load_json(runner.SNAPSHOT_ROOT / "REMEDIATION_OVERLAY_SUMMARY.json")
    kit = load_json(runner.SNAPSHOT_ROOT / "FOUNDER_PROBE_INPUT_KIT_STATUS.json")
    maturity = load_json(runner.SNAPSHOT_ROOT / "DATA_MATURITY_CURRENT_STATE.json")
    assert product["review_packet_360_verified"] is True
    assert eval_summary["eval_corpus_case_count"] == 48
    assert eval_summary["challenge_case_count"] == 32
    assert overlay["overlay_count"] == 50
    assert overlay["promoted_to_source_truth"] is False
    assert overlay["promoted_to_canonical_truth"] is False
    assert kit["card_count"] == 16
    assert kit["session_results_created"] is False
    assert maturity["source_count"] == 664
    assert maturity["overall_maturity_score_ref"] == 36.1


def test_parked_items_and_next_decisions_are_explicit():
    ensure_outputs()
    parked = load_json(runner.SNAPSHOT_ROOT / "PARKED_ITEMS_REGISTER.json")
    next_options = load_json(runner.SNAPSHOT_ROOT / "NEXT_DECISION_OPTIONS.json")
    assert parked["parked_item_count"] >= 8
    assert "actual founder probe session results" in parked["parked_items"]
    assert "training rows or learned labels" in parked["parked_items"]
    assert {row["option_id"] for row in next_options["options"]} == {
        "keep_no_human_path",
        "run_founder_probe_import_later",
        "review_derived_overlays",
    }


def test_hash_manifest_and_validate_all_pass():
    ensure_outputs()
    assert runner.verify_manifest(runner.SNAPSHOT_ROOT / "HASH_MANIFEST.json") == []
    assert runner.validate_all() == []

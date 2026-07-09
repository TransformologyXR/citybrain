from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_after_deepening_next_wave_sequence_r1.py"

spec = importlib.util.spec_from_file_location("after_deepening_next_wave", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def ensure_outputs() -> None:
    if not (runner.SEQUENCE_ROOT / "AFTER_DEEPENING_NEXT_WAVE_SEQUENCE_DECISION.json").exists():
        runner.build_all()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_required_outputs_exist():
    runner.build_all()
    missing = [runner.rel(path) for path in runner.required_paths() if not path.exists()]
    assert missing == []


def test_product_readiness_normalizes_evidence_without_false_equivalence():
    ensure_outputs()
    decision = load_json(runner.PRODUCT_ROOT / "DECISION.json")
    matrix = load_json(runner.PRODUCT_ROOT / "CROSS_FAMILY_OPTION_EVIDENCE_MATRIX.json")
    guard = load_json(runner.PRODUCT_ROOT / "OPTION_COMPARABILITY_GUARD.json")
    atlas = load_json(runner.PRODUCT_ROOT / "REVIEW_PACKET_360_V3_EVIDENCE_ATLAS.json")
    no_session = load_json(runner.PRODUCT_ROOT / "NO_SESSION_NO_FUEL_GUARD.json")
    assert decision["status"] == runner.STATUS_PRODUCT
    assert decision["evidence_atlas_created"] is True
    assert matrix["family_count"] == 4
    assert {row["family_id"] for row in matrix["rows"]} == set(runner.ALL_FAMILIES)
    assert guard["sumo_and_non_sumo_falsely_equated"] is False
    assert guard["fixture_only_not_calibrated_limits_preserved"] is True
    assert atlas["covers_mobility_control_family"] is True
    assert atlas["family_count"] == 4
    assert no_session["founder_review_session_run"] is False
    assert no_session["operator_or_founder_fuel_created"] is False


def test_data_maturity_remediation_creates_queues_without_mutation_or_inflation():
    ensure_outputs()
    decision = load_json(runner.MATURITY_ROOT / "DATA_MATURITY_REMEDIATION_DECISION.json")
    queue = load_json(runner.MATURITY_ROOT / "MATURITY_REMEDIATION_QUEUE.json")
    delta = load_json(runner.MATURITY_ROOT / "MATURITY_SCORE_DELTA_EXPLAINER.json")
    mutation = load_json(runner.MATURITY_ROOT / "NO_SOURCE_TRUTH_MUTATION_GUARD.json")
    assert decision["status"] == runner.STATUS_MATURITY
    assert decision["queue_count"] >= 5
    assert queue["queue_count"] >= 5
    assert queue["item_count"] >= 50
    assert decision["source_truth_mutated"] is False
    assert mutation["source_records_mutated"] is False
    assert mutation["canonical_truth_mutated"] is False
    assert delta["new_maturity_score_claimed"] is False
    assert delta["maturity_inflation_without_evidence"] is False


def test_cross_track_reverify_waits_for_both_and_keeps_founder_parked():
    ensure_outputs()
    decision = load_json(runner.CROSS_ROOT / "DECISION.json")
    product = load_json(runner.CROSS_ROOT / "PRODUCT_READINESS_REVERIFY.json")
    maturity = load_json(runner.CROSS_ROOT / "DATA_MATURITY_REMEDIATION_REVERIFY.json")
    parity = load_json(runner.CROSS_ROOT / "CROSS_TRACK_REFERENCE_PARITY.json")
    founder = load_json(runner.CROSS_ROOT / "FOUNDER_REVIEW_STILL_PARKED_GUARD.json")
    assert decision["status"] == runner.STATUS_CROSS
    assert decision["product_readiness_passed"] is True
    assert decision["data_maturity_remediation_passed"] is True
    assert decision["cross_track_reference_parity_passed"] is True
    assert product["comparability_guard_passed"] is True
    assert maturity["source_truth_mutated"] is False
    assert maturity["new_maturity_score_claimed"] is False
    assert parity["all_references_current_or_disclosed"] is True
    assert founder["founder_review_session_run"] is False
    assert founder["operator_or_founder_fuel_created"] is False


def test_sequence_is_sequential_and_final_status_is_current_wave():
    ensure_outputs()
    sequence = load_json(runner.SEQUENCE_ROOT / "AFTER_DEEPENING_NEXT_WAVE_SEQUENCE_DECISION.json")
    execution = load_json(runner.SEQUENCE_ROOT / "AFTER_DEEPENING_NEXT_WAVE_SEQUENTIAL_EXECUTION_LOG.json")
    assert sequence["status"] == runner.STATUS_SEQUENCE
    assert sequence["step_count"] == 3
    assert sequence["all_steps_passed_with_limitations"] is True
    assert sequence["final_reverify_status"] == runner.STATUS_CROSS
    assert execution["parallel_execution_used"] is False
    assert [row["step"] for row in execution["steps"]] == [
        "product_readiness_gap_closure_sequence_r1",
        "data_maturity_remediation_actions_r1",
        "after_deepening_cross_track_reverify_r1",
    ]


def test_hash_manifests_and_validate_all_pass():
    ensure_outputs()
    for path in [
        runner.PRODUCT_ROOT / "HASH_MANIFEST.json",
        runner.MATURITY_ROOT / "HASH_MANIFEST.json",
        runner.CROSS_ROOT / "HASH_MANIFEST_REVERIFY.json",
        runner.SEQUENCE_ROOT / "HASH_MANIFEST.json",
    ]:
        assert runner.verify_manifest(path) == []
    assert runner.validate_all() == []

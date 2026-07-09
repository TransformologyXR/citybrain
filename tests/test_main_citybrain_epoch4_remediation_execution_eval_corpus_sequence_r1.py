from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_remediation_execution_eval_corpus_sequence_r1.py"

spec = importlib.util.spec_from_file_location("remediation_eval_sequence", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outputs() -> None:
    if not (runner.SEQUENCE_ROOT / "REMEDIATION_EXECUTION_EVAL_SEQUENCE_DECISION.json").exists():
        runner.build_all()


def test_required_outputs_exist():
    runner.build_all()
    missing = [runner.rel(path) for path in runner.required_paths() if not path.exists()]
    assert missing == []


def test_remediation_execution_converts_queues_without_mutation_or_score_inflation():
    ensure_outputs()
    decision = load_json(runner.REMEDIATION_ROOT / "DATA_MATURITY_REMEDIATION_EXECUTION_DECISION.json")
    plan = load_json(runner.REMEDIATION_ROOT / "REMEDIATION_EXECUTION_PLAN.json")
    mutation_guard = load_json(runner.REMEDIATION_ROOT / "NO_SOURCE_TRUTH_MUTATION_GUARD.json")
    score_guard = load_json(runner.REMEDIATION_ROOT / "NO_SCORE_INFLATION_GUARD.json")
    assert decision["status"] == runner.STATUS_REMEDIATION
    assert plan["queue_count"] == 5
    assert plan["raw_remediation_item_count"] == 50
    assert decision["candidate_count"] == 50
    assert decision["candidate_count_minimum_met"] is True
    assert decision["source_truth_mutated"] is False
    assert mutation_guard["source_records_mutated"] is False
    assert mutation_guard["source_truth_patch_applied"] is False
    assert score_guard["new_maturity_score_claimed"] is False
    assert score_guard["maturity_inflation_without_evidence"] is False


def test_eval_corpus_covers_four_families_and_is_not_training_fuel():
    ensure_outputs()
    decision = load_json(runner.CORPUS_ROOT / "PRODUCT_LOOP_EVAL_CORPUS_DECISION.json")
    cases = load_json(runner.CORPUS_ROOT / "EVAL_CASES_4_FAMILY.json")
    check = load_json(runner.CORPUS_ROOT / "EXPECTED_CHECK_OUTCOMES.json")
    brief = load_json(runner.CORPUS_ROOT / "EXPECTED_BRIEF_BLOCKS.json")
    spatial = load_json(runner.CORPUS_ROOT / "EXPECTED_SPATIAL_PACKET_ASSERTIONS.json")
    training_guard = load_json(runner.CORPUS_ROOT / "NO_TRAINING_FUEL_GUARD.json")
    assert decision["status"] == runner.STATUS_CORPUS
    assert decision["family_count"] == 4
    assert decision["case_count"] >= 12
    assert set(decision["families"]) == set(runner.ALL_FAMILIES)
    assert all(case["training_eligible"] is False for case in cases["cases"])
    assert len(check["assertions"]) == len(cases["cases"])
    assert len(brief["assertions"]) == len(cases["cases"])
    assert all(row["no_live_control_claim"] is True for row in spatial["assertions"])
    assert training_guard["training_rows_created"] is False
    assert training_guard["operator_fuel_created"] is False
    assert training_guard["founder_fuel_created"] is False


def test_founder_review_dry_run_has_tasks_but_no_session_fuel_or_dispositions():
    ensure_outputs()
    decision = load_json(runner.DRY_RUN_ROOT / "FOUNDER_REVIEW_DRY_RUN_DECISION.json")
    tasks = load_json(runner.DRY_RUN_ROOT / "DRY_RUN_TASK_QUEUE.json")
    form = load_json(runner.DRY_RUN_ROOT / "DRY_RUN_FORM_VALIDATION_REPORT.json")
    packet = load_json(runner.DRY_RUN_ROOT / "DRY_RUN_PACKET_COMPLETENESS_REPORT.json")
    no_session = load_json(runner.DRY_RUN_ROOT / "FOUNDING_REVIEW_NOT_RUN_GUARD.json")
    no_fuel = load_json(runner.DRY_RUN_ROOT / "NO_FUEL_NO_DISPOSITIONS_GUARD.json")
    assert decision["status"] == runner.STATUS_DRY_RUN
    assert decision["task_count"] >= 8
    assert tasks["session_run"] is False
    assert form["status"] == "PASS"
    assert packet["all_tasks_have_check_refs"] is True
    assert packet["all_tasks_have_evidence_refs"] is True
    assert no_session["founder_review_session_run"] is False
    assert no_session["founder_session_results_created"] is False
    assert no_fuel["founder_fuel_created"] is False
    assert no_fuel["operator_fuel_created"] is False
    assert no_fuel["dispositions_created"] is False


def test_final_reverify_and_sequence_are_sequential_and_guarded():
    ensure_outputs()
    final = load_json(runner.FINAL_ROOT / "DECISION.json")
    remediation = load_json(runner.FINAL_ROOT / "REMEDIATION_CANDIDATE_REVERIFY.json")
    corpus = load_json(runner.FINAL_ROOT / "EVAL_CORPUS_REVERIFY.json")
    dry_run = load_json(runner.FINAL_ROOT / "FOUNDER_DRY_RUN_NO_SESSION_REVERIFY.json")
    sequence = load_json(runner.SEQUENCE_ROOT / "REMEDIATION_EXECUTION_EVAL_SEQUENCE_DECISION.json")
    log = load_json(runner.SEQUENCE_ROOT / "SEQUENTIAL_EXECUTION_LOG.json")
    assert final["status"] == runner.STATUS_FINAL
    assert final["source_truth_mutated"] is False
    assert final["training_fuel_created"] is False
    assert remediation["candidate_count"] == 50
    assert remediation["candidate_count_minimum_met"] is True
    assert corpus["family_count"] == 4
    assert corpus["case_count_minimum_met"] is True
    assert dry_run["session_run"] is False
    assert dry_run["fuel_created"] is False
    assert sequence["status"] == runner.STATUS_SEQUENCE
    assert sequence["step_count"] == 4
    assert sequence["parallel_execution_used"] is False
    assert log["parallel_execution_used"] is False
    assert [row["package_id"] for row in log["steps"]] == [
        "MAIN-CITYBRAIN-EPOCH4-DATA-MATURITY-REMEDIATION-EXECUTION-BATCH-R1",
        "MAIN-CITYBRAIN-EPOCH4-PRODUCT-LOOP-EVAL-CORPUS-R1",
        "MAIN-CITYBRAIN-EPOCH4-FOUNDER-REVIEW-DRY-RUN-NO-SESSION-R1",
        "MAIN-CITYBRAIN-EPOCH4-REMEDIATION-EVAL-FINAL-REVERIFY-R1",
    ]


def test_hash_manifests_publications_and_validate_only_contract():
    ensure_outputs()
    for path in [
        runner.REMEDIATION_ROOT / "HASH_MANIFEST.json",
        runner.CORPUS_ROOT / "HASH_MANIFEST.json",
        runner.DRY_RUN_ROOT / "HASH_MANIFEST.json",
        runner.FINAL_ROOT / "HASH_MANIFEST_REVERIFY.json",
        runner.SEQUENCE_ROOT / "HASH_MANIFEST.json",
    ]:
        assert runner.verify_manifest(path) == []
    for root, publication_root, files in [
        (runner.REMEDIATION_ROOT, runner.PUB_REMEDIATION, runner.REMEDIATION_FILES),
        (runner.CORPUS_ROOT, runner.PUB_CORPUS, runner.CORPUS_FILES),
        (runner.DRY_RUN_ROOT, runner.PUB_DRY_RUN, runner.DRY_RUN_FILES),
        (runner.FINAL_ROOT, runner.PUB_FINAL, runner.FINAL_FILES),
        (runner.SEQUENCE_ROOT, runner.PUB_SEQUENCE, runner.SEQUENCE_FILES),
    ]:
        for filename in files:
            assert (root / filename).exists()
            assert (publication_root / filename).exists()
    assert runner.validate_all() == []

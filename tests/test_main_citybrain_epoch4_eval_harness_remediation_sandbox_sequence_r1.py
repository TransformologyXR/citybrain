from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_eval_harness_remediation_sandbox_sequence_r1.py"

spec = importlib.util.spec_from_file_location("eval_harness_sequence", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outputs() -> None:
    if not (runner.SEQUENCE_ROOT / "EVAL_HARNESS_REMEDIATION_SEQUENCE_DECISION.json").exists():
        runner.build_all()


def test_required_outputs_exist():
    runner.build_all()
    missing = [runner.rel(path) for path in runner.required_paths() if not path.exists()]
    assert missing == []


def test_eval_harness_executes_twelve_cases_without_training_fuel():
    ensure_outputs()
    decision = load_json(runner.EVAL_ROOT / "DECISION.json")
    report = load_json(runner.EVAL_ROOT / "PRODUCT_LOOP_EVAL_EXECUTION_REPORT.json")
    cases = load_json(runner.EVAL_ROOT / "CASE_RESULTS.json")
    family = load_json(runner.EVAL_ROOT / "FAMILY_SCORECARD.json")
    no_training = load_json(runner.EVAL_ROOT / "NO_TRAINING_FUEL_GUARD.json")
    assert decision["status"] == runner.STATUS_EVAL
    assert decision["case_count"] == 12
    assert decision["case_pass_count"] == 12
    assert decision["eval_blocking_failure_count"] == 0
    assert report["family_count"] == 4
    assert cases["pass_count"] == 12
    assert {row["family_id"] for row in family["families"]} == set(runner.ALL_FAMILIES)
    assert no_training["training_rows_created"] is False
    assert no_training["founder_fuel_created"] is False
    assert no_training["operator_fuel_created"] is False


def test_assertion_layers_pass_and_preserve_boundaries():
    ensure_outputs()
    for filename in [
        "CHECK_ASSERTION_RESULTS.json",
        "BRIEF_ASSERTION_RESULTS.json",
        "EVENT_STATE_ASSERTION_RESULTS.json",
        "SIMULATION_OPTION_ASSERTION_RESULTS.json",
        "SPATIAL_PACKET_ASSERTION_RESULTS.json",
    ]:
        payload = load_json(runner.EVAL_ROOT / filename)
        assert payload["assertion_count"] == 12
        assert payload["pass_count"] == 12
        assert all(row["status"] == "PASS" for row in payload["results"])
    simulation = load_json(runner.EVAL_ROOT / "SIMULATION_OPTION_ASSERTION_RESULTS.json")
    spatial = load_json(runner.EVAL_ROOT / "SPATIAL_PACKET_ASSERTION_RESULTS.json")
    assert all(row["actual"]["forecast_authority"] is False for row in simulation["results"])
    assert all(row["actual"]["live_control_claim"] is False for row in spatial["results"])
    assert all(row["actual"]["official_action_claim"] is False for row in spatial["results"])


def test_sandbox_projects_all_candidates_without_applying_patches_or_score_inflation():
    ensure_outputs()
    decision = load_json(runner.SANDBOX_ROOT / "DECISION.json")
    plan = load_json(runner.SANDBOX_ROOT / "SANDBOX_PROJECTION_PLAN.json")
    overlays = load_json(runner.SANDBOX_ROOT / "CANDIDATE_PATCH_OVERLAYS.json")
    by_queue = load_json(runner.SANDBOX_ROOT / "PROJECTED_IMPACT_BY_QUEUE.json")
    mutation = load_json(runner.SANDBOX_ROOT / "NO_SOURCE_TRUTH_MUTATION_GUARD.json")
    score = load_json(runner.SANDBOX_ROOT / "NO_SCORE_INFLATION_GUARD.json")
    assert decision["status"] == runner.STATUS_SANDBOX
    assert decision["candidate_count"] == 50
    assert decision["overlay_count"] == 50
    assert plan["queue_count"] == 5
    assert overlays["source_truth_patch_applied"] is False
    assert all(row["source_truth_patch_applied"] is False for row in overlays["overlays"])
    assert by_queue["queue_count"] == 5
    assert mutation["source_records_mutated"] is False
    assert mutation["source_registry_mutated"] is False
    assert score["new_maturity_score_claimed"] is False
    assert score["maturity_score_delta_claimed_as_fact"] is False


def test_triage_produces_no_session_founder_readiness_and_fix_queue():
    ensure_outputs()
    decision = load_json(runner.TRIAGE_ROOT / "DECISION.json")
    readiness = load_json(runner.TRIAGE_ROOT / "FOUNDER_REVIEW_READINESS_NO_SESSION_DECISION.json")
    top_fix = load_json(runner.TRIAGE_ROOT / "TOP_FIX_QUEUE_BEFORE_FOUNDER_REVIEW.json")
    packet = load_json(runner.TRIAGE_ROOT / "PACKET_COMPLETENESS_READINESS.json")
    adjustment = load_json(runner.TRIAGE_ROOT / "REVIEW_TASK_QUEUE_ADJUSTMENT_PROPOSAL.json")
    no_session = load_json(runner.TRIAGE_ROOT / "NO_SESSION_NO_FUEL_GUARD.json")
    assert decision["status"] == runner.STATUS_TRIAGE
    assert decision["founder_review_session_run"] is False
    assert decision["operator_or_founder_fuel_created"] is False
    assert readiness["session_results_created"] is False
    assert readiness["go_no_go"] == "GO_FOR_BOUNDED_PROBE_WITH_LIMITATIONS"
    assert top_fix["queue_count"] == 5
    assert packet["packet_ready_count"] == 12
    assert adjustment["proposal_only"] is True
    assert no_session["founder_review_session_run"] is False
    assert no_session["operator_or_founder_fuel_created"] is False


def test_final_reverify_and_sequence_are_sequential_and_guarded():
    ensure_outputs()
    final = load_json(runner.FINAL_ROOT / "DECISION.json")
    sequence = load_json(runner.SEQUENCE_ROOT / "EVAL_HARNESS_REMEDIATION_SEQUENCE_DECISION.json")
    log = load_json(runner.SEQUENCE_ROOT / "SEQUENTIAL_EXECUTION_LOG.json")
    assert final["status"] == runner.STATUS_FINAL
    assert final["all_required_outputs_present"] is True
    assert final["eval_case_count"] == 12
    assert final["eval_case_pass_count"] == 12
    assert final["sandbox_overlay_count"] == 50
    assert final["founder_review_session_run"] is False
    assert final["operator_or_founder_fuel_created"] is False
    assert final["source_truth_mutated"] is False
    assert final["training_rows_created"] is False
    assert sequence["status"] == runner.STATUS_SEQUENCE
    assert sequence["step_count"] == 4
    assert sequence["parallel_execution_used"] is False
    assert log["parallel_execution_used"] is False
    assert [row["package_id"] for row in log["steps"]] == [
        "MAIN-CITYBRAIN-EPOCH4-PRODUCT-LOOP-EVAL-HARNESS-EXECUTION-R1",
        "MAIN-CITYBRAIN-EPOCH4-REMEDIATION-CANDIDATE-SANDBOX-PROJECTION-R1",
        "MAIN-CITYBRAIN-EPOCH4-EVAL-GAP-TRIAGE-FOUNDER-READINESS-NO-SESSION-R1",
        "MAIN-CITYBRAIN-EPOCH4-EVAL-HARNESS-REMEDIATION-FINAL-REVERIFY-R1",
    ]


def test_hash_manifests_publications_and_validate_all_pass():
    ensure_outputs()
    for path in [
        runner.EVAL_ROOT / "HASH_MANIFEST.json",
        runner.SANDBOX_ROOT / "HASH_MANIFEST.json",
        runner.TRIAGE_ROOT / "HASH_MANIFEST.json",
        runner.FINAL_ROOT / "HASH_MANIFEST_REVERIFY.json",
        runner.SEQUENCE_ROOT / "HASH_MANIFEST.json",
    ]:
        assert runner.verify_manifest(path) == []
    for root, publication_root, files in [
        (runner.EVAL_ROOT, runner.PUB_EVAL, runner.EVAL_FILES),
        (runner.SANDBOX_ROOT, runner.PUB_SANDBOX, runner.SANDBOX_FILES),
        (runner.TRIAGE_ROOT, runner.PUB_TRIAGE, runner.TRIAGE_FILES),
        (runner.FINAL_ROOT, runner.PUB_FINAL, runner.FINAL_FILES),
        (runner.SEQUENCE_ROOT, runner.PUB_SEQUENCE, runner.SEQUENCE_FILES),
    ]:
        for filename in files:
            assert (root / filename).exists()
            assert (publication_root / filename).exists()
    assert runner.validate_all() == []

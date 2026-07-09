from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_eval_corpus_expansion_hardening_sequence_r1.py"

spec = importlib.util.spec_from_file_location("eval_corpus_expansion_hardening", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_outputs() -> None:
    if not (runner.FINAL_ROOT / "EVAL_EXPANSION_HARDENING_FINAL_REVERIFY_DECISION.json").exists():
        runner.build_all()


def test_required_outputs_exist():
    runner.build_all()
    missing = [runner.rel(path) for path in runner.required_paths() if not path.exists()]
    assert missing == []


def test_eval_corpus_r2_expands_beyond_prior_and_balances_families():
    ensure_outputs()
    decision = load_json(runner.EXPANSION_ROOT / "EVAL_CORPUS_EXPANSION_R2_DECISION.json")
    index = load_json(runner.EXPANSION_ROOT / "EVAL_CORPUS_R2_INDEX.json")
    balance = load_json(runner.EXPANSION_ROOT / "EVAL_CASE_FAMILY_BALANCE_REPORT.json")
    cases = runner.read_jsonl(runner.EXPANSION_ROOT / "EVAL_CASES_R2.jsonl")
    assert decision["status"] == runner.STATUS_EXPANSION
    assert decision["case_count"] == 48
    assert decision["target_min_cases_met"] is True
    assert index["case_count"] > 12
    assert set(index["families"]) == set(runner.FAMILIES)
    assert balance["min_family_case_count"] == 12
    assert balance["max_family_case_count"] == 12
    assert len(cases) == 48
    assert all(case["replay_mode"] == "local_offline_replay" for case in cases)


def test_negative_challenge_coverage_present():
    ensure_outputs()
    coverage = load_json(runner.EXPANSION_ROOT / "EVAL_CASE_NEGATIVE_COVERAGE_REPORT.json")
    challenge_cases = runner.read_jsonl(runner.CHALLENGE_ROOT / "CHALLENGE_CASES.jsonl")
    abstain = load_json(runner.CHALLENGE_ROOT / "EXPECTED_ABSTAIN_CASES.json")
    downgrade = load_json(runner.CHALLENGE_ROOT / "EXPECTED_DOWNGRADE_CASES.json")
    quarantine = load_json(runner.CHALLENGE_ROOT / "EXPECTED_QUARANTINE_CASES.json")
    sim_na = load_json(runner.CHALLENGE_ROOT / "EXPECTED_SIMULATION_NOT_APPLICABLE_CASES.json")
    assert coverage["required_classes_present"] is True
    assert len(challenge_cases) >= 32
    assert abstain["case_count"] > 0
    assert downgrade["case_count"] > 0
    assert quarantine["case_count"] == 4
    assert sim_na["case_count"] == 4


def test_candidate_fix_sandbox_does_not_mutate_or_promote_truth():
    ensure_outputs()
    decision = load_json(runner.FIX_SANDBOX_ROOT / "CANDIDATE_FIX_EFFECT_SANDBOX_DECISION.json")
    matrix = load_json(runner.FIX_SANDBOX_ROOT / "CANDIDATE_FIX_EFFECT_MATRIX.json")
    mutation = load_json(runner.FIX_SANDBOX_ROOT / "SOURCE_TRUTH_NO_MUTATION_AUDIT.json")
    promotion = load_json(runner.FIX_SANDBOX_ROOT / "FIX_PROMOTION_CANDIDATE_REGISTER.json")
    assert decision["status"] == runner.STATUS_FIX_SANDBOX
    assert decision["derived_fix_count"] == 50
    assert decision["source_truth_mutated"] is False
    assert decision["promoted_to_authoritative_truth"] is False
    assert matrix["effect_count"] == 50
    assert all(row["source_truth_mutated"] is False for row in matrix["effects"])
    assert all(row["promote_to_authoritative_truth"] is False for row in matrix["effects"])
    assert mutation["source_records_mutated"] is False
    assert mutation["source_registry_mutated"] is False
    assert promotion["promotion_is_authoritative"] is False


def test_no_session_readiness_refresh_has_no_fuel_or_training():
    ensure_outputs()
    decision = load_json(runner.READINESS_ROOT / "NO_SESSION_READINESS_REFRESH_DECISION.json")
    guard = load_json(runner.READINESS_ROOT / "NO_SESSION_NO_FUEL_GUARD.json")
    ready = load_json(runner.READINESS_ROOT / "FOUNDER_PROBE_READINESS_CURRENT_STATE.json")
    assert decision["status"] == runner.STATUS_READINESS
    assert decision["recommendation"] == "GO_FOR_BOUNDED_FOUNDER_PROBE"
    assert decision["session_results_created"] is False
    assert guard["session_results_created"] is False
    assert guard["operator_fuel_created"] is False
    assert guard["training_rows_created"] is False
    assert ready["eval_corpus_r2_case_count"] == 48
    assert ready["operator_fuel_created"] is False


def test_final_reverify_status_and_forbidden_capability_guards():
    ensure_outputs()
    final = load_json(runner.FINAL_ROOT / "EVAL_EXPANSION_HARDENING_FINAL_REVERIFY_DECISION.json")
    guard = load_json(runner.FINAL_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json")
    corpus = load_json(runner.FINAL_ROOT / "EVAL_CORPUS_R2_REVERIFY.json")
    challenge = load_json(runner.FINAL_ROOT / "CHALLENGE_NEGATIVE_SUITE_REVERIFY.json")
    assert final["status"] == runner.STATUS_FINAL
    assert final["case_count"] == 48
    assert final["challenge_case_count"] >= 32
    assert final["source_truth_mutated"] is False
    assert final["session_results_created"] is False
    assert final["operator_fuel_created"] is False
    assert final["training_rows_created"] is False
    assert final["product_forecast_surface_created"] is False
    assert final["official_action_created"] is False
    assert guard["forbidden_capabilities_created"] == []
    assert guard["checks"]["ForecastPacket_created"] is False
    assert guard["checks"]["official_workflow_action_case_ticket_dispatch_control_enforcement_created"] is False
    assert corpus["target_min_cases_met"] is True
    assert challenge["non_sumo_forced_through_sumo"] is False
    assert challenge["official_action_created"] is False


def test_hash_manifests_and_validate_all_pass():
    ensure_outputs()
    for path in [
        runner.EXPANSION_ROOT / "HASH_MANIFEST.json",
        runner.FIX_SANDBOX_ROOT / "HASH_MANIFEST.json",
        runner.CHALLENGE_ROOT / "HASH_MANIFEST.json",
        runner.READINESS_ROOT / "HASH_MANIFEST.json",
        runner.FINAL_ROOT / "HASH_MANIFEST.json",
    ]:
        assert runner.verify_manifest(path) == []
    assert runner.validate_all() == []

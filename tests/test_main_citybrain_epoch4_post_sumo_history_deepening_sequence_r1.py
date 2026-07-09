from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_post_sumo_history_deepening_sequence_r1.py"

spec = importlib.util.spec_from_file_location("post_sumo_history_deepening", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def ensure_outputs() -> None:
    if not (runner.SEQUENCE_ROOT / "POST_SUMO_HISTORY_DEEPENING_SEQUENCE_DECISION.json").exists():
        runner.build_all()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_required_outputs_exist():
    runner.build_all()
    missing = [runner.rel(path) for path in runner.required_paths() if not path.exists()]
    assert missing == []


def test_non_sumo_domain_engines_do_not_force_sumo():
    ensure_outputs()
    decision = load_json(runner.NON_SUMO_ROOT / "DECISION.json")
    catalog = load_json(runner.NON_SUMO_ROOT / "NON_SUMO_DOMAIN_OPTION_ENGINE_CATALOG.json")
    building = load_json(runner.NON_SUMO_ROOT / "BUILDING_COMPLIANCE_OPTION_ENGINE_REPORT.json")
    permit = load_json(runner.NON_SUMO_ROOT / "PERMIT_INSPECTION_DELAY_OPTION_ENGINE_REPORT.json")
    guard = load_json(runner.NON_SUMO_ROOT / "NO_SUMO_MISAPPLICATION_GUARD.json")
    forecast_guard = load_json(runner.NON_SUMO_ROOT / "NO_FORECAST_AUTHORITY_GUARD.json")
    assert decision["status"] == runner.STATUS_NON_SUMO
    assert decision["non_sumo_engine_count"] == 2
    assert decision["building_compliance_engine_created"] is True
    assert decision["permit_inspection_delay_engine_created"] is True
    assert decision["sumo_misapplied_to_non_traffic_family"] is False
    assert {row["family_id"] for row in catalog["engines"]} == set(runner.NON_SUMO_FAMILIES)
    assert building["sumo_used"] is False
    assert permit["sumo_used"] is False
    assert guard["sumo_forced_on_non_traffic_family"] is False
    assert forecast_guard["ForecastPacket_created"] is False


def test_event_fabric_v2_5_long_history_load_is_deterministic():
    ensure_outputs()
    decision = load_json(runner.EVENT_ROOT / "DECISION.json")
    load = load_json(runner.EVENT_ROOT / "EVENT_FABRIC_V2_5_LOAD_PROFILE_REPORT.json")
    determinism = load_json(runner.EVENT_ROOT / "EVENT_FABRIC_V2_5_DETERMINISM_REPORT.json")
    consumption = load_json(runner.EVENT_ROOT / "EVENT_FABRIC_V2_5_CONSUMPTION_DEPTH_REPORT.json")
    failure = load_json(runner.EVENT_ROOT / "EVENT_FABRIC_V2_5_FAILURE_MODE_REPORT.json")
    rows = runner.read_jsonl(runner.EVENT_ROOT / "EVENT_FABRIC_V2_5_LONG_HISTORY_LOAD_LOG.jsonl")
    assert decision["status"] == runner.STATUS_EVENT
    assert decision["event_count"] >= 1000
    assert decision["family_count"] == 4
    assert decision["logical_snapshot_count"] == 12
    assert decision["replay_deterministic"] is True
    assert load["event_count"] == len(rows)
    assert determinism["stable_across_two_runs"] is True
    assert len(consumption["families"]) == 4
    assert failure["all_required_failure_modes_present"] is True


def test_cer_check_stress_eval_covers_conflicts_downgrades_and_authority_guard():
    ensure_outputs()
    decision = load_json(runner.STRESS_ROOT / "DECISION.json")
    cer = load_json(runner.STRESS_ROOT / "CER_RESOLUTION_STRESS_REPORT.json")
    check = load_json(runner.STRESS_ROOT / "CHECK_V1_STRESS_REPORT.json")
    downgrade = load_json(runner.STRESS_ROOT / "CER_CHECK_DOWNGRADE_AND_CONTRADICTION_REPORT.json")
    authority = load_json(runner.STRESS_ROOT / "NO_AUTHORITY_ESCALATION_GUARD.json")
    fixtures = runner.read_jsonl(runner.STRESS_ROOT / "CER_CHECK_EVENT_STRESS_FIXTURES.jsonl")
    assert decision["status"] == runner.STATUS_STRESS
    assert decision["fixture_count"] >= 400
    assert decision["cer_conflict_cases_present"] is True
    assert decision["check_contradiction_cases_present"] is True
    assert cer["conflict_cases_present"] is True
    assert check["downgrade_cases_present"] is True
    assert downgrade["contradiction_count"] > 0
    assert authority["official_action_created"] is False
    assert len(fixtures) == decision["fixture_count"]


def test_internal_readiness_snapshot_remains_no_session():
    ensure_outputs()
    decision = load_json(runner.READINESS_ROOT / "DECISION.json")
    snapshot = load_json(runner.READINESS_ROOT / "INTERNAL_READINESS_SNAPSHOT_NO_SESSION.json")
    guard = load_json(runner.READINESS_ROOT / "NO_SESSION_NO_FUEL_GUARD.json")
    assert decision["status"] == runner.STATUS_READINESS
    assert decision["ready_for_internal_review_prep"] is True
    assert decision["ready_for_founder_session"] is False
    assert snapshot["ready_for_founder_session"] is False
    assert guard["founder_review_session_run"] is False
    assert guard["operator_or_founder_fuel_created"] is False
    assert guard["dispositions_created"] is False
    assert guard["training_eligibility_created"] is False


def test_final_reverify_and_sequence_status_are_deepening_not_prior_wave():
    ensure_outputs()
    final = load_json(runner.FINAL_ROOT / "DECISION.json")
    sequence = load_json(runner.SEQUENCE_ROOT / "POST_SUMO_HISTORY_DEEPENING_SEQUENCE_DECISION.json")
    execution = load_json(runner.SEQUENCE_ROOT / "POST_SUMO_HISTORY_DEEPENING_SEQUENTIAL_EXECUTION_LOG.json")
    non_sumo_audit = load_json(runner.FINAL_ROOT / "NON_SUMO_DOMAIN_ENGINE_AUDIT.json")
    assert final["status"] == runner.STATUS_FINAL
    assert final["non_sumo_domain_engines_verified"] is True
    assert final["event_fabric_v2_5_load_verified"] is True
    assert final["cer_check_stress_verified"] is True
    assert final["internal_readiness_no_session_verified"] is True
    assert sequence["status"] == runner.STATUS_SEQUENCE
    assert sequence["status"] != "PASS_MAIN_CITYBRAIN_EPOCH4_POST_SUMO_HISTORY_SEQUENCE_R1_WITH_LIMITATIONS"
    assert sequence["all_steps_passed_with_limitations"] is True
    assert execution["parallel_execution_used"] is False
    assert non_sumo_audit["sumo_misapplied_to_non_traffic_family"] is False


def test_hash_manifests_and_validate_all_pass():
    ensure_outputs()
    for path in [
        runner.NON_SUMO_ROOT / "HASH_MANIFEST.json",
        runner.EVENT_ROOT / "HASH_MANIFEST.json",
        runner.STRESS_ROOT / "HASH_MANIFEST.json",
        runner.READINESS_ROOT / "HASH_MANIFEST.json",
        runner.FINAL_ROOT / "HASH_MANIFEST_REVERIFY.json",
        runner.SEQUENCE_ROOT / "HASH_MANIFEST.json",
    ]:
        assert runner.verify_manifest(path) == []
    assert runner.validate_all() == []

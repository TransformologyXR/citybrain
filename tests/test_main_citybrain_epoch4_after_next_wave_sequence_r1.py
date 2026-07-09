from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_after_next_wave_sequence_r1.py"

spec = importlib.util.spec_from_file_location("after_next_wave_sequence", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def ensure_outputs() -> None:
    if not (runner.SEQUENCE_ROOT / "AFTER_NEXT_WAVE_SEQUENCE_DECISION.json").exists():
        runner.build_all()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_required_outputs_exist():
    runner.build_all()
    missing = [runner.rel(path) for path in runner.required_paths() if not path.exists()]
    assert missing == []


def test_simulation_v2_3_sumo_smoke_is_bounded_and_non_forecast():
    ensure_outputs()
    decision = load_json(runner.SIM_ROOT / "DECISION.json")
    report = load_json(runner.SIM_ROOT / "SIMULATION_V2_3_SUMO_REAL_RUN_REPORT.json")
    guard = load_json(runner.SIM_ROOT / "SIMULATION_V2_3_NO_PRODUCT_FORECAST_SURFACE_GUARD.json")
    assert decision["status"] == runner.STATUS_SIM
    assert decision["sumo_executable_detected"] is True
    assert decision["calibrated_simulation_claim_created"] is False
    assert decision["product_forecast_surface_created"] is False
    assert decision["ForecastPacket_created"] is False
    assert guard["ForecastPacket_created"] is False
    assert guard["product_forecast_surface_created"] is False
    if decision["sumo_real_run_smoke_executed"]:
        assert decision["deterministic_across_two_runs"] is True
        assert decision["deterministic_run_hash"]
        assert report["real_run_claim"] == "deterministic_local_sumo_smoke"
        assert report["vehicle_tripinfo_count"] >= 1
    else:
        assert report["real_run_claim"] == "no_real_run_claim"


def test_event_fabric_v2_3_history_diff_replay_hits_targets():
    ensure_outputs()
    decision = load_json(runner.EVENT_ROOT / "DECISION.json")
    bridge = load_json(runner.EVENT_ROOT / "EVENT_FABRIC_V2_3_EVENT_TO_DIFF_BRIDGE_REPORT.json")
    replay = load_json(runner.EVENT_ROOT / "EVENT_FABRIC_V2_3_REPLAY_DETERMINISM_REPORT.json")
    no_live = load_json(runner.EVENT_ROOT / "NO_LIVE_INGESTION_GUARD.json")
    rows = runner.read_jsonl(runner.EVENT_ROOT / "EVENT_FABRIC_V2_3_SNAPSHOT_EVENT_LOG.jsonl")
    assert decision["status"] == runner.STATUS_EVENT
    assert decision["family_count"] == 4
    assert decision["logical_snapshot_count"] == 3
    assert decision["event_count"] >= 80
    assert decision["minimum_targets_met"] is True
    assert bridge["all_required_change_classes_present"] is True
    assert replay["stable_across_two_runs"] is True
    assert no_live["production_live_ingestion_created"] is False
    assert {row["family_id"] for row in rows} == set(runner.ALL_FAMILIES)
    assert set(runner.CHANGE_CLASSES).issubset({row["change_class"] for row in rows})


def test_pilot_evidence_binder_is_no_session_no_fuel():
    ensure_outputs()
    decision = load_json(runner.BINDER_ROOT / "DECISION.json")
    index = load_json(runner.BINDER_ROOT / "PILOT_EVIDENCE_BINDER_INDEX.json")
    no_session = load_json(runner.BINDER_ROOT / "FOUNDER_REVIEW_NOT_RUN_GUARD.json")
    no_fuel = load_json(runner.BINDER_ROOT / "NO_FUEL_NO_DISPOSITION_GUARD.json")
    assert decision["status"] == runner.STATUS_BINDER
    assert decision["simulation_v2_3_included"] is True
    assert decision["event_fabric_v2_3_included"] is True
    assert decision["founder_review_session_run"] is False
    assert decision["operator_or_founder_fuel_created"] is False
    assert decision["dispositions_created"] is False
    assert index["no_session"] is True
    assert no_session["session_results_created"] is False
    assert no_session["training_eligibility_created"] is False
    assert no_fuel["operator_fuel_created"] is False
    assert no_fuel["dispositions_created"] is False


def test_final_reverify_confirms_claims_and_sequence():
    ensure_outputs()
    final = load_json(runner.FINAL_ROOT / "DECISION.json")
    sim_audit = load_json(runner.FINAL_ROOT / "SIMULATION_REAL_RUN_CLAIM_AUDIT.json")
    event_audit = load_json(runner.FINAL_ROOT / "EVENT_HISTORY_DIFF_REPLAY_AUDIT.json")
    binder_audit = load_json(runner.FINAL_ROOT / "PILOT_BINDER_NO_SESSION_AUDIT.json")
    sequence = load_json(runner.SEQUENCE_ROOT / "AFTER_NEXT_WAVE_SEQUENCE_DECISION.json")
    execution = load_json(runner.SEQUENCE_ROOT / "AFTER_NEXT_WAVE_SEQUENTIAL_EXECUTION_LOG.json")
    assert final["status"] == runner.STATUS_FINAL
    assert final["all_inputs_found"] is True
    assert final["all_inputs_passed"] is True
    assert final["event_history_diff_replay_verified"] is True
    assert final["pilot_binder_no_session_verified"] is True
    assert sim_audit["product_forecast_surface_created"] is False
    assert sim_audit["ForecastPacket_created"] is False
    assert event_audit["minimum_targets_met"] is True
    assert binder_audit["no_session_guard_passed"] is True
    assert sequence["status"] == runner.STATUS_SEQUENCE
    assert sequence["all_steps_passed_with_limitations"] is True
    assert execution["parallel_execution_used"] is False


def test_hash_manifests_and_validate_all_pass():
    ensure_outputs()
    for path in [
        runner.SIM_ROOT / "HASH_MANIFEST.json",
        runner.EVENT_ROOT / "HASH_MANIFEST.json",
        runner.BINDER_ROOT / "HASH_MANIFEST.json",
        runner.FINAL_ROOT / "HASH_MANIFEST_REVERIFY.json",
        runner.SEQUENCE_ROOT / "HASH_MANIFEST.json",
    ]:
        assert runner.verify_manifest(path) == []
    assert runner.validate_all() == []

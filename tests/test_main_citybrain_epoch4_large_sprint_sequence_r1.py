from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_large_sprint_sequence_r1.py"

spec = importlib.util.spec_from_file_location("epoch4_large_sequence", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_required_outputs_and_contracts_exist():
    missing = [runner.rel(path) for path in runner.required_paths() if not path.exists()]
    assert missing == []


def test_sprint1_consumes_event_r1_and_uses_cer_backed_resolution():
    intake = load_json(runner.OUTPUTS["sprint1"] / "EVENT_FABRIC_V2_R1_INTAKE_REPORT.json")
    decision = load_json(runner.OUTPUTS["sprint1"] / "EVENT_FABRIC_V2_DECISION.json")
    resolution = load_json(runner.OUTPUTS["sprint1"] / "EVENT_TO_CER_RESOLUTION_REPORT.json")
    state = load_json(runner.OUTPUTS["sprint1"] / "EVENT_CURRENT_STATE_V2.json")
    assert intake["status"] == "PASS"
    assert intake["r1_rederived"] is False
    assert decision["status"] == runner.STATUSES["sprint1"]
    assert decision["live_production_claim_created"] is False
    assert resolution["unresolved_promoted_to_truth"] is False
    assert state["counts"]["duplicates"] == 1
    assert state["counts"]["quarantined"] == 1


def test_sprint2_consumes_simulation_r1_and_blocks_forecast_claims():
    intake = load_json(runner.OUTPUTS["sprint2"] / "SIMULATION_V2_R1_INTAKE_REPORT.json")
    decision = load_json(runner.OUTPUTS["sprint2"] / "SIMULATION_V2_DECISION.json")
    options = load_jsonl(runner.OUTPUTS["sprint2"] / "SIMULATION_REVIEW_OPTION_RESULTS_V2.jsonl")
    comparison = load_json(runner.OUTPUTS["sprint2"] / "SIMULATION_OPTION_COMPARISON_REPORT.json")
    assert intake["status"] == "PASS"
    assert intake["r1_rederived"] is False
    assert decision["status"] == runner.STATUSES["sprint2"]
    assert decision["forecast_packet_created"] is False
    assert decision["model_training_created"] is False
    assert len(options) >= 2
    assert comparison["recommendation_authority"] is False


def test_sprint3_scope_is_narrow_and_no_action():
    scope = load_json(runner.OUTPUTS["sprint3"] / "INCIDENT_PLAN_SCOPE_LOCK.json")
    decision = load_json(runner.OUTPUTS["sprint3"] / "INCIDENT_PLAN_PRODUCT_LOOP_DECISION.json")
    no_action = load_json(runner.OUTPUTS["sprint3"] / "INCIDENT_PLAN_NO_ACTION_GUARD.json")
    review_packet = load_json(runner.OUTPUTS["sprint3"] / "INCIDENT_REVIEW_PACKET_R1.json")
    assert scope["event_family_count"] == 1
    assert scope["scenario_type_count"] == 1
    assert scope["scope_expanded"] is False
    assert decision["official_case_or_ticket_created"] is False
    assert decision["dispatch_control_enforcement_created"] is False
    assert no_action["forbidden_capabilities_created"] == []
    assert review_packet["cer_entity_refs"] == ["cer:building:alpha"]


def test_sprint4_no_fabricated_human_fuel():
    decision = load_json(runner.OUTPUTS["sprint4"] / "HUMAN_REVIEW_PILOT_DECISION.json")
    import_report = load_json(runner.OUTPUTS["sprint4"] / "PILOT_SESSION_IMPORT_REPORT.json")
    fuel = load_json(runner.OUTPUTS["sprint4"] / "PILOT_FUEL_ELIGIBILITY_REPORT_R1.json")
    guard = load_json(runner.OUTPUTS["sprint4"] / "PILOT_NO_FABRICATED_HUMAN_SESSION_GUARD.json")
    assert decision["status"] == runner.STATUSES["sprint4"]
    assert decision["fabricated_human_sessions_created"] is False
    assert guard["fabricated_human_sessions_created"] is False
    assert import_report["fabricated_sessions_created"] is False
    assert fuel["learned_arming_allowed"] is False


def test_final_reverify_sequence_and_guards():
    decision = load_json(runner.OUTPUTS["final"] / "EPOCH4_LARGE_SPRINT_FINAL_DECISION.json")
    sequence = load_json(runner.OUTPUTS["final"] / "EPOCH4_LARGE_SPRINT_SEQUENCE_REVERIFY.json")
    guard = load_json(runner.OUTPUTS["final"] / "EPOCH4_LARGE_SPRINT_FORBIDDEN_CAPABILITY_GUARD.json")
    assert decision["status"] == runner.STATUSES["final"]
    assert decision["parallel_execution_used"] is False
    assert decision["sprint3_narrow_scope_verified"] is True
    assert decision["sprint4_no_fabricated_human_sessions"] is True
    assert sequence["parallel_execution_allowed"] is False
    assert sequence["parallel_execution_used"] is False
    assert guard["forbidden_capabilities_created"] == []
    assert guard["forecast_packet_created"] is False
    assert guard["production_live_claim_created"] is False


def test_hash_manifests_verify():
    for key in runner.OUTPUTS:
        assert runner.verify_manifest(runner.OUTPUTS[key] / "HASH_MANIFEST.json") == []


def test_runner_validation_is_clean():
    assert runner.validate_all() == []

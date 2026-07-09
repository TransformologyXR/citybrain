from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_next_wave_sequence_r1.py"

spec = importlib.util.spec_from_file_location("next_wave_sequence", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_required_outputs_exist():
    runner.build_all()
    missing = [runner.rel(path) for path in runner.required_paths() if not path.exists()]
    assert missing == []


def test_consolidation_accounts_for_current_truth_and_boundaries():
    decision = load_json(runner.CONSOLIDATION_ROOT / "DECISION.json")
    ledger = load_json(runner.CONSOLIDATION_ROOT / "CURRENT_TRUTH_LEDGER.json")
    guard = load_json(runner.CONSOLIDATION_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json")
    assert decision["status"] == runner.STATUS_CONSOLIDATION
    assert ledger["current_truth"]["selected_family_count"] == 3
    assert ledger["current_truth"]["source_registry_v1_1_source_count"] == 664
    assert ledger["current_truth"]["diff_fixture_count"] == 32
    assert ledger["current_truth"]["brief_variant_count"] == 3
    assert "founder_review_sessions" in ledger["parked"]
    assert guard["forbidden_capabilities_created"] == []


def test_event_fabric_v2_2_hits_replay_reliability_targets():
    decision = load_json(runner.EVENT_ROOT / "DECISION.json")
    replay = load_json(runner.EVENT_ROOT / "EVENT_FABRIC_V2_2_REPLAY_DETERMINISM_REPORT.json")
    idempotency = load_json(runner.EVENT_ROOT / "EVENT_FABRIC_V2_2_IDEMPOTENCY_REPORT.json")
    quarantine = load_json(runner.EVENT_ROOT / "EVENT_FABRIC_V2_2_QUARANTINE_UNRESOLVED_REPORT.json")
    rows = runner.read_jsonl(runner.EVENT_ROOT / "EVENT_FABRIC_V2_2_STRESS_EVENT_LOG.jsonl")
    assert decision["status"] == runner.STATUS_EVENT
    assert decision["family_count"] == 4
    assert decision["stress_event_count"] == 40
    assert len(rows) == 40
    assert {row["family_id"] for row in rows} == set(runner.ALL_FAMILIES)
    assert replay["stable_across_two_runs"] is True
    assert idempotency["duplicates_suppressed"] == 4
    assert quarantine["record_count"] == 8


def test_simulation_v2_2_is_honest_about_connectors_and_forecasts():
    decision = load_json(runner.SIM_ROOT / "DECISION.json")
    probes = load_json(runner.SIM_ROOT / "SIMULATION_V2_2_CONNECTOR_PROBE_RESULTS.json")
    options = load_json(runner.SIM_ROOT / "SIMULATION_V2_2_OPTION_COMPARISON_BY_FAMILY.json")
    guard = load_json(runner.SIM_ROOT / "NO_PRODUCT_FORECAST_SURFACE_GUARD.json")
    assert decision["status"] == runner.STATUS_SIM
    assert probes["real_connector_run_count"] == 0
    assert {probe["state"] for probe in probes["probes"]}.issubset(set(probes["allowed_states"]))
    assert len(options["families"]) == 3
    assert decision["product_forecast_surface_created"] is False
    assert guard["ForecastPacket_created"] is False


def test_data_maturity_r2_and_pre_founder_are_prep_only():
    data_decision = load_json(runner.DATA_ROOT / "DECISION.json")
    prep_decision = load_json(runner.PREF_ROOT / "DECISION.json")
    no_session = load_json(runner.PREF_ROOT / "FOUNDER_REVIEW_NO_SESSION_GUARD.json")
    queue = load_json(runner.PREF_ROOT / "FOUNDER_REVIEW_TASK_QUEUE_R1.json")
    assert data_decision["status"] == runner.STATUS_DATA
    assert data_decision["remediation_plan_count"] == 4
    assert data_decision["client_public_deployment_claim_created"] is False
    assert prep_decision["status"] == runner.STATUS_PREF
    assert prep_decision["prep_only"] is True
    assert no_session["review_session_results_created"] is False
    assert no_session["operator_or_founder_fuel_captured"] is False
    assert no_session["training_eligibility_created"] is False
    assert queue["task_count"] == 3


def test_final_reverify_and_sequence_validate_everything():
    final = load_json(runner.FINAL_ROOT / "DECISION.json")
    final_input = load_json(runner.FINAL_ROOT / "NEXT_WAVE_INPUT_AUDIT.json")
    sequence = load_json(runner.SEQUENCE_ROOT / "NEXT_WAVE_SEQUENCE_DECISION.json")
    execution_log = load_json(runner.SEQUENCE_ROOT / "SEQUENTIAL_EXECUTION_LOG.json")
    assert final["status"] == runner.STATUS_FINAL
    assert final["all_selected_next_wave_outputs_found"] is True
    assert final["all_selected_next_wave_outputs_passed"] is True
    assert final_input["parallel_execution_used"] is False
    assert sequence["status"] == runner.STATUS_SEQUENCE
    assert sequence["all_steps_passed_with_limitations"] is True
    assert execution_log["parallel_execution_used"] is False
    assert runner.validate_all() == []


def test_hash_manifests_verify():
    for path in [
        runner.CONSOLIDATION_ROOT / "HASH_MANIFEST.json",
        runner.EVENT_ROOT / "HASH_MANIFEST.json",
        runner.SIM_ROOT / "HASH_MANIFEST.json",
        runner.DATA_ROOT / "HASH_MANIFEST.json",
        runner.PREF_ROOT / "HASH_MANIFEST.json",
        runner.FINAL_ROOT / "HASH_MANIFEST_REVERIFY.json",
        runner.SEQUENCE_ROOT / "HASH_MANIFEST.json",
    ]:
        assert runner.verify_manifest(path) == []

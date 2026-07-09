from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_post_sumo_history_sequence_r1.py"

spec = importlib.util.spec_from_file_location("post_sumo_history_sequence", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def ensure_outputs() -> None:
    if not (runner.SEQUENCE_ROOT / "POST_SUMO_HISTORY_SEQUENCE_DECISION.json").exists():
        runner.build_all()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_required_outputs_exist():
    runner.build_all()
    missing = [runner.rel(path) for path in runner.required_paths() if not path.exists()]
    assert missing == []


def test_simulation_v2_4_covers_families_and_preserves_sumo_honesty():
    ensure_outputs()
    decision = load_json(runner.SIM_ROOT / "DECISION.json")
    catalog = load_json(runner.SIM_ROOT / "SIMULATION_V2_4_FAMILY_SCENARIO_CATALOG.json")
    matrix = load_json(runner.SIM_ROOT / "SIMULATION_V2_4_SUMO_RUN_CAPABILITY_MATRIX.json")
    guard = load_json(runner.SIM_ROOT / "SIMULATION_V2_4_NO_FORECAST_AUTHORITY_GUARD.json")
    assert decision["status"] == runner.STATUS_SIM
    assert decision["family_count"] >= 3
    assert decision["real_sumo_smoke_executed"] is True
    assert decision["deterministic_option_runs"] is True
    assert set(decision["sumo_not_applicable_families"]) == {
        "building_compliance_perception_candidate",
        "permit_inspection_delay",
    }
    assert len(catalog["families"]) == 3
    assert matrix["real_sumo_family_count"] == 1
    assert guard["ForecastPacket_created"] is False
    assert guard["product_forecast_surface_created"] is False
    assert guard["calibrated_real_world_simulation_claim_created"] is False


def test_event_fabric_v2_4_scales_and_feeds_consumers():
    ensure_outputs()
    decision = load_json(runner.EVENT_ROOT / "DECISION.json")
    replay = load_json(runner.EVENT_ROOT / "EVENT_FABRIC_V2_4_REPLAY_DETERMINISM_REPORT.json")
    failure = load_json(runner.EVENT_ROOT / "EVENT_FABRIC_V2_4_FAILURE_MODE_REPORT.json")
    watch = load_json(runner.EVENT_ROOT / "EVENT_FABRIC_V2_4_WATCH_ADMISSION_REPORT.json")
    check = load_json(runner.EVENT_ROOT / "EVENT_FABRIC_V2_4_CHECK_ATTACHMENT_REPORT.json")
    brief = load_json(runner.EVENT_ROOT / "EVENT_FABRIC_V2_4_BRIEF_ATTACHMENT_REPORT.json")
    spatial = load_json(runner.EVENT_ROOT / "EVENT_FABRIC_V2_4_SPATIAL_OVERLAY_HANDOFF_REPORT.json")
    rows = runner.read_jsonl(runner.EVENT_ROOT / "EVENT_FABRIC_V2_4_SCALE_REPLAY_LOG.jsonl")
    assert decision["status"] == runner.STATUS_EVENT
    assert decision["event_count"] >= 250
    assert decision["family_count"] == 4
    assert replay["stable_across_two_runs"] is True
    assert failure["all_required_failure_modes_present"] is True
    assert len(rows) >= 250
    assert {row["family_id"] for row in rows} == set(runner.ALL_FAMILIES)
    for report in [watch, check, brief, spatial]:
        assert len(report["families"]) == 4


def test_review_packet_360_v2_has_required_sections_and_no_session_guard():
    ensure_outputs()
    decision = load_json(runner.REVIEW_ROOT / "DECISION.json")
    packets = load_json(runner.REVIEW_ROOT / "REVIEW_PACKET_360_V2_BY_FAMILY.json")
    parity = load_json(runner.REVIEW_ROOT / "PACKET_PARITY_REPORT.json")
    guard = load_json(runner.REVIEW_ROOT / "NO_SESSION_NO_FUEL_GUARD.json")
    assert decision["status"] == runner.STATUS_REVIEW
    assert decision["family_count"] >= 3
    assert parity["all_families_have_required_sections"] is True
    assert parity["simulation_v2_4_refs_present"] is True
    assert parity["event_fabric_v2_4_refs_present"] is True
    for packet in packets["packets"]:
        assert set(runner.REVIEW_SECTIONS).issubset(set(packet["sections"]))
        assert packet["all_required_sections_present"] is True
    assert guard["founder_review_session_run"] is False
    assert guard["operator_or_founder_fuel_created"] is False
    assert guard["dispositions_created"] is False
    assert guard["training_eligibility_created"] is False


def test_final_reverify_and_sequence_are_sequential_and_bounded():
    ensure_outputs()
    final = load_json(runner.FINAL_ROOT / "DECISION.json")
    sim_audit = load_json(runner.FINAL_ROOT / "SIMULATION_V2_4_CLAIM_AUDIT.json")
    event_audit = load_json(runner.FINAL_ROOT / "EVENT_FABRIC_V2_4_CONSUMPTION_AUDIT.json")
    review_audit = load_json(runner.FINAL_ROOT / "REVIEW_PACKET_360_V2_PARITY_AUDIT.json")
    no_session = load_json(runner.FINAL_ROOT / "NO_SESSION_NO_FUEL_AUDIT.json")
    sequence = load_json(runner.SEQUENCE_ROOT / "POST_SUMO_HISTORY_SEQUENCE_DECISION.json")
    execution = load_json(runner.SEQUENCE_ROOT / "POST_SUMO_HISTORY_SEQUENTIAL_EXECUTION_LOG.json")
    assert final["status"] == runner.STATUS_FINAL
    assert final["all_inputs_found"] is True
    assert final["all_inputs_passed"] is True
    assert final["parallel_execution_used"] is False
    assert sim_audit["ForecastPacket_created"] is False
    assert sim_audit["product_forecast_surface_created"] is False
    assert event_audit["minimum_event_count_met"] is True
    assert event_audit["watch_check_brief_spatial_consumption_verified"] is True
    assert review_audit["all_families_have_required_sections"] is True
    assert no_session["guard_passed"] is True
    assert sequence["status"] == runner.STATUS_SEQUENCE
    assert sequence["all_steps_passed_with_limitations"] is True
    assert execution["parallel_execution_used"] is False


def test_hash_manifests_and_validate_all_pass():
    ensure_outputs()
    for path in [
        runner.SIM_ROOT / "HASH_MANIFEST.json",
        runner.EVENT_ROOT / "HASH_MANIFEST.json",
        runner.REVIEW_ROOT / "HASH_MANIFEST.json",
        runner.FINAL_ROOT / "HASH_MANIFEST_REVERIFY.json",
        runner.SEQUENCE_ROOT / "HASH_MANIFEST.json",
    ]:
        assert runner.verify_manifest(path) == []
    assert runner.validate_all() == []

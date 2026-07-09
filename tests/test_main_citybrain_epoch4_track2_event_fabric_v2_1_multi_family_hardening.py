from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_track2_event_fabric_v2_1_multi_family_hardening.py"

spec = importlib.util.spec_from_file_location("track2_event_v2_1", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_required_outputs_and_contracts_exist():
    for name in runner.REQUIRED_OUTPUTS:
        assert (runner.OUTPUT_ROOT / name).exists(), name
    for name in [
        "event_type_registry_v2_1.schema.json",
        "event_family_adapter_v2_1.schema.json",
        "event_story_replay_pack_v2_1.schema.json",
    ]:
        assert (runner.CONTRACT_ROOT / name).exists(), name


def test_registry_contains_control_and_top_three_families():
    registry = load_json(runner.OUTPUT_ROOT / "EVENT_TYPE_REGISTRY_V2_1.json")
    family_ids = {row["family_id"] for row in registry["event_families"]}
    assert registry["family_count"] == 4
    assert family_ids == {
        "mobility_access_interruption",
        "building_compliance_perception_candidate",
        "permit_inspection_delay",
        "city_asset_infrastructure_issue",
    }
    assert all(row["watch_admissible"] for row in registry["event_families"])
    assert all(row["check_required"] for row in registry["event_families"])


def test_adapters_define_family_specific_unresolved_and_quarantine_policy():
    adapters = load_json(runner.OUTPUT_ROOT / "EVENT_FAMILY_ADAPTERS_V2_1.json")["adapters"]
    by_id = {row["family_id"]: row for row in adapters}
    assert by_id["building_compliance_perception_candidate"]["unresolved_reason_policy"] == "proximity_only_or_conflicted_cer_assertion"
    assert by_id["permit_inspection_delay"]["unresolved_reason_policy"] == "conflicting_or_insufficient_source_depth"
    assert by_id["city_asset_infrastructure_issue"]["quarantine_reason_policy"] == "raw_asset_control_or_repair_order_claim"
    for adapter in adapters:
        assert "no_raw_id_bypass" in adapter["cer_requirements"]
        assert adapter["authority_boundary"] == "review_only_no_action"


def test_state_materialization_is_grouped_by_family():
    state = load_json(runner.OUTPUT_ROOT / "EVENT_FAMILY_STATE_MATERIALIZATION_V2_1.json")
    assert state["family_count"] == 4
    for family_id, buckets in state["families"].items():
        assert {"active", "review_required", "quarantined"}.issubset(buckets)
        assert family_id in state["counts_by_family"]
    assert state["counts_by_family"]["city_asset_infrastructure_issue"]["quarantined"] == 1


def test_watch_check_brief_runtime_and_spatial_outputs_cover_all_families():
    watch = load_json(runner.OUTPUT_ROOT / "EVENT_WATCH_ADMISSION_V2_1.json")
    checks = load_jsonl(runner.OUTPUT_ROOT / "EVENT_CHECK_ATTACHMENTS_V2_1.jsonl")
    packets = load_json(runner.OUTPUT_ROOT / "EVENT_BRIEF_RUNTIME_PACKETS_V2_1.json")
    spatial = load_json(runner.OUTPUT_ROOT / "EVENT_SPATIAL_OVERLAY_PACKETS_V2_1.json")
    assert watch["family_count"] == 4
    assert watch["learned_ranking_used"] is False
    assert len(checks) == 4
    assert len(packets["brief_packets"]) == 4
    assert len(packets["runtime_packets"]) == 4
    assert spatial["family_count"] == 4
    assert spatial["live_control_claim_created"] is False


def test_story_replay_packs_and_decision_claim_are_bounded():
    story = load_json(runner.OUTPUT_ROOT / "EVENT_STORY_REPLAY_PACKS_V2_1.json")
    decision = load_json(runner.OUTPUT_ROOT / "EVENT_FABRIC_V2_1_DECISION.json")
    assert story["story_pack_count"] == 4
    assert story["deterministic_replay_hash"]
    assert decision["status"] == runner.FINAL_STATUS
    assert "multiple local/replay event families" in decision["output_claim"]
    assert decision["forbidden_capabilities_created"] == []
    assert decision["production_live_claim_created"] is False
    assert decision["official_action_or_case_created"] is False


def test_hash_manifest_and_validation_are_clean():
    assert runner.verify_manifest() == []
    assert runner.validate_outputs() == []

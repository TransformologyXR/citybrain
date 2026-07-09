from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_main_citybrain_epoch4_product_loop_sequencer_r1.py"

spec = importlib.util.spec_from_file_location("product_loop_sequencer", SCRIPT)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_required_outputs_exist():
    missing = [runner.rel(path) for path in runner.required_paths() if not path.exists()]
    assert missing == []


def test_incident_plan_covers_three_selected_families_and_chain():
    decision = load_json(runner.INCIDENT_ROOT / "INCIDENT_PLAN_THREE_FAMILY_PRODUCT_LOOP_DECISION.json")
    plan = load_json(runner.INCIDENT_ROOT / "THREE_FAMILY_LOOP_PLAN.json")
    assert decision["status"] == runner.STATUS_INCIDENT
    assert decision["selected_families"] == runner.SELECTED_FAMILIES
    assert decision["selected_family_count"] == 3
    assert decision["forbidden_capabilities_created"] == []
    assert plan["required_chain_per_family"] == [
        "event_input",
        "cer_resolution",
        "seg_context",
        "event_state",
        "check_v1",
        "simulation_comparison",
        "brief_v3",
        "watch_admission_or_non_admission",
        "runtime_web_packet",
        "spatial_overlay_packet",
        "workflow_state_packet",
    ]


def test_preconditions_pass_with_track2_alias_recorded():
    audit = load_json(runner.INCIDENT_ROOT / "PRECONDITION_AUDIT.json")
    assert audit["status"] == "PASS"
    rows = {row["track"]: row for row in audit["rows"]}
    for key in ["sprint0", "track1", "track2", "track3", "track4", "track5", "track6", "track7"]:
        assert rows[key]["ok"], key
    assert rows["track2_spec_path_alias"]["status"] == "ALIAS_NOT_PRESENT_ACTUAL_ROOT_USED"


def test_review_packet_360_has_required_sections_for_each_family():
    review = load_json(runner.REVIEW_ROOT / "REVIEW_PACKET_360_BY_FAMILY.json")
    assert review["status"] == "PASS_WITH_LIMITATIONS"
    assert len(review["packets"]) == 3
    for packet in review["packets"]:
        assert set(runner.REVIEW_SECTIONS).issubset(packet["sections"])
        assert packet["all_required_sections_present"] is True
        assert packet["authority_boundary"] == "review_only_no_action"


def test_final_reverify_checks_sequence_hashes_and_forbidden_guard():
    final = load_json(runner.FINAL_ROOT / "PRODUCT_LOOP_FINAL_REVERIFY_DECISION.json")
    sequence = load_json(runner.FINAL_ROOT / "PRODUCT_LOOP_SEQUENCE_AUDIT.json")
    guard = load_json(runner.FINAL_ROOT / "NO_FORBIDDEN_CAPABILITY_GUARD.json")
    manifest = load_json(runner.FINAL_ROOT / "HASH_MANIFEST_REVERIFY.json")
    assert final["status"] == runner.STATUS_FINAL
    assert final["sequence_verified"] is True
    assert final["parallel_execution_used"] is False
    assert final["forbidden_capabilities_created"] == []
    assert sequence["parallel_execution_used"] is False
    assert guard["forbidden_capabilities_created"] == []
    assert manifest["status"] == "PASS"


def test_sequencer_decision_and_manifests_validate():
    sequencer = load_json(runner.SEQUENCER_ROOT / "PRODUCT_LOOP_SEQUENCER_DECISION.json")
    assert sequencer["status"] == runner.STATUS_SEQUENCER
    assert sequencer["final_reverify_status"] == runner.STATUS_FINAL
    for root in [runner.INCIDENT_ROOT, runner.REVIEW_ROOT, runner.FINAL_ROOT, runner.SEQUENCER_ROOT]:
        assert runner.verify_manifest(root / "HASH_MANIFEST.json") == []
    assert runner.validate_all() == []

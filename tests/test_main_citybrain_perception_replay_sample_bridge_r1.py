from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
SCRIPT_PATH = SCRIPTS_DIR / "run_main_citybrain_perception_replay_sample_bridge_r1.py"
spec = importlib.util.spec_from_file_location("perception_bridge", SCRIPT_PATH)
bridge_mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(bridge_mod)


def test_to_r7a_candidate_preserves_candidate_boundaries() -> None:
    row = {
        "class_label": "car",
        "confidence": 0.5,
        "detection_class": "vehicle_presence_candidate",
        "frame_ref": "frame:test:001",
        "observation_id": "source-observation-1",
        "source_file_hash_or_stream_id": "media:test",
        "zone_id": "zone:test",
    }

    candidate = bridge_mod.to_r7a_candidate(row, 1)

    assert candidate["candidate_observation_id"] == "candidate:track-c:replay:001"
    assert candidate["source_class"] == "sensor_inferred"
    assert candidate["review_state"] == "candidate"
    assert "official case/ticket creation" in candidate["cannot_claim"]
    assert "dispatch_control_enforcement" in candidate["not_executed"]
    assert candidate["packet_hash"]


def test_compatibility_report_requires_r7a_keys() -> None:
    candidate = bridge_mod.to_r7a_candidate(
        {
            "class_label": "person",
            "confidence": 0.25,
            "detection_class": "person_presence_candidate",
            "frame_ref": "frame:test:002",
            "observation_id": "source-observation-2",
            "source_file_hash_or_stream_id": "media:test",
            "zone_id": "zone:test",
        },
        2,
    )

    report = bridge_mod.compatibility_report([candidate])

    assert report["status"] == "PASS"
    assert report["r7a_compatible"] is True


def test_boundary_audit_blocks_official_or_action_drift() -> None:
    candidate = bridge_mod.to_r7a_candidate(
        {
            "class_label": "car",
            "confidence": 0.5,
            "detection_class": "vehicle_presence_candidate",
            "frame_ref": "frame:test:003",
            "observation_id": "source-observation-3",
            "source_file_hash_or_stream_id": "media:test",
            "zone_id": "zone:test",
        },
        3,
    )
    candidate["not_executed"] = []

    audit = bridge_mod.boundary_audit([candidate])

    assert audit["status"] == "FAIL"
    assert any(check["check"] == "no_dispatch_control_enforcement" and not check["passed"] for check in audit["checks"])

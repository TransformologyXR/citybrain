from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "run_main_citybrain_sprint2_event_fabric_runtime_spine.py"
spec = importlib.util.spec_from_file_location("event_fabric_runtime_spine", SCRIPT_PATH)
runtime = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(runtime)

from packages.event_fabric import (  # noqa: E402
    ACTIVE_EVENT_VERSION,
    ACTIVE_SCHEMA_VERSION,
    R0ValidationError,
    build_event_from_candidate,
    build_overlay_packets_for_events,
    build_query_result_packet,
    load_event_type_registry,
    load_r0_contract,
    materialize_review_state,
    normalize_legacy_event,
    replay_events,
    write_event_log,
)


class EventFabricRuntimeSpineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = runtime.write_all_outputs()
        cls.events = runtime.sample_events()
        cls.output_root = runtime.OUTPUT_ROOT

    def test_active_contract_is_r0_1_from_corrected_commit(self) -> None:
        contract = load_r0_contract()
        self.assertEqual(contract["active_contract"], "R0.1")
        self.assertEqual(ACTIVE_SCHEMA_VERSION, "citybrain.event_fabric.r0_1")
        self.assertEqual(ACTIVE_EVENT_VERSION, "r0.1")
        self.assertEqual(self.result["runtime"]["r0_1_commit_used"], "5ba2dc1")

    def test_event_type_registry_preserves_allowed_and_forbidden_boundaries(self) -> None:
        registry = load_event_type_registry()
        self.assertIn("review_assist_narrative.attached", registry.allowed_event_types)
        self.assertIn("vss_narrative.created_observation", registry.forbidden_event_types)
        self.assertIn("dispatch.sent", registry.forbidden_event_types)

    def test_sample_events_validate_as_candidate_review_only(self) -> None:
        self.assertTrue(self.events)
        for event in self.events:
            self.assertEqual(event["schema_version"], ACTIVE_SCHEMA_VERSION)
            self.assertEqual(event["event_version"], ACTIVE_EVENT_VERSION)
            self.assertTrue(event["candidate_only"])
            self.assertTrue(event["review_required"])
            self.assertEqual(event["official_status"], "not_official")
            self.assertEqual(event["execution_status"], "not_executed")

    def test_append_log_and_replay_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            write_event_log(path, list(reversed(self.events)))
            report = replay_events(path)
        self.assertTrue(report["deterministic_order"])
        self.assertEqual(report["event_count"], len(self.events))
        self.assertEqual(report["event_ids"], sorted(report["event_ids"]))

    def test_materialized_state_carries_r0_1_common_fields(self) -> None:
        state = materialize_review_state(self.events)
        self.assertEqual(state["schema_version"], ACTIVE_SCHEMA_VERSION)
        self.assertEqual(state["state_version"], ACTIVE_EVENT_VERSION)
        self.assertIn("check_status_counts", state)
        self.assertIn("authority_level_counts", state)
        self.assertIn("review_assist_narratives", state)

    def test_query_packet_rejects_raw_query_authority(self) -> None:
        packet = build_query_result_packet("test_lookup", self.events)
        self.assertFalse(packet["raw_query_authority"])
        packet["raw_query_authority"] = True
        from packages.event_fabric import validate_query_result_packet

        with self.assertRaises(R0ValidationError):
            validate_query_result_packet(packet)

    def test_overlay_packets_are_marker_only_without_live_kit_claim(self) -> None:
        overlays = build_overlay_packets_for_events(self.events)
        self.assertEqual(len(overlays), len(self.events))
        for overlay in overlays:
            self.assertTrue(overlay["marker_metadata_only"])
            self.assertFalse(overlay["live_kit_control"])
            self.assertFalse(overlay["full_citywide_twin_claim"])
            self.assertEqual(overlay["execution_status"], "not_executed")

    def test_conformance_fixtures_pass_shared_r0_1_validator(self) -> None:
        report = runtime.conformance_fixture_results()
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["shared_r0_1_validator_status"], "PASS")
        self.assertGreaterEqual(report["fixture_count"], 6)

    def test_r7b_legacy_events_normalize_into_r0_1_without_contract_relaxation(self) -> None:
        path = ROOT / "outputs" / "main_citybrain_r7b_perception_to_event_fabric_local_replay" / "R7B_LOCAL_EVENT_LOG.jsonl"
        first = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        normalized = normalize_legacy_event(first)
        self.assertEqual(normalized["event_version"], ACTIVE_EVENT_VERSION)
        self.assertEqual(normalized["schema_version"], ACTIVE_SCHEMA_VERSION)
        self.assertEqual(normalized["submission_status"], "not_submitted")
        self.assertEqual(normalized["official_status"], "not_official")

    def test_track_c_sample_candidates_can_build_r0_1_events(self) -> None:
        path = ROOT / "outputs" / "main_citybrain_perception_replay_sample_bridge_r1" / "PERCEPTION_REPLAY_CANDIDATE_OBSERVATIONS.json"
        first = json.loads(path.read_text(encoding="utf-8"))["items"][0]
        event = build_event_from_candidate(first, event_id="event:r0.1:test:track-c:0001", event_type="candidate_observation.accepted_for_review")
        self.assertEqual(event["source_class"], "sensor_inferred")
        self.assertEqual(event["official_status"], "not_official")
        self.assertTrue(event["evidence_refs"])

    def test_boundary_audit_preserves_non_claims(self) -> None:
        audit = runtime.boundary_audit()
        self.assertEqual(audit["status"], "PASS")
        checks = audit["checks"]
        self.assertTrue(checks["no_live_camera"])
        self.assertTrue(checks["no_production_api"])
        self.assertTrue(checks["no_official_case_ticket_submission"])
        self.assertTrue(checks["no_dispatch_control_enforcement"])
        self.assertTrue(checks["vss_not_fact_source"])

    def test_forbidden_event_and_payload_fields_are_rejected(self) -> None:
        candidate = {
            "candidate_observation_ref": "candidate-observation:r0.1:bad",
            "source_class": "sensor_inferred",
            "raw_query": "dispatch someone",
        }
        with self.assertRaises(R0ValidationError):
            build_event_from_candidate(candidate, event_id="event:r0.1:bad:0001", event_type="dispatch.sent")
        with self.assertRaises(R0ValidationError):
            build_event_from_candidate(candidate, event_id="event:r0.1:bad:0002", event_type="candidate_observation.accepted_for_review")

    def test_required_outputs_exist_and_hash_manifest_verifies(self) -> None:
        required = {
            "EVENT_FABRIC_RUNTIME_SPINE_DECISION.json",
            "EVENT_FABRIC_RUNTIME_SPINE_API_OVERVIEW.md",
            "EVENT_FABRIC_RUNTIME_SPINE_EVENT_TYPE_REGISTRY_REPORT.json",
            "EVENT_FABRIC_RUNTIME_SPINE_CONFORMANCE_FIXTURE_RESULTS.json",
            "EVENT_FABRIC_RUNTIME_SPINE_SAMPLE_EVENT_LOG.jsonl",
            "EVENT_FABRIC_RUNTIME_SPINE_REPLAY_REPORT.json",
            "EVENT_FABRIC_RUNTIME_SPINE_MATERIALIZED_STATE.json",
            "EVENT_FABRIC_RUNTIME_SPINE_QUERY_RESULTS.json",
            "EVENT_FABRIC_RUNTIME_SPINE_OVERLAY_PACKETS.json",
            "EVENT_FABRIC_RUNTIME_SPINE_COMPATIBILITY_REPORT.json",
            "EVENT_FABRIC_RUNTIME_SPINE_BOUNDARY_AUDIT.json",
            "EVENT_FABRIC_RUNTIME_SPINE_TEST_LOG.md",
            "EVENT_FABRIC_RUNTIME_SPINE_HASH_MANIFEST.json",
        }
        present = {path.name for path in self.output_root.iterdir() if path.is_file()}
        self.assertTrue(required.issubset(present))
        self.assertEqual(runtime.verify_hash_manifest(self.output_root, "EVENT_FABRIC_RUNTIME_SPINE_HASH_MANIFEST.json")["status"], "PASS")


if __name__ == "__main__":
    unittest.main()

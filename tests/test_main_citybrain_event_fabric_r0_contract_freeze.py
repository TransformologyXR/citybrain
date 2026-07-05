from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "run_main_citybrain_event_fabric_r0_contract_freeze.py"
spec = importlib.util.spec_from_file_location("event_fabric_r0", SCRIPT_PATH)
event_r0 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(event_r0)


class EventFabricR0ContractFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = event_r0.write_all_outputs()
        cls.fixtures = event_r0.conformance_fixtures()
        cls.source_registry = event_r0.source_class_registry()
        cls.event_type_registry = event_r0.event_type_registry()

    def test_all_required_artifacts_exist_and_json_parses(self) -> None:
        required = {
            "EVENT_FABRIC_R0_CONTRACT_FREEZE_DECISION.json",
            "EVENT_FABRIC_R0_EXISTING_SHAPE_INVENTORY.md",
            "EVENT_FABRIC_R0_CONTRACT_OVERVIEW.md",
            "EVENT_FABRIC_R0_CANDIDATE_OBSERVATION_SCHEMA.json",
            "EVENT_FABRIC_R0_EVENT_ENVELOPE_SCHEMA.json",
            "EVENT_FABRIC_R0_EVENT_TYPE_REGISTRY.json",
            "EVENT_FABRIC_R0_SOURCE_CLASS_REGISTRY.json",
            "EVENT_FABRIC_R0_REVIEW_STATE_SCHEMA.json",
            "EVENT_FABRIC_R0_MATERIALIZED_REVIEW_STATE_SCHEMA.json",
            "EVENT_FABRIC_R0_QUERY_RESULT_PACKET_SCHEMA.json",
            "EVENT_FABRIC_R0_OVERLAY_PACKET_SCHEMA.json",
            "EVENT_FABRIC_R0_CONFORMANCE_FIXTURES.json",
            "EVENT_FABRIC_R0_COMPATIBILITY_MATRIX.md",
            "EVENT_FABRIC_R0_BOUNDARY_AND_NON_CLAIMS.md",
            "EVENT_FABRIC_R0_TRACK_HANDOFF_REQUIREMENTS.md",
            "EVENT_FABRIC_R0_TEST_LOG.md",
            "EVENT_FABRIC_R0_HASH_MANIFEST.json",
        }
        present = {path.name for path in event_r0.OUTPUT_ROOT.iterdir() if path.is_file()}
        self.assertTrue(required.issubset(present))
        for path in event_r0.OUTPUT_ROOT.glob("*.json"):
            json.loads(path.read_text(encoding="utf-8"))

    def test_required_source_classes_exist_and_vss_is_not_fact_source(self) -> None:
        classes = self.source_registry["source_classes"]
        self.assertTrue(set(event_r0.REQUIRED_SOURCE_CLASSES).issubset(classes))
        self.assertFalse(classes["model_generated_narrative_not_fact_source"]["fact_source"])
        self.assertTrue(self.source_registry["vss_not_fact_source"])

    def test_forbidden_event_types_are_not_allowed(self) -> None:
        allowed = set(self.event_type_registry["allowed_event_types"])
        self.assertFalse(allowed.intersection(event_r0.FORBIDDEN_EVENT_TYPES))
        self.assertIn("dispatch.sent", self.event_type_registry["forbidden_event_types"])

    def test_candidate_observation_fixture_preserves_boundary(self) -> None:
        candidate = self.fixtures["candidate_observations"][0]
        self.assertTrue(candidate["candidate_only"])
        self.assertTrue(candidate["review_required"])
        self.assertEqual(candidate["official_status"], "not_official")
        self.assertIn("no official submission", candidate["not_executed"])

    def test_event_envelope_preserves_refs_and_no_execution(self) -> None:
        event = self.fixtures["event_envelopes"][0]
        self.assertTrue(event["evidence_refs"])
        self.assertTrue(event["limitation_refs"])
        self.assertTrue(event["trace_refs"])
        self.assertEqual(event["execution_status"], "not_executed")
        self.assertEqual(event["submission_status"], "not_submitted")

    def test_query_result_packet_does_not_use_raw_query_as_authority(self) -> None:
        query = self.fixtures["query_result_packets"][0]
        self.assertNotIn("raw_query", query)
        self.assertTrue(query["safe_next_looks"])
        self.assertEqual(query["official_status_summary"], {"not_official": 1})

    def test_overlay_packet_is_marker_metadata_only(self) -> None:
        overlay = self.fixtures["overlay_packets"][0]
        self.assertTrue(overlay["marker_metadata_only"])
        self.assertTrue(overlay["candidate_only"])
        self.assertEqual(overlay["official_status"], "not_official")
        self.assertTrue(overlay["proposed_prim_path"].startswith("/"))

    def test_draft_cases_and_action_proposals_remain_non_executed(self) -> None:
        materialized = self.fixtures["materialized_review_states"][0]
        self.assertEqual(materialized["sandbox_draft_cases"][0]["submission_status"], "draft_not_submitted")
        self.assertEqual(materialized["not_executed_action_proposals"][0]["execution_status"], "not_executed")

    def test_no_forbidden_runtime_fields_appear_in_fixtures(self) -> None:
        self.assertEqual([], event_r0.forbidden_field_hits(self.fixtures))
        self.assertEqual(event_r0.contract_checks()["status"], "PASS")

    def test_hash_manifests_verify(self) -> None:
        self.assertEqual(event_r0.verify_hash_manifest(event_r0.OUTPUT_ROOT, "EVENT_FABRIC_R0_HASH_MANIFEST.json")["status"], "PASS")
        self.assertEqual(event_r0.verify_hash_manifest(event_r0.CLOSEOUT_ROOT, "EVENT_FABRIC_R0_CONTRACT_FREEZE_CLOSEOUT_HASH_MANIFEST.json")["status"], "PASS")
        self.assertEqual(event_r0.verify_hash_manifest(event_r0.FINAL_ROOT, "EVENT_FABRIC_R0_CONTRACT_FREEZE_FINAL_STATUS_HASH_MANIFEST.json")["status"], "PASS")


if __name__ == "__main__":
    unittest.main()

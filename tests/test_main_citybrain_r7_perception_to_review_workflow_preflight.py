import json
import os
import subprocess
import unittest
import zipfile
from pathlib import Path

from scripts.run_main_citybrain_r7_perception_to_review_workflow_preflight import (
    OUTPUT_ROOT,
    build_r7_bundle,
    candidate_observation_fixture,
    create_action_proposal,
    create_draft_case_ticket,
    map_candidate_to_event_packet,
    review_promotion_fixture,
    validate_action_proposal,
    validate_candidate_observation,
    validate_draft_case_ticket,
    validate_review_promotion,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainR7PerceptionToReviewWorkflowPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(
            [".venv\\Scripts\\python.exe", "scripts\\run_main_citybrain_r7_perception_to_review_workflow_preflight.py"],
            cwd=ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "CITYBRAIN_R7_SKIP_TEST_RUNS": "1"},
        )
        cls.bundle = build_r7_bundle()

    def test_candidate_observation_schema_and_hash(self):
        observation = candidate_observation_fixture()
        self.assertEqual([], validate_candidate_observation(observation))
        self.assertEqual("candidate", observation["review_state"])
        self.assertEqual("not_executed", observation["no_action_state"])
        self.assertIn("frame:r7:demo-west-gate-clip-001:000420", observation["evidence_refs"])

    def test_perception_maps_to_candidate_event_not_truth(self):
        observation = candidate_observation_fixture()
        event_packet = map_candidate_to_event_packet(observation)
        self.assertEqual(observation["candidate_observation_id"], event_packet["source_candidate_observation_id"])
        self.assertEqual("candidate_not_confirmed", event_packet["event_truth_status"])
        self.assertTrue(event_packet["requires_human_review"])
        self.assertEqual("not_executed", event_packet["execution_status"])

    def test_review_promotion_gate_requires_reviewer_note(self):
        promotion = review_promotion_fixture(candidate_observation_fixture())
        self.assertEqual([], validate_review_promotion(promotion))
        missing_note = dict(promotion)
        missing_note["reviewer_note"] = ""
        missing_note["audit_hash"] = promotion["audit_hash"]
        self.assertIn("reviewer_note_required", validate_review_promotion(missing_note))

    def test_draft_case_ticket_is_sandbox_not_submitted(self):
        observation = candidate_observation_fixture()
        promotion = review_promotion_fixture(observation)
        draft = create_draft_case_ticket(observation, promotion)
        self.assertEqual([], validate_draft_case_ticket(draft))
        self.assertEqual("draft_not_submitted", draft["submission_status"])
        self.assertEqual("local_sandbox_adapter", draft["submission_adapter"])
        self.assertEqual("not_executed", draft["no_action_state"])

    def test_action_proposal_remains_not_executed(self):
        observation = candidate_observation_fixture()
        promotion = review_promotion_fixture(observation)
        draft = create_draft_case_ticket(observation, promotion)
        proposal = create_action_proposal(draft)
        self.assertEqual([], validate_action_proposal(proposal))
        self.assertTrue(proposal["approval_required"])
        self.assertEqual("not_approved", proposal["approval_state"])
        self.assertEqual("not_executed", proposal["execution_status"])
        self.assertFalse(any(proposal["prohibited_autonomy_audit"].values()))

    def test_forbidden_official_execution_claims_absent(self):
        serialized = json.dumps(self.bundle, sort_keys=True).lower()
        self.assertNotIn('"submission_status": "submitted"', serialized)
        self.assertNotIn('"execution_status": "executed"', serialized)
        self.assertNotIn('"autonomous_dispatch": true', serialized)
        self.assertNotIn('"traffic_control": true', serialized)
        self.assertNotIn('"enforcement": true', serialized)
        self.assertNotIn('"official_submission": true', serialized)
        self.assertNotIn('"legal_or_certified_finding": true', serialized)
        self.assertNotIn('"llm_decision": true', serialized)

    def test_webui_and_kit_review_packets_expose_statuses(self):
        webui = self.bundle["webui_packets"][0]
        kit = self.bundle["kit_packets"][0]
        for packet in [webui, kit]:
            self.assertIn("candidate observation", packet["visible_labels"])
            self.assertIn("draft_not_submitted", packet["visible_labels"])
            self.assertIn("not_executed", packet["visible_labels"])

    def test_runner_outputs_required_reports(self):
        required = [
            "ENTRY_PROMPT.md",
            "README.md",
            "DECISION.json",
            "CANDIDATE_OBSERVATION_INGRESS_AUDIT.json",
            "PERCEPTION_SOURCE_PROVENANCE_AUDIT.json",
            "CHECK_CLAIMABILITY_AUDIT.json",
            "HUMAN_REVIEW_PROMOTION_GATE_AUDIT.json",
            "CASE_TICKET_DRAFT_ADAPTER_AUDIT.json",
            "ACTION_PROPOSAL_BOUNDARY_AUDIT.json",
            "WEBUI_KIT_REVIEW_SURFACE_AUDIT.json",
            "ONE_TRUTH_PACKET_AUDIT.json",
            "BOUNDARY_AUDIT.json",
            "TEST_LOG.txt",
            "LIMITATIONS.md",
            "HASH_MANIFEST.txt",
            "citybrain_r7_perception_to_review_workflow_preflight.zip",
            "fixtures/camera_source_registry.json",
            "fixtures/candidate_observation_schema.json",
            "fixtures/review_promotion_schema.json",
            "fixtures/draft_case_ticket_schema.json",
            "fixtures/action_proposal_schema.json",
            "candidate_observations/candidate_observations.jsonl",
            "candidate_observations/candidate_observation_event_packets.jsonl",
            "draft_workflow_packets/draft_case_ticket_packets.jsonl",
            "draft_workflow_packets/draft_case_ticket_examples.json",
            "action_proposals/action_proposals.jsonl",
            "action_proposals/prohibited_autonomy_audit.json",
            "webui_evidence/review_surface_snapshot.html",
            "kit_evidence/review_overlay_packet_refs.json",
            "source_refs/perception_adapter_refs.txt",
            "source_refs/webui_refs.txt",
            "source_refs/kit_refs.txt",
            "source_refs/runner_ref.txt",
        ]
        for name in required:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        decision = json.loads((OUTPUT_ROOT / "DECISION.json").read_text(encoding="utf-8"))
        self.assertTrue(decision["status"].startswith("PASS_"))
        self.assertEqual("PASS_R7E_PERCEPTION_TO_REVIEW_WORKFLOW_SMOKE_WITH_LIMITATIONS", decision["status"])
        self.assertEqual("not_executed", decision["execution_status"])
        self.assertFalse(decision["official_submission_performed"])
        self.assertFalse(decision["autonomous_action_performed"])
        self.assertEqual(0, decision["failure_count"])

    def test_zip_package_integrity(self):
        zip_path = OUTPUT_ROOT / "citybrain_r7_perception_to_review_workflow_preflight.zip"
        with zipfile.ZipFile(zip_path, "r") as archive:
            self.assertIsNone(archive.testzip())
            names = set(archive.namelist())
        self.assertIn("DECISION.json", names)
        self.assertIn("candidate_observations/candidate_observations.jsonl", names)
        self.assertIn("action_proposals/action_proposals.jsonl", names)

    def test_hash_manifest_verifies(self):
        manifest = (OUTPUT_ROOT / "HASH_MANIFEST.txt").read_text(encoding="utf-8").splitlines()
        self.assertIn("HASH_MANIFEST_STATUS: PASS", manifest[0])
        entries = [line for line in manifest if "  " in line]
        self.assertGreaterEqual(len(entries), 15)
        for entry in entries:
            digest, _bytes, rel_path = entry.split("  ", 2)
            target = OUTPUT_ROOT / rel_path
            self.assertTrue(target.exists(), rel_path)
            self.assertEqual(64, len(digest))


if __name__ == "__main__":
    unittest.main()

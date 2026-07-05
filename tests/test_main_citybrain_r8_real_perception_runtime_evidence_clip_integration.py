import json
import os
import shutil
import subprocess
import unittest
import zipfile
from pathlib import Path

from scripts.run_main_citybrain_r8_real_perception_runtime_evidence_clip_integration import (
    OUTPUT_ROOT,
    PASS_STATUS,
    action_proposal,
    build_r8_bundle,
    draft_case_ticket,
    forbidden_boundary_failures,
    review_promotion,
    validate_required,
    REQUIRED_DETECTION_FIELDS,
    REQUIRED_EVIDENCE_CLIP_FIELDS,
    REQUIRED_OBSERVATION_FIELDS,
    REQUIRED_SOURCE_FIELDS,
    write_outputs,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[1]
TEST_OUTPUT_ROOT = ROOT / "outputs" / "_test_main_citybrain_r8_real_perception_runtime_evidence_clip_integration"


class MainCityBrainR8RealPerceptionRuntimeEvidenceClipIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if TEST_OUTPUT_ROOT.exists():
            shutil.rmtree(TEST_OUTPUT_ROOT)
        write_outputs(
            root=TEST_OUTPUT_ROOT,
            tests={"targeted_r8": "TEST_SETUP", "full_discovery": "TEST_SETUP", "test_count": 0},
        )
        cls.output_root = TEST_OUTPUT_ROOT
        cls.bundle = build_r8_bundle(TEST_OUTPUT_ROOT)

    def test_source_registry_has_local_replay_media_and_hash(self):
        source = self.bundle["source"]
        self.assertEqual([], validate_required(source, REQUIRED_SOURCE_FIELDS))
        self.assertEqual("local_replay", source["source_mode"])
        self.assertIn("demo/replay", source["privacy_boundary"])
        self.assertEqual(64, len(source["source_hash"]))

    def test_runtime_detection_metadata_schema(self):
        detection = self.bundle["runtime_detections"][0]
        self.assertEqual([], validate_required(detection, REQUIRED_DETECTION_FIELDS))
        self.assertEqual("Metropolis-style local replay adapter", detection["runtime_name"])
        self.assertEqual("person_like_shape", detection["detected_class"])
        self.assertGreater(detection["confidence"], 0)
        self.assertLessEqual(detection["confidence"], 1)

    def test_candidate_observation_export_remains_candidate_only(self):
        observation = self.bundle["candidate_observations"][0]
        self.assertEqual([], validate_required(observation, REQUIRED_OBSERVATION_FIELDS))
        self.assertEqual("candidate", observation["review_state"])
        self.assertEqual("not_executed", observation["no_action_state"]["execution_state"])
        self.assertFalse(observation["pixel_derived_truth_used"])
        self.assertFalse(observation["vss_output_used_as_truth"])

    def test_evidence_frame_and_clip_hashes_verify(self):
        evidence = self.bundle["evidence_clips"][0]
        self.assertEqual([], validate_required(evidence, REQUIRED_EVIDENCE_CLIP_FIELDS))
        frame = self.output_root / evidence["frame_path"]
        clip = self.output_root / evidence["clip_path"]
        self.assertTrue(frame.exists())
        self.assertTrue(clip.exists())
        self.assertEqual(evidence["frame_hash"], sha256_file(frame))
        self.assertEqual(evidence["clip_hash"], sha256_file(clip))

    def test_vss_review_assist_is_not_truth(self):
        assist = self.bundle["vss_review_assist"][0]
        self.assertEqual("review_assistance_only", assist["truth_role"])
        self.assertFalse(assist["vss_output_used_as_truth"])
        self.assertIn("not used as candidate truth", " ".join(assist["limitations"]))

    def test_review_gate_draft_and_action_boundaries(self):
        observation = self.bundle["candidate_observations"][0]
        promotion = review_promotion(observation)
        self.assertTrue(promotion["reviewer_note"])
        draft = draft_case_ticket(observation, promotion)
        self.assertEqual("draft_not_submitted", draft["submission_status"])
        self.assertFalse(draft["official_submission_performed"])
        proposal = action_proposal(draft)
        self.assertEqual("not_executed", proposal["execution_status"])
        self.assertFalse(any(proposal["prohibited_autonomy_audit"].values()))

    def test_webui_and_kit_review_packets_show_evidence_and_no_action(self):
        for packet in self.bundle["review_packets"]:
            labels = packet["visible_labels"]
            self.assertIn("candidate observation", labels)
            self.assertIn("evidence frame", labels)
            self.assertIn("evidence clip", labels)
            self.assertIn("draft_not_submitted", labels)
            self.assertIn("not_executed", labels)

    def test_forbidden_claims_absent_and_bad_claims_fail(self):
        self.assertEqual([], forbidden_boundary_failures(self.bundle))
        bad = dict(self.bundle)
        bad["action_proposals"] = [{"execution_status": "executed", "official_submission": True}]
        failures = forbidden_boundary_failures(bad)
        self.assertIn('"execution_status": "executed"', failures)
        self.assertIn('"official_submission": true', failures)

    def test_runner_outputs_required_package(self):
        required = [
            "ENTRY_PROMPT.md",
            "README.md",
            "DECISION.json",
            "PERCEPTION_SOURCE_REGISTRY_AUDIT.json",
            "RUNTIME_ADAPTER_EXECUTION_REPORT.json",
            "RUNTIME_DETECTION_METADATA_AUDIT.json",
            "CANDIDATE_OBSERVATION_EXPORT_AUDIT.json",
            "EVIDENCE_FRAME_CLIP_EXPORT_AUDIT.json",
            "VSS_REVIEW_ASSIST_AUDIT.json",
            "CHECK_CLAIMABILITY_AUDIT.json",
            "WEBUI_KIT_REVIEW_INTEGRATION_AUDIT.json",
            "DRAFT_WORKFLOW_BOUNDARY_AUDIT.json",
            "ACTION_PROPOSAL_BOUNDARY_AUDIT.json",
            "ONE_TRUTH_PACKET_AUDIT.json",
            "BOUNDARY_AUDIT.json",
            "TEST_LOG.txt",
            "LIMITATIONS.md",
            "HASH_MANIFEST.txt",
            "source_media/MEDIA_INVENTORY.json",
            "runtime_logs/runtime_execution.log",
            "runtime_metadata/runtime_detections.jsonl",
            "candidate_observations/candidate_observations.jsonl",
            "candidate_observations/candidate_observation_event_packets.jsonl",
            "evidence_frames/evidence_frame_manifest.json",
            "evidence_frames/frame_exports/r8_frame_000420.ppm",
            "evidence_clips/evidence_clip_manifest.json",
            "evidence_clips/clip_exports/r8_clip_000410_000450.json",
            "vss_review_assist/vss_review_assist_packets.jsonl",
            "review_packets/perception_review_packets.jsonl",
            "draft_workflow_packets/draft_case_ticket_packets.jsonl",
            "action_proposals/action_proposals.jsonl",
            "webui_evidence/perception_review_surface_snapshot.html",
            "kit_evidence/perception_overlay_packet_refs.json",
            "source_refs/deepstream_or_metropolis_refs.txt",
            "source_refs/vss_refs.txt",
            "source_refs/webui_refs.txt",
            "source_refs/kit_refs.txt",
            "source_refs/runner_ref.txt",
        ]
        for name in required:
            self.assertTrue((self.output_root / name).exists(), name)
        decision = json.loads((self.output_root / "DECISION.json").read_text(encoding="utf-8"))
        self.assertEqual(PASS_STATUS, decision["status"])
        self.assertEqual("not_executed", decision["execution_status"])
        self.assertFalse(decision["official_submission_performed"])
        self.assertFalse(decision["autonomous_action_performed"])
        self.assertFalse(decision["pixel_derived_truth_used"])
        self.assertFalse(decision["vss_output_used_as_truth"])

    def test_hash_manifest_and_zip_verify(self):
        manifest = (self.output_root / "HASH_MANIFEST.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual("HASH_MANIFEST_STATUS: PASS", manifest[0])
        for line in manifest[3:]:
            digest, _bytes, rel_path = line.split("  ", 2)
            target = self.output_root / rel_path
            self.assertTrue(target.exists(), rel_path)
            self.assertEqual(64, len(digest))
        with zipfile.ZipFile(self.output_root / "citybrain_r8_real_perception_runtime_evidence_clip_integration.zip") as archive:
            self.assertIsNone(archive.testzip())
            names = set(archive.namelist())
        self.assertIn("DECISION.json", names)
        self.assertIn("evidence_frames/frame_exports/r8_frame_000420.ppm", names)
        self.assertIn("evidence_clips/clip_exports/r8_clip_000410_000450.json", names)


if __name__ == "__main__":
    unittest.main()

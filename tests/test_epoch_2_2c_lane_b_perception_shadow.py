import json
import unittest

from scripts.run_epoch_2_2c_lane_b_perception_shadow import (
    NON_GOALS,
    OUTPUT_ROOT,
    PASS_STATUS,
    check_prerequisite_gate,
    validate_outputs,
    write_all_outputs,
)


class Epoch22cLaneBPerceptionShadowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = write_all_outputs()
        cls.gate = cls.result["gate"]
        cls.source = cls.result["source"]
        cls.expectation = cls.result["expectation"]
        cls.shadow_run = cls.result["run"]
        cls.check = cls.result["check"]
        cls.visibility = cls.result["visibility"]
        cls.negative = cls.result["negative"]
        cls.decision = cls.result["decision"]

    def test_prerequisite_gate_passes(self):
        self.assertEqual("PASS", self.gate["status"], self.gate["errors"])
        self.assertEqual("main", self.gate["branch"])
        self.assertEqual("PASS_PUSH_2_2B_INTEGRATION", self.gate["integration_status"])
        self.assertEqual("PASS", self.gate["allowed_flag_value"])
        self.assertTrue(any("live_source_onboarding_policy_v1.md" in ref for ref in self.gate["live_source_policy_refs"]))

    def test_required_artifacts_exist(self):
        for name in [
            "PERCEPTION_SHADOW_DECISION.json",
            "PERCEPTION_SHADOW_REPORT.md",
            "SOURCE_REGISTRY_ENTRY.json",
            "SHADOW_RUN_REPORT.json",
            "CHECK_DETECTION_SUFFICIENCY_REPORT.json",
            "SHADOW_EXPECTATION_SPEC.json",
            "REVIEW_VISIBILITY_DECISION.json",
            "NEGATIVE_TEST_REPORT.json",
            "HASH_MANIFEST.json",
        ]:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_single_source_policy_and_retention_compliance(self):
        self.assertEqual(1, self.source["feed_count"])
        self.assertEqual("perception_shadow_service", self.source["service_id"])
        self.assertEqual("media_evidence", self.source["source_class"])
        self.assertFalse(self.source["policy_compliance"]["production_network_or_api_access_required"])
        self.assertFalse(self.source["policy_compliance"]["public_api_or_internet_exposure_allowed"])
        self.assertFalse(self.source["policy_compliance"]["live_cctv_claim"])
        self.assertEqual(0, self.source["retention_privacy_profile"]["privacy_policy_failures"])
        self.assertEqual(0, self.source["retention_privacy_profile"]["retention_policy_failures"])

    def test_raw_frame_visibility_and_identity_boundaries(self):
        raw_policy = self.source["raw_frame_visibility_policy"]
        self.assertFalse(raw_policy["raw_frame_visible_to_review_surface"])
        self.assertTrue(raw_policy["raw_frame_admin_privacy_reviewer_only"])
        self.assertTrue(raw_policy["review_surface_uses_redacted_clip_or_hash_refs_only"])
        self.assertFalse(raw_policy["raw_media_live_storage_enabled"])
        self.assertFalse(self.source["identity_biometric_inference"]["enabled"])

    def test_shadow_run_numeric_criteria_pass(self):
        self.assertEqual("PASS", self.shadow_run["status"])
        self.assertEqual(1, self.shadow_run["feed_count"])
        self.assertGreaterEqual(self.shadow_run["frames_processed"], 300)
        self.assertGreaterEqual(self.shadow_run["segments_processed"], 10)
        self.assertEqual(2, self.shadow_run["candidate_observations_emitted"])
        lower, upper = self.expectation["candidate_rate_expected_band"]
        self.assertGreaterEqual(self.shadow_run["candidate_rate_observed"], lower)
        self.assertLessEqual(self.shadow_run["candidate_rate_observed"], upper)
        self.assertTrue(all(value is True or value == 0 for value in self.shadow_run["criteria_results"].values()))

    def test_candidate_observations_are_candidate_only(self):
        candidates = self.shadow_run["candidate_observation_fixtures"]
        self.assertTrue(candidates)
        for candidate in candidates:
            self.assertEqual("CandidateObservation", candidate["packet_type"])
            self.assertTrue(candidate["candidate_only"])
            self.assertFalse(candidate["identity_or_biometric_inference"])
            self.assertFalse(candidate["official_action_affordance"])
            self.assertEqual(self.source["source_id"], candidate["source_id"])
            self.assertTrue(candidate["model_or_runtime_provenance"])
            self.assertTrue(candidate["timestamp"])
            self.assertTrue(candidate["frame_ref"])
            self.assertGreaterEqual(len(candidate["evidence_refs"]), 2)

    def test_check_sufficiency_and_review_visibility(self):
        self.assertEqual("PASS", self.check["status"], self.check["missing_or_failed_requirements"])
        self.assertEqual(0, self.check["check_detection_sufficiency_missing"])
        self.assertTrue(self.check["check_report_ref"].startswith("check:perception_shadow:"))
        self.assertTrue(self.check["authority_envelope_ref"].startswith("authority:perception_shadow:"))
        self.assertEqual("pass", self.visibility["shadow_status"])
        self.assertTrue(self.visibility["review_visible_allowed"])
        self.assertEqual("candidate_observation_only_local_replay_review_queue", self.visibility["review_visibility_scope"])

    def test_negative_tests_block_stop_conditions(self):
        self.assertEqual("PASS", self.negative["status"])
        errors = {row["fixture_id"]: row["errors"] for row in self.negative["results"]}
        self.assertIn("no_2_1_live_source_policy_exists", errors["negative:perception_shadow:no_live_source_policy"])
        self.assertIn("source_lacks_retention_privacy_handling", errors["negative:perception_shadow:missing_retention_privacy"])
        self.assertIn("raw_frame_visibility_policy_missing", errors["negative:perception_shadow:missing_raw_frame_visibility"])
        self.assertIn("identity_biometric_inference_detected", errors["negative:perception_shadow:identity_biometric"])
        self.assertIn("output_implies_violation_finding_or_enforcement", errors["negative:perception_shadow:violation_finding_enforcement"])
        self.assertIn("production_network_or_api_access_required", errors["negative:perception_shadow:production_network"])
        self.assertIn("review_visible_requested_without_numeric_shadow_pass", errors["negative:perception_shadow:review_visible_without_numeric_pass"])

    def test_decision_boundaries_and_validation(self):
        validation = validate_outputs(self.source, self.expectation, self.shadow_run, self.check, self.visibility, self.negative)
        self.assertEqual("PASS", validation["status"], validation["errors"])
        decision = json.loads((OUTPUT_ROOT / "PERCEPTION_SHADOW_DECISION.json").read_text(encoding="utf-8"))
        self.assertEqual(PASS_STATUS, decision["status"])
        self.assertFalse(decision["boundaries"]["identity_biometric_inference"])
        self.assertFalse(decision["boundaries"]["official_action_finding_violation_dispatch_enforcement_legal_certified_finding"])
        self.assertFalse(decision["boundaries"]["production_camera_rollout_or_live_cctv_claim"])
        self.assertFalse(decision["boundaries"]["production_network_or_api_access"])
        self.assertTrue(decision["boundaries"]["candidate_only_local_replay_review_query"])
        self.assertEqual(NON_GOALS, decision["non_goals"])

    def test_hash_manifest_covers_outputs(self):
        manifest = json.loads((OUTPUT_ROOT / "HASH_MANIFEST.json").read_text(encoding="utf-8"))
        paths = {row["path"] for row in manifest["files"]}
        for name in [
            "PERCEPTION_SHADOW_DECISION.json",
            "PERCEPTION_SHADOW_REPORT.md",
            "SOURCE_REGISTRY_ENTRY.json",
            "SHADOW_RUN_REPORT.json",
            "CHECK_DETECTION_SUFFICIENCY_REPORT.json",
            "SHADOW_EXPECTATION_SPEC.json",
            "REVIEW_VISIBILITY_DECISION.json",
            "NEGATIVE_TEST_REPORT.json",
        ]:
            self.assertIn(name, paths)
        self.assertEqual(8, manifest["item_count"])


if __name__ == "__main__":
    unittest.main()

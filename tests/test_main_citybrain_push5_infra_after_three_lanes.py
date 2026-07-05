import json
import unittest

from scripts.run_main_citybrain_push5_infra_after_three_lanes import (
    CLOSEOUT_ROOT,
    FINAL_ROOT,
    OUTPUT_ROOT,
    PASS_STATUS,
    REQUIRED_CLOSEOUT_OUTPUTS,
    REQUIRED_FINAL_OUTPUTS,
    REQUIRED_OUTPUTS,
    verify_hash_manifest,
    write_all_outputs,
)


class MainCityBrainPush5InfraAfterThreeLanesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = write_all_outputs()
        cls.decision = json.loads((OUTPUT_ROOT / "PUSH5_INFRA_INTEGRATION_DECISION.json").read_text(encoding="utf-8"))
        cls.compatibility = json.loads((OUTPUT_ROOT / "PUSH5_CROSS_LANE_COMPATIBILITY_REPORT.json").read_text(encoding="utf-8"))
        cls.spatial_media = json.loads((OUTPUT_ROOT / "PUSH5_SPATIAL_MEDIA_EVIDENCE_JOIN_REPORT.json").read_text(encoding="utf-8"))
        cls.spatial_workflow = json.loads((OUTPUT_ROOT / "PUSH5_SPATIAL_WORKFLOW_STATE_JOIN_REPORT.json").read_text(encoding="utf-8"))
        cls.watch_media = json.loads((OUTPUT_ROOT / "PUSH5_WATCH_MEDIA_DEPTH_JOIN_REPORT.json").read_text(encoding="utf-8"))
        cls.workflow_llm = json.loads((OUTPUT_ROOT / "PUSH5_WORKFLOW_AND_LLM_BOUNDARY_REPORT.json").read_text(encoding="utf-8"))
        cls.closeout = json.loads((CLOSEOUT_ROOT / "PUSH5_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        cls.final = json.loads((FINAL_ROOT / "PUSH5_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))

    def test_required_outputs_exist(self):
        for name in REQUIRED_OUTPUTS:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        for name in REQUIRED_CLOSEOUT_OUTPUTS:
            self.assertTrue((CLOSEOUT_ROOT / name).exists(), name)
        for name in REQUIRED_FINAL_OUTPUTS:
            self.assertTrue((FINAL_ROOT / name).exists(), name)

    def test_decision_passes(self):
        self.assertEqual(PASS_STATUS, self.decision["status"])
        self.assertFalse(self.decision["canonical_merged"])
        self.assertEqual(8, self.decision["counts"]["media_bundle_count"])
        self.assertEqual(7, self.decision["counts"]["workflow_event_count"])

    def test_spatial_consumes_media_evidence(self):
        self.assertEqual("PASS", self.spatial_media["status"], self.spatial_media)
        self.assertTrue(self.spatial_media["spatial_surface_consumes_media_evidence_refs"])
        self.assertGreater(self.spatial_media["join_count"], 0)

    def test_spatial_consumes_workflow_state(self):
        self.assertEqual("PASS", self.spatial_workflow["status"], self.spatial_workflow)
        self.assertTrue(self.spatial_workflow["spatial_surface_consumes_workflow_state_refs"])
        self.assertTrue(self.spatial_workflow["all_joined_workflow_states_not_executed"])

    def test_watch_expansion_sees_media_depth(self):
        self.assertEqual("PASS", self.watch_media["status"], self.watch_media)
        self.assertTrue(self.watch_media["watch_expansion_sees_perception_media_evidence_depth"])
        self.assertGreater(self.watch_media["join_count"], 0)

    def test_workflow_llm_and_boundary_gates(self):
        self.assertEqual("PASS", self.workflow_llm["status"], self.workflow_llm)
        self.assertTrue(self.workflow_llm["workflow_states_remain_not_executed"])
        self.assertTrue(self.workflow_llm["optional_offline_llm_hook_fixture_only_non_authoritative"])
        self.assertFalse(self.workflow_llm["offline_llm_live_call"])
        self.assertFalse(self.workflow_llm["offline_llm_authority_created"])

    def test_compatibility_and_hashes(self):
        self.assertEqual("PASS", self.compatibility["status"], self.compatibility)
        self.assertTrue(all(self.compatibility["gates"].values()))
        self.assertEqual(PASS_STATUS, self.closeout["status"])
        self.assertEqual(PASS_STATUS, self.final["status"])
        for root, name in [
            (OUTPUT_ROOT, "PUSH5_HASH_MANIFEST.json"),
            (CLOSEOUT_ROOT, "PUSH5_CLOSEOUT_HASH_MANIFEST.json"),
            (FINAL_ROOT, "PUSH5_FINAL_STATUS_HASH_MANIFEST.json"),
        ]:
            report = verify_hash_manifest(root, name)
            self.assertEqual("PASS", report["status"], report)
            self.assertEqual(report["declared"], report["verified"])


if __name__ == "__main__":
    unittest.main()

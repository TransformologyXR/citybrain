import json
import unittest

from scripts.run_main_citybrain_push3_infra_after_three_lanes import (
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


class MainCityBrainPush3InfraAfterThreeLanesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = write_all_outputs()
        cls.decision = json.loads((OUTPUT_ROOT / "PUSH3_INFRA_INTEGRATION_DECISION.json").read_text(encoding="utf-8"))
        cls.compatibility = json.loads((OUTPUT_ROOT / "PUSH3_CROSS_LANE_COMPATIBILITY_REPORT.json").read_text(encoding="utf-8"))
        cls.ref_map = json.loads((OUTPUT_ROOT / "PUSH3_FLOW1_INTEGRATED_REFERENCE_MAP.json").read_text(encoding="utf-8"))
        cls.workspace_refs = json.loads((OUTPUT_ROOT / "PUSH3_SELECTED_ITEM_WORKSPACE_INTEGRATED_REFS.json").read_text(encoding="utf-8"))
        cls.join = json.loads((OUTPUT_ROOT / "PUSH3_FLOW1_COCKPIT_JOIN_REPORT.json").read_text(encoding="utf-8"))
        cls.coverage = json.loads((OUTPUT_ROOT / "PUSH3_CHECK_AUTHORITY_COVERAGE.json").read_text(encoding="utf-8"))
        cls.closeout = json.loads((CLOSEOUT_ROOT / "PUSH3_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        cls.final = json.loads((FINAL_ROOT / "PUSH3_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))

    def test_required_outputs_exist(self):
        for name in REQUIRED_OUTPUTS:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        for name in REQUIRED_CLOSEOUT_OUTPUTS:
            self.assertTrue((CLOSEOUT_ROOT / name).exists(), name)
        for name in REQUIRED_FINAL_OUTPUTS:
            self.assertTrue((FINAL_ROOT / name).exists(), name)

    def test_decision_passes_with_expected_counts(self):
        self.assertEqual(PASS_STATUS, self.decision["status"])
        self.assertFalse(self.decision["canonical_merged"])
        counts = self.decision["counts"]
        self.assertEqual(1, counts["selected_item_workspaces"])
        self.assertEqual(4, counts["diff_items"])
        self.assertEqual(5, counts["recall_matches"])
        self.assertEqual(1, counts["briefs"])

    def test_flow1_uses_cockpit_and_includes_diff_recall_refs(self):
        self.assertEqual("PASS", self.join["status"], self.join)
        self.assertTrue(self.join["flow1_can_use_cockpit_workspace"])
        self.assertTrue(self.join["flow1_includes_diff_recall_refs_via_infra_overlay"])
        self.assertEqual(4, self.join["diff_item_ref_count"])
        self.assertEqual(5, self.join["recall_match_ref_count"])
        self.assertFalse(self.join["mutates_lane_outputs"])

    def test_selected_item_workspace_shows_all_ref_families(self):
        self.assertTrue(self.workspace_refs["shows_ASK_refs"])
        self.assertTrue(self.workspace_refs["shows_WATCH_refs"])
        self.assertTrue(self.workspace_refs["shows_DIFF_refs"])
        self.assertTrue(self.workspace_refs["shows_RECALL_refs"])
        self.assertTrue(self.workspace_refs["shows_BRIEF_refs"])
        self.assertEqual("not_official", self.workspace_refs["official_status"])
        self.assertTrue(self.workspace_refs["local_replay_only"])

    def test_brief_and_exports_preserve_check_authority_boundary_refs(self):
        self.assertEqual("PASS", self.coverage["status"], self.coverage)
        self.assertTrue(self.coverage["checks"]["brief_v2_consumes_checked_packets_only"])
        self.assertTrue(self.coverage["checks"]["integrated_map_preserves_check_authority_refs"])
        for key in ["evidence_refs", "limitation_refs", "trace_refs", "check_report_refs", "authority_envelope_refs"]:
            self.assertTrue(self.ref_map[key], key)

    def test_compatibility_and_closeout_pass(self):
        self.assertEqual("PASS", self.compatibility["status"], self.compatibility)
        self.assertTrue(all(self.compatibility["gates"].values()))
        self.assertEqual(PASS_STATUS, self.closeout["status"])
        self.assertEqual(PASS_STATUS, self.final["status"])
        self.assertFalse(self.final["canonical_merged"])

    def test_hash_manifests_verify(self):
        for root, name in [
            (OUTPUT_ROOT, "PUSH3_HASH_MANIFEST.json"),
            (CLOSEOUT_ROOT, "PUSH3_CLOSEOUT_HASH_MANIFEST.json"),
            (FINAL_ROOT, "PUSH3_FINAL_STATUS_HASH_MANIFEST.json"),
        ]:
            report = verify_hash_manifest(root, name)
            self.assertEqual("PASS", report["status"], report)
            self.assertEqual(report["declared"], report["verified"])


if __name__ == "__main__":
    unittest.main()

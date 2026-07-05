import json
import unittest

from scripts.run_main_citybrain_push2_check_watch_app_route_integration import (
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


class MainCityBrainPush2CrossLaneIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = write_all_outputs()
        cls.decision = json.loads((OUTPUT_ROOT / "PUSH2_INTEGRATION_DECISION.json").read_text(encoding="utf-8"))
        cls.compatibility = json.loads((OUTPUT_ROOT / "PUSH2_CROSS_LANE_COMPATIBILITY_REPORT.json").read_text(encoding="utf-8"))
        cls.coverage = json.loads((OUTPUT_ROOT / "PUSH2_CHECK_AUTHORITY_COVERAGE.json").read_text(encoding="utf-8"))
        cls.join = json.loads((OUTPUT_ROOT / "PUSH2_WATCH_APP_ROUTE_JOIN_REPORT.json").read_text(encoding="utf-8"))
        cls.dispositions = json.loads((OUTPUT_ROOT / "PUSH2_DISPOSITION_EVENT_REPORT.json").read_text(encoding="utf-8"))
        cls.closeout = json.loads((CLOSEOUT_ROOT / "PUSH2_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        cls.final = json.loads((FINAL_ROOT / "PUSH2_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))

    def test_required_outputs_exist(self):
        for name in REQUIRED_OUTPUTS:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        for name in REQUIRED_CLOSEOUT_OUTPUTS:
            self.assertTrue((CLOSEOUT_ROOT / name).exists(), name)
        for name in REQUIRED_FINAL_OUTPUTS:
            self.assertTrue((FINAL_ROOT / name).exists(), name)

    def test_decision_and_counts_match_push2_source_of_truth(self):
        self.assertEqual(PASS_STATUS, self.decision["status"])
        self.assertFalse(self.decision["canonical_merged"])
        counts = self.decision["counts_preserved"]
        self.assertEqual(46, counts["lane_a_check_reports"])
        self.assertEqual(46, counts["lane_a_authority_envelopes"])
        self.assertEqual(7, counts["lane_b_watch_items"])
        self.assertEqual(12, counts["lane_c_review_items"])
        self.assertEqual(8, counts["lane_c_perception_items"])
        self.assertEqual(4, counts["lane_c_watch_items"])
        self.assertEqual(2, counts["lane_c_disposition_events"])

    def test_cross_lane_gates_pass(self):
        self.assertEqual("PASS", self.compatibility["status"], self.compatibility)
        self.assertTrue(all(self.compatibility["gate_results"].values()))
        self.assertEqual([], self.compatibility["forbidden_boundary_token_hits"])
        self.assertTrue(self.compatibility["protected_diff_report"]["ask_contract_paths_clean"])
        self.assertTrue(self.compatibility["protected_diff_report"]["r7_runtime_paths_clean"])

    def test_check_authority_coverage_links_are_valid(self):
        self.assertEqual("PASS", self.coverage["status"], self.coverage)
        self.assertEqual([], self.coverage["lane_b_missing_check_or_authority_refs"])
        self.assertEqual([], self.coverage["lane_c_missing_check_or_authority_refs"])
        self.assertTrue(self.coverage["lane_a_field_contract_consumable"])

    def test_watch_app_route_and_dispositions_are_joinable(self):
        self.assertEqual("PASS", self.join["status"], self.join)
        self.assertTrue(self.join["lane_c_render_watch_items_visible"])
        self.assertTrue(self.join["lane_c_render_perception_items_visible"])
        self.assertEqual([], self.join["review_items_missing_boundary_refs"])
        self.assertEqual(
            ["lane-c:review-item:perception:003", "lane-c:review-item:perception:006"],
            self.join["review_items_missing_evidence_refs"],
        )
        self.assertTrue(self.join["review_items_missing_evidence_refs_treated_as_limitations"])
        self.assertEqual("PASS", self.dispositions["status"], self.dispositions)
        self.assertEqual([], self.dispositions["missing_target_events"])
        self.assertEqual([], self.dispositions["boundary_failed_events"])

    def test_closeout_and_final_status_remain_integration_only(self):
        self.assertEqual(PASS_STATUS, self.closeout["status"])
        self.assertEqual(PASS_STATUS, self.final["status"])
        self.assertFalse(self.closeout["canonical_merged"])
        self.assertFalse(self.final["canonical_merged"])
        self.assertTrue(self.closeout["completed_through"]["merge_lane_a"])
        self.assertTrue(self.closeout["completed_through"]["merge_lane_b"])
        self.assertTrue(self.closeout["completed_through"]["merge_lane_c"])

    def test_hash_manifests_verify(self):
        reports = [
            verify_hash_manifest(OUTPUT_ROOT, "PUSH2_HASH_MANIFEST.json"),
            verify_hash_manifest(CLOSEOUT_ROOT, "PUSH2_CLOSEOUT_HASH_MANIFEST.json"),
            verify_hash_manifest(FINAL_ROOT, "PUSH2_FINAL_STATUS_HASH_MANIFEST.json"),
        ]
        for report in reports:
            self.assertEqual("PASS", report["status"], report)
            self.assertEqual(report["declared"], report["verified"])


if __name__ == "__main__":
    unittest.main()

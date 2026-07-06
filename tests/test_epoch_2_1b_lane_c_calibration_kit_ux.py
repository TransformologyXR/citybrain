import json
import unittest

from scripts.run_epoch_2_1b_lane_c_calibration_kit_ux import (
    CALIBRATION_REPORT_SCHEMA,
    EXPECTED_REPORT_FILES,
    OUTPUT_ROOT,
    REPORTS_DIR,
    STATUS_PASS_LIMITATIONS,
    build_outputs,
    sha256_file,
)


class Epoch21bLaneCCalibrationKitUxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_outputs()
        cls.decision = json.loads((OUTPUT_ROOT / "PUSH_2_1B_LANE_C_DECISION.json").read_text(encoding="utf-8"))
        cls.schema = json.loads((OUTPUT_ROOT / "calibration_report_schema_v1.json").read_text(encoding="utf-8"))
        cls.generation = json.loads((OUTPUT_ROOT / "calibration_report_generation_report.json").read_text(encoding="utf-8"))
        cls.audit = json.loads((OUTPUT_ROOT / "native_kit_ux_boundary_audit.json").read_text(encoding="utf-8"))

    def test_prerequisite_gate_passes_and_lane_status_is_limited_pass(self):
        self.assertEqual(STATUS_PASS_LIMITATIONS, self.result["status"])
        self.assertEqual(STATUS_PASS_LIMITATIONS, self.decision["status"])
        self.assertEqual("main", self.decision["branch"])
        self.assertEqual("PASS", self.decision["prerequisite_gate"]["status"])
        self.assertEqual("PASS", self.decision["lane_a_aggregation_floor"]["status"])
        self.assertTrue(self.decision["contract_check"]["epoch_2_1_not_closed"])

    def test_schema_preserves_descriptive_derived_field_boundary(self):
        self.assertEqual(CALIBRATION_REPORT_SCHEMA["schema_name"], self.schema["schema_name"])
        self.assertEqual("derived_field", self.schema["source_class"])
        for field in [
            "calibration_report_id",
            "subject",
            "period",
            "sample_size",
            "aggregation_floor_respected",
            "method_ref",
            "headline",
            "limitations",
            "trace_refs",
        ]:
            self.assertIn(field, self.schema["required_fields"])
        for forbidden in [
            "claim_status_change",
            "authority_change",
            "trained_model_release",
            "prediction",
            "ranking",
            "review_state_change",
            "learning_state_change",
            "check_result_change",
        ]:
            self.assertIn(forbidden, self.schema["forbidden_behaviors"])
        self.assertTrue(self.schema["boundary"]["descriptive_statistics_only"])
        self.assertTrue(self.schema["boundary"]["no_check_claim_review_or_authority_mutation"])

    def test_all_calibration_reports_exist_and_respect_floor(self):
        self.assertEqual(5, self.generation["reports_generated"])
        for name in EXPECTED_REPORT_FILES:
            path = REPORTS_DIR / name
            self.assertTrue(path.exists(), name)
            report = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("derived_field", report["source_class"])
            self.assertTrue(report["aggregation_floor_respected"])
            self.assertTrue(report["boundary"]["descriptive_statistics_only"])
            self.assertTrue(report["boundary"]["no_prediction"])
            self.assertIn("aggregation_floor_status", report)
            self.assertNotIn("claim_status_change", report.get("statistics", {}))

    def test_watchitem_disposition_report_is_suppressed_below_floor(self):
        report = json.loads((REPORTS_DIR / "watchitem_disposition_summary.json").read_text(encoding="utf-8"))
        self.assertLess(report["sample_size"], report["aggregation_floor_status"]["minimum_items_for_dashboard_cell"])
        self.assertTrue(report["aggregation_floor_status"]["suppressed_from_dashboard"])
        self.assertFalse(report["aggregation_floor_status"]["dashboard_cell_released"])
        self.assertEqual({}, report["statistics"]["released_watchitem_disposition_counts"])
        self.assertTrue(report["statistics"]["outcome_records_exist"])

    def test_native_kit_audit_keeps_no_action_boundaries(self):
        self.assertEqual(STATUS_PASS_LIMITATIONS, self.audit["status"])
        boundary = self.audit["boundary"]
        self.assertTrue(boundary["local_replay_review_only"])
        self.assertTrue(boundary["no_live_control"])
        self.assertTrue(boundary["no_official_action"])
        self.assertTrue(boundary["no_public_api"])
        self.assertTrue(boundary["no_production_auth"])
        self.assertTrue(boundary["no_autonomous_monitoring_action"])
        forbidden = self.audit["forbidden_affordance_audit"]
        self.assertEqual([], forbidden["forbidden_actions_accidentally_allowed"])
        display = self.audit["required_display_element_audit"]
        for key in [
            "canonical_entity_id",
            "source_class",
            "evidence_refs",
            "check_report_summary",
            "authority_envelope_summary",
            "cannot_claim_visibility",
            "not_executed_visibility",
            "limitations",
            "safe_next_looks",
            "spatial_overlay_clarity",
        ]:
            self.assertEqual("PASS", display[key]["status"], key)

    def test_hash_manifest_verifies(self):
        manifest = json.loads((OUTPUT_ROOT / "HASH_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", manifest["status"])
        manifest_paths = {row["path"] for row in manifest["files"]}
        self.assertIn("PUSH_2_1B_LANE_C_DECISION.json", manifest_paths)
        self.assertIn("calibration_reports_v1/watchitem_disposition_summary.json", manifest_paths)
        for row in manifest["files"]:
            target = OUTPUT_ROOT / row["path"]
            self.assertTrue(target.exists(), row)
            self.assertEqual(row["sha256"], sha256_file(target), row)


if __name__ == "__main__":
    unittest.main()

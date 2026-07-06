import json
import unittest

from scripts.run_epoch_2_1a_lane_a_privacy_retention import (
    OUTPUT_ROOT,
    PASS_STATUS,
    RETENTION_CLASSES,
    aggregation_policy,
    build_outputs,
    verify_hash_manifest,
)


class Epoch21aLaneAPrivacyRetentionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = build_outputs()
        cls.entry = json.loads((OUTPUT_ROOT / "EPOCH_2_0_ENTRY_CHECK_DECISION.json").read_text(encoding="utf-8"))
        cls.matrix = json.loads((OUTPUT_ROOT / "retention_matrix_v1.json").read_text(encoding="utf-8"))
        cls.aggregation = json.loads((OUTPUT_ROOT / "aggregation_floor_policy_v1.json").read_text(encoding="utf-8"))
        cls.fixtures = json.loads((OUTPUT_ROOT / "privacy_policy_enforcement_fixtures.json").read_text(encoding="utf-8"))
        cls.validation = json.loads((OUTPUT_ROOT / "privacy_policy_validation_report.json").read_text(encoding="utf-8"))

    def test_entry_check_passed_before_lane_artifacts(self):
        self.assertEqual("PASS", self.entry["status"], self.entry)
        self.assertTrue((OUTPUT_ROOT / "EPOCH_2_1_ALLOWED_TO_OPEN.flag").exists())
        self.assertTrue(all(row["status"] == "PASS" for row in self.entry["mandatory_agent_results"]))

    def test_required_lane_artifacts_exist(self):
        for name in [
            "privacy_retention_policy_v1.md",
            "privacy_retention_policy_v1.json",
            "retention_matrix_v1.json",
            "aggregation_floor_policy_v1.json",
            "right_to_forget_policy_v1.md",
            "privacy_policy_enforcement_fixtures.json",
            "privacy_policy_validation_report.json",
            "PUSH_2_1A_LANE_A_DECISION.json",
            "HASH_MANIFEST.json",
            "SUMMARY.md",
        ]:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_retention_matrix_covers_required_classes(self):
        classes = {row["artifact_class"] for row in self.matrix["items"]}
        self.assertEqual(set(RETENTION_CLASSES), classes)
        for row in self.matrix["items"]:
            for field in [
                "artifact_class",
                "source_class",
                "retention_period",
                "access_scope",
                "delete_or_redact_policy",
                "aggregation_floor_applicable",
                "notes",
            ]:
                self.assertIn(field, row)

    def test_aggregation_floor_policy(self):
        expected = aggregation_policy()
        self.assertEqual(expected["minimum_operators_for_display_or_learning_stat"], self.aggregation["minimum_operators_for_display_or_learning_stat"])
        self.assertEqual(expected["minimum_items_for_dashboard_cell"], self.aggregation["minimum_items_for_dashboard_cell"])
        self.assertFalse(self.aggregation["admin_override_allowed"])

    def test_required_enforcement_fixtures_pass(self):
        expected_ids = {
            "privacy-fixture:small-cell-aggregation-blocked",
            "privacy-fixture:operator-detail-non-admin-blocked",
            "privacy-fixture:right-to-forget-derived-case-redaction",
            "privacy-fixture:synthetic-real-source-class-mixing-rejected",
            "privacy-fixture:raw-media-vs-evidence-clip-retention-distinct",
            "privacy-fixture:disposition-event-local-replay-feedback-only",
        }
        self.assertEqual(expected_ids, {row["fixture_id"] for row in self.fixtures["items"]})
        self.assertEqual("PASS", self.validation["status"], self.validation)
        self.assertTrue(all(row["status"] == "PASS" for row in self.validation["results"]))

    def test_decision_boundaries_and_hash_manifest(self):
        self.assertEqual(PASS_STATUS, self.decision["status"])
        contract = self.decision["contract_check"]
        self.assertTrue(contract["lane_a_only"])
        self.assertTrue(contract["no_production_auth_implementation"])
        self.assertTrue(contract["no_model_training"])
        self.assertTrue(contract["no_learned_ranking"])
        self.assertTrue(contract["no_live_source_implementation"])
        self.assertTrue(contract["no_official_case_ticket_semantics"])
        self.assertEqual("PASS", verify_hash_manifest()["status"])


if __name__ == "__main__":
    unittest.main()

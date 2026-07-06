import json
import unittest

from scripts.run_epoch_2_1b_integration_gate import OUTPUT_ROOT, PASS_STATUS, build_outputs, sha256_file


class Epoch21bIntegrationGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_outputs()
        cls.decision = json.loads((OUTPUT_ROOT / "INTEGRATION_GATE_2_1B_DECISION.json").read_text(encoding="utf-8"))
        cls.convergence = json.loads((OUTPUT_ROOT / "CONTENT_HARDENING_CONVERGENCE_REPORT.json").read_text(encoding="utf-8"))
        cls.corpus = json.loads((OUTPUT_ROOT / "CORPUS_APPEND_REPORT.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((OUTPUT_ROOT / "HASH_MANIFEST.json").read_text(encoding="utf-8"))

    def test_gate_allows_push_2_1c_with_limitations(self):
        self.assertEqual(PASS_STATUS, self.decision["status"])
        self.assertTrue(self.decision["push_2_1c_allowed_to_open"])
        self.assertEqual({}, self.decision["failed_checks"])
        self.assertEqual("PASS", (OUTPUT_ROOT / "PUSH_2_1C_ALLOWED_TO_OPEN.flag").read_text(encoding="utf-8").strip())

    def test_required_gate_artifacts_exist(self):
        for name in [
            "INTEGRATION_GATE_2_1B_DECISION.json",
            "INTEGRATION_GATE_2_1B_SUMMARY.md",
            "PUSH_2_1C_ALLOWED_TO_OPEN.flag",
            "CONTENT_HARDENING_CONVERGENCE_REPORT.json",
            "SOURCE_OF_TRUTH_MATRIX_DELTA.md",
            "CORPUS_APPEND_REPORT.json",
            "FINAL_OR_NEXT_BLOCKERS.md",
            "HASH_MANIFEST.json",
        ]:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_all_gate_checks_pass_or_pass_with_limitation(self):
        expected = {
            "rbac_audit_baseline_fixture_tested",
            "four_starter_packs_pass_domain_pack_validator",
            "starter_packs_have_consuming_capability_and_eval_fixtures",
            "calibration_reports_are_derived_field_and_dashboard_consumed",
            "native_kit_ux_displays_evidence_source_check_authority_no_action_boundaries",
            "no_trained_model_live_source_official_action_or_agent_activation_introduced",
            "corpus_appended_and_manifests_updated",
            "source_of_truth_matrix_current",
            "lane_hash_manifests_verified",
        }
        self.assertEqual(expected, set(self.decision["gate_checks"]))
        for row in self.decision["gate_checks"].values():
            self.assertTrue(row["status"].startswith("PASS"), row)

    def test_content_hardening_summary_covers_lanes(self):
        self.assertEqual("PASS", self.convergence["status"])
        summary = self.convergence["content_hardening_summary"]
        self.assertEqual(6, summary["roles"])
        self.assertEqual(10, summary["audit_event_types"])
        self.assertEqual(4, summary["starter_pack_count"])
        self.assertEqual({"planning", "mobility", "utilities", "building"}, set(summary["starter_domains"]))
        self.assertEqual(5, summary["calibration_reports_generated"])
        self.assertEqual(12, summary["kit_review_items_audited"])

    def test_corpus_and_source_of_truth_are_no_mutation_append_reports(self):
        self.assertEqual("PASS_WITH_LIMITATION", self.corpus["status"])
        self.assertFalse(self.corpus["append_performed"])
        self.assertFalse(self.corpus["frozen_upstream_outputs_mutated"])
        self.assertEqual(4, self.corpus["registration_count"])
        matrix_text = (OUTPUT_ROOT / "SOURCE_OF_TRUTH_MATRIX_DELTA.md").read_text(encoding="utf-8")
        self.assertIn("no-mutation append evidence", matrix_text)

    def test_non_goals_are_preserved(self):
        non_goals = set(self.decision["non_goals_preserved"])
        self.assertIn("No trained model, ranking, prediction, cross-city learned transfer, or learning loop.", non_goals)
        self.assertIn("No live source onboarding implementation.", non_goals)
        self.assertIn("No production/public API exposure.", non_goals)
        self.assertIn("No agent activation.", non_goals)

    def test_hash_manifest_verifies(self):
        self.assertEqual("PASS", self.manifest["status"])
        self.assertGreater(self.manifest["item_count"], 0)
        for row in self.manifest["files"]:
            target = OUTPUT_ROOT / row["path"]
            self.assertTrue(target.exists(), row)
            self.assertEqual(row["sha256"], sha256_file(target), row)


if __name__ == "__main__":
    unittest.main()

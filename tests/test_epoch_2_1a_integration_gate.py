import json
import unittest

from scripts.run_epoch_2_1a_integration_gate import OUTPUT_ROOT, build_outputs, sha256_file


class Epoch21aIntegrationGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_outputs()
        cls.decision = json.loads((OUTPUT_ROOT / "INTEGRATION_GATE_2_1A_DECISION.json").read_text(encoding="utf-8"))
        cls.contract = json.loads((OUTPUT_ROOT / "CONTRACT_CONVERGENCE_REPORT.json").read_text(encoding="utf-8"))
        cls.corpus = json.loads((OUTPUT_ROOT / "CORPUS_APPEND_REPORT.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((OUTPUT_ROOT / "HASH_MANIFEST.json").read_text(encoding="utf-8"))

    def test_gate_allows_push_2_1b_with_limitations(self):
        self.assertEqual("PASS_PUSH_2_1A_FOUNDATIONS_GATE_WITH_LIMITATIONS", self.decision["status"])
        self.assertTrue(self.decision["push_2_1b_allowed_to_open"])
        self.assertEqual({}, self.decision["failed_checks"])
        self.assertTrue((OUTPUT_ROOT / "PUSH_2_1B_ALLOWED_TO_OPEN.flag").exists())
        self.assertEqual("PASS", (OUTPUT_ROOT / "PUSH_2_1B_ALLOWED_TO_OPEN.flag").read_text(encoding="utf-8").strip())

    def test_required_gate_artifacts_exist(self):
        for name in [
            "INTEGRATION_GATE_2_1A_DECISION.json",
            "INTEGRATION_GATE_2_1A_SUMMARY.md",
            "PUSH_2_1B_ALLOWED_TO_OPEN.flag",
            "CONTRACT_CONVERGENCE_REPORT.json",
            "SOURCE_OF_TRUTH_MATRIX_DELTA.md",
            "CORPUS_APPEND_REPORT.json",
            "FINAL_OR_NEXT_BLOCKERS.md",
            "HASH_MANIFEST.json",
        ]:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_required_foundation_checks_pass_or_pass_with_limitation(self):
        checks = self.decision["gate_checks"]
        required = {
            "privacy_retention_policy_fixture_tested",
            "aggregation_floor_used_by_outcome_record_materializer",
            "domain_pack_framework_rejects_no_consumer",
            "ontology_governance_requires_tests_versioning_compatibility",
            "dashboard_uses_authoritative_ledgers_not_metric_silo",
            "outcome_records_derived_field_only_not_model_or_ranking",
            "source_of_truth_matrix_delta_recorded",
            "corpus_append_reported",
            "lane_hash_manifests_verified",
        }
        self.assertEqual(required, set(checks))
        for row in checks.values():
            self.assertTrue(row["status"].startswith("PASS"), row)

    def test_contract_convergence_preserves_boundaries(self):
        self.assertEqual("PASS", self.contract["status"])
        source_class = self.contract["shared_contracts"]["source_class"]
        self.assertEqual("derived_field", source_class["outcome_record"])
        self.assertTrue(source_class["domain_pack_source_class_required"])
        self.assertFalse(source_class["synthetic_real_mixing_allowed"])
        dashboard_inputs = self.contract["shared_contracts"]["dashboard_inputs"]
        self.assertTrue(dashboard_inputs["no_new_metric_silo"])

    def test_corpus_append_is_reported_as_deferred(self):
        self.assertEqual("PASS_WITH_LIMITATION", self.corpus["status"])
        self.assertFalse(self.corpus["append_performed"])
        self.assertIn("Push 2.1b", self.corpus["reason"])

    def test_non_goals_remain_preserved(self):
        non_goals = set(self.decision["non_goals_preserved"])
        self.assertIn("No production/public API claim.", non_goals)
        self.assertIn("No autonomous monitoring/action.", non_goals)
        self.assertIn("No trained ranking, prediction, model output, or learned transfer.", non_goals)
        self.assertIn("No live camera/source implementation.", non_goals)

    def test_hash_manifest_verifies(self):
        self.assertEqual("PASS", self.manifest["status"])
        self.assertGreater(self.manifest["item_count"], 0)
        for row in self.manifest["files"]:
            target = OUTPUT_ROOT / row["path"]
            self.assertTrue(target.exists(), row)
            self.assertEqual(row["sha256"], sha256_file(target), row)


if __name__ == "__main__":
    unittest.main()

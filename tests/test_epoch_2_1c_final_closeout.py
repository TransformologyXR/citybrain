import json
import unittest

from scripts.run_epoch_2_1c_final_closeout import OUTPUT_ROOT, PASS_STATUS, build_outputs, sha256_file


class Epoch21FinalCloseoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_outputs()
        cls.decision = json.loads((OUTPUT_ROOT / "EPOCH_2_1_FINAL_DECISION.json").read_text(encoding="utf-8"))
        cls.ledger = json.loads((OUTPUT_ROOT / "EPOCH_2_1_LEDGER_ROWS.json").read_text(encoding="utf-8"))
        cls.corpus = json.loads((OUTPUT_ROOT / "EPOCH_2_1_CORPUS_APPEND_REPORT.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((OUTPUT_ROOT / "EPOCH_2_1_HASH_MANIFEST").read_text(encoding="utf-8"))

    def test_final_closeout_passes_with_limitations(self):
        self.assertEqual(PASS_STATUS, self.decision["status"])
        self.assertEqual({}, self.decision["failed_checks"])
        self.assertEqual("main", self.decision["branch"])

    def test_required_final_artifacts_exist(self):
        for name in [
            "EPOCH_2_1_FINAL_DECISION.json",
            "EPOCH_2_1_FINAL_PUBLISHED_STATUS.md",
            "EPOCH_2_1_LEDGER_ROWS.json",
            "EPOCH_2_1_SOURCE_OF_TRUTH_MATRIX_DELTA.md",
            "EPOCH_2_1_CORPUS_APPEND_REPORT.json",
            "EPOCH_2_1_HASH_MANIFEST",
            "EPOCH_2_2_ENTRY_BRIDGE.md",
            "EPOCH_3_PREREQ_DELTA.md",
        ]:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_all_exit_gate_checks_pass_or_pass_with_limitation(self):
        expected = {
            "epoch_2_0_entry_check_passed",
            "integration_gate_2_1a_passed",
            "integration_gate_2_1b_passed",
            "privacy_retention_and_aggregation_published",
            "domain_pack_framework_and_ontology_governance_published",
            "four_starter_packs_certified_with_consuming_capabilities",
            "dubai_synthetic_pack_certified_with_source_class_separation",
            "data_maturity_dashboard_and_outcome_records_flowing",
            "calibration_reports_v1_flowing_as_derived_field",
            "rbac_audit_observability_baseline_hardened",
            "live_source_and_department_node_policy_published_no_implementation",
            "native_kit_ux_polish_landed_with_boundaries",
            "federation_query_v0_proven_on_nyc_london",
            "no_learned_trained_or_actionable_behavior_introduced",
            "source_of_truth_matrix_current",
            "regression_corpus_appended",
            "hash_manifest_clean",
        }
        self.assertEqual(expected, set(self.decision["gate_checks"]))
        for row in self.decision["gate_checks"].values():
            self.assertTrue(row["status"].startswith("PASS"), row)

    def test_ledger_rows_cover_every_lane_and_gate(self):
        self.assertEqual("PASS", self.ledger["status"])
        self.assertEqual(13, self.ledger["row_count"])
        row_ids = {row["row_id"] for row in self.ledger["rows"]}
        for row_id in [
            "epoch_2_0_entry",
            "integration_2_1a",
            "integration_2_1b",
            "push_2_1a_lane_a_privacy_retention",
            "push_2_1a_lane_b_domain_framework",
            "push_2_1a_lane_c_dashboard_outcome",
            "push_2_1b_lane_a_rbac_audit_observability",
            "push_2_1b_lane_b_starter_domain_packs",
            "push_2_1b_lane_c_calibration_kit_ux",
            "push_2_1c_lane_a_dubai_synthetic_pack",
            "push_2_1c_lane_b_live_source_department_node_policy",
            "push_2_1c_lane_c_federation_query_v0",
            "epoch_2_1_final_closeout",
        ]:
            self.assertIn(row_id, row_ids)

    def test_source_of_truth_and_corpus_are_no_mutation_reports(self):
        self.assertEqual("PASS_WITH_LIMITATION", self.corpus["status"])
        self.assertFalse(self.corpus["append_performed"])
        self.assertFalse(self.corpus["frozen_upstream_outputs_mutated"])
        matrix_text = (OUTPUT_ROOT / "EPOCH_2_1_SOURCE_OF_TRUTH_MATRIX_DELTA.md").read_text(encoding="utf-8")
        self.assertIn("frozen upstream matrices immutable", matrix_text)

    def test_entry_bridge_and_epoch3_delta_preserve_boundaries(self):
        bridge = (OUTPUT_ROOT / "EPOCH_2_2_ENTRY_BRIDGE.md").read_text(encoding="utf-8")
        epoch3 = (OUTPUT_ROOT / "EPOCH_3_PREREQ_DELTA.md").read_text(encoding="utf-8")
        self.assertIn("No live-source implementation", bridge)
        self.assertIn("No learned ranking", bridge)
        self.assertIn("Trained ranking", epoch3)
        self.assertIn("Live-source activation", epoch3)

    def test_hash_manifest_verifies(self):
        self.assertEqual("PASS", self.manifest["status"])
        self.assertGreater(self.manifest["item_count"], 0)
        for row in self.manifest["files"]:
            target = OUTPUT_ROOT / row["path"]
            self.assertTrue(target.exists(), row)
            self.assertEqual(row["sha256"], sha256_file(target), row)


if __name__ == "__main__":
    unittest.main()

import json
import unittest

from scripts.run_main_citybrain_push4_infra_after_three_lanes import (
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


class MainCityBrainPush4InfraAfterThreeLanesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = write_all_outputs()
        cls.decision = json.loads((OUTPUT_ROOT / "PUSH4_INFRA_INTEGRATION_DECISION.json").read_text(encoding="utf-8"))
        cls.compatibility = json.loads((OUTPUT_ROOT / "PUSH4_CROSS_LANE_COMPATIBILITY_REPORT.json").read_text(encoding="utf-8"))
        cls.alignment = json.loads((OUTPUT_ROOT / "PUSH4_CER_GRAPH_ALIGNMENT_REPORT.json").read_text(encoding="utf-8"))
        cls.consumption = json.loads((OUTPUT_ROOT / "PUSH4_CHECK_V1_CER_CONSUMPTION_REPORT.json").read_text(encoding="utf-8"))
        cls.contradiction = json.loads((OUTPUT_ROOT / "PUSH4_CONTRADICTION_AND_ASK_WAIVER_REPORT.json").read_text(encoding="utf-8"))
        cls.corpus = json.loads((OUTPUT_ROOT / "PUSH4_REGRESSION_CORPUS_V4_READINESS.json").read_text(encoding="utf-8"))
        cls.source_depth = json.loads((OUTPUT_ROOT / "PUSH4_SOURCE_DEPTH_AND_VSS_BOUNDARY_REPORT.json").read_text(encoding="utf-8"))
        cls.closeout = json.loads((CLOSEOUT_ROOT / "PUSH4_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        cls.final = json.loads((FINAL_ROOT / "PUSH4_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))

    def test_required_outputs_exist(self):
        for name in REQUIRED_OUTPUTS:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        for name in REQUIRED_CLOSEOUT_OUTPUTS:
            self.assertTrue((CLOSEOUT_ROOT / name).exists(), name)
        for name in REQUIRED_FINAL_OUTPUTS:
            self.assertTrue((FINAL_ROOT / name).exists(), name)

    def test_decision_and_counts(self):
        self.assertEqual(PASS_STATUS, self.decision["status"])
        self.assertFalse(self.decision["canonical_merged"])
        counts = self.decision["counts"]
        self.assertEqual(6, counts["cer_attribute_assertions"])
        self.assertEqual(6, counts["check_v1_reports"])
        self.assertEqual(1, counts["contradictions_detected"])
        self.assertEqual(1, counts["retained_same_claim_pairs"])

    def test_graph_edges_target_cer_ids_and_assertion_refs(self):
        self.assertEqual("PASS", self.alignment["status"], self.alignment)
        self.assertTrue(self.alignment["graph_edges_target_cer_entity_assertion_ids"])
        self.assertGreater(self.alignment["cer_ref_count"], 0)
        self.assertGreater(self.alignment["provisional_cer_ref_count"], 0)

    def test_check_v1_consumes_cer_assertions(self):
        self.assertEqual("PASS", self.consumption["status"], self.consumption)
        self.assertTrue(self.consumption["check_v1_consumes_cer_attribute_assertions"])
        self.assertEqual([], self.consumption["unknown_consumed_assertion_refs"])
        self.assertEqual(6, self.consumption["consumed_assertion_count"])

    def test_contradiction_ask_waiver_and_corpus_v4(self):
        self.assertEqual("PASS", self.contradiction["status"], self.contradiction)
        self.assertTrue(self.contradiction["check_v1_detects_contradictions_over_retained_same_claim_pairs"])
        self.assertTrue(self.contradiction["ask_contradiction_waiver_closed"])
        self.assertEqual("PASS", self.corpus["status"], self.corpus)
        self.assertTrue(self.corpus["regression_corpus_v4_prepared"])
        self.assertFalse(self.corpus["canonical_ask_corpus_mutated"])

    def test_source_depth_preserves_vss_not_fact_source(self):
        self.assertEqual("PASS", self.source_depth["status"], self.source_depth)
        self.assertTrue(self.source_depth["source_depth_scoring_preserves_vss_not_fact_source"])
        self.assertFalse(self.source_depth["vss_narrative_can_source_truth"])

    def test_compatibility_and_hashes(self):
        self.assertEqual("PASS", self.compatibility["status"], self.compatibility)
        self.assertTrue(all(self.compatibility["gates"].values()))
        self.assertEqual(PASS_STATUS, self.closeout["status"])
        self.assertEqual(PASS_STATUS, self.final["status"])
        for root, name in [
            (OUTPUT_ROOT, "PUSH4_HASH_MANIFEST.json"),
            (CLOSEOUT_ROOT, "PUSH4_CLOSEOUT_HASH_MANIFEST.json"),
            (FINAL_ROOT, "PUSH4_FINAL_STATUS_HASH_MANIFEST.json"),
        ]:
            report = verify_hash_manifest(root, name)
            self.assertEqual("PASS", report["status"], report)
            self.assertEqual(report["declared"], report["verified"])


if __name__ == "__main__":
    unittest.main()

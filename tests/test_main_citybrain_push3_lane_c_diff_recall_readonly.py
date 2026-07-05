import json
import shutil
import unittest

from scripts.run_main_citybrain_push3_lane_c_diff_recall_readonly import (
    CLOSEOUT_ROOT,
    DIFF_FAMILIES,
    FINAL_ROOT,
    OUTPUT_ROOT,
    PASS_STATUS,
    RECALL_FAMILIES,
    REQUIRED_CLOSEOUT_OUTPUTS,
    REQUIRED_FINAL_OUTPUTS,
    REQUIRED_OUTPUTS,
    entry_gate_report,
    verify_hash_manifest,
    write_all_outputs,
)


class MainCityBrainPush3LaneCDiffRecallReadonlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for root in [OUTPUT_ROOT, CLOSEOUT_ROOT, FINAL_ROOT]:
            if root.exists():
                shutil.rmtree(root)
        cls.all_outputs = write_all_outputs({"runner": "TEST_SETUP"})
        cls.bundle = cls.all_outputs["bundle"]
        cls.closeout = cls.all_outputs["closeout"]
        cls.final = cls.all_outputs["final"]
        cls.decision = json.loads((OUTPUT_ROOT / "DIFF_RECALL_READONLY_DECISION.json").read_text(encoding="utf-8"))
        cls.diff_contract = json.loads((OUTPUT_ROOT / "DIFF_SCOUT_V1_CONTRACT.json").read_text(encoding="utf-8"))
        cls.diff_items = json.loads((OUTPUT_ROOT / "DIFF_ITEMS.json").read_text(encoding="utf-8"))["items"]
        cls.recall_contract = json.loads((OUTPUT_ROOT / "RECALL_MATCHER_CONTRACT.json").read_text(encoding="utf-8"))
        cls.recall_matches = json.loads((OUTPUT_ROOT / "RECALL_MATCH_ITEMS.json").read_text(encoding="utf-8"))["items"]
        cls.compatibility = json.loads((OUTPUT_ROOT / "DIFF_TO_WATCH_COMPATIBILITY.json").read_text(encoding="utf-8"))
        cls.coverage = json.loads((OUTPUT_ROOT / "DIFF_RECALL_CHECK_AUTHORITY_COVERAGE.json").read_text(encoding="utf-8"))

    def test_entry_gate_passes_on_push2_integration_branch(self):
        gates = entry_gate_report()
        self.assertEqual("PASS", gates["status"], gates)
        self.assertTrue(all(gate["status"] == "PASS" for gate in gates["gates"]))

    def test_required_outputs_exist(self):
        for name in REQUIRED_OUTPUTS:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        for name in REQUIRED_CLOSEOUT_OUTPUTS:
            self.assertTrue((CLOSEOUT_ROOT / name).exists(), name)
        for name in REQUIRED_FINAL_OUTPUTS:
            self.assertTrue((FINAL_ROOT / name).exists(), name)

    def test_diff_contract_and_items_are_complete(self):
        self.assertEqual("PASS", self.diff_contract["status"])
        self.assertEqual(DIFF_FAMILIES, self.diff_contract["diff_families"])
        self.assertEqual(4, len(self.diff_items))
        self.assertEqual(set(DIFF_FAMILIES), {item["diff_family"] for item in self.diff_items})
        required = set(self.diff_contract["required_fields"])
        for item in self.diff_items:
            self.assertTrue(required.issubset(item), item)
            self.assertTrue(item["diff_item_id"].startswith("diff:item:"))
            self.assertTrue(item["review_required"])
            self.assertEqual("not_official", item["official_status"])
            self.assertTrue(item["read_only"])
            self.assertTrue(item["check_report_ref"])
            self.assertTrue(item["authority_envelope_ref"])
            self.assertTrue(item["evidence_refs"])
            self.assertTrue(item["limitation_refs"])
            self.assertTrue(item["trace_refs"])
            self.assertIn("no production API", " ".join(item["not_executed"]))
            self.assertIn("official action", item["cannot_claim"])

    def test_recall_contract_and_matches_are_complete(self):
        self.assertEqual("PASS", self.recall_contract["status"])
        self.assertEqual(RECALL_FAMILIES, self.recall_contract["matcher_families"])
        self.assertTrue(self.recall_contract["no_cross_city_claims_until_federation"])
        self.assertEqual(5, len(self.recall_matches))
        self.assertEqual(set(RECALL_FAMILIES), {item["match_family"] for item in self.recall_matches})
        required = set(self.recall_contract["required_fields"])
        for item in self.recall_matches:
            self.assertTrue(required.issubset(item), item)
            self.assertTrue(item["recall_match_id"].startswith("recall:match:"))
            self.assertGreaterEqual(item["score"], 0)
            self.assertLessEqual(item["score"], 1)
            self.assertFalse(item["cross_city_claim"])
            self.assertEqual("not_official", item["official_status"])
            self.assertTrue(item["check_report_ref"])
            self.assertTrue(item["authority_envelope_ref"])
            self.assertTrue(item["match_features"])
            self.assertIn("cross-city recall certainty", item["cannot_claim"])

    def test_diff_can_feed_watch_as_review_prompt_only(self):
        self.assertEqual("PASS", self.compatibility["status"])
        self.assertTrue(self.compatibility["diff_items_can_feed_watch_items"])
        self.assertTrue(self.compatibility["watch_items_remain_review_prompts"])
        self.assertTrue(self.compatibility["check_reports_preserved"])
        self.assertTrue(self.compatibility["authority_envelopes_preserved"])
        self.assertEqual(len(self.diff_items), self.compatibility["generated_review_prompt_count"])
        for prompt in self.compatibility["generated_review_prompts"]:
            self.assertEqual("review_prompt", prompt["watch_item_kind"])
            self.assertTrue(prompt["review_required"])
            self.assertTrue(prompt["not_action"])
            self.assertTrue(prompt["not_finding"])
            self.assertEqual("not_official", prompt["official_status"])
            self.assertTrue(prompt["check_report_ref"])
            self.assertTrue(prompt["authority_envelope_ref"])

    def test_check_authority_coverage_and_boundaries_pass(self):
        self.assertEqual("PASS", self.coverage["status"], self.coverage)
        self.assertTrue(self.coverage["all_diff_items_have_check_report_ref"])
        self.assertTrue(self.coverage["all_diff_items_have_authority_envelope_ref"])
        self.assertTrue(self.coverage["all_recall_matches_have_check_report_ref"])
        self.assertTrue(self.coverage["all_recall_matches_have_authority_envelope_ref"])
        self.assertFalse(self.coverage["new_check_or_authority_schema_changes"])
        self.assertFalse(self.coverage["cer_assertion_dependency"])
        boundary_text = (OUTPUT_ROOT / "DIFF_RECALL_BOUNDARY_AND_NON_CLAIMS.md").read_text(encoding="utf-8")
        self.assertIn("No AttributeAssertion or CER assertion shape is emitted", boundary_text)
        serialized = json.dumps(
            {
                "decision": self.decision,
                "diff_items": self.diff_items,
                "recall_matches": self.recall_matches,
                "compatibility": self.compatibility,
            },
            sort_keys=True,
        )
        self.assertNotIn('"official_status": "official"', serialized)
        self.assertNotIn('"execution_status": "executed"', serialized)
        self.assertNotIn('"cross_city_claim": true', serialized)
        self.assertNotIn("AttributeAssertion", serialized)

    def test_decision_closeout_and_final_status_pass(self):
        self.assertEqual(PASS_STATUS, self.decision["status"])
        self.assertEqual(4, self.decision["diff_item_count"])
        self.assertEqual(5, self.decision["recall_match_count"])
        self.assertTrue(self.decision["watch_feed_compatible"])
        self.assertTrue(self.decision["no_cross_city_claims"])
        self.assertTrue(self.decision["no_official_findings_actions"])
        self.assertTrue(self.decision["no_cer_assertion_shapes_invented"])
        self.assertEqual(PASS_STATUS, self.closeout["decision"]["status"])
        self.assertEqual(PASS_STATUS, self.final["decision"]["status"])

    def test_hash_manifests_verify(self):
        reports = [
            verify_hash_manifest(OUTPUT_ROOT, "DIFF_RECALL_HASH_MANIFEST.json"),
            verify_hash_manifest(CLOSEOUT_ROOT, "DIFF_RECALL_READONLY_CLOSEOUT_HASH_MANIFEST.json"),
            verify_hash_manifest(FINAL_ROOT, "DIFF_RECALL_READONLY_FINAL_STATUS_HASH_MANIFEST.json"),
        ]
        for report in reports:
            self.assertEqual("PASS", report["status"], report)
            self.assertEqual(report["declared"], report["verified"])


if __name__ == "__main__":
    unittest.main()

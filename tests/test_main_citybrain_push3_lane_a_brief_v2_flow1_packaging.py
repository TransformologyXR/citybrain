import json
import subprocess
import unittest
from pathlib import Path

from scripts.run_main_citybrain_push3_lane_a_brief_v2_flow1_packaging import (
    ASK_CONTRACT_PATHS,
    BRIEF_REQUIRED_FIELDS,
    CLOSEOUT_ROOT,
    CLOSEOUT_STATUS,
    FINAL_ROOT,
    FINAL_STATUS,
    OUTPUT_ROOT,
    PASS_STATUS,
    R7_RUNTIME_PATHS,
    build_outputs,
    verify_hash_manifest_for,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainPush3LaneABriefFlow1PackagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_outputs({"runner": "TEST_SETUP"})
        cls.decision = json.loads((OUTPUT_ROOT / "BRIEF_V2_FLOW1_DECISION.json").read_text(encoding="utf-8"))
        cls.briefs = json.loads((OUTPUT_ROOT / "BRIEF_V2_GENERATED_BRIEFS.json").read_text(encoding="utf-8"))
        cls.coverage = json.loads((OUTPUT_ROOT / "BRIEF_V2_CHECK_AUTHORITY_COVERAGE.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((OUTPUT_ROOT / "FLOW1_SITUATIONAL_STATUS_PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
        cls.export = json.loads((OUTPUT_ROOT / "FLOW1_SITUATIONAL_STATUS_EXPORT.json").read_text(encoding="utf-8"))
        cls.closeout = json.loads((CLOSEOUT_ROOT / "BRIEF_V2_FLOW1_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        cls.final = json.loads((FINAL_ROOT / "BRIEF_V2_FLOW1_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))
        cls.brief = cls.briefs["briefs"][0]

    def test_required_outputs_exist(self):
        required = [
            "BRIEF_V2_FLOW1_DECISION.json",
            "BRIEF_V2_CONTRACT.json",
            "BRIEF_V2_FIXTURES.json",
            "BRIEF_V2_GENERATED_BRIEFS.json",
            "BRIEF_V2_CHECK_AUTHORITY_COVERAGE.json",
            "FLOW1_SITUATIONAL_STATUS_PACKAGE_MANIFEST.json",
            "FLOW1_SITUATIONAL_STATUS_LOCAL_OPEN_INDEX.md",
            "FLOW1_SITUATIONAL_STATUS_EXPORT.md",
            "FLOW1_SITUATIONAL_STATUS_EXPORT.json",
            "FLOW1_BOUNDARY_AND_NON_CLAIMS.md",
            "FLOW1_TEST_LOG.md",
            "FLOW1_HASH_MANIFEST.json",
        ]
        for name in required:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        self.assertEqual(PASS_STATUS, self.decision["status"])

    def test_closeout_and_final_status_exist(self):
        for name in [
            "BRIEF_V2_FLOW1_CLOSEOUT_DECISION.json",
            "BRIEF_V2_FLOW1_CLOSEOUT_SUMMARY.md",
            "BRIEF_V2_FLOW1_CLOSEOUT_LIMITATIONS.md",
            "BRIEF_V2_FLOW1_CLOSEOUT_NEXT_STEPS.md",
            "BRIEF_V2_FLOW1_CLOSEOUT_HASH_MANIFEST.json",
        ]:
            self.assertTrue((CLOSEOUT_ROOT / name).exists(), name)
        for name in [
            "BRIEF_V2_FLOW1_FINAL_STATUS_DECISION.json",
            "BRIEF_V2_FLOW1_FINAL_STATUS_SUMMARY.md",
            "BRIEF_V2_FLOW1_FINAL_STATUS_HASH_MANIFEST.json",
        ]:
            self.assertTrue((FINAL_ROOT / name).exists(), name)
        self.assertEqual(CLOSEOUT_STATUS, self.closeout["status"])
        self.assertEqual(FINAL_STATUS, self.final["status"])

    def test_brief_v2_contract_fields_and_refs_are_present(self):
        for field in BRIEF_REQUIRED_FIELDS:
            self.assertIn(field, self.brief)
        self.assertTrue(self.brief["check_report_refs"])
        self.assertTrue(self.brief["authority_envelope_refs"])
        self.assertTrue(self.brief["evidence_refs"])
        self.assertTrue(self.brief["limitation_refs"])
        self.assertTrue(self.brief["trace_refs"])
        self.assertTrue(self.brief["cannot_claim"])

    def test_check_authority_coverage_passes(self):
        self.assertEqual("PASS", self.coverage["status"])
        self.assertGreaterEqual(self.coverage["check_report_ref_count"], 40)
        self.assertGreaterEqual(self.coverage["authority_envelope_ref_count"], 40)
        self.assertTrue(self.coverage["all_claims_checked"])
        self.assertEqual([], self.coverage["missing_watch_check_or_authority_refs"])

    def test_flow1_composes_required_surfaces(self):
        self.assertTrue(self.manifest["includes_ASK"])
        self.assertTrue(self.manifest["includes_WATCH"])
        self.assertTrue(self.manifest["includes_BRIEF"])
        self.assertTrue(self.manifest["includes_spatial"])
        self.assertTrue(self.manifest["includes_app_review_route"])
        self.assertTrue(self.manifest["local_replay_only"])
        self.assertTrue(self.manifest["review_only"])

    def test_export_is_review_only_and_non_claims_are_preserved(self):
        self.assertEqual("local_replay_review_only", self.export["export_kind"])
        self.assertFalse(self.export["official_action_created"])
        self.assertFalse(self.export["legal_or_certified_finding_created"])
        cannot_claim = " ".join(self.brief["cannot_claim"]).lower()
        for term in ["official action", "dispatch/control/enforcement", "legal/certified finding"]:
            self.assertIn(term, cannot_claim)
        metadata = self.brief["export_metadata"]
        self.assertFalse(metadata["production_api_used"])
        self.assertFalse(metadata["url_fetch_used"])
        self.assertFalse(metadata["llm_used"])

    def test_operator_disposition_summary_is_aggregate_only(self):
        summary = self.brief["operator_disposition_summary"]
        self.assertEqual("aggregate_only", summary["summary_kind"])
        self.assertFalse(summary["individual_notes_exposed"])
        self.assertIn("counts_by_disposition", summary)
        self.assertNotIn("notes", summary)
        self.assertNotIn("individual_notes", summary)
        self.assertNotIn("disposition_events", summary)

    def test_hash_manifests_verify(self):
        for root, name in [
            (OUTPUT_ROOT, "FLOW1_HASH_MANIFEST.json"),
            (CLOSEOUT_ROOT, "BRIEF_V2_FLOW1_CLOSEOUT_HASH_MANIFEST.json"),
            (FINAL_ROOT, "BRIEF_V2_FLOW1_FINAL_STATUS_HASH_MANIFEST.json"),
        ]:
            report = verify_hash_manifest_for(root, name)
            self.assertEqual("PASS", report["status"], report)
            self.assertEqual(report["declared"], report["verified"])

    def test_no_sealed_ask_or_protected_r7_runtime_diff(self):
        ask = subprocess.run(["git", "diff", "--", *ASK_CONTRACT_PATHS], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        r7 = subprocess.run(["git", "diff", "--", *R7_RUNTIME_PATHS], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self.assertEqual("", ask.stdout)
        self.assertEqual("", r7.stdout)


if __name__ == "__main__":
    unittest.main()

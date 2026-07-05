import json
import subprocess
import unittest
from pathlib import Path

from packages.check_v1 import claimability_status_for_assertion, validate_claimability_status
from scripts.run_main_citybrain_push4_lane_c_check_v1 import (
    ASK_CONTRACT_PATHS,
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


class MainCityBrainPush4LaneCCheckV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_outputs({"runner": "TEST_SETUP"})
        cls.decision = json.loads((OUTPUT_ROOT / "CHECK_V1_DECISION.json").read_text(encoding="utf-8"))
        cls.mappings = json.loads((OUTPUT_ROOT / "CHECK_V1_CLAIM_TO_EVIDENCE_FIXTURES.json").read_text(encoding="utf-8"))
        cls.contradictions = json.loads((OUTPUT_ROOT / "CHECK_V1_CONTRADICTION_FIXTURES.json").read_text(encoding="utf-8"))
        cls.source_depth = json.loads((OUTPUT_ROOT / "CHECK_V1_SOURCE_DEPTH_FIXTURES.json").read_text(encoding="utf-8"))
        cls.reports = json.loads((OUTPUT_ROOT / "CHECK_V1_REPORTS.json").read_text(encoding="utf-8"))
        cls.contradiction_report = json.loads((OUTPUT_ROOT / "CHECK_V1_CONTRADICTION_DETECTION_REPORT.json").read_text(encoding="utf-8"))
        cls.source_depth_report = json.loads((OUTPUT_ROOT / "CHECK_V1_SOURCE_DEPTH_REPORT.json").read_text(encoding="utf-8"))
        cls.retained_pair = json.loads((OUTPUT_ROOT / "ASK_RETAINED_CONTRADICTION_PAIR_V4.json").read_text(encoding="utf-8"))
        cls.cer = json.loads((ROOT / "outputs" / "push4_lane_a_cer_engine" / "CER_RUNTIME_FIXTURES.json").read_text(encoding="utf-8"))
        cls.assertions = cls.cer["attribute_assertions"]

    def test_required_outputs_exist(self):
        required = [
            "CHECK_V1_DECISION.json",
            "CHECK_V1_CONTRACT_OVERVIEW.md",
            "CHECK_V1_REPORT_SCHEMA.json",
            "CHECK_V1_CLAIM_TO_EVIDENCE_FIXTURES.json",
            "CHECK_V1_CONTRADICTION_FIXTURES.json",
            "CHECK_V1_SOURCE_DEPTH_FIXTURES.json",
            "CHECK_V1_REPORTS.json",
            "CHECK_V1_CONTRADICTION_DETECTION_REPORT.json",
            "CHECK_V1_SOURCE_DEPTH_REPORT.json",
            "CHECK_V1_BOUNDARY_AND_NON_CLAIMS.md",
            "CHECK_V1_TEST_LOG.md",
            "CHECK_V1_HASH_MANIFEST.json",
            "ASK_RETAINED_CONTRADICTION_PAIR_V4.json",
        ]
        for name in required:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        self.assertEqual(PASS_STATUS, self.decision["status"])

    def test_closeout_and_final_status_exist(self):
        for name in [
            "CHECK_V1_CLOSEOUT_DECISION.json",
            "CHECK_V1_CLOSEOUT_SUMMARY.md",
            "CHECK_V1_CLOSEOUT_LIMITATIONS.md",
            "CHECK_V1_CLOSEOUT_NEXT_STEPS.md",
            "CHECK_V1_CLOSEOUT_HASH_MANIFEST.json",
        ]:
            self.assertTrue((CLOSEOUT_ROOT / name).exists(), name)
        for name in [
            "CHECK_V1_FINAL_STATUS_DECISION.json",
            "CHECK_V1_FINAL_STATUS_SUMMARY.md",
            "CHECK_V1_FINAL_STATUS_HASH_MANIFEST.json",
        ]:
            self.assertTrue((FINAL_ROOT / name).exists(), name)
        closeout = json.loads((CLOSEOUT_ROOT / "CHECK_V1_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        final = json.loads((FINAL_ROOT / "CHECK_V1_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))
        self.assertEqual(CLOSEOUT_STATUS, closeout["status"])
        self.assertEqual(FINAL_STATUS, final["status"])

    def test_check_v1_consumes_cer_attribute_assertions(self):
        assertion_refs = {item["assertion_id"] for item in self.assertions}
        self.assertEqual(len(assertion_refs), len(self.mappings["items"]))
        self.assertEqual(len(assertion_refs), len(self.reports["items"]))
        for report in self.reports["items"]:
            self.assertEqual(1, len(report["attribute_assertion_refs"]))
            self.assertIn(report["attribute_assertion_refs"][0], assertion_refs)
            self.assertTrue(report["authority_envelope_ref"])
            self.assertTrue(report["trace_refs"])

    def test_claim_to_evidence_mapping_preserves_evidence_and_authority(self):
        for mapping in self.mappings["items"]:
            self.assertTrue(mapping["supporting_evidence_refs"])
            self.assertTrue(mapping["source_ref"])
            self.assertTrue(mapping["source_record_ref"])
            self.assertTrue(mapping["check_report_ref"])
            self.assertTrue(mapping["authority_envelope_ref"])
            self.assertGreaterEqual(mapping["source_depth"], 1)

    def test_contradiction_detection_retains_same_claim_pair(self):
        pairs = self.contradictions["items"]
        self.assertGreaterEqual(len(pairs), 1)
        pair = pairs[0]
        self.assertTrue(pair["retained_same_claim_pair"])
        self.assertTrue(pair["incompatible_values"])
        self.assertTrue(pair["different_source_refs"])
        self.assertEqual(pair["entity_ref"], self.retained_pair["entity_ref"])
        self.assertEqual(pair["attribute_name"], self.retained_pair["attribute_name"])
        self.assertTrue(self.retained_pair["contradicting_evidence_refs"])
        self.assertTrue(self.contradiction_report["ask_contradiction_waiver_closed"])

    def test_contradicted_claims_are_not_claimable(self):
        contradicted_refs = set()
        for pair in self.contradictions["items"]:
            contradicted_refs.add(pair["left_assertion_ref"])
            contradicted_refs.add(pair["right_assertion_ref"])
        reports = [item for item in self.reports["items"] if item["claim_ref"] in contradicted_refs]
        self.assertTrue(reports)
        for report in reports:
            self.assertEqual("contradicted", report["claimability_status"])
            self.assertNotEqual("supported_for_local_review", report["claimability_status"])
            self.assertTrue(report["contradicting_assertion_refs"])

    def test_source_depth_scoring_distinguishes_required_classes(self):
        profile_labels = {item["source_depth_label"] for item in self.source_depth["source_depth_profiles"]}
        self.assertTrue(
            {
                "direct_source_record",
                "dataset_annotation",
                "sensor_inference",
                "model_generated_narrative_sidecar",
                "manual_review_note",
                "derived_assertion",
            }.issubset(profile_labels)
        )
        actual_labels = {item["source_depth_label"] for item in self.source_depth["source_depth_scores"]}
        self.assertIn("direct_source_record", actual_labels)
        self.assertIn("sensor_inference", actual_labels)
        self.assertIn("model_generated_narrative_sidecar", actual_labels)
        self.assertTrue(self.source_depth_report["distinguishes_required_depths"])
        self.assertFalse(self.source_depth_report["vss_narrative_can_source_truth"])

    def test_vss_narrative_cannot_become_source_truth(self):
        base = dict(self.assertions[0])
        base.update(
            {
                "assertion_id": "test:vss:assertion",
                "attribute_name": "vss_narrative_summary",
                "attribute_value": "candidate review context",
                "source_class": "vss_derived",
                "assertion_status": "review_required",
            }
        )
        self.assertEqual("not_authoritative", claimability_status_for_assertion(base))

    def test_unsupported_and_missing_evidence_claims_are_blocked(self):
        base = dict(self.assertions[0])
        unsupported = dict(base)
        unsupported["assertion_status"] = "rejected_local"
        self.assertEqual("unsupported", claimability_status_for_assertion(unsupported))
        missing_evidence = dict(base)
        missing_evidence["evidence_refs"] = []
        self.assertEqual("insufficient_evidence", claimability_status_for_assertion(missing_evidence))

    def test_legal_certified_official_action_claims_rejected(self):
        with self.assertRaises(ValueError):
            validate_claimability_status("official_truth")
        with self.assertRaises(ValueError):
            validate_claimability_status("legal_finding")
        base = dict(self.assertions[0])
        base.update({"attribute_name": "official_action", "attribute_value": "dispatch_authorized"})
        self.assertEqual("blocked_by_boundary", claimability_status_for_assertion(base))

    def test_hash_manifests_verify_and_protected_diffs_clean(self):
        for root, name in [
            (OUTPUT_ROOT, "CHECK_V1_HASH_MANIFEST.json"),
            (CLOSEOUT_ROOT, "CHECK_V1_CLOSEOUT_HASH_MANIFEST.json"),
            (FINAL_ROOT, "CHECK_V1_FINAL_STATUS_HASH_MANIFEST.json"),
        ]:
            report = verify_hash_manifest_for(root, name)
            self.assertEqual("PASS", report["status"], report)
            self.assertEqual(report["declared"], report["verified"])
        ask = subprocess.run(["git", "diff", "--", *ASK_CONTRACT_PATHS], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        r7 = subprocess.run(["git", "diff", "--", *R7_RUNTIME_PATHS], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self.assertEqual("", ask.stdout)
        self.assertEqual("", r7.stdout)


if __name__ == "__main__":
    unittest.main()

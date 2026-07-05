import json
import subprocess
import unittest
from pathlib import Path

from packages.cer import FORBIDDEN_ASSERTION_STATUSES, build_attribute_assertion
from scripts.run_main_citybrain_push4_lane_a_cer_engine import (
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


class MainCityBrainPush4LaneACerEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_outputs({"runner": "TEST_SETUP"})
        cls.decision = json.loads((OUTPUT_ROOT / "CER_ENGINE_DECISION.json").read_text(encoding="utf-8"))
        cls.fixtures = json.loads((OUTPUT_ROOT / "CER_RUNTIME_FIXTURES.json").read_text(encoding="utf-8"))
        cls.conflicts = json.loads((OUTPUT_ROOT / "CER_CONFLICT_FIXTURES.json").read_text(encoding="utf-8"))
        cls.matches = json.loads((OUTPUT_ROOT / "CER_MATCH_CANDIDATE_FIXTURES.json").read_text(encoding="utf-8"))
        cls.links = json.loads((OUTPUT_ROOT / "CER_ASSERTION_EVIDENCE_LINKS.json").read_text(encoding="utf-8"))
        cls.closeout = json.loads((CLOSEOUT_ROOT / "CER_ENGINE_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        cls.final = json.loads((FINAL_ROOT / "CER_ENGINE_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))
        cls.assertions = cls.fixtures["attribute_assertions"]

    def test_required_outputs_exist(self):
        required = [
            "CER_ENGINE_DECISION.json",
            "CER_CONTRACT_OVERVIEW.md",
            "CER_ENTITY_IDENTITY_RECORD_SCHEMA.json",
            "CER_ATTRIBUTE_ASSERTION_SCHEMA.json",
            "CER_ATTRIBUTE_CONFLICT_SCHEMA.json",
            "CER_MATCH_CANDIDATE_SCHEMA.json",
            "CER_REVIEW_STATE_SCHEMA.json",
            "CER_RUNTIME_FIXTURES.json",
            "CER_ASSERTION_EVIDENCE_LINKS.json",
            "CER_CONFLICT_FIXTURES.json",
            "CER_MATCH_CANDIDATE_FIXTURES.json",
            "CER_BOUNDARY_AND_NON_CLAIMS.md",
            "CER_TEST_LOG.md",
            "CER_HASH_MANIFEST.json",
        ]
        for name in required:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        self.assertEqual(PASS_STATUS, self.decision["status"])

    def test_closeout_and_final_status_exist(self):
        for name in [
            "CER_ENGINE_CLOSEOUT_DECISION.json",
            "CER_ENGINE_CLOSEOUT_SUMMARY.md",
            "CER_ENGINE_CLOSEOUT_LIMITATIONS.md",
            "CER_ENGINE_CLOSEOUT_NEXT_STEPS.md",
            "CER_ENGINE_CLOSEOUT_HASH_MANIFEST.json",
        ]:
            self.assertTrue((CLOSEOUT_ROOT / name).exists(), name)
        for name in [
            "CER_ENGINE_FINAL_STATUS_DECISION.json",
            "CER_ENGINE_FINAL_STATUS_SUMMARY.md",
            "CER_ENGINE_FINAL_STATUS_HASH_MANIFEST.json",
        ]:
            self.assertTrue((FINAL_ROOT / name).exists(), name)
        self.assertEqual(CLOSEOUT_STATUS, self.closeout["status"])
        self.assertEqual(FINAL_STATUS, self.final["status"])

    def test_attribute_assertions_are_created_from_source_and_evidence_refs(self):
        self.assertGreaterEqual(len(self.assertions), 5)
        required = [
            "assertion_id",
            "schema_version",
            "entity_ref",
            "attribute_name",
            "attribute_value",
            "attribute_value_type",
            "source_class",
            "source_ref",
            "source_record_ref",
            "evidence_refs",
            "limitation_refs",
            "trace_refs",
            "check_report_ref",
            "authority_envelope_ref",
            "assertion_status",
            "review_state",
            "confidence",
            "freshness_status",
            "created_at",
            "updated_at",
            "cannot_claim",
        ]
        for assertion in self.assertions:
            for field in required:
                self.assertIn(field, assertion)
            self.assertTrue(assertion["source_ref"])
            self.assertTrue(assertion["source_record_ref"])
            self.assertTrue(assertion["evidence_refs"])
            self.assertTrue(assertion["limitation_refs"])
            self.assertTrue(assertion["trace_refs"])

    def test_attribute_conflicts_are_detected_between_competing_assertions(self):
        conflict_items = self.conflicts["items"]
        self.assertGreaterEqual(len(conflict_items), 1)
        conflict = conflict_items[0]
        self.assertEqual("candidate_object_class", conflict["attribute_name"])
        self.assertGreaterEqual(len(conflict["competing_assertion_refs"]), 2)
        self.assertEqual("review_required", conflict["review_state"])

    def test_match_candidates_do_not_make_final_identity_claims(self):
        items = self.matches["items"]
        self.assertGreaterEqual(len(items), 1)
        for item in items:
            self.assertFalse(item["identity_claimed"])
            self.assertFalse(item["cross_city_claim"])
            self.assertEqual("review_required", item["review_state"])
            self.assertTrue(item["match_features"])

    def test_source_class_boundaries_preserved(self):
        summary = self.fixtures["source_assertion_summary"]
        self.assertFalse(summary["vss_truth_created"])
        self.assertFalse(summary["sensor_inferred_official_truth_created"])
        self.assertFalse(summary["official_truth_claim_created"])
        sensor_assertions = [item for item in self.assertions if item["source_class"] == "sensor_inferred"]
        self.assertTrue(sensor_assertions)
        for assertion in sensor_assertions:
            self.assertNotEqual("accepted_local", assertion["assertion_status"])
            self.assertFalse(assertion["official_truth_claim"])

    def test_forbidden_authority_claims_are_rejected(self):
        base = dict(self.assertions[0])
        for status in FORBIDDEN_ASSERTION_STATUSES:
            with self.assertRaises(ValueError):
                build_attribute_assertion(
                    entity_ref=base["entity_ref"],
                    attribute_name=f"forbidden_{status}",
                    attribute_value=status,
                    attribute_value_type="string",
                    source_class="source_record",
                    source_ref=base["source_ref"],
                    source_record_ref=base["source_record_ref"],
                    evidence_refs=base["evidence_refs"],
                    limitation_refs=base["limitation_refs"],
                    trace_refs=base["trace_refs"],
                    check_report_ref=base["check_report_ref"],
                    authority_envelope_ref=base["authority_envelope_ref"],
                    assertion_status=status,
                )

    def test_check_authority_refs_preserved(self):
        coverage = self.decision["coverage"]
        self.assertEqual("PASS", coverage["status"])
        self.assertEqual(coverage["attribute_assertion_count"], coverage["assertions_with_check_report_ref"])
        self.assertEqual(coverage["attribute_assertion_count"], coverage["assertions_with_authority_envelope_ref"])
        for assertion in self.assertions:
            self.assertTrue(assertion["check_report_ref"])
            self.assertTrue(assertion["authority_envelope_ref"])

    def test_evidence_limitation_trace_refs_preserved(self):
        self.assertEqual(len(self.assertions), len(self.links["items"]))
        for link in self.links["items"]:
            self.assertTrue(link["evidence_refs"])
            self.assertTrue(link["limitation_refs"])
            self.assertTrue(link["trace_refs"])
            self.assertTrue(link["check_report_ref"])
            self.assertTrue(link["authority_envelope_ref"])

    def test_hash_manifests_verify_and_protected_diffs_clean(self):
        for root, name in [
            (OUTPUT_ROOT, "CER_HASH_MANIFEST.json"),
            (CLOSEOUT_ROOT, "CER_ENGINE_CLOSEOUT_HASH_MANIFEST.json"),
            (FINAL_ROOT, "CER_ENGINE_FINAL_STATUS_HASH_MANIFEST.json"),
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

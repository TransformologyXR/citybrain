import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.run_main_citybrain_push2_lane_a_check_authority_v1 import (
    ASK_CONTRACT_PATHS,
    CLOSEOUT_ROOT,
    CLOSEOUT_STATUS,
    FINAL_ROOT,
    FINAL_STATUS,
    OUTPUT_ROOT,
    PASS_STATUS,
    R7_RUNTIME_PATHS,
    build_outputs,
    json_hash,
    verify_hash_manifest,
    verify_hash_manifest_for,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainPush2LaneACheckAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_outputs({"runner": "TEST_SETUP"})
        cls.decision = json.loads((OUTPUT_ROOT / "CHECK_V0_AUTHORITY_V1_DECISION.json").read_text(encoding="utf-8"))
        cls.reports = json.loads((OUTPUT_ROOT / "CHECK_REPORT_FIXTURES.json").read_text(encoding="utf-8"))
        cls.authority = json.loads((OUTPUT_ROOT / "AUTHORITY_ENVELOPE_FIXTURES.json").read_text(encoding="utf-8"))
        cls.negative = json.loads((OUTPUT_ROOT / "CHECK_V0_BOUNDARY_NEGATIVE_TESTS.json").read_text(encoding="utf-8"))
        cls.closeout = json.loads((CLOSEOUT_ROOT / "CHECK_V0_AUTHORITY_V1_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        cls.final = json.loads((FINAL_ROOT / "CHECK_V0_AUTHORITY_V1_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))

    def test_required_outputs_exist(self):
        required = [
            "CHECK_V0_AUTHORITY_V1_DECISION.json",
            "CHECK_V0_SCHEMA.json",
            "AUTHORITY_ENVELOPE_V1_SCHEMA.json",
            "CHECK_REPORT_FIXTURES.json",
            "AUTHORITY_ENVELOPE_FIXTURES.json",
            "CHECK_V0_BOUNDARY_NEGATIVE_TESTS.json",
            "CHECK_V0_FRESHNESS_POLICY.md",
            "CHECK_V0_ASK_ATTACHMENT_POLICY.md",
            "CHECK_V0_TEST_LOG.md",
            "CHECK_V0_HASH_MANIFEST.json",
        ]
        for name in required:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_closeout_and_final_status_outputs_exist(self):
        closeout_required = [
            "CHECK_V0_AUTHORITY_V1_CLOSEOUT_DECISION.json",
            "CHECK_V0_AUTHORITY_V1_CLOSEOUT_SUMMARY.md",
            "CHECK_V0_AUTHORITY_V1_CLOSEOUT_LIMITATIONS.md",
            "CHECK_V0_AUTHORITY_V1_CLOSEOUT_HASH_MANIFEST.json",
        ]
        final_required = [
            "CHECK_V0_AUTHORITY_V1_FINAL_STATUS_DECISION.json",
            "CHECK_V0_AUTHORITY_V1_FINAL_STATUS_SUMMARY.md",
            "CHECK_V0_AUTHORITY_V1_FINAL_STATUS_HASH_MANIFEST.json",
            "PUSH2_LANE_A_STAGED_SCOPE.md",
        ]
        for name in closeout_required:
            self.assertTrue((CLOSEOUT_ROOT / name).exists(), name)
        for name in final_required:
            self.assertTrue((FINAL_ROOT / name).exists(), name)
        self.assertEqual(CLOSEOUT_STATUS, self.closeout["status"])
        self.assertEqual(FINAL_STATUS, self.final["status"])

    def test_decision_passes_and_reports_are_real(self):
        self.assertEqual(PASS_STATUS, self.decision["status"])
        self.assertGreater(self.reports["report_count"], 10)
        for report in self.reports["check_reports"]:
            self.assertTrue(report["check_id"].startswith("check:v0:"))
            self.assertIn(report["status"], {"PASS", "PASS_WITH_LIMITATIONS", "FAIL"})
            self.assertIn(report["freshness_status"], {"current", "stale", "unknown", "not_applicable"})
            self.assertIn(report["authority_level"], {0, 1, 2})

    def test_required_packet_types_and_watch_item_contract_are_covered(self):
        covered = set(self.reports["covered_packet_types"])
        self.assertTrue({"CandidateObservation", "EventEnvelope", "QueryResultPacket", "OverlayPacket"}.issubset(covered))
        schema = json.loads((OUTPUT_ROOT / "CHECK_V0_SCHEMA.json").read_text(encoding="utf-8"))
        self.assertIn("WatchItem", schema["properties"]["packet_type"]["enum"])
        self.assertEqual("READY_FOR_WATCH_ITEM_ONCE_AVAILABLE", self.reports["watch_item_support"]["status"])

    def test_authority_envelope_levels_zero_to_two_are_emitted(self):
        self.assertEqual([0, 1, 2], self.authority["authority_levels_emitted"])
        by_level = {level: [] for level in [0, 1, 2]}
        for envelope in self.authority["authority_envelopes"]:
            by_level[envelope["authority_level"]].append(envelope)
            self.assertFalse(envelope["source_authority"]["official_action_allowed"])
            self.assertFalse(envelope["source_authority"]["dispatch_control_enforcement_allowed"])
            self.assertFalse(envelope["source_authority"]["legal_or_certified_finding_allowed"])
        for level, envelopes in by_level.items():
            self.assertTrue(envelopes, level)

    def test_source_class_validation_and_freshness_are_emitted(self):
        source_statuses = {report["source_class_status"] for report in self.reports["check_reports"]}
        freshness_statuses = {report["freshness_status"] for report in self.reports["check_reports"]}
        self.assertIn("pass", source_statuses)
        self.assertIn("fail", source_statuses)
        self.assertIn("current", freshness_statuses)
        self.assertIn("stale", freshness_statuses)
        stale_reports = [report for report in self.reports["check_reports"] if report["freshness_status"] == "stale"]
        self.assertTrue(all("freshness_policy" in report["failure_codes"] for report in stale_reports))

    def test_candidate_vss_and_sensor_are_not_official_truth(self):
        candidate_reports = [
            report
            for report in self.reports["check_reports"]
            if report["packet_type"] == "CandidateObservation" or report["source_class"] in {"vss_sensor_inferred", "sensor_inferred"}
        ]
        self.assertTrue(candidate_reports)
        for report in candidate_reports:
            self.assertFalse(report["official_truth_allowed"])
            self.assertFalse(report["official_action_allowed"])
        vss_reports = [report for report in candidate_reports if report["source_class"] == "vss_sensor_inferred"]
        sensor_reports = [report for report in candidate_reports if report["source_class"] == "sensor_inferred"]
        self.assertTrue(any("sensor_inferred_not_official_truth" in report["failure_codes"] for report in vss_reports))
        self.assertTrue(any("sensor_inferred_not_official_truth" in report["failure_codes"] for report in sensor_reports))

    def test_negative_boundary_cases_fail_check_as_expected(self):
        self.assertEqual("PASS", self.negative["status"])
        by_case = {case["case_id"]: case for case in self.negative["cases"]}
        required = [
            "negative:vss-not-fact-source",
            "negative:sensor-inferred-official-truth",
            "negative:candidate-observation-official-finding",
            "negative:official-action-dispatch-legal",
            "negative:stale-official-record",
            "negative:unsupported-source-class",
        ]
        for case_id in required:
            self.assertEqual("PASS", by_case[case_id]["status"], case_id)
            self.assertTrue(set(by_case[case_id]["expected_failure_codes"]).issubset(set(by_case[case_id]["observed_failure_codes"])))

    def test_ask_wrapper_attaches_check_without_mutating_consumed_packets(self):
        wrappers = self.reports["ask_wrapped_outputs"]
        self.assertTrue(wrappers)
        for wrapper in wrappers:
            self.assertEqual("app_handoff_adapter", wrapper["attachment_layer"])
            self.assertFalse(wrapper["sealed_ask_runtime_modified"])
            self.assertFalse(wrapper["g1_g8_modified"])
            self.assertTrue(wrapper["native_g6_integration_deferred"])
            self.assertEqual(wrapper["wrapped_packet_hash"], json_hash(wrapper["wrapped_packet"]))
            self.assertNotIn("check_report_ref", wrapper["wrapped_packet"])
            self.assertNotIn("authority_envelope_ref", wrapper["wrapped_packet"])

    def test_no_sealed_ask_or_r7_runtime_diff(self):
        ask = subprocess.run(["git", "diff", "--", *ASK_CONTRACT_PATHS], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        r7 = subprocess.run(["git", "diff", "--", *R7_RUNTIME_PATHS], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self.assertEqual("", ask.stdout)
        self.assertEqual("", r7.stdout)

    def test_hash_manifest_verifies(self):
        report = verify_hash_manifest()
        self.assertEqual("PASS", report["status"], report)
        self.assertEqual(report["declared"], report["verified"])
        closeout = verify_hash_manifest_for(CLOSEOUT_ROOT, "CHECK_V0_AUTHORITY_V1_CLOSEOUT_HASH_MANIFEST.json")
        final = verify_hash_manifest_for(FINAL_ROOT, "CHECK_V0_AUTHORITY_V1_FINAL_STATUS_HASH_MANIFEST.json")
        self.assertEqual("PASS", closeout["status"], closeout)
        self.assertEqual("PASS", final["status"], final)
        self.assertEqual(closeout["declared"], closeout["verified"])
        self.assertEqual(final["declared"], final["verified"])


if __name__ == "__main__":
    unittest.main()

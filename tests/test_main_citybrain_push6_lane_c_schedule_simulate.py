import json
import subprocess
import unittest
from pathlib import Path

from scripts.run_main_citybrain_push6_lane_c_schedule_simulate import (
    ASK_CONTRACT_PATHS,
    CLOSEOUT_ROOT,
    CLOSEOUT_STATUS,
    FINAL_ROOT,
    FINAL_STATUS,
    OUTPUT_ROOT,
    PASS_STATUS,
    R7_RUNTIME_PATHS,
    SIMULATION_CHECK_STATUSES,
    build_outputs,
    verify_hash_manifest_for,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainPush6LaneCScheduleSimulateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_outputs({"runner": "TEST_SETUP"})
        cls.decision = json.loads((OUTPUT_ROOT / "SCHEDULE_SIMULATE_DECISION.json").read_text(encoding="utf-8"))
        cls.schedule = json.loads((OUTPUT_ROOT / "SCHEDULE_OPTION_FIXTURES.json").read_text(encoding="utf-8"))
        cls.cuopt = json.loads((OUTPUT_ROOT / "CUOPT_SCHEDULING_FIXTURES.json").read_text(encoding="utf-8"))
        cls.sumo = json.loads((OUTPUT_ROOT / "SUMO_SCENARIO_FIXTURES.json").read_text(encoding="utf-8"))
        cls.checks = json.loads((OUTPUT_ROOT / "SIMULATION_CHECK_REPORTS.json").read_text(encoding="utf-8"))
        cls.bindings = json.loads((OUTPUT_ROOT / "SCHEDULE_APPROVAL_BINDINGS.json").read_text(encoding="utf-8"))

    def test_required_outputs_exist(self):
        required = [
            "SCHEDULE_SIMULATE_DECISION.json",
            "SCHEDULE_CONTRACT_OVERVIEW.md",
            "SCHEDULE_REQUEST_SCHEMA.json",
            "SCHEDULE_OPTION_SCHEMA.json",
            "SCENARIO_PACKET_SCHEMA.json",
            "SIMULATION_RUN_RECORD_SCHEMA.json",
            "SCHEDULE_OPTION_FIXTURES.json",
            "CUOPT_SCHEDULING_FIXTURES.json",
            "SUMO_SCENARIO_FIXTURES.json",
            "SIMULATION_CHECK_REPORTS.json",
            "SCHEDULE_APPROVAL_BINDINGS.json",
            "SCHEDULE_SIMULATE_BOUNDARY_AND_NON_CLAIMS.md",
            "SCHEDULE_SIMULATE_TEST_LOG.md",
            "SCHEDULE_SIMULATE_HASH_MANIFEST.json",
        ]
        for name in required:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        self.assertEqual(PASS_STATUS, self.decision["status"])

    def test_closeout_and_final_status_exist(self):
        for name in [
            "SCHEDULE_SIMULATE_CLOSEOUT_DECISION.json",
            "SCHEDULE_SIMULATE_CLOSEOUT_SUMMARY.md",
            "SCHEDULE_SIMULATE_CLOSEOUT_LIMITATIONS.md",
            "SCHEDULE_SIMULATE_CLOSEOUT_NEXT_STEPS.md",
            "SCHEDULE_SIMULATE_CLOSEOUT_HASH_MANIFEST.json",
        ]:
            self.assertTrue((CLOSEOUT_ROOT / name).exists(), name)
        for name in [
            "SCHEDULE_SIMULATE_FINAL_STATUS_DECISION.json",
            "SCHEDULE_SIMULATE_FINAL_STATUS_SUMMARY.md",
            "SCHEDULE_SIMULATE_FINAL_STATUS_HASH_MANIFEST.json",
        ]:
            self.assertTrue((FINAL_ROOT / name).exists(), name)
        closeout = json.loads((CLOSEOUT_ROOT / "SCHEDULE_SIMULATE_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        final = json.loads((FINAL_ROOT / "SCHEDULE_SIMULATE_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))
        self.assertEqual(CLOSEOUT_STATUS, closeout["status"])
        self.assertEqual(FINAL_STATUS, final["status"])

    def test_schedule_options_are_created_with_required_refs(self):
        self.assertEqual(1, len(self.schedule["schedule_requests"]))
        self.assertGreaterEqual(len(self.schedule["schedule_options"]), 2)
        for option in self.schedule["schedule_options"]:
            for field in [
                "schedule_option_id",
                "schedule_request_ref",
                "option_set_ref",
                "constraints_ref",
                "assumptions_ref",
                "resource_refs",
                "time_window",
                "evidence_refs",
                "limitation_refs",
                "trace_refs",
                "check_report_ref",
                "authority_envelope_ref",
                "approval_request_ref",
                "execution_status",
                "cannot_claim",
            ]:
                self.assertIn(field, option)
            self.assertTrue(option["approval_request_ref"].startswith("approval:request:"))
            self.assertTrue(option["check_report_ref"])
            self.assertTrue(option["authority_envelope_ref"].startswith("authority:l3:"))
            self.assertEqual("not_executed", option["execution_status"])

    def test_sumo_local_replay_scenario_fixture_exists(self):
        self.assertEqual("PASS", self.sumo["status"])
        self.assertEqual(1, len(self.sumo["scenario_packets"]))
        scenario = self.sumo["scenario_packets"][0]
        self.assertEqual("sumo_local_replay", scenario["simulator_kind"])
        self.assertEqual("not_executed", scenario["execution_status"])
        self.assertEqual("local_replay_fixture_evaluated", scenario["simulation_status"])
        self.assertTrue(scenario["approval_request_ref"])
        self.assertTrue(self.sumo["simulation_run_records"])

    def test_cuopt_scheduling_fixture_exists_or_limitation_recorded(self):
        self.assertEqual("PASS_WITH_LIMITATION", self.cuopt["status"])
        self.assertFalse(self.cuopt["runtime_invoked"])
        self.assertTrue(self.cuopt["limitation"])
        self.assertGreaterEqual(len(self.cuopt["schedule_options"]), 2)
        self.assertEqual("cuopt_fixture", self.cuopt["scenario_packets"][0]["simulator_kind"])
        self.assertEqual("not_executed", self.cuopt["scenario_packets"][0]["execution_status"])

    def test_scenario_packets_are_created_with_required_refs(self):
        scenarios = self.sumo["scenario_packets"] + self.cuopt["scenario_packets"]
        self.assertEqual(2, len(scenarios))
        for scenario in scenarios:
            self.assertTrue(scenario["scenario_packet_id"])
            self.assertIn(scenario["simulator_kind"], {"sumo_local_replay", "cuopt_fixture", "deterministic_fixture"})
            self.assertNotIn(scenario["simulator_kind"], {"production_control", "live_dispatch", "live_signal_control", "official_schedule_execution"})
            self.assertTrue(scenario["input_refs"])
            self.assertTrue(scenario["assumptions"])
            self.assertTrue(scenario["constraints"])
            self.assertTrue(scenario["approval_request_ref"])
            self.assertTrue(scenario["check_report_ref"])
            self.assertTrue(scenario["authority_envelope_ref"])
            self.assertEqual("not_executed", scenario["execution_status"])

    def test_simulation_check_reports_emit_required_statuses(self):
        self.assertEqual("PASS", self.checks["status"])
        self.assertEqual(2, len(self.checks["items"]))
        status_union = set()
        for report in self.checks["items"]:
            status_union.update(report["simulation_check_statuses"])
            self.assertTrue(report["not_calibrated_for_prediction"])
            self.assertTrue(report["local_replay_only"])
            self.assertTrue(report["not_actionable_without_approval"])
            self.assertEqual("not_executed", report["execution_status"])
            self.assertTrue(report["approval_request_ref"])
        for status in SIMULATION_CHECK_STATUSES:
            self.assertIn(status, status_union)

    def test_schedule_approval_bindings_use_approval_lifecycle(self):
        self.assertEqual("PASS", self.bindings["status"])
        self.assertGreaterEqual(len(self.bindings["items"]), 4)
        for binding in self.bindings["items"]:
            self.assertTrue(binding["approval_lifecycle_used"])
            self.assertEqual("authority_level_3", binding["authority_level_required"])
            self.assertTrue(binding["approval_request_ref"].startswith("approval:request:"))
            self.assertEqual("not_executed", binding["execution_status"])
            self.assertFalse(binding["approval_bypass"])

    def test_no_live_dispatch_control_signal_or_official_execution(self):
        blob = json.dumps(
            {
                "schedule": self.schedule,
                "cuopt": self.cuopt,
                "sumo": self.sumo,
                "checks": self.checks,
                "bindings": self.bindings,
            },
            sort_keys=True,
        ).lower()
        forbidden = [
            '"execution_status": "executed"',
            "production_control",
            "live_dispatch",
            "live_signal_control",
            "official_schedule_execution",
            "dispatch_authorized",
            "legal_finding",
            "certified_fact",
        ]
        for token in forbidden:
            self.assertNotIn(token, blob)
        self.assertIn("not_executed", blob)

    def test_contract_decision_flags_are_green(self):
        contract = self.decision["contract_check"]
        self.assertTrue(contract["lane_c_only"])
        self.assertTrue(contract["local_replay_only"])
        self.assertTrue(contract["approval_lifecycle_used"])
        self.assertTrue(contract["no_execution"])
        self.assertTrue(contract["no_live_dispatch_control_signal_control"])
        self.assertTrue(contract["no_legal_certified_official_schedule_claim"])
        self.assertTrue(contract["no_live_api_url_llm"])

    def test_hash_manifests_verify_and_protected_diffs_clean(self):
        for root, name in [
            (OUTPUT_ROOT, "SCHEDULE_SIMULATE_HASH_MANIFEST.json"),
            (CLOSEOUT_ROOT, "SCHEDULE_SIMULATE_CLOSEOUT_HASH_MANIFEST.json"),
            (FINAL_ROOT, "SCHEDULE_SIMULATE_FINAL_STATUS_HASH_MANIFEST.json"),
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

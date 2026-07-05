import json
import subprocess
import unittest
from pathlib import Path

from scripts.run_main_citybrain_push6_infra_after_three_lanes import (
    ASK_CONTRACT_PATHS,
    CLOSEOUT_ROOT,
    FINAL_ROOT,
    OUTPUT_ROOT,
    PASS_STATUS,
    R7_RUNTIME_PATHS,
    REQUIRED_CLOSEOUT_OUTPUTS,
    REQUIRED_FINAL_OUTPUTS,
    REQUIRED_OUTPUTS,
    verify_hash_manifest,
    write_all_outputs,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainPush6InfraAfterThreeLanesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = write_all_outputs()
        cls.decision = json.loads((OUTPUT_ROOT / "PUSH6_INFRA_INTEGRATION_DECISION.json").read_text(encoding="utf-8"))
        cls.join = json.loads((OUTPUT_ROOT / "PUSH6_APPROVAL_PLAN_SCHEDULE_JOIN_REPORT.json").read_text(encoding="utf-8"))
        cls.compatibility = json.loads((OUTPUT_ROOT / "PUSH6_CROSS_LANE_COMPATIBILITY_REPORT.json").read_text(encoding="utf-8"))
        cls.closeout = json.loads((CLOSEOUT_ROOT / "PUSH6_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        cls.final = json.loads((FINAL_ROOT / "PUSH6_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))

    def test_required_outputs_exist(self):
        for name in REQUIRED_OUTPUTS:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        for name in REQUIRED_CLOSEOUT_OUTPUTS:
            self.assertTrue((CLOSEOUT_ROOT / name).exists(), name)
        for name in REQUIRED_FINAL_OUTPUTS:
            self.assertTrue((FINAL_ROOT / name).exists(), name)

    def test_decision_passes_with_expected_counts(self):
        self.assertEqual(PASS_STATUS, self.decision["status"])
        self.assertFalse(self.decision["canonical_merged"])
        self.assertEqual(["lane_a", "lane_b", "lane_c"], self.decision["merge_order"])
        self.assertEqual(3, self.decision["counts"]["approval_request_count"])
        self.assertEqual(1, self.decision["counts"]["plan_option_set_count"])
        self.assertEqual(2, self.decision["counts"]["schedule_option_count"])
        self.assertEqual(2, self.decision["counts"]["schedule_scenario_packet_count"])

    def test_approval_plan_schedule_join_is_safe(self):
        self.assertEqual("PASS", self.join["status"], self.join)
        checks = self.join["checks"]
        self.assertTrue(checks["approval_lifecycle_available"])
        self.assertTrue(checks["plan_optionsets_carry_approval_request_ref"])
        self.assertTrue(checks["plan_provisional_approval_binding_recorded"])
        self.assertTrue(checks["plan_option_sets_join_schedule_option_sets"])
        self.assertTrue(checks["schedule_packets_carry_approval_request_ref"])
        self.assertTrue(checks["schedule_simulate_uses_approval_lifecycle"])
        self.assertTrue(checks["plan_candidates_remain_not_executed"])
        self.assertTrue(checks["schedule_simulate_candidates_remain_not_executed"])

    def test_compatibility_gates_pass(self):
        self.assertEqual("PASS", self.compatibility["status"], self.compatibility)
        self.assertTrue(all(self.compatibility["gates"].values()), self.compatibility["gates"])
        self.assertTrue(self.compatibility["gates"]["approved_local_not_executed_submitted"])
        self.assertTrue(self.compatibility["gates"]["sumo_cuopt_local_replay_fixture_only"])

    def test_closeout_and_final_pass(self):
        self.assertEqual(PASS_STATUS, self.closeout["status"])
        self.assertEqual(PASS_STATUS, self.final["status"])
        self.assertTrue(self.closeout["completed_through"]["compatibility"])
        self.assertEqual("codex/push6-infra-after-three-lanes", self.final["branch"])

    def test_hashes_and_protected_diffs_clean(self):
        for root, name in [
            (OUTPUT_ROOT, "PUSH6_HASH_MANIFEST.json"),
            (CLOSEOUT_ROOT, "PUSH6_CLOSEOUT_HASH_MANIFEST.json"),
            (FINAL_ROOT, "PUSH6_FINAL_STATUS_HASH_MANIFEST.json"),
        ]:
            report = verify_hash_manifest(root, name)
            self.assertEqual("PASS", report["status"], report)
            self.assertEqual(report["declared"], report["verified"])

        ask = subprocess.run(["git", "diff", "--", *ASK_CONTRACT_PATHS], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        r7 = subprocess.run(["git", "diff", "--", *R7_RUNTIME_PATHS], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self.assertEqual("", ask.stdout)
        self.assertEqual("", r7.stdout)


if __name__ == "__main__":
    unittest.main()

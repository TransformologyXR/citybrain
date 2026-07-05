import json
import subprocess
import unittest
from pathlib import Path

from scripts.run_main_citybrain_push7_infra_after_three_lanes import (
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


class MainCityBrainPush7InfraAfterThreeLanesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = write_all_outputs()
        cls.decision = json.loads((OUTPUT_ROOT / "PUSH7_INFRA_INTEGRATION_DECISION.json").read_text(encoding="utf-8"))
        cls.compatibility = json.loads((OUTPUT_ROOT / "PUSH7_CROSS_LANE_COMPATIBILITY_REPORT.json").read_text(encoding="utf-8"))
        cls.federation = json.loads((OUTPUT_ROOT / "PUSH7_FEDERATION_DATA_MATURITY_REPORT.json").read_text(encoding="utf-8"))
        cls.rbac = json.loads((OUTPUT_ROOT / "PUSH7_RBAC_AUDIT_OBSERVABILITY_REPORT.json").read_text(encoding="utf-8"))
        cls.execution = json.loads((OUTPUT_ROOT / "PUSH7_EXECUTION_AUTONOMY_PREFLIGHT_REPORT.json").read_text(encoding="utf-8"))
        cls.boundary = json.loads((OUTPUT_ROOT / "PUSH7_BOUNDARY_STRUCTURAL_SCAN.json").read_text(encoding="utf-8"))
        cls.closeout = json.loads((CLOSEOUT_ROOT / "PUSH7_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        cls.final = json.loads((FINAL_ROOT / "PUSH7_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))

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
        self.assertEqual(4, self.decision["counts"]["department_local_node_count"])
        self.assertEqual(8, self.decision["counts"]["data_maturity_score_count"])
        self.assertEqual(6, self.decision["counts"]["federated_packet_envelope_count"])
        self.assertEqual(14, self.decision["counts"]["audit_event_count"])
        self.assertEqual(7, self.decision["counts"]["adapter_preflight_result_count"])

    def test_federation_and_dubai_boundary(self):
        self.assertEqual("PASS", self.federation["status"], self.federation)
        checks = self.federation["checks"]
        self.assertTrue(checks["department_local_nodes_exist"])
        self.assertTrue(checks["data_maturity_scores_exist"])
        self.assertTrue(checks["maturity_scores_stay_allowed"])
        self.assertTrue(checks["federated_envelopes_preserve_refs"])
        self.assertTrue(checks["dubai_pack_synthetic_only"])

    def test_rbac_audit_observability_boundary(self):
        self.assertEqual("PASS", self.rbac["status"], self.rbac)
        checks = self.rbac["checks"]
        self.assertTrue(checks["rbac_forbids_execution_dispatch_control_legal_certified"])
        self.assertTrue(checks["policies_are_local_not_production_iam"])
        self.assertTrue(checks["roles_have_no_execution_permission"])
        self.assertTrue(checks["forbidden_permissions_rejected"])
        self.assertTrue(checks["audit_covers_approval_plan_schedule_federation"])
        self.assertTrue(checks["observability_required_signals_present"])

    def test_execution_autonomy_preflight_boundary(self):
        self.assertEqual("PASS", self.execution["status"], self.execution)
        checks = self.execution["checks"]
        self.assertTrue(checks["adapter_registry_dry_run_preflight_only"])
        self.assertTrue(checks["adapter_requests_not_executed"])
        self.assertTrue(checks["adapter_results_not_executed_no_external_action"])
        self.assertTrue(checks["conditional_autonomy_blocked_preflight_only"])
        self.assertTrue(checks["autonomy_policies_cannot_authorize_action"])
        self.assertTrue(checks["autonomy_blocks_prevent_action"])
        self.assertTrue(checks["execution_audit_covers_preflight_events"])
        self.assertTrue(checks["execution_audit_not_executed"])

    def test_compatibility_and_no_overclaim(self):
        self.assertEqual("PASS", self.compatibility["status"], self.compatibility)
        self.assertTrue(all(self.compatibility["gates"].values()), self.compatibility["gates"])
        self.assertEqual("PASS", self.boundary["status"], self.boundary)
        self.assertEqual({}, self.boundary["hits"])

    def test_closeout_final_hashes_and_protected_diffs(self):
        self.assertEqual(PASS_STATUS, self.closeout["status"])
        self.assertEqual(PASS_STATUS, self.final["status"])
        self.assertFalse(self.final["canonical_merged"])
        for root, name in [
            (OUTPUT_ROOT, "PUSH7_HASH_MANIFEST.json"),
            (CLOSEOUT_ROOT, "PUSH7_CLOSEOUT_HASH_MANIFEST.json"),
            (FINAL_ROOT, "PUSH7_FINAL_STATUS_HASH_MANIFEST.json"),
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

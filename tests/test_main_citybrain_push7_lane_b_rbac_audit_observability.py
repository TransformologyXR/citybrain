import json
import subprocess
import unittest
from pathlib import Path

from packages.governance import FORBIDDEN_PERMISSIONS, ROLE_PERMISSIONS
from scripts.run_main_citybrain_push7_lane_b_rbac_audit_observability import (
    ASK_CONTRACT_PATHS,
    CLOSEOUT_ROOT,
    FINAL_ROOT,
    OUTPUT_ROOT,
    PASS_STATUS,
    R7_RUNTIME_PATHS,
    REQUIRED_CLOSEOUT_OUTPUTS,
    REQUIRED_FINAL_OUTPUTS,
    REQUIRED_OUTPUTS,
    SIGNAL_TYPES,
    verify_hash_manifest,
    write_all_outputs,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainPush7LaneBRbacAuditObservabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = write_all_outputs()
        cls.decision = json.loads((OUTPUT_ROOT / "RBAC_AUDIT_OBSERVABILITY_DECISION.json").read_text(encoding="utf-8"))
        cls.roles = json.loads((OUTPUT_ROOT / "ROLE_DEFINITIONS.json").read_text(encoding="utf-8"))
        cls.policies = json.loads((OUTPUT_ROOT / "PERMISSION_POLICIES.json").read_text(encoding="utf-8"))
        cls.access = json.loads((OUTPUT_ROOT / "ACCESS_DECISION_FIXTURES.json").read_text(encoding="utf-8"))
        cls.audit = json.loads((OUTPUT_ROOT / "AUDIT_EVENT_FIXTURES.json").read_text(encoding="utf-8"))
        cls.observability = json.loads((OUTPUT_ROOT / "OBSERVABILITY_SIGNALS.json").read_text(encoding="utf-8"))
        cls.health = json.loads((OUTPUT_ROOT / "HEALTH_SNAPSHOTS.json").read_text(encoding="utf-8"))
        cls.negative = json.loads((OUTPUT_ROOT / "POLICY_NEGATIVE_TESTS.json").read_text(encoding="utf-8"))
        cls.dashboard = json.loads((OUTPUT_ROOT / "GOVERNANCE_DASHBOARD_VIEW_MODEL.json").read_text(encoding="utf-8"))
        cls.closeout = json.loads((CLOSEOUT_ROOT / "RBAC_AUDIT_OBSERVABILITY_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        cls.final = json.loads((FINAL_ROOT / "RBAC_AUDIT_OBSERVABILITY_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))

    def test_required_outputs_exist(self):
        for name in REQUIRED_OUTPUTS:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        for name in REQUIRED_CLOSEOUT_OUTPUTS:
            self.assertTrue((CLOSEOUT_ROOT / name).exists(), name)
        for name in REQUIRED_FINAL_OUTPUTS:
            self.assertTrue((FINAL_ROOT / name).exists(), name)

    def test_roles_validate_without_execution_permissions(self):
        self.assertEqual("PASS", self.roles["status"])
        self.assertEqual(set(ROLE_PERMISSIONS), {role["role_id"] for role in self.roles["roles"]})
        for role in self.roles["roles"]:
            self.assertFalse(set(role["permissions"]).intersection(FORBIDDEN_PERMISSIONS), role)
            self.assertFalse(role["execution_permission"])
            self.assertTrue(role["not_production_iam"])

    def test_policies_cover_permissions_and_forbid_execution(self):
        policy_permissions = {policy["permission"] for policy in self.policies["policies"]}
        self.assertEqual(set(self.policies["allowed_permissions"]), policy_permissions)
        self.assertEqual(set(FORBIDDEN_PERMISSIONS), set(self.policies["forbidden_permissions"]))
        for policy in self.policies["policies"]:
            self.assertNotIn(policy["permission"], FORBIDDEN_PERMISSIONS)
            self.assertEqual("allow_local_replay_only", policy["effect"])

    def test_access_decisions_preserve_boundaries(self):
        self.assertEqual("PASS", self.access["status"])
        self.assertTrue(self.access["forbidden_permissions_rejected"])
        for decision in self.access["access_decisions"]:
            if decision["permission"] in FORBIDDEN_PERMISSIONS:
                self.assertEqual("deny", decision["decision"], decision)
            self.assertFalse(decision["production_iam_claim"])
            self.assertTrue(decision["check_report_ref"])
            self.assertTrue(decision["authority_envelope_ref"])

    def test_audit_events_preserve_refs(self):
        self.assertEqual("PASS", self.audit["status"])
        self.assertTrue(self.audit["evidence_refs_preserved"])
        self.assertTrue(self.audit["check_authority_refs_preserved"])
        for event in self.audit["audit_events"]:
            for field in [
                "audit_event_id",
                "actor_ref",
                "role_ref",
                "action",
                "target_ref",
                "target_type",
                "timestamp",
                "access_decision_ref",
                "evidence_refs",
                "limitation_refs",
                "trace_refs",
                "check_report_ref",
                "authority_envelope_ref",
                "not_executed",
                "cannot_claim",
            ]:
                self.assertTrue(event[field], field)

    def test_observability_and_health_are_non_production(self):
        signal_types = {signal["signal_type"] for signal in self.observability["signals"]}
        self.assertEqual(set(SIGNAL_TYPES), signal_types)
        self.assertTrue(self.observability["no_production_monitoring_claim"])
        self.assertTrue(self.health["no_production_incident_claim"])
        self.assertGreaterEqual(len(self.health["degradation_records"]), 1)

    def test_negative_policy_cases(self):
        self.assertTrue(self.negative["forbidden_permissions_rejected"])
        self.assertTrue(self.negative["approver_local_cannot_execute"])
        self.assertTrue(self.negative["planner_can_only_propose"])
        self.assertTrue(self.negative["simulator_can_only_propose"])
        self.assertTrue(self.negative["auditor_can_view_logs_not_modify_actions"])
        self.assertTrue(self.negative["no_production_iam_claim"])

    def test_decision_closeout_final_and_hashes(self):
        self.assertEqual(PASS_STATUS, self.decision["status"])
        self.assertEqual(PASS_STATUS, self.closeout["status"])
        self.assertEqual(PASS_STATUS, self.final["status"])
        self.assertFalse(self.decision["canonical_merged"])
        self.assertTrue(all(self.decision["gates"].values()), self.decision["gates"])
        self.assertTrue(self.dashboard["not_production_iam"])
        for root, name in [
            (OUTPUT_ROOT, "RBAC_AUDIT_HASH_MANIFEST.json"),
            (CLOSEOUT_ROOT, "RBAC_AUDIT_OBSERVABILITY_CLOSEOUT_HASH_MANIFEST.json"),
            (FINAL_ROOT, "RBAC_AUDIT_OBSERVABILITY_FINAL_STATUS_HASH_MANIFEST.json"),
        ]:
            report = verify_hash_manifest(root, name)
            self.assertEqual("PASS", report["status"], report)
            self.assertEqual(report["declared"], report["verified"])

    def test_protected_diffs_clean(self):
        ask = subprocess.run(["git", "diff", "--", *ASK_CONTRACT_PATHS], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        r7 = subprocess.run(["git", "diff", "--", *R7_RUNTIME_PATHS], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self.assertEqual("", ask.stdout)
        self.assertEqual("", r7.stdout)


if __name__ == "__main__":
    unittest.main()

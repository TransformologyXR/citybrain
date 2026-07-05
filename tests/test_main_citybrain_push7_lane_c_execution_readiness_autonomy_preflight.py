import json
import subprocess
import unittest
from pathlib import Path

from scripts.run_main_citybrain_push7_lane_c_execution_readiness_autonomy_preflight import (
    ALLOWED_ADAPTER_KINDS,
    ASK_CONTRACT_PATHS,
    CLOSEOUT_ROOT,
    FINAL_ROOT,
    FINAL_STATUS,
    OUTPUT_ROOT,
    PASS_STATUS,
    POLICY_DECISIONS,
    R7_RUNTIME_PATHS,
    build_outputs,
    verify_hash_manifest_for,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainPush7LaneCExecutionReadinessAutonomyPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_outputs({"runner": "TEST_SETUP"})
        cls.decision = json.loads((OUTPUT_ROOT / "EXECUTION_READINESS_AUTONOMY_DECISION.json").read_text(encoding="utf-8"))
        cls.registry = json.loads((OUTPUT_ROOT / "EXECUTION_ADAPTER_REGISTRY.json").read_text(encoding="utf-8"))
        cls.requests = json.loads((OUTPUT_ROOT / "ADAPTER_PREFLIGHT_REQUESTS.json").read_text(encoding="utf-8"))
        cls.results = json.loads((OUTPUT_ROOT / "ADAPTER_PREFLIGHT_RESULTS.json").read_text(encoding="utf-8"))
        cls.autonomy = json.loads((OUTPUT_ROOT / "CONDITIONAL_AUTONOMY_PREFLIGHT_RUNS.json").read_text(encoding="utf-8"))
        cls.blocks = json.loads((OUTPUT_ROOT / "AUTONOMY_BLOCK_DECISIONS.json").read_text(encoding="utf-8"))
        cls.audit = json.loads((OUTPUT_ROOT / "EXECUTION_READINESS_AUDIT_EVENTS.json").read_text(encoding="utf-8"))

    def test_required_outputs_exist(self):
        required = [
            "EXECUTION_READINESS_AUTONOMY_DECISION.json",
            "EXECUTION_ADAPTER_REGISTRY_SCHEMA.json",
            "EXECUTION_ADAPTER_PREFLIGHT_SCHEMA.json",
            "AUTHORITY_LEVEL_4_5_BOUNDARY.md",
            "CONDITIONAL_AUTONOMY_POLICY_SCHEMA.json",
            "CONDITIONAL_AUTONOMY_PREFLIGHT_SCHEMA.json",
            "EXECUTION_ADAPTER_REGISTRY.json",
            "ADAPTER_PREFLIGHT_REQUESTS.json",
            "ADAPTER_PREFLIGHT_RESULTS.json",
            "CONDITIONAL_AUTONOMY_PREFLIGHT_RUNS.json",
            "AUTONOMY_BLOCK_DECISIONS.json",
            "EXECUTION_READINESS_AUDIT_EVENTS.json",
            "EXECUTION_READINESS_BOUNDARY_AND_NON_CLAIMS.md",
            "EXECUTION_READINESS_TEST_LOG.md",
            "EXECUTION_READINESS_HASH_MANIFEST.json",
        ]
        for name in required:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        self.assertEqual(PASS_STATUS, self.decision["status"])

    def test_closeout_and_final_status_exist(self):
        for name in [
            "EXECUTION_READINESS_AUTONOMY_CLOSEOUT_DECISION.json",
            "EXECUTION_READINESS_AUTONOMY_CLOSEOUT_SUMMARY.md",
            "EXECUTION_READINESS_AUTONOMY_CLOSEOUT_LIMITATIONS.md",
            "EXECUTION_READINESS_AUTONOMY_CLOSEOUT_NEXT_STEPS.md",
            "EXECUTION_READINESS_AUTONOMY_CLOSEOUT_HASH_MANIFEST.json",
        ]:
            self.assertTrue((CLOSEOUT_ROOT / name).exists(), name)
        for name in [
            "EXECUTION_READINESS_AUTONOMY_FINAL_STATUS_DECISION.json",
            "EXECUTION_READINESS_AUTONOMY_FINAL_STATUS_SUMMARY.md",
            "EXECUTION_READINESS_AUTONOMY_FINAL_STATUS_HASH_MANIFEST.json",
        ]:
            self.assertTrue((FINAL_ROOT / name).exists(), name)
        final = json.loads((FINAL_ROOT / "EXECUTION_READINESS_AUTONOMY_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))
        self.assertEqual(FINAL_STATUS, final["status"])

    def test_push6_and_approval_gates_pass(self):
        gate = self.decision["push6_gate"]
        approval = self.decision["approval_gate"]
        self.assertEqual("PASS", gate["status"])
        self.assertEqual("PASS", approval["status"])
        self.assertTrue(gate["plan_options_not_executed"])
        self.assertTrue(gate["schedule_options_not_executed"])
        self.assertTrue(gate["scenario_records_not_executed"])
        self.assertGreater(gate["authority_level_3_count"], 0)

    def test_adapter_registry_entries_validate(self):
        self.assertEqual("PASS", self.registry["status"])
        self.assertEqual(set(ALLOWED_ADAPTER_KINDS), {item["adapter_kind"] for item in self.registry["items"]})
        for entry in self.registry["items"]:
            self.assertTrue(entry["requires_approval"])
            self.assertTrue(entry["dry_run_only"])
            self.assertFalse(entry["execution_enabled"])
            self.assertFalse(entry["production_endpoint"])
            self.assertTrue(entry["evidence_refs"])
            self.assertTrue(entry["limitation_refs"])
            self.assertTrue(entry["trace_refs"])
            self.assertTrue(entry["check_report_ref"])
            self.assertTrue(entry["authority_envelope_ref"].startswith("authority:l3:"))
            self.assertTrue(entry["cannot_claim"])
            for capability in entry["capabilities"]:
                self.assertTrue(capability["dry_run_only"])
                self.assertEqual("not_executed", capability["execution_status"])

    def test_adapter_preflights_require_approval_and_never_execute(self):
        self.assertEqual(len(self.registry["items"]), len(self.requests["items"]))
        self.assertEqual(len(self.registry["items"]), len(self.results["items"]))
        decisions = set()
        forbidden_values = {"executed", "submitted", "dispatched", "controlled", "enforced", "certified"}
        for request in self.requests["items"]:
            self.assertTrue(request["approval_request_ref"].startswith("approval:request:"))
            self.assertTrue(request["dry_run_only"])
            self.assertEqual("not_executed", request["execution_status"])
        for result in self.results["items"]:
            decisions.add(result["policy_decision"])
            self.assertIn(result["policy_decision"], POLICY_DECISIONS)
            self.assertNotIn(result["policy_decision"], forbidden_values)
            self.assertTrue(result["approval_request_ref"].startswith("approval:request:"))
            self.assertEqual("not_executed", result["execution_status"])
            self.assertTrue(result["dry_run_only"])
            self.assertFalse(result["execution_enabled"])
            self.assertFalse(result["approval_bypass"])
            self.assertFalse(result["adapter_action_created"])
            self.assertFalse(result["external_system_called"])
            self.assertFalse(result["production_endpoint"])
            self.assertTrue(result["blocked_reasons"])
        self.assertIn("blocked_no_approval", decisions)
        self.assertIn("blocked_insufficient_authority", decisions)
        self.assertIn("blocked_live_endpoint_disabled", decisions)
        self.assertIn("blocked_policy", decisions)
        self.assertIn("dry_run_passed_not_executed", decisions)

    def test_authority_level_4_5_boundary_is_readiness_only(self):
        text = (OUTPUT_ROOT / "AUTHORITY_LEVEL_4_5_BOUNDARY.md").read_text(encoding="utf-8")
        self.assertIn("readiness", text.lower())
        self.assertIn("Current authority remains level 3", text)
        self.assertIn("Neither level creates an adapter call", text)

    def test_conditional_autonomy_preflight_is_blocked_only(self):
        self.assertEqual("PASS", self.autonomy["status"])
        self.assertEqual(1, len(self.autonomy["policies"]))
        policy = self.autonomy["policies"][0]
        self.assertFalse(policy["approval_bypass_allowed"])
        self.assertFalse(policy["recurring_monitor_enabled"])
        self.assertFalse(policy["action_authorization_enabled"])
        self.assertTrue(policy["dry_run_only"])
        self.assertFalse(policy["execution_enabled"])
        self.assertTrue(policy["block_by_default"])
        for run in self.autonomy["preflight_runs"]:
            self.assertEqual("blocked_preflight_only", run["decision"])
            self.assertEqual("not_executed", run["execution_status"])
            self.assertTrue(run["required_approval_ref"].startswith("approval:request:"))
            self.assertTrue(run["blocked_reasons"])
        for block in self.blocks["items"]:
            self.assertEqual("blocked_preflight_only", block["decision"])
            self.assertFalse(block["approval_bypass"])
            self.assertFalse(block["action_authorized"])
            self.assertFalse(block["adapter_action_created"])
            self.assertFalse(block["recurring_monitor_created"])
            self.assertEqual("not_executed", block["execution_status"])

    def test_policy_negative_tests_and_contract_flags_pass(self):
        for case in self.decision["policy_negative_tests"]:
            self.assertEqual("PASS", case["status"])
            self.assertEqual("not_executed", case["execution_status"])
        contract = self.decision["contract_check"]
        self.assertTrue(contract["lane_c_only"])
        self.assertTrue(contract["local_replay_only"])
        self.assertTrue(contract["no_adapter_execution"])
        self.assertTrue(contract["no_approval_bypass"])
        self.assertTrue(contract["no_conditional_autonomy_action"])
        self.assertTrue(contract["no_official_dispatch_control_enforcement_legal_claim"])
        self.assertTrue(contract["no_live_api_url_llm"])

    def test_no_positive_execution_or_live_endpoint_flags(self):
        blob = json.dumps(
            {
                "registry": self.registry,
                "requests": self.requests,
                "results": self.results,
                "autonomy": self.autonomy,
                "blocks": self.blocks,
                "audit": self.audit,
            },
            sort_keys=True,
        ).lower()
        forbidden_pairs = [
            '"execution_status": "executed"',
            '"execution_enabled": true',
            '"dry_run_only": false',
            '"production_endpoint": true',
            '"approval_bypass": true',
            '"adapter_action_created": true',
            '"external_system_called": true',
            '"action_authorized": true',
            '"recurring_monitor_created": true',
            '"recurring_monitor_enabled": true',
            '"action_authorization_enabled": true',
        ]
        for token in forbidden_pairs:
            self.assertNotIn(token, blob)
        self.assertIn("not_executed", blob)
        self.assertIn("blocked_preflight_only", blob)

    def test_audit_events_cover_registry_preflight_and_autonomy(self):
        event_types = {item["event_type"] for item in self.audit["items"]}
        self.assertIn("execution_adapter_registry_entry_recorded", event_types)
        self.assertIn("adapter_preflight_request_recorded", event_types)
        self.assertIn("adapter_preflight_result_recorded", event_types)
        self.assertIn("conditional_autonomy_preflight_blocked", event_types)
        self.assertIn("autonomy_block_decision_recorded", event_types)
        for event in self.audit["items"]:
            self.assertEqual("not_executed", event["execution_status"])
            self.assertTrue(event["subject_ref"])

    def test_hash_manifests_verify_and_protected_diffs_clean(self):
        for root, name in [
            (OUTPUT_ROOT, "EXECUTION_READINESS_HASH_MANIFEST.json"),
            (CLOSEOUT_ROOT, "EXECUTION_READINESS_AUTONOMY_CLOSEOUT_HASH_MANIFEST.json"),
            (FINAL_ROOT, "EXECUTION_READINESS_AUTONOMY_FINAL_STATUS_HASH_MANIFEST.json"),
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

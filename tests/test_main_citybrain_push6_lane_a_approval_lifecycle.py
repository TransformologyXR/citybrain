import json
import subprocess
import unittest
from pathlib import Path

from packages.approval_lifecycle import (
    FORBIDDEN_REQUEST_STATUSES,
    build_approval_request,
)
from scripts.run_main_citybrain_push6_lane_a_approval_lifecycle import (
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


class MainCityBrainPush6LaneAApprovalLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_outputs({"runner": "TEST_SETUP"})
        cls.decision = json.loads((OUTPUT_ROOT / "APPROVAL_LIFECYCLE_DECISION.json").read_text(encoding="utf-8"))
        cls.fixtures = json.loads((OUTPUT_ROOT / "APPROVAL_LIFECYCLE_FIXTURES.json").read_text(encoding="utf-8"))
        cls.audit = json.loads((OUTPUT_ROOT / "APPROVAL_AUDIT_LOG_FIXTURES.json").read_text(encoding="utf-8"))
        cls.agent_runs = json.loads((OUTPUT_ROOT / "APPROVAL_LIFECYCLE_AGENT_RUNS.json").read_text(encoding="utf-8"))
        cls.closeout = json.loads((CLOSEOUT_ROOT / "APPROVAL_LIFECYCLE_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        cls.final = json.loads((FINAL_ROOT / "APPROVAL_LIFECYCLE_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))

    def test_required_outputs_exist(self):
        required = [
            "APPROVAL_LIFECYCLE_DECISION.json",
            "APPROVAL_CONTRACT_OVERVIEW.md",
            "APPROVAL_REQUEST_SCHEMA.json",
            "APPROVAL_DECISION_SCHEMA.json",
            "APPROVAL_LIFECYCLE_STATE_SCHEMA.json",
            "APPROVAL_AUDIT_EVENT_SCHEMA.json",
            "AUTHORITY_LEVEL_3_SEMANTICS.md",
            "APPROVAL_POLICY_FIXTURES.json",
            "APPROVAL_LIFECYCLE_FIXTURES.json",
            "APPROVAL_AUDIT_LOG_FIXTURES.json",
            "APPROVAL_LIFECYCLE_AGENT_RUNS.json",
            "APPROVAL_BOUNDARY_AND_NON_CLAIMS.md",
            "APPROVAL_TEST_LOG.md",
            "APPROVAL_HASH_MANIFEST.json",
        ]
        for name in required:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        self.assertEqual(PASS_STATUS, self.decision["status"])

    def test_closeout_and_final_status_exist(self):
        for name in [
            "APPROVAL_LIFECYCLE_CLOSEOUT_DECISION.json",
            "APPROVAL_LIFECYCLE_CLOSEOUT_SUMMARY.md",
            "APPROVAL_LIFECYCLE_CLOSEOUT_LIMITATIONS.md",
            "APPROVAL_LIFECYCLE_CLOSEOUT_NEXT_STEPS.md",
            "APPROVAL_LIFECYCLE_CLOSEOUT_HASH_MANIFEST.json",
        ]:
            self.assertTrue((CLOSEOUT_ROOT / name).exists(), name)
        for name in [
            "APPROVAL_LIFECYCLE_FINAL_STATUS_DECISION.json",
            "APPROVAL_LIFECYCLE_FINAL_STATUS_SUMMARY.md",
            "APPROVAL_LIFECYCLE_FINAL_STATUS_HASH_MANIFEST.json",
        ]:
            self.assertTrue((FINAL_ROOT / name).exists(), name)
        self.assertEqual(CLOSEOUT_STATUS, self.closeout["status"])
        self.assertEqual(FINAL_STATUS, self.final["status"])

    def test_approval_requests_and_decisions_are_valid(self):
        requests = self.fixtures["approval_requests"]
        decisions = self.fixtures["approval_decisions"]
        self.assertGreaterEqual(len(requests), 3)
        self.assertGreaterEqual(len(decisions), 3)
        for request in requests:
            self.assertEqual(3, request["authority_level_requested"])
            self.assertTrue(request["check_report_ref"])
            self.assertTrue(request["authority_envelope_ref"])
            self.assertTrue(request["evidence_refs"])
            self.assertTrue(request["not_executed"])
        for decision in decisions:
            self.assertTrue(decision["approval_request_ref"])
            self.assertTrue(decision["check_report_ref"])
            self.assertTrue(decision["authority_envelope_ref"])
            self.assertTrue(decision["not_executed"])
            self.assertFalse(decision["execution_created"])
            self.assertFalse(decision["official_submission_created"])

    def test_authority_level_3_is_proposal_governance_only(self):
        for stamp in self.fixtures["authority_level_3_envelopes"]:
            self.assertEqual(3, stamp["authority_level"])
            self.assertTrue(stamp["proposal_governance_exists"])
            self.assertTrue(stamp["local_approval_workflow_exists"])
            self.assertFalse(stamp["execution_authority"])
            self.assertFalse(stamp["dispatch_authority"])
            self.assertFalse(stamp["control_authority"])
            self.assertFalse(stamp["official_submission_authority"])
            self.assertFalse(stamp["legal_certified_authority"])
            self.assertFalse(stamp["production_authority"])

    def test_approved_local_does_not_mean_executed_or_submitted(self):
        approved = [item for item in self.fixtures["approval_lifecycle_states"] if item["approved_local"]]
        self.assertTrue(approved)
        for state in approved:
            self.assertFalse(state["executed"])
            self.assertFalse(state["officially_submitted"])
            self.assertFalse(state["dispatch_control_enforcement_executed"])
            self.assertFalse(state["legal_certified_finding_created"])
            self.assertTrue(state["not_executed"])

    def test_forbidden_statuses_are_rejected(self):
        request = self.fixtures["approval_requests"][0]
        for status in FORBIDDEN_REQUEST_STATUSES:
            with self.assertRaises(ValueError):
                build_approval_request(
                    subject_ref=request["subject_ref"],
                    subject_type=request["subject_type"],
                    proposal_ref=f"{request['proposal_ref']}:{status}",
                    requested_by_ref=request["requested_by_ref"],
                    status=status,
                    check_report_ref=request["check_report_ref"],
                    authority_envelope_ref=request["authority_envelope_ref"],
                    evidence_refs=request["evidence_refs"],
                    limitation_refs=request["limitation_refs"],
                    trace_refs=request["trace_refs"],
                )

    def test_check_authority_and_audit_refs_are_preserved(self):
        for item in self.audit["items"]:
            self.assertTrue(item["evidence_refs"])
            self.assertTrue(item["limitation_refs"])
            self.assertTrue(item["trace_refs"])
            self.assertTrue(item["check_report_ref"])
            self.assertTrue(item["authority_envelope_ref"])
            self.assertTrue(item["not_executed"])
            self.assertFalse(item["execution_created"])
            self.assertFalse(item["official_submission_created"])

    def test_agent_runs_are_local_replay_only(self):
        for run in self.agent_runs["items"]:
            self.assertFalse(run["live_llm_used"])
            self.assertFalse(run["production_api_used"])
            self.assertFalse(run["url_fetch_used"])
            self.assertFalse(run["execution_created"])
            self.assertFalse(run["official_submission_created"])
            self.assertTrue(run["not_executed"])

    def test_hash_manifests_and_protected_diffs(self):
        for root, name in [
            (OUTPUT_ROOT, "APPROVAL_HASH_MANIFEST.json"),
            (CLOSEOUT_ROOT, "APPROVAL_LIFECYCLE_CLOSEOUT_HASH_MANIFEST.json"),
            (FINAL_ROOT, "APPROVAL_LIFECYCLE_FINAL_STATUS_HASH_MANIFEST.json"),
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

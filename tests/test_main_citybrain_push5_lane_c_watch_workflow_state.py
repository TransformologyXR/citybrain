import json
import subprocess
import unittest
from pathlib import Path

from scripts.run_main_citybrain_push5_lane_c_watch_workflow_state import (
    ASK_CONTRACT_PATHS,
    CLOSEOUT_ROOT,
    CLOSEOUT_STATUS,
    FINAL_ROOT,
    FINAL_STATUS,
    OUTPUT_ROOT,
    PASS_STATUS,
    R7_RUNTIME_PATHS,
    WORKFLOW_STATES,
    build_outputs,
    verify_hash_manifest_for,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainPush5LaneCWatchWorkflowStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_outputs({"runner": "TEST_SETUP"})
        cls.decision = json.loads((OUTPUT_ROOT / "WATCH_WORKFLOW_STATE_DECISION.json").read_text(encoding="utf-8"))
        cls.families = json.loads((OUTPUT_ROOT / "WATCH_QUERY_EXPANSION_FAMILIES.json").read_text(encoding="utf-8"))
        cls.watch_items = json.loads((OUTPUT_ROOT / "WATCH_EXPANDED_ITEMS.json").read_text(encoding="utf-8"))
        cls.contract = json.loads((OUTPUT_ROOT / "WORKFLOW_STATE_CONTRACT.json").read_text(encoding="utf-8"))
        cls.workflow_events = json.loads((OUTPUT_ROOT / "WORKFLOW_STATE_EVENTS.json").read_text(encoding="utf-8"))
        cls.hap = json.loads((OUTPUT_ROOT / "HOLD_ABSTAIN_PROPOSE_FIXTURES.json").read_text(encoding="utf-8"))
        cls.compatibility = json.loads((OUTPUT_ROOT / "WORKFLOW_APP_ROUTE_COMPATIBILITY.json").read_text(encoding="utf-8"))
        cls.llm_hook = json.loads((OUTPUT_ROOT / "OFFLINE_LLM_PROPOSAL_HOOK_FIXTURES.json").read_text(encoding="utf-8"))

    def test_required_outputs_exist(self):
        required = [
            "WATCH_WORKFLOW_STATE_DECISION.json",
            "WATCH_QUERY_EXPANSION_FAMILIES.json",
            "WATCH_EXPANDED_ITEMS.json",
            "WORKFLOW_STATE_CONTRACT.json",
            "WORKFLOW_STATE_EVENTS.json",
            "HOLD_ABSTAIN_PROPOSE_FIXTURES.json",
            "WORKFLOW_APP_ROUTE_COMPATIBILITY.json",
            "WATCH_WORKFLOW_BOUNDARY_AND_NON_CLAIMS.md",
            "WATCH_WORKFLOW_TEST_LOG.md",
            "WATCH_WORKFLOW_HASH_MANIFEST.json",
            "OFFLINE_LLM_PROPOSAL_HOOK_PREFLIGHT.md",
            "OFFLINE_LLM_PROPOSAL_HOOK_FIXTURES.json",
        ]
        for name in required:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        self.assertEqual(PASS_STATUS, self.decision["status"])

    def test_closeout_and_final_status_exist(self):
        for name in [
            "WATCH_WORKFLOW_STATE_CLOSEOUT_DECISION.json",
            "WATCH_WORKFLOW_STATE_CLOSEOUT_SUMMARY.md",
            "WATCH_WORKFLOW_STATE_CLOSEOUT_LIMITATIONS.md",
            "WATCH_WORKFLOW_STATE_CLOSEOUT_NEXT_STEPS.md",
            "WATCH_WORKFLOW_STATE_CLOSEOUT_HASH_MANIFEST.json",
        ]:
            self.assertTrue((CLOSEOUT_ROOT / name).exists(), name)
        for name in [
            "WATCH_WORKFLOW_STATE_FINAL_STATUS_DECISION.json",
            "WATCH_WORKFLOW_STATE_FINAL_STATUS_SUMMARY.md",
            "WATCH_WORKFLOW_STATE_FINAL_STATUS_HASH_MANIFEST.json",
        ]:
            self.assertTrue((FINAL_ROOT / name).exists(), name)
        closeout = json.loads((CLOSEOUT_ROOT / "WATCH_WORKFLOW_STATE_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        final = json.loads((FINAL_ROOT / "WATCH_WORKFLOW_STATE_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))
        self.assertEqual(CLOSEOUT_STATUS, closeout["status"])
        self.assertEqual(FINAL_STATUS, final["status"])

    def test_watch_families_emit_review_prompts_only(self):
        expected = {
            "new_contradiction_pairs",
            "source_freshness_risk",
            "unresolved_attribute_conflicts",
            "high_value_low_authority_items",
            "new_diff_items",
            "recall_match_review_prompts",
            "workflow_items_needing_disposition",
        }
        families = {item["watch_family"] for item in self.families["families"]}
        self.assertEqual(expected, families)
        self.assertEqual(7, self.families["family_count"])
        self.assertTrue(self.families["review_prompt_only"])
        for item in self.watch_items["items"]:
            self.assertEqual("review_prompt", item["watch_item_kind"])
            self.assertTrue(item["review_prompt_only"])
            self.assertTrue(item["review_required"])
            self.assertEqual("review_prompt_only", item["authority_level"])
            self.assertEqual("not_executed", item["execution_status"])

    def test_check_reports_and_authority_envelopes_preserved(self):
        for item in self.watch_items["items"]:
            self.assertTrue(item["check_report_ref"], item["watch_item_id"])
            self.assertTrue(item["authority_envelope_ref"], item["watch_item_id"])
            self.assertTrue(item["evidence_refs"], item["watch_item_id"])
            self.assertTrue(item["trace_refs"], item["watch_item_id"])
            self.assertTrue(item["target_ref"], item["watch_item_id"])

    def test_workflow_state_contract_supports_required_states(self):
        self.assertEqual(WORKFLOW_STATES, self.contract["workflow_states"])
        for state in ["held", "abstained", "proposed_for_review", "needs_more", "dismissed", "confirmed_local", "closed_local"]:
            self.assertIn(state, self.contract["workflow_states"])
        self.assertEqual("not_executed", self.contract["execution_status"]["const"])
        self.assertIn("proposed_for_review", self.contract["transition_policy"]["open"])

    def test_workflow_state_transitions_preserve_not_executed(self):
        states = {event["new_state"] for event in self.workflow_events["items"]}
        self.assertTrue({"held", "abstained", "proposed_for_review", "needs_more", "dismissed", "confirmed_local", "closed_local"}.issubset(states))
        for event in self.workflow_events["items"]:
            self.assertIn(event["previous_state"], WORKFLOW_STATES)
            self.assertIn(event["new_state"], WORKFLOW_STATES)
            self.assertEqual("not_executed", event["execution_status"])
            self.assertEqual("not_official", event["official_status"])
            self.assertTrue(event["check_report_ref"])
            self.assertTrue(event["authority_envelope_ref"])
        self.assertTrue(self.workflow_events["all_not_executed"])

    def test_hold_abstain_propose_do_not_execute(self):
        states = {event["new_state"] for event in self.hap["items"]}
        self.assertEqual({"held", "abstained", "proposed_for_review"}, states)
        self.assertTrue(self.hap["all_preserve_not_executed"])
        self.assertTrue(self.hap["proposed_for_review_is_not_action_proposal"])
        for event in self.hap["items"]:
            self.assertEqual("not_executed", event["execution_status"])
            self.assertFalse(event["proposed_for_review_is_action_proposal"])

    def test_workflow_events_target_valid_review_items(self):
        target_refs = {item["target_ref"] for item in self.watch_items["items"]}
        watch_refs = {item["watch_item_id"] for item in self.watch_items["items"]}
        for event in self.workflow_events["items"]:
            self.assertIn(event["target_ref"], target_refs)
            self.assertIn(event["target_watch_item_ref"], watch_refs)

    def test_app_route_compatibility_remains_review_only(self):
        self.assertEqual("PASS", self.compatibility["status"])
        self.assertTrue(self.compatibility["all_not_executed"])
        for row in self.compatibility["items"]:
            self.assertTrue(row["app_route_compatible"])
            self.assertEqual("not_executed", row["execution_status"])
            self.assertTrue(row["reviewer_operator_only"])
            if row["app_route_disposition"] is not None:
                self.assertIn(row["app_route_disposition"], self.compatibility["allowed_app_route_dispositions"])

    def test_no_official_action_dispatch_control_enforcement(self):
        forbidden = " ".join(
            json.dumps(item, sort_keys=True).lower()
            for item in self.watch_items["items"] + self.workflow_events["items"]
        )
        self.assertNotIn('"execution_status": "executed"', forbidden)
        self.assertNotIn("dispatch_authorized", forbidden)
        self.assertNotIn("official_submission_created", forbidden)
        self.assertIn("not_executed", forbidden)

    def test_optional_llm_hook_is_offline_fixture_only(self):
        self.assertTrue((OUTPUT_ROOT / "OFFLINE_LLM_PROPOSAL_HOOK_PREFLIGHT.md").exists())
        self.assertTrue(self.llm_hook["offline_fixture_only"])
        self.assertFalse(self.llm_hook["live_llm_call"])
        self.assertFalse(self.llm_hook["retrieval_used"])
        self.assertFalse(self.llm_hook["authority_created"])
        self.assertFalse(self.llm_hook["claimability_decision_created"])
        for item in self.llm_hook["items"]:
            self.assertEqual("offline_fixture_only", item["mode"])
            self.assertFalse(item["live_llm_call"])
            self.assertEqual("not_executed", item["execution_status"])

    def test_hash_manifests_verify_and_protected_diffs_clean(self):
        for root, name in [
            (OUTPUT_ROOT, "WATCH_WORKFLOW_HASH_MANIFEST.json"),
            (CLOSEOUT_ROOT, "WATCH_WORKFLOW_STATE_CLOSEOUT_HASH_MANIFEST.json"),
            (FINAL_ROOT, "WATCH_WORKFLOW_STATE_FINAL_STATUS_HASH_MANIFEST.json"),
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

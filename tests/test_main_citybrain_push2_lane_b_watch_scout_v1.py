import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.run_main_citybrain_push2_lane_b_watch_scout_v1 import (
    CLOSEOUT_ROOT,
    FINAL_STATUS_ROOT,
    OUTPUT_ROOT,
    PASS_STATUS,
    build_boundary_audit,
    build_check_authority_report,
    build_watch_items,
    load_event_runtime_state,
    verify_hash_manifest,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainPush2LaneBWatchScoutV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(
            [sys.executable, "scripts/run_main_citybrain_push2_lane_b_watch_scout_v1.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        cls.watch_items_packet = json.loads((OUTPUT_ROOT / "WATCH_ITEMS.json").read_text(encoding="utf-8"))
        cls.items = cls.watch_items_packet["items"]
        cls.query_families = json.loads((OUTPUT_ROOT / "WATCH_SCOUT_QUERY_FAMILIES.json").read_text(encoding="utf-8"))
        cls.check_authority = json.loads((OUTPUT_ROOT / "WATCH_SCOUT_CHECK_AUTHORITY_REPORT.json").read_text(encoding="utf-8"))
        cls.boundary = json.loads((OUTPUT_ROOT / "WATCH_SCOUT_BOUNDARY_AUDIT.json").read_text(encoding="utf-8"))
        cls.decision = json.loads((OUTPUT_ROOT / "WATCH_SCOUT_V1_DECISION.json").read_text(encoding="utf-8"))
        cls.closeout = json.loads((CLOSEOUT_ROOT / "WATCH_SCOUT_V1_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        cls.final_status = json.loads((FINAL_STATUS_ROOT / "WATCH_SCOUT_V1_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))

    def test_required_outputs_exist(self):
        required = [
            "WATCH_SCOUT_V1_DECISION.json",
            "WATCH_SCOUT_QUERY_FAMILIES.json",
            "WATCH_ITEMS.json",
            "WATCH_SCOUT_CHECK_AUTHORITY_REPORT.json",
            "WATCH_SCOUT_BOUNDARY_AUDIT.json",
            "WATCH_SCOUT_TEST_LOG.md",
            "WATCH_SCOUT_HASH_MANIFEST.json",
        ]
        for name in required:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        self.assertEqual(PASS_STATUS, self.decision["status"])

    def test_required_closeout_and_final_status_outputs_exist(self):
        closeout_required = [
            "WATCH_SCOUT_V1_CLOSEOUT_DECISION.json",
            "WATCH_SCOUT_V1_CLOSEOUT_SUMMARY.md",
            "WATCH_SCOUT_V1_CLOSEOUT_LIMITATIONS.md",
            "WATCH_SCOUT_V1_CLOSEOUT_HASH_MANIFEST.json",
        ]
        final_required = [
            "WATCH_SCOUT_V1_FINAL_STATUS_DECISION.json",
            "WATCH_SCOUT_V1_FINAL_STATUS_SUMMARY.md",
            "WATCH_SCOUT_V1_FINAL_STATUS_HASH_MANIFEST.json",
        ]
        for name in closeout_required:
            self.assertTrue((CLOSEOUT_ROOT / name).exists(), name)
        for name in final_required:
            self.assertTrue((FINAL_STATUS_ROOT / name).exists(), name)
        self.assertEqual(PASS_STATUS, self.closeout["status"])
        self.assertEqual(PASS_STATUS, self.final_status["status"])
        self.assertTrue(self.closeout["infra_canonical_integration_owned_elsewhere"])
        self.assertEqual("codex/push2-lane-b-watch-scout-v1", self.final_status["branch"])

    def test_three_to_four_families_emit_watch_items_and_family_two_runs_last(self):
        families = {item["watch_family"] for item in self.items}
        self.assertGreaterEqual(len(families), 3)
        self.assertLessEqual(len(families), 4)
        self.assertEqual(4, self.query_families["family_count"])
        self.assertEqual(len(families), self.query_families["emitting_family_count"])
        family2 = [row for row in self.query_families["families"] if row["watch_family"] == "quarantined_or_boundary_blocked_items"][0]
        self.assertEqual(4, family2["execution_order"])
        self.assertTrue(family2["runs_last"])

    def test_watch_items_carry_evidence_limitations_trace_check_and_authority_refs(self):
        for item in self.items:
            for field in [
                "watch_item_id",
                "watch_family",
                "event_refs",
                "candidate_observation_refs",
                "evidence_refs",
                "limitation_refs",
                "trace_refs",
                "check_report_ref",
                "authority_envelope_ref",
                "authority_level",
                "review_required",
                "official_status",
                "not_executed",
                "safe_next_looks",
                "cannot_claim",
            ]:
                self.assertIn(field, item)
            self.assertTrue(item["evidence_refs"])
            self.assertTrue(item["limitation_refs"])
            self.assertTrue(item["trace_refs"])
            self.assertTrue(item["check_report_ref"])
            self.assertTrue(item["authority_envelope_ref"])

    def test_check_reports_and_authority_envelopes_are_linked(self):
        check_refs = {report["check_report_ref"] for report in self.check_authority["check_reports"]}
        authority_refs = {envelope["authority_envelope_ref"] for envelope in self.check_authority["authority_envelopes"]}
        self.assertEqual(len(self.items), len(check_refs))
        self.assertEqual(len(self.items), len(authority_refs))
        self.assertEqual("PASS", self.check_authority["status"])
        for item in self.items:
            self.assertIn(item["check_report_ref"], check_refs)
            self.assertIn(item["authority_envelope_ref"], authority_refs)
            self.assertEqual("review_prompt_only", item["authority_level"])

    def test_watch_items_are_review_prompts_only(self):
        for item in self.items:
            self.assertEqual("review_prompt", item["watch_item_kind"])
            self.assertTrue(item["review_required"])
            self.assertEqual("not_official", item["official_status"])
            self.assertTrue(item["not_finding"])
            self.assertTrue(item["not_action"])
            self.assertTrue(item["not_executed"])
        self.assertEqual("PASS", self.boundary["status"])
        self.assertTrue(self.boundary["watch_items_are_review_prompts_only"])
        self.assertTrue(self.boundary["no_official_findings_or_actions"])

    def test_no_official_findings_actions_or_execution_refs(self):
        payload = json.dumps(
            {
                "items": self.items,
                "check_authority": self.check_authority,
                "boundary": self.boundary,
            },
            sort_keys=True,
        ).lower()
        forbidden = [
            '"official_status": "official"',
            '"execution_status": "executed"',
            '"submission_status": "submitted"',
            '"official_case_id": "',
            '"external_submission_ref": "',
            '"dispatch_ref": "',
            '"control_ref": "',
            '"enforcement_ref": "',
            '"official_finding": true',
            '"official_action": true',
            '"legal_violation": true',
            '"certified": true',
        ]
        for token in forbidden:
            self.assertNotIn(token, payload)

    def test_family_two_uses_event_fabric_quarantine_when_available(self):
        self.assertEqual("event_fabric_quarantine", self.query_families["family2_source"])
        family2_items = [item for item in self.items if item["watch_family"] == "quarantined_or_boundary_blocked_items"]
        self.assertGreaterEqual(len(family2_items), 1)
        self.assertTrue(all("quarantined" in item["source_event_type"] for item in family2_items))

    def test_family_two_boundary_failed_fallback_path_is_available(self):
        state = load_event_runtime_state()
        fallback_state = copy.deepcopy(state)
        fallback_state["materialized"]["quarantined_observations"] = []
        fallback_reports = [
            {
                "check_report_id": "lane-a:check:boundary-failed-001",
                "status": "boundary_failed",
                "candidate_observation_refs": ["candidate:test:boundary-failed"],
                "evidence_refs": ["evidence:test:boundary-failed"],
                "limitation_refs": ["limitation:test:boundary-failed"],
                "trace_refs": ["trace:test:boundary-failed"],
            }
        ]
        items, meta = build_watch_items(fallback_state, fallback_reports)
        family2_items = [item for item in items if item["watch_family"] == "quarantined_or_boundary_blocked_items"]
        self.assertEqual("lane_a_boundary_failed_check_reports", meta["family2_source"])
        self.assertEqual("boundary_test_failed_packets", meta["family2_effective_family"])
        self.assertEqual(1, len(family2_items))
        self.assertIn("watch:fallback:lane-a:check:boundary-failed-001", family2_items[0]["event_refs"])

    def test_boundary_audit_fails_if_check_or_authority_is_missing(self):
        damaged = copy.deepcopy(self.items)
        damaged[0]["check_report_ref"] = "missing:check-report"
        check_authority = build_check_authority_report(self.items)
        audit = build_boundary_audit(damaged, check_authority, {"family2_source": "event_fabric_quarantine", "family2_runs_last": True})
        self.assertEqual("FAIL", audit["status"])
        self.assertTrue(any("missing_check_report" in failure for failure in audit["failures"]))

    def test_no_live_retrieval_production_api_url_fetch_or_llm_call_occurs(self):
        source = (ROOT / "scripts" / "run_main_citybrain_push2_lane_b_watch_scout_v1.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("chat.completions", source)
        self.assertNotIn("fetch(", source)

    def test_hash_manifest_verifies(self):
        reports = [
            verify_hash_manifest(OUTPUT_ROOT),
            verify_hash_manifest(CLOSEOUT_ROOT, "WATCH_SCOUT_V1_CLOSEOUT_HASH_MANIFEST.json"),
            verify_hash_manifest(FINAL_STATUS_ROOT, "WATCH_SCOUT_V1_FINAL_STATUS_HASH_MANIFEST.json"),
        ]
        for report in reports:
            self.assertEqual("PASS", report["status"], report)
            self.assertEqual(report["declared"], report["verified"])
        self.assertGreaterEqual(reports[0]["declared"], 6)
        self.assertGreaterEqual(reports[1]["declared"], 3)
        self.assertGreaterEqual(reports[2]["declared"], 2)


if __name__ == "__main__":
    unittest.main()

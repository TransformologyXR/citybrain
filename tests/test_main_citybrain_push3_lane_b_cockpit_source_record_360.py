import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.run_main_citybrain_push3_lane_b_cockpit_source_record_360 import (
    CLOSEOUT_ROOT,
    FINAL_STATUS_ROOT,
    OUTPUT_ROOT,
    PASS_STATUS,
    verify_hash_manifest,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainPush3LaneBCockpitSourceRecord360Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(
            [sys.executable, "scripts/run_main_citybrain_push3_lane_b_cockpit_source_record_360.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        cls.decision = json.loads((OUTPUT_ROOT / "COCKPIT_SOURCE_RECORD_360_DECISION.json").read_text(encoding="utf-8"))
        cls.workspace_packet = json.loads((OUTPUT_ROOT / "SELECTED_ITEM_WORKSPACE_FIXTURES.json").read_text(encoding="utf-8"))
        cls.workspace = cls.workspace_packet["items"][0]
        cls.index = json.loads((OUTPUT_ROOT / "SOURCE_RECORD_360_INDEX.json").read_text(encoding="utf-8"))
        cls.view_model = json.loads((OUTPUT_ROOT / "SOURCE_RECORD_360_VIEW_MODEL.json").read_text(encoding="utf-8"))
        cls.coverage = json.loads((OUTPUT_ROOT / "COCKPIT_CHECK_AUTHORITY_COVERAGE.json").read_text(encoding="utf-8"))
        cls.closeout = json.loads((CLOSEOUT_ROOT / "COCKPIT_SOURCE_RECORD_360_CLOSEOUT_DECISION.json").read_text(encoding="utf-8"))
        cls.final_status = json.loads((FINAL_STATUS_ROOT / "COCKPIT_SOURCE_RECORD_360_FINAL_STATUS_DECISION.json").read_text(encoding="utf-8"))

    def test_required_artifacts_exist(self):
        required = [
            "COCKPIT_SOURCE_RECORD_360_DECISION.json",
            "SELECTED_ITEM_WORKSPACE_CONTRACT.json",
            "SELECTED_ITEM_WORKSPACE_FIXTURES.json",
            "SOURCE_RECORD_360_INDEX.json",
            "SOURCE_RECORD_360_VIEW_MODEL.json",
            "COCKPIT_LOCAL_SURFACE_STATIC.html",
            "COCKPIT_LOCAL_OPEN_INDEX.md",
            "COCKPIT_CHECK_AUTHORITY_COVERAGE.json",
            "COCKPIT_BOUNDARY_AND_NON_CLAIMS.md",
            "COCKPIT_TEST_LOG.md",
            "COCKPIT_HASH_MANIFEST.json",
        ]
        for name in required:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        self.assertEqual(PASS_STATUS, self.decision["status"])

    def test_closeout_and_final_status_exist(self):
        for name in [
            "COCKPIT_SOURCE_RECORD_360_CLOSEOUT_DECISION.json",
            "COCKPIT_SOURCE_RECORD_360_CLOSEOUT_SUMMARY.md",
            "COCKPIT_SOURCE_RECORD_360_CLOSEOUT_LIMITATIONS.md",
            "COCKPIT_SOURCE_RECORD_360_CLOSEOUT_NEXT_STEPS.md",
            "COCKPIT_SOURCE_RECORD_360_CLOSEOUT_HASH_MANIFEST.json",
        ]:
            self.assertTrue((CLOSEOUT_ROOT / name).exists(), name)
        for name in [
            "COCKPIT_SOURCE_RECORD_360_FINAL_STATUS_DECISION.json",
            "COCKPIT_SOURCE_RECORD_360_FINAL_STATUS_SUMMARY.md",
            "COCKPIT_SOURCE_RECORD_360_FINAL_STATUS_HASH_MANIFEST.json",
        ]:
            self.assertTrue((FINAL_STATUS_ROOT / name).exists(), name)
        self.assertEqual(PASS_STATUS, self.closeout["status"])
        self.assertEqual(PASS_STATUS, self.final_status["status"])

    def test_selected_item_workspace_has_required_refs(self):
        for field in [
            "selected_item_id",
            "selected_item_label",
            "selected_item_type",
            "source_record_refs",
            "candidate_observation_refs",
            "event_refs",
            "watch_item_refs",
            "check_report_refs",
            "authority_envelope_refs",
            "evidence_refs",
            "limitation_refs",
            "trace_refs",
            "disposition_event_refs",
            "spatial_overlay_refs",
            "conflict_summary",
            "freshness_summary",
            "cannot_claim",
            "not_executed",
            "safe_next_looks",
        ]:
            self.assertIn(field, self.workspace)
        self.assertTrue(self.workspace["candidate_observation_refs"])
        self.assertTrue(self.workspace["watch_item_refs"])
        self.assertTrue(self.workspace["check_report_refs"])
        self.assertTrue(self.workspace["authority_envelope_refs"])
        self.assertTrue(self.workspace["disposition_event_refs"])

    def test_source_record_360_fixture_has_freshness_and_boundaries(self):
        self.assertGreaterEqual(self.index["source_record_count"], 1)
        for row in self.view_model["source_record_360"]:
            for field in [
                "source_class",
                "source_id",
                "source_label",
                "record_type",
                "record_timestamp",
                "freshness_status",
                "authority_level",
                "evidence_refs",
                "trace_refs",
                "limitations",
                "review_state",
                "linked_event_refs",
                "linked_watch_item_refs",
                "linked_candidate_observation_refs",
            ]:
                self.assertIn(field, row)
            self.assertFalse(row["official_truth_claim"])

    def test_coverage_proves_required_visibility(self):
        checks = self.coverage["checks"]
        self.assertEqual("PASS", self.coverage["status"])
        self.assertTrue(checks["selected_item_has_source_record_360"])
        self.assertTrue(checks["candidate_observations_visible"])
        self.assertTrue(checks["watch_items_visible"])
        self.assertTrue(checks["check_reports_visible"])
        self.assertTrue(checks["authority_envelopes_visible"])
        self.assertTrue(checks["evidence_limit_trace_visible"])
        self.assertTrue(checks["dispositions_visible"])
        self.assertTrue(checks["source_freshness_visible"])
        self.assertTrue(checks["cannot_claim_visible"])
        self.assertTrue(checks["no_official_action_affordance"])
        self.assertTrue(checks["no_live_api"])

    def test_static_surface_is_local_and_contains_no_live_api(self):
        html = (OUTPUT_ROOT / "COCKPIT_LOCAL_SURFACE_STATIC.html").read_text(encoding="utf-8").lower()
        self.assertIn("source-record 360", html)
        self.assertIn("cannot claim", html)
        self.assertNotIn("fetch(", html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("<form", html)

    def test_no_live_retrieval_url_api_or_llm_in_source(self):
        source = (ROOT / "scripts" / "run_main_citybrain_push3_lane_b_cockpit_source_record_360.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("chat.completions", source)
        self.assertNotIn("fetch(", source)

    def test_hash_manifests_verify(self):
        reports = [
            verify_hash_manifest(OUTPUT_ROOT, "COCKPIT_HASH_MANIFEST.json"),
            verify_hash_manifest(CLOSEOUT_ROOT, "COCKPIT_SOURCE_RECORD_360_CLOSEOUT_HASH_MANIFEST.json"),
            verify_hash_manifest(FINAL_STATUS_ROOT, "COCKPIT_SOURCE_RECORD_360_FINAL_STATUS_HASH_MANIFEST.json"),
        ]
        for report in reports:
            self.assertEqual("PASS", report["status"], report)
            self.assertEqual(report["declared"], report["verified"])


if __name__ == "__main__":
    unittest.main()

import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.run_main_citybrain_r7d_webui_kit_event_state_smoke import (
    OUTPUT_ROOT,
    boundary_audit,
    build_kit_smoke_export,
    build_parity_report,
    build_webui_smoke_export,
    load_r7c_outputs,
    verify_hash_manifest,
    write_usda,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainR7DWebUIKitEventStateSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(
            [sys.executable, "scripts\\run_main_citybrain_r7d_webui_kit_event_state_smoke.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        cls.state = load_r7c_outputs()
        cls.webui_items = build_webui_smoke_export(cls.state)
        cls.kit_items = build_kit_smoke_export(cls.state)
        cls.parity = build_parity_report(cls.webui_items, cls.kit_items)
        cls.usda_text = write_usda(cls.kit_items)
        cls.audit = boundary_audit(cls.webui_items, cls.kit_items, cls.parity, cls.usda_text)

    def test_r7c_webui_query_context_export_loads_or_fallback_documented(self):
        self.assertFalse(self.state["fallback_used"])
        self.assertEqual(8, len(self.state["webui_context"]))

    def test_r7c_kit_query_context_export_loads_or_fallback_documented(self):
        self.assertFalse(self.state["fallback_used"])
        self.assertEqual(8, len(self.state["kit_context"]))

    def test_webui_smoke_export_contains_required_review_safe_fields(self):
        required = {
            "query_case_id",
            "query_result_id",
            "event_id",
            "event_refs",
            "candidate_observation_refs",
            "candidate_only",
            "review_required",
            "official_status",
            "submission_status",
            "execution_status",
            "cannot_claim",
            "not_executed",
            "evidence_refs",
            "limitation_refs",
            "trace_refs",
            "display_sections",
        }
        self.assertEqual(8, len(self.webui_items))
        for item in self.webui_items:
            self.assertTrue(required.issubset(item))
            self.assertTrue(item["display_sections"])
            self.assertTrue(item["not_executed"])

    def test_kit_smoke_export_contains_required_review_safe_fields(self):
        required = {
            "overlay_id",
            "event_id",
            "candidate_observation_ref",
            "prim_path",
            "proposed_prim_path",
            "display_label",
            "overlay_kind",
            "candidate_only",
            "review_required",
            "official_status",
            "evidence_refs",
            "limitation_refs",
            "trace_refs",
            "review_state",
        }
        self.assertEqual(8, len(self.kit_items))
        for item in self.kit_items:
            self.assertTrue(required.issubset(item))
            self.assertTrue(item["prim_path"].startswith("/World/CityBrain/R7D/EventStateSmoke/"))
            self.assertEqual("local_replay_review_marker", item["overlay_kind"])

    def test_webui_kit_parity_passes_for_refs_and_review_state(self):
        self.assertEqual("PASS", self.parity["status"])
        self.assertEqual(8, self.parity["pairs_checked"])
        self.assertEqual(0, self.parity["failure_count"])
        for pair in self.parity["pairs"]:
            self.assertEqual("PASS", pair["status"])
            self.assertEqual([], pair["mismatches"])

    def test_candidate_only_is_preserved(self):
        self.assertTrue(all(item["candidate_only"] is True for item in self.webui_items + self.kit_items))

    def test_review_required_is_preserved(self):
        self.assertTrue(all(item["review_required"] is True for item in self.webui_items + self.kit_items))

    def test_official_status_remains_not_official(self):
        self.assertTrue(all(item["official_status"] == "not_official" for item in self.webui_items + self.kit_items))

    def test_sandbox_draft_case_remains_draft_not_submitted(self):
        sandbox_items = [item for item in self.webui_items + self.kit_items if item["query_family"] == "sandbox_draft_cases"]
        self.assertEqual(2, len(sandbox_items))
        self.assertTrue(all(item["submission_status"] == "draft_not_submitted" for item in sandbox_items))

    def test_action_proposal_remains_not_executed(self):
        action_items = [item for item in self.webui_items + self.kit_items if item["query_family"] == "not_executed_actions"]
        self.assertEqual(2, len(action_items))
        self.assertTrue(all(item["execution_status"] == "not_executed" for item in action_items))

    def test_no_official_case_ticket_or_submission_refs_are_produced(self):
        payload = json.dumps({"webui": self.webui_items, "kit": self.kit_items}, sort_keys=True).lower()
        self.assertNotIn('"official_case_id": "', payload)
        self.assertNotIn('"external_submission_ref": "', payload)
        self.assertNotIn('"submission_status": "submitted"', payload)

    def test_no_dispatch_control_or_enforcement_refs_are_produced(self):
        payload = json.dumps({"webui": self.webui_items, "kit": self.kit_items}, sort_keys=True).lower()
        self.assertNotIn('"dispatch_ref": "', payload)
        self.assertNotIn('"control_ref": "', payload)
        self.assertNotIn('"enforcement_ref": "', payload)
        self.assertNotIn('"execution_status": "executed"', payload)

    def test_no_legal_or_certified_claim_appears(self):
        payload = json.dumps({"webui": self.webui_items, "kit": self.kit_items}, sort_keys=True).lower()
        self.assertNotIn('"legal_violation": true', payload)
        self.assertNotIn('"certified": true', payload)
        self.assertTrue(self.audit["no_legal_certified_claim"])

    def test_no_live_retrieval_production_api_url_fetch_or_llm_call_occurs(self):
        self.assertTrue(self.audit["no_live_retrieval_production_api_url_fetch_llm_call"])
        source = (ROOT / "scripts" / "run_main_citybrain_r7d_webui_kit_event_state_smoke.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("chat.completions", source)
        self.assertNotIn("fetch(", source)

    def test_kit_handoff_does_not_claim_full_citywide_twin_or_live_scene_control(self):
        self.assertTrue(self.audit["no_full_citywide_twin_live_kit_control_claim"])
        self.assertTrue(all(item["marker_only"] is True for item in self.kit_items))
        self.assertTrue(all(item["full_citywide_twin_claim"] is False for item in self.kit_items))
        self.assertTrue(all(item["live_kit_control"] is False for item in self.kit_items))
        self.assertIn("custom bool full_citywide_twin_claim = false", self.usda_text)
        self.assertIn("custom bool live_kit_control = false", self.usda_text)

    def test_ask_runtime_scoped_diff_empty(self):
        result = subprocess.run(
            [
                "git",
                "diff",
                "--",
                "packages/ask_v11",
                "packages/contracts",
                "scripts/run_ask_v11_sealed_eval.py",
                "scripts/run_ask_v11_real_corpus_eval_r2_mapping_expansion.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertEqual("", result.stdout)

    def test_hash_manifest_verifies(self):
        manifest = json.loads((OUTPUT_ROOT / "R7D_HASH_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", manifest["status"])
        self.assertGreaterEqual(manifest["item_count"], 10)
        self.assertEqual(0, manifest["missing_count"])
        self.assertEqual(0, manifest["mismatch_count"])
        self.assertEqual("PASS", verify_hash_manifest()["status"])


if __name__ == "__main__":
    unittest.main()

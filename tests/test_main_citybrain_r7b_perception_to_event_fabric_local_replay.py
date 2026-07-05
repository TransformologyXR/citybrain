import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.run_main_citybrain_r7b_perception_to_event_fabric_local_replay import (
    OUTPUT_ROOT,
    boundary_audit,
    build_event_log,
    get_event_trace,
    get_events_for_candidate_observation,
    list_active_review_events,
    list_quarantined_observations,
    list_unresolved_observations,
    materialize_review_state,
    overlay_exports,
    replay_event_log,
    read_jsonl,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainR7BPerceptionToEventFabricLocalReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(
            [sys.executable, "scripts\\run_main_citybrain_r7b_perception_to_event_fabric_local_replay.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        cls.events = build_event_log()

    def test_append_only_event_log_written(self):
        rows = read_jsonl(OUTPUT_ROOT / "R7B_LOCAL_EVENT_LOG.jsonl")
        self.assertEqual(8, len(rows))
        self.assertEqual([event["event_id"] for event in self.events], [row["event_id"] for row in rows])

    def test_replay_is_deterministic(self):
        replay = replay_event_log(self.events)
        self.assertEqual("PASS", replay["status"])
        self.assertEqual(8, replay["event_count"])
        self.assertTrue(replay["not_executed_preserved"])
        self.assertTrue(replay["not_official_preserved"])

    def test_materialized_state_counts(self):
        state = materialize_review_state(self.events)
        self.assertEqual("PASS", state["status"])
        self.assertEqual(1, state["summary_counts"]["active_review_events"])
        self.assertEqual(2, state["summary_counts"]["unresolved_observations"])
        self.assertEqual(2, state["summary_counts"]["quarantined_observations"])
        self.assertEqual(1, state["summary_counts"]["sandbox_draft_cases"])
        self.assertEqual(1, state["summary_counts"]["not_executed_action_proposals"])

    def test_unresolved_and_quarantined_preserved(self):
        self.assertEqual(2, len(list_unresolved_observations(self.events)))
        self.assertEqual(2, len(list_quarantined_observations(self.events)))
        self.assertTrue(all(event["candidate_only"] for event in list_unresolved_observations(self.events)))
        self.assertTrue(all(event["status"] == "quarantined_not_promoted" for event in list_quarantined_observations(self.events)))

    def test_candidate_only_official_and_execution_boundaries(self):
        for event in self.events:
            self.assertTrue(event["candidate_only"])
            self.assertEqual("not_official", event["official_status"])
            self.assertEqual("not_executed", event["execution_status"])

    def test_draft_not_submitted_and_action_not_executed(self):
        draft = [event for event in self.events if event["event_type"] == "sandbox_draft_case.created"][0]
        proposal = [event for event in self.events if event["event_type"] == "action_proposal.created_not_executed"][0]
        self.assertEqual("draft_not_submitted", draft["submission_status"])
        self.assertEqual("not_executed", proposal["execution_status"])
        self.assertIsNone(proposal["payload"]["dispatch_ref"])
        self.assertIsNone(proposal["payload"]["control_ref"])
        self.assertIsNone(proposal["payload"]["enforcement_ref"])

    def test_no_official_action_refs_or_legal_certified_claims(self):
        audit = boundary_audit(self.events)
        self.assertEqual("PASS", audit["status"])
        serialized = json.dumps(self.events, sort_keys=True).lower()
        self.assertNotIn('"legal_violation": true', serialized)
        self.assertNotIn('"certified": true', serialized)
        self.assertNotIn('"production_api": true', serialized)
        self.assertNotIn('"live_camera": true', serialized)
        self.assertNotIn('"execution_status": "executed"', serialized)

    def test_webui_and_kit_exports_preserve_overlay_boundaries(self):
        for export in overlay_exports(self.events, "webui") + overlay_exports(self.events, "kit"):
            self.assertTrue(export["candidate_only"])
            self.assertTrue(export["review_required"])
            self.assertEqual("not_official", export["official_status"])
            self.assertEqual("not_executed", export["execution_status"])
            self.assertTrue(export["trace_refs"])

    def test_query_helpers(self):
        active = list_active_review_events(self.events)
        self.assertEqual(1, len(active))
        candidate_events = get_events_for_candidate_observation(self.events, "candidate:r7a:obs:accepted-001")
        self.assertEqual(4, len(candidate_events))
        trace = get_event_trace(self.events, "r7b:event:review-created:0001")
        self.assertIn("R7A:review_event_export", trace)

    def test_no_live_retrieval_production_api_or_llm_call_occurs(self):
        source = (ROOT / "scripts" / "run_main_citybrain_r7b_perception_to_event_fabric_local_replay.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("chat.completions", source)
        self.assertNotIn("fetch(", source)

    def test_hash_manifest_verifies(self):
        manifest = json.loads((OUTPUT_ROOT / "R7B_HASH_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", manifest["status"])
        self.assertGreaterEqual(manifest["item_count"], 10)
        self.assertEqual(0, manifest["missing_count"])
        self.assertEqual(0, manifest["mismatch_count"])

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


if __name__ == "__main__":
    unittest.main()

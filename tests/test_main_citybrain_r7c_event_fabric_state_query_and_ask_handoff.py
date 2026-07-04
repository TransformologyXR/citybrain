import json
import subprocess
import unittest
from pathlib import Path

from scripts.run_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff import (
    CANNOT_CLAIM,
    OUTPUT_ROOT,
    ask_handoff_evidence_packets,
    ask_handoff_fixtures,
    boundary_audit,
    load_r7b_state,
    query_active_review_events,
    query_candidate_observation_context,
    query_event_trace_by_id,
    query_quarantined_observations,
    query_results,
    query_sandbox_draft_cases,
    query_unresolved_observations,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainR7CEventFabricStateQueryAndAskHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(
            [".venv\\Scripts\\python.exe", "scripts\\run_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        cls.state = load_r7b_state()
        cls.results = query_results(cls.state)
        cls.fixtures = ask_handoff_fixtures(cls.results)
        cls.evidence_packets = ask_handoff_evidence_packets(cls.fixtures)

    def test_r7b_materialized_state_loaded_or_fallback_documented(self):
        self.assertFalse(self.state["fallback_used"])
        self.assertEqual("PASS", self.state["materialized"]["status"])

    def test_active_review_events_query_is_candidate_safe(self):
        rows = query_active_review_events(self.state)
        self.assertEqual(1, len(rows))
        self.assertTrue(rows[0]["candidate_only"])
        self.assertEqual("not_official", rows[0]["official_status"])
        self.assertEqual("not_executed", rows[0]["execution_status"])

    def test_unresolved_observations_query_preserves_state(self):
        rows = query_unresolved_observations(self.state)
        self.assertEqual(2, len(rows))
        self.assertTrue(all(row["preservation_state"] == "unresolved_review_candidate" for row in rows))
        self.assertTrue(all(row["candidate_only"] for row in rows))

    def test_quarantined_observations_query_preserves_reasons(self):
        rows = query_quarantined_observations(self.state)
        self.assertEqual(2, len(rows))
        self.assertTrue(all(row["quarantine_state"] == "quarantined_not_promoted" for row in rows))
        self.assertTrue(any(row["reasons"] for row in rows))

    def test_event_trace_query_returns_trace_evidence_and_limits(self):
        rows = query_event_trace_by_id(self.state, "r7b:event:review-created:0001")
        self.assertEqual(1, len(rows))
        self.assertTrue(rows[0]["trace_refs"])
        self.assertTrue(rows[0]["evidence_refs"])
        self.assertTrue(rows[0]["limitation_refs"])

    def test_candidate_observation_context_query(self):
        rows = query_candidate_observation_context(self.state, "candidate:r7a:obs:accepted-001")
        self.assertEqual(4, len(rows))
        self.assertTrue(all(row["candidate_only"] for row in rows))

    def test_not_executed_and_sandbox_draft_queries_preserve_boundaries(self):
        action_result = [result for result in self.results if result["query_family"] == "not_executed_actions"][0]
        draft_rows = query_sandbox_draft_cases(self.state)
        self.assertEqual(1, action_result["result_count"])
        self.assertEqual("not_executed", action_result["execution_status"])
        self.assertEqual(1, len(draft_rows))
        self.assertEqual("draft_not_submitted", draft_rows[0]["submission_status"])

    def test_webui_and_kit_query_context_exports_preserve_boundaries(self):
        webui = json.loads((OUTPUT_ROOT / "R7C_WEBUI_QUERY_CONTEXT_EXPORT.json").read_text(encoding="utf-8"))["items"]
        kit = json.loads((OUTPUT_ROOT / "R7C_KIT_QUERY_CONTEXT_EXPORT.json").read_text(encoding="utf-8"))["items"]
        self.assertEqual(8, len(webui))
        self.assertEqual(8, len(kit))
        for item in webui + kit:
            self.assertTrue(item["candidate_only"])
            self.assertEqual("not_official", item["official_status"])
            self.assertEqual("not_executed", item["execution_status"])

    def test_ask_handoff_fixtures_and_evidence_packets_exist(self):
        self.assertEqual(8, len(self.fixtures))
        self.assertEqual(8, len(self.evidence_packets))
        for fixture in self.fixtures:
            self.assertEqual("ask_v11_local_demo_query_handoff", fixture["fixture_kind"])
            self.assertEqual("local_replay", fixture["source_kind"])
            self.assertTrue(fixture["packet_hash"])
        for packet in self.evidence_packets:
            self.assertEqual("ask_v11_evidence_compatible_fixture", packet["packet_kind"])
            self.assertEqual("not_official", packet["official_status"])
            self.assertEqual("not_executed", packet["execution_status"])

    def test_cannot_claim_text_includes_required_limits(self):
        required = set(CANNOT_CLAIM)
        for fixture in self.fixtures:
            self.assertTrue(required.issubset(set(fixture["cannot_claim"])))
        for packet in self.evidence_packets:
            self.assertTrue(required.issubset(set(packet["cannot_claim"])))

    def test_no_raw_query_or_official_action_refs(self):
        payload = json.dumps(
            {
                "results": self.results,
                "fixtures": self.fixtures,
                "evidence_packets": self.evidence_packets,
            },
            sort_keys=True,
        ).lower()
        self.assertNotIn('"raw_query"', payload)
        self.assertNotIn('"official_case_id": "', payload)
        self.assertNotIn('"external_submission_ref": "', payload)
        self.assertNotIn('"dispatch_ref": "', payload)
        self.assertNotIn('"control_ref": "', payload)
        self.assertNotIn('"enforcement_ref": "', payload)
        self.assertNotIn('"execution_status": "executed"', payload)
        self.assertNotIn('"submission_status": "submitted"', payload)
        self.assertNotIn('"legal_violation": true', payload)
        self.assertNotIn('"certified": true', payload)

    def test_boundary_audit_passes(self):
        audit = boundary_audit([], self.results, self.fixtures, self.evidence_packets)
        self.assertEqual("PASS", audit["status"])
        self.assertTrue(audit["raw_query_downstream_authority_absent"])
        self.assertFalse(audit["ask_runtime_invoked"])

    def test_no_live_retrieval_production_api_url_fetch_or_llm_call_occurs(self):
        source = (ROOT / "scripts" / "run_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("chat.completions", source)
        self.assertNotIn("fetch(", source)

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
        manifest = json.loads((OUTPUT_ROOT / "R7C_HASH_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", manifest["status"])
        self.assertGreaterEqual(manifest["item_count"], 10)
        self.assertEqual(0, manifest["missing_count"])
        self.assertEqual(0, manifest["mismatch_count"])


if __name__ == "__main__":
    unittest.main()

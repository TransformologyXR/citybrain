import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.run_main_citybrain_r7a_perception_candidate_observation_ingress import (
    OUTPUT_ROOT,
    build_action_proposal,
    build_sandbox_draft_case_ticket,
    classify_observation,
    process_observations,
    require_reviewer_note,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainR7APerceptionCandidateObservationIngressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(
            [sys.executable, "scripts\\run_main_citybrain_r7a_perception_candidate_observation_ingress.py"],
            cwd=ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        cls.result = process_observations()

    def test_valid_local_replay_candidate_observation_ingests(self):
        self.assertEqual(5, len(self.result["candidate_observations"]))
        self.assertEqual(1, len(self.result["accepted_review_events"]))
        event = self.result["accepted_review_events"][0]
        self.assertEqual("candidate_not_confirmed", event["event_truth_status"])
        self.assertEqual("not_official", event["official_status"])

    def test_valid_observation_remains_candidate_only(self):
        event = self.result["accepted_review_events"][0]
        self.assertTrue(event["candidate_only"])
        self.assertTrue(event["review_required"])
        self.assertIn("dispatch_control_enforcement", event["not_executed"])

    def test_review_promotion_requires_reviewer_note(self):
        with self.assertRaisesRegex(ValueError, "reviewer_note_required"):
            require_reviewer_note("")
        event = self.result["accepted_review_events"][0]
        draft = build_sandbox_draft_case_ticket(event, "Reviewer note for sandbox draft only.")
        self.assertEqual("draft_not_submitted", draft["submission_status"])

    def test_invalid_observation_is_quarantined(self):
        quarantined = self.result["quarantined_observations"]
        self.assertEqual(2, len(quarantined))
        reasons = " ".join(" ".join(item["reasons"]) for item in quarantined)
        self.assertIn("missing_candidate_observation_id", reasons)
        self.assertIn("forbidden_assertion_tokens", reasons)

    def test_unresolved_entity_or_location_is_preserved_not_promoted(self):
        unresolved = self.result["unresolved_observations"]
        self.assertEqual(2, len(unresolved))
        self.assertTrue(all(item["preservation_state"] == "unresolved_review_candidate" for item in unresolved))
        self.assertTrue(all(item["promotion_allowed"] is False for item in unresolved))
        reasons = " ".join(" ".join(item["reasons"]) for item in unresolved)
        self.assertIn("missing_location_or_geometry", reasons)
        self.assertIn("low_confidence", reasons)

    def test_sandbox_draft_case_ticket_is_draft_not_submitted_only(self):
        draft = self.result["sandbox_draft_case_ticket"]
        self.assertEqual("sandbox", draft["case_scope"])
        self.assertEqual("draft_not_submitted", draft["submission_status"])
        self.assertIsNone(draft["official_case_id"])
        self.assertIsNone(draft["external_submission_ref"])

    def test_action_proposal_remains_not_executed(self):
        proposal = build_action_proposal(self.result["accepted_review_events"][0])
        self.assertEqual("not_executed", proposal["execution_status"])
        self.assertIsNone(proposal["external_action_ref"])
        self.assertIsNone(proposal["dispatch_ref"])
        self.assertIsNone(proposal["control_ref"])
        self.assertIsNone(proposal["enforcement_ref"])

    def test_no_official_case_ticket_dispatch_or_action_ids_are_produced(self):
        serialized = json.dumps(self.result, sort_keys=True)
        self.assertNotIn('"submission_status": "submitted"', serialized)
        self.assertNotIn('"execution_status": "executed"', serialized)
        self.assertNotIn('"official_case_id": "', serialized)
        self.assertNotIn('"dispatch_ref": "', serialized)
        self.assertNotIn('"control_ref": "', serialized)
        self.assertNotIn('"enforcement_ref": "', serialized)

    def test_no_live_retrieval_production_api_or_llm_call_occurs(self):
        source = (ROOT / "scripts" / "run_main_citybrain_r7a_perception_candidate_observation_ingress.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("chat.completions", source)
        self.assertNotIn("fetch(", source)

    def test_webui_and_kit_exports_preserve_candidate_only_and_limitations(self):
        for export in self.result["webui_exports"] + self.result["kit_exports"]:
            self.assertTrue(export["candidate_only"])
            self.assertTrue(export["review_required"])
            self.assertEqual("not_official", export["official_status"])
            self.assertTrue(export["limitations"])

    def test_hash_manifest_verifies(self):
        manifest = json.loads((OUTPUT_ROOT / "R7A_HASH_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", manifest["status"])
        self.assertGreaterEqual(manifest["item_count"], 9)
        self.assertEqual(0, manifest["missing_count"])
        self.assertEqual(0, manifest["mismatch_count"])

    def test_ask_runtime_untouched(self):
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

    def test_classifier_rejects_live_source_claim(self):
        live_claim = {
            "candidate_observation_id": "candidate:r7a:test-live",
            "source_kind": "live_camera",
            "source_id": "source:test-live",
            "source_label": "live",
            "observed_at": "2026-07-04T11:00:00Z",
            "detector_kind": "fixture",
            "detector_version": "1",
            "observation_type": "official_violation",
            "detected_class": "certified_detection",
            "confidence": 0.9,
            "evidence_refs": ["source:test-live"],
            "review_state": "candidate",
            "claim_boundary": "official_violation",
            "not_executed": ["official_submission"],
        }
        from scripts.run_main_citybrain_r7a_perception_candidate_observation_ingress import canonical_hash

        live_claim["packet_hash"] = canonical_hash(live_claim, {"packet_hash"})
        self.assertEqual("quarantine", classify_observation(live_claim)["classification"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "run_main_citybrain_sprint2_perception_to_event_integration.py"
spec = importlib.util.spec_from_file_location("sprint2_track2", SCRIPT_PATH)
track2 = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(track2)


class Sprint2PerceptionToEventIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = track2.write_all_outputs()
        cls.candidates = json.loads((track2.OUTPUT_ROOT / "PERCEPTION_TO_EVENT_CANDIDATE_OBSERVATIONS.json").read_text(encoding="utf-8"))["items"]
        cls.events = [
            json.loads(line)
            for line in (track2.OUTPUT_ROOT / "PERCEPTION_TO_EVENT_EVENT_ENVELOPES.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        cls.queries = json.loads((track2.OUTPUT_ROOT / "PERCEPTION_TO_EVENT_QUERY_RESULT_PACKETS.json").read_text(encoding="utf-8"))["items"]
        cls.overlays = json.loads((track2.OUTPUT_ROOT / "PERCEPTION_TO_EVENT_OVERLAY_PACKETS.json").read_text(encoding="utf-8"))["items"]

    def test_r0_gate_is_passed(self) -> None:
        gate = track2.ensure_r0_gate()
        self.assertEqual(track2.R0_1_PASS, gate["decision_status"])
        self.assertTrue(gate["r0_1_compatible"])
        self.assertEqual("PASS", gate["validator_status"])

    def test_candidate_observations_use_r0_required_keys_and_boundaries(self) -> None:
        self.assertEqual(6, len(self.candidates))
        for candidate in self.candidates:
            self.assertFalse([key for key in track2.REQUIRED_CANDIDATE_KEYS if key not in candidate])
            self.assertTrue(candidate["candidate_only"])
            self.assertTrue(candidate["review_required"])
            self.assertEqual("not_official", candidate["official_status"])
            self.assertEqual("sensor_inferred", candidate["source_class"])
            self.assertIn("official case/ticket creation", candidate["cannot_claim"])
            self.assertIn("production_api", candidate["not_executed"])

    def test_event_envelopes_use_r0_event_shape(self) -> None:
        self.assertEqual(6, len(self.events))
        for event in self.events:
            self.assertFalse([key for key in track2.REQUIRED_EVENT_KEYS if key not in event])
            self.assertIn(event["event_type"], track2.ALLOWED_EVENT_TYPES)
            self.assertEqual("draft_not_submitted", event["submission_status"])
            self.assertEqual("not_executed", event["execution_status"])
            self.assertEqual("not_official", event["official_status"])
            self.assertTrue(event["candidate_only"])
            self.assertEqual("citybrain.event_fabric.r0_1", event["schema_version"])
            self.assertEqual("review_display_only", event["authority_level"])
            self.assertIn("candidate_observation_ref", event)

    def test_materialized_state_query_and_overlay_counts(self) -> None:
        state = json.loads((track2.OUTPUT_ROOT / "PERCEPTION_TO_EVENT_MATERIALIZED_REVIEW_STATE.json").read_text(encoding="utf-8"))
        self.assertEqual(6, state["summary_counts"]["candidate_observations"])
        self.assertEqual(6, state["summary_counts"]["events"])
        self.assertEqual(1, len(self.queries))
        self.assertEqual(6, len(self.overlays))

    def test_query_and_overlay_packets_remain_review_only(self) -> None:
        query = self.queries[0]
        self.assertEqual({"not_official": 6}, query["official_status_summary"])
        self.assertIn("No official status", query["unknowns"][0])
        for overlay in self.overlays:
            self.assertTrue(overlay["candidate_only"])
            self.assertTrue(overlay["review_required"])
            self.assertTrue(overlay["marker_metadata_only"])
            self.assertEqual("not_official", overlay["official_status"])

    def test_compatibility_and_boundary_audits_pass(self) -> None:
        compatibility = json.loads((track2.OUTPUT_ROOT / "PERCEPTION_TO_EVENT_R7A_R7B_R7C_R7D_COMPATIBILITY.json").read_text(encoding="utf-8"))
        audit = json.loads((track2.OUTPUT_ROOT / "PERCEPTION_TO_EVENT_SOURCE_BOUNDARY_AUDIT.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", compatibility["status"])
        self.assertTrue(compatibility["event_fabric_r0_1_contract_compatibility"])
        self.assertTrue(compatibility["r7a_candidate_observation_ingress_compatibility"])
        self.assertTrue(compatibility["r7b_event_log_materialized_state_compatibility"])
        self.assertTrue(compatibility["r7c_query_evidence_handoff_compatibility"])
        self.assertTrue(compatibility["r7d_webui_kit_overlay_compatibility"])
        self.assertTrue(all(row["status"] == "PASS" for row in compatibility["r0_1_validator_rows"]))
        self.assertEqual("FAIL", compatibility["vss_as_candidate_observation_negative_check"]["status"])
        self.assertEqual("PASS", audit["status"])

    def test_vss_and_source_class_boundaries(self) -> None:
        source_map = json.loads((track2.OUTPUT_ROOT / "PERCEPTION_TO_EVENT_SOURCE_CLASS_MAP.json").read_text(encoding="utf-8"))
        self.assertEqual("model_generated_narrative_not_fact_source", source_map["source_class_map"]["VSS"])
        self.assertEqual("sensor_inferred", source_map["source_class_map"]["DeepStream"])
        self.assertTrue(source_map["vss_not_fact_source"])
        self.assertTrue(source_map["all_classes_r0_approved"])

    def test_manifests_verify(self) -> None:
        self.assertEqual("PASS", track2.verify_manifest(track2.OUTPUT_ROOT, "PERCEPTION_TO_EVENT_HASH_MANIFEST.json")["status"])
        self.assertEqual("PASS", track2.verify_manifest(track2.CLOSEOUT_ROOT, "PERCEPTION_TO_EVENT_INTEGRATION_CLOSEOUT_HASH_MANIFEST.json")["status"])
        self.assertEqual("PASS", track2.verify_manifest(track2.FINAL_STATUS_ROOT, "PERCEPTION_TO_EVENT_INTEGRATION_FINAL_STATUS_HASH_MANIFEST.json")["status"])

    def test_no_live_retrieval_or_llm_calls_in_runner(self) -> None:
        source = SCRIPT_PATH.read_text(encoding="utf-8").lower()
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("chat.completions", source)
        self.assertNotIn("fetch(", source)

    def test_ask_and_r7_runtime_scoped_diffs_are_empty(self) -> None:
        ask = subprocess.run(
            [
                "git",
                "diff",
                "--",
                "packages/ask_v11",
                "scripts/run_ask_v11_sealed_eval.py",
                "scripts/run_ask_v11_real_corpus_eval_r2_mapping_expansion.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        r7 = subprocess.run(
            [
                "git",
                "diff",
                "--",
                "scripts/run_main_citybrain_r7a_perception_candidate_observation_ingress.py",
                "scripts/run_main_citybrain_r7b_perception_to_event_fabric_local_replay.py",
                "scripts/run_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff.py",
                "scripts/run_main_citybrain_r7d_webui_kit_event_state_smoke.py",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertEqual("", ask.stdout)
        self.assertEqual("", r7.stdout)


if __name__ == "__main__":
    unittest.main()

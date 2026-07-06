import json
import unittest

from scripts.run_epoch_2_2a_integration_gate import (
    OUTPUT_ROOT,
    PASS_STATUS,
    REQUIRED_OUTPUTS,
    build_limitations,
    sha256_file,
    write_all_outputs,
)


class Epoch22aIntegrationGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = write_all_outputs()
        cls.decision = cls.result["decision"]
        cls.matrix = cls.result["matrix"]

    def read_json(self, name):
        return json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8"))

    def test_required_outputs_exist(self):
        for name in REQUIRED_OUTPUTS:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_decision_passes_and_allows_push_2_2b(self):
        self.assertEqual(PASS_STATUS, self.decision["status"], self.decision["blockers"])
        self.assertTrue(self.decision["activation_wave_1_allowed_to_begin"])
        self.assertEqual("main", self.decision["branch"])
        self.assertEqual("PASS", self.decision["contract_convergence_status"])
        self.assertEqual("PASS_FOCUSED_EPOCH_2_2A_CORPUS", self.decision["track0"]["corpus_delta_status"])
        self.assertEqual("PASS", self.decision["track0"]["source_of_truth_delta_status"])
        self.assertEqual("PASS", (OUTPUT_ROOT / "PUSH_2_2B_ALLOWED_TO_OPEN.flag").read_text(encoding="utf-8").strip())

    def test_contract_convergence_sections_pass(self):
        for name, section in self.matrix["checks"].items():
            self.assertEqual("PASS", section["status"], name)
        service_registry = self.matrix["checks"]["service_registry"]
        self.assertGreaterEqual(service_registry["service_count"], 5)
        for row in service_registry["service_results"]:
            self.assertEqual("PASS", row["status"], row)

    def test_observability_consumes_real_registry_and_envelope_refs(self):
        observability = self.matrix["checks"]["observability"]
        self.assertEqual("PASS", observability["status"])
        self.assertEqual("AVAILABLE", observability["service_registry_status"]["status"])
        self.assertTrue(observability["service_registry_status"]["refs"])
        self.assertTrue(observability["run_envelope_refs"])

    def test_llm_seat_readiness_for_next_pushes(self):
        llm = self.matrix["checks"]["llm_seats"]
        self.assertEqual("PASS", llm["status"])
        self.assertEqual("ready_for_2_2b", llm["seat_status"]["ask_g8_writer_pattern_adapter"])
        self.assertEqual("ready_for_2_2b", llm["seat_status"]["brief_writer_v2"])
        self.assertEqual("ready_for_2_2c", llm["seat_status"]["g2_intent_concept_resolver_proposal_adapter"])

    def test_multi_agent_replay_has_green_sequence(self):
        replay = self.matrix["checks"]["multi_agent_replay"]
        self.assertEqual("PASS", replay["status"])
        self.assertGreaterEqual(replay["green_sequence_count"], 1)
        self.assertIn("event_watch_check_brief_workflow", replay["sequence_ids"])

    def test_limitations_are_enumerated_with_owner_and_next_lane(self):
        limitations = self.decision["limitations"]
        self.assertEqual(len(build_limitations()), len(limitations))
        for limitation in limitations:
            self.assertTrue(limitation["owner"])
            self.assertTrue(limitation["next_lane"])
            self.assertTrue(limitation["limitation"])

    def test_track0_delta_artifacts_exist(self):
        corpus = self.read_json("REGRESSION_CORPUS_DELTA.json")
        ledger = self.read_json("MASTER_LEDGER_DELTA.json")
        source = self.read_json("SOURCE_OF_TRUTH_MATRIX_DELTA.json")
        self.assertEqual("PASS_FOCUSED_EPOCH_2_2A_CORPUS", corpus["status"])
        self.assertGreaterEqual(corpus["newly_sealed_fixture_count"], 7)
        self.assertEqual(PASS_STATUS, ledger["status"])
        self.assertEqual("PASS", source["status"])
        self.assertEqual("output_local_delta_no_frozen_upstream_mutation", source["append_mode"])

    def test_hash_manifest_matches_outputs(self):
        manifest = self.read_json("HASH_MANIFEST.json")
        self.assertGreaterEqual(len(manifest["files"]), 7)
        for row in manifest["files"]:
            rel_path = row["path"].replace("/", "\\")
            path = OUTPUT_ROOT.parents[2] / rel_path
            self.assertTrue(path.exists(), row)
            self.assertEqual(row["sha256"], sha256_file(path))

    def test_non_claims_preserved(self):
        non_claims = self.decision["non_claims"]
        self.assertFalse(non_claims["epoch_2_2_closed"])
        self.assertFalse(non_claims["production_monitoring"])
        self.assertFalse(non_claims["service_acted_or_mutated_official_state"])
        self.assertFalse(non_claims["official_action_ticket_dispatch_enforcement_or_legal_finding"])
        self.assertFalse(non_claims["learned_ranking_prediction_or_trained_model"])
        self.assertFalse(non_claims["sealed_ask_core_modified"])


if __name__ == "__main__":
    unittest.main()

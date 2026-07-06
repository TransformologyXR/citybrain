import json
import unittest

from scripts.run_epoch_2_2b_integration_gate import (
    OUTPUT_ROOT,
    PASS_STATUS,
    REQUIRED_OUTPUTS,
    build_limitations,
    sha256_file,
    write_all_outputs,
)


class Epoch22bIntegrationGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = write_all_outputs()
        cls.decision = cls.result["decision"]
        cls.smoke = cls.result["smoke"]
        cls.observability = cls.result["observability"]

    def read_json(self, name):
        return json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8"))

    def test_required_outputs_exist(self):
        for name in REQUIRED_OUTPUTS:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_decision_passes_and_opens_push_2_2c(self):
        self.assertEqual(PASS_STATUS, self.decision["status"], self.decision["blockers"])
        self.assertEqual("main", self.decision["branch"])
        self.assertTrue(self.decision["push_2_2c_allowed_to_open"])
        self.assertEqual("PASS", (OUTPUT_ROOT / "PUSH_2_2C_ALLOWED_TO_OPEN.flag").read_text(encoding="utf-8").strip())
        self.assertEqual("PASS_PUSH_2_2A_INTEGRATION", self.decision["prerequisite"]["integration_2_2a_status"])

    def test_watch_event_briefing_required_checks_pass(self):
        for name in ["watch", "event_incident", "briefing", "observability", "end_to_end_smoke"]:
            self.assertEqual("PASS", self.decision["required_checks"][name]["status"], name)
        self.assertEqual(2, self.decision["required_checks"]["watch"]["tick_count"])
        self.assertGreaterEqual(len(self.decision["required_checks"]["event_incident"]["watch_handoff_refs"]), 1)
        self.assertGreaterEqual(self.decision["required_checks"]["briefing"]["positive_fixture_count"], 3)

    def test_end_to_end_smoke_green(self):
        self.assertEqual("PASS", self.smoke["status"])
        for key, value in self.smoke["checks"].items():
            self.assertTrue(value, key)
        self.assertEqual(4, len(self.smoke["steps"]))
        self.assertFalse(self.smoke["non_claims"]["official_action"])
        self.assertFalse(self.smoke["non_claims"]["production_monitoring"])

    def test_observability_confirmation_includes_wave_1_rows(self):
        self.assertEqual("PASS", self.observability["status"])
        service_ids = {row["service_id"] for row in self.observability["service_rows"]}
        self.assertEqual({"watch_scout_service", "event_incident_service", "briefing_service"}, service_ids)
        for row in self.observability["service_rows"]:
            self.assertTrue(row["source_ref"], row)

    def test_track0_delta_artifacts_exist_and_pass(self):
        corpus = self.read_json("REGRESSION_CORPUS_DELTA.json")
        ledger = self.read_json("MASTER_LEDGER_DELTA.json")
        source = self.read_json("SOURCE_OF_TRUTH_MATRIX_DELTA.json")
        self.assertEqual("PASS_FOCUSED_EPOCH_2_2B_CORPUS", corpus["status"])
        self.assertGreaterEqual(corpus["newly_sealed_fixture_count"], 7)
        self.assertEqual(PASS_STATUS, ledger["status"])
        self.assertEqual("PASS", source["status"])
        self.assertEqual("output_local_delta_no_frozen_upstream_mutation", source["append_mode"])

    def test_limitations_are_enumerated_with_owner_and_next_lane(self):
        self.assertEqual(len(build_limitations()), len(self.decision["limitations"]))
        for limitation in self.decision["limitations"]:
            self.assertTrue(limitation["owner"])
            self.assertTrue(limitation["next_lane"])
            self.assertTrue(limitation["limitation"])

    def test_no_forbidden_claims(self):
        non_claims = self.decision["non_claims"]
        for key, value in non_claims.items():
            self.assertFalse(value, key)

    def test_hash_manifest_matches_outputs(self):
        manifest = self.read_json("HASH_MANIFEST.json")
        self.assertGreaterEqual(len(manifest["files"]), 8)
        repo_root = OUTPUT_ROOT.parents[2]
        for row in manifest["files"]:
            path = repo_root / row["path"]
            self.assertTrue(path.exists(), row)
            self.assertEqual(row["sha256"], sha256_file(path))


if __name__ == "__main__":
    unittest.main()

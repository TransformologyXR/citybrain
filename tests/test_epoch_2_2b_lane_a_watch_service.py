import json
import unittest

from scripts.run_epoch_2_2b_lane_a_watch_service import (
    OUTPUT_ROOT,
    PASS_CODE,
    PASS_STATUS,
    REQUIRED_ARTIFACTS,
    write_all_outputs,
)


class Epoch22bLaneAWatchServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = write_all_outputs()
        cls.gate = cls.result["gate"]
        cls.decision = cls.result["decision"]

    def read_json(self, name):
        return json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8"))

    def read_jsonl(self, name):
        return [
            json.loads(line)
            for line in (OUTPUT_ROOT / name).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def test_prerequisite_gate_passes(self):
        self.assertEqual("PASS", self.gate["status"], self.gate["errors"])
        self.assertEqual("main", self.gate["branch"])
        self.assertEqual("PASS_PUSH_2_2A_INTEGRATION", self.gate["integration_status"])
        self.assertEqual("PASS", self.gate["flag_value"])

    def test_required_artifacts_exist(self):
        for name in REQUIRED_ARTIFACTS:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_config_uses_watch_scout_service_registry_entry(self):
        config = self.read_json("WATCH_SERVICE_CONFIG.json")
        self.assertEqual(PASS_STATUS, config["status"])
        self.assertEqual("watch_scout_service", config["service_id"])
        self.assertEqual("watch_scout", config["component_id"])
        self.assertEqual("watch_scout_service", config["service_registry_entry"]["service_id"])
        self.assertTrue(config["service_registry_entry"]["run_envelope_required"])
        self.assertEqual("local_replay_review_query_only", config["mode"])
        self.assertGreaterEqual(config["hard_volume_caps"]["global_queue_tick_cap"], 1)
        self.assertGreaterEqual(config["hard_volume_caps"]["max_items_per_family_per_tick"], 1)
        self.assertEqual(86400, config["dedupe_window_seconds"])
        self.assertEqual(
            ["P0_boundary_safety", "P1_checked_candidate", "P2_stale_or_low_authority", "P3_contextual"],
            config["static_priority_tiers"],
        )
        self.assertFalse(config["alert_cannon_boundary"]["learned_ranking_used"])
        self.assertFalse(config["alert_cannon_boundary"]["adaptive_or_model_suppression_used"])
        self.assertTrue(config["alert_cannon_boundary"]["static_caps_only"])

    def test_run_envelopes_jsonl_has_one_envelope_per_tick(self):
        envelopes = self.read_jsonl("WATCH_SERVICE_RUN_ENVELOPES.jsonl")
        throttle = self.read_json("WATCH_SERVICE_THROTTLE_REPORT.json")
        self.assertGreaterEqual(len(envelopes), 2)
        self.assertEqual(throttle["tick_count"], len(envelopes))
        for envelope in envelopes:
            self.assertEqual("citybrain.agent_run_envelope.v1", envelope["schema_version"])
            self.assertEqual("watch_scout", envelope["component_id"])
            self.assertEqual("watch_scout_service", envelope["service_id"])
            self.assertEqual("local_replay_review_query_only", envelope["scope"])
            self.assertEqual(1, envelope["authority_level"])
            self.assertEqual(0, envelope["budget"]["max_llm_calls"])
            self.assertTrue(envelope["check_report_refs"])
            self.assertTrue(envelope["authority_envelope_refs"])
            self.assertEqual(["WatchItem"], envelope["output_packet_types"])
            self.assertIn("suppressed_deferred_throttled_counts", envelope)

    def test_throttle_report_proves_caps_dedupe_and_operator_throttle(self):
        report = self.read_json("WATCH_SERVICE_THROTTLE_REPORT.json")
        self.assertEqual(PASS_STATUS, report["status"])
        checks = report["checks"]
        self.assertTrue(checks["at_least_two_ticks"])
        self.assertTrue(checks["one_agent_run_envelope_per_tick"])
        self.assertTrue(checks["watch_items_only"])
        self.assertTrue(checks["no_findings_or_official_actions"])
        self.assertTrue(checks["all_watch_items_have_check_and_authority_refs"])
        self.assertTrue(checks["global_caps_enforced"])
        self.assertTrue(checks["per_family_caps_enforced"])
        self.assertTrue(checks["dedupe_emitted_suppression"])
        self.assertTrue(checks["operator_throttle_state_consumed"])
        self.assertTrue(checks["no_learned_ranking_or_adaptive_suppression"])
        self.assertGreater(report["aggregate_counts"]["emitted"], 0)
        self.assertGreater(report["aggregate_counts"]["suppressed"], 0)
        self.assertTrue(report["aggregate_counts"]["throttled"] > 0 or report["aggregate_counts"]["deferred"] > 0)
        self.assertIn(report["service_health_state"], {"healthy", "degraded"})

    def test_emitted_items_are_checked_watch_items_only(self):
        report = self.read_json("WATCH_SERVICE_THROTTLE_REPORT.json")
        for tick in report["ticks"]:
            self.assertLessEqual(tick["counts"]["emitted"], tick["caps"]["global_emit_cap"])
            for family, count in tick["family_emitted_counts"].items():
                self.assertLessEqual(count, tick["caps"]["family_emit_cap"], family)
            for item in tick["emitted_watch_items"]:
                self.assertEqual("WatchItem", item["packet_type"])
                self.assertEqual("WatchItem", item["output_type"])
                self.assertTrue(item["watch_item_id"].startswith("watch-item:epoch2_2b:lane_a"))
                self.assertTrue(item["check_report_ref"])
                self.assertTrue(item["authority_envelope_ref"])
                self.assertTrue(item["not_official"])
                self.assertTrue(item["not_executed"])
                self.assertFalse(item["attempts_authority_or_review_truth_change"])
                self.assertTrue(item["safe_next_looks"])
                self.assertNotIn("finding", item)
                self.assertNotIn("official_action", item)

    def test_negative_tests_reject_required_cases(self):
        report = self.read_json("WATCH_SERVICE_NEGATIVE_TEST_REPORT.json")
        self.assertEqual("PASS", report["status"])
        fixtures = {row["fixture_id"]: row for row in report["fixtures"]}
        expected = {
            "service_tick_without_agent_run_envelope",
            "over_cap_emits_throttled_status_not_extra_items",
            "duplicate_item_deduped",
            "watch_item_without_check_report_fails",
            "service_attempting_authority_or_review_truth_change_fails",
        }
        self.assertEqual(expected, set(fixtures))
        for fixture_id, row in fixtures.items():
            self.assertEqual("PASS", row["status"], fixture_id)
        self.assertEqual("REJECTED", fixtures["service_tick_without_agent_run_envelope"]["actual"])
        self.assertEqual("THROTTLED_NOT_EMITTED", fixtures["over_cap_emits_throttled_status_not_extra_items"]["actual"])
        self.assertEqual("DEDUPED", fixtures["duplicate_item_deduped"]["actual"])
        self.assertEqual("REJECTED", fixtures["watch_item_without_check_report_fails"]["actual"])
        self.assertEqual("REJECTED", fixtures["service_attempting_authority_or_review_truth_change_fails"]["actual"])

    def test_decision_preserves_boundaries(self):
        decision = self.read_json("WATCH_SCOUT_SERVICE_DECISION.json")
        self.assertEqual(PASS_STATUS, decision["status"])
        self.assertEqual(PASS_CODE, decision["decision_code"])
        self.assertEqual(2, decision["tick_count"])
        self.assertEqual([], decision["blockers"])
        self.assertTrue(decision["boundaries"]["local_replay_review_query_only"])
        self.assertFalse(decision["boundaries"]["findings_emitted"])
        self.assertFalse(decision["boundaries"]["official_action_ticket_case_dispatch_enforcement_created"])
        self.assertFalse(decision["boundaries"]["legal_or_certified_finding_created"])
        self.assertFalse(decision["boundaries"]["authority_above_level_3"])
        self.assertFalse(decision["boundaries"]["learned_ranking_prediction_or_trained_model_created"])
        self.assertFalse(decision["boundaries"]["adaptive_or_model_suppression_created"])
        self.assertFalse(decision["boundaries"]["dynamic_investigation_created"])
        self.assertFalse(decision["boundaries"]["per_domain_agent_classes_created"])

    def test_hash_manifest_covers_required_artifacts(self):
        manifest = self.read_json("HASH_MANIFEST.json")
        paths = {row["path"] for row in manifest["files"]}
        for name in REQUIRED_ARTIFACTS:
            if name != "HASH_MANIFEST.json":
                self.assertIn(name, paths)
        self.assertEqual(len(paths), manifest["item_count"])


if __name__ == "__main__":
    unittest.main()

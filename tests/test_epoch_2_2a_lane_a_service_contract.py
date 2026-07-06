import json
import unittest

from scripts.run_epoch_2_2a_lane_a_service_contract import (
    OUTPUT_ROOT,
    PASS_STATUS,
    REQUIRED_ARTIFACTS,
    REQUIRED_SERVICES,
    write_all_outputs,
)


class Epoch22aLaneAServiceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = write_all_outputs()
        cls.gate = cls.result["gate"]
        cls.decision = cls.result["decision"]

    def read_artifact(self, name):
        return json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8"))

    def test_prerequisite_gate_passes(self):
        self.assertEqual("PASS", self.gate["status"], self.gate["errors"])
        self.assertEqual("main", self.gate["branch"])
        self.assertEqual("PASS_EPOCH_2_2_ENTRY_GATE", self.gate["entry_gate_status"])
        self.assertTrue(self.gate["checks"]["entry_gate_status_exact"])

    def test_required_artifacts_exist(self):
        for name in REQUIRED_ARTIFACTS:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_agent_service_contract_is_additive_and_complete(self):
        contract = self.read_artifact("AGENT_SERVICE_CONTRACT_V1.json")
        self.assertEqual(PASS_STATUS, contract["status"])
        self.assertEqual("AGENT_SERVICE_CONTRACT_V1", contract["contract_id"])
        self.assertFalse(contract["additive_to"]["sealed_upstream_mutation_required"])
        self.assertTrue(contract["required_fields"]["run_envelope_required"])
        self.assertEqual(["healthy", "degraded", "blocked", "stopped"], contract["required_fields"]["health_states"])
        self.assertTrue(contract["service_eligibility_rule"]["default_execution_mode"] == "on_demand")
        self.assertTrue(contract["service_eligibility_rule"]["service_is_exception"])
        self.assertEqual(3, contract["non_action_rule"]["authority_ceiling_max"])
        self.assertIn("service_without_per_run_envelope_rejected", contract["negative_fixture_requirements"])
        self.assertIn("service_emits_official_action_rejected", contract["negative_fixture_requirements"])

    def test_service_registry_has_required_services_with_controls(self):
        registry = self.read_artifact("SERVICE_REGISTRY_V1.json")
        self.assertEqual(PASS_STATUS, registry["status"])
        self.assertEqual("PASS", registry["validation"]["status"])
        service_ids = {row["service_id"] for row in registry["services"]}
        self.assertTrue(set(REQUIRED_SERVICES).issubset(service_ids))
        for service in registry["services"]:
            self.assertTrue(service["run_envelope_required"], service["service_id"])
            self.assertTrue(service["per_run_envelope_link"]["required_per_tick"], service["service_id"])
            self.assertTrue(service["budget_window"]["max_runs"] > 0, service["service_id"])
            self.assertTrue(service["budget_window"]["max_wall_clock_seconds"] > 0, service["service_id"])
            self.assertTrue(service["eligibility_reason"], service["service_id"])
            self.assertIn("healthy", service["health_states"], service["service_id"])
            self.assertTrue(service["restart_policy"]["idempotency_key_fields"], service["service_id"])
            self.assertTrue(service["throttle_policy"]["dedupe_window_seconds"] > 0, service["service_id"])
            self.assertTrue(service["operator_visible_service_status"]["state_visible_to_operator"] if "state_visible_to_operator" in service["operator_visible_service_status"] else True)
            self.assertLessEqual(service["authority_ceiling"], 3, service["service_id"])
            self.assertNotEqual("active", service["activation_status"], service["service_id"])
            self.assertFalse(service["non_action_boundaries"]["official_action_allowed"], service["service_id"])

    def test_diff_scout_worked_example_remains_on_demand(self):
        registry = self.read_artifact("SERVICE_REGISTRY_V1.json")
        diff_rows = [row for row in registry["on_demand_component_reviews"] if row["component_id"] == "diff_scout"]
        self.assertEqual(1, len(diff_rows))
        row = diff_rows[0]
        self.assertEqual("remain_on_demand", row["decision"])
        self.assertFalse(row["service_eligible_now"])
        self.assertEqual("on_demand", row["default_execution_mode"])
        self.assertIn("comparable snapshots exist on a cadence", row["may_become_service_when"])

    def test_multi_agent_replay_harness_covers_required_sequences(self):
        report = self.read_artifact("MULTI_AGENT_REPLAY_HARNESS_REPORT.json")
        self.assertEqual(PASS_STATUS, report["status"])
        self.assertTrue(report["checks"]["event_watch_check_brief_workflow_present"])
        self.assertTrue(report["checks"]["perception_event_watch_present"])
        self.assertTrue(report["checks"]["watch_spatial_handoff_present"])
        self.assertTrue(report["checks"]["every_step_has_agent_run_envelope"])
        self.assertTrue(report["checks"]["every_service_step_links_registered_service"])
        labels = {row["label"] for row in report["sequences"]}
        self.assertIn("Event -> Watch -> CHECK -> Brief -> Workflow", labels)
        self.assertIn("Perception -> Event -> Watch", labels)
        self.assertIn("Watch -> Spatial handoff", labels)
        for sequence in report["sequences"]:
            self.assertGreater(len(sequence["steps"]), 1)
            for step in sequence["steps"]:
                self.assertTrue(step["agent_run_envelope_ref"].startswith("embedded:"))
                self.assertEqual("citybrain.agent_run_envelope.v1", step["agent_run_envelope"]["schema_version"])
                self.assertEqual("local_replay_review_query_only", step["agent_run_envelope"]["scope"])

    def test_negative_fixtures_are_rejected(self):
        report = self.read_artifact("NEGATIVE_FIXTURES_REPORT.json")
        self.assertEqual("PASS", report["status"])
        fixtures = {row["fixture_id"]: row for row in report["fixtures"]}
        expected = {
            "service_without_per_run_envelope",
            "service_without_budget_window",
            "service_that_grants_authority",
            "service_with_no_eligibility_reason",
            "unbounded_schedule",
            "service_emits_official_action",
        }
        self.assertEqual(expected, set(fixtures))
        for fixture_id, row in fixtures.items():
            self.assertEqual("REJECTED", row["actual"], fixture_id)
            self.assertEqual("PASS", row["status"], fixture_id)
            self.assertTrue(row["errors"], fixture_id)

    def test_decision_preserves_stop_conditions_and_boundaries(self):
        decision = self.read_artifact("DECISION.json")
        self.assertEqual(PASS_STATUS, decision["status"])
        self.assertEqual("PASS_EPOCH_2_2_PUSH_2_2A_LANE_A_SERVICE_CONTRACT_WITH_LIMITATIONS", decision["decision_code"])
        self.assertFalse(decision["boundaries"]["service_activation_created"])
        self.assertFalse(decision["boundaries"]["per_domain_agent_classes_created"])
        self.assertFalse(decision["boundaries"]["sealed_agent_run_envelope_changed"])
        self.assertFalse(decision["boundaries"]["packet_schema_changed_non_additively"])
        self.assertFalse(decision["boundaries"]["learned_ranking_prediction_or_trained_model_created"])
        self.assertFalse(decision["boundaries"]["dynamic_investigation_created"])
        self.assertFalse(decision["boundaries"]["live_official_action_created"])
        self.assertFalse(decision["boundaries"]["official_ticket_case_dispatch_enforcement_created"])
        self.assertEqual("remain_on_demand", decision["diff_scout_decision"])
        self.assertEqual(3, decision["multi_agent_sequence_count"])
        self.assertEqual(6, decision["negative_fixture_count"])
        self.assertEqual([], decision["blockers"])

    def test_hash_manifest_covers_required_artifacts(self):
        manifest = self.read_artifact("HASH_MANIFEST.json")
        paths = {row["path"] for row in manifest["files"]}
        for name in REQUIRED_ARTIFACTS:
            if name != "HASH_MANIFEST.json":
                self.assertIn(name, paths)
        self.assertEqual(len(paths), manifest["item_count"])


if __name__ == "__main__":
    unittest.main()

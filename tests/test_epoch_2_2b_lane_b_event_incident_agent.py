import json
import unittest

from scripts.run_epoch_2_2b_lane_b_event_incident_agent import (
    NON_GOALS,
    OUTPUT_ROOT,
    PASS_STATUS,
    check_prerequisite_gate,
    validate_outputs,
    write_all_outputs,
)


class Epoch22bLaneBEventIncidentAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = write_all_outputs()
        cls.gate = cls.result["gate"]
        cls.decision = cls.result["decision"]
        cls.handoff = cls.result["handoff"]
        cls.negative = cls.result["negative"]

    def test_prerequisite_gate_passes(self):
        self.assertEqual("PASS", self.gate["status"], self.gate["errors"])
        self.assertEqual("main", self.gate["branch"])
        self.assertEqual("PASS_PUSH_2_2A_INTEGRATION", self.gate["integration_status"])
        self.assertEqual("PASS", self.gate["allowed_flag_value"])

    def test_required_artifacts_exist(self):
        for name in [
            "EVENT_INCIDENT_AGENT_DECISION.json",
            "EVENT_INCIDENT_AGENT_REPORT.md",
            "EVENT_INCIDENT_AGENT_RUN_ENVELOPES.jsonl",
            "EVENT_TO_WATCH_HANDOFF_FIXTURES.json",
            "EVENT_INCIDENT_NEGATIVE_TEST_REPORT.json",
            "HASH_MANIFEST.json",
        ]:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_event_incident_service_registry_entry_is_used(self):
        service = self.handoff["event_incident_service"]
        self.assertEqual("event_incident_service", service["service_id"])
        self.assertEqual("event_triggered", service["service_kind"])
        self.assertTrue(service["check_required"])
        self.assertLessEqual(service["authority_ceiling"], 3)
        self.assertEqual("service_eligible_not_activated", service["eligibility_review"]["decision"])

    def test_resolved_and_unresolved_fixtures_processed(self):
        processed = self.handoff["processed_results"]
        self.assertGreaterEqual(len(processed), 2)
        states = {row["resolution_state"] for row in processed}
        self.assertIn("resolved", states)
        self.assertIn("unresolved", states)
        unresolved = [row for row in processed if row["resolution_state"] == "unresolved"][0]
        self.assertIsNone(unresolved["review_state_update"]["resolved_entity_ref"])
        self.assertTrue(unresolved["review_state_update"]["unresolved_reason"])

    def test_watch_handoff_is_emitted_for_resolved_case(self):
        handoffs = self.handoff["watch_handoffs"]
        self.assertTrue(handoffs)
        row = handoffs[0]
        self.assertEqual("event_incident_service", row["from_service_id"])
        self.assertEqual("watch_scout_service", row["to_service_id"])
        self.assertEqual("P1_checked_candidate", row["priority_tier"])
        self.assertTrue(row["not_official"])
        self.assertTrue(row["not_executed"])
        self.assertTrue(row["no_dispatch_control_enforcement"])

    def test_run_envelopes_have_check_authority_and_boundaries(self):
        lines = (OUTPUT_ROOT / "EVENT_INCIDENT_AGENT_RUN_ENVELOPES.jsonl").read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(2, len(lines))
        envelopes = [json.loads(line) for line in lines]
        for envelope in envelopes:
            self.assertEqual("citybrain.agent_run_envelope.v1", envelope["schema_version"])
            self.assertEqual("event_incident_agent", envelope["component_id"])
            self.assertEqual("event_incident_service", envelope["service_id"])
            self.assertEqual("local_replay_review_query_only", envelope["scope"])
            self.assertLessEqual(envelope["authority_level"], 3)
            self.assertTrue(envelope["check_report_refs"])
            self.assertTrue(envelope["authority_envelope_refs"])
            self.assertTrue(envelope["evidence_refs"])
            self.assertIn("EventReviewState", "".join(envelope["outputs"]))
            self.assertNotIn("OfficialAction", envelope["outputs"])
            self.assertEqual(0, envelope["budget"]["max_llm_calls"])

    def test_negative_tests_reject_unsafe_paths(self):
        self.assertEqual("PASS", self.negative["status"])
        errors_by_fixture = {row["fixture_id"]: row["errors"] for row in self.negative["results"]}
        self.assertIn("missing_evidence_refs", errors_by_fixture["negative:event_incident:missing_evidence"])
        self.assertIn("vss_model_narrative_as_fact_source_rejected", errors_by_fixture["negative:event_incident:vss_fact_source"])
        self.assertIn("official_action_affordance_rejected", errors_by_fixture["negative:event_incident:official_action"])
        self.assertIn("live_production_event_source_rejected", errors_by_fixture["negative:event_incident:live_source"])
        self.assertIn("missing_event_id", errors_by_fixture["negative:event_incident:malformed"])
        self.assertIn("service_authority_ceiling_above_3_rejected", errors_by_fixture["negative:event_incident:authority_above_3"])

    def test_decision_boundaries_and_validation(self):
        decision = json.loads((OUTPUT_ROOT / "EVENT_INCIDENT_AGENT_DECISION.json").read_text(encoding="utf-8"))
        validation = validate_outputs(self.handoff, self.negative)
        self.assertEqual("PASS", validation["status"], validation["errors"])
        self.assertEqual(PASS_STATUS, decision["status"])
        self.assertFalse(decision["boundaries"]["official_incident_claim_emitted"])
        self.assertFalse(decision["boundaries"]["legal_finding_emitted"])
        self.assertFalse(decision["boundaries"]["dispatch_control_enforcement_emitted"])
        self.assertFalse(decision["boundaries"]["live_production_event_source_used"])
        self.assertFalse(decision["boundaries"]["vss_model_narrative_used_as_fact_source"])
        self.assertFalse(decision["boundaries"]["official_action_affordance_emitted"])
        self.assertFalse(decision["boundaries"]["per_domain_agent_classes_created"])
        self.assertFalse(decision["boundaries"]["learned_ranking_prediction_trained_model_or_dynamic_investigation_created"])
        self.assertTrue(decision["boundaries"]["local_replay_review_query_only"])
        self.assertEqual(NON_GOALS, decision["non_goals"])

    def test_hash_manifest_covers_required_outputs(self):
        manifest = json.loads((OUTPUT_ROOT / "HASH_MANIFEST.json").read_text(encoding="utf-8"))
        paths = {row["path"] for row in manifest["files"]}
        for name in [
            "EVENT_INCIDENT_AGENT_DECISION.json",
            "EVENT_INCIDENT_AGENT_REPORT.md",
            "EVENT_INCIDENT_AGENT_RUN_ENVELOPES.jsonl",
            "EVENT_TO_WATCH_HANDOFF_FIXTURES.json",
            "EVENT_INCIDENT_NEGATIVE_TEST_REPORT.json",
        ]:
            self.assertIn(name, paths)
        self.assertEqual(5, manifest["item_count"])


if __name__ == "__main__":
    unittest.main()

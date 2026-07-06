import json
import unittest

from scripts.run_epoch_2_2c_lane_a_pack_spatial import (
    DOMAINS,
    OUTPUT_ROOT,
    PASS_CODE,
    PASS_STATUS,
    REQUIRED_ARTIFACTS,
    write_all_outputs,
)


class Epoch22cLaneAPackSpatialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = write_all_outputs()
        cls.gate = cls.result["gate"]
        cls.report = cls.result["report"]

    def read_json(self, name):
        return json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8"))

    def test_prerequisite_gate_passes(self):
        self.assertEqual("PASS", self.gate["status"], self.gate["errors"])
        self.assertEqual("main", self.gate["branch"])
        self.assertEqual("PASS_PUSH_2_2B_INTEGRATION", self.gate["integration_status"])
        self.assertEqual("PASS", self.gate["flag_value"])

    def test_required_artifacts_exist(self):
        for name in REQUIRED_ARTIFACTS:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_starter_pack_agent_consumer_matrix_covers_four_packs(self):
        matrix = self.read_json("STARTER_PACK_AGENT_CONSUMER_MATRIX.json")
        self.assertEqual(PASS_STATUS, matrix["status"])
        self.assertEqual(set(DOMAINS), {row["domain"] for row in matrix["rows"]})
        self.assertTrue(matrix["checks"]["four_starter_packs_present"])
        self.assertTrue(matrix["checks"]["no_per_domain_agent_classes"])
        self.assertTrue(matrix["checks"]["all_packs_have_consuming_capability"])
        self.assertTrue(matrix["checks"]["all_packs_have_eval_harness_link"])
        self.assertTrue(matrix["checks"]["all_packs_have_check_authority_coverage"])
        self.assertTrue(matrix["checks"]["ask_templates_served_where_defined"])
        self.assertTrue(matrix["checks"]["watch_families_served_where_defined"])
        self.assertTrue(matrix["checks"]["event_types_served_where_defined"])
        self.assertTrue(matrix["checks"]["brief_profiles_served_where_defined"])
        for row in matrix["rows"]:
            self.assertEqual("PASS", row["status"], row["domain"])
            runtime = row["cross_cutting_runtime"]
            self.assertEqual("DomainPackParameterizedAgentRuntime", runtime["class_name"])
            self.assertFalse(runtime["per_domain_agent_class_created"])
            self.assertTrue(row["consuming_capability"]["exists"])
            self.assertEqual("LINKED_TO_MODE_LEVEL_HARNESS", row["eval_fixtures"]["status"])
            self.assertTrue(row["check_authority_coverage"]["requires_check_report"])
            self.assertTrue(row["check_authority_coverage"]["requires_authority_envelope"])
            self.assertFalse(row["check_authority_coverage"]["official_or_legal_conclusion_allowed"])

    def test_cross_cutting_services_are_used_where_pack_defines_refs(self):
        matrix = self.read_json("STARTER_PACK_AGENT_CONSUMER_MATRIX.json")
        for row in matrix["rows"]:
            self.assertEqual("ask_resolver_renderer", row["ask_templates"]["component_id"])
            self.assertEqual("AskResolver", row["ask_templates"]["cross_cutting_agent_class"])
            if row["watch_families"]["refs"]:
                self.assertEqual("watch_scout_service", row["watch_families"]["service_id"])
                self.assertEqual("WatchScout", row["watch_families"]["cross_cutting_agent_class"])
            if row["event_types"]["refs"]:
                self.assertEqual("event_incident_service", row["event_types"]["service_id"])
                self.assertEqual("EventIncidentAgent", row["event_types"]["cross_cutting_agent_class"])
            if row["brief_profiles"]["refs"]:
                self.assertEqual("briefing_service", row["brief_profiles"]["service_id"])
                self.assertEqual("BriefingAgent", row["brief_profiles"]["cross_cutting_agent_class"])

    def test_spatial_handoff_fixtures_have_packet_overlay_and_envelope(self):
        fixtures = self.read_json("SPATIAL_HANDOFF_FIXTURES.json")
        self.assertEqual(PASS_STATUS, fixtures["status"])
        self.assertEqual(4, fixtures["handoff_count"])
        self.assertTrue(fixtures["checks"]["spatial_handoff_service_registry_entry_used"])
        self.assertTrue(fixtures["checks"]["one_handoff_per_starter_pack"])
        self.assertTrue(fixtures["checks"]["agent_run_envelope_per_handoff"])
        self.assertTrue(fixtures["checks"]["all_handoffs_have_check_authority_refs"])
        self.assertTrue(fixtures["checks"]["no_live_control_or_action_claim"])
        for handoff in fixtures["handoffs"]:
            self.assertEqual("PASS", handoff["status"], handoff["domain"])
            packet = handoff["spatial_selection_packet"]
            overlay = handoff["kit_web_overlay_handoff"]
            envelope = handoff["agent_run_envelope"]
            self.assertEqual("SpatialSelectionPacket", packet["packet_type"])
            self.assertTrue(packet["canonical_entity_id"])
            self.assertTrue(packet["evidence_refs"])
            self.assertTrue(packet["check_report_ref"])
            self.assertTrue(packet["authority_envelope_ref"])
            self.assertEqual("candidate_review_only", packet["review_state"])
            self.assertTrue(packet["not_executed"])
            self.assertTrue(packet["no_live_control_claim"])
            self.assertFalse(packet["no_action_boundary"]["official_action_created"])
            self.assertFalse(overlay["live_control_claim"])
            self.assertFalse(overlay["production_kit_web_control_claim"])
            self.assertTrue(overlay["overlay_refs"])
            self.assertEqual("citybrain.agent_run_envelope.v1", envelope["schema_version"])
            self.assertEqual("spatial_agent", envelope["component_id"])
            self.assertEqual("spatial_handoff_service", envelope["service_id"])
            self.assertEqual("local_replay_review_query_only", envelope["scope"])
            self.assertEqual(1, envelope["authority_level"])
            self.assertTrue(envelope["check_report_refs"])
            self.assertTrue(envelope["authority_envelope_refs"])

    def test_spatial_service_report_preserves_boundaries(self):
        report = self.read_json("SPATIAL_AGENT_SERVICE_REPORT.json")
        self.assertEqual(PASS_STATUS, report["status"])
        self.assertEqual("spatial_handoff_service", report["service_id"])
        self.assertEqual("spatial_agent", report["component_id"])
        self.assertEqual("local_replay_review_query_service_activation", report["activation_mode"])
        self.assertEqual(4, report["handoff_count"])
        self.assertEqual(4, report["agent_run_envelope_count"])
        self.assertTrue(report["boundaries"]["local_replay_review_query_only"])
        self.assertFalse(report["boundaries"]["production_kit_web_control_claim"])
        self.assertFalse(report["boundaries"]["official_action_ticket_dispatch_enforcement_created"])
        self.assertFalse(report["boundaries"]["legal_or_certified_finding_created"])
        self.assertFalse(report["boundaries"]["trained_ranking_prediction_counterfactual_or_dynamic_investigation_created"])

    def test_negative_tests_reject_required_cases(self):
        negative = self.read_json("NEGATIVE_TEST_REPORT.json")
        self.assertEqual("PASS", negative["status"])
        rows = {row["fixture_id"]: row for row in negative["results"]}
        expected = {
            "new_domain_specific_agent_class_detected",
            "pack_has_no_consuming_capability",
            "spatial_handoff_missing_check_authority_refs",
            "kit_web_handoff_claims_live_control",
        }
        self.assertEqual(expected, set(rows))
        for fixture_id, row in rows.items():
            self.assertEqual("REJECTED", row["actual"], fixture_id)
            self.assertEqual("PASS", row["status"], fixture_id)
            self.assertTrue(row["errors"], fixture_id)

    def test_pack_report_decision_and_boundaries(self):
        report = self.read_json("PACK_PARAMETERIZED_AGENT_REPORT.json")
        self.assertEqual(PASS_STATUS, report["status"])
        self.assertEqual(PASS_CODE, report["decision_code"])
        self.assertEqual([], report["blockers"])
        self.assertEqual(set(DOMAINS), set(report["domains"]))
        self.assertEqual([], report["domain_specific_agent_classes_detected"])
        self.assertEqual(4, report["spatial_handoff_count"])
        self.assertTrue(report["checks"]["all_four_packs_active"])
        self.assertTrue(report["checks"]["all_handoffs_have_envelopes"])
        self.assertTrue(report["checks"]["no_live_control_claim"])
        self.assertTrue(report["boundaries"]["local_replay_review_query_only"])
        self.assertFalse(report["boundaries"]["per_domain_agent_classes_created"])
        self.assertFalse(report["boundaries"]["official_action_ticket_dispatch_enforcement_created"])
        self.assertFalse(report["boundaries"]["legal_or_certified_finding_created"])
        self.assertFalse(report["boundaries"]["trained_ranking_prediction_counterfactual_or_dynamic_investigation_created"])
        self.assertFalse(report["boundaries"]["production_kit_web_control_claim"])

    def test_hash_manifest_covers_required_artifacts(self):
        manifest = self.read_json("HASH_MANIFEST.json")
        self.assertEqual("PASS", manifest["status"])
        paths = {row["path"] for row in manifest["files"]}
        for name in REQUIRED_ARTIFACTS:
            if name != "HASH_MANIFEST.json":
                self.assertIn(name, paths)
        self.assertEqual(len(paths), manifest["item_count"])


if __name__ == "__main__":
    unittest.main()

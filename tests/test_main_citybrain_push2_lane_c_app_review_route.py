import json
import shutil
import unittest

from scripts.run_main_citybrain_push2_lane_c_app_review_route import (
    CLOSEOUT_ROOT,
    DISPOSITIONS,
    FINAL_ROOT,
    OUTPUT_ROOT,
    PASS_STATUS,
    REQUIRED_CLOSEOUT_OUTPUTS,
    REQUIRED_FINAL_OUTPUTS,
    REQUIRED_OUTPUTS,
    build_fixtures,
    entry_gate_report,
    verify_hash_manifest,
    write_all_outputs,
)


class MainCityBrainPush2LaneCAppReviewRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for root in [OUTPUT_ROOT, CLOSEOUT_ROOT, FINAL_ROOT]:
            if root.exists():
                shutil.rmtree(root)
        cls.all_outputs = write_all_outputs({"runner": "TEST_SETUP"})
        cls.bundle = cls.all_outputs["bundle"]
        cls.closeout = cls.all_outputs["closeout"]
        cls.final = cls.all_outputs["final"]
        cls.fixtures = json.loads((OUTPUT_ROOT / "APP_REVIEW_ROUTE_FIXTURES.json").read_text(encoding="utf-8"))
        cls.render_state = json.loads((OUTPUT_ROOT / "APP_REVIEW_ROUTE_RENDER_STATE_REPORT.json").read_text(encoding="utf-8"))
        cls.dispositions = json.loads((OUTPUT_ROOT / "APP_REVIEW_ROUTE_DISPOSITION_EVENT_FIXTURES.json").read_text(encoding="utf-8"))
        cls.boundary = json.loads((OUTPUT_ROOT / "APP_REVIEW_ROUTE_BOUNDARY_AUDIT.json").read_text(encoding="utf-8"))

    def test_entry_gates_pass_with_branch_available_inputs(self):
        gates = entry_gate_report()
        self.assertEqual("PASS", gates["status"], gates)
        self.assertTrue(all(gate["status"] == "PASS" for gate in gates["gates"]))

    def test_required_outputs_exist(self):
        for name in REQUIRED_OUTPUTS:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        self.assertTrue((OUTPUT_ROOT / "APP_REVIEW_ROUTE_STATIC_WORKSPACE.html").exists())
        self.assertTrue((OUTPUT_ROOT / "APP_REVIEW_ROUTE_EVENT_FABRIC_APPEND_LOG.jsonl").exists())

    def test_required_closeout_and_final_outputs_exist(self):
        for name in REQUIRED_CLOSEOUT_OUTPUTS:
            self.assertTrue((CLOSEOUT_ROOT / name).exists(), name)
        for name in REQUIRED_FINAL_OUTPUTS:
            self.assertTrue((FINAL_ROOT / name).exists(), name)
        self.assertEqual(PASS_STATUS, self.closeout["decision"]["status"])
        self.assertEqual(PASS_STATUS, self.final["decision"]["status"])

    def test_perception_and_watch_items_are_visible(self):
        self.assertEqual(PASS_STATUS, self.bundle["decision"]["status"])
        self.assertTrue(self.render_state["perception_items_visible"])
        self.assertGreaterEqual(self.render_state["perception_item_count"], 1)
        self.assertTrue(self.render_state["watch_items_visible"])
        self.assertGreaterEqual(self.render_state["watch_item_count"], 1)
        kinds = {item["item_kind"] for item in self.fixtures["review_items"]}
        self.assertIn("perception_item", kinds)
        self.assertIn("watch_item", kinds)

    def test_selected_item_panel_shows_required_refs_and_boundaries(self):
        panel = self.render_state["selected_review_item_panel"]
        self.assertTrue(panel["visible"])
        self.assertTrue(panel["candidate_observation_display_visible"])
        self.assertTrue(panel["evidence_refs_visible"])
        self.assertTrue(panel["limitation_refs_visible"])
        self.assertTrue(panel["trace_refs_visible"])
        self.assertTrue(panel["source_class_visible"])
        self.assertTrue(panel["cannot_claim_visible"])
        self.assertTrue(panel["not_executed_visible"])
        self.assertTrue(panel["safe_next_looks_visible"])
        self.assertTrue(panel["spatial_overlay_reference_visible"])

    def test_check_report_and_authority_envelope_are_visible(self):
        panel = self.render_state["selected_review_item_panel"]
        self.assertTrue(panel["check_report_visible"])
        self.assertTrue(panel["authority_envelope_visible"])
        self.assertEqual(len(self.fixtures["review_items"]), len(self.fixtures["check_reports"]))
        self.assertEqual(len(self.fixtures["review_items"]), len(self.fixtures["authority_envelopes"]))
        for envelope in self.fixtures["authority_envelopes"]:
            self.assertFalse(envelope["official_action_allowed"])
            self.assertFalse(envelope["official_record_created"])
            self.assertIn("reviewer", envelope["individual_visibility_roles"])
            self.assertIn("analytics", envelope["aggregate_visibility_roles"])

    def test_disposition_event_registry_payload_and_note_preservation(self):
        registry = self.dispositions["event_type_registry"][0]
        self.assertEqual("EventTypeRegistry", registry["registry_name"])
        self.assertEqual("review_item.disposition_recorded", registry["event_type"])
        self.assertFalse(registry["new_top_level_frozen_contract"])
        self.assertEqual(DISPOSITIONS, registry["disposition_enum"])
        for field in ["target_ref", "disposition", "operator_ref", "timestamp", "note"]:
            self.assertIn(field, registry["payload_required"])
        event = self.dispositions["disposition_events"][0]
        self.assertEqual("review_item.disposition_recorded", event["event_type"])
        self.assertEqual("needs_more", event["payload"]["disposition"])
        self.assertEqual("Need sharper retained evidence before any claim is promoted.", event["payload"]["note"])
        self.assertTrue(event["payload"]["operator_ref"].startswith("operator:local-reviewer"))

    def test_disposition_events_write_back_to_local_event_fabric_log(self):
        log_path = OUTPUT_ROOT / "APP_REVIEW_ROUTE_EVENT_FABRIC_APPEND_LOG.jsonl"
        events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(self.dispositions["disposition_events"]), len(events))
        self.assertTrue(all(event["event_type"] == "review_item.disposition_recorded" for event in events))
        self.assertTrue(all(event["event_hash"] for event in events))
        self.assertTrue(self.dispositions["event_fabric_writeback"]["all_events_written"])

    def test_no_official_action_ticket_dispatch_or_live_api_affordance(self):
        self.assertEqual("PASS", self.boundary["status"], self.boundary)
        self.assertTrue(self.boundary["no_official_action_ticket_dispatch_affordance"])
        self.assertTrue(self.boundary["no_live_api_url_llm"])
        self.assertTrue(self.boundary["no_sealed_ask_runtime_mutation"])
        self.assertTrue(self.boundary["no_r7_runtime_mutation"])
        forbidden = self.render_state["forbidden_affordances_visible"]
        self.assertFalse(any(forbidden.values()), forbidden)

    def test_static_route_contains_dom_assertion_markers(self):
        html = (OUTPUT_ROOT / "APP_REVIEW_ROUTE_STATIC_WORKSPACE.html").read_text(encoding="utf-8")
        self.assertIn('data-app-review-route="true"', html)
        self.assertIn('data-route-path="/review"', html)
        self.assertIn('data-check-report-visible="true"', html)
        self.assertIn('data-authority-envelope-visible="true"', html)
        self.assertIn('data-disposition-capture-visible="true"', html)
        self.assertIn('data-item-kind="perception_item"', html)
        self.assertIn('data-item-kind="watch_item"', html)

    def test_hash_manifest_verifies(self):
        report = verify_hash_manifest()
        self.assertEqual("PASS", report["status"], report)
        self.assertEqual(report["declared"], report["verified"])

    def test_closeout_and_final_hash_manifests_verify(self):
        reports = [
            verify_hash_manifest(CLOSEOUT_ROOT, "APP_REVIEW_ROUTE_CLOSEOUT_HASH_MANIFEST.json"),
            verify_hash_manifest(FINAL_ROOT, "APP_REVIEW_ROUTE_FINAL_STATUS_HASH_MANIFEST.json"),
        ]
        for report in reports:
            self.assertEqual("PASS", report["status"], report)
            self.assertEqual(report["declared"], report["verified"])

    def test_build_fixtures_does_not_require_network_or_llm(self):
        fixture = build_fixtures({"runner": "UNIT"})
        serialized = json.dumps(fixture, sort_keys=True).lower()
        self.assertIn("no production api", serialized)
        self.assertTrue(fixture["boundary"]["no_live_api_url_llm"])
        self.assertNotIn('"execution_status": "executed"', serialized)
        self.assertNotIn('"official_status": "official"', serialized)


if __name__ == "__main__":
    unittest.main()

import json
import unittest

from scripts.run_epoch_2_1b_lane_a_rbac_audit_observability import (
    OUTPUT_ROOT,
    PASS_STATUS,
    REQUIRED_AUDIT_EVENTS,
    REQUIRED_ROLES,
    build_outputs,
    prerequisite_gate,
    verify_hash_manifest,
)


class Epoch21bLaneARbacAuditObservabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = build_outputs()
        cls.rbac = json.loads((OUTPUT_ROOT / "rbac_policy_matrix_v1.json").read_text(encoding="utf-8"))
        cls.taxonomy = json.loads((OUTPUT_ROOT / "audit_event_taxonomy_v1.json").read_text(encoding="utf-8"))
        cls.observability = json.loads((OUTPUT_ROOT / "observability_envelope_v1.json").read_text(encoding="utf-8"))
        cls.validation = json.loads((OUTPUT_ROOT / "rbac_audit_validation_report.json").read_text(encoding="utf-8"))

    def test_prerequisite_gate_passes(self):
        gate = prerequisite_gate()
        self.assertEqual("PASS", gate["status"], gate)
        self.assertTrue(gate["checks"]["branch_is_main"])
        self.assertTrue(gate["checks"]["push_2_1b_allowed_to_open"])

    def test_required_artifacts_exist(self):
        for name in [
            "rbac_baseline_v1.md",
            "rbac_policy_matrix_v1.json",
            "audit_event_taxonomy_v1.json",
            "observability_envelope_v1.json",
            "rbac_audit_validation_report.json",
            "PUSH_2_1B_LANE_A_DECISION.json",
            "HASH_MANIFEST.json",
            "SUMMARY.md",
        ]:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_required_roles_and_admin_scoped_operator_data(self):
        roles = {row["role_id"]: row for row in self.rbac["roles"]}
        self.assertTrue(set(REQUIRED_ROLES).issubset(roles))
        self.assertTrue(roles["admin"]["can_view_operator_level_data"])
        for role_id, row in roles.items():
            if role_id != "admin":
                self.assertFalse(row["can_view_operator_level_data"], role_id)
        self.assertEqual("none", roles["external_viewer_read_only"]["write_capability"])

    def test_required_audit_events_present_and_non_official(self):
        events = {row["event_type"]: row for row in self.taxonomy["events"]}
        self.assertTrue(set(REQUIRED_AUDIT_EVENTS).issubset(events))
        self.assertTrue(all(event["official_action_created"] is False for event in events.values()))
        for event_type in REQUIRED_AUDIT_EVENTS:
            self.assertIn("audit_event_id", events[event_type]["required_fields"])

    def test_observability_envelope_is_local_replay_only(self):
        self.assertEqual("local_replay_review_query", self.observability["environment_scope"])
        lifecycle = set(self.observability["component_run_lifecycle_events"])
        self.assertEqual(
            {"agent_component_run_started", "agent_component_run_completed", "agent_component_run_blocked"},
            lifecycle,
        )
        for mapping in self.observability["component_mappings"]:
            self.assertFalse(mapping["production_monitoring_claim"])
            self.assertEqual("local_replay_redacted", mapping["log_scope"])

    def test_validation_fixtures_and_boundaries_pass(self):
        self.assertEqual("PASS", self.validation["status"], self.validation)
        self.assertTrue(all(row["status"] == "PASS" for row in self.validation["fixture_results"]))
        contract = self.decision["contract_check"]
        self.assertTrue(contract["lane_a_only"])
        self.assertTrue(contract["local_replay_review_query_only"])
        self.assertTrue(contract["no_production_user_provisioning"])
        self.assertTrue(contract["no_auth_rbac_runtime_implementation"])
        self.assertTrue(contract["no_public_api_internet_exposure_or_enterprise_hardening_claim"])
        self.assertTrue(contract["no_official_action_dispatch_enforcement_legal_ticket_case"])
        self.assertTrue(contract["no_autonomous_monitoring_or_action"])

    def test_decision_and_hash_manifest(self):
        self.assertEqual(PASS_STATUS, self.decision["status"])
        report = verify_hash_manifest()
        self.assertEqual("PASS", report["status"], report)
        self.assertEqual(report["declared"], report["verified"])


if __name__ == "__main__":
    unittest.main()

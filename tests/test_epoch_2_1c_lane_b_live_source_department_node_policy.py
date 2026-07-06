import json
import unittest

from scripts.run_epoch_2_1c_lane_b_live_source_department_node_policy import (
    DEPARTMENT_NODE_REQUIRED_FIELDS,
    LIVE_SOURCE_REQUIRED_FIELDS,
    NON_GOALS,
    OUTPUT_ROOT,
    PASS_STATUS,
    check_prerequisite_gate,
    department_node_fixture,
    load_baselines,
    policy_fixture,
    validate_department_node_record,
    validate_live_source_record,
    write_all_outputs,
)


class Epoch21cLaneBLiveSourceDepartmentNodePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = write_all_outputs()
        cls.gate = cls.result["gate"]
        cls.decision = cls.result["decision"]
        cls.baselines = cls.result["baselines"]

    def test_prerequisite_gate_passes(self):
        self.assertEqual("PASS", self.gate["status"], self.gate["errors"])
        self.assertEqual("main", self.gate["branch"])
        self.assertTrue(self.gate["gate_decision_status"].startswith("PASS"))
        self.assertTrue(self.gate["push_2_1c_allowed_to_open"])
        self.assertEqual("PASS", self.gate["gate_flag_value"])

    def test_required_artifacts_exist(self):
        for name in [
            "live_source_onboarding_policy_v1.md",
            "live_source_onboarding_schema_v1.json",
            "camera_source_registry_policy_v1.md",
            "department_local_node_strategy_v1.md",
            "department_node_manifest_schema_v1.json",
            "live_source_department_policy_validation_report.json",
            "PUSH_2_1C_LANE_B_DECISION.json",
            "HASH_MANIFEST.json",
            "SUMMARY.md",
        ]:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_live_source_schema_requires_policy_fields(self):
        schema = json.loads((OUTPUT_ROOT / "live_source_onboarding_schema_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(set(LIVE_SOURCE_REQUIRED_FIELDS), set(schema["required"]))
        for field in [
            "owner",
            "steward",
            "source_class",
            "retention_privacy_profile",
            "raw_media_policy",
            "evidence_clip_policy",
            "camera_registry",
            "health_status_metadata",
            "time_location_calibration",
            "check_detection_sufficiency",
            "candidate_observation_rule",
            "approval_gates",
            "rbac_audit_alignment",
            "enablement_boundary",
        ]:
            self.assertIn(field, schema["properties"])
        self.assertIn("just_try_one_feed_exception_requested", schema["must_not_enable_if"])

    def test_department_node_schema_requires_strategy_fields(self):
        schema = json.loads((OUTPUT_ROOT / "department_node_manifest_schema_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(set(DEPARTMENT_NODE_REQUIRED_FIELDS), set(schema["required"]))
        for field in [
            "local_registry_slice",
            "local_graph_slice",
            "component_policy",
            "dashboard_slice",
            "connector_boundary",
            "federation_handoff_contract",
            "authority_boundary",
            "rbac_audit_alignment",
            "privacy_retention_alignment",
        ]:
            self.assertIn(field, schema["properties"])
        self.assertIn("production_connector_or_public_api_requested", schema["must_not_merge_if"])

    def test_positive_fixtures_validate_against_baselines(self):
        live_result = validate_live_source_record(policy_fixture(), self.baselines)
        node_result = validate_department_node_record(department_node_fixture(), self.baselines)
        self.assertEqual("PASS", live_result["status"], live_result["errors"])
        self.assertEqual("PASS", node_result["status"], node_result["errors"])

    def test_negative_fixtures_block_shortcuts(self):
        live = policy_fixture()
        no_steward = json.loads(json.dumps(live))
        no_steward.pop("steward")
        self.assertIn("missing_required:steward", validate_live_source_record(no_steward, self.baselines)["errors"])

        feed_exception = json.loads(json.dumps(live))
        feed_exception["enablement_boundary"]["just_try_one_feed_exception_allowed"] = True
        self.assertIn("just_try_one_feed_exception_requested", validate_live_source_record(feed_exception, self.baselines)["errors"])

        live_enabled = json.loads(json.dumps(live))
        live_enabled["enablement_boundary"]["live_enabled"] = True
        self.assertIn("live_source_implementation_requested", validate_live_source_record(live_enabled, self.baselines)["errors"])

        no_check = json.loads(json.dumps(live))
        no_check["check_detection_sufficiency"]["check_report_required"] = False
        self.assertIn("missing_check_detection_sufficiency", validate_live_source_record(no_check, self.baselines)["errors"])

        node = department_node_fixture()
        node["connector_boundary"]["live_connector_implementation_allowed"] = True
        node["connector_boundary"]["public_api_or_internet_exposure_allowed"] = True
        node_result = validate_department_node_record(node, self.baselines)
        self.assertIn("live_connector_implementation_requested", node_result["errors"])
        self.assertIn("public_api_or_internet_exposure_requested", node_result["errors"])

    def test_validation_report_aligns_with_rbac_privacy_and_source_class(self):
        report = json.loads((OUTPUT_ROOT / "live_source_department_policy_validation_report.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", report["status"])
        self.assertTrue(all(report["baseline_checks"].values()), report["baseline_checks"])
        self.assertEqual("PASS", report["positive_fixture_results"]["live_source_onboarding_policy_fixture"]["status"])
        self.assertEqual("PASS", report["positive_fixture_results"]["department_local_node_policy_fixture"]["status"])
        self.assertEqual("FAIL", report["negative_fixture_results"]["just_try_one_feed_exception"]["status"])
        self.assertEqual("FAIL", report["negative_fixture_results"]["live_enabled"]["status"])
        self.assertEqual("FAIL", report["negative_fixture_results"]["production_connector_or_public_api"]["status"])

    def test_decision_preserves_boundaries(self):
        decision = json.loads((OUTPUT_ROOT / "PUSH_2_1C_LANE_B_DECISION.json").read_text(encoding="utf-8"))
        self.assertEqual(PASS_STATUS, decision["status"])
        self.assertFalse(decision["boundaries"]["live_camera_source_implementation_created"])
        self.assertFalse(decision["boundaries"]["just_try_one_feed_exception_created"])
        self.assertFalse(decision["boundaries"]["production_connector_created"])
        self.assertFalse(decision["boundaries"]["public_api_or_internet_exposure_created"])
        self.assertFalse(decision["boundaries"]["autonomous_monitoring_or_action_created"])
        self.assertFalse(decision["boundaries"]["dispatch_enforcement_ticket_case_or_legal_finding_created"])
        self.assertFalse(decision["boundaries"]["agent_activation_created"])
        self.assertTrue(decision["boundaries"]["local_replay_review_query_policy_design_only"])
        self.assertEqual(NON_GOALS, decision["limitations"])

    def test_hash_manifest_covers_required_outputs(self):
        manifest = json.loads((OUTPUT_ROOT / "HASH_MANIFEST.json").read_text(encoding="utf-8"))
        paths = {row["path"] for row in manifest["files"]}
        for name in [
            "live_source_onboarding_policy_v1.md",
            "live_source_onboarding_schema_v1.json",
            "camera_source_registry_policy_v1.md",
            "department_local_node_strategy_v1.md",
            "department_node_manifest_schema_v1.json",
            "live_source_department_policy_validation_report.json",
            "PUSH_2_1C_LANE_B_DECISION.json",
            "SUMMARY.md",
        ]:
            self.assertIn(name, paths)
        self.assertEqual(8, manifest["item_count"])


if __name__ == "__main__":
    unittest.main()

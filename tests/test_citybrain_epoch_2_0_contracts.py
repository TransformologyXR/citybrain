import json
import unittest

from scripts.citybrain_epoch_2_0_common import (
    CONTRACT_ROOT,
    OUTPUT_ROOT,
    PACKAGE_ROOT,
    STATUS_PASS_WITH_LIMITATIONS,
    validate_registry,
    verify_hash_manifest,
    write_all_outputs,
)


class CityBrainEpoch20ContractsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.decision = write_all_outputs()
        cls.registry = json.loads((PACKAGE_ROOT / "component_registry_v1.json").read_text(encoding="utf-8"))
        cls.final = json.loads((OUTPUT_ROOT / "final_published_status.json").read_text(encoding="utf-8"))

    def test_required_contract_schemas_exist(self):
        required = [
            "component_registry.schema.json",
            "agent_run_envelope.schema.json",
            "tool_permission_policy.schema.json",
            "llm_seat_registry.schema.json",
            "mode_invocation_registry.schema.json",
            "agent_handoff_matrix.schema.json",
            "budget_stop_policy.schema.json",
            "outcome_record.schema.json",
            "calibration_report.schema.json",
        ]
        for name in required:
            self.assertTrue((CONTRACT_ROOT / name).exists(), name)

    def test_registry_validates_and_contains_existing_agents(self):
        report = validate_registry(self.registry)
        self.assertEqual("PASS", report["status"], report)
        component_ids = {row["component_id"] for row in self.registry}
        for expected in {
            "check_agent",
            "watch_scout",
            "diff_scout",
            "recall_matcher",
            "briefing_agent",
            "spatial_agent",
            "perception_media_agent",
            "workflow_disposition_agent",
            "approval_lifecycle_agent",
            "plan_agent",
            "schedule_simulate_agent",
            "ask_resolver_renderer",
        }:
            self.assertIn(expected, component_ids)

    def test_closeout_decision_and_hash_manifest(self):
        self.assertEqual(STATUS_PASS_WITH_LIMITATIONS, self.decision["status"])
        self.assertTrue(all(self.decision["gates"].values()), self.decision["gates"])
        self.assertFalse(self.final["sealed_artifacts_touched"])
        self.assertFalse(self.final["data_dependency_changes"])
        self.assertEqual("PASS", verify_hash_manifest()["status"])


if __name__ == "__main__":
    unittest.main()

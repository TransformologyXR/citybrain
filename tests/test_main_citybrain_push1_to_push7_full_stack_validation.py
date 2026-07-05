import json
import unittest

from scripts.run_main_citybrain_push1_to_push7_full_stack_validation import (
    LIMITED_STATUS,
    OUTPUT_ROOT,
    REQUIRED_ARTIFACTS,
    write_all_outputs,
)


class MainCityBrainPush1ToPush7FullStackValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = write_all_outputs()
        cls.decision = json.loads((OUTPUT_ROOT / "PUSH1_TO_PUSH7_FULL_STACK_VALIDATION_DECISION.json").read_text(encoding="utf-8"))

    def test_required_artifacts_exist(self):
        for name in REQUIRED_ARTIFACTS:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_decision_passes_with_limitations(self):
        self.assertEqual(LIMITED_STATUS, self.decision["status"])
        self.assertFalse(self.decision["canonical_or_main_merged"])
        self.assertEqual("origin/codex/push7-infra-after-three-lanes", self.decision["validated_target"])
        self.assertEqual([], self.decision["blocking_issues"])

    def test_core_validation_sections_nonblocking(self):
        self.assertNotEqual("FAIL", self.reports["inventory"]["status"])
        self.assertNotEqual("FAIL", self.reports["hashes"]["status"])
        self.assertNotEqual("FAIL", self.reports["boundary"]["status"])
        self.assertNotEqual("FAIL", self.reports["protected"]["status"])

    def test_push7_core_artifacts_present(self):
        roots = {row["root"]: row for row in self.reports["inventory"]["roots"]}
        self.assertTrue(roots["outputs/push7_infra_after_three_lanes_integration"]["exists"])
        self.assertTrue(roots["outputs/push7_lane_a_federation_data_maturity"]["exists"])
        self.assertTrue(roots["outputs/push7_lane_b_rbac_audit_observability"]["exists"])
        self.assertTrue(roots["outputs/push7_lane_c_execution_readiness_autonomy_preflight"]["exists"])

    def test_hash_manifest_for_validation_outputs(self):
        manifest = json.loads((OUTPUT_ROOT / "PUSH1_TO_PUSH7_FULL_STACK_VALIDATION_HASH_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertIn("PUSH1_TO_PUSH7_FULL_STACK_VALIDATION_DECISION.json", manifest["files"])
        self.assertIn("PUSH1_TO_PUSH7_FULL_STACK_VALIDATION_SCORECARD.md", manifest["files"])


if __name__ == "__main__":
    unittest.main()

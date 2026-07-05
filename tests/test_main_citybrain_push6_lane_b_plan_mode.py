import json
import subprocess
import sys
import unittest
from pathlib import Path

from packages.plan_mode import validate_plan_bundle
from scripts.run_main_citybrain_push6_lane_b_plan_mode import (
    CLOSEOUT_ROOT,
    FINAL_STATUS_ROOT,
    OUTPUT_ROOT,
    REQUIRED_OUTPUT_FILES,
    STOP_APPROVAL,
    verify_hash_manifest,
)


ROOT = Path(__file__).resolve().parents[1]


class MainCityBrainPush6LaneBPlanModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(
            [sys.executable, "scripts/run_main_citybrain_push6_lane_b_plan_mode.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        cls.decision = json.loads((OUTPUT_ROOT / "PLAN_MODE_DECISION.json").read_text(encoding="utf-8"))
        cls.fixtures = json.loads((OUTPUT_ROOT / "PLAN_MODE_FIXTURES.json").read_text(encoding="utf-8"))
        cls.optionsets = json.loads((OUTPUT_ROOT / "OPTIONSET_V2_FIXTURES.json").read_text(encoding="utf-8"))
        cls.approval = json.loads((OUTPUT_ROOT / "PLAN_APPROVAL_BINDINGS.json").read_text(encoding="utf-8"))

    def test_required_artifacts_exist(self):
        for name in REQUIRED_OUTPUT_FILES:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)
        self.assertEqual("PASS", self.decision["required_output_status"]["status"])
        self.assertEqual(STOP_APPROVAL, self.decision["status"])

    def test_stops_before_closeout_when_approval_lifecycle_missing(self):
        self.assertEqual(STOP_APPROVAL, self.decision["approval_gate"]["status"])
        self.assertFalse(self.decision["contract_check"]["approval_lifecycle_used"])
        self.assertIn("B6_CLOSEOUT", self.decision["stopped_before"])
        self.assertFalse(CLOSEOUT_ROOT.exists())
        self.assertFalse(FINAL_STATUS_ROOT.exists())

    def test_push5_gate_is_green(self):
        gate = self.decision["push5_gate"]
        self.assertEqual("PASS", gate["status"])
        checks = gate["checks"]
        self.assertTrue(checks["spatial_ui_overlays_exist"])
        self.assertTrue(checks["perception_media_evidence_bundles_exist"])
        self.assertTrue(checks["watch_workflow_state_exists"])
        self.assertTrue(checks["check_v1_available"])

    def test_plan_contract_objects_are_defined(self):
        overview = (OUTPUT_ROOT / "PLAN_MODE_CONTRACT_OVERVIEW.md").read_text(encoding="utf-8")
        for term in [
            "PlanRequest",
            "OptionSetV2",
            "PlanOption",
            "DoNothingBaseline",
            "ConstraintSet",
            "AssumptionSet",
            "RiskSummary",
            "AbstainDecision",
            "NoSafeOptionReport",
            "PlanApprovalBinding",
        ]:
            self.assertIn(term, overview)

    def test_optionset_v2_created_with_required_refs(self):
        option_sets = self.fixtures["option_sets"]
        self.assertEqual(1, len(option_sets))
        option_set = option_sets[0]
        for field in [
            "option_set_id",
            "plan_request_ref",
            "scope_ref",
            "option_refs",
            "do_nothing_baseline_ref",
            "constraints_ref",
            "assumptions_ref",
            "risk_summary_ref",
            "evidence_refs",
            "limitation_refs",
            "trace_refs",
            "check_report_ref",
            "authority_envelope_ref",
            "approval_request_ref",
            "review_state",
            "execution_status",
            "cannot_claim",
        ]:
            self.assertIn(field, option_set)
            self.assertTrue(option_set[field])
        self.assertEqual("not_executed", option_set["execution_status"])
        self.assertTrue(option_set["approval_request_ref"].startswith("approval-request:"))

    def test_do_nothing_baseline_and_abstain_no_safe_option_exist(self):
        self.assertEqual(1, len(self.fixtures["do_nothing_baselines"]))
        self.assertEqual(1, len(self.fixtures["abstain_decisions"]))
        self.assertEqual(1, len(self.fixtures["no_safe_option_reports"]))
        baseline = self.fixtures["do_nothing_baselines"][0]
        abstain = self.fixtures["abstain_decisions"][0]
        no_safe = self.fixtures["no_safe_option_reports"][0]
        self.assertEqual("not_executed", baseline["execution_status"])
        self.assertEqual("not_executed", abstain["execution_status"])
        self.assertEqual("not_executed", no_safe["execution_status"])
        self.assertTrue(no_safe["approval_lifecycle_required"])
        self.assertFalse(no_safe["approval_lifecycle_present"])

    def test_every_plan_option_requires_approval_and_is_not_executed(self):
        self.assertEqual(3, len(self.fixtures["plan_options"]))
        for option in self.fixtures["plan_options"]:
            self.assertTrue(option["requires_approval"])
            self.assertEqual("not_executed", option["execution_status"])
            self.assertTrue(option["evidence_refs"])
            self.assertTrue(option["limitation_refs"])
            self.assertTrue(option["trace_refs"])
            self.assertTrue(option["check_report_ref"])
            self.assertTrue(option["authority_envelope_ref"])
            text = json.dumps(option).lower()
            self.assertNotIn("dispatch command", text)
            self.assertNotIn("control command", text)
            self.assertNotIn("enforcement action", text)
            self.assertNotIn("approved for execution", text)

    def test_approval_binding_is_present_but_provisional(self):
        bindings = self.approval["approval_bindings"]
        self.assertEqual(1, len(bindings))
        binding = bindings[0]
        self.assertTrue(binding["approval_request_ref"])
        self.assertEqual("authority_level_3", binding["authority_level_required"])
        self.assertFalse(binding["approval_lifecycle_used"])
        self.assertTrue(binding["provisional_until_lane_a"])
        self.assertEqual("not_executed", binding["execution_status"])

    def test_official_action_and_legal_claims_are_rejected(self):
        serialized = json.dumps(self.fixtures).lower()
        self.assertIn("dispatch/control/enforcement execution", serialized)
        self.assertIn("legal/certified finding", serialized)
        for forbidden in ["dispatch command", "control command", "enforcement action", "legal finding issued", "certified finding issued"]:
            self.assertNotIn(forbidden, serialized)
        for item in self.fixtures["plan_options"] + self.fixtures["option_sets"]:
            self.assertIn("dispatch/control/enforcement execution", item["cannot_claim"])
            self.assertIn("legal/certified finding", item["cannot_claim"])

    def test_plan_bundle_validator_passes_with_approval_warning(self):
        validation = validate_plan_bundle(self.fixtures)
        self.assertEqual("PASS", validation["status"], validation)
        self.assertEqual(1, validation["option_set_count"])
        self.assertEqual(3, validation["plan_option_count"])
        self.assertTrue(validation["warnings"])

    def test_no_live_retrieval_api_or_llm_source(self):
        source = (ROOT / "scripts" / "run_main_citybrain_push6_lane_b_plan_mode.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("openai", source)
        self.assertNotIn("fetch(", source)

    def test_hash_manifest_verifies(self):
        report = verify_hash_manifest(OUTPUT_ROOT, "PLAN_MODE_HASH_MANIFEST.json")
        self.assertEqual("PASS", report["status"], report)
        self.assertEqual(report["declared"], report["verified"])


if __name__ == "__main__":
    unittest.main()

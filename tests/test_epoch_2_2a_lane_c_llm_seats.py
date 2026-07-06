import json
import unittest

from scripts.run_epoch_2_2a_lane_c_llm_seats import (
    FORBIDDEN_ROLES,
    OUTPUT_ROOT,
    STATUS_PASS_LIMITATIONS,
    build_outputs,
    sha256_file,
)


class Epoch22aLaneCLlmSeatsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_outputs()
        cls.decision = json.loads((OUTPUT_ROOT / "DECISION.json").read_text(encoding="utf-8"))
        cls.readiness = json.loads((OUTPUT_ROOT / "LLM_SEAT_READINESS_REPORT.json").read_text(encoding="utf-8"))
        cls.delta = json.loads((OUTPUT_ROOT / "LLM_SEAT_REGISTRY_DELTA.json").read_text(encoding="utf-8"))
        cls.g8 = json.loads((OUTPUT_ROOT / "G8_OFFLINE_EVAL_REPORT.json").read_text(encoding="utf-8"))
        cls.g2 = json.loads((OUTPUT_ROOT / "G2_OFFLINE_EVAL_REPORT.json").read_text(encoding="utf-8"))
        cls.negative = json.loads((OUTPUT_ROOT / "NEGATIVE_FIXTURES_REPORT.json").read_text(encoding="utf-8"))

    def test_entry_gate_and_decision_pass_with_limitations(self):
        self.assertEqual(STATUS_PASS_LIMITATIONS, self.result["status"])
        self.assertEqual(STATUS_PASS_LIMITATIONS, self.decision["status"])
        self.assertEqual("main", self.decision["branch"])
        self.assertEqual("PASS", self.decision["prerequisite_gate"]["status"])
        self.assertFalse(self.decision["registry_mutation_performed"])
        self.assertFalse(self.decision["live_model_call_performed"])
        self.assertFalse(self.decision["operator_surface_activation_performed"])
        self.assertTrue(self.decision["contract_check"]["epoch_2_2_not_closed"])

    def test_allowed_and_inactive_seat_statuses(self):
        seat_status = self.decision["seat_status"]
        self.assertEqual("ready_for_2_2b", seat_status["ask_g8_writer_pattern_adapter"])
        self.assertEqual("ready_for_2_2c", seat_status["g2_intent_concept_resolver_proposal_adapter"])
        self.assertEqual("ready_for_2_2b", seat_status["brief_writer_v2"])
        self.assertEqual("registered_inactive_epoch3", seat_status["precedent_difference_explainer"])
        self.assertEqual("registered_inactive_epoch3", seat_status["investigation_decomposition_proposer"])

        for seat in self.readiness["active_or_eligible_seats"]:
            self.assertIn(seat["allowed_role"], {"writer", "resolver_proposer"})
            self.assertEqual(FORBIDDEN_ROLES, seat["forbidden_roles"])
            self.assertTrue(seat["check_required_before_operator_visibility"])
            self.assertTrue(seat["schema_validation_required_before_check"])
            self.assertTrue(seat["cost_latency_recording_shape"]["required"])
            self.assertTrue(seat["deterministic_fallback"])

        for seat in self.readiness["registered_inactive_epoch3_seats"]:
            self.assertEqual("registered_inactive_epoch3", seat["readiness_status"])
            self.assertIn("inactive_epoch3", seat["activation_state"])

    def test_all_required_contract_checks_are_present(self):
        for row in self.readiness["seat_readiness"]:
            self.assertTrue(row["all_required_checks_pass"], row)
            checks = row["check_results"]
            for key in [
                "component_id",
                "allowed_role",
                "forbidden_roles",
                "input_packet_schema",
                "output_schema",
                "model_version_placeholder_or_current_config",
                "deterministic_fallback",
                "eval_fixtures",
                "negative_tests",
                "cost_latency_recording_shape",
                "check_required_before_operator_visibility",
                "rollback_disable_semantics",
            ]:
                self.assertTrue(checks[key], f"{row['seat_id']} missing {key}")

    def test_g8_and_brief_writer_eval_catches_overclaim_without_sealed_core_touch(self):
        self.assertEqual(STATUS_PASS_LIMITATIONS, self.g8["status"])
        self.assertTrue(self.g8["controls"]["writer_must_not_add_unsupported_facts"])
        self.assertTrue(self.g8["controls"]["CHECK_catches_overclaim"])
        self.assertTrue(self.g8["controls"]["sealed_ASK_core_untouched"])
        self.assertTrue(self.g8["controls"]["brief_writer_v2_not_wired_into_ASK_internals"])
        self.assertEqual(4, self.g8["aggregate"]["fixture_count"])
        self.assertEqual(4, self.g8["aggregate"]["schema_valid_count"])
        self.assertEqual(0, self.g8["aggregate"]["unsupported_facts_operator_visible"])
        self.assertEqual(2, self.g8["aggregate"]["overclaim_caught_count"])
        for fixture in self.g8["fixtures"]:
            self.assertFalse(fixture["operator_visible_in_2_2a"])
            self.assertFalse(fixture["sealed_ask_core_touched"])

    def test_g2_eval_uses_adapter_compiler_no_direct_execution(self):
        self.assertEqual(STATUS_PASS_LIMITATIONS, self.g2["status"])
        self.assertTrue(self.g2["controls"]["proposes_only_to_adapter"])
        self.assertTrue(self.g2["controls"]["deterministic_compiler_accepts_rejects_or_falls_back"])
        self.assertTrue(self.g2["controls"]["no_direct_execution"])
        self.assertTrue(self.g2["controls"]["sealed_ASK_core_untouched"])
        metrics = self.g2["metrics"]
        self.assertEqual(1, metrics["accepted_count"])
        self.assertEqual(1, metrics["rejected_count"])
        self.assertEqual(1, metrics["fallback_count"])
        self.assertEqual(0, metrics["direct_execution_allowed_count"])
        self.assertEqual(0, metrics["sealed_ask_core_touch_count"])
        for fixture in self.g2["fixtures"]:
            self.assertFalse(fixture["deterministic_compiler"]["direct_execution_allowed"])
            self.assertFalse(fixture["deterministic_compiler"]["sealed_ask_core_touched"])

    def test_negative_fixtures_reject_stop_conditions(self):
        self.assertEqual("PASS", self.negative["status"])
        self.assertTrue(self.negative["all_stop_conditions_rejected"])
        attempted = {row["attempted_behavior"] for row in self.negative["fixtures"]}
        for behavior in [
            "source_facts",
            "compute_check",
            "grant_authority",
            "mutate_packet",
            "operator_surface_without_schema_validation_and_CHECK",
            "native_modification_of_sealed_ASK_G1_G8",
            "activate_precedent_difference_explainer_before_epoch3_loop4",
            "activate_investigation_decomposition_proposer_before_epoch3_loop5",
        ]:
            self.assertIn(behavior, attempted)
        for row in self.negative["fixtures"]:
            self.assertTrue(row["passed"], row)
            self.assertFalse(row["operator_visible"], row)
            self.assertFalse(row["model_call_allowed"], row)
            self.assertFalse(row["sealed_ask_core_touched"], row)

    def test_registry_delta_is_proposed_only_with_disable_semantics(self):
        self.assertEqual(STATUS_PASS_LIMITATIONS, self.delta["status"])
        self.assertFalse(self.delta["mutation_performed"])
        self.assertEqual("proposed_additive_registry_delta_only", self.delta["delta_type"])
        self.assertTrue(self.delta["registry_disable_semantics"]["no_delete"])
        self.assertFalse(self.delta["registry_disable_semantics"]["operator_visibility"])
        self.assertFalse(self.delta["registry_disable_semantics"]["model_call_allowed"])
        self.assertGreaterEqual(len(self.delta["rollback_triggers"]["universal"]), 1)

    def test_hash_manifest_verifies(self):
        manifest = json.loads((OUTPUT_ROOT / "HASH_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", manifest["status"])
        manifest_paths = {row["path"] for row in manifest["files"]}
        for name in [
            "LLM_SEAT_READINESS_REPORT.json",
            "LLM_SEAT_REGISTRY_DELTA.json",
            "G8_OFFLINE_EVAL_REPORT.json",
            "G2_OFFLINE_EVAL_REPORT.json",
            "NEGATIVE_FIXTURES_REPORT.json",
            "DECISION.json",
            "SUMMARY.md",
        ]:
            self.assertIn(name, manifest_paths)
        for row in manifest["files"]:
            target = OUTPUT_ROOT / row["path"]
            self.assertTrue(target.exists(), row)
            self.assertEqual(row["sha256"], sha256_file(target), row)


if __name__ == "__main__":
    unittest.main()

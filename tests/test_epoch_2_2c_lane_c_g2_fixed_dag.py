import json
import unittest

from scripts.run_epoch_2_2c_lane_c_g2_fixed_dag import (
    ALLOWED_PROPOSAL_FIELDS,
    FORBIDDEN_G2_ROLES,
    OUTPUT_ROOT,
    STATUS_PASS_LIMITATIONS,
    build_outputs,
    sha256_file,
)


class Epoch22cLaneCG2FixedDagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_outputs()
        cls.decision = json.loads((OUTPUT_ROOT / "G2_RESOLVER_PROPOSAL_DECISION.json").read_text(encoding="utf-8"))
        cls.metrics = json.loads((OUTPUT_ROOT / "G2_ACCEPTANCE_METRICS.json").read_text(encoding="utf-8"))
        cls.registry = json.loads((OUTPUT_ROOT / "FIXED_DAG_REGISTRY.json").read_text(encoding="utf-8"))
        cls.run_report = json.loads((OUTPUT_ROOT / "FIXED_DAG_RUN_REPORT.json").read_text(encoding="utf-8"))
        cls.negative = json.loads((OUTPUT_ROOT / "NEGATIVE_TEST_REPORT.json").read_text(encoding="utf-8"))

    def test_prerequisite_and_decision_pass_with_limitations(self):
        self.assertEqual(STATUS_PASS_LIMITATIONS, self.result["status"])
        self.assertEqual(STATUS_PASS_LIMITATIONS, self.decision["status"])
        self.assertEqual("main", self.decision["branch"])
        self.assertEqual("PASS", self.decision["prerequisite_gate"]["status"])
        self.assertEqual("PASS", self.decision["dependency_status"]["push_2_2b_integration"])
        self.assertEqual("ready_for_2_2c", self.decision["dependency_status"]["g2_readiness"])
        self.assertFalse(self.decision["dependency_status"]["sealed_ASK_core_delta_required"])
        self.assertTrue(self.decision["contract_check"]["epoch_2_2_not_closed"])

    def test_g2_adapter_proposals_have_only_allowed_fields_and_expected_metrics(self):
        self.assertEqual("g2_intent_concept_resolver_proposal_adapter", self.metrics["seat_id"])
        self.assertEqual("resolver_proposer", self.metrics["allowed_role"])
        self.assertEqual(FORBIDDEN_G2_ROLES, self.metrics["forbidden_roles"])
        self.assertEqual(4, self.metrics["proposal_count"])
        self.assertEqual(2, self.metrics["accepted_count"])
        self.assertEqual(1, self.metrics["rejected_count"])
        self.assertEqual(1, self.metrics["fallback_count"])
        self.assertEqual(2, self.metrics["unsupported_out_of_scope_count"])
        self.assertEqual(0, self.metrics["regression_failures"])
        for proposal in self.metrics["compiled_proposals"]:
            self.assertEqual(sorted(ALLOWED_PROPOSAL_FIELDS), sorted(proposal["raw_proposal"]))
            self.assertFalse(proposal["g2_direct_execution_allowed"])
            self.assertFalse(proposal["sealed_ASK_G1_G8_touched"])

    def test_compiler_accepts_rejects_and_falls_back(self):
        decisions = {row["compiler_decision"] for row in self.metrics["compiled_proposals"]}
        self.assertIn("ACCEPT", decisions)
        self.assertIn("REJECT", decisions)
        self.assertIn("FALLBACK", decisions)
        accepted = [row for row in self.metrics["compiled_proposals"] if row["accepted"]]
        self.assertGreaterEqual(len(accepted), 1)
        for row in accepted:
            self.assertTrue(row["compiled_dag_id"].startswith("fixed_dag:"))
            self.assertFalse(row["unsupported_or_out_of_scope"])

    def test_fixed_dag_registry_is_static_and_forbids_dynamic_planning(self):
        self.assertGreaterEqual(len(self.registry["dags"]), 1)
        self.assertFalse(self.registry["sealed_ASK_G1_G8_touched"])
        policy = self.registry["compiler_policy"]
        self.assertTrue(policy["deterministic_compiler_owns_execution"])
        self.assertTrue(policy["g2_never_executes"])
        self.assertTrue(policy["llm_may_not_choose_steps"])
        self.assertTrue(policy["no_dynamic_investigation"])
        for dag in self.registry["dags"]:
            step_names = [step["step"] for step in dag["steps"]]
            self.assertIn("compile_plan", step_names)
            self.assertIn("assemble_option_set", step_names)
            self.assertIn("check", step_names)
            self.assertIn("approval_boundary", step_names)
            self.assertIn("dynamic_step_selection", dag["forbidden"])
            self.assertIn("llm_tool_planning", dag["forbidden"])
            self.assertIn("free_form_tool_chain_selection", dag["forbidden"])

    def test_at_least_one_fixed_dag_runs_end_to_end_with_check_and_approval(self):
        summary = self.run_report["summary"]
        self.assertGreaterEqual(summary["end_to_end_dag_run_count"], 1)
        self.assertGreaterEqual(summary["check_applied_count"], 1)
        self.assertGreaterEqual(summary["approval_boundary_applied_count"], 1)
        self.assertEqual(0, summary["official_action_created_count"])
        self.assertEqual(0, summary["sealed_ASK_touch_count"])
        self.assertEqual(0, summary["dynamic_step_selection_count"])
        self.assertEqual(0, summary["llm_tool_planning_count"])
        for run in self.run_report["dag_runs"]:
            self.assertTrue(run["end_to_end"])
            self.assertTrue(run["check_applied"])
            self.assertTrue(run["approval_boundary_applied"])
            self.assertFalse(run["official_action_created"])
            self.assertFalse(run["sealed_ASK_G1_G8_touched"])

    def test_rollback_triggers_and_negative_tests(self):
        statuses = self.metrics["rollback_trigger_status"]
        for key in [
            "unsafe_compiler_acceptance",
            "route_or_intent_critical_regression_above_zero",
            "proposal_precision_below_95_percent",
            "acceptance_rate_anomaly",
        ]:
            self.assertEqual("PASS", statuses[key])
        self.assertEqual("PASS", self.negative["status"])
        self.assertTrue(self.negative["all_forbidden_behaviors_rejected"])
        attempted = {row["attempted_behavior"] for row in self.negative["tests"]}
        for behavior in [
            "dynamic_investigation_planner",
            "free_form_tool_chain_selection",
            "llm_chosen_executable_steps",
            "Loop5 InvestigationPacket",
            "trained ranking forecasting counterfactual",
            "native sealed ASK core change",
            "official ticket dispatch control enforcement legal certified finding",
        ]:
            self.assertIn(behavior, attempted)
        for row in self.negative["tests"]:
            self.assertTrue(row["passed"], row)
            self.assertFalse(row["operator_visible"], row)
            self.assertFalse(row["g2_direct_execution_allowed"], row)
            self.assertFalse(row["sealed_ASK_G1_G8_touched"], row)
            self.assertFalse(row["official_action_created"], row)

    def test_boundary_contract_non_claims(self):
        checks = self.decision["contract_check"]
        for key in [
            "g2_adapter_layer_only",
            "deterministic_compiler_accepts_rejects_falls_back",
            "no_dynamic_investigation",
            "no_free_form_tool_chain_selection",
            "no_llm_chosen_executable_steps",
            "no_loop5_investigation_packet",
            "no_trained_ranking_prediction_forecasting_counterfactual",
            "no_official_action_ticket_dispatch_control_enforcement",
            "no_native_sealed_ASK_core_change",
            "local_replay_review_query_only",
        ]:
            self.assertTrue(checks[key], key)

    def test_hash_manifest_verifies(self):
        manifest = json.loads((OUTPUT_ROOT / "HASH_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", manifest["status"])
        manifest_paths = {row["path"] for row in manifest["files"]}
        for name in [
            "G2_RESOLVER_PROPOSAL_DECISION.json",
            "G2_ACCEPTANCE_METRICS.json",
            "FIXED_DAG_REGISTRY.json",
            "FIXED_DAG_RUN_REPORT.json",
            "PLAN_SCHEDULE_SIMULATE_BOUNDARY_REPORT.md",
            "NEGATIVE_TEST_REPORT.json",
        ]:
            self.assertIn(name, manifest_paths)
        for row in manifest["files"]:
            target = OUTPUT_ROOT / row["path"]
            self.assertTrue(target.exists(), row)
            self.assertEqual(row["sha256"], sha256_file(target), row)


if __name__ == "__main__":
    unittest.main()

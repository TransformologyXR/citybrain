import json
import unittest
from pathlib import Path

from scripts.run_epoch_2_1a_lane_c_dashboard_outcome import (
    MANDATORY_AGENT_COMPONENTS,
    OUTPUT_ROOT,
    STATUS_PASS_DASHBOARD_OUTCOME,
    STATUS_PASS_OUTCOME_MATERIALIZED,
    build_outputs,
    sha256_file,
)


class Epoch21aLaneCDashboardOutcomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = build_outputs()
        cls.entry = json.loads((OUTPUT_ROOT / "EPOCH_2_0_ENTRY_CHECK_DECISION.json").read_text(encoding="utf-8"))
        cls.dashboard = json.loads((OUTPUT_ROOT / "data_maturity_dashboard_v1.json").read_text(encoding="utf-8"))
        cls.schema = json.loads((OUTPUT_ROOT / "outcome_record_schema_v1.json").read_text(encoding="utf-8"))
        cls.materialization = json.loads((OUTPUT_ROOT / "outcome_record_materialization_report.json").read_text(encoding="utf-8"))
        cls.decision = json.loads((OUTPUT_ROOT / "PUSH_2_1A_LANE_C_DECISION.json").read_text(encoding="utf-8"))

    def test_entry_check_passes_with_mandatory_agents_and_mode_scorecard(self):
        self.assertEqual("PASS", self.entry["status"])
        self.assertEqual(len(MANDATORY_AGENT_COMPONENTS), len(self.entry["mandatory_agent_rows"]))
        for row in self.entry["mandatory_agent_rows"]:
            self.assertTrue(row["registered"], row)
            self.assertEqual("PASS", row["recertification_status"], row)
            self.assertTrue(row["replay_or_eval_ref"], row)
            self.assertTrue(row["permission_valid"], row)
        self.assertEqual("PASS", self.entry["mode_scorecard"]["status"])
        self.assertGreater(self.entry["mode_scorecard"]["active_mode_count"], 0)

    def test_entry_check_outputs_exist(self):
        for name in [
            "EPOCH_2_0_ENTRY_CHECK_DECISION.json",
            "EPOCH_2_0_ENTRY_CHECK_SUMMARY.md",
            "EPOCH_2_0_AGENT_RECERTIFICATION_INDEX.json",
            "EPOCH_2_1_ALLOWED_TO_OPEN.flag",
        ]:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_dashboard_has_required_sections(self):
        required = [
            "source_freshness_status",
            "check_status_cannot_claim_stale_counts",
            "corpus_version_and_append_state",
            "agent_recertification_state",
            "mode_scorecard_state",
            "cer_conflict_assertion_summary",
            "outcome_record_availability_and_aggregation_status",
            "policy_compliance_flags",
        ]
        for key in required:
            self.assertIn(key, self.dashboard)
        self.assertEqual("PASS_DASHBOARD_MATERIALIZED_WITH_OUTCOME_RECORDS", self.dashboard["status"])
        self.assertTrue((OUTPUT_ROOT / "data_maturity_dashboard_v1.md").exists())

    def test_outcome_record_materializer_uses_lane_a_aggregation_floor(self):
        self.assertEqual(STATUS_PASS_OUTCOME_MATERIALIZED, self.materialization["status"])
        self.assertEqual(2, self.materialization["records_materialized"])
        self.assertTrue(self.materialization["aggregation_floor_respected"])
        self.assertTrue(self.materialization["derived_field_only"])
        self.assertTrue(self.materialization["small_cell_suppressed"])
        self.assertEqual(0, self.materialization["dashboard_cells_released"])
        floor = self.materialization["aggregation_floor"]
        self.assertEqual("PASS", floor["status"])
        self.assertTrue(floor["validated"])
        self.assertIn("aggregation_floor_policy_v1.json", " ".join(floor["refs"]))
        self.assertEqual("PASS", self.dashboard["outcome_record_availability_and_aggregation_status"]["status"])
        self.assertEqual(STATUS_PASS_OUTCOME_MATERIALIZED, self.decision["outcome_record_materializer_status"])

    def test_outcome_record_schema_preserves_boundaries(self):
        self.assertEqual("OutcomeRecordV1", self.schema["schema_name"])
        self.assertEqual("derived_field", self.schema["source_class"])
        for field in [
            "outcome_record_id",
            "target_ref",
            "trigger_packet_refs",
            "disposition_history_refs",
            "terminal_state",
            "time_to_terminal_seconds",
            "aggregation_floor_respected",
            "trace_refs",
        ]:
            self.assertIn(field, self.schema["required_fields"])
        for forbidden in ["ranking", "claim_status_change", "review_state_change", "authority_change", "model_training"]:
            self.assertIn(forbidden, self.schema["forbidden_behaviors"])
        boundary = self.schema["boundary"]
        self.assertTrue(boundary["descriptive_materialization_only"])
        self.assertTrue(boundary["not_a_claim"])
        self.assertTrue(boundary["not_model_output"])
        self.assertTrue(boundary["not_ranking_signal"])
        self.assertTrue(boundary["no_learned_ranking"])
        self.assertTrue(boundary["no_prediction"])

    def test_policy_compliance_flags_reject_non_goals(self):
        flags = self.dashboard["policy_compliance_flags"]
        for key in [
            "no_learned_ranking",
            "no_prediction",
            "no_new_data_warehouse",
            "no_live_dashboard_service",
            "no_official_ticket_case_submission",
            "no_dispatch_control_enforcement",
            "no_legal_certified_finding",
            "no_autonomous_execution",
            "no_identity_biometric_inference",
            "source_class_derived_field_only_for_outcome_record",
            "not_a_claim",
            "not_model_output",
            "not_ranking_signal",
        ]:
            self.assertTrue(flags[key], key)

    def test_decision_marks_lane_blocked_not_closed(self):
        self.assertEqual(STATUS_PASS_DASHBOARD_OUTCOME, self.decision["status"])
        self.assertEqual("main", self.decision["branch"])
        self.assertTrue(self.decision["contract_check"]["lane_c_only"])
        self.assertTrue(self.decision["contract_check"]["main_branch_only"])
        self.assertTrue(self.decision["contract_check"]["epoch_2_1_not_closed"])
        self.assertEqual("PASS", self.decision["lane_a_dependency"]["status"])

    def test_hash_manifest_verifies(self):
        manifest = json.loads((OUTPUT_ROOT / "PUSH_2_1A_LANE_C_HASH_MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", manifest["status"])
        self.assertGreater(manifest["item_count"], 0)
        for row in manifest["files"]:
            target = OUTPUT_ROOT / row["path"]
            self.assertTrue(target.exists(), row)
            self.assertEqual(row["sha256"], sha256_file(target), row)


if __name__ == "__main__":
    unittest.main()

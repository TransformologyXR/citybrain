from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from scripts.run_epoch3_day1_instrumentation_and_harness_r1 import (
    OUTPUT_ROOT,
    REQUIRED_OUTPUTS,
    STATUS,
    write_all_outputs,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


class Epoch3Day1InstrumentationAndHarnessR1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = write_all_outputs()
        cls.decision = cls.result["decision"]
        cls.arming = cls.result["arming_report"]
        cls.capabilities = {row["capability_id"]: row for row in cls.arming["capabilities"]}

    def test_required_outputs_exist(self):
        for name in REQUIRED_OUTPUTS:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_decision_arms_only_safe_work(self):
        expected_armed = {
            "L1.R0_EXPOSURE_AND_PROPENSITY_LOGGING",
            "L1.R0_WATCH_EXPLORATION_FLOOR_INFRA",
            "L1.R1_OUTCOME_LEDGER_HARDENING",
            "L1.R2_CALIBRATION_REPORT_HARDENING",
            "L2.R1_BACKTEST_HARNESS_BUILD",
            "E3.ARMING_STATUS_WATCH_FAMILY",
        }
        expected_blocked = {
            "L1.R3A_OFFLINE_RANKER_EXPERIMENT",
            "L1.R3B_OPERATOR_FACING_LEARNED_RANKING",
            "L2.R2_FORECAST_MODEL",
            "L3_COUNTERFACTUAL",
            "L4_CASE_MEMORY",
            "DYNAMIC_INVESTIGATION_AGENT",
            "CROSS_CITY_LEARNED_TRANSFER",
        }
        self.assertEqual(STATUS, self.decision["status"], self.decision["blockers"])
        self.assertEqual(expected_armed, set(self.decision["armed_now"]))
        self.assertEqual(expected_blocked, set(self.decision["not_armed"]))
        self.assertEqual("PASS", self.decision["no_model_guard"])
        self.assertTrue(self.decision["threshold_crossing_does_not_start_work"])

    def test_arming_status_watch_family_is_status_only(self):
        self.assertEqual("E3.ARMING_STATUS_WATCH_FAMILY", self.arming["component_id"])
        self.assertTrue(self.arming["threshold_crossing_does_not_start_work"])
        self.assertIn("NOT_STARTED", self.arming["arming_semantics"])
        self.assertTrue(self.arming["emits_status_only"])
        self.assertFalse(self.arming["executes_armed_work"])
        facts = self.arming["reconciled_gate_facts"]
        self.assertEqual(0, facts["terminal_dispositions"])
        self.assertEqual(0, facts["operator_refs_distinct_count"])
        self.assertEqual(5, facts["watch_family_count"])
        self.assertFalse(facts["l4_runtime_case_artifact_enforced"])
        self.assertFalse(facts["l4_production_erasure_workflow"])
        self.assertFalse(facts["aggregation_floor_satisfied"])
        self.assertNotEqual("green", facts["full_corpus_discovery_status"])

    def test_forbidden_capabilities_remain_blocked(self):
        for capability_id in self.decision["not_armed"]:
            self.assertIn(capability_id, self.capabilities)
            self.assertNotEqual("ARMED_NOW", self.capabilities[capability_id]["status"])
            self.assertFalse(self.capabilities[capability_id]["executes_work"])

    def test_r3a_blocked_by_full_corpus_and_fuel(self):
        r3a = self.capabilities["L1.R3A_OFFLINE_RANKER_EXPERIMENT"]
        self.assertEqual("NOT_ARMED", r3a["status"])
        failed = set(r3a["failed_requirement_ids"])
        self.assertIn("R3A_TOTAL_DISPOSITIONS", failed)
        self.assertIn("R3A_OPERATOR_DIVERSITY", failed)
        self.assertIn("R3A_FULL_CORPUS_DISCOVERY_GREEN", failed)

    def test_l4_blocked_on_runtime_metrics(self):
        l4 = self.capabilities["L4_CASE_MEMORY"]
        self.assertEqual("BLOCKED", l4["status"])
        failed = set(l4["failed_requirement_ids"])
        self.assertIn("L4_CASE_RETENTION_RUNTIME", failed)
        self.assertIn("L4_DELETE_PATH_RUNTIME", failed)
        self.assertIn("L4_AGGREGATION_FLOOR_CURRENT", failed)
        self.assertNotIn("L4_CASE_RETENTION", failed)
        self.assertNotIn("L4_DELETE_PATH", failed)

    def test_exposure_schema_and_unknown_records(self):
        schema = load_json(REPO_ROOT / "schemas" / "exposure_log_event.schema.json")
        required = set(schema["required"])
        for field in [
            "exposure_id",
            "watch_item_id",
            "operator_ref",
            "surfaced_at",
            "surface_policy",
            "surface_reason",
            "surface_reason_code",
            "deterministic_priority_tier",
            "family_cap_state",
            "operator_throttle_state",
            "exploration_bucket",
            "holdout_family_flag",
            "ranker_component_id",
            "ranker_score",
            "propensity",
            "propensity_status",
            "selected_item_context_ref",
            "disposition_ref",
            "source_class",
            "training_eligibility",
        ]:
            self.assertIn(field, required)

        report = load_json(OUTPUT_ROOT / "L1_R0_EXPOSURE_PROPENSITY_LOGGING_REPORT.json")
        rows = load_jsonl(OUTPUT_ROOT / "L1_R0_EXPOSURE_LOG_EVENTS.jsonl")
        self.assertTrue(report["logging_activated"])
        self.assertFalse(report["propensity_unknown_counts_toward_primary_r3_thresholds"])
        self.assertFalse(report["learned_ranker_created"])
        self.assertEqual(0, report["known_primary_r3_eligible_count"])
        self.assertTrue(any(row["propensity_status"] == "propensity_unknown" for row in rows))
        for row in rows:
            self.assertIsNone(row["ranker_component_id"])
            self.assertIsNone(row["ranker_score"])

    def test_exploration_floor_is_static(self):
        report = load_json(OUTPUT_ROOT / "L1_R0_WATCH_EXPLORATION_FLOOR_INFRA_REPORT.json")
        self.assertTrue(report["static_policy_only"])
        self.assertFalse(report["learned_ranker_enabled"])
        self.assertTrue(report["holdout_families_supported"])
        self.assertTrue(report["ranker_off_replay_hook_present"])
        self.assertFalse(report["operator_throttle_override_allowed"])
        self.assertFalse(report["safety_cap_override_allowed"])
        self.assertFalse(report["family_cap_override_allowed"])
        self.assertFalse(report["ranker_off_replay_hook"]["creates_ranker"])

    def test_outcome_and_calibration_are_descriptive(self):
        outcome = load_json(OUTPUT_ROOT / "L1_R1_OUTCOME_LEDGER_HARDENING_REPORT.json")
        calibration = load_json(OUTPUT_ROOT / "L1_R2_CALIBRATION_REPORT_HARDENING_REPORT.json")
        self.assertTrue(outcome["terminal_disposition_normalization_schema_present"])
        self.assertTrue(outcome["operator_diversity_metrics_present"])
        self.assertTrue(outcome["family_pack_attribution_present"])
        self.assertEqual(0, outcome["eligible_terminal_dispositions_current"])
        self.assertFalse(outcome["training_eligible_terminal_disposition_flow_started"])
        self.assertEqual("INSUFFICIENT", calibration["sample_depth_status"])
        self.assertFalse(calibration["true_calibration_claimed"])
        self.assertTrue(calibration["descriptive_only"])

    def test_backtest_shell_has_no_model(self):
        report = load_json(OUTPUT_ROOT / "L2_R1_BACKTEST_HARNESS_SHELL_REPORT.json")
        self.assertTrue(report["BacktestReport_template_exists"])
        self.assertFalse(report["BacktestReport_exists"])
        self.assertFalse(report["forecast_model_created"])
        self.assertFalse(report["ForecastPacket_created"])
        self.assertEqual("scaffolded", report["forecast_target_registry_status"])
        self.assertEqual("scaffolded", report["frozen_eval_slice_tooling_status"])
        self.assertEqual("scaffolded", report["baseline_do_nothing_comparator_status"])
        self.assertFalse(report["model_work_allowed"])

    def test_no_model_guard(self):
        guard = load_json(OUTPUT_ROOT / "E3_DAY1_NO_MODEL_GUARD_REPORT.json")
        self.assertEqual("PASS", guard["status"])
        self.assertEqual([], guard["forbidden_capabilities_armed"])
        self.assertFalse(guard["ranker_created"])
        self.assertFalse(guard["forecast_model_created"])
        self.assertFalse(guard["counterfactual_learner_created"])
        self.assertFalse(guard["case_memory_learner_created"])
        self.assertFalse(guard["dynamic_investigation_agent_created"])
        self.assertFalse(guard["cross_city_learned_transfer_created"])

    def test_hash_manifest_verifies(self):
        manifest = load_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
        self.assertTrue(manifest["files"])
        for row in manifest["files"]:
            path = REPO_ROOT / row["path"]
            data = path.read_bytes()
            self.assertEqual(len(data), row["bytes"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"])
        entry_names = {row["path"] for row in manifest["entries"]}
        self.assertIn("E3_DAY1_DECISION.json", entry_names)

    def test_no_crlf_in_publication(self):
        report = load_json(OUTPUT_ROOT / "E3_DAY1_LF_STABILITY_REPORT.json")
        self.assertEqual("PASS_LF_STABLE_FOR_DAY1_PUBLICATION", report["status"])
        self.assertEqual([], report["crlf_paths"])
        for path in OUTPUT_ROOT.glob("*"):
            if path.is_file():
                self.assertNotIn(b"\r\n", path.read_bytes(), path)


if __name__ == "__main__":
    unittest.main()

import json
import unittest

from scripts.run_epoch_2_2a_lane_b_observability import (
    ALLOWED_HEALTH_STATES,
    NON_GOALS,
    OUTPUT_ROOT,
    PASS_STATUS,
    REQUIRED_PANEL_FIELDS,
    check_prerequisite_gate,
    validate_report,
    write_all_outputs,
)


class Epoch22aLaneBObservabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = write_all_outputs()
        cls.gate = cls.result["gate"]
        cls.decision = cls.result["decision"]
        cls.report = cls.result["report"]

    def test_prerequisite_gate_passes(self):
        self.assertEqual("PASS", self.gate["status"], self.gate["errors"])
        self.assertEqual("main", self.gate["branch"])
        self.assertEqual("PASS_EPOCH_2_2_ENTRY_GATE", self.gate["entry_gate_status"])

    def test_required_artifacts_exist(self):
        for name in [
            "AGENT_OBSERVABILITY_REPORT.json",
            "AGENT_OBSERVABILITY_VIEW.md",
            "AGENT_OBSERVABILITY_FIXTURE.html",
            "OBSERVABILITY_SOURCE_MAP.json",
            "DECISION.json",
            "SUMMARY.md",
            "HASH_MANIFEST.json",
        ]:
            self.assertTrue((OUTPUT_ROOT / name).exists(), name)

    def test_required_panels_and_fields_present(self):
        report = json.loads((OUTPUT_ROOT / "AGENT_OBSERVABILITY_REPORT.json").read_text(encoding="utf-8"))
        for panel in [
            "service_health_summary",
            "latest_runs",
            "check_failures_downgrades",
            "authority_distribution",
            "budget_and_latency",
            "handoffs",
            "llm_seat_usage",
            "suppressed_deferred_throttled_watch_items",
            "corpus_scorecard_linkage",
            "open_blockers",
            "service_justification_status",
            "limitations_ledger",
        ]:
            self.assertIn(panel, report["report_panels"])
        self.assertTrue(report["service_rows"])
        row = report["service_rows"][0]
        for field in REQUIRED_PANEL_FIELDS:
            self.assertIn(field, row)

    def test_report_consumes_real_2_0_and_2_1_sources(self):
        row = self.report["service_rows"][0]
        refs = self.report["source_refs"]
        self.assertEqual("epoch2_replay_harness", row["component_id"])
        self.assertIn("agent_run_envelope_v1.json", refs["agent_run_envelope"])
        self.assertIn("component_registry_v1.json", refs["component_registry"])
        self.assertIn("observability_envelope_v1.json", refs["rbac_observability_envelope"])
        self.assertIn("data_maturity_dashboard_v1.json", refs["data_maturity_dashboard"])
        self.assertIn("EPOCH_2_1_LEDGER_ROWS.json", refs["ledger_rows"])

    def test_service_registry_pending_is_limited_not_blocking(self):
        status = self.report["service_registry_status"]
        self.assertIn(status["status"], {"AVAILABLE", "PENDING_LANE_A_SERVICE_REGISTRY"})
        if status["status"] == "PENDING_LANE_A_SERVICE_REGISTRY":
            self.assertIn("pending", status["limitation"].lower())
            self.assertEqual("degraded", self.report["service_rows"][0]["health_state"])

    def test_health_status_values_are_not_invented(self):
        for row in self.report["service_rows"]:
            self.assertIn(row["health_state"], ALLOWED_HEALTH_STATES)
        counts = self.report["report_panels"]["service_health_summary"]["health_state_counts"]
        self.assertEqual(set(ALLOWED_HEALTH_STATES), set(counts))

    def test_check_authority_budget_latency_and_handoff_fields_appear(self):
        row = self.report["service_rows"][0]
        self.assertTrue(row["check_report_refs"])
        self.assertLessEqual(row["authority_level"], 3)
        self.assertEqual(0, row["budget_consumed"]["llm_calls"])
        self.assertIn("tool_calls", row["budget_consumed"])
        self.assertIn("latency_ms", row)
        self.assertIn("error_count", row)
        self.assertIsInstance(row["handoff_target"], list)
        self.assertIn("suppressed", row["suppressed_deferred_throttled_count"])

    def test_boundaries_are_preserved(self):
        decision = json.loads((OUTPUT_ROOT / "DECISION.json").read_text(encoding="utf-8"))
        self.assertEqual(PASS_STATUS, decision["status"])
        for key, value in decision["boundaries"].items():
            self.assertFalse(value, key)
        self.assertEqual(NON_GOALS, decision["non_goals"])

    def test_validation_and_hash_manifest(self):
        validation = validate_report(self.report)
        self.assertEqual("PASS", validation["status"], validation["errors"])
        manifest = json.loads((OUTPUT_ROOT / "HASH_MANIFEST.json").read_text(encoding="utf-8"))
        paths = {row["path"] for row in manifest["files"]}
        for name in [
            "AGENT_OBSERVABILITY_REPORT.json",
            "AGENT_OBSERVABILITY_VIEW.md",
            "AGENT_OBSERVABILITY_FIXTURE.html",
            "OBSERVABILITY_SOURCE_MAP.json",
            "DECISION.json",
            "SUMMARY.md",
        ]:
            self.assertIn(name, paths)
        self.assertEqual(6, manifest["item_count"])


if __name__ == "__main__":
    unittest.main()

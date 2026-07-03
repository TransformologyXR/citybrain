from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from packages.ask_v11.eval import (
    REPORT_STATUS_PASS,
    evaluate_case,
    required_families_covered,
    run_sealed_eval,
    write_eval_report,
)
from packages.ask_v11.eval_cases import REQUIRED_EVAL_FAMILIES, SEALED_EVAL_CASES
from packages.ask_v11.packets import SeverityLabel
from packages.ask_v11.severity import (
    classify_eval_result,
    is_hard_failure,
    summarize_severity_counts,
)


class AskV11EvalSealingTests(unittest.TestCase):
    def test_severity_enum_mapping(self) -> None:
        self.assertEqual(
            [item.value for item in SeverityLabel],
            [
                "sev_0_clean",
                "sev_1_taxonomy_reporting_only",
                "sev_2_acceptable_but_weak",
                "sev_3_audit_uncertain",
                "sev_4_real_failure",
            ],
        )

    def test_sev4_boundary_action_is_hard_failure(self) -> None:
        severity = classify_eval_result(
            {},
            {"passed": False, "boundary_action_reached_execution": True},
        )
        self.assertTrue(is_hard_failure(severity))

    def test_sev1_reporting_only_not_hard_failure(self) -> None:
        severity = classify_eval_result(
            {"expected_severity_on_pass": SeverityLabel.sev_1_taxonomy_reporting_only.value},
            {"passed": True},
        )
        self.assertFalse(is_hard_failure(severity))

    def test_sealed_eval_cases_have_unique_ids(self) -> None:
        ids = [case["case_id"] for case in SEALED_EVAL_CASES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_sealed_eval_cases_cover_required_families(self) -> None:
        self.assertTrue(required_families_covered())
        families = {case["family"] for case in SEALED_EVAL_CASES}
        self.assertTrue(set(REQUIRED_EVAL_FAMILIES).issubset(families))

    def test_eval_runner_returns_report(self) -> None:
        report = run_sealed_eval()
        self.assertEqual(report.final_decision, REPORT_STATUS_PASS)
        self.assertGreaterEqual(report.total_cases, 20)

    def test_eval_report_has_severity_counts(self) -> None:
        report = run_sealed_eval()
        self.assertIn(SeverityLabel.sev_0_clean.value, report.severity_counts)
        self.assertIn(SeverityLabel.sev_4_real_failure.value, report.severity_counts)

    def test_eval_report_has_family_counts(self) -> None:
        report = run_sealed_eval()
        self.assertIn("boundary_action", report.family_counts)
        self.assertIn("renderer_no_undowngrade", report.family_counts)

    def test_eval_hard_pass_requires_zero_boundary_action_sev4(self) -> None:
        report = run_sealed_eval()
        self.assertEqual(report.boundary_action_sev4_count, 0)
        self.assertEqual(report.status, "PASS")

    def test_board_meta_eval_case_passes(self) -> None:
        case = next(case for case in SEALED_EVAL_CASES if case["case_id"].endswith("board-meta-alert-capability"))
        result = evaluate_case(case)
        self.assertTrue(result.passed, result.errors)

    def test_imperative_action_eval_case_stops_before_g5(self) -> None:
        case = next(case for case in SEALED_EVAL_CASES if case["case_id"].endswith("boundary-alert-now"))
        result = evaluate_case(case)
        self.assertTrue(result.passed, result.errors)
        self.assertNotIn("G5", result.actual["trace_stages"])

    def test_prediction_eval_case_does_not_forecast(self) -> None:
        case = next(case for case in SEALED_EVAL_CASES if case["family"] == "boundary_prediction")
        result = evaluate_case(case)
        self.assertTrue(result.passed, result.errors)

    def test_identity_person_eval_case_does_not_identify_person(self) -> None:
        case = next(case for case in SEALED_EVAL_CASES if case["family"] == "boundary_identity_person")
        result = evaluate_case(case)
        self.assertTrue(result.passed, result.errors)

    def test_external_context_eval_case_cannot_claim_live_fact(self) -> None:
        case = next(case for case in SEALED_EVAL_CASES if case["family"] == "external_context_need")
        result = evaluate_case(case)
        self.assertTrue(result.passed, result.errors)
        self.assertTrue(any("current charger availability" in item for item in result.actual["cannot_claim"]))

    def test_proximity_eval_case_does_not_claim_causality(self) -> None:
        case = next(case for case in SEALED_EVAL_CASES if case["family"] == "proximity_vs_causality")
        result = evaluate_case(case)
        self.assertTrue(result.passed, result.errors)
        self.assertIn("nearby/proximity context only", result.actual["rendered_text"])

    def test_no_data_eval_case_renders_no_data(self) -> None:
        case = next(case for case in SEALED_EVAL_CASES if case["family"] == "no_data")
        result = evaluate_case(case)
        self.assertTrue(result.passed, result.errors)
        self.assertTrue(result.actual["no_data"])

    def test_unsafe_action_render_eval_case_degrades(self) -> None:
        case = next(case for case in SEALED_EVAL_CASES if case.get("case_type") == "unsafe_action_render")
        result = evaluate_case(case)
        self.assertTrue(result.passed, result.errors)
        self.assertTrue(result.actual["render_degraded"])

    def test_raw_query_injection_eval_case_does_not_leak(self) -> None:
        case = next(case for case in SEALED_EVAL_CASES if case.get("case_type") == "raw_query_injection")
        result = evaluate_case(case)
        self.assertTrue(result.passed, result.errors)
        self.assertFalse(result.actual["raw_query_leak"])

    def test_future_flow_request_does_not_execute_future_flow(self) -> None:
        case = next(case for case in SEALED_EVAL_CASES if case["case_id"].endswith("future-flow-request"))
        result = evaluate_case(case)
        self.assertTrue(result.passed, result.errors)
        self.assertFalse(result.actual["future_flow_runtime_violation"])

    def test_eval_cli_writes_json_and_markdown_report(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, str(repo / "scripts" / "run_ask_v11_sealed_eval.py")],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertTrue((repo / "outputs" / "ask_v11_sealed_eval" / "ASK_V11_SEALED_EVAL_REPORT.json").exists())
        self.assertTrue((repo / "outputs" / "ask_v11_sealed_eval" / "ASK_V11_SEALED_EVAL_SUMMARY.md").exists())

    def test_write_eval_report_to_custom_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            paths = write_eval_report(run_sealed_eval(), tmp)
            self.assertTrue(paths["json"].exists())
            self.assertTrue(paths["markdown"].exists())

    def test_summarize_severity_counts_accepts_results(self) -> None:
        report = run_sealed_eval()
        counts = summarize_severity_counts(report.report_items)
        self.assertEqual(counts, report.severity_counts)


if __name__ == "__main__":
    unittest.main()

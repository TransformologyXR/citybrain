from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.ask_v11.packets import SeverityLabel
from packages.ask_v11.real_corpus_eval import (
    DEFAULT_MATRIX_PATH,
    RealCorpusEvalError,
    _resolve_repo_path,
    load_case_matrix,
    run_real_corpus_eval_r1,
    write_real_corpus_eval_report,
)


class AskV11RealCorpusEvalR1Tests(unittest.TestCase):
    def test_loads_preflight_case_matrix(self) -> None:
        cases = load_case_matrix()
        self.assertEqual(len(cases), 19)
        self.assertEqual(cases[0]["case_id"], "real-corpus-001-board-meta-product-boundary")

    def test_rejects_remote_matrix_or_artifact_path(self) -> None:
        with self.assertRaises(RealCorpusEvalError):
            _resolve_repo_path("https://example.test/not-retained.json")

    def test_rejects_path_escape(self) -> None:
        with self.assertRaises(RealCorpusEvalError):
            _resolve_repo_path("..\\outside-repo.json")

    def test_real_corpus_eval_returns_limited_pass(self) -> None:
        report = run_real_corpus_eval_r1()
        self.assertEqual(report.status, "PASS_WITH_LIMITATIONS")
        self.assertEqual(report.total_cases, 19)
        self.assertEqual(report.evaluated_cases, 18)
        self.assertEqual(report.excluded_cases, 1)
        self.assertEqual(report.pass_count, 18)
        self.assertEqual(report.fail_count, 0)

    def test_real_corpus_eval_reports_hard_failure_counts_separately(self) -> None:
        report = run_real_corpus_eval_r1()
        self.assertEqual(report.sev_4_real_failure_count, 0)
        self.assertEqual(report.boundary_action_sev4_count, 0)
        self.assertEqual(report.raw_query_leak_count, 0)
        self.assertEqual(report.official_action_claim_count, 0)
        self.assertEqual(report.future_flow_runtime_violation_count, 0)
        self.assertEqual(report.live_retrieval_attempt_count, 0)
        self.assertEqual(report.production_api_call_count, 0)
        self.assertEqual(report.legal_certified_claim_count, 0)

    def test_needs_mapping_cases_are_evaluated_by_adapter_only(self) -> None:
        report = run_real_corpus_eval_r1()
        needs_mapping = [item for item in report.report_items if item.readiness == "needs_mapping"]
        self.assertEqual(len(needs_mapping), 8)
        self.assertTrue(all(item.passed for item in needs_mapping))
        self.assertTrue(all(item.adapter_mapping_status.endswith("eval_adapter") for item in needs_mapping))
        self.assertTrue(all(item.actual["runtime_called"] is False for item in needs_mapping))

    def test_excluded_contradiction_is_explicit_not_failure(self) -> None:
        report = run_real_corpus_eval_r1()
        excluded = [item for item in report.report_items if item.status == "EXCLUDED"]
        self.assertEqual(len(excluded), 1)
        self.assertEqual(excluded[0].family, "contradiction")
        self.assertTrue(excluded[0].passed)
        self.assertEqual(excluded[0].severity, SeverityLabel.sev_1_taxonomy_reporting_only)

    def test_source_urls_are_citations_not_live_retrieval(self) -> None:
        report = run_real_corpus_eval_r1()
        self.assertGreater(report.source_url_citation_count, 0)
        self.assertEqual(report.live_retrieval_attempt_count, 0)
        self.assertTrue(
            all(
                (item.artifact is None or item.actual["external_urls_treated_as_citations_only"] >= 0)
                for item in report.report_items
            )
        )

    def test_no_raw_query_text_is_written_to_report(self) -> None:
        report = run_real_corpus_eval_r1()
        payload = json.loads(report.model_dump_json())
        rendered = json.dumps(payload)
        cases = load_case_matrix()
        for case in cases:
            self.assertNotIn(case["raw_query_candidate"], rendered)
        self.assertIn("raw_query_sha256", rendered)

    def test_write_real_corpus_report_outputs_three_artifacts(self) -> None:
        report = run_real_corpus_eval_r1()
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            paths = write_real_corpus_eval_report(report, tmp)
            self.assertTrue(paths["json"].exists())
            self.assertTrue(paths["summary"].exists())
            self.assertTrue(paths["failures"].exists())
            written = json.loads(paths["json"].read_text(encoding="utf-8"))
            self.assertEqual(written["final_decision"], report.final_decision)

    def test_default_matrix_path_is_repo_local(self) -> None:
        path = _resolve_repo_path(DEFAULT_MATRIX_PATH)
        self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()

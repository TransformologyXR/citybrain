from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from packages.ask_v11.real_corpus_eval import (
    R2_REPORT_STATUS_LIMITED,
    load_case_matrix,
    run_real_corpus_eval_r1,
    run_real_corpus_eval_r2_mapping_expansion,
    write_real_corpus_eval_r2_report,
)

ROOT = Path(__file__).resolve().parents[1]
SESSION_TEMPLATE = ROOT / "inputs" / "d11_real_operator_sessions" / "session_record_template.json"


def write_test_operator_session_template() -> None:
    SESSION_TEMPLATE.parent.mkdir(parents=True, exist_ok=True)
    SESSION_TEMPLATE.write_text(
        json.dumps(
            {
                "schema_version": "citybrain.operator_session_template.test.v1",
                "session_id": "session:test:clean-worktree",
                "surface_target": "review_only_local_replay",
                "spontaneous_questions": [
                    "Ask a targeted clarification before answering an unanchored city query."
                ],
                "selected_item_ref": "infrastructure_context_asset:uk-london:ev_charging_site:87",
                "boundary": {
                    "raw_query_policy": "raw_query is input-only and must not be copied into downstream packets",
                    "runtime_called": False,
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


class AskV11RealCorpusEvalR2MappingExpansionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        write_test_operator_session_template()

    def test_r2_mapping_expansion_returns_limited_pass(self) -> None:
        report = run_real_corpus_eval_r2_mapping_expansion()
        self.assertEqual(report.status, "PASS_WITH_LIMITATIONS")
        self.assertEqual(report.final_decision, R2_REPORT_STATUS_LIMITED)
        self.assertEqual(report.total_cases, 19)
        self.assertEqual(report.evaluated_cases, 18)
        self.assertEqual(report.pass_count, 18)
        self.assertEqual(report.fail_count, 0)
        self.assertEqual(report.excluded_cases, 1)

    def test_r2_maps_all_eight_r1_needs_mapping_cases(self) -> None:
        r1 = run_real_corpus_eval_r1()
        r2 = run_real_corpus_eval_r2_mapping_expansion()
        self.assertEqual(r1.cases_still_needing_mapping, 8)
        self.assertEqual(r2.cases_newly_mapped, 8)
        self.assertEqual(r2.cases_still_needing_mapping, 0)
        mapped = [item for item in r2.report_items if item.readiness == "mapped"]
        self.assertEqual(len(mapped), 8)
        self.assertTrue(all(item.adapter_mapping_status.startswith("r2_") for item in mapped))
        self.assertTrue(all(item.actual["runtime_called"] is False for item in mapped))

    def test_r2_carries_contradiction_waiver(self) -> None:
        report = run_real_corpus_eval_r2_mapping_expansion()
        contradiction = next(item for item in report.report_items if item.family == "contradiction")
        self.assertEqual(contradiction.status, "WAIVED")
        self.assertEqual(report.contradiction_case_status, "waived_no_retained_same_claim_pair")
        self.assertTrue(contradiction.actual["formal_waiver"])

    def test_r2_hard_failure_counts_are_zero(self) -> None:
        report = run_real_corpus_eval_r2_mapping_expansion()
        self.assertEqual(report.sev_4_real_failure_count, 0)
        self.assertEqual(report.boundary_action_sev4_count, 0)
        self.assertEqual(report.raw_query_leak_count, 0)
        self.assertEqual(report.official_action_claim_count, 0)
        self.assertEqual(report.future_flow_runtime_violation_count, 0)
        self.assertEqual(report.live_retrieval_attempt_count, 0)
        self.assertEqual(report.production_api_call_count, 0)
        self.assertEqual(report.legal_certified_claim_count, 0)

    def test_r2_report_does_not_write_raw_query_text(self) -> None:
        report = run_real_corpus_eval_r2_mapping_expansion()
        rendered = report.model_dump_json()
        for case in load_case_matrix():
            self.assertNotIn(case["raw_query_candidate"], rendered)
        self.assertIn("raw_query_sha256", rendered)

    def test_write_r2_report_outputs_four_artifacts(self) -> None:
        report = run_real_corpus_eval_r2_mapping_expansion()
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            paths = write_real_corpus_eval_r2_report(report, tmp)
            self.assertTrue(paths["json"].exists())
            self.assertTrue(paths["summary"].exists())
            self.assertTrue(paths["failures"].exists())
            self.assertTrue(paths["mapping_changes"].exists())
            written = json.loads(paths["json"].read_text(encoding="utf-8"))
            self.assertEqual(written["final_decision"], R2_REPORT_STATUS_LIMITED)
            self.assertIn("Mapping Changes", paths["mapping_changes"].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from packages.ask_v11.eval import run_sealed_eval
from packages.ask_v11.future_flow_skeletons import (
    FutureFlowNotImplementedError,
    ask_v1_is_only_implemented_flow,
    assert_all_skeletons_only,
    assert_skeleton_only,
    get_future_flow_skeleton,
    list_future_flow_skeletons,
    run_future_flow_skeleton,
)


class AskV11FutureFlowSkeletonTests(unittest.TestCase):
    def test_future_flow_skeletons_exist_for_watch_brief_diff_incident(self) -> None:
        self.assertEqual(
            {flow.flow_id for flow in list_future_flow_skeletons()},
            {"flow:watch_v1", "flow:brief_v1", "flow:diff_v1", "flow:incident_v1"},
        )

    def test_future_flow_skeletons_are_not_implemented(self) -> None:
        for flow in list_future_flow_skeletons():
            self.assertIn("not_implemented", flow.gates)
            self.assertIn("Skeleton contract only", flow.not_implemented_reason)

    def test_future_flow_skeletons_have_no_runtime_executor(self) -> None:
        for flow in list_future_flow_skeletons():
            self.assertIsNone(flow.runtime_executor)

    def test_future_flow_skeletons_have_no_retrieval_plan(self) -> None:
        for flow in list_future_flow_skeletons():
            self.assertIsNone(flow.retrieval_plan)

    def test_future_flow_skeletons_have_no_action_adapter(self) -> None:
        for flow in list_future_flow_skeletons():
            self.assertIsNone(flow.action_adapter)

    def test_attempt_to_run_watch_skeleton_fails_safely(self) -> None:
        with self.assertRaises(FutureFlowNotImplementedError):
            run_future_flow_skeleton("flow:watch_v1")

    def test_attempt_to_run_brief_skeleton_fails_safely(self) -> None:
        with self.assertRaises(FutureFlowNotImplementedError):
            run_future_flow_skeleton("flow:brief_v1")

    def test_attempt_to_run_diff_skeleton_fails_safely(self) -> None:
        with self.assertRaises(FutureFlowNotImplementedError):
            run_future_flow_skeleton("flow:diff_v1")

    def test_attempt_to_run_incident_skeleton_fails_safely(self) -> None:
        with self.assertRaises(FutureFlowNotImplementedError):
            run_future_flow_skeleton("flow:incident_v1")

    def test_ask_v1_is_only_implemented_flow(self) -> None:
        self.assertTrue(ask_v1_is_only_implemented_flow())

    def test_skeletons_do_not_call_g5_or_g6(self) -> None:
        for flow in list_future_flow_skeletons():
            self.assertNotIn("template_execute", flow.gates)
            self.assertNotIn("evidence_validate", flow.gates)
            self.assertTrue(assert_skeleton_only(flow))

    def test_skeletons_do_not_change_ask_eval(self) -> None:
        self.assertTrue(assert_all_skeletons_only())
        report = run_sealed_eval()
        self.assertEqual(report.future_flow_runtime_violation_count, 0)
        self.assertEqual(report.status, "PASS")

    def test_get_unknown_future_flow_skeleton_fails(self) -> None:
        with self.assertRaises(KeyError):
            get_future_flow_skeleton("flow:plan_v1")


if __name__ == "__main__":
    unittest.main()

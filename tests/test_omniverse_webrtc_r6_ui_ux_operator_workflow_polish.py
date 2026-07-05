from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_main_citybrain_omniverse_webrtc_r6_ui_ux_operator_workflow_polish import (  # noqa: E402
    PASS_STATUS,
    TASK_ID,
    WEB_STYLE,
    WEB_VIEW,
    WORKFLOW_STATES,
    boundary_audit,
    inspector_layout_audit,
    object_event_parity_regression,
    one_truth_packet_audit,
    review_export_packet,
    review_note_export_audit,
    r5_dependency,
    scene_polish_report,
    ui_layout_audit,
    workflow_state_audit,
)


class OmniverseWebRtcR6UiUxOperatorWorkflowPolishTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = WEB_VIEW.read_text(encoding="utf-8")
        self.style = WEB_STYLE.read_text(encoding="utf-8")

    def test_task_identity_and_status(self) -> None:
        self.assertIn("R6-UI-UX-OPERATOR-WORKFLOW-POLISH", TASK_ID)
        self.assertEqual(PASS_STATUS, "PASS_OMNIVERSE_WEBRTC_R6_UI_UX_OPERATOR_WORKFLOW_POLISH_WITH_LIMITATIONS")

    def test_side_rail_and_collapsible_overlay_are_present(self) -> None:
        audit = ui_layout_audit()
        self.assertEqual(audit["status"], "PASS")
        self.assertTrue(all(audit["checks"].values()))
        self.assertIn("citybrain-operator-side-rail", self.source)
        self.assertIn("data-inspector-collapsible-state", self.source)
        self.assertIn('data-side-rail-state="collapsed"', self.style)

    def test_inspector_sections_cover_required_operator_fields(self) -> None:
        audit = inspector_layout_audit()
        self.assertEqual(audit["status"], "PASS")
        for section in ["summary", "evidence", "limitations", "does-not-prove", "review-state", "no-action", "source-refs-packet-hash", "workflow-state", "empty-selection"]:
            self.assertIn(f'data-inspector-section="{section}"', self.source)
        self.assertIn("NoActionState", self.source)
        self.assertIn("Packet hash", self.source)

    def test_workflow_states_and_local_transition_log_exist(self) -> None:
        audit = workflow_state_audit()
        self.assertEqual(audit["status"], "PASS")
        for state in WORKFLOW_STATES:
            self.assertIn(state, self.source)
        self.assertIn("WORKFLOW_TRANSITION_KEY", self.source)
        self.assertIn("review_state_local_only", self.source)

    def test_review_note_export_packet_has_required_boundary_fields(self) -> None:
        audit = review_note_export_audit()
        self.assertEqual(audit["status"], "PASS")
        packet = review_export_packet()
        self.assertEqual(packet["local_review_state"], "note_added")
        self.assertTrue(packet["evidence_refs"])
        self.assertTrue(packet["limitation_refs"])
        self.assertIn("export_hash", packet)
        self.assertEqual(packet["no_action_state"]["execution_state"], "not_executed")
        self.assertTrue(packet["review_state_local_only"])
        self.assertFalse(packet["pixel_derived_truth_used"])

    def test_scene_polish_is_bounded_to_readability_and_bookmarks(self) -> None:
        report = scene_polish_report()
        if not report["checks"]["real_scene_dependency"]:
            self.skipTest("requires generated Omniverse R5 real-scene output package")
        self.assertEqual(report["status"], "PASS")
        self.assertIn("scene-polish-overlay", self.source)
        self.assertIn('data-scene-bookmark="overview"', self.source)
        self.assertIn("Not an official affected asset", self.source)

    def test_r5_dependency_and_parity_regression_remain_pass(self) -> None:
        dep = r5_dependency()
        if not dep["verified"]:
            self.skipTest("requires generated Omniverse R5 real-scene output package")
        self.assertTrue(dep["verified"])
        self.assertEqual(dep["status"], "PASS_OMNIVERSE_WEBRTC_R5_REAL_SCENE_OBJECT_EVENT_REVIEW_LOOP_WITH_LIMITATIONS")
        parity = object_event_parity_regression()
        self.assertEqual(parity["status"], "PASS")

    def test_one_truth_and_boundary_audits_pass_and_reject_bad_claims(self) -> None:
        one_truth = one_truth_packet_audit()
        if not one_truth["checks"]["r5_one_truth_pass"]:
            self.skipTest("requires generated Omniverse R5 real-scene output package")
        self.assertEqual(one_truth["status"], "PASS")
        ok = boundary_audit("stream_visual_context_only packet truth review_state_local_only not_executed no_action_state pixel_derived_truth_used false")
        self.assertEqual(ok["status"], "PASS")
        bad = boundary_audit("automated action implemented and ready", "packet truth not_executed no_action_state pixel_derived_truth_used false stream_visual_context_only review_state_local_only")
        self.assertEqual(bad["status"], "FAIL")

    def test_current_r6_outputs_parse_when_present(self) -> None:
        output_root = ROOT / "outputs" / "main_citybrain_omniverse_webrtc_r6_ui_ux_operator_workflow_polish"
        if not output_root.exists():
            return
        for path in output_root.rglob("*.json"):
            with self.subTest(path=path.name):
                json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

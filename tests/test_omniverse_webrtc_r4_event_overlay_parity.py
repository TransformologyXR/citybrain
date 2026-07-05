from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KIT_APP = ROOT / "apps" / "kit" / "citybrain.control_room"
sys.path.insert(0, str(KIT_APP))
sys.path.insert(0, str(ROOT))

from citybrain.control_room.event_overlay_registry import (  # noqa: E402
    EVENT_FOCUS_REQUEST,
    EVENT_OVERLAY_UPSERT,
    EVENT_SELECTION_CHANGED,
    event_fixtures,
    event_message,
    event_overlay_parity_audit,
    kit_event_overlay_registry,
)
from citybrain.control_room.overlay_manager import OverlayManager  # noqa: E402
from citybrain.control_room.runtime_bundle import load_bundle  # noqa: E402
from citybrain.control_room.selection_inspector import SelectionInspector  # noqa: E402
from scripts.run_main_citybrain_omniverse_webrtc_r4_event_overlay_parity import (  # noqa: E402
    PASS_STATUS,
    TASK_ID,
    boundary_audit,
    webui_event_source_audit,
)


class OmniverseWebRtcR4EventOverlayParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = load_bundle()
        self.events = event_fixtures()

    def test_task_identity_and_status_are_r4_event_overlay_parity(self) -> None:
        self.assertIn("EVENT-OVERLAY-PARITY", TASK_ID)
        self.assertEqual(PASS_STATUS, "PASS_OMNIVERSE_WEBRTC_R4_EVENT_OVERLAY_PARITY_WITH_LIMITATIONS")

    def test_event_packet_fixtures_validate(self) -> None:
        registry = kit_event_overlay_registry()
        self.assertEqual(registry["status"], "PASS")
        self.assertEqual(len(self.events), 3)
        self.assertTrue(registry["real_scene_used"])
        event_ids = {event["event_id"] for event in self.events}
        self.assertIn("event:replay:blockage:001", event_ids)
        self.assertIn("event:replay:evidence:001", event_ids)
        self.assertIn("event:replay:limitation:001", event_ids)
        for event in self.events:
            self.assertTrue(event["marker_prim_path"].startswith("/CityBrainR4EventOverlays/"))
            self.assertTrue(event["target_prim_path"].startswith("/"))
            self.assertTrue(event["evidence_refs"])
            self.assertTrue(event["limitation_refs"])
            self.assertEqual(event["review_state"]["review_state"], "needs_review")
            self.assertEqual(event["no_action_state"]["execution_state"], "not_executed")
            self.assertFalse(event["pixel_derived_truth_used"])

    def test_event_messages_preserve_packet_fields_both_directions(self) -> None:
        web_messages = [event_message(event, "web_to_kit", "webui_event_overlay_button") for event in self.events]
        kit_messages = [event_message(event, "kit_to_web", "kit_event_marker_selection") for event in self.events]
        upserts = [event_message(event, "kit_overlay_upsert", "kit_event_overlay_registry") for event in self.events]
        audit = event_overlay_parity_audit(web_messages, kit_messages)
        self.assertEqual(audit["status"], "PASS")
        for web, kit, upsert in zip(web_messages, kit_messages, upserts):
            self.assertEqual(web["message_type"], EVENT_FOCUS_REQUEST)
            self.assertEqual(kit["message_type"], EVENT_SELECTION_CHANGED)
            self.assertEqual(upsert["message_type"], EVENT_OVERLAY_UPSERT)
            self.assertEqual(web["event_id"], kit["event_id"])
            self.assertEqual(web["target_prim_path"], kit["target_prim_path"])
            self.assertEqual(web["marker_prim_path"], kit["marker_prim_path"])
            self.assertEqual(web["packet_hash"], kit["packet_hash"])
            self.assertEqual(web["no_action_state"]["execution_state"], "not_executed")
            self.assertFalse(web["pixel_derived_truth_used"])

    def test_kit_inspector_resolves_event_marker_prims(self) -> None:
        overlay = OverlayManager(self.bundle)
        inspector = SelectionInspector(self.bundle, overlay)
        self.assertEqual(overlay.contract()["status"], "PASS")
        for event in self.events:
            result = inspector.inspect_prim_path(event["marker_prim_path"])
            card = result["inspection_card"]
            self.assertTrue(result["found"])
            self.assertEqual(card["event_id"], event["event_id"])
            self.assertEqual(card["prim_path"], event["marker_prim_path"])
            self.assertEqual(card["target_prim_path"], event["target_prim_path"])
            self.assertEqual(card["packet_hash"], event["packet_hash"])
            self.assertIn(event["event_id"], result["visible_text"])
            self.assertIn("review_state:event-overlay:needs_review", result["visible_text"])
            self.assertIn("NoActionState:", result["visible_text"])

    def test_webui_source_contains_event_overlay_hooks(self) -> None:
        web_main = ROOT / "outputs" / "live_citybrain_webrtc_browser_client" / "citybrain-local" / "src" / "main.ts"
        if not web_main.exists():
            self.skipTest("requires generated live CityBrain WebRTC browser client output")
        audit = webui_event_source_audit()
        self.assertEqual(audit["status"], "PASS")
        self.assertTrue(all(audit["checks"].values()))

    def test_boundary_audit_rejects_forbidden_positive_claims(self) -> None:
        ok = boundary_audit(
            "local/replay review_only visual context only packet truth pixel_derived_truth_used false not_executed no_action_taken",
            "not live monitoring; not dispatch/control/enforcement; not automated action",
        )
        self.assertEqual(ok["status"], "PASS")
        self.assertFalse(ok["forbidden_claims_present"])
        bad = boundary_audit(
            "local/replay review_only visual context only packet truth pixel_derived_truth_used false not_executed no_action_taken",
            "automated action implemented and ready",
        )
        self.assertEqual(bad["status"], "FAIL")
        self.assertTrue(bad["forbidden_claims_present"])

    def test_pixel_derived_truth_remains_false(self) -> None:
        for event in self.events:
            self.assertFalse(event["packet"]["pixel_derived_truth_used"])
            self.assertTrue(event["packet"]["stream_visual_context_only"])


if __name__ == "__main__":
    unittest.main()

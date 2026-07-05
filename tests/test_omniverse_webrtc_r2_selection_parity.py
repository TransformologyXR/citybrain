from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KIT_APP = ROOT / "apps" / "kit" / "citybrain.control_room"
sys.path.insert(0, str(KIT_APP))
sys.path.insert(0, str(ROOT))

from citybrain.control_room.overlay_manager import OverlayManager  # noqa: E402
from citybrain.control_room.runtime_bundle import load_bundle  # noqa: E402
from citybrain.control_room.selection_message_parity import (  # noqa: E402
    apply_kit_to_web_selection,
    apply_web_to_kit_selection,
    build_selection_message,
    parity_audit,
)
from scripts.run_main_citybrain_omniverse_webrtc_r2_bidirectional_selection_parity import (  # noqa: E402
    FAIL_NO_STREAM_OR_MESSAGES,
    FAIL_ONE_TRUTH_OR_BOUNDARY,
    PARTIAL_KIT_TO_WEB_ONLY,
    PARTIAL_WEB_TO_KIT_ONLY,
    PASS_STATUS,
    TASK_ID,
    webui_source_audit,
)


class OmniverseWebRtcR2SelectionParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = load_bundle()
        self.refs = OverlayManager(self.bundle).entity_refs()[:2]

    def test_task_identity_and_status_labels_are_r2_selection_parity(self) -> None:
        self.assertIn("BIDIRECTIONAL-SELECTION-PARITY", TASK_ID)
        self.assertTrue(PASS_STATUS.startswith("PASS_OMNIVERSE_WEBRTC_R2"))
        self.assertIn("WEB_TO_KIT_ONLY", PARTIAL_WEB_TO_KIT_ONLY)
        self.assertIn("KIT_TO_WEB_ONLY", PARTIAL_KIT_TO_WEB_ONLY)
        self.assertIn("ONE_TRUTH_OR_BOUNDARY", FAIL_ONE_TRUTH_OR_BOUNDARY)
        self.assertIn("NO_LIVE_STREAM_OR_NO_MESSAGE_CAPTURE", FAIL_NO_STREAM_OR_MESSAGES)

    def test_two_entity_messages_preserve_same_packet_hashes_both_directions(self) -> None:
        web_messages = [
            build_selection_message(self.bundle, entity_ref, "web_to_kit", "web_ui_packet_selection_button")
            for entity_ref in self.refs
        ]
        kit_messages = [
            build_selection_message(self.bundle, entity_ref, "kit_to_web", "kit_native_spatial_cockpit_selection")
            for entity_ref in self.refs
        ]
        audit = parity_audit(web_messages, kit_messages)
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["entity_count"], 2)
        for web_message, kit_message in zip(web_messages, kit_messages):
            self.assertEqual(web_message["packet_hash"], kit_message["packet_hash"])
            self.assertFalse(web_message["pixel_derived_truth_used"])
            self.assertFalse(kit_message["pixel_derived_truth_used"])
            self.assertEqual(web_message["no_action_state"]["execution_state"], "not_executed")

    def test_web_to_kit_selection_updates_kit_visible_card_from_packet(self) -> None:
        message = build_selection_message(self.bundle, self.refs[0], "web_to_kit", "web_ui_packet_selection_button")
        result = apply_web_to_kit_selection(self.bundle, message)
        self.assertEqual(result["status"], "PASS")
        text = result["kit_visible_text"]
        self.assertIn("Selected entity:", text)
        self.assertIn("What supports this:", text)
        self.assertIn("Unknowns / limitations:", text)
        self.assertIn("NoActionState:", text)
        self.assertIn("execution_state=not_executed", text)

    def test_kit_to_web_selection_updates_packet_backed_dom_state(self) -> None:
        message = build_selection_message(self.bundle, self.refs[1], "kit_to_web", "kit_native_spatial_cockpit_selection")
        result = apply_kit_to_web_selection(self.bundle, message)
        self.assertEqual(result["status"], "PASS")
        dom = result["web_dom_state"]
        self.assertEqual(dom["selector"], "#omniverse-webrtc-bridge")
        self.assertEqual(dom["data-selected-entity-ref"], message["canonical_entity_id"])
        self.assertEqual(dom["packet_hash"], message["packet_hash"])
        self.assertEqual(dom["no_action_state_text"], "no_action_taken=true | execution_state=not_executed")
        self.assertGreater(dom["evidence_ref_count"], 1)
        self.assertGreater(dom["limitation_ref_count"], 1)

    def test_webui_source_contains_bidirectional_packet_hooks(self) -> None:
        audit = webui_source_audit()
        self.assertEqual(audit["status"], "PASS")
        checks = audit["checks"]
        self.assertTrue(checks["selection_message_builder_exported"])
        self.assertTrue(checks["kit_to_web_dom_apply_exported"])
        self.assertTrue(checks["packet_backed_entity_buttons"])
        self.assertTrue(checks["nvidia_sdk_message_send_path"])
        self.assertTrue(checks["sdk_custom_event_envelope"])
        self.assertTrue(checks["pixel_truth_rejected"])


if __name__ == "__main__":
    unittest.main()

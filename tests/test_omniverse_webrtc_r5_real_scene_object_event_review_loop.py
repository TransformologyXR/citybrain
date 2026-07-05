from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KIT_APP = ROOT / "apps" / "kit" / "citybrain.control_room"
sys.path.insert(0, str(KIT_APP))
sys.path.insert(0, str(ROOT))

from citybrain.control_room.overlay_manager import OverlayManager  # noqa: E402
from citybrain.control_room.real_scene_review_loop_registry import (  # noqa: E402
    object_event_relationship_audit,
    real_scene_event_fixtures,
    real_scene_event_message,
    real_scene_event_overlay_parity_audit,
    real_scene_review_loop_summary,
    real_scene_selection_parity_audit,
    r5_scene_prim_bindings,
)
from citybrain.control_room.runtime_bundle import load_bundle  # noqa: E402
from citybrain.control_room.scene_prim_selection_registry import (  # noqa: E402
    FOCUS_REQUEST_EVENT,
    SELECTION_CHANGED_EVENT,
    binding_for_entity,
    binding_for_prim_path,
    selection_message,
)
from citybrain.control_room.selection_inspector import SelectionInspector  # noqa: E402
from scripts.run_main_citybrain_omniverse_webrtc_r5_real_scene_object_event_review_loop import (  # noqa: E402
    PASS_STATUS,
    TASK_ID,
    boundary_audit,
)


class OmniverseWebRtcR5RealSceneObjectEventReviewLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = load_bundle()
        self.bindings = r5_scene_prim_bindings()
        self.events = real_scene_event_fixtures()

    def test_task_identity_and_status_are_r5_review_loop(self) -> None:
        self.assertIn("REAL-SCENE-OBJECT-EVENT-REVIEW-LOOP", TASK_ID)
        self.assertEqual(PASS_STATUS, "PASS_OMNIVERSE_WEBRTC_R5_REAL_SCENE_OBJECT_EVENT_REVIEW_LOOP_WITH_LIMITATIONS")

    def test_real_scene_registry_meets_minimum_scope(self) -> None:
        summary = real_scene_review_loop_summary()
        self.assertEqual(summary["status"], "PASS")
        self.assertTrue(summary["real_scene_used"])
        self.assertGreaterEqual(summary["actual_scene_prim_binding_count"], 5)
        self.assertGreaterEqual(summary["event_overlay_count"], 3)
        categories = {binding["category"] for binding in self.bindings}
        self.assertIn("building_or_building_like_prim", categories)
        self.assertIn("corridor_road_lane_infrastructure_prim", categories)
        self.assertIn("evidence_limitation_review_marker_prim", categories)
        self.assertIn("event_review_marker_prim", categories)
        building_count = sum(1 for binding in self.bindings if binding["category"] == "building_or_building_like_prim")
        self.assertGreaterEqual(building_count, 2)

    def test_real_scene_source_assets_exist(self) -> None:
        for binding in self.bindings:
            source = binding["source_scene"]
            if source.get("real_scene_asset"):
                source_path = ROOT / source["source_asset_path"]
                if not source_path.exists():
                    self.skipTest("requires generated Omniverse real-scene asset outputs")
                self.assertTrue(source_path.exists(), source_path)
                self.assertGreater(source_path.stat().st_size, 1000)

    def test_overlay_manager_and_inspector_resolve_r5_objects_and_events(self) -> None:
        overlay = OverlayManager(self.bundle)
        inspector = SelectionInspector(self.bundle, overlay)
        self.assertEqual(overlay.contract()["status"], "PASS")
        for binding in self.bindings:
            self.assertIsNotNone(binding_for_entity(binding["canonical_entity_id"]))
            self.assertEqual(binding_for_prim_path(binding["prim_path"])["canonical_entity_id"], binding["canonical_entity_id"])
            result = inspector.inspect_prim_path(binding["prim_path"])
            self.assertTrue(result["found"])
            self.assertEqual(result["inspection_card"]["packet_hash"], binding["packet_hash"])
            self.assertIn("NoActionState:", result["visible_text"])
        for event in self.events:
            result = inspector.inspect_prim_path(event["marker_prim_path"])
            self.assertTrue(result["found"])
            self.assertEqual(result["inspection_card"]["event_id"], event["event_id"])
            self.assertEqual(result["inspection_card"]["packet_hash"], event["packet_hash"])
            self.assertIn("not_executed", result["visible_text"])

    def test_object_selection_parity_messages_match_both_directions(self) -> None:
        web_messages = [selection_message(binding, "web_to_kit", "webui_real_scene_object_focus") for binding in self.bindings]
        kit_messages = [selection_message(binding, "kit_to_web", "kit_real_scene_prim_selection") for binding in self.bindings]
        audit = real_scene_selection_parity_audit(web_messages, kit_messages)
        self.assertEqual(audit["status"], "PASS")
        for web, kit in zip(web_messages, kit_messages):
            self.assertEqual(web["message_type"], FOCUS_REQUEST_EVENT)
            self.assertEqual(kit["message_type"], SELECTION_CHANGED_EVENT)
            self.assertEqual(web["packet_hash"], kit["packet_hash"])
            self.assertFalse(web["pixel_derived_truth_used"])

    def test_event_overlay_parity_messages_match_both_directions(self) -> None:
        web_messages = [real_scene_event_message(event, "web_to_kit", "webui_real_scene_event_focus") for event in self.events]
        kit_messages = [real_scene_event_message(event, "kit_to_web", "kit_real_scene_event_marker_selection") for event in self.events]
        audit = real_scene_event_overlay_parity_audit(web_messages, kit_messages)
        self.assertEqual(audit["status"], "PASS")
        for web, kit in zip(web_messages, kit_messages):
            self.assertEqual(web["event_id"], kit["event_id"])
            self.assertEqual(web["target_prim_path"], kit["target_prim_path"])
            self.assertEqual(web["marker_prim_path"], kit["marker_prim_path"])
            self.assertEqual(web["packet_hash"], kit["packet_hash"])
            self.assertTrue(web["review_only"])
            self.assertEqual(web["no_action_state"]["execution_state"], "not_executed")

    def test_object_event_relationships_are_candidate_review_context(self) -> None:
        audit = object_event_relationship_audit()
        self.assertEqual(audit["status"], "PASS")
        self.assertGreaterEqual(len(audit["relationships"]), 3)
        for row in audit["relationships"]:
            self.assertIn("candidate/review context", row["relationship_claim_boundary"])
            self.assertEqual(row["execution_state"], "not_executed")
            self.assertFalse(row["pixel_derived_truth_used"])

    def test_webui_source_contains_r5_hooks(self) -> None:
        web_main = ROOT / "outputs" / "live_citybrain_webrtc_browser_client" / "citybrain-local" / "src" / "main.ts"
        if not web_main.exists():
            self.skipTest("requires generated live CityBrain WebRTC browser client output")
        source = web_main.read_text(encoding="utf-8")
        self.assertIn("citybrainR5RealSceneReviewLoop", source)
        for binding in self.bindings:
            self.assertIn(binding["canonical_entity_id"], source)
            self.assertIn(binding["prim_path"], source)
        for event in self.events:
            self.assertIn(event["event_id"], source)
            self.assertIn(event["marker_prim_path"], source)
        self.assertIn("AppStreamer.sendMessage", source)
        self.assertIn("AppStreamer.setSelectedPrims", source)
        self.assertIn("pixel_derived_truth_used: false", source)

    def test_boundary_audit_rejects_positive_forbidden_claims(self) -> None:
        ok = boundary_audit(
            "local/dev replay review_only review context candidate/review context stream visual context only packet truth pixel_derived_truth_used false not_executed no_action_taken",
            "not live monitoring; not automated action; not a legal/certified finding",
        )
        self.assertEqual(ok["status"], "PASS")
        bad = boundary_audit(
            "local/dev replay review_only review context candidate/review context stream visual context only packet truth pixel_derived_truth_used false not_executed no_action_taken",
            "automated action implemented and ready",
        )
        self.assertEqual(bad["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()

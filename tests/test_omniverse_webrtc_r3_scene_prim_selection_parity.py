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
from citybrain.control_room.scene_prim_selection_registry import (  # noqa: E402
    FOCUS_REQUEST_EVENT,
    SELECTION_CHANGED_EVENT,
    binding_for_entity,
    binding_for_prim_path,
    registry_summary,
    scene_prim_bindings,
    selection_message,
)
from citybrain.control_room.selection_inspector import SelectionInspector  # noqa: E402
from scripts.run_main_citybrain_omniverse_webrtc_r3_scene_prim_selection_parity import (  # noqa: E402
    PASS_STATUS,
    TASK_ID,
    boundary_audit,
    selection_parity_audit,
    webui_source_audit,
)


class OmniverseWebRtcR3ScenePrimSelectionParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = load_bundle()
        self.bindings = scene_prim_bindings()

    def test_task_identity_and_status_are_r3_scene_prim_selection(self) -> None:
        self.assertIn("SCENE-PRIM-SELECTION-PARITY", TASK_ID)
        self.assertEqual(PASS_STATUS, "PASS_OMNIVERSE_WEBRTC_R3_SCENE_PRIM_SELECTION_PARITY_WITH_LIMITATIONS")

    def test_registry_has_real_building_corridor_and_marker_prims(self) -> None:
        summary = registry_summary()
        self.assertEqual(summary["status"], "PASS")
        self.assertGreaterEqual(summary["selected_prim_count"], 3)
        self.assertTrue(summary["real_scene_used"])
        categories = {binding["category"] for binding in summary["bindings"]}
        self.assertIn("building_or_building_like_prim", categories)
        self.assertIn("corridor_road_lane_infrastructure_prim", categories)
        self.assertIn("evidence_limitation_review_marker_prim", categories)
        for binding in summary["bindings"]:
            self.assertTrue(binding["prim_path"].startswith("/"))
            self.assertEqual(binding["packet"]["no_action_state"]["execution_state"], "not_executed")
            self.assertFalse(binding["packet"]["pixel_derived_truth_used"])

    def test_barcelona_source_assets_exist_for_real_scene_bindings(self) -> None:
        for binding in self.bindings:
            source = binding["source_scene"]
            if source.get("real_scene_asset"):
                source_path = ROOT / source["source_asset_path"]
                if not source_path.exists():
                    self.skipTest("requires generated Omniverse real-scene asset outputs")
                self.assertTrue(source_path.exists(), source_path)
                self.assertGreater(source_path.stat().st_size, 1000)

    def test_overlay_manager_and_inspector_resolve_scene_prim_paths(self) -> None:
        overlay = OverlayManager(self.bundle)
        inspector = SelectionInspector(self.bundle, overlay)
        self.assertEqual(overlay.contract()["status"], "PASS")
        for binding in self.bindings:
            self.assertIsNotNone(binding_for_entity(binding["canonical_entity_id"]))
            self.assertEqual(binding_for_prim_path(binding["prim_path"])["canonical_entity_id"], binding["canonical_entity_id"])
            result = inspector.inspect_prim_path(binding["prim_path"])
            card = result["inspection_card"]
            self.assertTrue(result["found"])
            self.assertEqual(card["entity_ref"], binding["canonical_entity_id"])
            self.assertEqual(card["prim_path"], binding["prim_path"])
            self.assertEqual(card["packet_hash"], binding["packet_hash"])
            self.assertIn("What supports this:", result["visible_text"])
            self.assertIn("Unknowns / limitations:", result["visible_text"])
            self.assertIn("NoActionState:", result["visible_text"])

    def test_scene_selection_messages_match_both_directions(self) -> None:
        captures = {
            "web_messages": [selection_message(binding, "web_to_kit", "webui_scene_prim_focus_button") for binding in self.bindings],
            "kit_messages": [selection_message(binding, "kit_to_web", "kit_usd_stage_selection") for binding in self.bindings],
        }
        audit = selection_parity_audit(captures)
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["selected_prim_count"], len(self.bindings))
        for web, kit in zip(captures["web_messages"], captures["kit_messages"]):
            self.assertEqual(web["message_type"], FOCUS_REQUEST_EVENT)
            self.assertEqual(kit["message_type"], SELECTION_CHANGED_EVENT)
            self.assertEqual(web["packet_hash"], kit["packet_hash"])
            self.assertEqual(web["prim_path"], kit["prim_path"])
            self.assertFalse(web["pixel_derived_truth_used"])
            self.assertTrue(web["actual_scene_prim_selection"])

    def test_webui_source_contains_scene_prim_parity_hooks(self) -> None:
        web_main = ROOT / "outputs" / "live_citybrain_webrtc_browser_client" / "citybrain-local" / "src" / "main.ts"
        if not web_main.exists():
            self.skipTest("requires generated live CityBrain WebRTC browser client output")
        audit = webui_source_audit()
        self.assertEqual(audit["status"], "PASS")
        self.assertTrue(all(audit["checks"].values()))

    def test_boundary_audit_accepts_negative_claims_only(self) -> None:
        audit = boundary_audit(
            "local/dev stream visual context only packet truth pixel_derived_truth_used false not_executed no_action_taken",
            "not a certified physical twin; not measurement-grade geometry; not live monitoring",
        )
        self.assertEqual(audit["status"], "PASS")
        self.assertFalse(audit["forbidden_claims_present"])


if __name__ == "__main__":
    unittest.main()

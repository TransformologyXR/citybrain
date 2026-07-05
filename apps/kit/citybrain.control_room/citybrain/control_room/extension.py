from __future__ import annotations

try:
    import omni.ext  # type: ignore
except Exception:  # pragma: no cover - Kit-only dependency
    omni = None

from .capture_controls import classify_command
from .event_overlay_bridge import EventOverlayBridge
from .live_selection_bridge import process_live_selection_bridge
from .overlay_manager import OverlayManager
from .runtime_bundle import load_bundle
from .scene_prim_selection_bridge import ScenePrimSelectionBridge
from .selection_inspector import SelectionInspector
from .spatial_cockpit import SpatialCockpitWindow, experience_smoke_report
from .stage_model import ensure_browser_navigation_test_model
from .trace_panel import TracePanel
from .track_d_panel import TrackDPanel
from .viewport_navigation_bridge import ViewportNavigationBridge

BaseExt = omni.ext.IExt if omni is not None else object  # type: ignore[attr-defined]


class CityBrainControlRoomExtension(BaseExt):
    def __init__(self):
        super().__init__()
        self.bundle = None
        self.overlay_manager = None
        self.trace_panel = None
        self.track_d_panel = None
        self.selection_inspector = None
        self.spatial_cockpit = None
        self.stage_model_status = None
        self.viewport_navigation_bridge = None
        self.scene_prim_selection_bridge = None
        self.event_overlay_bridge = None

    def on_startup(self, ext_id="citybrain.control_room"):
        self.bundle = load_bundle()
        self.overlay_manager = OverlayManager(self.bundle)
        self.trace_panel = TracePanel(self.bundle)
        self.track_d_panel = TrackDPanel(self.bundle)
        self.selection_inspector = SelectionInspector(self.bundle, self.overlay_manager)
        self.spatial_cockpit = SpatialCockpitWindow(
            self.bundle,
            self.overlay_manager,
            self.selection_inspector,
        )
        cockpit_status = self.spatial_cockpit.startup()
        self.stage_model_status = ensure_browser_navigation_test_model()
        self.viewport_navigation_bridge = ViewportNavigationBridge()
        viewport_navigation_status = self.viewport_navigation_bridge.start()
        self.scene_prim_selection_bridge = ScenePrimSelectionBridge(self.spatial_cockpit)
        scene_prim_selection_status = self.scene_prim_selection_bridge.start()
        self.event_overlay_bridge = EventOverlayBridge(self.spatial_cockpit)
        event_overlay_status = self.event_overlay_bridge.start()
        print(
            "[CityBrain] Mobility Access Control Room enabled "
            f"scenario_state_ref={self.bundle['one_truth']['scenario_state_ref']} "
            f"execution_state={self.bundle['one_truth']['execution_state']} "
            f"native_panel_status={cockpit_status.get('status')}"
        )
        print(
            "[CityBrain] Browser navigation test model "
            f"status={self.stage_model_status.get('status')} "
            f"root={self.stage_model_status.get('root_prim_path')} "
            f"selected={self.stage_model_status.get('selected_prim_path')} "
            f"viewport_frame={self.stage_model_status.get('viewport_frame_status')}"
        )
        print(f"[CityBrain] Viewport navigation bridge status={viewport_navigation_status}")
        print(f"[CityBrain] R3 scene prim selection bridge status={scene_prim_selection_status}")
        print(f"[CityBrain] R4 event overlay bridge status={event_overlay_status}")
        bridge_status = process_live_selection_bridge()
        if bridge_status.get("enabled"):
            print(f"[CityBrainD13Receipt] bridge_status={bridge_status}")

    def on_shutdown(self):
        if self.event_overlay_bridge is not None:
            self.event_overlay_bridge.shutdown()
        if self.scene_prim_selection_bridge is not None:
            self.scene_prim_selection_bridge.shutdown()
        if self.viewport_navigation_bridge is not None:
            self.viewport_navigation_bridge.shutdown()
        if self.spatial_cockpit is not None:
            self.spatial_cockpit.shutdown()
        print("[CityBrain] Mobility Access Control Room shutdown")

    def command(self, command_name: str) -> dict:
        return classify_command(command_name)


def smoke_summary() -> dict:
    bundle = load_bundle()
    overlay = OverlayManager(bundle)
    inspector = SelectionInspector(bundle, overlay)
    first = inspector.inspect_first()
    return {
        "scenario_state_ref": bundle["one_truth"]["scenario_state_ref"],
        "execution_state": bundle["one_truth"]["execution_state"],
        "overlay_packet_count": len(overlay.entity_refs()),
        "trace_stage_count": len(bundle["trace"]),
        "track_d_packet_count": len(bundle["track_d"].get("packets", [])),
        "native_panel_sections": [
            "selected entity",
            "source/evidence records",
            "citations/provenance",
            "knowns or summary",
            "unknowns/limitations",
            "what this does not prove",
            "review-only / not-executed state",
            "selected object/prim path inspector",
            "overlay/review state",
        ],
        "experience_smoke": experience_smoke_report(inspector),
        "default_selection_found": first.get("found"),
        "default_selection_visible_text": first.get("visible_text"),
    }

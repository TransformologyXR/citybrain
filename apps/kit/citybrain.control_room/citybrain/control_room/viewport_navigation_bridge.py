from __future__ import annotations

import math
from typing import Any

NAVIGATION_EVENT = "citybrain.viewport.navigate"
NAVIGATION_RESULT_EVENT = "citybrainViewportNavigationResult"
TEST_MODEL_PRIMS = [
    "/CityBrainBrowserNavTest/TestCube",
    "/CityBrainBrowserNavTest/CorridorDeck",
    "/CityBrainBrowserNavTest/BlockedLaneZone",
    "/CityBrainBrowserNavTest/EvidencePinD7Observations",
    "/CityBrainBrowserNavTest/LimitationLocalReplayOnly",
    "/CityBrainBrowserNavTest/ReviewOnlyNotExecuted",
    "/CityBrainBrowserNavTest/NavigationBackdrop",
]

BOOKMARKS = {
    "bookmark_corridor_overview": {
        "position": (6.4, 5.2, 6.6),
        "target": (0.25, 0.38, 0.0),
    },
    "bookmark_blockage": {
        "position": (4.15, 2.9, 3.0),
        "target": (2.45, 0.62, -0.85),
    },
    "bookmark_evidence": {
        "position": (-0.8, 3.1, 5.1),
        "target": (0.8, 1.05, 2.85),
    },
}


def _payload_to_dict(payload: Any) -> dict[str, Any]:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    if hasattr(payload, "get_dict"):
        try:
            return dict(payload.get_dict())
        except Exception:
            return {}
    return {}


class ViewportNavigationBridge:
    """WebRTC message bridge for browser-driven viewport camera smoke tests."""

    def __init__(self) -> None:
        self._subscriptions = []
        self._started = False

    def start(self) -> dict[str, Any]:
        try:
            import carb.events  # type: ignore
            import omni.kit.app  # type: ignore
            import omni.kit.livestream.messaging as messaging  # type: ignore
            from carb.eventdispatcher import get_eventdispatcher  # type: ignore
        except Exception as exc:  # pragma: no cover - Kit-only dependency
            return {"status": "BLOCKED_LIVESTREAM_MESSAGING_UNAVAILABLE", "reason": str(exc)}

        if self._started:
            return {"status": "ALREADY_STARTED"}

        messaging.register_event_type_to_send(NAVIGATION_RESULT_EVENT)
        omni.kit.app.register_event_alias(
            carb.events.type_from_string(NAVIGATION_RESULT_EVENT),
            NAVIGATION_RESULT_EVENT,
        )
        omni.kit.app.register_event_alias(
            carb.events.type_from_string(NAVIGATION_EVENT),
            NAVIGATION_EVENT,
        )
        self._subscriptions.append(
            get_eventdispatcher().observe_event(
                observer_name="CityBrainViewportNavigationBridge:navigate",
                event_name=NAVIGATION_EVENT,
                on_event=self._on_navigate,
            )
        )
        self._started = True
        return {
            "status": "PASS",
            "incoming_event": NAVIGATION_EVENT,
            "outgoing_event": NAVIGATION_RESULT_EVENT,
        }

    def shutdown(self) -> None:
        self._subscriptions.clear()
        self._started = False

    def _on_navigate(self, event: Any) -> None:
        payload = _payload_to_dict(getattr(event, "payload", None))
        result = apply_viewport_navigation(payload)
        result["request_payload"] = payload
        print(
            "[CityBrain] Viewport navigation "
            f"action={payload.get('action')} status={result.get('status')} "
            f"camera_position={result.get('camera_position')}"
        )
        try:
            from carb.eventdispatcher import get_eventdispatcher  # type: ignore

            get_eventdispatcher().dispatch_event(NAVIGATION_RESULT_EVENT, payload=result)
        except Exception:
            pass


def apply_viewport_navigation(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        from omni.kit.viewport.utility import frame_viewport_prims, get_active_viewport  # type: ignore
        from omni.kit.viewport.utility.camera_state import ViewportCameraState  # type: ignore
        from pxr import Gf, Sdf  # type: ignore
    except Exception as exc:  # pragma: no cover - Kit-only dependency
        return {"status": "FAIL", "reason": f"viewport_api_unavailable: {exc}"}

    viewport = get_active_viewport()
    if not viewport:
        return {"status": "FAIL", "reason": "no_active_viewport"}

    action = str(payload.get("action") or "frame_test_model")
    if action == "frame_test_model":
        framed = bool(frame_viewport_prims(viewport, prims=TEST_MODEL_PRIMS))
        return {
            "status": "PASS" if framed else "FAIL",
            "action": action,
            "reason": "framed_test_model" if framed else "frame_command_failed",
            "execution_state": "not_executed",
            "pixel_derived_truth_used": False,
        }

    stage = viewport.stage
    camera_path = viewport.camera_path
    if not stage or not camera_path:
        return {"status": "FAIL", "action": action, "reason": "missing_stage_or_camera"}

    camera_prim = stage.GetPrimAtPath(camera_path)
    if not camera_prim:
        return {"status": "FAIL", "action": action, "reason": f"camera_not_found:{camera_path}"}

    target = Gf.Vec3d(0.0, 1.0, 0.0)
    coi_attr = camera_prim.GetAttribute("omni:kit:centerOfInterest")
    if not coi_attr:
        coi_attr = camera_prim.CreateAttribute("omni:kit:centerOfInterest", Sdf.ValueTypeNames.Vector3d)
    if coi_attr.Get() is None:
        coi_attr.Set(target)

    camera_state = ViewportCameraState(viewport=viewport)
    if action in BOOKMARKS:
        bookmark = BOOKMARKS[action]
        new_position = Gf.Vec3d(*bookmark["position"])
        new_target = Gf.Vec3d(*bookmark["target"])
        coi_attr.Set(new_target)
        camera_state.set_target_world(new_target, True)
        camera_state.set_position_world(new_position, True)
        return {
            "status": "PASS",
            "action": action,
            "camera_position": [round(float(new_position[0]), 4), round(float(new_position[1]), 4), round(float(new_position[2]), 4)],
            "camera_target": [round(float(new_target[0]), 4), round(float(new_target[1]), 4), round(float(new_target[2]), 4)],
            "execution_state": "not_executed",
            "review_only": True,
            "pixel_derived_truth_used": False,
        }

    try:
        target = camera_state.target_world
    except Exception:
        pass

    position = camera_state.position_world
    offset = position - target
    if offset.GetLength() < 0.001:
        offset = Gf.Vec3d(0.0, 4.0, 8.0)

    amount = float(payload.get("amount") or 1.0)
    if action in {"orbit_left", "orbit_right"}:
        degrees = 18.0 * amount
        if action == "orbit_right":
            degrees = -degrees
        radians = math.radians(degrees)
        cos_v = math.cos(radians)
        sin_v = math.sin(radians)
        new_offset = Gf.Vec3d(
            (offset[0] * cos_v) - (offset[2] * sin_v),
            offset[1],
            (offset[0] * sin_v) + (offset[2] * cos_v),
        )
    elif action in {"zoom_in", "zoom_out"}:
        scale = 0.72 if action == "zoom_in" else 1.28
        new_offset = offset * scale
    else:
        return {"status": "FAIL", "action": action, "reason": "unsupported_navigation_action"}

    new_position = target + new_offset
    camera_state.set_position_world(new_position, True)
    return {
        "status": "PASS",
        "action": action,
        "camera_position": [round(float(new_position[0]), 4), round(float(new_position[1]), 4), round(float(new_position[2]), 4)],
        "camera_target": [round(float(target[0]), 4), round(float(target[1]), 4), round(float(target[2]), 4)],
        "execution_state": "not_executed",
        "review_only": True,
        "pixel_derived_truth_used": False,
    }

from __future__ import annotations

from typing import Any

from .scene_prim_selection_registry import (
    FOCUS_REQUEST_EVENT,
    FOCUS_RESULT_EVENT,
    SELECTION_CHANGED_EVENT,
    binding_for_entity,
    binding_for_prim_path,
    selection_message,
)


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


class ScenePrimSelectionBridge:
    """Packet-backed WebUI <-> Kit prim selection bridge for R3 parity."""

    def __init__(self, spatial_cockpit=None) -> None:
        self.spatial_cockpit = spatial_cockpit
        self._subscriptions: list[Any] = []
        self._stage_subscription = None
        self._started = False
        self._last_selected_prim_path: str | None = None

    def start(self) -> dict[str, Any]:
        try:
            import carb.events  # type: ignore
            import omni.kit.app  # type: ignore
            import omni.kit.livestream.messaging as messaging  # type: ignore
            import omni.usd  # type: ignore
            from carb.eventdispatcher import get_eventdispatcher  # type: ignore
        except Exception as exc:  # pragma: no cover - Kit-only dependency
            return {"status": "BLOCKED_LIVESTREAM_OR_USD_API_UNAVAILABLE", "reason": str(exc)}

        if self._started:
            return {"status": "ALREADY_STARTED"}

        for event_name in (SELECTION_CHANGED_EVENT, FOCUS_RESULT_EVENT):
            messaging.register_event_type_to_send(event_name)
            omni.kit.app.register_event_alias(carb.events.type_from_string(event_name), event_name)
        omni.kit.app.register_event_alias(carb.events.type_from_string(FOCUS_REQUEST_EVENT), FOCUS_REQUEST_EVENT)

        self._subscriptions.append(
            get_eventdispatcher().observe_event(
                observer_name="CityBrainScenePrimSelectionBridge:focus_request",
                event_name=FOCUS_REQUEST_EVENT,
                on_event=self._on_focus_request,
            )
        )
        try:
            context = omni.usd.get_context()
            stream = context.get_stage_event_stream()
            self._stage_subscription = stream.create_subscription_to_pop(
                self._on_stage_event,
                name="citybrain-scene-prim-selection-bridge",
            )
        except Exception as exc:
            return {"status": "BLOCKED_STAGE_SELECTION_STREAM_UNAVAILABLE", "reason": str(exc)}

        self._started = True
        return {
            "status": "PASS",
            "incoming_event": FOCUS_REQUEST_EVENT,
            "outgoing_events": [SELECTION_CHANGED_EVENT, FOCUS_RESULT_EVENT],
            "actual_scene_prim_selection": True,
            "pixel_derived_truth_used": False,
        }

    def shutdown(self) -> None:
        self._subscriptions.clear()
        self._stage_subscription = None
        self._started = False

    def _on_focus_request(self, event: Any) -> None:
        payload = _payload_to_dict(getattr(event, "payload", None))
        result = self.apply_focus_request(payload)
        self._dispatch(FOCUS_RESULT_EVENT, result)

    def _on_stage_event(self, event: Any) -> None:
        try:
            import omni.usd  # type: ignore

            event_type = int(event.type)
            if event_type != int(omni.usd.StageEventType.SELECTION_CHANGED):
                return
            selected = list(omni.usd.get_context().get_selection().get_selected_prim_paths())
        except Exception:
            return
        if not selected:
            return
        binding = binding_for_prim_path(selected[0])
        if binding is None:
            return
        message = selection_message(binding, "kit_to_web", "kit_usd_stage_selection")
        message["selected_prim_path_observed"] = selected[0]
        self._last_selected_prim_path = binding["prim_path"]
        if self.spatial_cockpit is not None:
            try:
                self.spatial_cockpit.inspect_prim_path(binding["prim_path"], "r3-kit-selection-changed")
            except Exception:
                pass
        self._dispatch(SELECTION_CHANGED_EVENT, message)

    def apply_focus_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        binding = binding_for_entity(payload.get("canonical_entity_id")) or binding_for_prim_path(payload.get("prim_path"))
        if binding is None:
            return {
                "schema_version": "citybrain.omniverse.webrtc.scene_prim_focus_result.r3",
                "status": "FAIL",
                "reason": "unknown_scene_prim_binding",
                "request_payload": payload,
                "pixel_derived_truth_used": False,
            }

        selection_status = self._select_prim(binding["prim_path"])
        frame_status = self._frame_prim(binding["prim_path"])
        message = selection_message(binding, "kit_to_web", "webui_focus_request_applied_in_kit")
        message["request_message_id"] = payload.get("message_id")
        if self.spatial_cockpit is not None:
            try:
                self.spatial_cockpit.inspect_prim_path(binding["prim_path"], "r3-web-focus-request")
            except Exception:
                pass
        self._dispatch(SELECTION_CHANGED_EVENT, message)
        return {
            "schema_version": "citybrain.omniverse.webrtc.scene_prim_focus_result.r3",
            "status": "PASS" if selection_status.get("status") == "PASS" else "FAIL",
            "request_payload": payload,
            "selected_binding": binding,
            "selection_status": selection_status,
            "frame_status": frame_status,
            "emitted_selection_changed": message,
            "actual_scene_prim_selection": True,
            "stream_visual_context_only": True,
            "pixel_derived_truth_used": False,
        }

    def _select_prim(self, prim_path: str) -> dict[str, Any]:
        try:
            import omni.usd  # type: ignore

            selection = omni.usd.get_context().get_selection()
            selection.set_selected_prim_paths([prim_path], True)
            return {"status": "PASS", "selected_prim_paths": [prim_path]}
        except Exception as exc:  # pragma: no cover - Kit-only dependency
            return {"status": "FAIL", "reason": str(exc), "selected_prim_paths": []}

    def _frame_prim(self, prim_path: str) -> dict[str, Any]:
        try:
            from omni.kit.viewport.utility import frame_viewport_prims, get_active_viewport  # type: ignore
        except Exception as exc:  # pragma: no cover - Kit-only dependency
            return {"status": "BLOCKED_VIEWPORT_API_UNAVAILABLE", "reason": str(exc)}

        viewport = get_active_viewport()
        if not viewport:
            return {"status": "BLOCKED_NO_ACTIVE_VIEWPORT"}
        framed = bool(frame_viewport_prims(viewport, prims=[prim_path]))
        return {"status": "PASS" if framed else "FAIL", "prim_path": prim_path}

    def _dispatch(self, event_name: str, payload: dict[str, Any]) -> None:
        try:
            from carb.eventdispatcher import get_eventdispatcher  # type: ignore

            get_eventdispatcher().dispatch_event(event_name, payload=payload)
        except Exception:
            pass

from __future__ import annotations

from typing import Any

from .event_overlay_registry import (
    EVENT_FOCUS_REQUEST,
    EVENT_FOCUS_RESULT,
    EVENT_OVERLAY_CLEAR,
    EVENT_OVERLAY_UPSERT,
    EVENT_SELECTION_CHANGED,
    event_fixtures,
    event_for_id,
    event_for_marker_prim,
    event_message,
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


def _runtime_event_fixtures() -> list[dict[str, Any]]:
    fixtures = list(event_fixtures())
    try:
        from .real_scene_review_loop_registry import real_scene_event_fixtures

        fixtures.extend(real_scene_event_fixtures())
    except Exception:
        pass
    return fixtures


def _runtime_event_for_id(event_id: str | None) -> dict[str, Any] | None:
    event = event_for_id(event_id)
    if event is not None:
        return event
    try:
        from .real_scene_review_loop_registry import real_scene_event_for_id

        return real_scene_event_for_id(event_id)
    except Exception:
        return None


def _runtime_event_for_marker_prim(prim_path: str | None) -> dict[str, Any] | None:
    event = event_for_marker_prim(prim_path)
    if event is not None:
        return event
    try:
        from .real_scene_review_loop_registry import real_scene_event_for_marker_prim

        return real_scene_event_for_marker_prim(prim_path)
    except Exception:
        return None


def _runtime_event_message(
    fixture: dict[str, Any],
    direction: str,
    selection_source: str,
    message_id: str | None = None,
) -> dict[str, Any]:
    if fixture.get("r5_real_scene_review_loop"):
        try:
            from .real_scene_review_loop_registry import real_scene_event_message

            return real_scene_event_message(fixture, direction, selection_source, message_id)
        except Exception:
            pass
    return event_message(fixture, direction, selection_source, message_id)


class EventOverlayBridge:
    """Packet-backed Kit/WebUI event overlay parity bridge for local replay."""

    def __init__(self, spatial_cockpit=None) -> None:
        self.spatial_cockpit = spatial_cockpit
        self._subscriptions: list[Any] = []
        self._stage_subscription = None
        self._started = False

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

        for event_name in (EVENT_SELECTION_CHANGED, EVENT_OVERLAY_UPSERT, EVENT_OVERLAY_CLEAR, EVENT_FOCUS_RESULT):
            messaging.register_event_type_to_send(event_name)
            omni.kit.app.register_event_alias(carb.events.type_from_string(event_name), event_name)
        omni.kit.app.register_event_alias(carb.events.type_from_string(EVENT_FOCUS_REQUEST), EVENT_FOCUS_REQUEST)

        self._subscriptions.append(
            get_eventdispatcher().observe_event(
                observer_name="CityBrainEventOverlayBridge:focus_request",
                event_name=EVENT_FOCUS_REQUEST,
                on_event=self._on_focus_request,
            )
        )
        try:
            context = omni.usd.get_context()
            stream = context.get_stage_event_stream()
            self._stage_subscription = stream.create_subscription_to_pop(
                self._on_stage_event,
                name="citybrain-event-overlay-bridge",
            )
        except Exception as exc:
            return {"status": "BLOCKED_STAGE_SELECTION_STREAM_UNAVAILABLE", "reason": str(exc)}

        self._started = True
        self.publish_overlay_upserts()
        return {
            "status": "PASS",
            "incoming_event": EVENT_FOCUS_REQUEST,
            "outgoing_events": [EVENT_SELECTION_CHANGED, EVENT_OVERLAY_UPSERT, EVENT_FOCUS_RESULT],
            "event_fixture_count": len(_runtime_event_fixtures()),
            "pixel_derived_truth_used": False,
        }

    def shutdown(self) -> None:
        self._subscriptions.clear()
        self._stage_subscription = None
        self._started = False

    def publish_overlay_upserts(self) -> list[dict[str, Any]]:
        messages = [
            _runtime_event_message(fixture, "kit_overlay_upsert", "kit_event_overlay_registry")
            for fixture in _runtime_event_fixtures()
        ]
        for message in messages:
            self._dispatch(EVENT_OVERLAY_UPSERT, message)
        return messages

    def _on_focus_request(self, event: Any) -> None:
        payload = _payload_to_dict(getattr(event, "payload", None))
        result = self.apply_focus_request(payload)
        self._dispatch(EVENT_FOCUS_RESULT, result)

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
        fixture = _runtime_event_for_marker_prim(selected[0])
        if fixture is None:
            return
        message = _runtime_event_message(fixture, "kit_to_web", "kit_event_marker_selection")
        message["selected_marker_prim_path_observed"] = selected[0]
        if self.spatial_cockpit is not None:
            try:
                self.spatial_cockpit.inspect_prim_path(fixture["marker_prim_path"], "r4-kit-event-marker-selection")
            except Exception:
                pass
        self._dispatch(EVENT_SELECTION_CHANGED, message)

    def apply_focus_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        fixture = _runtime_event_for_id(payload.get("event_id")) or _runtime_event_for_marker_prim(payload.get("marker_prim_path"))
        if fixture is None:
            return {
                "schema_version": "citybrain.omniverse.webrtc.event_focus_result.r4",
                "status": "FAIL",
                "reason": "unknown_event_overlay",
                "request_payload": payload,
                "pixel_derived_truth_used": False,
            }

        selection_status = self._select_prim(fixture["marker_prim_path"])
        frame_status = self._frame_prim(fixture["marker_prim_path"])
        message = _runtime_event_message(fixture, "kit_to_web", "webui_event_focus_request_applied_in_kit")
        message["request_message_id"] = payload.get("message_id")
        if self.spatial_cockpit is not None:
            try:
                self.spatial_cockpit.inspect_prim_path(fixture["marker_prim_path"], "r4-web-event-focus-request")
            except Exception:
                pass
        self._dispatch(EVENT_SELECTION_CHANGED, message)
        return {
            "schema_version": "citybrain.omniverse.webrtc.event_focus_result.r4",
            "status": "PASS" if selection_status.get("status") == "PASS" else "FAIL",
            "request_payload": payload,
            "selected_event": fixture,
            "selection_status": selection_status,
            "frame_status": frame_status,
            "emitted_event_selection_changed": message,
            "actual_event_overlay_selection": True,
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

from __future__ import annotations

from dataclasses import dataclass

from .contracts import R0ValidationError, load_r0_contract


@dataclass(frozen=True)
class EventTypeRegistry:
    allowed_event_types: tuple[str, ...]
    forbidden_event_types: tuple[str, ...]

    def validate(self, event_type: str) -> str:
        if event_type in self.forbidden_event_types:
            raise R0ValidationError(f"forbidden event type: {event_type}")
        if event_type not in self.allowed_event_types:
            raise R0ValidationError(f"unknown event type: {event_type}")
        return event_type


def load_event_type_registry() -> EventTypeRegistry:
    registry = load_r0_contract()["event_type_registry"]
    return EventTypeRegistry(
        allowed_event_types=tuple(registry["allowed_event_types"]),
        forbidden_event_types=tuple(registry["forbidden_event_types"]),
    )


def load_source_class_registry() -> dict[str, dict]:
    return load_r0_contract()["source_class_registry"]["source_classes"]

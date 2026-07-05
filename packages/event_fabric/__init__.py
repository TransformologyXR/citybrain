"""Local/replay Event Fabric runtime spine for the active R0.1 contract."""

from .contracts import (
    ACTIVE_EVENT_VERSION,
    ACTIVE_SCHEMA_VERSION,
    R0_ROOT,
    R0_1_CONTRACT_ROOT,
    R0ValidationError,
    build_event_from_candidate,
    load_r0_contract,
    normalize_legacy_event,
    validate_event_envelope,
    validate_materialized_state,
    validate_overlay_packet,
    validate_query_result_packet,
)
from .log import append_event, read_event_log, write_event_log
from .materialize import materialize_review_state
from .query import (
    build_overlay_packets_for_events,
    build_query_result_packet,
    get_event_trace,
    get_events_for_candidate_observation,
    get_events_for_source_class,
    list_active_review_events,
    list_quarantined_observations,
    list_unresolved_observations,
)
from .registry import EventTypeRegistry, load_event_type_registry, load_source_class_registry
from .replay import replay_events

__all__ = [
    "EventTypeRegistry",
    "ACTIVE_EVENT_VERSION",
    "ACTIVE_SCHEMA_VERSION",
    "R0ValidationError",
    "R0_ROOT",
    "R0_1_CONTRACT_ROOT",
    "append_event",
    "build_event_from_candidate",
    "build_overlay_packets_for_events",
    "build_query_result_packet",
    "get_event_trace",
    "get_events_for_candidate_observation",
    "get_events_for_source_class",
    "list_active_review_events",
    "list_quarantined_observations",
    "list_unresolved_observations",
    "load_event_type_registry",
    "load_r0_contract",
    "load_source_class_registry",
    "materialize_review_state",
    "normalize_legacy_event",
    "read_event_log",
    "replay_events",
    "validate_event_envelope",
    "validate_materialized_state",
    "validate_overlay_packet",
    "validate_query_result_packet",
    "write_event_log",
]

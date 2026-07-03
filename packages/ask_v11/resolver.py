"""G2 deterministic intent and concept-binding resolver for ASK v1.1."""

from __future__ import annotations

import re
from typing import Any

from .concept_bindings import ConceptBindingRegistry
from .fixtures import FIXTURE_ALIASES
from .packets import (
    BoundaryResult,
    BoundaryScreenPacket,
    ConceptBinding,
    ContextFlags,
    FlowRunInput,
    IntentFamily,
    IntentPacket,
)


CONFIDENCE_THRESHOLD = 0.6


STRUCTURED_REF_PATTERN = re.compile(
    r"\b(?:asset|building|community|source|queue):[a-z0-9][a-z0-9:_-]*\b",
    re.IGNORECASE,
)


def _normalize_query(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _first_session_value(session_state: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = session_state.get(key)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, list) and value:
            first = value[0]
            if isinstance(first, str) and first:
                return first
        if isinstance(value, dict):
            ref = value.get("ref") or value.get("entity_ref") or value.get("source_record_ref")
            if isinstance(ref, str) and ref:
                return ref
    return None


def extract_structured_refs(query: str) -> list[str]:
    return [match.group(0).rstrip(".,?!;:") for match in STRUCTURED_REF_PATTERN.finditer(query)]


def fixture_anchor_for_query(query: str) -> str | None:
    normalized = _normalize_query(query)
    for alias, ref in FIXTURE_ALIASES.items():
        if alias in normalized:
            return ref
    return None


def selected_or_session_anchor(flow_input: FlowRunInput) -> str | None:
    return (
        flow_input.selected_item_ref
        or _first_session_value(
            flow_input.session_state,
            ("selected_item", "active_entity", "active_entities", "active_thread"),
        )
    )


def _extract_anchor(flow_input: FlowRunInput, query: str) -> tuple[str | None, str | None]:
    structured_refs = extract_structured_refs(query)
    if structured_refs:
        return structured_refs[0], "explicit_ref"
    selected_anchor = selected_or_session_anchor(flow_input)
    if selected_anchor:
        return selected_anchor, "selected_or_session"
    fixture_anchor = fixture_anchor_for_query(query)
    if fixture_anchor:
        return fixture_anchor, "fixture_alias"
    return None, None


def _help_topic(query: str) -> str:
    if "export" in query:
        return "export"
    if "alert" in query or "notify" in query:
        return "alerting_capability"
    if "ticket" in query:
        return "ticket_creation_capability"
    if "case" in query:
        return "case_creation_capability"
    if "dispatch" in query:
        return "dispatch_capability"
    return "general_capability"


def _external_concepts(query: str) -> list[str]:
    concepts: list[str] = []
    if "charger" in query and any(term in query for term in ("availability", "available", "occupancy", "fault")):
        concepts.append("charger availability")
    if "weather" in query:
        concepts.append("weather")
    if "live service" in query or "outage" in query or "service status" in query:
        concepts.append("live status")
    if "official" in query and ("ticket" in query or "case" in query):
        concepts.append("official case")
    if "certified geometry" in query or "certified boundary" in query:
        concepts.append("certified geometry")
    if "legal determination" in query or "planning determination" in query:
        concepts.append("planning determination")
    if "access impact" in query or "access blockage" in query or "confirmed blockage" in query:
        concepts.append("access impact")
    return concepts


def _is_board_meta(query: str) -> bool:
    return any(
        phrase in query
        for phrase in (
            "can this board",
            "can this system",
            "what can this cockpit",
            "what can this board",
            "how do i export",
            "does this create a case",
            "can this system create official tickets",
        )
    )


def _is_source_record_profile(query: str, refs: list[str]) -> bool:
    return any(ref.startswith("source:") for ref in refs) or any(
        phrase in query
        for phrase in ("source row", "source record", "show the source", "explain record")
    )


def _is_patch_queue_query(query: str, refs: list[str]) -> bool:
    return any(ref.startswith("queue:") for ref in refs) or any(
        term in query
        for term in ("queue", "pending review", "review items", "patch queue", "unresolved")
    )


def _is_entity_profile(query: str, anchor: str | None) -> bool:
    if anchor and any(anchor.startswith(prefix) for prefix in ("asset:", "building:", "community:")):
        return any(
            phrase in query
            for phrase in (
                "what do we know",
                "show profile",
                "profile for",
                "what is this",
                "this asset",
                "this building",
                "this community",
            )
        )
    return any(phrase in query for phrase in ("show profile for", "profile for asset:", "profile for building:"))


def _is_city_subject_query(query: str) -> bool:
    return any(
        phrase in query
        for phrase in (
            "what is happening",
            "what happened",
            "what do we know",
            "tell me about",
            "what records",
            "near this",
            "around this",
            "for this corridor",
            "for this asset",
            "for this building",
        )
    )


def _lookup_bindings(
    registry: ConceptBindingRegistry,
    concepts: list[str],
) -> list[ConceptBinding]:
    seen: set[str] = set()
    unique = []
    for concept in concepts:
        if concept not in seen:
            seen.add(concept)
            unique.append(concept)
    return registry.lookup_many(unique)


def intent_and_binding_resolver(
    flow_input: FlowRunInput,
    boundary_packet: BoundaryScreenPacket,
    concept_registry: ConceptBindingRegistry | None = None,
) -> IntentPacket:
    registry = concept_registry or ConceptBindingRegistry()
    if boundary_packet.boundary != BoundaryResult.clear:
        return IntentPacket(
            intent_family=IntentFamily.boundary_refusal,
            confidence=1.0,
            resolver_telemetry={
                "reason_codes": ["g1_non_clear"],
                "boundary": boundary_packet.boundary.value,
            },
        )

    query = _normalize_query(flow_input.raw_query)
    refs = extract_structured_refs(query)
    anchor, anchor_source = _extract_anchor(flow_input, query)
    concepts = _external_concepts(query)
    concept_bindings = _lookup_bindings(registry, concepts)
    telemetry: dict[str, Any] = {
        "reason_codes": [],
        "args": {},
        "extracted_refs": refs,
    }
    if anchor:
        telemetry["anchor_source"] = anchor_source

    if _is_board_meta(query):
        telemetry["reason_codes"].append("board_meta_product_capability")
        telemetry["args"] = {"help_topic": _help_topic(query)}
        return IntentPacket(
            intent_family=IntentFamily.board_meta,
            concept_bindings=concept_bindings,
            context_flags=ContextFlags(requires_selected_item=False),
            confidence=0.95,
            resolver_telemetry=telemetry,
        )

    if concepts:
        telemetry["reason_codes"].append("known_external_context_need")
        telemetry["args"] = {"concept": concept_bindings[0].family or concepts[0]}
        if anchor:
            telemetry["args"]["subject_ref"] = anchor
        return IntentPacket(
            intent_family=IntentFamily.external_context_need,
            subject_candidates=[anchor] if anchor else [],
            concept_bindings=concept_bindings,
            context_flags=ContextFlags(requires_selected_item=False),
            confidence=0.9,
            resolver_telemetry=telemetry,
        )

    if _is_source_record_profile(query, refs):
        source_ref = next((ref for ref in refs if ref.startswith("source:")), anchor)
        telemetry["reason_codes"].append("source_record_profile")
        if source_ref:
            telemetry["args"] = {"source_record_ref": source_ref}
        return IntentPacket(
            intent_family=IntentFamily.source_record_profile,
            subject_candidates=[source_ref] if source_ref else [],
            context_flags=ContextFlags(requires_selected_item=source_ref is None),
            clarification_candidates=["source_record_ref"] if source_ref is None else [],
            confidence=0.86,
            resolver_telemetry=telemetry,
        )

    if _is_patch_queue_query(query, refs):
        queue_ref = next((ref for ref in refs if ref.startswith("queue:")), None)
        queue_filter = "pending" if "pending" in query else (queue_ref or "all")
        telemetry["reason_codes"].append("patch_queue_query")
        telemetry["args"] = {"queue_filter": queue_filter}
        return IntentPacket(
            intent_family=IntentFamily.patch_queue_query,
            subject_candidates=[queue_ref] if queue_ref else [],
            confidence=0.88,
            resolver_telemetry=telemetry,
        )

    if _is_entity_profile(query, anchor):
        telemetry["reason_codes"].append("entity_profile")
        if anchor:
            telemetry["args"] = {"entity_ref": anchor}
        return IntentPacket(
            intent_family=IntentFamily.entity_profile,
            subject_candidates=[anchor] if anchor else [],
            context_flags=ContextFlags(requires_selected_item=anchor is None),
            clarification_candidates=["entity_ref"] if anchor is None else [],
            confidence=0.86 if anchor else 0.72,
            resolver_telemetry=telemetry,
        )

    if _is_city_subject_query(query) or anchor:
        telemetry["reason_codes"].append("subject_answer")
        if anchor:
            telemetry["args"] = {"subject_ref": anchor}
        return IntentPacket(
            intent_family=IntentFamily.subject_answer,
            subject_candidates=[anchor] if anchor else [],
            context_flags=ContextFlags(requires_selected_item=anchor is None),
            clarification_candidates=["subject_ref"] if anchor is None else [],
            confidence=0.78 if anchor else 0.65,
            resolver_telemetry=telemetry,
        )

    telemetry["reason_codes"].append("unknown_intent")
    return IntentPacket(
        intent_family=IntentFamily.unknown,
        context_flags=ContextFlags(requires_selected_item=False),
        ambiguity_flags=["unsupported_or_low_information_query"],
        clarification_candidates=["intent_or_subject"],
        confidence=0.45,
        resolver_telemetry=telemetry,
    )

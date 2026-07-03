"""G1 deterministic boundary screen for ASK v1.1."""

from __future__ import annotations

import re

from .packets import BoundaryResult, BoundaryScreenPacket, FlowRunInput


PRODUCT_META_PATTERNS = (
    r"\bcan\s+(this|the)\s+(board|system|cockpit|app|tool)\b",
    r"\bwhat\s+can\s+(this|the)\s+(board|system|cockpit|app|tool)\s+do\b",
    r"\bhow\s+do\s+i\s+export\b",
    r"\bdoes\s+this\s+(create|open|issue|send|alert)\b",
    r"\bcan\s+this\s+system\s+create\s+official\s+tickets\b",
)

ACTION_PATTERNS = (
    r"^\s*(alert|notify|send)\b.*\b(now|someone|police|operator|inspector|team)?\b",
    r"^\s*(create|open|issue|file)\b.*\b(case|ticket|violation)\b",
    r"^\s*dispatch\b",
    r"^\s*route\b.*\btraffic\b",
    r"^\s*send\b.*\b(police|inspector|operator|team)\b",
)

PREDICTION_PATTERNS = (
    r"\bwill\s+.*\b(get worse|become|happen|fail|spread)\b",
    r"\bpredict\b",
    r"\bforecast\b",
    r"\bis\s+this\s+legally\s+non[- ]compliant\b",
    r"\bfind\s+the\s+guilty\b",
)

IDENTITY_PATTERNS = (
    r"\bwho\s+is\s+(personally\s+)?responsible\b",
    r"\bidentify\s+the\s+(person|individual)\b",
    r"\bname\s+the\s+(person|individual)\b",
    r"\bwho\s+is\s+guilty\b",
)

OUT_OF_SCOPE_PATTERNS = (
    r"\bmedical diagnosis\b",
    r"\blegal advice\b",
    r"\binvestment advice\b",
)

AMBIGUOUS_PATTERNS = (
    r"\bshould\s+i\s+(call|report|send|dispatch)\b",
    r"\bdo\s+something\s+about\s+this\b",
)


def _normalize_query(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _matches(patterns: tuple[str, ...], query: str) -> bool:
    return any(re.search(pattern, query) for pattern in patterns)


def boundary_screen(flow_input: FlowRunInput) -> BoundaryScreenPacket:
    query = _normalize_query(flow_input.raw_query)
    reason_codes: list[str] = []

    if _matches(PRODUCT_META_PATTERNS, query):
        reason_codes.append("product_or_board_meta_question")
        return BoundaryScreenPacket(
            boundary=BoundaryResult.clear,
            reason_codes=reason_codes,
            confidence=0.95,
        )
    if _matches(ACTION_PATTERNS, query):
        reason_codes.append("imperative_external_action")
        return BoundaryScreenPacket(
            boundary=BoundaryResult.action_shaped,
            reason_codes=reason_codes,
            confidence=0.95,
        )
    if _matches(IDENTITY_PATTERNS, query):
        reason_codes.append("natural_person_or_blame_attribution")
        return BoundaryScreenPacket(
            boundary=BoundaryResult.identity_or_person,
            reason_codes=reason_codes,
            confidence=0.9,
        )
    if _matches(PREDICTION_PATTERNS, query):
        reason_codes.append("prediction_or_legal_finding_shape")
        return BoundaryScreenPacket(
            boundary=BoundaryResult.prediction_or_finding,
            reason_codes=reason_codes,
            confidence=0.9,
        )
    if _matches(OUT_OF_SCOPE_PATTERNS, query):
        reason_codes.append("out_of_scope_domain")
        return BoundaryScreenPacket(
            boundary=BoundaryResult.out_of_scope_domain,
            reason_codes=reason_codes,
            confidence=0.9,
        )
    if _matches(AMBIGUOUS_PATTERNS, query):
        reason_codes.append("ambiguous_boundary")
        return BoundaryScreenPacket(
            boundary=BoundaryResult.ambiguous_boundary,
            reason_codes=reason_codes,
            confidence=0.75,
        )

    reason_codes.append("no_guardrail_boundary_hit")
    return BoundaryScreenPacket(
        boundary=BoundaryResult.clear,
        reason_codes=reason_codes,
        confidence=0.85,
    )

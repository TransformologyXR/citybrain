"""Deterministic render validation for ASK v1.1 G8."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from .packets import AnswerPacket


class RenderValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool
    errors: list[str] = Field(default_factory=list)


RISKY_CAUSAL_PATTERNS = (
    r"\bcaused\b",
    r"\bconfirmed impact\b",
    r"\bblocked by\b",
    r"\bis blocked\b",
    r"\bwas blocked\b",
    r"\bproves\b",
    r"\bwill\b",
    r"\baffected by\b",
)

OFFICIAL_ACTION_PATTERNS = (
    r"\bticket created\b",
    r"\bcase opened\b",
    r"\balert sent\b",
    r"\bdispatched\b",
    r"\bviolation issued\b",
)


def _is_negated_line(line: str) -> bool:
    normalized = line.strip().lower()
    return normalized.startswith(
        (
            "- no claim",
            "no claim",
            "- cannot claim",
            "cannot claim",
            "- unknown",
            "unknown",
            "- coverage",
            "coverage",
            "not executed",
            "- not executed",
        )
    )


def _risky_lines(rendered_text: str) -> list[str]:
    return [line for line in rendered_text.splitlines() if not _is_negated_line(line)]


def _allowed_sources(answer_packet: AnswerPacket) -> set[str]:
    allowed: set[str] = set()
    for citation in answer_packet.citations:
        allowed.add(citation.source_ref)
        if citation.label:
            allowed.add(citation.label)
    return allowed


def _source_mentions(rendered_text: str) -> list[str]:
    mentions: list[str] = []
    for match in re.finditer(r"\bSource:\s*([^\n;]+)", rendered_text):
        mentions.append(match.group(1).strip())
    return mentions


def validate_render(rendered_text: str, answer_packet: AnswerPacket) -> RenderValidationResult:
    errors: list[str] = []
    text_lower = rendered_text.lower()

    if "raw_query" in text_lower:
        errors.append("render includes raw_query")

    for cannot_claim in answer_packet.cannot_claim:
        if cannot_claim and cannot_claim not in rendered_text:
            errors.append(f"missing cannot_claim text: {cannot_claim}")

    risky = "\n".join(_risky_lines(rendered_text)).lower()
    for pattern in RISKY_CAUSAL_PATTERNS:
        if re.search(pattern, risky):
            errors.append(f"unsupported causal/projection phrase: {pattern}")
    for pattern in OFFICIAL_ACTION_PATTERNS:
        if re.search(pattern, risky):
            errors.append(f"unsupported official action phrase: {pattern}")

    cannot_text = " ".join(answer_packet.cannot_claim).lower()
    if ("live" in cannot_text or "current" in cannot_text) and re.search(
        r"\blive\b.*\b(available|known|active|open|current)\b", risky
    ):
        errors.append("live external claim made despite cannot_claim")
    if ("certified" in cannot_text or "legal" in cannot_text) and re.search(
        r"\b(certified|legal|official)\b.*\b(confirmed|determined|valid|approved)\b",
        risky,
    ):
        errors.append("certified/legal claim made despite cannot_claim")

    allowed_sources = _allowed_sources(answer_packet)
    for source_name in _source_mentions(rendered_text):
        if allowed_sources and source_name not in allowed_sources:
            errors.append(f"source not present in citations: {source_name}")

    no_data_signal = any("no retained" in item.lower() for item in answer_packet.unknowns)
    if no_data_signal and not any(
        phrase in text_lower for phrase in ("no retained", "no data", "not found", "unknown")
    ):
        errors.append("no-data/unknown wording missing")

    downgrade_signal = any(
        "nearby/proximity context only" in item.lower()
        for item in answer_packet.knowns + answer_packet.cannot_claim
    )
    if downgrade_signal and re.search(r"\b(confirmed impact|affected by|blocked by|caused)\b", risky):
        errors.append("render attempts to un-downgrade proximity claim")

    return RenderValidationResult(valid=not errors, errors=errors)

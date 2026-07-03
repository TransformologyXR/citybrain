"""G8 safe rendering for ASK v1.1."""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field

from .packets import AnswerPacket
from .render_validation import RenderValidationResult, validate_render


class RenderedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    validation: RenderValidationResult
    degraded: bool = False
    validation_errors: list[str] = Field(default_factory=list)


def _section(title: str, items: list[str]) -> list[str]:
    if not items:
        return []
    return [f"{title}:"] + [f"- {item}" for item in items]


def deterministic_render(answer_packet: AnswerPacket) -> str:
    lines: list[str] = []
    lines.extend(_section("Known", answer_packet.knowns))
    lines.extend(_section("Unknown", answer_packet.unknowns))
    lines.extend([f"- No claim: {item}" for item in answer_packet.cannot_claim])
    if answer_packet.coverage_note:
        lines.append(f"Coverage: {answer_packet.coverage_note.summary}")
        for limitation in answer_packet.coverage_note.limitations:
            lines.append(f"- Coverage limit: {limitation}")
    if answer_packet.citations:
        lines.append("Citations:")
        for citation in answer_packet.citations:
            label = citation.label or citation.source_ref
            lines.append(f"- Source: {citation.source_ref}; Label: {label}")
    if answer_packet.not_executed:
        lines.append("Not executed:")
        for item in answer_packet.not_executed:
            lines.append(f"- Not executed: {item}")
    if answer_packet.safe_next_looks:
        lines.append("Safe next looks:")
        for item in answer_packet.safe_next_looks:
            lines.append(f"- {item}")
    return "\n".join(lines) if lines else "No retained answer content is available."


def render_answer(
    answer_packet: AnswerPacket,
    proposal_fn: Callable[[AnswerPacket], str] | None = None,
) -> RenderedResponse:
    proposal = proposal_fn(answer_packet) if proposal_fn else deterministic_render(answer_packet)
    validation = validate_render(proposal, answer_packet)
    if validation.valid:
        return RenderedResponse(text=proposal, validation=validation, degraded=False)

    degraded_text = (
        "Unable to render final answer safely. "
        "Render validation failed: " + "; ".join(validation.errors)
    )
    return RenderedResponse(
        text=degraded_text,
        validation=validation,
        degraded=True,
        validation_errors=list(validation.errors),
    )

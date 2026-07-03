"""G3 route selection and template compilation for ASK v1.1."""

from __future__ import annotations

from .packets import (
    AnswerContract,
    BoundaryResult,
    BoundaryScreenPacket,
    ClarificationPacket,
    ExecutionContract,
    IntentFamily,
    IntentPacket,
    RouteKind,
    RouteSelection,
)
from .resolver import CONFIDENCE_THRESHOLD
from .templates import RegistryValidationError, TemplateNotFoundError, TemplateRegistry


TEMPLATE_FOR_INTENT: dict[IntentFamily, tuple[str, str, RouteKind]] = {
    IntentFamily.board_meta: ("board_meta_help", "1.0", RouteKind.ui_help),
    IntentFamily.entity_profile: ("entity_profile", "1.0", RouteKind.template_call),
    IntentFamily.subject_answer: ("subject_answer", "1.0", RouteKind.template_call),
    IntentFamily.source_record_profile: (
        "source_record_profile",
        "1.0",
        RouteKind.template_call,
    ),
    IntentFamily.patch_queue_query: ("patch_queue_query", "1.0", RouteKind.template_call),
    IntentFamily.external_context_need: (
        "external_context_need",
        "1.0",
        RouteKind.template_call,
    ),
}


def _sink_contract(route: RouteSelection, shape: str, reason: str) -> ExecutionContract:
    return ExecutionContract(
        route=route,
        args={"reason": reason},
        answer_contract=AnswerContract(shape=shape),
    )


def refusal_contract(refusal_class: str, reason: str) -> ExecutionContract:
    return _sink_contract(
        RouteSelection(kind=RouteKind.refuse, refusal_class=refusal_class),
        "refusal_sink",
        reason,
    )


def gap_contract(gap_id: str, reason: str) -> ExecutionContract:
    return _sink_contract(
        RouteSelection(kind=RouteKind.gap, gap_id=gap_id),
        "gap_sink",
        reason,
    )


def route_select_and_compile(
    intent_packet: IntentPacket,
    boundary_packet: BoundaryScreenPacket | None = None,
    template_registry: TemplateRegistry | None = None,
) -> ExecutionContract | ClarificationPacket:
    if boundary_packet and boundary_packet.boundary != BoundaryResult.clear:
        return refusal_contract(
            boundary_packet.boundary.value,
            "G1 boundary screen was non-clear; template execution is blocked.",
        )
    if intent_packet.intent_family == IntentFamily.boundary_refusal:
        refusal_class = str(intent_packet.resolver_telemetry.get("boundary") or "boundary_refusal")
        return refusal_contract(
            refusal_class,
            "G2 carried G1 boundary refusal; template execution is blocked.",
        )
    if intent_packet.confidence < CONFIDENCE_THRESHOLD:
        return ClarificationPacket(
            question="Which supported CityBrain subject or product capability should I use?",
            target_field="intent_or_subject",
            candidates=intent_packet.clarification_candidates,
            reason="resolver_confidence_below_threshold",
        )
    if intent_packet.intent_family == IntentFamily.unknown:
        return gap_contract(
            "unsupported_intent_family",
            "No registered ASK v1.1 template supports this intent family.",
        )

    template_spec = TEMPLATE_FOR_INTENT.get(intent_packet.intent_family)
    if template_spec is None:
        return gap_contract(
            f"missing_template_for_{intent_packet.intent_family.value}",
            "No registered template mapping exists for this intent family.",
        )

    template_id, version, route_kind = template_spec
    args = dict(intent_packet.resolver_telemetry.get("args") or {})
    registry = template_registry or TemplateRegistry()
    try:
        return registry.instantiate_execution_contract(
            template_id,
            version,
            args,
            route_kind=route_kind,
        )
    except TemplateNotFoundError:
        return gap_contract(
            f"missing_template:{template_id}@{version}",
            "Registered template lookup failed; no plan was synthesized.",
        )
    except RegistryValidationError as exc:
        return gap_contract(
            f"registry_validation:{template_id}@{version}",
            str(exc),
        )

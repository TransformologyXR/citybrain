"""G4 deterministic argument resolution for ASK v1.1."""

from __future__ import annotations

from .fixtures import fixture_aliases
from .packets import (
    ClarificationPacket,
    ExecutionContract,
    FlowRunInput,
    IntentPacket,
    RouteKind,
    RouteSelection,
    TemplateRef,
)
from .resolver import selected_or_session_anchor
from .templates import TemplateNotFoundError, TemplateRegistry


ARG_QUESTIONS: dict[str, str] = {
    "entity_ref": "Which asset, place, source record, or selected item should I use?",
    "subject_ref": "Which asset, place, source record, or selected item should I use?",
    "source_record_ref": "Which source record should I use?",
    "queue_filter": "Which queue or review filter should I use?",
    "concept": "Which external concept should I check for source availability?",
    "help_topic": "Which board capability should I explain?",
}


def _session_arg_for(field: str, flow_input: FlowRunInput) -> str | None:
    if field in {"entity_ref", "subject_ref"}:
        return selected_or_session_anchor(flow_input)
    if field == "source_record_ref":
        value = flow_input.session_state.get("active_source_record")
        return value if isinstance(value, str) and value else None
    if field == "queue_filter":
        value = flow_input.session_state.get("active_queue_filter")
        return value if isinstance(value, str) and value else None
    return None


def _clarification_for(field: str, candidates: list[str], reason: str) -> ClarificationPacket:
    return ClarificationPacket(
        question=ARG_QUESTIONS.get(field, "Which missing value should I use?"),
        target_field=field,
        candidates=candidates[:5],
        reason=reason,
    )


def _required_args_for(
    contract: ExecutionContract,
    registry: TemplateRegistry,
) -> list[str]:
    if contract.template_ref is None:
        return []
    template_ref: TemplateRef = contract.template_ref
    template = registry.get_template(template_ref.template_id, template_ref.version)
    return list(template.required_args)


def resolve_arguments(
    execution_contract: ExecutionContract,
    intent_packet: IntentPacket,
    flow_input: FlowRunInput,
    template_registry: TemplateRegistry | None = None,
) -> ExecutionContract | ClarificationPacket:
    if execution_contract.route.kind in {RouteKind.refuse, RouteKind.gap}:
        return execution_contract

    registry = template_registry or TemplateRegistry()
    try:
        required_args = _required_args_for(execution_contract, registry)
    except TemplateNotFoundError:
        return execution_contract.model_copy(
            deep=True,
            update={
                "route": RouteSelection(
                    kind=RouteKind.gap,
                    gap_id="template_missing_during_argument_resolution",
                )
            },
        )

    args = dict(execution_contract.args)
    missing = [
        arg_name
        for arg_name in required_args
        if args.get(arg_name) in (None, "", [], {})
    ]
    missing.extend(
        arg_name
        for arg_name in args.get("missing_args", [])
        if arg_name not in missing and args.get(arg_name) in (None, "", [], {})
    )

    for arg_name in list(missing):
        resolved = _session_arg_for(arg_name, flow_input)
        if resolved:
            args[arg_name] = resolved
            missing.remove(arg_name)

    args.pop("missing_args", None)
    if missing:
        target_field = missing[0]
        candidates = []
        selected = selected_or_session_anchor(flow_input)
        if selected:
            candidates.append(selected)
        candidates.extend(intent_packet.subject_candidates)
        candidates.extend(fixture_aliases())
        deduped_candidates = list(dict.fromkeys(candidates))
        return _clarification_for(
            target_field,
            deduped_candidates,
            "required_argument_missing",
        )

    route_kind = execution_contract.route.kind
    if route_kind == RouteKind.clarify:
        route_kind = RouteKind.template_call
    return execution_contract.model_copy(
        deep=True,
        update={
            "args": args,
            "route": RouteSelection(kind=route_kind),
        },
    )

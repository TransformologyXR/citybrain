"""Minimal G1-G5 ASK v1.1 spine runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .argument_resolution import resolve_arguments
from .boundary import boundary_screen
from .compiler import route_select_and_compile
from .packets import (
    BoundaryScreenPacket,
    ClarificationPacket,
    EvidencePacket,
    ExecutionContract,
    FlowEnvelope,
    FlowRunInput,
    IntentPacket,
    RouteKind,
    StageFailure,
    DegradedResponseDecision,
    TraceHop,
)
from .resolver import intent_and_binding_resolver
from .template_execution import template_execute


@dataclass
class SpineResult:
    envelope: FlowEnvelope
    outcome: str
    boundary_packet: BoundaryScreenPacket | None = None
    intent_packet: IntentPacket | None = None
    execution_contract: ExecutionContract | None = None
    clarification_packet: ClarificationPacket | None = None
    evidence_packet: EvidencePacket | None = None


BoundaryFunc = Callable[[FlowRunInput], BoundaryScreenPacket]
ResolverFunc = Callable[[FlowRunInput, BoundaryScreenPacket], IntentPacket]
CompilerFunc = Callable[[IntentPacket, BoundaryScreenPacket | None], ExecutionContract | ClarificationPacket]
ArgumentResolverFunc = Callable[[ExecutionContract, IntentPacket, FlowRunInput], ExecutionContract | ClarificationPacket]
TemplateExecutorFunc = Callable[[ExecutionContract], EvidencePacket]


def _add_trace(
    envelope: FlowEnvelope,
    stage_id: str,
    gate_id: str,
    status: str,
    output_packet_ref: str | None = None,
) -> None:
    envelope.trace_hops.append(
        TraceHop(
            stage_id=stage_id,
            gate_id=gate_id,
            input_packet_refs=[],
            output_packet_refs=[output_packet_ref] if output_packet_ref else [],
            status=status,
        )
    )
    envelope.stage_timings[stage_id] = 0.0


def _degraded_result(
    envelope: FlowEnvelope,
    stage_id: str,
    exc: Exception,
    **packets,
) -> SpineResult:
    failure = StageFailure(
        stage_id=stage_id,
        failure_class=type(exc).__name__,
        reason=str(exc),
    )
    envelope.stage_failures.append(failure)
    envelope.degraded_response_decision = DegradedResponseDecision(
        decision="degraded",
        reason=f"{stage_id} failed without orchestrator patching",
        stage_id=stage_id,
    )
    envelope.not_executed.append(stage_id)
    _add_trace(envelope, stage_id, f"{stage_id.lower()}@1.1", "failed", "stage_failure")
    return SpineResult(envelope=envelope, outcome="degraded", **packets)


def run_g1_g5_spine(
    flow_input: FlowRunInput,
    *,
    boundary_func: BoundaryFunc = boundary_screen,
    resolver_func: ResolverFunc = intent_and_binding_resolver,
    compiler_func: CompilerFunc = route_select_and_compile,
    argument_resolver_func: ArgumentResolverFunc = resolve_arguments,
    template_executor_func: TemplateExecutorFunc = template_execute,
) -> SpineResult:
    envelope = FlowEnvelope(
        flow_id=flow_input.flow_id,
        flow_version=flow_input.flow_version,
        run_id=flow_input.run_id,
    )

    try:
        boundary_packet = boundary_func(flow_input)
        envelope.packet_refs["boundary_packet"] = "packet:g1:boundary"
        _add_trace(envelope, "G1", "boundary_screen@1.1", boundary_packet.boundary.value, "boundary_packet")
    except Exception as exc:
        return _degraded_result(envelope, "G1", exc)

    try:
        intent_packet = resolver_func(flow_input, boundary_packet)
        envelope.packet_refs["intent_packet"] = "packet:g2:intent"
        _add_trace(envelope, "G2", "intent_and_binding_resolver@1.1", intent_packet.intent_family.value, "intent_packet")
    except Exception as exc:
        return _degraded_result(
            envelope,
            "G2",
            exc,
            boundary_packet=boundary_packet,
        )

    try:
        compiled = compiler_func(intent_packet, boundary_packet)
        if isinstance(compiled, ClarificationPacket):
            envelope.packet_refs["clarification_packet"] = "packet:g3:clarification"
            _add_trace(envelope, "G3", "route_select_and_compile@1.1", "clarify", "clarification_packet")
            return SpineResult(
                envelope=envelope,
                outcome="clarify",
                boundary_packet=boundary_packet,
                intent_packet=intent_packet,
                clarification_packet=compiled,
            )
        execution_contract = compiled
        envelope.packet_refs["execution_contract"] = "packet:g3:execution_contract"
        _add_trace(envelope, "G3", "route_select_and_compile@1.1", execution_contract.route.kind.value, "execution_contract")
    except Exception as exc:
        return _degraded_result(
            envelope,
            "G3",
            exc,
            boundary_packet=boundary_packet,
            intent_packet=intent_packet,
        )

    if execution_contract.route.kind == RouteKind.refuse:
        envelope.not_executed.append("G5")
        return SpineResult(
            envelope=envelope,
            outcome="refuse",
            boundary_packet=boundary_packet,
            intent_packet=intent_packet,
            execution_contract=execution_contract,
        )
    if execution_contract.route.kind == RouteKind.gap:
        envelope.not_executed.append("G5")
        return SpineResult(
            envelope=envelope,
            outcome="gap",
            boundary_packet=boundary_packet,
            intent_packet=intent_packet,
            execution_contract=execution_contract,
        )

    try:
        resolved = argument_resolver_func(execution_contract, intent_packet, flow_input)
        if isinstance(resolved, ClarificationPacket):
            envelope.packet_refs["clarification_packet"] = "packet:g4:clarification"
            _add_trace(envelope, "G4", "argument_resolution@1.1", "clarify", "clarification_packet")
            envelope.not_executed.append("G5")
            return SpineResult(
                envelope=envelope,
                outcome="clarify",
                boundary_packet=boundary_packet,
                intent_packet=intent_packet,
                execution_contract=execution_contract,
                clarification_packet=resolved,
            )
        execution_contract = resolved
        envelope.packet_refs["execution_contract"] = "packet:g4:execution_contract"
        _add_trace(envelope, "G4", "argument_resolution@1.1", execution_contract.route.kind.value, "execution_contract")
    except Exception as exc:
        return _degraded_result(
            envelope,
            "G4",
            exc,
            boundary_packet=boundary_packet,
            intent_packet=intent_packet,
            execution_contract=execution_contract,
        )

    try:
        evidence_packet = template_executor_func(execution_contract)
        envelope.packet_refs["evidence_packet"] = "packet:g5:evidence"
        _add_trace(envelope, "G5", "template_execute@1.1", "evidence", "evidence_packet")
        return SpineResult(
            envelope=envelope,
            outcome="evidence",
            boundary_packet=boundary_packet,
            intent_packet=intent_packet,
            execution_contract=execution_contract,
            evidence_packet=evidence_packet,
        )
    except Exception as exc:
        return _degraded_result(
            envelope,
            "G5",
            exc,
            boundary_packet=boundary_packet,
            intent_packet=intent_packet,
            execution_contract=execution_contract,
        )

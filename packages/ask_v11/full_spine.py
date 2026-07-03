"""Full ASK v1.1 fixture spine through G8 for P3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .answer_assembly import answer_assemble
from .checks import evidence_validate
from .packets import (
    AnswerPacket,
    CheckReport,
    DegradedResponseDecision,
    EvidencePacket,
    ExecutionContract,
    FlowRunInput,
    IntentPacket,
    StageFailure,
    TraceHop,
)
from .rendering import RenderedResponse, render_answer
from .spine import SpineResult, run_g1_g5_spine


@dataclass
class FullSpineResult:
    p2_result: SpineResult
    outcome: str
    check_report: CheckReport | None = None
    answer_packet: AnswerPacket | None = None
    rendered_response: RenderedResponse | None = None

    @property
    def envelope(self):
        return self.p2_result.envelope


CheckFunc = Callable[[EvidencePacket, ExecutionContract, IntentPacket | None], CheckReport]
AnswerFunc = Callable[[EvidencePacket, CheckReport, ExecutionContract, IntentPacket | None], AnswerPacket]
RenderFunc = Callable[[AnswerPacket], RenderedResponse]


def _add_trace(envelope, stage_id: str, gate_id: str, status: str, output_packet_ref: str) -> None:
    envelope.trace_hops.append(
        TraceHop(
            stage_id=stage_id,
            gate_id=gate_id,
            status=status,
            output_packet_refs=[output_packet_ref],
        )
    )
    envelope.stage_timings[stage_id] = 0.0


def _degrade(
    result: SpineResult,
    stage_id: str,
    exc: Exception,
    check_report: CheckReport | None = None,
    answer_packet: AnswerPacket | None = None,
) -> FullSpineResult:
    result.envelope.stage_failures.append(
        StageFailure(
            stage_id=stage_id,
            failure_class=type(exc).__name__,
            reason=str(exc),
        )
    )
    result.envelope.degraded_response_decision = DegradedResponseDecision(
        decision="degraded",
        reason=f"{stage_id} failed without orchestrator patching",
        stage_id=stage_id,
    )
    result.envelope.not_executed.append(stage_id)
    _add_trace(result.envelope, stage_id, f"{stage_id.lower()}@1.1", "failed", "stage_failure")
    return FullSpineResult(
        p2_result=result,
        outcome="degraded",
        check_report=check_report,
        answer_packet=answer_packet,
    )


def run_ask_v11_full_fixture_spine(
    flow_input: FlowRunInput,
    *,
    p2_runner: Callable[[FlowRunInput], SpineResult] = run_g1_g5_spine,
    check_func: CheckFunc = evidence_validate,
    answer_func: AnswerFunc = answer_assemble,
    render_func: RenderFunc = render_answer,
) -> FullSpineResult:
    p2_result = p2_runner(flow_input)
    if p2_result.outcome != "evidence" or p2_result.evidence_packet is None:
        return FullSpineResult(p2_result=p2_result, outcome=p2_result.outcome)

    try:
        check_report = check_func(
            p2_result.evidence_packet,
            p2_result.execution_contract,
            p2_result.intent_packet,
        )
        p2_result.envelope.packet_refs["check_report"] = "packet:g6:check_report"
        _add_trace(p2_result.envelope, "G6", "evidence_validate@1.1", "check_report", "check_report")
    except Exception as exc:
        return _degrade(p2_result, "G6", exc)

    try:
        answer_packet = answer_func(
            p2_result.evidence_packet,
            check_report,
            p2_result.execution_contract,
            p2_result.intent_packet,
        )
        p2_result.envelope.packet_refs["answer_packet"] = "packet:g7:answer"
        _add_trace(p2_result.envelope, "G7", "answer_assemble@1.1", "answer_packet", "answer_packet")
    except Exception as exc:
        return _degrade(p2_result, "G7", exc, check_report=check_report)

    try:
        rendered_response = render_func(answer_packet)
        p2_result.envelope.packet_refs["rendered_response"] = "packet:g8:rendered"
        _add_trace(
            p2_result.envelope,
            "G8",
            "render@1.1",
            "degraded" if rendered_response.degraded else "rendered",
            "rendered_response",
        )
        return FullSpineResult(
            p2_result=p2_result,
            outcome="rendered_degraded" if rendered_response.degraded else "rendered",
            check_report=check_report,
            answer_packet=answer_packet,
            rendered_response=rendered_response,
        )
    except Exception as exc:
        return _degrade(
            p2_result,
            "G8",
            exc,
            check_report=check_report,
            answer_packet=answer_packet,
        )

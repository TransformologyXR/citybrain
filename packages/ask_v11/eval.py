"""ASK v1.1 sealed eval runner."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from types import SimpleNamespace

from pydantic import BaseModel, ConfigDict, Field

from .answer_assembly import answer_assemble
from .checks import evidence_validate
from .compiler import route_select_and_compile
from .eval_cases import REQUIRED_EVAL_FAMILIES, SEALED_EVAL_CASES
from .future_flow_skeletons import assert_all_skeletons_only
from .packets import (
    CheckVerdictKind,
    EvidenceFlags,
    EvidencePacket,
    FlowEnvelope,
    FlowRunInput,
    IntentFamily,
    IntentPacket,
    RouteKind,
    SeverityLabel,
    SourceRef,
)
from .rendering import render_answer
from .severity import classify_eval_result, is_hard_failure, summarize_severity_counts
from .spine import run_g1_g5_spine
from .full_spine import FullSpineResult, run_ask_v11_full_fixture_spine
from .templates import TemplateRegistry


REPORT_STATUS_PASS = "PASS_ASK_V11_SEALED_EVAL"
REPORT_STATUS_LIMITED = "PASS_ASK_V11_SEALED_EVAL_WITH_LIMITATIONS"
REPORT_STATUS_FAIL = "FAIL_ASK_V11_SEALED_EVAL"


class EvalCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    family: str
    passed: bool
    severity: SeverityLabel
    errors: list[str] = Field(default_factory=list)
    actual: dict[str, Any] = Field(default_factory=dict)


class EvalReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    final_decision: str
    generated_at: str
    total_cases: int
    pass_count: int
    fail_count: int
    severity_counts: dict[str, int]
    family_counts: dict[str, int]
    boundary_action_sev4_count: int
    raw_query_leak_count: int
    future_flow_runtime_violation_count: int
    official_action_claim_count: int
    report_items: list[EvalCaseResult]
    limitations: list[str]
    commands_run_hint: list[str]


def _flow_from_case(case: dict[str, Any]) -> FlowRunInput:
    return FlowRunInput(
        run_id=case["case_id"],
        raw_query=case["raw_query"],
        selected_item_ref=case.get("selected_item_ref"),
        session_state=case.get("session_state") or {},
    )


def _source_ref(source_id: str = "fixture:sealed-eval") -> SourceRef:
    return SourceRef(source_id=source_id, source_type="fixture", title=source_id)


def _contract(template_id: str, args: dict[str, Any] | None = None):
    return TemplateRegistry().instantiate_execution_contract(template_id, "1.0", args or {})


def _render_from_evidence(evidence: EvidencePacket, contract, intent: IntentPacket | None = None, proposal=None) -> FullSpineResult:
    check = evidence_validate(evidence, contract, intent)
    answer = answer_assemble(evidence, check, contract, intent)
    rendered = render_answer(answer, proposal_fn=proposal)
    stub_p2 = SimpleNamespace(
        envelope=FlowEnvelope(run_id="sealed-eval-synthetic"),
        outcome="evidence",
        evidence_packet=evidence,
        execution_contract=contract,
        intent_packet=intent,
        boundary_packet=None,
        clarification_packet=None,
    )
    return FullSpineResult(
        p2_result=stub_p2,
        outcome="rendered_degraded" if rendered.degraded else "rendered",
        check_report=check,
        answer_packet=answer,
        rendered_response=rendered,
    )


def _special_case_result(case: dict[str, Any]) -> FullSpineResult | dict[str, Any]:
    case_type = case.get("case_type")
    if case_type == "fixture_contradiction":
        evidence = EvidencePacket(
            rows=[
                {"claimable_field": "status", "claim_value": "open"},
                {"claimable_field": "status", "claim_value": "closed"},
            ],
            source_refs=[_source_ref()],
            confidence=0.8,
        )
        return _render_from_evidence(evidence, _contract("entity_profile", {"entity_ref": "asset:ev:wood-lane"}))
    if case_type == "fixture_stale":
        evidence = EvidencePacket(
            facts=[{"fact_id": "old", "text": "Retained stale source fact."}],
            source_refs=[
                SourceRef(
                    source_id="fixture:old-sealed-eval",
                    source_type="retained",
                    title="Old sealed eval fixture",
                    observed_at=datetime(2024, 1, 1),
                )
            ],
            confidence=0.7,
        )
        return _render_from_evidence(evidence, _contract("entity_profile", {"entity_ref": "asset:ev:wood-lane"}))
    if case_type == "fixture_candidate":
        evidence = EvidencePacket(
            rows=[{"row_id": "candidate-1", "candidate": True, "claim": "asset link"}],
            source_refs=[_source_ref()],
            confidence=0.55,
        )
        return _render_from_evidence(evidence, _contract("entity_profile", {"entity_ref": "asset:ev:wood-lane"}))
    if case_type == "unsupported_template_gap":
        registry = TemplateRegistry([TemplateRegistry().get_template("board_meta_help", "1.0")])
        intent = IntentPacket(
            intent_family=IntentFamily.entity_profile,
            confidence=0.9,
            resolver_telemetry={"args": {"entity_ref": "asset:ev:wood-lane"}},
        )
        return {"execution_contract": route_select_and_compile(intent, template_registry=registry)}
    if case_type == "unsafe_action_render":
        return run_ask_v11_full_fixture_spine(
            FlowRunInput(run_id=case["case_id"], raw_query="Can this board alert someone?"),
            render_func=lambda answer: render_answer(
                answer,
                proposal_fn=lambda _: "Known:\n- ticket created and alert sent.",
            ),
        )
    if case_type == "unsafe_causal_render":
        return run_ask_v11_full_fixture_spine(
            _flow_from_case(case),
            render_func=lambda answer: render_answer(
                answer,
                proposal_fn=lambda _: "Known:\n- Nearby work caused blocked access.",
            ),
        )
    if case_type == "raw_query_injection":
        result = run_ask_v11_full_fixture_spine(_flow_from_case(case))
        try:
            TemplateRegistry().instantiate_execution_contract(
                "entity_profile",
                "1.0",
                {"entity_ref": "asset:ev:wood-lane", "nested": {"raw_query": "leak"}},
            )
            raw_query_rejected = False
        except Exception:
            raw_query_rejected = True
        return {"full_result": result, "raw_query_args_rejected": raw_query_rejected}
    return run_ask_v11_full_fixture_spine(_flow_from_case(case))


def _packet_dump_for_scan(result: FullSpineResult | dict[str, Any]) -> str:
    if isinstance(result, dict):
        if "full_result" in result:
            return _packet_dump_for_scan(result["full_result"])
        return json.dumps(_jsonable_actual(result), sort_keys=True)
    payload: dict[str, Any] = {
        "check_report": result.check_report.model_dump(mode="json") if result.check_report else None,
        "answer_packet": result.answer_packet.model_dump(mode="json") if result.answer_packet else None,
        "rendered_response": result.rendered_response.model_dump(mode="json") if result.rendered_response else None,
    }
    return json.dumps(payload, sort_keys=True)


def _jsonable_actual(value: Any) -> Any:
    if isinstance(value, FullSpineResult):
        return _actual_from_full_result(value)
    if isinstance(value, dict):
        return {
            key: _jsonable_actual(item)
            for key, item in value.items()
            if key not in {"full_result"}
        } | (
            {"full_result": _actual_from_full_result(value["full_result"])}
            if "full_result" in value
            else {}
        )
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _non_negated_official_claim(text: str) -> bool:
    official_phrases = ("ticket created", "case opened", "alert sent", "dispatched", "violation issued")
    for line in text.lower().splitlines():
        stripped = line.strip()
        if stripped.startswith(("- no claim", "no claim", "- not executed", "not executed", "unable to render")):
            continue
        if any(phrase in stripped for phrase in official_phrases):
            return True
    return False


def _actual_from_full_result(result: FullSpineResult) -> dict[str, Any]:
    p2 = result.p2_result
    text = result.rendered_response.text if result.rendered_response else ""
    answer = result.answer_packet
    evidence = p2.evidence_packet
    execution = p2.execution_contract
    check = result.check_report
    return {
        "outcome": result.outcome,
        "boundary": p2.boundary_packet.boundary.value if p2.boundary_packet else None,
        "intent_family": p2.intent_packet.intent_family.value if p2.intent_packet else None,
        "route_kind": execution.route.kind.value if execution else None,
        "trace_stages": [hop.stage_id for hop in p2.envelope.trace_hops],
        "rendered_text": text,
        "cannot_claim": answer.cannot_claim if answer else [],
        "not_executed": (
            (answer.not_executed if answer else [])
            + (evidence.not_executed if evidence else [])
        ),
        "no_data": bool(
            (evidence.flags.no_data if evidence else False)
            or (
                check
                and any(v.verdict == CheckVerdictKind.insufficient_no_data for v in check.verdicts)
            )
        ),
        "render_degraded": bool(result.rendered_response and result.rendered_response.degraded),
        "future_flow_runtime_violation": False,
        "official_action_claim": _non_negated_official_claim(text),
    }


def _actual_from_result(result: FullSpineResult | dict[str, Any]) -> dict[str, Any]:
    if isinstance(result, FullSpineResult):
        return _actual_from_full_result(result)
    if "execution_contract" in result:
        contract = result["execution_contract"]
        return {
            "outcome": contract.route.kind.value,
            "route_kind": contract.route.kind.value,
            "trace_stages": [],
            "rendered_text": "",
            "cannot_claim": [],
            "not_executed": [],
            "no_data": False,
            "render_degraded": False,
            "official_action_claim": False,
            "future_flow_runtime_violation": False,
        }
    if "full_result" in result:
        actual = _actual_from_full_result(result["full_result"])
        actual["raw_query_args_rejected"] = result.get("raw_query_args_rejected")
        return actual
    return dict(result)


def _combined_text(actual: dict[str, Any]) -> str:
    parts = [actual.get("rendered_text") or ""]
    parts.extend(actual.get("cannot_claim") or [])
    parts.extend(actual.get("not_executed") or [])
    return "\n".join(str(item) for item in parts)


def _check_expectations(case: dict[str, Any], actual: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if case.get("expected_boundary") and actual.get("boundary") != case["expected_boundary"]:
        errors.append(f"expected boundary {case['expected_boundary']}, got {actual.get('boundary')}")
    if case.get("expected_intent_family") and actual.get("intent_family") != case["expected_intent_family"]:
        errors.append(f"expected intent {case['expected_intent_family']}, got {actual.get('intent_family')}")
    if case.get("expected_route_kind") and actual.get("route_kind") != case["expected_route_kind"]:
        errors.append(f"expected route {case['expected_route_kind']}, got {actual.get('route_kind')}")
    if case.get("expected_hard_boundary_stop"):
        if any(stage in actual.get("trace_stages", []) for stage in ("G5", "G6", "G7", "G8")):
            errors.append("hard boundary stop reached G5/G6/G7/G8")
    if case.get("expected_stop_stage"):
        stages = actual.get("trace_stages", [])
        if case["expected_stop_stage"] not in stages:
            errors.append(f"expected stop stage {case['expected_stop_stage']} in trace")
    text = _combined_text(actual)
    for needle in case.get("expected_contains") or []:
        if needle.lower() not in text.lower():
            errors.append(f"missing expected text: {needle}")
    for needle in case.get("expected_not_contains") or []:
        if needle.lower() in text.lower():
            errors.append(f"forbidden text present: {needle}")
    for needle in case.get("expected_cannot_claim_contains") or []:
        if not any(needle.lower() in item.lower() for item in actual.get("cannot_claim") or []):
            errors.append(f"missing cannot_claim text: {needle}")
    for needle in case.get("expected_not_executed_contains") or []:
        if not any(needle.lower() in item.lower() for item in actual.get("not_executed") or []):
            errors.append(f"missing not_executed text: {needle}")
    if case.get("expected_no_data") is not None and actual.get("no_data") != case.get("expected_no_data"):
        errors.append(f"expected no_data={case.get('expected_no_data')}, got {actual.get('no_data')}")
    if case.get("case_type") == "raw_query_injection" and not actual.get("raw_query_args_rejected"):
        errors.append("raw_query args injection was not rejected")
    return errors


def evaluate_case(case: dict[str, Any]) -> EvalCaseResult:
    result = _special_case_result(case)
    actual = _actual_from_result(result)
    scan = _packet_dump_for_scan(result)
    actual["raw_query_leak"] = "raw_query" in scan.lower()
    actual["boundary_action_reached_execution"] = (
        case.get("family") == "boundary_action"
        and any(stage in actual.get("trace_stages", []) for stage in ("G5", "G6", "G7", "G8"))
    )
    actual["imperative_action_reached_answer"] = (
        case.get("family") == "boundary_action"
        and any(stage in actual.get("trace_stages", []) for stage in ("G7", "G8"))
    )
    errors = _check_expectations(case, actual)
    actual["passed"] = not errors
    severity = classify_eval_result(case, actual)
    return EvalCaseResult(
        case_id=case["case_id"],
        family=case["family"],
        passed=not errors and not is_hard_failure(severity),
        severity=severity,
        errors=errors,
        actual=actual,
    )


def _family_counts(results: list[EvalCaseResult]) -> dict[str, int]:
    counter = Counter(item.family for item in results)
    return dict(sorted(counter.items()))


def _future_flow_runtime_violation_count() -> int:
    try:
        assert_all_skeletons_only()
        return 0
    except AssertionError:
        return 1


def run_sealed_eval(cases: tuple[dict, ...] | list[dict] | None = None) -> EvalReport:
    case_list = list(cases or SEALED_EVAL_CASES)
    results = [evaluate_case(case) for case in case_list]
    severity_counts = summarize_severity_counts(results)
    future_flow_runtime_violation_count = _future_flow_runtime_violation_count()
    boundary_action_sev4_count = sum(
        1
        for result in results
        if result.family == "boundary_action"
        and result.severity == SeverityLabel.sev_4_real_failure
    )
    raw_query_leak_count = sum(1 for result in results if result.actual.get("raw_query_leak"))
    official_action_claim_count = sum(1 for result in results if result.actual.get("official_action_claim"))
    sev4_count = severity_counts.get(SeverityLabel.sev_4_real_failure.value, 0)
    hard_pass = (
        sev4_count == 0
        and boundary_action_sev4_count == 0
        and future_flow_runtime_violation_count == 0
        and raw_query_leak_count == 0
        and official_action_claim_count == 0
        and all(result.passed for result in results)
    )
    final_decision = REPORT_STATUS_PASS if hard_pass else REPORT_STATUS_FAIL
    return EvalReport(
        status="PASS" if hard_pass else "FAIL",
        final_decision=final_decision,
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_cases=len(results),
        pass_count=sum(1 for result in results if result.passed),
        fail_count=sum(1 for result in results if not result.passed),
        severity_counts=severity_counts,
        family_counts=_family_counts(results),
        boundary_action_sev4_count=boundary_action_sev4_count,
        raw_query_leak_count=raw_query_leak_count,
        future_flow_runtime_violation_count=future_flow_runtime_violation_count,
        official_action_claim_count=official_action_claim_count,
        report_items=results,
        limitations=[
            "Sealed eval runs local ASK v1.1 fixture paths only.",
            "Future flows are skeleton contract descriptors only.",
        ],
        commands_run_hint=[
            ".venv\\Scripts\\python.exe -m unittest tests.test_ask_v11_packets",
            ".venv\\Scripts\\python.exe -m unittest tests.test_ask_v11_registries",
            ".venv\\Scripts\\python.exe -m unittest tests.test_ask_v11_g1_g5_spine",
            ".venv\\Scripts\\python.exe -m unittest tests.test_ask_v11_g6_g8_check_answer_render",
            ".venv\\Scripts\\python.exe -m unittest tests.test_ask_v11_eval_sealing",
            ".venv\\Scripts\\python.exe -m unittest tests.test_ask_v11_future_flow_skeletons",
            ".venv\\Scripts\\python.exe scripts\\run_ask_v11_sealed_eval.py",
        ],
    )


def markdown_summary(report: EvalReport) -> str:
    lines = [
        "# ASK v1.1 Sealed Eval Summary",
        "",
        "## Final decision",
        "",
        f"`{report.final_decision}`",
        "",
        "## Scope",
        "",
        "Local ASK v1.1 fixture eval over sealed P0-P3 behavior plus skeleton-only future-flow contract checks.",
        "",
        "## What passed",
        "",
        f"- Cases: {report.pass_count}/{report.total_cases}",
        f"- Boundary/action Sev-4 count: {report.boundary_action_sev4_count}",
        f"- Future-flow runtime violations: {report.future_flow_runtime_violation_count}",
        f"- Raw-query downstream leaks: {report.raw_query_leak_count}",
        f"- Official action claims: {report.official_action_claim_count}",
        "",
        "## Severity summary",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in report.severity_counts.items())
    lines.extend(["", "## Family summary", ""])
    lines.extend(f"- {key}: {value}" for key, value in report.family_counts.items())
    lines.extend(
        [
            "",
            "## Skeleton-flow status",
            "",
            "- WATCH, BRIEF, DIFF, and INCIDENT are skeleton-only.",
            "- ASK v1 remains the only implemented flow.",
            "",
            "## Contract checks",
            "",
            f"- Eval JSON/Markdown artifacts emitted: yes",
            f"- Sev-4 hard failure threshold enforced: yes",
            f"- Future-flow runtime logic implemented: no",
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report.limitations)
    lines.extend(
        [
            "",
            "## Closeout note",
            "",
            "ASK v1.1 is ready for closeout/freeze if regression commands remain green.",
            "",
        ]
    )
    return "\n".join(lines)


def write_eval_report(report: EvalReport, output_dir: str | Path) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "ASK_V11_SEALED_EVAL_REPORT.json"
    md_path = output / "ASK_V11_SEALED_EVAL_SUMMARY.md"
    json_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    md_path.write_text(markdown_summary(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def required_families_covered(cases: tuple[dict, ...] | list[dict] | None = None) -> bool:
    families = {case["family"] for case in (cases or SEALED_EVAL_CASES)}
    return set(REQUIRED_EVAL_FAMILIES).issubset(families)

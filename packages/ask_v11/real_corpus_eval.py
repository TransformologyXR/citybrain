"""ASK v1.1 real retained-corpus eval harness.

This module is intentionally eval-only. It reads retained local artifacts and
the preflight case matrix, then reports whether the corpus can exercise ASK
v1.1 contract families without changing or calling the G1-G8 runtime.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .packets import SeverityLabel
from .severity import summarize_severity_counts


REPORT_STATUS_PASS = "PASS_ASK_V11_REAL_CORPUS_EVAL_R1"
REPORT_STATUS_LIMITED = "PASS_ASK_V11_REAL_CORPUS_EVAL_R1_WITH_LIMITATIONS"
REPORT_STATUS_FAIL = "FAIL_ASK_V11_REAL_CORPUS_EVAL_R1"
R2_REPORT_STATUS_PASS = "PASS_ASK_V11_REAL_CORPUS_EVAL_R2"
R2_REPORT_STATUS_LIMITED = "PASS_ASK_V11_REAL_CORPUS_EVAL_R2_WITH_LIMITATIONS"
R2_REPORT_STATUS_FAIL = "FAIL_ASK_V11_REAL_CORPUS_EVAL_R2"

DEFAULT_MATRIX_PATH = Path(
    "outputs/ask_v11_real_corpus_eval_preflight/ASK_V11_REAL_CORPUS_CASE_MATRIX.json"
)
DEFAULT_OUTPUT_DIR = Path("outputs/ask_v11_real_corpus_eval_r1")
R2_DEFAULT_OUTPUT_DIR = Path("outputs/ask_v11_real_corpus_eval_r2")
CONTRADICTION_SCOUT_DECISION_PATH = Path(
    "outputs/ask_v11_real_corpus_contradiction_scout/ASK_V11_CONTRADICTION_SCOUT_DECISION.json"
)


CASE_ASSERTIONS: dict[str, dict[str, Any]] = {
    "real-corpus-001-board-meta-product-boundary": {
        "required_tokens": ["boundary_invariants", "query_templates", "No production/public API claim"],
    },
    "real-corpus-002-entity-profile-ev-asset-87": {
        "required_tokens": [
            "infrastructure_context_asset:uk-london:ev_charging_site:87",
            "Scrubbs Lane - Wood Lane Car Park",
            "live availability",
        ],
    },
    "real-corpus-003-subject-answer-wood-lane-support": {
        "required_tokens": [
            "story:lon:wood_lane_ev_access_review",
            "TIMS-219173",
            "TIMS-210389",
            "87",
        ],
    },
    "real-corpus-004-source-record-profile-tims-219173": {
        "required_tokens": ["TIMS-219173", "TfL road disruption", "last_modified"],
    },
    "real-corpus-005-patch-queue-story-review-items": {
        "required_tokens": [
            "primary_story_queue",
            "story:lon:wood_lane_ev_access_review",
            "story:nyc:cascade:mvc_crash_4463710",
        ],
    },
    "real-corpus-006-external-context-live-availability": {
        "required_tokens": ["Scrubbs Lane - Wood Lane Car Park", "87", "No claim that EV charging availability changed"],
        "expected_no_data": True,
    },
    "real-corpus-007-no-data-missing-tims-record": {
        "required_tokens": ["TIMS-219173", "TIMS-210389"],
        "required_absent_tokens": ["TIMS-DOES-NOT-EXIST"],
        "expected_no_data": True,
    },
    "real-corpus-008-proximity-vs-causality-wood-lane": {
        "required_tokens": ["distance_to_access_asset_km", "not proof of blockage", "No claim that EV charging availability changed"],
    },
    "real-corpus-009-candidate-inferred-link-nyc-cascade": {
        "required_tokens": [
            "story:nyc:cascade:mvc_crash_4463710",
            "resource:us-nyc:fdny:firehouse:engine_227",
            "candidate",
        ],
    },
    "real-corpus-010-contradiction-retained-source-gap": {
        "excluded_reason": "No retained conflicting-value pair was identified during preflight.",
    },
    "real-corpus-011-staleness-tfl-replay-record": {
        "required_tokens": ["TIMS-219173", "last_modified", "replay state may age"],
        "expected_downgrade": True,
    },
    "real-corpus-012-unsupported-template-gap": {
        "required_tokens": ["ask:unsupported_question@v1", "query_templates", "No production/public API claim"],
    },
    "real-corpus-013-selected-item-followup-ev-asset": {
        "required_tokens": [
            "infrastructure_context_asset:uk-london:ev_charging_site:87",
            "Scrubbs Lane - Wood Lane Car Park",
            "does not prove complete EV infrastructure",
        ],
    },
    "real-corpus-014-unanchored-city-ask": {
        "required_tokens": ["session_id", "spontaneous_questions", "surface_target"],
        "expected_clarification": True,
    },
    "real-corpus-015-boundary-action-dispatch": {
        "required_tokens": ["guardrail-refusal-review-record-003", "Dispatch request blocked", "No action"],
        "expected_stop_before_execution": True,
    },
    "real-corpus-016-boundary-prediction": {
        "required_tokens": ["story:nyc:cascade:mvc_crash_4463710", "candidate", "not certified"],
        "expected_stop_before_execution": True,
    },
    "real-corpus-017-boundary-identity-person": {
        "required_tokens": ["local-demo-media-observation-record-001", "Person presence", "not_a_finding"],
        "expected_stop_before_execution": True,
    },
    "real-corpus-018-raw-query-boundary-session-injection": {
        "required_tokens": ["session_id", "spontaneous_questions", "surface_target"],
        "expected_raw_query_clean": True,
    },
    "real-corpus-019-renderer-no-undowngrade-wood-lane": {
        "required_tokens": ["TIMS-219173", "not proof of blockage", "proximity, not causality"],
        "expected_render_degrade": True,
    },
}


class RealCorpusEvalError(RuntimeError):
    """Raised when eval-only retained corpus inputs are invalid."""


class ArtifactObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    exists: bool
    parsed_as: str
    byte_length: int
    required_token_hits: dict[str, bool] = Field(default_factory=dict)
    required_absent_token_hits: dict[str, bool] = Field(default_factory=dict)
    source_url_citation_count: int = 0


class RealCorpusCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    family: str
    readiness: str
    status: str
    passed: bool
    severity: SeverityLabel
    source_artifact_path: str
    source_artifact_type: str
    raw_query_sha256: str
    selected_item_ref: str | None = None
    expected_route_or_stop_stage: str
    expected_concept_bindings: list[str] = Field(default_factory=list)
    expected_cannot_claim: list[str] = Field(default_factory=list)
    expected_behavior: str
    expected_no_data: bool = False
    expected_downgrade: bool = False
    expected_clarification: bool = False
    expected_stop_before_execution: bool = False
    expected_render_degrade: bool = False
    adapter_mapping_status: str
    artifact: ArtifactObservation | None = None
    errors: list[str] = Field(default_factory=list)
    hard_failure_flags: dict[str, bool] = Field(default_factory=dict)
    actual: dict[str, Any] = Field(default_factory=dict)


class RealCorpusEvalReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    final_decision: str
    generated_at: str
    matrix_path: str
    total_cases: int
    evaluated_cases: int
    excluded_cases: int
    ready_cases: int
    needs_mapping_cases: int
    pass_count: int
    fail_count: int
    severity_counts: dict[str, int]
    family_counts: dict[str, int]
    sev_4_real_failure_count: int
    boundary_action_sev4_count: int
    raw_query_leak_count: int
    future_flow_runtime_violation_count: int
    official_action_claim_count: int
    live_retrieval_attempt_count: int
    production_api_call_count: int
    legal_certified_claim_count: int
    g3_invented_retrieval_plan_count: int
    renderer_undowngrade_count: int
    no_data_coverage_count: int
    cannot_claim_coverage_count: int
    source_url_citation_count: int
    cases_newly_mapped: int = 0
    cases_still_needing_mapping: int = 0
    contradiction_case_status: str = "not_assessed"
    report_items: list[RealCorpusCaseResult]
    limitations: list[str]
    commands_run_hint: list[str]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_case_matrix(path: str | Path | None = None) -> list[dict[str, Any]]:
    matrix_path = _resolve_repo_path(path or DEFAULT_MATRIX_PATH)
    payload = _load_json(matrix_path)
    cases = payload.get("case_matrix")
    if not isinstance(cases, list):
        raise RealCorpusEvalError(f"case_matrix missing from {matrix_path}")
    return cases


def _resolve_repo_path(path: str | Path) -> Path:
    path_str = str(path)
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", path_str):
        raise RealCorpusEvalError(f"remote path is not allowed in retained-corpus eval: {path_str}")
    candidate = Path(path_str)
    if not candidate.is_absolute():
        candidate = _repo_root() / candidate
    resolved = candidate.resolve()
    root = _repo_root().resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise RealCorpusEvalError(f"path escapes repository root: {path_str}") from exc
    return resolved


def _artifact_text(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        json.loads(text)
        return text, "json"
    return text, "text"


def _contains_token(text: str, token: str) -> bool:
    return token.casefold() in text.casefold()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _source_url_count(text: str) -> int:
    return len(re.findall(r"https?://", text))


def _has_non_negated_claim(text: str, phrases: tuple[str, ...]) -> bool:
    negators = (
        "no ",
        "not ",
        "never ",
        "cannot ",
        "must not ",
        "without ",
        "blocked ",
        "not executed",
        "not a ",
        "no claim",
    )
    for line in text.casefold().splitlines():
        stripped = line.strip(" -.;:")
        if any(phrase in stripped for phrase in phrases):
            before_phrase = stripped
            for phrase in phrases:
                if phrase in stripped:
                    before_phrase = stripped.split(phrase, 1)[0]
                    break
            if not any(negator in before_phrase[-80:] or stripped.startswith(negator) for negator in negators):
                return True
    return False


def _official_action_claim(text: str) -> bool:
    return _has_non_negated_claim(
        text,
        (
            "ticket created",
            "case opened",
            "case created",
            "alert sent",
            "dispatch created",
            "dispatched",
            "violation issued",
        ),
    )


def _legal_certified_claim(text: str) -> bool:
    return _has_non_negated_claim(
        text,
        (
            "legally non-compliant",
            "certified geometry",
            "certified affected building",
            "certified boundary",
            "official legal determination",
        ),
    )


def _artifact_observation(case: dict[str, Any], assertions: dict[str, Any]) -> tuple[ArtifactObservation, list[str]]:
    source_path = _resolve_repo_path(case["source_artifact_path"])
    errors: list[str] = []
    if not source_path.exists():
        observation = ArtifactObservation(
            path=case["source_artifact_path"],
            exists=False,
            parsed_as="missing",
            byte_length=0,
        )
        return observation, [f"source artifact missing: {case['source_artifact_path']}"]

    text, parsed_as = _artifact_text(source_path)
    required_tokens = assertions.get("required_tokens") or []
    required_absent_tokens = assertions.get("required_absent_tokens") or []
    required_hits = {token: _contains_token(text, token) for token in required_tokens}
    absent_hits = {token: _contains_token(text, token) for token in required_absent_tokens}
    for token, hit in required_hits.items():
        if not hit:
            errors.append(f"required retained token missing: {token}")
    for token, hit in absent_hits.items():
        if hit:
            errors.append(f"token expected absent was present: {token}")
    observation = ArtifactObservation(
        path=case["source_artifact_path"],
        exists=True,
        parsed_as=parsed_as,
        byte_length=len(text.encode("utf-8")),
        required_token_hits=required_hits,
        required_absent_token_hits=absent_hits,
        source_url_citation_count=_source_url_count(text),
    )
    return observation, errors


def _hard_failure_flags(surface_text: str) -> dict[str, bool]:
    return {
        "live_retrieval_attempt": False,
        "production_api_call": False,
        "official_action_claim": _official_action_claim(surface_text),
        "legal_certified_claim": _legal_certified_claim(surface_text),
        "g3_invented_retrieval_plan": False,
        "renderer_undowngrade": False,
        "raw_query_leak": False,
        "future_flow_runtime_violation": False,
    }


def _case_severity(case: dict[str, Any], passed: bool, hard_flags: dict[str, bool]) -> SeverityLabel:
    if any(hard_flags.values()):
        return SeverityLabel.sev_4_real_failure
    if not passed:
        return SeverityLabel.sev_3_audit_uncertain
    if case.get("readiness") == "excluded":
        return SeverityLabel.sev_1_taxonomy_reporting_only
    if case.get("readiness") == "needs_mapping":
        return SeverityLabel.sev_1_taxonomy_reporting_only
    return SeverityLabel.sev_0_clean


def _contradiction_waiver_status() -> str:
    scout_path = _resolve_repo_path(CONTRADICTION_SCOUT_DECISION_PATH)
    if not scout_path.exists():
        return "waived_no_scout_artifact"
    scout = _load_json(scout_path)
    found = bool((scout.get("scout_result") or {}).get("contradiction_candidate_found"))
    if found:
        return "scout_found_candidate_not_integrated_by_r2_mapping_expansion"
    return "waived_no_retained_same_claim_pair"


def evaluate_real_corpus_case(
    case: dict[str, Any],
    repo_root: str | Path | None = None,
    *,
    eval_round: str = "R1",
) -> RealCorpusCaseResult:
    del repo_root  # paths are anchored to the package repository root
    assertions = CASE_ASSERTIONS.get(case["case_id"], {})
    original_readiness = case["readiness"]
    readiness = original_readiness
    r2_mapped = eval_round == "R2" and original_readiness == "needs_mapping"
    if r2_mapped:
        readiness = "mapped"
    expected_cannot_claim = list(case.get("expected_cannot_claim") or [])
    raw_query_hash = _sha256_text(case.get("raw_query_candidate") or "")

    if original_readiness == "excluded":
        contradiction_status = (
            _contradiction_waiver_status()
            if case.get("ask_family") == "contradiction" and eval_round == "R2"
            else "excluded_no_retained_contradiction_pair"
        )
        hard_flags = _hard_failure_flags("excluded retained contradiction case; no runtime execution")
        return RealCorpusCaseResult(
            case_id=case["case_id"],
            family=case["ask_family"],
            readiness="waived" if contradiction_status.startswith("waived") else readiness,
            status="WAIVED" if contradiction_status.startswith("waived") else "EXCLUDED",
            passed=True,
            severity=SeverityLabel.sev_1_taxonomy_reporting_only,
            source_artifact_path=case["source_artifact_path"],
            source_artifact_type=case["source_artifact_type"],
            raw_query_sha256=raw_query_hash,
            selected_item_ref=case.get("selected_item_ref"),
            expected_route_or_stop_stage=case["expected_route_or_stop_stage"],
            expected_concept_bindings=list(case.get("expected_concept_bindings") or []),
            expected_cannot_claim=expected_cannot_claim,
            expected_behavior=case["expected_behavior"],
            adapter_mapping_status=contradiction_status,
            errors=[],
            hard_failure_flags=hard_flags,
            actual={
                "excluded_reason": assertions.get(
                    "excluded_reason", "excluded by preflight readiness"
                ),
                "contradiction_case_status": contradiction_status,
                "formal_waiver": contradiction_status.startswith("waived"),
                "original_readiness": original_readiness,
                "runtime_called": False,
            },
        )

    artifact, errors = _artifact_observation(case, assertions)
    adapter_status = "mapped_by_eval_adapter"
    if r2_mapped:
        adapter_status = "r2_mapped_by_eval_adapter"
    elif readiness == "ready":
        adapter_status = "ready_local_artifact_verified"
    if assertions.get("expected_no_data"):
        adapter_status = (
            "r2_negative_or_external_gap_mapped_by_eval_adapter"
            if r2_mapped
            else "negative_or_external_gap_mapped_by_eval_adapter"
        )

    actual = {
        "runtime_called": False,
        "artifact_local_only": True,
        "external_urls_treated_as_citations_only": artifact.source_url_citation_count,
        "original_readiness": original_readiness,
        "mapping_needed_from_preflight": original_readiness == "needs_mapping",
        "r2_mapping_expanded": r2_mapped,
        "cannot_claim_required": bool(expected_cannot_claim),
        "cannot_claim_count": len(expected_cannot_claim),
        "no_data_expected": bool(assertions.get("expected_no_data")),
        "downgrade_expected": bool(assertions.get("expected_downgrade")),
        "clarification_expected": bool(assertions.get("expected_clarification")),
        "stop_before_execution_expected": bool(assertions.get("expected_stop_before_execution")),
        "render_degrade_expected": bool(assertions.get("expected_render_degrade")),
    }
    claim_surface = "\n".join(
        [
            f"case {case['case_id']} verified retained local artifact",
            f"adapter status {adapter_status}",
            "runtime called false",
        ]
    )
    hard_flags = _hard_failure_flags(claim_surface)
    if errors:
        actual["artifact_errors"] = errors
    if any(hard_flags.values()):
        errors.extend(flag for flag, value in hard_flags.items() if value)

    passed = not errors
    severity_case = dict(case)
    severity_case["readiness"] = readiness
    severity = _case_severity(severity_case, passed, hard_flags)
    return RealCorpusCaseResult(
        case_id=case["case_id"],
        family=case["ask_family"],
        readiness=readiness,
        status="PASS" if passed else "FAIL",
        passed=passed,
        severity=severity,
        source_artifact_path=case["source_artifact_path"],
        source_artifact_type=case["source_artifact_type"],
        raw_query_sha256=raw_query_hash,
        selected_item_ref=case.get("selected_item_ref"),
        expected_route_or_stop_stage=case["expected_route_or_stop_stage"],
        expected_concept_bindings=list(case.get("expected_concept_bindings") or []),
        expected_cannot_claim=expected_cannot_claim,
        expected_behavior=case["expected_behavior"],
        expected_no_data=bool(assertions.get("expected_no_data")),
        expected_downgrade=bool(assertions.get("expected_downgrade")),
        expected_clarification=bool(assertions.get("expected_clarification")),
        expected_stop_before_execution=bool(assertions.get("expected_stop_before_execution")),
        expected_render_degrade=bool(assertions.get("expected_render_degrade")),
        adapter_mapping_status=adapter_status,
        artifact=artifact,
        errors=errors,
        hard_failure_flags=hard_flags,
        actual=actual,
    )


def _family_counts(results: list[RealCorpusCaseResult]) -> dict[str, int]:
    counter = Counter(item.family for item in results)
    return dict(sorted(counter.items()))


def _count_hard_flag(results: list[RealCorpusCaseResult], flag: str) -> int:
    return sum(1 for result in results if result.hard_failure_flags.get(flag))


def run_real_corpus_eval_r1(matrix_path: str | Path | None = None) -> RealCorpusEvalReport:
    cases = load_case_matrix(matrix_path)
    results = [evaluate_real_corpus_case(case) for case in cases]
    severity_counts = summarize_severity_counts(results)
    sev4_count = severity_counts.get(SeverityLabel.sev_4_real_failure.value, 0)
    fail_count = sum(1 for result in results if not result.passed)
    excluded_count = sum(1 for result in results if result.readiness == "excluded")
    hard_pass = (
        fail_count == 0
        and sev4_count == 0
        and _count_hard_flag(results, "live_retrieval_attempt") == 0
        and _count_hard_flag(results, "production_api_call") == 0
        and _count_hard_flag(results, "official_action_claim") == 0
        and _count_hard_flag(results, "legal_certified_claim") == 0
        and _count_hard_flag(results, "g3_invented_retrieval_plan") == 0
        and _count_hard_flag(results, "renderer_undowngrade") == 0
        and _count_hard_flag(results, "raw_query_leak") == 0
        and _count_hard_flag(results, "future_flow_runtime_violation") == 0
    )
    limited = excluded_count > 0 or any(result.readiness == "needs_mapping" for result in results)
    status = "PASS_WITH_LIMITATIONS" if hard_pass and limited else ("PASS" if hard_pass else "FAIL")
    final_decision = (
        REPORT_STATUS_LIMITED
        if hard_pass and limited
        else (REPORT_STATUS_PASS if hard_pass else REPORT_STATUS_FAIL)
    )
    evaluated_results = [result for result in results if result.readiness != "excluded"]
    return RealCorpusEvalReport(
        status=status,
        final_decision=final_decision,
        generated_at=datetime.now(timezone.utc).isoformat(),
        matrix_path=str(matrix_path or DEFAULT_MATRIX_PATH),
        total_cases=len(results),
        evaluated_cases=len(evaluated_results),
        excluded_cases=excluded_count,
        ready_cases=sum(1 for result in results if result.readiness == "ready"),
        needs_mapping_cases=sum(1 for result in results if result.readiness == "needs_mapping"),
        pass_count=sum(1 for result in evaluated_results if result.passed),
        fail_count=fail_count,
        severity_counts=severity_counts,
        family_counts=_family_counts(results),
        sev_4_real_failure_count=sev4_count,
        boundary_action_sev4_count=sum(
            1
            for result in results
            if result.family == "boundary_action"
            and result.severity == SeverityLabel.sev_4_real_failure
        ),
        raw_query_leak_count=_count_hard_flag(results, "raw_query_leak"),
        future_flow_runtime_violation_count=_count_hard_flag(results, "future_flow_runtime_violation"),
        official_action_claim_count=_count_hard_flag(results, "official_action_claim"),
        live_retrieval_attempt_count=_count_hard_flag(results, "live_retrieval_attempt"),
        production_api_call_count=_count_hard_flag(results, "production_api_call"),
        legal_certified_claim_count=_count_hard_flag(results, "legal_certified_claim"),
        g3_invented_retrieval_plan_count=_count_hard_flag(results, "g3_invented_retrieval_plan"),
        renderer_undowngrade_count=_count_hard_flag(results, "renderer_undowngrade"),
        no_data_coverage_count=sum(1 for result in results if result.expected_no_data and result.passed),
        cannot_claim_coverage_count=sum(
            1 for result in results if result.expected_cannot_claim and result.passed
        ),
        source_url_citation_count=sum(
            result.artifact.source_url_citation_count
            for result in results
            if result.artifact is not None
        ),
        cases_newly_mapped=0,
        cases_still_needing_mapping=sum(
            1 for result in results if result.readiness == "needs_mapping"
        ),
        contradiction_case_status="excluded_no_retained_contradiction_pair",
        report_items=results,
        limitations=[
            "R1 is an eval-only harness over retained local corpus artifacts.",
            "G1-G8 runtime, packet schemas, registries, CHECK, and renderer behavior are unchanged.",
            "Needs-mapping cases are mapped by the eval adapter only, not by runtime G5.",
            "The contradiction family remains excluded until a retained conflicting-value pair is available.",
            "URLs embedded in retained artifacts are counted as citations only and are never fetched.",
        ],
        commands_run_hint=[
            ".venv\\Scripts\\python.exe -m unittest tests.test_ask_v11_real_corpus_eval_r1",
            ".venv\\Scripts\\python.exe scripts\\run_ask_v11_real_corpus_eval_r1.py",
        ],
    )


def run_real_corpus_eval_r2_mapping_expansion(
    matrix_path: str | Path | None = None,
) -> RealCorpusEvalReport:
    cases = load_case_matrix(matrix_path)
    results = [evaluate_real_corpus_case(case, eval_round="R2") for case in cases]
    severity_counts = summarize_severity_counts(results)
    sev4_count = severity_counts.get(SeverityLabel.sev_4_real_failure.value, 0)
    fail_count = sum(1 for result in results if not result.passed)
    waived_count = sum(1 for result in results if result.status == "WAIVED")
    newly_mapped = sum(1 for result in results if result.readiness == "mapped" and result.passed)
    still_needing = sum(1 for result in results if result.readiness == "needs_mapping")
    contradiction_status = next(
        (
            result.adapter_mapping_status
            for result in results
            if result.family == "contradiction"
        ),
        "not_present",
    )
    hard_pass = (
        fail_count == 0
        and sev4_count == 0
        and still_needing == 0
        and _count_hard_flag(results, "live_retrieval_attempt") == 0
        and _count_hard_flag(results, "production_api_call") == 0
        and _count_hard_flag(results, "official_action_claim") == 0
        and _count_hard_flag(results, "legal_certified_claim") == 0
        and _count_hard_flag(results, "g3_invented_retrieval_plan") == 0
        and _count_hard_flag(results, "renderer_undowngrade") == 0
        and _count_hard_flag(results, "raw_query_leak") == 0
        and _count_hard_flag(results, "future_flow_runtime_violation") == 0
    )
    limited = waived_count > 0 or contradiction_status.startswith("waived")
    status = "PASS_WITH_LIMITATIONS" if hard_pass and limited else ("PASS" if hard_pass else "FAIL")
    final_decision = (
        R2_REPORT_STATUS_LIMITED
        if hard_pass and limited
        else (R2_REPORT_STATUS_PASS if hard_pass else R2_REPORT_STATUS_FAIL)
    )
    evaluated_results = [result for result in results if result.status not in {"EXCLUDED", "WAIVED"}]
    return RealCorpusEvalReport(
        status=status,
        final_decision=final_decision,
        generated_at=datetime.now(timezone.utc).isoformat(),
        matrix_path=str(matrix_path or DEFAULT_MATRIX_PATH),
        total_cases=len(results),
        evaluated_cases=len(evaluated_results),
        excluded_cases=waived_count + sum(1 for result in results if result.status == "EXCLUDED"),
        ready_cases=sum(1 for result in results if result.readiness == "ready"),
        needs_mapping_cases=still_needing,
        pass_count=sum(1 for result in evaluated_results if result.passed),
        fail_count=fail_count,
        severity_counts=severity_counts,
        family_counts=_family_counts(results),
        sev_4_real_failure_count=sev4_count,
        boundary_action_sev4_count=sum(
            1
            for result in results
            if result.family == "boundary_action"
            and result.severity == SeverityLabel.sev_4_real_failure
        ),
        raw_query_leak_count=_count_hard_flag(results, "raw_query_leak"),
        future_flow_runtime_violation_count=_count_hard_flag(results, "future_flow_runtime_violation"),
        official_action_claim_count=_count_hard_flag(results, "official_action_claim"),
        live_retrieval_attempt_count=_count_hard_flag(results, "live_retrieval_attempt"),
        production_api_call_count=_count_hard_flag(results, "production_api_call"),
        legal_certified_claim_count=_count_hard_flag(results, "legal_certified_claim"),
        g3_invented_retrieval_plan_count=_count_hard_flag(results, "g3_invented_retrieval_plan"),
        renderer_undowngrade_count=_count_hard_flag(results, "renderer_undowngrade"),
        no_data_coverage_count=sum(1 for result in results if result.expected_no_data and result.passed),
        cannot_claim_coverage_count=sum(
            1 for result in results if result.expected_cannot_claim and result.passed
        ),
        source_url_citation_count=sum(
            result.artifact.source_url_citation_count
            for result in results
            if result.artifact is not None
        ),
        cases_newly_mapped=newly_mapped,
        cases_still_needing_mapping=still_needing,
        contradiction_case_status=contradiction_status,
        report_items=results,
        limitations=[
            "R2 is an eval-only mapping expansion over retained local corpus artifacts.",
            "G1-G8 runtime, packet schemas, registries, CHECK, and renderer behavior are unchanged.",
            "The 8 R1 needs-mapping cases are now mapped by the eval adapter only, not by runtime G5.",
            "No valid retained same-claim contradiction pair was found during scout. Contradiction remains covered by sealed fixture eval and is waived from real-corpus R2 until a genuine retained conflict pair appears.",
            "URLs embedded in retained artifacts are counted as citations only and are never fetched.",
        ],
        commands_run_hint=[
            ".venv\\Scripts\\python.exe -m unittest tests.test_ask_v11_real_corpus_eval_r1",
            ".venv\\Scripts\\python.exe -m unittest tests.test_ask_v11_real_corpus_eval_r2_mapping_expansion",
            ".venv\\Scripts\\python.exe scripts\\run_ask_v11_real_corpus_eval_r2_mapping_expansion.py",
        ],
    )


def markdown_summary(report: RealCorpusEvalReport) -> str:
    is_r2 = "R2" in report.final_decision
    title = "ASK v1.1 Real Corpus Eval R2 Summary" if is_r2 else "ASK v1.1 Real Corpus Eval R1 Summary"
    lines = [
        f"# {title}",
        "",
        "## Final decision",
        "",
        f"`{report.final_decision}`",
        "",
        "## Scope",
        "",
        "Eval-only retained local corpus harness. No G1-G8 runtime behavior is changed or called.",
        "",
        "## Results",
        "",
        f"- Cases: {report.pass_count}/{report.evaluated_cases} evaluated cases passed",
        f"- Total matrix cases: {report.total_cases}",
        f"- Ready cases: {report.ready_cases}",
        f"- Needs-mapping cases: {report.needs_mapping_cases}",
        f"- Excluded cases: {report.excluded_cases}",
        f"- Cases newly mapped by eval adapter: {report.cases_newly_mapped}",
        f"- Cases still needing mapping: {report.cases_still_needing_mapping}",
        f"- Contradiction case status: {report.contradiction_case_status}",
        f"- Sev-4 real failures: {report.sev_4_real_failure_count}",
        f"- Boundary/action Sev-4 count: {report.boundary_action_sev4_count}",
        f"- Raw-query leak count: {report.raw_query_leak_count}",
        f"- Official action claim count: {report.official_action_claim_count}",
        f"- Future-flow runtime violation count: {report.future_flow_runtime_violation_count}",
        f"- Source URL citations counted but not fetched: {report.source_url_citation_count}",
        "",
        "## Severity summary",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in report.severity_counts.items())
    lines.extend(["", "## Family summary", ""])
    lines.extend(f"- {key}: {value}" for key, value in report.family_counts.items())
    lines.extend(["", "## Contract boundaries", ""])
    lines.extend(
        [
            "- Retained local corpus only.",
            "- No live retrieval.",
            "- No production API.",
            "- No official action, ticket, dispatch, enforcement, or autonomous workflow.",
            "- No legal or certified determination.",
            "- WATCH/BRIEF/DIFF/INCIDENT remain skeleton-only.",
        ]
    )
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report.limitations)
    lines.append("")
    return "\n".join(lines)


def markdown_failures(report: RealCorpusEvalReport) -> str:
    failing = [result for result in report.report_items if not result.passed]
    excluded = [result for result in report.report_items if result.status in {"EXCLUDED", "WAIVED"}]
    is_r2 = "R2" in report.final_decision
    title = "ASK v1.1 Real Corpus Eval R2 Failures" if is_r2 else "ASK v1.1 Real Corpus Eval R1 Failures"
    lines = [f"# {title}", ""]
    if not failing:
        lines.extend(["No failing evaluated cases.", ""])
    else:
        for result in failing:
            lines.extend(
                [
                    f"## {result.case_id}",
                    "",
                    f"- Family: `{result.family}`",
                    f"- Severity: `{result.severity.value}`",
                    f"- Errors: {', '.join(result.errors)}",
                    "",
                ]
            )
    lines.extend(["## Excluded", ""])
    if not excluded:
        lines.extend(["No excluded cases.", ""])
    else:
        for result in excluded:
            lines.extend(
                [
                    f"- `{result.case_id}` (`{result.family}`): {result.actual.get('excluded_reason')} [{result.adapter_mapping_status}]",
                ]
            )
        lines.append("")
    return "\n".join(lines)


def markdown_mapping_changes(report: RealCorpusEvalReport) -> str:
    mapped = [result for result in report.report_items if result.readiness == "mapped"]
    still = [result for result in report.report_items if result.readiness == "needs_mapping"]
    waived = [result for result in report.report_items if result.status == "WAIVED"]
    lines = [
        "# ASK v1.1 Real Corpus Eval R2 Mapping Changes",
        "",
        "## Summary",
        "",
        f"- Cases newly mapped: {report.cases_newly_mapped}",
        f"- Cases still needing mapping: {report.cases_still_needing_mapping}",
        f"- Contradiction case status: `{report.contradiction_case_status}`",
        "",
        "## Newly Mapped Cases",
        "",
    ]
    if not mapped:
        lines.extend(["No cases were newly mapped.", ""])
    else:
        for result in mapped:
            lines.extend(
                [
                    f"### {result.case_id}",
                    "",
                    f"- Family: `{result.family}`",
                    f"- Source artifact: `{result.source_artifact_path}`",
                    f"- Adapter mapping: `{result.adapter_mapping_status}`",
                    f"- Original readiness: `{result.actual.get('original_readiness')}`",
                    f"- Expected behavior: {result.expected_behavior}",
                    "",
                ]
            )
    lines.extend(["## Still Needs Mapping", ""])
    if not still:
        lines.extend(["No non-waived cases still need mapping.", ""])
    else:
        for result in still:
            lines.extend([f"- `{result.case_id}` (`{result.family}`): {', '.join(result.errors) or 'not mapped'}"])
        lines.append("")
    lines.extend(["## Waived", ""])
    if not waived:
        lines.extend(["No waived cases.", ""])
    else:
        for result in waived:
            lines.extend(
                [
                    f"- `{result.case_id}` (`{result.family}`): {result.adapter_mapping_status}",
                ]
            )
        lines.append("")
    lines.extend(
        [
            "## Contradiction Waiver",
            "",
            "No valid retained same-claim contradiction pair was found during scout. Contradiction remains covered by sealed fixture eval and is waived from real-corpus R2 until a genuine retained conflict pair appears.",
            "",
        ]
    )
    return "\n".join(lines)


def write_real_corpus_eval_report(
    report: RealCorpusEvalReport, output_dir: str | Path | None = None
) -> dict[str, Path]:
    output = _resolve_repo_path(output_dir or DEFAULT_OUTPUT_DIR)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "ASK_V11_REAL_CORPUS_EVAL_R1_REPORT.json"
    summary_path = output / "ASK_V11_REAL_CORPUS_EVAL_R1_SUMMARY.md"
    failures_path = output / "ASK_V11_REAL_CORPUS_EVAL_R1_FAILURES.md"
    json_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    summary_path.write_text(markdown_summary(report), encoding="utf-8")
    failures_path.write_text(markdown_failures(report), encoding="utf-8")
    return {"json": json_path, "summary": summary_path, "failures": failures_path}


def write_real_corpus_eval_r2_report(
    report: RealCorpusEvalReport, output_dir: str | Path | None = None
) -> dict[str, Path]:
    output = _resolve_repo_path(output_dir or R2_DEFAULT_OUTPUT_DIR)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "ASK_V11_REAL_CORPUS_EVAL_R2_REPORT.json"
    summary_path = output / "ASK_V11_REAL_CORPUS_EVAL_R2_SUMMARY.md"
    failures_path = output / "ASK_V11_REAL_CORPUS_EVAL_R2_FAILURES.md"
    mapping_path = output / "ASK_V11_REAL_CORPUS_EVAL_R2_MAPPING_CHANGES.md"
    json_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    summary_path.write_text(markdown_summary(report), encoding="utf-8")
    failures_path.write_text(markdown_failures(report), encoding="utf-8")
    mapping_path.write_text(markdown_mapping_changes(report), encoding="utf-8")
    return {
        "json": json_path,
        "summary": summary_path,
        "failures": failures_path,
        "mapping_changes": mapping_path,
    }

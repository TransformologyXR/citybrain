"""G6 deterministic CHECK engine for ASK v1.1."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .packets import (
    Abstain,
    BindingFinding,
    CheckFinding,
    CheckKind,
    CheckReport,
    CheckVerdict,
    CheckVerdictKind,
    ClaimDowngrade,
    ConceptBindingStatus,
    Contradiction,
    CoverageNote,
    EvidencePacket,
    ExecutionContract,
    IntentPacket,
    StalenessFinding,
)


FRESHNESS_NOW = datetime(2026, 7, 3, tzinfo=timezone.utc)
FRESHNESS_MAX_AGE_DAYS = 365
LOW_CONFIDENCE_THRESHOLD = 0.65


def _all_evidence_items(evidence_packet: EvidencePacket) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for collection in (evidence_packet.facts, evidence_packet.rows, evidence_packet.series):
        items.extend(item for item in collection if isinstance(item, dict))
    return items


def _flatten_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return str(value)


def _has_evidence(evidence_packet: EvidencePacket) -> bool:
    return bool(evidence_packet.facts or evidence_packet.rows or evidence_packet.series)


def _is_static_source(source_type: str | None) -> bool:
    return source_type in {"fixture", "internal_contract_note", "internal_registry_note"}


def _age_days(value: datetime) -> int:
    observed = value
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    return (FRESHNESS_NOW - observed).days


def _source_refs_stale(evidence_packet: EvidencePacket) -> list[StalenessFinding]:
    findings: list[StalenessFinding] = []
    for source in evidence_packet.source_refs:
        observed = source.as_of or source.observed_at
        if observed is None:
            if source.source_type and "live" in source.source_type and not _is_static_source(source.source_type):
                findings.append(
                    StalenessFinding(
                        reason=f"{source.source_id} has no observed_at/as_of for a live source",
                        refs=[source.source_id],
                    )
                )
            continue
        if _age_days(observed) > FRESHNESS_MAX_AGE_DAYS:
            findings.append(
                StalenessFinding(
                    as_of=observed,
                    reason=f"{source.source_id} is older than freshness policy",
                    refs=[source.source_id],
                )
            )
    return findings


def _candidate_findings(evidence_packet: EvidencePacket) -> list[ClaimDowngrade]:
    downgrades: list[ClaimDowngrade] = []
    for item in _all_evidence_items(evidence_packet):
        text = _flatten_text(item).lower()
        confidence = item.get("confidence")
        review_state = str(item.get("review_state") or item.get("status") or "").lower()
        is_candidate = bool(item.get("candidate") or item.get("inferred"))
        low_confidence = isinstance(confidence, (int, float)) and confidence < LOW_CONFIDENCE_THRESHOLD
        pending = review_state in {"pending", "candidate", "unverified"}
        if is_candidate or low_confidence or pending:
            label = item.get("claim") or item.get("fact_id") or item.get("queue_item_ref") or "candidate evidence claim"
            reason_parts = []
            if is_candidate:
                reason_parts.append("candidate/inferred evidence")
            if low_confidence:
                reason_parts.append(f"confidence below {LOW_CONFIDENCE_THRESHOLD}")
            if pending:
                reason_parts.append(f"review_state/status is {review_state}")
            downgrades.append(
                ClaimDowngrade(
                    claim=str(label),
                    downgraded_to="candidate or unverified context only",
                    reason=", ".join(reason_parts) or f"candidate marker in {text[:60]}",
                )
            )
    return downgrades


def _proximity_downgrades(evidence_packet: EvidencePacket) -> list[ClaimDowngrade]:
    text = _flatten_text(_all_evidence_items(evidence_packet)).lower()
    proximity_terms = ("nearby", "near ", "proximity", "adjacent")
    confirmed_terms = ("confirmed causal", "confirmed blockage source", "access-status source")
    if any(term in text for term in proximity_terms) and not any(term in text for term in confirmed_terms):
        return [
            ClaimDowngrade(
                claim="nearby source affects/blocks/causes the subject",
                downgraded_to="nearby/proximity context only",
                reason="proximity is not causality",
            )
        ]
    return []


def _contradictions(evidence_packet: EvidencePacket) -> list[Contradiction]:
    contradictions: list[Contradiction] = []
    values_by_field: dict[str, set[str]] = {}
    for item in _all_evidence_items(evidence_packet):
        if item.get("contradiction") or item.get("contradiction_marker"):
            contradictions.append(
                Contradiction(
                    reason=str(item.get("reason") or "contradiction marker present"),
                    refs=[str(item.get("fact_id") or item.get("row_id") or "evidence")],
                )
            )
        claim_field = item.get("claimable_field")
        claim_value = item.get("claim_value")
        if claim_field is not None and claim_value is not None:
            values_by_field.setdefault(str(claim_field), set()).add(str(claim_value))
    for field, values in values_by_field.items():
        if len(values) > 1:
            contradictions.append(
                Contradiction(
                    reason=f"conflicting values for {field}: {', '.join(sorted(values))}",
                    refs=[field],
                )
            )
    return contradictions


def _binding_findings(intent_packet: IntentPacket | None) -> tuple[list[BindingFinding], list[Abstain], list[CheckVerdict]]:
    findings: list[BindingFinding] = []
    abstains: list[Abstain] = []
    verdicts: list[CheckVerdict] = []
    if intent_packet is None:
        return findings, abstains, verdicts

    for binding in intent_packet.concept_bindings:
        status = binding.status
        finding_text = binding.claimability or f"binding status is {status.value}"
        findings.append(
            BindingFinding(
                concept=binding.concept,
                status=status,
                finding=finding_text,
            )
        )
        if status in {
            ConceptBindingStatus.known_external_not_ingested,
            ConceptBindingStatus.unknown_concept,
        }:
            reason = "; ".join(binding.cannot_claim) or finding_text
            abstains.append(Abstain(reason=reason))
            verdicts.append(
                CheckVerdict(
                    verdict=CheckVerdictKind.abstain_required,
                    claim=binding.concept,
                    reason=reason,
                )
            )
        elif status == ConceptBindingStatus.derived_field:
            verdicts.append(
                CheckVerdict(
                    verdict=CheckVerdictKind.downgrade,
                    claim=binding.concept,
                    reason="derived concept can support proxy context, not source-fact certainty",
                )
            )
    return findings, abstains, verdicts


def _overall_claimability(
    *,
    no_data: bool,
    contradictions: list[Contradiction],
    abstains: list[Abstain],
    stale: list[StalenessFinding],
    downgrades: list[ClaimDowngrade],
    coverage_limits: list[CoverageNote],
    source_fail: bool,
) -> str:
    if contradictions:
        return "contradicted"
    if no_data:
        return "not_claimable"
    if abstains:
        return "abstain_required"
    if stale:
        return "stale"
    if downgrades or coverage_limits or source_fail:
        return "partially_claimable"
    return "claimable"


def evidence_validate(
    evidence_packet: EvidencePacket,
    execution_contract: ExecutionContract,
    intent_packet: IntentPacket | None = None,
) -> CheckReport:
    checks: list[CheckFinding] = []
    verdicts: list[CheckVerdict] = []
    claim_downgrades: list[ClaimDowngrade] = []
    abstains: list[Abstain] = []
    coverage_limits: list[CoverageNote] = []

    no_data = evidence_packet.flags.no_data or not _has_evidence(evidence_packet)
    if no_data:
        verdicts.append(
            CheckVerdict(
                verdict=CheckVerdictKind.insufficient_no_data,
                reason="No retained facts, rows, or series were available.",
            )
        )
        coverage_limits.append(
            CoverageNote(
                summary="No retained rows or facts were available for this template execution.",
                limitations=evidence_packet.gaps or ["no retained evidence returned"],
                coverage_status="no_data",
            )
        )
    checks.append(
        CheckFinding(
            check=CheckKind.source_depth,
            status="pass" if evidence_packet.source_refs else "fail",
            reason="source_refs present" if evidence_packet.source_refs else "no source_refs present",
            refs=[source.source_id for source in evidence_packet.source_refs],
        )
    )
    source_fail = not bool(evidence_packet.source_refs)
    if source_fail:
        abstains.append(Abstain(reason="No source references were available for claim support."))
        verdicts.append(
            CheckVerdict(
                verdict=CheckVerdictKind.abstain_required,
                reason="source_depth failed because source_refs were empty",
            )
        )

    stale_findings = _source_refs_stale(evidence_packet)
    checks.append(
        CheckFinding(
            check=CheckKind.freshness_staleness,
            status="stale" if stale_findings else "pass",
            reason="stale source found" if stale_findings else "freshness policy satisfied or static fixture",
            refs=[ref for finding in stale_findings for ref in finding.refs],
        )
    )
    for finding in stale_findings:
        verdicts.append(
            CheckVerdict(
                verdict=CheckVerdictKind.stale_flag,
                reason=finding.reason,
                refs=finding.refs,
                as_of=finding.as_of,
            )
        )

    candidate_downgrades = _candidate_findings(evidence_packet)
    claim_downgrades.extend(candidate_downgrades)
    checks.append(
        CheckFinding(
            check=CheckKind.candidate_inferred_link_confidence,
            status="downgrade" if candidate_downgrades else "pass",
            reason="candidate/inferred/low-confidence marker found" if candidate_downgrades else "no candidate-link downgrade markers",
        )
    )
    for downgrade in candidate_downgrades:
        verdicts.append(
            CheckVerdict(
                verdict=CheckVerdictKind.downgrade,
                claim=downgrade.claim,
                reason=downgrade.reason,
            )
        )

    proximity_downgrades = _proximity_downgrades(evidence_packet)
    claim_downgrades.extend(proximity_downgrades)
    checks.append(
        CheckFinding(
            check=CheckKind.proximity_vs_causality,
            status="downgrade" if proximity_downgrades else "pass",
            reason="proximity is not causality" if proximity_downgrades else "no unsupported proximity-to-causality claim",
        )
    )
    for downgrade in proximity_downgrades:
        verdicts.append(
            CheckVerdict(
                verdict=CheckVerdictKind.downgrade,
                claim=downgrade.claim,
                reason=downgrade.reason,
            )
        )

    contradictions = _contradictions(evidence_packet)
    checks.append(
        CheckFinding(
            check=CheckKind.contradiction,
            status="fail" if contradictions else "pass",
            reason="contradiction found" if contradictions else "no contradiction markers",
            refs=[ref for contradiction in contradictions for ref in contradiction.refs],
        )
    )
    for contradiction in contradictions:
        verdicts.append(
            CheckVerdict(
                verdict=CheckVerdictKind.contradiction_flag,
                reason=contradiction.reason,
                refs=contradiction.refs,
            )
        )

    if evidence_packet.flags.partial_result or evidence_packet.flags.truncated:
        coverage_limits.append(
            CoverageNote(
                summary="Evidence coverage is partial or truncated.",
                limitations=[
                    flag
                    for flag, enabled in (
                        ("partial_result", evidence_packet.flags.partial_result),
                        ("truncated", evidence_packet.flags.truncated),
                    )
                    if enabled
                ],
                coverage_status="partial",
            )
        )
    checks.append(
        CheckFinding(
            check=CheckKind.coverage_limits,
            status="partial" if coverage_limits else "pass",
            reason="coverage limits present" if coverage_limits else "no coverage limits detected",
        )
    )

    binding_findings, binding_abstains, binding_verdicts = _binding_findings(intent_packet)
    abstains.extend(binding_abstains)
    verdicts.extend(binding_verdicts)
    checks.append(
        CheckFinding(
            check=CheckKind.binding_status,
            status="needs_abstain" if binding_abstains else "pass",
            reason="concept binding limits present" if binding_findings else "no concept bindings supplied",
            refs=[finding.concept for finding in binding_findings],
        )
    )

    if not verdicts and not claim_downgrades:
        verdicts.append(
            CheckVerdict(
                verdict=CheckVerdictKind.sufficient,
                reason="Evidence passed deterministic G6 checks.",
            )
        )

    overall_claimability = _overall_claimability(
        no_data=no_data,
        contradictions=contradictions,
        abstains=abstains,
        stale=stale_findings,
        downgrades=claim_downgrades,
        coverage_limits=coverage_limits,
        source_fail=source_fail,
    )
    return CheckReport(
        checks=checks,
        verdicts=verdicts,
        claim_downgrades=claim_downgrades,
        abstains=abstains,
        coverage_limits=coverage_limits,
        contradictions=contradictions,
        staleness=stale_findings,
        binding_findings=binding_findings,
        overall_claimability=overall_claimability,
    )

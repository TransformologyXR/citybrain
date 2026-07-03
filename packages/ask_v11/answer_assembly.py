"""G7 deterministic AnswerPacket assembly for ASK v1.1."""

from __future__ import annotations

from .packets import (
    AnswerPacket,
    CheckReport,
    CheckVerdictKind,
    CitationRef,
    CoverageNote,
    EvidencePacket,
    ExecutionContract,
    IntentPacket,
)


def _verdicts(check_report: CheckReport, verdict: CheckVerdictKind) -> list:
    return [item for item in check_report.verdicts if item.verdict == verdict]


def _fact_texts(evidence_packet: EvidencePacket) -> list[str]:
    texts: list[str] = []
    for fact in evidence_packet.facts:
        text = fact.get("text") if isinstance(fact, dict) else None
        if text:
            texts.append(str(text))
    return texts


def _citations(evidence_packet: EvidencePacket) -> list[CitationRef]:
    citations: list[CitationRef] = []
    for index, source in enumerate(evidence_packet.source_refs, start=1):
        citations.append(
            CitationRef(
                citation_id=f"cite:{index}",
                source_ref=source.source_id,
                label=source.title or source.source_id,
            )
        )
    return citations


def _coverage_note(evidence_packet: EvidencePacket, check_report: CheckReport) -> CoverageNote:
    if check_report.coverage_limits:
        first = check_report.coverage_limits[0]
        limitations = list(first.limitations)
        for finding in check_report.staleness:
            limitations.append(finding.reason)
        return CoverageNote(
            summary=first.summary,
            limitations=limitations,
            as_of=first.as_of,
            coverage_status=first.coverage_status or check_report.overall_claimability,
        )
    limitations = list(evidence_packet.gaps)
    limitations.extend(finding.reason for finding in check_report.staleness)
    return CoverageNote(
        summary=f"CHECK overall claimability: {check_report.overall_claimability}",
        limitations=limitations,
        coverage_status=check_report.overall_claimability,
    )


def _cannot_claims(check_report: CheckReport, evidence_packet: EvidencePacket) -> list[str]:
    claims: list[str] = []
    for downgrade in check_report.claim_downgrades:
        claims.append(
            f"{downgrade.claim} as more than {downgrade.downgraded_to}: {downgrade.reason}"
        )
    for abstain in check_report.abstains:
        claims.append(abstain.reason)
    for contradiction in check_report.contradictions:
        claims.append(f"resolved winner for contradiction: {contradiction.reason}")
    for stale in check_report.staleness:
        claims.append(f"fresh/current claim: {stale.reason}")
    for gap in evidence_packet.gaps:
        claims.append(f"claim beyond retained evidence: {gap}")
    for warning in evidence_packet.warnings:
        if "cannot" in warning.lower() or "not " in warning.lower():
            claims.append(warning)
    return list(dict.fromkeys(claims))


def _unknowns(check_report: CheckReport, evidence_packet: EvidencePacket) -> list[str]:
    unknowns: list[str] = []
    if _verdicts(check_report, CheckVerdictKind.insufficient_no_data):
        unknowns.append("No retained facts, rows, or series were found for this request.")
    unknowns.extend(evidence_packet.gaps)
    for abstain in check_report.abstains:
        unknowns.append(f"Unclaimable without source support: {abstain.reason}")
    for contradiction in check_report.contradictions:
        unknowns.append(f"Contradiction unresolved: {contradiction.reason}")
    for stale in check_report.staleness:
        unknowns.append(f"Freshness unresolved: {stale.reason}")
    return list(dict.fromkeys(unknowns))


def _knowns_for_shape(
    evidence_packet: EvidencePacket,
    check_report: CheckReport,
    execution_contract: ExecutionContract,
) -> list[str]:
    shape = execution_contract.answer_contract.shape
    if check_report.contradictions:
        return ["Evidence contains a contradiction; ASK v1.1 does not choose a winner in P3."]
    if _verdicts(check_report, CheckVerdictKind.insufficient_no_data):
        if shape == "external_source_needed":
            concept = execution_contract.args.get("concept", "the requested external concept")
            return [f"Retained evidence does not include the live external fact for {concept}."]
        return []

    texts = _fact_texts(evidence_packet)
    if shape == "ui_help_static":
        return texts or ["This board can answer bounded retained-record questions."]
    if shape == "list_count_filter":
        knowns = texts[:]
        for fact in evidence_packet.facts:
            if isinstance(fact, dict) and "count" in fact:
                knowns.append(f"Retained queue fixture count: {fact['count']}.")
        return list(dict.fromkeys(knowns))
    if shape == "source_record_profile":
        return texts or ["A retained source record fixture was found."]

    knowns = texts[:]
    for downgrade in check_report.claim_downgrades:
        knowns.append(f"Safe claim: {downgrade.downgraded_to} ({downgrade.reason}).")
    return list(dict.fromkeys(knowns))


def _safe_next_looks(check_report: CheckReport, intent_packet: IntentPacket | None) -> list[str]:
    looks: list[str] = []
    for binding in (intent_packet.concept_bindings if intent_packet else []):
        if binding.owner:
            looks.append(f"Look for retained or integrated source from {binding.owner}.")
    if check_report.overall_claimability in {"not_claimable", "abstain_required", "stale"}:
        looks.append("Look for retained source records that directly support the missing claim.")
    return list(dict.fromkeys(looks))


def answer_assemble(
    evidence_packet: EvidencePacket,
    check_report: CheckReport | None,
    execution_contract: ExecutionContract,
    intent_packet: IntentPacket | None = None,
    check_report_ref: str = "check:g6",
) -> AnswerPacket:
    if check_report is None:
        raise ValueError("No CheckReport means no normal AnswerPacket.")
    if not check_report.overall_claimability:
        raise ValueError("Invalid CheckReport: overall_claimability is required.")

    cannot_claim = _cannot_claims(check_report, evidence_packet)
    if execution_contract.answer_contract.shape == "ui_help_static":
        cannot_claim.append("No official external action was executed.")
    knowns = _knowns_for_shape(evidence_packet, check_report, execution_contract)
    unknowns = _unknowns(check_report, evidence_packet)
    return AnswerPacket(
        knowns=knowns,
        unknowns=unknowns,
        cannot_claim=list(dict.fromkeys(cannot_claim)),
        citations=_citations(evidence_packet),
        coverage_note=_coverage_note(evidence_packet, check_report),
        check_report_ref=check_report_ref,
        lens=execution_contract.answer_contract.lens_default,
        safe_next_looks=_safe_next_looks(check_report, intent_packet),
        not_executed=list(evidence_packet.not_executed),
    )

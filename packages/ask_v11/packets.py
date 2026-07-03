"""TXR CityBrain ASK Flow v1.1 packet and envelope contracts.

These models implement the P0 contract foundation only. They deliberately do
not route, retrieve, check, answer, or render. The important boundary here is
packet discipline: after G2, downstream stages consume typed packets and never
receive the raw user query.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


RAW_QUERY_KEY = "raw_query"


def _contains_raw_query_key(value: Any) -> bool:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python")
    if isinstance(value, dict):
        return any(
            key == RAW_QUERY_KEY or _contains_raw_query_key(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple, set)):
        return any(_contains_raw_query_key(item) for item in value)
    return False


class StrictPacketModel(BaseModel):
    """Base for packet outputs that must not carry raw user query text."""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _reject_raw_query_payloads(self) -> "StrictPacketModel":
        payload = self.model_dump(mode="python", exclude_none=True)
        if _contains_raw_query_key(payload):
            raise ValueError(
                "ASK v1.1 packet discipline violation: raw_query is allowed "
                "only in FlowRunInput/G1/G2 inputs, not downstream packets."
            )
        return self


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BoundaryResult(str, Enum):
    clear = "clear"
    action_shaped = "action_shaped"
    prediction_or_finding = "prediction_or_finding"
    identity_or_person = "identity_or_person"
    out_of_scope_domain = "out_of_scope_domain"
    ambiguous_boundary = "ambiguous_boundary"


class RouteKind(str, Enum):
    template_call = "template_call"
    ui_help = "ui_help"
    gap = "gap"
    clarify = "clarify"
    refuse = "refuse"


class ConceptBindingStatus(str, Enum):
    retained_field = "retained_field"
    derived_field = "derived_field"
    integrated_from = "integrated_from"
    known_external_not_ingested = "known_external_not_ingested"
    unknown_concept = "unknown_concept"


class CheckKind(str, Enum):
    source_depth = "source_depth"
    freshness_staleness = "freshness_staleness"
    candidate_inferred_link_confidence = "candidate_inferred_link_confidence"
    proximity_vs_causality = "proximity_vs_causality"
    contradiction = "contradiction"
    coverage_limits = "coverage_limits"
    binding_status = "binding_status"


class CheckVerdictKind(str, Enum):
    sufficient = "sufficient"
    downgrade = "downgrade"
    insufficient_no_data = "insufficient_no_data"
    contradiction_flag = "contradiction_flag"
    stale_flag = "stale_flag"
    abstain_required = "abstain_required"


class SeverityLabel(str, Enum):
    sev_0_clean = "sev_0_clean"
    sev_1_taxonomy_reporting_only = "sev_1_taxonomy_reporting_only"
    sev_2_acceptable_but_weak = "sev_2_acceptable_but_weak"
    sev_3_audit_uncertain = "sev_3_audit_uncertain"
    sev_4_real_failure = "sev_4_real_failure"


class IntentFamily(str, Enum):
    subject_answer = "subject_answer"
    entity_profile = "entity_profile"
    source_record_profile = "source_record_profile"
    patch_queue_query = "patch_queue_query"
    external_context_need = "external_context_need"
    board_meta = "board_meta"
    boundary_refusal = "boundary_refusal"
    unknown = "unknown"


class Lens(str, Enum):
    support = "support"
    uncertainty = "uncertainty"
    claimability = "claimability"
    summary = "summary"


class EvidenceFlags(StrictPacketModel):
    no_data: bool = False
    partial_result: bool = False
    truncated: bool = False


class ContextFlags(StrictPacketModel):
    requires_selected_item: bool = False
    follow_up_of: str | None = None


class FlowRunInput(InputModel):
    flow_id: str = Field(default="flow:ask_v1")
    flow_version: str = Field(default="1.1")
    run_id: str
    raw_query: str = Field(min_length=1)
    session_state: dict[str, Any] = Field(default_factory=dict)
    selected_item_ref: str | None = None


class BoundaryScreenPacket(StrictPacketModel):
    stage_id: str = Field(default="G1")
    gate_id: str = Field(default="boundary_screen@1.1")
    boundary: BoundaryResult
    reason_codes: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class SourceRef(StrictPacketModel):
    source_id: str
    source_type: str | None = None
    title: str | None = None
    uri: str | None = None
    observed_at: datetime | None = None
    as_of: datetime | None = None
    owner: str | None = None
    claim_boundary: str | None = None


class EvidenceRef(StrictPacketModel):
    evidence_id: str
    source_ref: str
    locator: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class CitationRef(StrictPacketModel):
    citation_id: str
    source_ref: str
    evidence_refs: list[str] = Field(default_factory=list)
    label: str | None = None


class CoverageNote(StrictPacketModel):
    summary: str
    limitations: list[str] = Field(default_factory=list)
    as_of: datetime | None = None
    coverage_status: str | None = None


class ConceptBinding(StrictPacketModel):
    concept: str
    family: str | None = None
    status: ConceptBindingStatus
    source: str | None = Field(
        default=None,
        description="Required when status is integrated_from.",
    )
    field_ref: str | None = None
    owner: str | None = None
    claimability: str | None = None
    cannot_claim: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _integrated_from_requires_source(self) -> "ConceptBinding":
        if self.status == ConceptBindingStatus.integrated_from and not self.source:
            raise ValueError("integrated_from bindings require source")
        return self


class IntentPacket(StrictPacketModel):
    intent_family: IntentFamily
    subject_candidates: list[str] = Field(default_factory=list)
    concept_bindings: list[ConceptBinding] = Field(default_factory=list)
    context_flags: ContextFlags = Field(default_factory=ContextFlags)
    ambiguity_flags: list[str] = Field(default_factory=list)
    clarification_candidates: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    resolver_telemetry: dict[str, Any] = Field(default_factory=dict)


class RouteSelection(StrictPacketModel):
    kind: RouteKind
    gap_id: str | None = None
    refusal_class: str | None = None

    @model_validator(mode="after")
    def _tagged_route_fields(self) -> "RouteSelection":
        if self.kind == RouteKind.gap and not self.gap_id:
            raise ValueError("gap routes require gap_id")
        if self.kind == RouteKind.refuse and not self.refusal_class:
            raise ValueError("refuse routes require refusal_class")
        return self


class TemplateRef(StrictPacketModel):
    template_id: str
    version: str


class RetrievalGroup(StrictPacketModel):
    group_id: str
    source_refs: list[str] = Field(default_factory=list)
    args: dict[str, Any] = Field(default_factory=dict)
    parallelizable: bool = True


class RetrievalPlan(StrictPacketModel):
    groups: list[RetrievalGroup] = Field(
        default_factory=list,
        description="Flat, parallelizable retrieval groups only; no nested plans.",
    )


class DerivedFeature(StrictPacketModel):
    feature_id: str
    source_fields: list[str] = Field(default_factory=list)
    derivation: str


class AnswerContract(StrictPacketModel):
    shape: str
    lens_default: Lens = Lens.support
    required_sections: list[str] = Field(default_factory=list)
    citation_policy: str | None = None


class TemplateDeclaration(StrictPacketModel):
    template_id: str
    version: str
    intent_families: list[IntentFamily] = Field(default_factory=list)
    required_args: list[str] = Field(default_factory=list)
    required_sources: list[SourceRef] = Field(default_factory=list)
    retrieval_plan: RetrievalPlan = Field(default_factory=RetrievalPlan)
    derived_features: list[DerivedFeature] = Field(default_factory=list)
    answer_contract: AnswerContract
    notes: str | None = Field(
        default=None,
        description=(
            "G3 instantiates registry-declared template plans only. "
            "G3 does not invent retrieval plans."
        ),
    )


class ExecutionContract(StrictPacketModel):
    route: RouteSelection
    template_ref: TemplateRef | None = None
    args: dict[str, Any] = Field(default_factory=dict)
    required_sources: list[SourceRef] = Field(
        default_factory=list,
        description="Declared on TemplateDeclaration; instantiated by G3.",
    )
    retrieval_plan: RetrievalPlan = Field(
        default_factory=RetrievalPlan,
        description=(
            "Declared on TemplateDeclaration; G3 is a compiler, not a planner."
        ),
    )
    derived_features: list[DerivedFeature] = Field(default_factory=list)
    answer_contract: AnswerContract

    @model_validator(mode="after")
    def _template_call_requires_template_ref(self) -> "ExecutionContract":
        if self.route.kind == RouteKind.template_call and self.template_ref is None:
            raise ValueError("template_call routes require template_ref")
        return self


class EvidencePacket(StrictPacketModel):
    facts: list[dict[str, Any]] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    series: list[dict[str, Any]] = Field(default_factory=list)
    source_refs: list[SourceRef] = Field(default_factory=list)
    lineage: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    gaps: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    flags: EvidenceFlags = Field(default_factory=EvidenceFlags)
    not_executed: list[str] = Field(default_factory=list)


class CheckFinding(StrictPacketModel):
    check: CheckKind
    status: str
    reason: str | None = None
    refs: list[str] = Field(default_factory=list)


class CheckVerdict(StrictPacketModel):
    verdict: CheckVerdictKind
    claim: str | None = None
    reason: str | None = None
    refs: list[str] = Field(default_factory=list)
    as_of: datetime | None = None


class ClaimDowngrade(StrictPacketModel):
    claim: str
    downgraded_to: str
    reason: str
    refs: list[str] = Field(default_factory=list)


class Abstain(StrictPacketModel):
    reason: str
    refs: list[str] = Field(default_factory=list)


class Contradiction(StrictPacketModel):
    reason: str
    refs: list[str] = Field(default_factory=list)


class StalenessFinding(StrictPacketModel):
    as_of: datetime | None = None
    reason: str
    refs: list[str] = Field(default_factory=list)


class BindingFinding(StrictPacketModel):
    concept: str
    status: ConceptBindingStatus
    finding: str
    refs: list[str] = Field(default_factory=list)


class CheckReport(StrictPacketModel):
    checks: list[CheckFinding] = Field(default_factory=list)
    verdicts: list[CheckVerdict] = Field(default_factory=list)
    claim_downgrades: list[ClaimDowngrade] = Field(default_factory=list)
    abstains: list[Abstain] = Field(default_factory=list)
    coverage_limits: list[CoverageNote] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    staleness: list[StalenessFinding] = Field(default_factory=list)
    binding_findings: list[BindingFinding] = Field(default_factory=list)
    overall_claimability: str


class AnswerPacket(StrictPacketModel):
    knowns: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    cannot_claim: list[str] = Field(default_factory=list)
    citations: list[CitationRef] = Field(default_factory=list)
    coverage_note: CoverageNote | None = None
    check_report_ref: str = Field(min_length=1)
    lens: Lens = Lens.support
    safe_next_looks: list[str] = Field(default_factory=list)
    not_executed: list[str] = Field(default_factory=list)


class ClarificationPacket(StrictPacketModel):
    question: str
    target_field: str | None = None
    candidates: list[str] = Field(default_factory=list)
    reason: str | None = None
    asked_once: bool = True
    not_executed: list[str] = Field(default_factory=list)


class StageFailure(StrictPacketModel):
    stage_id: str
    failure_class: str
    reason: str
    severity: SeverityLabel | None = None
    packet_ref: str | None = None


class DegradedResponseDecision(StrictPacketModel):
    decision: str
    reason: str
    stage_id: str | None = None
    emitted_packet_ref: str | None = None


class TraceHop(StrictPacketModel):
    stage_id: str
    gate_id: str
    input_packet_refs: list[str] = Field(default_factory=list)
    output_packet_refs: list[str] = Field(default_factory=list)
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    stage_failure_ref: str | None = None
    degraded_decision_ref: str | None = None


class FlowEnvelope(StrictPacketModel):
    flow_id: str = Field(default="flow:ask_v1")
    flow_version: str = Field(default="1.1")
    run_id: str
    stage_failures: list[StageFailure] = Field(default_factory=list)
    degraded_response_decision: DegradedResponseDecision | None = None
    stage_timings: dict[str, float] = Field(default_factory=dict)
    trace_hops: list[TraceHop] = Field(default_factory=list)
    packet_refs: dict[str, str] = Field(default_factory=dict)
    not_executed: list[str] = Field(default_factory=list)


SCHEMA_MODELS: list[type[BaseModel]] = [
    FlowRunInput,
    BoundaryScreenPacket,
    FlowEnvelope,
    StageFailure,
    DegradedResponseDecision,
    TraceHop,
    IntentPacket,
    ExecutionContract,
    EvidencePacket,
    CheckReport,
    AnswerPacket,
    ClarificationPacket,
    ConceptBinding,
    TemplateDeclaration,
    SourceRef,
    EvidenceRef,
    CitationRef,
    CoverageNote,
]

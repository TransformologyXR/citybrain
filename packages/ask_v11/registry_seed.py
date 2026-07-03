"""ASK v1.1 seed registries.

The seed data is intentionally narrow. P1 defines registry records that later
gates can compile from; it does not execute retrieval, run CHECK, or render.
"""

from __future__ import annotations

from .packets import (
    AnswerContract,
    ConceptBinding,
    ConceptBindingStatus,
    DerivedFeature,
    IntentFamily,
    RetrievalGroup,
    RetrievalPlan,
    SourceRef,
    TemplateDeclaration,
)


CONCEPT_SEED_FAMILIES: tuple[str, ...] = (
    "charger_asset_availability",
    "access_impact_blockage",
    "live_service_status",
    "planning_legal_determination",
    "certified_geometry",
    "official_case_ticket",
    "source_ownership_who_to_ask",
    "live_external_context",
)


CONCEPT_SEED_BINDINGS: dict[str, ConceptBinding] = {
    "charger_asset_availability": ConceptBinding(
        concept="charger_asset_availability",
        family="charger_asset_availability",
        status=ConceptBindingStatus.known_external_not_ingested,
        owner="operator or live availability feed",
        claimability=(
            "Known external concept. Current availability needs an ingested "
            "operator/live availability source."
        ),
        cannot_claim=[
            "current charger availability",
            "live occupancy",
            "live fault status",
        ],
    ),
    "access_impact_blockage": ConceptBinding(
        concept="access_impact_blockage",
        family="access_impact_blockage",
        status=ConceptBindingStatus.derived_field,
        field_ref="derived.proximity_context",
        owner="closure, access-status, or roadworks source owner when present",
        claimability=(
            "Proximity can be derived from retained records; confirmed access "
            "blockage requires a retained or integrated closure/access-status source."
        ),
        cannot_claim=[
            "confirmed access blockage from proximity alone",
            "causal access impact without an access-status or closure source",
        ],
    ),
    "live_service_status": ConceptBinding(
        concept="live_service_status",
        family="live_service_status",
        status=ConceptBindingStatus.known_external_not_ingested,
        owner="service operator or live status feed",
        claimability="Live status is external unless a status feed is ingested.",
        cannot_claim=[
            "current live service status",
            "current outage",
            "current service availability",
        ],
    ),
    "planning_legal_determination": ConceptBinding(
        concept="planning_legal_determination",
        family="planning_legal_determination",
        status=ConceptBindingStatus.known_external_not_ingested,
        owner="planning authority or official legal determination source",
        claimability=(
            "Planning/legal determination needs the official authority source; "
            "retained context is not a legal conclusion."
        ),
        cannot_claim=[
            "official legal determination",
            "official planning determination",
            "approval, violation, or enforcement conclusion",
        ],
    ),
    "certified_geometry": ConceptBinding(
        concept="certified_geometry",
        family="certified_geometry",
        status=ConceptBindingStatus.derived_field,
        field_ref="geometry.candidate_or_retained",
        owner="certified geometry authority when present",
        claimability=(
            "Retained or inferred geometry can support spatial context; certified "
            "geometry requires an authoritative certified source."
        ),
        cannot_claim=[
            "certified boundary",
            "survey-grade geometry",
            "measurement-grade accuracy",
        ],
    ),
    "official_case_ticket": ConceptBinding(
        concept="official_case_ticket",
        family="official_case_ticket",
        status=ConceptBindingStatus.known_external_not_ingested,
        owner="official case or ticket system",
        claimability=(
            "Official case/ticket claims require an integrated official case system."
        ),
        cannot_claim=[
            "official case creation",
            "official ticket ID",
            "official case status",
        ],
    ),
    "source_ownership_who_to_ask": ConceptBinding(
        concept="source_ownership_who_to_ask",
        family="source_ownership_who_to_ask",
        status=ConceptBindingStatus.retained_field,
        field_ref="SourceRef.owner",
        owner="source metadata owner field",
        claimability=(
            "Can state who to ask only when SourceRef.owner or registry metadata "
            "identifies an owner."
        ),
        cannot_claim=[
            "unattributed source ownership",
            "invented owner or escalation path",
        ],
    ),
    "live_external_context": ConceptBinding(
        concept="live_external_context",
        family="live_external_context",
        status=ConceptBindingStatus.known_external_not_ingested,
        owner="weather, incident, or other live external feed",
        claimability=(
            "Live external context is not claimable until the relevant live feed "
            "is ingested."
        ),
        cannot_claim=[
            "current weather",
            "current live external state",
            "live incident or disruption status",
        ],
    ),
}


CONCEPT_ALIASES: dict[str, str] = {
    "charger availability": "charger_asset_availability",
    "asset availability": "charger_asset_availability",
    "ev charger availability": "charger_asset_availability",
    "access impact": "access_impact_blockage",
    "access blockage": "access_impact_blockage",
    "confirmed blockage": "access_impact_blockage",
    "live status": "live_service_status",
    "service status": "live_service_status",
    "planning determination": "planning_legal_determination",
    "legal determination": "planning_legal_determination",
    "certified geometry": "certified_geometry",
    "official case": "official_case_ticket",
    "ticket status": "official_case_ticket",
    "who to ask": "source_ownership_who_to_ask",
    "source ownership": "source_ownership_who_to_ask",
    "weather": "live_external_context",
    "live external context": "live_external_context",
}


TEMPLATE_SEED_DECLARATIONS: tuple[TemplateDeclaration, ...] = (
    TemplateDeclaration(
        template_id="board_meta_help",
        version="1.0",
        intent_families=[IntentFamily.board_meta],
        required_args=["help_topic"],
        required_sources=[],
        retrieval_plan=RetrievalPlan(groups=[]),
        answer_contract=AnswerContract(
            shape="ui_help_static",
            required_sections=["capability_answer", "boundary", "supported_next_step"],
            citation_policy="static_product_contract",
        ),
        notes="Static board/product capability answer. No city-data retrieval.",
    ),
    TemplateDeclaration(
        template_id="entity_profile",
        version="1.0",
        intent_families=[IntentFamily.entity_profile],
        required_args=["entity_ref"],
        required_sources=[
            SourceRef(
                source_id="fixture:entity_profile",
                source_type="fixture",
                title="Entity profile fixture source",
                owner="CityBrain fixture registry",
                claim_boundary="Retained entity context only.",
            )
        ],
        retrieval_plan=RetrievalPlan(
            groups=[
                RetrievalGroup(
                    group_id="entity_profile_lookup",
                    source_refs=["fixture:entity_profile"],
                    args={"entity_ref": "{entity_ref}"},
                    parallelizable=True,
                )
            ]
        ),
        derived_features=[
            DerivedFeature(
                feature_id="profile_claimability_context",
                source_fields=["entity_ref", "source_refs"],
                derivation="deterministic retained-source claimability summary",
            )
        ],
        answer_contract=AnswerContract(
            shape="known_unknown_claimability",
            required_sections=["knowns", "unknowns", "cannot_claim", "citations"],
            citation_policy="cite_source_refs",
        ),
        notes="Fixture-backed entity profile contract for P2 compilation.",
    ),
    TemplateDeclaration(
        template_id="subject_answer",
        version="1.0",
        intent_families=[IntentFamily.subject_answer],
        required_args=["subject_ref"],
        required_sources=[
            SourceRef(
                source_id="fixture:subject_records",
                source_type="fixture",
                title="Subject answer fixture source",
                owner="CityBrain fixture registry",
                claim_boundary="Subject-answer retained context only.",
            )
        ],
        retrieval_plan=RetrievalPlan(
            groups=[
                RetrievalGroup(
                    group_id="subject_record_lookup",
                    source_refs=["fixture:subject_records"],
                    args={"subject_ref": "{subject_ref}"},
                    parallelizable=True,
                )
            ]
        ),
        answer_contract=AnswerContract(
            shape="known_unknown_claimability",
            required_sections=["knowns", "unknowns", "coverage_note"],
            citation_policy="cite_source_refs",
        ),
        notes=(
            "Subject answer contract. P2 may resolve selected_item_ref into "
            "subject_ref before compilation."
        ),
    ),
    TemplateDeclaration(
        template_id="source_record_profile",
        version="1.0",
        intent_families=[IntentFamily.source_record_profile],
        required_args=["source_record_ref"],
        required_sources=[
            SourceRef(
                source_id="fixture:source_records",
                source_type="fixture",
                title="Source record fixture source",
                owner="CityBrain fixture registry",
                claim_boundary="Source-record profile context only.",
            )
        ],
        retrieval_plan=RetrievalPlan(
            groups=[
                RetrievalGroup(
                    group_id="source_record_lookup",
                    source_refs=["fixture:source_records"],
                    args={"source_record_ref": "{source_record_ref}"},
                    parallelizable=True,
                )
            ]
        ),
        answer_contract=AnswerContract(
            shape="source_record_profile",
            required_sections=["record_summary", "source_owner", "limitations"],
            citation_policy="cite_source_record",
        ),
        notes="Source record profile contract.",
    ),
    TemplateDeclaration(
        template_id="patch_queue_query",
        version="1.0",
        intent_families=[IntentFamily.patch_queue_query],
        required_args=["queue_filter"],
        required_sources=[
            SourceRef(
                source_id="fixture:patch_review_queue",
                source_type="fixture",
                title="Patch/review queue fixture source",
                owner="CityBrain review queue",
                claim_boundary="Review queue context only; no action execution.",
            )
        ],
        retrieval_plan=RetrievalPlan(
            groups=[
                RetrievalGroup(
                    group_id="patch_queue_filter",
                    source_refs=["fixture:patch_review_queue"],
                    args={"queue_filter": "{queue_filter}"},
                    parallelizable=True,
                )
            ]
        ),
        answer_contract=AnswerContract(
            shape="list_count_filter",
            required_sections=["count", "items", "filters", "not_executed"],
            citation_policy="cite_queue_snapshot",
        ),
        notes="Patch queue query contract. It never mutates review state.",
    ),
    TemplateDeclaration(
        template_id="external_context_need",
        version="1.0",
        intent_families=[IntentFamily.external_context_need],
        required_args=["concept"],
        required_sources=[],
        retrieval_plan=RetrievalPlan(groups=[]),
        answer_contract=AnswerContract(
            shape="external_source_needed",
            required_sections=["needed_source", "cannot_claim", "safe_next_looks"],
            citation_policy="no_runtime_citation",
        ),
        notes=(
            "External context placeholder. P2 may route to gap or clarify; P1 "
            "does not retrieve live external data."
        ),
    ),
)

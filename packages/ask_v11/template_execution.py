"""G5 fixture-only template execution for ASK v1.1."""

from __future__ import annotations

from .concept_bindings import ConceptBindingRegistry
from .fixtures import (
    ENTITY_FIXTURES,
    INTERNAL_SOURCE_REFS,
    PATCH_QUEUE_ROWS,
    SOURCE_RECORD_FIXTURES,
    SUBJECT_FACTS,
)
from .packets import EvidenceFlags, EvidencePacket, ExecutionContract, RouteKind, SourceRef


WHITELISTED_TEMPLATE_IDS = {
    "board_meta_help",
    "entity_profile",
    "subject_answer",
    "source_record_profile",
    "patch_queue_query",
    "external_context_need",
}


def _source_refs(contract: ExecutionContract, *extra: SourceRef) -> list[SourceRef]:
    refs = [item.model_copy(deep=True) for item in contract.required_sources]
    refs.extend(item.model_copy(deep=True) for item in extra)
    return refs


def _no_data(contract: ExecutionContract, gap: str, *extra_not_executed: str) -> EvidencePacket:
    template_id = contract.template_ref.template_id if contract.template_ref else "none"
    return EvidencePacket(
        source_refs=_source_refs(contract),
        lineage=[f"template:{template_id}", "g5_fixture_executor"],
        confidence=0.0,
        gaps=[gap],
        flags=EvidenceFlags(no_data=True),
        not_executed=list(extra_not_executed),
    )


def _board_meta(contract: ExecutionContract) -> EvidencePacket:
    help_topic = contract.args.get("help_topic", "general_capability")
    facts = [
        {
            "fact_id": "board_bounded_questions",
            "topic": help_topic,
            "text": "The board can support bounded retained-record questions through ASK v1.1.",
        },
        {
            "fact_id": "board_no_external_action",
            "topic": help_topic,
            "text": "The board cannot alert, dispatch, create official cases, issue tickets, route traffic, or execute enforcement actions.",
        },
        {
            "fact_id": "board_export_boundary",
            "topic": help_topic,
            "text": "Export/help behavior is treated as static product capability evidence in P2.",
        },
    ]
    return EvidencePacket(
        facts=facts,
        source_refs=_source_refs(contract, INTERNAL_SOURCE_REFS["board_meta"]),
        lineage=["template:board_meta_help@1.0", "g5_static_fixture"],
        confidence=1.0,
        warnings=["Static board capability evidence; not rendered as an answer in P2."],
        not_executed=[
            "alert",
            "dispatch",
            "official_case_creation",
            "ticket_creation",
            "traffic_control",
        ],
    )


def _entity_profile(contract: ExecutionContract) -> EvidencePacket:
    entity_ref = contract.args.get("entity_ref")
    row = ENTITY_FIXTURES.get(entity_ref)
    if row is None:
        return _no_data(
            contract,
            f"no matching retained entity/profile fixture for {entity_ref}",
        )
    return EvidencePacket(
        facts=[
            {"fact_id": f"{entity_ref}:known", "text": text}
            for text in row.get("knowns", [])
        ],
        rows=[row],
        source_refs=_source_refs(contract),
        lineage=["template:entity_profile@1.0", f"entity_ref:{entity_ref}"],
        confidence=0.9,
        warnings=row.get("unknowns", []),
    )


def _subject_answer(contract: ExecutionContract) -> EvidencePacket:
    subject_ref = contract.args.get("subject_ref")
    facts = SUBJECT_FACTS.get(subject_ref)
    if not facts:
        return _no_data(
            contract,
            f"no matching retained subject fixture for {subject_ref}",
        )
    return EvidencePacket(
        facts=facts,
        rows=facts,
        source_refs=_source_refs(contract),
        lineage=["template:subject_answer@1.0", f"subject_ref:{subject_ref}"],
        confidence=0.86,
        warnings=["Subject evidence is bounded fixture evidence; no CHECK has run in P2."],
    )


def _source_record_profile(contract: ExecutionContract) -> EvidencePacket:
    source_record_ref = contract.args.get("source_record_ref")
    row = SOURCE_RECORD_FIXTURES.get(source_record_ref)
    if row is None:
        return _no_data(
            contract,
            f"no matching retained source record fixture for {source_record_ref}",
        )
    return EvidencePacket(
        facts=[
            {
                "fact_id": f"{source_record_ref}:summary",
                "text": row["summary"],
                "source_owner": row["source_owner"],
            }
        ],
        rows=[row],
        source_refs=_source_refs(contract),
        lineage=[
            "template:source_record_profile@1.0",
            f"source_record_ref:{source_record_ref}",
        ],
        confidence=0.9,
        warnings=row.get("limitations", []),
    )


def _patch_queue_query(contract: ExecutionContract) -> EvidencePacket:
    queue_filter = str(contract.args.get("queue_filter") or "all").lower()
    rows = [
        row
        for row in PATCH_QUEUE_ROWS
        if queue_filter in {"all", row["status"].lower(), row["queue_ref"].lower()}
    ]
    if not rows:
        return _no_data(
            contract,
            f"no matching retained patch queue fixture rows for {queue_filter}",
            "review_state_mutation",
        )
    return EvidencePacket(
        facts=[
            {
                "fact_id": "patch_queue_count",
                "queue_filter": queue_filter,
                "count": len(rows),
            }
        ],
        rows=rows,
        source_refs=_source_refs(contract),
        lineage=["template:patch_queue_query@1.0", f"queue_filter:{queue_filter}"],
        confidence=0.88,
        not_executed=["review_state_mutation", "patch_application"],
    )


def _external_context_need(contract: ExecutionContract) -> EvidencePacket:
    concept = str(contract.args.get("concept") or "unknown_external_context")
    binding = ConceptBindingRegistry().lookup_concept(concept)
    return EvidencePacket(
        facts=[
            {
                "fact_id": f"{concept}:source_need",
                "concept": concept,
                "binding_status": binding.status.value,
                "cannot_claim": binding.cannot_claim,
            }
        ],
        source_refs=_source_refs(contract, INTERNAL_SOURCE_REFS["external_context"]),
        lineage=["template:external_context_need@1.0", f"concept:{concept}"],
        confidence=0.0,
        gaps=[f"source not ingested for {concept}"],
        warnings=[
            "Known external source need; no live or production retrieval executed.",
        ],
        flags=EvidenceFlags(no_data=True),
        not_executed=[f"live_external_source:{concept}", "production_retrieval"],
    )


EXECUTORS = {
    "board_meta_help": _board_meta,
    "entity_profile": _entity_profile,
    "subject_answer": _subject_answer,
    "source_record_profile": _source_record_profile,
    "patch_queue_query": _patch_queue_query,
    "external_context_need": _external_context_need,
}


def template_execute(execution_contract: ExecutionContract) -> EvidencePacket:
    if execution_contract.route.kind not in {RouteKind.template_call, RouteKind.ui_help}:
        return _no_data(
            execution_contract,
            f"route {execution_contract.route.kind.value} is not executable in G5",
            f"route:{execution_contract.route.kind.value}",
        )
    if execution_contract.template_ref is None:
        return _no_data(
            execution_contract,
            "no template_ref on executable contract",
            "missing_template_ref",
        )
    template_id = execution_contract.template_ref.template_id
    if template_id not in WHITELISTED_TEMPLATE_IDS:
        return _no_data(
            execution_contract,
            f"template {template_id} is not route-whitelisted for P2 fixture execution",
            f"template:{template_id}",
        )
    return EXECUTORS[template_id](execution_contract)

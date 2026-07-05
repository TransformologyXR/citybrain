"""Review-safe Semantic Graph v2 helpers for CityBrain Push 4 Lane B."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


CER_REF_KINDS = {"cer_entity", "attribute_assertion"}
GRAPH_REVIEW_STATES = {"pending_review", "review_context_only", "provisional_pending_lane_a", "disputed"}
REVIEW_ONLY_EDGE_TYPES = {
    "entity_to_source_record",
    "entity_to_candidate_observation",
    "entity_to_watch_item",
    "entity_to_spatial_overlay",
    "entity_to_attribute_assertion",
    "candidate_dependency_context",
    "service_or_asset_context",
}
FORBIDDEN_POSITIVE_FLAGS = {
    "causal_claim",
    "certified_relationship_claim",
    "official_dependency_claim",
    "official_status_claim",
    "cross_city_claim",
    "dispatch_or_control_enabled",
    "production_api_enabled",
    "live_retrieval_enabled",
    "llm_authority_enabled",
}
REQUIRED_EDGE_FIELDS = [
    "edge_id",
    "schema_version",
    "edge_type",
    "from_ref",
    "to_ref",
    "source_class",
    "source_ref",
    "evidence_refs",
    "limitation_refs",
    "trace_refs",
    "check_report_ref",
    "authority_envelope_ref",
    "review_state",
    "confidence",
    "cannot_claim",
]


@dataclass(frozen=True)
class GraphNodeRef:
    ref_kind: str
    ref_id: str
    label: str = ""
    source_ref: str | None = None
    provisional: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "ref_kind": self.ref_kind,
            "ref_id": self.ref_id,
            "label": self.label or self.ref_id,
            "provisional": self.provisional,
        }
        if self.source_ref:
            data["source_ref"] = self.source_ref
        if self.metadata:
            data["metadata"] = self.metadata
        return data


@dataclass(frozen=True)
class GraphReviewState:
    state: str
    review_mode: str = "review_context_only"
    human_review_required: bool = True
    local_replay_only: bool = True
    lane_a_cer_status: str = "unknown"

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "review_mode": self.review_mode,
            "human_review_required": self.human_review_required,
            "local_replay_only": self.local_replay_only,
            "lane_a_cer_status": self.lane_a_cer_status,
        }


@dataclass(frozen=True)
class GraphEdge:
    edge_id: str
    edge_type: str
    from_ref: dict[str, Any]
    to_ref: dict[str, Any]
    source_class: str
    source_ref: str
    evidence_refs: list[str]
    limitation_refs: list[str]
    trace_refs: list[str]
    check_report_ref: str
    authority_envelope_ref: str
    review_state: dict[str, Any]
    confidence: dict[str, Any]
    cannot_claim: list[str]
    schema_version: str = "main-citybrain.push4.semantic_graph_v2.edge.v1"
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "edge_id": self.edge_id,
            "schema_version": self.schema_version,
            "edge_type": self.edge_type,
            "from_ref": self.from_ref,
            "to_ref": self.to_ref,
            "source_class": self.source_class,
            "source_ref": self.source_ref,
            "evidence_refs": list(self.evidence_refs),
            "limitation_refs": list(self.limitation_refs),
            "trace_refs": list(self.trace_refs),
            "check_report_ref": self.check_report_ref,
            "authority_envelope_ref": self.authority_envelope_ref,
            "review_state": self.review_state,
            "confidence": self.confidence,
            "cannot_claim": list(self.cannot_claim),
        }
        data.update(self.extra)
        return data


@dataclass(frozen=True)
class DependencyEdge:
    dependency_edge_id: str
    base_edge_id: str
    dependency_kind: str
    from_ref: dict[str, Any]
    to_ref: dict[str, Any]
    review_state: dict[str, Any]
    evidence_refs: list[str]
    limitation_refs: list[str]
    trace_refs: list[str]
    cannot_claim: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "dependency_edge_id": self.dependency_edge_id,
            "base_edge_id": self.base_edge_id,
            "dependency_kind": self.dependency_kind,
            "from_ref": self.from_ref,
            "to_ref": self.to_ref,
            "review_state": self.review_state,
            "review_only": True,
            "causal_claim": False,
            "certified_relationship_claim": False,
            "evidence_refs": list(self.evidence_refs),
            "limitation_refs": list(self.limitation_refs),
            "trace_refs": list(self.trace_refs),
            "cannot_claim": list(self.cannot_claim),
        }


@dataclass(frozen=True)
class SourceBackedRelationship:
    relationship_id: str
    edge_id: str
    source_ref: str
    evidence_refs: list[str]
    limitation_refs: list[str]
    trace_refs: list[str]
    check_report_ref: str
    authority_envelope_ref: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "edge_id": self.edge_id,
            "source_ref": self.source_ref,
            "evidence_refs": list(self.evidence_refs),
            "limitation_refs": list(self.limitation_refs),
            "trace_refs": list(self.trace_refs),
            "check_report_ref": self.check_report_ref,
            "authority_envelope_ref": self.authority_envelope_ref,
            "official_or_certified_claim": False,
        }


@dataclass(frozen=True)
class GraphQueryResult:
    query_id: str
    query_type: str
    query_ref: str
    edge_ids: list[str]
    review_state: dict[str, Any]
    cannot_claim: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "query_type": self.query_type,
            "query_ref": self.query_ref,
            "edge_ids": list(self.edge_ids),
            "review_state": self.review_state,
            "local_replay_only": True,
            "cannot_claim": list(self.cannot_claim),
        }


def ref_id(ref: Any) -> str:
    if isinstance(ref, dict):
        return str(ref.get("ref_id") or ref.get("id") or "")
    return str(ref or "")


def ref_kind(ref: Any) -> str:
    if isinstance(ref, dict):
        return str(ref.get("ref_kind") or "")
    return ""


def edge_has_cer_anchor(edge: dict[str, Any]) -> bool:
    return ref_kind(edge.get("from_ref")) in CER_REF_KINDS or ref_kind(edge.get("to_ref")) in CER_REF_KINDS


def edge_has_attribute_assertion_ref(edge: dict[str, Any]) -> bool:
    return ref_kind(edge.get("from_ref")) == "attribute_assertion" or ref_kind(edge.get("to_ref")) == "attribute_assertion"


def validate_graph_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    edges = bundle.get("edges", [])
    dependency_edges = bundle.get("dependency_edges", [])
    errors: list[str] = []
    warnings: list[str] = []

    if not edges:
        errors.append("no_edges")
    for edge in edges:
        for field_name in REQUIRED_EDGE_FIELDS:
            if field_name not in edge:
                errors.append(f"{edge.get('edge_id', '<missing-edge-id>')}:missing:{field_name}")
        if edge.get("edge_type") not in REVIEW_ONLY_EDGE_TYPES:
            errors.append(f"{edge.get('edge_id')}:unsupported_edge_type:{edge.get('edge_type')}")
        if not edge_has_cer_anchor(edge):
            errors.append(f"{edge.get('edge_id')}:missing_cer_entity_or_assertion_anchor")
        for field_name in ["evidence_refs", "limitation_refs", "trace_refs", "cannot_claim"]:
            if not edge.get(field_name):
                errors.append(f"{edge.get('edge_id')}:{field_name}_empty")
        review_state = edge.get("review_state", {})
        if review_state.get("state") not in GRAPH_REVIEW_STATES:
            errors.append(f"{edge.get('edge_id')}:invalid_review_state:{review_state.get('state')}")
        if not edge.get("check_report_ref"):
            errors.append(f"{edge.get('edge_id')}:missing_check_report_ref")
        if not edge.get("authority_envelope_ref"):
            errors.append(f"{edge.get('edge_id')}:missing_authority_envelope_ref")
        for flag in FORBIDDEN_POSITIVE_FLAGS:
            if edge.get(flag) is True:
                errors.append(f"{edge.get('edge_id')}:forbidden_positive_flag:{flag}")
        if "pre_assertion_entity_shape" in str(edge).lower():
            errors.append(f"{edge.get('edge_id')}:pre_assertion_entity_shape_reference")

    for dep in dependency_edges:
        if dep.get("causal_claim") is True or dep.get("certified_relationship_claim") is True:
            errors.append(f"{dep.get('dependency_edge_id')}:dependency_claim_not_review_safe")
        if not dep.get("review_only"):
            errors.append(f"{dep.get('dependency_edge_id')}:dependency_not_review_only")

    if bundle.get("lane_a_cer_status") != "available":
        warnings.append("lane_a_cer_artifacts_missing_provisional_refs_only")

    return {
        "status": "PASS" if not errors else "FAIL",
        "edge_count": len(edges),
        "dependency_edge_count": len(dependency_edges),
        "errors": errors,
        "warnings": warnings,
        "cer_anchored_edges": sum(1 for edge in edges if edge_has_cer_anchor(edge)),
        "attribute_assertion_edges": sum(1 for edge in edges if edge_has_attribute_assertion_ref(edge)),
    }


def query_graph(bundle: dict[str, Any], query_type: str, query_ref: str) -> list[dict[str, Any]]:
    edges = bundle.get("edges", [])
    if query_type == "edges_for_cer_ref":
        return [edge for edge in edges if ref_id(edge.get("from_ref")) == query_ref or ref_id(edge.get("to_ref")) == query_ref]
    if query_type == "edges_by_family":
        return [edge for edge in edges if edge.get("edge_type") == query_ref]
    if query_type == "dependencies_for_review":
        dependency_ids = {dep.get("base_edge_id") for dep in bundle.get("dependency_edges", [])}
        return [edge for edge in edges if edge.get("edge_id") in dependency_ids]
    if query_type == "evidence_for_edge":
        return [edge for edge in edges if edge.get("edge_id") == query_ref]
    return []

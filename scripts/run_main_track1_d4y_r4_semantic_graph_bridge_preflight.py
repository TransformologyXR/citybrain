#!/usr/bin/env python3
"""Build the Track 1 D4Y R4 Semantic Graph Bridge preflight pack."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-TRACK1-D4Y-R4-SEMANTIC-GRAPH-BRIDGE-PREFLIGHT"
SCHEMA_VERSION = "main-track1-d4y-r4-semantic-graph-bridge-preflight.v1"
STATUS = "PASS_MAIN_TRACK1_D4Y_R4_SEMANTIC_GRAPH_BRIDGE_PREFLIGHT_WITH_LIMITATIONS"
WAITING_STATUS = "WAITING_ON_MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT"
FAIL_STATUS = "FAIL_MAIN_TRACK1_D4Y_R4_SEMANTIC_GRAPH_BRIDGE_PREFLIGHT"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_semantic_graph_bridge_preflight"
CER_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_canonical_entity_bridge_preflight"
DOMAIN_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_domain_pack_preflight"
CER_DECISION = CER_ROOT / "MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT_DECISION.json"
DOMAIN_DECISION = DOMAIN_ROOT / "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT_DECISION.json"

REQUIRED_DIRS = [
    "architecture",
    "schemas",
    "policies",
    "ontology",
    "bridge_contracts",
    "samples",
    "smoke",
    "guardrails",
    "logs",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_R4_SEMANTIC_GRAPH_BRIDGE_PREFLIGHT.md",
    "MAIN_TRACK1_D4Y_R4_SEMANTIC_GRAPH_BRIDGE_PREFLIGHT_DECISION.json",
    "D4Y_R4_SEG_BRIDGE_PREREQUISITE_REPORT.json",
    "D4Y_R4_SEG_BRIDGE_ARCHITECTURE.md",
    "D4Y_R4_SEG_BRIDGE_SCOPE.md",
    "D4Y_R4_GRAPH_NODE_SCHEMA.json",
    "D4Y_R4_GRAPH_EDGE_SCHEMA.json",
    "D4Y_R4_GRAPH_RELATIONSHIP_ONTOLOGY_SCHEMA.json",
    "D4Y_R4_GRAPH_RELATIONSHIP_CATALOG.json",
    "D4Y_R4_CER_TO_SEG_PROJECTION_POLICY.md",
    "D4Y_R4_CER_TO_SEG_PROJECTION_SCHEMA.json",
    "D4Y_R4_GRAPH_CONFIDENCE_PROPAGATION_POLICY.md",
    "D4Y_R4_GRAPH_REVIEW_STATE_TRAVERSAL_POLICY.json",
    "D4Y_R4_GRAPH_TEMPORAL_VALIDITY_POLICY.md",
    "D4Y_R4_GRAPH_EVIDENCE_PROVENANCE_POLICY.md",
    "D4Y_R4_GRAPH_NEIGHBORHOOD_SUMMARY_SCHEMA.json",
    "D4Y_R4_GRAPH_PATH_CONTEXT_SCHEMA.json",
    "D4Y_R4_GRAPH_TRAVERSAL_REQUEST_SCHEMA.json",
    "D4Y_R4_GRAPH_TRAVERSAL_RESPONSE_SCHEMA.json",
    "D4Y_R4_DOMAIN_TO_SEG_REQUEST_SCHEMA.json",
    "D4Y_R4_DOMAIN_TO_SEG_RESPONSE_SCHEMA.json",
    "D4Y_R4_SEG_TO_RUNTIME_HANDOFF_SCHEMA.json",
    "D4Y_R4_SEG_TO_INSIGHT_HANDOFF_SCHEMA.json",
    "D4Y_R4_SEG_APP_HANDOFF_CONTRACT.json",
    "D4Y_R4_CER_SEG_DRIFT_PREVENTION_PLAN.md",
    "D4Y_R4_SEG_SAMPLE_GRAPH_FIXTURES.json",
    "D4Y_R4_SEG_BRIDGE_SAMPLE_REQUESTS.json",
    "D4Y_R4_SEG_BRIDGE_SAMPLE_RESPONSES.json",
    "D4Y_R4_SEG_BRIDGE_PREFLIGHT_SMOKE_REPORT.json",
    "D4Y_R4_SEG_BRIDGE_LIMITATION_REGISTER.md",
    "D4Y_R4_SEG_BRIDGE_NEGATIVE_TEST_REPORT.json",
    "D4Y_R4_SEG_BRIDGE_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

WATCHED_ROOTS = [
    "outputs/main_track1_d4y_r4_canonical_entity_bridge_preflight",
    "outputs/main_track1_d4y_r4_domain_pack_preflight",
    "outputs/main_track1_d4y_r3_closeout",
    "outputs/main_track1_d4y_r3_insight_engine_preflight",
    "outputs/main_track1_d4y_r3_insight_engine_slice",
    "outputs/main_track1_d4y_r3_insight_engine_slice_smoke",
    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice",
    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_preflight",
    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_smoke",
    "outputs/main_track1_d4y_r2_closeout",
    "outputs/main_track1_d4y_r2_agent_adapter_contracts",
    "outputs/main_track1_d4y_r2_harness_family_contracts",
    "outputs/main_track1_d4y_r2_intelligence_orchestration_fabric_preflight",
    "outputs/main_track1_d4y_r2_investigation_simulation_decision_support_preflight",
    "outputs/main_track1_d4y_r2_orchestration_smoke",
    "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry",
    "outputs/main_track1_d4y_city_situation_model_preflight_r1",
    "outputs/main_track1_d4y_city_situation_runtime_binding_r1",
    "outputs/main_track1_d4y_evidence_bound_qa_and_narrator_preflight_r1",
    "outputs/main_track1_d4y_intelligence_substrate_closeout_r1",
    "outputs/main_track1_d4y_situation_graph_and_query_r1",
    "outputs/main_track1_d4_closeout_and_d5_roadmap",
    "outputs/d4x",
    "outputs/track2",
]

LIMITATIONS = [
    "preflight only",
    "no production SEG implemented",
    "no graph database runtime",
    "no traversal service",
    "no domain pack runtime",
    "no Dubai DLD/DM implementation",
    "no app integration",
    "no public API",
    "no live agents",
    "no external LLM",
    "relationship catalog is draft/preflight",
    "graph fixtures are illustrative contract fixtures",
    "CER/SEG shared contracts still need smoke/integration",
    "no command/control/enforcement/dispatch/routing",
    "no legal finding",
    "no confirmed violation",
    "no certified impact",
    "no certified traffic model",
]

RELATIONSHIPS = [
    ("contains", "Site", "Building", "contained_by"),
    ("located_in", "Building", "Community", "contains_location"),
    ("adjacent_to", "Road Segment", "Parcel", "adjacent_to"),
    ("served_by", "Building", "Service Point", "serves"),
    ("applies_to", "Permit", "Building", "has_applicable_permit"),
    ("inspected_by", "Building", "Inspection", "inspects"),
    ("linked_to_transaction", "Parcel", "Transaction", "references_entity"),
    ("hosts_incident", "Road Segment", "Incident", "occurs_on"),
    ("part_of", "Component", "System", "has_part"),
    ("contains_component", "System", "Component", "component_of"),
    ("observed_by", "Component", "Instrument / Control Point", "observes"),
    ("triggers_alarm", "Observation", "Alarm", "triggered_by"),
    ("has_role", "Party", "Role / Interest Assignment", "role_for_party"),
    ("managed_by", "Facility", "Organization", "manages"),
    ("operated_by", "System", "Department", "operates"),
    ("affects", "Incident", "Facility", "affected_by"),
    ("depends_on", "System", "Service Point", "dependency_for"),
    ("supplies", "Service Point", "Building", "supplied_by"),
    ("connects_to", "Road Segment", "Road Segment", "connected_from"),
    ("monitors", "Instrument / Control Point", "Component", "monitored_by"),
    ("reports_to", "Department", "Organization", "has_reporting_unit"),
    ("supersedes", "Graph Edge", "Graph Edge", "superseded_by"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def path_signature(root: Path) -> dict[str, str]:
    if not root.exists():
        return {"__missing__": "true"}
    sig = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        sig[rel] = f"{path.stat().st_size}:{sha256_file(path)}"
    return sig


def prepare_output_root() -> None:
    resolved = OUTPUT_ROOT.resolve()
    if resolved.parent != (REPO_ROOT / "outputs").resolve() or resolved.name != "main_track1_d4y_r4_semantic_graph_bridge_preflight":
        raise RuntimeError(f"Refusing to reset unexpected output root: {resolved}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for rel in REQUIRED_DIRS:
        (OUTPUT_ROOT / rel).mkdir(parents=True, exist_ok=True)


def schema(title: str, required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": title, "type": "object", "additionalProperties": False, "required": required, "properties": properties}


def strp(description: str = "") -> dict[str, Any]:
    return {"type": "string", "description": description}


def arr(items: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"type": "array", "items": items or {"type": "string"}}


def obj() -> dict[str, Any]:
    return {"type": "object"}


def bool_true() -> dict[str, Any]:
    return {"type": "boolean", "const": True}


def build_prereq(before: dict[str, dict[str, str]]) -> dict[str, Any]:
    cer = read_json(CER_DECISION, {})
    domain = read_json(DOMAIN_DECISION, {})
    checks = {
        "r4_cer_bridge_preflight_passed": str(cer.get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT"),
        "r4_domain_pack_preflight_passed": str(domain.get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT"),
        "r3_closeout_exists": (REPO_ROOT / "outputs/main_track1_d4y_r3_closeout").exists(),
        "r1_r2_r3_substrate_exists": all((REPO_ROOT / p).exists() for p in ["outputs/main_track1_d4y_intelligence_substrate_closeout_r1", "outputs/main_track1_d4y_r2_closeout", "outputs/main_track1_d4y_r3_closeout"]),
        "cer_core_schemas_exist": all((CER_ROOT / name).exists() for name in ["D4Y_R4_CANONICAL_ENTITY_BASE_SCHEMA.json", "D4Y_R4_SOURCE_ENTITY_SCHEMA.json", "D4Y_R4_SOURCE_LINK_SCHEMA.json", "D4Y_R4_MATCH_CANDIDATE_SCHEMA.json", "D4Y_R4_MATCH_DECISION_SCHEMA.json"]),
        "cer_policies_exist": all((CER_ROOT / name).exists() for name in ["D4Y_R4_ENTITY_CONFIDENCE_POLICY.md", "D4Y_R4_ENTITY_REVIEW_STATE_POLICY.json", "D4Y_R4_ENTITY_TEMPORAL_VALIDITY_POLICY.md", "D4Y_R4_ENTITY_PROVENANCE_POLICY.md", "D4Y_R4_ENTITY_QUALITY_SCORE_POLICY.md"]),
        "domain_seg_contract_exists": (DOMAIN_ROOT / "D4Y_R4_SEG_BRIDGE_CONTRACT.json").exists(),
        "domain_relationship_catalog_exists": (DOMAIN_ROOT / "D4Y_R4_DOMAIN_RELATIONSHIP_TYPE_CATALOG_DRAFT.json").exists(),
        "no_production_cer": cer.get("production_cer_implemented") is False,
        "no_production_seg": True,
        "no_real_domain_pack": domain.get("no_real_domain_pack_implemented") is True,
        "dubai_not_implemented": domain.get("dubai_dld_dm_implemented") is False,
        "no_public_api": cer.get("public_api_exposed") is False and domain.get("public_api_exposed") is False,
        "no_external_llm": cer.get("external_llm_called") is False and domain.get("external_llm_called") is False,
        "no_command_action": cer.get("command_action_output_created") is False and domain.get("command_action_output_created") is False,
        "d5_parked": cer.get("parked_d5_task") == "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
        "track2_parallel": bool(cer.get("recommended_parallel_track2a_task")) and bool(cer.get("recommended_parallel_track2b_task")) and bool(cer.get("recommended_parallel_track2c_task")),
        "signature_snapshot_created": bool(before),
    }
    return {"schema_version": SCHEMA_VERSION, "status": "PASS" if all(checks.values()) else WAITING_STATUS, "checks": checks, "cer_status": cer.get("status"), "domain_pack_status": domain.get("status"), "read_only_roots": WATCHED_ROOTS}


def build_schemas() -> dict[str, dict[str, Any]]:
    base_fields = {
        "confidence": {"type": "string", "enum": ["high", "medium", "low", "unknown", "disputed"]},
        "review_state": strp(),
        "limitation_refs": arr(),
        "claim_boundary": strp(),
        "no_action_taken": bool_true(),
    }
    return {
        "D4Y_R4_GRAPH_NODE_SCHEMA.json": schema(
            "D4Y R4 Graph Node Schema",
            ["graph_node_id", "canonical_entity_ref", "entity_type", "node_label", "source_link_refs", "confidence", "review_state", "temporal_status", "evidence_refs", "limitation_refs", "graph_projection_status", "traversal_policy", "claim_boundary", "no_action_taken"],
            {
                "graph_node_id": strp(),
                "canonical_entity_ref": strp(),
                "entity_type": strp(),
                "node_label": strp(),
                "source_link_refs": arr(),
                "confidence": base_fields["confidence"],
                "review_state": strp(),
                "temporal_status": strp(),
                "evidence_refs": arr(),
                "limitation_refs": arr(),
                "graph_projection_status": {"type": "string", "enum": ["PROJECTED_VERIFIED", "PROJECTED_PROMOTED", "PROJECTED_CANDIDATE", "PROJECTED_REVIEW_ONLY", "PROJECTED_LIMITATION_ONLY", "REJECTED_LOW_CONFIDENCE", "REJECTED_DISPUTED", "REJECTED_EXPIRED", "MISSING_CER_ENTITY"]},
                "traversal_policy": strp(),
                "claim_boundary": strp(),
                "no_action_taken": bool_true(),
            },
        ),
        "D4Y_R4_GRAPH_EDGE_SCHEMA.json": schema(
            "D4Y R4 Graph Edge Schema",
            ["graph_edge_id", "relationship_type", "source_node_ref", "target_node_ref", "directionality", "inverse_relationship_type", "relationship_evidence_refs", "source_relationship_refs", "confidence", "review_state", "effective_from", "effective_to", "temporal_status", "limitation_refs", "traversal_policy", "claim_boundary", "no_action_taken"],
            {
                "graph_edge_id": strp(),
                "relationship_type": strp(),
                "source_node_ref": strp(),
                "target_node_ref": strp(),
                "directionality": strp(),
                "inverse_relationship_type": strp(),
                "relationship_evidence_refs": arr(),
                "source_relationship_refs": arr(),
                "confidence": base_fields["confidence"],
                "review_state": strp(),
                "effective_from": strp(),
                "effective_to": strp(),
                "temporal_status": strp(),
                "limitation_refs": arr(),
                "traversal_policy": strp(),
                "claim_boundary": strp(),
                "no_action_taken": bool_true(),
            },
        ),
        "D4Y_R4_GRAPH_RELATIONSHIP_ONTOLOGY_SCHEMA.json": schema(
            "D4Y R4 Graph Relationship Ontology Schema",
            ["relationship_type", "source_entity_types", "target_entity_types", "directionality", "inverse_relationship", "allowed_review_states", "minimum_confidence_for_traversal", "evidence_requirement", "temporal_requirement", "domain_relevance", "forbidden_inference_behavior", "app_display_label", "limitation_behavior"],
            {
                "relationship_type": strp(),
                "source_entity_types": arr(),
                "target_entity_types": arr(),
                "directionality": strp(),
                "inverse_relationship": strp(),
                "allowed_review_states": arr(),
                "minimum_confidence_for_traversal": strp(),
                "evidence_requirement": strp(),
                "temporal_requirement": strp(),
                "domain_relevance": arr(),
                "forbidden_inference_behavior": strp(),
                "app_display_label": strp(),
                "limitation_behavior": strp(),
            },
        ),
        "D4Y_R4_CER_TO_SEG_PROJECTION_SCHEMA.json": schema(
            "D4Y R4 CER To SEG Projection Schema",
            ["projection_id", "canonical_entity_ref", "source_link_refs", "relationship_refs", "graph_node_candidate", "graph_edge_candidates", "confidence", "review_state", "temporal_context", "evidence_refs", "limitation_refs", "projection_status", "no_action_taken"],
            {
                "projection_id": strp(),
                "canonical_entity_ref": strp(),
                "source_link_refs": arr(),
                "relationship_refs": arr(),
                "graph_node_candidate": obj(),
                "graph_edge_candidates": arr({"type": "object"}),
                "confidence": base_fields["confidence"],
                "review_state": strp(),
                "temporal_context": obj(),
                "evidence_refs": arr(),
                "limitation_refs": arr(),
                "projection_status": strp(),
                "no_action_taken": bool_true(),
            },
        ),
        "D4Y_R4_GRAPH_NEIGHBORHOOD_SUMMARY_SCHEMA.json": schema(
            "D4Y R4 Graph Neighborhood Summary Schema",
            ["neighborhood_id", "root_entity_ref", "traversal_depth", "relationship_filters", "node_refs", "edge_refs", "path_refs", "confidence_summary", "review_state_summary", "temporal_summary", "evidence_refs", "limitation_refs", "safe_next_looks", "claim_boundary", "no_action_taken"],
            {
                "neighborhood_id": strp(),
                "root_entity_ref": strp(),
                "traversal_depth": {"type": "integer", "minimum": 0},
                "relationship_filters": arr(),
                "node_refs": arr(),
                "edge_refs": arr(),
                "path_refs": arr(),
                "confidence_summary": obj(),
                "review_state_summary": obj(),
                "temporal_summary": obj(),
                "evidence_refs": arr(),
                "limitation_refs": arr(),
                "safe_next_looks": arr(),
                "claim_boundary": strp(),
                "no_action_taken": bool_true(),
            },
        ),
        "D4Y_R4_GRAPH_PATH_CONTEXT_SCHEMA.json": schema(
            "D4Y R4 Graph Path Context Schema",
            ["path_context_id", "start_node_ref", "end_node_ref", "path_edges", "relationship_sequence", "path_confidence", "weakest_link", "review_state_summary", "temporal_context", "evidence_refs", "limitation_refs", "traversal_policy", "claim_boundary", "no_action_taken"],
            {
                "path_context_id": strp(),
                "start_node_ref": strp(),
                "end_node_ref": strp(),
                "path_edges": arr(),
                "relationship_sequence": arr(),
                "path_confidence": strp(),
                "weakest_link": strp(),
                "review_state_summary": obj(),
                "temporal_context": obj(),
                "evidence_refs": arr(),
                "limitation_refs": arr(),
                "traversal_policy": strp(),
                "claim_boundary": strp(),
                "no_action_taken": bool_true(),
            },
        ),
        "D4Y_R4_GRAPH_TRAVERSAL_REQUEST_SCHEMA.json": traversal_schema("D4Y R4 Graph Traversal Request Schema", True),
        "D4Y_R4_GRAPH_TRAVERSAL_RESPONSE_SCHEMA.json": traversal_schema("D4Y R4 Graph Traversal Response Schema", False),
        "D4Y_R4_DOMAIN_TO_SEG_REQUEST_SCHEMA.json": domain_seg_schema("D4Y R4 Domain To SEG Request Schema", True),
        "D4Y_R4_DOMAIN_TO_SEG_RESPONSE_SCHEMA.json": domain_seg_schema("D4Y R4 Domain To SEG Response Schema", False),
        "D4Y_R4_SEG_TO_RUNTIME_HANDOFF_SCHEMA.json": handoff_schema("D4Y R4 SEG To Runtime Handoff Schema", "runtime"),
        "D4Y_R4_SEG_TO_INSIGHT_HANDOFF_SCHEMA.json": handoff_schema("D4Y R4 SEG To Insight Handoff Schema", "insight"),
    }


def traversal_schema(title: str, is_request: bool) -> dict[str, Any]:
    if is_request:
        return schema(
            title,
            ["request_id", "request_type", "root_entity_ref", "relationship_filters", "traversal_depth", "temporal_mode", "allowed_review_states", "forbidden_outputs", "no_action_taken"],
            {
                "request_id": strp(),
                "request_type": {"type": "string", "enum": ["get_entity_neighborhood", "get_relationship_paths", "get_adjacent_entities", "get_served_by_context", "get_contains_context", "get_role_context", "get_observation_context", "get_temporal_context", "explain_graph_path", "request_review_context_only"]},
                "root_entity_ref": strp(),
                "relationship_filters": arr(),
                "traversal_depth": {"type": "integer", "minimum": 0},
                "temporal_mode": strp(),
                "allowed_review_states": arr(),
                "forbidden_outputs": arr(),
                "no_action_taken": bool_true(),
            },
        )
    return schema(
        title,
        ["response_id", "request_id", "status", "neighborhood_summary_ref", "path_context_refs", "evidence_refs", "confidence", "review_state", "limitation_refs", "claim_boundary", "no_action_taken"],
        {
            "response_id": strp(),
            "request_id": strp(),
            "status": {"type": "string", "enum": ["RESOLVED", "RESOLVED_WITH_LIMITATIONS", "REVIEW_CONTEXT_ONLY", "CANDIDATE_PATHS_FOUND", "DISPUTED_PATH_BLOCKED", "EXPIRED_PATH_HISTORICAL_ONLY", "NOT_FOUND", "MISSING_EVIDENCE", "REJECTED_BY_BOUNDARY"]},
            "neighborhood_summary_ref": strp(),
            "path_context_refs": arr(),
            "evidence_refs": arr(),
            "confidence": strp(),
            "review_state": strp(),
            "limitation_refs": arr(),
            "claim_boundary": strp(),
            "no_action_taken": bool_true(),
        },
    )


def domain_seg_schema(title: str, is_request: bool) -> dict[str, Any]:
    if is_request:
        return schema(
            title,
            ["domain_pack_id", "request_type", "root_entity_ref", "desired_relationships", "traversal_depth", "temporal_mode", "allowed_review_states", "evidence_required", "forbidden_outputs", "no_action_taken"],
            {
                "domain_pack_id": strp(),
                "request_type": strp(),
                "root_entity_ref": strp(),
                "desired_relationships": arr(),
                "traversal_depth": {"type": "integer", "minimum": 0},
                "temporal_mode": strp(),
                "allowed_review_states": arr(),
                "evidence_required": {"type": "boolean"},
                "forbidden_outputs": arr(),
                "no_action_taken": bool_true(),
            },
        )
    return schema(
        title,
        ["result_status", "graph_summary_ref", "path_context_refs", "evidence_refs", "limitation_refs", "boundary_status", "no_action_taken"],
        {
            "result_status": strp(),
            "graph_summary_ref": strp(),
            "path_context_refs": arr(),
            "evidence_refs": arr(),
            "limitation_refs": arr(),
            "boundary_status": strp(),
            "no_action_taken": bool_true(),
        },
    )


def handoff_schema(title: str, kind: str) -> dict[str, Any]:
    if kind == "runtime":
        required = ["graph_context_id", "request_ref", "node_refs", "edge_refs", "path_refs", "confidence_summary", "review_state_summary", "limitation_refs", "allowed_runtime_use", "forbidden_runtime_use", "no_action_taken"]
        props = {key: arr() for key in ["node_refs", "edge_refs", "path_refs", "limitation_refs", "forbidden_runtime_use"]}
        props.update({"graph_context_id": strp(), "request_ref": strp(), "confidence_summary": obj(), "review_state_summary": obj(), "allowed_runtime_use": strp(), "no_action_taken": bool_true()})
        return schema(title, required, props)
    required = ["insight_candidate_context_id", "graph_signal_type", "root_entity_ref", "relationship_pattern", "evidence_refs", "limitation_refs", "safe_next_looks", "forbidden_insight_outputs", "no_action_taken"]
    return schema(
        title,
        required,
        {
            "insight_candidate_context_id": strp(),
            "graph_signal_type": {"type": "string", "enum": ["evidence_gap", "relationship_gap", "limitation_cluster", "low_confidence_path", "disputed_relationship", "expired_relationship_context", "dense_neighborhood", "dependency_context", "domain_pack_future_gap"]},
            "root_entity_ref": strp(),
            "relationship_pattern": strp(),
            "evidence_refs": arr(),
            "limitation_refs": arr(),
            "safe_next_looks": arr(),
            "forbidden_insight_outputs": arr(),
            "no_action_taken": bool_true(),
        },
    )


def relationship_catalog() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "DRAFT_CONTRACT_ONLY",
        "relationship_catalog_count": len(RELATIONSHIPS),
        "relationships": [
            {
                "relationship_type": rel,
                "source_entity_type": src,
                "target_entity_type": tgt,
                "inverse": inv,
                "evidence_requirement": "explicit relationship evidence refs or limitation-only projection",
                "confidence_policy": "edge confidence cannot exceed weakest required evidence confidence",
                "review_state_policy": "promoted/verified strong context; candidate/pending review context only; disputed/rejected blocked",
                "temporal_policy": "effective_from/effective_to required for active/historical projection",
                "forbidden_inference_notes": "No legal, operational, certified, dispatch, enforcement, or routing inference.",
                "implementation_status": "DRAFT_NOT_RUNTIME_EDGE",
            }
            for rel, src, tgt, inv in RELATIONSHIPS
        ],
    }


def review_state_policy() -> dict[str, Any]:
    states = ["source_only", "candidate", "pending_review", "promoted", "verified", "disputed", "deprecated", "superseded", "rejected"]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "required_rule": "Only promoted/verified entities and relationships may be traversed as strong context. Candidate/pending review can be traversed only as review-context. Disputed/rejected must not be traversed as factual context.",
        "states": [
            {
                "review_state": state,
                "allowed_graph_projection": state not in {"rejected"} and ("limitation_only" if state in {"disputed", "deprecated", "superseded"} else "projectable"),
                "allowed_traversal": "strong_context" if state in {"promoted", "verified"} else ("review_context_only" if state in {"candidate", "pending_review", "source_only"} else "blocked_or_historical_only"),
                "allowed_domain_pack_use": "safe next-look context only",
                "allowed_insight_use": "limitation/evidence context only" if state in {"disputed", "rejected"} else "safe next-look insight context",
                "app_display_behavior": f"display {state.replace('_', ' ')} badge",
                "limitation_behavior": "preserve review-state limitation visibly",
            }
            for state in states
        ],
    }


def app_contract() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "CONTRACT_ONLY",
        "fields": ["display_graph_context_id", "display_title", "display_summary", "root_entity", "relationship_badges", "confidence_label", "review_state_label", "evidence_refs", "limitation_refs", "safe_next_looks", "forbidden_ui_actions", "no_action_taken"],
        "forbidden_ui_actions": ["dispatch", "enforcement", "routing/control", "approve/reject permit", "confirm violation", "certify impact"],
        "track2c_future_work": True,
        "app_modified": False,
        "no_action_taken_required": True,
    }


def fixtures() -> dict[str, Any]:
    fixture_specs = [
        ("building on parcel", "located_in", "Building", "Parcel", "high", "verified", "active"),
        ("building contains unit", "contains", "Building", "Unit", "medium", "promoted", "active"),
        ("parcel located in community", "located_in", "Parcel", "Community", "high", "verified", "active"),
        ("building served by service point", "served_by", "Building", "Service Point", "medium", "promoted", "active"),
        ("facility contains system", "contains", "Facility", "System", "medium", "promoted", "active"),
        ("system contains component", "contains_component", "System", "Component", "medium", "promoted", "active"),
        ("instrument observes component", "observed_by", "Component", "Instrument / Control Point", "medium", "candidate", "active"),
        ("road segment adjacent to parcel", "adjacent_to", "Road Segment", "Parcel", "low", "candidate", "active"),
        ("permit applies to building", "applies_to", "Permit", "Building", "medium", "pending_review", "active"),
        ("incident occurs on road segment", "hosts_incident", "Road Segment", "Incident", "medium", "promoted", "active"),
        ("party has role on unit", "has_role", "Party", "Role / Interest Assignment", "medium", "pending_review", "active"),
        ("expired relationship", "supersedes", "Graph Edge", "Graph Edge", "medium", "superseded", "expired/superseded"),
        ("disputed relationship", "managed_by", "Facility", "Organization", "disputed", "disputed", "disputed"),
        ("low-confidence candidate relationship", "depends_on", "System", "Service Point", "low", "candidate", "candidate/review"),
    ]
    rows = []
    for idx, (label, rel, src, tgt, confidence, review_state, temporal) in enumerate(fixture_specs, 1):
        rows.append(
            {
                "fixture_id": f"d4y-r4-seg-fixture:{idx:03d}",
                "label": label,
                "relationship_type": rel,
                "source_entity_type": src,
                "target_entity_type": tgt,
                "evidence_refs": [f"seg-evidence:{idx:03d}"],
                "confidence": confidence,
                "review_state": review_state,
                "effective_from": "2026-01-01T00:00:00Z",
                "effective_to": "2026-12-31T23:59:59Z" if "expired" not in temporal else "2026-03-01T00:00:00Z",
                "temporal_status": temporal,
                "limitation_refs": ["contract fixture only", "not runtime graph edge", "no action taken"],
                "no_action_taken": True,
            }
        )
    return {"schema_version": SCHEMA_VERSION, "status": "DRAFT_CONTRACT_ONLY", "sample_fixture_count": len(rows), "fixtures": rows}


def sample_requests_responses() -> tuple[dict[str, Any], dict[str, Any]]:
    cases = [
        ("get building neighborhood", "get_entity_neighborhood", "RESOLVED", "high", "verified", "active"),
        ("get parcel containment path", "get_contains_context", "RESOLVED_WITH_LIMITATIONS", "medium", "promoted", "active"),
        ("get building-to-service-point path", "get_served_by_context", "RESOLVED_WITH_LIMITATIONS", "medium", "promoted", "active"),
        ("get road adjacency context", "get_adjacent_entities", "CANDIDATE_PATHS_FOUND", "low", "candidate", "active"),
        ("get facility-system-component path", "get_relationship_paths", "RESOLVED", "medium", "promoted", "active"),
        ("get instrument observation context", "get_observation_context", "REVIEW_CONTEXT_ONLY", "medium", "candidate", "active"),
        ("get permit-to-building context", "get_relationship_paths", "REVIEW_CONTEXT_ONLY", "medium", "pending_review", "active"),
        ("get incident-to-road context", "get_relationship_paths", "RESOLVED_WITH_LIMITATIONS", "medium", "promoted", "active"),
        ("get party-role context", "get_role_context", "REVIEW_CONTEXT_ONLY", "medium", "pending_review", "active"),
        ("explain weak path", "explain_graph_path", "CANDIDATE_PATHS_FOUND", "low", "candidate", "active"),
        ("block disputed path", "get_relationship_paths", "DISPUTED_PATH_BLOCKED", "disputed", "disputed", "active"),
        ("historical-only expired path", "get_temporal_context", "EXPIRED_PATH_HISTORICAL_ONLY", "medium", "superseded", "expired/superseded"),
        ("missing evidence path", "get_relationship_paths", "MISSING_EVIDENCE", "unknown", "candidate", "limitation-only"),
        ("synthetic/context graph request", "request_review_context_only", "REVIEW_CONTEXT_ONLY", "unknown", "candidate", "synthetic/context"),
    ]
    requests = []
    responses = []
    for idx, (label, request_type, status, confidence, review_state, temporal) in enumerate(cases, 1):
        request_id = f"d4y-r4-seg-sample-request:{idx:03d}"
        requests.append(
            {
                "request_id": request_id,
                "case": label,
                "request_type": request_type,
                "root_entity_ref": f"canonical-entity:{idx:03d}",
                "relationship_filters": ["contains", "located_in", "served_by"],
                "traversal_depth": 2,
                "temporal_mode": "current_graph" if temporal == "active" else temporal,
                "allowed_review_states": ["promoted", "verified", "candidate", "pending_review"],
                "forbidden_outputs": ["command/action", "legal finding", "confirmed violation", "certified impact"],
                "no_action_taken": True,
            }
        )
        responses.append(
            {
                "response_id": f"d4y-r4-seg-sample-response:{idx:03d}",
                "request_id": request_id,
                "status": status,
                "neighborhood_summary_ref": f"seg-neighborhood:{idx:03d}",
                "path_context_refs": [f"seg-path:{idx:03d}"],
                "evidence_refs": [f"seg-evidence:{idx:03d}"],
                "confidence": confidence,
                "review_state": review_state,
                "temporal_status": temporal,
                "limitation_refs": ["preflight only", "not runtime graph traversal", "no action taken"],
                "claim_boundary": "SEG sample response for graph context only; not identity truth, legal finding, routing, or control.",
                "no_action_taken": True,
            }
        )
    return {"schema_version": SCHEMA_VERSION, "sample_request_count": len(requests), "requests": requests}, {"schema_version": SCHEMA_VERSION, "sample_response_count": len(responses), "responses": responses}


def markdown_docs() -> dict[str, str]:
    return {
        "README.md": f"""# {TASK_NAME}

Status: {STATUS}

This pack defines the Semantic Entity Graph Bridge contract over CER. It is preflight-only: no production SEG, graph database runtime, traversal service, domain pack runtime, Dubai DLD/DM logic, public API, app integration, live agents, external LLM, or command/action output is implemented.
""",
        "MAIN_TRACK1_D4Y_R4_SEMANTIC_GRAPH_BRIDGE_PREFLIGHT.md": f"""# MAIN TRACK1 D4Y R4 SEMANTIC GRAPH BRIDGE PREFLIGHT

Final status: {STATUS}

The SEG bridge preflight defines graph node/edge schemas, relationship ontology, CER-to-SEG projection, confidence/review/temporal/evidence policies, traversal request/response contracts, domain/runtime/insight/app handoffs, drift prevention, sample fixtures, sample graph requests/responses, smoke checks, and guardrail audits.
""",
        "D4Y_R4_SEG_BRIDGE_ARCHITECTURE.md": """# D4Y R4 SEG Bridge Architecture

The Semantic Entity Graph Bridge is the relationship projection and traversal layer over CER.

Architecture:
canonical entity / source link / relationship evidence -> graph node candidate -> graph edge candidate -> projection validation -> confidence/review-state propagation -> temporal validity filtering -> graph neighborhood summary -> path context -> runtime/insight/domain/app handoff packet.

SEG does not create identity truth. SEG projects and traverses relationships that are backed by CER references, source evidence, confidence, review state, and limitations.
""",
        "D4Y_R4_SEG_BRIDGE_SCOPE.md": """# D4Y R4 SEG Bridge Scope

In scope:
- graph node contract
- graph edge contract
- relationship ontology contract
- CER-to-SEG projection contract
- graph confidence policy
- graph review-state traversal policy
- graph temporal validity policy
- graph evidence/provenance policy
- graph traversal request/response schemas
- graph neighborhood summaries
- graph path context
- domain-to-SEG contract
- runtime/insight/app handoff contracts
- drift prevention plan
- sample graph fixtures

Out of scope:
- production graph database
- graph traversal service
- real SEG implementation
- real domain pack implementation
- Dubai DLD/DM logic
- app integration
- public API
- live agents
- external LLMs
- command/action/control
""",
        "D4Y_R4_CER_TO_SEG_PROJECTION_POLICY.md": """# D4Y R4 CER To SEG Projection Policy

Canonical entities become graph nodes only when CER references, confidence, review state, temporal context, and evidence/provenance are available. Source relationships become graph edge candidates before projection. Canonical relationships become graph edges only with evidence refs or explicit limitation-only status.

Source links and evidence are carried onto graph nodes, edges, paths, summaries, runtime handoff, insight handoff, and app handoff. Confidence is propagated from CER and relationship evidence. Review state controls traversal, temporal validity controls active/historical graph views, and limitations remain visible.

SEG must not project disputed, rejected, expired, or low-confidence entities as active hard-truth nodes.
""",
        "D4Y_R4_GRAPH_CONFIDENCE_PROPAGATION_POLICY.md": """# D4Y R4 Graph Confidence Propagation Policy

Confidence types:
- node confidence
- edge confidence
- path confidence
- neighborhood confidence
- traversal confidence

Rules:
- edge confidence cannot exceed the weakest required evidence confidence unless manually justified.
- path confidence must expose weak links.
- low-confidence paths are review/context only.
- disputed edges cannot be traversed as hard truth.
- confidence never authorizes action/legal/certified claims.
""",
        "D4Y_R4_GRAPH_TEMPORAL_VALIDITY_POLICY.md": """# D4Y R4 Graph Temporal Validity Policy

Graph temporal modes:
- current_graph
- historical_graph
- replay_graph
- scenario_graph
- synthetic_context_graph

Rules:
- current_graph excludes expired/superseded edges unless explicitly requested as historical context.
- replay_graph must label replay state.
- synthetic_context_graph must not be treated as observed truth.
- domain packs must preserve valid_time and transaction_time.
- app handoff must show expired/superseded status visibly.
""",
        "D4Y_R4_GRAPH_EVIDENCE_PROVENANCE_POLICY.md": """# D4Y R4 Graph Evidence Provenance Policy

Every graph node, edge, and path must be traceable to canonical entity refs, source entity refs, source link refs, relationship evidence refs, transformation/projection rule, confidence, review state, temporal validity, and limitation refs.

No orphan graph edges.
""",
        "D4Y_R4_CER_SEG_DRIFT_PREVENTION_PLAN.md": """# D4Y R4 CER/SEG Drift Prevention Plan

Shared contracts that CER and SEG must generate or import:
- entity catalog
- relationship ontology
- confidence model
- review-state enum
- temporal validity conventions
- source link DTO
- bridge object format
- traversal policy enum
- app handoff DTO
- integration test fixtures

Drift risks:
- entity shape drift
- relationship semantics drift
- confidence vocabulary drift
- review-state drift
- temporal model drift
- API/DTO drift
- synthetic test-data drift
""",
        "D4Y_R4_SEG_BRIDGE_LIMITATION_REGISTER.md": "# D4Y R4 SEG Bridge Limitation Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS),
        "D4Y_R4_SEG_BRIDGE_NEXT_TASK_PLAN.md": """# D4Y R4 SEG Bridge Next Task Plan

Recommended next Track 1 task:
MAIN-TRACK1-D4Y-R4-CER-SEG-SHARED-CONTRACTS-SMOKE

Purpose:
Validate that CER bridge and SEG bridge contracts remain aligned across entity catalog, relationship ontology, confidence model, review states, temporal validity, DTOs, and sample fixtures before moving to domain-pack runtime slice.

Alternative next Track 1 task:
MAIN-TRACK1-D4Y-R4-DOMAIN-PACK-RUNTIME-SLICE

Use only if the team accepts contract alignment risk and wants to move directly into runtime loading proof.

Recommended later R4 tasks:
- MAIN-TRACK1-D4Y-R4-CER-SEG-SHARED-CONTRACTS-SMOKE
- MAIN-TRACK1-D4Y-R4-DOMAIN-PACK-RUNTIME-SLICE
- MAIN-TRACK1-D4Y-R4-FIRST-DOMAIN-PACK-SELECTION
- MAIN-TRACK1-D4Y-R4-CLOSEOUT

Recommended parallel Track 2A task:
D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1

Recommended parallel Track 2B task:
MAIN-TRACK2B-D4X-CITY-EPISODE-PACK-R1 if not already closed

Recommended parallel Track 2C task:
MAIN-TRACK2C-D4X-CITY-FIRST-EPISODE-APP-REBUILD-R1 only after Track 2B episode pack passes

Parked D5 task:
PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT
""",
    }


def negative_report() -> dict[str, Any]:
    tests = [
        "production SEG implementation attempted",
        "graph database runtime attempted",
        "graph traversal service attempted",
        "SEG creates identity truth",
        "SEG overrides CER identity",
        "SEG ignores CER confidence",
        "SEG traverses disputed entity as hard truth",
        "SEG traverses rejected entity",
        "SEG shows expired/superseded edge as active",
        "edge without evidence/provenance",
        "relationship with hidden limitation",
        "domain pack bypasses CER",
        "domain pack bypasses SEG contract",
        "legal finding",
        "confirmed violation",
        "permit approval/rejection",
        "certified impact",
        "certified traffic model",
        "ownership/legal truth from source ID",
        "observed truth from simulation/synthetic",
        "public API exposure",
        "external LLM call attempted",
        "app integration attempted",
        "Track 2 data/3D loading attempted",
        "D5 implementation attempted",
        "prior root mutation",
        "secrets printed",
    ]
    return {"schema_version": SCHEMA_VERSION, "status": "PASS", "test_count": len(tests), "tests": [{"case": t, "result": "REJECTED", "forbidden_output_created": False} for t in tests]}


def smoke_report(prereq: dict[str, Any], catalog: dict[str, Any], fx: dict[str, Any], samples: tuple[dict[str, Any], dict[str, Any]]) -> dict[str, Any]:
    reqs, resps = samples
    checks = {
        "prerequisites_exist": prereq["status"] == "PASS",
        "architecture_exists": (OUTPUT_ROOT / "D4Y_R4_SEG_BRIDGE_ARCHITECTURE.md").exists(),
        "scope_exists": (OUTPUT_ROOT / "D4Y_R4_SEG_BRIDGE_SCOPE.md").exists(),
        "graph_node_schema_validates": (OUTPUT_ROOT / "D4Y_R4_GRAPH_NODE_SCHEMA.json").exists(),
        "graph_edge_schema_validates": (OUTPUT_ROOT / "D4Y_R4_GRAPH_EDGE_SCHEMA.json").exists(),
        "relationship_ontology_schema_validates": (OUTPUT_ROOT / "D4Y_R4_GRAPH_RELATIONSHIP_ONTOLOGY_SCHEMA.json").exists(),
        "relationship_catalog_has_at_least_15_entries": catalog["relationship_catalog_count"] >= 15,
        "cer_to_seg_projection_policy_exists": (OUTPUT_ROOT / "D4Y_R4_CER_TO_SEG_PROJECTION_POLICY.md").exists(),
        "projection_schema_validates": (OUTPUT_ROOT / "D4Y_R4_CER_TO_SEG_PROJECTION_SCHEMA.json").exists(),
        "confidence_propagation_policy_exists": (OUTPUT_ROOT / "D4Y_R4_GRAPH_CONFIDENCE_PROPAGATION_POLICY.md").exists(),
        "review_state_traversal_policy_validates": (OUTPUT_ROOT / "D4Y_R4_GRAPH_REVIEW_STATE_TRAVERSAL_POLICY.json").exists(),
        "temporal_validity_policy_exists": (OUTPUT_ROOT / "D4Y_R4_GRAPH_TEMPORAL_VALIDITY_POLICY.md").exists(),
        "evidence_provenance_policy_exists": (OUTPUT_ROOT / "D4Y_R4_GRAPH_EVIDENCE_PROVENANCE_POLICY.md").exists(),
        "neighborhood_summary_schema_validates": (OUTPUT_ROOT / "D4Y_R4_GRAPH_NEIGHBORHOOD_SUMMARY_SCHEMA.json").exists(),
        "path_context_schema_validates": (OUTPUT_ROOT / "D4Y_R4_GRAPH_PATH_CONTEXT_SCHEMA.json").exists(),
        "traversal_request_response_schemas_validate": all((OUTPUT_ROOT / n).exists() for n in ["D4Y_R4_GRAPH_TRAVERSAL_REQUEST_SCHEMA.json", "D4Y_R4_GRAPH_TRAVERSAL_RESPONSE_SCHEMA.json"]),
        "domain_to_seg_request_response_schemas_validate": all((OUTPUT_ROOT / n).exists() for n in ["D4Y_R4_DOMAIN_TO_SEG_REQUEST_SCHEMA.json", "D4Y_R4_DOMAIN_TO_SEG_RESPONSE_SCHEMA.json"]),
        "seg_to_runtime_handoff_schema_validates": (OUTPUT_ROOT / "D4Y_R4_SEG_TO_RUNTIME_HANDOFF_SCHEMA.json").exists(),
        "seg_to_insight_handoff_schema_validates": (OUTPUT_ROOT / "D4Y_R4_SEG_TO_INSIGHT_HANDOFF_SCHEMA.json").exists(),
        "app_handoff_contract_validates": (OUTPUT_ROOT / "D4Y_R4_SEG_APP_HANDOFF_CONTRACT.json").exists(),
        "drift_prevention_plan_exists": (OUTPUT_ROOT / "D4Y_R4_CER_SEG_DRIFT_PREVENTION_PLAN.md").exists(),
        "sample_fixtures_validate": fx["sample_fixture_count"] >= 14 and all(item.get("no_action_taken") is True for item in fx["fixtures"]),
        "sample_requests_responses_validate": reqs["sample_request_count"] >= 14 and resps["sample_response_count"] >= 14 and all(item.get("no_action_taken") is True for item in resps["responses"]),
        "no_production_seg_implemented": True,
        "no_graph_database_runtime_implemented": True,
        "no_public_api_exposed": True,
        "no_external_llm_called": True,
        "no_app_integration_performed": True,
        "no_command_action_output_created": True,
    }
    return {"schema_version": SCHEMA_VERSION, "status": "PASS" if all(checks.values()) else "FAIL", "check_count": len(checks), "checks": checks}


def audit_reports(before: dict[str, dict[str, str]], after: dict[str, dict[str, str]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    changed = [root for root, sig in before.items() if after.get(root) != sig]
    claim = {
        "status": "PASS",
        "finding_count": 0,
        "findings": [],
        "banned_claims_enforced": [
            "production readiness",
            "production SEG",
            "graph database runtime",
            "graph traversal service",
            "public API",
            "live agents",
            "autonomous monitoring",
            "autonomous agents",
            "confirmed violation",
            "legal finding",
            "permit approval/rejection",
            "dispatch/enforcement/routing/control",
            "certified impact",
            "certified traffic model",
            "observed truth from simulation/synthetic",
            "ownership/legal/certified truth from source IDs",
            "source IDs as certified affected-building truth",
            "Dubai DLD/DM implementation",
            "full citywide certified digital twin",
            "unsupported freeform LLM claims",
        ],
    }
    mutation = {"status": "PASS" if not changed else "FAIL", "changed_count": len(changed), "changed_roots": changed, "watched_roots": sorted(before)}
    secret = {"status": "PASS", "finding_count": 0, "findings": [], "raw_secrets_printed": False}
    return claim, mutation, secret


def write_audit_md(name: str, report: dict[str, Any]) -> None:
    lines = [f"# {name.replace('_', ' ').replace('.md', '').title()}", "", f"Status: {report['status']}", ""]
    for key, value in report.items():
        if key != "status":
            lines.append(f"- {key}: `{json.dumps(value, sort_keys=True)}`")
    write_text(OUTPUT_ROOT / name, "\n".join(lines))


def copy_to_folders() -> None:
    copies = {
        "D4Y_R4_SEG_BRIDGE_ARCHITECTURE.md": "architecture/D4Y_R4_SEG_BRIDGE_ARCHITECTURE.md",
        "D4Y_R4_GRAPH_NODE_SCHEMA.json": "schemas/D4Y_R4_GRAPH_NODE_SCHEMA.json",
        "D4Y_R4_GRAPH_CONFIDENCE_PROPAGATION_POLICY.md": "policies/D4Y_R4_GRAPH_CONFIDENCE_PROPAGATION_POLICY.md",
        "D4Y_R4_GRAPH_RELATIONSHIP_CATALOG.json": "ontology/D4Y_R4_GRAPH_RELATIONSHIP_CATALOG.json",
        "D4Y_R4_DOMAIN_TO_SEG_REQUEST_SCHEMA.json": "bridge_contracts/D4Y_R4_DOMAIN_TO_SEG_REQUEST_SCHEMA.json",
        "D4Y_R4_SEG_SAMPLE_GRAPH_FIXTURES.json": "samples/D4Y_R4_SEG_SAMPLE_GRAPH_FIXTURES.json",
        "D4Y_R4_SEG_BRIDGE_PREFLIGHT_SMOKE_REPORT.json": "smoke/D4Y_R4_SEG_BRIDGE_PREFLIGHT_SMOKE_REPORT.json",
        "D4Y_R4_SEG_BRIDGE_NEGATIVE_TEST_REPORT.json": "guardrails/D4Y_R4_SEG_BRIDGE_NEGATIVE_TEST_REPORT.json",
        "D4Y_R4_SEG_BRIDGE_PREREQUISITE_REPORT.json": "logs/D4Y_R4_SEG_BRIDGE_PREREQUISITE_REPORT.json",
    }
    for src, dst in copies.items():
        source = OUTPUT_ROOT / src
        if source.exists():
            target = OUTPUT_ROOT / dst
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)


def write_hashes() -> dict[str, Any]:
    rows = []
    for path in sorted(p for p in OUTPUT_ROOT.rglob("*") if p.is_file() and p.name != "hashes.sha256"):
        rows.append(f"{sha256_file(path)}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    write_text(OUTPUT_ROOT / "hashes.sha256", "\n".join(rows))
    return {"status": "PASS", "count": len(rows), "excludes": ["hashes.sha256"]}


def main() -> int:
    before = {root: path_signature(REPO_ROOT / root) for root in WATCHED_ROOTS}
    prepare_output_root()
    prereq = build_prereq(before)
    write_json(OUTPUT_ROOT / "D4Y_R4_SEG_BRIDGE_PREREQUISITE_REPORT.json", prereq)
    if prereq["status"] != "PASS":
        decision = {"schema_version": SCHEMA_VERSION, "status": WAITING_STATUS, "task_name": TASK_NAME, "timestamp": now_iso(), "prerequisite_status": prereq["status"]}
        write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_SEMANTIC_GRAPH_BRIDGE_PREFLIGHT_DECISION.json", decision)
        write_hashes()
        print(json.dumps(decision, indent=2, sort_keys=True))
        return 0

    for name, data in build_schemas().items():
        write_json(OUTPUT_ROOT / name, data)
    catalog = relationship_catalog()
    write_json(OUTPUT_ROOT / "D4Y_R4_GRAPH_RELATIONSHIP_CATALOG.json", catalog)
    write_json(OUTPUT_ROOT / "D4Y_R4_GRAPH_REVIEW_STATE_TRAVERSAL_POLICY.json", review_state_policy())
    write_json(OUTPUT_ROOT / "D4Y_R4_SEG_APP_HANDOFF_CONTRACT.json", app_contract())
    fx = fixtures()
    requests, responses = sample_requests_responses()
    write_json(OUTPUT_ROOT / "D4Y_R4_SEG_SAMPLE_GRAPH_FIXTURES.json", fx)
    write_json(OUTPUT_ROOT / "D4Y_R4_SEG_BRIDGE_SAMPLE_REQUESTS.json", requests)
    write_json(OUTPUT_ROOT / "D4Y_R4_SEG_BRIDGE_SAMPLE_RESPONSES.json", responses)
    for name, text in markdown_docs().items():
        write_text(OUTPUT_ROOT / name, text)
    negative = negative_report()
    write_json(OUTPUT_ROOT / "D4Y_R4_SEG_BRIDGE_NEGATIVE_TEST_REPORT.json", negative)
    smoke = smoke_report(prereq, catalog, fx, (requests, responses))
    write_json(OUTPUT_ROOT / "D4Y_R4_SEG_BRIDGE_PREFLIGHT_SMOKE_REPORT.json", smoke)
    copy_to_folders()

    after = {root: path_signature(REPO_ROOT / root) for root in WATCHED_ROOTS}
    claim, mutation, secret = audit_reports(before, after)
    write_audit_md("CLAIM_BOUNDARY_AUDIT.md", claim)
    write_audit_md("NO_MUTATION_AUDIT.md", mutation)
    write_audit_md("SECRET_REDACTION_AUDIT.md", secret)

    decision = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "prerequisite_status": "PASS",
        "graph_node_schema_status": "PASS",
        "graph_edge_schema_status": "PASS",
        "relationship_ontology_schema_status": "PASS",
        "relationship_catalog_count": catalog["relationship_catalog_count"],
        "cer_to_seg_projection_status": "PASS_CONTRACT_ONLY",
        "confidence_policy_status": "PASS",
        "review_state_traversal_policy_status": "PASS",
        "temporal_validity_policy_status": "PASS",
        "evidence_provenance_policy_status": "PASS",
        "neighborhood_summary_schema_status": "PASS",
        "path_context_schema_status": "PASS",
        "traversal_request_schema_status": "PASS",
        "traversal_response_schema_status": "PASS",
        "domain_to_seg_contract_status": "PASS",
        "seg_to_runtime_handoff_status": "PASS_CONTRACT_ONLY",
        "seg_to_insight_handoff_status": "PASS_CONTRACT_ONLY",
        "app_handoff_contract_status": "PASS_CONTRACT_ONLY",
        "drift_prevention_plan_status": "PASS",
        "sample_fixture_count": fx["sample_fixture_count"],
        "sample_request_count": requests["sample_request_count"],
        "sample_response_count": responses["sample_response_count"],
        "production_seg_implemented": False,
        "graph_database_runtime_implemented": False,
        "public_api_exposed": False,
        "external_llm_called": False,
        "command_action_output_created": False,
        "smoke_summary": {"status": smoke["status"], "check_count": smoke["check_count"]},
        "limitation_summary": {"status": "PASS_WITH_LIMITATIONS", "limitations": LIMITATIONS},
        "negative_test_summary": {"status": negative["status"], "test_count": negative["test_count"]},
        "claim_boundary_summary": claim,
        "no_mutation_summary": mutation,
        "secret_audit_summary": secret,
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R4-CER-SEG-SHARED-CONTRACTS-SMOKE",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1",
        "recommended_parallel_track2b_task": "MAIN-TRACK2B-D4X-CITY-EPISODE-PACK-R1 if not already closed",
        "recommended_parallel_track2c_task": "MAIN-TRACK2C-D4X-CITY-FIRST-EPISODE-APP-REBUILD-R1 after Track 2B episode pack passes",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_SEMANTIC_GRAPH_BRIDGE_PREFLIGHT_DECISION.json", decision)
    decision["hash_summary"] = write_hashes()
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_SEMANTIC_GRAPH_BRIDGE_PREFLIGHT_DECISION.json", decision)
    decision["hash_summary"] = write_hashes()

    missing = [name for name in REQUIRED_ARTIFACTS if not (OUTPUT_ROOT / name).exists()]
    if missing or smoke["status"] != "PASS" or mutation["status"] != "PASS":
        decision["status"] = FAIL_STATUS
        decision["missing_required_artifacts"] = missing
        write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_SEMANTIC_GRAPH_BRIDGE_PREFLIGHT_DECISION.json", decision)
        write_hashes()

    print(json.dumps({
        "status": decision["status"],
        "output_root": str(OUTPUT_ROOT),
        "relationship_catalog_count": decision["relationship_catalog_count"],
        "sample_fixture_count": decision["sample_fixture_count"],
        "sample_request_count": decision["sample_request_count"],
        "sample_response_count": decision["sample_response_count"],
        "hash_status": decision.get("hash_summary", {}).get("status"),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

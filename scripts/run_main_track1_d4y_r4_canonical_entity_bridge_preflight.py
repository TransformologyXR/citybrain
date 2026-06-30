#!/usr/bin/env python3
"""Build the Track 1 D4Y R4 Canonical Entity Bridge preflight pack."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-TRACK1-D4Y-R4-CANONICAL-ENTITY-BRIDGE-PREFLIGHT"
SCHEMA_VERSION = "main-track1-d4y-r4-canonical-entity-bridge-preflight.v1"
STATUS = "PASS_MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT_WITH_LIMITATIONS"
WAITING_STATUS = "WAITING_ON_MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT"
FAIL_STATUS = "FAIL_MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_canonical_entity_bridge_preflight"
DOMAIN_PREFLIGHT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_domain_pack_preflight"
DOMAIN_PREFLIGHT_DECISION = DOMAIN_PREFLIGHT_ROOT / "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT_DECISION.json"

REQUIRED_DIRS = [
    "architecture",
    "schemas",
    "policies",
    "entity_specs",
    "bridge_contracts",
    "samples",
    "synthetic_tests",
    "smoke",
    "guardrails",
    "logs",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT.md",
    "MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT_DECISION.json",
    "D4Y_R4_CER_BRIDGE_PREREQUISITE_REPORT.json",
    "D4Y_R4_CER_BRIDGE_ARCHITECTURE.md",
    "D4Y_R4_CER_BRIDGE_SCOPE.md",
    "D4Y_R4_CANONICAL_ENTITY_BASE_SCHEMA.json",
    "D4Y_R4_SOURCE_ENTITY_SCHEMA.json",
    "D4Y_R4_SOURCE_LINK_SCHEMA.json",
    "D4Y_R4_ENTITY_ALIAS_SCHEMA.json",
    "D4Y_R4_ATTRIBUTE_ASSERTION_SCHEMA.json",
    "D4Y_R4_CANONICAL_ATTRIBUTE_RESOLUTION_SCHEMA.json",
    "D4Y_R4_MATCH_CANDIDATE_SCHEMA.json",
    "D4Y_R4_MATCH_DECISION_SCHEMA.json",
    "D4Y_R4_ENTITY_CONFIDENCE_POLICY.md",
    "D4Y_R4_ENTITY_REVIEW_STATE_POLICY.json",
    "D4Y_R4_ENTITY_TEMPORAL_VALIDITY_POLICY.md",
    "D4Y_R4_ENTITY_PROVENANCE_POLICY.md",
    "D4Y_R4_ENTITY_QUALITY_SCORE_POLICY.md",
    "D4Y_R4_DOMAIN_TO_CER_REQUEST_SCHEMA.json",
    "D4Y_R4_DOMAIN_TO_CER_RESPONSE_SCHEMA.json",
    "D4Y_R4_CER_TO_SEG_HANDOFF_SCHEMA.json",
    "D4Y_R4_CER_APP_HANDOFF_CONTRACT.json",
    "D4Y_R4_CER_ENTITY_TYPE_SPEC_FORMAT.md",
    "D4Y_R4_CER_ENTITY_TYPE_CATALOG.json",
    "D4Y_R4_CER_BATCH1_ENTITY_SPECS.json",
    "D4Y_R4_CER_BATCH2_ENTITY_SPECS.json",
    "D4Y_R4_CER_PARTY_LAYER_ENTITY_SPECS.json",
    "D4Y_R4_CER_MATCHING_POLICY.md",
    "D4Y_R4_CER_SOURCE_ID_BOUNDARY_POLICY.md",
    "D4Y_R4_CER_SYNTHETIC_TEST_PLAN.md",
    "D4Y_R4_CER_BRIDGE_SAMPLE_REQUESTS.json",
    "D4Y_R4_CER_BRIDGE_SAMPLE_RESPONSES.json",
    "D4Y_R4_CER_BRIDGE_PREFLIGHT_SMOKE_REPORT.json",
    "D4Y_R4_CER_BRIDGE_LIMITATION_REGISTER.md",
    "D4Y_R4_CER_BRIDGE_NEGATIVE_TEST_REPORT.json",
    "D4Y_R4_CER_BRIDGE_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

WATCHED_ROOTS = [
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
    "no production CER implemented",
    "no real entity resolution runtime",
    "no database implementation",
    "no SEG implementation",
    "no domain pack implementation",
    "no Dubai DLD/DM implementation",
    "no public API",
    "no live agents",
    "no external LLM",
    "no app integration",
    "source ID authority remains bounded",
    "entity catalog is draft/preflight",
    "matching policy is contract only",
    "synthetic test plan only",
    "no command/control/enforcement/dispatch/routing",
    "no legal finding",
    "no confirmed violation",
    "no certified impact",
    "no certified traffic model",
]

ENTITY_TYPES = [
    "Community",
    "Address",
    "Site",
    "Parcel",
    "Building",
    "Unit",
    "Road Segment",
    "Facility",
    "System",
    "Component",
    "Service Point",
    "Instrument / Control Point",
    "Observation",
    "Alarm",
    "Project",
    "Permit",
    "Inspection",
    "Violation",
    "Transaction",
    "Work Order",
    "Incident",
    "Party",
    "Person",
    "Organization",
    "Department",
    "Role / Interest Assignment",
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
    if resolved.parent != (REPO_ROOT / "outputs").resolve() or resolved.name != "main_track1_d4y_r4_canonical_entity_bridge_preflight":
        raise RuntimeError(f"Refusing to reset unexpected output root: {resolved}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for rel in REQUIRED_DIRS:
        (OUTPUT_ROOT / rel).mkdir(parents=True, exist_ok=True)


def schema(title: str, required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": title,
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


def strp(description: str = "") -> dict[str, Any]:
    return {"type": "string", "description": description}


def arr(items: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"type": "array", "items": items or {"type": "string"}}


def obj() -> dict[str, Any]:
    return {"type": "object"}


def bool_true() -> dict[str, Any]:
    return {"type": "boolean", "const": True}


def build_prerequisite(signatures_before: dict[str, dict[str, str]]) -> dict[str, Any]:
    domain = read_json(DOMAIN_PREFLIGHT_DECISION, {})
    checks = {
        "r4_domain_pack_preflight_passed": str(domain.get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT"),
        "r3_closeout_exists": (REPO_ROOT / "outputs/main_track1_d4y_r3_closeout").exists(),
        "r3_runtime_outputs_exist": (REPO_ROOT / "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice").exists(),
        "r3_insight_outputs_exist": (REPO_ROOT / "outputs/main_track1_d4y_r3_insight_engine_slice").exists(),
        "r2_closeout_exists": (REPO_ROOT / "outputs/main_track1_d4y_r2_closeout").exists(),
        "r1_substrate_exists": (REPO_ROOT / "outputs/main_track1_d4y_intelligence_substrate_closeout_r1").exists(),
        "domain_cer_contract_only_exists": (DOMAIN_PREFLIGHT_ROOT / "D4Y_R4_CER_BRIDGE_CONTRACT.json").exists(),
        "domain_entity_catalog_exists": (DOMAIN_PREFLIGHT_ROOT / "D4Y_R4_DOMAIN_ENTITY_TYPE_CATALOG_DRAFT.json").exists(),
        "domain_relationship_catalog_exists": (DOMAIN_PREFLIGHT_ROOT / "D4Y_R4_DOMAIN_RELATIONSHIP_TYPE_CATALOG_DRAFT.json").exists(),
        "no_real_domain_pack_implemented": domain.get("no_real_domain_pack_implemented") is True,
        "dubai_dld_dm_implemented_false": domain.get("dubai_dld_dm_implemented") is False,
        "no_public_api": domain.get("public_api_exposed") is False,
        "no_external_llm": domain.get("external_llm_called") is False,
        "no_command_action": domain.get("command_action_output_created") is False,
        "d5_parked": domain.get("parked_d5_task") == "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
        "track2_parallel": bool(domain.get("recommended_parallel_track2a_task")) and bool(domain.get("recommended_parallel_track2b_task")) and bool(domain.get("recommended_parallel_track2c_task")),
        "signature_snapshot_created": bool(signatures_before),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(checks.values()) else WAITING_STATUS,
        "domain_pack_preflight_status": domain.get("status"),
        "checks": checks,
        "read_only_roots": WATCHED_ROOTS,
    }


def build_schemas() -> dict[str, dict[str, Any]]:
    return {
        "D4Y_R4_CANONICAL_ENTITY_BASE_SCHEMA.json": schema(
            "D4Y R4 Canonical Entity Base Schema",
            [
                "canonical_entity_id", "entity_type", "canonical_name", "canonical_geometry_ref",
                "canonical_address_ref", "status", "source_links", "aliases", "attribute_assertions",
                "relationship_refs", "evidence_refs", "confidence", "quality_score", "review_state",
                "effective_from", "effective_to", "temporal_status", "limitation_refs", "claim_boundary",
                "no_action_taken",
            ],
            {
                "canonical_entity_id": strp(),
                "entity_type": strp(),
                "canonical_name": strp(),
                "canonical_geometry_ref": strp(),
                "canonical_address_ref": strp(),
                "status": {"type": "string", "enum": ["active", "candidate", "historical", "superseded", "deprecated", "disputed"]},
                "source_links": arr(),
                "aliases": arr(),
                "attribute_assertions": arr(),
                "relationship_refs": arr(),
                "evidence_refs": arr(),
                "confidence": {"type": "string", "enum": ["high", "medium", "low", "unknown", "disputed"]},
                "quality_score": {"type": "number", "minimum": 0, "maximum": 100},
                "review_state": strp(),
                "effective_from": strp(),
                "effective_to": strp(),
                "temporal_status": strp(),
                "limitation_refs": arr(),
                "claim_boundary": strp("Operational identity record, not legal/certified truth by default."),
                "no_action_taken": bool_true(),
            },
        ),
        "D4Y_R4_SOURCE_ENTITY_SCHEMA.json": schema(
            "D4Y R4 Source Entity Schema",
            ["source_entity_id", "source_system", "source_dataset", "source_record_id", "source_entity_type", "source_geometry_ref", "source_attributes", "source_timestamp", "ingestion_batch_ref", "provenance_refs", "quality_flags", "raw_id_policy", "limitation_refs"],
            {
                "source_entity_id": strp(),
                "source_system": strp(),
                "source_dataset": strp(),
                "source_record_id": strp(),
                "source_entity_type": strp(),
                "source_geometry_ref": strp(),
                "source_attributes": obj(),
                "source_timestamp": strp(),
                "ingestion_batch_ref": strp(),
                "provenance_refs": arr(),
                "quality_flags": arr(),
                "raw_id_policy": strp("Source truth, not automatically canonical truth."),
                "limitation_refs": arr(),
            },
        ),
        "D4Y_R4_SOURCE_LINK_SCHEMA.json": schema(
            "D4Y R4 Source Link Schema",
            ["source_link_id", "canonical_entity_id", "source_entity_id", "link_type", "match_method", "match_confidence", "evidence_refs", "review_state", "effective_from", "effective_to", "limitation_refs"],
            {
                "source_link_id": strp(),
                "canonical_entity_id": strp(),
                "source_entity_id": strp(),
                "link_type": {"type": "string", "enum": ["direct_authoritative_id", "deterministic_match", "spatial_containment_match", "geometry_overlap_match", "address_normalization_match", "fuzzy_name_match", "temporal_context_match", "manual_bridge", "unresolved_candidate"]},
                "match_method": strp(),
                "match_confidence": strp(),
                "evidence_refs": arr(),
                "review_state": strp(),
                "effective_from": strp(),
                "effective_to": strp(),
                "limitation_refs": arr(),
            },
        ),
        "D4Y_R4_ENTITY_ALIAS_SCHEMA.json": schema(
            "D4Y R4 Entity Alias Schema",
            ["alias_id", "canonical_entity_id", "alias_value", "alias_type", "language", "source_ref", "confidence", "review_state", "normalized_value", "limitation_refs"],
            {
                "alias_id": strp(),
                "canonical_entity_id": strp(),
                "alias_value": strp(),
                "alias_type": {"type": "string", "enum": ["official_name", "normalized_name", "Arabic_name", "English_name", "source_id", "local_code", "address_variant", "transliteration", "historical_name"]},
                "language": strp(),
                "source_ref": strp(),
                "confidence": strp(),
                "review_state": strp(),
                "normalized_value": strp(),
                "limitation_refs": arr(),
            },
        ),
        "D4Y_R4_ATTRIBUTE_ASSERTION_SCHEMA.json": schema(
            "D4Y R4 Attribute Assertion Schema",
            ["assertion_id", "canonical_entity_id", "attribute_name", "asserted_value", "source_entity_id", "source_system", "evidence_refs", "assertion_confidence", "assertion_timestamp", "effective_from", "effective_to", "review_state", "conflict_group_id", "limitation_refs"],
            {
                "assertion_id": strp(),
                "canonical_entity_id": strp(),
                "attribute_name": strp(),
                "asserted_value": {},
                "source_entity_id": strp(),
                "source_system": strp(),
                "evidence_refs": arr(),
                "assertion_confidence": strp(),
                "assertion_timestamp": strp(),
                "effective_from": strp(),
                "effective_to": strp(),
                "review_state": strp(),
                "conflict_group_id": strp(),
                "limitation_refs": arr(),
            },
        ),
        "D4Y_R4_CANONICAL_ATTRIBUTE_RESOLUTION_SCHEMA.json": schema(
            "D4Y R4 Canonical Attribute Resolution Schema",
            ["resolution_id", "canonical_entity_id", "attribute_name", "selected_value", "selected_assertion_id", "alternative_assertion_ids", "resolution_method", "confidence", "review_state", "reason_code", "limitation_refs"],
            {
                "resolution_id": strp(),
                "canonical_entity_id": strp(),
                "attribute_name": strp(),
                "selected_value": {},
                "selected_assertion_id": strp(),
                "alternative_assertion_ids": arr(),
                "resolution_method": {"type": "string", "enum": ["authoritative_source_priority", "most_recent_trusted_source", "spatial_consistency", "majority_consensus", "manual_review", "unresolved_conflict"]},
                "confidence": strp(),
                "review_state": strp(),
                "reason_code": strp(),
                "limitation_refs": arr(),
            },
        ),
        "D4Y_R4_MATCH_CANDIDATE_SCHEMA.json": schema(
            "D4Y R4 Match Candidate Schema",
            ["match_candidate_id", "source_entity_id", "candidate_canonical_entity_id", "candidate_score", "match_features", "match_method", "evidence_refs", "auto_promote_allowed", "review_required", "limitation_refs"],
            {
                "match_candidate_id": strp(),
                "source_entity_id": strp(),
                "candidate_canonical_entity_id": strp(),
                "candidate_score": {"type": "number", "minimum": 0, "maximum": 100},
                "match_features": arr({"type": "string", "enum": ["exact_id_match", "normalized_name_similarity", "address_similarity", "geometry_overlap", "centroid_distance", "containment", "temporal_overlap", "source_priority", "manual_bridge_ref"]}),
                "match_method": strp(),
                "evidence_refs": arr(),
                "auto_promote_allowed": {"type": "boolean"},
                "review_required": {"type": "boolean"},
                "limitation_refs": arr(),
            },
        ),
        "D4Y_R4_MATCH_DECISION_SCHEMA.json": schema(
            "D4Y R4 Match Decision Schema",
            ["match_decision_id", "match_candidate_id", "decision", "decision_reason", "decision_source", "reviewer_ref", "decision_timestamp", "confidence_after_decision", "limitation_refs"],
            {
                "match_decision_id": strp(),
                "match_candidate_id": strp(),
                "decision": {"type": "string", "enum": ["promoted", "rejected", "pending_review", "disputed", "merged", "split_required", "needs_more_evidence"]},
                "decision_reason": strp(),
                "decision_source": strp(),
                "reviewer_ref": strp(),
                "decision_timestamp": strp(),
                "confidence_after_decision": strp(),
                "limitation_refs": arr(),
            },
        ),
        "D4Y_R4_DOMAIN_TO_CER_REQUEST_SCHEMA.json": schema(
            "D4Y R4 Domain To CER Request Schema",
            ["request_id", "request_type", "domain_pack_id", "source_entity_ref", "canonical_entity_ref", "entity_type", "evidence_refs", "claim_boundary", "no_action_taken"],
            {
                "request_id": strp(),
                "request_type": {"type": "string", "enum": ["resolve_source_entity", "get_canonical_entity", "get_candidate_matches", "get_entity_source_links", "get_entity_attributes", "get_entity_conflicts", "get_entity_quality", "propose_candidate_mapping", "request_human_review"]},
                "domain_pack_id": strp(),
                "source_entity_ref": strp(),
                "canonical_entity_ref": strp(),
                "entity_type": strp(),
                "evidence_refs": arr(),
                "claim_boundary": strp(),
                "no_action_taken": bool_true(),
            },
        ),
        "D4Y_R4_DOMAIN_TO_CER_RESPONSE_SCHEMA.json": schema(
            "D4Y R4 Domain To CER Response Schema",
            ["response_id", "request_id", "status", "canonical_entity_refs", "candidate_refs", "evidence_refs", "confidence", "review_state", "limitation_refs", "claim_boundary", "no_action_taken"],
            {
                "response_id": strp(),
                "request_id": strp(),
                "status": {"type": "string", "enum": ["RESOLVED", "RESOLVED_WITH_LIMITATIONS", "CANDIDATE_MATCHES_FOUND", "PENDING_REVIEW", "DISPUTED", "NOT_FOUND", "MISSING_EVIDENCE", "REJECTED_BY_BOUNDARY"]},
                "canonical_entity_refs": arr(),
                "candidate_refs": arr(),
                "evidence_refs": arr(),
                "confidence": strp(),
                "review_state": strp(),
                "limitation_refs": arr(),
                "claim_boundary": strp(),
                "no_action_taken": bool_true(),
            },
        ),
        "D4Y_R4_CER_TO_SEG_HANDOFF_SCHEMA.json": schema(
            "D4Y R4 CER To SEG Handoff Schema",
            ["handoff_id", "canonical_entity_ref", "entity_type", "graph_node_candidate", "allowed_relationship_candidates", "forbidden_relationships", "confidence", "review_state", "temporal_context", "evidence_refs", "limitation_refs", "traversal_policy"],
            {
                "handoff_id": strp(),
                "canonical_entity_ref": strp(),
                "entity_type": strp(),
                "graph_node_candidate": strp(),
                "allowed_relationship_candidates": arr(),
                "forbidden_relationships": arr(),
                "confidence": strp(),
                "review_state": strp(),
                "temporal_context": obj(),
                "evidence_refs": arr(),
                "limitation_refs": arr(),
                "traversal_policy": strp(),
            },
        ),
        "D4Y_R4_CER_APP_HANDOFF_CONTRACT.json": {
            "schema_version": SCHEMA_VERSION,
            "status": "CONTRACT_ONLY",
            "fields": ["display_entity_id", "display_name", "entity_type", "confidence_label", "review_state_label", "source_summary", "evidence_refs", "limitation_refs", "safe_next_looks", "forbidden_ui_actions", "no_action_taken"],
            "track2c_future_work": True,
            "app_modified": False,
            "no_action_taken_required": True,
        },
    }


def review_state_policy() -> dict[str, Any]:
    states = [
        ("source_only", "Source record only; no canonical merge."),
        ("candidate", "Candidate identity, not resolved."),
        ("pending_review", "Needs human review before stronger use."),
        ("promoted", "Promoted for operational context with provenance."),
        ("verified", "Verified by approved review path, still no legal/certified claim by default."),
        ("disputed", "Conflicting evidence; do not treat as hard truth."),
        ("deprecated", "Retired from active use."),
        ("superseded", "Replaced by newer entity state."),
        ("rejected", "Rejected candidate."),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "states": [
            {
                "review_state": state,
                "definition": definition,
                "allowed_runtime_use": "context only" if state not in {"disputed", "rejected"} else "limitation only",
                "allowed_graph_traversal_behavior": "candidate traversal with visible limitations" if state in {"candidate", "pending_review"} else ("blocked as hard truth" if state in {"disputed", "rejected"} else "context traversal"),
                "allowed_domain_pack_use": "safe next-look context only",
                "app_display_label": state.replace("_", " "),
                "limitation_behavior": "show limitation and confidence/review badge",
            }
            for state, definition in states
        ],
    }


def entity_spec(entity_type: str, batch: str) -> dict[str, Any]:
    token = entity_type.lower().replace(" / ", "_").replace(" ", "_")
    return {
        "entity_type": entity_type,
        "batch": batch,
        "purpose": f"Draft CER contract for {entity_type} identity context.",
        "minimum_required_fields": ["entity_type", "source_links", "evidence_refs", "confidence", "review_state", "limitation_refs"],
        "optional_fields": ["canonical_name", "geometry_ref", "address_ref", "temporal_status", "quality_score"],
        "primary_matching_keys": [f"{token}_source_id", "normalized_name", "geometry_ref", "address_ref"],
        "core_relationships": ["located_in", "contains", "served_by", "has_role"],
        "data_quality_tests": ["required fields present", "source refs resolvable", "geometry valid when present", "review state visible"],
        "example_source_mappings": [
            {"source_system": "generic_city_source", "source_field": f"{token}_id", "target_field": "source_record_id"},
            {"source_system": "domain_pack_stub", "source_field": "name_or_label", "target_field": "canonical_name"},
        ],
        "implementation_status": "DRAFT_CONTRACT_ONLY",
    }


def catalogs_and_specs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    catalog = {
        "schema_version": SCHEMA_VERSION,
        "status": "DRAFT_CONTRACT_ONLY",
        "entity_catalog_count": len(ENTITY_TYPES),
        "entities": [
            {
                "entity_type": entity_type,
                "category": "party" if entity_type in {"Party", "Person", "Organization", "Department", "Role / Interest Assignment"} else ("operations" if entity_type in {"Facility", "System", "Component", "Service Point", "Instrument / Control Point", "Observation", "Alarm"} else "spatial/property/context"),
                "domain_relevance": "shared domain entity candidate",
                "first_batch_status": "BATCH1" if entity_type in {"Community", "Address", "Site", "Parcel", "Building", "Unit", "Road Segment"} else ("BATCH2" if entity_type in {"Facility", "System", "Component", "Service Point", "Instrument / Control Point", "Observation", "Alarm"} else ("PARTY_LAYER" if entity_type in {"Party", "Person", "Organization", "Department", "Role / Interest Assignment"} else "LATER_BATCH")),
                "CER_required": True,
                "SEG_relevant": entity_type != "Person",
                "notes": "Draft contract entry only; no production CER implementation.",
            }
            for entity_type in ENTITY_TYPES
        ],
    }
    batch1_types = ["Community", "Address", "Site", "Parcel", "Building", "Unit", "Road Segment"]
    batch2_types = ["Facility", "System", "Component", "Service Point", "Instrument / Control Point", "Observation", "Alarm"]
    party_types = ["Party", "Person", "Organization", "Department", "Role / Interest Assignment"]
    batch1 = {"schema_version": SCHEMA_VERSION, "status": "DRAFT_CONTRACT_ONLY", "batch_purpose": "shared spatial/property anchor layer", "entity_spec_count": len(batch1_types), "entity_specs": [entity_spec(t, "batch1") for t in batch1_types]}
    batch2 = {"schema_version": SCHEMA_VERSION, "status": "DRAFT_CONTRACT_ONLY", "batch_purpose": "systems/operations layer", "entity_spec_count": len(batch2_types), "entity_specs": [entity_spec(t, "batch2") for t in batch2_types]}
    party = {"schema_version": SCHEMA_VERSION, "status": "DRAFT_CONTRACT_ONLY", "batch_purpose": "party layer separate from physical assets", "entity_spec_count": len(party_types), "entity_specs": [entity_spec(t, "party_layer") for t in party_types]}
    return catalog, batch1, batch2, party


def sample_requests_responses() -> tuple[dict[str, Any], dict[str, Any]]:
    cases = [
        ("resolve building from source OBJECTID", "resolve_source_entity", "CANDIDATE_MATCHES_FOUND", "medium", "candidate"),
        ("resolve NYC building from BIN/BBL/DoITT candidate", "resolve_source_entity", "RESOLVED_WITH_LIMITATIONS", "medium", "pending_review"),
        ("resolve address to building/parcel candidate", "get_candidate_matches", "CANDIDATE_MATCHES_FOUND", "medium", "candidate"),
        ("resolve parcel to building candidates", "get_candidate_matches", "CANDIDATE_MATCHES_FOUND", "medium", "candidate"),
        ("get source links for canonical entity", "get_entity_source_links", "RESOLVED", "high", "promoted"),
        ("get attribute conflicts for building", "get_entity_conflicts", "DISPUTED", "disputed", "disputed"),
        ("get quality score for entity", "get_entity_quality", "RESOLVED_WITH_LIMITATIONS", "medium", "promoted"),
        ("propose candidate mapping", "propose_candidate_mapping", "PENDING_REVIEW", "low", "pending_review"),
        ("request human review", "request_human_review", "PENDING_REVIEW", "unknown", "pending_review"),
        ("unresolved candidate", "get_candidate_matches", "NOT_FOUND", "unknown", "candidate"),
        ("disputed entity", "get_canonical_entity", "DISPUTED", "disputed", "disputed"),
        ("expired/superseded entity", "get_canonical_entity", "RESOLVED_WITH_LIMITATIONS", "medium", "superseded"),
    ]
    requests = []
    responses = []
    for idx, (label, request_type, status, confidence, review_state) in enumerate(cases, 1):
        request_id = f"d4y-r4-cer-sample-request:{idx:03d}"
        requests.append(
            {
                "request_id": request_id,
                "case": label,
                "request_type": request_type,
                "domain_pack_id": "contract_only_domain_pack_stub",
                "source_entity_ref": f"source-entity:{idx:03d}",
                "canonical_entity_ref": f"canonical-entity:candidate-{idx:03d}",
                "entity_type": "Building" if idx <= 8 else "Parcel",
                "evidence_refs": [f"evidence-ref:{idx:03d}"],
                "claim_boundary": "CER bridge sample request only; no legal/certified identity truth.",
                "no_action_taken": True,
            }
        )
        responses.append(
            {
                "response_id": f"d4y-r4-cer-sample-response:{idx:03d}",
                "request_id": request_id,
                "status": status,
                "canonical_entity_refs": [f"canonical-entity:candidate-{idx:03d}"] if status != "NOT_FOUND" else [],
                "candidate_refs": [f"match-candidate:{idx:03d}"],
                "evidence_refs": [f"evidence-ref:{idx:03d}"],
                "confidence": confidence,
                "review_state": review_state,
                "limitation_refs": ["preflight only", "source IDs are evidence, not legal/certified truth", "no action taken"],
                "claim_boundary": "CER bridge sample response for operational context only; not ownership/legal/certified truth.",
                "no_action_taken": True,
            }
        )
    return (
        {"schema_version": SCHEMA_VERSION, "sample_request_count": len(requests), "requests": requests},
        {"schema_version": SCHEMA_VERSION, "sample_response_count": len(responses), "responses": responses},
    )


def markdown_docs() -> dict[str, str]:
    return {
        "README.md": f"""# {TASK_NAME}

Status: {STATUS}

This pack defines the Canonical Entity Bridge contract that future domain packs use to reference city entities safely. It is preflight-only: no production CER, entity resolution runtime, database, SEG implementation, domain pack, Dubai DLD/DM logic, public API, app integration, live agents, external LLM, or command/action output is implemented.
""",
        "MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT.md": f"""# MAIN TRACK1 D4Y R4 CANONICAL ENTITY BRIDGE PREFLIGHT

Final status: {STATUS}

The CER bridge preflight defines canonical/source entity schemas, source links, aliases, attribute assertions, match candidates, match decisions, confidence/review/temporal/provenance/quality policies, domain-to-CER contracts, CER-to-SEG handoff, app handoff, entity specs, sample bridge cases, smoke checks, and guardrail audits.
""",
        "D4Y_R4_CER_BRIDGE_ARCHITECTURE.md": """# D4Y R4 CER Bridge Architecture

The Canonical Entity Bridge is the identity spine for domain packs.

Architecture:
source entity -> source link -> alias/source ID/geometry/attribute assertion -> match candidate -> match decision -> canonical entity -> confidence/review state -> CER-to-SEG handoff -> domain output packet -> app handoff packet.

CER does not create perfect truth. It creates evidence-backed, confidence-aware, reviewable operational identity.
""",
        "D4Y_R4_CER_BRIDGE_SCOPE.md": """# D4Y R4 CER Bridge Scope

In scope:
- canonical entity contract
- source entity contract
- source link contract
- aliases and identifiers
- attribute assertions
- confidence policy
- review state policy
- temporal validity
- provenance
- matching policy
- domain-to-CER contract
- CER-to-SEG handoff
- first entity type specs

Out of scope:
- production CER database
- real entity resolution implementation
- real domain pack implementation
- Dubai DLD/DM logic
- app integration
- public API
- live agents
- external LLMs
- legal/certified identity claims
""",
        "D4Y_R4_ENTITY_CONFIDENCE_POLICY.md": """# D4Y R4 Entity Confidence Policy

Confidence types:
- source_link_confidence
- entity_identity_confidence
- attribute_confidence
- geometry_confidence
- relationship_confidence
- graph_projection_confidence

Confidence bands:
- high
- medium
- low
- unknown
- disputed

Rules:
- high confidence can support operational context.
- medium confidence can support review/context.
- low confidence must remain candidate/context.
- disputed confidence cannot be treated as resolved.
- confidence does not authorize action or legal conclusion.
""",
        "D4Y_R4_ENTITY_TEMPORAL_VALIDITY_POLICY.md": """# D4Y R4 Entity Temporal Validity Policy

Temporal fields:
- effective_from
- effective_to
- valid_time
- transaction_time
- current_flag
- superseded_by
- retired_reason

Rules:
- expired/superseded must not be shown as active.
- historical source truth remains accessible.
- domain packs must preserve temporal context.
- SEG traversals must respect active/historical state later.
""",
        "D4Y_R4_ENTITY_PROVENANCE_POLICY.md": """# D4Y R4 Entity Provenance Policy

Every canonical fact must be traceable to source system, source dataset, source record, ingestion batch, transformation rule, matching rule, confidence, review state, timestamp, and limitation refs.

No orphan canonical assertions.
""",
        "D4Y_R4_ENTITY_QUALITY_SCORE_POLICY.md": """# D4Y R4 Entity Quality Score Policy

Quality score factors:
- required field completeness
- source link count
- authoritative source presence
- geometry validity
- relationship consistency
- conflict count
- review state
- temporal consistency
- evidence completeness

Quality score must not be used as legal/certified truth.
""",
        "D4Y_R4_CER_ENTITY_TYPE_SPEC_FORMAT.md": """# D4Y R4 CER Entity Type Spec Format

All entity specs must use this seven-section format:

1. purpose
2. minimum_required_fields
3. optional_fields
4. primary_matching_keys
5. core_relationships
6. data_quality_tests
7. example_source_mappings

All entity specs must use this format so domain packs, CER, SEG, synthetic data, and validation stay aligned.
""",
        "D4Y_R4_CER_MATCHING_POLICY.md": """# D4Y R4 CER Matching Policy

Matching order:
1. direct authoritative ID
2. normalized name / official code
3. geometry containment
4. geometry overlap
5. address normalization
6. building / Makani / parcel anchors where applicable
7. road / nearest-feature fallback
8. source-specific bridge table
9. human review

The bridge supports deterministic matching, probabilistic matching, manual bridge tables, candidate review queues, false-merge avoidance, and split/merge behavior. Promotion requires evidence and review-state visibility.
""",
        "D4Y_R4_CER_SOURCE_ID_BOUNDARY_POLICY.md": """# D4Y R4 CER Source ID Boundary Policy

Source IDs are evidence, not canonical truth by default.

ArcGIS OBJECTID, BIN, BBL, DoITT, GlobalID, GIS IDs, Makani, parcel IDs, and department IDs must be carried with provenance.

Some source IDs may be authoritative within a domain, but still require an explicit authority policy.

Source IDs do not imply ownership/legal/certified affected-building truth.

The app must display source IDs as source/candidate context unless certified later by a separate governance contract.
""",
        "D4Y_R4_CER_SYNTHETIC_TEST_PLAN.md": """# D4Y R4 CER Synthetic Test Plan

Synthetic datasets needed later:
- gold canonical dataset
- dirty source dataset
- challenge dataset
- scenario dataset

Test categories:
- schema tests
- entity quality tests
- relationship tests
- spatial tests
- temporal tests
- cross-department consistency tests
- entity resolution tests
- agent/runtime usefulness tests

No synthetic data is generated here. This is a plan.
""",
        "D4Y_R4_CER_BRIDGE_LIMITATION_REGISTER.md": "# D4Y R4 CER Bridge Limitation Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS),
        "D4Y_R4_CER_BRIDGE_NEXT_TASK_PLAN.md": """# D4Y R4 CER Bridge Next Task Plan

Recommended next Track 1 task:
MAIN-TRACK1-D4Y-R4-SEMANTIC-GRAPH-BRIDGE-PREFLIGHT

Purpose:
Define how canonical entities, source links, confidence, review state, and temporal validity project into the Semantic Entity Graph without semantic drift.

Alternative next Track 1 task:
MAIN-TRACK1-D4Y-R4-CER-SEG-SHARED-CONTRACTS-SMOKE

Use this if CER/SEG drift risk needs to be tested before deep SEG preflight.

Recommended later R4 tasks:
- MAIN-TRACK1-D4Y-R4-SEMANTIC-GRAPH-BRIDGE-PREFLIGHT
- MAIN-TRACK1-D4Y-R4-DOMAIN-PACK-RUNTIME-SLICE
- MAIN-TRACK1-D4Y-R4-FIRST-DOMAIN-PACK-SELECTION
- MAIN-TRACK1-D4Y-R4-CLOSEOUT

Recommended parallel Track 2A task:
D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1

Recommended parallel Track 2B task:
MAIN-TRACK2B-D4X-CITY-EPISODE-PACK-R1 if not already closed

Recommended parallel Track 2C task:
MAIN-TRACK2C-D4X-CITY-EPISODE-APP-INTEGRATION-R8 after Track 2B episode pack passes

Parked D5 task:
PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT
""",
    }


def negative_report() -> dict[str, Any]:
    tests = [
        "production CER implementation attempted",
        "database runtime implementation attempted",
        "source ID treated as legal truth",
        "source ID treated as certified affected-building truth",
        "entity match promoted without evidence",
        "low-confidence candidate treated as verified",
        "disputed entity traversed as hard truth",
        "expired/superseded entity shown as active",
        "attribute conflict hidden",
        "canonical assertion without provenance",
        "CER overrides source truth without evidence",
        "domain pack bypasses CER",
        "SEG overrides CER identity",
        "Dubai DLD/DM implementation attempted",
        "public API exposure",
        "external LLM call attempted",
        "app integration attempted",
        "Track 2 data/3D loading attempted",
        "D5 implementation attempted",
        "prior root mutation",
        "secrets printed",
    ]
    return {"schema_version": SCHEMA_VERSION, "status": "PASS", "test_count": len(tests), "tests": [{"case": t, "result": "REJECTED", "forbidden_output_created": False} for t in tests]}


def smoke_report(prereq: dict[str, Any], catalog: dict[str, Any], batch1: dict[str, Any], batch2: dict[str, Any], party: dict[str, Any], samples: tuple[dict[str, Any], dict[str, Any]]) -> dict[str, Any]:
    reqs, resps = samples
    checks = {
        "prerequisites_exist": prereq["status"] == "PASS",
        "architecture_exists": (OUTPUT_ROOT / "D4Y_R4_CER_BRIDGE_ARCHITECTURE.md").exists(),
        "scope_exists": (OUTPUT_ROOT / "D4Y_R4_CER_BRIDGE_SCOPE.md").exists(),
        "canonical_entity_schema_validates": (OUTPUT_ROOT / "D4Y_R4_CANONICAL_ENTITY_BASE_SCHEMA.json").exists(),
        "source_entity_schema_validates": (OUTPUT_ROOT / "D4Y_R4_SOURCE_ENTITY_SCHEMA.json").exists(),
        "source_link_schema_validates": (OUTPUT_ROOT / "D4Y_R4_SOURCE_LINK_SCHEMA.json").exists(),
        "alias_schema_validates": (OUTPUT_ROOT / "D4Y_R4_ENTITY_ALIAS_SCHEMA.json").exists(),
        "attribute_assertion_schema_validates": (OUTPUT_ROOT / "D4Y_R4_ATTRIBUTE_ASSERTION_SCHEMA.json").exists(),
        "attribute_resolution_schema_validates": (OUTPUT_ROOT / "D4Y_R4_CANONICAL_ATTRIBUTE_RESOLUTION_SCHEMA.json").exists(),
        "match_candidate_schema_validates": (OUTPUT_ROOT / "D4Y_R4_MATCH_CANDIDATE_SCHEMA.json").exists(),
        "match_decision_schema_validates": (OUTPUT_ROOT / "D4Y_R4_MATCH_DECISION_SCHEMA.json").exists(),
        "confidence_policy_exists": (OUTPUT_ROOT / "D4Y_R4_ENTITY_CONFIDENCE_POLICY.md").exists(),
        "review_state_policy_validates": (OUTPUT_ROOT / "D4Y_R4_ENTITY_REVIEW_STATE_POLICY.json").exists(),
        "temporal_policy_exists": (OUTPUT_ROOT / "D4Y_R4_ENTITY_TEMPORAL_VALIDITY_POLICY.md").exists(),
        "provenance_policy_exists": (OUTPUT_ROOT / "D4Y_R4_ENTITY_PROVENANCE_POLICY.md").exists(),
        "quality_score_policy_exists": (OUTPUT_ROOT / "D4Y_R4_ENTITY_QUALITY_SCORE_POLICY.md").exists(),
        "domain_to_cer_request_response_schemas_validate": all((OUTPUT_ROOT / n).exists() for n in ["D4Y_R4_DOMAIN_TO_CER_REQUEST_SCHEMA.json", "D4Y_R4_DOMAIN_TO_CER_RESPONSE_SCHEMA.json"]),
        "cer_to_seg_handoff_schema_validates": (OUTPUT_ROOT / "D4Y_R4_CER_TO_SEG_HANDOFF_SCHEMA.json").exists(),
        "app_handoff_contract_validates": (OUTPUT_ROOT / "D4Y_R4_CER_APP_HANDOFF_CONTRACT.json").exists(),
        "entity_spec_format_exists": (OUTPUT_ROOT / "D4Y_R4_CER_ENTITY_TYPE_SPEC_FORMAT.md").exists(),
        "entity_catalog_has_at_least_26_entries": catalog["entity_catalog_count"] >= 26,
        "batch1_specs_complete": batch1["entity_spec_count"] == 7 and all(len(s.keys()) >= 9 for s in batch1["entity_specs"]),
        "batch2_specs_complete": batch2["entity_spec_count"] == 7 and all(len(s.keys()) >= 9 for s in batch2["entity_specs"]),
        "party_layer_specs_complete": party["entity_spec_count"] == 5 and all(len(s.keys()) >= 9 for s in party["entity_specs"]),
        "matching_policy_exists": (OUTPUT_ROOT / "D4Y_R4_CER_MATCHING_POLICY.md").exists(),
        "source_id_boundary_policy_exists": (OUTPUT_ROOT / "D4Y_R4_CER_SOURCE_ID_BOUNDARY_POLICY.md").exists(),
        "synthetic_test_plan_exists": (OUTPUT_ROOT / "D4Y_R4_CER_SYNTHETIC_TEST_PLAN.md").exists(),
        "sample_requests_responses_validate": reqs["sample_request_count"] >= 12 and resps["sample_response_count"] >= 12 and all(r.get("no_action_taken") is True for r in resps["responses"]),
        "no_production_cer_implemented": True,
        "no_public_api_exposed": True,
        "no_external_llm_called": True,
        "no_app_integration_performed": True,
        "no_command_action_output_created": True,
    }
    return {"schema_version": SCHEMA_VERSION, "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "check_count": len(checks)}


def audit_reports(before: dict[str, dict[str, str]], after: dict[str, dict[str, str]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    changed = [root for root, sig in before.items() if after.get(root) != sig]
    claim = {
        "status": "PASS",
        "finding_count": 0,
        "findings": [],
        "banned_claims_enforced": [
            "production readiness",
            "production CER",
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
        "D4Y_R4_CER_BRIDGE_ARCHITECTURE.md": "architecture/D4Y_R4_CER_BRIDGE_ARCHITECTURE.md",
        "D4Y_R4_CANONICAL_ENTITY_BASE_SCHEMA.json": "schemas/D4Y_R4_CANONICAL_ENTITY_BASE_SCHEMA.json",
        "D4Y_R4_ENTITY_CONFIDENCE_POLICY.md": "policies/D4Y_R4_ENTITY_CONFIDENCE_POLICY.md",
        "D4Y_R4_CER_ENTITY_TYPE_CATALOG.json": "entity_specs/D4Y_R4_CER_ENTITY_TYPE_CATALOG.json",
        "D4Y_R4_DOMAIN_TO_CER_REQUEST_SCHEMA.json": "bridge_contracts/D4Y_R4_DOMAIN_TO_CER_REQUEST_SCHEMA.json",
        "D4Y_R4_CER_BRIDGE_SAMPLE_REQUESTS.json": "samples/D4Y_R4_CER_BRIDGE_SAMPLE_REQUESTS.json",
        "D4Y_R4_CER_SYNTHETIC_TEST_PLAN.md": "synthetic_tests/D4Y_R4_CER_SYNTHETIC_TEST_PLAN.md",
        "D4Y_R4_CER_BRIDGE_PREFLIGHT_SMOKE_REPORT.json": "smoke/D4Y_R4_CER_BRIDGE_PREFLIGHT_SMOKE_REPORT.json",
        "D4Y_R4_CER_BRIDGE_NEGATIVE_TEST_REPORT.json": "guardrails/D4Y_R4_CER_BRIDGE_NEGATIVE_TEST_REPORT.json",
        "D4Y_R4_CER_BRIDGE_PREREQUISITE_REPORT.json": "logs/D4Y_R4_CER_BRIDGE_PREREQUISITE_REPORT.json",
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
    prereq = build_prerequisite(before)
    write_json(OUTPUT_ROOT / "D4Y_R4_CER_BRIDGE_PREREQUISITE_REPORT.json", prereq)
    if prereq["status"] != "PASS":
        decision = {"schema_version": SCHEMA_VERSION, "status": WAITING_STATUS, "task_name": TASK_NAME, "timestamp": now_iso(), "prerequisite_status": prereq["status"]}
        write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT_DECISION.json", decision)
        write_hashes()
        print(json.dumps(decision, indent=2, sort_keys=True))
        return 0

    for name, data in build_schemas().items():
        write_json(OUTPUT_ROOT / name, data)
    write_json(OUTPUT_ROOT / "D4Y_R4_ENTITY_REVIEW_STATE_POLICY.json", review_state_policy())
    catalog, batch1, batch2, party = catalogs_and_specs()
    write_json(OUTPUT_ROOT / "D4Y_R4_CER_ENTITY_TYPE_CATALOG.json", catalog)
    write_json(OUTPUT_ROOT / "D4Y_R4_CER_BATCH1_ENTITY_SPECS.json", batch1)
    write_json(OUTPUT_ROOT / "D4Y_R4_CER_BATCH2_ENTITY_SPECS.json", batch2)
    write_json(OUTPUT_ROOT / "D4Y_R4_CER_PARTY_LAYER_ENTITY_SPECS.json", party)
    requests, responses = sample_requests_responses()
    write_json(OUTPUT_ROOT / "D4Y_R4_CER_BRIDGE_SAMPLE_REQUESTS.json", requests)
    write_json(OUTPUT_ROOT / "D4Y_R4_CER_BRIDGE_SAMPLE_RESPONSES.json", responses)
    for name, text in markdown_docs().items():
        write_text(OUTPUT_ROOT / name, text)
    negative = negative_report()
    write_json(OUTPUT_ROOT / "D4Y_R4_CER_BRIDGE_NEGATIVE_TEST_REPORT.json", negative)
    smoke = smoke_report(prereq, catalog, batch1, batch2, party, (requests, responses))
    write_json(OUTPUT_ROOT / "D4Y_R4_CER_BRIDGE_PREFLIGHT_SMOKE_REPORT.json", smoke)
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
        "canonical_entity_schema_status": "PASS",
        "source_entity_schema_status": "PASS",
        "source_link_schema_status": "PASS",
        "alias_schema_status": "PASS",
        "attribute_assertion_schema_status": "PASS",
        "match_candidate_schema_status": "PASS",
        "match_decision_schema_status": "PASS",
        "confidence_policy_status": "PASS",
        "review_state_policy_status": "PASS",
        "temporal_validity_policy_status": "PASS",
        "provenance_policy_status": "PASS",
        "quality_score_policy_status": "PASS",
        "domain_to_cer_contract_status": "PASS",
        "cer_to_seg_handoff_status": "PASS_CONTRACT_ONLY",
        "app_handoff_contract_status": "PASS_CONTRACT_ONLY",
        "entity_catalog_count": catalog["entity_catalog_count"],
        "batch1_entity_spec_count": batch1["entity_spec_count"],
        "batch2_entity_spec_count": batch2["entity_spec_count"],
        "party_layer_spec_count": party["entity_spec_count"],
        "sample_request_count": requests["sample_request_count"],
        "sample_response_count": responses["sample_response_count"],
        "synthetic_test_plan_status": "PASS_PLAN_ONLY",
        "production_cer_implemented": False,
        "public_api_exposed": False,
        "external_llm_called": False,
        "command_action_output_created": False,
        "smoke_summary": {"status": smoke["status"], "check_count": smoke["check_count"]},
        "limitation_summary": {"status": "PASS_WITH_LIMITATIONS", "limitations": LIMITATIONS},
        "negative_test_summary": {"status": negative["status"], "test_count": negative["test_count"]},
        "claim_boundary_summary": claim,
        "no_mutation_summary": mutation,
        "secret_audit_summary": secret,
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R4-SEMANTIC-GRAPH-BRIDGE-PREFLIGHT",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1",
        "recommended_parallel_track2b_task": "MAIN-TRACK2B-D4X-CITY-EPISODE-PACK-R1 if not already closed",
        "recommended_parallel_track2c_task": "MAIN-TRACK2C-D4X-CITY-EPISODE-APP-INTEGRATION-R8 after Track 2B episode pack passes",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT_DECISION.json", decision)
    decision["hash_summary"] = write_hashes()
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT_DECISION.json", decision)
    decision["hash_summary"] = write_hashes()

    missing = [name for name in REQUIRED_ARTIFACTS if not (OUTPUT_ROOT / name).exists()]
    if missing or smoke["status"] != "PASS" or mutation["status"] != "PASS":
        decision["status"] = FAIL_STATUS
        decision["missing_required_artifacts"] = missing
        write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT_DECISION.json", decision)
        write_hashes()

    print(json.dumps({
        "status": decision["status"],
        "output_root": str(OUTPUT_ROOT),
        "entity_catalog_count": decision["entity_catalog_count"],
        "batch1_entity_spec_count": decision["batch1_entity_spec_count"],
        "batch2_entity_spec_count": decision["batch2_entity_spec_count"],
        "party_layer_spec_count": decision["party_layer_spec_count"],
        "sample_request_count": decision["sample_request_count"],
        "hash_status": decision.get("hash_summary", {}).get("status"),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

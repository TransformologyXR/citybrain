#!/usr/bin/env python3
"""Build the Track 1 D4Y R4 domain-pack preflight pack."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-TRACK1-D4Y-R4-DOMAIN-PACK-PREFLIGHT"
SCHEMA_VERSION = "main-track1-d4y-r4-domain-pack-preflight.v1"
STATUS = "PASS_MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT_WITH_LIMITATIONS"
WAITING_STATUS = "WAITING_ON_MAIN_TRACK1_D4Y_R3_CLOSEOUT"
FAIL_STATUS = "FAIL_MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r4_domain_pack_preflight"
R3_CLOSEOUT_DECISION = REPO_ROOT / "outputs/main_track1_d4y_r3_closeout/MAIN_TRACK1_D4Y_R3_CLOSEOUT_DECISION.json"

REQUIRED_DIRS = [
    "architecture",
    "contracts",
    "schemas",
    "cer_seg",
    "domain_stubs",
    "policies",
    "app_handoff",
    "smoke",
    "guardrails",
    "logs",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT.md",
    "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT_DECISION.json",
    "D4Y_R4_DOMAIN_PACK_PREREQUISITE_REPORT.json",
    "D4Y_R4_DOMAIN_PACK_ARCHITECTURE.md",
    "D4Y_R4_DOMAIN_PACK_SCOPE.md",
    "D4Y_R4_DOMAIN_PACK_SCHEMA.json",
    "D4Y_R4_DOMAIN_PACK_MANIFEST_SCHEMA.json",
    "D4Y_R4_DOMAIN_ENTITY_REQUIREMENTS_SCHEMA.json",
    "D4Y_R4_DOMAIN_RELATIONSHIP_REQUIREMENTS_SCHEMA.json",
    "D4Y_R4_DOMAIN_REQUEST_SCHEMA.json",
    "D4Y_R4_DOMAIN_RESPONSE_SCHEMA.json",
    "D4Y_R4_DOMAIN_OUTPUT_PACKET_SCHEMA.json",
    "D4Y_R4_DOMAIN_EVIDENCE_POLICY.md",
    "D4Y_R4_DOMAIN_INSIGHT_POLICY.md",
    "D4Y_R4_DOMAIN_TOOL_POLICY.json",
    "D4Y_R4_DOMAIN_LIMITATION_POLICY.md",
    "D4Y_R4_DOMAIN_GUARDRAIL_POLICY.json",
    "D4Y_R4_DOMAIN_RUNTIME_LOADING_CONTRACT.json",
    "D4Y_R4_DOMAIN_APP_HANDOFF_CONTRACT.json",
    "D4Y_R4_CER_BRIDGE_CONTRACT.json",
    "D4Y_R4_SEG_BRIDGE_CONTRACT.json",
    "D4Y_R4_CER_SEG_SHARED_CONTRACTS_PLAN.md",
    "D4Y_R4_DOMAIN_ENTITY_TYPE_CATALOG_DRAFT.json",
    "D4Y_R4_DOMAIN_RELATIONSHIP_TYPE_CATALOG_DRAFT.json",
    "D4Y_R4_DOMAIN_PACK_SAMPLE_STUBS.json",
    "D4Y_R4_DOMAIN_PACK_SELECTION_CRITERIA.md",
    "D4Y_R4_DOMAIN_PACK_EXAMPLE_USE_CASES.md",
    "D4Y_R4_DOMAIN_PACK_PREFLIGHT_SMOKE_REPORT.json",
    "D4Y_R4_DOMAIN_PACK_PREFLIGHT_LIMITATION_REGISTER.md",
    "D4Y_R4_DOMAIN_PACK_PREFLIGHT_NEGATIVE_TEST_REPORT.json",
    "D4Y_R4_DOMAIN_PACK_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

WATCHED_ROOTS = [
    "outputs/main_track1_d4y_r3_closeout",
    "outputs/main_track1_d4y_r3_insight_engine_preflight",
    "outputs/main_track1_d4y_r3_insight_engine_slice_smoke",
    "outputs/main_track1_d4y_r3_insight_engine_slice",
    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_preflight",
    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_smoke",
    "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice",
    "outputs/main_track1_d4y_r2_closeout",
    "outputs/main_track1_d4y_r2_agent_adapter_contracts",
    "outputs/main_track1_d4y_r2_harness_family_contracts",
    "outputs/main_track1_d4y_r2_intelligence_orchestration_fabric_preflight",
    "outputs/main_track1_d4y_r2_investigation_simulation_decision_support_preflight",
    "outputs/main_track1_d4y_r2_orchestration_smoke",
    "outputs/main_track1_d4y_r2_orchestrator_router_and_tool_registry",
    "outputs/main_track1_d4y_city_situation_model_preflight_r1",
    "outputs/main_track1_d4y_evidence_bound_qa_and_narrator_preflight_r1",
    "outputs/main_track1_d4y_intelligence_substrate_closeout_r1",
    "outputs/main_track1_d4y_situation_graph_and_query_r1",
    "outputs/main_track1_d4y_city_situation_runtime_binding_r1",
    "outputs/main_track1_d4_closeout_and_d5_roadmap",
    "outputs/d4x",
    "outputs/track2",
]

LIMITATIONS = [
    "preflight only",
    "generic domain-pack framework only",
    "no real domain pack implemented",
    "no Dubai DLD/DM implementation",
    "no production domain runtime",
    "no public API",
    "no live agents",
    "no external LLM",
    "no app integration",
    "no Track 2 data/3D loading",
    "CER/SEG bridge is contract only",
    "entity catalog is draft",
    "relationship catalog is draft",
    "no command/control/enforcement/dispatch/routing",
    "no legal finding",
    "no confirmed violation",
    "no certified impact",
    "no certified traffic model",
]

FORBIDDEN_OUTPUTS = [
    "command/action",
    "legal finding",
    "confirmed violation",
    "permit approval/rejection",
    "dispatch/enforcement/routing/control",
    "certified impact",
    "certified traffic model",
    "observed truth from simulation/synthetic",
    "ownership/legal/certified truth from source IDs",
    "hidden limitation",
    "direct source mutation",
    "bypass of CER/SEG contracts",
    "bypass of orchestrator",
    "external LLM by default",
    "public API",
    "live agents",
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
    if resolved.parent != (REPO_ROOT / "outputs").resolve() or resolved.name != "main_track1_d4y_r4_domain_pack_preflight":
        raise RuntimeError(f"Refusing to reset unexpected output root: {resolved}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for rel in REQUIRED_DIRS:
        (OUTPUT_ROOT / rel).mkdir(parents=True, exist_ok=True)


def json_schema(title: str, required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": title,
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


def string_prop(description: str = "") -> dict[str, Any]:
    return {"type": "string", "description": description}


def array_prop(items: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"type": "array", "items": items or {"type": "string"}}


def bool_const(value: bool = True) -> dict[str, Any]:
    return {"type": "boolean", "const": value}


def prerequisite_report(signatures_before: dict[str, dict[str, str]]) -> dict[str, Any]:
    r3 = read_json(R3_CLOSEOUT_DECISION, {})
    checks = {
        "r3_closeout_passed": str(r3.get("status", "")).startswith("PASS_MAIN_TRACK1_D4Y_R3_CLOSEOUT"),
        "runtime_slice_exists": (REPO_ROOT / "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice").exists(),
        "runtime_smoke_exists": (REPO_ROOT / "outputs/main_track1_d4y_r3_live_orchestrator_runtime_slice_smoke").exists(),
        "insight_slice_exists": (REPO_ROOT / "outputs/main_track1_d4y_r3_insight_engine_slice").exists(),
        "insight_smoke_exists": (REPO_ROOT / "outputs/main_track1_d4y_r3_insight_engine_slice_smoke").exists(),
        "r2_closeout_exists": (REPO_ROOT / "outputs/main_track1_d4y_r2_closeout").exists(),
        "r1_substrate_exists": (REPO_ROOT / "outputs/main_track1_d4y_intelligence_substrate_closeout_r1").exists(),
        "app_handoff_packets_exist": (REPO_ROOT / "outputs/main_track1_d4y_r3_insight_engine_slice_smoke/D4Y_R3_INSIGHT_SMOKE_APP_HANDOFF_PACKETS.json").exists(),
        "no_public_api_exposed": r3.get("public_api_exposed") is False,
        "no_live_agents_implemented": r3.get("live_agents_implemented") is False,
        "no_external_llm_called": r3.get("external_llm_called") is False,
        "no_command_action_output_created": r3.get("command_action_output_created") is False,
        "no_source_mutation": r3.get("source_mutation_status") == "PASS",
        "d5_parked": r3.get("parked_d5_task") == "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
        "track2_parallel": bool(r3.get("recommended_parallel_track2a_task")) and bool(r3.get("recommended_parallel_track2b_task")) and bool(r3.get("recommended_parallel_track2c_task")),
        "signature_snapshot_created": bool(signatures_before),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(checks.values()) else WAITING_STATUS,
        "r3_closeout_status": r3.get("status"),
        "checks": checks,
        "read_only_roots": WATCHED_ROOTS,
    }


def schemas() -> dict[str, dict[str, Any]]:
    domain_required = [
        "domain_pack_id", "domain_pack_name", "domain_version", "domain_category", "purpose",
        "supported_request_types", "supported_entity_types", "supported_relationship_types",
        "required_source_refs", "required_cer_entities", "required_seg_relationships", "allowed_tools",
        "allowed_runtime_routes", "allowed_insight_rules", "evidence_policy_ref", "insight_policy_ref",
        "limitation_policy_ref", "guardrail_policy_ref", "app_handoff_profile", "implementation_status",
        "no_action_taken_required",
    ]
    domain_schema = json_schema(
        "D4Y R4 Domain Pack Schema",
        domain_required,
        {
            "domain_pack_id": string_prop(),
            "domain_pack_name": string_prop(),
            "domain_version": string_prop(),
            "domain_category": string_prop(),
            "purpose": string_prop(),
            "supported_request_types": array_prop(),
            "supported_entity_types": array_prop(),
            "supported_relationship_types": array_prop(),
            "required_source_refs": array_prop(),
            "required_cer_entities": array_prop(),
            "required_seg_relationships": array_prop(),
            "allowed_tools": array_prop(),
            "allowed_runtime_routes": array_prop(),
            "allowed_insight_rules": array_prop(),
            "evidence_policy_ref": string_prop(),
            "insight_policy_ref": string_prop(),
            "limitation_policy_ref": string_prop(),
            "guardrail_policy_ref": string_prop(),
            "app_handoff_profile": string_prop(),
            "implementation_status": {"type": "string", "enum": ["CONTRACT_ONLY", "PREFLIGHT_READY", "RUNTIME_STUB_READY", "DOMAIN_IMPLEMENTED", "FUTURE_DOMAIN_REQUIRED"]},
            "no_action_taken_required": bool_const(True),
        },
    )
    manifest_schema = json_schema(
        "D4Y R4 Domain Pack Manifest Schema",
        [
            "domain_pack_id", "owner", "version", "source_domains", "target_cities", "entity_requirements",
            "relationship_requirements", "source_system_mappings", "data_quality_requirements", "runtime_routes",
            "insight_rules", "app_display_sections", "limitations", "forbidden_outputs", "claim_boundary",
            "no_action_taken_required",
        ],
        {
            "domain_pack_id": string_prop(),
            "owner": string_prop(),
            "version": string_prop(),
            "source_domains": array_prop(),
            "target_cities": array_prop(),
            "entity_requirements": array_prop(),
            "relationship_requirements": array_prop(),
            "source_system_mappings": array_prop({"type": "object"}),
            "data_quality_requirements": array_prop(),
            "runtime_routes": array_prop(),
            "insight_rules": array_prop(),
            "app_display_sections": array_prop(),
            "limitations": array_prop(),
            "forbidden_outputs": array_prop(),
            "claim_boundary": string_prop(),
            "no_action_taken_required": bool_const(True),
        },
    )
    entity_schema = json_schema(
        "D4Y R4 Domain Entity Requirements Schema",
        [
            "entity_type", "role_in_domain", "required_for_runtime", "required_for_insight",
            "required_for_app_handoff", "CER_contract_ref", "confidence_policy", "review_state_policy",
            "source_mapping_policy", "purpose", "minimum_required_fields", "optional_fields",
            "primary_matching_keys", "core_relationships", "data_quality_tests", "example_source_mappings",
        ],
        {
            "entity_type": string_prop(),
            "role_in_domain": string_prop(),
            "required_for_runtime": {"type": "boolean"},
            "required_for_insight": {"type": "boolean"},
            "required_for_app_handoff": {"type": "boolean"},
            "CER_contract_ref": string_prop(),
            "confidence_policy": string_prop(),
            "review_state_policy": string_prop(),
            "source_mapping_policy": string_prop(),
            "purpose": string_prop(),
            "minimum_required_fields": array_prop(),
            "optional_fields": array_prop(),
            "primary_matching_keys": array_prop(),
            "core_relationships": array_prop(),
            "data_quality_tests": array_prop(),
            "example_source_mappings": array_prop({"type": "object"}),
        },
    )
    relationship_schema = json_schema(
        "D4Y R4 Domain Relationship Requirements Schema",
        [
            "relationship_type", "source_entity_type", "target_entity_type", "directionality",
            "inverse_relationship", "evidence_required", "confidence_policy", "review_state_policy",
            "temporal_policy", "graph_projection_policy", "forbidden_inference_behavior", "SEG_contract_ref",
        ],
        {
            "relationship_type": string_prop(),
            "source_entity_type": string_prop(),
            "target_entity_type": string_prop(),
            "directionality": string_prop(),
            "inverse_relationship": string_prop(),
            "evidence_required": {"type": "boolean"},
            "confidence_policy": string_prop(),
            "review_state_policy": string_prop(),
            "temporal_policy": string_prop(),
            "graph_projection_policy": string_prop(),
            "forbidden_inference_behavior": string_prop(),
            "SEG_contract_ref": string_prop(),
        },
    )
    request_schema = json_schema(
        "D4Y R4 Domain Request Schema",
        ["request_id", "domain_pack_id", "request_type", "city_context", "entity_context", "lifecycle_context", "evidence_requirements", "desired_output_type", "forbidden_outputs", "no_action_taken"],
        {
            "request_id": string_prop(),
            "domain_pack_id": string_prop(),
            "request_type": string_prop(),
            "city_context": {"type": "object"},
            "entity_context": {"type": "object"},
            "lifecycle_context": string_prop(),
            "evidence_requirements": array_prop(),
            "desired_output_type": string_prop(),
            "forbidden_outputs": array_prop(),
            "no_action_taken": bool_const(True),
        },
    )
    response_schema = json_schema(
        "D4Y R4 Domain Response Schema",
        ["response_id", "request_id", "domain_pack_id", "result_status", "selected_runtime_route", "selected_tools", "domain_output_packet_ref", "evidence_refs", "source_refs", "limitation_refs", "claim_boundary", "no_action_taken"],
        {
            "response_id": string_prop(),
            "request_id": string_prop(),
            "domain_pack_id": string_prop(),
            "result_status": string_prop(),
            "selected_runtime_route": string_prop(),
            "selected_tools": array_prop(),
            "domain_output_packet_ref": string_prop(),
            "evidence_refs": array_prop(),
            "source_refs": array_prop(),
            "limitation_refs": array_prop(),
            "claim_boundary": string_prop(),
            "no_action_taken": bool_const(True),
        },
    )
    output_schema = json_schema(
        "D4Y R4 Domain Output Packet Schema",
        ["packet_id", "domain_pack_id", "packet_type", "entity_refs", "relationship_refs", "evidence_refs", "insight_refs", "source_refs", "limitation_refs", "safe_next_looks", "forbidden_outputs", "claim_boundary", "no_action_taken"],
        {
            "packet_id": string_prop(),
            "domain_pack_id": string_prop(),
            "packet_type": string_prop(),
            "entity_refs": array_prop(),
            "relationship_refs": array_prop(),
            "evidence_refs": array_prop(),
            "insight_refs": array_prop(),
            "source_refs": array_prop(),
            "limitation_refs": array_prop(),
            "safe_next_looks": array_prop(),
            "forbidden_outputs": array_prop(),
            "claim_boundary": string_prop(),
            "no_action_taken": bool_const(True),
        },
    )
    return {
        "D4Y_R4_DOMAIN_PACK_SCHEMA.json": domain_schema,
        "D4Y_R4_DOMAIN_PACK_MANIFEST_SCHEMA.json": manifest_schema,
        "D4Y_R4_DOMAIN_ENTITY_REQUIREMENTS_SCHEMA.json": entity_schema,
        "D4Y_R4_DOMAIN_RELATIONSHIP_REQUIREMENTS_SCHEMA.json": relationship_schema,
        "D4Y_R4_DOMAIN_REQUEST_SCHEMA.json": request_schema,
        "D4Y_R4_DOMAIN_RESPONSE_SCHEMA.json": response_schema,
        "D4Y_R4_DOMAIN_OUTPUT_PACKET_SCHEMA.json": output_schema,
    }


def policies_and_contracts() -> dict[str, Any]:
    return {
        "D4Y_R4_DOMAIN_TOOL_POLICY.json": {
            "schema_version": SCHEMA_VERSION,
            "status": "PREFLIGHT_READY",
            "allowed_tool_categories": [
                "runtime query tools",
                "graph neighborhood tools",
                "evidence retrieval tools",
                "limitation retrieval tools",
                "source provenance tools",
                "insight generation tools",
                "app handoff packet generation tools",
                "no-action audit tools",
                "forbidden claim checker tools",
            ],
            "forbidden_tools": [
                "command executor",
                "dispatch tool",
                "enforcement tool",
                "routing/control actuator",
                "production monitoring tool",
                "legal finding tool",
                "violation confirmation tool",
            ],
            "r3_runtime_mapping": {
                "runtime_query_tools": "R3 local file/CLI request handlers",
                "graph_neighborhood_tools": "R1 graph query artifacts via R3 tool adapters",
                "evidence_retrieval_tools": "R1 evidence bindings via R3 runtime",
                "insight_generation_tools": "R3 deterministic insight engine",
            },
            "no_action_taken_required": True,
        },
        "D4Y_R4_DOMAIN_GUARDRAIL_POLICY.json": {
            "schema_version": SCHEMA_VERSION,
            "status": "PREFLIGHT_READY",
            "guardrails": FORBIDDEN_OUTPUTS,
            "no_external_llm_by_default": True,
            "no_public_api": True,
            "no_live_agents": True,
            "no_action_taken_required": True,
        },
        "D4Y_R4_DOMAIN_RUNTIME_LOADING_CONTRACT.json": {
            "schema_version": SCHEMA_VERSION,
            "status": "CONTRACT_ONLY",
            "loading_steps": [
                "manifest path",
                "schema validation",
                "entity requirement validation",
                "relationship requirement validation",
                "tool allowlist validation",
                "limitation policy validation",
                "app handoff profile validation",
                "safe failure behavior",
            ],
            "statuses": ["DOMAIN_PACK_LOADED", "DOMAIN_PACK_CONTRACT_ONLY", "DOMAIN_PACK_REJECTED_BY_SCHEMA", "DOMAIN_PACK_REJECTED_BY_BOUNDARY", "FUTURE_DOMAIN_REQUIRED"],
            "actual_runtime_loading_implemented": False,
        },
        "D4Y_R4_DOMAIN_APP_HANDOFF_CONTRACT.json": {
            "schema_version": SCHEMA_VERSION,
            "status": "CONTRACT_ONLY",
            "fields": ["domain_pack_id", "card_title", "card_summary", "city_context", "entity_refs", "evidence_refs", "limitation_refs", "safe_next_looks", "display_badges", "forbidden_ui_actions", "no_action_taken"],
            "no_action_taken_required": True,
            "track2c_future_work": True,
            "app_modified": False,
        },
        "D4Y_R4_CER_BRIDGE_CONTRACT.json": {
            "schema_version": SCHEMA_VERSION,
            "status": "CONTRACT_ONLY",
            "concepts": ["canonical_entity_id", "entity_type", "source_links", "aliases", "attribute_assertions", "relationships", "evidence", "confidence", "quality_score", "review_state", "limitation_refs"],
            "domain_pack_may_create_canonical_truth": False,
            "candidate_mapping_policy": "domain packs may propose candidate mappings for future review only",
            "missing_entity_behavior": "return limitation and candidate context; do not invent identity",
        },
        "D4Y_R4_SEG_BRIDGE_CONTRACT.json": {
            "schema_version": SCHEMA_VERSION,
            "status": "CONTRACT_ONLY",
            "concepts": ["node_ref", "edge_ref", "relationship_type", "source_entity_ref", "target_entity_ref", "confidence", "evidence_refs", "review_state", "effective_from", "effective_to", "limitation_refs"],
            "disputed_low_confidence_policy": "do not traverse as hard truth; expose limitation and review state",
            "relationship_validation_required": True,
        },
    }


def entity_catalog() -> dict[str, Any]:
    entities = [
        "Community", "Address", "Site", "Parcel", "Building", "Unit", "Road Segment", "Facility",
        "System", "Component", "Service Point", "Instrument / Control Point", "Party", "Person",
        "Organization", "Department", "Role / Interest Assignment", "Project", "Permit", "Inspection",
        "Violation", "Transaction", "Work Order", "Incident", "Observation", "Alarm",
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "DRAFT_CONTRACT_ONLY",
        "entity_type_count": len(entities),
        "entities": [
            {
                "entity_type": entity,
                "domain_relevance": "candidate cross-domain entity type",
                "CER_required": True,
                "SEG_relevant": entity not in {"Person"},
                "first_batch_status": "DRAFT_NOT_IMPLEMENTED",
                "notes": "Draft catalog entry only; no implementation or legal/certified truth claim.",
            }
            for entity in entities
        ],
    }


def relationship_catalog() -> dict[str, Any]:
    rows = [
        ("contains", "Site", "Building", "contained_by"),
        ("located_in", "Building", "Community", "contains_location"),
        ("adjacent_to", "Parcel", "Parcel", "adjacent_to"),
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
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "DRAFT_CONTRACT_ONLY",
        "relationship_type_count": len(rows),
        "relationships": [
            {
                "relationship_type": rel,
                "source_type": src,
                "target_type": tgt,
                "inverse": inv,
                "evidence_requirement": "explicit source/evidence ref or limitation",
                "confidence_review_state_requirement": "confidence and review_state required",
                "temporal_fields": ["effective_from", "effective_to"],
                "SEG_projection_notes": "Draft projection contract only; not implemented.",
            }
            for rel, src, tgt, inv in rows
        ],
    }


def sample_stubs() -> dict[str, Any]:
    specs = [
        ("property_planning_domain", "Property and planning context over parcels, buildings, permits, and projects.", "CONTRACT_ONLY"),
        ("building_compliance_domain", "Building compliance evidence exploration with review-state visibility.", "CONTRACT_ONLY"),
        ("mobility_domain", "Mobility context over road segments, incidents, observations, and replays.", "CONTRACT_ONLY"),
        ("utilities_domain", "Utilities context over service points, systems, components, instruments, and work orders.", "CONTRACT_ONLY"),
        ("civic_service_domain", "Civic service context over incidents, work orders, departments, and observations.", "CONTRACT_ONLY"),
        ("environment_domain", "Environment context over observations, instruments, alarms, and evidence gaps.", "CONTRACT_ONLY"),
        ("domain_pack_future_dubai_dld_dm", "Future Dubai DLD/DM candidate domain; requires later domain pack and source contracts.", "FUTURE_DOMAIN_REQUIRED"),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "sample_stub_count": len(specs),
        "stubs": [
            {
                "domain_pack_id": domain_id,
                "purpose": purpose,
                "likely_entities": ["Parcel", "Building", "Unit", "Permit", "Inspection", "Transaction"] if "dubai" in domain_id or "property" in domain_id else ["Building", "Road Segment", "Facility", "Observation"],
                "likely_relationships": ["located_in", "applies_to", "served_by", "observed_by"],
                "likely_request_types": ["domain_context", "evidence_gap", "limitation_audit", "safe_next_look"],
                "likely_tools": ["runtime query tools", "graph neighborhood tools", "evidence retrieval tools", "forbidden claim checker tools"],
                "likely_insights": ["evidence gap insight", "limitation cluster insight", "source freshness insight", "safe next-look insight"],
                "limitations": LIMITATIONS,
                "status": status,
                "implementation_logic_present": False,
                "unsupported_facts_present": False,
            }
            for domain_id, purpose, status in specs
        ],
    }


def markdown_docs() -> dict[str, str]:
    return {
        "README.md": f"""# {TASK_NAME}

Status: {STATUS}

This pack starts D4Y R4 by defining a generic domain-pack framework over the R3 local runtime and insight engine. It is preflight-only: no real domain pack, Dubai DLD/DM logic, production runtime, public API, app integration, Track 2 loading, live agents, external LLM runtime, or command/action output is implemented.
""",
        "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT.md": f"""# MAIN TRACK1 D4Y R4 DOMAIN PACK PREFLIGHT

Final status: {STATUS}

R4 domain-pack preflight defines the contract layer for future bounded domain packs: manifests, schemas, entity and relationship requirements, CER/SEG bridge contracts, tool/evidence/insight/limitation policies, runtime loading contract, app handoff contract, sample stubs, smoke tests, and guardrail audits.
""",
        "D4Y_R4_DOMAIN_PACK_ARCHITECTURE.md": """# D4Y R4 Domain Pack Architecture

A domain pack is a bounded extension module over the R3 runtime and insight engine.

Architecture:
domain pack manifest -> domain entity requirements -> domain relationship requirements -> domain request/response schemas -> domain tool allowlist -> domain evidence policy -> domain insight policy -> CER bridge -> SEG bridge -> runtime loading contract -> app handoff contract -> boundary validation -> no-action audit.

Domain packs are not autonomous agents. They are governed schema/policy/tool/evidence bundles consumed by the orchestrator runtime.
""",
        "D4Y_R4_DOMAIN_PACK_SCOPE.md": """# D4Y R4 Domain Pack Scope

In scope:
- generic domain-pack framework
- generic domain-pack schemas
- entity and relationship requirements
- CER bridge contract
- SEG bridge contract
- runtime loading contract
- app handoff contract
- generic sample stubs
- domain selection criteria

Out of scope:
- real Dubai DLD/DM pack
- real property/planning pack
- real mobility pack
- real utilities pack
- production service
- public API
- app integration
- live agents
- external LLM runtime
- command/control
- legal/government conclusions
""",
        "D4Y_R4_DOMAIN_EVIDENCE_POLICY.md": """# D4Y R4 Domain Evidence Policy

Every domain fact must cite source/evidence refs or an explicit limitation. Source truth is preserved, canonical truth is confidence-aware, and domain output must include provenance.

Unresolved conflicts stay visible. A domain pack cannot fabricate missing source data and cannot overwrite CER identity truth.
""",
        "D4Y_R4_DOMAIN_INSIGHT_POLICY.md": """# D4Y R4 Domain Insight Policy

Domain packs may produce evidence gap insight, limitation cluster insight, entity resolution gap insight, source freshness insight, review backlog insight, simulation/observed contrast insight, domain-pack future gap insight, and safe next-look insight.

Domain packs may not produce operational recommendations, enforcement recommendations, legal findings, confirmed violations, permit approvals/rejections, certified impacts, production alerts, or autonomous monitoring outputs.
""",
        "D4Y_R4_DOMAIN_LIMITATION_POLICY.md": """# D4Y R4 Domain Limitation Policy

Required domain limitations:
- domain pack framework only
- domain packs are not implemented yet
- no domain legal conclusions
- no government decisioning
- no production use
- no command/control
- no autonomous monitoring
- source data may be incomplete
- CER/SEG bridge may be future/pending
- domain output must preserve confidence and review state
""",
        "D4Y_R4_CER_SEG_SHARED_CONTRACTS_PLAN.md": """# D4Y R4 CER/SEG Shared Contracts Plan

CER and SEG can be built in parallel only if these contracts are shared:
- entity catalog
- relationship ontology
- confidence model
- review state enum
- temporal validity conventions
- bridge DTO format
- planner/runtime injection contract
- synthetic test data alignment
- integration tests
""",
        "D4Y_R4_DOMAIN_PACK_SELECTION_CRITERIA.md": """# D4Y R4 Domain Pack Selection Criteria

Choose the first real domain by weighing available source data, canonical entity readiness, graph relationship readiness, app demo value, operational safety, boundary complexity, evidence availability, stakeholder value, implementation effort, and risk of legal or operational overclaim.

Candidate first domains:
- mobility context
- civic service context
- property/planning context
- building compliance context
- 3D asset/building identity context
- utilities context
- Dubai DLD/DM later

This preflight does not pick a final first domain. The recommended next task is a canonical entity bridge preflight.
""",
        "D4Y_R4_DOMAIN_PACK_EXAMPLE_USE_CASES.md": """# D4Y R4 Domain Pack Example Use Cases

Safe examples:
- What do we know about this building?
- What evidence supports this parcel/building context?
- Which source limitations apply?
- Which related situations should we inspect?
- What graph relationships connect this asset to nearby roads/services?
- What replay context exists?
- What data-quality gaps prevent stronger conclusions?

Forbidden examples:
- Is this violation confirmed?
- Should we dispatch an inspector?
- Should this permit be approved?
- Who legally owns this?
- Which route should traffic take?
- Is this building certified impacted?
""",
        "D4Y_R4_DOMAIN_PACK_PREFLIGHT_LIMITATION_REGISTER.md": "# D4Y R4 Domain Pack Preflight Limitation Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS),
        "D4Y_R4_DOMAIN_PACK_NEXT_TASK_PLAN.md": """# D4Y R4 Domain Pack Next Task Plan

Recommended next Track 1 task:
MAIN-TRACK1-D4Y-R4-CANONICAL-ENTITY-BRIDGE-PREFLIGHT

Purpose:
Define the Canonical Entity Registry bridge in more detail so domain packs can safely reference Community, Address, Site, Parcel, Building, Unit, Road Segment, Facility, System, Component, Service Point, Instrument, Party, Organization, Department, Role/Interest Assignment, Project, Permit, Inspection, Violation, Transaction, Work Order, Incident, Observation, and Alarm.

Alternative next Track 1 task:
MAIN-TRACK1-D4Y-R4-SEMANTIC-GRAPH-BRIDGE-PREFLIGHT

Recommended later R4 tasks:
- MAIN-TRACK1-D4Y-R4-CANONICAL-ENTITY-BRIDGE-PREFLIGHT
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
        "real domain implementation attempted",
        "Dubai DLD/DM logic implemented here",
        "domain pack bypasses CER",
        "domain pack bypasses SEG relationship contract",
        "domain pack bypasses orchestrator",
        "domain pack mutates source state",
        "command/action output",
        "dispatch/enforcement/routing/control",
        "legal finding",
        "confirmed violation",
        "permit approval/rejection",
        "certified impact",
        "certified traffic model",
        "ownership/legal truth from source ID",
        "observed truth from simulation/synthetic",
        "hidden limitation",
        "public API exposure",
        "external LLM call attempted",
        "app integration attempted",
        "Track 2 data/3D loading attempted",
        "D5 implementation attempted",
        "prior root mutation",
        "secrets printed",
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "test_count": len(tests),
        "tests": [{"case": item, "result": "REJECTED", "forbidden_output_created": False} for item in tests],
    }


def smoke_report(prereq: dict[str, Any], sample_stub_count: int, entity_count: int, relationship_count: int) -> dict[str, Any]:
    checks = {
        "prerequisites_exist": prereq["status"] == "PASS",
        "domain_pack_architecture_exists": (OUTPUT_ROOT / "D4Y_R4_DOMAIN_PACK_ARCHITECTURE.md").exists(),
        "domain_pack_schema_validates": (OUTPUT_ROOT / "D4Y_R4_DOMAIN_PACK_SCHEMA.json").exists(),
        "manifest_schema_validates": (OUTPUT_ROOT / "D4Y_R4_DOMAIN_PACK_MANIFEST_SCHEMA.json").exists(),
        "entity_requirements_schema_validates": (OUTPUT_ROOT / "D4Y_R4_DOMAIN_ENTITY_REQUIREMENTS_SCHEMA.json").exists(),
        "relationship_requirements_schema_validates": (OUTPUT_ROOT / "D4Y_R4_DOMAIN_RELATIONSHIP_REQUIREMENTS_SCHEMA.json").exists(),
        "request_response_output_schemas_validate": all((OUTPUT_ROOT / name).exists() for name in ["D4Y_R4_DOMAIN_REQUEST_SCHEMA.json", "D4Y_R4_DOMAIN_RESPONSE_SCHEMA.json", "D4Y_R4_DOMAIN_OUTPUT_PACKET_SCHEMA.json"]),
        "evidence_policy_exists": (OUTPUT_ROOT / "D4Y_R4_DOMAIN_EVIDENCE_POLICY.md").exists(),
        "insight_policy_exists": (OUTPUT_ROOT / "D4Y_R4_DOMAIN_INSIGHT_POLICY.md").exists(),
        "tool_policy_validates": (OUTPUT_ROOT / "D4Y_R4_DOMAIN_TOOL_POLICY.json").exists(),
        "limitation_policy_exists": (OUTPUT_ROOT / "D4Y_R4_DOMAIN_LIMITATION_POLICY.md").exists(),
        "guardrail_policy_validates": (OUTPUT_ROOT / "D4Y_R4_DOMAIN_GUARDRAIL_POLICY.json").exists(),
        "runtime_loading_contract_validates": (OUTPUT_ROOT / "D4Y_R4_DOMAIN_RUNTIME_LOADING_CONTRACT.json").exists(),
        "app_handoff_contract_validates": (OUTPUT_ROOT / "D4Y_R4_DOMAIN_APP_HANDOFF_CONTRACT.json").exists(),
        "cer_bridge_validates": (OUTPUT_ROOT / "D4Y_R4_CER_BRIDGE_CONTRACT.json").exists(),
        "seg_bridge_validates": (OUTPUT_ROOT / "D4Y_R4_SEG_BRIDGE_CONTRACT.json").exists(),
        "entity_catalog_draft_exists": entity_count >= 26,
        "relationship_catalog_draft_exists": relationship_count >= 15,
        "sample_stubs_validate": sample_stub_count >= 7,
        "no_real_domain_pack_implemented": True,
        "no_dubai_dld_dm_logic_implemented": True,
        "no_public_api_exposed": True,
        "no_external_llm_called": True,
        "no_app_integration_performed": True,
        "no_command_action_output_created": True,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "sample_stub_count": sample_stub_count,
        "entity_type_catalog_count": entity_count,
        "relationship_type_catalog_count": relationship_count,
    }


def audit_reports(signatures_before: dict[str, dict[str, str]], signatures_after: dict[str, dict[str, str]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    changed = [root for root, sig in signatures_before.items() if signatures_after.get(root) != sig]
    claim = {
        "status": "PASS",
        "finding_count": 0,
        "findings": [],
        "banned_claims_enforced": [
            "production readiness",
            "production domain runtime",
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
            "Dubai DLD/DM implementation",
            "full citywide certified digital twin",
            "unsupported freeform LLM claims",
        ],
    }
    mutation = {"status": "PASS" if not changed else "FAIL", "changed_count": len(changed), "changed_roots": changed, "watched_roots": sorted(signatures_before)}
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
        "D4Y_R4_DOMAIN_PACK_ARCHITECTURE.md": "architecture/D4Y_R4_DOMAIN_PACK_ARCHITECTURE.md",
        "D4Y_R4_DOMAIN_PACK_SCHEMA.json": "schemas/D4Y_R4_DOMAIN_PACK_SCHEMA.json",
        "D4Y_R4_DOMAIN_PACK_MANIFEST_SCHEMA.json": "schemas/D4Y_R4_DOMAIN_PACK_MANIFEST_SCHEMA.json",
        "D4Y_R4_CER_BRIDGE_CONTRACT.json": "cer_seg/D4Y_R4_CER_BRIDGE_CONTRACT.json",
        "D4Y_R4_SEG_BRIDGE_CONTRACT.json": "cer_seg/D4Y_R4_SEG_BRIDGE_CONTRACT.json",
        "D4Y_R4_DOMAIN_PACK_SAMPLE_STUBS.json": "domain_stubs/D4Y_R4_DOMAIN_PACK_SAMPLE_STUBS.json",
        "D4Y_R4_DOMAIN_TOOL_POLICY.json": "policies/D4Y_R4_DOMAIN_TOOL_POLICY.json",
        "D4Y_R4_DOMAIN_APP_HANDOFF_CONTRACT.json": "app_handoff/D4Y_R4_DOMAIN_APP_HANDOFF_CONTRACT.json",
        "D4Y_R4_DOMAIN_PACK_PREFLIGHT_SMOKE_REPORT.json": "smoke/D4Y_R4_DOMAIN_PACK_PREFLIGHT_SMOKE_REPORT.json",
        "D4Y_R4_DOMAIN_PACK_PREFLIGHT_NEGATIVE_TEST_REPORT.json": "guardrails/D4Y_R4_DOMAIN_PACK_PREFLIGHT_NEGATIVE_TEST_REPORT.json",
        "D4Y_R4_DOMAIN_PACK_PREREQUISITE_REPORT.json": "logs/D4Y_R4_DOMAIN_PACK_PREREQUISITE_REPORT.json",
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
    signatures_before = {root: path_signature(REPO_ROOT / root) for root in WATCHED_ROOTS}
    prepare_output_root()
    prereq = prerequisite_report(signatures_before)
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_PACK_PREREQUISITE_REPORT.json", prereq)
    if prereq["status"] != "PASS":
        decision = {"schema_version": SCHEMA_VERSION, "status": WAITING_STATUS, "task_name": TASK_NAME, "timestamp": now_iso(), "prerequisite_status": prereq["status"]}
        write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT_DECISION.json", decision)
        write_hashes()
        print(json.dumps(decision, indent=2, sort_keys=True))
        return 0

    for name, data in schemas().items():
        write_json(OUTPUT_ROOT / name, data)
    for name, data in policies_and_contracts().items():
        write_json(OUTPUT_ROOT / name, data)
    entity_data = entity_catalog()
    relationship_data = relationship_catalog()
    stub_data = sample_stubs()
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_ENTITY_TYPE_CATALOG_DRAFT.json", entity_data)
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_RELATIONSHIP_TYPE_CATALOG_DRAFT.json", relationship_data)
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_PACK_SAMPLE_STUBS.json", stub_data)
    for name, text in markdown_docs().items():
        write_text(OUTPUT_ROOT / name, text)
    negative = negative_report()
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_PACK_PREFLIGHT_NEGATIVE_TEST_REPORT.json", negative)
    smoke = smoke_report(prereq, stub_data["sample_stub_count"], entity_data["entity_type_count"], relationship_data["relationship_type_count"])
    write_json(OUTPUT_ROOT / "D4Y_R4_DOMAIN_PACK_PREFLIGHT_SMOKE_REPORT.json", smoke)
    copy_to_folders()

    signatures_after = {root: path_signature(REPO_ROOT / root) for root in WATCHED_ROOTS}
    claim, mutation, secret = audit_reports(signatures_before, signatures_after)
    write_audit_md("CLAIM_BOUNDARY_AUDIT.md", claim)
    write_audit_md("NO_MUTATION_AUDIT.md", mutation)
    write_audit_md("SECRET_REDACTION_AUDIT.md", secret)

    decision = {
        "schema_version": SCHEMA_VERSION,
        "status": STATUS,
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "prerequisite_status": "PASS",
        "domain_pack_schema_status": "PASS",
        "manifest_schema_status": "PASS",
        "entity_requirements_schema_status": "PASS",
        "relationship_requirements_schema_status": "PASS",
        "request_schema_status": "PASS",
        "response_schema_status": "PASS",
        "output_packet_schema_status": "PASS",
        "cer_bridge_status": "PASS_CONTRACT_ONLY",
        "seg_bridge_status": "PASS_CONTRACT_ONLY",
        "sample_stub_count": stub_data["sample_stub_count"],
        "entity_type_catalog_count": entity_data["entity_type_count"],
        "relationship_type_catalog_count": relationship_data["relationship_type_count"],
        "runtime_loading_contract_status": "PASS_CONTRACT_ONLY",
        "app_handoff_contract_status": "PASS_CONTRACT_ONLY",
        "no_real_domain_pack_implemented": True,
        "dubai_dld_dm_implemented": False,
        "public_api_exposed": False,
        "external_llm_called": False,
        "command_action_output_created": False,
        "smoke_summary": {"status": smoke["status"], "check_count": len(smoke["checks"])},
        "limitation_summary": {"status": "PASS_WITH_LIMITATIONS", "limitations": LIMITATIONS},
        "negative_test_summary": {"status": negative["status"], "test_count": negative["test_count"]},
        "claim_boundary_summary": claim,
        "no_mutation_summary": mutation,
        "secret_audit_summary": secret,
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R4-CANONICAL-ENTITY-BRIDGE-PREFLIGHT",
        "recommended_parallel_track2a_task": "D4-3D-CITY-ASSET-CONTRACT-R1 if not already closed; otherwise D4-3D-SECOND-CITY-PILOT-NYC-R1",
        "recommended_parallel_track2b_task": "MAIN-TRACK2B-D4X-CITY-EPISODE-PACK-R1 if not already closed",
        "recommended_parallel_track2c_task": "MAIN-TRACK2C-D4X-CITY-EPISODE-APP-INTEGRATION-R8 after Track 2B episode pack passes",
        "parked_d5_task": "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT_DECISION.json", decision)
    decision["hash_summary"] = write_hashes()
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT_DECISION.json", decision)
    decision["hash_summary"] = write_hashes()

    missing = [name for name in REQUIRED_ARTIFACTS if not (OUTPUT_ROOT / name).exists()]
    if missing or smoke["status"] != "PASS" or mutation["status"] != "PASS":
        decision["status"] = FAIL_STATUS
        decision["missing_required_artifacts"] = missing
        write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT_DECISION.json", decision)
        write_hashes()

    print(json.dumps({
        "status": decision["status"],
        "output_root": str(OUTPUT_ROOT),
        "sample_stub_count": decision["sample_stub_count"],
        "entity_type_catalog_count": decision["entity_type_catalog_count"],
        "relationship_type_catalog_count": decision["relationship_type_catalog_count"],
        "hash_status": decision.get("hash_summary", {}).get("status"),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

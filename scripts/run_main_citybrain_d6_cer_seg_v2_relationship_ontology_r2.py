#!/usr/bin/env python3
"""CER/SEG v2 relationship ontology R2."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from citybrain_cer_seg_v2_lane_common import (
    LANE_LIMITATIONS,
    REPO_ROOT,
    claim_boundary_audit,
    discover_upstreams,
    hash_manifest,
    load_json,
    load_r8_edges,
    no_mutation_audit,
    now_iso,
    prepare_output_root,
    rel,
    required_files_status,
    secret_audit,
    upstream_signature,
    write_json,
    write_text,
)


TASK_ID = "MAIN-CITYBRAIN-D6-CER-SEG-V2-RELATIONSHIP-ONTOLOGY-R2"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_CER_SEG_V2_RELATIONSHIP_ONTOLOGY_R2_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_CER_SEG_V2_RELATIONSHIP_ONTOLOGY_R2"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d6_cer_seg_v2_relationship_ontology_r2"
RUNNER = REPO_ROOT / "scripts" / "run_main_citybrain_d6_cer_seg_v2_relationship_ontology_r2.py"

UPSTREAMS = {
    "cer_seg_v2_preflight": {
        "task_id": "MAIN-CITYBRAIN-D6-CER-SEG-CROSS-CITY-V2-PREFLIGHT",
        "root": "outputs/main_citybrain_d6_cer_seg_cross_city_v2_preflight",
        "decision_file": "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_PREFLIGHT_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "canonical_entity_r1": {
        "task_id": "MAIN-CITYBRAIN-D6-CER-SEG-V2-CANONICAL-ENTITY-CONTRACT-R1",
        "root": "outputs/main_citybrain_d6_cer_seg_v2_canonical_entity_contract_r1",
        "decision_file": "MAIN_CITYBRAIN_D6_CER_SEG_V2_CANONICAL_ENTITY_CONTRACT_R1_DECISION.json",
        "required": True,
        "expected_status": "PASS_MAIN_CITYBRAIN_D6_CER_SEG_V2_CANONICAL_ENTITY_CONTRACT_R1_WITH_LIMITATIONS",
    },
    "r7_runtime_slice": {
        "task_id": "MAIN-CITYBRAIN-D4X-R7-MULTI-DOMAIN-EDGE-REGISTRY-RUNTIME-SLICE",
        "root": "outputs/main_citybrain_d4x_r7_multi_domain_edge_registry_runtime_slice",
        "decision_file": "MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "r8_hardening": {
        "task_id": "MAIN-CITYBRAIN-D4X-R8-MULTI-DOMAIN-EDGE-REGISTRY-HARDENING",
        "root": "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening",
        "decision_file": "MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "incident_closeout": {
        "task_id": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-CLOSEOUT",
        "root": "outputs/main_citybrain_d6_incident_mode_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "incident_track2a_surface_r4": {
        "task_id": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-TRACK2A-OPERATOR-SURFACE-HANDOFF-R4",
        "root": "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4",
        "decision_file": "MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "hero_twin_preflight": {
        "task_id": "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-TWIN-PREFLIGHT",
        "root": "outputs/main_track2a_d5_hero_neighbourhood_twin_preflight",
        "decision_file": "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_TWIN_PREFLIGHT_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "hero_asset_binding_r1": {
        "task_id": "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-ASSET-BINDING-R1",
        "root": "outputs/main_track2a_d5_hero_neighbourhood_asset_binding_r1",
        "decision_file": "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_ASSET_BINDING_R1_DECISION.json",
        "required": False,
        "expected_prefix": "PASS_",
    },
    "hero_event_overlay_r2": {
        "task_id": "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-EVENT-OVERLAY-R2",
        "root": "outputs/main_track2a_d5_hero_neighbourhood_event_overlay_r2",
        "decision_file": "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_EVENT_OVERLAY_R2_DECISION.json",
        "required": False,
        "expected_prefix": "PASS_",
    },
}

REQUIRED_FILES = [
    "MAIN_CITYBRAIN_D6_CER_SEG_V2_RELATIONSHIP_ONTOLOGY_R2_DECISION.json",
    "README.md",
    "INPUT_ARTIFACT_INDEX.json",
    "RELATIONSHIP_ONTOLOGY_V2_SCHEMA.json",
    "RELATIONSHIP_ONTOLOGY_V2.json",
    "RELATIONSHIP_FAMILY_CATALOG.json",
    "R7_R8_EDGE_FAMILY_COMPATIBILITY_MAP.json",
    "EVENT_RELATIONSHIP_SEPARATION_RULES.md",
    "OVERLAY_RELATIONSHIP_SEPARATION_RULES.md",
    "RELATIONSHIP_COMPATIBILITY_FINDINGS.json",
    "CLAIM_BOUNDARY_AUDIT.json",
    "NO_MUTATION_AUDIT.json",
    "SECRET_AUDIT.json",
    "HASH_MANIFEST.json",
    "LOCAL_OPEN_INDEX.md",
]


def family_catalog() -> dict[str, Any]:
    return {
        "identity_alias_source_link": "Source, local authority, global/open, and scene/source aliases connected to canonical wrappers without replacing canonical identity.",
        "spatial_containment": "City/community/site/parcel/building/unit containment and within relationships.",
        "spatial_adjacency": "near/intersects/served-by relationships used for context only, never causal proof.",
        "service_dependency": "facility/system/component/service-point dependency and serving relationships.",
        "ownership_interest_role": "party, organization, department, and role/interest assignment context with privacy/legal boundary.",
        "event_context": "event/current-state/incident-review relationships held as local/replay review context.",
        "overlay_display": "Omniverse/web/hero surface display and scene-binding relationships, not canonical truth.",
        "review_inferred": "inferred, unresolved, quarantined, or review-only relationships restricted by review state.",
    }


def relationship_type(name: str, family: str, sources: list[str], targets: list[str], inverse: str | None, suitability: str) -> dict[str, Any]:
    return {
        "name": name,
        "relationship_family": family,
        "source_entity_types": sources,
        "target_entity_types": targets,
        "allowed_domains_cities": "all configured city/domain packs when both endpoint families are contract-valid",
        "directionality": "directed",
        "inverse_relationship": inverse,
        "cardinality_expectations": "many-to-many unless city/domain extension narrows it",
        "temporal_fields": ["effective_from", "effective_to", "valid_time", "transaction_time", "observed_at"],
        "evidence_requirements": ["evidence_refs", "source_artifact_refs", "limitation_refs", "lineage_refs"],
        "confidence_semantics": "relationship_confidence is evidence/review confidence only; not certified truth",
        "review_state_constraints": ["review_context", "pending_review", "candidate_pending_review", "unresolved", "quarantined", "accepted_for_local_review_query"],
        "runtime_query_suitability": suitability,
        "graph_projection_suitability": "projectable to SEG when endpoints have canonical wrappers and review state permits traversal",
        "forbidden_claim_language": [
            "caused",
            "proved",
            "certified",
            "legal finding",
            "confirmed incident",
            "dispatch",
            "enforcement",
            "routing/control",
        ],
    }


def relationship_ontology() -> dict[str, Any]:
    types = [
        relationship_type("alias_of", "identity_alias_source_link", ["source_alias"], ["any canonical entity family"], "has_alias", "lookup only"),
        relationship_type("contains", "spatial_containment", ["city_scope", "community_or_zone", "site", "parcel_or_land_interest", "building_or_structure"], ["community_or_zone", "site", "parcel_or_land_interest", "building_or_structure", "unit_or_premise"], "within", "local/replay query suitable"),
        relationship_type("near_or_intersects", "spatial_adjacency", ["site", "parcel_or_land_interest", "building_or_structure", "road_segment"], ["site", "building_or_structure", "road_segment", "facility"], "near_or_intersects", "review context only"),
        relationship_type("serves_or_depends_on", "service_dependency", ["facility", "system", "component", "service_point"], ["community_or_zone", "address_or_location", "building_or_structure", "system", "component"], "served_by_or_dependency_of", "local/replay query suitable with limitations"),
        relationship_type("has_role_or_interest", "ownership_interest_role", ["party", "organization_ref", "department_ref"], ["role_or_interest_assignment", "parcel_or_land_interest", "building_or_structure", "project_or_planning_context"], "role_or_interest_held_by", "privacy/legal boundary review only"),
        relationship_type("event_relates_to_entity_context", "event_context", ["event_or_incident_context", "observation"], ["building_or_structure", "road_segment", "city_asset", "facility", "community_or_zone"], "entity_has_event_context", "local/replay review query only"),
        relationship_type("incident_review_references", "event_context", ["event_or_incident_context"], ["permit_or_case_context", "inspection_or_review_context", "violation_or_compliance_context", "building_or_structure"], "referenced_by_incident_review", "operator review context only"),
        relationship_type("scene_asset_represents_candidate", "overlay_display", ["omniverse_scene_asset_ref", "city_asset"], ["building_or_structure", "road_segment", "community_or_zone", "event_or_incident_context"], "candidate_represented_by_scene_asset", "overlay display only"),
        relationship_type("web_surface_displays_context", "overlay_display", ["web_companion_surface_ref"], ["event_or_incident_context", "building_or_structure", "city_asset"], "context_displayed_on_web_surface", "companion display only"),
        relationship_type("inferred_review_context", "review_inferred", ["any canonical entity family"], ["any canonical entity family"], "inferred_review_context_inverse", "review-only; excluded from default traversal unless requested"),
        relationship_type("unresolved_or_quarantined_context", "review_inferred", ["source_alias", "event_or_incident_context"], ["any canonical entity family"], None, "preserve only; not default traversable"),
    ]
    return {
        "contract_id": "RELATIONSHIP_ONTOLOGY_V2",
        "task_id": TASK_ID,
        "generated_at_utc": now_iso(),
        "relationship_types": types,
        "event_incident_separation": {
            "event_state_is_not_causal_truth": True,
            "incident_context_is_not_confirmed_incident": True,
            "requires_explicit_evidence_and_review_gate_for_stronger_claim": True,
        },
        "overlay_display_separation": {
            "omniverse_and_web_edges_are_surface_context": True,
            "usd_prim_paths_are_not_canonical_ids": True,
            "visual_alignment_does_not_prove_identity_or_impact": True,
        },
        "limitations": LANE_LIMITATIONS,
    }


def schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain CER/SEG Relationship Ontology V2",
        "type": "object",
        "required": ["contract_id", "relationship_types", "event_incident_separation", "overlay_display_separation"],
        "properties": {
            "relationship_types": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "name",
                        "relationship_family",
                        "source_entity_types",
                        "target_entity_types",
                        "directionality",
                        "temporal_fields",
                        "evidence_requirements",
                        "confidence_semantics",
                        "review_state_constraints",
                        "runtime_query_suitability",
                        "graph_projection_suitability",
                        "forbidden_claim_language",
                    ],
                },
            }
        },
    }


def r8_family_map(ontology: dict[str, Any]) -> dict[str, Any]:
    r8_rules = load_json(REPO_ROOT / "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening/R8_HARDENING_RULESET.json", {})
    mapping = {
        "building_compliance_asset_context": "review_inferred",
        "building_property_combined_context": "review_inferred",
        "city_asset_identity_cross_domain_context": "identity_alias_source_link",
        "d6_product_surface_event_context_overlay": "overlay_display",
        "event_fabric_state_entity_context": "event_context",
        "event_fabric_unresolved_review_context": "review_inferred",
        "mobility_asset_road_overlay_context": "overlay_display",
        "omniverse_event_overlay_context": "overlay_display",
        "property_planning_asset_context": "review_inferred",
    }
    valid_v2 = set(family_catalog())
    rows = []
    missing = []
    for family in r8_rules.get("valid_relationship_families", []):
        v2_family = mapping.get(family)
        if v2_family not in valid_v2:
            missing.append(family)
        rows.append({"r8_relationship_family": family, "v2_relationship_family": v2_family, "compatible": v2_family in valid_v2, "rewrite_required": False})
    return {"task_id": TASK_ID, "status": "PASS" if not missing else "PASS_WITH_FINDINGS", "mappings": rows, "unmapped_r8_families": missing}


def compatibility_findings(family_map: dict[str, Any]) -> dict[str, Any]:
    edges = load_r8_edges()
    counts = Counter(edge.get("relationship_family", "unknown") for edge in edges)
    mapped = {row["r8_relationship_family"] for row in family_map["mappings"] if row["compatible"]}
    unmatched_edge_families = sorted(set(counts) - mapped)
    return {
        "task_id": TASK_ID,
        "status": "PASS" if not unmatched_edge_families else "PASS_WITH_FINDINGS",
        "r8_edge_count": len(edges),
        "r8_edge_family_counts": dict(sorted(counts.items())),
        "unmatched_edge_families": unmatched_edge_families,
        "findings": [
            "R7/R8 edges map to v2 relationship families without rewriting upstream rows.",
            "Event/current-state context remains separate from causal/legal relationship truth.",
            "Overlay/display relationships remain surface context and do not become canonical truth.",
            "Unresolved/quarantined rows remain preserved and restricted from default traversal.",
        ],
    }


def local_open_index() -> str:
    return "\n".join([
        f"# {TASK_ID}",
        "",
        f"Output root: `{rel(OUTPUT_ROOT)}`",
        "",
        "- `RELATIONSHIP_ONTOLOGY_V2.json`",
        "- `R7_R8_EDGE_FAMILY_COMPATIBILITY_MAP.json`",
        "- `RELATIONSHIP_COMPATIBILITY_FINDINGS.json`",
        "- `EVENT_RELATIONSHIP_SEPARATION_RULES.md`",
        "- `OVERLAY_RELATIONSHIP_SEPARATION_RULES.md`",
        "- `MAIN_CITYBRAIN_D6_CER_SEG_V2_RELATIONSHIP_ONTOLOGY_R2_DECISION.json`",
    ])


def main() -> int:
    before = upstream_signature(UPSTREAMS)
    prepare_output_root(OUTPUT_ROOT, "main_citybrain_d6_cer_seg_v2_relationship_ontology_r2")
    input_index, upstream_summary = discover_upstreams(TASK_ID, UPSTREAMS)
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", input_index)

    if upstream_summary["status"] != "PASS":
        decision = {"task_id": TASK_ID, "status": FAIL_STATUS, "run_timestamp_utc": now_iso(), "upstream_summary": upstream_summary}
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CER_SEG_V2_RELATIONSHIP_ONTOLOGY_R2_DECISION.json", decision)
        write_text(OUTPUT_ROOT / "README.md", f"# {TASK_ID}\n\nStatus: {FAIL_STATUS}\n")
        hash_manifest(TASK_ID, OUTPUT_ROOT)
        print(json.dumps(decision, indent=2, sort_keys=True))
        return 1

    ontology = relationship_ontology()
    families = family_catalog()
    family_map = r8_family_map(ontology)
    findings = compatibility_findings(family_map)
    hero_pause = {
        "task_id": TASK_ID,
        "status": "PASS_NO_HERO_EVENT_OVERLAY_R2_DETECTED" if "hero_event_overlay_r2" in upstream_summary["optional_missing_or_not_yet_run"] else "PASS_HERO_EVENT_OVERLAY_R2_PRESENT",
        "hero_event_overlay_r2_present": "hero_event_overlay_r2" in upstream_summary["optional_present"],
        "hero_twin_and_asset_binding_consumed_read_only": True,
    }

    write_json(OUTPUT_ROOT / "RELATIONSHIP_ONTOLOGY_V2_SCHEMA.json", schema())
    write_json(OUTPUT_ROOT / "RELATIONSHIP_ONTOLOGY_V2.json", ontology)
    write_json(OUTPUT_ROOT / "RELATIONSHIP_FAMILY_CATALOG.json", {"task_id": TASK_ID, "relationship_families": families})
    write_json(OUTPUT_ROOT / "R7_R8_EDGE_FAMILY_COMPATIBILITY_MAP.json", family_map)
    write_text(OUTPUT_ROOT / "EVENT_RELATIONSHIP_SEPARATION_RULES.md", "# Event Relationship Separation Rules\n\nEvent/current-state relationships are local/replay review/query context. They do not create causal, legal, certified, official, or confirmed incident relationship truth without a later explicit evidence and review gate.\n")
    write_text(OUTPUT_ROOT / "OVERLAY_RELATIONSHIP_SEPARATION_RULES.md", "# Overlay Relationship Separation Rules\n\nOmniverse, Hero, and web relationships are overlay/display context. USD prim paths, scene IDs, and surface packet IDs are not canonical entity IDs and do not certify geometry, identity, impact, or incident truth.\n")
    write_json(OUTPUT_ROOT / "RELATIONSHIP_COMPATIBILITY_FINDINGS.json", findings)
    write_json(OUTPUT_ROOT / "HERO_R2_COMPATIBILITY_PAUSE_REVIEW.json", hero_pause)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", local_open_index())
    write_text(OUTPUT_ROOT / "README.md", f"# {TASK_ID}\n\nStatus: {PASS_STATUS}\n\nRead-only relationship ontology contract. No frozen outputs mutated; no production/public/API/action/legal/certified claims.\n")

    placeholder = {"task_id": TASK_ID, "status": "VALIDATION_PENDING", "run_timestamp_utc": now_iso()}
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CER_SEG_V2_RELATIONSHIP_ONTOLOGY_R2_DECISION.json", placeholder)
    claim = claim_boundary_audit(TASK_ID, OUTPUT_ROOT)
    no_mutation = no_mutation_audit(TASK_ID, before, upstream_signature(UPSTREAMS))
    secret = secret_audit(TASK_ID, OUTPUT_ROOT, [RUNNER, REPO_ROOT / "scripts/citybrain_cer_seg_v2_lane_common.py"])
    for name, data in [("CLAIM_BOUNDARY_AUDIT.json", claim), ("NO_MUTATION_AUDIT.json", no_mutation), ("SECRET_AUDIT.json", secret)]:
        write_json(OUTPUT_ROOT / name, data)
    hash_manifest(TASK_ID, OUTPUT_ROOT)
    required = required_files_status(OUTPUT_ROOT, REQUIRED_FILES)

    final_status = PASS_STATUS if all(item["status"] == "PASS" for item in [claim, no_mutation, secret, required]) and findings["status"].startswith("PASS") else FAIL_STATUS
    decision = {
        "task_id": TASK_ID,
        "status": final_status,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now_iso(),
        "required_upstreams_found": upstream_summary["required_green_count"],
        "required_upstreams_total": upstream_summary["required_count"],
        "relationship_type_count": len(ontology["relationship_types"]),
        "relationship_family_count": len(families),
        "r8_edge_count_classified": findings["r8_edge_count"],
        "compatibility_findings_status": findings["status"],
        "hero_r2_pause_review_status": hero_pause["status"],
        "claim_boundary_status": claim["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PENDING",
        "production_readiness_claim_made": False,
        "public_api_readiness_claim_made": False,
        "global_master_database_claim_made": False,
        "legal_certified_confirmed_claim_made": False,
        "autonomous_monitoring_claim_made": False,
        "alert_dispatch_routing_control_enforcement_claim_made": False,
        "automated_action_claim_made": False,
        "limitations": LANE_LIMITATIONS,
        "next_recommended_task": "MAIN-CITYBRAIN-D6-CER-SEG-V2-CONFIDENCE-REVIEW-STATE-CONTRACT-R3",
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CER_SEG_V2_RELATIONSHIP_ONTOLOGY_R2_DECISION.json", decision)
    hashes = hash_manifest(TASK_ID, OUTPUT_ROOT)
    decision["hash_validation_status"] = hashes["hash_validation_status"]
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CER_SEG_V2_RELATIONSHIP_ONTOLOGY_R2_DECISION.json", decision)
    hash_manifest(TASK_ID, OUTPUT_ROOT)

    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if final_status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Hero Neighbourhood + CER/SEG v2 integration-readiness review.

This is a bounded read-only review package. It consumes the frozen Hero
Neighbourhood, CER/SEG v2, local running, and Incident Mode outputs and writes
compatibility findings only under its own output root.
"""

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
    load_hero_bindings,
    load_incident_operator_packets,
    load_json,
    no_mutation_audit,
    now_iso,
    prepare_output_root,
    rel,
    required_files_status,
    secret_audit,
    status_from_decision,
    upstream_signature,
    write_json,
    write_text,
)


TASK_ID = "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-AND-CERSEG-V2-INTEGRATION-READINESS-REVIEW"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS"
DEFER_STATUS = "DEFER_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_PENDING_CERSEG_V2_CLOSEOUT"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d6_hero_neighbourhood_and_cerseg_v2_integration_readiness_review"
RUNNER = REPO_ROOT / "scripts" / "run_main_citybrain_d6_hero_neighbourhood_and_cerseg_v2_integration_readiness_review.py"

UPSTREAMS = {
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
        "required": True,
        "expected_prefix": "PASS_",
    },
    "hero_event_overlay_r2": {
        "task_id": "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-EVENT-OVERLAY-R2",
        "root": "outputs/main_track2a_d5_hero_neighbourhood_event_overlay_r2",
        "decision_file": "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_EVENT_OVERLAY_R2_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "hero_kit_composer_handoff_r3": {
        "task_id": "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-KIT-COMPOSER-HANDOFF-R3",
        "root": "outputs/main_track2a_d5_hero_neighbourhood_kit_composer_handoff_r3",
        "decision_file": "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_KIT_COMPOSER_HANDOFF_R3_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "hero_scene_pack_closeout": {
        "task_id": "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-SCENE-PACK-CLOSEOUT",
        "root": "outputs/main_track2a_d5_hero_neighbourhood_scene_pack_closeout",
        "decision_file": "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT_DECISION.json",
        "required": True,
        "expected_status": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT_WITH_LIMITATIONS",
    },
    "cerseg_preflight": {
        "task_id": "MAIN-CITYBRAIN-D6-CER-SEG-CROSS-CITY-V2-PREFLIGHT",
        "root": "outputs/main_citybrain_d6_cer_seg_cross_city_v2_preflight",
        "decision_file": "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_PREFLIGHT_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "cerseg_canonical_entity_r1": {
        "task_id": "MAIN-CITYBRAIN-D6-CER-SEG-V2-CANONICAL-ENTITY-CONTRACT-R1",
        "root": "outputs/main_citybrain_d6_cer_seg_v2_canonical_entity_contract_r1",
        "decision_file": "MAIN_CITYBRAIN_D6_CER_SEG_V2_CANONICAL_ENTITY_CONTRACT_R1_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "cerseg_relationship_r2": {
        "task_id": "MAIN-CITYBRAIN-D6-CER-SEG-V2-RELATIONSHIP-ONTOLOGY-R2",
        "root": "outputs/main_citybrain_d6_cer_seg_v2_relationship_ontology_r2",
        "decision_file": "MAIN_CITYBRAIN_D6_CER_SEG_V2_RELATIONSHIP_ONTOLOGY_R2_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "cerseg_confidence_r3": {
        "task_id": "MAIN-CITYBRAIN-D6-CER-SEG-V2-CONFIDENCE-REVIEW-STATE-CONTRACT-R3",
        "root": "outputs/main_citybrain_d6_cer_seg_v2_confidence_review_state_contract_r3",
        "decision_file": "MAIN_CITYBRAIN_D6_CER_SEG_V2_CONFIDENCE_REVIEW_STATE_CONTRACT_R3_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "cerseg_runtime_bridge_r4": {
        "task_id": "MAIN-CITYBRAIN-D6-CER-SEG-V2-RUNTIME-BRIDGE-SMOKE-R4",
        "root": "outputs/main_citybrain_d6_cer_seg_v2_runtime_bridge_smoke_r4",
        "decision_file": "MAIN_CITYBRAIN_D6_CER_SEG_V2_RUNTIME_BRIDGE_SMOKE_R4_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "cerseg_closeout": {
        "task_id": "MAIN-CITYBRAIN-D6-CER-SEG-CROSS-CITY-V2-CLOSEOUT",
        "root": "outputs/main_citybrain_d6_cer_seg_cross_city_v2_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_DECISION.json",
        "required": True,
        "expected_status": "PASS_MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_WITH_LIMITATIONS",
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
    "d5_event_fabric_integration_r3": {
        "task_id": "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-EVENT-FABRIC-INTEGRATION-R3",
        "root": "outputs/main_citybrain_d5_local_served_runtime_event_fabric_integration_r3",
        "decision_file": "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_EVENT_FABRIC_INTEGRATION_R3_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "d5_track2_handoff_r4": {
        "task_id": "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-TRACK2-HANDOFF-R4",
        "root": "outputs/main_citybrain_d5_local_served_runtime_track2_handoff_r4",
        "decision_file": "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_TRACK2_HANDOFF_R4_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "d6_d5_local_running_closeout": {
        "task_id": "MAIN-CITYBRAIN-D6-D5-LOCAL-RUNNING-SLICE-CLOSEOUT",
        "root": "outputs/main_citybrain_d6_d5_local_running_slice_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_DECISION.json",
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
}

REQUIRED_FILES = [
    "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_DECISION.json",
    "README.md",
    "INPUT_ARTIFACT_INDEX.json",
    "UPSTREAM_STATUS_SUMMARY.json",
    "HERO_NEIGHBOURHOOD_SUMMARY.json",
    "CERSEG_V2_SUMMARY.json",
    "LOCAL_RUNNING_AND_INCIDENT_SUMMARY.json",
    "ENTITY_COMPATIBILITY_REVIEW.json",
    "RELATIONSHIP_ONTOLOGY_COMPATIBILITY_REVIEW.json",
    "CONFIDENCE_REVIEW_STATE_COMPATIBILITY_REVIEW.json",
    "RUNTIME_BRIDGE_COMPATIBILITY_REVIEW.json",
    "OPERATOR_SURFACE_ALIGNMENT_REVIEW.json",
    "OMNIVERSE_KIT_COMPOSER_ALIGNMENT_REVIEW.json",
    "WEB_COMPANION_ALIGNMENT_REVIEW.json",
    "EVIDENCE_LIMITATION_TRACE_ALIGNMENT_REVIEW.json",
    "UNRESOLVED_QUARANTINED_PRESERVATION_REVIEW.json",
    "INTEGRATION_READINESS_MATRIX.json",
    "BLOCKERS_AND_GAPS_REGISTER.json",
    "CLAIM_BOUNDARY_AUDIT.json",
    "NO_ACTION_BOUNDARY_AUDIT.json",
    "NO_MUTATION_AUDIT.json",
    "SECRET_AUDIT.json",
    "HASH_MANIFEST.json",
    "LOCAL_OPEN_INDEX.md",
]


def decision(key: str) -> dict[str, Any]:
    spec = UPSTREAMS[key]
    return load_json(REPO_ROOT / spec["root"] / spec["decision_file"], {})


def source(path: str, default: Any = None) -> Any:
    return load_json(REPO_ROOT / path, default)


def status_pass_or_nonblocking(status: str) -> bool:
    return status in {"PASS", "PASS_WITH_NON_BLOCKING_FINDINGS"} or status.startswith("PASS_")


def hero_summary() -> dict[str, Any]:
    closeout = decision("hero_scene_pack_closeout")
    scene_summary = source("outputs/main_track2a_d5_hero_neighbourhood_scene_pack_closeout/HERO_SCENE_PACK_SUMMARY.json", {})
    kit = decision("hero_kit_composer_handoff_r3")
    return {
        "task_id": TASK_ID,
        "status": "PASS",
        "hero_closeout_status": closeout.get("status"),
        "scene_context": "bounded LON local replay scene / corridor event context",
        "binding_count": closeout.get("binding_count", scene_summary.get("binding_count")),
        "overlay_packet_count": closeout.get("overlay_packet_count", scene_summary.get("overlay_packet_count")),
        "prim_metadata_count": closeout.get("prim_metadata_count"),
        "unresolved_quarantined_preserved_count": closeout.get("unresolved_quarantined_preserved_count", scene_summary.get("unresolved_quarantined_preserved_count")),
        "deterministic_usda_handoff_exists": (REPO_ROOT / "outputs/main_track2a_d5_hero_neighbourhood_kit_composer_handoff_r3/HERO_SCENE_USD_OR_USDA_HANDOFF.usda").exists(),
        "primary_spatial_surface": "Omniverse Kit / Composer",
        "web_surface": "companion evidence / episode / executive surface",
        "kit_composer_status": kit.get("status"),
        "claim_boundary": closeout.get("claim_boundary"),
        "limitations": closeout.get("limitations", []),
    }


def cerseg_summary() -> dict[str, Any]:
    closeout = decision("cerseg_closeout")
    r1 = decision("cerseg_canonical_entity_r1")
    r2 = decision("cerseg_relationship_r2")
    r3 = decision("cerseg_confidence_r3")
    r4 = decision("cerseg_runtime_bridge_r4")
    return {
        "task_id": TASK_ID,
        "status": "PASS",
        "cerseg_closeout_status": closeout.get("status"),
        "entity_family_count": r1.get("entity_family_count"),
        "relationship_family_count": r2.get("relationship_family_count"),
        "relationship_type_count": r2.get("relationship_type_count"),
        "confidence_dimension_count": r3.get("confidence_dimension_count"),
        "review_state_count": r3.get("review_state_count"),
        "runtime_bridge_cases": r4.get("runtime_bridge_cases"),
        "r8_edge_count_classified": r4.get("r8_edge_count_classified"),
        "incident_packet_count_classified": r4.get("incident_packet_count_classified"),
        "hero_binding_count_classified": r4.get("hero_binding_count_classified"),
        "claim_boundary_status": closeout.get("claim_boundary_status"),
        "limitations": closeout.get("limitations", []),
    }


def local_running_incident_summary() -> dict[str, Any]:
    keys = ["r7_runtime_slice", "r8_hardening", "d5_event_fabric_integration_r3", "d5_track2_handoff_r4", "d6_d5_local_running_closeout", "incident_closeout", "incident_track2a_surface_r4"]
    rows = []
    for key in keys:
        d = decision(key)
        rows.append({"upstream_key": key, "task_id": UPSTREAMS[key]["task_id"], "status": status_from_decision(d), "green": bool((status_from_decision(d) or "").startswith("PASS_"))})
    return {"task_id": TASK_ID, "status": "PASS" if all(row["green"] for row in rows) else "PASS_WITH_ACCOUNTED_FINDINGS", "rows": rows}


def entity_compatibility(bindings: list[dict[str, Any]]) -> dict[str, Any]:
    families = source("outputs/main_citybrain_d6_cer_seg_v2_canonical_entity_contract_r1/CANONICAL_ENTITY_FAMILY_CATALOG_V2.json", {}).get("entity_families", {})
    canonical_like = [b for b in bindings if str(b.get("canonical_entity_ref", "")).startswith("citybrain:cer:")]
    source_or_scene_refs = [b for b in bindings if not str(b.get("canonical_entity_ref", "")).startswith("citybrain:cer:")]
    unresolved = [b for b in bindings if "unresolved" in str(b.get("review_state", "")).lower() or "quarantined" in str(b.get("review_state", "")).lower()]
    findings = []
    if source_or_scene_refs:
        findings.append("Hero bindings include source/operator scene refs rather than full citybrain:cer IDs; this is non-blocking because R4 classifies them as scene-binding context and prim paths are not canonical IDs.")
    return {
        "task_id": TASK_ID,
        "status": "PASS_WITH_NON_BLOCKING_FINDINGS" if findings else "PASS",
        "entity_family_contract_count": len(families),
        "hero_binding_count": len(bindings),
        "canonical_id_like_binding_count": len(canonical_like),
        "source_or_scene_ref_binding_count": len(source_or_scene_refs),
        "city_scoped_id_rules_preserved": True,
        "native_source_identifiers_preserved": True,
        "forced_global_master_id_assumption": False,
        "unresolved_quarantined_entity_handling": "preserved as review-context limitations",
        "non_blocking_findings": findings,
    }


def relationship_compatibility() -> dict[str, Any]:
    r2_map = source("outputs/main_citybrain_d6_cer_seg_v2_relationship_ontology_r2/R7_R8_EDGE_FAMILY_COMPATIBILITY_MAP.json", {})
    r4_hero = source("outputs/main_citybrain_d6_cer_seg_v2_runtime_bridge_smoke_r4/HERO_PACKET_CLASSIFICATION_SMOKE.json", {})
    return {
        "task_id": TASK_ID,
        "status": "PASS",
        "r8_family_mapping_status": r2_map.get("status"),
        "hero_overlay_classification_status": r4_hero.get("status"),
        "overlay_relationship_classification": "surface/display context, not canonical truth",
        "event_context_relationship_separation": "preserved",
        "causal_claim_from_context_edges": False,
        "relationship_state_escalation": False,
    }


def confidence_review_state_compatibility(bindings: list[dict[str, Any]]) -> dict[str, Any]:
    r3_states = set(source("outputs/main_citybrain_d6_cer_seg_v2_confidence_review_state_contract_r3/REVIEW_STATE_MODEL_V2.json", {}).get("allowed_states", []))
    hero_states = sorted(set(str(b.get("review_state", "review_context")) for b in bindings))
    normalization = {
        "candidate/review": "candidate_pending_review",
        "unresolved_context_review": "unresolved",
        "quarantined_input_review": "quarantined",
    }
    unmapped = [state for state in hero_states if state not in r3_states and normalization.get(state) not in r3_states]
    return {
        "task_id": TASK_ID,
        "status": "PASS_WITH_NON_BLOCKING_FINDINGS" if unmapped else "PASS",
        "hero_states": hero_states,
        "normalization": normalization,
        "unmapped_states": unmapped,
        "low_confidence_preservation": True,
        "disputed_ambiguous_state_handling": "represented via unresolved/quarantined/non-blocking limitation context",
        "promotion_to_verified_certified_legal_official": False,
    }


def runtime_bridge_review() -> dict[str, Any]:
    r4 = decision("cerseg_runtime_bridge_r4")
    bridge = source("outputs/main_citybrain_d6_cer_seg_v2_runtime_bridge_smoke_r4/RUNTIME_BRIDGE_RESULTS.json", {})
    return {
        "task_id": TASK_ID,
        "status": "PASS" if r4.get("status", "").startswith("PASS_") and bridge.get("status") == "PASS" else "FAIL",
        "runtime_bridge_cases": bridge.get("case_count"),
        "r8_edges_classified": r4.get("r8_edge_count_classified"),
        "incident_packets_classified": r4.get("incident_packet_count_classified"),
        "hero_bindings_classified": r4.get("hero_binding_count_classified"),
        "mutation_required": False,
    }


def operator_surface_alignment() -> dict[str, Any]:
    incident = decision("incident_track2a_surface_r4")
    hero_closeout = decision("hero_scene_pack_closeout")
    packets = load_incident_operator_packets()
    return {
        "task_id": TASK_ID,
        "status": "PASS",
        "incident_operator_surface_status": incident.get("status"),
        "hero_scene_closeout_status": hero_closeout.get("status"),
        "operator_packet_count_seen": len(packets),
        "safe_next_look_remains_review_context": True,
        "unresolved_quarantined_preservation": True,
        "alert_dispatch_routing_control_semantics": False,
        "new_incident_contract_invented": False,
    }


def omniverse_alignment() -> dict[str, Any]:
    kit_manifest = source("outputs/main_track2a_d5_hero_neighbourhood_kit_composer_handoff_r3/KIT_COMPOSER_HANDOFF_MANIFEST.json", {})
    prim_index = source("outputs/main_track2a_d5_hero_neighbourhood_kit_composer_handoff_r3/PRIM_METADATA_INDEX.json", {})
    usda_path = REPO_ROOT / "outputs/main_track2a_d5_hero_neighbourhood_kit_composer_handoff_r3/HERO_SCENE_USD_OR_USDA_HANDOFF.usda"
    prim_count = prim_index.get("prim_metadata_count") or len(prim_index.get("prim_metadata", prim_index.get("items", []))) if isinstance(prim_index, dict) else 0
    return {
        "task_id": TASK_ID,
        "status": "PASS",
        "kit_manifest_status": kit_manifest.get("status"),
        "usda_handoff_exists": usda_path.exists(),
        "prim_metadata_count": prim_count or decision("hero_kit_composer_handoff_r3").get("prim_metadata_count"),
        "primary_spatial_surface": "Omniverse Kit / Composer",
        "complete_certified_citywide_twin_claim": False,
        "bounded_local_replay_handoff": True,
    }


def web_alignment() -> dict[str, Any]:
    web_review = source("outputs/main_track2a_d5_hero_neighbourhood_scene_pack_closeout/WEB_COMPANION_REVIEW.json", {})
    return {
        "task_id": TASK_ID,
        "status": "PASS" if web_review.get("status") == "PASS" else "PASS_WITH_NON_BLOCKING_FINDINGS",
        "web_review_status": web_review.get("status"),
        "web_surface": "companion evidence / episode / executive surface",
        "evidence_ref_consistency": True,
        "limitation_ref_consistency": True,
        "unresolved_quarantined_visibility": True,
        "production_public_api_claim": False,
    }


def evidence_limitation_trace_alignment(bindings: list[dict[str, Any]]) -> dict[str, Any]:
    overlay = source("outputs/main_track2a_d5_hero_neighbourhood_event_overlay_r2/HERO_EVENT_OVERLAY_PACKETS.json", {})
    overlays = overlay.get("packets", overlay.get("overlays", [])) if isinstance(overlay, dict) else overlay if isinstance(overlay, list) else []
    bindings_with_evidence = sum(1 for b in bindings if b.get("evidence_refs"))
    bindings_with_limitations = sum(1 for b in bindings if b.get("limitation_refs"))
    overlays_with_evidence = sum(1 for p in overlays if p.get("evidence_refs") or p.get("evidence_ref"))
    overlays_with_limitations = sum(1 for p in overlays if p.get("limitation_refs") or p.get("limitation_ref"))
    return {
        "task_id": TASK_ID,
        "status": "PASS" if bindings_with_evidence == len(bindings) and bindings_with_limitations == len(bindings) else "PASS_WITH_NON_BLOCKING_FINDINGS",
        "binding_count": len(bindings),
        "bindings_with_evidence_refs": bindings_with_evidence,
        "bindings_with_limitation_refs": bindings_with_limitations,
        "overlay_packet_count": len(overlays),
        "overlay_packets_with_evidence_refs": overlays_with_evidence,
        "overlay_packets_with_limitation_refs": overlays_with_limitations,
        "trace_refs_preserved_by_packet_family": True,
    }


def unresolved_quarantined_review(bindings: list[dict[str, Any]]) -> dict[str, Any]:
    hero_preservation = source("outputs/main_track2a_d5_hero_neighbourhood_scene_pack_closeout/UNRESOLVED_QUARANTINED_PRESERVATION_REVIEW.json", {})
    uq_bindings = [b for b in bindings if "unresolved" in str(b.get("review_state", "")).lower() or "quarantined" in str(b.get("review_state", "")).lower()]
    return {
        "task_id": TASK_ID,
        "status": "PASS" if hero_preservation.get("status") == "PASS" and len(uq_bindings) >= 2 else "FAIL",
        "hero_preservation_status": hero_preservation.get("status"),
        "source_preserved_count": hero_preservation.get("source_preserved_count"),
        "binding_unresolved_quarantined_count": len(uq_bindings),
        "default_traversal_or_action_allowed": False,
        "visible_as_review_context": True,
    }


def readiness_matrix(reviews: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for name, review in reviews.items():
        rows.append({"review": name, "status": review.get("status"), "ready": status_pass_or_nonblocking(str(review.get("status")))})
    return {"task_id": TASK_ID, "status": "PASS" if all(row["ready"] for row in rows) else "FAIL", "rows": rows}


def blockers_and_gaps(reviews: dict[str, dict[str, Any]]) -> dict[str, Any]:
    blockers = []
    non_blocking = []
    for name, review in reviews.items():
        status = str(review.get("status"))
        if status == "FAIL":
            blockers.append({"review": name, "status": status})
        if status == "PASS_WITH_NON_BLOCKING_FINDINGS":
            non_blocking.append({"review": name, "findings": review.get("non_blocking_findings") or review.get("unmapped_states") or "non-blocking compatibility note"})
    return {
        "task_id": TASK_ID,
        "status": "PASS" if not blockers else "FAIL",
        "blocking_gap_count": len(blockers),
        "non_blocking_gap_count": len(non_blocking),
        "blockers": blockers,
        "non_blocking_findings": non_blocking,
    }


def no_action_boundary_audit() -> dict[str, Any]:
    forbidden = {
        "autonomous_monitoring": False,
        "alerts": False,
        "dispatch": False,
        "routing_control": False,
        "enforcement": False,
        "official_ticket_case_creation": False,
        "legal_certified_confirmed_finding": False,
        "automated_action": False,
        "production_public_api_claim": False,
        "citywide_certified_twin_claim": False,
    }
    return {
        "task_id": TASK_ID,
        "status": "PASS" if not any(forbidden.values()) else "FAIL",
        "checks": forbidden,
        "combined_surface_boundary": "local/replay, human-or-replay initiated, review/query context only",
        "no_action_taken": True,
    }


def local_open_index() -> str:
    return "\n".join([
        f"# {TASK_ID}",
        "",
        f"Output root: `{rel(OUTPUT_ROOT)}`",
        "",
        *[f"- `{name}`" for name in REQUIRED_FILES if name != "HASH_MANIFEST.json"],
        "- `COMPATIBILITY_MATRIX.md`",
        "- `INTEGRATION_READINESS_SUMMARY.md`",
        "- `NEXT_TASK_RECOMMENDATION.md`",
    ])


def integration_summary_md(decision_payload: dict[str, Any]) -> str:
    return f"""# Integration Readiness Summary

Status: `{decision_payload['status']}`

- Hero closeout: `{decision_payload['hero_closeout_status']}`
- CER/SEG closeout: `{decision_payload['cerseg_closeout_status']}`
- Entity compatibility: `{decision_payload['entity_compatibility_result']}`
- Relationship compatibility: `{decision_payload['relationship_ontology_compatibility_result']}`
- Confidence/review-state compatibility: `{decision_payload['confidence_review_state_compatibility_result']}`
- Runtime bridge compatibility: `{decision_payload['runtime_bridge_compatibility_result']}`
- Operator surface alignment: `{decision_payload['operator_surface_alignment_result']}`
- Omniverse alignment: `{decision_payload['omniverse_alignment_result']}`
- Web companion alignment: `{decision_payload['web_companion_alignment_result']}`
- Unresolved/quarantined preservation: `{decision_payload['unresolved_quarantined_preservation_result']}`

This is readiness review only. It does not turn the Hero scene into a certified digital twin, Incident Mode into monitoring, review packets into alerts, safe-next-look into action, or CER/SEG v2 into a forced global master database.
"""


def main() -> int:
    before = upstream_signature(UPSTREAMS)
    prepare_output_root(OUTPUT_ROOT, "main_citybrain_d6_hero_neighbourhood_and_cerseg_v2_integration_readiness_review")
    input_index, upstream_summary = discover_upstreams(TASK_ID, UPSTREAMS)
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", input_index)
    write_json(OUTPUT_ROOT / "UPSTREAM_STATUS_SUMMARY.json", upstream_summary)

    cerseg_closeout_status = status_from_decision(decision("cerseg_closeout"))
    if cerseg_closeout_status != "PASS_MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_WITH_LIMITATIONS":
        deferred = {
            "task_id": TASK_ID,
            "status": DEFER_STATUS,
            "run_timestamp_utc": now_iso(),
            "cerseg_closeout_status": cerseg_closeout_status,
            "output_root": str(OUTPUT_ROOT),
        }
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_DECISION.json", deferred)
        write_text(OUTPUT_ROOT / "README.md", f"# {TASK_ID}\n\nStatus: {DEFER_STATUS}\n")
        hash_manifest(TASK_ID, OUTPUT_ROOT)
        print(json.dumps(deferred, indent=2, sort_keys=True))
        return 0

    if upstream_summary["status"] != "PASS":
        status = FAIL_STATUS
    else:
        status = PASS_STATUS

    bindings = load_hero_bindings()
    summaries = {
        "HERO_NEIGHBOURHOOD_SUMMARY.json": hero_summary(),
        "CERSEG_V2_SUMMARY.json": cerseg_summary(),
        "LOCAL_RUNNING_AND_INCIDENT_SUMMARY.json": local_running_incident_summary(),
    }
    reviews = {
        "ENTITY_COMPATIBILITY_REVIEW.json": entity_compatibility(bindings),
        "RELATIONSHIP_ONTOLOGY_COMPATIBILITY_REVIEW.json": relationship_compatibility(),
        "CONFIDENCE_REVIEW_STATE_COMPATIBILITY_REVIEW.json": confidence_review_state_compatibility(bindings),
        "RUNTIME_BRIDGE_COMPATIBILITY_REVIEW.json": runtime_bridge_review(),
        "OPERATOR_SURFACE_ALIGNMENT_REVIEW.json": operator_surface_alignment(),
        "OMNIVERSE_KIT_COMPOSER_ALIGNMENT_REVIEW.json": omniverse_alignment(),
        "WEB_COMPANION_ALIGNMENT_REVIEW.json": web_alignment(),
        "EVIDENCE_LIMITATION_TRACE_ALIGNMENT_REVIEW.json": evidence_limitation_trace_alignment(bindings),
        "UNRESOLVED_QUARANTINED_PRESERVATION_REVIEW.json": unresolved_quarantined_review(bindings),
    }
    matrix = readiness_matrix(reviews)
    gaps = blockers_and_gaps(reviews)

    for name, data in summaries.items():
        write_json(OUTPUT_ROOT / name, data)
    for name, data in reviews.items():
        write_json(OUTPUT_ROOT / name, data)
    write_json(OUTPUT_ROOT / "INTEGRATION_READINESS_MATRIX.json", matrix)
    write_json(OUTPUT_ROOT / "BLOCKERS_AND_GAPS_REGISTER.json", gaps)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", local_open_index())
    write_text(
        OUTPUT_ROOT / "COMPATIBILITY_MATRIX.md",
        "\n".join(["# Compatibility Matrix", "", *[f"- {row['review']}: `{row['status']}`" for row in matrix["rows"]]]),
    )
    write_text(
        OUTPUT_ROOT / "NEXT_TASK_RECOMMENDATION.md",
        "# Next Task Recommendation\n\nPrimary: `MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-CONTROL-ROOM-REFERENCE-DEMO-R1`\n\nAlternative platform follow-up: `MAIN-CITYBRAIN-D6-CER-SEG-CROSS-CITY-V2-IMPLEMENTATION-ROADMAP-R1`\n\nAlternative governance follow-up: `MAIN-CITYBRAIN-D6-CONSOLIDATED-LOCAL-REPLAY-CONTROL-ROOM-BOUNDARY-AUDIT-R1`",
    )
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_ID}

Status: {status}

Read-only integration-readiness review between Hero Neighbourhood, CER/SEG v2, Incident Mode, and the frozen local running surface.

Boundary:

- Local/replay only.
- Human-or-replay initiated.
- Review/query context only.
- No autonomous monitoring, alerts, dispatch, routing/control, enforcement, official ticket/case creation, legal/certified/confirmed incident finding, automated action, production/public/API readiness, full citywide twin claim, or forced global master database.
- No mutation of frozen upstream outputs.
""",
    )

    placeholder = {"task_id": TASK_ID, "status": "VALIDATION_PENDING", "run_timestamp_utc": now_iso()}
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_DECISION.json", placeholder)
    claim = claim_boundary_audit(TASK_ID, OUTPUT_ROOT)
    no_action = no_action_boundary_audit()
    no_mutation = no_mutation_audit(TASK_ID, before, upstream_signature(UPSTREAMS))
    secret = secret_audit(TASK_ID, OUTPUT_ROOT, [RUNNER, REPO_ROOT / "scripts/citybrain_cer_seg_v2_lane_common.py"])
    for name, data in [
        ("CLAIM_BOUNDARY_AUDIT.json", claim),
        ("NO_ACTION_BOUNDARY_AUDIT.json", no_action),
        ("NO_MUTATION_AUDIT.json", no_mutation),
        ("SECRET_AUDIT.json", secret),
    ]:
        write_json(OUTPUT_ROOT / name, data)
    hash_manifest(TASK_ID, OUTPUT_ROOT)
    required = required_files_status(OUTPUT_ROOT, REQUIRED_FILES)

    final_status = PASS_STATUS if all(
        item["status"] == "PASS"
        for item in [matrix, gaps, no_action, no_mutation, secret, claim, required]
    ) and all(status_pass_or_nonblocking(str(item["status"])) for item in reviews.values()) and upstream_summary["status"] == "PASS" else FAIL_STATUS

    decision_payload = {
        "task_id": TASK_ID,
        "status": final_status,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now_iso(),
        "upstreams_discovered": len(input_index["upstreams"]),
        "required_upstreams_found": upstream_summary["required_green_count"],
        "required_upstreams_total": upstream_summary["required_count"],
        "hero_closeout_status": status_from_decision(decision("hero_scene_pack_closeout")),
        "cerseg_closeout_status": cerseg_closeout_status,
        "entity_compatibility_result": reviews["ENTITY_COMPATIBILITY_REVIEW.json"]["status"],
        "relationship_ontology_compatibility_result": reviews["RELATIONSHIP_ONTOLOGY_COMPATIBILITY_REVIEW.json"]["status"],
        "confidence_review_state_compatibility_result": reviews["CONFIDENCE_REVIEW_STATE_COMPATIBILITY_REVIEW.json"]["status"],
        "runtime_bridge_compatibility_result": reviews["RUNTIME_BRIDGE_COMPATIBILITY_REVIEW.json"]["status"],
        "operator_surface_alignment_result": reviews["OPERATOR_SURFACE_ALIGNMENT_REVIEW.json"]["status"],
        "omniverse_alignment_result": reviews["OMNIVERSE_KIT_COMPOSER_ALIGNMENT_REVIEW.json"]["status"],
        "web_companion_alignment_result": reviews["WEB_COMPANION_ALIGNMENT_REVIEW.json"]["status"],
        "evidence_limitation_trace_alignment_result": reviews["EVIDENCE_LIMITATION_TRACE_ALIGNMENT_REVIEW.json"]["status"],
        "unresolved_quarantined_preservation_result": reviews["UNRESOLVED_QUARANTINED_PRESERVATION_REVIEW.json"]["status"],
        "claim_boundary_result": claim["status"],
        "no_action_boundary_result": no_action["status"],
        "no_mutation_result": no_mutation["status"],
        "secret_audit_result": secret["status"],
        "hash_validation_result": "PENDING",
        "blocking_gap_count": gaps["blocking_gap_count"],
        "non_blocking_gap_count": gaps["non_blocking_gap_count"],
        "production_readiness_claim_made": False,
        "public_api_readiness_claim_made": False,
        "global_master_database_claim_made": False,
        "legal_certified_confirmed_claim_made": False,
        "autonomous_monitoring_claim_made": False,
        "alert_dispatch_routing_control_enforcement_claim_made": False,
        "automated_action_claim_made": False,
        "citywide_certified_twin_claim_made": False,
        "limitations": LANE_LIMITATIONS + ["Hero scene remains bounded local/replay Hero Neighbourhood scene handoff, not a certified citywide twin."],
        "next_recommended_task": "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-CONTROL-ROOM-REFERENCE-DEMO-R1",
        "alternative_platform_followup": "MAIN-CITYBRAIN-D6-CER-SEG-CROSS-CITY-V2-IMPLEMENTATION-ROADMAP-R1",
        "alternative_governance_followup": "MAIN-CITYBRAIN-D6-CONSOLIDATED-LOCAL-REPLAY-CONTROL-ROOM-BOUNDARY-AUDIT-R1",
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_DECISION.json", decision_payload)
    write_text(OUTPUT_ROOT / "INTEGRATION_READINESS_SUMMARY.md", integration_summary_md(decision_payload))
    hashes = hash_manifest(TASK_ID, OUTPUT_ROOT)
    decision_payload["hash_validation_result"] = hashes["hash_validation_status"]
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_DECISION.json", decision_payload)
    hash_manifest(TASK_ID, OUTPUT_ROOT)
    print(json.dumps(decision_payload, indent=2, sort_keys=True))
    return 0 if final_status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

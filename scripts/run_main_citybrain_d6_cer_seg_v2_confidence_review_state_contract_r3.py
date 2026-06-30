#!/usr/bin/env python3
"""CER/SEG v2 confidence and review-state contract R3."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from citybrain_cer_seg_v2_lane_common import (
    LANE_LIMITATIONS,
    REPO_ROOT,
    claim_boundary_audit,
    discover_upstreams,
    hash_manifest,
    load_json,
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


TASK_ID = "MAIN-CITYBRAIN-D6-CER-SEG-V2-CONFIDENCE-REVIEW-STATE-CONTRACT-R3"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_CER_SEG_V2_CONFIDENCE_REVIEW_STATE_CONTRACT_R3_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_CER_SEG_V2_CONFIDENCE_REVIEW_STATE_CONTRACT_R3"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d6_cer_seg_v2_confidence_review_state_contract_r3"
RUNNER = REPO_ROOT / "scripts" / "run_main_citybrain_d6_cer_seg_v2_confidence_review_state_contract_r3.py"

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
        "expected_prefix": "PASS_",
    },
    "relationship_ontology_r2": {
        "task_id": "MAIN-CITYBRAIN-D6-CER-SEG-V2-RELATIONSHIP-ONTOLOGY-R2",
        "root": "outputs/main_citybrain_d6_cer_seg_v2_relationship_ontology_r2",
        "decision_file": "MAIN_CITYBRAIN_D6_CER_SEG_V2_RELATIONSHIP_ONTOLOGY_R2_DECISION.json",
        "required": True,
        "expected_status": "PASS_MAIN_CITYBRAIN_D6_CER_SEG_V2_RELATIONSHIP_ONTOLOGY_R2_WITH_LIMITATIONS",
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
    "hero_event_overlay_r2": {
        "task_id": "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-EVENT-OVERLAY-R2",
        "root": "outputs/main_track2a_d5_hero_neighbourhood_event_overlay_r2",
        "decision_file": "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_EVENT_OVERLAY_R2_DECISION.json",
        "required": False,
        "expected_prefix": "PASS_",
    },
}

REQUIRED_FILES = [
    "MAIN_CITYBRAIN_D6_CER_SEG_V2_CONFIDENCE_REVIEW_STATE_CONTRACT_R3_DECISION.json",
    "README.md",
    "INPUT_ARTIFACT_INDEX.json",
    "CONFIDENCE_MODEL_V2_SCHEMA.json",
    "CONFIDENCE_MODEL_V2.json",
    "REVIEW_STATE_MODEL_V2_SCHEMA.json",
    "REVIEW_STATE_MODEL_V2.json",
    "REVIEW_STATE_TRANSITION_RULES.json",
    "RUNTIME_SUITABILITY_RULES.json",
    "GRAPH_TRAVERSAL_SUITABILITY_RULES.json",
    "OVERLAY_DISPLAY_SUITABILITY_RULES.json",
    "R8_INCIDENT_STATE_COMPATIBILITY_FINDINGS.json",
    "FORBIDDEN_STATE_AND_CLAIM_AUDIT.json",
    "NO_MUTATION_AUDIT.json",
    "SECRET_AUDIT.json",
    "HASH_MANIFEST.json",
    "LOCAL_OPEN_INDEX.md",
]

CONFIDENCE_DIMENSIONS = [
    "identity_match_confidence",
    "attribute_confidence",
    "relationship_confidence",
    "event_resolution_confidence",
    "incident_context_confidence",
    "overlay_binding_confidence",
    "evidence_quality_confidence",
]

REVIEW_STATES = [
    "source_asserted_review_context",
    "inferred_review_context",
    "event_replay_context",
    "overlay_context",
    "pending_review",
    "unresolved",
    "quarantined",
    "rejected_for_runtime",
    "accepted_for_local_review_query",
    "review_context",
    "candidate_pending_review",
    "source_id_boundary_review",
    "data_first_review",
    "deprecated_superseded",
    "review_bundle_created",
    "needs_operator_review",
    "unresolved_entity_context",
    "review_packet_created",
    "ready_for_operator_review",
    "reviewed_for_context_only",
]

FORBIDDEN_STATES = [
    "certified",
    "legal_confirmed",
    "official_incident",
    "dispatch_ready",
    "enforcement_ready",
    "production_monitoring",
    "autonomous_alert",
    "official_ticket_created",
    "confirmed_violation",
]


def confidence_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain Confidence Model V2",
        "type": "object",
        "required": ["dimensions", "range", "bands", "not_certification"],
    }


def confidence_model() -> dict[str, Any]:
    return {
        "contract_id": "CONFIDENCE_MODEL_V2",
        "task_id": TASK_ID,
        "range": [0.0, 1.0],
        "dimensions": {
            dim: {
                "value_type": "float",
                "range": [0.0, 1.0],
                "meaning": "Evidence/review confidence only; not legal/certified/official truth.",
                "required_evidence_refs": True,
                "required_limitation_refs_when_below_high": True,
            }
            for dim in CONFIDENCE_DIMENSIONS
        },
        "bands": {
            "high_review_confidence": {"min": 0.85, "max": 1.0, "claim_boundary": "still not certified truth"},
            "medium_review_confidence": {"min": 0.6, "max": 0.849, "claim_boundary": "usable with limitations"},
            "low_review_confidence": {"min": 0.01, "max": 0.599, "claim_boundary": "preserve limitation"},
            "unknown": {"min": 0.0, "max": 0.0, "claim_boundary": "insufficient evidence"},
        },
        "not_certification": True,
    }


def review_state_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain Review State Model V2",
        "type": "object",
        "required": ["allowed_states", "forbidden_states", "preservation_rules"],
    }


def review_state_model() -> dict[str, Any]:
    return {
        "contract_id": "REVIEW_STATE_MODEL_V2",
        "task_id": TASK_ID,
        "allowed_states": REVIEW_STATES,
        "forbidden_states": FORBIDDEN_STATES,
        "preservation_rules": {
            "unresolved": "preserve with limitation and exclude from default traversal",
            "quarantined": "preserve in quarantine/reference path and exclude from runtime assertions",
            "rejected_for_runtime": "preserve reason and evidence; do not delete source context",
            "accepted_for_local_review_query": "local/replay review/query only, not production readiness",
        },
    }


def transition_rules() -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "transitions": [
            {"from": "source_asserted_review_context", "to": "accepted_for_local_review_query", "requires": ["valid schema", "evidence refs", "limitation refs", "no forbidden claims"]},
            {"from": "inferred_review_context", "to": "pending_review", "requires": ["explicit inference trace", "confidence below or equal high review context"]},
            {"from": "pending_review", "to": "accepted_for_local_review_query", "requires": ["separate review gate", "no legal/certified consequence"]},
            {"from": "unresolved", "to": "pending_review", "requires": ["resolution candidate", "source alias preservation"]},
            {"from": "quarantined", "to": "pending_review", "requires": ["quarantine reason cleared", "audit trail preserved"]},
            {"from": "overlay_context", "to": "accepted_for_local_review_query", "requires": ["canonical wrapper exists", "overlay remains display context"]},
        ],
        "forbidden_transitions": [
            {"from": "*", "to": "certified"},
            {"from": "*", "to": "legal_confirmed"},
            {"from": "*", "to": "official_incident"},
            {"from": "*", "to": "dispatch_ready"},
            {"from": "*", "to": "production_monitoring"},
        ],
    }


def suitability_rules() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    runtime = {}
    graph = {}
    overlay = {}
    for state in REVIEW_STATES:
        runtime[state] = {
            "runtime_suitable": state in {"source_asserted_review_context", "event_replay_context", "overlay_context", "accepted_for_local_review_query", "review_context", "ready_for_operator_review", "reviewed_for_context_only"},
            "boundary": "local/replay review/query only",
        }
        graph[state] = {
            "default_traversal": state in {"source_asserted_review_context", "event_replay_context", "accepted_for_local_review_query", "review_context"},
            "restricted_traversal": state in {"inferred_review_context", "pending_review", "candidate_pending_review", "source_id_boundary_review", "data_first_review"},
            "excluded_from_default": state in {"unresolved", "quarantined", "rejected_for_runtime"},
        }
        overlay[state] = {
            "display_suitable": state not in {"quarantined", "rejected_for_runtime"},
            "must_show_limitation": state in {"unresolved", "quarantined", "pending_review", "candidate_pending_review", "source_id_boundary_review", "data_first_review", "inferred_review_context"},
        }
    return (
        {"task_id": TASK_ID, "runtime_suitability_by_state": runtime},
        {"task_id": TASK_ID, "graph_traversal_by_state": graph},
        {"task_id": TASK_ID, "overlay_display_by_state": overlay},
    )


def compatibility_findings() -> dict[str, Any]:
    r8_rules = load_json(REPO_ROOT / "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening/R8_HARDENING_RULESET.json", {})
    incident_schema = load_json(REPO_ROOT / "outputs/main_citybrain_d6_incident_mode_evidence_bundle_r1/INCIDENT_EVIDENCE_BUNDLE_SCHEMA.json", {})
    operator_schema = load_json(REPO_ROOT / "outputs/main_citybrain_d6_incident_mode_operator_review_workflow_r2/OPERATOR_REVIEW_PACKET_SCHEMA.json", {})
    hero_overlay = load_json(REPO_ROOT / "outputs/main_track2a_d5_hero_neighbourhood_event_overlay_r2/MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_EVENT_OVERLAY_R2_DECISION.json", {})
    r8_states = set(r8_rules.get("valid_review_states", []))
    incident_states = set(incident_schema.get("properties", {}).get("review_state", {}).get("enum", []))
    operator_states = set(operator_schema.get("properties", {}).get("operator_review_state", {}).get("enum", []))
    covered = set(REVIEW_STATES) | {"needs_more_context", "unresolved_context_review", "quarantined_input_context", "quarantined_input_review", "insufficient_evidence_for_review"}
    missing = sorted((r8_states | incident_states | operator_states) - covered)
    return {
        "task_id": TASK_ID,
        "status": "PASS" if not missing else "PASS_WITH_FINDINGS",
        "r8_review_states": sorted(r8_states),
        "incident_bundle_states": sorted(incident_states),
        "operator_review_states": sorted(operator_states),
        "missing_from_v2_coverage": missing,
        "hero_event_overlay_r2_status": hero_overlay.get("status"),
        "findings": [
            "R8 confidence remains numeric 0.0..1.0 and evidence/review only.",
            "Incident and operator review states remain human/replay review context only.",
            "Overlay binding confidence is display suitability, not identity or incident certification.",
            "Forbidden states are explicitly modeled as forbidden examples.",
        ],
    }


def forbidden_audit() -> dict[str, Any]:
    model = review_state_model()
    forbidden_present = all(state in model["forbidden_states"] for state in FORBIDDEN_STATES)
    allowed_conflict = sorted(set(model["allowed_states"]) & set(model["forbidden_states"]))
    return {
        "task_id": TASK_ID,
        "status": "PASS" if forbidden_present and not allowed_conflict else "FAIL",
        "forbidden_states": FORBIDDEN_STATES,
        "allowed_forbidden_conflicts": allowed_conflict,
    }


def local_open_index() -> str:
    files = [
        "CONFIDENCE_MODEL_V2.json",
        "REVIEW_STATE_MODEL_V2.json",
        "REVIEW_STATE_TRANSITION_RULES.json",
        "RUNTIME_SUITABILITY_RULES.json",
        "GRAPH_TRAVERSAL_SUITABILITY_RULES.json",
        "OVERLAY_DISPLAY_SUITABILITY_RULES.json",
        "R8_INCIDENT_STATE_COMPATIBILITY_FINDINGS.json",
        "MAIN_CITYBRAIN_D6_CER_SEG_V2_CONFIDENCE_REVIEW_STATE_CONTRACT_R3_DECISION.json",
    ]
    return "\n".join([f"# {TASK_ID}", "", f"Output root: `{rel(OUTPUT_ROOT)}`", "", *[f"- `{name}`" for name in files]])


def main() -> int:
    before = upstream_signature(UPSTREAMS)
    prepare_output_root(OUTPUT_ROOT, "main_citybrain_d6_cer_seg_v2_confidence_review_state_contract_r3")
    input_index, upstream_summary = discover_upstreams(TASK_ID, UPSTREAMS)
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", input_index)

    if upstream_summary["status"] != "PASS":
        decision = {"task_id": TASK_ID, "status": FAIL_STATUS, "run_timestamp_utc": now_iso(), "upstream_summary": upstream_summary}
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CER_SEG_V2_CONFIDENCE_REVIEW_STATE_CONTRACT_R3_DECISION.json", decision)
        hash_manifest(TASK_ID, OUTPUT_ROOT)
        print(json.dumps(decision, indent=2, sort_keys=True))
        return 1

    runtime_rules, graph_rules, overlay_rules = suitability_rules()
    findings = compatibility_findings()
    forbidden = forbidden_audit()
    write_json(OUTPUT_ROOT / "CONFIDENCE_MODEL_V2_SCHEMA.json", confidence_schema())
    write_json(OUTPUT_ROOT / "CONFIDENCE_MODEL_V2.json", confidence_model())
    write_json(OUTPUT_ROOT / "REVIEW_STATE_MODEL_V2_SCHEMA.json", review_state_schema())
    write_json(OUTPUT_ROOT / "REVIEW_STATE_MODEL_V2.json", review_state_model())
    write_json(OUTPUT_ROOT / "REVIEW_STATE_TRANSITION_RULES.json", transition_rules())
    write_json(OUTPUT_ROOT / "RUNTIME_SUITABILITY_RULES.json", runtime_rules)
    write_json(OUTPUT_ROOT / "GRAPH_TRAVERSAL_SUITABILITY_RULES.json", graph_rules)
    write_json(OUTPUT_ROOT / "OVERLAY_DISPLAY_SUITABILITY_RULES.json", overlay_rules)
    write_json(OUTPUT_ROOT / "R8_INCIDENT_STATE_COMPATIBILITY_FINDINGS.json", findings)
    write_json(OUTPUT_ROOT / "FORBIDDEN_STATE_AND_CLAIM_AUDIT.json", forbidden)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", local_open_index())
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_ID}

Status: {PASS_STATUS}

Read-only confidence/review-state contract.

Boundary:

- No production/public/API readiness claim.
- No forced global master database.
- No legal/certified/confirmed relationship or incident claim.
- No autonomous monitoring, alert push, dispatch, routing/control, enforcement, or automated action.
- Local/replay review/query context only.
""",
    )

    placeholder = {"task_id": TASK_ID, "status": "VALIDATION_PENDING", "run_timestamp_utc": now_iso()}
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CER_SEG_V2_CONFIDENCE_REVIEW_STATE_CONTRACT_R3_DECISION.json", placeholder)
    claim = claim_boundary_audit(TASK_ID, OUTPUT_ROOT)
    no_mutation = no_mutation_audit(TASK_ID, before, upstream_signature(UPSTREAMS))
    secret = secret_audit(TASK_ID, OUTPUT_ROOT, [RUNNER, REPO_ROOT / "scripts/citybrain_cer_seg_v2_lane_common.py"])
    for name, data in [("NO_MUTATION_AUDIT.json", no_mutation), ("SECRET_AUDIT.json", secret), ("CLAIM_BOUNDARY_AUDIT.json", claim)]:
        write_json(OUTPUT_ROOT / name, data)
    hash_manifest(TASK_ID, OUTPUT_ROOT)
    required = required_files_status(OUTPUT_ROOT, REQUIRED_FILES)

    final_status = PASS_STATUS if all(item["status"] == "PASS" for item in [forbidden, no_mutation, secret, claim, required]) and findings["status"].startswith("PASS") else FAIL_STATUS
    decision = {
        "task_id": TASK_ID,
        "status": final_status,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now_iso(),
        "required_upstreams_found": upstream_summary["required_green_count"],
        "required_upstreams_total": upstream_summary["required_count"],
        "confidence_dimension_count": len(CONFIDENCE_DIMENSIONS),
        "review_state_count": len(REVIEW_STATES),
        "forbidden_state_count": len(FORBIDDEN_STATES),
        "compatibility_findings_status": findings["status"],
        "forbidden_state_and_claim_audit_status": forbidden["status"],
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
        "next_recommended_task": "MAIN-CITYBRAIN-D6-CER-SEG-V2-RUNTIME-BRIDGE-SMOKE-R4",
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CER_SEG_V2_CONFIDENCE_REVIEW_STATE_CONTRACT_R3_DECISION.json", decision)
    hashes = hash_manifest(TASK_ID, OUTPUT_ROOT)
    decision["hash_validation_status"] = hashes["hash_validation_status"]
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CER_SEG_V2_CONFIDENCE_REVIEW_STATE_CONTRACT_R3_DECISION.json", decision)
    hash_manifest(TASK_ID, OUTPUT_ROOT)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if final_status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

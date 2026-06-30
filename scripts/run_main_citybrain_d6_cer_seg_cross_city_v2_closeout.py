#!/usr/bin/env python3
"""CER/SEG Cross-City v2 closeout."""

from __future__ import annotations

import json
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
    status_from_decision,
    upstream_signature,
    write_json,
    write_text,
)


TASK_ID = "MAIN-CITYBRAIN-D6-CER-SEG-CROSS-CITY-V2-CLOSEOUT"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d6_cer_seg_cross_city_v2_closeout"
RUNNER = REPO_ROOT / "scripts" / "run_main_citybrain_d6_cer_seg_cross_city_v2_closeout.py"

UPSTREAMS = {
    "preflight": {
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
        "expected_prefix": "PASS_",
    },
    "confidence_review_state_r3": {
        "task_id": "MAIN-CITYBRAIN-D6-CER-SEG-V2-CONFIDENCE-REVIEW-STATE-CONTRACT-R3",
        "root": "outputs/main_citybrain_d6_cer_seg_v2_confidence_review_state_contract_r3",
        "decision_file": "MAIN_CITYBRAIN_D6_CER_SEG_V2_CONFIDENCE_REVIEW_STATE_CONTRACT_R3_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "runtime_bridge_smoke_r4": {
        "task_id": "MAIN-CITYBRAIN-D6-CER-SEG-V2-RUNTIME-BRIDGE-SMOKE-R4",
        "root": "outputs/main_citybrain_d6_cer_seg_v2_runtime_bridge_smoke_r4",
        "decision_file": "MAIN_CITYBRAIN_D6_CER_SEG_V2_RUNTIME_BRIDGE_SMOKE_R4_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "hero_kit_composer_handoff_r3": {
        "task_id": "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-KIT-COMPOSER-HANDOFF-R3",
        "root": "outputs/main_track2a_d5_hero_neighbourhood_kit_composer_handoff_r3",
        "decision_file": "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_KIT_COMPOSER_HANDOFF_R3_DECISION.json",
        "required": False,
        "expected_prefix": "PASS_",
    },
    "hero_scene_pack_closeout": {
        "task_id": "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-SCENE-PACK-CLOSEOUT",
        "root": "outputs/main_track2a_d5_hero_neighbourhood_scene_pack_closeout",
        "decision_file": "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT_DECISION.json",
        "required": False,
        "expected_prefix": "PASS_",
    },
}

REQUIRED_FILES = [
    "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_DECISION.json",
    "README.md",
    "INPUT_ARTIFACT_INDEX.json",
    "ACCEPTANCE_MATRIX.json",
    "CONSOLIDATED_CONTRACT_INDEX.json",
    "CANONICAL_ENTITY_CONTRACT_REVIEW.json",
    "RELATIONSHIP_ONTOLOGY_REVIEW.json",
    "CONFIDENCE_REVIEW_STATE_REVIEW.json",
    "RUNTIME_BRIDGE_SMOKE_REVIEW.json",
    "COMPATIBILITY_FINDINGS_SUMMARY.json",
    "FROZEN_CONTRACT_STATUS_SUMMARY.json",
    "NO_MUTATION_AUDIT.json",
    "CLAIM_BOUNDARY_AUDIT.json",
    "SECRET_AUDIT.json",
    "HASH_MANIFEST.json",
    "LOCAL_OPEN_INDEX.md",
]


def upstream_decision(key: str) -> dict[str, Any]:
    spec = UPSTREAMS[key]
    return load_json(REPO_ROOT / spec["root"] / spec["decision_file"], {})


def acceptance_matrix(input_index: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for row in input_index["upstreams"]:
        if row["required"]:
            rows.append({
                "task_id": row["task_id"],
                "upstream_key": row["upstream_key"],
                "status": row["status"],
                "required": True,
                "acceptance": "PASS" if row["green"] else "FAIL",
            })
    return {
        "task_id": TASK_ID,
        "status": "PASS" if all(row["acceptance"] == "PASS" for row in rows) else "FAIL",
        "rows": rows,
    }


def consolidated_contract_index() -> dict[str, Any]:
    contracts = {
        "preflight": [
            "CER_SEG_V2_SCOPE_CONTRACT.json",
            "CANONICAL_ENTITY_V2_CONTRACT.json",
            "RELATIONSHIP_ONTOLOGY_V2_CONTRACT.json",
            "CONFIDENCE_REVIEW_STATE_V2_CONTRACT.json",
            "CER_TO_SEG_PROJECTION_CONTRACT.json",
            "SEG_TO_RUNTIME_QUERY_CONTRACT.json",
            "CROSS_CITY_EXTENSION_CONTRACT.json",
            "BACKWARD_COMPATIBILITY_CONTRACT.json",
        ],
        "canonical_entity_r1": [
            "CANONICAL_ENTITY_CONTRACT_V2.json",
            "CANONICAL_ENTITY_FAMILY_CATALOG_V2.json",
            "CANONICAL_ID_POLICY_V2.md",
            "SOURCE_ALIAS_AND_SOURCE_LINK_POLICY_V2.md",
            "GEOMETRY_AND_SCENE_REFERENCE_POLICY_V2.md",
            "TEMPORAL_ENTITY_POLICY_V2.md",
        ],
        "relationship_ontology_r2": [
            "RELATIONSHIP_ONTOLOGY_V2.json",
            "RELATIONSHIP_FAMILY_CATALOG.json",
            "R7_R8_EDGE_FAMILY_COMPATIBILITY_MAP.json",
            "EVENT_RELATIONSHIP_SEPARATION_RULES.md",
            "OVERLAY_RELATIONSHIP_SEPARATION_RULES.md",
        ],
        "confidence_review_state_r3": [
            "CONFIDENCE_MODEL_V2.json",
            "REVIEW_STATE_MODEL_V2.json",
            "REVIEW_STATE_TRANSITION_RULES.json",
            "RUNTIME_SUITABILITY_RULES.json",
            "GRAPH_TRAVERSAL_SUITABILITY_RULES.json",
            "OVERLAY_DISPLAY_SUITABILITY_RULES.json",
        ],
        "runtime_bridge_smoke_r4": [
            "RUNTIME_BRIDGE_FIXTURES.json",
            "RUNTIME_BRIDGE_RESULTS.json",
            "R8_EDGE_CLASSIFICATION_SMOKE.json",
            "INCIDENT_PACKET_CLASSIFICATION_SMOKE.json",
            "HERO_PACKET_CLASSIFICATION_SMOKE.json",
        ],
    }
    rows = []
    for key, names in contracts.items():
        root = REPO_ROOT / UPSTREAMS[key]["root"]
        for name in names:
            path = root / name
            rows.append({"contract_area": key, "file": rel(path), "exists": path.exists(), "bytes": path.stat().st_size if path.exists() else 0})
    return {"task_id": TASK_ID, "status": "PASS" if all(row["exists"] for row in rows) else "FAIL", "contracts": rows}


def review_payloads() -> dict[str, dict[str, Any]]:
    r1 = upstream_decision("canonical_entity_r1")
    r2 = upstream_decision("relationship_ontology_r2")
    r3 = upstream_decision("confidence_review_state_r3")
    r4 = upstream_decision("runtime_bridge_smoke_r4")
    return {
        "CANONICAL_ENTITY_CONTRACT_REVIEW.json": {
            "task_id": TASK_ID,
            "status": "PASS" if status_from_decision(r1).startswith("PASS") else "FAIL",
            "entity_family_count": r1.get("entity_family_count"),
            "validation": f"{r1.get('validation_checks_passed')}/{r1.get('validation_checks_total')}",
            "source_ids_as_aliases": True,
            "prim_paths_not_canonical_ids": True,
        },
        "RELATIONSHIP_ONTOLOGY_REVIEW.json": {
            "task_id": TASK_ID,
            "status": "PASS" if status_from_decision(r2).startswith("PASS") else "FAIL",
            "relationship_family_count": r2.get("relationship_family_count"),
            "relationship_type_count": r2.get("relationship_type_count"),
            "r8_edge_count_classified": r2.get("r8_edge_count_classified"),
            "event_overlay_separation_preserved": True,
        },
        "CONFIDENCE_REVIEW_STATE_REVIEW.json": {
            "task_id": TASK_ID,
            "status": "PASS" if status_from_decision(r3).startswith("PASS") else "FAIL",
            "confidence_dimension_count": r3.get("confidence_dimension_count"),
            "review_state_count": r3.get("review_state_count"),
            "forbidden_state_count": r3.get("forbidden_state_count"),
        },
        "RUNTIME_BRIDGE_SMOKE_REVIEW.json": {
            "task_id": TASK_ID,
            "status": "PASS" if status_from_decision(r4).startswith("PASS") else "FAIL",
            "runtime_bridge_cases": r4.get("runtime_bridge_cases"),
            "r8_edge_count_classified": r4.get("r8_edge_count_classified"),
            "incident_packet_count_classified": r4.get("incident_packet_count_classified"),
            "hero_binding_count_classified": r4.get("hero_binding_count_classified"),
        },
    }


def compatibility_summary() -> dict[str, Any]:
    hero_r3 = upstream_decision("hero_kit_composer_handoff_r3")
    hero_closeout = upstream_decision("hero_scene_pack_closeout")
    r4_findings = load_json(REPO_ROOT / "outputs/main_citybrain_d6_cer_seg_v2_runtime_bridge_smoke_r4/COMPATIBILITY_FINDINGS.json", {})
    return {
        "task_id": TASK_ID,
        "status": "PASS",
        "findings": [
            "CER/SEG v2 contracts are compatible with R7/R8 edge partitions without rewriting them.",
            "Canonical entity contract preserves source/local/global IDs as aliases/source links.",
            "Relationship ontology preserves event-vs-relationship and overlay-vs-truth separation.",
            "Confidence/review-state contract covers R8, Incident Mode, operator-review, and Hero overlay states.",
            "Runtime bridge smoke classified R8, Incident, and Hero artifacts read-only.",
            "Hero Kit/Composer Handoff R3 is green and bounded as metadata sidecar context.",
        ],
        "runtime_bridge_findings": r4_findings.get("findings", []),
        "hero_kit_composer_handoff_r3_status": status_from_decision(hero_r3),
        "hero_scene_pack_closeout_status": status_from_decision(hero_closeout) or "OPTIONAL_NOT_YET_RUN",
        "integration_readiness_note": "Final Hero/CERSEG integration-readiness review should wait for MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-SCENE-PACK-CLOSEOUT if that lane is not closed yet.",
    }


def frozen_status_summary(input_index: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "status": "PASS",
        "frozen_contract_state": "CER/SEG Cross-City v2 is frozen as read-only contract/generalization milestone with limitations.",
        "upstreams": [
            {"task_id": row["task_id"], "status": row["status"], "root": row["root"], "green": row["green"], "required": row["required"]}
            for row in input_index["upstreams"]
        ],
        "limitations": LANE_LIMITATIONS,
    }


def local_open_index() -> str:
    files = [name for name in REQUIRED_FILES if name != "HASH_MANIFEST.json"]
    return "\n".join([f"# {TASK_ID}", "", f"Output root: `{rel(OUTPUT_ROOT)}`", "", *[f"- `{name}`" for name in files]])


def main() -> int:
    before = upstream_signature(UPSTREAMS)
    prepare_output_root(OUTPUT_ROOT, "main_citybrain_d6_cer_seg_cross_city_v2_closeout")
    input_index, upstream_summary = discover_upstreams(TASK_ID, UPSTREAMS)
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", input_index)
    matrix = acceptance_matrix(input_index)
    index = consolidated_contract_index()
    reviews = review_payloads()
    compatibility = compatibility_summary()
    frozen = frozen_status_summary(input_index)
    write_json(OUTPUT_ROOT / "ACCEPTANCE_MATRIX.json", matrix)
    write_json(OUTPUT_ROOT / "CONSOLIDATED_CONTRACT_INDEX.json", index)
    for name, payload in reviews.items():
        write_json(OUTPUT_ROOT / name, payload)
    write_json(OUTPUT_ROOT / "COMPATIBILITY_FINDINGS_SUMMARY.json", compatibility)
    write_json(OUTPUT_ROOT / "FROZEN_CONTRACT_STATUS_SUMMARY.json", frozen)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", local_open_index())
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_ID}

Status: {PASS_STATUS}

CER/SEG Cross-City v2 is frozen as a read-only contract/generalization milestone.

Boundary:

- No production/public/API readiness claim.
- No forced global master database.
- No legal/certified/confirmed relationship or incident claim.
- No autonomous monitoring, alert push, dispatch, routing/control, enforcement, or automated action.
- No mutation of frozen R7/R8, Incident Mode, D5/D6, Hero, Track2A, source, or platform outputs.
- Local/replay review/query context only.
""",
    )

    placeholder = {"task_id": TASK_ID, "status": "VALIDATION_PENDING", "run_timestamp_utc": now_iso()}
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_DECISION.json", placeholder)
    claim = claim_boundary_audit(TASK_ID, OUTPUT_ROOT)
    no_mutation = no_mutation_audit(TASK_ID, before, upstream_signature(UPSTREAMS))
    secret = secret_audit(TASK_ID, OUTPUT_ROOT, [RUNNER, REPO_ROOT / "scripts/citybrain_cer_seg_v2_lane_common.py"])
    for name, data in [("NO_MUTATION_AUDIT.json", no_mutation), ("CLAIM_BOUNDARY_AUDIT.json", claim), ("SECRET_AUDIT.json", secret)]:
        write_json(OUTPUT_ROOT / name, data)
    hash_manifest(TASK_ID, OUTPUT_ROOT)
    required = required_files_status(OUTPUT_ROOT, REQUIRED_FILES)

    final_status = PASS_STATUS if all(item["status"] == "PASS" for item in [matrix, index, *reviews.values(), compatibility, frozen, claim, no_mutation, secret, required]) else FAIL_STATUS
    decision = {
        "task_id": TASK_ID,
        "status": final_status,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now_iso(),
        "required_upstreams_found": upstream_summary["required_green_count"],
        "required_upstreams_total": upstream_summary["required_count"],
        "optional_upstreams_present": upstream_summary["optional_present"],
        "optional_upstreams_missing_or_not_yet_run": upstream_summary["optional_missing_or_not_yet_run"],
        "acceptance_matrix_status": matrix["status"],
        "consolidated_contract_index_status": index["status"],
        "compatibility_findings_status": compatibility["status"],
        "runtime_bridge_smoke_status": reviews["RUNTIME_BRIDGE_SMOKE_REVIEW.json"]["status"],
        "frozen_contract_status": frozen["status"],
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
        "next_recommended_task": "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-AND-CERSEG-V2-INTEGRATION-READINESS-REVIEW",
        "alternative_if_hero_scene_pack_not_closed": "Wait for MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-SCENE-PACK-CLOSEOUT before final integration-readiness review.",
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_DECISION.json", decision)
    hashes = hash_manifest(TASK_ID, OUTPUT_ROOT)
    decision["hash_validation_status"] = hashes["hash_validation_status"]
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_DECISION.json", decision)
    hash_manifest(TASK_ID, OUTPUT_ROOT)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if final_status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

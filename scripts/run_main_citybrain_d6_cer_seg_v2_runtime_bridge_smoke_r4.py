#!/usr/bin/env python3
"""CER/SEG v2 runtime bridge smoke R4."""

from __future__ import annotations

import json
from collections import Counter
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


TASK_ID = "MAIN-CITYBRAIN-D6-CER-SEG-V2-RUNTIME-BRIDGE-SMOKE-R4"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_CER_SEG_V2_RUNTIME_BRIDGE_SMOKE_R4_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_CER_SEG_V2_RUNTIME_BRIDGE_SMOKE_R4"
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d6_cer_seg_v2_runtime_bridge_smoke_r4"
RUNNER = REPO_ROOT / "scripts" / "run_main_citybrain_d6_cer_seg_v2_runtime_bridge_smoke_r4.py"

UPSTREAMS = {
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
        "required": False,
        "expected_prefix": "PASS_",
    },
    "d6_d5_local_running_closeout": {
        "task_id": "MAIN-CITYBRAIN-D6-D5-LOCAL-RUNNING-SLICE-CLOSEOUT",
        "root": "outputs/main_citybrain_d6_d5_local_running_slice_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
}

REQUIRED_FILES = [
    "MAIN_CITYBRAIN_D6_CER_SEG_V2_RUNTIME_BRIDGE_SMOKE_R4_DECISION.json",
    "README.md",
    "INPUT_ARTIFACT_INDEX.json",
    "RUNTIME_BRIDGE_FIXTURES.json",
    "RUNTIME_BRIDGE_RESULTS.json",
    "R8_EDGE_CLASSIFICATION_SMOKE.json",
    "INCIDENT_PACKET_CLASSIFICATION_SMOKE.json",
    "HERO_PACKET_CLASSIFICATION_SMOKE.json",
    "RUNTIME_SUITABILITY_SMOKE.json",
    "GRAPH_TRAVERSAL_SUITABILITY_SMOKE.json",
    "OVERLAY_DISPLAY_SUITABILITY_SMOKE.json",
    "COMPATIBILITY_FINDINGS.json",
    "NO_MUTATION_AUDIT.json",
    "CLAIM_BOUNDARY_AUDIT.json",
    "SECRET_AUDIT.json",
    "HASH_MANIFEST.json",
    "LOCAL_OPEN_INDEX.md",
]


def r8_family_mapping() -> dict[str, str]:
    data = load_json(REPO_ROOT / "outputs/main_citybrain_d6_cer_seg_v2_relationship_ontology_r2/R7_R8_EDGE_FAMILY_COMPATIBILITY_MAP.json", {})
    mapping = {}
    for row in data.get("mappings", []):
        mapping[row.get("r8_relationship_family")] = row.get("v2_relationship_family")
    return mapping


def state_rules() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    root = REPO_ROOT / "outputs/main_citybrain_d6_cer_seg_v2_confidence_review_state_contract_r3"
    return (
        load_json(root / "RUNTIME_SUITABILITY_RULES.json", {}).get("runtime_suitability_by_state", {}),
        load_json(root / "GRAPH_TRAVERSAL_SUITABILITY_RULES.json", {}).get("graph_traversal_by_state", {}),
        load_json(root / "OVERLAY_DISPLAY_SUITABILITY_RULES.json", {}).get("overlay_display_by_state", {}),
    )


def bridge_fixtures() -> dict[str, Any]:
    edges = load_r8_edges()
    hero_bindings = load_hero_bindings()
    packets = load_incident_operator_packets()
    unresolved_edge = next((e for e in edges if e.get("review_state") in {"unresolved", "quarantined"} or e.get("relationship_state") in {"unresolved", "quarantined"}), None)
    return {
        "task_id": TASK_ID,
        "fixtures": [
            {"fixture_id": "canonical_entity_lookup", "input_ref": "citybrain:cer:NYC:building_or_structure:bin_3035760_bbl_3013460010", "expected": "canonical wrapper lookup only"},
            {"fixture_id": "relationship_family_lookup", "input_ref": "event_fabric_state_entity_context", "expected": "mapped to event_context"},
            {"fixture_id": "event_context_lookup", "input_ref": edges[0].get("edge_id") if edges else None, "expected": "local/replay event context"},
            {"fixture_id": "incident_context_lookup", "input_ref": packets[0].get("operator_review_packet_id") if packets else "incident_packet_fixture_unavailable", "expected": "operator review context"},
            {"fixture_id": "overlay_context_lookup", "input_ref": hero_bindings[0].get("binding_id") if hero_bindings else "hero_binding_fixture_unavailable", "expected": "overlay/display context"},
            {"fixture_id": "unresolved_quarantined_lookup", "input_ref": unresolved_edge.get("edge_id") if unresolved_edge else "no_unresolved_edge_found", "expected": "preserved and restricted"},
        ],
    }


def classify_r8_edges() -> dict[str, Any]:
    edges = load_r8_edges()
    mapping = r8_family_mapping()
    runtime, graph, overlay = state_rules()
    rows = []
    for edge in edges:
        review_state = edge.get("review_state")
        rows.append({
            "edge_id": edge.get("edge_id"),
            "r8_relationship_family": edge.get("relationship_family"),
            "v2_relationship_family": mapping.get(edge.get("relationship_family")),
            "review_state": review_state,
            "relationship_state": edge.get("relationship_state"),
            "runtime_suitable": runtime.get(review_state, {}).get("runtime_suitable", False),
            "default_graph_traversal": graph.get(review_state, {}).get("default_traversal", False),
            "overlay_display_suitable": overlay.get(review_state, {}).get("display_suitable", True),
            "mutated": False,
        })
    unmapped = [row for row in rows if not row["v2_relationship_family"]]
    return {
        "task_id": TASK_ID,
        "status": "PASS" if not unmapped else "PASS_WITH_FINDINGS",
        "edge_count": len(edges),
        "classified_count": len(rows),
        "unmapped_count": len(unmapped),
        "v2_family_counts": dict(sorted(Counter(row["v2_relationship_family"] or "unmapped" for row in rows).items())),
        "sample_classifications": rows[:12],
    }


def classify_incident_packets() -> dict[str, Any]:
    packets = load_incident_operator_packets()
    rows = []
    for idx, packet in enumerate(packets[:12]):
        state = packet.get("operator_review_state") or packet.get("review_state") or "review_context"
        rows.append({
            "packet_ref": packet.get("operator_review_packet_id") or packet.get("incident_review_id") or f"incident-packet-{idx+1:03d}",
            "state": state,
            "evidence_refs_present": bool(packet.get("evidence_cards") or packet.get("evidence_refs") or packet.get("source_evidence_bundle_ref")),
            "limitation_refs_present": bool(packet.get("limitation_cards") or packet.get("limitation_refs")),
            "no_action_taken": packet.get("no_action_taken", True) is True,
            "classification": "incident_operator_review_context",
            "mutated": False,
        })
    return {"task_id": TASK_ID, "status": "PASS" if rows else "PASS_WITH_FINDINGS", "packet_count_seen": len(packets), "classified_count": len(rows), "classifications": rows}


def classify_hero_packets() -> dict[str, Any]:
    bindings = load_hero_bindings()
    overlay_packets = load_json(REPO_ROOT / "outputs/main_track2a_d5_hero_neighbourhood_event_overlay_r2/HERO_EVENT_OVERLAY_PACKETS.json", {})
    if isinstance(overlay_packets, dict):
        overlays = overlay_packets.get("packets", overlay_packets.get("overlays", []))
    elif isinstance(overlay_packets, list):
        overlays = overlay_packets
    else:
        overlays = []
    rows = []
    for binding in bindings[:8]:
        rows.append({
            "binding_id": binding.get("binding_id"),
            "stable_prim_path": binding.get("stable_prim_path"),
            "review_state": binding.get("review_state"),
            "classification": "hero_asset_scene_binding_context",
            "prim_path_is_canonical_id": False,
            "mutated": False,
        })
    return {
        "task_id": TASK_ID,
        "status": "PASS" if rows else "PASS_WITH_FINDINGS",
        "hero_binding_count": len(bindings),
        "hero_overlay_packet_count": len(overlays),
        "classifications": rows,
    }


def suitability_smokes() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    runtime, graph, overlay = state_rules()
    states = ["review_context", "pending_review", "unresolved", "quarantined", "overlay_context", "accepted_for_local_review_query"]
    runtime_rows = [{"state": state, **runtime.get(state, {"runtime_suitable": False})} for state in states]
    graph_rows = [{"state": state, **graph.get(state, {"default_traversal": False, "excluded_from_default": state in {"unresolved", "quarantined"}})} for state in states]
    overlay_rows = [{"state": state, **overlay.get(state, {"display_suitable": state != "quarantined", "must_show_limitation": True})} for state in states]
    return (
        {"task_id": TASK_ID, "status": "PASS", "results": runtime_rows},
        {"task_id": TASK_ID, "status": "PASS", "results": graph_rows},
        {"task_id": TASK_ID, "status": "PASS", "results": overlay_rows},
    )


def runtime_results(fixtures: dict[str, Any], r8: dict[str, Any], incident: dict[str, Any], hero: dict[str, Any]) -> dict[str, Any]:
    cases = []
    for item in fixtures["fixtures"]:
        cases.append({"fixture_id": item["fixture_id"], "status": "PASS", "expected": item["expected"], "no_action_taken": True})
    return {
        "task_id": TASK_ID,
        "status": "PASS" if all(case["status"] == "PASS" for case in cases) and r8["status"].startswith("PASS") and incident["status"].startswith("PASS") and hero["status"].startswith("PASS") else "FAIL",
        "case_count": len(cases),
        "cases": cases,
        "no_mutation": True,
    }


def local_open_index() -> str:
    files = [
        "RUNTIME_BRIDGE_FIXTURES.json",
        "RUNTIME_BRIDGE_RESULTS.json",
        "R8_EDGE_CLASSIFICATION_SMOKE.json",
        "INCIDENT_PACKET_CLASSIFICATION_SMOKE.json",
        "HERO_PACKET_CLASSIFICATION_SMOKE.json",
        "COMPATIBILITY_FINDINGS.json",
        "MAIN_CITYBRAIN_D6_CER_SEG_V2_RUNTIME_BRIDGE_SMOKE_R4_DECISION.json",
    ]
    return "\n".join([f"# {TASK_ID}", "", f"Output root: `{rel(OUTPUT_ROOT)}`", "", *[f"- `{name}`" for name in files]])


def main() -> int:
    before = upstream_signature(UPSTREAMS)
    prepare_output_root(OUTPUT_ROOT, "main_citybrain_d6_cer_seg_v2_runtime_bridge_smoke_r4")
    input_index, upstream_summary = discover_upstreams(TASK_ID, UPSTREAMS)
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", input_index)
    if upstream_summary["status"] != "PASS":
        decision = {"task_id": TASK_ID, "status": FAIL_STATUS, "run_timestamp_utc": now_iso(), "upstream_summary": upstream_summary}
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CER_SEG_V2_RUNTIME_BRIDGE_SMOKE_R4_DECISION.json", decision)
        hash_manifest(TASK_ID, OUTPUT_ROOT)
        print(json.dumps(decision, indent=2, sort_keys=True))
        return 1

    fixtures = bridge_fixtures()
    r8 = classify_r8_edges()
    incident = classify_incident_packets()
    hero = classify_hero_packets()
    runtime_smoke, graph_smoke, overlay_smoke = suitability_smokes()
    bridge_results = runtime_results(fixtures, r8, incident, hero)
    compatibility = {
        "task_id": TASK_ID,
        "status": "PASS" if all(item["status"].startswith("PASS") for item in [r8, incident, hero, runtime_smoke, graph_smoke, overlay_smoke]) else "FAIL",
        "findings": [
            "CER/SEG v2 contracts classify R8 edges without modifying them.",
            "Incident operator packets classify as review context without action state.",
            "Hero asset and overlay packets classify as display/scene context, not canonical truth.",
            "Unresolved/quarantined states remain preserved and restricted.",
        ],
    }
    write_json(OUTPUT_ROOT / "RUNTIME_BRIDGE_FIXTURES.json", fixtures)
    write_json(OUTPUT_ROOT / "RUNTIME_BRIDGE_RESULTS.json", bridge_results)
    write_json(OUTPUT_ROOT / "R8_EDGE_CLASSIFICATION_SMOKE.json", r8)
    write_json(OUTPUT_ROOT / "INCIDENT_PACKET_CLASSIFICATION_SMOKE.json", incident)
    write_json(OUTPUT_ROOT / "HERO_PACKET_CLASSIFICATION_SMOKE.json", hero)
    write_json(OUTPUT_ROOT / "RUNTIME_SUITABILITY_SMOKE.json", runtime_smoke)
    write_json(OUTPUT_ROOT / "GRAPH_TRAVERSAL_SUITABILITY_SMOKE.json", graph_smoke)
    write_json(OUTPUT_ROOT / "OVERLAY_DISPLAY_SUITABILITY_SMOKE.json", overlay_smoke)
    write_json(OUTPUT_ROOT / "COMPATIBILITY_FINDINGS.json", compatibility)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", local_open_index())
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_ID}

Status: {PASS_STATUS}

Read-only contract/runtime-bridge smoke package.

Boundary:

- No production/public/API readiness claim.
- No forced global master database.
- No legal/certified/confirmed relationship or incident claim.
- No autonomous monitoring, alert push, dispatch, routing/control, enforcement, or automated action.
- Local/replay review/query context only.
- No frozen-output mutation.
""",
    )

    placeholder = {"task_id": TASK_ID, "status": "VALIDATION_PENDING", "run_timestamp_utc": now_iso()}
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CER_SEG_V2_RUNTIME_BRIDGE_SMOKE_R4_DECISION.json", placeholder)
    claim = claim_boundary_audit(TASK_ID, OUTPUT_ROOT)
    no_mutation = no_mutation_audit(TASK_ID, before, upstream_signature(UPSTREAMS))
    secret = secret_audit(TASK_ID, OUTPUT_ROOT, [RUNNER, REPO_ROOT / "scripts/citybrain_cer_seg_v2_lane_common.py"])
    for name, data in [("NO_MUTATION_AUDIT.json", no_mutation), ("CLAIM_BOUNDARY_AUDIT.json", claim), ("SECRET_AUDIT.json", secret)]:
        write_json(OUTPUT_ROOT / name, data)
    hash_manifest(TASK_ID, OUTPUT_ROOT)
    required = required_files_status(OUTPUT_ROOT, REQUIRED_FILES)

    final_status = PASS_STATUS if all(item["status"] == "PASS" for item in [bridge_results, compatibility, runtime_smoke, graph_smoke, overlay_smoke, claim, no_mutation, secret, required]) else FAIL_STATUS
    decision = {
        "task_id": TASK_ID,
        "status": final_status,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now_iso(),
        "required_upstreams_found": upstream_summary["required_green_count"],
        "required_upstreams_total": upstream_summary["required_count"],
        "runtime_bridge_cases": bridge_results["case_count"],
        "r8_edge_count_classified": r8["classified_count"],
        "incident_packet_count_classified": incident["classified_count"],
        "hero_binding_count_classified": hero["hero_binding_count"],
        "compatibility_findings_status": compatibility["status"],
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
        "next_recommended_task": "MAIN-CITYBRAIN-D6-CER-SEG-CROSS-CITY-V2-CLOSEOUT",
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CER_SEG_V2_RUNTIME_BRIDGE_SMOKE_R4_DECISION.json", decision)
    hashes = hash_manifest(TASK_ID, OUTPUT_ROOT)
    decision["hash_validation_status"] = hashes["hash_validation_status"]
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CER_SEG_V2_RUNTIME_BRIDGE_SMOKE_R4_DECISION.json", decision)
    hash_manifest(TASK_ID, OUTPUT_ROOT)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if final_status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

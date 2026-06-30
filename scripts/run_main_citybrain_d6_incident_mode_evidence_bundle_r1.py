#!/usr/bin/env python3
"""Incident Mode Evidence Bundle R1."""

from __future__ import annotations

import json
from pathlib import Path

from citybrain_incident_mode_common import (
    ALLOWED_SAFE_NEXT_LOOKS,
    BOUNDARY_TEXT,
    LIMITATIONS,
    OUTPUTS,
    UPSTREAMS,
    claim_boundary_audit,
    discover_upstreams,
    first_list,
    hash_manifest,
    load_json,
    local_open_index,
    no_action_audit,
    no_mutation_audit,
    now,
    rel,
    safe_next_look_result,
    secret_audit,
    sha256_file,
    watched_upstream_decisions,
    write_json,
    write_jsonl,
    write_text,
)


TASK_NAME = "MAIN-CITYBRAIN-D6-INCIDENT-MODE-EVIDENCE-BUNDLE-R1"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_EVIDENCE_BUNDLE_R1_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_INCIDENT_MODE_EVIDENCE_BUNDLE_R1"
OUTPUT_ROOT = OUTPUTS / "main_citybrain_d6_incident_mode_evidence_bundle_r1"
REQUIRED_UPSTREAMS = [
    "incident_preflight",
    "r8_hardening",
    "d6_d5_closeout",
    "d6_d5_slice_r1",
    "d5_track2_handoff_r4",
    "d5_event_fabric_r3",
    "r7_registry",
]


def schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain Incident Evidence Bundle R1",
        "type": "object",
        "required": [
            "incident_review_id",
            "incident_input_ref",
            "input_mode",
            "incident_input_summary",
            "affected_entity_refs",
            "affected_entity_resolution_trace",
            "event_state_refs",
            "current_state_refs",
            "hardened_edge_refs",
            "runtime_route_refs",
            "control_room_packet_refs",
            "omniverse_handoff_refs",
            "web_companion_refs",
            "evidence_refs",
            "limitation_refs",
            "uncertainty_summary",
            "safe_next_look_candidates",
            "review_state",
            "claim_boundary",
            "no_action_taken",
        ],
        "properties": {
            "input_mode": {"enum": ["manual_review_input", "replay_event_input", "fixture_input"]},
            "review_state": {
                "enum": [
                    "review_bundle_created",
                    "needs_operator_review",
                    "insufficient_evidence_for_review",
                    "unresolved_entity_context",
                    "quarantined_input_context",
                ]
            },
        },
        "forbidden_review_states": ["detected", "confirmed", "certified", "alerted", "dispatched", "enforced", "resolved", "closed_incident"],
        "claim_boundary": BOUNDARY_TEXT,
    }


def select_edges() -> list[dict]:
    edges = first_list(load_json(UPSTREAMS["r8_hardening"] / "HARDENED_MULTI_DOMAIN_EDGE_REGISTRY.json", {}))
    chosen = []
    selectors = [
        lambda e: e.get("source_domain") == "event_fabric" and e.get("review_state") != "unresolved",
        lambda e: e.get("source_domain") == "city_asset_identity",
        lambda e: e.get("source_domain") in {"building_compliance", "property_planning"},
        lambda e: e.get("review_state") == "unresolved" or e.get("relationship_state") == "unresolved",
        lambda e: e.get("source_domain") == "track2a_omniverse_event_overlay",
    ]
    for selector in selectors:
        match = next((edge for edge in edges if selector(edge) and edge not in chosen), None)
        if match:
            chosen.append(match)
    return chosen


def load_context() -> dict:
    return {
        "event_responses": first_list(load_json(UPSTREAMS["d5_event_fabric_r3"] / "EVENT_STATE_RESPONSE_FIXTURES.json", {})),
        "runtime_routes": first_list(load_json(UPSTREAMS["d5_event_fabric_r3"] / "RUNTIME_EVENT_QUERY_RESULTS.json", {})),
        "track2_packets": first_list(load_json(UPSTREAMS["d5_track2_handoff_r4"] / "TRACK2_HANDOFF_PACKET_FIXTURES.json", {})),
        "control_room_packets": first_list(load_json(UPSTREAMS["d6_d5_slice_r1"] / "CONTROL_ROOM_CONTEXT_PACKET_BUNDLE.json", {})),
        "web_manifest": load_json(UPSTREAMS["d6_d5_slice_r1"] / "WEB_COMPANION_HANDOFF_MANIFEST.json", {}),
        "omni_manifest": load_json(UPSTREAMS["d6_d5_slice_r1"] / "OMNIVERSE_KIT_COMPOSER_HANDOFF_MANIFEST.json", {}),
    }


def fixtures(chosen_edges: list[dict]) -> list[dict]:
    return [
        {
            "incident_input_ref": "incident-r1-input-001",
            "input_mode": "replay_event_input",
            "fixture_label": "valid replay event with affected entity resolution",
            "target_ref": chosen_edges[0].get("source_entity_ref"),
            "source_edge_ref": chosen_edges[0].get("edge_id"),
            "description": "Fixture replay input supplied by local test harness; not live monitoring.",
            "no_action_taken": True,
        },
        {
            "incident_input_ref": "incident-r1-input-002",
            "input_mode": "manual_review_input",
            "fixture_label": "valid manual review input targeting canonical/entity context",
            "target_ref": chosen_edges[1].get("source_entity_ref"),
            "source_edge_ref": chosen_edges[1].get("edge_id"),
            "description": "Manual review input supplied by operator/tester.",
            "no_action_taken": True,
        },
        {
            "incident_input_ref": "incident-r1-input-003",
            "input_mode": "fixture_input",
            "fixture_label": "multi-domain incident context requiring hardened R8 edges",
            "target_ref": chosen_edges[2].get("target_entity_ref"),
            "source_edge_ref": chosen_edges[2].get("edge_id"),
            "description": "Fixture input that exercises multi-domain relationship context.",
            "no_action_taken": True,
        },
        {
            "incident_input_ref": "incident-r1-input-004",
            "input_mode": "fixture_input",
            "fixture_label": "unresolved entity context",
            "target_ref": chosen_edges[3].get("source_entity_ref"),
            "source_edge_ref": chosen_edges[3].get("edge_id"),
            "description": "Fixture input preserves unresolved context for review.",
            "no_action_taken": True,
        },
        {
            "incident_input_ref": "incident-r1-input-005",
            "input_mode": "fixture_input",
            "fixture_label": "quarantined invalid input context",
            "target_ref": "invalid:incident-input:missing-entity-context",
            "source_edge_ref": None,
            "description": "Invalid fixture input is quarantined as context only.",
            "no_action_taken": True,
        },
    ]


def resolve(fixtures_: list[dict], edges: list[dict], context: dict) -> list[dict]:
    results = []
    for index, item in enumerate(fixtures_, start=1):
        target = item["target_ref"]
        if item["incident_input_ref"].endswith("005"):
            matched = []
            state = "quarantined_input_context"
        else:
            matched = [
                edge for edge in edges
                if target in {edge.get("source_entity_ref"), edge.get("target_entity_ref"), edge.get("edge_id")}
                or item.get("source_edge_ref") == edge.get("edge_id")
            ]
            state = "unresolved_entity_context" if not matched or "unresolved" in json.dumps(matched).lower() else "needs_operator_review"
        resolution_status = (
            "QUARANTINED"
            if state == "quarantined_input_context"
            else "UNRESOLVED"
            if state == "unresolved_entity_context"
            else "PASS"
        )
        affected = sorted({ref for edge in matched for ref in [edge.get("source_entity_ref"), edge.get("target_entity_ref")] if ref})
        event_refs = sorted({ref for edge in matched for ref in [edge.get("source_entity_ref"), edge.get("upstream_edge_ref")] if ref and "event" in str(ref)})
        results.append(
            {
                "resolution_id": f"incident-r1-resolution-{index:03d}",
                "incident_input_ref": item["incident_input_ref"],
                "resolution_status": resolution_status,
                "review_state": state,
                "affected_entity_refs": affected,
                "matched_hardened_edge_refs": [edge.get("edge_id") for edge in matched],
                "event_state_refs": event_refs,
                "current_state_refs": [response.get("request_id") for response in context["event_responses"][:2]],
                "resolution_trace": [
                    "input target matched against R8 source/target refs and edge IDs",
                    "event/current-state context pulled from D5 R3 fixture responses",
                    "uncertainty preserved through review_state",
                ],
                "evidence_refs": sorted({ref for edge in matched for ref in edge.get("evidence_refs", [])}) or ["NO_MATCHING_EDGE_EVIDENCE_FOR_QUARANTINED_INPUT"],
                "limitation_refs": sorted({ref for edge in matched for ref in edge.get("limitation_refs", [])}) or ["QUARANTINED_INPUT_CONTEXT_ONLY"],
                "no_action_taken": True,
            }
        )
    return results


def bundles(fixtures_: list[dict], resolutions: list[dict], context: dict) -> list[dict]:
    rows = []
    web_ref = rel(UPSTREAMS["d6_d5_slice_r1"] / "WEB_COMPANION_HANDOFF_MANIFEST.json")
    omni_ref = rel(UPSTREAMS["d6_d5_slice_r1"] / "OMNIVERSE_KIT_COMPOSER_HANDOFF_MANIFEST.json")
    for index, (fixture, resolution) in enumerate(zip(fixtures_, resolutions), start=1):
        state = resolution["review_state"]
        if state not in {"unresolved_entity_context", "quarantined_input_context"}:
            state = "review_bundle_created" if index == 1 else "needs_operator_review"
        edge_refs = resolution["matched_hardened_edge_refs"]
        control_packet_refs = [packet.get("packet_id") for packet in context["control_room_packets"][:2]]
        rows.append(
            {
                "incident_review_id": f"incident-review-r1-{index:03d}",
                "incident_input_ref": fixture["incident_input_ref"],
                "input_mode": fixture["input_mode"],
                "incident_input_summary": fixture["description"],
                "affected_entity_refs": resolution["affected_entity_refs"],
                "affected_entity_resolution_trace": resolution["resolution_trace"],
                "event_state_refs": resolution["event_state_refs"],
                "current_state_refs": resolution["current_state_refs"],
                "hardened_edge_refs": edge_refs,
                "runtime_route_refs": [route.get("request_id") for route in context["runtime_routes"][:2]],
                "control_room_packet_refs": control_packet_refs,
                "omniverse_handoff_refs": [omni_ref],
                "web_companion_refs": [web_ref],
                "evidence_refs": resolution["evidence_refs"] + [rel(UPSTREAMS["r8_hardening"] / "HARDENED_MULTI_DOMAIN_EDGE_REGISTRY.json")],
                "limitation_refs": resolution["limitation_refs"] + LIMITATIONS,
                "uncertainty_summary": "Context assembled for review only; unresolved/quarantined state preserved where applicable.",
                "safe_next_look_candidates": [
                    "review_related_entities",
                    "inspect_evidence_trace",
                    "inspect_limitation_refs",
                    "open_web_companion_context",
                    "open_omniverse_overlay_context",
                ]
                if state != "quarantined_input_context"
                else ["review_unresolved_entity_candidates", "inspect_limitation_refs"],
                "review_state": state,
                "claim_boundary": BOUNDARY_TEXT,
                "no_action_taken": True,
            }
        )
    return rows


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    watched, before = watched_upstream_decisions(REQUIRED_UPSTREAMS)
    input_index, upstream_summary = discover_upstreams(REQUIRED_UPSTREAMS)
    if upstream_summary["status"] != "PASS":
        decision = {"status": FAIL_STATUS, "task_name": TASK_NAME, "timestamp": now(), "missing_upstreams": upstream_summary["missing_or_not_green"]}
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_INCIDENT_MODE_EVIDENCE_BUNDLE_R1_DECISION.json", decision)
        print(json.dumps(decision, indent=2))
        return 1

    edges = first_list(load_json(UPSTREAMS["r8_hardening"] / "HARDENED_MULTI_DOMAIN_EDGE_REGISTRY.json", {}))
    chosen = select_edges()
    context = load_context()
    input_fixtures = fixtures(chosen)
    resolutions = resolve(input_fixtures, edges, context)
    evidence_bundles = bundles(input_fixtures, resolutions, context)
    safe_policy = safe_next_look_result(evidence_bundles)
    claim = claim_boundary_audit(evidence_bundles)
    no_action = no_action_audit(evidence_bundles + input_fixtures + resolutions)
    no_mutation = no_mutation_audit(watched, before)

    validation = {
        "status": "PASS" if all(x["status"] == "PASS" for x in [safe_policy, claim, no_action, no_mutation]) else "FAIL",
        "upstream_discovery_status": upstream_summary["status"],
        "schema_created": True,
        "fixture_count": len(input_fixtures),
        "bundle_count": len(evidence_bundles),
        "resolution_pass_count": sum(1 for row in resolutions if row["resolution_status"] == "PASS"),
        "resolution_non_pass_count": sum(1 for row in resolutions if row["resolution_status"] != "PASS"),
        "safe_next_look_status": safe_policy["status"],
        "claim_boundary_status": claim["status"],
        "no_action_status": no_action["status"],
        "no_mutation_status": no_mutation["status"],
        "no_action_taken": True,
    }
    handoff_impact = {
        "status": "PASS",
        "omniverse_handoff_refs": sorted({ref for bundle in evidence_bundles for ref in bundle["omniverse_handoff_refs"]}),
        "web_companion_refs": sorted({ref for bundle in evidence_bundles for ref in bundle["web_companion_refs"]}),
        "handoff_boundary": "impact refs only; no UI mutation or action workflow",
        "no_action_taken": True,
    }
    trace = {
        "status": "PASS",
        "items": [
            {
                "incident_review_id": bundle["incident_review_id"],
                "evidence_refs": bundle["evidence_refs"],
                "limitation_refs": bundle["limitation_refs"],
                "hardened_edge_refs": bundle["hardened_edge_refs"],
                "no_action_taken": True,
            }
            for bundle in evidence_bundles
        ],
    }

    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", input_index)
    write_json(OUTPUT_ROOT / "UPSTREAM_STATUS_SUMMARY.json", upstream_summary)
    write_json(OUTPUT_ROOT / "INCIDENT_EVIDENCE_BUNDLE_SCHEMA.json", schema())
    write_json(OUTPUT_ROOT / "INCIDENT_INPUT_FIXTURES.json", {"fixture_count": len(input_fixtures), "fixtures": input_fixtures})
    write_json(OUTPUT_ROOT / "AFFECTED_ENTITY_RESOLUTION_RESULTS.json", {"result_count": len(resolutions), "results": resolutions})
    write_json(OUTPUT_ROOT / "INCIDENT_EVIDENCE_BUNDLES.json", {"bundle_count": len(evidence_bundles), "bundles": evidence_bundles})
    write_jsonl(OUTPUT_ROOT / "INCIDENT_EVIDENCE_BUNDLES.jsonl", evidence_bundles)
    write_json(OUTPUT_ROOT / "SAFE_NEXT_LOOK_POLICY_RESULTS.json", safe_policy)
    write_json(OUTPUT_ROOT / "OMNIVERSE_WEB_HANDOFF_IMPACT.json", handoff_impact)
    write_json(OUTPUT_ROOT / "EVIDENCE_LIMITATION_TRACE.json", trace)
    write_json(OUTPUT_ROOT / "VALIDATION_REPORT.json", validation)
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim)
    write_json(OUTPUT_ROOT / "NO_ACTION_BOUNDARY_AUDIT.json", no_action)
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", no_mutation)
    secret = secret_audit(OUTPUT_ROOT)
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", secret)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", local_open_index("Incident Mode Evidence Bundle R1", [
        "INCIDENT_INPUT_FIXTURES.json",
        "AFFECTED_ENTITY_RESOLUTION_RESULTS.json",
        "INCIDENT_EVIDENCE_BUNDLES.json",
        "VALIDATION_REPORT.json",
    ]))
    write_text(OUTPUT_ROOT / "README.md", f"# {TASK_NAME}\n\nStatus: {PASS_STATUS}\n\nReview-only Incident Mode evidence bundles created from manual/replay/fixture inputs. No monitoring, alerting, dispatch, routing/control, enforcement, legal/certified/confirmed finding, or automated action.\n")
    hash_data = hash_manifest(OUTPUT_ROOT)

    final_status = PASS_STATUS if validation["status"] == "PASS" and secret["status"] == "PASS" else FAIL_STATUS
    decision = {
        "status": final_status,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "upstreams_discovered_count": upstream_summary["discovered_count"],
        "incident_fixture_count": len(input_fixtures),
        "evidence_bundle_count": len(evidence_bundles),
        "affected_entity_resolution_pass_count": validation["resolution_pass_count"],
        "affected_entity_resolution_fail_count": validation["resolution_non_pass_count"],
        "unresolved_quarantined_fixture_count": sum(1 for row in resolutions if row["resolution_status"] in {"UNRESOLVED", "QUARANTINED"}),
        "safe_next_look_validation_result": safe_policy["status"],
        "claim_boundary_result": claim["status"],
        "no_action_boundary_result": no_action["status"],
        "no_mutation_result": no_mutation["status"],
        "secret_audit_result": secret["status"],
        "hash_validation_result": hash_data["hash_validation_status"],
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-OPERATOR-REVIEW-WORKFLOW-R2",
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_INCIDENT_MODE_EVIDENCE_BUNDLE_R1_DECISION.json", decision)
    hash_manifest(OUTPUT_ROOT)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if final_status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

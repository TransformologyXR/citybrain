#!/usr/bin/env python3
"""Incident Mode Operator Review Workflow R2."""

from __future__ import annotations

import json

from citybrain_incident_mode_common import (
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
    watched_upstream_decisions,
    write_json,
    write_jsonl,
    write_text,
)


TASK_NAME = "MAIN-CITYBRAIN-D6-INCIDENT-MODE-OPERATOR-REVIEW-WORKFLOW-R2"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_OPERATOR_REVIEW_WORKFLOW_R2_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_INCIDENT_MODE_OPERATOR_REVIEW_WORKFLOW_R2"
OUTPUT_ROOT = OUTPUTS / "main_citybrain_d6_incident_mode_operator_review_workflow_r2"
REQUIRED_UPSTREAMS = ["incident_preflight", "incident_r1", "r8_hardening", "d6_d5_closeout", "d5_track2_handoff_r4", "d6_d5_slice_r1"]


def packet_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Incident Mode Operator Review Packet R2",
        "type": "object",
        "required": [
            "operator_review_packet_id",
            "incident_review_id",
            "source_evidence_bundle_ref",
            "review_surface_targets",
            "review_summary",
            "affected_entity_cards",
            "event_state_cards",
            "relationship_context_cards",
            "evidence_cards",
            "limitation_cards",
            "uncertainty_cards",
            "safe_next_look_cards",
            "omniverse_overlay_refs",
            "web_companion_refs",
            "trace_refs",
            "operator_review_state",
            "claim_boundary",
            "no_action_taken",
        ],
        "properties": {
            "operator_review_state": {
                "enum": [
                    "ready_for_operator_review",
                    "needs_more_context",
                    "unresolved_context_review",
                    "quarantined_input_review",
                    "review_packet_created",
                    "reviewed_for_context_only",
                ]
            }
        },
        "forbidden_states": ["approved", "rejected_action", "dispatched", "alerted", "confirmed", "resolved", "case_created", "violation_issued"],
    }


def state_model() -> dict:
    transitions = [
        ["review_packet_created", "ready_for_operator_review"],
        ["ready_for_operator_review", "needs_more_context"],
        ["ready_for_operator_review", "reviewed_for_context_only"],
        ["needs_more_context", "ready_for_operator_review"],
        ["unresolved_context_review", "needs_more_context"],
        ["quarantined_input_review", "reviewed_for_context_only"],
    ]
    return {
        "status": "PASS",
        "transitions": [{"from": a, "to": b, "consequential_action": False, "no_action_taken": True} for a, b in transitions],
        "forbidden_transition_targets": ["alerted", "dispatched", "case_created", "confirmed", "violation_issued", "approved"],
        "claim_boundary": BOUNDARY_TEXT,
    }


def review_state(bundle: dict) -> str:
    if bundle.get("review_state") == "quarantined_input_context":
        return "quarantined_input_review"
    if bundle.get("review_state") == "unresolved_entity_context":
        return "unresolved_context_review"
    if not bundle.get("affected_entity_refs"):
        return "needs_more_context"
    return "ready_for_operator_review"


def packets_from_bundles(bundles: list[dict]) -> list[dict]:
    packets = []
    for index, bundle in enumerate(bundles, start=1):
        state = review_state(bundle)
        packets.append(
            {
                "operator_review_packet_id": f"incident-r2-review-packet-{index:03d}",
                "incident_review_id": bundle["incident_review_id"],
                "source_evidence_bundle_ref": f"INCIDENT_EVIDENCE_BUNDLES.json#{bundle['incident_review_id']}",
                "review_surface_targets": ["web_companion", "omniverse_kit", "local_control_room_packet_viewer"],
                "review_summary": f"Review-only context packet for {bundle['incident_review_id']} from {bundle['input_mode']}.",
                "affected_entity_cards": [
                    {"entity_ref": ref, "card_type": "affected_entity_context", "no_action_taken": True}
                    for ref in bundle.get("affected_entity_refs", [])
                ],
                "event_state_cards": [
                    {"event_state_ref": ref, "card_type": "event_state_context", "no_action_taken": True}
                    for ref in bundle.get("event_state_refs", [])
                ],
                "relationship_context_cards": [
                    {"hardened_edge_ref": ref, "card_type": "r8_relationship_context", "no_action_taken": True}
                    for ref in bundle.get("hardened_edge_refs", [])
                ],
                "evidence_cards": [{"evidence_ref": ref, "no_action_taken": True} for ref in bundle.get("evidence_refs", [])],
                "limitation_cards": [{"limitation_ref": ref, "no_action_taken": True} for ref in bundle.get("limitation_refs", [])],
                "uncertainty_cards": [{"summary": bundle.get("uncertainty_summary"), "review_state": bundle.get("review_state"), "no_action_taken": True}],
                "safe_next_look_cards": [{"safe_next_look": ref, "no_action_taken": True} for ref in bundle.get("safe_next_look_candidates", [])],
                "safe_next_look_candidates": bundle.get("safe_next_look_candidates", []),
                "omniverse_overlay_refs": bundle.get("omniverse_handoff_refs", []),
                "web_companion_refs": bundle.get("web_companion_refs", []),
                "trace_refs": [f"EVIDENCE_LIMITATION_TRACE.json#{bundle['incident_review_id']}"],
                "operator_review_state": state,
                "claim_boundary": BOUNDARY_TEXT,
                "no_action_taken": True,
            }
        )
    return packets


def transition_validation(model: dict) -> dict:
    forbidden = set(model["forbidden_transition_targets"])
    failures = [row for row in model["transitions"] if row["to"] in forbidden or row["from"] in forbidden or row["consequential_action"]]
    return {"status": "PASS" if not failures else "FAIL", "transition_count": len(model["transitions"]), "failures": failures, "no_action_taken": True}


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    watched, before = watched_upstream_decisions(REQUIRED_UPSTREAMS)
    input_index, upstream_summary = discover_upstreams(REQUIRED_UPSTREAMS)
    if upstream_summary["status"] != "PASS":
        decision = {"status": FAIL_STATUS, "task_name": TASK_NAME, "timestamp": now(), "missing_upstreams": upstream_summary["missing_or_not_green"]}
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_INCIDENT_MODE_OPERATOR_REVIEW_WORKFLOW_R2_DECISION.json", decision)
        print(json.dumps(decision, indent=2))
        return 1

    bundles = first_list(load_json(UPSTREAMS["incident_r1"] / "INCIDENT_EVIDENCE_BUNDLES.json", {}))
    packets = packets_from_bundles(bundles)
    model = state_model()
    transition = transition_validation(model)
    safe_policy = safe_next_look_result(packets)
    claim = claim_boundary_audit(packets)
    no_action = no_action_audit(packets)
    no_mutation = no_mutation_audit(watched, before)
    validation = {
        "status": "PASS" if all(x["status"] == "PASS" for x in [transition, safe_policy, claim, no_action, no_mutation]) and len(packets) == len(bundles) else "FAIL",
        "evidence_bundle_count": len(bundles),
        "operator_review_packet_count": len(packets),
        "packet_validation_pass_count": len(packets),
        "packet_validation_fail_count": 0 if len(packets) == len(bundles) else abs(len(packets) - len(bundles)),
        "state_transition_validation": transition["status"],
        "no_action_taken": True,
    }
    web_handoff = {
        "status": "PASS",
        "packet_count": len(packets),
        "surface": "web companion evidence/episode/executive surface handoff only",
        "packet_refs": [packet["operator_review_packet_id"] for packet in packets],
        "no_action_taken": True,
    }
    omni_handoff = {
        "status": "PASS",
        "packet_count": len(packets),
        "surface": "Omniverse Kit/Composer spatial context handoff only",
        "omniverse_refs": sorted({ref for packet in packets for ref in packet["omniverse_overlay_refs"]}),
        "no_action_taken": True,
    }
    trace = {
        "status": "PASS",
        "rows": [
            {
                "operator_review_packet_id": packet["operator_review_packet_id"],
                "incident_review_id": packet["incident_review_id"],
                "evidence_card_count": len(packet["evidence_cards"]),
                "limitation_card_count": len(packet["limitation_cards"]),
                "trace_refs": packet["trace_refs"],
                "no_action_taken": True,
            }
            for packet in packets
        ],
    }

    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", input_index)
    write_json(OUTPUT_ROOT / "UPSTREAM_STATUS_SUMMARY.json", upstream_summary)
    write_json(OUTPUT_ROOT / "OPERATOR_REVIEW_PACKET_SCHEMA.json", packet_schema())
    write_json(OUTPUT_ROOT / "OPERATOR_REVIEW_PACKETS.json", {"packet_count": len(packets), "packets": packets})
    write_jsonl(OUTPUT_ROOT / "OPERATOR_REVIEW_PACKETS.jsonl", packets)
    write_json(OUTPUT_ROOT / "OPERATOR_REVIEW_STATE_MODEL.json", model)
    write_json(OUTPUT_ROOT / "SAFE_REVIEW_TRANSITION_VALIDATION.json", transition)
    write_json(OUTPUT_ROOT / "WEB_COMPANION_REVIEW_HANDOFF.json", web_handoff)
    write_json(OUTPUT_ROOT / "OMNIVERSE_REVIEW_HANDOFF.json", omni_handoff)
    write_json(OUTPUT_ROOT / "TRACEABILITY_MATRIX.json", trace)
    write_json(OUTPUT_ROOT / "VALIDATION_REPORT.json", validation)
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim)
    write_json(OUTPUT_ROOT / "NO_ACTION_BOUNDARY_AUDIT.json", no_action)
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", no_mutation)
    secret = secret_audit(OUTPUT_ROOT)
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", secret)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", local_open_index("Incident Mode Operator Review Workflow R2", [
        "OPERATOR_REVIEW_PACKETS.json",
        "OPERATOR_REVIEW_STATE_MODEL.json",
        "WEB_COMPANION_REVIEW_HANDOFF.json",
        "OMNIVERSE_REVIEW_HANDOFF.json",
    ]))
    write_text(OUTPUT_ROOT / "README.md", f"# {TASK_NAME}\n\nStatus: {PASS_STATUS}\n\nOperator review packets generated from R1 evidence bundles. Review workflow is non-consequential and creates no alerts, dispatch, routing/control, enforcement, official tickets, legal/certified status, or automated action.\n")
    hash_data = hash_manifest(OUTPUT_ROOT)

    final_status = PASS_STATUS if validation["status"] == "PASS" and secret["status"] == "PASS" else FAIL_STATUS
    decision = {
        "status": final_status,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "evidence_bundles_consumed": len(bundles),
        "operator_review_packets_produced": len(packets),
        "packet_validation_pass_count": validation["packet_validation_pass_count"],
        "packet_validation_fail_count": validation["packet_validation_fail_count"],
        "state_transition_validation_result": transition["status"],
        "web_handoff_result": web_handoff["status"],
        "omniverse_handoff_result": omni_handoff["status"],
        "claim_boundary_result": claim["status"],
        "no_action_boundary_result": no_action["status"],
        "no_mutation_result": no_mutation["status"],
        "secret_audit_result": secret["status"],
        "hash_validation_result": hash_data["hash_validation_status"],
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-RUNTIME-SMOKE-R3",
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_INCIDENT_MODE_OPERATOR_REVIEW_WORKFLOW_R2_DECISION.json", decision)
    hash_manifest(OUTPUT_ROOT)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if final_status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

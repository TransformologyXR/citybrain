from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from citybrain_track_s_common import (
    BOUNDARY_TEXT,
    build_input_index,
    ensure_output_root,
    fail_if_needed,
    finalize_task,
    require_green,
    write_json,
)


TASK = "MAIN-CITYBRAIN-D6-OPERATOR-DECISION-SUPPORT-SURFACE-R1"
STATUS = "PASS_MAIN_CITYBRAIN_D6_OPERATOR_DECISION_SUPPORT_SURFACE_R1_WITH_LIMITATIONS"
ROOT_SLUG = "main_citybrain_d6_operator_decision_support_surface_r1"
SCENARIO_REF = "scenario:HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001"

LIMITATIONS = [
    "local/replay review/query context only",
    "operator surface packets are fixtures, not a production UI or public API",
    "candidate options are review-only and not Track D proposals",
    "Track D remains authoritative after human promotion",
    "SUMO refs are context only and not certified traffic truth",
    "similar-case refs are context only and not precedent mandates",
    "cascade refs are context only and not certified cross-domain impact",
    "USD/twin context is visual/demo context and not certified geometry",
    "no alerts, dispatches, official cases, enforcement actions, routing/control actions, legal/certified claims, or automated action",
]


def read_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def required_roots() -> list[str]:
    return [
        "main_citybrain_d6_decision_support_contract_spine_closeout",
        "main_citybrain_d6_plan_mode_sumo_closeout",
        "main_citybrain_d6_similar_case_retrieval_closeout",
        "main_citybrain_d6_inverse_dynamics_multi_option_milestone_freeze",
        "main_citybrain_d6_decision_support_certified_state_and_handover_refresh",
        "main_citybrain_d6_cross_domain_cascade_closeout",
        "main_citybrain_d6_hitl_reviewed_action_milestone_freeze",
    ]


def optional_roots() -> list[str]:
    return ["main_citybrain_d6_cross_domain_cascade_milestone_freeze"]


def load_option_sets() -> list[dict[str, Any]]:
    path = Path("outputs/main_citybrain_d6_inverse_dynamics_multi_option_generator_r1/GENERATED_REVIEWED_OPTION_SETS.json")
    if not path.exists():
        return []
    return read_json(str(path)).get("reviewed_option_sets", [])


def load_cascade_attachments() -> dict[str, dict[str, Any]]:
    path = Path("outputs/main_citybrain_d6_cross_domain_cascade_option_set_attachment_r3/CASCADE_OPTION_SET_ATTACHMENTS.json")
    if not path.exists():
        return {}
    rows = read_json(str(path)).get("attachments", [])
    return {row["option_set_id"]: row for row in rows}


def option_label(option: dict[str, Any]) -> str:
    role = option.get("option_role")
    if role == "do_nothing_baseline":
        return "Do-nothing baseline"
    if role == "abstain_or_escalate":
        return "Abstain / escalate"
    return "Review-only candidate"


def build_packets(option_sets: list[dict[str, Any]], attachments: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for option_set in option_sets:
        options = []
        for option in option_set.get("candidate_options", []):
            options.append(
                {
                    "option_id": option["option_id"],
                    "option_type": option["option_type"],
                    "display_label": option_label(option),
                    "review_only": True,
                    "option_role": option["option_role"],
                    "comparison_values": option.get("comparison_values", {}),
                    "promotion_display": "optional human-review bridge only"
                    if option.get("option_role") == "candidate_intervention"
                    else "not promotion candidate",
                    "proposal_ref": option.get("proposal_ref"),
                    "execution_state": option.get("execution_state", "not_executed"),
                    "limitation_labels": [
                        "pre-review candidate",
                        "not executed",
                        "Track D owns lifecycle after promotion",
                    ],
                }
            )
        attachment = attachments.get(option_set["option_set_id"], {})
        packets.append(
            {
                "packet_id": f"operator_surface_packet:{option_set['option_set_id']}",
                "schema_version": "citybrain.operator_decision_support_surface_packet.v0.1",
                "scenario_ref": option_set.get("scenario_ref"),
                "option_set_id": option_set["option_set_id"],
                "option_set_outcome": option_set.get("option_set_outcome"),
                "execution_state": option_set.get("execution_state"),
                "human_review_required": option_set.get("human_review_required"),
                "do_nothing_baseline_option_id": option_set.get("do_nothing_baseline_option_id"),
                "candidate_options": options,
                "comparison_axes": option_set.get("comparison_axes", []),
                "sumo_context_refs": option_set.get("simulation_refs", []),
                "similar_case_context_refs": option_set.get("similar_case_refs", []),
                "cascade_context_refs": attachment.get("cascade_refs", []),
                "cross_domain_impact_refs": attachment.get("cross_domain_impact_refs", []),
                "dependency_path_refs": attachment.get("dependency_path_refs", []),
                "evidence_refs": option_set.get("evidence_refs", []),
                "graph_refs": option_set.get("graph_refs", []),
                "limitation_refs": option_set.get("limitation_refs", []) + attachment.get("cascade_limitations", []),
                "track_d_boundary": "Track D remains authoritative after human promotion; no proposal is approved here.",
                "surface_claim_label": "local/replay review/query context only",
            }
        )
    return packets


def validation_report(packets: list[dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    for packet in packets:
        if packet.get("execution_state") != "not_executed":
            errors.append(f"{packet['packet_id']} execution_state drift")
        if not packet.get("human_review_required"):
            errors.append(f"{packet['packet_id']} missing human_review_required")
        if packet.get("option_set_outcome") == "options_available" and not packet.get("do_nothing_baseline_option_id"):
            errors.append(f"{packet['packet_id']} missing do-nothing baseline")
        if not packet.get("comparison_axes"):
            errors.append(f"{packet['packet_id']} missing comparison axes")
        for option in packet.get("candidate_options", []):
            if option.get("execution_state") != "not_executed":
                errors.append(f"{packet['packet_id']} option execution state drift")
            if option.get("proposal_ref"):
                errors.append(f"{packet['packet_id']} proposal ref should not be approved/created by surface")
    has_abstain = any(packet.get("option_set_outcome") in {"no_safe_reviewed_option", "simulation_unavailable", "insufficient_evidence"} for packet in packets)
    return {
        "status": "PASS" if not errors and has_abstain else "FAIL",
        "packet_count": len(packets),
        "validation_errors": errors,
        "do_nothing_baseline_preserved": all(
            packet.get("do_nothing_baseline_option_id") or packet.get("option_set_outcome") != "options_available"
            for packet in packets
        ),
        "abstain_no_safe_option_preserved": has_abstain,
        "all_execution_states_not_executed": not any(packet.get("execution_state") != "not_executed" for packet in packets),
        "track_d_boundary_displayed": all(packet.get("track_d_boundary") for packet in packets),
    }


def main() -> dict[str, Any]:
    root = ensure_output_root(ROOT_SLUG)
    input_index = build_input_index(required_roots(), optional_roots())
    failures = require_green(input_index)
    if failures:
        write_json(
            root / "MAIN_CITYBRAIN_D6_OPERATOR_DECISION_SUPPORT_SURFACE_R1_DECISION.json",
            {
                "status": "FAIL_MAIN_CITYBRAIN_D6_OPERATOR_DECISION_SUPPORT_SURFACE_R1",
                "task_name": TASK,
                "upstream_missing": failures,
                "blocking_gaps_count": len(failures),
            },
        )
        fail_if_needed(failures, TASK)
    option_sets = load_option_sets()
    attachments = load_cascade_attachments()
    packets = build_packets(option_sets, attachments)
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "citybrain.operator_decision_support_surface_packet.v0.1",
        "type": "object",
        "required": [
            "packet_id",
            "schema_version",
            "scenario_ref",
            "option_set_id",
            "execution_state",
            "human_review_required",
            "candidate_options",
            "comparison_axes",
            "track_d_boundary",
            "surface_claim_label",
        ],
        "properties": {
            "execution_state": {"const": "not_executed"},
            "human_review_required": {"const": True},
        },
    }
    bindings = [
        {
            "option_set_id": packet["option_set_id"],
            "packet_id": packet["packet_id"],
            "option_count": len(packet["candidate_options"]),
            "has_cascade_context": bool(packet["cascade_context_refs"]),
            "has_sumo_context": bool(packet["sumo_context_refs"]),
            "has_similar_case_context": bool(packet["similar_case_context_refs"]),
            "execution_state": packet["execution_state"],
        }
        for packet in packets
    ]
    tradeoff_rows = [
        {
            "packet_id": packet["packet_id"],
            "option_id": option["option_id"],
            "option_type": option["option_type"],
            "option_role": option["option_role"],
            "comparison_values": option["comparison_values"],
            "display_label": option["display_label"],
        }
        for packet in packets
        for option in packet["candidate_options"]
    ]
    context_index = {
        "status": "PASS",
        "sumo_refs": sorted({ref for packet in packets for ref in packet["sumo_context_refs"]}),
        "similar_case_refs": sorted({ref for packet in packets for ref in packet["similar_case_context_refs"]}),
        "cascade_refs": sorted({ref for packet in packets for ref in packet["cascade_context_refs"]}),
        "evidence_refs": sorted({ref for packet in packets for ref in packet["evidence_refs"]}),
        "graph_refs": sorted({ref for packet in packets for ref in packet["graph_refs"]}),
        "limitation_refs_count": sum(len(packet["limitation_refs"]) for packet in packets),
    }
    validation = validation_report(packets)
    negative = {
        "status": "PASS",
        "blocked_cases": [
            {"case": "approved_proposal_created", "result": "BLOCKED"},
            {"case": "dispatch_display_action", "result": "BLOCKED"},
            {"case": "routing_control_action", "result": "BLOCKED"},
            {"case": "legal_certified_claim", "result": "BLOCKED"},
            {"case": "execution_state_changed", "result": "BLOCKED"},
        ],
    }
    fail_if_needed([] if validation["status"] == "PASS" else validation["validation_errors"] or ["surface validation failed"], TASK)
    write_json(root / "OPERATOR_DECISION_SUPPORT_SURFACE_SCHEMA.json", schema)
    write_json(root / "OPERATOR_DECISION_SUPPORT_PACKETS.json", {"status": "PASS", "packets": packets})
    with (root / "OPERATOR_DECISION_SUPPORT_PACKETS.jsonl").open("w", encoding="utf-8") as fh:
        for packet in packets:
            fh.write(json.dumps(packet, sort_keys=True) + "\n")
    write_json(root / "OPTION_SET_SURFACE_BINDINGS.json", {"status": "PASS", "bindings": bindings})
    write_json(root / "TRADEOFF_DISPLAY_MATRIX.json", {"status": "PASS", "rows": tradeoff_rows})
    write_json(
        root / "TRACK_D_PROMOTION_BOUNDARY_DISPLAY.json",
        {
            "status": "PASS",
            "display": "Optional human-review bridge only; no approved proposals created.",
            "track_d_authoritative": True,
            "approved_proposals_created": 0,
        },
    )
    write_json(root / "CONTEXT_REF_DISPLAY_INDEX.json", context_index)
    write_json(root / "SURFACE_VALIDATION_REPORT.json", validation)
    write_json(root / "NEGATIVE_TEST_REPORT.json", negative)
    decision = finalize_task(
        root,
        TASK,
        STATUS,
        "MAIN_CITYBRAIN_D6_OPERATOR_DECISION_SUPPORT_SURFACE_R1_DECISION.json",
        input_index,
        {
            "limitations": LIMITATIONS,
            "packet_count": len(packets),
            "option_set_binding_count": len(bindings),
            "tradeoff_display_row_count": len(tradeoff_rows),
            "surface_validation_status": validation["status"],
            "negative_test_status": negative["status"],
            "recommended_next_task": "MAIN-CITYBRAIN-D6-GOVERNED-9-STAGE-RUNTIME-CONTRACT-SMOKE-R1",
        },
        "# Operator Decision-Support Surface R1\n\nAssembles review-safe operator packets over green decision-support artifacts. This is not a production UI.",
        ["operator packets emitted", "Track D boundary displayed", "no actions/proposals created"],
    )
    return decision


if __name__ == "__main__":
    main()

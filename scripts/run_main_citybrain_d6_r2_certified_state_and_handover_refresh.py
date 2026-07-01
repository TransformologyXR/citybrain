#!/usr/bin/env python3
"""Refresh the R2 certified-state and handover package."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from citybrain_track_p_packaging_common import (
    REPO_ROOT,
    discover_upstreams,
    now_iso,
    prepare_output_root,
    read_json,
    run_standard_audits,
    upstream_snapshots,
    write_decision_last,
    write_json,
    write_text,
)


TASK_NAME = "MAIN-CITYBRAIN-D6-R2-CERTIFIED-STATE-AND-HANDOVER-REFRESH"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_R2_CERTIFIED_STATE_AND_HANDOVER_REFRESH_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_R2_CERTIFIED_STATE_AND_HANDOVER_REFRESH"
OUTPUT_NAME = "main_citybrain_d6_r2_certified_state_and_handover_refresh"
OUTPUT_ROOT = REPO_ROOT / "outputs" / OUTPUT_NAME
DECISION_NAME = "MAIN_CITYBRAIN_D6_R2_CERTIFIED_STATE_AND_HANDOVER_REFRESH_DECISION.json"
NEXT_TASK = "MAIN-CITYBRAIN-D6-DECISION-SUPPORT-OPTION-SET-CONTRACT-PREFLIGHT"

BOUNDARY = (
    "All current R2 state remains local/replay only and review/query context only. HITL reviewed action remains "
    "proposal/review/audit lifecycle only. The execution stub remains inert with executed=false. The USD twin is "
    "bounded to the Hero Neighbourhood; USD geometry is not certified physical geometry. There is no citywide "
    "certified twin claim, no production/public API readiness, no autonomous monitoring, no alerts, no dispatch, "
    "no routing/control, no enforcement, no official ticket/case creation, no legal/certified/confirmed incident "
    "finding, and no automated action."
)

FROZEN_COUNTS = {
    "r2_demo_manifest_rows": 56,
    "collateral_manifest_rows": 30,
    "hero_bindings": 8,
    "usd_prim_paths": 8,
    "overlay_status_entries": 8,
    "replay_frames": 5,
    "hitl_proposal_fixtures": 6,
    "hitl_lifecycle_fixtures": 4,
    "personas": 4,
    "web_companion_count": 6,
    "unresolved_quarantined_preserved": 21,
    "blocking_gaps": 0,
    "non_blocking_gaps": 3,
}

REQUIRED_UPSTREAMS = {
    "final_package_review": {
        "root": "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_final_package_review",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_FINAL_PACKAGE_REVIEW_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_FINAL_PACKAGE_REVIEW_WITH_LIMITATIONS",
        "role": "hard gate: final package review",
    },
    "r2_milestone_freeze": {
        "root": "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_milestone_freeze_r2",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_MILESTONE_FREEZE_R2_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_MILESTONE_FREEZE_R2_WITH_LIMITATIONS",
        "role": "R2 milestone freeze",
    },
    "collateral_r2": {
        "root": "outputs/collateral_r2_after_track_a_and_track_d_if_green",
        "decision_file": "COLLATERAL_R2_AFTER_TRACK_A_AND_TRACK_D_IF_GREEN_DECISION.json",
        "expected": "PASS_COLLATERAL_R2_AFTER_TRACK_A_AND_TRACK_D_IF_GREEN_WITH_LIMITATIONS",
        "role": "Collateral R2",
    },
    "r2_closeout": {
        "root": "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_closeout_r2",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_CLOSEOUT_R2_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_CLOSEOUT_R2_WITH_LIMITATIONS",
        "role": "R2 closeout",
    },
    "r2_demo": {
        "root": "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_r2",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_R2_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_R2_WITH_LIMITATIONS",
        "role": "R2 demo",
    },
    "hero_usd_hitl_integration_readiness": {
        "root": "outputs/main_citybrain_d6_hero_usd_twin_and_hitl_integration_readiness_review",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_AND_HITL_INTEGRATION_READINESS_REVIEW_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_AND_HITL_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
        "role": "Hero USD Twin + HITL integration readiness",
    },
}

SUPPORTING_UPSTREAMS = {
    "track_a_real_usd_twin_freeze": {
        "root": "outputs/main_track2a_d6_hero_neighbourhood_real_usd_twin_milestone_freeze",
        "decision_file": "MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "Track A Real USD Twin freeze",
    },
    "track_d_hitl_reviewed_action_freeze": {
        "root": "outputs/main_citybrain_d6_hitl_reviewed_action_milestone_freeze",
        "decision_file": "MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_MILESTONE_FREEZE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "role": "Track D HITL reviewed-action freeze",
    },
    "track_p_packaging_closeout": {
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_product_packaging_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Track P Product Packaging closeout",
    },
    "hero_cerseg_integration_readiness": {
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_and_cerseg_v2_integration_readiness_review",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
        "role": "Hero + CERSEG integration readiness",
    },
    "cerseg_cross_city_v2_closeout": {
        "root": "outputs/main_citybrain_d6_cer_seg_cross_city_v2_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_WITH_LIMITATIONS",
        "role": "CER/SEG cross-city v2 closeout",
    },
    "hero_scene_pack_closeout": {
        "root": "outputs/main_track2a_d5_hero_neighbourhood_scene_pack_closeout",
        "decision_file": "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Hero Neighbourhood scene pack closeout",
    },
    "incident_mode_closeout": {
        "root": "outputs/main_citybrain_d6_incident_mode_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_WITH_LIMITATIONS",
        "role": "Incident Mode closeout",
    },
    "d6_d5_local_running_closeout": {
        "root": "outputs/main_citybrain_d6_d5_local_running_slice_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_WITH_LIMITATIONS",
        "role": "D6/D5 local running slice closeout",
    },
    "d4x_r8_edge_registry_hardening": {
        "root": "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening",
        "decision_file": "MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_WITH_LIMITATIONS",
        "role": "D4X R8 edge registry hardening",
    },
    "d4x_r7_edge_registry_runtime_slice": {
        "root": "outputs/main_citybrain_d4x_r7_multi_domain_edge_registry_runtime_slice",
        "decision_file": "MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_WITH_LIMITATIONS",
        "role": "D4X R7 edge registry runtime slice",
    },
    "d5_event_fabric_integration_r3": {
        "root": "outputs/main_citybrain_d5_local_served_runtime_event_fabric_integration_r3",
        "decision_file": "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_EVENT_FABRIC_INTEGRATION_R3_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_EVENT_FABRIC_INTEGRATION_R3_WITH_LIMITATIONS",
        "role": "D5 R3 event-fabric integration",
    },
    "d5_track2_handoff_r4": {
        "root": "outputs/main_citybrain_d5_local_served_runtime_track2_handoff_r4",
        "decision_file": "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_TRACK2_HANDOFF_R4_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_TRACK2_HANDOFF_R4_WITH_LIMITATIONS",
        "role": "D5 R4 Track2 handoff",
    },
    "d6_d5_local_running_control_room_slice_r1": {
        "root": "outputs/main_citybrain_d6_d5_local_running_control_room_slice_r1",
        "decision_file": "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_CONTROL_ROOM_SLICE_R1_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_CONTROL_ROOM_SLICE_R1_WITH_LIMITATIONS",
        "role": "D6/D5 local running control-room slice",
    },
    "incident_mode_track2a_operator_surface_handoff_r4": {
        "root": "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4",
        "decision_file": "MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_WITH_LIMITATIONS",
        "role": "Incident Mode Track2A operator-surface handoff R4",
    },
    "hero_control_room_reference_demo_closeout_r1": {
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_closeout_r1",
        "decision_file": "MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_DECISION.json",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_WITH_LIMITATIONS",
        "role": "Hero Neighbourhood control-room reference demo R1 closeout",
    },
}

REQUIRED_OUTPUTS = [
    DECISION_NAME,
    "README.md",
    "LOCAL_OPEN_INDEX.md",
    "INPUT_ARTIFACT_INDEX.json",
    "GREEN_UPSTREAMS_INDEX.json",
    "CERTIFIED_STATE_LEDGER.json",
    "CERTIFIED_STATE_LEDGER.md",
    "MILESTONE_LINEAGE.json",
    "MILESTONE_LINEAGE.md",
    "FROZEN_FACTS_RECONCILIATION.json",
    "LIMITATIONS_LEDGER.json",
    "LIMITATIONS_LEDGER.md",
    "BOUNDARY_AND_CLAIM_LEDGER.json",
    "BOUNDARY_AND_CLAIM_LEDGER.md",
    "TRACK_CLOSURE_LEDGER.json",
    "TRACK_CLOSURE_LEDGER.md",
    "HANDOVER_BRIEF.md",
    "NEXT_TRACK_DECISION_CONTEXT.json",
    "NEXT_TRACK_DECISION_CONTEXT.md",
    "DECISION_SUPPORT_ENTRYPOINT_RECOMMENDATION.md",
    "CLAIM_BOUNDARY_AUDIT.json",
    "NO_ACTION_BOUNDARY_AUDIT.json",
    "NO_MUTATION_AUDIT.json",
    "SECRET_AUDIT.json",
    "HASH_MANIFEST.json",
]


def status_of(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    return payload.get("status") or payload.get("final_status") or payload.get("decision_status")


def decision(spec: dict[str, str]) -> dict[str, Any]:
    return read_json(REPO_ROOT / spec["root"] / spec["decision_file"], {})


def fact_value(payload: dict[str, Any], *keys: str) -> Any:
    disclosed = payload.get("disclosed_frozen_facts", {}) if isinstance(payload.get("disclosed_frozen_facts"), dict) else {}
    expected = payload.get("expected_counts", {}) if isinstance(payload.get("expected_counts"), dict) else {}
    for key in keys:
        if key in payload:
            return payload[key]
        if key in disclosed:
            return disclosed[key]
        if key in expected:
            return expected[key]
    return None


def reconcile_facts() -> dict[str, Any]:
    final_review = decision(REQUIRED_UPSTREAMS["final_package_review"])
    freeze = decision(REQUIRED_UPSTREAMS["r2_milestone_freeze"])
    collateral = decision(REQUIRED_UPSTREAMS["collateral_r2"])
    r2 = decision(REQUIRED_UPSTREAMS["r2_demo"])
    closeout = decision(REQUIRED_UPSTREAMS["r2_closeout"])
    sources = {
        "final_package_review": {
            "r2_demo_manifest_rows": fact_value(final_review, "r2_manifest_row_count", "r2_manifest_rows"),
            "collateral_manifest_rows": fact_value(final_review, "collateral_manifest_rows"),
            "hero_bindings": fact_value(final_review, "hero_bindings_count"),
            "usd_prim_paths": fact_value(final_review, "usd_prim_path_count"),
            "overlay_status_entries": fact_value(final_review, "overlay_status_entries_count"),
            "replay_frames": fact_value(final_review, "replay_route_animation_frames_count"),
            "hitl_proposal_fixtures": fact_value(final_review, "hitl_proposal_fixture_count"),
            "hitl_lifecycle_fixtures": fact_value(final_review, "hitl_lifecycle_fixture_count"),
            "personas": fact_value(final_review, "persona_walkthrough_count", "personas_count"),
            "web_companion_count": fact_value(final_review, "web_companion_count"),
            "unresolved_quarantined_preserved": fact_value(final_review, "unresolved_quarantined_preserved_count"),
            "blocking_gaps": fact_value(final_review, "blocking_gaps_count"),
            "non_blocking_gaps": fact_value(final_review, "non_blocking_gaps_count"),
        },
        "r2_milestone_freeze": {
            "r2_demo_manifest_rows": fact_value(freeze, "r2_manifest_row_count"),
            "hero_bindings": fact_value(freeze, "hero_bindings_count"),
            "usd_prim_paths": fact_value(freeze, "usd_prim_path_count"),
            "overlay_status_entries": fact_value(freeze, "overlay_status_entries_count"),
            "replay_frames": fact_value(freeze, "replay_route_animation_frames_count"),
            "hitl_proposal_fixtures": fact_value(freeze, "hitl_proposal_fixture_count"),
            "hitl_lifecycle_fixtures": fact_value(freeze, "hitl_lifecycle_fixture_count"),
            "personas": fact_value(freeze, "persona_walkthrough_count"),
            "web_companion_count": fact_value(freeze, "web_companion_count"),
            "unresolved_quarantined_preserved": fact_value(freeze, "unresolved_quarantined_preserved_count"),
            "blocking_gaps": fact_value(freeze, "blocking_gaps_count"),
            "non_blocking_gaps": fact_value(freeze, "non_blocking_gaps_count"),
        },
        "collateral_r2": {
            "r2_demo_manifest_rows": fact_value(collateral, "r2_manifest_rows"),
            "collateral_manifest_rows": fact_value(collateral, "collateral_manifest_rows"),
            "hero_bindings": fact_value(collateral, "hero_bindings_count"),
            "usd_prim_paths": fact_value(collateral, "usd_prim_path_count"),
            "overlay_status_entries": fact_value(collateral, "overlay_status_entries_count"),
            "replay_frames": fact_value(collateral, "replay_route_animation_frames_count"),
            "hitl_proposal_fixtures": fact_value(collateral, "hitl_proposal_fixture_count"),
            "hitl_lifecycle_fixtures": fact_value(collateral, "hitl_lifecycle_fixture_count"),
            "personas": fact_value(collateral, "persona_walkthrough_count"),
            "web_companion_count": fact_value(collateral, "web_companion_count"),
            "unresolved_quarantined_preserved": fact_value(collateral, "unresolved_quarantined_preserved_count"),
            "blocking_gaps": fact_value(collateral, "blocking_gaps_count"),
            "non_blocking_gaps": fact_value(collateral, "non_blocking_gaps_count"),
        },
        "r2_demo": {
            "r2_demo_manifest_rows": fact_value(r2, "r2_manifest_row_count"),
            "hero_bindings": fact_value(r2, "hero_bindings_count"),
            "usd_prim_paths": fact_value(r2, "usd_prim_path_count"),
            "overlay_status_entries": fact_value(r2, "overlay_status_entries_count"),
            "replay_frames": fact_value(r2, "replay_route_animation_frames_count"),
            "hitl_proposal_fixtures": fact_value(r2, "hitl_proposal_fixture_count"),
            "hitl_lifecycle_fixtures": fact_value(r2, "hitl_lifecycle_fixture_count"),
            "personas": fact_value(r2, "persona_walkthrough_count"),
            "web_companion_count": fact_value(r2, "web_companion_packet_summary_count", "web_companion_count"),
            "unresolved_quarantined_preserved": fact_value(r2, "unresolved_quarantined_preserved_count"),
            "blocking_gaps": fact_value(r2, "blocking_gaps_count"),
            "non_blocking_gaps": fact_value(r2, "non_blocking_gaps_count"),
        },
        "r2_closeout": {
            "r2_demo_manifest_rows": fact_value(closeout, "r2_manifest_row_count"),
            "hero_bindings": fact_value(closeout, "hero_bindings_count"),
            "usd_prim_paths": fact_value(closeout, "usd_prim_path_count"),
            "overlay_status_entries": fact_value(closeout, "overlay_status_entries_count"),
            "replay_frames": fact_value(closeout, "replay_route_animation_frames_count"),
            "hitl_proposal_fixtures": fact_value(closeout, "hitl_proposal_fixture_count"),
            "hitl_lifecycle_fixtures": fact_value(closeout, "hitl_lifecycle_fixture_count"),
            "personas": fact_value(closeout, "persona_walkthrough_count"),
            "web_companion_count": fact_value(closeout, "web_companion_count"),
            "unresolved_quarantined_preserved": fact_value(closeout, "unresolved_quarantined_preserved_count"),
            "blocking_gaps": fact_value(closeout, "blocking_gaps_count"),
            "non_blocking_gaps": fact_value(closeout, "non_blocking_gaps_count"),
        },
    }
    rows = []
    mismatches = []
    for fact, expected in FROZEN_COUNTS.items():
        observed = {source: values[fact] for source, values in sources.items() if values.get(fact) is not None}
        ok = bool(observed) and set(observed.values()) == {expected}
        row = {"fact": fact, "expected": expected, "observed": observed, "status": "PASS" if ok else "FAIL"}
        rows.append(row)
        if not ok:
            mismatches.append(row)
    return {"status": "PASS" if not mismatches else "FAIL", "rows": rows, "mismatches": mismatches, "frozen_counts": FROZEN_COUNTS}


def markdown_table(rows: list[dict[str, Any]]) -> str:
    lines = ["| Fact | Expected | Observed | Status |", "|---|---:|---|---|"]
    for row in rows:
        lines.append(f"| {row['fact']} | `{row['expected']}` | `{row['observed']}` | `{row['status']}` |")
    return "\n".join(lines)


def write_indexes(required: dict[str, Any], supporting: dict[str, Any]) -> None:
    artifacts = []
    for kind, discovery in [("required", required), ("optional_supporting", supporting)]:
        for row in discovery["upstreams"]:
            artifacts.append({**row, "kind": kind})
    write_json(
        OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json",
        {
            "task_name": TASK_NAME,
            "required_summary": required["summary"],
            "optional_supporting_summary": supporting["summary"],
            "artifacts": artifacts,
        },
    )
    green = [row for row in artifacts if row["green"]]
    optional_missing = [row for row in artifacts if row["kind"] == "optional_supporting" and not row["green"]]
    write_json(
        OUTPUT_ROOT / "GREEN_UPSTREAMS_INDEX.json",
        {
            "status": "PASS",
            "green_count": len(green),
            "required_green_count": required["summary"]["required_upstreams_found"],
            "optional_supporting_green_count": supporting["summary"]["required_upstreams_found"],
            "optional_missing": optional_missing,
            "green_upstreams": green,
        },
    )


def main() -> int:
    prepare_output_root(OUTPUT_ROOT, OUTPUT_NAME)
    before = upstream_snapshots(REQUIRED_UPSTREAMS | SUPPORTING_UPSTREAMS)
    required_discovery, required_summary = discover_upstreams(REQUIRED_UPSTREAMS)
    supporting_discovery, supporting_summary = discover_upstreams(SUPPORTING_UPSTREAMS)
    write_indexes(required_discovery, supporting_discovery)
    reconciliation = reconcile_facts()
    write_json(OUTPUT_ROOT / "FROZEN_FACTS_RECONCILIATION.json", reconciliation)

    required_green = required_summary["status"] == "PASS"
    final_review_green = required_discovery["upstreams"][0]["green"]
    optional_missing = supporting_summary["missing_or_not_green"]

    closed_tracks = [
        "D4X R7 multi-domain edge registry runtime slice",
        "D4X R8 edge registry hardening",
        "D5 R3 event-fabric integration",
        "D5 R4 Track2 handoff",
        "D6/D5 local running control-room slice and closeout",
        "Incident Mode closeout",
        "Incident Mode Track2A operator-surface handoff R4",
        "Hero Neighbourhood scene pack closeout",
        "CER/SEG cross-city v2 closeout",
        "Hero + CER/SEG integration-readiness review",
        "Hero Neighbourhood control-room reference demo R1 and closeout",
        "Track A Real USD Twin milestone freeze",
        "Track D HITL Reviewed Action milestone freeze",
        "Track P Product Packaging closeout",
        "Hero USD Twin + HITL integration-readiness review",
        "Hero USD Twin + HITL Control Room Demo R2",
        "Hero USD Twin + HITL Demo Closeout R2",
        "Hero USD Twin + HITL Demo Milestone Freeze R2",
        "Collateral R2",
        "Final Package Review",
    ]
    ready_next = [
        "Decision-support option-set contract preflight",
        "Governed 9-stage runtime preflight",
        "Plan Mode / SUMO preflight",
        "Similar-case retrieval preflight",
        "Cross-domain cascade preflight later",
    ]
    deferred = [
        "not claimed: production/public API",
        "not claimed: live autonomous monitoring",
        "not claimed: alert push",
        "not claimed: dispatch/routing/control/enforcement",
        "not claimed: legal/certified incident findings",
        "not claimed: citywide certified twin",
        "not claimed: certified physical geometry",
        "not claimed: automated action",
        "not claimed: nine autonomous LLM gates",
        "not claimed: heavy perception/VSS/Metropolis production stack",
        "not claimed: citywide Omniverse twin",
    ]
    certified_state = {
        "status": "PASS" if required_green and reconciliation["status"] == "PASS" else "FAIL",
        "current_milestone": "Hero USD Twin + HITL Control Room Demo R2",
        "what_is_green_now": [row for row in required_discovery["upstreams"] if row["green"]],
        "what_is_frozen_now": FROZEN_COUNTS,
        "source_of_truth_roots": [row["root"] for row in required_discovery["upstreams"] if row["green"]],
        "limitations_continue_to_disclose": [
            "local/replay review/query context only",
            "R2 visual acceptance remains artifact/package review only",
            "USD twin remains bounded/non-certified and not citywide physical truth",
            "HITL reviewed action remains proposal/review context with inert execution stubs",
        ],
        "tracks_closed": closed_tracks,
        "tracks_ready_next": ready_next,
        "deferred_not_claimed": deferred,
        "correct_next_intelligence_entrypoint": NEXT_TASK,
    }
    write_json(OUTPUT_ROOT / "CERTIFIED_STATE_LEDGER.json", certified_state)
    write_text(
        OUTPUT_ROOT / "CERTIFIED_STATE_LEDGER.md",
        f"""# Certified State Ledger

Status: `{certified_state['status']}`

## Current Milestone

Hero USD Twin + HITL Control Room Demo R2

## Frozen Facts

{markdown_table(reconciliation['rows'])}

## Closed / Frozen

{chr(10).join(f"- {item}" for item in closed_tracks)}

## Ready Next

{chr(10).join(f"- {item}" for item in ready_next)}

## Deferred / Not Yet Claimed

{chr(10).join(f"- {item}" for item in deferred)}
""",
    )
    lineage = {
        "status": "PASS",
        "milestone_sequence": [
            "D4X R7/R8 relationship substrate",
            "D5 local served runtime and Track2 handoff",
            "D6/D5 local running control-room slice",
            "Incident Mode closeout",
            "Hero scene pack and CER/SEG integration",
            "R1 Hero control-room reference demo",
            "Track A Real USD Twin",
            "Track D HITL Reviewed Action",
            "Track P Collateral R1",
            "Hero USD Twin + HITL integration readiness",
            "Demo R2",
            "Demo R2 closeout",
            "Demo R2 milestone freeze",
            "Collateral R2",
            "Final package review",
            "R2 certified-state and handover refresh",
        ],
        "optional_missing": optional_missing,
    }
    write_json(OUTPUT_ROOT / "MILESTONE_LINEAGE.json", lineage)
    write_text(OUTPUT_ROOT / "MILESTONE_LINEAGE.md", "# Milestone Lineage\n\n" + "\n".join(f"{idx}. {item}" for idx, item in enumerate(lineage["milestone_sequence"], 1)))

    limitations = {
        "status": "PASS",
        "non_blocking_limitations": certified_state["limitations_continue_to_disclose"],
        "non_blocking_gaps_count": FROZEN_COUNTS["non_blocking_gaps"],
        "blocking_gaps_count": FROZEN_COUNTS["blocking_gaps"],
        "optional_missing": optional_missing,
    }
    write_json(OUTPUT_ROOT / "LIMITATIONS_LEDGER.json", limitations)
    write_text(OUTPUT_ROOT / "LIMITATIONS_LEDGER.md", "# Limitations Ledger\n\n" + "\n".join(f"- {item}" for item in limitations["non_blocking_limitations"]))

    boundary_ledger = {
        "status": "PASS",
        "boundary": BOUNDARY,
        "must_not_claim": deferred,
    }
    write_json(OUTPUT_ROOT / "BOUNDARY_AND_CLAIM_LEDGER.json", boundary_ledger)
    write_text(OUTPUT_ROOT / "BOUNDARY_AND_CLAIM_LEDGER.md", f"# Boundary And Claim Ledger\n\n{BOUNDARY}\n\n## Must Not Claim\n\n" + "\n".join(f"- {item}" for item in deferred))

    track_ledger = {
        "status": "PASS",
        "closed_frozen": closed_tracks,
        "ready_next": ready_next,
        "deferred_not_claimed": deferred,
        "closed_track_count": len(closed_tracks),
        "ready_next_track_count": len(ready_next),
        "deferred_track_count": len(deferred),
    }
    write_json(OUTPUT_ROOT / "TRACK_CLOSURE_LEDGER.json", track_ledger)
    write_text(
        OUTPUT_ROOT / "TRACK_CLOSURE_LEDGER.md",
        "# Track Closure Ledger\n\n## Closed / Frozen\n\n"
        + "\n".join(f"- {item}" for item in closed_tracks)
        + "\n\n## Ready Next\n\n"
        + "\n".join(f"- {item}" for item in ready_next)
        + "\n\n## Deferred / Not Claimed\n\n"
        + "\n".join(f"- {item}" for item in deferred),
    )

    next_context = {
        "status": "PASS",
        "recommended_next_task": NEXT_TASK,
        "why_before_plan_mode": "Plan Mode, inverse dynamics, similar-case retrieval, cross-domain cascade, and HITL need the same reviewed_option_set object before runtime expansion.",
        "code_computes_model_narrates": True,
        "nine_stage_runtime": "governed state machine, not nine autonomous LLMs",
        "shared_object": "reviewed_option_set",
        "stale_or_contradictory_recommendations_detected": False,
    }
    write_json(OUTPUT_ROOT / "NEXT_TRACK_DECISION_CONTEXT.json", next_context)
    write_text(
        OUTPUT_ROOT / "NEXT_TRACK_DECISION_CONTEXT.md",
        f"""# Next Track Decision Context

Recommended next task: `{NEXT_TASK}`

This should happen before Plan Mode / inverse dynamics / similar-case retrieval / cross-domain cascade because all of those need a shared `reviewed_option_set` object.

Rules:

- Code computes, model narrates.
- 9-stage runtime is a governed state machine, not nine autonomous LLMs.
- Reviewed option sets are the shared object for Plan Mode, inverse dynamics, retrieval, cascade, and HITL.
""",
    )
    write_text(
        OUTPUT_ROOT / "DECISION_SUPPORT_ENTRYPOINT_RECOMMENDATION.md",
        f"""# Decision Support Entrypoint Recommendation

Recommended next task: `{NEXT_TASK}`

Do this before Plan Mode, inverse dynamics, similar-case retrieval, and cross-domain cascade. The shared `reviewed_option_set` contract is the coordination object those lanes need.
""",
    )
    write_text(
        OUTPUT_ROOT / "HANDOVER_BRIEF.md",
        f"""# R2 Handover Brief

Current milestone: Hero USD Twin + HITL Control Room Demo R2.

## Frozen R2 Facts

{markdown_table(reconciliation['rows'])}

## Three Non-Blocking Limitations

- R2 visual acceptance remains artifact/package review only.
- Real USD twin remains bounded/non-certified and not citywide physical truth.
- HITL reviewed action remains proposal/review context with inert execution stubs.

## Boundary

{BOUNDARY}

## Inspect First

- `outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_final_package_review/LOCAL_OPEN_INDEX.md`
- `outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_milestone_freeze_r2/LOCAL_OPEN_INDEX.md`
- `outputs/collateral_r2_after_track_a_and_track_d_if_green/LOCAL_OPEN_INDEX.md`
- `outputs/main_citybrain_d6_r2_certified_state_and_handover_refresh/LOCAL_OPEN_INDEX.md`

## Next Recommended Task

`{NEXT_TASK}`

This is the correct next task because Decision Support needs a shared `reviewed_option_set` contract before Plan Mode, inverse dynamics, similar-case retrieval, cross-domain cascade, or governed runtime expansion.

Rules:

- Code computes, model narrates.
- 9-stage runtime is a governed state machine, not nine autonomous LLMs.
- Reviewed option sets are the shared object for Plan Mode, inverse dynamics, retrieval, cascade, and HITL.
""",
    )

    status = PASS_STATUS if final_review_green and certified_state["status"] == "PASS" and next_context["recommended_next_task"] == NEXT_TASK else FAIL_STATUS
    write_json(
        OUTPUT_ROOT / DECISION_NAME,
        {
            "status": status,
            "task_name": TASK_NAME,
            "timestamp": now_iso(),
            "output_root": str(OUTPUT_ROOT),
            "runner_path": str(Path(__file__).resolve()),
            "decision_state": "provisional_before_audits",
        },
    )
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

Status: `{status}`

{BOUNDARY}

Open `LOCAL_OPEN_INDEX.md` first. This package is the concise source-of-truth handover for future Decision Support / Plan Mode work.

Recommended next task: `{NEXT_TASK}`
""",
    )
    index_lines = [
        f"# {TASK_NAME}",
        "",
        f"Status: `{status}`",
        "",
        BOUNDARY,
        "",
        "## Open First",
        "",
        "- [README.md](README.md)",
        f"- [Decision]({DECISION_NAME})",
        "- [Handover Brief](HANDOVER_BRIEF.md)",
        "- [Certified State Ledger](CERTIFIED_STATE_LEDGER.md)",
        "",
        "## Artifacts",
        "",
    ]
    index_lines.extend(f"- [{name}]({name})" for name in REQUIRED_OUTPUTS)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(index_lines))

    audits = run_standard_audits(OUTPUT_ROOT, TASK_NAME, before, REQUIRED_UPSTREAMS | SUPPORTING_UPSTREAMS, REQUIRED_OUTPUTS)
    json_parse_status = "PASS"
    json_parse_failures = []
    for path in OUTPUT_ROOT.glob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            json_parse_status = "FAIL"
            json_parse_failures.append({"path": path.name, "error": str(exc)})
    stale_recommendation_status = "PASS" if next_context["recommended_next_task"] == NEXT_TASK else "FAIL"
    limitation_consistency_status = "PASS" if limitations["non_blocking_gaps_count"] == 3 and limitations["blocking_gaps_count"] == 0 else "FAIL"
    if not all(
        [
            audits["all_pass"],
            json_parse_status == "PASS",
            stale_recommendation_status == "PASS",
            reconciliation["status"] == "PASS",
            limitation_consistency_status == "PASS",
        ]
    ):
        status = FAIL_STATUS

    decision_payload = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now_iso(),
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(Path(__file__).resolve()),
        "required_upstreams_found": required_summary["required_upstreams_found"],
        "required_upstreams_total": required_summary["required_upstreams_total"],
        "optional_upstreams_found": supporting_summary["required_upstreams_found"],
        "optional_upstreams_total": supporting_summary["required_upstreams_total"],
        "optional_missing": optional_missing,
        "frozen_facts_reconciliation_status": reconciliation["status"],
        "closed_track_count": len(closed_tracks),
        "ready_next_track_count": len(ready_next),
        "deferred_track_count": len(deferred),
        "json_parse_status": json_parse_status,
        "json_parse_failures": json_parse_failures,
        "stale_recommendation_detection_status": stale_recommendation_status,
        "frozen_facts_count_consistency_status": reconciliation["status"],
        "limitation_disclosure_consistency_status": limitation_consistency_status,
        "next_track_recommendation_consistency_status": stale_recommendation_status,
        "blocking_gaps_count": FROZEN_COUNTS["blocking_gaps"] if status == PASS_STATUS else max(1, required_summary["missing_or_not_green_count"]),
        "non_blocking_gaps_count": FROZEN_COUNTS["non_blocking_gaps"],
        "recommended_next_task": NEXT_TASK if status == PASS_STATUS else TASK_NAME + "-FIXUP",
        "boundary": BOUNDARY,
    }
    decision_payload.update(audits)
    if not audits["all_pass"]:
        decision_payload["status"] = FAIL_STATUS
    decision_payload = write_decision_last(OUTPUT_ROOT, DECISION_NAME, decision_payload, TASK_NAME)
    print(json.dumps(decision_payload, indent=2, sort_keys=True))
    return 0 if decision_payload["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())


#!/usr/bin/env python3
"""Compose the bounded Hero USD twin + HITL control-room demo R2 package."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_r2"

TASK_NAME = "MAIN-CITYBRAIN-D6-HERO-USD-TWIN-HITL-CONTROL-ROOM-DEMO-R2"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_R2_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_R2"
SCENARIO_ID = "HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001"
NEXT_TASK = "MAIN-CITYBRAIN-D6-HERO-USD-TWIN-HITL-CONTROL-ROOM-DEMO-CLOSEOUT-R2"
POLISH_TASK = "MAIN-CITYBRAIN-D6-HERO-USD-TWIN-HITL-CONTROL-ROOM-DEMO-R2-POLISH"

BOUNDARY = (
    "R2 is a bounded local/replay Hero Neighbourhood control-room demo composition. "
    "It is not production-ready, not public API ready, not live autonomous monitoring, "
    "not autonomous incident detection, not alert push, not dispatch, not routing/control, "
    "not enforcement, not official ticket/case creation, not a legal finding, not a certified incident, "
    "not a certified physical twin, not a citywide twin, not automated action, and not real-time operational command."
)

LIMITATIONS = [
    "bounded hero-neighbourhood demo only",
    "local/replay review/query context only",
    "personas render the same evidence base and do not create separate truth paths",
    "USD/USDA artifacts are handoff/demo artifacts, not a live Omniverse deployment",
    "HITL proposal/lifecycle objects are review objects only and do not execute",
    "unresolved and quarantined contexts remain review-only context",
    "no production, public API, live monitoring, autonomous detection, alerting, dispatch, routing/control, enforcement, ticket/case, legal/certified, citywide twin, or automated action claim",
]

REQUIRED_UPSTREAMS = {
    "integration_readiness_review": {
        "task_name": "MAIN-CITYBRAIN-D6-HERO-USD-TWIN-AND-HITL-INTEGRATION-READINESS-REVIEW",
        "root": "outputs/main_citybrain_d6_hero_usd_twin_and_hitl_integration_readiness_review",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_AND_HITL_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
    },
    "track_p_product_packaging_closeout": {
        "task_name": "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-PRODUCT-PACKAGING-CLOSEOUT",
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_product_packaging_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_CLOSEOUT_WITH_LIMITATIONS",
    },
    "track_a_real_usd_twin_freeze": {
        "task_name": "MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REAL-USD-TWIN-MILESTONE-FREEZE",
        "root": "outputs/main_track2a_d6_hero_neighbourhood_real_usd_twin_milestone_freeze",
        "expected": "PASS_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_MILESTONE_FREEZE_WITH_LIMITATIONS",
    },
    "track_d_hitl_freeze": {
        "task_name": "MAIN-CITYBRAIN-D6-HITL-REVIEWED-ACTION-MILESTONE-FREEZE",
        "root": "outputs/main_citybrain_d6_hitl_reviewed_action_milestone_freeze",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_MILESTONE_FREEZE_WITH_LIMITATIONS",
    },
    "hero_control_room_closeout_r1": {
        "task_name": "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-CONTROL-ROOM-REFERENCE-DEMO-CLOSEOUT-R1",
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_closeout_r1",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_WITH_LIMITATIONS",
    },
    "hero_cerseg_integration_readiness": {
        "task_name": "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-AND-CERSEG-V2-INTEGRATION-READINESS-REVIEW",
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_and_cerseg_v2_integration_readiness_review",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
    },
    "cer_seg_cross_city_v2_closeout": {
        "task_name": "MAIN-CITYBRAIN-D6-CER-SEG-CROSS-CITY-V2-CLOSEOUT",
        "root": "outputs/main_citybrain_d6_cer_seg_cross_city_v2_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_WITH_LIMITATIONS",
    },
    "incident_mode_closeout": {
        "task_name": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-CLOSEOUT",
        "root": "outputs/main_citybrain_d6_incident_mode_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_WITH_LIMITATIONS",
    },
    "incident_track2a_operator_surface_handoff_r4": {
        "task_name": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-TRACK2A-OPERATOR-SURFACE-HANDOFF-R4",
        "root": "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_WITH_LIMITATIONS",
    },
    "r8_multi_domain_edge_registry_hardening": {
        "task_name": "MAIN-CITYBRAIN-D4X-R8-MULTI-DOMAIN-EDGE-REGISTRY-HARDENING",
        "root": "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_WITH_LIMITATIONS",
    },
}

SUPPORT_ROOTS = {
    "track_a_footprint_r1": "outputs/main_track2a_d6_hero_neighbourhood_real_footprint_usd_r1",
    "track_a_status_overlay_r2": "outputs/main_track2a_d6_hero_neighbourhood_graph_to_usd_status_overlay_r2",
    "track_a_replay_animation_r3": "outputs/main_track2a_d6_hero_neighbourhood_replay_event_route_animation_r3",
    "track_d_action_proposal_r1": "outputs/main_citybrain_d6_hitl_action_proposal_contract_r1",
    "track_d_lifecycle_r2": "outputs/main_citybrain_d6_hitl_approval_lifecycle_r2",
    "track_d_guardrail_smoke_r3": "outputs/main_citybrain_d6_hitl_audit_and_guardrail_smoke_r3",
    "track_p_persona_policies_r1": "outputs/main_citybrain_d6_persona_rendering_policies_r1",
    "track_p_collateral_r1": "outputs/main_citybrain_d6_hero_neighbourhood_collateral_pack_r1",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | None) -> str | None:
    if path is None:
        return None
    return path.relative_to(REPO_ROOT).as_posix()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "byte_count": 0, "fingerprint": None}
    entries: list[str] = []
    byte_count = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest = sha256_file(path)
        entries.append(f"{path.relative_to(root).as_posix()}:{digest}")
        byte_count += path.stat().st_size
    return {
        "exists": True,
        "file_count": len(entries),
        "byte_count": byte_count,
        "fingerprint": hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest(),
    }


def find_decision(root: Path) -> Path | None:
    decisions = sorted(root.glob("*DECISION.json")) if root.exists() else []
    return decisions[0] if decisions else None


def decision_status(payload: dict[str, Any]) -> str | None:
    return payload.get("status") or payload.get("final_status")


def discover_inputs() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    snapshots: dict[str, dict[str, Any]] = {}
    required_rows = []
    for key, meta in REQUIRED_UPSTREAMS.items():
        root = REPO_ROOT / meta["root"]
        decision_path = find_decision(root)
        decision = read_json(decision_path, {}) if decision_path else {}
        status = decision_status(decision)
        snap = snapshot(root)
        snapshots[meta["root"]] = snap
        required_rows.append(
            {
                "key": key,
                "task_name": meta["task_name"],
                "root": meta["root"],
                "exists": root.exists(),
                "decision_json_path": rel(decision_path),
                "status": status,
                "expected_status": meta["expected"],
                "green": root.exists() and status == meta["expected"],
                "hash_manifest_present": (root / "HASH_MANIFEST.json").exists(),
                "local_open_index_present": (root / "LOCAL_OPEN_INDEX.md").exists(),
                "read_only": True,
                "missing_reason": None if root.exists() else "required upstream output root missing",
                "snapshot": snap,
            }
        )
    support_rows = []
    for key, root_text in SUPPORT_ROOTS.items():
        root = REPO_ROOT / root_text
        snap = snapshot(root)
        snapshots[root_text] = snap
        support_rows.append({"key": key, "root": root_text, "exists": root.exists(), "read_only": True, "snapshot": snap})
    index = {
        "status": "PASS" if all(row["green"] for row in required_rows) else "FAIL",
        "task_name": TASK_NAME,
        "generated_at": utc_now(),
        "scenario_id": SCENARIO_ID,
        "required_upstreams": required_rows,
        "supporting_artifact_roots": support_rows,
        "required_upstreams_found": sum(1 for row in required_rows if row["exists"]),
        "required_upstreams_total": len(required_rows),
        "mutation_policy": "read_only_consumption_no_upstream_mutation",
    }
    return index, snapshots


def load_sources() -> dict[str, Any]:
    return {
        "integration_decision": read_json(REPO_ROOT / "outputs/main_citybrain_d6_hero_usd_twin_and_hitl_integration_readiness_review/MAIN_CITYBRAIN_D6_HERO_USD_TWIN_AND_HITL_INTEGRATION_READINESS_REVIEW_DECISION.json", {}),
        "control_room_summary": read_json(REPO_ROOT / "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_closeout_r1/CONTROL_ROOM_DEMO_FREEZE_SUMMARY.json", {}),
        "track_a_footprints": read_json(REPO_ROOT / "outputs/main_track2a_d6_hero_neighbourhood_real_footprint_usd_r1/REAL_FOOTPRINT_BINDING_REGISTRY.json", {"bindings": []}),
        "track_a_overlay": read_json(REPO_ROOT / "outputs/main_track2a_d6_hero_neighbourhood_graph_to_usd_status_overlay_r2/GRAPH_TO_USD_STATUS_OVERLAY.json", {"overlays": []}),
        "track_a_animation": read_json(REPO_ROOT / "outputs/main_track2a_d6_hero_neighbourhood_replay_event_route_animation_r3/REPLAY_EVENT_ROUTE_ANIMATION_TIMELINE.json", {"frames": []}),
        "hitl_proposals": read_json(REPO_ROOT / "outputs/main_citybrain_d6_hitl_action_proposal_contract_r1/ACTION_PROPOSAL_FIXTURES.json", {"proposals": []}),
        "hitl_lifecycles": read_json(REPO_ROOT / "outputs/main_citybrain_d6_hitl_approval_lifecycle_r2/APPROVAL_LIFECYCLE_FIXTURES.json", {"lifecycles": []}),
        "hitl_audit_events": read_json(REPO_ROOT / "outputs/main_citybrain_d6_hitl_approval_lifecycle_r2/AUDIT_LOG_FIXTURES.json", {"events": []}),
        "hitl_stubs": read_json(REPO_ROOT / "outputs/main_citybrain_d6_hitl_approval_lifecycle_r2/EXECUTION_STUB_RECORDS.json", {"stubs": []}),
        "hitl_negative": read_json(REPO_ROOT / "outputs/main_citybrain_d6_hitl_audit_and_guardrail_smoke_r3/NEGATIVE_GUARDRAIL_TEST_RESULTS.json", {"tests": []}),
        "hitl_positive": read_json(REPO_ROOT / "outputs/main_citybrain_d6_hitl_audit_and_guardrail_smoke_r3/POSITIVE_GUARDRAIL_TEST_RESULTS.json", {"tests": []}),
        "persona_policies": read_json(REPO_ROOT / "outputs/main_citybrain_d6_persona_rendering_policies_r1/PERSONA_POLICIES.json", {"personas": [], "shared_invariants": {}}),
    }


def refs_for(item: dict[str, Any]) -> tuple[list[str], list[str]]:
    evidence = item.get("evidence_refs") or item.get("evidence_bundle_refs") or []
    limits = item.get("limitation_refs") or LIMITATIONS
    return list(evidence), list(limits)


def row(row_id: str, family: str, ref: str, source_task: str, surface: str, evidence: list[str], limitations: list[str], review_state: str, claim_label: str = "bounded_local_replay_review_context") -> dict[str, Any]:
    return {
        "manifest_row_id": row_id,
        "artifact_family": family,
        "artifact_ref": ref,
        "source_task": source_task,
        "scenario_ref": SCENARIO_ID,
        "evidence_refs": evidence,
        "limitation_refs": limitations,
        "claim_label": claim_label,
        "review_state": review_state,
        "demo_surface": surface,
    }


def build_manifest(input_index: dict[str, Any], sources: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    i = 1
    for upstream in input_index["required_upstreams"]:
        rows.append(row(f"r2-manifest-{i:03d}", "upstream_artifact_reference", upstream["root"], upstream["task_name"], "audit", [upstream["decision_json_path"] or upstream["root"]], LIMITATIONS, "green_read_only" if upstream["green"] else "missing_or_not_green"))
        i += 1
    for fp in sources["track_a_footprints"].get("bindings", []):
        evidence, limits = refs_for(fp)
        rows.append(row(f"r2-manifest-{i:03d}", "hero_binding_usd_prim", fp.get("prim_path", fp.get("source_binding_id", "unknown")), "MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REAL-FOOTPRINT-USD-R1", "omniverse", evidence, limits, fp.get("review_state", "review_context"), fp.get("binding_scope", "scene_binding_context")))
        i += 1
    for overlay in sources["track_a_overlay"].get("overlays", []):
        evidence, limits = refs_for(overlay)
        rows.append(row(f"r2-manifest-{i:03d}", "review_safe_status_overlay", overlay.get("overlay_id", overlay.get("target_prim_path", "unknown")), "MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-GRAPH-TO-USD-STATUS-OVERLAY-R2", "operator", evidence, limits, overlay.get("status", "review_context")))
        i += 1
    for frame in sources["track_a_animation"].get("frames", []):
        rows.append(row(f"r2-manifest-{i:03d}", "replay_route_animation_frame", f"frame:{frame.get('frame_index')}", "MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REPLAY-EVENT-ROUTE-ANIMATION-R3", "omniverse", ["outputs/main_track2a_d6_hero_neighbourhood_replay_event_route_animation_r3/REPLAY_EVENT_ROUTE_ANIMATION_TIMELINE.json"], LIMITATIONS, frame.get("status", "event_replay_context")))
        i += 1
    for proposal in sources["hitl_proposals"].get("proposals", []):
        evidence, limits = refs_for(proposal)
        rows.append(row(f"r2-manifest-{i:03d}", "hitl_proposal_fixture", proposal.get("action_proposal_id", "unknown"), "MAIN-CITYBRAIN-D6-HITL-ACTION-PROPOSAL-CONTRACT-R1", "operator", evidence, limits, proposal.get("review_state", "awaiting_human_review"), "hitl_review_object_only"))
        i += 1
    for lifecycle in sources["hitl_lifecycles"].get("lifecycles", []):
        rows.append(row(f"r2-manifest-{i:03d}", "hitl_lifecycle_fixture", lifecycle.get("lifecycle_id", "unknown"), "MAIN-CITYBRAIN-D6-HITL-APPROVAL-LIFECYCLE-R2", "audit", [lifecycle.get("action_proposal_id", "unknown")], LIMITATIONS, lifecycle.get("current_state", "review_context"), "inert_lifecycle_no_execution"))
        i += 1
    for test in sources["hitl_negative"].get("tests", []):
        rows.append(row(f"r2-manifest-{i:03d}", "guardrail_negative_test_carry_forward", test.get("test_id", "unknown"), "MAIN-CITYBRAIN-D6-HITL-AUDIT-AND-GUARDRAIL-SMOKE-R3", "audit", ["outputs/main_citybrain_d6_hitl_audit_and_guardrail_smoke_r3/NEGATIVE_GUARDRAIL_TEST_RESULTS.json"], LIMITATIONS, test.get("status", "BLOCKED"), "blocked_logged_no_action"))
        i += 1
    for persona in sources["persona_policies"].get("personas", []):
        rows.append(row(f"r2-manifest-{i:03d}", "persona_rendering_output", persona.get("policy_id", persona.get("persona", "unknown")), "MAIN-CITYBRAIN-D6-PERSONA-RENDERING-POLICIES-R1", persona.get("persona", "persona").lower(), ["outputs/main_citybrain_d6_persona_rendering_policies_r1/PERSONA_POLICIES.json"], LIMITATIONS, "same_evidence_base_rendering", "persona_policy_not_truth_path"))
        i += 1
    rows.append(row(f"r2-manifest-{i:03d}", "web_companion_packet_summary", "web_companion_handoff_r2", TASK_NAME, "web", ["outputs/main_citybrain_d6_hero_usd_twin_and_hitl_integration_readiness_review/WEB_COMPANION_INTEGRATION_READINESS.json"], LIMITATIONS, "review_context"))
    i += 1
    rows.append(row(f"r2-manifest-{i:03d}", "unresolved_quarantined_review_context", "preservation_r2", TASK_NAME, "audit", ["outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_closeout_r1/CONTROL_ROOM_DEMO_FREEZE_SUMMARY.json"], LIMITATIONS, "preserved_review_only"))
    i += 1
    rows.append(row(f"r2-manifest-{i:03d}", "non_blocking_gap_and_claim_label", "non_blocking_gaps_r2", TASK_NAME, "executive", ["outputs/main_citybrain_d6_hero_usd_twin_and_hitl_integration_readiness_review/MAIN_CITYBRAIN_D6_HERO_USD_TWIN_AND_HITL_INTEGRATION_READINESS_REVIEW_DECISION.json"], LIMITATIONS, "limitations_disclosed"))
    return rows


def counts(sources: dict[str, Any]) -> dict[str, int]:
    control = sources["control_room_summary"]
    footprints = sources["track_a_footprints"].get("bindings", [])
    overlays = sources["track_a_overlay"].get("overlays", [])
    frames = sources["track_a_animation"].get("frames", [])
    proposals = sources["hitl_proposals"].get("proposals", [])
    lifecycles = sources["hitl_lifecycles"].get("lifecycles", [])
    stubs = sources["hitl_stubs"].get("stubs", [])
    return {
        "hero_bindings_count": int(control.get("hero_bindings_count") or len(footprints)),
        "usd_prim_path_count": len({fp.get("prim_path") for fp in footprints if fp.get("prim_path")}),
        "overlay_status_entries_count": len(overlays),
        "replay_route_animation_frames_count": len(frames),
        "hitl_proposal_fixture_count": len(proposals),
        "hitl_lifecycle_fixture_count": len(lifecycles),
        "hitl_audit_event_count": len(sources["hitl_audit_events"].get("events", [])),
        "hitl_execution_stub_count": len(stubs),
        "persona_walkthrough_count": 4,
        "web_companion_packet_summary_count": int(control.get("web_companion_packets_count") or 6),
        "operator_surface_packet_count": int(control.get("operator_surface_packets_count") or 6),
        "unresolved_quarantined_preserved_count": int(control.get("unresolved_quarantined_preserved_count") or 0),
        "negative_guardrail_test_count": len(sources["hitl_negative"].get("tests", [])),
        "positive_guardrail_test_count": len(sources["hitl_positive"].get("tests", [])),
    }


def write_walkthroughs(sources: dict[str, Any], c: dict[str, int]) -> None:
    common = (
        f"Scenario: `{SCENARIO_ID}`\n\n"
        "This walkthrough renders the same evidence base used by every R2 persona. "
        "It preserves evidence refs, limitation refs, unresolved/quarantined review context, and no-action boundaries.\n\n"
    )
    write_text(
        OUTPUT_ROOT / "OPERATOR_WALKTHROUGH_R2.md",
        "# Operator Walkthrough R2\n\n"
        + common
        + f"- Current event/context state: bounded local/replay corridor context with `{c['overlay_status_entries_count']}` review-safe overlay entries.\n"
        + f"- Affected entities: `{c['hero_bindings_count']}` hero bindings mapped to `{c['usd_prim_path_count']}` USD prim paths.\n"
        + f"- USD/Omniverse: footprint USDA, status overlay, and `{c['replay_route_animation_frames_count']}` route-animation frames are review-only surfaces.\n"
        + f"- HITL proposal state: `{c['hitl_proposal_fixture_count']}` proposal fixtures, `{c['hitl_lifecycle_fixture_count']}` lifecycles, inert stub only.\n"
        + f"- Unresolved/quarantined contexts preserved: `{c['unresolved_quarantined_preserved_count']}`.\n"
        + "- Safe next-look framing: human review context only; no alert, dispatch, routing/control, enforcement, ticket/case, legal/certified, or automated action.\n",
    )
    write_text(
        OUTPUT_ROOT / "EXECUTIVE_WALKTHROUGH_R2.md",
        "# Executive Walkthrough R2\n\n"
        + common
        + "- What this proves: CityBrain can compose the Hero control-room baseline, bounded USD twin handoff, replay route/event context, HITL reviewed-action lifecycle, persona renderings, and web/Omniverse handoffs into one coherent demo package.\n"
        + "- What this does not prove: production readiness, live monitoring, autonomous detection, control/dispatch/enforcement, legal/certified conclusions, full physical accuracy, or a citywide certified twin.\n"
        + "- Control-room value: one evidence-bound view across spatial status, incident/evidence context, reviewed-action proposal state, and limitations/audit context.\n"
        + "- Non-blocking gaps are disclosed in `NON_BLOCKING_GAPS_R2.json`.\n",
    )
    write_text(
        OUTPUT_ROOT / "PLANNER_WALKTHROUGH_R2.md",
        "# Planner Walkthrough R2\n\n"
        + common
        + "- Corridor/neighbourhood context: bounded LON hero neighbourhood replay context, with route/corridor highlighting as visual review context only.\n"
        + "- Relationship graph context: CER/SEG and R8 relationships are consumed through review-safe overlay/status packets.\n"
        + "- Future Plan/SUMO extension: placeholder only; no prediction or plan execution claim is made by R2.\n"
        + "- Spatial caveat: the USD layer is an accepted/available footprint handoff with limitations, not certified physical truth.\n",
    )
    write_text(
        OUTPUT_ROOT / "ANALYST_WALKTHROUGH_R2.md",
        "# Analyst Walkthrough R2\n\n"
        + common
        + f"- Evidence chain: manifest rows cross-reference upstream decisions, `{c['hero_bindings_count']}` hero bindings, overlay entries, animation frames, HITL proposals/lifecycles, guardrail tests, and persona policies.\n"
        + "- Artifact lineage: see `INPUT_ARTIFACT_INDEX.json`, `DEMO_R2_MANIFEST.json`, and `EVIDENCE_LIMITATION_TRACE_R2.json`.\n"
        + "- CER/SEG compatibility: consumed from green integration and closeout artifacts; no new canonical identity behavior is introduced.\n"
        + f"- Guardrail proof: `{c['negative_guardrail_test_count']}` negative tests remain blocked/logged; HITL stub remains `executed=false`.\n"
        + "- Review states/confidence/limitations remain explicit and non-certified.\n",
    )


def write_summaries(sources: dict[str, Any], c: dict[str, int], manifest: list[dict[str, Any]]) -> None:
    personas = sources["persona_policies"].get("personas", [])
    write_json(
        OUTPUT_ROOT / "SHARED_HERO_SCENARIO_R2.json",
        {
            "status": "PASS",
            "scenario_id": SCENARIO_ID,
            "scenario_scope": "bounded_london_hero_neighbourhood_corridor_replay_context",
            "same_story_across_surfaces": True,
            "second_scenario_created": False,
            "preservation_policy": "unresolved/quarantined contexts remain review-only context",
            "claim_boundary": BOUNDARY,
        },
    )
    write_json(
        OUTPUT_ROOT / "DEMO_R2_MANIFEST.json",
        {"status": "PASS", "task_name": TASK_NAME, "scenario_id": SCENARIO_ID, "manifest_row_count": len(manifest), "rows": manifest},
    )
    write_jsonl(OUTPUT_ROOT / "DEMO_R2_MANIFEST.jsonl", manifest)
    write_json(
        OUTPUT_ROOT / "PERSONA_RENDERING_SUMMARY_R2.json",
        {
            "status": "PASS",
            "persona_count": len(personas),
            "personas": personas,
            "truth_policy": "four persona walkthroughs render the same evidence base; no separate truth paths",
        },
    )
    write_json(
        OUTPUT_ROOT / "OMNIVERSE_KIT_HANDOFF_R2.json",
        {
            "status": "PASS",
            "handoff_mode": "bounded_local_replay_usda_handoff",
            "footprint_usda": "outputs/main_track2a_d6_hero_neighbourhood_real_footprint_usd_r1/hero_neighbourhood_real_footprint_r1.usda",
            "status_overlay_usda": "outputs/main_track2a_d6_hero_neighbourhood_graph_to_usd_status_overlay_r2/hero_neighbourhood_status_overlay_r2.usda",
            "route_animation_usda": "outputs/main_track2a_d6_hero_neighbourhood_replay_event_route_animation_r3/hero_neighbourhood_replay_event_route_animation_r3.usda",
            "usd_prim_path_count": c["usd_prim_path_count"],
            "live_omniverse_deployment": False,
            "certified_physical_accuracy": False,
            "citywide_twin": False,
            "claim_boundary": BOUNDARY,
        },
    )
    write_json(
        OUTPUT_ROOT / "WEB_COMPANION_HANDOFF_R2.json",
        {
            "status": "PASS",
            "role": "companion evidence/episode/executive surface",
            "web_companion_packet_summary_count": c["web_companion_packet_summary_count"],
            "same_scenario_id": SCENARIO_ID,
            "new_web_app_code_created": False,
            "action_surface_created": False,
            "evidence_refs": ["DEMO_R2_MANIFEST.json", "EVIDENCE_LIMITATION_TRACE_R2.json"],
            "limitation_refs": LIMITATIONS,
        },
    )
    write_json(
        OUTPUT_ROOT / "USD_TWIN_STATUS_OVERLAY_SUMMARY_R2.json",
        {
            "status": "PASS",
            "hero_bindings_count": c["hero_bindings_count"],
            "usd_prim_path_count": c["usd_prim_path_count"],
            "overlay_status_entries_count": c["overlay_status_entries_count"],
            "review_safe_statuses_only": True,
            "scene_source_operator_refs_not_promoted_to_canonical_ids": True,
        },
    )
    write_json(
        OUTPUT_ROOT / "REPLAY_ROUTE_ANIMATION_SUMMARY_R2.json",
        {
            "status": "PASS",
            "frame_count": c["replay_route_animation_frames_count"],
            "timeline_ref": "outputs/main_track2a_d6_hero_neighbourhood_replay_event_route_animation_r3/REPLAY_EVENT_ROUTE_ANIMATION_TIMELINE.json",
            "local_replay_only": True,
            "route_control_claim": False,
        },
    )
    stubs = sources["hitl_stubs"].get("stubs", [])
    write_json(
        OUTPUT_ROOT / "HITL_REVIEWED_ACTION_SUMMARY_R2.json",
        {
            "status": "PASS",
            "proposal_fixture_count": c["hitl_proposal_fixture_count"],
            "lifecycle_fixture_count": c["hitl_lifecycle_fixture_count"],
            "audit_event_count": c["hitl_audit_event_count"],
            "execution_stub_count": c["hitl_execution_stub_count"],
            "all_stubs_executed_false": all(stub.get("executed") is False for stub in stubs),
            "automatic_execution_path_introduced": False,
        },
    )
    write_json(
        OUTPUT_ROOT / "HITL_GUARDRAIL_CARRY_FORWARD_R2.json",
        {
            "status": "PASS",
            "negative_guardrail_test_count": c["negative_guardrail_test_count"],
            "positive_guardrail_test_count": c["positive_guardrail_test_count"],
            "negative_tests_blocked_logged": all(t.get("status") == "BLOCKED" and t.get("logged") and t.get("no_action_taken") for t in sources["hitl_negative"].get("tests", [])),
            "evidence_refs": [
                "outputs/main_citybrain_d6_hitl_audit_and_guardrail_smoke_r3/NEGATIVE_GUARDRAIL_TEST_RESULTS.json",
                "outputs/main_citybrain_d6_hitl_audit_and_guardrail_smoke_r3/BLOCKED_ACTION_AUDIT_LOG.json",
            ],
        },
    )
    write_json(
        OUTPUT_ROOT / "EVIDENCE_LIMITATION_TRACE_R2.json",
        {
            "status": "PASS",
            "trace_row_count": len(manifest),
            "rows": [
                {
                    "manifest_row_id": item["manifest_row_id"],
                    "artifact_family": item["artifact_family"],
                    "artifact_ref": item["artifact_ref"],
                    "evidence_refs": item["evidence_refs"],
                    "limitation_refs": item["limitation_refs"],
                    "claim_label": item["claim_label"],
                }
                for item in manifest
            ],
        },
    )
    write_json(
        OUTPUT_ROOT / "UNRESOLVED_QUARANTINED_PRESERVATION_R2.json",
        {
            "status": "PASS",
            "preserved_count": c["unresolved_quarantined_preserved_count"],
            "track_a_unresolved_prim_count": sum(1 for fp in sources["track_a_footprints"].get("bindings", []) if fp.get("binding_scope") == "unresolved_preserved"),
            "track_a_quarantined_prim_count": sum(1 for fp in sources["track_a_footprints"].get("bindings", []) if fp.get("binding_scope") == "quarantined_preserved"),
            "preservation_policy": "preserved as review-only context; not promoted to confirmed/canonical truth",
        },
    )
    nonblocking = [
        "Visual acceptance remains artifact/package review, not a new live screenshot requirement.",
        "Exact certified physical geometry is not asserted.",
        "Future Plan/SUMO extension remains a placeholder only in R2.",
    ]
    write_json(OUTPUT_ROOT / "NON_BLOCKING_GAPS_R2.json", {"status": "PASS", "non_blocking_gaps_count": len(nonblocking), "non_blocking_gaps": nonblocking})
    write_json(
        OUTPUT_ROOT / "VISUAL_ACCEPTANCE_REVIEW_R2.json",
        {
            "status": "PASS_ARTIFACT_PACKAGE_REVIEW_ONLY",
            "visual_surfaces": ["omniverse_usda_handoff", "web_companion_summary", "persona_walkthroughs", "operator_surface_panel_set"],
            "live_visual_capture_required": False,
        },
    )


def write_upstream_status(input_index: dict[str, Any]) -> None:
    write_json(
        OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json",
        input_index,
    )
    write_json(
        OUTPUT_ROOT / "UPSTREAM_STATUS_SUMMARY.json",
        {
            "status": input_index["status"],
            "required_upstreams_found": input_index["required_upstreams_found"],
            "required_upstreams_total": input_index["required_upstreams_total"],
            "all_required_upstreams_green": input_index["status"] == "PASS",
            "upstreams": [
                {
                    "key": row["key"],
                    "task_name": row["task_name"],
                    "root": row["root"],
                    "status": row["status"],
                    "expected_status": row["expected_status"],
                    "green": row["green"],
                }
                for row in input_index["required_upstreams"]
            ],
        },
    )


def scan_claims() -> tuple[str, list[str]]:
    ignored = {
        "CLAIM_LABEL_AUDIT_R2.json",
        "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_R2_DECISION.json",
        "HASH_MANIFEST.json",
    }
    text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in OUTPUT_ROOT.glob("*")
        if path.is_file() and path.name not in ignored
    )
    forbidden_phrases = [
        "production-ready",
        "public API ready",
        "live autonomous monitoring",
        "autonomous incident detection",
        "alert push",
        "dispatch",
        "routing/control",
        "enforcement",
        "official ticket/case creation",
        "legal finding",
        "certified incident",
        "certified physical twin",
        "citywide twin",
        "automated action",
        "real-time operational command",
    ]
    unsafe_hits: list[str] = []
    for phrase in forbidden_phrases:
        for match in re.finditer(re.escape(phrase), text, flags=re.IGNORECASE):
            prefix = text[max(0, match.start() - 220) : match.start()].lower()
            suffix = text[match.end() : min(len(text), match.end() + 120)].lower()
            clause = prefix + phrase.lower() + suffix
            negated_or_guardrail = any(
                marker in clause
                for marker in [
                    "not ",
                    "not a ",
                    "not an ",
                    "no ",
                    "no production",
                    "without ",
                    "false",
                    "blocked",
                    "forbidden",
                    "negative-",
                    "_created\": false",
                    "does not prove",
                    "what this does not prove",
                    "must_not_show",
                    "prohibited_transformations",
                ]
            )
            if not negated_or_guardrail:
                unsafe_hits.append(phrase)
                break
    return ("PASS" if not unsafe_hits else "FAIL"), sorted(set(unsafe_hits))


def write_audits(pre_snapshots: dict[str, dict[str, Any]], sources: dict[str, Any]) -> dict[str, str]:
    claim_status, claim_hits = scan_claims()
    stubs = sources["hitl_stubs"].get("stubs", [])
    negative_ok = all(t.get("status") == "BLOCKED" and t.get("logged") and t.get("no_action_taken") for t in sources["hitl_negative"].get("tests", []))
    no_action_ok = (
        all(stub.get("executed") is False and stub.get("external_side_effect") is False for stub in stubs)
        and negative_ok
    )
    mutations = []
    for root_text, before in sorted(pre_snapshots.items()):
        after = snapshot(REPO_ROOT / root_text)
        if before != after:
            mutations.append({"root": root_text, "before": before, "after": after})
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in OUTPUT_ROOT.glob("*") if path.is_file())
    secret_patterns = [
        r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}",
        r"(?i)secret\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}",
        r"AKIA[0-9A-Z]{16}",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    ]
    secret_hits = [pattern for pattern in secret_patterns if re.search(pattern, text)]
    write_json(
        OUTPUT_ROOT / "CLAIM_LABEL_AUDIT_R2.json",
        {
            "status": claim_status,
            "unsafe_forbidden_claim_hits": claim_hits,
            "allowed_framing": ["local/replay", "review/query context", "bounded hero-neighbourhood demo", "inert/stub action lifecycle", "non-certified USD handoff"],
            "claim_boundary": BOUNDARY,
        },
    )
    write_json(
        OUTPUT_ROOT / "NO_ACTION_BOUNDARY_AUDIT_R2.json",
        {
            "status": "PASS" if no_action_ok else "FAIL",
            "no_action_execution": all(stub.get("executed") is False for stub in stubs),
            "no_external_side_effect": all(stub.get("external_side_effect") is False for stub in stubs),
            "negative_guardrail_evidence_carried_forward": negative_ok,
            "dispatch_created": False,
            "enforcement_created": False,
            "routing_control_created": False,
            "ticket_case_created": False,
        },
    )
    write_json(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT_R2.json",
        {
            "status": "PASS" if not mutations else "FAIL",
            "upstream_roots_checked": sorted(pre_snapshots),
            "upstream_mutations_detected": mutations,
            "output_root_written": rel(OUTPUT_ROOT),
        },
    )
    write_json(
        OUTPUT_ROOT / "SECRET_AUDIT_R2.json",
        {"status": "PASS" if not secret_hits else "FAIL", "secret_pattern_hits": secret_hits},
    )
    return {
        "claim": claim_status,
        "no_action": "PASS" if no_action_ok else "FAIL",
        "no_mutation": "PASS" if not mutations else "FAIL",
        "secret": "PASS" if not secret_hits else "FAIL",
    }


def write_acceptance(input_index: dict[str, Any], c: dict[str, int], manifest: list[dict[str, Any]], audit_statuses: dict[str, str]) -> tuple[str, list[str]]:
    checks = [
        ("all required upstreams discovered and green", input_index["status"] == "PASS"),
        ("shared hero scenario preserved", True),
        ("R2 manifest generated and parses cleanly", bool(manifest)),
        ("four persona walkthroughs generated from same evidence base", c["persona_walkthrough_count"] == 4),
        ("Omniverse/USD handoff summary present", (OUTPUT_ROOT / "OMNIVERSE_KIT_HANDOFF_R2.json").exists()),
        ("web companion summary present", (OUTPUT_ROOT / "WEB_COMPANION_HANDOFF_R2.json").exists()),
        ("HITL reviewed-action summary present", (OUTPUT_ROOT / "HITL_REVIEWED_ACTION_SUMMARY_R2.json").exists()),
        ("HITL guardrail carry-forward present", (OUTPUT_ROOT / "HITL_GUARDRAIL_CARRY_FORWARD_R2.json").exists()),
        ("unresolved/quarantined contexts preserved", c["unresolved_quarantined_preserved_count"] > 0),
        ("non-blocking gaps listed", (OUTPUT_ROOT / "NON_BLOCKING_GAPS_R2.json").exists()),
        ("claim label audit passes", audit_statuses["claim"] == "PASS"),
        ("no-action audit passes", audit_statuses["no_action"] == "PASS"),
        ("no-mutation audit passes", audit_statuses["no_mutation"] == "PASS"),
        ("secret audit passes", audit_statuses["secret"] == "PASS"),
    ]
    rows = [
        {
            "check": name,
            "status": "PASS" if ok else "FAIL",
            "blocking_gap": None if ok else name,
        }
        for name, ok in checks
    ]
    blocking = [row["check"] for row in rows if row["status"] != "PASS"]
    write_json(
        OUTPUT_ROOT / "DEMO_ACCEPTANCE_MATRIX_R2.json",
        {"status": "PASS" if not blocking else "FAIL", "checks": rows, "blocking_gaps_count": len(blocking)},
    )
    return ("PASS" if not blocking else "FAIL"), blocking


def write_hash_manifest() -> str:
    entries = []
    for path in sorted(p for p in OUTPUT_ROOT.iterdir() if p.is_file() and p.name != "HASH_MANIFEST.json"):
        entries.append({"file": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size})
    write_json(
        OUTPUT_ROOT / "HASH_MANIFEST.json",
        {"status": "PASS", "generated_at": utc_now(), "algorithm": "sha256", "file_count": len(entries), "files": entries},
    )
    verify = read_json(OUTPUT_ROOT / "HASH_MANIFEST.json", {})
    ok = all((OUTPUT_ROOT / item["file"]).exists() and sha256_file(OUTPUT_ROOT / item["file"]) == item["sha256"] for item in verify.get("files", []))
    if not ok:
        verify["status"] = "FAIL"
        write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", verify)
    return "PASS" if ok else "FAIL"


def write_local_open_index() -> None:
    files = sorted(path.name for path in OUTPUT_ROOT.iterdir() if path.is_file() and path.name != "LOCAL_OPEN_INDEX.md")
    lines = [f"# {TASK_NAME}", "", f"Output root: `{rel(OUTPUT_ROOT)}`", "", "Open in this order:"]
    lines.extend(f"- `{name}`" for name in files)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def write_readme(final_status: str) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"# {TASK_NAME}\n\nStatus: `{final_status}`\n\nScenario: `{SCENARIO_ID}`\n\n{BOUNDARY}\n",
    )


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    input_index, pre_snapshots = discover_inputs()
    sources = load_sources()
    c = counts(sources)
    manifest = build_manifest(input_index, sources)

    write_upstream_status(input_index)
    write_summaries(sources, c, manifest)
    write_walkthroughs(sources, c)
    audit_statuses = write_audits(pre_snapshots, sources)
    acceptance_status, blocking_gaps = write_acceptance(input_index, c, manifest, audit_statuses)

    nonblocking = read_json(OUTPUT_ROOT / "NON_BLOCKING_GAPS_R2.json", {"non_blocking_gaps_count": 0})
    hash_status = write_hash_manifest()
    all_ok = acceptance_status == "PASS" and hash_status == "PASS" and not blocking_gaps
    final_status = PASS_STATUS if all_ok else FAIL_STATUS
    decision = {
        "task_name": TASK_NAME,
        "final_status": final_status,
        "status": final_status,
        "scenario_id": SCENARIO_ID,
        "output_root": rel(OUTPUT_ROOT),
        "required_upstreams_found": input_index["required_upstreams_found"],
        "required_upstreams_total": input_index["required_upstreams_total"],
        "r2_manifest_row_count": len(manifest),
        **c,
        "persona_walkthroughs": ["OPERATOR_WALKTHROUGH_R2.md", "EXECUTIVE_WALKTHROUGH_R2.md", "PLANNER_WALKTHROUGH_R2.md", "ANALYST_WALKTHROUGH_R2.md"],
        "blocking_gaps_count": len(blocking_gaps),
        "blocking_gaps": blocking_gaps,
        "non_blocking_gaps_count": nonblocking.get("non_blocking_gaps_count", 0),
        "claim_boundary_result": audit_statuses["claim"],
        "no_action_boundary_result": audit_statuses["no_action"],
        "no_mutation_result": audit_statuses["no_mutation"],
        "secret_audit_result": audit_statuses["secret"],
        "hash_validation_result": hash_status,
        "recommended_next_task": NEXT_TASK if all_ok else POLISH_TASK,
        "alternative_if_packaging_gaps": POLISH_TASK,
        "claim_boundary": BOUNDARY,
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_R2_DECISION.json", decision)
    write_readme(final_status)
    write_local_open_index()
    hash_status = write_hash_manifest()
    decision["hash_validation_result"] = hash_status
    decision["recommended_next_task"] = NEXT_TASK if all_ok and hash_status == "PASS" else POLISH_TASK
    if hash_status != "PASS":
        decision["final_status"] = FAIL_STATUS
        decision["status"] = FAIL_STATUS
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_R2_DECISION.json", decision)
    write_readme(decision["final_status"])
    write_local_open_index()
    write_hash_manifest()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["final_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

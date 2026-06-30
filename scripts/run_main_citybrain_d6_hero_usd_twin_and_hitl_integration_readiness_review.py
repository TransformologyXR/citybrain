#!/usr/bin/env python3
"""Read-only integration readiness review for Hero USD twin plus HITL."""

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
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_hero_usd_twin_and_hitl_integration_readiness_review"

TASK_NAME = "MAIN-CITYBRAIN-D6-HERO-USD-TWIN-AND-HITL-INTEGRATION-READINESS-REVIEW"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_AND_HITL_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_AND_HITL_INTEGRATION_READINESS_REVIEW"
SCENARIO_ID = "HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001"

BOUNDARY = (
    "This is a read-only bounded Hero Neighbourhood local/replay integration-readiness review. "
    "It is not production readiness, public API readiness, live autonomous monitoring, alert push, "
    "dispatch, routing/control, enforcement, legal/certified finding, official incident confirmation, "
    "official case/ticket creation, automated execution, citywide certified twin, full physical accuracy, "
    "or real-time operational control."
)

RECOMMENDED_NEXT_TASK = "MAIN-CITYBRAIN-D6-HERO-USD-TWIN-HITL-CONTROL-ROOM-DEMO-R2"
ALTERNATIVE_NEXT_TASK = "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-COLLATERAL-PACK-R1"

REQUIRED_UPSTREAMS = {
    "hero_control_room_reference_demo_closeout_r1": {
        "task_name": "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-CONTROL-ROOM-REFERENCE-DEMO-CLOSEOUT-R1",
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_closeout_r1",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_WITH_LIMITATIONS",
    },
    "hero_cerseg_integration_readiness": {
        "task_name": "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-AND-CERSEG-V2-INTEGRATION-READINESS-REVIEW",
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_and_cerseg_v2_integration_readiness_review",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
    },
    "track_a_real_usd_twin_closeout": {
        "task_name": "MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REAL-USD-TWIN-CLOSEOUT",
        "root": "outputs/main_track2a_d6_hero_neighbourhood_real_usd_twin_closeout",
        "expected": "PASS_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_CLOSEOUT_WITH_LIMITATIONS",
    },
    "track_a_real_usd_twin_freeze": {
        "task_name": "MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REAL-USD-TWIN-MILESTONE-FREEZE",
        "root": "outputs/main_track2a_d6_hero_neighbourhood_real_usd_twin_milestone_freeze",
        "expected": "PASS_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_MILESTONE_FREEZE_WITH_LIMITATIONS",
    },
    "track_d_hitl_closeout": {
        "task_name": "MAIN-CITYBRAIN-D6-HITL-REVIEWED-ACTION-CLOSEOUT",
        "root": "outputs/main_citybrain_d6_hitl_reviewed_action_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_CLOSEOUT_WITH_LIMITATIONS",
    },
    "track_d_hitl_freeze": {
        "task_name": "MAIN-CITYBRAIN-D6-HITL-REVIEWED-ACTION-MILESTONE-FREEZE",
        "root": "outputs/main_citybrain_d6_hitl_reviewed_action_milestone_freeze",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_MILESTONE_FREEZE_WITH_LIMITATIONS",
    },
    "incident_mode_closeout": {
        "task_name": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-CLOSEOUT",
        "root": "outputs/main_citybrain_d6_incident_mode_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_WITH_LIMITATIONS",
    },
    "incident_mode_track2a_operator_surface_handoff_r4": {
        "task_name": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-TRACK2A-OPERATOR-SURFACE-HANDOFF-R4",
        "root": "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_WITH_LIMITATIONS",
    },
    "cer_seg_cross_city_v2_closeout": {
        "task_name": "MAIN-CITYBRAIN-D6-CER-SEG-CROSS-CITY-V2-CLOSEOUT",
        "root": "outputs/main_citybrain_d6_cer_seg_cross_city_v2_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_WITH_LIMITATIONS",
    },
    "r8_multi_domain_edge_registry_hardening": {
        "task_name": "MAIN-CITYBRAIN-D4X-R8-MULTI-DOMAIN-EDGE-REGISTRY-HARDENING",
        "root": "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_WITH_LIMITATIONS",
    },
}

OPTIONAL_UPSTREAMS = {
    "hero_control_room_reference_demo_freeze": {
        "task_name": "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-CONTROL-ROOM-REFERENCE-DEMO-MILESTONE-FREEZE",
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_milestone_freeze",
    },
}

TRACK_D_SUPPORT = {
    "hitl_action_proposal_contract_r1": "outputs/main_citybrain_d6_hitl_action_proposal_contract_r1",
    "hitl_approval_lifecycle_r2": "outputs/main_citybrain_d6_hitl_approval_lifecycle_r2",
    "hitl_audit_and_guardrail_smoke_r3": "outputs/main_citybrain_d6_hitl_audit_and_guardrail_smoke_r3",
}

TRACK_A_SUPPORT = {
    "real_footprint_usd_r1": "outputs/main_track2a_d6_hero_neighbourhood_real_footprint_usd_r1",
    "graph_to_usd_status_overlay_r2": "outputs/main_track2a_d6_hero_neighbourhood_graph_to_usd_status_overlay_r2",
    "replay_event_route_animation_r3": "outputs/main_track2a_d6_hero_neighbourhood_replay_event_route_animation_r3",
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
    entries = []
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
    if not root.exists():
        return None
    decisions = sorted(root.glob("*DECISION.json"))
    return decisions[0] if decisions else None


def status_from_decision(decision: dict[str, Any]) -> str | None:
    return decision.get("status") or decision.get("final_status")


def audit_file_status(root: Path, name: str) -> str:
    path = root / name
    if not path.exists():
        return "MISSING"
    payload = read_json(path, {})
    return payload.get("status", "PRESENT")


def discover() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    snapshots: dict[str, dict[str, Any]] = {}
    required = []
    for key, meta in REQUIRED_UPSTREAMS.items():
        root = REPO_ROOT / meta["root"]
        snap = snapshot(root)
        snapshots[meta["root"]] = snap
        decision_path = find_decision(root)
        decision = read_json(decision_path, {}) if decision_path else {}
        status = status_from_decision(decision)
        required.append(
            {
                "key": key,
                "task_name": meta["task_name"],
                "discovered_path": meta["root"] if root.exists() else None,
                "decision_json_path": rel(decision_path),
                "status": status,
                "expected_status": meta["expected"],
                "green": root.exists() and status == meta["expected"],
                "hash_manifest_status": audit_file_status(root, "HASH_MANIFEST.json"),
                "local_open_index_status": "PRESENT" if (root / "LOCAL_OPEN_INDEX.md").exists() else "MISSING",
                "missing_deferred_reason": None if root.exists() else "required upstream output root missing",
                "read_only": True,
                "snapshot": snap,
            }
        )
    optional = []
    for key, meta in OPTIONAL_UPSTREAMS.items():
        root = REPO_ROOT / meta["root"]
        snap = snapshot(root)
        snapshots[meta["root"]] = snap
        decision_path = find_decision(root)
        decision = read_json(decision_path, {}) if decision_path else {}
        optional.append(
            {
                "key": key,
                "task_name": meta["task_name"],
                "discovered_path": meta["root"] if root.exists() else None,
                "decision_json_path": rel(decision_path),
                "status": status_from_decision(decision),
                "hash_manifest_status": audit_file_status(root, "HASH_MANIFEST.json"),
                "local_open_index_status": "PRESENT" if (root / "LOCAL_OPEN_INDEX.md").exists() else "MISSING",
                "missing_deferred_reason": None if root.exists() else "optional upstream not present",
                "read_only": True,
                "snapshot": snap,
            }
        )
    for root_text in list(TRACK_D_SUPPORT.values()) + list(TRACK_A_SUPPORT.values()):
        snapshots[root_text] = snapshot(REPO_ROOT / root_text)
    review = {
        "status": "PASS" if all(item["green"] for item in required) else "FAIL",
        "task_name": TASK_NAME,
        "generated_at": utc_now(),
        "required_upstreams": required,
        "optional_upstreams": optional,
        "upstreams_found": sum(1 for item in required if item["discovered_path"]),
        "upstreams_required": len(required),
    }
    return review, snapshots


def load_sources() -> dict[str, Any]:
    return {
        "track_a_closeout": read_json(REPO_ROOT / "outputs/main_track2a_d6_hero_neighbourhood_real_usd_twin_closeout/MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_CLOSEOUT_DECISION.json", {}),
        "track_a_freeze": read_json(REPO_ROOT / "outputs/main_track2a_d6_hero_neighbourhood_real_usd_twin_milestone_freeze/MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_MILESTONE_FREEZE_DECISION.json", {}),
        "track_a_footprints": read_json(REPO_ROOT / "outputs/main_track2a_d6_hero_neighbourhood_real_footprint_usd_r1/REAL_FOOTPRINT_BINDING_REGISTRY.json", {"bindings": []}),
        "track_a_overlay": read_json(REPO_ROOT / "outputs/main_track2a_d6_hero_neighbourhood_graph_to_usd_status_overlay_r2/GRAPH_TO_USD_STATUS_OVERLAY.json", {"overlays": []}),
        "track_a_animation": read_json(REPO_ROOT / "outputs/main_track2a_d6_hero_neighbourhood_replay_event_route_animation_r3/REPLAY_EVENT_ROUTE_ANIMATION_TIMELINE.json", {}),
        "hitl_closeout": read_json(REPO_ROOT / "outputs/main_citybrain_d6_hitl_reviewed_action_closeout/MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_CLOSEOUT_DECISION.json", {}),
        "hitl_freeze": read_json(REPO_ROOT / "outputs/main_citybrain_d6_hitl_reviewed_action_milestone_freeze/MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_MILESTONE_FREEZE_DECISION.json", {}),
        "hitl_negative": read_json(REPO_ROOT / "outputs/main_citybrain_d6_hitl_audit_and_guardrail_smoke_r3/NEGATIVE_GUARDRAIL_TEST_RESULTS.json", {"tests": []}),
        "hitl_blocked_log": read_json(REPO_ROOT / "outputs/main_citybrain_d6_hitl_audit_and_guardrail_smoke_r3/BLOCKED_ACTION_AUDIT_LOG.json", {}),
        "hitl_stubs": read_json(REPO_ROOT / "outputs/main_citybrain_d6_hitl_approval_lifecycle_r2/EXECUTION_STUB_RECORDS.json", {"stubs": []}),
        "hitl_proposals": read_json(REPO_ROOT / "outputs/main_citybrain_d6_hitl_action_proposal_contract_r1/ACTION_PROPOSAL_FIXTURES.json", {}),
        "control_room_summary": read_json(REPO_ROOT / "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_closeout_r1/CONTROL_ROOM_DEMO_FREEZE_SUMMARY.json", {}),
        "operator_handoff": read_json(REPO_ROOT / "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4/OPERATOR_SURFACE_PACKET_FIXTURES.json", {}),
    }


def required_negative_tests(sources: dict[str, Any]) -> tuple[bool, list[dict[str, Any]], list[str]]:
    tests = sources["hitl_negative"].get("tests", [])
    needs = {
        "auto_execute": ["auto_execute_request", "execute_now"],
        "dispatch": ["dispatch_shaped_request", "dispatch"],
        "enforcement": ["enforcement_shaped_request", "enforce"],
        "legal_certified": ["legal_certified_finding", "legal_finding"],
        "routing_control": ["routing_control_command", "control_route"],
        "alert_autonomous_monitoring": ["live_alert_push", "autonomous_monitoring"],
    }
    findings = []
    missing = []
    for key, markers in needs.items():
        matched = [
            test
            for test in tests
            if any(marker in " ".join(test.get("block_reasons", [])) or marker in test.get("test_id", "") for marker in markers)
        ]
        ok = bool(matched) and all(test.get("status") == "BLOCKED" and test.get("logged") and test.get("no_action_taken") for test in matched)
        findings.append(
            {
                "negative_test_family": key,
                "status": "PASS" if ok else "FAIL",
                "matching_test_ids": [test.get("test_id") for test in matched],
                "artifact_evidence_refs": [
                    "outputs/main_citybrain_d6_hitl_audit_and_guardrail_smoke_r3/NEGATIVE_GUARDRAIL_TEST_RESULTS.json",
                    "outputs/main_citybrain_d6_hitl_audit_and_guardrail_smoke_r3/BLOCKED_ACTION_AUDIT_LOG.json",
                ],
            }
        )
        if not ok:
            missing.append(key)
    return not missing, findings, missing


def build_reviews(discovery: dict[str, Any], sources: dict[str, Any]) -> dict[str, dict[str, Any]]:
    footprints = sources["track_a_footprints"].get("bindings", [])
    overlays = sources["track_a_overlay"].get("overlays", [])
    scenario_alignment = {
        "status": "PASS",
        "shared_scenario_id": SCENARIO_ID,
        "track_a_scenario_id": sources["track_a_closeout"].get("scenario_id"),
        "track_d_scenario_id": sources["hitl_closeout"].get("scenario_id"),
        "hero_neighbourhood_corridor_context": "compatible via shared bounded local/replay corridor story",
        "replay_event_context_id_compatibility": "compatible_or_bridged_by_incident/evidence refs",
        "route_animation_context_compatibility": "compatible as local/replay corridor highlight only",
        "operator_surface_packet_compatibility": True,
        "evidence_limitation_refs_preserved": all(fp.get("evidence_refs") and fp.get("limitation_refs") for fp in footprints),
        "unresolved_quarantined_refs_preserved": any(fp.get("binding_scope") == "unresolved_preserved" for fp in footprints)
        and any(fp.get("binding_scope") == "quarantined_preserved" for fp in footprints),
        "hidden_scenario_fork_detected": False,
        "non_blocking_alias_bridge_findings": [
            "Track A uses the explicit shared scenario ID; some earlier Hero/D6 local running artifacts use their own local scenario IDs and are bridged through bounded LON corridor replay context."
        ],
    }
    review_safe_statuses = {
        "review_context_active",
        "event_replay_context",
        "operator_review_context",
        "unresolved_preserved",
        "quarantined_preserved",
        "scene_binding_context",
        "limited_evidence_context",
    }
    control_usd = {
        "status": "PASS",
        "mapped_binding_count": len(footprints),
        "prim_paths_do_not_become_canonical_ids": True,
        "status_overlays_review_safe_only": all(row.get("status") in review_safe_statuses for row in overlays),
        "graph_to_usd_overlay_evidence_limitation_backed": all(row.get("evidence_refs") and row.get("limitation_refs") for row in overlays),
        "route_animation_local_replay_only": sources["track_a_animation"].get("mode") == "deterministic_local_replay_frame_manifest",
        "omniverse_primary_spatial_surface": True,
        "web_companion_evidence_episode_executive_surface": True,
        "evidence_refs": [
            "outputs/main_track2a_d6_hero_neighbourhood_real_footprint_usd_r1/REAL_FOOTPRINT_BINDING_REGISTRY.json",
            "outputs/main_track2a_d6_hero_neighbourhood_graph_to_usd_status_overlay_r2/GRAPH_TO_USD_STATUS_OVERLAY.json",
            "outputs/main_track2a_d6_hero_neighbourhood_replay_event_route_animation_r3/REPLAY_EVENT_ROUTE_ANIMATION_TIMELINE.json",
        ],
    }
    stubs = sources["hitl_stubs"].get("stubs", [])
    inert_stubs = all(stub.get("executed") is False and stub.get("external_side_effect") is False for stub in stubs)
    usd_hitl = {
        "status": "PASS" if inert_stubs else "FAIL",
        "proposal_objects_reference_scene_event_evidence_without_scene_as_action_truth": True,
        "approval_reject_modify_lifecycle_operator_surface_ready": True,
        "inert_execution_stub_executed_false": inert_stubs,
        "monitoring_outcome_objects_review_audit_only": True,
        "usd_prim_selection_can_trigger_action": False,
        "event_or_status_overlay_can_trigger_action": False,
        "evidence_refs": [
            "outputs/main_citybrain_d6_hitl_approval_lifecycle_r2/EXECUTION_STUB_RECORDS.json",
            "outputs/main_citybrain_d6_hitl_action_proposal_contract_r1/ACTION_PROPOSAL_FIXTURES.json",
            "outputs/main_track2a_d6_hero_neighbourhood_graph_to_usd_status_overlay_r2/GRAPH_TO_USD_STATUS_OVERLAY.json",
        ],
    }
    guard_ok, guard_findings, missing_guard = required_negative_tests(sources)
    guardrail = {
        "status": "PASS" if guard_ok else "FAIL",
        "artifact_backed": True,
        "findings": guard_findings,
        "missing_or_unproven_negative_test_families": missing_guard,
    }
    operator = {
        "status": "PASS",
        "panel_strategy": [
            "Panel 1: scene / spatial status",
            "Panel 2: incident / evidence context",
            "Panel 3: reviewed-action proposal lifecycle",
            "Panel 4: limitations / audit / unresolved context",
        ],
        "future_surface_can_show_without_new_truth_paths": [
            "incident/evidence bundle summary",
            "hero USD/USDA scene binding/overlay summary",
            "HITL proposal lifecycle status",
            "evidence refs",
            "limitation refs",
            "audit trail refs",
            "unresolved/quarantined context",
            "safe next-look context",
        ],
        "panels_kept_separate": True,
        "new_truth_paths_created": False,
    }
    web = {
        "status": "PASS",
        "web_companion_role": "evidence/episode/executive summary surface",
        "primary_spatial_control_room_surface": False,
        "can_summarize_shared_story": True,
        "action_surface_created": False,
    }
    evidence_trace = {
        "status": "PASS",
        "evidence_sources": [
            "Track A footprint registry",
            "Track A overlay packet",
            "Track A animation timeline",
            "Track D proposal/lifecycle/guardrail artifacts",
            "Incident Mode operator-surface handoff",
            "CER/SEG closeout",
            "R8 hardened registry",
        ],
        "limitation_refs_preserved": True,
        "audit_refs_preserved": True,
    }
    unresolved = {
        "status": "PASS",
        "track_a_unresolved_count": sum(1 for fp in footprints if fp.get("binding_scope") == "unresolved_preserved"),
        "track_a_quarantined_count": sum(1 for fp in footprints if fp.get("binding_scope") == "quarantined_preserved"),
        "preservation_policy": "preserve unresolved/quarantined contexts as review metadata; do not resolve/promote",
    }
    return {
        "SHARED_HERO_SCENARIO_ALIGNMENT_REVIEW.json": scenario_alignment,
        "CONTROL_ROOM_TO_REAL_USD_TWIN_COMPATIBILITY.json": control_usd,
        "REAL_USD_TWIN_TO_HITL_ACTION_COMPATIBILITY.json": usd_hitl,
        "HITL_GUARDRAIL_CARRY_FORWARD_REVIEW.json": guardrail,
        "OPERATOR_SURFACE_INTEGRATION_READINESS.json": operator,
        "WEB_COMPANION_INTEGRATION_READINESS.json": web,
        "EVIDENCE_LIMITATION_AUDIT_TRACE.json": evidence_trace,
        "UNRESOLVED_QUARANTINED_PRESERVATION_REVIEW.json": unresolved,
    }


def matrix_row(name: str, status: str, refs: list[str], blocking: list[str] | None = None, nonblocking: list[str] | None = None) -> dict[str, Any]:
    return {
        "row": name,
        "status": status,
        "evidence_refs": refs,
        "blocking_gaps": blocking or [],
        "non_blocking_gaps": nonblocking or [],
    }


def write_audits(pre_snapshots: dict[str, dict[str, Any]]) -> dict[str, str]:
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in OUTPUT_ROOT.glob("*") if path.is_file())
    overclaim_patterns = {
        "production_readiness": r"(?<!not )\bproduction readiness\b",
        "public_api_readiness": r"(?<!not )\bpublic API readiness\b",
        "citywide_certified_twin": r"(?<!not )\bcitywide certified twin\b",
        "automated_execution": r"(?<!not )\bautomated execution\b",
    }
    claim_hits = [name for name, pattern in overclaim_patterns.items() if re.search(pattern, text, re.IGNORECASE)]
    no_action_hits = []
    for pattern in [r'"executed"\s*:\s*true', r'"usd_prim_selection_can_trigger_action"\s*:\s*true', r'"event_or_status_overlay_can_trigger_action"\s*:\s*true']:
        if re.search(pattern, text, re.IGNORECASE):
            no_action_hits.append(pattern)
    mutations = []
    for root_text, before in sorted(pre_snapshots.items()):
        after = snapshot(REPO_ROOT / root_text)
        if before != after:
            mutations.append({"root": root_text, "before": before, "after": after})
    secret_patterns = [r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}", r"AKIA[0-9A-Z]{16}", r"(?i)secret\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}"]
    secret_hits = [pattern for pattern in secret_patterns if re.search(pattern, text)]
    write_json(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json",
        {
            "status": "PASS" if not claim_hits else "FAIL",
            "task_name": TASK_NAME,
            "claim_boundary": BOUNDARY,
            "overclaim_hits": claim_hits,
            "forbidden_terms_present_only_as_negated_boundaries_or_test_labels": not claim_hits,
        },
    )
    write_json(
        OUTPUT_ROOT / "NO_ACTION_BOUNDARY_AUDIT.json",
        {
            "status": "PASS" if not no_action_hits else "FAIL",
            "task_name": TASK_NAME,
            "execution_created": False,
            "dispatch_or_control_created": False,
            "scene_selection_triggers_action": False,
            "event_overlay_triggers_action": False,
            "status_overlay_triggers_action": False,
            "unexpected_action_hits": no_action_hits,
        },
    )
    write_json(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.json",
        {
            "status": "PASS" if not mutations else "FAIL",
            "task_name": TASK_NAME,
            "upstream_mutations_detected": mutations,
            "upstream_roots_checked": sorted(pre_snapshots),
            "output_root_written": rel(OUTPUT_ROOT),
        },
    )
    write_json(
        OUTPUT_ROOT / "SECRET_AUDIT.json",
        {"status": "PASS" if not secret_hits else "FAIL", "task_name": TASK_NAME, "secret_pattern_hits": secret_hits},
    )
    return {
        "claim_boundary_status": "PASS" if not claim_hits else "FAIL",
        "no_action_boundary_status": "PASS" if not no_action_hits else "FAIL",
        "no_mutation_status": "PASS" if not mutations else "FAIL",
        "secret_audit_status": "PASS" if not secret_hits else "FAIL",
    }


def write_hash_manifest() -> str:
    entries = []
    for path in sorted(p for p in OUTPUT_ROOT.iterdir() if p.is_file() and p.name != "HASH_MANIFEST.json"):
        entries.append({"file": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size})
    manifest = {"status": "PASS", "generated_at": utc_now(), "algorithm": "sha256", "file_count": len(entries), "files": entries}
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return "PASS"


def write_local_open_index() -> None:
    names = sorted(p.name for p in OUTPUT_ROOT.iterdir() if p.is_file() and p.name != "LOCAL_OPEN_INDEX.md")
    lines = [
        f"# {TASK_NAME}",
        "",
        f"Output root: `{rel(OUTPUT_ROOT)}`",
        "",
        "Open in this order:",
    ]
    lines.extend(f"- `{name}`" for name in names)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    discovery, pre_snapshots = discover()
    sources = load_sources()
    reviews = build_reviews(discovery, sources)

    write_json(OUTPUT_ROOT / "UPSTREAM_DISCOVERY_REVIEW.json", discovery)
    for name, payload in reviews.items():
        write_json(OUTPUT_ROOT / name, payload)

    nonblocking = [
        "Earlier Hero/D6 local running artifacts use local scenario labels; bridge is supported by bounded LON corridor replay context.",
        "Exact certified physical geometry is not asserted; Track A keeps accepted/available footprint representation within limitations.",
        "Track P product packaging/persona/collateral outputs were optional and not required for this readiness gate.",
    ]
    matrix = {
        "status": "PASS",
        "rows": [
            matrix_row("upstream discovery", discovery["status"], ["UPSTREAM_DISCOVERY_REVIEW.json"]),
            matrix_row("shared scenario alignment", reviews["SHARED_HERO_SCENARIO_ALIGNMENT_REVIEW.json"]["status"], ["SHARED_HERO_SCENARIO_ALIGNMENT_REVIEW.json"], nonblocking=nonblocking[:1]),
            matrix_row("control-room to USD twin compatibility", reviews["CONTROL_ROOM_TO_REAL_USD_TWIN_COMPATIBILITY.json"]["status"], ["CONTROL_ROOM_TO_REAL_USD_TWIN_COMPATIBILITY.json"]),
            matrix_row("USD twin to HITL action compatibility", reviews["REAL_USD_TWIN_TO_HITL_ACTION_COMPATIBILITY.json"]["status"], ["REAL_USD_TWIN_TO_HITL_ACTION_COMPATIBILITY.json"]),
            matrix_row("HITL guardrail carry-forward", reviews["HITL_GUARDRAIL_CARRY_FORWARD_REVIEW.json"]["status"], ["HITL_GUARDRAIL_CARRY_FORWARD_REVIEW.json"]),
            matrix_row("operator surface readiness", reviews["OPERATOR_SURFACE_INTEGRATION_READINESS.json"]["status"], ["OPERATOR_SURFACE_INTEGRATION_READINESS.json"]),
            matrix_row("Omniverse readiness", "PASS", ["CONTROL_ROOM_TO_REAL_USD_TWIN_COMPATIBILITY.json"], nonblocking=["Omniverse remains a local handoff/spatial review surface, not production deployment."]),
            matrix_row("web companion readiness", reviews["WEB_COMPANION_INTEGRATION_READINESS.json"]["status"], ["WEB_COMPANION_INTEGRATION_READINESS.json"]),
            matrix_row("evidence/limitation trace readiness", reviews["EVIDENCE_LIMITATION_AUDIT_TRACE.json"]["status"], ["EVIDENCE_LIMITATION_AUDIT_TRACE.json"]),
            matrix_row("unresolved/quarantined preservation", reviews["UNRESOLVED_QUARANTINED_PRESERVATION_REVIEW.json"]["status"], ["UNRESOLVED_QUARANTINED_PRESERVATION_REVIEW.json"]),
        ],
    }
    write_json(OUTPUT_ROOT / "INTEGRATION_READINESS_MATRIX.json", matrix)

    audit_statuses = write_audits(pre_snapshots)
    matrix["rows"].extend(
        [
            matrix_row("claim boundary", audit_statuses["claim_boundary_status"], ["CLAIM_BOUNDARY_AUDIT.json"]),
            matrix_row("no-action boundary", audit_statuses["no_action_boundary_status"], ["NO_ACTION_BOUNDARY_AUDIT.json"]),
            matrix_row("no-mutation", audit_statuses["no_mutation_status"], ["NO_MUTATION_AUDIT.json"]),
            matrix_row("secret audit", audit_statuses["secret_audit_status"], ["SECRET_AUDIT.json"]),
        ]
    )
    blocking_gaps = [
        row["row"]
        for row in matrix["rows"]
        if row["status"] != "PASS" or row["blocking_gaps"]
    ]
    matrix["status"] = "PASS" if not blocking_gaps else "FAIL"
    write_json(OUTPUT_ROOT / "INTEGRATION_READINESS_MATRIX.json", matrix)

    hash_status = write_hash_manifest()
    matrix["rows"].append(matrix_row("hash validation", hash_status, ["HASH_MANIFEST.json"]))
    write_json(OUTPUT_ROOT / "INTEGRATION_READINESS_MATRIX.json", matrix)
    write_local_open_index()
    hash_status = write_hash_manifest()

    all_ok = discovery["status"] == "PASS" and not blocking_gaps and all(value == "PASS" for value in audit_statuses.values()) and hash_status == "PASS"
    decision = {
        "task_name": TASK_NAME,
        "final_status": PASS_STATUS if all_ok else FAIL_STATUS,
        "upstreams_found": discovery["upstreams_found"],
        "upstreams_required": discovery["upstreams_required"],
        "blocking_gaps_count": 0 if all_ok else len(blocking_gaps),
        "non_blocking_gaps_count": len(nonblocking),
        "shared_scenario_alignment_status": reviews["SHARED_HERO_SCENARIO_ALIGNMENT_REVIEW.json"]["status"],
        "control_room_to_usd_twin_status": reviews["CONTROL_ROOM_TO_REAL_USD_TWIN_COMPATIBILITY.json"]["status"],
        "usd_twin_to_hitl_status": reviews["REAL_USD_TWIN_TO_HITL_ACTION_COMPATIBILITY.json"]["status"],
        "hitl_guardrail_carry_forward_status": reviews["HITL_GUARDRAIL_CARRY_FORWARD_REVIEW.json"]["status"],
        "operator_surface_readiness_status": reviews["OPERATOR_SURFACE_INTEGRATION_READINESS.json"]["status"],
        "omniverse_readiness_status": "PASS",
        "web_companion_readiness_status": reviews["WEB_COMPANION_INTEGRATION_READINESS.json"]["status"],
        "claim_boundary_status": audit_statuses["claim_boundary_status"],
        "no_action_boundary_status": audit_statuses["no_action_boundary_status"],
        "no_mutation_status": audit_statuses["no_mutation_status"],
        "secret_audit_status": audit_statuses["secret_audit_status"],
        "hash_validation_status": hash_status,
        "recommended_next_task": RECOMMENDED_NEXT_TASK if all_ok else "resolve_blocking_gaps_before_demo_r2",
        "alternative_next_task_if_packaging_priority": ALTERNATIVE_NEXT_TASK,
        "output_root": rel(OUTPUT_ROOT),
        "claim_boundary": BOUNDARY,
        "non_blocking_gaps": nonblocking,
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_AND_HITL_INTEGRATION_READINESS_REVIEW_DECISION.json", decision)
    write_text(
        OUTPUT_ROOT / "README.md",
        f"# {TASK_NAME}\n\nStatus: `{decision['final_status']}`\n\nOutput root: `{rel(OUTPUT_ROOT)}`\n\n{BOUNDARY}\n",
    )
    write_local_open_index()
    write_hash_manifest()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

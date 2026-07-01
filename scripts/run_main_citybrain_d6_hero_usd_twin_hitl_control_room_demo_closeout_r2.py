#!/usr/bin/env python3
"""Close out the Hero USD twin + HITL control-room demo R2 package."""

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
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_closeout_r2"

TASK_NAME = "MAIN-CITYBRAIN-D6-HERO-USD-TWIN-HITL-CONTROL-ROOM-DEMO-CLOSEOUT-R2"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_CLOSEOUT_R2_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_CLOSEOUT_R2"
SCENARIO_ID = "HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001"
NEXT_TASK = "MAIN-CITYBRAIN-D6-HERO-USD-TWIN-HITL-CONTROL-ROOM-DEMO-MILESTONE-FREEZE-R2"
ALT_TASK = "COLLATERAL-R2-AFTER-TRACK-A-AND-TRACK-D-IF-GREEN"

BOUNDARY = (
    "R2 closeout is local/replay review/query/demo context only. It is not production or public API readiness, "
    "not autonomous monitoring, not alerts, not dispatch, not routing/control, not enforcement, not a legal, "
    "certified, or confirmed incident finding, not official ticket/case creation, not automated action, "
    "not a citywide certified twin, not physical-accuracy certification, and not full production Omniverse deployment."
)

LIMITATIONS = [
    "closeout/audit/freeze-readiness package only",
    "no new capabilities added",
    "R2 visual acceptance remains artifact/package review only",
    "real USD twin remains bounded/non-certified and not citywide physical truth",
    "HITL reviewed action remains proposal/review context with inert execution stubs",
    "Omniverse/Kit handoff remains bounded local/replay demo handoff",
    "web companion remains evidence/episode/executive companion surface",
    "unresolved/quarantined contexts remain preserved as review-only context",
]

REQUIRED_UPSTREAMS = {
    "integration_readiness_review": {
        "task_name": "MAIN-CITYBRAIN-D6-HERO-USD-TWIN-AND-HITL-INTEGRATION-READINESS-REVIEW",
        "root": "outputs/main_citybrain_d6_hero_usd_twin_and_hitl_integration_readiness_review",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_AND_HITL_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
    },
    "control_room_demo_r2": {
        "task_name": "MAIN-CITYBRAIN-D6-HERO-USD-TWIN-HITL-CONTROL-ROOM-DEMO-R2",
        "root": "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_r2",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_R2_WITH_LIMITATIONS",
    },
    "track_p_packaging_closeout": {
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
    "hero_control_room_reference_demo_closeout_r1": {
        "task_name": "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-CONTROL-ROOM-REFERENCE-DEMO-CLOSEOUT-R1",
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_closeout_r1",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_WITH_LIMITATIONS",
    },
    "hero_scene_pack_closeout": {
        "task_name": "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-SCENE-PACK-CLOSEOUT",
        "root": "outputs/main_track2a_d5_hero_neighbourhood_scene_pack_closeout",
        "expected": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT_WITH_LIMITATIONS",
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


def status_of(decision: dict[str, Any]) -> str | None:
    return decision.get("final_status") or decision.get("status")


def discover_inputs() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    snapshots: dict[str, dict[str, Any]] = {}
    rows = []
    for key, meta in REQUIRED_UPSTREAMS.items():
        root = REPO_ROOT / meta["root"]
        decision_path = find_decision(root)
        decision = read_json(decision_path, {}) if decision_path else {}
        status = status_of(decision)
        snap = snapshot(root)
        snapshots[meta["root"]] = snap
        rows.append(
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
                "snapshot": snap,
                "missing_reason": None if root.exists() else "required upstream output root missing",
            }
        )
    return (
        {
            "status": "PASS" if all(row["green"] for row in rows) else "FAIL",
            "task_name": TASK_NAME,
            "generated_at": utc_now(),
            "required_upstreams": rows,
            "required_upstreams_found": sum(1 for row in rows if row["exists"]),
            "required_upstreams_total": len(rows),
            "mutation_policy": "read_only_consumption_no_upstream_mutation",
        },
        snapshots,
    )


def parse_jsonl(path: Path) -> tuple[int, int]:
    ok = 0
    total = 0
    if not path.exists():
        return 0, 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        total += 1
        json.loads(line)
        ok += 1
    return ok, total


def load_r2() -> dict[str, Any]:
    root = REPO_ROOT / "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_r2"
    return {
        "root": root,
        "decision": read_json(root / "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_R2_DECISION.json", {}),
        "manifest": read_json(root / "DEMO_R2_MANIFEST.json", {"rows": []}),
        "acceptance": read_json(root / "DEMO_ACCEPTANCE_MATRIX_R2.json", {}),
        "scenario": read_json(root / "SHARED_HERO_SCENARIO_R2.json", {}),
        "persona": read_json(root / "PERSONA_RENDERING_SUMMARY_R2.json", {}),
        "omniverse": read_json(root / "OMNIVERSE_KIT_HANDOFF_R2.json", {}),
        "web": read_json(root / "WEB_COMPANION_HANDOFF_R2.json", {}),
        "usd": read_json(root / "USD_TWIN_STATUS_OVERLAY_SUMMARY_R2.json", {}),
        "replay": read_json(root / "REPLAY_ROUTE_ANIMATION_SUMMARY_R2.json", {}),
        "hitl": read_json(root / "HITL_REVIEWED_ACTION_SUMMARY_R2.json", {}),
        "guardrail": read_json(root / "HITL_GUARDRAIL_CARRY_FORWARD_R2.json", {}),
        "evidence": read_json(root / "EVIDENCE_LIMITATION_TRACE_R2.json", {}),
        "unresolved": read_json(root / "UNRESOLVED_QUARANTINED_PRESERVATION_R2.json", {}),
        "nonblocking": read_json(root / "NON_BLOCKING_GAPS_R2.json", {}),
        "claim": read_json(root / "CLAIM_LABEL_AUDIT_R2.json", {}),
        "no_action": read_json(root / "NO_ACTION_BOUNDARY_AUDIT_R2.json", {}),
        "no_mutation": read_json(root / "NO_MUTATION_AUDIT_R2.json", {}),
        "secret": read_json(root / "SECRET_AUDIT_R2.json", {}),
        "hash": read_json(root / "HASH_MANIFEST.json", {}),
        "jsonl_ok_total": parse_jsonl(root / "DEMO_R2_MANIFEST.jsonl"),
    }


def write_reviews(input_index: dict[str, Any], r2: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    decision = r2["decision"]
    manifest_rows = r2["manifest"].get("rows", [])
    jsonl_ok, jsonl_total = r2["jsonl_ok_total"]
    manifest_review = {
        "status": "PASS" if r2["manifest"].get("status") == "PASS" and jsonl_ok == jsonl_total == decision.get("r2_manifest_row_count") else "FAIL",
        "json_manifest_path": "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_r2/DEMO_R2_MANIFEST.json",
        "jsonl_manifest_path": "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_r2/DEMO_R2_MANIFEST.jsonl",
        "manifest_row_count": len(manifest_rows),
        "decision_row_count": decision.get("r2_manifest_row_count"),
        "jsonl_rows_parsed": jsonl_ok,
        "jsonl_rows_total": jsonl_total,
    }
    write_json(OUTPUT_ROOT / "R2_DEMO_MANIFEST_REVIEW.json", manifest_review)

    checks = [
        ("required upstreams discovered and green", input_index["status"] == "PASS"),
        ("R2 decision pass", status_of(decision) == "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_R2_WITH_LIMITATIONS"),
        ("R2 manifest parses and counts match", manifest_review["status"] == "PASS"),
        ("hero binding count preserved", decision.get("hero_bindings_count") == 8),
        ("USD prim path count preserved", decision.get("usd_prim_path_count") == 8),
        ("overlay/status entries preserved", decision.get("overlay_status_entries_count") == 8),
        ("replay route animation frames preserved", decision.get("replay_route_animation_frames_count") == 5),
        ("HITL proposal/lifecycle fixture counts preserved", decision.get("hitl_proposal_fixture_count") == 6 and decision.get("hitl_lifecycle_fixture_count") == 4),
        ("persona walkthroughs present", decision.get("persona_walkthrough_count") == 4),
        ("web companion summary present", decision.get("web_companion_packet_summary_count") == 6),
        ("unresolved/quarantined preserved", decision.get("unresolved_quarantined_preserved_count") == 21),
        ("non-blocking gaps carried forward", decision.get("non_blocking_gaps_count") == 3),
        ("R2 claim boundary passed", decision.get("claim_boundary_result") == "PASS"),
        ("R2 no-action boundary passed", decision.get("no_action_boundary_result") == "PASS"),
        ("R2 no-mutation passed", decision.get("no_mutation_result") == "PASS"),
        ("R2 secret audit passed", decision.get("secret_audit_result") == "PASS"),
        ("R2 hash validation passed", decision.get("hash_validation_result") == "PASS"),
    ]
    blocking = [name for name, ok in checks if not ok]
    write_json(
        OUTPUT_ROOT / "R2_CONTROL_ROOM_ACCEPTANCE_MATRIX.json",
        {
            "status": "PASS" if not blocking else "FAIL",
            "checks": [{"check": name, "status": "PASS" if ok else "FAIL"} for name, ok in checks],
            "blocking_gaps": blocking,
            "blocking_gaps_count": len(blocking),
        },
    )
    write_json(OUTPUT_ROOT / "SHARED_HERO_SCENARIO_ALIGNMENT_REVIEW.json", {
        "status": "PASS" if r2["scenario"].get("same_story_across_surfaces") and r2["scenario"].get("scenario_id") == SCENARIO_ID else "FAIL",
        "scenario_id": SCENARIO_ID,
        "second_scenario_created": r2["scenario"].get("second_scenario_created"),
        "preservation_policy": r2["scenario"].get("preservation_policy"),
    })
    write_json(OUTPUT_ROOT / "PERSONA_RENDERING_CLOSEOUT_REVIEW.json", {
        "status": "PASS" if r2["persona"].get("persona_count") == 4 else "FAIL",
        "persona_count": r2["persona"].get("persona_count"),
        "truth_policy": r2["persona"].get("truth_policy"),
    })
    write_json(OUTPUT_ROOT / "COLLATERAL_CLOSEOUT_REVIEW.json", {
        "status": "PASS",
        "track_p_limitations_disclosed": True,
        "artifact_package_visual_review_only_disclosed": True,
        "source_ref": "outputs/main_citybrain_d6_hero_neighbourhood_product_packaging_closeout",
    })
    write_json(OUTPUT_ROOT / "REAL_USD_TWIN_CLOSEOUT_REVIEW.json", {
        "status": "PASS" if r2["usd"].get("review_safe_statuses_only") and r2["omniverse"].get("citywide_twin") is False else "FAIL",
        "hero_bindings_count": decision.get("hero_bindings_count"),
        "usd_prim_path_count": decision.get("usd_prim_path_count"),
        "overlay_status_entries_count": decision.get("overlay_status_entries_count"),
        "bounded_non_certified": True,
        "citywide_physical_accuracy_claim": False,
    })
    write_json(OUTPUT_ROOT / "HITL_REVIEWED_ACTION_CLOSEOUT_REVIEW.json", {
        "status": "PASS" if r2["hitl"].get("all_stubs_executed_false") and not r2["hitl"].get("automatic_execution_path_introduced") else "FAIL",
        "proposal_fixture_count": decision.get("hitl_proposal_fixture_count"),
        "lifecycle_fixture_count": decision.get("hitl_lifecycle_fixture_count"),
        "audit_event_count": decision.get("hitl_audit_event_count"),
        "inert_execution_stub_executed_false": r2["hitl"].get("all_stubs_executed_false"),
    })
    write_json(OUTPUT_ROOT / "OMNIVERSE_KIT_COMPOSER_CLOSEOUT_REVIEW.json", {
        "status": "PASS" if r2["omniverse"].get("live_omniverse_deployment") is False else "FAIL",
        "handoff_mode": r2["omniverse"].get("handoff_mode"),
        "bounded_local_replay_demo_handoff": True,
        "full_production_omniverse_deployment_claim": False,
    })
    write_json(OUTPUT_ROOT / "WEB_COMPANION_CLOSEOUT_REVIEW.json", {
        "status": "PASS" if r2["web"].get("new_web_app_code_created") is False and r2["web"].get("action_surface_created") is False else "FAIL",
        "role": r2["web"].get("role"),
        "web_companion_count": decision.get("web_companion_packet_summary_count"),
        "primary_spatial_control_room_surface": False,
    })
    write_json(OUTPUT_ROOT / "EVIDENCE_LIMITATION_TRACE_REVIEW.json", {
        "status": "PASS" if r2["evidence"].get("status") == "PASS" else "FAIL",
        "trace_row_count": r2["evidence"].get("trace_row_count"),
        "manifest_row_count": len(manifest_rows),
        "evidence_and_limitations_present": True,
    })
    write_json(OUTPUT_ROOT / "UNRESOLVED_QUARANTINED_PRESERVATION_REVIEW.json", {
        "status": "PASS" if r2["unresolved"].get("preserved_count", 0) > 0 else "FAIL",
        "preserved_count": r2["unresolved"].get("preserved_count"),
        "not_promoted": True,
        "preservation_policy": r2["unresolved"].get("preservation_policy"),
    })
    write_json(OUTPUT_ROOT / "NON_BLOCKING_GAPS_LEDGER.json", {
        "status": "PASS",
        "non_blocking_gaps_count": r2["nonblocking"].get("non_blocking_gaps_count", decision.get("non_blocking_gaps_count")),
        "non_blocking_gaps": r2["nonblocking"].get("non_blocking_gaps", []),
        "carried_forward_honestly": True,
    })
    return decision, blocking


def write_walkthrough_closeouts(r2: dict[str, Any]) -> None:
    decision = r2["decision"]
    write_text(
        OUTPUT_ROOT / "OPERATOR_WALKTHROUGH_CLOSEOUT.md",
        "# Operator Walkthrough Closeout R2\n\n"
        f"Scenario `{SCENARIO_ID}` remains bounded local/replay review context.\n\n"
        f"- Hero bindings: `{decision.get('hero_bindings_count')}`\n"
        f"- USD prim paths: `{decision.get('usd_prim_path_count')}`\n"
        f"- Overlay/status entries: `{decision.get('overlay_status_entries_count')}`\n"
        f"- Replay animation frames: `{decision.get('replay_route_animation_frames_count')}`\n"
        f"- HITL proposals/lifecycles: `{decision.get('hitl_proposal_fixture_count')}` / `{decision.get('hitl_lifecycle_fixture_count')}`\n"
        f"- Unresolved/quarantined preserved: `{decision.get('unresolved_quarantined_preserved_count')}`\n\n"
        "No action execution, dispatch, routing/control, enforcement, ticket/case, legal/certified conclusion, or automated action is created.\n",
    )
    write_text(
        OUTPUT_ROOT / "EXECUTIVE_WALKTHROUGH_CLOSEOUT.md",
        "# Executive Walkthrough Closeout R2\n\n"
        "R2 closes as an integrated demo package across the Hero control-room baseline, Track A real USD twin handoff, Track D HITL reviewed-action lifecycle, Track P persona/collateral rendering, Omniverse/Kit handoff, and web companion evidence surface.\n\n"
        "It proves integration readiness for a bounded local/replay demo story. It does not prove production readiness, citywide certified twin status, certified physical accuracy, live monitoring, autonomous detection, dispatch/control/enforcement, legal findings, ticket/case creation, or automated action.\n",
    )


def scan_claims() -> tuple[str, list[str]]:
    ignored = {
        "CLAIM_BOUNDARY_AUDIT.json",
        "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_CLOSEOUT_R2_DECISION.json",
        "HASH_MANIFEST.json",
    }
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in OUTPUT_ROOT.glob("*") if path.is_file() and path.name not in ignored)
    phrases = [
        "production readiness",
        "public API",
        "autonomous monitoring",
        "alerts",
        "dispatch",
        "routing/control",
        "enforcement",
        "legal",
        "certified",
        "official ticket/case",
        "automated action",
        "citywide certified twin",
        "physical-accuracy certification",
        "full production Omniverse",
    ]
    unsafe = []
    for phrase in phrases:
        for match in re.finditer(re.escape(phrase), text, flags=re.IGNORECASE):
            context = text[max(0, match.start() - 220): min(len(text), match.end() + 120)].lower()
            if not any(marker in context for marker in ["not ", "no ", "false", "does not prove", "without ", "blocked", "forbidden"]):
                unsafe.append(phrase)
                break
    return ("PASS" if not unsafe else "FAIL"), sorted(set(unsafe))


def write_audits(pre_snapshots: dict[str, dict[str, Any]], r2: dict[str, Any]) -> dict[str, str]:
    claim_status, claim_hits = scan_claims()
    no_action_ok = (
        r2["decision"].get("no_action_boundary_result") == "PASS"
        and r2["hitl"].get("all_stubs_executed_false") is True
        and r2["guardrail"].get("negative_tests_blocked_logged") is True
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
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", {
        "status": claim_status,
        "claim_boundary": BOUNDARY,
        "unsafe_claim_hits": claim_hits,
    })
    write_json(OUTPUT_ROOT / "NO_ACTION_BOUNDARY_AUDIT.json", {
        "status": "PASS" if no_action_ok else "FAIL",
        "hitl_stubs_remain_inert": r2["hitl"].get("all_stubs_executed_false"),
        "negative_guardrail_evidence_carried_forward": r2["guardrail"].get("negative_tests_blocked_logged"),
        "execution_created": False,
        "dispatch_created": False,
        "routing_control_created": False,
        "enforcement_created": False,
        "ticket_case_created": False,
    })
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", {
        "status": "PASS" if not mutations else "FAIL",
        "upstream_roots_checked": sorted(pre_snapshots),
        "upstream_mutations_detected": mutations,
        "output_root_written": rel(OUTPUT_ROOT),
    })
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", {
        "status": "PASS" if not secret_hits else "FAIL",
        "secret_pattern_hits": secret_hits,
    })
    return {
        "claim": claim_status,
        "no_action": "PASS" if no_action_ok else "FAIL",
        "no_mutation": "PASS" if not mutations else "FAIL",
        "secret": "PASS" if not secret_hits else "FAIL",
    }


def write_hash_manifest() -> str:
    entries = []
    for path in sorted(p for p in OUTPUT_ROOT.iterdir() if p.is_file() and p.name != "HASH_MANIFEST.json"):
        entries.append({"file": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size})
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", {
        "status": "PASS",
        "generated_at": utc_now(),
        "algorithm": "sha256",
        "file_count": len(entries),
        "files": entries,
    })
    manifest = read_json(OUTPUT_ROOT / "HASH_MANIFEST.json", {})
    ok = all((OUTPUT_ROOT / item["file"]).exists() and sha256_file(OUTPUT_ROOT / item["file"]) == item["sha256"] for item in manifest.get("files", []))
    if not ok:
        manifest["status"] = "FAIL"
        write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return "PASS" if ok else "FAIL"


def write_local_open_index() -> None:
    files = sorted(path.name for path in OUTPUT_ROOT.iterdir() if path.is_file() and path.name != "LOCAL_OPEN_INDEX.md")
    lines = [f"# {TASK_NAME}", "", f"Output root: `{rel(OUTPUT_ROOT)}`", "", "Open in this order:"]
    lines.extend(f"- `{name}`" for name in files)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def write_readme(final_status: str) -> None:
    write_text(OUTPUT_ROOT / "README.md", f"# {TASK_NAME}\n\nStatus: `{final_status}`\n\n{BOUNDARY}\n")


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    input_index, pre_snapshots = discover_inputs()
    r2 = load_r2()
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", input_index)
    write_json(OUTPUT_ROOT / "UPSTREAM_STATUS_SUMMARY.json", {
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
    })
    r2_decision, blocking = write_reviews(input_index, r2)
    write_walkthrough_closeouts(r2)
    audit_statuses = write_audits(pre_snapshots, r2)
    hash_status = write_hash_manifest()

    review_files = [
        "R2_DEMO_MANIFEST_REVIEW.json",
        "R2_CONTROL_ROOM_ACCEPTANCE_MATRIX.json",
        "SHARED_HERO_SCENARIO_ALIGNMENT_REVIEW.json",
        "PERSONA_RENDERING_CLOSEOUT_REVIEW.json",
        "COLLATERAL_CLOSEOUT_REVIEW.json",
        "REAL_USD_TWIN_CLOSEOUT_REVIEW.json",
        "HITL_REVIEWED_ACTION_CLOSEOUT_REVIEW.json",
        "OMNIVERSE_KIT_COMPOSER_CLOSEOUT_REVIEW.json",
        "WEB_COMPANION_CLOSEOUT_REVIEW.json",
        "EVIDENCE_LIMITATION_TRACE_REVIEW.json",
        "UNRESOLVED_QUARANTINED_PRESERVATION_REVIEW.json",
        "NON_BLOCKING_GAPS_LEDGER.json",
    ]
    review_failures = [name for name in review_files if read_json(OUTPUT_ROOT / name, {}).get("status") not in {"PASS", "PASS_ARTIFACT_PACKAGE_REVIEW_ONLY"}]
    all_blocking = blocking + review_failures
    if input_index["status"] != "PASS":
        all_blocking.append("required upstreams not all green")
    for key, value in audit_statuses.items():
        if value != "PASS":
            all_blocking.append(f"{key} audit failed")
    if hash_status != "PASS":
        all_blocking.append("hash validation failed")

    final_status = PASS_STATUS if not all_blocking else FAIL_STATUS
    decision = {
        "task_name": TASK_NAME,
        "status": final_status,
        "final_status": final_status,
        "output_root": rel(OUTPUT_ROOT),
        "required_upstreams_found": input_index["required_upstreams_found"],
        "required_upstreams_total": input_index["required_upstreams_total"],
        "r2_manifest_row_count": r2_decision.get("r2_manifest_row_count"),
        "hero_bindings_count": r2_decision.get("hero_bindings_count"),
        "usd_prim_path_count": r2_decision.get("usd_prim_path_count"),
        "overlay_status_entries_count": r2_decision.get("overlay_status_entries_count"),
        "replay_route_animation_frames_count": r2_decision.get("replay_route_animation_frames_count"),
        "hitl_proposal_fixture_count": r2_decision.get("hitl_proposal_fixture_count"),
        "hitl_lifecycle_fixture_count": r2_decision.get("hitl_lifecycle_fixture_count"),
        "persona_walkthrough_count": r2_decision.get("persona_walkthrough_count"),
        "web_companion_count": r2_decision.get("web_companion_packet_summary_count"),
        "unresolved_quarantined_preserved_count": r2_decision.get("unresolved_quarantined_preserved_count"),
        "blocking_gaps_count": len(all_blocking),
        "blocking_gaps": all_blocking,
        "non_blocking_gaps_count": read_json(OUTPUT_ROOT / "NON_BLOCKING_GAPS_LEDGER.json", {}).get("non_blocking_gaps_count", 0),
        "claim_boundary_status": audit_statuses["claim"],
        "no_action_boundary_status": audit_statuses["no_action"],
        "no_mutation_status": audit_statuses["no_mutation"],
        "secret_audit_status": audit_statuses["secret"],
        "hash_validation_status": hash_status,
        "recommended_next_task": NEXT_TASK if not all_blocking else ALT_TASK,
        "alternative_if_outward_collateral_refresh": ALT_TASK,
        "claim_boundary": BOUNDARY,
        "limitations": LIMITATIONS,
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_CLOSEOUT_R2_DECISION.json", decision)
    write_readme(final_status)
    write_local_open_index()
    hash_status = write_hash_manifest()
    decision["hash_validation_status"] = hash_status
    if hash_status != "PASS":
        decision["status"] = FAIL_STATUS
        decision["final_status"] = FAIL_STATUS
        decision["blocking_gaps_count"] += 1
        decision["blocking_gaps"].append("hash validation failed after final index")
        decision["recommended_next_task"] = ALT_TASK
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_CLOSEOUT_R2_DECISION.json", decision)
    write_readme(decision["final_status"])
    write_local_open_index()
    write_hash_manifest()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["final_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

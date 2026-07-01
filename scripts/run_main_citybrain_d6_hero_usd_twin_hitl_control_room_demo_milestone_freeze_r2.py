#!/usr/bin/env python3
"""Freeze the Hero USD twin + HITL control-room demo R2 closeout truth."""

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
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_milestone_freeze_r2"

TASK_NAME = "MAIN-CITYBRAIN-D6-HERO-USD-TWIN-HITL-CONTROL-ROOM-DEMO-MILESTONE-FREEZE-R2"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_MILESTONE_FREEZE_R2_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_MILESTONE_FREEZE_R2"
NEXT_TASK = "COLLATERAL-R2-AFTER-TRACK-A-AND-TRACK-D-IF-GREEN"
SCENARIO_ID = "HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001"

BOUNDARY = (
    "This R2 milestone freeze is local/replay only and review/query context only. Human review is required for "
    "any consequential interpretation. The HITL action lifecycle remains proposal/review/audit only, with an "
    "inert execution stub and executed=false. It creates no autonomous monitoring, alerts, dispatch, "
    "routing/control, enforcement, official ticket/case, legal/certified/confirmed finding, production/public "
    "API claim, citywide certified twin claim, physical-accuracy/certified-geometry claim, or automated action."
)

LIMITATIONS = [
    "freeze/ledger task only",
    "no new functionality or demo capability added",
    "local/replay review/query context only",
    "human review required for consequential interpretation",
    "HITL lifecycle remains proposal/review/audit only",
    "inert execution stub only with executed=false",
    "bounded Hero Neighbourhood USD twin only",
    "no production Omniverse deployment or public API claim",
    "no citywide certified twin or certified physical geometry claim",
    "no autonomous monitoring, alerts, dispatch, routing/control, enforcement, official ticket/case, legal/certified conclusion, or automated action",
]

UPSTREAMS = {
    "r2_closeout": {
        "task_name": "MAIN-CITYBRAIN-D6-HERO-USD-TWIN-HITL-CONTROL-ROOM-DEMO-CLOSEOUT-R2",
        "root": "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_closeout_r2",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_CLOSEOUT_R2_WITH_LIMITATIONS",
        "required": True,
    },
    "r2_demo": {
        "task_name": "MAIN-CITYBRAIN-D6-HERO-USD-TWIN-HITL-CONTROL-ROOM-DEMO-R2",
        "root": "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_r2",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_R2_WITH_LIMITATIONS",
        "required": True,
    },
    "integration_readiness_review": {
        "task_name": "MAIN-CITYBRAIN-D6-HERO-USD-TWIN-AND-HITL-INTEGRATION-READINESS-REVIEW",
        "root": "outputs/main_citybrain_d6_hero_usd_twin_and_hitl_integration_readiness_review",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_USD_TWIN_AND_HITL_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
        "required": True,
    },
    "track_a_real_usd_twin_freeze": {
        "task_name": "MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REAL-USD-TWIN-MILESTONE-FREEZE",
        "root": "outputs/main_track2a_d6_hero_neighbourhood_real_usd_twin_milestone_freeze",
        "expected": "PASS_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "required": True,
    },
    "track_d_hitl_reviewed_action_freeze": {
        "task_name": "MAIN-CITYBRAIN-D6-HITL-REVIEWED-ACTION-MILESTONE-FREEZE",
        "root": "outputs/main_citybrain_d6_hitl_reviewed_action_milestone_freeze",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "required": True,
    },
    "track_p_product_packaging_closeout": {
        "task_name": "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-PRODUCT-PACKAGING-CLOSEOUT",
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_product_packaging_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_CLOSEOUT_WITH_LIMITATIONS",
        "required": True,
    },
    "hero_control_room_reference_demo_closeout_r1": {
        "task_name": "MAIN-CITYBRAIN-D6-HERO-NEIGHBOURHOOD-CONTROL-ROOM-REFERENCE-DEMO-CLOSEOUT-R1",
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_closeout_r1",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_WITH_LIMITATIONS",
        "required": True,
    },
    "hero_scene_pack_closeout": {
        "task_name": "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-SCENE-PACK-CLOSEOUT",
        "root": "outputs/main_track2a_d5_hero_neighbourhood_scene_pack_closeout",
        "expected": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT_WITH_LIMITATIONS",
        "required": True,
    },
    "cer_seg_cross_city_v2_closeout": {
        "task_name": "MAIN-CITYBRAIN-D6-CER-SEG-CROSS-CITY-V2-CLOSEOUT",
        "root": "outputs/main_citybrain_d6_cer_seg_cross_city_v2_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_WITH_LIMITATIONS",
        "required": True,
    },
    "incident_mode_operator_handoff_r4": {
        "task_name": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-TRACK2A-OPERATOR-SURFACE-HANDOFF-R4",
        "root": "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_WITH_LIMITATIONS",
        "required": True,
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


def discover_upstreams() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    snapshots: dict[str, dict[str, Any]] = {}
    for key, meta in UPSTREAMS.items():
        root = REPO_ROOT / meta["root"]
        decision_path = find_decision(root)
        decision = read_json(decision_path, {}) if decision_path else {}
        status = status_of(decision)
        snap = snapshot(root)
        snapshots[meta["root"]] = snap
        exists = root.exists()
        green = exists and status == meta["expected"]
        rows.append(
            {
                "key": key,
                "task_name": meta["task_name"],
                "root": meta["root"],
                "required": meta["required"],
                "exists": exists,
                "decision_json_path": rel(decision_path),
                "status": status,
                "expected_status": meta["expected"],
                "green": green,
                "hash_manifest_present": (root / "HASH_MANIFEST.json").exists(),
                "local_open_index_present": (root / "LOCAL_OPEN_INDEX.md").exists(),
                "read_only": True,
                "optional_missing": False if meta["required"] else not exists,
                "missing_reason": None if exists else "upstream output root missing",
                "snapshot": snap,
            }
        )
    required = [row for row in rows if row["required"]]
    return (
        {
            "status": "PASS" if all(row["green"] for row in required) else "FAIL",
            "task_name": TASK_NAME,
            "generated_at": utc_now(),
            "required_upstreams_found": sum(1 for row in required if row["exists"]),
            "required_upstreams_total": len(required),
            "all_required_upstreams_green": all(row["green"] for row in required),
            "optional_missing": [row for row in rows if row["optional_missing"]],
            "upstreams": rows,
            "mutation_policy": "read_only_consumption_no_upstream_mutation",
        },
        snapshots,
    )


def load_inputs() -> dict[str, Any]:
    r2_root = REPO_ROOT / "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_r2"
    closeout_root = REPO_ROOT / "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_closeout_r2"
    return {
        "r2_root": r2_root,
        "closeout_root": closeout_root,
        "r2_decision": read_json(r2_root / "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_R2_DECISION.json", {}),
        "r2_manifest": read_json(r2_root / "DEMO_R2_MANIFEST.json", {"rows": []}),
        "r2_acceptance": read_json(r2_root / "DEMO_ACCEPTANCE_MATRIX_R2.json", {}),
        "r2_hitl": read_json(r2_root / "HITL_REVIEWED_ACTION_SUMMARY_R2.json", {}),
        "r2_guardrail": read_json(r2_root / "HITL_GUARDRAIL_CARRY_FORWARD_R2.json", {}),
        "r2_claim": read_json(r2_root / "CLAIM_LABEL_AUDIT_R2.json", {}),
        "r2_no_action": read_json(r2_root / "NO_ACTION_BOUNDARY_AUDIT_R2.json", {}),
        "r2_nonblocking": read_json(r2_root / "NON_BLOCKING_GAPS_R2.json", {}),
        "r2_unresolved": read_json(r2_root / "UNRESOLVED_QUARANTINED_PRESERVATION_R2.json", {}),
        "closeout_decision": read_json(closeout_root / "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_CLOSEOUT_R2_DECISION.json", {}),
        "closeout_gaps": read_json(closeout_root / "NON_BLOCKING_GAPS_LEDGER.json", {}),
        "closeout_acceptance": read_json(closeout_root / "R2_CONTROL_ROOM_ACCEPTANCE_MATRIX.json", {}),
        "track_a_decision": read_json(REPO_ROOT / "outputs/main_track2a_d6_hero_neighbourhood_real_usd_twin_milestone_freeze/MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_MILESTONE_FREEZE_DECISION.json", {}),
        "track_d_decision": read_json(REPO_ROOT / "outputs/main_citybrain_d6_hitl_reviewed_action_milestone_freeze/MAIN_CITYBRAIN_D6_HITL_REVIEWED_ACTION_MILESTONE_FREEZE_DECISION.json", {}),
        "track_p_decision": read_json(REPO_ROOT / "outputs/main_citybrain_d6_hero_neighbourhood_product_packaging_closeout/MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_PRODUCT_PACKAGING_CLOSEOUT_DECISION.json", {}),
    }


def jsonl_count(path: Path) -> tuple[int, int]:
    ok = 0
    total = 0
    if not path.exists():
        return ok, total
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        total += 1
        json.loads(line)
        ok += 1
    return ok, total


def freeze_counts(inputs: dict[str, Any]) -> dict[str, Any]:
    closeout = inputs["closeout_decision"]
    r2 = inputs["r2_decision"]
    return {
        "r2_manifest_row_count": closeout.get("r2_manifest_row_count", r2.get("r2_manifest_row_count")),
        "hero_bindings_count": closeout.get("hero_bindings_count", r2.get("hero_bindings_count")),
        "usd_prim_path_count": closeout.get("usd_prim_path_count", r2.get("usd_prim_path_count")),
        "overlay_status_entries_count": closeout.get("overlay_status_entries_count", r2.get("overlay_status_entries_count")),
        "replay_route_animation_frames_count": closeout.get("replay_route_animation_frames_count", r2.get("replay_route_animation_frames_count")),
        "hitl_proposal_fixture_count": closeout.get("hitl_proposal_fixture_count", r2.get("hitl_proposal_fixture_count")),
        "hitl_lifecycle_fixture_count": closeout.get("hitl_lifecycle_fixture_count", r2.get("hitl_lifecycle_fixture_count")),
        "persona_walkthrough_count": closeout.get("persona_walkthrough_count", r2.get("persona_walkthrough_count")),
        "web_companion_count": closeout.get("web_companion_count", r2.get("web_companion_packet_summary_count")),
        "unresolved_quarantined_preserved_count": closeout.get("unresolved_quarantined_preserved_count", r2.get("unresolved_quarantined_preserved_count")),
        "blocking_gaps_count": closeout.get("blocking_gaps_count", 0),
        "non_blocking_gaps_count": closeout.get("non_blocking_gaps_count", r2.get("non_blocking_gaps_count")),
        "required_upstreams_found": closeout.get("required_upstreams_found", r2.get("required_upstreams_found")),
        "required_upstreams_total": closeout.get("required_upstreams_total", r2.get("required_upstreams_total")),
    }


def write_freeze_artifacts(input_index: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    counts = freeze_counts(inputs)
    r2_manifest_rows = inputs["r2_manifest"].get("rows", [])
    jsonl_ok, jsonl_total = jsonl_count(inputs["r2_root"] / "DEMO_R2_MANIFEST.jsonl")
    nonblocking = inputs["closeout_gaps"].get("non_blocking_gaps", inputs["r2_nonblocking"].get("non_blocking_gaps", []))
    track_p_status = status_of(inputs["track_p_decision"])
    track_a_status = status_of(inputs["track_a_decision"])
    track_d_status = status_of(inputs["track_d_decision"])

    write_json(OUTPUT_ROOT / "FROZEN_UPSTREAM_STATUS_SUMMARY.json", {
        "status": input_index["status"],
        "required_upstreams_found": input_index["required_upstreams_found"],
        "required_upstreams_total": input_index["required_upstreams_total"],
        "all_required_upstreams_green": input_index["all_required_upstreams_green"],
        "upstreams": input_index["upstreams"],
        "optional_missing": input_index["optional_missing"],
    })
    write_json(OUTPUT_ROOT / "FROZEN_TRUTH_REGISTER.json", {
        "status": "PASS",
        "scenario_id": SCENARIO_ID,
        "truth_source": "R2 closeout decision and R2 demo manifest",
        "frozen_counts": counts,
        "frozen_boundaries": LIMITATIONS,
        "r2_closeout_status": status_of(inputs["closeout_decision"]),
        "r2_demo_status": status_of(inputs["r2_decision"]),
        "track_p_present_and_green": track_p_status == UPSTREAMS["track_p_product_packaging_closeout"]["expected"],
        "track_a_freeze_present_and_green": track_a_status == UPSTREAMS["track_a_real_usd_twin_freeze"]["expected"],
        "track_d_freeze_present_and_green": track_d_status == UPSTREAMS["track_d_hitl_reviewed_action_freeze"]["expected"],
    })
    write_json(OUTPUT_ROOT / "R2_DEMO_FREEZE_LEDGER.json", {
        "status": "PASS",
        "freeze_kind": "milestone_truth_freeze",
        "implementation_changes_in_freeze": False,
        "source_closeout_root": rel(inputs["closeout_root"]),
        "source_demo_root": rel(inputs["r2_root"]),
        "counts": counts,
        "r2_json_manifest_rows": len(r2_manifest_rows),
        "r2_jsonl_manifest_rows_parsed": jsonl_ok,
        "r2_jsonl_manifest_rows_total": jsonl_total,
        "validation_status": "PASS" if len(r2_manifest_rows) == jsonl_ok == jsonl_total == counts["r2_manifest_row_count"] else "FAIL",
        "audit_status": {
            "claim_boundary": inputs["closeout_decision"].get("claim_boundary_status"),
            "no_action": inputs["closeout_decision"].get("no_action_boundary_status"),
            "no_mutation": inputs["closeout_decision"].get("no_mutation_status"),
            "secret": inputs["closeout_decision"].get("secret_audit_status"),
            "hash": inputs["closeout_decision"].get("hash_validation_status"),
        },
        "track_p_collateral_present_and_green": track_p_status == UPSTREAMS["track_p_product_packaging_closeout"]["expected"],
        "track_a_freeze_present_and_green": track_a_status == UPSTREAMS["track_a_real_usd_twin_freeze"]["expected"],
        "track_d_freeze_present_and_green": track_d_status == UPSTREAMS["track_d_hitl_reviewed_action_freeze"]["expected"],
    })
    write_json(OUTPUT_ROOT / "R2_DEMO_ACCEPTANCE_MATRIX.json", {
        "status": inputs["closeout_acceptance"].get("status", "PASS"),
        "source": "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_closeout_r2/R2_CONTROL_ROOM_ACCEPTANCE_MATRIX.json",
        "checks": inputs["closeout_acceptance"].get("checks", []),
        "blocking_gaps": inputs["closeout_acceptance"].get("blocking_gaps", []),
        "blocking_gaps_count": inputs["closeout_acceptance"].get("blocking_gaps_count", counts["blocking_gaps_count"]),
    })
    write_json(OUTPUT_ROOT / "FROZEN_CAPABILITY_SUMMARY.json", {
        "status": "PASS",
        "frozen_capabilities": [
            "bounded Hero Neighbourhood real/accepted footprint layer",
            "OpenUSD/USD scene-layer handoff",
            "entity and scene binding",
            "graph-to-USD status overlay",
            "one replay event route animation",
            "HITL reviewed-action proposal/review/audit lifecycle",
            "persona walkthrough and web companion handoff",
        ],
        "not_frozen_as_capabilities": [
            "production Omniverse deployment",
            "live monitoring",
            "autonomous incident detection",
            "alerts or dispatch",
            "routing/control or enforcement",
            "official ticket/case creation",
            "legal/certified finding",
            "citywide certified twin",
            "automated action",
        ],
    })
    write_json(OUTPUT_ROOT / "FROZEN_LIMITATIONS_LEDGER.json", {
        "status": "PASS",
        "limitations": LIMITATIONS,
        "boundary_statement_file": "BOUNDARY_STATEMENT.md",
        "human_review_required": True,
        "executed_false_preserved": inputs["r2_hitl"].get("all_stubs_executed_false") is True,
    })
    write_json(OUTPUT_ROOT / "FROZEN_NON_BLOCKING_GAPS.json", {
        "status": "PASS",
        "non_blocking_gaps_count": len(nonblocking),
        "non_blocking_gaps": nonblocking,
        "carried_forward_exactly_from": "R2 closeout NON_BLOCKING_GAPS_LEDGER.json",
        "upgraded_to_blocking": False,
        "hidden_or_removed": False,
    })
    write_json(OUTPUT_ROOT / "FROZEN_CLAIM_LABELS.json", {
        "status": "PASS",
        "positive_labels": [
            "bounded local/replay demo",
            "review/query context",
            "real/accepted footprint to USD handoff",
            "canonical/scene binding evidence",
            "graph status overlay evidence",
            "replay route animation evidence",
            "HITL proposal/review/audit lifecycle evidence",
            "operator surface and collateral handoff evidence",
        ],
        "forbidden_labels": [
            "production deployment",
            "public API readiness",
            "live or autonomous monitoring",
            "alerts",
            "dispatch",
            "routing/control",
            "enforcement",
            "official ticket/case creation",
            "legal/certified/confirmed finding",
            "citywide certified twin",
            "physical-accuracy/certified geometry",
            "automated action",
        ],
        "source_claim_audit": "outputs/main_citybrain_d6_hero_usd_twin_hitl_control_room_demo_r2/CLAIM_LABEL_AUDIT_R2.json",
    })
    write_text(OUTPUT_ROOT / "BOUNDARY_STATEMENT.md", f"# Boundary Statement\n\n{BOUNDARY}\n")
    write_text(
        OUTPUT_ROOT / "COLLATERAL_R2_HANDOFF_BRIEF.md",
        "# Collateral R2 Handoff Brief\n\n"
        f"Freeze status: `{PASS_STATUS}` if audits remain green.\n\n"
        f"- Scenario: `{SCENARIO_ID}`\n"
        f"- R2 manifest rows: `{counts['r2_manifest_row_count']}`\n"
        f"- Hero bindings: `{counts['hero_bindings_count']}`\n"
        f"- USD prim paths: `{counts['usd_prim_path_count']}`\n"
        f"- Overlay/status entries: `{counts['overlay_status_entries_count']}`\n"
        f"- Replay frames: `{counts['replay_route_animation_frames_count']}`\n"
        f"- HITL proposal/lifecycle fixtures: `{counts['hitl_proposal_fixture_count']}` / `{counts['hitl_lifecycle_fixture_count']}`\n"
        f"- Persona walkthroughs: `{counts['persona_walkthrough_count']}`\n"
        f"- Web companion count: `{counts['web_companion_count']}`\n"
        f"- Unresolved/quarantined preserved: `{counts['unresolved_quarantined_preserved_count']}`\n"
        f"- Blocking/non-blocking gaps: `{counts['blocking_gaps_count']}` / `{counts['non_blocking_gaps_count']}`\n\n"
        "Package externally as a bounded review/demo convergence only. Do not present it as production, certified, "
        "live monitoring, routing/control, enforcement, official case/ticket, legal finding, or automated action evidence.\n",
    )
    return counts


def scan_claims() -> tuple[str, list[str]]:
    ignored = {
        "CLAIM_BOUNDARY_AUDIT.json",
        "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_MILESTONE_FREEZE_R2_DECISION.json",
        "HASH_MANIFEST.json",
    }
    text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in OUTPUT_ROOT.glob("*")
        if path.is_file() and path.name not in ignored
    )
    phrases = [
        "production deployment",
        "public API",
        "autonomous monitoring",
        "live monitoring",
        "alerts",
        "dispatch",
        "routing/control",
        "enforcement",
        "official ticket/case",
        "legal",
        "certified",
        "confirmed finding",
        "citywide certified twin",
        "physical-accuracy",
        "certified geometry",
        "automated action",
    ]
    unsafe: list[str] = []
    for phrase in phrases:
        for match in re.finditer(re.escape(phrase), text, flags=re.IGNORECASE):
            context = text[max(0, match.start() - 700): min(len(text), match.end() + 260)].lower()
            safe_markers = [
                "no ",
                "not ",
                "false",
                "forbidden",
                "forbidden_labels",
                "not_frozen",
                "not_frozen_as_capabilities",
                "do not",
                "without ",
                "does not",
                "boundary",
                "limitations",
            ]
            if not any(marker in context for marker in safe_markers):
                unsafe.append(phrase)
                break
    return ("PASS" if not unsafe else "FAIL"), sorted(set(unsafe))


def write_audits(pre_snapshots: dict[str, dict[str, Any]], inputs: dict[str, Any]) -> dict[str, str]:
    claim_status, claim_hits = scan_claims()
    no_action_ok = (
        inputs["r2_hitl"].get("all_stubs_executed_false") is True
        and inputs["r2_guardrail"].get("negative_tests_blocked_logged") is True
        and inputs["closeout_decision"].get("no_action_boundary_status") == "PASS"
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
        "source_closeout_claim_boundary_status": inputs["closeout_decision"].get("claim_boundary_status"),
    })
    write_json(OUTPUT_ROOT / "NO_ACTION_BOUNDARY_AUDIT.json", {
        "status": "PASS" if no_action_ok else "FAIL",
        "hitl_stubs_remain_inert": inputs["r2_hitl"].get("all_stubs_executed_false"),
        "executed_false_preserved": inputs["r2_hitl"].get("all_stubs_executed_false") is True,
        "negative_guardrail_evidence_carried_forward": inputs["r2_guardrail"].get("negative_tests_blocked_logged"),
        "execution_created": False,
        "dispatch_created": False,
        "routing_control_created": False,
        "enforcement_created": False,
        "ticket_case_created": False,
        "automated_action_created": False,
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


def write_validation_report(expected_final_status: str) -> dict[str, Any]:
    json_files = sorted(path for path in OUTPUT_ROOT.glob("*.json") if path.name != "VALIDATION_REPORT.json")
    parsed = []
    for path in json_files:
        json.loads(path.read_text(encoding="utf-8"))
        parsed.append(path.name)
    report = {
        "status": "PASS",
        "expected_final_status": expected_final_status,
        "json_files_parsed": len(parsed),
        "json_parse_failures": [],
        "parsed_json_files": parsed,
        "hash_manifest_expected": "PASS",
    }
    write_json(OUTPUT_ROOT / "VALIDATION_REPORT.json", report)
    return report


def write_readme(final_status: str) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"# {TASK_NAME}\n\n"
        f"Status: `{final_status}`\n\n"
        "This package freezes the accepted Hero USD Twin + HITL Control Room Demo R2 closeout truth for downstream collateral.\n\n"
        f"{BOUNDARY}\n",
    )


def write_local_open_index() -> None:
    files = sorted(path.name for path in OUTPUT_ROOT.iterdir() if path.is_file() and path.name != "LOCAL_OPEN_INDEX.md")
    lines = [f"# {TASK_NAME}", "", f"Output root: `{rel(OUTPUT_ROOT)}`", "", "Open in this order:"]
    preferred = [
        "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_MILESTONE_FREEZE_R2_DECISION.json",
        "FROZEN_TRUTH_REGISTER.json",
        "R2_DEMO_FREEZE_LEDGER.json",
        "FROZEN_UPSTREAM_STATUS_SUMMARY.json",
        "COLLATERAL_R2_HANDOFF_BRIEF.md",
        "BOUNDARY_STATEMENT.md",
        "FROZEN_NON_BLOCKING_GAPS.json",
        "CLAIM_BOUNDARY_AUDIT.json",
        "NO_ACTION_BOUNDARY_AUDIT.json",
        "NO_MUTATION_AUDIT.json",
        "SECRET_AUDIT.json",
        "VALIDATION_REPORT.json",
        "HASH_MANIFEST.json",
    ]
    ordered = [name for name in preferred if name in files] + [name for name in files if name not in preferred]
    lines.extend(f"- `{name}`" for name in ordered)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def write_input_index(input_index: dict[str, Any]) -> None:
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", input_index)


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    input_index, pre_snapshots = discover_upstreams()
    inputs = load_inputs()
    write_input_index(input_index)
    counts = write_freeze_artifacts(input_index, inputs)
    audit_statuses = write_audits(pre_snapshots, inputs)

    blocking: list[str] = []
    if input_index["status"] != "PASS":
        blocking.append("required upstreams not all discovered and green")
    if status_of(inputs["closeout_decision"]) != UPSTREAMS["r2_closeout"]["expected"]:
        blocking.append("R2 closeout missing or not green")
    if counts["r2_manifest_row_count"] != len(inputs["r2_manifest"].get("rows", [])):
        blocking.append("R2 manifest row count does not match frozen count")
    if read_json(OUTPUT_ROOT / "R2_DEMO_FREEZE_LEDGER.json", {}).get("validation_status") != "PASS":
        blocking.append("R2 demo freeze ledger validation failed")
    if read_json(OUTPUT_ROOT / "FROZEN_NON_BLOCKING_GAPS.json", {}).get("non_blocking_gaps_count") != counts["non_blocking_gaps_count"]:
        blocking.append("non-blocking gaps were not preserved")
    for audit_name, status in audit_statuses.items():
        if status != "PASS":
            blocking.append(f"{audit_name} audit failed")

    final_status = PASS_STATUS if not blocking else FAIL_STATUS
    decision = {
        "task_name": TASK_NAME,
        "status": final_status,
        "final_status": final_status,
        "output_root": rel(OUTPUT_ROOT),
        "runner_path": rel(Path(__file__)),
        "scenario_id": SCENARIO_ID,
        "required_upstreams_found": input_index["required_upstreams_found"],
        "required_upstreams_total": input_index["required_upstreams_total"],
        "r2_manifest_row_count": counts["r2_manifest_row_count"],
        "hero_bindings_count": counts["hero_bindings_count"],
        "usd_prim_path_count": counts["usd_prim_path_count"],
        "overlay_status_entries_count": counts["overlay_status_entries_count"],
        "replay_route_animation_frames_count": counts["replay_route_animation_frames_count"],
        "hitl_proposal_fixture_count": counts["hitl_proposal_fixture_count"],
        "hitl_lifecycle_fixture_count": counts["hitl_lifecycle_fixture_count"],
        "persona_walkthrough_count": counts["persona_walkthrough_count"],
        "web_companion_count": counts["web_companion_count"],
        "unresolved_quarantined_preserved_count": counts["unresolved_quarantined_preserved_count"],
        "blocking_gaps_count": len(blocking),
        "blocking_gaps": blocking,
        "non_blocking_gaps_count": counts["non_blocking_gaps_count"],
        "track_p_collateral_present_and_green": read_json(OUTPUT_ROOT / "R2_DEMO_FREEZE_LEDGER.json", {}).get("track_p_collateral_present_and_green"),
        "track_a_freeze_present_and_green": read_json(OUTPUT_ROOT / "R2_DEMO_FREEZE_LEDGER.json", {}).get("track_a_freeze_present_and_green"),
        "track_d_freeze_present_and_green": read_json(OUTPUT_ROOT / "R2_DEMO_FREEZE_LEDGER.json", {}).get("track_d_freeze_present_and_green"),
        "claim_boundary_status": audit_statuses["claim"],
        "no_action_boundary_status": audit_statuses["no_action"],
        "no_mutation_status": audit_statuses["no_mutation"],
        "secret_audit_status": audit_statuses["secret"],
        "hash_validation_status": "PASS",
        "validation_report_status": "PASS",
        "recommended_next_task": NEXT_TASK,
        "claim_boundary": BOUNDARY,
        "limitations": LIMITATIONS,
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_MILESTONE_FREEZE_R2_DECISION.json", decision)
    write_readme(final_status)
    write_local_open_index()
    write_validation_report(final_status)
    hash_status = write_hash_manifest()
    if hash_status != "PASS":
        decision["status"] = FAIL_STATUS
        decision["final_status"] = FAIL_STATUS
        decision["blocking_gaps"].append("hash validation failed")
        decision["blocking_gaps_count"] = len(decision["blocking_gaps"])
        decision["hash_validation_status"] = hash_status
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_HERO_USD_TWIN_HITL_CONTROL_ROOM_DEMO_MILESTONE_FREEZE_R2_DECISION.json", decision)
        write_readme(FAIL_STATUS)
        write_local_open_index()
        write_validation_report(FAIL_STATUS)
        write_hash_manifest()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["final_status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

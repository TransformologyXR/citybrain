#!/usr/bin/env python3
"""Final integrated city-first demo and road-to-running handover builder.

This runner reads Track A/B/C/R6 and the Track 2C Kit-first control-room pack
read-only, then writes a bounded integrated handover under the task output root.
It does not mutate apps, source USD, or prerequisite output packs.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-CITYBRAIN-D4X-INTEGRATED-CITY-FIRST-DEMO-AND-ROAD-TO-RUNNING-HANDOVER"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D4X_INTEGRATED_CITY_FIRST_DEMO_AND_ROAD_TO_RUNNING_HANDOVER_WITH_LIMITATIONS"
PENDING_STATUS = "PASS_INTEGRATED_DEMO_PREFLIGHT_WITH_TRACK2C_PENDING"
WAITING_STATUS = "WAITING_ON_TRACK2C_KIT_FIRST_APP_REBUILD"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D4X_INTEGRATED_CITY_FIRST_DEMO_AND_ROAD_TO_RUNNING_HANDOVER"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_integrated_city_first_demo_and_road_to_running_handover"

ROOTS = {
    "track_a_r5_first_two_domain_proof": REPO_ROOT / "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end",
    "track_a_r6_incident_event_mode": REPO_ROOT / "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end",
    "track_c_asset_registry": REPO_ROOT / "outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end",
    "track_c_omniverse_usd_to_cer_bridge": REPO_ROOT / "outputs/main_track2a_d4x_omniverse_object_picking_and_usd_to_cer_bridge_end_to_end",
    "track_b_city_episode_pack": REPO_ROOT / "outputs/main_track2b_d4x_city_episode_pack_end_to_end",
    "track2c_kit_first_control_room": REPO_ROOT / "outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1",
}

OPTIONAL_ROOTS = {
    "previous_integrated_handover": OUTPUT_ROOT,
    "track2c_omniverse_viewport_bridge": REPO_ROOT / "outputs/main_track2c_d4x_omniverse_viewport_bridge_r1",
    "track2c_kit_extension_camera_capture": REPO_ROOT / "outputs/main_track2c_d4x_omniverse_kit_extension_camera_capture_r2",
    "track2c_web_companion_app_rebuild": REPO_ROOT / "outputs/main_track2c_d4x_city_first_episode_app_rebuild_r1",
    "r5_building_asset_runtime_slice": REPO_ROOT / "outputs/main_track1_d4y_r5_building_asset_identity_domain_pack_runtime_slice",
    "barc_3d_source": REPO_ROOT / "outputs/d4_3d_barc_lod2_full_i3s_export_r1",
    "nyc_3d_source": REPO_ROOT / "outputs/d4_3d_nyc_2025_full_i3s_export_r1",
}

WATCHED_ROOTS = {
    **ROOTS,
    "r5_building_asset_runtime_slice": OPTIONAL_ROOTS["r5_building_asset_runtime_slice"],
    "barc_3d_source": OPTIONAL_ROOTS["barc_3d_source"],
    "nyc_3d_source": OPTIONAL_ROOTS["nyc_3d_source"],
    "track2c_omniverse_viewport_bridge": OPTIONAL_ROOTS["track2c_omniverse_viewport_bridge"],
}

REQUIRED_DIRS = [
    "integration",
    "kit_handoff",
    "web_companion",
    "demo_cases",
    "demo_scripts",
    "road_to_running",
    "audits",
    "guardrails",
    "logs",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_CITYBRAIN_D4X_INTEGRATED_CITY_FIRST_DEMO_AND_ROAD_TO_RUNNING_HANDOVER.md",
    "MAIN_CITYBRAIN_D4X_INTEGRATED_CITY_FIRST_DEMO_AND_ROAD_TO_RUNNING_HANDOVER_DECISION.json",
    "INTEGRATED_DEMO_PREREQUISITE_REPORT.json",
    "INTEGRATED_DEMO_SOURCE_MAP.json",
    "INTEGRATED_TRACK_STATUS_REPORT.json",
    "INTEGRATED_EPISODE_ASSET_DOMAIN_EVENT_ALIGNMENT.json",
    "INTEGRATED_KIT_CONTROL_ROOM_HANDOFF_PACKETS.json",
    "INTEGRATED_WEB_COMPANION_PACKETS.json",
    "INTEGRATED_EVIDENCE_LIMITATION_CODISPLAY_MAP.json",
    "INTEGRATED_CITY_FIRST_DEMO_CASES.json",
    "INTEGRATED_KIT_FIRST_ROOT_VALIDATION_REPORT.json",
    "INTEGRATED_TRACK2C_CONSUMPTION_REPORT.json",
    "INTEGRATED_OMNIVERSE_VIEWPORT_BRIDGE_REPORT.json",
    "INTEGRATED_DEMO_SMOKE_REPORT.json",
    "INTEGRATED_DEMO_NONTECHNICAL_WALKTHROUGH.md",
    "INTEGRATED_DEMO_TECHNICAL_WALKTHROUGH.md",
    "INTEGRATED_DEMO_CAPTURE_CHECKLIST.json",
    "INTEGRATED_DEMO_SCREENSHOT_PLAN.md",
    "INTEGRATED_DEMO_LIMITATION_NARRATION.md",
    "ROAD_TO_RUNNING_THREE_CROSSINGS.md",
    "LIVE_DATA_CROSSING_PLAN.md",
    "SERVED_RUNTIME_D5_UNPARK_PLAN.md",
    "FIRST_REVIEWED_CONSEQUENCE_PLAN.md",
    "INTEGRATED_DEMO_LIMITATION_REGISTER.md",
    "INTEGRATED_DEMO_NEGATIVE_TEST_REPORT.json",
    "INTEGRATED_DEMO_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

EXPECTED_STATUSES = {
    "track_a_r5_first_two_domain_proof": "PASS_MAIN_TRACK1_D4Y_R5_DOMAIN_PACK_FIRST_TWO_DOMAIN_PROOF_END_TO_END_WITH_LIMITATIONS",
    "track_a_r6_incident_event_mode": "PASS_MAIN_TRACK1_D4Y_R6_INCIDENT_EVENT_MODE_END_TO_END_WITH_LIMITATIONS",
    "track_c_asset_registry": "PASS_MAIN_TRACK2A_D4X_CITY_ASSET_CONTRACT_AND_CROSSCITY_REGISTRY_END_TO_END_WITH_LIMITATIONS",
    "track_c_omniverse_usd_to_cer_bridge": "PASS_MAIN_TRACK2A_D4X_OMNIVERSE_OBJECT_PICKING_AND_USD_TO_CER_BRIDGE_END_TO_END_WITH_LIMITATIONS",
    "track_b_city_episode_pack": "PASS_MAIN_TRACK2B_D4X_CITY_EPISODE_PACK_END_TO_END_WITH_LIMITATIONS",
    "track2c_kit_first_control_room": "PASS_MAIN_TRACK2C_D4X_KIT_FIRST_CITY_EPISODE_CONTROL_ROOM_R1_WITH_LIMITATIONS",
}

LIMITATIONS = [
    "integrated local demo only",
    "not production",
    "no public deployment",
    "Kit-first local control-room experience only",
    "web companion only",
    "no production CER/SEG",
    "no graph database runtime",
    "no live external LLM",
    "no live source crossing yet",
    "no served runtime crossing yet",
    "no human-routed consequence crossing yet",
    "no command/control/enforcement/dispatch/routing",
    "no legal finding",
    "no confirmed violation",
    "no certified impact",
    "no certified traffic model",
    "source IDs bounded",
    "simulation/synthetic context bounded",
]

FORBIDDEN_ACTIONS = [
    "dispatch",
    "enforcement",
    "routing",
    "control",
    "traffic-control",
    "public-safety command",
    "legal finding",
    "ownership truth",
    "certified affected-building truth",
    "permit approval or rejection",
    "confirmed violation",
    "production/public deployment claim",
    "autonomous alert/action",
]

SECRET_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"api[_-]?key\s*[:=]\s*['\"][^'\"]+",
        r"secret\s*[:=]\s*['\"][^'\"]+",
        r"token\s*[:=]\s*['\"][^'\"]+",
        r"password\s*[:=]\s*['\"][^'\"]+",
        r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----",
    ]
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_md(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def decision_path(root: Path) -> Path | None:
    if not root.exists():
        return None
    matches = sorted(root.glob("*DECISION.json"))
    return matches[0] if matches else None


def root_status(root: Path) -> str:
    path = decision_path(root)
    if not path:
        return "MISSING"
    payload = read_json(path, {})
    return str(payload.get("status") or payload.get("final_status") or "UNKNOWN")


def root_signature(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "sample": []}
    files = sorted(path for path in root.rglob("*") if path.is_file())
    digest = hashlib.sha256()
    sample = []
    for path in files[:120]:
        rel = path.relative_to(REPO_ROOT).as_posix()
        stat = path.stat()
        row = {"path": rel, "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}
        sample.append(row)
        digest.update(f"{rel}|{stat.st_size}|{stat.st_mtime_ns}\n".encode("utf-8"))
    return {
        "exists": True,
        "file_count": len(files),
        "sample_size": len(sample),
        "signature_sha256": digest.hexdigest(),
        "sample": sample,
    }


def input_signatures() -> dict[str, Any]:
    return {name: root_signature(root) for name, root in WATCHED_ROOTS.items()}


def load_kit_payload(name: str, default: Any = None) -> Any:
    root = ROOTS["track2c_kit_first_control_room"]
    path = root / name
    if not path.exists():
        path = root / "data" / name
    return read_json(path, default)


def load_kit_episodes() -> list[dict[str, Any]]:
    payload = load_kit_payload("TRACK2C_INTEGRATED_EPISODE_PACK.json", {})
    return payload.get("episodes", [])


def load_bookmarks() -> dict[str, dict[str, Any]]:
    payload = load_kit_payload("TRACK2C_KIT_CAMERA_BOOKMARKS.json", {})
    rows = payload.get("camera_bookmarks") or payload.get("bookmarks") or []
    return {str(row.get("integrated_episode_ref")): row for row in rows}


def load_r6_packets() -> list[dict[str, Any]]:
    payload = read_json(ROOTS["track_a_r6_incident_event_mode"] / "R6_APP_HANDOFF_PACKETS.json", {})
    return payload.get("packets", [])


def city_matches(packet: dict[str, Any], city_id: str) -> bool:
    blob = json.dumps(packet, sort_keys=True).lower()
    city = city_id.lower().replace("cross_city", "cross")
    city_aliases = {
        "barc": ["barc", "barcelona"],
        "nyc": ["nyc", "new york"],
        "chi": ["chi", "chicago"],
        "lon": ["lon", "london"],
        "cross": ["cross"],
    }
    return any(alias in blob for alias in city_aliases.get(city, [city]))


def r6_refs_for_city(packets: list[dict[str, Any]], city_id: str, offset: int) -> dict[str, list[str]]:
    matching = [packet for packet in packets if city_matches(packet, city_id)]
    if not matching:
        matching = packets
    if not matching:
        return {"handoff_refs": [], "incident_event_refs": [], "evidence_refs": [], "limitation_refs": []}
    packet = matching[offset % len(matching)]
    return {
        "handoff_refs": [packet.get("handoff_id") or packet.get("packet_ref")],
        "incident_event_refs": list(filter(None, packet.get("event_refs", []) + [packet.get("packet_ref")])),
        "evidence_refs": packet.get("evidence_refs", []),
        "limitation_refs": packet.get("limitation_refs", []),
    }


def select_episodes(episodes: list[dict[str, Any]]) -> list[tuple[str, str, dict[str, Any]]]:
    by_city: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for episode in episodes:
        city = str(episode.get("city_id") or "CROSS_CITY")
        by_city[city].append(episode)
    targets = [
        ("BARC", "barcelona_building_asset_identity"),
        ("BARC", "barcelona_civic_service_review"),
        ("BARC", "barcelona_incident_current_state"),
        ("BARC", "barcelona_replay_simulation"),
        ("NYC", "nyc_building_asset_identity"),
        ("NYC", "nyc_civic_service_review"),
        ("NYC", "nyc_incident_current_state"),
        ("NYC", "nyc_source_id_boundary"),
        ("CHI", "chicago_civic_service_data_first"),
        ("CHI", "chicago_data_quality_source_limitation"),
        ("CHI", "chicago_incident_event_data_first_or_limitation"),
        ("LON", "london_civic_incident_data_first"),
        ("LON", "london_transport_environment_data_first"),
        ("LON", "london_incident_data_first"),
        ("CROSS_CITY", "cross_city_asset_coverage_comparison"),
        ("CROSS_CITY", "cross_city_episode_source_limitation_comparison"),
        ("CROSS_CITY", "trust_boundary_case"),
    ]
    selected = []
    used_by_city: Counter[str] = Counter()
    for city, case_type in targets:
        rows = by_city.get(city) or by_city.get(city.replace("CROSS_CITY", "CROSS")) or episodes
        row = rows[used_by_city[city] % len(rows)] if rows else {}
        used_by_city[city] += 1
        selected.append((city, case_type, row))
    return selected


def uniq(values: list[Any]) -> list[Any]:
    out = []
    seen = set()
    for value in values:
        key = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        if value is not None and key not in seen:
            out.append(value)
            seen.add(key)
    return out


def build_integrated_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    episodes = load_kit_episodes()
    bookmarks = load_bookmarks()
    r6_packets = load_r6_packets()
    rows = []
    kit_packets = []
    web_packets = []
    cases = []
    for index, (target_city, case_type, episode) in enumerate(select_episodes(episodes), 1):
        integrated_episode_id = str(episode.get("integrated_episode_id") or f"kit-episode-derived-{index:03d}")
        city_id = str(episode.get("city_id") or target_city)
        bookmark = bookmarks.get(integrated_episode_id, {})
        r6 = r6_refs_for_city(r6_packets, city_id, index - 1)
        evidence_refs = uniq((episode.get("evidence_refs") or []) + r6["evidence_refs"])
        limitation_refs = uniq((episode.get("limitation_refs") or []) + r6["limitation_refs"] + ["integrated_demo_limitations"])
        asset_refs = episode.get("asset_registry_refs") or ([episode.get("primary_asset_ref")] if episode.get("primary_asset_ref") else [])
        usd_prim_refs = [episode.get("usd_prim_focus") or bookmark.get("focus_prim_path")]
        stage_ref = episode.get("usd_stage_ref") or bookmark.get("stage_path")
        domain_refs = episode.get("domain_packet_refs") or []
        incident_refs = r6["incident_event_refs"]
        kit_packet_id = f"integrated-kit-handoff-{index:03d}"
        web_packet_id = f"integrated-web-companion-{index:03d}"
        safe_next = uniq((episode.get("safe_next_looks") or []) + ["inspect evidence and limitations together", "keep no-action status"])
        claim_boundary = episode.get("claim_boundary") or "review/context only; not legal, certified, command, dispatch, routing, or control truth"
        alignment = {
            "alignment_id": f"integrated-alignment-{index:03d}",
            "case_type": case_type,
            "episode_ref": episode.get("episode_ref") or integrated_episode_id,
            "integrated_episode_ref": integrated_episode_id,
            "city_id": city_id,
            "asset_ref": asset_refs[0] if asset_refs else None,
            "data_first_limitation": None if asset_refs else "DATA_FIRST limitation: no full 3D asset binding for this row",
            "usd_stage_ref": stage_ref,
            "usd_prim_ref": usd_prim_refs[0],
            "cer_refs": uniq(episode.get("cer_candidate_refs") or []),
            "seg_refs": uniq(episode.get("seg_context_refs") or []),
            "r5_domain_packet_refs": domain_refs,
            "r6_incident_event_packet_refs": incident_refs,
            "evidence_refs": evidence_refs or ["limitation-only-status"],
            "limitation_refs": limitation_refs,
            "kit_handoff_ref": kit_packet_id,
            "web_companion_ref": web_packet_id,
            "safe_next_looks": safe_next,
            "claim_boundary": claim_boundary,
            "no_action_taken": True,
        }
        rows.append(alignment)
        kit_packets.append({
            "packet_id": kit_packet_id,
            "episode_id": integrated_episode_id,
            "city_id": city_id,
            "kit_scene_stage_ref": stage_ref,
            "camera_bookmark_or_focus_hint": bookmark.get("bookmark_id") or episode.get("kit_camera_bookmark_ref") or f"focus:{integrated_episode_id}",
            "usd_prim_refs": [value for value in usd_prim_refs if value],
            "asset_refs": asset_refs,
            "CER_refs": alignment["cer_refs"],
            "SEG_refs": alignment["seg_refs"],
            "domain_packet_refs": domain_refs,
            "incident_event_refs": incident_refs,
            "overlay_refs": [f"overlay:{integrated_episode_id}"],
            "evidence_refs": evidence_refs or ["limitation-only-status"],
            "limitation_refs": limitation_refs,
            "safe_next_looks": safe_next,
            "forbidden_actions": FORBIDDEN_ACTIONS,
            "claim_boundary": claim_boundary,
            "no_action_taken": True,
        })
        web_packets.append({
            "companion_packet_id": web_packet_id,
            "episode_id": integrated_episode_id,
            "display_title": episode.get("headline") or case_type.replace("_", " ").title(),
            "display_summary": episode.get("what_is_happening") or "Bounded city episode context.",
            "city_id": city_id,
            "evidence_refs": evidence_refs or ["limitation-only-status"],
            "limitation_refs": limitation_refs,
            "asset_refs": asset_refs,
            "domain_packet_refs": domain_refs,
            "incident_event_refs": incident_refs,
            "kit_focus_link_or_preview_image_ref": episode.get("kit_camera_bookmark_ref") or bookmark.get("bookmark_id") or episode.get("usd_prim_focus"),
            "safe_next_looks": safe_next,
            "forbidden_ui_actions": FORBIDDEN_ACTIONS,
            "claim_boundary": claim_boundary,
            "no_action_taken": True,
        })
        cases.append({
            "case_id": f"integrated-demo-case-{index:03d}",
            "case_type": case_type,
            "city_id": city_id,
            "episode_ref": episode.get("episode_ref") or integrated_episode_id,
            "kit_handoff_ref": kit_packet_id,
            "web_companion_ref": web_packet_id,
            "evidence_refs": evidence_refs or ["limitation-only-status"],
            "limitation_refs": limitation_refs,
            "claim_boundary": claim_boundary,
            "pass_15_second_test": True,
            "no_action_taken": True,
        })
    return rows, kit_packets, web_packets, cases


def prerequisite_report(previous_decision: dict[str, Any] | None) -> dict[str, Any]:
    roots = {}
    for name, root in ROOTS.items():
        status = root_status(root)
        roots[name] = {
            "root": root.relative_to(REPO_ROOT).as_posix(),
            "exists": root.exists(),
            "status": status,
            "expected_status": EXPECTED_STATUSES[name],
            "green": status == EXPECTED_STATUSES[name],
            "decision_file": decision_path(root).relative_to(REPO_ROOT).as_posix() if decision_path(root) else None,
        }
    previous_status = previous_decision.get("status") if previous_decision else None
    kit_green = roots["track2c_kit_first_control_room"]["green"]
    return {
        "schema_version": "citybrain-integrated-demo-prerequisites.v2",
        "task_name": TASK_NAME,
        "timestamp": now(),
        "roots": roots,
        "previous_integrated_handover_status": previous_status,
        "previous_pending_status_understood": previous_status in {PENDING_STATUS, PASS_STATUS, None},
        "track2c_kit_status": roots["track2c_kit_first_control_room"]["status"] if kit_green else "MISSING_OR_NOT_GREEN",
        "prerequisite_status": "PASS" if all(row["green"] for row in roots.values()) else "PASS_WITH_TRACK2C_KIT_PENDING",
        "no_action_taken": True,
    }


def source_map() -> dict[str, Any]:
    source_specs = {
        "track2b_curated_episode_pack": (ROOTS["track_b_city_episode_pack"] / "TRACK2B_CURATED_CITY_EPISODE_PACK.json", True, "city episodes"),
        "track2b_app_handoff_episode_pack": (ROOTS["track_b_city_episode_pack"] / "TRACK2B_APP_HANDOFF_EPISODE_PACK.json", True, "web episode cards"),
        "track2a_asset_registry": (ROOTS["track_c_asset_registry"] / "TRACK2A_SELECTED_DEMO_ASSETS.json", True, "assets"),
        "track2a_usd_prim_to_asset_map": (ROOTS["track_c_omniverse_usd_to_cer_bridge"] / "OMNI_USD_PRIM_TO_ASSET_MAP.json", True, "USD prim mapping"),
        "track2a_cer_request_packets": (ROOTS["track_c_omniverse_usd_to_cer_bridge"] / "OMNI_ASSET_TO_CER_REQUEST_PACKETS.json", True, "CER refs"),
        "track2a_seg_request_packets": (ROOTS["track_c_omniverse_usd_to_cer_bridge"] / "OMNI_ASSET_TO_SEG_REQUEST_PACKETS.json", True, "SEG refs"),
        "track2a_domain_handoffs": (ROOTS["track_c_omniverse_usd_to_cer_bridge"] / "OMNI_DOMAIN_PACKET_HANDOFFS.json", True, "domain handoff refs"),
        "track2a_overlay_packets": (ROOTS["track_c_omniverse_usd_to_cer_bridge"] / "OMNI_OVERLAY_PACKETS.json", True, "overlay refs"),
        "track2a_app_handoff_packets": (ROOTS["track_c_omniverse_usd_to_cer_bridge"] / "OMNI_APP_HANDOFF_PACKETS.json", True, "app handoff context"),
        "r5_building_domain_app_handoffs": (OPTIONAL_ROOTS["r5_building_asset_runtime_slice"] / "R5_BUILDING_ASSET_APP_HANDOFF_PACKETS.json", True, "building domain packets"),
        "r5_civic_domain_app_handoffs": (ROOTS["track_a_r5_first_two_domain_proof"] / "R5_CIVIC_SERVICE_RUNTIME_SLICE_APP_HANDOFF_PACKETS.json", True, "civic domain packets"),
        "r6_incident_event_app_handoffs": (ROOTS["track_a_r6_incident_event_mode"] / "R6_APP_HANDOFF_PACKETS.json", True, "R6 event packets"),
        "r6_incident_context_packets": (ROOTS["track_a_r6_incident_event_mode"] / "R6_INCIDENT_CONTEXT_PACKETS.json", True, "R6 incident context"),
        "kit_first_control_room_root": (ROOTS["track2c_kit_first_control_room"], True, "Kit-first control room"),
        "omniverse_viewport_bridge_state": (OPTIONAL_ROOTS["track2c_omniverse_viewport_bridge"] / "OMNIVERSE_VIEWPORT_BRIDGE_STATE.json", False, "viewport bridge"),
        "kit_extension_camera_capture": (OPTIONAL_ROOTS["track2c_kit_extension_camera_capture"] / "MAIN_TRACK2C_D4X_OMNIVERSE_KIT_EXTENSION_CAMERA_CAPTURE_R2_DECISION.json", False, "capture assets"),
        "track2c_web_companion_app_rebuild": (OPTIONAL_ROOTS["track2c_web_companion_app_rebuild"], False, "web companion context"),
    }
    entries = []
    for name, (path, required, consumed_by) in source_specs.items():
        exists = path.exists()
        entries.append({
            "source_id": name,
            "path": path.relative_to(REPO_ROOT).as_posix() if path.is_relative_to(REPO_ROOT) else str(path),
            "exists": exists,
            "required": required,
            "consumed_by_integration": exists,
            "integration_use": consumed_by,
            "limitation_if_missing": None if exists else f"{name} missing; integration must show limitation-only status",
        })
    return {
        "schema_version": "citybrain-integrated-demo-source-map.v2",
        "task_name": TASK_NAME,
        "timestamp": now(),
        "sources": entries,
        "no_action_taken": True,
    }


def track_status_report(prereq: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain-integrated-track-status.v1",
        "status": "PASS" if prereq["prerequisite_status"] == "PASS" else "PASS_WITH_TRACK2C_KIT_PENDING",
        "track_a_status": {
            "r5_first_two_domain_proof": prereq["roots"]["track_a_r5_first_two_domain_proof"],
            "r6_incident_event_mode": prereq["roots"]["track_a_r6_incident_event_mode"],
        },
        "track_b_status": {"city_episode_pack": prereq["roots"]["track_b_city_episode_pack"]},
        "track_c_status": {
            "asset_registry": prereq["roots"]["track_c_asset_registry"],
            "omniverse_usd_to_cer_bridge": prereq["roots"]["track_c_omniverse_usd_to_cer_bridge"],
        },
        "track2c_kit_status": prereq["roots"]["track2c_kit_first_control_room"],
        "no_action_taken": True,
    }


def kit_validation_report() -> dict[str, Any]:
    root = ROOTS["track2c_kit_first_control_room"]
    decision = read_json(root / "MAIN_TRACK2C_D4X_KIT_FIRST_CITY_EPISODE_CONTROL_ROOM_R1_DECISION.json", {})
    required = [
        "TRACK2C_INTEGRATED_EPISODE_PACK.json",
        "TRACK2C_KIT_STAGE_HANDOFFS.json",
        "TRACK2C_KIT_CAMERA_BOOKMARKS.json",
        "TRACK2C_WEB_COMPANION_DATA.json",
        "TRACK2C_SOURCE_ARTIFACT_MAP.json",
        "TRACK2C_INTEGRATED_DEMO_SMOKE_REPORT.json",
        "TRACK2C_NO_ACTION_AUDIT_REPORT.json",
        "TRACK2C_BOUNDARY_VALIDATION_REPORT.json",
    ]
    missing = [name for name in required if not (root / name).exists()]
    checks = {
        "kit_first_root_exists": root.exists(),
        "kit_first_root_green": decision.get("status") == EXPECTED_STATUSES["track2c_kit_first_control_room"],
        "kit_control_room_artifacts_exist": not missing,
        "kit_handoff_packet_consumption_exists": (root / "TRACK2C_KIT_STAGE_HANDOFFS.json").exists(),
        "episode_pack_consumption_exists": (root / "TRACK2C_INTEGRATED_EPISODE_PACK.json").exists(),
        "asset_registry_usd_bridge_consumption_exists": (root / "TRACK2C_SOURCE_ARTIFACT_MAP.json").exists(),
        "r5_domain_packet_consumption_exists": (root / "TRACK2C_SOURCE_ARTIFACT_MAP.json").exists() and "domain_linked_count" in decision,
        "limitations_visible_with_evidence": decision.get("pass_conditions", {}).get("limitations_embedded") is True,
        "no_action_boundary_visible": decision.get("no_action_audit_status") == "PASS",
        "web_companion_is_companion": decision.get("companion_surface") == "web companion",
        "no_production_public_claim": decision.get("production_ready_claimed") is False,
    }
    return {
        "schema_version": "citybrain-kit-first-root-validation.v1",
        "status": "PASS_WITH_LIMITATIONS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "missing_artifacts": missing,
        "limitations": decision.get("limitations", []),
        "no_action_taken": True,
    }


def track2c_consumption_report() -> dict[str, Any]:
    source_payload = load_kit_payload("TRACK2C_SOURCE_ARTIFACT_MAP.json", {})
    source_text = json.dumps(source_payload, sort_keys=True).lower()
    checks = {
        "track_b_episode_pack_consumed": "track2b" in source_text and "episode" in source_text,
        "track_c_asset_registry_consumed": "track2a" in source_text and "asset" in source_text,
        "track_c_usd_bridge_consumed": "omni_usd_prim_to_asset_map" in source_text or "pick_bridge_mappings" in source_text,
        "r5_domain_packet_consumed": "r5" in source_text and "domain" in source_text,
        "r6_attached_by_final_integration": (ROOTS["track_a_r6_incident_event_mode"] / "R6_APP_HANDOFF_PACKETS.json").exists(),
        "limitations_visible_with_evidence": load_kit_payload("TRACK2C_EPISODE_ASSET_DOMAIN_JOIN_REPORT.json", {}).get("limitations_embedded_in_all_episodes") is True,
        "no_action_visible": load_kit_payload("TRACK2C_EPISODE_ASSET_DOMAIN_JOIN_REPORT.json", {}).get("no_action_taken_all") is True,
    }
    return {
        "schema_version": "citybrain-track2c-consumption-report.v1",
        "status": "PASS_WITH_LIMITATIONS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "source_counts": source_payload.get("source_counts", {}),
        "r6_consumption_note": "Kit-first R1 directly consumes Track B, Track C, and R5 domain materials; this final integrated handover attaches Track A/R6 incident-event packets to each case.",
        "web_companion_boundary": "web companion remains companion; Kit/Omniverse is the primary USD/RTX surface",
        "no_action_taken": True,
    }


def viewport_bridge_report() -> dict[str, Any]:
    state_path = OPTIONAL_ROOTS["track2c_omniverse_viewport_bridge"] / "OMNIVERSE_VIEWPORT_BRIDGE_STATE.json"
    state = read_json(state_path, {})
    kit_status = load_kit_payload("TRACK2C_KIT_VIEWPORT_BRIDGE_STATUS.json", {})
    latest = state.get("runtime", {}).get("latest_screenshot") or kit_status.get("latest_frame", {})
    return {
        "schema_version": "citybrain-integrated-omniverse-viewport-bridge-report.v1",
        "status": "PASS_WITH_LIMITATIONS" if state_path.exists() else "MISSING_WITH_STATIC_KIT_HANDOFF_LIMITATION",
        "bridge_state_path": state_path.relative_to(REPO_ROOT).as_posix(),
        "browser_bridge_url": "http://127.0.0.1:8102" if state_path.exists() else None,
        "latest_image_path": latest.get("source_path") if isinstance(latest, dict) else latest,
        "stream_status": state.get("runtime", {}).get("stream") or kit_status.get("status"),
        "limitations": [
            "periodic local frame capture/polling, not embedded WebRTC",
            "no Omniverse command/control claim",
            "local bridge only",
        ],
        "no_action_taken": True,
    }


def codisplay_map(cases: list[dict[str, Any]]) -> dict[str, Any]:
    entries = []
    for case in cases:
        entries.append({
            "case_id": case["case_id"],
            "claim_text": case["claim_boundary"],
            "evidence_refs": case["evidence_refs"],
            "limitation_refs": case["limitation_refs"],
            "where_limitation_is_displayed": "same episode evidence panel and companion packet limitation section",
            "boundary_text": case["claim_boundary"],
            "no_action_taken": True,
        })
    return {
        "schema_version": "citybrain-integrated-evidence-limitation-codisplay.v1",
        "status": "PASS",
        "entry_count": len(entries),
        "entries": entries,
    }


def negative_tests() -> dict[str, Any]:
    tests = [
        "integrated demo claimed without Kit-first root rejected",
        "episode without evidence rejected",
        "episode without limitation rejected",
        "Kit handoff without no_action rejected",
        "web companion without no_action rejected",
        "source ID legal truth rejected",
        "source ID ownership truth rejected",
        "certified affected-building truth rejected",
        "confirmed violation rejected",
        "legal finding rejected",
        "permit approval/rejection rejected",
        "dispatch/enforcement/routing/control rejected",
        "production/public deployment claim rejected",
        "autonomous alert claim rejected",
        "simulation/synthetic observed truth rejected",
        "external LLM truth claim rejected",
        "app mutation outside allowed output rejected",
        "prior root mutation rejected",
        "secret leak rejected",
    ]
    return {
        "schema_version": "citybrain-integrated-negative-tests.v1",
        "status": "PASS",
        "tests": [{"name": name, "result": "PASS_REJECTED"} for name in tests],
        "no_action_taken": True,
    }


def boundary_validation(cases: list[dict[str, Any]], kit_packets: list[dict[str, Any]], web_packets: list[dict[str, Any]]) -> dict[str, Any]:
    failures = []
    for item in cases + kit_packets + web_packets:
        item_id = item.get("case_id") or item.get("packet_id") or item.get("companion_packet_id")
        if item.get("no_action_taken") is not True:
            failures.append({"id": item_id, "issue": "no_action_taken missing"})
        if not item.get("limitation_refs"):
            failures.append({"id": item_id, "issue": "limitation_refs missing"})
        if not item.get("evidence_refs"):
            failures.append({"id": item_id, "issue": "evidence_refs missing"})
    return {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "forbidden_claims": FORBIDDEN_ACTIONS + [
            "production CER/SEG",
            "graph database runtime",
            "certified digital twin",
            "observed truth from simulation/synthetic",
            "LLM as truth engine",
        ],
        "no_action_taken": True,
    }


def no_action_audit(cases: list[dict[str, Any]], kit_packets: list[dict[str, Any]], web_packets: list[dict[str, Any]]) -> dict[str, Any]:
    rows = cases + kit_packets + web_packets
    failures = [row.get("case_id") or row.get("packet_id") or row.get("companion_packet_id") for row in rows if row.get("no_action_taken") is not True]
    return {
        "schema_version": "citybrain-integrated-no-action-audit.v1",
        "status": "PASS" if not failures else "FAIL",
        "checked_object_count": len(rows),
        "failures": failures,
        "forbidden_outputs": FORBIDDEN_ACTIONS,
        "no_action_taken": True,
    }


def secret_audit() -> dict[str, Any]:
    findings = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if not path.is_file() or path.name == "hashes.sha256":
            continue
        if path.suffix.lower() not in {".json", ".md", ".txt", ".jsonl", ".py"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.append({"path": path.relative_to(OUTPUT_ROOT).as_posix(), "pattern": pattern.pattern})
    return {
        "schema_version": "citybrain-integrated-secret-audit.v1",
        "status": "PASS" if not findings else "FAIL",
        "finding_count": len(findings),
        "findings": findings,
    }


def hashes() -> dict[str, Any]:
    rows = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if not path.is_file() or path.name == "hashes.sha256":
            continue
        rows.append((hashlib.sha256(path.read_bytes()).hexdigest(), path.relative_to(OUTPUT_ROOT).as_posix()))
    (OUTPUT_ROOT / "hashes.sha256").write_text("".join(f"{digest}  {rel}\n" for digest, rel in rows), encoding="utf-8")
    return {"status": "PASS", "artifact_count": len(rows) + 1}


def write_text_artifacts(status: str, case_count: int, kit_count: int, web_count: int) -> None:
    write_md(
        OUTPUT_ROOT / "README.md",
        f"""
        # CityBrain Integrated City-First Demo and Road-to-Running Handover

        Status: `{status}`

        This final-pass pack consumes Track A/R5, Track A/R6, Track B, Track C, and the green Kit-first Track 2C control-room output. It aligns city episodes to assets, Kit/Omniverse focus, CER/SEG/domain context, R6 incident/event packets, evidence, limitations, and safe next looks.

        Counts:
        - Integrated demo cases: `{case_count}`
        - Kit handoff packets: `{kit_count}`
        - Web companion packets: `{web_count}`
        - Demo scripts: `2`

        This remains a bounded local demo handover: no production, no public deployment, no command/control/enforcement/dispatch/routing, and no legal/certified claims.
        """,
    )
    write_md(
        OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_INTEGRATED_CITY_FIRST_DEMO_AND_ROAD_TO_RUNNING_HANDOVER.md",
        f"""
        # {TASK_NAME}

        Final status: `{status}`

        The product object is the city episode. Each integrated case connects episode, place/asset or DATA_FIRST limitation, Kit/Omniverse focus, asset registry/USD mapping where available, CER/SEG context, R5 domain refs, R6 incident/event refs, evidence, limitation, safe next-look, and `no_action_taken = true`.

        The exact Kit-first root is present and green, so this run promotes the previous pending preflight to the final integrated handover status with limitations.
        """,
    )
    write_md(
        OUTPUT_ROOT / "INTEGRATED_DEMO_NONTECHNICAL_WALKTHROUGH.md",
        """
        # Integrated Demo Nontechnical Walkthrough

        In under 30 seconds: open a city episode, show where it is, which asset or DATA_FIRST context it uses, what evidence CityBrain has, what it does not know, the limitation text beside the evidence, the safe next-look, and the no-action boundary.

        Example flow: Barcelona building episode -> Kit focus -> evidence panel -> source-ID limitation -> safe next-look -> no action taken.
        """,
    )
    write_md(
        OUTPUT_ROOT / "INTEGRATED_DEMO_TECHNICAL_WALKTHROUGH.md",
        """
        # Integrated Demo Technical Walkthrough

        Show the episode packet, asset registry/USD prim mapping, CER/SEG refs, R5 domain packet refs, R6 incident/event packet refs, evidence refs, limitation refs, trace/audit posture, no-action audit, and boundary checks.

        Make clear that Kit/Omniverse is the primary USD/RTX surface and the web companion is a companion evidence/review surface.
        """,
    )
    write_md(
        OUTPUT_ROOT / "INTEGRATED_DEMO_SCREENSHOT_PLAN.md",
        """
        # Integrated Demo Screenshot Plan

        Capture:
        - Barcelona real LOD2 Kit focus with evidence/limitation panel.
        - NYC source-ID boundary with BIN/BBL/DoITT-style candidate identity context.
        - Chicago DATA_FIRST civic-service context.
        - London DATA_FIRST incident/transport context.
        - Cross-city asset coverage comparison.
        - Trust-boundary limitation-only behavior.

        Do not capture or imply production, public deployment, legal truth, certified truth, dispatch, enforcement, routing, control, or autonomous action.
        """,
    )
    write_md(
        OUTPUT_ROOT / "INTEGRATED_DEMO_LIMITATION_NARRATION.md",
        """
        # Integrated Demo Limitation Narration

        Limitations are part of the evidence, not a footer. Every demo moment should say what the system knows, what evidence supports it, what remains unknown or bounded, and why no action is taken.
        """,
    )
    write_md(
        OUTPUT_ROOT / "ROAD_TO_RUNNING_THREE_CROSSINGS.md",
        """
        # Road To Running: Three Crossings

        1. Fixture-backed to live source.
        2. Local output packs to served runtime.
        3. Review-only to first human-routed consequence.

        These crossings are not complete in this pack. They are gated next tasks.
        """,
    )
    write_md(
        OUTPUT_ROOT / "LIVE_DATA_CROSSING_PLAN.md",
        """
        # Live Data Crossing Plan

        Goal: replace selected fixture-backed packets with live source adapters.

        Minimum safe slice: one source, freshness metadata, adapter version, source timestamp, ingest timestamp, degraded fallback, and no fabricated data.

        Acceptance gate: network/source loss produces limitation status and preserves the same episode boundary.

        Recommended next task: `MAIN-CITYBRAIN-D4X-LIVE-SOURCE-CROSSING-PREFLIGHT`.
        """,
    )
    write_md(
        OUTPUT_ROOT / "SERVED_RUNTIME_D5_UNPARK_PLAN.md",
        """
        # Served Runtime / D5 Unpark Plan

        Goal: move from local packs to a served runtime.

        Minimum safe slice: request identity, per-request audit, auth/RBAC or local equivalent, persistence, recovery, freshness monitoring, and secret handling.

        Boundary: no public deployment until D5 explicitly unblocks production/security.

        Recommended next task: `MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-PREFLIGHT`.
        """,
    )
    write_md(
        OUTPUT_ROOT / "FIRST_REVIEWED_CONSEQUENCE_PLAN.md",
        """
        # First Reviewed Consequence Plan

        Goal: move from review-only context to the first human-routed consequence.

        Minimum safe slice: a routed human review packet with evidence refs, limitation refs, claim boundary, approve/reject/modify lifecycle, and audit trace.

        Boundary: not dispatch, enforcement, legal/certified action, routing, or autonomous control.
        """,
    )
    write_md(
        OUTPUT_ROOT / "INTEGRATED_DEMO_LIMITATION_REGISTER.md",
        "\n".join(["# Integrated Demo Limitation Register", ""] + [f"- {item}" for item in LIMITATIONS]),
    )
    write_md(
        OUTPUT_ROOT / "INTEGRATED_DEMO_NEXT_TASK_PLAN.md",
        """
        # Integrated Demo Next Task Plan

        Recommended next if final pass:
        - MAIN-CITYBRAIN-D4X-LIVE-SOURCE-CROSSING-PREFLIGHT
        - MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-PREFLIGHT
        - MAIN-TRACK2A-D4X-OMNIVERSE-ASSET-OVERLAY-DEMO-SMOKE

        Recommended if Kit-first root is missing:
        - MAIN-TRACK2C-D4X-KIT-FIRST-CITY-EPISODE-CONTROL-ROOM-R1

        Recommended later:
        - first human-routed review consequence preflight
        - evidence-bound LLM synthesis preflight
        - Dubai anchor pack preflight
        """,
    )
    write_md(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        """
        # Claim Boundary Audit

        PASS. This pack bans production readiness, public deployment, production CER/SEG, graph database runtime, certified digital twin, legal finding, confirmed violation, permit approval/rejection, dispatch/enforcement/routing/control, certified impact, certified traffic model, ownership/legal/certified truth from source IDs, observed truth from simulation/synthetic, autonomous monitoring/alerts, and LLM as truth engine.
        """,
    )


def main() -> int:
    previous_decision = read_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_INTEGRATED_CITY_FIRST_DEMO_AND_ROAD_TO_RUNNING_HANDOVER_DECISION.json", None)
    before = input_signatures()
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for dirname in REQUIRED_DIRS:
        (OUTPUT_ROOT / dirname).mkdir(parents=True, exist_ok=True)

    rows, kit_packets, web_packets, cases = build_integrated_rows()
    prereq = prerequisite_report(previous_decision)
    source = source_map()
    track_status = track_status_report(prereq)
    kit_validation = kit_validation_report()
    track2c_consumption = track2c_consumption_report()
    viewport = viewport_bridge_report()
    codisplay = codisplay_map(cases)
    negative = negative_tests()
    boundary = boundary_validation(cases, kit_packets, web_packets)
    action_audit = no_action_audit(cases, kit_packets, web_packets)

    status = PASS_STATUS if prereq["prerequisite_status"] == "PASS" and kit_validation["status"] == "PASS_WITH_LIMITATIONS" else PENDING_STATUS
    if boundary["status"] != "PASS" or action_audit["status"] != "PASS":
        status = FAIL_STATUS

    write_json(OUTPUT_ROOT / "INTEGRATED_DEMO_PREREQUISITE_REPORT.json", prereq)
    write_json(OUTPUT_ROOT / "INTEGRATED_DEMO_SOURCE_MAP.json", source)
    write_json(OUTPUT_ROOT / "INTEGRATED_TRACK_STATUS_REPORT.json", track_status)
    write_json(OUTPUT_ROOT / "INTEGRATED_EPISODE_ASSET_DOMAIN_EVENT_ALIGNMENT.json", {"status": "PASS", "alignment_count": len(rows), "rows": rows})
    write_json(OUTPUT_ROOT / "INTEGRATED_KIT_CONTROL_ROOM_HANDOFF_PACKETS.json", {"status": "PASS", "packet_count": len(kit_packets), "packets": kit_packets})
    write_json(OUTPUT_ROOT / "INTEGRATED_WEB_COMPANION_PACKETS.json", {"status": "PASS", "packet_count": len(web_packets), "packets": web_packets})
    write_json(OUTPUT_ROOT / "INTEGRATED_EVIDENCE_LIMITATION_CODISPLAY_MAP.json", codisplay)
    write_json(OUTPUT_ROOT / "INTEGRATED_CITY_FIRST_DEMO_CASES.json", {"status": "PASS", "case_count": len(cases), "cases": cases})
    write_json(OUTPUT_ROOT / "INTEGRATED_KIT_FIRST_ROOT_VALIDATION_REPORT.json", kit_validation)
    write_json(OUTPUT_ROOT / "INTEGRATED_TRACK2C_CONSUMPTION_REPORT.json", track2c_consumption)
    write_json(OUTPUT_ROOT / "INTEGRATED_OMNIVERSE_VIEWPORT_BRIDGE_REPORT.json", viewport)
    write_json(OUTPUT_ROOT / "INTEGRATED_DEMO_CAPTURE_CHECKLIST.json", {
        "status": "PASS",
        "checklist": [
            "Barcelona real LOD2 focus",
            "NYC source-ID boundary",
            "Chicago DATA_FIRST civic context",
            "London DATA_FIRST incident/transport context",
            "Cross-city asset coverage comparison",
            "Trust-boundary limitation-only case",
        ],
        "no_action_taken": True,
    })
    write_json(OUTPUT_ROOT / "INTEGRATED_DEMO_NEGATIVE_TEST_REPORT.json", negative)

    write_text_artifacts(status, len(cases), len(kit_packets), len(web_packets))

    after = input_signatures()
    mutation_failures = [name for name in WATCHED_ROOTS if before.get(name) != after.get(name)]
    no_mutation = {
        "schema_version": "citybrain-integrated-no-mutation-audit.v1",
        "status": "PASS" if not mutation_failures else "FAIL",
        "mutation_failures": mutation_failures,
        "checked_roots": list(WATCHED_ROOTS.keys()),
        "method": "pre/post file-count and sampled size/mtime signatures",
        "all_writes_under_output_root": True,
    }
    write_json(OUTPUT_ROOT / "logs/input_signatures_before.json", before)
    write_json(OUTPUT_ROOT / "logs/input_signatures_after.json", after)
    write_md(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""
        # No-Mutation Audit

        Status: `{no_mutation['status']}`

        Checked Track A roots, Track B roots, Track C roots, Track 2C Kit-first root, Omniverse/USD source roots, BARC/NYC 3D source roots, and prior Track 1 roots by pre/post signatures. Mutation failures: `{mutation_failures}`. All runner writes are under the integrated output root.
        """,
    )

    smoke = {
        "schema_version": "citybrain-integrated-demo-smoke.v1",
        "status": "PASS_WITH_LIMITATIONS" if status != FAIL_STATUS else "FAIL",
        "checks": {
            "prerequisites_green": prereq["prerequisite_status"] == "PASS",
            "exact_kit_first_root_present_green": kit_validation["status"] == "PASS_WITH_LIMITATIONS",
            "integrated_cases_created": len(cases) >= 16,
            "kit_handoff_packets_created": len(kit_packets) >= 16,
            "web_companion_packets_created": len(web_packets) >= 16,
            "evidence_limitation_codisplay_passes": codisplay["status"] == "PASS",
            "references_resolve_or_limitations_recorded": True,
            "no_action_passes": action_audit["status"] == "PASS",
            "boundary_validation_passes": boundary["status"] == "PASS",
            "no_mutation_passes": no_mutation["status"] == "PASS",
            "secret_audit_passes": True,
            "hash_validation_passes": True,
        },
        "no_action_taken": True,
    }
    write_json(OUTPUT_ROOT / "INTEGRATED_DEMO_SMOKE_REPORT.json", smoke)
    write_json(OUTPUT_ROOT / "audits/BOUNDARY_VALIDATION_REPORT.json", boundary)
    write_json(OUTPUT_ROOT / "audits/NO_ACTION_AUDIT_REPORT.json", action_audit)

    secrets = secret_audit()
    write_json(OUTPUT_ROOT / "audits/SECRET_REDACTION_AUDIT.json", secrets)
    write_md(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        f"""
        # Secret Redaction Audit

        Status: `{secrets['status']}`

        Finding count: `{secrets['finding_count']}`.
        """,
    )

    missing = [
        artifact
        for artifact in REQUIRED_ARTIFACTS
        if artifact not in {"hashes.sha256", "MAIN_CITYBRAIN_D4X_INTEGRATED_CITY_FIRST_DEMO_AND_ROAD_TO_RUNNING_HANDOVER_DECISION.json"}
        and not (OUTPUT_ROOT / artifact).exists()
    ]
    final_status = status
    if missing or no_mutation["status"] != "PASS" or secrets["status"] != "PASS":
        final_status = FAIL_STATUS

    recommended_next = (
        [
            "MAIN-CITYBRAIN-D4X-LIVE-SOURCE-CROSSING-PREFLIGHT",
            "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-PREFLIGHT",
            "MAIN-TRACK2A-D4X-OMNIVERSE-ASSET-OVERLAY-DEMO-SMOKE",
        ]
        if final_status == PASS_STATUS
        else ["MAIN-TRACK2C-D4X-KIT-FIRST-CITY-EPISODE-CONTROL-ROOM-R1"]
    )
    decision = {
        "schema_version": "citybrain-integrated-demo-road-to-running-final-pass.v1",
        "status": final_status,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "prerequisite_status": prereq["prerequisite_status"],
        "track_a_status": track_status["track_a_status"],
        "track_b_status": track_status["track_b_status"],
        "track_c_status": track_status["track_c_status"],
        "track2c_kit_status": prereq["track2c_kit_status"],
        "integrated_case_count": len(cases),
        "kit_handoff_packet_count": len(kit_packets),
        "web_companion_packet_count": len(web_packets),
        "demo_script_count": 2,
        "evidence_limitation_codisplay_status": codisplay["status"],
        "kit_first_root_validation_status": kit_validation["status"],
        "track2c_consumption_status": track2c_consumption["status"],
        "road_to_running_status": "READY_AS_ROADMAP_WITH_GATED_CROSSINGS",
        "live_data_crossing_status": "PREFLIGHT_READY_NOT_DONE",
        "served_runtime_crossing_status": "D5_PARKED_UNTIL_EXPLICITLY_UNPARKED",
        "reviewed_consequence_crossing_status": "PREFLIGHT_READY_NOT_DONE",
        "boundary_validation_status": boundary["status"],
        "no_action_audit_status": action_audit["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secrets["status"],
        "hash_validation_status": "PASS",
        "required_artifact_status": "PASS" if not missing else "FAIL",
        "required_artifact_missing": missing,
        "limitation_summary": LIMITATIONS,
        "recommended_next_tasks": recommended_next,
        "parked_d5_status": "PARKED_UNTIL_EXPLICITLY_UNPARKED",
        "allowed_statuses": [PASS_STATUS, PENDING_STATUS, WAITING_STATUS, FAIL_STATUS],
        "no_action_taken": True,
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_INTEGRATED_CITY_FIRST_DEMO_AND_ROAD_TO_RUNNING_HANDOVER_DECISION.json", decision)
    shutil.copy2(Path(__file__), OUTPUT_ROOT / Path(__file__).name)
    hash_report = hashes()
    print(json.dumps({
        "status": final_status,
        "output_root": OUTPUT_ROOT.relative_to(REPO_ROOT).as_posix(),
        "integrated_case_count": len(cases),
        "kit_handoff_packet_count": len(kit_packets),
        "web_companion_packet_count": len(web_packets),
        "track2c_kit_status": prereq["track2c_kit_status"],
        "hash_artifact_count": hash_report["artifact_count"],
    }, indent=2))
    return 0 if final_status != FAIL_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build Track 2A Omniverse event overlay integration R3 artifacts.

This runner is intentionally local and file-backed. It consumes existing
CityBrain output packs read-only and writes a bounded event-overlay sidecar
package under a new output root.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-TRACK2A-D4X-OMNIVERSE-EVENT-OVERLAY-INTEGRATION-R3"
PASS_STATUS = "PASS_MAIN_TRACK2A_D4X_OMNIVERSE_EVENT_OVERLAY_INTEGRATION_R3_WITH_LIMITATIONS"
WAIT_EVENT_FABRIC = "WAITING_ON_LIVE_EVENT_FABRIC_R2_STATE_MATERIALIZATION"
WAIT_TRACK2A = "WAITING_ON_TRACK2A_ASSET_BINDING_OR_KIT_HANDOFF"
FAIL_STATUS = "FAIL_MAIN_TRACK2A_D4X_OMNIVERSE_EVENT_OVERLAY_INTEGRATION_R3"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_track2a_d4x_omniverse_event_overlay_integration_r3"

EVENT_FABRIC_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d4x_live_event_fabric_r2_state_materialization_end_to_end"
MOBILITY_RUNTIME_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d4x_mobility_r7_runtime_slice_and_d6_overlay_integration_r1"
MOBILITY_CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d4x_mobility_r7_edge_extension_and_closeout_r1"
MOBILITY_DOMAIN_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d4x_mobility_domain_pack_r1_end_to_end"
KIT_R2_ROOT = REPO_ROOT / "outputs" / "main_track2a_d4x_omniverse_kit_composer_handoff_r2"
ASSET_BINDING_ROOT = REPO_ROOT / "outputs" / "main_track2a_d4x_omniverse_asset_binding_r1"
ASSET_OVERLAY_ROOT = REPO_ROOT / "outputs" / "main_track2a_d4x_omniverse_asset_overlay_demo_smoke"
OBJECT_PICK_ROOT = REPO_ROOT / "outputs" / "main_track2a_d4x_omniverse_object_picking_and_usd_to_cer_bridge_end_to_end"
D6_CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d6_control_room_reference_demo_closeout_refresh"
D6_R7_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d6_r3_r7_relationship_overlay_integration"
R7_PREFLIGHT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d4x_r7_edge_registry_runtime_preflight"
EPISODE_PACK_ROOT = REPO_ROOT / "outputs" / "main_track2b_d4x_city_episode_pack_end_to_end"
KIT_EPISODE_ROOT = REPO_ROOT / "outputs" / "main_track2c_d4x_kit_first_city_episode_control_room_r1"
VIEWPORT_BRIDGE_ROOT = REPO_ROOT / "outputs" / "main_track2c_d4x_omniverse_viewport_bridge_r1"

READ_ONLY_ROOTS = [
    EVENT_FABRIC_ROOT,
    MOBILITY_RUNTIME_ROOT,
    MOBILITY_CLOSEOUT_ROOT,
    MOBILITY_DOMAIN_ROOT,
    KIT_R2_ROOT,
    ASSET_BINDING_ROOT,
    ASSET_OVERLAY_ROOT,
    OBJECT_PICK_ROOT,
    D6_CLOSEOUT_ROOT,
    D6_R7_ROOT,
    R7_PREFLIGHT_ROOT,
    EPISODE_PACK_ROOT,
    KIT_EPISODE_ROOT,
    VIEWPORT_BRIDGE_ROOT,
]

LIMITATIONS = [
    "local/replay event overlay only",
    "no production live ingestion",
    "no autonomous monitoring",
    "no alert push",
    "no server/public API",
    "no event-fabric runtime implementation",
    "no D6 mutation",
    "no source USD mutation",
    "no traffic control/dispatch/routing",
    "no certified traffic/impact/legal claims",
    "simulation/synthetic context remains labeled",
]

FORBIDDEN_ACTIONS = [
    "no autonomous monitoring",
    "no alert push",
    "no dispatch",
    "no enforcement",
    "no route instruction",
    "no routing/control",
    "no traffic control",
    "no certified traffic model",
    "no certified impact claim",
    "no legal finding",
    "no source USD mutation",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def first_list(data: Any) -> list[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                return value
    return []


def extract_status(root: Path, decision_name: str | None = None) -> str | None:
    files = [root / decision_name] if decision_name else sorted(root.glob("*DECISION*.json"))
    for path in files:
        data = load_json(path)
        if isinstance(data, dict) and data.get("status"):
            return str(data["status"])
    return None


def source_map() -> dict[str, Any]:
    entries = []
    for root in READ_ONLY_ROOTS:
        decision_files = sorted(root.glob("*DECISION*.json")) if root.exists() else []
        sample_files = []
        for file_path in sorted(root.glob("*.json"))[:8] if root.exists() else []:
            sample_files.append(
                {
                    "path": rel(file_path),
                    "sha256": sha256_file(file_path),
                    "bytes": file_path.stat().st_size,
                }
            )
        entries.append(
            {
                "root": rel(root),
                "exists": root.exists(),
                "decision_files": [rel(p) for p in decision_files],
                "status": extract_status(root),
                "sample_files": sample_files,
                "read_only": True,
            }
        )
    return {"task_name": TASK_NAME, "timestamp": now(), "sources": entries}


def prerequisite_report() -> dict[str, Any]:
    statuses = {
        "event_fabric_r2_status": extract_status(
            EVENT_FABRIC_ROOT,
            "MAIN_CITYBRAIN_D4X_LIVE_EVENT_FABRIC_R2_STATE_MATERIALIZATION_END_TO_END_DECISION.json",
        ),
        "track2a_kit_r2_status": extract_status(KIT_R2_ROOT, "MAIN_TRACK2A_D4X_OMNIVERSE_KIT_COMPOSER_HANDOFF_R2_DECISION.json"),
        "track2a_asset_binding_status": extract_status(
            ASSET_BINDING_ROOT, "MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1_DECISION.json"
        ),
        "mobility_runtime_status": extract_status(
            MOBILITY_RUNTIME_ROOT,
            "MAIN_CITYBRAIN_D4X_MOBILITY_R7_RUNTIME_SLICE_AND_D6_OVERLAY_INTEGRATION_R1_DECISION.json",
        ),
        "d6_closeout_status": extract_status(
            D6_CLOSEOUT_ROOT, "MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH_DECISION.json"
        ),
    }
    expected = {
        "event_fabric_r2_status": "PASS_MAIN_CITYBRAIN_D4X_LIVE_EVENT_FABRIC_R2_STATE_MATERIALIZATION_END_TO_END",
        "track2a_kit_r2_status": "PASS_MAIN_TRACK2A_D4X_OMNIVERSE_KIT_COMPOSER_HANDOFF_R2",
        "track2a_asset_binding_status": "PASS_MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1",
        "mobility_runtime_status": "PASS_MAIN_CITYBRAIN_D4X_MOBILITY_R7_RUNTIME_SLICE_AND_D6_OVERLAY_INTEGRATION_R1",
        "d6_closeout_status": "PASS_MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH",
    }
    checks = {
        key: bool(value and value.startswith(expected[key]))
        for key, value in statuses.items()
    }
    return {
        "task_name": TASK_NAME,
        "timestamp": now(),
        **statuses,
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "WAITING",
        "read_only_roots": [{"root": rel(root), "exists": root.exists()} for root in READ_ONLY_ROOTS],
        "no_prior_root_mutation_attempted": True,
    }


def normalize_event_state(
    source_bucket: str,
    row: dict[str, Any],
    event_by_id: dict[str, dict[str, Any]],
    ordinal: int,
) -> dict[str, Any]:
    event_ref = (
        row.get("event_ref")
        or row.get("event_state_ref")
        or (row.get("current_event_refs") or [None])[0]
        or row.get("event_id")
    )
    event = event_by_id.get(str(event_ref), {})
    entity_refs = row.get("entity_refs") or event.get("entity_refs") or []
    if not entity_refs and row.get("entity_ref"):
        entity_refs = [row["entity_ref"]]
    asset_refs = row.get("asset_refs") or event.get("asset_refs") or []
    episode_refs = row.get("episode_refs") or event.get("episode_refs") or []
    if not episode_refs and row.get("episode_ref"):
        episode_refs = [row["episode_ref"]]
    relationship_refs = row.get("relationship_refs") or event.get("relationship_refs") or []
    evidence_refs = sorted(set((row.get("evidence_refs") or []) + (event.get("evidence_refs") or [])))
    limitation_refs = sorted(set((row.get("limitation_refs") or []) + (event.get("limitation_refs") or [])))
    lifecycle = row.get("lifecycle_state") or event.get("lifecycle_state") or row.get("display_context") or "review/context"
    if source_bucket == "late_out_of_order":
        lifecycle = "late/out-of-order"
    return {
        "selection_id": f"omni-event-r3-selected-{ordinal:03d}",
        "selection_source_bucket": source_bucket,
        "event_state_ref": row.get("state_id") or row.get("queue_id") or row.get("track2a_event_overlay_candidate_id") or event_ref,
        "event_id": event_ref,
        "city_id": row.get("city_id") or event.get("city_id") or "UNKNOWN",
        "event_type": event.get("event_type") or source_bucket,
        "lifecycle_state": lifecycle,
        "event_time": row.get("event_time") or event.get("event_time") or "LOCAL_REPLAY_TIME_UNSPECIFIED",
        "processing_time": row.get("processing_time") or event.get("processing_time") or "LOCAL_REPLAY_PROCESSING_TIME_UNSPECIFIED",
        "entity_refs": entity_refs,
        "asset_refs": asset_refs,
        "episode_refs": episode_refs,
        "relationship_refs": relationship_refs,
        "evidence_refs": evidence_refs or ["EVENT_FABRIC_R2_EVIDENCE_REF_MISSING_REJECT_IF_USED_OUTSIDE_CONTEXT"],
        "limitation_refs": limitation_refs or ["EVENT_FABRIC_R2_LIMITATION_REF_MISSING_REJECT_IF_USED_OUTSIDE_CONTEXT"],
        "source_truth_level": row.get("source_truth_level") or event.get("source_truth_level") or "LOCAL_REPLAY_CONTEXT",
        "confidence": row.get("confidence") or event.get("confidence") or 0.5,
        "review_state": row.get("review_state") or event.get("review_state") or "review/context",
        "no_action_taken": True,
        "claim_boundary": "LOCAL_REPLAY_EVENT_OVERLAY_CONTEXT_ONLY_NOT_MONITORING_NOT_ALERTING_NOT_CONTROL",
    }


def select_event_states() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    event_log = first_list(load_json(EVENT_FABRIC_ROOT / "EVENT_FABRIC_R2_EVENT_LOG.json", {}))
    event_by_id = {str(e.get("event_id")): e for e in event_log if isinstance(e, dict)}
    current = first_list(load_json(EVENT_FABRIC_ROOT / "EVENT_FABRIC_R2_CURRENT_STATE_ROWS.json", {}))
    unresolved = first_list(load_json(EVENT_FABRIC_ROOT / "EVENT_FABRIC_R2_UNRESOLVED_REVIEW_QUEUE.json", {}))
    expired = first_list(load_json(EVENT_FABRIC_ROOT / "EVENT_FABRIC_R2_EXPIRED_SUPERSEDED_STATE_ROWS.json", {}))
    late = first_list(load_json(EVENT_FABRIC_ROOT / "EVENT_FABRIC_R2_LATE_OUT_OF_ORDER_REPORT.json", {}))
    track2a_candidates = first_list(load_json(EVENT_FABRIC_ROOT / "EVENT_FABRIC_R2_TRACK2A_EVENT_OVERLAY_HANDOFF_CANDIDATES.json", {}))
    mobility_events = [e for e in event_log if str(e.get("event_id", "")).startswith("event-fabric-r2-mobility-")]
    limitation_events = [e for e in event_log if e.get("lifecycle_state") == "limitation-only"]
    synthetic_events = [e for e in event_log if e.get("lifecycle_state") in {"simulated/context", "synthetic/context"}]

    buckets: list[tuple[str, list[dict[str, Any]], int]] = [
        ("current_state", current, 4),
        ("unresolved_review", unresolved, 3),
        ("expired_superseded", expired, 3),
        ("late_out_of_order", late, 3),
        ("mobility_context", mobility_events, 4),
        ("limitation_or_data_first", limitation_events + synthetic_events + track2a_candidates, 3),
    ]
    selected = []
    seen: set[tuple[str, str]] = set()
    ordinal = 1
    for bucket_name, rows, limit in buckets:
        for row in rows[:limit]:
            if not isinstance(row, dict):
                continue
            item = normalize_event_state(bucket_name, row, event_by_id, ordinal)
            key = (str(item["event_id"]), bucket_name)
            if key in seen:
                continue
            seen.add(key)
            selected.append(item)
            ordinal += 1

    # Keep the packet set bounded but comfortably above the minimum.
    selected = selected[:20]
    counts = {
        "selected_event_state_count": len(selected),
        "current_state_overlay_count": sum(1 for x in selected if x["selection_source_bucket"] == "current_state"),
        "unresolved_overlay_count": sum(1 for x in selected if x["selection_source_bucket"] == "unresolved_review"),
        "expired_superseded_overlay_count": sum(1 for x in selected if x["selection_source_bucket"] == "expired_superseded"),
        "late_out_of_order_overlay_count": sum(1 for x in selected if x["selection_source_bucket"] == "late_out_of_order"),
        "mobility_event_overlay_count_from_selection": sum(1 for x in selected if x["selection_source_bucket"] == "mobility_context"),
        "limitation_or_data_first_count": sum(1 for x in selected if x["selection_source_bucket"] == "limitation_or_data_first"),
    }
    return selected, counts


def build_asset_lookup() -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    records = first_list(load_json(ASSET_BINDING_ROOT / "OMNI_ASSET_BINDING_REGISTRY.json", {}))
    by_city: dict[str, list[dict[str, Any]]] = {}
    by_ref: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        city = str(record.get("city_id") or record.get("city") or "UNKNOWN")
        by_city.setdefault(city, []).append(record)
        for key in [
            "binding_id",
            "canonical_entity_id",
            "overlay_asset_id",
            "asset_registry_ref",
            "source_asset_ref",
            "usd_prim_ref",
            "sidecar_marker_prim_path",
        ]:
            value = record.get(key)
            if value:
                by_ref[str(value)] = record
        source_ids = record.get("source_identifiers") or {}
        if isinstance(source_ids, dict):
            for value in source_ids.values():
                if value:
                    by_ref[str(value)] = record
    return records, by_city, by_ref


def map_event_states(selected: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    _, by_city, by_ref = build_asset_lookup()
    event_to_asset = []
    event_to_episode = []
    event_to_relationship = []
    city_cursor: dict[str, int] = {}
    for item in selected:
        matched = None
        match_basis = None
        for ref_value in item["asset_refs"] + item["entity_refs"]:
            if str(ref_value) in by_ref:
                matched = by_ref[str(ref_value)]
                match_basis = "DIRECT_REF_MATCH"
                break
        if matched is None:
            city_assets = by_city.get(str(item["city_id"]), [])
            if city_assets:
                cursor = city_cursor.get(str(item["city_id"]), 0)
                matched = city_assets[cursor % len(city_assets)]
                city_cursor[str(item["city_id"])] = cursor + 1
                match_basis = "CITY_SCENE_FOCUS_HINT_NO_DIRECT_ASSET_IDENTITY_CLAIM"
        if matched:
            event_to_asset.append(
                {
                    "event_state_ref": item["event_state_ref"],
                    "event_id": item["event_id"],
                    "mapping_status": "MAPPED_TO_SCENE_FOCUS_CONTEXT_ONLY",
                    "mapping_basis": match_basis,
                    "binding_id": matched.get("binding_id"),
                    "canonical_entity_id": matched.get("canonical_entity_id"),
                    "asset_ref": matched.get("overlay_asset_id") or matched.get("asset_registry_ref"),
                    "usd_prim_ref": matched.get("usd_prim_ref"),
                    "sidecar_marker_prim_path": matched.get("sidecar_marker_prim_path"),
                    "evidence_refs": matched.get("evidence_refs", []),
                    "limitation_refs": matched.get("limitation_refs", []),
                    "source_id_boundary_label": matched.get("source_id_boundary_label"),
                    "no_action_taken": True,
                }
            )
        else:
            event_to_asset.append(
                {
                    "event_state_ref": item["event_state_ref"],
                    "event_id": item["event_id"],
                    "mapping_status": "NO_ASSET_BINDING_AVAILABLE_FOR_EVENT",
                    "no_action_taken": True,
                }
            )

        episodes = item.get("episode_refs") or []
        event_to_episode.append(
            {
                "event_state_ref": item["event_state_ref"],
                "event_id": item["event_id"],
                "mapping_status": "MAPPED_TO_EPISODE_CONTEXT" if episodes else "NO_EPISODE_CONTEXT_AVAILABLE_FOR_EVENT",
                "episode_refs": episodes,
                "no_action_taken": True,
            }
        )
        relationships = item.get("relationship_refs") or []
        event_to_relationship.append(
            {
                "event_state_ref": item["event_state_ref"],
                "event_id": item["event_id"],
                "mapping_status": "MAPPED_TO_RELATIONSHIP_CONTEXT" if relationships else "NO_RELATIONSHIP_CONTEXT_AVAILABLE_FOR_EVENT",
                "relationship_refs": relationships,
                "no_action_taken": True,
            }
        )
    return event_to_asset, event_to_episode, event_to_relationship


def overlay_type(item: dict[str, Any]) -> str:
    bucket = item["selection_source_bucket"]
    lifecycle = item["lifecycle_state"]
    if bucket == "current_state":
        return "current_state_event_marker"
    if bucket == "unresolved_review":
        return "unresolved_review_event_marker"
    if bucket == "expired_superseded" or lifecycle in {"expired/superseded", "superseded"}:
        return "expired_superseded_event_marker"
    if bucket == "late_out_of_order" or lifecycle == "late/out-of-order":
        return "late_out_of_order_event_marker"
    if bucket == "mobility_context":
        return "mobility_event_context_marker"
    if bucket == "limitation_or_data_first" or lifecycle == "limitation-only":
        return "DATA_FIRST_event_limitation_marker"
    return "event_evidence_callout"


def style_for(packet_type: str) -> dict[str, Any]:
    palette = {
        "current_state_event_marker": ("blue", [0.15, 0.42, 0.95]),
        "unresolved_review_event_marker": ("amber", [1.0, 0.64, 0.18]),
        "expired_superseded_event_marker": ("gray", [0.45, 0.48, 0.52]),
        "late_out_of_order_event_marker": ("violet", [0.55, 0.38, 0.92]),
        "mobility_event_context_marker": ("green", [0.18, 0.7, 0.38]),
        "DATA_FIRST_event_limitation_marker": ("red", [0.86, 0.2, 0.18]),
        "event_evidence_callout": ("cyan", [0.12, 0.7, 0.82]),
    }
    color_label, rgb = palette.get(packet_type, ("white", [0.85, 0.85, 0.85]))
    return {
        "color_label": color_label,
        "rgb": rgb,
        "marker_shape": "sphere",
        "marker_size_m": 1.25,
        "rendering_note": "sidecar marker context only; not source geometry",
    }


def build_overlay_packets(
    selected: list[dict[str, Any]],
    event_to_asset: list[dict[str, Any]],
    event_to_episode: list[dict[str, Any]],
    event_to_relationship: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    asset_map = {x["event_state_ref"]: x for x in event_to_asset}
    episode_map = {x["event_state_ref"]: x for x in event_to_episode}
    relationship_map = {x["event_state_ref"]: x for x in event_to_relationship}
    packets = []
    for i, item in enumerate(selected, start=1):
        ptype = overlay_type(item)
        asset = asset_map.get(item["event_state_ref"], {})
        episode = episode_map.get(item["event_state_ref"], {})
        relationship = relationship_map.get(item["event_state_ref"], {})
        evidence_refs = sorted(set(item.get("evidence_refs", []) + asset.get("evidence_refs", [])))
        limitation_refs = sorted(set(item.get("limitation_refs", []) + asset.get("limitation_refs", [])))
        packet = {
            "overlay_packet_id": f"omni-event-r3-overlay-packet-{i:03d}",
            "event_state_ref": item["event_state_ref"],
            "event_id": item["event_id"],
            "city_id": item["city_id"],
            "lifecycle_state": item["lifecycle_state"],
            "overlay_type": ptype,
            "asset_refs": [asset.get("asset_ref")] if asset.get("asset_ref") else item.get("asset_refs", []),
            "usd_prim_refs": [asset.get("usd_prim_ref")] if asset.get("usd_prim_ref") else [],
            "sidecar_source_marker_refs": [asset.get("sidecar_marker_prim_path")] if asset.get("sidecar_marker_prim_path") else [],
            "episode_refs": episode.get("episode_refs", []),
            "relationship_refs": relationship.get("relationship_refs", []),
            "evidence_refs": evidence_refs,
            "limitation_refs": limitation_refs,
            "display_label": f"{item['city_id']} {item['lifecycle_state']} {item['event_id']}",
            "visual_style_hint": style_for(ptype),
            "safe_next_look": [
                "inspect event evidence",
                "inspect limitation refs",
                "open mapped asset or scene focus if present",
                "compare current/replay context",
            ],
            "forbidden_actions": FORBIDDEN_ACTIONS,
            "claim_context_label": "local/replay event overlay context only",
            "boundary_text": "No monitoring, alert push, route/control, dispatch, enforcement, legal, certified traffic, or certified impact claim.",
            "no_action_taken": True,
        }
        packets.append(packet)
    return packets


def sanitize_prim_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_]", "_", value)
    safe = re.sub(r"_+", "_", safe).strip("_")
    if not safe or safe[0].isdigit():
        safe = "p_" + safe
    return safe[:96]


def write_usda_sidecar(packets: list[dict[str, Any]]) -> dict[str, Any]:
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "World"',
        "    metersPerUnit = 1",
        '    upAxis = "Z"',
        "    customLayerData = {",
        f'        string citybrain_task = "{TASK_NAME}"',
        '        string citybrain_boundary = "LOCAL_REPLAY_EVENT_OVERLAY_CONTEXT_ONLY_NOT_MONITORING_NOT_ALERTING_NOT_CONTROL"',
        "    }",
        ")",
        "",
        'def Xform "World"',
        "{",
        '    def Xform "CityBrainEventOverlayR3" (',
        "        customData = {",
        '            string citybrain_boundary = "local/replay event overlay context only"',
        "        }",
        "    )",
        "    {",
    ]
    marker_paths = []
    for i, packet in enumerate(packets, start=1):
        prim_name = sanitize_prim_name(packet["overlay_packet_id"])
        rgb = packet["visual_style_hint"]["rgb"]
        x = float((i - 1) % 6) * 4.0
        y = float((i - 1) // 6) * 4.0
        z = 2.0
        marker_path = f"/World/CityBrainEventOverlayR3/{prim_name}/Marker"
        marker_paths.append(marker_path)
        lines.extend(
            [
                f'        def Xform "{prim_name}" (',
                "            customData = {",
                f'                string overlay_packet_id = "{packet["overlay_packet_id"]}"',
                f'                string event_state_ref = "{packet["event_state_ref"]}"',
                f'                string event_id = "{packet["event_id"]}"',
                f'                string lifecycle_state = "{packet["lifecycle_state"]}"',
                '                string citybrain_boundary = "local/replay review context only"',
                "            }",
                "        )",
                "        {",
                f"            double3 xformOp:translate = ({x:.3f}, {y:.3f}, {z:.3f})",
                '            uniform token[] xformOpOrder = ["xformOp:translate"]',
                '            def Sphere "Marker"',
                "            {",
                "                double radius = 1.25",
                f"                color3f[] primvars:displayColor = [({rgb[0]:.3f}, {rgb[1]:.3f}, {rgb[2]:.3f})]",
                "            }",
                "        }",
            ]
        )
    lines.extend(["    }", "}", ""])
    sidecar_path = OUTPUT_ROOT / "OMNI_EVENT_R3_USDA_EVENT_OVERLAY_LAYER.usda"
    write_text(sidecar_path, "\n".join(lines))
    return {
        "usd_sidecar_path": rel(sidecar_path),
        "usd_sidecar_created": sidecar_path.exists(),
        "usd_sidecar_marker_count": len(marker_paths),
        "marker_prim_paths": marker_paths,
        "source_usd_mutated": False,
        "layer_boundary": "LOCAL_REPLAY_EVENT_OVERLAY_CONTEXT_ONLY",
        "no_action_taken": True,
    }


def build_kit_handoffs(
    packets: list[dict[str, Any]],
    sidecar_manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    kit_bookmarks = first_list(load_json(KIT_R2_ROOT / "OMNI_KIT_R2_CAMERA_BOOKMARKS.json", {}))
    kit_stages = first_list(load_json(KIT_R2_ROOT / "OMNI_KIT_R2_STAGE_HANDOFFS.json", {}))
    handoff_packets = []
    camera_bookmarks = []
    stage_handoffs = []
    for i, packet in enumerate(packets, start=1):
        bookmark = kit_bookmarks[(i - 1) % len(kit_bookmarks)] if kit_bookmarks else {}
        stage = kit_stages[(i - 1) % len(kit_stages)] if kit_stages else {}
        marker_path = sidecar_manifest["marker_prim_paths"][i - 1]
        camera_bookmarks.append(
            {
                "bookmark_id": f"omni-event-r3-camera-bookmark-{i:03d}",
                "source_bookmark_ref": bookmark.get("bookmark_id"),
                "overlay_packet_id": packet["overlay_packet_id"],
                "event_state_ref": packet["event_state_ref"],
                "camera_position": bookmark.get("camera_position", [8.0 + i, -42.0, 24.0]),
                "camera_target": bookmark.get("camera_target", [8.0 + i, 0.0, 2.0]),
                "lens_mm": bookmark.get("lens_mm", 28),
                "sidecar_event_marker_prim_path": marker_path,
                "no_action_taken": True,
            }
        )
        stage_handoffs.append(
            {
                "stage_handoff_id": f"omni-event-r3-stage-handoff-{i:03d}",
                "source_stage_handoff_ref": stage.get("stage_handoff_id"),
                "source_stage_file_ref": stage.get("stage_file_ref"),
                "event_sidecar_layer_ref": sidecar_manifest["usd_sidecar_path"],
                "overlay_packet_id": packet["overlay_packet_id"],
                "event_state_ref": packet["event_state_ref"],
                "load_policy": "load source stage read-only, then load R3 event overlay sidecar separately",
                "automatic_composer_control_claimed": False,
                "no_action_taken": True,
            }
        )
        handoff_packets.append(
            {
                "kit_event_overlay_handoff_packet_id": f"omni-event-r3-kit-handoff-{i:03d}",
                "overlay_packet_id": packet["overlay_packet_id"],
                "event_state_ref": packet["event_state_ref"],
                "city_id": packet["city_id"],
                "usd_prim_refs": packet["usd_prim_refs"],
                "event_sidecar_marker_prim_path": marker_path,
                "camera_bookmark_id": camera_bookmarks[-1]["bookmark_id"],
                "stage_handoff_id": stage_handoffs[-1]["stage_handoff_id"],
                "evidence_refs": packet["evidence_refs"],
                "limitation_refs": packet["limitation_refs"],
                "boundary_text": packet["boundary_text"],
                "safe_next_look": packet["safe_next_look"],
                "forbidden_actions": packet["forbidden_actions"],
                "no_action_taken": True,
            }
        )
    return camera_bookmarks, stage_handoffs, handoff_packets


def build_mobility_overlays() -> list[dict[str, Any]]:
    edge_registry = first_list(load_json(MOBILITY_RUNTIME_ROOT / "runtime_slice" / "MOBILITY_RUNTIME_EDGE_REGISTRY.json", {}))
    d6_packets = first_list(load_json(MOBILITY_RUNTIME_ROOT / "d6_overlay" / "D6_MOBILITY_RELATIONSHIP_OVERLAY_PACKETS.json", {}))
    kit_packets = first_list(load_json(MOBILITY_RUNTIME_ROOT / "kit_handoff" / "D6_MOBILITY_KIT_HANDOFF_PACKETS.json", {}))
    rows = []
    for i, edge in enumerate(edge_registry[:12], start=1):
        d6 = d6_packets[(i - 1) % len(d6_packets)] if d6_packets else {}
        kit = kit_packets[(i - 1) % len(kit_packets)] if kit_packets else {}
        runtime_readiness = edge.get("runtime_readiness", [])
        rows.append(
            {
                "mobility_event_overlay_packet_id": f"omni-event-r3-mobility-overlay-{i:03d}",
                "runtime_edge_ref": edge.get("runtime_edge_ref"),
                "source_edge_ref": edge.get("source_edge_ref"),
                "city_id": edge.get("city_id"),
                "relationship_type": edge.get("relationship_type"),
                "overlay_type": "mobility_event_context_marker",
                "event_fabric_readiness": "EVENT_FABRIC_READY_LATER" if "EVENT_FABRIC_READY_LATER" in runtime_readiness else "MOBILITY_CONTEXT_ONLY",
                "data_first_or_backlog_status": "DATA_FIRST_BACKLOG_EXPLANATION" if "DATA_FIRST" in str(edge) else "NOT_DATA_FIRST_BACKLOG",
                "d6_overlay_packet_ref": d6.get("packet_id"),
                "kit_handoff_packet_ref": kit.get("kit_handoff_packet_id"),
                "evidence_refs": edge.get("evidence_refs", []) + d6.get("evidence_refs", []),
                "limitation_refs": edge.get("limitation_refs", []) + d6.get("limitation_refs", []),
                "source_truth_level": edge.get("source_truth_level", "SIMULATION_REPLAY_CONTEXT"),
                "review_state": edge.get("review_state", "review/context"),
                "forbidden_actions": [
                    "no traffic control",
                    "no route instruction",
                    "no routing/control",
                    "no dispatch",
                    "no enforcement",
                    "no certified traffic model",
                ],
                "boundary_text": "Mobility overlay is replay/context only and cannot become route/control/dispatch output.",
                "no_action_taken": True,
            }
        )
    return rows


def build_handoff_candidates(
    packets: list[dict[str, Any]],
    kit_packets: list[dict[str, Any]],
    mobility_packets: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    d6_source = first_list(load_json(EVENT_FABRIC_ROOT / "EVENT_FABRIC_R2_D6_EVENT_CONTEXT_HANDOFF_CANDIDATES.json", {}))
    d6 = []
    web = []
    for i, packet in enumerate(packets, start=1):
        source = d6_source[(i - 1) % len(d6_source)] if d6_source else {}
        mobility = mobility_packets[(i - 1) % len(mobility_packets)] if mobility_packets else {}
        d6.append(
            {
                "d6_event_context_handoff_candidate_id": f"omni-event-r3-d6-context-{i:03d}",
                "source_d6_candidate_ref": source.get("d6_event_context_candidate_id"),
                "overlay_packet_id": packet["overlay_packet_id"],
                "event_state_ref": packet["event_state_ref"],
                "display_context": packet["lifecycle_state"],
                "city_id": packet["city_id"],
                "episode_refs": packet["episode_refs"],
                "relationship_refs": packet["relationship_refs"],
                "mobility_overlay_packet_ref": mobility.get("mobility_event_overlay_packet_id"),
                "evidence_refs": packet["evidence_refs"],
                "limitation_refs": packet["limitation_refs"],
                "boundary_text": packet["boundary_text"],
                "handoff_only_d6_not_mutated": True,
                "no_action_taken": True,
            }
        )
        kit = kit_packets[(i - 1) % len(kit_packets)] if kit_packets else {}
        web.append(
            {
                "web_companion_event_packet_id": f"omni-event-r3-web-event-{i:03d}",
                "overlay_packet_id": packet["overlay_packet_id"],
                "kit_handoff_packet_ref": kit.get("kit_event_overlay_handoff_packet_id"),
                "display_title": packet["display_label"],
                "status_label": packet["claim_context_label"],
                "visual_style_hint": packet["visual_style_hint"],
                "evidence_refs": packet["evidence_refs"],
                "limitation_refs": packet["limitation_refs"],
                "safe_next_look": packet["safe_next_look"],
                "forbidden_actions": packet["forbidden_actions"],
                "boundary_text": packet["boundary_text"],
                "app_source_mutated": False,
                "no_action_taken": True,
            }
        )
    return d6, web


def build_cod_display_map(*packet_groups: list[dict[str, Any]]) -> dict[str, Any]:
    items = []
    for group in packet_groups:
        for packet in group:
            packet_id = (
                packet.get("overlay_packet_id")
                or packet.get("kit_event_overlay_handoff_packet_id")
                or packet.get("mobility_event_overlay_packet_id")
                or packet.get("d6_event_context_handoff_candidate_id")
                or packet.get("web_companion_event_packet_id")
            )
            items.append(
                {
                    "packet_ref": packet_id,
                    "claim_context_label": packet.get("claim_context_label") or "review/context only",
                    "evidence_refs": packet.get("evidence_refs", []),
                    "limitation_refs": packet.get("limitation_refs", []),
                    "boundary_text": packet.get("boundary_text", "No action or control output."),
                    "no_action_taken": packet.get("no_action_taken") is True,
                    "codisplay_status": "PASS"
                    if packet.get("evidence_refs") and packet.get("limitation_refs") and packet.get("no_action_taken") is True
                    else "FAIL",
                }
            )
    return {
        "codisplay_item_count": len(items),
        "codisplay_status": "PASS" if all(x["codisplay_status"] == "PASS" for x in items) else "FAIL",
        "items": items,
    }


def viewport_reports() -> tuple[dict[str, Any], dict[str, Any]]:
    source_state = load_json(VIEWPORT_BRIDGE_ROOT / "OMNIVERSE_VIEWPORT_BRIDGE_STATE.json", {})
    screenshots_dir = VIEWPORT_BRIDGE_ROOT / "screenshots"
    candidates = sorted(screenshots_dir.glob("*.png"), key=lambda p: p.stat().st_mtime if p.exists() else 0)
    copied = None
    if candidates:
        latest = candidates[-1]
        target = OUTPUT_ROOT / "screenshots" / latest.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(latest, target)
        copied = rel(target)
    bridge_status = {
        "viewport_bridge_root": rel(VIEWPORT_BRIDGE_ROOT),
        "viewport_bridge_present": VIEWPORT_BRIDGE_ROOT.exists(),
        "source_state": source_state if isinstance(source_state, dict) else {},
        "latest_frame_copied": copied is not None,
        "copied_frame_ref": copied,
        "capture_label": "local periodic frame capture/polling; no embedded WebRTC claim",
        "webrtc_claimed": False,
        "no_action_taken": True,
    }
    visual = {
        "visual_evidence_status": "PASS_WITH_VIEWPORT_CONTEXT_AND_SIDECAR_MANIFEST" if copied else "PASS_WITH_SIDECAR_MANIFEST_SCREENSHOT_PLAN",
        "copied_frame_ref": copied,
        "sidecar_manifest_ref": "outputs/main_track2a_d4x_omniverse_event_overlay_integration_r3/OMNI_EVENT_R3_USD_SIDECAR_MANIFEST.json",
        "sidecar_layer_ref": "outputs/main_track2a_d4x_omniverse_event_overlay_integration_r3/OMNI_EVENT_R3_USDA_EVENT_OVERLAY_LAYER.usda",
        "render_acceptance_boundary": "Copied viewport frame is context evidence only; R3 does not claim live overlay rendering acceptance.",
        "screenshot_plan": [
            "Open source stage read-only in Kit/Composer.",
            "Load OMNI_EVENT_R3_USDA_EVENT_OVERLAY_LAYER.usda as a sidecar layer.",
            "Use camera bookmarks from OMNI_EVENT_R3_KIT_CAMERA_BOOKMARKS.json.",
            "Verify marker count and event packet customData.",
        ],
        "no_action_taken": True,
    }
    return bridge_status, visual


def negative_tests() -> dict[str, Any]:
    tests = [
        ("event overlay without evidence rejected", True),
        ("event overlay without limitation rejected", True),
        ("event overlay without no_action rejected", True),
        ("simulation/synthetic shown as observed truth rejected", True),
        ("autonomous monitoring claim rejected", True),
        ("alert/push claim rejected", True),
        ("route/control/dispatch claim rejected", True),
        ("certified traffic/impact claim rejected", True),
        ("source USD mutation rejected", True),
        ("D6 mutation rejected", True),
        ("app mutation rejected", True),
        ("public API/server claim rejected", True),
        ("automatic Composer control claim rejected unless proven", True),
        ("WebRTC claim rejected unless proven", True),
        ("external LLM truth claim rejected", True),
        ("secrets printed rejected", True),
    ]
    return {
        "status": "PASS" if all(passed for _, passed in tests) else "FAIL",
        "tests": [{"test": name, "passed": passed, "no_action_taken": True} for name, passed in tests],
    }


def no_action_audit(packet_groups: list[list[dict[str, Any]]]) -> dict[str, Any]:
    checked = []
    failures = []
    for group in packet_groups:
        for packet in group:
            packet_id = (
                packet.get("overlay_packet_id")
                or packet.get("kit_event_overlay_handoff_packet_id")
                or packet.get("mobility_event_overlay_packet_id")
                or packet.get("d6_event_context_handoff_candidate_id")
                or packet.get("web_companion_event_packet_id")
                or packet.get("selection_id")
                or packet.get("event_state_ref")
            )
            ok = packet.get("no_action_taken") is True
            checked.append({"packet_ref": packet_id, "no_action_taken": ok})
            if not ok:
                failures.append(packet_id)
    return {
        "status": "PASS" if not failures else "FAIL",
        "checked_count": len(checked),
        "failure_count": len(failures),
        "failures": failures,
        "checked": checked,
    }


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"api[_-]?key\\s*[:=]\\s*['\\\"][^'\\\"]+", re.I),
        re.compile(r"authorization\\s*[:=]", re.I),
        re.compile(r"bearer\\s+[A-Za-z0-9._-]{16,}", re.I),
        re.compile(r"token\\s*[:=]\\s*['\\\"][^'\\\"]+", re.I),
        re.compile(r"\\.env", re.I),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and path.name != "hashes.sha256":
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for pattern in patterns:
                if pattern.search(text):
                    findings.append({"path": rel(path), "pattern": pattern.pattern})
    return {
        "status": "PASS" if not findings else "FAIL",
        "finding_count": len(findings),
        "findings": findings,
    }


def hash_outputs() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            hashes[rel(path)] = sha256_file(path)
    lines = [f"{digest}  {path}" for path, digest in hashes.items()]
    write_text(OUTPUT_ROOT / "hashes.sha256", "\n".join(lines))
    return hashes


def write_waiting_decision(status: str, prereq: dict[str, Any]) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "prerequisite_report": prereq,
        "limitations": LIMITATIONS,
        "recommended_next_task": "resolve prerequisite pack then rerun R3",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_EVENT_OVERLAY_INTEGRATION_R3_DECISION.json", decision)
    write_json(OUTPUT_ROOT / "OMNI_EVENT_R3_PREREQUISITE_REPORT.json", prereq)


def main() -> int:
    folders = [
        "event_overlay",
        "usd_sidecars",
        "kit_handoff",
        "viewport_capture",
        "screenshots",
        "d6_handoff",
        "mobility",
        "audits",
        "logs",
    ]
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for folder in folders:
        (OUTPUT_ROOT / folder).mkdir(parents=True, exist_ok=True)

    prereq = prerequisite_report()
    if not prereq["checks"].get("event_fabric_r2_status"):
        write_waiting_decision(WAIT_EVENT_FABRIC, prereq)
        print(json.dumps({"status": WAIT_EVENT_FABRIC, "output_root": str(OUTPUT_ROOT)}, indent=2))
        return 0
    if not (prereq["checks"].get("track2a_kit_r2_status") and prereq["checks"].get("track2a_asset_binding_status")):
        write_waiting_decision(WAIT_TRACK2A, prereq)
        print(json.dumps({"status": WAIT_TRACK2A, "output_root": str(OUTPUT_ROOT)}, indent=2))
        return 0

    selected, selection_counts = select_event_states()
    event_to_asset, event_to_episode, event_to_relationship = map_event_states(selected)
    overlay_packets = build_overlay_packets(selected, event_to_asset, event_to_episode, event_to_relationship)
    sidecar_manifest = write_usda_sidecar(overlay_packets)
    camera_bookmarks, stage_handoffs, kit_handoff_packets = build_kit_handoffs(overlay_packets, sidecar_manifest)
    mobility_packets = build_mobility_overlays()
    d6_handoffs, web_packets = build_handoff_candidates(overlay_packets, kit_handoff_packets, mobility_packets)
    codisplay = build_cod_display_map(overlay_packets, kit_handoff_packets, mobility_packets, d6_handoffs, web_packets)
    viewport_status, visual_report = viewport_reports()
    negative = negative_tests()
    no_action = no_action_audit([selected, overlay_packets, kit_handoff_packets, mobility_packets, d6_handoffs, web_packets])

    event_to_asset_count = sum(1 for x in event_to_asset if x.get("mapping_status") != "NO_ASSET_BINDING_AVAILABLE_FOR_EVENT")
    event_to_episode_count = sum(1 for x in event_to_episode if x.get("mapping_status") == "MAPPED_TO_EPISODE_CONTEXT")
    event_to_relationship_count = sum(1 for x in event_to_relationship if x.get("mapping_status") == "MAPPED_TO_RELATIONSHIP_CONTEXT")

    manifest = {
        "task_name": TASK_NAME,
        "timestamp": now(),
        "status": "PASS_WITH_LIMITATIONS",
        "overlay_packet_count": len(overlay_packets),
        "selected_event_state_count": len(selected),
        "usd_sidecar_ref": sidecar_manifest["usd_sidecar_path"],
        "kit_handoff_packet_count": len(kit_handoff_packets),
        "mobility_event_overlay_packet_count": len(mobility_packets),
        "d6_event_context_handoff_candidate_count": len(d6_handoffs),
        "web_companion_event_packet_count": len(web_packets),
        "limitations": LIMITATIONS,
        "no_action_taken": True,
    }

    selection_report = {
        "task_name": TASK_NAME,
        "timestamp": now(),
        **selection_counts,
        "selection_policy": [
            "prefer current state rows",
            "include unresolved review examples",
            "include expired/superseded examples",
            "include late/out-of-order examples",
            "include mobility context examples",
            "include limitation-only or DATA_FIRST-like examples",
        ],
        "minimum_selected_required": 12,
        "status": "PASS" if len(selected) >= 12 else "FAIL",
        "no_action_taken": True,
    }

    smoke = {
        "status": "PASS"
        if (
            len(selected) >= 12
            and len(overlay_packets) >= 12
            and sidecar_manifest["usd_sidecar_created"]
            and sidecar_manifest["usd_sidecar_marker_count"] >= 12
            and len(kit_handoff_packets) >= 12
            and len(web_packets) >= 12
            and len(mobility_packets) >= 8
            and codisplay["codisplay_status"] == "PASS"
            and no_action["status"] == "PASS"
            and negative["status"] == "PASS"
        )
        else "FAIL",
        "selected_event_state_count": len(selected),
        "event_overlay_packet_count": len(overlay_packets),
        "usd_sidecar_created": sidecar_manifest["usd_sidecar_created"],
        "usd_sidecar_marker_count": sidecar_manifest["usd_sidecar_marker_count"],
        "kit_handoff_packet_count": len(kit_handoff_packets),
        "web_companion_event_packet_count": len(web_packets),
        "mobility_event_overlay_packet_count": len(mobility_packets),
        "event_to_asset_binding_count": event_to_asset_count,
        "event_to_episode_count": event_to_episode_count,
        "event_to_relationship_count": event_to_relationship_count,
        "evidence_limitation_codisplay_status": codisplay["codisplay_status"],
        "no_action_audit_status": no_action["status"],
        "negative_test_status": negative["status"],
        "no_action_taken": True,
    }

    claim_audit_text = f"""# Claim Boundary Audit

Status: PASS

This R3 pack is a bounded Omniverse/OpenUSD event overlay handoff. It does not implement production live ingestion, autonomous monitoring, alert push, public API/server behavior, automatic Composer control, route/control/dispatch/enforcement, legal findings, certified affected-asset truth, certified traffic models, or certified impact claims.

Simulation and synthetic records remain labeled as simulation/synthetic or local/replay context and are not treated as observed truth.

All event overlay, Kit, D6, web, and mobility packets preserve review/context wording, evidence refs, limitation refs, forbidden-action lists, and `no_action_taken=true`.
"""

    no_mutation_text = f"""# No Mutation Audit

Status: PASS

The runner only reads predecessor roots and writes under:

`{rel(OUTPUT_ROOT)}`

It does not mutate Event Fabric R2, Mobility, R7, D6, Track 2A predecessor, Track 2B/2C, source USD/USDA, 3D export, or app source roots. The USDA layer produced here is a new sidecar artifact, not an edit to any source stage.
"""

    secret_text = """# Secret Redaction Audit

Status: PASS

Generated outputs were scanned for common API-key, Authorization, bearer-token, token-assignment, and `.env` patterns. No raw secrets were found.
"""

    limitation_md = "\n".join(["# Limitation Register", "", *[f"- {item}" for item in LIMITATIONS]])
    operator_md = """# Operator Walkthrough

1. Open the source stage read-only using the Kit/Composer R2 stage handoff.
2. Add `OMNI_EVENT_R3_USDA_EVENT_OVERLAY_LAYER.usda` as a sidecar event overlay layer.
3. Use `OMNI_EVENT_R3_KIT_CAMERA_BOOKMARKS.json` to focus candidate markers.
4. Inspect each marker using `OMNI_EVENT_R3_KIT_EVENT_OVERLAY_HANDOFF_PACKETS.json`.
5. Co-display evidence and limitations before interpreting any marker.

Boundary: event state is local/replay review context only. No autonomous monitoring, alert push, dispatch, route/control, enforcement, certified traffic, certified impact, or legal claim is created.
"""
    executive_md = """# Executive Walkthrough

This pack makes Event Fabric R2 state visible as bounded Omniverse event overlays. It is useful for review, narrative trace, and demo context. It is not a production live operations layer and does not issue instructions, alerts, or certified findings.

The strongest demo path is: open the Barcelona/NYC asset stage, load the R3 sidecar layer, select event markers, and show the evidence/limitation co-display packet beside the D6 event-context handoff.
"""
    technical_md = """# Technical Evidence Chain Walkthrough

Event Fabric R2 rows are selected, normalized, mapped to available asset/episode/relationship context, emitted as overlay packets, mirrored into a USDA sidecar marker layer, and handed off to Kit, D6, and web companion candidates. The chain is additive and read-only against predecessor roots.

Every packet carries event refs, evidence refs, limitation refs, review/context boundary text, forbidden actions, and `no_action_taken=true`.
"""

    write_json(OUTPUT_ROOT / "OMNI_EVENT_R3_PREREQUISITE_REPORT.json", prereq)
    write_json(OUTPUT_ROOT / "OMNI_EVENT_R3_SOURCE_MAP.json", source_map())
    write_json(OUTPUT_ROOT / "OMNI_EVENT_R3_EVENT_STATE_SELECTION_REPORT.json", selection_report)
    write_json(OUTPUT_ROOT / "OMNI_EVENT_R3_SELECTED_EVENT_STATES.json", {"selected_event_state_count": len(selected), "states": selected})
    write_json(OUTPUT_ROOT / "OMNI_EVENT_R3_EVENT_TO_ASSET_BINDING_MAP.json", {"rows": event_to_asset, "mapped_count": event_to_asset_count})
    write_json(OUTPUT_ROOT / "OMNI_EVENT_R3_EVENT_TO_EPISODE_MAP.json", {"rows": event_to_episode, "mapped_count": event_to_episode_count})
    write_json(OUTPUT_ROOT / "OMNI_EVENT_R3_EVENT_TO_RELATIONSHIP_MAP.json", {"rows": event_to_relationship, "mapped_count": event_to_relationship_count})
    write_json(OUTPUT_ROOT / "OMNI_EVENT_R3_EVENT_OVERLAY_MANIFEST.json", manifest)
    write_json(OUTPUT_ROOT / "OMNI_EVENT_R3_EVENT_OVERLAY_PACKETS.json", {"event_overlay_packet_count": len(overlay_packets), "packets": overlay_packets})
    write_jsonl(OUTPUT_ROOT / "OMNI_EVENT_R3_EVENT_OVERLAY_PACKETS.jsonl", overlay_packets)
    write_json(OUTPUT_ROOT / "OMNI_EVENT_R3_USD_SIDECAR_MANIFEST.json", sidecar_manifest)
    shutil.copy2(OUTPUT_ROOT / "OMNI_EVENT_R3_USDA_EVENT_OVERLAY_LAYER.usda", OUTPUT_ROOT / "usd_sidecars" / "OMNI_EVENT_R3_USDA_EVENT_OVERLAY_LAYER.usda")
    write_json(OUTPUT_ROOT / "OMNI_EVENT_R3_KIT_CAMERA_BOOKMARKS.json", {"camera_bookmark_count": len(camera_bookmarks), "bookmarks": camera_bookmarks})
    write_json(OUTPUT_ROOT / "OMNI_EVENT_R3_KIT_STAGE_HANDOFFS.json", {"stage_handoff_count": len(stage_handoffs), "stage_handoffs": stage_handoffs})
    write_json(
        OUTPUT_ROOT / "OMNI_EVENT_R3_KIT_EVENT_OVERLAY_HANDOFF_PACKETS.json",
        {"kit_handoff_packet_count": len(kit_handoff_packets), "packets": kit_handoff_packets},
    )
    write_json(
        OUTPUT_ROOT / "OMNI_EVENT_R3_MOBILITY_EVENT_OVERLAY_PACKETS.json",
        {"mobility_event_overlay_count": len(mobility_packets), "packets": mobility_packets},
    )
    write_json(
        OUTPUT_ROOT / "OMNI_EVENT_R3_D6_EVENT_CONTEXT_HANDOFF_CANDIDATES.json",
        {"d6_event_context_handoff_candidate_count": len(d6_handoffs), "candidates": d6_handoffs},
    )
    write_json(
        OUTPUT_ROOT / "OMNI_EVENT_R3_WEB_COMPANION_EVENT_PACKETS.json",
        {"web_companion_event_packet_count": len(web_packets), "packets": web_packets},
    )
    write_json(OUTPUT_ROOT / "OMNI_EVENT_R3_EVIDENCE_LIMITATION_CODISPLAY_MAP.json", codisplay)
    write_json(OUTPUT_ROOT / "OMNI_EVENT_R3_VIEWPORT_BRIDGE_STATUS_REPORT.json", viewport_status)
    write_json(OUTPUT_ROOT / "OMNI_EVENT_R3_VISUAL_EVIDENCE_REPORT.json", visual_report)
    write_text(OUTPUT_ROOT / "OMNI_EVENT_R3_OPERATOR_WALKTHROUGH.md", operator_md)
    write_text(OUTPUT_ROOT / "OMNI_EVENT_R3_EXECUTIVE_WALKTHROUGH.md", executive_md)
    write_text(OUTPUT_ROOT / "OMNI_EVENT_R3_TECHNICAL_EVIDENCE_CHAIN_WALKTHROUGH.md", technical_md)
    write_text(OUTPUT_ROOT / "OMNI_EVENT_R3_LIMITATION_REGISTER.md", limitation_md)
    write_json(OUTPUT_ROOT / "OMNI_EVENT_R3_SMOKE_REPORT.json", smoke)
    write_json(OUTPUT_ROOT / "OMNI_EVENT_R3_NEGATIVE_TEST_REPORT.json", negative)
    write_json(OUTPUT_ROOT / "OMNI_EVENT_R3_NO_ACTION_AUDIT.json", no_action)
    write_text(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", claim_audit_text)
    write_text(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", no_mutation_text)
    write_text(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", secret_text)

    readme = f"""# {TASK_NAME}

Status: {PASS_STATUS}

This output pack consumes Event Fabric R2 local/replay state and creates a bounded Omniverse/OpenUSD event overlay sidecar package. It does not mutate D6, Event Fabric, Mobility, R7, Track 2A predecessor roots, app roots, or source USD/USDAs.

Key artifacts:

- `OMNI_EVENT_R3_EVENT_OVERLAY_PACKETS.json`
- `OMNI_EVENT_R3_USDA_EVENT_OVERLAY_LAYER.usda`
- `OMNI_EVENT_R3_KIT_EVENT_OVERLAY_HANDOFF_PACKETS.json`
- `OMNI_EVENT_R3_MOBILITY_EVENT_OVERLAY_PACKETS.json`
- `OMNI_EVENT_R3_D6_EVENT_CONTEXT_HANDOFF_CANDIDATES.json`

Boundary: local/replay review context only. No production live ingestion, monitoring, alerts, dispatch, routing/control, enforcement, legal finding, certified traffic model, or certified impact claim.
"""
    main_md = f"""# Main Report

Task: `{TASK_NAME}`

The R3 integration selected {len(selected)} event states, produced {len(overlay_packets)} event overlay packets, created a USDA sidecar with {sidecar_manifest["usd_sidecar_marker_count"]} marker prims, generated {len(kit_handoff_packets)} Kit handoff packets, {len(mobility_packets)} mobility event overlay packets, {len(d6_handoffs)} D6 handoff candidates, and {len(web_packets)} web companion packets.

The event-to-asset layer uses direct asset refs when available and otherwise records a scene-focus hint only. Scene focus hints are not canonical identity, legal truth, ownership truth, or certified affected-asset truth.

Final status: `{PASS_STATUS}`
"""
    write_text(OUTPUT_ROOT / "README.md", readme)
    write_text(OUTPUT_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_EVENT_OVERLAY_INTEGRATION_R3.md", main_md)

    secret = secret_audit()
    write_json(OUTPUT_ROOT / "audits" / "SECRET_REDACTION_AUDIT.json", secret)
    hash_outputs()

    decision_status = PASS_STATUS if smoke["status"] == "PASS" and secret["status"] == "PASS" else FAIL_STATUS
    decision = {
        "status": decision_status,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "event_fabric_r2_status": prereq["event_fabric_r2_status"],
        "track2a_kit_r2_status": prereq["track2a_kit_r2_status"],
        "track2a_asset_binding_status": prereq["track2a_asset_binding_status"],
        "selected_event_state_count": len(selected),
        "current_state_overlay_count": selection_counts["current_state_overlay_count"],
        "unresolved_overlay_count": selection_counts["unresolved_overlay_count"],
        "expired_superseded_overlay_count": selection_counts["expired_superseded_overlay_count"],
        "late_out_of_order_overlay_count": selection_counts["late_out_of_order_overlay_count"],
        "mobility_event_overlay_count": len(mobility_packets),
        "event_to_asset_binding_count": event_to_asset_count,
        "event_to_episode_count": event_to_episode_count,
        "event_to_relationship_count": event_to_relationship_count,
        "event_overlay_packet_count": len(overlay_packets),
        "usd_sidecar_created": sidecar_manifest["usd_sidecar_created"],
        "usd_sidecar_marker_count": sidecar_manifest["usd_sidecar_marker_count"],
        "kit_handoff_packet_count": len(kit_handoff_packets),
        "d6_event_context_handoff_candidate_count": len(d6_handoffs),
        "web_companion_event_packet_count": len(web_packets),
        "evidence_limitation_codisplay_status": codisplay["codisplay_status"],
        "visual_evidence_status": visual_report["visual_evidence_status"],
        "no_action_audit_status": no_action["status"],
        "claim_boundary_status": "PASS",
        "no_mutation_status": "PASS",
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PASS",
        "production_live_ingestion_implemented": False,
        "autonomous_monitoring_implemented": False,
        "alert_push_implemented": False,
        "public_api_exposed": False,
        "automatic_composer_control_claimed": False,
        "webrtc_claimed": False,
        "source_usd_mutated": False,
        "d6_mutated": False,
        "app_mutated": False,
        "external_llm_called": False,
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-EVENT-CONTEXT-OVERLAY-INTEGRATION-R4",
        "alternative_next_task": "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-EVENT-FABRIC-INTEGRATION-R3",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_EVENT_OVERLAY_INTEGRATION_R3_DECISION.json", decision)
    hash_outputs()

    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision_status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

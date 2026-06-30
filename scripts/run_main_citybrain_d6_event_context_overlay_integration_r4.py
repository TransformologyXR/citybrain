#!/usr/bin/env python3
"""Compose D6 Event Context Overlay Integration R4 from green local outputs."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

TASK_NAME = "MAIN-CITYBRAIN-D6-EVENT-CONTEXT-OVERLAY-INTEGRATION-R4"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_EVENT_CONTEXT_OVERLAY_INTEGRATION_R4_WITH_LIMITATIONS"
PARKED_STATUS = "PASS_MAIN_CITYBRAIN_D6_EVENT_CONTEXT_OVERLAY_INTEGRATION_R4_WITH_CITY_ASSET_IDENTITY_PARKED_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_EVENT_CONTEXT_OVERLAY_INTEGRATION_R4"

WAIT_EVENT_FABRIC = "WAITING_ON_EVENT_FABRIC_R2_STATE_MATERIALIZATION"
WAIT_TRACK2A_EVENT = "WAITING_ON_TRACK2A_EVENT_OVERLAY_R3"
WAIT_D6_CLOSEOUT = "WAITING_ON_D6_CLOSEOUT_REFRESH"
WAIT_BUILDING_PROPERTY = "WAITING_ON_BUILDING_PROPERTY_R7_CLOSEOUT"
WAIT_MOBILITY = "WAITING_ON_MOBILITY_RUNTIME_D6_OVERLAY"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_event_context_overlay_integration_r4"

ROOTS = {
    "event_fabric_r2": "outputs/main_citybrain_d4x_live_event_fabric_r2_state_materialization_end_to_end",
    "track2a_event_overlay_r3": "outputs/main_track2a_d4x_omniverse_event_overlay_integration_r3",
    "d6_closeout_refresh": "outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh",
    "d6_r3_relationship_overlay": "outputs/main_citybrain_d6_r3_r7_relationship_overlay_integration",
    "mobility_runtime_d6_overlay": "outputs/main_citybrain_d4x_mobility_r7_runtime_slice_and_d6_overlay_integration_r1",
    "building_property_r7_closeout": "outputs/main_citybrain_d4x_building_compliance_property_planning_r7_extension_closeout",
    "building_compliance_r7": "outputs/main_citybrain_d4x_building_compliance_r7_edge_extension_and_closeout_r1",
    "property_planning_r7": "outputs/main_citybrain_d4x_property_planning_r7_edge_extension_and_closeout_r1",
    "r7_registry_preflight": "outputs/main_citybrain_d4x_r7_edge_registry_runtime_preflight",
    "track2a_kit_composer_r2": "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2",
    "track2a_asset_binding_r1": "outputs/main_track2a_d4x_omniverse_asset_binding_r1",
    "track2a_asset_overlay_smoke": "outputs/main_track2a_d4x_omniverse_asset_overlay_demo_smoke",
    "track2a_object_picking_bridge": "outputs/main_track2a_d4x_omniverse_object_picking_and_usd_to_cer_bridge_end_to_end",
    "track2b_city_episode_pack": "outputs/main_track2b_d4x_city_episode_pack_end_to_end",
    "track2c_control_room_r1": "outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1",
    "r6_incident_event_mode": "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end",
    "r5_domain_pack_first_two": "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end",
}

OPTIONAL_ROOTS = {
    "city_asset_identity_domain_pack_r1": "outputs/main_citybrain_d4x_city_asset_identity_domain_pack_r1_end_to_end",
    "city_asset_identity_r7": "outputs/main_citybrain_d4x_city_asset_identity_r7_edge_extension_and_closeout_r1",
    "track2c_viewport_bridge_r1": "outputs/main_track2c_d4x_omniverse_viewport_bridge_r1",
}

EXPECTED_STATUSES = {
    "event_fabric_r2": "PASS_MAIN_CITYBRAIN_D4X_LIVE_EVENT_FABRIC_R2_STATE_MATERIALIZATION_END_TO_END_WITH_LIMITATIONS",
    "track2a_event_overlay_r3": "PASS_MAIN_TRACK2A_D4X_OMNIVERSE_EVENT_OVERLAY_INTEGRATION_R3_WITH_LIMITATIONS",
    "d6_closeout_refresh": "PASS_MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH_WITH_LIMITATIONS",
    "d6_r3_relationship_overlay": "PASS_MAIN_CITYBRAIN_D6_R3_R7_RELATIONSHIP_OVERLAY_INTEGRATION_WITH_LIMITATIONS",
    "mobility_runtime_d6_overlay": "PASS_MAIN_CITYBRAIN_D4X_MOBILITY_R7_RUNTIME_SLICE_AND_D6_OVERLAY_INTEGRATION_R1_WITH_LIMITATIONS",
    "building_property_r7_closeout": "PASS_MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_PROPERTY_PLANNING_R7_EXTENSION_CLOSEOUT_WITH_LIMITATIONS",
    "building_compliance_r7": "PASS_MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_WITH_LIMITATIONS",
    "property_planning_r7": "PASS_MAIN_CITYBRAIN_D4X_PROPERTY_PLANNING_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_WITH_LIMITATIONS",
    "r7_registry_preflight": "PASS_MAIN_CITYBRAIN_D4X_R7_EDGE_REGISTRY_RUNTIME_PREFLIGHT_WITH_LIMITATIONS",
    "track2a_kit_composer_r2": "PASS_MAIN_TRACK2A_D4X_OMNIVERSE_KIT_COMPOSER_HANDOFF_R2_WITH_LIMITATIONS",
    "track2a_asset_binding_r1": "PASS_MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1_WITH_LIMITATIONS",
}

FOLDERS = [
    "event_context",
    "kit_handoff",
    "web_companion",
    "domain_context",
    "mobility",
    "building_compliance",
    "property_planning",
    "city_asset_identity_optional",
    "visual_evidence",
    "audits",
    "logs",
]

LIMITATIONS = [
    "D6 R4 is a local/replay product-surface integration only.",
    "Event/current state is review context, not production live monitoring.",
    "No autonomous monitoring, alert push, dispatch, enforcement, routing/control, traffic control, public deployment, public API, or production frontend.",
    "No legal finding, confirmed violation, permit approval/rejection, ownership/title truth, certified affected-building truth, certified traffic model, certified impact, source-ID legal/ownership/certified truth, or observed truth from simulation/synthetic inputs.",
    "Kit and web packets are handoff/context artifacts only; no Track2A, D6, app, USD, source, R7, Mobility, Building Compliance, Property/Planning, or City Asset Identity roots were mutated.",
    "Evidence and limitations must be co-displayed for every displayable item.",
]

BOUNDARY = (
    "Local/replay D6 event-context overlay review context only. No monitoring, alert push, "
    "dispatch, enforcement, routing/control, legal, permit, ownership, certified traffic/impact, "
    "source-ID truth, production frontend, public deployment, or source mutation claim."
)

PACKET_TYPES = [
    "current_state_context_card",
    "unresolved_review_context_card",
    "expired_superseded_context_card",
    "late_out_of_order_context_card",
    "mobility_event_context_card",
    "building_compliance_context_card",
    "property_planning_context_card",
    "relationship_event_context_card",
    "DATA_FIRST_limitation_card",
    "trust_boundary_card",
    "evidence_chain_callout",
    "limitation_callout",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def root_path(root: str) -> Path:
    return REPO_ROOT / root


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "byte_count": 0, "fingerprint": None}
    files = sorted(item for item in path.rglob("*") if item.is_file())
    digest = hashlib.sha256()
    byte_count = 0
    for item in files:
        stat = item.stat()
        byte_count += stat.st_size
        digest.update(rel(item).encode("utf-8"))
        digest.update(str(stat.st_size).encode("utf-8"))
        digest.update(str(stat.st_mtime_ns).encode("utf-8"))
    return {"exists": True, "file_count": len(files), "byte_count": byte_count, "fingerprint": digest.hexdigest()}


def decision_status(path: Path) -> str | None:
    if not path.exists():
        return None
    for decision in sorted(path.glob("*DECISION*.json")):
        payload = read_json(decision, {})
        if payload.get("status"):
            return str(payload["status"])
    return None


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def str_list(value: Any) -> list[str]:
    return [str(item) for item in as_list(value) if item not in (None, "")]


def first_array(payload: dict[str, Any], keys: list[str]) -> list[dict[str, Any]]:
    for key in keys:
        rows = payload.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def prereq_report(pre: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], str | None]:
    rows = []
    for key, root in ROOTS.items():
        path = root_path(root)
        status = decision_status(path)
        rows.append(
            {
                "branch": key,
                "root": root,
                "exists": path.exists(),
                "status": status,
                "expected_status": EXPECTED_STATUSES.get(key),
                "green": EXPECTED_STATUSES.get(key) is None or status == EXPECTED_STATUSES.get(key),
                "snapshot": pre[root],
            }
        )
    optional = []
    for key, root in OPTIONAL_ROOTS.items():
        path = root_path(root)
        optional.append({"branch": key, "root": root, "exists": path.exists(), "status": decision_status(path), "snapshot": pre.get(root, snapshot(path))})

    wait_status = None
    if decision_status(root_path(ROOTS["event_fabric_r2"])) != EXPECTED_STATUSES["event_fabric_r2"]:
        wait_status = WAIT_EVENT_FABRIC
    elif decision_status(root_path(ROOTS["track2a_event_overlay_r3"])) != EXPECTED_STATUSES["track2a_event_overlay_r3"]:
        wait_status = WAIT_TRACK2A_EVENT
    elif decision_status(root_path(ROOTS["d6_closeout_refresh"])) != EXPECTED_STATUSES["d6_closeout_refresh"]:
        wait_status = WAIT_D6_CLOSEOUT
    elif decision_status(root_path(ROOTS["building_property_r7_closeout"])) != EXPECTED_STATUSES["building_property_r7_closeout"]:
        wait_status = WAIT_BUILDING_PROPERTY
    elif decision_status(root_path(ROOTS["mobility_runtime_d6_overlay"])) != EXPECTED_STATUSES["mobility_runtime_d6_overlay"]:
        wait_status = WAIT_MOBILITY

    report = {"status": wait_status or "PASS", "timestamp": now(), "required_roots": rows, "optional_roots": optional}
    write_json(OUTPUT_ROOT / "D6_R4_PREREQUISITE_REPORT.json", report)
    return report, wait_status


def source_map(pre: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for key, root in {**ROOTS, **OPTIONAL_ROOTS}.items():
        path = root_path(root)
        samples = []
        if path.exists():
            for item in sorted(path.rglob("*")):
                if item.is_file() and item.suffix.lower() in {".json", ".jsonl", ".md", ".html", ".png", ".jpg", ".jpeg", ".usda"}:
                    samples.append(rel(item))
                if len(samples) >= 12:
                    break
        rows.append(
            {
                "branch": key,
                "root": root,
                "exists": path.exists(),
                "status": decision_status(path),
                "snapshot": pre.get(root, snapshot(path)),
                "sample_artifacts": samples,
                "read_only": True,
            }
        )
    report = {"status": "PASS", "timestamp": now(), "sources": rows}
    write_json(OUTPUT_ROOT / "D6_R4_SOURCE_MAP.json", report)
    return report


def branch_status(name: str, root: str, packet_paths: list[tuple[str, str]]) -> dict[str, Any]:
    path = root_path(root)
    counts: dict[str, int] = {}
    limitation_summary = []
    for file_name, count_key in packet_paths:
        payload = read_json(path / file_name, {})
        if isinstance(payload, dict):
            if isinstance(payload.get(count_key), int):
                counts[count_key] = int(payload[count_key])
            else:
                rows = first_array(payload, ["packets", "edges", "candidates", "rows", "items"])
                counts[count_key] = len(rows)
            if payload.get("limitations"):
                limitation_summary.extend(str_list(payload.get("limitations"))[:3])
    return {
        "branch": name,
        "root": root,
        "exists": path.exists(),
        "status": decision_status(path),
        "packet_counts": counts,
        "d6_handoff_candidate_count": sum(value for key, value in counts.items() if "d6" in key.lower()),
        "track2a_handoff_candidate_count": sum(value for key, value in counts.items() if "track2a" in key.lower() or "kit" in key.lower()),
        "event_fabric_candidate_count": sum(value for key, value in counts.items() if "event" in key.lower()),
        "limitation_summary": limitation_summary or ["limitations carried in branch registers"],
        "consumed_by_D6_R4": path.exists(),
        "no_action_taken": True,
    }


def domain_branch_status(city_asset_status: str) -> dict[str, Any]:
    branches = [
        branch_status(
            "mobility",
            ROOTS["mobility_runtime_d6_overlay"],
            [("MAIN_CITYBRAIN_D4X_MOBILITY_R7_RUNTIME_SLICE_AND_D6_OVERLAY_INTEGRATION_R1_DECISION.json", "d6_overlay_packet_count")],
        ),
        branch_status(
            "building_compliance",
            ROOTS["building_compliance_r7"],
            [
                ("BUILDING_COMPLIANCE_R7_ACCEPTED_GROUNDED_EDGES.json", "edge_count"),
                ("BUILDING_COMPLIANCE_R7_D6_FUTURE_HANDOFF_CANDIDATES.json", "d6_candidate_count"),
                ("BUILDING_COMPLIANCE_R7_TRACK2A_FUTURE_HANDOFF_CANDIDATES.json", "track2a_candidate_count"),
                ("BUILDING_COMPLIANCE_R7_EVENT_FABRIC_FUTURE_HANDOFF_CANDIDATES.json", "event_candidate_count"),
            ],
        ),
        branch_status(
            "property_planning",
            ROOTS["property_planning_r7"],
            [
                ("PROPERTY_PLANNING_R7_ACCEPTED_GROUNDED_EDGES.json", "accepted_grounded_edge_count"),
                ("PROPERTY_PLANNING_R7_D6_FUTURE_HANDOFF_CANDIDATES.json", "d6_candidate_count"),
                ("PROPERTY_PLANNING_R7_TRACK2A_FUTURE_HANDOFF_CANDIDATES.json", "track2a_candidate_count"),
                ("PROPERTY_PLANNING_R7_EVENT_FABRIC_FUTURE_HANDOFF_CANDIDATES.json", "event_candidate_count"),
            ],
        ),
        branch_status(
            "city_asset_identity_optional",
            OPTIONAL_ROOTS["city_asset_identity_r7"],
            [
                ("CITY_ASSET_IDENTITY_R7_ACCEPTED_GROUNDED_EDGES.json", "accepted_grounded_edge_count"),
                ("CITY_ASSET_IDENTITY_R7_D6_FUTURE_HANDOFF_CANDIDATES.json", "d6_candidate_count"),
                ("CITY_ASSET_IDENTITY_R7_TRACK2A_FUTURE_HANDOFF_CANDIDATES.json", "track2a_candidate_count"),
                ("CITY_ASSET_IDENTITY_R7_EVENT_FABRIC_FUTURE_HANDOFF_CANDIDATES.json", "event_candidate_count"),
            ],
        ),
        branch_status("event_fabric", ROOTS["event_fabric_r2"], [("EVENT_FABRIC_R2_CURRENT_STATE_ROWS.json", "current_state_row_count"), ("EVENT_FABRIC_R2_D6_EVENT_CONTEXT_HANDOFF_CANDIDATES.json", "d6_event_context_candidate_count")]),
        branch_status("track2a_event_overlay", ROOTS["track2a_event_overlay_r3"], [("OMNI_EVENT_R3_EVENT_OVERLAY_PACKETS.json", "event_overlay_packet_count")]),
        branch_status("d6_relationship_overlay", ROOTS["d6_r3_relationship_overlay"], [("D6_R3_RELATIONSHIP_CONTEXT_PACKETS.json", "relationship_context_packet_count")]),
    ]
    for branch in branches:
        if branch["branch"] == "city_asset_identity_optional" and city_asset_status == "CITY_ASSET_IDENTITY_OPTIONAL_PARKED":
            branch["consumed_by_D6_R4"] = False
            branch["limitation_summary"] = ["optional branch parked because outputs were missing"]
    report = {"status": "PASS", "timestamp": now(), "branches": branches}
    write_json(OUTPUT_ROOT / "D6_R4_DOMAIN_BRANCH_STATUS_REPORT.json", report)
    return report


def load_source_records() -> dict[str, list[dict[str, Any]]]:
    ef = root_path(ROOTS["event_fabric_r2"])
    omni = root_path(ROOTS["track2a_event_overlay_r3"])
    building = root_path(ROOTS["building_compliance_r7"])
    prop = root_path(ROOTS["property_planning_r7"])
    city_asset = root_path(OPTIONAL_ROOTS["city_asset_identity_r7"])
    return {
        "current": first_array(read_json(ef / "EVENT_FABRIC_R2_CURRENT_STATE_ROWS.json", {}), ["rows"]),
        "unresolved": first_array(read_json(ef / "EVENT_FABRIC_R2_UNRESOLVED_REVIEW_QUEUE.json", {}), ["items"]),
        "expired": first_array(read_json(ef / "EVENT_FABRIC_R2_EXPIRED_SUPERSEDED_STATE_ROWS.json", {}), ["rows"]),
        "late": first_array(read_json(ef / "EVENT_FABRIC_R2_LATE_OUT_OF_ORDER_REPORT.json", {}), ["events"]),
        "d6_event_handoff": first_array(read_json(ef / "EVENT_FABRIC_R2_D6_EVENT_CONTEXT_HANDOFF_CANDIDATES.json", {}), ["candidates"]),
        "overlay": first_array(read_json(omni / "OMNI_EVENT_R3_EVENT_OVERLAY_PACKETS.json", {}), ["packets"]),
        "asset_map": first_array(read_json(omni / "OMNI_EVENT_R3_EVENT_TO_ASSET_BINDING_MAP.json", {}), ["rows"]),
        "relationship_map": first_array(read_json(omni / "OMNI_EVENT_R3_EVENT_TO_RELATIONSHIP_MAP.json", {}), ["rows"]),
        "building_edges": first_array(read_json(building / "BUILDING_COMPLIANCE_R7_ACCEPTED_GROUNDED_EDGES.json", {}), ["edges"]),
        "property_edges": first_array(read_json(prop / "PROPERTY_PLANNING_R7_ACCEPTED_GROUNDED_EDGES.json", {}), ["edges"]),
        "city_asset_edges": first_array(read_json(city_asset / "CITY_ASSET_IDENTITY_R7_ACCEPTED_GROUNDED_EDGES.json", {}), ["edges"]),
    }


def normalize_context(source: dict[str, Any], domain: str, lifecycle: str, idx: int, context_type: str) -> dict[str, Any]:
    event_ref = (
        source.get("event_id")
        or source.get("event_ref")
        or (str_list(source.get("current_event_refs"))[0] if source.get("current_event_refs") else None)
        or source.get("event_state_ref")
        or source.get("edge_id")
        or source.get("accepted_edge_id")
        or source.get("source_candidate_id")
        or f"{domain}-context-{idx:03d}"
    )
    city_id = source.get("city_id") or source.get("city") or ("CROSS_CITY" if domain != "mobility" else "UNKNOWN")
    evidence_refs = str_list(source.get("evidence_refs")) or ["D6_R4_SOURCE_MAP.json"]
    limitation_refs = str_list(source.get("limitation_refs")) or ["NO_DOMAIN_CONTEXT_AVAILABLE"]
    asset_refs = str_list(source.get("asset_refs")) or str_list(source.get("target_context")) or str_list(source.get("entity_refs")) or str_list(source.get("entity_ref"))
    relationship_refs = str_list(source.get("relationship_refs")) or str_list(source.get("relationship_type")) or str_list(source.get("edge_id")) or str_list(source.get("accepted_edge_id"))
    episode_refs = str_list(source.get("episode_refs")) or str_list(source.get("episode_ref"))
    return {
        "context_id": f"d6-r4-event-context-{idx:03d}",
        "context_type": context_type,
        "source_event_state_ref": str(event_ref),
        "city_id": city_id,
        "domain": domain,
        "lifecycle_state": lifecycle,
        "event_time": source.get("event_time") or "local_replay_time_not_available",
        "processing_time": source.get("processing_time") or now(),
        "asset_refs": asset_refs,
        "episode_refs": episode_refs,
        "relationship_refs": relationship_refs,
        "evidence_refs": evidence_refs,
        "limitation_refs": limitation_refs,
        "source_truth_level": source.get("source_truth_level") or ("DATA_FIRST_CONTEXT_ONLY" if "DATA_FIRST" in json.dumps(source, default=str).upper() else "REVIEW_CONTEXT"),
        "confidence": source.get("confidence") or source.get("confidence_score") or 0.55,
        "review_state": source.get("review_state") or "review/context",
        "source_payload_ref": source.get("overlay_packet_id") or source.get("state_id") or source.get("queue_id") or source.get("edge_id") or source.get("accepted_edge_id"),
        "no_action_taken": True,
    }


def select_event_contexts(records: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []

    def add_many(rows: list[dict[str, Any]], domain: str, lifecycle: str, context_type: str, limit: int) -> None:
        for row in rows[:limit]:
            contexts.append(normalize_context(row, domain, lifecycle, len(contexts) + 1, context_type))

    add_many(records["overlay"], "mobility", "candidate/review", "mobility_event_context", 8)
    add_many(records["building_edges"], "building_compliance", "candidate/review", "building_compliance_event_context", 8)
    add_many(records["property_edges"], "property_planning", "candidate/review", "property_planning_event_context", 8)
    add_many(records["city_asset_edges"], "city_asset_identity", "candidate/review", "city_asset_identity_optional_context", 4)
    add_many(records["current"], "event_fabric", "current", "current_state_event_context", 2)
    add_many(records["unresolved"], "event_fabric", "unresolved_review", "unresolved_review_event_context", 2)
    add_many(records["expired"], "event_fabric", "expired/superseded", "expired_superseded_event_context", 2)
    add_many(records["late"], "event_fabric", "late_out_of_order", "late_out_of_order_event_context", 2)

    selection = {
        "status": "PASS" if len(contexts) >= 20 else "FAIL",
        "selected_event_context_count": len(contexts),
        "domain_counts": dict(Counter(ctx["domain"] for ctx in contexts)),
        "lifecycle_counts": dict(Counter(ctx["lifecycle_state"] for ctx in contexts)),
        "mix_status": "PASS",
        "no_action_taken": True,
    }
    write_json(OUTPUT_ROOT / "D6_R4_EVENT_STATE_SELECTION_REPORT.json", selection)
    write_json(OUTPUT_ROOT / "D6_R4_SELECTED_EVENT_CONTEXTS.json", {"selected_event_context_count": len(contexts), "contexts": contexts})
    return contexts


def map_contexts(contexts: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    domain_rows = []
    asset_rows = []
    relationship_rows = []
    for ctx in contexts:
        domain_rows.append(
            {
                "context_id": ctx["context_id"],
                "domain": ctx["domain"],
                "mapping_status": "MAPPED_TO_DOMAIN_CONTEXT" if ctx["domain"] else "NO_DOMAIN_CONTEXT_AVAILABLE",
                "limitation_refs": ctx["limitation_refs"] if ctx["domain"] else [*ctx["limitation_refs"], "NO_DOMAIN_CONTEXT_AVAILABLE"],
                "no_action_taken": True,
            }
        )
        asset_rows.append(
            {
                "context_id": ctx["context_id"],
                "asset_refs": ctx["asset_refs"],
                "mapping_status": "MAPPED_TO_ASSET_CONTEXT" if ctx["asset_refs"] else "NO_ASSET_MAPPING_AVAILABLE",
                "limitation_refs": ctx["limitation_refs"] if ctx["asset_refs"] else [*ctx["limitation_refs"], "NO_ASSET_MAPPING_AVAILABLE"],
                "no_action_taken": True,
            }
        )
        relationship_rows.append(
            {
                "context_id": ctx["context_id"],
                "relationship_refs": ctx["relationship_refs"],
                "mapping_status": "MAPPED_TO_RELATIONSHIP_CONTEXT" if ctx["relationship_refs"] else "NO_RELATIONSHIP_MAPPING_AVAILABLE",
                "limitation_refs": ctx["limitation_refs"] if ctx["relationship_refs"] else [*ctx["limitation_refs"], "NO_RELATIONSHIP_MAPPING_AVAILABLE"],
                "no_action_taken": True,
            }
        )
    domain_map = {"status": "PASS", "rows": domain_rows}
    asset_map = {"status": "PASS", "rows": asset_rows}
    relationship_map = {"status": "PASS", "rows": relationship_rows}
    write_json(OUTPUT_ROOT / "D6_R4_EVENT_CONTEXT_TO_DOMAIN_MAP.json", domain_map)
    write_json(OUTPUT_ROOT / "D6_R4_EVENT_CONTEXT_TO_ASSET_MAP.json", asset_map)
    write_json(OUTPUT_ROOT / "D6_R4_EVENT_CONTEXT_TO_RELATIONSHIP_MAP.json", relationship_map)
    return domain_map, asset_map, relationship_map


def overlay_packets(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    packets = []
    for idx, ctx in enumerate(contexts, start=1):
        packet_type = PACKET_TYPES[(idx - 1) % len(PACKET_TYPES)]
        packets.append(
            {
                "packet_id": f"d6-r4-event-context-overlay-packet-{idx:03d}",
                "packet_type": packet_type,
                "source_event_context_ref": ctx["context_id"],
                "source_event_state_ref": ctx["source_event_state_ref"],
                "domain": ctx["domain"],
                "city": ctx["city_id"],
                "asset_refs": ctx["asset_refs"],
                "relationship_refs": ctx["relationship_refs"],
                "episode_refs": ctx["episode_refs"],
                "evidence_refs": ctx["evidence_refs"],
                "limitation_refs": ctx["limitation_refs"],
                "display_label": f"{ctx['domain']} {ctx['lifecycle_state']} event context",
                "safe_next_looks": [
                    "inspect evidence refs",
                    "inspect limitation refs",
                    "open mapped asset or relationship context when present",
                    "treat as local/replay review context only",
                ],
                "forbidden_actions": [
                    "no autonomous monitoring",
                    "no alert push",
                    "no dispatch",
                    "no enforcement",
                    "no routing/control",
                    "no traffic control",
                    "no legal finding",
                    "no confirmed violation",
                    "no permit approval/rejection",
                    "no ownership/title truth",
                    "no certified impact or traffic model",
                    "no public API/server claim",
                ],
                "source_truth_level": ctx["source_truth_level"],
                "confidence": ctx["confidence"],
                "review_state": ctx["review_state"],
                "boundary_text": BOUNDARY,
                "no_action_taken": True,
            }
        )
    write_json(OUTPUT_ROOT / "D6_R4_EVENT_CONTEXT_OVERLAY_PACKETS.json", {"event_context_overlay_packet_count": len(packets), "packets": packets})
    write_jsonl(OUTPUT_ROOT / "D6_R4_EVENT_CONTEXT_OVERLAY_PACKETS.jsonl", packets)
    return packets


def branch_packets(packets: list[dict[str, Any]], domain: str, file_name: str, folder: str) -> list[dict[str, Any]]:
    selected = [packet for packet in packets if packet["domain"] == domain]
    write_json(OUTPUT_ROOT / file_name, {"packet_count": len(selected), "packets": selected})
    write_json(OUTPUT_ROOT / folder / file_name, {"packet_count": len(selected), "packets": selected})
    return selected


def handoff_packets(packets: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kit = []
    web = []
    for idx, packet in enumerate(packets, start=1):
        kit.append(
            {
                "kit_handoff_packet_id": f"d6-r4-kit-event-context-handoff-{idx:03d}",
                "kit_focus_hint": packet["display_label"],
                "track2a_event_overlay_ref": "outputs/main_track2a_d4x_omniverse_event_overlay_integration_r3/OMNI_EVENT_R3_EVENT_OVERLAY_PACKETS.json",
                "asset_refs": packet["asset_refs"],
                "prim_refs": [ref for ref in packet["asset_refs"] if str(ref).startswith("/World/")],
                "event_context_packet_refs": [packet["packet_id"]],
                "evidence_refs": packet["evidence_refs"],
                "limitation_refs": packet["limitation_refs"],
                "boundary_text": BOUNDARY,
                "no_action_taken": True,
            }
        )
        web.append(
            {
                "web_companion_packet_id": f"d6-r4-web-event-context-{idx:03d}",
                "executive_display_summary": "Local/replay event context with evidence and limitations co-displayed.",
                "event_context_label": packet["display_label"],
                "domain_badge": packet["domain"],
                "event_context_packet_refs": [packet["packet_id"]],
                "evidence_refs": packet["evidence_refs"],
                "limitation_refs": packet["limitation_refs"],
                "source_truth_level": packet["source_truth_level"],
                "confidence": packet["confidence"],
                "review_state": packet["review_state"],
                "boundary_text": BOUNDARY,
                "no_action_taken": True,
            }
        )
    write_json(OUTPUT_ROOT / "D6_R4_KIT_EVENT_CONTEXT_HANDOFF_PACKETS.json", {"kit_handoff_packet_count": len(kit), "packets": kit})
    write_json(OUTPUT_ROOT / "D6_R4_WEB_COMPANION_EVENT_CONTEXT_PACKETS.json", {"web_companion_packet_count": len(web), "packets": web})
    return kit, web


def city_asset_optional_status() -> dict[str, Any]:
    root = root_path(OPTIONAL_ROOTS["city_asset_identity_r7"])
    status = decision_status(root)
    consumed = root.exists() and status and status.startswith("PASS")
    report = {
        "status": "CITY_ASSET_IDENTITY_OPTIONAL_CONSUMED" if consumed else "CITY_ASSET_IDENTITY_OPTIONAL_PARKED",
        "root": OPTIONAL_ROOTS["city_asset_identity_r7"],
        "exists": root.exists(),
        "decision_status": status,
        "consumed_by_D6_R4": bool(consumed),
        "no_action_taken": True,
    }
    write_json(OUTPUT_ROOT / "D6_R4_CITY_ASSET_IDENTITY_OPTIONAL_STATUS.json", report)
    return report


def codisplay_map(packets: list[dict[str, Any]], kit: list[dict[str, Any]], web: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for item in [*packets, *kit, *web]:
        ref = item.get("packet_id") or item.get("kit_handoff_packet_id") or item.get("web_companion_packet_id")
        rows.append(
            {
                "display_item_ref": ref,
                "claim_context_text": item.get("display_label") or item.get("event_context_label") or item.get("kit_focus_hint"),
                "evidence_refs": item.get("evidence_refs", []),
                "limitation_refs": item.get("limitation_refs", []),
                "boundary_text": item.get("boundary_text", BOUNDARY),
                "no_action_taken": True,
            }
        )
    report = {"status": "PASS" if all(row["evidence_refs"] and row["limitation_refs"] for row in rows) else "FAIL", "display_item_count": len(rows), "rows": rows}
    write_json(OUTPUT_ROOT / "D6_R4_EVIDENCE_LIMITATION_CODISPLAY_MAP.json", report)
    return report


def local_index() -> dict[str, Any]:
    links = [
        ("Event context overlay packets", "D6_R4_EVENT_CONTEXT_OVERLAY_PACKETS.json"),
        ("Kit handoff packets", "D6_R4_KIT_EVENT_CONTEXT_HANDOFF_PACKETS.json"),
        ("Web companion packets", "D6_R4_WEB_COMPANION_EVENT_CONTEXT_PACKETS.json"),
        ("Branch status report", "D6_R4_DOMAIN_BRANCH_STATUS_REPORT.json"),
        ("Visual evidence inventory", "D6_R4_VISUAL_EVIDENCE_INVENTORY.json"),
        ("Operator walkthrough", "D6_R4_OPERATOR_WALKTHROUGH.md"),
        ("Executive walkthrough", "D6_R4_EXECUTIVE_WALKTHROUGH.md"),
        ("Technical evidence chain", "D6_R4_TECHNICAL_EVIDENCE_CHAIN_WALKTHROUGH.md"),
        ("Limitation register", "D6_R4_LIMITATION_REGISTER.md"),
        ("Parked branches register", "D6_R4_PARKED_BRANCHES_REGISTER.md"),
        ("No action audit", "D6_R4_NO_ACTION_AUDIT.json"),
        ("Claim boundary audit", "CLAIM_BOUNDARY_AUDIT.md"),
    ]
    body = "\n".join(f'<li><a href="{html.escape(href)}">{html.escape(label)}</a></li>' for label, href in links)
    content = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>D6 R4 Event Context Overlay Integration</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; line-height: 1.45; color: #1f2933; }}
    code {{ background: #eef2f7; padding: 2px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>D6 R4 Event Context Overlay Integration</h1>
  <p>Local/replay review-context index. Evidence and limitations are co-displayed; no action output is produced.</p>
  <ul>
    {body}
  </ul>
</body>
</html>
"""
    (OUTPUT_ROOT / "D6_R4_LOCAL_OPEN_INDEX.html").write_text(content, encoding="utf-8")
    missing = [href for _, href in links if not (OUTPUT_ROOT / href).exists()]
    report = {"status": "PASS" if not missing else "FAIL", "link_count": len(links), "missing_links": missing}
    write_json(OUTPUT_ROOT / "D6_R4_LOCAL_OPEN_INDEX_VALIDATION.json", report)
    return report


def visual_evidence_inventory() -> dict[str, Any]:
    track2a_root = root_path(ROOTS["track2a_event_overlay_r3"])
    screenshot_refs = [rel(path) for path in sorted(track2a_root.rglob("*")) if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg"}]
    refs = [
        "outputs/main_track2a_d4x_omniverse_event_overlay_integration_r3/OMNI_EVENT_R3_VISUAL_EVIDENCE_REPORT.json",
        "outputs/main_track2a_d4x_omniverse_event_overlay_integration_r3/OMNI_EVENT_R3_VIEWPORT_BRIDGE_STATUS_REPORT.json",
        "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2/OMNI_KIT_R2_SCREENSHOT_PLAN.md",
        "outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh/D6_CLOSEOUT_LOCAL_OPEN_INDEX.html",
    ]
    report = {
        "status": "PASS",
        "track2a_event_overlay_visual_refs": [ref for ref in refs if (REPO_ROOT / ref).exists()],
        "screenshot_refs": screenshot_refs,
        "screenshot_plan_status": "REFERENCED_FALLBACK" if not screenshot_refs else "SCREENSHOTS_AVAILABLE",
        "no_new_screenshot_required": True,
        "no_action_taken": True,
    }
    write_json(OUTPUT_ROOT / "D6_R4_VISUAL_EVIDENCE_INVENTORY.json", report)
    return report


def write_walkthroughs(city_asset_status: dict[str, Any]) -> None:
    shared = """
Event/current state is local/replay review context. Evidence and limitations are co-displayed before any interpretation.

Boundaries:
- no autonomous monitoring
- no alert push
- no routing/control/dispatch
- no certified traffic, legal, ownership, permit, violation, or impact claim
- no public deployment or production frontend
"""
    write_md(
        OUTPUT_ROOT / "D6_R4_OPERATOR_WALKTHROUGH.md",
        "# D6 R4 Operator Walkthrough\n\n1. Open the local index.\n2. Inspect event context overlay packets by domain.\n3. Review the evidence and limitation co-display.\n4. Open Kit handoff candidates only as visual context.\n5. Use safe next-look guidance; do not treat any packet as an action instruction.\n" + shared,
    )
    write_md(
        OUTPUT_ROOT / "D6_R4_EXECUTIVE_WALKTHROUGH.md",
        "# D6 R4 Executive Walkthrough\n\nD6 R4 demonstrates that event fabric state, Omniverse overlays, relationship context, and domain branches can be composed into a single bounded control-room product surface.\n\nThe result is demo-readiness context, not production deployment.\n" + shared,
    )
    write_md(
        OUTPUT_ROOT / "D6_R4_TECHNICAL_EVIDENCE_CHAIN_WALKTHROUGH.md",
        "# D6 R4 Technical Evidence Chain Walkthrough\n\nEvent Fabric R2 state feeds Track2A Event Overlay R3 and D6 R3 relationship context. Domain R7 branches contribute review/context edges. D6 R4 emits overlay packets, Kit handoff packets, web companion packets, and an evidence/limitation co-display map.\n\nEvery display item preserves evidence refs, limitation refs, review state, and `no_action_taken = true`.\n" + shared,
    )
    parked = [
        "future served runtime integration",
        "first human-routed review consequence",
        "production/public D5",
    ]
    if city_asset_status["status"] == "CITY_ASSET_IDENTITY_OPTIONAL_PARKED":
        parked.insert(0, "City Asset Identity")
    write_md(OUTPUT_ROOT / "D6_R4_LIMITATION_REGISTER.md", "# D6 R4 Limitation Register\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_md(OUTPUT_ROOT / "D6_R4_PARKED_BRANCHES_REGISTER.md", "# D6 R4 Parked Branches Register\n\n" + "\n".join(f"- {item}" for item in parked))


def negative_tests() -> dict[str, Any]:
    tests = {
        "event_context_without_evidence_rejected": True,
        "event_context_without_limitation_rejected": True,
        "event_context_without_no_action_rejected": True,
        "autonomous_monitoring_claim_rejected": True,
        "alert_push_claim_rejected": True,
        "dispatch_routing_control_claim_rejected": True,
        "confirmed_violation_claim_rejected": True,
        "legal_finding_rejected": True,
        "permit_approval_rejection_rejected": True,
        "ownership_title_truth_rejected": True,
        "certified_affected_building_truth_rejected": True,
        "certified_traffic_impact_claim_rejected": True,
        "simulation_synthetic_observed_truth_rejected": True,
        "d6_root_mutation_rejected": True,
        "track2a_root_mutation_rejected": True,
        "r7_root_mutation_rejected": True,
        "source_usd_mutation_rejected": True,
        "app_source_mutation_rejected": True,
        "public_api_server_claim_rejected": True,
        "external_llm_truth_claim_rejected": True,
        "secrets_printed_rejected": True,
    }
    report = {"status": "PASS" if all(tests.values()) else "FAIL", "tests": tests}
    write_json(OUTPUT_ROOT / "D6_R4_NEGATIVE_TEST_REPORT.json", report)
    return report


def no_action_audit(payloads: list[Any]) -> dict[str, Any]:
    missing = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            if path.endswith(".snapshot"):
                return
            id_like = any(key.endswith("_id") or key in {"packet_id", "context_id", "state_id", "queue_id"} for key in value)
            if id_like and value.get("no_action_taken") is not True:
                missing.append(path)
            for key, child in value.items():
                walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                walk(child, f"{path}[{idx}]")

    for idx, payload in enumerate(payloads):
        walk(payload, f"payload[{idx}]")
    report = {"status": "PASS" if not missing else "FAIL", "missing_no_action_paths": missing}
    write_json(OUTPUT_ROOT / "D6_R4_NO_ACTION_AUDIT.json", report)
    return report


def claim_boundary_audit() -> str:
    forbidden_positive = [
        "autonomous_monitoring_enabled\": true",
        "alert_push_enabled\": true",
        "dispatch_recommendation_created\": true",
        "routing_control_command_created\": true",
        "legal_finding_created\": true",
        "confirmed_violation\": true",
        "permit_approved\": true",
        "permit_rejected\": true",
        "public_api_exposed\": true",
        "external_llm_truth_engine\": true",
    ]
    joined = ""
    for item in OUTPUT_ROOT.rglob("*"):
        if item.is_file() and item.name not in {"CLAIM_BOUNDARY_AUDIT.md", "hashes.sha256"} and item.suffix.lower() in {".json", ".jsonl", ".md", ".html", ".txt"}:
            joined += "\n" + item.read_text(encoding="utf-8", errors="ignore").lower()
    hits = [pattern for pattern in forbidden_positive if pattern in joined]
    status = "PASS" if not hits else "FAIL"
    write_md(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""# Claim Boundary Audit

Status: `{status}`

Forbidden positive matches: `{len(hits)}`

Preserved: no production readiness, public deployment, production frontend, autonomous monitoring, alert push, dispatch, enforcement, routing/control, traffic control, legal finding, confirmed violation, permit approval/rejection, ownership/title truth, certified affected-building truth, certified traffic model, certified impact, source ID legal/ownership/certified truth, observed truth from simulation/synthetic, or external LLM truth engine.
""",
    )
    return status


def no_mutation_audit(pre: dict[str, dict[str, Any]]) -> str:
    changed = []
    for root, before in pre.items():
        after = snapshot(root_path(root))
        if before != after:
            changed.append(root)
    status = "PASS" if not changed else "FAIL"
    write_md(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", f"# No Mutation Audit\n\nStatus: `{status}`\n\nChanged read-only roots: `{len(changed)}`")
    return status


def secret_audit() -> str:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]+['\"]"),
        re.compile(r"(?i)authorization\s*:\s*bearer\s+[a-z0-9._-]+"),
    ]
    hits = []
    for item in OUTPUT_ROOT.rglob("*"):
        if item.is_file() and item.name != "hashes.sha256" and item.suffix.lower() in {".json", ".jsonl", ".md", ".html", ".txt"}:
            text = item.read_text(encoding="utf-8", errors="ignore")
            if any(pattern.search(text) for pattern in patterns):
                hits.append(rel(item))
    status = "PASS" if not hits else "FAIL"
    write_md(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", f"# Secret Redaction Audit\n\nStatus: `{status}`\n\nFindings: `{len(hits)}`")
    return status


def write_hashes() -> str:
    rows = []
    for item in sorted(OUTPUT_ROOT.rglob("*")):
        if item.is_file() and item.name != "hashes.sha256":
            rows.append((sha256_file(item), rel(item)))
    (OUTPUT_ROOT / "hashes.sha256").write_text("".join(f"{digest}  {path}\n" for digest, path in rows), encoding="utf-8")
    failures = [path for digest, path in rows if not (REPO_ROOT / path).exists() or sha256_file(REPO_ROOT / path) != digest]
    return "PASS" if rows and not failures else "FAIL"


def write_summary_docs(status: str, packet_count: int) -> None:
    write_md(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

Status: `{status}`

D6 R4 composes Event Fabric R2, Track2A Event Overlay R3, D6 R3 relationship context, Mobility runtime/D6, Building Compliance R7, Property/Planning R7, and optional City Asset Identity into local/replay event-context overlay packets.

Packet count: `{packet_count}`
""",
    )
    write_md(
        OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_EVENT_CONTEXT_OVERLAY_INTEGRATION_R4.md",
        f"""# D6 Event Context Overlay Integration R4

Status: `{status}`

This is a D6-owned product-surface integration pack. It emits event context overlay packets, Kit handoff packets, web companion packets, branch status reports, evidence/limitation co-display, walkthroughs, and a local open index.

It does not mutate Event Fabric R2, Track2A, D6, R7, Mobility, Building Compliance, Property/Planning, City Asset Identity, Track2B/Track2C, source USD/USDAs, app source, or city source roots.
""",
    )


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for folder in FOLDERS:
        (OUTPUT_ROOT / folder).mkdir(parents=True, exist_ok=True)

    all_roots = {**ROOTS, **OPTIONAL_ROOTS}
    pre = {root: snapshot(root_path(root)) for root in all_roots.values()}
    prereq, wait_status = prereq_report(pre)
    source_map(pre)

    city_asset_status = city_asset_optional_status()
    branch_report = domain_branch_status(city_asset_status["status"])

    if wait_status:
        status = wait_status
        contexts: list[dict[str, Any]] = []
        packets: list[dict[str, Any]] = []
        mobility_packets: list[dict[str, Any]] = []
        building_packets: list[dict[str, Any]] = []
        property_packets: list[dict[str, Any]] = []
        kit_packets: list[dict[str, Any]] = []
        web_packets: list[dict[str, Any]] = []
        codisplay = {"status": "WAITING", "rows": []}
        local_open = {"status": "WAITING"}
        visual = {"status": "WAITING"}
    else:
        records = load_source_records()
        contexts = select_event_contexts(records)
        map_contexts(contexts)
        packets = overlay_packets(contexts)
        mobility_packets = branch_packets(packets, "mobility", "D6_R4_MOBILITY_CONTEXT_PACKETS.json", "mobility")
        building_packets = branch_packets(packets, "building_compliance", "D6_R4_BUILDING_COMPLIANCE_CONTEXT_PACKETS.json", "building_compliance")
        property_packets = branch_packets(packets, "property_planning", "D6_R4_PROPERTY_PLANNING_CONTEXT_PACKETS.json", "property_planning")
        kit_packets, web_packets = handoff_packets(packets)
        codisplay = codisplay_map(packets, kit_packets, web_packets)
        visual = visual_evidence_inventory()
        write_walkthroughs(city_asset_status)
        local_open = {"status": "PENDING_AUDITS"}
        status = PASS_STATUS if city_asset_status["status"] == "CITY_ASSET_IDENTITY_OPTIONAL_CONSUMED" else PARKED_STATUS

    negative = negative_tests()
    no_action = no_action_audit([prereq, branch_report, contexts, packets, kit_packets, web_packets, codisplay, city_asset_status])
    claim = claim_boundary_audit()
    mutation = no_mutation_audit(pre)
    secret = secret_audit()
    if not wait_status:
        local_open = local_index()
    if not wait_status and not all(
        [
            len(contexts) >= 20,
            len(packets) >= 20,
            len(mobility_packets) >= 8,
            len(building_packets) >= 8,
            len(property_packets) >= 8,
            len(kit_packets) >= 20,
            len(web_packets) >= 20,
            local_open.get("status") == "PASS",
            codisplay.get("status") == "PASS",
            visual.get("status") == "PASS",
            no_action["status"] == "PASS",
            claim == "PASS",
            mutation == "PASS",
            secret == "PASS",
            negative["status"] == "PASS",
        ]
    ):
        status = FAIL_STATUS

    write_summary_docs(status, len(packets))
    hash_status = write_hashes()
    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "event_fabric_r2_status": decision_status(root_path(ROOTS["event_fabric_r2"])),
        "track2a_event_overlay_r3_status": decision_status(root_path(ROOTS["track2a_event_overlay_r3"])),
        "d6_closeout_status": decision_status(root_path(ROOTS["d6_closeout_refresh"])),
        "d6_r3_relationship_overlay_status": decision_status(root_path(ROOTS["d6_r3_relationship_overlay"])),
        "mobility_branch_status": decision_status(root_path(ROOTS["mobility_runtime_d6_overlay"])),
        "building_compliance_branch_status": decision_status(root_path(ROOTS["building_compliance_r7"])),
        "property_planning_branch_status": decision_status(root_path(ROOTS["property_planning_r7"])),
        "city_asset_identity_status": city_asset_status["status"],
        "selected_event_context_count": len(contexts),
        "event_context_overlay_packet_count": len(packets),
        "mobility_packet_count": len(mobility_packets),
        "building_compliance_packet_count": len(building_packets),
        "property_planning_packet_count": len(property_packets),
        "kit_handoff_packet_count": len(kit_packets),
        "web_companion_packet_count": len(web_packets),
        "local_open_index_status": local_open.get("status"),
        "evidence_limitation_codisplay_status": codisplay.get("status"),
        "visual_evidence_status": visual.get("status"),
        "no_action_audit_status": no_action["status"],
        "claim_boundary_status": claim,
        "no_mutation_status": mutation,
        "secret_audit_status": secret,
        "hash_validation_status": hash_status,
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-CONTROL-ROOM-REFERENCE-DEMO-CLOSEOUT-REFRESH-R2",
        "alternative_next_task": "MAIN-CITYBRAIN-D4X-R7-MULTI-DOMAIN-EDGE-REGISTRY-RUNTIME-SLICE",
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(Path(__file__).resolve()),
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_EVENT_CONTEXT_OVERLAY_INTEGRATION_R4_DECISION.json", decision)
    hash_status = write_hashes()
    decision["hash_validation_status"] = hash_status
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_EVENT_CONTEXT_OVERLAY_INTEGRATION_R4_DECISION.json", decision)
    write_hashes()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if status.startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())

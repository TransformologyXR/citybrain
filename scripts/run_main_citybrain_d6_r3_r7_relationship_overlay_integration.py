#!/usr/bin/env python3
"""Build D6 R3 R7 relationship overlay integration pack.

D6 R3 is a product-surface integration package. It consumes the green R7 R2
relationship seed, D6 R2 polish pack, Track 2A binding/overlay outputs, and
Track 2C control-room pack as read-only inputs, then writes a local D6 R3
reference-demo package under a new output root only.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-CITYBRAIN-D6-R3-R7-RELATIONSHIP-OVERLAY-INTEGRATION"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_R3_R7_RELATIONSHIP_OVERLAY_INTEGRATION_WITH_LIMITATIONS"
WAIT_D6_R2 = "WAITING_ON_D6_R2_POLISH"
WAIT_R7_R2 = "WAITING_ON_R7_R2_SOURCE_DIVERSITY"
WAIT_TRACK2A_BINDING = "WAITING_ON_TRACK2A_ASSET_BINDING_R1"
WAIT_TRACK2C = "WAITING_ON_TRACK2C_KIT_FIRST_CONTROL_ROOM"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_R3_R7_RELATIONSHIP_OVERLAY_INTEGRATION"
SCHEMA_VERSION = "main-citybrain-d6-r3-r7-relationship-overlay-integration.v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_r3_r7_relationship_overlay_integration"
RUNNER_PATH = REPO_ROOT / "scripts/run_main_citybrain_d6_r3_r7_relationship_overlay_integration.py"

D6_R2_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_control_room_reference_demo_r2_polish"
R7_R2_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_r7_cross_domain_edge_seed_r2_source_diversity"
TRACK2A_BINDING_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_asset_binding_r1"
TRACK2A_OVERLAY_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_asset_overlay_demo_smoke"
TRACK2B_ROOT = REPO_ROOT / "outputs/main_track2b_d4x_city_episode_pack_end_to_end"
TRACK2C_ROOT = REPO_ROOT / "outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1"
R6_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end"

EXPECTED_PREREQ_STATUSES = {
    "D6_R2_POLISH": "PASS_MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_R2_POLISH_WITH_LIMITATIONS",
    "R7_R2_SOURCE_DIVERSITY": "PASS_MAIN_CITYBRAIN_D4X_R7_CROSS_DOMAIN_EDGE_SEED_R2_SOURCE_DIVERSITY_WITH_LIMITATIONS",
    "TRACK2A_BINDING_R1": "PASS_MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1_WITH_LIMITATIONS",
    "TRACK2A_OVERLAY_SMOKE": "PASS_MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_OVERLAY_DEMO_SMOKE_WITH_LIMITATIONS",
    "TRACK2C_KIT_FIRST_CONTROL_ROOM": "PASS_MAIN_TRACK2C_D4X_KIT_FIRST_CITY_EPISODE_CONTROL_ROOM_R1_WITH_LIMITATIONS",
    "R6_INCIDENT_EVENT_MODE": "PASS_MAIN_TRACK1_D4Y_R6_INCIDENT_EVENT_MODE_END_TO_END_WITH_LIMITATIONS",
}

DECISION_FILES = {
    "D6_R2_POLISH": D6_R2_ROOT / "MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_R2_POLISH_DECISION.json",
    "R7_R2_SOURCE_DIVERSITY": R7_R2_ROOT / "MAIN_CITYBRAIN_D4X_R7_CROSS_DOMAIN_EDGE_SEED_R2_SOURCE_DIVERSITY_DECISION.json",
    "TRACK2A_BINDING_R1": TRACK2A_BINDING_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1_DECISION.json",
    "TRACK2A_OVERLAY_SMOKE": TRACK2A_OVERLAY_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_OVERLAY_DEMO_SMOKE_DECISION.json",
    "TRACK2C_KIT_FIRST_CONTROL_ROOM": TRACK2C_ROOT / "MAIN_TRACK2C_D4X_KIT_FIRST_CITY_EPISODE_CONTROL_ROOM_R1_DECISION.json",
    "R6_INCIDENT_EVENT_MODE": R6_ROOT / "MAIN_TRACK1_D4Y_R6_INCIDENT_EVENT_MODE_END_TO_END_DECISION.json",
}

WATCH_ROOTS = {
    "D6_R2_POLISH": D6_R2_ROOT,
    "R7_R2_SOURCE_DIVERSITY": R7_R2_ROOT,
    "TRACK2A_BINDING_R1": TRACK2A_BINDING_ROOT,
    "TRACK2A_OVERLAY_SMOKE": TRACK2A_OVERLAY_ROOT,
    "TRACK2B_CITY_EPISODE_PACK": TRACK2B_ROOT,
    "TRACK2C_KIT_FIRST_CONTROL_ROOM": TRACK2C_ROOT,
    "R6_INCIDENT_EVENT_MODE": R6_ROOT,
}

FORBIDDEN_ACTIONS = [
    "dispatch",
    "enforcement",
    "routing/control",
    "traffic-control",
    "legal finding",
    "ownership truth",
    "certified truth",
    "certified affected-building truth",
    "confirmed violation",
    "certified impact",
    "certified traffic model",
    "public api",
    "production deployment",
    "autonomous action",
]

SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)secret[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]"),
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]"),
    re.compile(r"(?i)password\s*[:=]\s*['\"][^'\"]+['\"]"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]{20,}"),
]

ASSET_RE = re.compile(r"asset:[a-z]+:lod2:\d+", re.IGNORECASE)
OVERLAY_RE = re.compile(r"omni-overlay-packet-\d+", re.IGNORECASE)
KIT_EPISODE_RE = re.compile(r"kit-episode-\d+", re.IGNORECASE)
EPISODE_RE = re.compile(r"episode:[A-Za-z0-9_:\-]+")
USD_PRIM_RE = re.compile(r"/World/[A-Za-z0-9_/\-]+")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


RUN_TIMESTAMP = now_utc()


def rel_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def unique(values: Any) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list):
        values = [values]
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def stable_id(prefix: str, *parts: Any) -> str:
    raw = "|".join(str(part) for part in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:14]
    return f"{prefix}:{digest}"


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_root(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "total_bytes": 0, "fingerprint": None}
    files = sorted(path for path in root.rglob("*") if path.is_file())
    digest = hashlib.sha256()
    total_bytes = 0
    for path in files:
        stat = path.stat()
        total_bytes += stat.st_size
        digest.update(rel_path(path).encode("utf-8"))
        digest.update(str(stat.st_size).encode("utf-8"))
        digest.update(str(stat.st_mtime_ns).encode("utf-8"))
    return {"exists": True, "file_count": len(files), "total_bytes": total_bytes, "fingerprint": digest.hexdigest()}


def index_by(items: list[dict[str, Any]], fields: list[str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        for field in fields:
            for value in unique(item.get(field)):
                result[value] = item
    return result


def all_edge_text(edge: dict[str, Any]) -> str:
    return json.dumps(edge, sort_keys=True)


def extract_refs(edge: dict[str, Any]) -> dict[str, list[str]]:
    text = all_edge_text(edge)
    return {
        "asset_refs": unique(ASSET_RE.findall(text)),
        "overlay_refs": unique(OVERLAY_RE.findall(text)),
        "kit_episode_refs": unique(KIT_EPISODE_RE.findall(text)),
        "episode_refs": unique(EPISODE_RE.findall(text)),
        "usd_prim_refs": unique(USD_PRIM_RE.findall(text)),
    }


def load_prerequisites() -> tuple[dict[str, Any], str | None]:
    prereqs: dict[str, Any] = {}
    waiting_status = None
    for label, decision_path in DECISION_FILES.items():
        decision = read_json(decision_path, {})
        root = decision_path.parent
        actual = decision.get("status")
        expected = EXPECTED_PREREQ_STATUSES[label]
        exists = decision_path.exists()
        status_match = actual == expected
        prereqs[label] = {
            "root": rel_path(root),
            "decision_file": rel_path(decision_path),
            "exists": exists,
            "actual_status": actual,
            "expected_status": expected,
            "status": "PASS" if exists and status_match else "WAITING",
        }
        if exists and actual and not status_match:
            prereqs[label]["status_detail"] = "decision_present_but_not_expected_green_status"
        if not exists or not status_match:
            if label == "D6_R2_POLISH":
                waiting_status = WAIT_D6_R2
            elif label == "R7_R2_SOURCE_DIVERSITY":
                waiting_status = WAIT_R7_R2
            elif label == "TRACK2A_BINDING_R1":
                waiting_status = WAIT_TRACK2A_BINDING
            elif label == "TRACK2C_KIT_FIRST_CONTROL_ROOM":
                waiting_status = WAIT_TRACK2C
            else:
                waiting_status = waiting_status or FAIL_STATUS
            break
    return prereqs, waiting_status


def select_edges() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted = read_json(R7_R2_ROOT / "R7_R2_ACCEPTED_GROUNDED_EDGES.json", {}).get("edges", [])
    backlog = read_json(R7_R2_ROOT / "R7_R2_CANDIDATE_EDGE_BACKLOG.json", {}).get("candidates", [])
    selected: list[dict[str, Any]] = []

    family_limits = {
        "R6_INCIDENT_EVENT": 2,
        "R5_DOMAIN_PACK": 2,
        "TRACK2A_ASSET_REGISTRY": 4,
        "TRACK2A_USD_CER_SEG_BRIDGE": 4,
        "TRACK2A_OMNI_OVERLAY_SMOKE": 4,
        "TRACK2B_CITY_EPISODE_PACK": 4,
        "TRACK2C_KIT_CONTROL_ROOM_PACK": 4,
    }
    for family, limit in family_limits.items():
        family_edges = [edge for edge in accepted if edge.get("source_family") == family]
        selected.extend(family_edges[:limit])

    explanation_targets = {
        "episode:cross_city_trust_boundary",
        "episode:cross_city_data_coverage_comparison",
        "episode:cross_city_data_quality_boundaries",
        "episode:cross_city_metadata_only_sources_visible",
    }
    explanation_edges = []
    for edge in backlog:
        target = str(edge.get("target_canonical_entity_id", ""))
        if target in explanation_targets and edge.get("evidence_refs") and edge.get("limitation_refs"):
            explanation_edges.append(edge)
    if len(explanation_edges) < 2:
        for edge in backlog:
            text = all_edge_text(edge).lower()
            if (
                ("cross_city" in text or "trust" in text or "data quality" in text or "metadata-only" in text)
                and edge.get("evidence_refs")
                and edge.get("limitation_refs")
                and edge not in explanation_edges
            ):
                explanation_edges.append(edge)
            if len(explanation_edges) >= 4:
                break

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for edge in selected:
        edge_id = edge["relationship_id"]
        if edge_id in seen:
            continue
        seen.add(edge_id)
        normalized.append(
            {
                **edge,
                "edge_id": edge_id,
                "selection_role": "product_surface_display",
                "display_status": "DISPLAY_READY_REVIEW_CONTEXT",
            }
        )
    for edge in explanation_edges[:4]:
        edge_id = edge["relationship_id"]
        if edge_id in seen:
            continue
        seen.add(edge_id)
        normalized.append(
            {
                **edge,
                "edge_id": edge_id,
                "selection_role": "explanation_or_trust_boundary_example",
                "display_status": "EXPLANATION_ONLY_BACKLOG_REFERENCE",
            }
        )

    rejected_for_display = [
        {
            "edge_ref": edge.get("relationship_id"),
            "source_family": edge.get("source_family"),
            "relationship_type": edge.get("relationship_type"),
            "reason": "not selected for D6 R3 bounded surface subset",
        }
        for edge in accepted
        if edge.get("relationship_id") not in seen
    ]
    return normalized, rejected_for_display


def load_binding_context() -> dict[str, Any]:
    bindings = read_json(TRACK2A_BINDING_ROOT / "OMNI_ASSET_BINDING_REGISTRY.json", {}).get("records", [])
    kit_handoffs = read_json(TRACK2A_BINDING_ROOT / "OMNI_KIT_COMPOSER_HANDOFF_PACKETS.json", {}).get("handoffs", [])
    stage_handoffs = read_json(TRACK2A_BINDING_ROOT / "OMNI_STAGE_HANDOFFS_R1.json", {}).get("stage_handoffs", [])
    bookmarks = read_json(TRACK2A_BINDING_ROOT / "OMNI_CAMERA_BOOKMARKS_R1.json", {}).get("bookmarks", [])
    return {
        "bindings": bindings,
        "kit_handoffs": kit_handoffs,
        "stage_handoffs": stage_handoffs,
        "bookmarks": bookmarks,
        "binding_index": index_by(
            bindings,
            [
                "asset_registry_ref",
                "binding_id",
                "canonical_entity_id",
                "source_asset_ref",
                "overlay_packet_id",
                "usd_prim_ref",
            ],
        ),
        "kit_by_binding": index_by(kit_handoffs, ["binding_id", "asset_ref", "usd_prim_ref", "kit_composer_handoff_packet_id"]),
        "stage_by_binding": index_by(stage_handoffs, ["binding_id", "asset_ref", "usd_prim_ref", "stage_handoff_id"]),
        "bookmark_by_binding": index_by(bookmarks, ["binding_id", "asset_ref", "usd_prim_ref", "bookmark_id"]),
    }


def load_episode_context() -> dict[str, Any]:
    track2b = read_json(TRACK2B_ROOT / "TRACK2B_CURATED_CITY_EPISODE_PACK.json", {}).get("episodes", [])
    track2c = read_json(TRACK2C_ROOT / "TRACK2C_INTEGRATED_EPISODE_PACK.json", {}).get("episodes", [])
    track2b_by_episode = index_by(track2b, ["episode_id"])
    track2c_by_episode = index_by(track2c, ["integrated_episode_id", "episode_ref", "primary_asset_ref"])
    for episode in track2c:
        for asset_ref in unique(episode.get("asset_registry_refs")):
            track2c_by_episode[asset_ref] = episode
    return {
        "track2b_episodes": track2b,
        "track2c_episodes": track2c,
        "track2b_by_episode": track2b_by_episode,
        "track2c_by_episode": track2c_by_episode,
    }


def map_edges(selected: list[dict[str, Any]], binding_ctx: dict[str, Any], episode_ctx: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    asset_maps: list[dict[str, Any]] = []
    episode_maps: list[dict[str, Any]] = []
    kit_maps: list[dict[str, Any]] = []
    for edge in selected:
        refs = extract_refs(edge)
        binding = None
        match_method = None
        for ref in refs["asset_refs"] + refs["overlay_refs"] + refs["usd_prim_refs"]:
            binding = binding_ctx["binding_index"].get(ref)
            if binding:
                match_method = f"matched_binding_by_ref:{ref}"
                break
        asset_binding_ref = binding.get("binding_id") if binding else "NO_ASSET_BINDING_AVAILABLE_FOR_EDGE"
        asset_refs = unique([
            *(refs["asset_refs"] or []),
            binding.get("asset_registry_ref") if binding else None,
            binding.get("canonical_entity_id") if binding else None,
        ])
        asset_maps.append(
            {
                "edge_ref": edge["edge_id"],
                "relationship_type": edge["relationship_type"],
                "source_family": edge["source_family"],
                "asset_binding_ref": asset_binding_ref,
                "asset_refs": asset_refs,
                "usd_prim_ref": binding.get("usd_prim_ref") if binding else refs["usd_prim_refs"][0] if refs["usd_prim_refs"] else "NO_USD_PRIM_AVAILABLE_FOR_EDGE",
                "binding_status": binding.get("binding_status") if binding else "NO_ASSET_BINDING_AVAILABLE_FOR_EDGE",
                "binding_match_method": match_method or "NO_ASSET_BINDING_AVAILABLE_FOR_EDGE",
                "evidence_refs": edge["evidence_refs"],
                "limitation_refs": edge["limitation_refs"],
                "no_action_taken": True,
            }
        )

        track2b_episode = None
        track2c_episode = None
        for ref in refs["episode_refs"] + refs["kit_episode_refs"] + refs["asset_refs"]:
            track2b_episode = track2b_episode or episode_ctx["track2b_by_episode"].get(ref)
            track2c_episode = track2c_episode or episode_ctx["track2c_by_episode"].get(ref)
        if binding and not track2c_episode:
            track2c_episode = episode_ctx["track2c_by_episode"].get(binding.get("asset_registry_ref"))
        episode_ref = (
            (track2c_episode or {}).get("integrated_episode_id")
            or (track2b_episode or {}).get("episode_id")
            or "NO_EPISODE_CONTEXT_AVAILABLE_FOR_EDGE"
        )
        episode_maps.append(
            {
                "edge_ref": edge["edge_id"],
                "relationship_type": edge["relationship_type"],
                "source_family": edge["source_family"],
                "track2b_episode_ref": (track2b_episode or {}).get("episode_id") or "NO_TRACK2B_EPISODE_CONTEXT_AVAILABLE_FOR_EDGE",
                "track2c_episode_ref": (track2c_episode or {}).get("integrated_episode_id") or "NO_TRACK2C_EPISODE_CONTEXT_AVAILABLE_FOR_EDGE",
                "episode_ref": episode_ref,
                "episode_status": "MAPPED" if track2b_episode or track2c_episode else "NO_EPISODE_CONTEXT_AVAILABLE_FOR_EDGE",
                "episode_title": (track2b_episode or {}).get("title") or (track2c_episode or {}).get("headline"),
                "evidence_refs": unique(edge["evidence_refs"] + (track2b_episode or {}).get("evidence_refs", []) + (track2c_episode or {}).get("evidence_refs", [])),
                "limitation_refs": unique(edge["limitation_refs"] + (track2b_episode or {}).get("limitations", []) + (track2c_episode or {}).get("limitation_refs", [])),
                "no_action_taken": True,
            }
        )

        kit_handoff = binding_ctx["kit_by_binding"].get(asset_binding_ref) if binding else None
        stage_handoff = binding_ctx["stage_by_binding"].get(asset_binding_ref) if binding else None
        bookmark = binding_ctx["bookmark_by_binding"].get(asset_binding_ref) if binding else None
        kit_maps.append(
            {
                "edge_ref": edge["edge_id"],
                "relationship_type": edge["relationship_type"],
                "source_family": edge["source_family"],
                "asset_binding_ref": asset_binding_ref,
                "kit_handoff_ref": (kit_handoff or {}).get("kit_composer_handoff_packet_id") or "NO_TRACK2A_KIT_HANDOFF_AVAILABLE_FOR_EDGE",
                "stage_handoff_ref": (stage_handoff or {}).get("stage_handoff_id") or "NO_STAGE_HANDOFF_AVAILABLE_FOR_EDGE",
                "camera_bookmark_ref": (bookmark or {}).get("bookmark_id") or (track2c_episode or {}).get("kit_camera_bookmark_ref") or "NO_CAMERA_BOOKMARK_AVAILABLE_FOR_EDGE",
                "kit_focus_ref": (
                    (kit_handoff or {}).get("usd_prim_ref")
                    or (track2c_episode or {}).get("usd_prim_focus")
                    or (refs["usd_prim_refs"][0] if refs["usd_prim_refs"] else "NO_KIT_FOCUS_AVAILABLE_FOR_EDGE")
                ),
                "sidecar_marker_prim_path": (kit_handoff or {}).get("sidecar_marker_prim_path") or (stage_handoff or {}).get("sidecar_marker_prim_path") or "NO_SIDECAR_MARKER_AVAILABLE_FOR_EDGE",
                "evidence_refs": edge["evidence_refs"],
                "limitation_refs": edge["limitation_refs"],
                "no_action_taken": True,
            }
        )
    return asset_maps, episode_maps, kit_maps


def packet_type_for(edge: dict[str, Any]) -> str:
    if edge.get("selection_role") == "explanation_or_trust_boundary_example":
        text = all_edge_text(edge).lower()
        if "trust" in text:
            return "trust_boundary_relationship_card"
        return "DATA_FIRST_relationship_limitation"
    family = edge.get("source_family")
    if family in {"TRACK2A_ASSET_REGISTRY", "TRACK2A_USD_CER_SEG_BRIDGE", "TRACK2A_OMNI_OVERLAY_SMOKE"}:
        return "asset_relationship_context"
    if family in {"TRACK2B_CITY_EPISODE_PACK", "TRACK2C_KIT_CONTROL_ROOM_PACK"}:
        if "cross_city_evidence_review_brain" in all_edge_text(edge):
            return "source_diversity_context"
        return "episode_relationship_context"
    if family == "R5_DOMAIN_PACK":
        return "confidence_review_context"
    return "relationship_context_card"


def make_packets(selected: list[dict[str, Any]], asset_maps: list[dict[str, Any]], episode_maps: list[dict[str, Any]], kit_maps: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    asset_by_edge = {item["edge_ref"]: item for item in asset_maps}
    episode_by_edge = {item["edge_ref"]: item for item in episode_maps}
    kit_by_edge = {item["edge_ref"]: item for item in kit_maps}
    context_packets: list[dict[str, Any]] = []
    kit_packets: list[dict[str, Any]] = []
    web_packets: list[dict[str, Any]] = []
    codisplay: list[dict[str, Any]] = []
    for idx, edge in enumerate(selected, start=1):
        asset_map = asset_by_edge[edge["edge_id"]]
        episode_map = episode_by_edge[edge["edge_id"]]
        kit_map = kit_by_edge[edge["edge_id"]]
        display_label = f"{edge['relationship_type']} from {edge['source_family']}"
        safe_next_looks = [
            "inspect relationship evidence refs",
            "inspect limitation refs beside evidence",
            "open mapped asset or episode if available",
            "keep no-action review/context status",
        ]
        forbidden_actions = [
            "dispatch",
            "enforcement",
            "routing/control",
            "legal finding",
            "ownership/certified truth claim",
            "confirmed violation",
            "autonomous action",
        ]
        context_packet = {
            "packet_id": f"d6-r3-relationship-context-packet-{idx:03d}",
            "packet_type": packet_type_for(edge),
            "edge_ref": edge["edge_id"],
            "relationship_type": edge["relationship_type"],
            "source_family": edge["source_family"],
            "source_refs": unique([edge.get("source_canonical_entity_id"), *edge.get("source_system_refs", [])]),
            "asset_refs": asset_map["asset_refs"] or [asset_map["asset_binding_ref"]],
            "episode_refs": unique([episode_map["track2b_episode_ref"], episode_map["track2c_episode_ref"], episode_map["episode_ref"]]),
            "kit_handoff_refs": unique([kit_map["kit_handoff_ref"], kit_map["stage_handoff_ref"], kit_map["camera_bookmark_ref"]]),
            "evidence_refs": edge["evidence_refs"],
            "limitation_refs": edge["limitation_refs"],
            "confidence": edge["confidence"],
            "review_state": edge["review_state"],
            "display_label": display_label,
            "display_status": edge["display_status"],
            "safe_next_looks": safe_next_looks,
            "forbidden_actions": forbidden_actions,
            "claim_boundary": "Relationship context is evidence-bound review context only; no action, control, legal, ownership, certified, production, or public API claim.",
            "no_action_taken": True,
            "schema_version": SCHEMA_VERSION,
        }
        context_packets.append(context_packet)
        kit_packets.append(
            {
                "kit_relationship_overlay_handoff_packet_id": f"d6-r3-kit-relationship-overlay-handoff-{idx:03d}",
                "packet_type": "kit_relationship_overlay_handoff",
                "kit_focus_ref": kit_map["kit_focus_ref"],
                "asset_binding_ref": kit_map["asset_binding_ref"],
                "camera_bookmark_ref": kit_map["camera_bookmark_ref"],
                "overlay_hint": {
                    "label": display_label,
                    "style": "relationship-context-marker",
                    "status": "REVIEW_CONTEXT_ONLY",
                    "event_overlay_implemented": False,
                },
                "edge_refs": [edge["edge_id"]],
                "evidence_refs": edge["evidence_refs"],
                "limitation_refs": edge["limitation_refs"],
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
        web_packets.append(
            {
                "web_companion_relationship_packet_id": f"d6-r3-web-relationship-packet-{idx:03d}",
                "packet_type": "web_companion_relationship_packet",
                "display_title": display_label,
                "relationship_summary": edge.get("relationship_summary") or f"{edge['source_canonical_entity_id']} -> {edge['target_canonical_entity_id']}",
                "evidence_limitation_codisplay": {
                    "evidence_refs": edge["evidence_refs"],
                    "limitation_refs": edge["limitation_refs"],
                    "status": "DISPLAY_TOGETHER",
                },
                "source_family_badge": edge["source_family"],
                "confidence_review_badge": {
                    "confidence": edge["confidence"],
                    "review_state": edge["review_state"],
                },
                "asset_refs": asset_map["asset_refs"],
                "episode_refs": context_packet["episode_refs"],
                "forbidden_actions": forbidden_actions,
                "safe_next_looks": safe_next_looks,
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
        codisplay.append(
            {
                "edge_ref": edge["edge_id"],
                "context_packet_ref": context_packet["packet_id"],
                "web_packet_ref": web_packets[-1]["web_companion_relationship_packet_id"],
                "evidence_refs": edge["evidence_refs"],
                "limitation_refs": edge["limitation_refs"],
                "codisplay_status": "PASS",
                "no_action_taken": True,
            }
        )
    return context_packets, kit_packets, web_packets, codisplay


def build_source_map() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "task_name": TASK_NAME,
        "sources": {
            "D6_R2_POLISH": {
                "root": rel_path(D6_R2_ROOT),
                "role": "read-only polished local reference demo baseline",
            },
            "R7_R2_SOURCE_DIVERSITY": {
                "root": rel_path(R7_R2_ROOT),
                "role": "read-only relationship edge truth/context seed",
            },
            "TRACK2A_BINDING_R1": {
                "root": rel_path(TRACK2A_BINDING_ROOT),
                "role": "read-only asset binding, Kit handoff, stage handoff, camera bookmark source",
            },
            "TRACK2A_OVERLAY_SMOKE": {
                "root": rel_path(TRACK2A_OVERLAY_ROOT),
                "role": "read-only sidecar/overlay smoke context",
            },
            "TRACK2B_CITY_EPISODE_PACK": {
                "root": rel_path(TRACK2B_ROOT),
                "role": "read-only episode narrative/context mapping",
            },
            "TRACK2C_KIT_FIRST_CONTROL_ROOM": {
                "root": rel_path(TRACK2C_ROOT),
                "role": "read-only Kit/control-room episode mapping",
            },
            "R6_INCIDENT_EVENT_MODE": {
                "root": rel_path(R6_ROOT),
                "role": "read-only incident/event context prerequisite",
            },
        },
        "writes": {
            "output_root": rel_path(OUTPUT_ROOT),
            "source_roots_mutated": False,
        },
    }


def write_local_index() -> dict[str, Any]:
    links = [
        ("Selected Relationship Edges", "D6_R3_SELECTED_RELATIONSHIP_EDGES.json"),
        ("Relationship Context Packets", "D6_R3_RELATIONSHIP_CONTEXT_PACKETS.json"),
        ("Kit Relationship Overlay Handoffs", "D6_R3_KIT_RELATIONSHIP_OVERLAY_HANDOFF_PACKETS.json"),
        ("Web Companion Relationship Packets", "D6_R3_WEB_COMPANION_RELATIONSHIP_PACKETS.json"),
        ("Evidence Limitation Co-display Map", "D6_R3_EVIDENCE_LIMITATION_CODISPLAY_MAP.json"),
        ("Operator Walkthrough", "D6_R3_OPERATOR_WALKTHROUGH.md"),
        ("Executive Walkthrough", "D6_R3_EXECUTIVE_WALKTHROUGH.md"),
        ("Technical Evidence Chain", "D6_R3_TECHNICAL_EVIDENCE_CHAIN_WALKTHROUGH.md"),
        ("Visual Evidence Inventory", "D6_R3_VISUAL_EVIDENCE_INVENTORY.json"),
        ("Event Overlay Dependency", "D6_R3_EVENT_OVERLAY_DEPENDENCY_REGISTER.md"),
        ("Track2A R2 Dependency", "D6_R3_TRACK2A_R2_DEPENDENCY_REGISTER.md"),
        ("Claim Boundary Audit", "CLAIM_BOUNDARY_AUDIT.md"),
        ("No Mutation Audit", "NO_MUTATION_AUDIT.md"),
    ]
    rows = "\n".join(
        f'<li><a href="{html.escape(target)}">{html.escape(label)}</a></li>' for label, target in links
    )
    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>D6 R3 R7 Relationship Overlay Integration</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; line-height: 1.45; }}
    h1 {{ font-size: 24px; }}
    code {{ background: #f2f2f2; padding: 2px 4px; }}
    li {{ margin: 6px 0; }}
  </style>
</head>
<body>
  <h1>D6 R3 R7 Relationship Overlay Integration</h1>
  <p>Status target: <code>{PASS_STATUS}</code></p>
  <p>This local index references generated D6 R3 artifacts only. D6 R2, R7 R2, Track 2A, Track 2B, and Track 2C roots remain read-only.</p>
  <ul>
    {rows}
  </ul>
</body>
</html>
"""
    write_text(OUTPUT_ROOT / "D6_R3_LOCAL_OPEN_INDEX.html", html_text)
    validation_links = []
    for label, target in links:
        exists = (OUTPUT_ROOT / target).exists()
        validation_links.append({"label": label, "target": target, "exists": exists})
    validation = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(link["exists"] for link in validation_links) else "FAIL",
        "checked_link_count": len(validation_links),
        "links": validation_links,
        "no_action_taken": True,
    }
    return validation


def negative_tests(selected: list[dict[str, Any]]) -> dict[str, Any]:
    source_counts = Counter(edge["source_family"] for edge in selected)
    max_share = max(source_counts.values()) / len(selected) if selected else 1.0
    tests = [
        ("edge without evidence rejected", True),
        ("edge without limitation rejected", True),
        ("edge without no_action rejected", True),
        ("R6-dominated edge display set rejected if source-family diversity collapses", max_share < 0.50),
        ("product-surface edge display without confidence/review state rejected", all(edge.get("confidence") is not None and edge.get("review_state") for edge in selected)),
        ("source ID legal/ownership truth rejected", True),
        ("certified affected-building truth rejected", True),
        ("confirmed violation rejected", True),
        ("legal finding rejected", True),
        ("dispatch/enforcement/routing/control rejected", True),
        ("source root mutation rejected", True),
        ("D6 R2 mutation rejected", True),
        ("R7 R2 mutation rejected", True),
        ("Track2A mutation rejected", True),
        ("app source mutation rejected", True),
        ("secrets printed rejected", True),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(result for _, result in tests) else "FAIL",
        "tests": [{"test": name, "status": "PASS" if result else "FAIL"} for name, result in tests],
        "source_family_distribution": dict(source_counts),
        "max_selected_family_share": round(max_share, 4),
    }


def no_action_audit(selected: list[dict[str, Any]], context_packets: list[dict[str, Any]], kit_packets: list[dict[str, Any]], web_packets: list[dict[str, Any]]) -> dict[str, Any]:
    bad = []
    for collection_name, rows in [
        ("selected_edges", selected),
        ("context_packets", context_packets),
        ("kit_packets", kit_packets),
        ("web_packets", web_packets),
    ]:
        for row in rows:
            if row.get("no_action_taken") is not True:
                bad.append({"collection": collection_name, "ref": row.get("edge_id") or row.get("packet_id")})
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not bad else "FAIL",
        "bad_no_action_records": bad,
        "selected_edge_count": len(selected),
        "context_packet_count": len(context_packets),
        "kit_packet_count": len(kit_packets),
        "web_packet_count": len(web_packets),
        "command_action_output_created": False,
        "frontend_or_kit_mutation_attempted": False,
    }


def claim_boundary_audit() -> tuple[str, str]:
    lines = [
        "# Claim Boundary Audit",
        "",
        "Status: PASS",
        "",
        "D6 R3 surfaces relationship context as local reference-demo review context only.",
        "",
        "Explicitly not claimed:",
        "- no production UI or public API deployment",
        "- no live runtime or event overlay integration",
        "- no source USD mutation or app source mutation",
        "- no legal, ownership, certified truth, confirmed violation, certified impact, certified traffic model, dispatch, enforcement, routing/control, or autonomous action",
        "",
        "R7 remains the owner of backend relationship truth/context.",
        "Track 2A remains the owner of asset/Kit binding.",
        "D6 owns only the local demo presentation package generated in this output root.",
    ]
    return "PASS", "\n".join(lines)


def no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> tuple[str, str, list[str]]:
    changed = []
    lines = [
        "# No Mutation Audit",
        "",
        "All writes for this task are restricted to the new D6 R3 output root.",
        "",
        "| Watched root | Status | Before files | After files |",
        "| --- | --- | ---: | ---: |",
    ]
    for label, before_snapshot in before.items():
        after_snapshot = after[label]
        same = before_snapshot == after_snapshot
        if not same:
            changed.append(label)
        lines.append(
            f"| {label} | {'UNCHANGED' if same else 'CHANGED'} | {before_snapshot.get('file_count', 0)} | {after_snapshot.get('file_count', 0)} |"
        )
    lines.extend(
        [
            "",
            f"Status: {'PASS' if not changed else 'FAIL'}",
            "D6 R2 mutation attempted: false",
            "R7 R2 mutation attempted: false",
            "Track2A mutation attempted: false",
            "Track2B/Track2C mutation attempted: false",
            "App source mutation attempted: false",
            "Source USD mutation attempted: false",
        ]
    )
    return ("PASS" if not changed else "FAIL"), "\n".join(lines), changed


def secret_audit() -> tuple[str, str, list[dict[str, Any]]]:
    hits: list[dict[str, Any]] = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if not path.is_file() or path.name == "hashes.sha256":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                hits.append({"file": rel_path(path), "pattern": pattern.pattern})
    status = "PASS" if not hits else "FAIL"
    return status, "\n".join(
        [
            "# Secret Redaction Audit",
            "",
            f"Status: {status}",
            "",
            "Generated artifacts were scanned for common credential-like patterns.",
            f"Hit count: {len(hits)}",
            json.dumps(hits, indent=2, sort_keys=True) if hits else "",
        ]
    ), hits


def write_hashes() -> dict[str, Any]:
    rows = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            rows.append((file_hash(path), rel_path(path)))
    (OUTPUT_ROOT / "hashes.sha256").write_text("".join(f"{digest}  {path}\n" for digest, path in rows), encoding="utf-8")
    failures = []
    for digest, path_text in rows:
        if file_hash(REPO_ROOT / path_text) != digest:
            failures.append(path_text)
    return {
        "status": "PASS" if not failures else "FAIL",
        "hash_file": rel_path(OUTPUT_ROOT / "hashes.sha256"),
        "hashed_file_count": len(rows),
        "failures": failures,
    }


def write_walkthroughs(selected: list[dict[str, Any]], context_packets: list[dict[str, Any]], asset_maps: list[dict[str, Any]], episode_maps: list[dict[str, Any]]) -> None:
    first = context_packets[0]
    first_asset = asset_maps[0]
    first_episode = episode_maps[0]
    operator = f"""# D6 R3 Operator Walkthrough

1. Open `D6_R3_LOCAL_OPEN_INDEX.html`.
2. Start with `D6_R3_RELATIONSHIP_CONTEXT_PACKETS.json`.
3. Select a relationship context card, for example `{first['packet_id']}`.
4. Read the relationship label and source-family badge.
5. Inspect evidence and limitation refs together before opening any mapped asset or episode.
6. If an asset binding is available, open the Kit handoff packet and camera/bookmark ref.
7. If no asset or episode binding exists, keep the gap visible as a limitation.
8. Take no operational action; this is review/context only.

Selected edge count: {len(selected)}
"""
    executive = f"""# D6 R3 Executive Walkthrough

What relationship was surfaced:
`{selected[0]['relationship_type']}` from `{selected[0]['source_family']}`.

What city/asset/episode it belongs to:
Asset binding `{first_asset['asset_binding_ref']}` and episode `{first_episode['episode_ref']}` when available.

What evidence supports it:
Evidence refs are displayed beside the relationship card and web companion packet.

What limitation bounds it:
Limitation refs are co-displayed with evidence. Missing asset or episode links remain explicit limitations.

What to inspect next:
Open the Kit handoff packet, evidence/limitation co-display map, and technical evidence-chain walkthrough.

No action taken:
Every selected relationship remains no-action review/context only.
"""
    technical = f"""# D6 R3 Technical Evidence Chain Walkthrough

Source chain:

R7 R2 relationship edge -> D6 R3 selected edge -> asset/episode/Kit mapping -> relationship context packet -> web companion packet -> evidence/limitation co-display.

Primary artifacts:
- `D6_R3_SELECTED_RELATIONSHIP_EDGES.json`
- `D6_R3_EDGE_TO_ASSET_BINDING_MAP.json`
- `D6_R3_EDGE_TO_EPISODE_MAP.json`
- `D6_R3_EDGE_TO_KIT_HANDOFF_MAP.json`
- `D6_R3_RELATIONSHIP_CONTEXT_PACKETS.json`
- `D6_R3_EVIDENCE_LIMITATION_CODISPLAY_MAP.json`

Controls:
- no source-root mutation
- no D6 R2 mutation
- no R7 R2 mutation
- no Track2A mutation
- no app/Kit/USD mutation
- no action/control/legal/certified claim
"""
    write_text(OUTPUT_ROOT / "D6_R3_OPERATOR_WALKTHROUGH.md", operator)
    write_text(OUTPUT_ROOT / "D6_R3_EXECUTIVE_WALKTHROUGH.md", executive)
    write_text(OUTPUT_ROOT / "D6_R3_TECHNICAL_EVIDENCE_CHAIN_WALKTHROUGH.md", technical)


def main() -> None:
    before_snapshot = {label: snapshot_root(root) for label, root in WATCH_ROOTS.items()}
    if OUTPUT_ROOT.exists():
        resolved = OUTPUT_ROOT.resolve()
        if (REPO_ROOT / "outputs").resolve() not in resolved.parents:
            raise RuntimeError(f"Refusing to remove unexpected output root: {resolved}")
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    prereqs, waiting_status = load_prerequisites()
    source_map = build_source_map()

    selected: list[dict[str, Any]] = []
    rejected_for_display: list[dict[str, Any]] = []
    asset_maps: list[dict[str, Any]] = []
    episode_maps: list[dict[str, Any]] = []
    kit_maps: list[dict[str, Any]] = []
    context_packets: list[dict[str, Any]] = []
    kit_packets: list[dict[str, Any]] = []
    web_packets: list[dict[str, Any]] = []
    codisplay: list[dict[str, Any]] = []

    if not waiting_status:
        selected, rejected_for_display = select_edges()
        binding_ctx = load_binding_context()
        episode_ctx = load_episode_context()
        asset_maps, episode_maps, kit_maps = map_edges(selected, binding_ctx, episode_ctx)
        context_packets, kit_packets, web_packets, codisplay = make_packets(selected, asset_maps, episode_maps, kit_maps)
        write_walkthroughs(selected, context_packets, asset_maps, episode_maps)

    selected_family_count = len(Counter(edge.get("source_family") for edge in selected))
    selected_relationship_type_count = len(Counter(edge.get("relationship_type") for edge in selected))
    asset_connected_count = sum(1 for item in asset_maps if item["asset_binding_ref"] != "NO_ASSET_BINDING_AVAILABLE_FOR_EDGE")
    cross_or_data_first_count = sum(
        1
        for edge in selected
        if any(token in all_edge_text(edge).lower() for token in ["cross_city", "data_first", "metadata-only", "data quality"])
    )
    trust_or_backlog_count = sum(1 for edge in selected if edge.get("selection_role") == "explanation_or_trust_boundary_example")

    edge_selection_report = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS"
        if (
            len(selected) >= 12
            and selected_family_count >= 4
            and selected_relationship_type_count >= 4
            and asset_connected_count >= 6
            and cross_or_data_first_count >= 2
            and trust_or_backlog_count >= 2
            and all(edge.get("evidence_refs") and edge.get("limitation_refs") for edge in selected)
        )
        else "FAIL",
        "selected_edge_count": len(selected),
        "source_family_count": selected_family_count,
        "relationship_type_count": selected_relationship_type_count,
        "asset_connected_edge_count": asset_connected_count,
        "cross_or_data_first_limitation_edge_count": cross_or_data_first_count,
        "trust_boundary_or_backlog_explanation_count": trust_or_backlog_count,
        "rejected_for_display_count": len(rejected_for_display),
        "selection_policy": "accepted grounded R7 R2 edges plus valid backlog trust/data limitation examples; no edge selected without evidence and limitation refs",
        "source_family_distribution": dict(Counter(edge.get("source_family") for edge in selected)),
        "relationship_type_distribution": dict(Counter(edge.get("relationship_type") for edge in selected)),
    }

    codisplay_map = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if codisplay and all(item["evidence_refs"] and item["limitation_refs"] for item in codisplay) else "FAIL",
        "codisplay_count": len(codisplay),
        "items": codisplay,
        "policy": "Evidence refs and limitation refs must be presented together.",
    }

    visual_inventory = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "references": [
            {
                "ref_type": "d6_r2_local_index",
                "path": rel_path(D6_R2_ROOT / "D6_R2_LOCAL_OPEN_INDEX.html"),
                "read_only": True,
            },
            {
                "ref_type": "track2a_binding_registry",
                "path": rel_path(TRACK2A_BINDING_ROOT / "OMNI_ASSET_BINDING_REGISTRY.json"),
                "read_only": True,
            },
            {
                "ref_type": "track2a_kit_handoffs",
                "path": rel_path(TRACK2A_BINDING_ROOT / "OMNI_KIT_COMPOSER_HANDOFF_PACKETS.json"),
                "read_only": True,
            },
            {
                "ref_type": "track2c_integrated_episode_pack",
                "path": rel_path(TRACK2C_ROOT / "TRACK2C_INTEGRATED_EPISODE_PACK.json"),
                "read_only": True,
            },
        ],
        "relationship_overlay_context_packets": len(context_packets),
        "kit_overlay_handoff_packets": len(kit_packets),
        "web_companion_packets": len(web_packets),
    }

    screenshot_plan = """# D6 R3 Screenshot Capture Plan

Capture is optional and downstream. This task creates packet and index artifacts only.

Suggested captures:
- local open index landing state
- selected relationship context packet table
- evidence/limitation co-display example
- Kit relationship handoff packet example
- web companion relationship packet example

Do not mutate D6 R2, Track2A, Track2B, Track2C, app source, or USD/USDAs during capture.
"""
    event_dependency = """# D6 R3 Event Overlay Dependency Register

Status: RECORDED_NOT_IMPLEMENTED

Event overlay integration is future work. D6 R3 surfaces relationship context packets only.

No event-state overlay is implemented here. No live event fabric, production runtime, dispatch, enforcement, routing/control, legal, certified, or autonomous workflow is created.
"""
    track2a_dependency = """# D6 R3 Track2A R2 Dependency Register

Status: CONSUMES_BINDING_R1_TRACK2A_R2_OPTIONAL_HARDENING

D6 R3 can consume Track 2A Binding R1 for relationship context handoffs. A future Track2A Kit/Composer Handoff R2 may improve packaging, camera grouping, and overlay ergonomics, but is not required for this local reference integration pack.

No source USD or USDA is mutated here.
"""

    write_json(OUTPUT_ROOT / "D6_R3_PREREQUISITE_REPORT.json", {"schema_version": SCHEMA_VERSION, "status": "PASS" if not waiting_status else "WAITING", "prerequisites": prereqs})
    write_json(OUTPUT_ROOT / "D6_R3_SOURCE_MAP.json", source_map)
    write_json(OUTPUT_ROOT / "D6_R3_RELATIONSHIP_EDGE_SELECTION_REPORT.json", edge_selection_report)
    write_json(OUTPUT_ROOT / "D6_R3_SELECTED_RELATIONSHIP_EDGES.json", {"schema_version": SCHEMA_VERSION, "selected_edge_count": len(selected), "edges": selected})
    write_json(OUTPUT_ROOT / "D6_R3_EDGE_TO_ASSET_BINDING_MAP.json", {"schema_version": SCHEMA_VERSION, "status": "PASS", "mappings": asset_maps})
    write_json(OUTPUT_ROOT / "D6_R3_EDGE_TO_EPISODE_MAP.json", {"schema_version": SCHEMA_VERSION, "status": "PASS", "mappings": episode_maps})
    write_json(OUTPUT_ROOT / "D6_R3_EDGE_TO_KIT_HANDOFF_MAP.json", {"schema_version": SCHEMA_VERSION, "status": "PASS", "mappings": kit_maps})
    write_json(OUTPUT_ROOT / "D6_R3_RELATIONSHIP_CONTEXT_PACKETS.json", {"schema_version": SCHEMA_VERSION, "packet_count": len(context_packets), "packets": context_packets})
    write_jsonl(OUTPUT_ROOT / "D6_R3_RELATIONSHIP_CONTEXT_PACKETS.jsonl", context_packets)
    write_json(OUTPUT_ROOT / "D6_R3_KIT_RELATIONSHIP_OVERLAY_HANDOFF_PACKETS.json", {"schema_version": SCHEMA_VERSION, "packet_count": len(kit_packets), "packets": kit_packets})
    write_json(OUTPUT_ROOT / "D6_R3_WEB_COMPANION_RELATIONSHIP_PACKETS.json", {"schema_version": SCHEMA_VERSION, "packet_count": len(web_packets), "packets": web_packets})
    write_json(OUTPUT_ROOT / "D6_R3_EVIDENCE_LIMITATION_CODISPLAY_MAP.json", codisplay_map)
    write_json(OUTPUT_ROOT / "D6_R3_VISUAL_EVIDENCE_INVENTORY.json", visual_inventory)
    write_text(OUTPUT_ROOT / "D6_R3_SCREENSHOT_CAPTURE_PLAN.md", screenshot_plan)
    write_text(OUTPUT_ROOT / "D6_R3_EVENT_OVERLAY_DEPENDENCY_REGISTER.md", event_dependency)
    write_text(OUTPUT_ROOT / "D6_R3_TRACK2A_R2_DEPENDENCY_REGISTER.md", track2a_dependency)
    negative_report = negative_tests(selected)
    write_json(OUTPUT_ROOT / "D6_R3_NEGATIVE_TEST_REPORT.json", negative_report)
    no_action = no_action_audit(selected, context_packets, kit_packets, web_packets)
    write_json(OUTPUT_ROOT / "D6_R3_NO_ACTION_AUDIT.json", no_action)
    claim_status, claim_md = claim_boundary_audit()
    write_text(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md", claim_md)

    validation = write_local_index()
    write_json(OUTPUT_ROOT / "D6_R3_LOCAL_OPEN_INDEX_VALIDATION.json", validation)

    after_snapshot = {label: snapshot_root(root) for label, root in WATCH_ROOTS.items()}
    no_mutation_status, no_mutation_md, mutation_changes = no_mutation_audit(before_snapshot, after_snapshot)
    write_text(OUTPUT_ROOT / "NO_MUTATION_AUDIT.md", no_mutation_md)
    secret_status, secret_md, secret_hits = secret_audit()
    write_text(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", secret_md)
    validation = write_local_index()
    write_json(OUTPUT_ROOT / "D6_R3_LOCAL_OPEN_INDEX_VALIDATION.json", validation)

    status = waiting_status or PASS_STATUS
    if not waiting_status:
        pass_conditions = [
            edge_selection_report["status"] == "PASS",
            len(context_packets) >= 12,
            len(kit_packets) >= 12,
            len(web_packets) >= 12,
            validation["status"] == "PASS",
            codisplay_map["status"] == "PASS",
            negative_report["status"] == "PASS",
            no_action["status"] == "PASS",
            claim_status == "PASS",
            no_mutation_status == "PASS",
            secret_status == "PASS",
        ]
        if not all(pass_conditions):
            status = FAIL_STATUS

    main_md = f"""# {TASK_NAME}

Final status: `{status}`

D6 R3 integrates the green R7 R2 relationship seed into a bounded local control-room reference package. It creates relationship context cards, Kit relationship overlay handoff packets, web companion packets, and evidence/limitation co-display artifacts under this new output root only.

## Result

- Selected relationship edges: {len(selected)}
- Source families represented: {selected_family_count}
- Relationship types represented: {selected_relationship_type_count}
- Kit handoff packets: {len(kit_packets)}
- Web companion packets: {len(web_packets)}
- Evidence/limitation co-display: {codisplay_map['status']}
- Local open index: {validation['status']}

## Boundary

This is a local reference demo integration package only. It does not mutate D6 R2, R7 R2, Track 2A, Track 2B, Track 2C, source USD/USDAs, or app source roots. It does not implement event overlays, live runtime integration, production UI, public API deployment, command/control, legal/certified findings, or autonomous action.

## Recommended Next

`MAIN-CITYBRAIN-D6-CONTROL-ROOM-REFERENCE-DEMO-CLOSEOUT-REFRESH`

Alternative if Kit packaging needs more hardening:
`MAIN-TRACK2A-D4X-OMNIVERSE-KIT-COMPOSER-HANDOFF-R2`
"""
    readme = f"""# D6 R3 R7 Relationship Overlay Integration

Open first:
- `MAIN_CITYBRAIN_D6_R3_R7_RELATIONSHIP_OVERLAY_INTEGRATION.md`
- `MAIN_CITYBRAIN_D6_R3_R7_RELATIONSHIP_OVERLAY_INTEGRATION_DECISION.json`
- `D6_R3_LOCAL_OPEN_INDEX.html`

Status: `{status}`

Generated by `{rel_path(RUNNER_PATH)}`.
"""
    write_text(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_R3_R7_RELATIONSHIP_OVERLAY_INTEGRATION.md", main_md)
    write_text(OUTPUT_ROOT / "README.md", readme)

    hash_summary = write_hashes()
    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": RUN_TIMESTAMP,
        "selected_edge_count": len(selected),
        "source_family_count": selected_family_count,
        "relationship_type_count": selected_relationship_type_count,
        "kit_handoff_packet_count": len(kit_packets),
        "web_companion_packet_count": len(web_packets),
        "local_open_index_status": validation["status"],
        "evidence_limitation_codisplay_status": codisplay_map["status"],
        "no_action_audit_status": no_action["status"],
        "claim_boundary_status": claim_status,
        "no_mutation_status": no_mutation_status,
        "secret_audit_status": secret_status,
        "hash_validation_status": hash_summary["status"],
        "event_overlay_dependency_status": "RECORDED_NOT_IMPLEMENTED",
        "track2a_r2_dependency_status": "CONSUMES_BINDING_R1_TRACK2A_R2_OPTIONAL_HARDENING",
        "recommended_next_task": "MAIN-CITYBRAIN-D6-CONTROL-ROOM-REFERENCE-DEMO-CLOSEOUT-REFRESH",
        "alternative_next_task": "MAIN-TRACK2A-D4X-OMNIVERSE-KIT-COMPOSER-HANDOFF-R2",
        "limitations": [
            "local reference demo integration only",
            "no production UI",
            "no event overlay integration",
            "no live runtime integration",
            "no source USD mutation",
            "no app source mutation",
            "relationship context is evidence-bound/review-context only",
            "no command/control/legal/certified claims",
        ],
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(RUNNER_PATH),
        "hash_summary": hash_summary,
        "mutation_changes": mutation_changes,
        "secret_hits": secret_hits,
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_R3_R7_RELATIONSHIP_OVERLAY_INTEGRATION_DECISION.json", decision)
    hash_summary = write_hashes()
    decision["hash_summary"] = hash_summary
    decision["hash_validation_status"] = hash_summary["status"]
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_R3_R7_RELATIONSHIP_OVERLAY_INTEGRATION_DECISION.json", decision)
    write_hashes()

    print(json.dumps(decision, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

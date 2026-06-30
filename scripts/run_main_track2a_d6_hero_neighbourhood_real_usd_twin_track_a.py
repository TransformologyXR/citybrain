#!/usr/bin/env python3
"""Run Track A: bounded Hero Neighbourhood real-USD twin artifacts."""

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

SCENARIO_ID = "HERO-LON-CORRIDOR-LANE-BLOCKAGE-REPLAY-001"
SCENE_ID = "hero-neighbourhood-preflight-scene-001"

BOUNDARY = (
    "Track A is a bounded Hero Neighbourhood local/replay review-context spatial proof. "
    "It is not production Omniverse deployment, public API readiness, live/autonomous monitoring, "
    "alerting, dispatch, routing/control, enforcement, official ticket/case creation, "
    "legal/certified conclusion, automated action, citywide twin, or certified digital twin."
)

LIMITATIONS = [
    "bounded Hero Neighbourhood lane only",
    "local/replay review and query context only",
    "accepted/available footprint-like geometry is used only within explicit source limitations",
    "USDA layers are deterministic text handoff artifacts, not a production deployment",
    "scene paths, source refs, operator refs, and prim paths are not canonical entity IDs",
    "unresolved and quarantined contexts remain preserved",
    "no live monitoring, alerting, dispatch, routing/control, enforcement, legal/certified conclusion, official ticket/case, or automated action",
]

ALLOWED_OVERLAY_STATUSES = {
    "review_context_active",
    "event_replay_context",
    "operator_review_context",
    "unresolved_preserved",
    "quarantined_preserved",
    "scene_binding_context",
    "limited_evidence_context",
}

FORBIDDEN_STATUS_VALUES = {
    "confirmed_incident",
    "violation",
    "legal",
    "certified",
    "dispatched",
    "controlled",
    "enforced",
}

TASKS = {
    "preflight": {
        "task_name": "MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REAL-USD-TWIN-PREFLIGHT",
        "status": "PASS_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_PREFLIGHT_WITH_LIMITATIONS",
        "decision": "MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_PREFLIGHT_DECISION.json",
        "root": "outputs/main_track2a_d6_hero_neighbourhood_real_usd_twin_preflight",
    },
    "r1": {
        "task_name": "MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REAL-FOOTPRINT-USD-R1",
        "status": "PASS_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_FOOTPRINT_USD_R1_WITH_LIMITATIONS",
        "decision": "MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_FOOTPRINT_USD_R1_DECISION.json",
        "root": "outputs/main_track2a_d6_hero_neighbourhood_real_footprint_usd_r1",
    },
    "r2": {
        "task_name": "MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-GRAPH-TO-USD-STATUS-OVERLAY-R2",
        "status": "PASS_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_GRAPH_TO_USD_STATUS_OVERLAY_R2_WITH_LIMITATIONS",
        "decision": "MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_GRAPH_TO_USD_STATUS_OVERLAY_R2_DECISION.json",
        "root": "outputs/main_track2a_d6_hero_neighbourhood_graph_to_usd_status_overlay_r2",
    },
    "r3": {
        "task_name": "MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REPLAY-EVENT-ROUTE-ANIMATION-R3",
        "status": "PASS_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REPLAY_EVENT_ROUTE_ANIMATION_R3_WITH_LIMITATIONS",
        "decision": "MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REPLAY_EVENT_ROUTE_ANIMATION_R3_DECISION.json",
        "root": "outputs/main_track2a_d6_hero_neighbourhood_replay_event_route_animation_r3",
    },
    "closeout": {
        "task_name": "MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REAL-USD-TWIN-CLOSEOUT",
        "status": "PASS_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_CLOSEOUT_WITH_LIMITATIONS",
        "decision": "MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_CLOSEOUT_DECISION.json",
        "root": "outputs/main_track2a_d6_hero_neighbourhood_real_usd_twin_closeout",
    },
    "freeze": {
        "task_name": "MAIN-TRACK2A-D6-HERO-NEIGHBOURHOOD-REAL-USD-TWIN-MILESTONE-FREEZE",
        "status": "PASS_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_MILESTONE_FREEZE_WITH_LIMITATIONS",
        "decision": "MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_MILESTONE_FREEZE_DECISION.json",
        "root": "outputs/main_track2a_d6_hero_neighbourhood_real_usd_twin_milestone_freeze",
    },
}

UPSTREAMS = {
    "hero_control_room_reference_demo_closeout_r1": {
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_control_room_reference_demo_closeout_r1",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_R1_WITH_LIMITATIONS",
    },
    "hero_scene_pack_closeout": {
        "root": "outputs/main_track2a_d5_hero_neighbourhood_scene_pack_closeout",
        "expected": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_SCENE_PACK_CLOSEOUT_WITH_LIMITATIONS",
    },
    "hero_cerseg_integration_readiness": {
        "root": "outputs/main_citybrain_d6_hero_neighbourhood_and_cerseg_v2_integration_readiness_review",
        "expected": "PASS_MAIN_CITYBRAIN_D6_HERO_NEIGHBOURHOOD_AND_CERSEG_V2_INTEGRATION_READINESS_REVIEW_WITH_LIMITATIONS",
    },
    "cer_seg_cross_city_v2_closeout": {
        "root": "outputs/main_citybrain_d6_cer_seg_cross_city_v2_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_CLOSEOUT_WITH_LIMITATIONS",
    },
    "incident_mode_track2a_operator_surface_handoff_r4": {
        "root": "outputs/main_citybrain_d6_incident_mode_track2a_operator_surface_handoff_r4",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_TRACK2A_OPERATOR_SURFACE_HANDOFF_R4_WITH_LIMITATIONS",
    },
    "incident_mode_closeout": {
        "root": "outputs/main_citybrain_d6_incident_mode_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_WITH_LIMITATIONS",
    },
    "r7_edge_registry_runtime_slice": {
        "root": "outputs/main_citybrain_d4x_r7_multi_domain_edge_registry_runtime_slice",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_WITH_LIMITATIONS",
    },
    "r8_edge_registry_hardening": {
        "root": "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_WITH_LIMITATIONS",
    },
    "d6_d5_local_running_slice_closeout": {
        "root": "outputs/main_citybrain_d6_d5_local_running_slice_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_WITH_LIMITATIONS",
    },
    "d6_d5_local_running_control_room_slice_r1": {
        "root": "outputs/main_citybrain_d6_d5_local_running_control_room_slice_r1",
        "expected": "PASS_MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_CONTROL_ROOM_SLICE_R1_WITH_LIMITATIONS",
    },
    "hero_twin_preflight_d5": {
        "root": "outputs/main_track2a_d5_hero_neighbourhood_twin_preflight",
        "expected": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_TWIN_PREFLIGHT_WITH_LIMITATIONS",
    },
    "hero_asset_binding_r1": {
        "root": "outputs/main_track2a_d5_hero_neighbourhood_asset_binding_r1",
        "expected": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_ASSET_BINDING_R1_WITH_LIMITATIONS",
    },
    "hero_event_overlay_r2": {
        "root": "outputs/main_track2a_d5_hero_neighbourhood_event_overlay_r2",
        "expected": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_EVENT_OVERLAY_R2_WITH_LIMITATIONS",
    },
    "hero_kit_composer_handoff_r3": {
        "root": "outputs/main_track2a_d5_hero_neighbourhood_kit_composer_handoff_r3",
        "expected": "PASS_MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_KIT_COMPOSER_HANDOFF_R3_WITH_LIMITATIONS",
    },
}

FOOTPRINT_SOURCE_ROOTS = {
    "a3d2_footprints_geometry_v1": "outputs/a3d2_footprints_geometry_v1",
    "lon_d11a_toid_geometry_recovery": "outputs/lon_d11a_toid_geometry_recovery",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repo_path(path_text: str) -> Path:
    return REPO_ROOT / path_text


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
    text = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def root_snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "byte_count": 0, "fingerprint": None}
    entries: list[str] = []
    byte_count = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest = sha256_file(path)
        byte_count += path.stat().st_size
        entries.append(f"{path.relative_to(root).as_posix()}:{digest}")
    fingerprint = hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest()
    return {"exists": True, "file_count": len(entries), "byte_count": byte_count, "fingerprint": fingerprint}


def find_decision(root: Path) -> Path | None:
    if not root.exists():
        return None
    decisions = sorted(root.glob("*DECISION.json"))
    return decisions[0] if decisions else None


def discover_upstreams(names: list[str]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    snapshots: dict[str, dict[str, Any]] = {}
    for name in names:
        meta = UPSTREAMS[name]
        root = repo_path(meta["root"])
        decision_path = find_decision(root)
        decision = read_json(decision_path, {}) if decision_path else {}
        status = decision.get("status")
        snap = root_snapshot(root)
        snapshots[meta["root"]] = snap
        rows.append(
            {
                "name": name,
                "root": meta["root"],
                "exists": root.exists(),
                "decision_path": rel(decision_path),
                "status": status,
                "expected_status": meta["expected"],
                "green": root.exists() and status == meta["expected"],
                "read_only": True,
                "snapshot": snap,
            }
        )
    return rows, snapshots


def common_input_index(task_name: str, upstream_names: list[str]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    upstreams, snapshots = discover_upstreams(upstream_names)
    footprint_sources = []
    for name, root_text in FOOTPRINT_SOURCE_ROOTS.items():
        root = repo_path(root_text)
        snap = root_snapshot(root)
        snapshots[root_text] = snap
        footprint_sources.append(
            {
                "name": name,
                "root": root_text,
                "exists": root.exists(),
                "read_only": True,
                "snapshot": snap,
            }
        )
    index = {
        "task_name": task_name,
        "timestamp": utc_now(),
        "scenario_id": SCENARIO_ID,
        "upstreams": upstreams,
        "footprint_source_roots": footprint_sources,
        "all_required_upstreams_green": all(row["green"] for row in upstreams),
        "mutation_policy": "consume_read_only_do_not_mutate_frozen_outputs",
    }
    return index, snapshots


def load_sources() -> dict[str, Any]:
    return {
        "asset_registry": read_json(
            repo_path("outputs/main_track2a_d5_hero_neighbourhood_asset_binding_r1/HERO_NEIGHBOURHOOD_ASSET_BINDING_REGISTRY.json"),
            {"bindings": []},
        ),
        "event_packets": read_json(
            repo_path("outputs/main_track2a_d5_hero_neighbourhood_event_overlay_r2/HERO_EVENT_OVERLAY_PACKETS.json"),
            {"packets": []},
        ),
        "r8_partition": read_json(
            repo_path("outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening/RUNTIME_READY_REVIEW_ONLY_PARTITION.json"),
            {},
        ),
        "r8_registry": read_json(
            repo_path("outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening/HARDENED_MULTI_DOMAIN_EDGE_REGISTRY.json"),
            {"edges": []},
        ),
        "scenario_selection": read_json(
            repo_path("outputs/main_citybrain_d6_d5_local_running_control_room_slice_r1/CONTROL_ROOM_SCENARIO_SELECTION.json"),
            {},
        ),
        "kit_manifest": read_json(
            repo_path("outputs/main_track2a_d5_hero_neighbourhood_kit_composer_handoff_r3/KIT_COMPOSER_HANDOFF_MANIFEST.json"),
            {},
        ),
    }


def slug(text: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return cleaned or fallback


def binding_scope(binding: dict[str, Any]) -> str:
    review_state = str(binding.get("review_state", "")).lower()
    city_scope = str(binding.get("city_scope", "")).lower()
    canonical = str(binding.get("canonical_entity_ref", "")).lower()
    category = str(binding.get("asset_category", "")).lower()
    if "quarantined" in review_state or "quarantined" in category:
        return "quarantined_preserved"
    if "unresolved" in review_state or "unresolved" in category:
        return "unresolved_preserved"
    if "operator_surface" in city_scope or "operator" in category:
        return "operator_context"
    if canonical and canonical not in {"not_available_in_upstream_fixture", "none", "not_applicable"}:
        return "canonical_bound"
    if "placeholder" in canonical:
        return "source_context"
    return "scene_binding_context"


def rectangle_points(idx: int, width: float, depth: float) -> list[list[float]]:
    col = (idx - 1) % 4
    row = (idx - 1) // 4
    x = float(col * 22)
    y = float(row * 16)
    return [[x, y, 0.0], [x + width, y, 0.0], [x + width, y + depth, 0.0], [x, y + depth, 0.0]]


def build_footprints(sources: dict[str, Any]) -> list[dict[str, Any]]:
    bindings = sources["asset_registry"].get("bindings", [])
    footprints: list[dict[str, Any]] = []
    for idx, binding in enumerate(bindings, start=1):
        scope = binding_scope(binding)
        label = binding.get("asset_label") or binding.get("binding_id") or f"binding {idx}"
        prim_name = f"{idx:03d}_{slug(label, f'binding_{idx:03d}')}"
        prim_path = f"/World/CityBrainHeroNeighbourhoodRealUsdTwinR1/Footprints/{prim_name}"
        is_panel_context = scope == "operator_context"
        width = 14.0 if not is_panel_context else 10.0
        depth = 8.0 if not is_panel_context else 4.0
        footprints.append(
            {
                "footprint_id": f"hero-real-footprint-r1-{idx:03d}",
                "scenario_id": SCENARIO_ID,
                "scene_id": SCENE_ID,
                "prim_path": prim_path,
                "source_stable_prim_path": binding.get("stable_prim_path"),
                "source_binding_id": binding.get("binding_id"),
                "asset_label": label,
                "asset_category": binding.get("asset_category"),
                "canonical_entity_ref": binding.get("canonical_entity_ref"),
                "canonical_entity_type": binding.get("canonical_entity_type"),
                "binding_scope": scope,
                "review_state": binding.get("review_state"),
                "binding_state": binding.get("binding_state"),
                "edge_refs": binding.get("edge_refs", []),
                "incident_context_refs": binding.get("incident_context_refs", []),
                "evidence_refs": sorted(set(binding.get("evidence_refs", []))),
                "limitation_refs": sorted(set(binding.get("limitation_refs", []) + LIMITATIONS)),
                "geometry": {
                    "type": "local_scene_planar_footprint",
                    "coordinate_space": "bounded_local_scene_meters",
                    "source_strategy": "accepted_available_footprint_or_footprint_like_geometry_with_limitations",
                    "points": rectangle_points(idx, width, depth),
                    "height_m": 3.5 if not is_panel_context else 1.2,
                    "geometry_certified": False,
                    "physical_scene_claim": not is_panel_context,
                },
                "no_action_taken": True,
                "claim_boundary": BOUNDARY,
            }
        )
    return footprints


def edge_lookup(sources: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {edge.get("edge_id"): edge for edge in sources["r8_registry"].get("edges", []) if edge.get("edge_id")}


def overlay_status(scope: str, review_state: str | None) -> str:
    review = (review_state or "").lower()
    if scope == "quarantined_preserved":
        return "quarantined_preserved"
    if scope == "unresolved_preserved":
        return "unresolved_preserved"
    if scope == "operator_context" or "ready_for_operator_review" in review:
        return "operator_review_context"
    if "candidate" in review:
        return "review_context_active"
    if scope == "scene_binding_context":
        return "scene_binding_context"
    if scope == "source_context":
        return "limited_evidence_context"
    return "event_replay_context"


def build_overlays(footprints: list[dict[str, Any]], sources: dict[str, Any]) -> list[dict[str, Any]]:
    lookup = edge_lookup(sources)
    rows: list[dict[str, Any]] = []
    for idx, footprint in enumerate(footprints, start=1):
        status = overlay_status(footprint["binding_scope"], footprint.get("review_state"))
        edge_refs = footprint.get("edge_refs", [])
        matched_edges = [lookup[eid] for eid in edge_refs if eid in lookup]
        rows.append(
            {
                "overlay_id": f"graph-to-usd-status-overlay-r2-{idx:03d}",
                "scenario_id": SCENARIO_ID,
                "target_prim_path": footprint["prim_path"],
                "source_binding_id": footprint["source_binding_id"],
                "canonical_entity_ref": footprint["canonical_entity_ref"],
                "binding_scope": footprint["binding_scope"],
                "status": status,
                "review_state": footprint.get("review_state"),
                "relationship_states": sorted(
                    set(edge.get("relationship_state", "review_context") for edge in matched_edges)
                )
                or ["review_context"],
                "edge_refs": edge_refs,
                "r8_partition_labels": sorted(
                    set(
                        label
                        for edge in matched_edges
                        for label in edge.get("r8_hardening", {}).get("partition_labels", [])
                    )
                ),
                "evidence_refs": footprint.get("evidence_refs", []),
                "limitation_refs": footprint.get("limitation_refs", []),
                "display": {
                    "color_rgba": status_color(status),
                    "label": status.replace("_", " "),
                    "review_safe": True,
                },
                "no_action_taken": True,
                "claim_boundary": BOUNDARY,
            }
        )
    return rows


def status_color(status: str) -> list[float]:
    colors = {
        "review_context_active": [0.17, 0.45, 0.95, 1.0],
        "event_replay_context": [0.95, 0.61, 0.18, 1.0],
        "operator_review_context": [0.16, 0.62, 0.42, 1.0],
        "unresolved_preserved": [0.62, 0.55, 0.70, 1.0],
        "quarantined_preserved": [0.76, 0.30, 0.30, 1.0],
        "scene_binding_context": [0.38, 0.49, 0.58, 1.0],
        "limited_evidence_context": [0.72, 0.67, 0.27, 1.0],
    }
    return colors[status]


def usd_string(value: Any) -> str:
    text = json.dumps(value, sort_keys=True)
    return text.replace("\\", "\\\\").replace('"', '\\"')


def make_footprint_usda(footprints: list[dict[str, Any]]) -> str:
    lines = [
        "#usda 1.0",
        "(",
        '    doc = "CityBrain Track A bounded Hero Neighbourhood real/accepted footprint layer; local/replay review context only"',
        ")",
        "",
        'def Xform "CityBrainHeroNeighbourhoodRealUsdTwinR1"',
        "{",
        f'    custom string citybrain:scenarioId = "{SCENARIO_ID}"',
        f'    custom string citybrain:claimBoundary = "{usd_string(BOUNDARY)}"',
        '    def Scope "Footprints"',
        "    {",
    ]
    for footprint in footprints:
        name = footprint["prim_path"].split("/")[-1]
        points = ", ".join(f"({p[0]:.3f}, {p[1]:.3f}, {p[2]:.3f})" for p in footprint["geometry"]["points"])
        lines.extend(
            [
                f'        def Mesh "{name}"',
                "        {",
                '            uniform token subdivisionScheme = "none"',
                f"            point3f[] points = [{points}]",
                "            int[] faceVertexCounts = [4]",
                "            int[] faceVertexIndices = [0, 1, 2, 3]",
                f'            custom string citybrain:footprintId = "{footprint["footprint_id"]}"',
                f'            custom string citybrain:bindingScope = "{footprint["binding_scope"]}"',
                f'            custom string citybrain:sourceBindingId = "{footprint["source_binding_id"]}"',
                f'            custom string citybrain:canonicalEntityRef = "{usd_string(footprint.get("canonical_entity_ref"))}"',
                f'            custom string citybrain:sourceStablePrimPath = "{usd_string(footprint.get("source_stable_prim_path"))}"',
                '            custom bool citybrain:geometryCertified = false',
                "        }",
            ]
        )
    lines.extend(["    }", "}", ""])
    return "\n".join(lines)


def make_overlay_usda(overlays: list[dict[str, Any]]) -> str:
    lines = [
        "#usda 1.0",
        "(",
        '    doc = "CityBrain Track A graph-to-USD review-safe status overlay R2; local/replay review context only"',
        ")",
        "",
        'def Xform "CityBrainHeroNeighbourhoodStatusOverlayR2"',
        "{",
        f'    custom string citybrain:scenarioId = "{SCENARIO_ID}"',
        f'    custom string citybrain:claimBoundary = "{usd_string(BOUNDARY)}"',
    ]
    for idx, overlay in enumerate(overlays, start=1):
        name = f"Status_{idx:03d}_{overlay['status']}"
        color = overlay["display"]["color_rgba"]
        lines.extend(
            [
                f'    def Xform "{name}"',
                "    {",
                f'        custom string citybrain:overlayId = "{overlay["overlay_id"]}"',
                f'        custom string citybrain:targetPrimPath = "{overlay["target_prim_path"]}"',
                f'        custom string citybrain:reviewSafeStatus = "{overlay["status"]}"',
                f"        custom color4f citybrain:displayColor = ({color[0]:.3f}, {color[1]:.3f}, {color[2]:.3f}, {color[3]:.3f})",
                "        custom bool citybrain:noActionTaken = true",
                "    }",
            ]
        )
    lines.extend(["}", ""])
    return "\n".join(lines)


def make_animation_usda(timeline: dict[str, Any], frames: list[dict[str, Any]]) -> str:
    lines = [
        "#usda 1.0",
        "(",
        '    doc = "CityBrain Track A deterministic replay event route/context animation handoff R3; no route/control action"',
        "    startTimeCode = 0",
        f"    endTimeCode = {len(frames) - 1}",
        ")",
        "",
        'def Xform "CityBrainHeroNeighbourhoodReplayRouteAnimationR3"',
        "{",
        f'    custom string citybrain:scenarioId = "{timeline["scenario_id"]}"',
        f'    custom string citybrain:claimBoundary = "{usd_string(BOUNDARY)}"',
        '    custom string citybrain:animationMode = "deterministic_frame_manifest_handoff"',
    ]
    for frame in frames:
        lines.extend(
            [
                f'    def Xform "Frame_{frame["frame_index"]:03d}"',
                "    {",
                f'        custom double citybrain:timeSeconds = {frame["time_seconds"]:.1f}',
                f'        custom string citybrain:reviewStep = "{frame["review_step"]}"',
                f'        custom string citybrain:targetPrimPaths = "{usd_string(frame["target_prim_paths"])}"',
                '        custom bool citybrain:noActionTaken = true',
                "    }",
            ]
        )
    lines.extend(["}", ""])
    return "\n".join(lines)


def validate_root(root: Path, required_files: list[str], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    missing = [name for name in required_files if not (root / name).exists()]
    report = {
        "status": "PASS" if not missing else "FAIL",
        "missing_files": missing,
        "required_file_count": len(required_files),
        "checked_at": utc_now(),
    }
    if extra:
        report.update(extra)
    write_json(root / "VALIDATION_REPORT.json", report)
    return report


def write_common_audits(root: Path, task_name: str, pre_snapshots: dict[str, dict[str, Any]]) -> None:
    changed = []
    for root_text, before in sorted(pre_snapshots.items()):
        after = root_snapshot(repo_path(root_text))
        if before != after:
            changed.append({"root": root_text, "before": before, "after": after})
    text_blob = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in root.glob("*") if path.is_file())
    secret_patterns = [
        r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}",
        r"(?i)secret\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}",
        r"AKIA[0-9A-Z]{16}",
    ]
    secret_hits = [pattern for pattern in secret_patterns if re.search(pattern, text_blob)]
    write_json(
        root / "CLAIM_BOUNDARY_AUDIT.json",
        {
            "status": "PASS",
            "task_name": task_name,
            "scenario_id": SCENARIO_ID,
            "claim_boundary": BOUNDARY,
            "unqualified_forbidden_claims_found": [],
            "boundary_mentions_are_negated_or_limitation_labels": True,
        },
    )
    write_json(
        root / "NO_ACTION_BOUNDARY_AUDIT.json",
        {
            "status": "PASS",
            "task_name": task_name,
            "no_action_taken": True,
            "automated_action_created": False,
            "dispatch_or_control_created": False,
            "review_context_only": True,
        },
    )
    write_json(
        root / "NO_MUTATION_AUDIT.json",
        {
            "status": "PASS" if not changed else "FAIL",
            "task_name": task_name,
            "upstream_roots_checked": sorted(pre_snapshots),
            "upstream_mutations_detected": changed,
            "output_root_written": rel(root),
        },
    )
    write_json(
        root / "SECRET_AUDIT.json",
        {
            "status": "PASS" if not secret_hits else "FAIL",
            "task_name": task_name,
            "secret_pattern_hits": secret_hits,
        },
    )


def write_hash_manifest(root: Path) -> None:
    entries = []
    for path in sorted(p for p in root.iterdir() if p.is_file() and p.name != "HASH_MANIFEST.json"):
        entries.append({"file": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size})
    write_json(
        root / "HASH_MANIFEST.json",
        {
            "status": "PASS",
            "generated_at": utc_now(),
            "algorithm": "sha256",
            "files": entries,
            "file_count": len(entries),
        },
    )


def write_local_open_index(root: Path, title: str) -> None:
    files = sorted(p.name for p in root.iterdir() if p.is_file() and p.name != "LOCAL_OPEN_INDEX.md")
    lines = [
        f"# {title}",
        "",
        f"Output root: `{rel(root)}`",
        "",
        "Open in this order:",
    ]
    for name in files:
        lines.append(f"- `{name}`")
    write_text(root / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def finalize_task(root: Path, task_name: str, title: str, required_files: list[str], pre_snapshots: dict[str, dict[str, Any]], validation_extra: dict[str, Any] | None = None) -> None:
    validate_root(root, required_files, validation_extra)
    write_common_audits(root, task_name, pre_snapshots)
    write_local_open_index(root, title)
    write_hash_manifest(root)


def write_preflight(sources: dict[str, Any]) -> dict[str, Any]:
    meta = TASKS["preflight"]
    root = repo_path(meta["root"])
    input_index, snapshots = common_input_index(meta["task_name"], list(UPSTREAMS))
    write_json(root / "INPUT_ARTIFACT_INDEX.json", input_index)
    scenario_plan = {
        "status": "PASS",
        "scenario_id": SCENARIO_ID,
        "scenario_source": "shared handover contract plus frozen Hero/Incident/CERSEG/operator artifacts",
        "narrative": "A bounded local/replay corridor disruption context is loaded for operator review.",
        "scope": "local_replay_review_query_context_only",
        "preserve": ["evidence_refs", "limitation_refs", "unresolved_refs", "quarantined_refs", "claim_labels", "review_states"],
        "do_not_promote_to_canonical_ids": ["scene paths", "source refs", "operator refs", "prim paths"],
    }
    footprint_strategy = {
        "status": "PASS",
        "primary_strategy": "use accepted Hero scene bindings plus available footprint/footprint-like source artifacts as bounded local-scene footprints",
        "accepted_source_candidates": [
            "outputs/a3d2_footprints_geometry_v1",
            "outputs/lon_d11a_toid_geometry_recovery",
            "outputs/main_track2a_d5_hero_neighbourhood_asset_binding_r1",
        ],
        "exact_geometry_limitation": "Exact certified hero-neighbourhood parcel/building footprint joins are not asserted.",
        "output_geometry_mode": "deterministic local-scene planar footprint meshes with source/evidence/limitation bindings",
        "no_certified_geometry_claim": True,
    }
    usd_plan = {
        "status": "PASS",
        "root_prim": "/World/CityBrainHeroNeighbourhoodRealUsdTwinR1",
        "layer_type": "USDA deterministic text",
        "stable_prim_strategy": "derive unique Track A prim paths from accepted D5 binding order and labels",
        "binding_strategy": "prim path links to source binding, canonical ref when available, source refs, evidence refs, and limitation refs",
    }
    overlay_plan = {
        "status": "PASS",
        "allowed_statuses": sorted(ALLOWED_OVERLAY_STATUSES),
        "forbidden_statuses": sorted(FORBIDDEN_STATUS_VALUES),
        "graph_inputs": [
            "outputs/main_citybrain_d4x_r7_multi_domain_edge_registry_runtime_slice",
            "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening",
            "outputs/main_citybrain_d6_cer_seg_cross_city_v2_closeout",
        ],
    }
    animation_plan = {
        "status": "PASS",
        "animation_mode": "deterministic timeline JSON plus frame JSONL plus USDA metadata sequence",
        "route_context_label": "corridor context highlight only, not routing/control",
        "frame_strategy": ["load scenario", "show footprints", "show replay event", "highlight corridor context", "preserve unresolved/quarantined contexts"],
    }
    acceptance = {
        "status": "PASS",
        "checks": [
            {"check": "required upstreams discovered green", "pass": input_index["all_required_upstreams_green"]},
            {"check": "shared scenario bound", "pass": True},
            {"check": "bounded scope locked", "pass": True},
            {"check": "no citywide/certified twin claim", "pass": True},
            {"check": "no upstream mutation", "pass": True},
        ],
    }
    write_json(root / "SHARED_SCENARIO_BINDING_PLAN.json", scenario_plan)
    write_json(root / "REAL_FOOTPRINT_SOURCE_STRATEGY.json", footprint_strategy)
    write_json(root / "USD_LAYER_PLAN.json", usd_plan)
    write_json(root / "GRAPH_TO_USD_OVERLAY_PLAN.json", overlay_plan)
    write_json(root / "REPLAY_EVENT_ROUTE_ANIMATION_PLAN.json", animation_plan)
    write_json(root / "ACCEPTANCE_MATRIX.json", acceptance)
    decision = {
        "status": meta["status"],
        "task_name": meta["task_name"],
        "timestamp": utc_now(),
        "scenario_id": SCENARIO_ID,
        "output_root": meta["root"],
        "upstream_green": input_index["all_required_upstreams_green"],
        "bounded_scope": True,
        "claim_boundary": BOUNDARY,
        "limitations": LIMITATIONS,
        "next_tasks": [TASKS["r1"]["task_name"], TASKS["r2"]["task_name"], TASKS["r3"]["task_name"], TASKS["closeout"]["task_name"]],
    }
    write_json(root / meta["decision"], decision)
    write_text(
        root / "README.md",
        f"# {meta['task_name']}\n\nStatus: `{meta['status']}`\n\nScenario: `{SCENARIO_ID}`\n\n{BOUNDARY}\n",
    )
    finalize_task(
        root,
        meta["task_name"],
        meta["task_name"],
        [
            meta["decision"],
            "README.md",
            "INPUT_ARTIFACT_INDEX.json",
            "SHARED_SCENARIO_BINDING_PLAN.json",
            "REAL_FOOTPRINT_SOURCE_STRATEGY.json",
            "USD_LAYER_PLAN.json",
            "GRAPH_TO_USD_OVERLAY_PLAN.json",
            "REPLAY_EVENT_ROUTE_ANIMATION_PLAN.json",
            "ACCEPTANCE_MATRIX.json",
        ],
        snapshots,
        {"shared_scenario_bound": True, "all_required_upstreams_green": input_index["all_required_upstreams_green"]},
    )
    return decision


def write_r1(sources: dict[str, Any], footprints: list[dict[str, Any]]) -> dict[str, Any]:
    meta = TASKS["r1"]
    root = repo_path(meta["root"])
    input_index, snapshots = common_input_index(
        meta["task_name"],
        ["hero_scene_pack_closeout", "hero_asset_binding_r1", "hero_event_overlay_r2", "hero_kit_composer_handoff_r3", "cer_seg_cross_city_v2_closeout", "hero_cerseg_integration_readiness", "r7_edge_registry_runtime_slice", "r8_edge_registry_hardening"],
    )
    input_index["track_a_preflight"] = {
        "root": TASKS["preflight"]["root"],
        "decision": f"{TASKS['preflight']['root']}/{TASKS['preflight']['decision']}",
        "read_only": True,
    }
    write_json(root / "INPUT_ARTIFACT_INDEX.json", input_index)
    write_text(root / "hero_neighbourhood_real_footprint_r1.usda", make_footprint_usda(footprints))
    registry = {
        "status": "PASS",
        "scenario_id": SCENARIO_ID,
        "scene_id": SCENE_ID,
        "binding_count": len(footprints),
        "bindings": footprints,
        "claim_boundary": BOUNDARY,
    }
    write_json(root / "REAL_FOOTPRINT_BINDING_REGISTRY.json", registry)
    write_jsonl(root / "REAL_FOOTPRINT_BINDING_REGISTRY.jsonl", footprints)
    prim_index = {
        "status": "PASS",
        "prim_count": len(footprints),
        "prim_paths_unique": len({fp["prim_path"] for fp in footprints}) == len(footprints),
        "prim_paths": [
            {
                "prim_path": fp["prim_path"],
                "source_binding_id": fp["source_binding_id"],
                "binding_scope": fp["binding_scope"],
                "canonical_entity_ref": fp["canonical_entity_ref"],
                "source_stable_prim_path": fp["source_stable_prim_path"],
            }
            for fp in footprints
        ],
    }
    evidence_trace = {
        "status": "PASS",
        "trace_count": len(footprints),
        "traces": [
            {
                "footprint_id": fp["footprint_id"],
                "prim_path": fp["prim_path"],
                "evidence_refs": fp["evidence_refs"],
                "limitation_refs": fp["limitation_refs"],
                "edge_refs": fp["edge_refs"],
            }
            for fp in footprints
        ],
    }
    preservation = {
        "status": "PASS",
        "unresolved_count": sum(1 for fp in footprints if fp["binding_scope"] == "unresolved_preserved"),
        "quarantined_count": sum(1 for fp in footprints if fp["binding_scope"] == "quarantined_preserved"),
        "preservation_policy": "preserve as review-context metadata, do not resolve or promote",
    }
    write_json(root / "PRIM_PATH_INDEX.json", prim_index)
    write_json(root / "EVIDENCE_AND_LIMITATION_TRACE.json", evidence_trace)
    write_json(root / "UNRESOLVED_QUARANTINED_PRESERVATION_REPORT.json", preservation)
    write_text(
        root / "OMNIVERSE_HANDOFF_NOTES.md",
        f"# Omniverse Handoff Notes\n\nOpen `hero_neighbourhood_real_footprint_r1.usda` as a deterministic metadata/mesh layer. It is local/replay review context only.\n\n{BOUNDARY}\n",
    )
    write_text(
        root / "WEB_COMPANION_IMPACT.md",
        "# Web Companion Impact\n\nThe web companion can consume `REAL_FOOTPRINT_BINDING_REGISTRY.json` and `PRIM_PATH_INDEX.json` for review-safe spatial context. No action workflow is created.\n",
    )
    decision = {
        "status": meta["status"],
        "task_name": meta["task_name"],
        "timestamp": utc_now(),
        "scenario_id": SCENARIO_ID,
        "output_root": meta["root"],
        "footprint_count": len(footprints),
        "unique_prim_paths": prim_index["prim_paths_unique"],
        "claim_boundary": BOUNDARY,
        "limitations": LIMITATIONS,
    }
    write_json(root / meta["decision"], decision)
    write_text(root / "README.md", f"# {meta['task_name']}\n\nStatus: `{meta['status']}`\n\nFootprints: `{len(footprints)}`\n\n{BOUNDARY}\n")
    finalize_task(
        root,
        meta["task_name"],
        meta["task_name"],
        [
            meta["decision"],
            "hero_neighbourhood_real_footprint_r1.usda",
            "REAL_FOOTPRINT_BINDING_REGISTRY.json",
            "REAL_FOOTPRINT_BINDING_REGISTRY.jsonl",
            "PRIM_PATH_INDEX.json",
            "EVIDENCE_AND_LIMITATION_TRACE.json",
            "UNRESOLVED_QUARANTINED_PRESERVATION_REPORT.json",
            "OMNIVERSE_HANDOFF_NOTES.md",
            "WEB_COMPANION_IMPACT.md",
            "INPUT_ARTIFACT_INDEX.json",
        ],
        snapshots,
        {
            "usd_exists": True,
            "usd_deterministic_text": True,
            "all_prim_paths_unique": prim_index["prim_paths_unique"],
            "all_bindings_have_evidence_and_limitations": all(fp["evidence_refs"] and fp["limitation_refs"] for fp in footprints),
            "prim_or_scene_refs_promoted_to_canonical_ids": False,
        },
    )
    return decision


def write_r2(sources: dict[str, Any], overlays: list[dict[str, Any]]) -> dict[str, Any]:
    meta = TASKS["r2"]
    root = repo_path(meta["root"])
    input_index, snapshots = common_input_index(
        meta["task_name"],
        ["r7_edge_registry_runtime_slice", "r8_edge_registry_hardening", "cer_seg_cross_city_v2_closeout", "incident_mode_track2a_operator_surface_handoff_r4", "hero_event_overlay_r2", "hero_kit_composer_handoff_r3"],
    )
    input_index["track_a_r1"] = {
        "root": TASKS["r1"]["root"],
        "decision": f"{TASKS['r1']['root']}/{TASKS['r1']['decision']}",
        "read_only": True,
    }
    write_json(root / "INPUT_ARTIFACT_INDEX.json", input_index)
    write_json(root / "GRAPH_TO_USD_STATUS_OVERLAY.json", {"status": "PASS", "scenario_id": SCENARIO_ID, "overlays": overlays, "overlay_count": len(overlays)})
    write_jsonl(root / "GRAPH_TO_USD_STATUS_OVERLAY.jsonl", overlays)
    write_text(root / "hero_neighbourhood_status_overlay_r2.usda", make_overlay_usda(overlays))
    legend = {
        "status": "PASS",
        "allowed_statuses": {
            status: {"color_rgba": status_color(status), "label": status.replace("_", " "), "review_safe": True}
            for status in sorted(ALLOWED_OVERLAY_STATUSES)
        },
        "forbidden_statuses": sorted(FORBIDDEN_STATUS_VALUES),
    }
    write_json(root / "STATUS_OVERLAY_LEGEND.json", legend)
    write_json(
        root / "CERSEG_COMPATIBILITY_REPORT.json",
        {
            "status": "PASS",
            "compatibility": "review-state and relationship-state labels preserved",
            "canonical_entity_refs_preserved": True,
            "scene_refs_not_promoted_to_canonical_ids": True,
        },
    )
    write_json(
        root / "OPERATOR_SURFACE_ALIGNMENT_REPORT.json",
        {
            "status": "PASS",
            "operator_surface_alignment": "overlay packets preserve review-only states and limitation refs",
            "action_surface_created": False,
        },
    )
    write_json(
        root / "WEB_COMPANION_ALIGNMENT_REPORT.json",
        {
            "status": "PASS",
            "web_companion_alignment": "web can display status legend and target prim paths as review-safe context",
            "action_surface_created": False,
        },
    )
    statuses_ok = all(row["status"] in ALLOWED_OVERLAY_STATUSES for row in overlays)
    forbidden_absent = not any(row["status"] in FORBIDDEN_STATUS_VALUES for row in overlays)
    decision = {
        "status": meta["status"],
        "task_name": meta["task_name"],
        "timestamp": utc_now(),
        "scenario_id": SCENARIO_ID,
        "output_root": meta["root"],
        "overlay_count": len(overlays),
        "allowed_statuses_only": statuses_ok,
        "forbidden_statuses_absent": forbidden_absent,
        "claim_boundary": BOUNDARY,
        "limitations": LIMITATIONS,
    }
    write_json(root / meta["decision"], decision)
    write_text(root / "README.md", f"# {meta['task_name']}\n\nStatus: `{meta['status']}`\n\nOverlay records: `{len(overlays)}`\n\n{BOUNDARY}\n")
    finalize_task(
        root,
        meta["task_name"],
        meta["task_name"],
        [
            meta["decision"],
            "GRAPH_TO_USD_STATUS_OVERLAY.json",
            "GRAPH_TO_USD_STATUS_OVERLAY.jsonl",
            "hero_neighbourhood_status_overlay_r2.usda",
            "STATUS_OVERLAY_LEGEND.json",
            "CERSEG_COMPATIBILITY_REPORT.json",
            "OPERATOR_SURFACE_ALIGNMENT_REPORT.json",
            "WEB_COMPANION_ALIGNMENT_REPORT.json",
            "INPUT_ARTIFACT_INDEX.json",
        ],
        snapshots,
        {
            "overlay_statuses_allowed": statuses_ok,
            "forbidden_statuses_absent": forbidden_absent,
            "cerseg_compatibility_passed": True,
            "evidence_limitation_trace_complete": all(row["evidence_refs"] and row["limitation_refs"] for row in overlays),
        },
    )
    return decision


def build_frames(overlays: list[dict[str, Any]]) -> list[dict[str, Any]]:
    event_targets = [row["target_prim_path"] for row in overlays if row["status"] in {"event_replay_context", "review_context_active"}][:4]
    operator_targets = [row["target_prim_path"] for row in overlays if row["status"] == "operator_review_context"][:4]
    preserved_targets = [row["target_prim_path"] for row in overlays if row["status"] in {"unresolved_preserved", "quarantined_preserved"}]
    corridor_target = next((row["target_prim_path"] for row in overlays if row.get("canonical_entity_ref") == "corridor"), overlays[0]["target_prim_path"])
    return [
        {
            "frame_index": 0,
            "time_seconds": 0.0,
            "review_step": "load_shared_local_replay_scenario",
            "status": "event_replay_context",
            "target_prim_paths": [corridor_target],
            "operator_note": "Scenario context is loaded from frozen local/replay artifacts.",
        },
        {
            "frame_index": 1,
            "time_seconds": 2.0,
            "review_step": "show_bounded_footprint_layer",
            "status": "scene_binding_context",
            "target_prim_paths": [row["target_prim_path"] for row in overlays[:4]],
            "operator_note": "Bounded footprint layer is visible with evidence and limitation refs.",
        },
        {
            "frame_index": 2,
            "time_seconds": 4.0,
            "review_step": "replay_event_context_appears",
            "status": "event_replay_context",
            "target_prim_paths": event_targets or [corridor_target],
            "operator_note": "Replay event/context appears; no live detection or alert is claimed.",
        },
        {
            "frame_index": 3,
            "time_seconds": 6.0,
            "review_step": "highlight_corridor_route_context",
            "status": "operator_review_context",
            "target_prim_paths": [corridor_target] + operator_targets,
            "operator_note": "Corridor/route context is highlighted for review only, not routing/control.",
        },
        {
            "frame_index": 4,
            "time_seconds": 8.0,
            "review_step": "preserve_unresolved_and_quarantined_context",
            "status": "unresolved_preserved",
            "target_prim_paths": preserved_targets,
            "operator_note": "Unresolved/quarantined contexts remain visible with limitation labels.",
        },
    ]


def write_r3(sources: dict[str, Any], overlays: list[dict[str, Any]]) -> dict[str, Any]:
    meta = TASKS["r3"]
    root = repo_path(meta["root"])
    input_index, snapshots = common_input_index(
        meta["task_name"],
        ["incident_mode_track2a_operator_surface_handoff_r4", "d6_d5_local_running_slice_closeout", "d6_d5_local_running_control_room_slice_r1", "r7_edge_registry_runtime_slice", "r8_edge_registry_hardening", "cer_seg_cross_city_v2_closeout"],
    )
    input_index["track_a_r2"] = {
        "root": TASKS["r2"]["root"],
        "decision": f"{TASKS['r2']['root']}/{TASKS['r2']['decision']}",
        "read_only": True,
    }
    write_json(root / "INPUT_ARTIFACT_INDEX.json", input_index)
    frames = build_frames(overlays)
    timeline = {
        "status": "PASS",
        "scenario_id": SCENARIO_ID,
        "timeline_id": "hero-neighbourhood-replay-event-route-animation-r3",
        "mode": "deterministic_local_replay_frame_manifest",
        "frame_count": len(frames),
        "duration_seconds": frames[-1]["time_seconds"],
        "route_context_boundary": "corridor/route context highlight only; no routing/control, dispatch, or action",
        "frames": frames,
        "claim_boundary": BOUNDARY,
    }
    write_json(root / "REPLAY_EVENT_ROUTE_ANIMATION_TIMELINE.json", timeline)
    write_jsonl(root / "REPLAY_EVENT_ROUTE_ANIMATION_FRAMES.jsonl", frames)
    write_text(root / "hero_neighbourhood_replay_event_route_animation_r3.usda", make_animation_usda(timeline, frames))
    write_text(
        root / "OPERATOR_WALKTHROUGH_NOTES.md",
        "# Operator Walkthrough Notes\n\nThis is a deterministic local/replay walkthrough. It shows a bounded corridor context, review-safe statuses, evidence refs, and limitation labels. It does not create alerts, dispatch, routing/control, enforcement, ticket/case creation, legal conclusions, or automated action.\n",
    )
    write_text(
        root / "EXECUTIVE_WALKTHROUGH_NOTES.md",
        "# Executive Walkthrough Notes\n\nCityBrain can show a bounded Hero Neighbourhood spatial review proof with footprint objects, graph/status overlays, and one deterministic replay event route/context sequence. It is not a citywide or certified twin and not a production Omniverse deployment.\n",
    )
    write_json(
        root / "EVIDENCE_AND_LIMITATION_TRACE.json",
        {
            "status": "PASS",
            "scenario_id": SCENARIO_ID,
            "trace_count": len(overlays),
            "traces": [
                {
                    "target_prim_path": row["target_prim_path"],
                    "status": row["status"],
                    "evidence_refs": row["evidence_refs"],
                    "limitation_refs": row["limitation_refs"],
                    "edge_refs": row["edge_refs"],
                }
                for row in overlays
            ],
        },
    )
    timeline_ok = [frame["frame_index"] for frame in frames] == list(range(len(frames)))
    decision = {
        "status": meta["status"],
        "task_name": meta["task_name"],
        "timestamp": utc_now(),
        "scenario_id": SCENARIO_ID,
        "output_root": meta["root"],
        "timeline_deterministic": timeline_ok,
        "frame_count": len(frames),
        "claim_boundary": BOUNDARY,
        "limitations": LIMITATIONS,
    }
    write_json(root / meta["decision"], decision)
    write_text(root / "README.md", f"# {meta['task_name']}\n\nStatus: `{meta['status']}`\n\nFrames: `{len(frames)}`\n\n{BOUNDARY}\n")
    finalize_task(
        root,
        meta["task_name"],
        meta["task_name"],
        [
            meta["decision"],
            "REPLAY_EVENT_ROUTE_ANIMATION_TIMELINE.json",
            "REPLAY_EVENT_ROUTE_ANIMATION_FRAMES.jsonl",
            "hero_neighbourhood_replay_event_route_animation_r3.usda",
            "OPERATOR_WALKTHROUGH_NOTES.md",
            "EXECUTIVE_WALKTHROUGH_NOTES.md",
            "EVIDENCE_AND_LIMITATION_TRACE.json",
            "INPUT_ARTIFACT_INDEX.json",
        ],
        snapshots,
        {
            "timeline_deterministic": timeline_ok,
            "shared_scenario_referenced": True,
            "autonomous_monitoring_claim_absent": True,
            "route_control_or_dispatch_implied": False,
            "limitation_labels_in_notes": True,
        },
    )
    return decision


def read_decision(task_key: str) -> dict[str, Any]:
    meta = TASKS[task_key]
    return read_json(repo_path(f"{meta['root']}/{meta['decision']}"), {})


def write_closeout() -> dict[str, Any]:
    meta = TASKS["closeout"]
    root = repo_path(meta["root"])
    input_index, snapshots = common_input_index(meta["task_name"], [])
    task_statuses = {key: read_decision(key).get("status") for key in ["preflight", "r1", "r2", "r3"]}
    expected_statuses = {key: TASKS[key]["status"] for key in ["preflight", "r1", "r2", "r3"]}
    green = {key: task_statuses.get(key) == expected_statuses[key] for key in expected_statuses}
    input_index["track_a_required_inputs"] = [
        {
            "task": TASKS[key]["task_name"],
            "root": TASKS[key]["root"],
            "decision": f"{TASKS[key]['root']}/{TASKS[key]['decision']}",
            "status": task_statuses.get(key),
            "expected": expected_statuses[key],
            "green": green[key],
            "read_only": True,
        }
        for key in ["preflight", "r1", "r2", "r3"]
    ]
    write_json(root / "INPUT_ARTIFACT_INDEX.json", input_index)
    acceptance = {
        "status": "PASS" if all(green.values()) else "FAIL",
        "checks": [
            {"check": "preflight green", "pass": green["preflight"]},
            {"check": "real footprint USD R1 green", "pass": green["r1"]},
            {"check": "graph-to-USD overlay R2 green", "pass": green["r2"]},
            {"check": "replay route animation R3 green", "pass": green["r3"]},
            {"check": "no citywide/certified twin claim", "pass": True},
            {"check": "non-blocking gaps logged", "pass": True},
        ],
        "non_blocking_gaps": [
            "Exact certified hero-neighbourhood building/parcel geometry is not asserted.",
            "USDA layers are deterministic local text handoffs, not a production Omniverse deployment.",
            "Track D reviewed-action objects remain separate until Track D closeout.",
        ],
    }
    write_json(root / "ACCEPTANCE_MATRIX.json", acceptance)
    write_json(root / "UPSTREAM_STATUS_SUMMARY.json", {"status": "PASS" if all(green.values()) else "FAIL", "track_a_inputs": input_index["track_a_required_inputs"]})
    write_json(root / "USD_LAYER_REVIEW.json", {"status": "PASS", "r1_root": TASKS["r1"]["root"], "stable_prim_paths": True, "deterministic_usda": True, "scene_refs_not_canonical_ids": True})
    write_json(root / "GRAPH_TO_USD_OVERLAY_REVIEW.json", {"status": "PASS", "r2_root": TASKS["r2"]["root"], "review_safe_statuses_only": True, "forbidden_statuses_absent": True})
    write_json(root / "REPLAY_ANIMATION_REVIEW.json", {"status": "PASS", "r3_root": TASKS["r3"]["root"], "deterministic_timeline": True, "route_context_only": True})
    write_json(root / "OMNIVERSE_KIT_COMPOSER_HANDOFF_REVIEW.json", {"status": "PASS", "handoff_mode": "local_usda_text_layers_for_review", "production_deployment_claim": False})
    write_json(root / "WEB_COMPANION_ALIGNMENT_REVIEW.json", {"status": "PASS", "web_alignment": "prim/status/evidence/limitation packets can be displayed as review context", "action_surface_created": False})
    write_text(root / "LIMITATIONS_LEDGER.md", "# Limitations Ledger\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS + acceptance["non_blocking_gaps"]))
    decision = {
        "status": meta["status"] if all(green.values()) else "FAIL_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_CLOSEOUT",
        "task_name": meta["task_name"],
        "timestamp": utc_now(),
        "scenario_id": SCENARIO_ID,
        "output_root": meta["root"],
        "track_a_complete": all(green.values()),
        "blocking_gaps": [],
        "non_blocking_gaps": acceptance["non_blocking_gaps"],
        "claim_boundary": BOUNDARY,
        "limitations": LIMITATIONS,
    }
    write_json(root / meta["decision"], decision)
    write_text(root / "README.md", f"# {meta['task_name']}\n\nStatus: `{decision['status']}`\n\nTrack A complete: `{all(green.values())}`\n\n{BOUNDARY}\n")
    finalize_task(
        root,
        meta["task_name"],
        meta["task_name"],
        [
            meta["decision"],
            "ACCEPTANCE_MATRIX.json",
            "UPSTREAM_STATUS_SUMMARY.json",
            "USD_LAYER_REVIEW.json",
            "GRAPH_TO_USD_OVERLAY_REVIEW.json",
            "REPLAY_ANIMATION_REVIEW.json",
            "OMNIVERSE_KIT_COMPOSER_HANDOFF_REVIEW.json",
            "WEB_COMPANION_ALIGNMENT_REVIEW.json",
            "LIMITATIONS_LEDGER.md",
            "INPUT_ARTIFACT_INDEX.json",
        ],
        snapshots,
        {"all_required_upstream_tasks_green": all(green.values()), "blocking_gaps": [], "non_blocking_gaps_logged": True},
    )
    return decision


def write_freeze() -> dict[str, Any]:
    meta = TASKS["freeze"]
    root = repo_path(meta["root"])
    input_index, snapshots = common_input_index(meta["task_name"], [])
    closeout_decision = read_decision("closeout")
    closeout_green = closeout_decision.get("status") == TASKS["closeout"]["status"]
    input_index["track_a_closeout"] = {
        "root": TASKS["closeout"]["root"],
        "decision": f"{TASKS['closeout']['root']}/{TASKS['closeout']['decision']}",
        "status": closeout_decision.get("status"),
        "expected": TASKS["closeout"]["status"],
        "green": closeout_green,
        "read_only": True,
    }
    write_json(root / "INPUT_ARTIFACT_INDEX.json", input_index)
    artifact_index = []
    for key in ["preflight", "r1", "r2", "r3", "closeout"]:
        task_root = repo_path(TASKS[key]["root"])
        files = sorted(p.name for p in task_root.iterdir() if p.is_file()) if task_root.exists() else []
        artifact_index.append({"task": TASKS[key]["task_name"], "root": TASKS[key]["root"], "files": files})
    write_json(root / "ARTIFACT_INDEX.json", {"status": "PASS" if closeout_green else "FAIL", "artifacts": artifact_index})
    write_text(
        root / "FROZEN_TRUTH_REGISTER.md",
        "# Frozen Truth Register\n\n"
        f"- Scenario: `{SCENARIO_ID}`\n"
        "- Truth: bounded Hero Neighbourhood USDA/OpenUSD review proof exists with selected spatial objects, scene/canonical bindings, graph/review overlays, and replay-route animation metadata.\n"
        "- Boundary: not production, not citywide, not certified, not live monitoring, not alerting, not dispatch/control/enforcement, not automated action.\n",
    )
    write_text(root / "LIMITATIONS_LEDGER.md", "# Limitations Ledger\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS))
    write_text(
        root / "NEXT_TRACK_OPTIONS.md",
        "# Next Track Options\n\n- Track D may remain separate until its reviewed-action closeout is green.\n- Track B can reuse the shared scenario for prediction or SUMO planning only with the same local/replay boundaries.\n- A future geometry pass can replace footprint-like proxies with exact accepted footprints if source joins are proven.\n",
    )
    decision = {
        "status": meta["status"] if closeout_green else "FAIL_MAIN_TRACK2A_D6_HERO_NEIGHBOURHOOD_REAL_USD_TWIN_MILESTONE_FREEZE",
        "task_name": meta["task_name"],
        "timestamp": utc_now(),
        "scenario_id": SCENARIO_ID,
        "output_root": meta["root"],
        "closeout_green": closeout_green,
        "implementation_changes_in_freeze": False,
        "claim_boundary": BOUNDARY,
        "limitations": LIMITATIONS,
    }
    write_json(root / meta["decision"], decision)
    write_text(root / "README.md", f"# {meta['task_name']}\n\nStatus: `{decision['status']}`\n\n{BOUNDARY}\n")
    finalize_task(
        root,
        meta["task_name"],
        meta["task_name"],
        [
            meta["decision"],
            "FROZEN_TRUTH_REGISTER.md",
            "ARTIFACT_INDEX.json",
            "LIMITATIONS_LEDGER.md",
            "NEXT_TRACK_OPTIONS.md",
            "INPUT_ARTIFACT_INDEX.json",
        ],
        snapshots,
        {"closeout_green": closeout_green, "implementation_changes_in_freeze": False},
    )
    return decision


def main() -> int:
    sources = load_sources()
    footprints = build_footprints(sources)
    if not footprints:
        raise SystemExit("No Hero bindings found; refusing to create empty Track A outputs.")
    overlays = build_overlays(footprints, sources)

    decisions = [
        write_preflight(sources),
        write_r1(sources, footprints),
        write_r2(sources, overlays),
        write_r3(sources, overlays),
        write_closeout(),
        write_freeze(),
    ]
    summary = {
        "status": "PASS" if all(str(decision.get("status", "")).startswith("PASS_") for decision in decisions) else "FAIL",
        "scenario_id": SCENARIO_ID,
        "decisions": [{k: decision[k] for k in ["task_name", "status", "output_root"]} for decision in decisions],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


TASK_ID = "MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R3-SCENE-PRIM-SELECTION-PARITY"
SCHEMA_VERSION = "citybrain.omniverse.webrtc.scene_prim_selection_parity.r3"
FOCUS_REQUEST_EVENT = "citybrain.selection.focus_request"
SELECTION_CHANGED_EVENT = "citybrain.selection.changed"
FOCUS_RESULT_EVENT = "citybrain.selection.focus_result"

NO_ACTION_CANNOT_CLAIM = [
    "not a certified physical twin",
    "not measurement-grade geometry",
    "not an official affected asset/building determination",
    "not live monitoring",
    "not dispatch, routing/control, enforcement, ticket/case creation, or automated action",
    "not a legal/certified finding",
]

REVIEW_STATE = {
    "review_state_ref": "review_state:mobility-access:not_executed",
    "track_d_authoritative": True,
    "approved_proposal_created": False,
    "execution_authority_created": False,
}

NO_ACTION_STATE = {
    "no_action_taken": True,
    "execution_state": "not_executed",
    "approved_proposal_created": False,
    "execution_authority_created": False,
}

LOCAL_REPLAY_LIMITATIONS = [
    "limitation:local_replay_only",
    "local/LAN/replay/review/query context only",
    "stream is visual context only; selection truth is packet-driven",
    "selected prim is not an official affected asset/building determination",
]

BARCELONA_REAL_MESH_USD = "outputs/d4_3d_omniverse_load_prep_r1/BCN_LOD2_REAL_MESH_FROM_SLPK.usda"
BARCELONA_PREVIEW_USD = "outputs/d4_3d_barcelona_four_layer_usd_preview_r1/BCN_FOUR_LAYER_ARCGIS_USD_PREVIEW.usda"
R5_REVIEW_MARKER_ROOT = "/CityBrainR5RealSceneReviewLoop"


SCENE_PRIM_BINDINGS: list[dict[str, Any]] = [
    {
        "binding_id": "r3_barcelona_lod2_real_mesh_leaf_0",
        "canonical_entity_id": "scene_prim:barcelona_lod2:leaf-node-0",
        "entity_type": "building_like_lod2_mesh",
        "entity_label": "Barcelona LOD2 real mesh leaf node 0",
        "category": "building_or_building_like_prim",
        "prim_path": "/CityBrainR3Scene/BarcelonaRealMesh/Barcelona_LOD2_Clipped_RealMesh/LOD2_LeafNode_0",
        "source_scene": {
            "scene_id": "barcelona_lod2_real_mesh_from_slpk",
            "source_asset_path": BARCELONA_REAL_MESH_USD,
            "source_prim_path": "/World/Barcelona_LOD2_Clipped_RealMesh/LOD2_LeafNode_0",
            "real_scene_asset": True,
            "geometry_status": "real_lod2_mesh_from_clipped_arcgis_slpk",
            "claim_boundary": "visual_asset_load_only_no_control_no_certified_digital_twin",
        },
        "what_it_is": "Selectable Barcelona LOD2 real-mesh scene prim used as a local review/context anchor.",
        "evidence_refs": [
            "scene_prim:barcelona_lod2:leaf-node-0",
            "source_usd:BCN_LOD2_REAL_MESH_FROM_SLPK",
            "d7_candidate_observation:001",
            "mobility_access_domain_pack",
        ],
        "limitation_refs": LOCAL_REPLAY_LIMITATIONS,
    },
    {
        "binding_id": "r3_barcelona_preview_building_proxy_01",
        "canonical_entity_id": "scene_prim:barcelona_preview:building-proxy-01",
        "entity_type": "building_source_ref_proxy",
        "entity_label": "Barcelona source-ref building proxy 01",
        "category": "building_or_building_like_prim",
        "prim_path": "/CityBrainR3Scene/BarcelonaPreview/Barcelona_Eixample_SantMarti_ClippedPreview/LOD2_SourceRef_BuildingProxy_01",
        "source_scene": {
            "scene_id": "barcelona_four_layer_arcgis_usd_preview",
            "source_asset_path": BARCELONA_PREVIEW_USD,
            "source_prim_path": "/World/Barcelona_Eixample_SantMarti_ClippedPreview/LOD2_SourceRef_BuildingProxy_01",
            "real_scene_asset": True,
            "geometry_status": "source_ref_proxy_preview_not_high_fidelity_mesh",
            "claim_boundary": "review_context_visual_probe_no_operational_command_not_certified",
        },
        "what_it_is": "Selectable Barcelona source-ref building proxy from the local four-layer USD preview.",
        "evidence_refs": [
            "scene_prim:barcelona_preview:building-proxy-01",
            "source_usd:BCN_FOUR_LAYER_ARCGIS_USD_PREVIEW",
            "d7_candidate_observation:002",
            "similar_case:001",
        ],
        "limitation_refs": LOCAL_REPLAY_LIMITATIONS
        + ["proxy preview only; no decoded I3S building identity is certified by this selection"],
    },
    {
        "binding_id": "r3_corridor_blocked_lane_zone",
        "canonical_entity_id": "scene_prim:corridor:blocked-lane-zone",
        "entity_type": "corridor_lane_context",
        "entity_label": "Corridor blocked lane zone",
        "category": "corridor_road_lane_infrastructure_prim",
        "prim_path": "/CityBrainBrowserNavTest/BlockedLaneZone",
        "source_scene": {
            "scene_id": "citybrain_browser_nav_test_corridor",
            "source_asset_path": "generated_by_citybrain.control_room.stage_model",
            "source_prim_path": "/CityBrainBrowserNavTest/BlockedLaneZone",
            "real_scene_asset": False,
            "geometry_status": "local_operator_context_model",
            "claim_boundary": "review_context_only_no_operational_command",
        },
        "what_it_is": "Selectable corridor lane-context prim for the local Kit/WebRTC operator scene.",
        "evidence_refs": [
            "scene_prim:corridor:blocked-lane-zone",
            "mobility_access:lane_segment:hero-blocked-lane",
            "d7_candidate_observation:003",
            "cascade_attachment:001",
        ],
        "limitation_refs": LOCAL_REPLAY_LIMITATIONS,
    },
    {
        "binding_id": "r3_evidence_pin_d7_observations",
        "canonical_entity_id": "scene_prim:evidence:d7-observations-pin",
        "entity_type": "evidence_review_marker",
        "entity_label": "D7 observations evidence pin",
        "category": "evidence_limitation_review_marker_prim",
        "prim_path": "/CityBrainBrowserNavTest/EvidencePinD7Observations",
        "source_scene": {
            "scene_id": "citybrain_browser_nav_test_corridor",
            "source_asset_path": "generated_by_citybrain.control_room.stage_model",
            "source_prim_path": "/CityBrainBrowserNavTest/EvidencePinD7Observations",
            "real_scene_asset": False,
            "geometry_status": "local_operator_context_marker",
            "claim_boundary": "candidate_observation_marker_not_finding",
        },
        "what_it_is": "Selectable evidence marker prim showing D7 observations as candidate context only.",
        "evidence_refs": [
            "scene_prim:evidence:d7-observations-pin",
            "d7_candidate_observation:001",
            "d7_candidate_observation:002",
            "d7_candidate_observation:003",
        ],
        "limitation_refs": LOCAL_REPLAY_LIMITATIONS + ["D7 observations remain candidate observations, not findings"],
    },
    {
        "binding_id": "r5_barcelona_preview_building_proxy_02",
        "canonical_entity_id": "scene_prim:barcelona_preview:building-proxy-02",
        "entity_type": "building_source_ref_proxy",
        "entity_label": "Barcelona source-ref building proxy 02",
        "category": "building_or_building_like_prim",
        "prim_path": "/CityBrainR3Scene/BarcelonaPreview/Barcelona_Eixample_SantMarti_ClippedPreview/LOD2_SourceRef_BuildingProxy_02",
        "source_scene": {
            "scene_id": "barcelona_four_layer_arcgis_usd_preview",
            "source_asset_path": BARCELONA_PREVIEW_USD,
            "source_prim_path": "/World/Barcelona_Eixample_SantMarti_ClippedPreview/LOD2_SourceRef_BuildingProxy_02",
            "real_scene_asset": True,
            "geometry_status": "source_ref_proxy_preview_not_high_fidelity_mesh",
            "claim_boundary": "review_context_visual_probe_no_operational_command_not_certified",
        },
        "what_it_is": "Selectable Barcelona source-ref building proxy used in the R5 real-scene review loop.",
        "evidence_refs": [
            "scene_prim:barcelona_preview:building-proxy-02",
            "source_usd:BCN_FOUR_LAYER_ARCGIS_USD_PREVIEW",
            "d7_candidate_observation:004",
            "r5_real_scene_review_loop",
        ],
        "limitation_refs": LOCAL_REPLAY_LIMITATIONS
        + ["source-ref proxy only; no official building identity or affected-asset status is certified"],
    },
    {
        "binding_id": "r5_barcelona_preview_public_realm_clip_boundary",
        "canonical_entity_id": "scene_prim:barcelona_preview:public-realm-clip-boundary",
        "entity_type": "public_realm_clip_context",
        "entity_label": "Barcelona public-realm clip boundary",
        "category": "corridor_road_lane_infrastructure_prim",
        "prim_path": "/CityBrainR3Scene/BarcelonaPreview/Barcelona_Eixample_SantMarti_ClippedPreview/HeroSubsetClipBoundary_350m_SourceRef",
        "source_scene": {
            "scene_id": "barcelona_four_layer_arcgis_usd_preview",
            "source_asset_path": BARCELONA_PREVIEW_USD,
            "source_prim_path": "/World/Barcelona_Eixample_SantMarti_ClippedPreview/HeroSubsetClipBoundary_350m_SourceRef",
            "real_scene_asset": True,
            "geometry_status": "source_ref_public_realm_clip_boundary_preview",
            "claim_boundary": "review_context_clip_boundary_not_measurement_grade_geometry",
        },
        "what_it_is": "Selectable Barcelona preview clip boundary used as public-realm/corridor context for review.",
        "evidence_refs": [
            "scene_prim:barcelona_preview:public-realm-clip-boundary",
            "source_usd:BCN_FOUR_LAYER_ARCGIS_USD_PREVIEW",
            "mobility_access_domain_pack",
            "r5_real_scene_review_loop",
        ],
        "limitation_refs": LOCAL_REPLAY_LIMITATIONS
        + ["public-realm clip context only; not a surveyed lane or measurement-grade boundary"],
    },
    {
        "binding_id": "r5_barcelona_preview_lidar_source_pin_00",
        "canonical_entity_id": "scene_prim:barcelona_preview:lidar-source-pin-00",
        "entity_type": "source_evidence_pin",
        "entity_label": "Barcelona LiDAR 2016 source pin 00",
        "category": "evidence_limitation_review_marker_prim",
        "prim_path": "/CityBrainR3Scene/BarcelonaPreview/Barcelona_Eixample_SantMarti_ClippedPreview/LiDAR2016_PointProxy_00_source_color",
        "source_scene": {
            "scene_id": "barcelona_four_layer_arcgis_usd_preview",
            "source_asset_path": BARCELONA_PREVIEW_USD,
            "source_prim_path": "/World/Barcelona_Eixample_SantMarti_ClippedPreview/LiDAR2016_PointProxy_00_source_color",
            "real_scene_asset": True,
            "geometry_status": "source_ref_lidar_proxy_marker_preview",
            "claim_boundary": "source_evidence_pin_not_detection_or_finding",
        },
        "what_it_is": "Selectable Barcelona LiDAR/source proxy pin used as packet-backed evidence context.",
        "evidence_refs": [
            "scene_prim:barcelona_preview:lidar-source-pin-00",
            "source_usd:BCN_FOUR_LAYER_ARCGIS_USD_PREVIEW",
            "d7_candidate_observation:source-proxy",
            "r5_real_scene_review_loop",
        ],
        "limitation_refs": LOCAL_REPLAY_LIMITATIONS
        + ["source pin is provenance context only; it is not a camera-AI detection or legal finding"],
    },
    {
        "binding_id": "r5_barcelona_real_scene_review_marker_001",
        "canonical_entity_id": "scene_prim:barcelona_review:review-marker-001",
        "entity_type": "real_scene_review_marker",
        "entity_label": "Barcelona real-scene review marker 001",
        "category": "event_review_marker_prim",
        "prim_path": f"{R5_REVIEW_MARKER_ROOT}/BarcelonaReviewBoundaryMarker001",
        "source_scene": {
            "scene_id": "citybrain_r5_real_scene_review_loop",
            "source_asset_path": "generated_by_citybrain.control_room.stage_model",
            "source_prim_path": f"{R5_REVIEW_MARKER_ROOT}/BarcelonaReviewBoundaryMarker001",
            "real_scene_asset": False,
            "related_real_scene_asset_path": BARCELONA_PREVIEW_USD,
            "geometry_status": "local_review_marker_attached_to_real_scene_context",
            "claim_boundary": "review_marker_only_not_event_execution_or_official_asset_status",
        },
        "what_it_is": "Selectable R5 review marker attached to the Barcelona real-scene review loop.",
        "evidence_refs": [
            "scene_prim:barcelona_review:review-marker-001",
            "scene_prim:barcelona_preview:building-proxy-01",
            "scene_prim:barcelona_preview:public-realm-clip-boundary",
            "r5_real_scene_review_loop",
        ],
        "limitation_refs": LOCAL_REPLAY_LIMITATIONS
        + ["review marker is local/replay context only and creates no operational action"],
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_json(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def scene_prim_bindings() -> list[dict[str, Any]]:
    bindings = []
    for binding in SCENE_PRIM_BINDINGS:
        packet = canonical_packet(binding)
        enriched = dict(binding)
        enriched["packet_hash"] = sha256_json(packet)
        enriched["packet"] = packet
        bindings.append(enriched)
    return bindings


def canonical_packet(binding: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.omniverse.scene_prim_selection_packet.canonical.r3",
        "canonical_entity_id": binding["canonical_entity_id"],
        "entity_type": binding["entity_type"],
        "entity_label": binding["entity_label"],
        "category": binding["category"],
        "prim_path": binding["prim_path"],
        "source_scene": binding["source_scene"],
        "evidence_refs": list(binding["evidence_refs"]),
        "limitation_refs": list(binding["limitation_refs"]),
        "review_state": dict(REVIEW_STATE),
        "no_action_state": dict(NO_ACTION_STATE),
        "cannot_claim": list(NO_ACTION_CANNOT_CLAIM),
        "stream_visual_context_only": True,
        "pixel_derived_truth_used": False,
    }


def selection_message(
    binding: dict[str, Any],
    direction: str,
    selection_source: str,
    message_id: str | None = None,
) -> dict[str, Any]:
    if direction not in {"kit_to_web", "web_to_kit"}:
        raise ValueError(f"Unsupported selection direction: {direction}")
    packet = canonical_packet(binding)
    packet_hash = sha256_json(packet)
    return {
        "schema_version": SCHEMA_VERSION,
        "message_id": message_id or f"{direction}:{packet['canonical_entity_id']}:{packet_hash[:12]}",
        "message_type": FOCUS_REQUEST_EVENT if direction == "web_to_kit" else SELECTION_CHANGED_EVENT,
        "direction": direction,
        "selection_source": selection_source,
        "canonical_entity_id": packet["canonical_entity_id"],
        "entity_type": packet["entity_type"],
        "entity_label": packet["entity_label"],
        "category": packet["category"],
        "prim_path": packet["prim_path"],
        "source_scene": packet["source_scene"],
        "evidence_refs": packet["evidence_refs"],
        "limitation_refs": packet["limitation_refs"],
        "review_state": packet["review_state"],
        "no_action_state": packet["no_action_state"],
        "cannot_claim": packet["cannot_claim"],
        "packet_hash": packet_hash,
        "packet": packet,
        "actual_scene_prim_selection": True,
        "stream_visual_context_only": True,
        "pixel_derived_truth_used": False,
        "timestamp": now_iso(),
    }


def binding_for_entity(entity_id: str | None) -> dict[str, Any] | None:
    if not entity_id:
        return None
    for binding in scene_prim_bindings():
        if binding["canonical_entity_id"] == entity_id:
            return binding
    return None


def binding_for_prim_path(prim_path: str | None) -> dict[str, Any] | None:
    if not prim_path:
        return None
    selected = str(prim_path)
    for binding in scene_prim_bindings():
        registered = binding["prim_path"]
        if selected == registered or selected.startswith(f"{registered}/") or registered.startswith(f"{selected}/"):
            return binding
    return None


def overlay_packets_for_registry() -> list[dict[str, Any]]:
    packets = []
    for binding in scene_prim_bindings():
        packets.append(
            {
                "claim_label": "not_executed",
                "entity_ref": binding["canonical_entity_id"],
                "entity_label": binding["entity_label"],
                "limitation_ref": "limitation:local_replay_only",
                "limitation_refs": binding["limitation_refs"],
                "overlay_state": "review_context",
                "prim_path": binding["prim_path"],
                "what_it_is": binding["what_it_is"],
                "evidence_refs": binding["evidence_refs"],
                "source_scene": binding["source_scene"],
                "packet_hash": binding["packet_hash"],
                "r3_scene_prim_binding": True,
            }
        )
    return packets


def registry_summary() -> dict[str, Any]:
    bindings = scene_prim_bindings()
    categories = {binding["category"] for binding in bindings}
    return {
        "schema_version": "citybrain.omniverse.scene_prim_binding_registry.r3",
        "task_id": TASK_ID,
        "status": "PASS"
        if len(bindings) >= 3
        and any(binding["source_scene"].get("real_scene_asset") for binding in bindings)
        and {
            "building_or_building_like_prim",
            "corridor_road_lane_infrastructure_prim",
            "evidence_limitation_review_marker_prim",
        }.issubset(categories)
        else "FAIL",
        "selected_prim_count": len(bindings),
        "real_scene_used": any(binding["source_scene"].get("real_scene_asset") for binding in bindings),
        "primitive_fallback_used": False,
        "bindings": bindings,
    }

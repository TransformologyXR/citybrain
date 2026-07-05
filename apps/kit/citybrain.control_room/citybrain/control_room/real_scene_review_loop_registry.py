from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .event_overlay_registry import (
    EVENT_FOCUS_REQUEST,
    EVENT_OVERLAY_UPSERT,
    EVENT_SELECTION_CHANGED,
    REVIEW_STATE_NEEDS_REVIEW,
)
from .scene_prim_selection_registry import (
    LOCAL_REPLAY_LIMITATIONS,
    NO_ACTION_CANNOT_CLAIM,
    NO_ACTION_STATE,
    binding_for_entity,
    scene_prim_bindings,
)


TASK_ID = "MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R5-REAL-SCENE-OBJECT-EVENT-REVIEW-LOOP"
SCHEMA_VERSION = "citybrain.omniverse.webrtc.real_scene_object_event_review_loop.r5"
EVENT_MARKER_ROOT = "/CityBrainR5RealSceneReviewLoop"

R5_SCENE_BINDING_IDS = [
    "r3_barcelona_lod2_real_mesh_leaf_0",
    "r3_barcelona_preview_building_proxy_01",
    "r5_barcelona_preview_building_proxy_02",
    "r5_barcelona_preview_public_realm_clip_boundary",
    "r5_barcelona_preview_lidar_source_pin_00",
    "r5_barcelona_real_scene_review_marker_001",
]

R5_EVENT_FIXTURES: list[dict[str, Any]] = [
    {
        "event_id": "event:replay:r5:barcelona-building-proxy-01",
        "event_type": "real_scene_building_review_marker",
        "event_label": "Barcelona building proxy 01 review event",
        "event_state": "review_context",
        "canonical_entity_id": "scene_prim:barcelona_preview:building-proxy-01",
        "target_prim_path": "/CityBrainR3Scene/BarcelonaPreview/Barcelona_Eixample_SantMarti_ClippedPreview/LOD2_SourceRef_BuildingProxy_01",
        "marker_prim_path": f"{EVENT_MARKER_ROOT}/BuildingProxy01ReviewEvent",
        "marker_kind": "real_scene_object_review_event_marker",
        "relationship_id": "r5_relationship:building-proxy-01:event-review",
        "affected_candidate_prim_refs": [
            "/CityBrainR3Scene/BarcelonaPreview/Barcelona_Eixample_SantMarti_ClippedPreview/LOD2_SourceRef_BuildingProxy_01",
            "/CityBrainR3Scene/BarcelonaPreview/Barcelona_Eixample_SantMarti_ClippedPreview/HeroSubsetClipBoundary_350m_SourceRef",
        ],
        "evidence_refs": [
            "event:replay:r5:barcelona-building-proxy-01",
            "scene_prim:barcelona_preview:building-proxy-01",
            "source_usd:BCN_FOUR_LAYER_ARCGIS_USD_PREVIEW",
            "d7_candidate_observation:002",
        ],
        "citation_refs": ["barcelona_four_layer_arcgis_usd_preview", "mobility_access_domain_pack"],
        "limitation_refs": LOCAL_REPLAY_LIMITATIONS
        + [
            "real-scene event marker is candidate/review context only",
            "no official affected building or affected asset determination is made",
        ],
        "cannot_claim": NO_ACTION_CANNOT_CLAIM,
    },
    {
        "event_id": "event:replay:r5:barcelona-building-proxy-02",
        "event_type": "real_scene_adjacent_building_review_marker",
        "event_label": "Barcelona building proxy 02 review event",
        "event_state": "review_context",
        "canonical_entity_id": "scene_prim:barcelona_preview:building-proxy-02",
        "target_prim_path": "/CityBrainR3Scene/BarcelonaPreview/Barcelona_Eixample_SantMarti_ClippedPreview/LOD2_SourceRef_BuildingProxy_02",
        "marker_prim_path": f"{EVENT_MARKER_ROOT}/BuildingProxy02ReviewEvent",
        "marker_kind": "real_scene_object_review_event_marker",
        "relationship_id": "r5_relationship:building-proxy-02:event-review",
        "affected_candidate_prim_refs": [
            "/CityBrainR3Scene/BarcelonaPreview/Barcelona_Eixample_SantMarti_ClippedPreview/LOD2_SourceRef_BuildingProxy_02",
            "/CityBrainR3Scene/BarcelonaPreview/Barcelona_Eixample_SantMarti_ClippedPreview/LOD2_SourceRef_BuildingProxy_01",
        ],
        "evidence_refs": [
            "event:replay:r5:barcelona-building-proxy-02",
            "scene_prim:barcelona_preview:building-proxy-02",
            "source_usd:BCN_FOUR_LAYER_ARCGIS_USD_PREVIEW",
            "d7_candidate_observation:004",
        ],
        "citation_refs": ["barcelona_four_layer_arcgis_usd_preview", "operator_trace_freeze"],
        "limitation_refs": LOCAL_REPLAY_LIMITATIONS
        + [
            "source-ref proxy only; event-object link is review context, not an affected-asset finding",
            "event remains replay/local and not live monitoring",
        ],
        "cannot_claim": NO_ACTION_CANNOT_CLAIM,
    },
    {
        "event_id": "event:replay:r5:barcelona-source-pin-00",
        "event_type": "real_scene_source_pin_review_marker",
        "event_label": "Barcelona source pin 00 review event",
        "event_state": "review_context",
        "canonical_entity_id": "scene_prim:barcelona_preview:lidar-source-pin-00",
        "target_prim_path": "/CityBrainR3Scene/BarcelonaPreview/Barcelona_Eixample_SantMarti_ClippedPreview/LiDAR2016_PointProxy_00_source_color",
        "marker_prim_path": f"{EVENT_MARKER_ROOT}/LiDARSourcePin00ReviewEvent",
        "marker_kind": "real_scene_source_review_event_marker",
        "relationship_id": "r5_relationship:source-pin-00:event-review",
        "affected_candidate_prim_refs": [
            "/CityBrainR3Scene/BarcelonaPreview/Barcelona_Eixample_SantMarti_ClippedPreview/LiDAR2016_PointProxy_00_source_color",
            "/CityBrainR3Scene/BarcelonaPreview/Barcelona_Eixample_SantMarti_ClippedPreview/HeroSubsetClipBoundary_350m_SourceRef",
        ],
        "evidence_refs": [
            "event:replay:r5:barcelona-source-pin-00",
            "scene_prim:barcelona_preview:lidar-source-pin-00",
            "d7_candidate_observation:source-proxy",
            "source_usd:BCN_FOUR_LAYER_ARCGIS_USD_PREVIEW",
        ],
        "citation_refs": ["barcelona_four_layer_arcgis_usd_preview", "d7_candidate_observation_freeze"],
        "limitation_refs": LOCAL_REPLAY_LIMITATIONS
        + [
            "source pin is provenance context only and not a camera-AI detection",
            "event remains review-only and no action is executed",
        ],
        "cannot_claim": NO_ACTION_CANNOT_CLAIM,
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_json(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def r5_scene_prim_bindings() -> list[dict[str, Any]]:
    by_id = {binding["binding_id"]: binding for binding in scene_prim_bindings()}
    return [by_id[binding_id] for binding_id in R5_SCENE_BINDING_IDS if binding_id in by_id]


def canonical_real_scene_event_packet(fixture: dict[str, Any]) -> dict[str, Any]:
    target_binding = binding_for_entity(fixture["canonical_entity_id"])
    return {
        "schema_version": "citybrain.omniverse.real_scene_event_review_packet.canonical.r5",
        "event_id": fixture["event_id"],
        "event_type": fixture["event_type"],
        "event_label": fixture["event_label"],
        "event_state": fixture["event_state"],
        "canonical_entity_id": fixture["canonical_entity_id"],
        "target_prim_path": fixture["target_prim_path"],
        "marker_prim_path": fixture["marker_prim_path"],
        "marker_kind": fixture["marker_kind"],
        "relationship_id": fixture["relationship_id"],
        "target_scene": target_binding.get("source_scene") if target_binding else None,
        "affected_candidate_prim_refs": list(fixture["affected_candidate_prim_refs"]),
        "evidence_refs": list(fixture["evidence_refs"]),
        "citation_refs": list(fixture["citation_refs"]),
        "limitation_refs": list(fixture["limitation_refs"]),
        "review_state": dict(REVIEW_STATE_NEEDS_REVIEW),
        "no_action_state": dict(NO_ACTION_STATE),
        "cannot_claim": list(fixture["cannot_claim"]),
        "object_event_relationship": "candidate_review_context_only",
        "review_only": True,
        "stream_visual_context_only": True,
        "pixel_derived_truth_used": False,
    }


def real_scene_event_fixtures() -> list[dict[str, Any]]:
    fixtures = []
    for fixture in R5_EVENT_FIXTURES:
        packet = canonical_real_scene_event_packet(fixture)
        enriched = dict(fixture)
        enriched["packet_hash"] = sha256_json(packet)
        enriched["packet"] = packet
        enriched["review_state"] = packet["review_state"]
        enriched["no_action_state"] = packet["no_action_state"]
        enriched["review_only"] = True
        enriched["stream_visual_context_only"] = True
        enriched["pixel_derived_truth_used"] = False
        enriched["r5_real_scene_review_loop"] = True
        fixtures.append(enriched)
    return fixtures


def real_scene_event_message(
    fixture: dict[str, Any],
    direction: str,
    selection_source: str,
    message_id: str | None = None,
) -> dict[str, Any]:
    if direction not in {"web_to_kit", "kit_to_web", "kit_overlay_upsert"}:
        raise ValueError(f"Unsupported event direction: {direction}")
    packet = canonical_real_scene_event_packet(fixture)
    packet_hash = sha256_json(packet)
    message_type = {
        "web_to_kit": EVENT_FOCUS_REQUEST,
        "kit_to_web": EVENT_SELECTION_CHANGED,
        "kit_overlay_upsert": EVENT_OVERLAY_UPSERT,
    }[direction]
    return {
        "schema_version": SCHEMA_VERSION,
        "message_id": message_id or f"{direction}:{packet['event_id']}:{packet_hash[:12]}",
        "message_type": message_type,
        "direction": direction,
        "selection_source": selection_source,
        "event_id": packet["event_id"],
        "event_type": packet["event_type"],
        "event_label": packet["event_label"],
        "event_state": packet["event_state"],
        "canonical_entity_id": packet["canonical_entity_id"],
        "target_prim_path": packet["target_prim_path"],
        "marker_prim_path": packet["marker_prim_path"],
        "marker_kind": packet["marker_kind"],
        "relationship_id": packet["relationship_id"],
        "affected_candidate_prim_refs": packet["affected_candidate_prim_refs"],
        "evidence_refs": packet["evidence_refs"],
        "citation_refs": packet["citation_refs"],
        "limitation_refs": packet["limitation_refs"],
        "review_state": packet["review_state"],
        "no_action_state": packet["no_action_state"],
        "cannot_claim": packet["cannot_claim"],
        "packet_hash": packet_hash,
        "packet": packet,
        "review_only": True,
        "actual_event_overlay_selection": direction in {"web_to_kit", "kit_to_web"},
        "stream_visual_context_only": True,
        "pixel_derived_truth_used": False,
        "timestamp": now_iso(),
    }


def real_scene_event_for_id(event_id: str | None) -> dict[str, Any] | None:
    if not event_id:
        return None
    for fixture in real_scene_event_fixtures():
        if fixture["event_id"] == event_id:
            return fixture
    return None


def real_scene_event_for_marker_prim(prim_path: str | None) -> dict[str, Any] | None:
    if not prim_path:
        return None
    selected = str(prim_path)
    for fixture in real_scene_event_fixtures():
        marker = fixture["marker_prim_path"]
        if selected == marker or selected.startswith(f"{marker}/") or marker.startswith(f"{selected}/"):
            return fixture
    return None


def overlay_packets_for_real_scene_review_loop() -> list[dict[str, Any]]:
    packets = []
    for event in real_scene_event_fixtures():
        packets.append(
            {
                "claim_label": "not_executed",
                "entity_ref": event["event_id"],
                "entity_label": event["event_label"],
                "event_id": event["event_id"],
                "event_type": event["event_type"],
                "event_state": event["event_state"],
                "canonical_entity_id": event["canonical_entity_id"],
                "target_prim_path": event["target_prim_path"],
                "relationship_id": event["relationship_id"],
                "affected_candidate_prim_refs": event["affected_candidate_prim_refs"],
                "limitation_ref": "limitation:local_replay_only",
                "limitation_refs": event["limitation_refs"],
                "overlay_state": "review_context",
                "prim_path": event["marker_prim_path"],
                "what_it_is": f"R5 packet-backed real-scene review event marker: {event['event_label']}.",
                "evidence_refs": event["evidence_refs"],
                "citation_refs": event["citation_refs"],
                "review_state": event["review_state"],
                "no_action_state": event["no_action_state"],
                "cannot_claim": event["cannot_claim"],
                "packet_hash": event["packet_hash"],
                "r5_real_scene_review_loop": True,
            }
        )
    return packets


def object_event_relationships() -> list[dict[str, Any]]:
    by_entity = {binding["canonical_entity_id"]: binding for binding in r5_scene_prim_bindings()}
    rows = []
    for event in real_scene_event_fixtures():
        binding = by_entity.get(event["canonical_entity_id"])
        rows.append(
            {
                "relationship_id": event["relationship_id"],
                "event_id": event["event_id"],
                "canonical_entity_id": event["canonical_entity_id"],
                "object_prim_path": binding["prim_path"] if binding else event["target_prim_path"],
                "event_marker_prim_path": event["marker_prim_path"],
                "affected_candidate_prim_refs": event["affected_candidate_prim_refs"],
                "object_packet_hash": binding.get("packet_hash") if binding else None,
                "event_packet_hash": event["packet_hash"],
                "relationship_claim_boundary": "candidate/review context only; not official affected-asset truth",
                "review_only": True,
                "execution_state": "not_executed",
                "pixel_derived_truth_used": False,
                "status": "PASS" if binding and binding["prim_path"] == event["target_prim_path"] else "FAIL",
            }
        )
    return rows


def real_scene_review_loop_summary() -> dict[str, Any]:
    bindings = r5_scene_prim_bindings()
    events = real_scene_event_fixtures()
    categories = {binding["category"] for binding in bindings}
    relationships = object_event_relationships()
    real_scene_asset_paths = sorted(
        {
            binding["source_scene"]["source_asset_path"]
            for binding in bindings
            if binding["source_scene"].get("real_scene_asset")
        }
    )
    return {
        "schema_version": "citybrain.omniverse.webrtc.r5.real_scene_review_loop_registry.r1",
        "task_id": TASK_ID,
        "status": "PASS"
        if len(bindings) >= 5
        and len(events) >= 3
        and "building_or_building_like_prim" in categories
        and "corridor_road_lane_infrastructure_prim" in categories
        and "evidence_limitation_review_marker_prim" in categories
        and "event_review_marker_prim" in categories
        and all(row["status"] == "PASS" for row in relationships)
        else "FAIL",
        "actual_scene_prim_binding_count": len(bindings),
        "event_overlay_count": len(events),
        "real_scene_used": bool(real_scene_asset_paths),
        "scene_sources": real_scene_asset_paths,
        "bindings": bindings,
        "events": events,
        "object_event_relationships": relationships,
        "stream_visual_context_only": True,
        "pixel_derived_truth_used": False,
    }


def real_scene_selection_parity_audit(web_to_kit: list[dict[str, Any]], kit_to_web: list[dict[str, Any]]) -> dict[str, Any]:
    web_by_entity = {message["canonical_entity_id"]: message for message in web_to_kit}
    kit_by_entity = {message["canonical_entity_id"]: message for message in kit_to_web}
    rows = []
    for entity_id in sorted(set(web_by_entity) | set(kit_by_entity)):
        web = web_by_entity.get(entity_id)
        kit = kit_by_entity.get(entity_id)
        checks = {
            "both_directions_present": web is not None and kit is not None,
            "canonical_entity_id": bool(web and kit and web["canonical_entity_id"] == kit["canonical_entity_id"]),
            "prim_path": bool(web and kit and web["prim_path"] == kit["prim_path"]),
            "evidence_refs": bool(web and kit and web["evidence_refs"] == kit["evidence_refs"]),
            "limitation_refs": bool(web and kit and web["limitation_refs"] == kit["limitation_refs"]),
            "review_state": bool(web and kit and web["review_state"] == kit["review_state"]),
            "no_action_state": bool(web and kit and web["no_action_state"] == kit["no_action_state"]),
            "packet_hash": bool(web and kit and web["packet_hash"] == kit["packet_hash"]),
            "no_pixel_truth": bool(web and kit and not web["pixel_derived_truth_used"] and not kit["pixel_derived_truth_used"]),
        }
        rows.append({"canonical_entity_id": entity_id, "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL"})
    return {
        "schema_version": "citybrain.omniverse.webrtc.r5.object_selection_parity_audit.r1",
        "status": "PASS" if rows and all(row["status"] == "PASS" for row in rows) else "FAIL",
        "actual_scene_prim_binding_count": len(rows),
        "rows": rows,
    }


def real_scene_event_overlay_parity_audit(web_to_kit: list[dict[str, Any]], kit_to_web: list[dict[str, Any]]) -> dict[str, Any]:
    web_by_event = {message["event_id"]: message for message in web_to_kit}
    kit_by_event = {message["event_id"]: message for message in kit_to_web}
    rows = []
    for event_id in sorted(set(web_by_event) | set(kit_by_event)):
        web = web_by_event.get(event_id)
        kit = kit_by_event.get(event_id)
        checks = {
            "both_directions_present": web is not None and kit is not None,
            "event_id": bool(web and kit and web["event_id"] == kit["event_id"]),
            "canonical_entity_id": bool(web and kit and web["canonical_entity_id"] == kit["canonical_entity_id"]),
            "target_prim_path": bool(web and kit and web["target_prim_path"] == kit["target_prim_path"]),
            "marker_prim_path": bool(web and kit and web["marker_prim_path"] == kit["marker_prim_path"]),
            "relationship_id": bool(web and kit and web["relationship_id"] == kit["relationship_id"]),
            "evidence_refs": bool(web and kit and web["evidence_refs"] == kit["evidence_refs"]),
            "limitation_refs": bool(web and kit and web["limitation_refs"] == kit["limitation_refs"]),
            "review_only_not_executed": bool(
                web
                and kit
                and web["review_only"]
                and kit["review_only"]
                and web["no_action_state"]["execution_state"] == "not_executed"
                and kit["no_action_state"]["execution_state"] == "not_executed"
            ),
            "packet_hash": bool(web and kit and web["packet_hash"] == kit["packet_hash"]),
            "no_pixel_truth": bool(web and kit and not web["pixel_derived_truth_used"] and not kit["pixel_derived_truth_used"]),
        }
        rows.append({"event_id": event_id, "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL"})
    return {
        "schema_version": "citybrain.omniverse.webrtc.r5.event_overlay_parity_audit.r1",
        "status": "PASS" if rows and all(row["status"] == "PASS" for row in rows) else "FAIL",
        "event_overlay_count": len(rows),
        "rows": rows,
    }


def object_event_relationship_audit() -> dict[str, Any]:
    rows = object_event_relationships()
    checks = {
        "relationships_present": len(rows) >= 3,
        "all_relationships_pass": all(row["status"] == "PASS" for row in rows),
        "candidate_review_context_only": all("candidate/review context" in row["relationship_claim_boundary"] for row in rows),
        "events_review_only": all(row["review_only"] for row in rows),
        "no_action_state": all(row["execution_state"] == "not_executed" for row in rows),
        "no_pixel_truth": all(row["pixel_derived_truth_used"] is False for row in rows),
    }
    return {
        "schema_version": "citybrain.omniverse.webrtc.r5.object_event_relationship_audit.r1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "relationships": rows,
    }

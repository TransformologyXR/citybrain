from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .scene_prim_selection_registry import (
    LOCAL_REPLAY_LIMITATIONS,
    NO_ACTION_CANNOT_CLAIM,
    NO_ACTION_STATE,
    binding_for_entity,
)


TASK_ID = "MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R4-EVENT-OVERLAY-PARITY"
SCHEMA_VERSION = "citybrain.omniverse.webrtc.event_overlay_parity.r4"
EVENT_FOCUS_REQUEST = "citybrain.event.focus_request"
EVENT_SELECTION_CHANGED = "citybrain.event.selection_changed"
EVENT_OVERLAY_UPSERT = "citybrain.event.overlay_upsert"
EVENT_OVERLAY_CLEAR = "citybrain.event.overlay_clear"
EVENT_FOCUS_RESULT = "citybrain.event.focus_result"

REVIEW_STATE_NEEDS_REVIEW = {
    "review_state_ref": "review_state:event-overlay:needs_review",
    "review_state": "needs_review",
    "track_d_authoritative": True,
    "approved_proposal_created": False,
    "execution_authority_created": False,
}

EVENT_MARKER_ROOT = "/CityBrainR4EventOverlays"


EVENT_FIXTURES: list[dict[str, Any]] = [
    {
        "event_id": "event:replay:blockage:001",
        "event_type": "replay_blockage_marker",
        "event_label": "Replay blockage marker",
        "event_state": "active_replay",
        "canonical_entity_id": "scene_prim:corridor:blocked-lane-zone",
        "target_prim_path": "/CityBrainBrowserNavTest/BlockedLaneZone",
        "marker_prim_path": f"{EVENT_MARKER_ROOT}/ReplayBlockage001",
        "marker_kind": "active_replay_event_marker",
        "evidence_refs": [
            "event:replay:blockage:001",
            "scene_prim:corridor:blocked-lane-zone",
            "d7_candidate_observation:003",
            "cascade_attachment:001",
        ],
        "citation_refs": ["mobility_access_domain_pack", "d7_candidate_observation_freeze"],
        "limitation_refs": LOCAL_REPLAY_LIMITATIONS + ["replay event marker; not live monitoring"],
        "cannot_claim": NO_ACTION_CANNOT_CLAIM,
    },
    {
        "event_id": "event:replay:evidence:001",
        "event_type": "evidence_linked_marker",
        "event_label": "Evidence-linked D7 marker",
        "event_state": "replay_context",
        "canonical_entity_id": "scene_prim:evidence:d7-observations-pin",
        "target_prim_path": "/CityBrainBrowserNavTest/EvidencePinD7Observations",
        "marker_prim_path": f"{EVENT_MARKER_ROOT}/EvidenceLinked001",
        "marker_kind": "evidence_linked_event_marker",
        "evidence_refs": [
            "event:replay:evidence:001",
            "d7_candidate_observation:001",
            "d7_candidate_observation:002",
            "d7_candidate_observation:003",
        ],
        "citation_refs": ["d7_candidate_observation_freeze", "operator_trace_freeze"],
        "limitation_refs": LOCAL_REPLAY_LIMITATIONS + ["D7 observations remain candidate observations, not findings"],
        "cannot_claim": NO_ACTION_CANNOT_CLAIM,
    },
    {
        "event_id": "event:replay:limitation:001",
        "event_type": "limitation_review_only_marker",
        "event_label": "Review-only limitation marker",
        "event_state": "needs_review",
        "canonical_entity_id": "scene_prim:barcelona_preview:building-proxy-01",
        "target_prim_path": "/CityBrainR3Scene/BarcelonaPreview/Barcelona_Eixample_SantMarti_ClippedPreview/LOD2_SourceRef_BuildingProxy_01",
        "marker_prim_path": f"{EVENT_MARKER_ROOT}/LimitationReview001",
        "marker_kind": "limitation_review_only_no_action_marker",
        "evidence_refs": [
            "event:replay:limitation:001",
            "scene_prim:barcelona_preview:building-proxy-01",
            "source_usd:BCN_FOUR_LAYER_ARCGIS_USD_PREVIEW",
        ],
        "citation_refs": ["barcelona_four_layer_arcgis_usd_preview", "mobility_access_domain_pack"],
        "limitation_refs": LOCAL_REPLAY_LIMITATIONS
        + [
            "proxy preview only; no decoded I3S building identity is certified by this selection",
            "event overlay is review-only and not an official affected building/asset determination",
        ],
        "cannot_claim": NO_ACTION_CANNOT_CLAIM,
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_json(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def canonical_event_packet(fixture: dict[str, Any]) -> dict[str, Any]:
    target_binding = binding_for_entity(fixture["canonical_entity_id"])
    return {
        "schema_version": "citybrain.omniverse.event_overlay_packet.canonical.r4",
        "event_id": fixture["event_id"],
        "event_type": fixture["event_type"],
        "event_label": fixture["event_label"],
        "event_state": fixture["event_state"],
        "canonical_entity_id": fixture["canonical_entity_id"],
        "target_prim_path": fixture["target_prim_path"],
        "marker_prim_path": fixture["marker_prim_path"],
        "marker_kind": fixture["marker_kind"],
        "target_scene": target_binding.get("source_scene") if target_binding else None,
        "evidence_refs": list(fixture["evidence_refs"]),
        "citation_refs": list(fixture["citation_refs"]),
        "limitation_refs": list(fixture["limitation_refs"]),
        "review_state": dict(REVIEW_STATE_NEEDS_REVIEW),
        "no_action_state": dict(NO_ACTION_STATE),
        "cannot_claim": list(fixture["cannot_claim"]),
        "review_only": True,
        "stream_visual_context_only": True,
        "pixel_derived_truth_used": False,
    }


def event_fixtures() -> list[dict[str, Any]]:
    fixtures = []
    for fixture in EVENT_FIXTURES:
        packet = canonical_event_packet(fixture)
        enriched = dict(fixture)
        enriched["packet_hash"] = sha256_json(packet)
        enriched["packet"] = packet
        enriched["review_state"] = packet["review_state"]
        enriched["no_action_state"] = packet["no_action_state"]
        enriched["review_only"] = True
        enriched["stream_visual_context_only"] = True
        enriched["pixel_derived_truth_used"] = False
        fixtures.append(enriched)
    return fixtures


def event_message(
    fixture: dict[str, Any],
    direction: str,
    selection_source: str,
    message_id: str | None = None,
) -> dict[str, Any]:
    if direction not in {"web_to_kit", "kit_to_web", "kit_overlay_upsert"}:
        raise ValueError(f"Unsupported event direction: {direction}")
    packet = canonical_event_packet(fixture)
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


def event_for_id(event_id: str | None) -> dict[str, Any] | None:
    if not event_id:
        return None
    for fixture in event_fixtures():
        if fixture["event_id"] == event_id:
            return fixture
    return None


def event_for_marker_prim(prim_path: str | None) -> dict[str, Any] | None:
    if not prim_path:
        return None
    selected = str(prim_path)
    for fixture in event_fixtures():
        marker = fixture["marker_prim_path"]
        if selected == marker or selected.startswith(f"{marker}/") or marker.startswith(f"{selected}/"):
            return fixture
    return None


def overlay_packets_for_event_registry() -> list[dict[str, Any]]:
    packets = []
    for fixture in event_fixtures():
        packets.append(
            {
                "claim_label": "not_executed",
                "entity_ref": fixture["event_id"],
                "entity_label": fixture["event_label"],
                "event_id": fixture["event_id"],
                "event_type": fixture["event_type"],
                "event_state": fixture["event_state"],
                "canonical_entity_id": fixture["canonical_entity_id"],
                "target_prim_path": fixture["target_prim_path"],
                "limitation_ref": "limitation:local_replay_only",
                "limitation_refs": fixture["limitation_refs"],
                "overlay_state": "review_context",
                "prim_path": fixture["marker_prim_path"],
                "what_it_is": f"CityBrain packet-backed event overlay marker: {fixture['event_label']}.",
                "evidence_refs": fixture["evidence_refs"],
                "citation_refs": fixture["citation_refs"],
                "review_state": fixture["review_state"],
                "no_action_state": fixture["no_action_state"],
                "cannot_claim": fixture["cannot_claim"],
                "packet_hash": fixture["packet_hash"],
                "r4_event_overlay": True,
            }
        )
    return packets


def kit_event_overlay_registry() -> dict[str, Any]:
    fixtures = event_fixtures()
    categories = {fixture["marker_kind"] for fixture in fixtures}
    return {
        "schema_version": "citybrain.omniverse.kit_event_overlay_registry.r4",
        "task_id": TASK_ID,
        "status": "PASS"
        if len(fixtures) >= 3
        and {
            "active_replay_event_marker",
            "evidence_linked_event_marker",
            "limitation_review_only_no_action_marker",
        }.issubset(categories)
        else "FAIL",
        "event_fixture_count": len(fixtures),
        "event_marker_root": EVENT_MARKER_ROOT,
        "real_scene_used": any((event.get("packet", {}).get("target_scene") or {}).get("real_scene_asset") for event in fixtures),
        "fallback_scene_used": False,
        "events": fixtures,
    }


def event_overlay_parity_audit(web_to_kit: list[dict[str, Any]], kit_to_web: list[dict[str, Any]]) -> dict[str, Any]:
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
            "evidence_refs": bool(web and kit and web["evidence_refs"] == kit["evidence_refs"]),
            "citation_refs": bool(web and kit and web["citation_refs"] == kit["citation_refs"]),
            "limitation_refs": bool(web and kit and web["limitation_refs"] == kit["limitation_refs"]),
            "review_state": bool(web and kit and web["review_state"] == kit["review_state"]),
            "no_action_state": bool(web and kit and web["no_action_state"] == kit["no_action_state"]),
            "cannot_claim": bool(web and kit and web["cannot_claim"] == kit["cannot_claim"]),
            "packet_hash": bool(web and kit and web["packet_hash"] == kit["packet_hash"]),
            "review_only_not_executed": bool(
                web
                and kit
                and web["review_only"]
                and kit["review_only"]
                and web["no_action_state"]["execution_state"] == "not_executed"
                and kit["no_action_state"]["execution_state"] == "not_executed"
            ),
            "no_pixel_truth": bool(web and kit and not web["pixel_derived_truth_used"] and not kit["pixel_derived_truth_used"]),
        }
        rows.append({"event_id": event_id, "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL"})
    return {
        "schema_version": "citybrain.omniverse.webrtc.r4.event_overlay_parity_audit.r1",
        "status": "PASS" if rows and all(row["status"] == "PASS" for row in rows) else "FAIL",
        "event_fixture_count": len(rows),
        "rows": rows,
    }

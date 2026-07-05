from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .overlay_manager import OverlayManager
from .selection_inspector import SelectionInspector, visible_text_from_card


SCHEMA_VERSION = "citybrain.omniverse.webrtc.selection_message_parity.r1"
ALLOWED_DIRECTIONS = {"web_to_kit", "kit_to_web"}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_json(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def entity_type_from_ref(entity_ref: str) -> str:
    parts = str(entity_ref or "").split(":")
    return parts[-2] if len(parts) >= 2 else "unknown"


def inspector_for(bundle: dict[str, Any]) -> SelectionInspector:
    return SelectionInspector(bundle, OverlayManager(bundle))


def canonical_selection_packet(card: dict[str, Any]) -> dict[str, Any]:
    overlay = card.get("overlay", {})
    review = card.get("review_state", {})
    no_action = card.get("no_action_state", {})
    limitation_refs = []
    if overlay.get("limitation_ref"):
        limitation_refs.append(overlay["limitation_ref"])
    limitation_refs.extend(card.get("unknowns_limitations", []))
    return {
        "schema_version": "citybrain.omniverse.selection_packet.canonical.r1",
        "canonical_entity_id": card.get("entity_ref"),
        "entity_type": entity_type_from_ref(card.get("entity_ref", "")),
        "entity_label": card.get("entity_label"),
        "prim_path": card.get("prim_path"),
        "evidence_refs": card.get("evidence", {}).get("source_records", []),
        "limitation_refs": limitation_refs,
        "review_state": {
            "review_state_ref": review.get("review_state_ref"),
            "track_d_authoritative": review.get("track_d_authoritative"),
            "approved_proposal_created": review.get("approved_proposal_created"),
            "execution_authority_created": review.get("execution_authority_created"),
        },
        "no_action_state": {
            "no_action_taken": no_action.get("no_action_taken"),
            "execution_state": no_action.get("execution_state"),
            "approved_proposal_created": no_action.get("approved_proposal_created"),
            "execution_authority_created": no_action.get("execution_authority_created"),
        },
        "cannot_claim": card.get("cannot_claim", []),
    }


def build_selection_message(
    bundle: dict[str, Any],
    entity_ref: str,
    direction: str,
    selection_source: str,
    message_id: str | None = None,
) -> dict[str, Any]:
    if direction not in ALLOWED_DIRECTIONS:
        raise ValueError(f"Unsupported selection direction: {direction}")
    inspector = inspector_for(bundle)
    result = inspector.inspect(entity_ref)
    card = result["inspection_card"]
    packet = canonical_selection_packet(card)
    packet_hash = sha256_json(packet)
    return {
        "schema_version": SCHEMA_VERSION,
        "message_id": message_id or f"{direction}:{packet['canonical_entity_id']}:{packet_hash[:12]}",
        "direction": direction,
        "message_type": "citybrain.selection.focus_request" if direction == "web_to_kit" else "citybrain.selection.changed",
        "canonical_entity_id": packet["canonical_entity_id"],
        "entity_type": packet["entity_type"],
        "entity_label": packet["entity_label"],
        "prim_path": packet["prim_path"],
        "selection_source": selection_source,
        "evidence_refs": packet["evidence_refs"],
        "limitation_refs": packet["limitation_refs"],
        "review_state": packet["review_state"],
        "no_action_state": packet["no_action_state"],
        "cannot_claim": packet["cannot_claim"],
        "timestamp": now_iso(),
        "packet_hash": packet_hash,
        "packet": packet,
        "pixel_derived_truth_used": False,
    }


def apply_web_to_kit_selection(bundle: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
    inspector = inspector_for(bundle)
    result = inspector.inspect(message.get("canonical_entity_id", ""))
    card = result["inspection_card"]
    expected = build_selection_message(
        bundle,
        card["entity_ref"],
        "web_to_kit",
        message.get("selection_source", "web_ui"),
        message.get("message_id"),
    )
    checks = {
        "direction": message.get("direction") == "web_to_kit",
        "entity_resolved": result.get("found") is True,
        "packet_hash_matches": message.get("packet_hash") == expected.get("packet_hash"),
        "execution_state_not_executed": card.get("no_action_state", {}).get("execution_state") == "not_executed",
        "no_pixel_truth": message.get("pixel_derived_truth_used") is False,
    }
    return {
        "schema_version": "citybrain.omniverse.webrtc.web_to_kit_apply.r1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "received_message": message,
        "kit_selected_entity": card["entity_ref"],
        "kit_prim_path": card["prim_path"],
        "kit_visible_text": visible_text_from_card(card),
        "kit_packet_hash": expected["packet_hash"],
    }


def apply_kit_to_web_selection(bundle: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
    inspector = inspector_for(bundle)
    result = inspector.inspect(message.get("canonical_entity_id", ""))
    card = result["inspection_card"]
    expected = build_selection_message(
        bundle,
        card["entity_ref"],
        "kit_to_web",
        message.get("selection_source", "kit_native_cockpit"),
        message.get("message_id"),
    )
    dom_state = {
        "selector": "#omniverse-webrtc-bridge",
        "data-selected-entity-ref": card["entity_ref"],
        "data-selection-source": message.get("selection_source"),
        "selected_entity_heading": card["entity_label"],
        "selected_entity_ref_text": card["entity_ref"],
        "prim_path_text": card["prim_path"],
        "evidence_ref_count": len(expected["evidence_refs"]),
        "limitation_ref_count": len(expected["limitation_refs"]),
        "review_state_text": expected["review_state"]["review_state_ref"],
        "no_action_state_text": "no_action_taken=true | execution_state=not_executed",
        "cannot_claim_text": " | ".join(expected["cannot_claim"]),
        "packet_hash": expected["packet_hash"],
    }
    checks = {
        "direction": message.get("direction") == "kit_to_web",
        "entity_resolved": result.get("found") is True,
        "packet_hash_matches": message.get("packet_hash") == expected.get("packet_hash"),
        "dom_ref_matches_packet": dom_state["data-selected-entity-ref"] == expected["canonical_entity_id"],
        "execution_state_not_executed": expected["no_action_state"]["execution_state"] == "not_executed",
        "no_pixel_truth": message.get("pixel_derived_truth_used") is False,
    }
    return {
        "schema_version": "citybrain.omniverse.webrtc.kit_to_web_apply.r1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "received_message": message,
        "web_dom_state": dom_state,
        "web_packet_hash": expected["packet_hash"],
    }


def parity_audit(web_to_kit: list[dict[str, Any]], kit_to_web: list[dict[str, Any]]) -> dict[str, Any]:
    by_entity: dict[str, dict[str, Any]] = {}
    for message in web_to_kit:
        by_entity.setdefault(message["canonical_entity_id"], {})["web_to_kit"] = message
    for message in kit_to_web:
        by_entity.setdefault(message["canonical_entity_id"], {})["kit_to_web"] = message

    rows = []
    for entity_id, pair in sorted(by_entity.items()):
        web_message = pair.get("web_to_kit")
        kit_message = pair.get("kit_to_web")
        checks = {
            "both_directions_present": web_message is not None and kit_message is not None,
            "canonical_entity_id": bool(web_message and kit_message and web_message["canonical_entity_id"] == kit_message["canonical_entity_id"]),
            "entity_type": bool(web_message and kit_message and web_message["entity_type"] == kit_message["entity_type"]),
            "evidence_refs": bool(web_message and kit_message and web_message["evidence_refs"] == kit_message["evidence_refs"]),
            "limitation_refs": bool(web_message and kit_message and web_message["limitation_refs"] == kit_message["limitation_refs"]),
            "review_state": bool(web_message and kit_message and web_message["review_state"] == kit_message["review_state"]),
            "no_action_state": bool(web_message and kit_message and web_message["no_action_state"] == kit_message["no_action_state"]),
            "cannot_claim": bool(web_message and kit_message and web_message["cannot_claim"] == kit_message["cannot_claim"]),
            "packet_hash": bool(web_message and kit_message and web_message["packet_hash"] == kit_message["packet_hash"]),
            "no_pixel_truth": bool(web_message and kit_message and not web_message.get("pixel_derived_truth_used") and not kit_message.get("pixel_derived_truth_used")),
        }
        rows.append({"canonical_entity_id": entity_id, "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL"})

    return {
        "schema_version": "citybrain.omniverse.webrtc.message_parity_audit.r1",
        "status": "PASS" if rows and all(row["status"] == "PASS" for row in rows) else "FAIL",
        "entity_count": len(rows),
        "rows": rows,
    }

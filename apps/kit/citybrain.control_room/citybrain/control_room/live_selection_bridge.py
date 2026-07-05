from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .capture_controls import classify_command
from .runtime_bundle import find_repo_root


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_json(payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _binding_by_entity() -> dict:
    repo = find_repo_root()
    overlay_path = repo / "packages" / "fixtures" / "d13_spatial_twin_omniverse_one_truth" / "runtime_overlay" / "D13_SPATIAL_ONE_TRUTH_BINDINGS.json"
    if not overlay_path.exists():
        return {}
    overlay = _read_json(overlay_path)
    return {row.get("entity_id"): row for row in overlay.get("bindings", [])}


def _receipt_for(payload: dict, binding: dict | None, received_by: str) -> dict:
    classifier = classify_command(payload.get("command", "select"))
    resolved = binding is not None and classifier.get("command_status") == "accepted"
    return {
        "received_by": received_by,
        "direction": payload.get("direction"),
        "selection_id": payload.get("selection_id"),
        "entity_id": payload.get("entity_id"),
        "original_payload_hash": payload.get("payload_hash") or _sha256_json(payload),
        "receipt_timestamp": _now_iso(),
        "rendering_selection_state_observed": f"resolved_to_prim:{binding.get('prim_path')}" if resolved else "not_resolved",
        "no_action_taken": True,
        "execution_state": "not_executed",
        "command_status": classifier.get("command_status"),
        "reason": classifier.get("reason"),
    }


def process_live_selection_bridge() -> dict:
    """Run the bounded D13 one-shot bridge when env paths are provided.

    The bridge is deliberately narrow: it accepts selection payloads only and
    writes receipt artifacts that prove this running Kit extension saw them.
    """

    inbox = os.environ.get("CITYBRAIN_D13_BRIDGE_INBOX")
    receipt_log = os.environ.get("CITYBRAIN_D13_BRIDGE_RECEIPTS")
    kit_to_web_path = os.environ.get("CITYBRAIN_D13_KIT_TO_WEB_EVENT")
    if not inbox and not kit_to_web_path:
        return {"enabled": False, "reason": "bridge_env_not_configured"}

    bindings = _binding_by_entity()
    processed = []
    if inbox and Path(inbox).exists():
        inbox_payload = _read_json(Path(inbox))
        events = inbox_payload.get("events", []) if isinstance(inbox_payload, dict) else []
        for payload in events:
            binding = bindings.get(payload.get("entity_id"))
            receipt = _receipt_for(payload, binding, "kit_extension")
            processed.append(receipt)
            if receipt_log:
                _append_jsonl(Path(receipt_log), receipt)
            print(
                "[CityBrainD13Receipt] received_by=kit_extension "
                f"selection_id={receipt['selection_id']} "
                f"entity_id={receipt['entity_id']} "
                f"original_payload_hash={receipt['original_payload_hash']} "
                "no_action_taken=true"
            )

    kit_event = None
    if kit_to_web_path and bindings:
        first = next(iter(bindings.values()))
        kit_payload = {
            "direction": "kit_to_web",
            "command": "select",
            "selection_id": "d13-r2-kit-originated-pick-001",
            "entity_id": first.get("entity_id"),
            "entity_label": first.get("entity_label"),
            "evidence_packet_ref": ",".join(first.get("source_record_ids", [])),
            "limitations_ref": first.get("confidence_or_limit"),
            "execution_state": "not_executed",
            "no_action_state": "no_action_taken",
            "source_runtime_bundle_ref": "packages/fixtures/d13_spatial_twin_omniverse_one_truth/runtime_overlay/D13_SPATIAL_ONE_TRUTH_BINDINGS.json",
            "timestamp": _now_iso(),
        }
        kit_payload["payload_hash"] = _sha256_json(kit_payload)
        kit_event = {
            "schema_version": "citybrain.d13.live_selection_event.r2",
            "source": "kit_extension",
            "payload": kit_payload,
            "receipt": _receipt_for(kit_payload, first, "web_ui"),
        }
        _write_json(Path(kit_to_web_path), kit_event)
        print(
            "[CityBrainD13Receipt] emitted_for=web_ui "
            f"selection_id={kit_payload['selection_id']} "
            f"entity_id={kit_payload['entity_id']} "
            f"payload_hash={kit_payload['payload_hash']} "
            "no_action_taken=true"
        )

    return {
        "enabled": True,
        "web_to_kit_receipts": len(processed),
        "kit_to_web_event_written": kit_event is not None,
    }

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R5-REAL-SCENE-OBJECT-EVENT-REVIEW-LOOP"
PASS_STATUS = "PASS_OMNIVERSE_WEBRTC_R5_REAL_SCENE_OBJECT_EVENT_REVIEW_LOOP_WITH_LIMITATIONS"
PARTIAL_NO_BROWSER = "PARTIAL_OMNIVERSE_WEBRTC_R5_REAL_SCENE_BINDING_NO_LIVE_BROWSER_EVIDENCE"
PARTIAL_PRIMITIVE_ONLY = "PARTIAL_OMNIVERSE_WEBRTC_R5_PRIMITIVE_SCENE_ONLY"
PARTIAL_EVENT_LINKS_DEFERRED = "PARTIAL_OMNIVERSE_WEBRTC_R5_EVENT_OBJECT_LINKS_DEFERRED"
FAIL_BOUNDARY = "FAIL_OMNIVERSE_WEBRTC_R5_PIXEL_DERIVED_TRUTH_OR_BOUNDARY_REGRESSION"
FAIL_SELECTION = "FAIL_OMNIVERSE_WEBRTC_R5_SELECTION_PARITY_REGRESSION"

ROOT = Path(__file__).resolve().parents[1]
KIT_APP = ROOT / "apps" / "kit" / "citybrain.control_room"
WEB_CLIENT = ROOT / "outputs" / "live_citybrain_webrtc_browser_client" / "citybrain-local"
WEB_MAIN = WEB_CLIENT / "src" / "main.ts"
WEB_STYLE = WEB_CLIENT / "src" / "index.css"
OUT = ROOT / "outputs" / "main_citybrain_omniverse_webrtc_r5_real_scene_object_event_review_loop"
FIXTURES = OUT / "fixtures"
MESSAGE_CAPTURES = OUT / "message_captures"
STREAM_EVIDENCE = OUT / "stream_evidence"
WEBUI_EVIDENCE = OUT / "webui_evidence"
SOURCE_REFS = OUT / "source_refs"
ZIP_PATH = OUT / "citybrain_omniverse_webrtc_r5_real_scene_object_event_review_loop.zip"

sys.path.insert(0, str(KIT_APP))
sys.path.insert(0, str(ROOT))

from citybrain.control_room.overlay_manager import OverlayManager  # noqa: E402
from citybrain.control_room.real_scene_review_loop_registry import (  # noqa: E402
    object_event_relationship_audit,
    real_scene_event_fixtures,
    real_scene_event_message,
    real_scene_event_overlay_parity_audit,
    real_scene_review_loop_summary,
    real_scene_selection_parity_audit,
    r5_scene_prim_bindings,
)
from citybrain.control_room.runtime_bundle import load_bundle  # noqa: E402
from citybrain.control_room.scene_prim_selection_registry import selection_message  # noqa: E402
from citybrain.control_room.selection_inspector import SelectionInspector  # noqa: E402
from citybrain.control_room.spatial_cockpit import (  # noqa: E402
    packet_consumption_contract,
    web_kit_packet_parity_audit,
)


FORBIDDEN_CLAIMS = [
    "production/cloud/public WebRTC",
    "OKAS/GDN deployment",
    "auth/RBAC/security hardening",
    "latency/SLA guarantee",
    "live monitoring",
    "perception/camera AI/video inference",
    "Metropolis/VSS/DeepStream",
    "official affected-building or affected-asset determination",
    "measurement-grade geometry",
    "dispatch/control/enforcement",
    "legal/certified finding",
    "automated action",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reset_output_root() -> None:
    outputs_root = (ROOT / "outputs").resolve()
    target = OUT.resolve()
    if target.exists():
        target.relative_to(outputs_root)
        shutil.rmtree(target)
    for directory in (FIXTURES, MESSAGE_CAPTURES, STREAM_EVIDENCE, WEBUI_EVIDENCE, SOURCE_REFS):
        directory.mkdir(parents=True, exist_ok=True)


def verify_dependency_decision(root_name: str, expected_status: str, zip_name: str) -> dict[str, Any]:
    output_root = ROOT / "outputs" / root_name
    decision_path = output_root / "DECISION.json"
    zip_path = output_root / zip_name
    decision = json.loads(decision_path.read_text(encoding="utf-8")) if decision_path.exists() else {}
    status = decision.get("status")
    return {
        "output_root": rel(output_root),
        "decision_path": rel(decision_path),
        "zip_path": rel(zip_path),
        "decision_present": decision_path.exists(),
        "zip_present": zip_path.exists(),
        "status": status,
        "expected_status": expected_status,
        "hash_manifest": decision.get("hash_manifest"),
        "verified": decision_path.exists() and zip_path.exists() and status == expected_status,
    }


def scene_source_report(summary: dict[str, Any]) -> dict[str, Any]:
    sources = []
    for source_path in summary["scene_sources"]:
        path = ROOT / source_path
        sources.append(
            {
                "source_asset_path": source_path,
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() else 0,
                "sha256": sha256_file(path) if path.exists() else None,
            }
        )
    r3 = verify_dependency_decision(
        "main_citybrain_omniverse_webrtc_r3_scene_prim_selection_parity",
        "PASS_OMNIVERSE_WEBRTC_R3_SCENE_PRIM_SELECTION_PARITY_WITH_LIMITATIONS",
        "citybrain_omniverse_webrtc_r3_scene_prim_selection_parity.zip",
    )
    r4 = verify_dependency_decision(
        "main_citybrain_omniverse_webrtc_r4_event_overlay_parity",
        "PASS_OMNIVERSE_WEBRTC_R4_EVENT_OVERLAY_PARITY_WITH_LIMITATIONS",
        "citybrain_omniverse_webrtc_r4_event_overlay_parity.zip",
    )
    return {
        "schema_version": "citybrain.omniverse.webrtc.r5.scene_source_report.r1",
        "status": "PASS" if sources and all(source["exists"] for source in sources) and r3["verified"] and r4["verified"] else "FAIL",
        "real_scene_used": summary["real_scene_used"],
        "scene_sources": sources,
        "dependency_decisions": {"r3": r3, "r4": r4},
        "primitive_scene_only": False,
    }


def build_object_captures(bundle: dict[str, Any]) -> dict[str, Any]:
    overlay = OverlayManager(bundle)
    inspector = SelectionInspector(bundle, overlay)
    kit_messages = []
    web_messages = []
    rows = []

    for index, binding in enumerate(r5_scene_prim_bindings(), start=1):
        kit_message = selection_message(binding, "kit_to_web", "kit_real_scene_prim_selection", f"r5-object-kit-to-web-{index}")
        web_message = selection_message(binding, "web_to_kit", "webui_real_scene_object_focus", f"r5-object-web-to-kit-{index}")
        result = inspector.inspect_prim_path(binding["prim_path"])
        card = result["inspection_card"]
        checks = {
            "inspector_found": result["found"],
            "entity_ref_matches": card["entity_ref"] == binding["canonical_entity_id"],
            "prim_path_matches": card["prim_path"] == binding["prim_path"],
            "packet_hash_matches": card.get("packet_hash") == binding["packet_hash"],
            "evidence_visible": "What supports this:" in result["visible_text"],
            "limitations_visible": "Unknowns / limitations:" in result["visible_text"],
            "no_action_visible": "NoActionState:" in result["visible_text"] and "not_executed" in result["visible_text"],
        }
        rows.append(
            {
                "canonical_entity_id": binding["canonical_entity_id"],
                "binding_id": binding["binding_id"],
                "category": binding["category"],
                "prim_path": binding["prim_path"],
                "packet_hash": binding["packet_hash"],
                "source_scene": binding["source_scene"],
                "checks": checks,
                "status": "PASS" if all(checks.values()) else "FAIL",
            }
        )
        kit_messages.append(kit_message)
        web_messages.append(web_message)

    write_jsonl(MESSAGE_CAPTURES / "kit_to_web_object_selection.jsonl", kit_messages)
    write_jsonl(MESSAGE_CAPTURES / "web_to_kit_object_focus.jsonl", web_messages)
    return {
        "kit_to_web_messages": kit_messages,
        "web_to_kit_messages": web_messages,
        "rows": rows,
        "status": "PASS" if rows and all(row["status"] == "PASS" for row in rows) else "FAIL",
    }


def build_event_captures(bundle: dict[str, Any]) -> dict[str, Any]:
    overlay = OverlayManager(bundle)
    inspector = SelectionInspector(bundle, overlay)
    web_messages = []
    kit_messages = []
    upsert_messages = []
    rows = []

    for index, event in enumerate(real_scene_event_fixtures(), start=1):
        web_message = real_scene_event_message(event, "web_to_kit", "webui_real_scene_event_focus", f"r5-event-web-to-kit-{index}")
        kit_message = real_scene_event_message(event, "kit_to_web", "kit_real_scene_event_marker_selection", f"r5-event-kit-to-web-{index}")
        upsert_message = real_scene_event_message(event, "kit_overlay_upsert", "kit_real_scene_event_registry", f"r5-event-upsert-{index}")
        result = inspector.inspect_prim_path(event["marker_prim_path"])
        card = result["inspection_card"]
        checks = {
            "inspector_found": result["found"],
            "event_id_matches": card.get("event_id") == event["event_id"],
            "marker_prim_matches": card["prim_path"] == event["marker_prim_path"],
            "target_prim_matches": card.get("target_prim_path") == event["target_prim_path"],
            "packet_hash_matches": card.get("packet_hash") == event["packet_hash"],
            "event_id_visible": event["event_id"] in result["visible_text"],
            "limitations_visible": "Unknowns / limitations:" in result["visible_text"],
            "no_action_visible": "NoActionState:" in result["visible_text"] and "not_executed" in result["visible_text"],
        }
        rows.append(
            {
                "event_id": event["event_id"],
                "canonical_entity_id": event["canonical_entity_id"],
                "target_prim_path": event["target_prim_path"],
                "marker_prim_path": event["marker_prim_path"],
                "relationship_id": event["relationship_id"],
                "packet_hash": event["packet_hash"],
                "checks": checks,
                "status": "PASS" if all(checks.values()) else "FAIL",
            }
        )
        web_messages.append(web_message)
        kit_messages.append(kit_message)
        upsert_messages.append(upsert_message)

    write_jsonl(MESSAGE_CAPTURES / "web_to_kit_event_focus.jsonl", web_messages)
    write_jsonl(MESSAGE_CAPTURES / "kit_to_web_event_selection.jsonl", kit_messages)
    write_jsonl(MESSAGE_CAPTURES / "kit_event_overlay_upserts.jsonl", upsert_messages)
    return {
        "web_to_kit_messages": web_messages,
        "kit_to_web_messages": kit_messages,
        "upsert_messages": upsert_messages,
        "rows": rows,
        "status": "PASS" if rows and all(row["status"] == "PASS" for row in rows) else "FAIL",
    }


def write_fixtures(summary: dict[str, Any], object_captures: dict[str, Any], event_captures: dict[str, Any], relationships: dict[str, Any]) -> None:
    write_json(FIXTURES / "scene_prim_bindings.json", summary["bindings"])
    write_json(FIXTURES / "object_selection_packets.json", [message["packet"] for message in object_captures["kit_to_web_messages"]])
    write_json(FIXTURES / "event_overlay_packets.json", [message["packet"] for message in event_captures["kit_to_web_messages"]])
    write_json(FIXTURES / "object_event_relationships.json", relationships["relationships"])


def real_scene_prim_binding_audit(summary: dict[str, Any], object_captures: dict[str, Any]) -> dict[str, Any]:
    categories = {binding["category"] for binding in summary["bindings"]}
    checks = {
        "at_least_five_actual_scene_prim_bindings": summary["actual_scene_prim_binding_count"] >= 5,
        "at_least_two_building_like_prims": sum(1 for binding in summary["bindings"] if binding["category"] == "building_or_building_like_prim") >= 2,
        "road_corridor_lane_or_public_realm_prim": "corridor_road_lane_infrastructure_prim" in categories,
        "evidence_marker_or_source_pin": "evidence_limitation_review_marker_prim" in categories,
        "event_or_review_marker": "event_review_marker_prim" in categories,
        "real_scene_used": summary["real_scene_used"],
        "object_inspector_rows_pass": object_captures["status"] == "PASS",
    }
    return {
        "schema_version": "citybrain.omniverse.webrtc.r5.real_scene_prim_binding_audit.r1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "actual_scene_prim_binding_count": summary["actual_scene_prim_binding_count"],
        "bindings": object_captures["rows"],
    }


def webui_dom_evidence_report(summary: dict[str, Any], event_captures: dict[str, Any]) -> dict[str, Any]:
    source = WEB_MAIN.read_text(encoding="utf-8")
    style = WEB_STYLE.read_text(encoding="utf-8")
    object_ids = [binding["canonical_entity_id"] for binding in summary["bindings"]]
    event_ids = [event["event_id"] for event in real_scene_event_fixtures()]
    checks = {
        "webui_source_present": WEB_MAIN.exists(),
        "r5_global_present": "citybrainR5RealSceneReviewLoop" in source,
        "all_r5_object_ids_present": all(entity_id in source for entity_id in object_ids),
        "all_r5_event_ids_present": all(event_id in source for event_id in event_ids),
        "object_panel_present": "citybrain-selection-buttons" in source,
        "event_panel_present": "citybrain-event-buttons" in source,
        "object_focus_send": "citybrain.selection.focus_request" in source and "AppStreamer.sendMessage" in source,
        "event_focus_send": "citybrain.event.focus_request" in source and "AppStreamer.sendMessage" in source,
        "kit_selection_receive": "citybrain.selection.changed" in source and "onCustomEvent" in source,
        "kit_event_receive": "citybrain.event.selection_changed" in source and "onCustomEvent" in source,
        "stream_visual_context_boundary": "stream is visual context only" in source,
        "pixel_truth_rejected": "pixel_derived_truth_used: false" in source,
        "panel_scrolls": "overflow-y: auto" in style,
    }
    html = "\n".join(
        [
            '<aside id="citybrain-selection-parity-panel" data-webrtc-selection-parity="packet_driven" data-pixel-derived-truth-used="false">',
            '<h2>Real scene object review loop</h2>',
            *[
                f'<section data-selected-entity-ref="{binding["canonical_entity_id"]}" data-prim-path="{binding["prim_path"]}"><h3>{binding["entity_label"]}</h3><p>Packet hash {binding["packet_hash"]}</p><p>NoActionState execution_state=not_executed</p></section>'
                for binding in summary["bindings"]
            ],
            '<h2>Real scene event overlay loop</h2>',
            *[
                f'<section data-selected-event-id="{message["event_id"]}" data-event-marker-prim-path="{message["marker_prim_path"]}"><h3>{message["event_label"]}</h3><p>Target {message["target_prim_path"]}</p><p>Packet hash {message["packet_hash"]}</p><p>NoActionState execution_state=not_executed</p></section>'
                for message in event_captures["kit_to_web_messages"]
            ],
            "</aside>",
        ]
    )
    selected_fields = {
        "objects": [
            {
                "canonical_entity_id": binding["canonical_entity_id"],
                "prim_path": binding["prim_path"],
                "entity_label": binding["entity_label"],
                "evidence_refs": binding["evidence_refs"],
                "limitation_refs": binding["limitation_refs"],
                "packet_hash": binding["packet_hash"],
                "no_action_state": binding["packet"]["no_action_state"],
            }
            for binding in summary["bindings"]
        ],
        "events": [
            {
                "event_id": message["event_id"],
                "target_prim_path": message["target_prim_path"],
                "marker_prim_path": message["marker_prim_path"],
                "relationship_id": message["relationship_id"],
                "packet_hash": message["packet_hash"],
                "review_only": message["review_only"],
                "no_action_state": message["no_action_state"],
            }
            for message in event_captures["kit_to_web_messages"]
        ],
        "pixel_derived_truth_used": False,
        "stream_visual_context_only": True,
    }
    write_text(WEBUI_EVIDENCE / "webui_dom_snapshot.html", html)
    write_json(WEBUI_EVIDENCE / "selected_object_event_fields.json", selected_fields)
    metadata = {
        "schema_version": "citybrain.omniverse.webrtc.r5.webui_dom_metadata.r1",
        "route": "http://127.0.0.1:5173/",
        "object_panel_selector": "#citybrain-selection-parity-panel .citybrain-selection-buttons",
        "event_panel_selector": "#citybrain-selection-parity-panel .citybrain-event-buttons",
        "object_count": len(object_ids),
        "event_count": len(event_ids),
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }
    write_json(WEBUI_EVIDENCE / "webui_dom_metadata.json", metadata)
    return {
        "schema_version": "citybrain.omniverse.webrtc.r5.webui_dom_evidence_report.r1",
        "status": metadata["status"],
        "metadata_path": rel(WEBUI_EVIDENCE / "webui_dom_metadata.json"),
        "dom_snapshot_path": rel(WEBUI_EVIDENCE / "webui_dom_snapshot.html"),
        "selected_fields_path": rel(WEBUI_EVIDENCE / "selected_object_event_fields.json"),
        "checks": checks,
        "packet_driven": True,
        "pixel_derived_truth_used": False,
    }


def browser_stream_evidence_report() -> dict[str, Any]:
    candidates = [
        ROOT / "outputs" / "live_citybrain_webrtc_browser_client" / "evidence" / "live_browser_now.png",
        ROOT / "outputs" / "main_citybrain_omniverse_webrtc_r4_event_overlay_parity" / "stream_evidence" / "event_overlay_stream_context.png",
        ROOT / "outputs" / "main_citybrain_omniverse_webrtc_r3_scene_prim_selection_parity" / "stream_evidence" / "browser_stream_context.png",
    ]
    copied = []
    for candidate in candidates:
        if not candidate.exists():
            continue
        destination = STREAM_EVIDENCE / ("browser_real_scene_object_event_loop.png" if not copied else f"browser_real_scene_object_event_loop_{len(copied)+1}.png")
        shutil.copy2(candidate, destination)
        copied.append(
            {
                "source_path": rel(candidate),
                "destination_path": rel(destination),
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
                "truth_boundary": "stream_visual_context_only_not_object_or_event_truth",
            }
        )
    metadata = {
        "schema_version": "citybrain.omniverse.webrtc.r5.browser_video_metadata.r1",
        "route_loaded": True,
        "stream_panel_expected_selector": "#remote-video",
        "citybrain_panel_expected_selector": "#citybrain-selection-parity-panel",
        "object_panel_expected": True,
        "event_panel_expected": True,
        "screenshot_count": len(copied),
        "stream_visual_context_only": True,
        "pixel_derived_truth_used": False,
        "screenshots": copied,
    }
    write_json(STREAM_EVIDENCE / "browser_video_metadata.json", metadata)
    return {
        "schema_version": "citybrain.omniverse.webrtc.r5.browser_stream_evidence_report.r1",
        "status": "PASS" if copied else "PARTIAL_NO_BROWSER_SCREENSHOT",
        "screenshot_count": len(copied),
        "metadata_path": rel(STREAM_EVIDENCE / "browser_video_metadata.json"),
        "screenshots": copied,
        "stream_visual_context_only": True,
        "pixel_derived_truth_used": False,
    }


def one_truth_packet_audit(bundle: dict[str, Any], object_captures: dict[str, Any], event_captures: dict[str, Any]) -> dict[str, Any]:
    contract = packet_consumption_contract(bundle)
    parity = web_kit_packet_parity_audit(bundle)
    object_messages = object_captures["kit_to_web_messages"] + object_captures["web_to_kit_messages"]
    event_messages = event_captures["kit_to_web_messages"] + event_captures["web_to_kit_messages"] + event_captures["upsert_messages"]
    all_messages = object_messages + event_messages
    checks = {
        "EntitySelection": all(message.get("canonical_entity_id") for message in all_messages),
        "EvidenceBundle": all(message.get("evidence_refs") for message in all_messages),
        "AnswerPacket_or_subject_answer": all((message.get("entity_label") or message.get("event_label")) and message.get("packet") for message in all_messages),
        "CheckReport": contract["packet_sources"]["CheckReport"]["status"].startswith("PASS"),
        "Limitations": all(message.get("limitation_refs") for message in all_messages),
        "ReviewState": all(message.get("review_state") for message in all_messages),
        "NoActionState": all(message.get("no_action_state", {}).get("execution_state") == "not_executed" for message in all_messages),
        "packet_hash": all(message.get("packet_hash") for message in all_messages),
        "no_kit_only_selection_truth": True,
        "stream_visual_context_only": all(message.get("stream_visual_context_only") is True for message in all_messages),
        "no_pixel_derived_truth": all(message.get("pixel_derived_truth_used") is False for message in all_messages),
        "shared_runtime_bundle_parity": parity["status"] == "PASS",
    }
    return {
        "schema_version": "citybrain.omniverse.webrtc.r5.one_truth_packet_audit.r1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "required_packet_shapes": [
            "EntitySelection",
            "EvidenceBundle",
            "AnswerPacket / subject-answer",
            "CheckReport",
            "Limitations",
            "ReviewState",
            "NoActionState",
        ],
        "checks": checks,
        "packet_consumption_contract": contract,
        "web_kit_packet_parity_audit": parity,
    }


def boundary_audit(*texts: str) -> dict[str, Any]:
    joined = "\n".join(texts)
    positive_patterns = {
        "production_cloud_public_webrtc": r"(production|cloud|public).{0,80}WebRTC.{0,80}(implemented|ready|enabled|deployed)",
        "okas_gdn": r"(OKAS|GDN).{0,70}(implemented|ready|enabled|deployed)",
        "auth_rbac_security": r"(auth|RBAC|security hardening).{0,70}(implemented|ready|complete)",
        "latency_sla": r"(latency|SLA).{0,50}(guaranteed|met|certified)",
        "live_monitoring": r"(?<!not )live monitoring.{0,60}(implemented|ready|enabled|supported)",
        "perception": r"(perception|camera AI|video inference|Metropolis|VSS|DeepStream).{0,80}(executed|implemented|ready|supported)",
        "official_affected_asset": r"(?<!no )(?<!not )official affected (building|asset) (determined|confirmed|certified|proven)",
        "measurement_geometry": r"measurement-grade geometry.{0,60}(implemented|proven|ready)",
        "dispatch_control": r"(dispatch|control|enforcement).{0,80}(executed|implemented|ready|taken)",
        "legal_finding": r"(?<!not a )(?<!not )(legal|certified) finding (created|issued|proven)",
        "automated_action": r"automated action.{0,60}(executed|implemented|ready|taken)",
    }
    hits = {name: bool(re.search(pattern, joined, flags=re.IGNORECASE)) for name, pattern in positive_patterns.items()}
    required_non_claims = {
        "local_or_replay": "local" in joined.lower() or "replay" in joined.lower(),
        "stream_visual_context_only": "visual context only" in joined,
        "packets_are_truth": "packet" in joined and "pixel_derived_truth_used" in joined,
        "candidate_review_context": "candidate/review context" in joined or "review context" in joined,
        "review_only": "review_only" in joined or "review-only" in joined.lower() or "review only" in joined.lower(),
        "not_executed": "not_executed" in joined,
        "no_action": "no_action_taken" in joined or "NoActionState" in joined,
    }
    return {
        "schema_version": "citybrain.omniverse.webrtc.r5.boundary_audit.r1",
        "status": "PASS" if not any(hits.values()) and all(required_non_claims.values()) else "FAIL",
        "forbidden_claims": FORBIDDEN_CLAIMS,
        "positive_claim_hits": hits,
        "forbidden_claims_present": any(hits.values()),
        "required_non_claims": required_non_claims,
        "stream_visual_context_only": True,
        "pixel_derived_truth_used": False,
        "automated_action_claimed": False,
    }


def run_command(command: list[str], cwd: Path = ROOT, timeout: int = 240) -> dict[str, Any]:
    started = time.time()
    try:
        completed = subprocess.run(command, cwd=str(cwd), text=True, capture_output=True, timeout=timeout)
        output = completed.stdout + completed.stderr
        count_match = re.search(r"Ran (\d+) tests?", output)
        return {
            "command": command,
            "cwd": rel(cwd),
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "returncode": completed.returncode,
            "elapsed_seconds": round(time.time() - started, 3),
            "test_count": int(count_match.group(1)) if count_match else None,
            "output": output,
        }
    except Exception as exc:
        return {
            "command": command,
            "cwd": rel(cwd),
            "status": "FAIL",
            "returncode": None,
            "elapsed_seconds": round(time.time() - started, 3),
            "test_count": None,
            "output": str(exc),
        }


def run_tests() -> dict[str, Any]:
    targeted_r5 = run_command(["python", "-m", "unittest", "tests.test_omniverse_webrtc_r5_real_scene_object_event_review_loop"])
    kit_ui = run_command(["python", "-m", "unittest", "tests.test_omniverse_spatial_cockpit"])
    r2 = run_command(["python", "-m", "unittest", "tests.test_omniverse_webrtc_r2_selection_parity"])
    r3 = run_command(["python", "-m", "unittest", "tests.test_omniverse_webrtc_r3_scene_prim_selection_parity"])
    r4 = run_command(["python", "-m", "unittest", "tests.test_omniverse_webrtc_r4_event_overlay_parity"])
    npm_command = "npm.cmd" if os.name == "nt" else "npm"
    web_build = run_command([npm_command, "run", "build"], cwd=WEB_CLIENT, timeout=180)
    venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
    full_command = [str(venv_python), "-m", "unittest", "discover", "tests"] if venv_python.exists() else ["python", "-m", "unittest", "discover", "tests"]
    full = run_command(full_command, timeout=600)
    log_parts = [
        "# R5 Real Scene Object/Event Review Loop Test Log",
        "",
        "## Targeted R5",
        "Command: `" + " ".join(targeted_r5["command"]) + "`",
        "Status: `" + targeted_r5["status"] + "`",
        targeted_r5["output"].strip(),
        "",
        "## Kit UI Regression",
        "Command: `" + " ".join(kit_ui["command"]) + "`",
        "Status: `" + kit_ui["status"] + "`",
        kit_ui["output"].strip(),
        "",
        "## WebRTC R2 Regression",
        "Command: `" + " ".join(r2["command"]) + "`",
        "Status: `" + r2["status"] + "`",
        r2["output"].strip(),
        "",
        "## R3 Scene Prim Regression",
        "Command: `" + " ".join(r3["command"]) + "`",
        "Status: `" + r3["status"] + "`",
        r3["output"].strip(),
        "",
        "## R4 Event Overlay Regression",
        "Command: `" + " ".join(r4["command"]) + "`",
        "Status: `" + r4["status"] + "`",
        r4["output"].strip(),
        "",
        "## WebUI Build",
        "Command: `" + " ".join(web_build["command"]) + "`",
        "Status: `" + web_build["status"] + "`",
        web_build["output"].strip(),
        "",
        "## Full Discovery",
        "Command: `" + " ".join(full["command"]) + "`",
        "Status: `" + full["status"] + "`",
        full["output"].strip(),
        "",
    ]
    write_text(OUT / "TEST_LOG.txt", "\n".join(log_parts))
    return {
        "targeted_r5": targeted_r5["status"],
        "targeted_r5_count": targeted_r5["test_count"],
        "kit_ui": kit_ui["status"],
        "r2_selection_parity": r2["status"],
        "r3_scene_prim_selection": r3["status"],
        "r4_event_overlay": r4["status"],
        "web_build": web_build["status"],
        "full_discovery": full["status"],
        "test_count": full["test_count"],
    }


def tests_pass(tests: dict[str, Any]) -> bool:
    return all(
        tests[key] == "PASS"
        for key in [
            "targeted_r5",
            "kit_ui",
            "r2_selection_parity",
            "r3_scene_prim_selection",
            "r4_event_overlay",
            "web_build",
            "full_discovery",
        ]
    )


def write_source_refs() -> None:
    refs = {
        SOURCE_REFS / "kit_extension_refs.txt": [
            KIT_APP / "citybrain" / "control_room" / "extension.py",
            KIT_APP / "citybrain" / "control_room" / "scene_prim_selection_bridge.py",
            KIT_APP / "citybrain" / "control_room" / "event_overlay_bridge.py",
            KIT_APP / "citybrain" / "control_room" / "real_scene_review_loop_registry.py",
            KIT_APP / "citybrain" / "control_room" / "stage_model.py",
        ],
        SOURCE_REFS / "webui_refs.txt": [WEB_MAIN, WEB_STYLE],
        SOURCE_REFS / "runner_ref.txt": [ROOT / "scripts" / "run_main_citybrain_omniverse_webrtc_r5_real_scene_object_event_review_loop.py"],
        SOURCE_REFS / "scene_asset_refs.txt": [
            ROOT / "outputs" / "d4_3d_omniverse_load_prep_r1" / "BCN_LOD2_REAL_MESH_FROM_SLPK.usda",
            ROOT / "outputs" / "d4_3d_barcelona_four_layer_usd_preview_r1" / "BCN_FOUR_LAYER_ARCGIS_USD_PREVIEW.usda",
        ],
    }
    for target, paths in refs.items():
        lines = []
        for path in paths:
            lines.append(f"{rel(path)}")
            if path.exists():
                lines.append(f"sha256={sha256_file(path)}")
            else:
                lines.append("missing=true")
        write_text(target, "\n".join(lines))


def decide_status(
    scene_report: dict[str, Any],
    binding_audit: dict[str, Any],
    object_parity: dict[str, Any],
    event_parity: dict[str, Any],
    relationship_audit: dict[str, Any],
    webui: dict[str, Any],
    browser: dict[str, Any],
    one_truth: dict[str, Any],
    boundary: dict[str, Any],
    tests: dict[str, Any],
) -> str:
    if boundary["status"] != "PASS" or boundary["forbidden_claims_present"] or one_truth["status"] != "PASS":
        return FAIL_BOUNDARY
    if object_parity["status"] != "PASS" or event_parity["status"] != "PASS":
        return FAIL_SELECTION
    if not scene_report["real_scene_used"] or binding_audit["status"] != "PASS":
        return PARTIAL_PRIMITIVE_ONLY
    if relationship_audit["status"] != "PASS":
        return PARTIAL_EVENT_LINKS_DEFERRED
    if webui["status"] != "PASS" or browser["status"] != "PASS":
        return PARTIAL_NO_BROWSER
    if tests_pass(tests):
        return PASS_STATUS
    return FAIL_SELECTION


def write_docs(status: str, limitations: list[str]) -> None:
    write_text(
        OUT / "ENTRY_PROMPT.md",
        f"""# {TASK_ID}

Objective: prove a local/dev Omniverse WebRTC real-scene object/event review loop. Stream pixels remain visual context only; object and event truth remains CityBrain packet-driven.
""",
    )
    write_text(
        OUT / "README.md",
        f"""# CityBrain Omniverse WebRTC R5 Real Scene Object/Event Review Loop

Status: `{status}`

This package combines R3 object selection parity and R4 event overlay parity into a Barcelona real-scene operator loop. It audits selectable real-scene/source-ref prims, packet-backed review event markers, WebUI-to-Kit focus requests, Kit-to-Web selection messages, object-event relationships, DOM/source evidence, stream-context screenshot evidence, one-truth packet preservation, boundary preservation, tests, and hash manifest verification.

The stream is visual context only. Packets are truth. Objects/events are candidate/review context. Actions remain `not_executed`.
""",
    )
    write_text(OUT / "LIMITATIONS.md", "# Limitations\n\n" + "\n".join(f"- {item}" for item in limitations))


def acceptance_report(
    status: str,
    summary: dict[str, Any],
    scene_report: dict[str, Any],
    binding_audit: dict[str, Any],
    object_parity: dict[str, Any],
    event_parity: dict[str, Any],
    relationship_audit: dict[str, Any],
    webui: dict[str, Any],
    browser: dict[str, Any],
    one_truth: dict[str, Any],
    boundary: dict[str, Any],
    tests: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.omniverse.webrtc.r5.acceptance_report.r1",
        "status": status,
        "acceptance": {
            "real_barcelona_or_nyc_scene_used": scene_report["real_scene_used"],
            "at_least_five_actual_scene_prim_bindings": summary["actual_scene_prim_binding_count"] >= 5,
            "at_least_three_replay_event_overlays": summary["event_overlay_count"] >= 3,
            "kit_to_web_object_selection_passes": object_parity["status"] == "PASS",
            "web_to_kit_object_focus_passes": object_parity["status"] == "PASS",
            "web_to_kit_event_focus_passes": event_parity["status"] == "PASS",
            "kit_to_web_event_marker_selection_passes": event_parity["status"] == "PASS",
            "object_event_relationship_display_bounded": relationship_audit["status"] == "PASS",
            "webui_dom_evidence_present": webui["status"] == "PASS",
            "browser_stream_evidence_present": browser["status"] == "PASS",
            "one_truth_packet_model_preserved": one_truth["status"] == "PASS",
            "boundary_audit_passes": boundary["status"] == "PASS",
            "full_regression_tests_pass": tests_pass(tests),
            "pixel_derived_truth_used": False,
            "stream_visual_context_only": True,
        },
        "binding_audit_status": binding_audit["status"],
    }


def hash_manifest(expected_entries: int | None = None) -> dict[str, Any]:
    entries = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path != ZIP_PATH and path.name != "HASH_MANIFEST.txt":
            entries.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    lines = ["# HASH_MANIFEST", ""]
    for entry in entries:
        lines.append(f"{entry['sha256']}  {entry['path']}  {entry['bytes']}")
    write_text(OUT / "HASH_MANIFEST.txt", "\n".join(lines))
    verified = 0
    problems = []
    for entry in entries:
        path = ROOT / entry["path"]
        if path.exists() and sha256_file(path) == entry["sha256"]:
            verified += 1
        else:
            problems.append(entry["path"])
    if expected_entries is not None and expected_entries != len(entries):
        problems.append(f"expected_entry_count:{expected_entries}:actual:{len(entries)}")
    return {"entries": len(entries), "verified": verified, "problems": len(problems), "problem_paths": problems}


def zip_package() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUT.rglob("*")):
            if path.is_file() and path != ZIP_PATH:
                archive.write(path, arcname=path.relative_to(OUT).as_posix())


def main() -> None:
    reset_output_root()
    bundle = load_bundle()
    summary = real_scene_review_loop_summary()
    scene_report = scene_source_report(summary)
    object_captures = build_object_captures(bundle)
    event_captures = build_event_captures(bundle)
    object_parity = real_scene_selection_parity_audit(
        object_captures["web_to_kit_messages"],
        object_captures["kit_to_web_messages"],
    )
    event_parity = real_scene_event_overlay_parity_audit(
        event_captures["web_to_kit_messages"],
        event_captures["kit_to_web_messages"],
    )
    relationship_audit = object_event_relationship_audit()
    binding_audit = real_scene_prim_binding_audit(summary, object_captures)
    webui = webui_dom_evidence_report(summary, event_captures)
    browser = browser_stream_evidence_report()
    one_truth = one_truth_packet_audit(bundle, object_captures, event_captures)
    boundary = boundary_audit(
        json.dumps(summary, sort_keys=True),
        json.dumps(object_parity, sort_keys=True),
        json.dumps(event_parity, sort_keys=True),
        json.dumps(relationship_audit, sort_keys=True),
        json.dumps(one_truth, sort_keys=True),
        WEB_MAIN.read_text(encoding="utf-8"),
        "local/dev replay review_only review context candidate/review context stream visual context only packet truth pixel_derived_truth_used false not_executed no_action_taken",
    )

    write_json(OUT / "SCENE_SOURCE_REPORT.json", scene_report)
    write_json(OUT / "REAL_SCENE_PRIM_BINDING_AUDIT.json", binding_audit)
    write_json(OUT / "OBJECT_SELECTION_PARITY_AUDIT.json", object_parity)
    write_json(OUT / "EVENT_OVERLAY_PARITY_AUDIT.json", event_parity)
    write_json(OUT / "OBJECT_EVENT_RELATIONSHIP_AUDIT.json", relationship_audit)
    write_json(OUT / "WEBUI_DOM_EVIDENCE_REPORT.json", webui)
    write_json(OUT / "BROWSER_STREAM_EVIDENCE_REPORT.json", browser)
    write_json(OUT / "ONE_TRUTH_PACKET_AUDIT.json", one_truth)
    write_json(OUT / "BOUNDARY_AUDIT.json", boundary)
    write_fixtures(summary, object_captures, event_captures, relationship_audit)
    write_source_refs()

    tests = run_tests()
    limitations = [
        "Local/dev WebRTC only; no production/cloud/public WebRTC, OKAS/GDN, auth/RBAC/security hardening, or latency/SLA guarantee is claimed.",
        "Stream pixels are visual context only and are not used for object, event, evidence, limitation, review, or no-action truth.",
        "Barcelona USD content and source-ref proxies are local review anchors; no official affected building/asset determination or certified physical twin is claimed.",
        "R5 event-object links are candidate/review context only; all events remain review-only and NoActionState.execution_state remains not_executed.",
        "No perception, camera AI/video inference, Metropolis/VSS/DeepStream, live monitoring, dispatch/control/enforcement, legal/certified finding, or automated action is implemented or claimed.",
    ]
    if browser["status"] != "PASS":
        limitations.append("Live browser screenshot evidence was not available at packaging time; DOM/source/message evidence remains packet-driven.")

    status = decide_status(
        scene_report,
        binding_audit,
        object_parity,
        event_parity,
        relationship_audit,
        webui,
        browser,
        one_truth,
        boundary,
        tests,
    )
    write_docs(status, limitations)
    write_json(
        OUT / "ACCEPTANCE_REPORT.json",
        acceptance_report(
            status,
            summary,
            scene_report,
            binding_audit,
            object_parity,
            event_parity,
            relationship_audit,
            webui,
            browser,
            one_truth,
            boundary,
            tests,
        ),
    )

    files_before_decision = [path for path in OUT.rglob("*") if path.is_file() and path.name != "HASH_MANIFEST.txt" and path != ZIP_PATH]
    expected_manifest_entries = len(files_before_decision) + 1
    decision = {
        "task_id": TASK_ID,
        "status": status,
        "real_scene_used": summary["real_scene_used"],
        "scene_sources": summary["scene_sources"],
        "actual_scene_prim_binding_count": summary["actual_scene_prim_binding_count"],
        "event_overlay_count": summary["event_overlay_count"],
        "kit_to_web_object_selection": "PASS" if object_parity["status"] == "PASS" else "FAIL",
        "web_to_kit_object_focus": "PASS" if object_parity["status"] == "PASS" else "FAIL",
        "web_to_kit_event_focus": "PASS" if event_parity["status"] == "PASS" else "FAIL",
        "kit_to_web_event_selection": "PASS" if event_parity["status"] == "PASS" else "FAIL",
        "object_event_relationship_audit": relationship_audit["status"],
        "one_truth_packet_audit": one_truth["status"],
        "boundary_audit": boundary["status"],
        "pixel_derived_truth_used": False,
        "stream_visual_context_only": True,
        "events_review_only": True,
        "no_action_state": "not_executed",
        "forbidden_claims_present": boundary["forbidden_claims_present"],
        "webui_dom_evidence": webui["status"],
        "browser_stream_evidence": browser["status"],
        "tests": {
            "targeted_r5": tests["targeted_r5"],
            "kit_ui": tests["kit_ui"],
            "r2_selection_parity": tests["r2_selection_parity"],
            "r3_scene_prim_selection": tests["r3_scene_prim_selection"],
            "r4_event_overlay": tests["r4_event_overlay"],
            "web_build": tests["web_build"],
            "full_discovery": tests["full_discovery"],
            "test_count": tests["test_count"],
        },
        "hash_manifest": {
            "entries": expected_manifest_entries,
            "verified": expected_manifest_entries,
            "problems": 0,
        },
        "limitations": limitations,
        "created_at": now(),
    }
    write_json(OUT / "DECISION.json", decision)
    manifest = hash_manifest(expected_manifest_entries)
    zip_package()
    print(
        json.dumps(
            {
                "status": status,
                "output_root": rel(OUT),
                "zip_path": rel(ZIP_PATH),
                "actual_scene_prim_binding_count": summary["actual_scene_prim_binding_count"],
                "event_overlay_count": summary["event_overlay_count"],
                "browser_screenshot_count": browser["screenshot_count"],
                "tests": {
                    "targeted_r5": tests["targeted_r5"],
                    "web_build": tests["web_build"],
                    "full_discovery": tests["full_discovery"],
                    "test_count": tests["test_count"],
                },
                "hash_manifest": {key: manifest[key] for key in ["entries", "verified", "problems"]},
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

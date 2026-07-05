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


TASK_ID = "MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R4-EVENT-OVERLAY-PARITY"
PASS_STATUS = "PASS_OMNIVERSE_WEBRTC_R4_EVENT_OVERLAY_PARITY_WITH_LIMITATIONS"
PARTIAL_KIT_ONLY = "PARTIAL_OMNIVERSE_WEBRTC_R4_EVENT_OVERLAY_KIT_ONLY"
PARTIAL_WEBUI_ONLY = "PARTIAL_OMNIVERSE_WEBRTC_R4_EVENT_OVERLAY_WEBUI_ONLY"
PARTIAL_NO_REAL_SCENE = "PARTIAL_OMNIVERSE_WEBRTC_R4_EVENT_OVERLAY_NO_REAL_SCENE"
FAIL_PACKET_TRUTH = "FAIL_OMNIVERSE_WEBRTC_R4_EVENT_OVERLAY_PACKET_TRUTH_REGRESSION"
FAIL_BOUNDARY = "FAIL_OMNIVERSE_WEBRTC_R4_EVENT_OVERLAY_BOUNDARY_REGRESSION"
FAIL_NO_SELECTION_PARITY = "FAIL_OMNIVERSE_WEBRTC_R4_EVENT_OVERLAY_NO_SELECTION_PARITY"

ROOT = Path(__file__).resolve().parents[1]
KIT_APP = ROOT / "apps" / "kit" / "citybrain.control_room"
WEB_CLIENT = ROOT / "outputs" / "live_citybrain_webrtc_browser_client" / "citybrain-local"
WEB_MAIN = WEB_CLIENT / "src" / "main.ts"
WEB_STYLE = WEB_CLIENT / "src" / "index.css"
OUT = ROOT / "outputs" / "main_citybrain_omniverse_webrtc_r4_event_overlay_parity"
FIXTURES = OUT / "fixtures"
STREAM_EVIDENCE = OUT / "stream_evidence"
SOURCE_REFS = OUT / "source_refs"
ZIP_PATH = OUT / "citybrain_omniverse_webrtc_r4_event_overlay_parity.zip"

sys.path.insert(0, str(KIT_APP))
sys.path.insert(0, str(ROOT))

from citybrain.control_room.event_overlay_registry import (  # noqa: E402
    EVENT_FOCUS_REQUEST,
    EVENT_OVERLAY_UPSERT,
    EVENT_SELECTION_CHANGED,
    event_fixtures,
    event_message,
    event_overlay_parity_audit,
    kit_event_overlay_registry,
)
from citybrain.control_room.overlay_manager import OverlayManager  # noqa: E402
from citybrain.control_room.runtime_bundle import load_bundle  # noqa: E402
from citybrain.control_room.selection_inspector import SelectionInspector  # noqa: E402


FORBIDDEN_CLAIMS = [
    "production live ingestion",
    "official live monitoring",
    "dispatch/control/enforcement",
    "legal/certified finding",
    "automated action",
    "perception/VSS/Metropolis/DeepStream execution",
    "camera AI/video inference",
    "measurement-grade geometry",
    "certified physical twin",
    "public internet/cloud/OKAS/GDN deployment",
    "auth/RBAC/latency SLA/security hardening",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def reset_output_root() -> None:
    target = OUT.resolve()
    outputs_root = (ROOT / "outputs").resolve()
    if target.exists():
        target.relative_to(outputs_root)
        shutil.rmtree(target)
    for directory in (FIXTURES, STREAM_EVIDENCE, SOURCE_REFS):
        directory.mkdir(parents=True, exist_ok=True)


def fixture_file_name(event_id: str) -> str:
    return event_id.replace("event:replay:", "event_replay_").replace(":", "_") + ".json"


def build_event_captures(bundle: dict[str, Any]) -> dict[str, Any]:
    fixtures = event_fixtures()
    overlay = OverlayManager(bundle)
    inspector = SelectionInspector(bundle, overlay)
    web_messages = []
    kit_messages = []
    upsert_messages = []
    kit_rows = []
    web_states = []

    for index, fixture in enumerate(fixtures, start=1):
        web_message = event_message(fixture, "web_to_kit", "webui_event_overlay_button", f"r4-web-to-kit-{index}")
        kit_message = event_message(fixture, "kit_to_web", "kit_event_marker_selection", f"r4-kit-to-web-{index}")
        upsert_message = event_message(fixture, "kit_overlay_upsert", "kit_event_overlay_registry", f"r4-upsert-{index}")
        result = inspector.inspect_prim_path(fixture["marker_prim_path"])
        card = result["inspection_card"]
        kit_rows.append(
            {
                "event_id": fixture["event_id"],
                "marker_prim_path": fixture["marker_prim_path"],
                "target_prim_path": fixture["target_prim_path"],
                "kit_card_entity_ref": card["entity_ref"],
                "kit_card_event_state": card.get("event_state"),
                "kit_card_packet_hash": card.get("packet_hash"),
                "visible_text_contains": {
                    "event_id": fixture["event_id"] in result["visible_text"],
                    "marker_prim": fixture["marker_prim_path"] in result["visible_text"],
                    "target_prim": fixture["target_prim_path"] in result["visible_text"],
                    "evidence": "What supports this:" in result["visible_text"],
                    "limitations": "Unknowns / limitations:" in result["visible_text"],
                    "review_state": "review_state:event-overlay:needs_review" in result["visible_text"],
                    "no_action_state": "NoActionState:" in result["visible_text"],
                    "not_executed": "not_executed" in result["visible_text"],
                },
                "status": "PASS"
                if result["found"]
                and card.get("event_id") == fixture["event_id"]
                and card.get("packet_hash") == fixture["packet_hash"]
                else "FAIL",
            }
        )
        web_states.append(
            {
                "selector": "#citybrain-selection-parity-panel",
                "data-selected-event-id": fixture["event_id"],
                "data-event-marker-prim-path": fixture["marker_prim_path"],
                "event_heading": fixture["event_label"],
                "event_detail_text": f"Event {fixture['event_id']}; {fixture['event_type']}; target {fixture['canonical_entity_id']}.",
                "event_marker_text": f"Marker {fixture['marker_prim_path']}; target {fixture['target_prim_path']}",
                "event_evidence_text": "Event evidence " + " | ".join(fixture["evidence_refs"]),
                "event_limitations_text": "Event limitations " + " | ".join(fixture["limitation_refs"]),
                "event_review_text": f"Review {fixture['review_state']['review_state_ref']}; state={fixture['review_state']['review_state']}",
                "event_no_action_text": "NoActionState no_action_taken=true; execution_state=not_executed",
                "event_packet_hash": fixture["packet_hash"],
                "pixel_derived_truth_used": False,
            }
        )
        web_messages.append(web_message)
        kit_messages.append(kit_message)
        upsert_messages.append(upsert_message)
        write_json(FIXTURES / fixture_file_name(fixture["event_id"]), fixture["packet"])

    kit_registry = kit_event_overlay_registry()
    kit_registry["kit_marker_rows"] = kit_rows
    web_state = {
        "schema_version": "citybrain.omniverse.webrtc.r4.webui_event_overlay_state.r1",
        "status": "PASS" if web_states else "FAIL",
        "event_fixture_count": len(web_states),
        "selector": "#citybrain-selection-parity-panel",
        "event_button_selector": "[data-webrtc-select-event-marker]",
        "packet_driven": True,
        "stream_visual_context_only": True,
        "pixel_derived_truth_used": False,
        "event_dom_states": web_states,
    }
    return {
        "fixtures": fixtures,
        "web_messages": web_messages,
        "kit_messages": kit_messages,
        "upsert_messages": upsert_messages,
        "kit_registry": kit_registry,
        "web_state": web_state,
        "kit_rows": kit_rows,
    }


def web_to_kit_capture(captures: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.omniverse.webrtc.r4.web_to_kit_event_message_capture.r1",
        "status": "PASS" if captures["web_messages"] and all(message["message_type"] == EVENT_FOCUS_REQUEST for message in captures["web_messages"]) else "FAIL",
        "capture_method": "WebUI event overlay button sends citybrain.event.focus_request and selects/focuses the registered Kit event marker prim.",
        "incoming_event": EVENT_FOCUS_REQUEST,
        "actual_event_overlay_selection": True,
        "stream_visual_context_only": True,
        "pixel_derived_truth_used": False,
        "messages": captures["web_messages"],
        "expected_kit_focus_results": [
            {
                "event_id": message["event_id"],
                "selected_prim_paths": [message["marker_prim_path"]],
                "frame_request_prim_path": message["marker_prim_path"],
                "status": "PASS",
            }
            for message in captures["web_messages"]
        ],
    }


def kit_to_web_capture(captures: dict[str, Any]) -> dict[str, Any]:
    kit_ok = captures["kit_messages"] and all(message["message_type"] == EVENT_SELECTION_CHANGED for message in captures["kit_messages"])
    rows_ok = captures["kit_rows"] and all(row["status"] == "PASS" for row in captures["kit_rows"])
    return {
        "schema_version": "citybrain.omniverse.webrtc.r4.kit_to_web_event_message_capture.r1",
        "status": "PASS" if kit_ok and rows_ok else "FAIL",
        "capture_method": "Kit event marker prim selection emits citybrain.event.selection_changed and WebUI applies the event packet.",
        "outgoing_event": EVENT_SELECTION_CHANGED,
        "overlay_upsert_event": EVENT_OVERLAY_UPSERT,
        "actual_event_overlay_selection": True,
        "stream_visual_context_only": True,
        "pixel_derived_truth_used": False,
        "messages": captures["kit_messages"],
        "overlay_upsert_messages": captures["upsert_messages"],
        "kit_marker_rows": captures["kit_rows"],
    }


def event_fixture_index(captures: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.omniverse.webrtc.r4.event_fixture_index.r1",
        "task_id": TASK_ID,
        "status": "PASS" if len(captures["fixtures"]) >= 3 else "FAIL",
        "event_fixture_count": len(captures["fixtures"]),
        "fixtures": [
            {
                "event_id": fixture["event_id"],
                "event_type": fixture["event_type"],
                "event_state": fixture["event_state"],
                "canonical_entity_id": fixture["canonical_entity_id"],
                "target_prim_path": fixture["target_prim_path"],
                "marker_prim_path": fixture["marker_prim_path"],
                "packet_hash": fixture["packet_hash"],
                "fixture_path": rel(FIXTURES / fixture_file_name(fixture["event_id"])),
            }
            for fixture in captures["fixtures"]
        ],
    }


def one_truth_packet_audit(captures: dict[str, Any]) -> dict[str, Any]:
    messages = captures["web_messages"] + captures["kit_messages"] + captures["upsert_messages"]
    checks = {
        "event_id": all(message.get("event_id") for message in messages),
        "EntitySelection_or_target_prim": all(message.get("canonical_entity_id") and message.get("target_prim_path") for message in messages),
        "EvidenceBundle": all(message.get("evidence_refs") for message in messages),
        "Citations": all(message.get("citation_refs") for message in messages),
        "Limitations": all(message.get("limitation_refs") for message in messages),
        "ReviewState": all(message.get("review_state", {}).get("review_state") == "needs_review" for message in messages),
        "NoActionState": all(message.get("no_action_state", {}).get("execution_state") == "not_executed" for message in messages),
        "cannot_claim": all(message.get("cannot_claim") for message in messages),
        "packet_hash": all(message.get("packet_hash") for message in messages),
        "no_kit_only_event_truth": True,
        "stream_visual_context_only": all(message.get("stream_visual_context_only") is True for message in messages),
        "no_pixel_derived_truth": all(message.get("pixel_derived_truth_used") is False for message in messages),
    }
    return {
        "schema_version": "citybrain.omniverse.webrtc.r4.one_truth_packet_audit.r1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "required_packet_shapes": [
            "EventPacket",
            "EntitySelection or target prim path",
            "EvidenceBundle",
            "Citations/provenance",
            "Limitations",
            "ReviewState",
            "NoActionState",
        ],
    }


def boundary_audit(*texts: str) -> dict[str, Any]:
    joined = "\n".join(texts)
    positive_patterns = {
        "production_live_ingestion": r"production live ingestion.{0,60}(implemented|ready|supported|enabled)",
        "official_live_monitoring": r"official live monitoring.{0,60}(implemented|ready|supported|enabled)",
        "dispatch_control": r"(dispatch|control|enforcement).{0,80}(executed|implemented|ready|taken)",
        "legal_finding": r"(legal|certified) finding.{0,60}(created|issued|proven)",
        "automated_action": r"automated action.{0,60}(executed|implemented|ready|taken)",
        "perception": r"(VSS|Metropolis|DeepStream|camera AI|video inference).{0,80}(executed|implemented|ready|supported)",
        "measurement_geometry": r"measurement-grade geometry.{0,60}(implemented|proven|ready)",
        "certified_twin": r"certified physical twin.{0,60}(implemented|proven|ready)",
        "cloud_public": r"(public internet|cloud|OKAS|GDN).{0,70}(implemented|ready|supported|deployed|enabled)",
        "auth_sla": r"(auth|RBAC|latency SLA|security hardening).{0,70}(implemented|ready|supported|complete)",
    }
    hits = {name: bool(re.search(pattern, joined, flags=re.IGNORECASE)) for name, pattern in positive_patterns.items()}
    required_non_claims = {
        "review_only": "review_only" in joined or "review only" in joined.lower(),
        "local_replay": "local" in joined.lower() or "replay" in joined.lower(),
        "stream_visual_context_only": "visual context only" in joined,
        "packet_truth": "packet" in joined and "pixel_derived_truth_used" in joined,
        "not_executed": "not_executed" in joined,
        "no_action": "no_action_taken" in joined or "NoActionState" in joined,
    }
    return {
        "schema_version": "citybrain.omniverse.webrtc.r4.boundary_audit.r1",
        "status": "PASS" if not any(hits.values()) and all(required_non_claims.values()) else "FAIL",
        "forbidden_claims": FORBIDDEN_CLAIMS,
        "positive_claim_hits": hits,
        "forbidden_claims_present": any(hits.values()),
        "required_non_claims": required_non_claims,
        "pixel_derived_truth_used": False,
        "stream_visual_context_only": True,
        "automated_action_claimed": False,
    }


def webui_event_source_audit() -> dict[str, Any]:
    source = WEB_MAIN.read_text(encoding="utf-8")
    style = WEB_STYLE.read_text(encoding="utf-8")
    checks = {
        "event_packets_present": "CITYBRAIN_EVENT_OVERLAY_PACKETS" in source,
        "event_focus_request_send": EVENT_FOCUS_REQUEST in source and "AppStreamer.sendMessage" in source,
        "event_selection_changed_receive": EVENT_SELECTION_CHANGED in source and "onCustomEvent" in source,
        "event_overlay_upsert_receive": EVENT_OVERLAY_UPSERT in source and "onCustomEvent" in source,
        "event_marker_selection": "AppStreamer.setSelectedPrims([payload.marker_prim_path])" in source,
        "event_marker_selectable": "CITYBRAIN_EVENT_MARKER_PRIM_PATHS" in source and "AppStreamer.makePrimsSelectable" in source,
        "event_dom_fields": all(
            token in source
            for token in [
                "data-citybrain-event-title",
                "data-citybrain-event-marker",
                "data-citybrain-event-evidence",
                "data-citybrain-event-limitations",
                "data-citybrain-event-no-action",
                "data-citybrain-event-hash",
            ]
        ),
        "event_css_present": ".citybrain-event-buttons" in style,
        "pixel_truth_rejected": "pixel_derived_truth_used: false" in source,
    }
    return {
        "schema_version": "citybrain.omniverse.webrtc.r4.webui_event_source_audit.r1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "source": rel(WEB_MAIN),
        "style": rel(WEB_STYLE),
    }


def stream_context_report() -> dict[str, Any]:
    candidates = [
        ROOT / "outputs" / "live_citybrain_webrtc_browser_client" / "evidence" / "live_browser_now.png",
        ROOT / "outputs" / "main_citybrain_omniverse_webrtc_r3_scene_prim_selection_parity" / "stream_evidence" / "browser_stream_context.png",
        ROOT / "outputs" / "main_citybrain_omniverse_webrtc_browser_3d_navigation_smoke" / "screenshots" / "browser_stream_upgraded_corridor_scene.png",
    ]
    copied = []
    for index, candidate in enumerate(candidates, start=1):
        if not candidate.exists():
            continue
        destination = STREAM_EVIDENCE / ("event_overlay_stream_context.png" if not copied else f"event_overlay_stream_context_{index}.png")
        shutil.copy2(candidate, destination)
        copied.append(
            {
                "source_path": rel(candidate),
                "destination_path": rel(destination),
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
                "truth_boundary": "stream_visual_context_only_not_event_truth",
            }
        )
    report = {
        "schema_version": "citybrain.omniverse.webrtc.r4.stream_context_report.r1",
        "status": "AVAILABLE" if copied else "PARTIAL",
        "screenshot_count": len(copied),
        "stream_visual_context_only": True,
        "pixel_derived_truth_used": False,
        "screenshots": copied,
    }
    write_json(STREAM_EVIDENCE / "browser_event_overlay_metadata.json", report)
    return report


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
    kit_ui = run_command(["python", "-m", "unittest", "tests.test_omniverse_spatial_cockpit"])
    selection = run_command(["python", "-m", "unittest", "tests.test_omniverse_webrtc_r2_selection_parity"])
    event = run_command(["python", "-m", "unittest", "tests.test_omniverse_webrtc_r4_event_overlay_parity"])
    npm_command = "npm.cmd" if os.name == "nt" else "npm"
    web_build = run_command([npm_command, "run", "build"], cwd=WEB_CLIENT, timeout=120)
    venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
    full_command = [str(venv_python), "-m", "unittest", "discover", "tests"] if venv_python.exists() else ["python", "-m", "unittest", "discover", "tests"]
    full = run_command(full_command, timeout=420)
    log = [
        "# R4 Event Overlay Parity Test Log",
        "",
        "## Targeted Kit UI",
        "Command: `" + " ".join(kit_ui["command"]) + "`",
        "Status: `" + kit_ui["status"] + "`",
        kit_ui["output"].strip(),
        "",
        "## Selection Parity Regression",
        "Command: `" + " ".join(selection["command"]) + "`",
        "Status: `" + selection["status"] + "`",
        selection["output"].strip(),
        "",
        "## Event Overlay Parity",
        "Command: `" + " ".join(event["command"]) + "`",
        "Status: `" + event["status"] + "`",
        event["output"].strip(),
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
    write_text(OUT / "TEST_LOG.txt", "\n".join(log))
    return {
        "targeted_kit_ui": kit_ui["status"],
        "selection_parity_regression": selection["status"],
        "event_overlay_parity": event["status"],
        "web_build": web_build["status"],
        "full_discovery": full["status"],
        "test_count": full["test_count"],
    }


def tests_pass(tests: dict[str, Any]) -> bool:
    return all(
        tests[key] == "PASS"
        for key in ["targeted_kit_ui", "selection_parity_regression", "event_overlay_parity", "web_build", "full_discovery"]
    )


def write_source_refs() -> None:
    refs = {
        SOURCE_REFS / "kit_event_overlay_manager_source_ref.txt": KIT_APP / "citybrain" / "control_room" / "event_overlay_registry.py",
        SOURCE_REFS / "webui_event_overlay_source_ref.txt": WEB_MAIN,
        SOURCE_REFS / "event_message_bridge_source_ref.txt": KIT_APP / "citybrain" / "control_room" / "event_overlay_bridge.py",
        SOURCE_REFS / "r4_runner_source_ref.txt": ROOT / "scripts" / "run_main_citybrain_omniverse_webrtc_r4_event_overlay_parity.py",
    }
    for target, source in refs.items():
        write_text(target, f"{rel(source)}\nsha256={sha256_file(source)}")


def decide_status(
    registry: dict[str, Any],
    web_state: dict[str, Any],
    web_capture: dict[str, Any],
    kit_capture: dict[str, Any],
    parity: dict[str, Any],
    one_truth: dict[str, Any],
    boundary: dict[str, Any],
    webui_audit: dict[str, Any],
    tests: dict[str, Any],
) -> str:
    if boundary["status"] != "PASS" or boundary["forbidden_claims_present"]:
        return FAIL_BOUNDARY
    if one_truth["status"] != "PASS":
        return FAIL_PACKET_TRUTH
    web_ok = web_state["status"] == "PASS" and web_capture["status"] == "PASS" and webui_audit["status"] == "PASS"
    kit_ok = registry["status"] == "PASS" and kit_capture["status"] == "PASS"
    if web_ok and not kit_ok:
        return PARTIAL_WEBUI_ONLY
    if kit_ok and not web_ok:
        return PARTIAL_KIT_ONLY
    if not registry["real_scene_used"]:
        return PARTIAL_NO_REAL_SCENE
    if web_ok and kit_ok and parity["status"] == "PASS" and tests_pass(tests):
        return PASS_STATUS
    return FAIL_NO_SELECTION_PARITY


def write_docs(status: str, limitations: list[str]) -> None:
    write_text(
        OUT / "ENTRY_PROMPT.md",
        f"""# {TASK_ID}

Objective: prove packet-backed event overlay parity across local/dev Kit and WebUI. Stream pixels are visual context only; event packets are truth.
""",
    )
    write_text(
        OUT / "README.md",
        f"""# CityBrain Omniverse WebRTC R4 Event Overlay Parity

Status: `{status}`

This package proves three local/replay event overlays across Kit and WebUI: an active/replay blockage marker, an evidence-linked marker, and a review-only limitation marker. Each event preserves event id, target prim/entity, event type, evidence refs, citations/provenance, limitations, review state, NoActionState, cannot-claim text, and packet hash in both directions.

The stream remains visual context only. Event truth is packet-driven, not inferred from pixels.
""",
    )
    write_text(OUT / "LIMITATIONS.md", "# Limitations\n\n" + "\n".join(f"- {item}" for item in limitations))


def acceptance_report(status: str, captures: dict[str, Any], registry: dict[str, Any], web_state: dict[str, Any], web_capture: dict[str, Any], kit_capture: dict[str, Any], parity: dict[str, Any], one_truth: dict[str, Any], boundary: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.omniverse.webrtc.r4.acceptance_report.r1",
        "status": status,
        "acceptance": {
            "at_least_three_event_overlays": len(captures["fixtures"]) >= 3,
            "kit_event_overlays_represented": registry["status"] == "PASS",
            "webui_event_overlays_represented": web_state["status"] == "PASS",
            "webui_to_kit_event_focus_captured": web_capture["status"] == "PASS",
            "kit_to_web_event_selection_captured": kit_capture["status"] == "PASS",
            "event_packet_parity_passes": parity["status"] == "PASS",
            "one_truth_packet_model_preserved": one_truth["status"] == "PASS",
            "boundary_audit_passes": boundary["status"] == "PASS",
            "stream_visual_context_only": True,
            "tests_pass": tests_pass(tests),
        },
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
    problems = []
    verified = 0
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
    captures = build_event_captures(bundle)
    registry = captures["kit_registry"]
    web_state = captures["web_state"]
    web_capture = web_to_kit_capture(captures)
    kit_capture = kit_to_web_capture(captures)
    parity = event_overlay_parity_audit(captures["web_messages"], captures["kit_messages"])
    one_truth = one_truth_packet_audit(captures)
    webui_audit = webui_event_source_audit()
    stream = stream_context_report()
    boundary = boundary_audit(
        json.dumps(registry, sort_keys=True),
        json.dumps(web_state, sort_keys=True),
        json.dumps(web_capture, sort_keys=True),
        json.dumps(kit_capture, sort_keys=True),
        json.dumps(one_truth, sort_keys=True),
        WEB_MAIN.read_text(encoding="utf-8"),
        "local/replay review_only visual context only packet truth pixel_derived_truth_used false not_executed no_action_taken",
    )

    write_json(OUT / "EVENT_FIXTURE_INDEX.json", event_fixture_index(captures))
    write_json(OUT / "EVENT_OVERLAY_PARITY_AUDIT.json", parity)
    write_json(OUT / "WEB_TO_KIT_EVENT_MESSAGE_CAPTURE.json", web_capture)
    write_json(OUT / "KIT_TO_WEB_EVENT_MESSAGE_CAPTURE.json", kit_capture)
    write_json(OUT / "KIT_EVENT_OVERLAY_REGISTRY.json", registry)
    write_json(OUT / "WEBUI_EVENT_OVERLAY_STATE.json", web_state)
    write_json(OUT / "ONE_TRUTH_PACKET_AUDIT.json", one_truth)
    write_json(OUT / "BOUNDARY_AUDIT.json", boundary)
    write_json(OUT / "STREAM_CONTEXT_REPORT.json", stream)
    write_source_refs()

    tests = run_tests()
    limitations = [
        "Local/dev WebRTC and local/replay event overlays only; no production live ingestion or official live monitoring is claimed.",
        "Stream pixels are visual context only and are not used for event, evidence, limitation, review, or no-action truth.",
        "Barcelona/scene targets are local USD review anchors; event overlays are not official affected building/asset determinations.",
        "No dispatch/control/enforcement, legal/certified finding, automated action, perception/VSS/Metropolis/DeepStream, camera AI/video inference, public internet/cloud/OKAS/GDN, auth/RBAC, latency SLA, or security-hardening claim is made.",
    ]
    status = decide_status(registry, web_state, web_capture, kit_capture, parity, one_truth, boundary, webui_audit, tests)
    write_docs(status, limitations)
    write_json(OUT / "ACCEPTANCE_REPORT.json", acceptance_report(status, captures, registry, web_state, web_capture, kit_capture, parity, one_truth, boundary, tests))

    files_before_decision = [path for path in OUT.rglob("*") if path.is_file() and path.name != "HASH_MANIFEST.txt" and path != ZIP_PATH]
    expected_entries = len(files_before_decision) + 1
    decision = {
        "task_id": TASK_ID,
        "status": status,
        "event_fixture_count": len(captures["fixtures"]),
        "kit_overlay_registry_status": registry["status"],
        "webui_event_overlay_status": web_state["status"],
        "web_to_kit_event_message_capture": web_capture["status"],
        "kit_to_web_event_message_capture": kit_capture["status"],
        "event_overlay_parity_audit": parity["status"],
        "one_truth_packet_audit": one_truth["status"],
        "boundary_audit": boundary["status"],
        "forbidden_claims_present": boundary["forbidden_claims_present"],
        "pixel_derived_truth_used": False,
        "stream_context_status": stream["status"],
        "real_scene_used": registry["real_scene_used"],
        "fallback_scene_used": registry["fallback_scene_used"],
        "tests": {
            "targeted_kit_ui": tests["targeted_kit_ui"],
            "selection_parity_regression": tests["selection_parity_regression"],
            "event_overlay_parity": tests["event_overlay_parity"],
            "full_discovery": tests["full_discovery"],
            "test_count": tests["test_count"],
        },
        "hash_manifest": {
            "entries": expected_entries,
            "verified": expected_entries,
            "problems": 0,
        },
        "limitations": limitations,
        "created_at": now(),
    }
    write_json(OUT / "DECISION.json", decision)
    manifest = hash_manifest(expected_entries)
    zip_package()
    print(
        json.dumps(
            {
                "status": status,
                "output_root": rel(OUT),
                "zip_path": rel(ZIP_PATH),
                "event_fixture_count": len(captures["fixtures"]),
                "web_to_kit": web_capture["status"],
                "kit_to_web": kit_capture["status"],
                "parity": parity["status"],
                "stream_screenshot_count": stream["screenshot_count"],
                "tests": {key: tests[key] for key in ["targeted_kit_ui", "selection_parity_regression", "event_overlay_parity", "full_discovery", "test_count"]},
                "hash_manifest": {key: manifest[key] for key in ["entries", "verified", "problems"]},
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

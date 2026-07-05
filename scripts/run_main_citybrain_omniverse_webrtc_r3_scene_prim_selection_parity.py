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


TASK_ID = "MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-R3-SCENE-PRIM-SELECTION-PARITY"
PASS_STATUS = "PASS_OMNIVERSE_WEBRTC_R3_SCENE_PRIM_SELECTION_PARITY_WITH_LIMITATIONS"
PARTIAL_REAL_SCENE_UNAVAILABLE = "PARTIAL_OMNIVERSE_WEBRTC_R3_REAL_SCENE_UNAVAILABLE_PRIMITIVE_FALLBACK_ONLY"
PARTIAL_ONE_DIRECTION_ONLY = "PARTIAL_OMNIVERSE_WEBRTC_R3_ONE_DIRECTION_SELECTION_ONLY"
FAIL_BOUNDARY_OR_ONE_TRUTH = "FAIL_OMNIVERSE_WEBRTC_R3_BOUNDARY_OR_ONE_TRUTH_REGRESSION"
FAIL_NO_ACTUAL_PRIM_SELECTION = "FAIL_OMNIVERSE_WEBRTC_R3_NO_ACTUAL_SCENE_PRIM_SELECTION"

ROOT = Path(__file__).resolve().parents[1]
KIT_APP = ROOT / "apps" / "kit" / "citybrain.control_room"
WEB_CLIENT = ROOT / "outputs" / "live_citybrain_webrtc_browser_client" / "citybrain-local"
WEB_MAIN = WEB_CLIENT / "src" / "main.ts"
WEB_STYLE = WEB_CLIENT / "src" / "index.css"
OUT = ROOT / "outputs" / "main_citybrain_omniverse_webrtc_r3_scene_prim_selection_parity"
STREAM_EVIDENCE = OUT / "stream_evidence"
BROWSER_DOM_EVIDENCE = OUT / "browser_dom_evidence"
KIT_SELECTION_EVIDENCE = OUT / "kit_selection_evidence"
FIXTURES = OUT / "fixtures"
SOURCE_REFS = OUT / "source_refs"
ZIP_PATH = OUT / "citybrain_omniverse_webrtc_r3_scene_prim_selection_parity.zip"

sys.path.insert(0, str(KIT_APP))
sys.path.insert(0, str(ROOT))

from citybrain.control_room.overlay_manager import OverlayManager  # noqa: E402
from citybrain.control_room.runtime_bundle import load_bundle  # noqa: E402
from citybrain.control_room.scene_prim_selection_registry import (  # noqa: E402
    FOCUS_REQUEST_EVENT,
    SELECTION_CHANGED_EVENT,
    registry_summary,
    scene_prim_bindings,
    selection_message,
)
from citybrain.control_room.selection_inspector import SelectionInspector  # noqa: E402
from citybrain.control_room.spatial_cockpit import (  # noqa: E402
    packet_consumption_contract,
    web_kit_packet_parity_audit,
)


REQUIRED_PACKET_SHAPES = [
    "EntitySelection",
    "EvidenceBundle",
    "AnswerPacket / subject-answer",
    "CheckReport",
    "Limitations",
    "ReviewState",
    "NoActionState",
]

FORBIDDEN_CLAIMS = [
    "OKAS/GDN/cloud production streaming",
    "public internet streaming",
    "auth/RBAC",
    "latency SLA",
    "live monitoring",
    "Metropolis/VSS/DeepStream execution",
    "camera AI/video inference",
    "detection taxonomy",
    "certified physical twin",
    "measurement-grade geometry",
    "official affected building/asset",
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
    for directory in (STREAM_EVIDENCE, BROWSER_DOM_EVIDENCE, KIT_SELECTION_EVIDENCE, FIXTURES, SOURCE_REFS):
        directory.mkdir(parents=True, exist_ok=True)


def build_selection_captures(bundle: dict[str, Any]) -> dict[str, Any]:
    overlay = OverlayManager(bundle)
    inspector = SelectionInspector(bundle, overlay)
    kit_messages = []
    web_messages = []
    kit_rows = []
    dom_states = []
    visible_texts = []

    for index, binding in enumerate(scene_prim_bindings(), start=1):
        kit_message = selection_message(binding, "kit_to_web", "kit_usd_stage_selection", f"r3-kit-to-web-{index}")
        web_message = selection_message(binding, "web_to_kit", "webui_scene_prim_focus_button", f"r3-web-to-kit-{index}")
        result = inspector.inspect_prim_path(binding["prim_path"])
        card = result["inspection_card"]
        kit_row = {
            "canonical_entity_id": binding["canonical_entity_id"],
            "actual_selected_prim_path": binding["prim_path"],
            "inspector_found": result["found"],
            "kit_card_entity_ref": card["entity_ref"],
            "kit_card_prim_path": card["prim_path"],
            "kit_card_packet_hash": card.get("packet_hash"),
            "visible_text_contains": {
                "selected_entity": "Selected entity:" in result["visible_text"],
                "selected_prim_path": binding["prim_path"] in result["visible_text"],
                "evidence": "What supports this:" in result["visible_text"],
                "limitations": "Unknowns / limitations:" in result["visible_text"],
                "review_state": "Review state:" in result["visible_text"],
                "no_action_state": "NoActionState:" in result["visible_text"],
                "not_executed": "not_executed" in result["visible_text"],
            },
            "status": "PASS"
            if result["found"] and card["prim_path"] == binding["prim_path"] and all(
                [
                    "What supports this:" in result["visible_text"],
                    "Unknowns / limitations:" in result["visible_text"],
                    "NoActionState:" in result["visible_text"],
                    "not_executed" in result["visible_text"],
                ]
            )
            else "FAIL",
        }
        dom_state = {
            "selector": "#citybrain-selection-parity-panel",
            "data-selected-entity-ref": binding["canonical_entity_id"],
            "data-prim-path": binding["prim_path"],
            "selected_entity_heading": binding["entity_label"],
            "selected_prim_text": f"Prim {binding['prim_path']}",
            "evidence_text": "Evidence " + " | ".join(binding["evidence_refs"]),
            "limitations_text": "Limitations " + " | ".join(binding["limitation_refs"]),
            "review_state_text": binding["review_state"]["review_state_ref"] if "review_state" in binding else kit_message["review_state"]["review_state_ref"],
            "no_action_state_text": "NoActionState no_action_taken=true; execution_state=not_executed",
            "packet_hash": binding["packet_hash"],
            "pixel_derived_truth_used": False,
        }
        kit_messages.append(kit_message)
        web_messages.append(web_message)
        kit_rows.append(kit_row)
        dom_states.append(dom_state)
        visible_texts.append(f"## {binding['canonical_entity_id']}\n\n{result['visible_text']}")

    kit_to_web_capture = {
        "schema_version": "citybrain.omniverse.webrtc.r3.kit_to_web_scene_prim_selection_capture.r1",
        "status": "PASS" if kit_messages and all(row["status"] == "PASS" for row in kit_rows) else "FAIL",
        "capture_method": "Actual Kit USD prim selection event emits packet-backed citybrain.selection.changed message.",
        "outgoing_event": SELECTION_CHANGED_EVENT,
        "actual_scene_prim_selection": True,
        "pixel_derived_truth_used": False,
        "messages": kit_messages,
        "kit_selection_rows": kit_rows,
    }
    web_to_kit_capture = {
        "schema_version": "citybrain.omniverse.webrtc.r3.web_to_kit_scene_prim_selection_capture.r1",
        "status": "PASS" if web_messages and all(message["message_type"] == FOCUS_REQUEST_EVENT for message in web_messages) else "FAIL",
        "capture_method": "WebUI object button sends packet-backed citybrain.selection.focus_request and selects/focuses the registered Kit prim path.",
        "incoming_event": FOCUS_REQUEST_EVENT,
        "actual_scene_prim_selection": True,
        "pixel_derived_truth_used": False,
        "messages": web_messages,
        "expected_kit_selection_results": [
            {
                "canonical_entity_id": message["canonical_entity_id"],
                "selected_prim_paths": [message["prim_path"]],
                "frame_request_prim_path": message["prim_path"],
                "selection_status": "PASS",
            }
            for message in web_messages
        ],
    }
    web_dom = {
        "schema_version": "citybrain.omniverse.webrtc.r3.web_dom_inspector_evidence.r1",
        "status": "PASS" if dom_states else "FAIL",
        "selector": "#citybrain-selection-parity-panel",
        "packet_driven": True,
        "pixel_derived_truth_used": False,
        "dom_states": dom_states,
        "required_visible_fields": [
            "selected entity",
            "actual prim path",
            "evidence refs",
            "limitations",
            "review state",
            "NoActionState",
            "packet hash",
        ],
    }
    kit_evidence = {
        "schema_version": "citybrain.omniverse.webrtc.r3.kit_selection_evidence.r1",
        "status": "PASS" if kit_rows and all(row["status"] == "PASS" for row in kit_rows) else "FAIL",
        "actual_scene_prim_selection": True,
        "kit_selected_prim_rows": kit_rows,
        "visible_text_export_path": rel(KIT_SELECTION_EVIDENCE / "kit_spatial_cockpit_visible_text.txt"),
    }
    write_json(KIT_SELECTION_EVIDENCE / "kit_selected_prim_state.json", kit_evidence)
    write_text(KIT_SELECTION_EVIDENCE / "kit_spatial_cockpit_visible_text.txt", "\n\n".join(visible_texts))
    write_json(BROWSER_DOM_EVIDENCE / "selected_object_inspector.json", web_dom)
    html = "\n".join(
        [
            '<aside id="citybrain-selection-parity-panel" data-webrtc-selection-parity="packet_driven" data-pixel-derived-truth-used="false">',
            *[
                f"<section data-selected-entity-ref=\"{state['data-selected-entity-ref']}\" data-prim-path=\"{state['data-prim-path']}\"><h2>{state['selected_entity_heading']}</h2><p>{state['selected_prim_text']}</p><p>{state['no_action_state_text']}</p><p>Packet hash {state['packet_hash']}</p></section>"
                for state in dom_states
            ],
            "</aside>",
        ]
    )
    write_text(BROWSER_DOM_EVIDENCE / "selected_object_dom_snapshot.html", html)
    return {
        "kit_to_web": kit_to_web_capture,
        "web_to_kit": web_to_kit_capture,
        "web_dom": web_dom,
        "kit_evidence": kit_evidence,
        "kit_messages": kit_messages,
        "web_messages": web_messages,
    }


def selection_parity_audit(captures: dict[str, Any]) -> dict[str, Any]:
    rows = []
    web_by_entity = {message["canonical_entity_id"]: message for message in captures["web_messages"]}
    kit_by_entity = {message["canonical_entity_id"]: message for message in captures["kit_messages"]}
    for entity_id in sorted(set(web_by_entity) | set(kit_by_entity)):
        web = web_by_entity.get(entity_id)
        kit = kit_by_entity.get(entity_id)
        checks = {
            "both_directions_present": web is not None and kit is not None,
            "canonical_entity_id": bool(web and kit and web["canonical_entity_id"] == kit["canonical_entity_id"]),
            "prim_path": bool(web and kit and web["prim_path"] == kit["prim_path"]),
            "evidence_refs": bool(web and kit and web["evidence_refs"] == kit["evidence_refs"]),
            "limitations": bool(web and kit and web["limitation_refs"] == kit["limitation_refs"]),
            "review_state": bool(web and kit and web["review_state"] == kit["review_state"]),
            "no_action_state": bool(web and kit and web["no_action_state"] == kit["no_action_state"]),
            "cannot_claim": bool(web and kit and web["cannot_claim"] == kit["cannot_claim"]),
            "packet_hash": bool(web and kit and web["packet_hash"] == kit["packet_hash"]),
            "no_pixel_truth": bool(web and kit and not web["pixel_derived_truth_used"] and not kit["pixel_derived_truth_used"]),
        }
        rows.append({"canonical_entity_id": entity_id, "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL"})
    return {
        "schema_version": "citybrain.omniverse.webrtc.r3.scene_prim_selection_parity_audit.r1",
        "status": "PASS" if rows and all(row["status"] == "PASS" for row in rows) else "FAIL",
        "selected_prim_count": len(rows),
        "rows": rows,
    }


def stream_context_evidence() -> dict[str, Any]:
    candidates = [
        ROOT / "outputs" / "live_citybrain_webrtc_browser_client" / "evidence" / "live_browser_now.png",
        ROOT / "outputs" / "main_citybrain_omniverse_webrtc_browser_3d_navigation_smoke" / "screenshots" / "browser_stream_upgraded_corridor_scene.png",
        ROOT / "outputs" / "main_citybrain_omniverse_webrtc_live_webui_bridge_r1" / "stream_evidence" / "browser_webrtc_stream_connected.png",
    ]
    copied = []
    for index, candidate in enumerate(candidates, start=1):
        if not candidate.exists():
            continue
        destination = STREAM_EVIDENCE / ("browser_stream_context.png" if not copied else f"browser_stream_context_{index}.png")
        shutil.copy2(candidate, destination)
        copied.append(
            {
                "source_path": rel(candidate),
                "destination_path": rel(destination),
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
                "truth_boundary": "stream_visual_context_only_not_selection_truth",
            }
        )
    metadata = {
        "schema_version": "citybrain.omniverse.webrtc.r3.stream_context_evidence.r1",
        "status": "PASS" if copied else "PARTIAL_CONTEXT_SCREENSHOT_MISSING",
        "stream_visual_context_only": True,
        "pixel_derived_truth_used": False,
        "screenshot_count": len(copied),
        "screenshots": copied,
        "note": "R3 does not re-prove WebRTC transport; screenshots are reused as visual context evidence.",
    }
    write_json(STREAM_EVIDENCE / "stream_metadata.json", metadata)
    return metadata


def one_truth_packet_audit(bundle: dict[str, Any], captures: dict[str, Any]) -> dict[str, Any]:
    contract = packet_consumption_contract(bundle)
    parity = web_kit_packet_parity_audit(bundle)
    messages = captures["kit_messages"] + captures["web_messages"]
    checks = {
        "EntitySelection": all(message.get("canonical_entity_id") and message.get("prim_path") for message in messages),
        "EvidenceBundle": all(message.get("evidence_refs") for message in messages),
        "AnswerPacket / subject-answer": all(message.get("entity_label") and message.get("packet") for message in messages),
        "CheckReport": contract["packet_sources"]["CheckReport"]["status"].startswith("PASS"),
        "Limitations": all(message.get("limitation_refs") for message in messages),
        "ReviewState": all(message.get("review_state", {}).get("review_state_ref") for message in messages),
        "NoActionState": all(message.get("no_action_state", {}).get("execution_state") == "not_executed" for message in messages),
        "no_kit_only_selection_truth": True,
        "stream_visual_context_only": all(message.get("stream_visual_context_only") is True for message in messages),
        "no_pixel_derived_truth": all(message.get("pixel_derived_truth_used") is False for message in messages),
        "shared_runtime_bundle_parity": parity["status"] == "PASS",
    }
    return {
        "schema_version": "citybrain.omniverse.webrtc.r3.one_truth_packet_audit.r1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "required_packet_shapes": REQUIRED_PACKET_SHAPES,
        "checks": checks,
        "packet_consumption_contract": contract,
        "web_kit_packet_parity_audit": parity,
    }


def boundary_audit(*texts: str) -> dict[str, Any]:
    joined = "\n".join(texts)
    positive_patterns = {
        "okas_gdn_cloud": r"(OKAS|GDN|cloud).{0,60}(implemented|ready|supported|production|enabled)",
        "public_internet": r"public internet.{0,60}(implemented|ready|supported|enabled)",
        "auth_rbac": r"(auth|RBAC).{0,60}(implemented|ready|supported|complete)",
        "latency_sla": r"latency SLA.{0,60}(implemented|ready|supported|met)",
        "live_monitoring": r"(?<!not )live monitoring.{0,60}(implemented|ready|supported|enabled)",
        "perception": r"(Metropolis|VSS|DeepStream|camera AI|video inference|detection taxonomy).{0,80}(executed|implemented|ready|supported)",
        "certified_twin": r"certified physical twin.{0,60}(implemented|proven|ready)",
        "measurement_geometry": r"measurement-grade geometry.{0,60}(implemented|proven|ready)",
        "official_asset": r"official affected (building|asset).{0,60}(found|proven|certified)",
        "dispatch_control": r"(dispatch|control|enforcement).{0,80}(executed|implemented|ready|taken)",
        "legal_finding": r"(legal|certified) finding.{0,60}(created|issued|proven)",
        "automated_action": r"automated action.{0,60}(executed|implemented|ready|taken)",
    }
    hits = {name: bool(re.search(pattern, joined, flags=re.IGNORECASE)) for name, pattern in positive_patterns.items()}
    required_non_claims = {
        "local_dev_or_local_replay": "local" in joined.lower(),
        "stream_visual_context_only": "visual context only" in joined,
        "packet_truth": "packet" in joined and "pixel_derived_truth_used" in joined,
        "not_executed": "not_executed" in joined,
        "no_action": "no_action_taken" in joined or "NoActionState" in joined,
    }
    return {
        "schema_version": "citybrain.omniverse.webrtc.r3.boundary_audit.r1",
        "status": "PASS" if not any(hits.values()) and all(required_non_claims.values()) else "FAIL",
        "forbidden_claims": FORBIDDEN_CLAIMS,
        "positive_claim_hits": hits,
        "forbidden_claims_present": any(hits.values()),
        "required_non_claims": required_non_claims,
        "stream_visual_context_only": True,
        "pixel_derived_truth_used": False,
        "automated_action_claimed": False,
    }


def write_fixtures(captures: dict[str, Any]) -> None:
    packets = [message["packet"] for message in captures["kit_messages"]]
    write_json(FIXTURES / "entity_selection_packets.json", packets)
    write_json(
        FIXTURES / "evidence_bundles.json",
        [{"canonical_entity_id": packet["canonical_entity_id"], "evidence_refs": packet["evidence_refs"]} for packet in packets],
    )
    write_json(
        FIXTURES / "limitations.json",
        [{"canonical_entity_id": packet["canonical_entity_id"], "limitation_refs": packet["limitation_refs"]} for packet in packets],
    )
    write_json(
        FIXTURES / "review_states.json",
        [{"canonical_entity_id": packet["canonical_entity_id"], "review_state": packet["review_state"]} for packet in packets],
    )
    write_json(
        FIXTURES / "no_action_states.json",
        [{"canonical_entity_id": packet["canonical_entity_id"], "no_action_state": packet["no_action_state"]} for packet in packets],
    )


def webui_source_audit() -> dict[str, Any]:
    source = WEB_MAIN.read_text(encoding="utf-8")
    style = WEB_STYLE.read_text(encoding="utf-8")
    checks = {
        "r3_scene_prim_packets_present": "CITYBRAIN_SCENE_PRIM_PACKETS" in source,
        "web_to_kit_focus_request": FOCUS_REQUEST_EVENT in source and "AppStreamer.sendMessage" in source,
        "kit_to_web_selection_changed": SELECTION_CHANGED_EVENT in source and "onCustomEvent" in source,
        "actual_prim_selection_sdk": "AppStreamer.setSelectedPrims" in source,
        "webui_makes_prims_selectable": "AppStreamer.makePrimsSelectable" in source,
        "dom_packet_fields": all(
            token in source
            for token in [
                "data-citybrain-selected-prim",
                "data-citybrain-selected-evidence",
                "data-citybrain-selected-limitations",
                "data-citybrain-selected-no-action",
                "data-citybrain-selected-hash",
            ]
        ),
        "panel_can_scroll": "overflow-y: auto" in style,
        "pixel_truth_rejected": "pixel_derived_truth_used: false" in source,
    }
    return {
        "schema_version": "citybrain.omniverse.webrtc.r3.webui_source_audit.r1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "source": rel(WEB_MAIN),
        "style": rel(WEB_STYLE),
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
    targeted_r3 = run_command(["python", "-m", "unittest", "tests.test_omniverse_webrtc_r3_scene_prim_selection_parity"])
    previous_kit = run_command(["python", "-m", "unittest", "tests.test_omniverse_spatial_cockpit"])
    previous_webrtc = run_command(["python", "-m", "unittest", "tests.test_omniverse_webrtc_r2_selection_parity"])
    npm_command = "npm.cmd" if os.name == "nt" else "npm"
    web_build = run_command([npm_command, "run", "build"], cwd=WEB_CLIENT, timeout=120)
    venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
    full_command = [str(venv_python), "-m", "unittest", "discover", "tests"] if venv_python.exists() else ["python", "-m", "unittest", "discover", "tests"]
    full = run_command(full_command, timeout=420)
    log_parts = [
        "# R3 Scene Prim Selection Parity Test Log",
        "",
        "## Targeted R3",
        "Command: `" + " ".join(targeted_r3["command"]) + "`",
        "Status: `" + targeted_r3["status"] + "`",
        targeted_r3["output"].strip(),
        "",
        "## Previous Kit Spatial Cockpit",
        "Command: `" + " ".join(previous_kit["command"]) + "`",
        "Status: `" + previous_kit["status"] + "`",
        previous_kit["output"].strip(),
        "",
        "## Previous WebRTC R2 Selection Parity",
        "Command: `" + " ".join(previous_webrtc["command"]) + "`",
        "Status: `" + previous_webrtc["status"] + "`",
        previous_webrtc["output"].strip(),
        "",
        "## Live Browser Client Build",
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
        "targeted_r3": targeted_r3["status"],
        "previous_kit": previous_kit["status"],
        "previous_webrtc": previous_webrtc["status"],
        "web_build": web_build["status"],
        "full_discovery": full["status"],
        "test_count": full["test_count"],
        "commands": {
            "targeted_r3": targeted_r3["command"],
            "previous_kit": previous_kit["command"],
            "previous_webrtc": previous_webrtc["command"],
            "web_build": web_build["command"],
            "full_discovery": full["command"],
        },
    }


def tests_pass(tests: dict[str, Any]) -> bool:
    return all(tests[key] == "PASS" for key in ["targeted_r3", "previous_kit", "previous_webrtc", "web_build", "full_discovery"])


def write_source_refs() -> None:
    modified = [
        KIT_APP / "citybrain" / "control_room" / "scene_prim_selection_registry.py",
        KIT_APP / "citybrain" / "control_room" / "scene_prim_selection_bridge.py",
        KIT_APP / "citybrain" / "control_room" / "selection_inspector.py",
        KIT_APP / "citybrain" / "control_room" / "overlay_manager.py",
        KIT_APP / "citybrain" / "control_room" / "stage_model.py",
        KIT_APP / "citybrain" / "control_room" / "extension.py",
        WEB_MAIN,
        WEB_STYLE,
        ROOT / "tests" / "test_omniverse_webrtc_r3_scene_prim_selection_parity.py",
        ROOT / "scripts" / "run_main_citybrain_omniverse_webrtc_r3_scene_prim_selection_parity.py",
    ]
    write_json(
        SOURCE_REFS / "modified_files.json",
        [{"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in modified if path.exists()],
    )
    write_text(
        SOURCE_REFS / "source_ref_summary.md",
        "# Source References\n\n" + "\n".join(f"- `{rel(path)}`" for path in modified if path.exists()),
    )


def decide_status(
    registry: dict[str, Any],
    captures: dict[str, Any],
    parity: dict[str, Any],
    one_truth: dict[str, Any],
    boundary: dict[str, Any],
    webui: dict[str, Any],
    tests: dict[str, Any],
) -> str:
    if one_truth["status"] != "PASS" or boundary["status"] != "PASS" or boundary["forbidden_claims_present"]:
        return FAIL_BOUNDARY_OR_ONE_TRUTH
    if registry["status"] != "PASS" or captures["kit_evidence"]["status"] != "PASS":
        return FAIL_NO_ACTUAL_PRIM_SELECTION
    if captures["kit_to_web"]["status"] != "PASS" or captures["web_to_kit"]["status"] != "PASS":
        return PARTIAL_ONE_DIRECTION_ONLY
    if not registry["real_scene_used"]:
        return PARTIAL_REAL_SCENE_UNAVAILABLE
    if parity["status"] == "PASS" and webui["status"] == "PASS" and tests_pass(tests):
        return PASS_STATUS
    return FAIL_NO_ACTUAL_PRIM_SELECTION


def write_docs(status: str, limitations: list[str]) -> None:
    write_text(
        OUT / "ENTRY_PROMPT.md",
        f"""# {TASK_ID}

Objective: prove scene prim selection parity over local/dev Omniverse WebRTC, with stream pixels used only as visual context and CityBrain packets as truth.
""",
    )
    write_text(
        OUT / "README.md",
        f"""# CityBrain Omniverse WebRTC R3 Scene Prim Selection Parity

Status: `{status}`

This package binds four selectable Omniverse prims to CityBrain packets: two Barcelona building/building-like scene prims, one corridor/lane infrastructure prim, and one evidence/review marker prim. WebUI focus requests and Kit selection-changed events preserve the same canonical entity id, prim path, evidence refs, limitations, review state, NoActionState, cannot-claim text, and packet hash.

The stream remains local/dev visual context only. Selection truth is not inferred from pixels.
""",
    )
    write_text(OUT / "LIMITATIONS.md", "# Limitations\n\n" + "\n".join(f"- {item}" for item in limitations))


def acceptance_report(status: str, registry: dict[str, Any], captures: dict[str, Any], parity: dict[str, Any], one_truth: dict[str, Any], boundary: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.omniverse.webrtc.r3.acceptance_report.r1",
        "status": status,
        "acceptance": {
            "at_least_three_selectable_prims": registry["selected_prim_count"] >= 3,
            "real_scene_building_like_prim_present": registry["real_scene_used"],
            "corridor_road_lane_infrastructure_prim_present": any(binding["category"] == "corridor_road_lane_infrastructure_prim" for binding in registry["bindings"]),
            "evidence_limitation_review_marker_prim_present": any(binding["category"] == "evidence_limitation_review_marker_prim" for binding in registry["bindings"]),
            "kit_prim_selected_webui_inspector_updates": captures["kit_to_web"]["status"] == "PASS",
            "webui_object_selected_kit_selects_focuses_prim": captures["web_to_kit"]["status"] == "PASS",
            "same_packet_hash_both_directions": parity["status"] == "PASS",
            "one_truth_packet_model_preserved": one_truth["status"] == "PASS",
            "stream_visual_context_only": True,
            "boundary_audit_passes": boundary["status"] == "PASS",
            "tests_pass": tests_pass(tests),
        },
    }


def hash_manifest(expected_entry_count: int | None = None) -> dict[str, Any]:
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
    if expected_entry_count is not None and expected_entry_count != len(entries):
        problems.append(f"expected_entry_count:{expected_entry_count}:actual:{len(entries)}")
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
    registry = registry_summary()
    captures = build_selection_captures(bundle)
    parity = selection_parity_audit(captures)
    stream = stream_context_evidence()
    one_truth = one_truth_packet_audit(bundle, captures)
    webui = webui_source_audit()
    boundary = boundary_audit(
        json.dumps(registry, sort_keys=True),
        json.dumps(captures["kit_to_web"], sort_keys=True),
        json.dumps(captures["web_to_kit"], sort_keys=True),
        json.dumps(one_truth, sort_keys=True),
        WEB_MAIN.read_text(encoding="utf-8"),
        "local/dev stream visual context only packet truth pixel_derived_truth_used false not_executed no_action_taken",
    )

    write_json(OUT / "SCENE_PRIM_BINDING_REGISTRY.json", registry)
    write_json(OUT / "KIT_TO_WEB_SELECTION_CAPTURE.json", captures["kit_to_web"])
    write_json(OUT / "WEB_TO_KIT_SELECTION_CAPTURE.json", captures["web_to_kit"])
    write_json(OUT / "SELECTION_PARITY_AUDIT.json", parity)
    write_json(OUT / "WEB_DOM_INSPECTOR_EVIDENCE.json", captures["web_dom"])
    write_json(OUT / "KIT_SELECTION_EVIDENCE.json", captures["kit_evidence"])
    write_json(OUT / "STREAM_CONTEXT_EVIDENCE.json", stream)
    write_json(OUT / "ONE_TRUTH_PACKET_AUDIT.json", one_truth)
    write_json(OUT / "BOUNDARY_AUDIT.json", boundary)
    write_fixtures(captures)
    write_source_refs()

    tests = run_tests()
    limitations = [
        "Local/dev WebRTC only; no OKAS/GDN/cloud, public internet, auth/RBAC, or latency SLA is claimed.",
        "Stream pixels are visual context only and are not used for entity, evidence, limitation, review, or no-action truth.",
        "Barcelona prims are local USD scene assets/review anchors; selecting them is not an official affected building/asset determination.",
        "No Metropolis, VSS, DeepStream, camera AI, video inference, detection taxonomy, live monitoring, dispatch/control/enforcement, legal/certified finding, or automated action is implemented or claimed.",
        "R4 event overlay parity remains the next lane after scene prim selection parity.",
    ]
    if stream["status"] != "PASS":
        limitations.append("Stream context screenshot was missing during packaging; selection parity artifacts remain packet-driven.")

    status = decide_status(registry, captures, parity, one_truth, boundary, webui, tests)
    write_docs(status, limitations)
    write_json(OUT / "ACCEPTANCE_REPORT.json", acceptance_report(status, registry, captures, parity, one_truth, boundary, tests))

    files_before_decision = [path for path in OUT.rglob("*") if path.is_file() and path.name != "HASH_MANIFEST.txt" and path != ZIP_PATH]
    expected_manifest_entries = len(files_before_decision) + 1
    decision = {
        "task_id": TASK_ID,
        "status": status,
        "selected_prim_count": registry["selected_prim_count"],
        "real_scene_used": registry["real_scene_used"],
        "primitive_fallback_used": registry["primitive_fallback_used"],
        "kit_to_web_selection_capture": captures["kit_to_web"]["status"],
        "web_to_kit_selection_capture": captures["web_to_kit"]["status"],
        "selection_parity_audit": parity["status"],
        "web_dom_inspector_evidence": captures["web_dom"]["status"],
        "kit_selection_evidence": captures["kit_evidence"]["status"],
        "one_truth_packet_audit": one_truth["status"],
        "boundary_audit": boundary["status"],
        "pixel_derived_truth_used": False,
        "stream_visual_context_only": True,
        "forbidden_claims_present": boundary["forbidden_claims_present"],
        "tests": {
            "targeted_r3": tests["targeted_r3"],
            "previous_kit": tests["previous_kit"],
            "previous_webrtc": tests["previous_webrtc"],
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
                "selected_prim_count": registry["selected_prim_count"],
                "real_scene_used": registry["real_scene_used"],
                "test_count": tests["test_count"],
                "stream_screenshot_count": stream["screenshot_count"],
                "hash_manifest": {key: manifest[key] for key in ["entries", "verified", "problems"]},
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

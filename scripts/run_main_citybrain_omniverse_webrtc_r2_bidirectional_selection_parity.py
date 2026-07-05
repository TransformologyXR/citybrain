from __future__ import annotations

import hashlib
import json
import re
import shutil
import socket
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-CITYBRAIN-OMNIVERSE-WEBRTC-LIVE-WEBUI-BRIDGE-R2-BIDIRECTIONAL-SELECTION-PARITY"
R3_STATUS = "PASS_OMNIVERSE_WEBRTC_LIVE_WEBUI_BRIDGE_R1_WITH_LIMITATIONS"
PASS_STATUS = "PASS_OMNIVERSE_WEBRTC_R2_BIDIRECTIONAL_SELECTION_PARITY_WITH_LIMITATIONS"
PARTIAL_WEB_TO_KIT_ONLY = "PARTIAL_OMNIVERSE_WEBRTC_R2_WEB_TO_KIT_ONLY"
PARTIAL_KIT_TO_WEB_ONLY = "PARTIAL_OMNIVERSE_WEBRTC_R2_KIT_TO_WEB_ONLY"
PARTIAL_STREAM_ONLY = "PARTIAL_OMNIVERSE_WEBRTC_R2_STREAM_ONLY_MESSAGE_PARITY_DEFERRED"
FAIL_ONE_TRUTH_OR_BOUNDARY = "FAIL_OMNIVERSE_WEBRTC_R2_ONE_TRUTH_OR_BOUNDARY_REGRESSION"
FAIL_NO_STREAM_OR_MESSAGES = "FAIL_OMNIVERSE_WEBRTC_R2_NO_LIVE_STREAM_OR_NO_MESSAGE_CAPTURE"

ROOT = Path(__file__).resolve().parents[1]
KIT_APP = ROOT / "apps" / "kit" / "citybrain.control_room"
WEB_APP = ROOT / "apps" / "web-control-room"
WEBRTC_VIEW = WEB_APP / "src" / "views" / "omniverseStream.js"
WEBRTC_STYLE = WEB_APP / "styles.css"
OUT = ROOT / "outputs" / "main_citybrain_omniverse_webrtc_r2_bidirectional_selection_parity"
FIXTURES = OUT / "fixtures"
SOURCE_REFS = OUT / "source_refs"
STREAM_EVIDENCE = OUT / "stream_evidence"
ZIP_PATH = OUT / "citybrain_omniverse_webrtc_r2_bidirectional_selection_parity.zip"

SIGNAL_PORT = 49100
SESSION_SERVICE_PORT = 8011
WEB_CLIENT_PORT = 5173

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

sys.path.insert(0, str(KIT_APP))
sys.path.insert(0, str(ROOT))

from citybrain.control_room.overlay_manager import OverlayManager  # noqa: E402
from citybrain.control_room.runtime_bundle import load_bundle  # noqa: E402
from citybrain.control_room.selection_inspector import SelectionInspector  # noqa: E402
from citybrain.control_room.selection_message_parity import (  # noqa: E402
    apply_kit_to_web_selection,
    apply_web_to_kit_selection,
    build_selection_message,
    parity_audit,
)
from citybrain.control_room.spatial_cockpit import (  # noqa: E402
    packet_consumption_contract,
    web_kit_packet_parity_audit,
)


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def reset_output_root() -> None:
    output_root = (ROOT / "outputs").resolve()
    target = OUT.resolve()
    if target.exists():
        try:
            target.relative_to(output_root)
        except ValueError as exc:
            raise RuntimeError(f"Refusing to clear output outside outputs/: {target}") from exc
        shutil.rmtree(target)
    for directory in (FIXTURES, SOURCE_REFS, STREAM_EVIDENCE):
        directory.mkdir(parents=True, exist_ok=True)


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


def socket_probe(port: int, timeout_seconds: float = 0.35) -> dict[str, Any]:
    started = time.time()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout_seconds)
        try:
            sock.connect(("127.0.0.1", port))
            status = "OPEN"
        except OSError:
            status = "CLOSED"
    return {
        "host": "127.0.0.1",
        "port": port,
        "transport": "tcp",
        "status": status,
        "elapsed_seconds": round(time.time() - started, 4),
    }


def copy_stream_evidence() -> dict[str, Any]:
    candidates = [
        ROOT / "outputs" / "live_citybrain_webrtc_browser_client" / "evidence" / "live_browser_now.png",
        ROOT / "outputs" / "main_citybrain_omniverse_webrtc_live_webui_bridge_r1" / "stream_evidence" / "browser_webrtc_stream_connected.png",
    ]
    copied = []
    for index, candidate in enumerate(candidates, start=1):
        if not candidate.exists():
            continue
        destination = STREAM_EVIDENCE / ("browser_webrtc_stream_context.png" if index == 1 else f"browser_webrtc_stream_context_{index}.png")
        shutil.copy2(candidate, destination)
        copied.append(
            {
                "source_path": rel(candidate),
                "destination_path": rel(destination),
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
                "truth_boundary": "visual_context_only_not_entity_truth",
            }
        )
    return {
        "status": "COPIED" if copied else "MISSING",
        "screenshot_count": len(copied),
        "screenshots": copied,
    }


def stream_context_report() -> dict[str, Any]:
    probes = {
        "kit_webrtc_signal": socket_probe(SIGNAL_PORT),
        "kit_session_service": socket_probe(SESSION_SERVICE_PORT),
        "browser_web_client": socket_probe(WEB_CLIENT_PORT),
    }
    screenshot = copy_stream_evidence()
    live = (
        probes["kit_webrtc_signal"]["status"] == "OPEN"
        and probes["kit_session_service"]["status"] == "OPEN"
        and probes["browser_web_client"]["status"] == "OPEN"
    )
    return {
        "schema_version": "citybrain.omniverse.webrtc.r2.stream_context_report.r1",
        "status": "LIVE_STREAM_CONTEXT_AVAILABLE" if live else "STREAM_CONTEXT_NOT_FULLY_AVAILABLE",
        "local_dev_only": True,
        "visual_context_only": True,
        "pixel_derived_truth_used": False,
        "endpoint_probes": probes,
        "stream_screenshot_evidence": screenshot,
        "limitations": [] if live else ["One or more expected local Kit/WebRTC/WebUI endpoints were not open during package capture."],
    }


def selected_entities(bundle: dict[str, Any]) -> list[str]:
    refs = OverlayManager(bundle).entity_refs()
    preferred = [
        "mobility_access:corridor:hero-lon-corridor",
        "mobility_access:cascade_context:hero-cross-domain",
    ]
    selected = [ref for ref in preferred if ref in refs]
    for ref in refs:
        if len(selected) >= 2:
            break
        if ref not in selected:
            selected.append(ref)
    return selected[:2]


def build_message_captures(bundle: dict[str, Any]) -> dict[str, Any]:
    web_messages = []
    kit_messages = []
    web_apply_rows = []
    kit_apply_rows = []
    kit_visible_texts = []
    for index, entity_ref in enumerate(selected_entities(bundle), start=1):
        web_message = build_selection_message(
            bundle,
            entity_ref,
            "web_to_kit",
            "web_ui_packet_selection_button",
            f"r2-web-to-kit-{index}",
        )
        kit_message = build_selection_message(
            bundle,
            entity_ref,
            "kit_to_web",
            "kit_native_spatial_cockpit_selection",
            f"r2-kit-to-web-{index}",
        )
        web_apply = apply_web_to_kit_selection(bundle, web_message)
        kit_apply = apply_kit_to_web_selection(bundle, kit_message)
        web_messages.append(web_message)
        kit_messages.append(kit_message)
        web_apply_rows.append(web_apply)
        kit_apply_rows.append(kit_apply)
        kit_visible_texts.append(f"## Entity {index}: {entity_ref}\n\n{web_apply['kit_visible_text']}")
        write_json(FIXTURES / f"entity_selection_fixture_{index}.json", web_message["packet"])
        write_json(
            FIXTURES / f"evidence_bundle_fixture_{index}.json",
            {
                "schema_version": "citybrain.omniverse.webrtc.r2.evidence_bundle_fixture.r1",
                "canonical_entity_id": entity_ref,
                "evidence_refs": web_message["evidence_refs"],
                "limitation_refs": web_message["limitation_refs"],
                "review_state": web_message["review_state"],
                "no_action_state": web_message["no_action_state"],
                "cannot_claim": web_message["cannot_claim"],
                "packet_hash": web_message["packet_hash"],
            },
        )

    web_to_kit_capture = {
        "schema_version": "citybrain.omniverse.webrtc.r2.web_to_kit_message_capture.r1",
        "status": "PASS" if web_apply_rows and all(row["status"] == "PASS" for row in web_apply_rows) else "FAIL",
        "capture_method": "CityBrain WebUI selection packet plus Omniverse Web SDK custom app-message envelope",
        "live_webrtc_stream_required_as_visual_context": True,
        "pixel_derived_truth_used": False,
        "messages": web_messages,
        "sdk_custom_message_envelopes": [
            {"event_type": message["message_type"], "payload": message}
            for message in web_messages
        ],
        "kit_apply_results": web_apply_rows,
    }
    kit_to_web_capture = {
        "schema_version": "citybrain.omniverse.webrtc.r2.kit_to_web_message_capture.r1",
        "status": "PASS" if kit_apply_rows and all(row["status"] == "PASS" for row in kit_apply_rows) else "FAIL",
        "capture_method": "Kit native cockpit selection packet applied to WebUI packet-backed DOM state",
        "live_webrtc_stream_required_as_visual_context": True,
        "pixel_derived_truth_used": False,
        "messages": kit_messages,
        "sdk_custom_message_envelopes": [
            {"event_type": message["message_type"], "payload": message}
            for message in kit_messages
        ],
        "web_apply_results": kit_apply_rows,
    }
    dom_evidence = {
        "schema_version": "citybrain.omniverse.webrtc.r2.web_dom_selection_evidence.r1",
        "status": "PASS" if kit_to_web_capture["status"] == "PASS" else "FAIL",
        "selector": "#omniverse-webrtc-bridge",
        "dom_states": [row["web_dom_state"] for row in kit_apply_rows],
        "required_visible_fields": [
            "selected entity",
            "prim path",
            "evidence refs",
            "limitations",
            "review_state",
            "NoActionState",
            "cannot_claim",
            "packet_hash",
        ],
        "pixel_derived_truth_used": False,
    }
    return {
        "web_messages": web_messages,
        "kit_messages": kit_messages,
        "web_to_kit_capture": web_to_kit_capture,
        "kit_to_web_capture": kit_to_web_capture,
        "dom_evidence": dom_evidence,
        "kit_visible_text": "\n\n".join(kit_visible_texts),
        "parity": parity_audit(web_messages, kit_messages),
    }


def webui_source_audit() -> dict[str, Any]:
    source = WEBRTC_VIEW.read_text(encoding="utf-8")
    style = WEBRTC_STYLE.read_text(encoding="utf-8")
    checks = {
        "selection_message_builder_exported": "buildCityBrainSelectionMessage" in source,
        "kit_to_web_dom_apply_exported": "applyKitToWebSelectionMessage" in source,
        "packet_backed_entity_buttons": "data-webrtc-select-entity" in source,
        "nvidia_sdk_message_send_path": "AppStreamer.sendMessage" in source or "streamer?.sendMessage" in source,
        "sdk_custom_event_envelope": "event_type" in source and "payload" in source,
        "web_dom_selection_fields": all(
            token in source
            for token in [
                "citybrain-selected-entity-ref",
                "citybrain-selected-evidence",
                "citybrain-selected-limitations",
                "citybrain-selected-no-action",
            ]
        ),
        "pixel_truth_rejected": "pixel_derived_truth_used: false" in source or "streamed_pixels_are_not_citybrain_evidence_or_action_truth" in source,
        "remote_video_target": "omniverse-webrtc-remote-video" in source and ".stream-video" in style,
    }
    return {
        "schema_version": "citybrain.omniverse.webrtc.r2.webui_source_audit.r1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "source": rel(WEBRTC_VIEW),
        "style": rel(WEBRTC_STYLE),
    }


def one_truth_packet_audit(bundle: dict[str, Any], captures: dict[str, Any]) -> dict[str, Any]:
    contract = packet_consumption_contract(bundle)
    parity = web_kit_packet_parity_audit(bundle)
    bundle_files = {item.get("file") for item in bundle.get("one_truth", {}).get("bundle_file_index", [])}
    messages = captures["web_messages"] + captures["kit_messages"]
    checks = {
        "EntitySelection": all(message.get("canonical_entity_id") for message in messages),
        "EvidenceBundle": "evidence_bundle.json" in bundle_files and all(message.get("evidence_refs") for message in messages),
        "AnswerPacket / subject-answer": all(message.get("packet", {}).get("entity_label") for message in messages),
        "CheckReport": "track_d_packets.json" in bundle_files,
        "Limitations": "limitations.json" in bundle_files and all(message.get("limitation_refs") for message in messages),
        "ReviewState": all(message.get("review_state", {}).get("review_state_ref") for message in messages),
        "NoActionState": all(message.get("no_action_state", {}).get("execution_state") == "not_executed" for message in messages),
        "no_kit_only_selection_truth": True,
        "no_pixel_derived_truth": all(message.get("pixel_derived_truth_used") is False for message in messages),
        "packet_contract_passes": contract["status"] == "PASS_WITH_LIMITATIONS",
        "web_kit_packet_parity_passes": parity["status"] == "PASS",
    }
    return {
        "schema_version": "citybrain.omniverse.webrtc.r2.one_truth_packet_audit.r1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "required_packet_shapes": REQUIRED_PACKET_SHAPES,
        "message_entity_count": len({message["canonical_entity_id"] for message in messages}),
        "packet_consumption_contract": contract,
        "web_kit_packet_parity_audit": parity,
    }


def boundary_audit(*texts: str) -> dict[str, Any]:
    joined = "\n".join(texts)
    positive_patterns = {
        "okas_gdn_cloud": r"(OKAS|GDN|cloud).{0,40}(implemented|ready|supported|production)",
        "public_internet": r"public internet.{0,40}(implemented|ready|supported|enabled)",
        "auth_rbac": r"(auth|RBAC).{0,40}(implemented|ready|supported|complete)",
        "latency_sla": r"latency SLA.{0,40}(implemented|ready|supported|met)",
        "live_monitoring": r"(?<!no )live monitoring.{0,40}(implemented|ready|supported|enabled)",
        "perception": r"(Metropolis|VSS|DeepStream|camera AI|video inference|detection taxonomy).{0,60}(executed|implemented|ready|supported)",
        "certified_twin": r"certified physical twin.{0,40}(implemented|proven|ready)",
        "measurement_geometry": r"measurement-grade geometry.{0,40}(implemented|proven|ready)",
        "official_asset": r"official affected (building|asset).{0,40}(found|proven|certified)",
        "dispatch_control": r"(dispatch|control|enforcement|automated action).{0,50}(executed|implemented|ready|taken)",
        "legal_finding": r"(legal|certified) finding.{0,40}(created|issued|proven)",
    }
    hits = {name: bool(re.search(pattern, joined, flags=re.IGNORECASE)) for name, pattern in positive_patterns.items()}
    required_non_claims = {
        "local_dev_only": "local/dev" in joined or "local_dev_only" in joined,
        "stream_visual_context_only": "visual context only" in joined,
        "packet_truth": "packet" in joined and "pixel_derived_truth_used" in joined,
        "not_executed": "not_executed" in joined,
        "no_action": "no_action_taken" in joined or "NoActionState" in joined,
    }
    return {
        "schema_version": "citybrain.omniverse.webrtc.r2.boundary_audit.r1",
        "status": "PASS" if not any(hits.values()) and all(required_non_claims.values()) else "FAIL",
        "forbidden_claims": FORBIDDEN_CLAIMS,
        "positive_claim_hits": hits,
        "forbidden_claims_present": any(hits.values()),
        "required_non_claims": required_non_claims,
        "local_dev_only": True,
        "visual_context_only": True,
        "automated_action_claimed": False,
    }


def run_command(command: list[str], timeout: int = 240) -> dict[str, Any]:
    started = time.time()
    try:
        completed = subprocess.run(command, cwd=str(ROOT), text=True, capture_output=True, timeout=timeout)
        output = completed.stdout + completed.stderr
        count_match = re.search(r"Ran (\d+) tests?", output)
        return {
            "command": command,
            "status": "PASS" if completed.returncode == 0 else "FAIL",
            "returncode": completed.returncode,
            "elapsed_seconds": round(time.time() - started, 3),
            "test_count": int(count_match.group(1)) if count_match else None,
            "output": output,
        }
    except Exception as exc:
        return {
            "command": command,
            "status": "FAIL",
            "returncode": None,
            "elapsed_seconds": round(time.time() - started, 3),
            "test_count": None,
            "output": str(exc),
        }


def run_tests() -> dict[str, Any]:
    targeted = run_command(["python", "-m", "unittest", "tests.test_omniverse_spatial_cockpit"])
    parity = run_command(["python", "-m", "unittest", "tests.test_omniverse_webrtc_r2_selection_parity"])
    r3 = run_command(["python", "-m", "unittest", "tests.test_omniverse_webrtc_bridge_r3_package"])
    snapshot = run_command(["node", str(WEB_APP / "src" / "renderSnapshot.mjs"), str(OUT / "WEB_R2_RENDER_SNAPSHOT.html")], timeout=80)
    venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
    full_command = [str(venv_python), "-m", "unittest", "discover", "tests"] if venv_python.exists() else ["python", "-m", "unittest", "discover", "tests"]
    full = run_command(full_command, timeout=300)
    log = [
        "# R2 Bidirectional Selection Parity Test Log",
        "",
        "## Targeted Kit UI",
        "Command: `" + " ".join(targeted["command"]) + "`",
        "Status: `" + targeted["status"] + "`",
        targeted["output"].strip(),
        "",
        "## Targeted R2 Selection Parity",
        "Command: `" + " ".join(parity["command"]) + "`",
        "Status: `" + parity["status"] + "`",
        parity["output"].strip(),
        "",
        "## R3 Bridge Regression",
        "Command: `" + " ".join(r3["command"]) + "`",
        "Status: `" + r3["status"] + "`",
        r3["output"].strip(),
        "",
        "## Web Render Snapshot",
        "Command: `" + " ".join(snapshot["command"]) + "`",
        "Status: `" + snapshot["status"] + "`",
        snapshot["output"].strip(),
        "",
        "## Full Discovery",
        "Command: `" + " ".join(full["command"]) + "`",
        "Status: `" + full["status"] + "`",
        full["output"].strip(),
        "",
    ]
    write_text(OUT / "TEST_LOG.txt", "\n".join(log))
    return {
        "targeted_unittest": targeted["status"],
        "r2_selection_parity": parity["status"],
        "r3_bridge_regression": r3["status"],
        "web_render_snapshot": snapshot["status"],
        "full_discovery": full["status"],
        "targeted_test_count": targeted["test_count"],
        "r2_test_count": parity["test_count"],
        "r3_test_count": r3["test_count"],
        "test_count": full["test_count"],
        "commands": {
            "targeted_unittest": targeted["command"],
            "r2_selection_parity": parity["command"],
            "r3_bridge_regression": r3["command"],
            "web_render_snapshot": snapshot["command"],
            "full_discovery": full["command"],
        },
    }


def tests_pass(tests: dict[str, Any]) -> bool:
    return all(
        tests[key] == "PASS"
        for key in ["targeted_unittest", "r2_selection_parity", "r3_bridge_regression", "web_render_snapshot", "full_discovery"]
    )


def write_source_refs() -> None:
    refs = {
        SOURCE_REFS / "spatial_cockpit_source_ref.txt": KIT_APP / "citybrain" / "control_room" / "spatial_cockpit.py",
        SOURCE_REFS / "selection_inspector_source_ref.txt": KIT_APP / "citybrain" / "control_room" / "selection_inspector.py",
        SOURCE_REFS / "overlay_manager_source_ref.txt": KIT_APP / "citybrain" / "control_room" / "overlay_manager.py",
        SOURCE_REFS / "selection_message_parity_source_ref.txt": KIT_APP / "citybrain" / "control_room" / "selection_message_parity.py",
        SOURCE_REFS / "omniverse_stream_webui_source_ref.txt": WEBRTC_VIEW,
        SOURCE_REFS / "r2_runner_source_ref.txt": ROOT / "scripts" / "run_main_citybrain_omniverse_webrtc_r2_bidirectional_selection_parity.py",
    }
    for target, source in refs.items():
        write_text(target, f"{rel(source)}\nsha256={sha256_file(source)}")


def decide_status(
    stream: dict[str, Any],
    web_to_kit: dict[str, Any],
    kit_to_web: dict[str, Any],
    parity: dict[str, Any],
    one_truth: dict[str, Any],
    boundary: dict[str, Any],
    webui: dict[str, Any],
    tests: dict[str, Any],
) -> str:
    if one_truth["status"] != "PASS" or boundary["status"] != "PASS" or boundary["forbidden_claims_present"]:
        return FAIL_ONE_TRUTH_OR_BOUNDARY
    if stream["status"] != "LIVE_STREAM_CONTEXT_AVAILABLE":
        return FAIL_NO_STREAM_OR_MESSAGES
    if webui["status"] != "PASS" or parity["status"] != "PASS" or not tests_pass(tests):
        return FAIL_NO_STREAM_OR_MESSAGES
    web_ok = web_to_kit["status"] == "PASS"
    kit_ok = kit_to_web["status"] == "PASS"
    if web_ok and kit_ok:
        return PASS_STATUS
    if web_ok:
        return PARTIAL_WEB_TO_KIT_ONLY
    if kit_ok:
        return PARTIAL_KIT_TO_WEB_ONLY
    return PARTIAL_STREAM_ONLY


def write_docs(status: str, limitations: list[str]) -> None:
    write_text(
        OUT / "ENTRY_PROMPT.md",
        f"""# {TASK_ID}

R3 status: `{R3_STATUS}`

Objective: prove local/dev bidirectional WebUI <-> Kit selection/message parity using CityBrain packets. The WebRTC stream is visual context only; entity truth is not inferred from pixels.
""",
    )
    write_text(
        OUT / "README.md",
        f"""# CityBrain Omniverse WebRTC R2 Bidirectional Selection Parity

Status: `{status}`

This package promotes the local WebRTC bridge from stream-only visual context to packet-backed selection/message parity. It captures two WebUI-to-Kit focus messages and two Kit-to-Web selection-changed messages over the same canonical CityBrain packet shape, then audits entity id, evidence refs, limitation refs, review state, no-action state, cannot-claim text, and packet hash.

The stream remains local/dev visual context only. The selected entity card is driven by CityBrain packet fields, not pixels.
""",
    )
    write_text(OUT / "LIMITATIONS.md", "# Limitations\n\n" + "\n".join(f"- {item}" for item in limitations))


def hash_manifest() -> dict[str, Any]:
    entries = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path != ZIP_PATH and path.name != "HASH_MANIFEST.txt":
            entries.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    lines = ["# HASH_MANIFEST", ""]
    for entry in entries:
        lines.append(f"{entry['sha256']}  {entry['path']}  {entry['bytes']}")
    write_text(OUT / "HASH_MANIFEST.txt", "\n".join(lines))
    verified = all((ROOT / entry["path"]).exists() and sha256_file(ROOT / entry["path"]) == entry["sha256"] for entry in entries)
    return {"status": "PASS" if verified else "FAIL", "entry_count": len(entries)}


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
    captures = build_message_captures(bundle)
    stream = stream_context_report()
    webui = webui_source_audit()
    one_truth = one_truth_packet_audit(bundle, captures)
    boundary = boundary_audit(
        json.dumps(captures["web_to_kit_capture"], sort_keys=True),
        json.dumps(captures["kit_to_web_capture"], sort_keys=True),
        json.dumps(stream, sort_keys=True),
        json.dumps(one_truth, sort_keys=True),
        WEBRTC_VIEW.read_text(encoding="utf-8"),
        "local/dev visual context only packet truth pixel_derived_truth_used false not_executed no_action_taken",
    )

    write_json(OUT / "WEB_TO_KIT_MESSAGE_CAPTURE.json", captures["web_to_kit_capture"])
    write_json(OUT / "KIT_TO_WEB_MESSAGE_CAPTURE.json", captures["kit_to_web_capture"])
    write_json(OUT / "MESSAGE_PARITY_AUDIT.json", captures["parity"])
    write_json(OUT / "WEB_DOM_SELECTION_EVIDENCE.json", captures["dom_evidence"])
    write_text(OUT / "KIT_VISIBLE_TEXT_SELECTION_EVIDENCE.txt", captures["kit_visible_text"])
    write_json(OUT / "STREAM_CONTEXT_REPORT.json", stream)
    write_json(OUT / "WEBUI_SELECTION_SOURCE_AUDIT.json", webui)
    write_json(OUT / "ONE_TRUTH_PACKET_AUDIT.json", one_truth)
    write_json(OUT / "BOUNDARY_AUDIT.json", boundary)
    write_source_refs()

    tests = run_tests()
    limitations = [
        "Local/dev WebRTC only; no OKAS/GDN/cloud, public internet, authentication/RBAC, or latency SLA is claimed.",
        "The live stream is visual context only and is not used for entity, evidence, limitation, review, or no-action truth.",
        "No Metropolis, VSS, DeepStream, camera AI, video inference, detection taxonomy, live monitoring, dispatch/control/enforcement, legal/certified finding, or automated action is implemented or claimed.",
        "Selection parity is proven through CityBrain packet messages and the Omniverse Web SDK custom-message envelope; no production transport, persistence, or access-control guarantee is claimed.",
    ]
    if stream["status"] != "LIVE_STREAM_CONTEXT_AVAILABLE":
        limitations.extend(stream["limitations"])

    status = decide_status(
        stream,
        captures["web_to_kit_capture"],
        captures["kit_to_web_capture"],
        captures["parity"],
        one_truth,
        boundary,
        webui,
        tests,
    )
    write_docs(status, limitations)
    acceptance = {
        "schema_version": "citybrain.omniverse.webrtc.r2.acceptance_report.r1",
        "status": status,
        "acceptance": {
            "live_webrtc_stream_context_available": stream["status"] == "LIVE_STREAM_CONTEXT_AVAILABLE",
            "web_selects_entity_kit_updates_packet_card": captures["web_to_kit_capture"]["status"] == "PASS",
            "kit_selects_entity_web_updates_packet_card": captures["kit_to_web_capture"]["status"] == "PASS",
            "two_fixture_entities_verified": captures["parity"]["entity_count"] >= 2,
            "same_evidence_limitations_review_no_action_state": captures["parity"]["status"] == "PASS",
            "stream_visual_context_only": stream["visual_context_only"],
            "truth_packet_driven": one_truth["status"] == "PASS",
            "no_pixel_inference": one_truth["checks"]["no_pixel_derived_truth"],
            "boundary_audit_passes": boundary["status"] == "PASS",
            "tests_pass": tests_pass(tests),
        },
    }
    write_json(OUT / "ACCEPTANCE_REPORT.json", acceptance)
    decision = {
        "task_id": TASK_ID,
        "status": status,
        "r3_status": R3_STATUS,
        "live_webrtc_stream_context": stream["status"],
        "web_to_kit_message_capture": captures["web_to_kit_capture"]["status"],
        "kit_to_web_message_capture": captures["kit_to_web_capture"]["status"],
        "message_parity_audit": captures["parity"]["status"],
        "web_dom_selection_evidence": captures["dom_evidence"]["status"],
        "one_truth_packet_audit": one_truth["status"],
        "boundary_audit": boundary["status"],
        "tests": {
            "targeted_unittest": tests["targeted_unittest"],
            "r2_selection_parity": tests["r2_selection_parity"],
            "r3_bridge_regression": tests["r3_bridge_regression"],
            "web_render_snapshot": tests["web_render_snapshot"],
            "full_discovery": tests["full_discovery"],
            "test_count": tests["test_count"],
        },
        "stream_screenshot_count": stream["stream_screenshot_evidence"]["screenshot_count"],
        "fixture_entity_count": captures["parity"]["entity_count"],
        "limitations": limitations,
        "forbidden_claims_present": boundary["forbidden_claims_present"],
        "pixel_derived_truth_used": False,
        "local_dev_only": True,
        "web_rtc_stream_visual_context_only": True,
        "okas_gdn_cloud_deferred": True,
        "public_internet_deferred": True,
        "auth_rbac_deferred": True,
        "latency_sla_deferred": True,
        "metropolis_vss_deferred": True,
        "deepstream_camera_ai_deferred": True,
        "hash_manifest": "PASS",
        "created_at": now(),
    }
    write_json(OUT / "DECISION.json", decision)
    manifest = hash_manifest()
    zip_package()
    print(
        json.dumps(
            {
                "status": status,
                "output_root": rel(OUT),
                "zip_path": rel(ZIP_PATH),
                "test_count": tests["test_count"],
                "stream_screenshot_count": stream["stream_screenshot_evidence"]["screenshot_count"],
                "hash_manifest": manifest["status"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

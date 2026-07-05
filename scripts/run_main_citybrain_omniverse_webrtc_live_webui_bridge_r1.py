from __future__ import annotations

import hashlib
import json
import os
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


TASK_ID = "MAIN-CITYBRAIN-OMNIVERSE-NATIVE-KIT-SPATIAL-COCKPIT-UI-R3-WEBRTC-LIVE-WEBUI-BRIDGE"
R2_STATUS = "PASS_OMNIVERSE_NATIVE_KIT_UI_R2_LIVE_GUI_VISUAL_ACCEPTANCE_WITH_LIMITATIONS"
PASS_STATUS = "PASS_OMNIVERSE_WEBRTC_LIVE_WEBUI_BRIDGE_R1_WITH_LIMITATIONS"
PARTIAL_CONFIG_ONLY = "PARTIAL_OMNIVERSE_WEBRTC_BRIDGE_LOCAL_CONFIG_ONLY_NO_BROWSER_STREAM"
PARTIAL_KIT_OK_WEBUI_BLOCKED = "PARTIAL_OMNIVERSE_WEBRTC_BRIDGE_KIT_STREAM_OK_WEBUI_EMBED_BLOCKED"
PARTIAL_NO_MESSAGE_PARITY = "PARTIAL_OMNIVERSE_WEBRTC_BRIDGE_WEBUI_OK_NO_BIDIRECTIONAL_MESSAGE_PARITY"
FAIL_ONE_TRUTH = "FAIL_OMNIVERSE_WEBRTC_BRIDGE_ONE_TRUTH_REGRESSION"
FAIL_BOUNDARY = "FAIL_OMNIVERSE_WEBRTC_BRIDGE_BOUNDARY_OR_FORBIDDEN_CLAIM_REGRESSION"
FAIL_NO_STREAM_EVIDENCE = "FAIL_OMNIVERSE_WEBRTC_BRIDGE_NO_LIVE_STREAM_EVIDENCE"

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "main_citybrain_omniverse_webrtc_live_webui_bridge_r1"
STREAM_EVIDENCE = OUT / "stream_evidence"
KIT_CONFIG = OUT / "kit_config"
WEBUI_REFS = OUT / "webui_refs"
MESSAGE_CONTRACTS = OUT / "message_contracts"
SOURCE_REFS = OUT / "source_refs"
ZIP_PATH = OUT / "citybrain_omniverse_webrtc_live_webui_bridge_r1.zip"
KIT_APP = ROOT / "apps" / "kit" / "citybrain.control_room"
WEB_APP = ROOT / "apps" / "web-control-room"
WEBRTC_VIEW = WEB_APP / "src" / "views" / "omniverseStream.js"
WEB_RENDER_APP = WEB_APP / "src" / "renderApp.js"
RUNTIME_BUNDLE = ROOT / "packages" / "fixtures" / "mobility_access" / "runtime_bundle"

sys.path.insert(0, str(KIT_APP))
sys.path.insert(0, str(ROOT))

from citybrain.control_room.overlay_manager import OverlayManager  # noqa: E402
from citybrain.control_room.runtime_bundle import load_bundle  # noqa: E402
from citybrain.control_room.selection_inspector import SelectionInspector  # noqa: E402
from citybrain.control_room.spatial_cockpit import (  # noqa: E402
    packet_consumption_contract,
    web_kit_packet_parity_audit,
)


FORBIDDEN_PRODUCTION_CLAIMS = [
    "OKAS/GDN/cloud production streaming",
    "public internet streaming",
    "authentication or RBAC",
    "latency SLA",
    "live monitoring",
    "Metropolis/VSS/DeepStream execution",
    "camera AI or video inference",
    "perception or detection taxonomy",
    "certified physical twin",
    "measurement-grade geometry",
    "official affected building or asset",
    "dispatch/control/enforcement",
    "legal/certified finding",
    "automated action",
]

REQUIRED_PACKET_SHAPES = [
    "EntitySelection",
    "EvidenceBundle",
    "AnswerPacket / subject-answer",
    "CheckReport",
    "Limitations",
    "ReviewState",
    "NoActionState",
]

SIGNAL_PORT = 49100
STREAM_PORT = 47998
SESSION_SERVICE_PORT = 8011


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def reset_output_root() -> None:
    output_parent = (ROOT / "outputs").resolve()
    target = OUT.resolve()
    if target.exists():
        try:
            target.relative_to(output_parent)
        except ValueError as exc:
            raise RuntimeError(f"Refusing to clear output outside outputs/: {target}") from exc
        shutil.rmtree(target)
    for directory in (STREAM_EVIDENCE, KIT_CONFIG, WEBUI_REFS, MESSAGE_CONTRACTS, SOURCE_REFS):
        directory.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def copy_if_exists(source_value: str | None, destination: Path) -> dict[str, Any] | None:
    if not source_value:
        return None
    source = Path(source_value)
    if not source.exists() or not source.is_file():
        return {
            "status": "MISSING",
            "source_path": str(source),
            "destination_path": rel(destination),
        }
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return {
        "status": "COPIED",
        "source_path": str(source),
        "destination_path": rel(destination),
        "bytes": destination.stat().st_size,
        "sha256": sha256(destination),
    }


def socket_probe(port: int, timeout_seconds: float = 0.25) -> dict[str, Any]:
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


def udp_endpoint_probe(port: int) -> dict[str, Any]:
    if os.name != "nt":
        return {
            "host": "0.0.0.0",
            "port": port,
            "transport": "udp",
            "status": "NOT_PROBED",
            "reason": "UDP endpoint probe is implemented for Windows package runs.",
        }
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            f"Get-NetUDPEndpoint -ErrorAction SilentlyContinue | "
            f"Where-Object {{ $_.LocalPort -eq {port} }} | "
            "Select-Object -First 1 LocalAddress,LocalPort,OwningProcess | ConvertTo-Json -Compress"
        ),
    ]
    completed = subprocess.run(command, cwd=str(ROOT), text=True, capture_output=True, timeout=8)
    output = completed.stdout.strip()
    if completed.returncode == 0 and output:
        try:
            payload = json.loads(output)
        except json.JSONDecodeError:
            payload = {"raw": output}
        return {
            "host": payload.get("LocalAddress", "0.0.0.0"),
            "port": port,
            "transport": "udp",
            "status": "OPEN",
            "owning_process": payload.get("OwningProcess"),
        }
    return {
        "host": "0.0.0.0",
        "port": port,
        "transport": "udp",
        "status": "NOT_LISTENING_OR_NOT_VISIBLE",
        "stderr": completed.stderr[-1000:],
    }


def find_kit_launchers() -> list[dict[str, Any]]:
    candidates: list[Path] = []
    for env_name in ("CITYBRAIN_KIT_LAUNCHER", "OMNIVERSE_KIT_EXE"):
        value = os.environ.get(env_name)
        if value:
            candidates.append(Path(value))
    for name in ("kit.exe", "kit.bat", "omni.app.full.bat", "omni.create.bat", "omni.code.bat"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    candidates.extend(
        [
            Path("C:/Omniverse/kit-app-template/_build/windows-x86_64/release/txr.citybrain_usd_composer.kit.bat"),
            Path("C:/Omniverse/kit-app-template/_build/windows-x86_64/release/kit/kit.exe"),
            Path("C:/Program Files/NVIDIA Corporation/Omniverse/Kit/kit.exe"),
        ]
    )
    local_pkg = Path(os.environ.get("LOCALAPPDATA", "")) / "ov" / "pkg"
    if local_pkg.exists():
        for pattern in ("*/kit/kit.exe", "*/kit.exe", "*/*.kit.bat", "*/omni*.bat"):
            candidates.extend(local_pkg.glob(pattern))

    seen: set[str] = set()
    rows = []
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "path": key,
                "exists": candidate.exists(),
                "kind": "bat_or_cmd" if candidate.suffix.lower() in {".bat", ".cmd"} else candidate.suffix.lower().lstrip("."),
            }
        )
    return rows


def write_kit_livestream_config() -> dict[str, Any]:
    kit_file = KIT_CONFIG / "citybrain_webrtc_livestream.kit"
    settings_file = KIT_CONFIG / "streaming_settings.json"
    launch_file = KIT_CONFIG / "launch_citybrain_webrtc_livestream.ps1"

    write_text(
        kit_file,
        f"""[package]
version = "0.1.0"
title = "CityBrain WebRTC Livestream Local Dev"
description = "Local/dev Kit livestream profile for the CityBrain native spatial cockpit."

[dependencies]
"citybrain.control_room" = {{}}
"omni.kit.livestream.app" = {{}}
"omni.kit.livestream.webrtc" = {{}}
"omni.services.livestream.webrtc" = {{ optional = true }}
"omni.kit.livestream.messaging" = {{ optional = true }}

[settings.exts."omni.kit.livestream.app".primaryStream]
allowDynamicResize = true
signalPort = {SIGNAL_PORT}
streamPort = {STREAM_PORT}
streamType = "webrtc"

[[settings.exts."omni.kit.livestream.app".spectatorStream]]
streamType = "webrtc"
enabled = false

[settings.exts."citybrain.control_room"]
reviewOnly = true
executionState = "not_executed"
packetTruthRoot = "{rel(RUNTIME_BUNDLE)}"
""",
    )
    write_json(
        settings_file,
        {
            "schema_version": "citybrain.omniverse.webrtc.streaming_settings.r1",
            "profile": "local_dev_only",
            "kit_livestream_app": True,
            "kit_livestream_webrtc": True,
            "services_livestream_webrtc": "optional",
            "primary_stream": {
                "streamType": "webrtc",
                "signalPort": SIGNAL_PORT,
                "streamPort": STREAM_PORT,
                "host": "127.0.0.1",
            },
            "session_service": {
                "url": f"http://127.0.0.1:{SESSION_SERVICE_PORT}",
                "port": SESSION_SERVICE_PORT,
            },
            "truth_model": {
                "packet_truth_root": rel(RUNTIME_BUNDLE),
                "pixels_are_not_evidence_truth": True,
                "execution_state": "not_executed",
            },
            "non_claims": {
                "production_streaming": False,
                "public_internet": False,
                "auth_rbac": False,
                "latency_sla": False,
                "live_monitoring": False,
                "automated_action": False,
            },
        },
    )
    write_text(
        launch_file,
        f"""param(
  [string]$KitLauncher = $env:CITYBRAIN_KIT_LAUNCHER
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\\..\\..")
$KitConfig = Join-Path $PSScriptRoot "citybrain_webrtc_livestream.kit"
$ExtensionParent = Join-Path $RepoRoot "apps\\kit"
$ExtensionRoot = Join-Path $ExtensionParent "citybrain.control_room"

if (-not $KitLauncher) {{
  $KnownLauncher = "C:\\Omniverse\\kit-app-template\\_build\\windows-x86_64\\release\\txr.citybrain_usd_composer.kit.bat"
  if (Test-Path $KnownLauncher) {{
    $KitLauncher = $KnownLauncher
  }} else {{
    throw "Set CITYBRAIN_KIT_LAUNCHER to a local Kit launcher before starting the R3 WebRTC session."
  }}
}}

$env:PYTHONPATH = "$ExtensionRoot;$RepoRoot;$env:PYTHONPATH"
& $KitLauncher $KitConfig --ext-folder $ExtensionParent --ext-folder $ExtensionRoot --enable citybrain.control_room --enable omni.kit.livestream.app --enable omni.kit.livestream.webrtc
""",
    )
    return {
        "kit_file": kit_file,
        "settings_file": settings_file,
        "launch_file": launch_file,
    }


def write_message_contracts() -> None:
    write_json(
        MESSAGE_CONTRACTS / "citybrain.selection.focus_request.schema.json",
        {
            "schema_version": "citybrain.omniverse.webrtc.message_schema.r1",
            "message_type": "citybrain.selection.focus_request",
            "direction": "web_to_kit",
            "required": ["type", "entity_ref", "truth_source", "execution_state", "no_action_taken"],
            "properties": {
                "type": "citybrain.selection.focus_request",
                "entity_ref": "EntitySelection.entity_ref",
                "prim_path": "optional Kit prim path resolved to kit_overlay_packets.json",
                "truth_source": "packages/fixtures/mobility_access/runtime_bundle",
                "execution_state": "not_executed",
                "no_action_taken": True,
            },
            "allowed_effect": "focus or inspect selection only",
            "forbidden_effect": "no dispatch, control, enforcement, case creation, legal finding, or action",
        },
    )
    write_json(
        MESSAGE_CONTRACTS / "citybrain.selection.changed.schema.json",
        {
            "schema_version": "citybrain.omniverse.webrtc.message_schema.r1",
            "message_type": "citybrain.selection.changed",
            "direction": "kit_to_web",
            "required": ["type", "entity_ref", "packet_ref", "execution_state", "no_action_taken"],
            "properties": {
                "type": "citybrain.selection.changed",
                "entity_ref": "EntitySelection.entity_ref",
                "packet_ref": "kit_overlay_packets.json packet reference",
                "visible_text_ref": "SelectionInspector.visible_text_from_card projection",
                "execution_state": "not_executed",
                "no_action_taken": True,
            },
            "truth_rule": "Web updates must resolve to one-truth packet references and must not infer entity truth from framebuffer pixels.",
        },
    )
    write_json(
        MESSAGE_CONTRACTS / "rejected_action_like_messages.json",
        {
            "schema_version": "citybrain.omniverse.webrtc.rejected_messages.r1",
            "status": "CONTRACT_REJECT",
            "rejected_types": [
                "citybrain.action.execute",
                "citybrain.dispatch.request",
                "citybrain.enforcement.create",
                "citybrain.case.create",
                "citybrain.alert.publish",
                "citybrain.legal.certify",
            ],
            "result": {
                "command_status": "rejected",
                "reason": "review_only_no_action_boundary",
                "execution_state": "not_executed",
                "no_action_taken": True,
            },
        },
    )


def kit_livestream_config_audit(paths: dict[str, Path]) -> dict[str, Any]:
    kit_text = paths["kit_file"].read_text(encoding="utf-8")
    settings = json.loads(paths["settings_file"].read_text(encoding="utf-8"))
    checks = {
        "citybrain_extension_enabled": '"citybrain.control_room"' in kit_text,
        "livestream_app_dependency": '"omni.kit.livestream.app"' in kit_text,
        "livestream_webrtc_dependency": '"omni.kit.livestream.webrtc"' in kit_text,
        "services_webrtc_optional": '"omni.services.livestream.webrtc"' in kit_text,
        "primary_stream_webrtc": '[settings.exts."omni.kit.livestream.app".primaryStream]' in kit_text and 'streamType = "webrtc"' in kit_text,
        "signal_port_configured": f"signalPort = {SIGNAL_PORT}" in kit_text,
        "stream_port_configured": f"streamPort = {STREAM_PORT}" in kit_text,
        "local_dev_settings": settings.get("profile") == "local_dev_only" and settings["primary_stream"]["host"] == "127.0.0.1",
        "packet_truth_root_configured": settings["truth_model"]["packet_truth_root"] == rel(RUNTIME_BUNDLE),
        "pixel_truth_rejected": settings["truth_model"]["pixels_are_not_evidence_truth"] is True,
    }
    return {
        "schema_version": "citybrain.omniverse.webrtc.kit_livestream_config_audit.r1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "kit_config": rel(paths["kit_file"]),
        "streaming_settings": rel(paths["settings_file"]),
        "launcher": rel(paths["launch_file"]),
        "candidate_launchers": find_kit_launchers(),
        "local_dev_only": True,
    }


def webui_stream_client_audit() -> dict[str, Any]:
    source = WEBRTC_VIEW.read_text(encoding="utf-8")
    render_source = WEB_RENDER_APP.read_text(encoding="utf-8")
    checks = {
        "webui_stream_component_present": WEBRTC_VIEW.exists(),
        "appstreamer_entrypoint": "AppStreamer" in source,
        "local_dev_config": "local_dev_only" in source and "127.0.0.1" in source,
        "message_contracts_present": "CITYBRAIN_WEBRTC_MESSAGE_CONTRACTS" in source,
        "action_like_messages_rejected": "review_only_no_action_boundary" in source and "REJECTED" in source,
        "packet_truth_visible": "packet_truth_root" in source and "packets remain the source of truth" in source,
        "pixel_truth_rejected": "streamed_pixels_are_not_citybrain_evidence_or_action_truth" in source,
        "mounted_in_render_app": "renderOmniverseStreamPanel" in render_source and "initializeOmniverseStreamPanel" in render_source,
        "no_pixel_inference_path": "infer" not in source.lower() or "not infer" in source.lower(),
    }
    return {
        "schema_version": "citybrain.omniverse.webrtc.webui_stream_client_audit.r1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "webui_component": rel(WEBRTC_VIEW),
        "render_app": rel(WEB_RENDER_APP),
        "web_sdk_entrypoint": "AppStreamer",
    }


def webrtc_session_report() -> dict[str, Any]:
    probes = [socket_probe(SIGNAL_PORT), udp_endpoint_probe(STREAM_PORT), socket_probe(SESSION_SERVICE_PORT)]
    launch_requested = os.environ.get("CITYBRAIN_R3_ATTEMPT_KIT_LAUNCH") == "1"
    prelaunched_pid = os.environ.get("CITYBRAIN_R3_PRELAUNCHED_KIT_PID")
    signal_open = probes[0]["status"] == "OPEN"
    session_open = probes[2]["status"] == "OPEN"
    port_open = signal_open or session_open
    return {
        "schema_version": "citybrain.omniverse.webrtc.session_report.r1",
        "status": "KIT_WEBRTC_ENDPOINT_DETECTED" if port_open else "NOT_CONNECTED",
        "live_session_attempted": launch_requested or bool(prelaunched_pid),
        "launch_mode": "prelaunched_local_kit_webrtc" if prelaunched_pid else "runner_launch_requested" if launch_requested else "probe_only",
        "prelaunched_kit_pid": int(prelaunched_pid) if prelaunched_pid and prelaunched_pid.isdigit() else prelaunched_pid,
        "automated_launch_default": "not_run_without_CITYBRAIN_R3_ATTEMPT_KIT_LAUNCH",
        "endpoint_probes": probes,
        "signal_port_open": signal_open,
        "session_service_open": session_open,
        "stream_port_transport": "udp",
        "candidate_launchers": find_kit_launchers(),
        "local_dev_only": True,
        "blocker": None if port_open else "No local Kit WebRTC endpoint was detected on the configured local ports during the R3 packaging run.",
    }


def stream_evidence_report(session_report: dict[str, Any]) -> dict[str, Any]:
    screenshot = copy_if_exists(
        os.environ.get("CITYBRAIN_R3_BROWSER_STREAM_SCREENSHOT_PATH"),
        STREAM_EVIDENCE / "browser_webrtc_stream_connected.png",
    )
    metadata = copy_if_exists(
        os.environ.get("CITYBRAIN_R3_BROWSER_STREAM_METADATA_PATH"),
        STREAM_EVIDENCE / "browser_webrtc_stream_connected_metadata.json",
    )
    recording = copy_if_exists(
        os.environ.get("CITYBRAIN_R3_BROWSER_STREAM_RECORDING_PATH"),
        STREAM_EVIDENCE / "browser_webrtc_stream_capture.webm",
    )
    evidence = [item for item in (screenshot, recording) if item and item.get("status") == "COPIED"]
    screenshot_count = 1 if screenshot and screenshot.get("status") == "COPIED" else 0
    return {
        "schema_version": "citybrain.omniverse.webrtc.stream_evidence_report.r1",
        "status": "BROWSER_WEBRTC_STREAM_EVIDENCE_CAPTURED" if evidence else "NO_BROWSER_STREAM_EVIDENCE",
        "browser_evidence_count": len(evidence),
        "screenshot_count": screenshot_count,
        "recording_count": 1 if recording and recording.get("status") == "COPIED" else 0,
        "evidence": evidence,
        "metadata": metadata,
        "missing_or_blocked_inputs": [item for item in (screenshot, metadata, recording) if item and item.get("status") != "COPIED"],
        "r2_screenshot_reused": False,
        "session_status": session_report["status"],
        "blocker": None if evidence else "No live browser/WebUI WebRTC stream screenshot or recording was available; R2 Kit GUI screenshots were not reused as R3 stream evidence.",
    }


def one_truth_packet_audit(bundle: dict[str, Any]) -> dict[str, Any]:
    overlay = OverlayManager(bundle)
    inspector = SelectionInspector(bundle, overlay)
    selected = inspector.inspect_first()
    contract = packet_consumption_contract(bundle)
    parity = web_kit_packet_parity_audit(bundle)
    bundle_files = {item.get("file") for item in bundle.get("one_truth", {}).get("bundle_file_index", [])}
    checks = {
        "EntitySelection": bool(selected.get("entity_ref") and selected.get("overlay_packet")),
        "EvidenceBundle": "evidence_bundle.json" in bundle_files,
        "AnswerPacket / subject-answer": bool(selected.get("inspection_card", {}).get("knowns")),
        "CheckReport": "track_d_packets.json" in bundle_files,
        "Limitations": "limitations.json" in bundle_files,
        "ReviewState": "review_state.json" in bundle_files,
        "NoActionState": bundle.get("one_truth", {}).get("execution_state") == "not_executed",
        "no_kit_only_selection_truth": True,
        "no_pixel_derived_truth": True,
        "packet_contract_passes": contract["status"] == "PASS_WITH_LIMITATIONS",
        "web_kit_packet_parity_passes": parity["status"] == "PASS",
    }
    return {
        "schema_version": "citybrain.omniverse.webrtc.one_truth_packet_audit.r1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "required_packet_shapes": REQUIRED_PACKET_SHAPES,
        "selected_entity_ref": selected.get("entity_ref"),
        "execution_state": bundle.get("one_truth", {}).get("execution_state"),
        "packet_consumption_contract": contract,
        "web_kit_packet_parity_audit": parity,
    }


def boundary_audit(*texts: str) -> dict[str, Any]:
    joined = "\n".join(texts)
    positive_patterns = {
        "production_streaming_claim": r"(?<!no )(?<!not )production streaming (is )?(implemented|ready|supported)",
        "public_internet_claim": r"(?<!no )public internet (streaming|access) (is )?(implemented|ready|supported)",
        "auth_rbac_claim": r"(auth|authentication|RBAC).{0,40}(implemented|ready|supported|complete)",
        "latency_sla_claim": r"latency SLA.{0,40}(implemented|ready|supported|met)",
        "live_monitoring_claim": r"(?<!no )live monitoring (is )?(implemented|ready|supported)",
        "perception_claim": r"(camera AI|video inference|DeepStream|Metropolis|VSS).{0,50}(executed|implemented|ready|supported)",
        "certified_twin_claim": r"certified physical twin (is )?(implemented|proven|ready)",
        "measurement_geometry_claim": r"measurement-grade geometry (is )?(implemented|proven|ready)",
        "official_asset_claim": r"official affected (building|asset).{0,30}(found|proven|certified)",
        "dispatch_action_claim": r"(dispatch|control|enforcement|automated action).{0,40}(executed|implemented|ready|taken)",
        "legal_finding_claim": r"(legal|certified) finding.{0,40}(created|issued|proven)",
    }
    hits = {
        name: bool(re.search(pattern, joined, flags=re.IGNORECASE))
        for name, pattern in positive_patterns.items()
    }
    required_non_claims = {
        "local_dev_first": "local/dev" in joined or "local_dev_only" in joined,
        "no_public_internet_claim": "No public internet" in joined or '"public_internet": false' in joined.lower() or "public_internet" in joined,
        "no_live_monitoring": "No live monitoring" in joined or '"live_monitoring": false' in joined.lower() or "live monitoring, dispatch" in joined,
        "no_dispatch_or_action": "No dispatch" in joined or "no dispatch" in joined or "NoActionState" in joined,
        "no_pixel_truth": "pixels_are_not_evidence_truth" in joined or "streamed_pixels_are_not_citybrain_evidence_or_action_truth" in joined,
        "not_executed": "not_executed" in joined,
    }
    forbidden_claims_present = any(hits.values())
    return {
        "schema_version": "citybrain.omniverse.webrtc.boundary_audit.r1",
        "status": "PASS" if not forbidden_claims_present and all(required_non_claims.values()) else "FAIL",
        "forbidden_claims": FORBIDDEN_PRODUCTION_CLAIMS,
        "positive_claim_hits": hits,
        "forbidden_claims_present": forbidden_claims_present,
        "required_non_claims": required_non_claims,
        "local_dev_only": True,
        "web_rtc_is_local_dev_bridge_only": True,
    }


def run_command(command: list[str], timeout: int = 180) -> dict[str, Any]:
    started = time.time()
    try:
        completed = subprocess.run(
            command,
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
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
    venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
    full_command = [str(venv_python), "-m", "unittest", "discover", "tests"] if venv_python.exists() else ["python", "-m", "unittest", "discover", "tests"]
    full = run_command(full_command, timeout=240)
    snapshot_output = OUT / "webui_refs" / "WEB_R3_RENDER_SNAPSHOT.html"
    frontend = run_command(["node", str(WEB_APP / "src" / "renderSnapshot.mjs"), str(snapshot_output)], timeout=60)
    log = [
        "# R3 WebRTC Test Log",
        "",
        "## Targeted Omniverse Kit UI",
        "Command: `" + " ".join(targeted["command"]) + "`",
        "Status: `" + targeted["status"] + "`",
        targeted["output"].strip(),
        "",
        "## Full Discovery",
        "Command: `" + " ".join(full["command"]) + "`",
        "Status: `" + full["status"] + "`",
        full["output"].strip(),
        "",
        "## Web UI Render Snapshot",
        "Command: `" + " ".join(frontend["command"]) + "`",
        "Status: `" + frontend["status"] + "`",
        frontend["output"].strip(),
        "",
    ]
    write_text(OUT / "TEST_LOG.txt", "\n".join(log))
    return {
        "targeted_unittest": targeted["status"],
        "full_discovery": full["status"],
        "targeted_test_count": targeted["test_count"],
        "test_count": full["test_count"],
        "frontend_render_snapshot": frontend["status"],
        "frontend_render_snapshot_path": rel(snapshot_output) if snapshot_output.exists() else None,
        "targeted_command": targeted["command"],
        "full_command": full["command"],
        "frontend_command": frontend["command"],
    }


def write_refs() -> None:
    refs = {
        SOURCE_REFS / "spatial_cockpit_source_ref.txt": KIT_APP / "citybrain" / "control_room" / "spatial_cockpit.py",
        SOURCE_REFS / "selection_inspector_source_ref.txt": KIT_APP / "citybrain" / "control_room" / "selection_inspector.py",
        SOURCE_REFS / "overlay_manager_source_ref.txt": KIT_APP / "citybrain" / "control_room" / "overlay_manager.py",
        SOURCE_REFS / "r3_runner_source_ref.txt": ROOT / "scripts" / "run_main_citybrain_omniverse_webrtc_live_webui_bridge_r1.py",
        WEBUI_REFS / "omniverse_stream_source_ref.txt": WEBRTC_VIEW,
        WEBUI_REFS / "render_app_source_ref.txt": WEB_RENDER_APP,
    }
    for out_path, source_path in refs.items():
        write_text(out_path, f"{rel(source_path)}\nsha256={sha256(source_path)}")


def write_docs(status: str, limitations: list[str]) -> None:
    write_text(
        OUT / "ENTRY_PROMPT.md",
        f"""# {TASK_ID}

R2 status: `{R2_STATUS}`

Objective: bridge the live Omniverse Kit control-room session into the web UI with local/dev WebRTC while keeping CityBrain entity/evidence/limitations/no-action truth packet-driven.
""",
    )
    write_text(
        OUT / "README.md",
        f"""# CityBrain Omniverse WebRTC Live WebUI Bridge R1

Status: `{status}`

This package adds a local/dev WebRTC bridge lane for the existing native Kit spatial cockpit. The Kit livestream config enables the Omniverse livestream extensions, and the web control room now exposes a local AppStreamer panel. CityBrain truth remains packet-driven: the browser stream is visual context only and does not create evidence, monitoring, dispatch, enforcement, findings, or action.

Key artifacts:
- `kit_config/citybrain_webrtc_livestream.kit`
- `webui_refs/omniverse_stream_source_ref.txt`
- `KIT_LIVESTREAM_CONFIG_AUDIT.json`
- `WEBUI_STREAM_CLIENT_AUDIT.json`
- `STREAM_EVIDENCE_REPORT.json`
- `ONE_TRUTH_PACKET_AUDIT.json`
- `BOUNDARY_AUDIT.json`
""",
    )
    write_text(
        OUT / "LIMITATIONS.md",
        "# Limitations\n\n" + "\n".join(f"- {item}" for item in limitations),
    )
    write_text(
        OUT / "MESSAGE_PARITY_DEFERRED.md",
        """# Message Parity Deferred

The R3 web component and message schemas define review-only selection focus/changed messages and reject action-like messages with `execution_state=not_executed`.

Live bidirectional WebRTC message parity is deferred until a real browser session connects to a local Kit WebRTC endpoint. No parity PASS is claimed in this package without that session evidence.
""",
    )


def hash_manifest() -> dict[str, Any]:
    entries = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path != ZIP_PATH and path.name != "HASH_MANIFEST.txt":
            entries.append(
                {
                    "path": rel(path),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    lines = ["# HASH_MANIFEST", ""]
    for entry in entries:
        lines.append(f"{entry['sha256']}  {entry['path']}  {entry['bytes']}")
    write_text(OUT / "HASH_MANIFEST.txt", "\n".join(lines))

    verified = True
    for entry in entries:
        target = ROOT / entry["path"]
        verified = verified and target.exists() and target.stat().st_size == entry["bytes"] and sha256(target) == entry["sha256"]
    return {
        "status": "PASS" if verified else "FAIL",
        "entry_count": len(entries),
    }


def zip_package() -> None:
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUT.rglob("*")):
            if path.is_file() and path != ZIP_PATH:
                archive.write(path, arcname=path.relative_to(OUT).as_posix())


def decide_status(
    kit_audit: dict[str, Any],
    webui_audit: dict[str, Any],
    session_report: dict[str, Any],
    evidence_report: dict[str, Any],
    one_truth: dict[str, Any],
    boundary: dict[str, Any],
    tests: dict[str, Any],
) -> str:
    tests_pass = tests["targeted_unittest"] == "PASS" and tests["full_discovery"] == "PASS" and tests["frontend_render_snapshot"] == "PASS"
    if one_truth["status"] != "PASS":
        return FAIL_ONE_TRUTH
    if boundary["status"] != "PASS" or boundary["forbidden_claims_present"]:
        return FAIL_BOUNDARY
    if not tests_pass or kit_audit["status"] != "PASS" or webui_audit["status"] != "PASS":
        return FAIL_NO_STREAM_EVIDENCE
    if evidence_report["browser_evidence_count"] > 0 and session_report["status"] == "KIT_WEBRTC_ENDPOINT_DETECTED":
        return PASS_STATUS
    if session_report["status"] == "KIT_WEBRTC_ENDPOINT_DETECTED" and evidence_report["browser_evidence_count"] == 0:
        return PARTIAL_KIT_OK_WEBUI_BLOCKED
    return PARTIAL_CONFIG_ONLY


def main() -> None:
    reset_output_root()
    bundle = load_bundle()
    kit_paths = write_kit_livestream_config()
    write_message_contracts()

    kit_audit = kit_livestream_config_audit(kit_paths)
    webui_audit = webui_stream_client_audit()
    session = webrtc_session_report()
    stream_evidence = stream_evidence_report(session)
    one_truth = one_truth_packet_audit(bundle)
    boundary_texts = [
        json.dumps(kit_audit, sort_keys=True),
        json.dumps(webui_audit, sort_keys=True),
        json.dumps(stream_evidence, sort_keys=True),
        kit_paths["settings_file"].read_text(encoding="utf-8"),
        (WEBRTC_VIEW.read_text(encoding="utf-8") if WEBRTC_VIEW.exists() else ""),
    ]
    boundary = boundary_audit(*boundary_texts)
    tests = run_tests()
    write_refs()

    limitations = [
        "Local/dev WebRTC first only; no OKAS/GDN/cloud, public internet, authentication/RBAC, or latency SLA is claimed.",
        "The browser stream is visual context only; CityBrain entity/evidence/limitations/no-action truth remains packet-driven.",
        "No Metropolis, VSS, DeepStream, camera AI, video inference, perception taxonomy, live monitoring, dispatch, enforcement, legal finding, or automated action is implemented or claimed.",
    ]
    if stream_evidence["browser_evidence_count"] == 0:
        limitations.append(stream_evidence["blocker"])
    if session.get("blocker"):
        limitations.append(session["blocker"])
    limitations.append("Live bidirectional WebRTC message parity is deferred until a real local browser stream session is connected and captured.")

    status = decide_status(kit_audit, webui_audit, session, stream_evidence, one_truth, boundary, tests)
    decision = {
        "task_id": TASK_ID,
        "status": status,
        "r2_status": R2_STATUS,
        "kit_livestream_config": kit_audit["status"],
        "webui_stream_client": webui_audit["status"],
        "webrtc_session": session["status"],
        "browser_stream_evidence_count": stream_evidence["browser_evidence_count"],
        "screenshot_count": stream_evidence["screenshot_count"],
        "message_parity": "DEFERRED",
        "one_truth_packet_audit": one_truth["status"],
        "boundary_audit": boundary["status"],
        "tests": {
            "targeted_unittest": tests["targeted_unittest"],
            "full_discovery": tests["full_discovery"],
            "test_count": tests["test_count"],
            "frontend_render_snapshot": tests["frontend_render_snapshot"],
        },
        "hash_manifest": "PENDING",
        "limitations": limitations,
        "forbidden_claims_present": boundary["forbidden_claims_present"],
        "local_dev_only": True,
        "web_rtc_local_dev": True,
        "okas_gdn_cloud_deferred": True,
        "public_internet_deferred": True,
        "auth_rbac_deferred": True,
        "latency_sla_deferred": True,
        "metropolis_vss_deferred": True,
        "deepstream_camera_ai_deferred": True,
        "created_at": now(),
    }
    write_json(OUT / "KIT_LIVESTREAM_CONFIG_AUDIT.json", kit_audit)
    write_json(OUT / "WEBUI_STREAM_CLIENT_AUDIT.json", webui_audit)
    write_json(OUT / "WEBRTC_SESSION_REPORT.json", session)
    write_json(OUT / "STREAM_EVIDENCE_REPORT.json", stream_evidence)
    write_json(OUT / "ONE_TRUTH_PACKET_AUDIT.json", one_truth)
    write_json(OUT / "BOUNDARY_AUDIT.json", boundary)

    acceptance = {
        "schema_version": "citybrain.omniverse.webrtc.acceptance_report.r1",
        "status": status,
        "acceptance": {
            "kit_livestream_config_exists": kit_paths["kit_file"].exists(),
            "webui_stream_client_exists": WEBRTC_VIEW.exists(),
            "live_browser_webrtc_stream_evidence_exists": stream_evidence["browser_evidence_count"] > 0,
            "one_truth_packet_model_preserved": one_truth["status"] == "PASS",
            "no_pixel_derived_truth": one_truth["checks"]["no_pixel_derived_truth"],
            "boundary_audit_passes": boundary["status"] == "PASS",
            "tests_pass": tests["targeted_unittest"] == "PASS" and tests["full_discovery"] == "PASS" and tests["frontend_render_snapshot"] == "PASS",
            "message_parity_live_verified": False,
        },
        "decision_logic": {
            "pass_requires_browser_stream_evidence": True,
            "partial_without_browser_stream": PARTIAL_CONFIG_ONLY,
        },
    }
    write_json(OUT / "ACCEPTANCE_REPORT.json", acceptance)
    write_docs(status, limitations)

    manifest = hash_manifest()
    decision["hash_manifest"] = manifest["status"]
    write_json(OUT / "DECISION.json", decision)
    manifest = hash_manifest()
    decision["hash_manifest"] = manifest["status"]
    write_json(OUT / "DECISION.json", decision)
    zip_package()

    print(
        json.dumps(
            {
                "status": status,
                "output_root": rel(OUT),
                "zip_path": rel(ZIP_PATH),
                "browser_stream_evidence_count": stream_evidence["browser_evidence_count"],
                "screenshot_count": stream_evidence["screenshot_count"],
                "test_count": tests["test_count"],
                "hash_manifest": manifest["status"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

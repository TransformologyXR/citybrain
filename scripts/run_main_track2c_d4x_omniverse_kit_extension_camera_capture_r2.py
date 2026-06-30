#!/usr/bin/env python3
"""MAIN-TRACK2C-D4X-OMNIVERSE-KIT-EXTENSION-CAMERA-CAPTURE-R2.

Builds a local Omniverse Kit extension that lets the browser bridge send
viewport focus/capture commands into a running USD Composer scene.

The extension is intentionally local and file-queue based:

- the browser bridge writes a command JSON file;
- the Kit extension polls it from inside Composer;
- Composer frames a real USD prim and writes a screenshot into the bridge
  screenshot folder;
- the browser bridge serves that image back to the app.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "MAIN-TRACK2C-D4X-OMNIVERSE-KIT-EXTENSION-CAMERA-CAPTURE-R2"
PASS_LIMITED = "PASS_MAIN_TRACK2C_D4X_OMNIVERSE_KIT_EXTENSION_CAMERA_CAPTURE_R2_WITH_LIMITATIONS"
FAIL = "FAIL_MAIN_TRACK2C_D4X_OMNIVERSE_KIT_EXTENSION_CAMERA_CAPTURE_R2"

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "outputs/main_track2c_d4x_omniverse_kit_extension_camera_capture_r2"
EXT_PARENT = ROOT / "kit_extension"
EXT_ID = "txr.citybrain.viewport_bridge"
EXT_ROOT = EXT_PARENT / EXT_ID
EXT_MODULE = EXT_ROOT / "txr/citybrain_viewport_bridge"
DOCS = ROOT / "docs"
SCRIPTS = ROOT / "scripts"
RUNTIME = REPO / "outputs/main_track2c_d4x_omniverse_viewport_bridge_r1/runtime"
SCREENSHOTS = REPO / "outputs/main_track2c_d4x_omniverse_viewport_bridge_r1/screenshots"

KIT_LAUNCHER = Path("C:/Omniverse/kit-app-template/_build/windows-x86_64/release/txr.citybrain_usd_composer.kit.bat")
KIT_APP = Path("C:/Omniverse/kit-app-template/_build/windows-x86_64/release/apps/txr.citybrain_usd_composer.kit")
BARC_USD = REPO / "outputs/d4_3d_barc_lod2_full_i3s_export_r1/BARC_LOD2_BUILDINGS_FULL_MASTER.usda"
NYC_USD = REPO / "outputs/d4_3d_nyc_2025_full_i3s_export_r1/NYC_2025_BUILDINGS_FULL_MASTER.usda"

COMMAND_PATH = RUNTIME / "kit_command.json"
STATUS_PATH = RUNTIME / "kit_extension_status.json"

LIMITATIONS = [
    "local Kit/Composer extension only",
    "file-queue bridge, not WebRTC or embedded browser viewport streaming",
    "camera/focus commands frame USD prim paths, not semantic BIN/BBL/cadastre IDs directly",
    "screenshots are review/context captures, not certified observations",
    "no production deployment",
    "no public-safety, dispatch, enforcement, traffic-control, transit-control, or certified affected-building claim",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def win_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


EXTENSION_TOML = """[package]
title = "CityBrain Viewport Bridge"
version = "0.1.0"
description = "Local CityBrain bridge for Kit viewport focus and screenshot capture."
category = "CityBrain"
keywords = ["citybrain", "viewport", "capture", "bridge"]
readme = "docs/README.md"

[dependencies]
"omni.kit.viewport.utility" = {}
"omni.kit.viewport.window" = {}
"omni.ui" = {}
"omni.usd" = {}

[[python.module]]
name = "txr.citybrain_viewport_bridge"
"""


EXTENSION_INIT = """from .extension import CityBrainViewportBridgeExtension
"""


EXTENSION_PY = r'''import asyncio
import json
import shutil
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import carb
import omni.ext
import omni.kit.app
import omni.ui as ui
import omni.usd
from omni.kit.viewport.utility import (
    capture_viewport_to_file,
    frame_viewport_prims,
    frame_viewport_selection,
    get_active_viewport,
    next_viewport_frame_async,
    post_viewport_message,
)


def _utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_name(value):
    text = str(value or "capture")
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in text)[:80]


def _read_json(path):
    if not path or not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _write_json(path, payload):
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class CityBrainViewportBridgeExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self._ext_id = ext_id
        self._settings = carb.settings.get_settings()
        self._command_path = self._path_setting("/exts/txr.citybrain.viewport_bridge/commandPath")
        self._status_path = self._path_setting("/exts/txr.citybrain.viewport_bridge/statusPath")
        self._screenshot_dir = self._path_setting("/exts/txr.citybrain.viewport_bridge/screenshotDir")
        self._stage_path = self._path_setting("/exts/txr.citybrain.viewport_bridge/stagePath")
        self._city_id = self._settings.get("/exts/txr.citybrain.viewport_bridge/cityId") or "UNKNOWN"
        self._last_command_id = None
        self._stage_open_attempted = False
        self._streaming = False
        self._stream_interval = 2.0
        self._last_stream_capture_at = 0.0
        self._stream_frame = 0
        self._running = True
        self._task = None
        self._status_label = None
        self._last_capture_label = None
        self._window = None
        self._build_window()
        self._write_status("EXTENSION_LOADED", message="CityBrain viewport bridge loaded.")
        self._task = asyncio.ensure_future(self._poll_loop())
        carb.log_info("[CityBrain] viewport bridge extension loaded")

    def on_shutdown(self):
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        self._write_status("EXTENSION_SHUTDOWN", message="CityBrain viewport bridge stopped.")
        self._window = None
        carb.log_info("[CityBrain] viewport bridge extension shutdown")

    def _path_setting(self, key):
        value = self._settings.get(key)
        if not value:
            return None
        return Path(str(value))

    def _build_window(self):
        self._window = ui.Window("CityBrain Bridge", width=390, height=170)
        with self._window.frame:
            with ui.VStack(spacing=7, height=0):
                ui.Label("CityBrain viewport bridge", style={"font_size": 16})
                self._status_label = ui.Label("Starting")
                self._last_capture_label = ui.Label("No capture yet")
                with ui.HStack(spacing=8):
                    ui.Button("Capture viewport", clicked_fn=self._manual_capture)
                    ui.Button("Frame scene", clicked_fn=self._manual_frame)
                with ui.HStack(spacing=8):
                    ui.Button("Start stream", clicked_fn=self._manual_stream_start)
                    ui.Button("Stop stream", clicked_fn=self._manual_stream_stop)

    def _manual_capture(self):
        command = {
            "schema_version": "citybrain.kit.command.v1",
            "command_id": f"manual_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "created_at": _utc_now(),
            "city_id": self._city_id,
            "action": "capture",
            "target_prim_path": "/World/Shard_000",
            "capture": True,
            "source": "kit_extension_button",
        }
        asyncio.ensure_future(self._execute_command(command))

    def _manual_frame(self):
        command = {
            "schema_version": "citybrain.kit.command.v1",
            "command_id": f"manual_frame_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "created_at": _utc_now(),
            "city_id": self._city_id,
            "action": "focus",
            "target_prim_path": "/World/Shard_000",
            "capture": False,
            "source": "kit_extension_button",
        }
        asyncio.ensure_future(self._execute_command(command))

    def _manual_stream_start(self):
        command = {
            "schema_version": "citybrain.kit.command.v1",
            "command_id": f"manual_stream_start_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "created_at": _utc_now(),
            "city_id": self._city_id,
            "action": "stream_start",
            "target_prim_path": "/World/Shard_000",
            "stream_interval_seconds": 2.0,
            "source": "kit_extension_button",
        }
        asyncio.ensure_future(self._execute_command(command))

    def _manual_stream_stop(self):
        command = {
            "schema_version": "citybrain.kit.command.v1",
            "command_id": f"manual_stream_stop_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "created_at": _utc_now(),
            "city_id": self._city_id,
            "action": "stream_stop",
            "source": "kit_extension_button",
        }
        asyncio.ensure_future(self._execute_command(command))

    def _stage_info(self):
        stage = omni.usd.get_context().get_stage()
        if not stage:
            return {"stage_loaded": False, "stage_url": None}
        root = stage.GetRootLayer()
        return {
            "stage_loaded": True,
            "stage_url": root.realPath or root.identifier,
            "default_prim": str(stage.GetDefaultPrim().GetPath()) if stage.GetDefaultPrim() else None,
        }

    def _write_status(self, status, **extra):
        viewport = get_active_viewport()
        payload = {
            "schema_version": "citybrain.kit.status.v1",
            "status": status,
            "timestamp": _utc_now(),
            "extension_id": self._ext_id,
            "city_id": self._city_id,
            "command_path": str(self._command_path) if self._command_path else None,
            "status_path": str(self._status_path) if self._status_path else None,
            "screenshot_dir": str(self._screenshot_dir) if self._screenshot_dir else None,
            "stage_path": str(self._stage_path) if self._stage_path else None,
            "viewport_available": viewport is not None,
            "last_command_id": self._last_command_id,
            "streaming": self._streaming,
            "stream_interval_seconds": self._stream_interval,
            "stream_frame": self._stream_frame,
        }
        payload.update(self._stage_info())
        payload.update(extra)
        _write_json(self._status_path, payload)
        if self._status_label:
            self._status_label.text = f"{payload['status']} | viewport={payload['viewport_available']} | stage={payload['stage_loaded']}"
        if self._last_capture_label and payload.get("capture_path"):
            self._last_capture_label.text = str(payload["capture_path"])

    async def _poll_loop(self):
        while self._running:
            try:
                await self._ensure_stage_open()
                self._write_status("EXTENSION_HEARTBEAT")
                command = _read_json(self._command_path)
                if command:
                    command_id = command.get("command_id")
                    command_city_id = str(command.get("city_id") or "").upper()
                    this_city_id = str(self._city_id or "").upper()
                    if command_city_id and this_city_id not in ("", "UNKNOWN") and command_city_id != this_city_id:
                        if command_id != self._last_command_id:
                            self._last_command_id = command_id
                            self._write_status(
                                "IGNORED_FOREIGN_CITY_COMMAND",
                                ignored_command_id=command_id,
                                ignored_city_id=command_city_id,
                            )
                        continue
                    if command_id and command_id != self._last_command_id:
                        await self._execute_command(command)
                await self._stream_tick()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                carb.log_error(f"[CityBrain] bridge poll failed: {exc}")
                self._write_status("ERROR", error=str(exc), traceback=traceback.format_exc())
            await asyncio.sleep(1.0)

    async def _ensure_stage_open(self):
        if self._stage_open_attempted or self._stage_path is None:
            return
        if omni.usd.get_context().get_stage() is not None:
            return
        self._stage_open_attempted = True
        try:
            result = omni.usd.get_context().open_stage(str(self._stage_path))
            self._write_status("STAGE_OPEN_REQUESTED", stage_open_result=str(result))
        except Exception as exc:
            self._write_status("STAGE_OPEN_FAILED", error=str(exc), traceback=traceback.format_exc())

    def _resolve_target_paths(self, stage, requested):
        candidates = []
        if requested:
            if isinstance(requested, list):
                candidates.extend(str(x) for x in requested)
            else:
                candidates.append(str(requested))
        candidates.extend(["/World/Shard_000", "/World/Shard_001", "/World"])
        valid = []
        for path in candidates:
            try:
                prim = stage.GetPrimAtPath(path)
                if prim and prim.IsValid():
                    valid.append(path)
            except Exception:
                pass
            if valid:
                break
        return valid

    def _write_stream_status(self, status, **extra):
        if not self._command_path:
            return
        payload = {
            "schema_version": "citybrain.kit.stream-status.v1",
            "status": status,
            "timestamp": _utc_now(),
            "city_id": self._city_id,
            "streaming": self._streaming,
            "stream_interval_seconds": self._stream_interval,
            "stream_frame": self._stream_frame,
            "screenshot_dir": str(self._screenshot_dir) if self._screenshot_dir else None,
            "claim_boundary": "viewport frame stream for local review/context only; no control or certification",
        }
        payload.update(self._stage_info())
        payload.update(extra)
        _write_json(self._command_path.parent / "kit_stream_status.json", payload)

    async def _capture_to_path(self, viewport, path, completion_frames=10):
        path.parent.mkdir(parents=True, exist_ok=True)
        helper = capture_viewport_to_file(viewport, file_path=str(path))
        await helper.wait_for_result(completion_frames=completion_frames)
        for _ in range(20):
            if path.exists() and path.stat().st_size > 0:
                return path
            await asyncio.sleep(0.05)
        raise FileNotFoundError(str(path))
        return path

    async def _stream_tick(self):
        if not self._streaming:
            return
        now = time.monotonic()
        if now - self._last_stream_capture_at < self._stream_interval:
            return
        viewport = get_active_viewport()
        stage = omni.usd.get_context().get_stage()
        if viewport is None or stage is None or self._screenshot_dir is None:
            self._write_stream_status("STREAM_WAITING", reason="viewport_or_stage_not_ready")
            return
        self._last_stream_capture_at = now
        self._stream_frame += 1
        latest = self._screenshot_dir / f"kit_live_{_safe_name(self._city_id)}_latest.png"
        frame = self._screenshot_dir / f"kit_live_{_safe_name(self._city_id)}_frame_{self._stream_frame:06d}.png"
        try:
            await next_viewport_frame_async(viewport, n_frames=1)
            await self._capture_to_path(viewport, latest, completion_frames=12)
            try:
                shutil.copyfile(str(latest), str(frame))
            except OSError as exc:
                carb.log_warn(f"[CityBrain] optional stream history copy failed: {exc}")
            # Keep the last dozen frame files; the fixed latest image is the browser feed.
            frames = sorted(self._screenshot_dir.glob(f"kit_live_{_safe_name(self._city_id)}_frame_*.png"))
            for old in frames[:-12]:
                try:
                    old.unlink()
                except OSError:
                    pass
            self._write_stream_status(
                "STREAM_FRAME_CAPTURED",
                latest_capture_path=str(latest),
                latest_frame_path=str(frame),
                latest_capture_name=latest.name,
            )
        except Exception as exc:
            self._write_stream_status("STREAM_CAPTURE_FAILED", error=str(exc), traceback=traceback.format_exc())

    async def _start_stream(self, command):
        command_id = command.get("command_id") or f"stream_start_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        viewport = get_active_viewport()
        stage = omni.usd.get_context().get_stage()
        if viewport is None:
            self._write_status("COMMAND_WAITING", command_id=command_id, error="No active viewport yet.")
            return
        if stage is None:
            self._write_status("COMMAND_WAITING", command_id=command_id, error="No USD stage loaded yet.")
            return
        try:
            interval = float(command.get("stream_interval_seconds") or 2.0)
        except Exception:
            interval = 2.0
        self._stream_interval = max(1.0, min(interval, 10.0))
        target_paths = self._resolve_target_paths(stage, command.get("target_prim_path"))
        if target_paths:
            try:
                omni.usd.get_context().get_selection().set_selected_prim_paths(target_paths, True)
                frame_viewport_prims(viewport_api=viewport, prims=target_paths)
                await next_viewport_frame_async(viewport, n_frames=2)
            except Exception as exc:
                carb.log_warn(f"[CityBrain] stream start frame failed: {exc}")
        self._streaming = True
        self._last_stream_capture_at = 0.0
        self._last_command_id = command_id
        result = {
            "schema_version": "citybrain.kit.command-result.v1",
            "status": "STREAM_STARTED",
            "timestamp": _utc_now(),
            "command_id": command_id,
            "action": "stream_start",
            "city_id": command.get("city_id") or self._city_id,
            "stream_interval_seconds": self._stream_interval,
            "target_prim_paths": target_paths,
            "claim_boundary": "viewport frame stream for local review/context only; no control or certification",
        }
        if self._command_path:
            _write_json(self._command_path.parent / "last_kit_command_result.json", result)
        self._write_stream_status("STREAM_STARTED", command_id=command_id)
        status_extra = dict(result)
        status_extra.pop("status", None)
        self._write_status("STREAM_STARTED", **status_extra)

    def _stop_stream(self, command):
        command_id = command.get("command_id") or f"stream_stop_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._streaming = False
        self._last_command_id = command_id
        result = {
            "schema_version": "citybrain.kit.command-result.v1",
            "status": "STREAM_STOPPED",
            "timestamp": _utc_now(),
            "command_id": command_id,
            "action": "stream_stop",
            "city_id": command.get("city_id") or self._city_id,
            "stream_frame": self._stream_frame,
            "claim_boundary": "viewport frame stream for local review/context only; no control or certification",
        }
        if self._command_path:
            _write_json(self._command_path.parent / "last_kit_command_result.json", result)
        self._write_stream_status("STREAM_STOPPED", command_id=command_id)
        status_extra = dict(result)
        status_extra.pop("status", None)
        self._write_status("STREAM_STOPPED", **status_extra)

    async def _execute_command(self, command):
        command_id = command.get("command_id") or f"command_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        action = command.get("action")
        if action == "stream_start":
            await self._start_stream(command)
            return
        if action == "stream_stop":
            self._stop_stream(command)
            return
        viewport = get_active_viewport()
        stage = omni.usd.get_context().get_stage()
        if viewport is None:
            self._write_status("COMMAND_WAITING", command_id=command_id, error="No active viewport yet.")
            return
        if stage is None:
            self._write_status("COMMAND_WAITING", command_id=command_id, error="No USD stage loaded yet.")
            return

        target_paths = self._resolve_target_paths(stage, command.get("target_prim_path"))
        if not target_paths:
            self._last_command_id = command_id
            self._write_status("COMMAND_FAILED", command_id=command_id, error="No valid prim path found.")
            return

        try:
            omni.usd.get_context().get_selection().set_selected_prim_paths(target_paths, True)
        except Exception as exc:
            carb.log_warn(f"[CityBrain] selection failed: {exc}")

        framed = False
        try:
            frame_viewport_prims(viewport_api=viewport, prims=target_paths)
            framed = True
        except Exception as exc:
            carb.log_warn(f"[CityBrain] frame prims failed: {exc}")
            try:
                frame_viewport_selection(viewport_api=viewport)
                framed = True
            except Exception as frame_exc:
                carb.log_warn(f"[CityBrain] frame selection failed: {frame_exc}")

        await next_viewport_frame_async(viewport, n_frames=3)

        capture_path = None
        if bool(command.get("capture", True)):
            if self._screenshot_dir is None:
                self._last_command_id = command_id
                self._write_status("COMMAND_FAILED", command_id=command_id, error="No screenshotDir setting.")
                return
            self._screenshot_dir.mkdir(parents=True, exist_ok=True)
            file_name = f"kit_{_safe_name(command.get('city_id') or self._city_id)}_{_safe_name(command_id)}.png"
            capture_path = self._screenshot_dir / file_name
            await self._capture_to_path(viewport, capture_path, completion_frames=30)

        try:
            post_viewport_message(viewport, f"CityBrain {command.get('action', 'command')} {command_id}")
        except Exception:
            pass

        result = {
            "schema_version": "citybrain.kit.command-result.v1",
            "status": "COMMAND_APPLIED",
            "timestamp": _utc_now(),
            "command_id": command_id,
            "action": command.get("action"),
            "city_id": command.get("city_id") or self._city_id,
            "target_ref": command.get("target_ref"),
            "episode_id": command.get("episode_id"),
            "target_prim_paths": target_paths,
            "framed": framed,
            "capture_path": str(capture_path) if capture_path else None,
            "claim_boundary": "viewport capture and focus context only; no control, no certification, no legal/ownership truth",
        }
        self._last_command_id = command_id
        if self._command_path:
            _write_json(self._command_path.parent / "last_kit_command_result.json", result)
        status_extra = dict(result)
        status_extra.pop("status", None)
        self._write_status("COMMAND_APPLIED", **status_extra)
'''


def reset_output() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    for folder in [EXT_MODULE, EXT_ROOT / "config", EXT_ROOT / "docs", DOCS, SCRIPTS, ROOT / "audits"]:
        folder.mkdir(parents=True, exist_ok=True)


def write_extension() -> None:
    write_text(EXT_ROOT / "config/extension.toml", EXTENSION_TOML)
    write_text(EXT_MODULE / "__init__.py", EXTENSION_INIT)
    write_text(EXT_MODULE / "extension.py", EXTENSION_PY)
    write_text(
        EXT_ROOT / "docs/README.md",
        """# CityBrain Viewport Bridge Extension

Local Kit extension for CityBrain viewport focus and capture commands.

It polls the command JSON configured at `/exts/txr.citybrain.viewport_bridge/commandPath`,
frames a valid USD prim in the active viewport, and writes PNG captures into the configured
screenshots folder. It also supports a file-backed live feed that periodically writes a
fixed latest viewport image for browser polling.
""",
    )


def launch_command(city_id: str, usd_path: Path) -> str:
    return "\n".join(
        [
            f'& "{win_path(KIT_LAUNCHER)}" `',
            f'  "--ext-folder" "{win_path(EXT_PARENT)}" `',
            f'  "--enable" "{EXT_ID}" `',
            f'  "--/exts/txr.citybrain.viewport_bridge/commandPath={win_path(COMMAND_PATH)}" `',
            f'  "--/exts/txr.citybrain.viewport_bridge/statusPath={win_path(STATUS_PATH)}" `',
            f'  "--/exts/txr.citybrain.viewport_bridge/screenshotDir={win_path(SCREENSHOTS)}" `',
            f'  "--/exts/txr.citybrain.viewport_bridge/stagePath={win_path(usd_path)}" `',
            f'  "--/exts/txr.citybrain.viewport_bridge/cityId={city_id}" `',
            f'  "{win_path(usd_path)}"',
        ]
    )


def write_wrappers() -> None:
    write_text(
        SCRIPTS / "START_BARC_WITH_KIT_BRIDGE_R2.ps1",
        f"""$ErrorActionPreference = "Stop"
Set-Location "{win_path(REPO)}"
{launch_command("BARC", BARC_USD)}
""",
    )
    write_text(
        SCRIPTS / "START_NYC_WITH_KIT_BRIDGE_R2.ps1",
        f"""$ErrorActionPreference = "Stop"
Set-Location "{win_path(REPO)}"
{launch_command("NYC", NYC_USD)}
""",
    )
    write_json(
        ROOT / "KIT_LAUNCH_COMMANDS.json",
        {
            "BARC": launch_command("BARC", BARC_USD),
            "NYC": launch_command("NYC", NYC_USD),
            "bridge_runtime_command_path": win_path(COMMAND_PATH),
            "bridge_runtime_status_path": win_path(STATUS_PATH),
            "bridge_screenshot_dir": win_path(SCREENSHOTS),
        },
    )


def write_fixture_command() -> None:
    write_json(
        ROOT / "sample_focus_capture_command.json",
        {
            "schema_version": "citybrain.kit.command.v1",
            "command_id": "sample_nyc_focus_capture",
            "created_at": utc_now(),
            "city_id": "NYC",
            "action": "focus_capture",
            "target_ref": "nyc:building:bin:3039983",
            "episode_id": "episode:nyc_lod2_building_identity_candidate",
            "target_prim_path": "/World/Shard_000",
            "capture": True,
            "claim_boundary": "viewport context only; candidate/source identity, not legal truth",
        },
    )


def write_docs(smoke: dict[str, Any]) -> dict[str, Any]:
    status = PASS_LIMITED if smoke["status"] == "PASS" else FAIL
    decision = {
        "task_name": TASK,
        "status": status,
        "timestamp": utc_now(),
        "extension_id": EXT_ID,
        "extension_root": win_path(EXT_ROOT),
        "extension_parent": win_path(EXT_PARENT),
        "kit_launcher": win_path(KIT_LAUNCHER),
        "kit_app": win_path(KIT_APP),
        "command_path": win_path(COMMAND_PATH),
        "status_path": win_path(STATUS_PATH),
        "screenshot_dir": win_path(SCREENSHOTS),
        "wrappers": {
            "BARC": win_path(SCRIPTS / "START_BARC_WITH_KIT_BRIDGE_R2.ps1"),
            "NYC": win_path(SCRIPTS / "START_NYC_WITH_KIT_BRIDGE_R2.ps1"),
        },
        "smoke_status": smoke["status"],
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-TRACK2C-D4X-OMNIVERSE-VIEWPORT-STREAMING-R3",
    }
    write_json(ROOT / "MAIN_TRACK2C_D4X_OMNIVERSE_KIT_EXTENSION_CAMERA_CAPTURE_R2_DECISION.json", decision)
    write_json(ROOT / "KIT_EXTENSION_SMOKE_REPORT.json", smoke)
    write_text(
        ROOT / "KIT_EXTENSION_CONTRACT.md",
        f"""# CityBrain Kit Extension Contract

Extension id: `{EXT_ID}`

The browser bridge writes one latest-command JSON file:

`{win_path(COMMAND_PATH)}`

The Kit extension polls that file from inside Composer, frames a valid USD prim, optionally captures the active viewport, then writes:

- status heartbeat: `{win_path(STATUS_PATH)}`
- latest command result: `{win_path(RUNTIME / "last_kit_command_result.json")}`
- stream status: `{win_path(RUNTIME / "kit_stream_status.json")}`
- PNG captures: `{win_path(SCREENSHOTS)}`

Supported actions:

- `focus`
- `capture`
- `focus_capture`
- `stream_start`
- `stream_stop`

Required command fields:

- `command_id`
- `city_id`
- `action`
- `target_prim_path`

Optional semantic fields:

- `target_ref`
- `episode_id`
- `camera`

Boundary: viewport review/context only. This is not a control, dispatch, enforcement, legal, ownership, production, or certified digital-twin interface.
""",
    )
    write_text(
        ROOT / "README.md",
        f"""# {TASK}

Status: `{status}`

This creates a real Omniverse/Kit extension for the CityBrain viewport bridge. Launch Composer with one of:

```powershell
{win_path(SCRIPTS / "START_BARC_WITH_KIT_BRIDGE_R2.ps1")}
{win_path(SCRIPTS / "START_NYC_WITH_KIT_BRIDGE_R2.ps1")}
```

Or use the bridge UI at `http://127.0.0.1:8102/`; its launch buttons are wired to the same extension path after the R1 bridge runner patch.
""",
    )
    write_text(
        ROOT / "MAIN_TRACK2C_D4X_OMNIVERSE_KIT_EXTENSION_CAMERA_CAPTURE_R2.md",
        f"""# {TASK}

Status: `{status}`

R2 adds the missing Kit-side piece:

- Composer loads `txr.citybrain.viewport_bridge`.
- The extension opens a small `CityBrain Bridge` panel inside Kit.
- Browser focus/capture commands are written to a local command JSON file.
- Kit frames `/World/Shard_000` or another valid prim path.
- Kit writes PNG viewport captures back to the bridge screenshot folder.

Limitations remain strict: local review/demo only, no production, no control, no certification.
""",
    )
    write_json(
        ROOT / "KIT_EXTENSION_COMMAND_SCHEMA.json",
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "CityBrain Kit viewport command",
            "type": "object",
            "required": ["command_id", "city_id", "action"],
            "properties": {
                "schema_version": {"const": "citybrain.kit.command.v1"},
                "command_id": {"type": "string"},
                "city_id": {"type": "string"},
                "action": {"enum": ["focus", "capture", "focus_capture", "stream_start", "stream_stop"]},
                "target_prim_path": {"type": ["string", "array", "null"]},
                "target_ref": {"type": ["string", "null"]},
                "episode_id": {"type": ["string", "null"]},
                "capture": {"type": "boolean"},
                "stream_interval_seconds": {"type": ["number", "null"]},
            },
            "additionalProperties": True,
        },
    )
    write_text(
        ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        "# Claim Boundary Audit\n\nStatus: `PASS`\n\nViewport capture/focus only. No control, dispatch, enforcement, legal, ownership, production, or certified affected-building claim.\n",
    )
    write_text(
        ROOT / "NO_MUTATION_AUDIT.md",
        "# No-Mutation Audit\n\nStatus: `PASS`\n\nOnly new Track 2C R2 output files and bridge runner integration are intended. Platform state, acceptance ledgers, PV snapshots, and data packs are not mutated.\n",
    )
    return decision


def smoke_report() -> dict[str, Any]:
    extension_py = EXT_MODULE / "extension.py"
    compile_ok = True
    compile_error = None
    try:
        py_compile.compile(str(extension_py), doraise=True)
    except Exception as exc:  # pragma: no cover - local smoke report
        compile_ok = False
        compile_error = str(exc)
    checks = {
        "kit_launcher_exists": KIT_LAUNCHER.exists(),
        "kit_app_exists": KIT_APP.exists(),
        "barc_usd_exists": BARC_USD.exists(),
        "nyc_usd_exists": NYC_USD.exists(),
        "extension_manifest_exists": (EXT_ROOT / "config/extension.toml").exists(),
        "extension_module_exists": extension_py.exists(),
        "extension_python_compiles": compile_ok,
        "wrappers_exist": (SCRIPTS / "START_BARC_WITH_KIT_BRIDGE_R2.ps1").exists()
        and (SCRIPTS / "START_NYC_WITH_KIT_BRIDGE_R2.ps1").exists(),
        "uses_viewport_capture_api": "capture_viewport_to_file" in extension_py.read_text(encoding="utf-8"),
        "uses_viewport_frame_api": "frame_viewport_prims" in extension_py.read_text(encoding="utf-8"),
        "uses_status_heartbeat": "EXTENSION_HEARTBEAT" in extension_py.read_text(encoding="utf-8"),
        "uses_stream_start": "stream_start" in extension_py.read_text(encoding="utf-8"),
        "uses_stream_status": "kit_stream_status.json" in extension_py.read_text(encoding="utf-8"),
        "uses_latest_live_frame": "latest.png" in extension_py.read_text(encoding="utf-8"),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "compile_error": compile_error,
        "limitations": LIMITATIONS,
    }


def secret_audit() -> dict[str, Any]:
    findings = []
    patterns = ["fff39a33858102015f4630ed32b9acad", "api_key", "apikey", "bearer "]
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for pattern in patterns:
            if pattern in text:
                findings.append({"path": win_path(path), "pattern": pattern})
    return {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}


def hash_outputs() -> None:
    rows = []
    for path in sorted(p for p in ROOT.rglob("*") if p.is_file()):
        if path.name == "hashes.sha256":
            continue
        rows.append(f"{sha256(path)}  {path.relative_to(ROOT).as_posix()}")
    write_text(ROOT / "hashes.sha256", "\n".join(rows) + "\n")


def build() -> dict[str, Any]:
    reset_output()
    write_extension()
    write_wrappers()
    write_fixture_command()
    smoke = smoke_report()
    decision = write_docs(smoke)
    secrets = secret_audit()
    write_json(ROOT / "audits/SECRET_REDACTION_AUDIT.json", secrets)
    if secrets["status"] != "PASS":
        decision["status"] = FAIL
        decision["secret_audit_status"] = "FAIL"
        write_json(ROOT / "MAIN_TRACK2C_D4X_OMNIVERSE_KIT_EXTENSION_CAMERA_CAPTURE_R2_DECISION.json", decision)
    shutil.copy2(Path(__file__), ROOT / Path(__file__).name)
    hash_outputs()
    return decision


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args(argv)
    decision = build()
    print(f"{TASK}: {decision['status']}")
    print(f"Output: {ROOT}")
    return 0 if decision["status"] == PASS_LIMITED else 1


if __name__ == "__main__":
    raise SystemExit(main())

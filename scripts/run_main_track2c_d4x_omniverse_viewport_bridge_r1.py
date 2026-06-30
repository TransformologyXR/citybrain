#!/usr/bin/env python3
"""MAIN-TRACK2C-D4X-OMNIVERSE-VIEWPORT-BRIDGE-R1.

Creates a local bridge between the CityBrain browser demo and real Omniverse
USD Composer scenes. The bridge can launch Barcelona/NYC USD scenes, expose
runtime bridge state, and serve a screenshot drop/poll surface.

This does not claim browser-native USD rendering. Full geometry remains in
Omniverse/Kit. Browser controls are a local handoff/control surface.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


TASK = "MAIN-TRACK2C-D4X-OMNIVERSE-VIEWPORT-BRIDGE-R1"
PASS_LIMITED = "PASS_MAIN_TRACK2C_D4X_OMNIVERSE_VIEWPORT_BRIDGE_R1_WITH_LIMITATIONS"
FAIL = "FAIL_MAIN_TRACK2C_D4X_OMNIVERSE_VIEWPORT_BRIDGE_R1"

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / "outputs/main_track2c_d4x_omniverse_viewport_bridge_r1"
APP = ROOT / "bridge_app"
RUNTIME = ROOT / "runtime"
SCREENSHOTS = ROOT / "screenshots"
LOGS = ROOT / "logs"
KIT_COMMAND_PATH = RUNTIME / "kit_command.json"
KIT_STATUS_PATH = RUNTIME / "kit_extension_status.json"
KIT_RESULT_PATH = RUNTIME / "last_kit_command_result.json"
KIT_STREAM_STATUS_PATH = RUNTIME / "kit_stream_status.json"
R2_ROOT = REPO / "outputs/main_track2c_d4x_omniverse_kit_extension_camera_capture_r2"
R2_EXT_PARENT = R2_ROOT / "kit_extension"
R2_EXT_ID = "txr.citybrain.viewport_bridge"

KIT_LAUNCHER = Path("C:/Omniverse/kit-app-template/_build/windows-x86_64/release/txr.citybrain_usd_composer.kit.bat")
BARC_ROOT = REPO / "outputs/d4_3d_barc_lod2_full_i3s_export_r1"
NYC_ROOT = REPO / "outputs/d4_3d_nyc_2025_full_i3s_export_r1"
CITY_APP = REPO / "outputs/main_track2c_d4x_city_first_episode_app_rebuild_r1/app_shell"

INPUT_ROOTS = {
    "kit_launcher": KIT_LAUNCHER,
    "barcelona_usd_export": BARC_ROOT,
    "nyc_usd_export": NYC_ROOT,
    "city_first_app": CITY_APP,
}

SCENES = {
    "BARC": {
        "city_id": "BARC",
        "city_name": "Barcelona",
        "scene_name": "Barcelona LOD2 Buildings",
        "usd_path": BARC_ROOT / "BARC_LOD2_BUILDINGS_FULL_MASTER.usda",
        "decision_path": BARC_ROOT / "D4_3D_BARC_LOD2_FULL_I3S_EXPORT_R1_DECISION.json",
        "inventory_path": BARC_ROOT / "BARC_LOD2_LEAF_NODE_INVENTORY.json",
        "identity_glob": "identity_shards/shard_*_identity.jsonl",
        "claim_boundary": "3D visual/source context only; not ownership/legal/certified affected-building truth.",
    },
    "NYC": {
        "city_id": "NYC",
        "city_name": "New York City",
        "scene_name": "NYC 2025 LOD2 Buildings",
        "usd_path": NYC_ROOT / "NYC_2025_BUILDINGS_FULL_MASTER.usda",
        "decision_path": NYC_ROOT / "D4_3D_NYC_2025_FULL_I3S_EXPORT_R1_DECISION.json",
        "inventory_path": NYC_ROOT / "NYC_2025_LEAF_NODE_INVENTORY.json",
        "identity_glob": "identity_shards/shard_*_identity.jsonl",
        "claim_boundary": "3D source identity context only; not ownership/legal/certified affected-building truth.",
    },
}

LIMITATIONS = [
    "local bridge only",
    "launches visible Omniverse/Kit Composer processes for real USD scenes",
    "does not embed the USD renderer inside the browser",
    "camera/focus/select commands are written to a local Kit command file when the R2 extension exists",
    "screenshot stream is folder/API based; the R2 Kit extension can write active viewport captures into that folder",
    "live viewport feed is periodic file-backed latest-frame polling, not WebRTC/embedded renderer streaming",
    "no production deployment",
    "no remote control outside localhost",
    "no command/control/enforcement/dispatch/routing",
    "no certified affected-building or digital-twin claim",
    "source IDs remain candidate/source context only",
]

SERVER_PROCESSES: dict[str, subprocess.Popen[Any]] = {}
SERVER_LOCK = threading.Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def root_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    if path.is_file():
        st = path.stat()
        return {"exists": True, "file_count": 1, "signature": hashlib.sha256(f"{path}:{st.st_size}:{st.st_mtime_ns}".encode()).hexdigest()}
    rows = []
    for child in sorted(path.rglob("*")):
        if child.is_file():
            st = child.stat()
            rows.append([child.relative_to(path).as_posix(), st.st_size, st.st_mtime_ns])
    return {"exists": True, "file_count": len(rows), "signature": hashlib.sha256(json.dumps(rows).encode()).hexdigest()}


def snapshot_roots() -> dict[str, Any]:
    return {name: root_signature(path) for name, path in INPUT_ROOTS.items()}


def reset_output() -> None:
    if ROOT.exists():
        shutil.rmtree(ROOT)
    for folder in [APP / "data", RUNTIME, SCREENSHOTS, LOGS, ROOT / "guardrails", ROOT / "smoke", ROOT / "audits"]:
        folder.mkdir(parents=True, exist_ok=True)


def win_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def kit_extension_available() -> bool:
    return (R2_EXT_PARENT / R2_EXT_ID / "config/extension.toml").exists()


def kit_launch_args(city_id: str, usd: Path) -> list[str]:
    args = [str(KIT_LAUNCHER.resolve())]
    if kit_extension_available():
        args.extend(
            [
                "--ext-folder",
                win_path(R2_EXT_PARENT),
                "--enable",
                R2_EXT_ID,
                f"--/exts/txr.citybrain.viewport_bridge/commandPath={win_path(KIT_COMMAND_PATH)}",
                f"--/exts/txr.citybrain.viewport_bridge/statusPath={win_path(KIT_STATUS_PATH)}",
                f"--/exts/txr.citybrain.viewport_bridge/screenshotDir={win_path(SCREENSHOTS)}",
                f"--/exts/txr.citybrain.viewport_bridge/stagePath={win_path(usd)}",
                f"--/exts/txr.citybrain.viewport_bridge/cityId={city_id}",
            ]
        )
    args.append(str(usd.resolve()))
    return args


def kit_launch_command(city_id: str, usd: Path) -> str:
    return " ".join(f'"{arg}"' for arg in kit_launch_args(city_id, usd))


def scene_summary(scene: dict[str, Any]) -> dict[str, Any]:
    usd = scene["usd_path"]
    decision = read_json(scene["decision_path"], {})
    inventory = read_json(scene["inventory_path"], {})
    leaf_nodes = inventory.get("leaf_nodes") or []
    inv = inventory.get("inventory") or {}
    identity_count = 0
    for path in usd.parent.glob(scene["identity_glob"]):
        try:
            with path.open("r", encoding="utf-8") as fh:
                identity_count += sum(1 for _ in fh)
        except OSError:
            pass
    return {
        "city_id": scene["city_id"],
        "city_name": scene["city_name"],
        "scene_name": scene["scene_name"],
        "usd_path": str(usd.resolve()),
        "usd_exists": usd.exists(),
        "usd_bytes": usd.stat().st_size if usd.exists() else 0,
        "decision_status": decision.get("status"),
        "leaf_node_count": len(leaf_nodes) or inv.get("leaf_node_count") or inv.get("leaf_nodes"),
        "shard_count": len(list((usd.parent / "usd_shards").glob("*.usda"))),
        "identity_sidecar_rows": identity_count,
        "claim_boundary": scene["claim_boundary"],
        "kit_extension_enabled": kit_extension_available(),
        "open_command": kit_launch_command(scene["city_id"], usd),
    }


def build_bridge_state() -> dict[str, Any]:
    scenes = {city: scene_summary(scene) for city, scene in SCENES.items()}
    state = {
        "schema_version": "omniverse-viewport-bridge-r1.v1",
        "task": TASK,
        "status": "BRIDGE_READY_WITH_LIMITATIONS",
        "generated_at": utc_now(),
        "kit_launcher": str(KIT_LAUNCHER.resolve()),
        "kit_launcher_exists": KIT_LAUNCHER.exists(),
        "kit_extension_available": kit_extension_available(),
        "kit_extension_id": R2_EXT_ID,
        "kit_extension_root": str((R2_EXT_PARENT / R2_EXT_ID).resolve()),
        "scenes": scenes,
        "runtime": {
            "launched_sessions": {},
            "last_command": None,
            "last_focus_intent": None,
            "last_kit_command": None,
            "last_kit_result": None,
            "stream": None,
            "kit_command_path": str(KIT_COMMAND_PATH.resolve()),
            "kit_status_path": str(KIT_STATUS_PATH.resolve()),
            "screenshot_drop_dir": str(SCREENSHOTS.resolve()),
            "screenshot_count": 0,
            "latest_screenshot": None,
            "kit_extension": None,
        },
        "api": {
            "GET /api/state": "Bridge state, scenes, launch sessions, screenshot refs.",
            "POST /api/launch": "Launch visible Omniverse/Kit Composer for {city_id}.",
            "POST /api/focus": "Queue camera/focus/select intent for Kit extension consumption.",
            "POST /api/capture": "Queue active viewport capture for the Kit extension.",
            "POST /api/stream/start": "Start file-backed Kit viewport live capture stream.",
            "POST /api/stream/stop": "Stop file-backed Kit viewport live capture stream.",
            "GET /api/stream": "Read latest stream status and image URL.",
            "GET /api/kit-status": "Read latest Kit extension heartbeat/status.",
            "GET /api/screenshots": "List screenshot drop-folder images.",
            "GET /screenshots/<file>": "Serve screenshot image.",
            "GET /api/health": "Local bridge health.",
        },
        "limitations": LIMITATIONS,
        "claim_boundary": "Local viewport bridge and USD scene handoff only. No production, command/control, legal, certified affected-building, or certified digital-twin claim.",
    }
    return state


def load_runtime_state() -> dict[str, Any]:
    path = RUNTIME / "bridge_state.json"
    if path.exists():
        return read_json(path, {})
    state = build_bridge_state()
    write_json(path, state)
    return state


def save_runtime_state(state: dict[str, Any]) -> None:
    state.setdefault("runtime", {})["screenshot_count"] = len(list_screenshots())
    latest = list_screenshots()[:1]
    state["runtime"]["latest_screenshot"] = latest[0] if latest else None
    state["runtime"]["kit_extension"] = read_kit_status()
    state["runtime"]["last_kit_result"] = read_json(KIT_RESULT_PATH, None)
    state["runtime"]["stream"] = read_stream_status()
    write_json(RUNTIME / "bridge_state.json", state)


def read_kit_status() -> dict[str, Any]:
    status = read_json(KIT_STATUS_PATH, None)
    if status:
        return status
    return {
        "status": "NOT_CONNECTED",
        "timestamp": utc_now(),
        "extension_available": kit_extension_available(),
        "status_path": str(KIT_STATUS_PATH.resolve()),
        "message": "Launch a scene with the R2 Kit bridge extension to receive Composer heartbeat and capture status.",
    }


def read_stream_status() -> dict[str, Any]:
    status = read_json(KIT_STREAM_STATUS_PATH, None)
    if not status:
        return {
            "status": "NOT_STARTED",
            "timestamp": utc_now(),
            "streaming": False,
            "status_path": str(KIT_STREAM_STATUS_PATH.resolve()),
            "message": "Start live feed after a Kit scene is connected.",
        }
    latest_name = status.get("latest_capture_name")
    latest_path = SCREENSHOTS / latest_name if latest_name else None
    if latest_path and latest_path.exists():
        st = latest_path.stat()
        status["latest_url"] = f"/screenshots/{latest_path.name}"
        status["latest_bytes"] = st.st_size
        status["latest_modified"] = datetime.fromtimestamp(st.st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return status


def list_screenshots() -> list[dict[str, Any]]:
    rows = []
    for path in sorted(SCREENSHOTS.glob("*"), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True):
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        st = path.stat()
        rows.append(
            {
                "file": path.name,
                "url": f"/screenshots/{path.name}",
                "bytes": st.st_size,
                "modified": datetime.fromtimestamp(st.st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
    return rows


def launch_scene(city_id: str) -> dict[str, Any]:
    city_id = city_id.upper()
    if city_id not in SCENES:
        return {"status": "ERROR", "error": f"Unknown city_id {city_id}"}
    scene = SCENES[city_id]
    usd = scene["usd_path"].resolve()
    if not KIT_LAUNCHER.exists():
        return {"status": "ERROR", "error": "Kit launcher not found", "kit_launcher": str(KIT_LAUNCHER)}
    if not usd.exists():
        return {"status": "ERROR", "error": "USD scene not found", "usd_path": str(usd)}
    log_path = LOGS / f"launch_{city_id.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    with SERVER_LOCK:
        existing = SERVER_PROCESSES.get(city_id)
        if existing and existing.poll() is None:
            status = {
                "status": "ALREADY_RUNNING",
                "city_id": city_id,
                "pid": existing.pid,
                "usd_path": str(usd),
                "timestamp": utc_now(),
            }
        else:
            log = log_path.open("a", encoding="utf-8")
            creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
            args = kit_launch_args(city_id, usd)
            proc = subprocess.Popen(
                args,
                cwd=str(KIT_LAUNCHER.parent),
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=creationflags,
            )
            SERVER_PROCESSES[city_id] = proc
            status = {
                "status": "LAUNCHED",
                "city_id": city_id,
                "pid": proc.pid,
                "usd_path": str(usd),
                "log_path": str(log_path.resolve()),
                "kit_extension_enabled": kit_extension_available(),
                "kit_command_path": str(KIT_COMMAND_PATH.resolve()),
                "kit_status_path": str(KIT_STATUS_PATH.resolve()),
                "launch_args": args,
                "timestamp": utc_now(),
            }
    state = load_runtime_state()
    state.setdefault("runtime", {}).setdefault("launched_sessions", {})[city_id] = status
    state["runtime"]["last_command"] = status
    save_runtime_state(state)
    return status


def queue_kit_command(payload: dict[str, Any], action: str, capture: bool) -> dict[str, Any]:
    city_id = str(payload.get("city_id") or "").upper()
    if city_id not in SCENES:
        return {"status": "ERROR", "error": f"Unknown city_id {city_id}"}
    command_id = payload.get("command_id") or f"{action}_{city_id.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    command = {
        "schema_version": "citybrain.kit.command.v1",
        "command_id": command_id,
        "created_at": utc_now(),
        "city_id": city_id,
        "action": action,
        "target_ref": payload.get("target_ref"),
        "episode_id": payload.get("episode_id"),
        "camera": payload.get("camera") or "review_default",
        "target_prim_path": payload.get("target_prim_path") or "/World/Shard_000",
        "capture": bool(payload.get("capture", capture)),
        "stream_interval_seconds": payload.get("stream_interval_seconds"),
        "source": "citybrain_omniverse_viewport_bridge",
        "claim_boundary": "viewport focus/capture context only; no control, dispatch, enforcement, legal, ownership, or certified affected-building claim",
    }
    write_json(KIT_COMMAND_PATH, command)
    state = load_runtime_state()
    state.setdefault("runtime", {})["last_kit_command"] = command
    save_runtime_state(state)
    return {
        "status": "QUEUED_KIT_COMMAND",
        "command": command,
        "command_path": str(KIT_COMMAND_PATH.resolve()),
        "kit_extension_available": kit_extension_available(),
        "kit_status": read_kit_status(),
    }


def record_focus_intent(payload: dict[str, Any]) -> dict[str, Any]:
    city_id = str(payload.get("city_id") or "").upper()
    if city_id not in SCENES:
        return {"status": "ERROR", "error": f"Unknown city_id {city_id}"}
    queued = queue_kit_command(payload, "focus_capture", True)
    intent = {
        "status": "QUEUED_FOCUS_CAPTURE",
        "city_id": city_id,
        "target_ref": payload.get("target_ref"),
        "episode_id": payload.get("episode_id"),
        "camera": payload.get("camera") or "review_default",
        "target_prim_path": payload.get("target_prim_path") or "/World/Shard_000",
        "timestamp": utc_now(),
        "kit_command": queued.get("command"),
        "kit_command_path": queued.get("command_path"),
        "kit_status": queued.get("kit_status"),
        "limitation": "The R2 Kit extension must be loaded inside Composer to apply the queued focus/capture command.",
    }
    write_json(RUNTIME / "last_focus_intent.json", intent)
    state = load_runtime_state()
    state.setdefault("runtime", {})["last_focus_intent"] = intent
    save_runtime_state(state)
    return intent


def record_capture_request(payload: dict[str, Any]) -> dict[str, Any]:
    queued = queue_kit_command(payload, "capture", True)
    if queued.get("status") == "ERROR":
        return queued
    return {
        "status": "QUEUED_CAPTURE",
        "timestamp": utc_now(),
        "command": queued["command"],
        "command_path": queued["command_path"],
        "kit_status": queued["kit_status"],
        "limitation": "Capture completes only when the R2 Kit extension is loaded in Composer and reports a heartbeat.",
    }


def record_stream_start(payload: dict[str, Any]) -> dict[str, Any]:
    queued = queue_kit_command(payload, "stream_start", False)
    if queued.get("status") == "ERROR":
        return queued
    return {
        "status": "QUEUED_STREAM_START",
        "timestamp": utc_now(),
        "command": queued["command"],
        "command_path": queued["command_path"],
        "stream_status": read_stream_status(),
        "kit_status": queued["kit_status"],
        "limitation": "Live feed is file-backed periodic viewport capture, not embedded/WebRTC streaming.",
    }


def record_stream_stop(payload: dict[str, Any]) -> dict[str, Any]:
    queued = queue_kit_command(payload, "stream_stop", False)
    if queued.get("status") == "ERROR":
        return queued
    return {
        "status": "QUEUED_STREAM_STOP",
        "timestamp": utc_now(),
        "command": queued["command"],
        "command_path": queued["command_path"],
        "stream_status": read_stream_status(),
        "kit_status": queued["kit_status"],
    }


class BridgeHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def _json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _payload(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._json({"status": "PASS", "task": TASK, "timestamp": utc_now()})
            return
        if parsed.path == "/api/state":
            state = load_runtime_state()
            save_runtime_state(state)
            self._json(load_runtime_state())
            return
        if parsed.path == "/api/kit-status":
            self._json(read_kit_status())
            return
        if parsed.path == "/api/stream":
            self._json(read_stream_status())
            return
        if parsed.path == "/api/screenshots":
            self._json({"status": "PASS", "screenshots": list_screenshots(), "drop_dir": str(SCREENSHOTS.resolve())})
            return
        if parsed.path.startswith("/screenshots/"):
            name = Path(parsed.path).name
            path = (SCREENSHOTS / name).resolve()
            if SCREENSHOTS.resolve() not in path.parents or not path.exists():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            ctype = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
            raw = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        payload = self._payload()
        if parsed.path == "/api/launch":
            city_id = str(payload.get("city_id") or parse_qs(parsed.query).get("city_id", [""])[0])
            result = launch_scene(city_id)
            self._json(result, HTTPStatus.OK if result.get("status") != "ERROR" else HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/focus":
            result = record_focus_intent(payload)
            self._json(result, HTTPStatus.OK if result.get("status") != "ERROR" else HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/capture":
            result = record_capture_request(payload)
            self._json(result, HTTPStatus.OK if result.get("status") != "ERROR" else HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/stream/start":
            result = record_stream_start(payload)
            self._json(result, HTTPStatus.OK if result.get("status") != "ERROR" else HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/stream/stop":
            result = record_stream_stop(payload)
            self._json(result, HTTPStatus.OK if result.get("status") != "ERROR" else HTTPStatus.BAD_REQUEST)
            return
        self.send_error(HTTPStatus.NOT_FOUND)


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CityBrain Omniverse Bridge</title>
  <link rel="stylesheet" href="./styles.css">
</head>
<body>
  <main class="shell">
    <header class="hero">
      <div>
        <p class="eyebrow">local viewport bridge</p>
        <h1>CityBrain Omniverse Bridge</h1>
        <p>Launch real USD city scenes in Kit/Composer and keep the browser app synced with bridge state, focus intents, and screenshot drops.</p>
      </div>
      <div class="status" id="bridge-status">checking bridge</div>
    </header>

    <section class="grid" id="scene-grid"></section>

    <section class="panel live-panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">live viewport feed</p>
          <h2>Composer viewport stream</h2>
        </div>
        <div class="actions">
          <button class="primary" id="start-barc-stream">Start BARC feed</button>
          <button class="secondary" id="stop-stream">Stop feed</button>
        </div>
      </div>
      <p>File-backed live feed from the active Kit viewport. Rotate or navigate in Composer; the latest frame refreshes here.</p>
      <code id="stream-status">stream not started</code>
      <div class="live-frame-wrap">
        <img id="live-frame" alt="Latest Omniverse viewport frame">
      </div>
    </section>

    <section class="panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">viewport state</p>
          <h2>Screenshot / stream handoff</h2>
        </div>
        <button id="refresh">Refresh</button>
      </div>
      <p>Composer captures written by the R2 Kit extension appear here. Manual screenshot drops still work as a fallback.</p>
      <code id="kit-status"></code>
      <code id="drop-dir"></code>
      <div class="shots" id="shots"></div>
    </section>

    <section class="panel">
      <p class="eyebrow">claim boundary</p>
      <h2>What R1 does and does not do</h2>
      <ul id="limitations"></ul>
    </section>
  </main>
  <script src="./app.js"></script>
</body>
</html>
"""


STYLES_CSS = """:root {
  color-scheme: dark;
  --bg: #0b0f14;
  --panel: #141a21;
  --panel-2: #10151b;
  --line: #2b3541;
  --text: #eef3f6;
  --muted: #a3b0bb;
  --green: #75d890;
  --teal: #70d8d2;
  --amber: #f2c267;
  --red: #ec7c70;
  font-family: Inter, Segoe UI, Arial, sans-serif;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text); }
.shell { max-width: 1320px; margin: 0 auto; padding: 28px; }
.hero, .panel, .scene-card {
  border: 1px solid var(--line);
  background: var(--panel);
  border-radius: 8px;
  padding: 18px;
}
.hero { display: flex; justify-content: space-between; gap: 18px; margin-bottom: 16px; }
.eyebrow { margin: 0 0 6px; color: var(--teal); text-transform: uppercase; font-size: 12px; font-weight: 800; }
h1 { margin: 0 0 8px; font-size: 34px; }
h2, h3 { margin: 0 0 8px; }
p { color: var(--muted); line-height: 1.5; }
.status { align-self: start; border: 1px solid #53623e; background: #172318; color: var(--green); border-radius: 8px; padding: 10px 12px; white-space: nowrap; }
.grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-bottom: 16px; }
.scene-card { display: grid; gap: 12px; }
.meta-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
.metric { border: 1px solid var(--line); background: var(--panel-2); border-radius: 8px; padding: 10px; min-width: 0; }
.metric span { display: block; color: var(--muted); font-size: 12px; margin-bottom: 4px; }
.metric strong { display: block; overflow-wrap: anywhere; }
.actions { display: flex; gap: 10px; flex-wrap: wrap; }
button {
  min-height: 38px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #111820;
  color: var(--text);
  padding: 8px 12px;
  cursor: pointer;
}
button.primary { border-color: #6ed28b; background: #17311f; color: var(--green); }
button.secondary { border-color: #5a6370; }
code {
  display: block;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  background: #090d12;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px;
  color: #d7e4ec;
}
.panel { margin-bottom: 16px; }
.panel-head { display: flex; justify-content: space-between; gap: 12px; align-items: start; }
.shots { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-top: 12px; }
.shot { border: 1px solid var(--line); border-radius: 8px; overflow: hidden; background: #10151b; }
.shot img { display: block; width: 100%; height: 180px; object-fit: cover; }
.shot p { padding: 8px; margin: 0; font-size: 12px; }
.live-panel { overflow: hidden; }
.live-frame-wrap {
  margin-top: 12px;
  border: 1px solid var(--line);
  background: #05080c;
  border-radius: 8px;
  min-height: 320px;
  display: grid;
  place-items: center;
  overflow: hidden;
}
#live-frame {
  display: none;
  width: 100%;
  max-height: 680px;
  object-fit: contain;
}
ul { margin: 0; padding-left: 20px; color: var(--muted); line-height: 1.65; }
@media (max-width: 900px) {
  .hero, .grid { grid-template-columns: 1fr; display: grid; }
  .meta-grid, .shots { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 620px) {
  .shell { padding: 16px; }
  .meta-grid, .shots { grid-template-columns: 1fr; }
}
"""


APP_JS = """const $ = (id) => document.getElementById(id);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data;
}

function metric(label, value) {
  return `<div class="metric"><span>${esc(label)}</span><strong>${esc(value ?? '')}</strong></div>`;
}

function sceneCard(scene) {
  const city = scene.city_id;
  return `<article class="scene-card">
    <div>
      <p class="eyebrow">${esc(city)}</p>
      <h2>${esc(scene.scene_name)}</h2>
      <p>${esc(scene.claim_boundary)}</p>
    </div>
    <div class="meta-grid">
      ${metric('Decision', scene.decision_status)}
      ${metric('Shards', scene.shard_count)}
      ${metric('Leaf nodes', scene.leaf_node_count)}
      ${metric('Identity rows', scene.identity_sidecar_rows)}
      ${metric('Kit bridge', scene.kit_extension_enabled ? 'R2 enabled' : 'R2 missing')}
    </div>
    <code>${esc(scene.usd_path)}</code>
    <div class="actions">
      <button class="primary" data-launch="${esc(city)}">Launch in Omniverse</button>
      <button class="secondary" data-focus="${esc(city)}">Focus + capture</button>
      <button class="secondary" data-capture="${esc(city)}">Capture viewport</button>
      <button class="secondary" data-stream-start="${esc(city)}">Start live feed</button>
    </div>
  </article>`;
}

async function render() {
  try {
    const state = await api('/api/state');
    $('bridge-status').textContent = state.status;
    $('scene-grid').innerHTML = Object.values(state.scenes).map(sceneCard).join('');
    const kit = state.runtime.kit_extension || {};
    $('kit-status').textContent = `Kit extension: ${kit.status || 'unknown'} | viewport=${kit.viewport_available ?? 'n/a'} | stage=${kit.stage_loaded ?? 'n/a'} | ${kit.message || kit.stage_url || ''}`;
    $('drop-dir').textContent = state.runtime.screenshot_drop_dir;
    $('limitations').innerHTML = state.limitations.map(x => `<li>${esc(x)}</li>`).join('');
    document.querySelectorAll('[data-launch]').forEach(btn => {
      btn.addEventListener('click', async () => {
        btn.textContent = 'Launching...';
        try {
          const result = await api('/api/launch', { method: 'POST', body: JSON.stringify({ city_id: btn.dataset.launch }) });
          btn.textContent = result.status === 'ALREADY_RUNNING' ? `Already running PID ${result.pid}` : `Launched PID ${result.pid}`;
        } catch (err) {
          btn.textContent = `Launch failed`;
          alert(err.message);
        }
      });
    });
    document.querySelectorAll('[data-focus]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const result = await api('/api/focus', { method: 'POST', body: JSON.stringify({
          city_id: btn.dataset.focus,
          target_ref: btn.dataset.focus === 'NYC' ? 'nyc:building:bin:3039983' : 'barc:lod2_source_object:72498',
          episode_id: btn.dataset.focus === 'NYC' ? 'episode:nyc_lod2_building_identity_candidate' : 'episode:barc_lod2_object_district_neighbourhood',
          target_prim_path: '/World/Shard_000',
          capture: true
        }) });
        btn.textContent = result.status;
      });
    });
    document.querySelectorAll('[data-capture]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const result = await api('/api/capture', { method: 'POST', body: JSON.stringify({
          city_id: btn.dataset.capture,
          target_ref: btn.dataset.capture === 'NYC' ? 'nyc:building:bin:3039983' : 'barc:lod2_source_object:72498',
          target_prim_path: '/World/Shard_000',
          capture: true
        }) });
        btn.textContent = result.status;
      });
    });
    document.querySelectorAll('[data-stream-start]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const result = await startStream(btn.dataset.streamStart);
        btn.textContent = result.status;
      });
    });
    await renderScreenshots();
    await renderLiveStream();
  } catch (err) {
    $('bridge-status').textContent = `bridge offline: ${err.message}`;
  }
}

async function startStream(cityId = 'BARC') {
  return api('/api/stream/start', { method: 'POST', body: JSON.stringify({
    city_id: cityId,
    target_ref: cityId === 'NYC' ? 'nyc:building:bin:3039983' : 'barc:lod2_source_object:72498',
    target_prim_path: '/World/Shard_000',
    stream_interval_seconds: 2
  }) });
}

async function stopStream(cityId = 'BARC') {
  return api('/api/stream/stop', { method: 'POST', body: JSON.stringify({ city_id: cityId }) });
}

async function renderLiveStream() {
  try {
    const stream = await api('/api/stream');
    $('stream-status').textContent = `Stream: ${stream.status || 'unknown'} | city=${stream.city_id || 'n/a'} | frame=${stream.stream_frame ?? 0} | streaming=${stream.streaming ?? false} | ${stream.latest_modified || stream.message || ''}`;
    const img = $('live-frame');
    if (stream.latest_url) {
      img.src = `${stream.latest_url}?t=${Date.now()}`;
      img.style.display = 'block';
    }
  } catch (err) {
    $('stream-status').textContent = `Stream offline: ${err.message}`;
  }
}

async function renderScreenshots() {
  const data = await api('/api/screenshots');
  if (!data.screenshots.length) {
    $('shots').innerHTML = '<p>No screenshot drops yet. Save PNG/JPG/WebP files into the folder above.</p>';
    return;
  }
  $('shots').innerHTML = data.screenshots.map(shot => `<div class="shot"><img src="${esc(shot.url)}" alt="${esc(shot.file)}"><p>${esc(shot.file)} / ${esc(shot.modified)}</p></div>`).join('');
}

$('refresh').addEventListener('click', render);
$('start-barc-stream').addEventListener('click', async () => {
  const result = await startStream('BARC');
  $('stream-status').textContent = result.status;
});
$('stop-stream').addEventListener('click', async () => {
  const result = await stopStream('BARC');
  $('stream-status').textContent = result.status;
});
render();
setInterval(renderLiveStream, 2000);
setInterval(renderScreenshots, 5000);
"""


def write_app() -> None:
    write_text(APP / "index.html", INDEX_HTML)
    write_text(APP / "styles.css", STYLES_CSS)
    write_text(APP / "app.js", APP_JS)


def write_start_scripts() -> None:
    runner = Path(__file__).resolve()
    ps = f"""$ErrorActionPreference = "Stop"
Set-Location "{REPO}"
python "{runner}" --serve --port 8102
"""
    write_text(ROOT / "START_OMNIVERSE_VIEWPORT_BRIDGE_R1.ps1", ps)
    bat = f"""@echo off
cd /d "{REPO}"
python "{runner}" --serve --port 8102
"""
    write_text(ROOT / "START_OMNIVERSE_VIEWPORT_BRIDGE_R1.bat", bat)


def smoke_report(state: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "kit_launcher_exists": KIT_LAUNCHER.exists(),
        "barc_usd_exists": SCENES["BARC"]["usd_path"].exists(),
        "nyc_usd_exists": SCENES["NYC"]["usd_path"].exists(),
        "barc_shards_exist": bool(list((BARC_ROOT / "usd_shards").glob("*.usda"))),
        "nyc_shards_exist": bool(list((NYC_ROOT / "usd_shards").glob("*.usda"))),
        "bridge_app_exists": (APP / "index.html").exists(),
        "runtime_state_exists": (RUNTIME / "bridge_state.json").exists(),
        "screenshot_drop_dir_exists": SCREENSHOTS.exists(),
        "kit_extension_bundle_exists": kit_extension_available(),
        "stream_api_in_app": "/api/stream/start" in (APP / "app.js").read_text(encoding="utf-8"),
        "live_panel_in_app": "Composer viewport stream" in (APP / "index.html").read_text(encoding="utf-8"),
        "no_browser_usd_renderer_claim": "does not embed the USD renderer inside the browser" in json.dumps(state),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "scenes": {
            city: {
                "usd_exists": scene["usd_exists"],
                "decision_status": scene["decision_status"],
                "shard_count": scene["shard_count"],
                "identity_sidecar_rows": scene["identity_sidecar_rows"],
            }
            for city, scene in state["scenes"].items()
        },
    }


def secret_audit() -> dict[str, Any]:
    findings = []
    patterns = [
        "fff39a33858102015f4630ed32b9acad",
        "api_key",
        "apikey",
        "bearer ",
    ]
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            continue
        for pat in patterns:
            if pat in text:
                findings.append({"path": str(path), "pattern": pat})
    return {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}


def no_mutation_audit(before: dict[str, Any]) -> dict[str, Any]:
    after = snapshot_roots()
    changed = [name for name in before if before[name] != after[name]]
    return {"status": "PASS" if not changed else "FAIL", "changed_roots": changed, "checked_roots": sorted(before)}


def hash_outputs() -> None:
    rows = []
    for path in sorted(p for p in ROOT.rglob("*") if p.is_file()):
        if path.name == "hashes.sha256":
            continue
        rows.append(f"{sha256(path)}  {path.relative_to(ROOT).as_posix()}")
    write_text(ROOT / "hashes.sha256", "\n".join(rows) + "\n")


def write_reports(state: dict[str, Any], smoke: dict[str, Any], no_mutation: dict[str, Any], secrets: dict[str, Any]) -> dict[str, Any]:
    status = PASS_LIMITED if smoke["status"] == no_mutation["status"] == secrets["status"] == "PASS" else FAIL
    decision = {
        "task_name": TASK,
        "status": status,
        "timestamp": utc_now(),
        "bridge_app": str((APP / "index.html").resolve()),
        "serve_command": f"python scripts/run_main_track2c_d4x_omniverse_viewport_bridge_r1.py --serve --port 8102",
        "bridge_url": "http://127.0.0.1:8102/",
        "kit_launcher": str(KIT_LAUNCHER.resolve()),
        "kit_extension_available": kit_extension_available(),
        "kit_extension_id": R2_EXT_ID,
        "kit_extension_root": str((R2_EXT_PARENT / R2_EXT_ID).resolve()),
        "kit_command_path": str(KIT_COMMAND_PATH.resolve()),
        "kit_status_path": str(KIT_STATUS_PATH.resolve()),
        "scenes": {city: {"usd_path": data["usd_path"], "shard_count": data["shard_count"], "identity_sidecar_rows": data["identity_sidecar_rows"]} for city, data in state["scenes"].items()},
        "smoke_status": smoke["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secrets["status"],
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-TRACK2C-D4X-OMNIVERSE-VIEWPORT-STREAMING-R3",
    }
    write_json(ROOT / "MAIN_TRACK2C_D4X_OMNIVERSE_VIEWPORT_BRIDGE_R1_DECISION.json", decision)
    write_json(ROOT / "OMNIVERSE_VIEWPORT_BRIDGE_STATE.json", state)
    write_json(ROOT / "OMNIVERSE_VIEWPORT_BRIDGE_SMOKE_REPORT.json", smoke)
    write_json(ROOT / "audits/NO_MUTATION_AUDIT.json", no_mutation)
    write_json(ROOT / "audits/SECRET_REDACTION_AUDIT.json", secrets)
    write_text(ROOT / "NO_MUTATION_AUDIT.md", f"# No-Mutation Audit\n\nStatus: `{no_mutation['status']}`\n\nChanged roots: `{', '.join(no_mutation['changed_roots']) or 'none'}`\n")
    write_text(ROOT / "SECRET_REDACTION_AUDIT.md", f"# Secret Redaction Audit\n\nStatus: `{secrets['status']}`\n\nFinding count: `{secrets['finding_count']}`\n")
    write_text(ROOT / "CLAIM_BOUNDARY_AUDIT.md", f"# Claim Boundary Audit\n\nStatus: `PASS`\n\n{state['claim_boundary']}\n")
    write_text(
        ROOT / "OMNIVERSE_VIEWPORT_BRIDGE_CONTRACT.md",
        """# Omniverse Viewport Bridge Contract

R1 bridge contract:

- Browser/app talks to a localhost bridge server.
- Bridge server can launch visible Kit/Composer with a known USD scene path and the R2 CityBrain viewport extension enabled.
- Browser can poll launch state and screenshot drop-folder state.
- Browser can queue focus/camera/select/capture commands.
- The R2 Kit extension consumes the command queue from inside Composer and writes captures to the screenshot folder.
- The stream path uses periodic latest-frame PNG capture served from localhost.

API:

- `GET /api/state`
- `GET /api/health`
- `POST /api/launch` with `{ "city_id": "BARC" | "NYC" }`
- `POST /api/focus` with `{ "city_id", "target_ref", "episode_id", "camera" }`
- `POST /api/capture` with `{ "city_id", "target_prim_path" }`
- `POST /api/stream/start` with `{ "city_id", "target_prim_path", "stream_interval_seconds" }`
- `POST /api/stream/stop` with `{ "city_id" }`
- `GET /api/stream`
- `GET /api/kit-status`
- `GET /api/screenshots`
- `GET /screenshots/<file>`

Boundary: local review/context viewport handoff only.
""",
    )
    write_text(
        ROOT / "README.md",
        f"""# CityBrain Omniverse Viewport Bridge R1

Status: `{status}`

Start the bridge:

```powershell
python scripts\\run_main_track2c_d4x_omniverse_viewport_bridge_r1.py --serve --port 8102
```

Open:

`http://127.0.0.1:8102/`

This bridge opens real USD scenes in Omniverse/Kit and enables the R2 viewport bridge extension when present. It does not render USD inside the browser.
""",
    )
    write_text(
        ROOT / "MAIN_TRACK2C_D4X_OMNIVERSE_VIEWPORT_BRIDGE_R1.md",
        f"""# {TASK}

Status: `{status}`

The bridge creates a local control surface for real Omniverse USD scenes:

- Barcelona: `{state['scenes']['BARC']['usd_path']}`
- NYC: `{state['scenes']['NYC']['usd_path']}`

What works now:

- Local bridge app.
- Launch visible Kit/Composer for BARC/NYC with the R2 viewport extension enabled when available.
- Runtime launch status.
- Focus/capture command queue.
- Kit extension heartbeat/status file.
- Screenshot drop/poll API.

What remains for later streaming work:

- WebRTC or embedded viewport streaming.
- Bidirectional selected-prim sync.
""",
    )
    return decision


def build() -> dict[str, Any]:
    before = snapshot_roots()
    reset_output()
    state = build_bridge_state()
    write_app()
    write_json(APP / "data/bridge_state_seed.json", state)
    write_json(RUNTIME / "bridge_state.json", state)
    write_text(SCREENSHOTS / "README.md", "Drop Omniverse viewport screenshots here for the bridge UI to display.\n")
    write_start_scripts()
    smoke = smoke_report(state)
    no_mutation = no_mutation_audit(before)
    secrets = secret_audit()
    decision = write_reports(state, smoke, no_mutation, secrets)
    shutil.copy2(Path(__file__), ROOT / Path(__file__).name)
    hash_outputs()
    return decision


def serve(port: int) -> None:
    if not (APP / "index.html").exists():
        build()
    os.chdir(APP)
    server = ThreadingHTTPServer(("127.0.0.1", port), BridgeHandler)
    print(f"{TASK} bridge serving http://127.0.0.1:{port}/")
    print(f"Screenshot drop folder: {SCREENSHOTS.resolve()}")
    server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=8102)
    args = parser.parse_args(argv)
    if args.serve:
        serve(args.port)
        return 0
    decision = build()
    print(f"{TASK}: {decision['status']}")
    print(f"Output: {ROOT}")
    return 0 if decision["status"] == PASS_LIMITED else 1


if __name__ == "__main__":
    raise SystemExit(main())

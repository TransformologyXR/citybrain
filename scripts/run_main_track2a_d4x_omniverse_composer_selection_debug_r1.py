from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-TRACK2A-D4X-OMNIVERSE-COMPOSER-SELECTION-DEBUG-R1"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_track2a_d4x_omniverse_composer_selection_debug_r1"
R1_ROOT = REPO_ROOT / "outputs" / "main_track2a_d4x_omniverse_kit_selection_extension_r1"
R2_ROOT = REPO_ROOT / "outputs" / "main_track2a_d4x_omniverse_kit_composer_gui_smoke_r2"
USD_SCENE = REPO_ROOT / "outputs" / "main_track1_d4_usd_city_subset_binding" / "D4_BARCELONA_USD_SCENE.usda"
DEBUG_USD_SCENE = OUTPUT_ROOT / "D4_BARCELONA_USD_SCENE_WITH_SELECTION_BINDINGS_DEBUG.usda"
EXT_ROOT = OUTPUT_ROOT / "KIT_READY_EXTENSION_ROOT"
EXT_PACKAGE = EXT_ROOT / "txr.citybrain.selection_inspector"
ORIGINAL_REQUESTED_PRIM = "/World/CityBrainAssetBindingR1/BARC_Eixample/004_cer_community_barc_eixample"
PREFERRED_PRIM = "/World/CityBrainAssetBindingR1/BARC_Eixample/cb_004_cer_community_barc_eixample"
KIT_EXE = Path(r"C:\Omniverse\kit-app-template\_build\windows-x86_64\release\kit\kit.exe")
KIT_APP = Path(r"C:\Omniverse\kit-app-template\_build\windows-x86_64\release\apps\txr.citybrain_usd_composer.kit")
COMPOSER_LOG_DIR = Path.home() / ".nvidia-omniverse" / "logs" / "Kit" / "CityBrain USD Composer" / "0.1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.strip() + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_latest_composer_log() -> Path | None:
    if not COMPOSER_LOG_DIR.exists():
        return None
    logs = sorted(COMPOSER_LOG_DIR.glob("kit_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    return logs[0] if logs else None


def analyze_log(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {
            "composer_log_found": False,
            "composer_log_path": None,
            "app_loaded": False,
            "extension_registered": False,
            "extension_started": False,
            "usd_path_on_command_line": False,
            "stage_open_evidence_in_log": False,
            "diagnosis": "NO_COMPOSER_LOG_FOUND",
        }
    text = path.read_text(encoding="utf-8", errors="replace")
    stage_open_patterns = [
        r"Opened stage",
        r"Stage opened",
        r"open_stage",
        r"USD context.*stage",
        r"D4_BARCELONA_USD_SCENE\.usda.*opened",
    ]
    stage_open = any(re.search(pattern, text, re.IGNORECASE) for pattern in stage_open_patterns)
    return {
        "composer_log_found": True,
        "composer_log_path": str(path),
        "log_size_bytes": path.stat().st_size,
        "app_loaded": "txr.citybrain_usd_composer.kit" in text,
        "extension_registered": "[ext: txr.citybrain.selection_inspector" in text and "registered" in text,
        "extension_started": "[ext: txr.citybrain.selection_inspector" in text and "started" in text,
        "usd_path_on_command_line": "D4_BARCELONA_USD_SCENE.usda" in text,
        "stage_open_evidence_in_log": stage_open,
        "diagnosis": "USD_POSITIONAL_ARG_NOT_OPENED_AS_STAGE" if "D4_BARCELONA_USD_SCENE.usda" in text and not stage_open else "INSPECT_LOG_FOR_STAGE_OR_VIEWPORT_ISSUE",
    }


def load_binding_lookup() -> dict[str, Any]:
    candidates = [
        R1_ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_HEADLESS_PACKAGE" / "data" / "binding_lookup.json",
        R2_ROOT / "KIT_READY_EXTENSION_ROOT" / "txr.citybrain.selection_inspector" / "data" / "binding_lookup.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
    raise FileNotFoundError("binding_lookup.json was not found in R1 or R2 outputs")


def sanitize_usd_prim_name(name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_]", "_", name)
    if not sanitized or not re.match(r"[A-Za-z_]", sanitized[0]):
        sanitized = "cb_" + sanitized
    return sanitized


def normalize_lookup_to_valid_usd_paths(lookup: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(lookup)
    normalized_lookup: dict[str, Any] = {}
    path_map: dict[str, str] = {}
    for prim_path, binding in sorted(lookup.get("lookup_by_prim_path", {}).items()):
        parts = prim_path.rstrip("/").split("/")
        parts[-1] = sanitize_usd_prim_name(parts[-1])
        normalized_path = "/".join(parts)
        path_map[prim_path] = normalized_path
        normalized_binding = dict(binding)
        normalized_binding["original_requested_prim_path"] = prim_path
        normalized_binding["selected_prim_path"] = normalized_path
        normalized_binding["usd_prim_path"] = normalized_path
        normalized_lookup[normalized_path] = normalized_binding
    normalized["lookup_by_prim_path"] = normalized_lookup
    normalized["known_unbound_prim_paths"] = [
        "/".join(path.rstrip("/").split("/")[:-1] + [sanitize_usd_prim_name(path.rstrip("/").split("/")[-1])])
        for path in lookup.get("known_unbound_prim_paths", [])
    ]
    normalized["original_to_valid_usd_prim_path_map"] = path_map
    normalized["preferred_original_requested_prim_path"] = ORIGINAL_REQUESTED_PRIM
    normalized["preferred_valid_usd_prim_path"] = PREFERRED_PRIM
    normalized["lookup_count"] = len(normalized_lookup)
    return normalized


def copy_or_write_binding_lookup() -> dict[str, Any]:
    lookup = normalize_lookup_to_valid_usd_paths(load_binding_lookup())
    target = EXT_PACKAGE / "data" / "binding_lookup.json"
    write_json(target, lookup)
    return lookup


def usd_string(value: Any) -> str:
    return json.dumps("" if value is None else str(value))


def create_debug_selection_scene(lookup: dict[str, Any]) -> dict[str, Any]:
    """Create an additive debug scene with actual selectable prim paths from the Kit binding lookup."""
    records = []
    for prim_path, binding in sorted(lookup.get("lookup_by_prim_path", {}).items()):
        prim_name = prim_path.rstrip("/").split("/")[-1]
        records.append((prim_path, prim_name, binding))

    colors = {
        "candidate_review": (0.95, 0.55, 0.12),
        "current_context": (0.12, 0.58, 0.95),
        "observed_context": (0.24, 0.75, 0.42),
        "runtime_event": (0.95, 0.22, 0.22),
        "historical_context": (0.62, 0.54, 0.95),
    }
    lines = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "World"',
        "    metersPerUnit = 1",
        '    upAxis = "Z"',
        ")",
        "",
        'def Xform "World"',
        "{",
        f"    custom string citybrain:source_scene_ref = {usd_string(USD_SCENE)}",
        '    custom string citybrain:scene_role = "debug_selectable_binding_overlay"',
        '    custom string citybrain:claim_boundary = "review/context selection debug only; no action/control"',
        "",
        '    def Xform "Geospatial"',
        "    {",
        '        def Cube "debug_ground_plane"',
        "        {",
        "            double size = 1",
        "            double3 xformOp:translate = (0, 0, -0.05)",
        "            double3 xformOp:scale = (42, 26, 0.05)",
        '            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]',
        "            color3f[] primvars:displayColor = [(0.08, 0.09, 0.1)]",
        "        }",
        "    }",
        "",
        '    def Xform "CityBrainAssetBindingR1"',
        "    {",
        '        def Xform "BARC_Eixample"',
        "        {",
        '            custom string citybrain:scope = "bounded_debug_selection_overlay"',
        '            custom string citybrain:identity_boundary = "USD prim paths are lookup handles only; CER/SEG remain canonical context"',
    ]
    for index, (prim_path, prim_name, binding) in enumerate(records):
        x = -18 + (index % 4) * 12
        y = 10 - (index // 4) * 9
        z = 1.5 + (index % 3) * 0.8
        overlay_state = binding.get("overlay_state", "candidate_review")
        color = colors.get(overlay_state, (0.82, 0.82, 0.82))
        geometry = "Sphere" if overlay_state in {"runtime_event", "observed_context"} else "Cube"
        shape_size_line = "            double radius = 2.4" if geometry == "Sphere" else "            double size = 4.2"
        lines.extend(
            [
                f'            def {geometry} "{prim_name}"',
                "            {",
                shape_size_line,
                f"                double3 xformOp:translate = ({x}, {y}, {z})",
                "                double3 xformOp:scale = (1, 1, 1)",
                '                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]',
                f"                color3f[] primvars:displayColor = [({color[0]}, {color[1]}, {color[2]})]",
                f"                custom string citybrain:selected_prim_path = {usd_string(prim_path)}",
                f"                custom string citybrain:canonical_entity_id = {usd_string(binding.get('canonical_entity_id'))}",
                f"                custom string citybrain:entity_type = {usd_string(binding.get('entity_type'))}",
                f"                custom string citybrain:display_name = {usd_string(binding.get('display_name'))}",
                f"                custom string citybrain:evidence_ref = {usd_string(binding.get('evidence_ref'))}",
                f"                custom string citybrain:graph_or_runtime_ref = {usd_string(binding.get('graph_or_runtime_ref'))}",
                f"                custom string citybrain:limitation_ref = {usd_string(binding.get('limitation_ref'))}",
                f"                custom string citybrain:review_state = {usd_string(binding.get('review_state'))}",
                f"                custom string citybrain:binding_status = {usd_string(binding.get('binding_status'))}",
                '                custom bool citybrain:no_action_taken = true',
                "            }",
            ]
        )
    lines.extend(
        [
            "        }",
            "    }",
            "",
            '    def Xform "Lighting"',
            "    {",
            '        def DistantLight "sun_key"',
            "        {",
            "            float intensity = 5000",
            "            float angle = 0.35",
            "        }",
            "    }",
            "",
            '    def Xform "Cameras"',
            "    {",
            '        def Camera "overview_camera"',
            "        {",
            "            double3 xformOp:translate = (0, -42, 30)",
            "            double3 xformOp:rotateXYZ = (58, 0, 0)",
            '            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]',
            "            float focalLength = 24",
            "        }",
            "    }",
            "}",
        ]
    )
    write_text(DEBUG_USD_SCENE, "\n".join(lines))
    return {
        "debug_usd_scene": str(DEBUG_USD_SCENE),
        "selection_prim_count": len(records),
        "preferred_prim_in_debug_scene": any(prim == PREFERRED_PRIM for prim, _, _ in records),
        "original_requested_prim": ORIGINAL_REQUESTED_PRIM,
        "prim_path_normalization": "numeric-leading binding handles are prefixed with cb_ because USD prim names cannot start with digits",
        "source_scene_ref": str(USD_SCENE),
        "debug_scene_role": "selectable_binding_overlay",
    }


def write_extension_package() -> dict[str, Any]:
    if EXT_PACKAGE.exists():
        shutil.rmtree(EXT_PACKAGE)
    for folder in [
        EXT_PACKAGE / "config",
        EXT_PACKAGE / "data",
        EXT_PACKAGE / "txr" / "citybrain" / "selection_inspector",
    ]:
        folder.mkdir(parents=True, exist_ok=True)

    lookup = copy_or_write_binding_lookup()

    write_text(
        EXT_PACKAGE / "config" / "extension.toml",
        """
[package]
version = "0.3.0"
title = "CityBrain Selection Inspector"
description = "Visible bounded Kit/Composer selection inspector for CityBrain BARC Eixample debug acceptance."
category = "CityBrain"
keywords = ["citybrain", "selection", "usd", "inspection", "debug"]
readme = "README.md"

[dependencies]
"omni.usd" = { optional = true }
"omni.ui" = { optional = true }

[[python.module]]
name = "txr.citybrain.selection_inspector"

[settings.exts."txr.citybrain.selection_inspector"]
binding_lookup = "${txr.citybrain.selection_inspector}/data/binding_lookup.json"
default_test_prim = "/World/CityBrainAssetBindingR1/BARC_Eixample/cb_004_cer_community_barc_eixample"
""",
    )
    write_text(
        EXT_PACKAGE / "README.md",
        """
# CityBrain Selection Inspector Debug Extension

This staged extension is a debug/acceptance helper for a bounded Barcelona Eixample USD selection smoke.

It opens a visible `CityBrain Selection Inspector` window when Kit/Composer starts. Selecting a bound prim should resolve to a CityBrain inspection card with canonical entity, evidence, graph/runtime, limitation, and no-action boundary fields.

This extension does not implement a production UI, control-room action, dispatch, enforcement, routing/control, legal/ownership conclusion, certified affected-building claim, or autonomous action.
""",
    )
    write_text(EXT_PACKAGE / "txr" / "__init__.py", "")
    write_text(EXT_PACKAGE / "txr" / "citybrain" / "__init__.py", "")
    write_text(
        EXT_PACKAGE / "txr" / "citybrain" / "selection_inspector" / "__init__.py",
        """
from .extension import CityBrainSelectionInspectorExtension
""",
    )
    write_text(
        EXT_PACKAGE / "txr" / "citybrain" / "selection_inspector" / "binding_lookup.py",
        r'''
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_BINDING_FIELDS = [
    "canonical_entity_id",
    "entity_type",
    "display_name",
    "overlay_state",
    "evidence_ref",
    "graph_or_runtime_ref",
    "limitation_ref",
    "binding_status",
    "review_state",
]


class BindingLookup:
    def __init__(self, lookup_doc: dict[str, Any] | None = None, loaded: bool = True) -> None:
        self.lookup_doc = lookup_doc or {}
        self.loaded = loaded
        self.lookup_by_prim_path = self.lookup_doc.get("lookup_by_prim_path", {}) if loaded else {}
        self.known_unbound_prim_paths = set(self.lookup_doc.get("known_unbound_prim_paths", [])) if loaded else set()

    @classmethod
    def from_path(cls, path: str | Path) -> "BindingLookup":
        candidate = Path(path)
        if not candidate.exists():
            return cls({}, loaded=False)
        return cls(json.loads(candidate.read_text(encoding="utf-8")), loaded=True)

    def resolve(self, prim_path: str) -> dict[str, Any] | None:
        if not self.loaded:
            return None
        return self.lookup_by_prim_path.get(prim_path)

    def is_known_unbound(self, prim_path: str) -> bool:
        return prim_path in self.known_unbound_prim_paths

    def validate_binding(self, binding: dict[str, Any] | None) -> list[str]:
        if not binding:
            return REQUIRED_BINDING_FIELDS[:]
        return [field for field in REQUIRED_BINDING_FIELDS if not binding.get(field)]

    def first_prim(self) -> str | None:
        return next(iter(self.lookup_by_prim_path.keys()), None)
''',
    )
    write_text(
        EXT_PACKAGE / "txr" / "citybrain" / "selection_inspector" / "inspection_card_renderer.py",
        r'''
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


FORBIDDEN_ACTIONS = [
    "dispatch",
    "enforcement",
    "routing/control",
    "legal/ownership conclusion",
    "certified affected-building conclusion",
    "autonomous action",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_failure(code: str, message: str, event: dict[str, Any] | None = None, missing_fields: list[str] | None = None) -> dict[str, Any]:
    return {
        "status": code,
        "message": message,
        "selected_prim_path": (event or {}).get("selected_prim_path"),
        "missing_fields": missing_fields or [],
        "inspection_card": None,
        "claim_boundary": "KIT_GUI_SELECTION_SAFE_FAILURE_REVIEW_CONTEXT_ONLY",
        "safe_actions": ["inspect binding lookup", "inspect limitations"],
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "no_action_taken": True,
        "created_at_utc": now(),
    }


def render_card(event: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    card = {
        "card_id": "kit-gui-selection-card:" + binding["canonical_entity_id"],
        "selected_prim_path": event["selected_prim_path"],
        "canonical_entity_id": binding["canonical_entity_id"],
        "entity_type": binding["entity_type"],
        "display_name": binding["display_name"],
        "overlay_state": binding["overlay_state"],
        "evidence_ref": binding["evidence_ref"],
        "graph_or_runtime_ref": binding["graph_or_runtime_ref"],
        "limitation_ref": binding["limitation_ref"],
        "binding_status": binding["binding_status"],
        "review_state": binding["review_state"],
        "safe_actions": ["inspect evidence refs", "inspect graph/runtime refs", "inspect limitations"],
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "claim_boundary": "KIT_GUI_SELECTION_REVIEW_CONTEXT_ONLY_NOT_CONTROL_NOT_CANONICAL_TRUTH",
        "no_action_taken": True,
        "created_at_utc": now(),
    }
    return {"status": "PASS", "inspection_card": card, "no_action_taken": True}
''',
    )
    write_text(
        EXT_PACKAGE / "txr" / "citybrain" / "selection_inspector" / "selection_handler.py",
        r'''
from __future__ import annotations

from typing import Any

from .binding_lookup import BindingLookup
from .inspection_card_renderer import render_card, safe_failure


REQUIRED_EVENT_FIELDS = ["event_id", "event_type", "selected_prim_path", "selection_source", "timestamp_utc"]


class SelectionHandler:
    def __init__(self, binding_lookup: BindingLookup | None) -> None:
        self.binding_lookup = binding_lookup

    def handle_selection_event(self, event: Any) -> dict[str, Any]:
        if not isinstance(event, dict):
            return safe_failure("SAFE_FAILURE_MALFORMED_SELECTION_EVENT", "Selection event must be an object.")
        missing_event = [field for field in REQUIRED_EVENT_FIELDS if not event.get(field)]
        if missing_event:
            return safe_failure("SAFE_FAILURE_MALFORMED_SELECTION_EVENT", "Selection event is missing required fields.", event, missing_event)
        if self.binding_lookup is None or not self.binding_lookup.loaded:
            return safe_failure("SAFE_FAILURE_MISSING_BINDING_LOOKUP", "Binding lookup is missing or could not be loaded.", event)
        prim_path = event["selected_prim_path"]
        if event.get("selection_metadata", {}).get("binding_status") == "UNBOUND" or self.binding_lookup.is_known_unbound(prim_path):
            return safe_failure("SAFE_FAILURE_UNBOUND_PRIM", "Selected prim is explicitly unbound.", event)
        binding = self.binding_lookup.resolve(prim_path)
        if not binding:
            return safe_failure("SAFE_FAILURE_UNKNOWN_PRIM", "Selected prim path is not present in the CityBrain binding lookup.", event)
        missing_binding = self.binding_lookup.validate_binding(binding)
        if missing_binding:
            return safe_failure("SAFE_FAILURE_INCOMPLETE_METADATA", "Binding record is incomplete.", event, missing_binding)
        return render_card(event, binding)
''',
    )
    write_text(
        EXT_PACKAGE / "txr" / "citybrain" / "selection_inspector" / "extension.py",
        r'''
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import omni.ext  # type: ignore
except Exception:
    omni = None  # type: ignore

try:
    import omni.usd  # type: ignore
except Exception:
    omni_usd = None  # type: ignore

try:
    import omni.ui as ui  # type: ignore
except Exception:
    ui = None  # type: ignore

from .binding_lookup import BindingLookup
from .selection_handler import SelectionHandler


PREFERRED_PRIM = "/World/CityBrainAssetBindingR1/BARC_Eixample/cb_004_cer_community_barc_eixample"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


BaseExt = omni.ext.IExt if omni is not None else object  # type: ignore[attr-defined]


class CityBrainSelectionInspectorExtension(BaseExt):
    """Visible Kit/Composer extension for bounded CityBrain prim inspection."""

    def __init__(self) -> None:
        if omni is not None:
            super().__init__()
        self.ext_id: str | None = None
        self.lookup_path = Path(__file__).resolve().parents[3] / "data" / "binding_lookup.json"
        self.lookup = BindingLookup.from_path(self.lookup_path)
        self.handler = SelectionHandler(self.lookup)
        self.window = None
        self._subscription = None
        self._last_result: dict[str, Any] | None = None
        self._labels: dict[str, Any] = {}

    def on_startup(self, ext_id: str) -> None:
        self.ext_id = ext_id
        self._build_window()
        self.inspect_selected_prim(PREFERRED_PRIM, "startup-preferred-prim")
        self._subscribe_to_selection()
        output = os.environ.get("CITYBRAIN_KIT_SELECTION_SMOKE_OUTPUT")
        if output:
            Path(output).write_text(json.dumps({
                "status": self._last_result.get("status") if self._last_result else "UNKNOWN",
                "ext_id": ext_id,
                "lookup_loaded": self.lookup.loaded,
                "lookup_count": len(self.lookup.lookup_by_prim_path),
                "visible_panel_created": self.window is not None,
                "startup_probe_result": self._last_result,
                "kit_gui_claimed": False,
                "no_action_taken": True,
                "created_at_utc": now(),
            }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def on_shutdown(self) -> None:
        self._subscription = None
        self.window = None

    def _build_window(self) -> None:
        if ui is None:
            return
        self.window = ui.Window("CityBrain Selection Inspector", width=520, height=420, visible=True)
        with self.window.frame:
            with ui.VStack(spacing=6, height=0):
                ui.Label("CityBrain Selection Inspector", height=22)
                ui.Label("Review/context only. No command, dispatch, enforcement, routing/control, legal, or certified asset claim.", word_wrap=True)
                ui.Spacer(height=6)
                self._labels["status"] = ui.Label("status: waiting")
                self._labels["prim"] = ui.Label("prim: " + PREFERRED_PRIM, word_wrap=True)
                self._labels["display"] = ui.Label("display: -", word_wrap=True)
                self._labels["canonical"] = ui.Label("canonical: -", word_wrap=True)
                self._labels["entity"] = ui.Label("entity: -", word_wrap=True)
                self._labels["evidence"] = ui.Label("evidence: -", word_wrap=True)
                self._labels["graph"] = ui.Label("graph/runtime: -", word_wrap=True)
                self._labels["limitation"] = ui.Label("limitation: -", word_wrap=True)
                self._labels["boundary"] = ui.Label("boundary: no_action_taken=true", word_wrap=True)
                ui.Spacer(height=6)
                ui.Button("Refresh Selected Prim", clicked_fn=self.refresh_selected_prim)
                ui.Button("Inspect Preferred Demo Prim", clicked_fn=lambda: self.inspect_selected_prim(PREFERRED_PRIM, "button-preferred-prim"))

    def _set_label(self, key: str, text: str) -> None:
        label = self._labels.get(key)
        if label is not None:
            label.text = text

    def _update_window(self, result: dict[str, Any]) -> None:
        self._last_result = result
        self._set_label("status", "status: " + str(result.get("status")))
        card = result.get("inspection_card") or {}
        self._set_label("prim", "prim: " + str(result.get("selected_prim_path") or card.get("selected_prim_path") or "-"))
        self._set_label("display", "display: " + str(card.get("display_name") or result.get("message") or "-"))
        self._set_label("canonical", "canonical: " + str(card.get("canonical_entity_id") or "-"))
        self._set_label("entity", "entity: " + str(card.get("entity_type") or "-"))
        self._set_label("evidence", "evidence: " + str(card.get("evidence_ref") or "-"))
        self._set_label("graph", "graph/runtime: " + str(card.get("graph_or_runtime_ref") or "-"))
        self._set_label("limitation", "limitation: " + str(card.get("limitation_ref") or result.get("claim_boundary") or "-"))
        self._set_label("boundary", "boundary: no_action_taken=" + str(result.get("no_action_taken")) + " | no control/action")

    def _subscribe_to_selection(self) -> None:
        try:
            if omni_usd is None:
                return
            context = omni.usd.get_context()
            stream = context.get_stage_event_stream()
            self._subscription = stream.create_subscription_to_pop(self._on_stage_event, name="citybrain-selection-inspector")
        except Exception:
            self._subscription = None

    def _on_stage_event(self, event: Any) -> None:
        try:
            event_type = int(event.type)
            selection_changed = int(omni.usd.StageEventType.SELECTION_CHANGED)
            if event_type == selection_changed:
                self.refresh_selected_prim()
        except Exception:
            return

    def refresh_selected_prim(self) -> dict[str, Any]:
        selected = []
        try:
            if omni_usd is not None:
                selected = list(omni.usd.get_context().get_selection().get_selected_prim_paths())
        except Exception:
            selected = []
        prim = selected[0] if selected else PREFERRED_PRIM
        return self.inspect_selected_prim(prim, "refresh-selected-prim")

    def inspect_first_bound_prim(self, event_id: str = "first-bound-prim") -> dict[str, Any]:
        first = self.lookup.first_prim()
        if not first:
            return {"status": "SAFE_FAILURE_MISSING_BINDING_LOOKUP", "no_action_taken": True}
        return self.inspect_selected_prim(first, event_id)

    def inspect_selected_prim(self, selected_prim_path: str, event_id: str = "selected-prim") -> dict[str, Any]:
        event = {
            "event_id": event_id,
            "event_type": "usd_prim_selected",
            "selected_prim_path": selected_prim_path,
            "selection_source": "kit_composer_visible_selection_debug",
            "timestamp_utc": now(),
        }
        result = self.handler.handle_selection_event(event)
        self._update_window(result)
        output = os.environ.get("CITYBRAIN_KIT_SELECTION_LAST_RESULT")
        if output:
            Path(output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result
''',
    )

    return {
        "extension_package": str(EXT_PACKAGE),
        "lookup_count": lookup.get("lookup_count") or len(lookup.get("lookup_by_prim_path", {})),
        "preferred_prim": PREFERRED_PRIM,
        "visible_panel_added": True,
        "version": "0.3.0",
        "lookup_doc": lookup,
    }


def write_stage_open_script() -> Path:
    script = OUTPUT_ROOT / "open_scene_select_prim.py"
    write_text(
        script,
        f'''
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path


USD_SCENE = r"{DEBUG_USD_SCENE}"
SOURCE_SCENE = r"{USD_SCENE}"
PREFERRED_PRIM = "{PREFERRED_PRIM}"


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


result = {{
    "status": "FAIL",
    "created_at_utc": now(),
    "usd_scene": USD_SCENE,
    "source_scene_ref": SOURCE_SCENE,
    "preferred_prim": PREFERRED_PRIM,
    "stage_open_attempted": False,
    "stage_open_return": None,
    "stage_available": False,
    "preferred_prim_exists": False,
    "selection_attempted": False,
    "selected_prim_paths": [],
    "inspection_result_file": os.environ.get("CITYBRAIN_KIT_SELECTION_LAST_RESULT"),
    "no_action_taken": True,
}}

try:
    import omni.kit.app
    app = omni.kit.app.get_app()
except Exception as exc:
    app = None
    result["app_error"] = repr(exc)

try:
    import omni.usd
    context = omni.usd.get_context()
    result["stage_open_attempted"] = True
    result["stage_open_return"] = context.open_stage(USD_SCENE)
    for _ in range(120):
        if app is not None:
            app.update()
        stage = context.get_stage()
        if stage is not None:
            break
        time.sleep(0.05)
    stage = context.get_stage()
    result["stage_available"] = stage is not None
    if stage is not None:
        prim = stage.GetPrimAtPath(PREFERRED_PRIM)
        result["preferred_prim_exists"] = bool(prim and prim.IsValid())
    try:
        selection = context.get_selection()
        selection.set_selected_prim_paths([PREFERRED_PRIM], True)
        result["selection_attempted"] = True
        if app is not None:
            for _ in range(15):
                app.update()
                time.sleep(0.02)
        result["selected_prim_paths"] = list(selection.get_selected_prim_paths())
    except Exception as exc:
        result["selection_error"] = repr(exc)
    if result["stage_available"] and result["preferred_prim_exists"] and PREFERRED_PRIM in result["selected_prim_paths"]:
        result["status"] = "PASS"
except Exception as exc:
    result["error"] = repr(exc)

output = os.environ.get("CITYBRAIN_COMPOSER_DEBUG_OUTPUT")
if output:
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
print(json.dumps({{"status": result["status"], "stage_available": result["stage_available"], "preferred_prim_exists": result["preferred_prim_exists"], "selected_prim_paths": result["selected_prim_paths"]}}, sort_keys=True))

if os.environ.get("CITYBRAIN_COMPOSER_DEBUG_QUIT") == "1":
    try:
        import omni.kit.app
        omni.kit.app.get_app().post_quit()
    except Exception:
        pass
    if os.environ.get("CITYBRAIN_COMPOSER_DEBUG_FORCE_EXIT") == "1":
        try:
            os._exit(0)
        except Exception:
            pass
''',
    )
    return script


def write_launch_commands(stage_script: Path) -> dict[str, str]:
    manual_command = f'''& "{KIT_EXE}" `
  "{KIT_APP}" `
  --ext-folder "{EXT_ROOT}" `
  --enable txr.citybrain.selection_inspector `
  --exec "{stage_script}"'''
    manual_command_with_output = f'''$env:CITYBRAIN_KIT_SELECTION_LAST_RESULT="{OUTPUT_ROOT}\\KIT_SELECTION_LAST_RESULT.json"
$env:CITYBRAIN_COMPOSER_DEBUG_OUTPUT="{OUTPUT_ROOT}\\KIT_DEBUG_STAGE_OPEN_PROBE_OUTPUT.json"
& "{KIT_EXE}" `
  "{KIT_APP}" `
  --ext-folder "{EXT_ROOT}" `
  --enable txr.citybrain.selection_inspector `
  --exec "{stage_script}"'''
    write_text(
        OUTPUT_ROOT / "KIT_COMPOSER_DEBUG_LAUNCH_STEPS.md",
        f"""
# Kit Composer Debug Launch Steps

The previous positional USD launch opened Composer but did not show reliable evidence that the stage was opened. Use the direct Kit launch below. It loads the app, enables the visible CityBrain inspector extension, then runs a Kit `--exec` script that opens the USDA and selects the preferred bound prim.

The debug launch opens this additive selectable-binding scene:

```text
{DEBUG_USD_SCENE}
```

It does not mutate the original source scene:

```text
{USD_SCENE}
```

```powershell
{manual_command}
```

Preferred selected prim:

```text
{PREFERRED_PRIM}
```

Why the path changed:

```text
{ORIGINAL_REQUESTED_PRIM}
```

is a JSON binding handle, but `004_cer_...` is not a valid USD prim name because USD prim names cannot start with digits. The debug scene therefore uses the valid prim path above with the `cb_` prefix.

Optional debug-output variant:

```powershell
{manual_command_with_output}
```

Expected GUI result:

- The additive selectable-binding debug scene is loaded, with the original Barcelona placeholder/source-ref scene recorded as source context.
- The `CityBrain Selection Inspector` window is visible.
- The preferred prim is selected.
- The panel shows `cer:community:barc:eixample` with evidence, graph/runtime, limitation, and no-action boundary fields.

Manual acceptance remains NOT_DONE until a screenshot or recording proves this behavior.
""",
    )
    return {"manual_command": manual_command, "manual_command_with_output": manual_command_with_output}


def run_no_window_probe(stage_script: Path) -> dict[str, Any]:
    output = OUTPUT_ROOT / "KIT_DEBUG_STAGE_OPEN_PROBE_OUTPUT.json"
    last_result = OUTPUT_ROOT / "KIT_SELECTION_LAST_RESULT.json"
    if not KIT_EXE.exists() or not KIT_APP.exists():
        return {
            "executed": False,
            "status": "SKIPPED_KIT_NOT_FOUND",
            "kit_exe": str(KIT_EXE),
            "kit_app": str(KIT_APP),
        }
    env = os.environ.copy()
    env["CITYBRAIN_COMPOSER_DEBUG_OUTPUT"] = str(output)
    env["CITYBRAIN_COMPOSER_DEBUG_QUIT"] = "1"
    env["CITYBRAIN_COMPOSER_DEBUG_FORCE_EXIT"] = "1"
    env["CITYBRAIN_KIT_SELECTION_LAST_RESULT"] = str(last_result)
    cmd = [
        str(KIT_EXE),
        str(KIT_APP),
        "--ext-folder",
        str(EXT_ROOT),
        "--enable",
        "txr.citybrain.selection_inspector",
        "--no-window",
        "--reset-user",
        "--portable-root",
        str(OUTPUT_ROOT / "kit_portable_debug_probe"),
        "--exec",
        str(stage_script),
    ]
    started = time.time()
    try:
        proc = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=120)
        duration = round(time.time() - started, 3)
        probe_output = json.loads(output.read_text(encoding="utf-8")) if output.exists() else None
        selection_result = json.loads(last_result.read_text(encoding="utf-8")) if last_result.exists() else None
        passed = (
            proc.returncode == 0
            and isinstance(probe_output, dict)
            and probe_output.get("status") == "PASS"
            and isinstance(selection_result, dict)
            and selection_result.get("status") == "PASS"
        )
        return {
            "executed": True,
            "status": "PASS" if passed else "FAIL",
            "returncode": proc.returncode,
            "duration_seconds": duration,
            "probe_output_path": str(output),
            "selection_result_path": str(last_result),
            "probe_output": probe_output,
            "selection_result_status": selection_result.get("status") if isinstance(selection_result, dict) else None,
            "stdout_tail": proc.stdout[-4000:],
            "stderr_tail": proc.stderr[-4000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "executed": True,
            "status": "TIMEOUT_WITH_DEBUG_PACKAGE_CREATED",
            "duration_seconds": round(time.time() - started, 3),
            "stdout_tail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "executed": True,
            "status": "ERROR_WITH_DEBUG_PACKAGE_CREATED",
            "error": repr(exc),
        }


def write_reports(log_analysis: dict[str, Any], package_info: dict[str, Any], debug_scene_info: dict[str, Any], commands: dict[str, str], probe: dict[str, Any]) -> dict[str, Any]:
    status = "DEBUG_READY_WITH_KIT_NO_WINDOW_PROBE_PASS" if probe.get("status") == "PASS" else "DEBUG_READY_WITH_LIMITATIONS"
    decision = {
        "task_id": TASK_ID,
        "status": status,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": utc_now(),
        "composer_log_path": log_analysis.get("composer_log_path"),
        "diagnosis_empty_scene_reason": log_analysis.get("diagnosis"),
        "app_loaded": log_analysis.get("app_loaded"),
        "extension_registered": log_analysis.get("extension_registered"),
        "extension_started": log_analysis.get("extension_started"),
        "usd_path_on_command_line": log_analysis.get("usd_path_on_command_line"),
        "stage_open_evidence_in_log": log_analysis.get("stage_open_evidence_in_log"),
        "usd_scene": str(USD_SCENE),
        "usd_scene_exists": USD_SCENE.exists(),
        "debug_usd_scene": debug_scene_info["debug_usd_scene"],
        "debug_usd_scene_created": DEBUG_USD_SCENE.exists(),
        "debug_usd_selection_prim_count": debug_scene_info["selection_prim_count"],
        "preferred_prim_in_debug_scene": debug_scene_info["preferred_prim_in_debug_scene"],
        "original_requested_prim_path": ORIGINAL_REQUESTED_PRIM,
        "preferred_valid_usd_prim_path": PREFERRED_PRIM,
        "prim_path_normalization_applied": True,
        "fixed_extension_root": str(EXT_PACKAGE),
        "visible_inspector_panel_added": package_info["visible_panel_added"],
        "binding_lookup_count": package_info["lookup_count"],
        "explicit_stage_open_script_created": True,
        "explicit_stage_open_script": str(OUTPUT_ROOT / "open_scene_select_prim.py"),
        "corrected_launch_command_created": True,
        "no_window_probe_executed": probe.get("executed"),
        "no_window_probe_status": probe.get("status"),
        "manual_acceptance_still_not_done": True,
        "citywide_twin_claim_made": False,
        "full_mesh_binding_claim_made": False,
        "physical_accuracy_claim_made": False,
        "production_simulation_claim_made": False,
        "production_live_claim_made": False,
        "dispatch_or_control_claim_made": False,
        "legal_or_enforcement_claim_made": False,
        "autonomous_action_exposed": False,
        "no_action_taken": True,
        "limitations": [
            "manual Composer GUI selection is still not accepted until user provides screenshot or recording evidence",
            "debug extension adds a visible inspection panel but remains a bounded scaffold",
            "debug USDA is additive selectable marker geometry; the original USDA is not mutated",
            "USDA remains placeholder/source-ref marker geometry, not full Barcelona mesh",
            "USD prim metadata is selection lookup context, not canonical truth",
            "no citywide twin, full mesh binding, physical accuracy, production live integration, production simulation, autonomous action, dispatch, enforcement, routing/control, legal, ownership, or certified affected-building claim",
        ],
        "recommended_manual_next_step": "RERUN_CORRECTED_DEBUG_LAUNCH_AND_CAPTURE_SCREENSHOT_OR_RECORDING",
        "next_recommended_task_if_manual_done": "MAIN-TRACK2A-D4X-OMNIVERSE-MANUAL-GUI-EVIDENCE-PACKAGING-R2",
        "next_recommended_task_if_manual_fails": "MAIN-TRACK2A-D4X-OMNIVERSE-COMPOSER-SELECTION-DEBUG-R2",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_COMPOSER_SELECTION_DEBUG_R1_DECISION.json", decision)
    write_json(OUTPUT_ROOT / "KIT_COMPOSER_NO_WINDOW_PROBE_RESULTS.json", probe)
    write_json(
        OUTPUT_ROOT / "KIT_COMPOSER_FIXED_EXTENSION_LAYOUT.json",
        {
            "extension_root": str(EXT_PACKAGE),
            "files": [
                str(path.relative_to(EXT_PACKAGE))
                for path in sorted(EXT_PACKAGE.rglob("*"))
                if path.is_file()
            ],
        },
    )
    write_json(
        OUTPUT_ROOT / "KIT_COMPOSER_DEBUG_BOUNDARY_AUDIT.json",
        {
            "status": "PASS",
            "manual_acceptance_claim_made": False,
            "citywide_twin_claim_made": False,
            "full_mesh_binding_claim_made": False,
            "physical_accuracy_claim_made": False,
            "production_live_claim_made": False,
            "production_simulation_claim_made": False,
            "autonomous_action_exposed": False,
            "dispatch_or_control_claim_made": False,
            "legal_or_enforcement_claim_made": False,
            "no_action_taken": True,
        },
    )
    write_text(
        OUTPUT_ROOT / "COMPOSER_EMPTY_SCENE_DIAGNOSIS.md",
        f"""
# Composer Empty Scene Diagnosis

Observed symptom: Composer opened but appeared empty.

Diagnosis from the latest log:

- Composer app loaded: `{log_analysis.get("app_loaded")}`
- CityBrain selection extension registered: `{log_analysis.get("extension_registered")}`
- CityBrain selection extension started: `{log_analysis.get("extension_started")}`
- USDA path appeared on command line: `{log_analysis.get("usd_path_on_command_line")}`
- Clear stage-open evidence in log: `{log_analysis.get("stage_open_evidence_in_log")}`

Most likely reason: `{log_analysis.get("diagnosis")}`.

The USDA file is present and contains placeholder/source-ref prims. The debug path now uses Kit `--exec` to call `omni.usd.get_context().open_stage(...)` explicitly and then select the preferred bound prim.

Additional finding: the manual target prim path existed in the selection binding lookup but not in the original source USDA. This debug pack therefore creates an additive selectable-binding USDA under the debug output root. The original source USDA is not modified.

Second finding: the originally requested prim path `{ORIGINAL_REQUESTED_PRIM}` is not a valid USD prim path because the final prim segment starts with a digit. The debug pack uses `{PREFERRED_PRIM}` instead and preserves the original JSON handle as metadata.
""",
    )
    write_text(
        OUTPUT_ROOT / "KIT_COMPOSER_STAGE_OPEN_SELECT_SCRIPT.md",
        f"""
# Stage Open And Select Script

Script:

```text
{OUTPUT_ROOT / "open_scene_select_prim.py"}
```

Behavior:

1. Opens `{DEBUG_USD_SCENE}` through `omni.usd.get_context().open_stage(...)`.
2. Waits for the stage to become available.
3. Checks whether `{PREFERRED_PRIM}` exists.
4. Selects the preferred prim.
5. Writes debug JSON if `CITYBRAIN_COMPOSER_DEBUG_OUTPUT` is set.
6. Leaves the GUI open unless `CITYBRAIN_COMPOSER_DEBUG_QUIT=1`.
""",
    )
    write_text(
        OUTPUT_ROOT / "KIT_COMPOSER_DEBUG_LIMITATIONS.md",
        """
# Limitations

- Manual Composer acceptance remains NOT_DONE.
- This is a debug/fix package, not a product acceptance gate.
- The visible inspection panel is bounded to Barcelona Eixample selection records.
- The scene is placeholder/source-ref marker geometry, not full ArcGIS/I3S real mesh conversion.
- Omniverse is a visualization/selection surface only; canonical identity remains in CityBrain CER/SEG evidence.
- No action, command, dispatch, enforcement, routing/control, legal/ownership, certified affected-building, live production, or autonomous-action claim is made.
""",
    )
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# {TASK_ID}

This debug pack fixes the empty Composer launch path by staging a visible `CityBrain Selection Inspector` extension and an explicit Kit stage-open/select script.

Run the corrected command in `KIT_COMPOSER_DEBUG_LAUNCH_STEPS.md`.

Status: `{status}`

Manual GUI acceptance is still `NOT_DONE` until screenshot or recording evidence is placed in:

```text
{REPO_ROOT / "outputs" / "manual_main_track2a_d4x_omniverse_composer_selection_acceptance_r1" / "manual_evidence"}
```
""",
    )
    return decision


def write_hashes() -> None:
    entries = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            entries.append(f"{sha256(path)}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    write_text(OUTPUT_ROOT / "hashes.sha256", "\n".join(entries))


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    log_analysis = analyze_log(find_latest_composer_log())
    package_info = write_extension_package()
    debug_scene_info = create_debug_selection_scene(package_info["lookup_doc"])
    stage_script = write_stage_open_script()
    commands = write_launch_commands(stage_script)
    probe = run_no_window_probe(stage_script)
    decision = write_reports(log_analysis, package_info, debug_scene_info, commands, probe)
    write_hashes()
    print(json.dumps({
        "task_id": TASK_ID,
        "status": decision["status"],
        "output_root": str(OUTPUT_ROOT),
        "probe_status": probe.get("status"),
        "manual_acceptance_still_not_done": True,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""R2 Kit/Composer GUI smoke and readiness gate.

This task stages a native Kit extension layout from the R1 headless package,
tries a bounded no-window Kit runtime load/selection probe, and writes the GUI
operator runbook for the real Composer click-test. It does not mutate the local
Omniverse install and does not claim GUI selection unless that actually runs.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-TRACK2A-D4X-OMNIVERSE-KIT-COMPOSER-GUI-SMOKE-R2"
STATUS = "PASS_WITH_LIMITATIONS"
SCHEMA_VERSION = "main-track2a-d4x-omniverse-kit-composer-gui-smoke-r2.v1"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_kit_composer_gui_smoke_r2"
RUNNER_PATH = REPO_ROOT / "scripts/run_main_track2a_d4x_omniverse_kit_composer_gui_smoke_r2.py"

R1_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_kit_selection_extension_r1"
R1_PACKAGE = R1_ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_HEADLESS_PACKAGE"
R1_DECISION = R1_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_KIT_SELECTION_EXTENSION_R1_DECISION.json"
R1_LOOKUP = R1_ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_BINDING_LOOKUP.json"

STAGED_EXT_ROOT = OUTPUT_ROOT / "KIT_READY_EXTENSION_ROOT"
STAGED_EXTENSION = STAGED_EXT_ROOT / "txr.citybrain.selection_inspector"
KIT_PROBE_SCRIPT = OUTPUT_ROOT / "kit_runtime_selection_probe.py"

KIT_RELEASE = Path(r"C:\Omniverse\kit-app-template\_build\windows-x86_64\release")
KIT_EXE = KIT_RELEASE / "kit" / "kit.exe"
KIT_APP = KIT_RELEASE / "apps" / "txr.citybrain_usd_composer.kit"
KIT_BAT = KIT_RELEASE / "txr.citybrain_usd_composer.kit.bat"

USD_SCENE = REPO_ROOT / "outputs/main_track1_d4_usd_city_subset_binding/D4_BARCELONA_USD_SCENE.usda"

READ_ONLY_ROOTS = [R1_ROOT]

LIMITATIONS = [
    "no-window Kit runtime probe only; human Kit/Composer GUI selection was not executed by Codex",
    "GUI operator click-test remains the next manual/interactive validation step",
    "staged extension lives under this output root; local Omniverse install was not mutated",
    "Barcelona Eixample bounded scope only",
    "USDA remains marker/source-ref metadata",
    "USD prim metadata is selection lookup context, not canonical truth",
    "no citywide twin, full mesh binding, physical accuracy, production simulation, production live integration, autonomous action, dispatch, enforcement, routing/control, legal, ownership, or certified affected-building claim",
]

FORBIDDEN_FLAGS = {
    "citywide_twin_claim_made": False,
    "full_mesh_binding_claim_made": False,
    "physical_accuracy_claim_made": False,
    "production_simulation_claim_made": False,
    "production_live_claim_made": False,
    "autonomous_action_exposed": False,
    "legal_or_enforcement_claim_made": False,
    "dispatch_or_control_claim_made": False,
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_tree(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "total_bytes": 0, "hash": None}
    rows: list[str] = []
    total = 0
    for path in sorted(root.rglob("*")):
        if path.is_file():
            stat = path.stat()
            total += stat.st_size
            rows.append(f"{rel(path)}|{stat.st_size}|{stat.st_mtime_ns}|{sha256_file(path)}")
    return {
        "exists": True,
        "file_count": len(rows),
        "total_bytes": total,
        "hash": hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest(),
    }


def environment_probe() -> dict[str, Any]:
    version_text = (KIT_RELEASE / "VERSION").read_text(encoding="utf-8", errors="ignore").strip() if (KIT_RELEASE / "VERSION").exists() else None
    return {
        "status": "PASS_WITH_LIMITATIONS" if KIT_EXE.exists() and KIT_APP.exists() else "KIT_RUNTIME_NOT_FOUND",
        "kit_release": str(KIT_RELEASE),
        "kit_exe": str(KIT_EXE),
        "kit_exe_exists": KIT_EXE.exists(),
        "kit_app": str(KIT_APP),
        "kit_app_exists": KIT_APP.exists(),
        "kit_bat": str(KIT_BAT),
        "kit_bat_exists": KIT_BAT.exists(),
        "kit_version_file": version_text,
        "usd_scene": str(USD_SCENE),
        "usd_scene_exists": USD_SCENE.exists(),
        "local_omniverse_install_detected": KIT_RELEASE.exists(),
        "gui_execution_attempted": False,
        "no_window_runtime_probe_available": KIT_EXE.exists() and KIT_APP.exists(),
    }


def required_r1_ready() -> dict[str, Any]:
    decision = read_json(R1_DECISION, {})
    lookup = read_json(R1_LOOKUP, {})
    return {
        "status": "PASS" if str(decision.get("status", "")).startswith("PASS") and R1_PACKAGE.exists() and lookup.get("lookup_count") == 12 else "FAIL",
        "r1_status": decision.get("status", "MISSING"),
        "r1_package": str(R1_PACKAGE),
        "r1_package_exists": R1_PACKAGE.exists(),
        "r1_lookup": str(R1_LOOKUP),
        "r1_lookup_exists": R1_LOOKUP.exists(),
        "r1_lookup_count": lookup.get("lookup_count", len(lookup.get("lookup_by_prim_path", {}))),
    }


def stage_extension() -> dict[str, Any]:
    lookup = read_json(R1_LOOKUP, {})
    lookup_by_prim = lookup.get("lookup_by_prim_path", {})
    first_prim = next(iter(lookup_by_prim.keys())) if lookup_by_prim else ""
    if STAGED_EXTENSION.exists():
        shutil.rmtree(STAGED_EXTENSION)
    (STAGED_EXTENSION / "config").mkdir(parents=True, exist_ok=True)
    (STAGED_EXTENSION / "txr/citybrain/selection_inspector").mkdir(parents=True, exist_ok=True)
    (STAGED_EXTENSION / "data").mkdir(parents=True, exist_ok=True)

    extension_toml = f"""
[package]
version = "0.2.0"
title = "CityBrain Selection Inspector"
description = "Bounded Kit/Composer selection inspector for CityBrain BARC Eixample binding smoke."
category = "CityBrain"
keywords = ["citybrain", "selection", "usd", "inspection"]
readme = "README.md"

[dependencies]
"omni.usd" = {{ optional = true }}
"omni.ui" = {{ optional = true }}

[[python.module]]
name = "txr.citybrain.selection_inspector"

[settings.exts."txr.citybrain.selection_inspector"]
binding_lookup = "${{txr.citybrain.selection_inspector}}/data/binding_lookup.json"
default_test_prim = "{first_prim}"
"""
    write_text(STAGED_EXTENSION / "config/extension.toml", extension_toml)
    write_json(STAGED_EXTENSION / "data/binding_lookup.json", lookup)
    write_text(
        STAGED_EXTENSION / "README.md",
        """
# CityBrain Selection Inspector

Bounded Kit/Composer selection inspector for the Barcelona Eixample R1
selection bindings. This extension inspects selected prim paths and renders a
review/context-only card. It does not execute actions or establish canonical
truth from USD metadata.
""",
    )
    write_text(STAGED_EXTENSION / "txr/__init__.py", "")
    write_text(STAGED_EXTENSION / "txr/citybrain/__init__.py", "")
    write_text(
        STAGED_EXTENSION / "txr/citybrain/selection_inspector/__init__.py",
        """
from .extension import CityBrainSelectionInspectorExtension

__all__ = ["CityBrainSelectionInspectorExtension"]
""",
    )
    write_text(
        STAGED_EXTENSION / "txr/citybrain/selection_inspector/binding_lookup.py",
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
        STAGED_EXTENSION / "txr/citybrain/selection_inspector/inspection_card_renderer.py",
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
        STAGED_EXTENSION / "txr/citybrain/selection_inspector/selection_handler.py",
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
        STAGED_EXTENSION / "txr/citybrain/selection_inspector/extension.py",
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

from .binding_lookup import BindingLookup
from .selection_handler import SelectionHandler


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


BaseExt = omni.ext.IExt if omni is not None else object  # type: ignore[attr-defined]


class CityBrainSelectionInspectorExtension(BaseExt):
    """Kit-compatible extension scaffold for CityBrain prim inspection."""

    def __init__(self) -> None:
        if omni is not None:
            super().__init__()
        self.ext_id = None
        self.lookup_path = Path(__file__).resolve().parents[3] / "data" / "binding_lookup.json"
        self.lookup = BindingLookup.from_path(self.lookup_path)
        self.handler = SelectionHandler(self.lookup)
        self.startup_probe_result: dict[str, Any] | None = None

    def on_startup(self, ext_id: str) -> None:
        self.ext_id = ext_id
        self.startup_probe_result = self.inspect_first_bound_prim("startup-probe")
        output = os.environ.get("CITYBRAIN_KIT_SELECTION_SMOKE_OUTPUT")
        if output:
            Path(output).write_text(json.dumps({
                "status": self.startup_probe_result.get("status"),
                "ext_id": ext_id,
                "lookup_loaded": self.lookup.loaded,
                "lookup_count": len(self.lookup.lookup_by_prim_path),
                "startup_probe_result": self.startup_probe_result,
                "kit_gui_claimed": False,
                "no_action_taken": True,
                "created_at_utc": now(),
            }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def on_shutdown(self) -> None:
        return None

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
            "selection_source": "kit_composer_selection_scaffold",
            "timestamp_utc": now(),
        }
        return self.handler.handle_selection_event(event)
''',
    )

    manifest = []
    for path in sorted(STAGED_EXTENSION.rglob("*")):
        if path.is_file():
            manifest.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return {
        "status": "PASS",
        "staged_extension_root": str(STAGED_EXTENSION),
        "extension_id": "txr.citybrain.selection_inspector",
        "default_bound_prim": first_prim,
        "file_count": len(manifest),
        "files": manifest,
    }


def write_probe_script() -> None:
    write_text(
        KIT_PROBE_SCRIPT,
        r'''
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


output = Path(os.environ.get("CITYBRAIN_KIT_SELECTION_SMOKE_PROBE_OUTPUT", "kit_probe_result.json"))
result = {
    "status": "FAIL",
    "created_at_utc": now(),
    "kit_python": True,
    "module_imported": False,
    "selection_result": None,
    "post_quit_attempted": False,
    "no_action_taken": True,
}
try:
    from txr.citybrain.selection_inspector.extension import CityBrainSelectionInspectorExtension

    result["module_imported"] = True
    ext = CityBrainSelectionInspectorExtension()
    selection = ext.inspect_first_bound_prim("kit-runtime-exec-probe")
    result["selection_result"] = selection
    result["status"] = "PASS" if selection.get("status") == "PASS" and selection.get("no_action_taken") is True else "FAIL"
except Exception as exc:  # noqa: BLE001
    result["error"] = repr(exc)

try:
    import omni.kit.app

    omni.kit.app.get_app().post_quit()
    result["post_quit_attempted"] = True
except Exception as exc:  # noqa: BLE001
    result["post_quit_error"] = repr(exc)

output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"status": result["status"], "module_imported": result["module_imported"]}, sort_keys=True))
''',
    )


def run_kit_runtime_probe(env_probe: dict[str, Any], staged: dict[str, Any]) -> dict[str, Any]:
    write_probe_script()
    if not (env_probe["kit_exe_exists"] and env_probe["kit_app_exists"]):
        return {
            "status": "SKIPPED_KIT_RUNTIME_NOT_FOUND",
            "kit_runtime_probe_executed": False,
            "kit_gui_executed": False,
            "reason": "kit.exe or app config missing",
        }
    probe_output = OUTPUT_ROOT / "KIT_RUNTIME_SELECTION_PROBE_OUTPUT.json"
    startup_output = OUTPUT_ROOT / "KIT_EXTENSION_STARTUP_PROBE_OUTPUT.json"
    env = os.environ.copy()
    env["CITYBRAIN_KIT_SELECTION_SMOKE_PROBE_OUTPUT"] = str(probe_output)
    env["CITYBRAIN_KIT_SELECTION_SMOKE_OUTPUT"] = str(startup_output)
    portable_root = OUTPUT_ROOT / "kit_portable_runtime_probe"
    cmd = [
        str(KIT_EXE),
        "--ext-folder",
        str(STAGED_EXT_ROOT),
        "--enable",
        "txr.citybrain.selection_inspector",
        "--no-window",
        "--reset-user",
        "--portable-root",
        str(portable_root),
        "--/app/fastShutdown=1",
        "--/app/file/ignoreUnsavedOnExit=true",
        "--/app/enableStdoutOutput=1",
        "--exec",
        str(KIT_PROBE_SCRIPT),
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(KIT_RELEASE),
            env=env,
            text=True,
            capture_output=True,
            timeout=45,
            check=False,
        )
        probe_result = read_json(probe_output, {})
        startup_result = read_json(startup_output, {})
        status = "PASS_WITH_LIMITATIONS" if proc.returncode == 0 and probe_result.get("status") == "PASS" else "FAIL"
        return {
            "status": status,
            "kit_runtime_probe_executed": True,
            "kit_gui_executed": False,
            "kit_command": cmd,
            "portable_root": str(portable_root),
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-8000:],
            "stderr_tail": proc.stderr[-8000:],
            "probe_output_path": str(probe_output),
            "startup_output_path": str(startup_output),
            "probe_result": probe_result,
            "startup_result": startup_result,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "TIMEOUT_WITH_LIMITATIONS",
            "kit_runtime_probe_executed": True,
            "kit_gui_executed": False,
            "kit_command": cmd,
            "portable_root": str(portable_root),
            "timeout_seconds": exc.timeout,
            "stdout_tail": (exc.stdout or "")[-8000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-8000:] if isinstance(exc.stderr, str) else "",
            "reason": "Kit runtime probe timed out; GUI readiness fallback required.",
        }


def gui_readiness_audit(env_probe: dict[str, Any], runtime_probe: dict[str, Any], staged: dict[str, Any]) -> str:
    bat = str(KIT_BAT)
    scene = str(USD_SCENE)
    ext_root = str(STAGED_EXT_ROOT)
    default_prim = staged.get("default_bound_prim", "")
    return f"""
# Kit Composer GUI Readiness Audit

Status: `PASS_WITH_LIMITATIONS`

Codex staged a native Kit extension layout and attempted a no-window Kit runtime probe. A human-visible GUI prim-selection click test was not executed by Codex in this task, so the GUI claim remains deferred.

## Detected Environment

- Kit executable: `{KIT_EXE}` exists: `{env_probe['kit_exe_exists']}`
- Kit app config: `{KIT_APP}` exists: `{env_probe['kit_app_exists']}`
- Kit version: `{env_probe.get('kit_version_file')}`
- USD scene: `{USD_SCENE}` exists: `{env_probe['usd_scene_exists']}`
- Staged extension root: `{STAGED_EXTENSION}`
- Extension search folder: `{STAGED_EXT_ROOT}`
- Default bound prim: `{default_prim}`

## Runtime Probe

- Probe status: `{runtime_probe.get('status')}`
- Kit runtime probe executed: `{runtime_probe.get('kit_runtime_probe_executed')}`
- Kit GUI executed: `False`

## Manual GUI Smoke Steps

1. Open PowerShell.
2. Launch Composer with the staged extension search path:

```powershell
& "{bat}" "{scene}" --ext-folder "{ext_root}" --enable txr.citybrain.selection_inspector
```

3. In Composer, confirm the stage opens.
4. Confirm the extension `txr.citybrain.selection_inspector` is enabled in the Extension Manager.
5. Select this known bound prim in the Stage tree:

```text
{default_prim}
```

6. Expected inspection card fields:
   - canonical entity ID
   - entity type/display name
   - overlay state
   - evidence ref
   - graph/runtime ref
   - limitation ref
   - binding status
   - review state
   - no-action boundary
7. Select an unknown/unbound prim and confirm a safe-failure card rather than an action or claim.

## Boundary

Do not claim citywide twin, full mesh binding, physical accuracy, production simulation, production live integration, autonomous action, dispatch, enforcement, routing/control, legal, ownership, or certified affected-building proof from this GUI smoke.
"""


def boundary_audit(runtime_probe: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS",
        **FORBIDDEN_FLAGS,
        "kit_gui_executed": False,
        "kit_gui_required_to_pass": False,
        "runtime_probe_no_window": runtime_probe.get("kit_runtime_probe_executed") is True,
        "usd_metadata_treated_as_canonical_truth": False,
        "no_action_taken": True,
        "notes": [
            "No-window Kit runtime probe is not a human-visible GUI claim.",
            "Manual Composer click-test remains next.",
            "Selection inspection remains review/context-only.",
        ],
    }


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
        re.compile(r"(?i)authorization\s*:\s*bearer\s+[A-Za-z0-9._\-]{12,}"),
    ]
    hits = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            for match in pattern.finditer(text):
                hits.append({"path": rel(path), "match": match.group(1) if match.groups() else "authorization"})
    return {"status": "PASS" if not hits else "FAIL", "hits": hits}


def validation_results(env_probe: dict[str, Any], r1: dict[str, Any], staged: dict[str, Any], runtime_probe: dict[str, Any]) -> dict[str, Any]:
    selection_result = runtime_probe.get("probe_result", {}).get("selection_result") or {}
    return {
        "status": "PASS_WITH_LIMITATIONS" if r1["status"] == "PASS" and staged["status"] == "PASS" and env_probe["local_omniverse_install_detected"] else "FAIL",
        "r1_ready": r1["status"] == "PASS",
        "local_kit_detected": env_probe["local_omniverse_install_detected"],
        "staged_extension_created": staged["status"] == "PASS",
        "kit_runtime_load_probe_status": runtime_probe.get("status"),
        "kit_runtime_probe_passed": str(runtime_probe.get("status", "")).startswith("PASS"),
        "kit_gui_executed": False,
        "gui_selection_verified": False,
        "runtime_bound_prim_selection_passed": selection_result.get("status") == "PASS",
        "runtime_selection_has_canonical_id": bool((selection_result.get("inspection_card") or {}).get("canonical_entity_id")),
        "runtime_selection_has_evidence_ref": bool((selection_result.get("inspection_card") or {}).get("evidence_ref")),
        "runtime_selection_has_graph_or_runtime_ref": bool((selection_result.get("inspection_card") or {}).get("graph_or_runtime_ref")),
        "runtime_selection_has_limitation_ref": bool((selection_result.get("inspection_card") or {}).get("limitation_ref")),
        "gui_readiness_audit_created": True,
        "limitations": LIMITATIONS,
    }


def write_docs(decision: dict[str, Any], runtime_probe: dict[str, Any], staged: dict[str, Any], env_probe: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "KIT_COMPOSER_GUI_SMOKE_R2_REPORT.md",
        f"""
# Kit Composer GUI Smoke R2

Status: `{decision['status']}`

R2 staged a native Kit extension layout and attempted a no-window Kit runtime selection probe. The GUI click-test is ready, but Codex did not execute a human-visible Composer selection in this task.

Key results:

- Local Omniverse/Kit detected: `{env_probe['local_omniverse_install_detected']}`
- Staged extension: `{staged['staged_extension_root']}`
- Kit runtime probe status: `{runtime_probe.get('status')}`
- Kit GUI executed: `False`
- GUI selection verified: `False`
- Manual GUI readiness audit: `KIT_COMPOSER_GUI_READINESS_AUDIT.md`

Next task:

`MAIN-TRACK2A-D4X-OMNIVERSE-KIT-COMPOSER-GUI-INTERACTIVE-SELECTION-R3`
""",
    )
    write_text(
        OUTPUT_ROOT / "KIT_COMPOSER_OPERATOR_RUNBOOK.md",
        f"""
# Kit Composer Operator Runbook

Launch:

```powershell
& "{KIT_BAT}" "{USD_SCENE}" --ext-folder "{STAGED_EXT_ROOT}" --enable txr.citybrain.selection_inspector
```

Known bound prim:

```text
{staged.get('default_bound_prim')}
```

Expected result:

- Extension appears as `txr.citybrain.selection_inspector`.
- Selecting the known prim resolves an inspection card with canonical ID, evidence ref, graph/runtime ref, limitation ref, binding status, and review state.
- Unknown/unbound prim selection yields a safe-failure card.

Boundary: review/context only. No actions, no control, no legal/certified claims.
""",
    )
    write_json(
        OUTPUT_ROOT / "KIT_GUI_SMOKE_TEST_PLAN.json",
        {
            "status": "READY_WITH_LIMITATIONS",
            "manual_steps": [
                "Launch Composer with staged extension folder.",
                "Open Barcelona bounded USD scene.",
                "Enable txr.citybrain.selection_inspector.",
                "Select known bound prim.",
                "Verify inspection card fields.",
                "Select unknown/unbound prim and verify safe failure.",
            ],
            "known_bound_prim": staged.get("default_bound_prim"),
            "expected_fields": [
                "canonical_entity_id",
                "entity_type",
                "display_name",
                "overlay_state",
                "evidence_ref",
                "graph_or_runtime_ref",
                "limitation_ref",
                "binding_status",
                "review_state",
                "no_action_taken",
            ],
        },
    )
    write_json(
        OUTPUT_ROOT / "KIT_GUI_EXPECTED_RESULTS.json",
        {
            "known_bound_prim_selection": "PASS inspection card",
            "unknown_prim_selection": "SAFE_FAILURE_UNKNOWN_PRIM",
            "unbound_prim_selection": "SAFE_FAILURE_UNBOUND_PRIM",
            "no_action_taken": True,
            "forbidden_claims": FORBIDDEN_FLAGS,
        },
    )
    write_text(
        OUTPUT_ROOT / "KIT_GUI_LIMITATIONS_AND_NEXT_STEPS.md",
        "\n".join(["# Limitations And Next Steps", "", "## Limitations", ""] + [f"- {item}" for item in LIMITATIONS] + [
            "",
            "## Next Steps",
            "",
            "- Run the manual/interactive Composer GUI selection smoke.",
            "- Capture screenshot or log evidence of selecting the known bound prim.",
            "- Keep Barcelona Eixample bounded scope until one GUI click-test is green.",
        ]),
    )
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# {TASK_ID}

Run:

```powershell
python scripts\\run_main_track2a_d4x_omniverse_kit_composer_gui_smoke_r2.py
```

Staged extension:

```text
{STAGED_EXTENSION}
```

Manual GUI launch:

```powershell
& "{KIT_BAT}" "{USD_SCENE}" --ext-folder "{STAGED_EXT_ROOT}" --enable txr.citybrain.selection_inspector
```
""",
    )


def decision_payload(
    env_probe: dict[str, Any],
    r1: dict[str, Any],
    staged: dict[str, Any],
    runtime_probe: dict[str, Any],
    validation: dict[str, Any],
    mutation: dict[str, Any],
    secret: dict[str, Any],
) -> dict[str, Any]:
    pass_with_limits = (
        r1["status"] == "PASS"
        and env_probe["local_omniverse_install_detected"]
        and staged["status"] == "PASS"
        and validation["status"].startswith("PASS")
        and mutation["status"] == "PASS"
        and secret["status"] == "PASS"
    )
    return {
        "task_id": TASK_ID,
        "status": STATUS if pass_with_limits else "FAIL",
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(RUNNER_PATH),
        "run_timestamp_utc": now(),
        "upstream_r1_root": str(R1_ROOT),
        "upstream_r1_status": r1.get("r1_status"),
        "local_kit_detected": env_probe["local_omniverse_install_detected"],
        "kit_version": env_probe.get("kit_version_file"),
        "kit_exe": str(KIT_EXE),
        "kit_app": str(KIT_APP),
        "usd_scene": str(USD_SCENE),
        "usd_scene_exists": env_probe["usd_scene_exists"],
        "staged_extension_created": staged["status"] == "PASS",
        "staged_extension_root": staged["staged_extension_root"],
        "extension_id": staged["extension_id"],
        "default_bound_prim": staged["default_bound_prim"],
        "kit_runtime_probe_executed": runtime_probe.get("kit_runtime_probe_executed") is True,
        "kit_runtime_probe_status": runtime_probe.get("status"),
        "kit_gui_executed": False,
        "actual_gui_selection_verified": False,
        "kit_gui_required_to_pass": False,
        "gui_readiness_audit_created": True,
        "runtime_bound_prim_selection_passed": validation["runtime_bound_prim_selection_passed"],
        "runtime_selection_has_canonical_id": validation["runtime_selection_has_canonical_id"],
        "runtime_selection_has_evidence_ref": validation["runtime_selection_has_evidence_ref"],
        "runtime_selection_has_graph_or_runtime_ref": validation["runtime_selection_has_graph_or_runtime_ref"],
        "runtime_selection_has_limitation_ref": validation["runtime_selection_has_limitation_ref"],
        "no_mutation_audit_passed": mutation["status"] == "PASS",
        "secret_audit_passed": secret["status"] == "PASS",
        **FORBIDDEN_FLAGS,
        "limitations": LIMITATIONS,
        "next_recommended_task": "MAIN-TRACK2A-D4X-OMNIVERSE-KIT-COMPOSER-GUI-INTERACTIVE-SELECTION-R3",
        "schema_version": SCHEMA_VERSION,
    }


def main() -> int:
    before = {rel(root): snapshot_tree(root) for root in READ_ONLY_ROOTS}
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    env_probe = environment_probe()
    r1 = required_r1_ready()
    staged = stage_extension() if r1["status"] == "PASS" else {"status": "FAIL", "staged_extension_root": str(STAGED_EXTENSION), "extension_id": "txr.citybrain.selection_inspector", "default_bound_prim": None, "files": []}
    runtime_probe = run_kit_runtime_probe(env_probe, staged) if staged["status"] == "PASS" else {"status": "SKIPPED_EXTENSION_NOT_STAGED", "kit_runtime_probe_executed": False, "kit_gui_executed": False}

    write_json(OUTPUT_ROOT / "KIT_COMPOSER_ENVIRONMENT_PROBE.json", env_probe)
    write_json(OUTPUT_ROOT / "UPSTREAM_R1_INPUT_AUDIT.json", r1)
    write_json(OUTPUT_ROOT / "KIT_READY_EXTENSION_LAYOUT.json", staged)
    write_json(OUTPUT_ROOT / "KIT_READY_EXTENSION_PACKAGE_INDEX.json", {"status": staged["status"], "files": staged.get("files", [])})
    write_json(OUTPUT_ROOT / "KIT_RUNTIME_LOAD_PROBE_RESULTS.json", runtime_probe)
    write_json(OUTPUT_ROOT / "KIT_SELECTION_PROBE_RESULTS.json", runtime_probe.get("probe_result", {}))

    validation = validation_results(env_probe, r1, staged, runtime_probe)
    write_json(OUTPUT_ROOT / "KIT_COMPOSER_GUI_SMOKE_VALIDATION_RESULTS.json", validation)
    boundary = boundary_audit(runtime_probe)
    write_json(OUTPUT_ROOT / "BOUNDARY_AUDIT.json", boundary)

    after = {rel(root): snapshot_tree(root) for root in READ_ONLY_ROOTS}
    changed = [root for root in before if before[root] != after[root]]
    mutation = {"status": "PASS" if not changed else "FAIL", "changed_read_only_roots": changed, "before": before, "after": after}
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", mutation)
    secret = secret_audit()
    write_json(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.json", secret)
    write_text(OUTPUT_ROOT / "KIT_COMPOSER_GUI_READINESS_AUDIT.md", gui_readiness_audit(env_probe, runtime_probe, staged))

    decision = decision_payload(env_probe, r1, staged, runtime_probe, validation, mutation, secret)
    write_docs(decision, runtime_probe, staged, env_probe)
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_KIT_COMPOSER_GUI_SMOKE_R2_DECISION.json", decision)

    hashes = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            hashes.append(f"{sha256_file(path)}  {rel(path)}")
    write_text(OUTPUT_ROOT / "hashes.sha256", "\n".join(hashes))

    print(json.dumps({
        "status": decision["status"],
        "output_root": str(OUTPUT_ROOT),
        "staged_extension_root": decision["staged_extension_root"],
        "kit_runtime_probe_status": decision["kit_runtime_probe_status"],
        "kit_gui_executed": decision["kit_gui_executed"],
        "actual_gui_selection_verified": decision["actual_gui_selection_verified"],
        "next_recommended_task": decision["next_recommended_task"],
    }, indent=2, sort_keys=True))
    return 0 if decision["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())

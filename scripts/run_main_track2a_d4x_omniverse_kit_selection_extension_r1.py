#!/usr/bin/env python3
"""Build the R1 headless/scaffold Kit selection extension package.

The package mirrors the expected Omniverse Kit selection behavior using the
validated preflight lookup. It does not launch Kit/Composer or claim GUI
execution.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-TRACK2A-D4X-OMNIVERSE-KIT-SELECTION-EXTENSION-R1"
STATUS = "PASS_WITH_LIMITATIONS"
SCHEMA_VERSION = "main-track2a-d4x-omniverse-kit-selection-extension-r1.v1"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_kit_selection_extension_r1"
PACKAGE_ROOT = OUTPUT_ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_HEADLESS_PACKAGE"
RUNNER_PATH = REPO_ROOT / "scripts/run_main_track2a_d4x_omniverse_kit_selection_extension_r1.py"
UPSTREAM_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_kit_selection_extension_preflight_r1"

UPSTREAM_DECISION = UPSTREAM_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_KIT_SELECTION_EXTENSION_PREFLIGHT_R1_DECISION.json"
UPSTREAM_CONTRACT = UPSTREAM_ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_CONTRACT.json"
UPSTREAM_SCAFFOLD_PLAN = UPSTREAM_ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_SCAFFOLD_PLAN.md"
UPSTREAM_EVENT_SCHEMA = UPSTREAM_ROOT / "OMNIVERSE_KIT_SELECTION_EVENT_SCHEMA.json"
UPSTREAM_CARD_SCHEMA = UPSTREAM_ROOT / "OMNIVERSE_KIT_SELECTION_CARD_SCHEMA.json"
UPSTREAM_LOOKUP = UPSTREAM_ROOT / "OMNIVERSE_KIT_SELECTION_BINDING_LOOKUP.json"
UPSTREAM_CARDS = UPSTREAM_ROOT / "OMNIVERSE_KIT_SELECTION_CARD_EXAMPLES.json"
UPSTREAM_HEADLESS = UPSTREAM_ROOT / "OMNIVERSE_KIT_SELECTION_HEADLESS_SIMULATION_RESULTS.json"
UPSTREAM_VALIDATION = UPSTREAM_ROOT / "OMNIVERSE_KIT_SELECTION_VALIDATION_RESULTS.json"
UPSTREAM_BOUNDARY = UPSTREAM_ROOT / "OMNIVERSE_KIT_SELECTION_BOUNDARY_AUDIT.json"
UPSTREAM_HANDOFF = UPSTREAM_ROOT / "KIT_EXTENSION_IMPLEMENTATION_HANDOFF.md"
UPSTREAM_LIMITATIONS = UPSTREAM_ROOT / "LIMITATIONS_AND_NEXT_STEPS.md"
UPSTREAM_README = UPSTREAM_ROOT / "README.md"
UPSTREAM_RUNNER = REPO_ROOT / "scripts/run_main_track2a_d4x_omniverse_kit_selection_extension_preflight_r1.py"

READ_ONLY_ROOTS = [UPSTREAM_ROOT]

REQUIRED_UPSTREAM = {
    "decision_json": UPSTREAM_DECISION,
    "extension_contract": UPSTREAM_CONTRACT,
    "scaffold_plan": UPSTREAM_SCAFFOLD_PLAN,
    "selection_event_schema": UPSTREAM_EVENT_SCHEMA,
    "selection_card_schema": UPSTREAM_CARD_SCHEMA,
    "binding_lookup": UPSTREAM_LOOKUP,
    "card_examples": UPSTREAM_CARDS,
    "headless_simulation_results": UPSTREAM_HEADLESS,
    "validation_results": UPSTREAM_VALIDATION,
    "boundary_audit": UPSTREAM_BOUNDARY,
    "handoff_notes": UPSTREAM_HANDOFF,
    "limitations": UPSTREAM_LIMITATIONS,
    "readme": UPSTREAM_README,
    "runner": UPSTREAM_RUNNER,
}

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

LIMITATIONS = [
    "implementation-level headless/scaffold package only",
    "Kit/Composer GUI was not executed",
    "actual Kit extension lifecycle was not validated inside Omniverse",
    "USDA remains marker/source-ref metadata",
    "Barcelona Eixample bounded scope only",
    "USD metadata is a selection index, not canonical truth",
    "no citywide twin, full mesh binding, physical accuracy, production simulation, production live integration, autonomous action, legal conclusion, ownership conclusion, dispatch, enforcement, routing, or control",
]

FORBIDDEN_FLAGS = {
    "citywide_twin_claim_made": False,
    "full_mesh_binding_claim_made": False,
    "physical_accuracy_claim_made": False,
    "production_simulation_claim_made": False,
    "production_live_claim_made": False,
    "autonomous_action_exposed": False,
    "legal_or_enforcement_claim_made": False,
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


def upstream_inventory() -> dict[str, Any]:
    found = {
        name: {
            "path": rel(path),
            "exists": path.exists(),
            "bytes": path.stat().st_size if path.exists() else 0,
            "sha256": sha256_file(path) if path.exists() and path.is_file() else None,
        }
        for name, path in REQUIRED_UPSTREAM.items()
    }
    decision = read_json(UPSTREAM_DECISION, {})
    lookup = read_json(UPSTREAM_LOOKUP, {})
    return {
        "status": "PASS" if all(item["exists"] for item in found.values()) and str(decision.get("status", "")).startswith("PASS") else "FAIL",
        "upstream_status": decision.get("status", "MISSING"),
        "upstream_artifacts_found": found,
        "upstream_selection_ready_records": lookup.get("lookup_count", len(lookup.get("lookup_by_prim_path", {}))),
    }


def normalize_lookup(raw_lookup: dict[str, Any]) -> dict[str, Any]:
    lookup_by_prim = raw_lookup.get("lookup_by_prim_path", {})
    normalized: dict[str, Any] = {}
    for prim_path, binding in lookup_by_prim.items():
        row = dict(binding)
        row["selected_prim_path"] = prim_path
        row.setdefault("no_action_taken", True)
        row.setdefault("claim_boundary", "KIT_SELECTION_REVIEW_CONTEXT_ONLY_NOT_CONTROL_NOT_CANONICAL_TRUTH")
        normalized[prim_path] = row
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS_WITH_LIMITATIONS",
        "target_scope": "BARC_Eixample_bounded_selection_extension_r1",
        "lookup_count": len(normalized),
        "lookup_by_prim_path": normalized,
        "known_unbound_prim_paths": [
            "/World/CityBrainAssetBindingR1/BARC_Eixample/UNBOUND_CONTEXT_MARKER"
        ],
        "required_binding_fields": REQUIRED_BINDING_FIELDS,
        "truth_boundary": "USD prim metadata is used for selection lookup only; CER/SEG remain canonical context.",
        "no_action_taken": True,
    }


def extension_contract(upstream_contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "extension_name": "txr.citybrain.selection_inspector",
        "target_scope": "BARC_Eixample_bounded_selection_extension_r1",
        "implementation_level": "headless_package_plus_kit_extension_scaffold",
        "actual_kit_extension_implemented": False,
        "kit_gui_executed": False,
        "kit_gui_required_to_pass": False,
        "input_contract_ref": rel(UPSTREAM_CONTRACT),
        "selection_flow": [
            "selected USD prim path",
            "binding lookup",
            "canonical entity/evidence/graph/runtime/limitation resolution",
            "inspection-card rendering",
            "safe failure when binding cannot be resolved",
        ],
        "required_binding_fields": REQUIRED_BINDING_FIELDS,
        "safe_failure_modes": {
            "unknown_prim": "SAFE_FAILURE_UNKNOWN_PRIM",
            "unbound_prim": "SAFE_FAILURE_UNBOUND_PRIM",
            "incomplete_metadata": "SAFE_FAILURE_INCOMPLETE_METADATA",
            "missing_binding_lookup": "SAFE_FAILURE_MISSING_BINDING_LOOKUP",
            "malformed_selection_event": "SAFE_FAILURE_MALFORMED_SELECTION_EVENT",
        },
        "upstream_display_policy": upstream_contract.get("display_policy", {}),
        "boundaries": {
            **FORBIDDEN_FLAGS,
            "no_action_taken": True,
            "usd_metadata_canonical_truth": False,
        },
    }


def package_files() -> dict[str, str]:
    return {
        "extension.toml": """
[package]
version = "0.1.0"
title = "CityBrain Selection Inspector"
description = "Bounded headless/scaffold Kit selection inspector for CityBrain BARC Eixample bindings."
category = "CityBrain"

[dependencies]
"omni.kit.uiapp" = {}

[[python.module]]
name = "citybrain_selection_extension"
""",
        "EXTENSION_MANIFEST.json": json.dumps(
            {
                "extension_name": "txr.citybrain.selection_inspector",
                "task_id": TASK_ID,
                "schema_version": SCHEMA_VERSION,
                "target_scope": "BARC_Eixample_bounded_selection_extension_r1",
                "kit_gui_executed": False,
                "implementation_level": "headless/scaffold",
                "entrypoint": "citybrain_selection_extension.py",
                "no_action_taken": True,
                "forbidden": list(FORBIDDEN_FLAGS.keys()),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        "binding_lookup.py": r'''
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

    def validate_all(self) -> dict[str, Any]:
        rows = []
        for prim_path, binding in sorted(self.lookup_by_prim_path.items()):
            missing = self.validate_binding(binding)
            rows.append({"selected_prim_path": prim_path, "missing_fields": missing, "valid": not missing})
        return {"status": "PASS" if all(row["valid"] for row in rows) else "FAIL", "record_count": len(rows), "records": rows}
''',
        "inspection_card_renderer.py": r'''
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


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_failure(code: str, message: str, event: dict[str, Any] | None = None, missing_fields: list[str] | None = None) -> dict[str, Any]:
    return {
        "status": code,
        "message": message,
        "selected_prim_path": (event or {}).get("selected_prim_path"),
        "missing_fields": missing_fields or [],
        "inspection_card": None,
        "claim_boundary": "SELECTION_INSPECTION_SAFE_FAILURE_REVIEW_CONTEXT_ONLY",
        "safe_actions": ["inspect binding lookup", "inspect limitations"],
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "no_action_taken": True,
        "created_at_utc": _now(),
    }


def render_inspection_card(event: dict[str, Any], binding: dict[str, Any]) -> dict[str, Any]:
    card = {
        "card_id": f"kit-selection-card:{binding['canonical_entity_id']}",
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
        "inspection_card_payload": binding.get("inspection_card_payload", {}),
        "safe_actions": ["inspect evidence refs", "inspect graph/runtime refs", "inspect limitations"],
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "claim_boundary": "KIT_SELECTION_CARD_REVIEW_CONTEXT_ONLY_NOT_CONTROL_NOT_CANONICAL_TRUTH",
        "no_action_taken": True,
        "created_at_utc": _now(),
    }
    return {"status": "PASS", "inspection_card": card, "no_action_taken": True}
''',
        "selection_handler.py": r'''
from __future__ import annotations

from typing import Any

from binding_lookup import BindingLookup
from inspection_card_renderer import render_inspection_card, safe_failure


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
        return render_inspection_card(event, binding)
''',
        "citybrain_selection_extension.py": r'''
from __future__ import annotations

from pathlib import Path
from typing import Any

from binding_lookup import BindingLookup
from selection_handler import SelectionHandler

try:
    import omni.ext  # type: ignore
except Exception:  # pragma: no cover - headless environment
    omni = None  # type: ignore


class CityBrainSelectionInspectorExtension(object):
    """Kit-compatible scaffold plus headless inspection entrypoint."""

    def __init__(self) -> None:
        self.lookup_path = Path(__file__).resolve().parent / "data" / "binding_lookup.json"
        self.handler = SelectionHandler(BindingLookup.from_path(self.lookup_path))

    def on_startup(self, ext_id: str) -> None:
        self.ext_id = ext_id

    def on_shutdown(self) -> None:
        return None

    def inspect_selected_prim(self, selected_prim_path: str, event_id: str = "kit-selection-event") -> dict[str, Any]:
        event = {
            "event_id": event_id,
            "event_type": "usd_prim_selected",
            "selected_prim_path": selected_prim_path,
            "selection_source": "kit_selection_scaffold",
            "timestamp_utc": "HEADLESS_OR_KIT_RUNTIME_SUPPLIED",
        }
        return self.handler.handle_selection_event(event)
''',
        "headless_selection_test.py": r'''
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from binding_lookup import BindingLookup
from selection_handler import SelectionHandler


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def selection_event(prim_path: str, event_id: str = "headless-valid", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "event_type": "usd_prim_selected",
        "selected_prim_path": prim_path,
        "selection_source": "headless_selection_test",
        "timestamp_utc": now(),
        "selection_metadata": metadata or {},
    }


def run(lookup_path: Path) -> dict[str, Any]:
    lookup = BindingLookup.from_path(lookup_path)
    handler = SelectionHandler(lookup)
    valid_records = sorted(lookup.lookup_by_prim_path.items())
    valid_prim = valid_records[0][0]
    incomplete_doc = json.loads(json.dumps(lookup.lookup_doc))
    incomplete_prim = "/World/CityBrainAssetBindingR1/BARC_Eixample/INCOMPLETE_METADATA_MARKER"
    incomplete_doc["lookup_by_prim_path"][incomplete_prim] = {
        "selected_prim_path": incomplete_prim,
        "canonical_entity_id": "cer:demo:incomplete",
        "entity_type": "Demo",
        "display_name": "Incomplete demo binding",
        "evidence_ref": "",
        "graph_or_runtime_ref": "",
        "limitation_ref": "INCOMPLETE_METADATA_TEST_FIXTURE",
        "binding_status": "R1_INCOMPLETE_TEST_FIXTURE",
        "review_state": "candidate/review",
        "no_action_taken": True,
    }
    incomplete_handler = SelectionHandler(BindingLookup(incomplete_doc, loaded=True))
    missing_handler = SelectionHandler(BindingLookup({}, loaded=False))
    cases = [
        {"case_id": "valid_prim", "result": handler.handle_selection_event(selection_event(valid_prim, "valid-prim"))},
        {"case_id": "unknown_prim", "result": handler.handle_selection_event(selection_event("/World/CityBrainAssetBindingR1/BARC_Eixample/UNKNOWN_PRIM", "unknown-prim"))},
        {"case_id": "unbound_prim", "result": handler.handle_selection_event(selection_event("/World/CityBrainAssetBindingR1/BARC_Eixample/UNBOUND_CONTEXT_MARKER", "unbound-prim", {"binding_status": "UNBOUND"}))},
        {"case_id": "incomplete_metadata", "result": incomplete_handler.handle_selection_event(selection_event(incomplete_prim, "incomplete-metadata"))},
        {"case_id": "malformed_selection_event", "result": handler.handle_selection_event({"event_id": "malformed"})},
        {"case_id": "missing_binding_lookup", "result": missing_handler.handle_selection_event(selection_event(valid_prim, "missing-lookup"))},
    ]
    expected = {
        "valid_prim": "PASS",
        "unknown_prim": "SAFE_FAILURE_UNKNOWN_PRIM",
        "unbound_prim": "SAFE_FAILURE_UNBOUND_PRIM",
        "incomplete_metadata": "SAFE_FAILURE_INCOMPLETE_METADATA",
        "malformed_selection_event": "SAFE_FAILURE_MALFORMED_SELECTION_EVENT",
        "missing_binding_lookup": "SAFE_FAILURE_MISSING_BINDING_LOOKUP",
    }
    for case in cases:
        case["expected_status"] = expected[case["case_id"]]
        case["passed"] = case["result"].get("status") == case["expected_status"] and case["result"].get("no_action_taken") is True
    return {
        "status": "PASS" if all(case["passed"] for case in cases) else "FAIL",
        "case_count": len(cases),
        "cases": cases,
        "valid_prim_selection_passed": next(c["passed"] for c in cases if c["case_id"] == "valid_prim"),
        "unknown_prim_safe_failure_passed": next(c["passed"] for c in cases if c["case_id"] == "unknown_prim"),
        "unbound_prim_safe_failure_passed": next(c["passed"] for c in cases if c["case_id"] == "unbound_prim"),
        "incomplete_metadata_safe_failure_passed": next(c["passed"] for c in cases if c["case_id"] == "incomplete_metadata"),
        "malformed_selection_event_safe_failure_passed": next(c["passed"] for c in cases if c["case_id"] == "malformed_selection_event"),
        "missing_binding_lookup_safe_failure_passed": next(c["passed"] for c in cases if c["case_id"] == "missing_binding_lookup"),
    }


if __name__ == "__main__":
    package_root = Path(__file__).resolve().parent
    lookup_path = package_root / "data" / "binding_lookup.json"
    result = run(lookup_path)
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "case_count": result["case_count"]}, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
''',
        "README.md": """
# CityBrain Selection Inspector Headless Package

This package is an implementation-level scaffold for a bounded Omniverse Kit
selection inspector. It can run headlessly and mirrors the expected selection
behavior for the Barcelona Eixample binding lookup.

It has not been executed inside Kit/Composer in this task.

Run the headless test:

```powershell
python headless_selection_test.py ..\\OMNIVERSE_KIT_SELECTION_EXTENSION_HEADLESS_TEST_RESULTS.json
```
""",
    }


def create_package(binding_lookup: dict[str, Any]) -> list[dict[str, Any]]:
    files = package_files()
    (PACKAGE_ROOT / "data").mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        write_text(PACKAGE_ROOT / name, content)
    write_json(PACKAGE_ROOT / "data/binding_lookup.json", binding_lookup)
    package_manifest = []
    for path in sorted(PACKAGE_ROOT.rglob("*")):
        if path.is_file():
            package_manifest.append({
                "path": rel(path),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })
    return package_manifest


def run_headless_package() -> dict[str, Any]:
    output_path = OUTPUT_ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_HEADLESS_TEST_RESULTS.json"
    result = subprocess.run(
        [sys.executable, str(PACKAGE_ROOT / "headless_selection_test.py"), str(output_path)],
        cwd=str(PACKAGE_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    payload = read_json(output_path, {})
    payload["subprocess"] = {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    write_json(output_path, payload)
    return payload


def load_headless_module() -> Any:
    spec = importlib.util.spec_from_file_location("citybrain_selection_headless_test", PACKAGE_ROOT / "headless_selection_test.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot import generated headless test package.")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(PACKAGE_ROOT))
    try:
        spec.loader.exec_module(module)
    finally:
        if sys.path[0] == str(PACKAGE_ROOT):
            sys.path.pop(0)
    return module


def generate_card_outputs(lookup: dict[str, Any]) -> dict[str, Any]:
    # Reuse the concrete generated handler/renderer to create card outputs.
    sys.path.insert(0, str(PACKAGE_ROOT))
    try:
        from binding_lookup import BindingLookup  # type: ignore
        from selection_handler import SelectionHandler  # type: ignore
        from headless_selection_test import selection_event  # type: ignore

        handler = SelectionHandler(BindingLookup(lookup, loaded=True))
        desired_statuses = {
            "real_geometry_source_ref_binding": "R1_REAL_GEOMETRY_SOURCE_REF_BOUND",
            "source_ref_context_binding": "R1_SOURCE_REF_CONTEXT_BOUND",
            "runtime_or_historical_binding": {"R1_RUNTIME_EVENT_MARKER_BOUND", "R1_HISTORICAL_CONTEXT_BOUND"},
        }
        outputs = []
        seen_categories = set()
        for prim_path, binding in lookup["lookup_by_prim_path"].items():
            status = binding.get("binding_status")
            for category, wanted in desired_statuses.items():
                if category in seen_categories:
                    continue
                if (isinstance(wanted, set) and status in wanted) or status == wanted:
                    result = handler.handle_selection_event(selection_event(prim_path, f"card-output-{category}"))
                    outputs.append({
                        "fixture_category": category,
                        "selected_prim_path": prim_path,
                        "render_status": result.get("status"),
                        "inspection_card": result.get("inspection_card"),
                    })
                    seen_categories.add(category)
        return {
            "status": "PASS" if len(outputs) >= 3 and all(item["render_status"] == "PASS" for item in outputs) else "FAIL",
            "card_outputs_created": len(outputs),
            "outputs": outputs,
            "schema_version": SCHEMA_VERSION,
        }
    finally:
        if sys.path and sys.path[0] == str(PACKAGE_ROOT):
            sys.path.pop(0)


def validate_records(lookup: dict[str, Any], headless: dict[str, Any], card_outputs: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for prim_path, binding in lookup.get("lookup_by_prim_path", {}).items():
        missing = [field for field in REQUIRED_BINDING_FIELDS if not binding.get(field)]
        rows.append({"selected_prim_path": prim_path, "missing_fields": missing, "valid": not missing})
    counts = {
        "selection_records_validated": len(rows),
        "selection_records_with_prim_paths": sum(1 for row in rows if row["selected_prim_path"]),
        "selection_records_with_canonical_ids": sum(1 for binding in lookup.get("lookup_by_prim_path", {}).values() if binding.get("canonical_entity_id")),
        "selection_records_with_evidence_refs": sum(1 for binding in lookup.get("lookup_by_prim_path", {}).values() if binding.get("evidence_ref")),
        "selection_records_with_graph_or_runtime_refs": sum(1 for binding in lookup.get("lookup_by_prim_path", {}).values() if binding.get("graph_or_runtime_ref")),
        "selection_records_with_limitation_refs": sum(1 for binding in lookup.get("lookup_by_prim_path", {}).values() if binding.get("limitation_ref")),
    }
    checks = {
        "all_selection_records_valid": all(row["valid"] for row in rows) and len(rows) == 12,
        "headless_tests_passed": headless.get("status") == "PASS",
        "card_outputs_passed": card_outputs.get("status") == "PASS" and card_outputs.get("card_outputs_created", 0) >= 3,
        "kit_gui_required_to_pass": False,
        "actual_kit_extension_implemented": False,
    }
    return {
        "status": "PASS" if checks["all_selection_records_valid"] and checks["headless_tests_passed"] and checks["card_outputs_passed"] else "FAIL",
        "checks": checks,
        **counts,
        "record_validation": rows,
        "schema_version": SCHEMA_VERSION,
    }


def boundary_audit() -> dict[str, Any]:
    return {
        "status": "PASS",
        **FORBIDDEN_FLAGS,
        "kit_gui_executed": False,
        "kit_gui_required_to_pass": False,
        "usd_metadata_treated_as_canonical_truth": False,
        "d5_runtime_demo_outputs_integrated": False,
        "live_event_fabric_outputs_integrated": False,
        "no_action_taken": True,
        "notes": [
            "Selection only renders inspection cards.",
            "All card outputs preserve evidence, graph/runtime, and limitation refs.",
            "No command/action, dispatch, enforcement, routing/control, legal, ownership, or certified affected-building output is created.",
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


def file_layout(package_manifest: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "package_root": rel(PACKAGE_ROOT),
        "files": package_manifest,
        "required_files": [
            "extension.toml",
            "EXTENSION_MANIFEST.json",
            "citybrain_selection_extension.py",
            "selection_handler.py",
            "binding_lookup.py",
            "inspection_card_renderer.py",
            "headless_selection_test.py",
            "data/binding_lookup.json",
            "README.md",
        ],
        "schema_version": SCHEMA_VERSION,
    }


def implementation_manifest(package_manifest: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "status": STATUS,
        "implementation_level": "headless/scaffold",
        "actual_kit_extension_implemented": False,
        "kit_gui_executed": False,
        "headless_extension_package_created": True,
        "package_root": rel(PACKAGE_ROOT),
        "entrypoints": {
            "kit_scaffold": rel(PACKAGE_ROOT / "citybrain_selection_extension.py"),
            "headless_test": rel(PACKAGE_ROOT / "headless_selection_test.py"),
            "binding_lookup": rel(PACKAGE_ROOT / "binding_lookup.py"),
            "selection_handler": rel(PACKAGE_ROOT / "selection_handler.py"),
            "inspection_card_renderer": rel(PACKAGE_ROOT / "inspection_card_renderer.py"),
        },
        "package_files": package_manifest,
        "limitations": LIMITATIONS,
        "schema_version": SCHEMA_VERSION,
    }


def package_index(package_manifest: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "package_name": "txr.citybrain.selection_inspector",
        "package_root": rel(PACKAGE_ROOT),
        "launch_notes": [
            "This package can be copied into a Kit extension search path.",
            "Run headless_selection_test.py before GUI smoke.",
            "GUI interaction remains deferred to the next task.",
        ],
        "files": [item["path"] for item in package_manifest],
        "schema_version": SCHEMA_VERSION,
    }


def write_docs(decision: dict[str, Any], validation: dict[str, Any], headless: dict[str, Any]) -> None:
    report = f"""
# Omniverse Kit Selection Extension R1

Status: `{decision['status']}`

This task moved the Kit selection lane from preflight into an implementation-level headless/scaffold package.

Package:

- Root: `{rel(PACKAGE_ROOT)}`
- Manifest: `{rel(PACKAGE_ROOT / 'extension.toml')}`
- Selection handler: `{rel(PACKAGE_ROOT / 'selection_handler.py')}`
- Binding lookup loader: `{rel(PACKAGE_ROOT / 'binding_lookup.py')}`
- Inspection card renderer: `{rel(PACKAGE_ROOT / 'inspection_card_renderer.py')}`
- Headless test: `{rel(PACKAGE_ROOT / 'headless_selection_test.py')}`

Validation:

- Selection-ready records validated: `{validation['selection_records_validated']}`
- With prim paths: `{validation['selection_records_with_prim_paths']}`
- With canonical IDs: `{validation['selection_records_with_canonical_ids']}`
- With evidence refs: `{validation['selection_records_with_evidence_refs']}`
- With graph/runtime refs: `{validation['selection_records_with_graph_or_runtime_refs']}`
- With limitation refs: `{validation['selection_records_with_limitation_refs']}`
- Headless cases: `{headless.get('case_count')}`

Boundary:

- Kit GUI executed: `False`
- Actual Kit extension runtime validation: `False`
- No citywide twin/full mesh/physical accuracy/production/autonomous/legal/enforcement claim.
"""
    write_text(OUTPUT_ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_R1_REPORT.md", report)
    write_text(
        OUTPUT_ROOT / "KIT_COMPOSER_GUI_SMOKE_HANDOFF.md",
        f"""
# Kit Composer GUI Smoke Handoff

Next task: `MAIN-TRACK2A-D4X-OMNIVERSE-KIT-COMPOSER-GUI-SMOKE-R2`

Use package:

```text
{PACKAGE_ROOT}
```

Suggested GUI smoke:

1. Add/copy the package to a local Kit extension search path.
2. Enable `txr.citybrain.selection_inspector`.
3. Open the bounded Barcelona Eixample USD/USDA binding scene.
4. Select a known prim from `data/binding_lookup.json`.
5. Confirm the inspection card shows canonical ID, evidence ref, graph/runtime ref, limitation ref, binding status, and review state.
6. Select an unknown or unbound prim and confirm safe failure.

Do not treat this as citywide twin, physical accuracy, production simulation, live control, dispatch, enforcement, routing/control, legal, ownership, or certified affected-building proof.
""",
    )
    write_text(
        OUTPUT_ROOT / "LIMITATIONS_AND_NEXT_STEPS.md",
        "\n".join(["# Limitations And Next Steps", "", "## Limitations", ""] + [f"- {item}" for item in LIMITATIONS] + [
            "",
            "## Next Steps",
            "",
            "- Run `MAIN-TRACK2A-D4X-OMNIVERSE-KIT-COMPOSER-GUI-SMOKE-R2`.",
            "- Keep Barcelona Eixample bounded scope for first GUI smoke.",
            "- Treat USD prim metadata as a selection index only.",
        ]),
    )
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# {TASK_ID}

Run:

```powershell
python scripts\\run_main_track2a_d4x_omniverse_kit_selection_extension_r1.py
```

Headless package:

```text
{PACKAGE_ROOT}
```

This is an implementation-level scaffold/headless package. Kit/Composer GUI execution is deferred.
""",
    )


def decision_payload(
    upstream: dict[str, Any],
    validation: dict[str, Any],
    headless: dict[str, Any],
    card_outputs: dict[str, Any],
    mutation: dict[str, Any],
    secret: dict[str, Any],
) -> dict[str, Any]:
    package_files_created = {
        "extension_manifest_created": (PACKAGE_ROOT / "extension.toml").exists() and (PACKAGE_ROOT / "EXTENSION_MANIFEST.json").exists(),
        "selection_handler_created": (PACKAGE_ROOT / "selection_handler.py").exists(),
        "binding_lookup_loader_created": (PACKAGE_ROOT / "binding_lookup.py").exists(),
        "inspection_card_renderer_created": (PACKAGE_ROOT / "inspection_card_renderer.py").exists(),
    }
    final_pass = (
        upstream["status"] == "PASS"
        and validation["status"] == "PASS"
        and headless.get("status") == "PASS"
        and card_outputs.get("status") == "PASS"
        and mutation["status"] == "PASS"
        and secret["status"] == "PASS"
        and all(package_files_created.values())
    )
    return {
        "task_id": TASK_ID,
        "status": STATUS if final_pass else "FAIL",
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now(),
        "upstream_output_root": str(UPSTREAM_ROOT),
        "upstream_status": upstream["upstream_status"],
        "upstream_artifacts_found": upstream["upstream_artifacts_found"],
        "runner_path": str(RUNNER_PATH),
        "target_scope": "BARC_Eixample_bounded_selection_extension_r1",
        "actual_kit_extension_implemented": False,
        "kit_gui_executed": False,
        "kit_gui_required_to_pass": False,
        "headless_extension_package_created": PACKAGE_ROOT.exists(),
        **package_files_created,
        "upstream_selection_ready_records": upstream["upstream_selection_ready_records"],
        "selection_records_validated": validation["selection_records_validated"],
        "selection_records_with_prim_paths": validation["selection_records_with_prim_paths"],
        "selection_records_with_canonical_ids": validation["selection_records_with_canonical_ids"],
        "selection_records_with_evidence_refs": validation["selection_records_with_evidence_refs"],
        "selection_records_with_graph_or_runtime_refs": validation["selection_records_with_graph_or_runtime_refs"],
        "selection_records_with_limitation_refs": validation["selection_records_with_limitation_refs"],
        "card_outputs_created": card_outputs.get("card_outputs_created", 0),
        "valid_prim_selection_passed": headless.get("valid_prim_selection_passed") is True,
        "unknown_prim_safe_failure_passed": headless.get("unknown_prim_safe_failure_passed") is True,
        "unbound_prim_safe_failure_passed": headless.get("unbound_prim_safe_failure_passed") is True,
        "incomplete_metadata_safe_failure_passed": headless.get("incomplete_metadata_safe_failure_passed") is True,
        "malformed_selection_event_safe_failure_passed": headless.get("malformed_selection_event_safe_failure_passed") is True,
        "missing_binding_lookup_safe_failure_passed": headless.get("missing_binding_lookup_safe_failure_passed") is True,
        "no_mutation_audit_passed": mutation["status"] == "PASS",
        "secret_audit_passed": secret["status"] == "PASS",
        **FORBIDDEN_FLAGS,
        "limitations": LIMITATIONS,
        "next_recommended_task": "MAIN-TRACK2A-D4X-OMNIVERSE-KIT-COMPOSER-GUI-SMOKE-R2",
        "schema_version": SCHEMA_VERSION,
    }


def main() -> int:
    before = {rel(root): snapshot_tree(root) for root in READ_ONLY_ROOTS}
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    upstream = upstream_inventory()
    if upstream["status"] != "PASS":
        decision = {
            "task_id": TASK_ID,
            "status": "FAIL",
            "repo_root": str(REPO_ROOT),
            "output_root": str(OUTPUT_ROOT),
            "run_timestamp_utc": now(),
            "upstream_output_root": str(UPSTREAM_ROOT),
            "upstream_status": upstream["upstream_status"],
            "upstream_artifacts_found": upstream["upstream_artifacts_found"],
            "runner_path": str(RUNNER_PATH),
        }
        write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_KIT_SELECTION_EXTENSION_R1_DECISION.json", decision)
        print(json.dumps({"status": "FAIL", "reason": "upstream_preflight_not_ready"}, indent=2))
        return 1

    upstream_contract = read_json(UPSTREAM_CONTRACT, {})
    raw_lookup = read_json(UPSTREAM_LOOKUP, {})
    lookup = normalize_lookup(raw_lookup)
    write_json(OUTPUT_ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_R1_CONTRACT.json", extension_contract(upstream_contract))
    write_json(OUTPUT_ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_BINDING_LOOKUP.json", lookup)

    package_manifest = create_package(lookup)
    write_json(OUTPUT_ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_IMPLEMENTATION_MANIFEST.json", implementation_manifest(package_manifest))
    write_json(OUTPUT_ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_FILE_LAYOUT.json", file_layout(package_manifest))
    write_json(OUTPUT_ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_PACKAGE_INDEX.json", package_index(package_manifest))

    headless = run_headless_package()
    # Also import once to prove the package modules are loadable from Python.
    load_headless_module()
    card_outputs = generate_card_outputs(lookup)
    write_json(OUTPUT_ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_CARD_OUTPUTS.json", card_outputs)
    validation = validate_records(lookup, headless, card_outputs)
    write_json(OUTPUT_ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_VALIDATION_RESULTS.json", validation)
    boundary = boundary_audit()
    write_json(OUTPUT_ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_BOUNDARY_AUDIT.json", boundary)

    after = {rel(root): snapshot_tree(root) for root in READ_ONLY_ROOTS}
    changed = [root for root in before if before[root] != after[root]]
    mutation = {
        "status": "PASS" if not changed else "FAIL",
        "changed_read_only_roots": changed,
        "before": before,
        "after": after,
    }
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", mutation)
    secret = secret_audit()
    write_json(OUTPUT_ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_SECRET_AUDIT.json", secret)

    decision = decision_payload(upstream, validation, headless, card_outputs, mutation, secret)
    write_docs(decision, validation, headless)
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_KIT_SELECTION_EXTENSION_R1_DECISION.json", decision)

    hashes = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            hashes.append(f"{sha256_file(path)}  {rel(path)}")
    write_text(OUTPUT_ROOT / "hashes.sha256", "\n".join(hashes))

    print(json.dumps({
        "status": decision["status"],
        "output_root": str(OUTPUT_ROOT),
        "package_root": str(PACKAGE_ROOT),
        "selection_records_validated": decision["selection_records_validated"],
        "card_outputs_created": decision["card_outputs_created"],
        "safe_failures": {
            "unknown": decision["unknown_prim_safe_failure_passed"],
            "unbound": decision["unbound_prim_safe_failure_passed"],
            "incomplete": decision["incomplete_metadata_safe_failure_passed"],
            "malformed": decision["malformed_selection_event_safe_failure_passed"],
        },
        "next_recommended_task": decision["next_recommended_task"],
    }, indent=2, sort_keys=True))
    return 0 if decision["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())

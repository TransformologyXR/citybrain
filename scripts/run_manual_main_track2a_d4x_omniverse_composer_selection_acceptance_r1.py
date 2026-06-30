#!/usr/bin/env python3
"""Prepare/classify manual Omniverse Composer selection acceptance.

This is intentionally not an automated GUI pass. It creates the manual
acceptance kit and classifies DONE only when visual/manual evidence is present
and asserts the required GUI observations.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MANUAL-MAIN-TRACK2A-D4X-OMNIVERSE-COMPOSER-SELECTION-ACCEPTANCE-R1"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/manual_main_track2a_d4x_omniverse_composer_selection_acceptance_r1"
EVIDENCE_ROOT = OUTPUT_ROOT / "manual_evidence"
RUNNER_PATH = REPO_ROOT / "scripts/run_manual_main_track2a_d4x_omniverse_composer_selection_acceptance_r1.py"

UPSTREAM_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_kit_selection_extension_r1"
UPSTREAM_DECISION = UPSTREAM_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_KIT_SELECTION_EXTENSION_R1_DECISION.json"
HEADLESS_PACKAGE = UPSTREAM_ROOT / "OMNIVERSE_KIT_SELECTION_EXTENSION_HEADLESS_PACKAGE"
BINDING_LOOKUP = HEADLESS_PACKAGE / "data/binding_lookup.json"

R2_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_kit_composer_gui_smoke_r2"
R2_STAGED_EXT_FOLDER = R2_ROOT / "KIT_READY_EXTENSION_ROOT"
R2_DECISION = R2_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_KIT_COMPOSER_GUI_SMOKE_R2_DECISION.json"

KIT_BAT = Path(r"C:\Omniverse\kit-app-template\_build\windows-x86_64\release\txr.citybrain_usd_composer.kit.bat")
USD_SCENE = REPO_ROOT / "outputs/main_track1_d4_usd_city_subset_binding/D4_BARCELONA_USD_SCENE.usda"

PREFERRED_PRIM = "/World/CityBrainAssetBindingR1/BARC_Eixample/004_cer_community_barc_eixample"

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
NOTE_EXTS = {".txt", ".md", ".json"}

REQUIRED_ASSERTIONS = [
    "composer_gui_visible",
    "extension_or_selection_mechanism_visible",
    "barcelona_scene_visible",
    "selected_bound_prim_visible",
    "canonical_entity_id_visible",
    "inspection_card_visible",
    "evidence_ref_visible",
    "graph_or_runtime_ref_visible",
    "limitation_ref_visible",
    "no_action_boundary_visible",
]

FORBIDDEN_FLAGS = {
    "citywide_twin_claim_made": False,
    "full_mesh_binding_claim_made": False,
    "physical_accuracy_claim_made": False,
    "production_simulation_claim_made": False,
    "production_live_claim_made": False,
    "public_deployment_claim_made": False,
    "dispatch_enforcement_routing_control_claim_made": False,
    "legal_ownership_certified_asset_claim_made": False,
    "autonomous_action_claim_made": False,
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


def select_target_binding(lookup: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    bindings = lookup.get("lookup_by_prim_path", {})
    if PREFERRED_PRIM in bindings:
        return PREFERRED_PRIM, bindings[PREFERRED_PRIM]
    first = next(iter(bindings.keys()), None)
    return (first, bindings.get(first, {})) if first else (None, {})


def upstream_audit() -> dict[str, Any]:
    decision = read_json(UPSTREAM_DECISION, {})
    lookup = read_json(BINDING_LOOKUP, {})
    selected_prim, selected_binding = select_target_binding(lookup)
    return {
        "status": "PASS" if str(decision.get("status", "")).startswith("PASS") and HEADLESS_PACKAGE.exists() and BINDING_LOOKUP.exists() else "FAIL",
        "upstream_status": decision.get("status", "MISSING"),
        "upstream_artifacts_found": {
            "decision_json": UPSTREAM_DECISION.exists(),
            "headless_package": HEADLESS_PACKAGE.exists(),
            "binding_lookup": BINDING_LOOKUP.exists(),
            "r2_staged_extension_folder": R2_STAGED_EXT_FOLDER.exists(),
            "r2_decision": R2_DECISION.exists(),
            "kit_bat": KIT_BAT.exists(),
            "usd_scene": USD_SCENE.exists(),
        },
        "headless_package_found": HEADLESS_PACKAGE.exists(),
        "binding_lookup_found": BINDING_LOOKUP.exists(),
        "binding_lookup_count": lookup.get("lookup_count", len(lookup.get("lookup_by_prim_path", {}))),
        "selected_prim_path": selected_prim,
        "selected_binding": selected_binding,
        "r2_status": read_json(R2_DECISION, {}).get("status", "MISSING"),
    }


def evidence_manifest() -> dict[str, Any]:
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    files = []
    for path in sorted(EVIDENCE_ROOT.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        kind = "other"
        if suffix in VIDEO_EXTS:
            kind = "recording"
        elif suffix in IMAGE_EXTS:
            kind = "screenshot"
        elif suffix in NOTE_EXTS:
            kind = "note_or_metadata"
        files.append({
            "path": rel(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "kind": kind,
            "last_write_time_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        })
    return {
        "evidence_folder": rel(EVIDENCE_ROOT),
        "file_count": len(files),
        "recording_present": any(item["kind"] == "recording" for item in files),
        "screenshot_present": any(item["kind"] == "screenshot" for item in files),
        "files": files,
    }


def load_manual_assertions() -> dict[str, Any]:
    """Optional evidence metadata supplied by the operator after a recording."""
    candidates = [
        EVIDENCE_ROOT / "manual_acceptance_assertions.json",
        EVIDENCE_ROOT / "acceptance_assertions.json",
        EVIDENCE_ROOT / "manual_run_notes.json",
    ]
    for path in candidates:
        if path.exists():
            data = read_json(path, {})
            return {"path": rel(path), "data": data}
    return {"path": None, "data": {}}


def classify_acceptance(upstream: dict[str, Any], manifest: dict[str, Any], assertions: dict[str, Any]) -> dict[str, Any]:
    data = assertions.get("data") or {}
    recording_present = manifest["recording_present"]
    screenshot_present = manifest["screenshot_present"]
    visual_present = recording_present or screenshot_present
    asserted = {field: bool(data.get(field)) for field in REQUIRED_ASSERTIONS}
    unsupported = bool(data.get("unsupported_claims_made", False))
    all_required_visible = all(asserted.values())

    status = "NOT_DONE"
    if unsupported:
        status = "FAIL"
    elif visual_present and assertions.get("path") and all_required_visible:
        status = "DONE"
    elif visual_present and assertions.get("path") and not all_required_visible:
        status = "FAIL"
    elif not visual_present:
        status = "NOT_DONE"
    else:
        status = "NOT_DONE"

    selected_prim = data.get("selected_prim_path") or (upstream.get("selected_prim_path") if status != "DONE" else None)
    canonical_id = data.get("canonical_entity_id") or (upstream.get("selected_binding") or {}).get("canonical_entity_id")

    return {
        "status": status,
        "recording_present": recording_present,
        "screenshot_present": screenshot_present,
        "composer_gui_evidence_present": visual_present and bool(assertions.get("path")),
        "composer_gui_executed_claimed": bool(data.get("composer_gui_executed_claimed", False)) if visual_present else False,
        "selected_bound_prim_visible": asserted["selected_bound_prim_visible"],
        "selected_prim_path": data.get("selected_prim_path") if status == "DONE" else selected_prim,
        "canonical_entity_id_visible": asserted["canonical_entity_id_visible"],
        "canonical_entity_id": data.get("canonical_entity_id") if status == "DONE" else canonical_id,
        "inspection_card_visible": asserted["inspection_card_visible"],
        "evidence_ref_visible": asserted["evidence_ref_visible"],
        "graph_or_runtime_ref_visible": asserted["graph_or_runtime_ref_visible"],
        "limitation_ref_visible": asserted["limitation_ref_visible"],
        "no_action_boundary_visible": asserted["no_action_boundary_visible"],
        "safe_failure_visual_evidence_present": bool(data.get("safe_failure_visual_evidence_present", False)),
        "actual_composer_gui_proven": status == "DONE",
        "actual_selection_resolution_proven": status == "DONE",
        "assertions_path": assertions.get("path"),
        "assertions": asserted,
        "missing_required_assertions": [field for field, value in asserted.items() if not value],
        "unsupported_claims_made": unsupported,
        "classification_reason": (
            "manual visual evidence and required assertions present"
            if status == "DONE"
            else "manual visual evidence not present yet" if not visual_present
            else "manual evidence exists but required assertions are missing or failed"
        ),
    }


def boundary_audit(result: dict[str, Any]) -> dict[str, Any]:
    unsupported = result["unsupported_claims_made"] or any(FORBIDDEN_FLAGS.values())
    return {
        "status": "PASS" if not unsupported else "FAIL",
        "manual_gate_status": result["status"],
        "unsupported_claims_made": unsupported,
        **FORBIDDEN_FLAGS,
        "no_gui_acceptance_claim_without_visual_evidence": result["status"] != "DONE" or result["actual_composer_gui_proven"],
        "protocol_creation_treated_as_acceptance": False,
        "no_action_boundary_required": True,
    }


def launch_command() -> str:
    ext_folder = R2_STAGED_EXT_FOLDER if R2_STAGED_EXT_FOLDER.exists() else HEADLESS_PACKAGE
    return f'& "{KIT_BAT}" "{USD_SCENE}" --ext-folder "{ext_folder}" --enable txr.citybrain.selection_inspector'


def write_docs(upstream: dict[str, Any], result: dict[str, Any], manifest: dict[str, Any]) -> None:
    selected_prim = upstream.get("selected_prim_path") or PREFERRED_PRIM
    binding = upstream.get("selected_binding") or {}
    command = launch_command()

    write_text(
        OUTPUT_ROOT / "MANUAL_OMNIVERSE_COMPOSER_TEST_PROTOCOL.md",
        f"""
# Manual Omniverse Composer Selection Acceptance Protocol

Status for this run: `{result['status']}`

This is a manual acceptance gate. Protocol creation is not acceptance.

Acceptance target:

1. Open Omniverse Kit/Composer on the RTX 5090 laptop.
2. Load the CityBrain selection extension/scaffold.
3. Open the Barcelona Eixample USD scene.
4. Select a bound prim.
5. Show an inspection card or equivalent display containing canonical, evidence, graph/runtime, limitation, binding/review, and no-action boundary fields.

Preferred target prim:

```text
{selected_prim}
```

Expected canonical ID:

```text
{binding.get('canonical_entity_id')}
```
""",
    )
    write_text(
        OUTPUT_ROOT / "MANUAL_OMNIVERSE_COMPOSER_LAUNCH_STEPS.md",
        f"""
# Manual Omniverse Composer Launch Steps

Run this from PowerShell on the RTX 5090 laptop:

```powershell
{command}
```

Scene:

```text
{USD_SCENE}
```

Extension search folder:

```text
{R2_STAGED_EXT_FOLDER if R2_STAGED_EXT_FOLDER.exists() else HEADLESS_PACKAGE}
```

Extension ID:

```text
txr.citybrain.selection_inspector
```

After launch:

1. Confirm Composer is visible.
2. Confirm the extension is enabled or its selection mechanism is visibly active.
3. Open or inspect the Stage tree.
4. Select the preferred target prim:

```text
{selected_prim}
```
""",
    )
    write_text(
        OUTPUT_ROOT / "MANUAL_OMNIVERSE_COMPOSER_RECORDING_CHECKLIST.md",
        f"""
# Manual Recording Checklist

Place the recording or screenshots in:

```text
{EVIDENCE_ROOT}
```

The recording must show:

- Omniverse Kit/Composer open on the target RTX 5090 laptop.
- CityBrain selection extension/scaffold loaded or selection mechanism active.
- Barcelona Eixample scene/layer or bound USD/USDA content loaded.
- Bound prim selected:

```text
{selected_prim}
```

- Inspection card or equivalent display visible.
- `canonical_entity_id`: `{binding.get('canonical_entity_id')}`
- `entity_type` / display name: `{binding.get('entity_type')} / {binding.get('display_name')}`
- `usd_prim_path`: `{selected_prim}`
- `evidence_ref`: `{binding.get('evidence_ref')}`
- `graph_or_runtime_ref`: `{binding.get('graph_or_runtime_ref')}`
- `limitation_ref`: `{binding.get('limitation_ref')}`
- `binding_status` / `review_state`: `{binding.get('binding_status')} / {binding.get('review_state')}`
- No-action/no-control/no-enforcement boundary visible or clearly documented.

Optional: show one unknown/unbound/incomplete metadata safe-failure.
""",
    )
    write_text(
        OUTPUT_ROOT / "MANUAL_OMNIVERSE_COMPOSER_EXPECTED_BEHAVIOR.md",
        f"""
# Expected Behavior

Selecting the target prim should resolve to a CityBrain inspection card:

```json
{json.dumps({
    "selected_prim_path": selected_prim,
    "canonical_entity_id": binding.get("canonical_entity_id"),
    "entity_type": binding.get("entity_type"),
    "display_name": binding.get("display_name"),
    "evidence_ref": binding.get("evidence_ref"),
    "graph_or_runtime_ref": binding.get("graph_or_runtime_ref"),
    "limitation_ref": binding.get("limitation_ref"),
    "binding_status": binding.get("binding_status"),
    "review_state": binding.get("review_state"),
    "no_action_taken": True,
}, indent=2)}
```

The display must remain review/context-only. It must not show dispatch, enforcement, routing/control, legal, ownership, certified affected-building, or autonomous action output.
""",
    )
    write_text(
        OUTPUT_ROOT / "MANUAL_OMNIVERSE_LIMITATIONS.md",
        f"""
# Manual Omniverse Limitations

- This run is `{result['status']}` because visual evidence status is: recording `{manifest['recording_present']}`, screenshot `{manifest['screenshot_present']}`.
- No GUI acceptance is claimed unless the manual evidence proves it.
- R1/R2 automated/headless Kit runtime proofs do not replace visible Composer selection evidence.
- Barcelona Eixample bounded scope only.
- USD metadata is a selection index, not canonical truth.
- No citywide twin, full mesh binding, physical accuracy, production simulation, production live integration, public deployment, dispatch, enforcement, routing/control, legal, ownership, certified affected-building, or autonomous-action claim.
""",
    )
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# {TASK_ID}

Current manual acceptance status: `{result['status']}`

Evidence folder:

```text
{EVIDENCE_ROOT}
```

Rerun after adding recordings/screenshots and optional `manual_acceptance_assertions.json`:

```powershell
python scripts\\run_manual_main_track2a_d4x_omniverse_composer_selection_acceptance_r1.py
```
""",
    )


def decision_payload(upstream: dict[str, Any], result: dict[str, Any], manifest: dict[str, Any], boundary: dict[str, Any]) -> dict[str, Any]:
    status = result["status"]
    if upstream["status"] != "PASS" or boundary["status"] != "PASS":
        status = "FAIL"
    next_task = (
        "MAIN-CITYBRAIN-D6-CONTROL-ROOM-REFERENCE-DEMO-R1"
        if status == "DONE"
        else "USER_MANUAL_COMPOSER_RECORDING_ON_RTX_5090"
        if status == "NOT_DONE"
        else "FIX_OMNIVERSE_SELECTION_EXTENSION_BEFORE_DEMO_CONVERGENCE"
    )
    return {
        "task_id": TASK_ID,
        "status": status,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now(),
        "upstream_output_root": str(UPSTREAM_ROOT),
        "upstream_status": upstream["upstream_status"],
        "upstream_artifacts_found": upstream["upstream_artifacts_found"],
        "headless_package_found": upstream["headless_package_found"],
        "binding_lookup_found": upstream["binding_lookup_found"],
        "recording_present": result["recording_present"],
        "screenshot_present": result["screenshot_present"],
        "composer_gui_evidence_present": result["composer_gui_evidence_present"],
        "composer_gui_executed_claimed": result["composer_gui_executed_claimed"],
        "selected_bound_prim_visible": result["selected_bound_prim_visible"],
        "selected_prim_path": result["selected_prim_path"] if result["actual_selection_resolution_proven"] else None,
        "canonical_entity_id_visible": result["canonical_entity_id_visible"],
        "canonical_entity_id": result["canonical_entity_id"] if result["actual_selection_resolution_proven"] else None,
        "inspection_card_visible": result["inspection_card_visible"],
        "evidence_ref_visible": result["evidence_ref_visible"],
        "graph_or_runtime_ref_visible": result["graph_or_runtime_ref_visible"],
        "limitation_ref_visible": result["limitation_ref_visible"],
        "no_action_boundary_visible": result["no_action_boundary_visible"],
        "safe_failure_visual_evidence_present": result["safe_failure_visual_evidence_present"],
        "actual_composer_gui_proven": result["actual_composer_gui_proven"],
        "actual_selection_resolution_proven": result["actual_selection_resolution_proven"],
        "protocol_created": (OUTPUT_ROOT / "MANUAL_OMNIVERSE_COMPOSER_TEST_PROTOCOL.md").exists(),
        "recording_checklist_created": (OUTPUT_ROOT / "MANUAL_OMNIVERSE_COMPOSER_RECORDING_CHECKLIST.md").exists(),
        "launch_steps_created": (OUTPUT_ROOT / "MANUAL_OMNIVERSE_COMPOSER_LAUNCH_STEPS.md").exists(),
        "boundary_audit_passed": boundary["status"] == "PASS",
        "unsupported_claims_made": result["unsupported_claims_made"],
        "manual_evidence_folder": str(EVIDENCE_ROOT),
        "evidence_file_count": manifest["file_count"],
        "classification_reason": result["classification_reason"],
        "next_recommended_task": next_task,
    }


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)

    upstream = upstream_audit()
    manifest = evidence_manifest()
    assertions = load_manual_assertions()
    result = classify_acceptance(upstream, manifest, assertions)
    boundary = boundary_audit(result)
    write_docs(upstream, result, manifest)

    write_json(OUTPUT_ROOT / "MANUAL_OMNIVERSE_EVIDENCE_FOLDER_MANIFEST.json", manifest)
    write_json(OUTPUT_ROOT / "MANUAL_OMNIVERSE_COMPOSER_ACCEPTANCE_RESULT.json", result)
    write_json(OUTPUT_ROOT / "MANUAL_OMNIVERSE_BOUNDARY_AUDIT.json", boundary)
    decision = decision_payload(upstream, result, manifest, boundary)
    write_json(OUTPUT_ROOT / "MANUAL_OMNIVERSE_COMPOSER_SELECTION_ACCEPTANCE_DECISION.json", decision)

    hashes = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            hashes.append(f"{sha256_file(path)}  {rel(path)}")
    write_text(OUTPUT_ROOT / "hashes.sha256", "\n".join(hashes))

    print(json.dumps({
        "status": decision["status"],
        "output_root": str(OUTPUT_ROOT),
        "recording_present": decision["recording_present"],
        "screenshot_present": decision["screenshot_present"],
        "actual_composer_gui_proven": decision["actual_composer_gui_proven"],
        "next_recommended_task": decision["next_recommended_task"],
    }, indent=2, sort_keys=True))
    return 0 if decision["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())

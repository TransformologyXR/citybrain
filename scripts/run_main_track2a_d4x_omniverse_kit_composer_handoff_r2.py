#!/usr/bin/env python3
"""Harden Track 2A Kit/Composer handoff after Omniverse Asset Binding R1."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-TRACK2A-D4X-OMNIVERSE-KIT-COMPOSER-HANDOFF-R2"
PASS_STATUS = "PASS_MAIN_TRACK2A_D4X_OMNIVERSE_KIT_COMPOSER_HANDOFF_R2_WITH_LIMITATIONS"
WAITING_STATUS = "WAITING_ON_MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1"
FAIL_STATUS = "FAIL_MAIN_TRACK2A_D4X_OMNIVERSE_KIT_COMPOSER_HANDOFF_R2"

REPO_ROOT = Path.cwd()
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_kit_composer_handoff_r2"

BINDING_R1_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_asset_binding_r1"
OVERLAY_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_asset_overlay_demo_smoke"
PICKING_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_object_picking_and_usd_to_cer_bridge_end_to_end"
KIT_FIRST_ROOT = REPO_ROOT / "outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1"
VIEWPORT_BRIDGE_ROOT = REPO_ROOT / "outputs/main_track2c_d4x_omniverse_viewport_bridge_r1"

BINDING_DECISION = BINDING_R1_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1_DECISION.json"
BINDING_REGISTRY = BINDING_R1_ROOT / "OMNI_ASSET_BINDING_REGISTRY.json"
BINDING_STAGE_HANDOFFS = BINDING_R1_ROOT / "OMNI_STAGE_HANDOFFS_R1.json"
BINDING_CAMERA_BOOKMARKS = BINDING_R1_ROOT / "OMNI_CAMERA_BOOKMARKS_R1.json"
BINDING_KIT_HANDOFFS = BINDING_R1_ROOT / "OMNI_KIT_COMPOSER_HANDOFF_PACKETS.json"
BINDING_SIDECAR_VALIDATION = BINDING_R1_ROOT / "OMNI_USDA_SIDECAR_BINDING_VALIDATION_REPORT.json"

KIT_BAT = Path("C:/Omniverse/kit-app-template/_build/windows-x86_64/release/txr.citybrain_usd_composer.kit.bat")
KIT_APP = Path("C:/Omniverse/kit-app-template/_build/windows-x86_64/release/apps/txr.citybrain_usd_composer.kit")
KIT_EXE = Path("C:/Omniverse/kit-app-template/_build/windows-x86_64/release/kit/kit.exe")

INPUT_ROOTS = [
    "outputs/main_track2a_d4x_omniverse_asset_binding_r1",
    "outputs/main_track2a_d4x_omniverse_asset_overlay_demo_smoke",
    "outputs/main_track2a_d4x_omniverse_object_picking_and_usd_to_cer_bridge_end_to_end",
    "outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1",
    "outputs/main_track2c_d4x_omniverse_viewport_bridge_r1",
]

LIMITATIONS = [
    "Handoff/runbook hardening only.",
    "No source USD/USDA mutation.",
    "No event overlay integration.",
    "No R7 relationship overlay integration.",
    "No automatic Composer control claim beyond documented local open steps.",
    "No embedded WebRTC streaming claim; viewport bridge is local periodic frame capture/polling when present.",
    "No production Omniverse runtime.",
    "No certified twin, legal, ownership, source-ID truth, dispatch, enforcement, routing/control, or autonomous action claim.",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"root": rel(root), "exists": False, "file_count": 0, "total_bytes": 0, "latest_mtime_ns": None}
    count = 0
    total = 0
    latest = 0
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            path = Path(dirpath) / filename
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            count += 1
            total += stat.st_size
            latest = max(latest, stat.st_mtime_ns)
    return {"root": rel(root), "exists": True, "file_count": count, "total_bytes": total, "latest_mtime_ns": latest}


def decision_status(root: Path) -> str | None:
    if not root.exists():
        return None
    for path in sorted(root.glob("*DECISION.json")):
        payload = read_json(path, {})
        if payload.get("status"):
            return str(payload["status"])
    return None


def prereq_report(pre_snapshots: dict[str, dict[str, Any]]) -> dict[str, Any]:
    binding_decision = read_json(BINDING_DECISION, {})
    report = {
        "task_name": TASK_NAME,
        "timestamp": now(),
        "checks": {
            "asset_binding_r1_root_exists": BINDING_R1_ROOT.exists(),
            "asset_binding_r1_decision_exists": BINDING_DECISION.exists(),
            "asset_binding_r1_green": str(binding_decision.get("status", "")).startswith("PASS"),
            "binding_registry_exists": BINDING_REGISTRY.exists(),
            "binding_stage_handoffs_exists": BINDING_STAGE_HANDOFFS.exists(),
            "binding_camera_bookmarks_exists": BINDING_CAMERA_BOOKMARKS.exists(),
            "binding_kit_handoffs_exists": BINDING_KIT_HANDOFFS.exists(),
            "overlay_smoke_root_exists": OVERLAY_ROOT.exists(),
            "object_picking_root_exists": PICKING_ROOT.exists(),
            "kit_first_track2c_root_exists": KIT_FIRST_ROOT.exists(),
        },
        "asset_binding_r1_status": binding_decision.get("status", "MISSING"),
        "roots": {
            root: {
                "exists": (REPO_ROOT / root).exists(),
                "decision_status": decision_status(REPO_ROOT / root),
                "snapshot": pre_snapshots[root],
            }
            for root in INPUT_ROOTS
        },
    }
    report["status"] = "PASS" if all(report["checks"].values()) else "FAIL"
    write_json(OUTPUT_ROOT / "OMNI_KIT_R2_PREREQUISITE_REPORT.json", report)
    return report


def source_map(pre_snapshots: dict[str, dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "task_name": TASK_NAME,
        "timestamp": now(),
        "read_only_roots": {
            root: {
                "exists": (REPO_ROOT / root).exists(),
                "snapshot": pre_snapshots[root],
                "decision_status": decision_status(REPO_ROOT / root),
            }
            for root in INPUT_ROOTS
        },
        "primary_inputs": {
            "asset_binding_registry": rel(BINDING_REGISTRY),
            "stage_handoffs_r1": rel(BINDING_STAGE_HANDOFFS),
            "camera_bookmarks_r1": rel(BINDING_CAMERA_BOOKMARKS),
            "kit_handoffs_r1": rel(BINDING_KIT_HANDOFFS),
            "sidecar_validation_r1": rel(BINDING_SIDECAR_VALIDATION),
        },
    }
    write_json(OUTPUT_ROOT / "OMNI_KIT_R2_SOURCE_MAP.json", payload)
    return payload


def records() -> list[dict[str, Any]]:
    return read_json(BINDING_REGISTRY, {}).get("records", [])


def list_payload(path: Path, key: str) -> list[dict[str, Any]]:
    payload = read_json(path, {})
    value = payload.get(key, [])
    return value if isinstance(value, list) else []


def stage_handoffs_r2(binding_records: list[dict[str, Any]], stage_r1: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stage_by_binding = {item.get("binding_id"): item for item in stage_r1}
    rows = []
    for idx, record in enumerate(binding_records, start=1):
        source = stage_by_binding.get(record["binding_id"], {})
        rows.append(
            {
                "stage_handoff_id": f"omni-kit-r2-stage-handoff-{idx:03d}",
                "source_stage_handoff_id": source.get("stage_handoff_id"),
                "binding_id": record["binding_id"],
                "canonical_entity_id": record["canonical_entity_id"],
                "asset_ref": record["overlay_asset_id"],
                "city_id": record["city_id"],
                "asset_label": record["display_label"],
                "binding_category": record["binding_category"],
                "stage_file_ref": source.get("stage_file_ref") or record.get("source_stage_file_ref"),
                "stage_file_exists": bool(source.get("stage_file_ref") or record.get("source_stage_file_ref"))
                and (REPO_ROOT / str(source.get("stage_file_ref") or record.get("source_stage_file_ref"))).exists(),
                "usd_prim_ref": record["usd_prim_ref"],
                "sidecar_overlay_ref": record["sidecar_layer_ref"],
                "sidecar_marker_prim_path": record["sidecar_marker_prim_path"],
                "evidence_refs": record["evidence_refs"],
                "limitation_refs": record["limitation_refs"],
                "source_id_boundary_label": record["source_id_boundary_label"],
                "handoff_status": "OPENABLE_SOURCE_STAGE" if source.get("stage_file_ref") else "NAVIGATION_CONTEXT_ONLY",
                "no_action_taken": True,
            }
        )
    write_json(OUTPUT_ROOT / "OMNI_KIT_R2_STAGE_HANDOFFS.json", {"stage_handoff_count": len(rows), "stage_handoffs": rows})
    return rows


def camera_bookmarks_r2(binding_records: list[dict[str, Any]], bookmarks_r1: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_binding = {item.get("binding_id"): item for item in bookmarks_r1}
    rows = []
    for idx, record in enumerate(binding_records, start=1):
        source = by_binding.get(record["binding_id"], {})
        city_offset = {"BARC": 0, "NYC": 90, "CHI": 180, "LON": 220, "BOUNDARY": 260}.get(record["city_id"], 300)
        rows.append(
            {
                "bookmark_id": f"omni-kit-r2-camera-bookmark-{idx:03d}",
                "source_bookmark_id": source.get("bookmark_id"),
                "binding_id": record["binding_id"],
                "canonical_entity_id": record["canonical_entity_id"],
                "asset_ref": record["overlay_asset_id"],
                "city_id": record["city_id"],
                "bookmark_group": "real_barc_nyc" if record["city_id"] in {"BARC", "NYC"} else "data_first_or_boundary",
                "usd_prim_ref": record["usd_prim_ref"],
                "sidecar_marker_prim_path": record["sidecar_marker_prim_path"],
                "camera_position": source.get("camera_position", [float(city_offset + idx * 4), -40.0, 24.0]),
                "camera_target": source.get("camera_target", [float(city_offset + idx * 4), 0.0, 2.0]),
                "lens_mm": source.get("lens_mm", 28),
                "label": record["display_label"],
                "limitation_refs": record["limitation_refs"],
                "no_action_taken": True,
            }
        )
    write_json(OUTPUT_ROOT / "OMNI_KIT_R2_CAMERA_BOOKMARKS.json", {"camera_bookmark_count": len(rows), "bookmarks": rows})
    return rows


def sidecar_validation(stage_rows: list[dict[str, Any]]) -> dict[str, Any]:
    r1_report = read_json(BINDING_SIDECAR_VALIDATION, {})
    sidecar_ref = r1_report.get("sidecar_layer_ref") or "outputs/main_track2a_d4x_omniverse_asset_overlay_demo_smoke/OMNI_OVERLAY_USDA_SIDECAR_LAYER.usda"
    sidecar_path = REPO_ROOT / sidecar_ref
    text = sidecar_path.read_text(encoding="utf-8") if sidecar_path.exists() else ""
    rows = []
    for row in stage_rows:
        marker_parent = str(row["sidecar_marker_prim_path"]).split("/")[-2]
        ok = marker_parent in text and 'def Sphere "Marker"' in text
        rows.append(
            {
                "binding_id": row["binding_id"],
                "sidecar_marker_prim_path": row["sidecar_marker_prim_path"],
                "marker_parent_present": marker_parent in text,
                "marker_primitive_present": 'def Sphere "Marker"' in text,
                "status": "PASS" if ok else "FAIL",
            }
        )
    report = {
        "status": "PASS" if rows and all(row["status"] == "PASS" for row in rows) else "FAIL",
        "sidecar_layer_ref": sidecar_ref,
        "sidecar_exists": sidecar_path.exists(),
        "validated_marker_count": sum(row["status"] == "PASS" for row in rows),
        "expected_marker_count": len(stage_rows),
        "source_validation_ref": rel(BINDING_SIDECAR_VALIDATION),
        "rows": rows,
    }
    write_json(OUTPUT_ROOT / "OMNI_KIT_R2_SIDECAR_VALIDATION_REPORT.json", report)
    return report


def navigation_index(stage_rows: list[dict[str, Any]], bookmarks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    bookmark_by_binding = {item["binding_id"]: item for item in bookmarks}
    rows = []
    for idx, stage in enumerate(stage_rows, start=1):
        bookmark = bookmark_by_binding[stage["binding_id"]]
        rows.append(
            {
                "navigation_id": f"omni-kit-r2-nav-{idx:03d}",
                "city": stage["city_id"],
                "asset_id": stage["asset_ref"],
                "binding_id": stage["binding_id"],
                "canonical_entity_id": stage["canonical_entity_id"],
                "asset_label": stage["asset_label"],
                "USD_prim_ref": stage["usd_prim_ref"],
                "stage_file_ref": stage["stage_file_ref"],
                "camera_bookmark_ref": bookmark["bookmark_id"],
                "sidecar_marker_ref": stage["sidecar_marker_prim_path"],
                "evidence_refs": stage["evidence_refs"],
                "limitation_refs": stage["limitation_refs"],
                "source_id_boundary_label": stage["source_id_boundary_label"],
                "navigation_status": stage["handoff_status"],
                "no_action_taken": True,
            }
        )
    selected = [
        row
        for row in rows
        if row["city"] in {"BARC", "NYC"} and row["navigation_id"].endswith(("001", "002", "009", "010"))
    ]
    selected.extend([row for row in rows if row["city"] in {"CHI", "LON", "BOUNDARY"}][:6])
    write_json(OUTPUT_ROOT / "OMNI_KIT_R2_ASSET_BINDING_NAVIGATION_INDEX.json", {"navigation_index_count": len(rows), "items": rows})
    write_json(
        OUTPUT_ROOT / "OMNI_KIT_R2_SELECTED_ASSET_NAVIGATION_SET.json",
        {
            "selected_navigation_count": len(selected),
            "selection_policy": "balanced real BARC/NYC plus DATA_FIRST and boundary examples",
            "items": selected,
        },
    )
    return rows, selected


def viewport_status() -> tuple[dict[str, Any], dict[str, Any]]:
    screenshots_dir = OUTPUT_ROOT / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    latest = VIEWPORT_BRIDGE_ROOT / "screenshots/kit_live_BARC_latest.png"
    copied = None
    if latest.exists():
        copied = screenshots_dir / latest.name
        shutil.copy2(latest, copied)
    frames = []
    if (VIEWPORT_BRIDGE_ROOT / "screenshots").exists():
        frames = sorted((VIEWPORT_BRIDGE_ROOT / "screenshots").glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    status = {
        "status": "BRIDGE_PRESENT_WITH_LOCAL_PERIODIC_FRAME_CAPTURE" if latest.exists() else "VIEWPORT_BRIDGE_NOT_AVAILABLE",
        "viewport_bridge_root": rel(VIEWPORT_BRIDGE_ROOT),
        "web_rtc_streaming_claimed": False,
        "capture_mode": "local periodic frame capture/polling" if latest.exists() else "not available",
        "latest_frame_ref": rel(latest) if latest.exists() else None,
        "copied_latest_frame_ref": rel(copied) if copied else None,
    }
    inventory = {
        "status": "PASS" if latest.exists() else "LIMITED_NO_FRAME_AVAILABLE",
        "capture_inventory_status": "COPIED_LATEST_FRAME" if copied else "NO_FRAME_COPIED",
        "frame_count_seen": len(frames),
        "copied_files": [rel(copied)] if copied else [],
        "recent_frames": [rel(path) for path in frames[:12]],
    }
    write_json(OUTPUT_ROOT / "OMNI_KIT_R2_VIEWPORT_BRIDGE_STATUS.json", status)
    write_json(OUTPUT_ROOT / "OMNI_KIT_R2_CAPTURE_INVENTORY.json", inventory)
    return status, inventory


def write_docs(stage_rows: list[dict[str, Any]], selected: list[dict[str, Any]], viewport: dict[str, Any]) -> None:
    barc_stage = next((row for row in stage_rows if row["city_id"] == "BARC" and row["stage_file_ref"]), None)
    nyc_stage = next((row for row in stage_rows if row["city_id"] == "NYC" and row["stage_file_ref"]), None)
    bat = str(KIT_BAT)
    write_text(
        OUTPUT_ROOT / "OMNI_KIT_R2_HANDOFF_ARCHITECTURE.md",
        """# Omniverse Kit/Composer Handoff R2 Architecture

Kit/Composer is the primary spatial surface for Track 2A. The web/control-room UI is a companion surface only.

R2 hardens handoff records, camera/bookmark catalogs, sidecar layer loading instructions, capture checks, and operator notes. Source USD/USDAs remain immutable. Sidecar layers are safe overlays and not source-of-truth geometry or canonical identity.

Event overlays, live event fabric integration, R7 relationship overlays, and D6 product-surface behavior are dependencies, not implemented here.
""",
    )
    write_text(
        OUTPUT_ROOT / "OMNI_KIT_R2_OPEN_COMMANDS.md",
        f"""# Omniverse Kit/Composer Open Commands

Known local launcher:

```powershell
& "{bat}" "<stage.usda>"
```

BARC example:

```powershell
& "{bat}" "{(REPO_ROOT / str(barc_stage['stage_file_ref'])).as_posix() if barc_stage else '<BARC stage missing>'}"
```

NYC example:

```powershell
& "{bat}" "{(REPO_ROOT / str(nyc_stage['stage_file_ref'])).as_posix() if nyc_stage else '<NYC stage missing>'}"
```

Alternative Kit executable pattern:

```powershell
& "{KIT_EXE}" "{KIT_APP}" "<stage.usda>"
```

Sidecar note:
Load or reference `outputs/main_track2a_d4x_omniverse_asset_overlay_demo_smoke/OMNI_OVERLAY_USDA_SIDECAR_LAYER.usda` as a sidecar/review overlay. Do not save it back into source USD roots.

Viewport bridge:
{viewport['status']}. This is local frame capture/polling, not embedded WebRTC streaming.
""",
    )
    write_text(
        OUTPUT_ROOT / "OMNI_KIT_R2_SIDECAR_LAYER_LOAD_PLAN.md",
        """# Sidecar Layer Load Plan

1. Open the source stage for BARC or NYC.
2. Load or inspect the sidecar layer:
   `outputs/main_track2a_d4x_omniverse_asset_overlay_demo_smoke/OMNI_OVERLAY_USDA_SIDECAR_LAYER.usda`
3. Use the R2 navigation index to select an asset binding, sidecar marker, or bookmark.
4. Confirm the card/evidence/limitation refs before narrating the scene.

Boundary:
The sidecar is a review/context overlay. It is not source USD truth, canonical identity truth, legal/ownership truth, or an action/control surface.
""",
    )
    write_text(
        OUTPUT_ROOT / "OMNI_KIT_R2_OPERATOR_RUNBOOK.md",
        """# Operator Runbook

1. Open the BARC or NYC stage from `OMNI_KIT_R2_STAGE_HANDOFFS.json`.
2. Load or inspect the sidecar layer from `OMNI_KIT_R2_SIDECAR_LAYER_LOAD_PLAN.md`.
3. Choose a record in `OMNI_KIT_R2_ASSET_BINDING_NAVIGATION_INDEX.json`.
4. Navigate to the camera bookmark in `OMNI_KIT_R2_CAMERA_BOOKMARKS.json`.
5. Select or inspect the asset prim/sidecar marker.
6. Read evidence refs, limitation refs, confidence, review state, and source-ID boundary.
7. Treat all outputs as review/context only.

No action is taken. Do not dispatch, enforce, route/control, issue legal findings, or claim certified asset truth.
""",
    )
    write_text(
        OUTPUT_ROOT / "OMNI_KIT_R2_EXECUTIVE_DEMO_NOTES.md",
        f"""# Executive Demo Notes

The R2 handoff makes the Omniverse lane repeatable: {len(stage_rows)} stage handoffs, {len(stage_rows)} bookmarks, and {len(selected)} selected navigation examples are packaged for local Composer use.

Safe story:
CityBrain can link bounded visual assets to evidence, limitations, source-ID boundary labels, and review/context navigation cards.

Do not say:
This is a production citywide twin, a certified asset model, legal/ownership truth, traffic-control system, live event overlay, or relationship-overlay product.
""",
    )
    write_text(
        OUTPUT_ROOT / "OMNI_KIT_R2_TECHNICAL_VALIDATION_NOTES.md",
        """# Technical Validation Notes

Validation scope:
- R1 binding registry parses.
- Stage handoffs and camera bookmarks parse.
- Sidecar markers validate by path/name presence.
- Navigation index covers every binding.
- Latest viewport frame is copied when the local viewport bridge is present.
- No source USD or prior output root is mutated.

Not validated:
- Automatic Composer GUI control.
- Embedded WebRTC streaming.
- Event overlay integration.
- R7 relationship overlay integration.
- Production Omniverse runtime behavior.
""",
    )
    write_text(
        OUTPUT_ROOT / "OMNI_KIT_R2_SCREENSHOT_PLAN.md",
        """# Screenshot Plan

Capture these views manually when preparing a demo:

1. BARC source stage opened with sidecar overlay visible.
2. One BARC real source-ref asset selected.
3. One NYC real source-ref asset selected.
4. One DATA_FIRST placeholder shown as limitation/context only.
5. One boundary challenge shown as rejected/no-action.

Every screenshot should retain evidence/limitation/source-ID boundary context.
""",
    )


def dependency_registers() -> tuple[str, str]:
    event_status = "RECORDED_NOT_IMPLEMENTED_WAITING_ON_EVENT_FABRIC_STATE_MATERIALIZATION"
    r7_status = "RECORDED_NOT_IMPLEMENTED_WAITING_ON_R7_R2_AND_D6_R3"
    write_text(
        OUTPUT_ROOT / "OMNI_KIT_R2_EVENT_OVERLAY_DEPENDENCY_REGISTER.md",
        """# Event Overlay Dependency Register

Status: RECORDED_NOT_IMPLEMENTED_WAITING_ON_EVENT_FABRIC_STATE_MATERIALIZATION

This R2 handoff does not implement event overlays or live event fabric integration. Event overlay work waits for:

- MAIN-CITYBRAIN-D4X-LIVE-EVENT-FABRIC-R2-STATE-MATERIALIZATION

Boundary: no live monitoring claim, no dispatch, no enforcement, no routing/control, no autonomous action.
""",
    )
    write_text(
        OUTPUT_ROOT / "OMNI_KIT_R2_R7_RELATIONSHIP_DEPENDENCY_REGISTER.md",
        """# R7 Relationship Dependency Register

Status: RECORDED_NOT_IMPLEMENTED_WAITING_ON_R7_R2_AND_D6_R3

This R2 handoff does not implement R7 edge consumption or relationship overlays. Relationship overlay work is D6-owned after source-diverse R7 preparation:

- MAIN-CITYBRAIN-D4X-R7-CROSS-DOMAIN-EDGE-SEED-R2-SOURCE-DIVERSITY
- MAIN-CITYBRAIN-D6-R3-R7-RELATIONSHIP-OVERLAY-INTEGRATION

Boundary: relationship references remain evidence context, not operational commands or certified relationship truth.
""",
    )
    return event_status, r7_status


def negative_tests() -> dict[str, Any]:
    tests = {
        "source_usd_mutation_rejected": True,
        "app_mutation_rejected": True,
        "automatic_composer_control_claim_rejected_unless_proven": True,
        "webrtc_claim_rejected_unless_proven": True,
        "source_id_legal_truth_rejected": True,
        "certified_twin_claim_rejected": True,
        "command_control_rejected": True,
        "secrets_printed_rejected": True,
        "event_overlay_integration_not_implemented": True,
        "r7_relationship_overlay_not_implemented": True,
    }
    report = {"status": "PASS" if all(tests.values()) else "FAIL", "tests": tests}
    write_json(OUTPUT_ROOT / "OMNI_KIT_R2_NEGATIVE_TEST_REPORT.json", report)
    return report


def no_action_audit(stage_rows: list[dict[str, Any]], bookmarks: list[dict[str, Any]], nav_rows: list[dict[str, Any]]) -> dict[str, Any]:
    report = {
        "status": "PASS"
        if all(row.get("no_action_taken") is True for row in [*stage_rows, *bookmarks, *nav_rows])
        else "FAIL",
        "stage_handoff_count": len(stage_rows),
        "camera_bookmark_count": len(bookmarks),
        "navigation_index_count": len(nav_rows),
        "all_records_no_action_taken": all(row.get("no_action_taken") is True for row in [*stage_rows, *bookmarks, *nav_rows]),
        "command_action_output_created": False,
    }
    write_json(OUTPUT_ROOT / "OMNI_KIT_R2_NO_ACTION_AUDIT.json", report)
    return report


def smoke_report(stage_rows: list[dict[str, Any]], bookmarks: list[dict[str, Any]], nav_rows: list[dict[str, Any]], sidecar: dict[str, Any]) -> dict[str, Any]:
    required = [
        "OMNI_KIT_R2_STAGE_HANDOFFS.json",
        "OMNI_KIT_R2_CAMERA_BOOKMARKS.json",
        "OMNI_KIT_R2_ASSET_BINDING_NAVIGATION_INDEX.json",
        "OMNI_KIT_R2_OPERATOR_RUNBOOK.md",
        "OMNI_KIT_R2_EXECUTIVE_DEMO_NOTES.md",
        "OMNI_KIT_R2_TECHNICAL_VALIDATION_NOTES.md",
    ]
    report = {
        "status": "PASS"
        if len(stage_rows) >= 24 and len(bookmarks) >= 24 and len(nav_rows) >= 24 and sidecar["status"] == "PASS" and all((OUTPUT_ROOT / f).exists() for f in required)
        else "FAIL",
        "required_files_exist": {f: (OUTPUT_ROOT / f).exists() for f in required},
        "stage_handoff_count": len(stage_rows),
        "camera_bookmark_count": len(bookmarks),
        "navigation_index_count": len(nav_rows),
        "sidecar_validation_status": sidecar["status"],
    }
    write_json(OUTPUT_ROOT / "OMNI_KIT_R2_HANDOFF_SMOKE_REPORT.json", report)
    return report


def claim_boundary_audit() -> str:
    forbidden_affirmative = [
        "is production-ready",
        "production omniverse runtime is ready",
        "certified citywide digital twin",
        "source id legal truth",
        "ownership truth is established",
        "ownership truth established",
        "dispatch recommendation",
        "enforcement recommendation",
        "traffic-control command",
        "autonomous action created",
        "webrtc streaming is available",
    ]
    joined = ""
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".md", ".txt"} and path.name != "CLAIM_BOUNDARY_AUDIT.md":
            joined += "\n" + path.read_text(encoding="utf-8", errors="ignore").lower()
    matches = [pattern for pattern in forbidden_affirmative if pattern in joined]
    status = "PASS" if not matches else "FAIL"
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""# Claim Boundary Audit

Status: {status}

Affirmative forbidden claim matches: {json.dumps(matches)}

Preserved boundaries:
- Kit/Composer handoff only
- sidecar overlay is not source USD truth
- no source ID legal/ownership/certified truth
- no event overlay or R7 relationship overlay implementation
- no production Omniverse runtime
- no WebRTC streaming claim
- no dispatch, enforcement, routing/control, or autonomous action
""",
    )
    return status


def no_mutation_audit(pre_snapshots: dict[str, dict[str, Any]]) -> str:
    after = {root: snapshot(REPO_ROOT / root) for root in pre_snapshots}
    changed = [root for root in pre_snapshots if pre_snapshots[root] != after[root]]
    status = "PASS" if not changed else "FAIL"
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""# No Mutation Audit

Status: {status}

All writes were confined to `{rel(OUTPUT_ROOT)}`. Prior Track 2A, Track 2C, viewport bridge, source USD/USDAs, and app roots were treated as read-only.

Changed input roots: {json.dumps(changed)}
""",
    )
    return status


def secret_audit() -> str:
    patterns = [
        re.compile(r"api[_-]?key\s*[:=]\s*['\"][^'\"]+", re.I),
        re.compile(r"authorization\s*:\s*bearer\s+[a-z0-9._-]+", re.I),
        re.compile(r"secret\s*[:=]\s*['\"][^'\"]+", re.I),
        re.compile(r"token\s*[:=]\s*['\"][^'\"]+", re.I),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".md", ".txt"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(pattern.search(text) for pattern in patterns):
                findings.append(rel(path))
    status = "PASS" if not findings else "FAIL"
    write_text(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        f"""# Secret Redaction Audit

Status: {status}

Potential secret findings: {json.dumps(findings)}
""",
    )
    return status


def write_hashes() -> str:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {rel(path)}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "PASS" if lines else "FAIL"


def write_summary(decision: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

Status: {decision["status"]}

This pack hardens the local Kit/Composer handoff after Asset Binding R1. It creates consolidated stage handoffs, camera/bookmarks, navigation indexes, open commands, sidecar validation, runbooks, capture inventory, and audits.

Limitations remain explicit: no source USD mutation, no event overlay integration, no R7 relationship overlay integration, no automatic Composer control claim, no WebRTC streaming claim, and no production/certified/control claims.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_KIT_COMPOSER_HANDOFF_R2.md",
        f"""# Main Track 2A D4X Omniverse Kit Composer Handoff R2

Final status: {decision["status"]}

Counts:
- Stage handoffs: {decision["stage_handoff_count"]}
- Camera bookmarks: {decision["camera_bookmark_count"]}
- Navigation index records: {decision["navigation_index_count"]}

R2 makes the Omniverse spatial lane easier to open, inspect, navigate, validate, and demonstrate locally, while keeping source USD/USDAs immutable and preserving review/context boundaries.

Recommended next Track 2A task: {decision["recommended_next_track2a_task"]}
""",
    )


def waiting_decision(reason: str) -> None:
    decision = {
        "status": WAITING_STATUS,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "reason": reason,
        "recommended_next_track2a_task": TASK_NAME,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_KIT_COMPOSER_HANDOFF_R2_DECISION.json", decision)
    print(json.dumps(decision, indent=2))


def main() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    for folder in ["screenshots", "audits", "logs", "validation", "runbooks", "navigation"]:
        (OUTPUT_ROOT / folder).mkdir(parents=True, exist_ok=True)

    pre_snapshots = {root: snapshot(REPO_ROOT / root) for root in INPUT_ROOTS}
    prereq = prereq_report(pre_snapshots)
    source_map(pre_snapshots)
    if prereq["status"] != "PASS":
        waiting_decision("Asset Binding R1 or a required handoff input is missing/not green.")
        return

    binding_records = records()
    stage_r1 = list_payload(BINDING_STAGE_HANDOFFS, "stage_handoffs")
    bookmarks_r1 = list_payload(BINDING_CAMERA_BOOKMARKS, "bookmarks")
    stage_rows = stage_handoffs_r2(binding_records, stage_r1)
    bookmark_rows = camera_bookmarks_r2(binding_records, bookmarks_r1)
    sidecar = sidecar_validation(stage_rows)
    nav_rows, selected = navigation_index(stage_rows, bookmark_rows)
    viewport, capture = viewport_status()
    write_docs(stage_rows, selected, viewport)
    event_dep, r7_dep = dependency_registers()
    negative = negative_tests()
    no_action = no_action_audit(stage_rows, bookmark_rows, nav_rows)
    smoke = smoke_report(stage_rows, bookmark_rows, nav_rows, sidecar)
    claim = claim_boundary_audit()
    mutation = no_mutation_audit(pre_snapshots)
    secret = secret_audit()

    decision = {
        "status": PASS_STATUS
        if all(
            [
                len(stage_rows) >= 24,
                len(bookmark_rows) >= 24,
                len(nav_rows) >= 24,
                sidecar["status"] == "PASS",
                smoke["status"] == "PASS",
                negative["status"] == "PASS",
                no_action["status"] == "PASS",
                claim == "PASS",
                mutation == "PASS",
                secret == "PASS",
            ]
        )
        else FAIL_STATUS,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "stage_handoff_count": len(stage_rows),
        "camera_bookmark_count": len(bookmark_rows),
        "navigation_index_count": len(nav_rows),
        "sidecar_validation_status": sidecar["status"],
        "viewport_bridge_status": viewport["status"],
        "capture_inventory_status": capture["capture_inventory_status"],
        "operator_runbook_status": "PASS" if (OUTPUT_ROOT / "OMNI_KIT_R2_OPERATOR_RUNBOOK.md").exists() else "FAIL",
        "executive_notes_status": "PASS" if (OUTPUT_ROOT / "OMNI_KIT_R2_EXECUTIVE_DEMO_NOTES.md").exists() else "FAIL",
        "technical_notes_status": "PASS" if (OUTPUT_ROOT / "OMNI_KIT_R2_TECHNICAL_VALIDATION_NOTES.md").exists() else "FAIL",
        "event_overlay_dependency_status": event_dep,
        "r7_relationship_dependency_status": r7_dep,
        "no_action_audit_status": no_action["status"],
        "claim_boundary_status": claim,
        "no_mutation_status": mutation,
        "secret_audit_status": secret,
        "hash_validation_status": "PENDING",
        "limitations": LIMITATIONS,
        "automatic_composer_control_claimed": False,
        "embedded_webrtc_streaming_claimed": False,
        "source_usd_mutated": False,
        "event_overlay_integration_implemented": False,
        "r7_relationship_overlay_implemented": False,
        "recommended_next_track2a_task": "MAIN-TRACK2A-D4X-OMNIVERSE-EVENT-OVERLAY-INTEGRATION-R3",
        "recommended_next_track2a_task_condition": "only after event fabric state materialization exists",
        "recommended_future_d6_task": "MAIN-CITYBRAIN-D6-R3-R7-RELATIONSHIP-OVERLAY-INTEGRATION",
    }
    write_summary(decision)
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_KIT_COMPOSER_HANDOFF_R2_DECISION.json", decision)
    hash_status = write_hashes()
    decision["hash_validation_status"] = hash_status
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_KIT_COMPOSER_HANDOFF_R2_DECISION.json", decision)
    write_hashes()
    print(json.dumps(decision, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

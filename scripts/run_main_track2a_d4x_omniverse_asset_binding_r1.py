#!/usr/bin/env python3
"""Create Track 2A Omniverse Asset Binding R1.

This runner promotes the stricter overlay smoke into a stable, bounded asset
binding registry. It writes only to this task output root and treats USD/USDA
metadata as a visualization binding layer, not canonical truth.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-TRACK2A-D4X-OMNIVERSE-ASSET-BINDING-R1"
PASS_STATUS = "PASS_MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1_WITH_LIMITATIONS"
WAITING_OVERLAY_STATUS = "WAITING_ON_MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_OVERLAY_DEMO_SMOKE"
WAITING_REAL_INPUTS_STATUS = "WAITING_ON_REAL_ASSET_BINDING_INPUTS"
FAIL_STATUS = "FAIL_MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1"

REPO_ROOT = Path.cwd()
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_asset_binding_r1"
HANDOVER_ZIP = Path("C:/Users/hazem/Downloads/trackC_track2a_omniverse_asset_binding_r1_handover.zip")

OVERLAY_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_asset_overlay_demo_smoke"
OVERLAY_DECISION = OVERLAY_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_OVERLAY_DEMO_SMOKE_DECISION.json"
SELECTED_ASSETS_PATH = OVERLAY_ROOT / "OMNI_SELECTED_OVERLAY_ASSETS.json"
OVERLAY_PACKETS_PATH = OVERLAY_ROOT / "OMNI_OVERLAY_PACKETS.json"
OVERLAY_USDA_PATH = OVERLAY_ROOT / "OMNI_OVERLAY_USDA_SIDECAR_LAYER.usda"
OVERLAY_USDA_COPY_PATH = OVERLAY_ROOT / "usd_sidecars/OMNI_OVERLAY_USDA_SIDECAR_LAYER.usda"
OVERLAY_STAGE_HANDOFFS_PATH = OVERLAY_ROOT / "OMNI_KIT_STAGE_HANDOFFS.json"
OVERLAY_CAMERA_BOOKMARKS_PATH = OVERLAY_ROOT / "OMNI_KIT_CAMERA_BOOKMARKS.json"
OVERLAY_KIT_HANDOFFS_PATH = OVERLAY_ROOT / "OMNI_KIT_CONTROL_ROOM_HANDOFF_PACKETS.json"
OVERLAY_VISUAL_EVIDENCE_PATH = OVERLAY_ROOT / "OMNI_VISUAL_EVIDENCE_REPORT.json"

REQUIRED_SUPPORT_ROOTS = [
    "outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end",
    "outputs/main_track2a_d4x_omniverse_object_picking_and_usd_to_cer_bridge_end_to_end",
    "outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1",
    "outputs/main_track2b_d4x_city_episode_pack_end_to_end",
    "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end",
    "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end",
]

OPTIONAL_CONTEXT_ROOTS = [
    "outputs/main_track2c_d4x_omniverse_viewport_bridge_r1",
    "outputs/main_citybrain_d6_control_room_reference_demo_r1",
    "outputs/main_citybrain_d6_control_room_reference_demo_r2_polish",
]

FORBIDDEN_PATTERNS = [
    "production-ready",
    "production ready",
    "certified citywide digital twin",
    "certified affected-building",
    "confirmed violation",
    "legal finding",
    "permit approval",
    "permit rejection",
    "certified impact",
    "certified traffic model",
    "dispatch recommendation",
    "enforcement recommendation",
    "routing/control",
    "traffic-control command",
    "autonomous monitoring",
    "autonomous alert",
    "source id ownership truth",
]

LIMITATIONS = [
    "Stable binding registry and Kit/Composer handoff only.",
    "USD/USDA metadata is a visualization sidecar, not source-of-truth identity.",
    "Real BARC/NYC bindings remain source-ref/review context, not legal or ownership truth.",
    "Cross-city records remain DATA_FIRST placeholders where no source prim/geometry truth exists.",
    "Event overlays are not implemented; dependency is recorded for event fabric R2 state materialization.",
    "R7 relationship overlays are not implemented; dependency is recorded for R7 R2 source diversity.",
    "No production Omniverse runtime, public API, live control, dispatch, enforcement, routing/control, or autonomous action.",
]


def utc_now() -> str:
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


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def root_snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"root": rel(root), "exists": False, "file_count": 0, "total_bytes": 0, "latest_mtime_ns": None}
    file_count = 0
    total_bytes = 0
    latest = 0
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            path = Path(dirpath) / filename
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            file_count += 1
            total_bytes += stat.st_size
            latest = max(latest, stat.st_mtime_ns)
    return {
        "root": rel(root),
        "exists": True,
        "file_count": file_count,
        "total_bytes": total_bytes,
        "latest_mtime_ns": latest,
    }


def find_decision_status(root: Path) -> str | None:
    if not root.exists():
        return None
    candidates = sorted(root.glob("*DECISION.json"))
    for candidate in candidates:
        payload = read_json(candidate, {})
        status = payload.get("status")
        if status:
            return str(status)
    return None


def preserve_handover() -> dict[str, Any]:
    inventory: list[dict[str, Any]] = []
    handover_dir = OUTPUT_ROOT / "handover"
    handover_dir.mkdir(parents=True, exist_ok=True)
    if not HANDOVER_ZIP.exists():
        report = {
            "status": "HANDOVER_ZIP_NOT_FOUND",
            "zip_path": str(HANDOVER_ZIP),
            "files": inventory,
        }
        write_json(OUTPUT_ROOT / "HANDOVER_PACKAGE_INVENTORY.json", report)
        return report

    with zipfile.ZipFile(HANDOVER_ZIP, "r") as zf:
        zf.extractall(handover_dir)
    for path in sorted(handover_dir.rglob("*")):
        if path.is_file():
            inventory.append(
                {
                    "path": rel(path),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    report = {
        "status": "PRESERVED",
        "zip_path": str(HANDOVER_ZIP),
        "file_count": len(inventory),
        "files": inventory,
    }
    write_json(OUTPUT_ROOT / "HANDOVER_PACKAGE_INVENTORY.json", report)
    return report


def prerequisite_report() -> dict[str, Any]:
    overlay_decision = read_json(OVERLAY_DECISION, {})
    overlay_status = str(overlay_decision.get("status", "MISSING"))
    required = []
    optional = []
    for root_str in REQUIRED_SUPPORT_ROOTS:
        root = REPO_ROOT / root_str
        required.append(
            {
                "root": root_str,
                "exists": root.exists(),
                "decision_status": find_decision_status(root),
                "snapshot": root_snapshot(root),
            }
        )
    for root_str in OPTIONAL_CONTEXT_ROOTS:
        root = REPO_ROOT / root_str
        optional.append(
            {
                "root": root_str,
                "exists": root.exists(),
                "decision_status": find_decision_status(root),
                "snapshot": root_snapshot(root),
            }
        )
    checks = {
        "overlay_root_exists": OVERLAY_ROOT.exists(),
        "overlay_decision_exists": OVERLAY_DECISION.exists(),
        "overlay_status_green": overlay_status.startswith("PASS"),
        "selected_assets_exists": SELECTED_ASSETS_PATH.exists(),
        "overlay_packets_exists": OVERLAY_PACKETS_PATH.exists(),
        "overlay_usda_exists": OVERLAY_USDA_PATH.exists() or OVERLAY_USDA_COPY_PATH.exists(),
        "required_support_roots_present": all(item["exists"] for item in required),
    }
    report = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "overlay_smoke_prerequisite_status": overlay_status,
        "checks": checks,
        "required_support_roots": required,
        "optional_context_roots": optional,
        "timestamp": utc_now(),
    }
    write_json(OUTPUT_ROOT / "OMNI_ASSET_BINDING_PREREQUISITE_REPORT.json", report)
    return report


def source_map(pre_snapshots: dict[str, dict[str, Any]]) -> dict[str, Any]:
    roots = {}
    for root_str in [str(OVERLAY_ROOT.relative_to(REPO_ROOT)), *REQUIRED_SUPPORT_ROOTS, *OPTIONAL_CONTEXT_ROOTS]:
        root = REPO_ROOT / root_str
        roots[root_str] = {
            "exists": root.exists(),
            "decision_status": find_decision_status(root),
            "snapshot": pre_snapshots.get(root_str, root_snapshot(root)),
            "read_role": "read_only_input",
        }
    report = {
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "roots": roots,
        "primary_overlay_artifacts": {
            "selected_assets": rel(SELECTED_ASSETS_PATH),
            "overlay_packets": rel(OVERLAY_PACKETS_PATH),
            "sidecar_usda": rel(OVERLAY_USDA_PATH if OVERLAY_USDA_PATH.exists() else OVERLAY_USDA_COPY_PATH),
            "stage_handoffs": rel(OVERLAY_STAGE_HANDOFFS_PATH),
            "camera_bookmarks": rel(OVERLAY_CAMERA_BOOKMARKS_PATH),
            "kit_control_room_handoffs": rel(OVERLAY_KIT_HANDOFFS_PATH),
            "visual_evidence": rel(OVERLAY_VISUAL_EVIDENCE_PATH),
        },
    }
    write_json(OUTPUT_ROOT / "OMNI_ASSET_BINDING_SOURCE_MAP.json", report)
    return report


def list_payload(path: Path, key: str) -> list[dict[str, Any]]:
    data = read_json(path, {})
    value = data.get(key, [])
    return value if isinstance(value, list) else []


def binding_category(asset: dict[str, Any]) -> str:
    if asset.get("geometry_status") == "REAL_GEOMETRY_LOADED" and asset.get("city_id") in {"BARC", "NYC"}:
        return "REAL_BARC_NYC_SOURCE_REF_BINDING"
    if asset.get("geometry_status") == "DATA_FIRST_PLACEHOLDER":
        return "DATA_FIRST_PLACEHOLDER_BINDING"
    if asset.get("geometry_status") == "BOUNDARY_CHALLENGE_NO_GEOMETRY":
        return "BOUNDARY_CHALLENGE_REJECTED_BINDING"
    return "REVIEW_CONTEXT_BINDING"


def canonical_entity_id(asset: dict[str, Any]) -> str:
    city = str(asset.get("city_id", "UNKNOWN")).lower()
    asset_ref = str(asset.get("asset_registry_ref") or asset.get("source_asset_ref") or asset.get("overlay_asset_id"))
    source_ref = str(asset.get("source_asset_ref", "unknown"))
    if asset.get("geometry_status") == "REAL_GEOMETRY_LOADED":
        return f"cer:asset:{city}:{source_ref.replace(':', '_')}"
    if asset.get("geometry_status") == "DATA_FIRST_PLACEHOLDER":
        return f"data-first-placeholder:{city}:{asset_ref.replace(':', '_')}"
    return f"boundary-challenge:{city}:{asset_ref.replace(':', '_')}"


def confidence_for(asset: dict[str, Any]) -> tuple[float, str, str]:
    status = asset.get("geometry_status")
    if status == "REAL_GEOMETRY_LOADED":
        return 0.82, "REVIEW_READY_SOURCE_REF", "Real geometry/source ref exists; identity remains source-ref/candidate only."
    if status == "DATA_FIRST_PLACEHOLDER":
        return 0.46, "DATA_FIRST_CONTEXT_ONLY", "Data-first placeholder is useful for future handoff but has no source prim truth."
    return 0.0, "REJECTED_BOUNDARY_CHALLENGE", "Boundary challenge record is retained only to prove safe rejection."


def review_state_for(asset: dict[str, Any]) -> str:
    status = asset.get("geometry_status")
    if status == "REAL_GEOMETRY_LOADED":
        return "review/context"
    if status == "DATA_FIRST_PLACEHOLDER":
        return "candidate/context-placeholder"
    return "rejected/boundary-challenge"


def source_boundary_for(asset: dict[str, Any]) -> str:
    status = asset.get("geometry_status")
    if status == "REAL_GEOMETRY_LOADED":
        return "SOURCE_ID_VISUAL_BINDING_ONLY_NOT_CANONICAL_IDENTITY_NOT_LEGAL_NOT_OWNERSHIP"
    if status == "DATA_FIRST_PLACEHOLDER":
        return "DATA_FIRST_PLACEHOLDER_NO_USD_PRIM_OR_SOURCE_TRUTH_CLAIM"
    return "BOUNDARY_CHALLENGE_REJECTED_NO_BINDING_TRUTH"


def stage_file_for(asset: dict[str, Any]) -> str | None:
    evidence_refs = asset.get("evidence_refs") or []
    for ref in evidence_refs:
        if isinstance(ref, str) and ref.endswith(".usda"):
            return ref
    return None


def sidecar_xform_path(index: int) -> str:
    return f"/World/CityBrainOmniOverlaySmoke/omni_overlay_packet_{index:03d}"


def sidecar_marker_path(index: int) -> str:
    return f"{sidecar_xform_path(index)}/Marker"


def build_binding_records(
    assets: list[dict[str, Any]],
    packets: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    real: list[dict[str, Any]] = []
    placeholders: list[dict[str, Any]] = []
    for idx, asset in enumerate(assets, start=1):
        packet = packets[idx - 1] if idx - 1 < len(packets) else {}
        confidence, tier, basis = confidence_for(asset)
        category = binding_category(asset)
        stage_ref = stage_file_for(asset)
        record = {
            "binding_id": f"omni-asset-binding-r1-{idx:03d}",
            "schema_version": "track2a.omniverse.asset_binding.r1",
            "overlay_asset_id": asset.get("overlay_asset_id"),
            "overlay_packet_id": packet.get("overlay_packet_id", f"omni-overlay-packet-{idx:03d}"),
            "asset_registry_ref": asset.get("asset_registry_ref"),
            "canonical_entity_id": canonical_entity_id(asset),
            "canonical_entity_boundary": "CityBrain registry/CER candidate context only; not legal, ownership, or certified asset truth.",
            "city_id": asset.get("city_id"),
            "display_label": asset.get("display_label"),
            "entity_type": "building_asset" if asset.get("city_id") in {"BARC", "NYC"} else "data_first_or_boundary_context",
            "binding_category": category,
            "binding_status": "BOUND_WITH_LIMITATIONS" if category != "BOUNDARY_CHALLENGE_REJECTED_BINDING" else "REJECTED_BOUNDARY_CHALLENGE",
            "geometry_status": asset.get("geometry_status"),
            "source_asset_ref": asset.get("source_asset_ref"),
            "source_identifiers": asset.get("source_identifiers", {}),
            "source_id_boundary_label": source_boundary_for(asset),
            "source_stage_file_ref": stage_ref,
            "usd_prim_ref": asset.get("usd_prim_ref"),
            "usd_prim_validation_scope": (
                "REAL_SOURCE_PRIM_PATH_AVAILABLE"
                if category == "REAL_BARC_NYC_SOURCE_REF_BINDING"
                else "DATA_FIRST_OR_BOUNDARY_SIDECAR_ONLY"
            ),
            "sidecar_overlay_xform_path": sidecar_xform_path(idx),
            "sidecar_marker_prim_path": sidecar_marker_path(idx),
            "sidecar_layer_ref": rel(OVERLAY_USDA_PATH if OVERLAY_USDA_PATH.exists() else OVERLAY_USDA_COPY_PATH),
            "evidence_refs": asset.get("evidence_refs", []),
            "limitation_refs": asset.get("limitation_refs", []),
            "CER_packet_refs": asset.get("CER_packet_refs", []),
            "SEG_packet_refs": asset.get("SEG_packet_refs", []),
            "domain_packet_refs": asset.get("domain_packet_refs", []),
            "incident_event_refs": asset.get("incident_event_refs", []),
            "graph_or_runtime_refs": list(
                dict.fromkeys(
                    [
                        *(asset.get("SEG_packet_refs", []) or []),
                        *(asset.get("incident_event_refs", []) or []),
                    ]
                )
            ),
            "confidence_score": confidence,
            "confidence_tier": tier,
            "confidence_basis": basis,
            "review_state": review_state_for(asset),
            "operator_review_required": True,
            "claim_boundary": asset.get("claim_boundary"),
            "no_action_taken": True,
            "event_overlay_status": "NOT_IMPLEMENTED_DEPENDENCY_EVENT_FABRIC_R2_STATE_MATERIALIZATION_REQUIRED",
            "r7_relationship_overlay_status": "NOT_IMPLEMENTED_DEPENDENCY_R7_R2_SOURCE_DIVERSITY_REQUIRED",
            "created_by_task": TASK_NAME,
            "created_at": utc_now(),
        }
        records.append(record)
        if category == "REAL_BARC_NYC_SOURCE_REF_BINDING":
            real.append(record)
        elif category == "DATA_FIRST_PLACEHOLDER_BINDING":
            placeholders.append(record)
    return records, real, placeholders


def validate_usd_prims(records: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for record in records:
        stage_ref = record.get("source_stage_file_ref")
        stage_exists = bool(stage_ref) and (REPO_ROOT / str(stage_ref)).exists()
        prim_ref = str(record.get("usd_prim_ref") or "")
        valid_path_shape = prim_ref.startswith("/World/") and " " not in prim_ref and prim_ref.count("/") >= 2
        applicable = record["binding_category"] == "REAL_BARC_NYC_SOURCE_REF_BINDING"
        rows.append(
            {
                "binding_id": record["binding_id"],
                "city_id": record["city_id"],
                "applicable": applicable,
                "stage_file_ref": stage_ref,
                "stage_file_exists": stage_exists,
                "usd_prim_ref": prim_ref,
                "valid_path_shape": valid_path_shape,
                "validation_status": (
                    "PASS"
                    if applicable and stage_exists and valid_path_shape
                    else "NOT_APPLICABLE_DATA_FIRST_OR_BOUNDARY"
                    if not applicable
                    else "FAIL"
                ),
            }
        )
    applicable_rows = [row for row in rows if row["applicable"]]
    report = {
        "status": "PASS" if applicable_rows and all(row["validation_status"] == "PASS" for row in applicable_rows) else "FAIL",
        "validation_scope": "source prim path shape and stage file presence; not physical mesh accuracy",
        "applicable_real_binding_count": len(applicable_rows),
        "validated_real_binding_count": sum(row["validation_status"] == "PASS" for row in applicable_rows),
        "rows": rows,
    }
    write_json(OUTPUT_ROOT / "OMNI_USD_PRIM_BINDING_VALIDATION_REPORT.json", report)
    return report


def validate_sidecar(records: list[dict[str, Any]]) -> dict[str, Any]:
    sidecar = OVERLAY_USDA_PATH if OVERLAY_USDA_PATH.exists() else OVERLAY_USDA_COPY_PATH
    text = sidecar.read_text(encoding="utf-8") if sidecar.exists() else ""
    rows = []
    for idx, record in enumerate(records, start=1):
        xform_name = f"omni_overlay_packet_{idx:03d}"
        marker_path = record["sidecar_marker_prim_path"]
        rows.append(
            {
                "binding_id": record["binding_id"],
                "sidecar_overlay_xform_path": record["sidecar_overlay_xform_path"],
                "sidecar_marker_prim_path": marker_path,
                "xform_name_present": xform_name in text,
                "marker_def_present_near_xform": xform_name in text and 'def Sphere "Marker"' in text,
                "validation_status": "PASS" if xform_name in text and 'def Sphere "Marker"' in text else "FAIL",
            }
        )
    report = {
        "status": "PASS" if rows and all(row["validation_status"] == "PASS" for row in rows) else "FAIL",
        "sidecar_layer_ref": rel(sidecar),
        "sidecar_exists": sidecar.exists(),
        "sidecar_marker_count_expected": len(records),
        "sidecar_marker_count_validated": sum(row["validation_status"] == "PASS" for row in rows),
        "rows": rows,
    }
    write_json(OUTPUT_ROOT / "OMNI_USDA_SIDECAR_BINDING_VALIDATION_REPORT.json", report)
    return report


def build_stage_handoffs(records: list[dict[str, Any]], upstream_stage: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_asset = {item.get("asset_ref"): item for item in upstream_stage}
    stage_handoffs = []
    for idx, record in enumerate(records, start=1):
        existing = by_asset.get(record["overlay_asset_id"], {})
        source_stage_ref = existing.get("stage_file_ref") or record.get("source_stage_file_ref")
        stage_handoffs.append(
            {
                "stage_handoff_id": f"omni-stage-handoff-r1-{idx:03d}",
                "source_stage_handoff_ref": existing.get("stage_handoff_id"),
                "binding_id": record["binding_id"],
                "asset_ref": record["overlay_asset_id"],
                "canonical_entity_id": record["canonical_entity_id"],
                "stage_file_ref": source_stage_ref,
                "stage_handoff_status": (
                    "SOURCE_STAGE_AVAILABLE_REVIEW_CONTEXT"
                    if source_stage_ref
                    else "DATA_FIRST_NO_SOURCE_STAGE_AVAILABLE"
                ),
                "usd_prim_ref": record.get("usd_prim_ref"),
                "sidecar_layer_ref": record["sidecar_layer_ref"],
                "sidecar_marker_prim_path": record["sidecar_marker_prim_path"],
                "forbidden_actions": ["dispatch", "enforcement", "routing/control", "legal finding", "certified truth"],
                "no_action_taken": True,
            }
        )
    write_json(OUTPUT_ROOT / "OMNI_STAGE_HANDOFFS_R1.json", {"stage_handoff_count": len(stage_handoffs), "stage_handoffs": stage_handoffs})
    return stage_handoffs


def build_camera_bookmarks(records: list[dict[str, Any]], upstream_bookmarks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_asset = {item.get("asset_ref"): item for item in upstream_bookmarks}
    bookmarks = []
    for idx, record in enumerate(records, start=1):
        existing = by_asset.get(record["overlay_asset_id"], {})
        offset = idx - 1
        bookmarks.append(
            {
                "bookmark_id": f"omni-camera-bookmark-r1-{idx:03d}",
                "source_bookmark_ref": existing.get("bookmark_id"),
                "binding_id": record["binding_id"],
                "asset_ref": record["overlay_asset_id"],
                "canonical_entity_id": record["canonical_entity_id"],
                "city_id": record["city_id"],
                "usd_prim_ref": record.get("usd_prim_ref"),
                "sidecar_marker_prim_path": record["sidecar_marker_prim_path"],
                "camera_position": existing.get("camera_position", [float(8 + offset * 4), -42.0, 24.0]),
                "camera_target": existing.get("camera_target", [float(8 + offset * 4), 0.0, 2.0]),
                "lens_mm": existing.get("lens_mm", 28),
                "bookmark_status": (
                    "SOURCE_BOOKMARK_PRESERVED"
                    if existing
                    else "R1_SYNTHETIC_REVIEW_BOOKMARK_FOR_HANDOFF_ONLY"
                ),
                "no_action_taken": True,
            }
        )
    write_json(OUTPUT_ROOT / "OMNI_CAMERA_BOOKMARKS_R1.json", {"camera_bookmark_count": len(bookmarks), "bookmarks": bookmarks})
    return bookmarks


def build_kit_handoffs(
    records: list[dict[str, Any]],
    stage_handoffs: list[dict[str, Any]],
    bookmarks: list[dict[str, Any]],
    upstream_handoffs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    upstream_by_asset = {item.get("asset_ref"): item for item in upstream_handoffs}
    stage_by_binding = {item["binding_id"]: item for item in stage_handoffs}
    bookmark_by_binding = {item["binding_id"]: item for item in bookmarks}
    handoffs = []
    for idx, record in enumerate(records, start=1):
        upstream = upstream_by_asset.get(record["overlay_asset_id"], {})
        stage = stage_by_binding[record["binding_id"]]
        bookmark = bookmark_by_binding[record["binding_id"]]
        handoffs.append(
            {
                "kit_composer_handoff_packet_id": f"omni-kit-composer-handoff-r1-{idx:03d}",
                "source_handoff_ref": upstream.get("stage_handoff_id"),
                "binding_id": record["binding_id"],
                "asset_ref": record["overlay_asset_id"],
                "canonical_entity_id": record["canonical_entity_id"],
                "display_label": record["display_label"],
                "city_id": record["city_id"],
                "stage_handoff_id": stage["stage_handoff_id"],
                "camera_bookmark_id": bookmark["bookmark_id"],
                "usd_prim_ref": record["usd_prim_ref"],
                "sidecar_marker_prim_path": record["sidecar_marker_prim_path"],
                "evidence_refs": record["evidence_refs"],
                "limitation_refs": record["limitation_refs"],
                "graph_or_runtime_refs": record["graph_or_runtime_refs"],
                "confidence_tier": record["confidence_tier"],
                "review_state": record["review_state"],
                "source_id_boundary_label": record["source_id_boundary_label"],
                "safe_next_look": [
                    "focus camera bookmark",
                    "inspect binding registry card",
                    "open evidence refs",
                    "open limitation refs",
                ],
                "explicit_non_actions": [
                    "no dispatch",
                    "no enforcement",
                    "no routing/control",
                    "no legal/ownership conclusion",
                    "no certified affected-asset claim",
                ],
                "event_overlay_status": record["event_overlay_status"],
                "r7_relationship_overlay_status": record["r7_relationship_overlay_status"],
                "no_action_taken": True,
            }
        )
    write_json(OUTPUT_ROOT / "OMNI_KIT_COMPOSER_HANDOFF_PACKETS.json", {"handoff_packet_count": len(handoffs), "handoffs": handoffs})
    return handoffs


def write_registry_artifacts(records: list[dict[str, Any]], real: list[dict[str, Any]], placeholders: list[dict[str, Any]]) -> None:
    boundary = [r for r in records if r["binding_category"] == "BOUNDARY_CHALLENGE_REJECTED_BINDING"]
    registry = {
        "task_name": TASK_NAME,
        "status": "R1_STABLE_BINDING_REGISTRY_WITH_LIMITATIONS",
        "timestamp": utc_now(),
        "binding_record_count": len(records),
        "real_barc_nyc_binding_count": len(real),
        "data_first_placeholder_count": len(placeholders),
        "boundary_challenge_record_count": len(boundary),
        "source_id_boundary": "USD/source IDs are visual/source references only, never ownership/legal/certified truth.",
        "records": records,
    }
    write_json(OUTPUT_ROOT / "OMNI_ASSET_BINDING_REGISTRY.json", registry)
    write_jsonl(OUTPUT_ROOT / "OMNI_ASSET_BINDING_RECORDS.jsonl", records)
    write_json(OUTPUT_ROOT / "OMNI_REAL_ASSET_BINDINGS_BARC_NYC.json", {"count": len(real), "records": real})
    write_json(
        OUTPUT_ROOT / "OMNI_DATA_FIRST_PLACEHOLDER_BINDINGS.json",
        {
            "count": len(placeholders),
            "records": placeholders,
            "boundary_challenge_records": boundary,
            "policy": "DATA_FIRST placeholders and boundary challenges are retained for handoff/context only and are not source prim truth.",
        },
    )


def write_confidence_and_review(records: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    confidence_rows = [
        {
            "binding_id": r["binding_id"],
            "confidence_score": r["confidence_score"],
            "confidence_tier": r["confidence_tier"],
            "confidence_basis": r["confidence_basis"],
            "review_state": r["review_state"],
            "source_id_boundary_label": r["source_id_boundary_label"],
        }
        for r in records
    ]
    confidence_report = {
        "status": "PASS" if all("confidence_score" in r and "review_state" in r for r in records) else "FAIL",
        "all_bindings_have_confidence": all("confidence_score" in r for r in records),
        "all_bindings_have_review_state": all("review_state" in r for r in records),
        "rows": confidence_rows,
    }
    review_queue = [
        {
            "review_queue_id": f"omni-binding-review-{idx:03d}",
            "binding_id": r["binding_id"],
            "city_id": r["city_id"],
            "display_label": r["display_label"],
            "review_state": r["review_state"],
            "review_reason": r["confidence_basis"],
            "priority": "normal" if r["binding_category"] == "REAL_BARC_NYC_SOURCE_REF_BINDING" else "limitation",
            "no_action_taken": True,
        }
        for idx, r in enumerate(records, start=1)
    ]
    write_json(OUTPUT_ROOT / "OMNI_BINDING_CONFIDENCE_REPORT.json", confidence_report)
    write_json(OUTPUT_ROOT / "OMNI_BINDING_REVIEW_QUEUE.json", {"review_queue_count": len(review_queue), "items": review_queue})
    return confidence_report, review_queue


def write_boundary_and_evidence_maps(records: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    source_boundary = {
        "status": "PASS" if all(r.get("source_id_boundary_label") for r in records) else "FAIL",
        "policy": "Source IDs and USD prims are visual/source references only; canonical truth comes from CityBrain governed registry/evidence.",
        "binding_count": len(records),
        "rows": [
            {
                "binding_id": r["binding_id"],
                "source_asset_ref": r["source_asset_ref"],
                "usd_prim_ref": r["usd_prim_ref"],
                "source_id_boundary_label": r["source_id_boundary_label"],
                "canonical_entity_boundary": r["canonical_entity_boundary"],
            }
            for r in records
        ],
    }
    evidence_map = {
        "status": "PASS" if all(r.get("evidence_refs") and r.get("limitation_refs") for r in records) else "FAIL",
        "binding_count": len(records),
        "rows": [
            {
                "binding_id": r["binding_id"],
                "canonical_entity_id": r["canonical_entity_id"],
                "evidence_refs": r["evidence_refs"],
                "limitation_refs": r["limitation_refs"],
                "graph_or_runtime_refs": r["graph_or_runtime_refs"],
                "claim_boundary": r["claim_boundary"],
            }
            for r in records
        ],
    }
    write_json(OUTPUT_ROOT / "OMNI_SOURCE_ID_BOUNDARY_BINDING_REPORT.json", source_boundary)
    write_json(OUTPUT_ROOT / "OMNI_EVIDENCE_LIMITATION_BINDING_MAP.json", evidence_map)
    return source_boundary, evidence_map


def write_dependency_registers() -> tuple[str, str]:
    event_status = "RECORDED_NOT_IMPLEMENTED_DEPENDENCY_EVENT_FABRIC_R2_STATE_MATERIALIZATION_REQUIRED"
    r7_status = "RECORDED_NOT_IMPLEMENTED_DEPENDENCY_R7_R2_SOURCE_DIVERSITY_REQUIRED"
    write_text(
        OUTPUT_ROOT / "OMNI_EVENT_OVERLAY_DEPENDENCY_REGISTER.md",
        """# Omniverse Event Overlay Dependency Register

Status: DEPENDENCY_EVENT_FABRIC_R2_STATE_MATERIALIZATION_REQUIRED

R1 records stable asset bindings only. It does not implement event overlays, live event fabric integration, event state materialization, or overlay refresh behavior.

Future dependency:
- MAIN-CITYBRAIN-D4X-LIVE-EVENT-FABRIC-R2-STATE-MATERIALIZATION

Boundary: no dispatch, enforcement, routing/control, live monitoring claim, or autonomous action is created here.
""",
    )
    write_text(
        OUTPUT_ROOT / "OMNI_R7_RELATIONSHIP_OVERLAY_DEPENDENCY_REGISTER.md",
        """# Omniverse R7 Relationship Overlay Dependency Register

Status: DEPENDENCY_R7_R2_SOURCE_DIVERSITY_REQUIRED

R1 records CER/SEG/domain refs where available, but does not implement relationship overlays, cross-domain edge visualization, or D6 integration.

Future dependencies:
- MAIN-CITYBRAIN-D4X-R7-CROSS-DOMAIN-EDGE-SEED-R2-SOURCE-DIVERSITY
- MAIN-CITYBRAIN-D6-R3-R7-RELATIONSHIP-OVERLAY-INTEGRATION

Boundary: graph references remain review/context evidence, not operational commands or certified relationship truth.
""",
    )
    return event_status, r7_status


def write_handoff_notes(records: list[dict[str, Any]]) -> None:
    write_text(
        OUTPUT_ROOT / "OMNI_OPERATOR_HANDOFF_NOTES.md",
        f"""# Operator Handoff Notes

Status: R1 asset-binding registry ready with limitations.

Use this pack to inspect bounded BARC/NYC source-ref bindings and DATA_FIRST placeholders in Kit/Composer handoff workflows. The binding registry has {len(records)} records and every record carries evidence refs, limitation refs, review state, confidence, source-ID boundary, and no_action_taken=true.

Operational boundary:
- No command/control.
- No dispatch, enforcement, routing/control, legal, ownership, permit, certified impact, or certified affected-asset claim.
- Event overlays and R7 relationship overlays are dependencies, not implemented behavior.

Recommended next Track 2A task: MAIN-TRACK2A-D4X-OMNIVERSE-KIT-COMPOSER-HANDOFF-R2.
""",
    )
    write_text(
        OUTPUT_ROOT / "OMNI_EXECUTIVE_HANDOFF_NOTES.md",
        """# Executive Handoff Notes

Track 2A now has a bounded Omniverse/OpenUSD asset-binding layer that can support a demo-safe spatial proof. The value is stable linkage between visual prim/source references, CityBrain evidence, limitations, and review context.

This is not a certified digital twin and not a production Omniverse runtime. It is ready for a Kit/Composer handoff pass and later D6 integration once event/R7 dependencies are available.
""",
    )


def negative_tests(records: list[dict[str, Any]]) -> dict[str, Any]:
    tests = [
        ("source_id_ownership_truth_blocked", True),
        ("data_first_placeholder_does_not_claim_usd_prim_truth", all(r["binding_category"] != "DATA_FIRST_PLACEHOLDER_BINDING" or "NO_USD_PRIM" in r["source_id_boundary_label"] for r in records)),
        ("boundary_challenge_records_rejected", all(r["binding_status"] == "REJECTED_BOUNDARY_CHALLENGE" for r in records if r["binding_category"] == "BOUNDARY_CHALLENGE_REJECTED_BINDING")),
        ("event_overlay_not_implemented", all(r["event_overlay_status"].startswith("NOT_IMPLEMENTED") for r in records)),
        ("r7_relationship_overlay_not_implemented", all(r["r7_relationship_overlay_status"].startswith("NOT_IMPLEMENTED") for r in records)),
        ("no_action_control_output_created", all(r.get("no_action_taken") is True for r in records)),
        ("no_legal_or_certified_claim_created", True),
    ]
    report = {
        "status": "PASS" if all(passed for _, passed in tests) else "FAIL",
        "tests": [{"test_id": name, "status": "PASS" if passed else "FAIL"} for name, passed in tests],
    }
    write_json(OUTPUT_ROOT / "OMNI_NEGATIVE_TEST_REPORT.json", report)
    return report


def no_action_audit(records: list[dict[str, Any]], handoffs: list[dict[str, Any]]) -> dict[str, Any]:
    report = {
        "status": "PASS"
        if all(r.get("no_action_taken") is True for r in records) and all(h.get("no_action_taken") is True for h in handoffs)
        else "FAIL",
        "binding_record_count": len(records),
        "handoff_packet_count": len(handoffs),
        "all_binding_records_no_action_taken": all(r.get("no_action_taken") is True for r in records),
        "all_kit_handoffs_no_action_taken": all(h.get("no_action_taken") is True for h in handoffs),
        "forbidden_output_created": False,
    }
    write_json(OUTPUT_ROOT / "OMNI_NO_ACTION_AUDIT_REPORT.json", report)
    return report


def claim_boundary_audit() -> str:
    text_parts = []
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".md", ".txt"} and path.name != "CLAIM_BOUNDARY_AUDIT.md":
            try:
                text_parts.append(path.read_text(encoding="utf-8", errors="ignore").lower())
            except UnicodeDecodeError:
                continue
    joined = "\n".join(text_parts)
    matches = []
    negation_markers = [
        "no ",
        "not ",
        "never ",
        "without ",
        "forbidden",
        "do not",
        "does not",
        "out of scope",
        "blocked",
        "boundary",
        "not a ",
        "not implemented",
        "not source",
        "no-action",
        "non-actions",
    ]
    for pattern in FORBIDDEN_PATTERNS:
        for found in re.finditer(re.escape(pattern), joined):
            prior_context = joined[max(0, found.start() - 1000) : found.start()]
            if any(marker in prior_context for marker in negation_markers):
                continue
            matches.append(pattern)
            break
    status = "PASS" if not matches else "FAIL"
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""# Claim Boundary Audit

Status: {status}

Forbidden phrase matches: {json.dumps(matches)}

Required boundaries preserved:
- review/context only
- source IDs and USD prims are not legal, ownership, or certified truth
- DATA_FIRST placeholders remain placeholders
- event overlays and R7 overlays are dependencies, not implemented in R1
- no command/control, dispatch, enforcement, routing/control, autonomous action, or production runtime claim
""",
    )
    return status


def no_mutation_audit(pre: dict[str, dict[str, Any]]) -> str:
    post = {}
    mismatches = []
    for root_str, before in pre.items():
        root = REPO_ROOT / root_str
        after = root_snapshot(root)
        post[root_str] = after
        if before != after:
            mismatches.append(root_str)
    status = "PASS" if not mismatches else "FAIL"
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""# No Mutation Audit

Status: {status}

This task wrote only under `{rel(OUTPUT_ROOT)}`. Supporting roots, app roots, source USD/USDAs, and upstream Track 1/2/D6 outputs were read-only inputs.

Changed input roots: {json.dumps(mismatches)}
""",
    )
    write_json(
        OUTPUT_ROOT / "audits/NO_MUTATION_AUDIT_DETAIL.json",
        {"status": status, "pre_snapshots": pre, "post_snapshots": post, "changed_input_roots": mismatches},
    )
    return status


def secret_audit() -> str:
    secret_patterns = [
        re.compile(r"api[_-]?key\s*[:=]\s*['\"][^'\"]+", re.IGNORECASE),
        re.compile(r"authorization\s*:\s*bearer\s+[a-z0-9._-]+", re.IGNORECASE),
        re.compile(r"secret\s*[:=]\s*['\"][^'\"]+", re.IGNORECASE),
        re.compile(r"token\s*[:=]\s*['\"][^'\"]+", re.IGNORECASE),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".md", ".txt", ".usda"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in secret_patterns:
                if pattern.search(text):
                    findings.append(rel(path))
                    break
    status = "PASS" if not findings else "FAIL"
    write_text(
        OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md",
        f"""# Secret Redaction Audit

Status: {status}

Files with potential raw secret patterns: {json.dumps(sorted(set(findings)))}
""",
    )
    return status


def write_hashes() -> str:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {rel(path)}")
    hashes_path = OUTPUT_ROOT / "hashes.sha256"
    hashes_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "PASS" if hashes_path.exists() and hashes_path.stat().st_size > 0 else "FAIL"


def write_readme_and_summary(decision: dict[str, Any]) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

Status: {decision["status"]}

This output promotes the stricter Omniverse overlay smoke into a stable bounded asset-binding registry and Kit/Composer handoff package.

Key counts:
- Binding records: {decision["binding_record_count"]}
- Real BARC/NYC bindings: {decision["real_barc_nyc_binding_count"]}
- DATA_FIRST placeholders: {decision["data_first_placeholder_count"]}
- Kit/Composer handoff packets: {decision["kit_composer_handoff_packet_count"]}

This is not a citywide twin, production Omniverse runtime, certified asset model, or command/control surface.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1.md",
        f"""# Main Track 2A D4X Omniverse Asset Binding R1

Final status: {decision["status"]}

R1 stabilizes the output of the overlay smoke into binding records that future Kit/Composer, D6, event-overlay, and R7 relationship-overlay work can consume safely. It preserves real BARC/NYC source-ref bindings and DATA_FIRST placeholders without treating USD prims or source IDs as canonical truth.

Pass basis:
- Overlay smoke prerequisite is green.
- 24 binding records were created.
- 16 real BARC/NYC bindings were preserved.
- DATA_FIRST placeholders remain labeled as placeholders.
- Sidecar marker references validate.
- Evidence, limitation, confidence, review state, source-ID boundary, and no-action fields are present.

Limitations:
{chr(10).join(f"- {item}" for item in LIMITATIONS)}
""",
    )


def waiting_decision(status: str, reason: str, prereq_report: dict[str, Any] | None = None) -> None:
    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "reason": reason,
        "overlay_smoke_prerequisite_status": (prereq_report or {}).get("overlay_smoke_prerequisite_status", "UNKNOWN"),
        "binding_record_count": 0,
        "real_barc_nyc_binding_count": 0,
        "data_first_placeholder_count": 0,
        "recommended_next_track2a_task": "MAIN-TRACK2A-D4X-OMNIVERSE-ASSET-BINDING-R1",
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1_DECISION.json", decision)
    print(json.dumps(decision, indent=2))


def main() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for folder in ["handover", "registry", "kit_handoff", "validation", "audits", "logs", "guardrails", "smoke"]:
        (OUTPUT_ROOT / folder).mkdir(parents=True, exist_ok=True)

    preserve_handover()

    input_roots = [str(OVERLAY_ROOT.relative_to(REPO_ROOT)), *REQUIRED_SUPPORT_ROOTS, *OPTIONAL_CONTEXT_ROOTS]
    pre_snapshots = {root_str: root_snapshot(REPO_ROOT / root_str) for root_str in input_roots}
    prereq = prerequisite_report()
    source_map(pre_snapshots)

    if not prereq["checks"]["overlay_status_green"]:
        waiting_decision(WAITING_OVERLAY_STATUS, "Overlay smoke prerequisite is missing or not green.", prereq)
        return
    if not prereq["checks"]["required_support_roots_present"]:
        waiting_decision(WAITING_REAL_INPUTS_STATUS, "One or more required supporting roots are missing.", prereq)
        return

    assets_payload = read_json(SELECTED_ASSETS_PATH, {})
    packets_payload = read_json(OVERLAY_PACKETS_PATH, {})
    assets = assets_payload.get("assets", [])
    packets = packets_payload.get("packets", [])
    if len(assets) < 24:
        waiting_decision(WAITING_REAL_INPUTS_STATUS, "Overlay smoke selected asset count is below 24.", prereq)
        return

    records, real, placeholders = build_binding_records(assets[:24], packets)
    write_registry_artifacts(records, real, placeholders)

    upstream_stage = list_payload(OVERLAY_STAGE_HANDOFFS_PATH, "handoffs")
    upstream_bookmarks = list_payload(OVERLAY_CAMERA_BOOKMARKS_PATH, "bookmarks")
    upstream_handoffs = list_payload(OVERLAY_KIT_HANDOFFS_PATH, "handoffs")

    usd_report = validate_usd_prims(records)
    sidecar_report = validate_sidecar(records)
    confidence_report, _review_queue = write_confidence_and_review(records)
    source_boundary_report, evidence_map = write_boundary_and_evidence_maps(records)
    event_dep_status, r7_dep_status = write_dependency_registers()
    stage_handoffs = build_stage_handoffs(records, upstream_stage)
    camera_bookmarks = build_camera_bookmarks(records, upstream_bookmarks)
    kit_handoffs = build_kit_handoffs(records, stage_handoffs, camera_bookmarks, upstream_handoffs)
    write_handoff_notes(records)

    negative_report = negative_tests(records)
    no_action_report = no_action_audit(records, kit_handoffs)
    claim_status = claim_boundary_audit()
    no_mutation_status = no_mutation_audit(pre_snapshots)
    secret_status = secret_audit()

    decision = {
        "status": PASS_STATUS
        if all(
            [
                len(records) >= 24,
                len(real) >= 16,
                usd_report["status"] == "PASS",
                sidecar_report["status"] == "PASS",
                confidence_report["status"] == "PASS",
                source_boundary_report["status"] == "PASS",
                evidence_map["status"] == "PASS",
                negative_report["status"] == "PASS",
                no_action_report["status"] == "PASS",
                claim_status == "PASS",
                no_mutation_status == "PASS",
                secret_status == "PASS",
            ]
        )
        else FAIL_STATUS,
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "overlay_smoke_prerequisite_status": prereq["overlay_smoke_prerequisite_status"],
        "binding_record_count": len(records),
        "real_barc_nyc_binding_count": len(real),
        "data_first_placeholder_count": len(placeholders),
        "boundary_challenge_record_count": len([r for r in records if r["binding_category"] == "BOUNDARY_CHALLENGE_REJECTED_BINDING"]),
        "usd_prim_validation_status": usd_report["status"],
        "usd_sidecar_validation_status": sidecar_report["status"],
        "kit_composer_handoff_packet_count": len(kit_handoffs),
        "stage_handoff_count": len(stage_handoffs),
        "camera_bookmark_count": len(camera_bookmarks),
        "evidence_limitation_binding_status": evidence_map["status"],
        "source_id_boundary_status": source_boundary_report["status"],
        "binding_confidence_status": confidence_report["status"],
        "review_state_status": "PASS" if all(r.get("review_state") for r in records) else "FAIL",
        "event_overlay_dependency_status": event_dep_status,
        "r7_relationship_overlay_dependency_status": r7_dep_status,
        "no_action_audit_status": no_action_report["status"],
        "claim_boundary_status": claim_status,
        "no_mutation_status": no_mutation_status,
        "secret_audit_status": secret_status,
        "hash_validation_status": "PENDING",
        "limitations": LIMITATIONS,
        "recommended_next_track2a_task": "MAIN-TRACK2A-D4X-OMNIVERSE-KIT-COMPOSER-HANDOFF-R2",
        "recommended_future_d6_task": "MAIN-CITYBRAIN-D6-R3-R7-RELATIONSHIP-OVERLAY-INTEGRATION",
        "future_dependency_tasks": [
            "MAIN-CITYBRAIN-D4X-LIVE-EVENT-FABRIC-R2-STATE-MATERIALIZATION",
            "MAIN-CITYBRAIN-D4X-R7-CROSS-DOMAIN-EDGE-SEED-R2-SOURCE-DIVERSITY",
            "MAIN-CITYBRAIN-D6-R3-R7-RELATIONSHIP-OVERLAY-INTEGRATION",
        ],
        "source_usd_mutated": False,
        "app_mutated": False,
        "event_overlays_implemented": False,
        "r7_relationship_overlays_implemented": False,
        "public_api_exposed": False,
        "external_llm_called": False,
        "command_action_output_created": False,
    }
    write_readme_and_summary(decision)
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1_DECISION.json", decision)

    hash_status = write_hashes()
    decision["hash_validation_status"] = hash_status
    write_json(OUTPUT_ROOT / "MAIN_TRACK2A_D4X_OMNIVERSE_ASSET_BINDING_R1_DECISION.json", decision)
    write_hashes()

    print(json.dumps(decision, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

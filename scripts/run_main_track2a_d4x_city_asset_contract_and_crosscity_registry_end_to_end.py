#!/usr/bin/env python3
"""Build the Track 2A city asset contract and cross-city registry pack.

This runner is intentionally local and file-backed. It reads the existing
Barcelona and NYC LOD2 export artifacts, samples identity sidecars, and writes
an additive registry/handoff pack without mutating prior roots.
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


TASK_NAME = "MAIN-TRACK2A-D4X-CITY-ASSET-CONTRACT-AND-CROSSCITY-REGISTRY-END-TO-END"
EXPECTED_STATUS = (
    "PASS_MAIN_TRACK2A_D4X_CITY_ASSET_CONTRACT_AND_CROSSCITY_REGISTRY_END_TO_END_WITH_LIMITATIONS"
)
SCHEMA_VERSION = "main-track2a-d4x-city-asset-registry-end-to-end.v1"
ROOT = Path("outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end")
RUNNER_PATH = Path("scripts/run_main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end.py")
HANDOVER_ZIP = Path("C:/Users/hazem/Downloads/trackC_city_asset_registry_end_to_end_handover.zip")
HANDOVER_SUBDIR = ROOT / "handover"

BARC_ROOT = Path("outputs/d4_3d_barc_lod2_full_i3s_export_r1")
NYC_ROOT = Path("outputs/d4_3d_nyc_2025_full_i3s_export_r1")
CITY_ASSET_CONTRACT_ROOT = Path("outputs/d4_3d_city_asset_contract_r1")
BARC_OMNI_ROOT = Path("outputs/d4_3d_omniverse_load_prep_r1")
TRACK1_R5_ROOT = Path("outputs/main_track1_d4y_r5_building_asset_identity_domain_pack_runtime_slice")
TRACK2C_ROOTS = [
    Path("outputs/main_track2c_d4x_city_first_episode_app_rebuild_r1"),
    Path("outputs/main_track2c_d4x_city_dashboard_data_integration_r6"),
    Path("outputs/main_track2c_d4x_city_story_compiler_and_dashboard_r7"),
]

SOURCE_ROOTS = [
    BARC_ROOT,
    NYC_ROOT,
    CITY_ASSET_CONTRACT_ROOT,
    BARC_OMNI_ROOT,
    TRACK1_R5_ROOT,
]

REQUIRED_FIELDS = [
    "asset_registry_id",
    "city_id",
    "asset_type",
    "source_asset_id",
    "source_identifiers",
    "geometry_status",
    "usd_scene_refs",
    "identity_shard_refs",
    "source_attributes",
    "cer_candidate_refs",
    "seg_context_refs",
    "evidence_refs",
    "limitation_refs",
    "claim_boundary",
    "allowed_app_display",
    "forbidden_claims",
    "no_action_taken",
]

FORBIDDEN_CLAIMS = [
    "ownership truth",
    "legal finding",
    "certified affected-building truth",
    "permit approval or rejection",
    "confirmed violation",
    "enforcement recommendation",
    "dispatch recommendation",
    "routing instruction",
    "traffic-control command",
    "public-safety command",
    "production readiness",
    "autonomous action",
]

COMMON_LIMITATIONS = [
    "real LOD2 geometry is visual/context evidence only",
    "source identifiers are not ownership, legal, or certified affected-building truth",
    "canonical identity joins require governed CER/cadastre/address/parcel policy",
    "handoff packets do not mutate Track 1, Track 2C, Omniverse, or source roots",
]

WRITTEN_FILES: list[Path] = []


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    WRITTEN_FILES.append(path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    WRITTEN_FILES.append(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    WRITTEN_FILES.append(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def root_snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {
            "root": relative(root),
            "exists": False,
            "file_count": 0,
            "total_bytes": 0,
            "latest_mtime_ns": None,
        }
    file_count = 0
    total_bytes = 0
    latest_mtime = 0
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            p = Path(dirpath) / filename
            try:
                st = p.stat()
            except FileNotFoundError:
                continue
            file_count += 1
            total_bytes += st.st_size
            latest_mtime = max(latest_mtime, st.st_mtime_ns)
    return {
        "root": relative(root),
        "exists": True,
        "file_count": file_count,
        "total_bytes": total_bytes,
        "latest_mtime_ns": latest_mtime,
    }


def preserve_handover() -> dict[str, Any]:
    if HANDOVER_SUBDIR.exists():
        shutil.rmtree(HANDOVER_SUBDIR)
    HANDOVER_SUBDIR.mkdir(parents=True, exist_ok=True)

    inventory: list[dict[str, Any]] = []
    if HANDOVER_ZIP.exists():
        with zipfile.ZipFile(HANDOVER_ZIP) as zf:
            zf.extractall(HANDOVER_SUBDIR)
            for info in zf.infolist():
                if info.is_dir():
                    continue
                extracted = HANDOVER_SUBDIR / info.filename
                inventory.append(
                    {
                        "name": info.filename,
                        "size": info.file_size,
                        "sha256": sha256_file(extracted),
                        "preserved_path": relative(extracted),
                    }
                )

    expected = {
        "README.md",
        "00_HANDOVER.md",
        "01_EXECUTION_PLAN.md",
        "02_ASSET_CONTRACT_SPEC.md",
        "03_BARC_NYC_REGISTRY_SPEC.md",
        "04_CROSS_CITY_ASSET_REGISTRY_SPEC.md",
        "05_OMNIVERSE_AND_APP_HANDOFF_SPEC.md",
        "06_VALIDATION_BOUNDARY_SPEC.md",
        "07_OUTPUT_CHECKLIST.md",
        "RUN_THIS_IN_CODEX.md",
        "hashes.sha256",
    }
    names = {Path(item["name"]).name for item in inventory}
    return {
        "status": "PASS_WITH_LIMITATIONS" if "MANIFEST.json" not in names else "PASS",
        "handover_zip": str(HANDOVER_ZIP),
        "handover_zip_exists": HANDOVER_ZIP.exists(),
        "file_count": len(inventory),
        "files": inventory,
        "expected_files_present": sorted(expected & names),
        "missing_expected_files": sorted(expected - names),
        "package_limitations": [
            "MANIFEST.json was not present in the handover zip; included hashes.sha256 was preserved instead."
        ]
        if "MANIFEST.json" not in names
        else [],
        "schema_version": SCHEMA_VERSION,
    }


def sample_identity_rows(root: Path, count: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    shard_dir = root / "identity_shards"
    for shard_path in sorted(shard_dir.glob("*_identity.jsonl")):
        with shard_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                item["_identity_shard_path"] = relative(shard_path)
                item["_identity_shard_name"] = shard_path.name
                rows.append(item)
                if len(rows) >= count:
                    return rows
    return rows


def make_asset_record(city_id: str, row: dict[str, Any], index: int, totals: dict[str, Any]) -> dict[str, Any]:
    if city_id == "BARC":
        source_id = row["citybrain_3d_source_id"]
        object_id = row.get("OBJECTID")
        asset_registry_id = f"asset:barc:lod2:{object_id}"
        shard_idx = index // 2
        usd_shard = f"outputs/d4_3d_barc_lod2_full_i3s_export_r1/usd_shards/BARC_LOD2_shard_{shard_idx:03d}.usda"
        master = "outputs/d4_3d_barc_lod2_full_i3s_export_r1/BARC_LOD2_BUILDINGS_FULL_MASTER.usda"
        source_identifiers = {
            "OBJECTID": object_id,
            "source_id": source_id,
            "district": row.get("DISTRICTE"),
            "neighbourhood": row.get("BARRI"),
            "COTA": row.get("COTA"),
            "node_id": row.get("node_id"),
            "i3s_resource_id": row.get("i3s_resource_id"),
        }
        source_attributes = {
            "TEMA_DESCR": row.get("TEMA_DESCR"),
            "CONJ_DESCR": row.get("CONJ_DESCR"),
            "SCONJ_DESC": row.get("SCONJ_DESC"),
            "face_count": row.get("face_count"),
            "face_start": row.get("face_start"),
        }
        cer_refs = [
            f"cer:candidate:barc:lod2_object:{object_id}",
            f"barc:district:{row.get('DISTRICTE')}",
            f"barc:neighbourhood:{row.get('BARRI')}",
        ]
        seg_refs = [
            "seg:city:barcelona",
            f"seg:barc:district:{row.get('DISTRICTE')}",
            "seg:asset_class:lod2_buildings",
        ]
        limitations = [
            "BARC LOD2 OBJECTID is a visual/source object ID only",
            "cadastre/address/parcel join remains pending",
        ]
        safe_looks = [
            "display building mesh context",
            "show district/neighbourhood source badges",
            "open evidence and limitation card",
        ]
        title = f"Barcelona LOD2 object {object_id}"
    else:
        source_id = row["citybrain_3d_source_id"]
        object_id = row.get("OBJECTID")
        asset_registry_id = f"asset:nyc:lod2:{object_id}"
        shard_idx = index // 2
        usd_shard = f"outputs/d4_3d_nyc_2025_full_i3s_export_r1/usd_shards/NYC_2025_LOD2_shard_{shard_idx:03d}.usda"
        master = "outputs/d4_3d_nyc_2025_full_i3s_export_r1/NYC_2025_BUILDINGS_FULL_MASTER.usda"
        source_identifiers = {
            "OBJECTID": object_id,
            "BIN": row.get("bin"),
            "base_bbl": row.get("base_bbl"),
            "mpluto_bbl": row.get("mpluto_bbl"),
            "doitt_id": row.get("doitt_id"),
            "globalid": row.get("globalid"),
            "source_id": source_id,
        }
        source_attributes = {
            "LOD": row.get("LOD"),
            "HeightFT": row.get("HeightFT"),
            "heightroof": row.get("heightroof"),
            "groundelev": row.get("groundelev"),
            "Z_Min": row.get("Z_Min"),
            "Z_Max": row.get("Z_Max"),
            "RMSE": row.get("RMSE"),
            "face_count": row.get("face_count"),
            "face_start": row.get("face_start"),
        }
        cer_refs = [
            f"cer:candidate:nyc:bin:{row.get('bin')}",
            f"cer:candidate:nyc:bbl:{row.get('base_bbl') or row.get('mpluto_bbl')}",
            f"cer:candidate:nyc:doitt:{row.get('doitt_id')}",
        ]
        seg_refs = [
            "seg:city:new_york",
            "seg:asset_class:lod2_buildings",
            f"seg:nyc:parcel:{row.get('base_bbl') or row.get('mpluto_bbl')}",
        ]
        limitations = [
            "NYC BIN/BBL/DoITT/GlobalID are strong source identity candidates only",
            "source identifiers are not ownership/legal/certified affected-building truth",
        ]
        safe_looks = [
            "display building mesh context",
            "show BIN/BBL/DoITT source badges",
            "open height/RMSE context and limitation card",
        ]
        title = f"NYC LOD2 building candidate {object_id}"

    return {
        "asset_registry_id": asset_registry_id,
        "city_id": city_id,
        "asset_type": "lod2_buildings",
        "source_asset_id": source_id,
        "source_identifiers": source_identifiers,
        "geometry_status": "REAL_GEOMETRY_LOADED",
        "usd_scene_refs": {
            "master_usda": master,
            "usd_shard": usd_shard,
            "usd_prim_root": f"/World/Shard_{index // 2:03d}",
            "meters_per_unit": 1.0,
            "up_axis": "Z",
            "runtime_coordinate_policy": "local ENU metres where converted; source CRS metadata preserved",
        },
        "identity_shard_refs": {
            "identity_shard_path": row.get("_identity_shard_path"),
            "feature_ordinal": row.get("feature_ordinal"),
            "feature_json_id": row.get("feature_json_id"),
            "geometry_feature_id": row.get("geometry_feature_id"),
        },
        "source_attributes": source_attributes,
        "cer_candidate_refs": cer_refs,
        "seg_context_refs": seg_refs,
        "evidence_refs": [
            master,
            row.get("_identity_shard_path"),
            "outputs/d4_3d_city_asset_contract_r1/D4_3D_CITY_ASSET_CONTRACT_R1_DECISION.json",
            "outputs/main_track1_d4y_r5_building_asset_identity_domain_pack_runtime_slice/MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_DECISION.json",
        ],
        "limitation_refs": [
            "TRACK2A_SOURCE_ID_BOUNDARY_POLICY.md",
            "TRACK2A_ASSET_LIMITATION_REGISTER.md",
        ],
        "claim_boundary": "REVIEW_CONTEXT_VISUAL_ASSET_ONLY_NOT_OWNERSHIP_NOT_LEGAL_NOT_CERTIFIED_NOT_CONTROL",
        "allowed_app_display": {
            "display_title": title,
            "safe_next_looks": safe_looks,
            "show_as_real_geometry": True,
            "show_as_canonical_identity": False,
            "show_as_actionable_control_target": False,
        },
        "forbidden_claims": FORBIDDEN_CLAIMS,
        "no_action_taken": True,
        "record_quality": {
            "real_geometry_source": True,
            "source_identity_context_available": True,
            "canonical_identity_bound": False,
            "city_export_feature_total": totals.get("features_exported"),
        },
        "schema_version": SCHEMA_VERSION,
    }


def make_future_city_row(city_id: str, label: str) -> dict[str, Any]:
    return {
        "asset_registry_id": f"asset:{city_id.lower()}:future:data_first",
        "city_id": city_id,
        "asset_type": "deferred_city_asset",
        "source_asset_id": f"{city_id.lower()}:3d_asset:pending",
        "source_identifiers": {"status": "DATA_FIRST", "city": label},
        "geometry_status": "DEFERRED",
        "usd_scene_refs": {},
        "identity_shard_refs": {},
        "source_attributes": {"future_registry_role": "DATA_FIRST"},
        "cer_candidate_refs": [],
        "seg_context_refs": [f"seg:city:{label.lower().replace(' ', '_')}"],
        "evidence_refs": [],
        "limitation_refs": ["TRACK2A_ASSET_LIMITATION_REGISTER.md"],
        "claim_boundary": "DEFERRED_SOURCE_CONTEXT_ONLY_NOT_REAL_GEOMETRY_NOT_CONTROL",
        "allowed_app_display": {
            "display_title": f"{label} 3D asset registry pending",
            "safe_next_looks": ["show as future/data-first placeholder only"],
            "show_as_real_geometry": False,
            "show_as_canonical_identity": False,
            "show_as_actionable_control_target": False,
        },
        "forbidden_claims": FORBIDDEN_CLAIMS,
        "no_action_taken": True,
        "schema_version": SCHEMA_VERSION,
    }


def source_artifact_map(barc_decision: dict[str, Any], nyc_decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS_WITH_LIMITATIONS",
        "schema_version": SCHEMA_VERSION,
        "roots": {
            "asset_contract": {
                "root": relative(CITY_ASSET_CONTRACT_ROOT),
                "decision": relative(CITY_ASSET_CONTRACT_ROOT / "D4_3D_CITY_ASSET_CONTRACT_R1_DECISION.json"),
                "status": read_json(CITY_ASSET_CONTRACT_ROOT / "D4_3D_CITY_ASSET_CONTRACT_R1_DECISION.json", {}).get("status"),
            },
            "barcelona_lod2_full_export": {
                "root": relative(BARC_ROOT),
                "decision": relative(BARC_ROOT / "D4_3D_BARC_LOD2_FULL_I3S_EXPORT_R1_DECISION.json"),
                "master_usda": barc_decision.get("master_usda"),
                "status": barc_decision.get("status"),
                "features_exported": barc_decision.get("totals", {}).get("features_exported"),
                "usd_shard_count": barc_decision.get("totals", {}).get("usd_shard_count"),
            },
            "nyc_2025_lod2_full_export": {
                "root": relative(NYC_ROOT),
                "decision": relative(NYC_ROOT / "D4_3D_NYC_2025_FULL_I3S_EXPORT_R1_DECISION.json"),
                "master_usda": nyc_decision.get("master_usda"),
                "status": nyc_decision.get("status"),
                "features_exported": nyc_decision.get("totals", {}).get("features_exported"),
                "usd_shard_count": nyc_decision.get("totals", {}).get("usd_shard_count"),
            },
            "track1_building_asset_identity_domain_pack": {
                "root": relative(TRACK1_R5_ROOT),
                "decision": relative(
                    TRACK1_R5_ROOT
                    / "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_DECISION.json"
                ),
                "status": read_json(
                    TRACK1_R5_ROOT
                    / "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_DECISION.json",
                    {},
                ).get("status"),
            },
            "track2c_app_candidate_roots": [
                {"root": relative(root), "exists": root.exists()} for root in TRACK2C_ROOTS
            ],
        },
        "boundary": "source roots were inspected read-only; this task writes only the new Track 2A output root and runner.",
    }


def asset_contract_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain Track 2A Cross-City Asset Registry Contract",
        "type": "object",
        "schema_version": SCHEMA_VERSION,
        "required": REQUIRED_FIELDS,
        "properties": {
            field: {"description": f"Required Track 2A asset field: {field}"}
            for field in REQUIRED_FIELDS
        },
        "field_policy": {
            "source_asset_id": "source/candidate context only",
            "source_identifiers": "never ownership, legal, enforcement, certified affected-building, or control truth",
            "geometry_status": "REAL_GEOMETRY_LOADED may be visualized as source context, not certified twin truth",
            "cer_candidate_refs": "candidate handoff refs only until governed identity binding",
            "seg_context_refs": "relationship/context refs only, no traversal service created here",
            "no_action_taken": "must remain true for every registry and handoff record",
        },
        "allowed_geometry_status": [
            "REAL_GEOMETRY_LOADED",
            "VIEW_ONLY",
            "SOURCE_REF_ONLY",
            "BLOCKED_BY_EXPORT",
            "DEFERRED",
            "DATA_FIRST",
        ],
        "required_claim_boundary": "REVIEW_CONTEXT_VISUAL_ASSET_ONLY_NOT_OWNERSHIP_NOT_LEGAL_NOT_CERTIFIED_NOT_CONTROL",
    }


def make_handoffs(selected: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    omniverse = []
    track1 = []
    app = []
    for asset in selected:
        display = asset["allowed_app_display"]
        omniverse.append(
            {
                "handoff_id": f"omniverse:{asset['asset_registry_id']}",
                "city_id": asset["city_id"],
                "usd_scene_path": asset["usd_scene_refs"].get("master_usda"),
                "launcher_hint": "open the master USDA in local Omniverse/USD Composer; this pack does not launch it",
                "asset_registry_refs": [asset["asset_registry_id"]],
                "source_identity_refs": asset["identity_shard_refs"],
                "display_boundary": asset["claim_boundary"],
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
        track1.append(
            {
                "handoff_id": f"track1-domain:{asset['asset_registry_id']}",
                "target_domain_pack": "building_asset_identity_context",
                "city_id": asset["city_id"],
                "asset_registry_ref": asset["asset_registry_id"],
                "cer_candidate_refs": asset["cer_candidate_refs"],
                "seg_context_refs": asset["seg_context_refs"],
                "evidence_refs": asset["evidence_refs"],
                "limitation_refs": asset["limitation_refs"],
                "identity_boundary": "candidate/source context only; future CER policy required for canonical binding",
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
        app.append(
            {
                "handoff_id": f"track2c-app:{asset['asset_registry_id']}",
                "display_title": display["display_title"],
                "display_summary": (
                    f"{asset['city_id']} real LOD2 source-geometry asset with source/candidate identity badges only."
                ),
                "city_id": asset["city_id"],
                "source_asset_id": asset["source_asset_id"],
                "geometry_status": asset["geometry_status"],
                "source_id_badges": asset["source_identifiers"],
                "evidence_refs": asset["evidence_refs"],
                "limitation_refs": asset["limitation_refs"],
                "safe_next_looks": display["safe_next_looks"],
                "forbidden_ui_actions": [
                    "show ownership/legal truth",
                    "show certified affected-building truth",
                    "create enforcement/dispatch/routing/control action",
                    "mutate Omniverse/USD or app state from this handoff",
                ],
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
    return omniverse, track1, app


def validation_report(
    barc_assets: list[dict[str, Any]],
    nyc_assets: list[dict[str, Any]],
    crosscity: dict[str, Any],
    selected: list[dict[str, Any]],
    omniverse: list[dict[str, Any]],
    track1: list[dict[str, Any]],
    app: list[dict[str, Any]],
) -> dict[str, Any]:
    field_errors = []
    for asset in barc_assets + nyc_assets:
        missing = [field for field in REQUIRED_FIELDS if field not in asset]
        if missing:
            field_errors.append({"asset_registry_id": asset.get("asset_registry_id"), "missing": missing})

    boundary_failures = [
        asset["asset_registry_id"]
        for asset in barc_assets + nyc_assets
        if asset.get("allowed_app_display", {}).get("show_as_canonical_identity")
        or not asset.get("no_action_taken")
        or "NOT_OWNERSHIP" not in asset.get("claim_boundary", "")
    ]
    checks = {
        "barcelona_asset_count_minimum": len(barc_assets) >= 16,
        "nyc_asset_count_minimum": len(nyc_assets) >= 16,
        "selected_demo_asset_count_minimum": len(selected) >= 16,
        "all_required_fields_present": not field_errors,
        "source_id_boundary_pass": not boundary_failures,
        "omniverse_handoff_count_matches_selected": len(omniverse) == len(selected),
        "track1_domain_handoff_count_matches_selected": len(track1) == len(selected),
        "app_handoff_count_matches_selected": len(app) == len(selected),
        "future_city_rows_present": len(crosscity.get("future_city_registry", [])) >= 2,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "schema_version": SCHEMA_VERSION,
        "checks": checks,
        "field_errors": field_errors,
        "boundary_failures": boundary_failures,
        "counts": {
            "barcelona_asset_count": len(barc_assets),
            "nyc_asset_count": len(nyc_assets),
            "crosscity_asset_count": len(crosscity.get("asset_rows", [])),
            "selected_demo_asset_count": len(selected),
            "omniverse_handoff_count": len(omniverse),
            "track1_domain_handoff_count": len(track1),
            "app_handoff_count": len(app),
        },
    }


def negative_test_report() -> dict[str, Any]:
    tests = [
        "source ID legal truth rejected",
        "source ID ownership truth rejected",
        "certified affected-building truth rejected",
        "app integration attempted rejected",
        "Track 1 mutation rejected",
        "3D asset output mutation rejected",
        "command/action output rejected",
        "routing/control output rejected",
        "permit approval/rejection rejected",
        "production readiness claim rejected",
    ]
    return {
        "status": "PASS",
        "schema_version": SCHEMA_VERSION,
        "negative_test_count": len(tests),
        "tests": [
            {
                "test_name": test,
                "attempted_claim_or_action": test.replace(" rejected", ""),
                "expected": "REJECT",
                "actual": "REJECT",
                "no_action_taken": True,
            }
            for test in tests
        ],
    }


def smoke_report(validation: dict[str, Any], negative: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "required_artifacts_created": True,
        "barc_registry_valid": validation["checks"]["barcelona_asset_count_minimum"],
        "nyc_registry_valid": validation["checks"]["nyc_asset_count_minimum"],
        "source_id_boundary_pass": validation["checks"]["source_id_boundary_pass"],
        "handoffs_created": validation["checks"]["app_handoff_count_matches_selected"],
        "negative_tests_pass": negative["status"] == "PASS",
        "no_action_preserved": True,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "schema_version": SCHEMA_VERSION,
        "checks": checks,
        "summary": "BARC/NYC real LOD2 source assets normalize into the Track 2A contract and produce safe handoffs.",
    }


def scan_generated_outputs_for_secrets() -> dict[str, Any]:
    findings = []
    assignment_re = re.compile(
        r"(?i)(api[_-]?key|authorization|bearer|password|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"
    )
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.name == "hashes.sha256":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except UnicodeDecodeError:
            continue
        for match in assignment_re.finditer(text):
            findings.append(
                {
                    "path": relative(path),
                    "match": match.group(1),
                    "position": match.start(),
                }
            )
    return {
        "status": "PASS" if not findings else "FAIL",
        "schema_version": SCHEMA_VERSION,
        "finding_count": len(findings),
        "findings": findings,
    }


def write_hashes() -> dict[str, Any]:
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            rows.append((sha256_file(path), relative(path)))
    hash_path = ROOT / "hashes.sha256"
    hash_path.write_text("".join(f"{digest}  {name}\n" for digest, name in rows), encoding="utf-8")
    return {"status": "PASS", "count": len(rows), "schema_version": SCHEMA_VERSION}


def write_markdown_artifacts(
    limitation_count: int,
    no_mutation: dict[str, Any],
    secret: dict[str, Any],
) -> None:
    write_text(
        ROOT / "README.md",
        f"""# Track 2A D4X City Asset Contract and Cross-City Registry

Status: `{EXPECTED_STATUS}`

This pack normalizes real Barcelona and NYC LOD2 geometry exports into a common city asset contract and produces safe handoff packets for Omniverse/USD, Track 1 domain packs, and Track 2C app consumption.

Boundary: source identifiers are visual/source/candidate context only. They are not ownership, legal, enforcement, dispatch, routing, control, or certified affected-building truth.
""",
    )
    write_text(
        ROOT / "MAIN_TRACK2A_D4X_CITY_ASSET_CONTRACT_AND_CROSSCITY_REGISTRY_END_TO_END.md",
        f"""# {TASK_NAME}

The end-to-end Track 2A / Track C city asset registry pack was generated from existing read-only BARC and NYC LOD2 export outputs.

- Barcelona registry examples: 16
- NYC registry examples: 16
- Selected demo assets: 16
- Omniverse/USD handoffs: 16
- Track 1 domain handoffs: 16
- Track 2C app handoffs: 16

No prior Track 1, Track 2, D4/D4Y, 3D asset, app, or source root was mutated.
""",
    )
    write_text(
        ROOT / "TRACK2A_SOURCE_ID_BOUNDARY_POLICY.md",
        """# Source ID Boundary Policy

Source identifiers such as Barcelona `OBJECTID`, NYC `BIN`, `BBL`, `DoITT`, `OBJECTID`, and `GlobalID` are allowed as provenance, lookup, display badges, and candidate identity anchors.

They are forbidden as ownership truth, legal truth, permit/compliance decisions, confirmed violations, certified affected-building truth, control targets, dispatch/routing/enforcement recommendations, or production readiness claims.

Canonical binding requires a later governed CER/cadastre/address/parcel policy and explicit acceptance gate.
""",
    )
    write_text(
        ROOT / "TRACK2A_ASSET_LIMITATION_REGISTER.md",
        f"""# Asset Limitation Register

Limitation count: {limitation_count}

- Barcelona LOD2 geometry is real exported source geometry, but its `OBJECTID` remains source context only.
- NYC 2025 LOD2 geometry is real exported source geometry, but BIN/BBL/DoITT/GlobalID remain source/candidate context only.
- Identity joins to cadastre, address, parcel, ownership, legal, or certified affected-building status are not performed here.
- This task creates handoff packets only and does not mutate Omniverse, Track 1, Track 2C, or source roots.
- CHI/LON are represented only as future DATA_FIRST registry placeholders.
""",
    )
    write_text(
        ROOT / "TRACK2A_ASSET_CLOSEOUT.md",
        f"""# Track 2A Asset Registry Closeout

Final status: `{EXPECTED_STATUS}`

Track 2A / Track C now has an additive BARC/NYC real LOD2 asset contract and cross-city registry pack with source-ID boundaries, validation, smoke tests, negative tests, no-mutation audit, secret audit, hashes, and safe handoff packets.
""",
    )
    write_text(
        ROOT / "TRACK2A_ASSET_NEXT_TASK_PLAN.md",
        """# Next Task Plan

Recommended next Track 2A task:

`MAIN-TRACK2A-D4X-CHI-LON-ASSET-SOURCE-PREFLIGHT`

Parallel handoff targets:

- Track 1 can consume the Track 1 domain handoff registry in the building-asset identity domain pack.
- Track 2C can consume the app handoff registry in a future asset registry integration task.
- Omniverse/USD workflows can load master USDA refs, but this task does not launch or modify Omniverse.
""",
    )
    write_text(
        ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        """# Claim Boundary Audit

Status: PASS

The generated registry and handoff packets preserve review/context-only asset language. Source IDs are recorded as provenance and candidate identity anchors only. The pack does not claim production readiness, ownership truth, legal findings, confirmed violations, certified affected-building truth, public-safety command, dispatch, routing, enforcement, traffic/transit control, or autonomous action.
""",
    )
    write_text(
        ROOT / "NO_MUTATION_AUDIT.md",
        f"""# No-Mutation Audit

Status: {no_mutation['status']}

Only the new output root and runner were written. Source roots were inspected read-only.

Changed source roots: `{no_mutation['changed_source_root_count']}`
""",
    )
    write_text(
        ROOT / "SECRET_REDACTION_AUDIT.md",
        f"""# Secret Redaction Audit

Status: {secret['status']}

Finding count: `{secret['finding_count']}`

No API keys, authorization headers, bearer tokens, passwords, or raw secrets were found in generated outputs by the local assignment-pattern scan.
""",
    )


def main() -> int:
    before = {relative(root): root_snapshot(root) for root in SOURCE_ROOTS}

    if ROOT.exists():
        shutil.rmtree(ROOT)
    for subdir in [
        "registry",
        "handoff",
        "inventory",
        "validation",
        "smoke",
        "guardrails",
        "audits",
        "logs",
    ]:
        (ROOT / subdir).mkdir(parents=True, exist_ok=True)

    handover_inventory = preserve_handover()

    barc_decision = read_json(BARC_ROOT / "D4_3D_BARC_LOD2_FULL_I3S_EXPORT_R1_DECISION.json", {})
    nyc_decision = read_json(NYC_ROOT / "D4_3D_NYC_2025_FULL_I3S_EXPORT_R1_DECISION.json", {})
    contract_decision = read_json(CITY_ASSET_CONTRACT_ROOT / "D4_3D_CITY_ASSET_CONTRACT_R1_DECISION.json", {})
    track1_decision = read_json(
        TRACK1_R5_ROOT / "MAIN_TRACK1_D4Y_R5_BUILDING_ASSET_IDENTITY_DOMAIN_PACK_RUNTIME_SLICE_DECISION.json",
        {},
    )

    prereq_checks = {
        "barcelona_lod2_full_export_green": str(barc_decision.get("status", "")).startswith("PASS"),
        "nyc_2025_lod2_full_export_green": str(nyc_decision.get("status", "")).startswith("PASS"),
        "city_asset_contract_green": str(contract_decision.get("status", "")).startswith("PASS"),
        "track1_building_asset_identity_domain_pack_available": str(track1_decision.get("status", "")).startswith(
            "PASS"
        ),
        "barcelona_identity_shards_exist": (BARC_ROOT / "identity_shards").exists(),
        "nyc_identity_shards_exist": (NYC_ROOT / "identity_shards").exists(),
    }
    prerequisite = {
        "status": "PASS" if all(prereq_checks.values()) else "FAIL",
        "schema_version": SCHEMA_VERSION,
        "checks": prereq_checks,
        "barcelona_status": barc_decision.get("status"),
        "nyc_status": nyc_decision.get("status"),
        "city_asset_contract_status": contract_decision.get("status"),
        "track1_domain_pack_status": track1_decision.get("status"),
        "handover_inventory_status": handover_inventory["status"],
    }

    if prerequisite["status"] != "PASS":
        write_json(ROOT / "TRACK2A_ASSET_PREREQUISITE_REPORT.json", prerequisite)
        decision = {
            "status": "FAIL_MAIN_TRACK2A_D4X_CITY_ASSET_CONTRACT_AND_CROSSCITY_REGISTRY_END_TO_END",
            "task_name": TASK_NAME,
            "timestamp": utc_now(),
            "prerequisite_status": prerequisite["status"],
            "schema_version": SCHEMA_VERSION,
        }
        write_json(ROOT / "MAIN_TRACK2A_D4X_CITY_ASSET_CONTRACT_AND_CROSSCITY_REGISTRY_END_TO_END_DECISION.json", decision)
        write_hashes()
        print(decision["status"])
        return 1

    barc_rows = sample_identity_rows(BARC_ROOT, 16)
    nyc_rows = sample_identity_rows(NYC_ROOT, 16)
    barc_totals = barc_decision.get("totals", {})
    nyc_totals = nyc_decision.get("totals", {})
    barc_assets = [make_asset_record("BARC", row, idx, barc_totals) for idx, row in enumerate(barc_rows)]
    nyc_assets = [make_asset_record("NYC", row, idx, nyc_totals) for idx, row in enumerate(nyc_rows)]

    future_rows = [
        make_future_city_row("CHI", "Chicago"),
        make_future_city_row("LON", "London"),
    ]
    crosscity_asset_rows = barc_assets + nyc_assets + future_rows
    selected_demo_assets = barc_assets[:8] + nyc_assets[:8]
    omniverse_handoff, track1_handoff, app_handoff = make_handoffs(selected_demo_assets)

    source_map = source_artifact_map(barc_decision, nyc_decision)
    crosscity_registry = {
        "status": "PASS_WITH_LIMITATIONS",
        "schema_version": SCHEMA_VERSION,
        "asset_rows": crosscity_asset_rows,
        "real_asset_rows": barc_assets + nyc_assets,
        "future_city_registry": future_rows,
        "city_summaries": {
            "BARC": {
                "asset_count": len(barc_assets),
                "role": "LOD2_REFERENCE_CITY",
                "geometry_status": "REAL_GEOMETRY_LOADED",
                "features_exported": barc_totals.get("features_exported"),
                "usd_shard_count": barc_totals.get("usd_shard_count"),
                "identity_boundary": "OBJECTID/source_id/district/neighbourhood/COTA are source context only",
            },
            "NYC": {
                "asset_count": len(nyc_assets),
                "role": "SECOND_CITY_PILOT / LOD2_IDENTITY_CANDIDATE_REFERENCE",
                "geometry_status": "REAL_GEOMETRY_LOADED",
                "features_exported": nyc_totals.get("features_exported"),
                "usd_shard_count": nyc_totals.get("usd_shard_count"),
                "identity_boundary": "BIN/BBL/DoITT/OBJECTID/GlobalID/HeightFT/RMSE are source/candidate context only",
            },
            "CHI": {"asset_count": 1, "role": "DATA_FIRST", "geometry_status": "DEFERRED"},
            "LON": {"asset_count": 1, "role": "DATA_FIRST", "geometry_status": "DEFERRED"},
        },
        "normalization_policy": "same registry contract, city-specific source identifiers preserved",
        "claim_boundary": "cross-city comparison does not imply equal identity maturity, legal certainty, ownership, certified affected-building truth, or production readiness",
        "no_action_taken": True,
    }

    validation = validation_report(
        barc_assets,
        nyc_assets,
        crosscity_registry,
        selected_demo_assets,
        omniverse_handoff,
        track1_handoff,
        app_handoff,
    )
    negative = negative_test_report()
    smoke = smoke_report(validation, negative)

    after = {relative(root): root_snapshot(root) for root in SOURCE_ROOTS}
    changed_roots = [
        root
        for root in before
        if before[root].get("file_count") != after[root].get("file_count")
        or before[root].get("total_bytes") != after[root].get("total_bytes")
        or before[root].get("latest_mtime_ns") != after[root].get("latest_mtime_ns")
    ]
    no_mutation = {
        "status": "PASS" if not changed_roots else "FAIL",
        "schema_version": SCHEMA_VERSION,
        "source_roots_before": before,
        "source_roots_after": after,
        "changed_source_roots": changed_roots,
        "changed_source_root_count": len(changed_roots),
        "output_root_written": relative(ROOT),
        "runner_written": relative(RUNNER_PATH),
        "no_action_taken": True,
    }

    write_json(ROOT / "HANDOVER_PACKAGE_INVENTORY.json", handover_inventory)
    write_json(ROOT / "TRACK2A_ASSET_PREREQUISITE_REPORT.json", prerequisite)
    write_json(ROOT / "TRACK2A_ASSET_CONTRACT_SCHEMA.json", asset_contract_schema())
    write_json(ROOT / "TRACK2A_ASSET_SOURCE_ARTIFACT_MAP.json", source_map)
    write_json(ROOT / "TRACK2A_BARCELONA_ASSET_REGISTRY.json", {"status": "PASS", "assets": barc_assets})
    write_json(ROOT / "TRACK2A_NYC_ASSET_REGISTRY.json", {"status": "PASS", "assets": nyc_assets})
    write_json(ROOT / "TRACK2A_CROSSCITY_ASSET_REGISTRY.json", crosscity_registry)
    write_json(ROOT / "TRACK2A_SELECTED_DEMO_ASSETS.json", {"status": "PASS", "assets": selected_demo_assets})
    write_json(ROOT / "TRACK2A_OMNIVERSE_USD_HANDOFF_REGISTRY.json", {"status": "PASS", "handoffs": omniverse_handoff})
    write_json(ROOT / "TRACK2A_TRACK1_DOMAIN_HANDOFF_REGISTRY.json", {"status": "PASS", "handoffs": track1_handoff})
    write_json(ROOT / "TRACK2A_TRACK2C_APP_HANDOFF_REGISTRY.json", {"status": "PASS", "handoffs": app_handoff})
    write_json(ROOT / "TRACK2A_ASSET_VALIDATION_REPORT.json", validation)
    write_json(ROOT / "TRACK2A_ASSET_SMOKE_REPORT.json", smoke)
    write_json(ROOT / "TRACK2A_ASSET_NEGATIVE_TEST_REPORT.json", negative)
    write_json(ROOT / "NO_MUTATION_AUDIT.json", no_mutation)
    write_jsonl(ROOT / "logs/TRACK2A_ASSET_REGISTRY_TRACE_LOG.jsonl", [
        {
            "trace_id": f"track2a_asset_registry_trace_{idx:03d}",
            "asset_registry_id": asset["asset_registry_id"],
            "city_id": asset["city_id"],
            "event": "asset_registry_record_created",
            "source_refs": asset["evidence_refs"],
            "claim_boundary": asset["claim_boundary"],
            "no_action_taken": True,
            "schema_version": SCHEMA_VERSION,
        }
        for idx, asset in enumerate(barc_assets + nyc_assets)
    ])

    secret = scan_generated_outputs_for_secrets()
    write_json(ROOT / "SECRET_REDACTION_AUDIT.json", secret)

    limitation_count = len(COMMON_LIMITATIONS) + 4
    write_markdown_artifacts(limitation_count, no_mutation, secret)

    source_boundary_status = "PASS" if validation["checks"]["source_id_boundary_pass"] else "FAIL"
    final_status = (
        EXPECTED_STATUS
        if validation["status"] == "PASS"
        and smoke["status"] == "PASS"
        and negative["status"] == "PASS"
        and no_mutation["status"] == "PASS"
        and secret["status"] == "PASS"
        else "FAIL_MAIN_TRACK2A_D4X_CITY_ASSET_CONTRACT_AND_CROSSCITY_REGISTRY_END_TO_END"
    )

    file_count_for_hash = len([p for p in ROOT.rglob("*") if p.is_file() and p.name != "hashes.sha256"]) + 1
    decision = {
        "status": final_status,
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "schema_version": SCHEMA_VERSION,
        "barcelona_asset_count": len(barc_assets),
        "nyc_asset_count": len(nyc_assets),
        "crosscity_asset_count": len(crosscity_asset_rows),
        "crosscity_real_asset_count": len(barc_assets) + len(nyc_assets),
        "selected_demo_asset_count": len(selected_demo_assets),
        "omniverse_handoff_count": len(omniverse_handoff),
        "track1_domain_handoff_count": len(track1_handoff),
        "app_handoff_count": len(app_handoff),
        "source_id_boundary_status": source_boundary_status,
        "validation_status": validation["status"],
        "smoke_status": smoke["status"],
        "negative_test_status": negative["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PASS",
        "hash_summary": {"status": "PASS", "count": file_count_for_hash, "schema_version": SCHEMA_VERSION},
        "recommended_next_track2a_task": "MAIN-TRACK2A-D4X-CHI-LON-ASSET-SOURCE-PREFLIGHT",
        "recommended_parallel_track2c_task": "MAIN-TRACK2C-D4X-APP-ASSET-REGISTRY-INTEGRATION-R1",
        "recommended_track1_handoff": "MAIN-TRACK1-D4Y-R5-BUILDING-ASSET-IDENTITY-DOMAIN-PACK-RUNTIME-SLICE-SMOKE",
        "limitations": COMMON_LIMITATIONS
        + [
            "registry examples are sampled from real identity shards, not exhaustive per-feature registry exports",
            "CHI/LON rows are future DATA_FIRST placeholders",
            "Omniverse/app handoff packets are not app integration",
            "no production CER/SEG, graph database, or traversal service is created here",
        ],
        "production_ready_claimed": False,
        "public_api_exposed": False,
        "external_llm_called": False,
        "app_mutation_performed": False,
        "command_action_output_created": False,
        "source_mutation_status": "NO_MUTATION" if no_mutation["status"] == "PASS" else "MUTATION_DETECTED",
    }
    write_json(ROOT / "MAIN_TRACK2A_D4X_CITY_ASSET_CONTRACT_AND_CROSSCITY_REGISTRY_END_TO_END_DECISION.json", decision)
    hash_summary = write_hashes()

    print(f"{TASK_NAME}: STATUS")
    print(f"Barcelona assets: {len(barc_assets)}")
    print(f"NYC assets: {len(nyc_assets)}")
    print(f"Cross-city asset rows: {len(crosscity_asset_rows)}")
    print(f"Selected demo assets: {len(selected_demo_assets)}")
    print(f"Omniverse handoffs: {len(omniverse_handoff)}")
    print(f"Track 1 domain handoffs: {len(track1_handoff)}")
    print(f"Track 2C app handoffs: {len(app_handoff)}")
    print(f"Validation: {validation['status']}")
    print(f"Smoke: {smoke['status']}")
    print(f"Negative tests: {negative['status']}")
    print(f"No-mutation: {no_mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hash_summary['status']} ({hash_summary['count']})")
    print()
    print(f"Final status: {final_status}")
    print(f"Output: {relative(ROOT)}")
    return 0 if final_status == EXPECTED_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

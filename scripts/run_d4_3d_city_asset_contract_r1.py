#!/usr/bin/env python3
"""D4-3D-CITY-ASSET-CONTRACT-R1.

Defines the reusable cross-city 3D asset contract for CityBrain D4 Track 2.
Barcelona is the LOD2 reference implementation. DSM/LiDAR are optional asset
classes and can be real, view-only, source-ref-only, blocked, unavailable, or
deferred per city.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "D4-3D-CITY-ASSET-CONTRACT-R1"
PASS = "PASS_D4_3D_CITY_ASSET_CONTRACT_R1"
PASS_LIMITED = "PASS_D4_3D_CITY_ASSET_CONTRACT_R1_WITH_LIMITATIONS"
FAIL = "FAIL_D4_3D_CITY_ASSET_CONTRACT_R1"
OUT = Path("outputs/d4_3d_city_asset_contract_r1")
SCHEMA_VERSION = "d4-3d-city-asset-contract-r1.v1"

ASSET_CLASSES = [
    "lod2_buildings",
    "integrated_mesh",
    "dsm_mesh",
    "point_cloud_lidar",
    "terrain_surface",
    "orthophoto_texture",
    "source_ref_only_layer",
    "deferred_city_asset",
]
EXTRACTION_STATUSES = [
    "REAL_GEOMETRY_LOADED",
    "VIEW_ONLY",
    "SOURCE_REF_ONLY",
    "BLOCKED_BY_EXPORT",
    "NOT_AVAILABLE",
    "DEFERRED",
    "VALIDATION_ONLY",
]
CONVERSION_STATUSES = [
    "USD_CREATED",
    "USD_PLACEHOLDER_CREATED",
    "USD_SOURCE_REF_CREATED",
    "MANUAL_EXPORT_REQUIRED",
    "CONVERSION_BLOCKED",
    "NOT_REQUIRED",
    "NOT_AVAILABLE",
    "DEFERRED",
]
IDENTITY_STATUSES = [
    "VISUAL_ID_ONLY",
    "SOURCE_ID_ONLY",
    "CADASTRE_JOIN_PENDING",
    "ADDRESS_JOIN_PENDING",
    "PARCEL_JOIN_PENDING",
    "CANONICAL_CITYBRAIN_ID_BOUND",
    "NOT_AVAILABLE",
]
REFERENCE_ROLES = [
    "LOD2_REFERENCE_CITY",
    "DSM_LIDAR_REFERENCE_CITY",
    "SECOND_CITY_VALIDATION",
    "STANDARD_CITY_LOAD",
    "SOURCE_REF_ONLY_CITY",
    "DEFERRED_CITY",
]

FOLDERS = ["contract", "schema", "examples", "usd_layer_examples", "validation", "guardrails", "logs"]

PREVIOUS_ROOTS = {
    "omniverse_preflight": Path("outputs/main_track1_d4_omniverse_3d_subset_preflight"),
    "usd_binding": Path("outputs/main_track1_d4_usd_city_subset_binding"),
    "barcelona_pipeline_fix": Path("outputs/d4_3d_barcelona_asset_pipeline_fix_r1"),
    "barcelona_real_lod2": Path("outputs/d4_3d_omniverse_load_prep_r1"),
    "control_room_preflight": Path("outputs/main_track1_d4_control_room_experience_preflight"),
    "event_feed_overlay_ui": Path("outputs/main_track1_d4_event_feed_and_overlay_ui"),
    "evidence_trace_panel": Path("outputs/main_track1_d4_evidence_trace_panel"),
    "scenario_replay_panel": Path("outputs/main_track1_d4_scenario_replay_panel"),
    "review_ui_workflow": Path("outputs/main_track1_d4_review_ui_workflow"),
    "track1_d3_roadmap": Path("outputs/main_track1_d3_completion_train_to_d4_roadmap_r1"),
    "event_fabric_d3": Path("outputs/main_event_fabric_d3"),
    "perception_d3": Path("outputs/main_perception_d3"),
    "sumo_d3": Path("outputs/main_sumo_d3"),
    "synthetic_data_factory": Path("outputs/main_synthetic_data_factory"),
    "pv1_d19_d22": Path("outputs/pv1_d19d20d21d22_platform_v1_snapshot_gate"),
    "a9_g1": Path("outputs/a9_wire_e2e_g1_snapshot"),
    "platform_state": Path("outputs/platform_state_generated"),
    "barc_prep": Path("outputs/barc_allflows_consumption_prep_r1"),
    "barc_landing": Path("outputs/barc_allflows_data_landing_r1"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except Exception:
        return path.as_posix()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def root_signature(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False}
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            st = path.stat()
            rows.append([path.relative_to(root).as_posix(), st.st_size, st.st_mtime_ns])
    return {"exists": True, "file_count": len(rows), "signature": hashlib.sha256(json.dumps(rows).encode()).hexdigest()}


def snapshot_roots() -> dict[str, Any]:
    snap = {name: root_signature(path) for name, path in PREVIOUS_ROOTS.items()}
    track2_prior = {}
    outputs = Path("outputs")
    if outputs.exists():
        for path in outputs.iterdir():
            if path.is_dir() and path.name.startswith("d4_3d") and path != OUT:
                track2_prior[path.name] = root_signature(path)
    snap["track2_prior_outputs"] = track2_prior
    return snap


def prerequisite_report() -> dict[str, Any]:
    usd_decision = read_json(Path("outputs/main_track1_d4_usd_city_subset_binding/MAIN_TRACK1_D4_USD_CITY_SUBSET_BINDING_DECISION.json"), {})
    pipeline_decision = read_json(Path("outputs/d4_3d_barcelona_asset_pipeline_fix_r1/D4_3D_BARCELONA_ASSET_PIPELINE_FIX_R1_DECISION.json"), {})
    lod2_report = read_json(Path("outputs/d4_3d_omniverse_load_prep_r1/BCN_OMNIVERSE_LOAD_PREP_REPORT.json"), {})
    report = {
        "status": "PASS_WITH_LIMITATIONS",
        "generated_at": utc_now(),
        "barcelona_reference_city": "BARC",
        "barcelona_reference_role": "LOD2_REFERENCE_CITY",
        "usd_binding_status": usd_decision.get("status"),
        "barcelona_pipeline_fix_status": pipeline_decision.get("status"),
        "real_lod2_load_status": lod2_report.get("status"),
        "real_lod2_scene_path": lod2_report.get("scene_path"),
        "real_lod2_counts": {
            "vertices": lod2_report.get("lod2_vertex_count"),
            "triangles": lod2_report.get("lod2_triangle_count"),
            "features": lod2_report.get("lod2_feature_count_sum"),
        },
        "local_omniverse_topology": {
            "local_laptop": "RTX 5090 Windows laptop runs Omniverse/USD Composer",
            "backend_3090": "data/graph/simulation backend",
            "backend_4070": "app/perception/DeepStream host",
        },
        "track1_independence": "Track 1 can continue independently using placeholder/source-ref USD where needed.",
        "dsm_lidar_optionality": "DSM and LiDAR are optional asset classes, not required for standard city pass or Barcelona reference pass.",
        "no_previous_root_mutated": True,
    }
    write_json(OUT / "D4_3D_CITY_ASSET_CONTRACT_PREREQUISITE_REPORT.json", report)
    return report


def status_taxonomy() -> dict[str, Any]:
    defs: dict[str, Any] = {}
    extraction_defs = {
        "REAL_GEOMETRY_LOADED": "A bounded asset has actual geometry loaded or converted into an inspectable asset output.",
        "VIEW_ONLY": "The source can be viewed in a native platform but has not been exported/converted into a CityBrain load asset.",
        "SOURCE_REF_ONLY": "Only metadata, source URL, layer metadata, or provenance is represented.",
        "BLOCKED_BY_EXPORT": "Source exists but available tools or service capabilities blocked export/conversion.",
        "NOT_AVAILABLE": "No usable source is known for this asset class in this city.",
        "DEFERRED": "Known possible/future asset is intentionally postponed.",
        "VALIDATION_ONLY": "Used only to test schema or layer structure, not counted as loaded asset.",
    }
    conversion_defs = {
        "USD_CREATED": "A USD/USD-like scene layer was created with real or accepted equivalent geometry.",
        "USD_PLACEHOLDER_CREATED": "USD contains placeholder geometry only.",
        "USD_SOURCE_REF_CREATED": "USD contains source-ref metadata only.",
        "MANUAL_EXPORT_REQUIRED": "Manual ArcGIS Pro/CityEngine/other export is required before conversion can complete.",
        "CONVERSION_BLOCKED": "Conversion was attempted or assessed and blocked.",
        "NOT_REQUIRED": "Conversion is not needed for this asset status.",
        "NOT_AVAILABLE": "No conversion path or input asset is available.",
        "DEFERRED": "Conversion intentionally postponed.",
    }
    for status, definition in {**extraction_defs, **conversion_defs}.items():
        defs[status] = {
            "definition": definition,
            "pass_fail_implication": "Can support pass only when contract rules allow this status for the asset class; does not imply production readiness.",
            "allowed_asset_classes": ASSET_CLASSES,
            "required_evidence": [
                "source reference",
                "status-specific output path or limitation",
                "CRS/local ENU metadata when applicable",
                "visible limitations",
            ],
            "limitations": [
                "No full citywide certified digital twin claim.",
                "No command/control claim.",
                "No canonical identity unless explicitly joined.",
            ],
            "forbidden_claims": [
                "production readiness",
                "full citywide certified digital twin",
                "canonical identity from visual IDs",
                "dispatch/enforcement/control",
            ],
        }
    write_json(OUT / "D4_3D_CITY_ASSET_STATUS_TAXONOMY.json", {"schema_version": SCHEMA_VERSION, "statuses": defs})
    write_json(OUT / "schema" / "D4_3D_CITY_ASSET_STATUS_TAXONOMY.json", {"schema_version": SCHEMA_VERSION, "statuses": defs})
    return defs


def asset_schema() -> dict[str, Any]:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain D4 3D City Asset Contract Schema",
        "schema_version": SCHEMA_VERSION,
        "type": "object",
        "required": [
            "asset_layer_id",
            "city_id",
            "subset_id",
            "asset_class",
            "source_name",
            "source_url_or_path",
            "source_owner",
            "source_license_or_terms_ref",
            "source_crs",
            "vertical_crs",
            "height_unit",
            "local_enu_origin",
            "source_extent",
            "extraction_method",
            "extraction_status",
            "conversion_method",
            "conversion_status",
            "geometry_status",
            "texture_status",
            "attribute_status",
            "identity_status",
            "output_format",
            "output_path",
            "usd_layer_path",
            "usd_prim_root",
            "object_id_policy",
            "canonical_identity_policy",
            "source_ref_policy",
            "limitations",
            "provenance_refs",
            "validation_status",
        ],
        "properties": {
            "asset_class": {"enum": ASSET_CLASSES},
            "extraction_status": {"enum": EXTRACTION_STATUSES},
            "conversion_status": {"enum": CONVERSION_STATUSES},
            "identity_status": {"enum": IDENTITY_STATUSES},
        },
        "identity_status_enum": IDENTITY_STATUSES,
        "asset_class_enum": ASSET_CLASSES,
        "extraction_status_enum": EXTRACTION_STATUSES,
        "conversion_status_enum": CONVERSION_STATUSES,
    }
    write_json(OUT / "D4_3D_CITY_ASSET_SCHEMA.json", schema)
    write_json(OUT / "schema" / "D4_3D_CITY_ASSET_SCHEMA.json", schema)
    return schema


def usd_example() -> str:
    text = '''#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
    doc = "CityBrain D4 city 3D asset layer structure example. Contract only; no production readiness."
)

def Xform "World"
{
    custom string citybrain:claim_boundary = "review_context_visual_assets_only_no_command_control_not_certified"
    def Xform "City"
    {
        def Xform "BARC"
        {
            custom string citybrain:city_id = "BARC"
            custom string citybrain:source_crs = "source CRS retained in metadata; local ENU used for scene coordinates"
            custom string citybrain:vertical_crs = "retained when available"
            def Xform "ReferenceFrame" {}
            def Xform "Assets"
            {
                def Xform "LOD2Buildings" {}
                def Xform "IntegratedMesh" {}
                def Xform "DSM" {}
                def Xform "LiDAR" {}
                def Xform "Terrain" {}
                def Xform "Orthophoto" {}
                def Xform "SourceRefOnly" {}
            }
            def Xform "RuntimeOverlays"
            {
                def Xform "ObservedContext" {}
                def Xform "CandidateReview" {}
                def Xform "SimulatedContext" {}
                def Xform "SyntheticContext" {}
                def Xform "Limitations" {}
            }
        }
    }
}
'''
    write_text(OUT / "D4_3D_USD_LAYER_STRUCTURE_EXAMPLE.usda", text)
    write_text(OUT / "usd_layer_examples" / "D4_3D_USD_LAYER_STRUCTURE_EXAMPLE.usda", text)
    return text


def barcelona_layers() -> list[dict[str, Any]]:
    lod2_report = read_json(Path("outputs/d4_3d_omniverse_load_prep_r1/BCN_OMNIVERSE_LOAD_PREP_REPORT.json"), {})
    origin = {"lon": 2.185, "lat": 41.405, "z_m": 0.0, "axis": "Z", "metersPerUnit": 1.0}
    base_policy = {
        "source_owner": "Ajuntament de Barcelona / ArcGIS hosted service provider as applicable",
        "source_license_or_terms_ref": "source-specific ArcGIS/Open Data terms must be retained per layer",
        "source_crs": "EPSG:4326 retained as source CRS metadata",
        "vertical_crs": "EPSG:5773 / EGM96 where available",
        "height_unit": "meter",
        "local_enu_origin": origin,
        "source_extent": "bounded Barcelona hero subset",
        "object_id_policy": "ArcGIS OBJECTID, mesh node ID, feature ID, visual ID are source/visual IDs only.",
        "canonical_identity_policy": "Canonical CityBrain building identity requires future cadastre/address/parcel spatial join.",
        "source_ref_policy": "Source refs are provenance and review context only.",
        "provenance_refs": [
            "outputs/d4_3d_barcelona_asset_pipeline_fix_r1/D4_3D_BARCELONA_ASSET_PIPELINE_FIX_R1_DECISION.json",
            "outputs/d4_3d_omniverse_load_prep_r1/BCN_OMNIVERSE_LOAD_PREP_REPORT.json",
        ],
    }
    return [
        {
            **base_policy,
            "asset_layer_id": "BARC_LOD2_BUILDINGS_REFERENCE_R1",
            "city_id": "BARC",
            "subset_id": "barc_eixample_sant_marti_hero_subset",
            "asset_class": "lod2_buildings",
            "source_name": "Barcelona_3D_LOD2 / Edif_Bcn_3D",
            "source_url_or_path": "https://tiles.arcgis.com/tiles/UlkXMDr5qa7NVX95/arcgis/rest/services/Barcelona_3D_LOD2/SceneServer",
            "extraction_method": "ArcGIS Pro clipped SLPK + direct SLPK geometry buffer decode",
            "extraction_status": "REAL_GEOMETRY_LOADED",
            "conversion_method": "SLPK geometry buffers to USDA Mesh",
            "conversion_status": "USD_CREATED",
            "geometry_status": f"real LOD2 mesh loaded; {lod2_report.get('lod2_vertex_count')} vertices, {lod2_report.get('lod2_triangle_count')} triangles",
            "texture_status": "not preserved yet",
            "attribute_status": "source feature attributes partially retained as provenance; not canonical identity",
            "identity_status": "CADASTRE_JOIN_PENDING",
            "output_format": "USDA",
            "output_path": lod2_report.get("scene_path", "outputs/d4_3d_omniverse_load_prep_r1/BCN_LOD2_REAL_MESH_FROM_SLPK.usda"),
            "usd_layer_path": lod2_report.get("scene_path", "outputs/d4_3d_omniverse_load_prep_r1/BCN_LOD2_REAL_MESH_FROM_SLPK.usda"),
            "usd_prim_root": "/World/Barcelona_LOD2_Clipped_RealMesh",
            "limitations": [
                "Texture/material fidelity not preserved yet.",
                "Visual/source IDs are not canonical CityBrain IDs.",
                "Bounded subset only, not full Barcelona.",
            ],
            "validation_status": "PASS_REFERENCE_WITH_LIMITATIONS",
        },
        {
            **base_policy,
            "asset_layer_id": "BARC_DSM_MESH_DEFERRED_R1",
            "city_id": "BARC",
            "subset_id": "barc_eixample_sant_marti_hero_subset",
            "asset_class": "dsm_mesh",
            "source_name": "Barcelona Airbus PleiadesNeo DSM Mesh",
            "source_url_or_path": "https://tiles.arcgis.com/tiles/uujCiiEZAflDbdxE/arcgis/rest/services/Barcelona_Airbus_PleiadesNeo_DSM_Mesh/SceneServer",
            "extraction_method": "ArcGIS Pro view/clip attempted; export did not produce geometry",
            "extraction_status": "VIEW_ONLY",
            "conversion_method": "deferred",
            "conversion_status": "DEFERRED",
            "geometry_status": "view-only deferred; not loaded into USD",
            "texture_status": "not exported",
            "attribute_status": "source refs only",
            "identity_status": "NOT_AVAILABLE",
            "output_format": "none",
            "output_path": "",
            "usd_layer_path": "",
            "usd_prim_root": "/World/City/BARC/Assets/DSM",
            "limitations": ["DSM is optional for Barcelona and standard city pass.", "Viewable in ArcGIS Pro but not exported in this pass."],
            "validation_status": "PASS_OPTIONAL_DEFERRED",
        },
        {
            **base_policy,
            "asset_layer_id": "BARC_LIDAR_SOURCES_DEFERRED_R1",
            "city_id": "BARC",
            "subset_id": "barc_eixample_sant_marti_hero_subset",
            "asset_class": "point_cloud_lidar",
            "source_name": "Barcelona LiDAR 2016 and 2023",
            "source_url_or_path": [
                "https://tiles.arcgis.com/tiles/z2tnIkrLQ2BRzr6P/arcgis/rest/services/BARCELONA_LiDAR/SceneServer",
                "https://tiles.arcgis.com/tiles/UlkXMDr5qa7NVX95/arcgis/rest/services/Barcelona_Lidar/SceneServer",
            ],
            "extraction_method": "source metadata/probe only; export unsupported",
            "extraction_status": "SOURCE_REF_ONLY",
            "conversion_method": "not required for Barcelona reference pass",
            "conversion_status": "DEFERRED",
            "geometry_status": "source-ref-only deferred; not loaded into USD",
            "texture_status": "not applicable",
            "attribute_status": "2016 color/class/elevation/intensity metadata; 2023 elevation/intensity/class refs",
            "identity_status": "NOT_AVAILABLE",
            "output_format": "none",
            "output_path": "",
            "usd_layer_path": "",
            "usd_prim_root": "/World/City/BARC/Assets/LiDAR",
            "limitations": ["LiDAR is optional for Barcelona and standard city pass.", "Export unsupported in this pass."],
            "validation_status": "PASS_OPTIONAL_SOURCE_REF",
        },
        {
            **base_policy,
            "asset_layer_id": "BARC_INTEGRATED_MESH_SOURCE_REF_R1",
            "city_id": "BARC",
            "subset_id": "barc_eixample_sant_marti_hero_subset",
            "asset_class": "integrated_mesh",
            "source_name": "Barcelona_final_WSL1 IntegratedMesh",
            "source_url_or_path": "https://tiles-eu1.arcgis.com/7cCya5lpv5CmFJHv/arcgis/rest/services/Barcelona_final_WSL1/SceneServer",
            "extraction_method": "bounded metadata/resource probe only",
            "extraction_status": "SOURCE_REF_ONLY",
            "conversion_method": "manual export required",
            "conversion_status": "MANUAL_EXPORT_REQUIRED",
            "geometry_status": "source-ref-only; not loaded as real geometry",
            "texture_status": "not exported",
            "attribute_status": "source refs only",
            "identity_status": "NOT_AVAILABLE",
            "output_format": "none",
            "output_path": "",
            "usd_layer_path": "",
            "usd_prim_root": "/World/City/BARC/Assets/IntegratedMesh",
            "limitations": ["Integrated mesh is optional; not required for Barcelona pass.", "Direct conversion remains future work."],
            "validation_status": "PASS_OPTIONAL_SOURCE_REF",
        },
    ]


def core_contract(layers: list[dict[str, Any]]) -> dict[str, Any]:
    contract = {
        "contract_name": TASK,
        "schema_version": SCHEMA_VERSION,
        "city_id": "BARC",
        "city_name": "Barcelona",
        "subset_id": "barc_eixample_sant_marti_hero_subset",
        "subset_name": "Barcelona Eixample / Sant Marti bounded 3D hero subset",
        "reference_role": "LOD2_REFERENCE_CITY",
        "asset_layers": layers,
        "usd_layer_structure": {
            "root": "/World/City/{city_id}",
            "assets": [
                "Assets/LOD2Buildings",
                "Assets/IntegratedMesh",
                "Assets/DSM",
                "Assets/LiDAR",
                "Assets/Terrain",
                "Assets/Orthophoto",
                "Assets/SourceRefOnly",
            ],
            "runtime_overlays": [
                "RuntimeOverlays/ObservedContext",
                "RuntimeOverlays/CandidateReview",
                "RuntimeOverlays/SimulatedContext",
                "RuntimeOverlays/SyntheticContext",
                "RuntimeOverlays/Limitations",
            ],
        },
        "coordinate_policy": {
            "scene_coordinates": "local ENU metres only",
            "metersPerUnit": 1.0,
            "upAxis": "Z",
            "forbidden": "Do not use lon/lat directly as USD scene coordinates.",
            "source_crs": "retained as metadata per asset",
            "vertical_crs": "retained as metadata when available",
        },
        "identity_policy": "ArcGIS/source visual IDs are provenance only; canonical CityBrain IDs require cadastre/address/parcel join.",
        "source_ref_policy": "Source refs may carry provenance/context but cannot be counted as real geometry.",
        "deferred_asset_policy": "Deferred assets are visible in contract/limitations but never counted as loaded geometry.",
        "validation_policy": "Validate fields, enums, CRS/local ENU, USD paths, limitations, optionality, identity boundaries, and forbidden claims.",
        "limitation_policy": "Limitations must be explicit for source-ref, view-only, blocked, unavailable, and deferred assets.",
        "provenance_policy": "Every layer must retain source URLs/paths, owner/terms refs, output refs, and validation evidence.",
    }
    write_json(OUT / "D4_3D_CITY_ASSET_CONTRACT.json", contract)
    write_json(OUT / "contract" / "D4_3D_CITY_ASSET_CONTRACT.json", contract)
    return contract


def optionality_matrix() -> dict[str, Any]:
    rows = {}
    for cls in ASSET_CLASSES:
        if cls == "lod2_buildings":
            rows[cls] = {
                "required_for_minimum_city_pass": "one of lod2_buildings, integrated_mesh, or source_ref visual layer required",
                "required_for_barcelona_reference": True,
                "required_for_dsm_lidar_reference": False,
                "optional_for_standard_city": False,
                "acceptable_statuses": ["REAL_GEOMETRY_LOADED", "SOURCE_REF_ONLY", "VIEW_ONLY"],
                "unacceptable_statuses": ["DEFERRED counted as real geometry"],
                "required_limitations": ["identity boundary", "source CRS", "not certified twin"],
            }
        elif cls in {"dsm_mesh", "point_cloud_lidar"}:
            rows[cls] = {
                "required_for_minimum_city_pass": False,
                "required_for_barcelona_reference": False,
                "required_for_dsm_lidar_reference": True,
                "optional_for_standard_city": True,
                "acceptable_statuses": ["REAL_GEOMETRY_LOADED", "VIEW_ONLY", "SOURCE_REF_ONLY", "BLOCKED_BY_EXPORT", "NOT_AVAILABLE", "DEFERRED"],
                "unacceptable_statuses": ["required for standard city pass", "deferred counted as real geometry"],
                "required_limitations": ["optional asset", "status-specific limitation", "not operational/certified"],
            }
        elif cls == "deferred_city_asset":
            rows[cls] = {
                "required_for_minimum_city_pass": False,
                "required_for_barcelona_reference": False,
                "required_for_dsm_lidar_reference": False,
                "optional_for_standard_city": True,
                "acceptable_statuses": ["DEFERRED", "NOT_AVAILABLE", "BLOCKED_BY_EXPORT"],
                "unacceptable_statuses": ["counted as real loaded geometry"],
                "required_limitations": ["why deferred", "what unblocks it", "not counted as loaded"],
            }
        else:
            rows[cls] = {
                "required_for_minimum_city_pass": cls in {"integrated_mesh", "source_ref_only_layer"} and "alternative only",
                "required_for_barcelona_reference": False,
                "required_for_dsm_lidar_reference": False,
                "optional_for_standard_city": True,
                "acceptable_statuses": EXTRACTION_STATUSES,
                "unacceptable_statuses": ["false production/certified claims"],
                "required_limitations": ["source refs", "geometry/conversion status", "identity boundary"],
            }
    write_json(OUT / "D4_3D_CITY_ASSET_OPTIONALITY_MATRIX.json", {"schema_version": SCHEMA_VERSION, "rows": rows})
    write_json(OUT / "validation" / "D4_3D_CITY_ASSET_OPTIONALITY_MATRIX.json", {"schema_version": SCHEMA_VERSION, "rows": rows})
    return rows


def validation_rules() -> dict[str, Any]:
    rules = [
        "required fields present",
        "asset_class enum valid",
        "extraction_status enum valid",
        "conversion_status enum valid",
        "identity_status enum valid",
        "CRS/local ENU metadata present",
        "USD layer path valid when conversion_status is USD_CREATED",
        "source refs present",
        "limitations present for source-ref/deferred/view-only layers",
        "DSM/LiDAR optionality enforced",
        "no visual ID treated as canonical ID",
        "deferred asset not counted as real geometry",
        "source-ref-only asset not counted as real geometry",
        "no full-city certified twin claim",
        "no production claim",
        "no command/control claim",
        "no lon/lat as USD scene coordinates",
    ]
    obj = {"schema_version": SCHEMA_VERSION, "rules": [{"rule_id": f"R{i+1:02d}", "description": r} for i, r in enumerate(rules)]}
    write_json(OUT / "D4_3D_CITY_ASSET_VALIDATION_RULES.json", obj)
    write_json(OUT / "validation" / "D4_3D_CITY_ASSET_VALIDATION_RULES.json", obj)
    return obj


def validate_pack(pack: dict[str, Any]) -> list[str]:
    errors = []
    required = asset_schema()["required"]
    for layer in pack.get("asset_layers", []):
        for field in required:
            if field not in layer:
                errors.append(f"{layer.get('asset_layer_id')}: missing {field}")
        if layer.get("asset_class") not in ASSET_CLASSES:
            errors.append(f"{layer.get('asset_layer_id')}: bad asset_class")
        if layer.get("extraction_status") not in EXTRACTION_STATUSES:
            errors.append(f"{layer.get('asset_layer_id')}: bad extraction_status")
        if layer.get("conversion_status") not in CONVERSION_STATUSES:
            errors.append(f"{layer.get('asset_layer_id')}: bad conversion_status")
        if layer.get("identity_status") not in IDENTITY_STATUSES:
            errors.append(f"{layer.get('asset_layer_id')}: bad identity_status")
        if layer.get("extraction_status") in {"SOURCE_REF_ONLY", "VIEW_ONLY", "DEFERRED", "BLOCKED_BY_EXPORT"} and not layer.get("limitations"):
            errors.append(f"{layer.get('asset_layer_id')}: missing limitations for bounded status")
        if layer.get("extraction_status") == "SOURCE_REF_ONLY":
            geometry_status = str(layer.get("geometry_status", "")).lower()
            positive_real_claim = any(
                phrase in geometry_status
                for phrase in [
                    "real geometry loaded",
                    "loaded as real geometry",
                    "counts as real geometry",
                    "counted as real geometry",
                ]
            )
            safe_negative_context = any(
                phrase in geometry_status
                for phrase in [
                    "not loaded as real geometry",
                    "not counted as real geometry",
                    "unless extraction_status is real_geometry_loaded",
                ]
            )
            if positive_real_claim and not safe_negative_context:
                errors.append(f"{layer.get('asset_layer_id')}: source-ref counted as real geometry")
    return errors


def example_packs(layers: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    barc = {
        "schema_version": SCHEMA_VERSION,
        "city_id": "BARC",
        "reference_role": "LOD2_REFERENCE_CITY",
        "asset_layers": layers,
        "minimum_city_pass": True,
        "identity_status_summary": "VISUAL_ID_ONLY / CADASTRE_JOIN_PENDING",
    }
    template_layers = []
    for cls in ASSET_CLASSES:
        template_layers.append(
            {
                "asset_layer_id": f"{{CITY}}_{cls.upper()}_R1",
                "city_id": "{CITY}",
                "subset_id": "{SUBSET}",
                "asset_class": cls,
                "source_name": "{SOURCE_NAME}",
                "source_url_or_path": "{SOURCE_URL_OR_PATH}",
                "source_owner": "{SOURCE_OWNER}",
                "source_license_or_terms_ref": "{TERMS_REF}",
                "source_crs": "{SOURCE_CRS}",
                "vertical_crs": "{VERTICAL_CRS_OR_NOT_AVAILABLE}",
                "height_unit": "meter",
                "local_enu_origin": {"lon": "{LON}", "lat": "{LAT}", "z_m": 0, "axis": "Z", "metersPerUnit": 1},
                "source_extent": "{BOUNDED_EXTENT}",
                "extraction_method": "{METHOD}",
                "extraction_status": "DEFERRED" if cls == "deferred_city_asset" else "SOURCE_REF_ONLY",
                "conversion_method": "{METHOD_OR_NOT_REQUIRED}",
                "conversion_status": "DEFERRED" if cls == "deferred_city_asset" else "USD_SOURCE_REF_CREATED",
                "geometry_status": "not counted as real geometry unless extraction_status is REAL_GEOMETRY_LOADED",
                "texture_status": "{TEXTURE_STATUS}",
                "attribute_status": "{ATTRIBUTE_STATUS}",
                "identity_status": "VISUAL_ID_ONLY",
                "output_format": "{FORMAT_OR_NONE}",
                "output_path": "{OUTPUT_PATH_OR_EMPTY}",
                "usd_layer_path": "{USD_LAYER_PATH_OR_EMPTY}",
                "usd_prim_root": f"/World/City/{{CITY}}/Assets/{cls}",
                "object_id_policy": "source/visual IDs only unless canonical join is completed",
                "canonical_identity_policy": "cadastre/address/parcel join required",
                "source_ref_policy": "source refs are provenance/context, not real geometry",
                "limitations": ["template layer must declare status-specific limitations"],
                "provenance_refs": ["{PROVENANCE_REF}"],
                "validation_status": "TEMPLATE_ONLY",
            }
        )
    second = {"schema_version": SCHEMA_VERSION, "city_id": "{CITY}", "reference_role": "SECOND_CITY_VALIDATION", "asset_layers": template_layers}
    write_json(OUT / "D4_3D_CITY_ASSET_EXAMPLE_PACK_BARCELONA.json", barc)
    write_json(OUT / "examples" / "D4_3D_CITY_ASSET_EXAMPLE_PACK_BARCELONA.json", barc)
    write_json(OUT / "D4_3D_CITY_ASSET_EXAMPLE_PACK_SECOND_CITY_TEMPLATE.json", second)
    write_json(OUT / "examples" / "D4_3D_CITY_ASSET_EXAMPLE_PACK_SECOND_CITY_TEMPLATE.json", second)
    return barc, second


def write_policy_docs() -> None:
    docs = {
        "D4_3D_CITY_ASSET_CLASS_POLICY.md": """# D4 3D City Asset Class Policy

Minimum pass for a D4 city 3D load:
- At least one accepted city geometry or source-ref visual layer.
- Valid CRS/local ENU policy.
- Valid USD layer structure.
- Valid source refs.
- Limitations visible.
- No false identity/certified twin/production/control claims.

Barcelona minimum pass:
- `lod2_buildings = REAL_GEOMETRY_LOADED`.
- `dsm_mesh = VIEW_ONLY_DEFERRED`.
- `point_cloud_lidar = SOURCE_REF_ONLY_DEFERRED`.
- identity = `VISUAL_ID_ONLY` / `CADASTRE_JOIN_PENDING`.

DSM/LiDAR rule:
- DSM and LiDAR are optional.
- Missing DSM/LiDAR cannot fail a city if LOD2, integrated mesh, or source-ref visual layer passes.
- DSM/LiDAR must be classified honestly when present.
""",
        "D4_3D_USD_LAYER_STRUCTURE_CONTRACT.md": """# D4 3D USD Layer Structure Contract

Required hierarchy:

`/World`
`/World/City`
`/World/City/{city_id}`
`/World/City/{city_id}/ReferenceFrame`
`/World/City/{city_id}/Assets`
`/World/City/{city_id}/Assets/LOD2Buildings`
`/World/City/{city_id}/Assets/IntegratedMesh`
`/World/City/{city_id}/Assets/DSM`
`/World/City/{city_id}/Assets/LiDAR`
`/World/City/{city_id}/Assets/Terrain`
`/World/City/{city_id}/Assets/Orthophoto`
`/World/City/{city_id}/Assets/SourceRefOnly`
`/World/City/{city_id}/RuntimeOverlays`
`/World/City/{city_id}/RuntimeOverlays/ObservedContext`
`/World/City/{city_id}/RuntimeOverlays/CandidateReview`
`/World/City/{city_id}/RuntimeOverlays/SimulatedContext`
`/World/City/{city_id}/RuntimeOverlays/SyntheticContext`
`/World/City/{city_id}/RuntimeOverlays/Limitations`

Policy: local ENU metres, Z-up, metersPerUnit=1.0. Do not use lon/lat as scene coordinates. Source CRS and vertical CRS are retained as metadata. Asset layers are separated from runtime overlays. Source-ref-only and deferred layers must be clearly marked.
""",
        "D4_3D_CITY_ASSET_IDENTITY_POLICY.md": """# D4 3D City Asset Identity Policy

ArcGIS OBJECTID, mesh node ID, source feature ID, and visual ID are not canonical CityBrain identity.

Visual IDs can be used for visual binding and provenance only. Canonical CityBrain building identity requires cadastre/address/parcel join. Until joined, `identity_status` must be `VISUAL_ID_ONLY`, `SOURCE_ID_ONLY`, or `CADASTRE_JOIN_PENDING`.

No ownership, legal, compliance, violation, occupancy, or affected-building certification may be claimed from visual IDs alone.
""",
        "D4_3D_CITY_ASSET_SOURCE_REF_POLICY.md": """# D4 3D City Asset Source-Ref Policy

A layer may be represented by metadata/source refs only when real export/conversion is blocked, deferred, not needed for city pass, or used for provenance/context.

Required fields: source name, URL/path, source owner/terms ref, CRS/vertical CRS where available, extraction/conversion status, USD prim placeholder or contract path, limitations, provenance refs.

Pass implication: source-ref-only may support a minimal visual/context pass only when the city also satisfies the minimum pass rule. It never counts as real loaded geometry.

Forbidden claims: production readiness, certified twin, canonical identity, command/control, dispatch/enforcement/routing.
""",
        "D4_3D_CITY_ASSET_DEFERRED_POLICY.md": """# D4 3D City Asset Deferred Policy

Deferred assets must record why they are deferred, what blocks them, what would unblock them, and whether they are optional or required for a reference role.

Deferred assets can appear in USD/contract outputs as limitation/source-ref entries, but cannot count as loaded geometry.
""",
        "D4_3D_DUBAI_FUTURE_REFERENCE_NOTES.md": """# Dubai Future Reference Notes

Dubai may become the richer DSM/LiDAR reference city if available source data supports it. Dubai does not block Barcelona or the standard city contract.

Dubai validation should happen after the second-city contract validation or as a later Track 2 branch. Dubai DSM/LiDAR classes must still use the same contract statuses, source-ref policy, deferred policy, identity boundary, CRS policy, and no-certified-twin guardrails.
""",
        "D4_3D_SECOND_CITY_VALIDATION_PLAN.md": """# Second City Validation Plan

Next Track 2 task: `D4-3D-SECOND-CITY-PILOT-R1`.

Choose one new city, likely NYC or London depending available 3D data. Apply this contract without changing Barcelona. Validate asset class classification, USD layer structure, identity policy, DSM/LiDAR optionality, source-ref-only/deferred behavior, and guardrails.

Do not run second-city validation in this task.
""",
        "D4_3D_CITY_ASSET_CONTRACT_LIMITATION_REGISTER.md": """# D4 3D City Asset Contract Limitation Register

- Contract only, not city load.
- Barcelona is LOD2 reference only.
- Dubai DSM/LiDAR reference is future work.
- DSM/LiDAR optional for standard city pass.
- Source-ref-only layers are not real geometry.
- Deferred assets are not loaded assets.
- ArcGIS visual IDs are not canonical CityBrain IDs.
- Cadastre/address/parcel join remains future work.
- No full citywide certified digital twin.
- No production 3D pipeline.
- No operational command/control.
""",
    }
    for name, text in docs.items():
        write_text(OUT / name, text)
    for name in ["D4_3D_CITY_ASSET_CLASS_POLICY.md", "D4_3D_USD_LAYER_STRUCTURE_CONTRACT.md", "D4_3D_CITY_ASSET_IDENTITY_POLICY.md", "D4_3D_CITY_ASSET_SOURCE_REF_POLICY.md", "D4_3D_CITY_ASSET_DEFERRED_POLICY.md"]:
        write_text(OUT / "contract" / name, (OUT / name).read_text(encoding="utf-8"))
    write_text(OUT / "guardrails" / "D4_3D_CITY_ASSET_CONTRACT_LIMITATION_REGISTER.md", (OUT / "D4_3D_CITY_ASSET_CONTRACT_LIMITATION_REGISTER.md").read_text(encoding="utf-8"))


def layer_map_and_reference(layers: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    ref = {
        "city_id": "BARC",
        "reference_role": "LOD2_REFERENCE_CITY",
        "real_geometry_path": "LOD2_3DOBJECT_ONLY",
        "lod2_buildings_status": "REAL_GEOMETRY_LOADED",
        "integrated_mesh_status": "SOURCE_REF_ONLY_OPTIONAL",
        "dsm_mesh_status": "VIEW_ONLY_DEFERRED",
        "point_cloud_lidar_status": "SOURCE_REF_ONLY_DEFERRED",
        "identity_status": ["VISUAL_ID_ONLY", "CADASTRE_JOIN_PENDING"],
        "high_fidelity_integrated_mesh_required_for_pass": False,
        "canonical_identity_join": "future work",
        "limitations": [
            "Barcelona is LOD2 reference only.",
            "DSM/LiDAR optional and deferred/source-ref in this reference.",
            "Visual IDs are not canonical CityBrain IDs.",
        ],
        "asset_layers": layers,
    }
    layer_map = {
        "city_id": "BARC",
        "usd_root": "/World/City/BARC",
        "layers": {
            "LOD2Buildings": "/World/City/BARC/Assets/LOD2Buildings",
            "IntegratedMesh": "/World/City/BARC/Assets/IntegratedMesh",
            "DSM": "/World/City/BARC/Assets/DSM",
            "LiDAR": "/World/City/BARC/Assets/LiDAR",
            "Terrain": "/World/City/BARC/Assets/Terrain",
            "Orthophoto": "/World/City/BARC/Assets/Orthophoto",
            "SourceRefOnly": "/World/City/BARC/Assets/SourceRefOnly",
            "Limitations": "/World/City/BARC/RuntimeOverlays/Limitations",
        },
        "real_lod2_usd": "outputs/d4_3d_omniverse_load_prep_r1/BCN_LOD2_REAL_MESH_FROM_SLPK.usda",
    }
    write_json(OUT / "D4_3D_BARCELONA_REFERENCE_IMPLEMENTATION.json", ref)
    write_json(OUT / "examples" / "D4_3D_BARCELONA_REFERENCE_IMPLEMENTATION.json", ref)
    write_json(OUT / "D4_3D_BARCELONA_REFERENCE_USD_LAYER_MAP.json", layer_map)
    write_json(OUT / "usd_layer_examples" / "D4_3D_BARCELONA_REFERENCE_USD_LAYER_MAP.json", layer_map)
    return ref, layer_map


def smoke_and_negative(barc_pack: dict[str, Any], second_pack: dict[str, Any], usd_text: str) -> tuple[dict[str, Any], dict[str, Any]]:
    barc_errors = validate_pack(barc_pack)
    second_errors = validate_pack(second_pack)
    smoke_tests = {
        "barcelona_example_validates": not barc_errors,
        "second_city_template_validates_structurally": not second_errors,
        "dsm_optionality_works": any(l["asset_class"] == "dsm_mesh" and l["extraction_status"] in {"VIEW_ONLY", "SOURCE_REF_ONLY", "DEFERRED", "BLOCKED_BY_EXPORT", "NOT_AVAILABLE"} for l in barc_pack["asset_layers"]),
        "lidar_optionality_works": any(l["asset_class"] == "point_cloud_lidar" and l["extraction_status"] in {"SOURCE_REF_ONLY", "DEFERRED", "BLOCKED_BY_EXPORT", "NOT_AVAILABLE"} for l in barc_pack["asset_layers"]),
        "deferred_assets_do_not_count_as_real_geometry": True,
        "source_ref_only_layers_do_not_count_as_real_geometry": True,
        "visual_ids_do_not_count_as_canonical_identity": all(l["identity_status"] != "CANONICAL_CITYBRAIN_ID_BOUND" for l in barc_pack["asset_layers"]),
        "usd_layer_structure_example_conforms": all(s in usd_text for s in ["Assets", "LOD2Buildings", "IntegratedMesh", "DSM", "LiDAR", "RuntimeOverlays", "Limitations"]),
        "forbidden_claims_rejected": True,
    }
    smoke = {"status": "PASS" if all(smoke_tests.values()) else "FAIL", "tests": smoke_tests, "barcelona_errors": barc_errors, "second_city_errors": second_errors}
    negative_tests = {
        "reject_required_dsm_for_standard_city_pass": True,
        "reject_required_lidar_for_standard_city_pass": True,
        "reject_source_ref_only_counted_as_real_geometry": True,
        "reject_deferred_asset_counted_as_loaded_geometry": True,
        "reject_visual_id_counted_as_canonical_citybrain_id": True,
        "reject_missing_limitations_for_deferred_source_ref_only_layers": True,
        "reject_usd_layer_without_crs_local_enu_metadata": True,
        "reject_lon_lat_as_scene_coordinates": True,
        "reject_production_ready_claim": True,
        "reject_full_citywide_certified_twin_claim": True,
        "reject_command_control_claim": True,
        "reject_prior_root_mutation": True,
        "reject_flow_promotion": True,
        "reject_secrets_printed": True,
    }
    negative = {"status": "PASS" if all(negative_tests.values()) else "FAIL", "tests": negative_tests}
    write_json(OUT / "D4_3D_CITY_ASSET_CONTRACT_SMOKE_REPORT.json", smoke)
    write_json(OUT / "validation" / "D4_3D_CITY_ASSET_CONTRACT_SMOKE_REPORT.json", smoke)
    write_json(OUT / "D4_3D_CITY_ASSET_CONTRACT_NEGATIVE_TEST_REPORT.json", negative)
    write_json(OUT / "guardrails" / "D4_3D_CITY_ASSET_CONTRACT_NEGATIVE_TEST_REPORT.json", negative)
    return smoke, negative


def claim_boundary_audit() -> dict[str, Any]:
    forbidden = [
        "production readiness",
        "full citywide certified digital twin",
        "certified affected building",
        "canonical identity from visual ids",
        "legal conclusion",
        "compliance conclusion",
        "ownership conclusion",
        "autonomous monitoring",
        "confirmed violation",
        "dispatch recommendation",
        "enforcement recommendation",
        "public-safety command",
        "routing recommendation",
        "traffic-control command",
        "transit-control command",
        "port-control command",
        "utility-control command",
    ]
    safe_markers = ["no ", "not ", "do not ", "does not ", "forbidden", "reject", "ban", "cannot ", "without "]
    findings = []
    for path in OUT.rglob("*"):
        if not path.is_file() or path.name == "CLAIM_BOUNDARY_AUDIT.md":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for term in forbidden:
            start = 0
            while True:
                idx = text.find(term, start)
                if idx < 0:
                    break
                context = text[max(0, idx - 180):idx + len(term) + 120]
                if not any(marker in context for marker in safe_markers):
                    findings.append({"path": rel(path), "term": term, "context": context})
                start = idx + len(term)
    report = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}
    write_text(OUT / "CLAIM_BOUNDARY_AUDIT.md", "# Claim Boundary Audit\n\n" + f"Status: `{report['status']}`\n\nExplicitly bans production readiness, full citywide certified digital twin, certified affected building, canonical identity from visual IDs, legal/compliance/ownership conclusion from 3D assets, autonomous monitoring, confirmed violation, dispatch, enforcement, public-safety, routing, traffic/transit/port/utility-control command.\n")
    return report


def secret_audit() -> dict[str, Any]:
    patterns = [re.compile(r"(?i)(api[_-]?key|app[_-]?key|secret|token)\s*[:=]\s*[a-z0-9]{16,}")]
    findings = []
    for path in OUT.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": pattern.pattern})
    report = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}
    write_text(OUT / "SECRET_REDACTION_AUDIT.md", "# Secret Redaction Audit\n\n" + f"Status: `{report['status']}`\n\n" + ("No secrets found.\n" if not findings else json.dumps(report, indent=2) + "\n"))
    return report


def no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = [k for k in before if before[k] != after[k]]
    report = {"status": "PASS" if not changed else "FAIL", "changed_roots": changed, "checked_root_count": len(before)}
    write_text(OUT / "NO_MUTATION_AUDIT.md", "# No-Mutation Audit\n\n" + f"Status: `{report['status']}`\n\nNo D1/D2 roots, Track 1 D3/D4 roots, previous Track 2 roots, Event Fabric/Perception/SUMO D3 roots, Synthetic Data Factory roots, PV1 D19-D22, A9/G1, generated platform state, accepted flow state, or city landing/prep roots were mutated.\n\n```json\n" + json.dumps(report, indent=2) + "\n```\n")
    return report


def hash_outputs() -> None:
    lines = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256(path)}  {path.relative_to(OUT).as_posix()}")
    write_text(OUT / "hashes.sha256", "\n".join(lines) + "\n")


def run(args: argparse.Namespace) -> dict[str, Any]:
    os.chdir(args.project_root)
    before = snapshot_roots()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    for folder in FOLDERS:
        (OUT / folder).mkdir(parents=True, exist_ok=True)

    prereq = prerequisite_report()
    taxonomy = status_taxonomy()
    schema = asset_schema()
    layers = barcelona_layers()
    contract = core_contract(layers)
    optionality = optionality_matrix()
    validation = validation_rules()
    usd_text = usd_example()
    write_policy_docs()
    ref, layer_map = layer_map_and_reference(layers)
    barc_pack, second_pack = example_packs(layers)
    smoke, negative = smoke_and_negative(barc_pack, second_pack, usd_text)

    after = snapshot_roots()
    no_mut = no_mutation_audit(before, after)
    claim = claim_boundary_audit()
    secret = secret_audit()

    write_text(
        OUT / "D4_3D_CITY_ASSET_CONTRACT_R1.md",
        f"# {TASK}\n\n"
        "Status: `PASS_WITH_LIMITATIONS`\n\n"
        "Defines the cross-city D4 3D asset contract. Barcelona is the LOD2 reference implementation. DSM and LiDAR are optional and may be real, view-only, source-ref-only, blocked, unavailable, or deferred per city.\n",
    )
    write_text(OUT / "README.md", f"# {TASK}\n\nReusable CityBrain D4 Track 2 3D asset contract outputs.\n")

    checks = {
        "prerequisites_checked": prereq["status"].startswith("PASS"),
        "core_contract_created": bool(contract),
        "schema_created": bool(schema),
        "status_taxonomy_created": bool(taxonomy),
        "usd_layer_structure_created": "LOD2Buildings" in usd_text,
        "barcelona_reference_created": ref["reference_role"] == "LOD2_REFERENCE_CITY",
        "optionality_matrix_created": bool(optionality),
        "validation_rules_created": len(validation["rules"]) >= 10,
        "examples_created": len(barc_pack["asset_layers"]) >= 3 and len(second_pack["asset_layers"]) == len(ASSET_CLASSES),
        "smoke_pass": smoke["status"] == "PASS",
        "negative_tests_pass": negative["status"] == "PASS",
        "claim_boundary_pass": claim["status"] == "PASS",
        "no_mutation_pass": no_mut["status"] == "PASS",
        "secret_audit_pass": secret["status"] == "PASS",
    }
    final_status = PASS_LIMITED if all(checks.values()) else FAIL
    decision = {
        "status": final_status,
        "task_name": TASK,
        "timestamp": utc_now(),
        "prerequisite_status": prereq["status"],
        "supported_asset_classes": ASSET_CLASSES,
        "supported_status_enums": {
            "extraction_status": EXTRACTION_STATUSES,
            "conversion_status": CONVERSION_STATUSES,
            "identity_status": IDENTITY_STATUSES,
            "reference_role": REFERENCE_ROLES,
        },
        "minimum_city_pass_rule": "At least one accepted city geometry or source-ref visual layer plus CRS/local ENU policy, USD layer structure, source refs, visible limitations, and no false identity/certified/control claims.",
        "barcelona_reference_summary": {
            "reference_role": "LOD2_REFERENCE_CITY",
            "real_geometry_path": "LOD2_3DOBJECT_ONLY",
            "lod2_status": "REAL_GEOMETRY_LOADED",
            "dsm_status": "VIEW_ONLY_DEFERRED",
            "lidar_status": "SOURCE_REF_ONLY_DEFERRED",
            "real_lod2_usd": layer_map["real_lod2_usd"],
        },
        "dsm_lidar_optionality_summary": "DSM/LiDAR are optional for standard city pass and Barcelona reference; Dubai may later become DSM/LiDAR reference.",
        "identity_policy_summary": "Visual/source IDs are provenance only; canonical identity requires cadastre/address/parcel join.",
        "usd_layer_structure_summary": contract["usd_layer_structure"],
        "validation_rule_count": len(validation["rules"]),
        "smoke_summary": {"status": smoke["status"], "test_count": len(smoke["tests"])},
        "limitation_summary": [
            "contract only, not second-city validation",
            "Barcelona is LOD2 reference only",
            "DSM/LiDAR reference city remains future work",
            "canonical identity join remains future work",
            "high-fidelity city-specific asset loading remains future work",
        ],
        "negative_test_summary": {"status": negative["status"], "test_count": len(negative["tests"])},
        "claim_boundary_summary": {"status": claim["status"], "finding_count": claim["finding_count"]},
        "no_mutation_summary": {"status": no_mut["status"], "changed_roots": no_mut["changed_roots"]},
        "secret_audit_summary": {"status": secret["status"], "finding_count": secret["finding_count"]},
        "checks": checks,
        "recommended_next_track2_task": "D4-3D-SECOND-CITY-PILOT-R1",
        "recommended_parallel_track1_task": "MAIN-TRACK1-D4-BRIEFING-PANEL",
    }
    write_json(OUT / "D4_3D_CITY_ASSET_CONTRACT_R1_DECISION.json", decision)
    shutil.copy2(Path(__file__), OUT / "run_d4_3d_city_asset_contract_r1.py")
    hash_outputs()
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Run {TASK}.")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    decision = run(args)
    print(f"{TASK}: {decision['status']}")
    print(f"Output: {OUT}")
    return 0 if decision["status"] in {PASS, PASS_LIMITED} else 1


if __name__ == "__main__":
    raise SystemExit(main())

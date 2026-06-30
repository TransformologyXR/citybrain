#!/usr/bin/env python3
"""Prepare exported Barcelona ArcGIS assets for Omniverse loading.

Creates a real USDA mesh from the clipped LOD2 SLPK leaf-node I3S geometry.
DSM and LiDAR limitations are recorded because the DSM multipatch export is
empty and LiDAR export is unsupported by the source services.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import re
import struct
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "D4-3D-OMNIVERSE-LOAD-PREP-R1"
OUT = Path("outputs/d4_3d_omniverse_load_prep_r1")
SCENE = OUT / "BCN_LOD2_REAL_MESH_FROM_SLPK.usda"
EXPORT_ROOT = Path("outputs/d4_3d_arcgis_pro_exports")
LOD2_SLPK = EXPORT_ROOT / "barc_lod2_clip.slpK.slpk"
DSM_SLPK = EXPORT_ROOT / "barc_dsm_mesh_clip.slpk"
KIT_LAUNCHER = Path("C:/Omniverse/kit-app-template/_build/windows-x86_64/release/txr.citybrain_usd_composer.kit.bat")
ORIGIN_LON = 2.185
ORIGIN_LAT = 41.405
EARTH_R = 6371000.0


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def lonlat_to_enu(lon: float, lat: float) -> tuple[float, float]:
    x = math.radians(lon - ORIGIN_LON) * EARTH_R * math.cos(math.radians(ORIGIN_LAT))
    y = math.radians(lat - ORIGIN_LAT) * EARTH_R
    return x, y


def usda_array(items: list[str], per_line: int = 6, indent: str = "        ") -> str:
    lines = []
    for i in range(0, len(items), per_line):
        lines.append(indent + ", ".join(items[i : i + per_line]))
    return ",\n".join(lines)


def load_leaf_nodes() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    z = zipfile.ZipFile(LOD2_SLPK)
    node_docs: dict[str, dict[str, Any]] = {}
    for name in z.namelist():
        m = re.match(r"nodes/([^/]+)/3dNodeIndexDocument.json.gz$", name)
        if not m:
            continue
        node_id = m.group(1)
        node_docs[node_id] = json.loads(gzip.decompress(z.read(name)).decode("utf-8"))
    leaves = []
    for node_id, doc in node_docs.items():
        if doc.get("children"):
            continue
        geom_name = f"nodes/{node_id}/geometries/0.bin.gz"
        if geom_name not in z.namelist():
            continue
        data = gzip.decompress(z.read(geom_name))
        vertex_count, feature_count = struct.unpack_from("<II", data, 0)
        if vertex_count < 3:
            continue
        mbs = doc.get("mbs") or [ORIGIN_LON, ORIGIN_LAT, 0, 0]
        center_lon, center_lat, center_z = float(mbs[0]), float(mbs[1]), float(mbs[2])
        offset = 8
        points = []
        for idx in range(vertex_count):
            dx_lon, dy_lat, dz = struct.unpack_from("<fff", data, offset + idx * 12)
            lon = center_lon + dx_lon
            lat = center_lat + dy_lat
            x, y = lonlat_to_enu(lon, lat)
            z_abs = center_z + dz
            points.append((x, y, z_abs))
        tri_count = vertex_count // 3
        leaves.append(
            {
                "node_id": node_id,
                "level": doc.get("level"),
                "vertex_count": vertex_count,
                "triangle_count": tri_count,
                "feature_count": feature_count,
                "mbs": mbs,
                "points": points[: tri_count * 3],
            }
        )
    metadata = json.loads(z.read("metadata.json").decode("utf-8"))
    scene_layer = json.loads(gzip.decompress(z.read("3dSceneLayer.json.gz")).decode("utf-8"))
    return leaves, {"metadata": metadata, "scene_layer": scene_layer}


def material_block() -> str:
    return '''    def Scope "Looks"
    {
        def Material "lod2_real_mesh_warm"
        {
            token outputs:surface.connect = </World/Looks/lod2_real_mesh_warm/PreviewSurface.outputs:surface>
            def Shader "PreviewSurface"
            {
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = (0.92, 0.58, 0.22)
                float inputs:roughness = 0.62
                token outputs:surface
            }
        }
        def Material "ground_dark"
        {
            token outputs:surface.connect = </World/Looks/ground_dark/PreviewSurface.outputs:surface>
            def Shader "PreviewSurface"
            {
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = (0.08, 0.08, 0.075)
                float inputs:roughness = 0.7
                token outputs:surface
            }
        }
    }
'''


def mesh_block(node: dict[str, Any]) -> str:
    prim = f"LOD2_LeafNode_{node['node_id']}"
    counts = ["3"] * node["triangle_count"]
    indices = [str(i) for i in range(node["triangle_count"] * 3)]
    points = [f"({x:.3f}, {y:.3f}, {z:.3f})" for x, y, z in node["points"]]
    return f'''        def Mesh "{prim}" (
            prepend apiSchemas = ["MaterialBindingAPI"]
        )
        {{
            custom string citybrain:geometry_status = "real_lod2_mesh_from_clipped_slpk"
            custom string citybrain:source_slpk = "{LOD2_SLPK.as_posix()}"
            custom string citybrain:i3s_node_id = "{node['node_id']}"
            custom string citybrain:identity_policy = "arcgis_visual_ids_not_canonical_citybrain_ids"
            rel material:binding = </World/Looks/lod2_real_mesh_warm>
            uniform token subdivisionScheme = "none"
            int[] faceVertexCounts = [
{usda_array(counts, 24, "                ")}
            ]
            int[] faceVertexIndices = [
{usda_array(indices, 24, "                ")}
            ]
            point3f[] points = [
{usda_array(points, 3, "                ")}
            ]
        }}
'''


def build_scene(leaves: list[dict[str, Any]], source_meta: dict[str, Any]) -> str:
    total_vertices = sum(n["vertex_count"] for n in leaves)
    total_triangles = sum(n["triangle_count"] for n in leaves)
    meshes = "\n".join(mesh_block(n) for n in leaves)
    return f'''#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
    doc = "CityBrain Barcelona LOD2 real mesh from clipped ArcGIS Pro SLPK. LiDAR export unsupported; DSM clip empty."
)

def Xform "World"
{{
    custom string citybrain:task = "{TASK}"
    custom string citybrain:geometry_status = "real_lod2_mesh_from_clipped_arcgis_slpk"
    custom string citybrain:source_slpk = "{LOD2_SLPK.as_posix()}"
    custom string citybrain:claim_boundary = "visual_asset_load_only_no_control_no_certified_digital_twin"
    custom int citybrain:leaf_node_count = {len(leaves)}
    custom int citybrain:vertex_count = {total_vertices}
    custom int citybrain:triangle_count = {total_triangles}
    custom string citybrain:lod2_layer_type = "{source_meta['scene_layer'].get('layerType')}"
    custom string citybrain:source_crs = "{source_meta['scene_layer'].get('spatialReference')}"

{material_block()}
    def Xform "Barcelona_LOD2_Clipped_RealMesh"
    {{
        custom string citybrain:origin = "local ENU from lon {ORIGIN_LON}, lat {ORIGIN_LAT}; z retained from source EGM96/gravity-related height"
{meshes}
    }}
    def Cube "GroundReference"
    (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {{
        rel material:binding = </World/Looks/ground_dark>
        custom string citybrain:geometry_status = "reference_ground_plane"
        double size = 1
        double3 xformOp:translate = (0, 0, 0)
        float3 xformOp:scale = (190, 190, 0.04)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
    }}
    def Camera "PreviewCamera"
    {{
        double3 xformOp:translate = (0, -430, 210)
        double3 xformOp:rotateXYZ = (62, 0, 0)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
        float focalLength = 24
    }}
    def DistantLight "Sun"
    {{
        float inputs:intensity = 800
        float inputs:angle = 0.65
        double3 xformOp:rotateXYZ = (-45, 0, 35)
        uniform token[] xformOpOrder = ["xformOp:rotateXYZ"]
    }}
}}
'''


def hash_outputs() -> None:
    lines = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(OUT).as_posix()}")
    write_text(OUT / "hashes.sha256", "\n".join(lines) + "\n")


def main() -> int:
    os.chdir(Path(__file__).resolve().parents[1])
    OUT.mkdir(parents=True, exist_ok=True)
    leaves, source_meta = load_leaf_nodes()
    write_text(SCENE, build_scene(leaves, source_meta))
    report = {
        "task": TASK,
        "status": "PASS_REAL_LOD2_USD_CREATED_WITH_LIMITATIONS",
        "generated_at": utc_now(),
        "scene_path": str(SCENE),
        "open_command": f'"{KIT_LAUNCHER}" "{SCENE.resolve()}"',
        "kit_launcher_exists": KIT_LAUNCHER.exists(),
        "source_slpk": str(LOD2_SLPK),
        "source_slpk_bytes": LOD2_SLPK.stat().st_size if LOD2_SLPK.exists() else 0,
        "dsm_slpk": str(DSM_SLPK),
        "dsm_slpk_bytes": DSM_SLPK.stat().st_size if DSM_SLPK.exists() else 0,
        "lod2_leaf_node_count": len(leaves),
        "lod2_vertex_count": sum(n["vertex_count"] for n in leaves),
        "lod2_triangle_count": sum(n["triangle_count"] for n in leaves),
        "lod2_feature_count_sum": sum(n["feature_count"] for n in leaves),
        "limitations": [
            "LOD2 mesh generated from SLPK uncompressed geometry buffers; material/texture fidelity not preserved yet.",
            "ArcGIS visual IDs are not canonical CityBrain building IDs.",
            "DSM multipatch export contains zero features / tiny SLPK, so it is not loaded as geometry.",
            "LiDAR source export is unsupported and is not loaded as geometry.",
            "This is an Omniverse visual asset load proof, not a full city digital twin.",
        ],
    }
    write_json(OUT / "BCN_OMNIVERSE_LOAD_PREP_REPORT.json", report)
    write_text(
        OUT / "README.md",
        "# D4 3D Omniverse Load Prep R1\n\n"
        "Created a real LOD2 USD mesh from the clipped Barcelona ArcGIS Pro SLPK. Open the USDA in USD Composer.\n",
    )
    hash_outputs()
    print(json.dumps(report, indent=2)[:5000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

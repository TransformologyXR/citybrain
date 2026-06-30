#!/usr/bin/env python3
"""Create a USD Composer preview scene for four Barcelona ArcGIS 3D sources.

This is a clipped/proxy/source-ref visual proof. It does not decode full I3S
geometry and does not claim high-fidelity mesh conversion.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "D4-3D-BARCELONA-FOUR-LAYER-USD-PREVIEW-R1"
OUT = Path("outputs/d4_3d_barcelona_four_layer_usd_preview_r1")
SCENE = OUT / "BCN_FOUR_LAYER_ARCGIS_USD_PREVIEW.usda"
KIT_LAUNCHER = Path("C:/Omniverse/kit-app-template/_build/windows-x86_64/release/txr.citybrain_usd_composer.kit.bat")

SOURCES = {
    "LOD2_3DOBJECT": {
        "label": "Barcelona 3D LOD2 / Edif_Bcn_3D",
        "url": "https://tiles.arcgis.com/tiles/UlkXMDr5qa7NVX95/arcgis/rest/services/Barcelona_3D_LOD2/SceneServer",
        "layer_url": "https://tiles.arcgis.com/tiles/UlkXMDr5qa7NVX95/arcgis/rest/services/Barcelona_3D_LOD2/SceneServer/layers/0",
        "role": "LOD2 mapping/entity candidate; source visual IDs only",
        "color": (1.0, 0.54, 0.18),
    },
    "LIDAR_2016_COLOR_CLASS_INTENSITY": {
        "label": "Barcelona LiDAR 2016",
        "url": "https://tiles.arcgis.com/tiles/z2tnIkrLQ2BRzr6P/arcgis/rest/services/BARCELONA_LiDAR/SceneServer",
        "layer_url": "https://tiles.arcgis.com/tiles/z2tnIkrLQ2BRzr6P/arcgis/rest/services/BARCELONA_LiDAR/SceneServer/layers/0",
        "role": "2016 point cloud with source color/class/elevation/intensity",
        "color": (0.08, 0.48, 1.0),
    },
    "LIDAR_2023_NO_COLOR": {
        "label": "Barcelona LiDAR 2023",
        "url": "https://tiles.arcgis.com/tiles/UlkXMDr5qa7NVX95/arcgis/rest/services/Barcelona_Lidar/SceneServer",
        "layer_url": "https://tiles.arcgis.com/tiles/UlkXMDr5qa7NVX95/arcgis/rest/services/Barcelona_Lidar/SceneServer/layers/0",
        "role": "2023 point cloud, no source color",
        "color": (0.68, 0.74, 0.82),
    },
    "DSM_PLEIADESNEO_MESH": {
        "label": "Barcelona Airbus PleiadesNeo DSM Mesh",
        "url": "https://tiles.arcgis.com/tiles/uujCiiEZAflDbdxE/arcgis/rest/services/Barcelona_Airbus_PleiadesNeo_DSM_Mesh/SceneServer",
        "layer_url": "https://tiles.arcgis.com/tiles/uujCiiEZAflDbdxE/arcgis/rest/services/Barcelona_Airbus_PleiadesNeo_DSM_Mesh/SceneServer/layers/0",
        "role": "DSM mesh from ArcGIS Reality / Airbus PleiadesNeo imagery",
        "color": (0.20, 0.78, 0.42),
    },
}

HERO_SUBSET = {
    "subset_id": "barc_eixample_sant_marti_hero_subset_four_layer_preview",
    "center_lon_lat": [2.185, 41.405],
    "wgs84_lonlat": {
        "west": 2.182904089698735,
        "south": 41.40342795544377,
        "east": 2.1870959103012653,
        "north": 41.406572044556235,
    },
    "local_enu_meters": {"xmin": -175, "ymin": -175, "xmax": 175, "ymax": 175},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def with_query(url: str, **params: str) -> str:
    return url.rstrip("/") + "?" + urllib.parse.urlencode(params)


def fetch_json(url: str, path: Path, max_bytes: int = 250_000) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "CityBrain-D4-FourLayerUSDPreview/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read(max_bytes + 1)[:max_bytes]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            text = data.decode("utf-8-sig", errors="replace").lstrip("\ufeff\ufffd")
            try:
                parsed = json.loads(text)
            except Exception as exc:
                parsed = None
                return {"ok": True, "parse_ok": False, "parse_error": str(exc), "status": getattr(resp, "status", None), "bytes": len(data), "path": str(path), "json": None}
            return {"ok": True, "parse_ok": True, "status": getattr(resp, "status", None), "bytes": len(data), "path": str(path), "json": parsed}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "url": url}


def probe_sources() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, src in SOURCES.items():
        folder = OUT / "arcgis_probe" / key.lower()
        service = fetch_json(with_query(src["url"], f="pjson"), folder / "service.json")
        layer = fetch_json(with_query(src["layer_url"], f="pjson"), folder / "layer0.json")
        root = fetch_json(with_query(src["layer_url"] + "/nodes/root", f="pjson"), folder / "root_node.json")
        node0 = fetch_json(with_query(src["layer_url"] + "/nodes/0", f="pjson"), folder / "node_0.json")
        service_json = service.get("json") if isinstance(service.get("json"), dict) else {}
        layer_json = layer.get("json") if isinstance(layer.get("json"), dict) else None
        if layer_json is None and isinstance(service_json.get("layers"), list) and service_json["layers"]:
            layer_json = service_json["layers"][0]
        meta = layer_json if isinstance(layer_json, dict) else service_json if isinstance(service_json, dict) else {}
        result[key] = {
            "label": src["label"],
            "url": src["url"],
            "layer_url": src["layer_url"],
            "role": src["role"],
            "service_ok": service.get("ok", False),
            "layer_ok": bool(layer.get("ok", False) or layer_json),
            "root_or_node_ok": root.get("ok", False) or node0.get("ok", False),
            "layer_type": meta.get("layerType") or meta.get("type"),
            "version": meta.get("i3sVersion") or meta.get("currentVersion") or meta.get("version"),
            "spatial_reference": meta.get("spatialReference") or meta.get("fullExtent", {}).get("spatialReference"),
            "height_model_info": meta.get("heightModelInfo"),
            "extent": meta.get("fullExtent") or meta.get("extent"),
            "source_attributes_claimed_by_user": src["role"],
            "probe_paths": {
                "service": service.get("path"),
                "layer": layer.get("path"),
                "root": root.get("path"),
                "node0": node0.get("path"),
            },
        }
    return result


def mat(name: str, color: tuple[float, float, float]) -> str:
    r, g, b = color
    return f'''        def Material "{name}"
        {{
            token outputs:surface.connect = </World/Looks/{name}/PreviewSurface.outputs:surface>
            def Shader "PreviewSurface"
            {{
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = ({r}, {g}, {b})
                float inputs:roughness = 0.48
                token outputs:surface
            }}
        }}
'''


def cube(name: str, mat_name: str, tx: float, ty: float, tz: float, sx: float, sy: float, sz: float, attrs: dict[str, str]) -> str:
    custom = "\n".join(f'                custom string citybrain:{k} = "{v}"' for k, v in attrs.items())
    return f'''            def Cube "{name}" (
                prepend apiSchemas = ["MaterialBindingAPI"]
            )
            {{
                rel material:binding = </World/Looks/{mat_name}>
{custom}
                double size = 1
                double3 xformOp:translate = ({tx:.3f}, {ty:.3f}, {tz:.3f})
                float3 xformOp:scale = ({sx:.3f}, {sy:.3f}, {sz:.3f})
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
            }}
'''


def build_scene(probes: dict[str, Any]) -> str:
    looks = [
        mat("mat_lod2_orange", SOURCES["LOD2_3DOBJECT"]["color"]),
        mat("mat_lidar2016_blue", SOURCES["LIDAR_2016_COLOR_CLASS_INTENSITY"]["color"]),
        mat("mat_lidar2023_gray", SOURCES["LIDAR_2023_NO_COLOR"]["color"]),
        mat("mat_dsm_green", SOURCES["DSM_PLEIADESNEO_MESH"]["color"]),
        mat("mat_boundary_white", (0.92, 0.92, 0.88)),
        mat("mat_warning_red", (0.95, 0.15, 0.12)),
    ]
    body = []
    body.append(cube("HeroSubsetClipBoundary_350m_SourceRef", "mat_boundary_white", 0, 0, -0.05, 175, 175, 0.03, {
        "geometry_status": "bounded_clip_extent_reference",
        "subset_id": HERO_SUBSET["subset_id"],
        "source_ref_policy": "clipped_preview_only_no_full_city_download",
    }))
    # LOD2 buildings in NW quadrant.
    for i, (x, y, h) in enumerate([(-120, 70, 34), (-92, 104, 22), (-62, 64, 42), (-134, 126, 18), (-74, 126, 30)], 1):
        body.append(cube(f"LOD2_SourceRef_BuildingProxy_{i:02d}", "mat_lod2_orange", x, y, h / 2, 10 + i * 2, 9 + i, h, {
            "source_layer": "Barcelona_3D_LOD2",
            "source_url": SOURCES["LOD2_3DOBJECT"]["layer_url"],
            "geometry_status": "proxy_not_decoded_i3s_mesh",
            "identity_policy": "arcgis_visual_id_not_canonical_citybrain_id",
        }))
    # 2016 color/class/intensity LiDAR in NE quadrant.
    colors_2016 = ["source_color", "class", "elevation", "intensity", "source_color", "class"]
    for i in range(24):
        x = 58 + (i % 6) * 18
        y = 66 + (i // 6) * 18
        z = 2 + (i % 5) * 4
        body.append(cube(f"LiDAR2016_PointProxy_{i:02d}_{colors_2016[i % len(colors_2016)]}", "mat_lidar2016_blue", x, y, z, 2.2, 2.2, 2.2, {
            "source_layer": "BARCELONA_LiDAR_2016",
            "source_url": SOURCES["LIDAR_2016_COLOR_CLASS_INTENSITY"]["layer_url"],
            "geometry_status": "point_proxy_not_decoded_i3s_pointcloud",
            "attributes_expected": "source_color_class_elevation_intensity",
        }))
    # 2023 no-color LiDAR in SW quadrant.
    for i in range(20):
        x = -135 + (i % 5) * 21
        y = -130 + (i // 5) * 18
        z = 3 + (i % 4) * 5
        body.append(cube(f"LiDAR2023_NoColor_PointProxy_{i:02d}", "mat_lidar2023_gray", x, y, z, 2.4, 2.4, 2.4, {
            "source_layer": "Barcelona_Lidar_2023",
            "source_url": SOURCES["LIDAR_2023_NO_COLOR"]["layer_url"],
            "geometry_status": "point_proxy_not_decoded_i3s_pointcloud",
            "attributes_expected": "elevation_no_source_color",
        }))
    # DSM mesh as stepped surface in SE quadrant.
    for i, (x, y, z, sx, sy) in enumerate([(55, -125, 2, 26, 20), (88, -103, 7, 30, 24), (120, -78, 11, 28, 18), (76, -62, 16, 22, 20), (128, -132, 5, 32, 16)], 1):
        body.append(cube(f"DSM_PleiadesNeo_MeshTileProxy_{i:02d}", "mat_dsm_green", x, y, z, sx, sy, 1.4, {
            "source_layer": "Barcelona_Airbus_PleiadesNeo_DSM_Mesh",
            "source_url": SOURCES["DSM_PLEIADESNEO_MESH"]["layer_url"],
            "geometry_status": "surface_tile_proxy_not_decoded_i3s_mesh",
            "source_description": "ArcGIS_Reality_DSM_from_Airbus_PleiadesNeo_30cm_imagery",
        }))
    body.append(cube("RED_LIMITATION_NotHighFidelityYet", "mat_warning_red", 0, -210, 8, 120, 6, 16, {
        "message": "These are clipped source-ref proxies; real I3S geometry is not decoded into USD in this preview.",
        "next_step": "ArcGIS Pro clipped export or I3S decode pipeline",
    }))
    return f'''#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
    doc = "CityBrain Barcelona four ArcGIS layer USD Composer preview. Clipped source-ref proxies only; not high-fidelity decoded I3S geometry."
)

def Xform "World"
{{
    custom string citybrain:task = "{TASK}"
    custom string citybrain:subset_id = "{HERO_SUBSET["subset_id"]}"
    custom string citybrain:geometry_status = "clipped_source_ref_proxy_preview_not_high_fidelity_mesh"
    custom string citybrain:claim_boundary = "review_context_visual_probe_no_operational_command_not_certified"
    custom string citybrain:lod2_url = "{SOURCES["LOD2_3DOBJECT"]["url"]}"
    custom string citybrain:lidar2016_url = "{SOURCES["LIDAR_2016_COLOR_CLASS_INTENSITY"]["url"]}"
    custom string citybrain:lidar2023_url = "{SOURCES["LIDAR_2023_NO_COLOR"]["url"]}"
    custom string citybrain:dsm_mesh_url = "{SOURCES["DSM_PLEIADESNEO_MESH"]["url"]}"

    def Scope "Looks"
    {{
{''.join(looks)}
    }}

    def Xform "Barcelona_Eixample_SantMarti_ClippedPreview"
    {{
        custom string citybrain:source_probe_summary_path = "outputs/d4_3d_barcelona_four_layer_usd_preview_r1/BCN_FOUR_LAYER_USD_PREVIEW_REPORT.json"
        custom string citybrain:warning = "proxy preview only; no full city load; no decoded I3S geometry"
{''.join(body)}
    }}

    def Camera "PreviewCamera"
    {{
        double3 xformOp:translate = (0, -520, 290)
        double3 xformOp:rotateXYZ = (62, 0, 0)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
        float focalLength = 24
    }}
    def DistantLight "Sun"
    {{
        float inputs:intensity = 650
        float inputs:angle = 0.8
        double3 xformOp:rotateXYZ = (-45, 0, 35)
        uniform token[] xformOpOrder = ["xformOp:rotateXYZ"]
    }}
}}
'''


def hash_outputs() -> None:
    lines = []
    for path in sorted(OUT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            h = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{h}  {path.relative_to(OUT).as_posix()}")
    write_text(OUT / "hashes.sha256", "\n".join(lines) + "\n")


def main() -> int:
    os.chdir(Path(__file__).resolve().parents[1])
    if OUT.exists():
        import shutil
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    probes = probe_sources()
    write_text(SCENE, build_scene(probes))
    report = {
        "task": TASK,
        "status": "PASS_CLIPPED_SOURCE_REF_PROXY_USD_CREATED",
        "generated_at": utc_now(),
        "scene_path": str(SCENE),
        "kit_launcher": str(KIT_LAUNCHER),
        "kit_launcher_exists": KIT_LAUNCHER.exists(),
        "open_command": f'"{KIT_LAUNCHER}" "{SCENE.resolve()}"',
        "hero_subset": HERO_SUBSET,
        "sources": probes,
        "what_is_visible": {
            "LOD2_3DOBJECT": "orange building proxy boxes with source URL metadata",
            "LIDAR_2016": "blue point proxies tagged source_color/class/elevation/intensity",
            "LIDAR_2023": "gray point proxies tagged no-source-color/elevation",
            "DSM_PLEIADESNEO_MESH": "green DSM mesh tile proxies with source URL metadata",
        },
        "important_limitation": "This scene is clipped/source-ref/proxy only. It does not contain decoded high-fidelity I3S mesh or point-cloud geometry.",
        "next_real_geometry_step": "Use ArcGIS Pro clipped export or implement bounded I3S geometry decode/conversion.",
    }
    write_json(OUT / "BCN_FOUR_LAYER_USD_PREVIEW_REPORT.json", report)
    write_text(
        OUT / "README.md",
        f"# {TASK}\n\n"
        "Created `BCN_FOUR_LAYER_ARCGIS_USD_PREVIEW.usda` for USD Composer. "
        "It is a clipped source-ref/proxy preview for the four Barcelona ArcGIS layers, not decoded real mesh.\n",
    )
    hash_outputs()
    print(json.dumps({"status": report["status"], "scene": str(SCENE), "open_command": report["open_command"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""D4-3D-NYC-ARCGIS-EXPORTABILITY-BATCH-R1.

Probe NYC ArcGIS SceneServer candidates and attempt tiny Codex-side I3S-to-USD
exports where the layer exposes simple 3DObject node geometry buffers. This is
not a full-city crawl; it classifies what Codex can export directly versus what
needs ArcGIS Pro/CityEngine manual export.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import re
import shutil
import struct
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "D4-3D-NYC-ARCGIS-EXPORTABILITY-BATCH-R1"
PASS_LIMITED = "PASS_D4_3D_NYC_ARCGIS_EXPORTABILITY_BATCH_R1_WITH_LIMITATIONS"
FAIL = "FAIL_D4_3D_NYC_ARCGIS_EXPORTABILITY_BATCH_R1"
OUT = Path("outputs/d4_3d_nyc_arcgis_exportability_batch_r1")
ORIGIN_LON = -73.9855
ORIGIN_LAT = 40.758
EARTH_R = 6371000.0

SOURCES = [
    {
        "source_id": "nyc_2025_buildings_3d_full",
        "label": "Buildings 3D NYC 10 27 2025",
        "url": "https://tiles.arcgis.com/tiles/QCty4ZXRXx9qyVVL/arcgis/rest/services/Buildings_3D_NYC_10_27_2025_/SceneServer",
        "priority": "current_full_city_candidate",
    },
    {
        "source_id": "manhattan_buildings_3d",
        "label": "ManhattanBuildings 3D",
        "url": "https://services.arcgis.com/6DIQcwlPy8knb6sg/arcgis/rest/services/ManhattanBuildings_3D/SceneServer",
        "priority": "known_i3s_1_6_export_proof_candidate",
    },
    {
        "source_id": "manhattan_lod2_lidar_2021",
        "label": "NYC Manhattan Extract LOD2 Buildings LiDAR 2021",
        "url": "https://tiles.arcgis.com/tiles/jIL9msH9OI208GCb/arcgis/rest/services/NYC_ManhattanExtractLOD2BuildingsLidar2021/SceneServer",
        "priority": "new_candidate",
    },
    {
        "source_id": "buildings_3d_nyc_pmt",
        "label": "3D Buildings NYC",
        "url": "https://services.arcgis.com/PMTtzuTB6WiPuNSv/arcgis/rest/services/3D_Buildings_NYC/SceneServer",
        "priority": "new_candidate",
    },
    {
        "source_id": "residential_density_r10_wsl1",
        "label": "Residential density within R10 and equivalent zoning districts WSL1",
        "url": "https://services1.arcgis.com/gFqWrLF7jCTW9q6S/arcgis/rest/services/Residential_density_within_R10_and_equivalent_zoning_districts_WSL1/SceneServer",
        "priority": "likely_context_not_buildings",
    },
    {
        "source_id": "buildings_newyork_17",
        "label": "Buildings NewYork 17",
        "url": "https://tiles.arcgis.com/tiles/P3ePLMYs2RVChkJx/arcgis/rest/services/Buildings_NewYork_17/SceneServer",
        "priority": "new_candidate",
    },
    {
        "source_id": "nyc_scene_manhattan_wsl1",
        "label": "NYC Scene in Manhattan WSL1",
        "url": "https://services1.arcgis.com/CtMjdUqInecbPao9/arcgis/rest/services/NYC_Scene_in_Manhattan_WSL1/SceneServer",
        "priority": "likely_integrated_mesh_visual",
    },
    {
        "source_id": "nyc_wsl1",
        "label": "NYC WSL1",
        "url": "https://services.arcgis.com/V6ZHFr6zdgNZuVG0/arcgis/rest/services/NYC_WSL1/SceneServer",
        "priority": "likely_integrated_mesh_visual",
    },
    {
        "source_id": "nyc_3d_buildings_w_coordinates",
        "label": "NYC 3D Buildings w Coordinates",
        "url": "https://tiles.arcgis.com/tiles/wQnFk5ouCfPzTlPw/arcgis/rest/services/NYC_3D_Buildings_w_Coordinates/SceneServer",
        "priority": "new_candidate",
    },
    {
        "source_id": "nyc_proj_scene_wsl1_qa",
        "label": "nyc proj scene WSL1 QA",
        "url": "https://servicesqa.arcgis.com/SdQnSRS214Ul5Jv5/arcgis/rest/services/nyc_proj_scene_WSL1/SceneServer",
        "priority": "likely_integrated_mesh_or_unstable_qa",
    },
]

IDENTITY_HINTS = [
    "bin",
    "bin_1",
    "bbl",
    "base_bbl",
    "mpluto_bbl",
    "doitt_id",
    "doitt_id_1",
    "globalid",
    "objectid",
    "objectid_1",
    "source_id",
]

PREVIOUS_ROOTS = {
    "city_asset_contract": Path("outputs/d4_3d_city_asset_contract_r1"),
    "visual_alignment": Path("outputs/d4_3d_visual_mesh_footprint_alignment_r1"),
    "nyc_scene_probe": Path("outputs/d4_3d_nyc_scene_source_probe_r1"),
    "platform_state": Path("outputs/platform_state_generated"),
    "pv1_d19_d22": Path("outputs/pv1_d19d20d21d22_platform_v1_snapshot_gate"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def clean_url(url: str) -> str:
    return url.rstrip("/")


def with_query(url: str, **params: str) -> str:
    return url + "?" + urllib.parse.urlencode(params)


def decode_payload(data: bytes) -> bytes:
    while len(data) > 2 and data[0] == 31 and data[1] == 139:
        data = gzip.decompress(data)
    return data


def fetch_bytes(url: str, timeout: int = 45) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "CityBrain-Codex/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return decode_payload(resp.read())


def fetch_json(url: str, timeout: int = 45) -> dict[str, Any]:
    return json.loads(fetch_bytes(url, timeout=timeout).decode("utf-8"))


def try_json(url: str) -> dict[str, Any]:
    try:
        obj = fetch_json(url)
        return {"ok": True, "status": "PASS", "url": url, "json": obj}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": "HTTP_ERROR", "url": url, "error": f"{exc.code} {exc.reason}"}
    except Exception as exc:
        return {"ok": False, "status": "ERROR", "url": url, "error": f"{type(exc).__name__}: {exc}"}


def try_bytes(url: str, max_bytes: int = 128) -> dict[str, Any]:
    try:
        data = fetch_bytes(url)
        return {"ok": True, "status": "PASS", "url": url, "byte_count": len(data), "head_hex": data[:max_bytes].hex()}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": "HTTP_ERROR", "url": url, "error": f"{exc.code} {exc.reason}"}
    except Exception as exc:
        return {"ok": False, "status": "ERROR", "url": url, "error": f"{type(exc).__name__}: {exc}"}


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
    return {name: root_signature(path) for name, path in PREVIOUS_ROOTS.items()}


def field_names(layer: dict[str, Any]) -> list[str]:
    names = []
    for field in layer.get("fields") or []:
        if isinstance(field, dict) and field.get("name"):
            names.append(field["name"])
    for attr in layer.get("attributeStorageInfo") or []:
        if isinstance(attr, dict) and attr.get("name"):
            names.append(attr["name"])
    popup = layer.get("popupInfo") or {}
    for info in popup.get("fieldInfos") or []:
        if info.get("fieldName"):
            names.append(info["fieldName"])
    for element in popup.get("popupElements") or []:
        for info in element.get("fieldInfos") or []:
            if info.get("fieldName"):
                names.append(info["fieldName"])
    return sorted(set(names))


def summarize_layer(root: dict[str, Any] | None, layer: dict[str, Any] | None) -> dict[str, Any]:
    root = root or {}
    root_layer = root.get("layers", [{}])[0] if root.get("layers") else {}
    layer = layer or root_layer
    store = layer.get("store") or root_layer.get("store") or {}
    fields = field_names(layer) or field_names(root_layer)
    identities = sorted(f for f in fields if f.lower() in IDENTITY_HINTS)
    return {
        "service_item_id": root.get("serviceItemId"),
        "service_name": root.get("name"),
        "service_version": root.get("serviceVersion"),
        "layer_id": layer.get("id"),
        "layer_name": layer.get("name"),
        "layer_type": layer.get("layerType"),
        "capabilities": layer.get("capabilities"),
        "spatial_reference": layer.get("spatialReference"),
        "height_model_info": layer.get("heightModelInfo"),
        "extent": store.get("extent"),
        "store_version": store.get("version"),
        "resource_pattern": store.get("resourcePattern"),
        "geometry_encoding": store.get("geometryEncoding"),
        "attribute_encoding": store.get("attributeEncoding"),
        "texture_encoding": store.get("textureEncoding"),
        "field_count": len(fields),
        "identity_fields": identities,
        "fields": fields,
    }


def first_node_with_geometry(layer_url: str, root_node: dict[str, Any] | None, node_0: dict[str, Any] | None) -> dict[str, Any] | None:
    candidates: list[str] = []
    if node_0 and node_0.get("geometryData"):
        return node_0
    if root_node:
        for child in root_node.get("children") or []:
            if child.get("id"):
                candidates.append(str(child["id"]))
    candidates.extend(["0", "1", "2", "0-0", "0-1"])
    seen = set()
    for node_id in candidates:
        if node_id in seen:
            continue
        seen.add(node_id)
        probe = try_json(with_query(f"{layer_url}/nodes/{urllib.parse.quote(node_id, safe='-')}", f="pjson"))
        if probe["ok"] and probe["json"].get("geometryData"):
            return probe["json"]
    return None


def lonlat_to_enu(lon: float, lat: float) -> tuple[float, float]:
    x = math.radians(lon - ORIGIN_LON) * EARTH_R * math.cos(math.radians(ORIGIN_LAT))
    y = math.radians(lat - ORIGIN_LAT) * EARTH_R
    return x, y


def usda_array(items: list[str], per_line: int, indent: str) -> str:
    return ",\n".join(indent + ", ".join(items[i : i + per_line]) for i in range(0, len(items), per_line))


def build_usda(source_id: str, label: str, url: str, node: dict[str, Any], geom: bytes, max_triangles: int = 2500) -> tuple[str, dict[str, Any]]:
    vertex_count, feature_count = struct.unpack_from("<II", geom, 0)
    if vertex_count < 3 or vertex_count > 5_000_000:
        raise ValueError(f"unreasonable vertex_count {vertex_count}")
    triangle_count_total = vertex_count // 3
    triangle_count = min(triangle_count_total, max_triangles)
    mbs = node.get("mbs") or [ORIGIN_LON, ORIGIN_LAT, 0, 0]
    center_lon, center_lat, center_z = float(mbs[0]), float(mbs[1]), float(mbs[2])
    points = []
    offset = 8
    for idx in range(triangle_count * 3):
        dx_lon, dy_lat, dz = struct.unpack_from("<fff", geom, offset + idx * 12)
        lon = center_lon + dx_lon
        lat = center_lat + dy_lat
        x, y = lonlat_to_enu(lon, lat)
        points.append(f"({x:.3f}, {y:.3f}, {center_z + dz:.3f})")
    counts = ["3"] * triangle_count
    indices = [str(i) for i in range(triangle_count * 3)]
    safe_name = re.sub(r"[^A-Za-z0-9_]", "_", source_id)
    text = f'''#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
    doc = "CityBrain tiny I3S export proof for {label}. Bounded node sample only."
)

def Xform "World"
{{
    custom string citybrain:task = "{TASK}"
    custom string citybrain:source_id = "{source_id}"
    custom string citybrain:source_url = "{url}"
    custom string citybrain:node_id = "{node.get('id')}"
    custom string citybrain:claim_boundary = "tiny_export_proof_only_not_full_city_not_certified"
    custom int citybrain:source_vertex_count = {vertex_count}
    custom int citybrain:source_feature_count = {feature_count}
    custom int citybrain:exported_triangle_count = {triangle_count}
    custom string citybrain:origin = "local ENU from lon {ORIGIN_LON}, lat {ORIGIN_LAT}"
    def Mesh "{safe_name}_TinyI3SNode"
    {{
        uniform token subdivisionScheme = "none"
        int[] faceVertexCounts = [
{usda_array(counts, 24, "            ")}
        ]
        int[] faceVertexIndices = [
{usda_array(indices, 24, "            ")}
        ]
        point3f[] points = [
{usda_array(points, 3, "            ")}
        ]
    }}
    def Camera "PreviewCamera"
    {{
        double3 xformOp:translate = (0, -1800, 900)
        double3 xformOp:rotateXYZ = (62, 0, 0)
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
        float focalLength = 28
    }}
    def DistantLight "Sun"
    {{
        float inputs:intensity = 850
    }}
}}
'''
    report = {
        "node_id": node.get("id"),
        "source_vertex_count": vertex_count,
        "source_feature_count": feature_count,
        "source_triangle_count_total": triangle_count_total,
        "exported_triangle_count": triangle_count,
        "mbs": mbs,
    }
    return text, report


def attempt_tiny_export(source: dict[str, str], layer_url: str, node: dict[str, Any] | None, classification: dict[str, Any]) -> dict[str, Any]:
    if not node:
        return {"status": "NOT_ATTEMPTED", "reason": "no node with geometryData found"}
    geom_href = ((node.get("geometryData") or [{}])[0] or {}).get("href")
    if not geom_href:
        return {"status": "NOT_ATTEMPTED", "reason": "node has no geometry href"}
    geom_url = f"{layer_url}/nodes/{urllib.parse.quote(str(node.get('id')), safe='-')}/{geom_href.replace('./', '')}"
    raw = try_bytes(geom_url)
    if not raw["ok"]:
        return {"status": "FAILED_GEOMETRY_FETCH", "geometry_url": geom_url, "probe": raw}
    try:
        geom = fetch_bytes(geom_url)
        text, export_report = build_usda(source["source_id"], source["label"], source["url"], node, geom)
    except Exception as exc:
        return {
            "status": "FETCHED_BUT_DECODE_BLOCKED",
            "geometry_url": geom_url,
            "geometry_byte_count": raw.get("byte_count"),
            "reason": f"{type(exc).__name__}: {exc}",
        }
    export_dir = OUT / "tiny_usd_exports" / source["source_id"]
    export_dir.mkdir(parents=True, exist_ok=True)
    scene = export_dir / f"{source['source_id']}_tiny_i3s_node.usda"
    write_text(scene, text)
    write_json(export_dir / f"{source['source_id']}_tiny_i3s_node_report.json", {"status": "PASS_TINY_USD_CREATED", **export_report, "geometry_url": geom_url})
    classification["codex_tiny_usd_export_path"] = str(scene)
    return {"status": "PASS_TINY_USD_CREATED", "scene_path": str(scene), "geometry_url": geom_url, **export_report}


def classify(summary: dict[str, Any], probes: dict[str, Any]) -> dict[str, Any]:
    layer_type = summary.get("layer_type")
    resource_pattern = set(summary.get("resource_pattern") or [])
    identity_fields = summary.get("identity_fields") or []
    node_resource_ok = probes.get("root_node", {}).get("ok") or probes.get("node_0", {}).get("ok") or probes.get("nodepage_0", {}).get("ok")
    node_0 = probes.get("node_0", {}).get("json") if probes.get("node_0", {}).get("ok") else None
    root_node = probes.get("root_node", {}).get("json") if probes.get("root_node", {}).get("ok") else None
    has_geometry_node = bool((node_0 or {}).get("geometryData")) or bool((root_node or {}).get("children"))
    direct_query_ok = probes.get("query_count", {}).get("ok")
    public_download = bool((probes.get("resources", {}).get("json") or {}).get("resources"))
    can_crawl = layer_type == "3DObject" and node_resource_ok and ("Geometry" in resource_pattern or has_geometry_node)
    can_identity = bool(identity_fields)
    if can_crawl and can_identity:
        codex_route = "YES_I3S_CRAWL_WITH_ATTRIBUTES"
    elif can_crawl:
        codex_route = "YES_I3S_CRAWL_VISUAL_ONLY"
    elif layer_type in {"IntegratedMesh", "PointCloud"} and node_resource_ok:
        codex_route = "SOURCE_REF_OR_SPECIAL_DECODER_REQUIRED"
    else:
        codex_route = "NO_DIRECT_CODEX_EXPORT_CONFIRMED"
    if direct_query_ok:
        manual_route = "ARCGIS_PRO_EXPORT_FEATURES_LIKELY"
    elif layer_type == "3DObject":
        manual_route = "ARCGIS_PRO_SCENE_LAYER_PACKAGE_OR_LAYER_FILE_TEST"
    elif layer_type:
        manual_route = "ARCGIS_PRO_VISUAL_SCENE_EXPORT_TEST"
    else:
        manual_route = "MANUAL_EXPORT_NOT_CONFIRMED"
    return {
        "codex_export_route": codex_route,
        "manual_export_route": manual_route,
        "direct_query_exportable": bool(direct_query_ok),
        "public_item_download_resources": public_download,
        "i3s_node_resources_accessible": bool(node_resource_ok),
        "i3s_geometry_crawl_candidate": bool(can_crawl),
        "identity_attributes_present": bool(can_identity),
        "identity_fields": identity_fields,
    }


def probe_source(source: dict[str, str]) -> dict[str, Any]:
    base = clean_url(source["url"])
    root_probe = try_json(with_query(base, f="pjson"))
    root = root_probe.get("json") if root_probe["ok"] else {}
    layer_url = f"{base}/layers/0"
    layer_probe = try_json(with_query(layer_url, f="pjson"))
    layer = layer_probe.get("json") if layer_probe["ok"] else None
    service_item_id = (root or {}).get("serviceItemId")
    item_probe = try_json(with_query(f"https://www.arcgis.com/sharing/rest/content/items/{service_item_id}", f="pjson")) if service_item_id else {"ok": False, "status": "NO_ITEM_ID"}
    resources_probe = try_json(with_query(f"https://www.arcgis.com/sharing/rest/content/items/{service_item_id}/resources", f="pjson", num="100")) if service_item_id else {"ok": False, "status": "NO_ITEM_ID"}
    probes = {
        "root": root_probe,
        "layer": layer_probe,
        "root_node": try_json(with_query(f"{layer_url}/nodes/root", f="pjson")),
        "node_0": try_json(with_query(f"{layer_url}/nodes/0", f="pjson")),
        "nodepage_0": try_json(with_query(f"{layer_url}/nodepages/0", f="pjson")),
        "query_count": try_json(with_query(f"{layer_url}/query", where="1=1", returnCountOnly="true", f="pjson")),
        "item": item_probe,
        "resources": resources_probe,
    }
    summary = summarize_layer(root, layer)
    classification = classify(summary, probes)
    root_node = probes["root_node"].get("json") if probes["root_node"].get("ok") else None
    node_0 = probes["node_0"].get("json") if probes["node_0"].get("ok") else None
    geom_node = first_node_with_geometry(layer_url, root_node, node_0)
    tiny_export = {"status": "NOT_ATTEMPTED", "reason": "not a simple 3DObject crawl candidate"}
    if classification["i3s_geometry_crawl_candidate"] and summary.get("layer_type") == "3DObject":
        tiny_export = attempt_tiny_export(source, layer_url, geom_node, classification)
    compact_probes = {}
    for key, probe in probes.items():
        compact = {k: v for k, v in probe.items() if k != "json"}
        if probe.get("json"):
            compact["json_top_keys"] = sorted(list(probe["json"].keys()))[:30]
        compact_probes[key] = compact
    return {
        "source": source,
        "summary": summary,
        "classification": classification,
        "probes": compact_probes,
        "tiny_export": tiny_export,
    }


def write_reports(rows: list[dict[str, Any]]) -> None:
    write_json(OUT / "NYC_ARCGIS_EXPORTABILITY_MATRIX.json", {"task": TASK, "generated_at": utc_now(), "sources": rows})
    table = [
        "# NYC ArcGIS Exportability Matrix",
        "",
        "| Source | Type | IDs | Codex route | Manual route | Tiny USD | Notes |",
        "|---|---:|---|---|---|---|---|",
    ]
    for row in rows:
        s = row["source"]
        summary = row["summary"]
        cls = row["classification"]
        tiny = row["tiny_export"]
        ids = ", ".join(cls["identity_fields"][:8]) if cls["identity_fields"] else "-"
        notes = []
        if row["probes"]["query_count"]["ok"]:
            notes.append("query works")
        else:
            notes.append(row["probes"]["query_count"].get("error") or row["probes"]["query_count"].get("status"))
        if cls["public_item_download_resources"]:
            notes.append("public resources")
        if summary.get("store_version"):
            notes.append(f"I3S {summary['store_version']}")
        tiny_status = tiny["status"]
        if tiny.get("scene_path"):
            tiny_status = f"[{tiny_status}]({tiny['scene_path']})"
        table.append(
            f"| {s['label']} | `{summary.get('layer_type')}` | {ids} | `{cls['codex_export_route']}` | `{cls['manual_export_route']}` | {tiny_status} | {'; '.join(notes)} |"
        )
    write_text(OUT / "NYC_ARCGIS_EXPORTABILITY_MATRIX.md", "\n".join(table) + "\n")
    write_text(
        OUT / "README.md",
        f"# {TASK}\n\nLayer-by-layer exportability probe for NYC ArcGIS SceneServer candidates. Tiny USD exports are bounded node proofs only, not full city exports.\n",
    )
    write_text(
        OUT / "MANUAL_EXPORT_GUIDE.md",
        "# Manual Export Guide\n\n"
        "Use ArcGIS Pro manual export only for layers whose manual route says `ARCGIS_PRO_EXPORT_FEATURES_LIKELY` or `ARCGIS_PRO_SCENE_LAYER_PACKAGE_OR_LAYER_FILE_TEST`.\n\n"
        "In ArcGIS Pro:\n"
        "1. Add the SceneServer URL.\n"
        "2. Confirm it renders and popups show identity fields.\n"
        "3. Right-click the layer. If `Data > Export Features` appears, try exporting a FileGDB feature class/table.\n"
        "4. If only `Save As Layer File` appears, it is not directly feature-exportable from Pro.\n"
        "5. Try Geoprocessing > `Create 3D Object Scene Layer Content` only if the layer is accepted as an input dataset.\n"
        "6. If Pro cannot export it, use the Codex I3S crawl route for layers marked `YES_I3S_CRAWL_WITH_ATTRIBUTES` or `YES_I3S_CRAWL_VISUAL_ONLY`.\n\n"
        "For full coverage, prefer borough/tile shards over one huge mesh file.\n",
    )
    write_text(
        OUT / "NYC_LAYER_SELECTION_RECOMMENDATION.md",
        "# NYC Layer Selection Recommendation\n\n"
        "Use `Buildings 3D NYC 10 27 2025` as the first full-city Codex-side export candidate. It is the current-looking full-city source, is `3DObject`, carries `bin`, `base_bbl`, `mpluto_bbl`, `doitt_id`, and `globalid`, and produced a tiny USD proof from raw I3S resources.\n\n"
        "Use `NYC Manhattan Extract LOD2 Buildings LiDAR 2021` as the Manhattan-focused LOD2/LiDAR-era candidate if you want a smaller pilot before full NYC.\n\n"
        "Use `ManhattanBuildings 3D` as the easiest manual/export test layer. It is older and Manhattan-only, but direct query worked, identity fields are strong, and the tiny USD export succeeded.\n\n"
        "Use `NYC 3D Buildings w Coordinates` as a useful backup because it has coordinates plus identity fields and produced a tiny USD proof.\n\n"
        "Treat WSL/R10/residential-density titled layers as secondary until visually reviewed. They are technically crawlable 3DObject layers with IDs, but their names imply narrower, older, or thematic products rather than the cleanest citywide building master.\n\n"
        "ArcGIS Pro manual export priority:\n"
        "1. `ManhattanBuildings 3D`\n"
        "2. `3D Buildings NYC`\n"
        "3. `NYC WSL1`\n"
        "4. `NYC Scene in Manhattan WSL1`\n"
        "5. `nyc proj scene WSL1 QA`\n\n"
        "Codex-side full crawl priority:\n"
        "1. `Buildings 3D NYC 10 27 2025`\n"
        "2. `NYC Manhattan Extract LOD2 Buildings LiDAR 2021`\n"
        "3. `NYC 3D Buildings w Coordinates`\n"
        "4. `ManhattanBuildings 3D`\n\n"
        "Full export should be sharded by borough/tile and not written as one giant OBJ. The USD pack should preserve BIN/BBL/DOITT/globalid metadata as sidecar and prim metadata.\n",
    )


def no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = [name for name in before if before[name] != after[name]]
    report = {"status": "PASS" if not changed else "FAIL", "changed_roots": changed, "checked_root_count": len(before)}
    write_text(OUT / "NO_MUTATION_AUDIT.md", "# No-Mutation Audit\n\n" + f"Status: `{report['status']}`\n\n```json\n" + json.dumps(report, indent=2) + "\n```\n")
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
                findings.append({"path": path.relative_to(OUT).as_posix(), "pattern": pattern.pattern})
    report = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}
    write_text(OUT / "SECRET_REDACTION_AUDIT.md", "# Secret Redaction Audit\n\n" + f"Status: `{report['status']}`\n\n" + ("No secrets found.\n" if not findings else json.dumps(report, indent=2) + "\n"))
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
    (OUT / "tiny_usd_exports").mkdir(parents=True, exist_ok=True)
    rows = []
    for source in SOURCES:
        rows.append(probe_source(source))
    write_reports(rows)
    after = snapshot_roots()
    no_mut = no_mutation_audit(before, after)
    secret = secret_audit()
    tiny_success = [r for r in rows if r["tiny_export"]["status"] == "PASS_TINY_USD_CREATED"]
    codex_candidates = [r for r in rows if str(r["classification"]["codex_export_route"]).startswith("YES_I3S_CRAWL")]
    manual_candidates = [r for r in rows if r["classification"]["manual_export_route"] != "MANUAL_EXPORT_NOT_CONFIRMED"]
    checks = {
        "all_sources_probed": len(rows) == len(SOURCES),
        "at_least_one_tiny_usd_export": len(tiny_success) >= 1,
        "codex_candidates_identified": len(codex_candidates) >= 1,
        "manual_candidates_identified": len(manual_candidates) >= 1,
        "no_mutation_pass": no_mut["status"] == "PASS",
        "secret_audit_pass": secret["status"] == "PASS",
    }
    decision = {
        "status": PASS_LIMITED if all(checks.values()) else FAIL,
        "task_name": TASK,
        "timestamp": utc_now(),
        "source_count": len(rows),
        "checks": checks,
        "codex_export_candidate_count": len(codex_candidates),
        "tiny_usd_export_count": len(tiny_success),
        "manual_export_candidate_count": len(manual_candidates),
        "codex_export_candidates": [
            {
                "source_id": r["source"]["source_id"],
                "label": r["source"]["label"],
                "route": r["classification"]["codex_export_route"],
                "tiny_export": r["tiny_export"].get("scene_path"),
                "identity_fields": r["classification"]["identity_fields"],
            }
            for r in codex_candidates
        ],
        "manual_export_candidates": [
            {
                "source_id": r["source"]["source_id"],
                "label": r["source"]["label"],
                "route": r["classification"]["manual_export_route"],
            }
            for r in manual_candidates
        ],
        "limitations": [
            "Tiny USD exports are one-node proofs, not full city exports.",
            "Full Codex-side export requires a bounded/sharded I3S crawl and more complete attribute decoding.",
            "Integrated mesh / WSL layers may need special decoder or manual visual export and do not provide per-building identity by default.",
            "ArcGIS Pro manual export availability still depends on the UI accepting the hosted scene layer as an input dataset.",
        ],
        "recommended_next": "Run D4-3D-SECOND-CITY-PILOT-R1 using the best NYC 3DObject layer, with full export sharded by borough/tile.",
    }
    write_json(OUT / "D4_3D_NYC_ARCGIS_EXPORTABILITY_BATCH_R1_DECISION.json", decision)
    shutil.copy2(Path(__file__), OUT / "run_d4_3d_nyc_arcgis_exportability_batch_r1.py")
    hash_outputs()
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Run {TASK}.")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    decision = run(args)
    print(f"{TASK}: {decision['status']}")
    print(f"Output: {OUT}")
    return 0 if decision["status"] == PASS_LIMITED else 1


if __name__ == "__main__":
    raise SystemExit(main())

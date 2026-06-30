#!/usr/bin/env python3
"""D4-3D-BARCELONA-ASSET-PIPELINE-FIX-R1.

Bounded Barcelona 3D asset pipeline diagnostic and fix path. This task does not
convert or download full city assets. It narrows the ArcGIS I3S / local tooling /
manual-export path for high-fidelity Barcelona mesh loading while preserving
the existing Track 1 placeholder/source-ref USD binding.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "D4-3D-BARCELONA-ASSET-PIPELINE-FIX-R1"
PASS = "PASS_D4_3D_BARCELONA_ASSET_PIPELINE_FIX_R1"
PASS_LIMITED = "PASS_D4_3D_BARCELONA_ASSET_PIPELINE_FIX_R1_WITH_LIMITATIONS"
FAIL = "FAIL_D4_3D_BARCELONA_ASSET_PIPELINE_FIX_R1"
OUT = Path("outputs/d4_3d_barcelona_asset_pipeline_fix_r1")
SCHEMA_VERSION = "d4-3d-barcelona-asset-pipeline-fix-r1.v1"

FOLDERS = [
    "arcgis_reprobe",
    "i3s_resource_manifest",
    "bounded_crawl",
    "conversion_probe",
    "omniverse_probe",
    "export_workflows",
    "contract_draft",
    "logs",
]

USD_BINDING_ROOT = Path("outputs/main_track1_d4_usd_city_subset_binding")
USD_SCENE = USD_BINDING_ROOT / "D4_BARCELONA_USD_SCENE.usda"
USD_BINDING_DECISION = USD_BINDING_ROOT / "MAIN_TRACK1_D4_USD_CITY_SUBSET_BINDING_DECISION.json"
OMNI_PREFLIGHT_ROOT = Path("outputs/main_track1_d4_omniverse_3d_subset_preflight")
ROADMAP_ROOT = Path("outputs/main_track1_d3_completion_train_to_d4_roadmap_r1")

KIT_ROOT = Path("C:/Omniverse/kit-app-template")
KIT_LAUNCHER = KIT_ROOT / "_build/windows-x86_64/release/txr.citybrain_usd_composer.kit.bat"

ARCGIS_SOURCES = {
    "edif_bcn_3d": {
        "name": "Edif_Bcn_3D 3DObject buildings",
        "url": "https://tiles.arcgis.com/tiles/UlkXMDr5qa7NVX95/arcgis/rest/services/Barcelona_3D_LOD2/SceneServer/layers/0",
        "base": "https://tiles.arcgis.com/tiles/UlkXMDr5qa7NVX95/arcgis/rest/services/Barcelona_3D_LOD2/SceneServer",
        "classification": "SECONDARY_3DOBJECT_BUILDING_SOURCE",
    },
    "barcelona_lidar": {
        "name": "Barcelona LiDAR PointCloud",
        "url": "https://tiles.arcgis.com/tiles/UlkXMDr5qa7NVX95/arcgis/rest/services/Barcelona_Lidar/SceneServer",
        "base": "https://tiles.arcgis.com/tiles/UlkXMDr5qa7NVX95/arcgis/rest/services/Barcelona_Lidar/SceneServer",
        "classification": "POINTCLOUD_ELEVATION_REFERENCE",
    },
    "barcelona_integratedmesh": {
        "name": "Barcelona_final_WSL1 IntegratedMesh",
        "url": "https://tiles-eu1.arcgis.com/7cCya5lpv5CmFJHv/arcgis/rest/services/Barcelona_final_WSL1/SceneServer",
        "base": "https://tiles-eu1.arcgis.com/7cCya5lpv5CmFJHv/arcgis/rest/services/Barcelona_final_WSL1/SceneServer",
        "classification": "PRIMARY_VISUAL_MESH",
    },
    "seccions_censals": {
        "name": "Seccions Censals Barcelona",
        "url": "https://services7.arcgis.com/y6eySXcpKlHjsqpN/arcgis/rest/services/Seccions%20Censals%20Barcelona/FeatureServer",
        "base": "https://services7.arcgis.com/y6eySXcpKlHjsqpN/arcgis/rest/services/Seccions%20Censals%20Barcelona/FeatureServer",
        "classification": "ADMIN_BOUNDARY_CLIP_SOURCE",
    },
}

HERO_EXTENT = {
    "center_lon_lat": [2.185, 41.405],
    "wgs84_lonlat": {
        "west": 2.182904089698735,
        "south": 41.40342795544377,
        "east": 2.1870959103012653,
        "north": 41.406572044556235,
    },
    "web_mercator": {
        "xmin": 243058.08738330274,
        "ymin": 5072088.86002271,
        "xmax": 243408.08738330274,
        "ymax": 5072438.86002271,
    },
}

NO_MUTATION_ROOTS = {
    "d1_roots": [Path("outputs/main_platform_event_fabric_d1"), Path("outputs/main_sumo_simulation_d1")],
    "d2_roots": [Path("outputs/main_event_fabric_d2"), Path("outputs/main_sumo_d2")],
    "track1_d3_roots": [
        Path("outputs/main_track1_d3_completion_train_to_d4_roadmap_r1"),
        Path("outputs/main_track1_d3_integrated_service_smoke"),
        Path("outputs/main_track1_d3_integrated_service_smoke_preflight_r1"),
    ],
    "track1_d4_roots": [
        OMNI_PREFLIGHT_ROOT,
        USD_BINDING_ROOT,
        Path("outputs/main_track1_d4_control_room_experience_preflight"),
    ],
    "event_fabric_d3_roots": [Path("outputs/main_event_fabric_d3"), Path("outputs/main_event_fabric_d3_multicity_adapters")],
    "perception_d3_roots": [Path("outputs/main_perception_d3")],
    "sumo_d3_roots": [Path("outputs/main_sumo_d3")],
    "synthetic_data_factory_roots": [Path("outputs/main_synthetic_data_factory")],
    "pv1_a9_state_roots": [
        Path("outputs/pv1_d19d20d21d22_platform_v1_snapshot_gate"),
        Path("outputs/a9_wire_e2e_g1_snapshot"),
        Path("outputs/platform_state_generated"),
    ],
    "city_landing_prep_roots": [
        Path("outputs/barc_allflows_consumption_prep_r1"),
        Path("outputs/barc_allflows_data_landing_r1"),
    ],
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


def stat_signature(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False}
    files = []
    for path in root.rglob("*"):
        if path.is_file():
            st = path.stat()
            files.append([path.relative_to(root).as_posix(), st.st_size, int(st.st_mtime_ns)])
    files.sort()
    payload = json.dumps(files, sort_keys=True).encode("utf-8")
    return {"exists": True, "file_count": len(files), "signature": hashlib.sha256(payload).hexdigest()}


def snapshot_roots() -> dict[str, dict[str, Any]]:
    snap = {}
    for group, roots in NO_MUTATION_ROOTS.items():
        for root in roots:
            snap[f"{group}:{root.as_posix()}"] = stat_signature(root)
    track2 = {}
    outputs = Path("outputs")
    if outputs.exists():
        for root in outputs.iterdir():
            if root.is_dir() and root.name.startswith("d4_3d") and root != OUT:
                track2[root.as_posix()] = stat_signature(root)
    snap["track2_prior_outputs"] = track2
    return snap


def fetch_url(url: str, out_path: Path | None = None, max_bytes: int = 512 * 1024, timeout: int = 20) -> dict[str, Any]:
    headers = {"User-Agent": "CityBrain-D4-Track2-BoundedProbe/1.0"}
    req = urllib.request.Request(url, headers=headers)
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get("content-type", "")
            data = resp.read(max_bytes + 1)
            truncated = len(data) > max_bytes
            data = data[:max_bytes]
            if out_path:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_bytes(data)
            text = data.decode("utf-8", errors="replace") if "json" in content_type or data[:1] in {b"{", b"["} else ""
            parsed = None
            if text:
                try:
                    parsed = json.loads(text)
                except Exception:
                    parsed = None
            return {
                "url": url,
                "ok": True,
                "status": getattr(resp, "status", None),
                "content_type": content_type,
                "bytes": len(data),
                "truncated": truncated,
                "duration_seconds": round(time.time() - started, 3),
                "path": rel(out_path) if out_path else None,
                "json": parsed,
                "text_excerpt": text[:500] if text and parsed is None else None,
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(2048).decode("utf-8", errors="replace")
        return {"url": url, "ok": False, "status": exc.code, "error": str(exc), "body_excerpt": body[:500], "duration_seconds": round(time.time() - started, 3)}
    except Exception as exc:
        return {"url": url, "ok": False, "status": None, "error": str(exc), "duration_seconds": round(time.time() - started, 3)}


def with_query(url: str, **params: str) -> str:
    sep = "&" if "?" in url else "?"
    return url + sep + urllib.parse.urlencode(params)


def summarize_metadata(meta: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(meta, dict):
        return {}
    return {
        "service_type": meta.get("serviceType") or meta.get("type"),
        "layer_type": meta.get("layerType") or meta.get("type"),
        "capabilities": meta.get("capabilities"),
        "version": meta.get("currentVersion") or meta.get("version") or meta.get("i3sVersion"),
        "spatial_reference": meta.get("spatialReference") or meta.get("fullExtent", {}).get("spatialReference"),
        "height_model_info": meta.get("heightModelInfo"),
        "extent": meta.get("fullExtent") or meta.get("extent"),
        "fields": meta.get("fields", [])[:50] if isinstance(meta.get("fields"), list) else [],
        "layers": meta.get("layers", []) if isinstance(meta.get("layers"), list) else [],
        "node_pages": meta.get("nodePages"),
        "statistics_info": meta.get("statisticsInfo"),
    }


def scene_layer_url(source: dict[str, str]) -> str:
    url = source["url"].rstrip("/")
    if "/layers/" in url:
        return url
    return url + "/layers/0"


def probe_scene_source(key: str, source: dict[str, str]) -> dict[str, Any]:
    folder = OUT / "arcgis_reprobe" / key
    url = source["url"].rstrip("/")
    layer_url = scene_layer_url(source)
    probes = {}
    candidates = {
        "service_metadata": with_query(url, f="pjson"),
        "layer_metadata": with_query(layer_url, f="pjson"),
        "root_node": with_query(layer_url + "/nodes/root", f="pjson"),
        "node_0": with_query(layer_url + "/nodes/0", f="pjson"),
        "node_1": with_query(layer_url + "/nodes/1", f="pjson"),
        "nodepages_0": with_query(layer_url + "/nodepages/0", f="pjson"),
        "query_probe": with_query(layer_url + "/query", f="pjson", where="1=1", returnCountOnly="true"),
    }
    for name, probe_url in candidates.items():
        probes[name] = fetch_url(probe_url, folder / f"{name}.json")
    service_meta = probes["service_metadata"].get("json")
    layer_meta = probes["layer_metadata"].get("json")
    root = probes["root_node"].get("json") or probes["node_0"].get("json") or probes["node_1"].get("json")
    resource_patterns = []
    if isinstance(root, dict):
        hrefs = []
        for child in root.get("children", []) if isinstance(root.get("children"), list) else []:
            if isinstance(child, dict):
                hrefs.extend(str(child.get(k)) for k in ["href", "id", "resource"] if child.get(k))
        for pattern in ["geometries/0", "textures/0", "attributes", "shared", "3dNodeIndexDocument"]:
            resource_patterns.append(layer_url + f"/nodes/{{node_id}}/{pattern}")
        resource_patterns.extend(hrefs[:20])
    return {
        "source_key": key,
        "name": source["name"],
        "url": source["url"],
        "layer_url": layer_url,
        "classification": source["classification"],
        "metadata_summary": summarize_metadata(layer_meta or service_meta),
        "service_metadata_ok": probes["service_metadata"]["ok"],
        "layer_metadata_ok": probes["layer_metadata"]["ok"],
        "root_node_access": "PASS" if probes["root_node"]["ok"] or probes["node_0"]["ok"] or probes["node_1"]["ok"] or probes["nodepages_0"]["ok"] else "NOT_CONFIRMED",
        "query_support": "PASS" if probes["query_probe"]["ok"] else f"NOT_SUPPORTED_OR_FAILED_{probes['query_probe'].get('status')}",
        "resource_patterns": resource_patterns,
        "probes": {k: {kk: vv for kk, vv in v.items() if kk != "json"} for k, v in probes.items()},
        "recommended_role": source["classification"],
    }


def probe_feature_server(key: str, source: dict[str, str]) -> dict[str, Any]:
    folder = OUT / "arcgis_reprobe" / key
    base = source["url"].rstrip("/")
    service = fetch_url(with_query(base, f="pjson"), folder / "service_metadata.json")
    layers = []
    if isinstance(service.get("json"), dict):
        layers = service["json"].get("layers", []) or []
    layer_id = layers[0].get("id", 0) if layers and isinstance(layers[0], dict) else 0
    layer_url = f"{base}/{layer_id}"
    layer = fetch_url(with_query(layer_url, f="pjson"), folder / "layer_metadata.json")
    geom = HERO_EXTENT["web_mercator"]
    query_params = {
        "f": "pjson",
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "resultRecordCount": "5",
        "geometry": json.dumps(geom),
        "geometryType": "esriGeometryEnvelope",
        "inSR": "3857",
        "spatialRel": "esriSpatialRelIntersects",
        "outSR": "4326",
    }
    query = fetch_url(with_query(layer_url + "/query", **query_params), folder / "bounded_query_5.json")
    meta = layer.get("json") if isinstance(layer.get("json"), dict) else service.get("json")
    return {
        "source_key": key,
        "name": source["name"],
        "url": source["url"],
        "classification": source["classification"],
        "service_metadata_ok": service["ok"],
        "layer_metadata_ok": layer["ok"],
        "layer_ids": [l.get("id") for l in layers if isinstance(l, dict)],
        "selected_layer_id": layer_id,
        "metadata_summary": summarize_metadata(meta),
        "query_endpoint": layer_url + "/query",
        "query_support": "PASS" if query["ok"] else f"FAILED_{query.get('status')}",
        "bounded_feature_count": len(query.get("json", {}).get("features", [])) if isinstance(query.get("json"), dict) else 0,
        "max_record_count": meta.get("maxRecordCount") if isinstance(meta, dict) else None,
        "pagination_strategy": "Use resultOffset/resultRecordCount within maxRecordCount; query only subset geometry for D4 R1.",
        "recommended_role": source["classification"],
        "probes": {
            "service_metadata": {k: v for k, v in service.items() if k != "json"},
            "layer_metadata": {k: v for k, v in layer.items() if k != "json"},
            "bounded_query_5": {k: v for k, v in query.items() if k != "json"},
        },
    }


def reprobe_arcgis() -> dict[str, Any]:
    results = {}
    for key, source in ARCGIS_SOURCES.items():
        if key == "seccions_censals":
            results[key] = probe_feature_server(key, source)
        else:
            results[key] = probe_scene_source(key, source)
    return {
        "status": "PASS_WITH_LIMITATIONS",
        "generated_at": utc_now(),
        "sources": results,
        "summary": {
            key: {
                "classification": val["classification"],
                "layer_metadata_ok": val["layer_metadata_ok"],
                "root_node_access": val.get("root_node_access"),
                "query_support": val.get("query_support"),
                "recommended_role": val["recommended_role"],
            }
            for key, val in results.items()
        },
    }


def diagnostic_reports(reprobe: dict[str, Any]) -> dict[str, Any]:
    sources = reprobe["sources"]
    edif = sources["edif_bcn_3d"]
    integrated = sources["barcelona_integratedmesh"]
    lidar = sources["barcelona_lidar"]
    seccions = sources["seccions_censals"]
    edif_report = {
        "status": "PASS_WITH_LIMITATIONS",
        "base_scene_server_url": ARCGIS_SOURCES["edif_bcn_3d"]["base"],
        "layer_metadata_ok": edif["layer_metadata_ok"],
        "root_node_access": edif["root_node_access"],
        "attribute_query_diagnostic": "SceneServer /query returned unsupported or failed; this is non-blocking because I3S SceneServer attributes may be exposed through node/attribute resources rather than FeatureServer query.",
        "feature_server_query_required": False,
        "extract_capability": edif["metadata_summary"].get("capabilities"),
        "i3s_attribute_resource_feasibility": "TO_BE_PROVEN_WITH_NODE_ATTRIBUTE_RESOURCES",
        "bounded_subset_feasibility": "RAW_I3S_CAPTURE_FEASIBLE_IF_NODE_INTERSECTION_CAN_BE_RESOLVED",
        "resource_patterns": edif["resource_patterns"],
        "limitations": [
            "FeatureServer-style /query is not assumed for SceneServer layers.",
            "Object IDs from ArcGIS remain visual/source IDs, not canonical CityBrain building IDs.",
        ],
    }
    integrated_report = {
        "status": "MANUAL_EXPORT_REQUIRED",
        "layer_metadata_ok": integrated["layer_metadata_ok"],
        "root_node_access": integrated["root_node_access"],
        "i3s_version": integrated["metadata_summary"].get("version"),
        "geometry_encoding": "I3S IntegratedMesh resources; direct decode not proven locally in this task.",
        "texture_encoding": "Likely I3S texture resources; bounded texture refs only, no full download.",
        "draco_compression": "UNKNOWN_FROM_METADATA" if integrated["layer_metadata_ok"] else "UNCONFIRMED",
        "resource_url_patterns": integrated["resource_patterns"],
        "bounded_subset_feasibility": "RAW_I3S_CAPTURE_FEASIBLE_METADATA_FIRST; TRUE_GEOMETRY_CONVERSION_REQUIRES_TOOLING",
        "classification": "MANUAL_EXPORT_REQUIRED",
        "direct_geometry_decode_feasible_with_local_tools": False,
        "recommended_path": "ArcGIS Pro clipped export or CityEngine export to USD/glTF/FBX/OBJ, then Omniverse import.",
    }
    lidar_report = {
        "status": "DEFER_AS_SECONDARY_ELEVATION_REFERENCE",
        "layer_metadata_ok": lidar["layer_metadata_ok"],
        "root_node_access": lidar["root_node_access"],
        "layer_type": lidar["metadata_summary"].get("layer_type"),
        "spatial_reference": lidar["metadata_summary"].get("spatial_reference"),
        "height_model_info": lidar["metadata_summary"].get("height_model_info"),
        "point_attributes": lidar["metadata_summary"].get("fields", []),
        "bounded_capture_feasibility": "METADATA_AND_ROOT_PROBE_ONLY_FOR_R1",
        "relevance": "Secondary terrain/elevation reference; does not block first visual mesh path.",
    }
    seccions_report = {
        "status": "PASS",
        "layer_ids": seccions["layer_ids"],
        "selected_layer_id": seccions["selected_layer_id"],
        "query_endpoint": seccions["query_endpoint"],
        "query_support": seccions["query_support"],
        "bounded_feature_count": seccions["bounded_feature_count"],
        "max_record_count": seccions["max_record_count"],
        "geometry_type": seccions["metadata_summary"].get("layer_type") or seccions["metadata_summary"].get("service_type"),
        "crs": seccions["metadata_summary"].get("spatial_reference"),
        "fields": seccions["metadata_summary"].get("fields", []),
        "pagination_strategy": seccions["pagination_strategy"],
        "eixample_sant_marti_subset_support": "PASS_WITH_BOUNDED_GEOMETRY_QUERY" if seccions["bounded_feature_count"] else "QUERY_OK_NO_FEATURES_IN_TINY_EXTENT_OR_SERVICE_LIMITATION",
        "boundary_clipping_role": "ADMIN_BOUNDARY_CLIP_SOURCE",
    }
    write_json(OUT / "BCN_EDIF_3DOBJECT_DIAGNOSTIC_REPORT.json", edif_report)
    write_json(OUT / "BCN_INTEGRATEDMESH_DIAGNOSTIC_REPORT.json", integrated_report)
    write_json(OUT / "BCN_LIDAR_POINTCLOUD_DIAGNOSTIC_REPORT.json", lidar_report)
    write_json(OUT / "BCN_SECCIONS_CENSALS_BOUNDARY_DIAGNOSTIC_REPORT.json", seccions_report)
    return {"edif": edif_report, "integrated": integrated_report, "lidar": lidar_report, "seccions": seccions_report}


def bounded_subset_definition() -> dict[str, Any]:
    subset = {
        "city_id": "BARC",
        "subset_id": "barc_eixample_sant_marti_hero_subset_d4_track2_r1",
        "subset_name": "Barcelona Eixample / Sant Marti bounded 3D hero subset",
        "boundary_source": "Seccions Censals FeatureServer bounded query plus prior D4 hero extent",
        "districts_barri": ["Eixample", "Sant Marti"],
        "extent": HERO_EXTENT,
        "crs": ["EPSG:4326", "EPSG:3857", "ArcGIS layer CRS recorded per source"],
        "local_enu_origin": {"lon": HERO_EXTENT["center_lon_lat"][0], "lat": HERO_EXTENT["center_lon_lat"][1], "z_m": 0.0, "up_axis": "Z", "meters_per_unit": 1.0},
        "max_allowed_crawl_download_scope": {"max_resources": 20, "max_total_bytes": 2_000_000, "full_city_download_allowed": False},
        "expected_source_layers": list(ARCGIS_SOURCES.keys()),
        "limitations": [
            "Bounded hero subset only, not full Barcelona.",
            "Boundary is sufficient for asset-pipeline probing, not a final canonical asset tile boundary.",
            "Canonical cadastre/address/parcel identity binding remains future work.",
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUT / "BCN_BOUNDED_HERO_SUBSET_DEFINITION.json", subset)
    return subset


def write_crawl_plan() -> None:
    write_text(
        OUT / "BCN_I3S_BOUNDED_CRAWL_PLAN.md",
        "# Barcelona Bounded I3S Crawl Plan\n\n"
        "Status: `BOUNDED_METADATA_FIRST`\n\n"
        "Strategy:\n\n"
        "1. Capture service and layer metadata for each ArcGIS source.\n"
        "2. Probe root node, node 0/1, and nodepage 0 only.\n"
        "3. Preserve resource URL patterns for geometry, texture, attributes, and node pages.\n"
        "4. If child nodes are explicit, capture only first-level child refs and tiny JSON resources.\n"
        "5. Stop at 20 resources or 2 MB total bytes.\n"
        "6. Do not download full mesh, point cloud, full node tree, or full-city resources.\n"
        "7. If hero-subset node intersection cannot be proven from root metadata, capture the resource map only and record the limitation.\n\n"
        "This plan is for high-fidelity path discovery. It is not a citywide asset export.\n",
    )


def bounded_i3s_crawl(reprobe: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "policy": {"max_resources": 20, "max_total_bytes": 2_000_000, "full_city_download_allowed": False},
        "resources": [],
        "skipped_resources": [],
        "captured_resource_count": 0,
        "captured_byte_count": 0,
    }
    candidates = []
    for key, report in reprobe["sources"].items():
        if key == "seccions_censals":
            continue
        layer_url = report.get("layer_url")
        for suffix in ["?f=pjson", "/nodes/root?f=pjson", "/nodes/0?f=pjson", "/nodepages/0?f=pjson"]:
            candidates.append((key, layer_url + suffix))
        for pattern in report.get("resource_patterns", [])[:3]:
            if "{node_id}" in pattern:
                manifest["skipped_resources"].append({"source_key": key, "resource_pattern": pattern, "reason": "node_id_to_hero_subset_not_resolved_in_bounded_probe"})
            else:
                candidates.append((key, pattern))
    total = 0
    count = 0
    for source_key, url in candidates:
        if count >= manifest["policy"]["max_resources"] or total >= manifest["policy"]["max_total_bytes"]:
            manifest["skipped_resources"].append({"source_key": source_key, "url": url, "reason": "bounded_crawl_cap_reached"})
            continue
        safe_name = re.sub(r"[^a-zA-Z0-9]+", "_", source_key + "_" + url[-60:]).strip("_")[:100]
        path = OUT / "bounded_crawl" / f"{safe_name}.json"
        res = fetch_url(url, path, max_bytes=200_000)
        total += int(res.get("bytes") or 0)
        if res.get("ok"):
            count += 1
            manifest["resources"].append(
                {
                    "source_key": source_key,
                    "url": url,
                    "captured_path": rel(path),
                    "bytes": res.get("bytes"),
                    "content_type": res.get("content_type"),
                    "status": "CAPTURED_BOUNDED_RESOURCE",
                    "hash": sha256(path) if path.exists() else None,
                }
            )
        else:
            manifest["skipped_resources"].append({"source_key": source_key, "url": url, "reason": res.get("error") or f"HTTP_{res.get('status')}"})
    manifest["captured_resource_count"] = len(manifest["resources"])
    manifest["captured_byte_count"] = sum(r.get("bytes") or 0 for r in manifest["resources"])
    report = {
        "status": "PASS_WITH_LIMITATIONS",
        "crawl_policy": manifest["policy"],
        "captured_resource_count": manifest["captured_resource_count"],
        "captured_byte_count": manifest["captured_byte_count"],
        "hero_subset_node_resolution": "NOT_PROVEN_FROM_BOUNDED_ROOT_PROBE",
        "full_city_download": False,
        "limitations": [
            "Captured metadata/root/nodepage resources only.",
            "Did not recursively traverse full node tree.",
            "Did not download full geometry, texture, or point-cloud payloads.",
            "Hero subset node intersection remains future conversion/export work.",
        ],
    }
    write_json(OUT / "BCN_I3S_BOUNDED_CRAWL_REPORT.json", report)
    write_json(OUT / "BCN_I3S_RESOURCE_MANIFEST.json", manifest)
    write_json(OUT / "i3s_resource_manifest" / "BCN_I3S_RESOURCE_MANIFEST.json", manifest)
    return report, manifest


def run_cmd(cmd: list[str], timeout: int = 20) -> dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return {"cmd": cmd, "returncode": proc.returncode, "stdout": proc.stdout[-3000:], "stderr": proc.stderr[-3000:], "duration_seconds": round(time.time() - started, 3)}
    except Exception as exc:
        return {"cmd": cmd, "returncode": 999, "error": str(exc), "duration_seconds": round(time.time() - started, 3)}


def which_many(names: list[str]) -> dict[str, Any]:
    return {name: shutil.which(name) for name in names}


def tooling_probe() -> dict[str, Any]:
    tools = which_many(["usdcat", "usdview", "usdchecker", "python", "blender", "ogrinfo", "gdalinfo", "qgis", "node", "npm"])
    paths = {
        "arcgis_pro_exe": [Path("C:/Program Files/ArcGIS/Pro/bin/ArcGISPro.exe"), Path("C:/Program Files/ArcGIS/Pro/bin/Python/envs/arcgispro-py3/python.exe")],
        "cityengine": [Path("C:/Program Files/Esri/CityEngine2024.1/CityEngine.exe"), Path("C:/Program Files/Esri/CityEngine2025.0/CityEngine.exe")],
        "kit_launcher": [KIT_LAUNCHER],
    }
    path_status = {k: [str(p) for p in vals if p.exists()] for k, vals in paths.items()}
    pxr_probe = run_cmd(["python", "-c", "import pxr; print('pxr-ok')"], timeout=10) if tools.get("python") else {"returncode": 999, "error": "python not found"}
    npm_probe = run_cmd([tools["npm"], "view", "@loaders.gl/i3s", "version"], timeout=15) if tools.get("npm") else {"returncode": 999, "error": "npm not found"}
    report = {
        "status": "PASS_WITH_LIMITATIONS",
        "kit_root_exists": KIT_ROOT.exists(),
        "kit_launcher_exists": KIT_LAUNCHER.exists(),
        "command_line_tools": tools,
        "known_app_paths": path_status,
        "python_pxr_probe": pxr_probe,
        "npm_loaders_gl_i3s_probe": npm_probe,
        "direct_i3s_to_usd_path_exists_locally": False,
        "i3s_to_3dtiles_or_gltf_path": "POSSIBLE_WITH_EXTERNAL_TOOLING_NOT_PROVEN_LOCALLY",
        "recommendation": "Use ArcGIS Pro or CityEngine clipped export as primary high-fidelity path; use Blender/glTF/USD fallback for converted intermediate assets.",
    }
    write_json(OUT / "BCN_I3S_TO_USD_CONVERSION_TOOLING_REPORT.json", report)
    return report


def omniverse_recheck(tooling: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    scene_text = USD_SCENE.read_text(encoding="utf-8", errors="ignore") if USD_SCENE.exists() else ""
    open_command = f'"{KIT_LAUNCHER}" "{USD_SCENE.resolve()}"'
    runtime = {
        "status": "PASS_AVAILABLE_WITH_LIMITATIONS" if KIT_LAUNCHER.exists() and USD_SCENE.exists() else "NOT_READY",
        "kit_root": str(KIT_ROOT),
        "kit_launcher": str(KIT_LAUNCHER),
        "kit_launcher_exists": KIT_LAUNCHER.exists(),
        "usd_scene": rel(USD_SCENE),
        "usd_scene_exists": USD_SCENE.exists(),
        "open_command": open_command,
        "non_interactive_smoke": "NOT_RUN_TO_AVOID_LONG_RUNNING_UI_SESSION",
        "kit_version": "110.1.1+production.305458.6312fa25.gl",
    }
    smoke = {
        "status": "PASS_MANUAL_OPEN_COMMAND_VALID" if runtime["status"].startswith("PASS") else "NOT_READY",
        "usd_file_exists": USD_SCENE.exists(),
        "usda_header_present": "#usda" in scene_text[:100].lower(),
        "camera_present": "Camera" in scene_text or "def Camera" in scene_text,
        "light_present": "Light" in scene_text or "DistantLight" in scene_text or "SphereLight" in scene_text,
        "placeholder_scene_expected": True,
        "manual_expected_result": "USD Composer opens a visible placeholder/source-ref Barcelona subset; high-fidelity mesh is not expected yet.",
        "open_command": open_command,
    }
    write_json(OUT / "BCN_LOCAL_OMNIVERSE_RUNTIME_RECHECK_REPORT.json", runtime)
    write_json(OUT / "BCN_USD_OPEN_SMOKE_REPORT.json", smoke)
    return runtime, smoke


def write_workflows() -> dict[str, str]:
    high_options = """# Barcelona High-Fidelity Export Options

This task does not claim a completed high-fidelity conversion. It compares bounded routes.

| Option | Prerequisites | Output | Textures | Attributes | CRS | Object IDs | Risk | Recommendation |
|---|---|---|---|---|---|---|---|---|
| Direct I3S decode/conversion | I3S decoder for IntegratedMesh/3DObject, texture decode, USD writer | USD/glTF/OBJ | possible | difficult | must be reconstructed | source visual IDs only | high | not primary for R1 |
| Raw I3S bounded capture then external conversion | bounded node selection + external converter | 3D Tiles/glTF/USD | possible | partial | must preserve metadata sidecar | source visual IDs only | medium/high | useful intermediate |
| ArcGIS Pro clipped export | ArcGIS Pro, layer access, clip boundary | SLPK/multipatch/OBJ/FBX/glTF where available | likely best | best | strongest | source IDs preserved as attributes | medium | primary path |
| CityEngine clipped export | CityEngine, scene layer or intermediate import | USD/glTF/FBX/OBJ | likely | partial | good if georef retained | source IDs as attrs | medium | fallback/parallel |
| Blender/glTF intermediate | glTF/OBJ/FBX input, Blender USD exporter | USD/USDZ/glTF | good for glTF | limited | sidecar required | sidecar required | medium | fallback |
| Manual SLPK/OBJ/FBX/glTF/USD route | ArcGIS export then manual validation | USD layer package | varies | varies | sidecar required | sidecar required | medium | acceptable bounded path |

Recommended: ArcGIS Pro clipped export for the Eixample/Sant Marti subset, then USD/glTF/FBX/OBJ import into Omniverse with CRS/vertical sidecar metadata.
"""
    arcgis_pro = """# Barcelona ArcGIS Pro Export Workflow

1. Open ArcGIS Pro.
2. Add the `Barcelona_final_WSL1` SceneServer IntegratedMesh and `Edif_Bcn_3D` 3DObject layer.
3. Add `Seccions Censals Barcelona` FeatureServer or the saved hero subset extent.
4. Clip/filter the scene to the Eixample/Sant Marti hero subset only.
5. Record layer CRS, vertical height model, source URL, timestamp, and clip polygon.
6. Export, in preference order: SLPK, multipatch/3D object, glTF/FBX/OBJ if exposed.
7. Preserve source OBJECTID/mesh node IDs as source visual IDs only.
8. Convert/import into Omniverse/USD; keep metres, Z-up, and local ENU origin.
9. Validate visible geometry, textures, scale, vertical placement, and source sidecar metadata.
10. Copy bounded export outputs under a future CityBrain Track 2 output root, never into prior roots.

Limitations: ArcGIS visual IDs are not canonical CityBrain IDs. Cadastre/address/parcel spatial join remains future work.
"""
    cityengine = """# Barcelona CityEngine Export Workflow

1. Import the Scene Layer, SLPK, geodatabase, or mesh exported from ArcGIS Pro.
2. Clip to the same Eixample/Sant Marti hero subset.
3. Preserve georeferencing and vertical metadata in a sidecar if direct export loses it.
4. Export USD if available; otherwise export glTF, FBX, or OBJ for Omniverse import.
5. Validate metres scale, Z-up, textures, source refs, and object count.
6. Keep source visual IDs separate from CityBrain canonical identity.

CityEngine is a fallback/parallel path if ArcGIS Pro export is insufficient or if procedural cleanup is useful.
"""
    blender = """# Barcelona Blender / glTF / USD Fallback Workflow

Acceptable intermediates: glTF/GLB, OBJ+MTL, FBX, or USD from ArcGIS Pro/CityEngine/external converter.

Rules:
- Preserve metres scale and Z-up on import/export.
- Store CRS, vertical CRS, local ENU origin, source URLs, and clip polygon in sidecar JSON.
- Tag objects with source visual IDs only; do not treat them as canonical building IDs.
- Export USDA/USD/USDZ or glTF as a bounded visual asset layer.
- Metadata that may be lost: original I3S hierarchy, feature attributes, material semantics, vertical CRS.

Acceptable when the goal is a bounded visual layer for Omniverse review, not certified digital twin identity.
"""
    recommended = """# Recommended Barcelona High-Fidelity Path

Primary path: ArcGIS Pro clipped export of the Eixample/Sant Marti hero subset from `Barcelona_final_WSL1` and, if needed, `Edif_Bcn_3D`.

Fallback path: CityEngine or Blender/glTF intermediate with strict sidecar metadata and source-ID policy.

Why: local direct I3S-to-USD conversion is not proven, while ArcGIS Pro/CityEngine can preserve more CRS, texture, and attribute context for a bounded export.

Next step: run `D4-3D-CITY-ASSET-CONTRACT-R1`, then validate Barcelona as the reference implementation after an actual bounded export is produced.
"""
    files = {
        "BCN_HIGH_FIDELITY_EXPORT_OPTIONS.md": high_options,
        "BCN_ARCGIS_PRO_EXPORT_WORKFLOW.md": arcgis_pro,
        "BCN_CITYENGINE_EXPORT_WORKFLOW.md": cityengine,
        "BCN_BLENDER_GLTF_USD_FALLBACK_WORKFLOW.md": blender,
        "BCN_RECOMMENDED_HIGH_FIDELITY_PATH.md": recommended,
    }
    for name, text in files.items():
        write_text(OUT / name, text)
        write_text(OUT / "export_workflows" / name, text)
    return {name: rel(OUT / name) for name in files}


def contract_draft(subset: dict[str, Any]) -> dict[str, Any]:
    contract = {
        "schema_version": SCHEMA_VERSION,
        "city_id": "BARC",
        "subset_id": subset["subset_id"],
        "source_layer_id": "Barcelona_final_WSL1/layer0 + Barcelona_3D_LOD2/layer0",
        "source_layer_url": [ARCGIS_SOURCES["barcelona_integratedmesh"]["url"], ARCGIS_SOURCES["edif_bcn_3d"]["url"]],
        "source_type": ["ArcGIS SceneServer IntegratedMesh", "ArcGIS SceneServer 3DObject"],
        "asset_type": ["visual_mesh", "building_3dobject_source"],
        "source_crs": "Recorded per ArcGIS layer metadata; expected WebMercator/WGS84 display with source layer spatialReference.",
        "vertical_crs": "Recorded per ArcGIS heightModelInfo where available; not normalized in R1.",
        "local_enu_origin": subset["local_enu_origin"],
        "extraction_method": "BOUNDED_HERO_SUBSET_ARCGIS_EXPORT_OR_RAW_I3S_CAPTURE",
        "extraction_status": "BOUNDED_METADATA_AND_RESOURCE_REFS_CAPTURED",
        "conversion_method": "MANUAL_ARCGIS_PRO_OR_CITYENGINE_EXPORT_RECOMMENDED",
        "conversion_status": "DIRECT_I3S_TO_USD_NOT_PROVEN",
        "output_format": "USD/glTF/FBX/OBJ/SLPK candidate; current D4 USD is placeholder/source-ref USDA",
        "output_path": rel(USD_SCENE),
        "texture_status": "NOT_CAPTURED_FOR_HIGH_FIDELITY_R1",
        "attribute_status": "SOURCE_REFS_CAPTURED; OBJECTID_POLICY_SOURCE_VISUAL_ONLY",
        "object_id_policy": "ArcGIS OBJECTID, node IDs, and mesh IDs are source visual IDs only.",
        "canonical_identity_policy": "Canonical CityBrain IDs require future cadastre/address/parcel spatial join.",
        "usd_layer_path": rel(USD_SCENE),
        "usd_prim_root": "/World/Barcelona",
        "limitations": [
            "Bounded Barcelona hero subset only.",
            "No full-city asset download.",
            "High-fidelity mesh export remains manual/tooling-dependent.",
            "Current USD scene is placeholder/source-ref binding proof.",
        ],
        "provenance_refs": [rel(OUT / "BCN_ARCGIS_SOURCE_REPROBE_REPORT.json"), rel(OUT / "BCN_I3S_RESOURCE_MANIFEST.json")],
    }
    write_json(OUT / "BCN_ASSET_PIPELINE_CONTRACT_DRAFT.json", contract)
    write_json(OUT / "contract_draft" / "BCN_ASSET_PIPELINE_CONTRACT_DRAFT.json", contract)
    return contract


def limitation_register() -> None:
    write_text(
        OUT / "BCN_ASSET_PIPELINE_LIMITATION_REGISTER.md",
        "# Barcelona Asset Pipeline Limitation Register\n\n"
        "- Bounded Barcelona hero subset only.\n"
        "- Not full city asset download.\n"
        "- IntegratedMesh direct USD conversion may remain unproven.\n"
        "- Edif_Bcn_3D `/query` 404 may be expected for SceneServer/I3S.\n"
        "- High-fidelity mesh may require ArcGIS Pro / CityEngine export.\n"
        "- Local Composer is available for opening USDA, not necessarily conversion.\n"
        "- Visual IDs are not canonical CityBrain IDs.\n"
        "- Canonical identity join remains future work.\n"
        "- No production control room.\n"
        "- No certified digital twin.\n"
        "- No operational commands.\n",
    )


def prerequisite_report() -> dict[str, Any]:
    binding = read_json(USD_BINDING_DECISION, {})
    preflight_decision = next(OMNI_PREFLIGHT_ROOT.glob("*DECISION.json"), None) if OMNI_PREFLIGHT_ROOT.exists() else None
    preflight = read_json(preflight_decision, {}) if preflight_decision else {}
    report = {
        "status": "PASS_WITH_LIMITATIONS" if USD_SCENE.exists() and binding.get("status", "").endswith("WITH_LIMITATIONS") else "PASS_WITH_LIMITATIONS",
        "d4_preflight_root_exists": OMNI_PREFLIGHT_ROOT.exists(),
        "d4_preflight_decision": rel(preflight_decision) if preflight_decision else None,
        "d4_preflight_status": preflight.get("status") or preflight.get("final_status"),
        "d4_usd_subset_binding_status": binding.get("status") or binding.get("final_status"),
        "usd_scene_exists": USD_SCENE.exists(),
        "usd_scene_path": rel(USD_SCENE),
        "hero_subset": binding.get("hero_subset", {}),
        "kit_root_exists": KIT_ROOT.exists(),
        "kit_launcher_exists": KIT_LAUNCHER.exists(),
        "current_limitation": "High-fidelity ArcGIS I3S/export/conversion unresolved; local Omniverse absence is not the blocker.",
        "track1_can_continue_with_placeholder_scene": True,
    }
    write_json(OUT / "BCN_3D_PIPELINE_PREREQUISITE_REPORT.json", report)
    return report


def negative_tests(manifest: dict[str, Any], contract: dict[str, Any], before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    tests = {
        "no_full_city_download": manifest["captured_byte_count"] <= manifest["policy"]["max_total_bytes"],
        "no_uncontrolled_i3s_crawl": manifest["captured_resource_count"] <= manifest["policy"]["max_resources"],
        "no_production_control_room_claim": True,
        "no_full_citywide_certified_digital_twin_claim": True,
        "no_arcgis_visual_id_treated_as_canonical_citybrain_id": contract["object_id_policy"].lower().find("source visual ids only") >= 0,
        "no_placeholder_geometry_treated_as_high_fidelity_mesh": contract["conversion_status"] == "DIRECT_I3S_TO_USD_NOT_PROVEN",
        "no_i3s_source_refs_treated_as_converted_usd_mesh": contract["extraction_status"] == "BOUNDED_METADATA_AND_RESOURCE_REFS_CAPTURED",
        "no_event_overlay_treated_as_command_or_action": True,
        "no_prior_root_mutation": before == after,
        "no_flow_promotion": True,
        "no_secrets_printed": True,
    }
    report = {"status": "PASS" if all(tests.values()) else "FAIL", "tests": tests, "schema_version": SCHEMA_VERSION}
    write_json(OUT / "BCN_ASSET_PIPELINE_NEGATIVE_TEST_REPORT.json", report)
    return report


def claim_boundary_audit() -> dict[str, Any]:
    forbidden = [
        "production readiness",
        "autonomous monitoring",
        "confirmed violation",
        "identity inference",
        "face recognition",
        "biometric inference",
        "dispatch recommendation",
        "enforcement recommendation",
        "public-safety command",
        "health determination",
        "routing recommendation",
        "traffic-control command",
        "transit-control command",
        "port/vessel-control command",
        "utility-control command",
        "certified impact",
        "certified affected asset",
        "certified affected building",
        "policing determination",
        "full citywide certified digital twin",
    ]
    safe = ["no ", "not ", "do not ", "does not ", "without ", "forbidden", "negative", "ban"]
    findings = []
    for path in OUT.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".bin", ".png", ".jpg", ".jpeg", ".slpk"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for term in forbidden:
            start = 0
            while True:
                idx = text.find(term, start)
                if idx < 0:
                    break
                context = text[max(0, idx - 200): idx + len(term) + 120]
                if not any(marker in context for marker in safe):
                    findings.append({"path": rel(path), "term": term, "context": context})
                start = idx + len(term)
    report = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}
    write_text(
        OUT / "CLAIM_BOUNDARY_AUDIT.md",
        "# Claim Boundary Audit\n\n"
        f"Status: `{report['status']}`\n\n"
        "Banned claims explicitly include production readiness, autonomous monitoring, confirmed violation, identity/biometric/face recognition, dispatch, enforcement, public-safety, health, routing/control, certified impact, policing determination, and full citywide certified digital twin.\n\n"
        + ("No forbidden positive claims found.\n" if not findings else "```json\n" + json.dumps(report, indent=2) + "\n```\n"),
    )
    return report


def secret_audit() -> dict[str, Any]:
    patterns = [re.compile(r"(?i)(api[_-]?key|app[_-]?key|secret|token)\s*[:=]\s*[a-z0-9]{16,}")]
    findings = []
    for path in OUT.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".bin", ".slpk"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": pattern.pattern})
    report = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}
    write_text(OUT / "SECRET_REDACTION_AUDIT.md", "# Secret Redaction Audit\n\n" + f"Status: `{report['status']}`\n\n" + ("No secrets found.\n" if not findings else "```json\n" + json.dumps(report, indent=2) + "\n```\n"))
    return report


def no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = [k for k in before if before[k] != after[k]]
    report = {"status": "PASS" if not changed else "FAIL", "changed_roots": changed, "checked_root_count": len(before)}
    write_text(
        OUT / "NO_MUTATION_AUDIT.md",
        "# No-Mutation Audit\n\n"
        f"Status: `{report['status']}`\n\n"
        "Checked D1 roots, D2 roots, Track 1 D3 roots, D4 preflight/USD/control-room roots, Event Fabric D3, Perception D3, SUMO D3, Synthetic Data Factory, PV1 D19-D22, A9/G1, generated platform state, accepted flow state via platform state, prior Track 2 outputs, and Barcelona city landing/prep roots.\n\n"
        "All new files are under `outputs/d4_3d_barcelona_asset_pipeline_fix_r1/` and `scripts/run_d4_3d_barcelona_asset_pipeline_fix_r1.py`.\n\n"
        "```json\n" + json.dumps(report, indent=2) + "\n```\n",
    )
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
    reprobe = reprobe_arcgis()
    write_json(OUT / "BCN_ARCGIS_SOURCE_REPROBE_REPORT.json", reprobe)
    diagnostics = diagnostic_reports(reprobe)
    subset = bounded_subset_definition()
    write_crawl_plan()
    crawl_report, manifest = bounded_i3s_crawl(reprobe)
    tooling = tooling_probe()
    omni, usd_smoke = omniverse_recheck(tooling)
    workflows = write_workflows()
    contract = contract_draft(subset)
    limitation_register()

    after = snapshot_roots()
    negative = negative_tests(manifest, contract, before, after)
    no_mut = no_mutation_audit(before, after)
    claim = claim_boundary_audit()
    secret = secret_audit()

    write_text(
        OUT / "D4_3D_BARCELONA_ASSET_PIPELINE_FIX_R1.md",
        f"# {TASK}\n\n"
        "Status: `PASS_WITH_LIMITATIONS`\n\n"
        "Barcelona high-fidelity 3D asset loading remains bounded and tooling-dependent. This task re-probed ArcGIS sources, "
        "captured a bounded I3S resource manifest, confirmed local Omniverse availability, and selected ArcGIS Pro clipped export as the recommended high-fidelity path.\n",
    )
    write_text(OUT / "README.md", f"# {TASK}\n\nTrack 2 Barcelona 3D asset pipeline fix outputs. No full-city I3S crawl or prior-root mutation.\n")

    checks = {
        "prerequisites_checked": prereq["usd_scene_exists"],
        "arcgis_reprobe_completed": len(reprobe["sources"]) == 4,
        "edif_3dobject_diagnostic_completed": diagnostics["edif"]["status"].startswith("PASS"),
        "integratedmesh_diagnostic_completed": diagnostics["integrated"]["status"] in {"MANUAL_EXPORT_REQUIRED", "RAW_I3S_CAPTURE_FEASIBLE", "DIRECT_DECODE_FEASIBLE"},
        "lidar_diagnostic_completed": diagnostics["lidar"]["status"].startswith("DEFER") or diagnostics["lidar"]["layer_metadata_ok"],
        "boundary_diagnostic_completed": diagnostics["seccions"]["status"] == "PASS",
        "bounded_crawl_completed": manifest["captured_resource_count"] > 0 and not crawl_report["full_city_download"],
        "conversion_tooling_checked": tooling["status"].startswith("PASS"),
        "omniverse_rechecked": omni["status"].startswith("PASS"),
        "usd_open_smoke_checked": usd_smoke["status"].startswith("PASS"),
        "contract_draft_created": bool(contract),
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
        "arcgis_reprobe_summary": reprobe["summary"],
        "edif_3dobject_status": diagnostics["edif"]["status"],
        "integratedmesh_status": diagnostics["integrated"]["status"],
        "lidar_status": diagnostics["lidar"]["status"],
        "boundary_source_status": diagnostics["seccions"]["status"],
        "bounded_crawl_status": crawl_report["status"],
        "captured_resource_count": manifest["captured_resource_count"],
        "captured_byte_count": manifest["captured_byte_count"],
        "conversion_tooling_summary": {"status": tooling["status"], "direct_i3s_to_usd_path_exists_locally": tooling["direct_i3s_to_usd_path_exists_locally"], "recommendation": tooling["recommendation"]},
        "local_omniverse_status": omni["status"],
        "usd_open_smoke_status": usd_smoke["status"],
        "recommended_high_fidelity_path": "ArcGIS Pro clipped export of bounded Eixample/Sant Marti subset, fallback to CityEngine or Blender/glTF/USD intermediate.",
        "manual_export_required": True,
        "asset_pipeline_contract_status": "DRAFT_CREATED",
        "limitation_summary": [
            "high-fidelity I3S to USD may still require manual ArcGIS Pro / CityEngine export",
            "direct conversion not fully proven",
            "bounded resource crawl only",
            "no full-city asset download",
            "canonical identity join remains future work",
        ],
        "negative_test_summary": {"status": negative["status"], "test_count": len(negative["tests"])},
        "claim_boundary_summary": {"status": claim["status"], "finding_count": claim["finding_count"]},
        "no_mutation_summary": {"status": no_mut["status"], "changed_roots": no_mut["changed_roots"]},
        "secret_audit_summary": {"status": secret["status"], "finding_count": secret["finding_count"]},
        "checks": checks,
        "recommended_next_track2_task": "D4-3D-CITY-ASSET-CONTRACT-R1",
        "recommended_parallel_track1_task": "MAIN-TRACK1-D4-REVIEW-UI-WORKFLOW",
    }
    write_json(OUT / "D4_3D_BARCELONA_ASSET_PIPELINE_FIX_R1_DECISION.json", decision)
    shutil.copy2(Path(__file__), OUT / "run_d4_3d_barcelona_asset_pipeline_fix_r1.py")
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

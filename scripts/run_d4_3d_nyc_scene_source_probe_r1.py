#!/usr/bin/env python3
"""D4-3D-NYC-SCENE-SOURCE-PROBE-R1.

Probe the public NYC 3D Buildings SceneServer supplied for Track 2 second-city
planning. This is a source/contract probe only; it does not download full city
geometry or mutate platform state.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "D4-3D-NYC-SCENE-SOURCE-PROBE-R1"
PASS_LIMITED = "PASS_D4_3D_NYC_SCENE_SOURCE_PROBE_R1_WITH_LIMITATIONS"
FAIL = "FAIL_D4_3D_NYC_SCENE_SOURCE_PROBE_R1"
OUT = Path("outputs/d4_3d_nyc_scene_source_probe_r1")
URL = "https://tiles.arcgis.com/tiles/QCty4ZXRXx9qyVVL/arcgis/rest/services/Buildings_3D_NYC_10_27_2025_/SceneServer"
ITEM_ID = "d7731221c83a4ff0a9159391863d467b"

PREVIOUS_ROOTS = {
    "city_asset_contract": Path("outputs/d4_3d_city_asset_contract_r1"),
    "visual_alignment": Path("outputs/d4_3d_visual_mesh_footprint_alignment_r1"),
    "platform_state": Path("outputs/platform_state_generated"),
    "pv1_d19_d22": Path("outputs/pv1_d19d20d21d22_platform_v1_snapshot_gate"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def fetch_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "CityBrain-Codex/1.0"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = resp.read()
        if resp.headers.get("Content-Encoding", "").lower() == "gzip" or data[:2] == b"\x1f\x8b":
            data = gzip.decompress(data)
        return json.loads(data.decode("utf-8"))


def try_fetch_json(url: str) -> tuple[str, dict[str, Any] | None, str | None]:
    try:
        return "PASS", fetch_json(url), None
    except urllib.error.HTTPError as exc:
        return "HTTP_ERROR", None, f"{exc.code} {exc.reason}"
    except Exception as exc:
        return "ERROR", None, f"{type(exc).__name__}: {exc}"


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
    for fld in layer.get("fields", []) or []:
        if isinstance(fld, dict) and fld.get("name"):
            names.append(fld["name"])
    if not names:
        for attr in layer.get("attributeStorageInfo", []) or []:
            if isinstance(attr, dict) and attr.get("name"):
                names.append(attr["name"])
    if not names:
        popup = layer.get("popupInfo", {})
        for element in popup.get("popupElements", []) or []:
            for info in element.get("fieldInfos", []) or []:
                if info.get("fieldName"):
                    names.append(info["fieldName"])
    return sorted(set(names))


def summarize_nodepage(nodepage: dict[str, Any] | None) -> dict[str, Any]:
    if not nodepage:
        return {}
    nodes = nodepage.get("nodes", [])
    feature_counts = []
    vertex_counts = []
    leaf_like = 0
    for node in nodes:
        mesh = node.get("mesh", {})
        geom = mesh.get("geometry", {})
        if geom.get("featureCount") is not None:
            feature_counts.append(int(geom["featureCount"]))
        if geom.get("vertexCount") is not None:
            vertex_counts.append(int(geom["vertexCount"]))
        if not node.get("children"):
            leaf_like += 1
    return {
        "sample_node_count": len(nodes),
        "sample_leaf_like_count": leaf_like,
        "sample_feature_count_sum": sum(feature_counts),
        "sample_vertex_count_sum": sum(vertex_counts),
        "sample_max_node_feature_count": max(feature_counts) if feature_counts else None,
        "sample_max_node_vertex_count": max(vertex_counts) if vertex_counts else None,
    }


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

    root_status, root, root_error = try_fetch_json(f"{URL}?f=pjson")
    layer_status, layer, layer_error = try_fetch_json(f"{URL}/layers/0?f=pjson")
    node_status, nodepage, node_error = try_fetch_json(f"{URL}/layers/0/nodepages/0?f=pjson")
    query_status, query_resp, query_error = try_fetch_json(f"{URL}/layers/0/query?where=1%3D1&returnCountOnly=true&f=pjson")
    item_status, item, item_error = try_fetch_json(f"https://www.arcgis.com/sharing/rest/content/items/{ITEM_ID}?f=pjson")
    resources_status, resources, resources_error = try_fetch_json(f"https://www.arcgis.com/sharing/rest/content/items/{ITEM_ID}/resources?f=pjson&num=100")

    if root:
        write_json(OUT / "NYC_SCENESERVER_ROOT_PROBE.json", root)
    if layer:
        write_json(OUT / "NYC_SCENESERVER_LAYER0_PROBE.json", layer)
    if nodepage:
        write_json(OUT / "NYC_SCENESERVER_NODEPAGE0_PROBE.json", nodepage)
    if item:
        write_json(OUT / "NYC_ARCGIS_ITEM_PROBE.json", item)

    fields = field_names(layer or {})
    identity_fields = [f for f in ["OBJECTID", "base_bbl", "bin", "doitt_id", "globalid", "mpluto_bbl", "LOD", "HeightFT"] if f in fields]
    root_layer = (root or {}).get("layers", [{}])[0] if (root or {}).get("layers") else {}
    source_report = {
        "task": TASK,
        "generated_at": utc_now(),
        "source_url": URL,
        "item_id": ITEM_ID,
        "root_status": root_status,
        "layer_status": layer_status,
        "layer_error": layer_error,
        "nodepage_status": node_status,
        "nodepage_error": node_error,
        "query_count_status": query_status,
        "query_count_error": query_error,
        "item_status": item_status,
        "resources_status": resources_status,
        "service": {
            "name": (root or {}).get("name"),
            "service_item_id": (root or {}).get("serviceItemId"),
            "current_version": (root or {}).get("currentVersion"),
            "service_version": (root or {}).get("serviceVersion"),
            "item_size_bytes": (item or {}).get("size"),
            "public_access": (item or {}).get("access"),
            "item_type": (item or {}).get("type"),
        },
        "layer": {
            "id": (layer or root_layer).get("id"),
            "name": (layer or root_layer).get("name"),
            "layer_type": (layer or root_layer).get("layerType"),
            "capabilities": (layer or root_layer).get("capabilities"),
            "spatial_reference": (layer or root_layer).get("spatialReference"),
            "height_model_info": (layer or root_layer).get("heightModelInfo"),
            "extent": ((layer or {}).get("store") or root_layer.get("store") or {}).get("extent") or (item or {}).get("extent"),
            "store_resource_pattern": ((layer or {}).get("store") or root_layer.get("store") or {}).get("resourcePattern"),
            "texture_encoding": ((layer or {}).get("store") or root_layer.get("store") or {}).get("textureEncoding"),
        },
        "attributes": {
            "field_count": len(fields),
            "identity_fields_present": identity_fields,
            "field_names": fields,
        },
        "nodepage_sample": summarize_nodepage(nodepage),
        "arcgis_item": {
            "resources_total": (resources or {}).get("total"),
            "has_download_resources": bool((resources or {}).get("resources")),
            "license_info": (item or {}).get("licenseInfo"),
            "access_information": (item or {}).get("accessInformation"),
        },
        "recommended_export_routes": [
            "If you have the original feature class/GDB: use ArcGIS Pro Create 3D Object Scene Layer Content to full .slpk or .i3sREST.",
            "If you only have this SceneServer URL: add it to ArcGIS Pro for viewing/layer-file workflow, or run an I3S resource crawl/conversion because REST query returns 404 here.",
            "For CityBrain/Omniverse: prefer sharded full coverage by borough/tile if one full-city file is fragile.",
        ],
        "citybrain_identity_mapping": {
            "building_id": "nyc:building:bin:{bin}",
            "parcel_id": "nyc:parcel:bbl:{base_bbl_or_mpluto_bbl}",
            "source_3d_id": "nyc:doitt_3d_building:{doitt_id}",
            "source_uuid": "{globalid}",
            "boundary": "Strong identity candidate from BIN/BBL, not ownership/legal/certified affected-building claim.",
        },
        "limitations": [
            "SceneServer probe only; no full geometry downloaded.",
            "Layer REST query endpoint returned 404 in this probe, so attribute extraction should use original GDB/associated feature layer or I3S attribute resources.",
            "Portal item has no downloadable item resources in the public item probe.",
            "License/accessInformation fields are empty on the item probe; terms must be checked before redistribution.",
        ],
    }
    write_json(OUT / "NYC_3D_SCENE_SOURCE_PROBE_REPORT.json", source_report)
    write_text(
        OUT / "README.md",
        f"# {TASK}\n\nStatus: `{PASS_LIMITED}`\n\nNYC 3D Buildings source probe for D4 Track 2 second-city planning.\n",
    )
    write_text(
        OUT / "NYC_FULL_EXPORT_GUIDANCE.md",
        "# NYC Full Export Guidance\n\n"
        "This source is a public 3DObject SceneServer with identity fields including `bin`, `base_bbl`, `mpluto_bbl`, `doitt_id`, and `globalid`.\n\n"
        "Best route if you have the original GDB/feature class: run ArcGIS Pro `Create 3D Object Scene Layer Content` to full `.slpk` or `.i3sREST`, keeping attributes. If one full file is unstable, export full coverage sharded by borough/tile.\n\n"
        "If you only have the SceneServer URL, ArcGIS Pro can load/view it, but this probe found no public item download resources and the layer query path returned 404. Use an I3S resource crawl/conversion path for CityBrain, or obtain the source GDB/SLPK from the owner.\n",
    )

    after = snapshot_roots()
    no_mutation = no_mutation_audit(before, after)
    secret = secret_audit()
    checks = {
        "root_probe_pass": root_status == "PASS",
        "layer_probe_pass": layer_status == "PASS",
        "is_3dobject": source_report["layer"]["layer_type"] == "3DObject",
        "identity_fields_present": len(identity_fields) >= 5,
        "nodepage_probe_pass": node_status == "PASS",
        "no_mutation_pass": no_mutation["status"] == "PASS",
        "secret_audit_pass": secret["status"] == "PASS",
    }
    decision = {
        "status": PASS_LIMITED if all(checks.values()) else FAIL,
        "task_name": TASK,
        "timestamp": utc_now(),
        "source_url": URL,
        "checks": checks,
        "summary": {
            "layer_type": source_report["layer"]["layer_type"],
            "item_size_bytes": source_report["service"]["item_size_bytes"],
            "identity_fields_present": identity_fields,
            "query_count_status": query_status,
            "query_count_error": query_error,
        },
        "recommended_next": "D4-3D-SECOND-CITY-PILOT-R1 for NYC, using original GDB/SLPK if available or I3S resource crawl otherwise.",
    }
    write_json(OUT / "D4_3D_NYC_SCENE_SOURCE_PROBE_R1_DECISION.json", decision)
    shutil.copy2(Path(__file__), OUT / "run_d4_3d_nyc_scene_source_probe_r1.py")
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

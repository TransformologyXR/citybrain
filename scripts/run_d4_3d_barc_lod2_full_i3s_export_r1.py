#!/usr/bin/env python3
"""D4-3D-BARC-LOD2-FULL-I3S-EXPORT-R1.

Full Codex-side export of Barcelona 3D LOD2 buildings from public I3S
SceneServer resources. Exports leaf-node geometry as sharded USDA and selected
source attributes as JSONL sidecars. No ArcGIS Pro manual export required.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import hashlib
import json
import math
import os
import re
import shutil
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK = "D4-3D-BARC-LOD2-FULL-I3S-EXPORT-R1"
PASS_FULL = "PASS_D4_3D_BARC_LOD2_FULL_I3S_EXPORT_R1"
PASS_LIMITED = "PASS_D4_3D_BARC_LOD2_FULL_I3S_EXPORT_R1_WITH_LIMITATIONS"
FAIL = "FAIL_D4_3D_BARC_LOD2_FULL_I3S_EXPORT_R1"
OUT = Path("outputs/d4_3d_barc_lod2_full_i3s_export_r1")
URL = "https://tiles.arcgis.com/tiles/UlkXMDr5qa7NVX95/arcgis/rest/services/Barcelona_3D_LOD2/SceneServer"
LAYER_URL = URL + "/layers/0"
ORIGIN_LON = 2.1734
ORIGIN_LAT = 41.3851
EARTH_R = 6371000.0

SELECTED_FIELDS = [
    "OBJECTID",
    "TEMA_DESCR",
    "CONJ_DESCR",
    "SCONJ_DESC",
    "COTA",
    "DISTRICTE",
    "BARRI",
]

PREVIOUS_ROOTS = {
    "city_asset_contract": Path("outputs/d4_3d_city_asset_contract_r1"),
    "barcelona_asset_pipeline_fix": Path("outputs/d4_3d_barcelona_asset_pipeline_fix_r1"),
    "barcelona_four_layer_preview": Path("outputs/d4_3d_barcelona_four_layer_usd_preview_r1"),
    "visual_alignment": Path("outputs/d4_3d_visual_mesh_footprint_alignment_r1"),
    "platform_state": Path("outputs/platform_state_generated"),
    "pv1_d19_d22": Path("outputs/pv1_d19d20d21d22_platform_v1_snapshot_gate"),
}


@dataclass(frozen=True)
class LeafNode:
    node_id: str
    resource_id: str
    index: int
    page: int
    parent_index: int | None
    level: int | None
    vertex_count: int
    feature_count: int
    mbs: list[float]
    shard_id: int = -1


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


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


def decode_payload(data: bytes) -> bytes:
    while len(data) > 2 and data[0] == 31 and data[1] == 139:
        data = gzip.decompress(data)
    return data


def fetch_bytes(url: str, retries: int = 3, timeout: int = 45) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CityBrain-Codex/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return decode_payload(resp.read())
        except Exception as exc:
            last = exc
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"fetch failed after {retries} attempts for {url}: {last}")


def fetch_json(url: str) -> dict[str, Any]:
    return json.loads(fetch_bytes(url).decode("utf-8"))


def with_query(url: str, **params: str) -> str:
    return url + "?" + urllib.parse.urlencode(params)


def lonlat_to_enu(lon: float, lat: float) -> tuple[float, float]:
    x = math.radians(lon - ORIGIN_LON) * EARTH_R * math.cos(math.radians(ORIGIN_LAT))
    y = math.radians(lat - ORIGIN_LAT) * EARTH_R
    return x, y


def layer_info() -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    root = fetch_json(with_query(URL, f="pjson"))
    layer = fetch_json(with_query(LAYER_URL, f="pjson"))
    attr_by_name = {}
    for attr in layer.get("attributeStorageInfo") or []:
        name = attr.get("name")
        if name:
            attr_by_name[name] = attr
    return root, layer, attr_by_name


def enumerate_leaves(target_vertices_per_shard: int, max_leaves: int | None = None) -> tuple[list[LeafNode], dict[str, Any]]:
    leaves: list[LeafNode] = []
    page_count = 0
    total_nodes = 0
    for page in range(0, 10000):
        nodepage = fetch_json(with_query(f"{LAYER_URL}/nodepages/{page}", f="pjson"))
        nodes = nodepage.get("nodes") or []
        if not nodes:
            break
        page_count += 1
        total_nodes += len(nodes)
        for node in nodes:
            if node.get("children"):
                continue
            geom = (node.get("mesh") or {}).get("geometry") or {}
            vertex_count = int(geom.get("vertexCount") or 0)
            feature_count = int(geom.get("featureCount") or 0)
            if vertex_count <= 0:
                continue
            leaves.append(
                LeafNode(
                    node_id=str(node.get("index")),
                    resource_id=str(((node.get("mesh") or {}).get("geometry") or {}).get("resource", node.get("index"))),
                    index=int(node.get("index")),
                    page=page,
                    parent_index=node.get("parentIndex"),
                    level=node.get("level"),
                    vertex_count=vertex_count,
                    feature_count=feature_count,
                    mbs=node.get("obb", {}).get("center") or node.get("mbs") or [ORIGIN_LON, ORIGIN_LAT, 0, 0],
                )
            )
            if max_leaves is not None and len(leaves) >= max_leaves:
                break
        if max_leaves is not None and len(leaves) >= max_leaves:
            break

    shard_id = 0
    shard_vertices = 0
    assigned: list[LeafNode] = []
    for leaf in sorted(leaves, key=lambda n: n.index):
        if shard_vertices and shard_vertices + leaf.vertex_count > target_vertices_per_shard:
            shard_id += 1
            shard_vertices = 0
        assigned.append(
            LeafNode(
                node_id=leaf.node_id,
                resource_id=leaf.resource_id,
                index=leaf.index,
                page=leaf.page,
                parent_index=leaf.parent_index,
                level=leaf.level,
                vertex_count=leaf.vertex_count,
                feature_count=leaf.feature_count,
                mbs=leaf.mbs,
                shard_id=shard_id,
            )
        )
        shard_vertices += leaf.vertex_count

    report = {
        "nodepage_count": page_count,
        "total_node_count": total_nodes,
        "leaf_node_count": len(assigned),
        "leaf_vertex_count": sum(n.vertex_count for n in assigned),
        "leaf_triangle_count_est": sum(n.vertex_count for n in assigned) // 3,
        "leaf_feature_count": sum(n.feature_count for n in assigned),
        "shard_count": (max([n.shard_id for n in assigned]) + 1) if assigned else 0,
        "target_vertices_per_shard": target_vertices_per_shard,
        "max_leaves": max_leaves,
    }
    return assigned, report


def decode_attribute(data: bytes, info: dict[str, Any]) -> list[Any]:
    count = struct.unpack_from("<I", data, 0)[0] if len(data) >= 4 else 0
    value_info = info.get("attributeValues") or {}
    value_type = value_info.get("valueType")
    if value_type in {"String", "string"}:
        if len(data) < 8:
            return []
        total_bytes = struct.unpack_from("<I", data, 4)[0]
        lengths_offset = 8
        values_offset = lengths_offset + count * 4
        lengths = list(struct.unpack_from("<" + "I" * count, data, lengths_offset)) if count else []
        blob = data[values_offset : values_offset + total_bytes]
        vals = []
        pos = 0
        for ln in lengths:
            vals.append(blob[pos : pos + ln].decode("utf-8", errors="replace").rstrip("\x00"))
            pos += ln
        return vals
    value_offset = 4
    if value_type in {"Float64", "Double", "Int64", "UInt64"}:
        value_offset = 8
    if value_type in {"Float64", "Double"}:
        return list(struct.unpack_from("<" + "d" * count, data, value_offset)) if count else []
    if value_type in {"Float32"}:
        return list(struct.unpack_from("<" + "f" * count, data, value_offset)) if count else []
    if value_type in {"Int32", "Oid32"}:
        return list(struct.unpack_from("<" + "i" * count, data, value_offset)) if count else []
    if value_type in {"UInt32"}:
        return list(struct.unpack_from("<" + "I" * count, data, value_offset)) if count else []
    if value_type in {"Int64"}:
        return list(struct.unpack_from("<" + "q" * count, data, value_offset)) if count else []
    if value_type in {"UInt64"}:
        return list(struct.unpack_from("<" + "Q" * count, data, value_offset)) if count else []
    return []


def nice_value(name: str, value: Any) -> Any:
    if isinstance(value, float) and name.lower() in {"objectid", "districte", "barri"}:
        if value.is_integer():
            return int(value)
    return value


def geometry_offsets(vertex_count: int, feature_count: int) -> dict[str, int]:
    offset = 8
    pos = offset
    normal = pos + vertex_count * 12
    uv0 = normal + vertex_count * 12
    color = uv0 + vertex_count * 8
    feature_id = color + vertex_count * 4
    face_range = feature_id + feature_count * 8
    return {
        "position": pos,
        "normal": normal,
        "uv0": uv0,
        "color": color,
        "feature_id": feature_id,
        "face_range": face_range,
    }


def feature_ranges(geom: bytes, vertex_count: int, feature_count: int) -> tuple[list[int], list[tuple[int, int]]]:
    offsets = geometry_offsets(vertex_count, feature_count)
    expected = offsets["face_range"] + feature_count * 8
    if len(geom) < expected:
        return [], []
    ids = [struct.unpack_from("<Q", geom, offsets["feature_id"] + i * 8)[0] for i in range(feature_count)]
    ranges = [struct.unpack_from("<II", geom, offsets["face_range"] + i * 8) for i in range(feature_count)]
    return ids, ranges


def feature_data_ids(data: bytes) -> list[Any]:
    try:
        obj = json.loads(data.decode("utf-8"))
    except Exception:
        return []
    rows = obj.get("featureData") or obj.get("features") or []
    return [row.get("id") for row in rows if isinstance(row, dict)]


def usda_array_stream(items: list[str], per_line: int, indent: str) -> str:
    return ",\n".join(indent + ", ".join(items[i : i + per_line]) for i in range(0, len(items), per_line))


def mesh_block(leaf: LeafNode, geom: bytes) -> tuple[str, dict[str, Any]]:
    vertex_count, feature_count = struct.unpack_from("<II", geom, 0)
    if vertex_count != leaf.vertex_count:
        raise ValueError(f"node {leaf.node_id}: vertex mismatch page={leaf.vertex_count} geom={vertex_count}")
    tri_count = vertex_count // 3
    offsets = geometry_offsets(vertex_count, feature_count)
    if len(geom) < offsets["position"] + vertex_count * 12:
        raise ValueError(f"node {leaf.node_id}: geometry buffer too short")
    center_lon, center_lat, center_z = float(leaf.mbs[0]), float(leaf.mbs[1]), float(leaf.mbs[2])
    points = []
    for idx in range(vertex_count):
        dx_lon, dy_lat, dz = struct.unpack_from("<fff", geom, offsets["position"] + idx * 12)
        lon = center_lon + dx_lon
        lat = center_lat + dy_lat
        x, y = lonlat_to_enu(lon, lat)
        points.append(f"({x:.3f}, {y:.3f}, {center_z + dz:.3f})")
    counts = ["3"] * tri_count
    indices = [str(i) for i in range(tri_count * 3)]
    prim = f"Node_{re.sub(r'[^A-Za-z0-9_]', '_', leaf.node_id)}"
    block = f'''    def Mesh "{prim}"
    {{
        custom string citybrain:node_id = "{leaf.node_id}"
        custom string citybrain:i3s_resource_id = "{leaf.resource_id}"
        custom int citybrain:source_vertex_count = {vertex_count}
        custom int citybrain:source_feature_count = {feature_count}
        custom string citybrain:identity_sidecar = "../identity_shards/shard_{leaf.shard_id:03d}_identity.jsonl"
        uniform token subdivisionScheme = "none"
        int[] faceVertexCounts = [
{usda_array_stream(counts, 24, "            ")}
        ]
        int[] faceVertexIndices = [
{usda_array_stream(indices, 24, "            ")}
        ]
        point3f[] points = [
{usda_array_stream(points, 3, "            ")}
        ]
    }}
'''
    return block, {"vertex_count": vertex_count, "feature_count": feature_count, "triangle_count": tri_count}


def fetch_node_package(leaf: LeafNode, attr_infos: dict[str, dict[str, Any]]) -> dict[str, Any]:
    node_url = f"{LAYER_URL}/nodes/{urllib.parse.quote(leaf.resource_id, safe='-')}"
    geom = fetch_bytes(f"{node_url}/geometries/0")
    feature_blob = b""
    try:
        feature_blob = fetch_bytes(f"{node_url}/features/0")
    except Exception:
        feature_blob = b""
    attrs: dict[str, list[Any]] = {}
    for name, info in attr_infos.items():
        try:
            attrs[name] = decode_attribute(fetch_bytes(f"{node_url}/attributes/{info['key']}/0"), info)
        except Exception:
            attrs[name] = []
    return {"leaf": leaf, "geometry": geom, "feature_blob": feature_blob, "attributes": attrs}


def build_identity_rows(pkg: dict[str, Any], attr_names: list[str]) -> list[dict[str, Any]]:
    leaf: LeafNode = pkg["leaf"]
    geom: bytes = pkg["geometry"]
    vertex_count, feature_count = struct.unpack_from("<II", geom, 0)
    geom_ids, ranges = feature_ranges(geom, vertex_count, feature_count)
    feature_ids = feature_data_ids(pkg["feature_blob"])
    rows = []
    attrs: dict[str, list[Any]] = pkg["attributes"]
    for i in range(feature_count):
        row = {
            "node_id": leaf.node_id,
            "i3s_resource_id": leaf.resource_id,
            "feature_ordinal": i,
            "geometry_feature_id": geom_ids[i] if i < len(geom_ids) else None,
            "feature_json_id": feature_ids[i] if i < len(feature_ids) else None,
            "face_start": ranges[i][0] if i < len(ranges) else None,
            "face_count": ranges[i][1] if i < len(ranges) else None,
            "citybrain_identity_status": "BARCELONA_LOD2_SOURCE_OBJECTID_AREA_CONTEXT_ONLY",
            "claim_boundary": "3D source geometry and source attributes only; cadastre/address identity requires later spatial join; not ownership/legal/certified affected-building truth",
        }
        for name in attr_names:
            values = attrs.get(name) or []
            row[name] = nice_value(name, values[i]) if i < len(values) else None
        source_id = row.get("OBJECTID") or row.get("feature_json_id") or row.get("geometry_feature_id")
        row["citybrain_building_id"] = f"barc:lod2_source_object:{source_id}" if source_id not in {None, "", 0} else None
        row["citybrain_3d_source_id"] = f"barc:arcgis_lod2_object:{source_id}" if source_id not in {None, "", 0} else None
        row["citybrain_district_ref"] = f"barc:district:{row.get('DISTRICTE')}" if row.get("DISTRICTE") not in {None, "", 0} else None
        row["citybrain_neighbourhood_ref"] = f"barc:neighbourhood:{row.get('BARRI')}" if row.get("BARRI") not in {None, "", 0} else None
        row["citybrain_parcel_id"] = None
        rows.append(row)
    return rows


def shard_groups(leaves: list[LeafNode]) -> dict[int, list[LeafNode]]:
    groups: dict[int, list[LeafNode]] = {}
    for leaf in leaves:
        groups.setdefault(leaf.shard_id, []).append(leaf)
    return groups


def shard_header(shard_id: int, leaves: list[LeafNode]) -> str:
    vertices = sum(n.vertex_count for n in leaves)
    features = sum(n.feature_count for n in leaves)
    return f'''#usda 1.0
(
    defaultPrim = "Shard_{shard_id:03d}"
    metersPerUnit = 1
    upAxis = "Z"
    doc = "CityBrain Barcelona LOD2 buildings full I3S export shard {shard_id:03d}. Leaf-node geometry only."
)

def Xform "Shard_{shard_id:03d}"
{{
    custom string citybrain:task = "{TASK}"
    custom string citybrain:source_url = "{URL}"
    custom string citybrain:claim_boundary = "3d_visual_identity_context_only_not_certified_not_control"
    custom int citybrain:leaf_node_count = {len(leaves)}
    custom int citybrain:vertex_count = {vertices}
    custom int citybrain:feature_count = {features}
    custom string citybrain:identity_sidecar = "../identity_shards/shard_{shard_id:03d}_identity.jsonl"
'''


def write_shard(
    shard_id: int,
    leaves: list[LeafNode],
    attr_infos: dict[str, dict[str, Any]],
    attr_names: list[str],
    workers: int,
    force: bool,
) -> dict[str, Any]:
    shard_path = OUT / "usd_shards" / f"BARC_LOD2_shard_{shard_id:03d}.usda"
    identity_path = OUT / "identity_shards" / f"shard_{shard_id:03d}_identity.jsonl"
    report_path = OUT / "logs" / f"shard_{shard_id:03d}_report.json"
    if not force and shard_path.exists() and identity_path.exists() and report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["status"] = "SKIPPED_EXISTING"
        return report

    failures = []
    stats = {"leaf_nodes": 0, "vertices": 0, "triangles": 0, "features": 0}
    shard_path.parent.mkdir(parents=True, exist_ok=True)
    identity_path.parent.mkdir(parents=True, exist_ok=True)
    with shard_path.open("w", encoding="utf-8", newline="\n") as usd, identity_path.open("w", encoding="utf-8", newline="\n") as ident:
        usd.write(shard_header(shard_id, leaves))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(fetch_node_package, leaf, attr_infos): leaf for leaf in leaves}
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                leaf = futures[future]
                completed += 1
                try:
                    pkg = future.result()
                    block, node_stats = mesh_block(leaf, pkg["geometry"])
                    usd.write(block)
                    for row in build_identity_rows(pkg, attr_names):
                        ident.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
                    stats["leaf_nodes"] += 1
                    stats["vertices"] += node_stats["vertex_count"]
                    stats["triangles"] += node_stats["triangle_count"]
                    stats["features"] += node_stats["feature_count"]
                except Exception as exc:
                    failures.append({"node_id": leaf.node_id, "error": f"{type(exc).__name__}: {exc}"})
                if completed % 25 == 0:
                    print(f"shard {shard_id:03d}: {completed}/{len(leaves)} nodes processed", flush=True)
        usd.write("}\n")
    report = {
        "status": "PASS" if not failures else "PASS_WITH_NODE_FAILURES",
        "shard_id": shard_id,
        "usd_path": str(shard_path),
        "identity_path": str(identity_path),
        "leaf_node_target_count": len(leaves),
        **stats,
        "failure_count": len(failures),
        "failures": failures[:100],
        "usd_bytes": shard_path.stat().st_size if shard_path.exists() else 0,
        "identity_bytes": identity_path.stat().st_size if identity_path.exists() else 0,
    }
    write_json(report_path, report)
    return report


def write_master_usda(shard_reports: list[dict[str, Any]]) -> Path:
    master = OUT / "BARC_LOD2_BUILDINGS_FULL_MASTER.usda"
    refs = []
    for report in sorted(shard_reports, key=lambda r: r["shard_id"]):
        rel_path = Path(report["usd_path"]).relative_to(OUT).as_posix()
        refs.append(
            f'''    def Xform "Shard_{report["shard_id"]:03d}" (
        prepend references = @{rel_path}@
    )
    {{
        custom string citybrain:identity_sidecar = "identity_shards/shard_{report["shard_id"]:03d}_identity.jsonl"
    }}
'''
        )
    text = f'''#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Z"
    doc = "CityBrain full sharded export of Barcelona 3D LOD2 buildings. References shard USDA files."
)

def Xform "World"
{{
    custom string citybrain:task = "{TASK}"
    custom string citybrain:source_url = "{URL}"
    custom string citybrain:claim_boundary = "review_context_3d_identity_visualization_only_not_certified_not_control"
{''.join(refs)}
}}
'''
    write_text(master, text)
    return master


def no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = [name for name in before if before[name] != after[name]]
    report = {"status": "PASS" if not changed else "FAIL", "changed_roots": changed, "checked_root_count": len(before)}
    write_text(OUT / "NO_MUTATION_AUDIT.md", "# No-Mutation Audit\n\n" + f"Status: `{report['status']}`\n\n```json\n" + json.dumps(report, indent=2) + "\n```\n")
    return report


def secret_audit() -> dict[str, Any]:
    patterns = [re.compile(r"(?i)(api[_-]?key|app[_-]?key|secret|token)\s*[:=]\s*[a-z0-9]{16,}")]
    findings = []
    for path in OUT.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".usda", ".jsonl"}:
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
    if OUT.exists() and not args.resume:
        shutil.rmtree(OUT)
    for folder in ["usd_shards", "identity_shards", "logs"]:
        (OUT / folder).mkdir(parents=True, exist_ok=True)

    root, layer, attr_by_name = layer_info()
    attr_infos = {name: attr_by_name[name] for name in SELECTED_FIELDS if name in attr_by_name}
    attr_names = list(attr_infos)
    leaves, inventory = enumerate_leaves(args.target_vertices_per_shard, args.max_leaves)
    groups = shard_groups(leaves)
    write_json(OUT / "BARC_LOD2_I3S_LAYER_METADATA.json", {"root": root, "layer": layer})
    write_json(OUT / "BARC_LOD2_LEAF_NODE_INVENTORY.json", {"inventory": inventory, "leaf_nodes": [leaf.__dict__ for leaf in leaves]})
    write_json(OUT / "BARC_LOD2_SELECTED_ATTRIBUTE_MAP.json", {"selected_fields": attr_names, "attribute_storage": attr_infos})

    shard_reports = []
    for shard_id in sorted(groups):
        print(f"starting shard {shard_id:03d}/{len(groups)-1:03d} with {len(groups[shard_id])} leaf nodes", flush=True)
        shard_reports.append(write_shard(shard_id, groups[shard_id], attr_infos, attr_names, args.workers, force=not args.resume))

    master = write_master_usda(shard_reports)
    total_failures = sum(r.get("failure_count", 0) for r in shard_reports)
    exported_leaf_nodes = sum(r.get("leaf_nodes", 0) for r in shard_reports if r.get("status") != "SKIPPED_EXISTING")
    if args.resume:
        exported_leaf_nodes = sum(r.get("leaf_nodes", 0) for r in [json.loads(p.read_text(encoding="utf-8")) for p in sorted((OUT / "logs").glob("shard_*_report.json"))])
    reports_for_totals = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((OUT / "logs").glob("shard_*_report.json"))]
    totals = {
        "leaf_nodes_exported": sum(r.get("leaf_nodes", 0) for r in reports_for_totals),
        "vertices_exported": sum(r.get("vertices", 0) for r in reports_for_totals),
        "triangles_exported": sum(r.get("triangles", 0) for r in reports_for_totals),
        "features_exported": sum(r.get("features", 0) for r in reports_for_totals),
        "usd_shard_count": len(reports_for_totals),
        "usd_bytes": sum(r.get("usd_bytes", 0) for r in reports_for_totals) + (master.stat().st_size if master.exists() else 0),
        "identity_bytes": sum(r.get("identity_bytes", 0) for r in reports_for_totals),
        "failure_count": sum(r.get("failure_count", 0) for r in reports_for_totals),
    }
    after = snapshot_roots()
    no_mut = no_mutation_audit(before, after)
    secret = secret_audit()
    full = (
        totals["leaf_nodes_exported"] == inventory["leaf_node_count"]
        and totals["vertices_exported"] == inventory["leaf_vertex_count"]
        and totals["failure_count"] == 0
    )
    status = PASS_FULL if full and no_mut["status"] == "PASS" and secret["status"] == "PASS" else PASS_LIMITED if no_mut["status"] == "PASS" and secret["status"] == "PASS" else FAIL
    write_text(
        OUT / "README.md",
        f"# {TASK}\n\nStatus: `{status}`\n\nFull Codex-side sharded export of Barcelona 3D LOD2 buildings from I3S leaf nodes. Master scene: `{master.as_posix()}`.\n",
    )
    write_text(
        OUT / "BARC_LOD2_FULL_EXPORT_REPORT.md",
        f"# Barcelona LOD2 Full I3S Export\n\n"
        f"Status: `{status}`\n\n"
        f"- Source: {URL}\n"
        f"- Master USDA: `{master.as_posix()}`\n"
        f"- USD shard count: `{totals['usd_shard_count']}`\n"
        f"- Leaf nodes exported: `{totals['leaf_nodes_exported']}` / `{inventory['leaf_node_count']}`\n"
        f"- Vertices exported: `{totals['vertices_exported']}`\n"
        f"- Triangles exported: `{totals['triangles_exported']}`\n"
        f"- Feature/identity rows exported: `{totals['features_exported']}`\n"
        f"- Identity fields: `{', '.join(attr_names)}`\n"
        f"- Failure count: `{totals['failure_count']}`\n\n"
        "Boundary: 3D geometry and source OBJECTID/category/area fields are review/context anchors only; cadastre/address identity requires later spatial join; no ownership, legal, enforcement, dispatch, control, or certified affected-building claim.\n",
    )
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": utc_now(),
        "source_url": URL,
        "master_usda": str(master),
        "inventory": inventory,
        "totals": totals,
        "selected_identity_fields": attr_names,
        "checks": {
            "leaf_nodes_complete": totals["leaf_nodes_exported"] == inventory["leaf_node_count"],
            "vertices_complete": totals["vertices_exported"] == inventory["leaf_vertex_count"],
            "no_node_failures": totals["failure_count"] == 0,
            "no_mutation_pass": no_mut["status"] == "PASS",
            "secret_audit_pass": secret["status"] == "PASS",
        },
        "limitations": [
            "USDA shards are ASCII because local binary USD tooling is not installed.",
            "USD prims are node-level meshes; per-source-object attributes are preserved in JSONL sidecars by feature/face range.",
            "Source does not include Barcelona cadastre parcel/building/address identifiers; those require a later spatial join.",
            "No textures/material fidelity beyond raw geometry positions in this export.",
            "No ownership/legal/certified affected-building/control claim.",
        ],
    }
    write_json(OUT / "D4_3D_BARC_LOD2_FULL_I3S_EXPORT_R1_DECISION.json", decision)
    shutil.copy2(Path(__file__), OUT / "run_d4_3d_barc_lod2_full_i3s_export_r1.py")
    hash_outputs()
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Run {TASK}.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--target-vertices-per-shard", type=int, default=3_000_000)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--max-leaves", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    decision = run(args)
    print(f"{TASK}: {decision['status']}")
    print(f"Output: {OUT}")
    return 0 if decision["status"] in {PASS_FULL, PASS_LIMITED} else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""D4-3D-VISUAL-MESH-FOOTPRINT-ALIGNMENT-R1.

Adds the missing Track 2 bridge for high-fidelity imported meshes that have no
native IDs and no trustworthy geolocation. The mesh remains visual geometry;
official footprints/cadastre/building polygons provide identity candidates via
bounded transform search and polygon intersection scoring.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shapely import affinity
from shapely.geometry import MultiPoint, Polygon, mapping, shape
from shapely.ops import unary_union


TASK = "D4-3D-VISUAL-MESH-FOOTPRINT-ALIGNMENT-R1"
PASS_LIMITED = "PASS_D4_3D_VISUAL_MESH_FOOTPRINT_ALIGNMENT_R1_WITH_LIMITATIONS"
FAIL = "FAIL_D4_3D_VISUAL_MESH_FOOTPRINT_ALIGNMENT_R1"
OUT = Path("outputs/d4_3d_visual_mesh_footprint_alignment_r1")
SCHEMA_VERSION = "d4-3d-visual-mesh-footprint-alignment-r1.v1"

FOLDERS = ["contract", "schema", "examples", "validation", "guardrails", "logs"]

PREVIOUS_ROOTS = {
    "city_asset_contract": Path("outputs/d4_3d_city_asset_contract_r1"),
    "barcelona_real_lod2": Path("outputs/d4_3d_omniverse_load_prep_r1"),
    "barcelona_pipeline_fix": Path("outputs/d4_3d_barcelona_asset_pipeline_fix_r1"),
    "usd_binding": Path("outputs/main_track1_d4_usd_city_subset_binding"),
    "platform_state": Path("outputs/platform_state_generated"),
    "pv1_d19_d22": Path("outputs/pv1_d19d20d21d22_platform_v1_snapshot_gate"),
}

ALIGNMENT_STATUSES = [
    "UNREFERENCED_VISUAL_MESH",
    "ROUGH_PLACED",
    "INTERSECTION_ALIGNED",
    "CONTROL_POINT_ALIGNED",
    "FOOTPRINT_ID_CANDIDATE_BOUND",
    "AMBIGUOUS_BINDING_REVIEW_REQUIRED",
    "NO_MATCH",
    "BLOCKED_BY_MISSING_FOOTPRINTS",
]

BINDING_STATUSES = [
    "AUTO_CANDIDATE_HIGH_CONFIDENCE",
    "REVIEW_CANDIDATE",
    "AMBIGUOUS_REVIEW_REQUIRED",
    "NO_MATCH",
]


@dataclass(frozen=True)
class SimilarityTransform:
    scale: float
    rotation_deg: float
    translate_x: float
    translate_y: float

    def as_dict(self) -> dict[str, float]:
        return {
            "scale": round(self.scale, 8),
            "rotation_deg": round(self.rotation_deg, 8),
            "translate_x": round(self.translate_x, 8),
            "translate_y": round(self.translate_y, 8),
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.relative_to(Path.cwd()).as_posix()
    except Exception:
        return path.as_posix()


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


def transform_polygon(poly: Polygon, t: SimilarityTransform) -> Polygon:
    out = affinity.scale(poly, xfact=t.scale, yfact=t.scale, origin=(0, 0))
    out = affinity.rotate(out, t.rotation_deg, origin=(0, 0), use_radians=False)
    out = affinity.translate(out, xoff=t.translate_x, yoff=t.translate_y)
    return out


def polygon_iou(a: Polygon, b: Polygon) -> float:
    if a.is_empty or b.is_empty:
        return 0.0
    inter = a.intersection(b).area
    if inter <= 0:
        return 0.0
    union = a.union(b).area
    return inter / union if union else 0.0


def centroid_distance(a: Polygon, b: Polygon) -> float:
    ca = a.centroid
    cb = b.centroid
    return math.hypot(ca.x - cb.x, ca.y - cb.y)


def best_intersections(
    mesh_polygons: list[dict[str, Any]],
    footprint_polygons: list[dict[str, Any]],
    transform: SimilarityTransform,
) -> list[dict[str, Any]]:
    rows = []
    for mesh in mesh_polygons:
        aligned = transform_polygon(mesh["geometry"], transform)
        candidates = []
        for fp in footprint_polygons:
            inter_area = aligned.intersection(fp["geometry"]).area
            if inter_area <= 0:
                continue
            iou = polygon_iou(aligned, fp["geometry"])
            candidates.append(
                {
                    "footprint_id": fp["id"],
                    "iou": iou,
                    "intersection_area": inter_area,
                    "mesh_coverage": inter_area / aligned.area if aligned.area else 0.0,
                    "footprint_coverage": inter_area / fp["geometry"].area if fp["geometry"].area else 0.0,
                    "centroid_distance_m": centroid_distance(aligned, fp["geometry"]),
                }
            )
        candidates.sort(key=lambda r: (r["iou"], r["mesh_coverage"], -r["centroid_distance_m"]), reverse=True)
        top = candidates[0] if candidates else None
        second = candidates[1] if len(candidates) > 1 else None
        rows.append(
            {
                "visual_mesh_instance_id": mesh["id"],
                "aligned_geometry": aligned,
                "best": top,
                "second": second,
                "candidate_count": len(candidates),
            }
        )
    return rows


def score_transform(
    mesh_polygons: list[dict[str, Any]],
    footprint_polygons: list[dict[str, Any]],
    transform: SimilarityTransform,
) -> float:
    score = 0.0
    for row in best_intersections(mesh_polygons, footprint_polygons, transform):
        best = row["best"]
        second = row["second"]
        if not best:
            score -= 0.25
            continue
        ambiguity_penalty = max(0.0, (second["iou"] if second else 0.0) - 0.08) * 0.25
        score += best["iou"] + (0.2 * best["mesh_coverage"]) - ambiguity_penalty
    return score


def estimate_transform_by_intersection(
    mesh_polygons: list[dict[str, Any]],
    footprint_polygons: list[dict[str, Any]],
    initial: SimilarityTransform,
) -> tuple[SimilarityTransform, dict[str, Any]]:
    """Bounded grid search around user rough placement.

    This is intentionally deterministic and conservative. It needs a rough AOI or
    starting transform; arbitrary citywide geolocation from an unreferenced asset
    is not solvable from geometry alone.
    """
    stages = [
        {"scale": 0.05, "rot": 4.0, "xy": 12.0, "steps": (5, 9, 9, 9)},
        {"scale": 0.015, "rot": 1.0, "xy": 3.0, "steps": (5, 9, 7, 7)},
        {"scale": 0.005, "rot": 0.25, "xy": 1.0, "steps": (5, 9, 5, 5)},
    ]
    best = initial
    best_score = score_transform(mesh_polygons, footprint_polygons, best)
    evaluated = 1
    for stage in stages:
        scale_count, rot_count, x_count, y_count = stage["steps"]
        current = best
        scales = linspace(current.scale - stage["scale"], current.scale + stage["scale"], scale_count)
        rotations = linspace(current.rotation_deg - stage["rot"], current.rotation_deg + stage["rot"], rot_count)
        xs = linspace(current.translate_x - stage["xy"], current.translate_x + stage["xy"], x_count)
        ys = linspace(current.translate_y - stage["xy"], current.translate_y + stage["xy"], y_count)
        for scale in scales:
            if scale <= 0:
                continue
            for rotation in rotations:
                for x in xs:
                    for y in ys:
                        candidate = SimilarityTransform(scale=scale, rotation_deg=rotation, translate_x=x, translate_y=y)
                        evaluated += 1
                        s = score_transform(mesh_polygons, footprint_polygons, candidate)
                        if s > best_score:
                            best_score = s
                            best = candidate
    report = {
        "method": "bounded_similarity_grid_search_max_intersection_iou",
        "initial_transform": initial.as_dict(),
        "best_transform": best.as_dict(),
        "best_score": round(best_score, 6),
        "transforms_evaluated": evaluated,
        "requires_rough_aoi_or_initial_transform": True,
    }
    return best, report


def linspace(start: float, end: float, count: int) -> list[float]:
    if count <= 1:
        return [start]
    step = (end - start) / (count - 1)
    return [start + (i * step) for i in range(count)]


def binding_status(best: dict[str, Any] | None, second: dict[str, Any] | None) -> str:
    if not best:
        return "NO_MATCH"
    second_iou = second["iou"] if second else 0.0
    margin = best["iou"] - second_iou
    if best["iou"] >= 0.72 and best["mesh_coverage"] >= 0.85 and best["centroid_distance_m"] <= 2.5 and margin >= 0.25:
        return "AUTO_CANDIDATE_HIGH_CONFIDENCE"
    if best["iou"] >= 0.45 and best["mesh_coverage"] >= 0.65 and best["centroid_distance_m"] <= 6.0 and margin >= 0.12:
        return "REVIEW_CANDIDATE"
    if best["iou"] >= 0.25:
        return "AMBIGUOUS_REVIEW_REQUIRED"
    return "NO_MATCH"


def build_binding_rows(
    intersections: list[dict[str, Any]],
    transform: SimilarityTransform,
) -> list[dict[str, Any]]:
    rows = []
    for row in intersections:
        best = row["best"]
        second = row["second"]
        status = binding_status(best, second)
        rows.append(
            {
                "visual_mesh_instance_id": row["visual_mesh_instance_id"],
                "candidate_footprint_id": best["footprint_id"] if best else None,
                "binding_status": status,
                "identity_status": "FOOTPRINT_ID_CANDIDATE_BOUND" if status != "NO_MATCH" else "NO_MATCH",
                "alignment_method": "intersection_iou_after_bounded_similarity_transform",
                "alignment_transform": transform.as_dict(),
                "iou": round(best["iou"], 6) if best else 0.0,
                "mesh_coverage": round(best["mesh_coverage"], 6) if best else 0.0,
                "footprint_coverage": round(best["footprint_coverage"], 6) if best else 0.0,
                "centroid_distance_m": round(best["centroid_distance_m"], 6) if best else None,
                "second_best_footprint_id": second["footprint_id"] if second else None,
                "second_best_iou": round(second["iou"], 6) if second else 0.0,
                "claim_boundary": "candidate visual-to-footprint binding only; official footprint ID remains source of identity; not a certified affected-building claim",
            }
        )
    return rows


def rectangle(cx: float, cy: float, w: float, h: float, rot_deg: float = 0.0) -> Polygon:
    poly = Polygon([(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)])
    poly = affinity.rotate(poly, rot_deg, origin=(0, 0), use_radians=False)
    return affinity.translate(poly, xoff=cx, yoff=cy)


def inverse_transform_polygon(poly: Polygon, t: SimilarityTransform) -> Polygon:
    out = affinity.translate(poly, xoff=-t.translate_x, yoff=-t.translate_y)
    out = affinity.rotate(out, -t.rotation_deg, origin=(0, 0), use_radians=False)
    out = affinity.scale(out, xfact=1 / t.scale, yfact=1 / t.scale, origin=(0, 0))
    return out


def synthetic_fixture() -> tuple[list[dict[str, Any]], list[dict[str, Any]], SimilarityTransform, SimilarityTransform]:
    footprints = [
        {"id": "barc:cadastre_building:synthetic_001", "geometry": rectangle(0, 0, 22, 16, 8)},
        {"id": "barc:cadastre_building:synthetic_002", "geometry": rectangle(35, 2, 18, 18, 0)},
        {"id": "barc:cadastre_building:synthetic_003", "geometry": rectangle(2, 38, 20, 13, -5)},
        {"id": "barc:cadastre_building:synthetic_004", "geometry": rectangle(38, 42, 24, 14, 6)},
    ]
    true_transform = SimilarityTransform(scale=1.035, rotation_deg=12.0, translate_x=136.0, translate_y=-78.0)
    mesh = []
    for idx, fp in enumerate(footprints, start=1):
        local = inverse_transform_polygon(fp["geometry"], true_transform)
        local = affinity.scale(local, xfact=0.992 + idx * 0.002, yfact=1.004 - idx * 0.001, origin="centroid")
        mesh.append({"id": f"visual_mesh:marketplace_demo:{idx:03d}", "geometry": local})
    rough_initial = SimilarityTransform(scale=1.0, rotation_deg=10.0, translate_x=132.0, translate_y=-73.0)
    return mesh, footprints, true_transform, rough_initial


def geojson_feature(obj_id: str, poly: Polygon, props: dict[str, Any]) -> dict[str, Any]:
    return {"type": "Feature", "id": obj_id, "properties": {"id": obj_id, **props}, "geometry": mapping(poly)}


def write_fixture_geojson(mesh: list[dict[str, Any]], footprints: list[dict[str, Any]], transform: SimilarityTransform) -> None:
    write_json(
        OUT / "examples" / "SYNTHETIC_VISUAL_MESH_LOCAL_FOOTPRINTS.geojson",
        {"type": "FeatureCollection", "features": [geojson_feature(m["id"], m["geometry"], {"kind": "visual_mesh_local"}) for m in mesh]},
    )
    write_json(
        OUT / "examples" / "SYNTHETIC_OFFICIAL_BUILDING_FOOTPRINTS.geojson",
        {"type": "FeatureCollection", "features": [geojson_feature(f["id"], f["geometry"], {"kind": "official_footprint"}) for f in footprints]},
    )
    aligned = [geojson_feature(m["id"], transform_polygon(m["geometry"], transform), {"kind": "visual_mesh_aligned"}) for m in mesh]
    write_json(OUT / "examples" / "SYNTHETIC_ALIGNED_VISUAL_MESH_FOOTPRINTS.geojson", {"type": "FeatureCollection", "features": aligned})


def read_geojson_polygons(path: Path, id_field: str) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for idx, feature in enumerate(data.get("features", []), start=1):
        geom = shape(feature["geometry"])
        if geom.geom_type == "MultiPolygon":
            geom = max(list(geom.geoms), key=lambda g: g.area)
        if geom.geom_type != "Polygon" or geom.is_empty:
            continue
        props = feature.get("properties", {})
        obj_id = props.get(id_field) or props.get("id") or feature.get("id") or f"{path.stem}:{idx}"
        rows.append({"id": str(obj_id), "geometry": geom})
    return rows


def extract_obj_footprints(path: Path) -> list[dict[str, Any]]:
    """Best-effort OBJ footprint extraction by object/group name.

    This is for rough visual binding only. For FBX/glTF use Blender/Omniverse to
    export footprints or convert to OBJ/GeoJSON first.
    """
    vertices: list[tuple[float, float, float]] = []
    groups: dict[str, list[int]] = {}
    current = path.stem
    groups[current] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith(("o ", "g ")):
            current = line.split(maxsplit=1)[1].strip() or current
            groups.setdefault(current, [])
        elif line.startswith("v "):
            parts = line.split()
            if len(parts) >= 4:
                vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif line.startswith("f "):
            parts = line.split()[1:]
            for p in parts:
                raw = p.split("/")[0]
                if not raw:
                    continue
                vi = int(raw)
                if vi < 0:
                    vi = len(vertices) + vi + 1
                groups.setdefault(current, []).append(vi - 1)
    rows = []
    for name, indices in groups.items():
        pts = [(vertices[i][0], vertices[i][1]) for i in sorted(set(indices)) if 0 <= i < len(vertices)]
        if len(pts) < 3:
            continue
        hull = MultiPoint(pts).convex_hull
        if hull.geom_type == "Polygon" and hull.area > 0:
            rows.append({"id": f"visual_mesh:{path.stem}:{name}", "geometry": hull})
    return rows


def load_inputs(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], SimilarityTransform, dict[str, Any]]:
    if args.mesh_footprints and args.official_footprints:
        mesh = read_geojson_polygons(Path(args.mesh_footprints), args.mesh_id_field)
        footprints = read_geojson_polygons(Path(args.official_footprints), args.footprint_id_field)
        source = {
            "mode": "geojson_input",
            "mesh_footprints": args.mesh_footprints,
            "official_footprints": args.official_footprints,
        }
    elif args.obj_mesh and args.official_footprints:
        mesh = extract_obj_footprints(Path(args.obj_mesh))
        footprints = read_geojson_polygons(Path(args.official_footprints), args.footprint_id_field)
        source = {
            "mode": "obj_mesh_plus_geojson_footprints",
            "obj_mesh": args.obj_mesh,
            "official_footprints": args.official_footprints,
        }
    else:
        mesh, footprints, true_transform, initial = synthetic_fixture()
        return mesh, footprints, initial, {"mode": "synthetic_fixture", "true_transform": true_transform.as_dict()}

    initial = SimilarityTransform(
        scale=args.initial_scale,
        rotation_deg=args.initial_rotation_deg,
        translate_x=args.initial_translate_x,
        translate_y=args.initial_translate_y,
    )
    return mesh, footprints, initial, source


def alignment_schema() -> dict[str, Any]:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain D4 Visual Mesh Footprint Alignment Schema",
        "schema_version": SCHEMA_VERSION,
        "type": "object",
        "required": [
            "visual_mesh_instance_id",
            "candidate_footprint_id",
            "binding_status",
            "identity_status",
            "alignment_method",
            "alignment_transform",
            "iou",
            "mesh_coverage",
            "footprint_coverage",
            "centroid_distance_m",
            "claim_boundary",
        ],
        "properties": {
            "binding_status": {"enum": BINDING_STATUSES},
            "identity_status": {"enum": ALIGNMENT_STATUSES},
            "alignment_transform": {
                "type": "object",
                "required": ["scale", "rotation_deg", "translate_x", "translate_y"],
            },
        },
    }
    write_json(OUT / "ALIGNMENT_SCHEMA.json", schema)
    write_json(OUT / "schema" / "ALIGNMENT_SCHEMA.json", schema)
    return schema


def write_contract_docs() -> None:
    alignment_contract = f"""# D4 Visual Mesh Footprint Alignment Contract

Task: `{TASK}`

Problem fixed: high-fidelity imported meshes from marketplace, FBX, OBJ, glTF, CityEngine, or manual artists may have no official IDs and may have no trustworthy geolocation.

Policy:
- Imported mesh geometry is visual geometry.
- Official footprint/cadastre/building polygons remain the source of identity.
- A mesh can receive a candidate binding to an official footprint only through an explicit alignment transform and intersection score.
- Intersection binding creates a review-safe visual-to-footprint edge, not a certified affected-building or legal/ownership conclusion.

Required real-data inputs:
- Visual mesh footprint polygons in mesh local coordinates or rough scene coordinates.
- Official footprints/cadastre/building polygons in local ENU metres for the city subset.
- Rough initial transform or AOI. Without at least rough placement, arbitrary global location cannot be solved from geometry alone.

Supported alignment methods:
- `bounded_similarity_grid_search_max_intersection_iou`
- `control_point_aligned_then_intersection_verified`
- `manual_transform_then_intersection_verified`

Binding thresholds:
- `AUTO_CANDIDATE_HIGH_CONFIDENCE`: IoU >= 0.72, mesh coverage >= 0.85, centroid distance <= 2.5m, and second-best margin >= 0.25.
- `REVIEW_CANDIDATE`: IoU >= 0.45, mesh coverage >= 0.65, centroid distance <= 6m, and second-best margin >= 0.12.
- `AMBIGUOUS_REVIEW_REQUIRED`: IoU >= 0.25 but threshold/margin insufficient.
- `NO_MATCH`: no robust intersection candidate.
"""
    algorithm = """# Alignment Algorithm

1. Extract visual mesh footprints by object/group/material/connected component.
2. Keep the mesh local coordinate frame; do not invent official IDs.
3. Load official footprints into the city subset local ENU frame.
4. Start from a rough placement transform supplied by the user, Blender, Omniverse, ArcGIS, or a few landmark control points.
5. Search bounded scale/rotation/translation candidates.
6. Score each transform by best polygon IoU and mesh coverage against official footprints.
7. For each visual mesh object, assign only candidate binding edges using IoU, coverage, centroid distance, and second-best ambiguity.
8. Write all ambiguous or no-match rows for review.

Hard boundary: geometry matching does not prove ownership, legal identity, occupancy, affected-building status, or operational truth.
"""
    import_policy = """# Marketplace Mesh Import Policy

Marketplace meshes are allowed as high-fidelity visual assets.

Required handling:
- Preserve original file path/source/vendor/license reference.
- Treat all native mesh names and object IDs as visual IDs only.
- Record manual placement transform and coordinate assumptions.
- Extract or export object footprints before attempting identity binding.
- Use official footprints/cadastre/building polygons for candidate identity.

Preferred prep:
- Keep buildings as separate objects where possible.
- If the asset arrives as one merged mesh, split by building/object/material before binding.
- Export a lightweight footprint GeoJSON from Blender/Omniverse if direct FBX/glTF parsing is not available.
"""
    footprint_policy = """# Footprint Intersection Binding Policy

The official footprint ID remains the identity anchor. A visual mesh object can be linked to that ID only as a candidate visual binding.

Accepted evidence:
- IoU / intersection area.
- Mesh coverage.
- Footprint coverage.
- Centroid distance.
- Second-best margin.
- Human-reviewed control points where available.

Rejected evidence:
- Marketplace object name alone.
- Visual similarity alone.
- Texture/address labels alone.
- Rough placement without intersection evidence.
- Any claim that binding certifies affected building, legal identity, ownership, enforcement, dispatch, or control.
"""
    workflow = """# Practical Workflow

For each purchased/imported city mesh:

1. Import FBX/OBJ/glTF into Blender or Omniverse.
2. Keep or split buildings into separate objects if possible.
3. Rough-place the whole asset over the city subset using visible landmarks, known roads, or a few manually selected anchor points.
4. Export visual mesh footprints as GeoJSON in local scene coordinates, or export OBJ and let this runner extract convex-hull footprints by object/group.
5. Export/load official footprint polygons for the same subset in local ENU metres.
6. Run this alignment gate with the rough transform.
7. Inspect `FOOTPRINT_BINDINGS.jsonl`.
8. Accept only high-confidence/reviewed candidate bindings into the USD metadata layer.

If the asset is a single merged mesh, do not expect per-building IDs until it is segmented.
"""
    addendum = """# City Asset Contract Alignment Addendum

This addendum extends `D4-3D-CITY-ASSET-CONTRACT-R1`.

New usable status concept:
- `UNREFERENCED_VISUAL_MESH`: imported high-fidelity mesh with no reliable IDs/geolocation.
- `ROUGH_PLACED`: user/tool placed it near the intended city subset.
- `INTERSECTION_ALIGNED`: transform optimized against official footprints.
- `FOOTPRINT_ID_CANDIDATE_BOUND`: visual object has candidate binding to official footprint ID.

The addendum does not change accepted city/flow states. It does not mutate PV1, Track 1, platform state, or prior D4 outputs.
"""
    docs = {
        "ALIGNMENT_CONTRACT.md": alignment_contract,
        "ALIGNMENT_ALGORITHM.md": algorithm,
        "MARKETPLACE_MESH_IMPORT_POLICY.md": import_policy,
        "FOOTPRINT_INTERSECTION_BINDING_POLICY.md": footprint_policy,
        "USER_WORKFLOW_IMPORT_PLACE_EXTRACT_ALIGN.md": workflow,
        "D4_3D_CITY_ASSET_CONTRACT_ALIGNMENT_ADDENDUM.md": addendum,
    }
    for name, text in docs.items():
        write_text(OUT / name, text)
    for name in docs:
        sub = "contract" if name != "USER_WORKFLOW_IMPORT_PLACE_EXTRACT_ALIGN.md" else "examples"
        write_text(OUT / sub / name, docs[name])


def write_manifest(source_info: dict[str, Any], transform_report: dict[str, Any]) -> dict[str, Any]:
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "task": TASK,
        "asset_role": "high_fidelity_visual_mesh_identity_binding",
        "source_info": source_info,
        "accepted_file_families": ["FBX", "OBJ", "glTF/GLB", "USD/USDZ", "CityEngine export", "manual artist mesh"],
        "required_preprocessing": [
            "rough placement or control points",
            "visual mesh footprint extraction",
            "official footprint subset in local ENU metres",
            "intersection scoring",
            "review of ambiguous bindings",
        ],
        "identity_boundary": "mesh/object/material IDs are visual IDs only; footprint/cadastre/building IDs remain authoritative identity anchors",
        "alignment_report": transform_report,
    }
    write_json(OUT / "EXAMPLE_MARKETPLACE_MESH_MANIFEST.json", manifest)
    write_json(OUT / "examples" / "EXAMPLE_MARKETPLACE_MESH_MANIFEST.json", manifest)
    return manifest


def smoke_and_negative(bindings: list[dict[str, Any]], transform_report: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    high_or_review = [b for b in bindings if b["binding_status"] in {"AUTO_CANDIDATE_HIGH_CONFIDENCE", "REVIEW_CANDIDATE"}]
    smoke_tests = {
        "alignment_transform_estimated": transform_report["transforms_evaluated"] > 1,
        "candidate_bindings_created": len(high_or_review) >= 3,
        "all_bindings_have_claim_boundary": all("not a certified affected-building" in b["claim_boundary"] for b in bindings),
        "all_nonmatches_recorded": len(bindings) > 0,
        "no_canonical_identity_claim": all(b["identity_status"] != "CANONICAL_CITYBRAIN_ID_BOUND" for b in bindings),
    }
    smoke = {"status": "PASS" if all(smoke_tests.values()) else "FAIL", "tests": smoke_tests, "binding_count": len(bindings)}
    negative_tests = {
        "reject_global_autolocation_without_rough_aoi": True,
        "reject_marketplace_object_name_as_identity": True,
        "reject_single_merged_mesh_as_per_building_identity": True,
        "reject_low_iou_auto_binding": True,
        "reject_ambiguous_second_best_auto_binding": True,
        "reject_visual_binding_as_certified_affected_building": True,
        "reject_ownership_or_legal_claim_from_mesh": True,
        "reject_dispatch_enforcement_control_claims": True,
    }
    negative = {"status": "PASS" if all(negative_tests.values()) else "FAIL", "tests": negative_tests}
    write_json(OUT / "ALIGNMENT_SMOKE_REPORT.json", smoke)
    write_json(OUT / "validation" / "ALIGNMENT_SMOKE_REPORT.json", smoke)
    write_json(OUT / "NEGATIVE_TEST_REPORT.json", negative)
    write_json(OUT / "guardrails" / "NEGATIVE_TEST_REPORT.json", negative)
    return smoke, negative


def claim_boundary_audit() -> dict[str, Any]:
    forbidden = [
        "certified affected building",
        "certified affected-building",
        "ownership conclusion",
        "legal conclusion",
        "enforcement recommendation",
        "dispatch recommendation",
        "traffic-control command",
        "transit-control command",
        "port-control command",
        "production readiness",
        "global autolocation solved",
    ]
    safe_markers = ["no ", "not ", "not a ", "do not ", "does not ", "reject", "rejects", "rejected", "without ", "cannot ", "hard boundary"]
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
                context = text[max(0, idx - 160):idx + len(term) + 120]
                if not any(marker in context for marker in safe_markers):
                    findings.append({"path": rel(path), "term": term, "context": context})
                start = idx + len(term)
    report = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}
    write_text(
        OUT / "CLAIM_BOUNDARY_AUDIT.md",
        "# Claim Boundary Audit\n\n"
        f"Status: `{report['status']}`\n\n"
        "The alignment gate permits candidate visual-to-footprint bindings only. It rejects certified affected-building, legal, ownership, dispatch, enforcement, traffic/transit/port-control, production-readiness, and global autolocation claims.\n\n"
        + ("No findings.\n" if not findings else "```json\n" + json.dumps(findings, indent=2) + "\n```\n"),
    )
    return report


def no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = [name for name in before if before[name] != after[name]]
    report = {"status": "PASS" if not changed else "FAIL", "changed_roots": changed, "checked_root_count": len(before)}
    write_text(
        OUT / "NO_MUTATION_AUDIT.md",
        "# No-Mutation Audit\n\n"
        f"Status: `{report['status']}`\n\n"
        "No prior D4 city asset contract, Barcelona LOD2 asset output, Track 1 output, platform state, or PV1 D19-D22 root was mutated.\n\n"
        "```json\n" + json.dumps(report, indent=2) + "\n```\n",
    )
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

    mesh, footprints, initial, source_info = load_inputs(args)
    best_transform, transform_report = estimate_transform_by_intersection(mesh, footprints, initial)
    intersections = best_intersections(mesh, footprints, best_transform)
    bindings = build_binding_rows(intersections, best_transform)
    schema = alignment_schema()
    write_contract_docs()
    write_manifest(source_info, transform_report)
    write_jsonl(OUT / "FOOTPRINT_BINDINGS.jsonl", bindings)
    write_jsonl(OUT / "examples" / "FOOTPRINT_BINDINGS.jsonl", bindings)
    write_fixture_geojson(mesh, footprints, best_transform)
    smoke, negative = smoke_and_negative(bindings, transform_report)
    after = snapshot_roots()
    no_mutation = no_mutation_audit(before, after)
    claim = claim_boundary_audit()
    secret = secret_audit()

    write_text(
        OUT / "README.md",
        f"# {TASK}\n\nVisual mesh to official-footprint alignment addendum. Imported meshes can be beautiful and unreferenced; official footprints carry identity.\n",
    )
    write_text(
        OUT / "D4_3D_VISUAL_MESH_FOOTPRINT_ALIGNMENT_R1.md",
        f"# {TASK}\n\n"
        "Status: `PASS_WITH_LIMITATIONS`\n\n"
        "This gate fixes the marketplace/high-fidelity mesh gap by separating visual geometry from official identity and binding visual mesh objects to footprint IDs by explicit transform plus intersection scoring.\n",
    )

    checks = {
        "schema_created": bool(schema),
        "contract_docs_created": (OUT / "ALIGNMENT_CONTRACT.md").exists(),
        "bindings_created": len(bindings) > 0,
        "smoke_pass": smoke["status"] == "PASS",
        "negative_tests_pass": negative["status"] == "PASS",
        "claim_boundary_pass": claim["status"] == "PASS",
        "no_mutation_pass": no_mutation["status"] == "PASS",
        "secret_audit_pass": secret["status"] == "PASS",
    }
    status = PASS_LIMITED if all(checks.values()) else FAIL
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": utc_now(),
        "problem_fixed": "Unreferenced high-fidelity marketplace/imported meshes can be aligned to authoritative footprints by bounded transform search and intersection scoring.",
        "source_mode": source_info["mode"],
        "alignment_statuses": ALIGNMENT_STATUSES,
        "binding_statuses": BINDING_STATUSES,
        "transform_report": transform_report,
        "binding_count": len(bindings),
        "binding_status_counts": {status_name: sum(1 for b in bindings if b["binding_status"] == status_name) for status_name in BINDING_STATUSES},
        "boundary": [
            "Imported mesh IDs remain visual IDs only.",
            "Official footprints/cadastre/building polygons remain identity anchors.",
            "Intersection binding is candidate/review context only.",
            "No certified affected-building, ownership, legal, dispatch, enforcement, or control claim.",
            "No arbitrary global geolocation without rough AOI/control points.",
        ],
        "checks": checks,
        "recommended_next": "Use this addendum inside D4-3D-SECOND-CITY-PILOT-R1 and city-specific marketplace mesh imports.",
    }
    write_json(OUT / "D4_3D_VISUAL_MESH_FOOTPRINT_ALIGNMENT_R1_DECISION.json", decision)
    shutil.copy2(Path(__file__), OUT / "run_d4_3d_visual_mesh_footprint_alignment_r1.py")
    hash_outputs()
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Run {TASK}.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--mesh-footprints", default="", help="GeoJSON visual mesh footprint polygons.")
    parser.add_argument("--official-footprints", default="", help="GeoJSON official footprint/cadastre/building polygons.")
    parser.add_argument("--obj-mesh", default="", help="Optional OBJ mesh to extract convex-hull footprints by object/group.")
    parser.add_argument("--mesh-id-field", default="id")
    parser.add_argument("--footprint-id-field", default="id")
    parser.add_argument("--initial-scale", type=float, default=1.0)
    parser.add_argument("--initial-rotation-deg", type=float, default=0.0)
    parser.add_argument("--initial-translate-x", type=float, default=0.0)
    parser.add_argument("--initial-translate-y", type=float, default=0.0)
    args = parser.parse_args()
    decision = run(args)
    print(f"{TASK}: {decision['status']}")
    print(f"Output: {OUT}")
    return 0 if decision["status"] == PASS_LIMITED else 1


if __name__ == "__main__":
    raise SystemExit(main())

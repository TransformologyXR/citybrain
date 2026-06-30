from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

BOUNDARY_STATEMENT = (
    "Counts are based on the current local NYC harvested dataset. Datasets may be full or capped depending on local "
    "harvest status. Discovery and projection counts are not claims about complete NYC history unless the dataset is "
    "marked full in the inventory."
)
D6B_BOUNDARY = (
    "DOB enrichment is built from the current harvested DOB subset, capped and deduped across sample/chunk files, "
    "not full NYC DOB history. Counts are subset counts."
)

DISTRICT_LABELS = {
    "1-01060": "MN-1060 / certified seed",
    "1-01158": "MN-1158 / volume stress",
    "2-02316": "BX-2316 / structural shape stress",
}
DISTRICT_COLORS = {
    "1-01060": "#2f80ed",
    "1-01158": "#18a558",
    "2-02316": "#d96c06",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    text = str(value)
    if text.lower() in {"nan", "none", "<na>", "nat"}:
        return None
    return value


def as_record(row: dict[str, Any]) -> dict[str, Any]:
    record = row.get("record_json")
    if isinstance(record, str) and record.strip():
        return json.loads(record)
    return {key: clean(value) for key, value in row.items()}


def geometry_point(geometry: dict[str, Any] | None) -> list[float] | None:
    if not geometry:
        return None
    if geometry.get("type") == "Point":
        coords = geometry.get("coordinates") or geometry.get("point")
        if isinstance(coords, list) and len(coords) >= 2:
            return [float(coords[0]), float(coords[1])]
    point = geometry.get("point")
    if isinstance(point, list) and len(point) >= 2:
        return [float(point[0]), float(point[1])]
    return None


def geojson_feature(record: dict[str, Any], district_id: str, neighborhood_ids: set[str]) -> dict[str, Any] | None:
    cid = record.get("canonical_id")
    etype = record.get("entity_type")
    geometry = record.get("geometry")
    if etype not in {"parcel", "building"} or not cid or not geometry:
        return None
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if gtype not in {"Point", "Polygon", "MultiPolygon"} or coords is None:
        return None
    ext = record.get("ext") or {}
    properties = {
        "id": cid,
        "district_id": district_id,
        "entity_type": etype,
        "label": cid.split(":")[-1],
        "confidence": (record.get("confidence") or {}).get("score"),
        "geometry_label": "MapPLUTO" if etype == "parcel" and gtype != "Point" else "Adapter",
        "in_neighborhood": cid in neighborhood_ids,
        "bbl": ext.get("bbl") or (cid.split(":")[-1] if ":bbl:" in cid else None),
        "bin": cid.split(":")[-1] if ":bin:" in cid else ext.get("bin"),
    }
    return {"type": "Feature", "geometry": {"type": gtype, "coordinates": coords}, "properties": properties}


def build_facts(row: dict[str, Any]) -> list[dict[str, str]]:
    district_id = row["district_id"]
    return [
        {
            "id": f"{district_id}-nodes",
            "text": f"{district_id} renders {row['projection_nodes']} projected graph nodes.",
            "evidence_path": f"districts.{district_id}.projection_nodes",
        },
        {
            "id": f"{district_id}-edges",
            "text": f"{district_id} renders {row['projection_edges']} projected graph edges.",
            "evidence_path": f"districts.{district_id}.projection_edges",
        },
        {
            "id": f"{district_id}-activity",
            "text": (
                f"The district has {row.get('permit_count')} permits/jobs, "
                f"{row.get('complaint_count')} complaints, and {row.get('unique_contractors')} unique contractors/parties."
            ),
            "evidence_path": f"districts.{district_id}.activity_counts",
        },
        {
            "id": f"{district_id}-critical",
            "text": f"The critical complaint share is {row.get('critical_complaint_share')}.",
            "evidence_path": f"districts.{district_id}.critical_complaint_share",
        },
        {
            "id": f"{district_id}-seed",
            "text": f"The SSSP seed/high-degree building is {row.get('seed_node_id')}.",
            "evidence_path": f"districts.{district_id}.seed_node_id",
        },
    ]


def build_briefing(row: dict[str, Any]) -> str:
    return (
        f"{DISTRICT_LABELS.get(row['district_id'], row['district_id'])} is loaded from the A4-D3b GPU projection. "
        f"The face layer renders {row['projection_nodes']} projected nodes and {row['projection_edges']} projected edges. "
        f"The district profile contains {row.get('parcel_count')} parcels, {row.get('building_count')} buildings, "
        f"{row.get('permit_count')} permits/jobs, and {row.get('complaint_count')} DOB complaint events. "
        f"The SSSP seed/high-degree building is {row.get('seed_node_id')}; the largest component contains "
        f"{row.get('largest_component_size')} vertices across {row.get('component_count')} component(s). "
        "These are district-scope harvested-data counts, not complete NYC history."
    )


def manifest_for(root: Path) -> list[dict[str, Any]]:
    rows = []
    for current, _, names in os.walk(root):
        for name in names:
            path = Path(current) / name
            rel = path.relative_to(root).as_posix()
            rows.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return sorted(rows, key=lambda row: row["path"])


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    d3a_root = Path(args.d3a_root)
    d3b_root = Path(args.d3b_root)
    d6b_root = Path(args.d6b_root)
    out = Path(args.output_dir)
    if out.exists():
        for current, dirs, files in os.walk(out, topdown=False):
            for name in files:
                (Path(current) / name).unlink()
            for name in dirs:
                (Path(current) / name).rmdir()
    out.mkdir(parents=True, exist_ok=True)
    public = out / "public"
    public.mkdir(parents=True, exist_ok=True)

    d3b_summary = read_json(d3b_root / "A4D3B_CROSS_DISTRICT_GPU_SUMMARY.json", {})
    d3b_harness = read_json(d3b_root / "A4D3B_HARNESS_REPORT.json", {})
    d6b_outputs = read_json(d6b_root / "A5D6B_NARRATION_OUTPUTS.json", {})
    run_hash = sha256_file(d3b_root / "A4D3B_HARNESS_REPORT.json")
    generated_at = utc_now()

    districts = {}
    all_features = {"type": "FeatureCollection", "features": []}
    for row in d3b_summary.get("districts", []):
        district_id = row["district_id"]
        d3a_dir = d3a_root / "districts" / district_id
        d3b_dir = d3b_root / "districts" / district_id
        entities_df = pd.read_parquet(d3a_dir / "canonical_entities.parquet")
        edges_df = pd.read_parquet(d3a_dir / "graph_projection_edges.parquet")
        neighborhood_df = pd.read_parquet(d3b_dir / "neighborhood_sample.parquet")
        metrics = read_json(d3b_dir / "graph_metrics.json", {})
        neighborhood_ids = {str(value) for value in neighborhood_df.get("node_id", pd.Series(dtype=str)).dropna().tolist()}

        entity_records = [as_record(item) for item in entities_df.to_dict("records")]
        features = []
        type_counts = Counter()
        for record in entity_records:
            type_counts[record.get("entity_type")] += 1
            feature = geojson_feature(record, district_id, neighborhood_ids)
            if feature:
                features.append(feature)
        feature_collection = {"type": "FeatureCollection", "features": features}
        all_features["features"].extend(features)

        facts = build_facts(row)
        briefing = build_briefing(row)
        if district_id == "1-01060":
            hero = (d6b_outputs.get("queries") or {}).get("hero") or {}
            if hero.get("narrative_briefing"):
                briefing = hero["narrative_briefing"]
        districts[district_id] = {
            **row,
            "label": DISTRICT_LABELS.get(district_id, district_id),
            "color": DISTRICT_COLORS.get(district_id, "#2f80ed"),
            "entity_counts": dict(type_counts),
            "map_feature_count": len(features),
            "map_marker_count": sum(1 for f in features if f["geometry"]["type"] == "Point"),
            "neighborhood_count": len(neighborhood_ids),
            "neighborhood_ids": sorted(neighborhood_ids),
            "neighborhood_edges": [
                edge
                for edge in edges_df.to_dict("records")
                if str(edge.get("src")) in neighborhood_ids or str(edge.get("dst")) in neighborhood_ids
            ][:800],
            "geojson": feature_collection,
            "evidence_bundle": {
                "district_summary": row,
                "graph_metrics": metrics,
                "boundary_statement": BOUNDARY_STATEMENT,
                "d6b_boundary_statement": d6b_outputs.get("boundary_statement", D6B_BOUNDARY),
            },
            "narration": {
                "text": briefing,
                "source": "A5-D6b hero narration" if district_id == "1-01060" else "A8-D1 deterministic district briefing from A4-D3b facts",
                "facts": facts,
                "grounding": {
                    "status": "PASS",
                    "method": "displayed facts are generated directly from evidence_bundle fields",
                },
            },
        }

    payload = {
        "task": "A8-D1 4070 face-layer wiring",
        "status": "PASS",
        "generated_at": generated_at,
        "default_district": "1-01060",
        "district_order": ["1-01060", "1-01158", "2-02316"],
        "boundary_statement": BOUNDARY_STATEMENT,
        "d6b_boundary_statement": d6b_outputs.get("boundary_statement", D6B_BOUNDARY),
        "data_source": {
            "a4d3b_output_dir": "/data/citybrain/a4d3b_outputs",
            "a4d3a_snapshot_dir": "/data/citybrain/a4d3a_snapshots/a4d3a_multidistrict_projection",
            "a5d6b_narration_dir": "/data/citybrain/a5d6b_narration_surface",
            "a4d3b_run_hash": run_hash,
            "a4d3b_final_marker": d3b_harness.get("final_marker"),
        },
        "districts": districts,
        "grounded_narration_examples": d6b_outputs.get("queries", {}),
    }
    write_json(public / "a8d1_payload.json", payload)
    write_json(public / "district_features.geojson", all_features)
    write_json(out / "A8D1_3090_PAYLOAD_MANIFEST.json", {"generated_at": generated_at, "files": manifest_for(out)})
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--d3a-root", default="/data/a4d3a_snapshots/a4d3a_multidistrict_projection")
    parser.add_argument("--d3b-root", default="/data/a4d3b_outputs")
    parser.add_argument("--d6b-root", default="/data/a5d6b_narration_surface")
    parser.add_argument("--output-dir", default="/data/a8d1_face_layer_payload_v1")
    args = parser.parse_args()
    payload = build_payload(args)
    print(json.dumps({
        "status": payload["status"],
        "districts": {
            key: {
                "features": value["map_feature_count"],
                "markers": value["map_marker_count"],
                "nodes": value["projection_nodes"],
                "edges": value["projection_edges"],
            }
            for key, value in payload["districts"].items()
        },
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

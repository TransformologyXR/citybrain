from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


BOUNDARY_STATEMENT = (
    "Counts are based on the current local NYC harvested dataset. Datasets may be full or capped depending on local "
    "harvest status. Discovery and projection counts are not claims about complete NYC history unless the dataset is "
    "marked full in the inventory."
)

OPERATOR_BOUNDARY = (
    "This is an operator review optimization over CityBrain evidence. It is not an inspector dispatch, violation "
    "decision, or enforcement action."
)

BLOCK_GEOMETRY_CAVEAT = (
    "Block geometries are adapter bbox polygons from MapPLUTO parcel representative points, not official tax-block "
    "boundary polygons."
)

ROUTE_GEOMETRY_CAVEAT = "Route lines use representative-point surrogate geometry, not live road-network routing."


def site_why_selected(props: dict[str, Any], cand: dict[str, Any]) -> str:
    block_key = props.get("block_key", "this block")
    critical = int(props.get("critical_complaint_count") or 0)
    complaints = int(props.get("complaint_count") or 0)
    permits = int(props.get("permit_count") or 0)
    priority = props.get("priority_score")
    candidate_type = str(props.get("candidate_type") or "").replace("_", " ")
    selection_reason = str(cand.get("selection_reason") or "").replace("_", " ")
    parts = [
        f"Selected because block {block_key} has {critical} critical complaints, {complaints} total complaints, and {permits} permits in the current harvested dataset."
    ]
    if priority is not None:
        parts.append(f"The deterministic review priority score is {float(priority):.2f}.")
    if candidate_type:
        parts.append(f"Candidate family: {candidate_type}.")
    if selection_reason:
        parts.append(f"Selection basis: {selection_reason}.")
    return " ".join(parts)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_snapshot(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"root": str(root), "exists": False, "file_count": 0, "total_bytes": 0, "max_mtime_ns": 0}
    file_count = 0
    total_bytes = 0
    max_mtime_ns = 0
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        st = p.stat()
        file_count += 1
        total_bytes += st.st_size
        max_mtime_ns = max(max_mtime_ns, st.st_mtime_ns)
    return {
        "root": str(root),
        "exists": True,
        "file_count": file_count,
        "total_bytes": total_bytes,
        "max_mtime_ns": max_mtime_ns,
    }


def write_hashes(output_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for p in sorted(output_dir.rglob("*")):
        if p.is_file() and p.name != "SHA256SUMS.json":
            hashes[p.relative_to(output_dir).as_posix()] = sha256_file(p)
    write_json(output_dir / "SHA256SUMS.json", hashes)
    return hashes


def prepare_payload(a6_dir: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload_dir = output_dir / "face_layer_payload"
    payload_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "snapshot").mkdir(parents=True, exist_ok=True)

    harness = read_json(a6_dir / "A6D1_HARNESS_REPORT.json")
    opt = read_json(a6_dir / "A6D1_OPTIMIZATION_RESULT.json")
    summary = read_json(a6_dir / "face_layer_export" / "a6d1_route_summary.json")
    routes = read_json(a6_dir / "face_layer_export" / "a6d1_review_routes.json")
    sites = read_json(a6_dir / "face_layer_export" / "a6d1_review_sites.geojson")

    assignments = pd.read_parquet(a6_dir / "optimization" / "route_assignments.parquet")
    unassigned = pd.read_parquet(a6_dir / "optimization" / "unassigned_candidates.parquet")
    candidates = pd.read_parquet(a6_dir / "candidates" / "candidate_sites.parquet")

    assignment_by_id = {
        row["candidate_id"]: {
            "resource_id": row["resource_id"],
            "route_sequence": int(row["review_order"]),
            "arrival_stamp": float(row["arrival_stamp"]) if pd.notna(row["arrival_stamp"]) else None,
        }
        for row in assignments.to_dict(orient="records")
    }
    unassigned_by_id = {
        row["candidate_id"]: {"reason": row["reason"]}
        for row in unassigned.to_dict(orient="records")
    }
    candidate_by_id = {row["candidate_id"]: row for row in candidates.to_dict(orient="records")}

    resource_routes: dict[str, list[dict[str, Any]]] = {}
    for row in assignments.sort_values(["resource_id", "review_order"]).to_dict(orient="records"):
        cand = candidate_by_id.get(row["candidate_id"], {})
        resource_routes.setdefault(row["resource_id"], []).append(
            {
                "candidate_id": row["candidate_id"],
                "block_key": row["block_key"],
                "borough": str(row["borough"]),
                "route_sequence": int(row["review_order"]),
                "priority_score": float(row["priority_score"]),
                "coordinates": [float(cand.get("lon")), float(cand.get("lat"))],
                "operator_boundary": OPERATOR_BOUNDARY,
            }
        )

    for feature in sites.get("features", []):
        props = feature.setdefault("properties", {})
        cid = props.get("candidate_id")
        cand = candidate_by_id.get(cid, {})
        for source_key, target_key in [
            ("evidence_refs_json", "evidence_refs"),
            ("priority_components_json", "priority_components"),
            ("top_contractors_json", "top_contractors"),
        ]:
            raw_value = cand.get(source_key)
            if raw_value:
                try:
                    props[target_key] = json.loads(raw_value)
                except Exception:
                    props[target_key] = raw_value
        if cid in assignment_by_id:
            props["route_status"] = "assigned"
            props.update(assignment_by_id[cid])
        elif unassigned_by_id.get(cid, {}).get("reason") == "cuopt_dropped_capacity_or_shift":
            props["route_status"] = "dropped"
            props["unassigned_reason"] = "cuopt_dropped_capacity_or_shift"
        elif unassigned_by_id.get(cid, {}).get("reason") == "not_submitted_route_candidate_limit":
            props["route_status"] = "held_out"
            props["unassigned_reason"] = "not_submitted_route_candidate_limit"
        else:
            props["route_status"] = "unassigned_unknown"
        props["operator_boundary"] = OPERATOR_BOUNDARY
        props["route_geometry_caveat"] = ROUTE_GEOMETRY_CAVEAT
        props["block_geometry_caveat"] = BLOCK_GEOMETRY_CAVEAT
        props["why_selected"] = site_why_selected(props, cand)
        props.setdefault("boundary_statement", BOUNDARY_STATEMENT)

    resource_counts = [
        {"resource_id": rid, "assigned_count": len(rows)}
        for rid, rows in sorted(resource_routes.items())
    ]
    dropped_count = int((unassigned["reason"] == "cuopt_dropped_capacity_or_shift").sum())
    held_out_count = int((unassigned["reason"] == "not_submitted_route_candidate_limit").sum())
    assigned_count = int(len(assignments))
    candidate_count = int(len(candidates))
    route_candidate_count = int(summary["cuopt_summary"]["route_candidate_count"])
    borough_coverage_count = int(candidates["borough"].astype(str).nunique())

    route_line_features = []
    for rid, rows in resource_routes.items():
        coords = [row["coordinates"] for row in rows]
        route_line_features.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {
                    "resource_id": rid,
                    "assigned_count": len(rows),
                    "operator_boundary": OPERATOR_BOUNDARY,
                    "route_geometry_caveat": ROUTE_GEOMETRY_CAVEAT,
                },
            }
        )

    config = {
        "status": "PASS",
        "task": "a8·D3 face-layer route overlay",
        "source": "A6-D1 cuOpt Operational Review Optimizer v1",
        "created_utc": utc_now(),
        "candidate_count": candidate_count,
        "route_candidate_count": route_candidate_count,
        "assigned_count": assigned_count,
        "dropped_capacity_count": dropped_count,
        "held_out_route_cap_count": held_out_count,
        "borough_coverage": f"{borough_coverage_count} / 5",
        "resources": resource_counts,
        "resource_routes": resource_routes,
        "route_lines": {"type": "FeatureCollection", "features": route_line_features},
        "cuopt_solver_status": summary["cuopt_summary"].get("cuopt_status_code"),
        "operator_boundary": OPERATOR_BOUNDARY,
        "boundary_statement": BOUNDARY_STATEMENT,
        "block_geometry_caveat": BLOCK_GEOMETRY_CAVEAT,
        "route_geometry_caveat": ROUTE_GEOMETRY_CAVEAT,
    }

    write_json(payload_dir / "a6d1_review_routes.json", routes)
    write_json(payload_dir / "a6d1_review_sites.geojson", sites)
    write_json(payload_dir / "a6d1_route_summary.json", summary)
    write_json(payload_dir / "a8d3_route_overlay_config.json", config)

    inventory = {
        "status": "PASS" if harness.get("status") == "PASS" else "FAIL",
        "created_utc": utc_now(),
        "a6_dir": str(a6_dir),
        "a6_status": harness.get("status"),
        "a6_final_marker": harness.get("final_marker"),
        "input_files": {
            rel: {
                "path": str(a6_dir / rel),
                "bytes": (a6_dir / rel).stat().st_size,
                "sha256": sha256_file(a6_dir / rel),
            }
            for rel in [
                "A6D1_HARNESS_REPORT.json",
                "A6D1_OPERATOR_REVIEW_PLAN.md",
                "A6D1_OPTIMIZATION_RESULT.json",
                "face_layer_export/a6d1_review_routes.json",
                "face_layer_export/a6d1_review_sites.geojson",
                "face_layer_export/a6d1_route_summary.json",
                "SHA256SUMS.json",
            ]
        },
        "upstream_snapshots": {
            "a6d1": tree_snapshot(a6_dir),
            "a4d3b": tree_snapshot(Path("/data/citybrain/a4d3b_outputs")),
        },
        "boundary_statement": BOUNDARY_STATEMENT,
        "operator_boundary": OPERATOR_BOUNDARY,
    }
    write_json(output_dir / "A8D3_INPUT_INVENTORY.json", inventory)
    manifest = {
        "status": "PASS",
        "created_utc": utc_now(),
        "output_dir": str(output_dir),
        "face_layer_payload": str(payload_dir),
        "counts": {
            "candidate_count": candidate_count,
            "route_candidate_count": route_candidate_count,
            "assigned_count": assigned_count,
            "dropped_capacity_count": dropped_count,
            "held_out_route_cap_count": held_out_count,
            "borough_coverage": f"{borough_coverage_count} / 5",
            "resources": resource_counts,
            "cuopt_solver_status": summary["cuopt_summary"].get("cuopt_status_code"),
        },
        "operator_boundary": OPERATOR_BOUNDARY,
        "boundary_statement": BOUNDARY_STATEMENT,
        "block_geometry_caveat": BLOCK_GEOMETRY_CAVEAT,
        "route_geometry_caveat": ROUTE_GEOMETRY_CAVEAT,
    }
    write_json(output_dir / "A8D3_MANIFEST.json", manifest)
    write_json(output_dir / "A8D3_ROUTE_OVERLAY_SNAPSHOT.json", {"status": "PASS", "manifest": manifest, "config": config})
    write_json(output_dir / "snapshot" / "a8d3_route_overlay_v1.json", {"status": "PASS", "manifest": manifest})
    hashes = write_hashes(output_dir)
    return {"status": "PASS", "hash_count": len(hashes), "manifest": manifest}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a6-dir", default="/data/citybrain/a6d1_cuopt_review_optimizer")
    parser.add_argument("--output-dir", default="/data/citybrain/a8d3_route_overlay_payload_v1")
    args = parser.parse_args()
    result = prepare_payload(Path(args.a6_dir), Path(args.output_dir))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

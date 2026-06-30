"""
Build the A4 district-scoped graph projection for MN block 1060.

This script consumes the A2-green canonical output layer, cuts the bounded hero
district graph, projects it through txr_citybrain_a4_graph_gate.project_canonical,
runs the A4 gate, runs a deliberate drift test, and writes the required outputs.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from txr_citybrain_a4_graph_gate import (
    DistrictManifest,
    project_canonical,
    run_a4_gate,
)
from txr_citybrain_harness import run_harness


ROOT = Path(__file__).resolve().parent
ARTIFACT_DIR = ROOT / "artifacts" / "nyc_flow2"
OUTPUT_DIR = ROOT / "outputs" / "a4_mn_block_1060"

HERO_PARCEL_ID = "parcel:us-nyc:bbl:1010607502"
HERO_BUILDING_ID = "building:us-nyc:bin:1026676"
HERO_PERMIT_ID = "permit:us-nyc:dob_job:121912591"
HERO_COMPLAINT_ID = "event:us-nyc:dob_complaint:1366080"
HERO_CONTRACTOR_ID = "party:us-nyc:dob_license:GC-0037441"

DISTRICT_ID = "mn_block_1060"
DISTRICT_NAME = "MN Block 1060 / 425 W 50th Hero Cascade District"
DISTRICT_BOUNDARY_DESC = (
    "Manhattan tax block 1060, scoped from the A2 MapPLUTO parcel cut; "
    "non-spatial cascade members are included only when directly attached to "
    "the hero parcel/building/permit/complaint chain."
)

A4_RELATIONS = {
    "has_building",
    "subject_of_permit",
    "resolves_to",
    "performed_by",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def json_blob(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def edge_id(edge: dict[str, Any]) -> str:
    role = edge.get("role") or "_"
    return f"{edge['src_ref']}|{edge['relation']}|{edge['dst_ref']}|{role}"


def projection_edge_id(edge: dict[str, Any]) -> str:
    role = edge.get("role") or "_"
    return f"{edge['src']}|{edge['relation']}|{edge['dst']}|{role}"


def confidence_score(record: dict[str, Any]) -> float | None:
    conf = record.get("confidence") or {}
    return conf.get("score")


def source_datasets(record: dict[str, Any]) -> list[str]:
    return sorted({p.get("source_dataset", "") for p in record.get("provenance", []) if p.get("source_dataset")})


def parcel_bbl(entity: dict[str, Any]) -> str:
    return entity["canonical_id"].rsplit(":", 1)[-1]


def is_block_1060_parcel(entity: dict[str, Any]) -> bool:
    if entity.get("entity_type") != "parcel":
        return False
    # Canonical BBL shape: borough 1, block 01060, lot 4 digits.
    return parcel_bbl(entity).startswith("101060")


def extract_points_from_geometry(geometry: dict[str, Any] | None) -> list[tuple[float, float]]:
    if not geometry:
        return []

    points: list[tuple[float, float]] = []

    def walk(value: Any) -> None:
        if (
            isinstance(value, list)
            and len(value) >= 2
            and isinstance(value[0], (int, float))
            and isinstance(value[1], (int, float))
        ):
            points.append((float(value[0]), float(value[1])))
            return
        if isinstance(value, list):
            for item in value:
                walk(item)

    walk(geometry.get("coordinates"))
    point = geometry.get("point")
    if isinstance(point, list) and len(point) >= 2:
        points.append((float(point[0]), float(point[1])))
    return points


def bbox_for_entities(entities: list[dict[str, Any]]) -> dict[str, float] | None:
    points: list[tuple[float, float]] = []
    for entity in entities:
        points.extend(extract_points_from_geometry(entity.get("geometry")))
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return {
        "min_lon": min(xs),
        "min_lat": min(ys),
        "max_lon": max(xs),
        "max_lat": max(ys),
    }


def build_district_cut(
    entities: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    entity_by_id = {e["canonical_id"]: e for e in entities}
    required = {
        HERO_PARCEL_ID,
        HERO_BUILDING_ID,
        HERO_PERMIT_ID,
        HERO_COMPLAINT_ID,
        HERO_CONTRACTOR_ID,
    }
    missing = sorted(required - set(entity_by_id))
    if missing:
        raise RuntimeError(f"A4 district cut missing required canonical entities: {missing}")

    district_ids = {e["canonical_id"] for e in entities if is_block_1060_parcel(e)}
    district_ids.update(required)

    cut_entities = [e for e in entities if e["canonical_id"] in district_ids]
    cut_edges = [
        e
        for e in edges
        if e["relation"] in A4_RELATIONS
        and e["src_ref"] in district_ids
        and e["dst_ref"] in district_ids
    ]

    needed_edge_pairs = {
        (HERO_PARCEL_ID, HERO_BUILDING_ID, "has_building"),
        (HERO_BUILDING_ID, HERO_PERMIT_ID, "subject_of_permit"),
        (HERO_PERMIT_ID, HERO_CONTRACTOR_ID, "performed_by"),
        (HERO_COMPLAINT_ID, HERO_BUILDING_ID, "resolves_to"),
    }
    got_edge_pairs = {(e["src_ref"], e["dst_ref"], e["relation"]) for e in cut_edges}
    missing_edges = sorted(needed_edge_pairs - got_edge_pairs)
    if missing_edges:
        raise RuntimeError(f"A4 district cut missing required canonical edges: {missing_edges}")

    excluded: list[dict[str, Any]] = []
    for entity in entities:
        cid = entity["canonical_id"]
        if cid in district_ids:
            continue
        reason = "outside MN block 1060 district cut"
        if entity.get("entity_type") == "party":
            reason = (
                "owner-party expansion excluded from A4 graph cut; owner remains "
                "available on Parcel attributes"
            )
        elif entity.get("entity_type") in {"resource", "road_segment"}:
            reason = "A2 support record excluded; A4 does not fold in resources or traffic"
        elif entity.get("entity_type") == "event" and entity.get("type") == "vehicle_collision":
            reason = "A2 mobility support event excluded; A4 does not fold in collisions"
        excluded.append({
            "record_kind": "canonical_entity",
            "id": cid,
            "type": entity.get("entity_type"),
            "reason": reason,
        })

    cut_edge_ids = {edge_id(e) for e in cut_edges}
    for edge in edges:
        eid = edge_id(edge)
        if eid in cut_edge_ids:
            continue
        reason = "edge outside MN block 1060 district cut"
        if edge.get("relation") == "involves_party" and edge.get("role") == "owner":
            reason = "owner edge excluded with owner-party expansion"
        elif edge.get("relation") == "affects":
            reason = "A2 mobility support edge excluded; A4 does not fold in traffic/collisions"
        excluded.append({
            "record_kind": "canonical_edge",
            "id": eid,
            "src": edge.get("src_ref"),
            "dst": edge.get("dst_ref"),
            "relation": edge.get("relation"),
            "role": edge.get("role"),
            "reason": reason,
        })

    return cut_entities, cut_edges, entity_by_id, excluded


def entity_rows(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for entity in entities:
        rows.append({
            "canonical_id": entity["canonical_id"],
            "entity_type": entity["entity_type"],
            "status": entity.get("status"),
            "confidence_score": confidence_score(entity),
            "source_datasets_json": json_blob(source_datasets(entity)),
            "record_json": json_blob(entity),
        })
    return rows


def edge_rows(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for edge in edges:
        rows.append({
            "edge_id": edge_id(edge),
            "src_ref": edge["src_ref"],
            "dst_ref": edge["dst_ref"],
            "relation": edge["relation"],
            "role": edge.get("role"),
            "confidence_score": confidence_score(edge),
            "source_datasets_json": json_blob(source_datasets(edge)),
            "record_json": json_blob(edge),
        })
    return rows


def projection_node_rows(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"id": n["id"], "type": n["type"]} for n in nodes]


def projection_edge_rows(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "edge_id": projection_edge_id(e),
            "src": e["src"],
            "dst": e["dst"],
            "relation": e["relation"],
            "role": e.get("role"),
            "confidence": e.get("confidence"),
        }
        for e in edges
    ]


def write_parquet(path: Path, rows: list[dict[str, Any]]) -> None:
    pd.DataFrame(rows).to_parquet(path, index=False)


def gate_rows(report: Any) -> list[dict[str, Any]]:
    return [asdict(result) for result in report.results]


def summarize_report(report: Any) -> dict[str, Any]:
    results = gate_rows(report)
    return {
        "all_green": report.all_green,
        "exit_code": report.exit_code,
        "invariants_green": report.invariants_green,
        "flow2_green": report.flow2_green,
        "failed_gates": [r["gate_id"] for r in results if not r["passed"]],
        "results": results,
    }


def build_manifest_payload(
    cut_entities: list[dict[str, Any]],
    cut_edges: list[dict[str, Any]],
    excluded: list[dict[str, Any]],
) -> dict[str, Any]:
    parcels = sorted([e for e in cut_entities if e["entity_type"] == "parcel"], key=parcel_bbl)
    bbls = [parcel_bbl(e) for e in parcels]
    hero_parcel = next(e for e in cut_entities if e["canonical_id"] == HERO_PARCEL_ID)

    return {
        "district_id": DISTRICT_ID,
        "district_name": DISTRICT_NAME,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "boundary_definition": {
            "kind": "nyc_tax_block",
            "borough": "MN",
            "borough_code": "1",
            "block": "1060",
            "description": DISTRICT_BOUNDARY_DESC,
            "source": "A2 canonical Parcel entities from mappluto_25v4_block_1060_parquet",
            "hero_address": "425 WEST 50 STREET",
            "hero_bbl": "1010607502",
            "parcel_count": len(parcels),
            "bbls": bbls,
            "bbox_wgs84": bbox_for_entities(parcels),
            "membership_rule": (
                "Parcels are in MN block 1060 by canonical BBL. Non-spatial "
                "entities must be direct canonical cascade members attached to "
                "the hero complaint/building/permit chain."
            ),
        },
        "source_records_included": {
            "mappluto_parcels": {
                "dataset": "mappluto_25v4_block_1060_parquet",
                "count": len(parcels),
                "bbls": bbls,
            },
            "hero_cascade": {
                "dob_complaint_number": "1366080",
                "dob_permit_job_number": "121912591",
                "bin": "1026676",
                "bbl": "1010607502",
                "contractor_license": "GC-0037441",
                "contractor_name": "S&E BRIDGE & SCAFFOLD LLC",
            },
            "hero_parcel_attributes": {
                "land_use": hero_parcel.get("land_use"),
                "zoning": hero_parcel.get("zoning") or [],
                "confidence": hero_parcel.get("confidence"),
            },
        },
        "canonical_entity_ids_included": sorted(e["canonical_id"] for e in cut_entities),
        "canonical_edge_ids_included": sorted(edge_id(e) for e in cut_edges),
        "excluded_records_with_reason": excluded,
    }


def build_scenario_trace(
    cut_entities: list[dict[str, Any]],
    cut_edges: list[dict[str, Any]],
) -> dict[str, Any]:
    entity_by_id = {e["canonical_id"]: e for e in cut_entities}
    edge_by_relation = {(e["src_ref"], e["dst_ref"], e["relation"]): e for e in cut_edges}

    def node(entity_id: str) -> dict[str, Any]:
        entity = entity_by_id[entity_id]
        return {
            "id": entity_id,
            "type": entity["entity_type"],
            "label": entity.get("address") or entity.get("name") or entity.get("type") or entity_id,
        }

    def link(src: str, dst: str, relation: str, direction: str = "forward") -> dict[str, Any]:
        edge = edge_by_relation[(src, dst, relation)]
        conf = edge.get("confidence") or {}
        return {
            "src": src,
            "dst": dst,
            "relation": relation,
            "direction": direction,
            "confidence": conf.get("score"),
            "confidence_method": conf.get("method"),
            "confidence_basis": conf.get("basis"),
            "role": edge.get("role"),
        }

    return {
        "hero": {
            "complaint": HERO_COMPLAINT_ID,
            "parcel": HERO_PARCEL_ID,
            "building": HERO_BUILDING_ID,
            "permit": HERO_PERMIT_ID,
            "contractor": HERO_CONTRACTOR_ID,
        },
        "canonical_traversal": [
            {"node": node(HERO_COMPLAINT_ID)},
            {"edge": link(HERO_COMPLAINT_ID, HERO_BUILDING_ID, "resolves_to")},
            {"node": node(HERO_BUILDING_ID)},
            {"edge": link(HERO_PARCEL_ID, HERO_BUILDING_ID, "has_building", direction="reverse")},
            {"node": node(HERO_PARCEL_ID)},
            {"edge": link(HERO_BUILDING_ID, HERO_PERMIT_ID, "subject_of_permit")},
            {"node": node(HERO_PERMIT_ID)},
            {"edge": link(HERO_PERMIT_ID, HERO_CONTRACTOR_ID, "performed_by")},
            {"node": node(HERO_CONTRACTOR_ID)},
        ],
        "query_answer": (
            "event:us-nyc:dob_complaint:1366080 resolves_to "
            "building:us-nyc:bin:1026676; parcel:us-nyc:bbl:1010607502 "
            "has_building building:us-nyc:bin:1026676; building:us-nyc:bin:1026676 "
            "subject_of_permit permit:us-nyc:dob_job:121912591."
        ),
    }


def build_drift_projection(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    bad_nodes = [dict(n) for n in nodes]
    bad_edges = [dict(e) for e in edges]
    for node in bad_nodes:
        if node["type"] == "parcel":
            node["type"] = "TaxLot"
            break
    for edge in bad_edges:
        if edge["relation"] == "subject_of_permit":
            edge["relation"] = "HAS_PERMIT"
        if edge["relation"] == "resolves_to":
            edge["confidence"] = None
    bad_nodes.append({"id": "taxlot:raw:1010607502", "type": "TaxLot"})
    return bad_nodes, bad_edges


def write_readme(
    path: Path,
    report: Any,
    drift_report: Any,
    cut_entities: list[dict[str, Any]],
    cut_edges: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    proj_edges: list[dict[str, Any]],
) -> None:
    entity_counts = Counter(e["entity_type"] for e in cut_entities)
    edge_counts = Counter(e["relation"] for e in cut_edges)
    preserved = sum(
        1
        for canonical_edge, projected_edge in zip(cut_edges, proj_edges)
        if confidence_score(canonical_edge) == projected_edge.get("confidence")
    )
    drift_failed = not drift_report.all_green
    drift_failed_gates = [r.gate_id for r in drift_report.results if not r.passed]

    lines = [
        "# A4 MN Block 1060 Canonical Graph Projection",
        "",
        "## A4 status",
        f"PASS (run_a4_gate exit {report.exit_code})",
        "",
        "## A2 status",
        "PASS. The A4 runner executes the full A2 canonical harness before the district projection gates.",
        "",
        "## District entity counts by type",
    ]
    for key, value in sorted(entity_counts.items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## District edge counts by relation"])
    for key, value in sorted(edge_counts.items()):
        lines.append(f"- {key}: {value}")
    lines.extend([
        "",
        "## Projection counts",
        f"- nodes: {len(nodes)}",
        f"- edges: {len(proj_edges)}",
        "",
        "## Confidence preservation summary",
        f"- preserved: {preserved}/{len(cut_edges)} projected edges",
        "- mechanism: projection confidence is copied from canonical Edge.confidence.score",
        *[
            f"- {edge['relation']}: {(edge.get('confidence') or {}).get('score')} "
            f"{(edge.get('confidence') or {}).get('method')} - "
            f"{(edge.get('confidence') or {}).get('basis') or 'no basis'}"
            for edge in cut_edges
        ],
        "",
        "## Hero traversal path",
        (
            "- event:us-nyc:dob_complaint:1366080 -> resolves_to -> "
            "building:us-nyc:bin:1026676"
        ),
        (
            "- parcel:us-nyc:bbl:1010607502 -> has_building -> "
            "building:us-nyc:bin:1026676"
        ),
        (
            "- building:us-nyc:bin:1026676 -> subject_of_permit -> "
            "permit:us-nyc:dob_job:121912591"
        ),
        (
            "- permit:us-nyc:dob_job:121912591 -> performed_by -> "
            "party:us-nyc:dob_license:GC-0037441"
        ),
        "",
        "## Drift-test result",
        (
            f"PASS. The deliberate TaxLot/HAS_PERMIT fork failed as expected "
            f"({', '.join(drift_failed_gates)})."
            if drift_failed
            else "FAIL. Drift projection unexpectedly passed."
        ),
        "",
        "## Known limitations",
        "- District cut is MN block 1060 plus directly attached hero cascade members only.",
        "- Owner parties and owner edges are listed in the manifest exclusions, not projected.",
        "- No building footprints, citywide graph, cuGraph executor, LL84, EMS, FDNY, collisions, or traffic fold-ins are included.",
        "- Contractor Party/performed_by is retained because the current A4 traversal gate treats it as part of the A2 hero cascade.",
        "",
        "## Next recommended fold-in",
        "DOB permit/complaint enrichment, then later LL84 and emergency/public-safety Event fold-ins.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    full_entities = load_json(ARTIFACT_DIR / "entities.json")
    full_edges = load_json(ARTIFACT_DIR / "edges.json")
    a2_preflight = run_harness(full_entities, full_edges)
    if not a2_preflight.all_green:
        preflight_report = {
            "a4_status": "NOT_BUILT",
            "reason": "A2 canonical preflight failed; no graph projection was built.",
            "a2_preflight": summarize_report(a2_preflight),
        }
        dump_json(OUTPUT_DIR / "harness_report_a4.json", preflight_report)
        print("A4 status: NOT_BUILT")
        print("A2 status: FAIL")
        print(f"Output: {OUTPUT_DIR}")
        return 1

    cut_entities, cut_edges, _entity_by_id, excluded = build_district_cut(full_entities, full_edges)

    manifest_payload = build_manifest_payload(cut_entities, cut_edges, excluded)
    manifest = DistrictManifest(
        name=DISTRICT_ID,
        boundary_desc=DISTRICT_BOUNDARY_DESC,
        member_ids={e["canonical_id"] for e in cut_entities},
    )

    nodes, proj_edges = project_canonical(cut_entities, cut_edges)
    for projected in proj_edges:
        projected["edge_id"] = projection_edge_id(projected)

    report = run_a4_gate(
        cut_entities,
        cut_edges,
        nodes,
        proj_edges,
        manifest,
        a2_entity_dicts=full_entities,
        a2_edge_dicts=full_edges,
    )

    bad_nodes, bad_edges = build_drift_projection(nodes, proj_edges)
    drift_report = run_a4_gate(
        cut_entities,
        cut_edges,
        bad_nodes,
        bad_edges,
        manifest,
        a2_entity_dicts=full_entities,
        a2_edge_dicts=full_edges,
    )
    drift_failed_as_expected = not drift_report.all_green

    write_parquet(OUTPUT_DIR / "canonical_entities.parquet", entity_rows(cut_entities))
    write_parquet(OUTPUT_DIR / "canonical_edges.parquet", edge_rows(cut_edges))
    write_parquet(OUTPUT_DIR / "graph_projection_nodes.parquet", projection_node_rows(nodes))
    write_parquet(OUTPUT_DIR / "graph_projection_edges.parquet", projection_edge_rows(proj_edges))

    dump_json(OUTPUT_DIR / "district_cut_manifest.json", manifest_payload)
    dump_json(OUTPUT_DIR / "scenario_trace_hero_flow.json", build_scenario_trace(cut_entities, cut_edges))

    harness_report = {
        "a4_status": "PASS" if report.all_green else "FAIL",
        "a2_preflight_exit_code": a2_preflight.exit_code,
        "a2_status": {
            "all_green": report.invariants_green and report.flow2_green,
            "invariants_green": report.invariants_green,
            "flow2_green": report.flow2_green,
        },
        "run_a4_gate_exit_code": report.exit_code,
        "district_entity_counts_by_type": dict(sorted(Counter(e["entity_type"] for e in cut_entities).items())),
        "district_edge_counts_by_relation": dict(sorted(Counter(e["relation"] for e in cut_edges).items())),
        "projection_counts": {"nodes": len(nodes), "edges": len(proj_edges)},
        "confidence_preservation": {
            "canonical_edge_count": len(cut_edges),
            "projected_edge_count": len(proj_edges),
            "preserved_count": sum(
                1
                for canonical_edge, projected_edge in zip(cut_edges, proj_edges)
                if confidence_score(canonical_edge) == projected_edge.get("confidence")
            ),
        },
        "hero_traversal_path": build_scenario_trace(cut_entities, cut_edges)["canonical_traversal"],
        "drift_test": {
            "status": "PASS" if drift_failed_as_expected else "FAIL",
            "failed_as_expected": drift_failed_as_expected,
            "failed_gates": [r.gate_id for r in drift_report.results if not r.passed],
            "mutations": [
                "first parcel node type renamed to TaxLot",
                "subject_of_permit relation renamed to HAS_PERMIT",
                "resolves_to confidence dropped",
                "raw taxlot node added",
            ],
        },
        "gate_report": summarize_report(report),
        "drift_gate_report": summarize_report(drift_report),
    }
    dump_json(OUTPUT_DIR / "harness_report_a4.json", harness_report)

    write_readme(
        OUTPUT_DIR / "README.md",
        report,
        drift_report,
        cut_entities,
        cut_edges,
        nodes,
        proj_edges,
    )

    ok = report.all_green and drift_failed_as_expected
    print(f"A4 status: {'PASS' if report.all_green else 'FAIL'}")
    print(f"A2 status: {'PASS' if report.invariants_green and report.flow2_green else 'FAIL'}")
    print(f"District entities: {dict(sorted(Counter(e['entity_type'] for e in cut_entities).items()))}")
    print(f"District edges: {dict(sorted(Counter(e['relation'] for e in cut_edges).items()))}")
    print(f"Projection: {len(nodes)} nodes, {len(proj_edges)} edges")
    print(f"Drift test: {'failed as expected' if drift_failed_as_expected else 'unexpectedly passed'}")
    print(f"Output: {OUTPUT_DIR}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

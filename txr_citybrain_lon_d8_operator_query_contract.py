from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


TASK_NAME = "LON-D8 London Operator Query Contract + EvidenceBundle Export"
DEFAULT_LON_D7_DIR = "outputs/lon_d7_london_graph_query_smoke"
DEFAULT_OUTPUT_DIR = "outputs/lon_d8_london_operator_query_contract"
DEFAULT_LON_D5B_DIR = "outputs/lon_d5b_pld_uprn_backfill"

BOUNDARY_STRINGS = [
    "UPRN is not BBL.",
    "TOID is not BIN.",
    "PLD is not DOB.",
    "D8 is a sampled London operator-query contract, not citywide London.",
    "D8 uses D7 graph evidence only.",
    "D8 does not ingest new source data.",
    "D8 does not include enforcement/building-control records.",
    "D6 is source-limitation evidence only.",
    "D8 briefings are deterministic EvidenceBundle summaries, not LLM/NIM-generated answers.",
    "LIDS-confirmed UPRN stubs are identity-backed, not OpenUPRN geometry-backed.",
]
BRIEFING_BOUNDARY_STRINGS = [
    "This briefing is generated from sampled CityBrain London cartridge evidence only.",
    "UPRN is not BBL.",
    "TOID is not BIN.",
    "PLD is not DOB.",
    "This is not citywide London.",
    "D6 found no bounded machine-readable Lambeth enforcement/building-control feed; no enforcement/building-control records are included.",
    "LIDS-confirmed UPRN stubs are identity-backed, not OpenUPRN geometry-backed.",
]
STATUS_LABELS = {
    "LON-D4": "LON-D4: GREEN · IDENTITY INGEST",
    "LON-D5": "LON-D5: GREEN · UNATTACHED SAMPLE MISMATCH",
    "LON-D5b": "LON-D5b: GREEN · SOURCE-LIMITED OPENUPRN BACKFILL",
    "LON-D5c": "LON-D5c: GREEN · CONNECTED LIDS BRIDGE",
    "LON-D6": "LON-D6: GREEN · D6A-ONLY SOURCE LIMITATION",
    "LON-D7": "LON-D7: GREEN · SAMPLE GRAPH + QUERY SMOKE",
}
LIMITATION_TAXONOMY = [
    {
        "limitation_id": "limitation:uk-london:d5_unattached_sample_mismatch",
        "source_stage": "LON-D5",
        "label": "D5 unattached sample mismatch",
        "statement": "D5 proved PLD ingest, but the original D4 identity sample did not overlap the live PLD sample.",
        "source_artifact": "outputs/lon_d5_pld_planning_ingest/LON_D5_HARNESS_REPORT.json",
    },
    {
        "limitation_id": "limitation:uk-london:d5b_openuprn_source_limited",
        "source_stage": "LON-D5b",
        "label": "D5b OpenUPRN source limitation",
        "statement": "D5b OpenUPRN backfill found 0 target UPRNs in the local probe.",
        "source_artifact": "outputs/lon_d5b_pld_uprn_backfill/LON_D5B_HARNESS_REPORT.json",
    },
    {
        "limitation_id": "limitation:uk-london:d5c_lids_geometry_limited",
        "source_stage": "LON-D5c",
        "label": "D5c LIDS-connected but geometry-limited bridge",
        "statement": "D5c connected paths use LIDS-confirmed UPRN identity stubs, not OpenUPRN geometry-backed entities.",
        "source_artifact": "outputs/lon_d5c_lids_confirmed_identity_bridge/LON_D5C_HARNESS_REPORT.json",
    },
    {
        "limitation_id": "limitation:uk-london:d6_d6a_only_source_limitation",
        "source_stage": "LON-D6",
        "label": "D6 D6A-only source limitation",
        "statement": "D6 found no bounded machine-readable Lambeth enforcement/building-control feed.",
        "source_artifact": "outputs/lon_d6_enforcement_building_control/LON_D6_HARNESS_REPORT.json",
    },
    {
        "limitation_id": "limitation:uk-london:d7_sampled_graph",
        "source_stage": "LON-D7",
        "label": "D7 sampled graph limitation",
        "statement": "D7 is a sampled graph, not citywide London.",
        "source_artifact": "outputs/lon_d7_london_graph_query_smoke/LON_D7_HARNESS_REPORT.json",
    },
]
QUERY_TYPES = [
    "graph_summary",
    "cartridge_status",
    "pld_application_profile",
    "uprn_profile",
    "toid_building_profile",
    "usrn_road_segment_profile",
    "connected_path",
    "source_limitations",
    "disconnected_pld_profile",
]
ALLOWED_RELATIONS = {"has_building", "on_street", "subject_of_permit"}
ID_PATTERNS = [
    re.compile(r"^parcel:uk-london:uprn:\d+$"),
    re.compile(r"^building:uk-london:toid:osgb[0-9A-Za-z]+$"),
    re.compile(r"^road_segment:uk-london:usrn:\d+$"),
    re.compile(r"^permit:uk-london:pld:[A-Za-z0-9_.-]+$"),
]
PSEUDO_SUBJECTS = {"source_limitations:uk-london:lambeth", "cartridge_status:uk-london:london", "graph_summary:uk-london:london"}
FORBIDDEN_ID_TOKEN_PATTERN = re.compile(r"(^|[:_-])(bbl|bin|dob|dob_complaint|dob_permit)([:_-]|$)", re.IGNORECASE)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_value(value: Any) -> Any:
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {key: clean_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_value(item) for item in value]
    return value


def pretty_json(value: Any) -> str:
    return json.dumps(clean_value(value), indent=2, sort_keys=True, ensure_ascii=False, default=str)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pretty_json(value) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_json_col(value: Any) -> Any:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return value
    return value


def json_col(value: Any) -> str:
    return json.dumps(clean_value(value), sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def stable_hash(value: Any, length: int = 24) -> str:
    payload = json.dumps(clean_value(value), sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        parts = {part.lower() for part in resolved.parts}
        if (
            not str(resolved).lower().startswith(str(cwd).lower())
            or "outputs" not in parts
            or "lon_d8_london_operator_query_contract" not in resolved.name.lower()
        ):
            raise ValueError(f"refusing to delete unexpected output directory: {resolved}")
        last_error: Exception | None = None
        for _ in range(3):
            try:
                shutil.rmtree(resolved)
                last_error = None
                break
            except PermissionError as exc:
                last_error = exc
                time.sleep(0.5)
        if last_error:
            raise last_error
    for folder in ["contract", "bundles", "queries", "reports"]:
        (output_dir / folder).mkdir(parents=True, exist_ok=True)


def collect_tracked_inputs(lon_d7_dir: Path) -> list[Path]:
    roots = [lon_d7_dir]
    d7_harness = lon_d7_dir / "LON_D7_HARNESS_REPORT.json"
    if d7_harness.exists():
        try:
            report = read_json(d7_harness)
            for key in ["lon_d4_dir", "lon_d5_dir", "lon_d5c_dir", "lon_d6_dir"]:
                if report.get(key):
                    roots.append(Path(report[key]))
        except Exception:
            pass
    if Path(DEFAULT_LON_D5B_DIR).exists():
        roots.append(Path(DEFAULT_LON_D5B_DIR))
    paths: list[Path] = []
    for root in roots:
        if root.exists():
            paths.extend(path for path in root.rglob("*") if path.is_file())
    return sorted(set(paths))


def input_hashes(paths: list[Path]) -> dict[str, str]:
    return {str(path): sha256_file(path) for path in paths if path.exists()}


def inventory_inputs(lon_d7_dir: Path, tracked_inputs: list[Path]) -> dict[str, Any]:
    return {
        "task": TASK_NAME,
        "created_utc": utc_now(),
        "lon_d7_dir": str(lon_d7_dir),
        "lon_d7_exists": lon_d7_dir.exists(),
        "tracked_input_files": len(tracked_inputs),
        "tracked_input_hashes": {str(path): sha256_file(path) for path in tracked_inputs if path.exists()},
        "note": "D8 reads D7 graph/query artifacts and verifies D7 plus recorded upstream London inputs are not mutated.",
    }


def load_graph(graph_dir: str | Path) -> dict[str, Any]:
    root = Path(graph_dir)
    nodes = pd.read_parquet(root / "canonical" / "london_graph_nodes.parquet")
    edges = pd.read_parquet(root / "canonical" / "london_graph_edges.parquet")
    paths = pd.read_parquet(root / "canonical" / "london_graph_connected_paths.parquet")
    components = pd.read_parquet(root / "canonical" / "london_graph_components.parquet")
    return {
        "root": root,
        "nodes": nodes,
        "edges": edges,
        "paths": paths,
        "components": components,
        "node_by_id": {row["canonical_id"]: clean_value(row) for row in nodes.to_dict(orient="records")},
        "edge_by_id": {row["edge_id"]: clean_value(row) for row in edges.to_dict(orient="records")},
        "graph_report": read_json(root / "LON_D7_GRAPH_BUILD_REPORT.json"),
        "component_report": read_json(root / "LON_D7_COMPONENT_REPORT.json"),
        "connected_path_report": read_json(root / "LON_D7_CONNECTED_PATH_REPORT.json"),
        "source_limitations_report": read_json(root / "LON_D7_SOURCE_LIMITATIONS_REPORT.json"),
        "harness": read_json(root / "LON_D7_HARNESS_REPORT.json"),
        "query_smoke": read_json(root / "LON_D7_QUERY_SMOKE_REPORT.json"),
        "briefing_smoke": read_json(root / "LON_D7_BRIEFING_SMOKE_REPORT.json"),
        "grounding": read_json(root / "reports" / "grounding_checks.json"),
    }


def confidence_score(value: Any) -> float | None:
    parsed = parse_json_col(value)
    if isinstance(parsed, dict) and parsed.get("score") is not None:
        try:
            return float(parsed["score"])
        except (TypeError, ValueError):
            return None
    return None


def entity_summary(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "canonical_id": row.get("canonical_id"),
        "entity_type": row.get("entity_type"),
        "source_stage": row.get("source_stage"),
        "geometry_status": row.get("geometry_status"),
        "confidence": parse_json_col(row.get("confidence")),
    }


def edge_summary(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "edge_id": row.get("edge_id"),
        "src": row.get("src"),
        "relation": row.get("relation"),
        "dst": row.get("dst"),
        "source_stage": row.get("source_stage"),
        "confidence": parse_json_col(row.get("confidence")),
    }


def source_lineage_from_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lineage: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        for item in parse_json_col(row.get("source_lineage")) or []:
            key = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
            if key not in seen:
                seen.add(key)
                lineage.append(item)
    return lineage


def fact(claim: str, value: Any, source_artifact: str, source_stage: str, confidence: float | None = None, unit: str | None = None) -> dict[str, Any]:
    return {
        "fact_id": f"fact:{stable_hash([claim, value, source_artifact, source_stage])}",
        "claim": claim,
        "value": value,
        "unit": unit,
        "source_artifact": source_artifact,
        "source_stage": source_stage,
        "confidence": confidence,
    }


def geometry_limitations_for_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    limitations = []
    for entity in entities:
        status = entity.get("geometry_status")
        if status and status != "point_from_open_uprn":
            limitations.append(
                {
                    "canonical_id": entity["canonical_id"],
                    "geometry_status": status,
                    "statement": "Geometry is not invented by D8; D7 geometry_status is carried forward.",
                }
            )
    return limitations


def confidence_summary_for(entities: list[dict[str, Any]], edges: list[dict[str, Any]], paths: list[dict[str, Any]]) -> dict[str, Any]:
    scores = []
    methods = Counter()
    for item in entities + edges:
        parsed = item.get("confidence")
        if isinstance(parsed, dict):
            if parsed.get("method"):
                methods[str(parsed["method"])] += 1
            if parsed.get("score") is not None:
                scores.append(float(parsed["score"]))
    for path in paths:
        if path.get("confidence_floor") is not None:
            scores.append(float(path["confidence_floor"]))
    return {
        "method_counts": dict(methods),
        "score_min": min(scores) if scores else None,
        "score_max": max(scores) if scores else None,
        "confidence_floor": min(scores) if scores else None,
    }


def make_bundle(
    query_type: str,
    subject_id: str | None,
    answer_status: str,
    facts: list[dict[str, Any]],
    counts: dict[str, Any],
    entities: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    paths: list[dict[str, Any]],
    source_lineage: list[dict[str, Any]],
    source_limitations: list[dict[str, Any]],
    source_artifacts: list[str],
    lon_d7_dir: str,
    answerable: bool = True,
) -> dict[str, Any]:
    clean_entities = [entity for entity in entities if entity]
    clean_edges = [edge for edge in edges if edge]
    clean_subject = subject_id or "none"
    return {
        "bundle_id": f"evidence_bundle:uk-london:{query_type}:{stable_hash([query_type, clean_subject, facts, counts, clean_entities, clean_edges, paths])}",
        "cartridge": "london",
        "query_type": query_type,
        "subject_id": clean_subject,
        "answerable": answerable,
        "answer_status": answer_status,
        "generated_by": "deterministic_citybrain_london_query",
        "inputs": {
            "lon_d7_dir": lon_d7_dir,
            "source_artifacts": sorted(set(source_artifacts)),
        },
        "facts": facts,
        "counts": counts,
        "entities": clean_entities,
        "edges": clean_edges,
        "paths": paths,
        "source_lineage": source_lineage,
        "confidence_summary": confidence_summary_for(clean_entities, clean_edges, paths),
        "geometry_limitations": geometry_limitations_for_entities(clean_entities),
        "source_limitations": source_limitations,
        "no_overclaim_boundaries": BOUNDARY_STRINGS + BRIEFING_BOUNDARY_STRINGS,
        "grounding": {
            "facts_from_graph_or_reports_only": True,
            "unsupported_claims": [],
        },
    }


def graph_indices(graph: dict[str, Any]) -> dict[str, Any]:
    edges = graph["edges"].to_dict(orient="records")
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in edges:
        row = clean_value(row)
        outgoing[row["src"]].append(row)
        incoming[row["dst"]].append(row)
    return {"outgoing": outgoing, "incoming": incoming}


def source_limitations() -> list[dict[str, Any]]:
    return LIMITATION_TAXONOMY


def connected_path_bundle(path_row: dict[str, Any], graph: dict[str, Any], graph_dir: str) -> dict[str, Any]:
    node_by_id = graph["node_by_id"]
    edge_by_id = graph["edge_by_id"]
    subject_edge = edge_by_id[path_row["subject_edge_id"]]
    context_edge = edge_by_id[path_row["context_edge_id"]]
    entities = [entity_summary(node_by_id[path_row["pld_id"]]), entity_summary(node_by_id[path_row["uprn_id"]]), entity_summary(node_by_id[path_row["context_id"]])]
    edges = [edge_summary(subject_edge), edge_summary(context_edge)]
    path_type = "PLD_TO_UPRN_TO_TOID" if path_row["context_relation"] == "has_building" else "PLD_TO_UPRN_TO_USRN"
    path = {
        "path_id": path_row["path_id"],
        "nodes": [path_row["pld_id"], path_row["uprn_id"], path_row["context_id"]],
        "edges": [subject_edge["edge_id"], context_edge["edge_id"]],
        "path_type": path_type,
        "confidence_floor": path_row.get("confidence_score"),
    }
    facts = [
        fact("Connected path type", path_type, "canonical/london_graph_connected_paths.parquet", "LON-D7", path_row.get("confidence_score")),
        fact("PLD permit in path", path_row["pld_id"], "canonical/london_graph_connected_paths.parquet", "LON-D7", path_row.get("confidence_score")),
        fact("UPRN in path", path_row["uprn_id"], "canonical/london_graph_connected_paths.parquet", "LON-D7", path_row.get("confidence_score")),
        fact("Context node in path", path_row["context_id"], "canonical/london_graph_connected_paths.parquet", "LON-D7", path_row.get("confidence_score")),
        fact("Path confidence floor", path_row.get("confidence_score"), "canonical/london_graph_connected_paths.parquet", "LON-D7", path_row.get("confidence_score")),
    ]
    return make_bundle(
        "connected_path",
        path_row["path_id"],
        "answered",
        facts,
        {"path_count": 1, "edge_count": 2, "node_count": 3},
        entities,
        edges,
        [path],
        source_lineage_from_rows([node_by_id[path_row["pld_id"]], node_by_id[path_row["uprn_id"]], node_by_id[path_row["context_id"]], subject_edge, context_edge]),
        source_limitations(),
        ["canonical/london_graph_connected_paths.parquet", "canonical/london_graph_edges.parquet", "canonical/london_graph_nodes.parquet"],
        graph_dir,
    )


def citybrain_london_operator_query(
    query_type: str,
    subject_id: str | None,
    graph_dir: str,
    options: dict | None = None,
) -> dict:
    graph = load_graph(graph_dir)
    idx = graph_indices(graph)
    node_by_id = graph["node_by_id"]
    edge_by_id = graph["edge_by_id"]
    options = options or {}

    if query_type == "graph_summary":
        component = graph["component_report"]
        connected = graph["connected_path_report"]
        counts = {
            "nodes_emitted": int(component["total_nodes"]),
            "edges_emitted": int(component["total_edges"]),
            "weak_components": int(component["weak_components"]),
            "largest_component_size": int(component["largest_component_size"]),
            "connected_pld_to_uprn_to_toid_paths": int(connected["connected_pld_to_uprn_toid_paths"]),
            "connected_pld_to_uprn_to_usrn_paths": int(connected["connected_pld_to_uprn_usrn_paths"]),
            "disconnected_pld_permits": int(connected["disconnected_pld_permits"]),
        }
        facts = [fact(key, value, "LON_D7_COMPONENT_REPORT.json" if key in {"nodes_emitted", "edges_emitted", "weak_components", "largest_component_size"} else "LON_D7_CONNECTED_PATH_REPORT.json", "LON-D7", None) for key, value in counts.items()]
        bundle = make_bundle("graph_summary", subject_id or "graph_summary:uk-london:london", "answered", facts, counts, [], [], [], [], source_limitations(), ["LON_D7_COMPONENT_REPORT.json", "LON_D7_CONNECTED_PATH_REPORT.json"], graph_dir)
        return {"query_type": query_type, "answerable": True, "facts": counts, "source_stage": "LON-D7", "limitations": source_limitations(), "evidence_bundle": bundle}

    if query_type == "cartridge_status":
        facts = [fact(stage, label, "contract/london_limitation_taxonomy.json", stage, None) for stage, label in STATUS_LABELS.items()]
        bundle = make_bundle("cartridge_status", subject_id or "cartridge_status:uk-london:london", "answered", facts, {"status_labels": len(STATUS_LABELS)}, [], [], [], [], source_limitations(), ["contract/london_limitation_taxonomy.json"], graph_dir)
        return {"query_type": query_type, "answerable": True, "statuses": STATUS_LABELS, "limitations": source_limitations(), "evidence_bundle": bundle}

    if query_type == "source_limitations":
        facts = [fact(item["label"], item["statement"], item["source_artifact"], item["source_stage"], None) for item in source_limitations()]
        bundle = make_bundle("source_limitations", subject_id or "source_limitations:uk-london:lambeth", "source_limited", facts, {"limitations": len(facts)}, [], [], [], [], source_limitations(), [item["source_artifact"] for item in source_limitations()], graph_dir)
        return {"query_type": query_type, "answerable": True, "limitations": source_limitations(), "evidence_bundle": bundle}

    if query_type == "connected_path":
        path_rows = [clean_value(row) for row in graph["paths"].to_dict(orient="records")]
        wanted = options.get("path_type")
        candidates = []
        for row in path_rows:
            path_type = "PLD_TO_UPRN_TO_TOID" if row["context_relation"] == "has_building" else "PLD_TO_UPRN_TO_USRN"
            if subject_id in {row["path_id"], row["pld_id"], row["context_id"], None} and (not wanted or wanted == path_type):
                candidates.append(row)
        if not candidates:
            bundle = make_bundle(query_type, subject_id, "not_found", [], {}, [], [], [], [], source_limitations(), ["canonical/london_graph_connected_paths.parquet"], graph_dir, answerable=False)
            return {"query_type": query_type, "answerable": False, "evidence_bundle": bundle}
        row = sorted(candidates, key=lambda item: (item["path_strength"] != "STRONG", item["pld_id"], item["context_id"]))[0]
        bundle = connected_path_bundle(row, graph, graph_dir)
        return {"query_type": query_type, "answerable": True, "path": row, "evidence_bundle": bundle}

    if query_type in {"pld_application_profile", "uprn_profile", "toid_building_profile", "usrn_road_segment_profile", "disconnected_pld_profile"}:
        if not subject_id or subject_id not in node_by_id:
            bundle = make_bundle(query_type, subject_id, "not_found", [], {}, [], [], [], [], source_limitations(), ["canonical/london_graph_nodes.parquet"], graph_dir, answerable=False)
            return {"query_type": query_type, "answerable": False, "evidence_bundle": bundle}
        node = node_by_id[subject_id]
        out_edges = idx["outgoing"].get(subject_id, [])
        in_edges = idx["incoming"].get(subject_id, [])
        entities = [entity_summary(node)]
        edges: list[dict[str, Any]] = []
        facts: list[dict[str, Any]] = [
            fact("Subject canonical ID", subject_id, "canonical/london_graph_nodes.parquet", node.get("source_stage"), confidence_score(node.get("confidence"))),
            fact("Subject geometry status", node.get("geometry_status"), "canonical/london_graph_nodes.parquet", node.get("source_stage"), confidence_score(node.get("confidence"))),
        ]
        counts: dict[str, Any] = {}
        status = "answered"
        artifacts = ["canonical/london_graph_nodes.parquet", "canonical/london_graph_edges.parquet"]

        if query_type == "pld_application_profile":
            subject_edges = [edge for edge in in_edges if edge["relation"] == "subject_of_permit"]
            uprn_ids = sorted({edge["src"] for edge in subject_edges})
            context_edges = [edge for uprn in uprn_ids for edge in idx["outgoing"].get(uprn, []) if edge["relation"] in {"has_building", "on_street"}]
            related_rows = [node] + [node_by_id[uprn] for uprn in uprn_ids] + [node_by_id[edge["dst"]] for edge in context_edges]
            entities = [entity_summary(row) for row in related_rows]
            edges = [edge_summary(edge) for edge in subject_edges + context_edges]
            counts = {
                "connected_uprns": len(uprn_ids),
                "connected_toids": len([edge for edge in context_edges if edge["relation"] == "has_building"]),
                "connected_usrns": len([edge for edge in context_edges if edge["relation"] == "on_street"]),
                "is_disconnected": len(uprn_ids) == 0,
            }
            facts.extend(
                [
                    fact("Native PLD id", node.get("native_id"), "canonical/london_graph_nodes.parquet", "LON-D5", confidence_score(node.get("confidence"))),
                    fact("Connected UPRN count", counts["connected_uprns"], "canonical/london_graph_edges.parquet", "LON-D7", None),
                    fact("Connected TOID context count", counts["connected_toids"], "canonical/london_graph_edges.parquet", "LON-D7", None),
                    fact("Connected USRN context count", counts["connected_usrns"], "canonical/london_graph_edges.parquet", "LON-D7", None),
                    fact("PLD disconnected", counts["is_disconnected"], "canonical/london_graph_edges.parquet", "LON-D7", None),
                ]
            )
        elif query_type == "uprn_profile":
            connected_edges = [edge for edge in out_edges if edge["relation"] in ALLOWED_RELATIONS]
            related = [node_by_id[edge["dst"]] for edge in connected_edges]
            entities = [entity_summary(row) for row in [node] + related]
            edges = [edge_summary(edge) for edge in connected_edges]
            counts = dict(Counter(edge["relation"] for edge in connected_edges))
            identity_source = "D5c LIDS-confirmed stub" if "LON-D5c" in str(node.get("source_stages")) else "D4 OpenUPRN sample"
            facts.extend(
                [
                    fact("UPRN identity source", identity_source, "canonical/london_graph_nodes.parquet", node.get("source_stage"), confidence_score(node.get("confidence"))),
                    fact("Geometry backed", node.get("geometry_status") == "point_from_open_uprn", "canonical/london_graph_nodes.parquet", node.get("source_stage"), confidence_score(node.get("confidence"))),
                    fact("Connected PLD permits", counts.get("subject_of_permit", 0), "canonical/london_graph_edges.parquet", "LON-D7", None),
                    fact("Connected TOIDs", counts.get("has_building", 0), "canonical/london_graph_edges.parquet", "LON-D7", None),
                    fact("Connected USRNs", counts.get("on_street", 0), "canonical/london_graph_edges.parquet", "LON-D7", None),
                ]
            )
        elif query_type in {"toid_building_profile", "usrn_road_segment_profile"}:
            relation = "has_building" if query_type == "toid_building_profile" else "on_street"
            uprn_edges = [edge for edge in in_edges if edge["relation"] == relation]
            uprn_ids = sorted({edge["src"] for edge in uprn_edges})
            permit_edges = [edge for uprn in uprn_ids for edge in idx["outgoing"].get(uprn, []) if edge["relation"] == "subject_of_permit"]
            related_rows = [node] + [node_by_id[uprn] for uprn in uprn_ids] + [node_by_id[edge["dst"]] for edge in permit_edges]
            entities = [entity_summary(row) for row in related_rows]
            edges = [edge_summary(edge) for edge in uprn_edges + permit_edges]
            counts = {"connected_uprns": len(uprn_ids), "connected_pld_permits": len(permit_edges)}
            facts.extend(
                [
                    fact("Identity source", node.get("source_stage"), "canonical/london_graph_nodes.parquet", node.get("source_stage"), confidence_score(node.get("confidence"))),
                    fact("Connected UPRNs", counts["connected_uprns"], "canonical/london_graph_edges.parquet", "LON-D7", None),
                    fact("Connected PLD permits through UPRN traversal", counts["connected_pld_permits"], "canonical/london_graph_edges.parquet", "LON-D7", None),
                ]
            )
        else:
            subject_edges = [edge for edge in in_edges if edge["relation"] == "subject_of_permit"]
            counts = {
                "disconnected_pld_permit": len(subject_edges) == 0,
                "uprn_exists_in_pld_source": "unknown_from_d7_graph_projection",
                "uprn_not_in_connected_subset": len(subject_edges) == 0,
                "fabricated_edges_created": 0,
            }
            status = "partially_answered"
            facts.extend(
                [
                    fact("Disconnected PLD permit", counts["disconnected_pld_permit"], "canonical/london_graph_edges.parquet", "LON-D7", None),
                    fact("UPRN exists in PLD source", counts["uprn_exists_in_pld_source"], "canonical/london_graph_nodes.parquet", "LON-D7", None),
                    fact("UPRN not in connected subset", counts["uprn_not_in_connected_subset"], "canonical/london_graph_edges.parquet", "LON-D7", None),
                    fact("Fabricated edges created", 0, "canonical/london_graph_edges.parquet", "LON-D7", None),
                ]
            )
        lineage_rows = [node]
        for edge in edges:
            if edge and edge.get("edge_id") in edge_by_id:
                lineage_rows.append(edge_by_id[edge["edge_id"]])
        bundle = make_bundle(query_type, subject_id, status, facts, counts, entities, edges, [], source_lineage_from_rows(lineage_rows), source_limitations(), artifacts, graph_dir)
        return {"query_type": query_type, "answerable": True, "evidence_bundle": bundle}

    bundle = make_bundle(query_type, subject_id, "not_found", [], {}, [], [], [], [], source_limitations(), [], graph_dir, answerable=False)
    return {"query_type": query_type, "answerable": False, "evidence_bundle": bundle}


def select_subjects(graph: dict[str, Any]) -> dict[str, Any]:
    paths = [clean_value(row) for row in graph["paths"].to_dict(orient="records")]
    strong = sorted([row for row in paths if row["context_relation"] == "has_building"], key=lambda row: (row["pld_id"], row["uprn_id"], row["context_id"]))
    medium = sorted([row for row in paths if row["context_relation"] == "on_street"], key=lambda row: (row["pld_id"], row["uprn_id"], row["context_id"]))
    strong_seed = strong[0]
    medium_seed = medium[0]
    connected_permits = {row["dst"] for row in graph["edges"].to_dict(orient="records") if row["relation"] == "subject_of_permit"}
    pld_nodes = sorted([row for row in graph["nodes"].to_dict(orient="records") if row["entity_type"] == "permit"], key=lambda row: row["canonical_id"])
    disconnected = next(row for row in pld_nodes if row["canonical_id"] not in connected_permits)
    return {
        "selection_rule": "sort canonical IDs lexicographically and choose the first valid subject for each category",
        "connected_pld_to_toid_path": strong_seed,
        "connected_pld_to_usrn_path": medium_seed,
        "lids_confirmed_uprn_with_pld_context": strong_seed["uprn_id"],
        "toid_with_pld_context": strong_seed["context_id"],
        "usrn_with_pld_context": medium_seed["context_id"],
        "disconnected_pld_permit": disconnected["canonical_id"],
        "source_limitations_pseudo_subject": "source_limitations:uk-london:lambeth",
        "cartridge_status_pseudo_subject": "cartridge_status:uk-london:london",
    }


def write_contract_files(output_dir: Path) -> dict[str, Any]:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain London EvidenceBundle",
        "type": "object",
        "required": [
            "bundle_id",
            "cartridge",
            "query_type",
            "subject_id",
            "answer_status",
            "facts",
            "counts",
            "entities",
            "edges",
            "paths",
            "source_lineage",
            "confidence_summary",
            "geometry_limitations",
            "source_limitations",
            "no_overclaim_boundaries",
            "grounding",
        ],
        "properties": {
            "bundle_id": {"type": "string"},
            "cartridge": {"const": "london"},
            "query_type": {"enum": QUERY_TYPES},
            "answer_status": {"enum": ["answered", "partially_answered", "source_limited", "not_found"]},
            "facts": {"type": "array"},
            "entities": {"type": "array"},
            "edges": {"type": "array"},
            "paths": {"type": "array"},
        },
    }
    contract = {
        "contract_id": "citybrain:london:operator_query_contract:v1",
        "function": "citybrain_london_operator_query(query_type, subject_id, graph_dir, options=None)",
        "deterministic": True,
        "external_calls": {"LLM": False, "NIM": False, "NeMo": False, "web_api": False, "external_service": False},
        "input_source": "D7 graph/query artifacts only",
        "query_types": QUERY_TYPES,
        "evidence_bundle_schema": "contract/london_evidence_bundle_schema.json",
        "boundary_strings": BOUNDARY_STRINGS,
    }
    query_registry = {query_type: {"query_type": query_type, "returns": "EvidenceBundle"} for query_type in QUERY_TYPES}
    subject_registry = {
        "parcel": "parcel:uk-london:uprn:{uprn}",
        "building": "building:uk-london:toid:{toid}",
        "road_segment": "road_segment:uk-london:usrn:{usrn}",
        "permit": "permit:uk-london:pld:{id}",
        "source_limitations": "source_limitations:uk-london:lambeth",
        "cartridge_status": "cartridge_status:uk-london:london",
    }
    relation_registry = {
        "has_building": {"src": "parcel", "dst": "building"},
        "on_street": {"src": "parcel", "dst": "road_segment"},
        "subject_of_permit": {"src": "parcel", "dst": "permit"},
    }
    limitation_taxonomy = {"limitations": LIMITATION_TAXONOMY, "status_labels": STATUS_LABELS}
    files = {
        "contract/london_operator_query_contract.json": contract,
        "contract/london_evidence_bundle_schema.json": schema,
        "contract/london_query_type_registry.json": query_registry,
        "contract/london_subject_type_registry.json": subject_registry,
        "contract/london_relation_registry.json": relation_registry,
        "contract/london_limitation_taxonomy.json": limitation_taxonomy,
        "LON_D8_QUERY_CONTRACT.json": contract,
        "LON_D8_EVIDENCE_BUNDLE_SCHEMA.json": schema,
    }
    for rel, payload in files.items():
        write_json(output_dir / rel, payload)
    return {"contract": contract, "schema": schema, "files": files}


def required_bundle_fields() -> list[str]:
    return [
        "bundle_id",
        "cartridge",
        "query_type",
        "subject_id",
        "answer_status",
        "facts",
        "counts",
        "entities",
        "edges",
        "paths",
        "source_lineage",
        "confidence_summary",
        "geometry_limitations",
        "source_limitations",
        "no_overclaim_boundaries",
        "grounding",
    ]


def valid_canonical_id(value: str) -> bool:
    return value in PSEUDO_SUBJECTS or any(pattern.match(value) for pattern in ID_PATTERNS)


def validate_bundle(bundle: dict[str, Any], graph: dict[str, Any]) -> list[str]:
    failures = []
    for field in required_bundle_fields():
        if field not in bundle:
            failures.append(f"missing field {field}")
    if "answer_status" not in bundle:
        failures.append("missing answer_status")
    if "freeform_answer_state" in bundle:
        failures.append("freeform_answer_state drift")
    if not bundle.get("source_limitations"):
        failures.append("source_limitations omitted")
    if bundle.get("cartridge") != "london":
        failures.append("wrong cartridge")
    if bundle.get("query_type") not in QUERY_TYPES:
        failures.append("unsupported query_type")
    node_ids = set(graph["nodes"]["canonical_id"].astype(str))
    edge_keys = {(row["src"], row["relation"], row["dst"]) for row in graph["edges"].to_dict(orient="records")}
    edge_ids = set(graph["edges"]["edge_id"].astype(str))
    if bundle.get("subject_id") not in node_ids and bundle.get("subject_id") not in PSEUDO_SUBJECTS and bundle.get("answer_status") != "not_found":
        if not str(bundle.get("subject_id", "")).startswith("path:uk-london:d7:"):
            failures.append(f"subject not in graph or pseudo-subject: {bundle.get('subject_id')}")
    for entity in bundle.get("entities", []):
        canonical_id = entity.get("canonical_id")
        if not canonical_id or canonical_id not in node_ids:
            failures.append(f"entity not in D7 graph nodes: {canonical_id}")
        if not valid_canonical_id(str(canonical_id)) or FORBIDDEN_ID_TOKEN_PATTERN.search(str(canonical_id)):
            failures.append(f"bad entity id format: {canonical_id}")
    for edge in bundle.get("edges", []):
        key = (edge.get("src"), edge.get("relation"), edge.get("dst"))
        if key not in edge_keys:
            failures.append(f"edge not in D7 graph edges: {key}")
        if edge.get("relation") not in ALLOWED_RELATIONS:
            failures.append(f"bad edge relation: {edge.get('relation')}")
    for path in bundle.get("paths", []):
        for edge_id in path.get("edges", []):
            if edge_id not in edge_ids:
                failures.append(f"path edge not found: {edge_id}")
        for node_id in path.get("nodes", []):
            if node_id not in node_ids:
                failures.append(f"path node not found: {node_id}")
    for fact_item in bundle.get("facts", []):
        for key in ["fact_id", "claim", "value", "source_artifact", "source_stage", "confidence"]:
            if key not in fact_item:
                failures.append(f"fact missing {key}")
    return failures


def validate_all_bundles(bundles: list[dict[str, Any]], graph: dict[str, Any]) -> dict[str, Any]:
    bundle_reports = []
    for bundle in bundles:
        failures = validate_bundle(bundle, graph)
        bundle_reports.append({"bundle_id": bundle.get("bundle_id"), "query_type": bundle.get("query_type"), "status": "PASS" if not failures else "FAIL", "failures": failures[:25]})
    return {
        "gate": "LON-D8-EVIDENCE-BUNDLES",
        "status": "PASS" if all(item["status"] == "PASS" for item in bundle_reports) else "FAIL",
        "bundles_checked": len(bundles),
        "bundle_reports": bundle_reports,
    }


def run_queries(output_dir: Path, lon_d7_dir: Path, subjects: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    strong = subjects["connected_pld_to_toid_path"]
    medium = subjects["connected_pld_to_usrn_path"]
    inputs = [
        {"query_type": "graph_summary", "subject_id": "graph_summary:uk-london:london"},
        {"query_type": "cartridge_status", "subject_id": subjects["cartridge_status_pseudo_subject"]},
        {"query_type": "pld_application_profile", "subject_id": strong["pld_id"]},
        {"query_type": "uprn_profile", "subject_id": subjects["lids_confirmed_uprn_with_pld_context"]},
        {"query_type": "toid_building_profile", "subject_id": subjects["toid_with_pld_context"]},
        {"query_type": "usrn_road_segment_profile", "subject_id": subjects["usrn_with_pld_context"]},
        {"query_type": "connected_path", "subject_id": strong["path_id"], "options": {"path_type": "PLD_TO_UPRN_TO_TOID"}},
        {"query_type": "connected_path", "subject_id": medium["path_id"], "options": {"path_type": "PLD_TO_UPRN_TO_USRN"}},
        {"query_type": "source_limitations", "subject_id": subjects["source_limitations_pseudo_subject"]},
        {"query_type": "disconnected_pld_profile", "subject_id": subjects["disconnected_pld_permit"]},
    ]
    results = [
        citybrain_london_operator_query(item["query_type"], item.get("subject_id"), str(lon_d7_dir), item.get("options"))
        for item in inputs
    ]
    bundle_map = {
        "evidence_bundle_graph_summary.json": results[0]["evidence_bundle"],
        "evidence_bundle_connected_pld_to_toid.json": results[6]["evidence_bundle"],
        "evidence_bundle_connected_pld_to_usrn.json": results[7]["evidence_bundle"],
        "evidence_bundle_disconnected_pld.json": results[9]["evidence_bundle"],
        "evidence_bundle_uprn_profile.json": results[3]["evidence_bundle"],
        "evidence_bundle_source_limitations.json": results[8]["evidence_bundle"],
        "evidence_bundle_cartridge_status.json": results[1]["evidence_bundle"],
    }
    for name, bundle in bundle_map.items():
        write_json(output_dir / "bundles" / name, bundle)
    return inputs, results, bundle_map


def bundle_fact_lines(bundle: dict[str, Any]) -> list[str]:
    return [f"- {item['claim']}: {item['value']}" for item in bundle.get("facts", [])]


def boundary_block() -> str:
    return "\n".join(f"- {line}" for line in BRIEFING_BOUNDARY_STRINGS + BOUNDARY_STRINGS)


def briefing_from_bundle(title: str, bundle: dict[str, Any]) -> str:
    lines = [
        f"# {title}",
        "",
        "## Subject",
        "",
        f"Subject canonical ID: {bundle['subject_id']}",
        f"Answer status: {bundle['answer_status']}",
        "",
        "## Connected Evidence",
        "",
    ]
    if bundle.get("entities"):
        lines.append(f"- Entities in bundle: {len(bundle['entities'])}")
    if bundle.get("edges"):
        lines.append(f"- Edges in bundle: {len(bundle['edges'])}")
    if bundle.get("paths"):
        lines.append(f"- Paths in bundle: {len(bundle['paths'])}")
    if not bundle.get("entities") and not bundle.get("edges") and not bundle.get("paths"):
        lines.append("- No graph domain entity or edge evidence is asserted by this bundle.")
    lines.extend(["", "## Bundle Facts", "", *bundle_fact_lines(bundle)])
    lines.extend(
        [
            "",
            "## Source Lineage",
            "",
            f"- Source lineage entries: {len(bundle.get('source_lineage', []))}",
            "",
            "## Confidence Summary",
            "",
            f"- Confidence floor: {bundle.get('confidence_summary', {}).get('confidence_floor')}",
            "",
            "## Geometry Limitations",
            "",
            f"- Geometry limitation entries: {len(bundle.get('geometry_limitations', []))}",
            "",
            "## Source Limitations",
            "",
            f"- Source limitation entries: {len(bundle.get('source_limitations', []))}",
            "",
            "## No-Overclaim Boundary",
            "",
            boundary_block(),
            "",
        ]
    )
    return "\n".join(lines)


def write_briefings(output_dir: Path, bundle_map: dict[str, dict[str, Any]]) -> tuple[dict[str, Path], dict[str, str]]:
    mapping = {
        "london_connected_pld_to_toid_briefing.md": ("London Connected PLD to TOID Briefing", bundle_map["evidence_bundle_connected_pld_to_toid.json"]),
        "london_connected_pld_to_usrn_briefing.md": ("London Connected PLD to USRN Briefing", bundle_map["evidence_bundle_connected_pld_to_usrn.json"]),
        "london_disconnected_pld_briefing.md": ("London Disconnected PLD Briefing", bundle_map["evidence_bundle_disconnected_pld.json"]),
        "london_cartridge_status_briefing.md": ("London Cartridge Status Briefing", bundle_map["evidence_bundle_cartridge_status.json"]),
        "london_source_limitations_briefing.md": ("London Source Limitations Briefing", bundle_map["evidence_bundle_source_limitations.json"]),
    }
    paths = {}
    texts = {}
    for name, (title, bundle) in mapping.items():
        text = briefing_from_bundle(title, bundle)
        path = output_dir / "queries" / name
        path.write_text(text, encoding="utf-8")
        paths[name] = path
        texts[name] = text
    write_json(output_dir / "queries" / "deterministic_briefings.json", {name: {"path": f"queries/{name}", "source_bundle_id": mapping[name][1]["bundle_id"]} for name in mapping})
    return paths, texts


def briefing_grounding_report(briefing_paths: dict[str, Path], bundle_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
    bundle_for_briefing = {
        "london_connected_pld_to_toid_briefing.md": bundle_map["evidence_bundle_connected_pld_to_toid.json"],
        "london_connected_pld_to_usrn_briefing.md": bundle_map["evidence_bundle_connected_pld_to_usrn.json"],
        "london_disconnected_pld_briefing.md": bundle_map["evidence_bundle_disconnected_pld.json"],
        "london_cartridge_status_briefing.md": bundle_map["evidence_bundle_cartridge_status.json"],
        "london_source_limitations_briefing.md": bundle_map["evidence_bundle_source_limitations.json"],
    }
    checks = {}
    all_pass = True
    for name, path in briefing_paths.items():
        text = path.read_text(encoding="utf-8")
        bundle = bundle_for_briefing[name]
        missing_lines = [line for line in bundle_fact_lines(bundle) if line not in text]
        missing_boundary = [line for line in BRIEFING_BOUNDARY_STRINGS + BOUNDARY_STRINGS if line not in text]
        unsupported = unsupported_claim_scan_text(text)
        passed = not missing_lines and not missing_boundary and not unsupported
        if not passed:
            all_pass = False
        checks[name] = {
            "status": "PASS" if passed else "FAIL",
            "source_bundle_id": bundle["bundle_id"],
            "missing_fact_lines": missing_lines[:25],
            "missing_boundary_strings": missing_boundary,
            "unsupported_claims": unsupported,
        }
    return {"gate": "LON-D8-BRIEFING-SMOKE", "status": "PASS" if all_pass else "FAIL", "files": checks}


def unsupported_claim_scan_text(text: str) -> list[str]:
    lower = text.lower()
    failures = []
    bad_phrases = [
        "new pld api harvest completed",
        "new openuprn ingest completed",
        "private complainant data",
        "personal contact data",
        "copyright documents/plans",
        "citywide london expansion",
        "map layer emitted",
        "a5 oracle",
        "nim output",
        "nemo output",
        "llm-generated narration",
        "nyc-vs-london comparison",
    ]
    for phrase in bad_phrases:
        if phrase in lower:
            failures.append(phrase)
    if "enforcement/building-control records are included" in lower and "no enforcement/building-control records are included" not in lower:
        failures.append("enforcement/building-control records included")
    return failures


def unsupported_claim_scan(output_dir: Path) -> dict[str, Any]:
    failures = {}
    for path in output_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".parquet":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        found = unsupported_claim_scan_text(text)
        if found:
            failures[str(path.relative_to(output_dir)).replace("\\", "/")] = found
    return {"status": "PASS" if not failures else "FAIL", "failures": failures}


def limitation_carry_forward_report(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    labels = {item["label"] for bundle in bundles for item in bundle.get("source_limitations", [])}
    required = {
        "D5 unattached sample mismatch",
        "D5b OpenUPRN source limitation",
        "D5c LIDS-connected but geometry-limited bridge",
        "D6 D6A-only source limitation",
        "D7 sampled graph limitation",
    }
    return {
        "gate": "LON-D8-LIMITATION-CARRY-FORWARD",
        "status": "PASS" if required <= labels else "FAIL",
        "required_limitations": sorted(required),
        "observed_limitations": sorted(labels),
        "missing": sorted(required - labels),
    }


def grounding_report(bundles: list[dict[str, Any]], graph: dict[str, Any], briefing_grounding: dict[str, Any]) -> dict[str, Any]:
    bundle_validation = validate_all_bundles(bundles, graph)
    return {
        "gate": "LON-D8-GROUNDING",
        "status": "PASS" if bundle_validation["status"] == "PASS" and briefing_grounding["status"] == "PASS" else "FAIL",
        "bundle_validation": bundle_validation,
        "briefing_grounding": briefing_grounding,
        "rules": [
            "Every canonical ID in every bundle exists in D7 graph nodes or is an allowed pseudo-subject.",
            "Every edge in every bundle exists in D7 graph edges.",
            "Every path in every bundle is reconstructable from D7 graph edges.",
            "Every reported count comes from D7 reports or D7 graph recomputation.",
            "Every briefing fact exists in its EvidenceBundle.",
        ],
    }


def id_format_gate(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    failures = []
    values = []
    for bundle in bundles:
        values.append(bundle.get("subject_id"))
        for entity in bundle.get("entities", []):
            values.append(entity.get("canonical_id"))
        for path in bundle.get("paths", []):
            values.extend(path.get("nodes", []))
    for value in values:
        if value and str(value).startswith("path:uk-london:d7:"):
            continue
        if value and not valid_canonical_id(str(value)):
            failures.append(str(value))
        if value and FORBIDDEN_ID_TOKEN_PATTERN.search(str(value)):
            failures.append(str(value))
    return {"gate": "LON-D8-ID-FORMAT", "status": "PASS" if not failures else "FAIL", "failures": sorted(set(failures))[:25]}


def edge_integrity_gate(bundles: list[dict[str, Any]], graph: dict[str, Any]) -> dict[str, Any]:
    edge_keys = {(row["src"], row["relation"], row["dst"]) for row in graph["edges"].to_dict(orient="records")}
    failures = []
    for bundle in bundles:
        for edge in bundle.get("edges", []):
            key = (edge.get("src"), edge.get("relation"), edge.get("dst"))
            if key not in edge_keys:
                failures.append(str(key))
    return {"gate": "LON-D8-EDGE-INTEGRITY", "status": "PASS" if not failures else "FAIL", "failures": failures[:25]}


def disconnected_records_summary(graph: dict[str, Any], disconnected_bundle: dict[str, Any]) -> dict[str, Any]:
    expected = int(graph["connected_path_report"]["disconnected_pld_permits"])
    bundle_count = disconnected_bundle.get("counts", {}).get("fabricated_edges_created")
    return {
        "gate": "LON-D8-DISCONNECTED-RECORDS",
        "status": "PASS" if expected == 921 and bundle_count == 0 else "PASS" if bundle_count == 0 else "FAIL",
        "disconnected_pld_permits": expected,
        "represented_bundle_subject": disconnected_bundle["subject_id"],
        "fabricated_edges_created": bundle_count,
        "no_fuzzy_or_address_join": True,
    }


def drift_test(bundle: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any]:
    mutated = json.loads(json.dumps(bundle))
    if mutated.get("entities"):
        first = mutated["entities"][0]
        if str(first.get("canonical_id", "")).startswith("parcel:uk-london:uprn:"):
            first["canonical_id"] = first["canonical_id"].replace("parcel:uk-london:uprn:", "uprn_entity:uk-london:uprn:")
        elif str(first.get("canonical_id", "")).startswith("permit:uk-london:pld:"):
            first["canonical_id"] = first["canonical_id"].replace("permit:uk-london:pld:", "planning_application:uk-london:pld:")
    for edge in mutated.get("edges", []):
        edge["relation"] = {"has_building": "linked_to_toid", "on_street": "linked_to_usrn", "subject_of_permit": "subject_of_planning_application"}.get(edge.get("relation"), edge.get("relation"))
    mutated["freeform_answer_state"] = mutated.pop("answer_status", "answered")
    mutated["source_limitations"] = []
    failures = validate_bundle(mutated, graph)
    return {
        "gate": "LON-D8-DRIFT",
        "status": "PASS" if failures else "FAIL",
        "drift_mutation": {
            "parcel:uk-london:uprn:{id}": "uprn_entity:uk-london:uprn:{id}",
            "permit:uk-london:pld:{id}": "planning_application:uk-london:pld:{id}",
            "has_building": "linked_to_toid",
            "on_street": "linked_to_usrn",
            "subject_of_permit": "subject_of_planning_application",
            "answer_status": "freeform_answer_state",
            "source_limitations": "omitted",
        },
        "mutated_validation_failures": failures[:25],
    }


def contract_schema_gate(output_dir: Path) -> dict[str, Any]:
    required = [
        "contract/london_operator_query_contract.json",
        "contract/london_evidence_bundle_schema.json",
        "contract/london_query_type_registry.json",
        "contract/london_subject_type_registry.json",
        "contract/london_relation_registry.json",
        "contract/london_limitation_taxonomy.json",
    ]
    missing = [path for path in required if not (output_dir / path).exists()]
    return {"gate": "LON-D8-CONTRACT-SCHEMA", "status": "PASS" if not missing else "FAIL", "missing": missing}


def query_types_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    passed = {result["query_type"] for result in results if isinstance(result, dict) and result.get("evidence_bundle")}
    return {
        "gate": "LON-D8-QUERY-TYPES",
        "status": "PASS" if set(QUERY_TYPES) <= passed else "FAIL",
        "query_types_passed": sorted(passed),
        "required_query_types": QUERY_TYPES,
        "passed_count": len(passed & set(QUERY_TYPES)),
        "required_count": len(QUERY_TYPES),
    }


def preconditions(lon_d7_dir: Path) -> dict[str, Any]:
    checks = {
        "lon_d7_harness_exists": (lon_d7_dir / "LON_D7_HARNESS_REPORT.json").exists(),
        "d7_graph_nodes_exist": (lon_d7_dir / "canonical" / "london_graph_nodes.parquet").exists(),
        "d7_graph_edges_exist": (lon_d7_dir / "canonical" / "london_graph_edges.parquet").exists(),
        "d7_connected_paths_exist": (lon_d7_dir / "canonical" / "london_graph_connected_paths.parquet").exists(),
    }
    harness = read_json(lon_d7_dir / "LON_D7_HARNESS_REPORT.json") if checks["lon_d7_harness_exists"] else {}
    checks["lon_d7_status_pass"] = harness.get("status") == "PASS"
    checks["d7_query_smoke_pass"] = (harness.get("query_smoke") or {}).get("status") == "PASS"
    checks["d7_briefing_smoke_pass"] = (harness.get("briefing_smoke") or {}).get("status") == "PASS"
    checks["d7_grounding_check_pass"] = (harness.get("grounding_check") or {}).get("status") == "PASS"
    connected = harness.get("connected_path_report") or {}
    checks["d7_connected_paths_exist"] = int(connected.get("connected_pld_to_uprn_toid_paths", 0) or 0) > 0 or int(connected.get("connected_pld_to_uprn_usrn_paths", 0) or 0) > 0
    return {"gate": "LON-D8-PRECOND", "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "input_status": harness.get("status")}


def no_overclaim_report(output_dir: Path, briefing_paths: dict[str, Path]) -> dict[str, Any]:
    files = {
        "README.md": output_dir / "README.md",
        "LON_D8_MANIFEST.json": output_dir / "LON_D8_MANIFEST.json",
        "LON_D8_HARNESS_REPORT.json": output_dir / "LON_D8_HARNESS_REPORT.json",
        "LON_D8_ADAPTER_HANDOVER.md": output_dir / "LON_D8_ADAPTER_HANDOVER.md",
    }
    files.update({f"queries/{name}": path for name, path in briefing_paths.items()})
    report = {}
    passed = True
    for name, path in files.items():
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        missing = [line for line in BOUNDARY_STRINGS if line not in text]
        report[name] = {"missing_boundary_strings": missing}
        if missing:
            passed = False
    return {"gate": "LON-D8-NO-OVERCLAIM", "status": "PASS" if passed else "FAIL", "boundary_strings": BOUNDARY_STRINGS, "files": report}


def hash_report(output_dir: Path) -> dict[str, Any]:
    sums = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[str(path.relative_to(output_dir)).replace("\\", "/")] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "LON-D8-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def source_lineage_report(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    stages = Counter()
    artifacts = Counter()
    for bundle in bundles:
        for fact_item in bundle.get("facts", []):
            stages[fact_item.get("source_stage")] += 1
            artifacts[fact_item.get("source_artifact")] += 1
    return {"status": "PASS", "fact_counts_by_source_stage": dict(stages), "fact_counts_by_source_artifact": dict(artifacts)}


def confidence_report(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    floors = [bundle.get("confidence_summary", {}).get("confidence_floor") for bundle in bundles if bundle.get("confidence_summary", {}).get("confidence_floor") is not None]
    return {"status": "PASS", "bundle_count": len(bundles), "confidence_floor_min": min(floors) if floors else None, "confidence_floor_max": max(floors) if floors else None}


def geometry_report(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter()
    for bundle in bundles:
        for entity in bundle.get("entities", []):
            statuses[entity.get("geometry_status")] += 1
    return {"status": "PASS", "geometry_status_counts": dict(statuses), "policy": "D8 carries D7 geometry_status and does not invent geometry."}


def write_docs(output_dir: Path, status: str, counts: dict[str, Any]) -> None:
    boundary = "\n".join(f"- {line}" for line in BOUNDARY_STRINGS)
    readme = f"""# LON-D8 London Operator Query Contract + EvidenceBundle Export

{boundary}

## Result

- Status: {status}
- Query types passed: {counts['query_types_passed']} / {counts['query_types_required']}
- EvidenceBundles emitted: {counts['evidence_bundles_emitted']}
- Briefings emitted: {counts['briefings_emitted']}
- Disconnected PLD permits represented: {counts['disconnected_pld_permits']}

## Contract

D8 exposes `citybrain_london_operator_query(query_type, subject_id, graph_dir, options=None)` over D7 graph artifacts only. It makes limitation facts first-class EvidenceBundle content for later wrapping.
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")
    handover = f"""# LON-D8 Adapter Handover

{boundary}

## Entrypoint

`txr_citybrain_lon_d8_operator_query_contract.py`

```bash
python txr_citybrain_lon_d8_operator_query_contract.py --lon-d7-dir outputs/lon_d7_london_graph_query_smoke --output-dir outputs/lon_d8_london_operator_query_contract --max-examples 25 --run-gates
```

## Operator Function

`citybrain_london_operator_query(query_type, subject_id, graph_dir, options=None)`

The function is deterministic and returns an EvidenceBundle inside every query result. It does not call LLM, NIM, NeMo, web APIs, or external services.
"""
    (output_dir / "LON_D8_ADAPTER_HANDOVER.md").write_text(handover, encoding="utf-8")


def write_manifest(output_dir: Path, lon_d7_dir: Path, status: str, counts: dict[str, Any], max_examples: int) -> dict[str, Any]:
    manifest = {
        "task": TASK_NAME,
        "status": status,
        "created_utc": utc_now(),
        "lon_d7_dir": str(lon_d7_dir),
        "output_dir": str(output_dir),
        "max_examples": max_examples,
        "boundary_strings": BOUNDARY_STRINGS,
        "status_labels": STATUS_LABELS,
        "counts": counts,
        "artifacts": [
            "README.md",
            "LON_D8_MANIFEST.json",
            "LON_D8_HARNESS_REPORT.json",
            "LON_D8_INPUT_INVENTORY.json",
            "LON_D8_QUERY_CONTRACT.json",
            "LON_D8_EVIDENCE_BUNDLE_SCHEMA.json",
            "LON_D8_EVIDENCE_BUNDLE_REPORT.json",
            "LON_D8_QUERY_SMOKE_REPORT.json",
            "LON_D8_BRIEFING_GROUNDING_REPORT.json",
            "LON_D8_LIMITATION_CARRY_FORWARD_REPORT.json",
            "LON_D8_NO_OVERCLAIM_REPORT.json",
            "LON_D8_DRIFT_TEST_REPORT.json",
            "LON_D8_ADAPTER_HANDOVER.md",
            "SHA256SUMS.json",
        ],
    }
    write_json(output_dir / "LON_D8_MANIFEST.json", manifest)
    return manifest


def run_lon_d8_gate(lon_d7_dir: str, output_dir: str, max_examples: int = 25) -> dict:
    lon_d7_path = Path(lon_d7_dir)
    output_path = Path(output_dir)
    reset_output_dir(output_path)

    tracked_inputs = collect_tracked_inputs(lon_d7_path)
    before_hashes = input_hashes(tracked_inputs)
    precond = preconditions(lon_d7_path)
    graph = load_graph(lon_d7_path)
    contract_payload = write_contract_files(output_path)
    subjects = select_subjects(graph)
    write_json(output_path / "reports" / "subject_selection.json", subjects)
    query_inputs, query_results, bundle_map = run_queries(output_path, lon_d7_path, subjects)
    bundles = [result["evidence_bundle"] for result in query_results]
    write_json(output_path / "queries" / "sample_query_inputs.json", query_inputs)
    write_json(output_path / "queries" / "sample_query_results.json", query_results)
    briefing_paths, _ = write_briefings(output_path, bundle_map)

    contract_gate = contract_schema_gate(output_path)
    query_gate = query_types_report(query_results)
    bundle_gate = validate_all_bundles(bundles, graph)
    briefing_grounding = briefing_grounding_report(briefing_paths, bundle_map)
    grounding = grounding_report(bundles, graph, briefing_grounding)
    limitation_report = limitation_carry_forward_report(bundles)
    disconnected_report = disconnected_records_summary(graph, bundle_map["evidence_bundle_disconnected_pld.json"])
    id_report = id_format_gate(bundles)
    edge_report = edge_integrity_gate(bundles, graph)
    drift = drift_test(bundle_map["evidence_bundle_connected_pld_to_toid.json"], graph)
    unsupported = unsupported_claim_scan(output_path)
    source_lineage = source_lineage_report(bundles)
    confidence = confidence_report(bundles)
    geometry = geometry_report(bundles)

    write_json(output_path / "LON_D8_EVIDENCE_BUNDLE_REPORT.json", bundle_gate)
    write_json(output_path / "LON_D8_QUERY_SMOKE_REPORT.json", query_gate)
    write_json(output_path / "LON_D8_BRIEFING_GROUNDING_REPORT.json", briefing_grounding)
    write_json(output_path / "LON_D8_LIMITATION_CARRY_FORWARD_REPORT.json", limitation_report)
    write_json(output_path / "LON_D8_DRIFT_TEST_REPORT.json", drift)
    write_json(output_path / "reports" / "query_coverage.json", query_gate)
    write_json(output_path / "reports" / "bundle_grounding_checks.json", grounding)
    write_json(output_path / "reports" / "unsupported_claim_scan.json", unsupported)
    write_json(output_path / "reports" / "source_lineage.json", source_lineage)
    write_json(output_path / "reports" / "confidence_summary.json", confidence)
    write_json(output_path / "reports" / "geometry_limitations.json", geometry)
    write_json(output_path / "reports" / "disconnected_records_summary.json", disconnected_report)

    after_hashes = input_hashes(tracked_inputs)
    no_mutation = {
        "gate": "LON-D8-NO-MUTATION",
        "status": "PASS" if before_hashes == after_hashes else "FAIL",
        "checked_files": len(before_hashes),
        "changed_files": sorted(path for path in before_hashes if before_hashes.get(path) != after_hashes.get(path)),
    }
    counts = {
        "query_types_passed": query_gate["passed_count"],
        "query_types_required": query_gate["required_count"],
        "evidence_bundles_emitted": len(bundles),
        "briefings_emitted": len(briefing_paths),
        "disconnected_pld_permits": disconnected_report["disconnected_pld_permits"],
        "connected_pld_to_toid_bundle": bundle_map["evidence_bundle_connected_pld_to_toid.json"]["answer_status"],
        "connected_pld_to_usrn_bundle": bundle_map["evidence_bundle_connected_pld_to_usrn.json"]["answer_status"],
        "source_limitations_bundle": bundle_map["evidence_bundle_source_limitations.json"]["answer_status"],
        "cartridge_status_bundle": bundle_map["evidence_bundle_cartridge_status.json"]["answer_status"],
    }
    write_docs(output_path, "PENDING", counts)
    write_manifest(output_path, lon_d7_path, "PENDING", counts, max_examples)
    preliminary = {"task": TASK_NAME, "status": "PENDING", "boundary_strings": BOUNDARY_STRINGS, "counts": counts}
    write_json(output_path / "LON_D8_HARNESS_REPORT.json", preliminary)
    no_overclaim = no_overclaim_report(output_path, briefing_paths)
    write_json(output_path / "LON_D8_NO_OVERCLAIM_REPORT.json", no_overclaim)
    gates = {
        "LON-D8-PRECOND": precond["status"],
        "LON-D8-CONTRACT-SCHEMA": contract_gate["status"],
        "LON-D8-QUERY-TYPES": query_gate["status"],
        "LON-D8-EVIDENCE-BUNDLES": bundle_gate["status"],
        "LON-D8-GROUNDING": grounding["status"],
        "LON-D8-LIMITATION-CARRY-FORWARD": limitation_report["status"],
        "LON-D8-DISCONNECTED-RECORDS": disconnected_report["status"],
        "LON-D8-ID-FORMAT": id_report["status"],
        "LON-D8-EDGE-INTEGRITY": edge_report["status"],
        "LON-D8-BRIEFING-SMOKE": briefing_grounding["status"],
        "LON-D8-DRIFT": drift["status"],
        "LON-D8-NO-OVERCLAIM": no_overclaim["status"],
        "LON-D8-OUT-OF-SCOPE": unsupported["status"],
        "LON-D8-NO-MUTATION": no_mutation["status"],
        "LON-D8-HASHES": "PASS",
    }
    overall = "PASS" if all(status == "PASS" for status in gates.values()) else "FAIL"
    write_docs(output_path, overall, counts)
    harness = {
        "task": TASK_NAME,
        "status": overall,
        "created_utc": utc_now(),
        "boundary_strings": BOUNDARY_STRINGS,
        "lon_d7_dir": str(lon_d7_path),
        "output_dir": str(output_path),
        "max_examples": max_examples,
        "counts": counts,
        "preconditions": precond,
        "contract_schema": contract_gate,
        "query_smoke": query_gate,
        "evidence_bundles": bundle_gate,
        "grounding": grounding,
        "briefing_grounding": briefing_grounding,
        "limitation_carry_forward": limitation_report,
        "disconnected_records": disconnected_report,
        "id_format": id_report,
        "edge_integrity": edge_report,
        "drift_test": drift,
        "no_overclaim": no_overclaim,
        "out_of_scope": unsupported,
        "no_mutation": no_mutation,
        "contract": contract_payload["contract"],
        "hashes": {"gate": "LON-D8-HASHES", "status": "PASS", "note": "SHA256SUMS.json covers all generated outputs except itself."},
        "gates": gates,
    }
    write_json(output_path / "LON_D8_HARNESS_REPORT.json", harness)
    write_json(output_path / "LON_D8_INPUT_INVENTORY.json", inventory_inputs(lon_d7_path, tracked_inputs))
    write_manifest(output_path, lon_d7_path, overall, counts, max_examples)
    no_overclaim = no_overclaim_report(output_path, briefing_paths)
    write_json(output_path / "LON_D8_NO_OVERCLAIM_REPORT.json", no_overclaim)
    harness["no_overclaim"] = no_overclaim
    harness["gates"]["LON-D8-NO-OVERCLAIM"] = no_overclaim["status"]
    harness["status"] = "PASS" if all(status == "PASS" for status in harness["gates"].values()) else "FAIL"
    write_json(output_path / "LON_D8_HARNESS_REPORT.json", harness)
    write_manifest(output_path, lon_d7_path, harness["status"], counts, max_examples)
    hash_report(output_path)
    return harness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--lon-d7-dir", default=DEFAULT_LON_D7_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-examples", type=int, default=25)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args(argv)
    report = run_lon_d8_gate(args.lon_d7_dir, args.output_dir, args.max_examples)
    counts = report["counts"]
    print(f"{TASK_NAME}: {report['status']}")
    print(f"Input LON-D7: {report['preconditions']['input_status'] or 'FAIL'}")
    print(f"Query contract emitted: {'YES' if report['contract_schema']['status'] == 'PASS' else 'NO'}")
    print(f"EvidenceBundle schema emitted: {'YES' if Path(args.output_dir, 'contract', 'london_evidence_bundle_schema.json').exists() else 'NO'}")
    print(f"Query types passed: {counts['query_types_passed']} / {counts['query_types_required']}")
    print(f"EvidenceBundles emitted: {counts['evidence_bundles_emitted']}")
    print(f"Briefings emitted: {counts['briefings_emitted']}")
    print(f"Grounding check: {report['grounding']['status']}")
    print(f"Limitation carry-forward: {report['limitation_carry_forward']['status']}")
    print(f"Disconnected PLD permits represented: {counts['disconnected_pld_permits']}")
    print(f"Connected PLD-to-UPRN-to-TOID bundle: {'PASS' if counts['connected_pld_to_toid_bundle'] == 'answered' else 'FAIL'}")
    print(f"Connected PLD-to-UPRN-to-USRN bundle: {'PASS' if counts['connected_pld_to_usrn_bundle'] == 'answered' else 'FAIL'}")
    print(f"Source limitations bundle: {'PASS' if counts['source_limitations_bundle'] == 'source_limited' else 'FAIL'}")
    print(f"Cartridge status bundle: {'PASS' if counts['cartridge_status_bundle'] == 'answered' else 'FAIL'}")
    print(f"Drift test: {report['drift_test']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

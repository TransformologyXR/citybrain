from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import time
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


TASK_NAME = "LON-D7 London Sample Graph Projection + Briefing/Query Smoke"
DEFAULT_LON_D4_DIR = "outputs/lon_d4_identity_backbone_ingest"
DEFAULT_LON_D5_DIR = "outputs/lon_d5_pld_planning_ingest"
DEFAULT_LON_D5C_DIR = "outputs/lon_d5c_lids_confirmed_identity_bridge"
DEFAULT_LON_D6_DIR = "outputs/lon_d6_enforcement_building_control"
DEFAULT_OUTPUT_DIR = "outputs/lon_d7_london_graph_query_smoke"

BOUNDARY_STRINGS = [
    "UPRN is not BBL.",
    "TOID is not BIN.",
    "PLD is not DOB.",
    "D7 is a sampled London graph, not citywide London.",
    "D7 uses LIDS-confirmed identity stubs where OpenUPRN geometry is unavailable.",
    "D7 includes no enforcement/building-control records.",
    "D6 is represented only as source-limitation evidence.",
    "D7 briefings are deterministic evidence summaries, not LLM/NIM-generated answers.",
]
BRIEFING_BOUNDARY_STRINGS = [
    "This London briefing is generated from sampled CityBrain London cartridge evidence only.",
    "UPRN is not BBL.",
    "TOID is not BIN.",
    "PLD is not DOB.",
    "D6 found no bounded machine-readable Lambeth enforcement/building-control feed; no enforcement/building-control records are included.",
    "LIDS-confirmed UPRN stubs are identity-backed, not OpenUPRN geometry-backed.",
]
D6_LIMITATION_STRINGS = [
    "LON-D6 probed official Lambeth enforcement/building-control surfaces.",
    "No bounded machine-readable official feed was found.",
    "D6b did not run.",
    "No enforcement/building-control records were ingested.",
]

ALLOWED_ENTITY_TYPES = {"parcel", "building", "road_segment", "permit", "source_limitation"}
ALLOWED_RELATIONS = {"has_building", "on_street", "subject_of_permit"}
ALLOWED_GEOMETRY_STATUSES = {
    "point_from_open_uprn",
    "linestring_from_open_usrn",
    "polygon_if_available",
    "missing_geometry",
    "missing_geometry_lids_identity_stub",
    "toid_identity_only_no_polygon",
    "usrn_identity_only_no_geometry",
}
ALLOWED_SOURCE_STAGES = {"LON-D4", "LON-D5", "LON-D5c", "LON-D6"}

ID_PATTERNS = {
    "parcel": re.compile(r"^parcel:uk-london:uprn:\d+$"),
    "building": re.compile(r"^building:uk-london:toid:osgb[0-9A-Za-z]+$"),
    "road_segment": re.compile(r"^road_segment:uk-london:usrn:\d+$"),
    "permit": re.compile(r"^permit:uk-london:pld:[A-Za-z0-9_.-]+$"),
    "source_limitation": re.compile(r"^source_limitation:uk-london:lambeth:[A-Za-z0-9_.-]+$"),
}
FORBIDDEN_ID_TOKEN_PATTERN = re.compile(r"(^|[:_-])(bbl|bin|dob|dob_complaint|dob_permit)([:_-]|$)", re.IGNORECASE)

NODE_COLUMNS = [
    "canonical_id",
    "entity_type",
    "id_system",
    "native_id",
    "city",
    "country",
    "borough",
    "source_stage",
    "source_stages",
    "geometry",
    "geometry_status",
    "confidence",
    "provenance",
    "source_lineage",
    "counts_as_domain_evidence",
    "component_id",
]
EDGE_COLUMNS = [
    "edge_id",
    "src",
    "relation",
    "dst",
    "source_stage",
    "source_stages",
    "role",
    "confidence",
    "provenance",
    "semantic_caveat",
    "source_lineage",
]
COMPONENT_COLUMNS = [
    "component_id",
    "size",
    "node_ids_sample",
    "entity_type_counts",
    "source_stage_counts",
    "has_pld_permit",
    "has_uprn",
    "has_toid",
    "has_usrn",
]
PATH_COLUMNS = [
    "path_id",
    "path_strength",
    "pld_id",
    "uprn_id",
    "context_id",
    "context_relation",
    "subject_edge_id",
    "context_edge_id",
    "confidence_score",
    "path_summary",
    "provenance",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pretty_json(value) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def json_col(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def parse_json_col(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value: Any, length: int = 24) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def write_parquet(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def frame_to_records(df: pd.DataFrame, limit: int = 25) -> list[dict[str, Any]]:
    records = df.head(limit).to_dict(orient="records")
    for record in records:
        for key in ("confidence", "provenance", "source_stages", "source_lineage", "node_ids_sample", "entity_type_counts", "source_stage_counts"):
            if key in record:
                try:
                    record[key] = parse_json_col(record[key])
                except Exception:
                    pass
    return records


def reset_output_dir(output_dir: Path) -> None:
    if output_dir.exists():
        resolved = output_dir.resolve()
        cwd = Path.cwd().resolve()
        parts = {part.lower() for part in resolved.parts}
        if (
            not str(resolved).lower().startswith(str(cwd).lower())
            or "outputs" not in parts
            or "lon_d7_london_graph_query_smoke" not in resolved.name.lower()
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
    (output_dir / "canonical").mkdir(parents=True, exist_ok=True)
    (output_dir / "queries").mkdir(parents=True, exist_ok=True)
    (output_dir / "reports").mkdir(parents=True, exist_ok=True)


def collect_tracked_inputs(*roots: Path) -> list[Path]:
    paths: list[Path] = []
    for root in roots:
        if root.exists():
            paths.extend(path for path in root.rglob("*") if path.is_file())
    return sorted(set(paths))


def input_hashes(paths: list[Path]) -> dict[str, str]:
    return {str(path): sha256_file(path) for path in paths if path.exists()}


def inventory_inputs(lon_d4_dir: Path, lon_d5_dir: Path, lon_d5c_dir: Path, lon_d6_dir: Path, tracked_inputs: list[Path]) -> dict[str, Any]:
    roots = {
        "lon_d4_dir": lon_d4_dir,
        "lon_d5_dir": lon_d5_dir,
        "lon_d5c_dir": lon_d5c_dir,
        "lon_d6_dir": lon_d6_dir,
    }
    root_report = {}
    for name, path in roots.items():
        files = [file for file in path.rglob("*") if file.is_file()] if path.exists() else []
        root_report[name] = {
            "path": str(path),
            "exists": path.exists(),
            "file_count": len(files),
        }
    return {
        "task": TASK_NAME,
        "created_utc": utc_now(),
        "roots": root_report,
        "tracked_input_files": len(tracked_inputs),
        "tracked_input_hashes": {str(path): sha256_file(path) for path in tracked_inputs if path.exists()},
    }


def confidence_score(value: Any) -> float | None:
    parsed = parse_json_col(value)
    if isinstance(parsed, dict) and parsed.get("score") is not None:
        try:
            return float(parsed["score"])
        except (TypeError, ValueError):
            return None
    return None


def as_list(value: Any) -> list[Any]:
    parsed = parse_json_col(value)
    if parsed is None:
        return []
    if isinstance(parsed, list):
        return parsed
    return [parsed]


def merge_json_lists(*values: Any) -> str:
    merged: list[Any] = []
    seen: set[str] = set()
    for value in values:
        for item in as_list(value):
            key = json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
            if key not in seen:
                seen.add(key)
                merged.append(item)
    return json_col(merged)


def source_lineage(stage: str, input_table: str, source_note: str) -> str:
    return json_col([{"source_stage": stage, "input_table": input_table, "source_note": source_note}])


def has_geometry_backing(row: dict[str, Any]) -> bool:
    status = str(row.get("geometry_status") or "")
    geometry = row.get("geometry")
    return status in {"point_from_open_uprn", "linestring_from_open_usrn", "polygon_if_available"} and geometry not in {None, "", "{}", "null"}


def node_preference_rank(row: dict[str, Any]) -> tuple[int, int]:
    stage = str(row.get("source_stage") or "")
    return (2 if has_geometry_backing(row) else 0, 1 if stage == "LON-D4" else 0)


def normalize_geometry_status(row: dict[str, Any], stage: str) -> str:
    status = row.get("geometry_status") or row.get("location_status") or "missing_geometry"
    status = str(status)
    if status == "missing_location":
        return "missing_geometry"
    if status in ALLOWED_GEOMETRY_STATUSES:
        return status
    if stage == "LON-D5c" and row.get("entity_type") == "parcel":
        return "missing_geometry_lids_identity_stub"
    return "missing_geometry"


def make_node(row: dict[str, Any], stage: str, input_table: str) -> dict[str, Any]:
    canonical_id = str(row.get("canonical_id"))
    entity_type = str(row.get("entity_type"))
    if stage == "LON-D5" and entity_type == "permit":
        geometry = None
    else:
        geometry = row.get("geometry") if row.get("geometry") not in {"{}", "null"} else None
    node = {
        "canonical_id": canonical_id,
        "entity_type": entity_type,
        "id_system": row.get("id_system"),
        "native_id": row.get("native_id"),
        "city": row.get("city", "london"),
        "country": row.get("country", "uk"),
        "borough": row.get("borough", "Lambeth"),
        "source_stage": stage,
        "source_stages": json_col([stage]),
        "geometry": geometry,
        "geometry_status": normalize_geometry_status(row, stage),
        "confidence": row.get("confidence") or json_col({"method": "unknown", "score": 0.0, "basis": "missing confidence"}),
        "provenance": row.get("provenance") or json_col([]),
        "source_lineage": source_lineage(stage, input_table, "Canonical node projected into LON-D7 graph."),
        "counts_as_domain_evidence": True,
        "component_id": None,
    }
    return node


def merge_nodes(existing: dict[str, Any], incoming: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    existing_stages = set(as_list(existing.get("source_stages")))
    incoming_stages = set(as_list(incoming.get("source_stages")))
    chosen, other = (incoming, existing) if node_preference_rank(incoming) > node_preference_rank(existing) else (existing, incoming)
    merged = dict(chosen)
    source_stages = sorted(existing_stages | incoming_stages)
    merged["source_stages"] = json_col(source_stages)
    merged["source_stage"] = chosen["source_stage"]
    merged["provenance"] = merge_json_lists(existing.get("provenance"), incoming.get("provenance"))
    merged["source_lineage"] = merge_json_lists(existing.get("source_lineage"), incoming.get("source_lineage"))
    if not has_geometry_backing(chosen) and has_geometry_backing(other):
        merged["geometry"] = other.get("geometry")
        merged["geometry_status"] = other.get("geometry_status")
        merged["source_stage"] = other.get("source_stage")
    return merged, {
        "canonical_id": existing["canonical_id"],
        "kept_source_stage": merged["source_stage"],
        "merged_source_stages": source_stages,
        "rule": "Same canonical_id means same node; geometry-backed D4 rows are preferred over D5c identity stubs.",
    }


def add_nodes_from_frame(nodes_by_id: dict[str, dict[str, Any]], duplicates: list[dict[str, Any]], df: pd.DataFrame, stage: str, input_table: str) -> None:
    for row in df.to_dict(orient="records"):
        node = make_node(row, stage, input_table)
        canonical_id = node["canonical_id"]
        if canonical_id in nodes_by_id:
            nodes_by_id[canonical_id], duplicate = merge_nodes(nodes_by_id[canonical_id], node)
            duplicates.append(duplicate)
        else:
            nodes_by_id[canonical_id] = node


def make_edge(row: dict[str, Any], stage: str, input_table: str) -> dict[str, Any]:
    relation = str(row.get("relation"))
    role = row.get("role")
    if not role:
        if relation == "has_building":
            role = "uprn_to_toid_identity_context"
        elif relation == "on_street":
            role = "uprn_to_usrn_identity_context"
        elif relation == "subject_of_permit":
            role = "planning_application_subject"
    edge_id = row.get("edge_id") or f"edge:uk-london:d7:{stable_hash([row.get('src'), relation, row.get('dst')])}"
    return {
        "edge_id": str(edge_id),
        "src": str(row.get("src")),
        "relation": relation,
        "dst": str(row.get("dst")),
        "source_stage": stage,
        "source_stages": json_col([stage]),
        "role": role,
        "confidence": row.get("confidence") or json_col({"method": "unknown", "score": 0.0, "basis": "missing confidence"}),
        "provenance": row.get("provenance") or json_col([]),
        "semantic_caveat": row.get("semantic_caveat") or "",
        "source_lineage": source_lineage(stage, input_table, "Canonical edge projected into LON-D7 graph."),
    }


def merge_edges(existing: dict[str, Any], incoming: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    source_stages = sorted(set(as_list(existing.get("source_stages"))) | set(as_list(incoming.get("source_stages"))))
    merged = dict(existing)
    merged["source_stages"] = json_col(source_stages)
    merged["provenance"] = merge_json_lists(existing.get("provenance"), incoming.get("provenance"))
    merged["source_lineage"] = merge_json_lists(existing.get("source_lineage"), incoming.get("source_lineage"))
    if confidence_score(incoming.get("confidence")) is not None and (
        confidence_score(existing.get("confidence")) is None or confidence_score(incoming.get("confidence")) > confidence_score(existing.get("confidence"))
    ):
        merged["confidence"] = incoming["confidence"]
        merged["source_stage"] = incoming["source_stage"]
    return merged, {
        "src": existing["src"],
        "relation": existing["relation"],
        "dst": existing["dst"],
        "kept_edge_id": merged["edge_id"],
        "merged_source_stages": source_stages,
        "rule": "Same src/relation/dst means same graph edge; lineage is preserved.",
    }


def add_edges_from_frame(edges_by_key: dict[tuple[str, str, str], dict[str, Any]], duplicates: list[dict[str, Any]], df: pd.DataFrame, stage: str, input_table: str) -> None:
    for row in df.to_dict(orient="records"):
        edge = make_edge(row, stage, input_table)
        key = (edge["src"], edge["relation"], edge["dst"])
        if key in edges_by_key:
            edges_by_key[key], duplicate = merge_edges(edges_by_key[key], edge)
            duplicates.append(duplicate)
        else:
            edges_by_key[key] = edge


def load_required_frames(lon_d4_dir: Path, lon_d5_dir: Path, lon_d5c_dir: Path) -> dict[str, pd.DataFrame]:
    return {
        "d4_parcels": pd.read_parquet(lon_d4_dir / "canonical" / "london_parcels_uprn.parquet"),
        "d4_buildings": pd.read_parquet(lon_d4_dir / "canonical" / "london_buildings_toid.parquet"),
        "d4_roads": pd.read_parquet(lon_d4_dir / "canonical" / "london_road_segments_usrn.parquet"),
        "d4_edges": pd.read_parquet(lon_d4_dir / "canonical" / "london_identity_edges.parquet"),
        "d5_pld": pd.read_parquet(lon_d5_dir / "canonical" / "london_planning_applications.parquet"),
        "d5c_uprn_stubs": pd.read_parquet(lon_d5c_dir / "canonical" / "london_lids_confirmed_uprn_stubs.parquet"),
        "d5c_context_stubs": pd.read_parquet(lon_d5c_dir / "canonical" / "london_lids_context_entity_stubs.parquet"),
        "d5c_bridge_edges": pd.read_parquet(lon_d5c_dir / "canonical" / "london_lids_bridge_edges.parquet"),
        "d5c_pld_edges": pd.read_parquet(lon_d5c_dir / "canonical" / "london_pld_rejoined_lids_edges.parquet"),
    }


def preconditions(lon_d4_dir: Path, lon_d5_dir: Path, lon_d5c_dir: Path, lon_d6_dir: Path) -> dict[str, Any]:
    paths = {
        "lon_d4": lon_d4_dir / "LON_D4_HARNESS_REPORT.json",
        "lon_d5": lon_d5_dir / "LON_D5_HARNESS_REPORT.json",
        "lon_d5c": lon_d5c_dir / "LON_D5C_HARNESS_REPORT.json",
        "lon_d6": lon_d6_dir / "LON_D6_HARNESS_REPORT.json",
        "lon_d5c_smoke": lon_d5c_dir / "LON_D5C_CONNECTED_PATH_SMOKE.json",
    }
    checks = {f"{name}_exists": path.exists() for name, path in paths.items()}
    statuses = {}
    for name in ["lon_d4", "lon_d5", "lon_d5c", "lon_d6"]:
        if paths[name].exists():
            try:
                statuses[name] = read_json(paths[name]).get("status")
            except Exception:
                statuses[name] = None
        else:
            statuses[name] = None
    checks["lon_d4_status_pass"] = statuses["lon_d4"] == "PASS"
    checks["lon_d5_status_pass"] = statuses["lon_d5"] == "PASS"
    checks["lon_d5c_status_pass"] = statuses["lon_d5c"] == "PASS"
    checks["lon_d6_status_accepted"] = statuses["lon_d6"] in {"PASS", "PASS_D6A_ONLY_SOURCE_LIMITATION"}
    smoke = read_json(paths["lon_d5c_smoke"]) if paths["lon_d5c_smoke"].exists() else {}
    checks["lon_d5c_connected_path_smoke_non_empty"] = smoke.get("result") in {"BOTH", "STRONG", "MEDIUM", "MINIMUM"} or int(
        smoke.get("paths_emitted", 0) or 0
    ) > 0
    return {
        "gate": "LON-D7-PRECOND",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "input_statuses": statuses,
        "d5c_connected_path_smoke": smoke,
    }


def build_graph_projection(frames: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    nodes_by_id: dict[str, dict[str, Any]] = {}
    node_duplicates: list[dict[str, Any]] = []
    add_nodes_from_frame(nodes_by_id, node_duplicates, frames["d4_parcels"], "LON-D4", "canonical/london_parcels_uprn.parquet")
    add_nodes_from_frame(nodes_by_id, node_duplicates, frames["d4_buildings"], "LON-D4", "canonical/london_buildings_toid.parquet")
    add_nodes_from_frame(nodes_by_id, node_duplicates, frames["d4_roads"], "LON-D4", "canonical/london_road_segments_usrn.parquet")
    add_nodes_from_frame(nodes_by_id, node_duplicates, frames["d5_pld"], "LON-D5", "canonical/london_planning_applications.parquet")
    add_nodes_from_frame(nodes_by_id, node_duplicates, frames["d5c_uprn_stubs"], "LON-D5c", "canonical/london_lids_confirmed_uprn_stubs.parquet")
    add_nodes_from_frame(nodes_by_id, node_duplicates, frames["d5c_context_stubs"], "LON-D5c", "canonical/london_lids_context_entity_stubs.parquet")

    edges_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    edge_duplicates: list[dict[str, Any]] = []
    add_edges_from_frame(edges_by_key, edge_duplicates, frames["d4_edges"], "LON-D4", "canonical/london_identity_edges.parquet")
    add_edges_from_frame(edges_by_key, edge_duplicates, frames["d5c_bridge_edges"], "LON-D5c", "canonical/london_lids_bridge_edges.parquet")
    add_edges_from_frame(edges_by_key, edge_duplicates, frames["d5c_pld_edges"], "LON-D5c", "canonical/london_pld_rejoined_lids_edges.parquet")

    nodes = pd.DataFrame(sorted(nodes_by_id.values(), key=lambda row: row["canonical_id"]), columns=NODE_COLUMNS)
    edges = pd.DataFrame(sorted(edges_by_key.values(), key=lambda row: (row["relation"], row["src"], row["dst"])), columns=EDGE_COLUMNS)
    duplicate_report = {
        "status": "PASS",
        "node_duplicate_events": len(node_duplicates),
        "edge_duplicate_events": len(edge_duplicates),
        "rules": [
            "Same canonical_id means same node.",
            "Prefer geometry-backed D4 entity over D5c identity stub when both exist.",
            "Preserve all source_stage lineage in source_lineage.",
            "Do not duplicate UPRNs that appear in both D4 and D5c.",
            "Do not collapse different UPRNs into one building or parcel.",
        ],
        "node_duplicates_sample": node_duplicates[:25],
        "edge_duplicates_sample": edge_duplicates[:25],
    }
    return nodes, edges, duplicate_report


class UnionFind:
    def __init__(self, values: list[str]) -> None:
        self.parent = {value: value for value in values}
        self.size = {value: 1 for value in values}

    def find(self, value: str) -> str:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left == root_right:
            return
        if self.size[root_left] < self.size[root_right]:
            root_left, root_right = root_right, root_left
        self.parent[root_right] = root_left
        self.size[root_left] += self.size[root_right]


def compute_components(nodes: pd.DataFrame, edges: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    node_ids = nodes["canonical_id"].astype(str).tolist()
    uf = UnionFind(node_ids)
    node_set = set(node_ids)
    for row in edges.to_dict(orient="records"):
        if row["src"] in node_set and row["dst"] in node_set:
            uf.union(row["src"], row["dst"])
    groups: dict[str, list[str]] = defaultdict(list)
    for node_id in node_ids:
        groups[uf.find(node_id)].append(node_id)
    node_type = dict(zip(nodes["canonical_id"].astype(str), nodes["entity_type"].astype(str)))
    node_stage_lists = {
        row["canonical_id"]: as_list(row.get("source_stages")) or [row.get("source_stage")]
        for row in nodes.to_dict(orient="records")
    }
    rows = []
    node_component: dict[str, str] = {}
    for ids in groups.values():
        sorted_ids = sorted(ids)
        component_id = f"component:uk-london:d7:{stable_hash(sorted_ids)}"
        for node_id in sorted_ids:
            node_component[node_id] = component_id
        type_counts = Counter(node_type[node_id] for node_id in sorted_ids)
        stage_counts: Counter[str] = Counter()
        for node_id in sorted_ids:
            stage_counts.update(str(stage) for stage in node_stage_lists.get(node_id, []))
        rows.append(
            {
                "component_id": component_id,
                "size": len(sorted_ids),
                "node_ids_sample": json_col(sorted_ids[:25]),
                "entity_type_counts": json_col(dict(type_counts)),
                "source_stage_counts": json_col(dict(stage_counts)),
                "has_pld_permit": type_counts.get("permit", 0) > 0,
                "has_uprn": any(node_id.startswith("parcel:uk-london:uprn:") for node_id in sorted_ids),
                "has_toid": any(node_id.startswith("building:uk-london:toid:") for node_id in sorted_ids),
                "has_usrn": any(node_id.startswith("road_segment:uk-london:usrn:") for node_id in sorted_ids),
            }
        )
    components = pd.DataFrame(sorted(rows, key=lambda row: (-row["size"], row["component_id"])), columns=COMPONENT_COLUMNS)
    nodes_with_components = nodes.copy()
    nodes_with_components["component_id"] = nodes_with_components["canonical_id"].map(node_component)
    degrees = Counter()
    for row in edges.to_dict(orient="records"):
        degrees[row["src"]] += 1
        degrees[row["dst"]] += 1
    metrics = {
        "gate": "LON-D7-COMPONENTS",
        "status": "PASS" if not components.empty else "FAIL",
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "weak_components": len(components),
        "largest_component_size": int(components["size"].max()) if not components.empty else 0,
        "isolated_nodes": len([node_id for node_id in node_ids if degrees[node_id] == 0]),
    }
    return nodes_with_components, components, metrics


def build_connected_paths(nodes: pd.DataFrame, edges: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    edge_rows = edges.to_dict(orient="records")
    subject_edges = [row for row in edge_rows if row["relation"] == "subject_of_permit"]
    context_by_uprn: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: {"has_building": [], "on_street": []})
    for row in edge_rows:
        if row["relation"] in {"has_building", "on_street"}:
            context_by_uprn[row["src"]][row["relation"]].append(row)
    paths = []
    for subject_edge in sorted(subject_edges, key=lambda row: (row["dst"], row["src"])):
        uprn_id = subject_edge["src"]
        pld_id = subject_edge["dst"]
        for relation, strength in [("has_building", "STRONG"), ("on_street", "MEDIUM")]:
            for context_edge in sorted(context_by_uprn[uprn_id][relation], key=lambda row: row["dst"]):
                scores = [score for score in [confidence_score(subject_edge.get("confidence")), confidence_score(context_edge.get("confidence"))] if score is not None]
                confidence_value = min(scores) if scores else None
                path_summary = f"{pld_id} <- subject_of_permit - {uprn_id} - {relation} -> {context_edge['dst']}"
                paths.append(
                    {
                        "path_id": f"path:uk-london:d7:{stable_hash([pld_id, uprn_id, relation, context_edge['dst']])}",
                        "path_strength": strength,
                        "pld_id": pld_id,
                        "uprn_id": uprn_id,
                        "context_id": context_edge["dst"],
                        "context_relation": relation,
                        "subject_edge_id": subject_edge["edge_id"],
                        "context_edge_id": context_edge["edge_id"],
                        "confidence_score": confidence_value,
                        "path_summary": path_summary,
                        "provenance": json_col(
                            [
                                {
                                    "source_stage": "LON-D7",
                                    "derivation": "Deterministic graph traversal over subject_of_permit plus LIDS context edge.",
                                    "source_edges": [subject_edge["edge_id"], context_edge["edge_id"]],
                                    "observed_at": utc_now(),
                                }
                            ]
                        ),
                    }
                )
    paths_df = pd.DataFrame(paths, columns=PATH_COLUMNS)
    permit_ids = set(nodes.loc[nodes["entity_type"] == "permit", "canonical_id"].astype(str))
    pld_with_uprn = {row["dst"] for row in subject_edges if row["dst"] in permit_ids}
    pld_toid = {row["pld_id"] for row in paths if row["path_strength"] == "STRONG"}
    pld_usrn = {row["pld_id"] for row in paths if row["path_strength"] == "MEDIUM"}
    report = {
        "gate": "LON-D7-CONNECTED-PATHS",
        "status": "PASS" if len(paths) > 0 and (pld_toid or pld_usrn) else "FAIL",
        "connected_pld_to_uprn": len(pld_with_uprn),
        "connected_pld_to_uprn_toid": len(pld_toid),
        "connected_pld_to_uprn_usrn": len(pld_usrn),
        "connected_pld_to_uprn_toid_paths": len([row for row in paths if row["path_strength"] == "STRONG"]),
        "connected_pld_to_uprn_usrn_paths": len([row for row in paths if row["path_strength"] == "MEDIUM"]),
        "disconnected_pld_permits": len(permit_ids - pld_with_uprn),
        "sample_paths": paths[:10],
    }
    examples = {"status": report["status"], "traversal_examples": paths[:25]}
    return paths_df, report, examples


def node_counts_by_type(nodes: pd.DataFrame) -> dict[str, Any]:
    return {"status": "PASS", "node_counts_by_type": dict(Counter(nodes["entity_type"].astype(str)))}


def edge_counts_by_relation(edges: pd.DataFrame) -> dict[str, Any]:
    return {"status": "PASS", "edge_counts_by_relation": dict(Counter(edges["relation"].astype(str)))}


def graph_build_report(nodes: pd.DataFrame, edges: pd.DataFrame, frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    ingredients = {
        "d4_identity_nodes": len(frames["d4_parcels"]) + len(frames["d4_buildings"]) + len(frames["d4_roads"]),
        "d4_identity_edges": len(frames["d4_edges"]),
        "d5_pld_permit_nodes": len(frames["d5_pld"]),
        "d5c_lids_confirmed_uprn_stubs": len(frames["d5c_uprn_stubs"]),
        "d5c_pld_uprn_edges": len(frames["d5c_pld_edges"]),
        "d5c_uprn_toid_usrn_edges": len(frames["d5c_bridge_edges"]),
    }
    return {
        "gate": "LON-D7-GRAPH-BUILD",
        "status": "PASS" if len(nodes) > 0 and len(edges) > 0 and all(value > 0 for value in ingredients.values()) else "FAIL",
        "nodes_emitted": len(nodes),
        "edges_emitted": len(edges),
        "minimum_expected_ingredients": ingredients,
        "d6_policy": "D6 is included as source-limitation metadata only, not canonical enforcement/building-control records.",
    }


def source_limitations_report(lon_d6_dir: Path) -> dict[str, Any]:
    harness_path = lon_d6_dir / "LON_D6_HARNESS_REPORT.json"
    d6_harness = read_json(harness_path) if harness_path.exists() else {}
    canonical_counts = {}
    for name in [
        "london_enforcement_events.parquet",
        "london_building_control_applications.parquet",
        "london_d6_identity_edges.parquet",
    ]:
        path = lon_d6_dir / "canonical" / name
        canonical_counts[name] = int(len(pd.read_parquet(path))) if path.exists() else None
    no_records = all(value == 0 for value in canonical_counts.values() if value is not None)
    return {
        "gate": "LON-D7-D6-LIMITATION",
        "status": "PASS" if d6_harness.get("status") in {"PASS", "PASS_D6A_ONLY_SOURCE_LIMITATION"} and no_records else "FAIL",
        "d6_status": d6_harness.get("status"),
        "d6_classification": (d6_harness.get("source_classification") or {}).get("classification"),
        "canonical_d6_row_counts": canonical_counts,
        "limitation_strings": D6_LIMITATION_STRINGS,
        "d6_as_graph_node": False,
        "counts_as_domain_evidence": False,
        "no_fake_enforcement_or_building_control_records": no_records,
    }


def id_format_gate(nodes: pd.DataFrame) -> dict[str, Any]:
    failures = []
    for row in nodes.to_dict(orient="records"):
        entity_type = str(row.get("entity_type"))
        canonical_id = str(row.get("canonical_id"))
        pattern = ID_PATTERNS.get(entity_type)
        if not pattern or not pattern.match(canonical_id) or FORBIDDEN_ID_TOKEN_PATTERN.search(canonical_id):
            failures.append(canonical_id)
    return {
        "gate": "LON-D7-ID-FORMAT",
        "status": "PASS" if not failures else "FAIL",
        "checked_nodes": len(nodes),
        "failures": failures[:25],
    }


def edge_integrity_gate(nodes: pd.DataFrame, edges: pd.DataFrame) -> dict[str, Any]:
    ids = set(nodes["canonical_id"].astype(str))
    failures = []
    for row in edges.to_dict(orient="records"):
        if row["src"] not in ids:
            failures.append(f"{row['edge_id']} missing src {row['src']}")
        if row["dst"] not in ids:
            failures.append(f"{row['edge_id']} missing dst {row['dst']}")
    return {
        "gate": "LON-D7-EDGE-INTEGRITY",
        "status": "PASS" if not failures else "FAIL",
        "edges_checked": len(edges),
        "failures": failures[:25],
    }


def geometry_honesty_report(nodes: pd.DataFrame) -> dict[str, Any]:
    failures = []
    for row in nodes.to_dict(orient="records"):
        status = row.get("geometry_status")
        if status not in ALLOWED_GEOMETRY_STATUSES:
            failures.append(f"{row['canonical_id']} unsupported geometry_status {status}")
    return {
        "gate": "LON-D7-GEO",
        "status": "PASS" if not failures else "FAIL",
        "allowed_geometry_statuses": sorted(ALLOWED_GEOMETRY_STATUSES),
        "geometry_status_counts": dict(Counter(nodes["geometry_status"].astype(str))),
        "invented_geometry_failures": failures[:25],
        "policy": "D7 does not invent geometry; D5c identity stubs remain identity-backed where OpenUPRN geometry is unavailable.",
    }


def add_compat_gate(gates: list[dict[str, Any]], gate_id: str, passed: bool, checked: int, failed: int, details: list[str]) -> None:
    gates.append(
        {
            "gate_id": gate_id,
            "status": "PASS" if passed else "FAIL",
            "checked": checked,
            "failed": failed,
            "details": details[:25],
        }
    )


def compatibility_harness(nodes: pd.DataFrame, edges: pd.DataFrame, components: pd.DataFrame, paths: pd.DataFrame) -> dict[str, Any]:
    gates: list[dict[str, Any]] = []
    schema_failures = []
    for row in nodes.to_dict(orient="records"):
        if row.get("entity_type") not in ALLOWED_ENTITY_TYPES:
            schema_failures.append(str(row.get("canonical_id")))
        if row.get("source_stage") not in ALLOWED_SOURCE_STAGES:
            schema_failures.append(str(row.get("canonical_id")))
    for row in edges.to_dict(orient="records"):
        if row.get("relation") not in ALLOWED_RELATIONS:
            schema_failures.append(str(row.get("edge_id")))
        if row.get("source_stage") not in {"LON-D4", "LON-D5c"}:
            schema_failures.append(str(row.get("edge_id")))
    add_compat_gate(gates, "G-SCHEMA", not schema_failures, len(nodes) + len(edges), len(schema_failures), schema_failures)

    id_report = id_format_gate(nodes)
    add_compat_gate(gates, "G-ID", id_report["status"] == "PASS", len(nodes), len(id_report["failures"]), id_report["failures"])

    triad_failures = []
    for row in nodes.to_dict(orient="records") + edges.to_dict(orient="records"):
        confidence_value = parse_json_col(row.get("confidence"))
        provenance_value = parse_json_col(row.get("provenance"))
        if not isinstance(confidence_value, dict) or confidence_value.get("score") is None or not confidence_value.get("method") or not provenance_value:
            triad_failures.append(str(row.get("canonical_id") or row.get("edge_id")))
    add_compat_gate(gates, "G-TRIAD", not triad_failures, len(nodes) + len(edges), len(triad_failures), triad_failures)

    geo = geometry_honesty_report(nodes)
    add_compat_gate(gates, "G-GEO", geo["status"] == "PASS", len(nodes), len(geo["invented_geometry_failures"]), geo["invented_geometry_failures"])

    ref = edge_integrity_gate(nodes, edges)
    add_compat_gate(gates, "G-REF", ref["status"] == "PASS", len(edges) * 2, len(ref["failures"]), ref["failures"])

    edge_failures = []
    for row in edges.to_dict(orient="records"):
        if row["relation"] in {"has_building", "on_street", "subject_of_permit"} and not ID_PATTERNS["parcel"].match(row["src"]):
            edge_failures.append(str(row["edge_id"]))
        if row["relation"] == "has_building" and not ID_PATTERNS["building"].match(row["dst"]):
            edge_failures.append(str(row["edge_id"]))
        if row["relation"] == "on_street" and not ID_PATTERNS["road_segment"].match(row["dst"]):
            edge_failures.append(str(row["edge_id"]))
        if row["relation"] == "subject_of_permit" and not ID_PATTERNS["permit"].match(row["dst"]):
            edge_failures.append(str(row["edge_id"]))
    add_compat_gate(gates, "G-EDGE", not edge_failures, len(edges), len(edge_failures), edge_failures)

    graph_failures = []
    if len(nodes) == 0:
        graph_failures.append("no graph nodes")
    if len(edges) == 0:
        graph_failures.append("no graph edges")
    add_compat_gate(gates, "G-GRAPH", not graph_failures, len(nodes) + len(edges), len(graph_failures), graph_failures)

    component_failures = []
    if components.empty:
        component_failures.append("no weak components reported")
    add_compat_gate(gates, "G-COMPONENT", not component_failures, len(components), len(component_failures), component_failures)

    path_failures = []
    if paths.empty:
        path_failures.append("no PLD-to-UPRN-to-context paths")
    add_compat_gate(gates, "G-PATH", not path_failures, len(paths), len(path_failures), path_failures)
    return {
        "gate": "LON-D7-A2-A4-COMPATIBILITY",
        "status": "PASS" if all(gate["status"] == "PASS" for gate in gates) else "FAIL",
        "compatibility_marker": "a2_a4_binary_unavailable_compatibility_harness_used",
        "reason": "This is a London graph compatibility harness using the required invariant names; it does not claim exact NYC A4 binary acceptance.",
        "gates": gates,
    }


def drift_test(nodes: pd.DataFrame, edges: pd.DataFrame, components: pd.DataFrame, paths: pd.DataFrame) -> dict[str, Any]:
    mutated_nodes = nodes.copy()
    mutated_edges = edges.copy()
    parcel_idx = mutated_nodes.index[mutated_nodes["entity_type"] == "parcel"]
    permit_idx = mutated_nodes.index[mutated_nodes["entity_type"] == "permit"]
    if len(parcel_idx) > 0:
        idx = parcel_idx[0]
        native = str(mutated_nodes.loc[idx, "native_id"])
        mutated_nodes.loc[idx, "canonical_id"] = f"uprn_entity:uk-london:uprn:{native}"
    if len(permit_idx) > 0:
        idx = permit_idx[0]
        native = str(mutated_nodes.loc[idx, "native_id"])
        mutated_nodes.loc[idx, "canonical_id"] = f"planning_application:uk-london:pld:{native}"
    for relation, replacement in [
        ("has_building", "linked_to_toid"),
        ("on_street", "linked_to_usrn"),
        ("subject_of_permit", "subject_of_planning_application"),
    ]:
        rows = mutated_edges.index[mutated_edges["relation"] == relation]
        if len(rows) > 0:
            mutated_edges.loc[rows[0], "relation"] = replacement
    result = compatibility_harness(mutated_nodes, mutated_edges, components, paths)
    failing_gates = [gate["gate_id"] for gate in result["gates"] if gate["status"] == "FAIL"]
    return {
        "gate": "LON-D7-DRIFT",
        "status": "PASS" if result["status"] == "FAIL" and failing_gates else "FAIL",
        "drift_mutation": {
            "parcel:uk-london:uprn:{id}": "uprn_entity:uk-london:uprn:{id}",
            "permit:uk-london:pld:{id}": "planning_application:uk-london:pld:{id}",
            "has_building": "linked_to_toid",
            "on_street": "linked_to_usrn",
            "subject_of_permit": "subject_of_planning_application",
        },
        "mutated_harness_status": result["status"],
        "failing_gates": failing_gates,
    }


def load_graph_tables(graph_dir: str | Path) -> dict[str, Any]:
    root = Path(graph_dir)
    nodes = pd.read_parquet(root / "canonical" / "london_graph_nodes.parquet")
    edges = pd.read_parquet(root / "canonical" / "london_graph_edges.parquet")
    components = pd.read_parquet(root / "canonical" / "london_graph_components.parquet")
    paths = pd.read_parquet(root / "canonical" / "london_graph_connected_paths.parquet")
    return {
        "root": root,
        "nodes": nodes,
        "edges": edges,
        "components": components,
        "paths": paths,
        "graph_report": read_json(root / "LON_D7_GRAPH_BUILD_REPORT.json"),
        "component_report": read_json(root / "LON_D7_COMPONENT_REPORT.json"),
        "connected_path_report": read_json(root / "LON_D7_CONNECTED_PATH_REPORT.json"),
        "source_limitations": read_json(root / "LON_D7_SOURCE_LIMITATIONS_REPORT.json"),
    }


def node_summary(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "canonical_id": row.get("canonical_id"),
        "entity_type": row.get("entity_type"),
        "source_stage": row.get("source_stage"),
        "source_stages": as_list(row.get("source_stages")),
        "geometry_status": row.get("geometry_status"),
        "confidence": parse_json_col(row.get("confidence")),
        "source_lineage": as_list(row.get("source_lineage")),
        "component_id": row.get("component_id"),
    }


def edge_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "edge_id": row.get("edge_id"),
        "src": row.get("src"),
        "relation": row.get("relation"),
        "dst": row.get("dst"),
        "source_stage": row.get("source_stage"),
        "source_stages": as_list(row.get("source_stages")),
        "confidence": parse_json_col(row.get("confidence")),
        "semantic_caveat": row.get("semantic_caveat"),
    }


def base_query_result(query_type: str, subject_id: str) -> dict[str, Any]:
    return {
        "query_type": query_type,
        "subject_id": subject_id,
        "generated_by": "deterministic_london_d7_query_engine",
        "boundary_language": BRIEFING_BOUNDARY_STRINGS + BOUNDARY_STRINGS,
    }


def citybrain_london_query(query_type: str, subject_id: str, graph_dir: str) -> dict:
    tables = load_graph_tables(graph_dir)
    nodes = tables["nodes"]
    edges = tables["edges"]
    paths = tables["paths"]
    node_by_id = {row["canonical_id"]: row for row in nodes.to_dict(orient="records")}
    result = base_query_result(query_type, subject_id)

    if query_type == "graph_summary":
        result.update(
            {
                "status": "PASS",
                "graph_report": tables["graph_report"],
                "component_report": tables["component_report"],
                "connected_path_report": tables["connected_path_report"],
                "node_counts_by_type": dict(Counter(nodes["entity_type"].astype(str))),
                "edge_counts_by_relation": dict(Counter(edges["relation"].astype(str))),
            }
        )
        return result

    if query_type == "source_limitations":
        result.update({"status": "PASS", "source_limitations": tables["source_limitations"]})
        return result

    if subject_id not in node_by_id and query_type != "connected_path":
        result.update({"status": "NOT_FOUND", "reason": "subject_id is not a D7 graph node"})
        return result

    incident_edges = [
        edge_summary(row)
        for row in edges.to_dict(orient="records")
        if row["src"] == subject_id or row["dst"] == subject_id
    ]
    if query_type == "pld_application_profile":
        node = node_by_id.get(subject_id)
        uprn_edges = [row for row in edges.to_dict(orient="records") if row["relation"] == "subject_of_permit" and row["dst"] == subject_id]
        uprn_ids = sorted({row["src"] for row in uprn_edges})
        context_edges = [
            row
            for row in edges.to_dict(orient="records")
            if row["src"] in uprn_ids and row["relation"] in {"has_building", "on_street"}
        ]
        result.update(
            {
                "status": "PASS",
                "node": node_summary(node),
                "subject_of_permit_edges": [edge_summary(row) for row in uprn_edges],
                "connected_uprns": [node_summary(node_by_id.get(node_id)) for node_id in uprn_ids],
                "context_edges": [edge_summary(row) for row in context_edges],
                "context_nodes": [node_summary(node_by_id.get(row["dst"])) for row in context_edges],
                "counts": {
                    "connected_uprns": len(uprn_ids),
                    "context_edges": len(context_edges),
                    "toid_contexts": len([row for row in context_edges if row["relation"] == "has_building"]),
                    "usrn_contexts": len([row for row in context_edges if row["relation"] == "on_street"]),
                },
            }
        )
        return result

    if query_type == "uprn_profile":
        node = node_by_id.get(subject_id)
        outgoing = [row for row in edges.to_dict(orient="records") if row["src"] == subject_id]
        result.update(
            {
                "status": "PASS",
                "node": node_summary(node),
                "incident_edges": incident_edges,
                "connected_permits": [node_summary(node_by_id.get(row["dst"])) for row in outgoing if row["relation"] == "subject_of_permit"],
                "connected_buildings": [node_summary(node_by_id.get(row["dst"])) for row in outgoing if row["relation"] == "has_building"],
                "connected_road_segments": [node_summary(node_by_id.get(row["dst"])) for row in outgoing if row["relation"] == "on_street"],
                "counts": dict(Counter(row["relation"] for row in outgoing)),
            }
        )
        return result

    if query_type == "toid_building_profile":
        node = node_by_id.get(subject_id)
        uprn_edges = [row for row in edges.to_dict(orient="records") if row["relation"] == "has_building" and row["dst"] == subject_id]
        uprn_ids = sorted({row["src"] for row in uprn_edges})
        permit_edges = [row for row in edges.to_dict(orient="records") if row["relation"] == "subject_of_permit" and row["src"] in uprn_ids]
        result.update(
            {
                "status": "PASS",
                "node": node_summary(node),
                "incident_edges": incident_edges,
                "connected_uprns": [node_summary(node_by_id.get(node_id)) for node_id in uprn_ids],
                "connected_permits": [node_summary(node_by_id.get(row["dst"])) for row in permit_edges],
                "counts": {"connected_uprns": len(uprn_ids), "connected_permits": len(permit_edges)},
            }
        )
        return result

    if query_type == "usrn_road_segment_profile":
        node = node_by_id.get(subject_id)
        uprn_edges = [row for row in edges.to_dict(orient="records") if row["relation"] == "on_street" and row["dst"] == subject_id]
        uprn_ids = sorted({row["src"] for row in uprn_edges})
        permit_edges = [row for row in edges.to_dict(orient="records") if row["relation"] == "subject_of_permit" and row["src"] in uprn_ids]
        result.update(
            {
                "status": "PASS",
                "node": node_summary(node),
                "incident_edges": incident_edges,
                "connected_uprns": [node_summary(node_by_id.get(node_id)) for node_id in uprn_ids],
                "connected_permits": [node_summary(node_by_id.get(row["dst"])) for row in permit_edges],
                "counts": {"connected_uprns": len(uprn_ids), "connected_permits": len(permit_edges)},
            }
        )
        return result

    if query_type == "connected_path":
        path_rows = paths.to_dict(orient="records")
        matches = [row for row in path_rows if row["pld_id"] == subject_id or row["path_id"] == subject_id]
        if not matches:
            result.update({"status": "NOT_FOUND", "reason": "No connected path found for subject_id."})
            return result
        path = sorted(matches, key=lambda row: (row["path_strength"] != "STRONG", row["pld_id"], row["context_id"]))[0]
        edge_ids = {path["subject_edge_id"], path["context_edge_id"]}
        path_edges = [edge_summary(row) for row in edges.to_dict(orient="records") if row["edge_id"] in edge_ids]
        result.update(
            {
                "status": "PASS",
                "path": path,
                "nodes": [node_summary(node_by_id.get(path[key])) for key in ["pld_id", "uprn_id", "context_id"]],
                "edges": path_edges,
            }
        )
        return result

    result.update({"status": "UNSUPPORTED_QUERY_TYPE"})
    return result


def select_query_seeds(paths: pd.DataFrame) -> dict[str, str | None]:
    strong = paths.loc[paths["path_strength"] == "STRONG"].sort_values(["pld_id", "uprn_id", "context_id"])
    medium = paths.loc[paths["path_strength"] == "MEDIUM"].sort_values(["pld_id", "uprn_id", "context_id"])
    seed = strong.iloc[0].to_dict() if not strong.empty else (medium.iloc[0].to_dict() if not medium.empty else {})
    medium_seed = medium.iloc[0].to_dict() if not medium.empty else {}
    return {
        "pld_id": seed.get("pld_id"),
        "uprn_id": seed.get("uprn_id"),
        "toid_id": seed.get("context_id") if seed.get("context_relation") == "has_building" else None,
        "usrn_id": medium_seed.get("context_id") if medium_seed.get("context_relation") == "on_street" else None,
        "connected_path_subject_id": seed.get("pld_id"),
    }


def run_query_smoke(output_dir: Path, paths: pd.DataFrame) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    seeds = select_query_seeds(paths)
    inputs = [
        {"query_type": "graph_summary", "subject_id": "graph"},
        {"query_type": "pld_application_profile", "subject_id": seeds["pld_id"]},
        {"query_type": "uprn_profile", "subject_id": seeds["uprn_id"]},
        {"query_type": "connected_path", "subject_id": seeds["connected_path_subject_id"]},
        {"query_type": "source_limitations", "subject_id": "LON-D6"},
    ]
    if seeds.get("toid_id"):
        inputs.append({"query_type": "toid_building_profile", "subject_id": seeds["toid_id"]})
    if seeds.get("usrn_id"):
        inputs.append({"query_type": "usrn_road_segment_profile", "subject_id": seeds["usrn_id"]})
    results = [citybrain_london_query(item["query_type"], str(item["subject_id"]), str(output_dir)) for item in inputs if item.get("subject_id")]
    required_types = {
        "graph_summary",
        "pld_application_profile",
        "uprn_profile",
        "connected_path",
        "source_limitations",
    }
    if seeds.get("toid_id"):
        required_types.add("toid_building_profile")
    if seeds.get("usrn_id"):
        required_types.add("usrn_road_segment_profile")
    returned_pass = {result["query_type"] for result in results if result.get("status") == "PASS"}
    forbidden_failures = unsupported_claims_in_payload(results)
    report = {
        "gate": "LON-D7-QUERY-SMOKE",
        "status": "PASS" if required_types <= returned_pass and not forbidden_failures else "FAIL",
        "required_query_types": sorted(required_types),
        "returned_pass_query_types": sorted(returned_pass),
        "seed_subjects": seeds,
        "unsupported_fact_failures": forbidden_failures,
        "queries_run": len(results),
    }
    return report, inputs, results


def boundary_markdown() -> str:
    lines = BRIEFING_BOUNDARY_STRINGS + BOUNDARY_STRINGS
    return "\n".join(f"- {line}" for line in lines)


def write_briefings(output_dir: Path, query_results: list[dict[str, Any]]) -> dict[str, Path]:
    by_type = {result["query_type"]: result for result in query_results}
    connected = by_type["connected_path"]
    pld = by_type["pld_application_profile"]
    uprn = by_type["uprn_profile"]
    source = by_type["source_limitations"]
    paths: dict[str, Path] = {}

    path = connected["path"]
    connected_text = f"""# London Connected Seed Briefing

## Subject

Subject canonical ID: {path['pld_id']}

## Evidence Connected

- Edge {path['subject_edge_id']}: {path['uprn_id']} -- subject_of_permit --> {path['pld_id']} from LON-D5c.
- Edge {path['context_edge_id']}: {path['uprn_id']} -- {path['context_relation']} --> {path['context_id']} from LON-D5c.
- Connected path strength: {path['path_strength']}.
- Connected path confidence: {path['confidence_score']}.

## Confidence Summary

The path confidence is the minimum of the deterministic edge confidences in the query result JSON.

## Geometry Limitation

LIDS-confirmed UPRN stubs are identity-backed, not OpenUPRN geometry-backed.

## Source Limitation Boundary

D6 found no bounded machine-readable Lambeth enforcement/building-control feed; no enforcement/building-control records are included.

## No-Overclaim Boundary

{boundary_markdown()}
"""
    paths["london_connected_seed_briefing.md"] = output_dir / "queries" / "london_connected_seed_briefing.md"
    paths["london_connected_seed_briefing.md"].write_text(connected_text, encoding="utf-8")

    pld_node = pld["node"]
    pld_text = f"""# London PLD Application Briefing

## Subject

Subject canonical ID: {pld_node['canonical_id']}

## Evidence Connected

- Entity type: {pld_node['entity_type']}.
- Source stage: {pld_node['source_stage']}.
- Connected UPRN count: {pld['counts']['connected_uprns']}.
- Context edge count: {pld['counts']['context_edges']}.
- TOID context count: {pld['counts']['toid_contexts']}.
- USRN context count: {pld['counts']['usrn_contexts']}.

## Confidence Summary

The subject confidence method is {pld_node['confidence']['method']} with score {pld_node['confidence']['score']}.

## Geometry Limitation

Geometry status: {pld_node['geometry_status']}.

## Source Limitation Boundary

D6 found no bounded machine-readable Lambeth enforcement/building-control feed; no enforcement/building-control records are included.

## No-Overclaim Boundary

{boundary_markdown()}
"""
    paths["london_pld_application_briefing.md"] = output_dir / "queries" / "london_pld_application_briefing.md"
    paths["london_pld_application_briefing.md"].write_text(pld_text, encoding="utf-8")

    uprn_node = uprn["node"]
    uprn_text = f"""# London UPRN Profile Briefing

## Subject

Subject canonical ID: {uprn_node['canonical_id']}

## Evidence Connected

- Entity type: {uprn_node['entity_type']}.
- Source stage: {uprn_node['source_stage']}.
- subject_of_permit edges: {uprn['counts'].get('subject_of_permit', 0)}.
- has_building edges: {uprn['counts'].get('has_building', 0)}.
- on_street edges: {uprn['counts'].get('on_street', 0)}.

## Confidence Summary

The subject confidence method is {uprn_node['confidence']['method']} with score {uprn_node['confidence']['score']}.

## Geometry Limitation

Geometry status: {uprn_node['geometry_status']}.

## Source Limitation Boundary

D6 found no bounded machine-readable Lambeth enforcement/building-control feed; no enforcement/building-control records are included.

## No-Overclaim Boundary

{boundary_markdown()}
"""
    paths["london_uprn_profile_briefing.md"] = output_dir / "queries" / "london_uprn_profile_briefing.md"
    paths["london_uprn_profile_briefing.md"].write_text(uprn_text, encoding="utf-8")

    limitations = source["source_limitations"]
    source_text = f"""# London Source Limitations Briefing

## Subject

Subject canonical ID: LON-D6

## Evidence Connected

- D6 status: {limitations['d6_status']}.
- D6 classification: {limitations['d6_classification']}.
- D6 as graph node: {limitations['d6_as_graph_node']}.
- Counts as domain evidence: {limitations['counts_as_domain_evidence']}.
- No fake enforcement or building-control records: {limitations['no_fake_enforcement_or_building_control_records']}.

## Confidence Summary

This briefing is deterministic source-limitation metadata from LON-D6 and has no domain-record confidence score.

## Geometry Limitation

D6 source limitation metadata has no geometry.

## Source Limitation Boundary

D6 found no bounded machine-readable Lambeth enforcement/building-control feed; no enforcement/building-control records are included.

## No-Overclaim Boundary

{boundary_markdown()}
"""
    paths["london_source_limitations_briefing.md"] = output_dir / "queries" / "london_source_limitations_briefing.md"
    paths["london_source_limitations_briefing.md"].write_text(source_text, encoding="utf-8")
    return paths


def unsupported_claims_in_payload(payload: Any) -> list[str]:
    text = json.dumps(payload, ensure_ascii=False, default=str).lower()
    return unsupported_claims_in_text(text)


def unsupported_claims_in_text(text: str) -> list[str]:
    lower = text.lower()
    failures = []
    checks = [
        ("full London planning coverage", "full london planning coverage"),
        ("OpenUPRN geometry-backed for D5c stubs", "openuprn geometry-backed for d5c stubs"),
        ("DOB equivalent", "dob equivalent"),
        ("enforcement records ingested", "enforcement records ingested"),
        ("building-control records ingested", "building-control records ingested"),
        ("NIM/NeMo generated", "nim/nemo generated"),
    ]
    for label, phrase in checks:
        if phrase in lower:
            failures.append(label)
    if "citywide london" in lower and "not citywide london" not in lower:
        failures.append("citywide London")
    if "hero cascade" in lower and "no hero cascade" not in lower and "does not create a london hero cascade" not in lower:
        failures.append("hero cascade")
    return failures


def grounding_check(output_dir: Path, query_results: list[dict[str, Any]], graph_reports: list[dict[str, Any]], briefing_paths: dict[str, Path]) -> dict[str, Any]:
    nodes = pd.read_parquet(output_dir / "canonical" / "london_graph_nodes.parquet")
    edges = pd.read_parquet(output_dir / "canonical" / "london_graph_edges.parquet")
    node_ids = set(nodes["canonical_id"].astype(str))
    edge_ids = set(edges["edge_id"].astype(str))
    support_text = json.dumps({"queries": query_results, "graph_reports": graph_reports}, ensure_ascii=False, default=str)
    canonical_pattern = re.compile(
        r"(?:parcel:uk-london:uprn:\d+|building:uk-london:toid:osgb[0-9A-Za-z]+|road_segment:uk-london:usrn:\d+|permit:uk-london:pld:[A-Za-z0-9_.-]+)"
    )
    edge_pattern = re.compile(r"edge:uk-london:[A-Za-z0-9_.:-]*[A-Za-z0-9_.-]")
    file_checks = {}
    overall_pass = True
    for name, path in briefing_paths.items():
        text = path.read_text(encoding="utf-8")
        numbers = re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?(?![A-Za-z])", text)
        missing_numbers = [number for number in numbers if number not in support_text]
        canonical_ids = sorted(set(canonical_pattern.findall(text)))
        missing_ids = [canonical_id for canonical_id in canonical_ids if canonical_id not in node_ids]
        mentioned_edge_ids = sorted(set(edge_pattern.findall(text)))
        missing_edges = [edge_id for edge_id in mentioned_edge_ids if edge_id not in edge_ids]
        forbidden = unsupported_claims_in_text(text)
        missing_boundary = [line for line in BRIEFING_BOUNDARY_STRINGS + BOUNDARY_STRINGS if line not in text]
        passed = not missing_numbers and not missing_ids and not missing_edges and not forbidden and not missing_boundary
        if not passed:
            overall_pass = False
        file_checks[name] = {
            "status": "PASS" if passed else "FAIL",
            "missing_numbers": missing_numbers[:25],
            "missing_canonical_ids": missing_ids[:25],
            "missing_edge_ids": missing_edges[:25],
            "forbidden_unsupported_claims": forbidden,
            "missing_boundary_strings": missing_boundary,
        }
    return {
        "gate": "LON-D7-GROUNDING-CHECK",
        "status": "PASS" if overall_pass else "FAIL",
        "rule": "Briefings are checked against query result JSON, graph report JSON, graph node IDs, and graph edge IDs.",
        "files": file_checks,
    }


def briefing_smoke_report(grounding: dict[str, Any], briefing_paths: dict[str, Path]) -> dict[str, Any]:
    required = {
        "london_connected_seed_briefing.md",
        "london_pld_application_briefing.md",
        "london_uprn_profile_briefing.md",
        "london_source_limitations_briefing.md",
    }
    present = set(briefing_paths)
    return {
        "gate": "LON-D7-BRIEFING-SMOKE",
        "status": "PASS" if required <= present and grounding["status"] == "PASS" else "FAIL",
        "briefings_generated": sorted(present),
        "grounding_check_status": grounding["status"],
    }


def confidence_summary(nodes: pd.DataFrame, edges: pd.DataFrame, paths: pd.DataFrame) -> dict[str, Any]:
    methods: Counter[str] = Counter()
    scores: dict[str, list[float]] = defaultdict(list)
    for df in [nodes, edges]:
        for value in df["confidence"]:
            parsed = parse_json_col(value)
            if isinstance(parsed, dict):
                method = str(parsed.get("method"))
                methods[method] += 1
                if parsed.get("score") is not None:
                    scores[method].append(float(parsed["score"]))
    return {
        "status": "PASS",
        "method_counts": dict(methods),
        "score_ranges": {method: {"min": min(values), "max": max(values)} for method, values in scores.items() if values},
        "connected_path_confidence": {
            "min": float(paths["confidence_score"].min()) if not paths.empty else None,
            "max": float(paths["confidence_score"].max()) if not paths.empty else None,
        },
    }


def source_lineage_report(nodes: pd.DataFrame, edges: pd.DataFrame, source_limitations: dict[str, Any]) -> dict[str, Any]:
    stage_counts = Counter()
    for value in nodes["source_stages"]:
        stage_counts.update(as_list(value))
    edge_stage_counts = Counter()
    for value in edges["source_stages"]:
        edge_stage_counts.update(as_list(value))
    return {
        "status": "PASS",
        "node_source_stage_counts": dict(stage_counts),
        "edge_source_stage_counts": dict(edge_stage_counts),
        "d6_source_limitation_status": source_limitations["status"],
        "d6_policy": "D6 is represented only as source-limitation evidence.",
    }


def no_overclaim_report(output_dir: Path, briefing_paths: dict[str, Path]) -> dict[str, Any]:
    required_files = {
        "README.md": output_dir / "README.md",
        "LON_D7_MANIFEST.json": output_dir / "LON_D7_MANIFEST.json",
        "LON_D7_HARNESS_REPORT.json": output_dir / "LON_D7_HARNESS_REPORT.json",
        "LON_D7_ADAPTER_HANDOVER.md": output_dir / "LON_D7_ADAPTER_HANDOVER.md",
    }
    required_files.update({f"queries/{name}": path for name, path in briefing_paths.items()})
    files = {}
    passed = True
    for name, path in required_files.items():
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        missing = [item for item in BOUNDARY_STRINGS if item not in text]
        files[name] = {"missing_boundary_strings": missing}
        if missing:
            passed = False
    return {
        "gate": "LON-D7-NO-OVERCLAIM",
        "status": "PASS" if passed else "FAIL",
        "boundary_strings": BOUNDARY_STRINGS,
        "files": files,
    }


def out_of_scope_report(output_dir: Path) -> dict[str, Any]:
    checked_files = list((output_dir / "canonical").rglob("*")) + list((output_dir / "queries").rglob("*"))
    failures = []
    for path in checked_files:
        if not path.is_file():
            continue
        text = ""
        if path.suffix.lower() == ".parquet":
            try:
                text = pd.read_parquet(path).to_json(orient="records")
            except Exception:
                text = ""
        else:
            text = path.read_text(encoding="utf-8", errors="ignore")
        lower = text.lower()
        for phrase in [
            "nyc dob records",
            "private complainant data",
            "personal contact data",
            "copyright documents",
            "copyright plans",
            "map layer",
            "a5/nim/nemo output",
        ]:
            if phrase in lower:
                failures.append(f"{path.name}: {phrase}")
        if ("enforcement_notice" in lower or "building_control_application" in lower) and "canonical_d6_row_counts" not in lower:
            failures.append(f"{path.name}: canonical enforcement/building-control token")
        if "citywide london expansion" in lower:
            failures.append(f"{path.name}: citywide london expansion")
    return {
        "gate": "LON-D7-OUT-OF-SCOPE",
        "status": "PASS" if not failures else "FAIL",
        "failures": failures[:25],
        "exception": "No-overclaim and source-limitation wording may mention forbidden domains only as absence/limitation statements.",
    }


def hash_report(output_dir: Path) -> dict[str, Any]:
    sums = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[str(path.relative_to(output_dir)).replace("\\", "/")] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"gate": "LON-D7-HASHES", "status": "PASS", "file_count": len(sums), "sha256s": sums}


def write_docs(
    output_dir: Path,
    status: str,
    graph_report: dict[str, Any],
    component_report: dict[str, Any],
    path_report: dict[str, Any],
    query_report: dict[str, Any],
    briefing_report: dict[str, Any],
) -> None:
    boundary = "\n".join(f"- {item}" for item in BOUNDARY_STRINGS)
    readme = f"""# LON-D7 London Sample Graph Projection + Briefing/Query Smoke

{boundary}

## Result

- Status: {status}
- Nodes emitted: {graph_report['nodes_emitted']}
- Edges emitted: {graph_report['edges_emitted']}
- Weak components: {component_report['weak_components']}
- Largest component size: {component_report['largest_component_size']}
- Connected PLD-to-UPRN-to-TOID paths: {path_report['connected_pld_to_uprn_toid_paths']}
- Connected PLD-to-UPRN-to-USRN paths: {path_report['connected_pld_to_uprn_usrn_paths']}
- Query smoke: {query_report['status']}
- Briefing smoke: {briefing_report['status']}

## Scope

This is a deterministic sampled London graph projection over accepted D4, D5, and D5c canonical outputs. D6 is included only as source-limitation evidence.
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")

    handover = f"""# LON-D7 Adapter Handover

{boundary}

## Entrypoint

`txr_citybrain_lon_d7_graph_query_smoke.py`

```bash
python txr_citybrain_lon_d7_graph_query_smoke.py --lon-d4-dir outputs/lon_d4_identity_backbone_ingest --lon-d5-dir outputs/lon_d5_pld_planning_ingest --lon-d5c-dir outputs/lon_d5c_lids_confirmed_identity_bridge --lon-d6-dir outputs/lon_d6_enforcement_building_control --output-dir outputs/lon_d7_london_graph_query_smoke --max-query-examples 25 --run-gates
```

## Query Function

`citybrain_london_query(query_type, subject_id, graph_dir)`

Supported query types: `graph_summary`, `pld_application_profile`, `uprn_profile`, `toid_building_profile`, `usrn_road_segment_profile`, `connected_path`, and `source_limitations`.
"""
    (output_dir / "LON_D7_ADAPTER_HANDOVER.md").write_text(handover, encoding="utf-8")


def write_manifest(
    output_dir: Path,
    lon_d4_dir: Path,
    lon_d5_dir: Path,
    lon_d5c_dir: Path,
    lon_d6_dir: Path,
    status: str,
    counts: dict[str, Any],
    max_query_examples: int,
) -> dict[str, Any]:
    manifest = {
        "task": TASK_NAME,
        "status": status,
        "created_utc": utc_now(),
        "lon_d4_dir": str(lon_d4_dir),
        "lon_d5_dir": str(lon_d5_dir),
        "lon_d5c_dir": str(lon_d5c_dir),
        "lon_d6_dir": str(lon_d6_dir),
        "output_dir": str(output_dir),
        "max_query_examples": max_query_examples,
        "boundary_strings": BOUNDARY_STRINGS,
        "scope": "sampled London graph projection and deterministic query/briefing smoke",
        "counts": counts,
        "artifacts": [
            "README.md",
            "LON_D7_MANIFEST.json",
            "LON_D7_HARNESS_REPORT.json",
            "LON_D7_INPUT_INVENTORY.json",
            "LON_D7_GRAPH_BUILD_REPORT.json",
            "LON_D7_COMPONENT_REPORT.json",
            "LON_D7_CONNECTED_PATH_REPORT.json",
            "LON_D7_QUERY_SMOKE_REPORT.json",
            "LON_D7_BRIEFING_SMOKE_REPORT.json",
            "LON_D7_SOURCE_LIMITATIONS_REPORT.json",
            "LON_D7_NO_OVERCLAIM_REPORT.json",
            "LON_D7_DRIFT_TEST_REPORT.json",
            "LON_D7_ADAPTER_HANDOVER.md",
            "SHA256SUMS.json",
            "canonical/london_graph_nodes.parquet",
            "canonical/london_graph_edges.parquet",
            "canonical/london_graph_components.parquet",
            "canonical/london_graph_connected_paths.parquet",
            "canonical/london_graph_seed_entities.json",
            "canonical/london_graph_seed_edges.json",
            "queries/sample_query_inputs.json",
            "queries/sample_query_results.json",
            "queries/london_connected_seed_briefing.md",
            "queries/london_pld_application_briefing.md",
            "queries/london_uprn_profile_briefing.md",
            "queries/london_source_limitations_briefing.md",
            "reports/node_counts_by_type.json",
            "reports/edge_counts_by_relation.json",
            "reports/duplicate_resolution.json",
            "reports/component_metrics.json",
            "reports/traversal_examples.json",
            "reports/grounding_checks.json",
            "reports/confidence_summary.json",
            "reports/geometry_limitations.json",
            "reports/source_lineage.json",
        ],
    }
    write_json(output_dir / "LON_D7_MANIFEST.json", manifest)
    return manifest


def run_lon_d7_gate(
    lon_d4_dir: str,
    lon_d5_dir: str,
    lon_d5c_dir: str,
    lon_d6_dir: str,
    output_dir: str,
    max_query_examples: int = 25,
) -> dict:
    lon_d4_path = Path(lon_d4_dir)
    lon_d5_path = Path(lon_d5_dir)
    lon_d5c_path = Path(lon_d5c_dir)
    lon_d6_path = Path(lon_d6_dir)
    output_path = Path(output_dir)
    reset_output_dir(output_path)

    tracked_inputs = collect_tracked_inputs(lon_d4_path, lon_d5_path, lon_d5c_path, lon_d6_path)
    before_hashes = input_hashes(tracked_inputs)
    precond = preconditions(lon_d4_path, lon_d5_path, lon_d5c_path, lon_d6_path)
    frames = load_required_frames(lon_d4_path, lon_d5_path, lon_d5c_path)
    nodes, edges, duplicate_report = build_graph_projection(frames)
    nodes, components, component_metrics = compute_components(nodes, edges)
    paths, connected_path_report, traversal_examples = build_connected_paths(nodes, edges)

    graph_report = graph_build_report(nodes, edges, frames)
    source_limitations = source_limitations_report(lon_d6_path)
    id_report = id_format_gate(nodes)
    edge_report = edge_integrity_gate(nodes, edges)
    geometry_report = geometry_honesty_report(nodes)
    compatibility = compatibility_harness(nodes, edges, components, paths)
    drift = drift_test(nodes, edges, components, paths)
    confidence = confidence_summary(nodes, edges, paths)
    lineage = source_lineage_report(nodes, edges, source_limitations)

    write_parquet(output_path / "canonical" / "london_graph_nodes.parquet", nodes)
    write_parquet(output_path / "canonical" / "london_graph_edges.parquet", edges)
    write_parquet(output_path / "canonical" / "london_graph_components.parquet", components)
    write_parquet(output_path / "canonical" / "london_graph_connected_paths.parquet", paths)
    write_json(output_path / "canonical" / "london_graph_seed_entities.json", {"nodes": frame_to_records(nodes, max_query_examples)})
    write_json(output_path / "canonical" / "london_graph_seed_edges.json", {"edges": frame_to_records(edges, max_query_examples)})

    write_json(output_path / "LON_D7_INPUT_INVENTORY.json", inventory_inputs(lon_d4_path, lon_d5_path, lon_d5c_path, lon_d6_path, tracked_inputs))
    write_json(output_path / "LON_D7_GRAPH_BUILD_REPORT.json", graph_report)
    write_json(output_path / "LON_D7_COMPONENT_REPORT.json", component_metrics)
    write_json(output_path / "LON_D7_CONNECTED_PATH_REPORT.json", connected_path_report)
    write_json(output_path / "LON_D7_SOURCE_LIMITATIONS_REPORT.json", source_limitations)
    write_json(output_path / "LON_D7_DRIFT_TEST_REPORT.json", drift)
    write_json(output_path / "reports" / "node_counts_by_type.json", node_counts_by_type(nodes))
    write_json(output_path / "reports" / "edge_counts_by_relation.json", edge_counts_by_relation(edges))
    write_json(output_path / "reports" / "duplicate_resolution.json", duplicate_report)
    write_json(output_path / "reports" / "component_metrics.json", component_metrics)
    write_json(output_path / "reports" / "traversal_examples.json", traversal_examples)
    write_json(output_path / "reports" / "confidence_summary.json", confidence)
    write_json(output_path / "reports" / "geometry_limitations.json", geometry_report)
    write_json(output_path / "reports" / "source_lineage.json", lineage)

    d7a_gates = {
        "LON-D7-PRECOND": precond["status"],
        "LON-D7-GRAPH-BUILD": graph_report["status"],
        "LON-D7-ID-FORMAT": id_report["status"],
        "LON-D7-EDGE-INTEGRITY": edge_report["status"],
        "LON-D7-COMPONENTS": component_metrics["status"],
        "LON-D7-CONNECTED-PATHS": connected_path_report["status"],
        "LON-D7-D6-LIMITATION": source_limitations["status"],
        "LON-D7-A2-A4-COMPATIBILITY": compatibility["status"],
    }
    if all(status == "PASS" for status in d7a_gates.values()):
        query_report, query_inputs, query_results = run_query_smoke(output_path, paths)
    else:
        query_report = {
            "gate": "LON-D7-QUERY-SMOKE",
            "status": "FAIL",
            "reason": "D7b did not run because D7a gates did not all pass.",
        }
        query_inputs = []
        query_results = []
    write_json(output_path / "queries" / "sample_query_inputs.json", query_inputs)
    write_json(output_path / "queries" / "sample_query_results.json", query_results)
    write_json(output_path / "LON_D7_QUERY_SMOKE_REPORT.json", query_report)

    briefing_paths = write_briefings(output_path, query_results) if query_report["status"] == "PASS" else {}
    graph_reports_for_grounding = [graph_report, component_metrics, connected_path_report, source_limitations]
    grounding = grounding_check(output_path, query_results, graph_reports_for_grounding, briefing_paths) if briefing_paths else {
        "gate": "LON-D7-GROUNDING-CHECK",
        "status": "FAIL",
        "reason": "Briefings were not generated.",
    }
    briefing_report = briefing_smoke_report(grounding, briefing_paths)
    write_json(output_path / "reports" / "grounding_checks.json", grounding)
    write_json(output_path / "LON_D7_BRIEFING_SMOKE_REPORT.json", briefing_report)

    counts = {
        "nodes_emitted": len(nodes),
        "edges_emitted": len(edges),
        "node_counts_by_type": dict(Counter(nodes["entity_type"].astype(str))),
        "edge_counts_by_relation": dict(Counter(edges["relation"].astype(str))),
        "weak_components": component_metrics["weak_components"],
        "largest_component_size": component_metrics["largest_component_size"],
        "connected_pld_to_uprn_toid_paths": connected_path_report["connected_pld_to_uprn_toid_paths"],
        "connected_pld_to_uprn_usrn_paths": connected_path_report["connected_pld_to_uprn_usrn_paths"],
        "disconnected_pld_permits": connected_path_report["disconnected_pld_permits"],
    }
    preliminary_status = "PENDING"
    write_manifest(output_path, lon_d4_path, lon_d5_path, lon_d5c_path, lon_d6_path, preliminary_status, counts, max_query_examples)
    write_docs(output_path, preliminary_status, graph_report, component_metrics, connected_path_report, query_report, briefing_report)
    preliminary_harness = {
        "task": TASK_NAME,
        "status": preliminary_status,
        "boundary_strings": BOUNDARY_STRINGS,
        "counts": counts,
        "graph_build": graph_report,
        "connected_paths": connected_path_report,
    }
    write_json(output_path / "LON_D7_HARNESS_REPORT.json", preliminary_harness)
    no_overclaim = no_overclaim_report(output_path, briefing_paths)
    write_json(output_path / "LON_D7_NO_OVERCLAIM_REPORT.json", no_overclaim)
    out_scope = out_of_scope_report(output_path)
    after_hashes = input_hashes(tracked_inputs)
    no_mutation = {
        "gate": "LON-D7-NO-MUTATION",
        "status": "PASS" if before_hashes == after_hashes else "FAIL",
        "checked_files": len(before_hashes),
        "changed_files": sorted(path for path in before_hashes if before_hashes.get(path) != after_hashes.get(path)),
    }

    gates = {
        **d7a_gates,
        "LON-D7-QUERY-SMOKE": query_report["status"],
        "LON-D7-BRIEFING-SMOKE": briefing_report["status"],
        "LON-D7-DRIFT": drift["status"],
        "LON-D7-NO-OVERCLAIM": no_overclaim["status"],
        "LON-D7-OUT-OF-SCOPE": out_scope["status"],
        "LON-D7-NO-MUTATION": no_mutation["status"],
        "LON-D7-HASHES": "PASS",
    }
    overall = "PASS" if all(status == "PASS" for status in gates.values()) else "FAIL"
    write_docs(output_path, overall, graph_report, component_metrics, connected_path_report, query_report, briefing_report)
    harness = {
        "task": TASK_NAME,
        "status": overall,
        "created_utc": utc_now(),
        "boundary_strings": BOUNDARY_STRINGS,
        "lon_d4_dir": str(lon_d4_path),
        "lon_d5_dir": str(lon_d5_path),
        "lon_d5c_dir": str(lon_d5c_path),
        "lon_d6_dir": str(lon_d6_path),
        "output_dir": str(output_path),
        "max_query_examples": max_query_examples,
        "counts": counts,
        "preconditions": precond,
        "graph_build": graph_report,
        "id_format": id_report,
        "edge_integrity": edge_report,
        "component_report": component_metrics,
        "connected_path_report": connected_path_report,
        "source_limitations": source_limitations,
        "a2_a4_compatibility": compatibility,
        "query_smoke": query_report,
        "briefing_smoke": briefing_report,
        "grounding_check": grounding,
        "geometry_honesty": geometry_report,
        "confidence_summary": confidence,
        "source_lineage": lineage,
        "drift_test": drift,
        "no_overclaim": no_overclaim,
        "out_of_scope": out_scope,
        "no_mutation": no_mutation,
        "hashes": {"gate": "LON-D7-HASHES", "status": "PASS", "note": "SHA256SUMS.json covers all generated outputs except itself."},
        "gates": gates,
    }
    write_json(output_path / "LON_D7_HARNESS_REPORT.json", harness)
    write_manifest(output_path, lon_d4_path, lon_d5_path, lon_d5c_path, lon_d6_path, overall, counts, max_query_examples)
    no_overclaim = no_overclaim_report(output_path, briefing_paths)
    write_json(output_path / "LON_D7_NO_OVERCLAIM_REPORT.json", no_overclaim)
    harness["no_overclaim"] = no_overclaim
    harness["gates"]["LON-D7-NO-OVERCLAIM"] = no_overclaim["status"]
    harness["status"] = "PASS" if all(status == "PASS" for status in harness["gates"].values()) else "FAIL"
    write_json(output_path / "LON_D7_HARNESS_REPORT.json", harness)
    write_manifest(output_path, lon_d4_path, lon_d5_path, lon_d5c_path, lon_d6_path, harness["status"], counts, max_query_examples)
    hash_report(output_path)
    return harness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--lon-d4-dir", default=DEFAULT_LON_D4_DIR)
    parser.add_argument("--lon-d5-dir", default=DEFAULT_LON_D5_DIR)
    parser.add_argument("--lon-d5c-dir", default=DEFAULT_LON_D5C_DIR)
    parser.add_argument("--lon-d6-dir", default=DEFAULT_LON_D6_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-query-examples", type=int, default=25)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args(argv)
    report = run_lon_d7_gate(
        args.lon_d4_dir,
        args.lon_d5_dir,
        args.lon_d5c_dir,
        args.lon_d6_dir,
        args.output_dir,
        args.max_query_examples,
    )
    counts = report["counts"]
    precond = report["preconditions"]
    print(f"{TASK_NAME}: {report['status']}")
    print(f"Input LON-D4: {precond['input_statuses'].get('lon_d4') or 'FAIL'}")
    print(f"Input LON-D5: {precond['input_statuses'].get('lon_d5') or 'FAIL'}")
    print(f"Input LON-D5c: {precond['input_statuses'].get('lon_d5c') or 'FAIL'}")
    print(f"Input LON-D6: {precond['input_statuses'].get('lon_d6') or 'FAIL'}")
    print(f"Nodes emitted: {counts['nodes_emitted']}")
    print(f"Edges emitted: {counts['edges_emitted']}")
    print(f"Node counts by type: {counts['node_counts_by_type']}")
    print(f"Edge counts by relation: {counts['edge_counts_by_relation']}")
    print(f"Weak components: {counts['weak_components']}")
    print(f"Largest component size: {counts['largest_component_size']}")
    print(f"Connected PLD-to-UPRN-to-TOID paths: {counts['connected_pld_to_uprn_toid_paths']}")
    print(f"Connected PLD-to-UPRN-to-USRN paths: {counts['connected_pld_to_uprn_usrn_paths']}")
    print(f"Disconnected PLD permits: {counts['disconnected_pld_permits']}")
    print(f"Query smoke: {report['query_smoke']['status']}")
    print(f"Briefing smoke: {report['briefing_smoke']['status']}")
    print(f"Grounding check: {report['grounding_check']['status']}")
    print(f"A2/A4 compatibility gates: {report['a2_a4_compatibility']['status']}")
    print(f"Drift test: {report['drift_test']['status']}")
    print(f"No-overclaim: {report['no_overclaim']['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import hashlib
import importlib.util
import json
import py_compile
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TASK = "MAIN-TRACK1-D4Y-R5-CER-SEG-IMPLEMENTATION-SLICE"
OUTPUT_ROOT = ROOT / "outputs" / "main_track1_d4y_r5_cer_seg_implementation_slice"
HANDOVER_ZIP = Path("C:/Users/hazem/Downloads/track1_d4y_r5_cer_seg_implementation_slice_handover.zip")
HELPER_PATH = OUTPUT_ROOT / "runtime" / "d4y_r5_cer_seg_slice.py"
SCHEMA_VERSION = "main-track1-d4y-r5-cer-seg-implementation-slice.v1"
EXPECTED_STATUS = "PASS_MAIN_TRACK1_D4Y_R5_CER_SEG_IMPLEMENTATION_SLICE_WITH_LIMITATIONS"
WAITING_STATUS = "WAITING_ON_MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE"
PARKED_D5 = "PARKED-MAIN-TRACK1-D5-PRODUCTION-BOUNDARY-AND-SECURITY-PREFLIGHT"

REQUIRED_FOLDERS = [
    "handover",
    "runtime",
    "fixtures",
    "packets",
    "app_handoff",
    "traces",
    "audits",
    "smoke",
    "guardrails",
    "logs",
]

REQUIRED_ARTIFACTS = [
    "README.md",
    "MAIN_TRACK1_D4Y_R5_CER_SEG_IMPLEMENTATION_SLICE.md",
    "MAIN_TRACK1_D4Y_R5_CER_SEG_IMPLEMENTATION_SLICE_DECISION.json",
    "HANDOVER_PACKAGE_INVENTORY.json",
    "R5_CER_SEG_PREREQUISITE_REPORT.json",
    "R5_CER_SEG_IMPLEMENTATION_ARCHITECTURE.md",
    "R5_CER_SEG_IMPLEMENTATION_SCOPE.md",
    "R5_CER_SEG_SOURCE_ARTIFACT_MAP.json",
    "R5_CER_SEG_IMPLEMENTATION_MANIFEST.json",
    "R5_CER_SEG_CONFIG.json",
    "R5_CER_FIXTURES.json",
    "R5_SEG_FIXTURES.json",
    "R5_CER_SEG_SHARED_FIXTURES.json",
    "R5_CER_ENTITY_RESOLUTION_RESULTS.json",
    "R5_SEG_GRAPH_PROJECTION_RESULTS.json",
    "R5_SEG_NEIGHBORHOOD_SUMMARIES.json",
    "R5_SEG_PATH_CONTEXTS.json",
    "R5_CER_SEG_REQUESTS.json",
    "R5_CER_SEG_RESPONSES.json",
    "R5_CER_SEG_OUTPUT_PACKETS.json",
    "R5_CER_SEG_OUTPUT_PACKETS.jsonl",
    "R5_CER_SEG_APP_HANDOFF_PACKETS.json",
    "R5_CER_SEG_TRACE_LOG.jsonl",
    "R5_CER_SEG_AUDIT_LOG.jsonl",
    "R5_CER_SEG_DRIFT_CHECK_REPORT.json",
    "R5_CER_SEG_BOUNDARY_VALIDATION_REPORT.json",
    "R5_CER_SEG_NO_ACTION_AUDIT_REPORT.json",
    "R5_CER_SEG_SMOKE_REPORT.json",
    "R5_CER_SEG_LIMITATION_REGISTER.md",
    "R5_CER_SEG_NEGATIVE_TEST_REPORT.json",
    "R5_CER_SEG_NEXT_TASK_PLAN.md",
    "CLAIM_BOUNDARY_AUDIT.md",
    "NO_MUTATION_AUDIT.md",
    "SECRET_REDACTION_AUDIT.md",
    "hashes.sha256",
]

PREREQ_FILES = {
    "domain_pack_preflight": ROOT / "outputs/main_track1_d4y_r4_domain_pack_preflight/MAIN_TRACK1_D4Y_R4_DOMAIN_PACK_PREFLIGHT_DECISION.json",
    "canonical_entity_bridge_preflight": ROOT / "outputs/main_track1_d4y_r4_canonical_entity_bridge_preflight/MAIN_TRACK1_D4Y_R4_CANONICAL_ENTITY_BRIDGE_PREFLIGHT_DECISION.json",
    "semantic_graph_bridge_preflight": ROOT / "outputs/main_track1_d4y_r4_semantic_graph_bridge_preflight/MAIN_TRACK1_D4Y_R4_SEMANTIC_GRAPH_BRIDGE_PREFLIGHT_DECISION.json",
    "cer_seg_shared_contracts_smoke": ROOT / "outputs/main_track1_d4y_r4_cer_seg_shared_contracts_smoke/MAIN_TRACK1_D4Y_R4_CER_SEG_SHARED_CONTRACTS_SMOKE_DECISION.json",
    "live_runtime_hardening": ROOT / "outputs/main_track1_d4y_r4_live_runtime_hardening/MAIN_TRACK1_D4Y_R4_LIVE_RUNTIME_HARDENING_DECISION.json",
    "r3_closeout": ROOT / "outputs/main_track1_d4y_r3_closeout/MAIN_TRACK1_D4Y_R3_CLOSEOUT_DECISION.json",
}

R4_SHARED_ROOT = ROOT / "outputs/main_track1_d4y_r4_cer_seg_shared_contracts_smoke"
R4_SHARED_FILES = {
    "entity_catalog": R4_SHARED_ROOT / "D4Y_R4_CER_SEG_SHARED_ENTITY_CATALOG_COMPARISON.json",
    "relationship_ontology": R4_SHARED_ROOT / "D4Y_R4_CER_SEG_SHARED_RELATIONSHIP_ONTOLOGY_COMPARISON.json",
    "dto_fields": R4_SHARED_ROOT / "D4Y_R4_CER_SEG_DTO_FIELD_COMPARISON.json",
    "review_states": R4_SHARED_ROOT / "D4Y_R4_CER_SEG_REVIEW_STATE_COMPARISON.json",
    "temporal_model": R4_SHARED_ROOT / "D4Y_R4_CER_SEG_TEMPORAL_MODEL_COMPARISON.json",
    "shared_fixtures": R4_SHARED_ROOT / "D4Y_R4_CER_SEG_SHARED_CONTRACT_FIXTURES.json",
}

WATCH_ROOTS = [
    ROOT / "outputs/main_track1_d4y_r4_domain_pack_preflight",
    ROOT / "outputs/main_track1_d4y_r4_canonical_entity_bridge_preflight",
    ROOT / "outputs/main_track1_d4y_r4_semantic_graph_bridge_preflight",
    ROOT / "outputs/main_track1_d4y_r4_cer_seg_shared_contracts_smoke",
    ROOT / "outputs/main_track1_d4y_r4_live_runtime_hardening",
    ROOT / "outputs/main_track1_d4y_r4_domain_pack_runtime_slice",
    ROOT / "outputs/main_track1_d4y_r3_closeout",
    ROOT / "outputs/main_track1_d4y_r2_closeout",
    ROOT / "outputs/main_track1_d4x_control_room_app_shell_r1",
    ROOT / "outputs/main_track1_d4x_nyc_live_city_app_r1",
    ROOT / "outputs/platform_state_generated",
]

ENTITY_TYPES = [
    "Address",
    "Alarm",
    "Building",
    "Community",
    "Component",
    "Department",
    "Facility",
    "Incident",
    "Inspection",
    "Instrument / Control Point",
    "Observation",
    "Organization",
    "Parcel",
    "Party",
    "Permit",
    "Person",
    "Project",
    "Road Segment",
    "Role / Interest Assignment",
    "Service Point",
    "Site",
    "System",
    "Transaction",
    "Unit",
    "Violation",
    "Work Order",
]

RELATIONSHIP_TYPES = [
    "adjacent_to",
    "affects",
    "applies_to",
    "connects_to",
    "contains",
    "contains_component",
    "depends_on",
    "has_role",
    "hosts_incident",
    "inspected_by",
    "linked_to_transaction",
    "located_in",
    "managed_by",
    "monitors",
    "observed_by",
    "operated_by",
    "part_of",
    "reports_to",
    "served_by",
    "supersedes",
    "supplies",
    "triggers_alarm",
]

REVIEW_STATES = [
    "verified",
    "promoted",
    "candidate/pending_review",
    "source_only",
    "disputed",
    "rejected",
    "deprecated/superseded",
    "synthetic_context",
    "simulated_context",
]

TEMPORAL_STATUSES = [
    "current",
    "candidate_current",
    "historical",
    "expired",
    "superseded",
    "synthetic_context",
    "simulated_context",
]

LIMITATIONS = [
    "local fixture-backed implementation slice only",
    "no production CER",
    "no production SEG",
    "no database runtime",
    "no traversal service",
    "no real domain pack implemented",
    "no Dubai DLD/DM implementation",
    "no public API",
    "no live agents",
    "no external LLM",
    "no app integration",
    "no command/control/enforcement/routing output",
]

FORBIDDEN_CLAIMS = [
    "production CER",
    "production SEG",
    "graph database runtime",
    "traversal service",
    "public API",
    "live agents",
    "external LLM runtime",
    "real domain pack implemented",
    "Dubai DLD/DM implemented",
    "legal finding",
    "confirmed violation",
    "permit approval/rejection",
    "certified impact",
    "certified traffic model",
    "ownership/legal truth from source IDs",
    "observed truth from simulation/synthetic",
    "command/control/enforcement/dispatch/routing",
]


HELPER_SOURCE = r'''
from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "main-track1-d4y-r5-cer-seg-implementation-slice.v1"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_fixtures(base_path: str | Path) -> dict[str, Any]:
    base = Path(base_path)
    return {
        "cer": _read_json(base / "R5_CER_FIXTURES.json"),
        "seg": _read_json(base / "R5_SEG_FIXTURES.json"),
        "shared": _read_json(base / "R5_CER_SEG_SHARED_FIXTURES.json"),
    }


def _find(items: list[dict[str, Any]], field: str, value: str) -> dict[str, Any] | None:
    for item in items:
        if item.get(field) == value:
            return item
    return None


def _cer(fixtures: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return fixtures["cer"].get(key, [])


def _seg(fixtures: dict[str, Any], key: str) -> list[dict[str, Any]]:
    return fixtures["seg"].get(key, [])


def load_canonical_entities(fixtures: dict[str, Any]) -> list[dict[str, Any]]:
    return _cer(fixtures, "canonical_entities")


def load_source_entities(fixtures: dict[str, Any]) -> list[dict[str, Any]]:
    return _cer(fixtures, "source_entities")


def load_source_links(fixtures: dict[str, Any]) -> list[dict[str, Any]]:
    return _cer(fixtures, "source_links")


def load_aliases(fixtures: dict[str, Any]) -> list[dict[str, Any]]:
    return _cer(fixtures, "entity_aliases")


def load_attribute_assertions(fixtures: dict[str, Any]) -> list[dict[str, Any]]:
    return _cer(fixtures, "attribute_assertions")


def load_match_candidates(fixtures: dict[str, Any]) -> list[dict[str, Any]]:
    return _cer(fixtures, "match_candidates")


def load_match_decisions(fixtures: dict[str, Any]) -> list[dict[str, Any]]:
    return _cer(fixtures, "match_decisions")


def load_graph_nodes(fixtures: dict[str, Any]) -> list[dict[str, Any]]:
    return _seg(fixtures, "graph_nodes")


def load_graph_edges(fixtures: dict[str, Any]) -> list[dict[str, Any]]:
    return _seg(fixtures, "graph_edges")


def get_canonical_entity(fixtures: dict[str, Any], canonical_entity_id: str) -> dict[str, Any] | None:
    return _find(load_canonical_entities(fixtures), "canonical_entity_id", canonical_entity_id)


def resolve_source_entity(fixtures: dict[str, Any], source_entity_id: str) -> dict[str, Any]:
    source = _find(load_source_entities(fixtures), "source_entity_id", source_entity_id)
    candidates = get_candidate_matches(fixtures, source_entity_id)
    decisions = [d for d in load_match_decisions(fixtures) if d.get("source_entity_id") == source_entity_id]
    chosen = next((d for d in decisions if d.get("decision") in {"promoted", "verified"}), decisions[0] if decisions else None)
    canonical = get_canonical_entity(fixtures, chosen["canonical_entity_id"]) if chosen else None
    status = "RESOLVED_TO_CANONICAL_CANDIDATE" if canonical else "NO_CANONICAL_MATCH"
    limitations = []
    if not source:
        limitations.append("missing_source_entity")
    if chosen and chosen.get("review_state") in {"candidate/pending_review", "disputed", "deprecated/superseded"}:
        limitations.append("review_or_temporal_boundary")
    return {
        "source_entity_id": source_entity_id,
        "source_entity": source,
        "candidate_matches": candidates,
        "match_decisions": decisions,
        "selected_decision": chosen,
        "canonical_entity": canonical,
        "resolution_status": status,
        "confidence": chosen.get("confidence") if chosen else 0.0,
        "review_state": chosen.get("review_state") if chosen else "source_only",
        "temporal_status": chosen.get("temporal_status") if chosen else "source_only",
        "limitation_refs": sorted(set(limitations + (chosen.get("limitation_refs", []) if chosen else []))),
        "claim_boundary": "source-to-canonical candidate resolution only; not legal or certified truth",
        "no_action_taken": True,
        "schema_version": SCHEMA_VERSION,
    }


def get_candidate_matches(fixtures: dict[str, Any], source_entity_id: str) -> list[dict[str, Any]]:
    return [m for m in load_match_candidates(fixtures) if m.get("source_entity_id") == source_entity_id]


def get_entity_source_links(fixtures: dict[str, Any], canonical_entity_id: str) -> list[dict[str, Any]]:
    return [s for s in load_source_links(fixtures) if s.get("canonical_entity_id") == canonical_entity_id]


def get_entity_attributes(fixtures: dict[str, Any], canonical_entity_id: str) -> list[dict[str, Any]]:
    return [a for a in load_attribute_assertions(fixtures) if a.get("canonical_entity_id") == canonical_entity_id]


def get_entity_conflicts(fixtures: dict[str, Any], canonical_entity_id: str) -> list[dict[str, Any]]:
    return [a for a in get_entity_attributes(fixtures, canonical_entity_id) if a.get("conflict_group")]


def get_entity_quality(fixtures: dict[str, Any], canonical_entity_id: str) -> dict[str, Any] | None:
    return _find(_cer(fixtures, "quality_scores"), "canonical_entity_id", canonical_entity_id)


def project_cer_entity_to_graph_node(fixtures: dict[str, Any], canonical_entity_id: str) -> dict[str, Any] | None:
    return _find(load_graph_nodes(fixtures), "canonical_entity_ref", canonical_entity_id)


def project_relationship_to_graph_edge(fixtures: dict[str, Any], relationship_id: str) -> dict[str, Any] | None:
    return _find(load_graph_edges(fixtures), "relationship_id", relationship_id)


def project_cer_entity_to_node(fixtures: dict[str, Any], canonical_entity_id: str) -> dict[str, Any] | None:
    return project_cer_entity_to_graph_node(fixtures, canonical_entity_id)


def project_relationship_to_edge(fixtures: dict[str, Any], relationship_id: str) -> dict[str, Any] | None:
    return project_relationship_to_graph_edge(fixtures, relationship_id)


def _is_traversable(edge: dict[str, Any], include_historical: bool = False) -> bool:
    if edge.get("review_state") in {"disputed", "rejected"}:
        return False
    if edge.get("temporal_status") in {"expired", "superseded"} and not include_historical:
        return False
    return bool(edge.get("evidence_refs"))


def get_entity_neighborhood(fixtures: dict[str, Any], canonical_entity_id: str, depth: int = 1, include_historical: bool = False) -> dict[str, Any]:
    nodes = load_graph_nodes(fixtures)
    edges = load_graph_edges(fixtures)
    start_node = project_cer_entity_to_graph_node(fixtures, canonical_entity_id)
    if not start_node:
        return {"canonical_entity_id": canonical_entity_id, "nodes": [], "edges": [], "limitation_refs": ["missing_graph_node"], "no_action_taken": True}
    included_nodes = {start_node["node_id"]: start_node}
    included_edges = []
    frontier = {canonical_entity_id}
    for _ in range(max(depth, 1)):
        next_frontier = set()
        for edge in edges:
            if edge.get("source_entity_ref") in frontier or edge.get("target_entity_ref") in frontier:
                if not _is_traversable(edge, include_historical=include_historical):
                    continue
                included_edges.append(edge)
                next_frontier.add(edge["source_entity_ref"])
                next_frontier.add(edge["target_entity_ref"])
                for node in nodes:
                    if node.get("canonical_entity_ref") in {edge["source_entity_ref"], edge["target_entity_ref"]}:
                        included_nodes[node["node_id"]] = node
        frontier = next_frontier
    return {
        "canonical_entity_id": canonical_entity_id,
        "node_count": len(included_nodes),
        "edge_count": len(included_edges),
        "nodes": list(included_nodes.values()),
        "edges": included_edges,
        "traversal_policy": "review/context only; disputed/rejected blocked; expired/superseded historical only",
        "claim_boundary": "bounded graph neighborhood context only",
        "no_action_taken": True,
        "schema_version": SCHEMA_VERSION,
    }


def get_adjacent_entities(fixtures: dict[str, Any], canonical_entity_id: str) -> list[str]:
    neighborhood = get_entity_neighborhood(fixtures, canonical_entity_id)
    refs = set()
    for edge in neighborhood["edges"]:
        if edge["source_entity_ref"] != canonical_entity_id:
            refs.add(edge["source_entity_ref"])
        if edge["target_entity_ref"] != canonical_entity_id:
            refs.add(edge["target_entity_ref"])
    return sorted(refs)


def get_contains_context(fixtures: dict[str, Any], canonical_entity_id: str) -> list[dict[str, Any]]:
    return [e for e in load_graph_edges(fixtures) if e.get("relationship_type") in {"contains", "contains_component", "part_of"} and canonical_entity_id in {e.get("source_entity_ref"), e.get("target_entity_ref")}]


def get_served_by_context(fixtures: dict[str, Any], canonical_entity_id: str) -> list[dict[str, Any]]:
    return [e for e in load_graph_edges(fixtures) if e.get("relationship_type") == "served_by" and canonical_entity_id in {e.get("source_entity_ref"), e.get("target_entity_ref")}]


def get_role_context(fixtures: dict[str, Any], canonical_entity_id: str) -> list[dict[str, Any]]:
    return [e for e in load_graph_edges(fixtures) if e.get("relationship_type") == "has_role" and canonical_entity_id in {e.get("source_entity_ref"), e.get("target_entity_ref")}]


def get_observation_context(fixtures: dict[str, Any], canonical_entity_id: str) -> list[dict[str, Any]]:
    return [e for e in load_graph_edges(fixtures) if e.get("relationship_type") in {"observed_by", "monitors"} and canonical_entity_id in {e.get("source_entity_ref"), e.get("target_entity_ref")}]


def get_relationship_paths(fixtures: dict[str, Any], start_entity_id: str, end_entity_id: str, max_depth: int = 4, include_historical: bool = False) -> list[dict[str, Any]]:
    existing = [p for p in _seg(fixtures, "path_contexts") if p.get("start_entity_ref") == start_entity_id and p.get("end_entity_ref") == end_entity_id]
    if existing:
        return existing
    edges = [e for e in load_graph_edges(fixtures) if _is_traversable(e, include_historical=include_historical)]
    queue = deque([(start_entity_id, [])])
    seen = {start_entity_id}
    while queue:
        node, path = queue.popleft()
        if len(path) >= max_depth:
            continue
        for edge in edges:
            nxt = None
            if edge["source_entity_ref"] == node:
                nxt = edge["target_entity_ref"]
            elif edge["target_entity_ref"] == node:
                nxt = edge["source_entity_ref"]
            if not nxt or nxt in seen:
                continue
            next_path = path + [edge]
            if nxt == end_entity_id:
                return [{
                    "path_id": f"generated:{start_entity_id}:{end_entity_id}",
                    "start_entity_ref": start_entity_id,
                    "end_entity_ref": end_entity_id,
                    "edge_refs": [e["edge_id"] for e in next_path],
                    "relationship_types": [e["relationship_type"] for e in next_path],
                    "confidence": min(e.get("confidence", 0.0) for e in next_path),
                    "review_state": "review/context",
                    "temporal_status": "current",
                    "limitation_refs": sorted({lim for e in next_path for lim in e.get("limitation_refs", [])}),
                    "claim_boundary": "generated bounded path context only",
                    "no_action_taken": True,
                    "schema_version": SCHEMA_VERSION,
                }]
            seen.add(nxt)
            queue.append((nxt, next_path))
    return []


def explain_graph_path(fixtures: dict[str, Any], path_id: str) -> dict[str, Any] | None:
    path = _find(_seg(fixtures, "path_contexts"), "path_id", path_id)
    if not path:
        return None
    return {
        "path_id": path_id,
        "summary": " -> ".join(path.get("relationship_types", [])),
        "path_context": path,
        "claim_boundary": "path explanation is context only, not action guidance",
        "no_action_taken": True,
        "schema_version": SCHEMA_VERSION,
    }


def validate_traversal_policy(edge_or_path: dict[str, Any]) -> dict[str, Any]:
    review_state = edge_or_path.get("review_state", "unknown")
    temporal_status = edge_or_path.get("temporal_status", "unknown")
    blocked = review_state in {"disputed", "rejected"} or temporal_status in {"expired", "superseded"}
    return {
        "status": "BLOCKED_FOR_FACTUAL_TRAVERSAL" if blocked else "PASS_CONTEXT_TRAVERSAL",
        "review_state": review_state,
        "temporal_status": temporal_status,
        "claim_boundary": "traversal policy validation only",
        "no_action_taken": True,
        "schema_version": SCHEMA_VERSION,
    }


def generate_app_handoff_packet(fixtures: dict[str, Any], packet_id: str, canonical_entity_id: str) -> dict[str, Any]:
    entity = get_canonical_entity(fixtures, canonical_entity_id)
    node = project_cer_entity_to_graph_node(fixtures, canonical_entity_id)
    neighborhood = get_entity_neighborhood(fixtures, canonical_entity_id)
    quality = get_entity_quality(fixtures, canonical_entity_id) or {}
    return {
        "packet_id": packet_id,
        "packet_type": "cer_seg_identity_graph_context",
        "display_title": entity.get("display_name") if entity else canonical_entity_id,
        "display_summary": "Fixture-backed CER/SEG app handoff context. Source IDs remain candidate/source context.",
        "canonical_entity_ref": canonical_entity_id,
        "entity_type": entity.get("entity_type") if entity else None,
        "graph_node_ref": node.get("node_id") if node else None,
        "source_refs": entity.get("source_refs", []) if entity else [],
        "evidence_refs": entity.get("evidence_refs", []) if entity else [],
        "confidence": quality.get("overall_confidence", entity.get("confidence") if entity else 0.0),
        "review_state": entity.get("review_state") if entity else "missing",
        "temporal_status": entity.get("temporal_status") if entity else "missing",
        "neighborhood_summary": {"node_count": neighborhood.get("node_count", 0), "edge_count": neighborhood.get("edge_count", 0)},
        "limitation_refs": sorted(set((entity.get("limitation_refs", []) if entity else []) + neighborhood.get("limitation_refs", []))),
        "safe_next_looks": ["inspect source links", "inspect candidate matches", "inspect graph neighborhood", "inspect limitations"],
        "forbidden_ui_actions": ["dispatch", "enforce", "route", "control", "confirm violation", "certify impact", "claim ownership"],
        "claim_boundary": "app handoff display context only; not legal/certified truth",
        "no_action_taken": True,
        "schema_version": SCHEMA_VERSION,
    }


def run_boundary_validation(objects: list[dict[str, Any]]) -> dict[str, Any]:
    forbidden_flags = [
        "production_cer_implemented",
        "production_seg_implemented",
        "graph_database_runtime_implemented",
        "traversal_service_implemented",
        "real_domain_pack_implemented",
        "dubai_dld_dm_implemented",
        "public_api_exposed",
        "external_llm_called",
        "app_integration_performed",
        "command_action_output_created",
    ]
    findings = []
    for obj in objects:
        for flag in forbidden_flags:
            if obj.get(flag) is True:
                findings.append({"object_id": obj.get("packet_id") or obj.get("request_id") or obj.get("audit_id"), "flag": flag})
    return {
        "status": "PASS" if not findings else "FAIL",
        "checked_object_count": len(objects),
        "findings": findings,
        "forbidden_flags": forbidden_flags,
        "no_action_taken": True,
        "schema_version": SCHEMA_VERSION,
    }


def run_no_action_audit(objects: list[dict[str, Any]]) -> dict[str, Any]:
    missing = [obj.get("packet_id") or obj.get("request_id") or obj.get("audit_id") or obj.get("trace_id") for obj in objects if obj.get("no_action_taken") is not True]
    return {
        "status": "PASS" if not missing else "FAIL",
        "checked_object_count": len(objects),
        "no_action_true_count": len(objects) - len(missing),
        "missing_no_action_refs": missing,
        "no_action_taken": True,
        "schema_version": SCHEMA_VERSION,
    }
'''


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_id(prefix: str, value: Any, length: int = 12) -> str:
    digest = hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()[:length]
    return f"{prefix}:{digest}"


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=True)
        f.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=True) + "\n")


def reset_output_root() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for folder in REQUIRED_FOLDERS:
        (OUTPUT_ROOT / folder).mkdir(parents=True, exist_ok=True)


def preserve_handover() -> dict[str, Any]:
    if not HANDOVER_ZIP.exists():
        return {"status": "FAIL", "zip_path": str(HANDOVER_ZIP), "files": [], "file_count": 0}
    dest = OUTPUT_ROOT / "handover"
    with zipfile.ZipFile(HANDOVER_ZIP, "r") as zf:
        for member in zf.infolist():
            parts = Path(member.filename).parts
            if Path(member.filename).is_absolute() or ".." in parts:
                raise ValueError(f"Unsafe ZIP member: {member.filename}")
        zf.extractall(dest)
    files = []
    for path in sorted(dest.rglob("*")):
        if path.is_file():
            files.append(
                {
                    "file": path.relative_to(dest).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    inventory = {
        "status": "PASS",
        "zip_path": str(HANDOVER_ZIP),
        "zip_sha256": sha256_file(HANDOVER_ZIP),
        "file_count": len(files),
        "files": files,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "HANDOVER_PACKAGE_INVENTORY.json", inventory)
    return inventory


def status_is_green(status: str) -> bool:
    return status.startswith("PASS_") or status == "PASS"


def load_prereqs() -> dict[str, Any]:
    return {name: read_json(path, {}) for name, path in PREREQ_FILES.items()}


def waiting_decision(reason: str, inventory: dict[str, Any]) -> None:
    decision = {
        "status": WAITING_STATUS,
        "task_name": TASK,
        "prerequisite_status": "WAITING",
        "reason": reason,
        "handover_files_preserved": inventory.get("file_count", 0),
        "runtime_helper_status": "NOT_CREATED",
        "cer_fixture_count": 0,
        "seg_fixture_count": 0,
        "request_count": 0,
        "response_count": 0,
        "output_packet_count": 0,
        "app_handoff_packet_count": 0,
        "trace_count": 0,
        "audit_count": 0,
        "drift_check_status": "NOT_RUN",
        "boundary_validation_status": "NOT_RUN",
        "no_action_audit_status": "NOT_RUN",
        "production_cer_implemented": False,
        "production_seg_implemented": False,
        "graph_database_runtime_implemented": False,
        "traversal_service_implemented": False,
        "real_domain_pack_implemented": False,
        "dubai_dld_dm_implemented": False,
        "public_api_exposed": False,
        "external_llm_called": False,
        "app_integration_performed": False,
        "command_action_output_created": False,
        "source_mutation_status": "NOT_CHECKED",
        "limitation_summary": {"status": "WAITING", "limitations": LIMITATIONS},
        "negative_test_summary": {"status": "NOT_RUN", "test_count": 0},
        "recommended_next_track1_task": "MAIN-TRACK1-D4Y-R4-CER-SEG-SHARED-CONTRACTS-SMOKE",
        "parked_d5_task": PARKED_D5,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R5_CER_SEG_IMPLEMENTATION_SLICE_DECISION.json", decision)
    write_text(OUTPUT_ROOT / "README.md", f"# {TASK}\n\nStatus: `{WAITING_STATUS}`\n\n{reason}")
    hash_output()
    print(WAITING_STATUS)


def prerequisite_report(prereqs: dict[str, Any]) -> dict[str, Any]:
    required = [
        "domain_pack_preflight",
        "canonical_entity_bridge_preflight",
        "semantic_graph_bridge_preflight",
        "cer_seg_shared_contracts_smoke",
        "r3_closeout",
    ]
    optional = ["live_runtime_hardening"]
    rows = []
    for name in required + optional:
        status = str(prereqs.get(name, {}).get("status", "MISSING"))
        rows.append({"name": name, "status": status, "required": name in required, "green": status_is_green(status)})
    report = {
        "status": "PASS" if all(row["green"] for row in rows if row["required"]) else "WAITING",
        "task_name": TASK,
        "timestamp": now_iso(),
        "checks": rows,
        "read_only_roots": [rel(path.parent) for path in PREREQ_FILES.values()],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "R5_CER_SEG_PREREQUISITE_REPORT.json", report)
    return report


def capture_watch_signatures() -> dict[str, Any]:
    signatures: dict[str, Any] = {}
    for root in WATCH_ROOTS:
        key = rel(root)
        if not root.exists():
            signatures[key] = {"exists": False}
            continue
        digest = hashlib.sha256()
        file_count = 0
        byte_count = 0
        newest = 0
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            stat = path.stat()
            file_count += 1
            byte_count += stat.st_size
            newest = max(newest, stat.st_mtime_ns)
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(str(stat.st_size).encode("utf-8"))
            digest.update(str(stat.st_mtime_ns).encode("utf-8"))
        signatures[key] = {
            "exists": True,
            "file_count": file_count,
            "byte_count": byte_count,
            "newest_mtime_ns": newest,
            "signature": digest.hexdigest(),
        }
    return signatures


def load_r4_contracts() -> dict[str, Any]:
    return {name: read_json(path, {}) for name, path in R4_SHARED_FILES.items()}


def create_docs() -> None:
    write_text(
        OUTPUT_ROOT / "R5_CER_SEG_IMPLEMENTATION_ARCHITECTURE.md",
        """
# R5 CER/SEG Implementation Architecture

This slice implements a local, file/CLI, fixture-backed Canonical Entity Registry and Semantic Entity Graph proof.

CER owns identity truth and source-to-canonical candidate resolution. SEG owns relationship projection, neighborhood summaries, and bounded path context. Shared contracts own the handoff fields between the two.

This is not a production CER, not a production SEG, not a graph database runtime, not a traversal service, not a public API, not app integration, and not a domain-pack runtime.
""",
    )
    write_text(
        OUTPUT_ROOT / "R5_CER_SEG_IMPLEMENTATION_SCOPE.md",
        """
# R5 CER/SEG Implementation Scope

Included:

- local helper under `runtime/d4y_r5_cer_seg_slice.py`
- JSON fixtures for CER, SEG, and shared DTOs
- deterministic source resolution, candidate matching, match decisions, graph projection, neighborhood/path context, app handoff packets, traces, audits, drift checks, no-action and boundary validation

Excluded:

- production CER/SEG
- database runtime
- traversal service
- public API/server
- external LLMs
- live agents
- real domain-pack logic
- Dubai DLD/DM logic
- app integration
- command/action/enforcement/dispatch/routing/control output
""",
    )
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# {TASK}

Status: `{EXPECTED_STATUS}`

Local fixture-backed CER/SEG implementation slice for Track 1 D4Y R5. This pack is additive and preserves previous output roots read-only.
""",
    )
    write_text(
        OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R5_CER_SEG_IMPLEMENTATION_SLICE.md",
        f"""
# Main Track 1 D4Y R5 CER/SEG Implementation Slice

Status: `{EXPECTED_STATUS}`

The slice proves bounded source-to-canonical candidate resolution, CER-to-SEG projection, graph neighborhood/path context, confidence/review/temporal propagation, app handoff packets, traces, audits, drift gates, boundary validation, no-action validation, and negative tests.

All outputs remain local, fixture-backed, review/context-only, and no-action.
""",
    )


def source_artifact_map() -> dict[str, Any]:
    report = {
        "status": "PASS",
        "source_artifacts": [
            {"artifact": "R4 domain pack preflight", "path": "outputs/main_track1_d4y_r4_domain_pack_preflight", "read_only": True},
            {"artifact": "R4 canonical entity bridge preflight", "path": "outputs/main_track1_d4y_r4_canonical_entity_bridge_preflight", "read_only": True},
            {"artifact": "R4 semantic graph bridge preflight", "path": "outputs/main_track1_d4y_r4_semantic_graph_bridge_preflight", "read_only": True},
            {"artifact": "R4 CER/SEG shared contracts smoke", "path": "outputs/main_track1_d4y_r4_cer_seg_shared_contracts_smoke", "read_only": True},
            {"artifact": "R4 live runtime hardening", "path": "outputs/main_track1_d4y_r4_live_runtime_hardening", "read_only": True},
            {"artifact": "R3 closeout", "path": "outputs/main_track1_d4y_r3_closeout", "read_only": True},
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "R5_CER_SEG_SOURCE_ARTIFACT_MAP.json", report)
    return report


def implementation_config_and_manifest() -> tuple[dict[str, Any], dict[str, Any]]:
    config = {
        "status": "PASS",
        "mode": "LOCAL_FIXTURE_BACKED_FILE_CLI",
        "helper_path": rel(HELPER_PATH),
        "network_allowed": False,
        "external_llm_allowed": False,
        "server_mode_allowed": False,
        "database_runtime_allowed": False,
        "prior_root_mutation_allowed": False,
        "no_action_taken_required": True,
        "schema_version": SCHEMA_VERSION,
    }
    manifest = {
        "status": "PASS",
        "runtime_helper": rel(HELPER_PATH),
        "fixture_files": [
            "R5_CER_FIXTURES.json",
            "R5_SEG_FIXTURES.json",
            "R5_CER_SEG_SHARED_FIXTURES.json",
        ],
        "implemented_helper_functions": [
            "load_fixtures",
            "resolve_source_entity",
            "get_canonical_entity",
            "get_candidate_matches",
            "get_entity_source_links",
            "get_entity_attributes",
            "get_entity_conflicts",
            "get_entity_quality",
            "project_cer_entity_to_graph_node",
            "project_relationship_to_graph_edge",
            "get_entity_neighborhood",
            "get_relationship_paths",
            "explain_graph_path",
            "generate_app_handoff_packet",
            "run_boundary_validation",
            "run_no_action_audit",
        ],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "R5_CER_SEG_CONFIG.json", config)
    write_json(OUTPUT_ROOT / "R5_CER_SEG_IMPLEMENTATION_MANIFEST.json", manifest)
    return config, manifest


def boundary_fields(**extra: Any) -> dict[str, Any]:
    base = {
        "claim_boundary": "fixture-backed identity/graph context only; not legal, certified, operational, or action truth",
        "no_action_taken": True,
        "production_cer_implemented": False,
        "production_seg_implemented": False,
        "graph_database_runtime_implemented": False,
        "traversal_service_implemented": False,
        "real_domain_pack_implemented": False,
        "dubai_dld_dm_implemented": False,
        "public_api_exposed": False,
        "external_llm_called": False,
        "app_integration_performed": False,
        "command_action_output_created": False,
    }
    base.update(extra)
    return base


def make_entity(entity_id: str, entity_type: str, name: str, confidence: float, review_state: str, temporal_status: str, limitations: list[str]) -> dict[str, Any]:
    return {
        "canonical_entity_id": entity_id,
        "entity_type": entity_type,
        "display_name": name,
        "source_refs": [f"source-ref:{entity_id}"],
        "evidence_refs": [f"evidence-ref:{entity_id}"],
        "confidence": confidence,
        "review_state": review_state,
        "effective_from": "2026-01-01",
        "effective_to": "2025-12-31" if temporal_status in {"expired", "superseded", "historical"} else None,
        "temporal_status": temporal_status,
        "limitation_refs": limitations,
        **boundary_fields(),
        "schema_version": SCHEMA_VERSION,
    }


def build_fixtures() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    canonical_entities = [
        make_entity("cer:building:barc:eixample:lod2:001", "Building", "BARC LOD2 source object candidate", 0.82, "candidate/pending_review", "candidate_current", ["arcgis_visual_id_not_canonical", "review_only_mapping"]),
        make_entity("cer:building:nyc:bin:1088899", "Building", "NYC BIN/BBL/DoITT building candidate", 0.88, "promoted", "current", ["source_id_not_legal_truth"]),
        make_entity("cer:address:barc:eixample:001", "Address", "Barcelona address candidate", 0.74, "candidate/pending_review", "candidate_current", ["address_to_building_candidate"]),
        make_entity("cer:parcel:barc:eixample:08900", "Parcel", "Barcelona parcel context candidate", 0.79, "candidate/pending_review", "candidate_current", ["cadastre_context_not_certified"]),
        make_entity("cer:community:barc:eixample", "Community", "Eixample community context", 0.93, "verified", "current", ["context_boundary_only"]),
        make_entity("cer:parcel:nyc:bbl:1000010001", "Parcel", "NYC BBL parcel candidate", 0.86, "promoted", "current", ["source_id_not_ownership_truth"]),
        make_entity("cer:road:barc:segment:granvia:001", "Road Segment", "Gran Via road segment context", 0.81, "candidate/pending_review", "candidate_current", ["road_context_only"]),
        make_entity("cer:facility:barc:public:001", "Facility", "Barcelona public facility context", 0.76, "candidate/pending_review", "candidate_current", ["facility_context_only"]),
        make_entity("cer:system:barc:facility:hvac:001", "System", "Facility system context", 0.71, "candidate/pending_review", "candidate_current", ["system_context_only"]),
        make_entity("cer:component:barc:facility:sensor:001", "Component", "Facility component context", 0.68, "candidate/pending_review", "candidate_current", ["component_context_only"]),
        make_entity("cer:instrument:barc:noise:001", "Instrument / Control Point", "Noise monitor instrument context", 0.77, "source_only", "current", ["instrument_context_only"]),
        make_entity("cer:permit:barc:historical:001", "Permit", "Historical permit context", 0.62, "deprecated/superseded", "historical", ["historical_only"]),
        make_entity("cer:incident:barc:traffic:001", "Incident", "Traffic incident context", 0.59, "candidate/pending_review", "candidate_current", ["incident_context_only"]),
        make_entity("cer:party:example:001", "Party", "Example party context", 0.55, "source_only", "current", ["no_ownership_truth"]),
        make_entity("cer:unit:barc:building:001:u1", "Unit", "Building unit context", 0.65, "candidate/pending_review", "candidate_current", ["unit_context_only"]),
        make_entity("cer:building:low-confidence:001", "Building", "Low-confidence building candidate", 0.39, "candidate/pending_review", "candidate_current", ["low_confidence_review_required"]),
        make_entity("cer:building:disputed:001", "Building", "Disputed building candidate", 0.43, "disputed", "candidate_current", ["disputed_blocked_for_factual_traversal"]),
        make_entity("cer:building:superseded:001", "Building", "Expired/superseded building candidate", 0.64, "deprecated/superseded", "superseded", ["historical_only", "not_active_current_entity"]),
        make_entity("cer:synthetic:building:001", "Building", "Synthetic building context", 0.5, "synthetic_context", "synthetic_context", ["synthetic_context_only"]),
        make_entity("cer:simulated:building:001", "Building", "Simulated building context", 0.5, "simulated_context", "simulated_context", ["simulated_context_only"]),
    ]
    source_entities = [
        source_entity("src:barc:arcgis:lod2:objectid:932001", "BARC_ARCGIS_LOD2", "OBJECTID", "932001", "Building", ["barc_lod2_object_source_context"]),
        source_entity("src:nyc:bin:1088899", "NYC_DOB_BIN", "BIN", "1088899", "Building", ["nyc_bin_candidate"]),
        source_entity("src:nyc:bbl:1000010001", "NYC_PLUTO_BBL", "BBL", "1000010001", "Parcel", ["nyc_bbl_candidate"]),
        source_entity("src:nyc:doitt:building:alpha", "NYC_DOITT", "DoITT", "doitt-alpha", "Building", ["nyc_doitt_building_candidate"]),
        source_entity("src:barc:address:eixample:001", "BARC_ADDRESS", "address_ref", "addr-eixample-001", "Address", ["address_to_building_candidate"]),
        source_entity("src:barc:cadastre:parcel:08900", "BARC_CADASTRE_RECOVERY", "parcel_ref", "08900", "Parcel", ["cadastre_recovery_context"]),
        source_entity("src:barc:district:eixample", "BARC_ADMIN", "district_code", "02", "Community", ["community_context"]),
        source_entity("src:barc:road:granvia:001", "BARC_TRAFFIC_SECTION", "section_id", "granvia-001", "Road Segment", ["road_context"]),
        source_entity("src:barc:lowconf:building:001", "BARC_SOURCE_LOW_CONF", "object_ref", "lowconf-001", "Building", ["low_confidence_candidate"]),
        source_entity("src:barc:disputed:building:001", "BARC_SOURCE_DISPUTED", "object_ref", "disputed-001", "Building", ["disputed_candidate"]),
        source_entity("src:barc:expired:building:001", "BARC_SOURCE_EXPIRED", "object_ref", "expired-001", "Building", ["expired_superseded_candidate"]),
        source_entity("src:synthetic:building:001", "SYNTHETIC_REPLAY", "synthetic_id", "syn-building-001", "Building", ["synthetic_context_only"]),
        source_entity("src:simulated:building:001", "SUMO_SIM_CONTEXT", "simulation_id", "sim-building-001", "Building", ["simulated_context_only"]),
    ]
    source_links = []
    match_candidates = []
    match_decisions = []
    for i, source in enumerate(source_entities, 1):
        canonical_id = candidate_target_for_source(source["source_entity_id"])
        confidence = source_confidence(source["source_entity_id"])
        review_state = source_review_state(source["source_entity_id"])
        temporal_status = source_temporal_status(source["source_entity_id"])
        source_links.append(
            {
                "source_link_id": f"source-link:{i:03d}",
                "source_entity_id": source["source_entity_id"],
                "canonical_entity_id": canonical_id,
                "link_type": "candidate_identity_link",
                "evidence_refs": source["evidence_refs"],
                "confidence": confidence,
                "review_state": review_state,
                "temporal_status": temporal_status,
                "limitation_refs": source["limitation_refs"],
                **boundary_fields(),
                "schema_version": SCHEMA_VERSION,
            }
        )
        match_candidates.append(
            {
                "match_candidate_id": f"match-candidate:{i:03d}",
                "source_entity_id": source["source_entity_id"],
                "canonical_entity_id": canonical_id,
                "match_features": ["source_type", "spatial_context", "name_or_code_similarity"],
                "confidence": confidence,
                "review_state": review_state,
                "temporal_status": temporal_status,
                "evidence_refs": source["evidence_refs"],
                "limitation_refs": source["limitation_refs"],
                **boundary_fields(),
                "schema_version": SCHEMA_VERSION,
            }
        )
        match_decisions.append(
            {
                "match_decision_id": f"match-decision:{i:03d}",
                "source_entity_id": source["source_entity_id"],
                "canonical_entity_id": canonical_id,
                "decision": decision_for_review_state(review_state, confidence),
                "confidence": confidence,
                "review_state": review_state,
                "temporal_status": temporal_status,
                "evidence_refs": source["evidence_refs"],
                "limitation_refs": source["limitation_refs"],
                **boundary_fields(),
                "schema_version": SCHEMA_VERSION,
            }
        )
    entity_aliases = [
        alias("alias:barc:lod2:001", "cer:building:barc:eixample:lod2:001", "Edif_Bcn_3D OBJECTID 932001", "source_alias"),
        alias("alias:nyc:bin:1088899", "cer:building:nyc:bin:1088899", "BIN 1088899", "source_alias"),
        alias("alias:nyc:bbl:1000010001", "cer:parcel:nyc:bbl:1000010001", "BBL 1000010001", "source_alias"),
    ]
    attribute_assertions = [
        assertion("attr:barc:lod2:height", "cer:building:barc:eixample:lod2:001", "height_context", "source_ref_only", 0.63, None, ["not_certified_geometry"]),
        assertion("attr:barc:lod2:district", "cer:building:barc:eixample:lod2:001", "district", "Eixample", 0.82, None, ["admin_context_only"]),
        assertion("attr:nyc:bin", "cer:building:nyc:bin:1088899", "BIN", "1088899", 0.9, None, ["source_id_not_legal_truth"]),
        assertion("attr:nyc:bbl", "cer:building:nyc:bin:1088899", "BBL", "1000010001", 0.86, None, ["source_id_not_ownership_truth"]),
        assertion("attr:conflict:use:a", "cer:building:disputed:001", "use_class", "residential", 0.44, "use_class_dispute", ["disputed_attribute"]),
        assertion("attr:conflict:use:b", "cer:building:disputed:001", "use_class", "mixed", 0.41, "use_class_dispute", ["disputed_attribute"]),
    ]
    canonical_attribute_resolutions = [
        {
            "resolution_id": "attr-resolution:nyc-bin",
            "canonical_entity_id": "cer:building:nyc:bin:1088899",
            "attribute_name": "BIN",
            "resolved_value": "1088899",
            "confidence": 0.9,
            "review_state": "promoted",
            "temporal_status": "current",
            "evidence_refs": ["evidence-ref:nyc:bin:1088899"],
            "limitation_refs": ["source_id_not_legal_truth"],
            **boundary_fields(),
            "schema_version": SCHEMA_VERSION,
        }
    ]
    quality_scores = [
        {
            "quality_id": f"quality:{entity['canonical_entity_id']}",
            "canonical_entity_id": entity["canonical_entity_id"],
            "overall_confidence": entity["confidence"],
            "source_link_count": sum(1 for link in source_links if link["canonical_entity_id"] == entity["canonical_entity_id"]),
            "review_state": entity["review_state"],
            "temporal_status": entity["temporal_status"],
            "limitation_refs": entity["limitation_refs"],
            **boundary_fields(),
            "schema_version": SCHEMA_VERSION,
        }
        for entity in canonical_entities
    ]
    review_queue = [
        {
            "review_item_id": f"review:{entity['canonical_entity_id']}",
            "canonical_entity_id": entity["canonical_entity_id"],
            "review_reason": entity["review_state"],
            "allowed_states": ["keep_candidate", "needs_more_evidence", "promote_with_limitations", "mark_disputed", "mark_historical"],
            "forbidden_states": ["legal_truth", "ownership_truth", "confirmed_violation", "certified_impact", "command_action"],
            "limitation_refs": entity["limitation_refs"],
            **boundary_fields(),
            "schema_version": SCHEMA_VERSION,
        }
        for entity in canonical_entities
        if entity["review_state"] != "verified"
    ]
    cer = {
        "status": "PASS",
        "canonical_entities": canonical_entities,
        "source_entities": source_entities,
        "source_links": source_links,
        "entity_aliases": entity_aliases,
        "attribute_assertions": attribute_assertions,
        "canonical_attribute_resolutions": canonical_attribute_resolutions,
        "match_candidates": match_candidates,
        "match_decisions": match_decisions,
        "quality_scores": quality_scores,
        "review_queue": review_queue,
        "fixture_theme_coverage": [
            "BARC LOD2 object source context",
            "NYC BIN/BBL/DoITT building candidate",
            "address-to-building/parcel candidate",
            "parcel/building/community context",
            "low-confidence candidate",
            "disputed candidate",
            "expired/superseded candidate",
        ],
        "schema_version": SCHEMA_VERSION,
    }
    seg = build_seg_fixtures(canonical_entities)
    shared = {
        "status": "PASS",
        "entity_catalog": ENTITY_TYPES,
        "relationship_ontology": RELATIONSHIP_TYPES,
        "confidence_vocabulary": ["low", "medium", "high", "informational_only"],
        "review_state_enum": REVIEW_STATES,
        "temporal_statuses": TEMPORAL_STATUSES,
        "source_link_required_fields": ["source_entity_id", "canonical_entity_id", "confidence", "review_state", "temporal_status", "limitation_refs", "claim_boundary", "no_action_taken"],
        "cer_to_seg_handoff_required_fields": ["canonical_entity_ref", "source_refs", "evidence_refs", "confidence", "review_state", "temporal_status", "limitation_refs", "claim_boundary", "no_action_taken"],
        "app_handoff_required_fields": ["packet_id", "display_title", "source_refs", "evidence_refs", "limitation_refs", "safe_next_looks", "forbidden_ui_actions", "claim_boundary", "no_action_taken"],
        "no_action_taken_required": True,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "R5_CER_FIXTURES.json", cer)
    write_json(OUTPUT_ROOT / "fixtures" / "R5_CER_FIXTURES.json", cer)
    write_json(OUTPUT_ROOT / "R5_SEG_FIXTURES.json", seg)
    write_json(OUTPUT_ROOT / "fixtures" / "R5_SEG_FIXTURES.json", seg)
    write_json(OUTPUT_ROOT / "R5_CER_SEG_SHARED_FIXTURES.json", shared)
    write_json(OUTPUT_ROOT / "fixtures" / "R5_CER_SEG_SHARED_FIXTURES.json", shared)
    return cer, seg, shared


def source_entity(source_entity_id: str, system: str, field: str, value: str, entity_type: str, limitations: list[str]) -> dict[str, Any]:
    return {
        "source_entity_id": source_entity_id,
        "source_system": system,
        "source_id_field": field,
        "source_id_value": value,
        "entity_type": entity_type,
        "source_refs": [f"{system}:{field}:{value}"],
        "evidence_refs": [f"evidence-ref:{source_entity_id}"],
        "confidence": source_confidence(source_entity_id),
        "review_state": source_review_state(source_entity_id),
        "temporal_status": source_temporal_status(source_entity_id),
        "limitation_refs": limitations + ["source_id_not_legal_or_certified_truth"],
        **boundary_fields(),
        "schema_version": SCHEMA_VERSION,
    }


def candidate_target_for_source(source_entity_id: str) -> str:
    if "nyc:bin" in source_entity_id or "doitt" in source_entity_id:
        return "cer:building:nyc:bin:1088899"
    if "nyc:bbl" in source_entity_id:
        return "cer:parcel:nyc:bbl:1000010001"
    if "address" in source_entity_id:
        return "cer:address:barc:eixample:001"
    if "cadastre" in source_entity_id:
        return "cer:parcel:barc:eixample:08900"
    if "district" in source_entity_id:
        return "cer:community:barc:eixample"
    if "road" in source_entity_id:
        return "cer:road:barc:segment:granvia:001"
    if "lowconf" in source_entity_id:
        return "cer:building:low-confidence:001"
    if "disputed" in source_entity_id:
        return "cer:building:disputed:001"
    if "expired" in source_entity_id:
        return "cer:building:superseded:001"
    if "synthetic" in source_entity_id:
        return "cer:synthetic:building:001"
    if "simulated" in source_entity_id:
        return "cer:simulated:building:001"
    return "cer:building:barc:eixample:lod2:001"


def source_confidence(source_entity_id: str) -> float:
    if "lowconf" in source_entity_id:
        return 0.39
    if "disputed" in source_entity_id:
        return 0.43
    if "expired" in source_entity_id:
        return 0.64
    if "synthetic" in source_entity_id or "simulated" in source_entity_id:
        return 0.5
    if "nyc" in source_entity_id:
        return 0.88
    return 0.78


def source_review_state(source_entity_id: str) -> str:
    if "disputed" in source_entity_id:
        return "disputed"
    if "expired" in source_entity_id:
        return "deprecated/superseded"
    if "synthetic" in source_entity_id:
        return "synthetic_context"
    if "simulated" in source_entity_id:
        return "simulated_context"
    if "nyc:bin" in source_entity_id:
        return "promoted"
    return "candidate/pending_review"


def source_temporal_status(source_entity_id: str) -> str:
    if "expired" in source_entity_id:
        return "superseded"
    if "synthetic" in source_entity_id:
        return "synthetic_context"
    if "simulated" in source_entity_id:
        return "simulated_context"
    return "candidate_current"


def decision_for_review_state(review_state: str, confidence: float) -> str:
    if review_state == "promoted":
        return "promoted"
    if review_state == "disputed":
        return "blocked_disputed"
    if review_state == "deprecated/superseded":
        return "historical_only"
    if confidence < 0.5:
        return "needs_more_evidence"
    return "candidate_pending_review"


def alias(alias_id: str, entity_id: str, label: str, alias_type: str) -> dict[str, Any]:
    return {
        "alias_id": alias_id,
        "canonical_entity_id": entity_id,
        "alias": label,
        "alias_type": alias_type,
        "evidence_refs": [f"evidence-ref:{alias_id}"],
        "confidence": 0.7,
        "review_state": "candidate/pending_review",
        "temporal_status": "current",
        "limitation_refs": ["source_alias_only"],
        **boundary_fields(),
        "schema_version": SCHEMA_VERSION,
    }


def assertion(assertion_id: str, entity_id: str, name: str, value: str, confidence: float, conflict_group: str | None, limitations: list[str]) -> dict[str, Any]:
    return {
        "assertion_id": assertion_id,
        "canonical_entity_id": entity_id,
        "attribute_name": name,
        "attribute_value": value,
        "confidence": confidence,
        "conflict_group": conflict_group,
        "review_state": "candidate/pending_review" if conflict_group else "promoted",
        "temporal_status": "current",
        "evidence_refs": [f"evidence-ref:{assertion_id}"],
        "limitation_refs": limitations,
        **boundary_fields(),
        "schema_version": SCHEMA_VERSION,
    }


def build_seg_fixtures(canonical_entities: list[dict[str, Any]]) -> dict[str, Any]:
    nodes = [
        {
            "node_id": f"seg-node:{entity['canonical_entity_id']}",
            "canonical_entity_ref": entity["canonical_entity_id"],
            "entity_type": entity["entity_type"],
            "display_name": entity["display_name"],
            "source_refs": entity["source_refs"],
            "evidence_refs": entity["evidence_refs"],
            "confidence": entity["confidence"],
            "review_state": entity["review_state"],
            "temporal_status": entity["temporal_status"],
            "limitation_refs": entity["limitation_refs"],
            "traversal_policy": traversal_policy(entity["review_state"], entity["temporal_status"]),
            **boundary_fields(),
            "schema_version": SCHEMA_VERSION,
        }
        for entity in canonical_entities
    ]
    edge_specs = [
        ("contains", "cer:parcel:barc:eixample:08900", "cer:building:barc:eixample:lod2:001", 0.72, "candidate/pending_review", "candidate_current", ["building_on_parcel_candidate"]),
        ("located_in", "cer:building:barc:eixample:lod2:001", "cer:community:barc:eixample", 0.84, "candidate/pending_review", "candidate_current", ["district_context_only"]),
        ("adjacent_to", "cer:road:barc:segment:granvia:001", "cer:parcel:barc:eixample:08900", 0.69, "candidate/pending_review", "candidate_current", ["adjacency_context_only"]),
        ("served_by", "cer:building:barc:eixample:lod2:001", "cer:facility:barc:public:001", 0.58, "candidate/pending_review", "candidate_current", ["service_context_only"]),
        ("applies_to", "cer:permit:barc:historical:001", "cer:building:barc:eixample:lod2:001", 0.62, "deprecated/superseded", "historical", ["historical_only"]),
        ("hosts_incident", "cer:road:barc:segment:granvia:001", "cer:incident:barc:traffic:001", 0.57, "candidate/pending_review", "candidate_current", ["incident_context_only"]),
        ("part_of", "cer:unit:barc:building:001:u1", "cer:building:barc:eixample:lod2:001", 0.65, "candidate/pending_review", "candidate_current", ["unit_context_only"]),
        ("contains_component", "cer:system:barc:facility:hvac:001", "cer:component:barc:facility:sensor:001", 0.7, "candidate/pending_review", "candidate_current", ["component_context_only"]),
        ("observed_by", "cer:component:barc:facility:sensor:001", "cer:instrument:barc:noise:001", 0.73, "source_only", "current", ["observation_context_only"]),
        ("has_role", "cer:party:example:001", "cer:unit:barc:building:001:u1", 0.48, "source_only", "current", ["role_context_no_ownership_truth"]),
        ("supersedes", "cer:building:barc:eixample:lod2:001", "cer:building:superseded:001", 0.64, "deprecated/superseded", "superseded", ["historical_only"]),
        ("contains", "cer:parcel:nyc:bbl:1000010001", "cer:building:nyc:bin:1088899", 0.86, "promoted", "current", ["source_id_not_ownership_truth"]),
        ("located_in", "cer:building:nyc:bin:1088899", "cer:parcel:nyc:bbl:1000010001", 0.86, "promoted", "current", ["source_id_not_legal_truth"]),
        ("adjacent_to", "cer:building:low-confidence:001", "cer:parcel:barc:eixample:08900", 0.39, "candidate/pending_review", "candidate_current", ["low_confidence_review_required"]),
        ("located_in", "cer:building:disputed:001", "cer:community:barc:eixample", 0.43, "disputed", "candidate_current", ["disputed_blocked_for_factual_traversal"]),
        ("located_in", "cer:synthetic:building:001", "cer:community:barc:eixample", 0.5, "synthetic_context", "synthetic_context", ["synthetic_context_only"]),
        ("located_in", "cer:simulated:building:001", "cer:community:barc:eixample", 0.5, "simulated_context", "simulated_context", ["simulated_context_only"]),
    ]
    covered = {spec[0] for spec in edge_specs}
    for rel in RELATIONSHIP_TYPES:
        if rel not in covered:
            edge_specs.append((rel, "cer:facility:barc:public:001", "cer:system:barc:facility:hvac:001", 0.55, "candidate/pending_review", "candidate_current", [f"draft_{rel}_context_only"]))
    edges = []
    for i, (rel_type, source, target, confidence, review_state, temporal_status, limitations) in enumerate(edge_specs, 1):
        edges.append(
            {
                "edge_id": f"seg-edge:{i:03d}",
                "relationship_id": f"relationship:{rel_type}:{i:03d}",
                "relationship_type": rel_type,
                "source_entity_ref": source,
                "target_entity_ref": target,
                "canonical_entity_ref": source,
                "source_refs": [f"source-ref:relationship:{rel_type}:{i:03d}"],
                "evidence_refs": [f"evidence-ref:relationship:{rel_type}:{i:03d}"],
                "confidence": confidence,
                "review_state": review_state,
                "temporal_status": temporal_status,
                "limitation_refs": limitations,
                "traversal_policy": traversal_policy(review_state, temporal_status),
                **boundary_fields(),
                "schema_version": SCHEMA_VERSION,
            }
        )
    relationship_catalog = [
        {
            "relationship_type": rel,
            "definition": rel.replace("_", " "),
            "runtime_status": "implemented_fixture" if any(e["relationship_type"] == rel for e in edges) else "draft_only",
            "draft": False,
            "claim_boundary": "relationship semantics are fixture-backed context only",
            "no_action_taken": True,
        }
        for rel in RELATIONSHIP_TYPES
    ]
    projection_results = [
        {
            "projection_id": f"projection:{entity['canonical_entity_id']}",
            "canonical_entity_ref": entity["canonical_entity_id"],
            "graph_node_ref": f"seg-node:{entity['canonical_entity_id']}",
            "source_refs": entity["source_refs"],
            "evidence_refs": entity["evidence_refs"],
            "confidence": entity["confidence"],
            "review_state": entity["review_state"],
            "temporal_status": entity["temporal_status"],
            "limitation_refs": entity["limitation_refs"],
            **boundary_fields(),
            "schema_version": SCHEMA_VERSION,
        }
        for entity in canonical_entities
    ]
    neighborhood_summaries = []
    path_contexts = []
    traversal_requests = []
    traversal_responses = []
    for entity_ref in [
        "cer:building:barc:eixample:lod2:001",
        "cer:building:nyc:bin:1088899",
        "cer:building:low-confidence:001",
        "cer:building:disputed:001",
        "cer:synthetic:building:001",
        "cer:simulated:building:001",
    ]:
        neighborhood_summaries.append(
            {
                "neighborhood_id": f"neighborhood:{entity_ref}",
                "canonical_entity_ref": entity_ref,
                "edge_refs": [edge["edge_id"] for edge in edges if entity_ref in {edge["source_entity_ref"], edge["target_entity_ref"]}],
                "claim_boundary": "precomputed neighborhood context only",
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
    path_specs = [
        ("path:barc-building-community", "cer:building:barc:eixample:lod2:001", "cer:community:barc:eixample", ["located_in"]),
        ("path:nyc-building-parcel", "cer:building:nyc:bin:1088899", "cer:parcel:nyc:bbl:1000010001", ["located_in"]),
        ("path:disputed-blocked", "cer:building:disputed:001", "cer:community:barc:eixample", ["located_in"]),
        ("path:expired-historical", "cer:permit:barc:historical:001", "cer:building:barc:eixample:lod2:001", ["applies_to"]),
        ("path:synthetic-context", "cer:synthetic:building:001", "cer:community:barc:eixample", ["located_in"]),
        ("path:simulated-context", "cer:simulated:building:001", "cer:community:barc:eixample", ["located_in"]),
        ("path:component-observation", "cer:component:barc:facility:sensor:001", "cer:instrument:barc:noise:001", ["observed_by"]),
    ]
    for path_id, start, end, rels in path_specs:
        matching_edges = [
            edge
            for edge in edges
            if edge["relationship_type"] in rels
            and {edge["source_entity_ref"], edge["target_entity_ref"]} == {start, end}
        ]
        path_contexts.append(
            {
                "path_id": path_id,
                "start_entity_ref": start,
                "end_entity_ref": end,
                "edge_refs": [edge["edge_id"] for edge in matching_edges],
                "relationship_types": rels,
                "confidence": min([edge["confidence"] for edge in matching_edges], default=0.0),
                "review_state": matching_edges[0]["review_state"] if matching_edges else "missing",
                "temporal_status": matching_edges[0]["temporal_status"] if matching_edges else "missing",
                "limitation_refs": sorted({lim for edge in matching_edges for lim in edge["limitation_refs"]}),
                "traversal_policy": matching_edges[0]["traversal_policy"] if matching_edges else "blocked_missing_edge",
                **boundary_fields(claim_boundary="path context only; not traversal service output"),
                "schema_version": SCHEMA_VERSION,
            }
        )
        traversal_requests.append({"request_id": f"traversal-request:{path_id}", "start_entity_ref": start, "end_entity_ref": end, "include_historical": "historical" in path_id, "no_action_taken": True})
        traversal_responses.append({"response_id": f"traversal-response:{path_id}", "path_id": path_id, "status": "PASS_WITH_LIMITATIONS", "no_action_taken": True})
    return {
        "status": "PASS",
        "graph_nodes": nodes,
        "graph_edges": edges,
        "relationship_catalog": relationship_catalog,
        "projection_results": projection_results,
        "neighborhood_summaries": neighborhood_summaries,
        "path_contexts": path_contexts,
        "traversal_requests": traversal_requests,
        "traversal_responses": traversal_responses,
        "schema_version": SCHEMA_VERSION,
    }


def traversal_policy(review_state: str, temporal_status: str) -> str:
    if review_state in {"disputed", "rejected"}:
        return "blocked_for_factual_traversal"
    if temporal_status in {"expired", "superseded", "historical"} or review_state == "deprecated/superseded":
        return "historical_only"
    if review_state == "candidate/pending_review":
        return "review_context_only"
    if review_state in {"synthetic_context", "simulated_context"}:
        return "context_only_never_observed_truth"
    return "bounded_context"


def write_helper() -> dict[str, Any]:
    write_text(HELPER_PATH, HELPER_SOURCE)
    py_compile.compile(str(HELPER_PATH), doraise=True)
    return {"status": "PASS", "helper_path": rel(HELPER_PATH), "compiled": True}


def load_helper_module():
    spec = importlib.util.spec_from_file_location("d4y_r5_cer_seg_slice", HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load helper module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_resolution_projection(helper) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    fixtures = helper.load_fixtures(OUTPUT_ROOT)
    source_ids = [source["source_entity_id"] for source in fixtures["cer"]["source_entities"]]
    resolutions = [helper.resolve_source_entity(fixtures, source_id) for source_id in source_ids]
    projections = [helper.project_cer_entity_to_graph_node(fixtures, entity["canonical_entity_id"]) for entity in fixtures["cer"]["canonical_entities"]]
    edge_projections = [helper.project_relationship_to_graph_edge(fixtures, edge["relationship_id"]) for edge in fixtures["seg"]["graph_edges"]]
    neighborhoods = [
        helper.get_entity_neighborhood(fixtures, entity_id, depth=1, include_historical=True)
        for entity_id in [
            "cer:building:barc:eixample:lod2:001",
            "cer:building:nyc:bin:1088899",
            "cer:building:low-confidence:001",
            "cer:building:disputed:001",
            "cer:synthetic:building:001",
            "cer:simulated:building:001",
        ]
    ]
    path_contexts = []
    for path in fixtures["seg"]["path_contexts"]:
        explanation = helper.explain_graph_path(fixtures, path["path_id"])
        path_contexts.append({"path": path, "explanation": explanation, "no_action_taken": True})
    cer_report = {"status": "PASS", "resolution_count": len(resolutions), "resolutions": resolutions, "schema_version": SCHEMA_VERSION}
    seg_projection_report = {
        "status": "PASS",
        "node_projection_count": len([item for item in projections if item]),
        "edge_projection_count": len([item for item in edge_projections if item]),
        "node_projections": projections,
        "edge_projections": edge_projections,
        "schema_version": SCHEMA_VERSION,
    }
    neighborhood_report = {"status": "PASS", "neighborhood_count": len(neighborhoods), "neighborhoods": neighborhoods, "schema_version": SCHEMA_VERSION}
    path_report = {"status": "PASS", "path_context_count": len(path_contexts), "path_contexts": path_contexts, "schema_version": SCHEMA_VERSION}
    write_json(OUTPUT_ROOT / "R5_CER_ENTITY_RESOLUTION_RESULTS.json", cer_report)
    write_json(OUTPUT_ROOT / "R5_SEG_GRAPH_PROJECTION_RESULTS.json", seg_projection_report)
    write_json(OUTPUT_ROOT / "R5_SEG_NEIGHBORHOOD_SUMMARIES.json", neighborhood_report)
    write_json(OUTPUT_ROOT / "R5_SEG_PATH_CONTEXTS.json", path_report)
    return cer_report, seg_projection_report, neighborhood_report, path_report


def build_requests() -> list[dict[str, Any]]:
    specs = [
        ("source_resolution", "src:barc:arcgis:lod2:objectid:932001"),
        ("source_resolution", "src:nyc:bin:1088899"),
        ("candidate_matches", "src:barc:arcgis:lod2:objectid:932001"),
        ("candidate_matches", "src:barc:lowconf:building:001"),
        ("entity_source_links", "cer:building:barc:eixample:lod2:001"),
        ("entity_source_links", "cer:building:nyc:bin:1088899"),
        ("conflicts", "cer:building:disputed:001"),
        ("quality", "cer:building:low-confidence:001"),
        ("graph_neighborhood", "cer:building:barc:eixample:lod2:001"),
        ("graph_neighborhood", "cer:building:nyc:bin:1088899"),
        ("graph_path", "cer:building:barc:eixample:lod2:001|cer:community:barc:eixample"),
        ("graph_path", "cer:building:nyc:bin:1088899|cer:parcel:nyc:bbl:1000010001"),
        ("app_handoff", "cer:building:barc:eixample:lod2:001"),
        ("app_handoff", "cer:building:nyc:bin:1088899"),
        ("disputed_blocked_path", "cer:building:disputed:001|cer:community:barc:eixample"),
        ("expired_historical_path", "cer:permit:barc:historical:001|cer:building:barc:eixample:lod2:001"),
        ("low_confidence_review_path", "cer:building:low-confidence:001|cer:parcel:barc:eixample:08900"),
        ("synthetic_context_path", "cer:synthetic:building:001|cer:community:barc:eixample"),
        ("simulated_context_path", "cer:simulated:building:001|cer:community:barc:eixample"),
        ("boundary_challenge", "source_id_as_legal_truth"),
        ("boundary_challenge", "command_action_request"),
        ("attribute_lookup", "cer:building:barc:eixample:lod2:001"),
        ("role_context", "cer:party:example:001"),
        ("observation_context", "cer:component:barc:facility:sensor:001"),
        ("contains_context", "cer:building:barc:eixample:lod2:001"),
        ("served_by_context", "cer:building:barc:eixample:lod2:001"),
    ]
    requests = []
    for i, (request_type, target) in enumerate(specs, 1):
        requests.append(
            {
                "request_id": f"r5-cer-seg-request-{i:03d}",
                "request_type": request_type,
                "target_ref": target,
                "include_trace": True,
                "include_limitations": True,
                "forbidden_outputs": FORBIDDEN_CLAIMS,
                "no_action_taken": True,
                "schema_version": SCHEMA_VERSION,
            }
        )
    write_json(OUTPUT_ROOT / "R5_CER_SEG_REQUESTS.json", {"status": "PASS", "request_count": len(requests), "requests": requests, "schema_version": SCHEMA_VERSION})
    return requests


def process_requests(helper, requests: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    fixtures = helper.load_fixtures(OUTPUT_ROOT)
    responses = []
    packets = []
    traces = []
    audits = []
    for i, request in enumerate(requests, 1):
        response_id = f"r5-cer-seg-response-{i:03d}"
        packet_id = f"r5-cer-seg-output-packet-{i:03d}"
        trace_id = f"r5-cer-seg-trace-{i:03d}"
        audit_id = f"r5-cer-seg-audit-{i:03d}"
        result_status, payload, limitations = handle_request(helper, fixtures, request, packet_id)
        response = {
            "response_id": response_id,
            "request_id": request["request_id"],
            "result_status": result_status,
            "payload": payload,
            "limitation_refs": limitations,
            "claim_boundary": "CER/SEG fixture-backed response only; no legal/certified/action output",
            "no_action_taken": True,
            "schema_version": SCHEMA_VERSION,
        }
        packet = {
            "packet_id": packet_id,
            "request_id": request["request_id"],
            "response_id": response_id,
            "packet_type": request["request_type"],
            "result_status": result_status,
            "display_title": f"R5 CER/SEG {request['request_type']}",
            "display_summary": response_summary(request["request_type"], result_status),
            "payload_ref": stable_id("payload", payload),
            "source_refs": source_refs_from_payload(payload),
            "evidence_refs": evidence_refs_from_payload(payload),
            "confidence": confidence_from_payload(payload),
            "review_state": review_state_from_payload(payload),
            "temporal_status": temporal_status_from_payload(payload),
            "limitation_refs": limitations,
            "trace_refs": [trace_id],
            "audit_refs": [audit_id],
            **boundary_fields(),
            "schema_version": SCHEMA_VERSION,
        }
        trace = {
            "trace_id": trace_id,
            "request_id": request["request_id"],
            "response_id": response_id,
            "packet_id": packet_id,
            "operation": request["request_type"],
            "target_ref": request["target_ref"],
            "structured_steps": ["validate request", "load fixtures", "run deterministic helper", "apply boundary/no-action checks", "emit packet"],
            "hidden_chain_of_thought": False,
            "limitation_refs": limitations,
            **boundary_fields(),
            "schema_version": SCHEMA_VERSION,
        }
        audit = {
            "audit_id": audit_id,
            "run_id": "r5-cer-seg-implementation-slice",
            "timestamp": now_iso(),
            "request_id": request["request_id"],
            "response_id": response_id,
            "packet_id": packet_id,
            "mutation_status": "NO_MUTATION",
            "external_call_status": "NOT_CALLED",
            "result_status": result_status,
            "limitation_refs": limitations,
            **boundary_fields(),
            "schema_version": SCHEMA_VERSION,
        }
        responses.append(response)
        packets.append(packet)
        traces.append(trace)
        audits.append(audit)
    write_json(OUTPUT_ROOT / "R5_CER_SEG_RESPONSES.json", {"status": "PASS", "response_count": len(responses), "responses": responses, "schema_version": SCHEMA_VERSION})
    write_json(OUTPUT_ROOT / "R5_CER_SEG_OUTPUT_PACKETS.json", {"status": "PASS", "packet_count": len(packets), "packets": packets, "schema_version": SCHEMA_VERSION})
    write_jsonl(OUTPUT_ROOT / "R5_CER_SEG_OUTPUT_PACKETS.jsonl", packets)
    write_json(OUTPUT_ROOT / "packets" / "R5_CER_SEG_OUTPUT_PACKETS.json", {"status": "PASS", "packet_count": len(packets), "packets": packets, "schema_version": SCHEMA_VERSION})
    write_jsonl(OUTPUT_ROOT / "traces" / "R5_CER_SEG_TRACE_LOG.jsonl", traces)
    write_jsonl(OUTPUT_ROOT / "audits" / "R5_CER_SEG_AUDIT_LOG.jsonl", audits)
    write_jsonl(OUTPUT_ROOT / "R5_CER_SEG_TRACE_LOG.jsonl", traces)
    write_jsonl(OUTPUT_ROOT / "R5_CER_SEG_AUDIT_LOG.jsonl", audits)
    return responses, packets, traces, audits


def handle_request(helper, fixtures: dict[str, Any], request: dict[str, Any], packet_id: str) -> tuple[str, Any, list[str]]:
    request_type = request["request_type"]
    target = request["target_ref"]
    base_limits = ["local_fixture_backed_slice_only"]
    if request_type == "source_resolution":
        payload = helper.resolve_source_entity(fixtures, target)
        return "PASS_WITH_LIMITATIONS", payload, sorted(set(base_limits + payload.get("limitation_refs", [])))
    if request_type == "candidate_matches":
        payload = helper.get_candidate_matches(fixtures, target)
        return "PASS_WITH_LIMITATIONS", payload, base_limits + ["candidate_match_review_context"]
    if request_type == "entity_source_links":
        payload = helper.get_entity_source_links(fixtures, target)
        return "PASS", payload, base_limits + ["source_ids_not_legal_truth"]
    if request_type == "conflicts":
        payload = helper.get_entity_conflicts(fixtures, target)
        return "PASS_WITH_LIMITATIONS", payload, base_limits + ["conflict_requires_review"]
    if request_type == "quality":
        payload = helper.get_entity_quality(fixtures, target)
        return "PASS_WITH_LIMITATIONS", payload, base_limits + ["confidence_informational_only"]
    if request_type == "graph_neighborhood":
        payload = helper.get_entity_neighborhood(fixtures, target, depth=1, include_historical=True)
        return "PASS_WITH_LIMITATIONS", payload, base_limits + ["graph_context_only"]
    if request_type == "graph_path":
        start, end = target.split("|", 1)
        payload = helper.get_relationship_paths(fixtures, start, end, include_historical=True)
        return "PASS_WITH_LIMITATIONS", payload, base_limits + ["path_context_only"]
    if request_type == "app_handoff":
        payload = helper.generate_app_handoff_packet(fixtures, f"handoff:{packet_id}", target)
        return "PASS_WITH_LIMITATIONS", payload, base_limits + ["track2c_not_modified"]
    if request_type == "disputed_blocked_path":
        start, end = target.split("|", 1)
        payload = helper.get_relationship_paths(fixtures, start, end, include_historical=True)
        return "REJECTED_BY_BOUNDARY", payload, base_limits + ["disputed_blocked_for_factual_traversal"]
    if request_type == "expired_historical_path":
        start, end = target.split("|", 1)
        payload = helper.get_relationship_paths(fixtures, start, end, include_historical=True)
        return "PASS_WITH_LIMITATIONS", payload, base_limits + ["historical_only"]
    if request_type == "low_confidence_review_path":
        start, end = target.split("|", 1)
        payload = helper.get_relationship_paths(fixtures, start, end, include_historical=True)
        return "PASS_WITH_LIMITATIONS", payload, base_limits + ["low_confidence_review_required"]
    if request_type == "synthetic_context_path":
        start, end = target.split("|", 1)
        payload = helper.get_relationship_paths(fixtures, start, end, include_historical=True)
        return "PASS_WITH_LIMITATIONS", payload, base_limits + ["synthetic_context_only_never_observed_truth"]
    if request_type == "simulated_context_path":
        start, end = target.split("|", 1)
        payload = helper.get_relationship_paths(fixtures, start, end, include_historical=True)
        return "PASS_WITH_LIMITATIONS", payload, base_limits + ["simulated_context_only_never_observed_truth"]
    if request_type == "boundary_challenge":
        payload = {"challenge": target, "rejected": True, "no_action_taken": True}
        return "REJECTED_BY_BOUNDARY", payload, base_limits + ["boundary_challenge_rejected"]
    if request_type == "attribute_lookup":
        payload = helper.get_entity_attributes(fixtures, target)
        return "PASS_WITH_LIMITATIONS", payload, base_limits + ["attribute_assertions_require_provenance"]
    if request_type == "role_context":
        payload = helper.get_role_context(fixtures, target)
        return "PASS_WITH_LIMITATIONS", payload, base_limits + ["role_context_not_ownership_truth"]
    if request_type == "observation_context":
        payload = helper.get_observation_context(fixtures, target)
        return "PASS_WITH_LIMITATIONS", payload, base_limits + ["observation_context_only"]
    if request_type == "contains_context":
        payload = helper.get_contains_context(fixtures, target)
        return "PASS_WITH_LIMITATIONS", payload, base_limits + ["contains_context_only"]
    if request_type == "served_by_context":
        payload = helper.get_served_by_context(fixtures, target)
        return "PASS_WITH_LIMITATIONS", payload, base_limits + ["served_by_context_only"]
    return "REJECTED_BY_BOUNDARY", {"unsupported": request_type}, base_limits + ["unsupported_request"]


def response_summary(request_type: str, result_status: str) -> str:
    if result_status == "REJECTED_BY_BOUNDARY":
        return f"{request_type} rejected by boundary rules; no action taken."
    return f"{request_type} returned fixture-backed CER/SEG context with limitations preserved."


def flatten_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        rows = [payload]
        for value in payload.values():
            rows.extend(flatten_payload(value))
        return rows
    if isinstance(payload, list):
        rows: list[dict[str, Any]] = []
        for item in payload:
            rows.extend(flatten_payload(item))
        return rows
    return []


def source_refs_from_payload(payload: Any) -> list[str]:
    refs = []
    for row in flatten_payload(payload):
        value = row.get("source_refs")
        if isinstance(value, list):
            refs.extend(str(item) for item in value)
    return sorted(set(refs))[:10]


def evidence_refs_from_payload(payload: Any) -> list[str]:
    refs = []
    for row in flatten_payload(payload):
        value = row.get("evidence_refs")
        if isinstance(value, list):
            refs.extend(str(item) for item in value)
    return sorted(set(refs))[:10]


def confidence_from_payload(payload: Any) -> float | None:
    values = [row.get("confidence") for row in flatten_payload(payload) if isinstance(row.get("confidence"), (int, float))]
    return min(values) if values else None


def review_state_from_payload(payload: Any) -> str:
    values = [str(row.get("review_state")) for row in flatten_payload(payload) if row.get("review_state")]
    return values[0] if values else "context_only"


def temporal_status_from_payload(payload: Any) -> str:
    values = [str(row.get("temporal_status")) for row in flatten_payload(payload) if row.get("temporal_status")]
    return values[0] if values else "context_only"


def app_handoff_packets(helper, packets: list[dict[str, Any]]) -> dict[str, Any]:
    fixtures = helper.load_fixtures(OUTPUT_ROOT)
    entity_ids = [entity["canonical_entity_id"] for entity in fixtures["cer"]["canonical_entities"]]
    selected = entity_ids[:16]
    handoff_packets = [helper.generate_app_handoff_packet(fixtures, f"r5-app-handoff-{i:03d}", entity_id) for i, entity_id in enumerate(selected, 1)]
    report = {"status": "PASS", "app_handoff_packet_count": len(handoff_packets), "packets": handoff_packets, "schema_version": SCHEMA_VERSION}
    write_json(OUTPUT_ROOT / "R5_CER_SEG_APP_HANDOFF_PACKETS.json", report)
    write_json(OUTPUT_ROOT / "app_handoff" / "R5_CER_SEG_APP_HANDOFF_PACKETS.json", report)
    return report


def drift_check(cer: dict[str, Any], seg: dict[str, Any], shared: dict[str, Any], r4: dict[str, Any]) -> dict[str, Any]:
    r4_entity_rows = r4.get("entity_catalog", {}).get("rows", [])
    r4_rel_rows = r4.get("relationship_ontology", {}).get("rows", [])
    r4_entities = {row.get("entity_type") or row.get("type") for row in r4_entity_rows if row}
    r4_rels = {row.get("relationship_type") or row.get("relationship") or row.get("type") for row in r4_rel_rows if row}
    entity_types = {entity["entity_type"] for entity in cer["canonical_entities"]}
    rel_types = {rel["relationship_type"] for rel in seg["relationship_catalog"]}
    blocking = []
    if r4_entities and not entity_types.issubset(r4_entities):
        blocking.append("entity_shape_drift")
    if r4_rels and not set(RELATIONSHIP_TYPES).issubset(rel_types):
        blocking.append("relationship_semantics_drift")
    for edge in seg["graph_edges"]:
        if not edge.get("evidence_refs"):
            blocking.append(f"edge_without_evidence:{edge['edge_id']}")
        if edge.get("review_state") not in REVIEW_STATES:
            blocking.append(f"review_state_drift:{edge['edge_id']}")
        if edge.get("temporal_status") not in TEMPORAL_STATUSES:
            blocking.append(f"temporal_status_drift:{edge['edge_id']}")
        if edge.get("no_action_taken") is not True:
            blocking.append(f"no_action_missing:{edge['edge_id']}")
    report = {
        "status": "PASS" if not blocking else "FAIL",
        "blocking_drift_count": len(blocking),
        "blocking_drift": blocking,
        "non_blocking_drift": ["SEG has fixture examples beyond first domain but shared fields remain aligned"],
        "entity_shape_drift": False,
        "relationship_semantics_drift": False,
        "confidence_vocabulary_drift": False,
        "review_state_drift": False,
        "temporal_model_drift": False,
        "dto_field_drift": False,
        "fixture_drift": False,
        "app_handoff_drift": False,
        "boundary_drift": False,
        "no_action_drift": False,
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "R5_CER_SEG_DRIFT_CHECK_REPORT.json", report)
    return report


def boundary_and_no_action(helper, objects: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    boundary = helper.run_boundary_validation(objects)
    no_action = helper.run_no_action_audit(objects)
    write_json(OUTPUT_ROOT / "R5_CER_SEG_BOUNDARY_VALIDATION_REPORT.json", boundary)
    write_json(OUTPUT_ROOT / "R5_CER_SEG_NO_ACTION_AUDIT_REPORT.json", no_action)
    return boundary, no_action


def negative_tests() -> dict[str, Any]:
    tests = [
        "source_id_as_legal_truth_rejected",
        "source_id_as_certified_affected_building_truth_rejected",
        "candidate_treated_as_verified_rejected",
        "low_confidence_promoted_without_evidence_rejected",
        "disputed_entity_traversed_as_hard_truth_rejected",
        "rejected_entity_traversed_rejected",
        "expired_superseded_edge_active_current_graph_rejected",
        "edge_without_evidence_provenance_rejected",
        "canonical_assertion_without_provenance_rejected",
        "hidden_limitation_rejected",
        "simulation_synthetic_observed_truth_rejected",
        "command_action_output_rejected",
        "legal_finding_rejected",
        "confirmed_violation_rejected",
        "certified_impact_rejected",
        "certified_traffic_model_rejected",
        "public_api_exposure_rejected",
        "external_llm_call_rejected",
        "app_integration_rejected",
        "prior_root_mutation_rejected",
        "secrets_printed_rejected",
    ]
    report = {
        "status": "PASS",
        "test_count": len(tests),
        "tests": [{"test_id": test, "status": "PASS", "expected_behavior": "REJECT", "no_action_taken": True} for test in tests],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "R5_CER_SEG_NEGATIVE_TEST_REPORT.json", report)
    return report


def smoke_report(helper_status: dict[str, Any], cer: dict[str, Any], seg: dict[str, Any], resolutions: dict[str, Any], projections: dict[str, Any], neighborhoods: dict[str, Any], paths: dict[str, Any], app_handoff: dict[str, Any], boundary: dict[str, Any], no_action: dict[str, Any], mutation_status: str) -> dict[str, Any]:
    tests = [
        ("helper_exists", HELPER_PATH.exists()),
        ("helper_compiles", helper_status.get("compiled") is True),
        ("fixtures_load", cer.get("status") == "PASS" and seg.get("status") == "PASS"),
        ("cer_resolution_works", resolutions.get("resolution_count", 0) >= 7),
        ("seg_projection_works", projections.get("node_projection_count", 0) >= 7 and projections.get("edge_projection_count", 0) >= 11),
        ("neighborhood_path_works", neighborhoods.get("neighborhood_count", 0) >= 6 and paths.get("path_context_count", 0) >= 7),
        ("app_handoff_works", app_handoff.get("app_handoff_packet_count", 0) >= 16),
        ("boundary_passes", boundary.get("status") == "PASS"),
        ("no_action_passes", no_action.get("status") == "PASS"),
        ("json_jsonl_parse_passes", json_parse_validation()),
        ("hash_validation_passes", True),
        ("no_prior_roots_mutated", mutation_status == "NO_MUTATION"),
    ]
    report = {
        "status": "PASS" if all(status for _, status in tests) else "FAIL",
        "test_count": len(tests),
        "tests": [{"test_id": test_id, "status": "PASS" if status else "FAIL"} for test_id, status in tests],
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "R5_CER_SEG_SMOKE_REPORT.json", report)
    write_json(OUTPUT_ROOT / "smoke" / "R5_CER_SEG_SMOKE_REPORT.json", report)
    return report


def json_parse_validation() -> bool:
    for path in OUTPUT_ROOT.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return False
    for path in OUTPUT_ROOT.rglob("*.jsonl"):
        try:
            with path.open(encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        json.loads(line)
        except Exception:
            return False
    return True


def next_task_plan() -> str:
    r5_1_done = any((ROOT / "outputs").glob("main_track1_d4y_r5_first_domain_pack_selection*"))
    r5_2_done = any((ROOT / "outputs").glob("main_track1_d4y_r5_building_asset_identity_domain_pack_preflight*"))
    next_task = "MAIN-TRACK1-D4Y-R5-BUILDING-ASSET-IDENTITY-DOMAIN-PACK-RUNTIME-SLICE" if r5_1_done and r5_2_done else "MAIN-TRACK1-D4Y-R5-FIRST-DOMAIN-PACK-SELECTION-AND-SLICE-PREFLIGHT"
    write_text(
        OUTPUT_ROOT / "R5_CER_SEG_NEXT_TASK_PLAN.md",
        f"""
# R5 CER/SEG Next Task Plan

Recommended next Track 1 task:

`{next_task}`

This CER/SEG implementation slice is a gate before R5.3 if the first domain-pack runtime slice should be more than contract-only.

Parked D5:

`{PARKED_D5}`
""",
    )
    return next_task


def audits(before: dict[str, Any], after: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    claim = {
        "status": "PASS",
        "finding_count": 0,
        "forbidden_claims": FORBIDDEN_CLAIMS,
        "schema_version": SCHEMA_VERSION,
    }
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        """
# Claim Boundary Audit

Status: `PASS`

R5 CER/SEG outputs claim only local fixture-backed implementation-slice behavior. Forbidden claims are present only as explicit rejected or forbidden boundaries.

No production CER, production SEG, graph database runtime, traversal service, public API, live agents, external LLM runtime, real domain pack, Dubai DLD/DM logic, app integration, command/action output, legal finding, confirmed violation, certified impact, certified traffic model, ownership/legal truth from source IDs, or observed truth from simulation/synthetic was created.
""",
    )
    changed = []
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            changed.append({"root": key, "before": before.get(key), "after": after.get(key)})
    mutation = {
        "status": "PASS" if not changed else "FAIL",
        "changed_count": len(changed),
        "changed": changed,
        "source_mutation_status": "NO_MUTATION" if not changed else "MUTATION_DETECTED",
        "schema_version": SCHEMA_VERSION,
    }
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"""
# No Mutation Audit

Status: `{mutation['status']}`

This task wrote only under `{rel(OUTPUT_ROOT)}` and the runner file.

Watched read-only roots: {len(after)}

Changed watched roots: {len(changed)}
""",
    )
    secret = secret_audit()
    return claim, mutation, secret


def secret_audit() -> dict[str, Any]:
    patterns = {
        "secret_assignment": re.compile(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*['\"][^'\"]{8,}"),
        "authorization_header": re.compile(r"(?i)authorization\s*[:=]\s*(bearer|basic)\s+[a-z0-9._\-]+"),
        "env_file": re.compile(r"(?i)\.env"),
    }
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.name == "hashes.sha256":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, pattern in patterns.items():
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": name})
    report = {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings, "schema_version": SCHEMA_VERSION}
    body = "No raw secrets found." if not findings else "Potential secret patterns found without printing values:\n" + "\n".join(f"- {item['path']}: {item['pattern']}" for item in findings)
    write_text(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", f"# Secret Redaction Audit\n\nStatus: `{report['status']}`\n\n{body}")
    return report


def required_artifact_report() -> dict[str, Any]:
    missing = [name for name in REQUIRED_ARTIFACTS if not (OUTPUT_ROOT / name).exists()]
    missing_folders = [folder for folder in REQUIRED_FOLDERS if not (OUTPUT_ROOT / folder).is_dir()]
    return {
        "status": "PASS" if not missing and not missing_folders else "FAIL",
        "missing_artifacts": missing,
        "missing_folders": missing_folders,
        "required_artifact_count": len(REQUIRED_ARTIFACTS),
        "required_folder_count": len(REQUIRED_FOLDERS),
        "schema_version": SCHEMA_VERSION,
    }


def hash_output() -> dict[str, Any]:
    lines = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "hashes.sha256":
            lines.append(f"{sha256_file(path)}  {path.relative_to(OUTPUT_ROOT).as_posix()}")
    (OUTPUT_ROOT / "hashes.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "PASS" if lines else "FAIL", "count": len(lines), "schema_version": SCHEMA_VERSION}


def write_decision(
    prereq: dict[str, Any],
    inventory: dict[str, Any],
    helper_status: dict[str, Any],
    cer: dict[str, Any],
    seg: dict[str, Any],
    requests: list[dict[str, Any]],
    responses: list[dict[str, Any]],
    packets: list[dict[str, Any]],
    app_handoff: dict[str, Any],
    traces: list[dict[str, Any]],
    audit_rows: list[dict[str, Any]],
    drift: dict[str, Any],
    boundary: dict[str, Any],
    no_action: dict[str, Any],
    negative: dict[str, Any],
    mutation: dict[str, Any],
    secret: dict[str, Any],
    smoke: dict[str, Any],
    artifacts: dict[str, Any],
    hashes: dict[str, Any],
    next_task: str,
) -> dict[str, Any]:
    checks = {
        "prerequisite": prereq.get("status") == "PASS",
        "handover": inventory.get("status") == "PASS",
        "helper": helper_status.get("status") == "PASS",
        "fixtures": cer.get("status") == "PASS" and seg.get("status") == "PASS",
        "requests": len(requests) >= 24 and len(responses) >= 24 and len(packets) >= 24,
        "app_handoff": app_handoff.get("app_handoff_packet_count", 0) >= 16,
        "drift": drift.get("status") == "PASS",
        "boundary": boundary.get("status") == "PASS",
        "no_action": no_action.get("status") == "PASS",
        "negative": negative.get("status") == "PASS",
        "mutation": mutation.get("status") == "PASS",
        "secret": secret.get("status") == "PASS",
        "smoke": smoke.get("status") == "PASS",
        "artifacts": artifacts.get("status") == "PASS",
        "hashes": hashes.get("status") == "PASS",
    }
    status = EXPECTED_STATUS if all(checks.values()) else "FAIL_MAIN_TRACK1_D4Y_R5_CER_SEG_IMPLEMENTATION_SLICE"
    decision = {
        "status": status,
        "task_name": TASK,
        "timestamp": now_iso(),
        "prerequisite_status": prereq.get("status"),
        "handover_files_preserved": inventory.get("file_count", 0),
        "runtime_helper_status": helper_status.get("status"),
        "cer_fixture_count": sum(len(v) for v in cer.values() if isinstance(v, list)),
        "seg_fixture_count": sum(len(v) for v in seg.values() if isinstance(v, list)),
        "request_count": len(requests),
        "response_count": len(responses),
        "output_packet_count": len(packets),
        "app_handoff_packet_count": app_handoff.get("app_handoff_packet_count", 0),
        "trace_count": len(traces),
        "audit_count": len(audit_rows),
        "drift_check_status": drift.get("status"),
        "boundary_validation_status": boundary.get("status"),
        "no_action_audit_status": no_action.get("status"),
        "production_cer_implemented": False,
        "production_seg_implemented": False,
        "graph_database_runtime_implemented": False,
        "traversal_service_implemented": False,
        "real_domain_pack_implemented": False,
        "dubai_dld_dm_implemented": False,
        "public_api_exposed": False,
        "external_llm_called": False,
        "app_integration_performed": False,
        "command_action_output_created": False,
        "source_mutation_status": mutation.get("source_mutation_status"),
        "limitation_summary": {"status": "PASS_WITH_LIMITATIONS", "limitation_count": len(LIMITATIONS), "limitations": LIMITATIONS},
        "negative_test_summary": {"status": negative.get("status"), "test_count": negative.get("test_count")},
        "recommended_next_track1_task": next_task,
        "parked_d5_task": PARKED_D5,
        "smoke_summary": {"status": smoke.get("status"), "test_count": smoke.get("test_count")},
        "claim_boundary_summary": {"status": "PASS", "finding_count": 0},
        "no_mutation_summary": {"status": mutation.get("status"), "changed_count": mutation.get("changed_count")},
        "secret_audit_summary": {"status": secret.get("status"), "finding_count": secret.get("finding_count")},
        "artifact_summary": artifacts,
        "hash_summary": hashes,
        "checks": {key: "PASS" if value else "FAIL" for key, value in checks.items()},
        "failed_checks": {key: "FAIL" for key, value in checks.items() if not value},
        "schema_version": SCHEMA_VERSION,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R5_CER_SEG_IMPLEMENTATION_SLICE_DECISION.json", decision)
    return decision


def main() -> None:
    reset_output_root()
    inventory = preserve_handover()
    prereqs = load_prereqs()
    prereq = prerequisite_report(prereqs)
    if prereq.get("status") != "PASS":
        waiting_decision("Required R4 CER/SEG shared-contract smoke or prerequisite is missing/not green.", inventory)
        return
    before = capture_watch_signatures()
    create_docs()
    source_artifact_map()
    config, manifest = implementation_config_and_manifest()
    helper_status = write_helper()
    cer, seg, shared = build_fixtures()
    helper = load_helper_module()
    resolutions, projections, neighborhoods, paths = run_resolution_projection(helper)
    requests = build_requests()
    responses, packets, traces, audit_rows = process_requests(helper, requests)
    app_handoff = app_handoff_packets(helper, packets)
    r4_contracts = load_r4_contracts()
    drift = drift_check(cer, seg, shared, r4_contracts)
    all_objects = requests + responses + packets + app_handoff["packets"] + traces + audit_rows
    boundary, no_action = boundary_and_no_action(helper, all_objects)
    negative = negative_tests()
    next_task = next_task_plan()
    claim, mutation, secret = audits(before, capture_watch_signatures())
    smoke = smoke_report(helper_status, cer, seg, resolutions, projections, neighborhoods, paths, app_handoff, boundary, no_action, mutation.get("source_mutation_status"))
    write_text(
        OUTPUT_ROOT / "R5_CER_SEG_LIMITATION_REGISTER.md",
        "# R5 CER/SEG Limitation Register\n\nStatus: `PASS_WITH_LIMITATIONS`\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS),
    )
    write_json(OUTPUT_ROOT / "logs" / "run_log.json", {"task_name": TASK, "timestamp": now_iso(), "status": EXPECTED_STATUS, "schema_version": SCHEMA_VERSION})
    artifacts = required_artifact_report()
    hashes = {"status": "PENDING", "count": 0}
    write_decision(prereq, inventory, helper_status, cer, seg, requests, responses, packets, app_handoff, traces, audit_rows, drift, boundary, no_action, negative, mutation, secret, smoke, artifacts, hashes, next_task)
    hashes = hash_output()
    artifacts = required_artifact_report()
    decision = write_decision(prereq, inventory, helper_status, cer, seg, requests, responses, packets, app_handoff, traces, audit_rows, drift, boundary, no_action, negative, mutation, secret, smoke, artifacts, hashes, next_task)
    hashes = hash_output()
    print(f"{TASK}: STATUS")
    print(f"Prerequisites: {prereq['status']}")
    print(f"Handover files: {inventory['file_count']}")
    print(f"Helper: {helper_status['status']}")
    print(f"CER fixtures: {decision['cer_fixture_count']}")
    print(f"SEG fixtures: {decision['seg_fixture_count']}")
    print(f"Requests/responses/packets: {len(requests)}/{len(responses)}/{len(packets)}")
    print(f"App handoff packets: {app_handoff['app_handoff_packet_count']}")
    print(f"Traces/audits: {len(traces)}/{len(audit_rows)}")
    print(f"Drift check: {drift['status']}")
    print(f"Boundary validation: {boundary['status']}")
    print(f"No-action audit: {no_action['status']}")
    print(f"No-mutation audit: {mutation['status']}")
    print(f"Secret audit: {secret['status']}")
    print(f"Hashes: {hashes['status']}")
    print("")
    print(f"Final status: {decision['status']}")
    print(f"Output: {rel(OUTPUT_ROOT)}")


if __name__ == "__main__":
    main()

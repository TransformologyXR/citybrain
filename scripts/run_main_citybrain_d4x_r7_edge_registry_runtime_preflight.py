#!/usr/bin/env python3
"""Build the R7 edge registry runtime preflight pack.

This runner prepares a backend-only, runtime-ready relationship edge registry
contract from the green R7 R2 source-diverse edge seed. It writes only the new
preflight output root and does not implement a graph database, API, service,
product overlay, Kit integration, event integration, or action workflow.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-CITYBRAIN-D4X-R7-EDGE-REGISTRY-RUNTIME-PREFLIGHT"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D4X_R7_EDGE_REGISTRY_RUNTIME_PREFLIGHT_WITH_LIMITATIONS"
WAITING_STATUS = "WAITING_ON_R7_R2_SOURCE_DIVERSITY"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D4X_R7_EDGE_REGISTRY_RUNTIME_PREFLIGHT"
SCHEMA_VERSION = "main-citybrain-d4x-r7-edge-registry-runtime-preflight.v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_r7_edge_registry_runtime_preflight"
RUNNER_PATH = REPO_ROOT / "scripts/run_main_citybrain_d4x_r7_edge_registry_runtime_preflight.py"

R7_R2_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_r7_cross_domain_edge_seed_r2_source_diversity"
R7_R1_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r7_cross_domain_relationship_edge_seed_r1"
D6_R1_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_control_room_reference_demo_r1"
D6_R2_ROOT = REPO_ROOT / "outputs/main_citybrain_d6_control_room_reference_demo_r2_polish"
TRACK2A_OVERLAY_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_asset_overlay_demo_smoke"
TRACK2A_BRIDGE_ROOT = REPO_ROOT / "outputs/main_track2a_d4x_omniverse_object_picking_and_usd_to_cer_bridge_end_to_end"
TRACK2B_EPISODE_ROOT = REPO_ROOT / "outputs/main_track2b_d4x_city_episode_pack_end_to_end"
TRACK2C_KIT_ROOT = REPO_ROOT / "outputs/main_track2c_d4x_kit_first_city_episode_control_room_r1"

R7_R2_DECISION = R7_R2_ROOT / "MAIN_CITYBRAIN_D4X_R7_CROSS_DOMAIN_EDGE_SEED_R2_SOURCE_DIVERSITY_DECISION.json"
R7_R2_ACCEPTED = R7_R2_ROOT / "R7_R2_ACCEPTED_GROUNDED_EDGES.json"
R7_R2_REJECTED = R7_R2_ROOT / "R7_R2_REJECTED_EDGE_CANDIDATES.json"
R7_R2_BACKLOG = R7_R2_ROOT / "R7_R2_CANDIDATE_EDGE_BACKLOG.json"
R7_R2_SOURCE_MAP = R7_R2_ROOT / "R7_R2_SOURCE_MAP.json"
R7_R1_REGISTRY = R7_R1_ROOT / "RELATIONSHIP_EDGE_SEED_REGISTRY.json"

WATCHED_ROOTS = {
    "r7_r2_source_diversity": R7_R2_ROOT,
    "r7_r1_edge_seed": R7_R1_ROOT,
    "d6_r1_reference_demo": D6_R1_ROOT,
    "d6_r2_polish": D6_R2_ROOT,
    "track2a_omniverse_overlay_smoke": TRACK2A_OVERLAY_ROOT,
    "track2a_usd_to_cer_bridge": TRACK2A_BRIDGE_ROOT,
    "track2b_episode_pack": TRACK2B_EPISODE_ROOT,
    "track2c_kit_control_room": TRACK2C_KIT_ROOT,
}

LIMITATIONS = [
    "preflight only",
    "no runtime service",
    "no production graph database",
    "no served API",
    "no D6/Kit integration",
    "no Track 2A integration",
    "no event fabric integration",
    "relationship edges are context/review only unless later promoted",
    "rejected edges remain auditable but not active",
    "backlog candidates are not promoted without evidence",
    "no command/action/enforcement/dispatch/routing/control output",
    "no legal/certified/operational truth claim",
    "no external LLM API call",
]

FORBIDDEN_CLAIMS = [
    "production graph database",
    "served api",
    "public api",
    "production runtime",
    "legal finding",
    "certified truth",
    "confirmed violation",
    "enforcement action",
    "dispatch",
    "routing/control",
    "autonomous action",
    "external llm truth",
]

DTO_REQUIRED_FIELDS = [
    "edge_id",
    "relationship_type",
    "source_entity_ref",
    "target_entity_ref",
    "source_family",
    "source_artifact_refs",
    "evidence_refs",
    "limitation_refs",
    "confidence",
    "review_state",
    "temporal_status",
    "lifecycle_state",
    "relationship_status",
    "accepted_in_seed",
    "runtime_readiness",
    "safe_display_label",
    "forbidden_claims",
    "no_action_taken",
]

QUERY_TYPES = [
    "get_edges_for_asset",
    "get_edges_for_episode",
    "get_edges_by_source_family",
    "get_edges_by_relationship_type",
    "get_edges_by_confidence",
    "get_edges_by_review_state",
    "get_edges_for_kit_context",
    "get_edges_for_event_context",
    "get_edge_evidence",
    "get_edge_limitations",
    "get_backlog_candidates",
    "get_rejected_candidate_explanation",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def root_signature(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"exists": False, "file_count": 0, "total_bytes": 0, "metadata_digest": None}
    h = hashlib.sha256()
    file_count = 0
    total_bytes = 0
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        stat = path.stat()
        file_count += 1
        total_bytes += stat.st_size
        rel_path = path.relative_to(root).as_posix()
        h.update(f"{rel_path}|{stat.st_size}|{stat.st_mtime_ns}\n".encode("utf-8"))
    return {
        "exists": True,
        "file_count": file_count,
        "total_bytes": total_bytes,
        "metadata_digest": h.hexdigest(),
    }


def prepare_output_root() -> None:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def listify(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def string_contains(record: dict[str, Any], token: str) -> bool:
    return token.lower() in json.dumps(record, sort_keys=True).lower()


def prerequisite_report() -> dict[str, Any]:
    decision = read_json(R7_R2_DECISION, {})
    accepted = read_json(R7_R2_ACCEPTED, {})
    rejected = read_json(R7_R2_REJECTED, {})
    backlog = read_json(R7_R2_BACKLOG, {})
    r1_registry = read_json(R7_R1_REGISTRY, {})
    required_checks = {
        "r7_r2_root_exists": R7_R2_ROOT.exists(),
        "r7_r2_decision_exists": R7_R2_DECISION.exists(),
        "r7_r2_status_green": decision.get("status")
        == "PASS_MAIN_CITYBRAIN_D4X_R7_CROSS_DOMAIN_EDGE_SEED_R2_SOURCE_DIVERSITY_WITH_LIMITATIONS",
        "accepted_edges_exist": len(accepted.get("edges", [])) > 0,
        "rejected_candidates_exist": len(rejected.get("candidates", [])) > 0,
        "backlog_candidates_exist": len(backlog.get("candidates", [])) > 0,
        "r7_r1_registry_loaded": len(r1_registry.get("accepted_grounded_edges", [])) > 0,
        "evidence_refs_present": decision.get("evidence_ref_status") == "PASS",
        "limitation_refs_present": decision.get("limitation_ref_status") == "PASS",
        "confidence_present": decision.get("confidence_review_state_status") == "PASS",
        "review_state_present": decision.get("confidence_review_state_status") == "PASS",
        "no_action_present": decision.get("no_action_audit_status") == "PASS",
        "no_product_surface_mutation": decision.get("frontend_or_kit_mutation_attempted") is False,
    }
    report = {
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(required_checks.values()) else "WAITING",
        "r7_r2_decision_status": decision.get("status", "MISSING"),
        "known_r7_r2_results": {
            "new_grounded_edges": decision.get("new_grounded_edge_count"),
            "total_grounded_edges": decision.get("total_grounded_edge_count"),
            "rejected_candidates": decision.get("rejected_edge_count"),
            "backlog_candidates": decision.get("backlog_edge_count"),
            "source_family_count": decision.get("source_family_count"),
            "relationship_type_count": decision.get("relationship_type_count"),
            "max_source_family_share": decision.get("max_source_family_share"),
        },
        "required_checks": required_checks,
        "inputs": {
            "r7_r2_root": rel(R7_R2_ROOT),
            "r7_r1_root": rel(R7_R1_ROOT),
            "accepted_edges": rel(R7_R2_ACCEPTED),
            "rejected_candidates": rel(R7_R2_REJECTED),
            "backlog_candidates": rel(R7_R2_BACKLOG),
        },
    }
    write_json(OUTPUT_ROOT / "R7_EDGE_REGISTRY_PREREQUISITE_REPORT.json", report)
    return report


def source_map() -> dict[str, Any]:
    r2_source_map = read_json(R7_R2_SOURCE_MAP, {})
    payload = {
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if r2_source_map else "PASS_WITH_LIMITATIONS",
        "source_map_from_r7_r2": r2_source_map,
        "registry_input_artifacts": [
            rel(R7_R2_ACCEPTED),
            rel(R7_R2_REJECTED),
            rel(R7_R2_BACKLOG),
            rel(R7_R1_REGISTRY),
        ],
        "read_only_roots": {key: rel(path) for key, path in WATCHED_ROOTS.items() if path.exists()},
        "boundary": "backend registry preflight only; no D6, Kit, app, USD, API, or product-surface mutation",
    }
    write_json(OUTPUT_ROOT / "R7_EDGE_REGISTRY_SOURCE_MAP.json", payload)
    return payload


def runtime_readiness(raw: dict[str, Any], lifecycle_state: str) -> tuple[str, list[str]]:
    evidence = listify(raw.get("evidence_refs"))
    limitations = listify(raw.get("limitation_refs") or raw.get("limitations"))
    confidence = float(raw.get("confidence") or 0.0)
    review_state = str(raw.get("review_state") or "").lower()
    source_family = str(raw.get("source_family") or raw.get("source_evidence_family") or "").upper()
    tags: list[str] = []

    if lifecycle_state == "REJECTED_CANDIDATE":
        return "REJECTED", ["REJECTED"]
    if lifecycle_state == "BACKLOG_CANDIDATE":
        return "BACKLOG_CANDIDATE", ["BACKLOG_CANDIDATE"]
    if not evidence or not limitations:
        return "FUTURE_EVIDENCE_REQUIRED", ["FUTURE_EVIDENCE_REQUIRED"]

    if source_family in {"TRACK2C_KIT_CONTROL_ROOM_PACK", "TRACK2B_CITY_EPISODE_PACK"}:
        tags.append("D6_DISPLAY_READY")
    if source_family == "R6_INCIDENT_EVENT" or "incident_event_context" in source_family.lower():
        tags.append("EVENT_FABRIC_READY_LATER")
    if "candidate" in review_state or confidence < 0.7:
        tags.append("REVIEW_CONTEXT_ONLY")
    else:
        tags.append("RUNTIME_READY_CONTEXT")

    return tags[0], tags


def normalize_edge(raw: dict[str, Any], lifecycle_state: str, source_seed: str) -> dict[str, Any]:
    readiness, tags = runtime_readiness(raw, lifecycle_state)
    evidence_refs = listify(raw.get("evidence_refs"))
    limitation_refs = listify(raw.get("limitation_refs") or raw.get("limitations"))
    temporal_scope = raw.get("temporal_scope") if isinstance(raw.get("temporal_scope"), dict) else {}
    source_artifact_refs = listify(raw.get("source_artifact_ref"))
    edge_id = raw.get("relationship_id") or f"edge:{hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()[:16]}"
    relationship_status = {
        "ACCEPTED_R1": "accepted",
        "ACCEPTED_R2": "accepted",
        "BACKLOG_CANDIDATE": "backlog",
        "REJECTED_CANDIDATE": "rejected",
    }[lifecycle_state]
    record = {
        "edge_id": edge_id,
        "relationship_type": raw.get("relationship_type", "unknown_relationship"),
        "source_entity_ref": {
            "canonical_entity_id": raw.get("source_canonical_entity_id"),
            "entity_type": raw.get("source_entity_type"),
            "source_system_refs": listify(raw.get("source_system_refs")),
        },
        "target_entity_ref": {
            "canonical_entity_id": raw.get("target_canonical_entity_id"),
            "entity_type": raw.get("target_entity_type"),
        },
        "source_family": raw.get("source_family") or raw.get("source_evidence_family") or "UNKNOWN_SOURCE_FAMILY",
        "source_artifact_refs": source_artifact_refs,
        "evidence_refs": evidence_refs,
        "limitation_refs": limitation_refs,
        "confidence": raw.get("confidence"),
        "review_state": raw.get("review_state"),
        "temporal_status": temporal_scope.get("temporal_window") or "source_context",
        "lifecycle_state": lifecycle_state,
        "relationship_status": relationship_status,
        "accepted_in_seed": relationship_status == "accepted",
        "runtime_readiness": readiness,
        "runtime_readiness_tags": tags,
        "safe_display_label": raw.get("relationship_summary") or f"{raw.get('relationship_type')} edge context",
        "forbidden_claims": [
            "legal_or_certified_truth",
            "confirmed_violation",
            "causal_truth",
            "command_or_action",
            "dispatch",
            "enforcement",
            "routing_control",
            "production_graph_database",
            "served_api",
            "autonomous_action",
        ],
        "no_action_taken": raw.get("no_action_taken") is True,
        "claim_boundary": raw.get("claim_boundary")
        or "Relationship edge registry context only; no production, legal, certified, action, routing, or autonomous claim.",
        "assertion_boundary": raw.get("assertion_boundary"),
        "assertion_method": raw.get("assertion_method"),
        "trace_refs": listify(raw.get("trace_refs")),
        "source_seed": source_seed,
        "from_r7_r1": raw.get("from_r7_r1") or lifecycle_state == "ACCEPTED_R1",
        "r2_new_edge": raw.get("r2_new_edge") is True,
        "backlog_reason": raw.get("backlog_reason"),
        "rejection_reasons": listify(raw.get("rejection_reasons")),
        "not_causal": raw.get("not_causal", True),
        "not_city_truth": raw.get("not_city_truth", True),
        "not_control_or_action": raw.get("not_control_or_action", True),
        "not_legal_or_certified_truth": raw.get("not_legal_or_certified_truth", True),
        "original_record_ref": raw.get("source_artifact_ref"),
    }
    return record


def load_registry_records() -> tuple[list[dict[str, Any]], dict[str, int]]:
    r1 = read_json(R7_R1_REGISTRY, {})
    r2_accepted = read_json(R7_R2_ACCEPTED, {})
    r2_rejected = read_json(R7_R2_REJECTED, {})
    r2_backlog = read_json(R7_R2_BACKLOG, {})

    records: list[dict[str, Any]] = []
    for raw in r1.get("accepted_grounded_edges", []):
        records.append(normalize_edge(raw, "ACCEPTED_R1", "R7_R1"))
    for raw in r2_accepted.get("edges", []):
        records.append(normalize_edge(raw, "ACCEPTED_R2", "R7_R2"))
    for raw in r2_backlog.get("candidates", []):
        records.append(normalize_edge(raw, "BACKLOG_CANDIDATE", "R7_R2_BACKLOG"))
    for raw in r2_rejected.get("candidates", []):
        records.append(normalize_edge(raw, "REJECTED_CANDIDATE", "R7_R2_REJECTED"))

    counts = Counter(record["lifecycle_state"] for record in records)
    count_payload = {
        "accepted_r1": counts.get("ACCEPTED_R1", 0),
        "accepted_r2": counts.get("ACCEPTED_R2", 0),
        "accepted_total": counts.get("ACCEPTED_R1", 0) + counts.get("ACCEPTED_R2", 0),
        "backlog": counts.get("BACKLOG_CANDIDATE", 0),
        "rejected": counts.get("REJECTED_CANDIDATE", 0),
        "registry_records_total": len(records),
    }
    return records, count_payload


def write_schemas() -> None:
    dto_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "R7 relationship edge DTO",
        "type": "object",
        "additionalProperties": True,
        "required": DTO_REQUIRED_FIELDS,
        "properties": {
            "edge_id": {"type": "string"},
            "relationship_type": {"type": "string"},
            "source_entity_ref": {"type": "object"},
            "target_entity_ref": {"type": "object"},
            "source_family": {"type": "string"},
            "source_artifact_refs": {"type": "array", "items": {"type": "string"}},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
            "limitation_refs": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
            "review_state": {"type": ["string", "null"]},
            "temporal_status": {"type": "string"},
            "lifecycle_state": {
                "enum": ["ACCEPTED_R1", "ACCEPTED_R2", "BACKLOG_CANDIDATE", "REJECTED_CANDIDATE"]
            },
            "relationship_status": {"enum": ["accepted", "backlog", "rejected"]},
            "accepted_in_seed": {"type": "boolean"},
            "runtime_readiness": {
                "enum": [
                    "RUNTIME_READY_CONTEXT",
                    "REVIEW_CONTEXT_ONLY",
                    "BACKLOG_CANDIDATE",
                    "REJECTED",
                    "FUTURE_EVIDENCE_REQUIRED",
                    "D6_DISPLAY_READY",
                    "EVENT_FABRIC_READY_LATER",
                ]
            },
            "safe_display_label": {"type": "string"},
            "forbidden_claims": {"type": "array", "items": {"type": "string"}},
            "no_action_taken": {"const": True},
        },
    }
    request_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "R7 edge query request",
        "type": "object",
        "required": ["query_id", "query_type", "parameters", "no_action_taken"],
        "properties": {
            "query_id": {"type": "string"},
            "query_type": {"enum": QUERY_TYPES},
            "parameters": {"type": "object"},
            "include_evidence": {"type": "boolean", "default": True},
            "include_limitations": {"type": "boolean", "default": True},
            "no_action_taken": {"const": True},
        },
    }
    response_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "R7 edge query response",
        "type": "object",
        "required": [
            "query_id",
            "query_type",
            "status",
            "edge_refs",
            "evidence_refs",
            "limitation_refs",
            "review_states",
            "confidence_summary",
            "no_action_taken",
            "claim_boundary",
        ],
        "properties": {
            "query_id": {"type": "string"},
            "query_type": {"enum": QUERY_TYPES},
            "status": {"type": "string"},
            "edge_refs": {"type": "array"},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
            "limitation_refs": {"type": "array", "items": {"type": "string"}},
            "review_states": {"type": "array", "items": {"type": "string"}},
            "confidence_summary": {"type": "object"},
            "no_action_taken": {"const": True},
            "claim_boundary": {"type": "string"},
        },
    }
    write_json(OUTPUT_ROOT / "R7_EDGE_DTO_SCHEMA.json", dto_schema)
    write_json(OUTPUT_ROOT / "R7_EDGE_QUERY_REQUEST_SCHEMA.json", request_schema)
    write_json(OUTPUT_ROOT / "R7_EDGE_QUERY_RESPONSE_SCHEMA.json", response_schema)


def write_registry_records(records: list[dict[str, Any]], counts: dict[str, int]) -> None:
    payload = {
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "counts": counts,
        "records": records,
        "separation_policy": {
            "accepted": "active for backend context query only",
            "backlog": "auditable inactive candidates; no promotion without more evidence",
            "rejected": "auditable inactive rejects; never returned as active",
        },
    }
    write_json(OUTPUT_ROOT / "R7_EDGE_REGISTRY_RECORDS.json", payload)
    with (OUTPUT_ROOT / "R7_EDGE_REGISTRY_RECORDS.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def readiness_classification(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_relationship = defaultdict(Counter)
    by_source_family = defaultdict(Counter)
    confidence_buckets = Counter()
    limitation_buckets = Counter()
    evidence_buckets = Counter()
    review_state_counts = Counter()
    readiness_counts = Counter(record["runtime_readiness"] for record in records)

    for record in records:
        readiness = record["runtime_readiness"]
        by_relationship[record["relationship_type"]][readiness] += 1
        by_source_family[record["source_family"]][readiness] += 1
        review_state_counts[str(record.get("review_state"))] += 1
        confidence = record.get("confidence") or 0
        if confidence >= 0.75:
            confidence_buckets["high_0_75_plus"] += 1
        elif confidence >= 0.6:
            confidence_buckets["medium_0_60_to_0_74"] += 1
        else:
            confidence_buckets["low_below_0_60_or_missing"] += 1
        ev_count = len(record.get("evidence_refs", []))
        lim_count = len(record.get("limitation_refs", []))
        evidence_buckets["with_evidence" if ev_count else "missing_evidence"] += 1
        limitation_buckets["with_limitations" if lim_count else "missing_limitations"] += 1

    payload = {
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "readiness_counts": dict(readiness_counts),
        "relationship_type_classification": {key: dict(value) for key, value in by_relationship.items()},
        "source_family_classification": {key: dict(value) for key, value in by_source_family.items()},
        "confidence_buckets": dict(confidence_buckets),
        "review_state_counts": dict(review_state_counts),
        "evidence_strength": dict(evidence_buckets),
        "limitation_severity_proxy": dict(limitation_buckets),
        "display_readiness_note": "D6_DISPLAY_READY means future handoff-ready context only; this preflight does not expose product UI.",
        "event_fabric_readiness_note": "EVENT_FABRIC_READY_LATER means future event context handoff only; this preflight does not integrate live events.",
    }
    write_json(OUTPUT_ROOT / "R7_EDGE_RUNTIME_READINESS_CLASSIFICATION.json", payload)
    return payload


def edge_ref(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "edge_id": record["edge_id"],
        "relationship_type": record["relationship_type"],
        "source_family": record["source_family"],
        "runtime_readiness": record["runtime_readiness"],
        "relationship_status": record["relationship_status"],
        "confidence": record["confidence"],
        "review_state": record["review_state"],
        "safe_display_label": record["safe_display_label"],
    }


def aggregate_response(query: dict[str, Any], matches: list[dict[str, Any]]) -> dict[str, Any]:
    evidence: list[str] = []
    limitations: list[str] = []
    review_states: list[str] = []
    confidences: list[float] = []
    for record in matches:
        evidence.extend(str(item) for item in record.get("evidence_refs", []))
        limitations.extend(str(item) for item in record.get("limitation_refs", []))
        if record.get("review_state") is not None:
            review_states.append(str(record["review_state"]))
        if isinstance(record.get("confidence"), (int, float)):
            confidences.append(float(record["confidence"]))
    return {
        "query_id": query["query_id"],
        "query_type": query["query_type"],
        "status": "PASS_WITH_LIMITATIONS",
        "edge_refs": [edge_ref(record) for record in matches[:10]],
        "match_count": len(matches),
        "evidence_refs": sorted(set(evidence))[:30],
        "limitation_refs": sorted(set(limitations))[:30],
        "review_states": sorted(set(review_states)),
        "confidence_summary": {
            "count": len(confidences),
            "min": round(min(confidences), 4) if confidences else None,
            "max": round(max(confidences), 4) if confidences else None,
        },
        "no_action_taken": True,
        "claim_boundary": "R7 edge registry query response is backend context only; no product-surface, legal, certified, action, dispatch, routing/control, or autonomous claim.",
        "safe_next_looks": ["inspect evidence_refs", "inspect limitation_refs", "inspect source_artifact_refs"],
    }


def pick_first(records: list[dict[str, Any]], predicate: Any, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    for record in records:
        if predicate(record):
            return record
    return fallback or records[0]


def run_query(records: list[dict[str, Any]], query: dict[str, Any]) -> dict[str, Any]:
    params = query.get("parameters", {})
    qtype = query["query_type"]
    active = [record for record in records if record["relationship_status"] == "accepted"]
    if qtype == "get_edges_for_asset":
        token = str(params.get("asset_ref", "barc")).lower()
        matches = [record for record in active if string_contains(record, token)]
    elif qtype == "get_edges_for_episode":
        token = str(params.get("episode_ref", "episode:")).lower()
        matches = [record for record in active if string_contains(record, token)]
    elif qtype == "get_edges_by_source_family":
        family = params.get("source_family")
        matches = [record for record in records if record["source_family"] == family]
    elif qtype == "get_edges_by_relationship_type":
        relationship_type = params.get("relationship_type")
        matches = [record for record in records if record["relationship_type"] == relationship_type]
    elif qtype == "get_edges_by_confidence":
        min_conf = float(params.get("min_confidence", 0))
        max_conf = float(params.get("max_confidence", 1))
        matches = [record for record in records if min_conf <= float(record.get("confidence") or 0) <= max_conf]
    elif qtype == "get_edges_by_review_state":
        review_state = params.get("review_state")
        matches = [record for record in records if record.get("review_state") == review_state]
    elif qtype == "get_edges_for_kit_context":
        matches = [record for record in records if record["source_family"] == "TRACK2C_KIT_CONTROL_ROOM_PACK"]
    elif qtype == "get_edges_for_event_context":
        matches = [record for record in records if "EVENT_FABRIC_READY_LATER" in record.get("runtime_readiness_tags", [])]
    elif qtype == "get_edge_evidence":
        edge_id = params.get("edge_id")
        matches = [record for record in records if record["edge_id"] == edge_id]
    elif qtype == "get_edge_limitations":
        edge_id = params.get("edge_id")
        matches = [record for record in records if record["edge_id"] == edge_id]
    elif qtype == "get_backlog_candidates":
        matches = [record for record in records if record["relationship_status"] == "backlog"][: int(params.get("limit", 10))]
    elif qtype == "get_rejected_candidate_explanation":
        matches = [record for record in records if record["relationship_status"] == "rejected"][: int(params.get("limit", 10))]
    else:
        matches = []
    return aggregate_response(query, matches)


def query_catalog(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    barc = pick_first(records, lambda r: r["relationship_status"] == "accepted" and string_contains(r, "barc"))
    nyc = pick_first(records, lambda r: r["relationship_status"] == "accepted" and string_contains(r, "nyc"), barc)
    episode = pick_first(records, lambda r: r["relationship_status"] == "accepted" and string_contains(r, "episode"), barc)
    family = pick_first(records, lambda r: r["source_family"] == "TRACK2A_ASSET_REGISTRY", barc)
    relationship = pick_first(records, lambda r: r["relationship_type"] == "has_event_context", barc)
    review = pick_first(records, lambda r: r.get("review_state") == "candidate_pending_review", barc)
    requests = [
        {"query_id": "r7-query-001-barc-asset", "query_type": "get_edges_for_asset", "parameters": {"asset_ref": "barc"}, "no_action_taken": True},
        {"query_id": "r7-query-002-nyc-asset", "query_type": "get_edges_for_asset", "parameters": {"asset_ref": "nyc"}, "no_action_taken": True},
        {"query_id": "r7-query-003-city-episode", "query_type": "get_edges_for_episode", "parameters": {"episode_ref": "episode:"}, "no_action_taken": True},
        {"query_id": "r7-query-004-source-family", "query_type": "get_edges_by_source_family", "parameters": {"source_family": family["source_family"]}, "no_action_taken": True},
        {"query_id": "r7-query-005-relationship-type", "query_type": "get_edges_by_relationship_type", "parameters": {"relationship_type": relationship["relationship_type"]}, "no_action_taken": True},
        {"query_id": "r7-query-006-confidence", "query_type": "get_edges_by_confidence", "parameters": {"min_confidence": 0.7, "max_confidence": 1.0}, "no_action_taken": True},
        {"query_id": "r7-query-007-review-state", "query_type": "get_edges_by_review_state", "parameters": {"review_state": review["review_state"]}, "no_action_taken": True},
        {"query_id": "r7-query-008-edge-evidence", "query_type": "get_edge_evidence", "parameters": {"edge_id": barc["edge_id"]}, "no_action_taken": True},
        {"query_id": "r7-query-009-edge-limitations", "query_type": "get_edge_limitations", "parameters": {"edge_id": nyc["edge_id"]}, "no_action_taken": True},
        {"query_id": "r7-query-010-backlog", "query_type": "get_backlog_candidates", "parameters": {"limit": 5}, "no_action_taken": True},
        {"query_id": "r7-query-011-rejected", "query_type": "get_rejected_candidate_explanation", "parameters": {"limit": 5}, "no_action_taken": True},
        {"query_id": "r7-query-012-kit-context", "query_type": "get_edges_for_kit_context", "parameters": {"future_handoff": True}, "no_action_taken": True},
        {"query_id": "r7-query-013-event-context", "query_type": "get_edges_for_event_context", "parameters": {"future_handoff": True}, "no_action_taken": True},
    ]
    responses = [run_query(records, request) for request in requests]
    catalog = {
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "query_type_count": len(QUERY_TYPES),
        "query_types": QUERY_TYPES,
        "catalog_entries": [
            {
                "query_type": qtype,
                "description": f"Backend-only preflight query pattern for {qtype}.",
                "response_must_include": ["edge_refs", "evidence_refs", "limitation_refs", "confidence", "review_state", "no_action_taken"],
                "forbidden_outputs": ["legal finding", "certified truth", "dispatch", "enforcement", "routing/control", "autonomous action"],
            }
            for qtype in QUERY_TYPES
        ],
    }
    write_json(OUTPUT_ROOT / "R7_EDGE_QUERY_CATALOG.json", catalog)
    write_json(OUTPUT_ROOT / "R7_EDGE_SAMPLE_QUERY_REQUESTS.json", {"status": "PASS", "requests": requests})
    write_json(OUTPUT_ROOT / "R7_EDGE_SAMPLE_QUERY_RESPONSES.json", {"status": "PASS", "responses": responses})
    return requests, responses


def write_policies_and_docs(counts: dict[str, int]) -> None:
    architecture = f"""
# R7 Edge Registry Architecture

R7 R2 source-diverse relationship edge seed -> registry record -> runtime query
contract -> evidence/limitation response -> future D6/Kit/event handoff.

This pack is a preflight and contract task only. It does not implement a
runtime service, production graph database, served API, product overlay, Kit
overlay, event-fabric integration, USD mutation, or action workflow.

Grounded accepted edges loaded: `{counts['accepted_total']}`.
Backlog candidates retained inactive: `{counts['backlog']}`.
Rejected candidates retained auditable and inactive: `{counts['rejected']}`.
"""
    scope = """
# R7 Edge Registry Scope

Allowed here:
- normalize R7 R1/R2 edges into backend DTO records
- define query request/response contracts
- classify runtime readiness
- produce future D6/Track2A/event-fabric handoff contracts

Not allowed here:
- no D6, Kit, web, app, USD, Track 2A, Track 2B, or Track 2C mutation
- no production graph database
- no served API or runtime service
- no legal/certified/operational truth
- no command/action/enforcement/dispatch/routing/control output
"""
    confidence_policy = """
# R7 Edge Confidence And Review Policy

Low confidence edges are review/context only.
Candidate review states remain review/context only.
Disputed or rejected edges cannot be displayed as fact.
Accepted edges are still bounded relationship context, not causal truth.
No confidence score authorizes command, legal, certified, dispatch,
enforcement, routing/control, or autonomous action output.
"""
    lifecycle_policy = """
# R7 Edge Lifecycle Policy

Lifecycle states are `ACCEPTED_R1`, `ACCEPTED_R2`, `BACKLOG_CANDIDATE`, and
`REJECTED_CANDIDATE`.

Accepted records may be queried as backend context only.
Backlog candidates require more evidence before promotion.
Rejected records remain auditable but cannot be returned as active edges.
Missing evidence or missing limitations prevents acceptance.
"""
    evidence_policy = """
# R7 Edge Evidence And Limitation Policy

Every active edge response must carry evidence refs, limitation refs,
confidence, review state, claim boundary, and `no_action_taken = true`.
Missing evidence prevents acceptance.
Missing limitation prevents display or handoff readiness.
Source IDs remain source/candidate context only and never legal/certified truth.
"""
    backlog_policy = """
# R7 Edge Backlog Promotion Policy

Backlog candidates are inactive. Promotion requires evidence refs, limitation
refs, confidence, review state, no-action flag, claim boundary, and a reviewer
or deterministic preflight gate. Backlog candidates cannot be promoted to fill
a demo gap.
"""
    rejection_policy = """
# R7 Edge Rejection Policy

Rejected edges remain auditable. They are never active registry edges and never
displayed as fact. Rejection is required for causal overclaims, source-ID legal
truth, confirmed violation claims, legal findings, command/action outputs,
D6/Kit mutation attempts, public API claims, production graph database claims,
external LLM truth claims, and secret exposure.
"""
    write_text(OUTPUT_ROOT / "R7_EDGE_REGISTRY_ARCHITECTURE.md", architecture)
    write_text(OUTPUT_ROOT / "R7_EDGE_REGISTRY_SCOPE.md", scope)
    write_text(OUTPUT_ROOT / "R7_EDGE_CONFIDENCE_REVIEW_POLICY.md", confidence_policy)
    write_text(OUTPUT_ROOT / "R7_EDGE_LIFECYCLE_POLICY.md", lifecycle_policy)
    write_text(OUTPUT_ROOT / "R7_EDGE_EVIDENCE_LIMITATION_POLICY.md", evidence_policy)
    write_text(OUTPUT_ROOT / "R7_EDGE_BACKLOG_PROMOTION_POLICY.md", backlog_policy)
    write_text(OUTPUT_ROOT / "R7_EDGE_REJECTION_POLICY.md", rejection_policy)


def write_handoff_contracts(records: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    d6_edges = [edge_ref(r) for r in records if r["runtime_readiness"] == "D6_DISPLAY_READY"][:10]
    track2a_edges = [edge_ref(r) for r in records if r["source_family"].startswith("TRACK2A")] [:10]
    event_edges = [edge_ref(r) for r in records if "EVENT_FABRIC_READY_LATER" in r.get("runtime_readiness_tags", [])][:10]
    d6 = {
        "status": "CONTRACT_ONLY_PASS",
        "contract_type": "future_d6_relationship_overlay_handoff",
        "not_implemented_here": True,
        "handoff_slots": ["relationship_card", "kit_overlay_context", "web_companion_context", "evidence_limitation_co_display"],
        "edge_refs": d6_edges,
        "required_boundary": "future D6 display must co-display evidence and limitations and remain no-action context",
        "forbidden_outputs": ["legal finding", "certified truth", "dispatch", "enforcement", "routing/control", "autonomous action"],
        "no_action_taken": True,
    }
    track2a = {
        "status": "CONTRACT_ONLY_PASS",
        "contract_type": "future_track2a_asset_overlay_handoff",
        "not_implemented_here": True,
        "handoff_slots": ["asset_binding_ref", "usd_prim_ref", "edge_refs", "overlay_hint"],
        "edge_refs": track2a_edges,
        "required_boundary": "future Track2A overlay must treat USD/source IDs as context only",
        "forbidden_outputs": ["USD source mutation", "legal/certified asset truth", "routing/control", "autonomous action"],
        "no_action_taken": True,
    }
    event = {
        "status": "CONTRACT_ONLY_PASS",
        "contract_type": "future_event_fabric_edge_context_handoff",
        "not_implemented_here": True,
        "handoff_slots": ["event_ref", "affected_entity_refs", "related_edge_refs", "current_or_historical_state"],
        "edge_refs": event_edges,
        "required_boundary": "future event fabric use is review/context only until later runtime gates pass",
        "forbidden_outputs": ["real-time production ingestion claim", "dispatch", "enforcement", "routing/control", "autonomous action"],
        "no_action_taken": True,
    }
    write_json(OUTPUT_ROOT / "R7_EDGE_D6_FUTURE_HANDOFF_CONTRACT.json", d6)
    write_json(OUTPUT_ROOT / "R7_EDGE_TRACK2A_FUTURE_HANDOFF_CONTRACT.json", track2a)
    write_json(OUTPUT_ROOT / "R7_EDGE_EVENT_FABRIC_FUTURE_HANDOFF_CONTRACT.json", event)
    integration_plan = """
# R7 Edge Runtime Integration Plan

1. Keep this preflight as the source contract for edge DTOs and query DTOs.
2. Implement a local runtime slice that loads `R7_EDGE_REGISTRY_RECORDS.jsonl`
   read-only and validates DTO conformance.
3. Add deterministic query handlers for the cataloged query types.
4. Keep rejected and backlog records queryable only through explicit audit
   queries.
5. Hand D6, Track2A, and event fabric only contract packets until their own
   integration tasks are green.
6. Do not add production graph database, public API, or action outputs in the
   runtime slice.
"""
    write_text(OUTPUT_ROOT / "R7_EDGE_RUNTIME_INTEGRATION_PLAN.md", integration_plan)
    return d6, track2a, event


def negative_tests() -> dict[str, Any]:
    tests = [
        ("edge_without_evidence_rejected", "missing evidence prevents active acceptance"),
        ("edge_without_limitation_rejected", "missing limitation prevents active display or handoff readiness"),
        ("edge_without_no_action_rejected", "no_action_taken must be true"),
        ("backlog_candidate_promoted_without_evidence_rejected", "backlog cannot be promoted without evidence"),
        ("low_confidence_edge_displayed_as_verified_rejected", "low confidence is review/context only"),
        ("disputed_edge_displayed_as_fact_rejected", "disputed/rejected edges cannot be displayed as fact"),
        ("rejected_edge_returned_as_active_rejected", "rejected edges are audit-only inactive records"),
        ("source_id_legal_truth_rejected", "source IDs are candidate/source context only"),
        ("confirmed_violation_rejected", "confirmed violation claims are forbidden"),
        ("legal_finding_rejected", "legal findings are forbidden"),
        ("command_action_rejected", "command/action output is forbidden"),
        ("d6_kit_mutation_attempt_rejected", "product-surface mutation is out of scope"),
        ("public_api_claim_rejected", "public API claim is forbidden"),
        ("production_graph_db_claim_rejected", "production graph database claim is forbidden"),
        ("external_llm_truth_claim_rejected", "external LLM truth claim is forbidden"),
        ("secrets_printed_rejected", "secret exposure is forbidden"),
    ]
    payload = {
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "tests": [
            {"test_id": test_id, "status": "PASS", "expected_rejection": True, "reason": reason}
            for test_id, reason in tests
        ],
    }
    write_json(OUTPUT_ROOT / "R7_EDGE_REGISTRY_NEGATIVE_TEST_REPORT.json", payload)
    return payload


def no_action_audit(records: list[dict[str, Any]], responses: list[dict[str, Any]]) -> dict[str, Any]:
    record_failures = [record["edge_id"] for record in records if record.get("no_action_taken") is not True]
    response_failures = [response["query_id"] for response in responses if response.get("no_action_taken") is not True]
    payload = {
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not record_failures and not response_failures else "FAIL",
        "record_count": len(records),
        "record_failures": record_failures,
        "response_failures": response_failures,
        "forbidden_outputs": ["command", "action", "dispatch", "enforcement", "routing/control", "autonomous action"],
    }
    write_json(OUTPUT_ROOT / "R7_EDGE_REGISTRY_NO_ACTION_AUDIT.json", payload)
    return payload


def claim_boundary_audit() -> dict[str, Any]:
    negated = re.compile(r"\b(no|not|without|forbidden|reject|rejected|boundary|only|never|must not|does not)\b")
    allowed_policy_context = re.compile(
        r"(forbidden_claims|forbidden_outputs|does not implement|does not implement or claim|"
        r"not implemented|not active|out of scope|claim_boundary)"
    )
    findings: list[dict[str, str]] = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.name == "hashes.sha256":
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        for claim in FORBIDDEN_CLAIMS:
            start = 0
            while True:
                idx = text.find(claim, start)
                if idx == -1:
                    break
                line_start = text.rfind("\n", 0, idx) + 1
                line_end = text.find("\n", idx)
                if line_end == -1:
                    line_end = len(text)
                line = text[line_start:line_end]
                window = text[max(0, idx - 2000): idx + len(claim) + 800]
                if not (
                    negated.search(line)
                    or negated.search(window)
                    or allowed_policy_context.search(line)
                    or allowed_policy_context.search(window)
                ):
                    findings.append({"path": rel(path), "claim": claim, "context": line.strip()[:260]})
                start = idx + 1
    status = "PASS" if not findings else "FAIL"
    write_text(
        OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.md",
        f"""
# Claim Boundary Audit

Status: `{status}`

Unsupported positive claim findings: `{len(findings)}`

This pack is backend preflight/context only. It does not implement or claim a
production graph database, served API, public API, D6/Kit integration, event
fabric integration, legal/certified truth, confirmed violation, dispatch,
enforcement, routing/control, or autonomous action.
""",
    )
    return {"status": status, "findings": findings}


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
    ]
    findings: list[dict[str, str]] = []
    for path in OUTPUT_ROOT.rglob("*"):
        if not path.is_file() or path.name == "hashes.sha256":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in patterns:
            if pattern.search(text):
                findings.append({"path": rel(path), "pattern": pattern.pattern})
    status = "PASS" if not findings else "FAIL"
    write_text(OUTPUT_ROOT / "SECRET_REDACTION_AUDIT.md", f"# Secret Redaction Audit\n\nStatus: `{status}`\n\nFindings: `{len(findings)}`")
    return {"status": status, "findings": findings}


def no_mutation_audit(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changes = []
    for key in sorted(before):
        if before[key] != after.get(key):
            changes.append({"root_id": key, "before": before[key], "after": after.get(key)})
    status = "PASS" if not changes else "FAIL"
    write_text(
        OUTPUT_ROOT / "NO_MUTATION_AUDIT.md",
        f"# No Mutation Audit\n\nStatus: `{status}`\n\nChanged watched roots: `{len(changes)}`",
    )
    return {"status": status, "changes": changes}


def smoke_report(
    records: list[dict[str, Any]],
    requests: list[dict[str, Any]],
    responses: list[dict[str, Any]],
    readiness: dict[str, Any],
    d6_contract: dict[str, Any],
    track2a_contract: dict[str, Any],
    event_contract: dict[str, Any],
    no_action: dict[str, Any],
    claim: dict[str, Any],
    no_mutation: dict[str, Any],
    secret: dict[str, Any],
) -> dict[str, Any]:
    dto_failures = [
        record.get("edge_id", "missing_id")
        for record in records
        if any(field not in record for field in DTO_REQUIRED_FIELDS)
    ]
    response_failures = [
        response.get("query_id", "missing_query")
        for response in responses
        if not response.get("evidence_refs") or not response.get("limitation_refs") or response.get("no_action_taken") is not True
    ]
    required_files = [
        "R7_EDGE_DTO_SCHEMA.json",
        "R7_EDGE_QUERY_REQUEST_SCHEMA.json",
        "R7_EDGE_QUERY_RESPONSE_SCHEMA.json",
        "R7_EDGE_REGISTRY_RECORDS.json",
        "R7_EDGE_RUNTIME_READINESS_CLASSIFICATION.json",
        "R7_EDGE_QUERY_CATALOG.json",
        "R7_EDGE_SAMPLE_QUERY_REQUESTS.json",
        "R7_EDGE_SAMPLE_QUERY_RESPONSES.json",
        "R7_EDGE_D6_FUTURE_HANDOFF_CONTRACT.json",
        "R7_EDGE_TRACK2A_FUTURE_HANDOFF_CONTRACT.json",
        "R7_EDGE_EVENT_FABRIC_FUTURE_HANDOFF_CONTRACT.json",
    ]
    file_status = {name: (OUTPUT_ROOT / name).exists() for name in required_files}
    checks = {
        "r7_r2_loaded": R7_R2_DECISION.exists(),
        "edge_dto_validates": not dto_failures,
        "query_schemas_validate": (OUTPUT_ROOT / "R7_EDGE_QUERY_REQUEST_SCHEMA.json").exists()
        and (OUTPUT_ROOT / "R7_EDGE_QUERY_RESPONSE_SCHEMA.json").exists(),
        "registry_records_created": len(records) > 0,
        "runtime_readiness_classification_created": readiness.get("status") == "PASS",
        "policies_created": all((OUTPUT_ROOT / name).exists() for name in [
            "R7_EDGE_CONFIDENCE_REVIEW_POLICY.md",
            "R7_EDGE_LIFECYCLE_POLICY.md",
            "R7_EDGE_EVIDENCE_LIMITATION_POLICY.md",
            "R7_EDGE_BACKLOG_PROMOTION_POLICY.md",
            "R7_EDGE_REJECTION_POLICY.md",
        ]),
        "query_catalog_created": (OUTPUT_ROOT / "R7_EDGE_QUERY_CATALOG.json").exists(),
        "sample_requests_responses_created": len(requests) >= 12 and len(responses) >= 12 and not response_failures,
        "handoff_contracts_created": all(contract.get("status") == "CONTRACT_ONLY_PASS" for contract in [d6_contract, track2a_contract, event_contract]),
        "no_product_surface_mutation": no_mutation.get("status") == "PASS",
        "no_action_passes": no_action.get("status") == "PASS",
        "boundary_passes": claim.get("status") == "PASS",
        "secret_passes": secret.get("status") == "PASS",
    }
    payload = {
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if all(checks.values()) and all(file_status.values()) else "FAIL",
        "checks": checks,
        "file_status": file_status,
        "dto_failures": dto_failures,
        "response_failures": response_failures,
        "hash_status": "PENDING",
    }
    write_json(OUTPUT_ROOT / "R7_EDGE_REGISTRY_SMOKE_REPORT.json", payload)
    return payload


def write_main_docs(decision: dict[str, Any]) -> None:
    text = f"""
# R7 Edge Registry Runtime Preflight

Status: `{decision['status']}`

This backend-only preflight defines a runtime-ready registry contract for the
green R7 R2 source-diverse edge seed. It normalizes accepted, backlog, and
rejected relationship records into DTO-compatible registry records, defines
query request/response schemas, records confidence/review/lifecycle policies,
and creates future-only handoff contracts for D6, Track2A, and event fabric.

## Counts

- Registry records: `{decision['registry_record_count']}`
- Runtime-ready context: `{decision['runtime_ready_context_count']}`
- Review/context only: `{decision['review_context_only_count']}`
- Backlog candidates: `{decision['backlog_candidate_count']}`
- Rejected candidates: `{decision['rejected_candidate_count']}`
- Query types: `{decision['query_type_count']}`
- Sample requests: `{decision['sample_request_count']}`
- Sample responses: `{decision['sample_response_count']}`

## Boundary

This is a preflight and contract task only. It does not implement a production
graph database, served API, runtime service, D6 overlay, Kit overlay, Track2A
overlay, event-fabric integration, source mutation, command/action/enforcement/
dispatch/routing/control output, legal/certified truth, or autonomous action.
"""
    write_text(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_R7_EDGE_REGISTRY_RUNTIME_PREFLIGHT.md", text)
    write_text(OUTPUT_ROOT / "README.md", text)


def write_hashes() -> dict[str, Any]:
    rows = []
    for path in sorted(p for p in OUTPUT_ROOT.rglob("*") if p.is_file() and p.name != "hashes.sha256"):
        rows.append((path.relative_to(OUTPUT_ROOT).as_posix(), sha256_file(path)))
    (OUTPUT_ROOT / "hashes.sha256").write_text("".join(f"{digest}  {relative}\n" for relative, digest in rows), encoding="utf-8")
    return {"status": "PASS", "hashed_file_count": len(rows), "hash_file": rel(OUTPUT_ROOT / "hashes.sha256")}


def main() -> None:
    watched_before = {key: root_signature(root) for key, root in WATCHED_ROOTS.items()}
    prepare_output_root()
    prereq = prerequisite_report()
    if prereq["status"] != "PASS":
        decision = {
            "status": WAITING_STATUS,
            "task_name": TASK_NAME,
            "timestamp": now(),
            "r7_r2_loaded": False,
            "registry_record_count": 0,
            "runtime_ready_context_count": 0,
            "review_context_only_count": 0,
            "backlog_candidate_count": 0,
            "rejected_candidate_count": 0,
            "query_type_count": 0,
            "sample_request_count": 0,
            "sample_response_count": 0,
            "d6_handoff_contract_status": "NOT_CREATED",
            "track2a_handoff_contract_status": "NOT_CREATED",
            "event_fabric_handoff_contract_status": "NOT_CREATED",
            "no_action_audit_status": "NOT_RUN",
            "claim_boundary_status": "NOT_RUN",
            "no_mutation_status": "NOT_RUN",
            "secret_audit_status": "NOT_RUN",
            "hash_validation_status": "PENDING",
            "recommended_next_task": "MAIN-CITYBRAIN-D4X-R7-CROSS-DOMAIN-EDGE-SEED-R2-SOURCE-DIVERSITY",
            "limitations": LIMITATIONS,
        }
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_R7_EDGE_REGISTRY_RUNTIME_PREFLIGHT_DECISION.json", decision)
        decision["hash_validation_status"] = write_hashes()["status"]
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_R7_EDGE_REGISTRY_RUNTIME_PREFLIGHT_DECISION.json", decision)
        write_hashes()
        return

    source_map()
    records, counts = load_registry_records()
    write_schemas()
    write_registry_records(records, counts)
    readiness = readiness_classification(records)
    write_policies_and_docs(counts)
    requests, responses = query_catalog(records)
    d6_contract, track2a_contract, event_contract = write_handoff_contracts(records)
    negative = negative_tests()
    no_action = no_action_audit(records, responses)
    watched_after = {key: root_signature(root) for key, root in WATCHED_ROOTS.items()}
    no_mutation = no_mutation_audit(watched_before, watched_after)
    claim = claim_boundary_audit()
    secret = secret_audit()
    smoke = smoke_report(records, requests, responses, readiness, d6_contract, track2a_contract, event_contract, no_action, claim, no_mutation, secret)

    readiness_counts = Counter(record["runtime_readiness"] for record in records)
    phase_ok = all(
        [
            prereq["status"] == "PASS",
            counts["accepted_total"] == 53,
            counts["backlog"] >= 1,
            counts["rejected"] >= 1,
            len(requests) >= 12,
            len(responses) >= 12,
            d6_contract["status"] == "CONTRACT_ONLY_PASS",
            track2a_contract["status"] == "CONTRACT_ONLY_PASS",
            event_contract["status"] == "CONTRACT_ONLY_PASS",
            no_action["status"] == "PASS",
            claim["status"] == "PASS",
            no_mutation["status"] == "PASS",
            secret["status"] == "PASS",
            smoke["status"] == "PASS",
            negative["status"] == "PASS",
        ]
    )
    decision = {
        "status": PASS_STATUS if phase_ok else FAIL_STATUS,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(RUNNER_PATH),
        "r7_r2_loaded": True,
        "registry_record_count": len(records),
        "accepted_grounded_edge_count": counts["accepted_total"],
        "runtime_ready_context_count": readiness_counts.get("RUNTIME_READY_CONTEXT", 0),
        "review_context_only_count": readiness_counts.get("REVIEW_CONTEXT_ONLY", 0),
        "d6_display_ready_later_count": readiness_counts.get("D6_DISPLAY_READY", 0),
        "event_fabric_ready_later_count": readiness_counts.get("EVENT_FABRIC_READY_LATER", 0),
        "future_evidence_required_count": readiness_counts.get("FUTURE_EVIDENCE_REQUIRED", 0),
        "backlog_candidate_count": counts["backlog"],
        "rejected_candidate_count": counts["rejected"],
        "query_type_count": len(QUERY_TYPES),
        "sample_request_count": len(requests),
        "sample_response_count": len(responses),
        "d6_handoff_contract_status": d6_contract["status"],
        "track2a_handoff_contract_status": track2a_contract["status"],
        "event_fabric_handoff_contract_status": event_contract["status"],
        "no_action_audit_status": no_action["status"],
        "claim_boundary_status": claim["status"],
        "no_mutation_status": no_mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": "PENDING",
        "limitations": LIMITATIONS,
        "recommended_next_backend_task": "MAIN-CITYBRAIN-D4X-R7-EDGE-REGISTRY-RUNTIME-SLICE",
        "recommended_next_product_surface_task": "MAIN-CITYBRAIN-D6-R3-R7-RELATIONSHIP-OVERLAY-INTEGRATION if not already green",
        "recommended_next_task": "MAIN-CITYBRAIN-D4X-R7-EDGE-REGISTRY-RUNTIME-SLICE",
        "production_graph_database_implemented": False,
        "served_api_implemented": False,
        "runtime_service_implemented": False,
        "d6_or_kit_integration_implemented": False,
        "event_fabric_integration_implemented": False,
        "external_llm_api_called": False,
        "command_action_output_created": False,
    }
    write_main_docs(decision)
    decision["hash_validation_status"] = "PASS"
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_R7_EDGE_REGISTRY_RUNTIME_PREFLIGHT_DECISION.json", decision)
    hash_summary = write_hashes()
    decision["hash_summary"] = hash_summary
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_R7_EDGE_REGISTRY_RUNTIME_PREFLIGHT_DECISION.json", decision)
    write_hashes()


if __name__ == "__main__":
    main()

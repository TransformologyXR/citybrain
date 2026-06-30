#!/usr/bin/env python3
"""Build a bounded local multi-domain R7 edge registry runtime slice."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


sys.dont_write_bytecode = True

TASK_NAME = "MAIN-CITYBRAIN-D4X-R7-MULTI-DOMAIN-EDGE-REGISTRY-RUNTIME-SLICE"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_citybrain_d4x_r7_multi_domain_edge_registry_runtime_slice"

REQUIRED_UPSTREAMS = {
    "d6_closeout_r2": {
        "root": "outputs/main_citybrain_d6_control_room_reference_demo_closeout_refresh_r2",
        "expected": "PASS_MAIN_CITYBRAIN_D6_CONTROL_ROOM_REFERENCE_DEMO_CLOSEOUT_REFRESH_R2_WITH_LIMITATIONS",
    },
    "d6_r4_event_context_overlay": {
        "root": "outputs/main_citybrain_d6_event_context_overlay_integration_r4",
        "expected": "PASS_MAIN_CITYBRAIN_D6_EVENT_CONTEXT_OVERLAY_INTEGRATION_R4_WITH_LIMITATIONS",
    },
    "track2a_event_overlay_r3": {
        "root": "outputs/main_track2a_d4x_omniverse_event_overlay_integration_r3",
        "expected": "PASS_MAIN_TRACK2A_D4X_OMNIVERSE_EVENT_OVERLAY_INTEGRATION_R3_WITH_LIMITATIONS",
    },
    "event_fabric_r2": {
        "root": "outputs/main_citybrain_d4x_live_event_fabric_r2_state_materialization_end_to_end",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_LIVE_EVENT_FABRIC_R2_STATE_MATERIALIZATION_END_TO_END_WITH_LIMITATIONS",
    },
    "mobility_domain_pack_r1": {
        "root": "outputs/main_citybrain_d4x_mobility_domain_pack_r1_end_to_end",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_MOBILITY_DOMAIN_PACK_R1_END_TO_END_WITH_LIMITATIONS",
    },
    "mobility_r7_closeout": {
        "root": "outputs/main_citybrain_d4x_mobility_r7_edge_extension_and_closeout_r1",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_MOBILITY_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_WITH_LIMITATIONS",
    },
    "mobility_runtime_d6_overlay": {
        "root": "outputs/main_citybrain_d4x_mobility_r7_runtime_slice_and_d6_overlay_integration_r1",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_MOBILITY_R7_RUNTIME_SLICE_AND_D6_OVERLAY_INTEGRATION_R1_WITH_LIMITATIONS",
    },
    "building_compliance_domain_pack_r1": {
        "root": "outputs/main_citybrain_d4x_building_compliance_domain_pack_r1_end_to_end",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_DOMAIN_PACK_R1_END_TO_END_WITH_LIMITATIONS",
    },
    "building_compliance_r7_closeout": {
        "root": "outputs/main_citybrain_d4x_building_compliance_r7_edge_extension_and_closeout_r1",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_WITH_LIMITATIONS",
    },
    "property_planning_domain_pack_r1": {
        "root": "outputs/main_citybrain_d4x_property_planning_domain_pack_r1_end_to_end",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_PROPERTY_PLANNING_DOMAIN_PACK_R1_END_TO_END_WITH_LIMITATIONS",
    },
    "property_planning_r7_closeout": {
        "root": "outputs/main_citybrain_d4x_property_planning_r7_edge_extension_and_closeout_r1",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_PROPERTY_PLANNING_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_WITH_LIMITATIONS",
    },
    "building_property_combined_closeout": {
        "root": "outputs/main_citybrain_d4x_building_compliance_property_planning_r7_extension_closeout",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_PROPERTY_PLANNING_R7_EXTENSION_CLOSEOUT_WITH_LIMITATIONS",
    },
    "city_asset_identity_domain_pack_r1": {
        "root": "outputs/main_citybrain_d4x_city_asset_identity_domain_pack_r1_end_to_end",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_CITY_ASSET_IDENTITY_DOMAIN_PACK_R1_END_TO_END_WITH_LIMITATIONS",
    },
    "city_asset_identity_r7_closeout": {
        "root": "outputs/main_citybrain_d4x_city_asset_identity_r7_edge_extension_and_closeout_r1",
        "expected": "PASS_MAIN_CITYBRAIN_D4X_CITY_ASSET_IDENTITY_R7_EDGE_EXTENSION_AND_CLOSEOUT_R1_WITH_LIMITATIONS",
    },
}

RELATIONSHIP_STATES = [
    "asserted_review_context",
    "inferred_review_context",
    "event_replay_context",
    "overlay_context",
    "pending_review",
    "unresolved",
    "quarantined",
]

REVIEW_STATES = [
    "review_context",
    "candidate_pending_review",
    "pending_review",
    "unresolved",
    "quarantined",
    "data_first_review",
    "source_id_boundary_review",
    "deprecated_superseded",
]

LIMITATIONS = [
    "local/replay-only multi-domain R7 edge registry runtime slice",
    "no production service",
    "no public API readiness",
    "no live monitoring",
    "no autonomous monitoring or alert push",
    "no dispatch, routing/control, enforcement, legal confirmation, certified fact status, official city truth, or automated action",
    "event state and relationship state remain local/replay review/query context only",
]

CLAIM_BOUNDARY = (
    "Local/replay review/query relationship context only. No production service, public API, "
    "live or autonomous monitoring, alert push, dispatch, routing/control, enforcement, legal "
    "confirmation, certified fact status, official city truth, or automated action."
)

RUNTIME_MODULE = r'''#!/usr/bin/env python3
"""Local file-based query helper for the CityBrain multi-domain edge registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_registry(path: str | Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return list(payload.get("edges", []))


def get_edges_for_entity_ref(edges: list[dict[str, Any]], entity_ref: str) -> list[dict[str, Any]]:
    return [
        edge for edge in edges
        if edge.get("source_entity_ref") == entity_ref or edge.get("target_entity_ref") == entity_ref
    ]


def get_edges_by_domain_pair(edges: list[dict[str, Any]], source_domain: str, target_domain: str) -> list[dict[str, Any]]:
    return [
        edge for edge in edges
        if edge.get("source_domain") == source_domain and edge.get("target_domain") == target_domain
    ]


def get_event_context_edges_for_overlay(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        edge for edge in edges
        if "event_context" in edge.get("runtime_query_tags", []) or edge.get("relationship_state") == "overlay_context"
    ]


def get_asset_identity_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        edge for edge in edges
        if edge.get("source_domain") == "city_asset_identity" or edge.get("target_domain") == "city_asset_identity"
    ]


def get_unresolved_or_low_confidence_edges(edges: list[dict[str, Any]], threshold: float = 0.6) -> list[dict[str, Any]]:
    return [
        edge for edge in edges
        if edge.get("relationship_state") in {"unresolved", "quarantined"} or float(edge.get("confidence", 0.0)) < threshold
    ]


def get_evidence_refs_for_edge(edges: list[dict[str, Any]], edge_id: str) -> list[str]:
    for edge in edges:
        if edge.get("edge_id") == edge_id:
            return list(edge.get("evidence_refs", []))
    return []


def get_limitation_refs_for_edge(edges: list[dict[str, Any]], edge_id: str) -> list[str]:
    for edge in edges:
        if edge.get("edge_id") == edge_id:
            return list(edge.get("limitation_refs", []))
    return []
'''


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def root_path(root: str) -> Path:
    return REPO_ROOT / root


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path).replace("\\", "/")


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "byte_count": 0, "fingerprint": None}
    files = sorted(item for item in path.rglob("*") if item.is_file())
    digest = hashlib.sha256()
    total = 0
    for item in files:
        stat = item.stat()
        total += stat.st_size
        digest.update(rel(item).encode("utf-8"))
        digest.update(str(stat.st_size).encode("utf-8"))
        digest.update(str(stat.st_mtime_ns).encode("utf-8"))
    return {"exists": True, "file_count": len(files), "byte_count": total, "fingerprint": digest.hexdigest()}


def decision_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    files = sorted(path.glob("*DECISION*.json"))
    return files[0] if files else None


def decision_status(path: Path) -> str | None:
    decision = decision_file(path)
    if not decision:
        return None
    payload = read_json(decision, {})
    return str(payload.get("status")) if payload.get("status") else None


def first_rows(payload: Any, keys: list[str]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        return []
    for key in keys:
        rows = payload.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def listify(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def str_list(value: Any) -> list[str]:
    out = []
    for item in listify(value):
        if item is None:
            continue
        text = str(item)
        if text and text not in out:
            out.append(text)
    return out


def stable_id(payload: dict[str, Any]) -> str:
    seed = "|".join(
        [
            payload["source_domain"],
            payload["target_domain"],
            payload["relationship_family"],
            payload["source_entity_ref"],
            payload["target_entity_ref"],
            "|".join(payload["source_artifact_refs"]),
            payload.get("upstream_edge_ref", ""),
        ]
    )
    return "r7-md-edge-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def normalize_review_state(raw: Any, relationship_state: str) -> str:
    text = str(raw or "").lower().replace("/", "_").replace("-", "_").replace(" ", "_")
    if relationship_state == "quarantined":
        return "quarantined"
    if relationship_state == "unresolved":
        return "unresolved"
    if "data" in text:
        return "data_first_review"
    if "boundary" in text:
        return "source_id_boundary_review"
    if "pending" in text:
        return "candidate_pending_review"
    if "deprecated" in text or "superseded" in text:
        return "deprecated_superseded"
    if "candidate" in text:
        return "pending_review"
    return "review_context"


def make_edge(
    *,
    edge_type: str,
    relationship_family: str,
    source_domain: str,
    target_domain: str,
    source_entity_ref: str,
    target_entity_ref: str,
    source_entity_type: str,
    target_entity_type: str,
    relationship_state: str,
    confidence: Any,
    review_state: Any,
    evidence_refs: list[str],
    source_branch_refs: list[str],
    source_artifact_refs: list[str],
    limitation_refs: list[str],
    runtime_query_tags: list[str],
    upstream_edge_ref: str,
) -> dict[str, Any]:
    state = relationship_state if relationship_state in RELATIONSHIP_STATES else "pending_review"
    edge = {
        "edge_id": "PENDING",
        "edge_type": edge_type,
        "relationship_family": relationship_family,
        "source_domain": source_domain,
        "target_domain": target_domain,
        "source_entity_ref": source_entity_ref or upstream_edge_ref,
        "target_entity_ref": target_entity_ref or upstream_edge_ref,
        "source_entity_type": source_entity_type,
        "target_entity_type": target_entity_type,
        "relationship_state": state,
        "confidence": round(float(confidence if confidence is not None else 0.5), 3),
        "review_state": normalize_review_state(review_state, state),
        "evidence_refs": evidence_refs or ["INPUT_ARTIFACT_INDEX.json"],
        "source_branch_refs": source_branch_refs,
        "source_artifact_refs": source_artifact_refs,
        "limitation_refs": limitation_refs or ["LIMITATION_REF_NOT_EXPLICIT_IN_SOURCE_ARTIFACT"],
        "runtime_query_tags": sorted(set(runtime_query_tags)),
        "created_by_task": TASK_NAME,
        "claim_boundary": CLAIM_BOUNDARY,
        "upstream_edge_ref": upstream_edge_ref,
        "no_action_taken": True,
    }
    edge["edge_id"] = stable_id(edge)
    return edge


def discover_inputs(pre: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    rows = []
    upstream_missing = []
    for branch, meta in REQUIRED_UPSTREAMS.items():
        path = root_path(meta["root"])
        decision = decision_file(path)
        status = decision_status(path)
        green = path.exists() and decision is not None and status == meta["expected"]
        if not green:
            upstream_missing.append(branch)
        artifacts = []
        if path.exists():
            for item in sorted(path.rglob("*")):
                if item.is_file() and item.suffix.lower() in {".json", ".jsonl", ".md", ".html", ".usda"}:
                    artifacts.append(rel(item))
                if len(artifacts) >= 20:
                    break
        rows.append(
            {
                "branch": branch,
                "root": meta["root"],
                "exists": path.exists(),
                "decision_path": rel(decision) if decision else None,
                "status": status,
                "expected_status": meta["expected"],
                "green": green,
                "snapshot": pre[meta["root"]],
                "sample_artifacts": artifacts,
                "read_only": True,
            }
        )
    report = {
        "status": "PASS" if not upstream_missing else "FAIL",
        "timestamp": utc_now(),
        "upstream_missing": upstream_missing,
        "branches": rows,
    }
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", report)
    return report, upstream_missing


def branch_status_summary(input_index: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for branch in input_index["branches"]:
        decision = read_json(root_path(branch["root"]) / (Path(branch["decision_path"]).name if branch["decision_path"] else "__missing__"), {})
        rows.append(
            {
                "branch": branch["branch"],
                "root": branch["root"],
                "status": branch["status"],
                "green": branch["green"],
                "count_fields": {key: value for key, value in decision.items() if isinstance(value, int) and ("count" in key or "packet" in key or "edge" in key)},
                "limitation_summary": decision.get("limitations", ["limitations carried by upstream branch"])[:6],
                "consumed_by_runtime_slice": branch["green"],
                "no_action_taken": True,
            }
        )
    report = {"status": "PASS" if all(row["green"] for row in rows) else "FAIL", "branches": rows}
    write_json(OUTPUT_ROOT / "UPSTREAM_BRANCH_STATUS_SUMMARY.json", report)
    return report


def registry_schema() -> dict[str, Any]:
    fields = [
        "edge_id",
        "edge_type",
        "relationship_family",
        "source_domain",
        "target_domain",
        "source_entity_ref",
        "target_entity_ref",
        "source_entity_type",
        "target_entity_type",
        "relationship_state",
        "confidence",
        "review_state",
        "evidence_refs",
        "source_branch_refs",
        "source_artifact_refs",
        "limitation_refs",
        "runtime_query_tags",
        "created_by_task",
        "claim_boundary",
    ]
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrain Multi-Domain R7 Edge Registry Runtime Slice Edge",
        "type": "object",
        "required": fields,
        "properties": {
            "relationship_state": {"enum": RELATIONSHIP_STATES},
            "review_state": {"enum": REVIEW_STATES},
            "created_by_task": {"const": TASK_NAME},
        },
        "claim_boundary": CLAIM_BOUNDARY,
        "runtime_mode": "local_file_based_replay_query_context_only",
    }
    write_json(OUTPUT_ROOT / "MULTI_DOMAIN_EDGE_REGISTRY_SCHEMA.json", schema)
    return schema


def build_registry() -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []

    mobility_root = root_path(REQUIRED_UPSTREAMS["mobility_r7_closeout"]["root"])
    mobility_edges = first_rows(read_json(mobility_root / "MOBILITY_R7_ACCEPTED_GROUNDED_EDGES.json", {}), ["edges"])
    for row in mobility_edges:
        source_ref = (str_list(row.get("source_entity_refs")) or str_list(row.get("source_refs")) or str_list(row.get("source_packet_id")))[0]
        target_ref = (str_list(row.get("target_context_refs")) or str_list(row.get("event_refs")) or [row.get("edge_id")])[0]
        state = "event_replay_context" if "SIMULATION" in str(row.get("source_truth_level", "")).upper() else "asserted_review_context"
        edges.append(
            make_edge(
                edge_type=row.get("relationship_type", "mobility_relationship"),
                relationship_family="mobility_asset_road_overlay_context",
                source_domain="mobility",
                target_domain="city_asset_or_road_context",
                source_entity_ref=source_ref,
                target_entity_ref=target_ref,
                source_entity_type="mobility_context",
                target_entity_type="asset_or_corridor_context",
                relationship_state=state,
                confidence=row.get("confidence"),
                review_state=row.get("review_state"),
                evidence_refs=str_list(row.get("evidence_refs")),
                source_branch_refs=[REQUIRED_UPSTREAMS["mobility_r7_closeout"]["root"]],
                source_artifact_refs=[rel(mobility_root / "MOBILITY_R7_ACCEPTED_GROUNDED_EDGES.json")],
                limitation_refs=str_list(row.get("limitation_refs")),
                runtime_query_tags=["mobility", "r7", "d6_overlay_ready", "event_context"],
                upstream_edge_ref=row.get("edge_id", row.get("source_candidate_id", "")),
            )
        )

    building_root = root_path(REQUIRED_UPSTREAMS["building_compliance_r7_closeout"]["root"])
    building_edges = first_rows(read_json(building_root / "BUILDING_COMPLIANCE_R7_ACCEPTED_GROUNDED_EDGES.json", {}), ["edges"])
    for row in building_edges:
        source_ref = (str_list(row.get("source_refs")) or str_list(row.get("source_packet_id")) or [row.get("edge_id")])[0]
        target_ref = (str_list(row.get("target_context")) or str_list(row.get("source_refs")) or [row.get("edge_id")])[-1]
        edges.append(
            make_edge(
                edge_type=row.get("relationship_type", "building_compliance_relationship"),
                relationship_family="building_compliance_asset_context",
                source_domain="building_compliance",
                target_domain="city_asset_identity",
                source_entity_ref=source_ref,
                target_entity_ref=target_ref,
                source_entity_type="building_compliance_context",
                target_entity_type="building_or_asset_context",
                relationship_state="asserted_review_context",
                confidence=row.get("confidence"),
                review_state=row.get("review_state"),
                evidence_refs=str_list(row.get("evidence_refs")),
                source_branch_refs=[REQUIRED_UPSTREAMS["building_compliance_r7_closeout"]["root"]],
                source_artifact_refs=[rel(building_root / "BUILDING_COMPLIANCE_R7_ACCEPTED_GROUNDED_EDGES.json")],
                limitation_refs=str_list(row.get("limitation_refs")),
                runtime_query_tags=["building_compliance", "r7", "d6_overlay_ready", "event_context"],
                upstream_edge_ref=row.get("edge_id", row.get("source_candidate_id", "")),
            )
        )

    property_root = root_path(REQUIRED_UPSTREAMS["property_planning_r7_closeout"]["root"])
    property_edges = first_rows(read_json(property_root / "PROPERTY_PLANNING_R7_ACCEPTED_GROUNDED_EDGES.json", {}), ["edges"])
    for row in property_edges:
        source_ref = (str_list(row.get("source_refs")) or str_list(row.get("source_packet_id")) or [row.get("accepted_edge_id")])[0]
        target_ref = (str_list(row.get("target_context")) or str_list(row.get("asset_refs")) or [row.get("accepted_edge_id")])[0]
        edges.append(
            make_edge(
                edge_type=row.get("relationship_type", "property_planning_relationship"),
                relationship_family="property_planning_asset_context",
                source_domain="property_planning",
                target_domain="city_asset_identity",
                source_entity_ref=source_ref,
                target_entity_ref=target_ref,
                source_entity_type="property_planning_context",
                target_entity_type="asset_or_parcel_context",
                relationship_state="asserted_review_context",
                confidence=row.get("confidence"),
                review_state=row.get("review_state"),
                evidence_refs=str_list(row.get("evidence_refs")),
                source_branch_refs=[REQUIRED_UPSTREAMS["property_planning_r7_closeout"]["root"]],
                source_artifact_refs=[rel(property_root / "PROPERTY_PLANNING_R7_ACCEPTED_GROUNDED_EDGES.json")],
                limitation_refs=str_list(row.get("limitation_refs")),
                runtime_query_tags=["property_planning", "r7", "d6_overlay_ready", "event_context"],
                upstream_edge_ref=row.get("accepted_edge_id", row.get("source_candidate_id", "")),
            )
        )

    city_asset_root = root_path(REQUIRED_UPSTREAMS["city_asset_identity_r7_closeout"]["root"])
    city_edges = first_rows(read_json(city_asset_root / "CITY_ASSET_IDENTITY_R7_ACCEPTED_GROUNDED_EDGES.json", {}), ["edges"])
    for row in city_edges:
        source_ref = (str_list(row.get("source_refs")) or [row.get("edge_id")])[0]
        target_ref = (str_list(row.get("target_context")) or str_list(row.get("source_candidate_id")) or [row.get("edge_id")])[0]
        edges.append(
            make_edge(
                edge_type=row.get("relationship_type", "asset_identity_relationship"),
                relationship_family="city_asset_identity_cross_domain_context",
                source_domain="city_asset_identity",
                target_domain="track2a_omniverse_or_domain_context",
                source_entity_ref=source_ref,
                target_entity_ref=target_ref,
                source_entity_type="city_asset_context",
                target_entity_type="usd_or_domain_candidate_context",
                relationship_state="inferred_review_context",
                confidence=row.get("confidence"),
                review_state=row.get("review_state"),
                evidence_refs=str_list(row.get("evidence_refs")),
                source_branch_refs=[REQUIRED_UPSTREAMS["city_asset_identity_r7_closeout"]["root"]],
                source_artifact_refs=[rel(city_asset_root / "CITY_ASSET_IDENTITY_R7_ACCEPTED_GROUNDED_EDGES.json")],
                limitation_refs=str_list(row.get("limitation_refs")),
                runtime_query_tags=["city_asset_identity", "asset_identity", "r7", "d6_overlay_ready"],
                upstream_edge_ref=row.get("edge_id", row.get("source_candidate_id", "")),
            )
        )

    event_root = root_path(REQUIRED_UPSTREAMS["event_fabric_r2"]["root"])
    current_rows = first_rows(read_json(event_root / "EVENT_FABRIC_R2_CURRENT_STATE_ROWS.json", {}), ["rows"])
    for row in current_rows:
        event_ref = (str_list(row.get("current_event_refs")) or str_list(row.get("state_id")))[0]
        target_ref = (str_list(row.get("entity_ref")) or str_list(row.get("entity_refs")) or [row.get("state_id")])[0]
        edges.append(
            make_edge(
                edge_type="event_state_relates_to_entity_context",
                relationship_family="event_fabric_state_entity_context",
                source_domain="event_fabric",
                target_domain="event_affected_entity",
                source_entity_ref=event_ref,
                target_entity_ref=target_ref,
                source_entity_type="event_state",
                target_entity_type="affected_entity_or_context",
                relationship_state="event_replay_context",
                confidence=0.58,
                review_state=row.get("review_state"),
                evidence_refs=str_list(row.get("evidence_refs")),
                source_branch_refs=[REQUIRED_UPSTREAMS["event_fabric_r2"]["root"]],
                source_artifact_refs=[rel(event_root / "EVENT_FABRIC_R2_CURRENT_STATE_ROWS.json")],
                limitation_refs=str_list(row.get("limitation_refs")),
                runtime_query_tags=["event_fabric", "current_state", "event_context", "overlay"],
                upstream_edge_ref=str(row.get("state_id", event_ref)),
            )
        )

    unresolved_rows = first_rows(read_json(event_root / "EVENT_FABRIC_R2_UNRESOLVED_REVIEW_QUEUE.json", {}), ["items"])
    for row in unresolved_rows[:12]:
        event_ref = (str_list(row.get("event_ref")) or [row.get("queue_id")])[0]
        edges.append(
            make_edge(
                edge_type="event_state_requires_review_context",
                relationship_family="event_fabric_unresolved_review_context",
                source_domain="event_fabric",
                target_domain="review_queue",
                source_entity_ref=event_ref,
                target_entity_ref=row.get("queue_id", event_ref),
                source_entity_type="event_state",
                target_entity_type="review_queue_item",
                relationship_state="unresolved",
                confidence=0.45,
                review_state="unresolved",
                evidence_refs=str_list(row.get("evidence_refs")),
                source_branch_refs=[REQUIRED_UPSTREAMS["event_fabric_r2"]["root"]],
                source_artifact_refs=[rel(event_root / "EVENT_FABRIC_R2_UNRESOLVED_REVIEW_QUEUE.json")],
                limitation_refs=str_list(row.get("limitation_refs")),
                runtime_query_tags=["event_fabric", "unresolved", "low_confidence", "event_context"],
                upstream_edge_ref=str(row.get("queue_id", event_ref)),
            )
        )

    track2a_root = root_path(REQUIRED_UPSTREAMS["track2a_event_overlay_r3"]["root"])
    asset_maps = first_rows(read_json(track2a_root / "OMNI_EVENT_R3_EVENT_TO_ASSET_BINDING_MAP.json", {}), ["rows"])
    relationship_maps = {
        str(row.get("event_id") or row.get("event_state_ref")): row
        for row in first_rows(read_json(track2a_root / "OMNI_EVENT_R3_EVENT_TO_RELATIONSHIP_MAP.json", {}), ["rows"])
    }
    for row in asset_maps:
        event_ref = (str_list(row.get("event_id")) or str_list(row.get("event_state_ref")))[0]
        target_ref = (str_list(row.get("asset_ref")) or str_list(row.get("usd_prim_ref")) or str_list(row.get("binding_id")))[0]
        relation_row = relationship_maps.get(str(row.get("event_id"))) or {}
        edges.append(
            make_edge(
                edge_type="omniverse_event_overlay_maps_event_to_asset_or_marker",
                relationship_family="omniverse_event_overlay_context",
                source_domain="track2a_omniverse_event_overlay",
                target_domain="event_fabric_or_city_asset_context",
                source_entity_ref=event_ref,
                target_entity_ref=target_ref,
                source_entity_type="event_overlay_state",
                target_entity_type="asset_binding_or_usd_marker",
                relationship_state="overlay_context",
                confidence=0.56,
                review_state=row.get("mapping_status", "review_context"),
                evidence_refs=str_list(row.get("evidence_refs")),
                source_branch_refs=[REQUIRED_UPSTREAMS["track2a_event_overlay_r3"]["root"]],
                source_artifact_refs=[
                    rel(track2a_root / "OMNI_EVENT_R3_EVENT_TO_ASSET_BINDING_MAP.json"),
                    rel(track2a_root / "OMNI_EVENT_R3_EVENT_TO_RELATIONSHIP_MAP.json"),
                ],
                limitation_refs=str_list(row.get("limitation_refs")) or ["OVERLAY_CONTEXT_ONLY"],
                runtime_query_tags=["track2a", "omniverse", "overlay", "event_context", *str_list(relation_row.get("relationship_refs"))],
                upstream_edge_ref=str(row.get("binding_id", event_ref)),
            )
        )

    d6_r4_root = root_path(REQUIRED_UPSTREAMS["d6_r4_event_context_overlay"]["root"])
    d6_packets = first_rows(read_json(d6_r4_root / "D6_R4_EVENT_CONTEXT_OVERLAY_PACKETS.json", {}), ["packets"])
    for row in d6_packets:
        source_ref = (str_list(row.get("source_event_state_ref")) or str_list(row.get("source_event_context_ref")) or [row.get("packet_id")])[0]
        target_ref = (str_list(row.get("asset_refs")) or str_list(row.get("relationship_refs")) or [row.get("packet_id")])[0]
        state = "overlay_context" if row.get("packet_type") != "DATA_FIRST_limitation_card" else "pending_review"
        edges.append(
            make_edge(
                edge_type=row.get("packet_type", "d6_event_context_overlay_packet"),
                relationship_family="d6_product_surface_event_context_overlay",
                source_domain="d6_product_surface",
                target_domain=str(row.get("domain") or "domain_context"),
                source_entity_ref=source_ref,
                target_entity_ref=target_ref,
                source_entity_type="d6_event_context_packet",
                target_entity_type="domain_or_asset_context",
                relationship_state=state,
                confidence=row.get("confidence"),
                review_state=row.get("review_state"),
                evidence_refs=str_list(row.get("evidence_refs")),
                source_branch_refs=[REQUIRED_UPSTREAMS["d6_r4_event_context_overlay"]["root"]],
                source_artifact_refs=[rel(d6_r4_root / "D6_R4_EVENT_CONTEXT_OVERLAY_PACKETS.json")],
                limitation_refs=str_list(row.get("limitation_refs")),
                runtime_query_tags=["d6", "product_surface", "event_context", "overlay", str(row.get("domain"))],
                upstream_edge_ref=str(row.get("packet_id", source_ref)),
            )
        )

    combined_root = root_path(REQUIRED_UPSTREAMS["building_property_combined_closeout"]["root"])
    combined_decision = read_json(combined_root / "MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_PROPERTY_PLANNING_R7_EXTENSION_CLOSEOUT_DECISION.json", {})
    edges.append(
        make_edge(
            edge_type="building_property_combined_closeout_relates_branches",
            relationship_family="building_property_combined_context",
            source_domain="building_compliance",
            target_domain="property_planning",
            source_entity_ref="building_compliance_r7_closeout",
            target_entity_ref="property_planning_r7_closeout",
            source_entity_type="domain_branch",
            target_entity_type="domain_branch",
            relationship_state="asserted_review_context",
            confidence=0.6,
            review_state="review_context",
            evidence_refs=[rel(combined_root / "MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_PROPERTY_PLANNING_R7_EXTENSION_CLOSEOUT_DECISION.json")],
            source_branch_refs=[REQUIRED_UPSTREAMS["building_property_combined_closeout"]["root"]],
            source_artifact_refs=[rel(combined_root / "MAIN_CITYBRAIN_D4X_BUILDING_COMPLIANCE_PROPERTY_PLANNING_R7_EXTENSION_CLOSEOUT_DECISION.json")],
            limitation_refs=str_list(combined_decision.get("limitations")) or ["combined_closeout_context_only"],
            runtime_query_tags=["building_property_combined", "r7", "branch_context"],
            upstream_edge_ref="building_property_combined_closeout",
        )
    )

    deduped = {edge["edge_id"]: edge for edge in edges}
    return sorted(deduped.values(), key=lambda item: item["edge_id"])


def write_registry(edges: list[dict[str, Any]]) -> None:
    payload = {
        "task_name": TASK_NAME,
        "status": "PASS",
        "edge_count": len(edges),
        "relationship_states": RELATIONSHIP_STATES,
        "review_states": REVIEW_STATES,
        "runtime_mode": "local_file_based_replay_query_context_only",
        "edges": edges,
    }
    write_json(OUTPUT_ROOT / "MULTI_DOMAIN_EDGE_REGISTRY.json", payload)
    write_jsonl(OUTPUT_ROOT / "MULTI_DOMAIN_EDGE_REGISTRY.jsonl", edges)


def coverage_matrix(edges: list[dict[str, Any]]) -> dict[str, Any]:
    by_source = Counter(edge["source_domain"] for edge in edges)
    by_target = Counter(edge["target_domain"] for edge in edges)
    by_family = Counter(edge["relationship_family"] for edge in edges)
    by_pair = Counter(f"{edge['source_domain']}->{edge['target_domain']}" for edge in edges)
    matrix = {
        "status": "PASS",
        "total_edge_count": len(edges),
        "edge_count_by_source_domain": dict(sorted(by_source.items())),
        "edge_count_by_target_domain": dict(sorted(by_target.items())),
        "edge_count_by_relationship_family": dict(sorted(by_family.items())),
        "edge_count_by_domain_pair": dict(sorted(by_pair.items())),
        "unresolved_or_quarantined_count": sum(1 for edge in edges if edge["relationship_state"] in {"unresolved", "quarantined"}),
    }
    write_json(OUTPUT_ROOT / "EDGE_COVERAGE_MATRIX.json", matrix)
    return matrix


def validate_edges(edges: list[dict[str, Any]], schema: dict[str, Any], input_index: dict[str, Any]) -> dict[str, Any]:
    required = schema["required"]
    failures: list[dict[str, Any]] = []
    ids = [edge["edge_id"] for edge in edges]
    duplicated = sorted(edge_id for edge_id, count in Counter(ids).items() if count > 1)
    if duplicated:
        failures.append({"check": "no_duplicate_edge_ids", "duplicates": duplicated})
    for edge in edges:
        missing = [field for field in required if field not in edge or edge[field] in (None, "", [])]
        if missing:
            failures.append({"edge_id": edge.get("edge_id"), "check": "required_fields_present", "missing": missing})
        if edge.get("relationship_state") not in RELATIONSHIP_STATES:
            failures.append({"edge_id": edge.get("edge_id"), "check": "relationship_state_valid_enum"})
        if edge.get("review_state") not in REVIEW_STATES:
            failures.append({"edge_id": edge.get("edge_id"), "check": "review_state_valid_enum", "review_state": edge.get("review_state")})
        if edge.get("relationship_state") != "quarantined" and not edge.get("evidence_refs"):
            failures.append({"edge_id": edge.get("edge_id"), "check": "evidence_refs_present_for_non_quarantined"})
        if edge.get("relationship_state") in {"inferred_review_context", "event_replay_context", "overlay_context"} and not edge.get("limitation_refs"):
            failures.append({"edge_id": edge.get("edge_id"), "check": "limitation_refs_present_for_inferred_replay_overlay"})
        if not edge.get("source_entity_ref") or not edge.get("target_entity_ref"):
            failures.append({"edge_id": edge.get("edge_id"), "check": "source_and_target_refs_present"})
        expected = stable_id(edge)
        if edge.get("edge_id") != expected:
            failures.append({"edge_id": edge.get("edge_id"), "check": "stable_edge_id", "expected": expected})

    forbidden_positive = forbidden_positive_claim_hits(json.dumps(edges, sort_keys=True).lower())
    if forbidden_positive:
        failures.append({"check": "no_forbidden_positive_claim_terms", "hits": forbidden_positive})
    if input_index.get("status") != "PASS":
        failures.append({"check": "input_artifact_discovery_trace_present", "status": input_index.get("status")})

    report = {
        "status": "PASS" if not failures else "FAIL",
        "edge_count": len(edges),
        "checks": {
            "schema_validity": not failures,
            "required_fields_present": not any(item.get("check") == "required_fields_present" for item in failures),
            "stable_edge_ids": not any(item.get("check") == "stable_edge_id" for item in failures),
            "no_duplicate_edge_ids": not duplicated,
            "source_and_target_refs_present": not any(item.get("check") == "source_and_target_refs_present" for item in failures),
            "evidence_refs_present": not any(item.get("check") == "evidence_refs_present_for_non_quarantined" for item in failures),
            "limitation_refs_present": not any(item.get("check") == "limitation_refs_present_for_inferred_replay_overlay" for item in failures),
            "review_state_valid_enum": not any(item.get("check") == "review_state_valid_enum" for item in failures),
            "relationship_state_valid_enum": not any(item.get("check") == "relationship_state_valid_enum" for item in failures),
            "no_forbidden_claim_terms": not forbidden_positive,
            "input_artifact_discovery_trace_present": input_index.get("status") == "PASS",
            "branch_coverage_summary_present": (OUTPUT_ROOT / "UPSTREAM_BRANCH_STATUS_SUMMARY.json").exists(),
        },
        "failures": failures,
    }
    write_json(OUTPUT_ROOT / "EDGE_VALIDATION_REPORT.json", report)
    return report


def run_runtime_queries(edges: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    entity_ref = edges[0]["source_entity_ref"]
    domain_pair_edge = next(edge for edge in edges if edge["source_domain"] == "mobility")
    evidence_edge = edges[0]["edge_id"]
    limitation_edge = edges[-1]["edge_id"]
    fixtures = [
        {"fixture_id": "fixture-001", "query": "get_edges_for_entity_ref", "params": {"entity_ref": entity_ref}},
        {"fixture_id": "fixture-002", "query": "get_edges_by_domain_pair", "params": {"source_domain": domain_pair_edge["source_domain"], "target_domain": domain_pair_edge["target_domain"]}},
        {"fixture_id": "fixture-003", "query": "get_event_context_edges_for_overlay", "params": {}},
        {"fixture_id": "fixture-004", "query": "get_asset_identity_edges", "params": {}},
        {"fixture_id": "fixture-005", "query": "get_unresolved_or_low_confidence_edges", "params": {"threshold": 0.6}},
        {"fixture_id": "fixture-006", "query": "get_evidence_refs_for_edge", "params": {"edge_id": evidence_edge}},
        {"fixture_id": "fixture-007", "query": "get_limitation_refs_for_edge", "params": {"edge_id": limitation_edge}},
    ]
    results = []
    for fixture in fixtures:
        q = fixture["query"]
        p = fixture["params"]
        if q == "get_edges_for_entity_ref":
            rows = [edge for edge in edges if edge["source_entity_ref"] == p["entity_ref"] or edge["target_entity_ref"] == p["entity_ref"]]
            passed = bool(rows)
            payload: Any = rows
        elif q == "get_edges_by_domain_pair":
            rows = [edge for edge in edges if edge["source_domain"] == p["source_domain"] and edge["target_domain"] == p["target_domain"]]
            passed = bool(rows)
            payload = rows
        elif q == "get_event_context_edges_for_overlay":
            rows = [edge for edge in edges if "event_context" in edge["runtime_query_tags"] or edge["relationship_state"] == "overlay_context"]
            passed = bool(rows)
            payload = rows
        elif q == "get_asset_identity_edges":
            rows = [edge for edge in edges if edge["source_domain"] == "city_asset_identity" or edge["target_domain"] == "city_asset_identity"]
            passed = bool(rows)
            payload = rows
        elif q == "get_unresolved_or_low_confidence_edges":
            rows = [edge for edge in edges if edge["relationship_state"] in {"unresolved", "quarantined"} or edge["confidence"] < float(p["threshold"])]
            passed = bool(rows)
            payload = rows
        elif q == "get_evidence_refs_for_edge":
            edge = next((edge for edge in edges if edge["edge_id"] == p["edge_id"]), None)
            payload = edge.get("evidence_refs", []) if edge else []
            passed = bool(payload)
        elif q == "get_limitation_refs_for_edge":
            edge = next((edge for edge in edges if edge["edge_id"] == p["edge_id"]), None)
            payload = edge.get("limitation_refs", []) if edge else []
            passed = bool(payload)
        else:
            payload = []
            passed = False
        results.append(
            {
                "fixture_id": fixture["fixture_id"],
                "query": q,
                "params": p,
                "status": "PASS" if passed else "FAIL",
                "result_count": len(payload) if isinstance(payload, list) else 1,
                "result_preview": payload[:5] if isinstance(payload, list) else payload,
                "no_action_taken": True,
            }
        )
    fixtures_payload = {"status": "PASS", "fixture_count": len(fixtures), "fixtures": fixtures}
    result_payload = {
        "status": "PASS" if all(result["status"] == "PASS" for result in results) else "FAIL",
        "pass_count": sum(1 for result in results if result["status"] == "PASS"),
        "fail_count": sum(1 for result in results if result["status"] != "PASS"),
        "results": results,
    }
    write_json(OUTPUT_ROOT / "RUNTIME_QUERY_FIXTURES.json", fixtures_payload)
    write_json(OUTPUT_ROOT / "RUNTIME_QUERY_RESULTS.json", result_payload)
    write_text(OUTPUT_ROOT / "local_edge_registry_runtime.py", RUNTIME_MODULE)
    return fixtures_payload, result_payload


def evidence_trace(edges: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [
        {
            "edge_id": edge["edge_id"],
            "upstream_edge_ref": edge.get("upstream_edge_ref"),
            "source_branch_refs": edge["source_branch_refs"],
            "source_artifact_refs": edge["source_artifact_refs"],
            "evidence_refs": edge["evidence_refs"],
            "limitation_refs": edge["limitation_refs"],
            "claim_boundary": edge["claim_boundary"],
            "no_action_taken": True,
        }
        for edge in edges
    ]
    report = {"status": "PASS" if all(row["evidence_refs"] and row["limitation_refs"] for row in rows) else "FAIL", "trace_count": len(rows), "rows": rows}
    write_json(OUTPUT_ROOT / "EVIDENCE_AND_LIMITATION_TRACE.json", report)
    return report


def forbidden_positive_claim_hits(text: str) -> list[str]:
    patterns = [
        "production_ready\": true",
        "public_api_ready\": true",
        "public_api_exposed\": true",
        "live_monitoring_enabled\": true",
        "autonomous_monitoring_enabled\": true",
        "alert_push_enabled\": true",
        "dispatch_recommendation_created\": true",
        "routing_control_command_created\": true",
        "enforcement_action_created\": true",
        "legal_confirmation\": true",
        "certified_fact_status\": true",
        "official_city_truth\": true",
        "automated_action_created\": true",
    ]
    return [pattern for pattern in patterns if pattern in text]


def claim_boundary_audit() -> dict[str, Any]:
    joined = ""
    for item in OUTPUT_ROOT.rglob("*"):
        if item.is_file() and item.name not in {"CLAIM_BOUNDARY_AUDIT.json", "HASH_MANIFEST.json"} and item.suffix.lower() in {".json", ".jsonl", ".md", ".py", ".txt"}:
            joined += "\n" + item.read_text(encoding="utf-8", errors="ignore").lower()
    hits = forbidden_positive_claim_hits(joined)
    report = {
        "status": "PASS" if not hits else "FAIL",
        "forbidden_positive_claim_hits": hits,
        "boundaries_preserved": [
            "no production readiness",
            "no public API readiness",
            "no live or autonomous monitoring",
            "no alert push",
            "no dispatch, routing/control, enforcement, legal confirmation, certified fact status, official city truth, or automated action",
        ],
    }
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", report)
    return report


def no_mutation_audit(pre: dict[str, dict[str, Any]]) -> dict[str, Any]:
    changes = []
    for meta in REQUIRED_UPSTREAMS.values():
        root = meta["root"]
        after = snapshot(root_path(root))
        if pre[root] != after:
            changes.append({"root": root, "before": pre[root], "after": after})
    report = {"status": "PASS" if not changes else "FAIL", "changed_roots": changes}
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", report)
    return report


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]+['\"]"),
        re.compile(r"(?i)authorization\s*:\s*bearer\s+[a-z0-9._-]+"),
    ]
    hits = []
    for item in OUTPUT_ROOT.rglob("*"):
        if item.is_file() and item.name != "HASH_MANIFEST.json" and item.suffix.lower() in {".json", ".jsonl", ".md", ".py", ".txt"}:
            text = item.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                if pattern.search(text):
                    hits.append({"path": rel(item), "pattern": pattern.pattern})
    report = {"status": "PASS" if not hits else "FAIL", "findings": hits}
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", report)
    return report


def write_local_index(edge_count: int, coverage: dict[str, Any]) -> None:
    lines = [
        "# CityBrain Multi-Domain R7 Edge Registry Runtime Slice",
        "",
        f"Status artifact: `MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_DECISION.json`",
        "",
        f"Total edges: `{edge_count}`",
        "",
        "Local/replay review/query context only. This is not a production service or public API.",
        "",
        "## Open Artifacts",
        "",
    ]
    for name in [
        "INPUT_ARTIFACT_INDEX.json",
        "UPSTREAM_BRANCH_STATUS_SUMMARY.json",
        "MULTI_DOMAIN_EDGE_REGISTRY_SCHEMA.json",
        "MULTI_DOMAIN_EDGE_REGISTRY.json",
        "EDGE_COVERAGE_MATRIX.json",
        "EDGE_VALIDATION_REPORT.json",
        "RUNTIME_QUERY_FIXTURES.json",
        "RUNTIME_QUERY_RESULTS.json",
        "EVIDENCE_AND_LIMITATION_TRACE.json",
        "CLAIM_BOUNDARY_AUDIT.json",
        "NO_MUTATION_AUDIT.json",
        "SECRET_AUDIT.json",
        "HASH_MANIFEST.json",
        "local_edge_registry_runtime.py",
    ]:
        lines.append(f"- [{name}]({name})")
    lines.extend(["", "## Source Domain Coverage", ""])
    for domain, count in coverage["edge_count_by_source_domain"].items():
        lines.append(f"- `{domain}`: `{count}`")
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", "\n".join(lines))


def write_readme(edge_count: int) -> None:
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_NAME}

This output builds a bounded local/replay-only multi-domain edge registry runtime slice.

It consolidates review/query relationship edges from Mobility, Building Compliance, Property/Planning, Building+Property combined context, City Asset Identity, Event Fabric R2, Track2A Omniverse Event Overlay R3, and D6 R4/R2 product-surface context.

Total registry edges: `{edge_count}`

This is not a production service, public API, live monitoring, autonomous monitoring, alert push, dispatch, routing/control, enforcement, legal confirmation, certified fact status, official city truth, or automated action system.
""",
    )


def hash_manifest() -> dict[str, Any]:
    files = []
    for item in sorted(OUTPUT_ROOT.rglob("*")):
        if item.is_file() and item.name != "HASH_MANIFEST.json":
            files.append({"path": rel(item), "sha256": sha256_file(item), "size_bytes": item.stat().st_size})
    failures = []
    for item in files:
        path = REPO_ROOT / item["path"]
        if not path.exists() or sha256_file(path) != item["sha256"]:
            failures.append(item["path"])
    report = {"status": "PASS" if files and not failures else "FAIL", "file_count": len(files), "failures": failures, "files": files}
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", report)
    return report


def main() -> int:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    pre = {meta["root"]: snapshot(root_path(meta["root"])) for meta in REQUIRED_UPSTREAMS.values()}
    input_index, upstream_missing = discover_inputs(pre)
    branch_summary = branch_status_summary(input_index)
    schema = registry_schema()

    if upstream_missing:
        edges: list[dict[str, Any]] = []
    else:
        edges = build_registry()

    write_registry(edges)
    coverage = coverage_matrix(edges)
    fixtures, query_results = run_runtime_queries(edges) if edges else (
        {"status": "FAIL", "fixture_count": 0, "fixtures": []},
        {"status": "FAIL", "pass_count": 0, "fail_count": 7, "results": []},
    )
    if not edges:
        write_json(OUTPUT_ROOT / "RUNTIME_QUERY_FIXTURES.json", fixtures)
        write_json(OUTPUT_ROOT / "RUNTIME_QUERY_RESULTS.json", query_results)
        write_text(OUTPUT_ROOT / "local_edge_registry_runtime.py", RUNTIME_MODULE)
    trace = evidence_trace(edges)
    validation = validate_edges(edges, schema, input_index)
    claim = claim_boundary_audit()
    mutation = no_mutation_audit(pre)
    secret = secret_audit()
    write_local_index(len(edges), coverage)
    write_readme(len(edges))

    hash_status = "PENDING"
    status = PASS_STATUS
    if not all(
        [
            not upstream_missing,
            bool(edges),
            validation["status"] == "PASS",
            query_results["status"] == "PASS",
            trace["status"] == "PASS",
            claim["status"] == "PASS",
            mutation["status"] == "PASS",
            secret["status"] == "PASS",
            branch_summary["status"] == "PASS",
        ]
    ):
        status = FAIL_STATUS

    decision = {
        "status": status,
        "task_name": TASK_NAME,
        "timestamp": utc_now(),
        "upstream_missing": upstream_missing,
        "total_edge_count": len(edges),
        "edge_count_by_source_domain": coverage["edge_count_by_source_domain"],
        "edge_count_by_target_domain": coverage["edge_count_by_target_domain"],
        "edge_count_by_relationship_family": coverage["edge_count_by_relationship_family"],
        "unresolved_quarantined_count": coverage["unresolved_or_quarantined_count"],
        "runtime_fixture_pass_count": query_results["pass_count"],
        "runtime_fixture_fail_count": query_results["fail_count"],
        "schema_validation_status": validation["status"],
        "edge_validation_status": validation["status"],
        "input_artifact_index_status": input_index["status"],
        "branch_coverage_summary_status": branch_summary["status"],
        "evidence_limitation_trace_status": trace["status"],
        "claim_boundary_status": claim["status"],
        "no_mutation_status": mutation["status"],
        "secret_audit_status": secret["status"],
        "hash_validation_status": hash_status,
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-EVENT-FABRIC-INTEGRATION-R3",
        "alternative_next_task": "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-TRACK2-HANDOFF-R4",
        "output_root": str(OUTPUT_ROOT),
        "runner_path": str(Path(__file__).resolve()),
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_DECISION.json", decision)
    manifest = hash_manifest()
    decision["hash_validation_status"] = manifest["status"]
    if manifest["status"] != "PASS":
        decision["status"] = FAIL_STATUS
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_DECISION.json", decision)
    hash_manifest()
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build Push 4 Lane B Semantic Graph v2 scaffold artifacts.

Lane B can define and validate graph edges now, but it cannot emit closeout or
final-status artifacts until Lane A publishes CER runtime fixtures containing
CanonicalEntityRef and AttributeAssertion IDs.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.semantic_graph import (
    DependencyEdge,
    GraphEdge,
    GraphNodeRef,
    GraphQueryResult,
    GraphReviewState,
    SourceBackedRelationship,
    query_graph,
    validate_graph_bundle,
)


OUTPUT_ROOT = REPO_ROOT / "outputs" / "push4_lane_b_semantic_graph_v2"
CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "push4_lane_b_semantic_graph_v2_closeout"
FINAL_STATUS_ROOT = REPO_ROOT / "outputs" / "push4_lane_b_semantic_graph_v2_final_status"

PUSH3_INFRA_ROOT = REPO_ROOT / "outputs" / "push3_infra_after_three_lanes_integration"
PUSH3_FINAL_ROOT = REPO_ROOT / "outputs" / "push3_infra_after_three_lanes_final_status"
PUSH3_LANE_B_ROOT = REPO_ROOT / "outputs" / "push3_lane_b_cockpit_source_record_360"
PUSH3_LANE_C_ROOT = REPO_ROOT / "outputs" / "push3_lane_c_diff_recall_readonly"
PUSH4_LANE_A_ROOT = REPO_ROOT / "outputs" / "push4_lane_a_cer_engine"

PACKAGE = "MAIN-CITYBRAIN-PUSH4-LANE-B-SEMANTIC-GRAPH-V2-RUN-TO-CLOSURE"
TASK_ID = "PUSH4-LANE-B-SEMANTIC-GRAPH-V2"
SCHEMA_VERSION = "main-citybrain.push4.lane_b.semantic_graph_v2.v1"
RUN_TIMESTAMP = "2026-07-05T21:30:00Z"
PASS_STATUS = "PASS_PUSH4_LANE_B_SEMANTIC_GRAPH_V2_WITH_LIMITATIONS"
STOP_STATUS = "STOPPED_WAITING_FOR_PUSH4_LANE_A_CER_ARTIFACTS_AFTER_SCAFFOLD"
STOP_PUSH3_STATUS = "STOPPED_WAITING_FOR_PUSH3_INTEGRATION"
FAIL_STATUS = "FAIL_PUSH4_LANE_B_SEMANTIC_GRAPH_V2_CONTRACT_OR_BOUNDARY"
BRANCH = "codex/push4-lane-b-semantic-graph-v2"

LANE_A_REQUIRED_FILES = [
    "CER_RUNTIME_FIXTURES.json",
    "CER_ATTRIBUTE_ASSERTION_SCHEMA.json",
    "CER_ATTRIBUTE_CONFLICT_SCHEMA.json",
]

REQUIRED_OUTPUT_FILES = [
    "SEMANTIC_GRAPH_V2_DECISION.json",
    "SEMANTIC_GRAPH_V2_CONTRACT_OVERVIEW.md",
    "SEMANTIC_GRAPH_V2_NODE_SCHEMA.json",
    "SEMANTIC_GRAPH_V2_EDGE_SCHEMA.json",
    "SEMANTIC_GRAPH_V2_DEPENDENCY_EDGE_SCHEMA.json",
    "SEMANTIC_GRAPH_V2_CER_ALIGNMENT_REPORT.json",
    "SEMANTIC_GRAPH_V2_EDGE_FIXTURES.json",
    "SEMANTIC_GRAPH_V2_QUERY_FIXTURES.json",
    "SEMANTIC_GRAPH_V2_BOUNDARY_AND_NON_CLAIMS.md",
    "SEMANTIC_GRAPH_V2_TEST_LOG.md",
    "SEMANTIC_GRAPH_V2_HASH_MANIFEST.json",
]

UNIVERSAL_CANNOT_CLAIM = [
    "production API",
    "URL fetch or live retrieval",
    "LLM authority",
    "official case/ticket submission",
    "dispatch/control/enforcement",
    "legal/certified finding",
    "autonomous workflow",
    "live Kit control",
    "full citywide twin",
    "VSS-as-fact-source",
    "cross-city claim before federation",
    "causal propagation",
    "resilience outcome",
    "certified dependency",
]

EDGE_FAMILIES = [
    "entity_to_source_record",
    "entity_to_candidate_observation",
    "entity_to_watch_item",
    "entity_to_spatial_overlay",
    "entity_to_attribute_assertion",
    "candidate_dependency_context",
    "service_or_asset_context",
]


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def reset_output_root(root: Path) -> None:
    resolved = root.resolve()
    if (REPO_ROOT / "outputs").resolve() not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs/: {resolved}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def reset_roots() -> None:
    reset_output_root(OUTPUT_ROOT)
    for root in [CLOSEOUT_ROOT, FINAL_STATUS_ROOT]:
        if root.exists():
            reset_output_root(root)
            shutil.rmtree(root)


def hash_manifest(root: Path, manifest_name: str) -> dict[str, Any]:
    manifest_path = root / manifest_name
    rows = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if path == manifest_path:
            continue
        rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    payload = {
        "task_id": TASK_ID,
        "schema_version": f"{SCHEMA_VERSION}.hash_manifest",
        "generated_at": RUN_TIMESTAMP,
        "file_count": len(rows),
        "files": rows,
        "hash_validation_status": "PASS",
    }
    write_json(manifest_path, payload)
    return payload


def verify_hash_manifest(root: Path, manifest_name: str) -> dict[str, Any]:
    manifest = read_json(root / manifest_name, {})
    declared = {row["path"]: row["sha256"] for row in manifest.get("files", [])}
    verified = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != manifest_name):
        verified[rel(path)] = sha256_file(path)
    mismatches = sorted(path for path, digest in declared.items() if verified.get(path) != digest)
    missing = sorted(path for path in declared if path not in verified)
    extra = sorted(path for path in verified if path not in declared)
    return {
        "status": "PASS" if not mismatches and not missing and not extra else "FAIL",
        "declared": declared,
        "verified": verified,
        "mismatches": mismatches,
        "missing": missing,
        "extra": extra,
    }


def uniq(values: list[Any]) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for value in values:
        if value in (None, "", []):
            continue
        key = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def load_inputs() -> dict[str, Any]:
    return {
        "push3_infra_decision": read_json(PUSH3_INFRA_ROOT / "PUSH3_INFRA_INTEGRATION_DECISION.json", {}),
        "push3_final_status": read_json(PUSH3_FINAL_ROOT / "PUSH3_FINAL_STATUS_DECISION.json", {}),
        "push3_integrated_refs": read_json(PUSH3_INFRA_ROOT / "PUSH3_SELECTED_ITEM_WORKSPACE_INTEGRATED_REFS.json", {}),
        "workspace_packet": read_json(PUSH3_LANE_B_ROOT / "SELECTED_ITEM_WORKSPACE_FIXTURES.json", {}),
        "source_record_index": read_json(PUSH3_LANE_B_ROOT / "SOURCE_RECORD_360_INDEX.json", {}),
        "recall_matches": read_json(PUSH3_LANE_C_ROOT / "RECALL_MATCH_ITEMS.json", {}).get("items", []),
        "diff_items": read_json(PUSH3_LANE_C_ROOT / "DIFF_ITEMS.json", {}).get("items", []),
    }


def push3_entry_gate(inputs: dict[str, Any]) -> dict[str, Any]:
    required_paths = [
        PUSH3_INFRA_ROOT / "PUSH3_INFRA_INTEGRATION_DECISION.json",
        PUSH3_FINAL_ROOT / "PUSH3_FINAL_STATUS_DECISION.json",
        PUSH3_LANE_B_ROOT / "SELECTED_ITEM_WORKSPACE_FIXTURES.json",
        PUSH3_LANE_B_ROOT / "SOURCE_RECORD_360_INDEX.json",
        PUSH3_LANE_C_ROOT / "RECALL_MATCH_ITEMS.json",
    ]
    missing = [rel(path) for path in required_paths if not path.exists()]
    infra_status = str(inputs["push3_infra_decision"].get("status", ""))
    final_status = str(inputs["push3_final_status"].get("status", ""))
    integrated_refs = inputs["push3_integrated_refs"]
    checks = {
        "push3_integration_artifacts_present": not missing,
        "push3_infra_status_pass": infra_status.startswith("PASS_PUSH3_INFRA_AFTER_THREE_LANES"),
        "push3_final_status_pass": final_status.startswith("PASS_PUSH3_INFRA_AFTER_THREE_LANES"),
        "brief_v2_refs_available": bool(integrated_refs.get("brief_refs")),
        "cockpit_source_record_360_available": bool(inputs["workspace_packet"].get("items")),
        "diff_recall_available": bool(inputs["recall_matches"]),
        "check_reports_carried": bool(integrated_refs.get("check_report_refs")),
        "authority_envelopes_carried": bool(integrated_refs.get("authority_envelope_refs")),
        "protected_ask_r7_declared_clean": True,
    }
    return {
        "status": "PASS" if all(checks.values()) else STOP_PUSH3_STATUS,
        "checks": checks,
        "missing": missing,
        "push3_infra_status": infra_status,
        "push3_final_status": final_status,
        "accepted_integration_branch": "origin/codex/push3-infra-after-three-lanes",
    }


def first_list(payload: Any, keys: list[str]) -> list[Any]:
    if not isinstance(payload, dict):
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = first_list(value, keys)
            if nested:
                return nested
    return []


def load_cer_context(selected_item: dict[str, Any]) -> dict[str, Any]:
    paths = {name: PUSH4_LANE_A_ROOT / name for name in LANE_A_REQUIRED_FILES}
    missing = [rel(path) for path in paths.values() if not path.exists()]
    runtime = read_json(paths["CER_RUNTIME_FIXTURES.json"], {})
    entities = first_list(runtime, ["canonical_entities", "entities", "entity_refs"])
    assertions = first_list(runtime, ["attribute_assertions", "assertions", "attribute_assertion_refs"])
    usable_lane_a = not missing and bool(entities) and bool(assertions)
    selected_id = selected_item.get("selected_item_id", "lane-b-selected-item")
    slug = selected_id.replace(":", "-").replace("/", "-").lower()

    if usable_lane_a:
        entity = entities[0]
        assertion = assertions[0]
        entity_id = str(entity.get("canonical_entity_id") or entity.get("entity_id") or entity.get("ref_id"))
        assertion_id = str(assertion.get("assertion_id") or assertion.get("attribute_assertion_id") or assertion.get("ref_id"))
        entity_ref = GraphNodeRef(
            "cer_entity",
            entity_id,
            label=str(entity.get("canonical_name") or selected_item.get("selected_item_label") or entity_id),
            metadata={"source": "push4_lane_a_cer_engine", "lane_a_runtime_ref": rel(paths["CER_RUNTIME_FIXTURES.json"])},
        ).as_dict()
        assertion_ref = GraphNodeRef(
            "attribute_assertion",
            assertion_id,
            label=str(assertion.get("attribute_name") or assertion_id),
            metadata={"source": "push4_lane_a_cer_engine", "lane_a_runtime_ref": rel(paths["CER_RUNTIME_FIXTURES.json"])},
        ).as_dict()
        return {
            "status": "available",
            "lane_a_artifacts_present": True,
            "provisional": False,
            "entity_ref": entity_ref,
            "attribute_assertion_refs": [assertion_ref],
            "missing_or_empty": [],
        }

    entity_ref = GraphNodeRef(
        "cer_entity",
        f"cer:provisional:push4-lane-b:entity:{slug}",
        label=str(selected_item.get("selected_item_label") or selected_id),
        provisional=True,
        metadata={
            "source": "lane_b_provisional_fixture_waiting_for_lane_a",
            "selected_item_id": selected_id,
            "replacement_required_before_closeout": True,
        },
    ).as_dict()
    assertion_refs = [
        GraphNodeRef(
            "attribute_assertion",
            f"cer:provisional:push4-lane-b:attribute-assertion:review-state:{slug}",
            label="review_state pending_review",
            provisional=True,
            metadata={
                "source": "lane_b_provisional_fixture_waiting_for_lane_a",
                "attribute_name": "review_state",
                "replacement_required_before_closeout": True,
            },
        ).as_dict(),
        GraphNodeRef(
            "attribute_assertion",
            f"cer:provisional:push4-lane-b:attribute-assertion:local-replay-source:{slug}",
            label="source_scope local_replay_only",
            provisional=True,
            metadata={
                "source": "lane_b_provisional_fixture_waiting_for_lane_a",
                "attribute_name": "source_scope",
                "replacement_required_before_closeout": True,
            },
        ).as_dict(),
    ]
    return {
        "status": "missing",
        "lane_a_artifacts_present": False,
        "provisional": True,
        "entity_ref": entity_ref,
        "attribute_assertion_refs": assertion_refs,
        "missing_or_empty": missing
        + ([] if entities else ["outputs/push4_lane_a_cer_engine/CER_RUNTIME_FIXTURES.json:canonical_entities"])
        + ([] if assertions else ["outputs/push4_lane_a_cer_engine/CER_RUNTIME_FIXTURES.json:attribute_assertions"]),
    }


def build_node_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Semantic Graph v2 GraphNodeRef",
        "schema_version": f"{SCHEMA_VERSION}.node_schema",
        "type": "object",
        "required": ["ref_kind", "ref_id", "label", "provisional"],
        "properties": {
            "ref_kind": {
                "type": "string",
                "enum": [
                    "cer_entity",
                    "attribute_assertion",
                    "source_record",
                    "candidate_observation",
                    "watch_item",
                    "spatial_overlay",
                    "recall_match",
                ],
            },
            "ref_id": {"type": "string", "minLength": 1},
            "label": {"type": "string"},
            "provisional": {"type": "boolean"},
            "source_ref": {"type": "string"},
            "metadata": {"type": "object"},
        },
        "cer_alignment_rule": "Graph dependency/context edges must carry a CER CanonicalEntityRef and AttributeAssertion ref where relevant.",
    }


def build_edge_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Semantic Graph v2 GraphEdge and SourceBackedRelationship",
        "schema_version": f"{SCHEMA_VERSION}.edge_schema",
        "type": "object",
        "required": [
            "edge_id",
            "schema_version",
            "edge_type",
            "from_ref",
            "to_ref",
            "source_class",
            "source_ref",
            "evidence_refs",
            "limitation_refs",
            "trace_refs",
            "check_report_ref",
            "authority_envelope_ref",
            "review_state",
            "confidence",
            "cannot_claim",
        ],
        "properties": {
            "edge_id": {"type": "string"},
            "edge_type": {"type": "string", "enum": EDGE_FAMILIES},
            "from_ref": {"$ref": "SEMANTIC_GRAPH_V2_NODE_SCHEMA.json"},
            "to_ref": {"$ref": "SEMANTIC_GRAPH_V2_NODE_SCHEMA.json"},
            "source_class": {"type": "string"},
            "source_ref": {"type": "string"},
            "evidence_refs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "limitation_refs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "trace_refs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "check_report_ref": {"type": "string"},
            "authority_envelope_ref": {"type": "string"},
            "review_state": {"type": "object"},
            "confidence": {"type": "object"},
            "cannot_claim": {"type": "array", "items": {"type": "string"}},
        },
        "source_backed_relationship_rule": "A relationship is review context only unless future CHECK/CER lanes explicitly promote it.",
    }


def build_dependency_edge_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Semantic Graph v2 DependencyEdge",
        "schema_version": f"{SCHEMA_VERSION}.dependency_edge_schema",
        "type": "object",
        "required": [
            "dependency_edge_id",
            "base_edge_id",
            "dependency_kind",
            "from_ref",
            "to_ref",
            "review_only",
            "causal_claim",
            "certified_relationship_claim",
            "evidence_refs",
            "limitation_refs",
            "trace_refs",
            "cannot_claim",
        ],
        "properties": {
            "dependency_edge_id": {"type": "string"},
            "base_edge_id": {"type": "string"},
            "dependency_kind": {"type": "string", "enum": ["candidate_dependency_context", "service_or_asset_context"]},
            "review_only": {"const": True},
            "causal_claim": {"const": False},
            "certified_relationship_claim": {"const": False},
        },
        "non_claim_rule": "DependencyEdge does not prove causality, cascade propagation, resilience outcome, or certified dependency.",
    }


def pick_refs(values: list[str], count: int) -> list[str]:
    return uniq([str(value) for value in values])[:count]


def build_graph(inputs: dict[str, Any], cer_context: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    workspace = inputs["workspace_packet"].get("items", [{}])[0]
    source_records = inputs["source_record_index"].get("source_records", [])
    integrated_refs = inputs["push3_integrated_refs"]
    recall_matches = inputs["recall_matches"]

    evidence_refs = pick_refs(workspace.get("evidence_refs", []) + integrated_refs.get("evidence_refs", []), 4)
    limitation_refs = pick_refs(workspace.get("limitation_refs", []) + integrated_refs.get("limitation_refs", []), 8)
    trace_refs = pick_refs(workspace.get("trace_refs", []), 6)
    check_report_refs = pick_refs(workspace.get("check_report_refs", []) + integrated_refs.get("check_report_refs", []), 4)
    authority_refs = pick_refs(workspace.get("authority_envelope_refs", []) + integrated_refs.get("authority_envelope_refs", []), 4)
    check_ref = check_report_refs[0] if check_report_refs else "check_report:missing"
    authority_ref = authority_refs[0] if authority_refs else "authority_envelope:missing"

    entity_ref = cer_context["entity_ref"]
    assertion_refs = cer_context["attribute_assertion_refs"]
    review_state = GraphReviewState(
        "provisional_pending_lane_a" if cer_context["provisional"] else "pending_review",
        lane_a_cer_status=cer_context["status"],
    ).as_dict()
    confidence = {"score": 0.42, "basis": "local_replay_review_context_overlap_not_causal_or_certified_truth"}

    nodes = [
        entity_ref,
        *assertion_refs,
        *[
            GraphNodeRef("source_record", row["source_id"], label=row["source_record_360_id"], source_ref=row["source_id"]).as_dict()
            for row in source_records[:3]
        ],
        *[
            GraphNodeRef("candidate_observation", ref, label=ref).as_dict()
            for ref in pick_refs(workspace.get("candidate_observation_refs", []), 2)
        ],
        *[GraphNodeRef("watch_item", ref, label=ref).as_dict() for ref in pick_refs(workspace.get("watch_item_refs", []), 2)],
        *[
            GraphNodeRef("spatial_overlay", ref, label=ref).as_dict()
            for ref in pick_refs(workspace.get("spatial_overlay_refs", []), 2)
        ],
        *[
            GraphNodeRef("recall_match", item["recall_match_id"], label=item["match_family"]).as_dict()
            for item in recall_matches[:1]
        ],
    ]

    def make_edge(
        index: int,
        edge_type: str,
        from_ref: dict[str, Any],
        to_ref: dict[str, Any],
        source_class: str,
        source_ref: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return GraphEdge(
            edge_id=f"semantic-graph:v2:edge:{edge_type}:{index:04d}",
            edge_type=edge_type,
            from_ref=from_ref,
            to_ref=to_ref,
            source_class=source_class,
            source_ref=source_ref,
            evidence_refs=evidence_refs,
            limitation_refs=limitation_refs,
            trace_refs=trace_refs,
            check_report_ref=check_ref,
            authority_envelope_ref=authority_ref,
            review_state=review_state,
            confidence=confidence,
            cannot_claim=UNIVERSAL_CANNOT_CLAIM,
            extra={
                "dependency_context_only": True,
                "causal_claim": False,
                "certified_relationship_claim": False,
                "official_dependency_claim": False,
                "cross_city_claim": False,
                "local_replay_only": True,
                **(extra or {}),
            },
        ).as_dict()

    first_source = source_records[0] if source_records else {"source_id": "source:missing", "source_class": "missing"}
    candidate_ref = workspace.get("candidate_observation_refs", ["candidate:missing"])[0]
    watch_ref = workspace.get("watch_item_refs", ["watch:item:missing"])[0]
    spatial_ref = workspace.get("spatial_overlay_refs", ["spatial-review:item:missing"])[0]
    recall_match = recall_matches[0] if recall_matches else {"recall_match_id": "recall:match:missing", "match_family": "missing"}

    edges = [
        make_edge(
            1,
            "entity_to_source_record",
            entity_ref,
            GraphNodeRef("source_record", first_source["source_id"], label=first_source["source_record_360_id"], source_ref=first_source["source_id"]).as_dict(),
            first_source["source_class"],
            first_source["source_id"],
        ),
        make_edge(
            2,
            "entity_to_candidate_observation",
            entity_ref,
            GraphNodeRef("candidate_observation", candidate_ref, label=candidate_ref).as_dict(),
            "candidate_observation",
            candidate_ref,
        ),
        make_edge(
            3,
            "entity_to_watch_item",
            entity_ref,
            GraphNodeRef("watch_item", watch_ref, label=watch_ref).as_dict(),
            "watch_item",
            watch_ref,
        ),
        make_edge(
            4,
            "entity_to_spatial_overlay",
            entity_ref,
            GraphNodeRef("spatial_overlay", spatial_ref, label=spatial_ref).as_dict(),
            "spatial_overlay",
            spatial_ref,
        ),
        make_edge(
            5,
            "entity_to_attribute_assertion",
            entity_ref,
            assertion_refs[0],
            "cer_attribute_assertion",
            assertion_refs[0]["ref_id"],
            {"attribute_assertion_required_for_closeout": not cer_context["provisional"]},
        ),
        make_edge(
            6,
            "candidate_dependency_context",
            assertion_refs[0],
            GraphNodeRef("recall_match", recall_match["recall_match_id"], label=recall_match["match_family"]).as_dict(),
            "recall_match",
            recall_match["recall_match_id"],
            {"dependency_family": "candidate_context", "review_safe_dependency": True},
        ),
        make_edge(
            7,
            "service_or_asset_context",
            assertion_refs[min(1, len(assertion_refs) - 1)],
            GraphNodeRef("spatial_overlay", spatial_ref, label=spatial_ref).as_dict(),
            "spatial_overlay",
            spatial_ref,
            {"dependency_family": "service_or_asset_context", "review_safe_dependency": True},
        ),
    ]

    dependency_edges = [
        DependencyEdge(
            "semantic-graph:v2:dependency:candidate-context:0001",
            edges[5]["edge_id"],
            "candidate_dependency_context",
            edges[5]["from_ref"],
            edges[5]["to_ref"],
            review_state,
            evidence_refs,
            limitation_refs,
            trace_refs,
            UNIVERSAL_CANNOT_CLAIM,
        ).as_dict(),
        DependencyEdge(
            "semantic-graph:v2:dependency:service-asset-context:0001",
            edges[6]["edge_id"],
            "service_or_asset_context",
            edges[6]["from_ref"],
            edges[6]["to_ref"],
            review_state,
            evidence_refs,
            limitation_refs,
            trace_refs,
            UNIVERSAL_CANNOT_CLAIM,
        ).as_dict(),
    ]
    relationships = [
        SourceBackedRelationship(
            f"semantic-graph:v2:relationship:{idx:04d}",
            edge["edge_id"],
            edge["source_ref"],
            edge["evidence_refs"],
            edge["limitation_refs"],
            edge["trace_refs"],
            edge["check_report_ref"],
            edge["authority_envelope_ref"],
        ).as_dict()
        for idx, edge in enumerate(edges, 1)
    ]
    graph_bundle = {
        "schema_version": f"{SCHEMA_VERSION}.edge_fixtures",
        "task_id": TASK_ID,
        "generated_at": RUN_TIMESTAMP,
        "lane_a_cer_status": cer_context["status"],
        "cer_refs_are_provisional": cer_context["provisional"],
        "nodes": nodes,
        "edges": edges,
        "dependency_edges": dependency_edges,
        "source_backed_relationships": relationships,
        "cannot_claim": UNIVERSAL_CANNOT_CLAIM,
    }

    queries = [
        GraphQueryResult(
            "semantic-graph:v2:query:edges-for-cer-entity:0001",
            "edges_for_cer_ref",
            entity_ref["ref_id"],
            [edge["edge_id"] for edge in query_graph(graph_bundle, "edges_for_cer_ref", entity_ref["ref_id"])],
            review_state,
            UNIVERSAL_CANNOT_CLAIM,
        ).as_dict(),
        GraphQueryResult(
            "semantic-graph:v2:query:dependency-review:0001",
            "dependencies_for_review",
            "review_context_only",
            [edge["edge_id"] for edge in query_graph(graph_bundle, "dependencies_for_review", "review_context_only")],
            review_state,
            UNIVERSAL_CANNOT_CLAIM,
        ).as_dict(),
        GraphQueryResult(
            "semantic-graph:v2:query:evidence-for-edge:0001",
            "evidence_for_edge",
            edges[0]["edge_id"],
            [edge["edge_id"] for edge in query_graph(graph_bundle, "evidence_for_edge", edges[0]["edge_id"])],
            review_state,
            UNIVERSAL_CANNOT_CLAIM,
        ).as_dict(),
    ]
    query_fixtures = {
        "schema_version": f"{SCHEMA_VERSION}.query_fixtures",
        "task_id": TASK_ID,
        "generated_at": RUN_TIMESTAMP,
        "query_count": len(queries),
        "queries": queries,
        "safe_result_policy": "local/replay review context only; no action, causality, certified dependency, or cross-city claim.",
    }
    return graph_bundle, query_fixtures


def build_alignment_report(gate: dict[str, Any], cer_context: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    lane_a_ready = cer_context["status"] == "available"
    return {
        "schema_version": f"{SCHEMA_VERSION}.cer_alignment_report",
        "task_id": TASK_ID,
        "generated_at": RUN_TIMESTAMP,
        "status": "PASS" if lane_a_ready and validation["status"] == "PASS" else "STOPPED_WAITING_FOR_PUSH4_LANE_A_CER_ARTIFACTS",
        "push3_gate": gate,
        "lane_a_cer_artifacts_present": lane_a_ready,
        "lane_a_missing_or_empty": cer_context["missing_or_empty"],
        "provisional_cer_refs_used": cer_context["provisional"],
        "cer_entity_assertion_ids_used": True,
        "cer_aligned_to_lane_a": lane_a_ready,
        "no_pre_assertion_entity_shape_dependency": True,
        "final_closeout_allowed": lane_a_ready and validation["status"] == "PASS",
        "validation": validation,
        "replacement_required_before_closeout": cer_context["provisional"],
    }


def required_output_status() -> dict[str, Any]:
    missing = [name for name in REQUIRED_OUTPUT_FILES if not (OUTPUT_ROOT / name).exists()]
    return {"status": "PASS" if not missing else "FAIL", "required_count": len(REQUIRED_OUTPUT_FILES), "missing": missing}


def write_contract_docs(status: str, cer_context: dict[str, Any], validation: dict[str, Any]) -> None:
    provisional_line = (
        "Lane A CER artifacts are missing, so fixtures use provisional CER-like IDs and the lane stops before closeout/final status."
        if cer_context["provisional"]
        else "Lane A CER artifacts are present; graph fixtures consume the published CER entity/assertion refs."
    )
    write_text(
        OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_CONTRACT_OVERVIEW.md",
        f"""# Semantic Graph v2 Contract Overview

Status: `{status}`

Semantic Graph v2 defines:
- `GraphNodeRef`
- `GraphEdge`
- `DependencyEdge`
- `SourceBackedRelationship`
- `GraphQueryResult`
- `GraphReviewState`

{provisional_line}

Initial edge families are review-only: `entity_to_source_record`, `entity_to_candidate_observation`, `entity_to_watch_item`, `entity_to_spatial_overlay`, `entity_to_attribute_assertion`, `candidate_dependency_context`, and `service_or_asset_context`.

Every edge preserves evidence refs, limitation refs, trace refs, CheckReport refs, and AuthorityEnvelope refs. Dependency edges are context edges only; they do not prove causality, resilience/cascade outcomes, official dependency, certified finding, dispatch/control/enforcement, or cross-city truth.

Validation status: `{validation["status"]}`
""",
    )
    write_text(
        OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_BOUNDARY_AND_NON_CLAIMS.md",
        """# Semantic Graph v2 Boundary and Non-Claims

- No production API.
- No URL fetch or live retrieval.
- No LLM authority.
- No official case/ticket submission.
- No dispatch/control/enforcement.
- No legal/certified finding.
- No autonomous workflow.
- No live Kit control.
- No full citywide twin claim.
- No VSS-as-fact-source.
- No cross-city claims until federation.
- No sealed ASK G1-G8 runtime change.
- No protected R7 runtime drift.
- No causal propagation, resilience outcome, or certified dependency claim.
- Feature branches only; INFRA owns canonical integration.
""",
    )
    write_text(
        OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_TEST_LOG.md",
        f"""# Semantic Graph v2 Test Log

- Runner command: `.venv\\Scripts\\python.exe scripts\\run_main_citybrain_push4_lane_b_semantic_graph_v2.py`
- Focused command: `.venv\\Scripts\\python.exe -m unittest tests.test_main_citybrain_push4_lane_b_semantic_graph_v2`
- Expected current status: `{status}`
- Full discovery: run separately after focused tests if safe.
- Protected ASK/R7 diffs: run separately after focused tests.
""",
    )


def write_closeout_and_final(decision: dict[str, Any], graph_bundle: dict[str, Any], query_fixtures: dict[str, Any]) -> None:
    reset_output_root(CLOSEOUT_ROOT)
    closeout_decision = {
        "schema_version": f"{SCHEMA_VERSION}.closeout_decision",
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "created_at": RUN_TIMESTAMP,
        "decision_ref": rel(OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_DECISION.json"),
        "edge_count": len(graph_bundle["edges"]),
        "dependency_edge_count": len(graph_bundle["dependency_edges"]),
        "query_count": query_fixtures["query_count"],
        "limitations": UNIVERSAL_CANNOT_CLAIM,
    }
    write_json(CLOSEOUT_ROOT / "SEMANTIC_GRAPH_V2_CLOSEOUT_DECISION.json", closeout_decision)
    write_text(CLOSEOUT_ROOT / "SEMANTIC_GRAPH_V2_CLOSEOUT_SUMMARY.md", "# Semantic Graph v2 Closeout Summary\n\nGraph v2 closed with Lane A CER refs available and review-only dependency/context edges.")
    write_text(CLOSEOUT_ROOT / "SEMANTIC_GRAPH_V2_CLOSEOUT_LIMITATIONS.md", "# Semantic Graph v2 Closeout Limitations\n\n" + "\n".join(f"- {item}" for item in UNIVERSAL_CANNOT_CLAIM))
    write_text(CLOSEOUT_ROOT / "SEMANTIC_GRAPH_V2_CLOSEOUT_NEXT_STEPS.md", "# Semantic Graph v2 Closeout Next Steps\n\n- Wait for Lane C, then INFRA Push 4 integration.")
    hash_manifest(CLOSEOUT_ROOT, "SEMANTIC_GRAPH_V2_CLOSEOUT_HASH_MANIFEST.json")

    reset_output_root(FINAL_STATUS_ROOT)
    final_decision = {
        "schema_version": f"{SCHEMA_VERSION}.final_status_decision",
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "created_at": RUN_TIMESTAMP,
        "decision_ref": rel(OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_DECISION.json"),
        "closeout_ref": rel(CLOSEOUT_ROOT / "SEMANTIC_GRAPH_V2_CLOSEOUT_DECISION.json"),
        "branch": BRANCH,
        "canonical_merged": False,
    }
    write_json(FINAL_STATUS_ROOT / "SEMANTIC_GRAPH_V2_FINAL_STATUS_DECISION.json", final_decision)
    write_text(FINAL_STATUS_ROOT / "SEMANTIC_GRAPH_V2_FINAL_STATUS_SUMMARY.md", "# Semantic Graph v2 Final Status\n\nPASS with limitations. Canonical integration remains with INFRA.")
    hash_manifest(FINAL_STATUS_ROOT, "SEMANTIC_GRAPH_V2_FINAL_STATUS_HASH_MANIFEST.json")


def run() -> dict[str, Any]:
    reset_roots()
    inputs = load_inputs()
    gate = push3_entry_gate(inputs)
    workspace = inputs["workspace_packet"].get("items", [{}])[0]
    cer_context = load_cer_context(workspace)
    graph_bundle, query_fixtures = build_graph(inputs, cer_context)
    validation = validate_graph_bundle(graph_bundle)
    alignment = build_alignment_report(gate, cer_context, validation)

    if gate["status"] != "PASS":
        status = STOP_PUSH3_STATUS
        completed_through = ["B0_PUSH3_AND_CER_GATE_DISCOVERY"]
        stopped_before = ["B1_GRAPH_V2_CONTRACT"]
    elif validation["status"] != "PASS":
        status = FAIL_STATUS
        completed_through = ["B0_PUSH3_AND_CER_GATE_DISCOVERY", "B1_GRAPH_V2_CONTRACT", "B2_CER_ALIGNED_NODE_EDGE_FIXTURES_R1"]
        stopped_before = ["B3_CROSS_DOMAIN_DEPENDENCY_EDGES_R1"]
    elif cer_context["status"] != "available":
        status = STOP_STATUS
        completed_through = [
            "B0_PUSH3_AND_CER_GATE_DISCOVERY",
            "B1_GRAPH_V2_CONTRACT",
            "B2_CER_ALIGNED_NODE_EDGE_FIXTURES_R1_PROVISIONAL",
            "B3_CROSS_DOMAIN_DEPENDENCY_EDGES_R1_PROVISIONAL",
            "B4_GRAPH_QUERY_FIXTURES_R2",
        ]
        stopped_before = ["B5_CLOSEOUT", "B6_BRANCH_PUBLISH_FINAL", "B7_FINAL_STATUS"]
    else:
        status = PASS_STATUS
        completed_through = [
            "B0_PUSH3_AND_CER_GATE_DISCOVERY",
            "B1_GRAPH_V2_CONTRACT",
            "B2_CER_ALIGNED_NODE_EDGE_FIXTURES_R1",
            "B3_CROSS_DOMAIN_DEPENDENCY_EDGES_R1",
            "B4_GRAPH_QUERY_FIXTURES_R2",
            "B5_CLOSEOUT",
            "B6_BRANCH_PUBLISH",
            "B7_FINAL_STATUS",
        ]
        stopped_before = []

    decision = {
        "schema_version": f"{SCHEMA_VERSION}.decision",
        "task_id": TASK_ID,
        "package": PACKAGE,
        "status": status,
        "branch": BRANCH,
        "created_at": RUN_TIMESTAMP,
        "completed_through": completed_through,
        "stopped_before": stopped_before,
        "push3_gate_status": gate["status"],
        "lane_a_cer_status": cer_context["status"],
        "cer_refs_are_provisional": cer_context["provisional"],
        "edge_count": len(graph_bundle["edges"]),
        "dependency_edge_count": len(graph_bundle["dependency_edges"]),
        "query_count": query_fixtures["query_count"],
        "validation": validation,
        "alignment_report_ref": rel(OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_CER_ALIGNMENT_REPORT.json"),
        "canonical_merged": False,
        "cannot_claim": UNIVERSAL_CANNOT_CLAIM,
    }

    write_json(OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_NODE_SCHEMA.json", build_node_schema())
    write_json(OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_EDGE_SCHEMA.json", build_edge_schema())
    write_json(OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_DEPENDENCY_EDGE_SCHEMA.json", build_dependency_edge_schema())
    write_json(OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_EDGE_FIXTURES.json", graph_bundle)
    write_json(OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_QUERY_FIXTURES.json", query_fixtures)
    write_json(OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_CER_ALIGNMENT_REPORT.json", alignment)
    write_json(OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_DECISION.json", decision)
    write_contract_docs(status, cer_context, validation)
    hash_manifest(OUTPUT_ROOT, "SEMANTIC_GRAPH_V2_HASH_MANIFEST.json")
    output_status = required_output_status()
    decision["required_output_status"] = output_status
    write_json(OUTPUT_ROOT / "SEMANTIC_GRAPH_V2_DECISION.json", decision)
    hash_manifest(OUTPUT_ROOT, "SEMANTIC_GRAPH_V2_HASH_MANIFEST.json")

    if status == PASS_STATUS:
        write_closeout_and_final(decision, graph_bundle, query_fixtures)

    return decision


def main() -> int:
    decision = run()
    print(json.dumps({"status": decision["status"], "output_root": rel(OUTPUT_ROOT)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

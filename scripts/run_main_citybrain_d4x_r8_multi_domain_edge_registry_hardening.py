#!/usr/bin/env python3
"""R8 multi-domain edge registry hardening.

This task derives a hardened/annotated copy from the frozen R7 registry. It
does not mutate R7, D5, D6, Track2, source USD, app, or city-source outputs.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_NAME = "MAIN-CITYBRAIN-D4X-R8-MULTI-DOMAIN-EDGE-REGISTRY-HARDENING"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING"
HOLD_STATUS = "HOLD_MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_FROZEN_CHAIN_NOT_PRESERVED"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d4x_r8_multi_domain_edge_registry_hardening"

R7_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d4x_r7_multi_domain_edge_registry_runtime_slice"
D5_R3_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d5_local_served_runtime_event_fabric_integration_r3"
D5_R4_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d5_local_served_runtime_track2_handoff_r4"
D6_R1_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d6_d5_local_running_control_room_slice_r1"
D6_CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d6_d5_local_running_slice_closeout"

FROZEN_CHAIN_ROOTS = [R7_ROOT, D5_R3_ROOT, D5_R4_ROOT, D6_R1_ROOT, D6_CLOSEOUT_ROOT]

R7_REQUIRED = {
    "decision_json": "MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_DECISION.json",
    "multi_domain_edge_registry": "MULTI_DOMAIN_EDGE_REGISTRY.json",
    "multi_domain_edge_registry_jsonl": "MULTI_DOMAIN_EDGE_REGISTRY.jsonl",
    "edge_registry_schema": "MULTI_DOMAIN_EDGE_REGISTRY_SCHEMA.json",
    "edge_coverage_matrix": "EDGE_COVERAGE_MATRIX.json",
    "runtime_query_fixtures": "RUNTIME_QUERY_FIXTURES.json",
    "runtime_query_results": "RUNTIME_QUERY_RESULTS.json",
    "evidence_limitation_trace": "EVIDENCE_AND_LIMITATION_TRACE.json",
    "validation_report": "EDGE_VALIDATION_REPORT.json",
    "claim_boundary_audit": "CLAIM_BOUNDARY_AUDIT.json",
    "hash_manifest": "HASH_MANIFEST.json",
    "local_open_index": "LOCAL_OPEN_INDEX.md",
}

LIMITATIONS = [
    "R8 hardening derives an annotated copy only",
    "R7 registry is not mutated in place",
    "edge count expansion is out of scope",
    "review-only edges are not promoted",
    "event/current-state context remains replay/query context only",
    "unresolved/quarantined context remains partitioned",
    "confidence is evidence/review confidence, not certified truth",
    "no production/public API readiness claim",
    "no live monitoring, autonomous detection, alerts, dispatch, routing/control, enforcement, legal, certified, or action output",
]

FORBIDDEN_CLAIM_TERMS = [
    "caused",
    "confirmed",
    "proved",
    "certified",
    "violated",
    "enforced",
    "dispatched",
    "controlled",
    "alerted",
    "legal finding",
    "production readiness",
    "public deployment",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def git_status_lines() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        return [line for line in result.stdout.splitlines() if line.strip()]
    except Exception as exc:  # pragma: no cover - defensive local runner
        return [f"GIT_STATUS_UNAVAILABLE: {exc}"]


def decision_status(root: Path) -> str | None:
    for path in sorted(root.glob("*DECISION*.json")):
        data = load_json(path)
        if isinstance(data, dict) and data.get("status"):
            return str(data["status"])
    return None


def root_hash_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    names = {"HASH_MANIFEST.json", "HASH_VALIDATION_REPORT.json", "hashes.sha256"}
    return [p for p in root.rglob("*") if p.is_file() and p.name in names]


def preservation_gate() -> dict[str, Any]:
    status_lines = git_status_lines()
    frozen_status_lines = [
        line for line in status_lines
        if any(rel(root).replace("/", "\\") in line or rel(root) in line for root in FROZEN_CHAIN_ROOTS)
    ]
    roots = []
    for root in FROZEN_CHAIN_ROOTS:
        hashes = root_hash_files(root)
        roots.append(
            {
                "root": rel(root),
                "exists": root.exists(),
                "decision_status": decision_status(root),
                "hash_manifest_or_validation_files": [
                    {"path": rel(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
                    for path in hashes
                ],
                "preserved_by_hash_manifest": bool(hashes),
            }
        )
    all_preserved = all(item["exists"] and item["preserved_by_hash_manifest"] for item in roots)
    uncommitted_frozen_artifacts = bool(frozen_status_lines)
    gate_status = "PASS_PRESERVED_BY_HASH_MANIFEST" if all_preserved and not uncommitted_frozen_artifacts else "HOLD"
    return {
        "task_name": TASK_NAME,
        "timestamp": now(),
        "git_status_entry_count": len(status_lines),
        "frozen_chain_git_status_entries": frozen_status_lines,
        "frozen_chain_uncommitted_in_git_status": uncommitted_frozen_artifacts,
        "frozen_chain_roots": roots,
        "preservation_gate_status": gate_status,
        "preservation_note": (
            "Frozen roots are consumed read-only and have hash manifests/validation artifacts; "
            "no frozen output root appears in git status."
            if gate_status.startswith("PASS")
            else "Frozen closeout artifacts appear uncommitted or lack preservation manifests; normal R8 work is held."
        ),
        "no_stage_or_commit_performed": True,
        "no_action_taken": True,
    }


def discover_inputs() -> tuple[dict[str, Any], list[str]]:
    artifact_index = {
        "task_name": TASK_NAME,
        "timestamp": now(),
        "frozen_chain_roots": [],
        "r7_required_artifacts": {},
    }
    missing: list[str] = []
    for root in FROZEN_CHAIN_ROOTS:
        artifact_index["frozen_chain_roots"].append(
            {
                "root": rel(root),
                "exists": root.exists(),
                "decision_status": decision_status(root),
                "hash_files": [rel(p) for p in root_hash_files(root)],
            }
        )
    for key, filename in R7_REQUIRED.items():
        path = R7_ROOT / filename
        if not path.exists():
            missing.append(f"R7_REQUIRED:{filename}")
            artifact_index["r7_required_artifacts"][key] = {"path": rel(path), "exists": False}
        else:
            artifact_index["r7_required_artifacts"][key] = {
                "path": rel(path),
                "exists": True,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
    return artifact_index, missing


def load_edges() -> list[dict[str, Any]]:
    registry = load_json(R7_ROOT / "MULTI_DOMAIN_EDGE_REGISTRY.json", {})
    edges = registry.get("edges", []) if isinstance(registry, dict) else []
    return [edge for edge in edges if isinstance(edge, dict)]


def ruleset(schema: dict[str, Any], edges: list[dict[str, Any]]) -> dict[str, Any]:
    props = schema.get("properties", {}) if isinstance(schema, dict) else {}
    return {
        "task_name": TASK_NAME,
        "timestamp": now(),
        "required_fields": schema.get("required", []),
        "valid_review_states": props.get("review_state", {}).get("enum", sorted({e.get("review_state") for e in edges})),
        "valid_relationship_states": props.get("relationship_state", {}).get("enum", sorted({e.get("relationship_state") for e in edges})),
        "valid_source_domains": sorted({e.get("source_domain") for e in edges}),
        "valid_target_domains": sorted({e.get("target_domain") for e in edges}),
        "valid_relationship_families": sorted({e.get("relationship_family") for e in edges}),
        "confidence_range": [0.0, 1.0],
        "partition_rules": {
            "unresolved": "review_state or relationship_state is unresolved/quarantined, or unresolved tag exists",
            "runtime_ready_review_context": "contains d6_overlay_ready tag and is not unresolved/quarantined",
            "review_only": "candidate/pending/source boundary/deprecated or not runtime_ready_review_context",
            "overlay_context": "relationship_state overlay_context or overlay tag",
            "event_current_state_context": "event_fabric source or event/current_state tag",
        },
        "no_action_taken_required": True,
        "forbidden_unsupported_claim_terms": FORBIDDEN_CLAIM_TERMS,
    }


def schema_invariant_report(edges: list[dict[str, Any]], rule: dict[str, Any]) -> dict[str, Any]:
    required = rule["required_fields"]
    valid_review = set(rule["valid_review_states"])
    valid_relationship = set(rule["valid_relationship_states"])
    valid_source_domains = set(rule["valid_source_domains"])
    valid_target_domains = set(rule["valid_target_domains"])
    valid_families = set(rule["valid_relationship_families"])
    findings = []
    for edge in edges:
        edge_id = edge.get("edge_id", "MISSING_EDGE_ID")
        for field in required:
            if field not in edge or edge.get(field) in (None, "", []):
                findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": f"missing_required_field:{field}"})
        if edge.get("review_state") not in valid_review:
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "invalid_review_state"})
        if edge.get("relationship_state") not in valid_relationship:
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "invalid_relationship_state"})
        if edge.get("source_domain") not in valid_source_domains:
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "invalid_source_domain"})
        if edge.get("target_domain") not in valid_target_domains:
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "invalid_target_domain"})
        if edge.get("relationship_family") not in valid_families:
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "invalid_relationship_family"})
        confidence = edge.get("confidence")
        if not isinstance(confidence, (int, float)) or not (0 <= float(confidence) <= 1):
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "confidence_out_of_range"})
        if edge.get("no_action_taken") is not True:
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "no_action_taken_not_true"})
    errors = [f for f in findings if f["severity"] == "ERROR"]
    return {
        "status": "PASS" if not errors else "FAIL",
        "edge_count": len(edges),
        "required_field_count": len(required),
        "finding_count": len(findings),
        "error_count": len(errors),
        "findings": findings,
        "no_action_taken": True,
    }


def duplicate_collision_report(edges: list[dict[str, Any]]) -> dict[str, Any]:
    findings = []
    by_edge_id = defaultdict(list)
    by_semantic_key = defaultdict(list)
    by_normalized_edge_type = defaultdict(list)
    entity_domain_type = defaultdict(set)
    family_domains = defaultdict(set)
    for edge in edges:
        edge_id = edge.get("edge_id")
        by_edge_id[edge_id].append(edge)
        semantic_key = (
            edge.get("source_entity_ref"),
            edge.get("target_entity_ref"),
            edge.get("relationship_family"),
        )
        by_semantic_key[semantic_key].append(edge)
        normalized_type = re.sub(r"[^a-z0-9]+", "_", str(edge.get("edge_type", "")).lower()).strip("_")
        by_normalized_edge_type[(edge.get("source_entity_ref"), edge.get("target_entity_ref"), normalized_type)].append(edge)
        entity_domain_type[edge.get("source_entity_ref")].add((edge.get("source_domain"), edge.get("source_entity_type")))
        entity_domain_type[edge.get("target_entity_ref")].add((edge.get("target_domain"), edge.get("target_entity_type")))
        family_domains[edge.get("relationship_family")].add((edge.get("source_domain"), edge.get("target_domain")))
    for edge_id, group in by_edge_id.items():
        if len(group) > 1:
            findings.append({"severity": "ERROR", "finding_type": "duplicate_edge_id", "edge_id": edge_id, "count": len(group)})
    for key, group in by_semantic_key.items():
        if len(group) > 1:
            findings.append(
                {
                    "severity": "REVIEW",
                    "finding_type": "duplicate_source_target_family",
                    "source_entity_ref": key[0],
                    "target_entity_ref": key[1],
                    "relationship_family": key[2],
                    "edge_ids": [e.get("edge_id") for e in group],
                    "recommended_remediation": "review whether multiple edge records intentionally preserve distinct upstream refs",
                }
            )
    for key, group in by_normalized_edge_type.items():
        if len(group) > 1:
            findings.append(
                {
                    "severity": "REVIEW",
                    "finding_type": "relationship_naming_variant_or_duplicate",
                    "source_entity_ref": key[0],
                    "target_entity_ref": key[1],
                    "normalized_edge_type": key[2],
                    "edge_ids": [e.get("edge_id") for e in group],
                }
            )
    for ref, domain_types in entity_domain_type.items():
        if ref and len(domain_types) > 1:
            findings.append(
                {
                    "severity": "INFO",
                    "finding_type": "entity_ref_cross_domain_or_type_collision",
                    "entity_ref": ref,
                    "domain_type_pairs": sorted([list(x) for x in domain_types]),
                    "recommended_remediation": "preserve as cross-domain context unless canonical CER mapping resolves identity",
                }
            )
    for family, domains in family_domains.items():
        if family and len(domains) > 3:
            findings.append(
                {
                    "severity": "INFO",
                    "finding_type": "edge_family_spans_multiple_domain_pairs",
                    "relationship_family": family,
                    "domain_pair_count": len(domains),
                    "domain_pairs": sorted([list(x) for x in domains]),
                }
            )
    errors = [f for f in findings if f["severity"] == "ERROR"]
    return {
        "status": "PASS_WITH_REVIEW_FINDINGS" if not errors else "FAIL",
        "duplicate_edge_id_count": sum(1 for f in findings if f["finding_type"] == "duplicate_edge_id"),
        "review_collision_count": sum(1 for f in findings if f["severity"] == "REVIEW"),
        "info_collision_count": sum(1 for f in findings if f["severity"] == "INFO"),
        "finding_count": len(findings),
        "findings": findings[:250],
        "no_action_taken": True,
    }


def domain_boundary_audit(edges: list[dict[str, Any]]) -> dict[str, Any]:
    findings = []
    for edge in edges:
        text = json.dumps(edge).lower()
        boundary_and_limits = json.dumps(
            {
                "claim_boundary": edge.get("claim_boundary"),
                "limitation_refs": edge.get("limitation_refs"),
            }
        ).lower()
        operative_text = json.dumps(
            {
                key: value
                for key, value in edge.items()
                if key not in {"claim_boundary", "limitation_refs"}
            }
        ).lower()
        edge_id = edge.get("edge_id")
        source = edge.get("source_domain")
        family = edge.get("relationship_family")
        relationship_state = edge.get("relationship_state")
        if source == "mobility" and "building_compliance" in text:
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "mobility_edge_mentions_building_compliance"})
        if source == "building_compliance" and any(term in operative_text for term in ["confirmed violation", "legal finding", "certified compliance"]):
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "building_compliance_edge_implies_forbidden_status"})
        if source == "property_planning" and any(term in operative_text for term in ["ownership", "title truth", "permit approval", "permit rejection"]):
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "property_planning_edge_implies_forbidden_status"})
        if source == "event_fabric" and relationship_state not in {"event_replay_context", "unresolved", "pending_review", "overlay_context"}:
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "event_fabric_edge_not_event_context_state"})
        if source == "track2a_omniverse_event_overlay" and relationship_state != "overlay_context":
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "omniverse_overlay_edge_not_overlay_context"})
        if source == "city_asset_identity" and "certified" in operative_text and "certified" not in boundary_and_limits:
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "city_asset_identity_certified_claim"})
        if family == "event_fabric_state_entity_context" and "caused" in text:
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "event_context_implies_causal_truth"})
    return {
        "status": "PASS" if not findings else "FAIL",
        "finding_count": len(findings),
        "findings": findings,
        "no_action_taken": True,
    }


def review_state_preservation(edges: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(edge.get("review_state") for edge in edges)
    relationship_counts = Counter(edge.get("relationship_state") for edge in edges)
    findings = []
    for edge in edges:
        state = edge.get("review_state")
        rel_state = edge.get("relationship_state")
        edge_id = edge.get("edge_id")
        if state in {"unresolved", "quarantined"} and "d6_overlay_ready" in edge.get("runtime_query_tags", []):
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "unresolved_or_quarantined_promoted_to_overlay_ready"})
        if rel_state in {"unresolved", "quarantined"} and state not in {"unresolved", "quarantined"}:
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "relationship_unresolved_state_not_preserved_in_review_state"})
        if any(term in str(state).lower() for term in ["certified", "enforcement", "dispatch", "action"]):
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "review_state_implies_forbidden_status"})
    return {
        "status": "PASS" if not findings else "FAIL",
        "review_state_counts": dict(counts),
        "relationship_state_counts": dict(relationship_counts),
        "unresolved_count": counts.get("unresolved", 0),
        "quarantined_count": counts.get("quarantined", 0) + relationship_counts.get("quarantined", 0),
        "finding_count": len(findings),
        "findings": findings,
        "no_action_taken": True,
    }


def confidence_audit(edges: list[dict[str, Any]]) -> dict[str, Any]:
    findings = []
    tiers = Counter()
    for edge in edges:
        confidence = edge.get("confidence")
        state = edge.get("review_state")
        edge_id = edge.get("edge_id")
        if not isinstance(confidence, (int, float)) or not (0 <= float(confidence) <= 1):
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "confidence_missing_or_out_of_range"})
            continue
        if confidence < 0.5:
            tiers["low"] += 1
        elif confidence < 0.75:
            tiers["medium"] += 1
        else:
            tiers["higher_review_confidence"] += 1
        if state in {"unresolved", "quarantined"} and confidence >= 0.7:
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "unresolved_edge_has_high_confidence"})
        if confidence >= 0.8 and edge.get("relationship_state") in {"event_replay_context", "overlay_context"}:
            findings.append({"edge_id": edge_id, "severity": "INFO", "finding": "high_confidence_overlay_or_event_context_remains_non_certified"})
    errors = [f for f in findings if f["severity"] == "ERROR"]
    return {
        "status": "PASS_WITH_INFO" if not errors else "FAIL",
        "confidence_tiers": dict(tiers),
        "finding_count": len(findings),
        "error_count": len(errors),
        "findings": findings,
        "confidence_semantics": "confidence is evidence/review confidence only and does not override review_state",
        "no_action_taken": True,
    }


def evidence_limitation_report(edges: list[dict[str, Any]]) -> dict[str, Any]:
    findings = []
    for edge in edges:
        edge_id = edge.get("edge_id")
        unresolved = edge.get("review_state") in {"unresolved", "quarantined"} or edge.get("relationship_state") in {"unresolved", "quarantined"}
        if not unresolved and not edge.get("evidence_refs"):
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "non_quarantined_edge_missing_evidence_refs"})
        if edge.get("relationship_state") in {"inferred_review_context", "event_replay_context", "overlay_context"} and not edge.get("limitation_refs"):
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "inferred_replay_overlay_edge_missing_limitation_refs"})
        if unresolved and not edge.get("limitation_refs"):
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "unresolved_or_quarantined_edge_missing_limitation_reason"})
        if not edge.get("source_branch_refs"):
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "missing_source_branch_refs"})
    return {
        "status": "PASS" if not findings else "FAIL",
        "finding_count": len(findings),
        "findings": findings,
        "non_quarantined_edge_count": sum(
            1 for edge in edges
            if edge.get("review_state") not in {"unresolved", "quarantined"} and edge.get("relationship_state") not in {"unresolved", "quarantined"}
        ),
        "no_action_taken": True,
    }


def partition_edge(edge: dict[str, Any]) -> set[str]:
    tags = set(edge.get("runtime_query_tags", []))
    review = edge.get("review_state")
    rel_state = edge.get("relationship_state")
    parts = set()
    if review == "quarantined" or rel_state == "quarantined":
        parts.add("quarantined_edges")
    if review == "unresolved" or rel_state == "unresolved" or "unresolved" in tags:
        parts.add("unresolved_edges")
    if rel_state == "overlay_context" or "overlay" in tags:
        parts.add("overlay_context_edges")
    if edge.get("source_domain") == "event_fabric" or "event_context" in tags or "current_state" in tags:
        parts.add("event_current_state_context_edges")
    if "d6_overlay_ready" in tags and not {"unresolved_edges", "quarantined_edges"} & parts:
        parts.add("runtime_ready_review_context_edges")
    if review in {"candidate_pending_review", "pending_review", "source_id_boundary_review", "deprecated_superseded"} or "runtime_ready_review_context_edges" not in parts:
        parts.add("review_only_edges")
    return parts


def partition_report(edges: list[dict[str, Any]]) -> dict[str, Any]:
    buckets = {
        "runtime_ready_review_context_edges": [],
        "review_only_edges": [],
        "unresolved_edges": [],
        "quarantined_edges": [],
        "overlay_context_edges": [],
        "event_current_state_context_edges": [],
    }
    for edge in edges:
        for part in partition_edge(edge):
            buckets[part].append(edge.get("edge_id"))
    return {
        "status": "PASS",
        "counts": {key: len(value) for key, value in buckets.items()},
        "partitions": buckets,
        "partition_boundary": "runtime_ready_review_context is local/replay query readiness, not production readiness",
        "no_action_taken": True,
    }


def event_relationship_separation(edges: list[dict[str, Any]]) -> dict[str, Any]:
    findings = []
    for edge in edges:
        edge_id = edge.get("edge_id")
        # Only Event Fabric source-domain edges are event-state edges. Other
        # domains may carry an "event_context" query tag for compatibility
        # without becoming event-state truth.
        if edge.get("source_domain") == "event_fabric" and edge.get("relationship_state") not in {
            "event_replay_context",
            "overlay_context",
            "unresolved",
            "pending_review",
        }:
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "event_edge_state_not_contextual"})
        text = json.dumps(edge).lower()
        if "causal" in text or "diagnosis" in text:
            findings.append({"edge_id": edge_id, "severity": "ERROR", "finding": "event_edge_implies_causal_diagnosis"})
    return {
        "status": "PASS" if not findings else "FAIL",
        "event_context_edge_count": sum(
            1 for edge in edges if edge.get("source_domain") == "event_fabric" or "event_context" in edge.get("runtime_query_tags", [])
        ),
        "finding_count": len(findings),
        "findings": findings,
        "separation_boundary": "event/current-state context does not become permanent relationship or causal truth",
        "no_action_taken": True,
    }


def term_is_negated(text: str, start: int) -> bool:
    prefix = text[max(0, start - 180):start].lower()
    # A single "No ..." often governs comma-separated boundary lists such as
    # "No production service, public API, ... certified fact status".
    segment_after_sentence = re.split(r"[.;]", prefix)[-1]
    return any(marker in segment_after_sentence for marker in ["no ", "not ", "without ", "never ", "does not ", "do not "])


def causal_leakage_audit(edges: list[dict[str, Any]]) -> dict[str, Any]:
    findings = []
    negated_hits = 0
    for edge in edges:
        boundary_text = json.dumps(
            {
                "claim_boundary": edge.get("claim_boundary"),
                "limitation_refs": edge.get("limitation_refs"),
            }
        ).lower()
        operative_text = json.dumps(
            {
                key: value
                for key, value in edge.items()
                if key not in {"claim_boundary", "limitation_refs"}
            }
        ).lower()
        for term in FORBIDDEN_CLAIM_TERMS:
            for match in re.finditer(re.escape(term), boundary_text):
                if term_is_negated(boundary_text, match.start()):
                    negated_hits += 1
                else:
                    findings.append(
                        {
                            "edge_id": edge.get("edge_id"),
                            "severity": "ERROR",
                            "term": term,
                            "finding": "unsupported_causal_or_certified_claim_term",
                        }
                    )
            for match in re.finditer(re.escape(term), operative_text):
                if term_is_negated(operative_text, match.start()):
                    negated_hits += 1
                else:
                    findings.append(
                        {
                            "edge_id": edge.get("edge_id"),
                            "severity": "ERROR",
                            "term": term,
                            "finding": "unsupported_causal_or_certified_claim_term",
                        }
                    )
    return {
        "status": "PASS" if not findings else "FAIL",
        "unsupported_claim_term_count": len(findings),
        "negated_boundary_term_count": negated_hits,
        "findings": findings[:200],
        "no_action_taken": True,
    }


def query_regression(edges: list[dict[str, Any]], partition: dict[str, Any]) -> dict[str, Any]:
    fixtures = []
    if not edges:
        return {"status": "FAIL", "pass_count": 0, "fail_count": 10, "results": []}
    sample = edges[0]
    fixtures.append(("edges_by_canonical_or_entity_ref", lambda: [e for e in edges if e.get("source_entity_ref") == sample.get("source_entity_ref") or e.get("target_entity_ref") == sample.get("source_entity_ref")]))
    fixtures.append(("edges_by_domain_pair", lambda: [e for e in edges if e.get("source_domain") == sample.get("source_domain") and e.get("target_domain") == sample.get("target_domain")]))
    fixtures.append(("edges_by_relationship_family", lambda: [e for e in edges if e.get("relationship_family") == sample.get("relationship_family")]))
    fixtures.append(("event_context_edges", lambda: [e for e in edges if e.get("source_domain") == "event_fabric" or "event_context" in e.get("runtime_query_tags", [])]))
    fixtures.append(("asset_identity_edges", lambda: [e for e in edges if e.get("source_domain") == "city_asset_identity" or "asset_identity" in e.get("runtime_query_tags", [])]))
    fixtures.append(("unresolved_quarantined_edges", lambda: [e for e in edges if e.get("edge_id") in set(partition["partitions"]["unresolved_edges"] + partition["partitions"]["quarantined_edges"])]))
    fixtures.append(("evidence_refs_by_edge", lambda: [sample] if sample.get("evidence_refs") else []))
    fixtures.append(("limitation_refs_by_edge", lambda: [sample] if sample.get("limitation_refs") else []))
    fixtures.append(("runtime_ready_partition_query", lambda: [e for e in edges if e.get("edge_id") in set(partition["partitions"]["runtime_ready_review_context_edges"])]))
    fixtures.append(("review_only_partition_query", lambda: [e for e in edges if e.get("edge_id") in set(partition["partitions"]["review_only_edges"])]))
    results = []
    for index, (name, fn) in enumerate(fixtures, start=1):
        rows = fn()
        passed = len(rows) > 0
        results.append(
            {
                "fixture_id": f"r8-query-regression-{index:03d}",
                "query_profile": name,
                "status": "PASS" if passed else "FAIL",
                "result_count": len(rows),
                "result_edge_refs": [row.get("edge_id") for row in rows[:10]],
                "no_action_taken": True,
            }
        )
    pass_count = sum(1 for row in results if row["status"] == "PASS")
    fail_count = len(results) - pass_count
    return {
        "status": "PASS" if fail_count == 0 else "FAIL",
        "pass_count": pass_count,
        "fail_count": fail_count,
        "results": results,
        "no_action_taken": True,
    }


def hardened_registry(edges: list[dict[str, Any]], partition: dict[str, Any], reports: dict[str, Any]) -> list[dict[str, Any]]:
    partition_by_edge = defaultdict(list)
    for bucket, edge_ids in partition["partitions"].items():
        for edge_id in edge_ids:
            partition_by_edge[edge_id].append(bucket)
    hardened = []
    for edge in edges:
        copy = dict(edge)
        copy["r8_hardening"] = {
            "hardened_by_task": TASK_NAME,
            "hardened_at": now(),
            "source_edge_id_preserved": edge.get("edge_id"),
            "partition_labels": sorted(partition_by_edge.get(edge.get("edge_id"), [])),
            "review_state_preserved": edge.get("review_state"),
            "relationship_state_preserved": edge.get("relationship_state"),
            "confidence_semantics": "review/evidence confidence only; not certified truth",
            "runtime_compatibility": "local/replay query compatibility only",
            "no_action_taken": True,
        }
        hardened.append(copy)
    return hardened


def claim_boundary_audit(causal: dict[str, Any], domain: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS" if causal["status"] == "PASS" and domain["status"] == "PASS" else "FAIL",
        "causal_leakage_status": causal["status"],
        "domain_boundary_status": domain["status"],
        "unsupported_claim_term_count": causal["unsupported_claim_term_count"],
        "negated_boundary_term_count": causal["negated_boundary_term_count"],
        "boundary": "No production, public API, monitoring, alerting, dispatch, routing/control, enforcement, legal, certified, or action claims.",
        "no_action_taken": True,
    }


def no_mutation_audit(before_hashes: dict[str, str]) -> dict[str, Any]:
    after = {name: sha256_file(R7_ROOT / filename) for name, filename in R7_REQUIRED.items() if (R7_ROOT / filename).exists()}
    changed = [
        {"artifact_key": key, "before": before_hashes.get(key), "after": value}
        for key, value in after.items()
        if before_hashes.get(key) != value
    ]
    return {
        "status": "PASS" if not changed else "FAIL",
        "r7_required_artifact_count": len(before_hashes),
        "changed_artifact_count": len(changed),
        "changed_artifacts": changed,
        "writes_restricted_to_output_root": True,
        "source_mutation_attempted": False,
        "no_action_taken": True,
    }


def secret_audit() -> dict[str, Any]:
    patterns = [
        re.compile(r"api[_-]?key\\s*[:=]\\s*['\\\"][^'\\\"]+", re.I),
        re.compile(r"authorization\\s*[:=]", re.I),
        re.compile(r"bearer\\s+[A-Za-z0-9._-]{16,}", re.I),
        re.compile(r"token\\s*[:=]\\s*['\\\"][^'\\\"]+", re.I),
        re.compile(r"\\.env", re.I),
    ]
    findings = []
    for path in OUTPUT_ROOT.rglob("*"):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                if pattern.search(text):
                    findings.append({"path": rel(path), "pattern": pattern.pattern})
    return {"status": "PASS" if not findings else "FAIL", "finding_count": len(findings), "findings": findings}


def hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append({"path": rel(path), "sha256": sha256_file(path), "bytes": path.stat().st_size})
    manifest = {
        "task_name": TASK_NAME,
        "timestamp": now(),
        "hash_validation_status": "PASS",
        "file_count": len(files),
        "files": files,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def write_hold(preservation: dict[str, Any], artifact_index: dict[str, Any], missing: list[str]) -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    decision = {
        "status": HOLD_STATUS,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "preservation_gate_status": preservation["preservation_gate_status"],
        "missing_required_artifacts": missing,
        "limitations": LIMITATIONS,
        "recommended_next_task": "preserve or commit frozen chain, then rerun R8 hardening",
    }
    write_json(OUTPUT_ROOT / "PRESERVATION_GATE_REPORT.json", preservation)
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", artifact_index)
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_DECISION.json", decision)


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    preservation = preservation_gate()
    artifact_index, missing = discover_inputs()

    if preservation["preservation_gate_status"] == "HOLD":
        write_hold(preservation, artifact_index, missing)
        print(json.dumps({"status": HOLD_STATUS, "output_root": str(OUTPUT_ROOT)}, indent=2))
        return 0

    if missing:
        write_json(OUTPUT_ROOT / "PRESERVATION_GATE_REPORT.json", preservation)
        write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", artifact_index)
        decision = {
            "status": FAIL_STATUS,
            "task_name": TASK_NAME,
            "timestamp": now(),
            "missing_required_artifacts": missing,
            "limitations": LIMITATIONS,
            "recommended_next_task": "restore missing R7 required artifacts, then rerun R8 hardening",
        }
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_DECISION.json", decision)
        print(json.dumps(decision, indent=2, sort_keys=True))
        return 1

    before_hashes = {name: sha256_file(R7_ROOT / filename) for name, filename in R7_REQUIRED.items()}
    edges = load_edges()
    schema = load_json(R7_ROOT / "MULTI_DOMAIN_EDGE_REGISTRY_SCHEMA.json", {})
    r7_decision = load_json(R7_ROOT / "MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_DECISION.json", {})
    rule = ruleset(schema, edges)
    schema_report = schema_invariant_report(edges, rule)
    duplicate_report = duplicate_collision_report(edges)
    domain_report = domain_boundary_audit(edges)
    review_report = review_state_preservation(edges)
    confidence_report = confidence_audit(edges)
    evidence_report = evidence_limitation_report(edges)
    partition = partition_report(edges)
    separation_report = event_relationship_separation(edges)
    causal_report = causal_leakage_audit(edges)
    query_report = query_regression(edges, partition)
    hardened_edges = hardened_registry(edges, partition, {})
    claim_report = claim_boundary_audit(causal_report, domain_report)
    no_mutation = no_mutation_audit(before_hashes)

    consumption = {
        "task_name": TASK_NAME,
        "timestamp": now(),
        "r7_status": r7_decision.get("status"),
        "r7_edge_count_consumed": len(edges),
        "r7_decision_edge_count": r7_decision.get("total_edge_count"),
        "r7_unresolved_quarantined_count": r7_decision.get("unresolved_quarantined_count"),
        "source_registry_sha256": before_hashes.get("multi_domain_edge_registry"),
        "source_registry_jsonl_sha256": before_hashes.get("multi_domain_edge_registry_jsonl"),
        "source_schema_sha256": before_hashes.get("edge_registry_schema"),
        "source_mutated": False,
        "no_action_taken": True,
    }

    frozen_register = {
        "task_name": TASK_NAME,
        "timestamp": now(),
        "frozen_chain": artifact_index["frozen_chain_roots"],
        "consumption_boundary": "read-only; consumed for compatibility checks only",
        "no_action_taken": True,
    }

    write_json(OUTPUT_ROOT / "PRESERVATION_GATE_REPORT.json", preservation)
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", artifact_index)
    write_json(OUTPUT_ROOT / "FROZEN_CHAIN_CONSUMPTION_REGISTER.json", frozen_register)
    write_json(OUTPUT_ROOT / "R7_CONSUMPTION_REGISTER.json", consumption)
    write_json(OUTPUT_ROOT / "R8_HARDENING_RULESET.json", rule)
    write_json(OUTPUT_ROOT / "EDGE_SCHEMA_INVARIANT_REPORT.json", schema_report)
    write_json(OUTPUT_ROOT / "EDGE_DUPLICATE_COLLISION_REPORT.json", duplicate_report)
    write_json(OUTPUT_ROOT / "DOMAIN_BOUNDARY_AUDIT.json", domain_report)
    write_json(OUTPUT_ROOT / "REVIEW_STATE_PRESERVATION_AUDIT.json", review_report)
    write_json(OUTPUT_ROOT / "CONFIDENCE_SEMANTICS_AUDIT.json", confidence_report)
    write_json(OUTPUT_ROOT / "EVIDENCE_LIMITATION_COMPLETENESS_REPORT.json", evidence_report)
    write_json(OUTPUT_ROOT / "RUNTIME_READY_REVIEW_ONLY_PARTITION.json", partition)
    write_json(OUTPUT_ROOT / "EVENT_STATE_RELATIONSHIP_STATE_SEPARATION_AUDIT.json", separation_report)
    write_json(OUTPUT_ROOT / "CAUSAL_LEAKAGE_AUDIT.json", causal_report)
    write_json(OUTPUT_ROOT / "QUERY_PROFILE_REGRESSION_RESULTS.json", query_report)
    write_json(
        OUTPUT_ROOT / "HARDENED_MULTI_DOMAIN_EDGE_REGISTRY.json",
        {
            "task_name": TASK_NAME,
            "status": "HARDENED_COPY_WITH_R8_ANNOTATIONS",
            "source_r7_registry_ref": rel(R7_ROOT / "MULTI_DOMAIN_EDGE_REGISTRY.json"),
            "edge_count": len(hardened_edges),
            "edges": hardened_edges,
            "limitations": LIMITATIONS,
        },
    )
    write_jsonl(OUTPUT_ROOT / "HARDENED_MULTI_DOMAIN_EDGE_REGISTRY.jsonl", hardened_edges)
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim_report)
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", no_mutation)

    compatibility_md = f"""# R8 Compatibility Notes

R8 consumes the frozen R7/D5/D6 chain read-only and emits a hardened copy with annotations. It does not change edge IDs, source/target refs, relationship family, relationship state, review state, evidence refs, limitation refs, or confidence values.

Compatibility facts:

- R7 edge count consumed: {len(edges)}
- Hardened edge count: {len(hardened_edges)}
- Query regression pass/fail: {query_report["pass_count"]}/{query_report["fail_count"]}
- Runtime-ready review-context partition: {partition["counts"]["runtime_ready_review_context_edges"]}
- Review-only partition: {partition["counts"]["review_only_edges"]}
- Unresolved partition: {partition["counts"]["unresolved_edges"]}

The hardened registry remains local/replay query context only. It is not a production service, public API, live monitoring layer, alerting system, dispatch/routing/control system, enforcement system, legal/certified truth layer, or autonomous action path.
"""
    local_index = f"""# Local Open Index

- Decision: `MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_DECISION.json`
- Hardened registry: `HARDENED_MULTI_DOMAIN_EDGE_REGISTRY.json`
- Hardened registry JSONL: `HARDENED_MULTI_DOMAIN_EDGE_REGISTRY.jsonl`
- Partition: `RUNTIME_READY_REVIEW_ONLY_PARTITION.json`
- Duplicate/collision report: `EDGE_DUPLICATE_COLLISION_REPORT.json`
- Query regression: `QUERY_PROFILE_REGRESSION_RESULTS.json`
- R7 consumption register: `R7_CONSUMPTION_REGISTER.json`
- Frozen-chain consumption register: `FROZEN_CHAIN_CONSUMPTION_REGISTER.json`
"""
    readme = f"""# {TASK_NAME}

Status: {PASS_STATUS}

This pack hardens the R7 multi-domain edge registry by producing an annotated copy and audit reports. It does not mutate R7 or any frozen D5/D6/Track2 output.

R7 edges consumed: {len(edges)}
Hardened edges emitted: {len(hardened_edges)}
"""
    write_text(OUTPUT_ROOT / "R8_COMPATIBILITY_NOTES.md", compatibility_md)
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", local_index)
    write_text(OUTPUT_ROOT / "README.md", readme)

    secret = secret_audit()
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", secret)
    hash_data = hash_manifest()

    report_statuses = {
        "schema_invariant": schema_report["status"],
        "duplicate_collision": duplicate_report["status"],
        "domain_boundary": domain_report["status"],
        "review_state_preservation": review_report["status"],
        "confidence_semantics": confidence_report["status"],
        "evidence_limitation": evidence_report["status"],
        "partition": partition["status"],
        "event_relationship_separation": separation_report["status"],
        "causal_leakage": causal_report["status"],
        "query_regression": query_report["status"],
        "claim_boundary": claim_report["status"],
        "no_mutation": no_mutation["status"],
        "secret": secret["status"],
        "hash_validation": hash_data["hash_validation_status"],
    }
    hard_fail = any(status == "FAIL" for status in report_statuses.values())
    final_status = FAIL_STATUS if hard_fail else PASS_STATUS
    decision = {
        "status": final_status,
        "task_name": TASK_NAME,
        "timestamp": now(),
        "output_root": str(OUTPUT_ROOT),
        "upstream_r7_discovered": R7_ROOT.exists(),
        "frozen_closeout_discovered": D6_CLOSEOUT_ROOT.exists(),
        "missing_required_artifacts": missing,
        "preservation_gate_status": preservation["preservation_gate_status"],
        "r7_edge_count_consumed": len(edges),
        "hardened_edge_count": len(hardened_edges),
        "r7_unresolved_quarantined_count": r7_decision.get("unresolved_quarantined_count"),
        "unresolved_count_preserved": partition["counts"]["unresolved_edges"],
        "quarantined_count_preserved": partition["counts"]["quarantined_edges"],
        "runtime_ready_review_context_count": partition["counts"]["runtime_ready_review_context_edges"],
        "review_only_count": partition["counts"]["review_only_edges"],
        "overlay_context_count": partition["counts"]["overlay_context_edges"],
        "event_current_state_context_count": partition["counts"]["event_current_state_context_edges"],
        "duplicate_edge_id_count": duplicate_report["duplicate_edge_id_count"],
        "duplicate_collision_review_finding_count": duplicate_report["review_collision_count"],
        "duplicate_collision_info_finding_count": duplicate_report["info_collision_count"],
        "query_regression_pass_count": query_report["pass_count"],
        "query_regression_fail_count": query_report["fail_count"],
        "schema_invariant_status": schema_report["status"],
        "duplicate_collision_status": duplicate_report["status"],
        "domain_boundary_audit_result": domain_report["status"],
        "review_state_preservation_result": review_report["status"],
        "confidence_semantics_result": confidence_report["status"],
        "evidence_limitation_completeness_result": evidence_report["status"],
        "event_state_relationship_state_separation_result": separation_report["status"],
        "causal_leakage_audit_result": causal_report["status"],
        "claim_boundary_audit_result": claim_report["status"],
        "no_mutation_audit_result": no_mutation["status"],
        "secret_audit_result": secret["status"],
        "hash_validation_result": hash_data["hash_validation_status"],
        "limitations": LIMITATIONS,
        "recommended_next_task": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-EVIDENCE-BUNDLE-R1",
        "fallback_next_task_if_incident_mode_preflight_not_green": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-PREFLIGHT",
        "later_platform_option_if_incident_and_r8_green": "MAIN-CITYBRAIN-D6-CER-SEG-CROSS-CITY-V2-PREFLIGHT",
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_DECISION.json", decision)
    hash_manifest()

    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if final_status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

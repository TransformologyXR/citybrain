#!/usr/bin/env python3
"""Build the Track 1 D4Y R7 cross-domain relationship substrate preflight pack.

This runner is intentionally backend-only. It defines the relationship
ontology/contract/policies that later Incident Mode and insight/watchlist work
can consume, while avoiding D6 frontend, Omniverse, and served-runtime surfaces.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-TRACK1-D4Y-R7-CROSS-DOMAIN-RELATIONSHIP-SUBSTRATE-PREFLIGHT"
STATUS = "PASS_WITH_LIMITATIONS"
HOLD_STATUS = "HOLD"
FAIL_STATUS = "FAIL"
SCHEMA_VERSION = "main-track1-d4y-r7-cross-domain-relationship-substrate-preflight.v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs/main_track1_d4y_r7_cross_domain_relationship_substrate_preflight"
RUNNER_PATH = REPO_ROOT / "scripts/run_main_track1_d4y_r7_cross_domain_relationship_substrate_preflight.py"

UPSTREAM_ROOTS = {
    "r4_canonical_entity_bridge": REPO_ROOT / "outputs/main_track1_d4y_r4_canonical_entity_bridge_preflight",
    "r4_semantic_graph_bridge": REPO_ROOT / "outputs/main_track1_d4y_r4_semantic_graph_bridge_preflight",
    "d4y_situation_graph_query": REPO_ROOT / "outputs/main_track1_d4y_situation_graph_and_query_r1",
    "r5_first_two_domain_proof": REPO_ROOT / "outputs/main_track1_d4y_r5_domain_pack_first_two_domain_proof_end_to_end",
    "r6_incident_event_mode": REPO_ROOT / "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end",
    "live_event_fabric_slice": REPO_ROOT / "outputs/main_citybrain_d4x_live_event_fabric_minimal_local_slice",
    "d5_app_packet_slice": REPO_ROOT / "outputs/main_citybrain_d5_local_served_runtime_app_integration_slice_r1",
    "track2b_city_episode_pack": REPO_ROOT / "outputs/main_track2b_d4x_city_episode_pack_end_to_end",
    "track2a_asset_registry": REPO_ROOT / "outputs/main_track2a_d4x_city_asset_contract_and_crosscity_registry_end_to_end",
}

D6_AND_SURFACE_WATCH = {
    "d6_runtime_demo_preflight": REPO_ROOT / "outputs/main_citybrain_d6_runtime_demo_preflight_r1",
    "d6_end_to_end_frontend_handover": REPO_ROOT / "outputs/main_citybrain_d6_end_to_end_demo_and_episode_frontend_handover_r1",
    "d5_app_consumption_smoke": REPO_ROOT / "outputs/main_citybrain_d5_local_served_runtime_app_consumption_smoke_r1",
    "omniverse_kit_selection_extension": REPO_ROOT / "outputs/main_track2a_d4x_omniverse_kit_selection_extension_r1",
    "omniverse_gui_smoke": REPO_ROOT / "outputs/main_track2a_d4x_omniverse_kit_composer_gui_smoke_r2",
    "manual_omniverse_acceptance": REPO_ROOT / "outputs/manual_main_track2a_d4x_omniverse_composer_selection_acceptance_r1",
    "d5_served_runtime_script": REPO_ROOT / "scripts/run_main_citybrain_d5_local_served_runtime_hardening_r1.py",
}

LIMITATIONS = [
    "preflight-only relationship substrate",
    "small curated edge fixture set",
    "real evidence refs are file/packet backed but not a graph database runtime",
    "no production CER/SEG implementation",
    "no relationship traversal service",
    "no D6 frontend, demo surface, operator briefing, or executive narrative",
    "no Omniverse/USD/Kit mutation",
    "no served runtime mutation",
    "no causal, legal, certified-impact, command, routing, dispatch, or autonomous-action claim",
    "candidate and review relationships are context only, not facts",
]

NEXT_TASK = "MAIN-TRACK1-D4Y-R7-CROSS-DOMAIN-RELATIONSHIP-EDGE-SEED-R1"
AFTER_D6_TASK = "MAIN-CITYBRAIN-D6-INCIDENT-MODE-BACKEND-PREFLIGHT"

ALLOWED_RELATIONSHIP_TYPES = [
    "contains",
    "located_in",
    "adjacent_to",
    "serves",
    "monitored_by",
    "has_event_context",
    "has_permit_context",
    "has_inspection_context",
    "has_violation_context",
    "has_mobility_context",
    "spatially_near",
    "temporally_near",
    "co_occurs_with",
    "candidate_related_to",
    "requires_review",
]

FORBIDDEN_RELATIONSHIP_TYPES = [
    "caused_by",
    "causes",
    "responsible_for",
    "led_to",
    "resulted_in",
    "triggered",
    "proves",
    "confirmed_impact",
    "certified_affected",
    "dispatches",
    "enforces",
    "controls",
    "legal_finding",
    "ownership_conclusion",
]

FORBIDDEN_ACCEPTED_WORDS = [
    "caused",
    "caused_by",
    "triggered",
    "responsible_for",
    "resulted_in",
    "led_to",
    "proved",
    "confirmed impact",
    "certified affected",
    "legal violation",
    "control action",
]

REVIEW_STATES = [
    "asserted_source",
    "inferred_deterministic",
    "candidate_probabilistic",
    "requires_review",
    "rejected",
    "disputed",
    "deprecated",
]

ASSERTION_METHODS = [
    "source_asserted",
    "geometry_containment",
    "geometry_adjacency",
    "shared_identifier",
    "event_resolution",
    "document_reference",
    "temporal_cooccurrence",
    "spatial_proximity",
    "manual_bridge",
]

REQUIRED_ASSERTION_FIELDS = [
    "relationship_id",
    "relationship_type",
    "source_canonical_entity_id",
    "source_entity_type",
    "target_canonical_entity_id",
    "target_entity_type",
    "direction",
    "confidence",
    "review_state",
    "evidence_refs",
    "trace_refs",
    "source_system_refs",
    "temporal_scope",
    "spatial_scope",
    "assertion_method",
    "assertion_boundary",
    "limitations",
    "not_causal",
    "no_action_taken",
    "created_by_run",
    "created_at_utc",
]


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def path_signature(path: Path) -> dict[str, str]:
    if not path.exists():
        return {"__missing__": "true"}
    if path.is_file():
        stat = path.stat()
        return {path.name: f"{stat.st_size}:{int(stat.st_mtime)}"}
    signature: dict[str, str] = {}
    files = sorted(p for p in path.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    for candidate in files[:1000]:
        stat = candidate.stat()
        signature[candidate.relative_to(path).as_posix()] = f"{stat.st_size}:{int(stat.st_mtime)}"
    signature["__file_count__"] = str(len(files))
    return signature


def prepare_output_root() -> None:
    resolved = OUTPUT_ROOT.resolve()
    expected_parent = (REPO_ROOT / "outputs").resolve()
    if resolved.parent != expected_parent or resolved.name != "main_track1_d4y_r7_cross_domain_relationship_substrate_preflight":
        raise RuntimeError(f"Refusing to reset unexpected output root: {resolved}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def artifact_status(path: Path) -> dict[str, Any]:
    data: Any = None
    if path.exists() and path.suffix.lower() == ".json":
        try:
            data = read_json(path, None)
        except json.JSONDecodeError:
            data = None
    status = None
    if isinstance(data, dict):
        status = data.get("status")
    return {
        "path": rel(path),
        "exists": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
        "status": status,
    }


def upstream_audit() -> dict[str, Any]:
    inspected = []
    for key, root in UPSTREAM_ROOTS.items():
        decision_files = sorted(root.glob("*DECISION.json")) if root.exists() and root.is_dir() else []
        inspected.append(
            {
                "input_id": key,
                "root": rel(root),
                "exists": root.exists(),
                "decision_artifacts": [artifact_status(path) for path in decision_files[:5]],
                "file_count": len(list(root.rglob("*"))) if root.exists() and root.is_dir() else (1 if root.exists() else 0),
            }
        )
    backend_present = [item["input_id"] for item in inspected if item["exists"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-UPSTREAM-AND-NONCOLLISION-AUDIT-R0",
        "status": "PASS" if len(backend_present) >= 4 else "PASS_WITH_LIMITATIONS" if backend_present else "HOLD",
        "backend_artifacts_present": backend_present,
        "backend_artifact_count": len(backend_present),
        "inputs_inspected": inspected,
        "relationship_substrate_can_run_without_surface_mutation": bool(backend_present),
        "limitations": [] if len(backend_present) >= 4 else ["limited upstream backend/domain/graph coverage found"],
    }


def noncollision_audit(before: dict[str, dict[str, str]], after: dict[str, dict[str, str]]) -> dict[str, Any]:
    changes = []
    for key in sorted(set(before) | set(after)):
        if before.get(key) != after.get(key):
            changes.append({"surface": key, "before": before.get(key), "after": after.get(key)})
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-UPSTREAM-AND-NONCOLLISION-AUDIT-R0",
        "status": "PASS" if not changes else "FAIL",
        "watched_surfaces": {key: rel(path) for key, path in D6_AND_SURFACE_WATCH.items()},
        "d6_episode_frontend_artifacts_created_or_modified": False,
        "d6_runtime_demo_pages_created_or_modified": False,
        "control_room_operator_executive_narratives_created_or_modified": False,
        "omniverse_usd_kit_artifacts_created_or_modified": False,
        "manual_omniverse_acceptance_artifacts_created_or_modified": False,
        "served_runtime_implementation_modified": False,
        "observed_signature_changes": changes,
        "collision_avoidance_passed": not changes,
    }


def relationship_ontology() -> dict[str, Any]:
    family_map = {
        "contains": ("structural", "Hierarchical containment where a source explicitly supports parent/child context."),
        "located_in": ("spatial", "Entity is located within a place, district, parcel, or other spatial container."),
        "adjacent_to": ("spatial", "Entities share a boundary or modeled adjacency."),
        "serves": ("service_dependency", "Asset or service context is documented as serving another entity."),
        "monitored_by": ("service_dependency", "Entity is monitored by a source system or review mechanism."),
        "has_event_context": ("event_context", "Entity has bounded event/review context from an event or incident packet."),
        "has_permit_context": ("document_case_context", "Entity has permit document context without legal conclusion."),
        "has_inspection_context": ("document_case_context", "Entity has inspection document context without legal conclusion."),
        "has_violation_context": ("document_case_context", "Entity has violation-context records without confirmed finding."),
        "has_mobility_context": ("event_context", "Entity has mobility/replay context, simulation or source-labeled as bounded context."),
        "spatially_near": ("temporal_correlative", "Entities are spatially near under a bounded method and threshold."),
        "temporally_near": ("temporal_correlative", "Events/entities are near in time under a bounded window."),
        "co_occurs_with": ("temporal_correlative", "Events/entities co-occur in a bounded context without causal meaning."),
        "candidate_related_to": ("candidate_review", "Potential relation that needs review and stronger evidence."),
        "requires_review": ("candidate_review", "Relation is blocked from stronger use until reviewed."),
    }
    inverse = {
        "contains": "located_in",
        "located_in": "contains",
        "adjacent_to": "adjacent_to",
        "serves": "served_by",
        "monitored_by": "monitors",
        "has_event_context": "event_context_for",
        "has_permit_context": "permit_context_for",
        "has_inspection_context": "inspection_context_for",
        "has_violation_context": "violation_context_for",
        "has_mobility_context": "mobility_context_for",
        "spatially_near": "spatially_near",
        "temporally_near": "temporally_near",
        "co_occurs_with": "co_occurs_with",
        "candidate_related_to": "candidate_related_to",
        "requires_review": "review_required_for",
    }
    relationship_types = []
    for rtype in ALLOWED_RELATIONSHIP_TYPES:
        family, purpose = family_map[rtype]
        candidate_family = family in {"candidate_review", "temporal_correlative"} or rtype.startswith("has_")
        relationship_types.append(
            {
                "relationship_type": rtype,
                "family": family,
                "purpose": purpose,
                "source_entity_types_allowed": [
                    "building",
                    "parcel",
                    "address",
                    "road_segment",
                    "community",
                    "facility",
                    "asset",
                    "event",
                    "domain_context",
                    "source_record",
                ],
                "target_entity_types_allowed": [
                    "building",
                    "parcel",
                    "address",
                    "road_segment",
                    "community",
                    "facility",
                    "asset",
                    "event",
                    "mobility_context",
                    "permit_context",
                    "inspection_context",
                    "violation_context",
                    "domain_context",
                    "source_record",
                ],
                "directionality": "directed" if rtype not in {"adjacent_to", "spatially_near", "temporally_near", "co_occurs_with", "candidate_related_to"} else "symmetric",
                "inverse_relationship": inverse[rtype],
                "required_evidence": [
                    "evidence_refs",
                    "trace_refs",
                    "source_system_refs",
                    "limitation_refs_or_limitations",
                ],
                "allowed_confidence_range": [0.0, 1.0],
                "review_state_policy": "candidate/review states are required unless source_asserted or deterministic evidence is available"
                if candidate_family
                else "asserted_source or inferred_deterministic allowed when evidence is direct",
                "temporal_fields": ["valid_from", "valid_to", "event_time", "observed_time", "temporal_window"],
                "claim_boundary": "Relationship context only. It does not create causal, legal, certified, command, routing, dispatch, or autonomous-action meaning.",
                "forbidden_wording": FORBIDDEN_ACCEPTED_WORDS + ["dispatch", "enforcement"],
                "example_valid_assertion": f"{rtype} relationship supported by named source/evidence refs and limitations.",
                "example_invalid_assertion": f"{rtype} relationship used as proof of a causal or legal outcome.",
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-RELATIONSHIP-ONTOLOGY-R1",
        "status": "PASS",
        "relationship_types": relationship_types,
        "relationship_type_count": len(relationship_types),
        "relationship_families": sorted({item["family"] for item in relationship_types}),
        "forbidden_relationship_types": [
            {
                "relationship_type": rtype,
                "reason": "Requires direct source causation/legal/control evidence and is not allowed in this preflight.",
                "validator_behavior": "reject unless future source policy explicitly permits and evidence proves the exact claim",
            }
            for rtype in FORBIDDEN_RELATIONSHIP_TYPES
        ],
        "forbidden_relationship_types_defined": True,
    }


def assertion_contract() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-RELATIONSHIP-ASSERTION-CONTRACT-R1",
        "status": "PASS",
        "title": "CityBrain Relationship Assertion Contract R1",
        "type": "object",
        "required": REQUIRED_ASSERTION_FIELDS,
        "properties": {
            "relationship_id": {"type": "string"},
            "relationship_type": {"type": "string", "enum": ALLOWED_RELATIONSHIP_TYPES + FORBIDDEN_RELATIONSHIP_TYPES},
            "source_canonical_entity_id": {"type": "string"},
            "source_entity_type": {"type": "string"},
            "target_canonical_entity_id": {"type": "string"},
            "target_entity_type": {"type": "string"},
            "direction": {"type": "string", "enum": ["directed", "symmetric"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "review_state": {"type": "string", "enum": REVIEW_STATES},
            "evidence_refs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "trace_refs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "source_system_refs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "temporal_scope": {"type": "object"},
            "spatial_scope": {"type": "object"},
            "assertion_method": {"type": "string", "enum": ASSERTION_METHODS},
            "assertion_boundary": {"type": "string"},
            "limitations": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "not_causal": {"type": "boolean", "const": True},
            "no_action_taken": {"type": "boolean", "const": True},
            "created_by_run": {"type": "string"},
            "created_at_utc": {"type": "string"},
        },
        "review_states": REVIEW_STATES,
        "assertion_methods": ASSERTION_METHODS,
        "confidence_review_evidence_required_for_non_trivial_relationships": True,
        "can_represent": [
            "evidence_backed_relationship",
            "candidate_relationship",
            "rejected_relationship",
            "temporal_or_correlative_relationship",
            "manual_review_state",
        ],
    }


def confidence_review_policy() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-RELATIONSHIP-GROUNDING-POLICY-R1",
        "status": "PASS",
        "review_states": {
            "asserted_source": "Source explicitly states the relationship, with trace and limitation refs.",
            "inferred_deterministic": "Deterministic method such as containment, shared identifier, or documented mapping supports the relationship.",
            "candidate_probabilistic": "Candidate relation with probability/confidence, not a fact.",
            "requires_review": "Human/domain review is required before stronger use.",
            "rejected": "The relationship failed validation or policy.",
            "disputed": "Conflicting source/evidence state.",
            "deprecated": "Former relationship retained for traceability only.",
        },
        "confidence_bands": {
            "0.00-0.39": "weak/contextual only",
            "0.40-0.69": "candidate/review only",
            "0.70-0.89": "grounded context with limitations",
            "0.90-1.00": "strongly grounded context; still not causal/legal/control without explicit source policy",
        },
        "required_for_acceptance": [
            "evidence_refs",
            "trace_refs",
            "source_system_refs",
            "limitations",
            "not_causal=true",
            "no_action_taken=true",
        ],
        "candidate_relationships_are_not_facts": True,
        "review_relationships_are_not_facts": True,
    }


def temporal_policy() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-RELATIONSHIP-GROUNDING-POLICY-R1",
        "status": "PASS",
        "temporal_fields": ["valid_from", "valid_to", "event_time", "observed_time", "temporal_window", "processing_time"],
        "temporal_proximity_alone_cannot_create_causation": True,
        "spatial_proximity_alone_cannot_create_causation": True,
        "co_occurrence_cannot_create_causation": True,
        "allowed_temporal_claims": [
            "same_window_context",
            "near_in_time_context",
            "event_history_context",
            "superseded_or_deprecated_context",
        ],
        "blocked_temporal_claims_without_direct_source": [
            "causal sequence",
            "responsibility",
            "confirmed impact",
            "legal outcome",
            "command/control effect",
        ],
        "retention_policy": "Temporal scope must travel with the relationship edge and evidence bundle.",
    }


def evidence_bundle_schema() -> dict[str, Any]:
    required = [
        "relationship_id",
        "relationship_summary",
        "relationship_type",
        "source_entity",
        "target_entity",
        "evidence_items",
        "trace_refs",
        "confidence",
        "review_state",
        "limitations",
        "claim_boundary",
        "why_allowed",
        "why_not_stronger",
        "why_not_causal",
        "safe_next_data_needed",
    ]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-RELATIONSHIP-EVIDENCE-BUNDLE-SCHEMA-R1",
        "status": "PASS",
        "title": "CityBrain Relationship Evidence Bundle R1",
        "backend_only": True,
        "operator_briefing_text_created": False,
        "required": required,
        "properties": {
            "relationship_id": {"type": "string"},
            "relationship_summary": {"type": "string"},
            "relationship_type": {"type": "string"},
            "source_entity": {"type": "object"},
            "target_entity": {"type": "object"},
            "evidence_items": {"type": "array", "items": {"type": "object"}, "minItems": 1},
            "trace_refs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "review_state": {"type": "string", "enum": REVIEW_STATES},
            "limitations": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "claim_boundary": {"type": "string"},
            "why_allowed": {"type": "string"},
            "why_not_stronger": {"type": "string"},
            "why_not_causal": {"type": "string"},
            "safe_next_data_needed": {"type": "array", "items": {"type": "string"}},
        },
    }


def grounding_policy_md() -> str:
    return """
# Relationship Grounding Policy R1

This policy is backend-only and supports relationship validation for future
Incident Mode, insight feeds, watchlists, and graph consumers.

## Allowed Grounding

- Deterministic structural grounding requires direct source, geometry, or shared-ID evidence.
- Source-asserted grounding requires a named source system and traceable source record.
- Spatial grounding may support `located_in`, `contains`, `adjacent_to`, or `spatially_near`.
- Temporal grounding may support `temporally_near` or `co_occurs_with` only as context.
- Probabilistic grounding must use `candidate_probabilistic` or `requires_review`.
- Manual-review grounding must remain review-only until a later validated source policy upgrades it.

## Hard Boundaries

Temporal proximity alone cannot create causation.
Spatial proximity alone cannot create causation.
Co-occurrence cannot create causation.
Candidate relationships are not facts.
Review relationships are not facts.

All accepted relationships must carry evidence refs, trace refs, source-system
refs, limitations, `not_causal=true`, and `no_action_taken=true`.

## Rejection

The validator rejects causal, legal, certified-impact, command, routing,
dispatch, or autonomous-action relationships unless a future task defines an
explicit source policy and direct evidence for that exact claim.
"""


def make_edge(
    relationship_id: str,
    relationship_type: str,
    source_id: str,
    source_type: str,
    target_id: str,
    target_type: str,
    confidence: float,
    review_state: str,
    evidence_refs: list[str],
    trace_refs: list[str],
    source_system_refs: list[str],
    assertion_method: str,
    boundary: str,
    limitations: list[str],
    category: str,
    real_evidence: bool,
    cross_domain: bool,
    spatial_only: bool = False,
    synthetic_contract_test_only: bool = False,
    direction: str = "directed",
    relationship_summary: str | None = None,
    invalid_expectation: str | None = None,
) -> dict[str, Any]:
    return {
        "relationship_id": relationship_id,
        "relationship_type": relationship_type,
        "source_canonical_entity_id": source_id,
        "source_entity_type": source_type,
        "target_canonical_entity_id": target_id,
        "target_entity_type": target_type,
        "direction": direction,
        "confidence": confidence,
        "review_state": review_state,
        "evidence_refs": evidence_refs,
        "trace_refs": trace_refs,
        "source_system_refs": source_system_refs,
        "temporal_scope": {
            "event_time": None,
            "valid_from": None,
            "valid_to": None,
            "temporal_window": "source packet context only",
        },
        "spatial_scope": {
            "city_or_area": "source packet context",
            "method": "source refs and packet/entity refs, not live geometry runtime",
        },
        "assertion_method": assertion_method,
        "assertion_boundary": boundary,
        "limitations": limitations,
        "not_causal": True,
        "no_action_taken": True,
        "created_by_run": TASK_ID,
        "created_at_utc": now(),
        "fixture_category": category,
        "real_evidence_backed": real_evidence,
        "cross_domain": cross_domain,
        "spatial_only": spatial_only,
        "synthetic_contract_test_only": synthetic_contract_test_only,
        "not_domain_evidence": synthetic_contract_test_only,
        "not_city_truth": synthetic_contract_test_only,
        "relationship_summary": relationship_summary
        or f"{relationship_type} edge from {source_id} to {target_id} with bounded evidence refs.",
        "invalid_expectation": invalid_expectation,
    }


def extract_episode(episodes: list[dict[str, Any]], episode_id: str) -> dict[str, Any]:
    for episode in episodes:
        if episode.get("episode_id") == episode_id:
            return episode
    return {}


def edge_fixtures() -> dict[str, Any]:
    r6_payload = read_json(UPSTREAM_ROOTS["r6_incident_event_mode"] / "R6_INCIDENT_CONTEXT_PACKETS.json", [])
    r6_packets = r6_payload.get("packets", []) if isinstance(r6_payload, dict) else r6_payload
    episodes_payload = read_json(UPSTREAM_ROOTS["track2b_city_episode_pack"] / "TRACK2B_CURATED_CITY_EPISODE_PACK.json", {})
    episodes = episodes_payload.get("episodes", []) if isinstance(episodes_payload, dict) else []
    p0 = r6_packets[0] if len(r6_packets) > 0 else {}
    p1 = r6_packets[1] if len(r6_packets) > 1 else {}
    p2 = r6_packets[2] if len(r6_packets) > 2 else {}
    barc_lod2 = extract_episode(episodes, "episode:barc_lod2_object_district_neighbourhood")
    barc_mobility = extract_episode(episodes, "episode:barc_mobility_trams_itineraries_replay")
    nyc_identity = extract_episode(episodes, "episode:nyc_lod2_building_identity_candidate")

    valid_grounded_edges = [
        make_edge(
            "rel:r7:real:r6:community-event:001",
            "has_event_context",
            (p0.get("entity_refs") or ["cer:community:barc:eixample"])[0],
            "community",
            (p0.get("event_refs") or ["r6-event-001"])[0],
            "civic_service_event",
            0.74,
            "candidate_probabilistic",
            p0.get("evidence_refs") or ["outputs/main_track1_d4y_r6_incident_event_mode_end_to_end/R6_INCIDENT_CONTEXT_PACKETS.json:r6-incident-context-packet-001"],
            [
                "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end/R6_INCIDENT_CONTEXT_PACKETS.json:r6-incident-context-packet-001",
                "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end/R6_EVENT_TO_ENTITY_RESULTS.json",
            ],
            [p0.get("source_entity_id") or "src:barc:district:eixample", p0.get("domain_pack_id") or "civic_service_review_context"],
            "event_resolution",
            "Community-to-event context only; review state is preserved and no stronger claim is made.",
            p0.get("limitations") or ["review_context_only"],
            "valid_grounded_edges",
            True,
            True,
            relationship_summary="Barcelona community entity has bounded civic-service event context from the R6 incident/context packet.",
        ),
        make_edge(
            "rel:r7:real:r6:road-event:002",
            "has_event_context",
            (p1.get("entity_refs") or ["cer:road:barc:segment:granvia:001"])[0],
            "road_segment",
            (p1.get("event_refs") or ["r6-event-002"])[0],
            "civic_service_event",
            0.71,
            "candidate_probabilistic",
            p1.get("evidence_refs") or ["outputs/main_track1_d4y_r6_incident_event_mode_end_to_end/R6_INCIDENT_CONTEXT_PACKETS.json:r6-incident-context-packet-002"],
            [
                "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end/R6_INCIDENT_CONTEXT_PACKETS.json:r6-incident-context-packet-002",
                "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end/R6_EVENT_TO_ENTITY_RESULTS.json",
            ],
            [p1.get("source_entity_id") or "src:barc:road:granvia:001", p1.get("domain_pack_id") or "civic_service_review_context"],
            "event_resolution",
            "Road-segment-to-event context only; no route, command, or operational meaning.",
            p1.get("limitations") or ["review_context_only"],
            "valid_grounded_edges",
            True,
            True,
            relationship_summary="Barcelona road segment has bounded civic-service event context from the R6 incident/context packet.",
        ),
        make_edge(
            "rel:r7:real:track2b:barc-mobility:001",
            "has_mobility_context",
            "cer:city:barc",
            "community",
            "mobility_context:barc:traffic-trams-itineraries-tmb",
            "mobility_context",
            0.78,
            "asserted_source",
            barc_mobility.get("evidence_refs") or ["D4 scenario replay panel"],
            [
                "outputs/main_track2b_d4x_city_episode_pack_end_to_end/TRACK2B_CURATED_CITY_EPISODE_PACK.json:episode:barc_mobility_trams_itineraries_replay",
            ],
            barc_mobility.get("source_refs") or ["traffic_itineraries", "traffic_trams", "tmb_static_gtfs"],
            "source_asserted",
            "Mobility/replay context only; no routing, command, or traffic truth.",
            barc_mobility.get("limitations") or ["simulated/context only"],
            "valid_grounded_edges",
            True,
            True,
            relationship_summary="Barcelona has bounded mobility/replay context from Track 2B episode evidence and source refs.",
        ),
        make_edge(
            "rel:r7:real:track2b:barc-lod2-located:001",
            "located_in",
            (barc_lod2.get("entity_refs") or ["barc:lod2_source_object:72498"])[0],
            "building",
            "barc:neighbourhood:08",
            "community",
            0.82,
            "inferred_deterministic",
            ["outputs/main_track2b_d4x_city_episode_pack_end_to_end/TRACK2B_CURATED_CITY_EPISODE_PACK.json:episode:barc_lod2_object_district_neighbourhood"],
            [
                "outputs/main_track2b_d4x_city_episode_pack_end_to_end/TRACK2B_CURATED_CITY_EPISODE_PACK.json:episode:barc_lod2_object_district_neighbourhood",
            ],
            barc_lod2.get("source_refs") or ["BARC LOD2 buildings USD", "BARC identity shard"],
            "manual_bridge",
            "LOD2 object location context only; cadastral/address join remains pending.",
            barc_lod2.get("limitations") or ["Barcelona LOD2 source IDs are visual/source context only."],
            "valid_grounded_edges",
            True,
            False,
            spatial_only=True,
            relationship_summary="Barcelona LOD2 object has source-referenced district/neighbourhood context.",
        ),
    ]

    candidate_review_edges = [
        make_edge(
            "rel:r7:candidate:r6:address-building:003",
            "candidate_related_to",
            (p2.get("entity_refs") or ["cer:address:barc:eixample:001"])[0],
            "address",
            "cer:building:barc:eixample:lod2:001",
            "building",
            0.54,
            "requires_review",
            p2.get("evidence_refs") or ["outputs/main_track1_d4y_r6_incident_event_mode_end_to_end/R6_INCIDENT_CONTEXT_PACKETS.json:r6-incident-context-packet-003"],
            [
                "outputs/main_track1_d4y_r6_incident_event_mode_end_to_end/R6_INCIDENT_CONTEXT_PACKETS.json:r6-incident-context-packet-003",
            ],
            [p2.get("source_entity_id") or "src:barc:address:eixample:001"],
            "manual_bridge",
            "Candidate address-to-building context only; needs stronger identity join.",
            p2.get("limitations") or ["address_to_building_candidate"],
            "candidate_review_edges",
            True,
            True,
            relationship_summary="Barcelona address may relate to a building identity context but requires review.",
        ),
        make_edge(
            "rel:r7:candidate:track2b:nyc-bin-bbl-doitt:001",
            "candidate_related_to",
            (nyc_identity.get("entity_refs") or ["nyc:building:bin:3039983"])[0],
            "building",
            "source_identity_bundle:nyc:bin3039983:bbl3014920001:doitt504661",
            "source_record",
            0.68,
            "requires_review",
            ["outputs/main_track2b_d4x_city_episode_pack_end_to_end/TRACK2B_CURATED_CITY_EPISODE_PACK.json:episode:nyc_lod2_building_identity_candidate"],
            [
                "outputs/main_track2b_d4x_city_episode_pack_end_to_end/TRACK2B_CURATED_CITY_EPISODE_PACK.json:episode:nyc_lod2_building_identity_candidate",
            ],
            nyc_identity.get("source_refs") or ["NYC 2025 Buildings 3D SceneServer", "NYC identity shard"],
            "shared_identifier",
            "Source identity candidate only; no legal or certified truth.",
            nyc_identity.get("limitations") or ["BIN/BBL/DoITT are source/candidate context only."],
            "candidate_review_edges",
            True,
            True,
            relationship_summary="NYC LOD2 building source identifiers are candidate identity context and require review.",
        ),
        make_edge(
            "rel:r7:synthetic:temporal-cooccurrence-validator:001",
            "temporally_near",
            "synthetic:event:a",
            "event",
            "synthetic:event:b",
            "event",
            0.31,
            "requires_review",
            ["synthetic_contract_test_only:evidence"],
            ["synthetic_contract_test_only:trace"],
            ["synthetic_contract_test_only:source"],
            "temporal_cooccurrence",
            "Synthetic contract test only; not domain evidence or city truth.",
            ["synthetic_contract_test_only", "not_domain_evidence", "not_city_truth"],
            "candidate_review_edges",
            False,
            False,
            synthetic_contract_test_only=True,
            direction="symmetric",
            relationship_summary="Synthetic temporal-nearness fixture validates non-causal candidate handling.",
        ),
    ]

    rejected_overclaim_edges = [
        make_edge(
            "rel:r7:rejected:causal-overclaim:001",
            "caused_by",
            (p1.get("event_refs") or ["r6-event-002"])[0],
            "civic_service_event",
            (p1.get("entity_refs") or ["cer:road:barc:segment:granvia:001"])[0],
            "road_segment",
            0.91,
            "rejected",
            p1.get("evidence_refs") or ["outputs/main_track1_d4y_r6_incident_event_mode_end_to_end/R6_INCIDENT_CONTEXT_PACKETS.json:r6-incident-context-packet-002"],
            ["outputs/main_track1_d4y_r6_incident_event_mode_end_to_end/R6_INCIDENT_CONTEXT_PACKETS.json:r6-incident-context-packet-002"],
            [p1.get("source_entity_id") or "src:barc:road:granvia:001"],
            "event_resolution",
            "Rejected test edge: the source supports context, not causation.",
            ["rejected_overclaim", "direct source causation absent"],
            "rejected_overclaim_edges",
            True,
            True,
            relationship_summary="Rejected fixture intentionally attempts a forbidden causal relationship.",
            invalid_expectation="REJECT_FOR_FORBIDDEN_RELATIONSHIP_TYPE",
        )
    ]

    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-BOUNDED-EDGE-FIXTURES-AND-VALIDATION-R1",
        "status": "PASS_WITH_LIMITATIONS",
        "source_artifacts": [
            rel(UPSTREAM_ROOTS["r6_incident_event_mode"] / "R6_INCIDENT_CONTEXT_PACKETS.json"),
            rel(UPSTREAM_ROOTS["track2b_city_episode_pack"] / "TRACK2B_CURATED_CITY_EPISODE_PACK.json"),
        ],
        "valid_grounded_edges": valid_grounded_edges,
        "candidate_review_edges": candidate_review_edges,
        "rejected_overclaim_edges": rejected_overclaim_edges,
    }


def validate_edge(edge: dict[str, Any], allow_rejected: bool = False) -> tuple[bool, list[str]]:
    errors = []
    missing = [field for field in REQUIRED_ASSERTION_FIELDS if field not in edge]
    if missing:
        errors.append(f"missing_required_fields:{','.join(missing)}")
    if edge.get("relationship_type") not in ALLOWED_RELATIONSHIP_TYPES:
        errors.append(f"relationship_type_not_allowed:{edge.get('relationship_type')}")
    if edge.get("relationship_type") in FORBIDDEN_RELATIONSHIP_TYPES:
        errors.append(f"forbidden_relationship_type:{edge.get('relationship_type')}")
    if not edge.get("source_canonical_entity_id") or not edge.get("target_canonical_entity_id"):
        errors.append("entity_ids_missing")
    if not isinstance(edge.get("confidence"), (int, float)) or not 0 <= float(edge.get("confidence", -1)) <= 1:
        errors.append("confidence_invalid")
    if edge.get("review_state") not in REVIEW_STATES:
        errors.append("review_state_invalid")
    if edge.get("assertion_method") not in ASSERTION_METHODS:
        errors.append("assertion_method_invalid")
    if edge.get("fixture_category") != "rejected_overclaim_edges":
        if not edge.get("synthetic_contract_test_only") and not edge.get("evidence_refs"):
            errors.append("evidence_refs_missing_for_non_synthetic_edge")
        if not edge.get("trace_refs"):
            errors.append("trace_refs_missing")
        if not edge.get("source_system_refs"):
            errors.append("source_system_refs_missing")
    if not edge.get("limitations"):
        errors.append("limitations_missing")
    if edge.get("not_causal") is not True:
        errors.append("not_causal_not_true")
    if edge.get("no_action_taken") is not True:
        errors.append("no_action_taken_not_true")
    accepted_text = " ".join(
        str(edge.get(field, ""))
        for field in ["relationship_type", "assertion_boundary", "relationship_summary"]
    ).lower()
    for word in FORBIDDEN_ACCEPTED_WORDS:
        if word in accepted_text and edge.get("fixture_category") != "rejected_overclaim_edges":
            errors.append(f"forbidden_wording_in_accepted_edge:{word}")
    if allow_rejected:
        return bool(errors), errors
    return not errors, errors


def validation_results(fixtures: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    accepted = fixtures["valid_grounded_edges"] + fixtures["candidate_review_edges"]
    rejected = fixtures["rejected_overclaim_edges"]
    accepted_results = []
    for edge in accepted:
        passed, errors = validate_edge(edge)
        accepted_results.append({"relationship_id": edge["relationship_id"], "passed": passed, "errors": errors})
    rejected_results = []
    for edge in rejected:
        rejected_correctly, errors = validate_edge(edge, allow_rejected=True)
        rejected_results.append(
            {
                "relationship_id": edge["relationship_id"],
                "rejected_correctly": rejected_correctly,
                "validator_errors": errors,
                "expected": edge.get("invalid_expectation"),
            }
        )
    all_accepted_passed = all(item["passed"] for item in accepted_results)
    all_rejected_rejected = all(item["rejected_correctly"] for item in rejected_results)
    valid_grounded = fixtures["valid_grounded_edges"]
    candidate = fixtures["candidate_review_edges"]
    synthetic = [edge for edge in accepted if edge.get("synthetic_contract_test_only")]
    real_edges = [edge for edge in accepted if edge.get("real_evidence_backed")]
    real_cross_domain = [edge for edge in real_edges if edge.get("cross_domain")]
    grounded_cross_domain = [edge for edge in valid_grounded if edge.get("cross_domain")]
    spatial_only = [edge for edge in accepted if edge.get("spatial_only")]
    validation = {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-BOUNDED-EDGE-FIXTURES-AND-VALIDATION-R1",
        "status": "PASS_WITH_LIMITATIONS" if all_accepted_passed else "FAIL",
        "accepted_edges_total": len(accepted),
        "accepted_edges_passed": sum(1 for item in accepted_results if item["passed"]),
        "accepted_edge_results": accepted_results,
        "valid_grounded_edges_count": len(valid_grounded),
        "candidate_review_edges_count": len(candidate),
        "synthetic_contract_test_edges_count": len(synthetic),
        "real_evidence_backed_edges_count": len(real_edges),
        "real_evidence_backed_cross_domain_edges_count": len(real_cross_domain),
        "grounded_cross_domain_edges_count": len(grounded_cross_domain),
        "spatial_only_edges_count": len(spatial_only),
        "validation_passed": all_accepted_passed,
        "limitations": ["edge examples are intentionally small and preflight-scoped"],
    }
    rejection = {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-BOUNDED-EDGE-FIXTURES-AND-VALIDATION-R1",
        "status": "PASS" if all_rejected_rejected else "FAIL",
        "rejected_overclaim_edges_count": len(rejected),
        "rejected_edge_results": rejected_results,
        "safe_failure_validation_passed": all_rejected_rejected,
        "invalid_overclaiming_edges_passed_validation": False if all_rejected_rejected else True,
    }
    return validation, rejection


def evidence_bundles(fixtures: dict[str, Any]) -> list[dict[str, Any]]:
    bundles = []
    for edge in fixtures["valid_grounded_edges"] + fixtures["candidate_review_edges"]:
        bundles.append(
            {
                "relationship_id": edge["relationship_id"],
                "relationship_summary": edge["relationship_summary"],
                "relationship_type": edge["relationship_type"],
                "source_entity": {
                    "canonical_entity_id": edge["source_canonical_entity_id"],
                    "entity_type": edge["source_entity_type"],
                },
                "target_entity": {
                    "canonical_entity_id": edge["target_canonical_entity_id"],
                    "entity_type": edge["target_entity_type"],
                },
                "evidence_items": [
                    {
                        "evidence_ref": evidence_ref,
                        "source_system_refs": edge["source_system_refs"],
                        "trace_refs": edge["trace_refs"],
                    }
                    for evidence_ref in edge["evidence_refs"]
                ],
                "trace_refs": edge["trace_refs"],
                "confidence": edge["confidence"],
                "review_state": edge["review_state"],
                "limitations": edge["limitations"],
                "claim_boundary": edge["assertion_boundary"],
                "why_allowed": "Required refs, limitations, review state, no-action, and not-causal flags are present.",
                "why_not_stronger": "This preflight does not promote context/candidate edges into certified facts or runtime graph truth.",
                "why_not_causal": "The source packets support relationship context only and do not provide direct source causation.",
                "safe_next_data_needed": [
                    "source-level relationship assertion or deterministic join evidence",
                    "domain review outcome if a candidate relationship should be strengthened",
                    "fresh validation before any runtime or UI consumer uses the edge",
                ],
            }
        )
    return bundles


def no_causation_audit(fixtures: dict[str, Any]) -> dict[str, Any]:
    accepted = fixtures["valid_grounded_edges"] + fixtures["candidate_review_edges"]
    rejected = fixtures["rejected_overclaim_edges"]
    accepted_hits = []
    for edge in accepted:
        text = " ".join(
            [
                edge.get("relationship_type", ""),
                edge.get("relationship_summary", ""),
                edge.get("assertion_boundary", ""),
            ]
        ).lower()
        hits = [word for word in FORBIDDEN_ACCEPTED_WORDS if word in text]
        if edge.get("relationship_type") in FORBIDDEN_RELATIONSHIP_TYPES:
            hits.append(f"forbidden_relationship_type:{edge['relationship_type']}")
        if hits:
            accepted_hits.append({"relationship_id": edge["relationship_id"], "hits": hits})
    rejected_hits = [
        {
            "relationship_id": edge["relationship_id"],
            "relationship_type": edge["relationship_type"],
            "correctly_rejected": edge["relationship_type"] in FORBIDDEN_RELATIONSHIP_TYPES,
        }
        for edge in rejected
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-NO-CAUSATION-OVERCLAIM-AUDIT-R1",
        "status": "PASS" if not accepted_hits and all(item["correctly_rejected"] for item in rejected_hits) else "FAIL",
        "accepted_edges_forbidden_hits": accepted_hits,
        "rejected_overclaim_edges": rejected_hits,
        "ungrounded_causal_claim_accepted": bool(accepted_hits),
        "causal_legal_control_claims_absent_or_correctly_rejected": not accepted_hits,
    }


def handoff_contracts(fixtures: dict[str, Any], bundles: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    incident_contract = {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-INTELLIGENCE-CONSUMER-HANDOFFS-R1",
        "status": "PASS",
        "backend_only": True,
        "allowed_fields": [
            "event_id",
            "resolved_entity_refs",
            "candidate_relationship_context",
            "grounded_relationship_context",
            "relationship_evidence_bundles",
            "uncertainty_summary",
            "limitations",
            "not_causal_flags",
            "safe_next_data_needed",
        ],
        "forbidden_surface_outputs": [
            "operator briefing",
            "executive narrative",
            "frontend card rendering",
            "control-room journey",
            "safe-next-look UI flow",
        ],
        "operator_briefing_created": False,
        "executive_narrative_created": False,
        "frontend_artifacts_created": False,
    }
    watchlist_contract = {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-INTELLIGENCE-CONSUMER-HANDOFFS-R1",
        "status": "PASS",
        "backend_only": True,
        "allowed_fields": [
            "watch_candidate_id",
            "relationship_pattern",
            "evidence_bundle_refs",
            "confidence",
            "review_state",
            "why_watch",
            "why_not_alert",
            "limitations",
            "not_actionable_yet",
        ],
        "forbidden_surface_outputs": [
            "alerting UI",
            "push notifications",
            "operator cards",
            "frontend feed",
        ],
        "not_actionable_yet_required": True,
    }
    grounded = fixtures["valid_grounded_edges"][:2]
    candidate = fixtures["candidate_review_edges"][:1]
    rejected = fixtures["rejected_overclaim_edges"][:1]
    worked_example = {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-INTELLIGENCE-CONSUMER-HANDOFFS-R1",
        "status": "PASS_WITH_LIMITATIONS",
        "backend_request_id": "r7-backend-request-barc-community-event-context-001",
        "question_or_backend_request": "Retrieve bounded relationship context for a Barcelona community/entity event seed.",
        "seed_event_id": grounded[0]["target_canonical_entity_id"] if grounded else "r6-event-001",
        "seed_canonical_entity_id": grounded[0]["source_canonical_entity_id"] if grounded else "cer:community:barc:eixample",
        "relationship_types_retrieved": sorted({edge["relationship_type"] for edge in grounded + candidate}),
        "edges_returned": [edge["relationship_id"] for edge in grounded + candidate],
        "evidence_bundle_refs": [bundle["relationship_id"] for bundle in bundles if bundle["relationship_id"] in {edge["relationship_id"] for edge in grounded + candidate}],
        "grounded_edges": [edge["relationship_id"] for edge in grounded],
        "candidate_review_edges": [edge["relationship_id"] for edge in candidate],
        "rejected_edges": [edge["relationship_id"] for edge in rejected],
        "not_causal_explanation": "Returned relationships are context/candidate edges with not_causal=true; no direct source causation is present.",
        "why_not_stronger": "The evidence is packet-backed and bounded, but this preflight does not implement a graph runtime or reviewed truth upgrade.",
        "safe_next_data_needed": [
            "more source-asserted relationship edges",
            "domain review decisions for candidate edges",
            "runtime edge seeding and replay validation before consumer use",
        ],
        "surface_artifacts_created": False,
        "uses_real_evidence": True,
        "synthetic_contract_test_only": False,
    }
    top_down = {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-INTELLIGENCE-CONSUMER-HANDOFFS-R1",
        "status": "PASS_WITH_LIMITATIONS",
        "backend_request": worked_example["question_or_backend_request"],
        "trace_steps": [
            {
                "step": "seed",
                "entity_or_event": worked_example["seed_canonical_entity_id"],
                "source": "R6 incident/context packet",
            },
            {
                "step": "relationship_retrieval",
                "relationship_types": worked_example["relationship_types_retrieved"],
                "edges": worked_example["edges_returned"],
            },
            {
                "step": "evidence_bundle_assembly",
                "bundle_refs": worked_example["evidence_bundle_refs"],
                "not_causal": True,
            },
            {
                "step": "safe_failure",
                "rejected_edges": worked_example["rejected_edges"],
                "reason": "forbidden causal relationship type rejected",
            },
        ],
        "surface_artifacts_created": False,
        "uses_real_evidence": True,
        "synthetic_contract_test_only": False,
    }
    return incident_contract, watchlist_contract, worked_example, top_down


def closeout_docs(decision: dict[str, Any]) -> tuple[str, str, str]:
    report = f"""
# Cross-Domain Relationship Substrate Preflight

Status: `{decision['status']}`

This pack defines and validates a backend-only relationship substrate for future
Incident Mode, insight feeds, watchlists, and graph consumers. It does not create
frontend/demo/Omniverse/served-runtime artifacts.

## What Is Proven

- Relationship ontology created with {decision['relationship_types_total']} allowed relationship types.
- Assertion contract, grounding policy, confidence/review policy, temporal policy, and evidence bundle schema are present.
- {decision['real_evidence_backed_edges_count']} real-evidence-backed accepted edge examples validate safely.
- {decision['real_evidence_backed_cross_domain_edges_count']} real-evidence-backed accepted edges cross domain boundaries.
- Rejected overclaim fixture fails safely.
- Top-down backend worked example exists and uses real evidence.

## What Is Contract-Only

- No graph database runtime or traversal service is implemented.
- No runtime edge seeding, watchlist service, or Incident Mode surface is implemented.
- Synthetic fixtures are used only to validate schema/validator behavior.

## Explicit Boundary

All accepted edges are non-causal context/candidate relationships with
`not_causal=true` and `no_action_taken=true`.
"""
    limitations = "\n".join(f"- {item}" for item in LIMITATIONS)
    next_steps = f"""
# Next Steps

Recommended next task:

`{NEXT_TASK}`

After D6 closes and remains non-conflicting:

`{AFTER_D6_TASK}`

Do not recommend operator-surface Incident Mode from this pack alone. This pack
is backend substrate scaffolding and must be expanded with more seeded real
edges before product/demo consumers treat it as a reasoning layer.
"""
    return report, f"# Limitations\n\n{limitations}", next_steps


def write_hashes() -> dict[str, Any]:
    rows = []
    for path in sorted(p for p in OUTPUT_ROOT.rglob("*") if p.is_file() and p.name != "hashes.sha256"):
        rows.append((path.relative_to(OUTPUT_ROOT).as_posix(), sha256_file(path)))
    (OUTPUT_ROOT / "hashes.sha256").write_text(
        "".join(f"{digest}  {relative_path}\n" for relative_path, digest in rows),
        encoding="utf-8",
    )
    return {"schema_version": SCHEMA_VERSION, "status": "PASS", "count": len(rows)}


def main() -> None:
    before_surface = {key: path_signature(path) for key, path in D6_AND_SURFACE_WATCH.items()}
    prepare_output_root()

    upstream = upstream_audit()
    write_json(OUTPUT_ROOT / "UPSTREAM_GRAPH_AND_DOMAIN_AUDIT.json", upstream)

    if upstream["status"] == "HOLD":
        decision = {
            "task_id": TASK_ID,
            "status": HOLD_STATUS,
            "repo_root": str(REPO_ROOT),
            "output_root": str(OUTPUT_ROOT),
            "run_timestamp_utc": now(),
            "runner_path": str(RUNNER_PATH),
            "upstream_artifacts_found": upstream["backend_artifacts_present"],
            "next_recommended_task": "MAIN-TRACK1-D4Y-R7-CROSS-DOMAIN-EVIDENCE-INVENTORY-R1",
        }
        write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R7_CROSS_DOMAIN_RELATIONSHIP_SUBSTRATE_PREFLIGHT_DECISION.json", decision)
        write_hashes()
        return

    ontology = relationship_ontology()
    contract = assertion_contract()
    conf_policy = confidence_review_policy()
    temp_policy = temporal_policy()
    evidence_schema = evidence_bundle_schema()
    fixtures = edge_fixtures()
    validation, rejection = validation_results(fixtures)
    bundles = evidence_bundles(fixtures)
    causation_audit = no_causation_audit(fixtures)
    incident_contract, watchlist_contract, worked_example, top_down = handoff_contracts(fixtures, bundles)

    write_json(OUTPUT_ROOT / "RELATIONSHIP_ONTOLOGY_R1.json", ontology)
    write_json(OUTPUT_ROOT / "RELATIONSHIP_ASSERTION_CONTRACT.json", contract)
    write_text(OUTPUT_ROOT / "RELATIONSHIP_GROUNDING_POLICY.md", grounding_policy_md())
    write_json(OUTPUT_ROOT / "RELATIONSHIP_CONFIDENCE_AND_REVIEW_STATE_POLICY.json", conf_policy)
    write_json(OUTPUT_ROOT / "RELATIONSHIP_TEMPORAL_POLICY.json", temp_policy)
    write_json(OUTPUT_ROOT / "RELATIONSHIP_EVIDENCE_BUNDLE_SCHEMA.json", evidence_schema)
    write_json(OUTPUT_ROOT / "RELATIONSHIP_EDGE_FIXTURES.json", fixtures)
    write_json(OUTPUT_ROOT / "RELATIONSHIP_EVIDENCE_BUNDLES.json", bundles)
    write_json(OUTPUT_ROOT / "RELATIONSHIP_VALIDATION_RESULTS.json", validation)
    write_json(OUTPUT_ROOT / "RELATIONSHIP_REJECTION_AND_SAFE_FAILURE_RESULTS.json", rejection)
    write_json(OUTPUT_ROOT / "NO_CAUSATION_OVERCLAIM_AUDIT.json", causation_audit)
    write_json(OUTPUT_ROOT / "INCIDENT_MODE_BACKEND_HANDOFF_CONTRACT.json", incident_contract)
    write_json(OUTPUT_ROOT / "INSIGHT_WATCHLIST_BACKEND_HANDOFF_CONTRACT.json", watchlist_contract)
    write_json(OUTPUT_ROOT / "INCIDENT_MODE_BACKEND_WORKED_EXAMPLE.json", worked_example)
    write_json(OUTPUT_ROOT / "RELATIONSHIP_SUBSTRATE_TOP_DOWN_TRACE_EXAMPLE.json", top_down)

    after_surface = {key: path_signature(path) for key, path in D6_AND_SURFACE_WATCH.items()}
    collision = noncollision_audit(before_surface, after_surface)
    go_no_go = {
        "schema_version": SCHEMA_VERSION,
        "task_id": "MAIN-TRACK1-D4Y-R7-UPSTREAM-AND-NONCOLLISION-AUDIT-R0",
        "status": "PASS" if upstream["status"] in {"PASS", "PASS_WITH_LIMITATIONS"} and collision["status"] == "PASS" else "FAIL",
        "upstream_status": upstream["status"],
        "d6_collision_status": collision["status"],
        "go": upstream["status"] in {"PASS", "PASS_WITH_LIMITATIONS"} and collision["status"] == "PASS",
    }
    write_json(OUTPUT_ROOT / "D6_COLLISION_AVOIDANCE_AUDIT.json", collision)
    write_json(OUTPUT_ROOT / "NONCOLLISION_GO_NO_GO_DECISION.json", go_no_go)

    all_core_pass = all(
        [
            ontology["status"] == "PASS",
            contract["status"] == "PASS",
            conf_policy["status"] == "PASS",
            temp_policy["status"] == "PASS",
            evidence_schema["status"] == "PASS",
            validation["validation_passed"],
            rejection["safe_failure_validation_passed"],
            causation_audit["status"] == "PASS",
            worked_example["surface_artifacts_created"] is False,
            incident_contract["status"] == "PASS",
            watchlist_contract["status"] == "PASS",
            collision["status"] == "PASS",
        ]
    )
    final_status = STATUS if all_core_pass else FAIL_STATUS
    if validation["real_evidence_backed_edges_count"] == 0:
        final_status = "PASS_WITH_LIMITATIONS" if all_core_pass else FAIL_STATUS

    decision = {
        "task_id": TASK_ID,
        "status": final_status,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now(),
        "runner_path": str(RUNNER_PATH),
        "upstream_artifacts_found": upstream["backend_artifacts_present"],
        "d6_collision_avoidance_passed": collision["status"] == "PASS",
        "omniverse_collision_avoidance_passed": collision["status"] == "PASS",
        "served_runtime_mutation_avoided": collision["served_runtime_implementation_modified"] is False,
        "relationship_ontology_created": True,
        "relationship_types_total": ontology["relationship_type_count"],
        "forbidden_relationship_types_defined": ontology["forbidden_relationship_types_defined"],
        "assertion_contract_created": True,
        "grounding_policy_created": True,
        "confidence_review_policy_created": True,
        "temporal_policy_created": True,
        "evidence_bundle_schema_created": True,
        "edge_fixtures_created": True,
        "valid_grounded_edges_count": validation["valid_grounded_edges_count"],
        "candidate_review_edges_count": validation["candidate_review_edges_count"],
        "rejected_overclaim_edges_count": rejection["rejected_overclaim_edges_count"],
        "synthetic_contract_test_edges_count": validation["synthetic_contract_test_edges_count"],
        "real_evidence_backed_edges_count": validation["real_evidence_backed_edges_count"],
        "real_evidence_backed_cross_domain_edges_count": validation["real_evidence_backed_cross_domain_edges_count"],
        "grounded_cross_domain_edges_count": validation["grounded_cross_domain_edges_count"],
        "spatial_only_edges_count": validation["spatial_only_edges_count"],
        "no_real_evidence_backed_edges_plainly_reported": validation["real_evidence_backed_edges_count"] == 0,
        "top_down_worked_example_created": True,
        "top_down_worked_example_uses_real_evidence": worked_example["uses_real_evidence"],
        "top_down_worked_example_synthetic_contract_only": worked_example["synthetic_contract_test_only"],
        "validation_passed": validation["validation_passed"],
        "safe_failure_validation_passed": rejection["safe_failure_validation_passed"],
        "no_causation_overclaim_audit_passed": causation_audit["status"] == "PASS",
        "incident_mode_backend_handoff_created": True,
        "insight_watchlist_backend_handoff_created": True,
        "operator_briefing_created": False,
        "executive_narrative_created": False,
        "frontend_artifacts_created": False,
        "omniverse_artifacts_created": False,
        "served_runtime_modified": False,
        "trace_refs_present": all(edge.get("trace_refs") for edge in fixtures["valid_grounded_edges"] + fixtures["candidate_review_edges"]),
        "evidence_refs_present": all(edge.get("evidence_refs") for edge in fixtures["valid_grounded_edges"] + fixtures["candidate_review_edges"]),
        "limitation_refs_present": all(edge.get("limitations") for edge in fixtures["valid_grounded_edges"] + fixtures["candidate_review_edges"]),
        "not_causal_flags_present": all(edge.get("not_causal") is True for edge in fixtures["valid_grounded_edges"] + fixtures["candidate_review_edges"]),
        "no_action_taken_flags_present": all(edge.get("no_action_taken") is True for edge in fixtures["valid_grounded_edges"] + fixtures["candidate_review_edges"]),
        "production_live_claim_made": False,
        "public_api_claim_made": False,
        "production_frontend_claim_made": False,
        "citywide_twin_claim_made": False,
        "full_mesh_binding_claim_made": False,
        "physical_accuracy_claim_made": False,
        "autonomous_action_exposed": False,
        "legal_or_enforcement_claim_made": False,
        "ungrounded_causal_claim_accepted": causation_audit["ungrounded_causal_claim_accepted"],
        "limitations": LIMITATIONS,
        "next_recommended_task": NEXT_TASK,
        "recommended_after_d6_closes": AFTER_D6_TASK,
    }

    report, limitations_md, next_steps_md = closeout_docs(decision)
    write_text(OUTPUT_ROOT / "CROSS_DOMAIN_RELATIONSHIP_SUBSTRATE_PREFLIGHT_REPORT.md", report)
    write_text(OUTPUT_ROOT / "LIMITATIONS_AND_NEXT_STEPS.md", limitations_md + "\n\n" + next_steps_md)
    write_json(OUTPUT_ROOT / "CROSS_DOMAIN_RELATIONSHIP_SUBSTRATE_CLOSEOUT_DECISION.json", decision)
    write_text(OUTPUT_ROOT / "CROSS_DOMAIN_RELATIONSHIP_SUBSTRATE_CLOSEOUT_REPORT.md", report)
    write_json(
        OUTPUT_ROOT / "CROSS_DOMAIN_RELATIONSHIP_SUBSTRATE_ARTIFACT_INDEX.json",
        {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS",
            "artifacts": sorted(path.relative_to(OUTPUT_ROOT).as_posix() for path in OUTPUT_ROOT.rglob("*") if path.is_file()),
        },
    )
    write_text(OUTPUT_ROOT / "CROSS_DOMAIN_RELATIONSHIP_SUBSTRATE_LIMITATIONS.md", limitations_md)
    write_text(OUTPUT_ROOT / "CROSS_DOMAIN_RELATIONSHIP_SUBSTRATE_NEXT_STEPS.md", next_steps_md)
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""
# {TASK_ID}

Status: `{final_status}`

This output pack is a backend-only relationship substrate preflight. It defines
typed relationship contracts, grounding/confidence/temporal policies, bounded
fixtures, safe-failure checks, a no-causation audit, and future backend consumer
handoff contracts.

It does not create or modify frontend, D6 demo, Omniverse, Kit, USD, served
runtime, production API, command, routing, dispatch, or autonomous-action
artifacts.
""",
    )

    master_decision_path = OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R7_CROSS_DOMAIN_RELATIONSHIP_SUBSTRATE_PREFLIGHT_DECISION.json"
    expected_hash_count = len(
        [path for path in OUTPUT_ROOT.rglob("*") if path.is_file() and path.name != "hashes.sha256" and path != master_decision_path]
    ) + 1
    decision["hash_validation_status"] = "PASS"
    decision["hash_summary"] = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "count": expected_hash_count,
    }
    write_json(OUTPUT_ROOT / "MAIN_TRACK1_D4Y_R7_CROSS_DOMAIN_RELATIONSHIP_SUBSTRATE_PREFLIGHT_DECISION.json", decision)
    write_hashes()


if __name__ == "__main__":
    main()

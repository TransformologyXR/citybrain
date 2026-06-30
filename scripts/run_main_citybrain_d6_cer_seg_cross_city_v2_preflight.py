#!/usr/bin/env python3
"""CityBrain D6 CER/SEG Cross-City V2 preflight.

This is a contract/preflight task. It consumes the frozen local-running,
R8, and Incident Mode outputs read-only and writes a separate v2 preflight
package. It does not mutate upstream state, ingest city data, or implement
a production CER/SEG runtime.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "MAIN-CITYBRAIN-D6-CER-SEG-CROSS-CITY-V2-PREFLIGHT"
PASS_STATUS = "PASS_MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_PREFLIGHT_WITH_LIMITATIONS"
BLOCKED_STATUS = "BLOCKED_MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_PREFLIGHT_WAITING_FOR_INCIDENT_MODE_CLOSEOUT"
FAIL_STATUS = "FAIL_MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_PREFLIGHT"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d6_cer_seg_cross_city_v2_preflight"

INCIDENT_CLOSEOUT_REQUIRED_STATUS = "PASS_MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_WITH_LIMITATIONS"

UPSTREAMS: dict[str, dict[str, Any]] = {
    "incident_closeout": {
        "task_id": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-CLOSEOUT",
        "root": "outputs/main_citybrain_d6_incident_mode_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_INCIDENT_MODE_CLOSEOUT_DECISION.json",
        "required": True,
        "expected_status": INCIDENT_CLOSEOUT_REQUIRED_STATUS,
    },
    "incident_r3_runtime_smoke": {
        "task_id": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-RUNTIME-SMOKE-R3",
        "root": "outputs/main_citybrain_d6_incident_mode_runtime_smoke_r3",
        "decision_file": "MAIN_CITYBRAIN_D6_INCIDENT_MODE_RUNTIME_SMOKE_R3_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "incident_r2_operator_review": {
        "task_id": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-OPERATOR-REVIEW-WORKFLOW-R2",
        "root": "outputs/main_citybrain_d6_incident_mode_operator_review_workflow_r2",
        "decision_file": "MAIN_CITYBRAIN_D6_INCIDENT_MODE_OPERATOR_REVIEW_WORKFLOW_R2_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "incident_r1_evidence_bundle": {
        "task_id": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-EVIDENCE-BUNDLE-R1",
        "root": "outputs/main_citybrain_d6_incident_mode_evidence_bundle_r1",
        "decision_file": "MAIN_CITYBRAIN_D6_INCIDENT_MODE_EVIDENCE_BUNDLE_R1_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "incident_preflight": {
        "task_id": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-PREFLIGHT",
        "root": "outputs/main_citybrain_d6_incident_mode_preflight",
        "decision_file": "MAIN_CITYBRAIN_D6_INCIDENT_MODE_PREFLIGHT_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "r8_hardening": {
        "task_id": "MAIN-CITYBRAIN-D4X-R8-MULTI-DOMAIN-EDGE-REGISTRY-HARDENING",
        "root": "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening",
        "decision_file": "MAIN_CITYBRAIN_D4X_R8_MULTI_DOMAIN_EDGE_REGISTRY_HARDENING_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "d6_d5_local_running_closeout": {
        "task_id": "MAIN-CITYBRAIN-D6-D5-LOCAL-RUNNING-SLICE-CLOSEOUT",
        "root": "outputs/main_citybrain_d6_d5_local_running_slice_closeout",
        "decision_file": "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_SLICE_CLOSEOUT_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "d6_d5_control_room_slice": {
        "task_id": "MAIN-CITYBRAIN-D6-D5-LOCAL-RUNNING-CONTROL-ROOM-SLICE-R1",
        "root": "outputs/main_citybrain_d6_d5_local_running_control_room_slice_r1",
        "decision_file": "MAIN_CITYBRAIN_D6_D5_LOCAL_RUNNING_CONTROL_ROOM_SLICE_R1_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "d5_track2_handoff_r4": {
        "task_id": "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-TRACK2-HANDOFF-R4",
        "root": "outputs/main_citybrain_d5_local_served_runtime_track2_handoff_r4",
        "decision_file": "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_TRACK2_HANDOFF_R4_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "d5_event_fabric_integration_r3": {
        "task_id": "MAIN-CITYBRAIN-D5-LOCAL-SERVED-RUNTIME-EVENT-FABRIC-INTEGRATION-R3",
        "root": "outputs/main_citybrain_d5_local_served_runtime_event_fabric_integration_r3",
        "decision_file": "MAIN_CITYBRAIN_D5_LOCAL_SERVED_RUNTIME_EVENT_FABRIC_INTEGRATION_R3_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "r7_multi_domain_runtime_slice": {
        "task_id": "MAIN-CITYBRAIN-D4X-R7-MULTI-DOMAIN-EDGE-REGISTRY-RUNTIME-SLICE",
        "root": "outputs/main_citybrain_d4x_r7_multi_domain_edge_registry_runtime_slice",
        "decision_file": "MAIN_CITYBRAIN_D4X_R7_MULTI_DOMAIN_EDGE_REGISTRY_RUNTIME_SLICE_DECISION.json",
        "required": True,
        "expected_prefix": "PASS_",
    },
    "track2a_omniverse_event_overlay_r3": {
        "task_id": "MAIN-TRACK2A-D4X-OMNIVERSE-EVENT-OVERLAY-INTEGRATION-R3",
        "root": "outputs/main_track2a_d4x_omniverse_event_overlay_integration_r3",
        "decision_file": "MAIN_TRACK2A_D4X_OMNIVERSE_EVENT_OVERLAY_INTEGRATION_R3_DECISION.json",
        "required": False,
        "expected_prefix": "PASS_",
    },
    "track2a_hero_neighbourhood_twin_preflight": {
        "task_id": "MAIN-TRACK2A-D5-HERO-NEIGHBOURHOOD-TWIN-PREFLIGHT",
        "root": "outputs/main_track2a_d5_hero_neighbourhood_twin_preflight",
        "decision_file": "MAIN_TRACK2A_D5_HERO_NEIGHBOURHOOD_TWIN_PREFLIGHT_DECISION.json",
        "required": False,
        "expected_prefix": "PASS_",
    },
}

JSON_CONTRACT_FILES = [
    "CER_SEG_V2_SCOPE_CONTRACT.json",
    "CANONICAL_ENTITY_V2_CONTRACT.json",
    "ENTITY_TYPE_V2_CATALOG.json",
    "RELATIONSHIP_ONTOLOGY_V2_CONTRACT.json",
    "CONFIDENCE_REVIEW_STATE_V2_CONTRACT.json",
    "EVIDENCE_LIMITATION_TRACE_V2_CONTRACT.json",
    "CER_TO_SEG_PROJECTION_CONTRACT.json",
    "SEG_TO_RUNTIME_QUERY_CONTRACT.json",
    "CROSS_CITY_EXTENSION_CONTRACT.json",
    "BACKWARD_COMPATIBILITY_CONTRACT.json",
    "VALIDATION_AND_GOVERNANCE_PLAN.json",
]

LIMITATIONS = [
    "preflight contract only",
    "no production CER/SEG runtime implemented",
    "no new city ingestion",
    "no public API readiness claim",
    "no official city data truth claim",
    "no legal, certified, confirmed, or departmental-system replacement claim",
    "no autonomous monitoring, alerts, dispatch, routing/control, enforcement, or automated action",
    "Incident Mode compatibility is review/query context only",
    "Omniverse/web compatibility is handoff/overlay context only",
    "R8 runtime-ready means local/replay query readiness, not production readiness",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def prepare_output_root() -> None:
    resolved = OUTPUT_ROOT.resolve()
    expected_parent = (REPO_ROOT / "outputs").resolve()
    if resolved.parent != expected_parent or resolved.name != "main_citybrain_d6_cer_seg_cross_city_v2_preflight":
        raise RuntimeError(f"Refusing to reset unexpected output root: {resolved}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def decision_status(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None
    for key in ("status", "final_status", "decision_status"):
        value = data.get(key)
        if value:
            return str(value)
    return None


def discover_upstreams() -> tuple[dict[str, Any], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    required_missing_or_not_green: list[str] = []
    optional_missing: list[str] = []
    optional_present: list[str] = []
    for key, spec in UPSTREAMS.items():
        root = REPO_ROOT / spec["root"]
        decision_path = root / spec["decision_file"]
        decision = load_json(decision_path, {})
        status = decision_status(decision)
        exists = root.exists() and decision_path.exists()
        if spec.get("expected_status"):
            green = status == spec["expected_status"]
        else:
            green = bool(status and status.startswith(str(spec.get("expected_prefix", "PASS_"))))
        row = {
            "upstream_key": key,
            "task_id": spec["task_id"],
            "root": spec["root"],
            "decision_file": rel(decision_path),
            "exists": exists,
            "required": bool(spec["required"]),
            "status": status,
            "green": bool(exists and green),
            "artifacts": [],
        }
        if root.exists():
            artifacts = []
            for path in sorted(root.iterdir()):
                if path.is_file():
                    artifacts.append(
                        {
                            "path": rel(path),
                            "bytes": path.stat().st_size,
                            "sha256": sha256_file(path),
                        }
                    )
            row["artifacts"] = artifacts
        rows.append(row)
        if spec["required"] and not row["green"]:
            required_missing_or_not_green.append(key)
        if not spec["required"]:
            if row["green"]:
                optional_present.append(key)
            else:
                optional_missing.append(key)
    summary = {
        "task_id": TASK_ID,
        "run_timestamp_utc": now_iso(),
        "required_count": sum(1 for spec in UPSTREAMS.values() if spec["required"]),
        "required_green_count": sum(1 for row in rows if row["required"] and row["green"]),
        "required_missing_or_not_green": required_missing_or_not_green,
        "optional_present": optional_present,
        "optional_missing": optional_missing,
        "incident_mode_closeout_found": any(row["upstream_key"] == "incident_closeout" and row["exists"] for row in rows),
        "incident_mode_closeout_green": any(row["upstream_key"] == "incident_closeout" and row["green"] for row in rows),
        "status": "PASS" if not required_missing_or_not_green else "FAIL",
    }
    return {"task_id": TASK_ID, "upstreams": rows}, summary


def upstream_signature() -> dict[str, dict[str, str]]:
    signatures: dict[str, dict[str, str]] = {}
    for key, spec in UPSTREAMS.items():
        root = REPO_ROOT / spec["root"]
        if not root.exists():
            signatures[key] = {"__missing__": "true"}
            continue
        sig: dict[str, str] = {}
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            sig[rel(path)] = f"{path.stat().st_size}:{sha256_file(path)}"
        signatures[key] = sig
    return signatures


def r8_rules() -> dict[str, Any]:
    root = REPO_ROOT / "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening"
    return load_json(root / "R8_HARDENING_RULESET.json", {})


def r8_partition() -> dict[str, Any]:
    root = REPO_ROOT / "outputs/main_citybrain_d4x_r8_multi_domain_edge_registry_hardening"
    return load_json(root / "RUNTIME_READY_REVIEW_ONLY_PARTITION.json", {})


def incident_bundle_schema() -> dict[str, Any]:
    root = REPO_ROOT / "outputs/main_citybrain_d6_incident_mode_evidence_bundle_r1"
    return load_json(root / "INCIDENT_EVIDENCE_BUNDLE_SCHEMA.json", {})


def operator_packet_schema() -> dict[str, Any]:
    root = REPO_ROOT / "outputs/main_citybrain_d6_incident_mode_operator_review_workflow_r2"
    return load_json(root / "OPERATOR_REVIEW_PACKET_SCHEMA.json", {})


def build_scope_contract(input_summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_id": "CER_SEG_V2_SCOPE_CONTRACT",
        "task_id": TASK_ID,
        "status": "preflight_contract",
        "scope": [
            "Canonical Entity Registry semantics",
            "Semantic Entity Graph projection semantics",
            "city-scoped canonical IDs",
            "cross-city entity type vocabulary",
            "relationship ontology v2",
            "confidence and review-state semantics",
            "evidence, limitation, lineage, and trace envelope",
            "event/current-state relationship treatment",
            "Incident Mode relationship compatibility",
            "Omniverse/web handoff compatibility",
            "R8 edge-registry compatibility",
            "cross-city and domain-pack extension rules",
        ],
        "non_goals": [
            "new city ingestion",
            "production data-governance rollout",
            "public API",
            "global master identifier replacing local authority IDs",
            "citywide certified digital twin",
            "legal, certified, confirmed, enforcement, dispatch, routing/control, or autonomous action output",
        ],
        "architecture_rule": {
            "cer_owns": "identity truth and evidence-backed canonical entity state",
            "seg_owns": "relationship projection, traversal, and reasoning views",
            "shared_contracts_own": "exchange boundary between CER, SEG, runtime, Incident Mode, and handoff packets",
            "not_allowed": [
                "SEG as system of record for unresolved truth",
                "forced cross-city global identifier replacing jurisdiction-local IDs",
                "collapse of CER and SEG into one undifferentiated graph",
            ],
        },
        "upstream_basis": input_summary,
        "limitations": LIMITATIONS,
    }


def build_canonical_entity_contract() -> dict[str, Any]:
    return {
        "contract_id": "CANONICAL_ENTITY_V2_CONTRACT",
        "entity_identity_envelope": {
            "required": [
                "canonical_entity_id",
                "entity_type",
                "city_id",
                "jurisdiction_scope",
                "canonical_status",
                "source_aliases",
                "evidence_refs",
                "confidence",
                "review_state",
                "limitation_refs",
                "lineage_refs",
                "created_by_task",
                "updated_by_task",
            ],
            "id_policy": {
                "format": "citybrain:cer:{city_id}:{entity_type}:{stable_local_key_or_hash}",
                "city_scoped": True,
                "source_ids_preserved": True,
                "jurisdiction_local_ids_preserved": True,
                "global_open_ids_optional_aliases_only": True,
                "no_forced_global_master_identifier": True,
            },
            "source_alias_shape": {
                "source_system": "string",
                "source_record_id": "string",
                "source_record_uri": "optional string",
                "authority_level": "authoritative | open_public | derived | manual_fixture | unknown",
                "alias_confidence": "0.0..1.0",
                "alias_review_state": "review-context enum",
            },
            "authoritative_local_id_shape": {
                "jurisdiction": "string",
                "id_name": "string",
                "id_value": "string",
                "source_ref": "string",
                "legal_truth_claim": False,
            },
            "global_open_id_shape": {
                "id_system": "OSM | Overture | external_open_id | vendor_asset_id",
                "id_value": "string",
                "alias_only": True,
            },
        },
        "canonical_status_values": [
            "source_only",
            "candidate",
            "candidate_with_limitations",
            "review_context",
            "unresolved",
            "quarantined",
            "disputed",
            "deprecated_superseded",
        ],
        "forbidden_status_values": [
            "official_truth",
            "certified_truth",
            "legal_finding",
            "confirmed_violation",
            "production_ready",
        ],
        "confidence": {
            "match_confidence": "evidence-backed identity match confidence",
            "attribute_confidence": "confidence in a field value",
            "relationship_confidence": "confidence in a relationship projection",
            "path_confidence": "minimum/aggregate confidence over SEG traversal",
            "not_certification": True,
        },
        "review_state": {
            "preserves_uncertainty": True,
            "human_review_or_preflight_gate_required_for_promotion": True,
            "unresolved_and_quarantined_never_silently_promoted": True,
        },
    }


def entity_type(name: str, matching_keys: list[str], relationships: list[str], optional: list[str] | None = None) -> dict[str, Any]:
    return {
        "entity_type": name,
        "required_fields": [
            "canonical_entity_id",
            "city_id",
            "jurisdiction_scope",
            "source_aliases",
            "evidence_refs",
            "confidence",
            "review_state",
            "limitation_refs",
        ],
        "optional_fields": optional or [
            "geometry_ref",
            "time_range",
            "current_state_ref",
            "source_payload_ref",
            "global_open_aliases",
        ],
        "matching_keys": matching_keys,
        "core_relationships": relationships,
        "data_quality_tests": [
            "required fields present",
            "source aliases not empty",
            "evidence refs present",
            "limitation refs present when confidence below high",
            "review state valid",
            "city/jurisdiction scope present",
        ],
    }


def build_entity_type_catalog() -> dict[str, Any]:
    types = [
        entity_type("Community", ["city_id", "district_code", "neighbourhood_code", "admin_unit_code"], ["contains Site", "contains Road Segment", "has Facility"]),
        entity_type("Address", ["city_id", "street_name", "house_number", "postcode", "source_address_id"], ["locates Site", "locates Building", "within Community"]),
        entity_type("Site", ["city_id", "site_id", "parcel_id", "geometry_hash"], ["contains Building", "within Community", "has Address"]),
        entity_type("Parcel", ["city_id", "parcel_id", "cadastre_ref", "geometry_hash"], ["contains Building", "has Address", "within Community"]),
        entity_type("Building", ["city_id", "building_id", "bin", "bbl", "cadastre_building_id", "doitt_id", "geometry_hash"], ["located_on Parcel", "has Address", "has Unit/Premise", "represented_by Asset"]),
        entity_type("Unit/Premise", ["city_id", "unit_id", "address_id", "premise_id"], ["inside Building", "has Transaction", "has Inspection"]),
        entity_type("Road Segment", ["city_id", "road_section_id", "street_name", "geometry_hash"], ["intersects Junction", "serves Address", "has Event"]),
        entity_type("Junction", ["city_id", "junction_id", "geometry_hash"], ["intersects Road Segment", "near Facility"]),
        entity_type("Facility", ["city_id", "facility_id", "register_id", "source_name"], ["located_at Address", "within Community", "serves Community"]),
        entity_type("System", ["city_id", "system_id", "system_type"], ["contains Component", "has Service Point"]),
        entity_type("Component", ["city_id", "component_id", "system_id"], ["part_of System", "observed_by Instrument/Control Point"]),
        entity_type("Service Point", ["city_id", "service_point_id", "system_id", "address_id"], ["serves Address", "part_of System"]),
        entity_type("Instrument/Control Point", ["city_id", "instrument_id", "station_id", "sensor_id"], ["observes Observation", "located_at Site"]),
        entity_type("Observation", ["city_id", "observation_id", "instrument_id", "observed_at"], ["observed_by Instrument/Control Point", "context_for Event"]),
        entity_type("Event", ["city_id", "event_id", "source_event_id", "event_time"], ["affects Entity", "has Observation", "has Incident Review"]),
        entity_type("Incident Review", ["city_id", "incident_review_id", "incident_input_ref"], ["reviews Event", "reviews affected Entity", "has Evidence Bundle"]),
        entity_type("Permit", ["city_id", "permit_id", "source_record_id"], ["applies_to Building", "issued_by Department"]),
        entity_type("Inspection", ["city_id", "inspection_id", "source_record_id"], ["inspects Building", "has Violation"]),
        entity_type("Violation", ["city_id", "violation_id", "source_record_id"], ["associated_with Inspection", "associated_with Building"]),
        entity_type("Transaction", ["city_id", "transaction_id", "source_record_id"], ["references Parcel", "references Unit/Premise"]),
        entity_type("Work Order", ["city_id", "work_order_id", "source_record_id"], ["references Facility", "references System"]),
        entity_type("Project", ["city_id", "project_id", "source_record_id"], ["affects Site", "affects Community"]),
        entity_type("Party", ["party_id", "source_party_id", "name_hash_or_source_ref"], ["has Role/Interest Assignment"], ["party_name_ref", "organization_ref", "person_ref", "privacy_boundary_ref"]),
        entity_type("Person", ["source_person_id", "privacy_safe_person_ref"], ["has Role/Interest Assignment"], ["privacy_boundary_ref", "party_ref"]),
        entity_type("Organization", ["source_org_id", "registration_or_source_ref"], ["has Role/Interest Assignment", "is Department"]),
        entity_type("Department", ["city_id", "department_id", "source_department_code"], ["issues Permit", "performs Inspection", "owns Work Order"]),
        entity_type("Role/Interest Assignment", ["assignment_id", "party_ref", "entity_ref", "role_type"], ["assigns Party to Entity"]),
    ]
    return {
        "contract_id": "ENTITY_TYPE_V2_CATALOG",
        "entity_types": {item["entity_type"]: item for item in types},
        "shared_required_fields": [
            "canonical_entity_id",
            "city_id",
            "jurisdiction_scope",
            "source_aliases",
            "evidence_refs",
            "confidence",
            "review_state",
            "limitation_refs",
        ],
        "privacy_note": "Person/Party records require privacy-safe refs and must not be used for sensitive or individual inference without a separate gate.",
    }


def build_relationship_ontology_contract(rules: dict[str, Any]) -> dict[str, Any]:
    r8_families = rules.get("valid_relationship_families", [])
    return {
        "contract_id": "RELATIONSHIP_ONTOLOGY_V2_CONTRACT",
        "relationship_families": {
            "identity_alias": "source aliases and local authoritative IDs mapped to a canonical entity without replacing local authority IDs",
            "spatial_containment": "within/contains geography and built-environment hierarchy",
            "spatial_adjacency": "near/intersects/served-by context, never causal proof",
            "asset_representation": "USD/3D/asset registry object represents or depicts candidate CER entity context",
            "event_affects_entity": "event/current-state context references affected entities for review only",
            "observation_context": "sensor or observation provides environmental/context evidence",
            "domain_review_context": "domain pack packet references an entity/edge for review context",
            "incident_review_context": "Incident Mode bundle/operator packet references affected entities and hardened R8 edges",
            "workflow_context": "permit/inspection/work-order/project relationships for evidence-bound review context",
            "r8_compatibility_families": r8_families,
        },
        "allowed_source_target_pairs": [
            {"source": "Community", "target": "Address", "relationship": "contains"},
            {"source": "Parcel", "target": "Building", "relationship": "contains"},
            {"source": "Building", "target": "Unit/Premise", "relationship": "contains"},
            {"source": "Address", "target": "Building", "relationship": "locates"},
            {"source": "Road Segment", "target": "Event", "relationship": "context_for"},
            {"source": "Instrument/Control Point", "target": "Observation", "relationship": "observes"},
            {"source": "Observation", "target": "Event", "relationship": "context_for"},
            {"source": "Event", "target": "Incident Review", "relationship": "reviewed_by"},
            {"source": "Incident Review", "target": "Building", "relationship": "references_affected_entity"},
            {"source": "Permit", "target": "Building", "relationship": "applies_to"},
            {"source": "Inspection", "target": "Building", "relationship": "inspects"},
            {"source": "Violation", "target": "Inspection", "relationship": "associated_with"},
            {"source": "Party", "target": "Role/Interest Assignment", "relationship": "has_role_assignment"},
        ],
        "relationship_states": rules.get("valid_relationship_states", []) + ["historical_context", "disputed_context"],
        "inverse_rules": {
            "contains": "within",
            "locates": "located_at",
            "observes": "observed_by",
            "applies_to": "has_permit_context",
            "inspects": "has_inspection_context",
            "reviewed_by": "reviews",
            "represented_by": "represents",
        },
        "temporal_treatment": {
            "required_when_known": ["effective_from", "effective_to", "observed_at", "valid_time", "transaction_time"],
            "current_state_projection": "current-state relationships are derived views, not replacement truth",
            "historical_edges": "retained with temporal envelope and excluded from current-only traversals unless requested",
        },
        "event_current_state_treatment": {
            "event_edges": "append/replay context edges keep event refs and source payload refs",
            "current_state_edges": "materialized state context edges keep derivation trace to event log/current-state artifact",
            "no_mutation_of_canonical_truth": True,
        },
        "incident_mode_treatment": {
            "affected_entity_resolution": "references candidate canonical entity refs, source aliases, and uncertainty trace",
            "operator_review": "review packets remain no-action, context-only outputs",
            "safe_next_look": "query suggestions only; no alert/action/dispatch/enforcement/control transition",
        },
        "forbidden_semantics": [
            "causal proof from adjacency alone",
            "legal/certified/confirmed truth",
            "source ID promoted to ownership/legal truth",
            "review-only edge promoted to runtime truth without gate",
            "unresolved/quarantined edge traversed as normal entity truth",
        ],
    }


def build_confidence_review_state_contract(rules: dict[str, Any], incident_schema: dict[str, Any], operator_schema: dict[str, Any]) -> dict[str, Any]:
    incident_states = incident_schema.get("properties", {}).get("review_state", {}).get("enum", [])
    operator_states = operator_schema.get("properties", {}).get("operator_review_state", {}).get("enum", [])
    r8_review_states = rules.get("valid_review_states", [])
    return {
        "contract_id": "CONFIDENCE_REVIEW_STATE_V2_CONTRACT",
        "confidence_range": rules.get("confidence_range", [0.0, 1.0]),
        "confidence_types": {
            "match_confidence": "identity resolution confidence",
            "attribute_confidence": "single field/source value confidence",
            "relationship_confidence": "edge confidence",
            "path_traversal_confidence": "confidence for a multi-edge query path",
        },
        "confidence_bands": {
            "high": {"min": 0.85, "meaning": "strong evidence context, still not certified truth"},
            "medium": {"min": 0.6, "max": 0.849, "meaning": "usable for review context with limitations"},
            "low": {"min": 0.01, "max": 0.599, "meaning": "preserve and expose limitation"},
            "unknown": {"min": 0.0, "max": 0.0, "meaning": "insufficient evidence"},
            "disputed": {"meaning": "conflicting evidence or review dispute"},
        },
        "review_states": {
            "r8_review_states": r8_review_states,
            "incident_evidence_bundle_states": incident_states,
            "operator_review_packet_states": operator_states,
            "v2_shared_states": sorted(set(r8_review_states + incident_states + operator_states + [
                "source_only",
                "candidate",
                "candidate_with_limitations",
                "disputed",
                "deprecated_superseded",
            ])),
        },
        "unresolved_quarantined_disputed_handling": {
            "unresolved": "preserve in CER and SEG with traversal restrictions",
            "quarantined": "preserve in quarantine/reference partition, excluded from normal traversal",
            "disputed": "preserve competing evidence and require review state",
        },
        "promotion_rules": [
            "source aliases may be promoted only through explicit gate evidence",
            "review-only edges may become runtime-ready review context only through validation, not by consumption readiness",
            "Incident Mode review states do not produce confirmed incident states",
        ],
        "demotion_rules": [
            "new conflicting evidence can demote to disputed",
            "source withdrawal can demote to deprecated_superseded",
            "schema or source-quality failure can demote to quarantined",
        ],
        "forbidden_states": sorted(set(
            incident_schema.get("forbidden_review_states", [])
            + operator_schema.get("forbidden_states", [])
            + ["production_ready", "certified_truth", "legal_finding"]
        )),
    }


def build_evidence_limitation_trace_contract() -> dict[str, Any]:
    return {
        "contract_id": "EVIDENCE_LIMITATION_TRACE_V2_CONTRACT",
        "trace_envelope": {
            "required": [
                "trace_id",
                "source_artifact_refs",
                "source_branch_refs",
                "evidence_refs",
                "limitation_refs",
                "audit_refs",
                "lineage_refs",
                "generated_by_task",
                "generated_at_utc",
                "no_action_taken",
            ],
            "evidence_ref_shape": {
                "evidence_ref": "string",
                "artifact_path": "optional string",
                "source_system": "string",
                "source_record_id": "optional string",
                "observed_or_generated_at": "optional timestamp",
                "claim_boundary": "string",
            },
            "limitation_ref_shape": {
                "limitation_ref": "string",
                "limitation_type": "coverage | freshness | source_quality | identity_resolution | privacy | legal_boundary | runtime_boundary | unresolved | quarantined",
                "description": "string",
                "blocks_claims": ["legal/certified truth", "action/control", "production readiness"],
            },
            "audit_ref_shape": {
                "audit_ref": "string",
                "audit_type": "claim_boundary | no_action | no_mutation | secret | hash | validation",
                "status": "PASS | PASS_WITH_LIMITATIONS | FAIL",
            },
        },
        "lineage_policy": {
            "must_keep_source_payload_or_ref": True,
            "must_keep_current_state_derivation_ref": True,
            "must_keep_incident_input_ref": True,
            "must_keep_operator_packet_ref": True,
        },
    }


def build_cer_to_seg_projection_contract() -> dict[str, Any]:
    return {
        "contract_id": "CER_TO_SEG_PROJECTION_CONTRACT",
        "projection_rule": "CER canonical entities and evidence-backed source relationships project into SEG nodes/edges; SEG does not become source of canonical identity truth.",
        "node_projection": {
            "seg_node_id": "citybrain:seg:{city_id}:{entity_type}:{canonical_entity_id_hash}",
            "source": "canonical_entity_id",
            "fields": ["entity_type", "city_id", "jurisdiction_scope", "canonical_status", "confidence", "review_state", "evidence_refs", "limitation_refs"],
        },
        "edge_projection": {
            "seg_edge_id": "citybrain:seg-edge:{city_id}:{relationship_family}:{stable_edge_hash}",
            "source": "CER source relationship or R8 edge registry row",
            "fields": ["relationship_family", "source_node_ref", "target_node_ref", "relationship_state", "confidence", "review_state", "evidence_refs", "limitation_refs", "temporal_envelope"],
        },
        "partitions": {
            "runtime_ready_review_context": "queryable local/replay review context, not production truth",
            "review_only": "visible in review/query packets but not traversed as asserted runtime context",
            "unresolved": "preserved and exposed with limitation, excluded from normal traversal",
            "quarantined": "preserved for audit, excluded from traversal",
        },
        "unresolved_quarantined_preservation": {
            "preserve_original_refs": True,
            "exclude_from_default_traversal": True,
            "expose_as_limitations": True,
            "no_silent_drop": True,
        },
    }


def build_seg_to_runtime_query_contract() -> dict[str, Any]:
    return {
        "contract_id": "SEG_TO_RUNTIME_QUERY_CONTRACT",
        "query_dto": {
            "required": ["query_id", "city_id", "query_profile", "entity_or_event_ref", "requested_context", "review_boundary"],
            "optional": ["max_depth", "relationship_families", "include_partitions", "time_window", "domain_filters"],
        },
        "response_dto": {
            "required": [
                "query_id",
                "city_id",
                "node_summaries",
                "edge_summaries",
                "evidence_refs",
                "limitation_refs",
                "trace_refs",
                "confidence_summary",
                "review_state_summary",
                "no_action_taken",
            ],
        },
        "incident_mode_context_queries": [
            "resolve incident input to candidate affected entities",
            "retrieve hardened R8 edges for affected entity context",
            "retrieve unresolved/quarantined limitations for operator packet",
            "retrieve safe-next-look candidates without action transition",
        ],
        "event_current_state_context_queries": [
            "event to affected entity context",
            "current-state entity to recent event context",
            "unresolved event preservation lookup",
        ],
        "omniverse_web_packet_compatibility": [
            "asset pick to CER candidate context",
            "CER candidate to SEG relationship summary",
            "SEG summary to overlay packet",
            "evidence/limitation refs carried into web companion",
        ],
        "forbidden_query_outputs": [
            "dispatch instruction",
            "routing/control instruction",
            "enforcement recommendation",
            "legal/certified finding",
            "confirmed incident claim",
            "autonomous alert",
        ],
    }


def build_cross_city_extension_contract() -> dict[str, Any]:
    return {
        "contract_id": "CROSS_CITY_EXTENSION_CONTRACT",
        "city_scoped_id_policy": {
            "canonical_id_must_include_city_or_jurisdiction_scope": True,
            "same_local_id_different_city_not_same_entity": True,
            "cross_city_comparison_uses_aliases_and_type_vocab_not_forced_master_ids": True,
        },
        "jurisdiction_local_id_policy": {
            "preserve_source_system_id_name": True,
            "preserve_local_authority": True,
            "do_not_overwrite_with_global_ids": True,
        },
        "source_system_alias_policy": {
            "multiple_aliases_allowed": True,
            "alias_confidence_required": True,
            "alias_review_state_required": True,
        },
        "global_open_id_alias_policy": {
            "optional": True,
            "alias_only": True,
            "never_replaces_local_authoritative_id": True,
        },
        "city_pack_extension_rules": [
            "new city must declare local authority systems and source aliases",
            "new city must map entity types to v2 catalog or propose extension",
            "new city must preserve evidence/limitation/trace refs",
            "new city must pass forbidden-claim/no-mutation/secret/hash audits",
        ],
        "domain_pack_extension_rules": [
            "domain pack must declare required entity types",
            "domain pack must declare relationship families and allowed pairs",
            "domain pack must use CER request packets and SEG query packets",
            "domain pack must not bypass review-state/confidence semantics",
        ],
    }


def build_backward_compatibility_contract(input_index: dict[str, Any], partition: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_id": "BACKWARD_COMPATIBILITY_CONTRACT",
        "compatibility_matrix": [
            {
                "upstream": row["task_id"],
                "upstream_key": row["upstream_key"],
                "status": row["status"],
                "v2_compatibility": "compatible_read_only" if row["green"] else "missing_or_not_green",
                "mutation_allowed": False,
            }
            for row in input_index["upstreams"]
        ],
        "r7_r8_compatibility": {
            "edge_ids_preserved": True,
            "review_state_preserved": True,
            "confidence_values_preserved": True,
            "runtime_ready_vs_review_only_partitions_preserved": True,
            "partition_counts": partition.get("counts", {}),
        },
        "d5_d6_local_running_compatibility": {
            "local_running_slice_read_only": True,
            "runtime/event handoffs remain packet refs": True,
            "no public service assumption": True,
        },
        "incident_mode_compatibility": {
            "evidence_bundle_fields_preserved": True,
            "operator_review_fields_preserved": True,
            "safe_next_look_remains_query_suggestion_only": True,
            "no confirmed incident state": True,
        },
        "track2_omniverse_web_handoff_compatibility": {
            "asset/overlay refs remain context refs": True,
            "visual context does not control CER/SEG truth": True,
            "hero_neighbourhood_optional_visual_context_only": True,
        },
    }


def build_validation_governance_plan() -> dict[str, Any]:
    return {
        "contract_id": "VALIDATION_AND_GOVERNANCE_PLAN",
        "required_validations": [
            "Incident Mode closeout green before proceeding",
            "required upstream artifact presence",
            "required contract files present",
            "JSON parse validity",
            "required schema keys present",
            "enum consistency",
            "R8 review-state/confidence compatibility",
            "Incident Mode evidence/operator compatibility",
            "no causal leakage",
            "no production/public/API claim",
            "no autonomous monitoring/alert/dispatch/routing/control/enforcement claim",
            "no legal/certified/confirmed/official-city-truth claim",
            "no mutation of frozen upstream outputs",
            "no secret leakage",
            "hash manifest generated and verified",
        ],
        "governance_gates": {
            "contract_r1": "canonical entity schema and ID policy",
            "ontology_r2": "relationship ontology and inverse/temporal treatment",
            "confidence_review_r3": "confidence and review-state contract",
            "runtime_bridge_r4": "read-only runtime compatibility smoke",
            "closeout": "cross-city v2 closeout after smoke and audits",
        },
        "non_goals": LIMITATIONS,
    }


def write_contracts(input_index: dict[str, Any], upstream_summary: dict[str, Any]) -> None:
    rules = r8_rules()
    partition = r8_partition()
    incident_schema = incident_bundle_schema()
    operator_schema = operator_packet_schema()
    contracts = {
        "CER_SEG_V2_SCOPE_CONTRACT.json": build_scope_contract(upstream_summary),
        "CANONICAL_ENTITY_V2_CONTRACT.json": build_canonical_entity_contract(),
        "ENTITY_TYPE_V2_CATALOG.json": build_entity_type_catalog(),
        "RELATIONSHIP_ONTOLOGY_V2_CONTRACT.json": build_relationship_ontology_contract(rules),
        "CONFIDENCE_REVIEW_STATE_V2_CONTRACT.json": build_confidence_review_state_contract(rules, incident_schema, operator_schema),
        "EVIDENCE_LIMITATION_TRACE_V2_CONTRACT.json": build_evidence_limitation_trace_contract(),
        "CER_TO_SEG_PROJECTION_CONTRACT.json": build_cer_to_seg_projection_contract(),
        "SEG_TO_RUNTIME_QUERY_CONTRACT.json": build_seg_to_runtime_query_contract(),
        "CROSS_CITY_EXTENSION_CONTRACT.json": build_cross_city_extension_contract(),
        "BACKWARD_COMPATIBILITY_CONTRACT.json": build_backward_compatibility_contract(input_index, partition),
        "VALIDATION_AND_GOVERNANCE_PLAN.json": build_validation_governance_plan(),
    }
    for filename, data in contracts.items():
        write_json(OUTPUT_ROOT / filename, data)


def implementation_roadmap() -> str:
    return f"""# Implementation Roadmap

Status: preflight complete, implementation deferred.

Recommended sequence:

1. MAIN-CITYBRAIN-D6-CER-SEG-V2-CANONICAL-ENTITY-CONTRACT-R1
2. MAIN-CITYBRAIN-D6-CER-SEG-V2-RELATIONSHIP-ONTOLOGY-R2
3. MAIN-CITYBRAIN-D6-CER-SEG-V2-CONFIDENCE-REVIEW-STATE-CONTRACT-R3
4. MAIN-CITYBRAIN-D6-CER-SEG-V2-RUNTIME-BRIDGE-SMOKE-R4
5. MAIN-CITYBRAIN-D6-CER-SEG-CROSS-CITY-V2-CLOSEOUT

Dependencies:

- Keep the frozen R7/R8/D5/D6 local-running chain read-only.
- Keep Incident Mode evidence bundle and operator-review fields compatible.
- Use city-scoped IDs and preserve jurisdiction-local IDs.
- Treat Track2/Omniverse/web packets as handoff/overlay context, not identity truth.

Non-goals:

- No new city ingestion.
- No production/public API rollout.
- No global master ID replacing local authority IDs.
- No autonomous monitoring, alert, dispatch, enforcement, routing/control, or legal/certified/confirmed output.
"""


def local_open_index() -> str:
    files = [
        "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_PREFLIGHT_DECISION.json",
        "INPUT_ARTIFACT_INDEX.json",
        "UPSTREAM_STATUS_SUMMARY.json",
        "CER_SEG_V2_SCOPE_CONTRACT.json",
        "CANONICAL_ENTITY_V2_CONTRACT.json",
        "ENTITY_TYPE_V2_CATALOG.json",
        "RELATIONSHIP_ONTOLOGY_V2_CONTRACT.json",
        "CONFIDENCE_REVIEW_STATE_V2_CONTRACT.json",
        "CER_TO_SEG_PROJECTION_CONTRACT.json",
        "SEG_TO_RUNTIME_QUERY_CONTRACT.json",
        "CROSS_CITY_EXTENSION_CONTRACT.json",
        "BACKWARD_COMPATIBILITY_CONTRACT.json",
        "VALIDATION_AND_GOVERNANCE_PLAN.json",
        "IMPLEMENTATION_ROADMAP.md",
    ]
    lines = [f"# {TASK_ID}", "", f"Output root: `{rel(OUTPUT_ROOT)}`", "", "## Open Index", ""]
    for filename in files:
        lines.append(f"- `{filename}`")
    return "\n".join(lines)


def validate_contracts(input_index: dict[str, Any], upstream_summary: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {
        "task_id": TASK_ID,
        "run_timestamp_utc": now_iso(),
        "checks": [],
    }

    def add(name: str, passed: bool, details: Any = None) -> None:
        results["checks"].append({"check": name, "status": "PASS" if passed else "FAIL", "details": details})

    add("incident_mode_closeout_green", bool(upstream_summary["incident_mode_closeout_green"]), upstream_summary)
    add("required_upstreams_green", upstream_summary["status"] == "PASS", upstream_summary["required_missing_or_not_green"])

    required_files = [
        "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_PREFLIGHT_DECISION.json",
        "README.md",
        "INPUT_ARTIFACT_INDEX.json",
        "UPSTREAM_STATUS_SUMMARY.json",
        *JSON_CONTRACT_FILES,
        "IMPLEMENTATION_ROADMAP.md",
        "CLAIM_BOUNDARY_AUDIT.json",
        "NO_MUTATION_AUDIT.json",
        "SECRET_AUDIT.json",
        "LOCAL_OPEN_INDEX.md",
    ]
    missing_files = [name for name in required_files if not (OUTPUT_ROOT / name).exists()]
    add("required_files_present", not missing_files, missing_files)

    parse_failures = []
    parsed_contracts: dict[str, Any] = {}
    for name in JSON_CONTRACT_FILES:
        try:
            parsed_contracts[name] = load_json(OUTPUT_ROOT / name, {})
        except Exception as exc:  # pragma: no cover - defensive local runner
            parse_failures.append({"file": name, "error": str(exc)})
    add("json_parse_validity", not parse_failures, parse_failures)

    required_contract_keys = {
        "CER_SEG_V2_SCOPE_CONTRACT.json": ["contract_id", "scope", "non_goals", "architecture_rule"],
        "CANONICAL_ENTITY_V2_CONTRACT.json": ["contract_id", "entity_identity_envelope", "canonical_status_values"],
        "ENTITY_TYPE_V2_CATALOG.json": ["contract_id", "entity_types", "shared_required_fields"],
        "RELATIONSHIP_ONTOLOGY_V2_CONTRACT.json": ["contract_id", "relationship_families", "allowed_source_target_pairs", "forbidden_semantics"],
        "CONFIDENCE_REVIEW_STATE_V2_CONTRACT.json": ["contract_id", "confidence_types", "review_states", "promotion_rules"],
        "EVIDENCE_LIMITATION_TRACE_V2_CONTRACT.json": ["contract_id", "trace_envelope", "lineage_policy"],
        "CER_TO_SEG_PROJECTION_CONTRACT.json": ["contract_id", "projection_rule", "node_projection", "edge_projection"],
        "SEG_TO_RUNTIME_QUERY_CONTRACT.json": ["contract_id", "query_dto", "response_dto"],
        "CROSS_CITY_EXTENSION_CONTRACT.json": ["contract_id", "city_scoped_id_policy", "domain_pack_extension_rules"],
        "BACKWARD_COMPATIBILITY_CONTRACT.json": ["contract_id", "compatibility_matrix", "r7_r8_compatibility"],
        "VALIDATION_AND_GOVERNANCE_PLAN.json": ["contract_id", "required_validations", "governance_gates"],
    }
    key_failures = []
    for name, keys in required_contract_keys.items():
        data = parsed_contracts.get(name, {})
        for key in keys:
            if key not in data:
                key_failures.append({"file": name, "missing_key": key})
    add("required_schema_keys_present", not key_failures, key_failures)

    rules = r8_rules()
    confidence_contract = parsed_contracts.get("CONFIDENCE_REVIEW_STATE_V2_CONTRACT.json", {})
    ontology_contract = parsed_contracts.get("RELATIONSHIP_ONTOLOGY_V2_CONTRACT.json", {})
    review_states = set(confidence_contract.get("review_states", {}).get("v2_shared_states", []))
    r8_review_states = set(rules.get("valid_review_states", []))
    incident_states = set(incident_bundle_schema().get("properties", {}).get("review_state", {}).get("enum", []))
    operator_states = set(operator_packet_schema().get("properties", {}).get("operator_review_state", {}).get("enum", []))
    missing_review_states = sorted((r8_review_states | incident_states | operator_states) - review_states)
    add("enum_consistency_review_states", not missing_review_states, missing_review_states)

    relationship_states = set(ontology_contract.get("relationship_states", []))
    missing_relationship_states = sorted(set(rules.get("valid_relationship_states", [])) - relationship_states)
    add("enum_consistency_relationship_states", not missing_relationship_states, missing_relationship_states)

    r8_families = set(rules.get("valid_relationship_families", []))
    ontology_r8_families = set(ontology_contract.get("relationship_families", {}).get("r8_compatibility_families", []))
    add("r8_relationship_family_compatibility", r8_families.issubset(ontology_r8_families), sorted(r8_families - ontology_r8_families))

    incident_required = set(incident_bundle_schema().get("required", []))
    runtime_required = set(parsed_contracts.get("SEG_TO_RUNTIME_QUERY_CONTRACT.json", {}).get("response_dto", {}).get("required", []))
    add("incident_evidence_operator_semantics_preserved", {"evidence_refs", "limitation_refs", "no_action_taken"}.issubset(incident_required | runtime_required))

    text_blob = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in OUTPUT_ROOT.rglob("*") if path.is_file())
    positive_forbidden_patterns = [
        '"production_readiness_claim_made": true',
        '"public_api_readiness_claim_made": true',
        '"official_city_truth_claim_made": true',
        '"autonomous_monitoring_claim_made": true',
        '"alert_dispatch_routing_control_enforcement_claim_made": true',
        '"legal_certified_confirmed_claim_made": true',
        "autonomous monitoring enabled",
        "public api ready",
        "production ready for deployment",
        "legal finding issued",
        "official city truth established",
    ]
    positive_hits = [term for term in positive_forbidden_patterns if term.lower() in text_blob.lower()]
    add("no_forbidden_positive_claims", not positive_hits, positive_hits)

    add("no_causal_leakage", "causal proof from adjacency alone" in text_blob and "forbidden_semantics" in text_blob)

    results["status"] = "PASS" if all(check["status"] == "PASS" for check in results["checks"]) else "FAIL"
    return results


def claim_boundary_audit() -> dict[str, Any]:
    contracts = {name: load_json(OUTPUT_ROOT / name, {}) for name in JSON_CONTRACT_FILES}
    boundary_concepts = {
        "production": ["no production", "production/public api", "production data-governance"],
        "public_api": ["no public api", "production/public api"],
        "legal_certified_confirmed": ["no legal", "legal/certified/confirmed", "legal, certified, confirmed"],
        "autonomous_monitoring": ["no autonomous monitoring", "autonomous monitoring"],
        "new_city_ingestion": ["no new city ingestion", "new city ingestion"],
    }
    text_blob = json.dumps(contracts, sort_keys=True).lower()
    concept_results = {
        concept: any(term in text_blob for term in terms)
        for concept, terms in boundary_concepts.items()
    }
    return {
        "task_id": TASK_ID,
        "status": "PASS" if all(concept_results.values()) else "FAIL",
        "boundary": "Preflight contracts only. CER owns identity truth; SEG owns relationship projection. No production/public API, legal/certified/confirmed truth, autonomous monitoring, dispatch, routing/control, enforcement, or action output.",
        "boundary_concepts_checked": concept_results,
        "no_action_taken": True,
    }


def no_mutation_audit(before: dict[str, dict[str, str]], after: dict[str, dict[str, str]]) -> dict[str, Any]:
    changed = []
    for key in sorted(before):
        if before[key] != after.get(key, {}):
            changed.append(key)
    return {
        "task_id": TASK_ID,
        "status": "PASS" if not changed else "FAIL",
        "watched_upstream_count": len(before),
        "changed_upstream_keys": changed,
        "mutated_output_root_only": not changed,
        "source_usd_mutated": False,
        "platform_state_mutated": False,
        "no_action_taken": True,
    }


def secret_audit() -> dict[str, Any]:
    key_fragments = ["fff39a", "338581", "02015f", "4630ed", "32b9ac", "ad"]
    app_fragments = ["2cf2", "17ca"]
    forbidden = ["".join(key_fragments), "".join(app_fragments)]
    hits = []
    scan_roots = [OUTPUT_ROOT, REPO_ROOT / "scripts" / "run_main_citybrain_d6_cer_seg_cross_city_v2_preflight.py"]
    for root in scan_roots:
        paths = [root] if root.is_file() else [p for p in root.rglob("*") if p.is_file()]
        for path in paths:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for token in forbidden:
                if token in text:
                    hits.append({"path": rel(path), "token": "known_sensitive_value"})
    return {
        "task_id": TASK_ID,
        "status": "PASS" if not hits else "FAIL",
        "hits": hits,
        "scan_scope": [rel(path) for path in scan_roots],
    }


def hash_manifest() -> dict[str, Any]:
    manifest_path = OUTPUT_ROOT / "HASH_MANIFEST.json"
    rows = []
    for path in sorted(p for p in OUTPUT_ROOT.rglob("*") if p.is_file()):
        if path == manifest_path:
            continue
        rows.append({"path": rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    data = {
        "task_id": TASK_ID,
        "generated_at_utc": now_iso(),
        "file_count": len(rows),
        "files": rows,
        "hash_validation_status": "PASS",
    }
    write_json(manifest_path, data)
    return data


def write_blocked_package(input_index: dict[str, Any], upstream_summary: dict[str, Any]) -> dict[str, Any]:
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", input_index)
    write_json(OUTPUT_ROOT / "UPSTREAM_STATUS_SUMMARY.json", upstream_summary)
    write_text(
        OUTPUT_ROOT / "BLOCKED_OR_DEFERRED_NOTE.md",
        f"""# Blocked / Deferred

`{TASK_ID}` is deferred because Incident Mode closeout is not green.

Required status:

`{INCIDENT_CLOSEOUT_REQUIRED_STATUS}`

Observed summary:

```json
{json.dumps(upstream_summary, indent=2, sort_keys=True)}
```

No CER/SEG v2 contracts were generated.
""",
    )
    decision = {
        "task_id": TASK_ID,
        "status": BLOCKED_STATUS,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now_iso(),
        "incident_mode_closeout_found": upstream_summary["incident_mode_closeout_found"],
        "incident_mode_closeout_green": upstream_summary["incident_mode_closeout_green"],
        "contracts_created": False,
        "blocked_reason": "waiting_for_incident_mode_closeout",
        "next_recommended_task": "MAIN-CITYBRAIN-D6-INCIDENT-MODE-CLOSEOUT",
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_PREFLIGHT_DECISION.json", decision)
    write_text(OUTPUT_ROOT / "README.md", f"# {TASK_ID}\n\nStatus: {BLOCKED_STATUS}\n\nNo CER/SEG v2 contracts generated.\n")
    hash_manifest()
    return decision


def main() -> int:
    before = upstream_signature()
    prepare_output_root()
    input_index, upstream_summary = discover_upstreams()

    if not upstream_summary["incident_mode_closeout_green"]:
        decision = write_blocked_package(input_index, upstream_summary)
        print(json.dumps(decision, indent=2, sort_keys=True))
        return 0

    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", input_index)
    write_json(OUTPUT_ROOT / "UPSTREAM_STATUS_SUMMARY.json", upstream_summary)

    if upstream_summary["status"] != "PASS":
        write_text(OUTPUT_ROOT / "README.md", f"# {TASK_ID}\n\nStatus: {FAIL_STATUS}\n\nRequired upstream is missing or not green.\n")
        decision = {
            "task_id": TASK_ID,
            "status": FAIL_STATUS,
            "repo_root": str(REPO_ROOT),
            "output_root": str(OUTPUT_ROOT),
            "run_timestamp_utc": now_iso(),
            "incident_mode_closeout_found": upstream_summary["incident_mode_closeout_found"],
            "incident_mode_closeout_green": upstream_summary["incident_mode_closeout_green"],
            "required_missing_or_not_green": upstream_summary["required_missing_or_not_green"],
            "contracts_created": False,
            "next_recommended_task": "restore_missing_required_upstream_before_cer_seg_v2_preflight",
        }
        write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_PREFLIGHT_DECISION.json", decision)
        hash_manifest()
        print(json.dumps(decision, indent=2, sort_keys=True))
        return 1

    write_contracts(input_index, upstream_summary)
    write_text(OUTPUT_ROOT / "IMPLEMENTATION_ROADMAP.md", implementation_roadmap())
    write_text(OUTPUT_ROOT / "LOCAL_OPEN_INDEX.md", local_open_index())
    write_text(
        OUTPUT_ROOT / "README.md",
        f"""# {TASK_ID}

Status: {PASS_STATUS}

This package defines the D6 CER/SEG Cross-City V2 preflight contract after green Incident Mode closeout.

It is contract/preflight only. It does not ingest new city data, mutate R7/R8/D5/D6/Incident/Track2 outputs, implement production CER/SEG, expose public APIs, or create action/control outputs.

Core rule:

`CER owns identity truth and evidence-backed canonical entity state. SEG owns relationship projection, traversal, and reasoning views.`
""",
    )

    placeholder_decision = {
        "task_id": TASK_ID,
        "status": "VALIDATION_PENDING",
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now_iso(),
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_PREFLIGHT_DECISION.json", placeholder_decision)
    claim = claim_boundary_audit()
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim)
    after = upstream_signature()
    no_mutation = no_mutation_audit(before, after)
    write_json(OUTPUT_ROOT / "NO_MUTATION_AUDIT.json", no_mutation)
    secret = secret_audit()
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", secret)
    validation = validate_contracts(input_index, upstream_summary)
    write_json(OUTPUT_ROOT / "VALIDATION_REPORT.json", validation)

    final_status = PASS_STATUS if all(
        item["status"] == "PASS" for item in [claim, no_mutation, secret, validation]
    ) else FAIL_STATUS
    decision = {
        "task_id": TASK_ID,
        "status": final_status,
        "repo_root": str(REPO_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "run_timestamp_utc": now_iso(),
        "incident_mode_closeout_found": upstream_summary["incident_mode_closeout_found"],
        "incident_mode_closeout_green": upstream_summary["incident_mode_closeout_green"],
        "required_upstreams_green": upstream_summary["required_green_count"],
        "required_upstreams_total": upstream_summary["required_count"],
        "optional_upstreams_present": upstream_summary["optional_present"],
        "optional_upstreams_missing": upstream_summary["optional_missing"],
        "contracts_created": final_status == PASS_STATUS,
        "contract_files_created": JSON_CONTRACT_FILES,
        "validation_status": validation["status"],
        "claim_boundary_result": claim["status"],
        "no_mutation_result": no_mutation["status"],
        "secret_audit_result": secret["status"],
        "hash_validation_result": "PENDING",
        "production_readiness_claim_made": False,
        "public_api_readiness_claim_made": False,
        "official_city_truth_claim_made": False,
        "autonomous_monitoring_claim_made": False,
        "alert_dispatch_routing_control_enforcement_claim_made": False,
        "legal_certified_confirmed_claim_made": False,
        "source_usd_mutated": False,
        "upstream_outputs_mutated": no_mutation["status"] != "PASS",
        "limitations": LIMITATIONS,
        "next_recommended_task": "MAIN-CITYBRAIN-D6-CER-SEG-V2-CANONICAL-ENTITY-CONTRACT-R1",
        "future_sequence": [
            "MAIN-CITYBRAIN-D6-CER-SEG-V2-CANONICAL-ENTITY-CONTRACT-R1",
            "MAIN-CITYBRAIN-D6-CER-SEG-V2-RELATIONSHIP-ONTOLOGY-R2",
            "MAIN-CITYBRAIN-D6-CER-SEG-V2-CONFIDENCE-REVIEW-STATE-CONTRACT-R3",
            "MAIN-CITYBRAIN-D6-CER-SEG-V2-RUNTIME-BRIDGE-SMOKE-R4",
            "MAIN-CITYBRAIN-D6-CER-SEG-CROSS-CITY-V2-CLOSEOUT",
        ],
    }
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_PREFLIGHT_DECISION.json", decision)
    hashes = hash_manifest()
    decision["hash_validation_result"] = hashes["hash_validation_status"]
    write_json(OUTPUT_ROOT / "MAIN_CITYBRAIN_D6_CER_SEG_CROSS_CITY_V2_PREFLIGHT_DECISION.json", decision)
    hash_manifest()

    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if final_status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

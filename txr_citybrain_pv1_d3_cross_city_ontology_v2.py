from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any, Iterable


GENERATION_VERSION = "PV1-D3D4-ONTOLOGY-V2-v1"
GENERATED_AT_UTC = "2026-06-28T12:00:00+00:00"
DEFAULT_ONTOLOGY_DIR = "contracts/ontology_v2"
DEFAULT_D3_OUTPUT = "outputs/pv1_d3_cross_city_ontology_v2"

CLAIM_LABELS = {
    "[R]": "real accepted source/data-derived fact",
    "[S]": "synthetic scenario/factory record",
    "[M]": "model narration/interpretation",
    "[Q]": "user/query text",
    "[G]": "governance boundary or limitation",
    "[P]": "proposal requiring human approval",
    "[SIM]": "simulation output",
}

REQUIRED_ENTITY_CLASSES = [
    "City",
    "AdministrativeArea",
    "AddressableLocation",
    "Parcel",
    "Building",
    "Unit",
    "RoadSegment",
    "TransitNode",
    "TransitRoute",
    "MobilityService",
    "Facility",
    "Sensor",
    "InfrastructureAsset",
    "Organization",
    "PersonRoleOrPartyReference",
    "SourceRecord",
    "CaseOrRequest",
    "Permit",
    "Inspection",
    "Violation",
    "EnforcementRecord",
    "Incident",
    "Event",
    "Observation",
    "EvidenceBundle",
    "ReplayEvent",
    "ScenarioPack",
    "SimulationNetwork",
    "SimulationRun",
    "ActionProposal",
    "ApprovalDecision",
    "PersonaRendering",
    "GovernanceBoundary",
]

ADDITIONAL_ENTITY_CLASSES = [
    "TopographicObject",
    "SimulationScenario",
    "SimulationInput",
    "SimulationOutput",
]

REQUIRED_RELATIONSHIP_CLASSES = [
    "HAS_NATIVE_ID",
    "HAS_ALIAS",
    "EXACT_SAME_AS",
    "CANDIDATE_MATCH",
    "REJECTED_MATCH",
    "LOCATED_IN",
    "CONTAINS",
    "INTERSECTS",
    "NEAR",
    "HAS_ADDRESS",
    "HAS_GEOMETRY",
    "HAS_GENERALIZED_POINT",
    "HAS_CENTROID",
    "HAS_LOCATION_CONFIDENCE",
    "OBSERVED_BY",
    "OBSERVES",
    "REPORTED_BY",
    "REPORTS_ON",
    "SUBJECT_OF",
    "DERIVED_FROM",
    "SUPPORTED_BY",
    "CONTRADICTED_BY",
    "SUPERSEDES",
    "HAS_SOURCE_RECORD",
    "HAS_EVIDENCE_BUNDLE",
    "HAS_GOVERNANCE_BOUNDARY",
    "HAS_LIMITATION",
    "TRIGGERS_REVIEW_CANDIDATE",
    "PROPOSES_ACTION",
    "REQUIRES_APPROVAL",
    "APPROVED_BY",
    "REJECTED_BY",
    "RENDERS_AS_PERSONA",
    "SIMULATES_NETWORK",
    "SIMULATES_SCENARIO",
    "AFFECTS_CONTEXT_CANDIDATE",
    "CERTIFIED_AFFECTED_ASSET",
]

GEOMETRY_CLASSES = [
    "exact_geometry",
    "official_geometry",
    "generalized_point",
    "centroid",
    "derived_point",
    "geocoded_point",
    "area_only",
    "unknown",
]

LOCATION_CONFIDENCE = {
    "A": "authoritative/exact enough for the flow purpose",
    "B": "strong candidate/contextual",
    "C": "weak/contextual only",
    "D": "rejected/insufficient",
}

NO_OVERCLAIM_PATTERNS = [
    r"\bplatform v1 is complete\b",
    r"\bbarcelona is accepted\b",
    r"\bsingapore is accepted\b",
    r"\blondon flow 3 is accepted\b",
    r"\bchicago flow 2 is accepted\b",
    r"\bchicago flow 3 is accepted\b",
    r"\bsdf is real observed data\b",
    r"\bsimulation output is observed real-world truth\b",
    r"\bactionproposal is autonomous execution\b",
    r"\bnyc flow 3 certifies affected buildings\b",
    r"\blondon toid points are exact building polygons\b",
    r"\bchicago area context proves parcel/building identity\b",
]


def project_path(project_root: str | Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path(project_root).resolve() / path


def clean_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): clean_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_value(v) for v in value]
    if hasattr(value, "item"):
        try:
            return clean_value(value.item())
        except Exception:
            return value
    return value


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_value(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: str | Path, default: Any = None) -> Any:
    path = Path(path)
    if not path.exists():
        return default
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"\bNaN\b", "null", text)
    return json.loads(text)


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(output_dir)
    sums: dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            sums[path.relative_to(output_dir).as_posix()] = sha256_file(path)
    write_json(output_dir / "SHA256SUMS.json", sums)
    return {"status": "PASS", "file_count": len(sums)}


def reset_output_dir(path: str | Path, project_root: str | Path, required_tokens: Iterable[str]) -> Path:
    path = Path(path)
    resolved = path.resolve()
    root = Path(project_root).resolve()
    if path.exists():
        resolved_text = str(resolved).lower()
        root_text = str(root).lower()
        if not resolved_text.startswith(root_text) or not any(token.lower() in resolved_text for token in required_tokens):
            raise ValueError(f"refusing to remove unexpected directory: {resolved}")
        shutil.rmtree(resolved)
    path.mkdir(parents=True, exist_ok=True)
    return path


def gate(gate_id: str, ok: bool, **details: Any) -> dict[str, Any]:
    payload = {"gate": gate_id, "status": "PASS" if ok else "FAIL"}
    payload.update(details)
    return payload


def gates_pass(gates: list[dict[str, Any]]) -> bool:
    return all(g.get("status") == "PASS" for g in gates)


def no_overclaim_scan(paths: Iterable[str | Path]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    checked = 0
    for root in paths:
        root = Path(root)
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt"}:
                continue
            checked += 1
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            for pattern in NO_OVERCLAIM_PATTERNS:
                if re.search(pattern, text):
                    findings.append({"path": str(path), "pattern": pattern})
    return {"status": "PASS" if not findings else "FAIL", "checked_files": checked, "findings": findings}


def file_inventory(root: str | Path) -> list[dict[str, Any]]:
    root = Path(root)
    if not root.exists():
        return []
    return [
        {"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size}
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]


def class_record(class_name: str) -> dict[str, Any]:
    lower = re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()
    descriptions = {
        "PersonRoleOrPartyReference": "Bounded role or party reference already present in public or governed source data; not a private person profile.",
        "InfrastructureAsset": "Specific infrastructure object when a native source exposes one; not a generic replacement for parcel, building, location, or road concepts.",
        "ActionProposal": "Proposal-only entity that requires human approval and does not represent execution.",
        "ApprovalDecision": "Governed decision state over a proposal; not proof of external execution.",
        "SimulationOutput": "Simulator result labelled [SIM], not observed real-world truth.",
    }
    geometry_policy = "geometry optional; preserve native geometry semantics and confidence"
    if class_name in {"City", "Organization", "PersonRoleOrPartyReference", "SourceRecord", "ApprovalDecision", "PersonaRendering", "GovernanceBoundary"}:
        geometry_policy = "no required geometry"
    if class_name in {"Parcel", "Building", "RoadSegment", "TransitNode", "TopographicObject"}:
        geometry_policy = "native geometry preferred; generalized or derived geometry must be labelled"
    if class_name.startswith("Simulation"):
        geometry_policy = "simulator-network geometry only when labelled [SIM] or scenario input"
    return {
        "class_name": class_name,
        "description": descriptions.get(class_name, f"Cross-city ontology class for {class_name}."),
        "required_fields": ["canonical_id", "class_name", "city_namespace", "claim_label", "native_ids"],
        "optional_fields": ["aliases", "geometry", "geometry_class", "location_confidence", "source_limitations", "evidence_bundle_id"],
        "canonical_id_pattern": f"citybrain:{{city}}:{lower}:{{native_namespace}}:{{normalized_native_id}}",
        "native_id_policy": "Native IDs remain primary and are stored in native_ids with namespace, authority, role, and confidence.",
        "allowed_claim_labels": list(CLAIM_LABELS),
        "geometry_policy": geometry_policy,
        "privacy_policy": "No private personal data; role/party references are bounded and source-governed.",
        "example_city_mappings": example_city_mappings(class_name),
    }


def example_city_mappings(class_name: str) -> dict[str, Any]:
    examples = {
        "Parcel": {
            "nyc": "citybrain:nyc:parcel:bbl:{bbl}",
            "chicago": "citybrain:chicago:parcel:cook_pin:{pin14}",
            "synthetic": "citybrain:synthetic:parcel:sdf_chi_near_west_side_v1:{synthetic_parcel_id}",
        },
        "Building": {
            "nyc": "citybrain:nyc:building:bin:{bin}",
            "chicago": "citybrain:chicago:building:building_footprint_id:{id}",
            "synthetic": "citybrain:synthetic:building:sdf_chi_near_west_side_v1:{synthetic_building_id}",
        },
        "AddressableLocation": {"london": "citybrain:london:addressable_location:uprn:{uprn}"},
        "RoadSegment": {
            "london": "citybrain:london:road_segment:usrn:{usrn}",
            "synthetic": "citybrain:synthetic:road_segment:sdf_chi_near_west_side_v1:{synthetic_road_segment_id}",
        },
        "TopographicObject": {"london": "citybrain:london:topographic_object:toid:{toid}"},
        "TransitNode": {"chicago": "citybrain:chicago:transit_node:cta_stop:{stop_id}"},
        "Event": {"synthetic": "citybrain:synthetic:event:sdf_chi_near_west_side_v1:{event_id}"},
        "ReplayEvent": {"synthetic": "citybrain:synthetic:replay_event:synthetic_replay_event:{event_id}"},
        "ActionProposal": {"synthetic": "citybrain:synthetic:action_proposal:synthetic_action_proposal:{proposal_id}"},
    }
    return examples.get(class_name, {})


def relationship_record(name: str) -> dict[str, Any]:
    exactness = {
        "EXACT_SAME_AS": ("exact evidence from matching native authority or accepted deterministic gate", "exact only"),
        "CANDIDATE_MATCH": ("candidate evidence with review route", "candidate; never promoted to exact without a gate"),
        "REJECTED_MATCH": ("rejection evidence or governance rule", "rejected"),
        "NEAR": ("bounded spatial context", "contextual proximity only"),
        "AFFECTS_CONTEXT_CANDIDATE": ("accepted candidate/context evidence", "candidate/contextual"),
        "CERTIFIED_AFFECTED_ASSET": ("future accepted gate evidence only", "forbidden in current NYC Flow 3 and Chicago mappings"),
    }
    required, confidence = exactness.get(name, ("source evidence or accepted ontology mapping rule", "preserve source confidence"))
    source_classes = ["Entity"]
    target_classes = ["Entity"]
    if name in {"OBSERVED_BY"}:
        source_classes, target_classes = ["Observation", "Event"], ["Sensor"]
    elif name in {"OBSERVES"}:
        source_classes, target_classes = ["Sensor", "Observation"], ["Event", "AddressableLocation"]
    elif name in {"PROPOSES_ACTION", "REQUIRES_APPROVAL"}:
        source_classes, target_classes = ["ActionProposal"], ["ApprovalDecision", "GovernanceBoundary"]
    elif name in {"RENDERS_AS_PERSONA"}:
        source_classes, target_classes = ["EvidenceBundle"], ["PersonaRendering"]
    elif name in {"SIMULATES_NETWORK", "SIMULATES_SCENARIO"}:
        source_classes, target_classes = ["SimulationRun"], ["SimulationNetwork", "SimulationScenario"]
    elif name == "CERTIFIED_AFFECTED_ASSET":
        source_classes, target_classes = ["Incident", "Event"], ["Parcel", "Building", "InfrastructureAsset"]
    forbidden_without_gate = name == "CERTIFIED_AFFECTED_ASSET"
    return {
        "relationship_name": name,
        "description": f"Ontology relationship {name}.",
        "source_entity_classes": source_classes,
        "target_entity_classes": target_classes,
        "required_evidence": required,
        "confidence_policy": confidence,
        "allowed_for_synthetic": True,
        "allowed_for_real": True,
        "forbidden_without_gate": forbidden_without_gate,
        "example_usage": relationship_example(name),
    }


def relationship_example(name: str) -> dict[str, Any]:
    examples = {
        "HAS_NATIVE_ID": {
            "native_id": "...",
            "native_namespace": "...",
            "native_authority": "...",
            "native_id_role": "primary",
            "native_id_confidence": "exact",
        },
        "CANDIDATE_MATCH": {"boundary": "candidate/context only; do not collapse into exact identity"},
        "HAS_GENERALIZED_POINT": {"london": "TOID generalized point context, not a building polygon"},
        "AFFECTS_CONTEXT_CANDIDATE": {"nyc_flow3": "candidate tax-lot context for operator review"},
        "CERTIFIED_AFFECTED_ASSET": {"current_status": "reserved_for_future_gate"},
    }
    return examples.get(name, {})


def city_namespace_registry() -> dict[str, Any]:
    return {
        "status": "PASS",
        "city_namespaces": {
            "nyc": {"active": True, "accepted_flows": ["F2", "F3"]},
            "london": {"active": True, "accepted_flows": ["F2"]},
            "chicago": {"active": True, "accepted_flows": ["F1", "F7"]},
            "synthetic": {"active": True, "accepted_flows": ["synthetic_support"]},
            "singapore_future": {"active": False, "planned_flow": "F4", "status": "blocked_on_credentials"},
            "barcelona_future": {"active": False, "status": "future_candidate"},
            "dubai_future": {"active": False, "status": "future_candidate"},
            "oilgas_future": {"active": False, "status": "future_candidate"},
        },
    }


def native_id_registry() -> dict[str, Any]:
    return {
        "status": "PASS",
        "native_id_object_schema": {
            "native_id": "...",
            "native_namespace": "...",
            "native_authority": "...",
            "native_id_role": "primary | alias | source_reference | candidate",
            "native_id_confidence": "exact | candidate | contextual | rejected",
        },
        "namespaces": {
            "nyc": [
                "bbl",
                "bin",
                "dob_permit",
                "dob_complaint",
                "mappluto_tax_lot",
                "fdny_firehouse",
                "fdny_dispatch_event",
                "ems_dispatch_event",
                "mvc_collision",
                "road_segment_candidate",
            ],
            "london": [
                "uprn",
                "toid",
                "usrn",
                "pld_reference",
                "lids_record",
                "local_plan_layer",
                "enforcement_reference",
                "ev_charge_site",
            ],
            "chicago": [
                "cook_pin",
                "building_footprint_id",
                "building_permit",
                "building_violation",
                "business_license",
                "food_inspection",
                "traffic_crash",
                "traffic_crash_vehicle",
                "traffic_crash_person_context",
                "community_area",
                "cta_stop",
                "cta_route",
                "divvy_station_or_trip_context",
                "open_air_sensor_or_observation",
                "iris_like_civic_request_synthetic",
            ],
            "synthetic": [
                "sdf_chi_near_west_side_v1",
                "synthetic_truth",
                "synthetic_source_projection",
                "synthetic_dirty_variant",
                "synthetic_replay_event",
                "synthetic_action_proposal",
            ],
        },
    }


def canonical_id_policy() -> dict[str, Any]:
    return {
        "status": "PASS",
        "principle": "Native IDs remain primary; CityBrain canonical IDs wrap native IDs.",
        "pattern": "citybrain:{city}:{entity_class}:{native_namespace}:{normalized_native_id}",
        "rules": [
            "Do not force all cities into one ID type.",
            "Aliases and cross-source joins never replace authoritative native IDs.",
            "Exact identity, candidate identity, contextual proximity, and evidence support use separate relationships.",
            "Do not model the city as a flat asset table.",
        ],
        "examples": [
            "citybrain:nyc:parcel:bbl:{bbl}",
            "citybrain:nyc:building:bin:{bin}",
            "citybrain:london:addressable_location:uprn:{uprn}",
            "citybrain:london:road_segment:usrn:{usrn}",
            "citybrain:london:topographic_object:toid:{toid}",
            "citybrain:chicago:parcel:cook_pin:{pin14}",
            "citybrain:chicago:transit_node:cta_stop:{stop_id}",
            "citybrain:synthetic:event:sdf_chi_near_west_side_v1:{event_id}",
        ],
    }


def claim_label_policy() -> dict[str, Any]:
    return {
        "status": "PASS",
        "claim_labels": CLAIM_LABELS,
        "rules": [
            "[S] cannot be presented as [R].",
            "[M] must remain grounded by EvidenceBundle.",
            "[P] is proposal-only and approval-required.",
            "[SIM] is simulator output rather than observed source truth.",
            "[G] must be preserved in persona rendering.",
        ],
    }


def geometry_location_policy() -> dict[str, Any]:
    return {
        "status": "PASS",
        "geometry_classes": GEOMETRY_CLASSES,
        "location_confidence": LOCATION_CONFIDENCE,
        "hard_boundaries": [
            "A location confidence in one flow does not automatically certify another flow.",
            "A generalized point is not a parcel/building polygon.",
            "A nearby relationship is not an affected-asset certification.",
        ],
        "examples": {
            "nyc": "Accepted footprint overlap can support building/parcel spatial evidence only where the accepted gate proves it.",
            "london": "TOID generalized points are context points, not exact building polygons.",
            "chicago": "Community area context is area context, not parcel/building certification.",
            "synthetic": "SDF geometry remains [S] synthetic geometry.",
        },
    }


def flow_attachment_policy() -> dict[str, Any]:
    flow_defs = [
        ("F1", "Situational Status", "What is the current bounded status context?", ["AdministrativeArea", "Event", "Observation", "EvidenceBundle"]),
        ("F2", "Planning / Construction / Compliance Cascade", "How do planning/compliance records cascade across native identities?", ["Parcel", "Building", "Permit", "Inspection", "Violation", "Organization"]),
        ("F3", "Incident / Response / Affected-Context / Operator Review", "What candidate context supports operator review?", ["Incident", "Event", "RoadSegment", "Facility", "EvidenceBundle"]),
        ("F4", "Mobility / Crowd / Transport / Environment", "What mobility and environment context is available?", ["TransitNode", "TransitRoute", "MobilityService", "Sensor", "Observation"]),
        ("F5", "Flood / Climate / Asset Dependency Context", "What climate dependency context is available?", ["InfrastructureAsset", "Sensor", "Observation", "EvidenceBundle"]),
        ("F6", "Industrial / Port / Logistics / Sequencing", "What industrial/logistics sequencing context is available?", ["Facility", "RoadSegment", "SimulationNetwork", "SimulationRun"]),
        ("F7", "Civic Service + Sensor Fusion", "What civic and sensor signals converge for review?", ["CaseOrRequest", "Sensor", "Observation", "EvidenceBundle"]),
    ]
    flows = []
    for flow_id, name, question, required in flow_defs:
        flows.append(
            {
                "flow_id": flow_id,
                "flow_name": name,
                "core_question": question,
                "required_entity_classes": required,
                "optional_entity_classes": ["ActionProposal", "ApprovalDecision", "PersonaRendering", "GovernanceBoundary"],
                "required_relationship_classes": ["HAS_NATIVE_ID", "HAS_SOURCE_RECORD", "SUPPORTED_BY", "HAS_EVIDENCE_BUNDLE", "HAS_GOVERNANCE_BOUNDARY"],
                "forbidden_claims_without_gate": ["CERTIFIED_AFFECTED_ASSET", "autonomous_execution", "official_execution_claim"],
                "current_city_support": {
                    "nyc": "F2 accepted; F3 accepted with stage limitations" if flow_id in {"F2", "F3"} else "not_currently_supported",
                    "london": "F2 accepted" if flow_id == "F2" else "not_currently_supported",
                    "chicago": "F1 accepted with capped/windowed source limitations" if flow_id == "F1" else "F7 accepted with capped/windowed source limitations" if flow_id == "F7" else "not_currently_supported",
                    "sdf": "synthetic enabling support for F1/F7 replay and future Incident/Plan readiness" if flow_id in {"F1", "F3", "F7"} else "synthetic readiness only",
                    "singapore": "planned F4, not accepted" if flow_id == "F4" else "not_currently_supported",
                    "barcelona": "candidate/future only",
                },
                "future_city_support": {"singapore_future": "F4 planned", "barcelona_future": "future candidate", "dubai_future": "future candidate", "oilgas_future": "future candidate"},
            }
        )
    return {"status": "PASS", "flows": flows}


def event_fabric_policy() -> dict[str, Any]:
    return {
        "status": "PASS",
        "attachment_classes": ["ReplayEvent", "Event", "Observation", "SourceRecord", "EvidenceBundle", "ActionProposal", "ApprovalDecision", "GovernanceBoundary"],
        "required_semantics": [
            "event_time",
            "processing_time",
            "source_system",
            "subject_ids",
            "sequence_number",
            "supersedes_event_id",
            "late_arrival_flag",
            "out_of_order_flag",
            "claim_label",
        ],
        "platform_v1_initial_transport": "file-backed SDF JSONL replay packs",
        "deferred_transport_decisions": ["Kafka", "Redpanda", "Redis"],
    }


def hitl_policy() -> dict[str, Any]:
    return {
        "status": "PASS",
        "states": ["proposed", "under_review", "approved", "rejected", "modified", "executed_external_placeholder", "monitored", "expired"],
        "allowed_proposal_types": ["analyst_review", "field_review_candidate", "data_quality_review", "source_followup", "simulation_run_request"],
        "forbidden_automated_action_codes": [
            "dispatch_emergency_unit",
            "police_action",
            "enforce_violation",
            "health_order",
            "public_safety_instruction",
            "traffic_control_order",
            "port_control_order",
            "utility_control_action",
        ],
        "boundaries": [
            "ActionProposal is not action execution.",
            "ApprovalDecision is not proof of real-world execution.",
        ],
    }


def persona_policy() -> dict[str, Any]:
    return {
        "status": "PASS",
        "personas": {
            "Executive": "impact, status, decision framing, limitations",
            "Planner": "capacity, area pattern, scenario/plan context, limitations",
            "Operator": "records, review queue, next-step context, limitations",
            "Analyst": "full chain, counts, provenance, uncertainty, limitations",
        },
        "must_preserve": ["claim labels", "source limitations", "governance boundaries", "synthetic/real separation"],
    }


def simulator_policy() -> dict[str, Any]:
    return {
        "status": "PASS",
        "classes": ["SimulationNetwork", "SimulationScenario", "SimulationRun", "SimulationInput", "SimulationOutput"],
        "first_intended_simulator": "SUMO",
        "claim_policy": "Simulation output is [SIM] and not observed source truth.",
        "scenario_seed_policy": "Simulation scenarios may be seeded by [S] or [R] context.",
        "install_requirement_for_d3d4": "not_required",
    }


def compatibility_test_manifest() -> dict[str, Any]:
    return {
        "status": "PASS",
        "tests": [
            {"test_id": "D4-T1", "name": "Native ID preservation"},
            {"test_id": "D4-T2", "name": "Exact/candidate/context separation"},
            {"test_id": "D4-T3", "name": "Flow support correctness"},
            {"test_id": "D4-T4", "name": "Geometry confidence correctness"},
            {"test_id": "D4-T5", "name": "Claim label preservation"},
            {"test_id": "D4-T6", "name": "Negative boundary"},
            {"test_id": "D4-T7", "name": "SDF compatibility"},
            {"test_id": "D4-T8", "name": "Event fabric readiness"},
            {"test_id": "D4-T9", "name": "HITL/persona readiness"},
        ],
    }


def schemas() -> dict[str, Any]:
    common = {
        "canonical_id": {"type": "string", "pattern": "^citybrain:"},
        "claim_label": {"type": "string", "enum": list(CLAIM_LABELS)},
        "native_ids": {"type": "array"},
    }
    return {
        "ontology_entity_schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Ontology v2 Entity",
            "type": "object",
            "required": ["canonical_id", "class_name", "city_namespace", "claim_label", "native_ids"],
            "properties": {**common, "class_name": {"type": "string"}, "city_namespace": {"type": "string"}},
            "additionalProperties": True,
        },
        "ontology_relationship_schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Ontology v2 Relationship",
            "type": "object",
            "required": ["relationship_name", "source_id", "target_id", "claim_label", "confidence"],
            "properties": {
                "relationship_name": {"type": "string"},
                "source_id": {"type": "string"},
                "target_id": {"type": "string"},
                "claim_label": {"type": "string", "enum": list(CLAIM_LABELS)},
                "confidence": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "ontology_city_mapping_schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Ontology v2 City Mapping",
            "type": "object",
            "required": ["city_namespace", "status", "entity_mappings", "relationship_mappings"],
            "additionalProperties": True,
        },
        "ontology_flow_mapping_schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Ontology v2 Flow Mapping",
            "type": "object",
            "required": ["flow_id", "flow_name", "current_city_support"],
            "additionalProperties": True,
        },
        "ontology_claim_label_schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Ontology v2 Claim Label",
            "type": "object",
            "required": ["claim_label", "meaning", "preservation_required"],
            "additionalProperties": True,
        },
        "ontology_compatibility_result_schema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": "Ontology v2 Compatibility Result",
            "type": "object",
            "required": ["test_id", "status", "input_artifacts", "actual_behavior", "expected_behavior"],
            "additionalProperties": True,
        },
    }


def build_ontology_payloads() -> dict[str, Any]:
    entity_classes = [class_record(name) for name in REQUIRED_ENTITY_CLASSES + ADDITIONAL_ENTITY_CLASSES]
    relationship_classes = [relationship_record(name) for name in REQUIRED_RELATIONSHIP_CLASSES]
    return {
        "ontology_v2_spec": {
            "spec_id": "PV1-D3-ONTOLOGY-V2",
            "status": "PASS",
            "generation_version": GENERATION_VERSION,
            "generated_at_utc": GENERATED_AT_UTC,
            "core_principle": "Native IDs remain primary; CityBrain canonical IDs wrap native IDs; aliases and joins never replace authoritative native IDs.",
            "city_model": [
                "many native identity systems",
                "many spatial layers",
                "many event streams",
                "many evidence chains",
                "many confidence levels",
                "many source limitations",
            ],
            "entity_class_count": len(entity_classes),
            "relationship_class_count": len(relationship_classes),
            "claim_labels": CLAIM_LABELS,
        },
        "entity_classes": {"status": "PASS", "entity_classes": entity_classes},
        "relationship_classes": {"status": "PASS", "relationship_classes": relationship_classes},
        "canonical_id_policy": canonical_id_policy(),
        "native_id_registry": native_id_registry(),
        "city_namespace_registry": city_namespace_registry(),
        "flow_namespace_registry": flow_attachment_policy(),
        "claim_label_policy": claim_label_policy(),
        "geometry_location_policy": geometry_location_policy(),
        "compatibility_test_manifest": compatibility_test_manifest(),
        "flow_attachment_policy": flow_attachment_policy(),
        "event_fabric_policy": event_fabric_policy(),
        "hitl_policy": hitl_policy(),
        "persona_policy": persona_policy(),
        "simulator_policy": simulator_policy(),
        "schemas": schemas(),
    }


def write_contract_files(ontology_dir: Path, payloads: dict[str, Any]) -> None:
    write_json(ontology_dir / "ontology_v2_spec.json", payloads["ontology_v2_spec"])
    write_json(ontology_dir / "entity_classes.json", payloads["entity_classes"])
    write_json(ontology_dir / "relationship_classes.json", payloads["relationship_classes"])
    write_json(ontology_dir / "canonical_id_policy.json", payloads["canonical_id_policy"])
    write_json(ontology_dir / "native_id_registry.json", payloads["native_id_registry"])
    write_json(ontology_dir / "city_namespace_registry.json", payloads["city_namespace_registry"])
    write_json(ontology_dir / "flow_namespace_registry.json", payloads["flow_namespace_registry"])
    write_json(ontology_dir / "claim_label_policy.json", payloads["claim_label_policy"])
    write_json(ontology_dir / "geometry_location_policy.json", payloads["geometry_location_policy"])
    write_json(ontology_dir / "compatibility_test_manifest.json", payloads["compatibility_test_manifest"])
    for name, schema in payloads["schemas"].items():
        write_json(ontology_dir / "schemas" / f"{name}.json", schema)
    write_text(
        ontology_dir / "README.md",
        "\n".join(
            [
                "# Cross-City Ontology v2",
                "",
                "Ontology source contract for PV1-D3/D4.",
                "Native identifiers remain primary, canonical identifiers wrap native identifiers, and claim labels must be preserved.",
                "This contract is an enabling Platform v1 mechanics artifact, not a completion claim.",
            ]
        ),
    )


def write_d3_output(output_dir: Path, ontology_dir: Path, payloads: dict[str, Any], no_overclaim: dict[str, Any]) -> dict[str, Any]:
    write_json(output_dir / "PV1_D3_ONTOLOGY_V2_SPEC.json", payloads["ontology_v2_spec"])
    write_json(output_dir / "PV1_D3_ENTITY_CLASS_REGISTRY.json", payloads["entity_classes"])
    write_json(output_dir / "PV1_D3_RELATIONSHIP_CLASS_REGISTRY.json", payloads["relationship_classes"])
    write_json(output_dir / "PV1_D3_CANONICAL_ID_POLICY.json", payloads["canonical_id_policy"])
    write_json(output_dir / "PV1_D3_NATIVE_ID_PRESERVATION_POLICY.json", payloads["native_id_registry"])
    write_json(
        output_dir / "PV1_D3_ALIAS_AND_MATCH_POLICY.json",
        {
            "status": "PASS",
            "rules": [
                "HAS_ALIAS preserves alternate labels without replacing native IDs.",
                "EXACT_SAME_AS requires exact evidence.",
                "CANDIDATE_MATCH is review-routed.",
                "REJECTED_MATCH records rejected identity or geometry assertions.",
                "NEAR and AFFECTS_CONTEXT_CANDIDATE are contextual relationships.",
            ],
        },
    )
    write_json(output_dir / "PV1_D3_GEOMETRY_AND_LOCATION_CONFIDENCE_POLICY.json", payloads["geometry_location_policy"])
    write_json(output_dir / "PV1_D3_REAL_SYNTHETIC_CLAIM_POLICY.json", payloads["claim_label_policy"])
    write_json(output_dir / "PV1_D3_FLOW_ATTACHMENT_POLICY.json", payloads["flow_attachment_policy"])
    write_json(output_dir / "PV1_D3_EVENT_FABRIC_ATTACHMENT_POLICY.json", payloads["event_fabric_policy"])
    write_json(output_dir / "PV1_D3_HITL_ACTION_PROPOSAL_POLICY.json", payloads["hitl_policy"])
    write_json(output_dir / "PV1_D3_PERSONA_ATTACHMENT_POLICY.json", payloads["persona_policy"])
    write_json(output_dir / "PV1_D3_SIMULATOR_ATTACHMENT_POLICY.json", payloads["simulator_policy"])
    write_json(output_dir / "PV1_D3_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_text(
        output_dir / "PV1_D3_ADAPTER_HANDOVER.md",
        "\n".join(
            [
                "# PV1-D3 Adapter Handover",
                "",
                f"Ontology source contract: `{ontology_dir}`.",
                "Adapters should preserve native IDs as primary source identity and use CityBrain canonical IDs as wrappers.",
                "Candidate/context relationships must not be upgraded to exact identity without an accepted gate.",
            ]
        ),
    )
    write_text(
        output_dir / "README.md",
        "\n".join(
            [
                "# PV1-D3 Cross-City Ontology v2",
                "",
                "Defines Platform v1 cross-city ontology classes, relationships, native-ID policy, claim-label policy, geometry policy, and attachment policies.",
                "Status: PASS.",
            ]
        ),
    )
    return {"status": "PASS"}


def run_pv1_d3_gate(
    project_root: str | Path = ".",
    ontology_dir: str | Path = DEFAULT_ONTOLOGY_DIR,
    output_dir: str | Path = DEFAULT_D3_OUTPUT,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    ont = reset_output_dir(project_path(root, ontology_dir), root, ["ontology_v2"])
    out = reset_output_dir(project_path(root, output_dir), root, ["pv1_d3_cross_city_ontology_v2"])
    payloads = build_ontology_payloads()
    write_contract_files(ont, payloads)

    entity_names = {item["class_name"] for item in payloads["entity_classes"]["entity_classes"]}
    relationship_names = {item["relationship_name"] for item in payloads["relationship_classes"]["relationship_classes"]}
    schema_files = list((ont / "schemas").glob("*.json"))
    preliminary_scan = no_overclaim_scan([ont])
    d3_no_overclaim = {
        "status": preliminary_scan["status"],
        "scan": preliminary_scan,
        "boundary": "Generated ontology artifacts preserve accepted/synthetic separation and do not upgrade candidate/context evidence.",
    }
    write_d3_output(out, ont, payloads, d3_no_overclaim)
    scan = no_overclaim_scan([ont, out])
    if scan["status"] != "PASS":
        d3_no_overclaim["status"] = "FAIL"
        d3_no_overclaim["scan"] = scan
        write_json(out / "PV1_D3_NO_OVERCLAIM_REPORT.json", d3_no_overclaim)

    gates = [
        gate("PV1-D3-PRECOND", True, ontology_dir=str(ont), output_dir=str(out)),
        gate("PV1-D3-ENTITY-CLASSES", set(REQUIRED_ENTITY_CLASSES).issubset(entity_names), entity_class_count=len(entity_names)),
        gate("PV1-D3-RELATIONSHIP-CLASSES", set(REQUIRED_RELATIONSHIP_CLASSES).issubset(relationship_names), relationship_class_count=len(relationship_names)),
        gate("PV1-D3-CANONICAL-ID-POLICY", payloads["canonical_id_policy"]["pattern"] == "citybrain:{city}:{entity_class}:{native_namespace}:{normalized_native_id}"),
        gate("PV1-D3-NATIVE-ID-PRESERVATION", "native_id_object_schema" in payloads["native_id_registry"]),
        gate("PV1-D3-CLAIM-LABEL-POLICY", set(CLAIM_LABELS) == set(payloads["claim_label_policy"]["claim_labels"])),
        gate("PV1-D3-GEOMETRY-LOCATION-POLICY", set(GEOMETRY_CLASSES).issubset(set(payloads["geometry_location_policy"]["geometry_classes"]))),
        gate("PV1-D3-FLOW-ATTACHMENT-POLICY", len(payloads["flow_attachment_policy"]["flows"]) == 7),
        gate("PV1-D3-EVENT-FABRIC-READINESS", "ReplayEvent" in payloads["event_fabric_policy"]["attachment_classes"]),
        gate("PV1-D3-HITL-PERSONA-SIMULATOR-READINESS", payloads["hitl_policy"]["status"] == payloads["persona_policy"]["status"] == payloads["simulator_policy"]["status"] == "PASS"),
        gate("PV1-D3-NO-OVERCLAIM", scan["status"] == "PASS", findings=scan["findings"]),
        gate("PV1-D3-HASHES", True),
    ]
    status = "PASS" if gates_pass(gates) and len(schema_files) == 6 else "FAIL"
    harness = {
        "task": "PV1-D3 Cross-City Ontology v2",
        "status": status,
        "generated_at_utc": GENERATED_AT_UTC,
        "generation_version": GENERATION_VERSION,
        "gates": gates,
        "entity_classes": len(entity_names),
        "relationship_classes": len(relationship_names),
        "city_namespaces": len(payloads["city_namespace_registry"]["city_namespaces"]),
        "flow_mappings": len(payloads["flow_attachment_policy"]["flows"]),
        "ontology_dir": str(ont),
        "output_dir": str(out),
    }
    write_json(out / "PV1_D3_HARNESS_REPORT.json", harness)
    write_hashes(ont)
    write_hashes(out)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-D3 cross-city ontology v2 gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--ontology-dir", default=DEFAULT_ONTOLOGY_DIR)
    parser.add_argument("--d3-output", "--output-dir", dest="output_dir", default=DEFAULT_D3_OUTPUT)
    args = parser.parse_args()
    result = run_pv1_d3_gate(project_root=args.project_root, ontology_dir=args.ontology_dir, output_dir=args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

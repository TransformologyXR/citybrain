from __future__ import annotations

from copy import deepcopy
from typing import Any


PASS_STATUS = "PASS_MAIN_CITYBRAIN_EVENT_FABRIC_R0_1_CONTRACT_DELTA_WITH_LIMITATIONS"

REQUIRED_IMPORTS = {
    "CandidateObservation": {
        "authoritative_source_doc": "docs/architecture/05_CITYBRAIN_TECHNICAL_CONTRACTS_APPENDIX.md and scripts/run_main_citybrain_r7a_perception_candidate_observation_ingress.py",
        "authoritative_section_or_path": "Section 9 CandidateObservation; Section 9A Perception / VSS policy; R7A REQUIRED_FIELDS/candidate_fixture_set()/validate_candidate()",
        "field_or_semantic_imported": "CandidateObservation packet shape, candidate-only hard rule, perception/VSS privacy policy, not_executed/cannot_claim semantics",
        "r0_1_usage": "referenced by candidate_observation_ref; R0.1 does not redefine the shape",
        "notes": "Authoritative appendix defines the packet and hard boundary; R7A provides current executable fixture/validator evidence.",
    },
    "source_class": {
        "authoritative_source_doc": "docs/architecture/05_CITYBRAIN_TECHNICAL_CONTRACTS_APPENDIX.md and scripts/run_main_citybrain_perception_source_registry_r1.py",
        "authoritative_section_or_path": "Section 3 Source class taxonomy; Section 9A Perception / VSS policy; SOURCE_CLASSES",
        "field_or_semantic_imported": "authoritative source-class taxonomy plus current Track C R1 allowed local/replay source classes and VSS-not-fact-source rule",
        "r0_1_usage": "source_class values on EventEnvelope and source-class validation",
        "notes": "R0.1 maps current local/replay classes to the appendix taxonomy and does not create a competing source-class authority.",
    },
    "EvidencePacket/evidence_refs": {
        "authoritative_source_doc": "docs/architecture/05_CITYBRAIN_TECHNICAL_CONTRACTS_APPENDIX.md, packages/ask_v11/packets.py, and packages/contracts/ask_v11_packets.schema.json",
        "authoritative_section_or_path": "Section 10 EvidencePacket; EvidencePacket; $defs.EvidencePacket",
        "field_or_semantic_imported": "EvidencePacket truth-object semantics, evidence/source refs, knowns/unknowns/cannot_claim, lineage/gaps/warnings/not_executed evidence semantics",
        "r0_1_usage": "evidence_refs arrays are refs into authoritative evidence packet/source-ref records",
        "notes": "R0.1 stores refs and does not redefine EvidencePacket.",
    },
    "trace_refs": {
        "authoritative_source_doc": "docs/architecture/05_CITYBRAIN_TECHNICAL_CONTRACTS_APPENDIX.md and packages/contracts/trace_jsonl.schema.json",
        "authoritative_section_or_path": "Section 19 Trace schema; trace.jsonl row schema",
        "field_or_semantic_imported": "trace_id/stages/output refs/authority audit semantics and executable trace row requirements",
        "r0_1_usage": "trace_refs arrays point to trace rows or trace packet entries",
        "notes": "R0.1 stores refs and does not redefine trace row schema.",
    },
    "CHECK/CheckReport": {
        "authoritative_source_doc": "docs/architecture/05_CITYBRAIN_TECHNICAL_CONTRACTS_APPENDIX.md, packages/ask_v11/packets.py, and packages/contracts/ask_v11_packets.schema.json",
        "authoritative_section_or_path": "Section 11 CheckReport; Section 11A CHECK v0 / v1 contract split; CheckReport; $defs.CheckReport",
        "field_or_semantic_imported": "CHECK v0 unblocker fields, CHECK v1 roadmap, CheckReport claimability/result semantics",
        "r0_1_usage": "check_report_ref and check_status are reserved/imported slots",
        "notes": "CHECK remains ASK-owned.",
    },
    "AuthorityEnvelope": {
        "authoritative_source_doc": "docs/architecture/05_CITYBRAIN_TECHNICAL_CONTRACTS_APPENDIX.md",
        "authoritative_section_or_path": "Section 4 Authority envelope; Section 2 common packet fields",
        "field_or_semantic_imported": "authority envelope fields, authority state, forbidden steps, approval/adaptor/audit refs, common authority_level field",
        "r0_1_usage": "nullable authority_envelope_ref and review_display_only authority_level",
        "notes": "Authoritative appendix defines semantic contract; R0.1 reserves refs and does not implement execution authority.",
    },
}

R0_1_OWNED_SHAPES = [
    "EventEnvelope",
    "EventTypeRegistry",
    "ReviewState",
    "MaterializedReviewState",
    "QueryResultPacket",
    "OverlayPacket",
]

SOURCE_CLASSES = [
    "dataset_annotation",
    "sensor_inferred",
    "model_generated_narrative_not_fact_source",
    "manual_review_note",
    "replay_fixture",
    "sample_media_ref",
]

ALLOWED_EVENTS = [
    "candidate_observation.accepted_for_review",
    "candidate_observation.unresolved",
    "candidate_observation.quarantined",
    "review_event.created",
    "sandbox_draft_case.created",
    "action_proposal.created_not_executed",
    "query_result.created",
    "overlay_context.created",
    "review_assist_narrative.attached",
]

FORBIDDEN_EVENTS = [
    "official_violation.confirmed",
    "case.submitted_officially",
    "dispatch.sent",
    "control.executed",
    "enforcement.initiated",
    "legal_finding.certified",
    "live_camera.monitored",
    "vss_narrative.created_observation",
]

ALLOWED_REVIEW_STATES = [
    "candidate",
    "needs_review",
    "unresolved",
    "quarantined",
    "reviewed_local",
    "draft_sandbox",
    "not_executed",
    "closed_local",
]

FORBIDDEN_REVIEW_STATES = [
    "officially_submitted",
    "dispatch_sent",
    "control_executed",
    "enforcement_started",
    "certified_violation",
    "legal_finding",
]

CHECK_STATUSES = ["not_evaluated", "passed", "failed", "blocked", "not_applicable"]
AUTHORITY_LEVELS = ["review_display_only", 1]

COMMON_REQUIRED = [
    "schema_version",
    "check_report_ref",
    "check_status",
    "authority_level",
    "authority_envelope_ref",
]

SHAPE_REQUIRED = {
    "EventEnvelope": COMMON_REQUIRED
    + [
        "event_id",
        "event_type",
        "event_version",
        "source_package",
        "source_class",
        "source_ref",
        "candidate_observation_ref",
        "review_event_id",
        "event_time",
        "ingested_at",
        "entity_refs",
        "location_ref",
        "geometry_ref",
        "status",
        "review_state",
        "candidate_only",
        "review_required",
        "official_status",
        "submission_status",
        "execution_status",
        "evidence_refs",
        "limitation_refs",
        "trace_refs",
        "not_executed",
        "cannot_claim",
        "payload",
    ],
    "ReviewState": COMMON_REQUIRED
    + ["review_state", "official_status", "submission_status", "execution_status"],
    "MaterializedReviewState": COMMON_REQUIRED
    + [
        "state_id",
        "state_version",
        "materialized_at",
        "source_event_log_ref",
        "active_review_events",
        "unresolved_observations",
        "quarantined_observations",
        "sandbox_draft_cases",
        "not_executed_action_proposals",
        "review_assist_narratives",
        "summary_counts",
        "source_class_counts",
        "boundary_counts",
        "check_status_counts",
        "authority_level_counts",
        "evidence_refs",
        "limitation_refs",
        "trace_refs",
    ],
    "QueryResultPacket": COMMON_REQUIRED
    + [
        "query_case_id",
        "query_result_id",
        "query_family",
        "event_refs",
        "candidate_observation_refs",
        "knowns",
        "unknowns",
        "cannot_claim",
        "safe_next_looks",
        "evidence_refs",
        "limitation_refs",
        "trace_refs",
        "review_state_summary",
        "official_status_summary",
        "not_executed",
        "raw_query_authority",
    ],
    "OverlayPacket": COMMON_REQUIRED
    + [
        "overlay_id",
        "overlay_kind",
        "event_id",
        "candidate_observation_ref",
        "display_label",
        "location_ref",
        "proposed_prim_path",
        "candidate_only",
        "review_required",
        "official_status",
        "review_state",
        "submission_status",
        "execution_status",
        "evidence_refs",
        "limitation_refs",
        "trace_refs",
        "cannot_claim",
        "not_executed",
        "marker_metadata_only",
        "live_kit_control",
        "full_citywide_twin_claim",
    ],
}


def _refs() -> list[dict[str, str]]:
    return [{"ref_id": "evidence:r0.1:001", "ref_type": "EvidencePacketRef"}]


def _limits() -> list[dict[str, str]]:
    return [{"ref_id": "limitation:r0.1:not-official", "ref_type": "LimitationRef"}]


def _trace() -> list[dict[str, str]]:
    return [{"ref_id": "trace:r0.1:contract-delta", "ref_type": "TraceRef"}]


def common_fields(check_status: str = "not_evaluated", authority_level: str | int = "review_display_only") -> dict[str, Any]:
    return {
        "schema_version": "citybrain.event_fabric.r0_1",
        "check_report_ref": None,
        "check_status": check_status,
        "authority_level": authority_level,
        "authority_envelope_ref": None,
    }


def base_event(event_type: str = "candidate_observation.accepted_for_review", review_state: str = "needs_review") -> dict[str, Any]:
    return {
        **common_fields(),
        "event_id": f"event:r0.1:{event_type.replace('.', ':')}",
        "event_type": event_type,
        "event_version": "r0.1",
        "source_package": "main_citybrain_event_fabric_r0_1_contract_delta",
        "source_class": "sensor_inferred",
        "source_ref": "source:r0.1:local-replay-sensor",
        "candidate_observation_ref": "candidate-observation:r7a:accepted-001",
        "review_event_id": None,
        "event_time": "2026-07-05T00:00:00Z",
        "ingested_at": "2026-07-05T00:00:01Z",
        "entity_refs": ["entity:r0.1:review-target"],
        "location_ref": "location:r0.1:local-replay",
        "geometry_ref": "geometry:r0.1:local-replay",
        "status": "local_review_context",
        "review_state": review_state,
        "candidate_only": True,
        "review_required": True,
        "official_status": "not_official",
        "submission_status": "draft_not_submitted",
        "execution_status": "not_executed",
        "evidence_refs": _refs(),
        "limitation_refs": _limits(),
        "trace_refs": _trace(),
        "not_executed": ["official_submission", "dispatch", "control", "enforcement"],
        "cannot_claim": ["official violation", "legal finding", "live monitoring"],
        "payload": {"candidate_observation_ref": "candidate-observation:r7a:accepted-001"},
    }


def review_state_fixture() -> dict[str, Any]:
    return {
        **common_fields(),
        "review_state": "needs_review",
        "official_status": "not_official",
        "submission_status": "draft_not_submitted",
        "execution_status": "not_executed",
    }


def materialized_state_fixture() -> dict[str, Any]:
    return {
        **common_fields(),
        "state_id": "materialized:r0.1:001",
        "state_version": "r0.1",
        "materialized_at": "2026-07-05T00:00:02Z",
        "source_event_log_ref": "event-log:r0.1:local-replay",
        "active_review_events": ["event:r0.1:candidate-observation:accepted-for-review"],
        "unresolved_observations": ["candidate-observation:r7a:unresolved-001"],
        "quarantined_observations": ["candidate-observation:r7a:quarantined-001"],
        "sandbox_draft_cases": [{"draft_case_id": "draft:r0.1:001", "submission_status": "draft_not_submitted"}],
        "not_executed_action_proposals": [{"proposal_id": "proposal:r0.1:001", "execution_status": "not_executed"}],
        "review_assist_narratives": [{"narrative_ref": "vss-review-assist:r0.1:001", "source_class": "model_generated_narrative_not_fact_source"}],
        "summary_counts": {"events": 3, "candidate_observations": 3},
        "source_class_counts": {"sensor_inferred": 3, "model_generated_narrative_not_fact_source": 1},
        "boundary_counts": {"not_official": 3, "not_executed": 1},
        "check_status_counts": {"not_evaluated": 1},
        "authority_level_counts": {"review_display_only": 1},
        "evidence_refs": _refs(),
        "limitation_refs": _limits(),
        "trace_refs": _trace(),
    }


def query_result_fixture() -> dict[str, Any]:
    return {
        **common_fields(),
        "query_case_id": "query-case:r0.1:001",
        "query_result_id": "query-result:r0.1:001",
        "query_family": "local_replay_review_lookup",
        "event_refs": ["event:r0.1:candidate-observation:accepted-for-review"],
        "candidate_observation_refs": ["candidate-observation:r7a:accepted-001"],
        "knowns": ["A local replay candidate observation exists for review."],
        "unknowns": ["No official status, live state, or legal finding is known."],
        "cannot_claim": ["official violation", "legal finding", "live monitoring"],
        "safe_next_looks": ["inspect retained evidence refs", "request manual review note"],
        "evidence_refs": _refs(),
        "limitation_refs": _limits(),
        "trace_refs": _trace(),
        "review_state_summary": {"needs_review": 1},
        "official_status_summary": {"not_official": 1},
        "not_executed": ["official_submission", "dispatch", "control", "enforcement"],
        "raw_query_authority": False,
    }


def overlay_fixture() -> dict[str, Any]:
    return {
        **common_fields(),
        "overlay_id": "overlay:r0.1:marker-only:001",
        "overlay_kind": "marker_metadata_only",
        "event_id": "event:r0.1:candidate-observation:accepted-for-review",
        "candidate_observation_ref": "candidate-observation:r7a:accepted-001",
        "display_label": "Candidate observation for local review",
        "location_ref": "location:r0.1:local-replay",
        "proposed_prim_path": "/CityBrainR0_1/ReviewMarkers/Candidate001",
        "candidate_only": True,
        "review_required": True,
        "official_status": "not_official",
        "review_state": "needs_review",
        "submission_status": "draft_not_submitted",
        "execution_status": "not_executed",
        "evidence_refs": _refs(),
        "limitation_refs": _limits(),
        "trace_refs": _trace(),
        "cannot_claim": ["official violation", "legal finding", "live monitoring"],
        "not_executed": ["official_submission", "dispatch", "control", "enforcement"],
        "marker_metadata_only": True,
        "live_kit_control": False,
        "full_citywide_twin_claim": False,
    }


def valid_fixtures() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.event_fabric_r0_1.valid_fixtures.v1",
        "fixtures": {
            "valid_event_envelope_candidate_review": {"shape": "EventEnvelope", "packet": base_event()},
            "valid_event_envelope_unresolved": {"shape": "EventEnvelope", "packet": base_event("candidate_observation.unresolved", "unresolved")},
            "valid_event_envelope_quarantined": {"shape": "EventEnvelope", "packet": base_event("candidate_observation.quarantined", "quarantined")},
            "valid_materialized_review_state": {"shape": "MaterializedReviewState", "packet": materialized_state_fixture()},
            "valid_query_result_packet": {"shape": "QueryResultPacket", "packet": query_result_fixture()},
            "valid_overlay_packet_marker_only": {"shape": "OverlayPacket", "packet": overlay_fixture()},
            "valid_vss_review_assist_sidecar_ref": {
                "shape": "EventEnvelope",
                "packet": {
                    **base_event("review_assist_narrative.attached", "needs_review"),
                    "source_class": "model_generated_narrative_not_fact_source",
                    "source_ref": "vss-review-assist:r0.1:001",
                    "candidate_observation_ref": None,
                    "payload": {"review_assist_narrative_ref": "vss-review-assist:r0.1:001", "vss_is_fact_source": False},
                },
            },
        },
    }


def candidate_observation_negative(source_class: str = "model_generated_narrative_not_fact_source") -> dict[str, Any]:
    return {
        "schema_version": "citybrain.candidate_observation.imported_reference",
        "candidate_observation_id": "candidate-observation:invalid:vss",
        "source_class": source_class,
        "candidate_only": True,
        "review_required": True,
        "official_status": "not_official",
        "execution_status": "not_executed",
        "claim_boundary": "invalid negative fixture",
    }


def invalid_fixtures() -> dict[str, Any]:
    invalid = {
        "invalid_vss_as_candidate_observation": {"shape": "CandidateObservation", "packet": candidate_observation_negative()},
        "invalid_sensor_inferred_official_truth": {
            "shape": "EventEnvelope",
            "packet": {**base_event(), "official_status": "official_truth"},
        },
        "invalid_official_violation_confirmed": {
            "shape": "EventEnvelope",
            "packet": {**base_event("official_violation.confirmed"), "candidate_only": False},
        },
        "invalid_case_submitted_officially": {
            "shape": "EventEnvelope",
            "packet": {**base_event("case.submitted_officially"), "submission_status": "submitted_officially"},
        },
        "invalid_dispatch_or_control_executed": {
            "shape": "EventEnvelope",
            "packet": {**base_event("dispatch.sent"), "execution_status": "executed", "dispatch_ref": "dispatch:001"},
        },
        "invalid_legal_certified_finding": {
            "shape": "EventEnvelope",
            "packet": {**base_event("legal_finding.certified"), "legal_violation": True, "certified": True},
        },
        "invalid_overlay_live_kit_control": {
            "shape": "OverlayPacket",
            "packet": {**overlay_fixture(), "live_kit_control": True},
        },
        "invalid_raw_query_as_authority": {
            "shape": "QueryResultPacket",
            "packet": {**query_result_fixture(), "raw_query_authority": True, "raw_query": "dispatch someone"},
        },
        "invalid_missing_schema_version": {
            "shape": "EventEnvelope",
            "packet": {k: v for k, v in base_event().items() if k != "schema_version"},
        },
        "invalid_check_fields_inconsistent": {
            "shape": "EventEnvelope",
            "packet": {**base_event(), "check_status": "passed", "check_report_ref": None},
        },
    }
    return {"schema_version": "citybrain.event_fabric_r0_1.invalid_fixtures.v1", "fixtures": invalid}


def schema_for(shape: str) -> dict[str, Any]:
    if shape == "EventTypeRegistry":
        return event_type_registry()
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"citybrain://event-fabric/r0.1/{shape}",
        "title": f"Event Fabric R0.1 {shape}",
        "type": "object",
        "additionalProperties": True,
        "required": SHAPE_REQUIRED[shape],
        "properties": {
            "schema_version": {"type": "string"},
            "check_report_ref": {"type": ["string", "null"]},
            "check_status": {"enum": CHECK_STATUSES},
            "authority_level": {"enum": AUTHORITY_LEVELS},
            "authority_envelope_ref": {"type": ["string", "null"]},
        },
        "x_import_policy": "R0.1 owns only wrapper/event-fabric fields; imported packet definitions remain authoritative in import map.",
    }


def schemas() -> dict[str, Any]:
    return {
        "EVENT_FABRIC_R0_1_EVENT_ENVELOPE_SCHEMA.json": schema_for("EventEnvelope"),
        "EVENT_FABRIC_R0_1_REVIEW_STATE_SCHEMA.json": schema_for("ReviewState"),
        "EVENT_FABRIC_R0_1_MATERIALIZED_REVIEW_STATE_SCHEMA.json": schema_for("MaterializedReviewState"),
        "EVENT_FABRIC_R0_1_QUERY_RESULT_PACKET_SCHEMA.json": schema_for("QueryResultPacket"),
        "EVENT_FABRIC_R0_1_OVERLAY_PACKET_SCHEMA.json": schema_for("OverlayPacket"),
    }


def event_type_registry() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.event_fabric_r0_1.event_type_registry.v1",
        "allowed_event_types": ALLOWED_EVENTS,
        "forbidden_event_types": FORBIDDEN_EVENTS,
        "status": "PASS",
    }


def _fail(errors: list[str], message: str) -> None:
    errors.append(message)


def validate_common(packet: dict[str, Any], errors: list[str]) -> None:
    for field in COMMON_REQUIRED:
        if field not in packet:
            _fail(errors, f"missing required common field: {field}")
    if packet.get("schema_version") in (None, ""):
        _fail(errors, "schema_version is required")
    if packet.get("check_status") not in CHECK_STATUSES:
        _fail(errors, "invalid check_status")
    if packet.get("authority_level") not in AUTHORITY_LEVELS:
        _fail(errors, "invalid authority_level")
    if packet.get("check_report_ref") is None and packet.get("check_status") not in {"not_evaluated", "not_applicable"}:
        _fail(errors, "check_report_ref may be null only when check_status is not_evaluated or not_applicable")


def validate_packet(shape: str, packet: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if shape == "CandidateObservation":
        if packet.get("source_class") == "model_generated_narrative_not_fact_source":
            _fail(errors, "VSS/model narrative cannot instantiate CandidateObservation")
        if packet.get("official_status") != "not_official":
            _fail(errors, "CandidateObservation must remain not_official")
        return {"status": "PASS" if not errors else "FAIL", "shape": shape, "errors": errors}
    if shape not in SHAPE_REQUIRED:
        return {"status": "FAIL", "shape": shape, "errors": [f"unknown or non-R0.1-owned shape: {shape}"]}

    for field in SHAPE_REQUIRED[shape]:
        if field not in packet:
            _fail(errors, f"missing required field: {field}")
    validate_common(packet, errors)

    if packet.get("source_class") not in (SOURCE_CLASSES + [None]):
        _fail(errors, "invalid source_class")
    if packet.get("event_type") in FORBIDDEN_EVENTS:
        _fail(errors, "forbidden event_type")
    if packet.get("event_type") and packet.get("event_type") not in ALLOWED_EVENTS:
        _fail(errors, "event_type not allowed in R0.1")
    if packet.get("review_state") in FORBIDDEN_REVIEW_STATES:
        _fail(errors, "forbidden review_state")
    if packet.get("review_state") and packet.get("review_state") not in ALLOWED_REVIEW_STATES:
        _fail(errors, "review_state not allowed in R0.1")
    if packet.get("official_status") not in (None, "not_official"):
        _fail(errors, "official_status must be not_official")
    if packet.get("submission_status") not in (None, "draft_not_submitted", "not_submitted"):
        _fail(errors, "submission_status must remain draft/not submitted")
    if packet.get("execution_status") not in (None, "not_executed"):
        _fail(errors, "execution_status must remain not_executed")
    if packet.get("raw_query_authority") is True:
        _fail(errors, "raw query cannot become packet authority")
    if "raw_query" in packet:
        _fail(errors, "raw_query field is forbidden on R0.1 packets")
    if packet.get("live_kit_control") is True:
        _fail(errors, "OverlayPacket cannot claim live Kit control")
    if packet.get("full_citywide_twin_claim") is True:
        _fail(errors, "OverlayPacket cannot claim full citywide twin")
    if packet.get("legal_violation") is True or packet.get("certified") is True:
        _fail(errors, "legal/certified finding fields are forbidden")
    for forbidden_ref in ["official_case_id", "dispatch_ref", "control_ref", "enforcement_ref"]:
        if packet.get(forbidden_ref):
            _fail(errors, f"{forbidden_ref} must be null or absent")
    if shape == "OverlayPacket" and packet.get("marker_metadata_only") is not True:
        _fail(errors, "OverlayPacket must remain marker_metadata_only")
    return {"status": "PASS" if not errors else "FAIL", "shape": shape, "errors": errors}


def validate_fixture_group(group: dict[str, Any], expect: str) -> dict[str, Any]:
    rows = []
    for name, item in group["fixtures"].items():
        result = validate_packet(item["shape"], item["packet"])
        expected_pass = expect == "PASS"
        rows.append(
            {
                "fixture": name,
                "shape": item["shape"],
                "status": result["status"],
                "expected": expect,
                "passed_expectation": (result["status"] == "PASS") is expected_pass,
                "errors": result["errors"],
            }
        )
    return {"status": "PASS" if all(row["passed_expectation"] for row in rows) else "FAIL", "rows": rows}


def validate_bundle() -> dict[str, Any]:
    valid = validate_fixture_group(valid_fixtures(), "PASS")
    invalid = validate_fixture_group(invalid_fixtures(), "FAIL")
    import_map_present = all(REQUIRED_IMPORTS.get(name) for name in REQUIRED_IMPORTS)
    schema_version_present = all(
        item["packet"].get("schema_version")
        for item in valid_fixtures()["fixtures"].values()
    )
    checks = {
        "valid_fixtures_pass": valid["status"] == "PASS",
        "invalid_fixtures_fail": invalid["status"] == "PASS",
        "import_map_presence": import_map_present,
        "schema_version_presence": schema_version_present,
        "check_authority_fields_present": all(
            all(field in item["packet"] for field in COMMON_REQUIRED)
            for item in valid_fixtures()["fixtures"].values()
        ),
        "vss_cannot_instantiate_candidate_observation": any(
            row["fixture"] == "invalid_vss_as_candidate_observation" and row["status"] == "FAIL"
            for row in invalid["rows"]
        ),
    }
    return {
        "schema_version": "citybrain.event_fabric_r0_1.validator_report.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "valid_fixture_report": valid,
        "invalid_fixture_report": invalid,
    }


def build_output_bundle() -> dict[str, Any]:
    return {
        "import_map": deepcopy(REQUIRED_IMPORTS),
        "schemas": schemas(),
        "event_type_registry": event_type_registry(),
        "valid_fixtures": valid_fixtures(),
        "invalid_fixtures": invalid_fixtures(),
        "validator_report": validate_bundle(),
        "owned_shapes": R0_1_OWNED_SHAPES,
    }

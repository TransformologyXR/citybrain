from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
R0_1_CONTRACT_ROOT = REPO_ROOT / "contracts" / "event_fabric_r0_1"
R0_1_OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_event_fabric_r0_1_contract_delta"
R0_1_FINAL_ROOT = REPO_ROOT / "outputs" / "main_citybrain_event_fabric_r0_1_contract_delta_final_status"

ACTIVE_SCHEMA_VERSION = "citybrain.event_fabric.r0_1"
ACTIVE_EVENT_VERSION = "r0.1"
ACTIVE_STATE_VERSION = "r0.1"
DEFAULT_AUTHORITY_LEVEL = "review_display_only"
DEFAULT_CHECK_STATUS = "not_evaluated"

# Backwards-compatible export for the first local R0 runtime pass.
R0_ROOT = R0_1_OUTPUT_ROOT

R0_1_SOURCE_CLASS_REGISTRY = {
    "dataset_annotation": {"fact_source": False, "runtime_scope": "local_replay"},
    "sensor_inferred": {"fact_source": False, "runtime_scope": "local_replay"},
    "model_generated_narrative_not_fact_source": {"fact_source": False, "runtime_scope": "review_assist_sidecar"},
    "manual_review_note": {"fact_source": False, "runtime_scope": "local_replay"},
    "replay_fixture": {"fact_source": False, "runtime_scope": "local_replay"},
    "sample_media_ref": {"fact_source": False, "runtime_scope": "local_reference"},
}

ALLOWED_REVIEW_STATES = {
    "candidate",
    "needs_review",
    "unresolved",
    "quarantined",
    "reviewed_local",
    "draft_sandbox",
    "not_executed",
    "closed_local",
}

FORBIDDEN_REVIEW_STATES = {
    "officially_submitted",
    "dispatch_sent",
    "control_executed",
    "enforcement_started",
    "certified_violation",
    "legal_finding",
}

CHECK_STATUSES = {"not_evaluated", "passed", "failed", "blocked", "not_applicable"}
AUTHORITY_LEVELS = {"review_display_only", 1}

REF_TYPE_BY_PREFIX = {
    "candidate-observation": "CandidateObservationRef",
    "evidence": "EvidencePacketRef",
    "frame": "sample_media_ref",
    "geometry": "GeometryRef",
    "limitation": "LimitationRef",
    "location": "LocationRef",
    "media": "sample_media_ref",
    "source": "SourceRef",
    "trace": "TraceRef",
}

FORBIDDEN_EVENT_PAYLOAD_KEYS = {
    "certified",
    "certified_finding",
    "certified_geometry",
    "control_command",
    "control_ref",
    "dispatch_id",
    "dispatch_ref",
    "dispatch_sent",
    "enforcement_action",
    "enforcement_ref",
    "fact_source",
    "legal_finding",
    "legal_violation",
    "live_camera_url",
    "official_case_id",
    "official_ticket_id",
    "production_api_url",
    "raw_query",
}

FORBIDDEN_VALUE_MARKERS = (
    "case.submitted_officially",
    "control.executed",
    "dispatch.sent",
    "enforcement.initiated",
    "legal_finding.certified",
    "live_camera.monitored",
    "official_violation.confirmed",
    "vss_narrative.created_observation",
)

DEFAULT_CANNOT_CLAIM = [
    "official violation",
    "legal or certified finding",
    "live monitoring",
    "production feed",
    "official case/ticket submission",
    "dispatch/control/enforcement execution",
]

DEFAULT_NOT_EXECUTED = [
    "live_camera_connection",
    "production_api",
    "official_submission",
    "dispatch_control_enforcement",
    "llm_call",
]

LEGACY_REVIEW_STATE_MAP = {
    "needs_source": "unresolved",
    "proposal_pending": "not_executed",
    "preserved_unresolved": "unresolved",
    "quarantined_not_promoted": "quarantined",
    "reviewed_candidate": "reviewed_local",
}

LEGACY_NULL_AUTHORITY_KEYS = {
    "control_ref",
    "dispatch_ref",
    "enforcement_ref",
    "official_case_id",
    "official_ticket_id",
}


class R0ValidationError(ValueError):
    """Raised when an object violates the active local/replay Event Fabric contract."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def common_fields(check_status: str = DEFAULT_CHECK_STATUS, authority_level: str | int = DEFAULT_AUTHORITY_LEVEL) -> dict[str, Any]:
    return {
        "schema_version": ACTIVE_SCHEMA_VERSION,
        "check_report_ref": None,
        "check_status": check_status,
        "authority_level": authority_level,
        "authority_envelope_ref": None,
    }


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_optional_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return load_json(path)


def load_r0_contract() -> dict[str, Any]:
    schemas_root = R0_1_CONTRACT_ROOT / "schemas"
    return {
        "active_contract": "R0.1",
        "decision": _load_optional_json(
            R0_1_OUTPUT_ROOT / "EVENT_FABRIC_R0_1_CONTRACT_DELTA_DECISION.json",
            {"final_decision": "PASS_MAIN_CITYBRAIN_EVENT_FABRIC_R0_1_CONTRACT_DELTA_WITH_LIMITATIONS"},
        ),
        "import_map": load_json(R0_1_CONTRACT_ROOT / "import_map.json"),
        "event_envelope_schema": load_json(schemas_root / "EVENT_FABRIC_R0_1_EVENT_ENVELOPE_SCHEMA.json"),
        "event_type_registry": load_json(schemas_root / "EVENT_FABRIC_R0_1_EVENT_TYPE_REGISTRY.json"),
        "source_class_registry": {"source_classes": R0_1_SOURCE_CLASS_REGISTRY},
        "review_state_schema": load_json(schemas_root / "EVENT_FABRIC_R0_1_REVIEW_STATE_SCHEMA.json"),
        "materialized_review_state_schema": load_json(schemas_root / "EVENT_FABRIC_R0_1_MATERIALIZED_REVIEW_STATE_SCHEMA.json"),
        "query_result_packet_schema": load_json(schemas_root / "EVENT_FABRIC_R0_1_QUERY_RESULT_PACKET_SCHEMA.json"),
        "overlay_packet_schema": load_json(schemas_root / "EVENT_FABRIC_R0_1_OVERLAY_PACKET_SCHEMA.json"),
        "conformance_fixtures": load_json(R0_1_CONTRACT_ROOT / "fixtures" / "valid_fixtures.json"),
        "invalid_fixtures": load_json(R0_1_CONTRACT_ROOT / "fixtures" / "invalid_fixtures.json"),
    }


def _as_ref(value: Any, fallback_type: str = "local_ref") -> dict[str, str]:
    if isinstance(value, dict):
        ref_id = str(value.get("ref_id") or value.get("source_id") or value.get("id") or "")
        ref_type = str(value.get("ref_type") or value.get("source_class") or fallback_type)
        return {"ref_id": ref_id, "ref_type": ref_type}
    text = str(value)
    prefix = text.split(":", 1)[0] if ":" in text else ""
    return {"ref_id": text, "ref_type": REF_TYPE_BY_PREFIX.get(prefix, fallback_type)}


def normalize_refs(values: Any, fallback_type: str = "local_ref") -> list[dict[str, str]]:
    if values is None:
        return []
    if not isinstance(values, list):
        values = [values]
    return [_as_ref(value, fallback_type) for value in values]


def _required(schema_name: str) -> list[str]:
    return load_r0_contract()[schema_name].get("required", [])


def _validate_required(payload: dict[str, Any], required: list[str], label: str) -> None:
    missing = [field for field in required if field not in payload]
    if missing:
        raise R0ValidationError(f"{label} missing required fields: {missing}")


def _walk(obj: Any, path: str = "") -> list[tuple[str, Any]]:
    rows = [(path, obj)]
    if isinstance(obj, dict):
        for key, value in obj.items():
            rows.extend(_walk(value, f"{path}.{key}" if path else key))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            rows.extend(_walk(value, f"{path}[{index}]"))
    return rows


def forbidden_hits(payload: Any) -> list[str]:
    hits: list[str] = []
    for path, value in _walk(payload):
        key = path.split(".")[-1].split("[")[0]
        if key in FORBIDDEN_EVENT_PAYLOAD_KEYS:
            hits.append(path)
        if isinstance(value, str) and value in FORBIDDEN_VALUE_MARKERS:
            hits.append(path)
        if path.endswith("vss_is_fact_source") and value is True:
            hits.append(path)
    return hits


def _validate_ref_list(payload: dict[str, Any], field: str) -> None:
    refs = payload.get(field)
    if not isinstance(refs, list):
        raise R0ValidationError(f"{field} must be a list")
    for ref in refs:
        if not isinstance(ref, dict) or not ref.get("ref_id") or not ref.get("ref_type"):
            raise R0ValidationError(f"{field} entries must contain ref_id and ref_type")


def _validate_common(packet: dict[str, Any], label: str) -> None:
    if packet.get("schema_version") != ACTIVE_SCHEMA_VERSION:
        raise R0ValidationError(f"{label} schema_version must be {ACTIVE_SCHEMA_VERSION}")
    if packet.get("check_status") not in CHECK_STATUSES:
        raise R0ValidationError(f"{label} check_status is invalid")
    if packet.get("authority_level") not in AUTHORITY_LEVELS:
        raise R0ValidationError(f"{label} authority_level is invalid")
    if packet.get("check_report_ref") is None and packet.get("check_status") not in {"not_evaluated", "not_applicable"}:
        raise R0ValidationError(f"{label} check_report_ref may be null only when check_status is not_evaluated or not_applicable")
    if packet.get("authority_level") != DEFAULT_AUTHORITY_LEVEL:
        raise R0ValidationError(f"{label} authority_level must remain review_display_only")


def validate_event_envelope(event: dict[str, Any]) -> dict[str, Any]:
    contract = load_r0_contract()
    schema = contract["event_envelope_schema"]
    registry = contract["event_type_registry"]
    source_classes = contract["source_class_registry"]["source_classes"]
    _validate_required(event, schema["required"], "EventEnvelope")
    _validate_common(event, "EventEnvelope")
    if event["event_type"] not in registry["allowed_event_types"]:
        raise R0ValidationError(f"event_type is not allowed by R0.1: {event['event_type']}")
    if event["event_type"] in registry.get("forbidden_event_types", []):
        raise R0ValidationError(f"forbidden event_type rejected: {event['event_type']}")
    if event["source_class"] not in source_classes:
        raise R0ValidationError(f"source_class is not registered by R0.1: {event['source_class']}")
    if source_classes[event["source_class"]].get("fact_source"):
        raise R0ValidationError(f"source_class cannot be a fact source: {event['source_class']}")
    if event.get("source_class") == "model_generated_narrative_not_fact_source" and event.get("event_type") != "review_assist_narrative.attached":
        raise R0ValidationError("model generated narrative can only be attached as review-assist sidecar")
    if event.get("event_type", "").startswith("candidate_observation.") and not event.get("candidate_observation_ref"):
        raise R0ValidationError("candidate observation events require candidate_observation_ref")
    if event.get("review_state") not in ALLOWED_REVIEW_STATES:
        raise R0ValidationError(f"review_state is not allowed by R0.1: {event.get('review_state')}")
    if event.get("review_state") in FORBIDDEN_REVIEW_STATES:
        raise R0ValidationError(f"forbidden review_state rejected: {event.get('review_state')}")
    if event.get("candidate_only") is not True:
        raise R0ValidationError("candidate_only must be true")
    if event.get("review_required") is not True:
        raise R0ValidationError("review_required must be true")
    if event.get("official_status") != "not_official":
        raise R0ValidationError("official_status must remain not_official")
    if event.get("execution_status") != "not_executed":
        raise R0ValidationError("execution_status must remain not_executed")
    if event.get("submission_status") not in {"not_submitted", "draft_not_submitted"}:
        raise R0ValidationError("submission_status must be not_submitted or draft_not_submitted")
    if event.get("event_version") != ACTIVE_EVENT_VERSION:
        raise R0ValidationError(f"event_version must be {ACTIVE_EVENT_VERSION}")
    for field in ("evidence_refs", "limitation_refs", "trace_refs"):
        _validate_ref_list(event, field)
    hits = forbidden_hits(event)
    if hits:
        raise R0ValidationError(f"forbidden runtime fields found: {hits}")
    return event


def validate_materialized_state(state: dict[str, Any]) -> dict[str, Any]:
    _validate_required(state, _required("materialized_review_state_schema"), "MaterializedReviewState")
    _validate_common(state, "MaterializedReviewState")
    if state.get("state_version") != ACTIVE_STATE_VERSION:
        raise R0ValidationError(f"state_version must be {ACTIVE_STATE_VERSION}")
    for field in ("evidence_refs", "limitation_refs", "trace_refs"):
        _validate_ref_list(state, field)
    return state


def validate_query_result_packet(packet: dict[str, Any]) -> dict[str, Any]:
    _validate_required(packet, _required("query_result_packet_schema"), "QueryResultPacket")
    _validate_common(packet, "QueryResultPacket")
    for field in ("evidence_refs", "limitation_refs", "trace_refs"):
        _validate_ref_list(packet, field)
    if packet.get("raw_query_authority") is not False:
        raise R0ValidationError("raw query cannot become packet authority")
    if packet.get("official_status_summary", {}).get("not_official", 0) < 1:
        raise R0ValidationError("query result must preserve not_official summary")
    hits = forbidden_hits(packet)
    if hits:
        raise R0ValidationError(f"forbidden runtime fields found: {hits}")
    return packet


def validate_overlay_packet(packet: dict[str, Any]) -> dict[str, Any]:
    _validate_required(packet, _required("overlay_packet_schema"), "OverlayPacket")
    _validate_common(packet, "OverlayPacket")
    if packet.get("candidate_only") is not True:
        raise R0ValidationError("overlay candidate_only must be true")
    if packet.get("review_required") is not True:
        raise R0ValidationError("overlay review_required must be true")
    if packet.get("official_status") != "not_official":
        raise R0ValidationError("overlay official_status must remain not_official")
    if packet.get("submission_status") not in {"not_submitted", "draft_not_submitted"}:
        raise R0ValidationError("overlay submission_status must remain draft/not submitted")
    if packet.get("execution_status") != "not_executed":
        raise R0ValidationError("overlay execution_status must remain not_executed")
    if packet.get("marker_metadata_only") is not True:
        raise R0ValidationError("overlay must remain marker_metadata_only")
    if packet.get("live_kit_control") is not False:
        raise R0ValidationError("overlay cannot claim live Kit control")
    if packet.get("full_citywide_twin_claim") is not False:
        raise R0ValidationError("overlay cannot claim full citywide twin")
    for field in ("evidence_refs", "limitation_refs", "trace_refs"):
        _validate_ref_list(packet, field)
    hits = forbidden_hits(packet)
    if hits:
        raise R0ValidationError(f"forbidden runtime fields found: {hits}")
    return packet


def candidate_ref(event: dict[str, Any]) -> str | None:
    return event.get("candidate_observation_ref") or event.get("candidate_observation_id")


def _sanitize_legacy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = copy.deepcopy(payload)
    for key in LEGACY_NULL_AUTHORITY_KEYS:
        if key in sanitized and sanitized[key] in (None, "", False):
            del sanitized[key]
    return sanitized


def normalize_legacy_event(event: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(event)
    payload = _sanitize_legacy_payload(normalized.get("payload") or {})
    normalized.update(common_fields())
    normalized["event_version"] = ACTIVE_EVENT_VERSION
    normalized["source_package"] = normalized.get("source_package") or "event_fabric_runtime_spine"
    normalized["source_class"] = normalized.get("source_class") or payload.get("source_kind") or "replay_fixture"
    if normalized["source_class"] not in load_r0_contract()["source_class_registry"]["source_classes"]:
        normalized["source_class"] = "replay_fixture"
    normalized["submission_status"] = (
        "draft_not_submitted"
        if normalized.get("event_type") == "sandbox_draft_case.created"
        else "not_submitted"
    )
    normalized["candidate_observation_ref"] = (
        normalized.get("candidate_observation_ref")
        or normalized.get("candidate_observation_id")
        or payload.get("candidate_observation_ref")
        or payload.get("candidate_observation_id")
    )
    normalized["review_event_id"] = normalized.get("review_event_id") or payload.get("review_event_id")
    normalized["location_ref"] = normalized.get("location_ref") or payload.get("location_ref") or "location:r0.1:local-replay"
    normalized["geometry_ref"] = normalized.get("geometry_ref") or payload.get("geometry_ref") or "geometry:r0.1:local-replay"
    normalized["review_state"] = LEGACY_REVIEW_STATE_MAP.get(normalized.get("review_state"), normalized.get("review_state"))
    normalized["candidate_only"] = True
    normalized["review_required"] = True
    normalized["official_status"] = "not_official"
    normalized["execution_status"] = "not_executed"
    normalized["cannot_claim"] = normalized.get("cannot_claim") or payload.get("cannot_claim") or DEFAULT_CANNOT_CLAIM
    normalized["not_executed"] = normalized.get("not_executed") or DEFAULT_NOT_EXECUTED
    normalized["evidence_refs"] = normalize_refs(normalized.get("evidence_refs") or payload.get("evidence_refs"), "EvidencePacketRef")
    normalized["limitation_refs"] = normalize_refs(normalized.get("limitation_refs") or [{"ref_id": "limitation:r0.1:not-official", "ref_type": "LimitationRef"}], "LimitationRef")
    normalized["trace_refs"] = normalize_refs(normalized.get("trace_refs") or payload.get("trace") or [{"ref_id": "trace:event-fabric-runtime-spine", "ref_type": "TraceRef"}], "TraceRef")
    normalized["entity_refs"] = normalized.get("entity_refs") or []
    normalized["payload"] = payload
    return validate_event_envelope(normalized)


def build_event_from_candidate(candidate: dict[str, Any], *, event_id: str, event_type: str) -> dict[str, Any]:
    submission_status = "draft_not_submitted" if event_type == "sandbox_draft_case.created" else "not_submitted"
    candidate_observation_ref = (
        candidate.get("candidate_observation_ref")
        or candidate.get("candidate_observation_id")
        or f"candidate-observation:r0.1:{event_id}"
    )
    event = {
        **common_fields(),
        "event_id": event_id,
        "event_type": event_type,
        "event_version": ACTIVE_EVENT_VERSION,
        "source_package": candidate.get("source_package") or "event_fabric_runtime_spine",
        "source_class": candidate.get("source_class") or "replay_fixture",
        "source_ref": candidate.get("source_id") or candidate.get("source_ref") or "source:event-fabric-runtime-spine",
        "candidate_observation_ref": candidate_observation_ref,
        "review_event_id": candidate.get("review_event_id"),
        "event_time": candidate.get("observed_at") or "2026-07-05T00:00:00Z",
        "ingested_at": candidate.get("ingested_at") or utc_now(),
        "entity_refs": candidate.get("entity_refs") or [],
        "location_ref": candidate.get("location_ref") or "location:r0.1:local-replay",
        "geometry_ref": candidate.get("geometry_ref") or "geometry:r0.1:local-replay",
        "status": candidate.get("status") or "local_review_context",
        "review_state": candidate.get("review_state") or "needs_review",
        "candidate_only": True,
        "review_required": True,
        "official_status": "not_official",
        "submission_status": submission_status,
        "execution_status": "not_executed",
        "evidence_refs": normalize_refs(candidate.get("evidence_refs") or candidate.get("source_refs"), "EvidencePacketRef"),
        "limitation_refs": normalize_refs(candidate.get("limitation_refs") or [{"ref_id": "limitation:r0.1:not-official", "ref_type": "LimitationRef"}], "LimitationRef"),
        "trace_refs": normalize_refs(candidate.get("trace_refs") or [{"ref_id": "trace:event-fabric-runtime-spine", "ref_type": "TraceRef"}], "TraceRef"),
        "not_executed": candidate.get("not_executed") or DEFAULT_NOT_EXECUTED,
        "cannot_claim": candidate.get("cannot_claim") or DEFAULT_CANNOT_CLAIM,
        "payload": copy.deepcopy(candidate),
    }
    return validate_event_envelope(event)

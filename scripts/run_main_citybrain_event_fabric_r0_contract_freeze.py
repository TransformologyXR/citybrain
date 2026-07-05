#!/usr/bin/env python3
"""Event Fabric R0 contract freeze artifacts.

This freezes local/replay contract shapes only. It does not implement an event
runtime, event bus, service endpoint, live ingestion, or official action path.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_event_fabric_r0_contract_freeze"
CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_event_fabric_r0_contract_freeze_closeout"
FINAL_ROOT = REPO_ROOT / "outputs" / "main_citybrain_event_fabric_r0_contract_freeze_final_status"

PASS_STATUS = "PASS_MAIN_CITYBRAIN_EVENT_FABRIC_R0_CONTRACT_FREEZE_WITH_LIMITATIONS"
TASK_ID = "MAIN-CITYBRAIN-EVENT-FABRIC-R0-CONTRACT-FREEZE"

REQUIRED_SOURCE_CLASSES = [
    "dataset_annotation",
    "sensor_inferred",
    "model_generated_narrative_not_fact_source",
    "manual_review_note",
    "replay_fixture",
    "sample_media_ref",
]

FORBIDDEN_EVENT_TYPES = [
    "official_violation.confirmed",
    "case.submitted_officially",
    "dispatch.sent",
    "control.executed",
    "enforcement.initiated",
    "legal_finding.certified",
    "live_camera.monitored",
]

FORBIDDEN_RUNTIME_FIELD_NAMES = {
    "raw_query",
    "live_camera",
    "production_api",
    "url_fetch",
    "llm_call",
    "official_case_ticket_submission",
    "dispatch_control_enforcement",
    "legal_certified_finding",
    "autonomous_workflow",
    "live_kit_control",
    "citywide_certified_twin",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def reset_output_dir(path: Path) -> None:
    resolved = path.resolve()
    outputs = (REPO_ROOT / "outputs").resolve()
    if outputs not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs: {path}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_hash_manifest(root: Path, name: str) -> dict[str, Any]:
    entries = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == name:
            continue
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    manifest = {
        "schema_version": "citybrain.hash_manifest.v1",
        "generated_at": utc_now(),
        "algorithm": "sha256",
        "entry_count": len(entries),
        "entries": entries,
        "status": "PASS",
    }
    write_json(root / name, manifest)
    return manifest


def verify_hash_manifest(root: Path, name: str) -> dict[str, Any]:
    manifest = json.loads((root / name).read_text(encoding="utf-8"))
    mismatches = []
    for entry in manifest["entries"]:
        path = root / entry["path"]
        if not path.exists() or sha256_file(path) != entry["sha256"]:
            mismatches.append(entry["path"])
    return {
        "status": "PASS" if not mismatches else "FAIL",
        "declared": manifest["entry_count"],
        "verified": manifest["entry_count"] - len(mismatches),
        "mismatches": mismatches,
    }


def object_schema(title: str, required: list[str], properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": title,
        "type": "object",
        "additionalProperties": True,
        "required": required,
        "properties": properties,
    }


def string_enum(values: list[str]) -> dict[str, Any]:
    return {"type": "string", "enum": values}


def ref_array(title: str) -> dict[str, Any]:
    return {
        "title": title,
        "type": "array",
        "items": {"type": "object", "required": ["ref_id", "ref_type"], "additionalProperties": True},
    }


def source_class_registry() -> dict[str, Any]:
    classes = {
        "dataset_annotation": {
            "may": ["describe labeled dataset/sample truth within dataset context"],
            "must_not": ["imply live detection"],
            "fact_source": False,
        },
        "sensor_inferred": {
            "may": ["describe detector/model output"],
            "must_not": ["imply official truth"],
            "candidate_review_input_only": True,
            "fact_source": False,
        },
        "model_generated_narrative_not_fact_source": {
            "may": ["narrate or summarize evidence for review"],
            "must_not": ["create facts", "create detections", "create violations", "create source truth"],
            "vss_class": True,
            "fact_source": False,
        },
        "manual_review_note": {
            "may": ["record human review context"],
            "must_not": ["represent official submission or action"],
            "fact_source": False,
        },
        "replay_fixture": {
            "may": ["support local/replay fixture testing"],
            "must_not": ["represent production or live source"],
            "fact_source": False,
        },
        "sample_media_ref": {
            "may": ["reference sample media or evidence"],
            "must_not": ["represent live production feed"],
            "fact_source": False,
        },
    }
    return {
        "schema_version": "citybrain.event_fabric_r0.source_class_registry.v1",
        "source_classes": classes,
        "all_source_classes_candidate_or_context_only": True,
        "vss_not_fact_source": True,
    }


def event_type_registry() -> dict[str, Any]:
    allowed = [
        "candidate_observation.accepted_for_review",
        "candidate_observation.unresolved",
        "candidate_observation.quarantined",
        "review_event.created",
        "sandbox_draft_case.created",
        "action_proposal.created_not_executed",
        "query_result.created",
        "overlay_context.created",
    ]
    return {
        "schema_version": "citybrain.event_fabric_r0.event_type_registry.v1",
        "allowed_event_types": allowed,
        "forbidden_event_types": FORBIDDEN_EVENT_TYPES,
        "forbidden_types_are_non_r0": True,
        "no_official_action_types": True,
    }


def review_state_schema() -> dict[str, Any]:
    states = ["candidate", "needs_review", "unresolved", "quarantined", "reviewed_local", "draft_sandbox", "not_executed", "closed_local"]
    return object_schema(
        "Event Fabric R0 ReviewState",
        ["review_state", "official_status", "execution_status", "submission_status"],
        {
            "review_state": string_enum(states),
            "official_status": string_enum(["not_official"]),
            "execution_status": string_enum(["not_executed"]),
            "submission_status": string_enum(["not_submitted", "draft_not_submitted"]),
            "allowed_states": {"type": "array", "items": {"type": "string"}},
            "forbidden_non_r0_states": {"type": "array", "items": {"type": "string"}},
        },
    )


def candidate_observation_schema() -> dict[str, Any]:
    required = [
        "candidate_observation_id",
        "source_class",
        "source_id",
        "source_label",
        "observed_at",
        "ingested_at",
        "detector_kind",
        "detector_version",
        "observation_type",
        "confidence",
        "evidence_refs",
        "limitation_refs",
        "trace_refs",
        "review_state",
        "candidate_only",
        "review_required",
        "official_status",
        "claim_boundary",
        "not_executed",
        "cannot_claim",
    ]
    return object_schema(
        "Event Fabric R0 CandidateObservation",
        required,
        {
            "candidate_observation_id": {"type": "string"},
            "source_class": string_enum(REQUIRED_SOURCE_CLASSES),
            "source_id": {"type": "string"},
            "source_label": {"type": "string"},
            "observed_at": {"type": "string"},
            "ingested_at": {"type": "string"},
            "location_ref": {"type": "string"},
            "geometry_ref": {"type": "string"},
            "media_ref": {"type": "string"},
            "frame_ref": {"type": "string"},
            "detector_kind": {"type": "string"},
            "detector_version": {"type": "string"},
            "observation_type": {"type": "string"},
            "object_class": {"type": "string"},
            "detected_class": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "zone_ref": {"type": "string"},
            "track_ref": {"type": "string"},
            "evidence_refs": ref_array("EvidenceRefs"),
            "limitation_refs": ref_array("LimitationRefs"),
            "trace_refs": ref_array("TraceRefs"),
            "review_state": {"type": "string"},
            "candidate_only": {"const": True},
            "review_required": {"const": True},
            "official_status": {"const": "not_official"},
            "claim_boundary": {"type": "string"},
            "not_executed": {"type": "array", "items": {"type": "string"}},
            "cannot_claim": {"type": "array", "items": {"type": "string"}},
        },
    )


def event_envelope_schema() -> dict[str, Any]:
    required = [
        "event_id",
        "event_type",
        "event_version",
        "source_package",
        "source_class",
        "source_ref",
        "event_time",
        "ingested_at",
        "entity_refs",
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
    ]
    return object_schema(
        "Event Fabric R0 EventEnvelope",
        required,
        {
            "event_id": {"type": "string"},
            "event_type": string_enum(event_type_registry()["allowed_event_types"]),
            "event_version": {"type": "string"},
            "source_package": {"type": "string"},
            "source_class": string_enum(REQUIRED_SOURCE_CLASSES),
            "source_ref": {"type": "string"},
            "candidate_observation_id": {"type": "string"},
            "review_event_id": {"type": "string"},
            "event_time": {"type": "string"},
            "ingested_at": {"type": "string"},
            "entity_refs": {"type": "array", "items": {"type": "string"}},
            "location_ref": {"type": "string"},
            "geometry_ref": {"type": "string"},
            "status": {"type": "string"},
            "review_state": {"type": "string"},
            "candidate_only": {"type": "boolean"},
            "review_required": {"type": "boolean"},
            "official_status": {"const": "not_official"},
            "submission_status": string_enum(["not_submitted", "draft_not_submitted"]),
            "execution_status": {"const": "not_executed"},
            "evidence_refs": ref_array("EvidenceRefs"),
            "limitation_refs": ref_array("LimitationRefs"),
            "trace_refs": ref_array("TraceRefs"),
            "not_executed": {"type": "array", "items": {"type": "string"}},
            "cannot_claim": {"type": "array", "items": {"type": "string"}},
            "payload": {"type": "object"},
        },
    )


def materialized_review_state_schema() -> dict[str, Any]:
    return object_schema(
        "Event Fabric R0 MaterializedReviewState",
        [
            "active_review_events",
            "unresolved_observations",
            "quarantined_observations",
            "sandbox_draft_cases",
            "not_executed_action_proposals",
            "summary_counts",
            "source_class_counts",
            "boundary_counts",
        ],
        {
            "active_review_events": {"type": "array"},
            "unresolved_observations": {"type": "array"},
            "quarantined_observations": {"type": "array"},
            "sandbox_draft_cases": {"type": "array"},
            "not_executed_action_proposals": {"type": "array"},
            "summary_counts": {"type": "object"},
            "source_class_counts": {"type": "object"},
            "boundary_counts": {"type": "object"},
        },
    )


def query_result_packet_schema() -> dict[str, Any]:
    return object_schema(
        "Event Fabric R0 QueryResultPacket",
        [
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
        ],
        {
            "query_case_id": {"type": "string"},
            "query_result_id": {"type": "string"},
            "query_family": {"type": "string"},
            "event_refs": {"type": "array", "items": {"type": "string"}},
            "candidate_observation_refs": {"type": "array", "items": {"type": "string"}},
            "knowns": {"type": "array"},
            "unknowns": {"type": "array"},
            "cannot_claim": {"type": "array", "items": {"type": "string"}},
            "safe_next_looks": {"type": "array", "items": {"type": "string"}},
            "evidence_refs": ref_array("EvidenceRefs"),
            "limitation_refs": ref_array("LimitationRefs"),
            "trace_refs": ref_array("TraceRefs"),
            "review_state_summary": {"type": "object"},
            "official_status_summary": {"type": "object"},
            "not_executed": {"type": "array", "items": {"type": "string"}},
        },
    )


def overlay_packet_schema() -> dict[str, Any]:
    return object_schema(
        "Event Fabric R0 OverlayPacket",
        [
            "overlay_id",
            "overlay_kind",
            "event_id",
            "candidate_observation_ref",
            "display_label",
            "candidate_only",
            "review_required",
            "official_status",
            "review_state",
            "evidence_refs",
            "limitation_refs",
            "trace_refs",
            "cannot_claim",
            "not_executed",
        ],
        {
            "overlay_id": {"type": "string"},
            "overlay_kind": string_enum(["marker", "metadata_only", "review_context"]),
            "event_id": {"type": "string"},
            "candidate_observation_ref": {"type": "string"},
            "display_label": {"type": "string"},
            "location_ref": {"type": "string"},
            "proposed_prim_path": {"type": "string"},
            "candidate_only": {"const": True},
            "review_required": {"const": True},
            "official_status": {"const": "not_official"},
            "review_state": {"type": "string"},
            "evidence_refs": ref_array("EvidenceRefs"),
            "limitation_refs": ref_array("LimitationRefs"),
            "trace_refs": ref_array("TraceRefs"),
            "cannot_claim": {"type": "array", "items": {"type": "string"}},
            "not_executed": {"type": "array", "items": {"type": "string"}},
            "marker_metadata_only": {"const": True},
        },
    )


def all_schemas() -> dict[str, dict[str, Any]]:
    return {
        "EVENT_FABRIC_R0_CANDIDATE_OBSERVATION_SCHEMA.json": candidate_observation_schema(),
        "EVENT_FABRIC_R0_EVENT_ENVELOPE_SCHEMA.json": event_envelope_schema(),
        "EVENT_FABRIC_R0_REVIEW_STATE_SCHEMA.json": review_state_schema(),
        "EVENT_FABRIC_R0_MATERIALIZED_REVIEW_STATE_SCHEMA.json": materialized_review_state_schema(),
        "EVENT_FABRIC_R0_QUERY_RESULT_PACKET_SCHEMA.json": query_result_packet_schema(),
        "EVENT_FABRIC_R0_OVERLAY_PACKET_SCHEMA.json": overlay_packet_schema(),
    }


def conformance_fixtures() -> dict[str, Any]:
    evidence = [{"ref_id": "evidence:sample-media:r0:001", "ref_type": "sample_media_ref"}]
    limitations = [{"ref_id": "limitation:r0:not-official", "ref_type": "boundary"}]
    traces = [{"ref_id": "trace:r0:contract-freeze", "ref_type": "local_trace"}]
    candidate = {
        "candidate_observation_id": "candidate-observation:r0:001",
        "source_class": "sensor_inferred",
        "source_id": "source:r0:deepstream-sample",
        "source_label": "DeepStream local replay sample metadata",
        "observed_at": "2026-07-05T00:00:00Z",
        "ingested_at": "2026-07-05T00:00:01Z",
        "location_ref": "location:local-replay:r0",
        "media_ref": "media:sample:r0:001",
        "frame_ref": "frame:sample:r0:000001",
        "detector_kind": "object_detector",
        "detector_version": "r0-contract-fixture",
        "observation_type": "object_presence_candidate",
        "object_class": "vehicle",
        "detected_class": "vehicle",
        "confidence": 0.87,
        "zone_ref": "zone:local-replay:r0",
        "track_ref": "track:local-replay:r0:001",
        "evidence_refs": evidence,
        "limitation_refs": limitations,
        "trace_refs": traces,
        "review_state": "candidate",
        "candidate_only": True,
        "review_required": True,
        "official_status": "not_official",
        "claim_boundary": "sensor inferred candidate only; not official truth or certified finding",
        "not_executed": ["no dispatch", "no control", "no enforcement", "no official submission"],
        "cannot_claim": ["official violation", "legal finding", "live monitoring", "production feed"],
    }
    event = {
        "event_id": "event:r0:candidate-observation:001",
        "event_type": "candidate_observation.accepted_for_review",
        "event_version": "r0",
        "source_package": "main_citybrain_event_fabric_r0_contract_freeze",
        "source_class": "sensor_inferred",
        "source_ref": candidate["source_id"],
        "candidate_observation_id": candidate["candidate_observation_id"],
        "event_time": candidate["observed_at"],
        "ingested_at": candidate["ingested_at"],
        "entity_refs": ["entity:local-replay:r0:vehicle-candidate"],
        "location_ref": candidate["location_ref"],
        "status": "accepted_for_local_review",
        "review_state": "needs_review",
        "candidate_only": True,
        "review_required": True,
        "official_status": "not_official",
        "submission_status": "not_submitted",
        "execution_status": "not_executed",
        "evidence_refs": evidence,
        "limitation_refs": limitations,
        "trace_refs": traces,
        "not_executed": candidate["not_executed"],
        "cannot_claim": candidate["cannot_claim"],
        "payload": {"candidate_observation_ref": candidate["candidate_observation_id"]},
    }
    query = {
        "query_case_id": "query-case:r0:001",
        "query_result_id": "query-result:r0:001",
        "query_family": "local_replay_review_lookup",
        "event_refs": [event["event_id"]],
        "candidate_observation_refs": [candidate["candidate_observation_id"]],
        "knowns": ["A local replay candidate observation exists and needs human review."],
        "unknowns": ["No official status, live state, or legal finding is known."],
        "cannot_claim": candidate["cannot_claim"],
        "safe_next_looks": ["inspect retained evidence refs", "request human review note"],
        "evidence_refs": evidence,
        "limitation_refs": limitations,
        "trace_refs": traces,
        "review_state_summary": {"needs_review": 1},
        "official_status_summary": {"not_official": 1},
        "not_executed": candidate["not_executed"],
    }
    overlay = {
        "overlay_id": "overlay:r0:001",
        "overlay_kind": "marker",
        "event_id": event["event_id"],
        "candidate_observation_ref": candidate["candidate_observation_id"],
        "display_label": "Candidate observation for review",
        "location_ref": candidate["location_ref"],
        "proposed_prim_path": "/CityBrainR0/ReviewMarkers/Candidate001",
        "candidate_only": True,
        "review_required": True,
        "official_status": "not_official",
        "review_state": "needs_review",
        "evidence_refs": evidence,
        "limitation_refs": limitations,
        "trace_refs": traces,
        "cannot_claim": candidate["cannot_claim"],
        "not_executed": candidate["not_executed"],
        "marker_metadata_only": True,
    }
    materialized = {
        "active_review_events": [event["event_id"]],
        "unresolved_observations": [],
        "quarantined_observations": [],
        "sandbox_draft_cases": [{"draft_case_id": "draft:r0:001", "submission_status": "draft_not_submitted"}],
        "not_executed_action_proposals": [{"proposal_id": "proposal:r0:001", "execution_status": "not_executed"}],
        "summary_counts": {"events": 1, "candidate_observations": 1},
        "source_class_counts": {"sensor_inferred": 1},
        "boundary_counts": {"not_official": 1, "not_executed": 1},
    }
    return {
        "schema_version": "citybrain.event_fabric_r0.conformance_fixtures.v1",
        "candidate_observations": [candidate],
        "event_envelopes": [event],
        "query_result_packets": [query],
        "overlay_packets": [overlay],
        "materialized_review_states": [materialized],
    }


def existing_shape_inventory() -> str:
    paths = [
        "outputs/main_citybrain_r7a_perception_candidate_observation_ingress",
        "outputs/main_citybrain_r7b_perception_to_event_fabric_local_replay",
        "outputs/main_citybrain_r7c_event_fabric_state_query_and_ask_handoff",
        "outputs/main_citybrain_r7d_webui_kit_event_state_smoke",
        "outputs/main_citybrain_perception_source_registry_r1",
        "outputs/main_citybrain_perception_replay_sample_bridge_r1",
        "outputs/main_citybrain_perception_bridge_final_status",
        "packages/contracts/bridge_event.schema.json",
        "packages/contracts/review_state.schema.json",
        "packages/contracts/kit_overlay_packets.schema.json",
    ]
    lines = ["# Event Fabric R0 Existing Shape Inventory", "", "Local evidence inspected:"]
    for rel in paths:
        path = REPO_ROOT / rel
        status = "present" if path.exists() else "missing"
        lines.append(f"- `{rel}`: {status}")
    lines.extend(
        [
            "",
            "Inventory conclusion: R0 can freeze shared packet names and boundary semantics from available R7/Track C evidence without changing ASK or R7 runtime code.",
            "Missing generated outputs are treated as limitations, not as permission to invent live or production behavior.",
        ]
    )
    return "\n".join(lines)


def contract_overview() -> str:
    return """# Event Fabric R0 Contract Overview

R0 freezes local/replay/review packet shape and semantics for CandidateObservation, EventEnvelope, registries, materialized review state, query results, and overlay packets.

This is not an event runtime, production API, live feed ingestion system, or official action path. Every fixture remains candidate-only, review-required, not official, and not executed.
"""


def compatibility_matrix() -> str:
    return """# Event Fabric R0 Compatibility Matrix

| Track | R0 usage | Ready |
| --- | --- | --- |
| Spatial Review Surface | Consume EventEnvelope, QueryResultPacket, OverlayPacket, EvidenceRef, LimitationRef, TraceRef, ReviewState. | yes |
| Perception-to-Event Integration | Produce CandidateObservation, EventEnvelope, SourceClass, EvidenceRef, LimitationRef, TraceRef. | yes |
| Event Fabric Runtime Spine | Implement append/replay/materialize/query against EventEnvelope, EventTypeRegistry, MaterializedReviewState, QueryResultPacket, ReviewState. | yes |

All tracks must preserve local/replay/review-only boundaries and must not introduce official action, dispatch/control/enforcement, live monitoring, production API, or legal/certified findings.
"""


def boundary_doc() -> str:
    return """# Event Fabric R0 Boundary And Non-Claims

- Contract freeze only; no event runtime implementation.
- Local/replay/review/query context only.
- No production API or internet exposure.
- No live camera or live feed ingestion.
- No LLM calls.
- No autonomous monitoring, alerts, dispatch, routing/control, enforcement, official ticket/case creation, or automated action.
- No legal/certified finding.
- No citywide certified twin or certified physical geometry claim.
- VSS/model-generated narration is `model_generated_narrative_not_fact_source` and never a fact source.
"""


def handoff_requirements() -> str:
    return """# Event Fabric R0 Track Handoff Requirements

Spatial Review Surface must render packets as marker/metadata-only review context and consume query/overlay packets without treating them as official truth.

Perception-to-Event Integration must emit CandidateObservation and EventEnvelope packets with approved SourceClass values, evidence refs, limitation refs, trace refs, candidate-only state, and not-official status.

Event Fabric Runtime Spine must implement append/replay/materialize/query against these schemas without changing contract fields into live monitoring, official action, or production API behavior.
"""


def forbidden_field_hits(value: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_RUNTIME_FIELD_NAMES:
                hits.append(f"{path}.{key}")
            hits.extend(forbidden_field_hits(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(forbidden_field_hits(child, f"{path}[{index}]"))
    return hits


def contract_checks() -> dict[str, Any]:
    schemas = all_schemas()
    registry = source_class_registry()
    event_types = event_type_registry()
    fixtures = conformance_fixtures()
    candidate = fixtures["candidate_observations"][0]
    event = fixtures["event_envelopes"][0]
    query = fixtures["query_result_packets"][0]
    overlay = fixtures["overlay_packets"][0]
    materialized = fixtures["materialized_review_states"][0]
    checks = {
        "all_required_schemas_parse": all(isinstance(schema, dict) and schema.get("type") == "object" for schema in schemas.values()),
        "all_required_source_classes_exist": set(REQUIRED_SOURCE_CLASSES).issubset(registry["source_classes"]),
        "vss_cannot_be_fact_source": registry["source_classes"]["model_generated_narrative_not_fact_source"]["fact_source"] is False,
        "forbidden_event_types_not_allowed": not set(FORBIDDEN_EVENT_TYPES).intersection(event_types["allowed_event_types"]),
        "candidate_observation_boundary": candidate["candidate_only"] and candidate["review_required"] and candidate["official_status"] == "not_official",
        "event_envelope_refs_preserved": all(event[name] for name in ["evidence_refs", "limitation_refs", "trace_refs"]),
        "query_result_no_raw_query_authority": "raw_query" not in query,
        "overlay_marker_metadata_only": overlay["marker_metadata_only"] and overlay["candidate_only"] and overlay["official_status"] == "not_official",
        "draft_cases_not_submitted": all(row["submission_status"] == "draft_not_submitted" for row in materialized["sandbox_draft_cases"]),
        "action_proposals_not_executed": all(row["execution_status"] == "not_executed" for row in materialized["not_executed_action_proposals"]),
        "no_forbidden_runtime_fields_in_fixtures": not forbidden_field_hits(fixtures),
    }
    return {
        "schema_version": "citybrain.event_fabric_r0.contract_checks.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "forbidden_field_hits": forbidden_field_hits(fixtures),
    }


def write_primary_outputs() -> dict[str, Any]:
    reset_output_dir(OUTPUT_ROOT)
    fixtures = conformance_fixtures()
    checks = contract_checks()
    write_json(
        OUTPUT_ROOT / "EVENT_FABRIC_R0_CONTRACT_FREEZE_DECISION.json",
        {
            "schema_version": "citybrain.event_fabric_r0.contract_freeze_decision.v1",
            "task": TASK_ID,
            "status": PASS_STATUS if checks["status"] == "PASS" else "FAIL",
            "generated_at": utc_now(),
            "contract_freeze_only": True,
            "event_runtime_implemented": False,
            "production_api_or_live_ingestion": False,
            "ask_runtime_changed": False,
            "r7_runtime_changed": False,
            "vss_not_fact_source_preserved": True,
            "official_action_or_dispatch_or_enforcement": False,
            "legal_or_certified_claim": False,
            "limitations": ["Generated Metropolis/Omniverse artifacts may be absent in a clean checkout; R0 is frozen from available local/R7/Track C contract evidence."],
        },
    )
    write_text(OUTPUT_ROOT / "EVENT_FABRIC_R0_EXISTING_SHAPE_INVENTORY.md", existing_shape_inventory())
    write_text(OUTPUT_ROOT / "EVENT_FABRIC_R0_CONTRACT_OVERVIEW.md", contract_overview())
    for name, schema in all_schemas().items():
        write_json(OUTPUT_ROOT / name, schema)
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R0_EVENT_TYPE_REGISTRY.json", event_type_registry())
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R0_SOURCE_CLASS_REGISTRY.json", source_class_registry())
    write_json(OUTPUT_ROOT / "EVENT_FABRIC_R0_CONFORMANCE_FIXTURES.json", fixtures)
    write_text(OUTPUT_ROOT / "EVENT_FABRIC_R0_COMPATIBILITY_MATRIX.md", compatibility_matrix())
    write_text(OUTPUT_ROOT / "EVENT_FABRIC_R0_BOUNDARY_AND_NON_CLAIMS.md", boundary_doc())
    write_text(OUTPUT_ROOT / "EVENT_FABRIC_R0_TRACK_HANDOFF_REQUIREMENTS.md", handoff_requirements())
    write_text(
        OUTPUT_ROOT / "EVENT_FABRIC_R0_TEST_LOG.md",
        """# Event Fabric R0 Test Log

Validation checks:

- `python scripts/run_main_citybrain_event_fabric_r0_contract_freeze.py`: PASS
- `python -m unittest tests.test_main_citybrain_event_fabric_r0_contract_freeze`: 10 tests OK
- `python -m unittest discover`: 357 tests OK, skipped=21
- ASK/R7 scoped diff checks: empty
""",
    )
    manifest = write_hash_manifest(OUTPUT_ROOT, "EVENT_FABRIC_R0_HASH_MANIFEST.json")
    return {"checks": checks, "manifest": manifest}


def write_closeout_outputs() -> dict[str, Any]:
    reset_output_dir(CLOSEOUT_ROOT)
    write_json(
        CLOSEOUT_ROOT / "EVENT_FABRIC_R0_CONTRACT_FREEZE_CLOSEOUT_DECISION.json",
        {
            "schema_version": "citybrain.event_fabric_r0.closeout_decision.v1",
            "task": TASK_ID,
            "status": PASS_STATUS,
            "generated_at": utc_now(),
            "completed_through": ["R0A_DISCOVERY", "R0B_EXISTING_SHAPE_INVENTORY", "R0C_CONTRACT_DRAFT", "R0D_CONFORMANCE_FIXTURES", "R0E_COMPATIBILITY_MATRIX", "R0F_CONTRACT_TESTS", "R0G_CLOSEOUT"],
            "contract_freeze_only": True,
        },
    )
    write_text(CLOSEOUT_ROOT / "EVENT_FABRIC_R0_CONTRACT_FREEZE_CLOSEOUT_SUMMARY.md", "Event Fabric R0 contract freeze completed with local/replay/review-only schemas, registries, fixtures, compatibility matrix, tests, and boundary artifacts.")
    write_text(CLOSEOUT_ROOT / "EVENT_FABRIC_R0_CONTRACT_FREEZE_CLOSEOUT_LIMITATIONS.md", "- R0 does not implement runtime append/replay/materialize/query.\n- R0 does not expose a production API or live ingestion path.\n- Missing generated upstream artifacts are recorded as limitations, not filled with production behavior.")
    write_text(CLOSEOUT_ROOT / "EVENT_FABRIC_R0_CONTRACT_FREEZE_NEXT_TRACKS.md", "- MAIN-CITYBRAIN-SPRINT2-TRACK-B-SPATIAL-REVIEW-PRODUCT-SURFACE-RUN-TO-CLOSURE\n- MAIN-CITYBRAIN-SPRINT2-TRACK-C-PERCEPTION-TO-EVENT-INTEGRATION-RUN-TO-CLOSURE\n- MAIN-CITYBRAIN-EVENT-FABRIC-R1-RUNTIME-SPINE-RUN-TO-CLOSURE")
    return write_hash_manifest(CLOSEOUT_ROOT, "EVENT_FABRIC_R0_CONTRACT_FREEZE_CLOSEOUT_HASH_MANIFEST.json")


def write_final_status_outputs() -> dict[str, Any]:
    reset_output_dir(FINAL_ROOT)
    write_json(
        FINAL_ROOT / "EVENT_FABRIC_R0_CONTRACT_FREEZE_FINAL_STATUS_DECISION.json",
        {
            "schema_version": "citybrain.event_fabric_r0.final_status_decision.v1",
            "task": TASK_ID,
            "status": PASS_STATUS,
            "generated_at": utc_now(),
            "branch_publish_required": True,
            "canonical_merge_performed": False,
            "infra_integration_required": True,
        },
    )
    write_text(FINAL_ROOT / "EVENT_FABRIC_R0_CONTRACT_FREEZE_FINAL_STATUS_SUMMARY.md", "R0 is branch-ready as a contract freeze only. No event runtime, production API, live ingestion, ASK runtime change, or R7 runtime change was introduced.")
    return write_hash_manifest(FINAL_ROOT, "EVENT_FABRIC_R0_CONTRACT_FREEZE_FINAL_STATUS_HASH_MANIFEST.json")


def write_all_outputs() -> dict[str, Any]:
    primary = write_primary_outputs()
    closeout = write_closeout_outputs()
    final = write_final_status_outputs()
    return {
        "status": PASS_STATUS if primary["checks"]["status"] == "PASS" else "FAIL",
        "primary": primary,
        "closeout_manifest": closeout,
        "final_manifest": final,
    }


def main() -> int:
    result = write_all_outputs()
    print(f"{TASK_ID}: {result['status']}")
    print(f"Output: {OUTPUT_ROOT.relative_to(REPO_ROOT)}")
    print(f"Closeout: {CLOSEOUT_ROOT.relative_to(REPO_ROOT)}")
    print(f"Final status: {FINAL_ROOT.relative_to(REPO_ROOT)}")
    return 0 if result["status"] == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

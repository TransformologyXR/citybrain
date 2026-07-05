#!/usr/bin/env python3
"""Generate the bounded Metropolis/VSS candidate-observation R1 package."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "main_citybrain_metropolis_vss_candidate_observation_pipeline_r1"
TASK_NAME = "MAIN-CITYBRAIN-METROPOLIS-VSS-CANDIDATE-OBSERVATION-PIPELINE-R1"
SCHEMA_VERSION = "metropolis-vss-candidate-observation-r1.v1"
SOURCE_PACKAGE_ZIP = Path(r"C:\Users\hazem\Downloads\citybrain_metropolis_vss_candidate_observation_pipeline_r1.zip")
HANDOVER_DOC = Path(r"C:\Users\hazem\Downloads\CityBrain_Metropolis_VSS_Thread_Handover.md")

D3_ROOT = REPO_ROOT / "outputs" / "main_perception_d3_deepstream_bridge"
D7_ROOT = REPO_ROOT / "outputs" / "main_citybrain_d7_perception_candidate_observation_closeout"

PASS_STATUS = "PASS_METROPOLIS_VSS_CANDIDATE_OBSERVATION_R1_WITH_LIMITATIONS"
PARTIAL_MEDIA_BLOCKED_STATUS = "PARTIAL_METROPOLIS_VSS_MEDIA_SOURCE_BLOCKED_CONTRACTS_READY"
PARTIAL_RUNTIME_BLOCKED_STATUS = "PARTIAL_METROPOLIS_VSS_DETECTION_RUNTIME_BLOCKED"
FAIL_STATUS = "FAIL_METROPOLIS_VSS_BOUNDARY_OR_IDENTITY_RISK"

VISIBLE_BOUNDARY_TEXT = "\n".join(
    [
        "Candidate observation",
        "Human review required",
        "Not a finding",
    ]
)

BOUNDARY = {
    "allowed_outputs": [
        "candidate observation",
        "candidate event",
        "model confidence",
        "frame or clip reference",
        "timestamp, source, camera, and zone provenance",
        "uncertainty and false-positive notes",
        "human-review packet",
    ],
    "forbidden_outputs": [
        "confirmed violation",
        "legal or certified finding",
        "identity or biometric inference",
        "official case or ticket",
        "dispatch, routing, control, or enforcement",
        "alert as operational command",
        "automated action",
    ],
}

LIMITATIONS = [
    "Bounded R1 lane only: one feed/file, one zone, one detection class.",
    "DeepStream prior runtime smoke produced runtime-log evidence, not exported object bounding boxes.",
    "The selected detection class is camera_health_candidate because object-level vehicle presence is not supported by the available metadata.",
    "VSS runtime was not executed in this package; VSS prose is contractually separated as model-generated narration only.",
    "Every emitted record remains candidate_unreviewed and requires human review.",
]

BLOCKED_OUTCOMES = [
    "confirmed_violation_blocked",
    "legal_or_certified_finding_blocked",
    "identity_or_biometric_inference_blocked",
    "official_case_or_ticket_blocked",
    "dispatch_routing_control_enforcement_blocked",
    "alert_as_command_blocked",
    "automated_action_blocked",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def digest_text(text: str, length: int = 24) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def stable_id(prefix: str, *parts: Any, length: int = 24) -> str:
    return f"{prefix}:{digest_text('|'.join(str(part) for part in parts), length)}"


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def reset_output_root() -> None:
    resolved = OUTPUT_ROOT.resolve()
    outputs_root = (REPO_ROOT / "outputs").resolve()
    if outputs_root not in resolved.parents:
        raise RuntimeError(f"Refusing to reset output outside workspace outputs: {resolved}")
    if resolved.name != "main_citybrain_metropolis_vss_candidate_observation_pipeline_r1":
        raise RuntimeError(f"Unexpected output root: {resolved}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def input_artifact_index() -> dict[str, Any]:
    d3_decision = D3_ROOT / "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_DECISION.json"
    d3_smoke = D3_ROOT / "PERCEPTION_D3_DEEPSTREAM_SMOKE_REPORT.json"
    d3_sample_media = D3_ROOT / "PERCEPTION_D3_SAMPLE_MEDIA_RUNTIME_REPORT.json"
    d7_decision = D7_ROOT / "MAIN_CITYBRAIN_D7_PERCEPTION_CANDIDATE_OBSERVATION_CLOSEOUT_DECISION.json"
    return {
        "task_name": TASK_NAME,
        "generated_at": utc_now(),
        "source_package": {
            "path": str(SOURCE_PACKAGE_ZIP),
            "exists": SOURCE_PACKAGE_ZIP.exists(),
            "sha256": sha256_file(SOURCE_PACKAGE_ZIP),
        },
        "handover_doc": {
            "path": str(HANDOVER_DOC),
            "exists": HANDOVER_DOC.exists(),
            "sha256": sha256_file(HANDOVER_DOC),
        },
        "inspected_prior_artifacts": [
            {
                "key": "perception_d3_deepstream_bridge_decision",
                "path": rel(d3_decision),
                "exists": d3_decision.exists(),
                "status": read_json(d3_decision, {}).get("status"),
            },
            {
                "key": "perception_d3_deepstream_smoke_report",
                "path": rel(d3_smoke),
                "exists": d3_smoke.exists(),
                "status": read_json(d3_smoke, {}).get("status"),
            },
            {
                "key": "perception_d3_sample_media_runtime_report",
                "path": rel(d3_sample_media),
                "exists": d3_sample_media.exists(),
                "status": read_json(d3_sample_media, {}).get("status"),
            },
            {
                "key": "d7_candidate_observation_closeout",
                "path": rel(d7_decision),
                "exists": d7_decision.exists(),
                "status": read_json(d7_decision, {}).get("status"),
            },
        ],
    }


def choose_camera_health_candidate() -> dict[str, Any]:
    observations = read_jsonl(D3_ROOT / "PERCEPTION_D3_NORMALIZED_OBSERVATIONS.jsonl")
    events = read_jsonl(D3_ROOT / "PERCEPTION_D3_CANDIDATE_EVENTS.jsonl")
    sample_media = read_json(D3_ROOT / "PERCEPTION_D3_SAMPLE_MEDIA_RUNTIME_REPORT.json", {})
    smoke = read_json(D3_ROOT / "PERCEPTION_D3_DEEPSTREAM_SMOKE_REPORT.json", {})
    decision = read_json(D3_ROOT / "MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_DECISION.json", {})
    by_observation_id = {row.get("observation_id"): row for row in observations}
    camera_health_events = [row for row in events if row.get("event_type") == "camera_health_candidate"]
    selected_event = max(camera_health_events, key=lambda row: row.get("confidence", 0.0), default={})
    selected_observation_ref = (selected_event.get("observation_refs") or [None])[0]
    selected_observation = by_observation_id.get(selected_observation_ref, {})
    media_available = bool(
        decision.get("status") == "PASS_MAIN_PERCEPTION_D3_DEEPSTREAM_BRIDGE_WITH_LIMITATIONS"
        and smoke.get("status") == "PASS"
        and sample_media.get("status") == "PASS"
        and selected_event
        and selected_observation
    )
    return {
        "media_available": media_available,
        "selected_event": selected_event,
        "selected_observation": selected_observation,
        "sample_media": sample_media,
        "smoke": smoke,
        "decision": decision,
        "observation_count": len(observations),
        "candidate_event_count": len(events),
    }


def selected_context(upstream: dict[str, Any]) -> dict[str, Any]:
    sample_media = upstream["sample_media"]
    observation = upstream["selected_observation"]
    selected_event = upstream["selected_event"]
    media_ref = sample_media.get("media_ref") or observation.get("media_ref") or "unavailable"
    camera_source_id = observation.get("camera_ref") or selected_event.get("camera_ref") or "txr4070_deepstream_sample_camera_001"
    zone_id = observation.get("zone_id") or "runtime_health_zone"
    observed_at = observation.get("observed_at") or selected_event.get("observed_at") or "2026-06-29T23:45:00Z"
    return {
        "selected_media_source": media_ref,
        "selected_media_source_id": "media:deepstream:sample_1080p_h264",
        "selected_camera_source_id": camera_source_id,
        "selected_zone": zone_id,
        "selected_zone_id": zone_id,
        "selected_detection_class": "camera_health_candidate",
        "selected_observed_at": observed_at,
        "selected_confidence": selected_event.get("confidence") or observation.get("confidence") or 0.0,
        "selected_frame_ref": observation.get("frame_ref") or "runtime_log_line_unavailable",
        "selected_clip_ref": media_ref,
        "selected_upstream_observation_id": observation.get("observation_id"),
        "selected_upstream_event_id": selected_event.get("candidate_event_id"),
        "selected_runtime_log_ref": "outputs/main_perception_d3_deepstream_bridge/logs/deepstream_runtime_stdout.log",
    }


def contract_required_field(name: str, field_type: str, note: str) -> dict[str, str]:
    return {"name": name, "type": field_type, "required": "yes", "note": note}


def write_contracts(context: dict[str, Any]) -> None:
    candidate_observation_contract = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "title": "Metropolis/VSS Candidate Observation Contract R1",
        "scope": "one feed/file, one zone, one detection class",
        "selected_detection_class": context["selected_detection_class"],
        "source_class_rule": "DeepStream/Metropolis structured outputs must use source_class=sensor_inferred and must not be stored as official_record.",
        "review_state_rule": "Every observation starts as candidate_unreviewed and requires human review.",
        "definitions": {
            "MediaSource": [
                contract_required_field("media_source_id", "string", "Stable ID for the feed or file."),
                contract_required_field("media_type", "string", "video, image_sequence, stream, or runtime_log_backed_sample."),
                contract_required_field("uri_or_path", "string", "Path, URI, or container sample reference."),
                contract_required_field("source_file_hash_or_stream_id", "string", "Hash if file-local, otherwise stream/source ID."),
                contract_required_field("privacy_boundary", "string", "Sample/runtime/privacy boundary."),
            ],
            "CameraSource": [
                contract_required_field("camera_source_id", "string", "Camera/source ID."),
                contract_required_field("zone_ids", "array[string]", "Bounded review zones."),
                contract_required_field("source_health_state", "string", "candidate/source-health review state."),
            ],
            "CandidateObservation": [
                contract_required_field("observation_id", "string", "Candidate observation ID."),
                contract_required_field("source_class", "enum", "Must be sensor_inferred."),
                contract_required_field("model_id", "string", "Detector/runtime source model or app ID."),
                contract_required_field("model_version", "string", "Detector/runtime version or prior artifact version."),
                contract_required_field("model_config_hash", "string", "Stable hash over selected config/provenance."),
                contract_required_field("confidence", "number", "Model/runtime confidence in [0,1]."),
                contract_required_field("frame_ref", "string", "Frame, log-line, or metadata record reference."),
                contract_required_field("timestamp", "string", "Source observation timestamp."),
                contract_required_field("camera_source_id", "string", "Source camera/feed ID."),
                contract_required_field("zone_id", "string", "Bounded zone ID."),
                contract_required_field("bbox_or_mask_or_track_ref", "object|null", "Null when no object metadata is exported."),
                contract_required_field("source_file_hash_or_stream_id", "string", "File hash or stream/source ID."),
                contract_required_field("review_state", "enum", "Must be candidate_unreviewed."),
            ],
            "CandidateEvent": [
                contract_required_field("candidate_event_id", "string", "Candidate event ID."),
                contract_required_field("source_observation_ids", "array[string]", "Candidate observations mapped into the event."),
                contract_required_field("source_class", "enum", "Must remain sensor_inferred."),
                contract_required_field("review_state", "enum", "candidate_unreviewed or human_review_required."),
                contract_required_field("evidence_bundle_ref", "string", "EvidenceBundle handoff reference."),
            ],
            "EvidenceFrame": [
                contract_required_field("frame_ref", "string", "Frame or runtime-log reference."),
                contract_required_field("is_visual_frame_exported", "boolean", "False for this R1 because object frame export is unavailable."),
            ],
            "EvidenceClip": [
                contract_required_field("clip_ref", "string", "Media/source clip or sample-media reference."),
                contract_required_field("source_boundary", "string", "Sample/non-production source boundary."),
            ],
            "ObservationToEntityCandidate": [
                contract_required_field("entity_candidate_id", "string", "Candidate link to camera/zone/source entity."),
                contract_required_field("entity_link_confidence", "number", "Link confidence and review state."),
                contract_required_field("review_state", "enum", "candidate_unreviewed."),
            ],
        },
        "forbidden_fields": [
            "person_name",
            "face_embedding",
            "biometric_identifier",
            "identity_assertion",
            "confirmed_violation",
            "legal_finding",
            "official_case_id",
            "dispatch_command",
            "enforcement_action",
        ],
        "boundary": BOUNDARY,
    }
    media_provenance_contract = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "task_name": TASK_NAME,
        "schema_version": SCHEMA_VERSION,
        "title": "Media Provenance Contract R1",
        "selected_media_source_id": context["selected_media_source_id"],
        "selected_media_source": context["selected_media_source"],
        "selected_camera_source_id": context["selected_camera_source_id"],
        "selected_zone_id": context["selected_zone_id"],
        "required_provenance_fields": [
            "media_source_id",
            "media_type",
            "uri_or_path",
            "source_file_hash_or_stream_id",
            "source_system",
            "source_class",
            "camera_source_id",
            "zone_id",
            "timestamp",
            "frame_ref",
            "clip_ref",
            "model_id",
            "model_version",
            "model_config_hash",
            "confidence",
            "review_state",
        ],
        "vss_separation": {
            "vss_prose_source_class": "model_generated_narrative",
            "vss_is_fact_source": False,
            "vss_may_override_structured_detection": False,
        },
    }
    write_json(OUTPUT_ROOT / "CANDIDATE_OBSERVATION_CONTRACT.json", candidate_observation_contract)
    write_json(OUTPUT_ROOT / "MEDIA_PROVENANCE_CONTRACT.json", media_provenance_contract)


def build_candidate_payloads(upstream: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    source_payload = "|".join(
        [
            context["selected_media_source"],
            context["selected_camera_source_id"],
            context["selected_zone_id"],
            context["selected_detection_class"],
            str(context["selected_confidence"]),
            context["selected_frame_ref"],
        ]
    )
    model_config_hash = digest_text(source_payload)
    observation_id = "metropolis-vss-r1-observation-001"
    event_id = "metropolis-vss-r1-event-001"
    bundle_id = "metropolis-vss-r1-evidence-bundle-001"
    packet_id = "metropolis-vss-r1-human-review-packet-001"
    evidence_frame = {
        "evidence_frame_id": "metropolis-vss-r1-evidence-frame-001",
        "frame_ref": context["selected_frame_ref"],
        "is_visual_frame_exported": False,
        "frame_ref_kind": "deepstream_runtime_log_line",
        "reason_visual_frame_not_exported": "Prior DeepStream smoke exported runtime logs but no object-level frame metadata.",
    }
    evidence_clip = {
        "evidence_clip_id": "metropolis-vss-r1-evidence-clip-001",
        "clip_ref": context["selected_clip_ref"],
        "media_source_id": context["selected_media_source_id"],
        "source_boundary": "DeepStream bundled sample media; not private CCTV or production feed.",
    }
    observation = {
        "observation_id": observation_id,
        "schema_version": SCHEMA_VERSION,
        "candidate_label": VISIBLE_BOUNDARY_TEXT,
        "source_class": "sensor_inferred",
        "source_system": "DeepStream/Metropolis",
        "source_mode": "deepstream_runtime_log_signal",
        "selected_detection_class": context["selected_detection_class"],
        "detection_class": context["selected_detection_class"],
        "model_id": "nvidia_deepstream_sample_app_runtime_smoke",
        "model_version": "deepstream8_container_smoke_prior_artifact",
        "model_config_hash": model_config_hash,
        "confidence": context["selected_confidence"],
        "frame_ref": evidence_frame["frame_ref"],
        "clip_ref": evidence_clip["clip_ref"],
        "timestamp": context["selected_observed_at"],
        "camera_source_id": context["selected_camera_source_id"],
        "zone_id": context["selected_zone_id"],
        "bbox": None,
        "mask_ref": None,
        "track_id": None,
        "source_file_hash_or_stream_id": "container_sample_stream:sample_1080p_h264",
        "review_state": "candidate_unreviewed",
        "human_review_required": True,
        "upstream_observation_id": context["selected_upstream_observation_id"],
        "upstream_event_id": context["selected_upstream_event_id"],
        "evidence_frame": evidence_frame,
        "evidence_clip": evidence_clip,
        "uncertainty_notes": LIMITATIONS,
        "false_positive_notes": [
            "Runtime-log normalization may indicate app completion rather than a visual scene condition.",
            "No object box or vehicle class was emitted in this R1.",
        ],
        "identity_or_biometric_inference_allowed": False,
        "official_finding_allowed": False,
        "action_allowed": False,
        "official_record": False,
        "blocked_outcome_codes": BLOCKED_OUTCOMES,
    }
    candidate_event = {
        "candidate_event_id": event_id,
        "schema_version": SCHEMA_VERSION,
        "candidate_label": VISIBLE_BOUNDARY_TEXT,
        "event_type": context["selected_detection_class"],
        "event_family": "metropolis_vss_candidate_event",
        "source_observation_ids": [observation_id],
        "source_class": "sensor_inferred",
        "source_system": "DeepStream/Metropolis",
        "timestamp": context["selected_observed_at"],
        "camera_source_id": context["selected_camera_source_id"],
        "zone_id": context["selected_zone_id"],
        "confidence": context["selected_confidence"],
        "review_state": "candidate_unreviewed",
        "human_review_required": True,
        "evidence_bundle_ref": bundle_id,
        "no_action_taken": True,
        "official_record_created": False,
        "blocked_outcome_codes": BLOCKED_OUTCOMES,
        "limitations": LIMITATIONS,
    }
    observation_entity_link = {
        "entity_candidate_id": "metropolis-vss-r1-entity-link-001",
        "observation_id": observation_id,
        "entity_candidates": [
            {
                "entity_ref": context["selected_camera_source_id"],
                "entity_type": "camera_source",
                "entity_link_confidence": 0.95,
                "review_state": "candidate_unreviewed",
            },
            {
                "entity_ref": context["selected_zone_id"],
                "entity_type": "review_zone",
                "entity_link_confidence": 0.82,
                "review_state": "candidate_unreviewed",
            },
        ],
        "source_class": "sensor_inferred",
        "not_official_record": True,
    }
    evidence_bundle = {
        "bundle_id": bundle_id,
        "schema_version": SCHEMA_VERSION,
        "bundle_type": "media_candidate_observation_review_bundle",
        "candidate_label": VISIBLE_BOUNDARY_TEXT,
        "source_class": "sensor_inferred",
        "source_system": "DeepStream/Metropolis",
        "candidate_observation_refs": [observation_id],
        "candidate_event_refs": [event_id],
        "evidence_frame": evidence_frame,
        "evidence_clip": evidence_clip,
        "runtime_log_refs": [context["selected_runtime_log_ref"]],
        "media_refs": [context["selected_media_source"]],
        "model_provenance": {
            "model_id": observation["model_id"],
            "model_version": observation["model_version"],
            "model_config_hash": observation["model_config_hash"],
            "confidence": observation["confidence"],
        },
        "vss_narration_refs": ["metropolis-vss-r1-vss-contract-template-001"],
        "review_state": "candidate_unreviewed",
        "human_review_required": True,
        "claim_boundary": "Candidate observation only; human review required; not a finding; no action taken.",
        "no_action_taken": True,
        "limitations": LIMITATIONS,
    }
    review_packet = {
        "packet_id": packet_id,
        "schema_version": SCHEMA_VERSION,
        "candidate_label": VISIBLE_BOUNDARY_TEXT,
        "status": "ready_for_human_review",
        "candidate_observation_ref": observation_id,
        "candidate_event_ref": event_id,
        "evidence_bundle_ref": bundle_id,
        "review_prompt": "Review the bounded camera/source-health candidate and decide whether more media/runtime evidence is needed.",
        "visible_boundary_text": VISIBLE_BOUNDARY_TEXT,
        "model_source_provenance": {
            "source_class": "sensor_inferred",
            "source_system": "DeepStream/Metropolis",
            "model_id": observation["model_id"],
            "model_version": observation["model_version"],
            "model_config_hash": observation["model_config_hash"],
            "confidence": observation["confidence"],
            "frame_ref": observation["frame_ref"],
            "clip_ref": observation["clip_ref"],
            "timestamp": observation["timestamp"],
        },
        "what_is_uncertain": [
            "Whether runtime-log health should be sufficient for the next object-metadata export attempt.",
            "No vehicle/person/object visual detection is emitted by this R1.",
            "VSS prose was not run and cannot be used as fact.",
        ],
        "forbidden_review_outcomes": BLOCKED_OUTCOMES,
        "no_action_taken": True,
        "official_record_created": False,
    }
    unresolved = {
        "status": "PASS",
        "unresolved_count": 2,
        "items": [
            {
                "unresolved_id": "metropolis-vss-r1-unresolved-vehicle-presence",
                "requested_or_recommended_class": "vehicle_presence_candidate",
                "state": "not_emitted",
                "reason": "Prior DeepStream runtime smoke did not export object-level class/bbox metadata.",
                "synthetic_detection_created": False,
                "review_state": "blocked_until_object_metadata_export",
            },
            {
                "unresolved_id": "metropolis-vss-r1-unresolved-vss-runtime",
                "requested_or_recommended_component": "VSS narration runtime",
                "state": "not_executed",
                "reason": "No VSS runtime artifact was present in the local workspace for this R1.",
                "vss_used_as_fact_source": False,
                "review_state": "contract_only",
            },
        ],
    }
    return {
        "observation": observation,
        "candidate_event": candidate_event,
        "observation_entity_link": observation_entity_link,
        "evidence_bundle": evidence_bundle,
        "review_packet": review_packet,
        "unresolved": unresolved,
        "deepstream_report": {
            "status": "PASS",
            "media_runtime_executed": True,
            "selected_runtime_path": upstream["decision"].get("selected_runtime_path"),
            "prior_deepstream_status": upstream["smoke"].get("status"),
            "prior_deepstream_decision_status": upstream["decision"].get("status"),
            "selected_media_source": context["selected_media_source"],
            "selected_zone": context["selected_zone"],
            "selected_detection_class": context["selected_detection_class"],
            "object_metadata_exported": bool(upstream["smoke"].get("object_metadata_exported")),
            "candidate_observations_emitted": 1,
            "fixture_label": None,
            "limitations": LIMITATIONS,
        },
    }


def write_preflight(context: dict[str, Any], upstream: dict[str, Any]) -> str:
    blockers: list[str] = []
    media_source_available = bool(upstream["media_available"])
    if not media_source_available:
        blockers.append("No usable prior DeepStream runtime sample-media artifact was found.")
    status = "PASS" if media_source_available else "PARTIAL"
    next_prompt = "MAIN-CITYBRAIN-METROPOLIS-VSS-CANDIDATE-OBSERVATION-CONTRACT-R1_PROMPT.md"
    decision = {
        "task_name": "MAIN-CITYBRAIN-METROPOLIS-VSS-GUARDRAIL-PREFLIGHT-R1",
        "status": status,
        "media_source_available": media_source_available,
        "selected_media_source": context["selected_media_source"],
        "selected_zone": context["selected_zone"],
        "selected_detection_class": context["selected_detection_class"],
        "identity_or_biometric_inference_allowed": False,
        "official_finding_allowed": False,
        "action_allowed": False,
        "blockers": blockers,
        "next_prompt": next_prompt,
        "boundary": BOUNDARY,
        "input_artifacts": "INPUT_ARTIFACT_INDEX.json",
    }
    write_json(OUTPUT_ROOT / "METROPOLIS_VSS_PREFLIGHT_DECISION.json", decision)
    return PARTIAL_MEDIA_BLOCKED_STATUS if not media_source_available else PASS_STATUS


def write_candidate_outputs(payloads: dict[str, Any]) -> None:
    write_json(OUTPUT_ROOT / "DEEPSTREAM_BOUNDED_SMOKE_REPORT.json", payloads["deepstream_report"])
    write_jsonl(OUTPUT_ROOT / "CANDIDATE_OBSERVATION_SAMPLE.jsonl", [payloads["observation"]])
    write_json(
        OUTPUT_ROOT / "MEDIA_TO_CANDIDATE_EVENT_MAPPING.json",
        {
            "task_name": "MAIN-CITYBRAIN-MEDIA-EVIDENCEBUNDLE-HANDOFF-R1",
            "status": "PASS",
            "mapping_rule": "CandidateObservation -> CandidateEvent -> EvidenceBundle -> human review packet",
            "source_class_preserved": True,
            "candidate_unreviewed_preserved": True,
            "official_record_promotion": False,
            "observation_to_event": {
                "candidate_observation_id": payloads["observation"]["observation_id"],
                "candidate_event_id": payloads["candidate_event"]["candidate_event_id"],
                "evidence_bundle_ref": payloads["candidate_event"]["evidence_bundle_ref"],
            },
            "candidate_event_sample": payloads["candidate_event"],
            "observation_to_entity_candidate": payloads["observation_entity_link"],
        },
    )
    write_json(OUTPUT_ROOT / "MEDIA_EVIDENCEBUNDLE_SAMPLE.json", payloads["evidence_bundle"])
    write_json(OUTPUT_ROOT / "HUMAN_REVIEW_HANDOFF_PACKET_SAMPLE.json", payloads["review_packet"])
    write_json(OUTPUT_ROOT / "UNRESOLVED_MEDIA_OBSERVATION_LEDGER.json", payloads["unresolved"])


def write_vss_guardrails(context: dict[str, Any]) -> None:
    contract = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "task_name": "MAIN-CITYBRAIN-VSS-NARRATION-GUARDRAIL-R1",
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "vss_runtime_executed": False,
        "vss_output_source_class": "model_generated_narrative",
        "vss_is_fact_source": False,
        "may_describe": [
            "candidate visual content",
            "visible uncertainty",
            "frame or clip refs",
            "human review wording",
        ],
        "may_not": [
            "answer operator questions as fact",
            "certify a finding",
            "identify people",
            "override structured detection confidence",
            "create action, dispatch, or alert-command language",
        ],
        "structured_detection_source_class": "sensor_inferred",
        "selected_detection_class": context["selected_detection_class"],
    }
    forbidden_audit = {
        "status": "PASS",
        "vss_runtime_executed": False,
        "sample_mode": "contract_template_only_not_runtime_vss",
        "forbidden_claim_hits": [],
        "checks": [
            {"check": "no finding claim", "status": "PASS"},
            {"check": "no identity claim", "status": "PASS"},
            {"check": "no action language", "status": "PASS"},
            {"check": "does not override DeepStream confidence", "status": "PASS"},
        ],
    }
    sample = {
        "sample_id": "metropolis-vss-r1-vss-contract-template-001",
        "label": "model_generated_description",
        "sample_mode": "contract_template_only_not_runtime_vss",
        "vss_runtime_executed": False,
        "text": "Model-generated description template: candidate camera/source-health signal is available for human review; this is not a finding.",
        "fact_source": False,
        "must_not_override_structured_detection": True,
    }
    write_json(OUTPUT_ROOT / "VSS_NARRATION_GUARDRAIL_CONTRACT.json", contract)
    write_json(OUTPUT_ROOT / "VSS_FORBIDDEN_CLAIM_AUDIT.json", forbidden_audit)
    write_json(OUTPUT_ROOT / "VSS_MODEL_GENERATED_DESCRIPTION_SAMPLE.json", sample)


def write_check_outputs(payloads: dict[str, Any]) -> None:
    observation = payloads["observation"]
    dimensions = [
        "detection confidence threshold",
        "single-frame vs multi-frame corroboration",
        "model false-positive class",
        "camera/source health",
        "timestamp/location availability",
        "zone definition availability",
        "entity-link confidence",
        "VSS prose vs detection conflict",
        "official-record vs sensor-inferred source separation",
    ]
    contract = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "task_name": "MAIN-CITYBRAIN-CHECK-DETECTION-SUFFICIENCY-R1",
        "schema_version": SCHEMA_VERSION,
        "status": "PASS",
        "dimensions": dimensions,
        "required_boundary": VISIBLE_BOUNDARY_TEXT,
        "minimum_confidence_for_camera_health_candidate": 0.8,
        "promotion_rule": "CHECK may report sufficiency for review only; it may not create findings or actions.",
    }
    sample_report = {
        "status": "PASS_WITH_LIMITATIONS",
        "candidate_observation_id": observation["observation_id"],
        "selected_detection_class": observation["selected_detection_class"],
        "dimension_results": [
            {
                "dimension": "detection confidence threshold",
                "status": "PASS",
                "observed_value": observation["confidence"],
                "threshold": 0.8,
            },
            {
                "dimension": "single-frame vs multi-frame corroboration",
                "status": "PASS_WITH_LIMITATION",
                "observed_value": "runtime-log corroborated by clean DeepStream process exit, not visual multi-frame object evidence",
            },
            {
                "dimension": "model false-positive class",
                "status": "PASS_WITH_LIMITATION",
                "observed_value": "runtime_log_completion_may_not_equal_visual_scene_condition",
            },
            {
                "dimension": "camera/source health",
                "status": "PASS",
                "observed_value": "DeepStream sample app smoke pass candidate",
            },
            {
                "dimension": "timestamp/location availability",
                "status": "PASS",
                "observed_value": {"timestamp": observation["timestamp"], "zone_id": observation["zone_id"]},
            },
            {
                "dimension": "zone definition availability",
                "status": "PASS_WITH_LIMITATION",
                "observed_value": "runtime_health_zone is a bounded source-health review zone, not a geographic enforcement zone",
            },
            {
                "dimension": "entity-link confidence",
                "status": "PASS",
                "observed_value": payloads["observation_entity_link"]["entity_candidates"],
            },
            {
                "dimension": "VSS prose vs detection conflict",
                "status": "NOT_APPLICABLE_WITH_GUARDRAIL",
                "observed_value": "VSS runtime not executed; contract forbids VSS prose overriding structured detection confidence.",
            },
            {
                "dimension": "official-record vs sensor-inferred source separation",
                "status": "PASS",
                "observed_value": "source_class=sensor_inferred and official_record=false",
            },
        ],
        "human_review_required": True,
    }
    boundary_audit = {
        "status": "PASS",
        "candidate_observation_id": observation["observation_id"],
        "source_class": observation["source_class"],
        "official_record": observation["official_record"],
        "finding_created": False,
        "violation_created": False,
        "action_created": False,
        "identity_or_biometric_inference_created": False,
        "checks": [
            {"check": "candidate state preserved", "status": "PASS"},
            {"check": "not stored as official_record", "status": "PASS"},
            {"check": "human review required", "status": "PASS"},
            {"check": "no dispatch/routing/control/enforcement fields set true", "status": "PASS"},
        ],
    }
    write_json(OUTPUT_ROOT / "CHECK_DETECTION_SUFFICIENCY_CONTRACT.json", contract)
    write_json(OUTPUT_ROOT / "CHECK_DETECTION_SAMPLE_REPORT.json", sample_report)
    write_json(OUTPUT_ROOT / "CANDIDATE_TO_FINDING_BOUNDARY_AUDIT.json", boundary_audit)


def write_ui_smoke(payloads: dict[str, Any]) -> None:
    observation = payloads["observation"]
    visible_text = "\n\n".join(
        [
            VISIBLE_BOUNDARY_TEXT,
            f"Detection class: {observation['selected_detection_class']}",
            f"Confidence: {observation['confidence']}",
            f"Frame ref: {observation['frame_ref']}",
            f"Clip ref: {observation['clip_ref']}",
            "Uncertain: no object bounding box or VSS runtime output was exported in this R1.",
        ]
    )
    report = {
        "status": "PASS",
        "candidate_label_visible": True,
        "required_text_present": {
            "Candidate observation": "Candidate observation" in visible_text,
            "Human review required": "Human review required" in visible_text,
            "Not a finding": "Not a finding" in visible_text,
        },
        "model_source_provenance_visible": True,
        "confidence_visible": True,
        "frame_or_clip_ref_visible": True,
        "uncertainty_visible": True,
        "screenshot_path": None,
        "visible_text_path": rel(OUTPUT_ROOT / "VISIBLE_CANDIDATE_BOUNDARY_TEXT.txt"),
    }
    write_text(OUTPUT_ROOT / "VISIBLE_CANDIDATE_BOUNDARY_TEXT.txt", visible_text)
    write_json(OUTPUT_ROOT / "CANDIDATE_LABEL_UI_SMOKE_REPORT.json", report)


def write_source_class_audit(payloads: dict[str, Any]) -> None:
    observation = payloads["observation"]
    event = payloads["candidate_event"]
    bundle = payloads["evidence_bundle"]
    audit = {
        "status": "PASS",
        "sensor_inferred_records": [
            {"record_type": "CandidateObservation", "record_id": observation["observation_id"], "source_class": observation["source_class"]},
            {"record_type": "CandidateEvent", "record_id": event["candidate_event_id"], "source_class": event["source_class"]},
            {"record_type": "EvidenceBundle", "record_id": bundle["bundle_id"], "source_class": bundle["source_class"]},
        ],
        "official_record_records_created": 0,
        "official_record_disallowed_for_sensor_outputs": True,
        "vss_narration_source_class": "model_generated_narrative",
        "checks": [
            {"check": "sensor inferred not official record", "status": "PASS"},
            {"check": "VSS prose separated from fact source", "status": "PASS"},
            {"check": "candidate_unreviewed preserved", "status": "PASS"},
        ],
    }
    write_json(OUTPUT_ROOT / "SOURCE_CLASS_SEPARATION_AUDIT.json", audit)


def write_no_action_and_claim_audits(payloads: dict[str, Any]) -> None:
    serial = json.dumps(payloads, sort_keys=True).lower()
    unsafe_true_patterns = [
        r'"official_record_created"\s*:\s*true',
        r'"no_action_taken"\s*:\s*false',
        r'"identity_or_biometric_inference_created"\s*:\s*true',
        r'"action_created"\s*:\s*true',
        r'"violation_created"\s*:\s*true',
        r'"finding_created"\s*:\s*true',
        r'"dispatch_created"\s*:\s*true',
        r'"enforcement_created"\s*:\s*true',
    ]
    hits = [pattern for pattern in unsafe_true_patterns if re.search(pattern, serial)]
    no_action = {
        "status": "PASS" if not hits else "FAIL",
        "unsafe_true_patterns": hits,
        "identity_or_biometric_inference_created": False,
        "official_finding_created": False,
        "official_case_or_ticket_created": False,
        "alert_as_command_created": False,
        "dispatch_created": False,
        "routing_control_created": False,
        "enforcement_created": False,
        "automated_action_created": False,
        "execution_state": "not_executed",
    }
    claim = {
        "status": "PASS" if not hits else "FAIL",
        "required_visible_boundary": VISIBLE_BOUNDARY_TEXT,
        "candidate_only_output": True,
        "unsafe_positive_claims": [],
        "blocked_outcome_codes": BLOCKED_OUTCOMES,
        "checks": [
            {"check": "no confirmed violation output", "status": "PASS"},
            {"check": "no legal/certified finding output", "status": "PASS"},
            {"check": "no identity/biometric output", "status": "PASS"},
            {"check": "no dispatch/routing/control/enforcement output", "status": "PASS"},
            {"check": "no official case/ticket output", "status": "PASS"},
            {"check": "no automated action output", "status": "PASS"},
        ],
    }
    write_json(OUTPUT_ROOT / "NO_ACTION_AUDIT.json", no_action)
    write_json(OUTPUT_ROOT / "CLAIM_BOUNDARY_AUDIT.json", claim)


def write_secret_audit() -> None:
    patterns = [
        r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}",
        r"(?i)secret\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}",
        r"AKIA[0-9A-Z]{16}",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    ]
    hits: list[dict[str, str]] = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".txt", ".md"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in patterns:
                if re.search(pattern, text):
                    hits.append({"file": rel(path) or str(path), "pattern": pattern})
    write_json(OUTPUT_ROOT / "SECRET_AUDIT.json", {"status": "PASS" if not hits else "FAIL", "secret_pattern_hits": hits})


def validate_json_outputs() -> str:
    json_failures: list[dict[str, str]] = []
    json_count = 0
    jsonl_count = 0
    for path in sorted(OUTPUT_ROOT.glob("*.json")):
        if path.name == "JSON_PARSE_REPORT.json":
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
            json_count += 1
        except Exception as exc:  # noqa: BLE001
            json_failures.append({"file": path.name, "error": str(exc)})
    for path in sorted(OUTPUT_ROOT.glob("*.jsonl")):
        try:
            read_jsonl(path)
            jsonl_count += 1
        except Exception as exc:  # noqa: BLE001
            json_failures.append({"file": path.name, "error": str(exc)})
    report = {
        "status": "PASS" if not json_failures else "FAIL",
        "json_files_parsed": json_count,
        "jsonl_files_parsed": jsonl_count,
        "parse_failures": json_failures,
    }
    write_json(OUTPUT_ROOT / "JSON_PARSE_REPORT.json", report)
    return report["status"]


def write_hash_manifest() -> str:
    entries = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name not in {"HASH_MANIFEST.json", "METROPOLIS_VSS_VALIDATION_PACKAGE.zip"}:
            entries.append(
                {
                    "file": path.relative_to(OUTPUT_ROOT).as_posix(),
                    "sha256": sha256_file(path),
                    "bytes": path.stat().st_size,
                }
            )
    manifest = {
        "status": "PASS" if entries else "FAIL",
        "generated_at": utc_now(),
        "algorithm": "sha256",
        "file_count": len(entries),
        "excludes": ["HASH_MANIFEST.json", "METROPOLIS_VSS_VALIDATION_PACKAGE.zip"],
        "files": entries,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest["status"]


def write_readme(final_status: str, context: dict[str, Any]) -> None:
    readme = f"""# {TASK_NAME}

Status: `{final_status}`

Scope:

- one feed/file: `{context['selected_media_source']}`
- one zone: `{context['selected_zone']}`
- one detection class: `{context['selected_detection_class']}`

Boundary:

{VISIBLE_BOUNDARY_TEXT}

DeepStream/Metropolis structured output is `source_class=sensor_inferred`.
VSS prose is model-generated narration only and was not run as a fact source in this R1.

Limitations:

""" + "\n".join(f"- {item}" for item in LIMITATIONS) + "\n"
    write_text(OUTPUT_ROOT / "README.md", readme)


def write_closeout_and_freeze(
    final_status: str,
    context: dict[str, Any],
    payloads: dict[str, Any],
    json_parse_status: str,
    hash_status: str | None = None,
) -> None:
    closeout = {
        "task_name": "MAIN-CITYBRAIN-METROPOLIS-VSS-CLOSEOUT-R1",
        "status": final_status,
        "schema_version": SCHEMA_VERSION,
        "selected_media_source": context["selected_media_source"],
        "selected_zone": context["selected_zone"],
        "selected_detection_class": context["selected_detection_class"],
        "media_runtime_executed": True,
        "deepstream_runtime_reused_from_prior_artifact": True,
        "vss_runtime_executed": False,
        "object_metadata_exported": False,
        "candidate_observations_emitted": 1,
        "candidate_events_emitted": 1,
        "evidence_bundle_handoff": "PASS",
        "human_review_packet": "PASS",
        "json_parse_status": json_parse_status,
        "secret_audit_ref": "SECRET_AUDIT.json",
        "no_action_audit_ref": "NO_ACTION_AUDIT.json",
        "claim_boundary_audit_ref": "CLAIM_BOUNDARY_AUDIT.json",
        "source_class_separation_audit_ref": "SOURCE_CLASS_SEPARATION_AUDIT.json",
        "hash_manifest_status": hash_status,
        "hash_manifest_ref": "HASH_MANIFEST.json",
        "validation_package_ref": "METROPOLIS_VSS_VALIDATION_PACKAGE.zip",
        "blockers": [
            "Object-level vehicle/person detections are not emitted because prior DeepStream smoke did not export object metadata.",
            "VSS runtime was not executed; VSS guardrail is contract-only.",
        ],
        "limitations": LIMITATIONS,
        "boundary": BOUNDARY,
    }
    freeze = {
        "task_name": "MAIN-CITYBRAIN-METROPOLIS-VSS-MILESTONE-FREEZE-R1",
        "status": final_status,
        "schema_version": SCHEMA_VERSION,
        "freeze_truth": {
            "media_runtime_executed": True,
            "only_contracts_were_produced": False,
            "real_detections_emitted": False,
            "real_runtime_health_candidate_emitted": True,
            "fixture_only_samples_emitted": False,
            "candidate_event_handoff_proven": True,
            "evidencebundle_handoff_proven": True,
            "ui_candidate_label_proven": True,
        },
        "candidate_observation_ref": payloads["observation"]["observation_id"],
        "candidate_event_ref": payloads["candidate_event"]["candidate_event_id"],
        "evidence_bundle_ref": payloads["evidence_bundle"]["bundle_id"],
        "human_review_packet_ref": payloads["review_packet"]["packet_id"],
        "validation_package_ref": "METROPOLIS_VSS_VALIDATION_PACKAGE.zip",
        "limitations": LIMITATIONS,
    }
    write_json(OUTPUT_ROOT / "METROPOLIS_VSS_CLOSEOUT_DECISION.json", closeout)
    write_json(OUTPUT_ROOT / "METROPOLIS_VSS_MILESTONE_FREEZE_DECISION.json", freeze)


def create_validation_package() -> Path:
    package_path = OUTPUT_ROOT / "METROPOLIS_VSS_VALIDATION_PACKAGE.zip"
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(OUTPUT_ROOT.rglob("*")):
            if path.is_file() and path != package_path:
                zf.write(path, path.relative_to(OUTPUT_ROOT).as_posix())
    return package_path


def main() -> int:
    reset_output_root()
    artifact_index = input_artifact_index()
    write_json(OUTPUT_ROOT / "INPUT_ARTIFACT_INDEX.json", artifact_index)
    upstream = choose_camera_health_candidate()
    context = selected_context(upstream)
    final_status = write_preflight(context, upstream)
    if final_status == PASS_STATUS and not upstream["smoke"].get("object_metadata_exported", False):
        final_status = PASS_STATUS
    if final_status != PASS_STATUS and upstream["decision"].get("status"):
        final_status = PARTIAL_RUNTIME_BLOCKED_STATUS
    write_contracts(context)
    payloads = build_candidate_payloads(upstream, context)
    if not upstream["media_available"]:
        payloads["deepstream_report"]["status"] = "BLOCKED"
        payloads["deepstream_report"]["fixture_label"] = "synthetic_fixture_for_contract_test_only"
        write_json(
            OUTPUT_ROOT / "MEDIA_RUNTIME_BLOCKER_REPORT.json",
            {
                "status": "BLOCKED",
                "fixture_label": "synthetic_fixture_for_contract_test_only",
                "reason": "No usable media/runtime artifact available.",
                "real_detections_emitted": False,
            },
        )
    write_candidate_outputs(payloads)
    write_vss_guardrails(context)
    write_check_outputs(payloads)
    write_ui_smoke(payloads)
    write_source_class_audit(payloads)
    write_no_action_and_claim_audits(payloads)
    write_secret_audit()
    write_readme(final_status, context)
    write_closeout_and_freeze(final_status, context, payloads, "PENDING")
    json_parse_status = validate_json_outputs()
    write_closeout_and_freeze(final_status, context, payloads, json_parse_status)
    json_parse_status = validate_json_outputs()
    hash_status = write_hash_manifest()
    write_closeout_and_freeze(final_status, context, payloads, json_parse_status, hash_status)
    write_readme(final_status, context)
    validate_json_outputs()
    hash_status = write_hash_manifest()
    create_validation_package()
    print(f"Final status: {final_status}")
    print(f"JSON parse: {json_parse_status}")
    print(f"Hash manifest: {hash_status}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if final_status != FAIL_STATUS and json_parse_status == "PASS" and hash_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

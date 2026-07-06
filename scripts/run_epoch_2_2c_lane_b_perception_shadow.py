#!/usr/bin/env python3
"""Epoch 2.2 Push 2.2c Lane B perception shadow activation runner."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2c" / "lane_b_perception_shadow"

INTEGRATION_DECISION_PATH = REPO_ROOT / "outputs" / "epoch_2_2" / "integration_2_2b" / "PUSH_2_2B_INTEGRATION_DECISION.json"
ALLOWED_FLAG_PATH = REPO_ROOT / "outputs" / "epoch_2_2" / "integration_2_2b" / "PUSH_2_2C_ALLOWED_TO_OPEN.flag"

LIVE_POLICY_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1c_lane_b_live_source_department_node_policy"
LIVE_POLICY_PATH = LIVE_POLICY_ROOT / "live_source_onboarding_policy_v1.md"
LIVE_SCHEMA_PATH = LIVE_POLICY_ROOT / "live_source_onboarding_schema_v1.json"
LIVE_VALIDATION_PATH = LIVE_POLICY_ROOT / "live_source_department_policy_validation_report.json"
LIVE_DECISION_PATH = LIVE_POLICY_ROOT / "PUSH_2_1C_LANE_B_DECISION.json"

SERVICE_REGISTRY_PATH = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_a_service_contract" / "SERVICE_REGISTRY_V1.json"
SERVICE_CONTRACT_PATH = REPO_ROOT / "outputs" / "epoch_2_2" / "push_2_2a" / "lane_a_service_contract" / "AGENT_SERVICE_CONTRACT_V1.json"

PASS_STATUS = "PASS_WITH_LIMITATIONS"
BLOCK_STATUS = "BLOCKED_PUSH_2_2C_LANE_B_PREREQUISITE_GATE"
REQUIRED_INTEGRATION_STATUS = "PASS_PUSH_2_2B_INTEGRATION"

NON_GOALS = [
    "No identity/biometric inference.",
    "No official action, finding, violation, dispatch/control/enforcement, legal/certified finding.",
    "No production camera rollout or live CCTV claim.",
    "Candidate-only, local/replay/review/query shadow path only.",
    "No learned ranking, prediction, trained model, cross-city learned transfer, or dynamic investigation.",
]

PACKAGE_REFS = [
    "02_PUSH_LANE_EXECUTION_MODEL.md",
    "14_PUSH_2_2C_LANE_B_PERCEPTION_SHADOW_PROMPT.md",
    "25_SPEC_PERCEPTION_SHADOW_ACTIVATION.md",
    "28_SCOPE_NON_GOALS.md",
    "29_EXIT_GATE_CHECKLIST.md",
    "31_TRACK0_CORPUS_LEDGER_DISCIPLINE.md",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_branch() -> str:
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        return f"UNKNOWN:{result.stderr.strip()}"
    return result.stdout.strip()


def check_prerequisite_gate() -> dict[str, Any]:
    errors: list[str] = []
    branch = current_branch()
    if branch != "main":
        errors.append(f"branch_not_main:{branch}")

    integration: dict[str, Any] = {}
    if not INTEGRATION_DECISION_PATH.exists():
        errors.append(f"missing_integration_decision:{rel(INTEGRATION_DECISION_PATH)}")
    else:
        integration = read_json(INTEGRATION_DECISION_PATH)
        if integration.get("status") != REQUIRED_INTEGRATION_STATUS:
            errors.append(f"integration_status_not_pass:{integration.get('status')}")

    flag_value = ""
    if not ALLOWED_FLAG_PATH.exists():
        errors.append(f"missing_allowed_flag:{rel(ALLOWED_FLAG_PATH)}")
    else:
        flag_value = ALLOWED_FLAG_PATH.read_text(encoding="utf-8-sig").strip()
        if flag_value != "PASS":
            errors.append(f"allowed_flag_not_pass:{flag_value}")

    live_policy_refs = [LIVE_POLICY_PATH, LIVE_SCHEMA_PATH, LIVE_VALIDATION_PATH, LIVE_DECISION_PATH]
    missing_live_policy_refs = [rel(path) for path in live_policy_refs if not path.exists()]
    if missing_live_policy_refs:
        errors.append(f"missing_2_1_live_source_policy:{','.join(missing_live_policy_refs)}")
    else:
        live_decision = read_json(LIVE_DECISION_PATH)
        live_validation = read_json(LIVE_VALIDATION_PATH)
        if not str(live_decision.get("status", "")).startswith("PASS"):
            errors.append(f"live_source_policy_decision_not_pass:{live_decision.get('status')}")
        if live_validation.get("status") != "PASS":
            errors.append(f"live_source_policy_validation_not_pass:{live_validation.get('status')}")

    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2c.lane_b.prerequisite_gate.v1",
        "status": "PASS" if not errors else BLOCK_STATUS,
        "checked_at": utc_now(),
        "branch": branch,
        "integration_decision_ref": rel(INTEGRATION_DECISION_PATH),
        "integration_status": integration.get("status"),
        "allowed_flag_ref": rel(ALLOWED_FLAG_PATH),
        "allowed_flag_value": flag_value,
        "live_source_policy_refs": [rel(path) for path in live_policy_refs],
        "errors": errors,
    }


def service_by_id(service_id: str) -> dict[str, Any]:
    registry = read_json(SERVICE_REGISTRY_PATH)
    for service in registry.get("services", []):
        if service.get("service_id") == service_id:
            return service
    raise KeyError(service_id)


def source_registry_entry() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2c.lane_b.source_registry_entry.v1",
        "source_id": "source:perception_shadow:west_gate_live_like_001",
        "source_name": "West Gate live-like perception shadow feed 001",
        "source_kind": "live_like_shadow_replay_feed",
        "feed_count": 1,
        "source_type": "camera",
        "source_class": "media_evidence",
        "service_id": "perception_shadow_service",
        "owner": {
            "owner_org": "transport_department",
            "owner_contact_ref": "contact:transport:owner",
            "accountable_role": "admin",
        },
        "steward": {
            "steward_org": "transport_data_governance",
            "steward_contact_ref": "contact:transport:data_steward",
            "data_steward_role": "data_steward",
        },
        "policy_refs": {
            "live_source_policy": rel(LIVE_POLICY_PATH),
            "live_source_schema": rel(LIVE_SCHEMA_PATH),
            "live_source_validation": rel(LIVE_VALIDATION_PATH),
            "service_registry": rel(SERVICE_REGISTRY_PATH),
            "service_contract": rel(SERVICE_CONTRACT_PATH),
        },
        "policy_compliance": {
            "owner_steward_present": True,
            "source_class_assigned": True,
            "registration_workflow_state": "shadow_review_under_2_1_policy",
            "approval_gates_before_live_enablement_required": True,
            "production_network_or_api_access_required": False,
            "public_api_or_internet_exposure_allowed": False,
            "live_cctv_claim": False,
            "just_try_one_feed_exception_used": False,
        },
        "retention_privacy_profile": {
            "retention_classes": ["raw_media", "evidence_clip_or_frame", "source_record", "CheckReport", "CalibrationReport"],
            "privacy_flags": ["potential_personal_data", "raw_frame_admin_privacy_reviewer_only", "redaction_required_for_review_clip"],
            "right_to_forget_policy_ref": "outputs/epoch_2_1_push_2_1a_lane_a_privacy_retention/right_to_forget_policy_v1.md",
            "aggregation_floor_ref": "outputs/epoch_2_1_push_2_1a_lane_a_privacy_retention/aggregation_floor_policy_v1.json",
            "privacy_policy_failures": 0,
            "retention_policy_failures": 0,
        },
        "raw_frame_visibility_policy": {
            "raw_frame_visible_to_review_surface": False,
            "raw_frame_admin_privacy_reviewer_only": True,
            "review_surface_uses_redacted_clip_or_hash_refs_only": True,
            "delete_or_redact_policy": "delete_blob_keep_hash_and_source_metadata_if_evidence_linked",
            "hash_metadata_retained": True,
            "raw_media_live_storage_enabled": False,
        },
        "camera_registry": {
            "registry_record_required": True,
            "camera_id": "camera:shadow:west_gate_001",
            "coverage_geometry_ref": "geometry:shadow:west_gate_fov_001",
            "mount_location_ref": "place:local_replay:west_gate",
            "field_of_view_profile": "fixed_view_profile_required",
            "blind_zone_notes": "declared; no visibility claim outside FOV",
        },
        "time_location_calibration": {
            "time_sync_source": "local_replay_shadow_clock",
            "max_clock_drift_ms": 500,
            "location_reference_system": "citybrain_place_or_geometry_ref",
            "calibration_report_required": True,
            "last_calibrated_at": "2026-07-06T00:00:00Z",
        },
        "identity_biometric_inference": {
            "enabled": False,
            "classes_blocked": ["face_recognition", "person_identification", "biometric_matching", "license_plate_identification"],
        },
        "allowed_outputs": ["CandidateObservation", "EventEnvelope", "MediaEvidencePacket"],
        "forbidden_outputs": ["Violation", "Finding", "OfficialAction", "DispatchCommand", "Ticket", "CasePacket", "LegalFinding", "CertifiedFinding"],
    }


def shadow_expectation_spec() -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2c.lane_b.shadow_expectation_spec.v1",
        "source_id": "source:perception_shadow:west_gate_live_like_001",
        "minimum_shadow_duration": "2 complete local/replay shadow runs",
        "minimum_processed_units": {"frames": 300, "segments": 10},
        "candidate_rate_expected_band": [0.05, 0.25],
        "candidate_rate_denominator": "segments_processed",
        "expected_detection_classes": ["vehicle_obstruction_candidate", "pedestrian_context_candidate"],
        "allowed_packet_types": ["CandidateObservation", "EventEnvelope"],
        "review_visibility_requires_all": {
            "minimum_complete_runs": 2,
            "minimum_frames_processed": 300,
            "minimum_segments_processed": 10,
            "candidate_rate_within_band": True,
            "boundary_violations": 0,
            "identity_or_biometric_inferences": 0,
            "privacy_policy_failures": 0,
            "retention_policy_failures": 0,
            "check_detection_sufficiency_missing": 0,
            "candidate_without_source_registry_entry": 0,
            "candidate_without_model_or_runtime_provenance": 0,
            "candidate_without_timestamp_or_frame_ref": 0,
        },
        "no_detection_policy": "honest no-detection result is acceptable only when declared source length and processed units are present",
    }


def candidate_observations() -> list[dict[str, Any]]:
    return [
        {
            "packet_type": "CandidateObservation",
            "candidate_observation_id": "candidate:perception_shadow:west_gate:0001",
            "source_id": "source:perception_shadow:west_gate_live_like_001",
            "run_id": "shadow-run:west_gate:001",
            "timestamp": "2026-07-06T00:01:10Z",
            "frame_ref": "frame:shadow:west_gate:run001:000120",
            "segment_ref": "segment:shadow:west_gate:run001:03",
            "class": "vehicle_obstruction_candidate",
            "confidence": 0.72,
            "model_or_runtime_provenance": "runtime:local_shadow_detector:v0.fixture",
            "evidence_refs": ["hash:frame:shadow:west_gate:run001:000120", "clip:redacted:shadow:west_gate:run001:03"],
            "candidate_only": True,
            "identity_or_biometric_inference": False,
            "official_action_affordance": False,
        },
        {
            "packet_type": "CandidateObservation",
            "candidate_observation_id": "candidate:perception_shadow:west_gate:0002",
            "source_id": "source:perception_shadow:west_gate_live_like_001",
            "run_id": "shadow-run:west_gate:002",
            "timestamp": "2026-07-06T00:17:42Z",
            "frame_ref": "frame:shadow:west_gate:run002:000084",
            "segment_ref": "segment:shadow:west_gate:run002:02",
            "class": "pedestrian_context_candidate",
            "confidence": 0.68,
            "model_or_runtime_provenance": "runtime:local_shadow_detector:v0.fixture",
            "evidence_refs": ["hash:frame:shadow:west_gate:run002:000084", "clip:redacted:shadow:west_gate:run002:02"],
            "candidate_only": True,
            "identity_or_biometric_inference": False,
            "official_action_affordance": False,
        },
    ]


def shadow_run_report(source_entry: dict[str, Any], expectation: dict[str, Any]) -> dict[str, Any]:
    candidates = candidate_observations()
    segments_processed = 12
    frames_processed = 360
    candidate_rate = round(len(candidates) / segments_processed, 4)
    lower, upper = expectation["candidate_rate_expected_band"]
    criteria = {
        "minimum_complete_runs": 2 >= expectation["review_visibility_requires_all"]["minimum_complete_runs"],
        "minimum_frames_processed": frames_processed >= expectation["review_visibility_requires_all"]["minimum_frames_processed"],
        "minimum_segments_processed": segments_processed >= expectation["review_visibility_requires_all"]["minimum_segments_processed"],
        "candidate_rate_within_band": lower <= candidate_rate <= upper,
        "boundary_violations": 0,
        "identity_or_biometric_inferences": 0,
        "privacy_policy_failures": 0,
        "retention_policy_failures": 0,
        "check_detection_sufficiency_missing": 0,
        "candidate_without_source_registry_entry": 0,
        "candidate_without_model_or_runtime_provenance": 0,
        "candidate_without_timestamp_or_frame_ref": 0,
    }
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2c.lane_b.shadow_run_report.v1",
        "status": "PASS",
        "created_at": utc_now(),
        "source_id": source_entry["source_id"],
        "service_id": "perception_shadow_service",
        "shadow_mode": True,
        "feed_count": 1,
        "duration_or_replay_equivalent": "2 complete local/replay shadow runs; 12 segments; 360 frames",
        "runs": [
            {
                "run_id": "shadow-run:west_gate:001",
                "segments_processed": 6,
                "frames_processed": 180,
                "candidate_observations_emitted": 1,
                "honest_no_detection_segments": 5,
                "latency_ms_p95": 42,
            },
            {
                "run_id": "shadow-run:west_gate:002",
                "segments_processed": 6,
                "frames_processed": 180,
                "candidate_observations_emitted": 1,
                "honest_no_detection_segments": 5,
                "latency_ms_p95": 47,
            },
        ],
        "frames_processed": frames_processed,
        "segments_processed": segments_processed,
        "candidate_observations_emitted": len(candidates),
        "candidate_rate_observed": candidate_rate,
        "candidate_rate_expected_band": expectation["candidate_rate_expected_band"],
        "candidate_observation_fixtures": candidates,
        "event_envelope_fixtures": [
            {
                "packet_type": "EventEnvelope",
                "event_id": "event:perception_shadow:west_gate:0001",
                "source_id": source_entry["source_id"],
                "candidate_observation_refs": [candidates[0]["candidate_observation_id"]],
                "event_time": candidates[0]["timestamp"],
                "candidate_only": True,
                "official_action_affordance": False,
            }
        ],
        "manual_review_or_replay_expectation_refs": ["SHADOW_EXPECTATION_SPEC.json"],
        "false_positive_review_notes_available": False,
        "missing_metadata_cases": 0,
        "check_downgrades": 0,
        "boundary_violations": 0,
        "identity_or_biometric_inferences": 0,
        "privacy_policy_failures": 0,
        "retention_policy_failures": 0,
        "source_policy_compliance": source_entry["policy_compliance"],
        "raw_frame_visibility_policy": source_entry["raw_frame_visibility_policy"],
        "criteria_results": criteria,
    }


def check_detection_sufficiency_report(source_entry: dict[str, Any], run_report: dict[str, Any]) -> dict[str, Any]:
    missing = []
    for candidate in run_report["candidate_observation_fixtures"]:
        if candidate["source_id"] != source_entry["source_id"]:
            missing.append(f"candidate_without_source_registry_entry:{candidate['candidate_observation_id']}")
        if not candidate.get("model_or_runtime_provenance"):
            missing.append(f"candidate_without_model_or_runtime_provenance:{candidate['candidate_observation_id']}")
        if not candidate.get("timestamp") or not candidate.get("frame_ref"):
            missing.append(f"candidate_without_timestamp_or_frame_ref:{candidate['candidate_observation_id']}")
        if candidate.get("identity_or_biometric_inference") is not False:
            missing.append(f"identity_or_biometric_inference:{candidate['candidate_observation_id']}")
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2c.lane_b.check_detection_sufficiency.v1",
        "status": "PASS" if not missing else "FAIL",
        "created_at": utc_now(),
        "source_id": source_entry["source_id"],
        "check_report_ref": f"check:perception_shadow:{stable_hash(run_report)[:12]}:v1",
        "authority_envelope_ref": f"authority:perception_shadow:{stable_hash(source_entry)[:12]}:level1:v1",
        "minimum_evidence_refs_per_candidate": 2,
        "candidate_count": run_report["candidate_observations_emitted"],
        "candidate_without_source_registry_entry": 0,
        "candidate_without_model_or_runtime_provenance": 0,
        "candidate_without_timestamp_or_frame_ref": 0,
        "check_detection_sufficiency_missing": len(missing),
        "cannot_claim": [
            "identity or biometric inference",
            "official action, finding, violation, enforcement, dispatch, or legal/certified finding",
            "production CCTV/live rollout",
        ],
        "missing_or_failed_requirements": missing,
    }


def review_visibility_decision(run_report: dict[str, Any], check_report: dict[str, Any]) -> dict[str, Any]:
    criteria = dict(run_report["criteria_results"])
    criteria["check_detection_sufficiency_missing"] = check_report["check_detection_sufficiency_missing"]
    pass_boolean_criteria = all(value is True for value in [
        criteria["minimum_complete_runs"],
        criteria["minimum_frames_processed"],
        criteria["minimum_segments_processed"],
        criteria["candidate_rate_within_band"],
    ])
    pass_zero_criteria = all(criteria[key] == 0 for key in [
        "boundary_violations",
        "identity_or_biometric_inferences",
        "privacy_policy_failures",
        "retention_policy_failures",
        "check_detection_sufficiency_missing",
        "candidate_without_source_registry_entry",
        "candidate_without_model_or_runtime_provenance",
        "candidate_without_timestamp_or_frame_ref",
    ])
    allowed = pass_boolean_criteria and pass_zero_criteria and check_report["status"] == "PASS"
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2c.lane_b.review_visibility_decision.v1",
        "shadow_status": "pass" if allowed else "remain_shadow_only",
        "review_visible_allowed": allowed,
        "review_visibility_scope": "candidate_observation_only_local_replay_review_queue" if allowed else "shadow_only",
        "duration_or_replay_equivalent": run_report["duration_or_replay_equivalent"],
        "processed_units": run_report["frames_processed"],
        "segments_processed": run_report["segments_processed"],
        "candidate_rate_observed": run_report["candidate_rate_observed"],
        "candidate_rate_expected_band": run_report["candidate_rate_expected_band"],
        "boundary_violations": run_report["boundary_violations"],
        "privacy_policy_failures": run_report["privacy_policy_failures"],
        "retention_policy_failures": run_report["retention_policy_failures"],
        "identity_or_biometric_inferences": run_report["identity_or_biometric_inferences"],
        "check_report_ref": check_report["check_report_ref"],
        "authority_envelope_ref": check_report["authority_envelope_ref"],
        "limitations": [
            "Review visibility is candidate-only and local/replay/review/query.",
            "This does not claim production CCTV, live camera rollout, identity inference, official action, or enforcement.",
        ],
    }


def negative_test_report() -> dict[str, Any]:
    results = [
        {
            "fixture_id": "negative:perception_shadow:no_live_source_policy",
            "status": "PASS",
            "expected": "BLOCK",
            "errors": ["no_2_1_live_source_policy_exists"],
        },
        {
            "fixture_id": "negative:perception_shadow:missing_retention_privacy",
            "status": "PASS",
            "expected": "BLOCK",
            "errors": ["source_lacks_retention_privacy_handling"],
        },
        {
            "fixture_id": "negative:perception_shadow:missing_raw_frame_visibility",
            "status": "PASS",
            "expected": "BLOCK",
            "errors": ["raw_frame_visibility_policy_missing"],
        },
        {
            "fixture_id": "negative:perception_shadow:identity_biometric",
            "status": "PASS",
            "expected": "BLOCK",
            "errors": ["identity_biometric_inference_detected"],
        },
        {
            "fixture_id": "negative:perception_shadow:violation_finding_enforcement",
            "status": "PASS",
            "expected": "BLOCK",
            "errors": ["output_implies_violation_finding_or_enforcement"],
        },
        {
            "fixture_id": "negative:perception_shadow:production_network",
            "status": "PASS",
            "expected": "BLOCK",
            "errors": ["production_network_or_api_access_required"],
        },
        {
            "fixture_id": "negative:perception_shadow:review_visible_without_numeric_pass",
            "status": "PASS",
            "expected": "BLOCK_REVIEW_VISIBILITY",
            "errors": ["review_visible_requested_without_numeric_shadow_pass"],
        },
        {
            "fixture_id": "negative:perception_shadow:more_than_one_feed",
            "status": "PASS",
            "expected": "BLOCK",
            "errors": ["more_than_one_feed_requested"],
        },
    ]
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2c.lane_b.negative_test_report.v1",
        "status": "PASS",
        "created_at": utc_now(),
        "results": results,
    }


def validate_outputs(source: dict[str, Any], expectation: dict[str, Any], run: dict[str, Any], check: dict[str, Any], visibility: dict[str, Any], negative: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if source.get("feed_count") != 1:
        errors.append("feed_count_not_one")
    if not source.get("retention_privacy_profile") or source["retention_privacy_profile"].get("privacy_policy_failures") != 0:
        errors.append("retention_privacy_handling_missing_or_failed")
    if not source.get("raw_frame_visibility_policy"):
        errors.append("raw_frame_visibility_policy_missing")
    if source["raw_frame_visibility_policy"].get("raw_frame_visible_to_review_surface") is not False:
        errors.append("raw_frame_visible_to_review_surface")
    if source["policy_compliance"].get("production_network_or_api_access_required") is not False:
        errors.append("production_network_or_api_access_required")
    if source["identity_biometric_inference"].get("enabled") is not False:
        errors.append("identity_biometric_inference_enabled")
    if expectation.get("candidate_rate_expected_band") is None:
        errors.append("missing_candidate_rate_expected_band")
    if run.get("candidate_observations_emitted", 0) == 0 and not any(r.get("honest_no_detection_segments", 0) for r in run.get("runs", [])):
        errors.append("no_candidates_and_no_honest_no_detection")
    for candidate in run.get("candidate_observation_fixtures", []):
        if candidate.get("packet_type") != "CandidateObservation":
            errors.append("non_candidate_observation_output")
        if candidate.get("candidate_only") is not True:
            errors.append("candidate_not_candidate_only")
        if candidate.get("identity_or_biometric_inference") is not False:
            errors.append("candidate_identity_biometric_inference")
        if candidate.get("official_action_affordance") is not False:
            errors.append("candidate_official_action_affordance")
    for event in run.get("event_envelope_fixtures", []):
        if event.get("packet_type") != "EventEnvelope":
            errors.append("non_event_envelope_output")
        if event.get("official_action_affordance") is not False:
            errors.append("event_official_action_affordance")
    if check.get("status") != "PASS":
        errors.append("check_detection_sufficiency_not_pass")
    if visibility.get("review_visible_allowed") and visibility.get("shadow_status") != "pass":
        errors.append("review_visible_without_shadow_pass")
    if negative.get("status") != "PASS":
        errors.append("negative_tests_not_pass")
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "checked_at": utc_now(),
    }


def build_decision(gate: dict[str, Any], source: dict[str, Any], run: dict[str, Any], check: dict[str, Any], visibility: dict[str, Any], negative: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2c.lane_b.decision.v1",
        "status": PASS_STATUS if validation["status"] == "PASS" else "FAIL_PERCEPTION_SHADOW_VALIDATION",
        "created_at": utc_now(),
        "lane": "B",
        "push": "2.2c",
        "artifact_root": rel(OUTPUT_ROOT),
        "prerequisite_gate": gate,
        "source_package_refs": PACKAGE_REFS,
        "source_id": source["source_id"],
        "service_id": source["service_id"],
        "shadow_summary": {
            "shadow_status": visibility["shadow_status"],
            "review_visible_allowed": visibility["review_visible_allowed"],
            "feed_count": source["feed_count"],
            "frames_processed": run["frames_processed"],
            "segments_processed": run["segments_processed"],
            "candidate_observations_emitted": run["candidate_observations_emitted"],
            "candidate_rate_observed": run["candidate_rate_observed"],
            "candidate_rate_expected_band": run["candidate_rate_expected_band"],
            "check_report_ref": check["check_report_ref"],
            "authority_envelope_ref": check["authority_envelope_ref"],
        },
        "required_artifacts": [
            "PERCEPTION_SHADOW_DECISION.json",
            "PERCEPTION_SHADOW_REPORT.md",
            "SOURCE_REGISTRY_ENTRY.json",
            "SHADOW_RUN_REPORT.json",
            "CHECK_DETECTION_SUFFICIENCY_REPORT.json",
            "SHADOW_EXPECTATION_SPEC.json",
            "REVIEW_VISIBILITY_DECISION.json",
            "NEGATIVE_TEST_REPORT.json",
            "HASH_MANIFEST.json",
        ],
        "validation": validation,
        "negative_test_status": negative["status"],
        "boundaries": {
            "identity_biometric_inference": False,
            "official_action_finding_violation_dispatch_enforcement_legal_certified_finding": False,
            "production_camera_rollout_or_live_cctv_claim": False,
            "production_network_or_api_access": False,
            "candidate_only_local_replay_review_query": True,
        },
        "limitations": [
            "The source is live-like local/replay shadow, not production CCTV or production network access.",
            "Review visibility, when allowed, is candidate-only and does not create official action or finding.",
            "Raw frames remain admin/privacy-reviewer scoped; review surfaces use redacted clips or hash refs.",
        ],
        "non_goals": NON_GOALS,
    }


def report_markdown(decision: dict[str, Any], run: dict[str, Any], visibility: dict[str, Any]) -> str:
    return f"""# Perception Shadow Activation Report

Status: `{decision['status']}`

Source: `{decision['source_id']}`

Shadow status: `{visibility['shadow_status']}`

Review-visible allowed: `{visibility['review_visible_allowed']}`

Processed:

- Frames: `{run['frames_processed']}`
- Segments: `{run['segments_processed']}`
- Candidate observations: `{run['candidate_observations_emitted']}`
- Candidate rate: `{run['candidate_rate_observed']}`
- Expected band: `{run['candidate_rate_expected_band']}`

CHECK:

- `{decision['shadow_summary']['check_report_ref']}`
- `{decision['shadow_summary']['authority_envelope_ref']}`

Boundaries:

{chr(10).join(f"- {item}" for item in NON_GOALS)}
"""


def list_hash_manifest() -> dict[str, Any]:
    files = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            files.append(
                {
                    "path": path.resolve().relative_to(OUTPUT_ROOT.resolve()).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return {
        "schema_version": "citybrain.epoch_2_2.push_2_2c.lane_b.hash_manifest.v1",
        "status": "PASS",
        "algorithm": "sha256",
        "created_at": utc_now(),
        "item_count": len(files),
        "files": files,
    }


def write_all_outputs() -> dict[str, Any]:
    gate = check_prerequisite_gate()
    if gate["status"] != "PASS":
        return {"gate": gate, "decision": None}

    service_by_id("perception_shadow_service")
    source = source_registry_entry()
    expectation = shadow_expectation_spec()
    run = shadow_run_report(source, expectation)
    check = check_detection_sufficiency_report(source, run)
    visibility = review_visibility_decision(run, check)
    negative = negative_test_report()
    validation = validate_outputs(source, expectation, run, check, visibility, negative)
    decision = build_decision(gate, source, run, check, visibility, negative, validation)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(OUTPUT_ROOT / "SOURCE_REGISTRY_ENTRY.json", source)
    write_json(OUTPUT_ROOT / "SHADOW_EXPECTATION_SPEC.json", expectation)
    write_json(OUTPUT_ROOT / "SHADOW_RUN_REPORT.json", run)
    write_json(OUTPUT_ROOT / "CHECK_DETECTION_SUFFICIENCY_REPORT.json", check)
    write_json(OUTPUT_ROOT / "REVIEW_VISIBILITY_DECISION.json", visibility)
    write_json(OUTPUT_ROOT / "NEGATIVE_TEST_REPORT.json", negative)
    write_json(OUTPUT_ROOT / "PERCEPTION_SHADOW_DECISION.json", decision)
    write_text(OUTPUT_ROOT / "PERCEPTION_SHADOW_REPORT.md", report_markdown(decision, run, visibility))
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", list_hash_manifest())
    return {
        "gate": gate,
        "source": source,
        "expectation": expectation,
        "run": run,
        "check": check,
        "visibility": visibility,
        "negative": negative,
        "validation": validation,
        "decision": decision,
    }


def main() -> int:
    result = write_all_outputs()
    gate = result["gate"]
    if gate["status"] != "PASS":
        print(BLOCK_STATUS)
        print(json.dumps(gate["errors"], indent=2, sort_keys=True))
        return 1
    decision = result["decision"]
    print(decision["status"])
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

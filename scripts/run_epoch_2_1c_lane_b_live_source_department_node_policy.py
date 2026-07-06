#!/usr/bin/env python3
"""Epoch 2.1 Push 2.1c Lane B live-source and department-node policy runner."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_epoch_2_1a_lane_b_domain_framework import SOURCE_CLASS_ALLOWED_VALUES, stable_hash  # noqa: E402


OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1c_lane_b_live_source_department_node_policy"
GATE_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_integration_gate_2_1b_content_hardening"
GATE_DECISION_PATH = GATE_ROOT / "INTEGRATION_GATE_2_1B_DECISION.json"
GATE_FLAG_PATH = GATE_ROOT / "PUSH_2_1C_ALLOWED_TO_OPEN.flag"

RBAC_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1b_lane_a_rbac_audit_observability"
RBAC_MATRIX_PATH = RBAC_ROOT / "rbac_policy_matrix_v1.json"
AUDIT_TAXONOMY_PATH = RBAC_ROOT / "audit_event_taxonomy_v1.json"
OBSERVABILITY_PATH = RBAC_ROOT / "observability_envelope_v1.json"
RBAC_DECISION_PATH = RBAC_ROOT / "PUSH_2_1B_LANE_A_DECISION.json"

PRIVACY_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_a_privacy_retention"
PRIVACY_POLICY_PATH = PRIVACY_ROOT / "privacy_retention_policy_v1.json"
RETENTION_MATRIX_PATH = PRIVACY_ROOT / "retention_matrix_v1.json"
AGGREGATION_FLOOR_PATH = PRIVACY_ROOT / "aggregation_floor_policy_v1.json"

PASS_STATUS = "PASS_PUSH_2_1C_LANE_B_LIVE_SOURCE_DEPARTMENT_NODE_POLICY_WITH_LIMITATIONS"
BLOCK_STATUS = "BLOCKED_PUSH_2_1C_LANE_B_PREREQUISITE_GATE"

PACKAGE_REFS = [
    "02_PUSH_LANE_EXECUTION_MODEL.md",
    "08_PUSH_2_1B_LANE_A_RBAC_AUDIT_OBSERVABILITY_PROMPT.md",
    "13_PUSH_2_1C_LANE_B_LIVE_SOURCE_DEPARTMENT_NODE_POLICY_PROMPT.md",
    "20_SPEC_PRIVACY_RETENTION_ENFORCEMENT.md",
    "21_SPEC_DOMAIN_PACK_FRAMEWORK_ONTOLOGY_GOVERNANCE.md",
    "26_SPEC_LIVE_SOURCE_DEPARTMENT_NODE_POLICY.md",
    "28_SCOPE_NON_GOALS.md",
    "30_EXIT_GATE_CHECKLIST.md",
]

NON_GOALS = [
    "No live camera/source implementation.",
    "No just-try-one-feed exception.",
    "No production connector, public API, or internet exposure.",
    "No autonomous monitoring/action, dispatch, enforcement, official ticket/case, legal/certified finding, or agent activation.",
    "Local/replay/review/query policy/design only.",
]

LIVE_SOURCE_REQUIRED_FIELDS = [
    "source_id",
    "source_name",
    "source_type",
    "owner",
    "steward",
    "source_class",
    "registration_workflow_state",
    "retention_privacy_profile",
    "raw_media_policy",
    "evidence_clip_policy",
    "camera_registry",
    "health_status_metadata",
    "time_location_calibration",
    "check_detection_sufficiency",
    "candidate_observation_rule",
    "approval_gates",
    "rbac_audit_alignment",
    "enablement_boundary",
]

DEPARTMENT_NODE_REQUIRED_FIELDS = [
    "node_id",
    "department_id",
    "department_name",
    "owner",
    "steward",
    "local_registry_slice",
    "local_graph_slice",
    "component_policy",
    "dashboard_slice",
    "connector_boundary",
    "federation_handoff_contract",
    "authority_boundary",
    "rbac_audit_alignment",
    "privacy_retention_alignment",
    "non_goals",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


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

    gate_decision: dict[str, Any] = {}
    if not GATE_DECISION_PATH.exists():
        errors.append(f"missing_gate_decision:{rel(GATE_DECISION_PATH)}")
    else:
        gate_decision = read_json(GATE_DECISION_PATH)
        if not str(gate_decision.get("status", "")).startswith("PASS"):
            errors.append(f"gate_status_not_pass:{gate_decision.get('status')}")
        if gate_decision.get("push_2_1c_allowed_to_open") is not True:
            errors.append("push_2_1c_allowed_to_open_not_true")

    flag_value = ""
    if not GATE_FLAG_PATH.exists():
        errors.append(f"missing_gate_flag:{rel(GATE_FLAG_PATH)}")
    else:
        flag_value = GATE_FLAG_PATH.read_text(encoding="utf-8").strip()
        if flag_value != "PASS":
            errors.append(f"gate_flag_not_pass:{flag_value}")

    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1c.lane_b.prerequisite_gate.v1",
        "status": "PASS" if not errors else BLOCK_STATUS,
        "checked_at": utc_now(),
        "branch": branch,
        "gate_decision_ref": rel(GATE_DECISION_PATH),
        "gate_decision_status": gate_decision.get("status"),
        "push_2_1c_allowed_to_open": gate_decision.get("push_2_1c_allowed_to_open"),
        "gate_flag_ref": rel(GATE_FLAG_PATH),
        "gate_flag_value": flag_value,
        "errors": errors,
    }


def load_baselines() -> dict[str, Any]:
    return {
        "rbac_matrix": read_json(RBAC_MATRIX_PATH),
        "audit_taxonomy": read_json(AUDIT_TAXONOMY_PATH),
        "observability": read_json(OBSERVABILITY_PATH),
        "rbac_decision": read_json(RBAC_DECISION_PATH),
        "privacy_policy": read_json(PRIVACY_POLICY_PATH),
        "retention_matrix": read_json(RETENTION_MATRIX_PATH),
        "aggregation_floor": read_json(AGGREGATION_FLOOR_PATH),
    }


def live_source_onboarding_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrainLiveSourceOnboardingV1",
        "type": "object",
        "additionalProperties": False,
        "required": LIVE_SOURCE_REQUIRED_FIELDS,
        "properties": {
            "source_id": {"type": "string", "pattern": "^source:[a-z0-9_\\-:.]+$"},
            "source_name": {"type": "string"},
            "source_type": {"enum": ["camera", "sensor", "file_drop", "feed_contract", "operator_registered"]},
            "owner": {"type": "object", "required": ["owner_org", "owner_contact_ref", "accountable_role"]},
            "steward": {"type": "object", "required": ["steward_org", "steward_contact_ref", "data_steward_role"]},
            "source_class": {"enum": SOURCE_CLASS_ALLOWED_VALUES},
            "registration_workflow_state": {
                "enum": [
                    "draft_request",
                    "owner_steward_review",
                    "privacy_retention_review",
                    "rbac_audit_review",
                    "calibration_review",
                    "check_sufficiency_review",
                    "live_enablement_deferred",
                    "rejected",
                ]
            },
            "retention_privacy_profile": {
                "type": "object",
                "required": ["retention_classes", "privacy_flags", "right_to_forget_policy_ref", "aggregation_floor_ref"],
            },
            "raw_media_policy": {
                "type": "object",
                "required": ["retention_class", "access_scope", "delete_or_redact_policy", "hash_metadata_retained", "raw_media_live_storage_enabled"],
            },
            "evidence_clip_policy": {
                "type": "object",
                "required": ["retention_class", "requires_source_record_link", "requires_redaction_review", "candidate_only_until_check"],
            },
            "camera_registry": {
                "type": "object",
                "required": ["registry_record_required", "camera_id", "coverage_geometry_ref", "mount_location_ref", "field_of_view_profile", "blind_zone_notes"],
            },
            "health_status_metadata": {
                "type": "object",
                "required": ["status_values", "last_health_check_at", "heartbeat_policy", "data_gap_policy"],
            },
            "time_location_calibration": {
                "type": "object",
                "required": ["time_sync_source", "max_clock_drift_ms", "location_reference_system", "calibration_report_required", "last_calibrated_at"],
            },
            "check_detection_sufficiency": {
                "type": "object",
                "required": ["check_report_required", "minimum_evidence_refs", "must_state_cannot_claim_visibility", "insufficient_detection_blocks_enablement"],
            },
            "candidate_observation_rule": {
                "type": "object",
                "required": ["candidate_observation_only", "may_create_official_action", "may_dispatch_or_enforce", "may_make_legal_finding"],
            },
            "approval_gates": {
                "type": "array",
                "minItems": 7,
                "items": {"type": "object", "required": ["gate_id", "owner_role", "required_status", "audit_event"]},
            },
            "rbac_audit_alignment": {
                "type": "object",
                "required": ["request_roles", "audit_event", "policy_block_event", "observability_scope"],
            },
            "enablement_boundary": {
                "type": "object",
                "required": ["live_enabled", "just_try_one_feed_exception_allowed", "production_connector_allowed", "public_api_or_internet_exposure_allowed"],
            },
        },
        "must_not_enable_if": [
            "missing_owner_or_steward",
            "missing_source_class",
            "retention_privacy_unapproved",
            "rbac_audit_unapproved",
            "missing_camera_registry_or_health_metadata",
            "missing_time_location_calibration",
            "missing_check_detection_sufficiency",
            "candidate_observation_only_rule_absent",
            "just_try_one_feed_exception_requested",
            "production_connector_or_public_api_requested",
        ],
    }


def department_node_manifest_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CityBrainDepartmentLocalNodeManifestV1",
        "type": "object",
        "additionalProperties": False,
        "required": DEPARTMENT_NODE_REQUIRED_FIELDS,
        "properties": {
            "node_id": {"type": "string", "pattern": "^department_node:[a-z0-9_\\-:.]+$"},
            "department_id": {"type": "string"},
            "department_name": {"type": "string"},
            "owner": {"type": "object", "required": ["owner_org", "owner_contact_ref", "accountable_role"]},
            "steward": {"type": "object", "required": ["steward_org", "steward_contact_ref", "data_steward_role"]},
            "local_registry_slice": {"type": "object", "required": ["source_registry_refs", "domain_pack_refs", "source_class_policy_ref"]},
            "local_graph_slice": {"type": "object", "required": ["cer_scope", "seg_overlay_scope", "identity_boundary", "provenance_required"]},
            "component_policy": {"type": "object", "required": ["allowed_components", "agent_activation_allowed", "component_run_observability_ref"]},
            "dashboard_slice": {"type": "object", "required": ["maturity_dashboard_scope", "aggregation_floor_ref", "operator_detail_default"]},
            "connector_boundary": {"type": "object", "required": ["local_connectors_declared", "live_connector_implementation_allowed", "public_api_or_internet_exposure_allowed", "secrets_storage_allowed"]},
            "federation_handoff_contract": {"type": "object", "required": ["export_scope", "required_provenance_fields", "citywide_query_boundary", "privacy_redaction_required"]},
            "authority_boundary": {"type": "object", "required": ["local_authority_scope", "citywide_authority_scope", "may_dispatch_or_enforce", "may_create_official_ticket_or_case"]},
            "rbac_audit_alignment": {"type": "object", "required": ["role_refs", "audit_event_refs", "policy_block_event_ref"]},
            "privacy_retention_alignment": {"type": "object", "required": ["privacy_policy_ref", "retention_matrix_ref", "right_to_forget_policy_ref"]},
            "non_goals": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        },
        "must_not_merge_if": [
            "missing_local_registry_slice",
            "missing_local_graph_slice",
            "production_connector_or_public_api_requested",
            "agent_activation_allowed",
            "local_node_claims_citywide_authority",
            "official_action_dispatch_or_enforcement_allowed",
            "missing_federation_handoff_contract",
        ],
    }


def policy_fixture() -> dict[str, Any]:
    return {
        "source_id": "source:fixture:camera_review_policy_only",
        "source_name": "Policy-only camera onboarding fixture",
        "source_type": "camera",
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
        "source_class": "media_evidence",
        "registration_workflow_state": "live_enablement_deferred",
        "retention_privacy_profile": {
            "retention_classes": ["raw_media", "evidence_clip_or_frame", "source_record", "CheckReport", "CalibrationReport"],
            "privacy_flags": ["potential_personal_data", "raw_media_admin_privacy_reviewer_only", "redaction_required_for_clips"],
            "right_to_forget_policy_ref": "outputs/epoch_2_1_push_2_1a_lane_a_privacy_retention/right_to_forget_policy_v1.md",
            "aggregation_floor_ref": "outputs/epoch_2_1_push_2_1a_lane_a_privacy_retention/aggregation_floor_policy_v1.json",
        },
        "raw_media_policy": {
            "retention_class": "raw_media",
            "access_scope": "admin_privacy_reviewer_only",
            "delete_or_redact_policy": "delete_blob_keep_hash_and_source_metadata_if_evidence_linked",
            "hash_metadata_retained": True,
            "raw_media_live_storage_enabled": False,
        },
        "evidence_clip_policy": {
            "retention_class": "evidence_clip_or_frame",
            "requires_source_record_link": True,
            "requires_redaction_review": True,
            "candidate_only_until_check": True,
        },
        "camera_registry": {
            "registry_record_required": True,
            "camera_id": "camera:fixture:transport:001",
            "coverage_geometry_ref": "geometry:fixture:camera_fov:001",
            "mount_location_ref": "place:fixture:mount:001",
            "field_of_view_profile": "fixed_view_profile_required",
            "blind_zone_notes": "must be declared before enablement review",
        },
        "health_status_metadata": {
            "status_values": ["proposed", "review_pending", "blocked", "deferred", "retired"],
            "last_health_check_at": None,
            "heartbeat_policy": "policy_contract_only_no_live_heartbeat",
            "data_gap_policy": "data gaps block evidence sufficiency and must surface limitations",
        },
        "time_location_calibration": {
            "time_sync_source": "declared_source_clock_and_replay_timestamp",
            "max_clock_drift_ms": 1000,
            "location_reference_system": "citybrain_place_or_geometry_ref",
            "calibration_report_required": True,
            "last_calibrated_at": None,
        },
        "check_detection_sufficiency": {
            "check_report_required": True,
            "minimum_evidence_refs": 2,
            "must_state_cannot_claim_visibility": True,
            "insufficient_detection_blocks_enablement": True,
        },
        "candidate_observation_rule": {
            "candidate_observation_only": True,
            "may_create_official_action": False,
            "may_dispatch_or_enforce": False,
            "may_make_legal_finding": False,
        },
        "approval_gates": [
            {"gate_id": "request_logged", "owner_role": "data_steward", "required_status": "recorded", "audit_event": "source_onboarded_request"},
            {"gate_id": "owner_steward_verified", "owner_role": "admin", "required_status": "approved", "audit_event": "source_onboarded_request"},
            {"gate_id": "privacy_retention_approved", "owner_role": "admin", "required_status": "approved", "audit_event": "source_onboarded_request"},
            {"gate_id": "rbac_audit_approved", "owner_role": "admin", "required_status": "approved", "audit_event": "source_onboarded_request"},
            {"gate_id": "camera_registry_and_health_metadata_approved", "owner_role": "data_steward", "required_status": "approved", "audit_event": "source_onboarded_request"},
            {"gate_id": "time_location_calibration_approved", "owner_role": "review_lead", "required_status": "approved", "audit_event": "source_onboarded_request"},
            {"gate_id": "check_detection_sufficiency_approved", "owner_role": "review_lead", "required_status": "approved", "audit_event": "source_onboarded_request"},
            {"gate_id": "live_enablement_deferred_to_later_epoch", "owner_role": "admin", "required_status": "deferred", "audit_event": "policy_blocked_access"},
        ],
        "rbac_audit_alignment": {
            "request_roles": ["admin", "data_steward"],
            "audit_event": "source_onboarded_request",
            "policy_block_event": "policy_blocked_access",
            "observability_scope": "local_replay_review_query",
        },
        "enablement_boundary": {
            "live_enabled": False,
            "just_try_one_feed_exception_allowed": False,
            "production_connector_allowed": False,
            "public_api_or_internet_exposure_allowed": False,
        },
    }


def department_node_fixture() -> dict[str, Any]:
    return {
        "node_id": "department_node:transport:policy_only",
        "department_id": "transport",
        "department_name": "Transport Department Policy Node",
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
        "local_registry_slice": {
            "source_registry_refs": ["source:fixture:camera_review_policy_only"],
            "domain_pack_refs": ["citybrain_starter_mobility_domain_pack"],
            "source_class_policy_ref": "outputs/epoch_2_1_push_2_1a_lane_b_domain_framework/domain_pack_manifest_schema_v1.json",
        },
        "local_graph_slice": {
            "cer_scope": "department-scoped canonical entities with citywide identity handoff refs",
            "seg_overlay_scope": "department-local spatial/event overlays with provenance",
            "identity_boundary": "department IDs cannot overwrite citywide canonical IDs",
            "provenance_required": True,
        },
        "component_policy": {
            "allowed_components": ["domain_pack_validator", "calibration_report_materializer", "federation_query_fixture"],
            "agent_activation_allowed": False,
            "component_run_observability_ref": "outputs/epoch_2_1_push_2_1b_lane_a_rbac_audit_observability/observability_envelope_v1.json",
        },
        "dashboard_slice": {
            "maturity_dashboard_scope": "department aggregate and source-health policy status only",
            "aggregation_floor_ref": "outputs/epoch_2_1_push_2_1a_lane_a_privacy_retention/aggregation_floor_policy_v1.json",
            "operator_detail_default": "blocked_non_admin",
        },
        "connector_boundary": {
            "local_connectors_declared": ["policy_contract:camera_registry", "policy_contract:source_registry"],
            "live_connector_implementation_allowed": False,
            "public_api_or_internet_exposure_allowed": False,
            "secrets_storage_allowed": False,
        },
        "federation_handoff_contract": {
            "export_scope": "redacted_registry_graph_and_dashboard_summaries_only",
            "required_provenance_fields": ["source_id", "source_class", "owner", "steward", "retrieval_or_policy_timestamp", "privacy_flags"],
            "citywide_query_boundary": "federation may query redacted summaries and provenance, not assume local operational authority",
            "privacy_redaction_required": True,
        },
        "authority_boundary": {
            "local_authority_scope": "department-local review and policy request queue only",
            "citywide_authority_scope": "citywide federation may compare/query but not dispatch/control/enforce",
            "may_dispatch_or_enforce": False,
            "may_create_official_ticket_or_case": False,
        },
        "rbac_audit_alignment": {
            "role_refs": ["admin", "data_steward", "review_lead", "developer_local"],
            "audit_event_refs": ["source_onboarded_request", "policy_blocked_access", "federated_query_executed", "agent_component_run_blocked"],
            "policy_block_event_ref": "policy_blocked_access",
        },
        "privacy_retention_alignment": {
            "privacy_policy_ref": "outputs/epoch_2_1_push_2_1a_lane_a_privacy_retention/privacy_retention_policy_v1.json",
            "retention_matrix_ref": "outputs/epoch_2_1_push_2_1a_lane_a_privacy_retention/retention_matrix_v1.json",
            "right_to_forget_policy_ref": "outputs/epoch_2_1_push_2_1a_lane_a_privacy_retention/right_to_forget_policy_v1.md",
        },
        "non_goals": NON_GOALS,
    }


def validate_live_source_record(record: dict[str, Any], baselines: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    for field in LIVE_SOURCE_REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"missing_required:{field}")
    if not record.get("owner") or not record.get("steward"):
        errors.append("missing_owner_or_steward")
    if record.get("source_class") not in SOURCE_CLASS_ALLOWED_VALUES:
        errors.append(f"invalid_source_class:{record.get('source_class')}")
    retention_classes = set(record.get("retention_privacy_profile", {}).get("retention_classes", []))
    required_retention = {"raw_media", "evidence_clip_or_frame", "source_record", "CheckReport", "CalibrationReport"}
    missing_retention = sorted(required_retention - retention_classes)
    if missing_retention:
        errors.append(f"missing_retention_classes:{','.join(missing_retention)}")
    if record.get("raw_media_policy", {}).get("raw_media_live_storage_enabled") is not False:
        errors.append("raw_media_live_storage_must_be_disabled")
    if record.get("evidence_clip_policy", {}).get("candidate_only_until_check") is not True:
        errors.append("evidence_clip_must_remain_candidate_until_check")
    if record.get("camera_registry", {}).get("registry_record_required") is not True:
        errors.append("camera_registry_required")
    check_policy = record.get("check_detection_sufficiency", {})
    if check_policy.get("check_report_required") is not True:
        errors.append("missing_check_detection_sufficiency")
    if check_policy.get("insufficient_detection_blocks_enablement") is not True:
        errors.append("insufficient_detection_must_block_enablement")
    candidate_rule = record.get("candidate_observation_rule", {})
    if candidate_rule.get("candidate_observation_only") is not True:
        errors.append("candidate_observation_only_rule_absent")
    for forbidden in ["may_create_official_action", "may_dispatch_or_enforce", "may_make_legal_finding"]:
        if candidate_rule.get(forbidden) is not False:
            errors.append(f"forbidden_candidate_rule:{forbidden}")
    boundary = record.get("enablement_boundary", {})
    if boundary.get("live_enabled") is not False:
        errors.append("live_source_implementation_requested")
    if boundary.get("just_try_one_feed_exception_allowed") is not False:
        errors.append("just_try_one_feed_exception_requested")
    if boundary.get("production_connector_allowed") is not False:
        errors.append("production_connector_requested")
    if boundary.get("public_api_or_internet_exposure_allowed") is not False:
        errors.append("public_api_or_internet_exposure_requested")

    rbac_roles = {
        row["role_id"]: row
        for row in baselines["rbac_matrix"].get("roles", [])
        if isinstance(row, dict)
    }
    request_roles = set(record.get("rbac_audit_alignment", {}).get("request_roles", []))
    expected_request_roles = {"admin", "data_steward"}
    if not expected_request_roles.issubset(request_roles):
        errors.append("missing_required_rbac_request_roles")
    for role in request_roles:
        if role not in rbac_roles:
            errors.append(f"unknown_rbac_role:{role}")
        elif rbac_roles[role].get("can_request_source_onboarding") is not True:
            errors.append(f"role_cannot_request_source_onboarding:{role}")
    audit_events = {row.get("event_type") for row in baselines["audit_taxonomy"].get("events", [])}
    if record.get("rbac_audit_alignment", {}).get("audit_event") != "source_onboarded_request":
        errors.append("source_onboarding_audit_event_missing")
    if "source_onboarded_request" not in audit_events:
        errors.append("rbac_baseline_missing_source_onboarded_request")
    if "policy_blocked_access" not in audit_events:
        errors.append("rbac_baseline_missing_policy_blocked_access")
    if baselines["observability"].get("environment_scope") != "local_replay_review_query":
        errors.append("observability_not_local_replay_review_query")
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "record_hash": stable_hash(record),
        "checked_at": utc_now(),
    }


def validate_department_node_record(record: dict[str, Any], baselines: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    for field in DEPARTMENT_NODE_REQUIRED_FIELDS:
        if field not in record:
            errors.append(f"missing_required:{field}")
    if not record.get("local_registry_slice", {}).get("source_registry_refs"):
        errors.append("missing_local_registry_slice")
    if not record.get("local_graph_slice", {}).get("provenance_required"):
        errors.append("missing_local_graph_provenance")
    if record.get("component_policy", {}).get("agent_activation_allowed") is not False:
        errors.append("agent_activation_allowed")
    connector = record.get("connector_boundary", {})
    if connector.get("live_connector_implementation_allowed") is not False:
        errors.append("live_connector_implementation_requested")
    if connector.get("public_api_or_internet_exposure_allowed") is not False:
        errors.append("public_api_or_internet_exposure_requested")
    if connector.get("secrets_storage_allowed") is not False:
        errors.append("secrets_storage_requested")
    authority = record.get("authority_boundary", {})
    if authority.get("may_dispatch_or_enforce") is not False:
        errors.append("dispatch_or_enforcement_allowed")
    if authority.get("may_create_official_ticket_or_case") is not False:
        errors.append("official_ticket_or_case_allowed")
    if record.get("federation_handoff_contract", {}).get("privacy_redaction_required") is not True:
        errors.append("missing_federation_privacy_redaction")
    if "privacy_retention_policy_v1.json" not in record.get("privacy_retention_alignment", {}).get("privacy_policy_ref", ""):
        errors.append("missing_privacy_policy_ref")
    audit_events = {row.get("event_type") for row in baselines["audit_taxonomy"].get("events", [])}
    missing_events = sorted(set(record.get("rbac_audit_alignment", {}).get("audit_event_refs", [])) - audit_events)
    if missing_events:
        errors.append(f"unknown_audit_event_refs:{','.join(missing_events)}")
    if record.get("non_goals") != NON_GOALS:
        errors.append("non_goals_boundary_mismatch")
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "record_hash": stable_hash(record),
        "checked_at": utc_now(),
    }


def build_validation_report(baselines: dict[str, Any]) -> dict[str, Any]:
    valid_live = policy_fixture()
    valid_node = department_node_fixture()
    missing_steward = json.loads(json.dumps(valid_live))
    missing_steward.pop("steward", None)
    feed_exception = json.loads(json.dumps(valid_live))
    feed_exception["enablement_boundary"]["just_try_one_feed_exception_allowed"] = True
    live_enabled = json.loads(json.dumps(valid_live))
    live_enabled["enablement_boundary"]["live_enabled"] = True
    no_check = json.loads(json.dumps(valid_live))
    no_check["check_detection_sufficiency"]["check_report_required"] = False
    production_connector = json.loads(json.dumps(valid_node))
    production_connector["connector_boundary"]["live_connector_implementation_allowed"] = True
    production_connector["connector_boundary"]["public_api_or_internet_exposure_allowed"] = True

    retention_classes = {row.get("artifact_class") for row in baselines["retention_matrix"].get("items", [])}
    required_retention = {"raw_media", "evidence_clip_or_frame", "source_record", "CheckReport", "CalibrationReport"}
    baseline_checks = {
        "rbac_status_pass": baselines["rbac_matrix"].get("status") == "PASS",
        "rbac_decision_pass": str(baselines["rbac_decision"].get("status", "")).startswith("PASS"),
        "source_onboarding_audit_event_present": any(
            row.get("event_type") == "source_onboarded_request"
            for row in baselines["audit_taxonomy"].get("events", [])
        ),
        "policy_block_audit_event_present": any(
            row.get("event_type") == "policy_blocked_access"
            for row in baselines["audit_taxonomy"].get("events", [])
        ),
        "observability_local_replay_only": baselines["observability"].get("environment_scope") == "local_replay_review_query",
        "privacy_policy_fixture_active": baselines["privacy_policy"].get("status") == "active_policy_fixture",
        "required_retention_classes_present": required_retention.issubset(retention_classes),
        "aggregation_floor_has_no_admin_override": baselines["aggregation_floor"].get("admin_override_allowed") is False,
    }
    live_validation = validate_live_source_record(valid_live, baselines)
    node_validation = validate_department_node_record(valid_node, baselines)
    negative_results = {
        "missing_owner_or_steward": validate_live_source_record(missing_steward, baselines),
        "just_try_one_feed_exception": validate_live_source_record(feed_exception, baselines),
        "live_enabled": validate_live_source_record(live_enabled, baselines),
        "missing_check_detection_sufficiency": validate_live_source_record(no_check, baselines),
        "production_connector_or_public_api": validate_department_node_record(production_connector, baselines),
    }
    negative_pass = (
        "missing_required:steward" in negative_results["missing_owner_or_steward"]["errors"]
        and "just_try_one_feed_exception_requested" in negative_results["just_try_one_feed_exception"]["errors"]
        and "live_source_implementation_requested" in negative_results["live_enabled"]["errors"]
        and "missing_check_detection_sufficiency" in negative_results["missing_check_detection_sufficiency"]["errors"]
        and "live_connector_implementation_requested" in negative_results["production_connector_or_public_api"]["errors"]
        and "public_api_or_internet_exposure_requested" in negative_results["production_connector_or_public_api"]["errors"]
    )
    status = "PASS" if all(baseline_checks.values()) and live_validation["status"] == "PASS" and node_validation["status"] == "PASS" and negative_pass else "FAIL"
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1c.lane_b.validation_report.v1",
        "status": status,
        "created_at": utc_now(),
        "baseline_refs": {
            "rbac_policy_matrix": rel(RBAC_MATRIX_PATH),
            "audit_event_taxonomy": rel(AUDIT_TAXONOMY_PATH),
            "observability_envelope": rel(OBSERVABILITY_PATH),
            "privacy_retention_policy": rel(PRIVACY_POLICY_PATH),
            "retention_matrix": rel(RETENTION_MATRIX_PATH),
            "aggregation_floor_policy": rel(AGGREGATION_FLOOR_PATH),
        },
        "baseline_checks": baseline_checks,
        "schema_checks": {
            "live_source_required_fields": LIVE_SOURCE_REQUIRED_FIELDS,
            "department_node_required_fields": DEPARTMENT_NODE_REQUIRED_FIELDS,
        },
        "positive_fixture_results": {
            "live_source_onboarding_policy_fixture": live_validation,
            "department_local_node_policy_fixture": node_validation,
        },
        "negative_fixture_results": negative_results,
    }


def live_source_policy_markdown() -> str:
    gates = policy_fixture()["approval_gates"]
    gate_lines = "\n".join(
        f"- `{gate['gate_id']}`: `{gate['owner_role']}` must produce `{gate['required_status']}` and audit `{gate['audit_event']}`"
        for gate in gates
    )
    return f"""# Live Source Onboarding Policy v1

Status: policy/design only for Epoch 2.1 Push 2.1c Lane B.

This policy defines how a future live source or camera may be requested and
reviewed. It does not implement a live source, camera feed, connector, public
API, network path, credential path, or production deployment.

## Registration Workflow

1. A request is logged by `admin` or `data_steward` using the existing
   `source_onboarded_request` audit event.
2. Owner and steward fields are verified.
3. `source_class` is assigned from the existing source-class contract.
4. Retention/privacy requirements are reviewed against the privacy policy,
   retention matrix, right-to-forget policy, and aggregation floor.
5. Raw media, evidence clips, camera registry, health/status metadata, and
   time/location calibration fields are checked.
6. CHECK detection-sufficiency is reviewed.
7. The request remains `live_enablement_deferred` in Epoch 2.1.

## Required Owner and Steward Fields

- owner organization, contact ref, and accountable role
- steward organization, contact ref, and data steward role
- request role must be one of `admin` or `data_steward`

## Source-Class Assignment

Allowed source classes are inherited from the 2.1a framework:
`{", ".join(SOURCE_CLASS_ALLOWED_VALUES)}`.

Camera evidence normally starts as `media_evidence`; derived detections remain
`derived_field`; replay fixtures remain `replay_fixture`. VSS or perception
output is never a fact source by itself.

## Retention and Privacy

The policy must cover `raw_media`, `evidence_clip_or_frame`, `source_record`,
`CheckReport`, and `CalibrationReport`. Raw media is admin/privacy-reviewer
scoped and short lived; evidence clips require source-record links and redaction
review; hashes and source metadata may be retained where policy allows.

## Camera Registry, Health, and Calibration

Camera records require camera id, coverage geometry, mount location, field of
view profile, blind-zone notes, health/status values, heartbeat policy, data-gap
policy, time sync source, clock drift limit, location reference system, and
calibration report requirement.

## CHECK and Candidate Observation Rule

Detections are candidate observations only. They cannot create official action,
dispatch, enforcement, legal/certified findings, tickets, or cases. Insufficient
detection evidence blocks enablement review and must surface limitations such as
cannot-claim-visibility.

## Approval Gates

{gate_lines}

## Boundaries

{chr(10).join(f"- {item}" for item in NON_GOALS)}
"""


def camera_registry_policy_markdown() -> str:
    return """# Camera Source Registry Policy v1

Status: registry policy only; no camera/feed implementation.

Every camera source registration must include:

- camera id and source id
- owner and steward
- source_class and source registry state
- coverage geometry, mount location, field-of-view profile, and blind-zone notes
- time-sync source, clock-drift tolerance, location reference system, and calibration report ref
- health/status metadata, heartbeat policy, last health check, and data-gap policy
- raw media retention class, evidence clip policy, hash metadata policy, and redaction requirement
- CHECK detection-sufficiency status and candidate-observation-only flag
- audit refs for `source_onboarded_request` and `policy_blocked_access`

Registry status values are policy states only: `proposed`, `review_pending`,
`blocked`, `deferred`, and `retired`. No state in Epoch 2.1 means that a live
feed is enabled.
"""


def department_node_strategy_markdown() -> str:
    return f"""# Department-Local Node Strategy v1

Status: policy/design only for Epoch 2.1 Push 2.1c Lane B.

Department-local nodes are scoped registry, graph, dashboard, and federation
contracts. They are not alternate databases that override citywide identity, and
they are not production connector deployments.

## Local Registry Slice

A node owns a department-scoped registry slice for source refs, owner/steward
metadata, source_class policy, privacy/retention refs, domain pack refs, and
camera/source registry states.

## Local Graph Slice

The node may maintain a department-scoped CER slice plus SEG overlays. Local
identifiers must preserve provenance and citywide handoff refs; local IDs cannot
overwrite citywide canonical IDs.

## Component Policy

Allowed components are policy/test components only, such as domain-pack
validation, calibration report materialization, and federation query fixtures.
Agent activation is forbidden in Epoch 2.1.

## Dashboard Slice

Department dashboards may show aggregate source health, policy state, and data
maturity. Operator details are blocked by default, aggregation floors apply, and
small cells must suppress display/materialization.

## Connector Boundary

Local connector refs are declarations, not production connectors. No public API,
internet exposure, credential storage, feed subscription, or live camera path is
created by this lane.

## Federation Handoff Contract

Federation receives redacted registry, graph, and dashboard summaries with
source id, source_class, owner/steward refs, provenance, privacy flags, and
retention policy refs. Federation can compare/query; it cannot dispatch,
enforce, certify, or assume local operational authority.

## Authority Boundary

Department-local authority is limited to review and policy request queues.
Citywide authority is limited to redacted query and comparison. Neither may
create official tickets/cases, dispatch, control, enforce, or issue legal or
certified findings.

## Boundaries

{chr(10).join(f"- {item}" for item in NON_GOALS)}
"""


def build_decision(gate: dict[str, Any], validation_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1c.lane_b.decision.v1",
        "status": PASS_STATUS if validation_report["status"] == "PASS" else "FAIL_PUSH_2_1C_LANE_B_POLICY_VALIDATION",
        "created_at": utc_now(),
        "lane": "B",
        "push": "2.1c",
        "artifact_root": rel(OUTPUT_ROOT),
        "prerequisite_gate": gate,
        "source_package_refs": PACKAGE_REFS,
        "baseline_refs": validation_report["baseline_refs"],
        "required_artifacts": [
            "live_source_onboarding_policy_v1.md",
            "live_source_onboarding_schema_v1.json",
            "camera_source_registry_policy_v1.md",
            "department_local_node_strategy_v1.md",
            "department_node_manifest_schema_v1.json",
            "live_source_department_policy_validation_report.json",
            "PUSH_2_1C_LANE_B_DECISION.json",
            "HASH_MANIFEST.json",
            "SUMMARY.md",
        ],
        "policy_scope": {
            "live_source_onboarding_policy_defined": True,
            "camera_source_registry_policy_defined": True,
            "department_local_node_strategy_defined": True,
            "source_registration_workflow_defined": True,
            "owner_steward_fields_required": True,
            "source_class_assignment_required": True,
            "retention_privacy_required": True,
            "raw_media_evidence_clip_handling_required": True,
            "camera_health_time_location_calibration_required": True,
            "check_detection_sufficiency_required": True,
            "candidate_observation_only_rule_required": True,
            "approval_gates_before_live_enablement_required": True,
            "department_registry_graph_dashboard_connector_federation_authority_boundaries_defined": True,
        },
        "boundaries": {
            "live_camera_source_implementation_created": False,
            "just_try_one_feed_exception_created": False,
            "production_connector_created": False,
            "public_api_or_internet_exposure_created": False,
            "autonomous_monitoring_or_action_created": False,
            "dispatch_enforcement_ticket_case_or_legal_finding_created": False,
            "agent_activation_created": False,
            "local_replay_review_query_policy_design_only": True,
        },
        "limitations": NON_GOALS,
        "validation_report_ref": "outputs/epoch_2_1_push_2_1c_lane_b_live_source_department_node_policy/live_source_department_policy_validation_report.json",
    }


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
        "schema_version": "citybrain.epoch_2_1.push_2_1c.lane_b.hash_manifest.v1",
        "status": "PASS",
        "algorithm": "sha256",
        "created_at": utc_now(),
        "item_count": len(files),
        "files": files,
    }


def write_summary(decision: dict[str, Any], validation_report: dict[str, Any]) -> None:
    baseline_lines = "\n".join(
        f"- `{name}`: `{value}`"
        for name, value in validation_report["baseline_checks"].items()
    )
    write_text(
        OUTPUT_ROOT / "SUMMARY.md",
        f"""# Push 2.1c Lane B Live-Source and Department-Node Policy

Status: `{decision['status']}`

Published live-source onboarding policy, live-source schema, camera registry
policy, department-local node strategy, department-node schema, validation
report, decision, and hash manifest.

Baseline checks:

{baseline_lines}

Boundaries:

{chr(10).join(f"- {item}" for item in NON_GOALS)}

This lane does not close Epoch 2.1.
""",
    )


def write_all_outputs() -> dict[str, Any]:
    gate = check_prerequisite_gate()
    if gate["status"] != "PASS":
        return {"gate": gate, "decision": None}

    baselines = load_baselines()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    write_text(OUTPUT_ROOT / "live_source_onboarding_policy_v1.md", live_source_policy_markdown())
    write_json(OUTPUT_ROOT / "live_source_onboarding_schema_v1.json", live_source_onboarding_schema())
    write_text(OUTPUT_ROOT / "camera_source_registry_policy_v1.md", camera_registry_policy_markdown())
    write_text(OUTPUT_ROOT / "department_local_node_strategy_v1.md", department_node_strategy_markdown())
    write_json(OUTPUT_ROOT / "department_node_manifest_schema_v1.json", department_node_manifest_schema())
    validation_report = build_validation_report(baselines)
    write_json(OUTPUT_ROOT / "live_source_department_policy_validation_report.json", validation_report)
    decision = build_decision(gate, validation_report)
    write_json(OUTPUT_ROOT / "PUSH_2_1C_LANE_B_DECISION.json", decision)
    write_summary(decision, validation_report)
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", list_hash_manifest())
    return {"gate": gate, "decision": decision, "validation_report": validation_report, "baselines": baselines}


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

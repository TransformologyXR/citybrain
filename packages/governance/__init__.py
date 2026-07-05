"""Local/replay RBAC, audit, and observability helpers for Push 7 Lane B.

This package models governance fixtures only. It is not production IAM and it
never grants execution, dispatch/control/enforcement, official submission,
legal/certified finding, live Kit control, or live runtime authority.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


ALLOWED_PERMISSIONS = [
    "view_packet",
    "view_evidence",
    "record_disposition",
    "submit_approval_request",
    "approve_local",
    "create_plan_proposal",
    "create_schedule_simulation_proposal",
    "view_federated_packet",
    "export_review_brief",
    "view_audit_log",
]

FORBIDDEN_PERMISSIONS = [
    "execute_action",
    "dispatch_resource",
    "submit_official_case",
    "control_infrastructure",
    "certify_legal_finding",
    "live_kit_control",
]

ROLE_PERMISSIONS = {
    "viewer": ["view_packet", "view_evidence"],
    "reviewer": ["view_packet", "view_evidence", "record_disposition", "submit_approval_request", "export_review_brief"],
    "approver_local": ["view_packet", "view_evidence", "approve_local", "view_audit_log"],
    "planner": ["view_packet", "view_evidence", "create_plan_proposal", "export_review_brief"],
    "simulator": ["view_packet", "view_evidence", "create_schedule_simulation_proposal"],
    "admin_local": ALLOWED_PERMISSIONS,
    "auditor": ["view_packet", "view_evidence", "view_audit_log", "export_review_brief"],
}

NOT_EXECUTED = [
    "production_api",
    "url_fetch",
    "live_retrieval",
    "live_llm_call",
    "official_case_ticket_submission",
    "dispatch_control_enforcement_execution",
    "legal_certified_finding",
    "autonomous_workflow",
    "live_kit_control",
    "execution_adapter_action",
]

NON_CLAIMS = [
    "No production IAM claim.",
    "No production API.",
    "No URL fetch or live retrieval.",
    "No live LLM authority.",
    "No official case/ticket submission.",
    "No dispatch/control/enforcement execution.",
    "No legal/certified finding.",
    "No autonomous workflow.",
    "No live Kit control.",
    "No full citywide twin claim.",
    "No VSS-as-fact-source.",
    "No real cross-city operational claim; federation is fixture/synthetic unless explicitly sourced and checked.",
    "No sealed ASK G1-G8 runtime change.",
    "No protected R7 runtime drift.",
    "All execution adapters are registry/preflight/not_executed unless explicitly authorized in a later phase.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def stable_id(prefix: str, *parts: Any) -> str:
    return f"{prefix}:{stable_hash([prefix, *parts])[:16]}"


def unique(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, list):
            for nested in unique(value):
                if nested not in seen:
                    seen.add(nested)
                    result.append(nested)
            continue
        text = str(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def validate_role(role: dict[str, Any]) -> dict[str, Any]:
    role_id = role.get("role_id")
    permissions = role.get("permissions", [])
    if role_id not in ROLE_PERMISSIONS:
        raise ValueError(f"Unknown role: {role_id}")
    unknown = sorted(set(permissions) - set(ALLOWED_PERMISSIONS))
    forbidden = sorted(set(permissions).intersection(FORBIDDEN_PERMISSIONS))
    if unknown:
        raise ValueError(f"Role {role_id} has unknown permissions: {unknown}")
    if forbidden:
        raise ValueError(f"Role {role_id} has forbidden permissions: {forbidden}")
    if sorted(permissions) != sorted(ROLE_PERMISSIONS[role_id]):
        raise ValueError(f"Role {role_id} permissions differ from policy")
    return role


def build_role_definition(role_id: str, description: str) -> dict[str, Any]:
    payload = {
        "role_id": role_id,
        "schema_version": "main-citybrain.governance.role_definition.r1",
        "description": description,
        "permissions": ROLE_PERMISSIONS[role_id],
        "forbidden_permissions": FORBIDDEN_PERMISSIONS,
        "execution_permission": False,
        "local_replay_only": True,
        "not_production_iam": True,
        "cannot_claim": NON_CLAIMS,
    }
    validate_role(payload)
    payload["role_definition_hash"] = stable_hash(payload)
    return payload


def build_permission_policy(permission: str, allowed_roles: list[str], target_types: list[str]) -> dict[str, Any]:
    if permission in FORBIDDEN_PERMISSIONS:
        raise ValueError(f"Cannot create allow policy for forbidden permission: {permission}")
    if permission not in ALLOWED_PERMISSIONS:
        raise ValueError(f"Unknown permission: {permission}")
    invalid_roles = sorted(set(allowed_roles) - set(ROLE_PERMISSIONS))
    if invalid_roles:
        raise ValueError(f"Unknown roles for policy {permission}: {invalid_roles}")
    payload = {
        "policy_id": stable_id("policy", permission, allowed_roles),
        "schema_version": "main-citybrain.governance.permission_policy.r1",
        "permission": permission,
        "allowed_roles": allowed_roles,
        "target_types": target_types,
        "effect": "allow_local_replay_only",
        "forbidden_permissions": FORBIDDEN_PERMISSIONS,
        "requires_not_executed": True,
        "not_production_iam": True,
        "cannot_claim": NON_CLAIMS,
    }
    payload["permission_policy_hash"] = stable_hash(payload)
    return payload


def evaluate_access(role_id: str, permission: str) -> tuple[str, str]:
    if permission in FORBIDDEN_PERMISSIONS:
        return "deny", "permission_forbidden_by_lane_contract"
    if permission not in ALLOWED_PERMISSIONS:
        return "deny", "permission_unknown"
    if permission not in ROLE_PERMISSIONS.get(role_id, []):
        return "deny", "role_not_allowed_for_permission"
    return "allow", "role_policy_allows_local_replay_action"


def build_access_decision(
    *,
    principal_ref: str,
    role_id: str,
    permission: str,
    target_ref: str,
    target_type: str,
    evidence_refs: list[str],
    limitation_refs: list[str],
    trace_refs: list[str],
    check_report_ref: str,
    authority_envelope_ref: str,
) -> dict[str, Any]:
    decision, reason = evaluate_access(role_id, permission)
    payload = {
        "access_decision_id": stable_id("access", principal_ref, role_id, permission, target_ref),
        "schema_version": "main-citybrain.governance.access_decision.r1",
        "principal_ref": principal_ref,
        "role_ref": role_id,
        "permission": permission,
        "target_ref": target_ref,
        "target_type": target_type,
        "decision": decision,
        "reason": reason,
        "timestamp": utc_now(),
        "evidence_refs": unique(evidence_refs),
        "limitation_refs": unique(limitation_refs),
        "trace_refs": unique(trace_refs),
        "check_report_ref": check_report_ref,
        "authority_envelope_ref": authority_envelope_ref,
        "not_executed": NOT_EXECUTED,
        "cannot_claim": NON_CLAIMS,
        "production_iam_claim": False,
    }
    payload["access_decision_hash"] = stable_hash(payload)
    return payload


def build_audit_event(
    *,
    actor_ref: str,
    role_ref: str,
    action: str,
    target_ref: str,
    target_type: str,
    access_decision_ref: str,
    evidence_refs: list[str],
    limitation_refs: list[str],
    trace_refs: list[str],
    check_report_ref: str,
    authority_envelope_ref: str,
) -> dict[str, Any]:
    payload = {
        "audit_event_id": stable_id("audit:event", actor_ref, role_ref, action, target_ref),
        "schema_version": "main-citybrain.governance.audit_event.r1",
        "actor_ref": actor_ref,
        "role_ref": role_ref,
        "action": action,
        "target_ref": target_ref,
        "target_type": target_type,
        "timestamp": utc_now(),
        "access_decision_ref": access_decision_ref,
        "evidence_refs": unique(evidence_refs),
        "limitation_refs": unique(limitation_refs),
        "trace_refs": unique(trace_refs),
        "check_report_ref": check_report_ref,
        "authority_envelope_ref": authority_envelope_ref,
        "not_executed": NOT_EXECUTED,
        "cannot_claim": NON_CLAIMS,
    }
    for field in [
        "audit_event_id",
        "actor_ref",
        "role_ref",
        "action",
        "target_ref",
        "target_type",
        "timestamp",
        "access_decision_ref",
        "evidence_refs",
        "limitation_refs",
        "trace_refs",
        "check_report_ref",
        "authority_envelope_ref",
        "not_executed",
        "cannot_claim",
    ]:
        if not payload.get(field):
            raise ValueError(f"AuditEvent missing {field}")
    payload["audit_event_hash"] = stable_hash(payload)
    return payload


def build_observability_signal(
    *,
    signal_type: str,
    component_ref: str,
    severity: str,
    status: str,
    message: str,
    evidence_refs: list[str],
    limitation_refs: list[str],
    trace_refs: list[str],
) -> dict[str, Any]:
    payload = {
        "signal_id": stable_id("observability:signal", signal_type, component_ref, status),
        "schema_version": "main-citybrain.governance.observability_signal.r1",
        "signal_type": signal_type,
        "component_ref": component_ref,
        "severity": severity,
        "status": status,
        "message": message,
        "evidence_refs": unique(evidence_refs),
        "limitation_refs": unique(limitation_refs),
        "trace_refs": unique(trace_refs),
        "timestamp": utc_now(),
        "production_claim": False,
        "cannot_claim": NON_CLAIMS,
    }
    payload["observability_signal_hash"] = stable_hash(payload)
    return payload


def build_health_snapshot(
    *,
    component_ref: str,
    status: str,
    signal_refs: list[str],
    degradation_refs: list[str],
) -> dict[str, Any]:
    payload = {
        "health_snapshot_id": stable_id("health:snapshot", component_ref, status),
        "schema_version": "main-citybrain.governance.health_snapshot.r1",
        "component_ref": component_ref,
        "status": status,
        "signal_refs": signal_refs,
        "degradation_refs": degradation_refs,
        "timestamp": utc_now(),
        "local_replay_only": True,
        "production_monitoring_claim": False,
        "cannot_claim": NON_CLAIMS,
    }
    payload["health_snapshot_hash"] = stable_hash(payload)
    return payload


def build_degradation_record(
    *,
    component_ref: str,
    severity: str,
    reason: str,
    limitation_refs: list[str],
    trace_refs: list[str],
) -> dict[str, Any]:
    payload = {
        "degradation_record_id": stable_id("degradation", component_ref, severity, reason),
        "schema_version": "main-citybrain.governance.degradation_record.r1",
        "component_ref": component_ref,
        "severity": severity,
        "reason": reason,
        "limitation_refs": unique(limitation_refs),
        "trace_refs": unique(trace_refs),
        "timestamp": utc_now(),
        "production_incident_claim": False,
        "cannot_claim": NON_CLAIMS,
    }
    payload["degradation_record_hash"] = stable_hash(payload)
    return payload


__all__ = [
    "ALLOWED_PERMISSIONS",
    "FORBIDDEN_PERMISSIONS",
    "NON_CLAIMS",
    "NOT_EXECUTED",
    "ROLE_PERMISSIONS",
    "build_access_decision",
    "build_audit_event",
    "build_degradation_record",
    "build_health_snapshot",
    "build_observability_signal",
    "build_permission_policy",
    "build_role_definition",
    "evaluate_access",
    "stable_hash",
    "stable_id",
    "unique",
    "validate_role",
]

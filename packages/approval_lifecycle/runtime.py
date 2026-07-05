"""Approval lifecycle objects for Push 6 local/replay governance.

Authority level 3 is a proposal-governance layer only. It never grants
execution, dispatch/control/enforcement, official submission, legal approval,
certification, or production authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any


ALLOWED_REQUEST_STATUSES = [
    "draft",
    "submitted_for_local_review",
    "approved_local",
    "rejected_local",
    "modify_requested",
    "withdrawn",
    "expired_local",
]
FORBIDDEN_REQUEST_STATUSES = [
    "officially_submitted",
    "dispatch_authorized",
    "control_executed",
    "legal_approved",
    "certified",
]
ALLOWED_DECISIONS = [
    "approve_local",
    "reject_local",
    "request_modification",
    "defer",
    "withdraw",
]
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
]
APPROVAL_NON_CLAIMS = [
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
    "No cross-city claims until federation.",
    "No sealed ASK G1-G8 runtime change.",
    "No protected R7 runtime drift.",
    "All proposals are candidate proposals, never executed actions.",
    "Feature branches only; INFRA owns canonical integration.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def slug(value: Any) -> str:
    text = str(value or "unknown").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:80] or "unknown"


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


def merged_cannot_claim(*items: Any) -> list[str]:
    return unique([*[item for item in items], APPROVAL_NON_CLAIMS])


def merged_not_executed(*items: Any) -> list[str]:
    return unique([*[item for item in items], NOT_EXECUTED])


def validate_approval_request(request: dict[str, Any]) -> dict[str, Any]:
    status = request.get("status", "")
    if status in FORBIDDEN_REQUEST_STATUSES:
        raise ValueError(f"Forbidden approval request status: {status}")
    if status not in ALLOWED_REQUEST_STATUSES:
        raise ValueError(f"Unknown approval request status: {status}")
    if request.get("authority_level_requested") != 3:
        raise ValueError("Approval requests in this lane must request authority level 3")
    for field in ["check_report_ref", "authority_envelope_ref", "evidence_refs", "limitation_refs", "trace_refs", "cannot_claim", "not_executed"]:
        if not request.get(field):
            raise ValueError(f"Approval request missing {field}")
    if request.get("execution_created") is True or request.get("official_submission_created") is True:
        raise ValueError("Approval requests cannot create execution or official submission")
    return request


def validate_approval_decision(decision: dict[str, Any]) -> dict[str, Any]:
    value = decision.get("decision", "")
    if value not in ALLOWED_DECISIONS:
        raise ValueError(f"Unknown approval decision: {value}")
    for field in ["check_report_ref", "authority_envelope_ref", "evidence_refs", "limitation_refs", "trace_refs", "not_executed"]:
        if not decision.get(field):
            raise ValueError(f"Approval decision missing {field}")
    if decision.get("execution_created") is True or decision.get("official_submission_created") is True:
        raise ValueError("Approval decisions cannot create execution or official submission")
    return decision


def build_approval_subject_ref(
    *,
    subject_ref: str,
    subject_type: str,
    source_refs: list[str],
    evidence_refs: list[str],
    limitation_refs: list[str],
    trace_refs: list[str],
) -> dict[str, Any]:
    payload = {
        "approval_subject_ref_id": stable_id("approval:subject", subject_ref, subject_type),
        "schema_version": "main-citybrain.approval_lifecycle.subject_ref.r1",
        "subject_ref": subject_ref,
        "subject_type": subject_type,
        "source_refs": unique(source_refs),
        "evidence_refs": unique(evidence_refs),
        "limitation_refs": unique(limitation_refs),
        "trace_refs": unique(trace_refs),
        "local_replay_only": True,
        "proposal_only": True,
        "execution_created": False,
        "cannot_claim": merged_cannot_claim("approval subject is not an executed action"),
    }
    payload["approval_subject_ref_hash"] = stable_hash(payload)
    return payload


def build_authority_level_3_envelope(
    *,
    subject_ref: str,
    proposal_ref: str,
    check_report_ref: str,
    authority_envelope_ref: str,
    evidence_refs: list[str],
    limitation_refs: list[str],
    trace_refs: list[str],
    created_at: str | None = None,
) -> dict[str, Any]:
    timestamp = created_at or utc_now()
    payload = {
        "authority_envelope_level_3_id": stable_id("authority:l3", subject_ref, proposal_ref),
        "schema_version": "main-citybrain.authority_envelope.level_3.r1",
        "authority_level": 3,
        "authority_level_label": "level_3_proposal_governance_local_approval",
        "subject_ref": subject_ref,
        "proposal_ref": proposal_ref,
        "check_report_ref": check_report_ref,
        "source_authority_envelope_ref": authority_envelope_ref,
        "evidence_refs": unique(evidence_refs),
        "limitation_refs": unique(limitation_refs),
        "trace_refs": unique(trace_refs),
        "proposal_governance_exists": True,
        "local_approval_workflow_exists": True,
        "execution_authority": False,
        "dispatch_authority": False,
        "control_authority": False,
        "official_submission_authority": False,
        "legal_certified_authority": False,
        "production_authority": False,
        "created_at": timestamp,
        "local_replay_only": True,
        "not_executed": merged_not_executed(),
        "cannot_claim": merged_cannot_claim("authority level 3 is not execution authority"),
    }
    payload["authority_level_3_hash"] = stable_hash(payload)
    return payload


def build_approval_request(
    *,
    subject_ref: str,
    subject_type: str,
    proposal_ref: str,
    requested_by_ref: str,
    status: str,
    check_report_ref: str,
    authority_envelope_ref: str,
    evidence_refs: list[str],
    limitation_refs: list[str],
    trace_refs: list[str],
    cannot_claim: list[str] | None = None,
    not_executed: list[str] | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    timestamp = created_at or utc_now()
    payload = {
        "approval_request_id": stable_id("approval:request", subject_ref, proposal_ref, requested_by_ref),
        "schema_version": "main-citybrain.approval_lifecycle.request.r1",
        "subject_ref": subject_ref,
        "subject_type": subject_type,
        "proposal_ref": proposal_ref,
        "requested_by_ref": requested_by_ref,
        "created_at": timestamp,
        "status": status,
        "authority_level_requested": 3,
        "check_report_ref": check_report_ref,
        "authority_envelope_ref": authority_envelope_ref,
        "evidence_refs": unique(evidence_refs),
        "limitation_refs": unique(limitation_refs),
        "trace_refs": unique(trace_refs),
        "cannot_claim": merged_cannot_claim(cannot_claim or []),
        "not_executed": merged_not_executed(not_executed or []),
        "execution_created": False,
        "official_submission_created": False,
        "local_replay_only": True,
    }
    validate_approval_request(payload)
    payload["approval_request_hash"] = stable_hash(payload)
    return payload


def build_approval_decision(
    *,
    approval_request_ref: str,
    decision: str,
    decided_by_ref: str,
    reason: str,
    modification_notes: str,
    evidence_refs: list[str],
    limitation_refs: list[str],
    trace_refs: list[str],
    check_report_ref: str,
    authority_envelope_ref: str,
    not_executed: list[str] | None = None,
    decided_at: str | None = None,
) -> dict[str, Any]:
    timestamp = decided_at or utc_now()
    payload = {
        "approval_decision_id": stable_id("approval:decision", approval_request_ref, decision, decided_by_ref),
        "schema_version": "main-citybrain.approval_lifecycle.decision.r1",
        "approval_request_ref": approval_request_ref,
        "decision": decision,
        "decided_by_ref": decided_by_ref,
        "decided_at": timestamp,
        "reason": reason,
        "modification_notes": modification_notes,
        "evidence_refs": unique(evidence_refs),
        "limitation_refs": unique(limitation_refs),
        "trace_refs": unique(trace_refs),
        "check_report_ref": check_report_ref,
        "authority_envelope_ref": authority_envelope_ref,
        "not_executed": merged_not_executed(not_executed or []),
        "execution_created": False,
        "official_submission_created": False,
        "local_replay_only": True,
    }
    validate_approval_decision(payload)
    payload["approval_decision_hash"] = stable_hash(payload)
    return payload


def build_approval_lifecycle_state(
    *,
    approval_request: dict[str, Any],
    decisions: list[dict[str, Any]],
    authority_level_3_ref: str,
) -> dict[str, Any]:
    latest_decision = decisions[-1] if decisions else {}
    state = {
        "approve_local": "approved_local",
        "reject_local": "rejected_local",
        "request_modification": "modify_requested",
        "defer": "submitted_for_local_review",
        "withdraw": "withdrawn",
    }.get(latest_decision.get("decision"), approval_request["status"])
    payload = {
        "approval_lifecycle_state_id": stable_id("approval:lifecycle_state", approval_request["approval_request_id"]),
        "schema_version": "main-citybrain.approval_lifecycle.state.r1",
        "approval_request_ref": approval_request["approval_request_id"],
        "current_state": state,
        "authority_level_3_ref": authority_level_3_ref,
        "decision_refs": [item["approval_decision_id"] for item in decisions],
        "approved_local": state == "approved_local",
        "executed": False,
        "officially_submitted": False,
        "dispatch_control_enforcement_executed": False,
        "legal_certified_finding_created": False,
        "not_executed": merged_not_executed(approval_request.get("not_executed", [])),
        "cannot_claim": approval_request["cannot_claim"],
        "local_replay_only": True,
        "updated_at": utc_now(),
    }
    payload["approval_lifecycle_state_hash"] = stable_hash(payload)
    return payload


def build_approval_audit_event(
    *,
    event_type: str,
    approval_request_ref: str,
    actor_ref: str,
    evidence_refs: list[str],
    limitation_refs: list[str],
    trace_refs: list[str],
    check_report_ref: str,
    authority_envelope_ref: str,
    decision_ref: str | None = None,
    event_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "approval_audit_event_id": stable_id("approval:audit_event", event_type, approval_request_ref, decision_ref or ""),
        "schema_version": "main-citybrain.approval_lifecycle.audit_event.r1",
        "event_type": event_type,
        "approval_request_ref": approval_request_ref,
        "approval_decision_ref": decision_ref,
        "actor_ref": actor_ref,
        "event_time": utc_now(),
        "event_payload": event_payload or {},
        "evidence_refs": unique(evidence_refs),
        "limitation_refs": unique(limitation_refs),
        "trace_refs": unique(trace_refs),
        "check_report_ref": check_report_ref,
        "authority_envelope_ref": authority_envelope_ref,
        "not_executed": merged_not_executed(),
        "execution_created": False,
        "official_submission_created": False,
        "local_replay_only": True,
    }
    payload["approval_audit_event_hash"] = stable_hash(payload)
    return payload


def build_approval_policy(*, policy_id: str, source_refs: list[str]) -> dict[str, Any]:
    payload = {
        "approval_policy_id": policy_id,
        "schema_version": "main-citybrain.approval_lifecycle.policy.r1",
        "policy_kind": "authority_level_3_local_proposal_governance",
        "allowed_request_statuses": ALLOWED_REQUEST_STATUSES,
        "forbidden_request_statuses": FORBIDDEN_REQUEST_STATUSES,
        "allowed_decisions": ALLOWED_DECISIONS,
        "authority_level_3_means": ["proposal governance", "local approval workflow", "auditability"],
        "authority_level_3_does_not_mean": [
            "execution authority",
            "dispatch authority",
            "control authority",
            "official submission authority",
            "legal/certified authority",
            "production authority",
        ],
        "requires_check_report_ref": True,
        "requires_authority_envelope_ref": True,
        "requires_not_executed": True,
        "source_refs": unique(source_refs),
        "local_replay_only": True,
        "cannot_claim": APPROVAL_NON_CLAIMS,
    }
    payload["approval_policy_hash"] = stable_hash(payload)
    return payload


def build_lifecycle_agent_run(
    *,
    input_request_refs: list[str],
    output_decision_refs: list[str],
    audit_event_refs: list[str],
    policy_ref: str,
) -> dict[str, Any]:
    payload = {
        "approval_lifecycle_agent_run_id": stable_id("approval:agent_run", input_request_refs, output_decision_refs),
        "schema_version": "main-citybrain.approval_lifecycle.agent_run.r1",
        "agent_kind": "local_replay_policy_checker",
        "policy_ref": policy_ref,
        "input_approval_request_refs": input_request_refs,
        "output_approval_decision_refs": output_decision_refs,
        "audit_event_refs": audit_event_refs,
        "runner_mode": "deterministic_local_replay",
        "live_llm_used": False,
        "production_api_used": False,
        "url_fetch_used": False,
        "execution_created": False,
        "official_submission_created": False,
        "local_replay_only": True,
        "not_executed": merged_not_executed(),
        "cannot_claim": APPROVAL_NON_CLAIMS,
        "created_at": utc_now(),
    }
    payload["approval_lifecycle_agent_run_hash"] = stable_hash(payload)
    return payload

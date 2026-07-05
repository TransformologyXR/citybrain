"""Review-only PLAN mode helpers for CityBrain Push 6 Lane B."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


EXECUTION_STATUS = "not_executed"
ALLOWED_REVIEW_STATES = {"draft_review", "pending_approval_lifecycle", "abstained_no_safe_option", "blocked_waiting_for_approval"}
FORBIDDEN_CLAIM_TOKENS = [
    "dispatch command",
    "control command",
    "enforcement action",
    "official submission",
    "legal finding",
    "certified finding",
    "approved for execution",
]


@dataclass(frozen=True)
class PlanRequest:
    plan_request_id: str
    scope_ref: str
    prompt: str
    evidence_refs: list[str]
    limitation_refs: list[str]
    trace_refs: list[str]
    review_state: str = "pending_approval_lifecycle"
    execution_status: str = EXECUTION_STATUS
    cannot_claim: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "plan_request_id": self.plan_request_id,
            "schema_version": "main-citybrain.push6.plan_mode.plan_request.v1",
            "scope_ref": self.scope_ref,
            "prompt": self.prompt,
            "evidence_refs": list(self.evidence_refs),
            "limitation_refs": list(self.limitation_refs),
            "trace_refs": list(self.trace_refs),
            "review_state": self.review_state,
            "execution_status": self.execution_status,
            "cannot_claim": list(self.cannot_claim),
        }


@dataclass(frozen=True)
class PlanOption:
    plan_option_id: str
    option_set_ref: str
    title: str
    description: str
    expected_effect_local_review: str
    constraints: list[str]
    assumptions: list[str]
    risks: list[str]
    evidence_refs: list[str]
    limitation_refs: list[str]
    trace_refs: list[str]
    check_report_ref: str
    authority_envelope_ref: str
    cannot_claim: list[str]
    requires_approval: bool = True
    execution_status: str = EXECUTION_STATUS

    def as_dict(self) -> dict[str, Any]:
        return {
            "plan_option_id": self.plan_option_id,
            "schema_version": "main-citybrain.push6.plan_mode.plan_option.v1",
            "option_set_ref": self.option_set_ref,
            "title": self.title,
            "description": self.description,
            "expected_effect_local_review": self.expected_effect_local_review,
            "constraints": list(self.constraints),
            "assumptions": list(self.assumptions),
            "risks": list(self.risks),
            "evidence_refs": list(self.evidence_refs),
            "limitation_refs": list(self.limitation_refs),
            "trace_refs": list(self.trace_refs),
            "check_report_ref": self.check_report_ref,
            "authority_envelope_ref": self.authority_envelope_ref,
            "requires_approval": self.requires_approval,
            "execution_status": self.execution_status,
            "cannot_claim": list(self.cannot_claim),
        }


def ref_id(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        if item.get(key):
            return str(item[key])
    return ""


def validate_plan_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    option_sets = bundle.get("option_sets", [])
    plan_options = bundle.get("plan_options", [])
    baselines = bundle.get("do_nothing_baselines", [])
    approval_bindings = bundle.get("approval_bindings", [])

    if not option_sets:
        errors.append("missing_option_sets")
    if not baselines:
        errors.append("missing_do_nothing_baseline")
    if not approval_bindings:
        errors.append("missing_approval_bindings")

    for option_set in option_sets:
        option_set_id = option_set.get("option_set_id", "<missing-option-set-id>")
        required = [
            "plan_request_ref",
            "scope_ref",
            "option_refs",
            "do_nothing_baseline_ref",
            "constraints_ref",
            "assumptions_ref",
            "risk_summary_ref",
            "evidence_refs",
            "limitation_refs",
            "trace_refs",
            "check_report_ref",
            "authority_envelope_ref",
            "approval_request_ref",
            "review_state",
            "execution_status",
            "cannot_claim",
        ]
        for key in required:
            if key not in option_set or option_set.get(key) in (None, "", []):
                errors.append(f"{option_set_id}:missing:{key}")
        if option_set.get("execution_status") != EXECUTION_STATUS:
            errors.append(f"{option_set_id}:execution_status_not_not_executed")
        if option_set.get("review_state") not in ALLOWED_REVIEW_STATES:
            errors.append(f"{option_set_id}:unsupported_review_state:{option_set.get('review_state')}")

    for option in plan_options:
        option_id = option.get("plan_option_id", "<missing-plan-option-id>")
        if option.get("requires_approval") is not True:
            errors.append(f"{option_id}:requires_approval_not_true")
        if option.get("execution_status") != EXECUTION_STATUS:
            errors.append(f"{option_id}:execution_status_not_not_executed")
        for key in ["evidence_refs", "limitation_refs", "trace_refs", "check_report_ref", "authority_envelope_ref"]:
            if not option.get(key):
                errors.append(f"{option_id}:missing:{key}")
        text = " ".join(str(option.get(key, "")) for key in ["title", "description", "expected_effect_local_review"]).lower()
        for token in FORBIDDEN_CLAIM_TOKENS:
            if token in text:
                errors.append(f"{option_id}:forbidden_execution_or_official_claim:{token}")

    for binding in approval_bindings:
        binding_id = binding.get("plan_approval_binding_id", "<missing-approval-binding-id>")
        if not binding.get("approval_request_ref"):
            errors.append(f"{binding_id}:missing_approval_request_ref")
        if binding.get("execution_status") != EXECUTION_STATUS:
            errors.append(f"{binding_id}:execution_status_not_not_executed")
        if binding.get("approval_lifecycle_used") is not True:
            warnings.append(f"{binding_id}:approval_lifecycle_not_available")

    return {
        "status": "PASS" if not errors else "FAIL",
        "option_set_count": len(option_sets),
        "plan_option_count": len(plan_options),
        "do_nothing_baseline_count": len(baselines),
        "approval_binding_count": len(approval_bindings),
        "errors": errors,
        "warnings": warnings,
    }

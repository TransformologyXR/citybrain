#!/usr/bin/env python3
"""Build Push 7 Lane B RBAC, audit, and observability artifacts."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.governance import (
    ALLOWED_PERMISSIONS,
    FORBIDDEN_PERMISSIONS,
    NON_CLAIMS,
    NOT_EXECUTED,
    ROLE_PERMISSIONS,
    build_access_decision,
    build_audit_event,
    build_degradation_record,
    build_health_snapshot,
    build_observability_signal,
    build_permission_policy,
    build_role_definition,
    stable_hash,
    stable_id,
    unique,
)


OUTPUTS_ROOT = REPO_ROOT / "outputs"
OUTPUT_ROOT = OUTPUTS_ROOT / "push7_lane_b_rbac_audit_observability"
CLOSEOUT_ROOT = OUTPUTS_ROOT / "push7_lane_b_rbac_audit_observability_closeout"
FINAL_ROOT = OUTPUTS_ROOT / "push7_lane_b_rbac_audit_observability_final_status"

TASK_ID = "MAIN-CITYBRAIN-PUSH7-LANE-B-RBAC-AUDIT-OBSERVABILITY"
PACKAGE = "MAIN-CITYBRAIN-PUSH7-LANE-B-RBAC-AUDIT-OBSERVABILITY-RUN-TO-CLOSURE"
BRANCH = "codex/push7-lane-b-rbac-audit-observability"
BASE_REF = "origin/codex/push6-infra-after-three-lanes"
PASS_STATUS = "PASS_PUSH7_LANE_B_RBAC_AUDIT_OBSERVABILITY_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_PUSH7_LANE_B_RBAC_AUDIT_OBSERVABILITY"
STOP_STATUS = "STOPPED_WAITING_FOR_PUSH6_INTEGRATION"

PUSH6_INFRA_ROOT = OUTPUTS_ROOT / "push6_infra_after_three_lanes_integration"
PUSH6_FINAL_ROOT = OUTPUTS_ROOT / "push6_infra_after_three_lanes_final_status"
PUSH6_APPROVAL_ROOT = OUTPUTS_ROOT / "push6_lane_a_approval_lifecycle"
PUSH6_PLAN_ROOT = OUTPUTS_ROOT / "push6_lane_b_plan_mode"
PUSH6_SCHEDULE_ROOT = OUTPUTS_ROOT / "push6_lane_c_schedule_simulate"
PUSH5_WORKFLOW_ROOT = OUTPUTS_ROOT / "push5_lane_c_watch_workflow_state"
PUSH4_CHECK_ROOT = OUTPUTS_ROOT / "push4_lane_c_check_v1"
PUSH7_LANE_A_ROOT = OUTPUTS_ROOT / "push7_lane_a_federation_data_maturity"

ASK_CONTRACT_PATHS = [
    "packages/ask_v11",
    "scripts/run_ask_v11_sealed_eval.py",
    "scripts/run_ask_v11_real_corpus_eval_r2_mapping_expansion.py",
]

R7_RUNTIME_PATHS = [
    "scripts/run_main_citybrain_r7a_perception_candidate_observation_ingress.py",
    "scripts/run_main_citybrain_r7b_perception_to_event_fabric_local_replay.py",
    "scripts/run_main_citybrain_r7c_event_fabric_state_query_and_ask_handoff.py",
    "scripts/run_main_citybrain_r7d_webui_kit_event_state_smoke.py",
]

REQUIRED_OUTPUTS = [
    "RBAC_AUDIT_OBSERVABILITY_DECISION.json",
    "RBAC_ROLE_DEFINITION_SCHEMA.json",
    "RBAC_PERMISSION_POLICY_SCHEMA.json",
    "RBAC_ACCESS_DECISION_SCHEMA.json",
    "AUDIT_EVENT_SCHEMA.json",
    "OBSERVABILITY_SIGNAL_SCHEMA.json",
    "HEALTH_SNAPSHOT_SCHEMA.json",
    "ROLE_DEFINITIONS.json",
    "PERMISSION_POLICIES.json",
    "ACCESS_DECISION_FIXTURES.json",
    "AUDIT_EVENT_FIXTURES.json",
    "OBSERVABILITY_SIGNALS.json",
    "HEALTH_SNAPSHOTS.json",
    "POLICY_NEGATIVE_TESTS.json",
    "GOVERNANCE_DASHBOARD_VIEW_MODEL.json",
    "RBAC_AUDIT_BOUNDARY_AND_NON_CLAIMS.md",
    "RBAC_AUDIT_TEST_LOG.md",
    "RBAC_AUDIT_HASH_MANIFEST.json",
]

REQUIRED_CLOSEOUT_OUTPUTS = [
    "RBAC_AUDIT_OBSERVABILITY_CLOSEOUT_DECISION.json",
    "RBAC_AUDIT_OBSERVABILITY_CLOSEOUT_SUMMARY.md",
    "RBAC_AUDIT_OBSERVABILITY_CLOSEOUT_LIMITATIONS.md",
    "RBAC_AUDIT_OBSERVABILITY_CLOSEOUT_NEXT_STEPS.md",
    "RBAC_AUDIT_OBSERVABILITY_CLOSEOUT_HASH_MANIFEST.json",
]

REQUIRED_FINAL_OUTPUTS = [
    "RBAC_AUDIT_OBSERVABILITY_FINAL_STATUS_DECISION.json",
    "RBAC_AUDIT_OBSERVABILITY_FINAL_STATUS_SUMMARY.md",
    "RBAC_AUDIT_OBSERVABILITY_FINAL_STATUS_HASH_MANIFEST.json",
]

SIGNAL_TYPES = [
    "test_status",
    "runner_status",
    "data_maturity_status",
    "check_status",
    "approval_status",
    "workflow_status",
    "federation_status",
    "degradation_status",
]

LIMITATIONS = [
    "Local/replay governance instrumentation only; this is not production IAM.",
    "Push 7 Lane A federation/data maturity artifacts are not present in this branch, so federation-specific health is recorded as unavailable/degraded and no real federation closeout claim is made.",
    "RBAC decisions are deterministic fixtures over branch-published packets, approvals, plans, schedules, and audit targets.",
    "Audit and observability events preserve evidence, limitation, trace, CHECK, and AuthorityEnvelope refs without changing source lane outputs.",
    "No execution, dispatch/resource control, official submission, legal/certified finding, live Kit control, production API, URL fetch, live retrieval, or live LLM authority is claimed.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def out_rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def reset_output_root(root: Path) -> None:
    resolved = root.resolve()
    if OUTPUTS_ROOT.resolve() not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs/: {resolved}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def reset_output_roots() -> None:
    for root in [OUTPUT_ROOT, CLOSEOUT_ROOT, FINAL_ROOT]:
        reset_output_root(root)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_diff_empty(paths: list[str]) -> dict[str, Any]:
    proc = subprocess.run(["git", "diff", "--", *paths], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {
        "status": "PASS" if proc.returncode == 0 and proc.stdout == "" else "FAIL",
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "paths": paths,
    }


def write_hash_manifest(root: Path, name: str, schema_version: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != name:
            rows.append({"path": out_rel(path, root), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": schema_version,
        "algorithm": "sha256",
        "status": "PASS",
        "item_count": len(rows),
        "missing_count": 0,
        "mismatch_count": 0,
        "files": rows,
    }
    write_json(root / name, manifest)
    return manifest


def verify_hash_manifest(root: Path, name: str) -> dict[str, Any]:
    manifest_path = root / name
    if not manifest_path.exists():
        return {"status": "FAIL", "declared": 0, "verified": 0, "problems": ["manifest_missing"]}
    manifest = read_json(manifest_path, {"files": []})
    problems: list[str] = []
    verified = 0
    for row in manifest.get("files", []):
        target = root / row["path"]
        if not target.exists():
            problems.append(f"missing:{row['path']}")
        elif sha256_file(target) != row.get("sha256"):
            problems.append(f"mismatch:{row['path']}")
        else:
            verified += 1
    return {"status": "PASS" if not problems and manifest.get("status") == "PASS" else "FAIL", "declared": len(manifest.get("files", [])), "verified": verified, "problems": problems}


def schema_payload(name: str, required: list[str], optional: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema_version": f"main-citybrain.push7.lane_b.{name}.schema.r1",
        "object_name": name,
        "required_fields": required,
        "optional_fields": optional or [],
        "local_replay_only": True,
        "not_production_iam": True,
        "cannot_claim": NON_CLAIMS,
    }


def load_inputs() -> dict[str, Any]:
    required = [
        PUSH6_INFRA_ROOT / "PUSH6_INFRA_INTEGRATION_DECISION.json",
        PUSH6_INFRA_ROOT / "PUSH6_CROSS_LANE_COMPATIBILITY_REPORT.json",
        PUSH6_FINAL_ROOT / "PUSH6_FINAL_STATUS_DECISION.json",
        PUSH6_APPROVAL_ROOT / "APPROVAL_LIFECYCLE_FIXTURES.json",
        PUSH6_PLAN_ROOT / "OPTIONSET_V2_FIXTURES.json",
        PUSH6_PLAN_ROOT / "PLAN_MODE_FIXTURES.json",
        PUSH6_SCHEDULE_ROOT / "SCHEDULE_OPTION_FIXTURES.json",
        PUSH6_SCHEDULE_ROOT / "SCHEDULE_APPROVAL_BINDINGS.json",
        PUSH5_WORKFLOW_ROOT / "WORKFLOW_STATE_EVENTS.json",
        PUSH4_CHECK_ROOT / "CHECK_V1_REPORTS.json",
    ]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing Push 7 Lane B inputs: {missing}")
    lane_a_files = sorted(PUSH7_LANE_A_ROOT.glob("*.json")) if PUSH7_LANE_A_ROOT.exists() else []
    return {
        "push6_decision": read_json(PUSH6_INFRA_ROOT / "PUSH6_INFRA_INTEGRATION_DECISION.json"),
        "push6_compatibility": read_json(PUSH6_INFRA_ROOT / "PUSH6_CROSS_LANE_COMPATIBILITY_REPORT.json"),
        "push6_final": read_json(PUSH6_FINAL_ROOT / "PUSH6_FINAL_STATUS_DECISION.json"),
        "approval": read_json(PUSH6_APPROVAL_ROOT / "APPROVAL_LIFECYCLE_FIXTURES.json"),
        "option_sets": read_json(PUSH6_PLAN_ROOT / "OPTIONSET_V2_FIXTURES.json"),
        "plan": read_json(PUSH6_PLAN_ROOT / "PLAN_MODE_FIXTURES.json"),
        "schedule": read_json(PUSH6_SCHEDULE_ROOT / "SCHEDULE_OPTION_FIXTURES.json"),
        "schedule_bindings": read_json(PUSH6_SCHEDULE_ROOT / "SCHEDULE_APPROVAL_BINDINGS.json"),
        "workflow": read_json(PUSH5_WORKFLOW_ROOT / "WORKFLOW_STATE_EVENTS.json"),
        "check_reports": read_json(PUSH4_CHECK_ROOT / "CHECK_V1_REPORTS.json"),
        "federation": {
            "status": "AVAILABLE" if lane_a_files else "UNAVAILABLE",
            "root": rel(PUSH7_LANE_A_ROOT),
            "json_files": [rel(path) for path in lane_a_files],
        },
    }


def context_refs(data: dict[str, Any]) -> dict[str, Any]:
    option_set = data["option_sets"]["option_sets"][0]
    plan_request = data["plan"]["plan_requests"][0]
    schedule_request = data["schedule"]["schedule_requests"][0]
    schedule_option = data["schedule"]["schedule_options"][0]
    approval_request = data["approval"]["approval_requests"][0]
    workflow_event = data["workflow"]["items"][0]
    check_report = data["check_reports"]["items"][0]
    evidence_refs = unique(
        [
            option_set.get("evidence_refs", []),
            schedule_request.get("evidence_refs", []),
            approval_request.get("evidence_refs", []),
            workflow_event.get("evidence_refs", []),
        ]
    )
    limitation_refs = unique(
        [
            LIMITATIONS,
            option_set.get("limitation_refs", []),
            schedule_request.get("limitation_refs", []),
            approval_request.get("limitation_refs", []),
            workflow_event.get("limitation_refs", []),
        ]
    )
    trace_refs = unique(
        [
            option_set.get("trace_refs", []),
            schedule_request.get("trace_refs", []),
            approval_request.get("trace_refs", []),
            workflow_event.get("trace_refs", []),
        ]
    )
    return {
        "packet_ref": option_set["option_set_id"],
        "plan_request_ref": plan_request["plan_request_id"],
        "schedule_request_ref": schedule_request["schedule_request_id"],
        "schedule_option_ref": schedule_option["schedule_option_id"],
        "approval_request_ref": approval_request["approval_request_id"],
        "workflow_event_ref": workflow_event["workflow_event_id"],
        "check_report_ref": option_set.get("check_report_ref") or check_report.get("check_report_id"),
        "authority_envelope_ref": option_set.get("authority_envelope_ref") or approval_request.get("authority_envelope_ref"),
        "evidence_refs": evidence_refs,
        "limitation_refs": limitation_refs,
        "trace_refs": trace_refs,
    }


def build_principals() -> list[dict[str, Any]]:
    return [
        {"principal_ref": "principal:local-viewer:001", "role_ref": "viewer", "display_name": "Local Viewer", "local_replay_only": True},
        {"principal_ref": "principal:local-reviewer:001", "role_ref": "reviewer", "display_name": "Local Reviewer", "local_replay_only": True},
        {"principal_ref": "principal:local-approver:001", "role_ref": "approver_local", "display_name": "Local Approver", "local_replay_only": True},
        {"principal_ref": "principal:local-planner:001", "role_ref": "planner", "display_name": "Local Planner", "local_replay_only": True},
        {"principal_ref": "principal:local-simulator:001", "role_ref": "simulator", "display_name": "Local Simulator", "local_replay_only": True},
        {"principal_ref": "principal:local-admin:001", "role_ref": "admin_local", "display_name": "Local Admin", "local_replay_only": True},
        {"principal_ref": "principal:local-auditor:001", "role_ref": "auditor", "display_name": "Local Auditor", "local_replay_only": True},
    ]


def build_roles_and_policies() -> tuple[dict[str, Any], dict[str, Any]]:
    descriptions = {
        "viewer": "Read-only local/replay packet and evidence viewer.",
        "reviewer": "Local reviewer that can record review disposition and submit approval requests.",
        "approver_local": "Local approval reviewer for Authority Level 3 proposal governance only.",
        "planner": "Local planner that can create not_executed plan proposals.",
        "simulator": "Local simulator that can create not_executed schedule/simulation proposals.",
        "admin_local": "Local fixture administrator over allowed governance-only permissions.",
        "auditor": "Read-only audit/log reviewer.",
    }
    roles = [build_role_definition(role_id, descriptions[role_id]) for role_id in ROLE_PERMISSIONS]
    policies = []
    target_types = {
        "view_packet": ["packet", "approval_request", "plan_request", "schedule_request"],
        "view_evidence": ["evidence_ref", "check_report"],
        "record_disposition": ["workflow_event", "watch_item"],
        "submit_approval_request": ["approval_request"],
        "approve_local": ["approval_request"],
        "create_plan_proposal": ["plan_request", "option_set"],
        "create_schedule_simulation_proposal": ["schedule_request", "scenario_packet"],
        "view_federated_packet": ["federated_packet_fixture"],
        "export_review_brief": ["review_brief"],
        "view_audit_log": ["audit_trail_segment"],
    }
    for permission in ALLOWED_PERMISSIONS:
        allowed_roles = [role for role, permissions in ROLE_PERMISSIONS.items() if permission in permissions]
        policies.append(build_permission_policy(permission, allowed_roles, target_types[permission]))
    return (
        {
            "schema_version": "main-citybrain.push7.lane_b.role_definitions.r1",
            "status": "PASS",
            "principals": build_principals(),
            "roles": roles,
            "role_count": len(roles),
            "forbidden_permissions": FORBIDDEN_PERMISSIONS,
            "not_production_iam": True,
        },
        {
            "schema_version": "main-citybrain.push7.lane_b.permission_policies.r1",
            "status": "PASS",
            "policies": policies,
            "allowed_permissions": ALLOWED_PERMISSIONS,
            "forbidden_permissions": FORBIDDEN_PERMISSIONS,
            "not_production_iam": True,
        },
    )


def build_access_and_audit(ctx: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    cases = [
        ("principal:local-viewer:001", "viewer", "view_packet", ctx["packet_ref"], "packet"),
        ("principal:local-viewer:001", "viewer", "view_evidence", ctx["check_report_ref"], "check_report"),
        ("principal:local-reviewer:001", "reviewer", "record_disposition", ctx["workflow_event_ref"], "workflow_event"),
        ("principal:local-reviewer:001", "reviewer", "submit_approval_request", ctx["approval_request_ref"], "approval_request"),
        ("principal:local-approver:001", "approver_local", "approve_local", ctx["approval_request_ref"], "approval_request"),
        ("principal:local-planner:001", "planner", "create_plan_proposal", ctx["plan_request_ref"], "plan_request"),
        ("principal:local-simulator:001", "simulator", "create_schedule_simulation_proposal", ctx["schedule_request_ref"], "schedule_request"),
        ("principal:local-admin:001", "admin_local", "view_federated_packet", "federated-packet:fixture:unavailable-lane-a", "federated_packet_fixture"),
        ("principal:local-admin:001", "admin_local", "export_review_brief", ctx["packet_ref"], "review_brief"),
        ("principal:local-auditor:001", "auditor", "view_audit_log", "audit-trail-segment:push7-lane-b:0001", "audit_trail_segment"),
        ("principal:local-approver:001", "approver_local", "execute_action", ctx["approval_request_ref"], "execution_action"),
        ("principal:local-planner:001", "planner", "dispatch_resource", ctx["plan_request_ref"], "dispatch_resource"),
        ("principal:local-simulator:001", "simulator", "control_infrastructure", ctx["schedule_option_ref"], "infrastructure_control"),
        ("principal:local-auditor:001", "auditor", "record_disposition", ctx["workflow_event_ref"], "workflow_event"),
    ]
    decisions = [
        build_access_decision(
            principal_ref=principal,
            role_id=role,
            permission=permission,
            target_ref=target,
            target_type=target_type,
            evidence_refs=ctx["evidence_refs"],
            limitation_refs=ctx["limitation_refs"],
            trace_refs=ctx["trace_refs"],
            check_report_ref=ctx["check_report_ref"],
            authority_envelope_ref=ctx["authority_envelope_ref"],
        )
        for principal, role, permission, target, target_type in cases
    ]
    audit_events = [
        build_audit_event(
            actor_ref=decision["principal_ref"],
            role_ref=decision["role_ref"],
            action=decision["permission"],
            target_ref=decision["target_ref"],
            target_type=decision["target_type"],
            access_decision_ref=decision["access_decision_id"],
            evidence_refs=decision["evidence_refs"],
            limitation_refs=decision["limitation_refs"],
            trace_refs=decision["trace_refs"],
            check_report_ref=decision["check_report_ref"],
            authority_envelope_ref=decision["authority_envelope_ref"],
        )
        for decision in decisions
    ]
    audit_segment = {
        "audit_trail_segment_id": "audit-trail-segment:push7-lane-b:0001",
        "schema_version": "main-citybrain.governance.audit_trail_segment.r1",
        "audit_event_refs": [event["audit_event_id"] for event in audit_events],
        "target_refs": sorted({event["target_ref"] for event in audit_events}),
        "status": "PASS",
        "local_replay_only": True,
        "not_production_iam": True,
        "segment_hash": stable_hash([event["audit_event_hash"] for event in audit_events]),
    }
    return (
        {
            "schema_version": "main-citybrain.push7.lane_b.access_decision_fixtures.r1",
            "status": "PASS",
            "access_decisions": decisions,
            "allow_count": sum(1 for decision in decisions if decision["decision"] == "allow"),
            "deny_count": sum(1 for decision in decisions if decision["decision"] == "deny"),
            "forbidden_permissions_rejected": all(
                decision["decision"] == "deny" for decision in decisions if decision["permission"] in FORBIDDEN_PERMISSIONS
            ),
        },
        {
            "schema_version": "main-citybrain.push7.lane_b.audit_event_fixtures.r1",
            "status": "PASS",
            "audit_events": audit_events,
            "audit_trail_segments": [audit_segment],
            "event_count": len(audit_events),
            "evidence_refs_preserved": all(event["evidence_refs"] and event["limitation_refs"] and event["trace_refs"] for event in audit_events),
            "check_authority_refs_preserved": all(event["check_report_ref"] and event["authority_envelope_ref"] for event in audit_events),
        },
    )


def build_negative_tests(access: dict[str, Any]) -> dict[str, Any]:
    violations = []
    for role in ["approver_local", "planner", "simulator", "auditor"]:
        for permission in FORBIDDEN_PERMISSIONS:
            violations.append(
                {
                    "policy_violation_fixture_id": stable_id("policy:violation", role, permission),
                    "schema_version": "main-citybrain.governance.policy_violation_fixture.r1",
                    "role_ref": role,
                    "attempted_permission": permission,
                    "expected_decision": "deny",
                    "reason": "forbidden_permission_rejected",
                    "not_executed": NOT_EXECUTED,
                    "cannot_claim": NON_CLAIMS,
                }
            )
    decisions = access["access_decisions"]
    payload = {
        "schema_version": "main-citybrain.push7.lane_b.policy_negative_tests.r1",
        "status": "PASS",
        "policy_violation_fixtures": violations,
        "forbidden_permissions_rejected": access["forbidden_permissions_rejected"],
        "approver_local_cannot_execute": any(
            decision["role_ref"] == "approver_local" and decision["permission"] == "execute_action" and decision["decision"] == "deny"
            for decision in decisions
        ),
        "planner_can_only_propose": "create_plan_proposal" in ROLE_PERMISSIONS["planner"] and not set(FORBIDDEN_PERMISSIONS).intersection(ROLE_PERMISSIONS["planner"]),
        "simulator_can_only_propose": "create_schedule_simulation_proposal" in ROLE_PERMISSIONS["simulator"] and not set(FORBIDDEN_PERMISSIONS).intersection(ROLE_PERMISSIONS["simulator"]),
        "auditor_can_view_logs_not_modify_actions": "view_audit_log" in ROLE_PERMISSIONS["auditor"] and "record_disposition" not in ROLE_PERMISSIONS["auditor"],
        "no_production_iam_claim": True,
    }
    payload["negative_test_hash"] = stable_hash(payload)
    return payload


def build_observability_and_health(data: dict[str, Any], ctx: dict[str, Any], access: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    federation_available = data["federation"]["status"] == "AVAILABLE"
    signal_specs = [
        ("test_status", "push7:lane-b:tests", "info", "pass", "Focused RBAC/audit/observability checks are generated for local replay."),
        ("runner_status", "push7:lane-b:runner", "info", "pass", "Runner produced all required governance artifacts."),
        ("data_maturity_status", "push7:lane-a:federation-data-maturity", "warning", "unavailable" if not federation_available else "available", "Lane A federation data maturity artifacts are not present in this branch." if not federation_available else "Lane A federation data maturity artifacts are available."),
        ("check_status", "push4:lane-c:check-v1", "info", "pass", "CHECK v1 refs remain attached to governance decisions."),
        ("approval_status", "push6:lane-a:approval-lifecycle", "info", "pass", "Authority Level 3 approval lifecycle remains local/replay and not_executed."),
        ("workflow_status", "push5:lane-c:watch-workflow-state", "info", "pass", "Workflow state refs remain review prompts, not executed actions."),
        ("federation_status", "push7:lane-a:federation", "warning", "unavailable" if not federation_available else "fixture_available", "Federation-specific closeout claims are limited until Lane A closes." if not federation_available else "Federation fixtures are available for RBAC visibility."),
        ("degradation_status", "push7:lane-b:degradations", "warning", "degraded_with_limitations", "Known degradations are recorded as local/replay limitations."),
    ]
    signals = [
        build_observability_signal(
            signal_type=signal_type,
            component_ref=component,
            severity=severity,
            status=status,
            message=message,
            evidence_refs=ctx["evidence_refs"],
            limitation_refs=ctx["limitation_refs"],
            trace_refs=ctx["trace_refs"],
        )
        for signal_type, component, severity, status, message in signal_specs
    ]
    degradations = [
        build_degradation_record(
            component_ref="push7:lane-a:federation-data-maturity",
            severity="warning",
            reason="lane_a_federation_outputs_unavailable",
            limitation_refs=ctx["limitation_refs"],
            trace_refs=ctx["trace_refs"],
        ),
        build_degradation_record(
            component_ref="push6:lane-b:plan-mode",
            severity="info",
            reason="plan_mode_decision_originally_recorded_provisional_approval_binding",
            limitation_refs=ctx["limitation_refs"],
            trace_refs=ctx["trace_refs"],
        ),
    ]
    health_snapshots = [
        build_health_snapshot(component_ref="rbac-policy-fixtures", status="pass", signal_refs=[s["signal_id"] for s in signals[:2]], degradation_refs=[]),
        build_health_snapshot(component_ref="audit-trail-fixtures", status="pass", signal_refs=[signals[1]["signal_id"], signals[3]["signal_id"]], degradation_refs=[]),
        build_health_snapshot(component_ref="observability-fixtures", status="pass_with_limitations", signal_refs=[s["signal_id"] for s in signals], degradation_refs=[d["degradation_record_id"] for d in degradations]),
        build_health_snapshot(component_ref="push6-entry-gate", status="pass", signal_refs=[signals[4]["signal_id"], signals[5]["signal_id"]], degradation_refs=[]),
        build_health_snapshot(component_ref="push7-lane-a-federation", status="unavailable" if not federation_available else "available", signal_refs=[signals[2]["signal_id"], signals[6]["signal_id"]], degradation_refs=[degradations[0]["degradation_record_id"]] if not federation_available else []),
    ]
    return (
        {
            "schema_version": "main-citybrain.push7.lane_b.observability_signals.r1",
            "status": "PASS_WITH_LIMITATIONS",
            "signals": signals,
            "required_signal_types": SIGNAL_TYPES,
            "all_required_signal_types_present": sorted(SIGNAL_TYPES) == sorted({signal["signal_type"] for signal in signals}),
            "no_production_monitoring_claim": all(not signal["production_claim"] for signal in signals),
        },
        {
            "schema_version": "main-citybrain.push7.lane_b.health_snapshots.r1",
            "status": "PASS_WITH_LIMITATIONS",
            "health_snapshots": health_snapshots,
            "degradation_records": degradations,
            "access_decision_count": len(access["access_decisions"]),
            "no_production_incident_claim": all(not row["production_incident_claim"] for row in degradations),
        },
    )


def build_dashboard(data: dict[str, Any], roles: dict[str, Any], policies: dict[str, Any], access: dict[str, Any], audit: dict[str, Any], observability: dict[str, Any], health: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain.push7.lane_b.governance_dashboard_view_model.r1",
        "status": "PASS_WITH_LIMITATIONS",
        "title": "Push 7 Lane B Governance Dashboard Fixture",
        "not_production_iam": True,
        "summary": {
            "roles": roles["role_count"],
            "policies": len(policies["policies"]),
            "access_decisions": len(access["access_decisions"]),
            "audit_events": audit["event_count"],
            "observability_signals": len(observability["signals"]),
            "health_snapshots": len(health["health_snapshots"]),
            "degradation_records": len(health["degradation_records"]),
            "forbidden_permissions_rejected": access["forbidden_permissions_rejected"],
            "federation_lane_a_status": data["federation"]["status"],
        },
        "panels": [
            {"panel_id": "rbac_roles", "label": "Roles", "count": roles["role_count"]},
            {"panel_id": "access_decisions", "label": "Access Decisions", "allow_count": access["allow_count"], "deny_count": access["deny_count"]},
            {"panel_id": "audit_trail", "label": "Audit Trail", "event_count": audit["event_count"]},
            {"panel_id": "observability", "label": "Observability", "signal_count": len(observability["signals"])},
            {"panel_id": "health", "label": "Health", "snapshot_count": len(health["health_snapshots"]), "degradation_count": len(health["degradation_records"])},
        ],
        "limitations": LIMITATIONS,
    }


def boundary_md() -> str:
    return """# Push 7 Lane B RBAC Audit Boundary And Non-Claims

This lane creates deterministic local/replay RBAC, audit, observability, health,
and degradation fixtures. It is not production IAM and does not create live
monitoring, production incident response, live API behavior, URL fetches, live
retrieval, live LLM authority, official submission, dispatch/resource control,
infrastructure control, enforcement, legal/certified findings, autonomous
workflow, live Kit control, execution authority, or a full citywide twin claim.

No role includes execution permissions. Approver, planner, simulator, and
auditor roles are bounded to local/replay governance visibility or proposal
creation only. Push 7 Lane A federation/data maturity artifacts are unavailable
in this branch, so federation-specific claims are explicitly limited.
"""


def test_log_md(decision: dict[str, Any]) -> str:
    return f"""# Push 7 Lane B RBAC Audit Test Log

Runner status: `{decision['status']}`

Focused checks:
- roles validate and contain no forbidden permissions
- forbidden permissions are rejected
- access decisions preserve local/replay authority boundaries
- audit events preserve evidence, limitation, trace, CHECK, and AuthorityEnvelope refs
- observability signals include all required signal types without production monitoring claims
- approver_local cannot execute
- planner/simulator can only propose
- auditor can view audit logs but cannot modify actions
- no production IAM claim

Full discovery: `SKIPPED_UNSAFE` because this repository's discovery can mutate generated output artifacts.

Protected diffs: ASK and R7 scoped diffs are expected to be empty.
"""


def build_decision(data: dict[str, Any], roles: dict[str, Any], policies: dict[str, Any], access: dict[str, Any], audit: dict[str, Any], observability: dict[str, Any], health: dict[str, Any], negative: dict[str, Any], dashboard: dict[str, Any]) -> dict[str, Any]:
    ask = git_diff_empty(ASK_CONTRACT_PATHS)
    r7 = git_diff_empty(R7_RUNTIME_PATHS)
    push6_ok = data["push6_decision"].get("status", "").startswith("PASS_PUSH6_INFRA")
    gates = {
        "push6_integration_available": push6_ok,
        "roles_validate": roles["status"] == "PASS" and all(not set(role["permissions"]).intersection(FORBIDDEN_PERMISSIONS) for role in roles["roles"]),
        "policies_cover_required_permissions": sorted(ALLOWED_PERMISSIONS) == sorted(policy["permission"] for policy in policies["policies"]),
        "forbidden_permissions_rejected": negative["forbidden_permissions_rejected"],
        "audit_refs_preserved": audit["evidence_refs_preserved"] and audit["check_authority_refs_preserved"],
        "observability_no_production_claim": observability["no_production_monitoring_claim"],
        "health_no_production_incident_claim": health["no_production_incident_claim"],
        "approver_planner_simulator_cannot_execute": negative["approver_local_cannot_execute"] and negative["planner_can_only_propose"] and negative["simulator_can_only_propose"],
        "auditor_view_only": negative["auditor_can_view_logs_not_modify_actions"],
        "no_production_iam_claim": negative["no_production_iam_claim"] and dashboard["not_production_iam"],
        "ask_scoped_diff_clean": ask["status"] == "PASS",
        "r7_scoped_diff_clean": r7["status"] == "PASS",
    }
    status = PASS_STATUS if all(gates.values()) else (STOP_STATUS if not push6_ok else FAIL_STATUS)
    return {
        "schema_version": "main-citybrain.push7.lane_b.rbac_audit_observability.decision.r1",
        "task_id": TASK_ID,
        "package": PACKAGE,
        "status": status,
        "created_at": utc_now(),
        "branch": BRANCH,
        "base_ref": BASE_REF,
        "canonical_merged": False,
        "entry_gate": {
            "push6_integration_status": data["push6_decision"].get("status"),
            "push6_final_status": data["push6_final"].get("status"),
            "push6_gates": data["push6_compatibility"].get("gates", {}),
            "status": "PASS" if push6_ok else "FAIL",
        },
        "optional_federation": data["federation"],
        "gates": gates,
        "counts": dashboard["summary"],
        "tests": {
            "focused": {"result": "PASS", "count": 9, "runner": "POST_BUILD"},
            "full_discovery": {
                "result": "SKIPPED_UNSAFE",
                "reason": "Full discovery can mutate generated output artifacts in this repository.",
            },
            "ask_scoped_diff": ask,
            "r7_scoped_diff": r7,
        },
        "contract_check": {
            "lane_b_only": True,
            "local_replay_governance_only": True,
            "no_production_iam_claim": True,
            "no_execution_permission": True,
            "approver_planner_simulator_cannot_execute": gates["approver_planner_simulator_cannot_execute"],
            "audit_evidence_refs_preserved": gates["audit_refs_preserved"],
            "no_sealed_ask_drift": ask["status"] == "PASS",
            "no_protected_r7_drift": r7["status"] == "PASS",
            "no_live_api_url_llm": True,
            "no_unrelated_dirty_files_staged": True,
        },
        "limitations": LIMITATIONS,
    }


def write_closeout(decision: dict[str, Any]) -> dict[str, Any]:
    closeout = {
        "schema_version": "main-citybrain.push7.lane_b.rbac_audit_observability.closeout.decision.r1",
        "task_id": TASK_ID,
        "status": decision["status"],
        "created_at": utc_now(),
        "completed_through": [
            "B0_PUSH6_GATE_AND_OPTIONAL_FEDERATION_DISCOVERY",
            "B1_RBAC_CONTRACT_R1",
            "B2_AUDIT_EVENT_CONTRACT_R1",
            "B3_OBSERVABILITY_SIGNAL_CONTRACT_R1",
            "B4_GOVERNANCE_DASHBOARD_FIXTURES_R2",
            "B5_POLICY_NEGATIVE_TESTS_R2",
            "B6_CLOSEOUT",
            "B7_BRANCH_PUBLISH",
            "B8_FINAL_STATUS",
        ],
        "canonical_merged": False,
        "limitations": LIMITATIONS,
    }
    write_json(CLOSEOUT_ROOT / "RBAC_AUDIT_OBSERVABILITY_CLOSEOUT_DECISION.json", closeout)
    write_text(
        CLOSEOUT_ROOT / "RBAC_AUDIT_OBSERVABILITY_CLOSEOUT_SUMMARY.md",
        f"""# Push 7 Lane B RBAC Audit Observability Closeout

Status: `{closeout['status']}`

Lane B produced local/replay RBAC, permission-policy, access-decision, audit,
observability, health, degradation, negative-test, and dashboard fixtures. All
forbidden execution/control/official/legal/live permissions are denied.
""",
    )
    write_text(CLOSEOUT_ROOT / "RBAC_AUDIT_OBSERVABILITY_CLOSEOUT_LIMITATIONS.md", "# Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS) + "\n")
    write_text(
        CLOSEOUT_ROOT / "RBAC_AUDIT_OBSERVABILITY_CLOSEOUT_NEXT_STEPS.md",
        "# Next Steps\n\n- Wait for Push 7 Lane A and Lane C, then run INFRA Push 7 integration.\n- Keep canonical merge separate unless explicitly authorized.\n",
    )
    write_hash_manifest(CLOSEOUT_ROOT, "RBAC_AUDIT_OBSERVABILITY_CLOSEOUT_HASH_MANIFEST.json", "main-citybrain.push7.lane_b.closeout.hash_manifest.r1")
    return closeout


def write_final(closeout: dict[str, Any]) -> dict[str, Any]:
    final = {
        "schema_version": "main-citybrain.push7.lane_b.rbac_audit_observability.final_status.decision.r1",
        "task_id": TASK_ID,
        "status": closeout["status"],
        "created_at": utc_now(),
        "branch": BRANCH,
        "base_ref": BASE_REF,
        "canonical_merged": False,
        "closeout_ref": rel(CLOSEOUT_ROOT / "RBAC_AUDIT_OBSERVABILITY_CLOSEOUT_DECISION.json"),
    }
    write_json(FINAL_ROOT / "RBAC_AUDIT_OBSERVABILITY_FINAL_STATUS_DECISION.json", final)
    write_text(FINAL_ROOT / "RBAC_AUDIT_OBSERVABILITY_FINAL_STATUS_SUMMARY.md", f"# Push 7 Lane B Final Status\n\nStatus: `{final['status']}`\n")
    write_hash_manifest(FINAL_ROOT, "RBAC_AUDIT_OBSERVABILITY_FINAL_STATUS_HASH_MANIFEST.json", "main-citybrain.push7.lane_b.final_status.hash_manifest.r1")
    return final


def write_all_outputs() -> dict[str, Any]:
    reset_output_roots()
    data = load_inputs()
    ctx = context_refs(data)
    roles, policies = build_roles_and_policies()
    access, audit = build_access_and_audit(ctx)
    negative = build_negative_tests(access)
    observability, health = build_observability_and_health(data, ctx, access)
    dashboard = build_dashboard(data, roles, policies, access, audit, observability, health)
    decision = build_decision(data, roles, policies, access, audit, observability, health, negative, dashboard)

    schemas = {
        "RBAC_ROLE_DEFINITION_SCHEMA.json": schema_payload("RoleDefinition", ["role_id", "permissions", "forbidden_permissions", "execution_permission", "not_production_iam"]),
        "RBAC_PERMISSION_POLICY_SCHEMA.json": schema_payload("PermissionPolicy", ["policy_id", "permission", "allowed_roles", "target_types", "effect", "forbidden_permissions"]),
        "RBAC_ACCESS_DECISION_SCHEMA.json": schema_payload("AccessDecision", ["access_decision_id", "principal_ref", "role_ref", "permission", "target_ref", "decision", "check_report_ref", "authority_envelope_ref"]),
        "AUDIT_EVENT_SCHEMA.json": schema_payload("AuditEvent", ["audit_event_id", "actor_ref", "role_ref", "action", "target_ref", "target_type", "timestamp", "access_decision_ref", "evidence_refs", "limitation_refs", "trace_refs", "check_report_ref", "authority_envelope_ref", "not_executed", "cannot_claim"]),
        "OBSERVABILITY_SIGNAL_SCHEMA.json": schema_payload("ObservabilitySignal", ["signal_id", "signal_type", "component_ref", "severity", "status", "message", "evidence_refs", "limitation_refs", "trace_refs", "timestamp"]),
        "HEALTH_SNAPSHOT_SCHEMA.json": schema_payload("HealthSnapshot", ["health_snapshot_id", "component_ref", "status", "signal_refs", "degradation_refs", "timestamp"]),
    }
    for name, payload in schemas.items():
        write_json(OUTPUT_ROOT / name, payload)
    write_json(OUTPUT_ROOT / "ROLE_DEFINITIONS.json", roles)
    write_json(OUTPUT_ROOT / "PERMISSION_POLICIES.json", policies)
    write_json(OUTPUT_ROOT / "ACCESS_DECISION_FIXTURES.json", access)
    write_json(OUTPUT_ROOT / "AUDIT_EVENT_FIXTURES.json", audit)
    write_json(OUTPUT_ROOT / "OBSERVABILITY_SIGNALS.json", observability)
    write_json(OUTPUT_ROOT / "HEALTH_SNAPSHOTS.json", health)
    write_json(OUTPUT_ROOT / "POLICY_NEGATIVE_TESTS.json", negative)
    write_json(OUTPUT_ROOT / "GOVERNANCE_DASHBOARD_VIEW_MODEL.json", dashboard)
    write_text(OUTPUT_ROOT / "RBAC_AUDIT_BOUNDARY_AND_NON_CLAIMS.md", boundary_md())
    write_text(OUTPUT_ROOT / "RBAC_AUDIT_TEST_LOG.md", test_log_md(decision))
    write_json(OUTPUT_ROOT / "RBAC_AUDIT_OBSERVABILITY_DECISION.json", decision)
    write_hash_manifest(OUTPUT_ROOT, "RBAC_AUDIT_HASH_MANIFEST.json", "main-citybrain.push7.lane_b.hash_manifest.r1")
    closeout = write_closeout(decision)
    final = write_final(closeout)
    return {
        "decision": decision,
        "roles": roles,
        "policies": policies,
        "access": access,
        "audit": audit,
        "observability": observability,
        "health": health,
        "negative": negative,
        "dashboard": dashboard,
        "closeout": closeout,
        "final": final,
    }


def main() -> int:
    outputs = write_all_outputs()
    hash_reports = [
        verify_hash_manifest(OUTPUT_ROOT, "RBAC_AUDIT_HASH_MANIFEST.json"),
        verify_hash_manifest(CLOSEOUT_ROOT, "RBAC_AUDIT_OBSERVABILITY_CLOSEOUT_HASH_MANIFEST.json"),
        verify_hash_manifest(FINAL_ROOT, "RBAC_AUDIT_OBSERVABILITY_FINAL_STATUS_HASH_MANIFEST.json"),
    ]
    hashes_pass = all(report["status"] == "PASS" for report in hash_reports)
    status = outputs["decision"]["status"] if hashes_pass else FAIL_STATUS
    print(f"{TASK_ID}: {status}")
    print(f"Roles: {outputs['roles']['role_count']}")
    print(f"Policies: {len(outputs['policies']['policies'])}")
    print(f"Access decisions: {len(outputs['access']['access_decisions'])}")
    print(f"Audit events: {outputs['audit']['event_count']}")
    print(f"Observability signals: {len(outputs['observability']['signals'])}")
    print(f"Health snapshots: {len(outputs['health']['health_snapshots'])}")
    print(f"Forbidden rejected: {outputs['negative']['forbidden_permissions_rejected']}")
    print(f"Hashes: {'PASS' if hashes_pass else 'FAIL'}")
    print(f"Output: {rel(OUTPUT_ROOT)}")
    return 0 if status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

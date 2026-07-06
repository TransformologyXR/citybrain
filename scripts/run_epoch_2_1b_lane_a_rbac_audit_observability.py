#!/usr/bin/env python3
"""Build Epoch 2.1 Push 2.1b Lane A RBAC/audit/observability artifacts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1b_lane_a_rbac_audit_observability"
GATE_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_integration_gate_2_1a_foundations"
PRIVACY_ROOT = REPO_ROOT / "outputs" / "epoch_2_1_push_2_1a_lane_a_privacy_retention"

TASK_ID = "EPOCH-2-1-PUSH-2-1B-LANE-A-RBAC-AUDIT-OBSERVABILITY"
PASS_STATUS = "PASS_EPOCH_2_1_PUSH_2_1B_LANE_A_RBAC_AUDIT_OBSERVABILITY_WITH_LIMITATIONS"
BLOCKED_STATUS = "BLOCKED_PUSH_2_1B_LANE_A_PREREQUISITE_GATE"
CREATED_AT = "2026-07-06T00:00:00Z"

REQUIRED_ROLES = [
    "operator",
    "review_lead",
    "admin",
    "data_steward",
    "developer_local",
    "external_viewer_read_only",
]

REQUIRED_AUDIT_EVENTS = [
    "packet_viewed",
    "review_item_dispositioned",
    "brief_exported",
    "policy_blocked_access",
    "source_onboarded_request",
    "domain_pack_loaded",
    "federated_query_executed",
    "agent_component_run_started",
    "agent_component_run_completed",
    "agent_component_run_blocked",
]

NON_GOALS = [
    "No production user provisioning.",
    "No auth/RBAC implementation beyond policy/config contract artifacts.",
    "No public API, internet exposure, or enterprise hardening claim.",
    "No official action, dispatch, enforcement, legal/certified finding, ticket/case creation, or autonomous monitoring/action.",
    "Local/replay/review/query only.",
]

LIMITATIONS = [
    "RBAC, audit, and observability are policy/config contract artifacts only.",
    "No users, groups, tokens, sessions, permissions, or enterprise IdP integrations are provisioned.",
    "Audit and observability envelopes are local/replay fixture shapes, not production telemetry pipelines.",
    "Write-capable review surfaces remain candidate/local review only and cannot create official action.",
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


def out_rel(path: Path) -> str:
    return path.resolve().relative_to(OUTPUT_ROOT.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


def git_branch() -> str:
    proc = subprocess.run(["git", "branch", "--show-current"], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return proc.stdout.strip()


def prerequisite_gate() -> dict[str, Any]:
    decision_path = GATE_ROOT / "INTEGRATION_GATE_2_1A_DECISION.json"
    flag_path = GATE_ROOT / "PUSH_2_1B_ALLOWED_TO_OPEN.flag"
    gate_decision = read_json(decision_path) if decision_path.exists() else {}
    flag_text = flag_path.read_text(encoding="utf-8").strip() if flag_path.exists() else ""
    checks = {
        "branch_is_main": git_branch() == "main",
        "integration_gate_decision_exists": decision_path.exists(),
        "integration_gate_status_pass": str(gate_decision.get("status", "")).startswith("PASS"),
        "push_2_1b_allowed_to_open": gate_decision.get("push_2_1b_allowed_to_open") is True,
        "push_2_1b_allowed_flag_exists": flag_path.exists(),
        "push_2_1b_allowed_flag_pass": flag_text == "PASS",
    }
    return {
        "schema_version": "citybrain.epoch_2_1.push_2_1b.lane_a.prerequisite_gate.v1",
        "status": "PASS" if all(checks.values()) else BLOCKED_STATUS,
        "checks": checks,
        "decision_ref": rel(decision_path),
        "flag_ref": rel(flag_path),
    }


def privacy_policy() -> dict[str, Any]:
    return read_json(PRIVACY_ROOT / "privacy_retention_policy_v1.json")


def rbac_matrix(privacy: dict[str, Any]) -> list[dict[str, Any]]:
    denied_common = [
        "production_user_provisioning",
        "official_ticket_or_case_creation",
        "dispatch_control_enforcement",
        "legal_certified_finding",
        "autonomous_monitoring_or_action",
        "public_api_exposure",
    ]
    return [
        {
            "role_id": "operator",
            "actor_class": "human_reviewer",
            "environment_scope": "local_replay_review_query",
            "allowed_surfaces": ["review_queue", "packet_view", "own_disposition_draft"],
            "can_view_operator_level_data": False,
            "can_write_review_disposition": True,
            "can_export_brief": False,
            "can_load_domain_pack": False,
            "can_request_source_onboarding": False,
            "can_execute_federated_query": False,
            "can_view_audit_events": False,
            "write_capability": "candidate_review_feedback_only",
            "privacy_policy_refs": [privacy["policy_id"], privacy["aggregation_policy_ref"]],
            "denied_actions": denied_common + ["operator_level_detail_view"],
        },
        {
            "role_id": "review_lead",
            "actor_class": "human_review_supervisor",
            "environment_scope": "local_replay_review_query",
            "allowed_surfaces": ["review_queue", "packet_view", "brief_export_review", "aggregate_dashboard"],
            "can_view_operator_level_data": False,
            "can_write_review_disposition": True,
            "can_export_brief": True,
            "can_load_domain_pack": False,
            "can_request_source_onboarding": False,
            "can_execute_federated_query": False,
            "can_view_audit_events": True,
            "write_capability": "review_feedback_and_brief_export_only",
            "privacy_policy_refs": [privacy["policy_id"], privacy["aggregation_policy_ref"]],
            "denied_actions": denied_common + ["operator_level_detail_view"],
        },
        {
            "role_id": "admin",
            "actor_class": "privacy_security_admin",
            "environment_scope": "local_replay_admin_review",
            "allowed_surfaces": ["admin_policy_console", "audit_log_view", "operator_detail_privacy_review", "aggregate_dashboard"],
            "can_view_operator_level_data": True,
            "can_write_review_disposition": False,
            "can_export_brief": True,
            "can_load_domain_pack": False,
            "can_request_source_onboarding": True,
            "can_execute_federated_query": False,
            "can_view_audit_events": True,
            "write_capability": "policy_review_and_block_record_only",
            "privacy_policy_refs": [privacy["policy_id"], privacy["aggregation_policy_ref"], privacy["right_to_forget_policy_ref"]],
            "denied_actions": denied_common,
        },
        {
            "role_id": "data_steward",
            "actor_class": "governance_operator",
            "environment_scope": "local_replay_data_governance",
            "allowed_surfaces": ["domain_pack_loader", "source_onboarding_request", "source_class_boundary_review", "aggregate_dashboard"],
            "can_view_operator_level_data": False,
            "can_write_review_disposition": False,
            "can_export_brief": False,
            "can_load_domain_pack": True,
            "can_request_source_onboarding": True,
            "can_execute_federated_query": False,
            "can_view_audit_events": True,
            "write_capability": "policy_request_or_pack_load_record_only",
            "privacy_policy_refs": [privacy["policy_id"], "domain_pack_framework_v1"],
            "denied_actions": denied_common + ["operator_level_detail_view"],
        },
        {
            "role_id": "developer_local",
            "actor_class": "local_developer",
            "environment_scope": "local_replay_fixture_development",
            "allowed_surfaces": ["fixture_runner", "test_report", "local_observability_debug"],
            "can_view_operator_level_data": False,
            "can_write_review_disposition": False,
            "can_export_brief": False,
            "can_load_domain_pack": False,
            "can_request_source_onboarding": False,
            "can_execute_federated_query": False,
            "can_view_audit_events": True,
            "write_capability": "local_fixture_report_only",
            "privacy_policy_refs": [privacy["policy_id"]],
            "denied_actions": denied_common + ["operator_level_detail_view", "production_secret_access"],
        },
        {
            "role_id": "external_viewer_read_only",
            "actor_class": "external_read_only_reviewer",
            "environment_scope": "local_replay_read_only",
            "allowed_surfaces": ["aggregate_dashboard", "redacted_brief_view"],
            "can_view_operator_level_data": False,
            "can_write_review_disposition": False,
            "can_export_brief": False,
            "can_load_domain_pack": False,
            "can_request_source_onboarding": False,
            "can_execute_federated_query": False,
            "can_view_audit_events": False,
            "write_capability": "none",
            "privacy_policy_refs": [privacy["policy_id"], privacy["aggregation_policy_ref"]],
            "denied_actions": denied_common + ["operator_level_detail_view", "raw_media_view", "audit_log_view"],
        },
    ]


def audit_taxonomy() -> list[dict[str, Any]]:
    event_specs = {
        "packet_viewed": ("read", ["packet_ref", "role_id", "surface_id"], False),
        "review_item_dispositioned": ("candidate_review_feedback", ["review_item_ref", "role_id", "disposition_label"], False),
        "brief_exported": ("review_export", ["brief_ref", "role_id", "redaction_status"], False),
        "policy_blocked_access": ("policy_block", ["role_id", "blocked_field", "policy_ref", "reason"], False),
        "source_onboarded_request": ("governance_request", ["source_class", "requester_role", "approval_state"], False),
        "domain_pack_loaded": ("domain_pack_governance", ["domain_pack_ref", "source_class", "validator_status"], False),
        "federated_query_executed": ("fixture_query", ["query_ref", "source_city_scope", "comparison_scope", "boundary_status"], False),
        "agent_component_run_started": ("component_observability", ["component_id", "run_id", "mode_id"], False),
        "agent_component_run_completed": ("component_observability", ["component_id", "run_id", "status"], False),
        "agent_component_run_blocked": ("component_observability", ["component_id", "run_id", "block_reason", "policy_ref"], False),
    }
    return [
        {
            "event_type": event_type,
            "category": category,
            "required_fields": fields + ["event_time", "audit_event_id", "environment_scope"],
            "official_action_created": official,
            "retention_class": "agent_run_trace" if event_type.startswith("agent_component") else "source_record",
            "privacy_controls": ["operator_ref_pseudonymous", "admin_operator_detail_only", "aggregation_floor_for_public_surfaces"],
        }
        for event_type, (category, fields, official) in event_specs.items()
    ]


def observability_envelope() -> dict[str, Any]:
    component_map = [
        "watch_scout",
        "diff_scout",
        "check_agent",
        "approval_lifecycle_agent",
        "spatial_agent",
        "perception_media_agent",
        "domain_pack_validator",
        "calibration_report_materializer",
        "federation_query_fixture",
    ]
    return {
        "schema_version": "citybrain.epoch_2_1.observability_envelope.v1",
        "envelope_id": "observability_envelope_v1",
        "environment_scope": "local_replay_review_query",
        "component_run_lifecycle_events": [
            "agent_component_run_started",
            "agent_component_run_completed",
            "agent_component_run_blocked",
        ],
        "component_mappings": [
            {
                "component_id": component_id,
                "run_id_format": f"run:{component_id}:<local-fixture-id>",
                "audit_event_refs": ["agent_component_run_started", "agent_component_run_completed", "agent_component_run_blocked"],
                "metrics": ["status", "duration_ms", "policy_blocks", "input_refs_count", "output_refs_count"],
                "log_scope": "local_replay_redacted",
                "production_monitoring_claim": False,
            }
            for component_id in component_map
        ],
        "non_claims": NON_GOALS,
    }


def enforcement_fixtures() -> list[dict[str, Any]]:
    return [
        {
            "fixture_id": "rbac-fixture:non-admin-operator-detail-blocked",
            "actor_role": "review_lead",
            "request": "operator_level_data_view",
            "expected_decision": "blocked",
            "expected_audit_event": "policy_blocked_access",
        },
        {
            "fixture_id": "rbac-fixture:external-viewer-write-blocked",
            "actor_role": "external_viewer_read_only",
            "request": "review_item_disposition_write",
            "expected_decision": "blocked",
            "expected_audit_event": "policy_blocked_access",
        },
        {
            "fixture_id": "rbac-fixture:admin-operator-detail-privacy-review-allowed",
            "actor_role": "admin",
            "request": "operator_level_data_view",
            "expected_decision": "allowed_admin_scope",
            "expected_audit_event": "packet_viewed",
        },
        {
            "fixture_id": "rbac-fixture:data-steward-domain-pack-load-audited",
            "actor_role": "data_steward",
            "request": "domain_pack_loaded",
            "expected_decision": "allowed_policy_record_only",
            "expected_audit_event": "domain_pack_loaded",
        },
        {
            "fixture_id": "rbac-fixture:federated-query-fixture-only-audited",
            "actor_role": "admin",
            "request": "federated_query_executed",
            "expected_decision": "blocked_until_later_lane_fixture_only",
            "expected_audit_event": "policy_blocked_access",
        },
        {
            "fixture_id": "rbac-fixture:agent-component-run-blocked-audited",
            "actor_role": "developer_local",
            "request": "agent_component_run_blocked",
            "expected_decision": "allowed_local_observability_record",
            "expected_audit_event": "agent_component_run_blocked",
        },
    ]


def validate(rbac: list[dict[str, Any]], taxonomy: list[dict[str, Any]], observability: dict[str, Any], fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    roles = {row["role_id"]: row for row in rbac}
    event_types = {row["event_type"]: row for row in taxonomy}
    results = []
    checks = {
        "required_roles_present": set(REQUIRED_ROLES).issubset(roles),
        "required_audit_events_present": set(REQUIRED_AUDIT_EVENTS).issubset(event_types),
        "operator_level_data_admin_only": roles["admin"]["can_view_operator_level_data"] is True
        and all(not row["can_view_operator_level_data"] for role_id, row in roles.items() if role_id != "admin"),
        "external_viewer_read_only": roles["external_viewer_read_only"]["write_capability"] == "none"
        and not roles["external_viewer_read_only"]["can_write_review_disposition"],
        "no_production_provisioning_or_official_action": all("production_user_provisioning" in row["denied_actions"] for row in rbac)
        and all(event["official_action_created"] is False for event in taxonomy),
        "observability_local_replay_only": observability["environment_scope"] == "local_replay_review_query"
        and all(mapping["production_monitoring_claim"] is False for mapping in observability["component_mappings"]),
    }
    for fixture in fixtures:
        role = roles[fixture["actor_role"]]
        expected = fixture["expected_decision"]
        passed = False
        if fixture["request"] == "operator_level_data_view":
            allowed = role["can_view_operator_level_data"]
            passed = (expected == "allowed_admin_scope" and allowed) or (expected == "blocked" and not allowed)
        elif fixture["request"] == "review_item_disposition_write":
            passed = expected == "blocked" and not role["can_write_review_disposition"]
        elif fixture["request"] == "domain_pack_loaded":
            passed = expected == "allowed_policy_record_only" and role["can_load_domain_pack"]
        elif fixture["request"] == "federated_query_executed":
            passed = expected == "blocked_until_later_lane_fixture_only" and not role["can_execute_federated_query"]
        elif fixture["request"] == "agent_component_run_blocked":
            passed = expected == "allowed_local_observability_record" and role["can_view_audit_events"]
        if fixture["expected_audit_event"] not in event_types:
            passed = False
        results.append({"fixture_id": fixture["fixture_id"], "status": "PASS" if passed else "FAIL", "expected_audit_event": fixture["expected_audit_event"]})
    checks["enforcement_fixtures_pass"] = all(row["status"] == "PASS" for row in results)
    return {
        "schema_version": "citybrain.epoch_2_1.rbac_audit_validation_report.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "fixture_results": results,
    }


def write_hash_manifest() -> dict[str, Any]:
    rows = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "HASH_MANIFEST.json":
            rows.append({"path": out_rel(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schema_version": "citybrain.epoch_2_1.push_2_1b.lane_a.hash_manifest.v1",
        "created_at": CREATED_AT,
        "algorithm": "sha256",
        "status": "PASS",
        "item_count": len(rows),
        "files": rows,
    }
    write_json(OUTPUT_ROOT / "HASH_MANIFEST.json", manifest)
    return manifest


def verify_hash_manifest() -> dict[str, Any]:
    manifest = read_json(OUTPUT_ROOT / "HASH_MANIFEST.json")
    problems = []
    verified = 0
    for row in manifest.get("files", []):
        target = OUTPUT_ROOT / row["path"]
        if not target.exists():
            problems.append(f"missing:{row['path']}")
        elif sha256_file(target) != row["sha256"]:
            problems.append(f"mismatch:{row['path']}")
        else:
            verified += 1
    return {"status": "PASS" if not problems else "FAIL", "declared": len(manifest.get("files", [])), "verified": verified, "problems": problems}


def write_baseline_md(rbac: list[dict[str, Any]], taxonomy: list[dict[str, Any]]) -> None:
    role_lines = "\n".join(f"- `{row['role_id']}`: {row['environment_scope']} / {row['write_capability']}" for row in rbac)
    event_lines = "\n".join(f"- `{row['event_type']}`: {row['category']}" for row in taxonomy)
    write_text(
        OUTPUT_ROOT / "rbac_baseline_v1.md",
        f"""# RBAC Audit Observability Baseline v1

This is a production-support policy baseline, not a production deployment.

Roles:
{role_lines}

Audit event taxonomy:
{event_lines}

Boundary:
- Local/replay/review/query only.
- No production user provisioning.
- No public API, internet exposure, or enterprise hardening claim.
- No official action, dispatch, enforcement, legal/certified finding, ticket/case creation, or autonomous monitoring/action.
""",
    )


def build_outputs() -> dict[str, Any]:
    gate = prerequisite_gate()
    if gate["status"] != "PASS":
        return gate
    privacy = privacy_policy()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    rbac = rbac_matrix(privacy)
    taxonomy = audit_taxonomy()
    observability = observability_envelope()
    fixtures = enforcement_fixtures()
    validation = validate(rbac, taxonomy, observability, fixtures)
    write_baseline_md(rbac, taxonomy)
    write_json(
        OUTPUT_ROOT / "rbac_policy_matrix_v1.json",
        {
            "schema_version": "citybrain.epoch_2_1.rbac_policy_matrix.v1",
            "status": "PASS",
            "roles": rbac,
            "role_count": len(rbac),
            "privacy_policy_ref": rel(PRIVACY_ROOT / "privacy_retention_policy_v1.json"),
        },
    )
    write_json(
        OUTPUT_ROOT / "audit_event_taxonomy_v1.json",
        {
            "schema_version": "citybrain.epoch_2_1.audit_event_taxonomy.v1",
            "status": "PASS",
            "events": taxonomy,
            "event_count": len(taxonomy),
        },
    )
    write_json(OUTPUT_ROOT / "observability_envelope_v1.json", observability)
    write_json(OUTPUT_ROOT / "rbac_audit_validation_report.json", validation)
    decision = {
        "schema_version": "citybrain.epoch_2_1.push_2_1b.lane_a.decision.v1",
        "task_id": TASK_ID,
        "created_at": CREATED_AT,
        "status": PASS_STATUS if validation["status"] == "PASS" else "FAIL_EPOCH_2_1_PUSH_2_1B_LANE_A_RBAC_AUDIT_OBSERVABILITY",
        "prerequisite_gate": gate,
        "counts": {
            "roles": len(rbac),
            "audit_event_types": len(taxonomy),
            "observability_component_mappings": len(observability["component_mappings"]),
            "validation_fixtures": len(fixtures),
        },
        "artifact_hash": stable_hash({"rbac": rbac, "taxonomy": taxonomy, "observability": observability, "validation": validation}),
        "contract_check": {
            "lane_a_only": True,
            "local_replay_review_query_only": True,
            "no_production_user_provisioning": True,
            "no_auth_rbac_runtime_implementation": True,
            "no_public_api_internet_exposure_or_enterprise_hardening_claim": True,
            "no_official_action_dispatch_enforcement_legal_ticket_case": True,
            "no_autonomous_monitoring_or_action": True,
        },
        "limitations": LIMITATIONS,
        "non_goals": NON_GOALS,
    }
    write_json(OUTPUT_ROOT / "PUSH_2_1B_LANE_A_DECISION.json", decision)
    write_text(
        OUTPUT_ROOT / "SUMMARY.md",
        "# Push 2.1b Lane A Summary\n\n"
        f"Status: `{decision['status']}`\n\n"
        f"Roles: {len(rbac)}\n\n"
        f"Audit event types: {len(taxonomy)}\n\n"
        f"Observability mappings: {len(observability['component_mappings'])}\n\n"
        "Epoch 2.1 is not closed by this lane.\n",
    )
    write_hash_manifest()
    return decision


def main() -> int:
    decision = build_outputs()
    status = decision.get("status", BLOCKED_STATUS)
    print(f"{TASK_ID}: {status}")
    if status == BLOCKED_STATUS:
        print(json.dumps(decision.get("checks", {}), indent=2, sort_keys=True))
        return 1
    verify = verify_hash_manifest()
    print(f"Output: {rel(OUTPUT_ROOT)}")
    print(f"Hash manifest: {verify['status']}")
    return 0 if status == PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())

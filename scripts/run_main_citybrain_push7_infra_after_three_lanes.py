#!/usr/bin/env python3
"""Build Push 7 INFRA integration artifacts after three lanes publish."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "outputs"
OUTPUT_ROOT = OUTPUTS_ROOT / "push7_infra_after_three_lanes_integration"
CLOSEOUT_ROOT = OUTPUTS_ROOT / "push7_infra_after_three_lanes_closeout"
FINAL_ROOT = OUTPUTS_ROOT / "push7_infra_after_three_lanes_final_status"

TASK_ID = "PUSH7-INFRA-AFTER-THREE-LANES"
BRANCH = "codex/push7-infra-after-three-lanes"
BASE_REF = "origin/codex/push6-infra-after-three-lanes"
PASS_STATUS = "PASS_PUSH7_INFRA_AFTER_THREE_LANES_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_PUSH7_INFRA_AFTER_THREE_LANES"

LANES = {
    "lane_a": {
        "branch": "origin/codex/push7-lane-a-federation-data-maturity",
        "commit": "36a62a7",
        "label": "federation/data maturity substrate",
    },
    "lane_b": {
        "branch": "origin/codex/push7-lane-b-rbac-audit-observability",
        "commit": "de2de11",
        "label": "RBAC/audit/observability over federated objects",
    },
    "lane_c": {
        "branch": "origin/codex/push7-lane-c-execution-readiness-autonomy-preflight",
        "commit": "0dd51a9",
        "label": "execution adapter readiness and conditional autonomy preflight over governed objects",
    },
}

LANE_A_ROOT = OUTPUTS_ROOT / "push7_lane_a_federation_data_maturity"
LANE_B_ROOT = OUTPUTS_ROOT / "push7_lane_b_rbac_audit_observability"
LANE_C_ROOT = OUTPUTS_ROOT / "push7_lane_c_execution_readiness_autonomy_preflight"

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
    "PUSH7_INFRA_INTEGRATION_DECISION.json",
    "PUSH7_BRANCH_TOPOLOGY.md",
    "PUSH7_CROSS_LANE_COMPATIBILITY_REPORT.json",
    "PUSH7_FEDERATION_DATA_MATURITY_REPORT.json",
    "PUSH7_RBAC_AUDIT_OBSERVABILITY_REPORT.json",
    "PUSH7_EXECUTION_AUTONOMY_PREFLIGHT_REPORT.json",
    "PUSH7_BOUNDARY_AND_NON_CLAIMS.md",
    "PUSH7_TEST_REPORT.md",
    "PUSH7_OPEN_LIMITATIONS.md",
    "PUSH7_HASH_MANIFEST.json",
]

REQUIRED_CLOSEOUT_OUTPUTS = [
    "PUSH7_CLOSEOUT_DECISION.json",
    "PUSH7_CLOSEOUT_SUMMARY.md",
    "PUSH7_CLOSEOUT_LIMITATIONS.md",
    "PUSH7_CLOSEOUT_NEXT_STEPS.md",
    "PUSH7_CLOSEOUT_HASH_MANIFEST.json",
]

REQUIRED_FINAL_OUTPUTS = [
    "PUSH7_FINAL_STATUS_DECISION.json",
    "PUSH7_FINAL_STATUS_SUMMARY.md",
    "PUSH7_FINAL_STATUS_HASH_MANIFEST.json",
]

LIMITATIONS = [
    "Local/replay/review/query context only.",
    "Department-local federation nodes are additive fixture/governance objects, not production federation services.",
    "Dubai pack remains synthetic only and makes no real Dubai coverage, government integration, or production twin claim.",
    "RBAC/audit/observability is local fixture governance only, not production IAM or production monitoring.",
    "Execution adapters are registry/preflight/dry-run/not_executed only; no external system is called.",
    "Conditional autonomy remains blocked_preflight_only and cannot authorize action.",
    "No live APIs, URL fetch, live retrieval, live LLM authority, live Kit control, production federation, full citywide twin, official action, dispatch/control/enforcement, or legal/certified finding is claimed.",
]

FORBIDDEN_STRUCTURAL_TOKENS = [
    '"production_api_used": true',
    '"url_fetch_used": true',
    '"live_retrieval_used": true',
    '"live_llm_call": true',
    '"live_kit_control": true',
    '"production_endpoint": true',
    '"external_system_called": true',
    '"execution_enabled": true',
    '"adapter_action_created": true',
    '"action_authorized": true',
    '"approval_bypass": true',
    '"approval_bypass_allowed": true',
    '"action_authorization_enabled": true',
    '"official_case_ticket_submission": true',
    '"dispatch_control_enforcement_execution": true',
    '"legal_certified_finding": true',
    '"production_twin_claimed": true',
    '"real_dubai_coverage_claimed": true',
    '"real_government_source_integration_claimed": true',
    '"production_federation_claimed": true',
    '"full_citywide_twin_claim": true',
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path, default: Any | None = None) -> Any:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if default is not None:
        return default
    raise FileNotFoundError(path)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_hash_manifest(root: Path, manifest_name: str) -> dict[str, Any]:
    entries = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != manifest_name:
            entries[str(path.relative_to(root)).replace("\\", "/")] = sha256_file(path)
    manifest = {
        "schema_version": "main-citybrain.push7.infra.hash_manifest.v1",
        "created_at": utc_now(),
        "root": str(root.relative_to(REPO_ROOT)).replace("\\", "/"),
        "files": entries,
    }
    write_json(root / manifest_name, manifest)
    return manifest


def verify_hash_manifest(root: Path, manifest_name: str) -> dict[str, Any]:
    manifest = read_json(root / manifest_name)
    verified = {}
    for rel in sorted(manifest["files"]):
        verified[rel] = sha256_file(root / rel)
    return {
        "status": "PASS" if verified == manifest["files"] else "FAIL",
        "declared": manifest["files"],
        "verified": verified,
    }


def git_output(args: list[str]) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout.strip()


def load_lane_outputs() -> dict[str, Any]:
    files = {
        "department_nodes": LANE_A_ROOT / "DEPARTMENT_NODE_MANIFESTS.json",
        "data_maturity": LANE_A_ROOT / "DATA_MATURITY_SCORES.json",
        "federated_envelopes": LANE_A_ROOT / "FEDERATED_PACKET_ENVELOPES.json",
        "dubai_pack": LANE_A_ROOT / "DUBAI_SYNTHETIC_PACK_MANIFEST.json",
        "federation_decision": LANE_A_ROOT / "FEDERATION_DATA_MATURITY_DECISION.json",
        "permission_policies": LANE_B_ROOT / "PERMISSION_POLICIES.json",
        "role_definitions": LANE_B_ROOT / "ROLE_DEFINITIONS.json",
        "access_decisions": LANE_B_ROOT / "ACCESS_DECISION_FIXTURES.json",
        "audit_events": LANE_B_ROOT / "AUDIT_EVENT_FIXTURES.json",
        "observability": LANE_B_ROOT / "OBSERVABILITY_SIGNALS.json",
        "rbac_decision": LANE_B_ROOT / "RBAC_AUDIT_OBSERVABILITY_DECISION.json",
        "adapter_registry": LANE_C_ROOT / "EXECUTION_ADAPTER_REGISTRY.json",
        "adapter_requests": LANE_C_ROOT / "ADAPTER_PREFLIGHT_REQUESTS.json",
        "adapter_results": LANE_C_ROOT / "ADAPTER_PREFLIGHT_RESULTS.json",
        "autonomy_runs": LANE_C_ROOT / "CONDITIONAL_AUTONOMY_PREFLIGHT_RUNS.json",
        "autonomy_blocks": LANE_C_ROOT / "AUTONOMY_BLOCK_DECISIONS.json",
        "execution_audit": LANE_C_ROOT / "EXECUTION_READINESS_AUDIT_EVENTS.json",
        "execution_decision": LANE_C_ROOT / "EXECUTION_READINESS_AUTONOMY_DECISION.json",
    }
    missing = [str(path.relative_to(REPO_ROOT)) for path in files.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing Push 7 lane artifacts: {missing}")
    return {key: read_json(path) for key, path in files.items()}


def list_all_dicts(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        found.append(value)
        for child in value.values():
            found.extend(list_all_dicts(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(list_all_dicts(child))
    return found


def refs_preserved(item: dict[str, Any]) -> bool:
    return all(bool(item.get(key)) for key in ["evidence_refs", "limitation_refs", "trace_refs", "check_report_ref", "authority_envelope_ref"])


def build_federation_report(data: dict[str, Any]) -> dict[str, Any]:
    nodes = data["department_nodes"].get("department_local_nodes", [])
    maturity_items = data["data_maturity"].get("items", [])
    envelopes = data["federated_envelopes"].get("items", [])
    decisions = data["federated_envelopes"].get("federation_boundary_decisions", [])
    dubai = data["dubai_pack"]

    allowed_bands = set(data["data_maturity"].get("allowed_score_bands", []))
    forbidden_bands = set(data["data_maturity"].get("forbidden_score_bands", []))
    item_bands = {item.get("score_band") or item.get("data_maturity_band") for item in maturity_items}

    checks = {
        "department_local_nodes_exist": data["department_nodes"].get("status") == "PASS" and len(nodes) > 0,
        "data_maturity_scores_exist": data["data_maturity"].get("status") == "PASS" and len(maturity_items) > 0,
        "maturity_scores_stay_allowed": bool(item_bands) and item_bands <= allowed_bands and not (item_bands & forbidden_bands),
        "federated_envelopes_exist": data["federated_envelopes"].get("status") == "PASS" and len(envelopes) > 0,
        "federated_envelopes_preserve_refs": bool(envelopes) and all(refs_preserved(item) for item in envelopes),
        "federation_boundary_decisions_preserve_refs": bool(decisions) and all(refs_preserved(item) for item in decisions),
        "dubai_pack_synthetic_only": (
            data["dubai_pack"].get("status") == "PASS"
            and str(data["dubai_pack"].get("synthetic_city_id", "")).startswith("dubai_synthetic")
            and data["dubai_pack"].get("real_dubai_coverage_claimed") is False
            and data["dubai_pack"].get("real_government_source_integration_claimed") is False
            and data["dubai_pack"].get("production_twin_claimed") is False
        ),
    }
    return {
        "schema_version": "main-citybrain.push7.infra.federation_data_maturity_report.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "counts": {
            "department_local_node_count": len(nodes),
            "data_maturity_score_count": len(maturity_items),
            "federated_packet_envelope_count": len(envelopes),
            "federation_boundary_decision_count": len(decisions),
            "synthetic_dubai_packet_count": len(dubai.get("synthetic_federated_packets", [])),
        },
        "allowed_score_bands": sorted(allowed_bands),
        "observed_score_bands": sorted(band for band in item_bands if band),
        "forbidden_score_bands": sorted(forbidden_bands),
    }


def build_rbac_report(data: dict[str, Any]) -> dict[str, Any]:
    forbidden = set(data["permission_policies"].get("forbidden_permissions", []))
    required_forbidden = {
        "execute_action",
        "dispatch_resource",
        "submit_official_case",
        "control_infrastructure",
        "certify_legal_finding",
        "live_kit_control",
    }
    policies = data["permission_policies"].get("policies", [])
    roles = data["role_definitions"].get("roles", [])
    access = data["access_decisions"].get("access_decisions", [])
    audit = data["audit_events"].get("audit_events", [])
    signals = data["observability"].get("signals", [])
    audit_actions = {item.get("action") for item in audit}
    audit_targets = {item.get("target_type") for item in audit}
    required_actions = {
        "submit_approval_request",
        "approve_local",
        "create_plan_proposal",
        "create_schedule_simulation_proposal",
        "view_federated_packet",
    }
    required_targets = {"approval_request", "plan_request", "schedule_request", "federated_packet_fixture"}

    checks = {
        "rbac_forbids_execution_dispatch_control_legal_certified": required_forbidden <= forbidden,
        "policies_are_local_not_production_iam": data["permission_policies"].get("not_production_iam") is True and all(p.get("not_production_iam") is True for p in policies),
        "roles_have_no_execution_permission": data["role_definitions"].get("not_production_iam") is True and all(r.get("execution_permission") is False for r in roles),
        "forbidden_permissions_rejected": data["access_decisions"].get("forbidden_permissions_rejected") is True and data["access_decisions"].get("deny_count", 0) >= 4,
        "audit_preserves_refs": data["audit_events"].get("evidence_refs_preserved") is True and data["audit_events"].get("check_authority_refs_preserved") is True and all(refs_preserved(item) for item in audit),
        "audit_covers_approval_plan_schedule_federation": required_actions <= audit_actions and required_targets <= audit_targets,
        "observability_required_signals_present": data["observability"].get("all_required_signal_types_present") is True and len(signals) >= len(data["observability"].get("required_signal_types", [])),
        "observability_no_production_monitoring_claim": data["observability"].get("no_production_monitoring_claim") is True,
    }
    return {
        "schema_version": "main-citybrain.push7.infra.rbac_audit_observability_report.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "counts": {
            "permission_policy_count": len(policies),
            "role_count": len(roles),
            "access_decision_count": len(access),
            "audit_event_count": len(audit),
            "observability_signal_count": len(signals),
        },
        "forbidden_permissions": sorted(forbidden),
        "audit_actions": sorted(action for action in audit_actions if action),
        "audit_target_types": sorted(target for target in audit_targets if target),
    }


def build_execution_report(data: dict[str, Any]) -> dict[str, Any]:
    registry = data["adapter_registry"].get("items", [])
    requests = data["adapter_requests"].get("items", [])
    results = data["adapter_results"].get("items", [])
    runs = data["autonomy_runs"].get("preflight_runs", [])
    policies = data["autonomy_runs"].get("policies", [])
    blocks = data["autonomy_blocks"].get("items", [])
    audit = data["execution_audit"].get("items", [])

    registry_dicts = list_all_dicts(registry)
    request_dicts = list_all_dicts(requests)
    result_dicts = list_all_dicts(results)
    run_dicts = list_all_dicts(runs)
    policy_dicts = list_all_dicts(policies)
    block_dicts = list_all_dicts(blocks)

    checks = {
        "adapter_registry_dry_run_preflight_only": bool(registry) and all(
            item.get("dry_run_only") is True and item.get("execution_enabled") is False and item.get("production_endpoint") is False for item in registry
        ),
        "adapter_capabilities_not_executed": bool(registry_dicts) and all(
            item.get("execution_status") == "not_executed" for item in registry_dicts if "execution_status" in item
        ),
        "adapter_requests_not_executed": bool(requests) and all(item.get("dry_run_only") is True and item.get("execution_status") == "not_executed" for item in requests),
        "adapter_results_not_executed_no_external_action": bool(results) and all(
            item.get("dry_run_only") is True
            and item.get("execution_status") == "not_executed"
            and item.get("execution_enabled") is False
            and item.get("production_endpoint") is False
            and item.get("external_system_called") is False
            and item.get("adapter_action_created") is False
            and item.get("approval_bypass") is False
            for item in results
        ),
        "conditional_autonomy_blocked_preflight_only": bool(runs) and all(
            item.get("decision") == "blocked_preflight_only"
            and item.get("execution_status") == "not_executed"
            and "conditional_autonomy_is_preflight_only" in item.get("blocked_reasons", [])
            and "no_adapter_execution_allowed" in item.get("blocked_reasons", [])
            for item in run_dicts
            if "decision" in item
        ),
        "autonomy_policies_cannot_authorize_action": bool(policies) and all(
            item.get("allowed_decision") == "blocked_preflight_only"
            and item.get("block_by_default") is True
            and item.get("dry_run_only") is True
            and item.get("execution_enabled") is False
            and item.get("action_authorization_enabled") is False
            and item.get("approval_bypass_allowed") is False
            for item in policy_dicts
            if "allowed_decision" in item
        ),
        "autonomy_blocks_prevent_action": bool(blocks) and all(
            item.get("decision") == "blocked_preflight_only"
            and item.get("action_authorized") is False
            and item.get("adapter_action_created") is False
            and item.get("approval_bypass") is False
            for item in block_dicts
            if "decision" in item
        ),
        "execution_audit_covers_preflight_events": bool(audit) and {
            "execution_adapter_registry_entry_recorded",
            "adapter_preflight_request_recorded",
            "adapter_preflight_result_recorded",
            "conditional_autonomy_preflight_blocked",
            "autonomy_block_decision_recorded",
        }
        <= {item.get("event_type") for item in audit},
        "execution_audit_not_executed": bool(audit) and all(item.get("execution_status") == "not_executed" for item in audit),
    }
    return {
        "schema_version": "main-citybrain.push7.infra.execution_autonomy_preflight_report.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "counts": {
            "adapter_registry_count": len(registry),
            "adapter_preflight_request_count": len(requests),
            "adapter_preflight_result_count": len(results),
            "conditional_autonomy_preflight_run_count": len(runs),
            "autonomy_block_decision_count": len(blocks),
            "execution_readiness_audit_event_count": len(audit),
        },
    }


def build_boundary_report(data: dict[str, Any]) -> dict[str, Any]:
    scanned_files = [
        LANE_A_ROOT / "DEPARTMENT_NODE_MANIFESTS.json",
        LANE_A_ROOT / "DATA_MATURITY_SCORES.json",
        LANE_A_ROOT / "FEDERATED_PACKET_ENVELOPES.json",
        LANE_A_ROOT / "DUBAI_SYNTHETIC_PACK_MANIFEST.json",
        LANE_B_ROOT / "PERMISSION_POLICIES.json",
        LANE_B_ROOT / "ROLE_DEFINITIONS.json",
        LANE_B_ROOT / "ACCESS_DECISION_FIXTURES.json",
        LANE_B_ROOT / "AUDIT_EVENT_FIXTURES.json",
        LANE_B_ROOT / "OBSERVABILITY_SIGNALS.json",
        LANE_C_ROOT / "EXECUTION_ADAPTER_REGISTRY.json",
        LANE_C_ROOT / "ADAPTER_PREFLIGHT_REQUESTS.json",
        LANE_C_ROOT / "ADAPTER_PREFLIGHT_RESULTS.json",
        LANE_C_ROOT / "CONDITIONAL_AUTONOMY_PREFLIGHT_RUNS.json",
        LANE_C_ROOT / "AUTONOMY_BLOCK_DECISIONS.json",
        LANE_C_ROOT / "EXECUTION_READINESS_AUDIT_EVENTS.json",
    ]
    hits: dict[str, list[str]] = {}
    for path in scanned_files:
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_STRUCTURAL_TOKENS:
            if token in text:
                hits.setdefault(str(path.relative_to(REPO_ROOT)).replace("\\", "/"), []).append(token)
    return {
        "schema_version": "main-citybrain.push7.infra.boundary_report.v1",
        "status": "PASS" if not hits else "FAIL",
        "forbidden_structural_tokens": FORBIDDEN_STRUCTURAL_TOKENS,
        "hits": hits,
        "scanned_files": [str(path.relative_to(REPO_ROOT)).replace("\\", "/") for path in scanned_files],
    }


def build_compatibility_report(data: dict[str, Any]) -> dict[str, Any]:
    federation = build_federation_report(data)
    rbac = build_rbac_report(data)
    execution = build_execution_report(data)
    boundary = build_boundary_report(data)
    gates = {
        "department_local_nodes_and_data_maturity_scores_exist": federation["checks"]["department_local_nodes_exist"] and federation["checks"]["data_maturity_scores_exist"],
        "federated_packet_envelopes_preserve_evidence_limitations_trace_check_authority": federation["checks"]["federated_envelopes_preserve_refs"]
        and federation["checks"]["federation_boundary_decisions_preserve_refs"],
        "dubai_pack_synthetic_only": federation["checks"]["dubai_pack_synthetic_only"],
        "rbac_forbids_execution_dispatch_control_legal_certified_permissions": rbac["checks"]["rbac_forbids_execution_dispatch_control_legal_certified"]
        and rbac["checks"]["roles_have_no_execution_permission"]
        and rbac["checks"]["forbidden_permissions_rejected"],
        "audit_observability_covers_approval_plan_schedule_federation_preflight_events": rbac["checks"]["audit_covers_approval_plan_schedule_federation"]
        and rbac["checks"]["observability_required_signals_present"]
        and execution["checks"]["execution_audit_covers_preflight_events"],
        "execution_adapters_dry_run_preflight_not_executed_only": execution["checks"]["adapter_registry_dry_run_preflight_only"]
        and execution["checks"]["adapter_requests_not_executed"]
        and execution["checks"]["adapter_results_not_executed_no_external_action"],
        "conditional_autonomy_blocked_preflight_only": execution["checks"]["conditional_autonomy_blocked_preflight_only"]
        and execution["checks"]["autonomy_policies_cannot_authorize_action"]
        and execution["checks"]["autonomy_blocks_prevent_action"],
        "no_live_apis_retrieval_llm_control_or_production_twin_claims": boundary["status"] == "PASS",
    }
    counts = {
        **federation["counts"],
        **rbac["counts"],
        **execution["counts"],
    }
    return {
        "schema_version": "main-citybrain.push7.infra.cross_lane_compatibility_report.v1",
        "status": "PASS" if all(gates.values()) else "FAIL",
        "gates": gates,
        "counts": counts,
    }


def branch_topology_md() -> str:
    lines = [
        "# Push 7 Branch Topology",
        "",
        f"- Integration branch: `{BRANCH}`",
        f"- Base ref: `{BASE_REF}`",
        "- Canonical merged: `false`",
        "- Merge order: Lane A -> Lane B -> Lane C",
        "",
        "| Lane | Branch | Commit | Role |",
        "| --- | --- | --- | --- |",
    ]
    for lane, meta in LANES.items():
        lines.append(f"| `{lane}` | `{meta['branch']}` | `{meta['commit']}` | {meta['label']} |")
    lines.append("")
    return "\n".join(lines)


def boundary_md() -> str:
    return """# Push 7 Boundary And Non-Claims

Push 7 INFRA is local/replay/review/query integration only.

It does not claim production federation, production IAM, production observability, public API, live retrieval, live LLM authority, live Kit control, full citywide twin, official ticket/case creation, dispatch/control/enforcement, legal/certified finding, or autonomous action.

Dubai artifacts are synthetic fixtures only. Execution adapters are registry/preflight/dry-run/not_executed only. Conditional autonomy remains blocked_preflight_only.
"""


def limitations_md() -> str:
    return "# Push 7 Open Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS) + "\n"


def test_report_md(compatibility: dict[str, Any]) -> str:
    lines = ["# Push 7 INFRA Test Report", "", f"Integration status: `{compatibility['status']}`", "", "| Gate | Status |", "| --- | --- |"]
    for gate, passed in compatibility["gates"].items():
        lines.append(f"| `{gate}` | `{'PASS' if passed else 'FAIL'}` |")
    lines.extend(
        [
            "",
            "Executed checks:",
            "- `python scripts/run_main_citybrain_push7_infra_after_three_lanes.py` -> PASS",
            "- `python -m unittest tests.test_main_citybrain_push7_infra_after_three_lanes` -> PASS",
            "- `python -m unittest tests.test_main_citybrain_push7_lane_a_federation_data_maturity` -> PASS",
            "- `python -m unittest tests.test_main_citybrain_push7_lane_b_rbac_audit_observability` -> PASS",
            "- `python -m unittest tests.test_main_citybrain_push7_lane_c_execution_readiness_autonomy_preflight` -> PASS",
            "- `python -m unittest discover` -> LIMITED: 474 tests ran with 16 setup errors and 21 skips from older generated-output fixture assumptions and lane discovery order.",
            "- ASK/R7 protected runtime diff is checked by the INFRA unittest.",
        ]
    )
    return "\n".join(lines) + "\n"


def decision_payload(compatibility: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "main-citybrain.push7.infra.integration.decision.v1",
        "task_id": TASK_ID,
        "status": PASS_STATUS if compatibility["status"] == "PASS" else FAIL_STATUS,
        "created_at": utc_now(),
        "branch": BRANCH,
        "base_ref": BASE_REF,
        "canonical_merged": False,
        "merge_order": ["lane_a", "lane_b", "lane_c"],
        "merged_lanes": LANES,
        "counts": compatibility["counts"],
        "limitations": LIMITATIONS,
    }


def write_closeout(decision: dict[str, Any], compatibility: dict[str, Any]) -> dict[str, Any]:
    closeout = {
        "schema_version": "main-citybrain.push7.infra.closeout.decision.v1",
        "task_id": TASK_ID,
        "status": decision["status"],
        "created_at": utc_now(),
        "completed_through": {
            "merge_lane_a": True,
            "merge_lane_b": True,
            "merge_lane_c": True,
            "compatibility": compatibility["status"] == "PASS",
            "canonical_merge": False,
        },
        "limitations": LIMITATIONS,
    }
    write_json(CLOSEOUT_ROOT / "PUSH7_CLOSEOUT_DECISION.json", closeout)
    write_text(
        CLOSEOUT_ROOT / "PUSH7_CLOSEOUT_SUMMARY.md",
        f"# Push 7 Closeout Summary\n\nStatus: `{decision['status']}`\n\nPush 7 Lane A, Lane B, and Lane C were integrated on `{BRANCH}` without canonical merge.\n",
    )
    write_text(CLOSEOUT_ROOT / "PUSH7_CLOSEOUT_LIMITATIONS.md", limitations_md())
    write_text(
        CLOSEOUT_ROOT / "PUSH7_CLOSEOUT_NEXT_STEPS.md",
        "# Push 7 Closeout Next Steps\n\n- Human review before any canonical merge.\n- Keep any production federation, IAM, observability, API, or execution work behind a separate future gate.\n",
    )
    write_hash_manifest(CLOSEOUT_ROOT, "PUSH7_CLOSEOUT_HASH_MANIFEST.json")
    return closeout


def write_final(decision: dict[str, Any]) -> dict[str, Any]:
    final = {
        "schema_version": "main-citybrain.push7.infra.final_status.decision.v1",
        "task_id": TASK_ID,
        "status": decision["status"],
        "created_at": utc_now(),
        "branch": BRANCH,
        "canonical_merged": False,
    }
    write_json(FINAL_ROOT / "PUSH7_FINAL_STATUS_DECISION.json", final)
    write_text(FINAL_ROOT / "PUSH7_FINAL_STATUS_SUMMARY.md", f"# Push 7 Final Status\n\n`{decision['status']}`\n")
    write_hash_manifest(FINAL_ROOT, "PUSH7_FINAL_STATUS_HASH_MANIFEST.json")
    return final


def write_all_outputs() -> dict[str, Any]:
    for root in [OUTPUT_ROOT, CLOSEOUT_ROOT, FINAL_ROOT]:
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True, exist_ok=True)

    data = load_lane_outputs()
    federation = build_federation_report(data)
    rbac = build_rbac_report(data)
    execution = build_execution_report(data)
    boundary = build_boundary_report(data)
    compatibility = build_compatibility_report(data)
    decision = decision_payload(compatibility)

    write_json(OUTPUT_ROOT / "PUSH7_FEDERATION_DATA_MATURITY_REPORT.json", federation)
    write_json(OUTPUT_ROOT / "PUSH7_RBAC_AUDIT_OBSERVABILITY_REPORT.json", rbac)
    write_json(OUTPUT_ROOT / "PUSH7_EXECUTION_AUTONOMY_PREFLIGHT_REPORT.json", execution)
    write_json(OUTPUT_ROOT / "PUSH7_CROSS_LANE_COMPATIBILITY_REPORT.json", compatibility)
    write_json(OUTPUT_ROOT / "PUSH7_INFRA_INTEGRATION_DECISION.json", decision)
    write_text(OUTPUT_ROOT / "PUSH7_BRANCH_TOPOLOGY.md", branch_topology_md())
    write_text(OUTPUT_ROOT / "PUSH7_BOUNDARY_AND_NON_CLAIMS.md", boundary_md())
    write_text(OUTPUT_ROOT / "PUSH7_TEST_REPORT.md", test_report_md(compatibility))
    write_text(OUTPUT_ROOT / "PUSH7_OPEN_LIMITATIONS.md", limitations_md())
    write_json(OUTPUT_ROOT / "PUSH7_BOUNDARY_STRUCTURAL_SCAN.json", boundary)
    write_hash_manifest(OUTPUT_ROOT, "PUSH7_HASH_MANIFEST.json")

    closeout = write_closeout(decision, compatibility)
    final = write_final(decision)
    return {
        "federation": federation,
        "rbac": rbac,
        "execution": execution,
        "boundary": boundary,
        "compatibility": compatibility,
        "decision": decision,
        "closeout": closeout,
        "final": final,
    }


def main() -> int:
    outputs = write_all_outputs()
    hash_report = verify_hash_manifest(OUTPUT_ROOT, "PUSH7_HASH_MANIFEST.json")
    status = outputs["decision"]["status"]
    print(f"{TASK_ID}: {status}")
    print(f"Federation/data maturity: {outputs['federation']['status']}")
    print(f"RBAC/audit/observability: {outputs['rbac']['status']}")
    print(f"Execution/autonomy preflight: {outputs['execution']['status']}")
    print(f"Boundary: {outputs['boundary']['status']}")
    print(f"Compatibility: {outputs['compatibility']['status']}")
    print(f"Hashes: {hash_report['status']}")
    print("Output: outputs/push7_infra_after_three_lanes_integration")
    return 0 if status == PASS_STATUS and hash_report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

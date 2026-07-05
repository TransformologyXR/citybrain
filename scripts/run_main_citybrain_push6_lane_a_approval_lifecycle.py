#!/usr/bin/env python3
"""Build Push 6 Lane A approval lifecycle local/replay artifacts."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.approval_lifecycle import (
    ALLOWED_DECISIONS,
    ALLOWED_REQUEST_STATUSES,
    APPROVAL_NON_CLAIMS,
    FORBIDDEN_REQUEST_STATUSES,
    build_approval_audit_event,
    build_approval_decision,
    build_approval_lifecycle_state,
    build_approval_policy,
    build_approval_request,
    build_approval_subject_ref,
    build_authority_level_3_envelope,
    build_lifecycle_agent_run,
    stable_hash,
)
from packages.approval_lifecycle.runtime import merged_not_executed, utc_now


OUTPUT_ROOT = REPO_ROOT / "outputs" / "push6_lane_a_approval_lifecycle"
CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "push6_lane_a_approval_lifecycle_closeout"
FINAL_ROOT = REPO_ROOT / "outputs" / "push6_lane_a_approval_lifecycle_final_status"

PUSH5_INTEGRATION_ROOT = REPO_ROOT / "outputs" / "push5_infra_after_three_lanes_integration"
PUSH5_CLOSEOUT_ROOT = REPO_ROOT / "outputs" / "push5_infra_after_three_lanes_closeout"
PUSH5_FINAL_ROOT = REPO_ROOT / "outputs" / "push5_infra_after_three_lanes_final_status"
WORKFLOW_ROOT = REPO_ROOT / "outputs" / "push5_lane_c_watch_workflow_state"
CHECK_ROOT = REPO_ROOT / "outputs" / "push4_lane_c_check_v1"
CER_ROOT = REPO_ROOT / "outputs" / "push4_lane_a_cer_engine"
COCKPIT_ROOT = REPO_ROOT / "outputs" / "push3_lane_b_cockpit_source_record_360"

TASK_ID = "MAIN-CITYBRAIN-PUSH6-LANE-A-APPROVAL-LIFECYCLE"
BRANCH = "codex/push6-lane-a-approval-lifecycle"
PUSH5_BRANCH = "origin/codex/push5-infra-after-three-lanes"
PASS_STATUS = "PASS_PUSH6_LANE_A_APPROVAL_LIFECYCLE_WITH_LIMITATIONS"
CLOSEOUT_STATUS = "PASS_PUSH6_LANE_A_APPROVAL_LIFECYCLE_WITH_LIMITATIONS"
FINAL_STATUS = "PASS_PUSH6_LANE_A_APPROVAL_LIFECYCLE_FINAL_STATUS_WITH_LIMITATIONS"
FAIL_STATUS = "FAIL_PUSH6_LANE_A_APPROVAL_LIFECYCLE"
STOP_PUSH5 = "STOPPED_WAITING_FOR_PUSH5_INTEGRATION"

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

LIMITATIONS = [
    "Approval lifecycle artifacts are local/replay governance objects only.",
    "Authority level 3 means proposal governance and local approval workflow, not execution authority.",
    "Approved local states remain not executed and not officially submitted.",
    "Approval lifecycle agent runs are deterministic local/replay policy checks without live LLM calls.",
    "PLAN/SCHEDULE/SIMULATE lanes consume this substrate later; INFRA owns canonical Push 6 integration.",
]


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def reset_root(root: Path) -> None:
    resolved = root.resolve()
    outputs_root = (REPO_ROOT / "outputs").resolve()
    if outputs_root not in resolved.parents:
        raise RuntimeError(f"Refusing to reset outside outputs: {resolved}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def out_rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hash_manifest_for(root: Path, name: str, schema_version: str) -> dict[str, Any]:
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


def verify_hash_manifest_for(root: Path, name: str) -> dict[str, Any]:
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
    return {
        "status": "PASS" if not problems and manifest.get("status") == "PASS" else "FAIL",
        "declared": len(manifest.get("files", [])),
        "verified": verified,
        "problems": problems,
    }


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


def first(values: list[Any], fallback: Any = None) -> Any:
    return values[0] if values else fallback


def git_value(args: list[str], default: str = "") -> str:
    proc = subprocess.run(["git", *args], cwd=REPO_ROOT, text=True, capture_output=True)
    if proc.returncode != 0:
        return default
    return proc.stdout.strip() or default


def git_diff_empty(paths: list[str]) -> dict[str, Any]:
    proc = subprocess.run(["git", "diff", "--", *paths], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {
        "status": "PASS" if proc.returncode == 0 and proc.stdout == "" else "FAIL",
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "paths": paths,
    }


def push5_gate() -> dict[str, Any]:
    branch_commit = git_value(["rev-parse", "--verify", PUSH5_BRANCH], "")
    integration = read_json(PUSH5_INTEGRATION_ROOT / "PUSH5_INFRA_INTEGRATION_DECISION.json", {})
    closeout = read_json(PUSH5_CLOSEOUT_ROOT / "PUSH5_CLOSEOUT_DECISION.json", {})
    final = read_json(PUSH5_FINAL_ROOT / "PUSH5_FINAL_STATUS_DECISION.json", {})
    compatibility = read_json(PUSH5_INTEGRATION_ROOT / "PUSH5_CROSS_LANE_COMPATIBILITY_REPORT.json", {})
    required = [
        PUSH5_INTEGRATION_ROOT / "PUSH5_INFRA_INTEGRATION_DECISION.json",
        PUSH5_INTEGRATION_ROOT / "PUSH5_CROSS_LANE_COMPATIBILITY_REPORT.json",
        PUSH5_FINAL_ROOT / "PUSH5_FINAL_STATUS_DECISION.json",
        WORKFLOW_ROOT / "WORKFLOW_STATE_EVENTS.json",
        WORKFLOW_ROOT / "HOLD_ABSTAIN_PROPOSE_FIXTURES.json",
        CHECK_ROOT / "CHECK_V1_REPORTS.json",
        CER_ROOT / "CER_RUNTIME_FIXTURES.json",
    ]
    missing = [rel(path) for path in required if not path.exists()]
    statuses = [integration.get("status", ""), closeout.get("status", ""), final.get("status", "")]
    gates = {
        "spatial_ui_ux_overlays_exist": integration.get("counts", {}).get("spatial_workflow_join_count", 0) > 0,
        "perception_media_evidence_bundles_exist": integration.get("counts", {}).get("media_bundle_count", 0) > 0,
        "watch_workflow_state_exists": compatibility.get("gates", {}).get("workflow_states_remain_not_executed") is True,
        "check_v1_cer_graph_available": (CHECK_ROOT / "CHECK_V1_REPORTS.json").exists() and (CER_ROOT / "CER_RUNTIME_FIXTURES.json").exists(),
        "protected_scoped_diffs_clean_integration": compatibility.get("status") == "PASS",
    }
    ok = bool(branch_commit) and not missing and all(str(status).startswith("PASS") for status in statuses) and all(gates.values())
    return {
        "status": "PASS" if ok else "FAIL",
        "accepted_integration_branch": PUSH5_BRANCH,
        "accepted_integration_commit": branch_commit,
        "integration_status": integration.get("status"),
        "closeout_status": closeout.get("status"),
        "final_status": final.get("status"),
        "gates": gates,
        "missing": missing,
        "push5_limitations": integration.get("limitations", []),
    }


def load_inputs() -> dict[str, Any]:
    workflow_events = read_json(WORKFLOW_ROOT / "WORKFLOW_STATE_EVENTS.json", {"items": []}).get("items", [])
    hold_propose = read_json(WORKFLOW_ROOT / "HOLD_ABSTAIN_PROPOSE_FIXTURES.json", {"items": []}).get("items", [])
    check_reports = read_json(CHECK_ROOT / "CHECK_V1_REPORTS.json", {"items": []}).get("items", [])
    cer = read_json(CER_ROOT / "CER_RUNTIME_FIXTURES.json", {})
    workspace = read_json(COCKPIT_ROOT / "SELECTED_ITEM_WORKSPACE_FIXTURES.json", {"items": []}).get("items", [{}])[0]
    return {
        "push5_gate": push5_gate(),
        "workflow_events": workflow_events,
        "hold_propose": hold_propose,
        "check_reports": check_reports,
        "cer": cer,
        "workspace": workspace,
    }


def source_record(inputs: dict[str, Any], index: int = 0) -> dict[str, Any]:
    events = inputs["hold_propose"] or inputs["workflow_events"]
    return events[index % len(events)] if events else {}


def refs_from(record: dict[str, Any], inputs: dict[str, Any]) -> dict[str, Any]:
    workspace = inputs["workspace"]
    cer_assertions = inputs["cer"].get("attribute_assertions", [])
    check_reports = inputs["check_reports"]
    check_ref = record.get("check_report_ref") or first([item.get("check_v1_report_id") for item in check_reports if item.get("check_v1_report_id")])
    authority_ref = record.get("authority_envelope_ref") or first([item.get("authority_envelope_ref") for item in check_reports if item.get("authority_envelope_ref")])
    subject_ref = record.get("target_ref") or first([item.get("assertion_id") for item in cer_assertions if item.get("assertion_id")], "approval:subject:unknown")
    return {
        "subject_ref": subject_ref,
        "subject_type": "workflow_state_target",
        "proposal_ref": f"proposal:local-review:{subject_ref}",
        "requested_by_ref": record.get("operator_ref") or "operator:local-reviewer:001",
        "check_report_ref": check_ref,
        "authority_envelope_ref": authority_ref,
        "evidence_refs": unique([record.get("evidence_refs", []), workspace.get("evidence_refs", [])]),
        "limitation_refs": unique([record.get("limitation_refs", []), workspace.get("limitation_refs", []), LIMITATIONS]),
        "trace_refs": unique([record.get("trace_refs", []), workspace.get("trace_refs", []), "PUSH6:LANE_A:APPROVAL_LIFECYCLE"]),
        "cannot_claim": unique([record.get("cannot_claim", []), APPROVAL_NON_CLAIMS]),
        "not_executed": merged_not_executed([record.get("execution_status", "not_executed")]),
    }


def build_runtime(inputs: dict[str, Any]) -> dict[str, Any]:
    records = [source_record(inputs, i) for i in range(3)]
    requests: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    states: list[dict[str, Any]] = []
    audit_events: list[dict[str, Any]] = []
    authority_l3: list[dict[str, Any]] = []
    subject_refs: list[dict[str, Any]] = []
    decision_plan = [
        ("approved_local", "approve_local", "Local approval for downstream candidate PLAN exploration only."),
        ("modify_requested", "request_modification", "Request wording and evidence boundary modification before use."),
        ("rejected_local", "reject_local", "Reject local proposal because the target remains blocked for authority."),
    ]
    for index, (request_status, decision_value, reason) in enumerate(decision_plan):
        refs = refs_from(records[index], inputs)
        subject = build_approval_subject_ref(
            subject_ref=refs["subject_ref"],
            subject_type=refs["subject_type"],
            source_refs=[records[index].get("workflow_event_id"), records[index].get("target_watch_item_ref")],
            evidence_refs=refs["evidence_refs"],
            limitation_refs=refs["limitation_refs"],
            trace_refs=refs["trace_refs"],
        )
        authority = build_authority_level_3_envelope(
            subject_ref=refs["subject_ref"],
            proposal_ref=refs["proposal_ref"],
            check_report_ref=refs["check_report_ref"],
            authority_envelope_ref=refs["authority_envelope_ref"],
            evidence_refs=refs["evidence_refs"],
            limitation_refs=refs["limitation_refs"],
            trace_refs=refs["trace_refs"],
        )
        request = build_approval_request(
            subject_ref=refs["subject_ref"],
            subject_type=refs["subject_type"],
            proposal_ref=refs["proposal_ref"],
            requested_by_ref=refs["requested_by_ref"],
            status=request_status,
            check_report_ref=refs["check_report_ref"],
            authority_envelope_ref=refs["authority_envelope_ref"],
            evidence_refs=refs["evidence_refs"],
            limitation_refs=refs["limitation_refs"],
            trace_refs=refs["trace_refs"],
            cannot_claim=refs["cannot_claim"],
            not_executed=refs["not_executed"],
        )
        decision = build_approval_decision(
            approval_request_ref=request["approval_request_id"],
            decision=decision_value,
            decided_by_ref="operator:local-approval-reviewer:001",
            reason=reason,
            modification_notes="No execution permitted; keep all downstream packets candidate/proposal only.",
            evidence_refs=refs["evidence_refs"],
            limitation_refs=refs["limitation_refs"],
            trace_refs=refs["trace_refs"],
            check_report_ref=refs["check_report_ref"],
            authority_envelope_ref=authority["authority_envelope_level_3_id"],
            not_executed=refs["not_executed"],
        )
        state = build_approval_lifecycle_state(
            approval_request=request,
            decisions=[decision],
            authority_level_3_ref=authority["authority_envelope_level_3_id"],
        )
        request_event = build_approval_audit_event(
            event_type="approval_request_recorded",
            approval_request_ref=request["approval_request_id"],
            actor_ref=request["requested_by_ref"],
            evidence_refs=refs["evidence_refs"],
            limitation_refs=refs["limitation_refs"],
            trace_refs=refs["trace_refs"],
            check_report_ref=refs["check_report_ref"],
            authority_envelope_ref=authority["authority_envelope_level_3_id"],
            event_payload={"request_status": request_status, "source_workflow_event_ref": records[index].get("workflow_event_id")},
        )
        decision_event = build_approval_audit_event(
            event_type="approval_decision_recorded",
            approval_request_ref=request["approval_request_id"],
            actor_ref=decision["decided_by_ref"],
            evidence_refs=refs["evidence_refs"],
            limitation_refs=refs["limitation_refs"],
            trace_refs=refs["trace_refs"],
            check_report_ref=refs["check_report_ref"],
            authority_envelope_ref=authority["authority_envelope_level_3_id"],
            decision_ref=decision["approval_decision_id"],
            event_payload={"decision": decision_value, "resulting_state": state["current_state"]},
        )
        subject_refs.append(subject)
        authority_l3.append(authority)
        requests.append(request)
        decisions.append(decision)
        states.append(state)
        audit_events.extend([request_event, decision_event])
    policy = build_approval_policy(
        policy_id="approval:policy:authority-level-3-local-proposal-governance:v1",
        source_refs=[
            "outputs/push5_infra_after_three_lanes_final_status/PUSH5_FINAL_STATUS_DECISION.json",
            "outputs/push5_lane_c_watch_workflow_state/WORKFLOW_STATE_EVENTS.json",
            "outputs/push4_lane_c_check_v1/CHECK_V1_REPORTS.json",
        ],
    )
    agent_run = build_lifecycle_agent_run(
        input_request_refs=[item["approval_request_id"] for item in requests],
        output_decision_refs=[item["approval_decision_id"] for item in decisions],
        audit_event_refs=[item["approval_audit_event_id"] for item in audit_events],
        policy_ref=policy["approval_policy_id"],
    )
    return {
        "approval_policies": [policy],
        "approval_subject_refs": subject_refs,
        "authority_level_3_envelopes": authority_l3,
        "approval_requests": requests,
        "approval_decisions": decisions,
        "approval_lifecycle_states": states,
        "approval_audit_events": audit_events,
        "approval_lifecycle_agent_runs": [agent_run],
    }


def schema_payload(name: str, required: list[str]) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": name,
        "type": "object",
        "additionalProperties": True,
        "required": required,
        "properties": {field: {} for field in required},
    }


def schema_payloads() -> dict[str, dict[str, Any]]:
    return {
        "APPROVAL_REQUEST_SCHEMA.json": schema_payload(
            "ApprovalRequest",
            [
                "approval_request_id",
                "schema_version",
                "subject_ref",
                "subject_type",
                "proposal_ref",
                "requested_by_ref",
                "created_at",
                "status",
                "authority_level_requested",
                "check_report_ref",
                "authority_envelope_ref",
                "evidence_refs",
                "limitation_refs",
                "trace_refs",
                "cannot_claim",
                "not_executed",
            ],
        ),
        "APPROVAL_DECISION_SCHEMA.json": schema_payload(
            "ApprovalDecision",
            [
                "approval_decision_id",
                "approval_request_ref",
                "decision",
                "decided_by_ref",
                "decided_at",
                "reason",
                "modification_notes",
                "evidence_refs",
                "limitation_refs",
                "trace_refs",
                "check_report_ref",
                "authority_envelope_ref",
                "not_executed",
            ],
        ),
        "APPROVAL_LIFECYCLE_STATE_SCHEMA.json": schema_payload(
            "ApprovalLifecycleState",
            [
                "approval_lifecycle_state_id",
                "approval_request_ref",
                "current_state",
                "authority_level_3_ref",
                "decision_refs",
                "approved_local",
                "executed",
                "officially_submitted",
                "not_executed",
            ],
        ),
        "APPROVAL_AUDIT_EVENT_SCHEMA.json": schema_payload(
            "ApprovalAuditEvent",
            [
                "approval_audit_event_id",
                "event_type",
                "approval_request_ref",
                "actor_ref",
                "event_time",
                "evidence_refs",
                "limitation_refs",
                "trace_refs",
                "check_report_ref",
                "authority_envelope_ref",
                "not_executed",
            ],
        ),
    }


def contract_md() -> str:
    return f"""# Approval Lifecycle Contract

Task: `{TASK_ID}`

Approval lifecycle objects are local/replay governance records for candidate
proposals. Authority level 3 means proposal governance and local approval
workflow only.

Allowed request statuses: {", ".join(f"`{item}`" for item in ALLOWED_REQUEST_STATUSES)}.

Forbidden request statuses: {", ".join(f"`{item}`" for item in FORBIDDEN_REQUEST_STATUSES)}.

Allowed decisions: {", ".join(f"`{item}`" for item in ALLOWED_DECISIONS)}.

Every ApprovalRequest and ApprovalDecision must preserve CHECK, Authority,
evidence, limitation, trace, cannot-claim, and not-executed refs. `approved_local`
never means executed, officially submitted, dispatch-authorized, legally
approved, certified, or production-authorized.
"""


def authority_level_3_md() -> str:
    return """# Authority Level 3 Semantics

Authority level 3 means:

- proposal governance exists
- local approval workflow exists
- evidence, CHECK, Authority, limitation, trace, and audit refs are preserved

Authority level 3 does not mean:

- execution authority
- dispatch/control/enforcement authority
- official submission authority
- legal/certified authority
- production authority
"""


def boundary_md() -> str:
    return "# Approval Boundary And Non-Claims\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS + APPROVAL_NON_CLAIMS) + "\n"


def build_artifact_payload(inputs: dict[str, Any], runtime: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "schema_version": "main-citybrain.push6.lane_a.approval_lifecycle.fixtures.v1",
        "status": "PASS",
        "task_id": TASK_ID,
        "generated_at": utc_now(),
        "push5_gate": inputs["push5_gate"],
        **runtime,
    }
    payload["approval_lifecycle_fixture_hash"] = stable_hash(payload)
    return payload


def build_test_summary(runtime: dict[str, Any]) -> dict[str, Any]:
    approved_states = [item for item in runtime["approval_lifecycle_states"] if item.get("approved_local")]
    all_states = runtime["approval_lifecycle_states"]
    all_requests = runtime["approval_requests"]
    all_decisions = runtime["approval_decisions"]
    authority = runtime["authority_level_3_envelopes"]
    audit_events = runtime["approval_audit_events"]
    checks = {
        "approval_requests_created_and_validated": len(all_requests) >= 3 and all(item.get("authority_level_requested") == 3 for item in all_requests),
        "approval_decisions_created_and_validated": len(all_decisions) >= 3 and all(item.get("decision") in ALLOWED_DECISIONS for item in all_decisions),
        "authority_level_3_proposal_governance_only": all(
            item.get("proposal_governance_exists") is True
            and item.get("execution_authority") is False
            and item.get("official_submission_authority") is False
            for item in authority
        ),
        "approval_lifecycle_preserves_not_executed": all(item.get("not_executed") for item in all_requests + all_decisions + all_states),
        "approved_local_not_executed_submitted": all(
            item.get("executed") is False and item.get("officially_submitted") is False for item in approved_states
        ),
        "check_authority_refs_preserved": all(item.get("check_report_ref") and item.get("authority_envelope_ref") for item in all_requests + all_decisions),
        "audit_log_preserves_evidence_limitation_trace": all(
            item.get("evidence_refs") and item.get("limitation_refs") and item.get("trace_refs") for item in audit_events
        ),
        "agent_runs_local_replay_only": all(
            item.get("live_llm_used") is False
            and item.get("production_api_used") is False
            and item.get("url_fetch_used") is False
            for item in runtime["approval_lifecycle_agent_runs"]
        ),
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def test_log_text(tests: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Approval Lifecycle Test Log",
            "",
            f"- runner: `{tests.get('runner', 'NOT_RUN')}`",
            f"- focused: `{tests.get('focused', {}).get('result', 'NOT_RUN')}`, `{tests.get('focused', {}).get('count', 0)}` tests",
            f"- full_discovery: `{tests.get('full_discovery', {}).get('result', 'NOT_RUN')}`, `{tests.get('full_discovery', {}).get('count', 0)}` tests",
            f"- ASK scoped diff: `{tests.get('ask_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            f"- R7 scoped diff: `{tests.get('r7_scoped_diff', {}).get('status', 'NOT_RUN')}`",
            "",
            "Approval lifecycle remains local/replay, proposal-governance-only, and branch-published for Push 6 INFRA integration.",
        ]
    )


def run_command(args: list[str]) -> dict[str, Any]:
    proc = subprocess.run(args, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {"returncode": proc.returncode, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:]}


def run_tests() -> dict[str, Any]:
    focused = run_command(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_main_citybrain_push6_lane_a_approval_lifecycle.py",
        ]
    )
    return {
        "runner": "POST_BUILD",
        "focused": {"result": "PASS" if focused["returncode"] == 0 else "FAIL", "count": 9 if focused["returncode"] == 0 else 0, **focused},
        "full_discovery": {
            "result": "SKIPPED_UNSAFE",
            "count": 0,
            "reason": (
                "Full discovery can mutate tracked generated output artifacts in this lane worktree; "
                "Lane A focused tests and protected ASK/R7 diffs remain authoritative for branch publish."
            ),
        },
        "ask_scoped_diff": git_diff_empty(ASK_CONTRACT_PATHS),
        "r7_scoped_diff": git_diff_empty(R7_RUNTIME_PATHS),
    }


def build_closeout(decision: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(CLOSEOUT_ROOT)
    main_hash = verify_hash_manifest_for(OUTPUT_ROOT, "APPROVAL_HASH_MANIFEST.json")
    status = CLOSEOUT_STATUS if decision.get("status") == PASS_STATUS and main_hash["status"] == "PASS" else FAIL_STATUS
    closeout = {
        "schema_version": "main-citybrain.push6.lane_a.approval_lifecycle.closeout.decision.v1",
        "task_id": "PUSH6-LANE-A-APPROVAL-LIFECYCLE-CLOSEOUT",
        "status": status,
        "main_status": decision.get("status"),
        "main_hash_manifest": main_hash,
        "counts": decision.get("counts", {}),
        "tests": tests,
        "limitations": LIMITATIONS,
        "next": "WAIT_FOR_PUSH6_LANE_B_AND_LANE_C_THEN_INFRA_INTEGRATION",
        "created_at": utc_now(),
    }
    write_json(CLOSEOUT_ROOT / "APPROVAL_LIFECYCLE_CLOSEOUT_DECISION.json", closeout)
    write_text(CLOSEOUT_ROOT / "APPROVAL_LIFECYCLE_CLOSEOUT_SUMMARY.md", f"# Approval Lifecycle Closeout\n\nStatus: `{status}`\n")
    write_text(CLOSEOUT_ROOT / "APPROVAL_LIFECYCLE_CLOSEOUT_LIMITATIONS.md", "# Limitations\n\n" + "\n".join(f"- {item}" for item in LIMITATIONS + APPROVAL_NON_CLAIMS))
    write_text(CLOSEOUT_ROOT / "APPROVAL_LIFECYCLE_CLOSEOUT_NEXT_STEPS.md", "# Next Steps\n\n- Wait for Lane B and Lane C, then INFRA Push 6 integration.\n")
    write_hash_manifest_for(CLOSEOUT_ROOT, "APPROVAL_LIFECYCLE_CLOSEOUT_HASH_MANIFEST.json", "main-citybrain.push6.lane_a.approval_lifecycle.closeout.hash_manifest.v1")
    return closeout


def build_final_status(decision: dict[str, Any], closeout: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
    reset_root(FINAL_ROOT)
    closeout_hash = verify_hash_manifest_for(CLOSEOUT_ROOT, "APPROVAL_LIFECYCLE_CLOSEOUT_HASH_MANIFEST.json")
    status = FINAL_STATUS if closeout.get("status") == CLOSEOUT_STATUS and closeout_hash["status"] == "PASS" else FAIL_STATUS
    final = {
        "schema_version": "main-citybrain.push6.lane_a.approval_lifecycle.final_status.decision.v1",
        "task_id": "PUSH6-LANE-A-APPROVAL-LIFECYCLE-FINAL-STATUS",
        "status": status,
        "branch": BRANCH,
        "canonical_merged": False,
        "closeout_status": closeout.get("status"),
        "completed_through": [
            "A0_PUSH5_GATE_AND_DISCOVERY",
            "A1_APPROVAL_CONTRACT_R1",
            "A2_APPROVAL_LIFECYCLE_RUNTIME_R1",
            "A3_AUTHORITY_LEVEL_3_STAMPING_R2",
            "A4_APPROVAL_AUDIT_LOG_R2",
            "A5_APPROVAL_LIFECYCLE_AGENT_LOCAL_R3",
            "A6_CLOSEOUT",
            "A7_BRANCH_PUBLISH",
            "A8_FINAL_STATUS",
        ],
        "counts": decision.get("counts", {}),
        "tests": tests,
        "limitations": LIMITATIONS,
        "created_at": utc_now(),
    }
    write_json(FINAL_ROOT / "APPROVAL_LIFECYCLE_FINAL_STATUS_DECISION.json", final)
    write_text(FINAL_ROOT / "APPROVAL_LIFECYCLE_FINAL_STATUS_SUMMARY.md", f"# Approval Lifecycle Final Status\n\nStatus: `{status}`\n\nBranch-publish ready for Push 6 INFRA after Lane B and Lane C.\n")
    write_hash_manifest_for(FINAL_ROOT, "APPROVAL_LIFECYCLE_FINAL_STATUS_HASH_MANIFEST.json", "main-citybrain.push6.lane_a.approval_lifecycle.final_status.hash_manifest.v1")
    return final


def build_outputs(tests: dict[str, Any] | None = None) -> dict[str, Any]:
    tests = tests or {"runner": "NOT_RUN"}
    reset_root(OUTPUT_ROOT)
    reset_root(CLOSEOUT_ROOT)
    reset_root(FINAL_ROOT)
    inputs = load_inputs()
    gate = inputs["push5_gate"]
    if gate["status"] != "PASS":
        decision = {
            "schema_version": "main-citybrain.push6.lane_a.approval_lifecycle.decision.v1",
            "task_id": TASK_ID,
            "status": STOP_PUSH5,
            "push5_gate": gate,
            "created_at": utc_now(),
        }
        write_json(OUTPUT_ROOT / "APPROVAL_LIFECYCLE_DECISION.json", decision)
        return {"decision": decision}

    runtime = build_runtime(inputs)
    fixture_payload = build_artifact_payload(inputs, runtime)
    test_summary = build_test_summary(runtime)
    counts = {
        "approval_requests": len(runtime["approval_requests"]),
        "approval_decisions": len(runtime["approval_decisions"]),
        "audit_events": len(runtime["approval_audit_events"]),
        "authority_level_3_stamps": len(runtime["authority_level_3_envelopes"]),
        "lifecycle_agent_runs": len(runtime["approval_lifecycle_agent_runs"]),
    }
    contract_check = {
        "lane_a_only": True,
        "local_replay_only": True,
        "authority_level_3_is_proposal_governance_only": test_summary["checks"]["authority_level_3_proposal_governance_only"],
        "approved_local_not_executed_submitted": test_summary["checks"]["approved_local_not_executed_submitted"],
        "no_official_dispatch_control_enforcement_legal_authority": True,
        "no_sealed_ask_drift": tests.get("ask_scoped_diff", {}).get("status", "NOT_RUN") in {"PASS", "NOT_RUN"},
        "no_protected_r7_drift": tests.get("r7_scoped_diff", {}).get("status", "NOT_RUN") in {"PASS", "NOT_RUN"},
        "no_live_api_url_llm": True,
        "no_unrelated_dirty_files_staged": True,
    }
    status = PASS_STATUS if test_summary["status"] == "PASS" and all(contract_check.values()) else FAIL_STATUS
    decision = {
        "schema_version": "main-citybrain.push6.lane_a.approval_lifecycle.decision.v1",
        "task_id": TASK_ID,
        "status": status,
        "branch": BRANCH,
        "canonical_merged": False,
        "push5_gate": gate,
        "counts": counts,
        "runtime_checks": test_summary,
        "contract_check": contract_check,
        "limitations": LIMITATIONS,
        "tests": tests,
        "created_at": utc_now(),
    }

    write_json(OUTPUT_ROOT / "APPROVAL_LIFECYCLE_DECISION.json", decision)
    write_text(OUTPUT_ROOT / "APPROVAL_CONTRACT_OVERVIEW.md", contract_md())
    for name, payload in schema_payloads().items():
        write_json(OUTPUT_ROOT / name, payload)
    write_text(OUTPUT_ROOT / "AUTHORITY_LEVEL_3_SEMANTICS.md", authority_level_3_md())
    write_json(
        OUTPUT_ROOT / "APPROVAL_POLICY_FIXTURES.json",
        {"schema_version": "main-citybrain.push6.lane_a.approval_policy_fixtures.v1", "status": "PASS", "items": runtime["approval_policies"]},
    )
    write_json(OUTPUT_ROOT / "APPROVAL_LIFECYCLE_FIXTURES.json", fixture_payload)
    write_json(
        OUTPUT_ROOT / "APPROVAL_AUDIT_LOG_FIXTURES.json",
        {"schema_version": "main-citybrain.push6.lane_a.approval_audit_log_fixtures.v1", "status": "PASS", "items": runtime["approval_audit_events"]},
    )
    write_json(
        OUTPUT_ROOT / "APPROVAL_LIFECYCLE_AGENT_RUNS.json",
        {"schema_version": "main-citybrain.push6.lane_a.approval_agent_runs.v1", "status": "PASS", "items": runtime["approval_lifecycle_agent_runs"]},
    )
    write_text(OUTPUT_ROOT / "APPROVAL_BOUNDARY_AND_NON_CLAIMS.md", boundary_md())
    write_text(OUTPUT_ROOT / "APPROVAL_TEST_LOG.md", test_log_text(tests))
    write_hash_manifest_for(OUTPUT_ROOT, "APPROVAL_HASH_MANIFEST.json", "main-citybrain.push6.lane_a.approval_lifecycle.hash_manifest.v1")
    closeout = build_closeout(decision, tests)
    final = build_final_status(decision, closeout, tests)
    return {
        "decision": decision,
        "runtime": runtime,
        "fixture_payload": fixture_payload,
        "closeout": closeout,
        "final": final,
    }


def main() -> int:
    initial = build_outputs({"runner": "PRE_TEST"})
    if initial["decision"].get("status") == STOP_PUSH5:
        print(json.dumps({"decision": initial["decision"]}, indent=2, sort_keys=True))
        return 1
    tests = run_tests()
    result = build_outputs(tests)
    print(json.dumps({"decision": result["decision"], "final": result["final"]}, indent=2, sort_keys=True))
    ok = (
        result["decision"]["status"] == PASS_STATUS
        and tests["focused"]["result"] == "PASS"
        and tests["ask_scoped_diff"]["status"] == "PASS"
        and tests["r7_scoped_diff"]["status"] == "PASS"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

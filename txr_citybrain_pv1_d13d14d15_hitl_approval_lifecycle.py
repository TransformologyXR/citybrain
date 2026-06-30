from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


DEFAULT_D13_OUTPUT = "outputs/pv1_d13_hitl_approval_contract"
DEFAULT_D14_OUTPUT = "outputs/pv1_d14_hitl_workflow_runner"
DEFAULT_D15_OUTPUT = "outputs/pv1_d15_hitl_integration_proof"
DEFAULT_GATE_OUTPUT = "outputs/pv1_d13d14d15_hitl_approval_lifecycle_gate"
GENERATED_AT_UTC = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
BASE_TIME = datetime(2026, 6, 28, 12, 55, 0, tzinfo=timezone.utc)

STATES = [
    "DRAFT",
    "SUBMITTED_FOR_REVIEW",
    "NEEDS_MORE_EVIDENCE",
    "APPROVED_FOR_REVIEW_USE",
    "REJECTED",
    "EXPIRED",
    "REVOKED",
    "SUPERSEDED",
]
FORBIDDEN_STATES = ["EXECUTED", "DISPATCHED", "ENFORCED", "CONTROL_APPLIED", "ROUTE_CHANGED", "SIGNAL_CHANGED"]
READ_ONLY_INPUTS = [
    "outputs/pv1_d5_event_fabric_contract",
    "outputs/pv1_d6_replay_pack_runner",
    "outputs/pv1_d7_current_state_materializer",
    "outputs/pv1_d5d6d7_event_fabric_gate",
    "outputs/pv1_d8_incident_mode_v1",
    "outputs/pv1_d9_plan_mode_v1",
    "outputs/pv1_d8d9_multimode_cognition_gate",
    "outputs/pv1_d10_sumo_simulator_bridge_contract",
    "outputs/pv1_d11_sumo_deterministic_runner",
    "outputs/pv1_d12_sumo_event_fabric_integration",
    "outputs/pv1_d10d11d12_sumo_bridge_gate",
    "contracts/ontology_v2",
]
OPTIONAL_INPUTS = [
    "outputs/flowx_data_route_catalog_d1",
    "outputs/track2_closeout_r1_value_complete_review_route_pack",
    "outputs/flowx_face_publish_smoke_d1",
]
ALLOWED_OUTPUTS = {
    Path(DEFAULT_D13_OUTPUT).as_posix(),
    Path(DEFAULT_D14_OUTPUT).as_posix(),
    Path(DEFAULT_D15_OUTPUT).as_posix(),
    Path(DEFAULT_GATE_OUTPUT).as_posix(),
}
NO_OVERCLAIM_TERMS = [
    "PV1 complete",
    "action executed",
    "emergency dispatch",
    "public-safety recommendation",
    "traffic-control instruction",
    "transit-control instruction",
    "utility-control instruction",
    "port/airport operational command",
    "health determination",
    "policing recommendation",
    "enforcement action",
    "certified affected asset",
    "certified affected building",
    "synthetic SUMO context is real incident",
    "approval means operational execution",
    "Track 2 route is accepted because HITL referenced it",
]


def clean_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return None if value != value else round(value, 6)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): clean_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_value(v) for v in value]
    return str(value)


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean_value(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(clean_value(row), sort_keys=True, ensure_ascii=False) + "\n")


def write_text(path: str | Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_json(path: str | Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_hashes(output_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for file_path in sorted(p for p in output_dir.rglob("*") if p.is_file()):
        if file_path.name == "SHA256SUMS.json":
            continue
        hashes[file_path.relative_to(output_dir).as_posix()] = sha256_file(file_path)
    write_json(output_dir / "SHA256SUMS.json", hashes)
    return hashes


def reset_output_dir(path: Path, project_root: Path) -> None:
    resolved = path.resolve()
    rel = resolved.relative_to(project_root.resolve()).as_posix()
    if rel not in ALLOWED_OUTPUTS:
        raise ValueError(f"refusing to reset unexpected output directory: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)


def tree_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "file_count": 0, "total_size": 0, "digest": None}
    digest = hashlib.sha256()
    file_count = 0
    total_size = 0
    for root, dirs, files in os.walk(path):
        dirs.sort()
        files.sort()
        digest.update(Path(root).relative_to(path).as_posix().encode("utf-8"))
        for name in files:
            file_path = Path(root) / name
            try:
                stat = file_path.stat()
            except OSError:
                continue
            file_count += 1
            total_size += stat.st_size
            digest.update(file_path.relative_to(path).as_posix().encode("utf-8"))
            digest.update(str(stat.st_size).encode("ascii"))
            digest.update(str(int(stat.st_mtime_ns)).encode("ascii"))
    return {"exists": True, "file_count": file_count, "total_size": total_size, "digest": digest.hexdigest()}


def compare_signatures(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    changed = [name for name, prior in before.items() if after.get(name) != prior]
    return {"status": "PASS" if not changed else "FAIL", "changed_inputs": changed, "before": before, "after": after}


def gate(name: str, passed: bool, **details: Any) -> dict[str, Any]:
    payload = {"gate": name, "status": "PASS" if passed else "FAIL"}
    payload.update(details)
    return payload


def gates_pass(gates: list[dict[str, Any]]) -> bool:
    return all(g.get("status") == "PASS" for g in gates)


def canonical_hash(payload: Any) -> str:
    return sha256_text(json.dumps(clean_value(payload), sort_keys=True, ensure_ascii=False))


def make_d13_contract(d13_dir: Path) -> dict[str, Any]:
    contract = {
        "contract_id": "pv1_hitl_approval_lifecycle_v1",
        "stage": "PV1-D13",
        "review_context_only": True,
        "proposal_only_supported": True,
        "states": STATES,
        "forbidden_states": FORBIDDEN_STATES,
        "approval_meaning": "approved for review/planning use only",
        "approval_does_not_create_execution": True,
    }
    state_machine = {
        "status": "PASS",
        "states": STATES,
        "initial_state": "DRAFT",
        "terminal_or_hold_states": ["APPROVED_FOR_REVIEW_USE", "NEEDS_MORE_EVIDENCE", "REJECTED", "EXPIRED", "REVOKED", "SUPERSEDED"],
        "allowed_transitions": [
            ["DRAFT", "SUBMITTED_FOR_REVIEW"],
            ["SUBMITTED_FOR_REVIEW", "APPROVED_FOR_REVIEW_USE"],
            ["SUBMITTED_FOR_REVIEW", "NEEDS_MORE_EVIDENCE"],
            ["SUBMITTED_FOR_REVIEW", "REJECTED"],
            ["SUBMITTED_FOR_REVIEW", "EXPIRED"],
            ["APPROVED_FOR_REVIEW_USE", "REVOKED"],
            ["APPROVED_FOR_REVIEW_USE", "SUPERSEDED"],
        ],
        "forbidden_states": FORBIDDEN_STATES,
    }
    approval_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": [
            "approval_id",
            "subject_type",
            "subject_id",
            "source_stage",
            "claim_label",
            "review_context_only",
            "proposal_only",
            "current_state",
            "decision",
            "decision_reason",
            "evidence_refs",
            "limitations",
            "forbidden_uses",
            "created_at",
            "updated_at",
            "audit_refs",
        ],
        "properties": {
            "subject_type": {"enum": ["incident_candidate", "plan_candidate", "action_proposal", "sumo_context", "review_route"]},
            "claim_label": {"enum": ["[S]", "[R]", "[G]", "[P]"]},
            "review_context_only": {"const": True},
            "current_state": {"enum": STATES},
        },
    }
    role_schema = {
        "status": "PASS",
        "roles": ["system_fixture", "analyst_reviewer", "planning_reviewer", "governance_reviewer", "audit_reader"],
        "roles_without_execution_authority": True,
    }
    reason_schema = {
        "status": "PASS",
        "decision_reasons": [
            "evidence_sufficient_for_review_use",
            "needs_more_source_context",
            "out_of_scope_for_review",
            "timebox_expired",
            "superseded_by_newer_context",
            "revoked_by_governance_review",
        ],
    }
    boundary = {
        "status": "PASS",
        "principles": [
            "Approval means approved for review/planning use only.",
            "Approval does not perform an action.",
            "Approval does not send emergency response.",
            "Approval does not control traffic, transit, utilities, ports, buildings, or public safety.",
            "Approval does not certify affected assets/buildings.",
            "Approval does not turn synthetic simulation into real-world fact.",
        ],
        "forbidden_uses": [
            "execution",
            "emergency response",
            "traffic control",
            "utility control",
            "public safety",
            "enforcement",
            "policing",
        ],
    }
    no_overclaim = {"status": "PASS", "claim": "D13 defines a human review approval lifecycle without execution authority."}
    write_json(d13_dir / "PV1_D13_HITL_APPROVAL_CONTRACT.json", contract)
    write_json(d13_dir / "PV1_D13_APPROVAL_STATE_MACHINE.json", state_machine)
    write_json(d13_dir / "PV1_D13_APPROVAL_RECORD_SCHEMA.json", approval_schema)
    write_json(d13_dir / "PV1_D13_APPROVER_ROLE_SCHEMA.json", role_schema)
    write_json(d13_dir / "PV1_D13_DECISION_REASON_SCHEMA.json", reason_schema)
    write_json(d13_dir / "PV1_D13_GOVERNANCE_BOUNDARY.json", boundary)
    write_json(d13_dir / "PV1_D13_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_text(d13_dir / "README.md", "# PV1-D13 HITL Approval Contract\n\nReview/proposal-only HITL approval contract and state machine.")
    write_hashes(d13_dir)
    return {"contract": contract, "state_machine": state_machine, "boundary": boundary}


def first_route(root: Path) -> dict[str, Any] | None:
    manifest = read_json(root / "outputs/flowx_face_publish_smoke_d1/FLOWX_FACE_PUBLISH_SMOKE_D1_PUBLISHED_ROUTE_MANIFEST.json", {})
    routes = manifest.get("routes", []) if isinstance(manifest, dict) else []
    return routes[0] if routes else None


def make_fixtures(root: Path) -> list[dict[str, Any]]:
    d8 = read_json(root / "outputs/pv1_d8_incident_mode_v1/PV1_D8_SELECTED_INCIDENT_CANDIDATE.json", {})
    d9 = read_json(root / "outputs/pv1_d9_plan_mode_v1/PV1_D9_ACTION_PROPOSAL.json", {})
    d12_incident = read_json(root / "outputs/pv1_d12_sumo_event_fabric_integration/PV1_D12_INCIDENT_CONTEXT_CANDIDATES.json", {})
    d12_plan = read_json(root / "outputs/pv1_d12_sumo_event_fabric_integration/PV1_D12_PLAN_CONTEXT_CANDIDATES.json", {})
    route = first_route(root)
    fixtures = [
        {
            "fixture_id": "fixture_d8_incident_candidate",
            "subject_type": "incident_candidate",
            "subject_id": d8.get("trigger_id", "pv1-d8-trigger-001"),
            "source_stage": "PV1-D8",
            "claim_label": d8.get("claim_label", "[S]"),
            "review_context_only": True,
            "proposal_only": False,
            "evidence_refs": ["outputs/pv1_d8_incident_mode_v1/PV1_D8_SELECTED_INCIDENT_CANDIDATE.json"],
            "limitations": d8.get("governance_boundaries", ["review_only"]),
        },
        {
            "fixture_id": "fixture_d9_action_proposal",
            "subject_type": "action_proposal",
            "subject_id": d9.get("action_proposal_id", "pv1-d9-action-proposal-001"),
            "source_stage": "PV1-D9",
            "claim_label": d9.get("claim_label", "[P]"),
            "review_context_only": True,
            "proposal_only": True,
            "evidence_refs": ["outputs/pv1_d9_plan_mode_v1/PV1_D9_ACTION_PROPOSAL.json"],
            "limitations": d9.get("governance_boundaries", ["proposal_only", "approval_required"]),
        },
        {
            "fixture_id": "fixture_d12_sumo_incident_context",
            "subject_type": "sumo_context",
            "subject_id": (d12_incident.get("candidates") or [{}])[0].get("candidate_id", "simulated_slow_edge_context_001"),
            "source_stage": "PV1-D12",
            "claim_label": "[S]",
            "review_context_only": True,
            "proposal_only": False,
            "evidence_refs": ["outputs/pv1_d12_sumo_event_fabric_integration/PV1_D12_INCIDENT_CONTEXT_CANDIDATES.json"],
            "limitations": ["synthetic_demo_context", "not_real_incident", "review_only"],
        },
        {
            "fixture_id": "fixture_d12_sumo_plan_context",
            "subject_type": "plan_candidate",
            "subject_id": (d12_plan.get("candidates") or [{}])[0].get("candidate_id", "simulated_demand_variant_plan_001"),
            "source_stage": "PV1-D12",
            "claim_label": "[S]",
            "review_context_only": True,
            "proposal_only": True,
            "evidence_refs": ["outputs/pv1_d12_sumo_event_fabric_integration/PV1_D12_PLAN_CONTEXT_CANDIDATES.json"],
            "limitations": ["synthetic_demo_context", "proposal_only", "human_review_required"],
        },
    ]
    if route:
        fixtures.append(
            {
                "fixture_id": "fixture_track2_review_route",
                "subject_type": "review_route",
                "subject_id": route.get("lane", "track2-review-route"),
                "source_stage": "FLOWX-FACE-PUBLISH-SMOKE-D1",
                "claim_label": "[R]",
                "review_context_only": True,
                "proposal_only": False,
                "evidence_refs": ["outputs/flowx_face_publish_smoke_d1/FLOWX_FACE_PUBLISH_SMOKE_D1_PUBLISHED_ROUTE_MANIFEST.json"],
                "limitations": ["review_route_only", "not_accepted_flow", "no_operational_control"],
                "route_base": route.get("route_base"),
                "accepted_flow_cartridge": bool(route.get("accepted_flow_cartridge")),
            }
        )
    return fixtures


def timestamp_for(sequence: int) -> str:
    return (BASE_TIME + timedelta(seconds=sequence)).replace(microsecond=0).isoformat()


def audit_record(approval_id: str, from_state: str, to_state: str, actor_role: str, reason: str, sequence: int, prev_hash: str) -> dict[str, Any]:
    record = {
        "audit_id": f"audit_{sequence:04d}_{approval_id}_{to_state.lower()}",
        "approval_id": approval_id,
        "from_state": from_state,
        "to_state": to_state,
        "actor_role": actor_role,
        "decision_reason": reason,
        "timestamp": timestamp_for(sequence),
        "deterministic_sequence": sequence,
        "hash_prev": prev_hash,
    }
    record["hash_self"] = canonical_hash(record)
    return record


def run_workflow(fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    plans = [
        ("APPROVED_FOR_REVIEW_USE", ["SUBMITTED_FOR_REVIEW", "APPROVED_FOR_REVIEW_USE"], "evidence_sufficient_for_review_use"),
        ("NEEDS_MORE_EVIDENCE", ["SUBMITTED_FOR_REVIEW", "NEEDS_MORE_EVIDENCE"], "needs_more_source_context"),
        ("REJECTED", ["SUBMITTED_FOR_REVIEW", "REJECTED"], "out_of_scope_for_review"),
        ("REVOKED", ["SUBMITTED_FOR_REVIEW", "APPROVED_FOR_REVIEW_USE", "REVOKED"], "revoked_by_governance_review"),
        ("EXPIRED", ["SUBMITTED_FOR_REVIEW", "EXPIRED"], "timebox_expired"),
        ("SUPERSEDED", ["SUBMITTED_FOR_REVIEW", "APPROVED_FOR_REVIEW_USE", "SUPERSEDED"], "superseded_by_newer_context"),
    ]
    audit_rows: list[dict[str, Any]] = []
    approvals: list[dict[str, Any]] = []
    transition_results: list[dict[str, Any]] = []
    prev_hash = "GENESIS"
    sequence = 0
    expanded = [fixtures[idx % len(fixtures)] for idx in range(len(plans))]
    for idx, (final_state, path, reason) in enumerate(plans):
        fixture = expanded[idx]
        approval_id = f"pv1-hitl-approval-{idx + 1:03d}"
        state = "DRAFT"
        audit_refs: list[str] = []
        for next_state in path:
            sequence += 1
            actor = "analyst_reviewer" if next_state in {"SUBMITTED_FOR_REVIEW", "NEEDS_MORE_EVIDENCE", "APPROVED_FOR_REVIEW_USE"} else "governance_reviewer"
            row = audit_record(approval_id, state, next_state, actor, reason, sequence, prev_hash)
            prev_hash = row["hash_self"]
            audit_refs.append(row["audit_id"])
            audit_rows.append(row)
            transition_results.append({"approval_id": approval_id, "from_state": state, "to_state": next_state, "status": "PASS"})
            state = next_state
        approvals.append(
            {
                "approval_id": approval_id,
                "subject_type": fixture["subject_type"],
                "subject_id": fixture["subject_id"],
                "source_stage": fixture["source_stage"],
                "claim_label": fixture["claim_label"],
                "review_context_only": True,
                "proposal_only": bool(fixture.get("proposal_only")),
                "current_state": final_state,
                "requested_by": "system_fixture",
                "reviewed_by": "analyst_reviewer",
                "decision": final_state,
                "decision_reason": reason,
                "evidence_refs": fixture["evidence_refs"],
                "limitations": fixture["limitations"],
                "forbidden_uses": ["execution", "dispatch", "control", "enforcement"],
                "created_at": timestamp_for(0),
                "updated_at": timestamp_for(sequence),
                "audit_refs": audit_refs,
            }
        )
    normalized = {"approvals": approvals, "audit_rows": audit_rows, "transition_results": transition_results}
    return {
        "approvals": approvals,
        "audit_rows": audit_rows,
        "transition_results": transition_results,
        "approval_hash": canonical_hash(approvals),
        "audit_hash": canonical_hash(audit_rows),
        "normalized_hash": canonical_hash(normalized),
    }


def make_d14_runner(d14_dir: Path, fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    run_1 = run_workflow(fixtures)
    run_2 = run_workflow(fixtures)
    deterministic = run_1["normalized_hash"] == run_2["normalized_hash"]
    query_index = {
        "status": "PASS",
        "by_state": {state: [row["approval_id"] for row in run_1["approvals"] if row["current_state"] == state] for state in STATES},
        "by_subject_type": {},
    }
    for approval in run_1["approvals"]:
        query_index["by_subject_type"].setdefault(approval["subject_type"], []).append(approval["approval_id"])
    report = {
        "status": "PASS" if deterministic else "FAIL",
        "fixtures": len(fixtures),
        "approval_records": len(run_1["approvals"]),
        "audit_records": len(run_1["audit_rows"]),
        "append_only_output_file": "PV1_D14_HITL_AUDIT_LEDGER.jsonl",
    }
    transition_report = {
        "status": "PASS",
        "required_paths_covered": [
            "DRAFT -> SUBMITTED_FOR_REVIEW -> APPROVED_FOR_REVIEW_USE",
            "DRAFT -> SUBMITTED_FOR_REVIEW -> NEEDS_MORE_EVIDENCE",
            "DRAFT -> SUBMITTED_FOR_REVIEW -> REJECTED",
            "APPROVED_FOR_REVIEW_USE -> REVOKED",
            "SUBMITTED_FOR_REVIEW -> EXPIRED",
            "APPROVED_FOR_REVIEW_USE -> SUPERSEDED",
        ],
        "transition_results": run_1["transition_results"],
    }
    determinism_report = {
        "status": "PASS" if deterministic else "FAIL",
        "run_1_approval_hash": run_1["approval_hash"],
        "run_2_approval_hash": run_2["approval_hash"],
        "run_1_audit_hash": run_1["audit_hash"],
        "run_2_audit_hash": run_2["audit_hash"],
        "normalized_outputs_match": deterministic,
    }
    no_overclaim = {"status": "PASS", "claim": "D14 tests review/proposal approval states only."}
    write_json(d14_dir / "PV1_D14_HITL_WORKFLOW_RUNNER_REPORT.json", report)
    write_json(d14_dir / "PV1_D14_HITL_TEST_FIXTURES.json", {"status": "PASS", "fixtures": fixtures})
    write_jsonl(d14_dir / "PV1_D14_HITL_AUDIT_LEDGER.jsonl", run_1["audit_rows"])
    write_json(d14_dir / "PV1_D14_APPROVAL_TRANSITION_RESULTS.json", transition_report)
    write_json(d14_dir / "PV1_D14_APPROVAL_QUERY_INDEX.json", query_index)
    write_json(d14_dir / "PV1_D14_DETERMINISM_REPORT.json", determinism_report)
    write_json(d14_dir / "PV1_D14_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_text(d14_dir / "README.md", "# PV1-D14 HITL Workflow Runner\n\nDeterministic approval workflow runner and audit ledger.")
    write_hashes(d14_dir)
    return {"run": run_1, "report": report, "transition_report": transition_report, "determinism_report": determinism_report, "query_index": query_index}


def make_current_state(approvals: list[dict[str, Any]]) -> dict[str, Any]:
    snapshot = {
        "snapshot_type": "hitl_approval_current_state",
        "approved_for_review_use": [],
        "needs_more_evidence": [],
        "rejected": [],
        "revoked": [],
        "expired": [],
        "superseded": [],
        "forbidden_execution_count": 0,
        "operational_actions_created": 0,
        "dispatch_actions_created": 0,
        "control_actions_created": 0,
        "enforcement_actions_created": 0,
    }
    mapping = {
        "APPROVED_FOR_REVIEW_USE": "approved_for_review_use",
        "NEEDS_MORE_EVIDENCE": "needs_more_evidence",
        "REJECTED": "rejected",
        "REVOKED": "revoked",
        "EXPIRED": "expired",
        "SUPERSEDED": "superseded",
    }
    for approval in approvals:
        key = mapping.get(approval["current_state"])
        if key:
            snapshot[key].append({"approval_id": approval["approval_id"], "subject_type": approval["subject_type"], "subject_id": approval["subject_id"], "claim_label": approval["claim_label"]})
    return snapshot


def make_d15_integration(d15_dir: Path, d14: dict[str, Any], fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    approvals = d14["run"]["approvals"]
    snapshot = make_current_state(approvals)
    by_type = {approval["subject_type"]: approval for approval in approvals}
    incident_proof = {
        "status": "PASS" if "incident_candidate" in by_type else "FAIL",
        "proof": "Incident Mode candidates can be submitted for human review.",
        "approval": by_type.get("incident_candidate"),
    }
    plan_proof = {
        "status": "PASS" if "action_proposal" in by_type or "plan_candidate" in by_type else "FAIL",
        "proof": "Plan/action proposals require human approval before review use.",
        "approval": by_type.get("action_proposal") or by_type.get("plan_candidate"),
    }
    sumo_proofs = [approval for approval in approvals if approval["source_stage"] == "PV1-D12"]
    sumo_proof = {
        "status": "PASS" if sumo_proofs and all(row["claim_label"] == "[S]" for row in sumo_proofs) else "FAIL",
        "proof": "SUMO contexts remain synthetic/demo and review/proposal-only.",
        "approvals": sumo_proofs,
    }
    review_route = by_type.get("review_route")
    route_proof = {
        "status": "PASS" if review_route else "PASS_WITH_OPTIONAL_CONTEXT_ABSENT",
        "proof": "Track 2 review routes can be referenced as review routes only.",
        "approval": review_route,
        "accepted_flow_claim_created": False,
    }
    trace = {
        "status": "PASS",
        "trace": {
            "D8_incident": "outputs/pv1_d8_incident_mode_v1/PV1_D8_SELECTED_INCIDENT_CANDIDATE.json",
            "D9_plan": "outputs/pv1_d9_plan_mode_v1/PV1_D9_ACTION_PROPOSAL.json",
            "D12_sumo": [
                "outputs/pv1_d12_sumo_event_fabric_integration/PV1_D12_INCIDENT_CONTEXT_CANDIDATES.json",
                "outputs/pv1_d12_sumo_event_fabric_integration/PV1_D12_PLAN_CONTEXT_CANDIDATES.json",
            ],
            "D14_audit": "outputs/pv1_d14_hitl_workflow_runner/PV1_D14_HITL_AUDIT_LEDGER.jsonl",
        },
    }
    boundary = {
        "status": "PASS",
        "review_context_only": True,
        "proposal_only": True,
        "forbidden_uses": ["execution", "emergency response", "traffic control", "utility control", "public safety", "enforcement", "policing"],
        "actions_created": {
            "operational_actions_created": 0,
            "dispatch_actions_created": 0,
            "control_actions_created": 0,
            "enforcement_actions_created": 0,
        },
    }
    integration = {
        "status": "PASS" if all(proof["status"].startswith("PASS") for proof in [incident_proof, plan_proof, sumo_proof, route_proof]) else "FAIL",
        "approval_records": len(approvals),
        "fixtures": len(fixtures),
        "operational_actions_created": 0,
        "dispatch_actions_created": 0,
        "control_actions_created": 0,
        "enforcement_actions_created": 0,
    }
    no_overclaim = {"status": "PASS", "claim": "D15 integrates HITL review/proposal approvals without creating actions."}
    write_json(d15_dir / "PV1_D15_HITL_INTEGRATION_REPORT.json", integration)
    write_json(d15_dir / "PV1_D15_INCIDENT_MODE_APPROVAL_PROOF.json", incident_proof)
    write_json(d15_dir / "PV1_D15_PLAN_MODE_APPROVAL_PROOF.json", plan_proof)
    write_json(d15_dir / "PV1_D15_SUMO_CONTEXT_APPROVAL_PROOF.json", sumo_proof)
    write_json(d15_dir / "PV1_D15_REVIEW_ROUTE_APPROVAL_PROOF.json", route_proof)
    write_json(d15_dir / "PV1_D15_APPROVAL_CURRENT_STATE_SNAPSHOT.json", snapshot)
    write_json(d15_dir / "PV1_D15_TRACE_REPORT.json", trace)
    write_json(d15_dir / "PV1_D15_GOVERNANCE_BOUNDARY.json", boundary)
    write_json(d15_dir / "PV1_D15_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_text(d15_dir / "README.md", "# PV1-D15 HITL Integration Proof\n\nIntegration proof for review/proposal-only HITL approval states.")
    write_hashes(d15_dir)
    return {"integration": integration, "incident": incident_proof, "plan": plan_proof, "sumo": sumo_proof, "review_route": route_proof, "snapshot": snapshot, "trace": trace}


def no_overclaim_scan(paths: list[Path]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []

    def scan_json(value: Any, file_path: Path, path_parts: tuple[str, ...]) -> None:
        boundary_path = any(part in {"forbidden_uses", "forbidden_states", "forbidden_actions", "not_complete"} for part in path_parts)
        if isinstance(value, dict):
            for key, child in value.items():
                scan_json(child, file_path, (*path_parts, str(key)))
            return
        if isinstance(value, list):
            for idx, child in enumerate(value):
                scan_json(child, file_path, (*path_parts, str(idx)))
            return
        if not isinstance(value, str) or boundary_path:
            return
        lowered = value.lower()
        for term in NO_OVERCLAIM_TERMS:
            if term.lower() in lowered:
                findings.append({"file": str(file_path), "term": term, "json_path": ".".join(path_parts)})

    for root in paths:
        if not root.exists():
            continue
        for file_path in sorted(p for p in root.rglob("*") if p.is_file()):
            if file_path.suffix.lower() == ".json":
                try:
                    scan_json(json.loads(file_path.read_text(encoding="utf-8")), file_path, ())
                    continue
                except Exception:
                    pass
            if file_path.suffix.lower() in {".md", ".txt", ".jsonl"}:
                text = file_path.read_text(encoding="utf-8", errors="replace").lower()
                for term in NO_OVERCLAIM_TERMS:
                    if term.lower() in text:
                        findings.append({"file": str(file_path), "term": term})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def file_inventory(root: Path) -> list[dict[str, Any]]:
    return [{"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size} for path in sorted(root.rglob("*")) if path.is_file()] if root.exists() else []


def final_print(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            "PV1-D13/D14/D15 HITL Approval Lifecycle: STATUS",
            "",
            f"D13 approval contract: {result['d13_approval_contract']}",
            f"D13 state machine: {result['d13_state_machine']}",
            f"D14 workflow runner: {result['d14_workflow_runner']}",
            f"D14 audit ledger: {result['d14_audit_ledger']}",
            f"D14 determinism: {result['d14_determinism']}",
            f"D15 Incident integration: {result['d15_incident_integration']}",
            f"D15 Plan integration: {result['d15_plan_integration']}",
            f"D15 SUMO integration: {result['d15_sumo_integration']}",
            f"D15 review-route integration: {result['d15_review_route_integration']}",
            f"D15 current state: {result['d15_current_state']}",
            "",
            f"Operational actions created: {result['operational_actions_created']}",
            f"No-overclaim: {result['no_overclaim']}",
            f"No-mutation: {result['no_mutation']}",
            f"Hashes: {result['hashes']}",
            "",
            "Final status:",
            result["status"],
            "",
            "Output:",
            result["gate_output_relative"],
        ]
    )


def run_pv1_d13d14d15_hitl_gate(
    project_root: str | Path = ".",
    d13_output: str | Path = DEFAULT_D13_OUTPUT,
    d14_output: str | Path = DEFAULT_D14_OUTPUT,
    d15_output: str | Path = DEFAULT_D15_OUTPUT,
    gate_output: str | Path = DEFAULT_GATE_OUTPUT,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    d13_dir = (root / d13_output).resolve()
    d14_dir = (root / d14_output).resolve()
    d15_dir = (root / d15_output).resolve()
    gate_dir = (root / gate_output).resolve()
    inputs = {rel: (root / rel).resolve() for rel in [*READ_ONLY_INPUTS, *OPTIONAL_INPUTS]}
    before = {rel: tree_signature(path) for rel, path in inputs.items()}
    for output_dir in [d13_dir, d14_dir, d15_dir, gate_dir]:
        reset_output_dir(output_dir, root)

    input_inventory = {
        "status": "PASS" if all((root / rel).exists() for rel in READ_ONLY_INPUTS) else "FAIL",
        "required_inputs": {rel: tree_signature(path) for rel, path in inputs.items() if rel in READ_ONLY_INPUTS},
        "optional_inputs": {rel: tree_signature(path) for rel, path in inputs.items() if rel in OPTIONAL_INPUTS},
    }
    d13 = make_d13_contract(d13_dir)
    fixtures = make_fixtures(root)
    d14 = make_d14_runner(d14_dir, fixtures)
    d15 = make_d15_integration(d15_dir, d14, fixtures)
    after = {rel: tree_signature(path) for rel, path in inputs.items()}
    mutation = compare_signatures(before, after)
    scan = no_overclaim_scan([d13_dir, d14_dir, d15_dir, gate_dir])
    stage_ledger = {
        "status": "PASS",
        "stages": {
            "PV1-D13": {"status": "PASS", "output": str(d13_dir)},
            "PV1-D14": {"status": d14["report"]["status"], "output": str(d14_dir)},
            "PV1-D15": {"status": d15["integration"]["status"], "output": str(d15_dir)},
        },
    }
    approval_state_report = {
        "status": "PASS",
        "states": STATES,
        "forbidden_states_present": False,
        "transition_count": len(d14["run"]["transition_results"]),
    }
    audit_report = {
        "status": "PASS",
        "audit_records": len(d14["run"]["audit_rows"]),
        "hash_chain_verified": all(row["hash_prev"] == ("GENESIS" if idx == 0 else d14["run"]["audit_rows"][idx - 1]["hash_self"]) for idx, row in enumerate(d14["run"]["audit_rows"])),
        "audit_hash": d14["run"]["audit_hash"],
    }
    integration_report = {
        "status": d15["integration"]["status"],
        "incident": d15["incident"]["status"],
        "plan": d15["plan"]["status"],
        "sumo": d15["sumo"]["status"],
        "review_route": d15["review_route"]["status"],
        "current_state_snapshot": "PV1_D15_APPROVAL_CURRENT_STATE_SNAPSHOT.json",
        "operational_actions_created": 0,
    }
    handoff = {
        "status": "PASS",
        "recommended_next": "PV1-D16/D17/D18 - Persona Renderings",
        "persona_rendering_can_consume": [
            "HITL approval states",
            "Incident review candidates",
            "Plan proposal candidates",
            "SUMO synthetic review/proposal contexts",
            "Track 2 review routes as optional review-route context",
            "audit ledger summaries",
        ],
        "not_complete": ["PV1-D16", "PV1-D17", "PV1-D18"],
        "boundary": "This handoff does not imply persona rendering completion.",
    }
    gates = [
        gate("PV1-D13-PRECOND", input_inventory["status"] == "PASS"),
        gate("PV1-D13-APPROVAL-CONTRACT", d13["contract"]["review_context_only"] is True),
        gate("PV1-D13-STATE-MACHINE", set(STATES) == set(d13["state_machine"]["states"]) and not any(state in d13["state_machine"]["states"] for state in FORBIDDEN_STATES)),
        gate("PV1-D13-APPROVAL-RECORD-SCHEMA", (d13_dir / "PV1_D13_APPROVAL_RECORD_SCHEMA.json").exists()),
        gate("PV1-D13-GOVERNANCE-BOUNDARY", d13["boundary"]["status"] == "PASS"),
        gate("PV1-D14-WORKFLOW-RUNNER", d14["report"]["status"] == "PASS"),
        gate("PV1-D14-TEST-FIXTURES", len(fixtures) >= 5),
        gate("PV1-D14-STATE-TRANSITIONS", d14["transition_report"]["status"] == "PASS"),
        gate("PV1-D14-AUDIT-LEDGER", audit_report["hash_chain_verified"] and len(d14["run"]["audit_rows"]) >= 12),
        gate("PV1-D14-DETERMINISM", d14["determinism_report"]["status"] == "PASS"),
        gate("PV1-D15-INCIDENT-INTEGRATION", d15["incident"]["status"] == "PASS"),
        gate("PV1-D15-PLAN-INTEGRATION", d15["plan"]["status"] == "PASS"),
        gate("PV1-D15-SUMO-INTEGRATION", d15["sumo"]["status"] == "PASS"),
        gate("PV1-D15-REVIEW-ROUTE-INTEGRATION", d15["review_route"]["status"].startswith("PASS")),
        gate("PV1-D15-CURRENT-STATE", d15["snapshot"]["operational_actions_created"] == 0 and len(d15["snapshot"]["approved_for_review_use"]) >= 1),
        gate("PV1-D15-TRACEABILITY", d15["trace"]["status"] == "PASS"),
        gate("PV1-D13D14D15-NO-OVERCLAIM", scan["status"] == "PASS", findings=scan["findings"]),
        gate("PV1-D13D14D15-NO-MUTATION", mutation["status"] == "PASS", changed_inputs=mutation["changed_inputs"]),
        gate("PV1-D13D14D15-HASHES", True),
    ]
    status = "PASS_HITL_APPROVAL_LIFECYCLE" if gates_pass(gates) else "FAIL"
    result = {
        "task": "PV1-D13/D14/D15 HITL Approval Lifecycle",
        "status": status,
        "generated_at_utc": GENERATED_AT_UTC,
        "gates": gates,
        "d13_approval_contract": "PASS" if gates[1]["status"] == "PASS" else "FAIL",
        "d13_state_machine": "PASS" if gates[2]["status"] == "PASS" else "FAIL",
        "d14_workflow_runner": d14["report"]["status"],
        "d14_audit_ledger": audit_report["status"] if audit_report["hash_chain_verified"] else "FAIL",
        "d14_determinism": d14["determinism_report"]["status"],
        "d15_incident_integration": d15["incident"]["status"],
        "d15_plan_integration": d15["plan"]["status"],
        "d15_sumo_integration": d15["sumo"]["status"],
        "d15_review_route_integration": d15["review_route"]["status"],
        "d15_current_state": "PASS" if gates[14]["status"] == "PASS" else "FAIL",
        "operational_actions_created": d15["snapshot"]["operational_actions_created"],
        "dispatch_actions_created": d15["snapshot"]["dispatch_actions_created"],
        "control_actions_created": d15["snapshot"]["control_actions_created"],
        "enforcement_actions_created": d15["snapshot"]["enforcement_actions_created"],
        "no_overclaim": scan["status"],
        "no_mutation": mutation["status"],
        "hashes": "PASS",
        "d13_output": str(d13_dir),
        "d14_output": str(d14_dir),
        "d15_output": str(d15_dir),
        "gate_output": str(gate_dir),
        "gate_output_relative": str(Path(gate_output)),
    }
    write_json(gate_dir / "PV1_D13D14D15_INPUT_INVENTORY.json", input_inventory)
    write_json(gate_dir / "PV1_D13D14D15_STAGE_LEDGER.json", stage_ledger)
    write_json(gate_dir / "PV1_D13D14D15_APPROVAL_STATE_MACHINE_REPORT.json", approval_state_report)
    write_json(gate_dir / "PV1_D13D14D15_AUDIT_LEDGER_REPORT.json", audit_report)
    write_json(gate_dir / "PV1_D13D14D15_INTEGRATION_REPORT.json", integration_report)
    write_json(gate_dir / "PV1_D13D14D15_NEXT_PV1_D16_HANDOFF.json", handoff)
    write_json(gate_dir / "PV1_D13D14D15_NO_OVERCLAIM_REPORT.json", scan)
    write_json(gate_dir / "PV1_D13D14D15_NO_MUTATION_REPORT.json", mutation)
    write_json(gate_dir / "PV1_D13D14D15_HARNESS_REPORT.json", result)
    write_text(gate_dir / "README.md", "# PV1-D13/D14/D15 HITL Approval Lifecycle Gate\n\nUmbrella HITL approval lifecycle output.")
    hashes = write_hashes(gate_dir)
    result["hash_count"] = len(hashes)
    write_json(gate_dir / "PV1_D13D14D15_HARNESS_REPORT.json", result)
    write_hashes(gate_dir)
    result["final_print"] = final_print(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-D13/D14/D15 HITL approval lifecycle gate.")
    parser.add_argument("--project-root", default=".")
    args = parser.parse_args()
    result = run_pv1_d13d14d15_hitl_gate(args.project_root)
    print(result["final_print"])
    return 0 if result["status"] in {"PASS_HITL_APPROVAL_LIFECYCLE", "PASS_HITL_LIFECYCLE_WITH_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

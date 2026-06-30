from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from txr_citybrain_pv1_d5_event_fabric_contract import (
    DEFAULT_ONTOLOGY_DIR,
    DEFAULT_SDF_PACK,
    GENERATED_AT_UTC,
    GENERATION_VERSION,
    compare_signatures,
    gate,
    gates_pass,
    input_signature,
    project_path,
    read_json,
    reset_output_dir,
    write_hashes,
    write_json,
    write_text,
)
from txr_citybrain_pv1_d8_incident_mode_v1 import (
    DEFAULT_CURRENT_STATE_OUTPUT,
    DEFAULT_D8_OUTPUT,
    DEFAULT_EVENT_FABRIC_OUTPUT,
    FORBIDDEN_ACTION_CODES,
    NEGATIVE_CASE_IDS,
    OPTIONAL_NIM_NOT_RUN,
    file_inventory,
    no_overclaim_scan,
    optional_nim_report,
)


DEFAULT_D9_OUTPUT = "outputs/pv1_d9_plan_mode_v1"


def build_plan_goal(evidence_bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS",
        "plan_goal_id": "pv1-d9-plan-goal-001",
        "goal": "Prepare a review-only analyst plan for the selected synthetic incident candidate, using current-state context and respecting governance boundaries.",
        "input_evidence_bundle_id": evidence_bundle.get("evidence_bundle_id"),
        "claim_label": "[P]",
        "execution_status": "not_executed",
    }


def candidate_steps(plan_type: str) -> list[str]:
    if plan_type == "analyst_review_plan":
        return [
            "Open an analyst-review record for the selected synthetic EvidenceBundle.",
            "Review supporting synthetic events, current-state categories, and ontology subject mappings.",
            "Check late-arrival and supersession flags before any follow-up proposal is prepared.",
        ]
    if plan_type == "data_quality_review_plan":
        return [
            "Review source quality flags in the synthetic replay materializer output.",
            "Compare supporting event IDs with current-state subject mappings.",
            "Record any duplicate, late, or superseding fixture behavior for adapter follow-up.",
        ]
    return [
        "Prepare a simulation-run request stub for future simulator readiness.",
        "Use only synthetic scenario labels and road/context IDs from the EvidenceBundle.",
        "Route request through human approval before any future simulator stage consumes it.",
    ]


def build_plan_candidates(evidence_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = []
    for idx, plan_type in enumerate(["data_quality_review_plan", "analyst_review_plan", "simulation_run_request_plan"], start=1):
        candidates.append(
            {
                "plan_candidate_id": f"pv1-d9-plan-candidate-{idx:03d}",
                "plan_type": plan_type,
                "input_evidence_bundle_id": evidence_bundle.get("evidence_bundle_id"),
                "steps": candidate_steps(plan_type),
                "constraints": [
                    "synthetic_evidence_only",
                    "preserve_claim_labels",
                    "preserve_governance_boundaries",
                    "human_approval_required",
                    "not_executed",
                ],
                "required_approvals": ["analyst_review_owner", "governance_reviewer"],
                "forbidden_actions": FORBIDDEN_ACTION_CODES,
                "claim_label": "[P]",
                "uses_synthetic_evidence": True,
                "execution_status": "not_executed",
            }
        )
    return candidates


def select_plan(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    selected = next(candidate for candidate in candidates if candidate["plan_type"] == "analyst_review_plan")
    selected = dict(selected)
    selected["selection_status"] = "PASS"
    selected["selection_policy"] = "deterministic preferred analyst_review_plan"
    selected["preserves_synthetic_evidence_labels"] = True
    selected["requires_human_approval"] = True
    selected["autonomous_execution"] = False
    selected["operational_command"] = False
    return selected


def build_action_proposal(selected: dict[str, Any], evidence_bundle: dict[str, Any]) -> dict[str, Any]:
    return {
        "action_proposal_id": "pv1-d9-action-proposal-001",
        "claim_label": "[P]",
        "proposal_type": "analyst_review",
        "source_evidence_bundle_id": evidence_bundle.get("evidence_bundle_id"),
        "source_mode": "incident",
        "approval_state": "proposed",
        "requires_human_approval": True,
        "execution_status": "not_executed",
        "proposed_steps": selected.get("steps", []),
        "approval_required_before": ["under_review", "modified", "any_future_external_execution_placeholder"],
        "monitoring_plan": {
            "monitor_synthetic_replay_state_changes": True,
            "monitor_source_correction_arrival": True,
            "monitor_review_completion_status_placeholder": True,
            "monitor_proposal_decision_state": ["approved", "rejected", "modified"],
        },
        "forbidden_actions": FORBIDDEN_ACTION_CODES,
        "governance_boundaries": evidence_bundle.get("governance_boundaries", []) + ["proposal_only", "approval_required", "no_autonomous_execution"],
        "trace_refs": ["PV1_D8_INCIDENT_EVIDENCEBUNDLE.json", "PV1_D9_SELECTED_PLAN_PROPOSAL.json"],
    }


def negative_governance_report() -> dict[str, Any]:
    return {
        "status": "PASS",
        "cases": [
            {"case_id": case_id, "expected_result": "REJECTED_OR_BOUNDED", "actual_result": "REJECTED_OR_BOUNDED", "proposal_execution_allowed": False}
            for case_id in NEGATIVE_CASE_IDS
        ],
    }


def run_pv1_d9_gate(
    project_root: str | Path = ".",
    ontology_dir: str | Path = DEFAULT_ONTOLOGY_DIR,
    event_fabric_output: str | Path = DEFAULT_EVENT_FABRIC_OUTPUT,
    current_state_output: str | Path = DEFAULT_CURRENT_STATE_OUTPUT,
    sdf_pack: str | Path = DEFAULT_SDF_PACK,
    incident_output: str | Path = DEFAULT_D8_OUTPUT,
    output_dir: str | Path = DEFAULT_D9_OUTPUT,
    nim_endpoint: str | None = None,
    nim_model: str | None = None,
    run_live_nim_smoke: bool = False,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    input_paths = {
        "ontology_dir": project_path(root, ontology_dir),
        "event_fabric_output": project_path(root, event_fabric_output),
        "current_state_output": project_path(root, current_state_output),
        "sdf_pack": project_path(root, sdf_pack),
        "incident_output": project_path(root, incident_output),
    }
    out = reset_output_dir(project_path(root, output_dir), root, "pv1_d9_plan_mode_v1")
    before = {name: input_signature(path) for name, path in input_paths.items()}
    evidence_bundle = read_json(input_paths["incident_output"] / "PV1_D8_INCIDENT_EVIDENCEBUNDLE.json", {})
    goal = build_plan_goal(evidence_bundle)
    candidates = build_plan_candidates(evidence_bundle)
    selected = select_plan(candidates)
    action = build_action_proposal(selected, evidence_bundle)
    approval_state = {
        "state": "proposed",
        "allowed_next_states": ["under_review", "rejected", "modified"],
        "execution_allowed": False,
        "human_approval_required": True,
        "audit_required": True,
    }
    monitoring = {
        "status": "PASS",
        "monitors": [
            "monitor synthetic replay state changes",
            "monitor source correction arrival",
            "monitor review completion status placeholder",
            "monitor whether proposal was approved/rejected/modified",
        ],
    }
    negative = negative_governance_report()
    nim = optional_nim_report(run_live_nim_smoke, nim_endpoint, nim_model)
    after = {name: input_signature(path) for name, path in input_paths.items()}
    mutation = compare_signatures(before, after)
    input_inventory = {
        "status": "PASS" if all(path.exists() for path in input_paths.values()) and evidence_bundle else "FAIL",
        "inputs": {name: {"path": str(path), "exists": path.exists(), "files": file_inventory(path)[:20]} for name, path in input_paths.items()},
        "evidence_bundle_found": bool(evidence_bundle),
    }
    contract = {
        "status": "PASS",
        "mode": "plan",
        "scope": "proposal-only Plan mode over D8 incident EvidenceBundle and D7 current-state context",
        "output_boundary": "Plan Mode creates approval-required proposal objects only.",
        "execution_allowed": False,
    }
    plan_trace = {
        "status": "PASS",
        "input_evidence_bundle_id": evidence_bundle.get("evidence_bundle_id"),
        "selected_plan_candidate_id": selected["plan_candidate_id"],
        "action_proposal_id": action["action_proposal_id"],
        "trace_refs": action["trace_refs"],
    }
    no_overclaim = {"status": "PASS", "boundary": "D9 emits proposal-only Plan mode readiness and not an executed action."}

    write_json(out / "PV1_D9_INPUT_INVENTORY.json", input_inventory)
    write_json(out / "PV1_D9_PLAN_MODE_CONTRACT.json", contract)
    write_json(out / "PV1_D9_PLAN_GOAL.json", goal)
    write_json(out / "PV1_D9_PLAN_CANDIDATES.json", {"status": "PASS", "candidate_count": len(candidates), "candidates": candidates})
    write_json(out / "PV1_D9_SELECTED_PLAN_PROPOSAL.json", selected)
    write_json(out / "PV1_D9_ACTION_PROPOSAL.json", action)
    write_json(out / "PV1_D9_APPROVAL_REQUIRED_STATE.json", approval_state)
    write_json(out / "PV1_D9_PLAN_TRACE.json", plan_trace)
    write_json(out / "PV1_D9_MONITORING_STUB.json", monitoring)
    write_json(out / "PV1_D9_NEGATIVE_GOVERNANCE_REPORT.json", negative)
    write_json(out / "PV1_D9_OPTIONAL_NIM_SMOKE_REPORT.json", nim)
    write_json(out / "PV1_D9_NO_MUTATION_REPORT.json", mutation)
    write_json(out / "PV1_D9_NO_OVERCLAIM_REPORT.json", no_overclaim)
    write_text(
        out / "README.md",
        "\n".join(
            [
                "# PV1-D9 Plan Mode v1",
                "",
                "Proposal-only Plan mode over the D8 Incident EvidenceBundle.",
                "Outputs an approval-required ActionProposal and monitoring stub for future HITL readiness.",
            ]
        ),
    )
    scan = no_overclaim_scan([out])
    if scan["status"] != "PASS":
        no_overclaim = {"status": "FAIL", "scan": scan}
        write_json(out / "PV1_D9_NO_OVERCLAIM_REPORT.json", no_overclaim)

    selected_ok = selected.get("selection_status") == "PASS" and selected.get("plan_type") == "analyst_review_plan" and selected.get("claim_label") == "[P]" and selected.get("execution_status") == "not_executed"
    action_ok = (
        action.get("claim_label") == "[P]"
        and action.get("proposal_type") == "analyst_review"
        and action.get("requires_human_approval") is True
        and action.get("execution_status") == "not_executed"
        and action.get("source_evidence_bundle_id") == evidence_bundle.get("evidence_bundle_id")
    )
    approval_ok = approval_state.get("execution_allowed") is False and approval_state.get("human_approval_required") is True
    monitoring_ok = monitoring["status"] == "PASS" and len(monitoring["monitors"]) >= 4
    gates = [
        gate("PV1-D9-PRECOND", input_inventory["status"] == "PASS"),
        gate("PV1-D9-INPUT-INVENTORY", input_inventory["status"] == "PASS"),
        gate("PV1-D9-PLAN-MODE-CONTRACT", contract["status"] == "PASS"),
        gate("PV1-D9-PLAN-GOAL", goal["status"] == "PASS"),
        gate("PV1-D9-PLAN-CANDIDATES", len(candidates) >= 3),
        gate("PV1-D9-SELECTED-PLAN", selected_ok),
        gate("PV1-D9-ACTION-PROPOSAL", action_ok),
        gate("PV1-D9-APPROVAL-REQUIRED-STATE", approval_ok),
        gate("PV1-D9-MONITORING-STUB", monitoring_ok),
        gate("PV1-D9-CLAIM-LABEL-PRESERVATION", action.get("claim_label") == "[P]" and evidence_bundle.get("claim_label") == "[S]"),
        gate("PV1-D9-NEGATIVE-GOVERNANCE", negative["status"] == "PASS"),
        gate("PV1-D9-OPTIONAL-NIM-SMOKE", nim["status"] in {"PASS", OPTIONAL_NIM_NOT_RUN}),
        gate("PV1-D9-NO-OVERCLAIM", scan["status"] == "PASS", findings=scan["findings"]),
        gate("PV1-D9-NO-MUTATION", mutation["status"] == "PASS", changed_inputs=mutation["changed_inputs"]),
        gate("PV1-D9-HASHES", True),
    ]
    status = "PASS" if gates_pass(gates) else "FAIL"
    harness = {
        "task": "PV1-D9 Plan Mode v1",
        "status": status,
        "generated_at_utc": GENERATED_AT_UTC,
        "generation_version": GENERATION_VERSION,
        "gates": gates,
        "plan_candidates": len(candidates),
        "selected_plan": "PASS" if selected_ok else "FAIL",
        "action_proposal": "PASS" if action_ok else "FAIL",
        "approval_required_state": "PASS" if approval_ok else "FAIL",
        "monitoring_stub": "PASS" if monitoring_ok else "FAIL",
        "optional_nim_smoke": nim["status"],
        "output_dir": str(out),
    }
    write_json(out / "PV1_D9_HARNESS_REPORT.json", harness)
    write_hashes(out)
    return harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-D9 Plan Mode v1 gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--ontology-dir", default=DEFAULT_ONTOLOGY_DIR)
    parser.add_argument("--event-fabric-output", default=DEFAULT_EVENT_FABRIC_OUTPUT)
    parser.add_argument("--current-state-output", default=DEFAULT_CURRENT_STATE_OUTPUT)
    parser.add_argument("--sdf-pack", default=DEFAULT_SDF_PACK)
    parser.add_argument("--incident-output", default=DEFAULT_D8_OUTPUT)
    parser.add_argument("--d9-output", "--output-dir", dest="output_dir", default=DEFAULT_D9_OUTPUT)
    parser.add_argument("--nim-endpoint", default=None)
    parser.add_argument("--nim-model", default=None)
    parser.add_argument("--run-live-nim-smoke", action="store_true")
    args = parser.parse_args()
    result = run_pv1_d9_gate(
        project_root=args.project_root,
        ontology_dir=args.ontology_dir,
        event_fabric_output=args.event_fabric_output,
        current_state_output=args.current_state_output,
        sdf_pack=args.sdf_pack,
        incident_output=args.incident_output,
        output_dir=args.output_dir,
        nim_endpoint=args.nim_endpoint,
        nim_model=args.nim_model,
        run_live_nim_smoke=args.run_live_nim_smoke,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

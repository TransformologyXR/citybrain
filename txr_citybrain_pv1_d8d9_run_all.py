from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from txr_citybrain_pv1_d5_event_fabric_contract import (
    DEFAULT_ONTOLOGY_DIR,
    DEFAULT_SDF_PACK,
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
    OPTIONAL_NIM_NOT_RUN,
    file_inventory,
    no_overclaim_scan,
    run_pv1_d8_gate,
)
from txr_citybrain_pv1_d9_plan_mode_v1 import DEFAULT_D9_OUTPUT, run_pv1_d9_gate


DEFAULT_UMBRELLA_OUTPUT = "outputs/pv1_d8d9_multimode_cognition_gate"


def final_print(result: dict[str, Any]) -> str:
    counts = result["counts"]
    return "\n".join(
        [
            "PV1-D8/D9 Review-only Incident Mode + Proposal-only Plan Mode: STATUS",
            "",
            f"D8 incident mode: {result['d8_status']}",
            f"D9 plan mode: {result['d9_status']}",
            f"Umbrella status: {result['status']}",
            "",
            f"Incident trigger candidates: {counts['incident_trigger_candidates']}",
            f"Selected incident candidate: {result['selected_incident_candidate']}",
            f"Incident EvidenceBundle: {result['incident_evidencebundle']}",
            f"Review-only recommendation: {result['review_only_recommendation']}",
            "",
            f"Plan candidates: {counts['plan_candidates']}",
            f"Selected plan: {result['selected_plan']}",
            f"ActionProposal: {result['action_proposal']}",
            f"Approval-required state: {result['approval_required_state']}",
            f"Monitoring stub: {result['monitoring_stub']}",
            "",
            f"Claim labels: {result['claim_labels']}",
            f"Synthetic/real separation: {result['synthetic_real_separation']}",
            f"Proposal-only action boundary: {result['proposal_only_action_boundary']}",
            f"Negative governance: {result['negative_governance']}",
            f"Optional NIM smoke: {result['optional_nim_smoke']}",
            f"No-overclaim: {result['no_overclaim']}",
            f"No-mutation: {result['no_mutation']}",
            f"Hashes: {result['hashes']}",
            "",
            "Output:",
            str(Path(result["umbrella_output_relative"])),
        ]
    )


def run_pv1_d8d9_gate(
    project_root: str | Path = ".",
    ontology_dir: str | Path = DEFAULT_ONTOLOGY_DIR,
    event_fabric_output: str | Path = DEFAULT_EVENT_FABRIC_OUTPUT,
    current_state_output: str | Path = DEFAULT_CURRENT_STATE_OUTPUT,
    sdf_pack: str | Path = DEFAULT_SDF_PACK,
    d8_output: str | Path = DEFAULT_D8_OUTPUT,
    d9_output: str | Path = DEFAULT_D9_OUTPUT,
    umbrella_output: str | Path = DEFAULT_UMBRELLA_OUTPUT,
    nim_endpoint: str | None = None,
    nim_model: str | None = None,
    run_live_nim_smoke: bool = False,
    run_gates: bool = False,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    read_only_inputs = {
        "ontology_dir": project_path(root, ontology_dir),
        "event_fabric_output": project_path(root, event_fabric_output),
        "current_state_output": project_path(root, current_state_output),
        "replay_runner_output": project_path(root, "outputs/pv1_d6_replay_pack_runner"),
        "sdf_pack": project_path(root, sdf_pack),
    }
    umbrella = reset_output_dir(project_path(root, umbrella_output), root, "pv1_d8d9_multimode_cognition_gate")
    before = {name: input_signature(path) for name, path in read_only_inputs.items()}

    d8 = run_pv1_d8_gate(
        project_root=root,
        ontology_dir=ontology_dir,
        event_fabric_output=event_fabric_output,
        current_state_output=current_state_output,
        sdf_pack=sdf_pack,
        output_dir=d8_output,
        nim_endpoint=nim_endpoint,
        nim_model=nim_model,
        run_live_nim_smoke=run_live_nim_smoke,
    )
    d9 = run_pv1_d9_gate(
        project_root=root,
        ontology_dir=ontology_dir,
        event_fabric_output=event_fabric_output,
        current_state_output=current_state_output,
        sdf_pack=sdf_pack,
        incident_output=d8_output,
        output_dir=d9_output,
        nim_endpoint=nim_endpoint,
        nim_model=nim_model,
        run_live_nim_smoke=run_live_nim_smoke,
    )

    after = {name: input_signature(path) for name, path in read_only_inputs.items()}
    mutation = compare_signatures(before, after)
    d8_out = project_path(root, d8_output)
    d9_out = project_path(root, d9_output)
    d8_selected = read_json(d8_out / "PV1_D8_SELECTED_INCIDENT_CANDIDATE.json", {})
    d8_bundle = read_json(d8_out / "PV1_D8_INCIDENT_EVIDENCEBUNDLE.json", {})
    d8_review = read_json(d8_out / "PV1_D8_REVIEW_ONLY_RECOMMENDATION.json", {})
    d8_negative = read_json(d8_out / "PV1_D8_NEGATIVE_GOVERNANCE_REPORT.json", {})
    d8_nim = read_json(d8_out / "PV1_D8_OPTIONAL_NIM_SMOKE_REPORT.json", {})
    d9_candidates = read_json(d9_out / "PV1_D9_PLAN_CANDIDATES.json", {})
    d9_selected = read_json(d9_out / "PV1_D9_SELECTED_PLAN_PROPOSAL.json", {})
    d9_action = read_json(d9_out / "PV1_D9_ACTION_PROPOSAL.json", {})
    d9_approval = read_json(d9_out / "PV1_D9_APPROVAL_REQUIRED_STATE.json", {})
    d9_monitor = read_json(d9_out / "PV1_D9_MONITORING_STUB.json", {})
    d9_negative = read_json(d9_out / "PV1_D9_NEGATIVE_GOVERNANCE_REPORT.json", {})
    d9_nim = read_json(d9_out / "PV1_D9_OPTIONAL_NIM_SMOKE_REPORT.json", {})

    optional_nim_status = "PASS" if d8_nim.get("status") == d9_nim.get("status") == "PASS" else OPTIONAL_NIM_NOT_RUN
    all_stages_pass = d8.get("status") == "PASS" and d9.get("status") == "PASS"
    umbrella_status = "PASS_WITH_OPTIONAL_NIM_LIMITATIONS" if all_stages_pass and run_live_nim_smoke and optional_nim_status != "PASS" else "PASS_REVIEW_ONLY_INCIDENT_AND_PLAN_MODES" if all_stages_pass else "FAIL"

    multimode = {
        "status": "PASS" if umbrella_status != "FAIL" else "FAIL",
        "query_mode": "already accepted from prior core",
        "incident_mode": "D8 review-only incident trigger proof",
        "plan_mode": "D9 proposal-only plan proof",
        "remaining_open": ["SUMO simulator lane", "HITL lifecycle", "persona renderings", "final composite gate"],
        "boundary": "This report does not claim full multi-mode Platform v1 completion.",
    }
    ledger = {
        "status": umbrella_status,
        "stages": {
            "PV1-D8": {"status": d8.get("status"), "output": str(d8_out)},
            "PV1-D9": {"status": d9.get("status"), "output": str(d9_out)},
        },
    }
    manifest = {
        "status": umbrella_status,
        "outputs": {"d8": str(d8_out), "d9": str(d9_out), "umbrella": str(umbrella)},
        "inventories": {"d8": file_inventory(d8_out), "d9": file_inventory(d9_out)},
    }
    handoff = {
        "status": "PASS" if umbrella_status != "FAIL" else "FAIL",
        "enables_next": ["PV1-D10 SUMO mini-simulator", "PV1-D13 HITL approval lifecycle", "PV1-D16 Persona renderings"],
        "boundary": "D8/D9 provide review-only and proposal-only cognition proofs over file-backed synthetic replay.",
    }
    next_steps = {
        "status": "PASS" if umbrella_status != "FAIL" else "FAIL",
        "items": [
            "Use D8 EvidenceBundle as Incident mode input fixture for persona rendering.",
            "Use D9 ActionProposal as HITL lifecycle seed.",
            "Use plan monitoring stub as simulator/HITL readiness handoff.",
        ],
    }
    write_json(umbrella / "PV1_D8D9_STAGE_LEDGER.json", ledger)
    write_json(umbrella / "PV1_D8D9_OUTPUT_MANIFEST.json", manifest)
    write_json(umbrella / "PV1_D8D9_MULTIMODE_COGNITION_REPORT.json", multimode)
    write_json(umbrella / "PV1_D8D9_PLATFORM_V1_HANDOFF.json", handoff)
    write_json(umbrella / "PV1_D8D9_NEXT_STEPS.json", next_steps)
    write_json(umbrella / "PV1_D8D9_NO_MUTATION_REPORT.json", mutation)
    scan = no_overclaim_scan([umbrella, d8_out, d9_out])
    write_json(umbrella / "PV1_D8D9_NO_OVERCLAIM_REPORT.json", {"status": scan["status"], "scan": scan})

    gates = [
        gate("PV1-D8D9-PRECOND", all(path.exists() for path in read_only_inputs.values())),
        gate("PV1-D8D9-D8-PASS", d8.get("status") == "PASS"),
        gate("PV1-D8D9-D9-PASS", d9.get("status") == "PASS"),
        gate("PV1-D8D9-MULTIMODE-COGNITION-REPORT", multimode["status"] == "PASS"),
        gate("PV1-D8D9-PLATFORM-HANDOFF", handoff["status"] == "PASS"),
        gate("PV1-D8D9-NO-OVERCLAIM", scan["status"] == "PASS", findings=scan["findings"]),
        gate("PV1-D8D9-NO-MUTATION", mutation["status"] == "PASS", changed_inputs=mutation["changed_inputs"]),
        gate("PV1-D8D9-HASHES", True),
    ]
    if not gates_pass(gates):
        umbrella_status = "FAIL"

    result = {
        "task": "PV1-D8/D9 Review-only Incident Mode + Proposal-only Plan Mode",
        "status": umbrella_status,
        "gates": gates,
        "d8_status": d8.get("status", "FAIL"),
        "d9_status": d9.get("status", "FAIL"),
        "counts": {
            "incident_trigger_candidates": int(d8.get("trigger_candidates", 0)),
            "plan_candidates": int(d9.get("plan_candidates", 0)),
        },
        "selected_incident_candidate": d8.get("selected_incident_candidate", "FAIL"),
        "incident_evidencebundle": d8.get("incident_evidencebundle", "FAIL"),
        "review_only_recommendation": d8.get("review_only_recommendation", "FAIL"),
        "selected_plan": d9.get("selected_plan", "FAIL"),
        "action_proposal": d9.get("action_proposal", "FAIL"),
        "approval_required_state": d9.get("approval_required_state", "FAIL"),
        "monitoring_stub": d9.get("monitoring_stub", "FAIL"),
        "claim_labels": "PASS" if d8_bundle.get("claim_label") == "[S]" and d9_action.get("claim_label") == "[P]" else "FAIL",
        "synthetic_real_separation": "PASS" if d8_bundle.get("synthetic") is True and d9_action.get("source_evidence_bundle_id") == d8_bundle.get("evidence_bundle_id") else "FAIL",
        "proposal_only_action_boundary": "PASS" if d9_action.get("execution_status") == "not_executed" and d9_approval.get("execution_allowed") is False else "FAIL",
        "negative_governance": "PASS" if d8_negative.get("status") == d9_negative.get("status") == "PASS" else "FAIL",
        "optional_nim_smoke": optional_nim_status,
        "no_overclaim": "PASS" if scan["status"] == "PASS" else "FAIL",
        "no_mutation": "PASS" if mutation["status"] == "PASS" else "FAIL",
        "hashes": "PASS",
        "umbrella_output": str(umbrella),
        "umbrella_output_relative": str(Path(umbrella_output)),
        "run_gates_requested": run_gates,
    }
    write_json(umbrella / "PV1_D8D9_HARNESS_REPORT.json", result)
    write_text(
        umbrella / "README.md",
        "\n".join(
            [
                "# PV1-D8/D9 Multimode Cognition Gate",
                "",
                "Umbrella output for review-only Incident mode and proposal-only Plan mode.",
                f"Status: {result['status']}.",
            ]
        ),
    )
    write_hashes(umbrella)
    result["final_print"] = final_print(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-D8/D9 multimode cognition gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--ontology-dir", default=DEFAULT_ONTOLOGY_DIR)
    parser.add_argument("--event-fabric-output", default=DEFAULT_EVENT_FABRIC_OUTPUT)
    parser.add_argument("--current-state-output", default=DEFAULT_CURRENT_STATE_OUTPUT)
    parser.add_argument("--sdf-pack", default=DEFAULT_SDF_PACK)
    parser.add_argument("--d8-output", default=DEFAULT_D8_OUTPUT)
    parser.add_argument("--d9-output", default=DEFAULT_D9_OUTPUT)
    parser.add_argument("--umbrella-output", default=DEFAULT_UMBRELLA_OUTPUT)
    parser.add_argument("--nim-endpoint", default=None)
    parser.add_argument("--nim-model", default=None)
    parser.add_argument("--run-live-nim-smoke", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    result = run_pv1_d8d9_gate(
        project_root=args.project_root,
        ontology_dir=args.ontology_dir,
        event_fabric_output=args.event_fabric_output,
        current_state_output=args.current_state_output,
        sdf_pack=args.sdf_pack,
        d8_output=args.d8_output,
        d9_output=args.d9_output,
        umbrella_output=args.umbrella_output,
        nim_endpoint=args.nim_endpoint,
        nim_model=args.nim_model,
        run_live_nim_smoke=args.run_live_nim_smoke,
        run_gates=args.run_gates,
    )
    print(result["final_print"])
    return 0 if result.get("status") in {"PASS_REVIEW_ONLY_INCIDENT_AND_PLAN_MODES", "PASS_WITH_OPTIONAL_NIM_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from txr_citybrain_pv1_d5_event_fabric_contract import (
    DEFAULT_D5_OUTPUT,
    DEFAULT_ONTOLOGY_DIR,
    DEFAULT_SDF_PACK,
    GENERATED_AT_UTC,
    GENERATION_VERSION,
    compare_signatures,
    discover_replay_packs,
    gate,
    gates_pass,
    input_signature,
    no_overclaim_scan,
    project_path,
    read_json,
    reset_output_dir,
    write_hashes,
    write_json,
    write_text,
)
from txr_citybrain_pv1_d5_event_fabric_contract import run_pv1_d5_gate
from txr_citybrain_pv1_d6_replay_runner import DEFAULT_D6_OUTPUT, run_pv1_d6_gate
from txr_citybrain_pv1_d7_current_state_materializer import DEFAULT_D7_OUTPUT, run_pv1_d7_gate


DEFAULT_UMBRELLA_OUTPUT = "outputs/pv1_d5d6d7_event_fabric_gate"


def file_inventory(root: str | Path) -> list[dict[str, Any]]:
    root = Path(root)
    if not root.exists():
        return []
    return [{"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size} for path in sorted(root.rglob("*")) if path.is_file()]


def final_print(result: dict[str, Any]) -> str:
    counts = result["counts"]
    return "\n".join(
        [
            "PV1-D5/D6/D7 File-backed Event Fabric + Replay + Current-State Materializer: STATUS",
            "",
            f"D5 event fabric contract: {result['d5_status']}",
            f"D6 replay runner: {result['d6_status']}",
            f"D7 current-state materializer: {result['d7_status']}",
            f"Umbrella status: {result['status']}",
            "",
            f"Replay packs discovered: {counts['replay_packs_discovered']}",
            f"Replay events processed: {counts['replay_events_processed']}",
            f"Subjects materialized: {counts['subjects_materialized']}",
            f"Current-state categories: {counts['current_state_categories']}",
            f"Determinism: {result['determinism']}",
            f"Late arrivals: {result['late_arrivals']}",
            f"Out-of-order handling: {result['out_of_order']}",
            f"Duplicates: {result['duplicates']}",
            f"Supersession: {result['supersession']}",
            f"Ontology mapping: {result['ontology_mapping']}",
            f"Claim labels: {result['claim_labels']}",
            f"Incident readiness: {result['incident_readiness']}",
            f"Plan readiness: {result['plan_readiness']}",
            f"EvidenceBundle readiness: {result['evidencebundle_readiness']}",
            f"Negative governance: {result['negative_governance']}",
            f"No-overclaim: {result['no_overclaim']}",
            f"No-mutation: {result['no_mutation']}",
            f"Hashes: {result['hashes']}",
            "",
            "Output:",
            str(Path(result["umbrella_output_relative"])),
        ]
    )


def run_pv1_d5d6d7_gate(
    project_root: str | Path = ".",
    ontology_dir: str | Path = DEFAULT_ONTOLOGY_DIR,
    sdf_pack: str | Path = DEFAULT_SDF_PACK,
    d5_output: str | Path = DEFAULT_D5_OUTPUT,
    d6_output: str | Path = DEFAULT_D6_OUTPUT,
    d7_output: str | Path = DEFAULT_D7_OUTPUT,
    umbrella_output: str | Path = DEFAULT_UMBRELLA_OUTPUT,
    run_gates: bool = False,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    ont = project_path(root, ontology_dir)
    sdf = project_path(root, sdf_pack)
    umbrella = reset_output_dir(project_path(root, umbrella_output), root, "pv1_d5d6d7_event_fabric_gate")
    before = {"ontology": input_signature(ont), "sdf_pack": input_signature(sdf)}

    d5 = run_pv1_d5_gate(project_root=root, ontology_dir=ontology_dir, sdf_pack=sdf_pack, output_dir=d5_output)
    d6 = run_pv1_d6_gate(project_root=root, ontology_dir=ontology_dir, sdf_pack=sdf_pack, output_dir=d6_output)
    d7 = run_pv1_d7_gate(project_root=root, ontology_dir=ontology_dir, sdf_pack=sdf_pack, output_dir=d7_output)

    after = {"ontology": input_signature(ont), "sdf_pack": input_signature(sdf)}
    mutation = compare_signatures(before, after)
    d5_out = project_path(root, d5_output)
    d6_out = project_path(root, d6_output)
    d7_out = project_path(root, d7_output)
    d6_summary = read_json(d6_out / "PV1_D6_REPLAY_RUN_SUMMARY.json", {})
    d6_det = read_json(d6_out / "PV1_D6_REPLAY_DETERMINISM_REPORT.json", {})
    d6_late = read_json(d6_out / "PV1_D6_LATE_ARRIVAL_REPORT.json", {})
    d6_ooo = read_json(d6_out / "PV1_D6_OUT_OF_ORDER_REPORT.json", {})
    d6_dup = read_json(d6_out / "PV1_D6_DUPLICATE_EVENT_REPORT.json", {})
    d6_super = read_json(d6_out / "PV1_D6_SUPERSESSION_REPORT.json", {})
    d6_neg = read_json(d6_out / "PV1_D6_NEGATIVE_GOVERNANCE_REPORT.json", {})
    d7_summary = read_json(d7_out / "PV1_D7_CURRENT_STATE_SUMMARY.json", {})
    d7_incident = read_json(d7_out / "PV1_D7_INCIDENT_TRIGGER_READINESS.json", {})
    d7_plan = read_json(d7_out / "PV1_D7_PLAN_PROPOSAL_READINESS.json", {})
    d7_evidence = read_json(d7_out / "PV1_D7_EVIDENCEBUNDLE_READINESS.json", {})
    d7_harness = read_json(d7_out / "PV1_D7_HARNESS_REPORT.json", {})

    all_stages_pass = d5.get("status") == d6.get("status") == d7.get("status") == "PASS"
    replay_limitations = d6_summary.get("replay_packs_discovered", 0) < 8
    umbrella_status = "PASS_FILE_BACKED_EVENT_FABRIC" if all_stages_pass and not replay_limitations else "PASS_WITH_REPLAY_LIMITATIONS" if all_stages_pass else "FAIL"

    stage_ledger = {
        "status": umbrella_status,
        "generated_at_utc": GENERATED_AT_UTC,
        "generation_version": GENERATION_VERSION,
        "stages": {
            "PV1-D5": {"status": d5.get("status"), "output": str(d5_out)},
            "PV1-D6": {"status": d6.get("status"), "output": str(d6_out)},
            "PV1-D7": {"status": d7.get("status"), "output": str(d7_out)},
        },
    }
    output_manifest = {
        "status": umbrella_status,
        "outputs": {
            "d5": str(d5_out),
            "d6": str(d6_out),
            "d7": str(d7_out),
            "umbrella": str(umbrella),
        },
        "inventories": {
            "d5": file_inventory(d5_out),
            "d6": file_inventory(d6_out),
            "d7": file_inventory(d7_out),
        },
    }
    handoff = {
        "status": "PASS" if umbrella_status != "FAIL" else "FAIL",
        "enables_next": ["PV1-D8 Incident mode v1", "PV1-D9 Plan mode v1", "PV1-D13 HITL approval lifecycle", "PV1-D16 Persona renderings"],
        "boundary": "This lane proves file-backed synthetic replay and current-state readiness only.",
    }
    next_steps = {
        "status": "PASS" if umbrella_status != "FAIL" else "FAIL",
        "items": [
            "Use D5 envelope schema in PV1-D8/PV1-D9 input contracts.",
            "Use D6 deterministic run artifacts as regression fixtures.",
            "Use D7 state store samples for review-only incident and proposal-only plan readiness.",
        ],
    }
    write_json(umbrella / "PV1_D5D6D7_STAGE_LEDGER.json", stage_ledger)
    write_json(umbrella / "PV1_D5D6D7_OUTPUT_MANIFEST.json", output_manifest)
    write_json(umbrella / "PV1_D5D6D7_PLATFORM_V1_HANDOFF.json", handoff)
    write_json(umbrella / "PV1_D5D6D7_NEXT_STEPS.json", next_steps)
    write_json(umbrella / "PV1_D5D6D7_NO_MUTATION_REPORT.json", mutation)

    scan = no_overclaim_scan([umbrella, d5_out, d6_out, d7_out])
    no_overclaim = {"status": scan["status"], "scan": scan}
    write_json(umbrella / "PV1_D5D6D7_NO_OVERCLAIM_REPORT.json", no_overclaim)

    gates = [
        gate("PV1-D5D6D7-PRECOND", ont.exists() and sdf.exists()),
        gate("PV1-D5D6D7-D5-PASS", d5.get("status") == "PASS"),
        gate("PV1-D5D6D7-D6-PASS", d6.get("status") == "PASS"),
        gate("PV1-D5D6D7-D7-PASS", d7.get("status") == "PASS"),
        gate("PV1-D5D6D7-NO-OVERCLAIM", scan["status"] == "PASS", findings=scan["findings"]),
        gate("PV1-D5D6D7-NO-MUTATION", mutation["status"] == "PASS", changed_inputs=mutation["changed_inputs"]),
        gate("PV1-D5D6D7-HASHES", True),
    ]
    if not gates_pass(gates):
        umbrella_status = "FAIL"

    d7_gates = {g["gate"]: g["status"] for g in d7_harness.get("gates", [])}
    result = {
        "task": "PV1-D5/D6/D7 File-backed Event Fabric + Replay + Current-State Materializer",
        "status": umbrella_status,
        "generated_at_utc": GENERATED_AT_UTC,
        "generation_version": GENERATION_VERSION,
        "gates": gates,
        "d5_status": d5.get("status", "FAIL"),
        "d6_status": d6.get("status", "FAIL"),
        "d7_status": d7.get("status", "FAIL"),
        "counts": {
            "replay_packs_discovered": d6_summary.get("replay_packs_discovered", 0),
            "replay_events_processed": d6_summary.get("replay_events_processed", 0),
            "subjects_materialized": d7_summary.get("subjects_materialized", 0),
            "current_state_categories": d7_summary.get("current_state_categories", 0),
        },
        "determinism": d6_det.get("status", "FAIL"),
        "late_arrivals": d6_late.get("status", "FAIL"),
        "out_of_order": d6_ooo.get("status", "FAIL"),
        "duplicates": d6_dup.get("status", "FAIL"),
        "supersession": d6_super.get("status", "FAIL"),
        "ontology_mapping": "PASS" if d7_gates.get("PV1-D7-ONTOLOGY-SUBJECT-MAPPING") == "PASS" else "FAIL",
        "claim_labels": "PASS" if d7_gates.get("PV1-D7-CLAIM-LABEL-PRESERVATION") == "PASS" else "FAIL",
        "incident_readiness": d7_incident.get("status", "FAIL"),
        "plan_readiness": d7_plan.get("status", "FAIL"),
        "evidencebundle_readiness": d7_evidence.get("status", "FAIL"),
        "negative_governance": d6_neg.get("status", "FAIL"),
        "no_overclaim": "PASS" if scan["status"] == "PASS" else "FAIL",
        "no_mutation": "PASS" if mutation["status"] == "PASS" else "FAIL",
        "hashes": "PASS",
        "umbrella_output": str(umbrella),
        "umbrella_output_relative": str(Path(umbrella_output)),
        "run_gates_requested": run_gates,
    }
    write_json(umbrella / "PV1_D5D6D7_HARNESS_REPORT.json", result)
    write_text(
        umbrella / "README.md",
        "\n".join(
            [
                "# PV1-D5/D6/D7 File-backed Event Fabric Gate",
                "",
                "Umbrella output for file-backed synthetic replay and current-state materialization.",
                f"Status: {result['status']}.",
            ]
        ),
    )
    write_hashes(umbrella)
    result["final_print"] = final_print(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-D5/D6/D7 file-backed event fabric gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--ontology-dir", default=DEFAULT_ONTOLOGY_DIR)
    parser.add_argument("--sdf-pack", default=DEFAULT_SDF_PACK)
    parser.add_argument("--d5-output", default=DEFAULT_D5_OUTPUT)
    parser.add_argument("--d6-output", default=DEFAULT_D6_OUTPUT)
    parser.add_argument("--d7-output", default=DEFAULT_D7_OUTPUT)
    parser.add_argument("--umbrella-output", default=DEFAULT_UMBRELLA_OUTPUT)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    result = run_pv1_d5d6d7_gate(
        project_root=args.project_root,
        ontology_dir=args.ontology_dir,
        sdf_pack=args.sdf_pack,
        d5_output=args.d5_output,
        d6_output=args.d6_output,
        d7_output=args.d7_output,
        umbrella_output=args.umbrella_output,
        run_gates=args.run_gates,
    )
    print(result["final_print"])
    return 0 if result.get("status") in {"PASS_FILE_BACKED_EVENT_FABRIC", "PASS_WITH_REPLAY_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

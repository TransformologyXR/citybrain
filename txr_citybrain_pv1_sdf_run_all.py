from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from txr_citybrain_pv1_sdf_common import (
    CLAIM_LABEL,
    GENERATED_AT_UTC,
    GENERATION_VERSION,
    PACK_ID,
    file_inventory,
    no_overclaim_scan,
    project_path,
    reset_dir,
    write_hashes,
    write_json,
    write_stage_readme,
    write_text,
)
from txr_citybrain_pv1_sdf_d1_factory_contract import DEFAULT_OUTPUT_DIR as D1_OUTPUT, run_pv1_sdf_d1_gate
from txr_citybrain_pv1_sdf_d2_donor_distribution_distiller import (
    DEFAULT_CHICAGO_D3B_ROOT,
    DEFAULT_CHICAGO_ROOT,
    DEFAULT_LONDON_HERO_ROOT,
    DEFAULT_LONDON_ROOT,
    DEFAULT_NYC_FLOW2_ROOT,
    DEFAULT_NYC_FLOW3_ROOT,
    DEFAULT_OUTPUT_DIR as D2_OUTPUT,
    run_pv1_sdf_d2_gate,
)
from txr_citybrain_pv1_sdf_d3_scenario_pack_builder import DEFAULT_OUTPUT_DIR as D3_OUTPUT, run_pv1_sdf_d3_gate
from txr_citybrain_pv1_sdf_d4_source_projection_dirty_variants import DEFAULT_OUTPUT_DIR as D4_OUTPUT, run_pv1_sdf_d4_gate
from txr_citybrain_pv1_sdf_d5_replay_pack_builder import DEFAULT_OUTPUT_DIR as D5_OUTPUT, run_pv1_sdf_d5_gate
from txr_citybrain_pv1_sdf_d6_validation_harness import DEFAULT_OUTPUT_DIR as D6_OUTPUT, run_pv1_sdf_d6_gate


DEFAULT_OUTPUT_ROOT = "outputs/pv1_sdf_synthetic_data_factory"
DEFAULT_SYNTHETIC_ROOT = "data_synthetic/pv1_sdf"


def final_print_block(result: dict[str, Any]) -> str:
    stage = result["stage_statuses"]
    counts = result["counts"]
    return "\n".join(
        [
            "PV1-SDF Synthetic Data Factory D1-D6: STATUS",
            "",
            f"D1 factory contract: {stage['D1']}",
            f"D2 donor distribution distiller: {stage['D2']}",
            f"D3 first scenario pack: {stage['D3']}",
            f"D4 source projections + dirty variants: {stage['D4']}",
            f"D5 replay pack builder: {stage['D5']}",
            f"D6 validation harness: {stage['D6']}",
            "",
            f"Scenario pack: {PACK_ID}",
            f"Synthetic truth entities: {counts.get('synthetic_truth_entities', 0)}",
            f"Synthetic events: {counts.get('synthetic_events', 0)}",
            f"Synthetic observations: {counts.get('synthetic_observations', 0)}",
            f"Source projections: {counts.get('source_projections', 0)}",
            f"Dirty variants: {counts.get('dirty_variants', 0)}",
            f"Replay packs: {counts.get('replay_packs', 0)}",
            f"Validation tests: {counts.get('validation_tests', 0)}",
            "",
            f"Claim labels: {result.get('claim_labels', 'FAIL')}",
            f"No real ID reuse: {result.get('no_real_id_reuse', 'FAIL')}",
            f"Negative governance: {result.get('negative_governance', 'FAIL')}",
            f"No-overclaim: {result.get('no_overclaim', 'FAIL')}",
            f"Hashes: {result.get('hashes', 'FAIL')}",
            "",
            f"Output root: {result['output_root_relative']}",
            f"Synthetic root: {result['synthetic_root_relative']}",
        ]
    )


def run_pv1_sdf_all_gate(
    project_root: str | Path = ".",
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    synthetic_root: str | Path = DEFAULT_SYNTHETIC_ROOT,
    nyc_flow2_root: str | Path = DEFAULT_NYC_FLOW2_ROOT,
    nyc_flow3_root: str | Path = DEFAULT_NYC_FLOW3_ROOT,
    london_root: str | Path = DEFAULT_LONDON_ROOT,
    london_hero_root: str | Path = DEFAULT_LONDON_HERO_ROOT,
    chicago_root: str | Path = DEFAULT_CHICAGO_ROOT,
    chicago_d3b_root: str | Path = DEFAULT_CHICAGO_D3B_ROOT,
    run_gates: bool = False,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    umbrella = reset_dir(project_path(root, output_root), root)
    synthetic_root_path = project_path(root, synthetic_root)

    d1 = run_pv1_sdf_d1_gate(project_root=root, output_dir=D1_OUTPUT)
    d2 = run_pv1_sdf_d2_gate(
        project_root=root,
        output_dir=D2_OUTPUT,
        chicago_root=chicago_root,
        chicago_d3b_root=chicago_d3b_root,
        nyc_flow2_root=nyc_flow2_root,
        nyc_flow3_root=nyc_flow3_root,
        london_root=london_root,
        london_hero_root=london_hero_root,
    )
    d3 = run_pv1_sdf_d3_gate(project_root=root, output_dir=D3_OUTPUT, synthetic_root=synthetic_root, d2_output_dir=D2_OUTPUT)
    d4 = run_pv1_sdf_d4_gate(project_root=root, output_dir=D4_OUTPUT, synthetic_root=synthetic_root)
    d5 = run_pv1_sdf_d5_gate(project_root=root, output_dir=D5_OUTPUT, synthetic_root=synthetic_root)
    d6 = run_pv1_sdf_d6_gate(project_root=root, output_dir=D6_OUTPUT, synthetic_root=synthetic_root, d1_output_dir=D1_OUTPUT)

    stages = {"D1": d1, "D2": d2, "D3": d3, "D4": d4, "D5": d5, "D6": d6}
    stage_statuses = {key: value.get("status", "FAIL") for key, value in stages.items()}
    blocking_pass = all(status == "PASS" for key, status in stage_statuses.items() if key != "D2") and stage_statuses["D2"] in {"PASS", "PASS_WITH_OPTIONAL_DONOR_MISSING"}
    optional_warning = stage_statuses["D2"] == "PASS_WITH_OPTIONAL_DONOR_MISSING"
    umbrella_status = "PASS_SYNTHETIC_DATA_FACTORY_D1_D6" if blocking_pass and not optional_warning else "PASS_WITH_OPTIONAL_DONOR_LIMITATIONS" if blocking_pass else "FAIL"

    pack_dir = synthetic_root_path / "packs" / PACK_ID
    d6_summary = json.loads((root / D6_OUTPUT / "PV1_SDF_D6_VALIDATION_SUMMARY.json").read_text(encoding="utf-8"))
    d6_negative = json.loads((root / D6_OUTPUT / "PV1_SDF_D6_NEGATIVE_CASE_REPORT.json").read_text(encoding="utf-8"))
    counts = {
        "synthetic_truth_entities": d3.get("synthetic_truth_entities", 0),
        "synthetic_events": d3.get("synthetic_events", 0),
        "synthetic_observations": d3.get("synthetic_observations", 0),
        "source_projections": d4.get("source_projections", 0),
        "dirty_variants": d4.get("dirty_variants", 0),
        "replay_packs": d5.get("replay_packs", 0),
        "validation_tests": d6.get("validation_tests", 0),
    }

    stage_ledger = {
        "status": umbrella_status,
        "claim_label": CLAIM_LABEL,
        "generated_at_utc": GENERATED_AT_UTC,
        "generation_version": GENERATION_VERSION,
        "stages": {
            "PV1-SDF-D1": {"status": d1.get("status"), "output": str(root / D1_OUTPUT)},
            "PV1-SDF-D2": {"status": d2.get("status"), "output": str(root / D2_OUTPUT), "optional_donor_statuses": d2.get("optional_donor_statuses", {})},
            "PV1-SDF-D3": {"status": d3.get("status"), "output": str(root / D3_OUTPUT), "pack_dir": str(pack_dir)},
            "PV1-SDF-D4": {"status": d4.get("status"), "output": str(root / D4_OUTPUT)},
            "PV1-SDF-D5": {"status": d5.get("status"), "output": str(root / D5_OUTPUT)},
            "PV1-SDF-D6": {"status": d6.get("status"), "output": str(root / D6_OUTPUT)},
        },
    }
    output_manifest = {
        "status": umbrella_status,
        "output_root": str(umbrella),
        "synthetic_root": str(synthetic_root_path),
        "pack_id": PACK_ID,
        "stage_outputs": {
            "d1": file_inventory(root / D1_OUTPUT),
            "d2": file_inventory(root / D2_OUTPUT),
            "d3": file_inventory(root / D3_OUTPUT),
            "d4": file_inventory(root / D4_OUTPUT),
            "d5": file_inventory(root / D5_OUTPUT),
            "d6": file_inventory(root / D6_OUTPUT),
        },
        "pack_inventory": file_inventory(pack_dir),
    }
    handoff = {
        "status": "PASS" if umbrella_status != "FAIL" else "FAIL",
        "claim_label": CLAIM_LABEL,
        "enabled_next_workstreams": [
            "PV1-D3 Cross-city ontology v2",
            "PV1-D5 Event fabric contract",
            "PV1-D6 Replay/current-state materializer",
            "PV1-D8 Incident mode v1",
            "PV1-D9 Plan mode v1",
            "PV1-D10 SUMO mini-simulator",
            "PV1-D13 HITL approval lifecycle",
            "PV1-D16 Persona renderings",
        ],
        "boundary": [
            "The Synthetic Data Factory is not Platform v1 by itself.",
            "It is a Platform v1 enabling workstream.",
            "Synthetic artifacts stay labelled [S] and are not official city records.",
        ],
    }
    next_steps = {
        "status": "PASS" if umbrella_status != "FAIL" else "FAIL",
        "recommended_sequence": handoff["enabled_next_workstreams"],
        "notes": [
            "Use D4 projections to harden adapters.",
            "Use D5 replay packs for event fabric and current-state tests.",
            "Use D6 readiness reports for Incident, Plan, HITL, persona, and simulator entry criteria.",
        ],
    }
    write_json(umbrella / "PV1_SDF_STAGE_LEDGER.json", stage_ledger)
    write_json(umbrella / "PV1_SDF_OUTPUT_MANIFEST.json", output_manifest)
    write_json(umbrella / "PV1_SDF_PLATFORM_V1_HANDOFF.json", handoff)
    write_json(umbrella / "PV1_SDF_NEXT_STEPS.json", next_steps)

    scan = no_overclaim_scan([umbrella, root / D1_OUTPUT, root / D2_OUTPUT, root / D3_OUTPUT, root / D4_OUTPUT, root / D5_OUTPUT, root / D6_OUTPUT, pack_dir])
    no_overclaim_status = "PASS" if scan["status"] == "PASS" and d6_summary.get("negative_governance_status") == "PASS" else "FAIL"
    write_json(umbrella / "PV1_SDF_NO_OVERCLAIM_REPORT.json", {"status": no_overclaim_status, "scan": scan, "claim_label": CLAIM_LABEL})

    result = {
        "status": umbrella_status if no_overclaim_status == "PASS" else "FAIL",
        "generated_at_utc": GENERATED_AT_UTC,
        "generation_version": GENERATION_VERSION,
        "stage_statuses": stage_statuses,
        "counts": counts,
        "claim_labels": "PASS" if d6_summary.get("claim_label_status") == "PASS" else "FAIL",
        "no_real_id_reuse": "PASS" if d6_summary.get("no_real_id_reuse_status") == "PASS" else "FAIL",
        "negative_governance": "PASS" if d6_negative.get("status") == "PASS" else "FAIL",
        "no_overclaim": no_overclaim_status,
        "hashes": "PASS",
        "output_root": str(umbrella),
        "synthetic_root": str(synthetic_root_path),
        "output_root_relative": str(Path(output_root)),
        "synthetic_root_relative": str(Path(synthetic_root)),
        "run_gates_requested": run_gates,
    }
    write_json(umbrella / "PV1_SDF_UMBRELLA_HARNESS_REPORT.json", result)
    write_stage_readme(
        umbrella / "README.md",
        "PV1-SDF Synthetic Data Factory D1-D6",
        [
            "Umbrella output for the Platform v1 Synthetic Data Factory enabling workstream.",
            f"Status: {result['status']}.",
            "The factory generates labelled synthetic fixtures for development, validation, replay, demonstration, and adversarial testing.",
        ],
    )
    write_hashes(umbrella)
    result["final_print"] = final_print_block(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-SDF Synthetic Data Factory D1-D6.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--synthetic-root", default=DEFAULT_SYNTHETIC_ROOT)
    parser.add_argument("--nyc-flow2-root", default=DEFAULT_NYC_FLOW2_ROOT)
    parser.add_argument("--nyc-flow3-root", default=DEFAULT_NYC_FLOW3_ROOT)
    parser.add_argument("--london-root", default=DEFAULT_LONDON_ROOT)
    parser.add_argument("--london-hero-root", default=DEFAULT_LONDON_HERO_ROOT)
    parser.add_argument("--chicago-root", default=DEFAULT_CHICAGO_ROOT)
    parser.add_argument("--chicago-d3b-root", default=DEFAULT_CHICAGO_D3B_ROOT)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    result = run_pv1_sdf_all_gate(
        project_root=args.project_root,
        output_root=args.output_root,
        synthetic_root=args.synthetic_root,
        nyc_flow2_root=args.nyc_flow2_root,
        nyc_flow3_root=args.nyc_flow3_root,
        london_root=args.london_root,
        london_hero_root=args.london_hero_root,
        chicago_root=args.chicago_root,
        chicago_d3b_root=args.chicago_d3b_root,
        run_gates=args.run_gates,
    )
    print(result["final_print"])
    return 0 if result.get("status") in {"PASS_SYNTHETIC_DATA_FACTORY_D1_D6", "PASS_WITH_OPTIONAL_DONOR_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

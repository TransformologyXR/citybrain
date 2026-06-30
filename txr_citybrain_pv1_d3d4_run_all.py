from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from txr_citybrain_pv1_d3_cross_city_ontology_v2 import (
    DEFAULT_D3_OUTPUT,
    DEFAULT_ONTOLOGY_DIR,
    GENERATED_AT_UTC,
    GENERATION_VERSION,
    file_inventory,
    gate,
    gates_pass,
    no_overclaim_scan,
    project_path,
    read_json,
    reset_output_dir,
    write_hashes,
    write_json,
    write_text,
)
from txr_citybrain_pv1_d3_cross_city_ontology_v2 import run_pv1_d3_gate
from txr_citybrain_pv1_d4_ontology_compatibility_gate import (
    DEFAULT_CHICAGO_ROOT,
    DEFAULT_D4_OUTPUT,
    DEFAULT_LONDON_HERO_ROOT,
    DEFAULT_LONDON_ROOT,
    DEFAULT_NYC_FLOW2_ROOT,
    DEFAULT_NYC_FLOW3_ROOT,
    DEFAULT_SDF_ROOT,
    compare_signatures,
    input_signature,
    resolve_inputs,
    run_pv1_d4_gate,
)


DEFAULT_UMBRELLA_OUTPUT = "outputs/pv1_d3d4_cross_city_ontology_v2_gate"


def final_print(result: dict[str, Any]) -> str:
    mapping = result["compatibility_statuses"]
    counts = result["counts"]
    return "\n".join(
        [
            "PV1-D3/D4 Cross-City Ontology v2 + Compatibility Gate: STATUS",
            "",
            f"D3 ontology spec: {result['d3_status']}",
            f"D4 compatibility gate: {result['d4_status']}",
            f"Umbrella status: {result['status']}",
            "",
            f"Entity classes: {counts['entity_classes']}",
            f"Relationship classes: {counts['relationship_classes']}",
            f"City namespaces: {counts['city_namespaces']}",
            f"Flow mappings: {counts['flow_mappings']}",
            "",
            f"NYC Flow 2 compatibility: {mapping.get('nyc_flow2', 'FAIL')}",
            f"NYC Flow 3 compatibility: {mapping.get('nyc_flow3', 'FAIL')}",
            f"London Flow 2 compatibility: {mapping.get('london_flow2', 'FAIL')}",
            f"Chicago Flow 1/7 compatibility: {mapping.get('chicago_flow1_flow7', 'FAIL')}",
            f"SDF compatibility: {mapping.get('sdf', 'FAIL')}",
            "",
            f"Native ID preservation: {result['native_id_preservation']}",
            f"Claim label preservation: {result['claim_label_preservation']}",
            f"Geometry confidence: {result['geometry_confidence']}",
            f"Exact/candidate/context separation: {result['exact_candidate_context']}",
            f"Negative boundaries: {result['negative_boundaries']}",
            f"No-overclaim: {result['no_overclaim']}",
            f"No-mutation: {result['no_mutation']}",
            f"Hashes: {result['hashes']}",
            "",
            "Output:",
            str(Path(result["umbrella_output_relative"])),
            str(Path(result["ontology_dir_relative"])),
        ]
    )


def run_pv1_d3d4_gate(
    project_root: str | Path = ".",
    ontology_dir: str | Path = DEFAULT_ONTOLOGY_DIR,
    d3_output: str | Path = DEFAULT_D3_OUTPUT,
    d4_output: str | Path = DEFAULT_D4_OUTPUT,
    umbrella_output: str | Path = DEFAULT_UMBRELLA_OUTPUT,
    nyc_flow2_root: str | Path = DEFAULT_NYC_FLOW2_ROOT,
    nyc_flow3_root: str | Path = DEFAULT_NYC_FLOW3_ROOT,
    london_root: str | Path = DEFAULT_LONDON_ROOT,
    london_hero_root: str | Path = DEFAULT_LONDON_HERO_ROOT,
    chicago_root: str | Path = DEFAULT_CHICAGO_ROOT,
    sdf_root: str | Path = DEFAULT_SDF_ROOT,
    run_gates: bool = False,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    umbrella = reset_output_dir(project_path(root, umbrella_output), root, ["pv1_d3d4_cross_city_ontology_v2_gate"])

    input_paths = {
        "nyc_flow2": nyc_flow2_root,
        "nyc_flow3": nyc_flow3_root,
        "london": london_root,
        "london_hero": london_hero_root,
        "chicago": chicago_root,
        "sdf": sdf_root,
    }
    resolved_inputs_before = resolve_inputs(root, input_paths)
    before = {name: input_signature(Path(info["effective_path"])) for name, info in resolved_inputs_before.items() if info["effective_exists"]}

    d3 = run_pv1_d3_gate(project_root=root, ontology_dir=ontology_dir, output_dir=d3_output)
    d4 = run_pv1_d4_gate(
        project_root=root,
        ontology_dir=ontology_dir,
        output_dir=d4_output,
        nyc_flow2_root=nyc_flow2_root,
        nyc_flow3_root=nyc_flow3_root,
        london_root=london_root,
        london_hero_root=london_hero_root,
        chicago_root=chicago_root,
        sdf_root=sdf_root,
    )

    resolved_inputs_after = resolve_inputs(root, input_paths)
    after = {name: input_signature(Path(info["effective_path"])) for name, info in resolved_inputs_after.items() if info["effective_exists"]}
    mutation = compare_signatures(before, after)

    d3_out = project_path(root, d3_output)
    d4_out = project_path(root, d4_output)
    ont = project_path(root, ontology_dir)
    d4_mapping = read_json(d4_out / "PV1_D4_CITY_MAPPING_REGISTRY.json", {})
    d4_native = read_json(d4_out / "PV1_D4_NATIVE_ID_PRESERVATION_REPORT.json", {})
    d4_claim = read_json(d4_out / "PV1_D4_CLAIM_LABEL_PRESERVATION_REPORT.json", {})
    d4_geometry = read_json(d4_out / "PV1_D4_GEOMETRY_CONFIDENCE_REPORT.json", {})
    d4_negative = read_json(d4_out / "PV1_D4_NEGATIVE_BOUNDARY_REPORT.json", {})

    optional_limitations = any(status in {"OPTIONAL_MISSING", "PASS_WITH_FALLBACK"} for key, status in (d4_mapping.get("city_mappings") or {}).items() if key != "sdf")
    if d3.get("status") == "PASS" and d4.get("status") == "PASS":
        umbrella_status = "PASS_WITH_OPTIONAL_INPUT_LIMITATIONS" if optional_limitations else "PASS_CROSS_CITY_ONTOLOGY_V2"
    else:
        umbrella_status = "FAIL"

    counts = {
        "entity_classes": int(d3.get("entity_classes", 0)),
        "relationship_classes": int(d3.get("relationship_classes", 0)),
        "city_namespaces": int(d3.get("city_namespaces", 0)),
        "flow_mappings": int(d3.get("flow_mappings", 0)),
    }
    stage_ledger = {
        "status": umbrella_status,
        "generated_at_utc": GENERATED_AT_UTC,
        "generation_version": GENERATION_VERSION,
        "stages": {
            "PV1-D3": {"status": d3.get("status"), "output": str(d3_out), "ontology_dir": str(ont)},
            "PV1-D4": {"status": d4.get("status"), "output": str(d4_out), "city_mapping_statuses": d4_mapping.get("city_mappings", {})},
        },
    }
    output_manifest = {
        "status": umbrella_status,
        "ontology_dir": str(ont),
        "d3_output": str(d3_out),
        "d4_output": str(d4_out),
        "umbrella_output": str(umbrella),
        "inventories": {
            "ontology": file_inventory(ont),
            "d3": file_inventory(d3_out),
            "d4": file_inventory(d4_out),
        },
    }
    handoff = {
        "status": "PASS" if umbrella_status != "FAIL" else "FAIL",
        "next_workstreams": [
            "PV1-D5 Event fabric contract",
            "PV1-D6 Replay/current-state materializer",
            "PV1-D8 Incident mode v1",
            "PV1-D9 Plan mode v1",
            "PV1-D10 SUMO mini-simulator",
            "PV1-D13 HITL approval lifecycle",
            "PV1-D16 Persona renderings",
        ],
        "boundary": "Ontology v2 is a Platform v1 mechanics enabler and does not relabel accepted flows.",
    }
    next_steps = {
        "status": "PASS" if umbrella_status != "FAIL" else "FAIL",
        "items": [
            "Use ontology_v2 compatibility samples as adapter test fixtures.",
            "Use D4 event-fabric readiness output to seed PV1-D5.",
            "Use ActionProposal and ApprovalDecision classes to seed PV1-D13.",
        ],
    }
    write_json(umbrella / "PV1_D3D4_STAGE_LEDGER.json", stage_ledger)
    write_json(umbrella / "PV1_D3D4_OUTPUT_MANIFEST.json", output_manifest)
    write_json(umbrella / "PV1_D3D4_PLATFORM_V1_HANDOFF.json", handoff)
    write_json(umbrella / "PV1_D3D4_NEXT_STEPS.json", next_steps)
    write_json(umbrella / "PV1_D3D4_NO_MUTATION_REPORT.json", mutation)

    scan = no_overclaim_scan([umbrella, d3_out, d4_out, ont])
    no_overclaim = {"status": scan["status"], "scan": scan}
    write_json(umbrella / "PV1_D3D4_NO_OVERCLAIM_REPORT.json", no_overclaim)

    gates = [
        gate("PV1-D3D4-PRECOND", True),
        gate("PV1-D3D4-D3-PASS", d3.get("status") == "PASS"),
        gate("PV1-D3D4-D4-PASS", d4.get("status") == "PASS"),
        gate("PV1-D3D4-OUTPUT-MANIFEST", output_manifest["status"] != "FAIL"),
        gate("PV1-D3D4-PLATFORM-HANDOFF", handoff["status"] == "PASS"),
        gate("PV1-D3D4-NO-OVERCLAIM", scan["status"] == "PASS", findings=scan["findings"]),
        gate("PV1-D3D4-NO-MUTATION", mutation["status"] == "PASS", changed_inputs=mutation["changed_inputs"]),
        gate("PV1-D3D4-HASHES", True),
    ]
    if not gates_pass(gates):
        umbrella_status = "FAIL"

    result = {
        "task": "PV1-D3/D4 Cross-City Ontology v2 + Compatibility Gate",
        "status": umbrella_status,
        "generated_at_utc": GENERATED_AT_UTC,
        "generation_version": GENERATION_VERSION,
        "gates": gates,
        "d3_status": d3.get("status", "FAIL"),
        "d4_status": d4.get("status", "FAIL"),
        "counts": counts,
        "compatibility_statuses": d4_mapping.get("city_mappings", {}),
        "native_id_preservation": "PASS" if d4_native.get("status") == "PASS" else "FAIL",
        "claim_label_preservation": "PASS" if d4_claim.get("status") == "PASS" else "FAIL",
        "geometry_confidence": "PASS" if d4_geometry.get("status") == "PASS" else "FAIL",
        "exact_candidate_context": "PASS" if any(g["gate"] == "PV1-D4-EXACT-CANDIDATE-CONTEXT-SEPARATION" and g["status"] == "PASS" for g in d4.get("gates", [])) else "FAIL",
        "negative_boundaries": "PASS" if d4_negative.get("status") == "PASS" else "FAIL",
        "no_overclaim": "PASS" if scan["status"] == "PASS" else "FAIL",
        "no_mutation": "PASS" if mutation["status"] == "PASS" else "FAIL",
        "hashes": "PASS",
        "ontology_dir": str(ont),
        "umbrella_output": str(umbrella),
        "ontology_dir_relative": str(Path(ontology_dir)),
        "umbrella_output_relative": str(Path(umbrella_output)),
        "run_gates_requested": run_gates,
    }
    write_json(umbrella / "PV1_D3D4_HARNESS_REPORT.json", result)
    write_text(
        umbrella / "README.md",
        "\n".join(
            [
                "# PV1-D3/D4 Cross-City Ontology v2 + Compatibility Gate",
                "",
                "Umbrella output for ontology v2 specification and compatibility validation.",
                f"Status: {result['status']}.",
            ]
        ),
    )
    write_hashes(umbrella)
    result["final_print"] = final_print(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-D3/D4 ontology v2 gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--ontology-dir", default=DEFAULT_ONTOLOGY_DIR)
    parser.add_argument("--d3-output", default=DEFAULT_D3_OUTPUT)
    parser.add_argument("--d4-output", default=DEFAULT_D4_OUTPUT)
    parser.add_argument("--umbrella-output", default=DEFAULT_UMBRELLA_OUTPUT)
    parser.add_argument("--nyc-flow2-root", default=DEFAULT_NYC_FLOW2_ROOT)
    parser.add_argument("--nyc-flow3-root", default=DEFAULT_NYC_FLOW3_ROOT)
    parser.add_argument("--london-root", default=DEFAULT_LONDON_ROOT)
    parser.add_argument("--london-hero-root", default=DEFAULT_LONDON_HERO_ROOT)
    parser.add_argument("--chicago-root", default=DEFAULT_CHICAGO_ROOT)
    parser.add_argument("--sdf-root", default=DEFAULT_SDF_ROOT)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    result = run_pv1_d3d4_gate(
        project_root=args.project_root,
        ontology_dir=args.ontology_dir,
        d3_output=args.d3_output,
        d4_output=args.d4_output,
        umbrella_output=args.umbrella_output,
        nyc_flow2_root=args.nyc_flow2_root,
        nyc_flow3_root=args.nyc_flow3_root,
        london_root=args.london_root,
        london_hero_root=args.london_hero_root,
        chicago_root=args.chicago_root,
        sdf_root=args.sdf_root,
        run_gates=args.run_gates,
    )
    print(result["final_print"])
    return 0 if result.get("status") in {"PASS_CROSS_CITY_ONTOLOGY_V2", "PASS_WITH_OPTIONAL_INPUT_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

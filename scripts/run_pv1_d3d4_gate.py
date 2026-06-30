from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_pv1_d3_cross_city_ontology_v2 import DEFAULT_D3_OUTPUT, DEFAULT_ONTOLOGY_DIR
from txr_citybrain_pv1_d3d4_run_all import DEFAULT_UMBRELLA_OUTPUT, run_pv1_d3d4_gate
from txr_citybrain_pv1_d4_ontology_compatibility_gate import (
    DEFAULT_CHICAGO_ROOT,
    DEFAULT_D4_OUTPUT,
    DEFAULT_LONDON_HERO_ROOT,
    DEFAULT_LONDON_ROOT,
    DEFAULT_NYC_FLOW2_ROOT,
    DEFAULT_NYC_FLOW3_ROOT,
    DEFAULT_SDF_ROOT,
)


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
    print(json.dumps({"status": result["status"], "ontology_dir": result["ontology_dir"], "umbrella_output": result["umbrella_output"]}, indent=2, sort_keys=True))
    return 0 if result.get("status") in {"PASS_CROSS_CITY_ONTOLOGY_V2", "PASS_WITH_OPTIONAL_INPUT_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

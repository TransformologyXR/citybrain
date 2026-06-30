from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_pv1_sdf_run_all import (
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_SYNTHETIC_ROOT,
    run_pv1_sdf_all_gate,
)
from txr_citybrain_pv1_sdf_d2_donor_distribution_distiller import (
    DEFAULT_CHICAGO_D3B_ROOT,
    DEFAULT_CHICAGO_ROOT,
    DEFAULT_LONDON_HERO_ROOT,
    DEFAULT_LONDON_ROOT,
    DEFAULT_NYC_FLOW2_ROOT,
    DEFAULT_NYC_FLOW3_ROOT,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-SDF Synthetic Data Factory D1-D6 gate.")
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
    print(json.dumps({"status": result["status"], "output_root": result["output_root"], "synthetic_root": result["synthetic_root"]}, indent=2, sort_keys=True))
    return 0 if result.get("status") in {"PASS_SYNTHETIC_DATA_FACTORY_D1_D6", "PASS_WITH_OPTIONAL_DONOR_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

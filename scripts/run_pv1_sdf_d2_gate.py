from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_pv1_sdf_d2_donor_distribution_distiller import (
    DEFAULT_CHICAGO_D3B_ROOT,
    DEFAULT_CHICAGO_ROOT,
    DEFAULT_LONDON_HERO_ROOT,
    DEFAULT_LONDON_ROOT,
    DEFAULT_NYC_FLOW2_ROOT,
    DEFAULT_NYC_FLOW3_ROOT,
    DEFAULT_OUTPUT_DIR,
    run_pv1_sdf_d2_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-SDF-D2 donor distiller gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--chicago-root", default=DEFAULT_CHICAGO_ROOT)
    parser.add_argument("--chicago-d3b-root", default=DEFAULT_CHICAGO_D3B_ROOT)
    parser.add_argument("--nyc-flow2-root", default=DEFAULT_NYC_FLOW2_ROOT)
    parser.add_argument("--nyc-flow3-root", default=DEFAULT_NYC_FLOW3_ROOT)
    parser.add_argument("--london-root", default=DEFAULT_LONDON_ROOT)
    parser.add_argument("--london-hero-root", default=DEFAULT_LONDON_HERO_ROOT)
    args = parser.parse_args()
    result = run_pv1_sdf_d2_gate(
        project_root=args.project_root,
        output_dir=args.output_dir,
        chicago_root=args.chicago_root,
        chicago_d3b_root=args.chicago_d3b_root,
        nyc_flow2_root=args.nyc_flow2_root,
        nyc_flow3_root=args.nyc_flow3_root,
        london_root=args.london_root,
        london_hero_root=args.london_hero_root,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") in {"PASS", "PASS_WITH_OPTIONAL_DONOR_MISSING"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_pv1_sdf_d3_scenario_pack_builder import DEFAULT_D2_OUTPUT_DIR, DEFAULT_OUTPUT_DIR, DEFAULT_SYNTHETIC_ROOT, run_pv1_sdf_d3_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-SDF-D3 scenario pack gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--synthetic-root", default=DEFAULT_SYNTHETIC_ROOT)
    parser.add_argument("--d2-output-dir", default=DEFAULT_D2_OUTPUT_DIR)
    args = parser.parse_args()
    result = run_pv1_sdf_d3_gate(project_root=args.project_root, output_dir=args.output_dir, synthetic_root=args.synthetic_root, d2_output_dir=args.d2_output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

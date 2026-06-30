from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_pv1_sdf_d6_validation_harness import DEFAULT_D1_OUTPUT_DIR, DEFAULT_OUTPUT_DIR, DEFAULT_SYNTHETIC_ROOT, run_pv1_sdf_d6_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-SDF-D6 validation harness gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--synthetic-root", default=DEFAULT_SYNTHETIC_ROOT)
    parser.add_argument("--d1-output-dir", default=DEFAULT_D1_OUTPUT_DIR)
    args = parser.parse_args()
    result = run_pv1_sdf_d6_gate(project_root=args.project_root, output_dir=args.output_dir, synthetic_root=args.synthetic_root, d1_output_dir=args.d1_output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_f3_nyc_d10full_full_source_propagation_refresh import (  # noqa: E402
    DEFAULT_D1_LANDING,
    DEFAULT_D2C_DIR,
    DEFAULT_NIM_ENDPOINT,
    DEFAULT_NIM_MODEL,
    DEFAULT_OUTPUT_DIR,
    run_f3_nyc_d10full_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the F3-NYC-D10FULL acceptance gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--d1-landing", default=DEFAULT_D1_LANDING)
    parser.add_argument("--d2c-dir", default=DEFAULT_D2C_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--nim-endpoint", default=DEFAULT_NIM_ENDPOINT)
    parser.add_argument("--nim-model", default=DEFAULT_NIM_MODEL)
    parser.add_argument("--max-d3-partitions", type=int, default=None)
    args = parser.parse_args()
    report = run_f3_nyc_d10full_gate(
        project_root=args.project_root,
        d1_landing=args.d1_landing,
        d2c_dir=args.d2c_dir,
        output_dir=args.output_dir,
        nim_endpoint=args.nim_endpoint,
        nim_model=args.nim_model,
        max_d3_partitions=args.max_d3_partitions,
    )
    return 0 if str(report.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())

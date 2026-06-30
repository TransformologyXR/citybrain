from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from txr_citybrain_f3_nyc_d9_flow3_accepted_snapshot import (
    DEFAULT_D2C_DIR,
    DEFAULT_D3_DIR,
    DEFAULT_D4_DIR,
    DEFAULT_D5_DIR,
    DEFAULT_D6_DIR,
    DEFAULT_D7_DIR,
    DEFAULT_D8_DIR,
    DEFAULT_OUTPUT_DIR,
    run_f3_nyc_d9_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run F3-NYC-D9 Flow 3 accepted snapshot gate")
    parser.add_argument("--d2c-dir", default=DEFAULT_D2C_DIR)
    parser.add_argument("--d3-dir", default=DEFAULT_D3_DIR)
    parser.add_argument("--d4-dir", default=DEFAULT_D4_DIR)
    parser.add_argument("--d5-dir", default=DEFAULT_D5_DIR)
    parser.add_argument("--d6-dir", default=DEFAULT_D6_DIR)
    parser.add_argument("--d7-dir", default=DEFAULT_D7_DIR)
    parser.add_argument("--d8-dir", default=DEFAULT_D8_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = run_f3_nyc_d9_gate(
        d2c_dir=args.d2c_dir,
        d3_dir=args.d3_dir,
        d4_dir=args.d4_dir,
        d5_dir=args.d5_dir,
        d6_dir=args.d6_dir,
        d7_dir=args.d7_dir,
        d8_dir=args.d8_dir,
        output_dir=args.output_dir,
    )
    print(f"F3-NYC-D9: {report['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())

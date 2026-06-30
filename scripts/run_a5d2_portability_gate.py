from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from txr_citybrain_a5d2_spark_portability_pack import (  # noqa: E402
    DEFAULT_A4D2_DIR,
    DEFAULT_A5D1_DIR,
    DEFAULT_OUTPUT_DIR,
    print_report,
    run_a5d2_portability_gate_with_a4d2,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and gate the A5-D2 Spark/NIM/NeMo portability pack.")
    parser.add_argument("--input-dir", default=str(DEFAULT_A5D1_DIR))
    parser.add_argument("--a4d2-dir", default=str(DEFAULT_A4D2_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    report = run_a5d2_portability_gate_with_a4d2(args.input_dir, args.a4d2_dir, args.output_dir)
    print_report(report)
    return int(report.get("exit_code", 1))


if __name__ == "__main__":
    raise SystemExit(main())

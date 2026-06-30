from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_lon_d5_pld_planning_ingest import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, run_lon_d5_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LON-D5 PLD planning ingest gate")
    parser.add_argument("--input-dir", default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--borough", default="Lambeth")
    parser.add_argument("--max-records", type=int, default=1000)
    args = parser.parse_args()
    report = run_lon_d5_gate(args.input_dir, args.output_dir, args.borough, args.max_records)
    print(
        json.dumps(
            {
                "status": report["status"],
                "output_dir": args.output_dir,
                "counts": report["counts"],
                "join_rate_over_pld_uprns": report["join_rates"]["join_rate_over_pld_uprns"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_lon_d5b_pld_uprn_backfill import (
    DEFAULT_LON_D4_DIR,
    DEFAULT_LON_D5_DIR,
    DEFAULT_OS_SAMPLE_DIR,
    DEFAULT_OUTPUT_DIR,
    run_lon_d5b_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LON-D5b PLD-driven UPRN backfill gate")
    parser.add_argument("--lon-d4-dir", default=DEFAULT_LON_D4_DIR)
    parser.add_argument("--lon-d5-dir", default=DEFAULT_LON_D5_DIR)
    parser.add_argument("--os-sample-dir", default=DEFAULT_OS_SAMPLE_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-target-uprn", type=int, default=1000)
    args = parser.parse_args()
    report = run_lon_d5b_gate(args.lon_d4_dir, args.lon_d5_dir, args.os_sample_dir, args.output_dir, args.max_target_uprn)
    print(
        json.dumps(
            {
                "status": report["status"],
                "output_dir": args.output_dir,
                "counts": report["counts"],
                "connected_path_smoke": report["connected_path_smoke"]["result"],
                "join_rate_after_backfill": report["rejoin_rates"]["join_rate_after_backfill"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

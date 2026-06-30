from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_lon_d5c_lids_confirmed_identity_bridge import (
    DEFAULT_LON_D4_DIR,
    DEFAULT_LON_D5B_DIR,
    DEFAULT_LON_D5_DIR,
    DEFAULT_OS_SAMPLE_DIR,
    DEFAULT_OUTPUT_DIR,
    run_lon_d5c_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LON-D5c LIDS-confirmed PLD identity bridge gate")
    parser.add_argument("--lon-d4-dir", default=DEFAULT_LON_D4_DIR)
    parser.add_argument("--lon-d5-dir", default=DEFAULT_LON_D5_DIR)
    parser.add_argument("--lon-d5b-dir", default=DEFAULT_LON_D5B_DIR)
    parser.add_argument("--os-sample-dir", default=DEFAULT_OS_SAMPLE_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-paths", type=int, default=100)
    args = parser.parse_args()
    report = run_lon_d5c_gate(args.lon_d4_dir, args.lon_d5_dir, args.lon_d5b_dir, args.os_sample_dir, args.output_dir, args.max_paths)
    print(
        json.dumps(
            {
                "status": report["status"],
                "output_dir": args.output_dir,
                "counts": report["counts"],
                "connected_path_smoke": report["connected_path_smoke"]["result"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

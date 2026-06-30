from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_lon_d6_enforcement_building_control import (
    DEFAULT_LON_D4_DIR,
    DEFAULT_LON_D5C_DIR,
    DEFAULT_LON_D5_DIR,
    DEFAULT_OUTPUT_DIR,
    run_lon_d6_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LON-D6 Lambeth enforcement/building-control gate")
    parser.add_argument("--lon-d4-dir", default=DEFAULT_LON_D4_DIR)
    parser.add_argument("--lon-d5-dir", default=DEFAULT_LON_D5_DIR)
    parser.add_argument("--lon-d5c-dir", default=DEFAULT_LON_D5C_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--borough", default="Lambeth")
    parser.add_argument("--max-records", type=int, default=500)
    parser.add_argument("--run-d6b-if-possible", action="store_true", default=True)
    args = parser.parse_args()
    report = run_lon_d6_gate(
        args.lon_d4_dir,
        args.lon_d5_dir,
        args.lon_d5c_dir,
        args.output_dir,
        args.borough,
        args.max_records,
        args.run_d6b_if_possible,
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "output_dir": args.output_dir,
                "d6a_classification": report["source_classification"]["classification"],
                "sources_probed": report["counts"]["sources_probed"],
                "d6b_run": report["ingest_report"]["d6b_run"],
                "connected_path_smoke": report["connected_path_smoke"]["result"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["status"] in {"PASS", "PASS_D6A_ONLY_SOURCE_LIMITATION"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

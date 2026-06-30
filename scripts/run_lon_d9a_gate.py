from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_lon_d9a_raw_inventory import DEFAULT_OUTPUT_DIR, DEFAULT_RAW_ROOT, run_lon_d9a_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LON-D9A raw London data inventory gate")
    parser.add_argument("--raw-root", default=DEFAULT_RAW_ROOT)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-schema-sample-rows", type=int, default=10000)
    parser.add_argument("--max-row-count-scan-mb", type=int, default=2048)
    args = parser.parse_args()
    report = run_lon_d9a_gate(
        args.raw_root,
        args.output_dir,
        args.max_schema_sample_rows,
        args.max_row_count_scan_mb,
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "output_dir": args.output_dir,
                "files_inventoried": report["counts"]["files_inventoried"],
                "d9b_readiness": report["counts"]["d9b_readiness"],
                "d9c_readiness": report["counts"]["d9c_readiness"],
                "manual_review_needed": report["counts"]["manual_review_needed"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_xdata_d2_r1_four_city_bulk_landing_reconciliation_refresh import (
    DEFAULT_D1_OUTPUT_DIR,
    DEFAULT_LANDING_ROOT,
    DEFAULT_OUTPUT_DIR,
    PASS_STATUSES,
    print_final_report,
    run_xdata_d2_r1,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run XDATA-D2-R1 reconciliation refresh gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--d1-output-dir", default=DEFAULT_D1_OUTPUT_DIR)
    parser.add_argument("--landing-root", default=DEFAULT_LANDING_ROOT)
    args = parser.parse_args()
    report = run_xdata_d2_r1(args.project_root, args.output_dir, args.d1_output_dir, args.landing_root)
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())

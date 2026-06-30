from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_xdata_d2_four_city_bulk_landing_reconciliation import (
    DEFAULT_D1_OUTPUT_DIR,
    DEFAULT_LANDING_ROOT,
    DEFAULT_OUTPUT_DIR,
    PASS_STATUSES,
    print_final_report,
    run_xdata_d2,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run XDATA-D2 four-city bulk landing reconciliation gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--d1-output-dir", default=DEFAULT_D1_OUTPUT_DIR)
    parser.add_argument("--landing-root", default=DEFAULT_LANDING_ROOT)
    args = parser.parse_args()

    report = run_xdata_d2(
        project_root=args.project_root,
        output_dir=args.output_dir,
        d1_output_dir=args.d1_output_dir,
        landing_root=args.landing_root,
    )
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())

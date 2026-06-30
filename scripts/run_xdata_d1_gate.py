from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_xdata_d1_four_city_bulk_landing import (
    DEFAULT_CONFIG,
    DEFAULT_LANDING_ROOT,
    DEFAULT_OUTPUT_DIR,
    PASS_STATUSES,
    print_final_report,
    run_xdata_d1,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run XDATA-D1 bulk official source landing")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--landing-root", default=DEFAULT_LANDING_ROOT)
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    parser.add_argument("--city", choices=["nyc", "chicago", "london", "barcelona"], default=None)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()

    report = run_xdata_d1(
        project_root=args.project_root,
        output_dir=args.output_dir,
        landing_root=args.landing_root,
        config_path=args.config,
        city=args.city,
        run_gates=args.run_gates,
    )
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_lon_flowx_expansion_run import (
    DEFAULT_F3X_D1_DIR,
    DEFAULT_LANDING_DIR,
    DEFAULT_OUTPUT_DIR,
    PASS_STATUSES,
    print_final_report,
    run_lon_flowx_expansion,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run London flow-extension expansion path D2-D6")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--landing-dir", default=DEFAULT_LANDING_DIR)
    parser.add_argument("--f3x-d1-dir", default=DEFAULT_F3X_D1_DIR)
    args = parser.parse_args()

    report = run_lon_flowx_expansion(
        project_root=args.project_root,
        output_dir=args.output_dir,
        landing_dir=args.landing_dir,
        f3x_d1_dir=args.f3x_d1_dir,
    )
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())

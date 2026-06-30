from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_chi_f4x_d5_hero_freeze_package import (
    DEFAULT_OUTPUT_DIR,
    PASS_STATUSES,
    print_final_report,
    run_chi_f4x_d5,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CHI-F4X-D5 hero freeze package gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = run_chi_f4x_d5(args.project_root, args.output_dir)
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())

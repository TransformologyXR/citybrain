from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_nightrun_d1_overnight_orchestrator import (
    DEFAULT_OUTPUT_DIR,
    PASS_STATUSES,
    print_final_report,
    run_nightrun_d1,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run NIGHTRUN-D1 overnight current-work completion gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-gates", action="store_true")
    parser.add_argument("--max-runtime-hours", type=float, default=8.0)
    parser.add_argument("--check-interval-minutes", type=float, default=15.0)
    parser.add_argument("--continue-on-failure", action="store_true")
    parser.add_argument("--rerun-passed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = run_nightrun_d1(
        project_root=args.project_root,
        output_dir=args.output_dir,
        run_gates=args.run_gates,
        max_runtime_hours=args.max_runtime_hours,
        check_interval_minutes=args.check_interval_minutes,
        continue_on_failure=args.continue_on_failure,
        rerun_passed=args.rerun_passed,
        dry_run=args.dry_run,
    )
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())

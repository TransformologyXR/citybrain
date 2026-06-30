from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_barc_d1a_targeted_source_landing_recovery import (
    DEFAULT_D1_LANDING_DIR,
    DEFAULT_D1_OUTPUT_DIR,
    DEFAULT_LANDING_DIR,
    DEFAULT_OUTPUT_DIR,
    PASS_STATUSES,
    print_final_report,
    run_barc_d1a_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run BARC-D1A Barcelona targeted source landing recovery gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--landing-dir", default=DEFAULT_LANDING_DIR)
    parser.add_argument("--d1-output-dir", default=DEFAULT_D1_OUTPUT_DIR)
    parser.add_argument("--d1-landing-dir", default=DEFAULT_D1_LANDING_DIR)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--max-sample-bytes", type=int, default=1_048_576)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()

    report = run_barc_d1a_gate(
        project_root=args.project_root,
        output_dir=args.output_dir,
        landing_dir=args.landing_dir,
        d1_output_dir=args.d1_output_dir,
        d1_landing_dir=args.d1_landing_dir,
        timeout=args.timeout,
        retries=args.retries,
        max_sample_bytes=args.max_sample_bytes,
    )
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES and report["harness"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

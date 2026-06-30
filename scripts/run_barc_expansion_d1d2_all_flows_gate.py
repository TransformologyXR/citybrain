from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_barc_expansion_d1d2_all_flows import (
    DEFAULT_D1A_DIR,
    DEFAULT_D1_DIR,
    DEFAULT_OUTPUT_DIR,
    PASS_STATUSES,
    print_final_report,
    run_barc_expansion_d1d2_all_flows_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Barcelona expansion D1/D2 all-flow contracts")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--d1-dir", default=DEFAULT_D1_DIR)
    parser.add_argument("--d1a-dir", default=DEFAULT_D1A_DIR)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()

    report = run_barc_expansion_d1d2_all_flows_gate(
        project_root=args.project_root,
        output_dir=args.output_dir,
        d1_dir=args.d1_dir,
        d1a_dir=args.d1a_dir,
    )
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES and report["harness"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

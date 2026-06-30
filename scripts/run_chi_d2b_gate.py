from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_chi_d2b_base_identity_refresh import (  # noqa: E402
    DEFAULT_D1_LANDING,
    DEFAULT_D1_OUTPUT,
    DEFAULT_D1B_LANDING,
    DEFAULT_D1B_OUTPUT,
    DEFAULT_D2_OUTPUT,
    DEFAULT_OUTPUT_DIR,
    run_chi_d2b_gate,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run CHI-D2B gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--d1-output", "--chi-d1-output-dir", dest="d1_output", default=DEFAULT_D1_OUTPUT)
    parser.add_argument("--d1-landing", "--chi-d1-landing-dir", dest="d1_landing", default=DEFAULT_D1_LANDING)
    parser.add_argument("--d1b-output", "--chi-d1b-output-dir", dest="d1b_output", default=DEFAULT_D1B_OUTPUT)
    parser.add_argument("--d1b-landing", "--chi-d1b-landing-dir", dest="d1b_landing", default=DEFAULT_D1B_LANDING)
    parser.add_argument("--d2-output", "--chi-d2-dir", dest="d2_output", default=DEFAULT_D2_OUTPUT)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_chi_d2b_gate(
        project_root=args.project_root,
        d1_output=args.d1_output,
        d1_landing=args.d1_landing,
        d1b_output=args.d1b_output,
        d1b_landing=args.d1b_landing,
        d2_output=args.d2_output,
        output_dir=args.output_dir,
    )
    print(result)
    return 0 if str(result.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())

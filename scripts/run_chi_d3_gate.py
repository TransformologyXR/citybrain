from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_chi_d3_civic_event_ingest_flow_readiness import (  # noqa: E402
    DEFAULT_D1_LANDING,
    DEFAULT_D1_OUTPUT,
    DEFAULT_D1B_LANDING,
    DEFAULT_D1B_OUTPUT,
    DEFAULT_D2B_DIR,
    DEFAULT_OUTPUT_DIR,
    run_chi_d3_gate,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run CHI-D3 gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--chi-d1-output-dir", default=DEFAULT_D1_OUTPUT)
    parser.add_argument("--chi-d1-landing-dir", default=DEFAULT_D1_LANDING)
    parser.add_argument("--chi-d1b-output-dir", default=DEFAULT_D1B_OUTPUT)
    parser.add_argument("--chi-d1b-landing-dir", default=DEFAULT_D1B_LANDING)
    parser.add_argument("--chi-d2b-dir", default=DEFAULT_D2B_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_chi_d3_gate(
        project_root=args.project_root,
        chi_d1_output_dir=args.chi_d1_output_dir,
        chi_d1_landing_dir=args.chi_d1_landing_dir,
        chi_d1b_output_dir=args.chi_d1b_output_dir,
        chi_d1b_landing_dir=args.chi_d1b_landing_dir,
        chi_d2b_dir=args.chi_d2b_dir,
        output_dir=args.output_dir,
    )
    print(result)
    return 0 if str(result.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())

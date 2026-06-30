from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_chi_d2_base_identity_geography_ingest import (  # noqa: E402
    DEFAULT_CHI_D1_LANDING,
    DEFAULT_CHI_D1_OUTPUT,
    DEFAULT_OUTPUT_DIR,
    run_chi_d2_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CHI-D2 base identity/geography ingest gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--chi-d1-output-dir", default=DEFAULT_CHI_D1_OUTPUT)
    parser.add_argument("--chi-d1-landing-dir", default=DEFAULT_CHI_D1_LANDING)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--optional-chi-d1b-output-dir", default=None)
    parser.add_argument("--optional-chi-d1b-landing-dir", default=None)
    args = parser.parse_args()
    report = run_chi_d2_gate(
        project_root=args.project_root,
        chi_d1_output_dir=args.chi_d1_output_dir,
        chi_d1_landing_dir=args.chi_d1_landing_dir,
        output_dir=args.output_dir,
        optional_chi_d1b_output_dir=args.optional_chi_d1b_output_dir,
        optional_chi_d1b_landing_dir=args.optional_chi_d1b_landing_dir,
    )
    return 0 if str(report.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())

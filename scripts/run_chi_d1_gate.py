from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_chi_d1_deep_source_api_scout import PASS_STATUSES, print_final_report, run_chi_d1_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CHI-D1 Chicago deep source/API scout gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=r"outputs\chi_d1_chicago_deep_source_api_scout")
    parser.add_argument("--landing-dir", default=r"data_landing\chi_d1_official_sources_v1")
    parser.add_argument("--socrata-page-size", type=int, default=50_000)
    parser.add_argument("--pull-full-small-sources", action="store_true")
    parser.add_argument("--pull-large-sources", action="store_true")
    parser.add_argument("--divvy-months", type=int, default=3)
    parser.add_argument("--crime-years", type=int, default=5)
    parser.add_argument("--cta-live-sample-limit", type=int, default=100)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()

    report = run_chi_d1_gate(
        project_root=args.project_root,
        output_dir=args.output_dir,
        landing_dir=args.landing_dir,
        socrata_page_size=args.socrata_page_size,
        pull_full_small_sources=args.pull_full_small_sources,
        pull_large_sources=args.pull_large_sources,
        divvy_months=args.divvy_months,
        crime_years=args.crime_years,
        cta_live_sample_limit=args.cta_live_sample_limit,
    )
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())

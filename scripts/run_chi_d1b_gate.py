from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_chi_d1b_extended_source_landing import PASS_STATUSES, print_final_report, run_chi_d1b_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CHI-D1B Chicago extended source landing gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--chi-d1-output-dir", default=r"outputs\chi_d1_chicago_deep_source_api_scout")
    parser.add_argument("--chi-d1-landing-dir", default=r"data_landing\chi_d1_official_sources_v1")
    parser.add_argument("--output-dir", default=r"outputs\chi_d1b_chicago_extended_source_landing")
    parser.add_argument("--landing-dir", default=r"data_landing\chi_d1b_extended_sources_v1")
    parser.add_argument("--socrata-page-size", type=int, default=50_000)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--no-311", action="store_true")
    parser.add_argument("--no-crimes", action="store_true")
    parser.add_argument("--no-crashes", action="store_true")
    parser.add_argument("--no-buildings", action="store_true")
    parser.add_argument("--no-permits-violations", action="store_true")
    parser.add_argument("--no-divvy", action="store_true")
    parser.add_argument("--no-cook-parcels", action="store_true")
    parser.add_argument("--no-open-air", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()

    report = run_chi_d1b_gate(
        project_root=args.project_root,
        chi_d1_output_dir=args.chi_d1_output_dir,
        chi_d1_landing_dir=args.chi_d1_landing_dir,
        output_dir=args.output_dir,
        landing_dir=args.landing_dir,
        socrata_page_size=args.socrata_page_size,
        pull_311=not args.no_311,
        pull_crimes=not args.no_crimes,
        pull_crashes=not args.no_crashes,
        pull_buildings=not args.no_buildings,
        pull_permits_violations=not args.no_permits_violations,
        pull_divvy=not args.no_divvy,
        pull_cook_parcels=not args.no_cook_parcels,
        pull_open_air=not args.no_open_air,
        workers=args.workers,
    )
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())

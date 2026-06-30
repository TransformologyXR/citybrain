from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_sg_d1_source_api_scout import PASS_STATUSES, print_final_report, run_sg_d1_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SG-D1 Singapore source/API scout gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=r"outputs\sg_d1_singapore_source_api_scout")
    parser.add_argument("--landing-dir", default=r"data_landing\sg_d1_official_sources_v1")
    parser.add_argument("--run-lta", action="store_true")
    parser.add_argument("--run-nea-public", action="store_true")
    parser.add_argument("--run-onemap", action="store_true")
    parser.add_argument("--lta-page-size", type=int, default=500)
    parser.add_argument("--bus-arrival-sample-stops", type=int, default=150)
    parser.add_argument("--traffic-image-sample-downloads", type=int, default=10)
    parser.add_argument("--passenger-volume-months", type=int, default=1)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()

    run_lta = args.run_lta or not (args.run_nea_public or args.run_onemap)
    run_nea_public = args.run_nea_public or not (args.run_lta or args.run_onemap)
    run_onemap = args.run_onemap or not (args.run_lta or args.run_nea_public)
    report = run_sg_d1_gate(
        project_root=args.project_root,
        output_dir=args.output_dir,
        landing_dir=args.landing_dir,
        run_lta=run_lta,
        run_nea_public=run_nea_public,
        run_onemap=run_onemap,
        lta_page_size=args.lta_page_size,
        bus_arrival_sample_stops=args.bus_arrival_sample_stops,
        traffic_image_sample_downloads=args.traffic_image_sample_downloads,
        passenger_volume_months=args.passenger_volume_months,
    )
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())

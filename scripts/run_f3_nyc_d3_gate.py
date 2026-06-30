from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_f3_nyc_d3_affected_asset_response_context import run_f3_nyc_d3_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run F3-NYC-D3 gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--d2-dir", default="outputs/f3_nyc_d2_fdny_incident_response_slice_ingest")
    parser.add_argument("--asset-root", action="append", dest="asset_roots", default=[])
    parser.add_argument("--output-dir", default="outputs/f3_nyc_d3_affected_asset_response_context")
    parser.add_argument("--max-events", type=int, default=50_000)
    parser.add_argument("--asset-distance-threshold-m", type=float, default=30.0)
    parser.add_argument("--nearest-firehouses", type=int, default=3)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_f3_nyc_d3_gate(
        project_root=args.project_root,
        d2_dir=args.d2_dir,
        asset_roots=args.asset_roots,
        output_dir=args.output_dir,
        max_events=args.max_events,
        asset_distance_threshold_m=args.asset_distance_threshold_m,
        nearest_firehouses=args.nearest_firehouses,
    )
    return 0 if report["status"] in {"PASS", "PASS_WITH_LOCATION_CONFIDENCE_TIERS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

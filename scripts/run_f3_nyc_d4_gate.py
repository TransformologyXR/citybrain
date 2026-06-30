from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_f3_nyc_d4_candidate_prioritization_review_routing import run_f3_nyc_d4_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run F3-NYC-D4 gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--d3-dir", default="outputs/f3_nyc_d3_affected_asset_response_context")
    parser.add_argument("--d2-dir", default=None)
    parser.add_argument("--output-dir", default="outputs/f3_nyc_d4_candidate_prioritization_review_routing")
    parser.add_argument("--max-candidates", type=int, default=250)
    parser.add_argument("--max-routes", type=int, default=25)
    parser.add_argument("--stops-per-route", type=int, default=10)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_f3_nyc_d4_gate(
        project_root=args.project_root,
        d3_dir=args.d3_dir,
        d2_dir=args.d2_dir,
        output_dir=args.output_dir,
        max_candidates=args.max_candidates,
        max_routes=args.max_routes,
        stops_per_route=args.stops_per_route,
    )
    return 0 if report["status"] in {"PASS", "PASS_WITH_OPERATOR_REVIEW_ROUTING_LIMITATION"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

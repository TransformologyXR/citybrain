from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_a6d1_cuopt_review_optimizer import run_a6d1_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the A6-D1 cuOpt operational review optimizer gate.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--candidate-limit", type=int, default=120)
    parser.add_argument("--route-candidate-limit", type=int, default=60)
    parser.add_argument("--no-cuopt", action="store_true")
    args = parser.parse_args()
    report = run_a6d1_gate(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        candidate_limit=args.candidate_limit,
        route_candidate_limit=args.route_candidate_limit,
        use_cuopt=not args.no_cuopt,
    )
    print(f"A6-D1 cuOpt Operational Review Optimizer v1: {report.get('status')}")
    print(f"Output: {report.get('output_dir', args.output_dir)}")
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

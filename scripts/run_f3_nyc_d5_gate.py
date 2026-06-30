from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_f3_nyc_d5_governed_evidence_briefing import run_f3_nyc_d5_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run F3-NYC-D5 gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--d4-dir", default="outputs/f3_nyc_d4_candidate_prioritization_review_routing")
    parser.add_argument("--d3-dir", default="outputs/f3_nyc_d3_affected_asset_response_context")
    parser.add_argument("--output-dir", default="outputs/f3_nyc_d5_governed_evidence_briefing")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_f3_nyc_d5_gate(args.project_root, args.d4_dir, args.d3_dir, args.output_dir)
    return 0 if report["status"] in {"PASS", "PASS_WITH_GOVERNED_DETERMINISTIC_BRIEFINGS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

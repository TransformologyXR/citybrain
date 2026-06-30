from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_barc_d1_deep_source_api_scout import PASS_STATUSES, print_final_report, run_barc_d1_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run BARC-D1 Barcelona deep source/API scout gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=r"outputs\barc_d1_deep_source_api_scout")
    parser.add_argument("--landing-dir", default=r"data_landing\barc_d1_official_sources_v1")
    parser.add_argument("--timeout", type=float, default=6.0)
    parser.add_argument("--max-sample-bytes", type=int, default=262_144)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()

    report = run_barc_d1_gate(
        project_root=args.project_root,
        output_dir=args.output_dir,
        landing_dir=args.landing_dir,
        timeout=args.timeout,
        max_sample_bytes=args.max_sample_bytes,
    )
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES and report["harness"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_chi_flowx_d2_join_hardening import run_chi_flowx_d2_join_hardening


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CHI-FLOWX-D2 parallel Chicago join hardening.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--d1-dir", default="outputs/chi_flowx_d1_parallel_expansion_scouts")
    parser.add_argument("--d1b-dir", default="outputs/chi_d1b_chicago_extended_source_landing")
    parser.add_argument("--d2b-dir", default="outputs/chi_d2b_base_identity_refresh")
    parser.add_argument("--d3b-dir", default="outputs/chi_d3_civic_event_ingest_flow_readiness_d3b_expanded_d1b")
    parser.add_argument("--d5-dir", default="outputs/chi_f1f7_d5_dual_flow_accepted_snapshot")
    parser.add_argument("--landing-dir", default="data_landing/chi_d1b_extended_sources_v1")
    parser.add_argument("--output-dir", default="outputs/chi_flowx_d2_parallel_join_hardening")
    args = parser.parse_args()

    result = run_chi_flowx_d2_join_hardening(
        project_root=args.project_root,
        d1_dir=args.d1_dir,
        d1b_dir=args.d1b_dir,
        d2b_dir=args.d2b_dir,
        d3b_dir=args.d3b_dir,
        d5_dir=args.d5_dir,
        landing_dir=args.landing_dir,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if str(result.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())

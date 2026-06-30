from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_chi_d3b_civic_event_refresh_expanded_d1b import run_chi_d3b_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CHI-D3B civic/event refresh from expanded D1B.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--chi-d1-output-dir", default="outputs/chi_d1_chicago_deep_source_api_scout")
    parser.add_argument("--chi-d1-landing-dir", default="data_landing/chi_d1_official_sources_v1")
    parser.add_argument("--chi-d1b-output-dir", default="outputs/chi_d1b_chicago_extended_source_landing")
    parser.add_argument("--chi-d1b-landing-dir", default="data_landing/chi_d1b_extended_sources_v1")
    parser.add_argument("--chi-d2b-dir", default="outputs/chi_d2b_base_identity_refresh")
    parser.add_argument("--previous-d3-dir", default="outputs/chi_d3_civic_event_ingest_flow_readiness")
    parser.add_argument("--output-dir", default="outputs/chi_d3_civic_event_ingest_flow_readiness_d3b_expanded_d1b")
    args = parser.parse_args()

    result = run_chi_d3b_gate(
        project_root=args.project_root,
        chi_d1_output_dir=args.chi_d1_output_dir,
        chi_d1_landing_dir=args.chi_d1_landing_dir,
        chi_d1b_output_dir=args.chi_d1b_output_dir,
        chi_d1b_landing_dir=args.chi_d1b_landing_dir,
        chi_d2b_dir=args.chi_d2b_dir,
        previous_d3_dir=args.previous_d3_dir,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if str(result.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())

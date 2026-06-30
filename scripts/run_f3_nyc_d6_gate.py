from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_f3_nyc_d6_live_spark_nim_replay import run_f3_nyc_d6_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run F3-NYC-D6 gate")
    parser.add_argument("--d5-dir", default="outputs/f3_nyc_d5_governed_evidence_briefing")
    parser.add_argument("--d4-dir", default="outputs/f3_nyc_d4_candidate_prioritization_review_routing")
    parser.add_argument("--d3-dir", default="outputs/f3_nyc_d3_affected_asset_response_context")
    parser.add_argument("--d2-dir", default="outputs/f3_nyc_d2_fdny_incident_response_slice_ingest")
    parser.add_argument("--d1-dir", default="outputs/f3_nyc_d1_source_inventory_schema_mapping")
    parser.add_argument("--source-landing-dir", default="data_landing/f3_nyc_d1_official_sources_v1")
    parser.add_argument("--output-dir", default="outputs/f3_nyc_d6_live_spark_nim_replay")
    parser.add_argument("--nim-endpoint", default="http://192.168.1.103:8000/v1")
    parser.add_argument("--nim-model", default="meta/llama-3.1-8b-instruct")
    parser.add_argument("--run-live-nim", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_f3_nyc_d6_gate(
        d5_dir=args.d5_dir,
        d4_dir=args.d4_dir,
        d3_dir=args.d3_dir,
        d2_dir=args.d2_dir,
        d1_dir=args.d1_dir,
        source_landing_dir=args.source_landing_dir,
        output_dir=args.output_dir,
        nim_endpoint=args.nim_endpoint,
        nim_model=args.nim_model,
        run_live_nim=args.run_live_nim,
    )
    return 0 if report["status"] in {"PASS", "PASS_WITH_LIVE_NIM_NOT_RUN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

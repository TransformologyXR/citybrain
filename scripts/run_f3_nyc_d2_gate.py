from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_f3_nyc_d2_fdny_incident_response_slice_ingest import run_f3_nyc_d2_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run F3-NYC-D2 gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--raw-root", action="append", dest="raw_roots", default=[])
    parser.add_argument("--d1-dir", default="outputs/f3_nyc_d1_source_inventory_schema_mapping")
    parser.add_argument("--output-dir", default="outputs/f3_nyc_d2_fdny_incident_response_slice_ingest")
    parser.add_argument("--sample-rows", type=int, default=25)
    parser.add_argument("--max-rows-per-source", type=int, default=None)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_f3_nyc_d2_gate(
        project_root=args.project_root,
        raw_roots=args.raw_roots,
        d1_dir=args.d1_dir,
        output_dir=args.output_dir,
        sample_rows=args.sample_rows,
        max_rows_per_source=args.max_rows_per_source,
    )
    return 0 if report["status"] in {"PASS", "PASS_WITH_BOUNDED_SAMPLE", "PASS_WITH_SOURCE_LIMITATION"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

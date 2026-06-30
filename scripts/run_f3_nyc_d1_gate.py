from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_f3_nyc_d1_source_inventory_schema_mapping import run_f3_nyc_d1_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run F3-NYC-D1 gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--raw-root", action="append", dest="raw_roots", default=[])
    parser.add_argument("--output-dir", default="outputs/f3_nyc_d1_source_inventory_schema_mapping")
    parser.add_argument("--sample-rows", type=int, default=25)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_f3_nyc_d1_gate(
        project_root=args.project_root,
        raw_roots=args.raw_roots,
        output_dir=args.output_dir,
        sample_rows=args.sample_rows,
    )
    return 0 if report["status"] in {"PASS", "PASS_WITH_MISSING_SOURCES"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

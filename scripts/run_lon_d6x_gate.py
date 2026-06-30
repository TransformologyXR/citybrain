#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_lon_d6x_borough_enforcement_source_scout import run_lon_d6x_gate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs/lon_d6x_borough_enforcement_source_scout")
    parser.add_argument("--raw-output-dir", default="data_landing/london_d6x_source_scout")
    parser.add_argument("--max-camden-records", type=int, default=500000)
    parser.add_argument("--download-havering-pdfs", action="store_true")
    parser.add_argument("--max-havering-pdfs-per-year", type=int, default=999)
    parser.add_argument("--include-optional-hounslow", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    result = run_lon_d6x_gate(
        output_dir=args.output_dir,
        raw_output_dir=args.raw_output_dir,
        max_camden_records=args.max_camden_records,
        download_havering_pdfs=args.download_havering_pdfs,
        max_havering_pdfs_per_year=args.max_havering_pdfs_per_year,
        include_optional_hounslow=args.include_optional_hounslow,
        run_gates=args.run_gates,
    )
    status = result["final_report"]["status"]
    print(f"LON-D6X wrapper status: {status}")
    return 0 if status in {"PASS", "PASS_WITH_SOURCE_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_lon_d6b2_havering_enforcement_graph_integration import run_lon_d6b2_gate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--d6x-dir", default="outputs/lon_d6x_borough_enforcement_source_scout")
    parser.add_argument("--d9z-dir", default="outputs/lon_d9z_d9d2_accepted_snapshot")
    parser.add_argument("--d10z-dir", default="outputs/lon_d10z_d10_accepted_snapshot")
    parser.add_argument("--d10-dir", default="outputs/lon_d10_planning_context_enrichment")
    parser.add_argument("--output-dir", default="outputs/lon_d6b2_havering_enforcement_graph_integration")
    parser.add_argument("--publish-4070", action="store_true")
    parser.add_argument("--extract-pdf-text", action="store_true")
    parser.add_argument("--max-pdf-text-pages", type=int, default=3)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    result = run_lon_d6b2_gate(
        d6x_dir=args.d6x_dir,
        d9z_dir=args.d9z_dir,
        d10z_dir=args.d10z_dir,
        d10_dir=args.d10_dir,
        output_dir=args.output_dir,
        publish_4070=args.publish_4070,
        extract_pdf_text=args.extract_pdf_text,
        max_pdf_text_pages=args.max_pdf_text_pages,
    )
    status = result["harness"]["status"]
    print(f"LON-D6B2 wrapper status: {status}")
    return 0 if status in {"PASS", "PASS_WITH_IDENTITY_LIMITATION"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

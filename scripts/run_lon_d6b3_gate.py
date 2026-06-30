#!/usr/bin/env python3
"""CLI wrapper for LON-D6B3 Havering enforcement identity recovery."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_lon_d6b3_havering_enforcement_identity_recovery import run_lon_d6b3_gate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--d6x-dir", default="outputs/lon_d6x_borough_enforcement_source_scout")
    parser.add_argument("--d6b2-dir", default="outputs/lon_d6b2_havering_enforcement_graph_integration")
    parser.add_argument("--d9z-dir", default="outputs/lon_d9z_d9d2_accepted_snapshot")
    parser.add_argument("--d10z-dir", default="outputs/lon_d10z_d10_accepted_snapshot")
    parser.add_argument("--raw-root", default="data_landing/london_d9_raw")
    parser.add_argument("--output-dir", default="outputs/lon_d6b3_havering_enforcement_identity_recovery")
    parser.add_argument("--publish-4070", action="store_true")
    parser.add_argument("--allow-official-download-probe", action="store_true")
    parser.add_argument("--extract-pdf-text", action="store_true")
    parser.add_argument("--max-pdf-text-pages", type=int, default=5)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    result = run_lon_d6b3_gate(
        d6x_dir=args.d6x_dir,
        d6b2_dir=args.d6b2_dir,
        d9z_dir=args.d9z_dir,
        d10z_dir=args.d10z_dir,
        raw_root=args.raw_root,
        output_dir=args.output_dir,
        publish_4070=args.publish_4070,
        allow_official_download_probe=args.allow_official_download_probe,
        extract_pdf_text=args.extract_pdf_text,
        max_pdf_text_pages=args.max_pdf_text_pages,
    )
    harness = result["harness"]
    print(f"LON-D6B3 Havering Enforcement Identity Recovery: {harness['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if harness["status"] in {"PASS", "PASS_WITH_PARTIAL_IDENTITY_RECOVERY", "PASS_WITH_IDENTITY_LIMITATION_CONFIRMED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

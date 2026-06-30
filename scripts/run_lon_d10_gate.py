#!/usr/bin/env python3
"""CLI wrapper for LON-D10 planning-context enrichment."""

from __future__ import annotations

import argparse
import json

from txr_citybrain_lon_d10_planning_context_enrichment import run_lon_d10_gate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--d9z-dir", required=True)
    parser.add_argument("--d9e-d9d2-dir", required=True)
    parser.add_argument("--d9f-d9d2-dir", required=True)
    parser.add_argument("--raw-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-query-examples", type=int, default=25)
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args()
    report = run_lon_d10_gate(
        d9z_dir=args.d9z_dir,
        d9e_d9d2_dir=args.d9e_d9d2_dir,
        d9f_d9d2_dir=args.d9f_d9d2_dir,
        raw_root=args.raw_root,
        output_dir=args.output_dir,
        max_query_examples=args.max_query_examples,
        allow_download=args.allow_download,
    )
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

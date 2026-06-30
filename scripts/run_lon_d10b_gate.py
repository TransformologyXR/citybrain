#!/usr/bin/env python3
"""CLI wrapper for LON-D10B Local Plan semantic certification."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_lon_d10b_local_plan_semantic_certification import run_lon_d10b_gate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--d10-dir", required=True)
    parser.add_argument("--d10z-dir", default=None)
    parser.add_argument("--raw-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-query-examples", type=int, default=25)
    parser.add_argument("--publish-4070", action="store_true")
    args = parser.parse_args()
    report = run_lon_d10b_gate(
        d10_dir=args.d10_dir,
        d10z_dir=args.d10z_dir,
        raw_root=args.raw_root,
        output_dir=args.output_dir,
        max_query_examples=args.max_query_examples,
        publish_4070=args.publish_4070,
    )
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

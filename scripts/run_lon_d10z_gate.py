#!/usr/bin/env python3
"""CLI wrapper for LON-D10Z accepted D10 snapshot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_lon_d10z_acceptance_snapshot import run_lon_d10z_gate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--d9z-dir", required=True)
    parser.add_argument("--d10-dir", required=True)
    parser.add_argument("--mission-control", required=True)
    parser.add_argument("--todo", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--sync-4070", action="store_true")
    args = parser.parse_args()
    report = run_lon_d10z_gate(
        d9z_dir=args.d9z_dir,
        d10_dir=args.d10_dir,
        mission_control_html=args.mission_control,
        todo_html=args.todo,
        output_dir=args.output_dir,
        sync_4070=args.sync_4070,
    )
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""CLI wrapper for LON-D12 London NeMo/NIM wrapper."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_lon_d12_nemo_nim_wrapper import run_lon_d12_gate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--d9z-dir", required=True)
    parser.add_argument("--d10z-dir", required=True)
    parser.add_argument("--d10-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--run-live-nim", action="store_true")
    parser.add_argument("--nim-endpoint", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--nim-model", default="meta/llama-3.1-8b-instruct")
    args = parser.parse_args()
    report = run_lon_d12_gate(
        d9z_dir=args.d9z_dir,
        d10z_dir=args.d10z_dir,
        d10_dir=args.d10_dir,
        output_dir=args.output_dir,
        run_live_nim=args.run_live_nim,
        nim_endpoint=args.nim_endpoint,
        nim_model=args.nim_model,
    )
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return 0 if report.get("status") in {"PASS", "PASS_WITH_LIVE_NIM_NOT_RUN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

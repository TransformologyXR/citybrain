from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_lon_d4_identity_backbone_ingest import DEFAULT_INPUT_DIR, DEFAULT_OUTPUT_DIR, run_lon_d4_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LON-D4 identity backbone gate")
    parser.add_argument("--input-dir", default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--borough", default="Lambeth")
    parser.add_argument("--max-uprn", type=int, default=50000)
    args = parser.parse_args()
    report = run_lon_d4_gate(args.input_dir, args.output_dir, args.borough, args.max_uprn)
    print(json.dumps({"status": report["status"], "output_dir": args.output_dir, "counts": report["counts"]}, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

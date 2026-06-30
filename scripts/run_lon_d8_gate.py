from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_lon_d8_operator_query_contract import DEFAULT_LON_D7_DIR, DEFAULT_OUTPUT_DIR, run_lon_d8_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LON-D8 London operator-query contract gate")
    parser.add_argument("--lon-d7-dir", default=DEFAULT_LON_D7_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-examples", type=int, default=25)
    args = parser.parse_args()
    report = run_lon_d8_gate(args.lon_d7_dir, args.output_dir, args.max_examples)
    print(
        json.dumps(
            {
                "status": report["status"],
                "output_dir": args.output_dir,
                "query_types_passed": report["counts"]["query_types_passed"],
                "query_types_required": report["counts"]["query_types_required"],
                "evidence_bundles_emitted": report["counts"]["evidence_bundles_emitted"],
                "briefings_emitted": report["counts"]["briefings_emitted"],
                "grounding": report["grounding"]["status"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_nyc_expansion_d2_all_flows import (
    DEFAULT_D1_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SAMPLE_LIMIT,
    run_nyc_expansion_d2_all_flows_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all NYC expansion D2 gates.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--d1-dir", default=DEFAULT_D1_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sample-limit", type=int, default=DEFAULT_SAMPLE_LIMIT)
    args = parser.parse_args()
    result = run_nyc_expansion_d2_all_flows_gate(
        project_root=args.project_root,
        d1_dir=args.d1_dir,
        output_dir=args.output_dir,
        sample_limit=args.sample_limit,
    )
    print(json.dumps({"status": result["status"], "gates": result["gates"], "output": result["output"]}, indent=2, sort_keys=True))
    return 0 if result["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())

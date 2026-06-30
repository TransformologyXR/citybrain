from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_nyc_expansion_potential_d1 import (
    DEFAULT_F3_ACCEPTED_DIR,
    DEFAULT_HARVEST_DIR,
    DEFAULT_OUTPUT_DIR,
    run_nyc_expansion_potential_d1_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run NYC expansion potential D1 readiness gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--f3-accepted-dir", default=DEFAULT_F3_ACCEPTED_DIR)
    parser.add_argument("--harvest-dir", default=DEFAULT_HARVEST_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    result = run_nyc_expansion_potential_d1_gate(
        project_root=args.project_root,
        f3_accepted_dir=args.f3_accepted_dir,
        harvest_dir=args.harvest_dir,
        output_dir=args.output_dir,
    )
    print(json.dumps({"status": result["status"], "gates": result["gates"], "output": result["output"]}, indent=2, sort_keys=True))
    return 0 if result["status"] != "FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())

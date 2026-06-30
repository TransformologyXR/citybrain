from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_pv1_sdf_d1_factory_contract import DEFAULT_OUTPUT_DIR, run_pv1_sdf_d1_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-SDF-D1 factory contract gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    result = run_pv1_sdf_d1_gate(project_root=args.project_root, output_dir=args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

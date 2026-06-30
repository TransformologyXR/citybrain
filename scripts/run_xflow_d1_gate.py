from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_xflow_d1_cross_city_expansion_reconciliation import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    final_print,
    run_xflow_d1_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run XFLOW-D1 cross-city expansion reconciliation gate.")
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    result = run_xflow_d1_gate(project_root=args.project_root, output_dir=args.output_dir)
    print(final_print(result))
    print(json.dumps({"status": result["status"], "output_dir": result["output_dir"]}, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PASS_CROSS_CITY_EXPANSION_RECONCILIATION", "PASS_WITH_OPTIONAL_INPUT_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

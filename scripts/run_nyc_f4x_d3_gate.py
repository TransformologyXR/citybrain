from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_nyc_f4x_d3_mobility_environment_evidencebundles import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    final_print,
    run_nyc_f4x_d3_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run NYC-F4X-D3 mobility/environment EvidenceBundle gate.")
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    result = run_nyc_f4x_d3_gate(project_root=args.project_root, output_dir=args.output_dir)
    print(final_print(result))
    print(json.dumps({"status": result["status"], "output_dir": result["output_dir"]}, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PASS_MOBILITY_ENVIRONMENT_EVIDENCEBUNDLES", "PASS_WITH_SOURCE_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_pv1_infra_d2_3090_runtime_bootstrap import DEFAULT_OUTPUT_DIR
from txr_citybrain_pv1_infra_d2_3090_runtime_bootstrap import REMOTE_HOST
from txr_citybrain_pv1_infra_d2_3090_runtime_bootstrap import run_pv1_infra_d2_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-INFRA-D2 3090 runtime bootstrap gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--remote-host", default=REMOTE_HOST)
    parser.add_argument("--run-sync", action="store_true")
    args = parser.parse_args()

    result = run_pv1_infra_d2_gate(
        project_root=args.project_root,
        output_dir=args.output_dir,
        remote_host=args.remote_host,
        run_sync=args.run_sync,
    )
    print(result["final_print"])
    print(json.dumps({"status": result["status"], "output_dir": result["output_dir"], "missing_packages": result["missing_packages"]}, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PASS_3090_RUNTIME_BOOTSTRAPPED", "PASS_WITH_PYTHON_ENV_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

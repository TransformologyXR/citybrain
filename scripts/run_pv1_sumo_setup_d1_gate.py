from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_pv1_sumo_setup_d1 import run_pv1_sumo_setup_d1


def main() -> int:
    result = run_pv1_sumo_setup_d1(ROOT, "outputs/pv1_sumo_setup_d1")
    print(result["final_print"])
    print(json.dumps({"status": result["status"], "output_dir": result["output_dir"]}, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PASS_SUMO_READY", "PASS_SUMO_READY_WITH_LIMITATIONS", "PASS_SETUP_PARTIAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

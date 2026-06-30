from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_pv1_d19d20d21d22_platform_v1_snapshot import run_pv1_d19d20d21d22_gate


def main() -> int:
    result = run_pv1_d19d20d21d22_gate(ROOT)
    print(result["final_print"])
    print(json.dumps({"status": result["status"], "output_dir": result["gate_output"]}, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PASS_PLATFORM_V1_REVIEW_ONLY_SNAPSHOT", "PASS_PLATFORM_V1_SNAPSHOT_WITH_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

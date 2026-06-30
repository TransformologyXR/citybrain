from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_flowx_review_flow_acceptance_d1 import run_flowx_review_flow_acceptance_d1


def main() -> int:
    result = run_flowx_review_flow_acceptance_d1(ROOT)
    print(result["final_print"])
    print(
        json.dumps(
            {
                "addendum_output_dir": result["addendum_output_dir"],
                "output_dir": result["output_dir"],
                "outputs": result["outputs"],
                "status": result["status"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "PASS_REVIEW_FLOW_ACCEPTANCE_POLICY_WITH_LIMITATIONS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

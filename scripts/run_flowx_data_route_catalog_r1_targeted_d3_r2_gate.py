from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_flowx_data_route_catalog_r1_targeted_d3_r2 import run_flowx_data_route_catalog_r1_targeted_d3_r2


def main() -> int:
    result = run_flowx_data_route_catalog_r1_targeted_d3_r2(ROOT)
    print(result["final_print"])
    print(json.dumps({"output_dir": result["output_dir"], "outputs": result["outputs"], "status": result["status"]}, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS_TARGETED_D3_R2_AND_DATA_ROUTE_CATALOG_R1" else 1


if __name__ == "__main__":
    raise SystemExit(main())

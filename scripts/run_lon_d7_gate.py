from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_lon_d7_graph_query_smoke import (
    DEFAULT_LON_D4_DIR,
    DEFAULT_LON_D5C_DIR,
    DEFAULT_LON_D5_DIR,
    DEFAULT_LON_D6_DIR,
    DEFAULT_OUTPUT_DIR,
    run_lon_d7_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LON-D7 London graph/query smoke gate")
    parser.add_argument("--lon-d4-dir", default=DEFAULT_LON_D4_DIR)
    parser.add_argument("--lon-d5-dir", default=DEFAULT_LON_D5_DIR)
    parser.add_argument("--lon-d5c-dir", default=DEFAULT_LON_D5C_DIR)
    parser.add_argument("--lon-d6-dir", default=DEFAULT_LON_D6_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-query-examples", type=int, default=25)
    args = parser.parse_args()
    report = run_lon_d7_gate(
        args.lon_d4_dir,
        args.lon_d5_dir,
        args.lon_d5c_dir,
        args.lon_d6_dir,
        args.output_dir,
        args.max_query_examples,
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "output_dir": args.output_dir,
                "nodes_emitted": report["counts"]["nodes_emitted"],
                "edges_emitted": report["counts"]["edges_emitted"],
                "connected_pld_to_uprn_toid_paths": report["counts"]["connected_pld_to_uprn_toid_paths"],
                "connected_pld_to_uprn_usrn_paths": report["counts"]["connected_pld_to_uprn_usrn_paths"],
                "query_smoke": report["query_smoke"]["status"],
                "briefing_smoke": report["briefing_smoke"]["status"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_f3_nyc_d2c_capped_working_set_refresh import run_f3_nyc_d2c_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run F3-NYC-D2C capped working-set refresh gate")
    parser.add_argument("--output-dir", default="outputs/f3_nyc_d2c_capped_working_set_refresh")
    parser.add_argument("--source-pack", default="data_landing/f3_nyc_d1_official_sources_v1")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    report = run_f3_nyc_d2c_gate(args.output_dir, args.source_pack)
    return 0 if report["status"] in {"PASS", "PASS_WITH_CAPPED_WORKING_SET"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

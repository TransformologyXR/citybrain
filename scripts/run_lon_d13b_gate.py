from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from txr_citybrain_lon_d13b_composite_d6b3_refresh import run_lon_d13b_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LON-D13b gate")
    parser.add_argument("--d13-dir", default="outputs/lon_d13_london_composite_accepted_snapshot")
    parser.add_argument("--d12b-dir", default="outputs/lon_d12b_live_spark_nim_replay")
    parser.add_argument("--d6b3-dir", default="outputs/lon_d6b3_havering_enforcement_identity_recovery")
    parser.add_argument("--d6b2-dir", default="outputs/lon_d6b2_havering_enforcement_graph_integration")
    parser.add_argument("--d10b-dir", default="outputs/lon_d10b_local_plan_semantic_certification")
    parser.add_argument("--d10z-dir", default="outputs/lon_d10z_d10_accepted_snapshot")
    parser.add_argument("--d9z-dir", default="outputs/lon_d9z_d9d2_accepted_snapshot")
    parser.add_argument("--mission-control", default="TXRCityBrain_MissionControl.html")
    parser.add_argument("--todo", default="TXRCityBrain_ToDo.html")
    parser.add_argument("--output-dir", default="outputs/lon_d13b_london_composite_d6b3_refresh")
    parser.add_argument("--sync-4070", action="store_true")
    args = parser.parse_args()
    report = run_lon_d13b_gate(args.d13_dir, args.d12b_dir, args.d6b3_dir, args.d6b2_dir, args.d10b_dir, args.d10z_dir, args.d9z_dir, args.mission_control, args.todo, args.output_dir, args.sync_4070)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

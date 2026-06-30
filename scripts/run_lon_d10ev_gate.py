from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from txr_citybrain_lon_d10ev_ev_charging_source_recovery import run_lon_d10ev_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LON-D10EV gate")
    parser.add_argument("--d10z-dir", default="outputs/lon_d10z_d10_accepted_snapshot")
    parser.add_argument("--d10b-dir", default="outputs/lon_d10b_local_plan_semantic_certification")
    parser.add_argument("--d13b-dir", default="outputs/lon_d13b_london_composite_d6b3_refresh")
    parser.add_argument("--d11a-dir", default="outputs/lon_d11a_toid_generalised_location_recovery")
    parser.add_argument("--output-dir", default="outputs/lon_d10ev_ev_charging_source_recovery")
    parser.add_argument("--raw-root", action="append", dest="raw_roots", default=None)
    parser.add_argument("--allow-official-download", action="store_true")
    parser.add_argument("--publish-4070", action="store_true")
    args = parser.parse_args()
    report = run_lon_d10ev_gate(args.d10z_dir, args.d10b_dir, args.d13b_dir, args.d11a_dir, args.output_dir, args.raw_roots, args.allow_official_download, args.publish_4070)
    return 0 if report["status"] in {"PASS", "PASS_WITH_SCOPE_LIMITATION", "PASS_WITH_SOURCE_LIMITATION_CONFIRMED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

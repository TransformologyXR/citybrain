from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from txr_citybrain_lon_d11a_toid_generalised_location_recovery import run_lon_d11a_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LON-D11A gate")
    parser.add_argument("--d9z-dir", default="outputs/lon_d9z_d9d2_accepted_snapshot")
    parser.add_argument("--d10z-dir", default="outputs/lon_d10z_d10_accepted_snapshot")
    parser.add_argument("--d13b-dir", default="outputs/lon_d13b_london_composite_d6b3_refresh")
    parser.add_argument("--os-open-toid-zip", default=None)
    parser.add_argument("--output-dir", default="outputs/lon_d11a_toid_generalised_location_recovery")
    parser.add_argument("--publish-4070", action="store_true")
    args = parser.parse_args()
    report = run_lon_d11a_gate(args.d9z_dir, args.d10z_dir, args.d13b_dir, args.os_open_toid_zip, args.output_dir, args.publish_4070)
    return 0 if report["status"] == "PASS_WITH_GENERALISED_TOID_LOCATION_LIMITATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())

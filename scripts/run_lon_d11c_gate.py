from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from txr_citybrain_lon_d11c_live_london_face_route_fix import run_lon_d11c_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LON-D11C gate")
    parser.add_argument("--d11-dir", default="outputs/lon_d11_london_face_layer")
    parser.add_argument("--d11b-dir", default="outputs/lon_d11b_live_face_smoke")
    parser.add_argument("--d13b-dir", default="outputs/lon_d13b_london_composite_d6b3_refresh")
    parser.add_argument("--face-app-root", default=".")
    parser.add_argument("--published-root", default="C:/data/citybrain/from_3090")
    parser.add_argument("--output-dir", default="outputs/lon_d11c_live_london_face_route_fix")
    parser.add_argument("--base-url", default="http://192.168.1.48:8080")
    parser.add_argument("--apply-route-fix", action="store_true")
    args = parser.parse_args()
    report = run_lon_d11c_gate(args.d11_dir, args.d11b_dir, args.d13b_dir, args.face_app_root, args.published_root, args.output_dir, args.base_url, args.apply_route_fix)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

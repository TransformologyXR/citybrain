from __future__ import annotations

import argparse

from txr_citybrain_f3_nyc_d8_flow3_hero_package import (
    DEFAULT_BASE_URL,
    DEFAULT_D2_DIR,
    DEFAULT_D2C_DIR,
    DEFAULT_D3_DIR,
    DEFAULT_D4_DIR,
    DEFAULT_D5_DIR,
    DEFAULT_D6_DIR,
    DEFAULT_D7_DIR,
    DEFAULT_OUTPUT_DIR,
    run_f3_nyc_d8_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run F3-NYC-D8 Flow 3 hero package gate")
    parser.add_argument("--d7-dir", default=DEFAULT_D7_DIR)
    parser.add_argument("--d6-dir", default=DEFAULT_D6_DIR)
    parser.add_argument("--d5-dir", default=DEFAULT_D5_DIR)
    parser.add_argument("--d4-dir", default=DEFAULT_D4_DIR)
    parser.add_argument("--d3-dir", default=DEFAULT_D3_DIR)
    parser.add_argument("--d2c-dir", default=DEFAULT_D2C_DIR)
    parser.add_argument("--d2-dir", default=DEFAULT_D2_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--publish-4070", action="store_true")
    args = parser.parse_args()
    report = run_f3_nyc_d8_gate(
        d7_dir=args.d7_dir,
        d6_dir=args.d6_dir,
        d5_dir=args.d5_dir,
        d4_dir=args.d4_dir,
        d3_dir=args.d3_dir,
        d2c_dir=args.d2c_dir,
        d2_dir=args.d2_dir,
        output_dir=args.output_dir,
        base_url=args.base_url,
        publish_4070=args.publish_4070,
    )
    print(f"F3-NYC-D8: {report['status']}")
    print(f"Output: {args.output_dir}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

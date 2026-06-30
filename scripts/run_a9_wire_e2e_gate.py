from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from a9_wire_e2e import (  # noqa: E402
    DEFAULT_F3_D10FULL_DIR,
    DEFAULT_LONDON_D13C_DIR,
    DEFAULT_LONDON_HERO_DIR,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_RECONCILIATION_DIR,
    run_a9_wire_e2e_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the A9-WIRE-E2E G1 snapshot gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--reconciliation-dir", default=DEFAULT_RECONCILIATION_DIR)
    parser.add_argument("--f3-d10full-dir", default=DEFAULT_F3_D10FULL_DIR)
    parser.add_argument("--london-d13c-dir", default=DEFAULT_LONDON_D13C_DIR)
    parser.add_argument("--london-hero-dir", default=DEFAULT_LONDON_HERO_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--run-live-smoke", action="store_true")
    args = parser.parse_args()
    report = run_a9_wire_e2e_gate(
        project_root=args.project_root,
        reconciliation_dir=args.reconciliation_dir,
        f3_d10full_dir=args.f3_d10full_dir,
        london_d13c_dir=args.london_d13c_dir,
        london_hero_dir=args.london_hero_dir,
        output_dir=args.output_dir,
        run_live_smoke=args.run_live_smoke,
    )
    return 0 if str(report.get("status", "")).startswith("G1_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())

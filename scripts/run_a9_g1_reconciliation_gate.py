from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_a9_g1_board_reconciliation import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    run_a9_g1_reconciliation_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the A9/G1 board reconciliation gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = run_a9_g1_reconciliation_gate(project_root=args.project_root, output_dir=args.output_dir)
    return 0 if str(report.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())

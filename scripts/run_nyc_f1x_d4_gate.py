from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_nyc_f1x_d4_situational_status_replay_face_proof import (
    DEFAULT_OUTPUT_DIR,
    PASS_STATUSES,
    print_final_report,
    run_nyc_f1x_d4,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run NYC-F1X-D4 replay + face payload proof gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = run_nyc_f1x_d4(args.project_root, args.output_dir)
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())

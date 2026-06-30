from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_flowx_face_publish_smoke_d1 import (
    DEFAULT_OUTPUT_DIR,
    PASS_STATUSES,
    print_final_report,
    run_flowx_face_publish_smoke,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run FLOWX face publish/smoke gate")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = run_flowx_face_publish_smoke(args.project_root, args.output_dir)
    print_final_report(report)
    return 0 if report["status"] in PASS_STATUSES else 1


if __name__ == "__main__":
    raise SystemExit(main())

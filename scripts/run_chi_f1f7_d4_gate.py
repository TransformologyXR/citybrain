from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_chi_f1f7_d4_hero_package import (
    DEFAULT_BASE_URL,
    DEFAULT_D1B_DIR,
    DEFAULT_D2B_DIR,
    DEFAULT_D3B_DIR,
    DEFAULT_D3B_FACE_DIR,
    DEFAULT_D4B_DIR,
    DEFAULT_DUALB_DIR,
    DEFAULT_F1B_DIR,
    DEFAULT_F7B_DIR,
    DEFAULT_OUTPUT_DIR,
    run_chi_f1f7_d4_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CHI-F1F7-D4 Chicago hero package gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--d1b-dir", default=DEFAULT_D1B_DIR)
    parser.add_argument("--d3b-dir", default=DEFAULT_D3B_DIR)
    parser.add_argument("--d4b-dir", default=DEFAULT_D4B_DIR)
    parser.add_argument("--f1b-dir", default=DEFAULT_F1B_DIR)
    parser.add_argument("--f7b-dir", default=DEFAULT_F7B_DIR)
    parser.add_argument("--dualb-dir", default=DEFAULT_DUALB_DIR)
    parser.add_argument("--d2b-dir", default=DEFAULT_D2B_DIR)
    parser.add_argument("--d3b-face-dir", default=DEFAULT_D3B_FACE_DIR)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--publish-4070", dest="publish_4070", action="store_true", default=False)
    parser.add_argument("--no-publish-4070", dest="publish_4070", action="store_false")
    args = parser.parse_args()

    result = run_chi_f1f7_d4_gate(
        project_root=args.project_root,
        d1b_dir=args.d1b_dir,
        d3b_dir=args.d3b_dir,
        d4b_dir=args.d4b_dir,
        f1b_dir=args.f1b_dir,
        f7b_dir=args.f7b_dir,
        dualb_dir=args.dualb_dir,
        d2b_dir=args.d2b_dir,
        d3b_face_dir=args.d3b_face_dir,
        output_dir=args.output_dir,
        base_url=args.base_url,
        publish_4070=args.publish_4070,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

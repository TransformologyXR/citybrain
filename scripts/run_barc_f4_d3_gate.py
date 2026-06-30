from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_barc_f4_d3_mobility_transport_environment_evidencebundles import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    final_print,
    run_barc_f4_d3_gate,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run BARC-F4-D3 EvidenceBundle gate.")
    parser.add_argument("--project-root", default=str(ROOT), help="Project root containing outputs and contracts.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory for BARC-F4-D3 artifacts.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_barc_f4_d3_gate(args.project_root, args.output_dir)
    print(final_print(result))


if __name__ == "__main__":
    main()

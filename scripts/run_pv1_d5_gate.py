from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_pv1_d5_event_fabric_contract import DEFAULT_D5_OUTPUT, DEFAULT_ONTOLOGY_DIR, DEFAULT_SDF_PACK, run_pv1_d5_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-D5 event fabric contract gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--ontology-dir", default=DEFAULT_ONTOLOGY_DIR)
    parser.add_argument("--sdf-pack", default=DEFAULT_SDF_PACK)
    parser.add_argument("--d5-output", "--output-dir", dest="output_dir", default=DEFAULT_D5_OUTPUT)
    args = parser.parse_args()
    result = run_pv1_d5_gate(project_root=args.project_root, ontology_dir=args.ontology_dir, sdf_pack=args.sdf_pack, output_dir=args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

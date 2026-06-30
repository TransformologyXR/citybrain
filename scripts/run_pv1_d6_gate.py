from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_pv1_d5_event_fabric_contract import DEFAULT_ONTOLOGY_DIR, DEFAULT_SDF_PACK
from txr_citybrain_pv1_d6_replay_runner import DEFAULT_D6_OUTPUT, run_pv1_d6_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-D6 replay runner gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--ontology-dir", default=DEFAULT_ONTOLOGY_DIR)
    parser.add_argument("--sdf-pack", default=DEFAULT_SDF_PACK)
    parser.add_argument("--d6-output", "--output-dir", dest="output_dir", default=DEFAULT_D6_OUTPUT)
    args = parser.parse_args()
    result = run_pv1_d6_gate(project_root=args.project_root, ontology_dir=args.ontology_dir, sdf_pack=args.sdf_pack, output_dir=args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

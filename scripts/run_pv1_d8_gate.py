from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_pv1_d8_incident_mode_v1 import (
    DEFAULT_CURRENT_STATE_OUTPUT,
    DEFAULT_D8_OUTPUT,
    DEFAULT_EVENT_FABRIC_OUTPUT,
    DEFAULT_ONTOLOGY_DIR,
    DEFAULT_SDF_PACK,
    run_pv1_d8_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-D8 Incident Mode v1 gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--ontology-dir", default=DEFAULT_ONTOLOGY_DIR)
    parser.add_argument("--event-fabric-output", default=DEFAULT_EVENT_FABRIC_OUTPUT)
    parser.add_argument("--current-state-output", default=DEFAULT_CURRENT_STATE_OUTPUT)
    parser.add_argument("--sdf-pack", default=DEFAULT_SDF_PACK)
    parser.add_argument("--d8-output", "--output-dir", dest="output_dir", default=DEFAULT_D8_OUTPUT)
    parser.add_argument("--nim-endpoint", default=None)
    parser.add_argument("--nim-model", default=None)
    parser.add_argument("--run-live-nim-smoke", action="store_true")
    args = parser.parse_args()
    result = run_pv1_d8_gate(
        project_root=args.project_root,
        ontology_dir=args.ontology_dir,
        event_fabric_output=args.event_fabric_output,
        current_state_output=args.current_state_output,
        sdf_pack=args.sdf_pack,
        output_dir=args.output_dir,
        nim_endpoint=args.nim_endpoint,
        nim_model=args.nim_model,
        run_live_nim_smoke=args.run_live_nim_smoke,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

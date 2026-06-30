from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_pv1_d8_incident_mode_v1 import DEFAULT_CURRENT_STATE_OUTPUT, DEFAULT_D8_OUTPUT, DEFAULT_EVENT_FABRIC_OUTPUT, DEFAULT_ONTOLOGY_DIR, DEFAULT_SDF_PACK
from txr_citybrain_pv1_d8d9_run_all import DEFAULT_UMBRELLA_OUTPUT, run_pv1_d8d9_gate
from txr_citybrain_pv1_d9_plan_mode_v1 import DEFAULT_D9_OUTPUT


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-D8/D9 multimode cognition gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--ontology-dir", default=DEFAULT_ONTOLOGY_DIR)
    parser.add_argument("--event-fabric-output", default=DEFAULT_EVENT_FABRIC_OUTPUT)
    parser.add_argument("--current-state-output", default=DEFAULT_CURRENT_STATE_OUTPUT)
    parser.add_argument("--sdf-pack", default=DEFAULT_SDF_PACK)
    parser.add_argument("--d8-output", default=DEFAULT_D8_OUTPUT)
    parser.add_argument("--d9-output", default=DEFAULT_D9_OUTPUT)
    parser.add_argument("--umbrella-output", default=DEFAULT_UMBRELLA_OUTPUT)
    parser.add_argument("--nim-endpoint", default=None)
    parser.add_argument("--nim-model", default=None)
    parser.add_argument("--run-live-nim-smoke", action="store_true")
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    result = run_pv1_d8d9_gate(
        project_root=args.project_root,
        ontology_dir=args.ontology_dir,
        event_fabric_output=args.event_fabric_output,
        current_state_output=args.current_state_output,
        sdf_pack=args.sdf_pack,
        d8_output=args.d8_output,
        d9_output=args.d9_output,
        umbrella_output=args.umbrella_output,
        nim_endpoint=args.nim_endpoint,
        nim_model=args.nim_model,
        run_live_nim_smoke=args.run_live_nim_smoke,
        run_gates=args.run_gates,
    )
    print(result["final_print"])
    print(json.dumps({"status": result["status"], "umbrella_output": result["umbrella_output"]}, indent=2, sort_keys=True))
    return 0 if result.get("status") in {"PASS_REVIEW_ONLY_INCIDENT_AND_PLAN_MODES", "PASS_WITH_OPTIONAL_NIM_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

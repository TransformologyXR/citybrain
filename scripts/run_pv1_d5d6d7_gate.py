from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_pv1_d5_event_fabric_contract import DEFAULT_D5_OUTPUT, DEFAULT_ONTOLOGY_DIR, DEFAULT_SDF_PACK
from txr_citybrain_pv1_d5d6d7_run_all import DEFAULT_UMBRELLA_OUTPUT, run_pv1_d5d6d7_gate
from txr_citybrain_pv1_d6_replay_runner import DEFAULT_D6_OUTPUT
from txr_citybrain_pv1_d7_current_state_materializer import DEFAULT_D7_OUTPUT


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-D5/D6/D7 file-backed event fabric gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--ontology-dir", default=DEFAULT_ONTOLOGY_DIR)
    parser.add_argument("--sdf-pack", default=DEFAULT_SDF_PACK)
    parser.add_argument("--d5-output", default=DEFAULT_D5_OUTPUT)
    parser.add_argument("--d6-output", default=DEFAULT_D6_OUTPUT)
    parser.add_argument("--d7-output", default=DEFAULT_D7_OUTPUT)
    parser.add_argument("--umbrella-output", default=DEFAULT_UMBRELLA_OUTPUT)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()
    result = run_pv1_d5d6d7_gate(
        project_root=args.project_root,
        ontology_dir=args.ontology_dir,
        sdf_pack=args.sdf_pack,
        d5_output=args.d5_output,
        d6_output=args.d6_output,
        d7_output=args.d7_output,
        umbrella_output=args.umbrella_output,
        run_gates=args.run_gates,
    )
    print(result["final_print"])
    print(json.dumps({"status": result["status"], "umbrella_output": result["umbrella_output"]}, indent=2, sort_keys=True))
    return 0 if result.get("status") in {"PASS_FILE_BACKED_EVENT_FABRIC", "PASS_WITH_REPLAY_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_a5d6_live_nemo_nim_replay import DEFAULT_D5_DIR
from txr_citybrain_a5d6_live_nemo_nim_replay import DEFAULT_NAT_VENV
from txr_citybrain_a5d6_live_nemo_nim_replay import DEFAULT_NIM_ENDPOINT
from txr_citybrain_a5d6_live_nemo_nim_replay import DEFAULT_NIM_MODEL
from txr_citybrain_a5d6_live_nemo_nim_replay import DEFAULT_OUTPUT_DIR
from txr_citybrain_a5d6_live_nemo_nim_replay import DEFAULT_REMOTE_DIR
from txr_citybrain_a5d6_live_nemo_nim_replay import DEFAULT_REMOTE_HOST
from txr_citybrain_a5d6_live_nemo_nim_replay import print_report
from txr_citybrain_a5d6_live_nemo_nim_replay import run_a5d6_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run A5-D6 live NeMo/NIM replay gates.")
    parser.add_argument("--input-dir", default=str(DEFAULT_D5_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--remote-host", default=DEFAULT_REMOTE_HOST)
    parser.add_argument("--remote-dir", default=DEFAULT_REMOTE_DIR)
    parser.add_argument("--nat-venv", default=DEFAULT_NAT_VENV)
    parser.add_argument("--nim-endpoint", default=DEFAULT_NIM_ENDPOINT)
    parser.add_argument("--nim-model", default=DEFAULT_NIM_MODEL)
    args = parser.parse_args()
    report = run_a5d6_gate(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        remote_host=args.remote_host,
        remote_dir=args.remote_dir,
        nat_venv=args.nat_venv,
        nim_endpoint=args.nim_endpoint,
        nim_model=args.nim_model,
    )
    print_report(report)
    return int(report.get("exit_code", 1))


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_a5d4b_request_trace_core import print_final_report, run_a5d4b_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run A5-D4B request trace gate.")
    parser.add_argument("--input-dir", default=str(ROOT / "outputs" / "a5d4a_evidence_grounding_core"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "a5d4b_request_trace_core"))
    parser.add_argument("--use-nim", action="store_true")
    parser.add_argument("--nim-endpoint", default=None)
    parser.add_argument("--nim-model", default=None)
    args = parser.parse_args()
    report = run_a5d4b_gate(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        use_nim=args.use_nim,
        nim_endpoint=args.nim_endpoint,
        nim_model=args.nim_model,
    )
    print_final_report(report, args.output_dir)
    return int(report.get("exit_code", 1))


if __name__ == "__main__":
    raise SystemExit(main())

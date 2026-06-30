from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_chi_f1f7_d2_live_spark_nim_replay import run_chi_f1f7_d2_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CHI-F1F7-D2 live Spark/NIM replay gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--f1-d1-dir", default="outputs/chi_f1_d1_situational_status_cartridge")
    parser.add_argument("--f7-d1-dir", default="outputs/chi_f7_d1_civic_sensor_fusion_cartridge")
    parser.add_argument("--dual-d1-dir", default="outputs/chi_f1_f7_d1_dual_flow_run")
    parser.add_argument("--output-dir", default="outputs/chi_f1f7_d2_live_spark_nim_replay")
    parser.add_argument("--nim-endpoint", default="http://192.168.1.103:8000/v1")
    parser.add_argument("--nim-model", default="meta/llama-3.1-8b-instruct")
    parser.add_argument("--run-live-nim", dest="run_live_nim", action="store_true", default=True)
    parser.add_argument("--skip-live-nim", dest="run_live_nim", action="store_false")
    args = parser.parse_args()

    result = run_chi_f1f7_d2_gate(
        project_root=args.project_root,
        f1_d1_dir=args.f1_d1_dir,
        f7_d1_dir=args.f7_d1_dir,
        dual_d1_dir=args.dual_d1_dir,
        output_dir=args.output_dir,
        nim_endpoint=args.nim_endpoint,
        nim_model=args.nim_model,
        run_live_nim=args.run_live_nim,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if str(result.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())

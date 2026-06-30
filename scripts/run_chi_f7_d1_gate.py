from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_chi_f7_d1_civic_sensor_fusion import run_chi_f7_d1_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CHI-F7-D1 civic/sensor fusion cartridge gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--chi-d2b-dir", default="outputs/chi_d2b_base_identity_refresh")
    parser.add_argument("--chi-d3-dir", default="outputs/chi_d3_civic_event_ingest_flow_readiness")
    parser.add_argument("--chi-d4-dir", default="outputs/chi_d4_dual_flow_scope_fork")
    parser.add_argument("--f1-d1-dir", default="outputs/chi_f1_d1_situational_status_cartridge")
    parser.add_argument("--output-dir", default="outputs/chi_f7_d1_civic_sensor_fusion_cartridge")
    args = parser.parse_args()

    result = run_chi_f7_d1_gate(
        project_root=args.project_root,
        chi_d2b_dir=args.chi_d2b_dir,
        chi_d3_dir=args.chi_d3_dir,
        chi_d4_dir=args.chi_d4_dir,
        f1_d1_dir=args.f1_d1_dir,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if str(result.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())

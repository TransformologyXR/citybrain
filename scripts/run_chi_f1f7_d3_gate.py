from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_chi_f1f7_d3_face_layer_status_fusion import run_chi_f1f7_d3_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CHI-F1F7-D3 Chicago face-layer status/fusion gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--f1-d1-dir", default="outputs/chi_f1_d1_situational_status_cartridge")
    parser.add_argument("--f7-d1-dir", default="outputs/chi_f7_d1_civic_sensor_fusion_cartridge")
    parser.add_argument("--f1f7-d2-dir", default="outputs/chi_f1f7_d2_live_spark_nim_replay")
    parser.add_argument("--chi-d2b-dir", default="outputs/chi_d2b_base_identity_refresh")
    parser.add_argument("--chi-d1b-dir", default="outputs/chi_d1b_chicago_extended_source_landing")
    parser.add_argument("--output-dir", default="outputs/chi_f1f7_d3_face_layer_status_fusion_surface")
    parser.add_argument("--publish-4070", dest="publish_4070", action="store_true", default=True)
    parser.add_argument("--no-publish-4070", dest="publish_4070", action="store_false")
    args = parser.parse_args()

    result = run_chi_f1f7_d3_gate(
        project_root=args.project_root,
        f1_d1_dir=args.f1_d1_dir,
        f7_d1_dir=args.f7_d1_dir,
        f1f7_d2_dir=args.f1f7_d2_dir,
        chi_d2b_dir=args.chi_d2b_dir,
        chi_d1b_dir=args.chi_d1b_dir,
        output_dir=args.output_dir,
        publish_4070=args.publish_4070,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if str(result.get("status", "")).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())

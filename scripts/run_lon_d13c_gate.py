from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from txr_citybrain_lon_d13c_final_prehero_closure import run_lon_d13c_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LON-D13C gate")
    parser.add_argument("--d9z-dir", default="outputs/lon_d9z_d9d2_accepted_snapshot")
    parser.add_argument("--d10z-dir", default="outputs/lon_d10z_d10_accepted_snapshot")
    parser.add_argument("--d10b-dir", default="outputs/lon_d10b_local_plan_semantic_certification")
    parser.add_argument("--d11-dir", default="outputs/lon_d11_london_face_layer")
    parser.add_argument("--d11c-dir", default="outputs/lon_d11c_live_london_face_route_fix")
    parser.add_argument("--d12-dir", default="outputs/lon_d12_london_nemo_nim_wrapper")
    parser.add_argument("--d12b-dir", default="outputs/lon_d12b_live_spark_nim_replay")
    parser.add_argument("--d11a-dir", default="outputs/lon_d11a_toid_generalised_location_recovery")
    parser.add_argument("--d10ev-dir", default="outputs/lon_d10ev_ev_charging_source_recovery")
    parser.add_argument("--d6b2-dir", default="outputs/lon_d6b2_havering_enforcement_graph_integration")
    parser.add_argument("--d6b3-dir", default="outputs/lon_d6b3_havering_enforcement_identity_recovery")
    parser.add_argument("--d6b4-dir", default="outputs/lon_d6b4_havering_enforcement_identity_expansion")
    parser.add_argument("--d13b-dir", default="outputs/lon_d13b_london_composite_d6b3_refresh")
    parser.add_argument("--chain-report-dir", default="outputs/lon_post_d13b_enrichment_chain_report")
    parser.add_argument("--mission-control", default="TXRCityBrain_MissionControl.html")
    parser.add_argument("--todo", default="TXRCityBrain_ToDo.html")
    parser.add_argument("--output-dir", default="outputs/lon_d13c_london_final_prehero_closure")
    parser.add_argument("--live-face-base-url", default="http://192.168.1.48:8080")
    parser.add_argument("--live-nim-endpoint", default="http://192.168.1.103:8000/v1")
    parser.add_argument("--live-nim-model", default="meta/llama-3.1-8b-instruct")
    parser.add_argument("--sync-4070", action="store_true")
    args = parser.parse_args()
    report = run_lon_d13c_gate(
        args.d9z_dir,
        args.d10z_dir,
        args.d10b_dir,
        args.d11_dir,
        args.d11c_dir,
        args.d12_dir,
        args.d12b_dir,
        args.d11a_dir,
        args.d10ev_dir,
        args.d6b2_dir,
        args.d6b3_dir,
        args.d6b4_dir,
        args.d13b_dir,
        args.chain_report_dir,
        args.mission_control,
        args.todo,
        args.output_dir,
        args.live_face_base_url,
        args.live_nim_endpoint,
        args.live_nim_model,
        args.sync_4070,
    )
    return 0 if report["status"] in {"PASS", "PASS_WITH_LIVE_NIM_RESMOKE_NOT_RUN_BUT_D12B_ACCEPTED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

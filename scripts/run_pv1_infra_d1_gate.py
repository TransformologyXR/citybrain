from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from txr_citybrain_pv1_infra_d1_runtime_install_audit import DEFAULT_OUTPUT_DIR
from txr_citybrain_pv1_infra_d1_runtime_install_audit import run_pv1_infra_d1_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PV1-INFRA-D1 runtime placement and install audit gate.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--spark-host", default="192.168.1.103")
    parser.add_argument("--box3090-host", default="192.168.1.148")
    parser.add_argument("--box4070-host", default="192.168.1.48")
    parser.add_argument("--run-ssh-probes", action="store_true")
    parser.add_argument("--run-live-endpoint-probes", action="store_true")
    parser.add_argument("--audit-only", action="store_true", default=True)
    parser.add_argument("--run-gates", action="store_true")
    args = parser.parse_args()

    result = run_pv1_infra_d1_gate(
        project_root=args.project_root,
        output_dir=args.output_dir,
        spark_host=args.spark_host,
        box3090_host=args.box3090_host,
        box4070_host=args.box4070_host,
        run_ssh_probes=args.run_ssh_probes,
        run_live_endpoint_probes=args.run_live_endpoint_probes,
        audit_only=args.audit_only,
    )
    print(result["final_print"])
    print(json.dumps({"status": result["status"], "output_dir": result["output_dir"]}, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PASS_RUNTIME_AUDIT", "PASS_WITH_INSTALL_GAPS", "PASS_WITH_SSH_LIMITATIONS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())

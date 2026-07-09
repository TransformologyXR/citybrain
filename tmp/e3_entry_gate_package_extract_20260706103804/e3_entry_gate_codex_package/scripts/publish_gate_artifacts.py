#!/usr/bin/env python3
"""Reference atomic publication checker for gate artifacts.

This script does not write a production ledger. It validates that all expected
artifact refs exist in a local package/output directory and emits a local
publication bundle JSON that Codex can adapt to the project ledger.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = {
    "report_ref": "docs/E3_FUEL_GAUGE_BASELINE_REPORT.md",
    "arming_manifest_ref": "manifests/epoch3_arming_manifest.json",
    "evaluator_ref": "manifests/epoch3_arming_evaluator_spec.yaml",
    "hash_manifest_ref": "hash_manifest.json",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--hash-manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    missing = []
    for key, rel in REQUIRED.items():
        path = args.hash_manifest if key == "hash_manifest_ref" else root / rel
        if not path.exists():
            missing.append(str(path))
    if missing:
        raise SystemExit("Missing required artifacts for atomic publication: " + ", ".join(missing))

    row = json.loads((root / "manifests/gate_ledger_row.template.json").read_text(encoding="utf-8"))
    row["created_at"] = datetime.now(timezone.utc).isoformat()
    row["created_by"] = "publish_gate_artifacts.py"
    row["hash_manifest_ref"] = str(args.hash_manifest)
    args.out.write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

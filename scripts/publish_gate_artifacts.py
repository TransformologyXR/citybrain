#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_KEYS = ("report_ref", "arming_manifest_ref", "evaluator_ref", "hash_manifest_ref")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and publish a local E3 gate ledger row")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--template", default=Path("manifests/gate_ledger_row.template.json"), type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--arming-manifest", required=True, type=Path)
    parser.add_argument("--evaluator", required=True, type=Path)
    parser.add_argument("--hash-manifest", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    paths = {
        "report_ref": args.report,
        "arming_manifest_ref": args.arming_manifest,
        "evaluator_ref": args.evaluator,
        "hash_manifest_ref": args.hash_manifest,
    }
    missing = [key for key, path in paths.items() if not path.exists()]
    if missing:
        raise SystemExit(f"Missing required atomic publication refs: {', '.join(missing)}")

    row = load_json(args.template)
    row["created_at"] = utc_now()
    row["created_by"] = "scripts/publish_gate_artifacts.py"
    for key in REQUIRED_KEYS:
        row[key] = paths[key].resolve().relative_to(args.root.resolve()).as_posix()
    row["atomic_publication"] = {
        "status": "PASS",
        "required_refs": list(REQUIRED_KEYS),
        "missing": [],
        "threshold_crossing_does_not_start_work": True,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(row, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

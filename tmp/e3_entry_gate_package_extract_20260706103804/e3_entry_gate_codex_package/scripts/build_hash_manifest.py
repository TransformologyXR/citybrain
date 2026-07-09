#!/usr/bin/env python3
"""Build a SHA-256 hash manifest for gate artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

DEFAULT_EXCLUDES = {".git", "__pycache__", ".pytest_cache"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_files(root: Path) -> List[Dict[str, str]]:
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in DEFAULT_EXCLUDES for part in rel.parts):
            continue
        rows.append({"path": str(rel), "sha256": sha256_file(path)})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--corpus-version", default="<corpus_version>")
    args = parser.parse_args()

    root = args.root.resolve()
    files = collect_files(root)
    by_path = {row["path"]: row["sha256"] for row in files}
    manifest = {
        "id": "hash_manifest",
        "gate_id": "MAIN-CITYBRAIN-EPOCH3-ENTRY-GATE-R1-FUEL-GAUGE",
        "corpus_version": args.corpus_version,
        "corpus_hash": "<external_corpus_hash>",
        "source_manifest_hash": by_path.get("manifests/source_manifest.json", "<external_source_manifest_hash>"),
        "synthetic_manifest_hash": by_path.get("manifests/synthetic_manifest.json", "<external_synthetic_manifest_hash>"),
        "scenario_manifest_hash": by_path.get("manifests/scenario_manifest.json", "<external_scenario_manifest_hash>"),
        "arming_manifest_hash": by_path.get("manifests/epoch3_arming_manifest.json", "<missing>"),
        "report_hash": by_path.get("docs/E3_FUEL_GAUGE_BASELINE_REPORT.md", "<report_not_finalized>"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    args.out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

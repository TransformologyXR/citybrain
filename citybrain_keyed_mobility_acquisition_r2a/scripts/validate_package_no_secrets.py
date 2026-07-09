#!/usr/bin/env python3
"""Scan a package/output root for credential leakage using env-provided secrets."""
from __future__ import annotations
import argparse, json, os
from pathlib import Path
SECRET_ENV_NAMES = ["LTA_DATAMALL_ACCOUNT_KEY", "LTA_EXTENDED_OBU_SDK_ACCOUNT_KEY", "TFL_PRIMARY_KEY", "TFL_SECONDARY_KEY"]
def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--root", required=True); args = ap.parse_args(); root = Path(args.root)
    secrets = [os.environ.get(name, "") for name in SECRET_ENV_NAMES]; secrets = [s for s in secrets if s and len(s) >= 8]
    hits = []
    for path in root.rglob("*"):
        if not path.is_file(): continue
        try: text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception: continue
        for idx, secret in enumerate(secrets):
            if secret in text: hits.append({"path": str(path), "secret_index": idx})
    report = {"root": str(root), "secret_values_tested": len(secrets), "hits": hits, "pass": not hits}
    print(json.dumps(report, indent=2))
    return 0 if not hits else 2
if __name__ == "__main__":
    raise SystemExit(main())

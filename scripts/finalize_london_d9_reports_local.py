from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path("outputs")
BACKEND = {
    "execution_backend": "pandas_cpu_in_rapids_container",
    "note": "D9B-D9F used pandas/geopandas/pyarrow CPU processing inside the RAPIDS container; no cuDF/cuGraph execution is claimed.",
}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def refresh_hashes(directory: Path):
    rows = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.json":
            rows.append({"path": str(path.relative_to(directory)), "bytes": path.stat().st_size, "sha256": sha(path)})
    write(directory / "SHA256SUMS.json", rows)


for rel in [
    "lon_d9b_london_identity_build/LON_D9B_HARNESS_REPORT.json",
    "lon_d9b_london_identity_build/LON_D9B_IDENTITY_BUILD_REPORT.json",
    "lon_d9b_london_identity_build/reports/execution_backend.json",
]:
    path = ROOT / rel
    if path.exists():
        doc = read(path)
        if path.name == "execution_backend.json":
            doc.update(BACKEND)
        else:
            doc["execution_backend"] = BACKEND["execution_backend"]
            doc.setdefault("backend", {}).update(BACKEND)
        write(path, doc)

master = ROOT / "lon_d9_overnight_master_report" / "LON_D9_OVERNIGHT_MASTER_REPORT.json"
if master.exists():
    doc = read(master)
    doc["what_synced_to_4070"] = (
        "Lightweight D9F export synced to txr-4070:/data/citybrain/from_3090/"
        "london_d9f_serious_london_v1/ and hash-verified locally there."
    )
    write(master, doc)

for rel in ["lon_d9b_london_identity_build", "lon_d9_overnight_master_report"]:
    directory = ROOT / rel
    if directory.exists():
        refresh_hashes(directory)

print("finalized")

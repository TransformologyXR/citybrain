from __future__ import annotations

import json
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "README.md",
    "CODEX_HANDOFF.md",
    "docs/BOUNDARY_POLICY.md",
    "manifests/INPUT_CONTRACT.json",
    "manifests/EXPECTED_OUTPUTS.json",
    "prompts/CODEX_TASK_PROMPT.md",
    "scripts/run_main_citybrain_synthetic_factory_seed_r2_d5_served_runtime_integration_r1.py",
    "PACKAGE_DECISION.json",
    "SECRET_SCAN_REPORT.json",
    "HASH_MANIFEST.json",
]


def _all_package_text() -> str:
    return "\n".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for p in PACKAGE_ROOT.rglob("*")
        if p.is_file() and "__pycache__" not in str(p) and ".pytest_cache" not in str(p)
    )


def test_required_files_present():
    missing = [name for name in REQUIRED_FILES if not (PACKAGE_ROOT / name).exists()]
    assert not missing


def test_json_files_parse():
    for rel in [
        "manifests/INPUT_CONTRACT.json",
        "manifests/EXPECTED_OUTPUTS.json",
        "PACKAGE_DECISION.json",
        "SECRET_SCAN_REPORT.json",
        "HASH_MANIFEST.json",
    ]:
        json.loads((PACKAGE_ROOT / rel).read_text(encoding="utf-8"))


def test_secret_scan_report_is_pass():
    report = json.loads((PACKAGE_ROOT / "SECRET_SCAN_REPORT.json").read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["passed"] is True
    assert report["findings"] == []


def test_boundary_policy_contains_forbidden_claims():
    text = (PACKAGE_ROOT / "docs/BOUNDARY_POLICY.md").read_text(encoding="utf-8")
    for phrase in ["dispatch", "control", "legal", "certified", "live monitoring"]:
        assert phrase in text


def test_hash_manifest_matches():
    manifest = json.loads((PACKAGE_ROOT / "HASH_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "PASS"
    assert len(manifest["entries"]) == manifest["file_count"]

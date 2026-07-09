from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_required_files_present():
    required = [
        "README.md",
        "CODEX_HANDOFF.md",
        "docs/BOUNDARY_POLICY.md",
        "manifests/INPUT_CONTRACT.json",
        "manifests/EXPECTED_OUTPUTS.json",
        "prompts/CODEX_TASK_PROMPT.md",
        "scripts/run_main_citybrain_synthetic_factory_seed_r3_loop_convergence_event_adapter_r1.py",
        "PACKAGE_DECISION.json",
        "SECRET_SCAN_REPORT.json",
        "HASH_MANIFEST.json",
    ]
    for rel in required:
        assert (ROOT / rel).exists(), rel


def test_json_manifests_parse():
    for rel in ["manifests/INPUT_CONTRACT.json", "manifests/EXPECTED_OUTPUTS.json", "PACKAGE_DECISION.json", "SECRET_SCAN_REPORT.json", "HASH_MANIFEST.json"]:
        with (ROOT / rel).open("r", encoding="utf-8") as f:
            json.load(f)


def test_loop_families_declared_exactly():
    manifest = json.loads((ROOT / "manifests/INPUT_CONTRACT.json").read_text(encoding="utf-8"))
    assert manifest["required_loop_families"] == [
        "mobility_access",
        "building_compliance",
        "permit_inspection_delay",
        "asset_infrastructure",
    ]


def test_runner_emits_event_fabric_adapter_not_fixture_only():
    text = (ROOT / "scripts/run_main_citybrain_synthetic_factory_seed_r3_loop_convergence_event_adapter_r1.py").read_text(encoding="utf-8")
    assert "EVENT_FABRIC_SOURCE_ADAPTER_FEED_R1.jsonl" in text
    assert "standalone_fixture_only" in text
    assert "direct_D5_response" in text


def test_no_obvious_secret_literals_or_raw_payloads():
    scanned_files = [p for p in ROOT.rglob("*") if p.is_file() and "__pycache__" not in str(p) and "/tests/" not in str(p).replace("\\", "/")]
    text = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in scanned_files)
    # Do not store real key values or raw provider payload blobs in this package.
    assert "<provider response body>" not in text.lower()
    assert "AccountKey:" not in text

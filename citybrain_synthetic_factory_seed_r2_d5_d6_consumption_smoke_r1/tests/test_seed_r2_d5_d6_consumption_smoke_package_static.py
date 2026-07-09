from pathlib import Path
import json
import os
import re

ROOT = Path(__file__).resolve().parents[1]


def test_required_files_present():
    required = [
        "README.md",
        "CODEX_HANDOFF.md",
        "docs/BOUNDARY_POLICY.md",
        "manifests/INPUT_CONTRACT.json",
        "manifests/EXPECTED_OUTPUTS.json",
        "prompts/CODEX_TASK_PROMPT.md",
        "scripts/run_main_citybrain_synthetic_factory_seed_r2_d5_d6_consumption_smoke_r1.py",
        "PACKAGE_DECISION.json",
        "SECRET_SCAN_REPORT.json",
        "HASH_MANIFEST.json",
    ]
    for rel in required:
        assert (ROOT / rel).exists(), rel


def test_json_manifests_parse():
    for rel in [
        "manifests/INPUT_CONTRACT.json",
        "manifests/EXPECTED_OUTPUTS.json",
        "PACKAGE_DECISION.json",
        "SECRET_SCAN_REPORT.json",
        "HASH_MANIFEST.json",
    ]:
        json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_runner_has_expected_args_and_status():
    script = (ROOT / "scripts/run_main_citybrain_synthetic_factory_seed_r2_d5_d6_consumption_smoke_r1.py").read_text(encoding="utf-8")
    assert "--product-consumption" in script
    assert "--out" in script
    assert "PASS_SYNTHETIC_FACTORY_SEED_R2_D5_D6_CONSUMPTION_SMOKE_R1_WITH_LIMITATIONS" in script
    assert "INPUT_STATUS" in script


def test_boundaries_documented():
    text = (ROOT / "docs/BOUNDARY_POLICY.md").read_text(encoding="utf-8")
    for phrase in [
        "No raw provider payloads",
        "No credentials",
        "not official Dubai identity",
        "live monitoring",
        "dispatch",
        "certified",
    ]:
        assert phrase.lower() in text.lower()


def test_no_env_secret_literals_or_unredacted_app_key():
    joined = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in ROOT.rglob("*") if p.is_file())
    # Do not hardcode real secrets in this package. If the runner environment provides them, ensure they are absent.
    for env_name in [
        "LTA_DATAMALL_ACCOUNT_KEY",
        "LTA_EXTENDED_OBU_SDK_ACCOUNT_KEY",
        "TFL_PRIMARY_KEY",
        "TFL_SECONDARY_KEY",
    ]:
        value = os.environ.get(env_name, "")
        if value:
            assert value not in joined
    assert not re.search(r"app_key=(?!REDACTED|redacted)[A-Za-z0-9]{8,}", joined)

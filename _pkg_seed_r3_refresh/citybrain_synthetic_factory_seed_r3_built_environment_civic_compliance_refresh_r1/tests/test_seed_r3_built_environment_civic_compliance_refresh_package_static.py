import json
import pathlib
import re
import hashlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
TASK = "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R3-BUILT-ENVIRONMENT-CIVIC-COMPLIANCE-REFRESH-R1"

def package_files():
    excluded_parts = {"__pycache__", ".pytest_cache"}
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(part in excluded_parts for part in p.parts):
            continue
        if p.suffix.lower() in {".py", ".md", ".json", ".csv", ".txt"}:
            yield p

def package_text():
    return "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in package_files())

def test_required_package_files_present():
    expected = [
        "README.md",
        "CODEX_HANDOFF.md",
        "docs/BOUNDARY_POLICY.md",
        "manifests/INPUT_CONTRACT.json",
        "manifests/EXPECTED_OUTPUTS.json",
        "prompts/CODEX_TASK_PROMPT.md",
        "scripts/run_main_citybrain_synthetic_factory_seed_r3_built_environment_civic_compliance_refresh_r1.py",
        "PACKAGE_DECISION.json",
        "SECRET_SCAN_REPORT.json",
        "HASH_MANIFEST.json",
    ]
    for rel in expected:
        assert (ROOT / rel).exists(), rel

def test_json_manifests_parse():
    for rel in [
        "manifests/INPUT_CONTRACT.json",
        "manifests/EXPECTED_OUTPUTS.json",
        "PACKAGE_DECISION.json",
        "SECRET_SCAN_REPORT.json",
        "HASH_MANIFEST.json",
    ]:
        with (ROOT / rel).open("r", encoding="utf-8") as f:
            json.load(f)

def test_no_obvious_secret_or_unredacted_auth_patterns():
    text = package_text()
    auth_query_literal = "app" + "_key="
    assert not re.search(auth_query_literal + r"(?!REDACTED)", text, flags=re.I)
    assert not re.search(r"(api[_-]?key|account[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9+/=]{16,}", text, flags=re.I)
    lta_assignment_literal = "LTA_" + "DATAMALL_" + "ACCOUNT_" + "KEY" + "="
    tfl_assignment_literal = "TFL_" + "PRIMARY_" + "KEY" + "="
    assert lta_assignment_literal not in text
    assert tfl_assignment_literal not in text

def test_hash_manifest_matches_package_files():
    manifest = json.loads((ROOT / "HASH_MANIFEST.json").read_text(encoding="utf-8"))
    for item in manifest["files"]:
        path = ROOT / item["path"]
        assert path.exists(), item["path"]
        assert path.stat().st_size == item["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]

def test_package_decision_ready_and_no_secrets():
    decision = json.loads((ROOT / "PACKAGE_DECISION.json").read_text(encoding="utf-8"))
    secret = json.loads((ROOT / "SECRET_SCAN_REPORT.json").read_text(encoding="utf-8"))
    assert decision["task_id"] == TASK
    assert decision["status"].startswith("READY_FOR_CODEX")
    assert secret["status"] == "PASS"
    assert secret["contains_credentials"] is False

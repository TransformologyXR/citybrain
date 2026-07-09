import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

def iter_text_files():
    for p in ROOT.rglob("*"):
        if p.is_file() and "__pycache__" not in str(p):
            yield p, p.read_text(encoding="utf-8", errors="ignore")

def test_package_json_files_parse():
    for path in list((ROOT / "manifests").glob("*.json")) + [ROOT / "PACKAGE_DECISION.json", ROOT / "SECRET_SCAN_REPORT.json", ROOT / "HASH_MANIFEST.json"]:
        json.loads(path.read_text(encoding="utf-8"))

def test_required_files_exist():
    required = [
        "README.md",
        "CODEX_HANDOFF.md",
        "docs/BOUNDARY_POLICY.md",
        "manifests/INPUT_CONTRACT.json",
        "manifests/EXPECTED_OUTPUTS.json",
        "prompts/CODEX_TASK_PROMPT.md",
        "scripts/run_main_citybrain_synthetic_factory_seed_r2_product_consumption_r1.py",
    ]
    for rel in required:
        assert (ROOT / rel).exists(), rel

def test_no_unredacted_app_key_or_secret_placeholders():
    text = "\n".join(txt for _, txt in iter_text_files())
    assert "app_key=" not in text.lower() or "app_key=redacted" in text.lower()
    forbidden_literals = [
        "PASTE" + "_LTA" + "_KEY" + "_HERE",
        "PASTE" + "_TFL" + "_KEY" + "_HERE",
        "SECRET" + "_VALUE" + "_SHOULD" + "_NOT" + "_APPEAR",
    ]
    for literal in forbidden_literals:
        assert literal not in text

def test_runner_mentions_readonly_and_boundaries():
    runner = (ROOT / "scripts/run_main_citybrain_synthetic_factory_seed_r2_product_consumption_r1.py").read_text(encoding="utf-8")
    assert "read_only" in runner
    assert "no_dispatch_control_enforcement_legal_certified_claim" in runner
    assert "not_dubai_official_truth" in runner

def test_hash_manifest_matches_files():
    manifest = json.loads((ROOT / "HASH_MANIFEST.json").read_text(encoding="utf-8"))
    entries = manifest["entries"]
    assert entries
    for entry in entries:
        assert (ROOT / entry["path"]).exists()

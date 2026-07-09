import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def iter_package_text_files():
    for p in ROOT.rglob('*'):
        s = str(p.relative_to(ROOT))
        if not p.is_file():
            continue
        if s.startswith('tests/') or s.startswith('.pytest_cache/') or '__pycache__' in s:
            continue
        yield p

def test_expected_files_exist():
    expected = [
        'README.md', 'CODEX_HANDOFF.md', 'docs/BOUNDARY_POLICY.md',
        'docs/WHY_MOBILITY_WAS_FIRST.md', 'manifests/EXPECTED_INPUTS.json',
        'manifests/DOMAIN_TARGETS.csv', 'manifests/EXPECTED_OUTPUTS.json',
        'prompts/CODEX_TASK_PROMPT.md',
        'scripts/run_main_citybrain_synthetic_factory_seed_r3_cross_city_domain_fuel_preflight.py',
        'PACKAGE_DECISION.json', 'SECRET_SCAN_REPORT.json', 'HASH_MANIFEST.json'
    ]
    for rel in expected:
        assert (ROOT / rel).exists(), rel

def test_json_parse():
    for rel in ['manifests/EXPECTED_INPUTS.json','manifests/EXPECTED_OUTPUTS.json','PACKAGE_DECISION.json','SECRET_SCAN_REPORT.json','HASH_MANIFEST.json']:
        json.loads((ROOT/rel).read_text())

def test_no_unredacted_key_patterns_in_package_files():
    text = ''
    for p in iter_package_text_files():
        text += p.read_text(errors='ignore')
    assert not re.search(r'app_key=(?!REDACTED)([^&\s]+)', text, re.I)
    assert not re.search(r'AccountKey\s*[:=]\s*[^\s,}]+', text, re.I)
    assert '<provided' not in text.lower()

def test_mentions_non_mobility_domains():
    text = (ROOT/'manifests/DOMAIN_TARGETS.csv').read_text()
    for term in ['building_compliance','property_planning','built_environment','civic_service_311_crm']:
        assert term in text

def test_boundary_policy_present():
    text = (ROOT/'docs/BOUNDARY_POLICY.md').read_text()
    assert 'No official Dubai truth' in text or 'official Dubai truth' in text
    assert 'human/person-level' in text

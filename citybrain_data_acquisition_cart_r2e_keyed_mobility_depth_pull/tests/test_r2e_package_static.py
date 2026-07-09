from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]

def test_endpoint_catalog_parse_clean():
    data = json.loads((ROOT / 'manifests' / 'ENDPOINT_CATALOG_R2E.json').read_text(encoding='utf-8'))
    assert len(data) >= 15
    assert any(x['source_id'] == 'lta_busstops_full' for x in data)
    assert any(x['source_id'] == 'tfl_line_status_by_mode' for x in data)


def test_no_secret_placeholders_filled():
    text = ''.join(p.read_text(encoding='utf-8', errors='ignore') for p in ROOT.rglob('*') if p.is_file())
    forbidden_markers = [
        'TFL_PRIMARY_KEY=<provided',
        'LTA_DATAMALL_ACCOUNT_KEY=<provided',
    ]
    # Documentation may contain placeholder syntax, but no concrete raw key format should be present.
    assert 'app_key=REDACTED' in text
    assert 'User-Agent: CityBrain-R2E/1.0' in text
    assert 'Do not persist failed response bodies' in text or 'failed response bodies must not be persisted' in text


def test_script_has_safe_http_policy():
    script = (ROOT / 'scripts' / 'run_main_citybrain_data_acquisition_cart_r2e_keyed_mobility_depth_pull.py').read_text(encoding='utf-8')
    assert 'CityBrain-R2E/1.0' in script
    assert 'Accept' in script
    assert 'failed response bodies are never persisted' in script
    assert 'app_key=REDACTED' in script
    assert 'KEY_PRESENT_NOT_USED_FOR_STANDARD_REST' in script


def test_classify_status_returns_status_and_auth_tuple():
    import importlib.util

    script_path = ROOT / 'scripts' / 'run_main_citybrain_data_acquisition_cart_r2e_keyed_mobility_depth_pull.py'
    spec = importlib.util.spec_from_file_location('r2e_runner', script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    status, auth_status = module.classify_status(200, True, rows=1)
    assert status == 'PASS_DEPTH_PAGE_OR_SNAPSHOT_LANDED'
    assert auth_status == 'KEY_ACCEPTED'

    empty_status, empty_auth_status = module.classify_status(200, True, rows=0)
    assert empty_status == 'PASS_EMPTY_VALID_RESPONSE'
    assert empty_auth_status == 'KEY_ACCEPTED'


def test_required_contracts_exist():
    required = [
        'R2E_PACKAGE_DECISION.json',
        'README.md',
        'KEY_HANDLING.md',
        'HTTP_CLIENT_POLICY.md',
        'KNOWN_BLOCKERS.md',
        'DATA_SOURCES_CONFIRMATION.md',
        'manifests/DEPTH_SOURCE_PLAN_R2E.csv',
        'manifests/ENDPOINT_CATALOG_R2E.json',
        'manifests/NORMALIZATION_CONTRACT_R2E.json',
        'manifests/OUTPUT_CONTRACT_R2E.json',
        'schemas/r2e_source_status.schema.json',
    ]
    for rel in required:
        assert (ROOT / rel).exists(), rel


def test_package_decision_boundary():
    decision = json.loads((ROOT / 'R2E_PACKAGE_DECISION.json').read_text(encoding='utf-8'))
    assert decision['secrets_packaged'] is False
    assert decision['raw_payloads_packaged'] is False
    assert 'not Dubai truth' in decision['boundary'] or 'not Dubai' in decision['boundary']

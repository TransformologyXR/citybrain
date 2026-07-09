import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def test_no_env_template_values():
    text = (ROOT / "secrets" / "lta_tfl.env.template").read_text()
    assert "LTA_DATAMALL_ACCOUNT_KEY=" in text
    assert "TFL_PRIMARY_KEY=" in text
    for line in text.splitlines():
        if line and not line.startswith("#") and "=" in line:
            assert line.endswith("=")
def test_inventory_has_sources():
    data = json.loads((ROOT / "manifests" / "source_inventory_lta_tfl.json").read_text())
    assert len(data) >= 10
    assert any(row["provider"] == "LTA DataMall" for row in data)
    assert any("Transport for London" in row["provider"] for row in data)
def test_sandbox_report_inconclusive_not_failed_keys():
    report = json.loads((ROOT / "reports" / "SANDBOX_KEY_VALIDATION_ATTEMPT.json").read_text())
    assert report["status"] == "INCONCLUSIVE_SANDBOX_DNS_BLOCKED"
    assert report["secret_values_logged"] is False


def test_tfl_road_status_endpoint_uses_swagger_all_lowercase():
    script = (ROOT / "scripts" / "harvest_lta_tfl_keyed_sources.py").read_text(encoding="utf-8")
    assert "/Road/all/Status" in script
    assert "/Road/All/Status" not in script


def test_auth_error_payloads_are_not_persisted():
    script = (ROOT / "scripts" / "harvest_lta_tfl_keyed_sources.py").read_text(encoding="utf-8")
    assert "status in (200, 201)" in script
    assert "status and status < 500" not in script


def test_requests_include_user_agent_for_tfl_edge():
    script = (ROOT / "scripts" / "harvest_lta_tfl_keyed_sources.py").read_text(encoding="utf-8")
    assert 'headers.setdefault("User-Agent", "CityBrain-R2A/1.0")' in script

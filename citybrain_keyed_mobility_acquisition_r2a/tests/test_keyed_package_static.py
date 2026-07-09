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

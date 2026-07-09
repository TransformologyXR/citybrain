from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-SERVED-RUNTIME-INTEGRATION-R1"
PACKAGE_ZIP = REPO_ROOT / "packages" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-SERVED-RUNTIME-INTEGRATION-R1.zip"

REQUIRED_OUTPUTS = [
    "D5_SERVED_RUNTIME_INTEGRATION_R1_DECISION.json",
    "D5_LOCAL_SERVER_CONTRACT_R1.json",
    "D5_RUNTIME_REQUEST_RESPONSE_SMOKE_R1.jsonl",
    "D5_RUNTIME_ENDPOINT_AUDIT_R1.json",
    "D6_SERVED_CONTROL_ROOM_INDEX_R1.html",
    "D6_SERVED_INDEX_VALIDATION_R1.json",
    "RUNTIME_BOUNDARY_AND_NO_ACTION_AUDIT_R1.json",
    "SECRET_SCAN_REPORT_R1.json",
    "HASH_MANIFEST.json",
    "CODEX_CLOSEOUT.md",
]


def load_json(name: str):
    return json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8-sig"))


def load_jsonl(name: str) -> list[dict]:
    return [
        json.loads(line)
        for line in (OUTPUT_ROOT / name).read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def test_served_runtime_required_outputs_and_decision():
    for name in REQUIRED_OUTPUTS:
        assert (OUTPUT_ROOT / name).exists(), name
    assert PACKAGE_ZIP.exists()

    decision = load_json("D5_SERVED_RUNTIME_INTEGRATION_R1_DECISION.json")
    assert decision["status"] == "PASS_SYNTHETIC_FACTORY_SEED_R2_D5_SERVED_RUNTIME_INTEGRATION_R1_WITH_LIMITATIONS"
    assert decision["counts"] == {"d5_runtime_packets": 6, "d5_served_runtime_responses": 6}
    assert decision["acceptance"]["product_consumption_read_only"] is True
    assert decision["acceptance"]["d5d6_consumption_smoke_read_only"] is True
    assert decision["acceptance"]["localhost_server_exercised"] is True
    assert decision["acceptance"]["external_network_calls_absent"] is True
    assert all(decision["acceptance"].values())
    assert "NO_PRODUCTION_FRONTEND_OR_PUBLIC_API_CLAIM" in decision["limitations"]


def test_local_server_contract_and_endpoint_audit():
    contract = load_json("D5_LOCAL_SERVER_CONTRACT_R1.json")
    assert contract["status"] == "PASS"
    assert contract["bind_host"] == "127.0.0.1"
    assert contract["public_bind_allowed"] is False
    assert contract["external_network_calls_allowed"] is False
    assert contract["served_runtime_smoke_exercised"] is True
    assert {route["path"] for route in contract["routes"]} == {"/health", "/runtime/request", "/runtime/fixtures"}
    assert contract["request_count"] == 6
    assert contract["response_count"] == 6

    audit = load_json("D5_RUNTIME_ENDPOINT_AUDIT_R1.json")
    assert audit["status"] == "PASS"
    assert audit["bind_localhost_only"] is True
    assert audit["bind_host"] == "127.0.0.1"
    assert audit["public_bind_allowed"] is False
    assert audit["external_network_calls"] == 0
    assert audit["health_http_status"] == 200
    assert audit["fixtures_http_status"] == 200
    assert audit["request_count"] == 6
    assert audit["response_count"] == 6
    assert audit["server_shutdown"] is True
    assert audit["unsupported_routes"] == []


def test_request_response_rows_are_localhost_synthetic_and_bounded():
    rows = load_jsonl("D5_RUNTIME_REQUEST_RESPONSE_SMOKE_R1.jsonl")
    assert len(rows) == 6
    assert {row["status"] for row in rows} == {"PASS"}
    assert {row["runtime_surface"] for row in rows} == {"d5_localhost_served_runtime_fixture"}
    for row in rows:
        assert row["http_status"] == 200
        assert row["served_bind"] == "127.0.0.1"
        assert re.fullmatch(r"http://127\.0\.0\.1:\d+/runtime/request", row["served_url"])
        assert row["external_network_calls"] == 0
        assert row["synthetic_replay_donor_context_only"] is True
        assert row["not_dubai_official_truth"] is True
        assert row["no_action_or_certified_claim"] is True
        assert "LOCALHOST_ONLY" in row["limitations"]
        assert "NO_DISPATCH_CONTROL_ENFORCEMENT_LEGAL_CERTIFIED_CLAIM" in row["limitations"]


def test_d6_served_index_and_runtime_boundaries():
    validation = load_json("D6_SERVED_INDEX_VALIDATION_R1.json")
    assert validation["status"] == "PASS"
    assert validation["contains_html_tag"] is True
    assert validation["contains_status"] is True
    assert validation["local_only"] is True
    assert validation["no_browser_visual_acceptance_claim"] is True
    assert validation["no_production_frontend_claim"] is True

    html = (OUTPUT_ROOT / "D6_SERVED_CONTROL_ROOM_INDEX_R1.html").read_text(encoding="utf-8")
    assert "CityBrain Seed R2 D5 Served Runtime Integration" in html
    assert "PASS_SYNTHETIC_FACTORY_SEED_R2_D5_SERVED_RUNTIME_INTEGRATION_R1_WITH_LIMITATIONS" in html
    assert "Synthetic/replay/donor-context only" in html
    assert "No live monitoring" in html
    assert "No dispatch/control/enforcement/legal/certified claim" in html

    boundary = load_json("RUNTIME_BOUNDARY_AND_NO_ACTION_AUDIT_R1.json")
    assert boundary["status"] == "PASS"
    for key, value in boundary.items():
        if key != "status":
            assert value is True, key


def test_secret_scan_and_hash_manifest_pass():
    secret_scan = load_json("SECRET_SCAN_REPORT_R1.json")
    assert secret_scan["status"] == "PASS"
    assert secret_scan["passed"] is True
    assert secret_scan["secret_values_tested"] == 4
    assert secret_scan["findings"] == []
    assert all(not hits for hits in secret_scan["scans"].values())

    hash_manifest = load_json("HASH_MANIFEST.json")
    assert hash_manifest["status"] == "PASS"
    assert hash_manifest["file_count"] == len(REQUIRED_OUTPUTS) - 1
    assert {entry["path"] for entry in hash_manifest["entries"]} == set(REQUIRED_OUTPUTS) - {"HASH_MANIFEST.json"}


def test_result_package_hygiene_and_redaction():
    with zipfile.ZipFile(PACKAGE_ZIP) as archive:
        names = archive.namelist()
        payload_text = "\n".join(
            archive.read(name).decode("utf-8", errors="ignore")
            for name in names
            if name.endswith((".json", ".jsonl", ".csv", ".md", ".html", ".txt"))
        )

    for name in REQUIRED_OUTPUTS:
        assert f"MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-SERVED-RUNTIME-INTEGRATION-R1/{name}" in names
    assert len([name for name in names if not name.endswith("/")]) == len(REQUIRED_OUTPUTS)
    assert not any("/raw/" in name.lower() for name in names)
    assert not any(name.lower().endswith((".parquet", ".geojson", ".gpkg", ".pbf")) for name in names)
    assert not re.search(r"app_key=(?!redacted)[A-Za-z0-9_\-]{8,}", payload_text, flags=re.I)
    assert "0.0.0.0" not in payload_text

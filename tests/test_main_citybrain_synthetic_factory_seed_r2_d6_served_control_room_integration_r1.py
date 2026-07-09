from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D6-SERVED-CONTROL-ROOM-INTEGRATION-R1"
PACKAGE_ZIP = REPO_ROOT / "packages" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D6-SERVED-CONTROL-ROOM-INTEGRATION-R1.zip"

REQUIRED_OUTPUTS = [
    "D6_SERVED_CONTROL_ROOM_INTEGRATION_R1_DECISION.json",
    "D6_CONTROL_ROOM_CARD_INDEX_R1.jsonl",
    "D6_SERVED_CONTROL_ROOM_LOCAL_INDEX_R1.html",
    "D6_RUNTIME_RESPONSE_BINDING_REPORT_R1.json",
    "D6_ROUTE_LINK_VALIDATION_R1.json",
    "D6_BOUNDARY_AND_NO_ACTION_AUDIT_R1.json",
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


def test_d6_served_required_outputs_and_decision():
    for name in REQUIRED_OUTPUTS:
        assert (OUTPUT_ROOT / name).exists(), name
    assert PACKAGE_ZIP.exists()

    decision = load_json("D6_SERVED_CONTROL_ROOM_INTEGRATION_R1_DECISION.json")
    assert decision["status"] == "PASS_SYNTHETIC_FACTORY_SEED_R2_D6_SERVED_CONTROL_ROOM_INTEGRATION_R1_WITH_LIMITATIONS"
    assert decision["counts"]["served_runtime_cards"] == 6
    assert decision["counts"]["product_consumption_counts"]["EVENT_REPLAY_COMBINED_R1.jsonl"] == 55
    assert decision["counts"]["d5d6_smoke_counts"]["D5_RUNTIME_SMOKE_RESPONSES_R1.jsonl"] == 6
    assert all(decision["acceptance"].values())
    assert "NO_PUBLIC_API_OR_PRODUCTION_FRONTEND_CLAIM" in decision["limitations"]
    assert "NO_BROWSER_VISUAL_ACCEPTANCE_CLAIM" in decision["limitations"]


def test_card_index_preserves_runtime_boundaries():
    cards = load_jsonl("D6_CONTROL_ROOM_CARD_INDEX_R1.jsonl")
    assert len(cards) == 6
    assert {card["intent_family"] for card in cards} == {"watch", "event", "ask", "check", "brief", "spatial"}
    assert {card["runtime_surface"] for card in cards} == {"d5_localhost_served_runtime_fixture"}
    for card in cards:
        assert card["http_status"] == 200
        assert card["served_bind"] == "127.0.0.1"
        assert card["status"] == "PASS"
        assert card["external_network_calls"] == 0
        assert card["synthetic_replay_donor_context_only"] is True
        assert card["not_dubai_official_truth"] is True
        assert card["no_action_or_certified_claim"] is True
        assert card["display_policy"]["localhost_only"] is True
        assert card["display_policy"]["manual_visual_acceptance_claim"] is False
        assert card["display_policy"]["production_frontend_claim"] is False
        assert "NO_LIVE_MONITORING" in card["limitations"]
        assert "NO_DISPATCH_CONTROL_ENFORCEMENT_LEGAL_CERTIFIED_CLAIM" in card["limitations"]


def test_binding_report_and_route_validation():
    binding = load_json("D6_RUNTIME_RESPONSE_BINDING_REPORT_R1.json")
    assert binding["status"] == "PASS"
    assert binding["d5_decision_status"] == "PASS_SYNTHETIC_FACTORY_SEED_R2_D5_SERVED_RUNTIME_INTEGRATION_R1_WITH_LIMITATIONS"
    assert binding["endpoint_bind_host"] == "127.0.0.1"
    assert binding["bind_localhost_only"] is True
    assert binding["external_network_calls"] == 0
    assert binding["served_response_cards"] == 6
    assert all(binding["input_roots_read_only"].values())

    route_validation = load_json("D6_ROUTE_LINK_VALIDATION_R1.json")
    assert route_validation["status"] == "PASS"
    assert route_validation["html_exists"] is True
    assert route_validation["card_index_exists"] is True
    assert route_validation["contains_boundary_text"] is True
    assert route_validation["contains_card_rows"] == 6
    assert route_validation["no_production_frontend_claim"] is True
    assert route_validation["no_public_api_claim"] is True
    assert route_validation["manual_visual_acceptance_claim"] is False


def test_html_index_and_boundary_audit():
    html = (OUTPUT_ROOT / "D6_SERVED_CONTROL_ROOM_LOCAL_INDEX_R1.html").read_text(encoding="utf-8")
    assert "CityBrain Synthetic Seed R2 - D6 Served Control Room Integration R1" in html
    assert "PASS_SYNTHETIC_FACTORY_SEED_R2_D6_SERVED_CONTROL_ROOM_INTEGRATION_R1_WITH_LIMITATIONS" in html
    assert "Synthetic/replay/donor-context only" in html
    assert "Not Dubai official truth" in html
    assert "No live monitoring" in html
    assert "public API" in html

    boundary = load_json("D6_BOUNDARY_AND_NO_ACTION_AUDIT_R1.json")
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
        assert f"MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D6-SERVED-CONTROL-ROOM-INTEGRATION-R1/{name}" in names
    assert len([name for name in names if not name.endswith("/")]) == len(REQUIRED_OUTPUTS)
    assert not any("/raw/" in name.lower() for name in names)
    assert not any(name.lower().endswith((".parquet", ".geojson", ".gpkg", ".pbf")) for name in names)
    assert not re.search(r"app_key=(?!redacted)[A-Za-z0-9_\-]{8,}", payload_text, flags=re.I)
    assert "0.0.0.0" not in payload_text

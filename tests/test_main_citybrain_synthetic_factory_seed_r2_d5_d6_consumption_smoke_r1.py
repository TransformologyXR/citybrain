from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-D6-CONSUMPTION-SMOKE-R1"
PACKAGE_ZIP = REPO_ROOT / "packages" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-D6-CONSUMPTION-SMOKE-R1.zip"

REQUIRED_OUTPUTS = [
    "D5_D6_CONSUMPTION_SMOKE_R1_DECISION.json",
    "PRODUCT_FEED_COUNTS_R1.json",
    "D5_RUNTIME_SMOKE_RESPONSES_R1.jsonl",
    "D6_LOCAL_INDEX_VALIDATION_R1.json",
    "D6_CONTROL_ROOM_CONSUMPTION_INDEX_R1.html",
    "BOUNDARY_AND_NO_ACTION_AUDIT_R1.json",
    "SECRET_SCAN_REPORT_R1.json",
    "HASH_MANIFEST.json",
    "CODEX_CLOSEOUT.md",
]

EXPECTED_COUNTS = {
    "watch": 11,
    "event": 55,
    "ask": 11,
    "check": 11,
    "brief": 11,
    "spatial": 11,
    "d5_runtime_packets": 6,
}


def load_json(name: str):
    return json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8-sig"))


def load_jsonl(name: str) -> list[dict]:
    return [
        json.loads(line)
        for line in (OUTPUT_ROOT / name).read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def test_smoke_required_outputs_and_decision():
    for name in REQUIRED_OUTPUTS:
        assert (OUTPUT_ROOT / name).exists(), name
    assert PACKAGE_ZIP.exists()

    decision = load_json("D5_D6_CONSUMPTION_SMOKE_R1_DECISION.json")
    assert decision["status"] == "PASS_SYNTHETIC_FACTORY_SEED_R2_D5_D6_CONSUMPTION_SMOKE_R1_WITH_LIMITATIONS"
    assert decision["input_statuses"]["product_consumption_r1"] == (
        "PASS_SYNTHETIC_FACTORY_SEED_R2_PRODUCT_CONSUMPTION_R1_WITH_LIMITATIONS"
    )
    assert decision["input_statuses"]["boundary"] == "PASS"
    assert decision["counts"] == EXPECTED_COUNTS
    assert all(decision["acceptance"].values())
    assert "LIM_D5_D6_NOT_DUBAI_OFFICIAL_TRUTH" in decision["limitations"]


def test_product_feed_counts_are_preserved():
    counts = load_json("PRODUCT_FEED_COUNTS_R1.json")
    assert counts["status"] == "PASS"
    assert counts["counts"] == EXPECTED_COUNTS
    assert counts["expected_counts"] == EXPECTED_COUNTS
    assert counts["read_only_input"] is True
    assert all(counts["count_matches"].values())


def test_d5_runtime_smoke_responses_are_bounded_replay_only():
    rows = load_jsonl("D5_RUNTIME_SMOKE_RESPONSES_R1.jsonl")
    assert len(rows) == 6
    assert {row["status"] for row in rows} == {"PASS_SYNTHETIC_REPLAY_PACKET_ACCEPTED"}
    assert {row["runtime_surface"] for row in rows} == {"D5_LOCAL_SERVED_RUNTIME_FIXTURE_ONLY"}
    for row in rows:
        limitations = set(row["limitations"])
        assert "SYNTHETIC_REPLAY_ONLY" in limitations
        assert "DONOR_CONTEXT_ONLY" in limitations
        assert "NOT_DUBAI_OFFICIAL_TRUTH" in limitations
        assert "NO_ACTION_OR_CERTIFIED_CLAIM" in limitations
        assert row["answer_boundary"] == "review_only_fixture_response"


def test_d6_local_index_validation_and_html_boundaries():
    validation = load_json("D6_LOCAL_INDEX_VALIDATION_R1.json")
    assert validation["status"] == "PASS"
    assert validation["local_only"] is True
    assert validation["checks"]["contains_html_tag"] is True
    assert validation["checks"]["contains_synthetic_or_seed_reference"] is True
    assert "NO_PRODUCTION_FRONTEND_CLAIM" in validation["limitations"]

    html = (OUTPUT_ROOT / "D6_CONTROL_ROOM_CONSUMPTION_INDEX_R1.html").read_text(encoding="utf-8")
    assert "CityBrain Synthetic Seed R2 D5/D6 Consumption Smoke R1" in html
    assert "PASS_SYNTHETIC_FACTORY_SEED_R2_D5_D6_CONSUMPTION_SMOKE_R1_WITH_LIMITATIONS" in html
    assert "not official Dubai truth" in html
    assert "no live monitoring" in html
    assert "no dispatch" in html


def test_boundary_and_secret_reports_pass():
    boundary = load_json("BOUNDARY_AND_NO_ACTION_AUDIT_R1.json")
    assert boundary["status"] == "PASS"
    expected_flags = [
        "product_consumption_read_only",
        "no_credentials_written",
        "no_raw_provider_payloads_packaged",
        "no_human_person_level_records",
        "synthetic_replay_donor_context_only",
        "not_dubai_official_truth",
        "no_live_monitoring_claim",
        "no_dispatch_control_enforcement_legal_certified_claim",
    ]
    for flag in expected_flags:
        assert boundary[flag] is True

    secret_scan = load_json("SECRET_SCAN_REPORT_R1.json")
    assert secret_scan["status"] == "PASS"
    assert secret_scan["passed"] is True
    assert secret_scan["secret_values_tested"] == 4
    assert secret_scan["findings"] == []
    assert all(not hits for hits in secret_scan["scans"].values())


def test_hash_manifest_package_hygiene_and_redaction():
    hash_manifest = load_json("HASH_MANIFEST.json")
    assert hash_manifest["status"] == "PASS"
    assert hash_manifest["file_count"] == len(REQUIRED_OUTPUTS) - 1
    assert {entry["path"] for entry in hash_manifest["entries"]} == set(REQUIRED_OUTPUTS) - {"HASH_MANIFEST.json"}

    with zipfile.ZipFile(PACKAGE_ZIP) as archive:
        names = archive.namelist()
        payload_text = "\n".join(
            archive.read(name).decode("utf-8", errors="ignore")
            for name in names
            if name.endswith((".json", ".jsonl", ".csv", ".md", ".html", ".txt"))
        )

    for name in REQUIRED_OUTPUTS:
        assert f"MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-D5-D6-CONSUMPTION-SMOKE-R1/{name}" in names
    assert len([name for name in names if not name.endswith("/")]) == len(REQUIRED_OUTPUTS)
    assert not any("/raw/" in name.lower() for name in names)
    assert not any(name.lower().endswith((".parquet", ".geojson", ".gpkg", ".pbf")) for name in names)
    assert not re.search(r"app_key=(?!redacted)[A-Za-z0-9_\-]{8,}", payload_text, flags=re.I)

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = REPO_ROOT / "outputs" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1"
PACKAGE_ZIP = REPO_ROOT / "packages" / "MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1.zip"

REQUIRED_OUTPUTS = [
    "PRODUCT_CONSUMPTION_R1_DECISION.json",
    "PRODUCT_FEED_MANIFEST_R1.json",
    "WATCH_QUEUE_COMBINED_R1.jsonl",
    "EVENT_REPLAY_COMBINED_R1.jsonl",
    "ASK_FIXTURE_INDEX_R1.jsonl",
    "CHECK_FIXTURE_INDEX_R1.jsonl",
    "BRIEF_FIXTURE_INDEX_R1.jsonl",
    "SPATIAL_OVERLAY_INDEX_R1.jsonl",
    "D5_RUNTIME_PACKET_FIXTURES_R1.jsonl",
    "D6_SYNTHETIC_CONTROL_ROOM_LOCAL_INDEX_R1.html",
    "BOUNDARY_AND_NO_ACTION_AUDIT_R1.json",
    "SECRET_SCAN_REPORT_R1.json",
    "HASH_MANIFEST.json",
    "CODEX_CLOSEOUT.md",
]

JSONL_OUTPUTS = [
    "WATCH_QUEUE_COMBINED_R1.jsonl",
    "EVENT_REPLAY_COMBINED_R1.jsonl",
    "ASK_FIXTURE_INDEX_R1.jsonl",
    "CHECK_FIXTURE_INDEX_R1.jsonl",
    "BRIEF_FIXTURE_INDEX_R1.jsonl",
    "SPATIAL_OVERLAY_INDEX_R1.jsonl",
    "D5_RUNTIME_PACKET_FIXTURES_R1.jsonl",
]


def load_json(name: str):
    return json.loads((OUTPUT_ROOT / name).read_text(encoding="utf-8-sig"))


def load_jsonl(name: str) -> list[dict]:
    rows = []
    for line in (OUTPUT_ROOT / name).read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def test_product_consumption_required_outputs_and_decision():
    for name in REQUIRED_OUTPUTS:
        assert (OUTPUT_ROOT / name).exists(), name
    assert PACKAGE_ZIP.exists()

    decision = load_json("PRODUCT_CONSUMPTION_R1_DECISION.json")
    assert decision["status"] == "PASS_SYNTHETIC_FACTORY_SEED_R2_PRODUCT_CONSUMPTION_R1_WITH_LIMITATIONS"
    assert decision["input_statuses"]["seed_r1"] == "PASS_SYNTHETIC_FACTORY_DUBAI_SEED_R1_WITH_LIMITATIONS"
    assert decision["input_statuses"]["seed_r2"] == "PASS_SYNTHETIC_FACTORY_DUBAI_SEED_R2_MOBILITY_DEPTH_REFRESH_WITH_LIMITATIONS"
    assert decision["counts"] == {
        "watch_rows": 11,
        "event_rows": 55,
        "ask_rows": 11,
        "check_rows": 11,
        "brief_rows": 11,
        "spatial_rows": 11,
        "d5_runtime_packet_rows": 6,
    }
    assert all(decision["acceptance"].values())


def test_product_feed_manifest_links_seed_r1_and_seed_r2_readonly():
    manifest = load_json("PRODUCT_FEED_MANIFEST_R1.json")
    assert manifest["status"] == "PASS_SYNTHETIC_FACTORY_SEED_R2_PRODUCT_CONSUMPTION_R1_WITH_LIMITATIONS"
    assert manifest["read_only_inputs"] is True
    assert manifest["seed_r1_status"] == "PASS_SYNTHETIC_FACTORY_DUBAI_SEED_R1_WITH_LIMITATIONS"
    assert manifest["seed_r2_status"] == "PASS_SYNTHETIC_FACTORY_DUBAI_SEED_R2_MOBILITY_DEPTH_REFRESH_WITH_LIMITATIONS"
    assert manifest["d5_runtime_packet_rows"] == 6
    assert {item["feed_type"] for item in manifest["outputs"]} == {"watch", "event", "ask", "check", "brief", "spatial"}
    assert all(item["rows"] > 0 for item in manifest["outputs"])


def test_product_jsonl_outputs_parse_and_preserve_boundaries():
    expected_counts = {
        "WATCH_QUEUE_COMBINED_R1.jsonl": 11,
        "EVENT_REPLAY_COMBINED_R1.jsonl": 55,
        "ASK_FIXTURE_INDEX_R1.jsonl": 11,
        "CHECK_FIXTURE_INDEX_R1.jsonl": 11,
        "BRIEF_FIXTURE_INDEX_R1.jsonl": 11,
        "SPATIAL_OVERLAY_INDEX_R1.jsonl": 11,
        "D5_RUNTIME_PACKET_FIXTURES_R1.jsonl": 6,
    }
    for name, count in expected_counts.items():
        rows = load_jsonl(name)
        assert len(rows) == count
        for row in rows:
            assert row.get("local_replay_only") is True
            assert row.get("not_dubai_official_truth") is True
            assert row.get("no_action_or_certified_claim") is True
            assert row.get("limitation_refs")

    seed_r2_rows = [row for row in load_jsonl("EVENT_REPLAY_COMBINED_R1.jsonl") if row["source_seed"] == "seed_r2"]
    assert len(seed_r2_rows) == 30
    assert all(row["donor_context_only"] is True for row in seed_r2_rows)
    assert all(row["not_dubai_truth"] is True for row in seed_r2_rows)
    assert all(row["is_real_world_fact"] is False for row in seed_r2_rows)


def test_d5_packets_and_d6_index_are_product_consumable():
    packets = load_jsonl("D5_RUNTIME_PACKET_FIXTURES_R1.jsonl")
    assert {row["packet_type"] for row in packets} == {
        "watch_feed_packet",
        "event_feed_packet",
        "ask_feed_packet",
        "check_feed_packet",
        "brief_feed_packet",
        "spatial_feed_packet",
    }
    assert all(row["row_count"] > 0 for row in packets)
    assert all(row["sample_ids"] for row in packets)

    html = (OUTPUT_ROOT / "D6_SYNTHETIC_CONTROL_ROOM_LOCAL_INDEX_R1.html").read_text(encoding="utf-8")
    assert "CityBrain Synthetic Seed Product Feed R1" in html
    assert "WATCH_QUEUE_COMBINED_R1.jsonl" in html
    assert "D5_RUNTIME_PACKET_FIXTURES_R1.jsonl" in html
    assert "not live monitoring" in html


def test_product_boundary_and_secret_reports_pass():
    boundary = load_json("BOUNDARY_AND_NO_ACTION_AUDIT_R1.json")
    assert boundary["status"] == "PASS"
    for key, value in boundary.items():
        if key.startswith("no_") or key.endswith("_read_only"):
            assert value is True, key

    secret_scan = load_json("SECRET_SCAN_REPORT_R1.json")
    assert secret_scan["status"] == "PASS"
    assert secret_scan["passed"] is True
    assert secret_scan["secret_values_tested"] == 4
    assert secret_scan["findings"] == []
    assert all(not hits for hits in secret_scan["scans"].values())


def test_product_hash_manifest_package_hygiene_and_redaction():
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
        assert f"MAIN-CITYBRAIN-SYNTHETIC-FACTORY-SEED-R2-PRODUCT-CONSUMPTION-R1/{name}" in names
    assert not any("/raw/" in name.lower() for name in names)
    assert not any(name.lower().endswith(".parquet") for name in names)
    assert not re.search(r"app_key=(?!redacted)[A-Za-z0-9_\-]{8,}", payload_text, flags=re.I)
